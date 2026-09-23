# Foundation Architecture

This contract is the single canonical generic owner for the Foundation three-layer model and the L1 control-and-continuity semantics that connect governance to reusable capability. It does not replace target-repository authority, the Task Protocol, individual skills, standards, document models, or operator configuration.

The Foundation has exactly three conceptual layers. A repository subtree is not automatically a layer, and an execution transport is not a layer.

## L0 — Governance Kernel

L0 owns authority, not engineering methodology.

There are exactly two organizational roles: Architect and Executor.

- Architect owns final governance judgment, task authority, material WHAT/BOUNDARY/PROOF, and final canonical acceptance/revision/block judgment.
- Executor executes one exact authorized binding and owns implementation evidence. Specialization never increases authority.
- task.yaml, report.yaml, and review.yaml ownership and lifecycle boundaries remain governed by the [Task Protocol](../protocols/TASK_PROTOCOL.md).
- Repository rebinding, cross-repository isolation, exact-base binding, authority-versus-capability separation, and minimum freshness/safety invariants remain L0 concerns.

Sync and read-only Researcher are Executor specializations. They are not organizational roles and have no independent task, mutation, review, acceptance, rebinding, or architecture authority.

## L1 — Control and Continuity

L1 owns deterministic capability navigation and non-authoritative continuity. It does not own product decisions or implementation methodology.

### Capability control

Capability discovery and reuse use explicit state distinctions:

- INDEXED != LOADED: discoverability does not inject content into active context.
- PINNED != TRUSTED: immutable identity does not establish quality, safety, or applicability.
- SYNCED != ADOPTED: local synchronization does not make upstream content canonical.
- ADOPTED != AUTHORIZED: accepted reusable content does not grant target mutation or lifecycle authority.
- LOADED != AUTHORIZED: context availability never grants permission.
- SNAPSHOT != AUTHORITY: a reproducible snapshot is evidence/navigation input, not governing authority.

No capability state transition manufactures L0 authority. External or internal capability may be indexed, pinned, synchronized, evaluated, adopted, and loaded only as independently justified; target authorization still comes from the exact current binding.

Routing is deterministic and bounded: resolve the required semantic capability, resolve the immutable source identity when source identity matters, apply compatibility/admission evidence, then load only the minimum capability content required for the current decision. Mutable popularity, installation, provider identity, or availability is never a substitute for authority.

### Execution surface and publication control

Routing order is required semantic capability → current authority → authorized available surface. Provider-specific handoff wording binds execution only when the canonical task, proof, or consequence materially requires that surface identity.

When consequences and equivalent evidence are available, prefer the narrowest explicit bounded action with machine-checkable inputs, target, precondition, mutability, and postcondition. Typed does not mean automatically safe. Generic terminal remains a valid fallback when authorized, when no sufficient narrower surface exists, and when the consequence is platform-permitted.

A platform/tool safety block fails closed. It does not permit obfuscation, encoding intent, command splitting, permission widening, disabling protections, or an unchanged retry made only to obtain another safety decision.

Platform compliance changes HOW, never WHAT must be proven. Surface changes must preserve acceptance criteria, verifier requirements, exact commit/content identity, remote freshness, scope checks, and evidence quality.

An immutable publication handoff is valid only after the prior writer is terminal and an explicit publication authority transfer identifies the immutable checkpoint. The successor may publish only that checkpoint and may not edit, recreate, or amend it without new content-mutation authority.

Exact-commit publication and content-identity publication are distinct. A different commit identity is acceptable only when the task explicitly permits content identity and preserves parent/base, scope, freshness, and proof.

Operator fallback is a last-resort consequence when automation is materially unavailable or an action is genuinely user-only/approval-bound. It retains exact preconditions and post-publication remote proof.

Operator attention/manual labor is a constrained resource: do not use the operator as a manual command/RPC bridge when an authorized capable surface can perform the action. Human input remains valid for unavailable capability, destructive/irreversible authority, material paid-cost approval, unresolved intent, or genuinely user-only action.

Agent Runtime remains an optional capability surface. Mobile/ChatGPT+GitHub-only operation is first-class whenever the exact task does not materially require unavailable native capability. Tool availability is not permission to consume quota, and GitHub Actions must not become an iterative debugger.

### Sync specialization

Sync is a named Executor specialization for bounded deterministic synchronization work. A Sync Executor may resolve and compare immutable source identities and perform synchronization only inside an explicit current repository/task binding. Sync cannot self-admit upstream content, change architecture, create or accept tasks, mutate sibling repositories, or convert synchronized bytes into authority.

This task does not create a package manager, plugin manager, registry service, daemon, scheduler, queue, database, provider pool, or workflow engine. Later external ecosystem reuse must fit these same boundaries.

