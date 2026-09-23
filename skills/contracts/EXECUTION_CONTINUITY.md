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

## Long-running execution

A long-running Executor may explicitly start an attempt, execute bounded work, heartbeat or checkpoint at material boundaries, create coherent Git checkpoints when task authority permits and recovery value justifies them, and terminalize when a terminal result exists.

There is no background heartbeat. Do not keep a large known-valid dirty worktree merely to wait for unrelated broad verification when an authorized coherent checkpoint is available.

## Recovery

A successor Architect or Executor may inspect attempt data before recovering interrupted work. `INTERRUPTED_UNKNOWN` is only a hint.

Recovery still requires fresh independent inspection of canonical remote truth, local HEAD, index/worktree state, local Git checkpoints, and current task/revision/base authority.

Attempt data cannot authorize cleanup, mutation, continuation, publication, rebinding, task creation, review, acceptance, or release. Fresh Git inspection remains mandatory.

## Evidence and domain boundary

The primitive preserves existing Foundation evidence semantics: stale or missing evidence stays UNKNOWN; material execution state is attributable to one attempt and exact binding; lease/recovery behavior is bounded; claims remain attributable to direct evidence.

Execution-attempt liveness is operational work-control telemetry, not project-document authority.
