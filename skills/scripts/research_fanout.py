#!/usr/bin/env python3
"""Validate and render non-authoritative read-only research artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from validate_skill_library import (
    ProtocolYamlError,
    UnsupportedProtocolSerializationError,
    parse_mapping,
    preprocess_yaml,
)

SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA64_RE = re.compile(r"^[0-9a-f]{64}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

REQUEST_KEYS = {
    "schema_version",
    "artifact",
    "authority",
    "specialization",
    "target",
    "question",
    "evidence_scope",
    "context_refs",
    "read_only",
    "mutation_authority",
    "decision_authority",
    "peer_results",
    "architect_synthesis_required",
}
RESULT_KEYS = {
    "schema_version",
    "artifact",
    "authority",
    "request",
    "facts",
    "inferences",
    "options",
    "recommendation",
    "risks",
    "unknown",
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
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(f"{label} keys mismatch: missing={missing} extra={extra}")


def _bounded_string(value: Any, label: str, *, maximum: int, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    if not allow_empty and not value.strip():
        raise ValueError(f"{label} must be non-empty")
    if len(value) > maximum or "\n" in value or "\r" in value:
        raise ValueError(f"{label} must be single-line and <= {maximum} characters")
    return value


def _repository(value: Any, label: str) -> str:
    text = _bounded_string(value, label, maximum=200)
    if not REPOSITORY_RE.fullmatch(text) or ".." in text:
        raise ValueError(f"{label} must be owner/repo")
    return text


def _relative_path(value: str, label: str) -> None:
    path = value.split("#", 1)[0]
    if path.startswith("/") or not path:
        raise ValueError(f"{label} path must be repository-relative")
    parts = Path(path).parts
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"{label} path must not escape its repository")


def validate_context_locator(value: Any, label: str) -> str:
    text = _bounded_string(value, label, maximum=512)
    if "@" not in text or ":" not in text:
        raise ValueError(f"{label} must be repository@revision:path")
    repository, revision_path = text.split("@", 1)
    revision, path = revision_path.split(":", 1)
    _repository(repository, f"{label}.repository")
    if not SHA40_RE.fullmatch(revision):
        raise ValueError(f"{label} must use an exact 40-hex revision")
    _relative_path(path, label)
    return text


def validate_evidence_locator(value: Any, label: str) -> str:
    text = _bounded_string(value, label, maximum=512)
    if text.startswith("https://"):
        if any(char.isspace() for char in text):
            raise ValueError(f"{label} URL must not contain whitespace")
        return text
    return validate_context_locator(text, label)


def _string_list(value: Any, label: str, *, maximum_items: int, maximum_item_length: int, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    if not allow_empty and not value:
        raise ValueError(f"{label} must not be empty")
    if len(value) > maximum_items:
        raise ValueError(f"{label} exceeds {maximum_items} items")
    return [
        _bounded_string(item, f"{label}[{index}]", maximum=maximum_item_length)
        for index, item in enumerate(value)
    ]


def validate_request(document: dict[str, Any]) -> dict[str, Any]:
    _exact_keys(document, REQUEST_KEYS, "research request")
    if document["schema_version"] != 1 or document["artifact"] != "RESEARCH_REQUEST":
        raise ValueError("research request identity is invalid")
    if document["authority"] != "NONE" or document["specialization"] != "RESEARCHER":
        raise ValueError("research request must remain non-authoritative Researcher specialization")
    target = document["target"]
    if not isinstance(target, dict):
        raise ValueError("research request target must be a mapping")
    _exact_keys(target, {"repository", "base_revision"}, "research request target")
    _repository(target["repository"], "target.repository")
    if not isinstance(target["base_revision"], str) or not SHA40_RE.fullmatch(target["base_revision"]):
        raise ValueError("target.base_revision must be an exact 40-hex revision")
    _bounded_string(document["question"], "question", maximum=2000)
    _string_list(document["evidence_scope"], "evidence_scope", maximum_items=10, maximum_item_length=300)
    context_refs = document["context_refs"]
    if not isinstance(context_refs, list) or len(context_refs) > 8:
        raise ValueError("context_refs must be a list with at most 8 locators")
    for index, locator in enumerate(context_refs):
        validate_context_locator(locator, f"context_refs[{index}]")
    if document["read_only"] is not True:
        raise ValueError("research request must be read_only")
    if document["mutation_authority"] != "NONE" or document["decision_authority"] != "NONE":
        raise ValueError("research request cannot carry mutation or decision authority")
    if document["peer_results"] != []:
        raise ValueError("research request cannot contain peer results")
    if document["architect_synthesis_required"] is not True:
        raise ValueError("Architect synthesis must remain required")
    return document


def request_digest(document: dict[str, Any]) -> str:
    validate_request(document)
    payload = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_result(document: dict[str, Any]) -> dict[str, Any]:
    _exact_keys(document, RESULT_KEYS, "research result")
    if document["schema_version"] != 1 or document["artifact"] != "RESEARCH_RESULT":
        raise ValueError("research result identity is invalid")
    if document["authority"] != "NONE":
        raise ValueError("research result authority must be NONE")

    request = document["request"]
    if not isinstance(request, dict):
        raise ValueError("research result request must be a mapping")
    _exact_keys(request, {"repository", "base_revision", "request_digest"}, "research result request")
    _repository(request["repository"], "request.repository")
    if not isinstance(request["base_revision"], str) or not SHA40_RE.fullmatch(request["base_revision"]):
        raise ValueError("request.base_revision must be an exact 40-hex revision")
    if not isinstance(request["request_digest"], str) or not SHA64_RE.fullmatch(request["request_digest"]):
        raise ValueError("request.request_digest must be an exact 64-hex digest")

    evidence = document["evidence"]
    if not isinstance(evidence, list) or not evidence or len(evidence) > 20:
        raise ValueError("evidence must contain 1..20 items")
    evidence_ids: set[str] = set()
    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            raise ValueError(f"evidence[{index}] must be a mapping")
        _exact_keys(item, {"id", "locator"}, f"evidence[{index}]")
        evidence_id = _bounded_string(item["id"], f"evidence[{index}].id", maximum=40)
        if evidence_id in evidence_ids:
            raise ValueError(f"duplicate evidence id: {evidence_id}")
        evidence_ids.add(evidence_id)
        validate_evidence_locator(item["locator"], f"evidence[{index}].locator")

    facts = document["facts"]
    if not isinstance(facts, list) or not facts or len(facts) > 30:
        raise ValueError("facts must contain 1..30 items")
    for index, fact in enumerate(facts):
        if not isinstance(fact, dict):
            raise ValueError(f"facts[{index}] must be a mapping")
        _exact_keys(fact, {"statement", "evidence"}, f"facts[{index}]")
        _bounded_string(fact["statement"], f"facts[{index}].statement", maximum=500)
        refs = _string_list(
            fact["evidence"],
            f"facts[{index}].evidence",
            maximum_items=8,
            maximum_item_length=40,
        )
        unknown = sorted(set(refs) - evidence_ids)
        if unknown:
            raise ValueError(f"facts[{index}] references unknown evidence ids: {unknown}")

    _string_list(document["inferences"], "inferences", maximum_items=20, maximum_item_length=500, allow_empty=True)
    _string_list(document["options"], "options", maximum_items=20, maximum_item_length=500, allow_empty=True)
    _bounded_string(document["recommendation"], "recommendation", maximum=1000)
    _string_list(document["risks"], "risks", maximum_items=20, maximum_item_length=500, allow_empty=True)
    _string_list(document["unknown"], "unknown", maximum_items=20, maximum_item_length=500, allow_empty=True)
    return document


def render_packet(document: dict[str, Any], slot: int) -> str:
    validate_request(document)
    target = document["target"]
    lines = [
        f"RESEARCH PACKET {slot}",
        "Role: read-only Researcher (Executor specialization)",
        "Authority: NONE",
        f"Target repository: {target['repository']}",
        f"Exact base revision: {target['base_revision']}",
        f"Question: {document['question']}",
        "",
        "Allowed evidence scope:",
    ]
    lines.extend(f"- {item}" for item in document["evidence_scope"])
    lines.extend(["", "Minimal context references:"])
    if document["context_refs"]:
        lines.extend(f"- {item}" for item in document["context_refs"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "Return one RESEARCH_RESULT with FACTS, INFERENCES, OPTIONS, RECOMMENDATION, RISKS, UNKNOWN, and EVIDENCE.",
            "Do not mutate the target, create tasks/reviews, rebind authority, make final decisions, or consume peer results.",
            "Architect alone performs final evidence synthesis and direction judgment.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_three(request_paths: list[Path]) -> list[str]:
    if len(request_paths) != 3:
        raise ValueError("three-way fan-out requires exactly three request inputs")
    documents = [validate_request(_load_yaml(path)) for path in request_paths]
    return [render_packet(document, index + 1) for index, document in enumerate(documents)]


def _main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    validate_request_parser = sub.add_parser("validate-request")
    validate_request_parser.add_argument("path", type=Path)

    validate_result_parser = sub.add_parser("validate-result")
    validate_result_parser.add_argument("path", type=Path)

    render_parser = sub.add_parser("render-three")
    render_parser.add_argument("requests", nargs=3, type=Path)
    render_parser.add_argument("--output-dir", required=True, type=Path)

    args = parser.parse_args()
    try:
        if args.command == "validate-request":
            document = validate_request(_load_yaml(args.path))
            print(f"OK request {request_digest(document)}")
        elif args.command == "validate-result":
            validate_result(_load_yaml(args.path))
            print("OK result authority=NONE")
        else:
            packets = render_three(args.requests)
            args.output_dir.mkdir(parents=True, exist_ok=True)
            for index, packet in enumerate(packets, 1):
                (args.output_dir / f"research-{index}.txt").write_text(packet, encoding="utf-8")
            print("OK rendered 3 independent research packets")
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
