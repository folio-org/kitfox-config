# ADR-0005 — Operations: modifiers in config, selectors in pipeline

**Status:** Accepted · **Anchored in:** §0, §5.3, corrections #9/#25, NFR4

## Context

`CreateNamespaceParameters` mixes two very different kinds of operational input. Some tune
*how* a deploy behaves (`runSanityCheck`, `uiBuild`, `skipReindex`, install flags like
`simulate`/`async`). Others pick *which* operation runs and can change provisioned
infrastructure: `type` (`full`/`terraform`/`update`) is passed to Terraform as `setup_type`
and **gates whether RDS snapshot-restore resources are created** (`postgresql.tf:558,571`);
`namespaceOnly` stops after Terraform; `dmSnapshot` names a migration snapshot. Chain-trace #2
flagged that treating `type` as ephemeral "how it runs" desired-state was wrong — a per-run
`type` override changes real infra.

## Decision

Split operational inputs by nature:

- **Modifiers → config defaults, run-overridable (ephemeral).** `namespace.operations.*`
  (`uiBuild`, `runSanityCheck`, `skipReindex`, `entitlementApproach`, `setBaseUrl`) and
  per-tenant `install.*` (`simulate`, `reinstall`, `async`, `ignoreErrors`, `purgeOnRollback`,
  `loadReference`, `loadSample`) carry config **defaults**. A run may override any of them for
  that run only — the override is ephemeral and never written back.
- **Selectors → pipeline-only inputs, never config.** `type`, `namespaceOnly`, `dmSnapshot`
  have **no** `operations` field. They are run params.
- **Approval/governance gates → pipeline-only.** `kitfoxApproval` gates (e.g. for `pgType=aws`,
  or `etesting`/`dataset`/`release`) are CI guardrails like environment-protection rules, not
  namespace desired-state.

`namespace.schema.json` enforces this: `operations` is `additionalProperties: false` over the
modifier keys, so `type`/`namespaceOnly`/`dmSnapshot` are **rejected** if anyone tries to add
them.

## Rationale

- Desired-state should describe *what* a namespace is, not *which one-off operation* an
  operator is running today. Selectors that change provisioned infra are runtime decisions,
  not config.
- Keeping modifiers in config (as defaults) preserves the convenient "this namespace usually
  runs the sanity check" behavior while still allowing a per-run opt-out.

## Consequences

- The pipeline owns the *override channel* for modifiers, not the values; and owns selectors
  and approval gates entirely (§5.3).
- The contract summary (§5.4): `config → WHAT + default modifiers`;
  `descriptor/FAR → WHICH versions`; `Terraform → WHERE + secrets`;
  `run params → selectors + ephemeral modifier overrides`.
- This is why `operations` has exactly five keys and no `type`. If a future need makes a
  selector legitimately part of desired-state, it gets its own ADR — it does not quietly join
  `operations`.
