#!/usr/bin/env python3
"""Validate the curated Agent Skills library and reusable task protocol."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_PROTOCOL_VERSION = 3
STARTING_SKILLS = (
    "adversarial-audit",
    "architect",
    "cloud-run-basics",
    "debugging",
    "design-review",
    "executor",
    "gap-analysis",
    "github-workflow",
    "optimization",
    "reliability",
    "research",
    "reuse-first",
    "security-review",
    "simplicity",
    "verification",
)
RATIONALE_DISPOSITIONS = frozenset({
    "KEEP_FOUNDATION_SPECIFIC",
    "THIN_DELTA",
    "REPLACE_BY_EXTERNAL",
    "RETIRE",
})
MANDATORY_INTERNAL_ROLES = frozenset({"architect", "executor"})
EXTERNAL_DISPOSITIONS = frozenset({"THIN_DELTA", "REPLACE_BY_EXTERNAL"})
INTERNAL_DISPOSITIONS = frozenset({"KEEP_FOUNDATION_SPECIFIC", "THIN_DELTA"})
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
FRONTMATTER_KEYS = frozenset({"name", "description"})
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CAPABILITY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
CATALOG_ROW_RE = re.compile(r"^\| `([a-z0-9-]+)` \|", re.MULTILINE)
KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(.*)$")
INT_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)$")
CATALOG_START = "<!-- SKILL_CATALOG_START -->"
CATALOG_END = "<!-- SKILL_CATALOG_END -->"
RFC3339_UTC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$"
)

CONTINUATION_MODES = frozenset({"MANUAL", "AUTO_UNTIL_STOP"})
CONTINUATION_STOP_CONDITIONS = frozenset({
    "BLOCKED", "STALE_STATE", "AUTHORITY_REQUIRED",
    "CURRENT_PHASE_CAPABILITY_UNAVAILABLE", "REVIEW_REQUIRED",
    "REVERIFY_REQUIRED", "USER_STOP",
})
CAPABILITY_PHASES = frozenset({"EXECUTION", "REVIEW", "VERIFICATION", "PROMOTION", "RELEASE"})
CONTINUATION_PHASES = frozenset({"REVIEW", "VERIFICATION", "PROMOTION", "RELEASE"})
CONTINUATION_ACTIONS = frozenset({
    "REQUEST_ARCHITECT_REVIEW", "RUN_AUTHORITATIVE_VERIFICATION", "PROMOTE_TARGET_REF", "PROMOTE_TO_MAIN",
    "CREATE_VERSION_TAG", "MUTATE_REPOSITORY_METADATA", "PUBLISH_RELEASE", "FINAL_VERIFY", "STOP",
})
CONTINUATION_PHASE_ACTIONS: dict[str, frozenset[str]] = {
    "REVIEW": frozenset({"REQUEST_ARCHITECT_REVIEW", "STOP"}),
    "VERIFICATION": frozenset({"RUN_AUTHORITATIVE_VERIFICATION", "STOP"}),
    "PROMOTION": frozenset({"PROMOTE_TARGET_REF", "PROMOTE_TO_MAIN", "STOP"}),
    "RELEASE": frozenset({
        "CREATE_VERSION_TAG", "MUTATE_REPOSITORY_METADATA", "PUBLISH_RELEASE", "FINAL_VERIFY", "STOP",
    }),
}
LIFECYCLE_STATES = frozenset({
    "PLANNED", "REPORTED", "ACCEPTED", "VERIFIED", "PROMOTED_NOT_RELEASED", "RELEASED",
})
PROGRAM_ARTIFACT_TYPE = "GENERATED_PROGRAM"
PROGRAM_AUTHORITY = "NONE"
PROGRAM_INVALIDATION = "FULL_REGENERATION_ON_MATERIAL_INPUT_CHANGE"
CASE_ROUTER_PATH = ".agent/case-router.yaml"
EXPECTED_CASE_ROUTER: dict[str, Any] = {
    "authority": "NONE",
    "routes": [
        {
            "id": "MATERIAL_JUDGMENT",
            "role": "architect",
            "binding": "generic",
            "specialization": "none",
            "capabilities": ["architect"],
            "navigation": "none",
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
            "specialization": "none",
            "capabilities": ["executor", "task_protocol"],
            "navigation": "none",
        },
    ],
    "legacy_aliases": [{"from": "EXECUTE", "to": "TASK_EXECUTION"}],
}
AGENT_FOUNDATION_PRODUCT_FEATURES = (
    ("F001", "operator-and-architect-configuration", "profile/"),
    ("F002", "governance-control-and-capability", "skills/"),
    ("F003", "documentation-model-and-closure", "documents/"),
    ("F004", "engineering-assurance", "standards/"),
)
AGENT_FOUNDATION_LIFECYCLE_GATES = (
    "scope",
    "specification",
    "implementation",
    "integration",
    "verification",
    "release_readiness",
    "production_acceptance",
)
AGENT_FOUNDATION_LIFECYCLE_STATES = (
    "PLANNED",
    "SPEC_READY",
    "IMPLEMENTING",
    "INTEGRATED",
    "VERIFIED",
    "RELEASE_READY",
    "LIVE",
)
AGENT_FOUNDATION_GATE_STATUSES = frozenset({"PASS", "FAIL", "PENDING", "N/A", "UNKNOWN"})
AGENT_FOUNDATION_MAX_EVIDENCE_REFS = 8
AGENT_FOUNDATION_SYSTEM_GATE_LEAVES = (
    ("foundation", (
        "architecture",
        "dependency_rules",
        "test_infrastructure",
        "telemetry",
        "security",
        "ci",
    )),
    ("integration", (
        "cross_feature_flows",
        "contracts",
        "data_consistency",
        "authorization",
        "external_dependencies",
    )),
    ("verification", (
        "unit",
        "integration",
        "contract",
        "e2e",
        "security",
        "failure_paths",
    )),
    ("hardening", (
        "performance",
        "capacity",
        "security",
        "privacy",
        "observability",
        "slo",
        "alerts",
        "rollback",
        "backup_restore",
        "disaster_recovery",
        "cost",
    )),
    ("production", (
        "deployment",
        "smoke_test",
        "critical_journeys",
        "telemetry",
        "operational_readiness",
    )),
)
AGENT_FOUNDATION_SYSTEM_GATE_MAP = dict(AGENT_FOUNDATION_SYSTEM_GATE_LEAVES)
AGENT_FOUNDATION_PRODUCTION_ACCEPTANCE_LEAVES = (
    "deployment",
    "smoke_test",
    "critical_journeys",
    "telemetry",
)
AGENT_FOUNDATION_PROJECT_PHASES = (
    "P0_SCOPE",
    "P1_FOUNDATION",
    "P2_FEATURE_BUILD",
    "P3_INTEGRATION",
    "P4_VERIFICATION",
    "P5_HARDENING",
    "P6_RELEASE_READY",
    "P7_LIVE",
)

# One normalized semantic model serves both sparse protocol-v3 serialization and
# explicit expanded-v3 task artifacts.  -1 means that no exact-file count cap is
# imposed inside an already-authorized semantic/component boundary.
TASK_NORMALIZATION_DEFAULTS: dict[str, Any] = {
    "scope": {
        "expected_files_are_restrictive": False,
    },
    "structure_policy": {
        "expected_new_files": [],
        "unlisted_new_files": {
            "allowed": True,
            "max": -1,
            "within": [],
            "purpose": "Executor-local structure inside the authorized semantic/component boundary",
        },
        "allow_new_top_level_directories": False,
        "allow_new_shared_modules": False,
    },
    "continuation_policy": {
        "mode": "MANUAL",
        "stop_conditions": [
            "BLOCKED",
            "STALE_STATE",
            "AUTHORITY_REQUIRED",
            "CURRENT_PHASE_CAPABILITY_UNAVAILABLE",
            "REVIEW_REQUIRED",
            "REVERIFY_REQUIRED",
            "USER_STOP",
        ],
    },
    "capability_requirements": {},
    "release_authority": {
        "create_version_tag": False,
        "mutate_repository_metadata": False,
        "publish_release": False,
    },
}

errors: list[str] = []
warnings: list[str] = []


def error(message: str) -> None:
    errors.append(message)


def warning(message: str) -> None:
    warnings.append(message)


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        error(f"{path.relative_to(ROOT)}: missing opening YAML frontmatter delimiter")
        return {}, text
    try:
        closing = lines.index("---", 1)
    except ValueError:
        error(f"{path.relative_to(ROOT)}: missing closing YAML frontmatter delimiter")
        return {}, text

    metadata: dict[str, str] = {}
    for line_no, raw in enumerate(lines[1:closing], start=2):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[:1].isspace() or ":" not in raw:
            error(f"{path.relative_to(ROOT)}:{line_no}: unsupported/invalid frontmatter")
            continue
        key, value = raw.split(":", 1)
        key, value = key.strip(), value.strip()
        if key not in FRONTMATTER_KEYS:
            error(f"{path.relative_to(ROOT)}:{line_no}: unexpected frontmatter key '{key}'")
            continue
        if not value:
            error(f"{path.relative_to(ROOT)}:{line_no}: empty frontmatter value for '{key}'")
            continue
        if key in metadata:
            error(f"{path.relative_to(ROOT)}:{line_no}: duplicate frontmatter key '{key}'")
            continue
        if value[0] in "[{|>" or value.startswith("-"):
            error(f"{path.relative_to(ROOT)}:{line_no}: unsupported frontmatter value syntax for '{key}'")
            continue
        metadata[key] = value.strip("\"'")
    return metadata, text


def validate_links(path: Path, text: str) -> None:
    for target in LINK_RE.findall(text):
        target = target.strip().split("#", 1)[0]
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        resolved = (path.parent / target).resolve()
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError:
            error(f"{path.relative_to(ROOT)}: internal link escapes repository: {target}")
            continue
        if not resolved.exists():
            error(f"{path.relative_to(ROOT)}: broken internal link: {target}")


def _load_json_mapping(path: Path, label: str) -> dict[str, Any] | None:
    if not path.is_file():
        error(f"missing {label}")
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        error(f"{label}: invalid JSON: {exc}")
        return None
    if type(document) is not dict:
        error(f"{label}: top-level JSON document must be mapping")
        return None
    return document


def validate_rationalization() -> frozenset[str]:
    label = ".agent/rationalization.json"
    document = _load_json_mapping(ROOT / ".agent" / "rationalization.json", label)
    if document is None:
        return frozenset()

    if set(document) != {"schema_version", "starting_taxonomy", "dispositions"}:
        error(f"{label}: top-level keys must be exactly schema_version, starting_taxonomy, dispositions")
    if document.get("schema_version") != 1:
        error(f"{label}: schema_version must be 1")

    starting = document.get("starting_taxonomy")
    if type(starting) is not list or any(type(item) is not str for item in starting):
        error(f"{label}: starting_taxonomy must be a string list")
        starting = []
    elif tuple(starting) != STARTING_SKILLS:
        error(f"{label}: starting_taxonomy must exactly match the TASK-0010 starting taxonomy in deterministic order")

    dispositions = document.get("dispositions")
    if type(dispositions) is not list:
        error(f"{label}: dispositions must be a list")
        return frozenset()

    catalog = _load_json_mapping(
        ROOT / ".agent" / "external-capabilities" / "catalog.json",
        ".agent/external-capabilities/catalog.json",
    )
    sources = _load_json_mapping(
        ROOT / ".agent" / "external-capabilities" / "sources.json",
        ".agent/external-capabilities/sources.json",
    )
    catalog_entries = {}
    source_entries = {}
    if catalog is not None and type(catalog.get("entries")) is list:
        catalog_entries = {
            entry.get("id"): entry
            for entry in catalog["entries"]
            if type(entry) is dict and type(entry.get("id")) is str
        }
    if sources is not None and type(sources.get("sources")) is list:
        source_entries = {
            entry.get("id"): entry
            for entry in sources["sources"]
            if type(entry) is dict and type(entry.get("id")) is str
        }

    seen_ids: set[str] = set()
    seen_owners: set[str] = set()
    internal: set[str] = set()
    ordered_ids: list[str] = []

    required_keys = {
        "skill_id",
        "current_path",
        "disposition",
        "rationale",
        "surviving_semantic_owner",
        "external_capability",
    }
    external_keys = {"catalog_entry_id", "repository", "revision", "path"}

    for index, record in enumerate(dispositions):
        prefix = f"{label}: dispositions[{index}]"
        if type(record) is not dict:
            error(f"{prefix}: record must be a mapping")
            continue
        if set(record) != required_keys:
            error(f"{prefix}: record keys must be exactly {sorted(required_keys)}")
            continue

        skill_id = record["skill_id"]
        current_path = record["current_path"]
        disposition = record["disposition"]
        rationale = record["rationale"]
        owner = record["surviving_semantic_owner"]
        external = record["external_capability"]

        if type(skill_id) is not str or skill_id not in STARTING_SKILLS:
            error(f"{prefix}: unknown starting skill id {skill_id!r}")
            continue
        ordered_ids.append(skill_id)
        if skill_id in seen_ids:
            error(f"{label}: duplicate disposition for starting skill {skill_id!r}")
        seen_ids.add(skill_id)

        if current_path != f"{skill_id}/SKILL.md":
            error(f"{prefix}: current_path must be {skill_id}/SKILL.md")
        if disposition not in RATIONALE_DISPOSITIONS:
            error(f"{prefix}: unsupported disposition {disposition!r}")
            continue
        if skill_id in MANDATORY_INTERNAL_ROLES and disposition != "KEEP_FOUNDATION_SPECIFIC":
            error(f"{prefix}: {skill_id} must remain KEEP_FOUNDATION_SPECIFIC")

        if type(rationale) is not str or not rationale.strip():
            error(f"{prefix}: rationale must be non-empty")
        elif len(rationale) > 1600:
            error(f"{prefix}: rationale is not bounded")

        if type(owner) is not str or not owner.strip():
            error(f"{prefix}: surviving_semantic_owner must be non-empty")
        elif owner in seen_owners:
            error(f"{label}: duplicate semantic owner {owner!r}")
        else:
            seen_owners.add(owner)

        if disposition in INTERNAL_DISPOSITIONS:
            internal.add(skill_id)
            if owner != f"internal:{skill_id}":
                error(f"{prefix}: internal disposition must resolve to internal:{skill_id}")
        elif disposition == "REPLACE_BY_EXTERNAL":
            if type(external) is dict and type(external.get("catalog_entry_id")) is str:
                expected_owner = f"external:{external['catalog_entry_id']}"
                if owner != expected_owner:
                    error(f"{prefix}: external replacement owner must be {expected_owner}")
        elif disposition == "RETIRE":
            if type(owner) is not str:
                error(f"{prefix}: RETIRE must identify a resolvable canonical or target-repository owner")
            elif owner.startswith("canonical:"):
                relative = Path(owner.removeprefix("canonical:"))
                target = (ROOT.parent / relative).resolve()
                repository_root = ROOT.parent.resolve()
                try:
                    target.relative_to(repository_root)
                except ValueError:
                    error(f"{prefix}: RETIRE owner escapes Foundation repository")
                else:
                    if not target.exists() and relative.parts[:1] == ("skills",):
                        isolated = (ROOT / Path(*relative.parts[1:])).resolve()
                        try:
                            isolated.relative_to(ROOT.resolve())
                        except ValueError:
                            isolated = target
                        if isolated.exists():
                            target = isolated
                    if not target.exists():
                        error(f"{prefix}: orphaned semantic capability; RETIRE owner does not exist")
            elif owner.startswith("target-repository:") and NAME_RE.fullmatch(owner.removeprefix("target-repository:")):
                architecture = ROOT / "contracts" / "FOUNDATION_ARCHITECTURE.md"
                if not architecture.is_file():
                    error(f"{prefix}: target-repository owner is not resolvable without Foundation Architecture")
            else:
                error(f"{prefix}: RETIRE must identify a resolvable canonical or target-repository owner")

        if disposition in EXTERNAL_DISPOSITIONS:
            if type(external) is not dict:
                error(f"{prefix}: {disposition} requires exact external_capability metadata")
                continue
            if set(external) != external_keys:
                error(f"{prefix}: external_capability keys must be exactly {sorted(external_keys)}")
                continue
            entry_id = external["catalog_entry_id"]
            repository = external["repository"]
            revision = external["revision"]
            path = external["path"]
            if not all(type(value) is str and value for value in (entry_id, repository, revision, path)):
                error(f"{prefix}: external capability identity fields must be non-empty strings")
                continue
            if not SHA40_RE.fullmatch(revision):
                error(f"{prefix}: external revision must be an exact immutable 40-hex SHA")

            entry = catalog_entries.get(entry_id)
            if type(entry) is not dict:
                error(f"{prefix}: external catalog entry {entry_id!r} is missing")
                continue
            source_id = entry.get("source")
            source = source_entries.get(source_id)
            if (
                entry.get("kind") != "capability"
                or type(source) is not dict
                or source.get("kind") not in {"capability_source", "harness_source"}
            ):
                error(f"{prefix}: discovery-only/Awesome entries cannot be adopted")
                continue
            if source_id == "awesome":
                error(f"{prefix}: Awesome is discovery-only and cannot be adopted")
            if entry.get("revision") != revision or source.get("snapshot_revision") != revision:
                error(f"{prefix}: external revision does not match exact pinned catalog/source identity")
            if entry.get("source_path") != path:
                error(f"{prefix}: external path does not match catalog source_path")
            if source.get("repository") != repository:
                error(f"{prefix}: external repository does not match source registry")

            if disposition == "THIN_DELTA":
                skill_path = ROOT / skill_id / "SKILL.md"
                if skill_path.is_file():
                    body = skill_path.read_text(encoding="utf-8")
                    for token in (entry_id, repository, revision, path):
                        if token not in body:
                            error(f"{prefix}: thin-delta skill is missing exact external reference token {token!r}")
        else:
            if external is not None:
                error(f"{prefix}: {disposition} must not declare external_capability metadata")

    missing = set(STARTING_SKILLS) - seen_ids
    extra = seen_ids - set(STARTING_SKILLS)
    if missing or extra:
        error(f"{label}: starting-skill disposition coverage mismatch; missing={sorted(missing)} unexpected={sorted(extra)}")
    if ordered_ids != list(STARTING_SKILLS):
        error(f"{label}: dispositions must use deterministic starting-taxonomy order")

    return frozenset(internal)


def validate_readme_catalog(expected_skills: frozenset[str]) -> None:
    path = ROOT / "README.md"
    if not path.is_file():
        error("missing README.md")
        return
    text = path.read_text(encoding="utf-8")
    if text.count(CATALOG_START) != 1 or text.count(CATALOG_END) != 1:
        error("README.md: skill catalog markers must each appear exactly once")
        validate_links(path, text)
        return
    section = text.split(CATALOG_START, 1)[1].split(CATALOG_END, 1)[0]
    names = CATALOG_ROW_RE.findall(section)
    if len(names) != len(set(names)):
        error("README.md: duplicate skill in catalog")
    if set(names) != expected_skills:
        error(
            "README.md: catalog does not match rationalized internal skill set; "
            f"missing={sorted(expected_skills - set(names))} "
            f"unexpected={sorted(set(names) - expected_skills)}"
        )
    validate_links(path, text)


class ProtocolYamlError(ValueError):
    pass

class UnsupportedProtocolSerializationError(ProtocolYamlError):
    pass


def display_path(path: Path) -> str:
    """Render repository paths compactly while keeping external-file diagnostics useful."""
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def strip_yaml_comment(raw: str) -> str:
    single = double = escaped = False
    for index, char in enumerate(raw):
        if escaped:
            escaped = False
        elif char == "\\" and double:
            escaped = True
        elif char == "'" and not double:
            single = not single
        elif char == '"' and not single:
            double = not double
        elif char == "#" and not single and not double:
            return raw[:index]
    return raw


def preprocess_yaml(path: Path) -> list[tuple[int, int, str]]:
    lines: list[tuple[int, int, str]] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if "\t" in raw:
            raise ProtocolYamlError(f"{display_path(path)}:{number}: tabs are not supported")
        raw = strip_yaml_comment(raw).rstrip()
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent % 2:
            raise ProtocolYamlError(f"{display_path(path)}:{number}: indentation must use two-space steps")
        lines.append((number, indent, raw[indent:]))
    if not lines:
        raise ProtocolYamlError(f"{display_path(path)}: empty YAML document")
    if lines[0][1] != 0:
        raise ProtocolYamlError(f"{display_path(path)}:{lines[0][0]}: top-level content must start at column 1")
    return lines


def parse_flat_flow_list(raw: str, path: Path, number: int) -> list[Any]:
    """Parse the deliberately small flow-list subset used by task artifacts."""
    if not raw.endswith("]"):
        raise ProtocolYamlError(f"{display_path(path)}:{number}: malformed flow list")
    inner = raw[1:-1].strip()
    if not inner:
        return []

    items: list[str] = []
    start = 0
    quote: str | None = None
    escaped = False
    for index, char in enumerate(inner):
        if quote:
            if escaped:
                escaped = False
            elif quote == '"' and char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in ("'", '"'):
            quote = char
        elif char == ",":
            item = inner[start:index].strip()
            if not item:
                raise ProtocolYamlError(f"{display_path(path)}:{number}: malformed flow list")
            items.append(item)
            start = index + 1
    if quote or escaped:
        raise ProtocolYamlError(f"{display_path(path)}:{number}: malformed flow list")
    item = inner[start:].strip()
    if not item:
        raise ProtocolYamlError(f"{display_path(path)}:{number}: malformed flow list")
    items.append(item)

    values: list[Any] = []
    for item in items:
        quoted = item[:1] in ("'", '"')
        if not quoted and (
            item.startswith(("!", "&", "*", "[", "{", "|", ">"))
            or any(indicator in item for indicator in ("[", "]", "{", "}"))
            or re.search(r":\s", item)
        ):
            raise UnsupportedProtocolSerializationError(f"{display_path(path)}:{number}: unsupported flow list item syntax")
        values.append(scalar_value(item, path, number))
    return values


def scalar_value(raw: str, path: Path, number: int) -> Any:
    raw = raw.strip()
    if raw == "[]":
        return []
    if raw == "{}":
        return {}
    if raw in ("true", "false"):
        return raw == "true"
    if raw in ("null", "~"):
        return None
    if INT_RE.fullmatch(raw):
        return int(raw)
    if raw[:1] in ("'", '"'):
        quote = raw[0]
        if len(raw) < 2 or raw[-1] != quote:
            raise ProtocolYamlError(f"{display_path(path)}:{number}: unterminated quoted scalar")
        inner = raw[1:-1]
        escaped = False
        for char in inner:
            if quote == '"' and char == "\\" and not escaped:
                escaped = True
                continue
            if char == quote and not escaped:
                raise ProtocolYamlError(f"{display_path(path)}:{number}: unexpected quote inside quoted scalar")
            escaped = False
        if escaped:
            raise ProtocolYamlError(f"{display_path(path)}:{number}: unterminated escape in quoted scalar")
        return inner
    if raw.startswith("["):
        return parse_flat_flow_list(raw, path, number)
    if raw.startswith(("{", "|", ">", "!", "&", "*")):
        raise UnsupportedProtocolSerializationError(f"{display_path(path)}:{number}: unsupported YAML value syntax")
    return raw


def split_mapping(text: str, path: Path, number: int) -> tuple[str, str]:
    match = KEY_RE.match(text)
    if not match:
        raise ProtocolYamlError(f"{display_path(path)}:{number}: expected mapping key")
    return match.group(1), match.group(2).strip()


def parse_mapping(
    lines: list[tuple[int, int, str]], index: int, indent: int, path: Path
) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    while index < len(lines):
        number, current_indent, text = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise ProtocolYamlError(f"{display_path(path)}:{number}: unexpected indentation")
        if text.startswith("-"):
            break
        key, raw_value = split_mapping(text, path, number)
        if key in result:
            raise ProtocolYamlError(f"{display_path(path)}:{number}: duplicate mapping key '{key}'")
        index += 1
        if raw_value:
            result[key] = scalar_value(raw_value, path, number)
            if index < len(lines) and lines[index][1] > indent:
                raise ProtocolYamlError(
                    f"{display_path(path)}:{lines[index][0]}: scalar '{key}' cannot have nested content"
                )
            continue
        if index >= len(lines) or lines[index][1] <= indent:
            result[key] = None
            continue
        if lines[index][1] != indent + 2:
            raise ProtocolYamlError(
                f"{display_path(path)}:{lines[index][0]}: nested content for '{key}' must indent by two spaces"
            )
        if lines[index][2].startswith("-"):
            result[key], index = parse_sequence(lines, index, indent + 2, path)
        else:
            result[key], index = parse_mapping(lines, index, indent + 2, path)
    return result, index


def parse_sequence(
    lines: list[tuple[int, int, str]], index: int, indent: int, path: Path
) -> tuple[list[Any], int]:
    result: list[Any] = []
    while index < len(lines):
        number, current_indent, text = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise ProtocolYamlError(f"{display_path(path)}:{number}: unexpected indentation in sequence")
        if not text.startswith("-"):
            break
        if text == "-" or not text.startswith("- "):
            raise ProtocolYamlError(f"{display_path(path)}:{number}: malformed sequence item")

        item_text = text[2:].strip()
        index += 1
        mapping_match = KEY_RE.match(item_text)
        if not mapping_match:
            value = scalar_value(item_text, path, number)
            if index < len(lines) and lines[index][1] > indent:
                raise ProtocolYamlError(
                    f"{display_path(path)}:{lines[index][0]}: scalar sequence item cannot have nested content"
                )
            result.append(value)
            continue

        key, raw_value = mapping_match.group(1), mapping_match.group(2).strip()
        item: dict[str, Any] = {}
        if raw_value:
            item[key] = scalar_value(raw_value, path, number)
        else:
            if index >= len(lines) or lines[index][1] <= indent:
                item[key] = None
            else:
                if lines[index][1] != indent + 2:
                    raise ProtocolYamlError(
                        f"{display_path(path)}:{lines[index][0]}: nested sequence mapping must indent by two spaces"
                    )
                if lines[index][2].startswith("-"):
                    item[key], index = parse_sequence(lines, index, indent + 2, path)
                else:
                    item[key], index = parse_mapping(lines, index, indent + 2, path)

        if index < len(lines) and lines[index][1] > indent:
            if lines[index][1] != indent + 2 or lines[index][2].startswith("-"):
                raise ProtocolYamlError(
                    f"{display_path(path)}:{lines[index][0]}: malformed sequence mapping item"
                )
            tail, index = parse_mapping(lines, index, indent + 2, path)
            overlap = set(item) & set(tail)
            if overlap:
                duplicate = sorted(overlap)[0]
                raise ProtocolYamlError(
                    f"{display_path(path)}:{number}: duplicate mapping key '{duplicate}' inside sequence item"
                )
            item.update(tail)
        result.append(item)
    return result, index


def load_protocol_path(path: Path, label: str | None = None, *, unsupported_serialization_is_inconclusive: bool = False) -> dict[str, Any] | None:
    label = label or display_path(path)
    if not path.is_file():
        error(f"{label}: file does not exist")
        return None
    try:
        lines = preprocess_yaml(path)
        if lines[0][2].startswith("-"):
            raise ProtocolYamlError(f"{label}:{lines[0][0]}: top-level document must be a mapping")
        document, index = parse_mapping(lines, 0, 0, path)
        if index != len(lines):
            number, _, _ = lines[index]
            raise ProtocolYamlError(f"{label}:{number}: unexpected content or indentation")
    except UnsupportedProtocolSerializationError as exc:
        if unsupported_serialization_is_inconclusive:
            raise
        error(str(exc))
        return None
    except ProtocolYamlError as exc:
        error(str(exc))
        return None
    return document


def load_protocol_document(relative_path: str) -> dict[str, Any] | None:
    path = ROOT / relative_path
    if not path.is_file():
        error(f"missing required protocol template: {relative_path}")
        return None
    return load_protocol_path(path, relative_path)


def load_json_document(relative_path: str) -> dict[str, Any] | None:
    path = ROOT / relative_path
    if not path.is_file():
        error(f"missing required generated program template: {relative_path}")
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        error(f"{relative_path}: invalid JSON: {exc}")
        return None
    if type(document) is not dict:
        error(f"{relative_path}: top-level JSON document must be mapping")
        return None
    return document


def validate_case_navigation(expected_skills: frozenset[str]) -> None:
    label = CASE_ROUTER_PATH
    document = load_protocol_document(label)
    if document is None:
        return
    if type(document) is not dict:
        error(f"{label}: top-level document must be a mapping")
        return

    expected_fields = set(EXPECTED_CASE_ROUTER)
    actual_fields = set(document)
    if actual_fields != expected_fields:
        error(
            f"{label}: top-level fields must be exactly "
            f"{sorted(expected_fields)}"
        )
    if document.get("authority") != "NONE":
        error(f"{label}: authority must be NONE")

    routes = document.get("routes")
    expected_routes = EXPECTED_CASE_ROUTER["routes"]
    if type(routes) is not list or len(routes) != len(expected_routes):
        error(f"{label}: routes must contain exactly three canonical route classes")
    else:
        for index, (route, expected) in enumerate(zip(routes, expected_routes)):
            if type(route) is not dict:
                error(f"{label}: routes[{index}] must be a mapping")
                continue
            if route != expected:
                error(
                    f"{label}: routes[{index}] must exactly match "
                    f"canonical route {expected['id']}"
                )
    aliases = document.get("legacy_aliases")
    if aliases != EXPECTED_CASE_ROUTER["legacy_aliases"]:
        error(
            f"{label}: legacy_aliases must map EXECUTE to TASK_EXECUTION "
            "exactly once"
        )


_MISSING = object()


def normalize_task_document(document: dict[str, Any]) -> dict[str, Any]:
    """Materialize one canonical meaning for omitted optional task controls."""
    normalized = deepcopy(document)

    scope = normalized.get("scope")
    if type(scope) is dict:
        scope.setdefault(
            "expected_files_are_restrictive",
            TASK_NORMALIZATION_DEFAULTS["scope"]["expected_files_are_restrictive"],
        )

    for key in (
        "structure_policy",
        "continuation_policy",
        "capability_requirements",
        "release_authority",
    ):
        if key not in normalized or normalized[key] == {}:
            normalized[key] = deepcopy(TASK_NORMALIZATION_DEFAULTS[key])

    return normalized

TASK_SEQUENCE_SCHEMAS: dict[str, dict[str, type]] = {
    "authority_sources": {"source": str, "role": str, "precedence": int},
    "acceptance_criteria": {"id": str, "requirement": str, "evidence_required": str},
    "verification.executor_checks": {"id": str, "command_or_check": str, "required": bool},
}
REPORT_SEQUENCE_SCHEMAS: dict[str, dict[str, type]] = {
    "changed_files": {
        "path": str, "summary": str, "new_file": bool,
        "in_scope": bool, "structure_authorized": bool,
    },
    "commits_created": {"sha": str, "message": str},
    "acceptance_evidence": {"criterion_id": str, "status": str, "evidence": str},
    "executor_checks": {"check_id": str, "result": str, "evidence": str},
    "discovered_gaps": {
        "gap_id": str, "classification": str, "type": str, "severity": str,
        "description": str, "evidence": str, "impact": str,
        "blocks_current_task": bool, "action_taken": str, "suggested_next_step": str,
    },
    "structural_observations": {
        "type": str, "path": str, "evidence": str,
        "recommendation": str, "action_taken": str,
    },
}
REVIEW_SEQUENCE_SCHEMAS: dict[str, dict[str, type]] = {
    "gap_disposition": {"gap_id": str, "decision": str, "rationale": str},
    "follow_up_tasks": {"task_id": str, "origin": dict},
}
FOLLOW_UP_ORIGIN_SCHEMA: dict[str, type] = {"type": str, "task_id": str, "gap_id": str}
GAP_CLASSIFICATIONS = frozenset({"LOCAL", "FOLLOW_UP", "BLOCKING"})
REVIEW_STATES = frozenset({"ACCEPTED", "REVISION_REQUIRED", "BLOCKED"})
LOCAL_HYGIENE_RESULTS = frozenset({"PASS", "RETAINED_FOR_EVIDENCE", "BLOCKED"})
LOCAL_HYGIENE_RETAINED_SCHEMA: dict[str, type] = {"identity": str, "reason": str}
CONTINUATION_REF_SCHEMA: dict[str, type] = {"ref": str, "commit": str}
PROGRAM_ITEM_SCHEMA: dict[str, type] = {
    "id": str,
    "traceability": list,
    "depends_on": list,
    "obligations": list,
    "acceptance_refs": list,
    "required_evidence": list,
    "required_capabilities": list,
}
PROGRAM_EXCLUSION_SCHEMA: dict[str, type] = {"ref": str, "rationale": str}
PROGRAM_EXTERNAL_AUTHORITY_SCHEMA: dict[str, type] = {"source": str, "revision": str}


def get_path(document: dict[str, Any], dotted: str) -> Any:
    value: Any = document
    for key in dotted.split("."):
        if not isinstance(value, dict) or key not in value:
            return _MISSING
        value = value[key]
    return value


def require_field(
    label: str,
    document: dict[str, Any],
    dotted: str,
    expected_type: type,
    expected_value: Any = _MISSING,
) -> None:
    value = get_path(document, dotted)
    if value is _MISSING:
        error(f"{label}: missing required path '{dotted}'")
        return
    if type(value) is not expected_type:
        error(f"{label}: path '{dotted}' must be {expected_type.__name__}, got {type(value).__name__}")
        return
    if expected_value is not _MISSING and value != expected_value:
        error(f"{label}: path '{dotted}' must equal {expected_value!r}, got {value!r}")


def require_mapping_schema(
    label: str,
    value: Any,
    item_path: str,
    required_fields: dict[str, type],
    closed_values: dict[str, frozenset[Any]] | None = None,
) -> bool:
    if type(value) is not dict:
        error(f"{label}: path '{item_path}' must be mapping")
        return False

    expected_keys = set(required_fields)
    actual_keys = set(value)
    missing = sorted(expected_keys - actual_keys)
    unexpected = sorted(actual_keys - expected_keys)
    if missing:
        error(f"{label}: path '{item_path}' missing required fields {missing}")
    if unexpected:
        error(f"{label}: path '{item_path}' has unexpected fields {unexpected}")

    valid = not missing and not unexpected
    for field, expected_type in required_fields.items():
        if field not in value:
            continue
        field_value = value[field]
        if type(field_value) is not expected_type:
            error(
                f"{label}: path '{item_path}.{field}' must be {expected_type.__name__}, "
                f"got {type(field_value).__name__}"
            )
            valid = False
            continue
        if closed_values and field in closed_values and field_value not in closed_values[field]:
            error(f"{label}: path '{item_path}.{field}' has unsupported value {field_value!r}")
            valid = False
    return valid


def require_mapping_sequence_schema(
    label: str,
    document: dict[str, Any],
    dotted: str,
    required_fields: dict[str, type],
    closed_values: dict[str, frozenset[Any]] | None = None,
) -> list[tuple[int, dict[str, Any]]]:
    value = get_path(document, dotted)
    if value is _MISSING:
        error(f"{label}: missing required path '{dotted}'")
        return []
    if type(value) is not list:
        error(f"{label}: path '{dotted}' must be list")
        return []

    valid_items: list[tuple[int, dict[str, Any]]] = []
    for index, item in enumerate(value):
        item_path = f"{dotted}[{index}]"
        if require_mapping_schema(label, item, item_path, required_fields, closed_values):
            valid_items.append((index, item))
    return valid_items


def validate_follow_up_tasks(label: str, document: dict[str, Any]) -> None:
    """Validate canonical mappings and the bounded legacy string encoding."""
    value = get_path(document, "follow_up_tasks")
    if value is _MISSING:
        return
    if type(value) is not list:
        error(f"{label}: path 'follow_up_tasks' must be list")
        return

    # Historical protocol-v3 reviews serialized follow-up task references as a
    # non-empty homogeneous list of strings. This is compatibility recognition,
    # not semantic validation of the referenced task or review judgment.
    if value and all(type(item) is str for item in value):
        for index, item in enumerate(value):
            if not item.strip():
                error(f"{label}: path 'follow_up_tasks[{index}]' must be non-empty string")
        return

    # Canonical new reviews use the structured mapping form. Keeping this
    # branch separate makes mixed and malformed representations fail closed.
    items = require_mapping_sequence_schema(
        label, document, "follow_up_tasks", REVIEW_SEQUENCE_SCHEMAS["follow_up_tasks"]
    )
    for index, item in items:
        require_mapping_schema(
            label, item["origin"], f"follow_up_tasks[{index}].origin", FOLLOW_UP_ORIGIN_SCHEMA
        )


def validate_string_list(
    label: str,
    value: Any,
    item_path: str,
    *,
    require_non_empty: bool = False,
) -> list[str]:
    if type(value) is not list:
        error(f"{label}: path '{item_path}' must be list")
        return []
    if require_non_empty and not value:
        error(f"{label}: path '{item_path}' must not be empty")
    valid: list[str] = []
    for index, item in enumerate(value):
        if type(item) is not str or not item.strip():
            error(f"{label}: path '{item_path}[{index}]' must be non-empty string")
            continue
        valid.append(item)
    if len(valid) == len(value) and len(valid) != len(set(valid)):
        error(f"{label}: path '{item_path}' must not contain duplicates")
    return valid


def validate_version(label: str, document: dict[str, Any]) -> None:
    require_field(label, document, "protocol_version", int, SUPPORTED_PROTOCOL_VERSION)


def validate_continuation_policy(label: str, doc: dict[str, Any]) -> None:
    value = get_path(doc, "continuation_policy")
    if value is _MISSING:
        return
    valid = require_mapping_schema(
        label,
        value,
        "continuation_policy",
        {"mode": str, "stop_conditions": list},
    )
    if not valid:
        return
    mode = value["mode"]
    if mode not in CONTINUATION_MODES:
        error(f"{label}: unsupported continuation mode {mode!r}")
    stops = value["stop_conditions"]
    if any(type(item) is not str for item in stops):
        error(f"{label}: path 'continuation_policy.stop_conditions' must contain strings")
        return
    stop_set = set(stops)
    unsupported = sorted(stop_set - CONTINUATION_STOP_CONDITIONS)
    if unsupported:
        error(f"{label}: unsupported continuation stop conditions {unsupported}")
    missing = sorted(CONTINUATION_STOP_CONDITIONS - stop_set)
    if missing:
        error(f"{label}: missing non-waivable continuation stop conditions {missing}")
    if len(stops) != len(stop_set):
        error(f"{label}: continuation_policy.stop_conditions must not contain duplicates")


def validate_capability_requirements(label: str, doc: dict[str, Any]) -> None:
    value = get_path(doc, "capability_requirements")
    if value is _MISSING:
        return
    if type(value) is not dict:
        error(f"{label}: path 'capability_requirements' must be mapping")
        return
    for phase, requirements in value.items():
        if phase not in CAPABILITY_PHASES:
            error(f"{label}: unsupported capability phase {phase!r}")
            continue
        dotted = f"capability_requirements.{phase}"
        if type(requirements) is not list:
            error(f"{label}: path '{dotted}' must be list")
            continue
        if len(requirements) != len(set(map(str, requirements))):
            error(f"{label}: path '{dotted}' must not contain duplicates")
        for item in requirements:
            if type(item) is not str or not CAPABILITY_RE.fullmatch(item):
                error(f"{label}: path '{dotted}' contains invalid semantic capability {item!r}")


def validate_release_authority(label: str, doc: dict[str, Any]) -> None:
    value = get_path(doc, "release_authority")
    if value is _MISSING:
        return
    require_mapping_schema(
        label,
        value,
        "release_authority",
        {
            "create_version_tag": bool,
            "mutate_repository_metadata": bool,
            "publish_release": bool,
        },
    )


def validate_operational_timing(label: str, doc: dict[str, Any]) -> None:
    timing = get_path(doc, "operational_timing")
    if timing is _MISSING:
        return
    valid = require_mapping_schema(
        label,
        timing,
        "operational_timing",
        {
            "started_at_utc": str,
            "terminal_decision_at_utc": str,
        },
    )
    if not valid:
        return
    for field in ("started_at_utc", "terminal_decision_at_utc"):
        value = timing[field]
        if not RFC3339_UTC_RE.fullmatch(value):
            error(f"{label}: path 'operational_timing.{field}' must be RFC 3339 UTC timestamp")
            continue
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            error(f"{label}: path 'operational_timing.{field}' must be a valid RFC 3339 UTC timestamp")


def validate_generated_program_template() -> None:
    label = "templates/program.generated.json"
    doc = load_json_document(label)
    if doc is None:
        return

    top_valid = require_mapping_schema(
        label,
        doc,
        "program",
        {
            "protocol_version": int,
            "artifact_type": str,
            "authority": str,
            "invalidation": str,
            "synthesis": dict,
            "coverage": dict,
            "items": list,
        },
    )
    require_field(label, doc, "protocol_version", int, SUPPORTED_PROTOCOL_VERSION)
    require_field(label, doc, "artifact_type", str, PROGRAM_ARTIFACT_TYPE)
    require_field(label, doc, "authority", str, PROGRAM_AUTHORITY)
    require_field(label, doc, "invalidation", str, PROGRAM_INVALIDATION)
    if not top_valid:
        return

    synthesis = doc["synthesis"]
    synthesis_valid = require_mapping_schema(
        label,
        synthesis,
        "synthesis",
        {"target": dict, "external_authorities": list, "synthesis_policy": dict},
    )
    if synthesis_valid:
        target = synthesis["target"]
        if require_mapping_schema(
            label,
            target,
            "synthesis.target",
            {"repository": str, "source_revision": str},
        ):
            for key in ("repository", "source_revision"):
                if not target[key].strip():
                    error(f"{label}: path 'synthesis.target.{key}' must be non-empty")

        policy = synthesis["synthesis_policy"]
        if require_mapping_schema(
            label,
            policy,
            "synthesis.synthesis_policy",
            {"id": str, "revision": str},
        ):
            for key in ("id", "revision"):
                if not policy[key].strip():
                    error(f"{label}: path 'synthesis.synthesis_policy.{key}' must be non-empty")

        external_seen: set[tuple[str, str]] = set()
        for index, authority in enumerate(synthesis["external_authorities"]):
            item_path = f"synthesis.external_authorities[{index}]"
            if not require_mapping_schema(
                label,
                authority,
                item_path,
                PROGRAM_EXTERNAL_AUTHORITY_SCHEMA,
            ):
                continue
            if not authority["source"].strip() or not authority["revision"].strip():
                error(f"{label}: path '{item_path}' requires non-empty immutable source and revision")
                continue
            identity = (authority["source"], authority["revision"])
            if identity in external_seen:
                error(f"{label}: duplicate external authority identity {identity!r}")
            external_seen.add(identity)

    coverage = doc["coverage"]
    required_refs: list[str] = []
    exclusion_refs: set[str] = set()
    if require_mapping_schema(
        label,
        coverage,
        "coverage",
        {"required_refs": list, "exclusions": list},
    ):
        required_refs = validate_string_list(label, coverage["required_refs"], "coverage.required_refs")
        required_ref_set = set(required_refs)
        for index, exclusion in enumerate(coverage["exclusions"]):
            item_path = f"coverage.exclusions[{index}]"
            if not require_mapping_schema(label, exclusion, item_path, PROGRAM_EXCLUSION_SCHEMA):
                continue
            ref = exclusion["ref"]
            rationale = exclusion["rationale"]
            if not ref.strip() or not rationale.strip():
                error(f"{label}: path '{item_path}' requires non-empty ref and bounded rationale")
                continue
            if ref in exclusion_refs:
                error(f"{label}: duplicate exclusion ref {ref!r}")
            exclusion_refs.add(ref)
            if ref not in required_ref_set:
                error(f"{label}: exclusion ref {ref!r} is not present in coverage.required_refs")

    item_ids: set[str] = set()
    item_dependencies: dict[str, list[str]] = {}
    covered_refs: set[str] = set()
    required_ref_set = set(required_refs)
    for index, item in enumerate(doc["items"]):
        item_path = f"items[{index}]"
        if not require_mapping_schema(label, item, item_path, PROGRAM_ITEM_SCHEMA):
            continue
        item_id = item["id"]
        if not item_id.strip():
            error(f"{label}: path '{item_path}.id' must be non-empty")
            continue
        if item_id in item_ids:
            error(f"{label}: duplicate generated item id {item_id!r}")
        item_ids.add(item_id)

        traceability = validate_string_list(
            label, item["traceability"], f"{item_path}.traceability", require_non_empty=True
        )
        dependencies = validate_string_list(label, item["depends_on"], f"{item_path}.depends_on")
        obligations = validate_string_list(label, item["obligations"], f"{item_path}.obligations")
        validate_string_list(
            label, item["acceptance_refs"], f"{item_path}.acceptance_refs", require_non_empty=True
        )
        validate_string_list(
            label, item["required_evidence"], f"{item_path}.required_evidence", require_non_empty=True
        )
        capabilities = validate_string_list(
            label, item["required_capabilities"], f"{item_path}.required_capabilities"
        )
        for capability in capabilities:
            if not CAPABILITY_RE.fullmatch(capability):
                error(f"{label}: path '{item_path}.required_capabilities' contains invalid semantic capability {capability!r}")

        item_dependencies[item_id] = dependencies
        covered_refs.update(traceability)
        covered_refs.update(obligations)
        for ref in traceability + obligations:
            if ref not in required_ref_set:
                error(f"{label}: item {item_id!r} references unselected coverage ref {ref!r}")

    for item_id, dependencies in item_dependencies.items():
        for dependency in dependencies:
            if dependency not in item_ids:
                error(f"{label}: item {item_id!r} depends on unknown item {dependency!r}")
            if dependency == item_id:
                error(f"{label}: item {item_id!r} cannot depend on itself")

    graph = {
        item_id: [dependency for dependency in dependencies if dependency in item_ids]
        for item_id, dependencies in item_dependencies.items()
    }
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(item_id: str) -> bool:
        if item_id in visiting:
            return True
        if item_id in visited:
            return False
        visiting.add(item_id)
        for dependency in graph.get(item_id, []):
            if visit(dependency):
                return True
        visiting.remove(item_id)
        visited.add(item_id)
        return False

    if any(visit(item_id) for item_id in graph):
        error(f"{label}: dependency graph must be acyclic")

    for ref in required_refs:
        covered = ref in covered_refs
        excluded = ref in exclusion_refs
        if not covered and not excluded:
            error(f"{label}: required coverage ref {ref!r} is neither covered nor excluded")
        if covered and excluded:
            error(f"{label}: coverage ref {ref!r} cannot be both covered and excluded")


def validate_foundation_architecture_contract() -> None:
    path = ROOT / "contracts" / "FOUNDATION_ARCHITECTURE.md"
    label = "contracts/FOUNDATION_ARCHITECTURE.md"
    if not path.is_file():
        error(f"missing {label}")
        return
    text = path.read_text(encoding="utf-8")
    layer_headings = re.findall(r"^## L\d+ — .+$", text, flags=re.MULTILINE)
    expected_layers = [
        "## L0 — Governance Kernel",
        "## L1 — Control and Continuity",
        "## L2 — Capability and Knowledge",
    ]
    if layer_headings != expected_layers:
        error(f"{label}: must define exactly the canonical L0/L1/L2 layer headings")
    required = (
        "exactly two organizational roles: Architect and Executor",
        "Sync and read-only Researcher are Executor specializations",
        "INDEXED != LOADED",
        "PINNED != TRUSTED",
        "SYNCED != ADOPTED",
        "ADOPTED != AUTHORIZED",
        "LOADED != AUTHORIZED",
        "SNAPSHOT != AUTHORITY",
        "one exact target, base, and question",
        "only minimum relevant context",
        "peer results are not visible",
        "compact evidence",
        "not by majority voting",
        "cannot mutate the owner repository",
        "create a task automatically",
        "freshly revalidated",
        "orthogonal substrates",
        "fourth Foundation layer",
    )
    for token in required:
        if token not in text:
            error(f"{label}: missing required architecture invariant {token!r}")
    validate_links(path, text)

    architect_owner_references = (
        "[Task Protocol — Core bindings](../protocols/TASK_PROTOCOL.md#core-bindings)",
        "[Task Protocol — Artifact ownership and authority](../protocols/TASK_PROTOCOL.md#artifact-ownership-and-authority)",
        "[Task Protocol — Phase-specific capability preflight](../protocols/TASK_PROTOCOL.md#phase-specific-capability-preflight)",
        "[Foundation Architecture — Target repository product authority](../contracts/FOUNDATION_ARCHITECTURE.md#target-repository-product-authority)",
        "[Foundation Architecture — Target product progression consumption](../contracts/FOUNDATION_ARCHITECTURE.md#target-product-progression-consumption)",
        "[Foundation Architecture — Capability control](../contracts/FOUNDATION_ARCHITECTURE.md#capability-control)",
        "[Architect Review — Review ownership and exact report identity](../contracts/ARCHITECT_REVIEW.md#review-ownership-and-exact-report-identity)",
        "[Architect Review — Review artifact obligations](../contracts/ARCHITECT_REVIEW.md#review-artifact-obligations)",
        "[Execution Continuity — Recovery](../contracts/EXECUTION_CONTINUITY.md#recovery)",
        "[Simplicity — Stable governance and change admission](../simplicity/SKILL.md#stable-governance-and-change-admission)",
        "[Verification — Acceptance and evidence](../verification/SKILL.md#acceptance-and-evidence)",
    )
    architect_text = (ROOT / "architect" / "SKILL.md").read_text(encoding="utf-8")
    for reference in architect_owner_references:
        if reference not in architect_text:
            error(f"architect/SKILL.md: missing required Architect owner reference {reference!r}")



    executor_owner_references = (
        "[Task Protocol — Core bindings](../protocols/TASK_PROTOCOL.md#core-bindings)",
        "[Task Protocol — Artifact ownership and authority](../protocols/TASK_PROTOCOL.md#artifact-ownership-and-authority)",
        "[Task Protocol — Executor-binding terminal vs whole-task lifecycle](../protocols/TASK_PROTOCOL.md#executor-binding-terminal-vs-whole-task-lifecycle)",
        "[Task Protocol — Phase-specific capability preflight](../protocols/TASK_PROTOCOL.md#phase-specific-capability-preflight)",
        "[Task Protocol — Consequence-based execution guards](../protocols/TASK_PROTOCOL.md#consequence-based-execution-guards)",
        "[Task Protocol — GitHub/local drift](../protocols/TASK_PROTOCOL.md#githublocal-drift)",
        "[Task Protocol — Local Hygiene Contract](../protocols/TASK_PROTOCOL.md#local-hygiene-contract)",
        "[Task Protocol — Protocol-v3 candidate/report publication closure](../protocols/TASK_PROTOCOL.md#protocol-v3-candidatereport-publication-closure)",
        "[Foundation Architecture — Target repository product authority](../contracts/FOUNDATION_ARCHITECTURE.md#target-repository-product-authority)",
        "[Foundation Architecture — Capability control](../contracts/FOUNDATION_ARCHITECTURE.md#capability-control)",
        "[Foundation Architecture — Execution surface and publication control](../contracts/FOUNDATION_ARCHITECTURE.md#execution-surface-and-publication-control)",
        "[Implementation Report — Ownership and commit identity](../contracts/IMPLEMENTATION_REPORT.md#ownership-and-commit-identity)",
        "[Implementation Report — Required evidence](../contracts/IMPLEMENTATION_REPORT.md#required-evidence)",
        "[Implementation Report — Backward-compatible operational timing evidence](../contracts/IMPLEMENTATION_REPORT.md#backward-compatible-operational-timing-evidence)",
        "[Execution Continuity — Execution Slice](../contracts/EXECUTION_CONTINUITY.md#execution-slice)",
        "[Execution Continuity — Optional performance attribution](../contracts/EXECUTION_CONTINUITY.md#optional-performance-attribution)",
        "[Execution Continuity — Carrier and long-running execution](../contracts/EXECUTION_CONTINUITY.md#carrier-and-long-running-execution)",
        "[Execution Continuity — Recovery](../contracts/EXECUTION_CONTINUITY.md#recovery)",
        "[Executor Engineering HOW — Repository construction and acquisition](references/ENGINEERING_HOW.md#repository-construction-and-acquisition)",
        "[Executor Engineering HOW — Process/resource ownership boundary](references/ENGINEERING_HOW.md#processresource-ownership-boundary)",
    )
    executor_text = (ROOT / "executor" / "SKILL.md").read_text(encoding="utf-8")
    for reference in executor_owner_references:
        if reference not in executor_text:
            error(f"executor/SKILL.md: missing required Executor owner reference {reference!r}")

    role_requirements = {
        "architect/SKILL.md": ("../contracts/FOUNDATION_ARCHITECTURE.md", "Capability control and reusable HOW"),
        "executor/SKILL.md": ("../contracts/FOUNDATION_ARCHITECTURE.md", "Capability HOW and acquisition"),
        "protocols/TASK_PROTOCOL.md": ("../contracts/FOUNDATION_ARCHITECTURE.md", "Execution capability and authority boundary"),
    }
    forbidden_headings = {
        "architect/SKILL.md": ("## External normative authority and execution environment",),
        "executor/SKILL.md": ("## Repository construction and acquisition",),
        "protocols/TASK_PROTOCOL.md": (
            "## Execution environment, operator attention, and surface selection",
            "## Deterministic execution bundling",
        ),
    }
    for relative, tokens in role_requirements.items():
        role_text = (ROOT / relative).read_text(encoding="utf-8")
        for token in tokens:
            if token not in role_text:
                error(f"{relative}: missing Foundation architecture delegation marker {token!r}")
        for heading in forbidden_headings[relative]:
            if heading in role_text:
                error(f"{relative}: L1/L2 detail remains duplicated under {heading!r}")

def validate_task_document(label: str, doc: dict[str, Any]) -> None:
    doc = normalize_task_document(doc)
    validate_version(label, doc)
    for dotted, expected_type in [
        ("task_id", str), ("task_revision", int), ("state", str),
        ("origin.type", str), ("origin.task_id", str), ("origin.gap_id", str),
        ("architect_binding.target_repository", str), ("target.repository", str),
        ("target.branch.name", str), ("target.branch.role", str),
        ("execution_base.mode", str), ("execution_base.capture", str),
        ("execution_base.require_exact_match", bool),
        ("skill_library.repository", str), ("skill_library.revision", str),
        ("architect_analysis_skills", list),
        ("execution_skills.required", list), ("execution_skills.recommended", list),
        ("external_skills.architect_analysis", list),
        ("external_skills.execution_required", list),
        ("external_skills.execution_recommended", list),
        ("structure_authority.status", str), ("structure_authority.source", str),
        ("structure_authority.rationale", str), ("objective", str),
        ("scope.required_changes", list),
        ("scope.allowed_existing_files_or_components", list),
        ("scope.expected_files_are_restrictive", bool),
        ("invariants", list), ("forbidden_changes", list),
        ("gap_policy.local_auto_fix", bool),
        ("gap_policy.scope_expansion", str), ("gap_policy.architecture_change", str),
        ("gap_policy.spec_change", str), ("gap_policy.dependency_change", str),
        ("gap_policy.public_contract_change", str),
        ("gap_policy.blocking_gap_behavior", str),
        ("structure_policy.expected_new_files", list),
        ("structure_policy.unlisted_new_files.allowed", bool),
        ("structure_policy.unlisted_new_files.max", int),
        ("structure_policy.unlisted_new_files.within", list),
        ("structure_policy.unlisted_new_files.purpose", str),
        ("structure_policy.allow_new_top_level_directories", bool),
        ("structure_policy.allow_new_shared_modules", bool),
        ("verification.authoritative_verification", dict),
        ("verification.authoritative_verification.required", bool),
        ("verification.authoritative_verification.mechanism", str),
        ("verification.authoritative_verification.expected_signal", str),
        ("git_authority.create_branch", bool), ("git_authority.commit", bool),
        ("git_authority.push", bool), ("git_authority.promote_to_main", bool),
        ("blocking_decisions", list), ("execution_ready", bool),
    ]:
        require_field(label, doc, dotted, expected_type)
    for dotted, schema in TASK_SEQUENCE_SCHEMAS.items():
        if dotted == "verification.executor_checks" and get_path(doc, dotted) is _MISSING:
            continue
        require_mapping_sequence_schema(label, doc, dotted, schema)
    require_field(label, doc, "execution_base.mode", str, "handoff_snapshot")
    require_field(label, doc, "execution_base.require_exact_match", bool, True)
    require_field(label, doc, "gap_policy.blocking_gap_behavior", str, "BLOCKED")

    validate_continuation_policy(label, doc)
    validate_capability_requirements(label, doc)
    validate_release_authority(label, doc)

    bound = get_path(doc, "architect_binding.target_repository")
    target = get_path(doc, "target.repository")
    if bound is not _MISSING and target is not _MISSING and bound != target:
        error(f"{label}: architect binding must equal target repository")

    status = get_path(doc, "structure_authority.status")
    source = get_path(doc, "structure_authority.source")
    rationale = get_path(doc, "structure_authority.rationale")
    ready = get_path(doc, "execution_ready")
    if status is not _MISSING and status not in {"RESOLVED", "NOT_APPLICABLE", "UNRESOLVED"}:
        error(f"{label}: unsupported structure_authority.status {status!r}")
    if status == "RESOLVED" and not source:
        error(f"{label}: RESOLVED structure authority requires non-empty source")
    if status == "NOT_APPLICABLE" and not rationale:
        error(f"{label}: NOT_APPLICABLE structure authority requires non-empty rationale")
    if status == "UNRESOLVED" and ready is True:
        error(f"{label}: UNRESOLVED structure authority cannot be execution-ready")
    if ready is True and get_path(doc, "git_authority.commit") is not True:
        error(f"{label}: execution-ready task requires Executor git_authority.commit for canonical report evidence")


def validate_task_template() -> None:
    label = "templates/task.yaml"
    doc = load_protocol_document(label)
    if doc is not None:
        validate_task_document(label, doc)


def validate_handoff_template() -> None:
    label = "templates/handoff.yaml"
    doc = load_protocol_document(label)
    if doc is None:
        return
    validate_version(label, doc)
    for dotted, expected_type in [
        ("handoff_type", str), ("task.id", str), ("task.revision", int),
        ("task.path", str), ("target.repository", str), ("target.branch", str),
        ("target.base_head", str),
    ]:
        require_field(label, doc, dotted, expected_type)
    require_field(label, doc, "handoff_type", str, "EXECUTOR")


def validate_report_document(label: str, doc: dict[str, Any]) -> None:
    validate_version(label, doc)
    for dotted, expected_type in [
        ("task_id", str), ("task_revision", int), ("report_revision", int),
        ("state", str), ("task_source.path", str), ("execution.repository", str),
        ("execution.branch.name", str), ("execution.branch.role", str),
        ("execution.authorized_base_head", str), ("execution.final_execution_head", str),
        ("skill_library.repository", str), ("skill_library.authorized_revision", str),
        ("pushed", bool),
        ("authoritative_verification", dict),
        ("authoritative_verification.required", bool),
        ("authoritative_verification.performed", bool),
        ("authoritative_verification.result", str),
        ("authoritative_verification.evidence", str),
        ("result", str),
    ]:
        require_field(label, doc, dotted, expected_type)

    for dotted, expected_type in [
        ("execution.pre_execution_head", str),
        ("skill_library.observed_revision", str),
        ("promoted_to_main", bool),
    ]:
        value = get_path(doc, dotted)
        if value is not _MISSING and type(value) is not expected_type:
            error(f"{label}: path '{dotted}' must be {expected_type.__name__}, got {type(value).__name__}")

    execution_skills = get_path(doc, "execution_skills_used")
    if execution_skills is not _MISSING:
        require_mapping_schema(
            label,
            execution_skills,
            "execution_skills_used",
            {"required": list, "recommended": list, "external": list},
        )

    pre_checks = get_path(doc, "pre_execution_checks")
    if pre_checks is not _MISSING:
        require_mapping_schema(
            label,
            pre_checks,
            "pre_execution_checks",
            {
                "protocol_version_supported": bool,
                "handoff_type_confirmed": bool,
                "task_at_base_confirmed": bool,
                "task_identity_confirmed": bool,
                "architect_binding_confirmed": bool,
                "repository_confirmed": bool,
                "branch_confirmed": bool,
                "base_head_confirmed": bool,
                "skill_revision_confirmed": bool,
                "required_execution_skills_available": bool,
                "structure_authority_confirmed": bool,
                "working_tree_clean": bool,
            },
        )

    working_tree_after = get_path(doc, "working_tree_after")
    if working_tree_after is not _MISSING:
        require_mapping_schema(
            label,
            working_tree_after,
            "working_tree_after",
            {"clean": bool, "summary": str},
        )

    optional_sequences = {"changed_files", "commits_created", "discovered_gaps", "structural_observations", "executor_checks"}
    for dotted, schema in REPORT_SEQUENCE_SCHEMAS.items():
        if dotted in optional_sequences and get_path(doc, dotted) is _MISSING:
            continue
        closed_values = {"classification": GAP_CLASSIFICATIONS} if dotted == "discovered_gaps" else None
        require_mapping_sequence_schema(label, doc, dotted, schema, closed_values)
    for dotted in ("deviations_from_task", "blockers"):
        value = get_path(doc, dotted)
        if value is not _MISSING and type(value) is not list:
            error(f"{label}: path '{dotted}' must be list")
    require_field(label, doc, "state", str, "REPORTED")

    preflight = get_path(doc, "capability_preflight")
    if preflight is not _MISSING:
        valid = require_mapping_schema(
            label,
            preflight,
            "capability_preflight",
            {"phase": str, "required": list, "available": list, "missing": list, "passed": bool},
        )
        if valid and preflight["phase"] not in CAPABILITY_PHASES:
            error(f"{label}: unsupported capability phase {preflight['phase']!r}")

    hygiene = get_path(doc, "local_hygiene")
    if hygiene is not _MISSING:
        valid = require_mapping_schema(
            label,
            hygiene,
            "local_hygiene",
            {
                "result": str,
                "run_root": str,
                "cleanup_performed": bool,
                "retained": list,
                "evidence": str,
            },
        )
        if valid:
            result = hygiene["result"]
            if result not in LOCAL_HYGIENE_RESULTS:
                error(f"{label}: unsupported local hygiene result {result!r}")
            retained = hygiene["retained"]
            for index, item in enumerate(retained):
                item_valid = require_mapping_schema(
                    label,
                    item,
                    f"local_hygiene.retained[{index}]",
                    LOCAL_HYGIENE_RETAINED_SCHEMA,
                )
                if item_valid and (not item["identity"] or not item["reason"]):
                    error(f"{label}: retained local hygiene artifact requires non-empty identity and reason")
            if result == "PASS" and retained:
                error(f"{label}: PASS local hygiene cannot retain artifacts")
            if result == "RETAINED_FOR_EVIDENCE" and not retained:
                error(f"{label}: RETAINED_FOR_EVIDENCE requires retained artifact identity and reason")

    validate_operational_timing(label, doc)


def validate_report_template() -> None:
    label = "templates/report.yaml"
    doc = load_protocol_document(label)
    if doc is not None:
        validate_report_document(label, doc)


def validate_review_document(label: str, doc: dict[str, Any]) -> None:
    validate_version(label, doc)
    for dotted, expected_type in [
        ("task_id", str), ("task_revision", int), ("review_revision", int),
        ("state", str), ("reviewed_report.repository", str),
        ("reviewed_report.path", str), ("reviewed_report.commit", str),
        ("reviewed_report.report_revision", int),
        ("contract_compliance.protocol_version", str),
        ("contract_compliance.identity", str),
        ("contract_compliance.execution_base", str),
        ("contract_compliance.skill_rules", str),
        ("contract_compliance.scope", str),
        ("contract_compliance.structure_policy", str),
        ("contract_compliance.git_authority", str),
        ("contract_compliance.acceptance_criteria", str),
        ("contract_compliance.verifier_evidence", str),
    ]:
        require_field(label, doc, dotted, expected_type)
    for dotted, schema in REVIEW_SEQUENCE_SCHEMAS.items():
        if dotted == "follow_up_tasks":
            validate_follow_up_tasks(label, doc)
            continue
        if get_path(doc, dotted) is _MISSING:
            continue
        require_mapping_sequence_schema(label, doc, dotted, schema)

    promotion_readiness = get_path(doc, "promotion_readiness")
    if promotion_readiness is not _MISSING:
        require_mapping_schema(
            label,
            promotion_readiness,
            "promotion_readiness",
            {"eligible_for_candidate_capture": bool, "reason": str},
        )

    notes = get_path(doc, "notes")
    if notes is not _MISSING and type(notes) is not list:
        error(f"{label}: path 'notes' must be list")

    validate_operational_timing(label, doc)

    independence = get_path(doc, "independence")
    if independence is not _MISSING:
        valid = require_mapping_schema(
            label,
            independence,
            "independence",
            {
                "reviewer_role": str,
                "separate_session_from_executor": bool,
                "exact_report_identity_verified": bool,
            },
        )
        if valid:
            if independence["reviewer_role"] != "ARCHITECT":
                error(f"{label}: independence.reviewer_role must equal 'ARCHITECT'")
            if independence["separate_session_from_executor"] is not True:
                error(f"{label}: independent review requires separate_session_from_executor=true")

    state = get_path(doc, "state")
    eligible = get_path(doc, "promotion_readiness.eligible_for_candidate_capture")
    if state is not _MISSING and state not in REVIEW_STATES:
        error(f"{label}: unsupported review state {state!r}")
    if state == "ACCEPTED":
        exact_identity = get_path(doc, "independence.exact_report_identity_verified")
        if exact_identity is not True:
            error(f"{label}: ACCEPTED review requires independence.exact_report_identity_verified=true")
    if eligible is True and state != "ACCEPTED":
        error(f"{label}: only ACCEPTED review may be candidate-eligible")


def validate_review_template() -> None:
    label = "templates/review.yaml"
    doc = load_protocol_document(label)
    if doc is not None:
        validate_review_document(label, doc)


def validate_continuation_template() -> None:
    label = "templates/continuation.yaml"
    doc = load_protocol_document(label)
    if doc is None:
        return
    validate_version(label, doc)
    for dotted, expected_type in [
        ("handoff_type", str),
        ("task.id", str), ("task.revision", int), ("task.path", str),
        ("phase", str),
        ("reviewed_report.repository", str), ("reviewed_report.path", str),
        ("reviewed_report.commit", str), ("reviewed_report.report_revision", int),
        ("promotion_candidate_head", str),
        ("expected_state.lifecycle", str),
        ("prior_result", str), ("prior_lifecycle_state", str),
        ("next_authorized_action", str),
    ]:
        require_field(label, doc, dotted, expected_type)
    require_field(label, doc, "handoff_type", str, "CONTINUATION")

    expected_refs = get_path(doc, "expected_refs")
    canonical_ref_names: set[str] = set()
    legacy_expected_refs = False
    if expected_refs is _MISSING:
        error(f"{label}: missing required path 'expected_refs'")
    elif type(expected_refs) is list:
        items = require_mapping_sequence_schema(label, doc, "expected_refs", CONTINUATION_REF_SCHEMA)
        for index, item in items:
            ref = item["ref"]
            commit = item["commit"]
            if not ref or not commit:
                error(f"{label}: expected_refs[{index}] requires non-empty ref and commit identity")
            canonical_ref_names.add(ref)
    elif type(expected_refs) is dict:
        legacy_expected_refs = True
        require_field(label, doc, "expected_refs.dev", str)
        require_field(label, doc, "expected_refs.main", str)
    else:
        error(f"{label}: path 'expected_refs' must be canonical list or legacy dev/main mapping")

    phase = get_path(doc, "phase")
    if phase is not _MISSING and phase not in CONTINUATION_PHASES:
        error(f"{label}: unsupported continuation phase {phase!r}")
    expected_lifecycle = get_path(doc, "expected_state.lifecycle")
    if expected_lifecycle is not _MISSING and expected_lifecycle not in LIFECYCLE_STATES:
        error(f"{label}: unsupported expected lifecycle state {expected_lifecycle!r}")
    lifecycle = get_path(doc, "prior_lifecycle_state")
    if lifecycle is not _MISSING and lifecycle not in LIFECYCLE_STATES:
        error(f"{label}: unsupported lifecycle state {lifecycle!r}")
    if (
        type(expected_lifecycle) is str
        and type(lifecycle) is str
        and expected_lifecycle != lifecycle
    ):
        error(f"{label}: expected_state.lifecycle must equal prior_lifecycle_state for the bound snapshot")

    action = get_path(doc, "next_authorized_action")
    if action is not _MISSING and action not in CONTINUATION_ACTIONS:
        error(f"{label}: unsupported next authorized action {action!r}")
    if phase in CONTINUATION_PHASE_ACTIONS and action in CONTINUATION_ACTIONS:
        if action not in CONTINUATION_PHASE_ACTIONS[phase]:
            error(f"{label}: action {action!r} is not valid for continuation phase {phase!r}")

    if action == "PROMOTE_TO_MAIN" and not legacy_expected_refs:
        error(f"{label}: PROMOTE_TO_MAIN is legacy compatibility input and requires expected_refs.dev/main")
    if action == "PROMOTE_TARGET_REF":
        if type(expected_refs) is not list:
            error(f"{label}: PROMOTE_TARGET_REF requires canonical topology-neutral expected_refs")
        target_ref = get_path(doc, "promotion_target_ref")
        if type(target_ref) is not str or not target_ref:
            error(f"{label}: PROMOTE_TARGET_REF requires non-empty promotion_target_ref")
        elif target_ref not in canonical_ref_names:
            error(f"{label}: promotion_target_ref must identify a ref present in expected_refs")


def validate_template_consistency() -> None:
    docs = {
        name: load_protocol_document(f"templates/{name}.yaml")
        for name in ("task", "handoff", "report", "review", "continuation")
    }
    if any(doc is None for doc in docs.values()):
        return
    task = docs["task"]
    assert task is not None
    task_id = task.get("task_id")
    task_revision = task.get("task_revision")
    for name in ("handoff", "continuation"):
        doc = docs[name]
        assert doc is not None
        nested = doc.get("task")
        if not isinstance(nested, dict) or nested.get("id") != task_id or nested.get("revision") != task_revision:
            error(f"templates/{name}.yaml: task identity must match templates/task.yaml")
    for name in ("report", "review"):
        doc = docs[name]
        assert doc is not None
        if doc.get("task_id") != task_id or doc.get("task_revision") != task_revision:
            error(f"templates/{name}.yaml: task identity must match templates/task.yaml")


def require_tokens(path: Path, tokens: list[str]) -> None:
    if not path.is_file():
        error(f"missing required protocol file: {path.relative_to(ROOT)}")
        return
    text = path.read_text(encoding="utf-8")
    for token in tokens:
        if token not in text:
            error(f"{path.relative_to(ROOT)}: missing required protocol term '{token}'")
    validate_links(path, text)


def validate_protocol_docs() -> None:
    require_tokens(ROOT / "protocols" / "TASK_PROTOCOL.md", [
        "Supported protocol version", "one active target repository",
        "Decision ownership and consequence-based materiality",
        "implementation judgment and local HOW by default",
        "Uncertainty, unfamiliarity, or a preference difference alone is not an escalation trigger",
        "Protocol-v3 task normalization/defaults",
        "same protocol-v3 semantic model",
        "missing authority remains fail-closed",
        "semantic/component boundary",
        "A newly discovered companion surface",
        "Local structure is Executor-owned",
        "material structure and remain Architect-owned",
        "LOCAL needs no Architect approval",
        "simultaneous ambiguous active target is forbidden",
        "explicit terminal handoff/result", "fresh repository-local task",
        "fresh exact handoff", "fresh exact base HEAD",
        "authority for repository A never grants authority for repository B",
        "report/review/verifier/promotion/release lineage remains repository-local",
        "PROGRAM", "ordered repository-local tasks",
        "not a universal multi-repository task authority",
        "program.generated.json", "authority: NONE", "mathematically unique DAG",
        "whole generated program stale", "fully regenerate", "Task authority remains just in time",
        "two organizational roles", "Executor specializations",
        "templates/handoff.yaml", "templates/continuation.yaml", "handoff_snapshot",
        "RESOLVED", "NOT_APPLICABLE", "UNRESOLVED", "promotion_candidate_head",
        "REVERIFY / REVIEW_REQUIRED", "LOCAL", "FOLLOW_UP",
        "No orphan source files", "No speculative scale structure",
        "reviewed_report.commit", "single-parent direct child",
        "shared trusted", "create_branch: false", "PROMOTED_NOT_RELEASED",
        "AUTO_UNTIL_STOP", "CURRENT_PHASE_CAPABILITY_UNAVAILABLE",
        "capability_requirements", "release_authority", "RELEASED",
        "GitHub Actions must not become an iterative debugger",
        "Tool availability is not permission to consume quota",
        "Normal Executor reports are evidence indexes",
        "changed-file enumeration may be omitted",
        "omission never means PASS, permission, or hidden success",
        "Sparse reports remain evidence-backed rather than self-attested",
        "Evidence-first Architect review",
        "Deep implementation reconstruction occurs only for",
        "preference-only revision",
        "Operational timing is omitted by default",
        "explicitly requests",
        "No timing-enabled or telemetry-mode field",
    ])
    require_tokens(ROOT / "architect" / "SKILL.md", [
        "material WHAT, BOUNDARY, and PROOF",
        "delegates implementation judgment to Executor by default",
        "uncertainty alone does not require escalation",
        "normalization/default table",
        "Omitted implementation prescription",
        "one active target repository", "close the current repository-specific phase",
        "explicitly identify the next `owner/repo`", "refresh canonical GitHub truth",
        "discard previous repository-specific assumptions",
        "simultaneous ambiguous active target is forbidden",
        "PROGRAM", "program.generated.json", "full regeneration", "just in time",
        "PROMPT TO COPY",
        "evidence-first sequence", "candidate diff boundary", "material risk triggers",
        "stop when material predicates are proven", "preference-only revision",
        "default hot path", "explicitly requests", "No timing-enabled or telemetry-mode field",
    ])
    require_tokens(ROOT / "executor" / "SKILL.md", [
        "implementation judgment belongs to Executor by default",
        "smallest sufficient repo-native implementation",
        "LOCAL needs no Architect approval",
        "automatic pre-mutation blockers",
        "active task/repository binding remains immutable",
        "EXECUTION BUNDLE",
        "maximal contiguous mechanically derivable suffix",
        "one `terminal_exec` invocation",
        "Omit reconstructible execution transcript",
    ])
    require_tokens(ROOT / "README.md", [
        "PROGRAM", "presentation only", "ordered repository-local tasks",
        "program.generated.json", "authority `NONE`",
        "TASK LAUNCH",
    ])
    require_tokens(ROOT / "contracts" / "IMPLEMENTATION_CONTRACT.md", [
        "positive semantic/component scope",
        "normalization/default table",
        "Missing exact-file or local-structure prescription",
        "Missing authority fields never default to permission",
        "template", "continuation_policy", "capability_requirements", "release_authority",
    ])
    require_tokens(ROOT / "contracts" / "IMPLEMENTATION_REPORT.md", [
        "template", "capability_preflight", "PROMOTED_NOT_RELEASED",
        "compact evidence index", "changed-file enumeration may be omitted",
        "omission never means PASS, permission, or hidden success", "explicitly requests",
        "No timing-enabled or telemetry-mode field",
    ])
    require_tokens(ROOT / "contracts" / "ARCHITECT_REVIEW.md", [
        "template", "separate agent/session", "PROMOTED_NOT_RELEASED",
        "evidence-first", "candidate diff boundary", "deviations/gaps",
        "material risk triggers", "stop when material predicates are proven",
        "preference-only revision", "omitted by default", "explicitly requests",
        "No timing-enabled or telemetry-mode field",
    ])


def _require_exact_object_keys(label: str, value: Any, expected: set[str]) -> bool:
    if not isinstance(value, dict):
        error(f"{label}: expected object")
        return False
    actual = set(value)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing:
        error(f"{label}: missing keys {missing}")
    if unexpected:
        error(f"{label}: unexpected keys {unexpected}")
    return not missing and not unexpected


def _derive_agent_foundation_feature_state(gates: list[dict[str, Any]]) -> str | None:
    consecutive_passes = 0
    for gate in gates:
        if gate.get("status") != "PASS":
            break
        consecutive_passes += 1
    if consecutive_passes == 0:
        return None
    return AGENT_FOUNDATION_LIFECYCLE_STATES[consecutive_passes - 1]


def _derive_agent_foundation_gate_aggregate(
    leaves: list[dict[str, Any]],
    expected_names: tuple[str, ...],
) -> str:
    if type(leaves) is not list or len(leaves) != len(expected_names):
        raise ValueError("malformed system-gate leaf inventory")
    statuses: list[str] = []
    for expected_name, leaf in zip(expected_names, leaves):
        if not isinstance(leaf, dict) or leaf.get("name") != expected_name:
            raise ValueError("malformed or non-canonical system-gate leaf order")
        status = leaf.get("status")
        if status not in AGENT_FOUNDATION_GATE_STATUSES:
            raise ValueError("unsupported system-gate leaf status")
        statuses.append(status)
    if "FAIL" in statuses:
        return "FAIL"
    if "UNKNOWN" in statuses:
        return "UNKNOWN"
    if "PENDING" in statuses:
        return "PENDING"
    if all(status == "N/A" for status in statuses):
        return "N/A"
    if all(status in {"PASS", "N/A"} for status in statuses) and any(status == "PASS" for status in statuses):
        return "PASS"
    raise ValueError("system-gate aggregate is not derivable")


def _agent_foundation_group_leaves(document: dict[str, Any], group_name: str) -> list[dict[str, Any]]:
    system_gates = document.get("system_gates")
    if not isinstance(system_gates, dict):
        raise ValueError("missing system_gates")
    group = system_gates.get(group_name)
    if not isinstance(group, dict):
        raise ValueError(f"missing system gate group {group_name}")
    leaves = group.get("leaves")
    if type(leaves) is not list:
        raise ValueError(f"malformed system gate group {group_name}")
    return leaves


def _derive_agent_foundation_group_status(document: dict[str, Any], group_name: str) -> str:
    leaves = _agent_foundation_group_leaves(document, group_name)
    expected_names = AGENT_FOUNDATION_SYSTEM_GATE_MAP[group_name]
    if group_name == "production":
        acceptance = [
            leaf for leaf in leaves
            if isinstance(leaf, dict) and leaf.get("name") in AGENT_FOUNDATION_PRODUCTION_ACCEPTANCE_LEAVES
        ]
        return _derive_agent_foundation_gate_aggregate(
            acceptance,
            AGENT_FOUNDATION_PRODUCTION_ACCEPTANCE_LEAVES,
        )
    return _derive_agent_foundation_gate_aggregate(leaves, expected_names)


def _normalize_agent_foundation_required_feature_ids(document: dict[str, Any]) -> list[str] | None:
    release = document.get("release")
    if not isinstance(release, dict):
        return None
    if release.get("required_feature_ids_resolution") != "KNOWN":
        return None
    required = release.get("required_feature_ids")
    if type(required) is not list:
        return None
    if any(type(feature_id) is not str for feature_id in required):
        raise ValueError("required_feature_ids must contain only feature IDs")
    if len(required) != len(set(required)):
        raise ValueError("required_feature_ids contains duplicates")
    canonical = [feature_id for feature_id, _, _ in AGENT_FOUNDATION_PRODUCT_FEATURES]
    foreign = sorted(set(required) - set(canonical))
    if foreign:
        raise ValueError(f"required_feature_ids contains foreign IDs {foreign}")
    selected = set(required)
    return [feature_id for feature_id in canonical if feature_id in selected]


def _agent_foundation_feature_by_id(document: dict[str, Any], feature_id: str) -> dict[str, Any]:
    registered = (
        document.get("product_scope", {})
        .get("features", {})
        .get("registered", [])
    )
    if type(registered) is not list:
        raise ValueError("malformed feature registry")
    for feature in registered:
        if isinstance(feature, dict) and feature.get("id") == feature_id:
            return feature
    raise ValueError(f"required feature is not registered: {feature_id}")


def _agent_foundation_feature_state(document: dict[str, Any], feature_id: str) -> str | None:
    feature = _agent_foundation_feature_by_id(document, feature_id)
    lifecycle = feature.get("lifecycle")
    if not isinstance(lifecycle, dict) or type(lifecycle.get("gates")) is not list:
        raise ValueError(f"malformed lifecycle for {feature_id}")
    return _derive_agent_foundation_feature_state(lifecycle["gates"])


def _agent_foundation_feature_below(
    document: dict[str, Any],
    feature_id: str,
    threshold: str,
) -> bool:
    state = _agent_foundation_feature_state(document, feature_id)
    if state is None:
        return True
    return AGENT_FOUNDATION_LIFECYCLE_STATES.index(state) < AGENT_FOUNDATION_LIFECYCLE_STATES.index(threshold)


def _derive_agent_foundation_project_phase(document: dict[str, Any]) -> str:
    release = document.get("release")
    if not isinstance(release, dict):
        return "P0_SCOPE"
    required_raw = release.get("required_feature_ids")
    if (
        release.get("status") != "FROZEN"
        or release.get("required_feature_ids_resolution") != "KNOWN"
        or type(required_raw) is not list
    ):
        return "P0_SCOPE"

    required = _normalize_agent_foundation_required_feature_ids(document)
    assert required is not None

    if _derive_agent_foundation_group_status(document, "foundation") != "PASS":
        return "P1_FOUNDATION"
    if any(_agent_foundation_feature_below(document, feature_id, "INTEGRATED") for feature_id in required):
        return "P2_FEATURE_BUILD"
    if _derive_agent_foundation_group_status(document, "integration") != "PASS":
        return "P3_INTEGRATION"
    if (
        any(_agent_foundation_feature_below(document, feature_id, "VERIFIED") for feature_id in required)
        or _derive_agent_foundation_group_status(document, "verification") != "PASS"
    ):
        return "P4_VERIFICATION"
    if (
        any(_agent_foundation_feature_below(document, feature_id, "RELEASE_READY") for feature_id in required)
        or _derive_agent_foundation_group_status(document, "hardening") != "PASS"
    ):
        return "P5_HARDENING"

    production_leaves = _agent_foundation_group_leaves(document, "production")
    operational = next(
        (
            leaf for leaf in production_leaves
            if isinstance(leaf, dict) and leaf.get("name") == "operational_readiness"
        ),
        None,
    )
    operational_status = operational.get("status") if isinstance(operational, dict) else None
    if (
        any(_agent_foundation_feature_below(document, feature_id, "LIVE") for feature_id in required)
        or _derive_agent_foundation_group_status(document, "production") != "PASS"
        or operational_status != "PASS"
    ):
        return "P6_RELEASE_READY"
    return "P7_LIVE"


def _first_unmet_agent_foundation_feature_gate(
    document: dict[str, Any],
    feature_id: str,
    final_gate: str,
) -> str:
    feature = _agent_foundation_feature_by_id(document, feature_id)
    gates = feature.get("lifecycle", {}).get("gates", [])
    limit = AGENT_FOUNDATION_LIFECYCLE_GATES.index(final_gate)
    for gate in gates[: limit + 1]:
        if gate.get("status") != "PASS":
            return f"features.{feature_id}.{gate.get('name')}"
    return f"features.{feature_id}.{final_gate}"


def _first_unmet_agent_foundation_system_leaf(
    document: dict[str, Any],
    group_name: str,
    names: tuple[str, ...],
) -> str:
    leaves = _agent_foundation_group_leaves(document, group_name)
    by_name = {
        leaf.get("name"): leaf
        for leaf in leaves
        if isinstance(leaf, dict) and isinstance(leaf.get("name"), str)
    }
    for name in names:
        leaf = by_name.get(name)
        if not isinstance(leaf, dict):
            raise ValueError(f"malformed {group_name} leaf {name}")
        status = leaf.get("status")
        if status in {"PASS", "N/A"}:
            continue
        if status in {"FAIL", "UNKNOWN", "PENDING"}:
            return f"system_gates.{group_name}.{name}"
        raise ValueError(f"unsupported {group_name} leaf status for {name}: {status!r}")
    raise ValueError(f"no unmet {group_name} leaf")


def _resolve_agent_foundation_earliest_blocker(document: dict[str, Any]) -> str | None:
    phase = _derive_agent_foundation_project_phase(document)
    release = document.get("release", {})
    if phase == "P0_SCOPE":
        if not isinstance(release, dict) or release.get("status") != "FROZEN":
            return "release.status"
        return "required_feature_ids_resolution"

    required = _normalize_agent_foundation_required_feature_ids(document)
    if required is None:
        raise ValueError("resolved project phase requires resolved required_feature_ids")

    if phase == "P1_FOUNDATION":
        return _first_unmet_agent_foundation_system_leaf(
            document,
            "foundation",
            AGENT_FOUNDATION_SYSTEM_GATE_MAP["foundation"],
        )
    if phase == "P2_FEATURE_BUILD":
        for feature_id in required:
            if _agent_foundation_feature_below(document, feature_id, "INTEGRATED"):
                return _first_unmet_agent_foundation_feature_gate(document, feature_id, "integration")
    if phase == "P3_INTEGRATION":
        return _first_unmet_agent_foundation_system_leaf(
            document,
            "integration",
            AGENT_FOUNDATION_SYSTEM_GATE_MAP["integration"],
        )
    if phase == "P4_VERIFICATION":
        for feature_id in required:
            if _agent_foundation_feature_below(document, feature_id, "VERIFIED"):
                return _first_unmet_agent_foundation_feature_gate(document, feature_id, "verification")
        return _first_unmet_agent_foundation_system_leaf(
            document,
            "verification",
            AGENT_FOUNDATION_SYSTEM_GATE_MAP["verification"],
        )
    if phase == "P5_HARDENING":
        for feature_id in required:
            if _agent_foundation_feature_below(document, feature_id, "RELEASE_READY"):
                return _first_unmet_agent_foundation_feature_gate(document, feature_id, "release_readiness")
        return _first_unmet_agent_foundation_system_leaf(
            document,
            "hardening",
            AGENT_FOUNDATION_SYSTEM_GATE_MAP["hardening"],
        )
    if phase == "P6_RELEASE_READY":
        for feature_id in required:
            if _agent_foundation_feature_below(document, feature_id, "LIVE"):
                return _first_unmet_agent_foundation_feature_gate(document, feature_id, "production_acceptance")
        production_blocker = _first_unmet_agent_foundation_system_leaf(
            document,
            "production",
            AGENT_FOUNDATION_PRODUCTION_ACCEPTANCE_LEAVES,
        ) if _derive_agent_foundation_group_status(document, "production") != "PASS" else None
        if production_blocker is not None:
            return production_blocker
        return "system_gates.production.operational_readiness"
    return None


def _validate_product_evidence_ref(
    ref: Any,
    *,
    evidence_root: Path,
    label: str,
) -> bool:
    if type(ref) is not str or not ref.strip() or len(ref) > 256:
        error(f"{label}: evidence reference must be a non-empty bounded string")
        return False
    if ref != ref.strip() or "\\" in ref or ref.startswith(("/", "./")):
        error(f"{label}: evidence reference must be canonical repository-relative POSIX path")
        return False
    relative = Path(ref)
    if any(part in {"", ".", ".."} for part in relative.parts):
        error(f"{label}: evidence reference contains non-canonical path traversal")
        return False
    if ref == "product-state.json":
        error(f"{label}: product-state.json cannot self-attest feature state")
        return False
    if ref.startswith(".agent/tasks/TASK-0020/"):
        error(f"{label}: TASK-0020 task/report/review artifacts cannot evidence their own implementation candidate")
        return False
    resolved = (evidence_root / relative).resolve()
    try:
        resolved.relative_to(evidence_root.resolve())
    except ValueError:
        error(f"{label}: evidence reference escapes repository")
        return False
    if not resolved.is_file():
        error(f"{label}: evidence reference is missing or inaccessible: {ref}")
        return False
    return True


def _iter_protocol_scalars(value: Any):
    if isinstance(value, dict):
        for child in value.values():
            yield from _iter_protocol_scalars(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_protocol_scalars(child)
    else:
        yield value


def _collect_named_mapping_blocks(value: Any, names: frozenset[str]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in names and isinstance(child, dict):
                blocks.append(child)
            blocks.extend(_collect_named_mapping_blocks(child, names))
    elif isinstance(value, list):
        for child in value:
            blocks.extend(_collect_named_mapping_blocks(child, names))
    return blocks


PROFILE_BOOTSTRAP_RESULT_BLOCKS = frozenset({
    "bootstrap_validator",
    "bootstrap_remote_validator",
    "bootstrap_local",
    "bootstrap_remote",
    "bootstrap_unit_tests",
})


def _profile_acceptance_evidence_signals(document: dict[str, Any]) -> list[str]:
    signals: list[str] = []
    items = document.get("acceptance_evidence")
    if not isinstance(items, list):
        return signals
    for item in items:
        if not isinstance(item, dict) or item.get("status") != "PASS":
            continue
        evidence = item.get("evidence")
        if not isinstance(evidence, str):
            continue
        signals.extend(
            match.upper()
            for match in re.findall(
                r"\bbootstrap\s+(?:local\s+and\s+remote|local|remote)\s+validation\s+returns?\s+"
                r"OPM_BOOTSTRAP\s*=\s*([A-Z_]+)\b",
                evidence,
                flags=re.IGNORECASE,
            )
        )
    return signals


def _profile_verification_is_positive(document: dict[str, Any]) -> bool:
    signals: list[str] = []
    blocks = _collect_named_mapping_blocks(document, PROFILE_BOOTSTRAP_RESULT_BLOCKS)
    for block in blocks:
        signal = block.get("signal")
        result_values = [
            block.get(key)
            for key in ("result", "required_run_result")
            if key in block
        ]
        if any(result != "PASS" for result in result_values):
            return False
        if isinstance(signal, str):
            scoped_signals = [
                match.upper()
                for match in re.findall(
                    r"^\s*OPM_BOOTSTRAP\s*=\s*([A-Z_]+)\s*$",
                    signal,
                    flags=re.IGNORECASE,
                )
            ]
            if scoped_signals and not result_values:
                return False
            signals.extend(scoped_signals)

    signals.extend(_profile_acceptance_evidence_signals(document))
    return bool(signals) and all(signal == "TRUE" for signal in signals)


def _named_result_blocks_are_positive(
    document: dict[str, Any],
    names: frozenset[str],
) -> bool:
    blocks = _collect_named_mapping_blocks(document, names)
    if not blocks:
        return False
    results = [block.get("result") for block in blocks]
    return all(result == "PASS" for result in results)


def _owner_verification_is_positive(document: dict[str, Any], owner: str) -> bool:
    if owner == "profile/":
        return _profile_verification_is_positive(document)
    if owner == "documents/":
        return _named_result_blocks_are_positive(
            document,
            frozenset({"documents_tests"}),
        )
    if owner == "standards/":
        return _named_result_blocks_are_positive(
            document,
            frozenset({"standards_verifier"}),
        )
    if owner == "skills/":
        return _named_result_blocks_are_positive(
            document,
            frozenset({"skills_validator", "skills_validator_tests", "skills_tests"}),
        )
    return False


def _verification_report_covers_owner(
    report_ref: str,
    *,
    owner: str,
    evidence_root: Path,
) -> bool:
    if not re.fullmatch(r"\.agent/tasks/TASK-\d{4}/report(?:-r\d+)?\.yaml", report_ref):
        return False
    path = evidence_root / report_ref
    if not path.is_file():
        return False

    document = load_protocol_path(path, report_ref)
    if document is None:
        return False
    execution = document.get("execution")
    if not isinstance(execution, dict):
        return False
    final_execution_head = execution.get("final_execution_head")
    if not isinstance(final_execution_head, str) or not SHA40_RE.fullmatch(final_execution_head):
        return False
    if not _owner_verification_is_positive(document, owner):
        return False

    try:
        result = subprocess.run(
            ["git", "-C", str(evidence_root), "diff", "--quiet", final_execution_head, "--", owner],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return False
    return result.returncode == 0


def _validate_agent_foundation_lifecycle(
    feature: dict[str, Any],
    *,
    evidence_root: Path,
    label: str,
    release_unresolved: bool,
) -> None:
    owner = feature.get("owner")
    lifecycle = feature.get("lifecycle")
    if not _require_exact_object_keys(label, lifecycle, {"gates", "derived_state", "regression"}):
        return

    gates = lifecycle.get("gates")
    if type(gates) is not list:
        error(f"{label}.gates: expected array")
        return
    if len(gates) != len(AGENT_FOUNDATION_LIFECYCLE_GATES):
        error(f"{label}.gates: expected exactly seven ordered lifecycle gates")
        return

    saw_blocker = False
    verification_reports: list[str] = []
    for index, expected_name in enumerate(AGENT_FOUNDATION_LIFECYCLE_GATES):
        gate = gates[index]
        gate_label = f"{label}.gates[{index}]"
        if not _require_exact_object_keys(gate_label, gate, {"name", "status", "evidence_refs", "reason"}):
            continue
        if gate.get("name") != expected_name:
            error(f"{gate_label}.name: expected {expected_name!r}")

        status = gate.get("status")
        if status not in AGENT_FOUNDATION_GATE_STATUSES:
            error(f"{gate_label}.status: unsupported gate status {status!r}")
            status = None

        refs = gate.get("evidence_refs")
        valid_refs: list[str] = []
        if type(refs) is not list:
            error(f"{gate_label}.evidence_refs: expected array")
        else:
            if len(refs) > AGENT_FOUNDATION_MAX_EVIDENCE_REFS:
                error(f"{gate_label}.evidence_refs: exceeds bounded evidence reference limit")
            if all(type(ref) is str for ref in refs) and len(refs) != len(set(refs)):
                error(f"{gate_label}.evidence_refs: duplicate evidence references")
            for ref_index, ref in enumerate(refs):
                if _validate_product_evidence_ref(
                    ref,
                    evidence_root=evidence_root,
                    label=f"{gate_label}.evidence_refs[{ref_index}]",
                ):
                    valid_refs.append(ref)

        reason = gate.get("reason")
        if status == "PASS":
            if not refs:
                error(f"{gate_label}: PASS requires inspectable persisted evidence")
            if reason is not None:
                error(f"{gate_label}.reason: PASS requires null reason")
            if saw_blocker:
                error(f"{gate_label}: later gate cannot PASS while an earlier prerequisite is not PASS")
            if expected_name not in {"scope", "release_readiness", "production_acceptance"} and isinstance(owner, str):
                if not any(ref.startswith(owner) for ref in valid_refs):
                    error(f"{gate_label}: PASS requires current evidence from owning domain {owner}")
            if expected_name == "verification" and isinstance(owner, str):
                verification_reports = [
                    ref for ref in valid_refs
                    if _verification_report_covers_owner(
                        ref,
                        owner=owner,
                        evidence_root=evidence_root,
                    )
                ]
                if not verification_reports:
                    error(
                        f"{gate_label}: verification PASS requires persisted result evidence "
                        "attributable to exact current owner bytes"
                    )
        elif status in {"FAIL", "PENDING", "N/A", "UNKNOWN"}:
            if type(reason) is not str or not reason.strip():
                error(f"{gate_label}.reason: {status} requires a non-empty reason")
            if status == "FAIL" and not refs:
                error(f"{gate_label}: FAIL requires attributable evidence")
            saw_blocker = True

        if release_unresolved and expected_name in {"release_readiness", "production_acceptance"}:
            if status == "PASS":
                error(f"{gate_label}: unresolved OPEN release forbids PASS")

    if gates and gates[0].get("status") != "PASS":
        error(f"{label}.gates[0]: frozen registered feature scope gate must PASS")

    derived = _derive_agent_foundation_feature_state(gates)
    authored = lifecycle.get("derived_state")
    if authored not in AGENT_FOUNDATION_LIFECYCLE_STATES:
        error(f"{label}.derived_state: unsupported lifecycle state {authored!r}")
    if derived is None:
        error(f"{label}.derived_state: scope must PASS before lifecycle state is derivable")
    elif authored != derived:
        error(f"{label}.derived_state: expected recomputed state {derived}, got {authored!r}")
    if release_unresolved and authored in {"RELEASE_READY", "LIVE"}:
        error(f"{label}.derived_state: unresolved OPEN release caps state at VERIFIED")

    regression = lifecycle.get("regression")
    if regression is not None:
        regression_label = f"{label}.regression"
        if _require_exact_object_keys(
            regression_label,
            regression,
            {"from_state", "to_state", "reason", "evidence_refs"},
        ):
            from_state = regression.get("from_state")
            to_state = regression.get("to_state")
            if from_state not in AGENT_FOUNDATION_LIFECYCLE_STATES:
                error(f"{regression_label}.from_state: unsupported lifecycle state")
            if to_state not in AGENT_FOUNDATION_LIFECYCLE_STATES:
                error(f"{regression_label}.to_state: unsupported lifecycle state")
            if (
                from_state in AGENT_FOUNDATION_LIFECYCLE_STATES
                and to_state in AGENT_FOUNDATION_LIFECYCLE_STATES
                and AGENT_FOUNDATION_LIFECYCLE_STATES.index(from_state)
                <= AGENT_FOUNDATION_LIFECYCLE_STATES.index(to_state)
            ):
                error(f"{regression_label}: regression must describe a strict backward transition")
            if to_state != authored:
                error(f"{regression_label}.to_state: must equal current derived_state")
            reason = regression.get("reason")
            if type(reason) is not str or not reason.strip():
                error(f"{regression_label}.reason: regression requires non-empty reason")
            refs = regression.get("evidence_refs")
            if type(refs) is not list or not refs:
                error(f"{regression_label}.evidence_refs: regression requires evidence")
            elif len(refs) > AGENT_FOUNDATION_MAX_EVIDENCE_REFS:
                error(f"{regression_label}.evidence_refs: exceeds bounded evidence reference limit")
            else:
                for ref_index, ref in enumerate(refs):
                    _validate_product_evidence_ref(
                        ref,
                        evidence_root=evidence_root,
                        label=f"{regression_label}.evidence_refs[{ref_index}]",
                    )


def _validate_system_evidence_ref(
    ref: Any,
    *,
    evidence_root: Path,
    label: str,
) -> bool:
    if type(ref) is not str or not ref.strip() or len(ref) > 256:
        error(f"{label}: evidence reference must be a non-empty bounded string")
        return False
    if ref != ref.strip() or "\\" in ref or ref.startswith(("/", "./")):
        error(f"{label}: evidence reference must be canonical repository-relative POSIX path")
        return False
    relative = Path(ref)
    if any(part in {"", ".", ".."} for part in relative.parts):
        error(f"{label}: evidence reference contains non-canonical path traversal")
        return False
    if ref == "product-state.json":
        error(f"{label}: product-state.json cannot self-attest system-gate state")
        return False
    if ref.startswith(".agent/tasks/TASK-0021/"):
        error(f"{label}: TASK-0021 task/report/review artifacts cannot evidence their own implementation candidate")
        return False
    resolved = (evidence_root / relative).resolve()
    try:
        resolved.relative_to(evidence_root.resolve())
    except ValueError:
        error(f"{label}: evidence reference escapes repository")
        return False
    if not resolved.is_file():
        error(f"{label}: evidence reference is missing or inaccessible: {ref}")
        return False
    return True


def _validate_agent_foundation_system_leaf(
    leaf: Any,
    *,
    expected_name: str,
    evidence_root: Path,
    label: str,
) -> None:
    if not _require_exact_object_keys(
        label,
        leaf,
        {"name", "status", "evidence_refs", "reason"},
    ):
        return
    if leaf.get("name") != expected_name:
        error(f"{label}.name: expected {expected_name!r}")
    status = leaf.get("status")
    if status not in AGENT_FOUNDATION_GATE_STATUSES:
        error(f"{label}.status: unsupported gate status {status!r}")
        status = None

    refs = leaf.get("evidence_refs")
    if type(refs) is not list:
        error(f"{label}.evidence_refs: expected array")
        refs = []
    else:
        if len(refs) > AGENT_FOUNDATION_MAX_EVIDENCE_REFS:
            error(f"{label}.evidence_refs: exceeds bounded evidence reference limit")
        if all(type(ref) is str for ref in refs) and len(refs) != len(set(refs)):
            error(f"{label}.evidence_refs: duplicate evidence references")
        for ref_index, ref in enumerate(refs):
            _validate_system_evidence_ref(
                ref,
                evidence_root=evidence_root,
                label=f"{label}.evidence_refs[{ref_index}]",
            )

    reason = leaf.get("reason")
    if status == "PASS":
        if not refs:
            error(f"{label}: PASS requires inspectable persisted evidence")
        if reason is not None:
            error(f"{label}.reason: PASS requires null reason")
    elif status == "FAIL":
        if not refs:
            error(f"{label}: FAIL requires attributable evidence")
        if type(reason) is not str or not reason.strip():
            error(f"{label}.reason: FAIL requires a non-empty reason")
    elif status in {"PENDING", "N/A", "UNKNOWN"}:
        if type(reason) is not str or not reason.strip():
            error(f"{label}.reason: {status} requires a non-empty reason")


def _validate_agent_foundation_system_gates(
    document: dict[str, Any],
    *,
    evidence_root: Path,
    label: str,
) -> None:
    system_gates = document.get("system_gates")
    expected_groups = {name for name, _ in AGENT_FOUNDATION_SYSTEM_GATE_LEAVES}
    if not _require_exact_object_keys(f"{label}.system_gates", system_gates, expected_groups):
        if not isinstance(system_gates, dict):
            return

    for group_name, expected_names in AGENT_FOUNDATION_SYSTEM_GATE_LEAVES:
        group = system_gates.get(group_name) if isinstance(system_gates, dict) else None
        aggregate_key = "acceptance_status" if group_name == "production" else "status"
        if not _require_exact_object_keys(
            f"{label}.system_gates.{group_name}",
            group,
            {"leaves", aggregate_key},
        ):
            continue
        leaves = group.get("leaves")
        if type(leaves) is not list:
            error(f"{label}.system_gates.{group_name}.leaves: expected array")
            continue
        if len(leaves) != len(expected_names):
            error(
                f"{label}.system_gates.{group_name}.leaves: "
                f"expected exactly {len(expected_names)} canonical leaves"
            )
        for index, expected_name in enumerate(expected_names):
            if index >= len(leaves):
                break
            _validate_agent_foundation_system_leaf(
                leaves[index],
                expected_name=expected_name,
                evidence_root=evidence_root,
                label=f"{label}.system_gates.{group_name}.leaves[{index}]",
            )

        aggregate_leaves = leaves
        aggregate_names = expected_names
        if group_name == "production":
            aggregate_names = AGENT_FOUNDATION_PRODUCTION_ACCEPTANCE_LEAVES
            aggregate_leaves = [
                leaf for leaf in leaves
                if isinstance(leaf, dict) and leaf.get("name") in aggregate_names
            ]

        aggregate_statuses = [
            leaf.get("status")
            for leaf in aggregate_leaves
            if isinstance(leaf, dict)
        ]
        if (
            len(aggregate_statuses) == len(aggregate_names)
            and aggregate_statuses
            and all(status == "N/A" for status in aggregate_statuses)
        ):
            error(
                f"{label}.system_gates.{group_name}: "
                "all-N/A aggregate is invalid; at least one applicable leaf is required"
            )

        authored = group.get(aggregate_key)
        if authored not in AGENT_FOUNDATION_GATE_STATUSES:
            error(
                f"{label}.system_gates.{group_name}.{aggregate_key}: "
                f"unsupported aggregate status {authored!r}"
            )
        try:
            derived = _derive_agent_foundation_gate_aggregate(
                aggregate_leaves,
                aggregate_names,
            )
        except ValueError as exc:
            error(f"{label}.system_gates.{group_name}: {exc}")
            continue
        if authored != derived:
            error(
                f"{label}.system_gates.{group_name}.{aggregate_key}: "
                f"expected recomputed status {derived}, got {authored!r}"
            )


def validate_agent_foundation_product_state(
    path: Path,
    *,
    evidence_root: Path | None = None,
) -> None:
    """Validate agent-foundation's target-specific T2+T3+T4 product-state object."""
    label = str(path)
    if evidence_root is None:
        evidence_root = path.parent
    if not path.is_file():
        error(f"{label}: missing canonical target product-state.json")
        return
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        error(f"{label}: invalid JSON: {exc}")
        return

    if not _require_exact_object_keys(
        label,
        document,
        {"schema_version", "target", "product_scope", "release", "system_gates", "derived_project"},
    ):
        if not isinstance(document, dict):
            return

    if document.get("schema_version") != 3 or type(document.get("schema_version")) is not int:
        error(f"{label}.schema_version: expected integer 3")

    target = document.get("target")
    if _require_exact_object_keys(f"{label}.target", target, {"repository"}):
        if target.get("repository") != "phatnguyen03022001/agent-foundation":
            error(f"{label}.target.repository: unexpected target repository")

    release = document.get("release")
    release_unresolved = True
    if _require_exact_object_keys(
        f"{label}.release",
        release,
        {
            "status",
            "id",
            "id_resolution",
            "required_feature_ids",
            "required_feature_ids_resolution",
        },
    ):
        if release.get("status") != "OPEN":
            error(f"{label}.release.status: expected OPEN")
        if release.get("id") is not None:
            error(f"{label}.release.id: unresolved release identity must be null")
        if release.get("id_resolution") != "UNKNOWN":
            error(f"{label}.release.id_resolution: expected UNKNOWN")
        if release.get("required_feature_ids") is not None:
            error(
                f"{label}.release.required_feature_ids: "
                "unresolved required feature set must be null, never an empty array"
            )
        if release.get("required_feature_ids_resolution") != "UNKNOWN":
            error(f"{label}.release.required_feature_ids_resolution: expected UNKNOWN")
        release_unresolved = (
            release.get("status") == "OPEN"
            or release.get("id") is None
            or release.get("id_resolution") == "UNKNOWN"
            or release.get("required_feature_ids") is None
            or release.get("required_feature_ids_resolution") == "UNKNOWN"
        )

    product_scope = document.get("product_scope")
    if _require_exact_object_keys(
        f"{label}.product_scope",
        product_scope,
        {"revision", "scope_status", "features"},
    ):
        if product_scope.get("revision") != 1 or type(product_scope.get("revision")) is not int:
            error(f"{label}.product_scope.revision: expected frozen revision 1")
        if product_scope.get("scope_status") != "FROZEN":
            error(f"{label}.product_scope.scope_status: expected FROZEN")

        features = product_scope.get("features")
        if _require_exact_object_keys(
            f"{label}.product_scope.features",
            features,
            {"total", "registered"},
        ):
            if features.get("total") != 4 or type(features.get("total")) is not int:
                error(f"{label}.product_scope.features.total: expected integer 4")
            registered = features.get("registered")
            if not isinstance(registered, list):
                error(f"{label}.product_scope.features.registered: expected array")
            else:
                expected_identity = [
                    {"id": feature_id, "semantic_name": semantic_name, "owner": owner}
                    for feature_id, semantic_name, owner in AGENT_FOUNDATION_PRODUCT_FEATURES
                ]
                actual_identity: list[dict[str, Any]] = []
                ids: list[str] = []
                names: list[str] = []
                for index, feature in enumerate(registered):
                    feature_label = f"{label}.product_scope.features.registered[{index}]"
                    if not _require_exact_object_keys(
                        feature_label,
                        feature,
                        {"id", "semantic_name", "owner", "lifecycle"},
                    ):
                        continue
                    identity = {
                        "id": feature.get("id"),
                        "semantic_name": feature.get("semantic_name"),
                        "owner": feature.get("owner"),
                    }
                    actual_identity.append(identity)
                    if isinstance(identity["id"], str):
                        ids.append(identity["id"])
                    if isinstance(identity["semantic_name"], str):
                        names.append(identity["semantic_name"])
                    _validate_agent_foundation_lifecycle(
                        feature,
                        evidence_root=evidence_root,
                        label=f"{feature_label}.lifecycle",
                        release_unresolved=release_unresolved,
                    )
                if len(ids) != len(set(ids)):
                    error(f"{label}.product_scope.features.registered: duplicate feature IDs")
                if len(names) != len(set(names)):
                    error(f"{label}.product_scope.features.registered: duplicate semantic names")
                if len(registered) != features.get("total"):
                    error(f"{label}.product_scope.features: total does not match registered count")
                if actual_identity != expected_identity:
                    error(
                        f"{label}.product_scope.features.registered: "
                        "revision 1 must exactly preserve F001-F004 semantic identities and owners"
                    )


    _validate_agent_foundation_system_gates(
        document,
        evidence_root=evidence_root,
        label=label,
    )

    derived_project = document.get("derived_project")
    if _require_exact_object_keys(
        f"{label}.derived_project",
        derived_project,
        {"phase"},
    ):
        authored_phase = derived_project.get("phase")
        if authored_phase not in AGENT_FOUNDATION_PROJECT_PHASES:
            error(f"{label}.derived_project.phase: unsupported project phase {authored_phase!r}")
        try:
            derived_phase = _derive_agent_foundation_project_phase(document)
        except ValueError as exc:
            error(f"{label}.derived_project.phase: {exc}")
        else:
            if authored_phase != derived_phase:
                error(
                    f"{label}.derived_project.phase: "
                    f"expected recomputed phase {derived_phase}, got {authored_phase!r}"
                )


