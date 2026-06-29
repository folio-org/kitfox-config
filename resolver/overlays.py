"""B.4/B.5 — feature overlays as data (§2.2b).

One generic merge loop over configExtensions (list order), then presence-driven
selection (secure-tenant iff any tenant secure; rtr iff features.rtr), then
${var} value-substitution. Zero per-feature branches: the only feature names
hard-referenced are the presence-driven selectors, which are SELECTION keys, not
behavioral branches (the behavior lives entirely in the overlay files)."""

from __future__ import annotations

import copy
import re
from typing import Any

from resolver.merge import deep_merge

_PLACEHOLDER = re.compile(r"\$\{(\w+)\}")

# Overlay metadata keys that must not merge into the resolved namespace body.
_META_KEYS = {"schemaVersion", "name"}

PRESENCE_SECURE = "secure-tenant"
PRESENCE_RTR = "rtr"


def substitute(data: Any, values: dict[str, str]) -> Any:
    """Recursively replace ${var} occurrences in strings using `values`. Unknown
    placeholders are left intact (value-substitution only, no logic)."""
    if isinstance(data, dict):
        return {k: substitute(v, values) for k, v in data.items()}
    if isinstance(data, list):
        return [substitute(v, values) for v in data]
    if isinstance(data, str):
        return _PLACEHOLDER.sub(
            lambda m: values.get(m.group(1), m.group(0)), data
        )
    return data


def _overlay_body(overlay: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in overlay.items() if k not in _META_KEYS}


def apply_overlays(
    base: dict[str, Any],
    config_extensions: list[str],
    overlays: dict[str, dict[str, Any]],
    any_secure: bool,
    secure_tenant_id: str | None,
    rtr: bool,
) -> dict[str, Any]:
    result = copy.deepcopy(base)

    # Explicit overlays, in list order (later overrides earlier).
    names = list(config_extensions or [])
    # Presence-driven selection appended after explicit list.
    if any_secure and PRESENCE_SECURE not in names:
        names.append(PRESENCE_SECURE)
    if rtr and PRESENCE_RTR not in names:
        names.append(PRESENCE_RTR)

    for name in names:
        overlay = overlays.get(name)
        if overlay is None:
            continue
        result = deep_merge(result, _overlay_body(overlay))

    # Value substitution (only secureTenantId today).
    subs: dict[str, str] = {}
    if secure_tenant_id is not None:
        subs["secureTenantId"] = secure_tenant_id
    if subs:
        result = substitute(result, subs)
    return result
