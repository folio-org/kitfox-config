"""Epic D runner — discover every (cluster, namespace), run all cross-level checks,
return {(cluster, namespace): [Violation, ...]}.

D.2–D.5 + gap#8 read the raw tree. D.1 needs the Epic B resolver's deployed-app
set, so it runs only when (a) D.3 found no dangling tenant ids (else resolution
would raise) and (b) an AppIndex is supplied (else there is no deployed set)."""

from __future__ import annotations

from pathlib import Path

from resolver import resolve_namespace
from resolver.apps import AppIndex
from resolver.loader import ConfigTree, load_tree
from resolver.tenants import tenant_membership

from validators.core import Violation, ns_file
from validators.d1_tenant_type import check_tenant_type_ruleset
from validators.d2_default_tenant import check_default_tenant
from validators.d3_catalog import check_tenants_in_catalog
from validators.d4_consortia import check_consortia_block
from validators.d5_dataset_tenants import check_dataset_xor_tenants
from validators.d8_release_type import check_release_type_sunflower


def run_namespace(
    tree: ConfigTree, cluster: str, namespace: str, app_index: AppIndex | None
) -> list[Violation]:
    ns_doc = tree.namespace(cluster, namespace)
    membership = tenant_membership(tree, cluster, namespace)

    violations: list[Violation] = []
    violations += check_dataset_xor_tenants(cluster, namespace, ns_doc)
    catalog_violations = check_tenants_in_catalog(tree, cluster, namespace, membership)
    violations += catalog_violations
    violations += check_default_tenant(cluster, namespace, membership)
    violations += check_consortia_block(tree, cluster, namespace, membership)
    violations += check_release_type_sunflower(cluster, namespace, ns_doc)

    # D.1 needs the resolved deployed-app set. Skip if catalog refs are unsound
    # (resolution would raise) or no descriptor is available.
    if not catalog_violations and app_index is not None:
        try:
            resolved = resolve_namespace(tree.root, cluster, namespace, app_index)
            violations += check_tenant_type_ruleset(
                resolved, tree.tenant_ruleset, cluster, namespace
            )
        except Exception as exc:  # resolution failure — surface, don't crash the gate
            violations.append(Violation(
                "D.1", ns_file(cluster, namespace), namespace,
                f"could not resolve namespace for tenant-type check: {exc}",
            ))
    return violations


def run_tree(
    root: Path, app_index: AppIndex | None
) -> dict[tuple[str, str], list[Violation]]:
    tree = load_tree(Path(root))
    results: dict[tuple[str, str], list[Violation]] = {}
    for cluster in tree.list_clusters():
        for namespace in tree.list_namespaces(cluster):
            results[(cluster, namespace)] = run_namespace(
                tree, cluster, namespace, app_index
            )
    return results
