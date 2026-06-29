"""D.3 — every tenant id a namespace references (its tenant set + consortia
central/members + dataset-profile tenants) must exist in tenant-catalog.yaml, so
identity resolution can never dangle (§2.4, §3)."""

from __future__ import annotations

from resolver.loader import ConfigTree
from resolver.tenants import Membership

from validators.core import Violation, ns_file, referenced_tenant_ids


def check_tenants_in_catalog(
    tree: ConfigTree, cluster: str, namespace: str, membership: Membership
) -> list[Violation]:
    file = ns_file(cluster, namespace)
    violations: list[Violation] = []
    for tid in referenced_tenant_ids(membership):
        if tid not in tree.catalog:
            violations.append(Violation(
                "D.3", file, tid,
                f"tenant id '{tid}' is referenced by namespace '{namespace}' but is "
                f"not in platform/tenant-catalog.yaml",
            ))
    return violations
