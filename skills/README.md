# Foundation skills

A deliberately curated library of reusable internal agent skills plus deterministic contracts, templates, and protocols for software engineering across repositories. The active internal taxonomy is derived from [`.agent/rationalization.json`](.agent/rationalization.json).

`skills/` defines **HOW WE WORK**. A target repository defines **WHAT THE PRODUCT IS** and stores live tasks/evidence. Supported protocol version is **3**; existing valid historical protocol-v3 artifacts remain valid canonical evidence even when their serialization is outside the current constrained validator subset and therefore need not be parseable by every later constrained validator.

## Governance ownership

[Foundation Architecture](contracts/FOUNDATION_ARCHITECTURE.md) is the single canonical generic owner for the three-layer Foundation model and L1 capability-control/continuity semantics. When `agent-foundation` is itself the target, [Agent Foundation Product Architecture Boundaries](contracts/AGENT_FOUNDATION_PRODUCT_ARCHITECTURE.md) separately owns its T1 target-product capability/dependency boundaries, while [Agent Foundation Product State](contracts/AGENT_FOUNDATION_PRODUCT_STATE.md) owns the distinct T2 target product-scope, feature-registry, and release-scope contract. [Task Protocol](protocols/TASK_PROTOCOL.md) remains the L0 semantic owner for reusable cross-role task-governance semantics. Architect and Executor skills own role-local procedure and safety boundaries; contracts own artifact-specific obligations; templates are example/default shapes. Protocol semantic validity and current validator serialization support are distinct: the constrained validator mechanically enforces supported structure only for serialization inside its deterministic subset. This README is discovery and navigation, not a second normative protocol.

The normal flow is planning and exact handoff → restrictive execution and Executor report → Architect review → exact-SHA verification when required → explicit promotion → separately authorized release. Binding, lifecycle, authority/capability separation, continuation, promotion lineage, and release semantics are defined only by the Task Protocol.

`PROGRAM` remains presentation only for ordered repository-local tasks. It may be rendered from the optional machine-readable [generated program template](templates/program.generated.json), which is derived planning data with authority `NONE`: it records immutable synthesis identities, validated coverage/dependencies, and Architect judgment, but never replaces repository-local task authority or authorizes execution, lifecycle mutation, review, verification, promotion, or release. See the Task Protocol for the governing semantics.

## Operator-facing presentation

TASK LAUNCH is operator-facing presentation only. It is non-authoritative, is not persisted as task state, and remains separate from `PROMPT TO COPY`.

`PROMPT TO COPY` is a compact authority locator to the canonical repository/task/base/phase authority, not duplicated authority. Generic Foundation `skills/` guidance does not prescribe TASK LAUNCH field names, ordering, language, executor menus, model/effort display, or other operator-profile presentation choices.

## Maintenance and frozen taxonomy

Mature governance may correctly return NO CHANGE REQUIRED when no material reproduced problem exists. Corrective maintenance uses the smallest safe change. The rationalization-derived internal taxonomy remains closed to ad hoc additions by default; admission reasoning is owned by [simplicity](simplicity/SKILL.md), while this README remains discovery/navigation rather than a second ownership registry.

## Curated skill catalog

<!-- SKILL_CATALOG_START -->
| Skill | Type | Decision domain / trigger |
| --- | --- | --- |
| `architect` | core | repository-bound routing/governance, planning authority, task creation, handoffs, and final review judgment |
| `executor` | core | controlled execution of one approved task revision against one exact repository/base |
| `simplicity` | governance | Foundation change admission, taxonomy closure, and anti-overengineering boundaries |
| `adversarial-audit` | assurance | stale state, retries, partial effects, process death, and governance-bypass pressure |
| `security-review` | delta | Foundation threat-path, trust/authority-boundary, and security-evidence semantics over exact-pinned ECC generic HOW |
| `verification` | delta | acceptance/evidence, exact-candidate, authoritative-verifier, and execution-bundle semantics over exact-pinned ECC generic HOW |
| `reliability` | engineering | operability through dependency failure, retries/backpressure, recovery, rollout/rollback, and production incidents |
<!-- SKILL_CATALOG_END -->

The validator recursively discovers every `SKILL.md` and requires exact agreement with the `KEEP_FOUNDATION_SPECIFIC` plus `THIN_DELTA` records in `.agent/rationalization.json`. A replaced/retired implementation that still exists, an omitted retained/thin skill, or an extra hidden/nested skill is an error.

## Canonical v3 artifacts

There is one task model, not task-lite/task-compact variants. Navigation:

