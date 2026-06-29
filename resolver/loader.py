"""B.1 — discovery + layer loading. The directory tree IS the deployment
hierarchy (§5.1); discovery is readdir, not parsing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


@dataclass
class ConfigTree:
    """All on-disk layers loaded once. Tenant-override files are loaded lazily by
    id via tenant_override(). Reference (non-merge) files are loaded eagerly."""

    root: Path
    defaults: dict[str, Any]
    deployment_profiles: dict[str, dict[str, Any]]   # configType -> profile
    catalog: dict[str, Any]                           # tenant id -> identity
    type_defaults: dict[str, dict[str, Any]]          # type -> file
    feature_overlays: dict[str, dict[str, Any]]       # name -> overlay
    dataset_profiles: dict[str, dict[str, Any]]       # name -> profile
    module_roles: dict[str, Any]
    tenant_ruleset: dict[str, Any]

    def cluster(self, cluster: str) -> dict[str, Any]:
        return _load_yaml(self.root / "clusters" / cluster / "cluster.yaml")

    def namespace(self, cluster: str, namespace: str) -> dict[str, Any]:
        return _load_yaml(
            self.root / "clusters" / cluster / "namespaces" / namespace / "namespace.yaml"
        )

    def tenant_override(self, cluster: str, namespace: str, tenant_id: str) -> dict[str, Any]:
        return _load_yaml(
            self.root / "clusters" / cluster / "namespaces" / namespace
            / "tenants" / f"{tenant_id}.yaml"
        )

    def list_clusters(self) -> list[str]:
        base = self.root / "clusters"
        return sorted(p.name for p in base.iterdir() if p.is_dir()) if base.exists() else []

    def list_namespaces(self, cluster: str) -> list[str]:
        base = self.root / "clusters" / cluster / "namespaces"
        return sorted(p.name for p in base.iterdir() if p.is_dir()) if base.exists() else []


def _load_dir(directory: Path, key: str) -> dict[str, dict[str, Any]]:
    """Load every *.yaml in a dir into {selectorValue: doc}, keyed by doc[key]
    (falling back to the filename stem)."""
    out: dict[str, dict[str, Any]] = {}
    if not directory.exists():
        return out
    for f in sorted(directory.glob("*.yaml")):
        doc = _load_yaml(f)
        out[doc.get(key, f.stem)] = doc
    return out


def load_tree(root: Path) -> ConfigTree:
    platform = root / "platform"
    return ConfigTree(
        root=root,
        defaults=_load_yaml(platform / "defaults.yaml"),
        deployment_profiles=_load_dir(platform / "deployment-profiles", "configType"),
        catalog=_load_yaml(platform / "tenant-catalog.yaml").get("tenants", {}),
        type_defaults=_load_dir(platform / "tenant-type-defaults", "type"),
        feature_overlays=_load_dir(platform / "feature-overlays", "name"),
        dataset_profiles=_load_dir(platform / "dataset-profiles", "name"),
        module_roles=_load_yaml(platform / "module-roles.yaml"),
        # Not a merge layer; pre-loaded so the Epic D cross-level validators can
        # consume it from the same tree (B.1 readiness gap #1).
        tenant_ruleset=_load_yaml(platform / "tenant-type-ruleset.yaml"),
    )
