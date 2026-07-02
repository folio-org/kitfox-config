# Glossary

Terms used across `kitfox-config` and these docs. Section markers (§N) point into
`design-artifacts/B-Trigger-Map/kitfox-config-schema-architecture.md`.

### Cluster
A Kubernetes cluster, modeled as **pure infrastructure identity** — cloud placement,
container registry, root DNS, shared pre-provisioned endpoints, and the supertenant
username. A cluster deliberately carries **no** `platform` or `configType`; those are
per-namespace decisions (§2.5, [ADR-0003](architecture/decisions/0003-kiss-one-concept-per-entity.md)).
One directory per cluster under `clusters/`.

### Namespace
A deployment environment inside a cluster (e.g. `sprint`, `bugfest`). Owns `platform`
(OKAPI/EUREKA), `configType`, topology overrides, feature flags, overlays, app exclusions,
member teams, operational modifier defaults, and its tenant set. Maps the bulk of the
legacy `CreateNamespaceParameters` (§2.6).

### Tenant
A FOLIO tenant deployed in a namespace. **Identity** (type, name, code, admin username)
lives once in the [tenant catalog](#tenant-catalog); a namespace references tenants by id.
Per-namespace **deviations** go in an optional `tenants/<id>.yaml` override file (§2.7).

### Tenant type
The enum `{standard, consortia-member, consortia-central}` (§4 model note). Drives the
per-type default app exclusions and the tenant-type ruleset. **Not** a place for `secure`.

### Secure (tenant)
An **orthogonal boolean** on a tenant (`secure: true`), independent of tenant type. Needed
because `app-requests-mediated-ui` requires a tenant that is *both* `consortia-central`
*and* secure — impossible as a single enum value
([ADR-0008](architecture/decisions/0008-tenant-type-ruleset.md)). Presence of any secure
tenant auto-selects the `secure-tenant` overlay.

### Tenant catalog
`platform/tenant-catalog.yaml` — the canonical inventory of every known tenant, keyed by
id, holding **identity only** (type, name, optional code, `adminUser.username`). No apps,
branding, smtp, or plaintext passwords. A referenced id absent from the catalog fails
validation (D.3) (§2.4, [ADR-0004](architecture/decisions/0004-tenant-catalog-and-dataset-profiles.md)).

### Dataset profile
`platform/dataset-profiles/<name>.yaml` — names the **fixed tenant structure of an RDS
snapshot** (tenant ids, default tenant, consortia) plus restore sizing (`dbName`,
`pgInstanceType`, `moduleReplicas`). A *dataset namespace* selects a profile instead of
hand-authoring tenants; the two are mutually exclusive (D.5) (§2.4b).

### Deployment profile
`platform/deployment-profiles/<configType>.yaml` — a named **compute base layer** (replica
counts, resource envelopes, autoscaling, Stripes UI tunables) selected by the namespace's
`configType` (`development`, `testing`, `performance`, `release`). Deployment *shape*, not
feature toggles (§2.2).

### Feature overlay
`platform/feature-overlays/<name>.yaml` — a feature's effect on module configuration
expressed as **declarative data** (module `extraEnvVars`, UI values), not pipeline code.
Selecting a feature *is* selecting its overlay (config-as-data,
[ADR-0002](architecture/decisions/0002-config-as-data-overlays.md), §2.2b).

### configExtensions
The namespace field listing feature overlays to apply, in merge order. Each entry pulls
`platform/feature-overlays/<entry>.yaml` at layer 7 of resolution (§3).

### Presence-driven overlay
An overlay the resolver auto-selects from the resolved model rather than from an explicit
list. `secure-tenant` (any tenant `secure: true`) and `rtr` (`features.rtr: true`) are
presence/flag-driven; everything else is listed in `configExtensions` (§2.2b, §3).

### Exclude model
There is no application *include* pool. The available app set is the full
`platform-descriptor.json` list for the branch; config only ever **excludes** apps
(namespace-wide, per-type default, per-tenant). Exclusions **union** across layers
([ADR-0001](architecture/decisions/0001-exclude-model-for-apps.md), §0, §3).

### App-exclusion cascade
The pipeline-side derivation that prunes an excluded app's **UI modules** from a tenant's
bundle (backend modules of an excluded app are simply never entitled). One general rule, not
a `modules.exclude` config surface; the resolver only surfaces the excluded apps' UI module
names as cascade input (§3, §5.3).

### Tenant-type ruleset
`platform/tenant-type-ruleset.yaml` — maps `application → allowedTypes / requireSecure`.
The PR-time **validator** (D.1) that proves a resolved tenant's deployed app set is legal
for its type/secure. The per-type defaults author the exclusions; the ruleset is the
backstop (§4).

### Operations: modifiers vs selectors
**Modifiers** (`uiBuild`, `runSanityCheck`, `skipReindex`, `entitlementApproach`,
`setBaseUrl`; and per-tenant `install.*`) tune *how* a deploy behaves — config defaults,
overridable per-run. **Selectors** (`type`, `namespaceOnly`, `dmSnapshot`) pick *which*
operation runs and can change provisioned infra — **pipeline-only inputs, never config**
([ADR-0005](architecture/decisions/0005-operations-modifiers-vs-selectors.md), §5.3).

### Credential-free / `*Ref`
No secret value ever appears in config. Every secret is a pointer — a `secretsmanager://`,
`ssm://`, or `tf://` reference (`*Ref` fields) — or convention-derived by the pipeline. Admin
passwords are derived from a Secrets Manager path by convention
([ADR-0006](architecture/decisions/0006-credential-free.md), §0).

### edge_admin
The single edge service account (`edge-modules.yaml: edgeAdmin.username`) created per tenant
for Eureka edge modules. Its password is convention-derived. The only *real* edge config is
platform-level (the account + per-module capabilities/permissions + optional
`institutionalUsers`); the rest of an edge module's ephemeral-properties is **derived** by
the pipeline ([ADR-0007](architecture/decisions/0007-edge-mostly-derived.md), §2.4c, §5.3).

### Topology, not coordinates
Config states `built-in` vs `aws` for PG/Kafka/OpenSearch/S3 — never a host/port/url.
Coordinates for provisioned infra come from Terraform outputs at deploy time; shared
pre-provisioned endpoints (OpenSearch, Eureka registry, Rancher, FAR) are cluster identity
(§0).

### Names, not versions
Config holds app and module **names**; versions resolve at deploy from
`platform-lsp/platform-descriptor.json` via **FAR** (§0).

### FAR
The FOLIO Application Registry — the version-resolution authority. Given a branch's
`platform-descriptor.json`, FAR resolves concrete app/module versions. `cluster.endpoints.farUrl`
points at it. The resolver works in names; FAR/versions are a deploy-time concern (§5.3).

### Resolved model
The output of the resolver: a `ResolvedNamespace` containing `ResolvedTenant`s, with
topology flags and names present but coordinates/versions deliberately absent. Maps onto the
pipeline's `EurekaNamespace`/`EurekaTenant`. A pure, deterministic function of the config
tree (§5.2, [resolver-reference.md](resolver-reference.md)).
