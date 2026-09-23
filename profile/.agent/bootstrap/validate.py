#!/usr/bin/env python3
"""Validate and resolve the agent-foundation profile bootstrap contract."""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

FOUNDATION_REPOSITORY = "phatnguyen03022001/agent-foundation"
FOUNDATION_RESOLVED_KEY = "agent-foundation"
INTERNAL_DOMAINS = {
    "profile": "profile",
    "skills": "skills",
    "documents": "documents",
    "standards": "standards",
}
LEGACY_INTERNAL_OWNER_ALIASES = frozenset(
    {"architect-profile", "agent-skills", "agent-documents", "agent-standards"}
)
EXPECTED_EXTERNAL_REPOSITORIES = {
    "agent-runtime": "phatnguyen03022001/agent-runtime",
}


EXPECTED_SURFACES = {
    "CHATGPT_GITHUB": ("CHATGPT", "GITHUB", "GITHUB", "GPT-5.6 Sol", "HIGH"),
    "CHATGPT_LOCAL": ("CHATGPT", "LOCAL", "AGENT_RUNTIME", "GPT-5.6 Sol", "HIGH"),
    "CODEX_CLOUD": ("CODEX", "CLOUD", "NATIVE", "LUNA", "MEDIUM"),
    "CODEX_LOCAL": ("CODEX", "LOCAL", "NATIVE", "LUNA", "MEDIUM"),
}

