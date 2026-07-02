# CLAUDE.md

Guidance for Claude Code when working in `kitfox-config`. For the full picture start at
[`README.md`](README.md) and [`docs/index.md`](docs/index.md).

## Project purpose

`kitfox-config` is a GitOps, **configuration-as-data** repository that declares the FOLIO
platform's `cluster → namespace → tenant` deployment configuration as schema-validated YAML.
It replaces hardcoded configuration in `pipelines-shared-library` (`Constants.groovy`,
`DependentParametersResolver`, `CreateNamespaceParameters`) and per-chart Helm values. The end
goal: the deployment pipeline becomes a **pure executor** over this config.

## Tech stack

- **Config:** YAML, validated by **JSON Schema** (draft 2020-12) under `schemas/`.
- **Tooling:** **Python 3.12+** — the resolver (`resolver/`), validators (`validators/`), and
  CLIs (`scripts/`). Deps: `PyYAML`, `jsonschema` (`requirements.txt`); `pytest`
  (`requirements-dev.txt`). Use the project virtualenv at `.venv` — activate it before running
  anything: `source .venv/bin/activate`.

## Repository structure

| Path | What |
|------|------|
| `platform/` | Repo-wide layer: `defaults.yaml`, `deployment-profiles/`, `feature-overlays/`, `tenant-catalog.yaml`, `dataset-profiles/`, `tenant-type-defaults/`, `module-roles.yaml`, `edge-modules.yaml`, `tenant-type-ruleset.yaml` |
| `clusters/<c>/` | `cluster.yaml` + `namespaces/<ns>/namespace.yaml` (+ optional `tenants/<id>.yaml`). The directory tree *is* the deployment hierarchy |
| `schemas/` | One JSON Schema per config kind + shared `_defs.schema.json` |
| `resolver/` | Python 8-layer merge engine → resolved `EurekaNamespace`/`EurekaTenant` model |
| `validators/` | Cross-level guards D.1–D.5 + gap#8 |
| `scripts/` | `validate_config.py`, `validate_cross_level.py`, `resolve.py`, `smoke_test.py` |
| `tests/` | `pytest` suite (resolver + validators) |
| `docs/` | Architecture, ADRs, schema/resolver/validator references, pipeline mapping, contributing, glossary |

## Commands

```bash
source .venv/bin/activate
python scripts/validate_config.py                      # gate 1 — schema (23/23 valid)
python scripts/validate_cross_level.py                 # gate 2 — cross-level guards (0 violations)
python scripts/smoke_test.py                           # schema smoke test
python -m pytest -q                                    # 76 tests
python scripts/resolve.py folio-etesting sprint --no-apps   # resolve a namespace to JSON
```

## Working conventions (load-bearing — see docs/architecture/decisions/)

- **Credential-free:** every secret is a `*Ref` (`^(secretsmanager|ssm|tf)://`) or
  convention-derived (username only). Never write a plaintext secret.
- **KISS / one concept per entity:** `platform`/`configType` live on the namespace; the cluster
  is pure infra identity; tenant identity lives once in the catalog. Don't mirror fields.
- **Config-as-data:** feature behavior is a `feature-overlays/*.yaml` overlay, not pipeline
  code. No per-feature branches.
- **Exclude-model:** no app include pool; config only excludes (unioned across layers).
- **Operations split:** `operations.*` are modifier defaults; selectors
  (`type`/`namespaceOnly`/`dmSnapshot`) are pipeline-only and schema-rejected.
- Every schema is `additionalProperties: false` — adding an unlisted field fails the gate.

## Status

**Iteration 1 (config side) — complete and verified.** Epics A (schemas), B (resolver),
C (reference slice: `folio-etesting/sprint` + `bugfest`), D (validators) are done and green.
Epic E (Okapi pass) and Epic F (wire the live pipeline to consume the resolved model) are later,
separate phases — the pipeline is read-only reference until then. Plan + status:
`../_bmad-output/planning-artifacts/epics.md`,
`../design-artifacts/kitfox-config-session-snapshot-2026-06-30.md`.

## Tooling notes

This repo is configured for Serena (semantic code tools) — prefer it for `resolver/` and
`validators/` work. The design source of truth lives in the parent workspace under
`../design-artifacts/B-Trigger-Map/kitfox-config-schema-architecture.md` (cited as §N
throughout `docs/`).
