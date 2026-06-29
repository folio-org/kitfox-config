"""D.2 — a namespace's defaultTenant must be one of its resolved tenant ids
(explicit list or dataset-profile set). Replaces the derived
`dataset ? fs09000000 : diku` logic with an explicit, checked field (§2.6, §6 §12d)."""

from __future__ import annotations

from resolver.tenants import Membership

from validators.core import Violation, ns_file


def check_default_tenant(
    cluster: str, namespace: str, membership: Membership
) -> list[Violation]:
    default = membership.default_tenant
    if default is None:
        return []
    if default in membership.tenant_ids:
        return []
    valid = ", ".join(membership.tenant_ids) or "(none)"
    return [Violation(
        "D.2", ns_file(cluster, namespace), default,
        f"defaultTenant '{default}' is not in namespace '{namespace}' tenant set "
        f"[{valid}]",
    )]
