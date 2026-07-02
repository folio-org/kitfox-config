"""B.2 — deep-merge with the §3 merge semantics.

Scalars/maps: deep-merge, higher layer wins. Named lists: wholesale replace (no
implicit concatenation). applications.exclude UNION is handled separately in
resolver.excludes — deep_merge stays a pure generic merge."""

from __future__ import annotations

import copy
from typing import Any


def deep_merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    """Return base ⊕ over without mutating either. Dicts merge recursively; any
    non-dict value (including lists) from `over` replaces the value in `base`."""
    result = copy.deepcopy(base)
    for key, over_val in over.items():
        base_val = result.get(key)
        if isinstance(base_val, dict) and isinstance(over_val, dict):
            result[key] = deep_merge(base_val, over_val)
        else:
            result[key] = copy.deepcopy(over_val)
    return result
