---
name: verification
description: Use when Foundation needs acceptance-to-evidence mapping, exact-candidate proof, execution-bundle safety, or authoritative-verifier boundaries beyond generic build/test completion checks.
---

# Verification — Foundation Delta

Generic build, type-check, lint, test, security-scan, and diff-review completion HOW is adopted from the exact external capability:

- catalog entry: `ecc:verification-loop`
- repository: `affaan-m/ECC`
- revision: `bf70150eb2df8070024e5bdf08e4aa08959e2735`
- path: `skills/verification-loop/SKILL.md`

That pinned capability is L2 HOW only. Target-repository verifier commands and acceptance authority remain authoritative; ECC does not create Foundation PASS, review, promotion, or release authority.

## Acceptance and evidence

Map each acceptance criterion and material invariant to the cheapest reliable evidence that would fail when the required behavior is wrong. Preserve distinct predicates even when execution is deduplicated. Passing Git, CI, build, lint, or a broad suite is not proof of an acceptance condition unless it actually establishes that condition.

Separate Executor implementation checks, integration/CI evidence, acceptance evidence, and project-designated authoritative verification. Bind every reusable result to the exact candidate identity, selected command/profile, and material environment. Rerun only when the candidate, required predicate, verifier selection, material environment, or ability to establish the prior result changes.

## Bounded deterministic execution bundles

Several required deterministic checks may share one **EXECUTION BUNDLE** only when the bundled jobs have no shared mutable state, no ordering dependency, no conflicting externally rate-limited dependency, no material resource contention, and independently attributable results. Otherwise serialize the affected jobs. Publication/ref mutation, migrations, shared mutable stores, and final mutation gates remain serial.

One bounded invocation may return a compact attributable `JOIN`, but every job keeps its identity and result; aggregate success cannot hide failure. Bundling removes synchronization cost, never assurance predicates.

When a mandatory full suite semantically subsumes a focused happy path suite, run the mandatory full suite directly and use the focused suite as a diagnostic after failure unless it has distinct acceptance authority or proves a distinct predicate. Deduplicate evidence, not predicates.

## Completion boundary

Before claiming contract satisfaction, require evidence for every required criterion, record substitutions or unavailable proof truthfully, and surface residual uncertainty. Failed mandatory evidence remains FAIL unless governing authority changes the requirement. Generic root-cause diagnosis routes through the admitted external debugging capability; production recovery routes through `reliability`; security-specific assurance uses `security-review`.
