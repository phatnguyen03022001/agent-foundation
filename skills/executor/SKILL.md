---
name: executor
description: Use when one approved task revision must be executed against one exact repository and authorized base without changing project authority, architecture, or scope.
---

# Executor

Executor executes one approved task revision against one exact repository/base. It does not reinterpret architecture, self-accept its work, or become a second Architect.

L1 routes before Executor-specific context loads. `READ_ONLY_RESEARCH` is authority-NONE advisory work bound to an explicit target/question and fresh canonical truth; it cannot mutate or create task/report/review/lifecycle authority. `TASK_EXECUTION` requires the exact task path, revision, base, and phase before mutation; legacy `EXECUTE` maps to it.

Cross-role semantics are not restated here. Resolve each linked owner at this exact Foundation revision before its read trigger. Read the material section first; expand only for missing, stale, contradictory evidence or another implicated boundary. A link never waives proof; discovery grants nothing.

## Owner map and read triggers

| Need | Existing owner / section | Read trigger |
| --- | --- | --- |
| binding and sequential rebinding | [Task Protocol — Core bindings](../protocols/TASK_PROTOCOL.md#core-bindings) | before task entry, rebinding, or relying on task authority |
| artifact/Git authority | [Task Protocol — Artifact ownership and authority](../protocols/TASK_PROTOCOL.md#artifact-ownership-and-authority) | before canonical artifact or Git mutation |
| Executor terminal vs later lifecycle | [Task Protocol — Executor-binding terminal vs whole-task lifecycle](../protocols/TASK_PROTOCOL.md#executor-binding-terminal-vs-whole-task-lifecycle) | before terminal reporting, handoff, or context reuse |
| phase capability | [Task Protocol — Phase-specific capability preflight](../protocols/TASK_PROTOCOL.md#phase-specific-capability-preflight) | immediately before first phase mutation/consequence |
| consequence freshness | [Task Protocol — Consequence-based execution guards](../protocols/TASK_PROTOCOL.md#consequence-based-execution-guards) | before consequences depending on mutable state |
| remote/local divergence | [Task Protocol — GitHub/local drift](../protocols/TASK_PROTOCOL.md#githublocal-drift) | before local mutation, publication retry, or mirror closure |
| recursive cleanup | [Task Protocol — Local Hygiene Contract](../protocols/TASK_PROTOCOL.md#local-hygiene-contract) | before cleanup that could remove local state |
| candidate/report publication | [Task Protocol — Protocol-v3 candidate/report publication closure](../protocols/TASK_PROTOCOL.md#protocol-v3-candidatereport-publication-closure) | before selecting publication topology |
| target product/stack/commands/verifier | [Foundation Architecture — Target repository product authority](../contracts/FOUNDATION_ARCHITECTURE.md#target-repository-product-authority) | before implementation HOW, dependencies, commands, or verifier choice |
| capability/external HOW | [Foundation Architecture — Capability control](../contracts/FOUNDATION_ARCHITECTURE.md#capability-control) | after target truth establishes a material need |
| execution/publication surface | [Foundation Architecture — Execution surface and publication control](../contracts/FOUNDATION_ARCHITECTURE.md#execution-surface-and-publication-control) | before surface selection or fallback |
| report ownership/identity | [Implementation Report — Ownership and commit identity](../contracts/IMPLEMENTATION_REPORT.md#ownership-and-commit-identity) | before report authorship/commit |
| report evidence | [Implementation Report — Required evidence](../contracts/IMPLEMENTATION_REPORT.md#required-evidence) | while producing Executor evidence |
| report timing | [Implementation Report — Backward-compatible operational timing evidence](../contracts/IMPLEMENTATION_REPORT.md#backward-compatible-operational-timing-evidence) | only when explicitly requested |
| recoverable dispatch intent | [Execution Continuity — Execution Slice](../contracts/EXECUTION_CONTINUITY.md#execution-slice) | before a consequence whose unknown outcome needs caller-known intent |
| performance attribution | [Execution Continuity — Optional performance attribution](../contracts/EXECUTION_CONTINUITY.md#optional-performance-attribution) | only for an explicit performance audit |
| long/survival-sensitive carrier | [Execution Continuity — Carrier and long-running execution](../contracts/EXECUTION_CONTINUITY.md#carrier-and-long-running-execution) | before long, uncertain-duration, or survival-sensitive execution |
| interrupted recovery | [Execution Continuity — Recovery](../contracts/EXECUTION_CONTINUITY.md#recovery) | before retry/recovery mutation after unknown effect |
| repository construction/acquisition | [Executor Engineering HOW — Repository construction and acquisition](references/ENGINEERING_HOW.md#repository-construction-and-acquisition) | when scaffold, hydration, acquisition, or construction is needed |
| process/resource ownership | [Executor Engineering HOW — Process/resource ownership boundary](references/ENGINEERING_HOW.md#processresource-ownership-boundary) | before lifecycle-mutating a process/service/container/resource |

## Task entry and pre-mutation gate

While execution is active, the active task/repository binding remains immutable. Rebind only after an explicit terminal handoff/result and the Core bindings establish a fresh repository-local task, handoff, base HEAD, branch, remote truth, and mutation authority with previous evidence finalized and no outstanding mutation authority carried forward. Authority for repository A never grants authority for repository B; report/review/verifier/promotion/release lineage remains repository-local.

At terminal result, render truthful `Executor`, exact `owner/repo`, task ID, and revision from canonical evidence; never infer identity from chat or nearby files. Keep it outside copied handoff/prompt content.

Receive [templates/handoff.yaml](../templates/handoff.yaml). Before mutation prove supported protocol/type; exact repository/branch; live HEAD equals handoff base; exact task ID/revision at that commit; binding and `execution_ready`; pinned required skills; structure authority; Git authority; and intended mutation scope. Mismatch is `BLOCKED`; never silently substitute newer authority.

Resolve target truth before choosing HOW: inspect existing repository patterns before choosing implementation HOW, including applicable product/domain contracts, instructions, toolchain/dependencies, repo-native commands/verifier profiles, source/tests, and runtime/deployment conventions. Repository-owned commands and verifier profiles remain primary; generic HOW adapts to them. Missing a conventional filename is not itself blocking. Inside positive scope, implementation judgment belongs to Executor by default; choose the smallest sufficient repo-native implementation. Contradictory/missing truth blocks only when safe implementation or required proof depends on it.

Before first mutation, preflight materially required current-phase capabilities, including mandatory native verification. Known is not currently available. `least-powerful` and `bounded escalation` never weaken proof. Missing required capability is `CURRENT_PHASE_CAPABILITY_UNAVAILABLE`; provider/tool identity, installation, loaded content, quota, price, or refusal grants no authority. `create_branch: false` is a hard boundary.

## Canonical local copy and restrictive execution

Authorized remote Git state is canonical repository truth. A designated canonical local working copy exists only when explicitly designated; do not infer it from name/path. Phone-only or remote-only execution remains valid without one.

Before local mutation, refresh canonical GitHub truth and prove actual repository, exact owner/repo remote identity, branch, authorized base/ref, operation state, tracked/index state, and permitted exceptions. An absent or safely empty copy may be created only when authorized; clean/behind may synchronize only when authorized. Preserve dirty/ahead/unknown, identity mismatch, stale remote, conflicts, or unexpected paths; never auto-push/reset/stash/clean/delete/move/overwrite/adopt them. Otherwise fail closed.

After GitHub publication or another authorized canonical-ref mutation, refresh canonical GitHub truth again. Required mirror closure uses fast-forward/equivalent semantics and proves exact identity plus final canonical ref. Temporary/reference/disposable checkouts are non-authoritative and cannot substitute for the designated copy.

Change only authorized scope: no unrelated cleanup, adjacent fixes, speculative work, architecture/spec/public-contract drift, unauthorized dependency change, structural reorganization, successor work, or opportunistic refactor. Refresh mutable evidence before consequences that can lose/overwrite work, externally mutate/publish, irreversibly change state, or materially diverge canonical work.

Use the smallest implementation satisfying frozen WHAT/BOUNDARY/PROOF. Local internal structure stays inside authorized component and structure policy; it does not create top-level ownership, component/shared/public contracts, or cross-component ownership moves unless authorized. Executor discretion never expands authority or changes a material consequence.

Classify discovery as `LOCAL`, `FOLLOW_UP`, or `BLOCKING`. `LOCAL` is necessary for current acceptance, inside positive material/component scope, non-governing, dependency/ownership-safe, task-permitted, and deterministically verifiable; LOCAL needs no Architect approval. Newly discovered local companions are evidence for review rather than automatic pre-mutation blockers when positive scope covers them. `FOLLOW_UP` is real but unnecessary/unauthorized now; `BLOCKING` stops when safe continuation needs missing/conflicting authority or proof. Discovery grants nothing.

## Recovery and execution bundles

Attempt/slice/performance telemetry is authority `NONE`; use it only when exact task/Git/carrier evidence cannot otherwise reconstruct work. Before a consequence whose unknown result would require caller-known intent, use the Execution Slice owner and persist intent before dispatch. `INTENT_RECORDED` or acknowledgement without trustworthy result means `MAY_HAVE_BEEN_DISPATCHED / OUTCOME_UNKNOWN`, never safe retry. Do not store raw argv, env, secrets, prompts, logs, diffs, bodies, or broad inventories.

Recovery first resolves retained keyed carrier identity/typed effect, then any external consequence not proven by that result. Unknown outcome never authorizes retry. A proven typed result needs no ceremonial second process check; publication ambiguity still needs fresh remote reconciliation.

An **EXECUTION BUNDLE** is one bounded invocation containing deterministic jobs and returning one compact independently attributable `JOIN`. It carries no authority/lifecycle and creates no cache, registry, scheduler, queue, daemon, workflow engine, or Runtime intelligence. Each job keeps stable identity, its own result, and failure attribution.

After semantic choices, authority, and current capability resolve, execute the maximal contiguous mechanically derivable suffix as one bounded bundle. Consequence-refresh remains mandatory but stays inside that bundle when no judgment intervenes. Do not reread unchanged `IMMUTABLE` evidence merely for confidence after a successful attributable `JOIN`.

Parallelize only when every pair has **no shared mutable state**, **no ordering dependency**, **no conflicting externally rate-limited dependency**, **no material resource contention**, and **independently attributable** results; otherwise serialize them. Same write surface, database/port/temp/cache conflicts, migrations, canonical publication/ref mutation, and final mutation gates remain serial.

A bundle may contain serial phases. Priority is `correctness -> survivability/recoverability -> boundedness -> round-trip minimization`. Stop on failed/ambiguous postconditions, preserve truthful partial state, return attributable evidence, and never self-retry. Return control only for material new/contradictory/ambiguous evidence, invalidated/missing authority or capability, semantic judgment, failed/ambiguous postcondition, terminal lifecycle, or governed `USER_STOP`.

With Agent Runtime, a confidently bounded, non-interactive, synchronously safe logical bundle maps to exactly one `terminal_exec` invocation. Derive jobs, ordering, guards, stop-on-failure behavior, and compact attributable `JOIN` before dispatch. Do not split mechanically derivable checks into per-job calls.

Split only at semantic/authority/capability/failure/terminal boundaries or concrete limits: timeout, output/command bound, interactivity, or survival requirement. Name the reason. For long, duration-uncertain, or survival-sensitive non-interactive work, inspect installed `runtime_capabilities` and selected request/result/effect semantics, then use an authorized recoverable carrier; retain `start_identity` for durable Runtime work and poll the keyed operation after lost acknowledgement. Unknown/corrupt retained state stops; never replay unknown mutation. Interactive work needs a carrier meeting its interaction/survival requirement.

## Capability HOW and acquisition

Generic engineering methodology is L2. After target truth, use [Foundation Architecture — Capability control](../contracts/FOUNDATION_ARCHITECTURE.md#capability-control) and load only the minimum exact-pinned capability. Exact-pinned ECC is default generic HOW after repo-native conventions; another admitted capability requires a material ECC gap. Repository construction/acquisition and process/resource lifecycle HOW are delegated to the table owners. Existing pinned tooling outranks remembered/global/latest tooling; ECC selection does not activate hooks, installers, role/task/session/memory systems, settings, or unrelated surfaces. Never install/update/repair/configure ECC merely for routing.

Ordinary task authority does not authorize global package-manager/profile mutation, persistent services, shared Runtime/tunnel lifecycle mutation, or host security/credential changes. Generated/scaffolded/hydrated/companion artifacts remain task-bound.

For authorized local startup using an env example, reconcile the named operator env with target-native equivalent or `scripts/reconcile_env.py --example PATH --env PATH`. Default is read-only; `--write` is explicit. Quoted `<thiếu key>` means unresolved required configuration. Values are opaque and never returned to the model; this does not certify provider credentials.

Temporary work uses one isolated run-owned root. Clean only current-run-created or explicitly disposable runtime-owned state. Before recursive cleanup read the Local Hygiene owner and prove root, creation/ownership/run identity, realpath containment, and non-symlink traversal. Reject empty/unresolved targets, filesystem root, home, workspace/repository root or ancestors, pre-existing user state, sibling projects, and arbitrary user-supplied input. Missing proof is retain/`BLOCKED`; needed diagnostic evidence is `RETAINED_FOR_EVIDENCE`.

## Report and terminal stop

Executor owns implementation evidence/`report.yaml`; Architect owns review. Read the Implementation Report identity/evidence owners before authorship. `final_execution_head` is the implementation candidate before report commit. The report records only truthful candidate/pre-publication evidence plus immutable identities and never self-attests its own publication.

Produce a bounded truthful report for `NEEDS_REVIEW` and authorized/capable blocking outcomes; failed verification stays FAIL. If publication is unavailable/unauthorized, return the exact non-durable result and preserve any immutable checkpoint rather than rewriting it.

Reports are compact evidence indexes: exact task/revision/base/candidate/binding, AC evidence, required verifier result, material gaps/deviations/blockers, publication identity, terminal result. Omit reconstructible execution transcript and empty ceremony. Optional timing/performance loads only when explicitly requested; never invent/backfill it.

Before publication topology, read its Task Protocol owner. Single-publication requires remote target still at authorized base, immutable fully verified candidate, no evidence needing prior remote candidate visibility, commit+push authority, truthful prepublication report, and no CI/external verifier/cross-checkout/promotion/explicit dependency on remote candidate. Then create the report-only sole direct child and make one ordinary non-force compare-and-swap publication; `pushed: false` remains truthful candidate-prepublication state. Otherwise use two-publication.

After publication resolve fresh remote proof. Failed/ambiguous publication requires fresh reconciliation before retry; never blind retry from `OUTCOME_UNKNOWN`. Preserve immutable candidate/report checkpoints.

Executor does not write Architect review, choose `promotion_candidate_head`, declare project PASS, promote refs, create release tags, mutate repository metadata, or publish releases without separately authorized later authority. Stop after exact Executor evidence and terminal handoff/result.
