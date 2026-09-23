# Executor Engineering HOW

This L2 reference owns generic engineering methodology delegated from the Executor authority kernel. It grants no task, repository, mutation, publication, review, acceptance, or infrastructure authority; the active task and Task Protocol remain governing.

## Repository construction and acquisition

After binding authority, classify repository-construction work as an existing repository or greenfield/framework bootstrap, then inspect the target/toolchain before acquisition or generation. The later discovery, acquisition, reuse, scaffold, and generation steps are decision gates when applicable, not mandatory ceremony.

For an existing repository, inspect Git state, manifests, lockfiles, package-manager markers/versions, runtime pins, scripts, framework configuration, generator/codegen configuration, `.gitignore`, and repository-native verification surfaces before acquiring, scaffolding, generating, or substituting tooling. Existing repository-pinned tooling, scripts, generators, and verification commands take precedence over remembered, globally installed, or merely latest external tooling unless an explicit upgrade or tool-contract change is authorized.

For greenfield/framework bootstrap, fresh-resolve the current official framework/toolchain documentation and supported scaffold/generator behavior before manually recreating equivalent boilerplate. Resolve the current official mechanism when execution needs it rather than encoding transient package versions, flags, or one-shot command syntax into reusable doctrine.

Operationalize [reuse-first](../reuse-first/SKILL.md) before custom implementation of commodity capability. Evaluate, in order, an existing repository implementation, standard library/native platform capability, framework/platform capability, maintained ecosystem tooling/library, and mature admitted OSS. Use a small local implementation only when the prior options do not fit the authorized requirement, and treat a custom framework as a last resort justified by evidence. Fast model-generated code is not itself justification for a custom replacement.

Choose the least-persistent sufficient authorized acquisition mode; this classification creates no acquisition subsystem:

- `REPO_LOCAL`: tooling belongs to the reproducible repository build, test, or codegen contract.
- `EPHEMERAL`: one-shot scaffold, research, codegen, or exact run-owned temporary tooling when persistence is unnecessary.
- `GLOBAL`: stable cross-repository workstation primitives only under separate machine/operator authority.
- `CONTAINERIZED`: tooling that is materially heavy, conflicting, service-like, or benefits from isolation/reproducibility.

Ordinary target-task authority does not silently authorize Homebrew mutation, global npm/pnpm installs, persistent uv tool installs, persistent go installs, PATH or shell-profile changes, runtime-manager changes, Docker-engine changes, persistent service mutation, or Agent Runtime or tunnel lifecycle mutation. Those machine/global/shared-infrastructure actions require separate machine/operator authority.

After scaffold or generation, inspect the generated diff before pruning or reshaping it. Preserve required framework/tool-owned baseline and required companion files where applicable, including hygiene, configuration, lock, runtime, package-manager, and verification metadata. Manual recreation or deletion of an accepted generated baseline requires concrete task-compatible justification.

Treat `.gitignore` as an explicit bounded repository-construction concern rather than a universal template. Preserve official framework defaults where applicable, then add only target-specific generated/local artifacts justified by the repository. Generated source, migrations, or codegen output are not automatically ignored; their source-control policy remains target-specific.

If a restrictive task path/file scope excludes required companion files from an accepted scaffold/generator baseline, including a required `.gitignore`, treat the mismatch as a `BLOCKING` authority gap before destructive pruning, silent omission, or manual reconstruction. Generated output does not expand task authority.

Dependency hydration executes an already-declared/pinned/locked dependency contract needed for authorized repository execution or verification and is not, by itself, dependency redesign. A command becomes dependency/tool-contract mutation when it intentionally adds/removes/changes dependencies, ranges, resolutions, lifecycle execution policy, persistent codegen/tool contracts, or otherwise materially rewrites the declared/locked contract; that mutation requires the authority already governed by the Task Protocol. If a nominal hydration step unexpectedly rewrites the contract, stop and classify the gap instead of normalizing the rewrite.

### Process/resource ownership boundary

Executor may terminate, signal, stop, restart, reconfigure, or otherwise lifecycle-mutate a process, service, container, or other execution resource only when ownership by the current authorized task/run is positively established and current task authority permits that cleanup. Positively task-owned children, descendants, test servers, and explicitly task-owned local services/containers remain eligible for bounded cleanup when that authority exists; exact PID/PGID ownership evidence may be used for such task-owned cleanup.

Unknown ownership fails closed. An unknown process occupying a needed port must not be signaled. Process-name, tree, PID/PGID, port, service, container, pkill-style, or equivalent broad selection may act only on a selected target set whose current-task ownership is already positively proven; matching or apparent relevance is not ownership proof.

Agent Runtime, the secure tunnel, execution transport/controller ancestors, and other shared operator execution infrastructure are not task-owned merely because they carry, support, block, or appear related to current target work. Ordinary target-task authority does not authorize signaling, stopping, restarting, or reconfiguring them, even when they appear to cause a target-task problem.

This is not an absolute never-terminate-Runtime rule. A separately authorized infrastructure-maintenance task may resolve its own exact authority for bounded Agent Runtime/tunnel lifecycle action; ordinary target-task authority never implicitly inherits that infrastructure authority.

Classify discovered gaps only as `LOCAL`, `FOLLOW_UP`, or `BLOCKING` under the [Task Protocol](../protocols/TASK_PROTOCOL.md). A `LOCAL` fix is necessary for current acceptance, inside the authorized material/component boundary, changes no governing semantics or authority, creates no material dependency or ownership boundary, is permitted by task policy, and is deterministically verifiable; LOCAL needs no Architect approval. Unexpected but materially local companion surfaces required for acceptance are reported truthfully rather than treated as automatic pre-mutation blockers. Record `FOLLOW_UP` when the issue is real but unnecessary or unauthorized; stop on `BLOCKING` when safe continuation requires missing or conflicting authority. Discovery is never implicit authority.
