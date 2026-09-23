# agent-foundation

`agent-foundation` is the shared physical Git repository and lifecycle boundary for four support domains:

- `profile/` — operator and Architect configuration and bootstrap authority.
- `skills/` — reusable behavior, task protocol, routing, and work procedure.
- `documents/` — documentation model and closure semantics.
- `standards/` — engineering assurance and evidence semantics.

Semantic ownership remains separated across those subtrees. `agent-runtime` remains a separate execution product.

GitHub `main` is canonical and this repository is `MAIN_ONLY`. Historical source commits are intentionally retained in the ancestry of `main`.

TASK-0001 established physical consolidation and history continuity. TASK-0002 established the Foundation self-identity / `MAIN_ONLY` bootstrap contract at [`profile/.agent/bootstrap/bootstrap.json`](profile/.agent/bootstrap/bootstrap.json). TASK-0003 resolves the selected `agent-skills`, `agent-standards`, and `agent-documents` semantic owners from their same immutable commits through `agent-foundation`; semantic ownership remains distinct, and imported newer development tips do not become authority automatically. The generated navigation projection is now refreshed from the current Foundation-native inputs and preserves the accepted TASK-0001 → TASK-0002 → TASK-0003 lineage. `agent-runtime` remains a separate external execution authority. Consolidation is complete: `agent-foundation` is the active canonical support repository; `architect-profile`, `agent-skills`, `agent-documents`, and `agent-standards` are archived/read-only and intentionally retained to preserve historical Git identity and `repo@SHA:path` resolution.
