# ADR-0008 — Tenant-type ruleset with `secure` as an orthogonal boolean

**Status:** Accepted · **Anchored in:** §4 model note (supersedes catalog §13)

## Context

The Phase-1 entity catalog listed tenant `type` as a four-value enum:
`standard | consortia | consortia-central | secure`. But the application policy needs a tenant
that is **both** `consortia-central` **and** secure — `app-requests-mediated-ui` requires
exactly that combination. A single mutually-exclusive enum cannot express "central *and*
secure". Separately, the per-type application policy (which type may run which app) was buried
in the pipeline's `assignApplications()` exclusion logic, not expressed as data.

## Decision

Two parts:

1. **`type` is the enum `{standard, consortia-member, consortia-central}`; `secure` is an
   orthogonal boolean** on the tenant (`secure: true`). This preserves all four conceptual
   states without making them exclusive, and matches the `isSecureTenant` boolean already on
   `EurekaTenant`. (This supersedes the catalog §13 four-value enum.)
2. **A data-driven ruleset** — `platform/tenant-type-ruleset.yaml` maps each application to its
   `allowedTypes` and `requireSecure`. The per-type defaults
   ([ADR-0001](0001-exclude-model-for-apps.md)) *author* the exclusions; the ruleset is the
   PR-time **validator** (D.1) that proves the result: for every app a tenant **deploys**, the
   tenant's `type ∈ rule.allowedTypes` and, if `rule.requireSecure`, `tenant.secure` is true.

## Rationale

- The enum is made non-lossy without re-opening any prior decision: four states, two
  orthogonal axes.
- The business rule ("a standard tenant must not run consortia apps"; "mediated-UI needs
  central + secure") lives entirely as **data** in two files — the per-type default (the green
  path) and the ruleset (the backstop) — not in pipeline code.
- The validator catches a tenant that overrides its type default incorrectly, or a hand-edited
  type default that drops a required exclusion, with a precise message.

## Consequences

- `secure` lives on the per-tenant override (`tenants/<id>.yaml: secure`), not in the catalog —
  it is per-deployment, while the catalog is identity.
- Presence of any `secure: true` tenant auto-selects the `secure-tenant` overlay
  ([ADR-0002](0002-config-as-data-overlays.md)) — the same `secure` flag drives both the app
  policy and the module env.
- The ruleset is **role-aware and intentionally non-monotonic** across consortia types — e.g.
  `app-linked-data` is allowed for `standard` and `consortia-central` but **not** for a
  `consortia-member` (correction #5). See the D.1 algorithm in
  [validator-reference.md](../../validator-reference.md).
- The schemas constrain `allowedTypes` and tenant `type` to the three-value enum
  (`_defs.tenantType`), so a stray `secure` "type" fails validation.
