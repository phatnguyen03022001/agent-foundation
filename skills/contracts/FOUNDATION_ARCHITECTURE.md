# Foundation Architecture — active capability-router contract

This file governs new Foundation-based sessions. The prior Architect/Executor organizational workflow belongs to **historical protocol-v3 bindings**, not the active default. Prior commits and artifacts remain readable by exact Git identity; no historical claim is retroactively changed.

## Governance boundary

```text
User request → Intent router (authority NONE) → Explicit target + authority check
→ Target-native instructions/state → Selected ECC HOW + specialist
→ Proportional evidence → Local Git checkpoint → Authorized remote publication
```

Router is static metadata, not a running orchestrator. It classifies request intent, selects bounded capabilities, asks for exact target/authority and routes genuine escalation. It cannot create scope, mutation, acceptance, release, deployment or destructive authority. No queue, daemon, database, or automatic memory/state synchronization.

Specialists are optional, **not organizational roles**: Researcher (READ_ONLY), Implementer (IMPLEMENT), Architect (DESIGN), Reviewer/Verifier (REVIEW), Security Reviewer (SECURITY), Release Operator (RELEASE). LEGACY_TASK is exclusively for explicit historical protocol-v3 bindings. A single session may activate several sequentially without claiming independent review. Use another session only for genuine independence, concurrent writer isolation, or missing specialty capability.

## Target repository product authority

The explicitly bound target owns product truth, behavior, architecture, tests, tooling, CI/deploy, security and domain decisions. Workspace and nearest target instructions apply. Bind canonical `owner/repo`, branch, actual root and origin before writes. Inspect local HEAD, index, dirty/untracked/ignored work and any in-flight Git operation. A missing conventional filename is not by itself an authority gap. Never infer target from memory/cwd, and never preload `product-state.json`, `documents/`, or `standards/` in an unrelated target. These optional Foundation-as-target models are not universal task prerequisites.

The operator's exact request and target policy supply mutation scope; neither a selected specialization nor an ECC skill can enlarge it. One authorized writer per affected scope. Separate explicit authority is required for release, deployment, destructive synchronization, force/rewrite, protected service lifecycle, or other irreversible consequences. Read-only work stays read-only.

## Capability control

Load only the selected capability entrypoint and exact relevant target context. Local ECC checkout resolved through bootstrap metadata is the default **read-only generic HOW** if available and its Git revision is observed. Adapt source to target and never execute ECC installer, hooks, Claude-specific agent/session policy, continuous memory, global settings or dependency installation implicitly. Pin an immutable commit before relying on an external surface as normative methodology. ECC missing locally is not authority to fetch/install it; use explicitly approved immutable remote source only when needed, or report the capability gap.

Selection examples: `intent-driven-development` and `product-capability` for ambiguous cross-boundary scope, `orch-add-feature`/`orch-change-feature`/`orch-fix-defect` for implementation, `contract-first` for shared API boundaries, `tdd-workflow` for code/tests, `verification-loop` for regression, `security-review` for sensitive changes, `production-audit` for shipping risk, `living-docs-governance` for drifting existing docs. `orch-pipeline` is a dependent reference, never an independent agent mandate. ECC approval gates are advice when they conflict with an already explicit operator authorization; they cannot silently insert unrequested ceremony.

`skills/.agent/external-capabilities/` retains optional historical snapshot/catalog tooling. It is not active bootstrap or a prerequisite for local ECC skill selection. No duplicate Foundation engineering HOW is normative.

## Execution surface and publication control

Default to target-local read/edit/build/test/debug through available Agent Runtime and repo-native scripts on macOS. Prefer the narrowest explicitly authorized action with equivalent evidence; typed interfaces never imply automatic safety or permission. If there is no sufficient narrower surface, a platform-permitted generic terminal remains a valid fallback only with explicit authority, recoverability, and the same proof obligations. Avoid remote calls during ordinary local steps. The local tree is the current *work surface* and must not be overwritten or reset to simulate remote truth; GitHub is the *published source of truth*. On commit/push, inspect only intended paths, distinguish local commits from pushed commits, observe fresh remote branch HEAD, require fast-forward safety and re-observe publication outcome. Exact commit identity is distinct from content identity: a content-equivalent but different commit is not an authorized substitute without explicit permission. Unknown effects require postcondition reconciliation before retry. Failed or ambiguous publication requires fresh remote reconciliation; never blind retry an OUTCOME_UNKNOWN effect.

## Risk-proportional assurance

Small reversible authorized tasks: direct execution, focused tests and diff review, concise chat report; no mandatory YAML. Multi-session, high-impact, regulated/external-governed or high-risk tasks: retain explicit task, report, review and continuity artifacts when actually required. Independent review must be performed independently; self-review is only local verification. No fabricated PASS or implicit accepted state.

### Recovery

After interruption, stale observations or unknown-effects operations, rebind exact target, read local/remote postconditions as appropriate, preserve dirty state and stop rather than blindly replay. For historical v3 bindings, consult the unchanged historical semantics in [Task Protocol](../protocols/TASK_PROTOCOL.md) and its compatible validators.

## Canonical navigation

- Active intent metadata: [case-router.yaml](../.agent/case-router.yaml).
- Bounded local implementation: [executor](../executor/SKILL.md).
- Optional design specialist: [architect](../architect/SKILL.md).
- Historical protocol-v3 semantics: [Task Protocol](../protocols/TASK_PROTOCOL.md).
- Evidence and recovery details, only when needed: [Execution Continuity](EXECUTION_CONTINUITY.md), [Implementation Report](IMPLEMENTATION_REPORT.md), [Architect Review](ARCHITECT_REVIEW.md).
- Optional assurance/document models: `standards/`, `documents/` — never universal task prerequisites.
