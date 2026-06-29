"""B.6/B.7 — tenant resolution.

Per tenant (tenant-scoped layers, in precedence order §3):
  1 tenantDefaults (type/secure/install/config base)
  3 tenant-catalog[id] (type/name/code/adminUser identity)
  4 tenant-type-defaults[type].applications.exclude  -> UNION
  6 namespace.applications.exclude                    -> UNION
  8 tenants/{id}.yaml override (secure/install/config/index/ui + exclude UNION)

Gap #5: config.kb kept only when mod-kb-ebsco-java is present in the tenant's
deployed apps; config.worldcat only when mod-copycat is present."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from resolver.apps import AppIndex
from resolver.excludes import union_excludes
from resolver.loader import ConfigTree
from resolver.merge import deep_merge

KB_MODULE = "mod-kb-ebsco-java"
WORLDCAT_MODULE = "mod-copycat"


@dataclass
class Membership:
    tenant_ids: list[str]
    default_tenant: str | None
    consortia: list[dict[str, Any]]
    dataset: dict[str, Any] | None   # the resolved dataset profile, or None


def tenant_membership(tree: ConfigTree, cluster: str, namespace: str) -> Membership:
    ns = tree.namespace(cluster, namespace)
    dataset_ref = ns.get("dataset")
    if dataset_ref and dataset_ref.get("profile"):
        # deepcopy so callers never mutate the shared loaded dataset profile.
        profile = copy.deepcopy(tree.dataset_profiles[dataset_ref["profile"]])
        return Membership(
            tenant_ids=list(profile.get("tenants", [])),
            default_tenant=profile.get("defaultTenant"),
            consortia=profile.get("consortia", []),
            dataset={
                "snapshot": dataset_ref.get("snapshot"),
                "profile": dataset_ref["profile"],
                "dbName": profile.get("dbName"),
                "infra": profile.get("infra", {}),
                "moduleReplicas": profile.get("moduleReplicas", {}),
            },
        )
    return Membership(
        tenant_ids=list(ns.get("tenants", [])),
        default_tenant=ns.get("defaultTenant"),
        consortia=copy.deepcopy(ns.get("consortia", [])),
        dataset=None,
    )


def resolve_tenant(
    tree: ConfigTree,
    cluster: str,
    namespace: str,
    tenant_id: str,
    namespace_exclude: list[str],
    app_index: AppIndex | None,
) -> dict[str, Any]:
    if tenant_id not in tree.catalog:
        raise KeyError(f"tenant id '{tenant_id}' not in tenant-catalog.yaml")

    defaults = tree.defaults.get("tenantDefaults", {})
    identity = tree.catalog[tenant_id]
    override = tree.tenant_override(cluster, namespace, tenant_id)

    # Base from tenantDefaults (type/secure/install/config).
    tenant: dict[str, Any] = copy.deepcopy({
        "type": defaults.get("type"),
        "secure": defaults.get("secure", False),
        "install": defaults.get("install", {}),
        "config": defaults.get("config", {}),
    })

    # Layer 3 — catalog identity (type from catalog wins).
    tenant["tenantId"] = tenant_id
    tenant["type"] = identity.get("type", tenant["type"])
    tenant["name"] = identity.get("name")
    if "code" in identity:
        tenant["code"] = identity["code"]
    tenant["adminUser"] = copy.deepcopy(identity.get("adminUser", {}))

    # Layer 8 — override (merge install/config; set secure; carry index/ui; adminUser.passwordRef).
    if override:
        if "secure" in override:
            tenant["secure"] = override["secure"]
        if "install" in override:
            tenant["install"] = deep_merge(tenant["install"], override["install"])
        if "config" in override:
            tenant["config"] = deep_merge(tenant["config"], override["config"])
        if "index" in override:
            tenant["index"] = copy.deepcopy(override["index"])
        if "ui" in override:
            tenant["ui"] = copy.deepcopy(override["ui"])
        if "adminUser" in override:
            tenant["adminUser"] = deep_merge(tenant["adminUser"], override["adminUser"])

    # applications.exclude UNION (layers 4 + 6 + 8).
    type_default_exclude = (
        tree.type_defaults.get(tenant["type"], {})
        .get("applications", {})
        .get("exclude", [])
    )
    tenant_exclude = (override.get("applications", {}) or {}).get("exclude", [])
    excluded = union_excludes(type_default_exclude, namespace_exclude, tenant_exclude)
    tenant["applications"] = {"exclude": excluded}

    # Deployed set + UI cascade inputs (B.8) and Gap #5 gating, when an index is given.
    if app_index is not None:
        deployed = app_index.deployed(excluded)
        tenant["deployedApps"] = deployed
        tenant["excludedAppsUiModules"] = app_index.excluded_ui_modules(excluded)
        present = app_index.modules_of(deployed)
        if KB_MODULE not in present:
            tenant["config"].pop("kb", None)
        if WORLDCAT_MODULE not in present:
            tenant["config"].pop("worldcat", None)

    return tenant
