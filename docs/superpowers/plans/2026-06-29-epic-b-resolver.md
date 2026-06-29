# Epic B — Resolver / Merge Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone, pure-function Python resolver under `kitfox-config/` that takes the on-disk config tree + a `(cluster, namespace)` and emits the fully-resolved namespace + per-tenant model, implementing the §3 8-layer resolution and merge semantics exactly.

**Architecture:** A small package `kitfox-config/resolver/` with one responsibility per module — `loader` (discovery + YAML load, B.1), `merge` (deep-merge + named-list replace, B.2), `excludes` (UNION accumulation, B.3), `tenants` (catalog identity + type-default + dataset, B.6/B.7), `apps` (available set, deployed-by-subtraction, UI-cascade inputs, Gap #5 presence, B.8), `overlays` (configExtensions + presence-driven + `${var}` substitution, B.4/B.5), `roles` (rwSplit reader marking, B.10), `model` (resolved dataclasses, B.9), `resolve` (orchestration + deterministic emit, B.9). A thin CLI lives at `scripts/resolve.py`. Descriptor data (app names, app→modules/uiModules) is an **injected input** standing in for FAR/descriptors — the resolver stays a pure function of `(config, injected descriptor index)`; versions/coordinates are deliberately absent.

**Tech Stack:** Python 3.14 (existing `kitfox-config/.venv`), PyYAML (already installed), pytest (installed in Task 0), stdlib `json`/`dataclasses`/`pathlib`. No new runtime deps beyond pytest for tests.

---

## Design facts locked from the frozen architecture (read before coding)

These are the exact rules the code must encode. Citations are to `design-artifacts/B-Trigger-Map/kitfox-config-schema-architecture.md`.

**Resolution order — 8 layers, lowest→highest (§3 "Resolution order"):**
1. `platform/defaults.yaml` (global; `infra`/`features` are namespace-scoped, `tenantDefaults` is the tenant base)
2. `platform/deployment-profiles/{configType}.yaml` — **selector** = `namespace.configType` (default `development`); selection-key ≠ precedence
3. `platform/tenant-catalog.yaml[id]` — tenant identity (tenant-scoped)
4. `platform/tenant-type-defaults/{type}.yaml` — type drives this (tenant-scoped)
5. `clusters/{cluster}/cluster.yaml`
6. `clusters/{cluster}/namespaces/{ns}/namespace.yaml`
7. `platform/feature-overlays/{ext}.yaml` — one per `configExtensions` entry, in list order (namespace-scoped)
8. `clusters/{cluster}/namespaces/{ns}/tenants/{id}.yaml` — optional per-tenant override (tenant-scoped, highest)

**Merge semantics (§3 "Merge semantics" table):**
- Scalars/maps: deep-merge, higher layer wins per key.
- Named lists (e.g. `members`, module `extraEnvVars`): **wholesale replace** at the level that states them — no implicit concatenation.
- `applications.exclude`: **UNION** across layer 4 (type-default) + layer 6 (namespace) + layer 8 (tenant). Accumulates only; a lower layer never un-excludes. (B.3)
- `configExtensions`: each entry pulls its overlay (layer 7); overlays merge in list order, later overrides earlier. (B.4)
- Secret `*Ref` strings: pass through untouched, never merged into values.

**Presence-driven overlays (§2.2b, §3, B.5):** `secure-tenant` overlay is applied (without being listed in `configExtensions`) iff any tenant has `secure: true`; `${secureTenantId}` is substituted from that tenant's id. `rtr` overlay is applied iff `features.rtr` is true. Value-substitution only; no business branching.

**Tenant identity (§2.4, B.6):** `type`/`name`/`code`/`adminUser.username` come from `tenant-catalog.yaml` by id; `type` drives the layer-4 default. A referenced id absent from the catalog is a resolution error.

**Dataset (§2.4b, B.7):** when `namespace.dataset.profile` is set, the tenant set + `defaultTenant` + `consortia` + `dbName` + `infra.pgInstanceType` + `moduleReplicas` come from the dataset profile (mutually exclusive with an explicit `tenants[]`). `moduleReplicas.<m>` maps onto `modules.<m>.replicaCount` at resolve time.

**Deployed-app set + cascade (§3, §5.2/§5.3, B.8):** `available = required+optional app NAMES from platform-descriptor.json (for the branch)`. `deployed = available − UNION(excludes)`. The resolver surfaces, per excluded app, its **UI module names** (from the app descriptor's `uiModules`) so the pipeline can later run the UI-module cascade — cascade *execution* is Epic F. No `modules.exclude` config surface is introduced. App descriptors are matched by **name** ignoring version (names-not-versions).

**Gap #5 (§2.1 notes, task brief):** `tenantDefaults.config.kb` applies to a tenant only when `mod-kb-ebsco-java` is present; `tenantDefaults.config.worldcat` only when `mod-copycat` is present. "Present" = the module appears in the union of the tenant's deployed apps' `modules`. (In the reference tree both live in `app-platform-complete`, which is in the descriptor's `required` set, so both apply for sprint.)

**module-roles / rwSplit (§2.3, §6, B.10):** load `platform/module-roles.yaml`. When `features.rwSplit` is true, mark each module named in `readWriteModules` to receive `integrations.db.hostReader` (set the flag `true` — mark only; the reader **coordinate** is injected by the pipeline from TF output at deploy, topology-not-coordinates). When false, no module is flagged.

**Emit (§5.2, §5.4, B.9):** output maps onto `CreateNamespaceParameters` / `EurekaNamespace` / `EurekaTenant` field names. Topology flags (`built-in|aws`) + names present; coordinates and versions deliberately **absent**. Pure function: resolving the same tree twice yields byte-identical output.

**Out of scope (do NOT build):** pipeline/Groovy wiring, deploy actions, Helm rendering, FAR/version resolution, TF coordinate injection, UI-module cascade *execution*, system-user provisioning (all Epic F); the five cross-level validators (Epic D). The resolver may *surface* data those validators need but does not enforce them.

---

## Reference data the tests assert against (verified on disk)

- `platform/defaults.yaml`: `tenantDefaults.config.kb {url: https://sandbox.ebsco.io, customerId: apidvcorp}`, `tenantDefaults.config.worldcat {profileId: f26df83c-...}`, `features.scNative: true`.
- `platform/tenant-catalog.yaml`: `diku` (standard), `university` (consortia-member, code um), `college` (consortia-member, code cl), `consortium` (consortia-central, code cs), `fs09000000` (standard, user folio), `cs00000int` (consortia-central), `cs00000int_0001` (consortia-member).
- `platform/tenant-type-defaults/standard.yaml` exclude: `[app-consortia, app-consortia-manager, app-dcb, app-requests-ecs, app-requests-mediated, app-requests-mediated-ui]`.
- `platform/tenant-type-defaults/consortia-member.yaml` exclude: `[app-requests-mediated-ui, app-consortia-manager, app-linked-data]`.
- `platform/tenant-type-defaults/consortia-central.yaml` exclude: `[]`.
- `platform/module-roles.yaml` `readWriteModules`: `[mod-audit, mod-authtoken, mod-circulation-storage, mod-data-import, mod-di-converter-storage, mod-inventory-storage, mod-source-record-storage, mod-users]`.
- `clusters/folio-etesting/namespaces/sprint/namespace.yaml`: `configType: testing`, `tenants: [diku, university, college]`, `defaultTenant: diku`, `configExtensions: [sunflower, consortia-single-ui]`, `applications.exclude: []`, `features.rwSplit: false`, `consortia: [{central: consortium, name: Consortium, members: [university, college]}]`.
- `clusters/folio-etesting/namespaces/sprint/tenants/university.yaml`: `secure: true`, `applications.exclude: [app-fqm]`, `install.loadSample: false`, `config.kb.apiKeyRef`, `config.smtp`, `config.ldp`, `ui.*`.
- `clusters/folio-etesting/namespaces/bugfest/namespace.yaml`: `dataset: {snapshot: bugfest-2025-r1-snapshot, profile: bugfest}`, NO `tenants[]`, `configType: performance`.
- `platform/dataset-profiles/bugfest.yaml`: `defaultTenant: fs09000000`, `tenants: [fs09000000, fs09000002, fs09000003, cs00000int, cs00000int_0001]`, `dbName: folio`, `infra.pgInstanceType: db.r6g.xlarge`, `moduleReplicas: {mod-inventory-storage: 4, mod-search: 4}`, `consortia: [{central: cs00000int, name: Consortium, members: [cs00000int_0001]}]`.
- `platform-lsp/platform-descriptor.json`: `applications.required` = `[app-platform-minimal, app-platform-complete]`; `applications.optional` includes `app-consortia, app-dcb, app-fqm, app-linked-data, app-consortia-manager, ...` (each `{name, version}`).
- `platform-lsp/local-dev/appDescriptors/*.json`: each has `modules` and `uiModules` lists of `{name, version, id}`. `app-platform-complete-3.3.0.json` contains both `mod-kb-ebsco-java` and `mod-copycat`.

**Resolver-input data sources (injected, descriptor stand-in):**
- Available app names: `platform-lsp/platform-descriptor.json` → names of `applications.required` + `applications.optional`.
- App→modules/uiModules index: `platform-lsp/local-dev/appDescriptors/<app-name>-<version>.json` matched by name prefix.

> **Baseline to protect:** `./.venv/bin/python scripts/validate_config.py` currently prints `23/23 files valid.` (exit 0). The resolver must not add any YAML under `platform/` or `clusters/`, so this stays 23/23.

---

## File Structure

All paths are relative to `kitfox-config/`.

| File | Responsibility |
|------|----------------|
| `resolver/__init__.py` | Package marker; re-export `resolve_namespace`, model classes. |
| `resolver/loader.py` | B.1 — discovery (`readdir`) + YAML loading of all layer + reference files into a `ConfigTree`. |
| `resolver/merge.py` | B.2 — `deep_merge` (dict deep-merge, list wholesale-replace). |
| `resolver/excludes.py` | B.3 — `union_excludes` accumulator. |
| `resolver/apps.py` | B.8 + Gap #5 — `AppIndex` loader, available/deployed sets, excluded-app UI modules, module-presence. |
| `resolver/tenants.py` | B.6/B.7 — per-tenant resolution (catalog → type-default → override), dataset membership. |
| `resolver/overlays.py` | B.4/B.5 — configExtensions merge, presence-driven selection, `${var}` substitution. |
| `resolver/roles.py` | B.10 — rwSplit reader-endpoint marking from module-roles. |
| `resolver/model.py` | B.9 — `ResolvedNamespace`/`ResolvedTenant` dataclasses + `to_dict`. |
| `resolver/resolve.py` | B.9 — orchestration `resolve_namespace(...)` + deterministic `emit_json`. |
| `scripts/resolve.py` | CLI wrapper around `resolve.resolve_namespace`. |
| `tests/conftest.py` | Shared paths + fixtures (config root, app index, tiny in-memory trees). |
| `tests/test_merge.py` | B.2 unit tests (deep-merge, wholesale-replace). |
| `tests/test_excludes.py` | B.3 unit tests (UNION; cannot un-exclude). |
| `tests/test_apps.py` | B.8/Gap#5 unit tests (deployed subtraction, UI cascade, presence). |
| `tests/test_overlays.py` | B.4/B.5 unit tests (list-order merge, presence-driven, substitution). |
| `tests/test_tenants.py` | B.6/B.7 unit tests (identity, type-default, dataset, missing-id error). |
| `tests/test_roles.py` | B.10 unit tests (mark iff rwSplit). |
| `tests/test_resolve_sprint.py` | E2E asserts for `folio-etesting/sprint`. |
| `tests/test_resolve_bugfest.py` | E2E asserts for `folio-etesting/bugfest`. |
| `tests/test_determinism.py` | Resolving twice → byte-identical. |
| `requirements-dev.txt` | `pytest>=8`. |

---

### Task 0: Scaffolding — package, test runner, fixtures

**Files:**
- Create: `resolver/__init__.py`
- Create: `requirements-dev.txt`
- Create: `tests/conftest.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create the package marker**

`resolver/__init__.py`:

```python
"""kitfox-config reference resolver (Epic B).

Pure function of the config tree: resolve_namespace(tree, cluster, namespace)
deep-merges the 8 precedence layers (§3) and emits the resolved namespace +
per-tenant model (§5.2). Versions/coordinates are deliberately absent.
"""

from resolver.model import ResolvedNamespace, ResolvedTenant
from resolver.resolve import resolve_namespace, emit_json

__all__ = ["ResolvedNamespace", "ResolvedTenant", "resolve_namespace", "emit_json"]
```

> Note: this import line will fail until `model.py`/`resolve.py` exist (Tasks 4–8). That is expected; do not run anything that imports the package top-level until Task 8. Unit tests in Tasks 1–7 import submodules directly (e.g. `from resolver.merge import deep_merge`), which is fine.

- [ ] **Step 2: Add the dev requirement and install pytest**

`requirements-dev.txt`:

```
pytest>=8
```

Run: `cd kitfox-config && ./.venv/bin/python -m pip install -r requirements-dev.txt`
Expected: pytest installs successfully (no other deps needed).

- [ ] **Step 3: Create the test package marker**

`tests/__init__.py`:

```python
```

(empty file)

- [ ] **Step 4: Create shared fixtures**

`tests/conftest.py`:

```python
"""Shared test fixtures. CONFIG_ROOT is the kitfox-config repo; PLATFORM_LSP is
the sibling descriptor source. Both are located WITHOUT resolving symlinks so the
workspace symlinks (kitfox-config, platform-lsp) are followed correctly."""

from pathlib import Path

import pytest

# tests/conftest.py -> parents[1] = kitfox-config, parents[2] = workspace root.
CONFIG_ROOT = Path(__file__).parents[1]
WORKSPACE = Path(__file__).parents[2]
PLATFORM_LSP = WORKSPACE / "platform-lsp"
PLATFORM_DESCRIPTOR = PLATFORM_LSP / "platform-descriptor.json"
APP_DESCRIPTORS = PLATFORM_LSP / "local-dev" / "appDescriptors"


@pytest.fixture
def config_root() -> Path:
    return CONFIG_ROOT


@pytest.fixture
def platform_descriptor() -> Path:
    return PLATFORM_DESCRIPTOR


@pytest.fixture
def app_descriptors_dir() -> Path:
    return APP_DESCRIPTORS
```

- [ ] **Step 5: Verify pytest collects an empty suite**

Run: `cd kitfox-config && ./.venv/bin/python -m pytest tests/ -q`
Expected: `no tests ran` (exit code 5) — collection works, conftest imports cleanly.

- [ ] **Step 6: Commit**

```bash
cd kitfox-config && git add resolver/__init__.py requirements-dev.txt tests/__init__.py tests/conftest.py && git commit -m "chore(resolver): scaffold Epic B package, pytest, fixtures"
```

---

### Task 1: Discovery + layer loading (Story B.1)

**Files:**
- Create: `resolver/loader.py`
- Test: covered indirectly by later e2e tasks; add a focused test in `tests/test_tenants.py` (Task 4). No standalone test file for the loader to avoid duplication — its behavior is asserted via `load_tree` in e2e.

Implements §5.1: clusters = `readdir clusters/`; namespaces = `readdir clusters/{c}/namespaces/`; tenant membership comes from `namespace.tenants[]` or `dataset.profile` (never `readdir tenants/`). Also loads the non-merge reference files (`module-roles.yaml`, `tenant-type-ruleset.yaml`) so downstream consumers have them (readiness gap #1).

- [ ] **Step 1: Write `loader.py`**

```python
"""B.1 — discovery + layer loading. The directory tree IS the deployment
hierarchy (§5.1); discovery is readdir, not parsing."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


@dataclass
class ConfigTree:
    """All on-disk layers loaded once. Tenant-override files are loaded lazily by
    id via tenant_override(). Reference (non-merge) files are loaded eagerly."""

    root: Path
    defaults: dict[str, Any]
    deployment_profiles: dict[str, dict[str, Any]]   # configType -> profile
    catalog: dict[str, Any]                           # tenant id -> identity
    type_defaults: dict[str, dict[str, Any]]          # type -> file
    feature_overlays: dict[str, dict[str, Any]]       # name -> overlay
    dataset_profiles: dict[str, dict[str, Any]]       # name -> profile
    module_roles: dict[str, Any]
    tenant_ruleset: dict[str, Any]
    _cluster_dir: Path = field(default=None)

    def cluster(self, cluster: str) -> dict[str, Any]:
        return _load_yaml(self.root / "clusters" / cluster / "cluster.yaml")

    def namespace(self, cluster: str, namespace: str) -> dict[str, Any]:
        return _load_yaml(
            self.root / "clusters" / cluster / "namespaces" / namespace / "namespace.yaml"
        )

    def tenant_override(self, cluster: str, namespace: str, tenant_id: str) -> dict[str, Any]:
        return _load_yaml(
            self.root / "clusters" / cluster / "namespaces" / namespace
            / "tenants" / f"{tenant_id}.yaml"
        )

    def list_clusters(self) -> list[str]:
        base = self.root / "clusters"
        return sorted(p.name for p in base.iterdir() if p.is_dir()) if base.exists() else []

    def list_namespaces(self, cluster: str) -> list[str]:
        base = self.root / "clusters" / cluster / "namespaces"
        return sorted(p.name for p in base.iterdir() if p.is_dir()) if base.exists() else []


def _load_dir(directory: Path, key: str) -> dict[str, dict[str, Any]]:
    """Load every *.yaml in a dir into {selectorValue: doc}, keyed by doc[key]
    (falling back to the filename stem)."""
    out: dict[str, dict[str, Any]] = {}
    if not directory.exists():
        return out
    for f in sorted(directory.glob("*.yaml")):
        doc = _load_yaml(f)
        out[doc.get(key, f.stem)] = doc
    return out


def load_tree(root: Path) -> ConfigTree:
    platform = root / "platform"
    return ConfigTree(
        root=root,
        defaults=_load_yaml(platform / "defaults.yaml"),
        deployment_profiles=_load_dir(platform / "deployment-profiles", "configType"),
        catalog=_load_yaml(platform / "tenant-catalog.yaml").get("tenants", {}),
        type_defaults=_load_dir(platform / "tenant-type-defaults", "type"),
        feature_overlays=_load_dir(platform / "feature-overlays", "name"),
        dataset_profiles=_load_dir(platform / "dataset-profiles", "name"),
        module_roles=_load_yaml(platform / "module-roles.yaml"),
        tenant_ruleset=_load_yaml(platform / "tenant-type-ruleset.yaml"),
    )
```

- [ ] **Step 2: Write a smoke test for discovery**

Add to a new `tests/test_loader.py`:

```python
from resolver.loader import load_tree


def test_load_tree_discovers_hierarchy(config_root):
    tree = load_tree(config_root)
    assert "folio-etesting" in tree.list_clusters()
    assert set(tree.list_namespaces("folio-etesting")) >= {"sprint", "bugfest"}
    # tenant membership comes from namespace.tenants, not readdir
    ns = tree.namespace("folio-etesting", "sprint")
    assert ns["tenants"] == ["diku", "university", "college"]
    # catalog identity keyed by id
    assert tree.catalog["university"]["type"] == "consortia-member"
    # reference (non-merge) files loaded
    assert "readWriteModules" in tree.module_roles
    assert "rules" in tree.tenant_ruleset
    # type-defaults keyed by type
    assert "app-consortia" in tree.type_defaults["standard"]["applications"]["exclude"]
```

- [ ] **Step 3: Run it**

Run: `cd kitfox-config && ./.venv/bin/python -m pytest tests/test_loader.py -q`
Expected: 1 passed.

- [ ] **Step 4: Commit**

```bash
cd kitfox-config && git add resolver/loader.py tests/test_loader.py && git commit -m "feat(resolver): discovery + layer loading (B.1)"
```

---

### Task 2: Deep-merge with named-list wholesale-replace (Story B.2)

**Files:**
- Create: `resolver/merge.py`
- Test: `tests/test_merge.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_merge.py`:

```python
from resolver.merge import deep_merge


def test_scalars_and_maps_deep_merge_higher_wins():
    base = {"infra": {"pgType": "built-in", "pgVersion": "16.8"}}
    over = {"infra": {"pgType": "aws"}}
    assert deep_merge(base, over) == {"infra": {"pgType": "aws", "pgVersion": "16.8"}}


def test_named_lists_replace_wholesale_no_concat():
    base = {"members": ["a", "b", "c"]}
    over = {"members": ["x"]}
    assert deep_merge(base, over) == {"members": ["x"]}


def test_merge_does_not_mutate_inputs():
    base = {"a": {"b": 1}}
    over = {"a": {"c": 2}}
    deep_merge(base, over)
    assert base == {"a": {"b": 1}}
    assert over == {"a": {"c": 2}}


def test_new_keys_from_higher_layer_are_added():
    assert deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}
```

- [ ] **Step 2: Run to verify failure**

Run: `cd kitfox-config && ./.venv/bin/python -m pytest tests/test_merge.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'resolver.merge'`.

- [ ] **Step 3: Implement `merge.py`**

```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `cd kitfox-config && ./.venv/bin/python -m pytest tests/test_merge.py -q`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd kitfox-config && git add resolver/merge.py tests/test_merge.py && git commit -m "feat(resolver): deep-merge with named-list wholesale-replace (B.2)"
```

---

### Task 3: `applications.exclude` UNION (Story B.3)

**Files:**
- Create: `resolver/excludes.py`
- Test: `tests/test_excludes.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_excludes.py`:

```python
from resolver.excludes import union_excludes


def test_union_accumulates_across_layers():
    type_default = ["app-consortia", "app-dcb"]
    namespace = ["app-reading-room"]
    tenant = ["app-fqm"]
    assert union_excludes(type_default, namespace, tenant) == sorted(
        {"app-consortia", "app-dcb", "app-reading-room", "app-fqm"}
    )


def test_union_is_deduplicated_and_sorted():
    assert union_excludes(["b", "a"], ["a"], ["b"]) == ["a", "b"]


def test_tenant_omission_cannot_unexclude_type_default():
    # tenant override does not list app-consortia; the union still excludes it.
    resolved = union_excludes(["app-consortia"], [], [])
    assert "app-consortia" in resolved


def test_none_layers_treated_as_empty():
    assert union_excludes(None, ["a"], None) == ["a"]
```

- [ ] **Step 2: Run to verify failure**

Run: `cd kitfox-config && ./.venv/bin/python -m pytest tests/test_excludes.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `excludes.py`**

```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `cd kitfox-config && ./.venv/bin/python -m pytest tests/test_excludes.py -q`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd kitfox-config && git add resolver/excludes.py tests/test_excludes.py && git commit -m "feat(resolver): applications.exclude UNION (B.3)"
```

---

### Task 4: App index — available set, deployed subtraction, UI cascade, presence (Story B.8 + Gap #5)

**Files:**
- Create: `resolver/apps.py`
- Test: `tests/test_apps.py`

This is built before tenant resolution because tenant resolution (Task 5) consumes `AppIndex` for the deployed set, UI-cascade inputs, and Gap #5 module-presence.

- [ ] **Step 1: Write the failing tests**

`tests/test_apps.py`:

```python
from resolver.apps import AppIndex


def test_available_names_from_descriptor(platform_descriptor, app_descriptors_dir):
    idx = AppIndex.load(platform_descriptor, app_descriptors_dir)
    # required + optional names, versions ignored
    assert "app-platform-complete" in idx.available
    assert "app-fqm" in idx.available
    assert "app-consortia" in idx.available


def test_deployed_is_available_minus_excludes(platform_descriptor, app_descriptors_dir):
    idx = AppIndex.load(platform_descriptor, app_descriptors_dir)
    deployed = idx.deployed(exclude=["app-fqm", "app-consortia"])
    assert "app-fqm" not in deployed
    assert "app-consortia" not in deployed
    assert "app-platform-complete" in deployed
    assert deployed == sorted(deployed)  # deterministic order


def test_ui_modules_for_excluded_apps(platform_descriptor, app_descriptors_dir):
    idx = AppIndex.load(platform_descriptor, app_descriptors_dir)
    cascade = idx.excluded_ui_modules(["app-consortia"])
    # app-consortia is matched by name in appDescriptors; its uiModules surface
    assert "app-consortia" in cascade
    assert isinstance(cascade["app-consortia"], list)


def test_module_present_in_deployed_apps(platform_descriptor, app_descriptors_dir):
    idx = AppIndex.load(platform_descriptor, app_descriptors_dir)
    # app-platform-complete is in the descriptor required set and carries both modules
    present = idx.modules_of(["app-platform-complete"])
    assert "mod-kb-ebsco-java" in present
    assert "mod-copycat" in present


def test_missing_app_descriptor_is_tolerated(platform_descriptor, app_descriptors_dir):
    idx = AppIndex.load(platform_descriptor, app_descriptors_dir)
    # an app with no descriptor file contributes no modules/uiModules, no crash
    assert idx.excluded_ui_modules(["app-does-not-exist"]) == {"app-does-not-exist": []}
    assert idx.modules_of(["app-does-not-exist"]) == set()
```

- [ ] **Step 2: Run to verify failure**

Run: `cd kitfox-config && ./.venv/bin/python -m pytest tests/test_apps.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `apps.py`**

```python
"""B.8 + Gap #5 — descriptor-derived app data (injected input, FAR stand-in).

available  = required+optional NAMES from platform-descriptor.json (versions ignored).
deployed   = available − unioned excludes.
UI cascade = per excluded app, its uiModules names (for the pipeline's cascade, Epic F).
presence   = modules of a set of apps (Gap #5 gating of config.kb / config.worldcat).

App descriptors are matched by NAME, ignoring version (names-not-versions, §0)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppIndex:
    available: list[str]
    _modules: dict[str, list[str]]     # app name -> backend module names
    _ui_modules: dict[str, list[str]]  # app name -> UI module names

    @classmethod
    def load(cls, platform_descriptor: Path, app_descriptors_dir: Path) -> "AppIndex":
        desc = json.loads(Path(platform_descriptor).read_text())
        apps = desc.get("applications", {})
        names = [a["name"] for a in apps.get("required", [])] + [
            a["name"] for a in apps.get("optional", [])
        ]
        available = sorted(set(names))

        modules: dict[str, list[str]] = {}
        ui_modules: dict[str, list[str]] = {}
        ddir = Path(app_descriptors_dir)
        if ddir.exists():
            for f in sorted(ddir.glob("*.json")):
                doc = json.loads(f.read_text())
                app_name = doc.get("name")
                if not app_name:
                    continue
                modules[app_name] = sorted(m["name"] for m in doc.get("modules", []))
                ui_modules[app_name] = sorted(m["name"] for m in doc.get("uiModules", []))
        return cls(available=available, _modules=modules, _ui_modules=ui_modules)

    def deployed(self, exclude: list[str]) -> list[str]:
        excluded = set(exclude or [])
        return sorted(a for a in self.available if a not in excluded)

    def excluded_ui_modules(self, excluded_apps: list[str]) -> dict[str, list[str]]:
        return {app: self._ui_modules.get(app, []) for app in (excluded_apps or [])}

    def modules_of(self, apps: list[str]) -> set[str]:
        present: set[str] = set()
        for app in apps or []:
            present.update(self._modules.get(app, []))
        return present
```

- [ ] **Step 4: Run to verify pass**

Run: `cd kitfox-config && ./.venv/bin/python -m pytest tests/test_apps.py -q`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
cd kitfox-config && git add resolver/apps.py tests/test_apps.py && git commit -m "feat(resolver): app index — deployed set, UI cascade, module presence (B.8, Gap #5)"
```

---

### Task 5: Tenant resolution — identity, type-default, dataset, Gap #5 config gating (Stories B.6, B.7)

**Files:**
- Create: `resolver/tenants.py`
- Test: `tests/test_tenants.py`

Per tenant, the resolved config is built in precedence order using tenant-shaped layers: (1) `tenantDefaults` base → (3) catalog identity → (4) type-default exclude → (6 namespace + 8 tenant) override + exclude UNION. Gap #5 trims `config.kb`/`config.worldcat` by module presence.

- [ ] **Step 1: Write the failing tests**

`tests/test_tenants.py`:

```python
import pytest

from resolver.apps import AppIndex
from resolver.loader import load_tree
from resolver.tenants import resolve_tenant, tenant_membership


def _idx(platform_descriptor, app_descriptors_dir):
    return AppIndex.load(platform_descriptor, app_descriptors_dir)


def test_identity_from_catalog(config_root):
    tree = load_tree(config_root)
    t = resolve_tenant(tree, "folio-etesting", "sprint", "diku",
                       namespace_exclude=[], app_index=None)
    assert t["type"] == "standard"
    assert t["name"] == "Datalogisk Institut"
    assert t["adminUser"]["username"] == "diku_admin"


def test_type_default_exclude_applied(config_root):
    tree = load_tree(config_root)
    t = resolve_tenant(tree, "folio-etesting", "sprint", "diku",
                       namespace_exclude=[], app_index=None)
    # standard type default exclusions present
    assert "app-consortia" in t["applications"]["exclude"]
    assert "app-requests-mediated-ui" in t["applications"]["exclude"]


def test_override_unions_exclude_and_sets_secure(config_root):
    tree = load_tree(config_root)
    t = resolve_tenant(tree, "folio-etesting", "sprint", "university",
                       namespace_exclude=[], app_index=None)
    assert t["secure"] is True
    # consortia-member type defaults UNION the tenant override (app-fqm)
    assert "app-fqm" in t["applications"]["exclude"]
    assert "app-consortia-manager" in t["applications"]["exclude"]   # from type default
    assert "app-linked-data" in t["applications"]["exclude"]         # from type default


def test_install_defaults_merge_with_override(config_root):
    tree = load_tree(config_root)
    t = resolve_tenant(tree, "folio-etesting", "sprint", "university",
                       namespace_exclude=[], app_index=None)
    assert t["install"]["loadSample"] is False          # override
    assert t["install"]["loadReference"] is True        # inherited default
    assert t["install"]["async"] is True                # inherited default


def test_code_present_for_member(config_root):
    tree = load_tree(config_root)
    t = resolve_tenant(tree, "folio-etesting", "sprint", "university",
                       namespace_exclude=[], app_index=None)
    assert t["code"] == "um"


def test_unknown_id_raises(config_root):
    tree = load_tree(config_root)
    with pytest.raises(KeyError):
        resolve_tenant(tree, "folio-etesting", "sprint", "ghost",
                       namespace_exclude=[], app_index=None)


def test_membership_explicit(config_root):
    tree = load_tree(config_root)
    m = tenant_membership(tree, "folio-etesting", "sprint")
    assert m.tenant_ids == ["diku", "university", "college"]
    assert m.default_tenant == "diku"
    assert m.dataset is None


def test_membership_from_dataset(config_root):
    tree = load_tree(config_root)
    m = tenant_membership(tree, "folio-etesting", "bugfest")
    assert m.tenant_ids == ["fs09000000", "fs09000002", "fs09000003",
                            "cs00000int", "cs00000int_0001"]
    assert m.default_tenant == "fs09000000"
    assert m.dataset["dbName"] == "folio"
    assert m.dataset["infra"]["pgInstanceType"] == "db.r6g.xlarge"
    assert m.dataset["moduleReplicas"]["mod-search"] == 4


def test_gap5_keeps_config_when_module_present(config_root, platform_descriptor,
                                               app_descriptors_dir):
    tree = load_tree(config_root)
    idx = _idx(platform_descriptor, app_descriptors_dir)
    t = resolve_tenant(tree, "folio-etesting", "sprint", "diku",
                       namespace_exclude=[], app_index=idx)
    # app-platform-complete (required) carries mod-kb-ebsco-java + mod-copycat
    assert "kb" in t["config"]
    assert "worldcat" in t["config"]


def test_gap5_drops_config_when_module_absent(config_root, platform_descriptor,
                                              app_descriptors_dir):
    tree = load_tree(config_root)
    idx = _idx(platform_descriptor, app_descriptors_dir)
    # Exclude every app that carries the modules → kb/worldcat must drop.
    kb_apps = [a for a in idx.available if "mod-kb-ebsco-java" in idx.modules_of([a])]
    wc_apps = [a for a in idx.available if "mod-copycat" in idx.modules_of([a])]
    t = resolve_tenant(tree, "folio-etesting", "sprint", "diku",
                       namespace_exclude=sorted(set(kb_apps + wc_apps)), app_index=idx)
    assert "kb" not in t["config"]
    assert "worldcat" not in t["config"]
```

- [ ] **Step 2: Run to verify failure**

Run: `cd kitfox-config && ./.venv/bin/python -m pytest tests/test_tenants.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `tenants.py`**

```python
"""B.6/B.7 — tenant resolution.

Per tenant (tenant-scoped layers, in precedence order §3):
  1 tenantDefaults (type/secure/install/config base)
  3 tenant-catalog[id] (type/name/code/adminUser identity)
  4 tenant-type-defaults[type].applications.exclude  -> UNION
  6 namespace.applications.exclude                    -> UNION
  8 tenants/{id}.yaml override (secure/install/config/index/ui + exclude UNION)

Gap #5: config.kb kept only when mod-kb-ebsco-java is present in the tenant's
deployed apps; config.worldcat only when mod-copycat is present."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from resolver.apps import AppIndex
from resolver.excludes import union_excludes
from resolver.loader import ConfigTree
from resolver.merge import deep_merge

KB_MODULE = "mod-kb-ebsco-java"
WORLDCAT_MODULE = "mod-copycat"


@dataclass
class Membership:
    tenant_ids: list[str]
    default_tenant: str
    consortia: list[dict[str, Any]]
    dataset: dict[str, Any] | None   # the resolved dataset profile, or None


def tenant_membership(tree: ConfigTree, cluster: str, namespace: str) -> Membership:
    ns = tree.namespace(cluster, namespace)
    dataset_ref = ns.get("dataset")
    if dataset_ref and dataset_ref.get("profile"):
        profile = tree.dataset_profiles[dataset_ref["profile"]]
        return Membership(
            tenant_ids=list(profile.get("tenants", [])),
            default_tenant=profile.get("defaultTenant"),
            consortia=profile.get("consortia", []),
            dataset={
                "snapshot": dataset_ref.get("snapshot"),
                "profile": dataset_ref["profile"],
                "dbName": profile.get("dbName"),
                "infra": profile.get("infra", {}),
                "moduleReplicas": profile.get("moduleReplicas", {}),
            },
        )
    return Membership(
        tenant_ids=list(ns.get("tenants", [])),
        default_tenant=ns.get("defaultTenant"),
        consortia=ns.get("consortia", []),
        dataset=None,
    )


def resolve_tenant(
    tree: ConfigTree,
    cluster: str,
    namespace: str,
    tenant_id: str,
    namespace_exclude: list[str],
    app_index: AppIndex | None,
) -> dict[str, Any]:
    if tenant_id not in tree.catalog:
        raise KeyError(f"tenant id '{tenant_id}' not in tenant-catalog.yaml")

    defaults = tree.defaults.get("tenantDefaults", {})
    identity = tree.catalog[tenant_id]
    override = tree.tenant_override(cluster, namespace, tenant_id)

    # Base from tenantDefaults (type/secure/install/config).
    tenant: dict[str, Any] = copy.deepcopy({
        "type": defaults.get("type"),
        "secure": defaults.get("secure", False),
        "install": defaults.get("install", {}),
        "config": defaults.get("config", {}),
    })

    # Layer 3 — catalog identity (type from catalog wins).
    tenant["tenantId"] = tenant_id
    tenant["type"] = identity.get("type", tenant["type"])
    tenant["name"] = identity.get("name")
    if "code" in identity:
        tenant["code"] = identity["code"]
    tenant["adminUser"] = copy.deepcopy(identity.get("adminUser", {}))

    # Layer 8 — override (merge install/config; set secure; carry index/ui; adminUser.passwordRef).
    if override:
        if "secure" in override:
            tenant["secure"] = override["secure"]
        if "install" in override:
            tenant["install"] = deep_merge(tenant["install"], override["install"])
        if "config" in override:
            tenant["config"] = deep_merge(tenant["config"], override["config"])
        if "index" in override:
            tenant["index"] = copy.deepcopy(override["index"])
        if "ui" in override:
            tenant["ui"] = copy.deepcopy(override["ui"])
        if "adminUser" in override:
            tenant["adminUser"] = deep_merge(tenant["adminUser"], override["adminUser"])

    # applications.exclude UNION (layers 4 + 6 + 8).
    type_default_exclude = (
        tree.type_defaults.get(tenant["type"], {})
        .get("applications", {})
        .get("exclude", [])
    )
    tenant_exclude = (override.get("applications", {}) or {}).get("exclude", [])
    excluded = union_excludes(type_default_exclude, namespace_exclude, tenant_exclude)
    tenant["applications"] = {"exclude": excluded}

    # Deployed set + UI cascade inputs (B.8) and Gap #5 gating, when an index is given.
    if app_index is not None:
        deployed = app_index.deployed(excluded)
        tenant["deployedApps"] = deployed
        tenant["excludedAppsUiModules"] = app_index.excluded_ui_modules(excluded)
        present = app_index.modules_of(deployed)
        if KB_MODULE not in present:
            tenant["config"].pop("kb", None)
        if WORLDCAT_MODULE not in present:
            tenant["config"].pop("worldcat", None)

    return tenant
```

- [ ] **Step 4: Run to verify pass**

Run: `cd kitfox-config && ./.venv/bin/python -m pytest tests/test_tenants.py -q`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
cd kitfox-config && git add resolver/tenants.py tests/test_tenants.py && git commit -m "feat(resolver): tenant identity, type-default, dataset, Gap #5 gating (B.6, B.7)"
```

---

### Task 6: Feature overlays — configExtensions, presence-driven, substitution (Stories B.4, B.5)

**Files:**
- Create: `resolver/overlays.py`
- Test: `tests/test_overlays.py`

Overlays are namespace-scoped (layer 7). They contribute `modules` and `ui`. A generic loop merges each `configExtensions` entry in list order, then presence-driven overlays (`secure-tenant` iff any tenant secure; `rtr` iff `features.rtr`), then `${secureTenantId}` substitution. NO per-feature `if` branches.

- [ ] **Step 1: Write the failing tests**

`tests/test_overlays.py`:

```python
from resolver.overlays import apply_overlays, substitute


def test_substitute_replaces_placeholders_only():
    data = {"modules": {"m": {"extraEnvVars": [{"name": "X", "value": "${secureTenantId}"}]}}}
    out = substitute(data, {"secureTenantId": "university"})
    assert out["modules"]["m"]["extraEnvVars"][0]["value"] == "university"


def test_substitute_leaves_unknown_text_untouched():
    assert substitute({"a": "plain"}, {"secureTenantId": "u"}) == {"a": "plain"}


def test_configextensions_merge_in_list_order():
    overlays = {
        "first":  {"name": "first",  "ui": {"flag": "a"}},
        "second": {"name": "second", "ui": {"flag": "b"}},
    }
    base = {"ui": {}}
    out = apply_overlays(
        base, config_extensions=["first", "second"], overlays=overlays,
        any_secure=False, secure_tenant_id=None, rtr=False,
    )
    assert out["ui"]["flag"] == "b"   # later wins


def test_presence_driven_secure_tenant_applied_and_substituted():
    overlays = {
        "secure-tenant": {
            "name": "secure-tenant",
            "modules": {
                "mod-patron": {"extraEnvVars": [{"name": "SECURE_TENANT_ID",
                                                 "value": "${secureTenantId}"}]}
            },
        }
    }
    out = apply_overlays(
        {}, config_extensions=[], overlays=overlays,
        any_secure=True, secure_tenant_id="university", rtr=False,
    )
    ev = out["modules"]["mod-patron"]["extraEnvVars"][0]
    assert ev["value"] == "university"


def test_secure_tenant_not_applied_when_no_secure_tenant():
    overlays = {"secure-tenant": {"name": "secure-tenant", "modules": {"m": {}}}}
    out = apply_overlays({}, config_extensions=[], overlays=overlays,
                         any_secure=False, secure_tenant_id=None, rtr=False)
    assert "modules" not in out or "m" not in out.get("modules", {})


def test_rtr_overlay_applied_by_flag():
    overlays = {"rtr": {"name": "rtr",
                        "modules": {"mod-authtoken": {"extraEnvVars": [
                            {"name": "LEGACY_TOKEN_TENANTS", "value": ""}]}}}}
    out = apply_overlays({}, config_extensions=[], overlays=overlays,
                         any_secure=False, secure_tenant_id=None, rtr=True)
    assert "mod-authtoken" in out["modules"]
```

- [ ] **Step 2: Run to verify failure**

Run: `cd kitfox-config && ./.venv/bin/python -m pytest tests/test_overlays.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `overlays.py`**

```python
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
```

> **NFR3 note for the implementer/reviewer:** `PRESENCE_SECURE`/`PRESENCE_RTR` are overlay *names* used for selection (which file to merge), not behavioral branches. No code reads a feature and then sets module env — the env mapping lives in the overlay YAML. This satisfies "zero per-feature `if` branches."

- [ ] **Step 4: Run to verify pass**

Run: `cd kitfox-config && ./.venv/bin/python -m pytest tests/test_overlays.py -q`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
cd kitfox-config && git add resolver/overlays.py tests/test_overlays.py && git commit -m "feat(resolver): feature overlays + presence-driven + substitution (B.4, B.5)"
```

---

### Task 7: module-roles — rwSplit reader-endpoint marking (Story B.10)

**Files:**
- Create: `resolver/roles.py`
- Test: `tests/test_roles.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_roles.py`:

```python
from resolver.roles import mark_read_write_modules


def test_marks_modules_when_rwsplit_true():
    modules, marked = mark_read_write_modules(
        base_modules={"mod-users": {"replicaCount": 1}},
        read_write_modules=["mod-users", "mod-audit"],
        rw_split=True,
    )
    assert marked == ["mod-audit", "mod-users"]
    assert modules["mod-users"]["integrations"]["db"]["hostReader"] is True
    assert modules["mod-audit"]["integrations"]["db"]["hostReader"] is True
    # existing per-module config is preserved
    assert modules["mod-users"]["replicaCount"] == 1


def test_no_marking_when_rwsplit_false():
    modules, marked = mark_read_write_modules(
        base_modules={"mod-users": {}},
        read_write_modules=["mod-users"],
        rw_split=False,
    )
    assert marked == []
    assert "integrations" not in modules["mod-users"]


def test_marking_does_not_set_coordinate():
    modules, _ = mark_read_write_modules(
        base_modules={}, read_write_modules=["mod-audit"], rw_split=True,
    )
    db = modules["mod-audit"]["integrations"]["db"]
    assert db == {"hostReader": True}   # flag only; no host/port/url coordinate
```

- [ ] **Step 2: Run to verify failure**

Run: `cd kitfox-config && ./.venv/bin/python -m pytest tests/test_roles.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `roles.py`**

```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `cd kitfox-config && ./.venv/bin/python -m pytest tests/test_roles.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd kitfox-config && git add resolver/roles.py tests/test_roles.py && git commit -m "feat(resolver): rwSplit reader-endpoint marking (B.10)"
```

---

### Task 8: Model + orchestration + deterministic emit (Story B.9)

**Files:**
- Create: `resolver/model.py`
- Create: `resolver/resolve.py`
- Test: `tests/test_determinism.py`

`resolve_namespace` ties everything together: load tree, resolve membership, resolve each tenant (Task 5), build the namespace base by merging namespace-scoped layers (1 defaults.infra/features → 2 profile → 5 cluster → 6 namespace), apply overlays (Task 6) using the resolved secure info, apply rwSplit marking (Task 7), fold in dataset `moduleReplicas`, and emit a `ResolvedNamespace`. `emit_json` produces sorted-key JSON for byte-identical reproducibility.

- [ ] **Step 1: Write `model.py`**

```python
"""B.9 — resolved model objects. Field names map onto CreateNamespaceParameters /
EurekaNamespace / EurekaTenant (§5.2). Topology flags + names present; coordinates
and versions deliberately absent (filled by TF outputs / FAR at deploy)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ResolvedTenant:
    tenantId: str
    type: str
    name: str | None
    secure: bool
    adminUser: dict[str, Any]
    install: dict[str, Any]
    config: dict[str, Any]
    applications: dict[str, Any]                 # {"exclude": [...]}
    code: str | None = None
    index: list[dict[str, Any]] | None = None
    ui: dict[str, Any] | None = None
    deployedApps: list[str] | None = None
    excludedAppsUiModules: dict[str, list[str]] | None = None


@dataclass
class ResolvedNamespace:
    clusterName: str
    namespaceName: str
    platform: str
    configType: str
    platformBranch: str | None
    releaseType: str | None
    lifecycle: dict[str, Any]
    members: list[str]
    infra: dict[str, Any]
    features: dict[str, Any]
    operations: dict[str, Any]
    consortia: list[dict[str, Any]]
    applications: dict[str, Any]                 # namespace-wide {"exclude": [...]}
    modules: dict[str, Any]
    readWriteModules: list[str]
    defaultTenant: str | None
    tenants: list[ResolvedTenant]
    dataset: dict[str, Any] | None = None
    podPlacement: dict[str, Any] | None = None
    ui: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
```

- [ ] **Step 2: Write `resolve.py`**

```python
"""B.9 — orchestration + deterministic emit."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from resolver.apps import AppIndex
from resolver.loader import ConfigTree, load_tree
from resolver.merge import deep_merge
from resolver.model import ResolvedNamespace, ResolvedTenant
from resolver.overlays import apply_overlays
from resolver.roles import mark_read_write_modules
from resolver.tenants import resolve_tenant, tenant_membership


def _namespace_base(tree: ConfigTree, cluster: str, namespace: str) -> dict[str, Any]:
    """Merge namespace-scoped layers 1 (defaults infra/features) → 2 (profile) →
    5 (cluster) → 6 (namespace). tenantDefaults is excluded (tenant-scoped)."""
    ns = tree.namespace(cluster, namespace)
    config_type = ns.get("configType", "development")
    profile = tree.deployment_profiles.get(config_type, {})
    defaults = {k: v for k, v in tree.defaults.items() if k != "tenantDefaults"}
    cluster_doc = tree.cluster(cluster)

    merged = deep_merge(defaults, profile)
    merged = deep_merge(merged, cluster_doc)
    merged = deep_merge(merged, ns)
    return merged, config_type


def resolve_namespace(
    root: Path,
    cluster: str,
    namespace: str,
    app_index: AppIndex | None = None,
) -> ResolvedNamespace:
    tree = load_tree(Path(root))
    merged, config_type = _namespace_base(tree, cluster, namespace)
    membership = tenant_membership(tree, cluster, namespace)
    ns_exclude = (merged.get("applications", {}) or {}).get("exclude", [])

    # Resolve tenants first (need secure info for presence-driven overlays).
    tenants_raw = [
        resolve_tenant(tree, cluster, namespace, tid, ns_exclude, app_index)
        for tid in membership.tenant_ids
    ]
    secure_ids = [t["tenantId"] for t in tenants_raw if t.get("secure")]
    any_secure = bool(secure_ids)
    secure_tenant_id = secure_ids[0] if secure_ids else None

    features = merged.get("features", {})

    # Overlays (layer 7) — namespace-scoped modules/ui.
    overlaid = apply_overlays(
        base={"modules": copy.deepcopy(merged.get("modules", {})),
              "ui": copy.deepcopy(merged.get("ui", {}))},
        config_extensions=merged.get("configExtensions", []),
        overlays=tree.feature_overlays,
        any_secure=any_secure,
        secure_tenant_id=secure_tenant_id,
        rtr=bool(features.get("rtr", False)),
    )
    modules = overlaid.get("modules", {})
    ui = overlaid.get("ui", {})

    # Dataset moduleReplicas -> modules.<m>.replicaCount (§6 §12d).
    dataset = membership.dataset
    if dataset:
        for mod_name, replicas in (dataset.get("moduleReplicas") or {}).items():
            modules.setdefault(mod_name, {})["replicaCount"] = replicas
        # Dataset restore sizing onto infra.
        merged.setdefault("infra", {})
        if dataset.get("infra", {}).get("pgInstanceType"):
            merged["infra"]["pgInstanceType"] = dataset["infra"]["pgInstanceType"]

    # rwSplit marking (B.10).
    modules, rw_marked = mark_read_write_modules(
        base_modules=modules,
        read_write_modules=tree.module_roles.get("readWriteModules", []),
        rw_split=bool(features.get("rwSplit", False)),
    )

    tenants = [
        ResolvedTenant(
            tenantId=t["tenantId"],
            type=t["type"],
            name=t.get("name"),
            secure=t.get("secure", False),
            adminUser=t.get("adminUser", {}),
            install=t.get("install", {}),
            config=t.get("config", {}),
            applications=t.get("applications", {"exclude": []}),
            code=t.get("code"),
            index=t.get("index"),
            ui=t.get("ui"),
            deployedApps=t.get("deployedApps"),
            excludedAppsUiModules=t.get("excludedAppsUiModules"),
        )
        for t in tenants_raw
    ]

    dataset_out = None
    if dataset:
        dataset_out = {
            "snapshot": dataset.get("snapshot"),
            "profile": dataset.get("profile"),
            "dbName": dataset.get("dbName"),
        }

    return ResolvedNamespace(
        clusterName=cluster,
        namespaceName=namespace,
        platform=merged.get("platform"),
        configType=config_type,
        platformBranch=merged.get("platformBranch"),
        releaseType=merged.get("releaseType"),
        lifecycle=merged.get("lifecycle", {}),
        members=merged.get("members", []),
        infra=merged.get("infra", {}),
        features=features,
        operations=merged.get("operations", {}),
        consortia=membership.consortia,
        applications={"exclude": sorted(ns_exclude)},
        modules=modules,
        readWriteModules=rw_marked,
        defaultTenant=membership.default_tenant,
        tenants=tenants,
        dataset=dataset_out,
        podPlacement=merged.get("podPlacement"),
        ui=ui,
    )


def emit_json(resolved: ResolvedNamespace) -> str:
    """Deterministic serialization: sorted keys → byte-identical across runs (§3)."""
    return json.dumps(resolved.to_dict(), sort_keys=True, indent=2, ensure_ascii=False)
```

- [ ] **Step 3: Write the determinism + smoke test**

`tests/test_determinism.py`:

```python
from resolver import emit_json, resolve_namespace
from resolver.apps import AppIndex


def test_resolving_twice_is_byte_identical(config_root, platform_descriptor,
                                           app_descriptors_dir):
    idx = AppIndex.load(platform_descriptor, app_descriptors_dir)
    a = emit_json(resolve_namespace(config_root, "folio-etesting", "sprint", idx))
    b = emit_json(resolve_namespace(config_root, "folio-etesting", "sprint", idx))
    assert a == b


def test_top_level_import_works():
    # resolver/__init__.py re-exports must import cleanly now that model/resolve exist
    from resolver import ResolvedNamespace, ResolvedTenant  # noqa: F401
```

- [ ] **Step 4: Run to verify pass**

Run: `cd kitfox-config && ./.venv/bin/python -m pytest tests/test_determinism.py -q`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
cd kitfox-config && git add resolver/model.py resolver/resolve.py tests/test_determinism.py && git commit -m "feat(resolver): model + orchestration + deterministic emit (B.9)"
```

---

### Task 9: CLI wrapper

**Files:**
- Create: `scripts/resolve.py`

- [ ] **Step 1: Write `scripts/resolve.py`**

```python
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
```

- [ ] **Step 2: Run the CLI on the sprint namespace**

Run: `cd kitfox-config && ./.venv/bin/python scripts/resolve.py folio-etesting sprint | ./.venv/bin/python -c "import sys,json; d=json.load(sys.stdin); print('tenants', [t['tenantId'] for t in d['tenants']]); print('defaultTenant', d['defaultTenant'])"`
Expected: `tenants ['diku', 'university', 'college']` and `defaultTenant diku`.

- [ ] **Step 3: Commit**

```bash
cd kitfox-config && git add scripts/resolve.py && git commit -m "feat(resolver): CLI wrapper scripts/resolve.py"
```

---

### Task 10: End-to-end verification tests + no-regression gate (VERIFICATION)

**Files:**
- Create: `tests/test_resolve_sprint.py`
- Create: `tests/test_resolve_bugfest.py`

These encode the task's required assertions and the no-regression check.

- [ ] **Step 1: Write the sprint e2e test**

`tests/test_resolve_sprint.py`:

```python
"""E2E: folio-etesting/sprint (§3 resolution end-to-end).
Asserts: tenant set; university deployed apps exclude app-fqm + consortia-member
type-default exclusions; secure-tenant overlay applied iff a tenant is secure;
defaultTenant = diku."""

import pytest

from resolver import resolve_namespace
from resolver.apps import AppIndex


@pytest.fixture
def sprint(config_root, platform_descriptor, app_descriptors_dir):
    idx = AppIndex.load(platform_descriptor, app_descriptors_dir)
    return resolve_namespace(config_root, "folio-etesting", "sprint", idx)


def _tenant(resolved, tid):
    return next(t for t in resolved.tenants if t.tenantId == tid)


def test_tenant_set_and_default(sprint):
    assert [t.tenantId for t in sprint.tenants] == ["diku", "university", "college"]
    assert sprint.defaultTenant == "diku"


def test_university_excludes_fqm_and_type_defaults(sprint):
    uni = _tenant(sprint, "university")
    excl = uni.applications["exclude"]
    assert "app-fqm" in excl                       # tenant override
    assert "app-consortia-manager" in excl         # consortia-member type default
    assert "app-linked-data" in excl               # consortia-member type default
    assert "app-requests-mediated-ui" in excl      # consortia-member type default
    # deployed set excludes them
    assert "app-fqm" not in uni.deployedApps
    assert "app-consortia-manager" not in uni.deployedApps


def test_secure_tenant_overlay_applied_when_secure_present(sprint):
    # university is secure -> SECURE_TENANT_ID lands, substituted to 'university'
    env = sprint.modules["mod-patron"]["extraEnvVars"]
    val = next(e["value"] for e in env if e["name"] == "SECURE_TENANT_ID")
    assert val == "university"


def test_secure_tenant_overlay_absent_when_no_secure(config_root, platform_descriptor,
                                                     app_descriptors_dir, tmp_path):
    """Build a copy of the tree with university.secure removed → overlay must NOT apply."""
    import shutil
    import yaml
    dst = tmp_path / "cfg"
    shutil.copytree(config_root / "platform", dst / "platform")
    shutil.copytree(config_root / "clusters", dst / "clusters")
    uni = dst / "clusters/folio-etesting/namespaces/sprint/tenants/university.yaml"
    doc = yaml.safe_load(uni.read_text())
    doc["secure"] = False
    uni.write_text(yaml.safe_dump(doc))
    idx = AppIndex.load(platform_descriptor, app_descriptors_dir)
    resolved = resolve_namespace(dst, "folio-etesting", "sprint", idx)
    assert "mod-patron" not in resolved.modules


def test_rwsplit_false_marks_nothing(sprint):
    assert sprint.readWriteModules == []


def test_excluded_app_ui_modules_surfaced(sprint):
    uni = _tenant(sprint, "university")
    # cascade input present for each excluded app (value may be [] if no descriptor)
    assert set(uni.excludedAppsUiModules.keys()) == set(uni.applications["exclude"])
```

- [ ] **Step 2: Write the bugfest e2e test**

`tests/test_resolve_bugfest.py`:

```python
"""E2E: folio-etesting/bugfest (dataset path, §2.4b).
Asserts: tenant set + defaultTenant from the profile; no explicit tenants list in
the namespace; pgInstanceType/moduleReplicas surfaced; rwSplit marking only when true."""

import pytest

from resolver import resolve_namespace
from resolver.apps import AppIndex


@pytest.fixture
def bugfest(config_root, platform_descriptor, app_descriptors_dir):
    idx = AppIndex.load(platform_descriptor, app_descriptors_dir)
    return resolve_namespace(config_root, "folio-etesting", "bugfest", idx)


def test_tenants_and_default_from_profile(bugfest):
    assert [t.tenantId for t in bugfest.tenants] == [
        "fs09000000", "fs09000002", "fs09000003", "cs00000int", "cs00000int_0001"
    ]
    assert bugfest.defaultTenant == "fs09000000"
    assert bugfest.dataset["profile"] == "bugfest"
    assert bugfest.dataset["dbName"] == "folio"


def test_restore_sizing_surfaced(bugfest):
    assert bugfest.infra["pgInstanceType"] == "db.r6g.xlarge"
    assert bugfest.modules["mod-inventory-storage"]["replicaCount"] == 4
    assert bugfest.modules["mod-search"]["replicaCount"] == 4


def test_member_type_default_exclusions_applied(bugfest):
    member = next(t for t in bugfest.tenants if t.tenantId == "cs00000int_0001")
    assert "app-consortia-manager" in member.applications["exclude"]
    central = next(t for t in bugfest.tenants if t.tenantId == "cs00000int")
    assert central.applications["exclude"] == []   # consortia-central excludes nothing


def test_rwsplit_marks_when_enabled(config_root, platform_descriptor,
                                    app_descriptors_dir, tmp_path):
    """Flip features.rwSplit on a copied bugfest tree → readWriteModules marked."""
    import shutil
    import yaml
    dst = tmp_path / "cfg"
    shutil.copytree(config_root / "platform", dst / "platform")
    shutil.copytree(config_root / "clusters", dst / "clusters")
    ns = dst / "clusters/folio-etesting/namespaces/bugfest/namespace.yaml"
    doc = yaml.safe_load(ns.read_text())
    doc["features"]["rwSplit"] = True
    ns.write_text(yaml.safe_dump(doc))
    idx = AppIndex.load(platform_descriptor, app_descriptors_dir)
    resolved = resolve_namespace(dst, "folio-etesting", "bugfest", idx)
    assert "mod-users" in resolved.readWriteModules
    assert resolved.modules["mod-users"]["integrations"]["db"]["hostReader"] is True
```

- [ ] **Step 3: Run the full test suite**

Run: `cd kitfox-config && ./.venv/bin/python -m pytest tests/ -q`
Expected: all tests pass (Tasks 1–10). No failures, no errors.

- [ ] **Step 4: Run the no-regression schema gate**

Run: `cd kitfox-config && ./.venv/bin/python scripts/validate_config.py`
Expected: ends with `23/23 files valid.` and exit code 0 (resolver added no YAML under `platform/`/`clusters/`).

- [ ] **Step 5: Capture the VERIFICATION evidence**

Run and record the output of each, confirming the task's required assertions:

```bash
cd kitfox-config
./.venv/bin/python -m pytest tests/ -q
./.venv/bin/python scripts/validate_config.py | tail -1
./.venv/bin/python scripts/resolve.py folio-etesting sprint  | ./.venv/bin/python -c "import sys,json;d=json.load(sys.stdin);u=[t for t in d['tenants'] if t['tenantId']=='university'][0];print('sprint tenants:',[t['tenantId'] for t in d['tenants']]);print('default:',d['defaultTenant']);print('uni excl:',u['applications']['exclude']);print('secure overlay mod-patron:', 'mod-patron' in d['modules'])"
./.venv/bin/python scripts/resolve.py folio-etesting bugfest | ./.venv/bin/python -c "import sys,json;d=json.load(sys.stdin);print('bugfest tenants:',[t['tenantId'] for t in d['tenants']]);print('default:',d['defaultTenant']);print('pgInstanceType:',d['infra'].get('pgInstanceType'));print('replicas:',{k:v.get('replicaCount') for k,v in d['modules'].items() if 'replicaCount' in v})"
```

Expected: sprint tenants `[diku, university, college]`, default `diku`, uni exclude contains `app-fqm` + consortia-member defaults, `mod-patron` present (secure overlay applied); bugfest tenants from profile, default `fs09000000`, `pgInstanceType db.r6g.xlarge`, replicas `{mod-inventory-storage: 4, mod-search: 4}`.

- [ ] **Step 6: Commit**

```bash
cd kitfox-config && git add tests/test_resolve_sprint.py tests/test_resolve_bugfest.py && git commit -m "test(resolver): e2e sprint + bugfest verification (B.1–B.10)"
```

---

## VERIFICATION section (to fill in during execution)

Paste the actual command output here as evidence (verification-before-completion):

- [ ] `pytest tests/ -q` → all passed (count: ____)
- [ ] `validate_config.py` → `23/23 files valid.` (no regression)
- [ ] sprint: tenants `[diku, university, college]`, defaultTenant `diku`, university deployed apps exclude `app-fqm` + `{app-consortia-manager, app-linked-data, app-requests-mediated-ui}`, secure-tenant overlay applied (`mod-patron` has `SECURE_TENANT_ID=university`)
- [ ] bugfest: tenants + defaultTenant (`fs09000000`) from dataset profile, no explicit `tenants[]`, `pgInstanceType=db.r6g.xlarge`, `moduleReplicas` surfaced
- [ ] readWriteModules marked for hostReader only when `rwSplit: true`
- [ ] resolving twice → byte-identical (`test_determinism`)

Per-rule unit coverage: B.2 (`test_merge`), B.3 (`test_excludes`), B.8/Gap#5 (`test_apps`), B.4/B.5 (`test_overlays`), B.6/B.7 (`test_tenants`), B.10 (`test_roles`).

Architecture citations per rule: B.1 §5.1; B.2 §3 merge semantics; B.3 §3 UNION; B.4 §2.2b/§3 configExtensions; B.5 §2.2b/§3 presence-driven; B.6 §2.4/§3 layers 3–4; B.7 §2.4b/§3; B.8 §3/§5.2/§5.3; B.9 §5.2/§5.4; B.10 §2.3/§6.

---

## Self-Review (performed against the spec)

**Spec coverage:** B.1 Task 1; B.2 Task 2; B.3 Task 3; B.8+Gap#5 Task 4; B.6/B.7 Task 5; B.4/B.5 Task 6; B.10 Task 7; B.9 Tasks 8–9; verification Task 10. All ten Epic B stories + Gap #5 mapped to a task. Out-of-scope items (Epic D validators, Epic F pipeline, FAR/TF/version/coordinate, cascade execution, system users) are explicitly not built — the resolver only *surfaces* `excludedAppsUiModules` and `readWriteModules` marks.

**Placeholder scan:** every code step contains complete, runnable code; every run step states the exact command and expected output. No TBD/TODO.

**Type consistency:** `deep_merge(base, over)` used identically everywhere; `union_excludes(*layers)` returns sorted list; `AppIndex.load/.deployed/.excluded_ui_modules/.modules_of` names consistent across Tasks 4–5/10; `resolve_tenant(...)` signature identical in Task 5 tests + Task 8 caller; `apply_overlays(...)` keyword args match Task 6 + Task 8; `mark_read_write_modules(...)` returns `(modules, marked)` in Task 7 + Task 8; `ResolvedNamespace`/`ResolvedTenant` field names match between `model.py`, `resolve.py`, and the e2e tests.

**Known design choices flagged for the reviewer:**
- Descriptor data is an injected input (not resolution logic), matching "names not versions / out of scope FAR." Without it, deployed-set/cascade/Gap#5 are omitted but all other resolution still emits.
- `secureTenantId` uses the first `secure: true` tenant; the design implies a single secure tenant per namespace.
- Module `extraEnvVars` follow the named-list wholesale-replace rule; the reference overlays do not collide on the same module, so no env is lost. If future overlays collide, revisit per §3.
```
