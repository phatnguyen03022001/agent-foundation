# Agent Foundation Product State

This contract is the canonical target-owned T2+T3 product-state contract for `phatnguyen03022001/agent-foundation`. Its sole machine-readable object is the repository-root [`product-state.json`](../../product-state.json).

It is distinct from [Agent Foundation Product Architecture Boundaries](AGENT_FOUNDATION_PRODUCT_ARCHITECTURE.md), which remains the accepted T1 owner of product-capability architecture, and from [Foundation Architecture](FOUNDATION_ARCHITECTURE.md), which remains the generic owner of Foundation governance/control-plane semantics. T3 does not change either contract's ownership boundaries.

`product-state.json` is target-specific to this repository. It is not a universal Foundation manifest and does not create a requirement for other target repositories.

T3 evolves, rather than replaces, the canonical target-owned T2 product-state contract. Product scope and release scope are separate. PROGRAM remains derived planning data with authority `NONE`; task lifecycle cannot manufacture product state.

## Ownership

T2 remains the owner of:

1. frozen current product scope revision;
2. stable feature identity and semantic-owner registration;
3. current release-scope truth, including explicit unresolved release facts.

T3 adds, in the same object and contract:

1. one explicit ordered lifecycle per registered feature;
2. inspectable evidence references for each gate;
3. deterministic `derived_state` projection;
4. bounded forward-only regression semantics.

There is no second feature-state file or lifecycle authority. `derived_state` is validated projection, never independently authored truth.
## Frozen product scope revision 1

Current product scope revision `1` remains `FROZEN` at exactly four semantic features:

| Feature | Semantic identity | Owning domain |
| --- | --- | --- |
| `F001` | `operator-and-architect-configuration` | `profile/` |
| `F002` | `governance-control-and-capability` | `skills/` |
| `F003` | `documentation-model-and-closure` | `documents/` |
| `F004` | `engineering-assurance` | `standards/` |

The identity, semantic name, owner, count, and ordering are unchanged from T2. Adding, removing, renaming, re-identifying, or changing the semantic owner still requires an explicitly authorized future product-scope revision.

## Current release scope

Current release scope remains `OPEN`:

- `release.id == null`;
- `release.id_resolution == "UNKNOWN"`;
- `release.required_feature_ids == null`;
- `release.required_feature_ids_resolution == "UNKNOWN"`.

Frozen product inventory does not imply a release identity or required-feature set. While these release facts remain unresolved, no feature may pass `release_readiness` or `production_acceptance`, so no current feature may exceed `VERIFIED`.
## Schema version 2

Each registered feature has exactly one `lifecycle` object containing exactly:

- `gates`;
- `derived_state`;
- `regression`.

The lifecycle has exactly seven gates in this order:

1. `scope`
2. `specification`
3. `implementation`
4. `integration`
5. `verification`
6. `release_readiness`
7. `production_acceptance`

Each gate contains exactly `name`, `status`, `evidence_refs`, and `reason`. Valid status values are `PASS | FAIL | PENDING | N/A | UNKNOWN`.

`PASS` requires at least one inspectable persisted evidence reference and a null reason. `FAIL` requires attributable evidence plus a non-empty reason. `PENDING`, `UNKNOWN`, and `N/A` require a non-empty reason. `N/A` is exclusion, not success, and never advances lifecycle.

Evidence references are bounded canonical repository-relative file paths. Missing, stale, contradictory, inaccessible, or non-attributable evidence is not PASS. `product-state.json` cannot evidence itself. TASK-0020 task/report/review artifacts cannot evidence the candidate that precedes them.
## Evidence attribution

A current source file, contract, schema, or implementation artifact may directly prove static scope, specification, implementation, or integration facts when its content establishes that claim.

Verification is stronger. A verifier or test definition alone does not prove that verification ran or passed. `verification: PASS` requires persisted result evidence and current owning-domain evidence. Historical task/report lifecycle status alone is insufficient; only concrete result evidence inside an immutable historical artifact can contribute.

For historical verification evidence, deterministic validation extracts the historical implementation candidate and proves the current owning subtree is byte-equivalent to that candidate. If the owner changed afterward, the historical result is stale for current verification.

Fresh Executor terminal output qualifies TASK-0020 itself but does not become hidden feature-state evidence. When T3 changes feature-owned bytes and no pre-existing persisted result covers those exact final bytes, that feature's verification gate remains not-PASS.

## Deterministic derivation

Lifecycle advancement is the longest consecutive PASS prefix:

| Consecutive PASS gates | Derived state |
| --- | --- |
| `scope` | `PLANNED` |
| through `specification` | `SPEC_READY` |
| through `implementation` | `IMPLEMENTING` |
| through `integration` | `INTEGRATED` |
| through `verification` | `VERIFIED` |
| through `release_readiness` | `RELEASE_READY` |
| through `production_acceptance` | `LIVE` |

The first gate that is not PASS stops advancement. Later PASS is invalid while an earlier prerequisite is not PASS. The validator recomputes `derived_state` and rejects disagreement.
## Current conservative feature state

The current evidence-derived projection is:

| Feature | Scope | Spec | Impl | Integration | Verification | Release readiness | Production acceptance | Derived |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `F001` | PASS | PASS | PASS | PASS | PASS | UNKNOWN | UNKNOWN | `VERIFIED` |
| `F002` | PASS | PASS | PASS | PASS | UNKNOWN | UNKNOWN | UNKNOWN | `INTEGRATED` |
| `F003` | PASS | PASS | PASS | PASS | PASS | UNKNOWN | UNKNOWN | `VERIFIED` |
| `F004` | PASS | PASS | PASS | PASS | UNKNOWN | UNKNOWN | UNKNOWN | `INTEGRATED` |

F001 has persisted bootstrap validation/regression evidence from TASK-0015 whose implementation candidate still has the exact current `profile/` tree.

F002 is intentionally not VERIFIED. T3 changes `skills/` bytes, including this contract, the validator, and its regressions. No pre-existing persisted result independently covers those final bytes.

F003 has persisted document validator evidence from TASK-0004 and the current `documents/` tree is still exact to that evidenced candidate.

F004 is intentionally not VERIFIED. TASK-0004 persisted the exact current `standards/` tree but records the standards verifier as capability-blocked because PyYAML was unavailable; that is evidence for UNKNOWN, not PASS.
## Forward-only transition semantics

Normal lifecycle movement is forward-only. A schema-2 state that moves a feature backward requires one current `regression` record containing exactly:

- `from_state`;
- `to_state`;
- non-empty `reason`;
- inspectable `evidence_refs`.

The record must match the actual previous and current derived states. A same-state or forward transition must keep `regression: null`; regression is not a history log. Initial schema-1 to schema-2 adoption also uses `regression: null`.

## T3 boundary

T3 does not implement:

- global/system gates;
- project phase or aggregate release phase/state;
- progress metrics or earliest-blocker selection;
- Architect progression integration;
- scheduler, daemon, queue, or workflow engine;
- execution/UI recovery redesign;
- adoption closure;
- future task artifacts.

PROGRAM remains derived navigation with authority `NONE`. Task/report/review state, chat/UI state, and Runtime execution state do not manufacture product state.

```text
PRODUCT SCOPE != RELEASE SCOPE
FROZEN PRODUCT INVENTORY != RELEASE REQUIRED-FEATURE SET
UNKNOWN != PASS
N/A != PASS
TEST DEFINITION != TEST RESULT
TASK LIFECYCLE != FEATURE STATE
DERIVED STATE == VALIDATED GATE PROJECTION
```
