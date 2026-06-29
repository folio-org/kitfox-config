#!/usr/bin/env python3
"""Resolve a (cluster, namespace) and print the resolved model as JSON (B.9).

Usage:
    python scripts/resolve.py <cluster> <namespace> \
        [--descriptor PATH] [--app-descriptors DIR]

The descriptor inputs are optional (FAR/descriptor stand-in). When omitted, the
deployed-app set / UI-cascade / Gap #5 gating are not computed; the exclude set
and all other resolution still emit."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make the repo root importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from resolver import emit_json, resolve_namespace          # noqa: E402
from resolver.apps import AppIndex                          # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = Path(__file__).parent.parent.parent  # unresolved: follows symlinks
DEFAULT_DESCRIPTOR = WORKSPACE / "platform-lsp" / "platform-descriptor.json"
DEFAULT_APP_DESCRIPTORS = WORKSPACE / "platform-lsp" / "local-dev" / "appDescriptors"


def main() -> int:
    parser = argparse.ArgumentParser(description="kitfox-config reference resolver")
    parser.add_argument("cluster")
    parser.add_argument("namespace")
    parser.add_argument("--descriptor", type=Path, default=DEFAULT_DESCRIPTOR)
    parser.add_argument("--app-descriptors", type=Path, default=DEFAULT_APP_DESCRIPTORS)
    parser.add_argument("--no-apps", action="store_true",
                        help="skip descriptor-driven deployed-set/cascade/Gap#5")
    args = parser.parse_args()

    app_index = None
    if not args.no_apps and args.descriptor.exists():
        app_index = AppIndex.load(args.descriptor, args.app_descriptors)

    resolved = resolve_namespace(REPO_ROOT, args.cluster, args.namespace, app_index)
    print(emit_json(resolved))
    return 0


if __name__ == "__main__":
    sys.exit(main())
