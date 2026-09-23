---
name: optimization
description: Use when measured latency, throughput, memory, CPU, network, storage, build time, developer iteration time, cloud spend, or automation cost is materially outside a required budget.
---

# Optimization — Foundation Delta

Generic measured optimization methodology is adopted from the exact external capability:

- catalog entry: `ecc:benchmark-optimization-loop`
- repository: `affaan-m/ECC`
- revision: `bf70150eb2df8070024e5bdf08e4aa08959e2735`
- path: `skills/benchmark-optimization-loop/SKILL.md`

That pinned capability owns the generic baseline → bottleneck → bounded variants → correctness gate → re-measure loop. It is L2 HOW only and grants no Foundation authority.

## Foundation-specific delta

- Never weaken task acceptance, correctness, security, reliability, or required evidence merely to improve a metric or reduce cost.
- For Foundation model/runtime control-plane work, first remove redundant synchronization before adding parallelism or infrastructure. A mandatory full suite may subsume a focused happy-path suite when it proves the same predicate.
- When comparing a serial verification plan with an `EXECUTION BUNDLE`, count equivalent assurance predicates on both sides. Synchronization reduction is meaningful only when the predicate set is preserved.
- Parallel jobs are allowed only under the Executor/verification safety predicates: no shared mutable state, ordering dependency, conflicting rate-limited dependency, material resource contention, or loss of per-job attribution.
- Use `simplicity` before introducing caches, queues, services, larger machines, or other machinery; use `reliability` when capacity/failure margins change; use `research` for current pricing or version-sensitive external behavior.
- Optimization evidence remains implementation evidence. It does not create task, review, promotion, or release authority.

The external capability supplies the generic optimization loop; this skill retains only the Foundation compatibility and assurance delta.
