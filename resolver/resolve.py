"""B.9 — orchestration + deterministic emit."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from resolver.apps import AppIndex
from resolver.loader import ConfigTree, load_tree
from resolver.merge import deep_merge
from resolver.model import ResolvedNamespace, ResolvedTenant
from resolver.overlays import apply_overlays
from resolver.roles import mark_read_write_modules
from resolver.tenants import resolve_tenant, tenant_membership


def _namespace_base(
    tree: ConfigTree, cluster: str, namespace: str
) -> tuple[dict[str, Any], str]:
    """Merge namespace-scoped layers 1 (defaults infra/features) → 2 (profile) →
    5 (cluster) → 6 (namespace). tenantDefaults is excluded (tenant-scoped)."""
    ns = tree.namespace(cluster, namespace)
    config_type = ns.get("configType", "development")
    profile = tree.deployment_profiles.get(config_type, {})
    defaults = {k: v for k, v in tree.defaults.items() if k != "tenantDefaults"}
    cluster_doc = tree.cluster(cluster)

    merged = deep_merge(defaults, profile)
    merged = deep_merge(merged, cluster_doc)
    merged = deep_merge(merged, ns)
    return merged, config_type


def resolve_namespace(
    root: Path,
    cluster: str,
    namespace: str,
    app_index: AppIndex | None = None,
) -> ResolvedNamespace:
    tree = load_tree(Path(root))
    merged, config_type = _namespace_base(tree, cluster, namespace)
    membership = tenant_membership(tree, cluster, namespace)
    ns_exclude = (merged.get("applications", {}) or {}).get("exclude", [])

    # Resolve tenants first (need secure info for presence-driven overlays).
    tenants_raw = [
        resolve_tenant(tree, cluster, namespace, tid, ns_exclude, app_index)
        for tid in membership.tenant_ids
    ]
    secure_ids = [t["tenantId"] for t in tenants_raw if t.get("secure")]
    any_secure = bool(secure_ids)
    secure_tenant_id = secure_ids[0] if secure_ids else None

    features = merged.get("features", {})

    # Overlays (layer 7) — namespace-scoped modules/ui.
    overlaid = apply_overlays(
        base={"modules": copy.deepcopy(merged.get("modules", {})),
              "ui": copy.deepcopy(merged.get("ui", {}))},
        config_extensions=merged.get("configExtensions", []),
        overlays=tree.feature_overlays,
        any_secure=any_secure,
        secure_tenant_id=secure_tenant_id,
        rtr=bool(features.get("rtr", False)),
    )
    modules = overlaid.get("modules", {})
    ui = overlaid.get("ui", {})

    # Dataset moduleReplicas -> modules.<m>.replicaCount (§6 §12d).
    dataset = membership.dataset
    if dataset:
        for mod_name, replicas in (dataset.get("moduleReplicas") or {}).items():
            modules.setdefault(mod_name, {})["replicaCount"] = replicas
        # Dataset restore sizing onto infra.
        merged.setdefault("infra", {})
        if dataset.get("infra", {}).get("pgInstanceType"):
            merged["infra"]["pgInstanceType"] = dataset["infra"]["pgInstanceType"]

    # rwSplit marking (B.10).
    modules, rw_marked = mark_read_write_modules(
        base_modules=modules,
        read_write_modules=tree.module_roles.get("readWriteModules", []),
        rw_split=bool(features.get("rwSplit", False)),
    )

    tenants = [
        ResolvedTenant(
            tenantId=t["tenantId"],
            type=t["type"],
            name=t.get("name"),
            secure=t.get("secure", False),
            adminUser=t.get("adminUser", {}),
            install=t.get("install", {}),
            config=t.get("config", {}),
            applications=t.get("applications", {"exclude": []}),
            code=t.get("code"),
            index=t.get("index"),
            ui=t.get("ui"),
            deployedApps=t.get("deployedApps"),
            excludedAppsUiModules=t.get("excludedAppsUiModules"),
        )
        for t in tenants_raw
    ]

    dataset_out = None
    if dataset:
        dataset_out = {
            "snapshot": dataset.get("snapshot"),
            "profile": dataset.get("profile"),
            "dbName": dataset.get("dbName"),
        }

    return ResolvedNamespace(
        clusterName=cluster,
        namespaceName=namespace,
        platform=merged.get("platform"),
        configType=config_type,
        platformBranch=merged.get("platformBranch"),
        releaseType=merged.get("releaseType"),
        lifecycle=merged.get("lifecycle", {}),
        members=merged.get("members", []),
        infra=merged.get("infra", {}),
        features=features,
        operations=merged.get("operations", {}),
        consortia=membership.consortia,
        applications={"exclude": sorted(ns_exclude)},
        modules=modules,
        readWriteModules=rw_marked,
        defaultTenant=membership.default_tenant,
        tenants=tenants,
        dataset=dataset_out,
        podPlacement=merged.get("podPlacement"),
        ui=ui,
    )


def emit_json(resolved: ResolvedNamespace) -> str:
    """Deterministic serialization: sorted keys → byte-identical across runs (§3)."""
    return json.dumps(resolved.to_dict(), sort_keys=True, indent=2, ensure_ascii=False)
