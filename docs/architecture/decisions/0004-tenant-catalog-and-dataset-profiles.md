# ADR-0004 — Tenant catalog (identity once) + dataset profiles

**Status:** Accepted · **Anchored in:** §2.4, §2.4b, §3, correction #8

## Context

A handful of well-known tenants (`diku`, `consortium`, `university`, `college`, `fs09000000`,
`cs00000int*`, …) recur across 20+ namespaces. Their type, name, and admin username were
hardcoded and repeated across `pipelines-shared-library` (`folioDefault.groovy`). Separately,
a **dataset namespace** is restored from an RDS snapshot, so its tenant structure is fixed by
the snapshot's DB contents — you don't hand-author it — yet the legacy pipeline hardcoded the
dataset tenant set (`fs09000002/3`, `cs00000int*`) and derived `defaultTenant` with a
`dataset ? 'fs09000000' : 'diku'` ternary.

## Decision

Two related moves:

1. **Tenant catalog** — `platform/tenant-catalog.yaml` defines each tenant's **stable
   identity once**, keyed by id: `type`, `name`, optional `code`, and `adminUser.username`.
   Namespaces and dataset profiles reference tenants **by id**. Identity only — no apps,
   branding, smtp, or secret values. A per-namespace `tenants/<id>.yaml` carries *only*
   deployment-specific deviations.
2. **Dataset profiles** — `platform/dataset-profiles/<name>.yaml` names a snapshot's tenant
   structure (catalog ids, `defaultTenant`, `consortia`) plus restore sizing (`dbName`,
   `infra.pgInstanceType`, `moduleReplicas`). A dataset namespace sets `dataset.profile` and
   omits an explicit `tenants[]`; the two are **mutually exclusive** (enforced by D.5).
   `defaultTenant` is explicit and validated to be a member of the tenant set (D.2).

## Rationale

- Tenant identity is single-sourced; changing `university`'s admin username is one edit, not
  twenty. A referenced id absent from the catalog fails fast (D.3), so identity resolution can
  never dangle.
- Snapshot tenant structure is *referenced*, not retyped — and stays consistent with the
  snapshot. The volatile snapshot **name** stays on the namespace (`dataset.snapshot`), while
  the stable structure + sizing live in the profile.
- Replaces the derived `dataset ? fs09000000 : diku` logic with an explicit, checked field.

## Consequences

- The catalog holds the `secure` flag's *type* dimension but not `secure` itself — `secure` is
  per-deployment, on the tenant override
  ([ADR-0008](0008-tenant-type-ruleset.md)).
- Admin **passwords** are never in the catalog — only `adminUser.username`. The pipeline
  derives the password from a Secrets Manager path by convention, with an optional
  `adminUser.passwordRef` override ([ADR-0006](0006-credential-free.md)).
- Tenant membership is **never** `readdir tenants/` — it's the namespace's `tenants[]` id list
  or the dataset profile's list. The `tenants/` subdir holds only override files
  (`resolver/tenants.py: tenant_membership`).
- Two cross-level guards exist because of this model: D.3 (`tenants ⊂ catalog`) and D.5
  (`dataset ⊕ explicit-tenants`) — see
  [validator-reference.md](../../validator-reference.md).
