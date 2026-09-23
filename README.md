# agent-foundation

`agent-foundation` is the shared physical Git repository and lifecycle boundary for four support domains:

- `profile/` — operator and Architect configuration and bootstrap authority.
- `skills/` — reusable behavior, task protocol, routing, and work procedure.
- `documents/` — documentation model and closure semantics.
- `standards/` — engineering assurance and evidence semantics.

Semantic ownership remains separated across those subtrees. `agent-runtime` remains a separate execution product.

GitHub `main` is canonical and this repository is `MAIN_ONLY`. Historical source commits are intentionally retained in the ancestry of `main`.

TASK-0001 established physical consolidation and history continuity. TASK-0002 establishes the Foundation self-identity / `MAIN_ONLY` bootstrap contract at [`profile/.agent/bootstrap/bootstrap.json`](profile/.agent/bootstrap/bootstrap.json). The selected support Authority Set is still the existing locked external support revisions; Authority Set cutover is pending, and the four legacy repositories are not retired by TASK-0002.
