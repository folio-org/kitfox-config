"""B.10 — rwSplit reader-endpoint marking (§2.3, §6).

When features.rwSplit is true, every module named in module-roles.readWriteModules
is flagged to receive integrations.db.hostReader (mark only). The reader COORDINATE
is injected by the pipeline from the Terraform enable_rw_split output at deploy
(topology-not-coordinates, NFR7). When rwSplit is false, nothing is flagged."""

from __future__ import annotations

import copy
from typing import Any


def mark_read_write_modules(
    base_modules: dict[str, Any],
    read_write_modules: list[str],
    rw_split: bool,
) -> tuple[dict[str, Any], list[str]]:
    modules = copy.deepcopy(base_modules or {})
    if not rw_split:
        return modules, []
    marked: list[str] = []
    for name in read_write_modules or []:
        mod = modules.setdefault(name, {})
        mod.setdefault("integrations", {}).setdefault("db", {})["hostReader"] = True
        marked.append(name)
    return modules, sorted(marked)
