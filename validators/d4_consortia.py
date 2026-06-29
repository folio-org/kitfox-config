"""D.4 — when a namespace DEPLOYS a consortia-central tenant (catalog type), it
must have exactly one consortia block naming that central, and every listed member
must be a consortia-member tenant present in the namespace's tenant set (§2.6,
§2.4b). The block lives on the namespace, or — for a dataset namespace — on the
dataset profile; both surface via Membership.consortia.

Trigger is the deployed central tenant, not the block: sprint names central
`consortium` only in its consortia block (not in tenants[]), so it does not deploy
a central and is correctly skipped."""

from __future__ import annotations

from resolver.loader import ConfigTree
from resolver.tenants import Membership

from validators.core import Violation, catalog_type, ns_file


def check_consortia_block(
    tree: ConfigTree, cluster: str, namespace: str, membership: Membership
) -> list[Violation]:
    file = ns_file(cluster, namespace)
    violations: list[Violation] = []
    tenant_set = set(membership.tenant_ids)

    central_tenants = [
        tid for tid in membership.tenant_ids
        if catalog_type(tree, tid) == "consortia-central"
    ]

    for central in central_tenants:
        entries = [c for c in (membership.consortia or []) if c.get("central") == central]
        if not entries:
            violations.append(Violation(
                "D.4", file, central,
                f"namespace '{namespace}' deploys consortia-central tenant '{central}' "
                f"but has no consortia block naming it as central",
            ))
            continue
        if len(entries) > 1:
            violations.append(Violation(
                "D.4", file, central,
                f"namespace '{namespace}' has {len(entries)} consortia blocks for "
                f"central '{central}'; exactly one is required",
            ))
            continue
        for member in entries[0].get("members", []) or []:
            mtype = catalog_type(tree, member)
            if mtype != "consortia-member":
                violations.append(Violation(
                    "D.4", file, member,
                    f"consortia member '{member}' (central '{central}') has catalog type "
                    f"'{mtype}', expected consortia-member",
                ))
            if member not in tenant_set:
                violations.append(Violation(
                    "D.4", file, member,
                    f"consortia member '{member}' (central '{central}') is not in the "
                    f"namespace '{namespace}' tenant set",
                ))
    return violations