The Foundation-owned external capability plane lives at `skills/.agent/external-capabilities/`. Its registry selects immutable upstream snapshot identities; source snapshots and the aggregate catalog are inert metadata. Bootstrap exposes only the aggregate catalog locator at the active Foundation `authority_set_identity` revision. The catalog is not a capability route, trust decision, adoption record, or authority source. Awesome entries remain discovery-only pointers and require separate downstream source resolution before capability admission.

### Independent read-only research fan-out

Independent research fan-out is advisory Executor-specialized work:

1. each researcher receives one exact target, base, and question;
2. only minimum relevant context is supplied;
3. researchers are read-only for the target and have no canonical mutation authority;
4. peer results are not visible before individual evidence returns;
5. each return is compact evidence with source identity, observations, uncertainty, and materially relevant implications;
6. Architect synthesizes evidence by quality and applicability, not by majority voting.

A Researcher cannot create canonical task/review authority, rebind the target, or make the final decision.

For materially uncertain direction-setting, Architect may issue exactly three independent fresh-context Research Requests using `skills/templates/research-request.yaml` and render standalone packets with `skills/scripts/research_fanout.py`. Narrower questions may use one Research Request. Every Research Request and Research Result has authority `NONE`; peer results remain absent until each return is final. Architect alone owns evidence synthesis and direction judgment, and neither majority vote, confidence averaging, model score, nor council consensus creates authority.

### Cross-repository finding continuity

A finding discovered while bound to repository A may be durably referenced as non-authoritative evidence for a future owner of repository B. The reference has authority NONE until repository B is explicitly bound and the finding is freshly revalidated against B's current canonical truth.

A cross-repository finding cannot mutate the owner repository, create a task automatically, create acceptance authority, rebind the active target, or bypass fresh revalidation. Durable continuity is a pointer/evidence obligation, not a shared mutable cross-repository authority object or task queue.

Canonical Continuity Findings use `skills/templates/continuity-finding.yaml` with authority `NONE` and status `UNVALIDATED_FOR_OWNER`. Foundation stores only bounded pointer/metadata records under the owner-keyed `profile/.agent/continuity/` root. When Architect explicitly binds owner repository B, only B's continuity file is loaded; B's canonical truth is freshly resolved and each material finding is revalidated before Architect may discard it, retain it, or separately task it through normal L0 authority.

### Execution-attempt continuity

Local Executor liveness hints follow [Execution Attempt Continuity](EXECUTION_CONTINUITY.md). Producer state is only `RUNNING` or explicit `TERMINAL`; observers classify only `TERMINAL_CONFIRMED`, `ACTIVE_LEASE`, or `INTERRUPTED_UNKNOWN`. A fresh lease means only recent `last_seen_at_utc`; a stale non-terminal lease remains unknown and never manufactures failure, death, terminal state, or an exact death timestamp.

Attempt records have authority `NONE` and live only in repository-local Git metadata resolved through `git rev-parse --git-path`. They are bounded recovery hints, not project documents, remote truth, task state, or a fourth layer. Recovery still requires fresh canonical remote, HEAD, index/worktree, checkpoint, and task-authority inspection. No daemon, background heartbeat, scheduler, automatic recovery, or Agent Runtime service is introduced.

## L2 — Capability and Knowledge

L2 owns reusable HOW and domain knowledge:

- the existing internal and later-admitted external skills;
- standards and evidence models;
- document models and references;
- catalogs and repository-local reusable capabilities;
- engineering methodology such as research, debugging, verification, security review, optimization, reuse analysis, and domain guidance.

The current 15-skill taxonomy remains unchanged. L2 content can inform work only through L0 authority and L1 routing; maturity, popularity, loading, or adoption does not grant permission.

## Orthogonal substrates

agent-runtime, GitHub, MCP, and native execution tools are orthogonal substrates. They provide transport, storage, or execution capability; they are not organizational roles, authority sources, or a fourth Foundation layer.

agent-runtime remains a separate repository/product. Foundation governance must not mutate Runtime, service state, host permissions, credentials, TCC, Keychain, or System Settings without separate explicit authority.

## Canonical navigation

Bootstrap exposes this contract through foundation_control_plane in profile/.agent/bootstrap/bootstrap.json. Resolution binds the locator to the exact Foundation authority_set_identity commit, so the path is immutable for that bootstrap context and fails closed when the locator is missing or malformed.

The existing Case Router remains static navigation and does not become a lifecycle engine. The [Task Protocol](../protocols/TASK_PROTOCOL.md) remains the L0 semantic owner for cross-role authority and lifecycle. Architect/Executor skills retain role-local procedure. L2 owners retain capability-specific HOW.

The four physical Foundation domains remain semantically distinct: profile/ owns operator configuration, skills/ reusable behavior/control contracts, documents/ documentation semantics, and standards/ engineering assurance semantics.
