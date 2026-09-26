#!/usr/bin/env python3
"""Local-only execution-attempt continuity telemetry.

Attempt records have authority NONE. They live only in repository-local Git
metadata and never replace fresh task, remote, HEAD, index, or worktree truth.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

LEGACY_SCHEMA_VERSION = 1
SCHEMA_VERSION = 2
ARTIFACT = "EXECUTION_ATTEMPT"
AUTHORITY = "NONE"
DEFAULT_LEASE_SECONDS = 900
MIN_LEASE_SECONDS = 30
MAX_LEASE_SECONDS = 86400
MAX_UNTRACKED_COUNT = 100
MAX_LIST_RESULTS = 100

ATTEMPT_ID_RE = re.compile(r"^[0-9a-f]{32}$")
SLICE_ID_RE = ATTEMPT_ID_RE
TASK_ID_RE = re.compile(r"^TASK-[0-9]{4,}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
CHECKPOINT_KIND_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
BOUNDED_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
RFC3339_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")

LEGACY_RECORD_KEYS = {
    "schema_version",
    "artifact",
    "authority",
    "attempt_id",
    "repository",
    "task_id",
    "task_revision",
    "execution_base",
    "started_at_utc",
    "last_seen_at_utc",
    "lease_seconds",
    "state",
    "last_checkpoint",
    "terminal_result",
    "terminal_at_utc",
}
RECORD_KEYS = LEGACY_RECORD_KEYS | {
    "next_slice_ordinal",
    "current_slice",
}
SLICE_KEYS = {
    "authority",
    "execution_slice_id",
    "ordinal",
    "operation_class",
    "carrier",
    "intent",
    "reconciliation_kind",
    "postcondition_kind",
    "lifecycle_observation",
    "observed_at_utc",
    "runtime_session_observation",
    "reconciliation_result",
    "result_classification",
}
RECONCILIATION_RULES = {
    "runtime_start": "runtime_session_identity",
    "expected_state_filesystem": "expected_state",
    "git_commit_update": "git_object_identity",
    "git_publication": "remote_ref_identity",
    "report_publication": "remote_report_identity",
}
SLICE_OBSERVATION_RESULTS = {
    "ACK_OBSERVED": ("ACK_OBSERVED", "UNRESOLVED"),
    "RESULT_SUCCEEDED": ("RESULT_OBSERVED", "SUCCEEDED"),
    "RESULT_NO_EFFECT": ("RESULT_OBSERVED", "NO_EFFECT"),
    "OUTCOME_UNKNOWN": ("OUTCOME_UNKNOWN", "OUTCOME_UNKNOWN"),
}
RECONCILIATION_RESULTS = frozenset({
    "EFFECT_PRESENT",
    "EFFECT_ABSENT_PRECONDITIONS_HOLD",
    "REPLAY_SAFE_CONTRACT",
    "UNRESOLVED",
})
RESOLVED_SLICE_RESULTS = frozenset({
    "SUCCEEDED",
    "NO_EFFECT",
    "EFFECT_PRESENT",
    "RETRY_ALLOWED",
})
CHECKPOINT_KEYS = {
    "kind",
    "observed_at_utc",
    "local_head",
    "upstream_ref",
    "upstream_head",
    "tracked_dirty",
    "untracked_count",
    "untracked_count_capped",
}
FORBIDDEN_FIELD_TOKENS = {
    "secret",
    "secrets",
    "token",
    "tokens",
    "credential",
    "credentials",
    "argv",
    "raw_argv",
    "environment",
    "env",
    "prompt",
    "prompts",
    "conversation",
    "transcript",
    "transcripts",
    "log",
    "logs",
    "raw_log",
    "raw_logs",
    "tool_log",
    "tool_logs",
    "diff",
    "full_diff",
    "file_body",
    "file_bodies",
    "file_content",
    "file_contents",
    "file_inventory",
    "inventory",
    "report_body",
    "death_at",
    "death_at_utc",
}


def _run_git(root: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError(f"git {' '.join(args)} failed: {detail or result.returncode}")
    return result.stdout.strip() if result.returncode == 0 else ""


def _repository_root(root: Path | str) -> Path:
    candidate = Path(root).expanduser().resolve()
    top = _run_git(candidate, "rev-parse", "--show-toplevel")
    resolved = Path(top).resolve()
    if resolved != candidate:
        raise ValueError("root must be the repository root")
    return resolved


def _git_metadata_root(root: Path) -> Path:
    absolute_git_dir = Path(_run_git(root, "rev-parse", "--absolute-git-dir")).resolve()
    raw = _run_git(root, "rev-parse", "--git-path", "agent-foundation/execution-attempts")
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(absolute_git_dir)
    except ValueError as exc:
        raise ValueError("execution-attempt store escapes repository Git metadata") from exc
    return resolved


def _store_root(root: Path, *, create: bool) -> Path:
    store = _git_metadata_root(root)
    if create:
        store.mkdir(parents=True, exist_ok=True, mode=0o700)
        if store.is_symlink():
            raise ValueError("execution-attempt store must not be a symlink")
    return store


def _record_path(root: Path, attempt_id: str, *, create_store: bool) -> Path:
    if not ATTEMPT_ID_RE.fullmatch(attempt_id):
        raise ValueError("invalid attempt_id")
    store = _store_root(root, create=create_store)
    path = store / f"{attempt_id}.json"
    resolved = path.resolve()
    try:
        resolved.relative_to(store.resolve())
    except ValueError as exc:
        raise ValueError("attempt path escapes execution-attempt store") from exc
    return path


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    value = value.astimezone(timezone.utc)
    if value.microsecond:
        return value.isoformat(timespec="microseconds").replace("+00:00", "Z")
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not RFC3339_UTC_RE.fullmatch(value):
        raise ValueError("timestamp must be RFC3339 UTC")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError as exc:
        raise ValueError("timestamp must be valid RFC3339 UTC") from exc


def _normalize_repository(value: str) -> str:
    if not isinstance(value, str) or not REPOSITORY_RE.fullmatch(value):
        raise ValueError("repository must be owner/repo")
    return value


def _normalize_task_id(value: str) -> str:
    if not isinstance(value, str) or not TASK_ID_RE.fullmatch(value):
        raise ValueError("invalid task_id")
    return value


def _normalize_revision(value: int) -> int:
    if type(value) is not int or value < 1:
        raise ValueError("task_revision must be a positive integer")
    return value


def _normalize_base(value: str) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise ValueError("execution_base must be a 40-character lowercase Git SHA")
    return value


def _normalize_lease(value: int) -> int:
    if type(value) is not int or not MIN_LEASE_SECONDS <= value <= MAX_LEASE_SECONDS:
        raise ValueError(
            f"lease_seconds must be between {MIN_LEASE_SECONDS} and {MAX_LEASE_SECONDS}"
        )
    return value


def _origin_repository(root: Path) -> str:
    remote = _run_git(root, "remote", "get-url", "origin")
    patterns = (
        re.compile(r"^https://github\.com/([^/]+/[^/]+?)(?:\.git)?$"),
        re.compile(r"^git@github\.com:([^/]+/[^/]+?)(?:\.git)?$"),
        re.compile(r"^ssh://git@github\.com/([^/]+/[^/]+?)(?:\.git)?$"),
    )
    for pattern in patterns:
        match = pattern.fullmatch(remote)
        if match:
            return match.group(1)
    raise ValueError("origin must identify a GitHub owner/repo repository")


def _task_identity(root: Path, task_id: str) -> tuple[str, int]:
    task_path = root / ".agent" / "tasks" / task_id / "task.yaml"
    if not task_path.is_file() or task_path.is_symlink():
        raise ValueError("canonical task artifact is missing")
    text = task_path.read_text(encoding="utf-8")
    id_match = re.search(r"(?m)^task_id:\s*['\"]?([^'\"\s]+)['\"]?\s*$", text)
    revision_match = re.search(r"(?m)^task_revision:\s*([0-9]+)\s*$", text)
    if not id_match or not revision_match:
        raise ValueError("canonical task identity is unreadable")
    return id_match.group(1), int(revision_match.group(1))


def _validate_live_binding(
    root: Path,
    repository: str,
    task_id: str,
    task_revision: int,
    execution_base: str,
) -> None:
    if _origin_repository(root).lower() != repository.lower():
        raise ValueError("repository binding does not match origin")
    current_head = _run_git(root, "rev-parse", "HEAD")
    if current_head != execution_base:
        raise ValueError("execution_base does not match current HEAD")
    actual_task_id, actual_revision = _task_identity(root, task_id)
    if actual_task_id != task_id or actual_revision != task_revision:
        raise ValueError("task binding does not match canonical task artifact")


def _reject_forbidden_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).strip().lower()
            if normalized in FORBIDDEN_FIELD_TOKENS:
                raise ValueError(f"forbidden execution-attempt field: {key}")
            _reject_forbidden_fields(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_forbidden_fields(nested)


def _bounded_token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not BOUNDED_TOKEN_RE.fullmatch(value):
        raise ValueError(f"{label} must be a bounded non-secret identifier")
    return value


def _validate_slice(slice_record: Any, *, started: datetime, last_seen: datetime) -> dict[str, Any]:
    if not isinstance(slice_record, dict) or set(slice_record) != SLICE_KEYS:
        raise ValueError("current_slice fields are invalid")
    if slice_record["authority"] != AUTHORITY:
        raise ValueError("execution slice authority must be NONE")
    if not SLICE_ID_RE.fullmatch(str(slice_record["execution_slice_id"])):
        raise ValueError("invalid execution_slice_id")
    ordinal = slice_record["ordinal"]
    if type(ordinal) is not int or ordinal < 1:
        raise ValueError("execution slice ordinal is invalid")

    operation_class = _bounded_token(slice_record["operation_class"], "operation_class")
    reconciliation_kind = _bounded_token(slice_record["reconciliation_kind"], "reconciliation_kind")
    postcondition_kind = _bounded_token(slice_record["postcondition_kind"], "postcondition_kind")
    if operation_class not in RECONCILIATION_RULES:
        raise ValueError("unsupported execution slice operation_class")
    if reconciliation_kind != operation_class:
        raise ValueError("reconciliation_kind must match operation_class")
    if RECONCILIATION_RULES[reconciliation_kind] != postcondition_kind:
        raise ValueError("postcondition_kind does not match reconciliation rule")
    _bounded_token(slice_record["carrier"], "carrier")
    _bounded_token(slice_record["intent"], "intent")

    observed = _parse_utc(slice_record["observed_at_utc"])
    if observed < started or observed > last_seen:
        raise ValueError("execution slice timestamp is outside attempt bounds")
    runtime_session = slice_record["runtime_session_observation"]
    if runtime_session is not None:
        _bounded_token(runtime_session, "runtime_session_observation")
    lifecycle = slice_record["lifecycle_observation"]
    result = slice_record["result_classification"]
    reconciliation_result = slice_record["reconciliation_result"]
    if lifecycle == "INTENT_RECORDED" and result != "UNRESOLVED":
        raise ValueError("INTENT_RECORDED slice must remain unresolved")
    if lifecycle == "ACK_OBSERVED" and result != "UNRESOLVED":
        raise ValueError("ACK_OBSERVED slice must remain unresolved")
    if lifecycle == "OUTCOME_UNKNOWN" and result != "OUTCOME_UNKNOWN":
        raise ValueError("OUTCOME_UNKNOWN lifecycle requires OUTCOME_UNKNOWN result")
    if lifecycle == "RESULT_OBSERVED" and result not in {"SUCCEEDED", "NO_EFFECT"}:
        raise ValueError("RESULT_OBSERVED slice result is invalid")
    if lifecycle == "RECONCILED" and result not in {"EFFECT_PRESENT", "RETRY_ALLOWED", "OUTCOME_UNKNOWN"}:
        raise ValueError("RECONCILED slice result is invalid")
    if lifecycle not in {"INTENT_RECORDED", "ACK_OBSERVED", "OUTCOME_UNKNOWN", "RESULT_OBSERVED", "RECONCILED"}:
        raise ValueError("execution slice lifecycle observation is invalid")
    if lifecycle == "RECONCILED":
        if reconciliation_result not in RECONCILIATION_RESULTS:
            raise ValueError("reconciled slice requires reconciliation_result")
    elif reconciliation_result is not None:
        raise ValueError("reconciliation_result requires RECONCILED lifecycle")
    return slice_record


def validate_record(record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError("execution-attempt record must be an object")
    _reject_forbidden_fields(record)
    schema_version = record.get("schema_version")
    if schema_version == LEGACY_SCHEMA_VERSION:
        if set(record) != LEGACY_RECORD_KEYS:
            raise ValueError("legacy execution-attempt record fields are invalid")
    elif schema_version == SCHEMA_VERSION:
        if set(record) != RECORD_KEYS:
            raise ValueError("execution-attempt record fields are invalid")
    else:
        raise ValueError("unsupported execution-attempt schema_version")
    if record["artifact"] != ARTIFACT:
        raise ValueError("execution-attempt record identity is invalid")
    if record["authority"] != AUTHORITY:
        raise ValueError("execution-attempt authority must be NONE")
    if not ATTEMPT_ID_RE.fullmatch(str(record["attempt_id"])):
        raise ValueError("invalid attempt_id")
    _normalize_repository(record["repository"])
    _normalize_task_id(record["task_id"])
    _normalize_revision(record["task_revision"])
    _normalize_base(record["execution_base"])
    _normalize_lease(record["lease_seconds"])

    started = _parse_utc(record["started_at_utc"])
    last_seen = _parse_utc(record["last_seen_at_utc"])
    if last_seen < started:
        raise ValueError("last_seen_at_utc precedes started_at_utc")

    if schema_version == SCHEMA_VERSION:
        next_slice_ordinal = record["next_slice_ordinal"]
        if type(next_slice_ordinal) is not int or next_slice_ordinal < 1:
            raise ValueError("next_slice_ordinal is invalid")
        current_slice = record["current_slice"]
        if current_slice is not None:
            _validate_slice(current_slice, started=started, last_seen=last_seen)
            if current_slice["ordinal"] >= next_slice_ordinal:
                raise ValueError("current_slice ordinal must precede next_slice_ordinal")

    checkpoint = record["last_checkpoint"]
    if checkpoint is not None:
        if not isinstance(checkpoint, dict) or set(checkpoint) != CHECKPOINT_KEYS:
            raise ValueError("last_checkpoint fields are invalid")
        if not CHECKPOINT_KIND_RE.fullmatch(str(checkpoint["kind"])):
            raise ValueError("checkpoint kind is invalid")
        observed = _parse_utc(checkpoint["observed_at_utc"])
        if observed < started or observed > last_seen:
            raise ValueError("checkpoint timestamp is outside attempt bounds")
        _normalize_base(checkpoint["local_head"])
        upstream_ref = checkpoint["upstream_ref"]
        upstream_head = checkpoint["upstream_head"]
        if upstream_ref is not None and (
            not isinstance(upstream_ref, str)
            or not upstream_ref
            or len(upstream_ref) > 255
            or "\n" in upstream_ref
        ):
            raise ValueError("checkpoint upstream_ref is invalid")
        if upstream_head is not None:
            _normalize_base(upstream_head)
        if (upstream_ref is None) != (upstream_head is None):
            raise ValueError("checkpoint upstream identity must be complete")
        if type(checkpoint["tracked_dirty"]) is not bool:
            raise ValueError("checkpoint tracked_dirty must be boolean")
        if (
            type(checkpoint["untracked_count"]) is not int
            or not 0 <= checkpoint["untracked_count"] <= MAX_UNTRACKED_COUNT
        ):
            raise ValueError("checkpoint untracked_count is invalid")
        if type(checkpoint["untracked_count_capped"]) is not bool:
            raise ValueError("checkpoint untracked_count_capped must be boolean")

    state = record["state"]
    if state not in {"RUNNING", "TERMINAL"}:
        raise ValueError("execution-attempt state is invalid")
    if state == "RUNNING":
        if record["terminal_result"] is not None or record["terminal_at_utc"] is not None:
            raise ValueError("RUNNING attempt cannot contain terminal marker")
    else:
        result = record["terminal_result"]
        if not isinstance(result, str) or not result.strip() or len(result) > 256 or "\n" in result:
            raise ValueError("TERMINAL attempt requires bounded terminal_result")
        terminal_at = _parse_utc(record["terminal_at_utc"])
        if terminal_at < last_seen:
            raise ValueError("terminal_at_utc precedes last_seen_at_utc")
    return record


def _read_record(root: Path, attempt_id: str) -> dict[str, Any]:
    path = _record_path(root, attempt_id, create_store=False)
    if not path.is_file() or path.is_symlink():
        raise ValueError("execution-attempt record not found")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("execution-attempt record is unreadable") from exc
    return validate_record(record)


def _write_record(root: Path, record: dict[str, Any], *, create: bool) -> Path:
    validate_record(record)
    path = _record_path(root, record["attempt_id"], create_store=True)
    if create and path.exists():
        raise ValueError("attempt_id collision")
    if not create and (not path.is_file() or path.is_symlink()):
        raise ValueError("execution-attempt record not found")
    payload = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=".attempt-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return path


def _assert_forward_time(record: dict[str, Any], now: datetime) -> None:
    if now.astimezone(timezone.utc) < _parse_utc(record["last_seen_at_utc"]):
        raise ValueError("operation time precedes last_seen_at_utc")


def start_attempt(
    root: Path | str,
    repository: str,
    task_id: str,
    task_revision: int,
    execution_base: str,
    *,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    now: datetime | None = None,
    attempt_id: str | None = None,
) -> dict[str, Any]:
    root_path = _repository_root(root)
    repository = _normalize_repository(repository)
    task_id = _normalize_task_id(task_id)
    task_revision = _normalize_revision(task_revision)
    execution_base = _normalize_base(execution_base)
    lease_seconds = _normalize_lease(lease_seconds)
    _validate_live_binding(root_path, repository, task_id, task_revision, execution_base)

    identity = uuid.uuid4().hex if attempt_id is None else attempt_id
    if not ATTEMPT_ID_RE.fullmatch(identity):
        raise ValueError("invalid attempt_id")
    timestamp = _format_utc(now or _now_utc())
    record = {
        "schema_version": SCHEMA_VERSION,
        "artifact": ARTIFACT,
        "authority": AUTHORITY,
        "attempt_id": identity,
        "repository": repository,
        "task_id": task_id,
        "task_revision": task_revision,
        "execution_base": execution_base,
        "started_at_utc": timestamp,
        "last_seen_at_utc": timestamp,
        "lease_seconds": lease_seconds,
        "state": "RUNNING",
        "last_checkpoint": None,
        "next_slice_ordinal": 1,
        "current_slice": None,
        "terminal_result": None,
        "terminal_at_utc": None,
    }
    _write_record(root_path, record, create=True)
    return record


def upgrade_attempt(root: Path | str, attempt_id: str) -> dict[str, Any]:
    root_path = _repository_root(root)
    record = _read_record(root_path, attempt_id)
    if record["schema_version"] == SCHEMA_VERSION:
        return record
    if record["schema_version"] != LEGACY_SCHEMA_VERSION:
        raise ValueError("unsupported execution-attempt schema_version")
    if record["state"] != "RUNNING":
        raise ValueError("only a RUNNING legacy attempt can be upgraded")
    upgraded = dict(record)
    upgraded["schema_version"] = SCHEMA_VERSION
    upgraded["next_slice_ordinal"] = 1
    upgraded["current_slice"] = None
    _write_record(root_path, upgraded, create=False)
    return upgraded


def heartbeat_attempt(
    root: Path | str,
    attempt_id: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    root_path = _repository_root(root)
    record = _read_record(root_path, attempt_id)
    if record["state"] != "RUNNING":
        raise ValueError("TERMINAL attempt cannot return to RUNNING")
    current = now or _now_utc()
    _assert_forward_time(record, current)
    record["last_seen_at_utc"] = _format_utc(current)
    _write_record(root_path, record, create=False)
    return record


def _require_slice_capable_running(record: dict[str, Any]) -> None:
    if record["schema_version"] != SCHEMA_VERSION:
        raise ValueError("legacy execution-attempt record requires explicit upgrade")
    if record["state"] != "RUNNING":
        raise ValueError("TERMINAL attempt cannot accept execution slices")


def _current_slice(record: dict[str, Any], execution_slice_id: str) -> dict[str, Any]:
    _require_slice_capable_running(record)
    current = record["current_slice"]
    if current is None:
        raise ValueError("no unresolved execution slice")
    if current["execution_slice_id"] != execution_slice_id:
        raise ValueError("execution_slice_id does not match current slice")
    return current


def record_slice_intent(
    root: Path | str,
    attempt_id: str,
    operation_class: str,
    carrier: str,
    intent: str,
    reconciliation_kind: str,
    postcondition_kind: str,
    *,
    now: datetime | None = None,
    execution_slice_id: str | None = None,
) -> dict[str, Any]:
    root_path = _repository_root(root)
    record = _read_record(root_path, attempt_id)
    _require_slice_capable_running(record)
    if record["current_slice"] is not None:
        raise ValueError("one unresolved execution slice is already active")
    _bounded_token(operation_class, "operation_class")
    _bounded_token(carrier, "carrier")
    _bounded_token(intent, "intent")
    _bounded_token(reconciliation_kind, "reconciliation_kind")
    _bounded_token(postcondition_kind, "postcondition_kind")
    if operation_class not in RECONCILIATION_RULES:
        raise ValueError("unsupported execution slice operation_class")
    if reconciliation_kind != operation_class:
        raise ValueError("reconciliation_kind must match operation_class")
    if RECONCILIATION_RULES[reconciliation_kind] != postcondition_kind:
        raise ValueError("postcondition_kind does not match reconciliation rule")
    identity = uuid.uuid4().hex if execution_slice_id is None else execution_slice_id
    if not SLICE_ID_RE.fullmatch(identity):
        raise ValueError("invalid execution_slice_id")
    current = now or _now_utc()
    _assert_forward_time(record, current)
    timestamp = _format_utc(current)
    ordinal = record["next_slice_ordinal"]
    record["last_seen_at_utc"] = timestamp
    record["next_slice_ordinal"] = ordinal + 1
    record["current_slice"] = {
        "authority": AUTHORITY,
        "execution_slice_id": identity,
        "ordinal": ordinal,
        "operation_class": operation_class,
        "carrier": carrier,
        "intent": intent,
        "reconciliation_kind": reconciliation_kind,
        "postcondition_kind": postcondition_kind,
        "lifecycle_observation": "INTENT_RECORDED",
        "observed_at_utc": timestamp,
        "runtime_session_observation": None,
        "reconciliation_result": None,
        "result_classification": "UNRESOLVED",
    }
    _write_record(root_path, record, create=False)
    return record


def observe_slice(
    root: Path | str,
    attempt_id: str,
    execution_slice_id: str,
    observation: str,
    *,
    runtime_session_observation: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    if observation not in SLICE_OBSERVATION_RESULTS:
        raise ValueError("unsupported execution slice observation")
    if runtime_session_observation is not None:
        _bounded_token(runtime_session_observation, "runtime_session_observation")
    root_path = _repository_root(root)
    record = _read_record(root_path, attempt_id)
    current_slice = _current_slice(record, execution_slice_id)
    if current_slice["lifecycle_observation"] == "RECONCILED":
        raise ValueError("reconciled execution slice cannot accept direct observation")
    current = now or _now_utc()
    _assert_forward_time(record, current)
    timestamp = _format_utc(current)
    lifecycle, result = SLICE_OBSERVATION_RESULTS[observation]
    current_slice["lifecycle_observation"] = lifecycle
    current_slice["result_classification"] = result
    current_slice["observed_at_utc"] = timestamp
    if runtime_session_observation is not None:
        current_slice["runtime_session_observation"] = runtime_session_observation
    record["last_seen_at_utc"] = timestamp
    _write_record(root_path, record, create=False)
    return record


def reconcile_slice(
    root: Path | str,
    attempt_id: str,
    execution_slice_id: str,
    reconciliation_result: str,
    *,
    fresh: bool,
    now: datetime | None = None,
) -> dict[str, Any]:
    if fresh is not True:
        raise ValueError("reconciliation must be based on fresh attributable state")
    if reconciliation_result not in RECONCILIATION_RESULTS:
        raise ValueError("unsupported reconciliation_result")
    root_path = _repository_root(root)
    record = _read_record(root_path, attempt_id)
    current_slice = _current_slice(record, execution_slice_id)
    if current_slice["result_classification"] in RESOLVED_SLICE_RESULTS:
        raise ValueError("resolved execution slice cannot be reconciled again")
    current = now or _now_utc()
    _assert_forward_time(record, current)
    timestamp = _format_utc(current)
    if reconciliation_result == "EFFECT_PRESENT":
        result_classification = "EFFECT_PRESENT"
    elif reconciliation_result in {"EFFECT_ABSENT_PRECONDITIONS_HOLD", "REPLAY_SAFE_CONTRACT"}:
        result_classification = "RETRY_ALLOWED"
    else:
        result_classification = "OUTCOME_UNKNOWN"
    current_slice["lifecycle_observation"] = "RECONCILED"
    current_slice["observed_at_utc"] = timestamp
    current_slice["reconciliation_result"] = reconciliation_result
    current_slice["result_classification"] = result_classification
    record["last_seen_at_utc"] = timestamp
    _write_record(root_path, record, create=False)
    return record


def retry_is_legal(slice_record: dict[str, Any]) -> bool:
    return (
        slice_record.get("result_classification") == "RETRY_ALLOWED"
        and slice_record.get("reconciliation_result")
        in {"EFFECT_ABSENT_PRECONDITIONS_HOLD", "REPLAY_SAFE_CONTRACT"}
    )


def _checkpoint_git_state(root: Path) -> dict[str, Any]:
    local_head = _run_git(root, "rev-parse", "HEAD")
    upstream_ref = _run_git(
        root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}", check=False
    )
    upstream_head = _run_git(root, "rev-parse", "@{upstream}", check=False) if upstream_ref else ""
    status = _run_git(root, "status", "--porcelain=v1", "--untracked-files=normal")
    tracked_dirty = False
    untracked_count = 0
    capped = False
    for line in status.splitlines():
        if line.startswith("?? "):
            if untracked_count < MAX_UNTRACKED_COUNT:
                untracked_count += 1
            else:
                capped = True
        elif line:
            tracked_dirty = True
    return {
        "local_head": local_head,
        "upstream_ref": upstream_ref or None,
        "upstream_head": upstream_head or None,
        "tracked_dirty": tracked_dirty,
        "untracked_count": untracked_count,
        "untracked_count_capped": capped,
    }


def checkpoint_attempt(
    root: Path | str,
    attempt_id: str,
    kind: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not CHECKPOINT_KIND_RE.fullmatch(kind):
        raise ValueError("checkpoint kind is invalid")
    root_path = _repository_root(root)
    record = _read_record(root_path, attempt_id)
    if record["state"] != "RUNNING":
        raise ValueError("TERMINAL attempt cannot return to RUNNING")
    current = now or _now_utc()
    _assert_forward_time(record, current)
    timestamp = _format_utc(current)
    git_state = _checkpoint_git_state(root_path)
    record["last_seen_at_utc"] = timestamp
    record["last_checkpoint"] = {
        "kind": kind,
        "observed_at_utc": timestamp,
        **git_state,
    }
    _write_record(root_path, record, create=False)
    return record


def clear_slice(
    root: Path | str,
    attempt_id: str,
    execution_slice_id: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    root_path = _repository_root(root)
    record = _read_record(root_path, attempt_id)
    current_slice = _current_slice(record, execution_slice_id)
    if current_slice["result_classification"] not in RESOLVED_SLICE_RESULTS:
        raise ValueError("unresolved or unknown execution slice cannot be cleared")
    checkpoint = record["last_checkpoint"]
    if checkpoint is None:
        raise ValueError("execution slice requires a coherent checkpoint before clear")
    if _parse_utc(checkpoint["observed_at_utc"]) < _parse_utc(current_slice["observed_at_utc"]):
        raise ValueError("checkpoint predates execution slice result observation")
    current = now or _now_utc()
    _assert_forward_time(record, current)
    record["last_seen_at_utc"] = _format_utc(current)
    record["current_slice"] = None
    _write_record(root_path, record, create=False)
    return record


def slice_recovery_classification(slice_record: dict[str, Any] | None) -> str | None:
    if slice_record is None:
        return None
    result = slice_record["result_classification"]
    if result in {"UNRESOLVED", "OUTCOME_UNKNOWN"}:
        return "OUTCOME_UNKNOWN"
    return result


def select_carrier(
    *,
    bounded_sync_safe: bool,
    long_or_uncertain: bool,
    interactive: bool,
    survival_sensitive: bool,
    mutating: bool,
    durable_pipe_available: bool,
    independently_reconcilable: bool,
) -> str:
    """Select the concrete Runtime carrier without assuming PTY restart durability."""
    if (
        bounded_sync_safe
        and not long_or_uncertain
        and not interactive
        and (
            not survival_sensitive
            or (not durable_pipe_available and independently_reconcilable)
        )
    ):
        return "terminal_exec"
    if durable_pipe_available and not interactive:
        return "terminal_start_durable_pipe"
    if not mutating or independently_reconcilable:
        return "terminal_start_process"
    raise ValueError("CURRENT_PHASE_CAPABILITY_UNAVAILABLE")


def terminal_attempt(
    root: Path | str,
    attempt_id: str,
    terminal_result: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    if (
        not isinstance(terminal_result, str)
        or not terminal_result.strip()
        or len(terminal_result) > 256
        or "\n" in terminal_result
    ):
        raise ValueError("terminal_result must be a bounded single-line string")
    root_path = _repository_root(root)
    record = _read_record(root_path, attempt_id)
    if record["state"] == "TERMINAL":
        if record["terminal_result"] != terminal_result:
            raise ValueError("terminal result is immutable once confirmed")
        return record
    current = now or _now_utc()
    _assert_forward_time(record, current)
    timestamp = _format_utc(current)
    record["last_seen_at_utc"] = timestamp
    record["state"] = "TERMINAL"
    record["terminal_result"] = terminal_result
    record["terminal_at_utc"] = timestamp
    _write_record(root_path, record, create=False)
    return record


def inspect_record(record: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    validate_record(record)
    current = (now or _now_utc()).astimezone(timezone.utc)
    if record["state"] == "TERMINAL":
        classification = "TERMINAL_CONFIRMED"
    else:
        expiry = _parse_utc(record["last_seen_at_utc"]) + timedelta(
            seconds=record["lease_seconds"]
        )
        classification = "ACTIVE_LEASE" if current <= expiry else "INTERRUPTED_UNKNOWN"
    current_slice = record.get("current_slice") if record["schema_version"] == SCHEMA_VERSION else None
    return {
        "authority": AUTHORITY,
        "schema_version": record["schema_version"],
        "legacy_schema": record["schema_version"] == LEGACY_SCHEMA_VERSION,
        "attempt_id": record["attempt_id"],
        "repository": record["repository"],
        "task_id": record["task_id"],
        "task_revision": record["task_revision"],
        "execution_base": record["execution_base"],
        "classification": classification,
        "last_seen_at_utc": record["last_seen_at_utc"],
        "last_checkpoint": record["last_checkpoint"],
        "current_slice": current_slice,
        "slice_recovery_classification": slice_recovery_classification(current_slice),
        "terminal_result": record["terminal_result"] if classification == "TERMINAL_CONFIRMED" else None,
        "terminal_at_utc": record["terminal_at_utc"] if classification == "TERMINAL_CONFIRMED" else None,
    }


def inspect_attempt(
    root: Path | str,
    attempt_id: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    root_path = _repository_root(root)
    return inspect_record(_read_record(root_path, attempt_id), now=now)


def list_current_task(
    root: Path | str,
    repository: str,
    task_id: str,
    task_revision: int,
    execution_base: str,
    *,
    now: datetime | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    root_path = _repository_root(root)
    repository = _normalize_repository(repository)
    task_id = _normalize_task_id(task_id)
    task_revision = _normalize_revision(task_revision)
    execution_base = _normalize_base(execution_base)
    if type(limit) is not int or not 1 <= limit <= MAX_LIST_RESULTS:
        raise ValueError(f"limit must be between 1 and {MAX_LIST_RESULTS}")
    store = _store_root(root_path, create=False)
    if not store.exists():
        return []
    if not store.is_dir() or store.is_symlink():
        raise ValueError("execution-attempt store is invalid")

    matches: list[dict[str, Any]] = []
    for path in sorted(store.glob("*.json")):
        attempt_id = path.stem
        if not ATTEMPT_ID_RE.fullmatch(attempt_id):
            continue
        record = _read_record(root_path, attempt_id)
        if (
            record["repository"] == repository
            and record["task_id"] == task_id
            and record["task_revision"] == task_revision
            and record["execution_base"] == execution_base
        ):
            matches.append(inspect_record(record, now=now))
    matches.sort(key=lambda item: (item["last_seen_at_utc"], item["attempt_id"]), reverse=True)
    return matches[:limit]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="exact repository root")
    sub = parser.add_subparsers(dest="operation", required=True)

    start = sub.add_parser("start")
    start.add_argument("--repository", required=True)
    start.add_argument("--task-id", required=True)
    start.add_argument("--task-revision", required=True, type=int)
    start.add_argument("--execution-base", required=True)
    start.add_argument("--lease-seconds", type=int, default=DEFAULT_LEASE_SECONDS)

    for name in ("heartbeat", "inspect", "upgrade"):
        command = sub.add_parser(name)
        command.add_argument("--attempt-id", required=True)

    slice_intent = sub.add_parser("slice-intent")
    slice_intent.add_argument("--attempt-id", required=True)
    slice_intent.add_argument("--operation-class", required=True)
    slice_intent.add_argument("--carrier", required=True)
    slice_intent.add_argument("--intent", required=True)
    slice_intent.add_argument("--reconciliation-kind", required=True)
    slice_intent.add_argument("--postcondition-kind", required=True)
    slice_intent.add_argument("--execution-slice-id")

    slice_observe = sub.add_parser("slice-observe")
    slice_observe.add_argument("--attempt-id", required=True)
    slice_observe.add_argument("--execution-slice-id", required=True)
    slice_observe.add_argument("--observation", required=True)
    slice_observe.add_argument("--runtime-session-observation")

    slice_reconcile = sub.add_parser("slice-reconcile")
    slice_reconcile.add_argument("--attempt-id", required=True)
    slice_reconcile.add_argument("--execution-slice-id", required=True)
    slice_reconcile.add_argument("--reconciliation-result", required=True)
    slice_reconcile.add_argument("--fresh", action="store_true")

    slice_clear = sub.add_parser("slice-clear")
    slice_clear.add_argument("--attempt-id", required=True)
    slice_clear.add_argument("--execution-slice-id", required=True)

    checkpoint = sub.add_parser("checkpoint")
    checkpoint.add_argument("--attempt-id", required=True)
    checkpoint.add_argument("--kind", required=True)

    terminal = sub.add_parser("terminal")
    terminal.add_argument("--attempt-id", required=True)
    terminal.add_argument("--result", required=True)

    listing = sub.add_parser("list-current-task")
    listing.add_argument("--repository", required=True)
    listing.add_argument("--task-id", required=True)
    listing.add_argument("--task-revision", required=True, type=int)
    listing.add_argument("--execution-base", required=True)
    listing.add_argument("--limit", type=int, default=20)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.root)
    try:
        if args.operation == "start":
            result: Any = start_attempt(
                root,
                args.repository,
                args.task_id,
                args.task_revision,
                args.execution_base,
                lease_seconds=args.lease_seconds,
            )
        elif args.operation == "heartbeat":
            result = heartbeat_attempt(root, args.attempt_id)
        elif args.operation == "upgrade":
            result = upgrade_attempt(root, args.attempt_id)
        elif args.operation == "slice-intent":
            result = record_slice_intent(
                root,
                args.attempt_id,
                args.operation_class,
                args.carrier,
                args.intent,
                args.reconciliation_kind,
                args.postcondition_kind,
                execution_slice_id=args.execution_slice_id,
            )
        elif args.operation == "slice-observe":
            result = observe_slice(
                root,
                args.attempt_id,
                args.execution_slice_id,
                args.observation,
                runtime_session_observation=args.runtime_session_observation,
            )
        elif args.operation == "slice-reconcile":
            result = reconcile_slice(
                root,
                args.attempt_id,
                args.execution_slice_id,
                args.reconciliation_result,
                fresh=args.fresh,
            )
        elif args.operation == "slice-clear":
            result = clear_slice(root, args.attempt_id, args.execution_slice_id)
        elif args.operation == "checkpoint":
            result = checkpoint_attempt(root, args.attempt_id, args.kind)
        elif args.operation == "terminal":
            result = terminal_attempt(root, args.attempt_id, args.result)
        elif args.operation == "inspect":
            result = inspect_attempt(root, args.attempt_id)
        else:
            result = list_current_task(
                root,
                args.repository,
                args.task_id,
                args.task_revision,
                args.execution_base,
                limit=args.limit,
            )
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=os.sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
