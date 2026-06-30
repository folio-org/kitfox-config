# ADR-0001 — Exclude-model for applications (no include pool)

**Status:** Accepted · **Anchored in:** §0, §3, §4, correction #1

## Context

Each tenant runs a subset of the platform's applications. The naïve model is an *include
list* per tenant. But the FOLIO branch already defines the full app set in
`platform-lsp/platform-descriptor.json`, and the existing pipeline's `assignApplications()`
already starts from "every app assigned to every tenant" and then **removes** the ones a
tenant must not have (e.g. a standard tenant must not run consortia apps). An include list
would duplicate the descriptor and drift from it.

## Decision

There is **no application include pool** in config. The available app set is the full
`platform-descriptor.json` list for the namespace's `platformBranch`. Config only ever
**excludes** apps, at three layers, and the exclusions **UNION**:

1. `platform/tenant-type-defaults/<type>.yaml` — default exclusions per tenant type
2. `namespace.yaml: applications.exclude` — namespace-wide (rare; debug/special cases)
3. `tenants/<id>.yaml: applications.exclude` — per-tenant

A tenant's deployed set is `available − UNION(excludes)`, never read from a stored include
list. The tenant-type **ruleset** (§4, [ADR-0008](0008-tenant-type-ruleset.md)) is the
PR-time backstop that proves the resolved exclusion set is correct.

## Rationale

- **Single source of truth for app availability** — the descriptor, not a hand-maintained
  list that can drift.
- **Mirrors existing pipeline behavior** (`assignApplications()` removes, never includes),
  so the migration is faithful rather than a re-design.
- The UNION rule means a lower layer can *add* an exclusion but can **never** silently
  un-exclude an app a higher-precedence policy layer disallowed — a tenant cannot grant
  itself a type-forbidden app.

## Consequences

- Excluding an app cascades: its **backend** modules are simply never entitled; its **UI**
  modules are pruned from the bundle by the pipeline (the *app-exclusion cascade*, §3, §5.3).
  This is one general derivation, **not** a `modules.exclude` config surface (correction #6).
- `applications.exclude` is the one deliberate exception to the wholesale-replace merge rule
  (it unions instead) — see `resolver/excludes.py` and
  [resolver-reference.md](../../resolver-reference.md).
- Former namespace flags like `linkedData` disappear as inputs: they become the presence (or
  absence) of `app-linked-data` in the exclusion set.
- The resolver needs the descriptor to compute the deployed set; without it (`--no-apps`) the
  exclude set still resolves but the deployed-app list and D.1 check are skipped.
