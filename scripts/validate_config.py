#!/usr/bin/env python3
"""kitfox-config schema validator (Epic A, Story A.9).

Validates every committed YAML under platform/ and clusters/ against the JSON
Schema for its kind (schemas/*.schema.json). A schema violation, or a YAML file
with no matching schema (an unexpected/generated artifact, NFR8), fails the run.

Usage:
    python scripts/validate_config.py                  # default roots: platform/ clusters/
    python scripts/validate_config.py <path|dir> ...   # explicit files/dirs (used by smoke test)

Exit code 0 = all valid; 1 = at least one failure.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = REPO_ROOT / "schemas"
DEFAULT_ROOTS = ["platform", "clusters"]
SCHEMA_BASE = "https://kitfox-config.folio.org/schemas/"

# Map a file path to its schema kind by the §3/§5.1 naming convention. Matching is
# on trailing path segments, so it works for real paths and for test fixtures
# rooted under an arbitrary prefix.
KIND_RULES = [
    (re.compile(r"(^|/)cluster\.yaml$"), "cluster"),
    (re.compile(r"(^|/)namespace\.yaml$"), "namespace"),
    (re.compile(r"/tenants/[^/]+\.yaml$"), "tenant"),
    (re.compile(r"/deployment-profiles/[^/]+\.yaml$"), "deployment-profile"),
    (re.compile(r"/feature-overlays/[^/]+\.yaml$"), "feature-overlay"),
    (re.compile(r"/tenant-type-defaults/[^/]+\.yaml$"), "tenant-type-default"),
    (re.compile(r"/dataset-profiles/[^/]+\.yaml$"), "dataset-profile"),
    (re.compile(r"(^|/)tenant-catalog\.yaml$"), "tenant-catalog"),
    (re.compile(r"(^|/)edge-modules\.yaml$"), "edge-modules"),
    (re.compile(r"(^|/)module-roles\.yaml$"), "module-roles"),
    (re.compile(r"(^|/)tenant-type-ruleset\.yaml$"), "tenant-type-ruleset"),
    (re.compile(r"(^|/)defaults\.yaml$"), "platform-defaults"),
]


@dataclass
class FileResult:
    file: str
    kind: str | None
    ok: bool
    errors: list[str] = field(default_factory=list)


def kind_for(file_path: Path | str) -> str | None:
    norm = str(file_path).replace("\\", "/")
    for regex, kind in KIND_RULES:
        if regex.search(norm):
            return kind
    return None


def build_registry() -> Registry:
    """Load every schema keyed by its $id so cross-file $ref (to _defs) resolves."""
    resources = []
    for schema_file in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = json.loads(schema_file.read_text())
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def _pointer(error) -> str:
    """JSON-pointer of the offending field (A.9 message requirement)."""
    return "/" + "/".join(str(p) for p in error.absolute_path)


def _intra_file_checks(kind: str, doc) -> list[str]:
    """Checks JSON Schema core cannot express (A.5: dataset-profile defaultTenant
    must be a member of tenants[]). Scoped to a single file — cross-file/relational
    guards are Epic D."""
    errors: list[str] = []
    if kind == "dataset-profile" and isinstance(doc, dict) and "defaultTenant" in doc:
        tenants = doc.get("tenants") or []
        if doc["defaultTenant"] not in tenants:
            errors.append(
                f"defaultTenant '{doc['defaultTenant']}' is not a member of "
                f"tenants[] (A.5 intra-file check)"
            )
    return errors


def _collect_yaml_files(roots) -> list[Path]:
    files: set[Path] = set()
    for root in roots:
        abs_root = (REPO_ROOT / root).resolve()
        if not abs_root.exists():
            continue  # root does not exist yet (e.g. clusters/ before Epic C)
        if abs_root.is_dir():
            files.update(abs_root.rglob("*.yaml"))
            files.update(abs_root.rglob("*.yml"))
        elif abs_root.suffix in (".yaml", ".yml"):
            files.add(abs_root)
    return sorted(files)


def validate_paths(roots) -> tuple[list[Path], list[FileResult]]:
    registry = build_registry()
    files = _collect_yaml_files(roots)
    results: list[FileResult] = []

    for file in files:
        rel = str(file.relative_to(REPO_ROOT))
        kind = kind_for(file)
        if kind is None:
            results.append(FileResult(rel, None, False, [
                "no matching schema for this path (unexpected/generated artifact — NFR8)"
            ]))
            continue

        try:
            doc = yaml.safe_load(file.read_text())
        except yaml.YAMLError as exc:
            results.append(FileResult(rel, kind, False, [f"YAML parse error: {exc}"]))
            continue

        schema = registry.get_or_retrieve(SCHEMA_BASE + kind + ".schema.json").value.contents
        validator = Draft202012Validator(
            schema, registry=registry,
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        )
        errors = [
            f"{_pointer(e)} {e.message}"
            for e in sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))
        ]
        errors.extend(_intra_file_checks(kind, doc))
        results.append(FileResult(rel, kind, len(errors) == 0, errors))

    return files, results


def main() -> int:
    roots = sys.argv[1:] or DEFAULT_ROOTS
    files, results = validate_paths(roots)

    if not files:
        print(f"No YAML files found under: {', '.join(roots)}")
        return 0

    failed = 0
    for r in results:
        if r.ok:
            print(f"PASS  {r.file}  [{r.kind}]")
        else:
            failed += 1
            print(f"FAIL  {r.file}" + (f"  [{r.kind}]" if r.kind else ""))
            for e in r.errors:
                print(f"        - {e}")
    print(f"\n{len(results) - failed}/{len(results)} files valid.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())