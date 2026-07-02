# Contributing & coding guide

How to change `kitfox-config` safely: add a cluster / namespace / tenant, run the gates
locally, follow the conventions, and pass review. Everything here is enforced by the two PR
gates ([validator-reference.md](validator-reference.md)) — green locally means green in CI.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt        # PyYAML, jsonschema (validators + resolver)
pip install -r requirements-dev.txt    # + pytest
```

The two commands you run before every PR:

```bash
python scripts/validate_config.py        # gate 1 — schema (→ N/N files valid)
python scripts/validate_cross_level.py   # gate 2 — cross-level guards (→ N/N namespaces clean)
```

And, when touching the resolver or validators:

```bash
python -m pytest -q                      # 76 tests
python scripts/resolve.py <cluster> <namespace> --no-apps   # eyeball the resolved model
```

## Add a cluster

1. Create `clusters/<cluster>/cluster.yaml` — pure infrastructure identity
   ([schema: `cluster`](schema-reference.md#cluster--clusterscclusteryaml-25)). Required:
   `schemaVersion: 1`, `name`, `cloud.{region,vpcName}`, `registry.ecr`, `dns.rootDomain`,
   `endpoints.{rancherApiUrl,eurekaRegistryUrl,openSearchUrl,farUrl}`, `superuser.username`.
2. Do **not** add `platform`, `configType`, or any app list — the schema forbids them
   ([ADR-0003](architecture/decisions/0003-kiss-one-concept-per-entity.md)).
3. Create the `clusters/<cluster>/namespaces/` directory (add a namespace next).
4. `python scripts/validate_config.py` → the new file must show `PASS … [cluster]`.

## Add a namespace

1. Create `clusters/<cluster>/namespaces/<ns>/namespace.yaml`
   ([schema: `namespace`](schema-reference.md#namespace--clusterscnamespacesnsnamespaceyaml-26)).
   Required: `schemaVersion: 1`, `name`, `platform` (`OKAPI|EUREKA`).
2. Choose the tenant model — **exactly one** (guard D.5):
   - *Explicit*: `tenants: [<id>, …]` + `defaultTenant: <id>` (must be in the list, D.2).
   - *Dataset*: `dataset: { snapshot: <name>, profile: <profileName> }` and **no** `tenants:`.
3. If any tenant is `consortia-central`, add a `consortia:` block naming its central + members
   (guard D.4). Every member must be a `consortia-member` in the tenant set.
4. Set `configType` (selects the deployment profile; default `development`), `infra` overrides
   (topology flags only), `features`, `configExtensions`, `operations`, and any
   `modules.<name>` / `podPlacement` deviations as needed.
5. Run both gates. A new namespace should resolve:
   `python scripts/resolve.py <cluster> <ns> --no-apps`.

Worked example: `clusters/folio-etesting/namespaces/sprint/namespace.yaml` (explicit tenants +
consortium + overlays) and `…/bugfest/namespace.yaml` (dataset).

## Add a tenant

1. **Identity → catalog.** Add the tenant to `platform/tenant-catalog.yaml`
   ([schema: `tenant-catalog`](schema-reference.md#tenant-catalog--platformtenant-catalogyaml-24)):

   ```yaml
   tenants:
     newtenant: { type: standard, name: "New Tenant", adminUser: { username: newtenant_admin } }
   ```

   `type` is `standard | consortia-member | consortia-central`. **No password** — only
   `adminUser.username` (the password is convention-derived;
   [ADR-0006](architecture/decisions/0006-credential-free.md)).
2. **Membership.** Add the id to the namespace's `tenants:` list (and, if it's a consortium
   member/central, to the `consortia:` block).
3. **Deviations (optional).** Only if this tenant differs from catalog identity + type
   defaults, create `clusters/<cluster>/namespaces/<ns>/tenants/<id>.yaml`
   ([schema: `tenant`](schema-reference.md#tenant--clusterscnamespacesnstenantsidyaml-27)):
   `secure`, extra `applications.exclude`, `install` deviations, `config.*` (all secrets as
   `*Ref`), `index`, `ui`. Identity (`type`/`name`) is **not** repeated here — the schema
   rejects it.
4. Run both gates. D.3 will fail loudly if the id isn't in the catalog; D.1 will fail if the
   tenant's type isn't allowed to run an app it would deploy.

## Add a feature overlay

Create `platform/feature-overlays/<name>.yaml`
([schema: `feature-overlay`](schema-reference.md#feature-overlay--platformfeature-overlaysnameyaml-22b)),
declaring the module `extraEnvVars` (and any `ui.*`) the feature contributes. Reference it from
a namespace via `configExtensions: [<name>]`. No pipeline change — that's the point
([ADR-0002](architecture/decisions/0002-config-as-data-overlays.md)). `secure-tenant` and `rtr`
are presence-driven and need no `configExtensions` entry.

## Add an edge module

Edit `platform/edge-modules.yaml` only — add `modules.<name>` with `capabilities`/
`capabilitySets` (Eureka) and/or `permissions` (Okapi). Do **not** add anything under
`clusters/` — edge ephemeral-properties are derived
([ADR-0007](architecture/decisions/0007-edge-mostly-derived.md)). Any `institutionalUsers` need
a `passwordRef`.

## Conventions (what review and CI enforce)

- **Credential-free.** Every secret is a `*Ref` matching `^(secretsmanager|ssm|tf)://`, or
  convention-derived (username only). A plaintext value fails schema validation. Never commit a
  password ([ADR-0006](architecture/decisions/0006-credential-free.md)).