def validate_agent_foundation_product_state_transition(
    previous: dict[str, Any],
    current: dict[str, Any],
    *,
    evidence_root: Path,
    label: str = "product-state transition",
) -> None:
    current_features = (
        current.get("product_scope", {})
        .get("features", {})
        .get("registered", [])
    )
    if type(current_features) is not list:
        error(f"{label}: current feature registry is malformed")
        return

    if previous.get("schema_version") == 1:
        for feature in current_features:
            lifecycle = feature.get("lifecycle", {}) if isinstance(feature, dict) else {}
            if lifecycle.get("regression") is not None:
                error(f"{label}: initial schema-1 to schema-2 adoption requires regression null")
        return

    if previous.get("schema_version") not in {2, 3}:
        error(f"{label}: previous state must be valid schema 1, schema 2, or schema 3")
        return

    previous_features = (
        previous.get("product_scope", {})
        .get("features", {})
        .get("registered", [])
    )
    if type(previous_features) is not list:
        error(f"{label}: previous feature registry is malformed")
        return
    previous_by_id = {
        feature.get("id"): feature
        for feature in previous_features
        if isinstance(feature, dict) and isinstance(feature.get("id"), str)
    }

    for feature in current_features:
        if not isinstance(feature, dict):
            continue
        feature_id = feature.get("id")
        prior = previous_by_id.get(feature_id)
        if prior is None:
            error(f"{label}: missing prior feature identity {feature_id!r}")
            continue
        prior_state = prior.get("lifecycle", {}).get("derived_state")
        current_lifecycle = feature.get("lifecycle", {})
        current_state = current_lifecycle.get("derived_state")
        if prior_state not in AGENT_FOUNDATION_LIFECYCLE_STATES or current_state not in AGENT_FOUNDATION_LIFECYCLE_STATES:
            error(f"{label}: invalid lifecycle state for {feature_id}")
            continue
        reg = current_lifecycle.get("regression")
        moved_backward = (
            AGENT_FOUNDATION_LIFECYCLE_STATES.index(current_state)
            < AGENT_FOUNDATION_LIFECYCLE_STATES.index(prior_state)
        )
        if moved_backward:
            if not isinstance(reg, dict):
                error(f"{label}: {feature_id} downgrade requires explicit regression record")
                continue
            if reg.get("from_state") != prior_state or reg.get("to_state") != current_state:
                error(f"{label}: {feature_id} regression must exactly match prior/current derived states")
            reason = reg.get("reason")
            if type(reason) is not str or not reason.strip():
                error(f"{label}: {feature_id} regression requires non-empty reason")
            refs = reg.get("evidence_refs")
            if type(refs) is not list or not refs:
                error(f"{label}: {feature_id} regression requires inspectable evidence")
            else:
                for ref_index, ref in enumerate(refs):
                    _validate_product_evidence_ref(
                        ref,
                        evidence_root=evidence_root,
                        label=f"{label}.{feature_id}.regression.evidence_refs[{ref_index}]",
                    )
        elif reg is not None:
            error(f"{label}: {feature_id} non-regression transition must keep regression null")


