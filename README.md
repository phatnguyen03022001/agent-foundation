# agent-foundation

`agent-foundation` is the shared physical Git repository and lifecycle boundary for four support domains:

- `profile/` — operator and Architect configuration and bootstrap authority.
- `skills/` — reusable behavior, task protocol, routing, and work procedure.
- `documents/` — documentation model and closure semantics.
- `standards/` — engineering assurance and evidence semantics.

Semantic ownership remains separated across those subtrees. `agent-runtime` remains a separate execution product.

GitHub `main` is canonical and this repository is `MAIN_ONLY`. Historical source commits are intentionally retained in the ancestry of `main`.

TASK-0001 establishes physical consolidation and history continuity only. Semantic, bootstrap, and authority cutover are not completed by this task.
