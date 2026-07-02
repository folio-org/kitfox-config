# ADR-0009 — Deployment profile owns the full per-module Helm values

**Status:** Accepted · **Supersedes:** the §2.6b "static module config → chart `values.yaml`" rule (correction #7, row 1) · **Anchored in:** §2.2, §2.6b, decision D1=B

## Context

§2.6b ("Per-module config — three homes") originally routed *static* module
config (default probes, JVM, resources, `spring.cache.type`, ingress/service
shape, integrations wiring) to the `folio-helm-v2` chart `values.yaml` as the
chart default, leaving only per-namespace deviations and feature-driven env in
kitfox-config. In practice the authoritative per-environment values already live
in `pipelines-shared-library/resources/helm/{development,testing,performance,release}.yaml`
— a full module map per environment, ~3.8k-5.3k lines each. Splitting "static vs
deviation" across two repos (chart + config) means no single source of truth for
what a module actually runs with in a given environment, and keeps the pipeline
reaching into chart internals.

## Decision

**The deployment profile owns the full per-module Helm values per profile.**
`platform/deployment-profiles/{configType}.yaml` carries a `modules:` map keyed by
module name; its value is the module's Helm values (permissive shape). The four
`resources/helm/*.yaml` environment files are transferred verbatim (credential-free
already — `existingSecret` references only) into the matching profile's `modules:`.

The resolver consumes this as the **base** module layer:
`defaults → deployment-profile (incl. modules) → cluster → namespace`, then feature
overlays, then `namespace.modules.<name>` overrides. The chart `values.yaml` retains
only true chart-shipped defaults; kitfox-config no longer relies on it for
per-environment module values.

Credential-free is preserved by convention: secrets are k8s `existingSecret`
references, never plaintext. The transfer tool (`scripts/transfer_helm_profiles.py`)
asserts no plaintext secret value before writing.

## Consequences

- One source of truth per environment for module values, in config, versioned and gated.
- The profile files are large; that is acceptable — they are generated from the
  source helm files and validated by the schema gate.
- The §2.6b merge precedence gains an explicit base layer (deployment-profile
  `modules`). Per-namespace `modules.<name>` and feature overlays still override.
- Follow-up: the remaining `folioHelm.groovy` switch (the static-config branch)
  is dismantled in the pipeline-redesign phase, now that config owns the values.
