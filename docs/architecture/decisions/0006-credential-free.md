# ADR-0006 — Credential-free: every secret is a `*Ref` or convention-derived

**Status:** Accepted · **Anchored in:** §0, corrections #14/#22/#24, NFR1

## Context

The legacy configuration is full of plaintext secrets: tenant admin credentials in
`folioDefault.groovy` (`diku_admin/admin`, `folio/folio`, `ECSAdmin/admin`, …), the
supertenant `admin/admin` (`RancherNamespace:75`), PostgreSQL root/pgadmin/LDP default
passwords in `Constants.groovy`, and edge test users as plaintext `test/test`. Committing this
configuration as-is would version-control real credentials.

## Decision

**No secret value ever appears in config.** Every secret is one of:

- A **reference** — a `*Ref` string field matching `^(secretsmanager|ssm|tf)://` (the
  `secretRef` pattern in `schemas/_defs.schema.json`): `apiKeyRef`, `credentialsRef`,
  `dbUserPasswordRef`, `passwordRef`, etc. A plaintext value fails schema validation.
- **Convention-derived** — for admin/superuser/edge passwords, config holds only the
  `username`; the pipeline derives the password from a Secrets Manager/SSM path by convention
  (the existing `getTenantClientAWSSecretStoragePath` mechanism), with an optional
  `*.passwordRef` override when the secret isn't at the conventional path.

Schemas enforce this structurally: `tenant-catalog`, `cluster.superuser`, and
`edge-modules.edgeAdmin` accept `username` (+ optional `passwordRef`) but **no** password
field; `edge-modules.institutionalUsers` *require* a `passwordRef`.

## Rationale

- A config repo that can never contain a secret is safe to make broadly readable and to diff
  in PRs.
- Convention-derived passwords mean the common case needs *zero* secret config — just the
  username — while still allowing an explicit `passwordRef` escape hatch.
- References (vs values) keep rotation entirely in the secret store; config never changes when
  a secret rotates.

## Consequences

- Ephemeral secrets the **pipeline itself generates** (the `mod-authtoken` JWT signing key, the
  supertenant bootstrap) never touch config and are out of scope — acceptable (§0).
- Provisioned-infra secrets (PG/Kafka/S3 passwords) are Terraform-generated → Secrets Manager;
  the pipeline reads the output at deploy. Config holds only the topology flag, never the
  coordinate or the secret.
- Wiring the convention-derived admin secret resolution into the live pipeline (deleting the
  plaintext `folioDefault.groovy` credentials) is Epic F (Story F.5). The schema + reference
  config are already fully credential-free.
- The chain-trace flagged a real leak this model fixes: the legacy edge render accumulated test
  users across modules — `institutionalUsers` are now rendered per-module only
  ([ADR-0007](0007-edge-mostly-derived.md)).
