# agent-foundation

`agent-foundation` is the shared physical Git repository and lifecycle boundary for four support domains:

- `profile/` — operator and Architect configuration and bootstrap authority.
- `skills/` — reusable behavior, task protocol, routing, and work procedure.
- `documents/` — documentation model and closure semantics.
- `standards/` — engineering assurance and evidence semantics.

Semantic ownership remains separated across those subtrees. `agent-runtime` remains a separate execution product.

Foundation governance is organized by the canonical [three-layer architecture](skills/contracts/FOUNDATION_ARCHITECTURE.md): L0 Governance Kernel, L1 Control and Continuity, and L2 Capability and Knowledge. `agent-runtime`, GitHub, MCP, and native tools are orthogonal substrates rather than additional layers.

GitHub `main` is canonical and this repository is `MAIN_ONLY`. Historical source commits are intentionally retained in the ancestry of `main`.

TASK-0001 established physical consolidation and history continuity. TASK-0002 established the Foundation self-identity / `MAIN_ONLY` bootstrap contract at [`profile/.agent/bootstrap/bootstrap.json`](profile/.agent/bootstrap/bootstrap.json). TASK-0003 established the historical support-authority lineage. The active bootstrap now resolves the `skills/`, `standards/`, `documents/`, and `profile/` domains from one exact `agent-foundation` authority-set revision; semantic ownership remains path/domain-specific rather than revision-specific. Historical generated planning snapshots retain authority `NONE` and do not select current internal revisions. `agent-runtime` remains a separate external execution authority. Consolidation is complete: `agent-foundation` is the active canonical support repository; `architect-profile`, `agent-skills`, `agent-documents`, and `agent-standards` are archived/read-only and intentionally retained to preserve historical Git identity and `repo@SHA:path` resolution.
