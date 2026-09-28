#!/usr/bin/env python3
"""Deterministically index pinned external capability ecosystems without executing upstream code."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
EXTERNAL_DIR = REPO_ROOT / "skills" / ".agent" / "external-capabilities"
REGISTRY_PATH = EXTERNAL_DIR / "sources.json"
CATALOG_PATH = EXTERNAL_DIR / "catalog.json"
SNAPSHOT_DIR = EXTERNAL_DIR / "snapshots"
TASK_VALIDATOR_DIR = REPO_ROOT / "skills" / "scripts"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
FRONTMATTER_KEY_RE = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")
AWESOME_ENTRY_RE = re.compile(
    r"^\s*-\s+\[([^\]]+)\]\((https?://[^)]+)\)(?:\s+[-–—]\s+(.*))?\s*$"
)
EXPECTED_SOURCES = {
    "awesome": {
        "repository": "sindresorhus/awesome",
        "tracking_ref": "main",
        "kind": "discovery_source",
        "license": "CC0-1.0",
        "snapshot": "awesome.json",
        "mode": "awesome_markdown_links",
    },
    "ecc": {
        "repository": "affaan-m/ECC",
        "tracking_ref": "main",
        "kind": "harness_source",
        "license": "MIT",
        "snapshot": "ecc.json",
        "mode": "harness_surfaces",
    },
    "matt-skills": {
        "repository": "mattpocock/skills",
        "tracking_ref": "main",
        "kind": "capability_source",
        "license": "MIT",
        "snapshot": "matt-skills.json",
        "mode": "manifest_promoted_skills",
    },
    "superpowers": {
        "repository": "obra/superpowers",
        "tracking_ref": "main",
        "kind": "capability_source",
        "license": "MIT",
        "snapshot": "superpowers.json",
        "mode": "skill_frontmatter",
    },
}
ECC_INDEXING_POLICY = {
    "mode": "harness_surfaces",
    "surfaces": {
        "skills": "skills/**/SKILL.md",
        "commands": "commands/*.md",
        "agents": "agents/*.md",
    },
    "metadata": [
        ".claude-plugin/plugin.json",
        "docs/COMMAND-REGISTRY.json",
        "manifests/install-components.json",
        "manifests/install-modules.json",
        "manifests/install-profiles.json",
    ],
}
MANAGED_RELATIVE_PATHS = (
    "skills/.agent/external-capabilities/sources.json",
    "skills/.agent/external-capabilities/catalog.json",
    "skills/.agent/external-capabilities/snapshots/ecc.json",
    "skills/.agent/external-capabilities/snapshots/superpowers.json",
    "skills/.agent/external-capabilities/snapshots/matt-skills.json",
    "skills/.agent/external-capabilities/snapshots/awesome.json",
)


class SourceError(RuntimeError):
    """External source data was unavailable or malformed."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SourceError(f"{path} must contain a JSON object")
    return value


def validate_registry(registry: dict[str, Any]) -> list[dict[str, Any]]:
    if set(registry) != {"schema_version", "sources"} or registry.get("schema_version") != 1:
        raise SourceError("source registry must use schema_version 1 and contain only sources")
    sources = registry.get("sources")
    if not isinstance(sources, list):
        raise SourceError("source registry sources must be a list")
    by_id: dict[str, dict[str, Any]] = {}
    required = {
        "id", "repository", "tracking_ref", "snapshot_revision",
        "kind", "license", "indexing_policy",
    }
    for source in sources:
        if not isinstance(source, dict) or set(source) != required:
            raise SourceError("each source registry entry must use the canonical closed schema")
        source_id = source.get("id")
        if not isinstance(source_id, str) or source_id in by_id:
            raise SourceError("source ids must be unique strings")
        by_id[source_id] = source
    if set(by_id) != set(EXPECTED_SOURCES):
        raise SourceError("source registry must contain exactly the four authorized ecosystems")
    normalized: list[dict[str, Any]] = []
    for source_id in sorted(by_id):
        source = by_id[source_id]
        expected = EXPECTED_SOURCES[source_id]
        for field in ("repository", "tracking_ref", "kind", "license"):
            if source.get(field) != expected[field]:
                raise SourceError(f"{source_id}: unauthorized {field}")
        if not SHA_RE.fullmatch(str(source.get("snapshot_revision", ""))):
            raise SourceError(f"{source_id}: snapshot_revision must be an immutable 40-hex commit")
        policy = source.get("indexing_policy")
        if not isinstance(policy, dict) or policy.get("mode") != expected["mode"]:
            raise SourceError(f"{source_id}: unauthorized indexing policy")
        if source_id == "ecc" and policy != ECC_INDEXING_POLICY:
            raise SourceError("ecc: unauthorized indexing policy")
        normalized.append(deepcopy(source))
    return normalized


