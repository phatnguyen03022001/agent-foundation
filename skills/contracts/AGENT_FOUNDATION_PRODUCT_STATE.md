# Agent Foundation Product State

This contract is the canonical target-owned T2 product-state contract for `phatnguyen03022001/agent-foundation`. Its machine-readable object is the repository-root [`product-state.json`](../../product-state.json).

It is distinct from [Agent Foundation Product Architecture Boundaries](AGENT_FOUNDATION_PRODUCT_ARCHITECTURE.md), which remains the accepted T1 owner of product-capability architecture, and from [Foundation Architecture](FOUNDATION_ARCHITECTURE.md), which remains the generic owner of Foundation governance/control-plane semantics. T2 does not change either contract's ownership boundaries.

`product-state.json` is target-specific to this repository. It is not a universal Foundation manifest and does not create a requirement for other target repositories.

## T2 ownership

T2 owns exactly three current target-product facts:

1. the frozen current product scope revision;
2. stable feature identity and semantic-owner registration inside that scope;
3. current release-scope truth, including explicit unresolved release facts.

Product scope and release scope are separate. Freezing the product inventory does not imply that every registered feature is required by a particular release.

The product-state object is the sole machine-readable T2 owner. README links are navigation only. `profile/.agent/program.generated.json`, task/report/review artifacts, chat/session state, and Runtime/execution state are not product-scope, feature-registry, or release-scope authorities. PROGRAM remains derived planning data with authority `NONE`; task lifecycle cannot manufacture product state.

## Frozen product scope revision 1

Current product scope revision `1` is `FROZEN` at exactly four semantic features derived from the accepted T1 capability model:

| Feature | Semantic identity | Owning domain |
| --- | --- | --- |
| `F001` | `operator-and-architect-configuration` | `profile/` |
| `F002` | `governance-control-and-capability` | `skills/` |
| `F003` | `documentation-model-and-closure` | `documents/` |
| `F004` | `engineering-assurance` | `standards/` |

These identities come from T1 semantics, not directory spelling alone. A directory name does not create a feature.

For revision 1, all of the following must agree exactly:

- `features.total == 4`;
- exactly four registered feature objects exist;
- feature IDs are unique and exactly `F001` through `F004`;
- semantic names are unique and match the table above;
- each feature maps to exactly the owning domain above.

Adding, removing, renaming, re-identifying, or changing the semantic owner of a registered feature changes product scope. Because revision 1 is frozen, such a change requires an explicitly authorized future product-scope revision; it must not be silently folded into revision 1.

## Current release scope

Current release scope is `OPEN`.

Repository evidence does not establish one unified `agent-foundation` release/tag identity or one authoritative required-feature set. Domain-local document/standard versions, task protocol versions, Runtime versions, or other component-local identities do not become a repository-wide release identity.

Therefore the current machine-readable release object must preserve:

- `release.status == "OPEN"`;
- `release.id == null`;
- `release.id_resolution == "UNKNOWN"`;
- `release.required_feature_ids == null`;
- `release.required_feature_ids_resolution == "UNKNOWN"`.

`UNKNOWN` means unresolved from current target authority. It is not equivalent to an empty release, an empty required-feature set, `FROZEN`, `PASS`, `DONE`, or release readiness. In particular, `required_feature_ids: []` is invalid while required release scope is unresolved.

A future release identity or required-feature set needs exact target authority. T2 does not infer either from the frozen product inventory.

## Machine-readable shape

The current `product-state.json` schema version is `1`. It contains only:

- target repository identity;
- product-scope revision and freeze status;
- the feature count and exact registered feature identity/name/owner triples;
- release-scope status and explicit unresolved release facts.

Unknown fields are rejected by deterministic validation. This keeps the registry an inventory and release-scope truth object rather than an operational store.

## T2 / T3 boundary

T2 does not own or persist feature lifecycle state. The machine-readable product state must not contain or derive:

- feature state or lifecycle state;
- feature gates or gate applicability;
- verification/readiness state;
- global/system gates;
- project phase, progression selection, or completion percentage;
- earliest-blocker selection;
- task/report/review references;
- execution attempts, process IDs, raw tool output, terminal logs, prompts, chat IDs, model IDs, arbitrary TODOs, or implementation diary data.

Those facts are outside T2. T3, if separately authorized, may define evidence/gate-derived lifecycle semantics without retroactively turning T2 into a lifecycle-state owner.

## Freeze and reconstruction invariants

The current T2 truth is reconstructable from canonical repository state without one initiating chat/session.

```text
PRODUCT SCOPE != RELEASE SCOPE
FROZEN PRODUCT INVENTORY != RELEASE REQUIRED-FEATURE SET
UNKNOWN != EMPTY
PROGRAM != PRODUCT STATE
TASK LIFECYCLE != PRODUCT STATE
EXECUTION/UI STATE != PRODUCT STATE
T2 REGISTRY != FEATURE LIFECYCLE STATE
```
