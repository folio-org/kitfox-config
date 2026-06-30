# ADR-0007 — Edge config is mostly derived; only the account + capabilities are config

**Status:** Accepted · **Anchored in:** §2.4c, §5.3, correction #22 (supersedes #12)

## Context

Edge modules (`edge-orders`, `edge-patron`, `edge-oai-pmh`, …) need an `ephemeral-properties`
configmap with `edge_tenants`, `edge_mappings`, `edge_users`, and per-module
capabilities/permissions. An early design modeled a full per-namespace `edge:` block. But
*rendering the actual `config_eureka.yaml` / ephemeral-properties template* showed most of it
is **derivable** from data the model already has — and that the legacy render had a bug where a
shared `tenants` list accumulated across modules (e.g. `edge-orders` carried `edge-patron`'s
test tenants).

## Decision

Edge ephemeral-properties are **derived by the pipeline**, not configured:

- `edge_tenants` = the namespace's tenants; `edge_mappings` = the default tenant;
  `edge_users` = the `edge_admin` service account (Eureka) or each `tenant.adminUser` + the
  shared ECS edge user (Okapi).

The **only** real edge config is platform-level, in `platform/edge-modules.yaml`:

- `edgeAdmin` — the edge service account (username; password convention-derived).
- `modules.<name>` — per-module `capabilities`/`capabilitySets` (Eureka) and `permissions`
  (Okapi), which are stable, not per-namespace.
- optional `modules.<name>.institutionalUsers` — dev/test edge users, **credential-free**
  (each requires a `passwordRef`), rendered into **that module's** ephemeral-properties only.

There is **no** per-namespace `edge:` block — `namespace.schema.json` rejects it.

## Rationale

- Verified against `folioEdge` + `Edge.groovy` by rendering the real output: tenants/mappings/
  users genuinely fall out of the resolved model, so storing them would be redundant config
  that can drift.
- Scoping `institutionalUsers` per module fixes the legacy cumulative-list leak — a module
  only ever sees its own test users.
- The account + capabilities *are* stable and real, so they live once at platform level.

## Consequences

- Edge "mostly-derived" means the resolver does **not** emit edge ephemeral-properties; that
  render is pipeline-owned derivation (Epic F, Story F.4).
- Some render constants stay pipeline-owned (e.g. `secureStore.type=Ephemeral` for dev, the
  `fli01:` InnReach mapping prefix) — flagged as future config candidates if they must vary.
- Okapi `permissions` coverage and the shared ECS edge user are part of the deferred Okapi pass
  (Epic E, §7).
- This decision is *why* a contributor adding an edge module edits `platform/edge-modules.yaml`
  and nothing under `clusters/` — see [contributing.md](../../contributing.md).
