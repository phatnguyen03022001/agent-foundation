---
name: simplicity
description: Use when a Foundation governance or execution change risks adding authority, state, layers, taxonomy, infrastructure, or ceremony beyond a currently proven requirement.
---

# Foundation Simplicity

Choose the smallest governance/execution change that satisfies current authority and preserves known correctness, security, compatibility, evidence, and recovery obligations.

## Consequence-first reduction

Challenge new Foundation machinery in this order:

`existing owner → smaller rule/change → bounded delta → new reusable owner → new subsystem`

Move right only when a concrete current requirement cannot be satisfied by the simpler owner or shape. New registries, roles, state stores, daemons, queues, orchestration layers, configuration axes, capability wrappers, or persistent metadata must justify the authority/state/operational surface they add.

Simplicity is not minimum lines or minimum files. An explicit invariant, state machine, compatibility guard, or independent evidence boundary is justified when removing it would make a material requirement unprovable or unsafe. Prefer deletion of duplicate ownership and representations over adding indirection to reconcile them.

## Stable governance and change admission

For mature Foundation governance, **NO CHANGE REQUIRED** is a valid preferred result when no material reproduced problem exists. Admit reusable governance change for an evidence-backed defect, stale rule/external reality, recurring missing capability, security or compatibility failure, material cost/usability/maintainability regression, or explicit durable maintainer objective change. Preference, novelty, elegance, architectural fashion, and hypothetical future scale are insufficient authority.

The internal skill taxonomy is derived from `.agent/rationalization.json` and is closed to ad hoc additions by default. A new internal skill requires repeated evidence of a materially distinct recurring responsibility that is Foundation-wide and cannot fit an existing canonical owner or an exact admitted external capability, or exceptional correctness/security justification. Do not create a wrapper merely to rename an external capability or restate semantics already owned by a role, contract, documents, or standards. Do not optimize the taxonomy for an arbitrary numeric threshold; ownership evidence decides the shape.

Apply the accepted capability precedence: exact target-repository truth and repo-native conventions first; exact-pinned ECC generic HOW second; another independently admitted exact capability only for a material ECC gap; Foundation-internal HOW only for an irreducible Foundation-specific delta or a real uncovered Foundation-wide capability.

## Review output

For each proposed Foundation complexity increase, identify the current requirement, the existing owner considered, the new state/authority/operational surface created, and why the smaller alternative fails. Classify it as **required now**, **justified boundary**, **premature/speculative**, or **duplicate/indirect**.

Generic build-vs-reuse, architecture-pattern, language naming/layout, and framework-specific HOW belongs to the target repository or exact external harness rather than this skill.
