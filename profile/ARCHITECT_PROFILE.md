# Operator Profile (optional; not governance authority)

## Working preferences

Prefer a single bounded ChatGPT worker directly handling the current repository. Speak Vietnamese with the operator; commit and engineering artifacts use English by default unless the target says otherwise.

Priorities: correctness and security, KISS, target-native architecture, local execution, small context, no unnecessary chats/agents/dependencies, exact evidence and reversible Git checkpoints. Product facts belong to the target, not this profile.

## Bootstrap

1. Read workspace and nearest target instructions.
2. Bind explicit target identity, canonical origin, branch, local HEAD, dirty/index/untracked work.
3. Read [Case Router](../skills/.agent/case-router.yaml) for the request's intent.
4. Load one matching [specialist](../skills/contracts/FOUNDATION_ARCHITECTURE.md) and relevant target-owned code/tests; use ECC read-only HOW selectively.

No mandatory Architect session, task/report/review YAML, global skill inventory, external snapshot/catalog, standards/docs/product-state scan, historical task context, or provider/model/effort preference. A routing choice is **not** permission to mutate.

## Execution and publication

Use the available `CHATGPT_LOCAL` / Agent Runtime transport for macOS source, edits, build and tests. Do not restart shared services. Preserve operator-owned changes. Commit/push only with explicit scoped authority and verified remote safety. A single chat can design, implement and verify sequentially; independent review means genuinely separate verification.

Current local tree is working state. Published remote is durable canonical state. Do not reset/reclone to resolve divergence; report BLOCKED when safe reconciliation is impossible.

## Historical compatibility

Existing protocol-v3 tasks and historical review artifacts retain their original meaning. Resolve their exact commit and [Task Protocol](../skills/protocols/TASK_PROTOCOL.md) when one is explicitly bound. Do not apply v3 ceremony to routine fresh work.

## Material changes

For ambiguous system design, security/data risk or irreversible change, use appropriate specialization and ask only for genuine missing authority/product decisions. Never invent acceptance evidence or silently escalate scope.