class GitHubClient:
    def __init__(self) -> None:
        self._token = os.environ.get("GITHUB_TOKEN") or None

    def _request(self, url: str) -> bytes:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "agent-foundation-external-capability-sync/1",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            detail = str(exc)
            if self._token:
                detail = detail.replace(self._token, "<redacted>")
            raise SourceError(f"GitHub source request failed: {url}: {detail}") from exc

    def json(self, url: str) -> Any:
        try:
            return json.loads(self._request(url).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SourceError(f"GitHub returned malformed JSON: {url}: {exc}") from exc

    def tree(self, repository: str, revision: str) -> list[str]:
        value = self.json(
            f"https://api.github.com/repos/{repository}/git/trees/{revision}?recursive=1"
        )
        if not isinstance(value, dict) or value.get("truncated") is True:
            raise SourceError(f"GitHub tree unavailable or truncated: {repository}@{revision}")
        entries = value.get("tree")
        if not isinstance(entries, list):
            raise SourceError(f"GitHub tree missing entries: {repository}@{revision}")
        paths = [
            item["path"]
            for item in entries
            if isinstance(item, dict)
            and item.get("type") == "blob"
            and isinstance(item.get("path"), str)
        ]
        return sorted(paths)

    def text(self, repository: str, revision: str, path: str) -> str:
        encoded = urllib.parse.quote(path, safe="/")
        url = f"https://raw.githubusercontent.com/{repository}/{revision}/{encoded}"
        try:
            return self._request(url).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SourceError(f"upstream text is not UTF-8: {repository}@{revision}:{path}") from exc

    def resolve_ref(self, repository: str, tracking_ref: str) -> str:
        encoded = urllib.parse.quote(tracking_ref, safe="")
        value = self.json(f"https://api.github.com/repos/{repository}/commits/{encoded}")
        revision = value.get("sha") if isinstance(value, dict) else None
        if not isinstance(revision, str) or not SHA_RE.fullmatch(revision):
            raise SourceError(f"tracking ref did not resolve immutably: {repository}@{tracking_ref}")
        return revision


def parse_frontmatter(text: str, source_path: str) -> tuple[str, str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise SourceError(f"missing SKILL.md frontmatter: {source_path}")
    fields: dict[str, str] = {}
    current: str | None = None
    for raw in lines[1:]:
        if raw == "---":
            break
        if raw and not raw[0].isspace():
            match = FRONTMATTER_KEY_RE.match(raw)
            if not match:
                current = None
                continue
            current = match.group(1)
            value = match.group(2).strip()
            if value[:1] in {"'", '"'} and value[-1:] == value[:1] and len(value) >= 2:
                value = value[1:-1]
            fields[current] = value
        elif current in {"name", "description"} and raw.strip():
            fields[current] = (fields.get(current, "") + " " + raw.strip()).strip()
    name = fields.get("name", "").strip()
    description = fields.get("description", "").strip()
    if not name or not description:
        raise SourceError(f"SKILL.md requires name and description metadata: {source_path}")
    return name, description


def capability_entry(
    source: dict[str, Any],
    path: str,
    name: str,
    description: str,
    *,
    id_name: str | None = None,
    surface: str | None = None,
    status: str | None = None,
    invocation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "id": f"{source['id']}:{id_name or name}",
        "source": source["id"],
        "revision": source["snapshot_revision"],
        "source_path": path,
        "kind": "capability",
        "title": name,
        "description": description,
        "license": source["license"],
    }
    if surface is not None:
        entry["surface"] = surface
    if status is not None:
        entry["status"] = status
    if invocation is not None:
        entry["invocation"] = invocation
    return entry


def skill_entries(
    source: dict[str, Any],
    client: GitHubClient,
    paths: list[str],
    *,
    surface: str | None = None,
) -> list[dict[str, Any]]:
    selected = [
        path for path in paths
        if path.startswith("skills/") and path.endswith("/SKILL.md")
    ]
    entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    with ThreadPoolExecutor(max_workers=min(16, max(1, len(selected)))) as pool:
        texts = list(pool.map(
            lambda path: client.text(
                source["repository"], source["snapshot_revision"], path
            ),
            selected,
        ))
    for path, text in zip(selected, texts):
        name, description = parse_frontmatter(text, path)
        entry = capability_entry(
            source,
            path,
            name,
            description,
            surface=surface,
        )
        if entry["id"] in seen_ids:
            raise SourceError(f"duplicate capability id: {entry['id']}")
        seen_ids.add(entry["id"])
        entries.append(entry)
    return sorted(entries, key=lambda item: item["id"])


def summarize_plugin_manifest(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SourceError(f"plugin manifest must be an object: {path}")
    summary = {"path": path}
    for key in ("name", "version", "description", "license"):
        if key in value:
            if not isinstance(value[key], str):
                raise SourceError(f"plugin manifest field must be string: {path}:{key}")
            summary[key] = value[key]
    return summary


def upstream_json(
    source: dict[str, Any],
    client: GitHubClient,
    path: str,
) -> dict[str, Any]:
    try:
        value = json.loads(
            client.text(source["repository"], source["snapshot_revision"], path)
        )
    except json.JSONDecodeError as exc:
        raise SourceError(f"upstream JSON is malformed: {path}") from exc
    if not isinstance(value, dict):
        raise SourceError(f"upstream JSON must be an object: {path}")
    return value


def string_list(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if (
        not isinstance(value, list)
        or (not allow_empty and not value)
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise SourceError(f"{label} must be a string list")
    return list(value)


def build_ecc_agents(
    source: dict[str, Any],
    client: GitHubClient,
    paths: list[str],
) -> list[dict[str, Any]]:
    selected = sorted(
        path for path in paths
        if path.startswith("agents/") and path.endswith(".md")
    )
    with ThreadPoolExecutor(max_workers=min(16, max(1, len(selected)))) as pool:
        texts = list(pool.map(
            lambda path: client.text(
                source["repository"], source["snapshot_revision"], path
            ),
            selected,
        ))
    entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for path, text in zip(selected, texts):
        name, description = parse_frontmatter(text, path)
        entry = capability_entry(
            source,
            path,
            name,
            description,
            id_name=f"agent:{name}",
            surface="agent",
        )
        if entry["id"] in seen_ids:
            raise SourceError(f"duplicate ECC agent id: {entry['id']}")
        seen_ids.add(entry["id"])
        entries.append(entry)
    return sorted(entries, key=lambda item: item["id"])


def build_ecc_commands(
    source: dict[str, Any],
    command_registry: dict[str, Any],
    paths: list[str],
) -> list[dict[str, Any]]:
    if command_registry.get("schemaVersion") != 1:
        raise SourceError("ECC command registry must use schemaVersion 1")
    commands = command_registry.get("commands")
    total = command_registry.get("totalCommands")
    if not isinstance(commands, list) or not isinstance(total, int) or total != len(commands):
        raise SourceError("ECC command registry count is inconsistent")

    entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in commands:
        if not isinstance(item, dict):
            raise SourceError("ECC command registry entries must be objects")
        name = item.get("command")
        description = item.get("description")
        path = item.get("path")
        if not all(isinstance(value, str) and value for value in (name, description, path)):
            raise SourceError("ECC command registry requires command, description, and path")
        if (
            not path.startswith("commands/")
            or not path.endswith(".md")
            or path not in paths
            or Path(path).stem != name
        ):
            raise SourceError(f"ECC command path is invalid or missing: {path}")
        primary_agents = string_list(
            item.get("primaryAgents", []),
            f"ECC command primaryAgents: {name}",
        )
        skills = string_list(
            item.get("skills", []),
            f"ECC command skills: {name}",
        )
        entry = capability_entry(
            source,
            path,
            name,
            description,
            id_name=f"command:{name}",
            surface="command",
            invocation={
                "declared_by": "docs/COMMAND-REGISTRY.json",
                "primary_agents": primary_agents,
                "skills": skills,
            },
        )
        if entry["id"] in seen_ids:
            raise SourceError(f"duplicate ECC command id: {entry['id']}")
        seen_ids.add(entry["id"])
        entries.append(entry)
    return sorted(entries, key=lambda item: item["id"])


def summarize_ecc_plugin_manifest(value: dict[str, Any], path: str) -> dict[str, Any]:
    summary = summarize_plugin_manifest(value, path)
    if value.get("name") != "ecc" or value.get("license") != "MIT":
        raise SourceError("ECC plugin manifest identity is invalid")
    summary["declared_surfaces"] = {
        "commands": string_list(
            value.get("commands"),
            "ECC plugin commands",
            allow_empty=False,
        ),
        "skills": string_list(
            value.get("skills"),
            "ECC plugin skills",
            allow_empty=False,
        ),
    }
    return summary


def summarize_ecc_components(value: dict[str, Any], path: str) -> dict[str, Any]:
    components = value.get("components")
    if not isinstance(value.get("version"), int) or not isinstance(components, list):
        raise SourceError("ECC install components manifest is malformed")
    summarized = []
    for item in components:
        if not isinstance(item, dict):
            raise SourceError("ECC install component must be an object")
        component_id = item.get("id")
        family = item.get("family")
        if not isinstance(component_id, str) or not component_id or not isinstance(family, str):
            raise SourceError("ECC install component identity is malformed")
        summarized.append({
            "id": component_id,
            "family": family,
            "modules": string_list(item.get("modules"), f"ECC component modules: {component_id}"),
        })
    return {
        "path": path,
        "version": value["version"],
        "components": sorted(summarized, key=lambda item: item["id"]),
    }


def summarize_ecc_modules(value: dict[str, Any], path: str) -> dict[str, Any]:
    modules = value.get("modules")
    if not isinstance(value.get("version"), int) or not isinstance(modules, list):
        raise SourceError("ECC install modules manifest is malformed")
    summarized = []
    for item in modules:
        if not isinstance(item, dict):
            raise SourceError("ECC install module must be an object")
        module_id = item.get("id")
        kind = item.get("kind")
        if not isinstance(module_id, str) or not module_id or not isinstance(kind, str):
            raise SourceError("ECC install module identity is malformed")
        summarized.append({
            "id": module_id,
            "kind": kind,
            "paths": string_list(item.get("paths"), f"ECC module paths: {module_id}"),
        })
    return {
        "path": path,
        "version": value["version"],
        "modules": sorted(summarized, key=lambda item: item["id"]),
    }


def summarize_ecc_profiles(value: dict[str, Any], path: str) -> dict[str, Any]:
    profiles = value.get("profiles")
    if not isinstance(value.get("version"), int) or not isinstance(profiles, dict):
        raise SourceError("ECC install profiles manifest is malformed")
    summarized: dict[str, list[str]] = {}
    for name, item in profiles.items():
        if not isinstance(name, str) or not name or not isinstance(item, dict):
            raise SourceError("ECC install profile identity is malformed")
        summarized[name] = string_list(
            item.get("modules"),
            f"ECC profile modules: {name}",
        )
    return {
        "path": path,
        "version": value["version"],
        "profiles": summarized,
    }


def build_ecc(source: dict[str, Any], client: GitHubClient, paths: list[str]) -> dict[str, Any]:
    metadata_paths = source["indexing_policy"]["metadata"]
    missing = [path for path in metadata_paths if path not in paths]
    if missing:
        raise SourceError(f"ECC harness metadata is missing: {missing}")

    plugin_path = ".claude-plugin/plugin.json"
    registry_path = "docs/COMMAND-REGISTRY.json"
    components_path = "manifests/install-components.json"
    modules_path = "manifests/install-modules.json"
    profiles_path = "manifests/install-profiles.json"

    plugin = upstream_json(source, client, plugin_path)
    command_registry = upstream_json(source, client, registry_path)
    components = upstream_json(source, client, components_path)
    modules = upstream_json(source, client, modules_path)
    profiles = upstream_json(source, client, profiles_path)

    skills = skill_entries(source, client, paths, surface="skill")
    commands = build_ecc_commands(source, command_registry, paths)
    agents = build_ecc_agents(source, client, paths)
    entries = sorted(skills + commands + agents, key=lambda item: item["id"])

    return {
        "schema_version": 1,
        "source": provenance(source),
        "indexing": {
            "mode": "harness_surfaces",
            "surfaces": deepcopy(source["indexing_policy"]["surfaces"]),
            "metadata": list(metadata_paths),
            "excluded_activation_surfaces": [
                ".agents/",
                ".claude/",
                ".cursor/",
                ".kiro/",
                "AGENTS.md",
                "CLAUDE.md",
                "hooks/",
                "install.sh",
                "install.ps1",
                "rules/",
                "scripts/install*",
            ],
        },
        "source_metadata": {
            "harness": {
                "activation": "inert_metadata_only",
                "cli_required": False,
                "surface_counts": {
                    "agents": len(agents),
                    "commands": len(commands),
                    "skills": len(skills),
                },
                "plugin_manifest": summarize_ecc_plugin_manifest(plugin, plugin_path),
                "command_registry": {
                    "path": registry_path,
                    "schema_version": command_registry["schemaVersion"],
                    "total_commands": command_registry["totalCommands"],
                },
                "install_metadata": {
                    "components": summarize_ecc_components(components, components_path),
                    "modules": summarize_ecc_modules(modules, modules_path),
                    "profiles": summarize_ecc_profiles(profiles, profiles_path),
                },
            },
        },
        "entries": entries,
    }


def build_superpowers(
    source: dict[str, Any], client: GitHubClient, paths: list[str]
) -> dict[str, Any]:
    manifest_path = ".claude-plugin/plugin.json"
    if manifest_path not in paths:
        raise SourceError("superpowers plugin manifest is missing")
    manifest = json.loads(
        client.text(source["repository"], source["snapshot_revision"], manifest_path)
    )
    behavioral = sorted(
        path for path in paths
        if path.startswith(("hooks/", "commands/"))
        or "bootstrap" in path.lower()
        or ("session" in path.lower() and not path.startswith("skills/"))
    )
    return {
        "schema_version": 1,
        "source": provenance(source),
        "source_metadata": {
            "plugin_manifest": summarize_plugin_manifest(manifest, manifest_path),
            "skill_root": "skills/",
            "non_capability_behavioral_surfaces": behavioral,
        },
        "entries": skill_entries(source, client, paths),
    }


def build_matt(source: dict[str, Any], client: GitHubClient, paths: list[str]) -> dict[str, Any]:
    manifest_path = ".claude-plugin/plugin.json"
    if manifest_path not in paths:
        raise SourceError("Matt skills plugin manifest is missing")
    try:
        manifest = json.loads(
            client.text(source["repository"], source["snapshot_revision"], manifest_path)
        )
    except json.JSONDecodeError as exc:
        raise SourceError("Matt skills plugin manifest is malformed") from exc
    if not isinstance(manifest, dict) or not isinstance(manifest.get("skills"), list):
        raise SourceError("Matt skills plugin manifest must declare promoted skills")
    promoted = manifest["skills"]
    if not promoted or any(not isinstance(item, str) for item in promoted):
        raise SourceError("Matt promoted skill inventory must be a non-empty string list")
    if len(promoted) != len(set(promoted)):
        raise SourceError("Matt promoted skill inventory must not contain duplicates")
    entries: list[dict[str, Any]] = []
    for declared in promoted:
        normalized = declared[2:] if declared.startswith("./") else declared
        skill_path = f"{normalized.rstrip('/')}/SKILL.md"
        if skill_path not in paths:
            raise SourceError(f"Matt promoted skill is missing SKILL.md: {declared}")
        name, description = parse_frontmatter(
            client.text(source["repository"], source["snapshot_revision"], skill_path),
            skill_path,
        )
        entries.append(
            capability_entry(
                source,
                skill_path,
                name,
                description,
                status="promoted",
                invocation={"declared_by": manifest_path},
            )
        )
    ids = [entry["id"] for entry in entries]
    if len(ids) != len(set(ids)):
        raise SourceError("Matt promoted capability ids must be unique")
    return {
        "schema_version": 1,
        "source": provenance(source),
        "source_metadata": {
            "plugin_manifest": summarize_plugin_manifest(manifest, manifest_path),
            "promoted_skill_count": len(promoted),
        },
        "entries": sorted(entries, key=lambda item: item["id"]),
    }


def build_awesome(
    source: dict[str, Any], client: GitHubClient, paths: list[str]
) -> dict[str, Any]:
    readme = source["indexing_policy"].get("readme")
    if not isinstance(readme, str) or readme not in paths:
        raise SourceError("Awesome discovery README is missing")
    text = client.text(source["repository"], source["snapshot_revision"], readme)
    category = "Uncategorized"
    entries: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for raw in text.splitlines():
        if raw.startswith("## "):
            category = raw[3:].strip()
            continue
        match = AWESOME_ENTRY_RE.match(raw)
        if not match:
            continue
        title, url, description = match.groups()
        if url in seen_urls:
            continue
        seen_urls.add(url)
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        entries.append({
            "id": f"awesome:{digest}",
            "source": source["id"],
            "revision": source["snapshot_revision"],
            "discovery_url": url,
            "kind": "discovery",
            "title": title.strip(),
            "description": (description or "").strip(),
            "category": category,
            "license": source["license"],
        })
    if not entries:
        raise SourceError("Awesome discovery README produced no curated links")
    return {
        "schema_version": 1,
        "source": provenance(source),
        "source_metadata": {"readme": readme},
        "entries": sorted(entries, key=lambda item: item["id"]),
    }


def require_capability_entry(entry: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(entry, dict) or entry.get("kind") != "capability":
        raise SourceError("catalog entry is not an admitted capability candidate")
    return entry


def resolve_harness_entry(
    registry: dict[str, Any],
    catalog: dict[str, Any],
    *,
    source_id: str,
    surface: str,
    title: str,
) -> dict[str, Any]:
    sources = {source["id"]: source for source in validate_registry(registry)}
    source = sources.get(source_id)
    if not isinstance(source, dict) or source.get("kind") != "harness_source":
        raise SourceError(f"{source_id}: source is not an admitted harness source")
    if catalog.get("authority") != "NONE" or not isinstance(catalog.get("entries"), list):
        raise SourceError("external catalog must remain inert authority NONE metadata")

    matches = [
        entry for entry in catalog["entries"]
        if isinstance(entry, dict)
        and entry.get("kind") == "capability"
        and entry.get("source") == source_id
        and entry.get("surface") == surface
        and entry.get("title") == title
        and entry.get("revision") == source["snapshot_revision"]
        and isinstance(entry.get("source_path"), str)
        and entry["source_path"]
    ]
    if len(matches) != 1:
        raise SourceError(
            f"{source_id}: expected exactly one pinned harness entry for {surface}:{title}"
        )
    return deepcopy(matches[0])


def provenance(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": source["id"],
        "repository": source["repository"],
        "revision": source["snapshot_revision"],
        "tracking_ref": source["tracking_ref"],
        "kind": source["kind"],
        "license": source["license"],
    }


def build_snapshot(source: dict[str, Any], client: GitHubClient) -> dict[str, Any]:
    paths = client.tree(source["repository"], source["snapshot_revision"])
    if source["id"] == "ecc":
        return build_ecc(source, client, paths)
    if source["id"] == "superpowers":
        return build_superpowers(source, client, paths)
    if source["id"] == "matt-skills":
        return build_matt(source, client, paths)
    if source["id"] == "awesome":
        return build_awesome(source, client, paths)
    raise SourceError(f"unsupported source: {source['id']}")


def build_outputs(
    registry: dict[str, Any], client: GitHubClient
) -> dict[str, str]:
    sources = validate_registry(registry)
    outputs: dict[str, str] = {}
    catalog_entries: list[dict[str, Any]] = []
    generated_from: list[dict[str, Any]] = []
    for source in sources:
        snapshot = build_snapshot(source, client)
        relative = f"skills/.agent/external-capabilities/snapshots/{EXPECTED_SOURCES[source['id']]['snapshot']}"
        outputs[relative] = canonical_json(snapshot)
        catalog_entries.extend(snapshot["entries"])
        generated_from.append(provenance(source))
    ids = [entry["id"] for entry in catalog_entries]
    if len(ids) != len(set(ids)):
        raise SourceError("aggregate external catalog ids must be unique")
    catalog = {
        "schema_version": 1,
        "authority": "NONE",
        "state_model": [
            "INDEXED != LOADED",
            "PINNED != TRUSTED",
            "SYNCED != ADOPTED",
            "ADOPTED != AUTHORIZED",
            "LOADED != AUTHORIZED",
            "SNAPSHOT != AUTHORITY",
        ],
        "generated_from": sorted(generated_from, key=lambda item: item["id"]),
        "entries": sorted(catalog_entries, key=lambda item: item["id"]),
    }
    outputs["skills/.agent/external-capabilities/catalog.json"] = canonical_json(catalog)
    return outputs


def compare_outputs(outputs: dict[str, str], root: Path = REPO_ROOT) -> list[str]:
    mismatches: list[str] = []
    for relative, expected in sorted(outputs.items()):
        path = root / relative
        try:
            actual = path.read_text(encoding="utf-8")
        except OSError:
            mismatches.append(relative)
            continue
        if actual != expected:
            mismatches.append(relative)
    return mismatches


def write_outputs(outputs: dict[str, str], root: Path = REPO_ROOT) -> None:
    allowed = set(MANAGED_RELATIVE_PATHS) - {"skills/.agent/external-capabilities/sources.json"}
    if set(outputs) != allowed:
        raise SourceError("generated output set escaped the authorized external-capability boundary")
    for relative, content in sorted(outputs.items()):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def validate_refresh_authority(document: dict[str, Any]) -> None:
    if document.get("state") != "APPROVED" or document.get("execution_ready") is not True:
        raise SourceError("refresh requires an APPROVED execution-ready task")
    target = document.get("target")
    branch = target.get("branch") if isinstance(target, dict) else None
    if (
        not isinstance(target, dict)
        or target.get("repository") != "phatnguyen03022001/agent-foundation"
        or not isinstance(branch, dict)
        or branch.get("name") != "main"
    ):
        raise SourceError("refresh task must bind agent-foundation main")
    scope = document.get("scope")
    required_changes = scope.get("required_changes") if isinstance(scope, dict) else None
    if not isinstance(required_changes, list) or any(
        not isinstance(item, str) for item in required_changes
    ):
        raise SourceError("refresh task must define structured required changes")
    authorized_scope = "\n".join(required_changes).lower()
    if (
        "skills/.agent/external-capabilities" not in authorized_scope
        and "sync_external_capabilities.py" not in authorized_scope
    ):
        raise SourceError("refresh task does not authorize the external-capability plane")


def load_authorized_task(task_path: str) -> None:
    path = (REPO_ROOT / task_path).resolve()
    try:
        path.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise SourceError("task path must stay inside agent-foundation") from exc
    if not path.is_file():
        raise SourceError("refresh task path does not exist")
    sys.path.insert(0, str(TASK_VALIDATOR_DIR))
    try:
        import validate_skill_library as validator
    finally:
        sys.path.pop(0)
    validator.errors.clear()
    validator.warnings.clear()
    document = validator.load_protocol_path(path, str(path))
    if document is None:
        raise SourceError("refresh task is not parseable by the canonical task validator")
    validator.validate_task_document(str(path), document)
    if validator.errors:
        raise SourceError("refresh task is invalid: " + "; ".join(validator.errors))
    validate_refresh_authority(document)


def refreshed_registry(
    registry: dict[str, Any], client: GitHubClient
) -> dict[str, Any]:
    sources = validate_registry(registry)
    refreshed = {"schema_version": 1, "sources": []}
    for source in sources:
        item = deepcopy(source)
        item["snapshot_revision"] = client.resolve_ref(
            item["repository"], item["tracking_ref"]
        )
        refreshed["sources"].append(item)
    validate_registry(refreshed)
    return refreshed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="regenerate in memory and compare with committed metadata")
    mode.add_argument("--refresh", action="store_true", help="advance tracking refs and rewrite only registry/snapshots/catalog")
    parser.add_argument("--task", help="repository-relative approved task path required for --refresh")
    args = parser.parse_args(argv)
    client = GitHubClient()
    try:
        registry = load_json(REGISTRY_PATH)
        if args.check:
            if args.task:
                raise SourceError("--task is only valid with --refresh")
            outputs = build_outputs(registry, client)
            mismatches = compare_outputs(outputs)
            if mismatches:
                print("EXTERNAL_CAPABILITY_SYNC = STALE", file=sys.stderr)
                for path in mismatches:
                    print(f"  {path}", file=sys.stderr)
                return 1
            print("EXTERNAL_CAPABILITY_SYNC = CURRENT")
            return 0

        if not args.task:
            raise SourceError("--refresh requires --task")
        load_authorized_task(args.task)
        new_registry = refreshed_registry(registry, client)
        outputs = build_outputs(new_registry, client)
        REGISTRY_PATH.write_text(canonical_json(new_registry), encoding="utf-8")
        write_outputs(outputs)
        print("EXTERNAL_CAPABILITY_SYNC = REFRESHED")
        return 0
    except (SourceError, OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"EXTERNAL_CAPABILITY_SYNC = ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
