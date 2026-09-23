# Execution Attempt Continuity

This contract defines the Foundation L1 execution-attempt continuity primitive. Attempt data is local operational telemetry with `authority NONE`; it never changes task, review, acceptance, rebinding, Git, promotion, or release authority.

Canonical surfaces are `skills/scripts/execution_attempt.py` and `skills/templates/execution-attempt.yaml`.

## Truth model

Producer states are exactly `RUNNING` and `TERMINAL`.

Observer classifications are exactly `TERMINAL_CONFIRMED`, `ACTIVE_LEASE`, and `INTERRUPTED_UNKNOWN`.

`TERMINAL_CONFIRMED` requires an explicit terminal marker.

`ACTIVE_LEASE` means only that `last_seen_at_utc` is still inside the bounded lease. It is not proof that a ChatGPT UI, model process, network stream, browser session, or execution transport is alive.

`INTERRUPTED_UNKNOWN` means the producer state is still `RUNNING`, the lease is stale, and no terminal marker exists. It does not mean failed, dead, or terminal. Lease expiry is never an exact death timestamp.

Missing, stale, contradictory, malformed, or inaccessible attempt evidence remains unresolved and never becomes PASS.

## Exact binding

Each opaque `attempt_id` binds one exact repository, task id, positive task revision, 40-character execution base, start time, last-seen time, bounded lease, and producer state.

Starting an attempt verifies the repository root, GitHub origin identity, current HEAD, and canonical task identity against that binding. Attempt data never authorizes a binding change.

## Execution Slice

Schema v2 adds at most one unresolved `current_slice` under a `RUNNING` attempt. A slice has `authority NONE` and carries only an opaque caller-known `execution_slice_id`, monotonic ordinal, operation class, selected carrier, bounded non-secret intent identifier, reconciliation/postcondition kinds, bounded lifecycle/result observation, optional known runtime-session observation, and timestamp. It grants no mutation, retry, task, review, publication, promotion, or release authority.

Before a consequence-bearing request may leave the caller, Executor generates the slice identity and atomically persists `INTENT_RECORDED`. The durable order is therefore `generate identity -> persist intent -> dispatch`. There is deliberately no durable `DISPATCHED` transition: a local write cannot truthfully be atomic with a network or tool call.

`INTENT_RECORDED` with no later trustworthy observation means the request **may have been dispatched**. The same conservative rule applies when an acknowledgement was observed but no trustworthy result/postcondition was checkpointed. Both recover as `OUTCOME_UNKNOWN`; neither proves `FAILED`, `NOT_DISPATCHED`, or `SAFE_TO_RETRY`.

Slice telemetry never stores raw argv, environment, credentials, secrets, prompts/transcripts, raw logs/tool output, full diffs, file bodies, or broad inventories. It remains in the same repository-local Git metadata record as the attempt; no second continuity store or unbounded slice history exists. Once a result/postcondition is established and a coherent checkpoint at or after that observation exists, the resolved slice may be cleared and Git/post-state becomes the durable consequence evidence.

Schema-v1 attempt records remain readable explicitly as legacy records with no slice. A `RUNNING` legacy attempt must be explicitly upgraded before slice mutation; old bytes are never silently reinterpreted.

## Local Git metadata

Attempt state lives only under repository-local Git metadata resolved with:

`git rev-parse --git-path agent-foundation/execution-attempts`

The resolved store must remain inside the repository absolute Git directory. Attempt data must not require a tracked or untracked worktree file, a `.gitignore` change, remote publication, database, daemon, scheduler, background heartbeat, queue, browser automation, provider API, or Agent Runtime mutation.

The local attempt-state directory is never a bootstrap authority artifact.

## Operations

### start

Create one new opaque `RUNNING` attempt after exact repository/task/base verification.

### heartbeat

For a `RUNNING` attempt, refresh only `last_seen_at_utc`. This changes no authority and proves no liveness beyond lease freshness.

### slice intent / observation / reconciliation / clear

`slice-intent` persists the one current pre-dispatch intent. `slice-observe` records only trustworthy acknowledgement/result observations; an ambiguous mutating response is `OUTCOME_UNKNOWN`. `slice-reconcile` requires an explicit fresh consequence-specific observation before it can classify the intended effect. `slice-clear` is legal only after a resolved result and a coherent checkpoint at or after that result observation.

The minimum reconciliation classes are fixed and consequence-specific: `runtime_start -> runtime_session_identity`; `expected_state_filesystem -> expected_state`; `git_commit_update -> git_object_identity`; `git_publication -> remote_ref_identity`; and `report_publication -> remote_report_identity`. Reconciliation does not create a transaction framework.

