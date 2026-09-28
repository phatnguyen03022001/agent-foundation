# Agent Foundation Product Architecture Boundaries

This contract is the canonical target-owned T1 product-architecture boundary for `phatnguyen03022001/agent-foundation` when this repository is itself the bound target. It defines semantic ownership and dependency boundaries only.

It is distinct from [Foundation Architecture](FOUNDATION_ARCHITECTURE.md), which remains the canonical generic owner of the Foundation L0/L1/L2 governance and control-plane model. This contract does not redefine task authority, role authority, capability routing, execution continuity, or external-HOW admission.

## Authority and filename neutrality

`agent-foundation` owns its product truth. Architecture ownership is resolved from current repository semantics and applicable authority, not from a filename or directory spelling.

The reference names `features/`, `shared/`, `platform/`, and `app/` describe semantic roles only. They are not required physical directories. Existing repository-native names remain valid when their semantics are explicit.

A path name never manufactures a product capability. T1 does not rename or reorganize `profile/`, `skills/`, `documents/`, or `standards/`, and it does not invent fake business features to make the repository resemble a reference tree.

## Current durable product capabilities

The current repository exposes four durable target-owned product capabilities, established by their actual contracts and behavior:

| Current physical domain | Product-capability semantics | Boundary |
| --- | --- | --- |
| `profile/` | durable operator and Architect configuration plus bootstrap/composition locators | does not own generic governance, target-product truth for other repositories, or runtime execution |
| `skills/` | Foundation governance/control contracts, reusable behavior, protocols, role procedure, and admitted reusable HOW | does not become target-product truth for another repository; its governance/control-plane semantics remain owned by `FOUNDATION_ARCHITECTURE.md` and the applicable protocol/contracts |
| `documents/` | documentation model, documentation authority domains, validation, and closure semantics | does not own engineering maturity, workflow authority, or another target's product truth |
| `standards/` | engineering assurance, maturity, requirement, applicability, and evidence semantics | does not own target architecture, product decisions, target-specific domain behavior, or assessment results |

These are semantic product capabilities of this repository. They are not inferred from the four directory names, and T1 does not claim that every child path is an independent feature.

The Foundation governance/control-plane model is a distinct semantic owner inside the `skills/` capability. Product architecture describes how this target repository's durable capabilities relate; Foundation Architecture describes governance/control-plane ownership. Neither absorbs the other.

## Target-specific architecture model

The default architecture for `agent-foundation` is a modular monolith:

- one canonical repository and `main` lineage;
- durable semantic product capabilities kept locally coherent;
- explicit public contracts between capabilities;
- reusable shared mechanics admitted only by evidence;
- runtime/operational mechanics kept separate from product/governance semantics;
- composition/bootstrap limited to wiring and locator concerns.

No literal reference directory layout is required.

### Product-capability ownership

Capability-specific semantics remain with the owning product capability.

Examples:

- operator-specific configuration remains owned by `profile/`;
- task/governance semantics remain owned by the applicable `skills/` contract or protocol;
- documentation closure semantics remain owned by `documents/`;
- assurance/maturity semantics remain owned by `standards/`.

A semantic rule does not move to a shared or platform role merely because several files inside one capability use it.

### Shared-capability admission

A reusable implementation capability may be treated as shared only when all are true:

1. it is consumed by at least two independent product capabilities;
2. it contains no capability-specific product semantics;
3. it exposes a stable reusable contract.

Two files inside one capability are not two independent consumers. Convenience, duplicate-looking helpers, or a generic name are not admission evidence.

If any predicate is false, the behavior remains capability-local.

A shared role must never become a `common`, `utils`, `misc`, or `everything` dumping ground. Shared mechanics must not import or own private product-capability semantics.

T1 does not create a shared directory or shared module because no such physical extraction is required to establish this rule.

### Platform/runtime-operational ownership

A platform role owns execution, infrastructure, or operational mechanics only: how a capability is hosted, executed, observed, delivered, recovered, or provided with infrastructure.

Platform mechanics must not own product or governance behavior merely because they execute, persist, host, or observe it.

Existing capability-local validators and tools remain with their semantic owners unless concrete reuse and ownership evidence justifies a later move. T1 does not centralize them.

`agent-runtime` remains a separate product/execution substrate. GitHub, MCP, and native execution tools remain orthogonal substrates. None becomes the internal product-semantics owner of `agent-foundation`.

### Composition/bootstrap ownership

Composition owns wiring only:

- bootstrap and entrypoint resolution;
- capability registration or locator wiring;
- configuration composition;
- navigation among explicit public contracts.

The current `profile/.agent/bootstrap/` surface is a repository-native composition/bootstrap surface because it binds locators for the Foundation authority set and external authorities. Its existence does not authorize it to absorb governance behavior, product rules, task lifecycle, or capability-local semantics.

Composition may depend on explicit public capability contracts. Product/governance behavior must not accumulate in the composition root.

## Dependency direction

The semantic dependency direction is:

