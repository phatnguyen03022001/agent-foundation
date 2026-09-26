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

## ECC CLI boundary

The pinned ECC entry in `sources.json` and this catalog are Foundation's discovery path for ECC skills. Resolve the exact indexed source revision, check applicability, and load only the relevant skill content under current target and phase authority. The index and loaded skill remain non-authoritative.

`ecc consult` is an optional heuristic for exploring ECC install components and profiles. Its recommendations are advisory only: they cannot route a Foundation task, select an execution surface, establish trust or authority, or become a required preflight. `ecc plan` and `ecc install` plan and apply installation into ECC-supported harnesses; they are outside the normal ChatGPT task flow. Do not infer a ChatGPT install target or install ECC hooks and commands as a side effect of loading a skill.