- [templates/task.yaml](templates/task.yaml): Architect-owned implementation-authority shape;
- [templates/handoff.yaml](templates/handoff.yaml): exact Architect-to-Executor locator/authorization shape;
- [templates/report.yaml](templates/report.yaml): Executor-owned evidence shape;
- [templates/review.yaml](templates/review.yaml): Architect-owned judgment shape;
- [templates/continuation.yaml](templates/continuation.yaml): post-review exact-identity continuation shape;
- [templates/execution-attempt.yaml](templates/execution-attempt.yaml): local execution-attempt telemetry example with authority `NONE`;
- [templates/program.generated.json](templates/program.generated.json): optional derived generated-planning snapshot with authority `NONE`, never task/lifecycle authority;
- [contracts/FOUNDATION_ARCHITECTURE.md](contracts/FOUNDATION_ARCHITECTURE.md): three-layer Foundation and L1 control/continuity contract;
- [contracts/AGENT_FOUNDATION_PRODUCT_ARCHITECTURE.md](contracts/AGENT_FOUNDATION_PRODUCT_ARCHITECTURE.md): target-owned T1 product-capability, dependency, cross-cutting, telemetry, and extraction boundaries for agent-foundation itself;
- [contracts/AGENT_FOUNDATION_PRODUCT_STATE.md](contracts/AGENT_FOUNDATION_PRODUCT_STATE.md): target-owned T2 product-scope, stable feature-registry, and truthful release-scope contract for agent-foundation itself;
- [contracts/EXECUTION_CONTINUITY.md](contracts/EXECUTION_CONTINUITY.md): local-only lease/checkpoint truth model and recovery boundary;
- [scripts/execution_attempt.py](scripts/execution_attempt.py): stdlib-only local Git-metadata attempt operations;
- [contracts/IMPLEMENTATION_CONTRACT.md](contracts/IMPLEMENTATION_CONTRACT.md): task artifact obligations;
- [contracts/IMPLEMENTATION_REPORT.md](contracts/IMPLEMENTATION_REPORT.md): report artifact obligations;
- [contracts/ARCHITECT_REVIEW.md](contracts/ARCHITECT_REVIEW.md): review artifact obligations;
- [protocols/TASK_PROTOCOL.md](protocols/TASK_PROTOCOL.md): reusable cross-role semantic authority.

## External capability discovery

[External capability plane](.agent/external-capabilities/README.md) provides the Foundation-owned registry, immutable metadata snapshots, and aggregate discovery catalog for approved external ecosystems. The catalog is inert navigation data with authority `NONE`; it does not add trust, installation, authorization, or behavioral activation. After exact target-repository truth and repo-native conventions, the exact-pinned ECC harness is the default source for generic engineering HOW; its indexed skills, commands, agents, and deterministic manifest/catalog/install metadata remain subordinate to Foundation governance and current target authority.

Use `python3 -B scripts/sync_external_capabilities.py --check` to regenerate the pinned metadata in memory and verify byte-identical committed output. For an unfamiliar bounded need, use the existing external-plane procedure to query committed ECC metadata with `--query`, reject incompatible candidates under target truth, then `--resolve` one explicit surface/title before reading only relevant pinned source sections. ECC rule guidance uses the [scoped target-owned rule-adoption procedure](.agent/external-capabilities/README.md#scoped-target-owned-rule-adoption) and remains advisory until target-owned authority explicitly scopes and integrates it. The ECC CLI is optional because exact pinned source/snapshot/catalog metadata is the fail-closed resolution path when the CLI is absent. Advancing tracking refs requires an explicit approved Foundation task and the script's `--refresh --task <path>` gate.

## Validation

The stdlib-only validator checks the exact rationalization-derived taxonomy, frontmatter/catalog, constrained YAML, canonical templates, generated-program JSON shape/graph/coverage invariants, protocol-v3 compatibility, required doctrine tokens, and internal links. Target-repository workflow configuration remains target-owned; Foundation Git authority, publication, promotion, and release semantics are owned by the [Task Protocol](protocols/TASK_PROTOCOL.md), while generic Git/GitHub HOW routes through the exact-pinned external capability seam.

Validate one authored artifact without changing it with `python3 scripts/validate_skill_library.py --artifact report .agent/tasks/TASK-0043/report.yaml`; replace `report` with `task` or `review` as needed.

For an authorized local target that supplies an env example, check its operator env without changing it using `python3 scripts/reconcile_env.py --example .env.example --env .env`; add `--write` to reconcile that one file. The supported subset is single-line identifier assignments (with optional `export`), unquoted/single/double-quoted values, comments, and blanks; duplicate, multiline, ambiguous, symlink, and non-regular inputs fail closed. Exit `0` means current with no placeholder, `1` means reconciliation or operator configuration remains needed, and `2` means input/write failure. Missing keys stay as quoted `<thiếu key>` placeholders, which keep startup blocked until the operator supplies configuration. The command preserves opaque values but cannot certify provider credentials.
