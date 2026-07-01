# Config → pipeline mapping

How each piece of `kitfox-config` relates to its consumer in `pipelines-shared-library`
(PSL), which deployment layer it lands in, and its status. Sourced from the schema
architecture §5–§6 migration map and the two chain-trace reports
(`design-artifacts/B-Trigger-Map/namespace-creation-chain-review.md` and
`…-parameter-layer-trace.md`). PSL citations are `path:line` relative to
`pipelines-shared-library/`.

> **Iteration-1 boundary.** Everything in the **config** column is implemented *on the config
> side* (schemas + resolver + reference slice). The pipeline does **not** yet read it —
> wiring PSL to consume the resolved model and deleting its legacy derivations is **Epic F**, a
> separate later phase. So "config" here means "modeled and resolvable", not "already consumed
> by the live pipeline".

## Status legend

| Status | Meaning |
|--------|---------|
| **config** | An authored `kitfox-config` field (Iteration-1) |
| **derived** | Not a field — the pipeline computes it from config + descriptors at deploy (Epic F) |
| **pipeline-only** | Never config — run-control selectors, versions, coordinates, ephemeral secrets, approval gates |
| **deferred-E/F** | Modeled but wiring/extension is Epic E (Okapi) or Epic F (pipeline executor) |

## Deployment layers

A namespace creation run flows through five layers (chain-trace §2): **Terraform** (infra
provisioning) → **Helm** (module deploy + feature overlays) → **REST-init** (tenant/consortia/
index configuration) → **UI** (Stripes build) → **edge** (edge module ephemeral-properties).

---

## Infrastructure & cluster identity → Terraform / cluster layer

| Config | PSL consumer | Layer | Status |
|--------|--------------|-------|--------|
| `cluster.cloud.region` | `Constants.AWS_REGION` | Terraform | config |
| `cluster.cloud.vpcName` | `Constants.AWS_EKS_VPC_NAME` | Terraform | config |
| `cluster.registry.ecr` | `Constants.ECR_FOLIO_REPOSITORY` + `charts/mgr-*/values.yaml:image.repository` (single-sourced) | Helm | config |
| `cluster.dns.rootDomain` | `Constants.CI_ROOT_DOMAIN` | UI/edge/ingress | config |
| `cluster.endpoints.openSearchUrl` | `Constants.FOLIO_OPEN_SEARCH_URL` | Terraform/REST | config |
| `cluster.endpoints.eurekaRegistryUrl` | `Constants.EUREKA_REGISTRY_URL` | Helm | config |
| `cluster.endpoints.rancherApiUrl` | `Constants.RANCHER_API_URL` | Terraform | config |
| `cluster.endpoints.farUrl` | `FAR_URL` | REST (version resolution) | config |
| `cluster.superuser.username` | `RancherNamespace:75` `admin/admin` | REST | config (password → derived, F.5) |
| `namespace.infra.{pgType,kafkaType,opensearchType,s3Type}` | `resolveInfraType` + `NAMESPACE_OVERRIDES`; `pg_embedded`/`kafka_shared`/`opensearch_shared`/`s3_embedded` TF vars | Terraform | config |
| `namespace.infra.pgVersion` | `Constants.PGSQL_DEFAULT_VERSION` → `pg_version` | Terraform | config |
| PG/Kafka/S3 **host/port/password** | Terraform outputs + Secrets Manager | Terraform | pipeline-only (coordinates) |
| `eureka-components` kong/keycloak/sidecar versions → `kong_version`/`keycloak_version` TF vars (`folioNamespaceCreateEureka:99-100`) | FAR → **Terraform** inputs | Terraform | pipeline-only (versions) |

## Cluster / namespace registry → discovery & lifecycle

| Config | PSL consumer | Layer | Status |
|--------|--------------|-------|--------|
| existence of `clusters/<name>/` | `Constants.AWS_EKS_CLUSTERS` | discovery | config |
| existence of `clusters/<c>/namespaces/<n>/` | `Constants.AWS_EKS_NAMESPACE_MAPPING` | discovery | config |
| `namespace.platform` | `resolvePlatform(clusterName)` (`DPR:51-57`) | orchestrator gate | config (derivation removed, F.1) |
| `namespace.configType` | `resolveConfigType(clusterName)` (`DPR:59-64`) | Helm profile select | config (derivation removed, F.1) |
| `namespace.members[]` | `ENVS_MEMBERS_LIST` via `resolveMembers` (`DPR:83`) **and** the duplicate re-read at `folioNamespaceCreateEureka:96` → `github_team_ids` | Terraform (RBAC) | config (both reads retire, F.1) |
| `namespace.lifecycle.category` | `RANCHER_KNOWN_NAMESPACES` / `AWS_EKS_{DEV,TESTING,RELEASE,TMP}_NAMESPACES` | governance | config |
| `namespace.lifecycle.protected` | `RANCHER_PROTECTED_NAMESPACES` | governance | config |
| `NAMESPACE_OVERRIDES[...]` | — | Terraform/Helm | config (explicit `infra:`/`features:` block; map deleted, F.1) |

