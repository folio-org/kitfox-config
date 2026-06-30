# Validator reference

`kitfox-config` has **two PR gates**. Both must be green to merge. This page documents the
second — the cross-level guards — including the exact failure messages, so you can decode a
red build.

| Gate | Script | What it checks |
|------|--------|----------------|
| **1 · Schema** | `scripts/validate_config.py` | Every committed YAML validates against its JSON Schema (per-file, structural). See [schema-reference.md](schema-reference.md) |
| **2 · Cross-level** | `scripts/validate_cross_level.py` | The 5 relational guards (D.1–D.5) + the gap#8 advisory — rules JSON Schema can't express within one file |

Both run in CI via `.github/workflows/validate-config.yml` on any PR touching `platform/**`,
`clusters/**`, `schemas/**`, `scripts/**`, `validators/**`, or the fixtures, plus the schema
**smoke test** (`scripts/smoke_test.py`) that proves valid fixtures pass and broken ones fail.

## Gate 1 — schema validation

```bash
python scripts/validate_config.py            # default roots: platform/ clusters/
# PASS  clusters/folio-etesting/namespaces/sprint/namespace.yaml  [namespace]
# ...
# 23/23 files valid.
```

A failure prints the file, the JSON-pointer of the offending field, and the message:

```
FAIL  clusters/.../namespace.yaml  [namespace]
        - /operations/type Additional properties are not allowed ('type' was unexpected)
```

Two non-schema checks live here too:

- **No-matching-schema** → a YAML file whose path matches no kind fails:
  `no matching schema for this path (unexpected/generated artifact — NFR8)`.
- **Intra-file** (A.5) → a dataset profile whose `defaultTenant` is not in its `tenants[]`:
  `defaultTenant '<x>' is not a member of tenants[] (A.5 intra-file check)`.

## Gate 2 — cross-level guards

```bash
python scripts/validate_cross_level.py
# PASS  folio-etesting/bugfest
# PASS  folio-etesting/sprint
# 2/2 namespaces clean; 0 violation(s).
```

It discovers every `(cluster, namespace)` and runs the guards. The descriptor for D.1 is the
sibling `platform-lsp/platform-descriptor.json` when present (local dev), else the vendored
`tests/fixtures/platform-descriptor.json` (CI). If no descriptor is found, D.1 is skipped with
a warning; D.2–D.5 + gap#8 still run.

Each violation prints as `[rule] file: message`. The guards:

### D.1 — tenant-type ruleset (`validators/d1_tenant_type.py`)

For every app a tenant **deploys** (`available − UNION(excludes)`), the tenant's `type` must be
in the matching rule's `allowedTypes`, and if the rule sets `requireSecure`, the tenant must be
`secure`. Needs the resolved deployed set, so it runs only when D.3 found no dangling ids and a
descriptor is available.

```
[D.1] clusters/.../namespace.yaml: standard tenant 'diku' deploys app-consortia (allowed: consortia-member, consortia-central)
[D.1] clusters/.../namespace.yaml: tenant 'X' deploys app-requests-mediated-ui which requires secure: true, but the tenant is not secure
```

### D.2 — `defaultTenant ∈ tenants` (`validators/d2_default_tenant.py`)

```
[D.2] clusters/.../namespace.yaml: defaultTenant '<x>' is not in namespace '<ns>' tenant set [<list>]
```

### D.3 — `tenants ⊂ catalog` (`validators/d3_catalog.py`)

Every referenced tenant id — the tenant set (explicit or from the dataset profile) **plus** each
consortia block's central + members — must exist in `tenant-catalog.yaml`.

```
[D.3] clusters/.../namespace.yaml: tenant id '<x>' is referenced by namespace '<ns>' but is not in platform/tenant-catalog.yaml
```

### D.4 — consortia-block-required (`validators/d4_consortia.py`)

When a namespace **deploys** a `consortia-central` tenant (catalog type), it must have exactly
one consortia block naming that central, and every listed member must be a `consortia-member`
tenant present in the tenant set. (Trigger is the deployed central, not the block — `sprint`
names `consortium` only in its `consortia:` block, so it does not deploy a central and is
correctly skipped.)

```
[D.4] ...: namespace '<ns>' deploys consortia-central tenant '<c>' but has no consortia block naming it as central
[D.4] ...: namespace '<ns>' has N consortia blocks for central '<c>'; exactly one is required
[D.4] ...: consortia member '<m>' (central '<c>') has catalog type '<t>', expected consortia-member
[D.4] ...: consortia member '<m>' (central '<c>') is not in the namespace '<ns>' tenant set
```

### D.5 — `dataset ⊕ explicit-tenants` (`validators/d5_dataset_tenants.py`)

A namespace must reference tenants **either** via `dataset.profile` **or** an explicit
`tenants[]`, never both and never neither. Reads the authored `namespace.yaml` (not the
resolved tree, which collapses the dataset into a tenant set).

```
[D.5] ...: namespace '<ns>' sets both dataset.profile ('<p>') and an explicit tenants[] list; they are mutually exclusive (§2.6/§2.4b)
[D.5] ...: namespace '<ns>' sets neither dataset.profile nor an explicit tenants[] list; exactly one is required (§2.6/§2.4b)
```

### gap#8 — releaseType ↔ sunflower (`validators/d8_release_type.py`)

Advisory consistency check: a namespace with `releaseType: SUNFLOWER` should also list
`sunflower` in `configExtensions` so the overlay is applied.

```
[gap#8] ...: namespace '<ns>' has releaseType: SUNFLOWER but 'sunflower' is not in configExtensions (the overlay would not be applied)
```

## How the guards compose (`validators/runner.py`)

D.2–D.5 and gap#8 read the **raw** loaded tree, so a dangling tenant id surfaces as a clean D.3
message instead of crashing the resolver. Only D.1 uses the resolver (for the deployed set), and
it is skipped when D.3 found dangling ids (resolution would raise) or no descriptor is present.
A resolution failure inside D.1 is caught and reported as a D.1 violation rather than crashing
the gate.

`Violation` (`validators/core.py`) carries `rule`, `file` (repo-relative), `entity`, and
`message`, and stringifies as `[rule] file: message`.

## Negative fixtures

`schemas/examples/invalid/` and the tests in `tests/test_validators_invalid.py` exercise each
guard's failure path — the smoke test asserts every broken fixture is rejected for the right
reason, proving the gate bites (Epic C.4 / D.6).
