# kitfox-config

**Centralized, GitOps configuration-as-data for the FOLIO platform.** One repository
that declares *what* to deploy for every `cluster → namespace → tenant`, validates itself
at PR time, and resolves to a model the deployment pipeline consumes. The end goal: the
pipeline becomes a **pure executor** over this config, holding no policy of its own.

## The problem it solves

Today the configuration that drives namespace creation lives in code: hardcoded constants
and derivation logic scattered across `pipelines-shared-library` (`Constants.groovy`,
`DependentParametersResolver`, the `CreateNamespaceParameters` model) and per-chart Helm
`values.yaml`. Adding a namespace means editing a code array; a feature flag means a new
`if` branch; tenant admin passwords sit in plaintext in `folioDefault.groovy`. None of it
is reviewable as data, and the Ops team runs 3 clusters × 20+ namespaces × 3–11 tenants on
top of it.

`kitfox-config` moves that configuration out of code and into declarative, schema-validated
YAML — credential-free, minimally redundant, and diffable in a PR. See
[docs/pipeline-mapping.md](docs/pipeline-mapping.md) for the field-by-field migration.

## Repository structure

| Path | Purpose |
|------|---------|
| `platform/` | Cluster-agnostic, repo-wide layer: global defaults, deployment profiles, feature overlays, the tenant catalog, dataset profiles, per-type defaults, module roles, edge modules, and the tenant-type ruleset |
| `clusters/<cluster>/` | Per-cluster infra identity (`cluster.yaml`) and its `namespaces/<ns>/namespace.yaml` (+ optional `tenants/<id>.yaml` overrides). The directory tree *is* the deployment hierarchy |
| `schemas/` | JSON Schema (draft 2020-12) — the validation source of truth, one file per config kind + shared `_defs` |
| `resolver/` | Python reference resolver: deep-merges the 8 precedence layers into a resolved `EurekaNamespace`/`EurekaTenant` model |
| `validators/` | Cross-level PR guards (D.1–D.5 + gap#8) that JSON Schema cannot express within one file |
| `scripts/` | CLIs: `validate_config.py`, `validate_cross_level.py`, `resolve.py`, `smoke_test.py` |
| `tests/` | `pytest` suite for the resolver + validators |
| `docs/` | This documentation set (see below) |
| `.github/workflows/validate-config.yml` | The PR gate that runs both validators + the smoke test |

## How to navigate the docs

Start at **[docs/index.md](docs/index.md)**. The high-value entry points:

- New to the design? → [docs/architecture/overview.md](docs/architecture/overview.md) (diagrams + the cluster→namespace→tenant model)
- *Why* is it shaped this way? → [docs/architecture/decisions/](docs/architecture/decisions/) (the ADR log)
- Authoring config? → [docs/contributing.md](docs/contributing.md) + [docs/schema-reference.md](docs/schema-reference.md)
- What does the resolver emit? → [docs/resolver-reference.md](docs/resolver-reference.md)
- Why did my PR fail? → [docs/validator-reference.md](docs/validator-reference.md)
- How does config map to the pipeline? → [docs/pipeline-mapping.md](docs/pipeline-mapping.md)
- Unfamiliar term? → [docs/glossary.md](docs/glossary.md)

## Quick start

```bash
# One-time: create the virtualenv and install validator + resolver deps.
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt        # PyYAML, jsonschema
pip install -r requirements-dev.txt    # + pytest (for the test suite)
```

**Validate every committed YAML against its schema** (PR gate #1):

```bash
python scripts/validate_config.py
# → 23/23 files valid.
```

**Run the cross-level guards** (PR gate #2):

```bash
python scripts/validate_cross_level.py
# → 2/2 namespaces clean; 0 violation(s).
```

**Resolve a namespace** to the model the pipeline will consume:

```bash
python scripts/resolve.py folio-etesting sprint --no-apps
# → JSON: platform EUREKA, configType testing, tenants [diku, university, college], …
```

**Add a tenant** (the short version — full steps in [docs/contributing.md](docs/contributing.md)):

1. Add its identity to `platform/tenant-catalog.yaml` (`id → {type, name, adminUser.username}`).
2. List the id in the namespace's `tenants:` (and, if it's a consortium member, the `consortia:` block).
3. Only if it deviates, add `clusters/<cluster>/namespaces/<ns>/tenants/<id>.yaml`.
4. Run both validators above — green is the merge gate.

## Status

**Iteration 1 (config side) — complete and verified.** Epics A (schemas), B (resolver),
C (reference slice), D (validators) are done and green. Epic E (Okapi pass) and Epic F
(wiring the live pipeline to consume the resolved model) are later, separate phases. See
[docs/index.md § Status](docs/index.md#status) and `_bmad-output/planning-artifacts/epics.md`.
