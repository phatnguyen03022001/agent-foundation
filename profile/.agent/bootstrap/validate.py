#!/usr/bin/env python3
"""Validate and resolve the agent-foundation profile bootstrap contract."""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
GENERIC_TARGET_FIELDS = ("repository", "branch")
TASK_BOUND_TARGET_FIELDS = ("task_path", "task_revision", "base_head", "phase")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

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
L1_NAVIGATION = {
    "research_request_contract": {
        "owner": "skills",
        "path": "skills/templates/research-request.yaml",
    },
    "research_result_contract": {
        "owner": "skills",
        "path": "skills/templates/research-result.yaml",
    },
    "continuity_finding_contract": {
        "owner": "skills",
        "path": "skills/templates/continuity-finding.yaml",
    },
    "execution_continuity_contract": {
        "owner": "skills",
        "path": "skills/contracts/EXECUTION_CONTINUITY.md",
    },
    "execution_continuity_tool": {
        "owner": "skills",
        "path": "skills/scripts/execution_attempt.py",
    },
    "continuity_root": {
        "owner": "profile",
        "path": "profile/.agent/continuity",
    },
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


def external_capability_catalog_locator(bootstrap: dict[str, Any]) -> dict[str, str]:
    locator = bootstrap.get("external_capability_catalog")
    expected = {
        "owner": "skills",
        "path": "skills/.agent/external-capabilities/catalog.json",
    }
    if locator != expected:
        raise ValueError(
            "external_capability_catalog must identify the canonical Foundation external catalog path"
        )
    return dict(expected)


def external_capability_catalog_artifact(
    bootstrap: dict[str, Any], foundation_revision: str
) -> dict[str, str]:
    locator = external_capability_catalog_locator(bootstrap)
    return {
        "repository": bootstrap["repository_contract"]["repository"],
        "revision": foundation_revision,
        "path": locator["path"],
    }


def validate_local_external_capability_catalog(
    root: Path, bootstrap: dict[str, Any]
) -> None:
    locator = external_capability_catalog_locator(bootstrap)
    path = root / locator["path"]
    if not path.is_file():
        raise ValueError(f"missing external capability catalog path: {locator['path']}")
    catalog = load_json(path)
    if (
        catalog.get("schema_version") != 1
        or catalog.get("authority") != "NONE"
        or not isinstance(catalog.get("entries"), list)
    ):
        raise ValueError("external capability catalog is malformed or authoritative")


def l1_navigation_locator(bootstrap: dict[str, Any], key: str) -> dict[str, str]:
    expected = L1_NAVIGATION.get(key)
    if expected is None:
        raise ValueError(f"unknown L1 navigation key: {key}")
    locator = bootstrap.get(key)
    if locator != expected:
        raise ValueError(f"{key} must identify its canonical Foundation repository-relative path")
    return dict(expected)


def l1_navigation_artifacts(
    bootstrap: dict[str, Any], foundation_revision: str
) -> dict[str, dict[str, str]]:
    repository = bootstrap["repository_contract"]["repository"]
    return {
        key: {
            "repository": repository,
            "revision": foundation_revision,
            "path": l1_navigation_locator(bootstrap, key)["path"],
        }
        for key in L1_NAVIGATION
    }


def validate_local_l1_navigation(root: Path, bootstrap: dict[str, Any]) -> None:
    root_real = root.resolve()
    for key in L1_NAVIGATION:
        locator = l1_navigation_locator(bootstrap, key)
        path = (root / locator["path"]).resolve()
        try:
            path.relative_to(root_real)
        except ValueError as exc:
            raise ValueError(f"{key} path escapes the Foundation repository") from exc
        exists = path.is_dir() if key == "continuity_root" else path.is_file()
        if not exists:
            raise ValueError(f"missing canonical L1 navigation path: {key}={locator['path']}")


def case_router_locator(bootstrap: dict[str, Any]) -> dict[str, str]:
    locator = bootstrap.get("case_router")
    expected = {
        "owner": "skills",
        "path": "skills/.agent/case-router.yaml",
    }
    if locator != expected:
        raise ValueError("case_router must identify the canonical Foundation skills-domain router path")
    return dict(expected)

EXPECTED_CASE_ROUTER = {
    "authority": "NONE",
    "routes": [
        {
            "id": "MATERIAL_JUDGMENT",
            "role": "architect",
            "binding": "generic",
            "specialization": None,
            "capabilities": ["architect"],
            "navigation": [],
        },
        {
            "id": "READ_ONLY_RESEARCH",
            "role": "executor",
            "binding": "generic",
            "specialization": "researcher",
            "capabilities": ["executor"],
            "navigation": ["research_request_contract", "research_result_contract"],
        },
        {
            "id": "TASK_EXECUTION",
            "role": "executor",
            "binding": "task",
            "specialization": None,
            "capabilities": ["executor", "task_protocol"],
            "navigation": [],
        },
    ],
    "legacy_aliases": {"EXECUTE": "TASK_EXECUTION"},
}


def parse_case_router(content: str) -> dict[str, Any]:
    if not isinstance(content, str):
        raise ValueError("malformed Case Router")
    lines = [line for line in content.splitlines() if line.strip()]
    legacy_execute = [
        "cases:",
        "  - id: EXECUTE",
        "    capabilities:",
        "      - executor",
    ]
    if lines == legacy_execute:
        return {
            "authority": "NONE",
            "routes": [{
                **EXPECTED_CASE_ROUTER["routes"][2],
                "capabilities": list(EXPECTED_CASE_ROUTER["routes"][2]["capabilities"]),
                "navigation": list(EXPECTED_CASE_ROUTER["routes"][2]["navigation"]),
            }],
            "legacy_aliases": {"EXECUTE": "TASK_EXECUTION"},
        }
    if lines[:2] != ["authority: NONE", "routes:"]:
        raise ValueError("malformed Case Router")

    routes: list[dict[str, Any]] = []
    index = 2
    while index < len(lines) and lines[index].startswith("  - id: "):
        route_id = lines[index][8:]
        if not route_id:
            raise ValueError("malformed Case Router")
        index += 1

        fields: dict[str, str] = {}
        for field in ("role", "binding", "specialization"):
            prefix = f"    {field}: "
            if index >= len(lines) or not lines[index].startswith(prefix):
                raise ValueError("malformed Case Router")
            fields[field] = lines[index][len(prefix):]
            if not fields[field]:
                raise ValueError("malformed Case Router")
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

        if index >= len(lines):
            raise ValueError("malformed Case Router")
        navigation_line = lines[index]
        if navigation_line == "    navigation: none":
            navigation: list[str] = []
            index += 1
        elif navigation_line == "    navigation:":
            index += 1
            navigation = []
            while index < len(lines) and lines[index].startswith("      - "):
                item = lines[index][8:]
                if not item:
                    raise ValueError("malformed Case Router")
                navigation.append(item)
                index += 1
            if not navigation:
                raise ValueError("malformed Case Router")
        else:
            raise ValueError("malformed Case Router")

        routes.append({
            "id": route_id,
            "role": fields["role"],
            "binding": fields["binding"],
            "specialization": None if fields["specialization"] == "none" else fields["specialization"],
            "capabilities": capabilities,
            "navigation": navigation,
        })

    if index >= len(lines) or lines[index] != "legacy_aliases:":
        raise ValueError("malformed Case Router")
    index += 1
    aliases: dict[str, str] = {}
    while index < len(lines) and lines[index].startswith("  - from: "):
        alias = lines[index][10:]
        index += 1
        if not alias or index >= len(lines) or not lines[index].startswith("    to: "):
            raise ValueError("malformed Case Router")
        target = lines[index][8:]
        if not target or alias in aliases:
            raise ValueError("malformed Case Router")
        aliases[alias] = target
        index += 1
    if index != len(lines):
        raise ValueError("malformed Case Router")
    return {"authority": "NONE", "routes": routes, "legacy_aliases": aliases}


def validate_case_router(router: dict[str, Any]) -> None:
    legacy_router = {
        "authority": "NONE",
        "routes": [EXPECTED_CASE_ROUTER["routes"][2]],
        "legacy_aliases": {"EXECUTE": "TASK_EXECUTION"},
    }
    if router not in (EXPECTED_CASE_ROUTER, legacy_router):
        raise ValueError("unauthorized Case Router semantics")


def select_semantic_route(router: dict[str, Any], entry_intent: object) -> dict[str, Any]:
    validate_case_router(router)
    legacy_router = len(router["routes"]) == 1
    if legacy_router:
        if not isinstance(entry_intent, str):
            raise ValueError("legacy Case Router requires explicit EXECUTE task intent")
        route_id = router["legacy_aliases"].get(entry_intent, entry_intent)
        if route_id != "TASK_EXECUTION":
            raise ValueError("legacy Case Router supports only EXECUTE task compatibility")
        return {
            "route": dict(router["routes"][0]),
            "disposition": "LEGACY_EXECUTE_COMPATIBILITY",
        }
    if entry_intent is None:
        return {
            "route": dict(router["routes"][0]),
            "disposition": "DEFAULTED_TO_MATERIAL_JUDGMENT",
        }
    if not isinstance(entry_intent, str):
        raise ValueError("entry intent must identify one unambiguous semantic route")
    route_id = router["legacy_aliases"].get(entry_intent, entry_intent)
    for route in router["routes"]:
        if route["id"] == route_id:
            return {"route": dict(route), "disposition": "EXPLICIT"}
    return {
        "route": dict(router["routes"][0]),
        "disposition": "DEFAULTED_TO_MATERIAL_JUDGMENT",
    }


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
    selection = select_semantic_route(router, case_id)
    if selection["disposition"] not in {"EXPLICIT", "LEGACY_EXECUTE_COMPATIBILITY"}:
        raise ValueError(f"unknown case: {case_id}")
    return select_capability_routes(bootstrap, selection["route"]["capabilities"])


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
    external_capability_catalog_locator(bootstrap)
    for key in L1_NAVIGATION:
        l1_navigation_locator(bootstrap, key)

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
        "generic_required_fields": ["repository", "branch"],
        "task_bound_required_fields": ["task_path", "task_revision", "base_head", "phase"],
    }:
        raise ValueError("target binding must separate generic and task-bound fields and require fresh GitHub resolution")

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
    chat_actions = task_launch.get("chat_actions")
    task_actions = task_launch.get("task_actions")
    prompt_inputs = task_launch.get("prompt_inputs")
    prompt_template = task_launch.get("prompt_template")
    if not isinstance(template, str) or not isinstance(prompt_template, str) or not isinstance(fixtures, dict):
        raise ValueError("task_launch requires one line_template, one prompt_template, and fixtures")
    if chat_actions != ["NEW CHAT", "CONTINUE CHAT"]:
        raise ValueError("task_launch chat_actions must be exactly NEW CHAT and CONTINUE CHAT")
    if task_actions != ["NEW TASK", "CONTINUE TASK"]:
        raise ValueError("task_launch task_actions must be exactly NEW TASK and CONTINUE TASK")
    if not isinstance(prompt_inputs, list) or len(prompt_inputs) != len(set(prompt_inputs)):
        raise ValueError("task_launch prompt_inputs must be unique")
    by_id = {surface["id"]: surface for surface in surfaces}
    if set(fixtures) != set(EXPECTED_SURFACES):
        raise ValueError("TASK LAUNCH fixtures must cover all execution surfaces")
    for surface_id, chat_fixtures in fixtures.items():
        if surface_id not in by_id:
            raise ValueError(f"fixture has unknown execution surface: {surface_id}")
        if not isinstance(chat_fixtures, dict) or set(chat_fixtures) != set(chat_actions):
            raise ValueError(f"TASK LAUNCH fixture chat-action coverage mismatch: {surface_id}")
        for chat_action, task_fixtures in chat_fixtures.items():
            if not isinstance(task_fixtures, dict) or set(task_fixtures) != set(task_actions):
                raise ValueError(
                    f"TASK LAUNCH fixture task-action coverage mismatch: {surface_id}/{chat_action}"
                )
            for task_action, expected in task_fixtures.items():
                if not isinstance(expected, str):
                    raise ValueError(
                        f"TASK LAUNCH fixture must be a string: {surface_id}/{chat_action}/{task_action}"
                    )
                if render_task_launch(
                    bootstrap,
                    surface_id,
                    chat_action,
                    task_action,
                ) != expected:
                    raise ValueError(
                        f"TASK LAUNCH fixture mismatch: {surface_id}/{chat_action}/{task_action}"
                    )

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


