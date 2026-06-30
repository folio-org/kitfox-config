# Architecture Decision Records

The load-bearing decisions behind `kitfox-config`, each as a short ADR: context → decision →
rationale → consequences. They are extracted from the ~30 numbered corrections and the
design principles in `design-artifacts/B-Trigger-Map/kitfox-config-schema-architecture.md`
(cited as “§N”) and the two chain-trace reviews.

These records explain **why** the schema is shaped the way it is. For **what** the fields
are, see [../../schema-reference.md](../../schema-reference.md); for **how** resolution
works, [../../resolver-reference.md](../../resolver-reference.md).

| ADR | Decision | Anchored in |
|-----|----------|-------------|
| [0001](0001-exclude-model-for-apps.md) | Exclude-model for applications — no include pool | §0, §3, §4, correction #1 |
| [0002](0002-config-as-data-overlays.md) | Feature behavior is declarative overlays, not pipeline branches | §2.2b, correction #2 |
| [0003](0003-kiss-one-concept-per-entity.md) | KISS — `platform`/`configType` on the namespace only; cluster is pure infra | §2.5, corrections #3/#4 |
| [0004](0004-tenant-catalog-and-dataset-profiles.md) | Tenant catalog (identity once) + dataset profiles | §2.4, §2.4b, correction #8 |
| [0005](0005-operations-modifiers-vs-selectors.md) | Operations: modifiers in config, selectors in pipeline | §0, §5.3, corrections #9/#25 |
| [0006](0006-credential-free.md) | Credential-free — every secret is a `*Ref` or convention-derived | §0, corrections #14/#22/#24 |
| [0007](0007-edge-mostly-derived.md) | Edge config is mostly derived; only the account + capabilities are config | §2.4c, §5.3, correction #22 |
| [0008](0008-tenant-type-ruleset.md) | Tenant-type ruleset with `secure` as an orthogonal boolean | §4 model note |

All ADRs are **Accepted** and reflected in the Iteration-1 code.
