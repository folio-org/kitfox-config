# Resolver reference

The resolver (`resolver/` package) is the **reference implementation** of the 8-layer
resolution (§3). It is a pure, deterministic function of the config tree: it deep-merges the
precedence layers, computes per-tenant exclusions and deployed-app sets, applies feature
overlays, and emits a resolved `EurekaNamespace`/`EurekaTenant` model. Versions and
coordinates are deliberately absent — they enter at deploy time (Epic F).

> Reference, not production wiring. How the live pipeline will consume this output (invoke the
> Python, port to Groovy, or read an emitted artifact) is an open Epic-F decision; see
> `design-artifacts/kitfox-config-session-snapshot-2026-06-30.md § 8`.

## CLI

```bash
python scripts/resolve.py <cluster> <namespace> [--descriptor PATH] [--app-descriptors DIR] [--no-apps]
```

- Prints the resolved model as deterministic JSON (sorted keys, indent 2) — resolving the same
  tree twice yields byte-identical output.
- `--descriptor` / `--app-descriptors` default to the sibling
  `platform-lsp/platform-descriptor.json` and `platform-lsp/local-dev/appDescriptors`. When
  present, the resolver computes each tenant's **deployed app set**, the app-exclusion-cascade
  inputs, and the Gap-#5 config gating.
- `--no-apps` (or no descriptor available) skips the descriptor-driven work; the exclude set
  and everything else still resolve.

```bash
# Examples
python scripts/resolve.py folio-etesting sprint --no-apps
python scripts/resolve.py folio-etesting bugfest          # uses sibling descriptor if present
```

## The 8 layers (lowest → highest precedence)

```
1  platform/defaults.yaml                          (global)
2  platform/deployment-profiles/{configType}.yaml  (compute base, selected by namespace.configType)
3  platform/tenant-catalog.yaml[id]                (tenant scope — identity)
4  platform/tenant-type-defaults/{type}.yaml       (tenant scope — default excludes)
5  clusters/{cluster}/cluster.yaml                 (cluster identity)
6  clusters/{cluster}/.../namespace.yaml           (namespace scope)
7  platform/feature-overlays/{ext}.yaml            (one per configExtensions entry, in order)
8  clusters/{cluster}/.../tenants/{id}.yaml        (tenant scope — optional override)
```

The resolver splits this into a **namespace-scoped** merge and a **tenant-scoped** merge
(repeated per tenant id), then composes them. Layer 2's *selector* (`configType`) is read from
the namespace — selection key ≠ precedence (default `development` if omitted; an unknown
`configType` raises `KeyError`).

## Package map

| Module | Story | Responsibility |
|--------|-------|----------------|
| `loader.py` | B.1 | Discover clusters/namespaces by `readdir`; load every layer file into a `ConfigTree`. Reference files (`module-roles`, `tenant-type-ruleset`) loaded eagerly for the validators |
| `merge.py` | B.2 | `deep_merge(base, over)` — recursive dict merge; any non-dict (incl. lists) from `over` replaces. Never mutates inputs |
| `excludes.py` | B.3 | `union_excludes(*layers)` — the UNION exception to wholesale-replace for `applications.exclude` |
| `overlays.py` | B.4/B.5 | Apply `configExtensions` overlays in order; presence-driven `secure-tenant`/`rtr`; `${var}` value substitution |
| `tenants.py` | B.6/B.7 | Tenant membership (explicit list or dataset profile); per-tenant resolution (catalog identity → type-default → override) |
| `apps.py` | B.8 | `AppIndex` from the descriptor: `available`, `deployed(exclude)`, excluded apps' UI modules, modules-of (Gap #5) |
| `roles.py` | B.10 | `mark_read_write_modules` — flag `readWriteModules` for `integrations.db.hostReader` when `rwSplit` |
| `resolve.py` | B.9 | Orchestration: build the namespace base, resolve tenants, apply overlays + dataset sizing + rwSplit marking, emit the model |
| `model.py` | B.9 | `ResolvedNamespace` / `ResolvedTenant` dataclasses; `to_dict()` for emission |

## Merge semantics (`merge.py`, `excludes.py`, `overlays.py`)

| Construct | Rule | Where |
|-----------|------|-------|
| Scalars / maps | Deep merge; higher layer replaces the key | `deep_merge` |
| Named lists (e.g. `members`) | **Replace** wholesale — no implicit concatenation | `deep_merge` (lists are non-dict ⇒ replace) |
| `applications.exclude` | **UNION** across layers 4, 6, 8 (sorted) | `union_excludes` |
| `configExtensions` overlays | Merge in list order; later wins; same-module `extraEnvVars` *replace* | `apply_overlays` |
| Presence-driven overlays | `secure-tenant` appended if any tenant `secure`; `rtr` if `features.rtr` | `apply_overlays` |
| `${var}` placeholders | Value substitution only (`secureTenantId` today); unknown placeholders left intact | `substitute` |
| Available app set | Not stored — `available − UNION(excludes)` | `AppIndex.deployed` |
| Secret `*Ref`s | Pass through untouched | all |

## Per-tenant resolution (`tenants.resolve_tenant`)

For each tenant id in the membership:

1. Base from `tenantDefaults` (`type`, `secure`, `install`, `config`).
2. **Layer 3** — catalog identity (`type` from catalog wins; `name`, `code`, `adminUser`).
3. **Layer 8** — the optional `tenants/<id>.yaml` override: sets `secure`; deep-merges
   `install`/`config`/`adminUser`; carries `index`/`ui`.
4. **`applications.exclude`** = UNION(type-default `exclude`, namespace `exclude`, tenant
   `exclude`).
5. If a descriptor `AppIndex` is supplied: compute `deployedApps`, the excluded apps' UI
   modules (cascade input), and **Gap #5** gating — drop `config.kb` unless `mod-kb-ebsco-java`
   is deployed, drop `config.worldcat` unless `mod-copycat` is deployed.

A referenced id absent from the catalog raises `KeyError` (also caught at PR time by D.3).

## Dataset namespaces (`tenants.tenant_membership`)

When `namespace.dataset.profile` is set, membership (tenant ids, `defaultTenant`, `consortia`,
`dbName`, `infra`, `moduleReplicas`) comes from the dataset profile instead of the namespace.
The resolver then maps `moduleReplicas.<m>` onto `modules.<m>.replicaCount` and applies the
restore `pgInstanceType` onto `infra`.

## Resolved model shape (`model.py`)

`ResolvedNamespace`: `clusterName, namespaceName, platform, configType, platformBranch,
releaseType, lifecycle, members, infra, features, operations, consortia, applications
{exclude}, modules, readWriteModules, defaultTenant, tenants[], dataset?, podPlacement?, ui`.

`ResolvedTenant`: `tenantId, type, name, secure, adminUser, install, config, applications
{exclude}, code?, index?, ui?, deployedApps?, excludedAppsUiModules?`.

Topology flags (`built-in|aws`) and names are present; coordinates and versions are
deliberately **absent** (filled by Terraform outputs / FAR at deploy). `emit_json` serializes
with `sort_keys=True` for reproducibility.

## Tests

`tests/` (76 passing) covers each story: `test_merge`, `test_excludes`, `test_overlays`,
`test_tenants`, `test_apps`, `test_roles`, `test_resolve_sprint`, `test_resolve_bugfest`,
`test_determinism`, plus the validator tests. Run with `python -m pytest -q` inside the venv.
