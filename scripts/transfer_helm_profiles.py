#!/usr/bin/env python3
"""One-shot transfer of folio-helm-v2 per-module values into kitfox-config
deployment profiles (D1=B / ADR-0009).

For each profile name, load the sibling pipelines-shared-library helm values
(a module->values map) and nest it under `modules:` in the existing
platform/deployment-profiles/<name>.yaml, preserving that file's existing keys
(schemaVersion, configType, defaults, moduleClassOverrides, ui).

Sanitization: the source files are credential-free (existingSecret references
only). This tool asserts that no plaintext secret value is present before
writing, and preserves existingSecret references verbatim.

Usage: python scripts/transfer_helm_profiles.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
HELM_DIR = REPO_ROOT.parent / "pipelines-shared-library" / "resources" / "helm"
PROFILE_DIR = REPO_ROOT / "platform" / "deployment-profiles"
NAMES = ["development", "testing", "performance", "release"]

# Keys whose *value* would be a plaintext secret. existingSecret/*Ref are allowed.
PLAINTEXT_SECRET_KEY = re.compile(r"(?i)(password|passwd|pwd|apikey|api_key|"
                                  r"client_secret|access_key|secret_key|private_key)$")
ALLOWED_REF = re.compile(r"^(secretsmanager|ssm|tf)://")


def scan_plaintext(node, path: str, hits: list[str]) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            kp = f"{path}.{k}"
            if isinstance(v, str) and PLAINTEXT_SECRET_KEY.search(str(k)) \
                    and not ALLOWED_REF.match(v):
                hits.append(f"{kp} = {v!r}")
            scan_plaintext(v, kp, hits)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            scan_plaintext(v, f"{path}[{i}]", hits)


def main() -> int:
    for name in NAMES:
        helm_file = HELM_DIR / f"{name}.yaml"
        profile_file = PROFILE_DIR / f"{name}.yaml"
        modules = yaml.safe_load(helm_file.read_text())
        if not isinstance(modules, dict):
            print(f"FAIL {name}: helm file is not a module map")
            return 1

        hits: list[str] = []
        scan_plaintext(modules, "modules", hits)
        if hits:
            print(f"FAIL {name}: plaintext secret(s) detected:")
            for h in hits:
                print(f"   - {h}")
            return 1

        profile = yaml.safe_load(profile_file.read_text())
        profile["modules"] = modules
        with profile_file.open("w") as fh:
            fh.write(f"# platform/deployment-profiles/{name}.yaml — compute base + "
                     f"per-module Helm values (§2.2, ADR-0009)\n")
            yaml.safe_dump(profile, fh, sort_keys=False, default_flow_style=False,
                           width=4096)
        print(f"OK   {name}: {len(modules)} modules transferred")
    return 0


if __name__ == "__main__":
    sys.exit(main())