## Tenant identity & membership → REST-init

| Config | PSL consumer | Layer | Status |
|--------|--------------|-------|--------|
| `tenant-catalog.<id>.{type,name,code}` | hardcoded tenant ids/types across PSL; `folioDefault.groovy` | REST-init | config |
| `tenant-catalog.<id>.adminUser.username` | plaintext `diku_admin/admin`, `folio/folio`, `ECSAdmin/admin` (`folioDefault.groovy:73-330`); `createUserFlow` (`Eureka.groovy:112-150`) | REST-init | config (password → convention-derived, F.5) |
| `namespace.tenants[]` / `defaultTenant` | `EurekaNamespace.addTenant`; `dataset ? fs09000000 : diku` (`folioNamespaceCreateEureka:71`) | REST-init | config |
| `namespace.consortia[]` | `setUpConsortiaFlow` name-based grouping (`Eureka.groovy:223-224`) | REST-init | config |
| `tenant.config.kb.{url,customerId}` + `.apiKeyRef` | `setRmapiConfig` — `Constants.KB_API_URL`/`KB_CUSTOMER_ID` + `kbApiKey` | REST-init | config (applied when `mod-kb-ebsco-java` present) |
| `tenant.config.worldcat` | `setWorldcat` — `Constants.WORLDCAT`, `COPYCAT_PROFILE_ID` | REST-init | config (applied when `mod-copycat` present) |
| `tenant.config.smtp` / `tenant.config.ldp.*Ref` | SMTP config; `PG_LDP_DEFAULT_PASSWORD` (plaintext) | REST-init | config (secrets → `*Ref`) |
| `tenant.install.{loadReference,loadSample,…}` | `EurekaRequestParams` (`folioNamespaceCreateEureka:159-163`, namespace-wide today) | REST-init | config (modifier defaults; scope shifts to per-tenant) |
| `tenant.index[]` | `runIndexFlow` | REST-init | config |

## Dataset / RDS snapshot → Terraform + REST-init

| Config | PSL consumer | Layer | Status |
|--------|--------------|-------|--------|
| `namespace.dataset.profile` set ⇒ dataset namespace | `CreateNamespaceParameters.dataset` boolean + `resolveDataset` | — | config (no separate flag) |
| `namespace.dataset.snapshot` | `BUGFEST_SNAPSHOT_NAME` / `DATA_MIGRATION_SNAPSHOT_NAME` → `pg_rds_snapshot_name` | Terraform | config |
| `dataset-profile.dbName` | `BUGFEST_SNAPSHOT_DBNAME` → `pg_dbname` | Terraform | config |
| `dataset-profile.infra.pgInstanceType` | hardcoded `db.r6g.xlarge` (`folioNamespaceCreateEureka:105`) | Terraform | config |
| `dataset-profile.moduleReplicas.<m>` | dataset scale-out `mod-inventory-storage`/`mod-search`→4 (`:359-361`) → `modules.<m>.replicaCount` | Helm | config |
| `dataset-profile.{tenants,defaultTenant,consortia}` | hardcoded `fs09000002/3` + `cs00000int*` (`:193-214`) | REST-init | config |

## Features → Helm overlays (config-as-data)

| Config | PSL consumer | Layer | Status |
|--------|--------------|-------|--------|
| `configExtensions: [sunflower, …]` | runtime fetch of `resources/helm/features/*.yaml` + generic `configExtensions.each` (`EurekaNamespace:73-77`) | Helm | config |
| `feature-overlays/consortia-single-ui.yaml` | `if(isConsortiaSingleUi) merge` branch (`RancherNamespace:184`) | Helm | config (branch folded into loop, F.2) |
| `feature-overlays/split-files.yaml` | `split-files` branch (`RancherNamespace:180`) | Helm | config (F.2) |
| `feature-overlays/ecs-ccl.yaml` | `ecs-ccl` branch (`EurekaNamespace:71`) | Helm | config (F.2) |
| `feature-overlays/secure-tenant.yaml` (presence-driven) | `SECURE_TENANT_ID` env via `folioHelm` switch (`:368-399`) | Helm | config (auto-selected from `secure: true`) |
| `feature-overlays/rtr.yaml` | `setEnableRtr` → `LEGACY_TOKEN_TENANTS` (`folioHelm:421`) — **no overlay file existed** | Helm | config (overlay authored; F.4 wiring) |
| `feature-overlays/sunflower.yaml` | `FolioRelease.fromPlatformBranch` SUNFLOWER (`DPR:18,26`) | Helm | config |
| tenant `ui.consortiaSingleUx` (catalog identity, centrals only) + `isEcsBff` | central-tenant single bundle (`:228-231`); `isEcsBff = isConsortia && ecsCCL` (`:396`) | UI | config (per-tenant) + derived |

### Removed namespace flags → derived/relocated