`OUTCOME_UNKNOWN` never authorizes blind retry. Fresh reconciliation may permit retry only when attributable state establishes `EFFECT_ABSENT_PRECONDITIONS_HOLD`, or when the exact selected tool contract establishes `REPLAY_SAFE_CONTRACT`. `EFFECT_PRESENT` means the original consequence exists and must not be repeated merely because its earlier acknowledgement was lost. `UNRESOLVED` remains `OUTCOME_UNKNOWN`.

### checkpoint

For a `RUNNING` attempt, refresh `last_seen_at_utc` and record only bounded recovery hints: checkpoint kind, local HEAD, upstream ref and remote-tracking HEAD when available, tracked dirty state, and a capped untracked count.

Checkpoint data excludes full diffs, file contents, broad file inventories, prompts, conversation bodies, raw tool output, authentication material, and report bodies.

### terminal

Explicitly transition `RUNNING` to `TERMINAL` with `terminal_result` and `terminal_at_utc`.

Repeating the same terminal result is idempotent. A different terminal result is rejected. A confirmed terminal attempt never returns to `RUNNING`.

### inspect

Inspection is read-only. At a supplied/current time:

- `TERMINAL` becomes `TERMINAL_CONFIRMED`.
- `RUNNING` at or before lease expiry becomes `ACTIVE_LEASE`.
- `RUNNING` beyond lease expiry becomes `INTERRUPTED_UNKNOWN`.

Inspection returns the attempt identity, `authority: NONE`, classification, `last_seen_at_utc`, the last checkpoint, and explicit terminal data only when terminal is confirmed. It never synthesizes a death-time field.

### list-current-task

Return a bounded read-only list for one exact repository/task revision/execution-base binding. Listing does not choose a successor, restart work, or authorize recovery.

## Carrier and long-running execution

Execution decisions prioritize `correctness -> survivability/recoverability -> boundedness -> round-trip minimization`. Execution Bundle remains the bounded deterministic synchronization-reduction abstraction, but fewer round trips never justify a carrier whose interruption semantics make a consequence unrecoverable.

`terminal_exec` remains valid for work that is confidently bounded, non-interactive, and synchronously safe. Long, duration-uncertain, interactive, or survival-sensitive work requires a recoverable asynchronous carrier when such an authorized capability exists. The currently selected Runtime is **not** claimed here to provide caller-keyed lost-ACK recovery for `terminal_start`; unkeyed async start is acceptable only for read-only, independently replay-safe, or otherwise fully independently reconcilable work. Survival-sensitive async mutation that cannot currently be reconciled safely fails closed as `CURRENT_PHASE_CAPABILITY_UNAVAILABLE`, unless an already-authorized expected-state/bounded alternative preserves the same proof.

A long-running Executor may explicitly start an attempt, execute bounded work, heartbeat or checkpoint at material boundaries, create coherent Git checkpoints when task authority permits and recovery value justifies them, and terminalize when a terminal result exists.

There is no background heartbeat. Do not keep a large known-valid dirty worktree merely to wait for unrelated broad verification when an authorized coherent checkpoint is available. No hard ChatGPT duration, universal tool-call count, or platform-time assumption is a correctness rule.

## Recovery

A successor Architect or Executor may inspect attempt data before recovering interrupted work. `INTERRUPTED_UNKNOWN` is only a hint.

Recovery still requires fresh independent inspection of canonical remote truth, local HEAD, index/worktree state, local Git checkpoints, and current task/revision/base authority. If a current slice exists, the successor must also reconcile its specific consequence before deciding whether continuation or repetition is legal. `INTENT_RECORDED` without later trustworthy evidence is treated as `MAY_HAVE_BEEN_DISPATCHED / OUTCOME_UNKNOWN`.

Attempt data cannot authorize cleanup, mutation, continuation, publication, rebinding, task creation, review, acceptance, or release. Fresh Git/postcondition inspection remains mandatory, and unknown outcome never becomes retry permission.

## Evidence and domain boundary

The primitive preserves existing Foundation evidence semantics: stale or missing evidence stays UNKNOWN; material execution state is attributable to one attempt and exact binding; lease/recovery behavior is bounded; claims remain attributable to direct evidence.

Model-visible evidence is the minimum sufficient bounded proof. Large/raw output remains external and addressable where available. Truncated, missing, stale, or inaccessible raw evidence never becomes PASS; safe read-only verification may be rerun when needed, while mutation replay remains subject to the no-blind-retry rule.

Execution-attempt and slice telemetry are operational work-control evidence, not project-document or standards authority.
