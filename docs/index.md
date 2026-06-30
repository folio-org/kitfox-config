# kitfox-config documentation

The documentation hub for `kitfox-config` — the GitOps, config-as-data repository that
declares the FOLIO platform's `cluster → namespace → tenant` deployment configuration.

> New here? Read the [top-level README](../README.md) first for the one-paragraph what/why
> and the quick start.

## Map of the docs

| Doc | Read it when you want to… |
|-----|---------------------------|
| [architecture/overview.md](architecture/overview.md) | Understand the design, the entity model, the 8-layer resolution, and the data flow (with diagrams) |
| [architecture/decisions/](architecture/decisions/) | Understand *why* — the load-bearing decisions, each as an ADR |
| [pipeline-mapping.md](pipeline-mapping.md) | See how each config field maps to its `pipelines-shared-library` consumer and deployment layer |
| [contributing.md](contributing.md) | Add a cluster / namespace / tenant, run the gates locally, and pass review |
| [schema-reference.md](schema-reference.md) | Look up the fields, types, and rules of each config file kind |
| [resolver-reference.md](resolver-reference.md) | Understand the merge engine, its semantics, and the `resolve.py` CLI |
| [validator-reference.md](validator-reference.md) | Decode a failed cross-level check (the exact messages) |
| [glossary.md](glossary.md) | Look up a term (tenant type, overlay, dataset profile, edge_admin, …) |

`docs/superpowers/` holds the original Epic B and Epic D implementation plans — kept for
historical reference, not part of this maintained set.

## Source of truth

This documentation **distills** the design artifacts; it does not replace them. When a
detail here is thin, the authoritative sources are:

- **Design / schema architecture:** `design-artifacts/B-Trigger-Map/kitfox-config-schema-architecture.md` (cited as “§N” throughout these docs)
- **Entity inventory:** `design-artifacts/A-Product-Brief/config-entity-catalog.md`
- **Pipeline traces:** `design-artifacts/B-Trigger-Map/namespace-creation-chain-review.md` and `…/namespace-creation-parameter-layer-trace.md`
- **Plan + status:** `_bmad-output/planning-artifacts/epics.md`, `design-artifacts/kitfox-config-session-snapshot-2026-06-30.md`
- **The code:** `schemas/`, `resolver/`, `validators/`, `scripts/`

## Status

| Epic | Scope | State |
|------|-------|-------|
| **A** | JSON Schemas + CI schema gate | ✅ Iteration 1 — 13 schema files, `validate_config.py` 23/23 valid |
| **B** | Resolver / 8-layer merge engine | ✅ Iteration 1 — `resolver/`, 76 tests pass |
| **C** | Reference config slice (`platform/` + `folio-etesting`) | ✅ Iteration 1 — `sprint` (explicit tenants) + `bugfest` (dataset) |
| **D** | Cross-level PR validators | ✅ Iteration 1 — D.1–D.5 + gap#8, `validate_cross_level.py` 0 violations |
| **E** | Okapi-platform pass | ⏭️ Iteration 2, only if Okapi clusters stay in scope |
| **F** | Pipeline-as-pure-executor (live `pipelines-shared-library`) | ⏭️ Later / separate phase — config side is read-only reference until then |

**What “done” means for Iteration 1:** the repo is self-validating (two PR gates) and
resolvable (config tree → deterministic resolved model). The pipeline does **not** yet
consume it — that is Epic F. See [pipeline-mapping.md](pipeline-mapping.md) for the
config-vs-deferred split.
