"""gap #8 — releaseType ↔ sunflower consistency. The legacy
DependentParametersResolver coupled the SUNFLOWER release to the `sunflower`
feature overlay; when a namespace declares releaseType: SUNFLOWER it should also
list `sunflower` in configExtensions so the overlay is applied (§2.6, gap #8).

Light/advisory by intent: namespace-internal, kept minimal."""

from __future__ import annotations

from typing import Any

from validators.core import Violation, ns_file


def check_release_type_sunflower(
    cluster: str, namespace: str, ns_doc: dict[str, Any]
) -> list[Violation]:
    if ns_doc.get("releaseType") != "SUNFLOWER":
        return []
    if "sunflower" in (ns_doc.get("configExtensions") or []):
        return []
    return [Violation(
        "gap#8", ns_file(cluster, namespace), namespace,
        f"namespace '{namespace}' has releaseType: SUNFLOWER but 'sunflower' is not in "
        f"configExtensions (the overlay would not be applied)",
    )]
