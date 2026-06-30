# Schema reference

Per-kind field reference, derived from `schemas/*.json` (JSON Schema draft 2020-12). Every
schema sets `additionalProperties: false`, so **any field not listed below is rejected** —
this is how removed legacy flags and stray edge blocks fail validation. Section markers (§N)
point into the schema architecture doc.

## How a file is matched to its schema

`scripts/validate_config.py` maps each YAML file to a schema **kind** by path
(`KIND_RULES`). If a committed YAML under `platform/` or `clusters/` matches no kind, the run
**fails** (an unexpected/generated artifact — NFR8).

| Path pattern | Kind / schema |
|--------------|---------------|
| `**/cluster.yaml` | `cluster` |
| `**/namespace.yaml` | `namespace` |
| `**/tenants/<id>.yaml` | `tenant` |
| `**/deployment-profiles/<x>.yaml` | `deployment-profile` |
| `**/feature-overlays/<x>.yaml` | `feature-overlay` |
| `**/tenant-type-defaults/<x>.yaml` | `tenant-type-default` |
| `**/dataset-profiles/<x>.yaml` | `dataset-profile` |
| `**/tenant-catalog.yaml` | `tenant-catalog` |
| `**/edge-modules.yaml` | `edge-modules` |
| `**/module-roles.yaml` | `module-roles` |
| `**/tenant-type-ruleset.yaml` | `tenant-type-ruleset` |
| `**/defaults.yaml` | `platform-defaults` |

Every file requires `schemaVersion: 1`.

## Shared definitions (`_defs.schema.json`)

Reused across all schemas:

| `$def` | Rule |
|--------|------|
| `schemaVersion` | `const: 1` |
| `secretRef` | string matching `^(secretsmanager\|ssm\|tf)://` — the only allowed form of a secret |
| `topologyType` | enum `built-in \| aws` (never a host/port/url) |
| `tenantType` | enum `standard \| consortia-member \| consortia-central` |
| `envVar` | `{ name, value }` (both strings, required) |
| `extraEnvVars` | array of `envVar` |
| `moduleOverride` | `{ replicaCount, resources, autoscaling, extraEnvVars, extraJavaOpts, initContainer.enabled, volumeClaims.<name>.enabled }` |
| `consortiaEntry` | `{ central, name, members[] }` (all required) |
| `resources` | `{ requests{memory,cpu}, limits{memory,cpu} }` |
| `autoscaling` | `{ enabled, minReplicas, maxReplicas, targetCPUUtilizationPercentage }` |

---

## `cluster` — `clusters/<c>/cluster.yaml` (§2.5)

Pure infrastructure identity. **Required:** `schemaVersion, name, cloud, registry, dns,
endpoints, superuser`.

| Field | Type | Notes |
|-------|------|-------|
| `name` | string | Cluster name (matches directory) |
| `cloud.region` / `cloud.vpcName` | string | Required. Replaces `Constants.AWS_REGION` / `AWS_EKS_VPC_NAME` |
| `registry.ecr` | string | Required. Replaces `Constants.ECR_FOLIO_REPOSITORY` |
| `dns.rootDomain` | string | Required. Root for all generated domains |
| `endpoints.{rancherApiUrl, eurekaRegistryUrl, openSearchUrl, farUrl}` | uri | Required. Shared pre-provisioned endpoints |
| `superuser.username` | string | Required. **No password field** ([ADR-0006](architecture/decisions/0006-credential-free.md)) |

**Forbidden** (rejected by `additionalProperties:false`): `platform`, `configType`, any
application list ([ADR-0003](architecture/decisions/0003-kiss-one-concept-per-entity.md)).

## `namespace` — `clusters/<c>/namespaces/<ns>/namespace.yaml` (§2.6)

**Required:** `schemaVersion, name, platform`.

