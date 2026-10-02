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

### Bounded need discovery and exact resolution

First resolve exact target truth and the current concern. Keep known language, framework, contract, and mutation constraints explicit while deriving a small literal metadata query. Query reads only committed registry/catalog metadata; it does not access the network, read upstream capability bodies, execute indexed bytes, write repository state, or activate anything:

```bash
python3 -B skills/scripts/sync_external_capabilities.py --query react testing --surface skill --limit 5
```

The query matches every supplied term case-insensitively against existing `title`, `description`, and `source_path` fields. It performs no synonym expansion, generated tagging, semantic ranking, or automatic best-fit selection. Output includes the exact pinned source repository/revision, authority `NONE`, total matches, visible truncation, and at most ten unchanged catalog rows; the default limit is five. A valid zero-match query is an honest empty result. Multiple or truncated matches are candidates only: reject stack-incompatible entries and refine the query when needed.

After choosing one candidate using target/task constraints, resolve its exact surface/title identity through the existing pinned resolver:

```bash
python3 -B skills/scripts/sync_external_capabilities.py --resolve --surface skill --title react-testing
```

Then read only the materially relevant sections of normally one to three selected capabilities at the returned immutable revision before applying their HOW. A lexical hit or successful exact lookup does not establish applicability, trust, task authority, role admission, or execution capability; missing or unfamiliar applicability stays explicit. Selection never activates upstream role/model/hook/session/install conventions.

The ECC CLI is optional. Its absence does not block generic HOW resolution when the exact pinned Foundation source/snapshot/catalog metadata resolves one entry uniquely; do not install, update, repair, or configure ECC merely to make the CLI available. Any ECC install/plan/apply operation remains outside this inert discovery seam unless separately and explicitly authorized.
