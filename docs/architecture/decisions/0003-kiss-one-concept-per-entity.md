# ADR-0003 — KISS: `platform`/`configType` on the namespace only; cluster is pure infra

**Status:** Accepted · **Anchored in:** §2.5, §3, corrections #3/#4, NFR2

## Context

In the legacy model the cluster carried a `platform: [...]` list, and
`DependentParametersResolver` *derived* a namespace's `platform` and `configType` from the
cluster name (`resolvePlatform(clusterName)`, `resolveConfigType(clusterName)`). This mirrors
the same concept across two levels: a cluster "has platforms" and a namespace "has a
platform", and the relationship is buried in derivation code. It invites the question "is this
namespace's platform the cluster's, or its own?" and makes the cluster-vs-namespace boundary
fuzzy.

## Decision

Apply KISS / one-concept-per-entity:

- A **cluster** is *pure infrastructure identity* — the "where": cloud region/VPC, ECR
  registry, root DNS, shared pre-provisioned endpoints, supertenant username. Nothing else.
- `platform` (OKAPI/EUREKA) and `configType` live **only on the namespace**, declared, not
  derived. `cluster.schema.json` **forbids** `platform`, `configType`, and any application
  list via `additionalProperties: false`.
- The `DependentParametersResolver` derivations (`resolvePlatform`, `resolveConfigType`) are
  removed; the values come straight from `namespace.yaml`.

## Rationale

- No field is mirrored across cluster + namespace, so there is no "which level wins"
  ambiguity.
- A namespace fully declares how it runs; reading one file tells you its platform and profile.
- The cluster file stays small and stable — it changes only when the underlying infra
  identity changes, not when a namespace picks a different profile.

## Consequences

- `configType` is a *selection key* for the deployment-profile base (layer 2) but is read from
  the **namespace** — proving selection-key ≠ precedence (§3). Default is `development` when
  omitted (`resolver/resolve.py:_namespace_base`).
- The legacy `NAMESPACE_OVERRIDES` special-casing (e.g. `folio-etesting/sprint` forcing `aws`
  infra) becomes an explicit `infra:` block in that one `namespace.yaml` — no hardcoded
  resolver branch (§3). Any new exception is a new override block, never a code change.
- Removing the derivations in the live pipeline is Epic F (Story F.1).
- The same discipline applies elsewhere: tenant *identity* lives once in the catalog, not
  repeated per namespace ([ADR-0004](0004-tenant-catalog-and-dataset-profiles.md)).
