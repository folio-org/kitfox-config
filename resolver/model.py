"""B.9 — resolved model objects. Field names map onto CreateNamespaceParameters /
EurekaNamespace / EurekaTenant (§5.2). Topology flags + names present; coordinates
and versions deliberately absent (filled by TF outputs / FAR at deploy)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ResolvedTenant:
    tenantId: str
    type: str
    name: str | None
    secure: bool
    adminUser: dict[str, Any]
    install: dict[str, Any]
    config: dict[str, Any]
    applications: dict[str, Any]                 # {"exclude": [...]}
    code: str | None = None
    index: list[dict[str, Any]] | None = None
    ui: dict[str, Any] | None = None
    deployedApps: list[str] | None = None
    excludedAppsUiModules: dict[str, list[str]] | None = None


@dataclass
class ResolvedNamespace:
    clusterName: str
    namespaceName: str
    platform: str
    configType: str
    platformBranch: str | None
    releaseType: str | None
    lifecycle: dict[str, Any]
    members: list[str]
    infra: dict[str, Any]
    features: dict[str, Any]
    operations: dict[str, Any]
    consortia: list[dict[str, Any]]
    applications: dict[str, Any]                 # namespace-wide {"exclude": [...]}
    modules: dict[str, Any]
    readWriteModules: list[str]
    defaultTenant: str | None
    tenants: list[ResolvedTenant]
    dataset: dict[str, Any] | None = None
    podPlacement: dict[str, Any] | None = None
    uiDefaults: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
