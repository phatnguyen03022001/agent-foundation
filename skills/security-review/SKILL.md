---
name: security-review
description: Use when Foundation assurance needs threat-path, trust-boundary, authority-boundary, or security-evidence judgment beyond generic implementation security guidance.
---

# Security Review — Foundation Delta

Generic security implementation and checklist HOW is adopted from the exact external capability:

- catalog entry: `ecc:security-review`
- repository: `affaan-m/ECC`
- revision: `bf70150eb2df8070024e5bdf08e4aa08959e2735`
- path: `skills/security-review/SKILL.md`

That pinned capability is L2 HOW only. Target-repository security authority and current platform/framework guidance still outrank it, and it grants no Foundation task, mutation, review, acceptance, promotion, or release authority.

## Foundation-specific delta

- Model security from concrete protected assets, attacker-controlled inputs, trust and authority boundaries, privileges, sensitive state, and meaningful sinks. A checklist match is not itself a vulnerability.
- Trace a plausible attack path from controllable source to privileged or sensitive effect. Record prerequisites, existing mitigations, blast radius, and the evidence that distinguishes an exploitable path from a theoretical pattern.
- Preserve least authority and fail closed at ambiguous privilege, identity, secret, or trust-boundary transitions. A security control never expands the active task boundary.
- Security evidence must be attributable to the exact candidate and relevant environment. Negative/boundary tests, artifact inspection, runtime observation, or independent verification are selected by the governing acceptance/assurance requirement rather than by ECC ceremony.
- Do not weaken threat-path coverage because the external checklist is narrower, and do not import framework-specific ECC examples as universal policy.

Use `adversarial-audit` for non-malicious failure/governance pressure and `reliability` for availability/recovery. Completion and authoritative evidence semantics remain owned by Foundation `verification` and the Task Protocol.
