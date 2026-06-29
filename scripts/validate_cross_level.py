#!/usr/bin/env python3
"""kitfox-config cross-level validator (Epic D, Story D.6).

Runs AFTER schema validation (scripts/validate_config.py). Discovers every
(cluster, namespace) and enforces the five cross-level guards (D.1-D.5) plus the
gap#8 releaseType/sunflower check — the relational rules JSON Schema cannot express.

Descriptor (D.1 deployed-app set): the sibling platform-lsp descriptor when present
(local dev), else the vendored tests/fixtures/platform-descriptor.json (CI).

Usage:
    python scripts/validate_cross_level.py [--descriptor PATH] [--app-descriptors DIR]

Exit code 0 = no violations; 1 = at least one violation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make the repo root importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resolver.apps import AppIndex          # noqa: E402
from validators import run_tree             # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = Path(__file__).parent.parent.parent  # unresolved: follows symlinks
SIBLING_DESCRIPTOR = WORKSPACE / "platform-lsp" / "platform-descriptor.json"
SIBLING_APP_DESCRIPTORS = WORKSPACE / "platform-lsp" / "local-dev" / "appDescriptors"
VENDORED_DESCRIPTOR = REPO_ROOT / "tests" / "fixtures" / "platform-descriptor.json"
VENDORED_APP_DESCRIPTORS = REPO_ROOT / "tests" / "fixtures" / "appDescriptors"


def _resolve_descriptor(arg: Path | None) -> tuple[Path, Path]:
    if arg is not None:
        return arg, arg.parent / "appDescriptors"
    if SIBLING_DESCRIPTOR.exists():
        return SIBLING_DESCRIPTOR, SIBLING_APP_DESCRIPTORS
    return VENDORED_DESCRIPTOR, VENDORED_APP_DESCRIPTORS


def main() -> int:
    parser = argparse.ArgumentParser(description="kitfox-config cross-level validator")
    parser.add_argument("--descriptor", type=Path, default=None)
    parser.add_argument("--app-descriptors", type=Path, default=None)
    args = parser.parse_args()

    descriptor, app_descriptors = _resolve_descriptor(args.descriptor)
    if args.app_descriptors is not None:
        app_descriptors = args.app_descriptors

    app_index = None
    if descriptor.exists():
        app_index = AppIndex.load(descriptor, app_descriptors)
    else:
        print(f"WARNING: no descriptor at {descriptor}; D.1 deployed-app checks skipped")

    results = run_tree(REPO_ROOT, app_index)

    total = 0
    for (cluster, namespace), violations in sorted(results.items()):
        label = f"{cluster}/{namespace}"
        if not violations:
            print(f"PASS  {label}")
            continue
        total += len(violations)
        print(f"FAIL  {label}")
        for v in violations:
            print(f"        - {v}")

    n = len(results)
    print(f"\n{n - sum(1 for vs in results.values() if vs)}/{n} namespaces clean; "
          f"{total} violation(s).")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
