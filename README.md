# agent-foundation

Minimal governance for ChatGPT's bounded, local-first engineering sessions. MAIN_ONLY; `main` is the sole active branch.

```text
Request → Capability Router → Target + authority check → Target-native context
→ Optional ECC specialist HOW → Local implementation/verification
→ Local commit (authorized) → Fresh remote check → Push (authorized)
```

- [Active Foundation Architecture](skills/contracts/FOUNDATION_ARCHITECTURE.md) — binding, authority, assurance, local/remote distinctions.
- [Case Router](skills/.agent/case-router.yaml) — intent to specialist navigation, **authority NONE**.
- [Implementer](skills/executor/SKILL.md) / [Architect](skills/architect/SKILL.md) — optional specialist entrypoints.
- [Task Protocol](skills/protocols/TASK_PROTOCOL.md) — historical protocol-v3 contract, used only for explicit task-bound/external governance work.
- [Bootstrap](profile/.agent/bootstrap/bootstrap.json) — thin entrypoint. [Profile](profile/ARCHITECT_PROFILE.md) is optional operator preference, not authority.

The target repository owns product knowledge, design, commands, tests and durable decisions. `documents/`, `standards/` and `product-state.json` describe optional *Foundation-as-target* models, not generic prerequisites for a new chat.

ECC at `/Users/tienphat/Developer/third-party/ECC` is a read-only engineering-methodology reference, not an installed global agent framework. Agent Runtime is local execution transport. GitHub is authoritative *published* state; the local Git tree is protected *working* state. Historical protocol-v3 task/report/review evidence remains in Git without rewrite or backfill.
