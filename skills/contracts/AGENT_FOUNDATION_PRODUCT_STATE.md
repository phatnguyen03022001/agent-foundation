# Agent Foundation Product State

This contract is the canonical target-owned T2+T3+T4 product-state contract for `phatnguyen03022001/agent-foundation`. Its sole machine-readable object is the repository-root [`product-state.json`](../../product-state.json).

It is distinct from [Agent Foundation Product Architecture Boundaries](AGENT_FOUNDATION_PRODUCT_ARCHITECTURE.md), which remains the accepted T1 owner of product-capability architecture, and from [Foundation Architecture](FOUNDATION_ARCHITECTURE.md), which remains the generic owner of Foundation governance/control-plane semantics. T3 does not change either contract's ownership boundaries.

`product-state.json` is target-specific to this repository. It is not a universal Foundation manifest and does not create a requirement for other target repositories.

T3 evolves, rather than replaces, the canonical target-owned T2 product-state contract. T4 evolves that same single authority in place with global gates and deterministic project progression. Product scope and release scope are separate. PROGRAM remains derived planning data with authority `NONE`; task lifecycle cannot manufacture product state.

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

T4 adds, in the same object and contract:

1. canonical global system-gate groups and evidence-backed leaf truth;
2. mechanically derived aggregate statuses;
3. one validated `derived_project.phase` projection;
4. one pure deterministic earliest-blocker resolver contract.

There is no second feature-state, project-state, system-gate, or progression authority. `derived_state`, aggregate statuses, and project phase are validated projections, never independently authored truth.

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
## Schema version 3

Schema 3 preserves the accepted T3 feature lifecycle exactly and extends the same object with `system_gates` and `derived_project`.

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

F001's profile-bootstrap result is persisted in `.agent/tasks/TASK-0024/report.yaml`, whose `execution.final_execution_head` is `dbdff63fb2e9572ed9ba9748de046f4c35e33c23`. Its recognized local and remote bootstrap evidence both record `OPM_BOOTSTRAP = TRUE`. The current `profile/` tree is byte-equivalent to that commit, and the canonical historical-evidence helper accepts the report for owner `profile/`. F001 is therefore `VERIFIED` with verification `PASS`; its verification references include the persisted report and current profile bootstrap artifacts, and its regression is null. This refresh consumes persisted result evidence; current terminal output, TASK-0025, and task/review status do not self-attest verification.

F002 is intentionally not VERIFIED. T3 changes `skills/` bytes, including this contract, the validator, and its regressions. No pre-existing persisted result independently covers those final bytes.

F003 has persisted document validator evidence from TASK-0004 and the current `documents/` tree is still exact to that evidenced candidate.

F004 is intentionally not VERIFIED. TASK-0004 persisted the exact current `standards/` tree but records the standards verifier as capability-blocked because PyYAML was unavailable; that is evidence for UNKNOWN, not PASS.
## Forward-only transition semantics

Normal lifecycle movement is forward-only. A schema-2 or schema-3 state that moves a feature backward requires one current `regression` record containing exactly:

- `from_state`;
- `to_state`;
- non-empty `reason`;
- inspectable `evidence_refs`.

The record must match the actual previous and current derived states. A same-state or forward transition must keep `regression: null`; regression is not a history log. Initial schema-1 to schema-2 adoption also uses `regression: null`.

## T4 global system gates

Schema 3 adds exactly one `system_gates` object with the canonical groups and leaf order below:

- `foundation`: `architecture`, `dependency_rules`, `test_infrastructure`, `telemetry`, `security`, `ci`;
- `integration`: `cross_feature_flows`, `contracts`, `data_consistency`, `authorization`, `external_dependencies`;
- `verification`: `unit`, `integration`, `contract`, `e2e`, `security`, `failure_paths`;
- `hardening`: `performance`, `capacity`, `security`, `privacy`, `observability`, `slo`, `alerts`, `rollback`, `backup_restore`, `disaster_recovery`, `cost`;
- `production`: `deployment`, `smoke_test`, `critical_journeys`, `telemetry`, `operational_readiness`.

