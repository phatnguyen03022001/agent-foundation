---
name: debugging
description: Use when a bug, failing test, broken CI job, incident symptom, regression, or unexpected behavior needs a reproducible root cause rather than speculative fixes.
---

# Debugging — Foundation Delta

Generic debugging methodology is adopted from the exact external capability:

- catalog entry: `superpowers:systematic-debugging`
- repository: `obra/superpowers`
- revision: `5bf4e78011075bcfc0dc295f0724994cd123ee71`
- path: `skills/systematic-debugging/SKILL.md`

That pinned capability owns the generic reproduce → investigate → hypothesize → isolate root cause → implement → verify method. It is L2 HOW only and grants no Foundation authority.

## Foundation-specific delta

- Task/repository/base authority, mutation scope, and lifecycle remain governed by Foundation contracts and the active task. An upstream debugging step never authorizes adjacent refactors, architecture changes, dependency changes, or repository mutation.
- During a production incident, safe mitigation and restoration may precede complete root-cause work when current authority permits it. Coordinate failure/recovery decisions with `reliability` and preserve evidence for later diagnosis.
- A workaround that restores behavior without establishing the causal mechanism is a **mitigation**, not a root-cause fix.
- If investigation exposes a material architectural or scope gap outside current authority, report it rather than smuggling redesign into the fix.
- Route version-sensitive or externally documented unknowns through `research`; route completion evidence through Foundation `verification`.

The external capability supplies methodology, not governance, review authority, task authority, or acceptance authority.
