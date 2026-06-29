"""D.5 — a namespace must reference its tenants EITHER via dataset.profile OR an
explicit tenants[] list, never both and never neither (§2.6, §2.4b). Raw-file
check: the resolver collapses a dataset profile into a tenant set, so this must
read the authored namespace.yaml to see what the author actually wrote."""

from __future__ import annotations

from typing import Any

from validators.core import Violation, ns_file


def check_dataset_xor_tenants(
    cluster: str, namespace: str, ns_doc: dict[str, Any]
) -> list[Violation]:
    has_dataset = bool((ns_doc.get("dataset") or {}).get("profile"))
    has_tenants = bool(ns_doc.get("tenants"))
    file = ns_file(cluster, namespace)

    if has_dataset and has_tenants:
        profile = ns_doc["dataset"]["profile"]
        return [Violation(
            "D.5", file, namespace,
            f"namespace '{namespace}' sets both dataset.profile ('{profile}') and an "
            f"explicit tenants[] list; they are mutually exclusive (§2.6/§2.4b)",
        )]
    if not has_dataset and not has_tenants:
        return [Violation(
            "D.5", file, namespace,
            f"namespace '{namespace}' sets neither dataset.profile nor an explicit "
            f"tenants[] list; exactly one is required (§2.6/§2.4b)",
        )]
    return []