```text
composition/bootstrap
        |
        +--> product capabilities
        +--> admitted shared mechanics
        +--> platform/operational mechanics

product capability
        +--> its own internals
        +--> admitted shared public contracts
        +--> platform interfaces/mechanics when needed
        +--> another product capability only through an explicit public contract

shared mechanics
        +--> shared/public abstractions
        +--> platform mechanics
        -/-> product-capability private internals

platform/operational mechanics
        +--> platform mechanics
        -/-> product/governance semantics
```

Direct dependency from one product capability into another capability's private internals is rejected by doctrine.

Allowed cross-capability interaction uses an explicit public contract, application interface, event, schema, CLI/API contract, or explicit orchestration boundary. A documentation link to a canonical public contract is not a private dependency.

Forbidden examples include one capability importing another capability's private implementation, reading its private storage representation as an API, or calling an implementation detail that has no explicit cross-capability contract.

## Cross-cutting ownership

Cross-cutting concerns are split by semantic ownership, reusable mechanics, and operational infrastructure. Existing narrower canonical owners remain authoritative.

| Dimension | Owning product capability | Shared mechanics, only if admitted | Platform / operational infrastructure |
| --- | --- | --- | --- |
| Security | capability-specific policy, trust behavior, redaction/handling requirements | generic security primitives or test helpers | identity, secret, host/runtime, and delivery infrastructure |
| Reliability | capability-specific failure, retry, idempotency, recovery, and compatibility semantics | reusable reliability primitives | process/runtime resilience and operational recovery infrastructure |
| Testing | capability-local behavioral and contract tests | reusable test utilities | CI/execution infrastructure |
| Configuration | capability-local configuration contract; `profile/` owns operator configuration semantics | stable reusable parsing/validation mechanics | environment, secret, host, and deployment mechanics |
| Delivery / operations | capability declares required compatibility, migration, release, rollback, and runbook needs where applicable | reusable delivery tooling | GitHub/runtime/deployment/backup/operational infrastructure |
| Telemetry | capability-semantic events and meaningful dimensions | instrumentation mechanics | observability backend, storage, alerting, dashboards, and retention |

`standards/` may define assurance requirements and evidence semantics across these dimensions, and `skills/` may provide reusable Foundation methodology. Neither fact transfers another capability's product behavior to those domains.

## Telemetry ownership

When telemetry is applicable, ownership has exactly three semantic levels:

1. **Product-capability semantic events** — the owning capability defines what happened, why it matters, and which dimensions are meaningful.
2. **Shared instrumentation mechanics** — an admitted shared capability may define how logs, metrics, traces, correlation, sampling, redaction, or audit signals are emitted.
3. **Platform observability infrastructure** — operational infrastructure owns where telemetry is transported, stored, queried, alerted, and retained.

A shared SDK or observability backend never becomes the owner of capability event meaning.

T1 does not require adding telemetry code, a telemetry SDK, an observability backend, dashboards, alerts, or new infrastructure merely to document these boundaries.

## Evidence-based movement and extraction

Ownership changes require evidence. Do not restructure because a reference architecture has a familiar folder name.

Move capability-local mechanics into a shared role only after the shared-admission predicates are proven.

Move or extract a module from the modular monolith only when evidence demonstrates an independent operational boundary such as:

- independent scaling;
- independent failure isolation;
- independent deployment;
- a distinct security boundary;
- distinct storage requirements;
- a distinct latency profile;
- distinct organizational ownership.

Large size, many folders, perceived future scale, or an external template are not extraction evidence.

## No premature infrastructure

The default remains a modular monolith. T1 does not introduce or require:

- microservices or multiple repositories;
- distributed transactions;
- Kafka or another message broker;
- Kubernetes or a service mesh;
- CQRS or event sourcing;
- a workflow engine;
- a central state service;
- a scheduler, daemon, or queue;
- an orchestration database;
- a custom agent framework.

Any later introduction requires a demonstrated current requirement and its own authority.

## T1 boundary

This contract establishes architecture ownership only. It intentionally does **not** implement or partially implement:

- release scope or a feature registry;
- feature lifecycle, gates, or feature-state derivation;
- global gates or project-phase derivation;
- Architect progression integration;
- execution or UI recovery redesign;
- adoption or closure work;
- future task artifacts.

Those concerns require separate acceptance boundaries. T1 also leaves the accepted seven-skill taxonomy and all ECC/external pins unchanged.

## Canonical invariants

```text
PRODUCT CAPABILITIES own their semantics.
SHARED owns only proven reusable mechanics.
PLATFORM owns runtime and operational mechanics.
COMPOSITION wires explicit owners together.

FILENAMES do not create ownership.
PRIVATE cross-capability internals are not public contracts.
CROSS-CUTTING semantics stay with the owning capability.
TELEMETRY meaning, instrumentation, and infrastructure are distinct.
EXTRACTION requires evidence.
DISTRIBUTED INFRASTRUCTURE is not the default.
```