Every leaf contains exactly `name`, `status`, `evidence_refs`, and `reason`. The evidence rules are fail-closed: PASS needs attributable persisted evidence; N/A needs explicit target-specific justification; missing, stale, contradictory, inaccessible, or non-attributable evidence is UNKNOWN. TASK-0021 task/report/review output cannot self-attest these gates.

For non-production groups, `status` is derived from the canonical leaves. Production stores `acceptance_status`, derived only from `deployment`, `smoke_test`, `critical_journeys`, and `telemetry`. `operational_readiness` is a separate leaf checked independently by project-phase derivation.

Aggregate precedence is exact:

1. any FAIL -> FAIL;
2. otherwise any UNKNOWN -> UNKNOWN;
3. otherwise any PENDING -> PENDING;
4. otherwise PASS only when every applicable leaf is PASS and every N/A leaf is explicitly justified.

N/A is exclusion, not PASS. At least one applicable non-N/A leaf is required; an all-N/A aggregate is invalid and cannot manufacture PASS.

The current audit is intentionally conservative. Architecture, dependency rules, test infrastructure, integration contracts, and exact-pinned external dependency state have attributable persisted/static evidence. Other global concerns remain UNKNOWN where the repository does not contain sufficient attributable evidence. TASK-0021 execution results qualify this task but do not retroactively manufacture system-gate PASS.

## Deterministic project phase

Schema 3 also adds exactly one `derived_project` object containing only `phase`. It is a projection: the validator recomputes it and rejects disagreement.

Phase precedence is exact:

1. release not `FROZEN` or required release feature set unresolved -> `P0_SCOPE`;
2. foundation aggregate not PASS -> `P1_FOUNDATION`;
3. any required feature below `INTEGRATED` -> `P2_FEATURE_BUILD`;
4. integration aggregate not PASS -> `P3_INTEGRATION`;
5. any required feature below `VERIFIED` or verification aggregate not PASS -> `P4_VERIFICATION`;
6. any required feature below `RELEASE_READY` or hardening aggregate not PASS -> `P5_HARDENING`;
7. any required feature not `LIVE`, production acceptance not PASS, or `operational_readiness` not PASS -> `P6_RELEASE_READY`;
8. otherwise -> `P7_LIVE`.

No percentage, subjective override, task status, or later evidence can skip an earlier blocker. The current release remains OPEN with unresolved required features, so the current phase is exactly `P0_SCOPE`.

## Deterministic earliest blocker

The resolver is a pure projection and is not Architect behavior.

Tie-breaking mirrors phase precedence:

- P0: `release.status`, then `required_feature_ids_resolution`;
- P1: foundation leaves in canonical order;
- P2: required features normalized to canonical product-registry order, then the earliest unmet lifecycle gate through integration;
- P3: integration leaves in canonical order;
- P4: required features below VERIFIED in registry order before verification leaves;
- P5: required features below RELEASE_READY in registry order before hardening leaves;
- P6: required features not LIVE in registry order before production-acceptance leaves, then `operational_readiness`.

Unknown or foreign required feature IDs fail closed. Caller-provided feature ordering never overrides the canonical F001-F004 registry order. The current earliest blocker is exactly `release.status`.

## T4 boundary

T4 does not implement Architect progression consumption, task generation, execution/UI recovery redesign, adoption/dogfood closure, a scheduler, daemon, queue, workflow engine, central state database, or another product-state authority.

PROGRAM remains derived navigation with authority `NONE`. Task/report/review state, chat/UI state, and Runtime execution state do not manufacture product state.

```text
PRODUCT SCOPE != RELEASE SCOPE
FROZEN PRODUCT INVENTORY != RELEASE REQUIRED-FEATURE SET
UNKNOWN != PASS
N/A != PASS
ALL-N/A != PASS
TEST DEFINITION != TEST RESULT
TASK LIFECYCLE != FEATURE OR SYSTEM-GATE STATE
DERIVED FEATURE STATE == VALIDATED LIFECYCLE PROJECTION
DERIVED PROJECT PHASE == VALIDATED RELEASE + FEATURE + SYSTEM-GATE PROJECTION
EARLIEST BLOCKER == DETERMINISTIC PHASE-ORDERED PROJECTION
```