| Legacy flag (`CreateNamespaceParameters`) | New home | Status |
|-------------------------------------------|----------|--------|
| `consortia` / `consortiaExtra` | presence of consortia-type tenants + `consortia:` blocks | derived |
| `isConsortiaSingleUi` | `consortia-single-ui` overlay (backend env) + central tenant `ui.consortiaSingleUx` in `tenant-catalog.yaml` | config (overlay + catalog identity) |
| `hasSecureTenant` / `secureTenantId` | tenant `secure: true` → presence-driven overlay; `${secureTenantId}` substituted | derived |
| `linkedData` | `app-linked-data` in/out of `applications.exclude`; `folio_ld-folio-wrapper` cleanup | config + derived |
| `loadReference` / `loadSample` | `tenant.install.*` | config |
| `marcMigrations` | `app-marc-migrations` exclusion (flag was already inert — never wired, F5) | config |

## Per-module config → three homes (folioHelm switch split, §2.6b)

The `folioHelm.groovy:~353-523` `switch(moduleName)` block splits by nature (correction #7).
See ADR-0009 — the deployment profile owns the full per-module values.

| Legacy branch | New home | Layer | Status |
|---------------|----------|-------|--------|
| Static module env (`spring.cache.type`, default probes/JVM/resources, ingress/service shape, integrations) | `platform/deployment-profiles/{configType}.yaml: modules.<name>` (per ADR-0009) | Helm | config |
| `mod-fqm-manager` cache timeout (`:406`) | `namespace.modules.mod-fqm-manager.extraEnvVars` | Helm | config |
| `mod-scheduler` timer (`:428`), `mod-bulk-operations` multipart (`:433`) | `namespace.modules.<m>` | Helm | config |
| `mod-data-export`/`mod-marc-migrations` initContainer+PVC (`:447-461`) | `namespace.modules.<m>.{initContainer,volumeClaims}` | Helm | config |
| quality-gate `nodeSelector`/`tolerations` (`:464`) | `namespace.podPlacement` | Helm | config |
| `mod-authtoken` `LEGACY_TOKEN_TENANTS` under `rtr` (`:421`) | `feature-overlays/rtr.yaml` | Helm | config |
| ingress `host`, ALB `group.name`, edge NLB domain, `MOD_USERS_ID`, `jwt.signing.key` (`:472-524`) | — | Helm | derived |
| `module-roles.readWriteModules` + `features.rwSplit` → per-module `hostReader` mark | `READ_WRITE_MODULES` (dead constant) + `enable_rw_split` TF var | Helm | config (resolver B.10); reader coordinate derived |
| `module-roles.systemUserModules` | `SYSTEM_USER_MODULES` (dead constant) | REST-init | deferred-F (Story F.6) |

## Edge → mostly derived (§2.4c, ADR-0007)

| Config | PSL consumer | Layer | Status |
|--------|--------------|-------|--------|
| `edge-modules.edgeAdmin.username` | `edge_admin` Keycloak user (`Edge.groovy:44-65`) | edge | config (password derived) |
| `edge-modules.modules.<m>.{capabilities,capabilitySets}` | `config_eureka.yaml` (Eureka) | edge | config |
| `edge-modules.modules.<m>.permissions` | `config.yaml` (Okapi) | edge | deferred-E (Okapi) |
| `edge-modules.modules.<m>.institutionalUsers` | per-module `tenants[]` (plaintext `test/test`) | edge | config (credential-free; per-module render fixes leak) |
| `edge_tenants` / `edge_mappings` / `edge_users` | `folioEdge.renderEphemeralProperties` | edge | derived (Story F.4) |

## What is never config (pipeline-only)

| Concern | Why | Reference |
|---------|-----|-----------|
| `type` / `namespaceOnly` / `dmSnapshot` | run-control selectors; `type`→TF `setup_type` gates RDS snapshot-restore resources (`postgresql.tf:558,571`) | [ADR-0005](architecture/decisions/0005-operations-modifiers-vs-selectors.md) |
| `kitfoxApproval` gates | governance guardrails (`pgType=aws`; `etesting`/`dataset`/`release`) | §5.3 |
| App/module versions | FAR-resolved from `platform-descriptor.json` at deploy | §5.3 |
| Coordinates + secret values | Terraform outputs + Secrets Manager | §5.3 |
| Ephemeral generated secrets | JWT signing key, supertenant bootstrap | §0 |
| Install-list normalization | `mod-consortia-keycloak`/`folio_consortia-settings` stripped from every Eureka tenant (`EurekaTenant.withInstallJson:165`) | §5.3 (confirm in F.3) |

## Residuals flagged for Epic F

- `EurekaTenant.withInstallJson:165` install-list normalization — confirm still required under
  the app-driven model.
- The `members` double-read retirement (`folioNamespaceCreateEureka:96`).
- The `fli01:` InnReach mapping constant in `ephemeral-properties.tpl` — future config candidate.
- The open Epic-F decision: how the pipeline consumes the resolved model (invoke Python /
  port to Groovy / read an emitted artifact). A shadow-run is recommended before deleting any
  `DependentParametersResolver` derivations.
