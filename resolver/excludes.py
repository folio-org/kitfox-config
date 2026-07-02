"""B.3 — applications.exclude UNION across type-default (4), namespace (6), and
tenant override (8). The deliberate exception to wholesale-replace: exclusions
only accumulate; a lower layer can add but never un-exclude (§3)."""

from __future__ import annotations

from typing import Iterable


def union_excludes(*layers: Iterable[str] | None) -> list[str]:
    acc: set[str] = set()
    for layer in layers:
        if layer:
            acc.update(layer)
    return sorted(acc)
