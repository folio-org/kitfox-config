"""Cross-level validators (Epic D) — shared model + helpers.

D.2–D.5 and gap#8 read the RAW loaded tree (ConfigTree + tenant_membership), so a
dangling tenant id reports as a clean D.3 message rather than crashing the Epic B
resolver. Only D.1 uses the resolver (deployed-app set)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from resolver.loader import ConfigTree
from resolver.tenants import Membership


@dataclass(frozen=True)
class Violation:
    rule: str       # "D.1".."D.5", "gap#8"
    file: str       # offending file path, repo-relative
    entity: str     # tenant id / namespace name / app — whatever the rule names
    message: str    # precise, actionable (D.6)

    def __str__(self) -> str:
        return f"[{self.rule}] {self.file}: {self.message}"


def ns_file(cluster: str, namespace: str) -> str:
    """Repo-relative path to a namespace.yaml (the entity most rules name)."""
    return f"clusters/{cluster}/namespaces/{namespace}/namespace.yaml"


def catalog_type(tree: ConfigTree, tenant_id: str) -> str | None:
    """The tenant's `type` from tenant-catalog.yaml, or None if absent."""
    return (tree.catalog.get(tenant_id) or {}).get("type")


def referenced_tenant_ids(membership: Membership) -> list[str]:
    """Every tenant id a namespace references: its tenant set (explicit or dataset
    profile) plus each consortia block's central + members (which may not all be in
    the tenant set — e.g. sprint names central `consortium` only in `consortia:`)."""
    ids: set[str] = set(membership.tenant_ids)
    for entry in membership.consortia or []:
        if entry.get("central"):
            ids.add(entry["central"])
        ids.update(entry.get("members", []) or [])
    return sorted(ids)
