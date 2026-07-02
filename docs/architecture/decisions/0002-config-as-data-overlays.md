# ADR-0002 — Feature behavior is declarative overlays, not pipeline branches

**Status:** Accepted · **Anchored in:** §2.2b, §3, correction #2, NFR3

## Context

In the legacy pipeline a "feature" is code. `isConsortiaSingleUi` triggers a dedicated merge
branch (`RancherNamespace:184`), `split-files` another (`RancherNamespace:180`), `ecs-ccl`
another (`EurekaNamespace:71`). Each branch hardcodes which modules get which env vars. The
pipeline *already* has a generic loop (`EurekaNamespace:73-77`:
`configExtensions.each { mergeMaps(getFeatureConfig(feature)) }`) — but three features bypass
it with bespoke `if` branches. Feature behavior is therefore not reviewable as data, and
adding a feature means editing Groovy.

## Decision

A feature's effect on module configuration lives in a config **overlay file**,
`platform/feature-overlays/<name>.yaml`, carrying the module `extraEnvVars` (and any declared
UI values) the feature contributes. The resolver composes whichever overlays are declared via
one **generic deep-merge loop** — there are **zero per-feature `if` branches**. Selecting a
feature *is* the act of selecting its overlay. Two selection modes:

- **Explicit** — the overlay name appears in `namespace.yaml: configExtensions[]`, merged in
  list order (e.g. `sunflower`, `consortia-single-ui`).
- **Presence-driven** — the resolver auto-selects an overlay from the resolved model:
  `secure-tenant` when any tenant has `secure: true` (with `${secureTenantId}` substituted
  from that tenant), and `rtr` when `features.rtr: true`.

This is the Kustomize-"components" / Configuration-as-Data pattern. See
`resolver/overlays.py`.

## Rationale

- Folds the three bespoke branches into the *one* generic loop the pipeline already runs —
  fewer code paths, not more.
- Feature behavior becomes a reviewable diff: "this feature sets these env vars on these
  modules" is data in version control.
- Value substitution (`${secureTenantId}`) is *value*-only — the mapping of which module gets
  which env key stays declarative; only the value is filled in. No conditional business logic
  is introduced.

## Consequences

- Removed namespace flags (`isConsortiaSingleUi`, `splitFiles`, `hasSecureTenant`/`secureTenantId`)
  are now overlay selection + presence derivation (see the migration table in
  [pipeline-mapping.md](../../pipeline-mapping.md)).
- Overlays touching the **same module's** `extraEnvVars` *replace* rather than concatenate (the
  §3 named-list rule), so overlay module sets are kept disjoint to avoid dropping env vars.
- Realizing the "no per-feature branches" goal in the live pipeline is Epic F (Story F.2); the
  resolver already proves it works (`resolver/overlays.py`, tests in `tests/test_overlays.py`).
- One coupling is kept as a light validator, not a branch: `releaseType: SUNFLOWER` should also
  list `sunflower` in `configExtensions` — enforced advisorily by gap#8
  ([validator-reference.md](../../validator-reference.md)).
- `consortiaSingleUx` is **not** an overlay-declared value. It is per-tenant catalog
  identity (`tenant-catalog.yaml`, centrals only); the `consortia-single-ui` overlay now
  contributes only the backend `SINGLE_TENANT_UX` module env. "Has a UI bundle" is likewise
  per-tenant catalog identity (`tenants.<id>.ui`), and the build-wide Stripes tunables live in
  a global `uiDefaults` block in `platform/defaults.yaml` that the resolver folds into each
  UI-having tenant's `ui` (there is no standalone namespace `uiDefaults` in the resolved model).