def render_task_launch(
    bootstrap: dict[str, Any],
    surface_id: str,
    chat_action: str,
    task_action: str,
) -> str:
    task_launch = bootstrap.get("task_launch")
    if not isinstance(task_launch, dict):
        raise ValueError("task_launch must be an object")
    chat_actions = task_launch.get("chat_actions")
    task_actions = task_launch.get("task_actions")
    if chat_actions != ["NEW CHAT", "CONTINUE CHAT"]:
        raise ValueError("task_launch chat_actions must be exactly NEW CHAT and CONTINUE CHAT")
    if task_actions != ["NEW TASK", "CONTINUE TASK"]:
        raise ValueError("task_launch task_actions must be exactly NEW TASK and CONTINUE TASK")
    if chat_action not in chat_actions:
        raise ValueError(f"unknown chat action: {chat_action}")
    if task_action not in task_actions:
        raise ValueError(f"unknown task action: {task_action}")
    surface = surface_by_id(bootstrap, surface_id)
    template = task_launch.get("line_template")
    if not isinstance(template, str):
        raise ValueError("task_launch line_template must be a string")
    try:
        return template.format(
            chat_action=chat_action,
            task_action=task_action,
            surface=surface_id,
            model=surface["model"],
            effort=surface["effort"],
        )
    except (KeyError, IndexError, ValueError) as exc:
        raise ValueError("malformed task_launch line_template") from exc


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
        external_capability_catalog_locator(bootstrap)["path"],
    }
    paths.update(l1_navigation_locator(bootstrap, key)["path"] for key in L1_NAVIGATION)
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
    token = os.environ.get("GITHUB_TOKEN") or None
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "architect-profile-opm-validator/1",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            value = json.load(response)
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        detail = str(exc)
        if token:
            detail = detail.replace(token, "<redacted>")
        raise ValueError(f"remote resolution failed: {url}: {detail}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"remote resolution returned non-object: {url}")
    return value


def resolve_target_branch(repository: str, branch: str) -> dict[str, str]:
    if not isinstance(repository, str) or not REPOSITORY_RE.fullmatch(repository):
        raise ValueError("target repository must be an explicit owner/repository identity")
    if not isinstance(branch, str) or not branch or branch.strip() != branch:
        raise ValueError("target branch must be an explicit non-empty ref")
    value = _github_json(
        f"https://api.github.com/repos/{repository}/branches/{quote(branch, safe='')}"
    )
    commit = value.get("commit")
    head = commit.get("sha") if isinstance(commit, dict) else None
    if value.get("name") != branch or not isinstance(head, str) or not SHA_RE.fullmatch(head):
        raise ValueError("fresh GitHub target branch resolution is malformed")
    return {"repository": repository, "branch": branch, "head": head}


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

def validate_generic_target_binding(target_binding: dict[str, Any]) -> dict[str, str]:
    if not isinstance(target_binding, dict) or set(target_binding) != set(GENERIC_TARGET_FIELDS):
        raise ValueError("generic target binding requires exactly repository and branch")
    repository = target_binding.get("repository")
    branch = target_binding.get("branch")
    if not isinstance(repository, str) or not REPOSITORY_RE.fullmatch(repository):
        raise ValueError("target repository must be an explicit owner/repository identity")
    if not isinstance(branch, str) or not branch or branch.strip() != branch:
        raise ValueError("target branch must be an explicit non-empty ref")
    return {"repository": repository, "branch": branch}


def validate_task_target_binding(target_binding: dict[str, Any]) -> dict[str, Any]:
    required = {*GENERIC_TARGET_FIELDS, *TASK_BOUND_TARGET_FIELDS}
    if not isinstance(target_binding, dict) or set(target_binding) != required:
        raise ValueError("task-bound target binding requires exact task identity, revision, base, and phase")
    generic = validate_generic_target_binding({
        "repository": target_binding.get("repository"),
        "branch": target_binding.get("branch"),
    })
    for field in ("task_path", "phase"):
        value = target_binding.get(field)
        if not isinstance(value, str) or not value:
            raise ValueError(f"task-bound target field must be a non-empty string: {field}")
    revision = target_binding.get("task_revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise ValueError("task-bound target task_revision must be a positive integer")
    base_head = target_binding.get("base_head")
    if not isinstance(base_head, str) or not SHA_RE.fullmatch(base_head):
        raise ValueError("task-bound target base_head must be an exact commit")
    return {**generic, **{field: target_binding[field] for field in TASK_BOUND_TARGET_FIELDS}}


def reconstruct_entry_context(
    root: Path,
    profile_revision: str,
    target_binding: dict[str, Any],
    request_identity: str | None,
    entry_intent: object,
    resolved: dict[str, dict[str, Any]],
    controller: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    if not SHA_RE.fullmatch(profile_revision):
        raise ValueError("authority-set identity must be an exact agent-foundation commit")
    bootstrap, lock = load_contract(root)
    validate_contract(bootstrap, lock)

    if not isinstance(target_binding, dict):
        raise ValueError("target binding must be an explicit mapping")
    for field in GENERIC_TARGET_FIELDS:
        if field not in target_binding:
            raise ValueError(f"generic target binding requires {field}")
    repository = target_binding.get("repository")
    branch = target_binding.get("branch")
    if not isinstance(repository, str) or not REPOSITORY_RE.fullmatch(repository):
        raise ValueError("target repository must be an explicit owner/repository identity")
    if not isinstance(branch, str) or not branch or branch.strip() != branch:
        raise ValueError("target branch must be an explicit non-empty ref")

    target_resolution = resolve_target_branch(repository, branch)
    router = resolve_case_router(bootstrap, profile_revision, resolved)
    selection = select_semantic_route(router, entry_intent)
    route = selection["route"]

    if route["binding"] == "task":
        bound_target = validate_task_target_binding(target_binding)
        if bound_target["base_head"] != target_resolution["head"]:
            raise ValueError("task-bound base_head does not match fresh GitHub branch resolution")
    else:
        bound_target = validate_generic_target_binding(target_binding)
        if not isinstance(request_identity, str) or not request_identity.strip():
            raise ValueError("generic entry requires an explicit current request identity")

    capabilities = select_capability_routes(bootstrap, route["capabilities"])
    artifacts = canonical_artifacts(profile_revision, lock, capabilities, resolved)
    all_navigation = l1_navigation_artifacts(bootstrap, profile_revision)
    foundation = resolved.get(FOUNDATION_RESOLVED_KEY)
    if foundation is None or foundation.get("revision") != profile_revision:
        raise ValueError(f"unresolvable Foundation authority-set revision: {profile_revision}")
    foundation_paths = foundation.get("paths")
    if not isinstance(foundation_paths, (set, frozenset)):
        foundation_paths = set(foundation_paths or [])
    selected_navigation: dict[str, dict[str, str]] = {}
    for key in route["navigation"]:
        artifact = all_navigation[key]
        if artifact["path"] not in foundation_paths:
            raise ValueError(f"missing routed Foundation navigation path: {artifact['path']}")
        selected_navigation[key] = artifact

    if (controller is None) != (location is None):
        raise ValueError("execution surface requires both controller and location")
    surface = (
        normalize_surface(bootstrap, controller, location)
        if controller is not None and location is not None
        else None
    )
    result = {
        "authority": "NONE",
        "authority_set_identity": profile_revision,
        "target_binding": bound_target,
        "target_resolution": target_resolution,
        "request_identity": request_identity,
        "case_router": router,
        "entry_route": route["id"],
        "role": route["role"],
        "specialization": route["specialization"],
        "route_disposition": selection["disposition"],
        "capability_routes": capabilities,
        "canonical_artifacts": artifacts,
        "l1_navigation": selected_navigation,
    }
    if surface is not None:
        result["surface"] = surface
    return result


def reconstruct_execution_context(
    root: Path,
    profile_revision: str,
    target_locator: dict[str, Any],
    case_id: str,
    resolved: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    result = reconstruct_entry_context(
        root=root,
        profile_revision=profile_revision,
        target_binding=target_locator,
        request_identity=None,
        entry_intent=case_id,
        resolved=resolved,
    )
    result["bootstrap_trace"] = [
        "PROFILE_REVISION",
        "AUTHORITY_LOCK",
        "TARGET_BINDING",
        "CASE_ROUTER",
        "SEMANTIC_ROUTE",
        "CAPABILITY_ROUTE",
        "CANONICAL_ARTIFACT",
    ]
    result["case"] = result["entry_route"]
    return result


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
        validate_local_external_capability_catalog(ROOT, bootstrap)
        validate_local_l1_navigation(ROOT, bootstrap)
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