ARTIFACT_VALIDATORS = {
    "task": validate_task_document,
    "report": validate_report_document,
    "review": validate_review_document,
}


def print_errors() -> int:
    if errors:
        print("\nErrors:", file=sys.stderr)
        for message in errors:
            print(f"  ERROR: {message}", file=sys.stderr)
        return 1
    return 0


def validate_explicit_artifact(kind: str, raw_path: str) -> int:
    errors.clear()
    warnings.clear()
    validator = ARTIFACT_VALIDATORS.get(kind)
    if validator is None:
        error(f"unsupported artifact type {kind!r}; expected task, report, or review")
        return print_errors()

    path = Path(raw_path)
    label = str(path)
    try:
        document = load_protocol_path(path, label, unsupported_serialization_is_inconclusive=True)
    except UnsupportedProtocolSerializationError as exc:
        print(f"UNSUPPORTED_SERIALIZATION: {exc}; protocol validity not mechanically determined by this constrained validator", file=sys.stderr)
        return 3
    if document is not None:
        validator(label, document)

    if print_errors():
        return 1
    print(f"OK: validated {kind} artifact {label}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = [] if argv is None else argv
    if argv:
        if len(argv) == 3 and argv[0] == "--artifact":
            return validate_explicit_artifact(argv[1], argv[2])
        print(
            "usage: validate_skill_library.py [--artifact {task,report,review} PATH]",
            file=sys.stderr,
        )
        return 2

    errors.clear()
    warnings.clear()

    expected_skills = validate_rationalization()

    discovered = sorted(ROOT.rglob("SKILL.md"))
    allowed = {ROOT / name / "SKILL.md" for name in expected_skills}
    unexpected = [path for path in discovered if path not in allowed]
    missing = sorted(path for path in allowed if not path.is_file())
    if unexpected or missing or set(discovered) != allowed:
        error(
            "curated skill locations mismatch; "
            f"missing={[str(p.relative_to(ROOT)) for p in missing]} "
            f"unexpected={[str(p.relative_to(ROOT)) for p in unexpected]}"
        )

    seen_names: dict[str, Path] = {}
    print("Skill word counts:")
    for path in discovered:
        metadata, text = parse_frontmatter(path)
        rel = path.relative_to(ROOT)
        if path not in allowed:
            continue
        name = metadata.get("name", "")
        description = metadata.get("description", "")
        folder = path.parent.name

        if not name:
            error(f"{rel}: missing frontmatter name")
        else:
            if len(name) > 64:
                error(f"{rel}: skill name exceeds 64 characters")
            if not NAME_RE.fullmatch(name):
                error(f"{rel}: invalid skill name '{name}'")
            if name != folder:
                error(f"{rel}: skill name '{name}' must match folder '{folder}'")
            if name in seen_names:
                error(f"duplicate skill name '{name}': {seen_names[name]} and {rel}")
            else:
                seen_names[name] = rel

        if not description:
            error(f"{rel}: missing frontmatter description")
        elif not description.startswith("Use when"):
            error(f"{rel}: description must begin with 'Use when'")
        if len(description) > 1024:
            error(f"{rel}: description exceeds 1024 characters")

        body = text.split("---", 2)[-1] if text.startswith("---") else text
        word_count = len(re.findall(r"\b[\w'-]+\b", body, flags=re.UNICODE))
        line_count = len(text.splitlines())
        print(f"  {folder}: {word_count} words, {line_count} lines")
        if word_count > 800:
            warning(f"{rel}: {word_count} words; consider moving heavy detail to references/")
        if line_count > 500:
            warning(f"{rel}: {line_count} lines; Agent Skills recommends keeping SKILL.md under 500 lines")
        validate_links(path, text)

    if set(seen_names) != expected_skills:
        error("frontmatter names do not match rationalized internal skill set")

    validate_readme_catalog(expected_skills)
    validate_foundation_architecture_contract()
    validate_generated_program_template()
    validate_case_navigation(expected_skills)
    validate_task_template()
    validate_handoff_template()
    validate_report_template()
    validate_review_template()
    validate_continuation_template()
    validate_template_consistency()
    validate_protocol_docs()

    repository_root = ROOT.parent
    if ROOT.name == "skills" and all(
        (repository_root / name).is_dir() for name in ("profile", "documents", "standards")
    ):
        validate_agent_foundation_product_state(repository_root / "product-state.json")

    if warnings:
        print("\nWarnings:")
        for message in warnings:
            print(f"  WARN: {message}")
    if print_errors():
        return 1

    print(f"\nOK: validated rationalized {len(expected_skills)}-skill internal taxonomy and protocol v{SUPPORTED_PROTOCOL_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
