#!/usr/bin/env python3
"""Validate and store bounded non-authoritative continuity findings."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from validate_skill_library import (
    ProtocolYamlError,
    UnsupportedProtocolSerializationError,
    parse_mapping,
    preprocess_yaml,
)

FOUNDATION_REPOSITORY = "phatnguyen03022001/agent-foundation"
CONTINUITY_ROOT = Path("profile/.agent/continuity")
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
FINDING_KEYS = {
    "schema_version",
    "artifact",
    "authority",
    "status",
    "source",
    "owner_repository",
    "summary",
    "observation",
    "inference",
    "evidence",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        lines = preprocess_yaml(path)
        document, index = parse_mapping(lines, 0, 0, path)
        if index != len(lines):
            raise ValueError(f"{path}: unexpected trailing YAML")
    except (ProtocolYamlError, UnsupportedProtocolSerializationError, OSError) as exc:
        raise ValueError(str(exc)) from exc
    if not isinstance(document, dict):
        raise ValueError(f"{path}: top-level document must be a mapping")
    return document


def _exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise ValueError(
            f"{label} keys mismatch: missing={sorted(expected - actual)} extra={sorted(actual - expected)}"
        )


def _bounded_string(value: Any, label: str, *, maximum: int, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    if not allow_empty and not value.strip():
        raise ValueError(f"{label} must be non-empty")
    if len(value) > maximum or "\n" in value or "\r" in value:
        raise ValueError(f"{label} must be single-line and <= {maximum} characters")
    return value


def normalize_repository(value: Any, label: str = "repository") -> str:
    text = _bounded_string(value, label, maximum=200).lower()
    if not REPOSITORY_RE.fullmatch(text) or ".." in text:
        raise ValueError(f"{label} must be owner/repo")
    return text


def owner_store_name(owner_repository: str) -> str:
    owner = normalize_repository(owner_repository, "owner_repository")
    digest = hashlib.sha256(owner.encode("utf-8")).hexdigest()
    safe = owner.replace("/", "--")
    return f"{safe}--{digest}.json"


def validate_finding(document: dict[str, Any]) -> dict[str, Any]:
    _exact_keys(document, FINDING_KEYS, "continuity finding")
    if document["schema_version"] != 1 or document["artifact"] != "CONTINUITY_FINDING":
        raise ValueError("continuity finding identity is invalid")
    if document["authority"] != "NONE":
        raise ValueError("continuity finding authority must be NONE")
    if document["status"] != "UNVALIDATED_FOR_OWNER":
        raise ValueError("continuity finding status must be UNVALIDATED_FOR_OWNER")

    source = document["source"]
    if not isinstance(source, dict):
        raise ValueError("source must be a mapping")
    _exact_keys(source, {"repository", "task_locator", "report_locator"}, "source")
    normalize_repository(source["repository"], "source.repository")
    for field in ("task_locator", "report_locator"):
        value = _bounded_string(source[field], f"source.{field}", maximum=300, allow_empty=True)
        if value:
            path = Path(value)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"source.{field} must be a bounded repository-relative locator")

    normalize_repository(document["owner_repository"], "owner_repository")
    _bounded_string(document["summary"], "summary", maximum=500)
    _bounded_string(document["observation"], "observation", maximum=1200)
    _bounded_string(document["inference"], "inference", maximum=1200, allow_empty=True)

    evidence = document["evidence"]
    if not isinstance(evidence, list) or not evidence or len(evidence) > 8:
        raise ValueError("evidence must contain 1..8 bounded locators")
    for index, locator in enumerate(evidence):
        _bounded_string(locator, f"evidence[{index}]", maximum=512)
    return document


def finding_key(document: dict[str, Any]) -> str:
    validate_finding(document)
    canonical = {
        "source": document["source"],
        "owner_repository": normalize_repository(document["owner_repository"]),
        "summary": document["summary"],
        "observation": document["observation"],
        "inference": document["inference"],
        "evidence": document["evidence"],
    }
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_task(root: Path, task_relative: str) -> dict[str, Any]:
    task_path = Path(task_relative)
    if task_path.is_absolute() or ".." in task_path.parts:
        raise ValueError("authority task path must stay inside the Foundation repository")
    if len(task_path.parts) < 4 or task_path.parts[:2] != (".agent", "tasks"):
        raise ValueError("authority task must be a canonical .agent/tasks task")
    resolved = (root / task_path).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("authority task path escapes the Foundation repository") from exc
    return _load_yaml(resolved)


def validate_record_authority(root: Path, task_relative: str) -> dict[str, Any]:
    task = _load_task(root, task_relative)
    if task.get("state") != "APPROVED" or task.get("execution_ready") is not True:
        raise ValueError("continuity recording requires an approved execution-ready task")
    target = task.get("target")
    if not isinstance(target, dict) or normalize_repository(target.get("repository"), "task target") != FOUNDATION_REPOSITORY:
        raise ValueError("continuity recording authority must target agent-foundation")
    scope = task.get("scope")
    required = scope.get("required_changes") if isinstance(scope, dict) else None
    if not isinstance(required, list) or not any(
        isinstance(item, str) and "continuity" in item.lower() and ("record" in item.lower() or "store" in item.lower())
        for item in required
    ):
        raise ValueError("task does not explicitly authorize continuity recording/storage")
    return task


def _continuity_root(root: Path) -> Path:
    store_root = (root / CONTINUITY_ROOT).resolve()
    try:
        store_root.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("continuity root escapes Foundation repository") from exc
    if not store_root.is_dir():
        raise ValueError("canonical continuity root is missing")
    return store_root


def _entry(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "finding_key": finding_key(document),
        "authority": "NONE",
        "status": "UNVALIDATED_FOR_OWNER",
        "source": document["source"],
        "summary": document["summary"],
        "observation": document["observation"],
        "inference": document["inference"],
        "evidence": document["evidence"],
    }


def record_finding(root: Path, document: dict[str, Any], authority_task: str) -> tuple[Path, str, bool]:
    validate_finding(document)
    validate_record_authority(root, authority_task)
    store_root = _continuity_root(root)
    owner = normalize_repository(document["owner_repository"], "owner_repository")
    path = store_root / owner_store_name(owner)
    resolved = path.resolve()
    try:
        resolved.relative_to(store_root)
    except ValueError as exc:
        raise ValueError("owner-keyed continuity path escapes canonical root") from exc

    if path.exists():
        store = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(store, dict):
            raise ValueError("owner continuity file must contain a JSON object")
    else:
        store = {
            "schema_version": 1,
            "owner_repository": owner,
            "authority": "NONE",
            "findings": [],
        }

    if (
        store.get("schema_version") != 1
        or store.get("owner_repository") != owner
        or store.get("authority") != "NONE"
        or not isinstance(store.get("findings"), list)
    ):
        raise ValueError("owner continuity file is malformed or authoritative")

    entry = _entry(document)
    existing = {item.get("finding_key") for item in store["findings"] if isinstance(item, dict)}
    created = entry["finding_key"] not in existing
    if created:
        store["findings"].append(entry)
    store["findings"] = sorted(store["findings"], key=lambda item: item["finding_key"])
    content = json.dumps(store, indent=2, sort_keys=True, ensure_ascii=True) + "\n"

    fd, temp_name = tempfile.mkstemp(prefix=".continuity-", dir=store_root, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        Path(temp_name).replace(path)
    finally:
        temp_path = Path(temp_name)
        if temp_path.exists():
            temp_path.unlink()
    return path, entry["finding_key"], created


def load_for_binding(root: Path, owner_repository: str, fresh_owner_revision: str) -> dict[str, Any]:
    owner = normalize_repository(owner_repository, "owner_repository")
    if not SHA40_RE.fullmatch(fresh_owner_revision):
        raise ValueError("fresh_owner_revision must be an exact freshly resolved 40-hex commit")
    store_root = _continuity_root(root)
    path = store_root / owner_store_name(owner)
    if not path.exists():
        findings: list[dict[str, Any]] = []
    else:
        store = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(store, dict)
            or store.get("schema_version") != 1
            or store.get("owner_repository") != owner
            or store.get("authority") != "NONE"
            or not isinstance(store.get("findings"), list)
        ):
            raise ValueError("owner continuity file is malformed or authoritative")
        findings = store["findings"]

    return {
        "owner_repository": owner,
        "fresh_owner_revision": fresh_owner_revision,
        "authority": "NONE",
        "status": "UNVALIDATED_FOR_OWNER",
        "requires_fresh_revalidation": True,
        "consequence_authorized": False,
        "findings": findings,
    }


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    sub = parser.add_subparsers(dest="command", required=True)

    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("finding", type=Path)

    record_parser = sub.add_parser("record")
    record_parser.add_argument("finding", type=Path)
    record_parser.add_argument("--authority-task", required=True)

    load_parser = sub.add_parser("load")
    load_parser.add_argument("--owner-repository", required=True)
    load_parser.add_argument("--fresh-owner-revision", required=True)

    args = parser.parse_args()
    try:
        if args.command == "validate":
            validate_finding(_load_yaml(args.finding))
            print("OK continuity authority=NONE status=UNVALIDATED_FOR_OWNER")
        elif args.command == "record":
            path, key, created = record_finding(
                args.root, _load_yaml(args.finding), args.authority_task
            )
            print(json.dumps({"path": str(path.relative_to(args.root)), "finding_key": key, "created": created}))
        else:
            print(
                json.dumps(
                    load_for_binding(args.root, args.owner_repository, args.fresh_owner_revision),
                    sort_keys=True,
                )
            )
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