EXPECTED_REPOSITORY_CONTRACT = {
    "repository": "phatnguyen03022001/agent-foundation",
    "topology": "MAIN_ONLY",
    "working_ref": "main",
    "stable_ref": "main",
    "local_policy": "MANAGED_MIRROR",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def load_contract(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    bootstrap = load_json(root / "profile" / ".agent" / "bootstrap" / "bootstrap.json")
    lock_rel = bootstrap.get("authority_lock")
    if lock_rel != "profile/.agent/bootstrap/authority.lock.json":
        raise ValueError("authority_lock must identify the Foundation repository-relative bootstrap lock")
    lock_path = (root / lock_rel).resolve()
    try:
        lock_path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("authority_lock must stay inside the repository") from exc
    lock = load_json(lock_path)
    return bootstrap, lock


def foundation_control_plane_locator(bootstrap: dict[str, Any]) -> dict[str, str]:
    locator = bootstrap.get("foundation_control_plane")
    expected = {
        "owner": "skills",
        "path": "skills/contracts/FOUNDATION_ARCHITECTURE.md",
    }
    if locator != expected:
        raise ValueError("foundation_control_plane must identify the canonical Foundation control-plane path")
    return dict(expected)

def foundation_control_plane_artifact(
    bootstrap: dict[str, Any], profile_revision: str
) -> dict[str, str]:
    locator = foundation_control_plane_locator(bootstrap)
    return {
        "repository": bootstrap["repository_contract"]["repository"],
        "revision": profile_revision,
        "path": locator["path"],
    }


def validate_local_foundation_control_plane(root: Path, bootstrap: dict[str, Any]) -> None:
    locator = foundation_control_plane_locator(bootstrap)
    path = root / locator["path"]
    if not path.is_file():
        raise ValueError(f"missing Foundation control-plane path: {locator['path']}")

def case_router_locator(bootstrap: dict[str, Any]) -> dict[str, str]:
    locator = bootstrap.get("case_router")
    expected = {
        "owner": "skills",
        "path": "skills/.agent/case-router.yaml",
    }
    if locator != expected:
        raise ValueError("case_router must identify the canonical Foundation skills-domain router path")
    return dict(expected)

def parse_case_router(content: str) -> dict[str, Any]:
    if not isinstance(content, str):
        raise ValueError("malformed Case Router")
    lines = content.splitlines()
    if not lines or lines[0] != "cases:":
        raise ValueError("malformed Case Router")
    cases: list[dict[str, Any]] = []
    index = 1
    while index < len(lines):
        line = lines[index]
        if not line.startswith("  - id: ") or not line[8:]:
            raise ValueError("malformed Case Router")
        case_id = line[8:]
        index += 1
        if index >= len(lines) or lines[index] != "    capabilities:":
            raise ValueError("malformed Case Router")
        index += 1
        capabilities: list[str] = []
        while index < len(lines) and lines[index].startswith("      - "):
            capability = lines[index][8:]
            if not capability:
                raise ValueError("malformed Case Router")
            capabilities.append(capability)
            index += 1
        if not capabilities:
            raise ValueError("malformed Case Router")
        cases.append({"id": case_id, "capabilities": capabilities})
    return {"cases": cases}


def validate_case_router(router: dict[str, Any]) -> None:
    if router != {"cases": [{"id": "EXECUTE", "capabilities": ["executor"]}]}:
        raise ValueError("unauthorized Case Router semantics")


def resolve_case_router(
    bootstrap: dict[str, Any],
    foundation_revision: str,
    resolved: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    locator = case_router_locator(bootstrap)
    observation = resolved.get(FOUNDATION_RESOLVED_KEY)
    if observation is None or observation.get("revision") != foundation_revision:
        raise ValueError(f"unresolvable Foundation authority-set revision: {foundation_revision}")
    paths = observation.get("paths")
    if not isinstance(paths, (set, frozenset)):
        paths = set(paths or [])
    if locator["path"] not in paths:
        raise ValueError(
            f"missing Case Router path: {FOUNDATION_REPOSITORY}@{foundation_revision}:{locator['path']}"
        )
    contents = observation.get("contents")
    if not isinstance(contents, dict) or not isinstance(contents.get(locator["path"]), str):
        raise ValueError(
            f"unresolvable Case Router bytes: {FOUNDATION_REPOSITORY}@{foundation_revision}:{locator['path']}"
        )
    router = parse_case_router(contents[locator["path"]])
    validate_case_router(router)
    return router

def select_case_capability_routes(
    bootstrap: dict[str, Any], router: dict[str, Any], case_id: str
) -> list[dict[str, Any]]:
    if not isinstance(case_id, str):
        raise ValueError("unknown case")
    for case in router["cases"]:
        if case["id"] == case_id:
            return select_capability_routes(bootstrap, case["capabilities"])
    raise ValueError(f"unknown case: {case_id}")


def canonical_artifacts(
    foundation_revision: str,
    lock: dict[str, Any],
    routes: list[dict[str, Any]],
    resolved: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    for route in routes:
        owner = route["owner"]
        if owner in INTERNAL_DOMAINS:
            repository = FOUNDATION_REPOSITORY
            revision = foundation_revision
            resolved_key = FOUNDATION_RESOLVED_KEY
        else:
            entry = lock["repositories"][owner]
            repository = entry["repository"]
            revision = entry["revision"]
            resolved_key = owner
        observation = resolved.get(resolved_key)
        if observation is None or observation.get("revision") != revision:
            raise ValueError(f"unresolvable routed revision: {repository}@{revision}")
        paths = observation.get("paths")
        if not isinstance(paths, (set, frozenset)):
            paths = set(paths or [])
        if route["path"] not in paths:
            raise ValueError(f"missing routed path: {repository}@{revision}:{route['path']}")
        artifacts.append({
            "capability": route["capability"],
            "repository": repository,
            "revision": revision,
            "path": route["path"],
        })
    return artifacts

def validate_contract(bootstrap: dict[str, Any], lock: dict[str, Any]) -> None:
    repositories = lock.get("repositories")
    if not isinstance(repositories, dict):
        raise ValueError("authority lock repositories must be an object")
    legacy_internal = sorted(set(repositories) & LEGACY_INTERNAL_OWNER_ALIASES)
    if legacy_internal:
        raise ValueError(
            f"Foundation-internal semantic owners must not be independently pinned: {legacy_internal}"
        )
    if set(repositories) != set(EXPECTED_EXTERNAL_REPOSITORIES):
        raise ValueError("authority lock must contain exactly the independently versioned external authorities")
    for owner, repository in EXPECTED_EXTERNAL_REPOSITORIES.items():
        entry = repositories.get(owner)
        if not isinstance(entry, dict):
            raise ValueError(f"missing external lock entry: {owner}")
        if entry.get("repository") != repository:
            raise ValueError(f"incorrect external repository identity: {owner}")
        if not SHA_RE.fullmatch(str(entry.get("revision", ""))):
            raise ValueError(f"invalid immutable revision: {owner}")

    case_router_locator(bootstrap)
    foundation_control_plane_locator(bootstrap)

    if bootstrap.get("repository_contract") != EXPECTED_REPOSITORY_CONTRACT:
        raise ValueError("repository_contract must explicitly declare agent-foundation MAIN_ONLY identity")
    if bootstrap.get("bootstrap_default_topology") != "DEV_MAIN":
        raise ValueError("bootstrap default topology must be DEV_MAIN")

    identity = bootstrap.get("authority_set_identity")
    if identity != {
        "source": "AGENT_FOUNDATION_COMMIT",
        "self_pin": False,
        "evolution_ref": "main",
        "activation_ref": "main",
        "rollback": "FORWARD_ACTIVATION_COMMIT",
    }:
        raise ValueError("authority-set identity must use the agent-foundation main lifecycle without self-pin")

    target_binding = bootstrap.get("target_binding")
    if target_binding != {
        "source": "EXPLICIT_CURRENT_REQUEST_OR_EXACT_ACTIVE_BINDING",
        "fresh_github_resolution_required": True,
        "unresolved_action": "ASK_OPERATOR",
        "forbidden_inference_sources": [
            "STALE_CHAT_HISTORY",
            "MEMORY",
            "CWD",
            "LOCAL_DIRECTORY_NAME",
        ],
        "required_fields": ["repository", "branch", "task_path", "task_revision", "base_head", "phase"],
    }:
        raise ValueError("target binding must require explicit current identity and fresh GitHub resolution")

    routes = bootstrap.get("capability_routes")
    if not isinstance(routes, list) or not routes:
        raise ValueError("capability_routes must be a non-empty list")
    seen: set[str] = set()
    for route in routes:
        if not isinstance(route, dict):
            raise ValueError("each capability route must be an object")
        if set(route) != {"capability", "owner", "path"}:
            raise ValueError("capability route must contain exactly capability, owner, and path")
        capability = route["capability"]
        owner = route["owner"]
        path = route["path"]
        if not all(isinstance(value, str) and value for value in (capability, owner, path)):
            raise ValueError("capability route requires capability, owner, and path")
        if capability in seen:
            raise ValueError(f"duplicate capability entrypoint: {capability}")
        seen.add(capability)
        if owner in LEGACY_INTERNAL_OWNER_ALIASES:
            raise ValueError(f"legacy internal revision-selection alias is forbidden: {owner}")
        if owner in INTERNAL_DOMAINS:
            prefix = f"{INTERNAL_DOMAINS[owner]}/"
            if not path.startswith(prefix):
                raise ValueError(f"Foundation-internal capability path must stay inside domain {owner}: {capability}")
        elif owner not in repositories:
            raise ValueError(
                f"capability route owner is neither a Foundation domain nor locked external owner: {owner}"
            )
        if path.startswith("/") or ".." in Path(path).parts:
            raise ValueError(f"capability path must be repository-relative: {capability}")

    surfaces = bootstrap.get("execution_surfaces")
    if not isinstance(surfaces, list):
        raise ValueError("execution_surfaces must be a list")
    actual_ids = {str(surface.get("id")) for surface in surfaces if isinstance(surface, dict)}
    if actual_ids != set(EXPECTED_SURFACES) or len(surfaces) != 4:
        raise ValueError("execution_surfaces must contain exactly the four OPM-01 surfaces")
    normalized_pairs: set[tuple[str, str]] = set()
    for surface in surfaces:
        if not isinstance(surface, dict):
            raise ValueError("execution surface must be an object")
        surface_id = str(surface.get("id"))
        actual = (
            surface.get("controller"),
            surface.get("location"),
            surface.get("transport"),
            surface.get("model"),
            surface.get("effort"),
        )
        if actual != EXPECTED_SURFACES[surface_id]:
            raise ValueError(f"unauthorized execution routing: {surface_id}")
        if surface_id == "AGENT_RUNTIME" or surface.get("controller") == "AGENT_RUNTIME":
            raise ValueError("AGENT_RUNTIME is transport only")
        pair = (str(surface.get("controller")), str(surface.get("location")))
        if pair in normalized_pairs:
            raise ValueError(f"ambiguous execution surface normalization: {pair}")
        normalized_pairs.add(pair)

    task_launch = bootstrap.get("task_launch")
    if not isinstance(task_launch, dict):
        raise ValueError("task_launch must be an object")
    template = task_launch.get("line_template")
    fixtures = task_launch.get("fixtures")
    continuations = task_launch.get("continuations")
    prompt_inputs = task_launch.get("prompt_inputs")
    prompt_template = task_launch.get("prompt_template")
    if not isinstance(template, str) or not isinstance(prompt_template, str) or not isinstance(fixtures, dict):
        raise ValueError("task_launch requires one line_template, one prompt_template, and fixtures")
    if continuations != ["NEW", "CONTINUE"]:
        raise ValueError("task_launch continuations must be exactly NEW and CONTINUE")
    if not isinstance(prompt_inputs, list) or len(prompt_inputs) != len(set(prompt_inputs)):
        raise ValueError("task_launch prompt_inputs must be unique")
    by_id = {surface["id"]: surface for surface in surfaces}
    for surface_id, expected in fixtures.items():
        if surface_id not in by_id:
            raise ValueError(f"fixture has unknown execution surface: {surface_id}")
        if render_task_launch(bootstrap, surface_id, "NEW") != expected:
            raise ValueError(f"TASK LAUNCH fixture mismatch: {surface_id}")
    if set(fixtures) != set(EXPECTED_SURFACES):
        raise ValueError("TASK LAUNCH fixtures must cover all execution surfaces")

def normalize_surface(bootstrap: dict[str, Any], controller: str, location: str) -> dict[str, Any]:
    surfaces = bootstrap.get("execution_surfaces")
    if not isinstance(surfaces, list):
        raise ValueError("execution_surfaces must be a list")
    matches = [
        surface
        for surface in surfaces
        if isinstance(surface, dict)
        and surface.get("controller") == controller
        and surface.get("location") == location
    ]
    if not matches:
        raise ValueError(f"unknown execution surface: {controller}/{location}")
    if len(matches) != 1:
        raise ValueError(f"ambiguous execution surface: {controller}/{location}")
    return dict(matches[0])


def surface_by_id(bootstrap: dict[str, Any], surface_id: str) -> dict[str, Any]:
    matches = [
        surface
        for surface in bootstrap.get("execution_surfaces", [])
        if isinstance(surface, dict) and surface.get("id") == surface_id
    ]
    if len(matches) != 1:
        raise ValueError(f"unknown execution surface: {surface_id}")
    return dict(matches[0])


def render_task_launch(bootstrap: dict[str, Any], surface_id: str, continuation: str) -> str:
    task_launch = bootstrap.get("task_launch")
    if not isinstance(task_launch, dict):
        raise ValueError("task_launch must be an object")
    if continuation not in task_launch.get("continuations", []):
        raise ValueError(f"unknown continuation: {continuation}")
    surface = surface_by_id(bootstrap, surface_id)
    template = task_launch.get("line_template")
    if not isinstance(template, str):
        raise ValueError("task_launch line_template must be a string")
    return template.format(
        continuation=continuation,
        surface=surface_id,
        model=surface["model"],
        effort=surface["effort"],
    )


def render_task_prompt(bootstrap: dict[str, Any], inputs: dict[str, Any]) -> str:
    task_launch = bootstrap.get("task_launch")
    if not isinstance(task_launch, dict):
        raise ValueError("task_launch must be an object")
    required = task_launch.get("prompt_inputs")
    if not isinstance(required, list):
        raise ValueError("task_launch prompt_inputs must be a list")
    if set(inputs) != set(required):
        raise ValueError("TASK LAUNCH prompt requires exactly the canonical locator inputs")
    surface_id = inputs.get("surface")
    if not isinstance(surface_id, str):
        raise ValueError("TASK LAUNCH prompt surface must be a string")
    surface_by_id(bootstrap, surface_id)
    template = task_launch.get("prompt_template")
    if not isinstance(template, str):
        raise ValueError("task_launch prompt_template must be a string")
    return template.format(**inputs)


def select_capability_routes(bootstrap: dict[str, Any], required: list[str]) -> list[dict[str, Any]]:
    routes = bootstrap.get("capability_routes")
    if not isinstance(routes, list):
        raise ValueError("capability_routes must be a list")
    by_capability = {
        route["capability"]: route
        for route in routes
        if isinstance(route, dict) and isinstance(route.get("capability"), str)
    }
    selected: list[dict[str, Any]] = []
    for capability in required:
        route = by_capability.get(capability)
        if route is None:
            raise ValueError(f"unknown capability: {capability}")
        selected.append(dict(route))
    return selected


def required_foundation_paths(bootstrap: dict[str, Any]) -> set[str]:
    paths = {
        "profile/ARCHITECT_PROFILE.md",
        "profile/.agent/bootstrap/bootstrap.json",
        "profile/.agent/bootstrap/authority.lock.json",
        case_router_locator(bootstrap)["path"],
        foundation_control_plane_locator(bootstrap)["path"],
    }
    paths.update(
        route["path"]
        for route in bootstrap["capability_routes"]
        if route["owner"] in INTERNAL_DOMAINS
    )
    return paths


def validate_resolution(
    bootstrap: dict[str, Any],
    lock: dict[str, Any],
    resolved: dict[str, dict[str, Any]],
    foundation_revision: str,
) -> None:
    if not SHA_RE.fullmatch(foundation_revision):
        raise ValueError("authority-set identity must be an exact agent-foundation commit")

    foundation = resolved.get(FOUNDATION_RESOLVED_KEY)
    if foundation is None or foundation.get("revision") != foundation_revision:
        raise ValueError(f"unresolvable Foundation authority-set revision: {foundation_revision}")
    foundation_paths = foundation.get("paths")
    if not isinstance(foundation_paths, (set, frozenset)):
        foundation_paths = set(foundation_paths or [])
    for path in sorted(required_foundation_paths(bootstrap)):
        if path not in foundation_paths:
            raise ValueError(
                f"missing Foundation canonical path: {FOUNDATION_REPOSITORY}@{foundation_revision}:{path}"
            )

    for owner, entry in lock["repositories"].items():
        observation = resolved.get(owner)
        if observation is None or observation.get("revision") != entry["revision"]:
            raise ValueError(f"unresolvable locked revision: {owner}@{entry['revision']}")
        paths = observation.get("paths")
        if not isinstance(paths, (set, frozenset)):
            paths = set(paths or [])
        for route in bootstrap["capability_routes"]:
            if route["owner"] == owner and route["path"] not in paths:
                raise ValueError(f"missing routed path: {owner}@{entry['revision']}:{route['path']}")

    resolve_case_router(bootstrap, foundation_revision, resolved)

def _github_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "architect-profile-opm-validator/1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            value = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ValueError(f"remote resolution failed: {url}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"remote resolution returned non-object: {url}")
    return value


def _github_blob_text(repository: str, blob_sha: str) -> str:
    if not SHA_RE.fullmatch(blob_sha):
        raise ValueError(f"router blob is not immutable: {repository}@{blob_sha}")
    blob = _github_json(f"https://api.github.com/repos/{repository}/git/blobs/{blob_sha}")
    if blob.get("encoding") != "base64" or not isinstance(blob.get("content"), str):
        raise ValueError(f"router blob is malformed: {repository}@{blob_sha}")
    try:
        return base64.b64decode("".join(blob["content"].split()), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise ValueError(f"router blob is malformed: {repository}@{blob_sha}") from exc


def _resolve_remote_repository(repository: str, revision: str) -> tuple[list[dict[str, Any]], set[str]]:
    commit = _github_json(f"https://api.github.com/repos/{repository}/git/commits/{revision}")
    if commit.get("sha") != revision:
        raise ValueError(f"unresolvable immutable revision: {repository}@{revision}")
    tree = commit.get("tree")
    if not isinstance(tree, dict) or not isinstance(tree.get("sha"), str):
        raise ValueError(f"immutable revision has no tree: {repository}@{revision}")
    tree_data = _github_json(
        f"https://api.github.com/repos/{repository}/git/trees/{tree['sha']}?recursive=1"
    )
    if tree_data.get("truncated") is True:
        raise ValueError(f"remote tree is truncated: {repository}@{revision}")
    entries = tree_data.get("tree")
    if not isinstance(entries, list):
        raise ValueError(f"remote tree missing entries: {repository}@{revision}")
    paths = {
        item["path"]
        for item in entries
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    return entries, paths


def resolve_remote(
    bootstrap: dict[str, Any],
    lock: dict[str, Any],
    foundation_revision: str,
) -> dict[str, dict[str, Any]]:
    if not SHA_RE.fullmatch(foundation_revision):
        raise ValueError("authority-set identity must be an exact agent-foundation commit")

    resolved: dict[str, dict[str, Any]] = {}
    entries, paths = _resolve_remote_repository(FOUNDATION_REPOSITORY, foundation_revision)
    router_path = case_router_locator(bootstrap)["path"]
    router_entry = next(
        (item for item in entries if isinstance(item, dict) and item.get("path") == router_path),
        None,
    )
    if not isinstance(router_entry, dict) or not isinstance(router_entry.get("sha"), str):
        raise ValueError(
            f"missing Case Router path: {FOUNDATION_REPOSITORY}@{foundation_revision}:{router_path}"
        )
    resolved[FOUNDATION_RESOLVED_KEY] = {
        "revision": foundation_revision,
        "paths": paths,
        "contents": {
            router_path: _github_blob_text(FOUNDATION_REPOSITORY, router_entry["sha"])
        },
    }

    for owner, entry in lock["repositories"].items():
        repository = entry["repository"]
        revision = entry["revision"]
        _entries, external_paths = _resolve_remote_repository(repository, revision)
        resolved[owner] = {"revision": revision, "paths": external_paths}
    return resolved

def reconstruct_context(
    root: Path,
    profile_revision: str,
    target_locator: dict[str, Any],
    required_capabilities: list[str],
    controller: str,
    location: str,
) -> dict[str, Any]:
    if not SHA_RE.fullmatch(profile_revision):
        raise ValueError("authority-set identity must be an exact agent-foundation commit")
    bootstrap, lock = load_contract(root)
    validate_contract(bootstrap, lock)
    validate_local_foundation_control_plane(root, bootstrap)
    required_target_fields = bootstrap["target_binding"]["required_fields"]
    if set(target_locator) != set(required_target_fields):
        raise ValueError("target locator requires exactly the canonical binding fields")
    for field in ("repository", "branch", "task_path", "base_head", "phase"):
        if not isinstance(target_locator.get(field), str) or not target_locator[field]:
            raise ValueError(f"target locator field must be a non-empty string: {field}")
    if not isinstance(target_locator.get("task_revision"), int) or target_locator["task_revision"] < 1:
        raise ValueError("target locator task_revision must be a positive integer")
    if not SHA_RE.fullmatch(target_locator["base_head"]):
        raise ValueError("target locator base_head must be an exact commit")
    return {
        "authority_set_identity": profile_revision,
        "authority_lock": lock,
        "case_router": case_router_locator(bootstrap),
        "foundation_control_plane": foundation_control_plane_artifact(bootstrap, profile_revision),
        "repository_contract": bootstrap["repository_contract"],
        "target_binding": dict(target_locator),
        "capability_routes": select_capability_routes(bootstrap, required_capabilities),
        "surface": normalize_surface(bootstrap, controller, location),
    }


def reconstruct_execution_context(
    root: Path,
    profile_revision: str,
    target_locator: dict[str, Any],
    case_id: str,
    resolved: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if not SHA_RE.fullmatch(profile_revision):
        raise ValueError("authority-set identity must be an exact agent-foundation commit")
    bootstrap, lock = load_contract(root)
    validate_contract(bootstrap, lock)
    validate_local_foundation_control_plane(root, bootstrap)
    required_target_fields = bootstrap["target_binding"]["required_fields"]
    if set(target_locator) != set(required_target_fields):
        raise ValueError("target locator requires exactly the canonical binding fields")
    for field in ("repository", "branch", "task_path", "base_head", "phase"):
        if not isinstance(target_locator.get(field), str) or not target_locator[field]:
            raise ValueError(f"target locator field must be a non-empty string: {field}")
    if not isinstance(target_locator.get("task_revision"), int) or target_locator["task_revision"] < 1:
        raise ValueError("target locator task_revision must be a positive integer")
    if not SHA_RE.fullmatch(target_locator["base_head"]):
        raise ValueError("target locator base_head must be an exact commit")

    router = resolve_case_router(bootstrap, profile_revision, resolved)
    routes = select_case_capability_routes(bootstrap, router, case_id)
    return {
        "bootstrap_trace": [
            "PROFILE_REVISION",
            "AUTHORITY_LOCK",
            "FOUNDATION_CONTROL_PLANE",
            "CASE_ROUTER",
            "CASE",
            "CAPABILITY_ROUTE",
            "CANONICAL_ARTIFACT",
        ],
        "authority_set_identity": profile_revision,
        "authority_lock": lock,
        "foundation_control_plane": foundation_control_plane_artifact(bootstrap, profile_revision),
        "target_binding": dict(target_locator),
        "case_router": router,
        "case": case_id,
        "capability_routes": routes,
        "canonical_artifacts": canonical_artifacts(profile_revision, lock, routes, resolved),
    }


def current_foundation_revision(root: Path = ROOT) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    revision = result.stdout.strip()
    if result.returncode != 0 or not SHA_RE.fullmatch(revision):
        raise ValueError("current Foundation checkout must resolve one exact HEAD commit")
    return revision


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--remote",
        action="store_true",
        help="also resolve every locked GitHub revision and routed path at that exact revision",
    )
    args = parser.parse_args(argv)
    try:
        bootstrap, lock = load_contract()
        validate_contract(bootstrap, lock)
        validate_local_foundation_control_plane(ROOT, bootstrap)
        if args.remote:
            foundation_revision = current_foundation_revision(ROOT)
            validate_resolution(
                bootstrap,
                lock,
                resolve_remote(bootstrap, lock, foundation_revision),
                foundation_revision,
            )
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        print(f"OPM_BOOTSTRAP = FALSE: {exc}", file=sys.stderr)
        return 1
    print("OPM_BOOTSTRAP = TRUE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