- **KISS / one concept per entity.** Don't mirror a field across levels. `platform`/`configType`
  live on the namespace; the cluster is pure infra; tenant identity lives once in the catalog
  ([ADR-0003](architecture/decisions/0003-kiss-one-concept-per-entity.md)).
- **Minimal redundancy.** State a value once at the highest applicable level; lower levels carry
  only overrides. An override file should exist *only* when a tenant deviates.
- **No removed flags.** `consortia`, `isConsortiaSingleUi`, `hasSecureTenant`, `linkedData`,
  `loadReference`/`loadSample` at namespace scope are gone — `additionalProperties:false` rejects
  them. Use the overlay/derivation/relocation instead (see
  [pipeline-mapping.md](pipeline-mapping.md)).
- **Operations: modifiers only.** `operations` holds modifier defaults; the run-control selectors
  `type`/`namespaceOnly`/`dmSnapshot` are pipeline-only and rejected
  ([ADR-0005](architecture/decisions/0005-operations-modifiers-vs-selectors.md)).
- **Topology, not coordinates.** `infra.*` is `built-in|aws` only — never a host/port/url.
- **Exclude-only apps.** There is no include list; add to `applications.exclude`, never invent a
  `modules.exclude` ([ADR-0001](architecture/decisions/0001-exclude-model-for-apps.md)).
- **No generated config.** Only hand-authored YAML is committed; a file matching no schema fails
  the gate (NFR8).

## Python style (resolver / validators)

- The resolver is a **pure function** of the config tree — no I/O side effects beyond reading
  files, deterministic output (`emit_json` sorts keys). Keep it that way.
- `from __future__ import annotations`; type hints throughout; `copy.deepcopy` so layers never
  mutate the shared loaded tree.
- One story per module (`merge`, `excludes`, `overlays`, `tenants`, `apps`, `roles`, `resolve`,
  `model`); a new validator is one `d<N>_<name>.py` returning `list[Violation]`, wired into
  `validators/runner.py`.
- Add or update tests in `tests/` for any behavior change; `python -m pytest -q` must stay green.

## PR checklist

Before requesting review, confirm:

- [ ] `python scripts/validate_config.py` → all files valid
- [ ] `python scripts/validate_cross_level.py` → 0 violations
- [ ] `python scripts/smoke_test.py` → passes (if you touched schemas/fixtures)
- [ ] `python -m pytest -q` → green (if you touched `resolver/` or `validators/`)
- [ ] No plaintext secret anywhere — only `*Ref` or username-only
- [ ] No field mirrored across levels; override files exist only for real deviations
- [ ] New tenant ids are in `platform/tenant-catalog.yaml`
- [ ] Architecture/ADR/reference docs updated if you changed a schema or the resolver

CI (`.github/workflows/validate-config.yml`) runs the first three on every PR touching
`platform/**`, `clusters/**`, `schemas/**`, `scripts/**`, `validators/**`, or fixtures.
