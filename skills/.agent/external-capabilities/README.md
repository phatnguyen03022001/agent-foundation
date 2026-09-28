# External capability plane

This directory is Foundation-owned inert metadata for external capability discovery. It is L1/L2 navigation data, not authority, executable code, an installation surface, or an active capability route.

The canonical sources are `sources.json`. Every source is pinned to one immutable upstream commit and carries repository, tracking-ref, kind, license, and source-specific indexing policy. Generated snapshots live under `snapshots/`; `catalog.json` is the aggregate searchable index.

State boundaries remain strict: INDEXED != LOADED, PINNED != TRUSTED, SYNCED != ADOPTED, ADOPTED != AUTHORIZED, LOADED != AUTHORIZED, and SNAPSHOT != AUTHORITY. Awesome entries are discovery-only and cannot satisfy capability routing.

The sync implementation is stdlib-only and never executes upstream bytes. Check committed metadata with:

```bash
python3 -B skills/scripts/sync_external_capabilities.py --check
```

Refreshing tracking refs is mutation and requires an explicit approved Foundation task that authorizes this plane:

```bash
python3 -B skills/scripts/sync_external_capabilities.py --refresh --task .agent/tasks/TASK-XXXX/task.yaml
```

## ECC harness boundary

The pinned ECC entry in `sources.json` is Foundation's default generic engineering harness source after exact target-repository truth and repo-native conventions. Its deterministic snapshot distinguishes skills, commands, agents, the ECC command registry, plugin manifest, and install component/module/profile metadata at one immutable upstream commit. These bytes are indexed as inert L2 resolution metadata with authority `NONE`; selecting an entry does not activate it.

Resolve only the minimum relevant ECC surface under current target/task authority. Upstream `AGENTS.md`/`CLAUDE.md`, hooks, rules, installers, global configuration, and role/task/session/memory systems do not become Foundation governance or target authority. Another independently admitted exact external capability is a fallback only for a material ECC gap; Foundation-internal generic HOW is reserved for Foundation-specific deltas or genuinely uncovered capability.

The ECC CLI is optional. Its absence does not block generic HOW resolution when the exact pinned Foundation source/snapshot/catalog metadata resolves one entry uniquely; do not install, update, repair, or configure ECC merely to make the CLI available. Any ECC install/plan/apply operation remains outside this inert discovery seam unless separately and explicitly authorized.