| Field | Type | Notes |
|-------|------|-------|
| `platform` | enum `OKAPI\|EUREKA` | Owned here, not derived |
| `configType` | string | Selects the deployment profile; default `development` |
| `platformBranch` | string | Eureka: drives versions via FAR |
| `releaseType` | enum `SNAPSHOT\|SUNFLOWER\|TRILLIUM` | |
| `okapiVersion`, `folioBranch` | string | Okapi-only (accommodated for Epic E) |
| `lifecycle.category` | enum `dev\|testing\|release\|tmp` | Replaces the Constants category arrays |
| `lifecycle.protected` | boolean | Was `RANCHER_PROTECTED_NAMESPACES` membership |
| `members[]` | string[] | GitHub team names (+ pseudo tokens like `Eureka`) |
| `infra.{pgType,kafkaType,opensearchType,s3Type}` | `topologyType` | Topology override only |
| `infra.pgVersion` | string | A name, not a coordinate |
| `features.{rwSplit,rtr,ecsCCL,scNative,greenmail,mockServer}` | boolean | Removed flags rejected (correction #2) |
| `configExtensions[]` | string[] | Feature-overlay names, applied in order |
| `consortia[]` | `consortiaEntry[]` | Required when a central tenant is present (D.4) |
| `applications.exclude[]` | string[] | Namespace-wide exclusions (exclude-only) |
| `tenants[]` | string[] | Catalog ids; mutually exclusive with `dataset` (D.5) |
| `defaultTenant` | string | Must be in `tenants[]` (D.2) |
| `dataset.{snapshot,profile}` | string | Dataset restore; XOR `tenants[]` (D.5) |
| `operations.{uiBuild,runSanityCheck,skipReindex,setBaseUrl}` | boolean | Modifier defaults |
| `operations.entitlementApproach` | enum `STATE\|CREATE` | |
| `podPlacement.{nodeSelector,tolerations}` | object/array | Namespace-wide pod placement |
| `modules.<name>` | `moduleOverride` | Per-module config override |

**Forbidden:** the removed flags (`consortia`, `isConsortiaSingleUi`, `hasSecureTenant`,
`linkedData`, `loadReference`, `loadSample`, `dataset` boolean), any per-namespace `edge:`
block ([ADR-0007](architecture/decisions/0007-edge-mostly-derived.md)), and the run-control
selectors `type`/`namespaceOnly`/`dmSnapshot` under `operations`
([ADR-0005](architecture/decisions/0005-operations-modifiers-vs-selectors.md)).

## `tenant` — `clusters/<c>/namespaces/<ns>/tenants/<id>.yaml` (§2.7)

Per-namespace deviations only. **Required:** `schemaVersion, tenantId`.

| Field | Type | Notes |
|-------|------|-------|
| `tenantId` | string | Must be in the namespace `tenants[]` and the catalog |
| `secure` | boolean | Per-deployment; orthogonal to type ([ADR-0008](architecture/decisions/0008-tenant-type-ruleset.md)) |
| `adminUser.passwordRef` | `secretRef` | Optional; username comes from the catalog |
| `applications.exclude[]` | string[] | Unioned with type-default + namespace |
| `index[]` | `{type,recreate,waitComplete}` | Search index rebuild config |
| `install.{loadReference,loadSample,ignoreErrors,async,reinstall,simulate,purgeOnRollback}` | boolean | Install-param deviations |
| `config.kb.{url,customerId,apiKeyRef}` | string / `secretRef` | API key is a ref |
| `config.worldcat.{profileId,credentialsRef}` | string / `secretRef` | |
| `config.smtp.{host,port,from,credentialsRef}` | string/int / `secretRef` | |
| `config.ldp.{dbHost, dbUserPasswordRef, adminDbUserPasswordRef, configDbUserPasswordRef, sqconfigRepoTokenRef}` | string / `secretRef` | All passwords are refs |
| `ui.{enabled,branch,add[],remove[],branding.logo,branding.favicon}` | mixed | UI sub-block |

**Forbidden:** `type`, `name`, `description` (identity is catalog-resolved). Every credential
field must be a `*Ref` — a plaintext value fails.

## `tenant-catalog` — `platform/tenant-catalog.yaml` (§2.4)

**Required:** `schemaVersion, tenants`. `tenants` is a map `id → identity`; each entry
**requires** `type, name, adminUser`.

| Field | Type | Notes |
|-------|------|-------|
| `tenants.<id>.type` | `tenantType` | Drives type-defaults + ruleset |
| `tenants.<id>.name` | string | Display name |
| `tenants.<id>.description` | string | Optional |
| `tenants.<id>.code` | string | Optional ECS short code |
| `tenants.<id>.adminUser.username` | string | Required identity |
| `tenants.<id>.adminUser.passwordRef` | `secretRef` | Optional; **no plaintext password** |

## `dataset-profile` — `platform/dataset-profiles/<name>.yaml` (§2.4b)

**Required:** `schemaVersion, name, tenants`.

| Field | Type | Notes |
|-------|------|-------|
| `dbName` | string | Restored DB name |
| `infra.pgInstanceType` | string | Restore **sizing** (not topology) |
| `moduleReplicas.<module>` | integer | Dataset pod scale-out |
| `defaultTenant` | string | Must be a member of `tenants[]` — **validator intra-file check** (A.5) |
| `tenants[]` | string[] | Catalog ids |
| `consortia[]` | `consortiaEntry[]` | Same shape as namespace `consortia` |

> `defaultTenant ∈ tenants[]` is checked in `validate_config.py:_intra_file_checks` (JSON
> Schema core can't express cross-property containment), not by the schema itself.

## `platform-defaults` — `platform/defaults.yaml` (§2.1)

**Required:** `schemaVersion`. The lowest-precedence layer.

| Field | Type | Notes |
|-------|------|-------|
| `infra.{pgType,pgVersion,kafkaType,opensearchType,s3Type}` | `topologyType`/string | Default topology |
| `features.{rwSplit,rtr,ecsCCL,scNative}` | boolean | Removed flags rejected |
| `tenantDefaults.type` / `.secure` | `tenantType` / boolean | |
| `tenantDefaults.install.{loadReference,loadSample,ignoreErrors,async,reinstall,simulate,purgeOnRollback}` | boolean | Repo-wide install defaults |
| `tenantDefaults.config.kb.{url,customerId,apiKeyRef}` | string/`secretRef` | |
| `tenantDefaults.config.worldcat.{profileId,credentialsRef}` | string/`secretRef` | |

## `deployment-profile` — `platform/deployment-profiles/<configType>.yaml` (§2.2)

**Required:** `schemaVersion, configType`. Compute shape, not feature toggles.

| Field | Type | Notes |
|-------|------|-------|
| `defaults.{replicaCount,resources,autoscaling}` | mixed | Default compute envelope |
| `moduleClassOverrides.<class>.{replicaCount,resources,autoscaling}` | mixed | e.g. `mgr` is heavier |
| `modules.<name>` | permissive object | Full per-module Helm values for this profile (ADR-0009). Transferred verbatim from `pipelines-shared-library/resources/helm/<configType>.yaml`; consumed as the base module layer before `moduleClassOverrides`, feature overlays, and `namespace.modules.<name>` overrides. Credential-free — only `existingSecret` references, never plaintext values. |
| `ui.{idleSessionWarningSeconds,maxUnpagedResourceCount,rtr.idleSessionTTL,rtr.idleModalTTL}` | mixed | Stripes tunables |

## `feature-overlay` — `platform/feature-overlays/<name>.yaml` (§2.2b)

**Required:** `schemaVersion, name`. Module env values may carry `${...}` substitution
placeholders resolved by the pipeline/resolver.

| Field | Type | Notes |
|-------|------|-------|
| `modules.<name>` | `moduleOverride` | Per-module config the feature contributes |
| `ui.consortiaSingleUx` | boolean | Declared UI value read directly by the build |

## `edge-modules` — `platform/edge-modules.yaml` (§2.4c)

**Required:** `schemaVersion, edgeAdmin, modules`.

| Field | Type | Notes |
|-------|------|-------|
| `edgeAdmin.username` | string | Required; password convention-derived |
| `edgeAdmin.passwordRef` | `secretRef` | Optional |
| `modules.<name>.capabilities[]` / `.capabilitySets[]` | string[] | Eureka |
| `modules.<name>.permissions[]` | string[] | Okapi |
| `modules.<name>.institutionalUsers[]` | `{tenant,username,passwordRef}` | Each **requires** `passwordRef` |

## `module-roles` — `platform/module-roles.yaml` (§2.3)

**Required:** `schemaVersion`.

| Field | Type | Notes |
|-------|------|-------|
| `readWriteModules[]` | string[] | Receive `integrations.db.hostReader` when `rwSplit` (resolver B.10) |
| `systemUserModules[]` | string[] | Need a system user at tenant init (consumed in Epic F) |
| `eurekaModules[]` | string[] | `EUREKA_MODULES` list |

## `tenant-type-default` — `platform/tenant-type-defaults/<type>.yaml` (§2.8)

**Required:** `schemaVersion, type`.

| Field | Type | Notes |
|-------|------|-------|
| `type` | `tenantType` | |
| `applications.exclude[]` | string[] | Default exclusions for this type |

## `tenant-type-ruleset` — `platform/tenant-type-ruleset.yaml` (§4)

**Required:** `schemaVersion, default, rules`.

| Field | Type | Notes |
|-------|------|-------|
| `default.allowedTypes[]` | `tenantType[]` | For any app not listed in `rules` |
| `default.requireSecure` | boolean | |
| `rules[].applications[]` | string[] | Apps this rule covers |
| `rules[].allowedTypes[]` | `tenantType[]` | Types allowed to run them |
| `rules[].requireSecure` | boolean | Optional |

The schema validates the rule file's **shape**; the rules are *applied* to resolved tenants by
the D.1 validator — see [validator-reference.md](validator-reference.md).
