"""D.1 — for every app a tenant DEPLOYS, assert the tenant's type is in the
matching rule's allowedTypes and, if the rule requires it, the tenant is secure
(§4 algorithm). The per-type defaults (§2.8) make the green path automatic; this is
the backstop against an incorrect override or a hand-edited type default.

Consumes a resolved namespace (Epic B) — `deployed = available − UNION(excludes)`
is already computed as ResolvedTenant.deployedApps. A tenant with deployedApps None
(no descriptor available) is skipped: nothing to check without the deployed set."""

from __future__ import annotations

from typing import Any

from resolver.model import ResolvedNamespace

from validators.core import Violation, ns_file


def _rule_for(app: str, ruleset: dict[str, Any]) -> dict[str, Any]:
    for rule in ruleset.get("rules", []):
        if app in rule.get("applications", []):
            return rule
    return ruleset.get("default", {"allowedTypes": [], "requireSecure": False})


def check_tenant_type_ruleset(
    resolved: ResolvedNamespace,
    ruleset: dict[str, Any],
    cluster: str,
    namespace: str,
) -> list[Violation]:
    file = ns_file(cluster, namespace)
    violations: list[Violation] = []

    for tenant in resolved.tenants:
        if tenant.deployedApps is None:
            continue
        for app in tenant.deployedApps:
            rule = _rule_for(app, ruleset)
            allowed = rule.get("allowedTypes", [])
            if tenant.type not in allowed:
                violations.append(Violation(
                    "D.1", file, tenant.tenantId,
                    f"{tenant.type} tenant '{tenant.tenantId}' deploys {app} "
                    f"(allowed: {', '.join(allowed) or '(none)'})",
                ))
            elif rule.get("requireSecure") and not tenant.secure:
                violations.append(Violation(
                    "D.1", file, tenant.tenantId,
                    f"tenant '{tenant.tenantId}' deploys {app} which requires "
                    f"secure: true, but the tenant is not secure",
                ))
    return violations
