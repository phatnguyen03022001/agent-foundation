#!/usr/bin/env python3
"""Adversarial regression tests for validate_skill_library.py."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = Path("scripts/validate_skill_library.py")
_VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "validate_skill_library_under_test",
    ROOT / VALIDATOR,
)
assert _VALIDATOR_SPEC is not None and _VALIDATOR_SPEC.loader is not None
VALIDATOR_MODULE = importlib.util.module_from_spec(_VALIDATOR_SPEC)
_VALIDATOR_SPEC.loader.exec_module(VALIDATOR_MODULE)


class ValidatorRegressionTests(unittest.TestCase):
    def fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name) / "repo"
        shutil.copytree(ROOT, root)
        self.addCleanup(temp.cleanup)
        return temp, root

    def materialize_expanded_task_template(self, root: Path) -> Path:
        path = root / "templates" / "task.yaml"
        text = path.read_text(encoding="utf-8")
        marker = "\nacceptance_criteria:\n"
        self.assertIn(marker, text)
        block = (
            "\ncontinuation_policy:\n"
            "  mode: MANUAL\n"
            "  stop_conditions:\n"
            "    - BLOCKED\n"
            "    - STALE_STATE\n"
            "    - AUTHORITY_REQUIRED\n"
            "    - CURRENT_PHASE_CAPABILITY_UNAVAILABLE\n"
            "    - REVIEW_REQUIRED\n"
            "    - REVERIFY_REQUIRED\n"
            "    - USER_STOP\n"
            "\ncapability_requirements:\n"
            "  EXECUTION:\n"
            "    - repository_content_write\n"
            "\nrelease_authority:\n"
            "  create_version_tag: false\n"
            "  mutate_repository_metadata: false\n"
            "  publish_release: false\n"
        )
        path.write_text(text.replace(marker, block + marker, 1), encoding="utf-8")
        return path

    def materialize_expanded_report_template(self, root: Path) -> Path:
        path = root / "templates" / "report.yaml"
        text = path.read_text(encoding="utf-8")
        text = text.replace('  authorized_base_head: ""\n  final_execution_head: ""', '  authorized_base_head: ""\n  pre_execution_head: ""\n  final_execution_head: ""', 1)
        text = text.replace('  authorized_revision: ""\n', '  authorized_revision: ""\n  observed_revision: ""\n', 1)
        marker = "\ncapability_preflight:\n"
        self.assertIn(marker, text)
        preflight = (
            "\nexecution_skills_used:\n"
            "  required: []\n"
            "  recommended: []\n"
            "  external: []\n"
            "\npre_execution_checks:\n"
            "  protocol_version_supported: false\n"
            "  handoff_type_confirmed: false\n"
            "  task_at_base_confirmed: false\n"
            "  task_identity_confirmed: false\n"
            "  architect_binding_confirmed: false\n"
            "  repository_confirmed: false\n"
            "  branch_confirmed: false\n"
            "  base_head_confirmed: false\n"
            "  skill_revision_confirmed: false\n"
            "  required_execution_skills_available: false\n"
            "  structure_authority_confirmed: false\n"
            "  working_tree_clean: false\n"
        )
        text = text.replace(marker, preflight + marker, 1)
        marker = "\npushed: false\n"
        self.assertIn(marker, text)
        evidence = (
            "\nlocal_hygiene:\n"
            "  result: PASS\n"
            '  run_root: ""\n'
            "  cleanup_performed: false\n"
            "  retained: []\n"
            '  evidence: ""\n'
            "\ncommits_created:\n"
            '  - sha: ""\n'
            '    message: ""\n'
        )
        text = text.replace(marker, evidence + marker + "promoted_to_main: false\n", 1)
        marker = "\nresult: NEEDS_REVIEW\n"
        text = text.replace(
            marker,
            '\nexecutor_checks:\n  - check_id: CHECK-1\n    result: NOT_PROVEN\n    evidence: ""\n' + marker,
            1,
        )
        self.assertIn(marker, text)
        tail = (
            "\ndiscovered_gaps:\n"
            "  - gap_id: GAP-001\n"
            "    classification: FOLLOW_UP\n"
            "    type: architecture\n"
            "    severity: high\n"
            '    description: ""\n'
            '    evidence: ""\n'
            '    impact: ""\n'
            "    blocks_current_task: false\n"
            "    action_taken: none\n"
            "    suggested_next_step: architect_review\n"
            "\nstructural_observations:\n"
            "  - type: file_growth\n"
            '    path: ""\n'
            '    evidence: ""\n'
            "    recommendation: split_candidate\n"
            "    action_taken: none\n"
            "\ndeviations_from_task: []\n"
            "blockers: []\n"
            "\nworking_tree_after:\n"
            "  clean: false\n"
            '  summary: ""\n'
        )
        path.write_text(text.replace(marker, tail + marker, 1), encoding="utf-8")
        return path

    def materialize_expanded_review_template(self, root: Path) -> Path:
        path = root / "templates" / "review.yaml"
        text = path.read_text(encoding="utf-8")
        marker = "\ncontract_compliance:\n"
        self.assertIn(marker, text)
        independence = (
            "\nindependence:\n"
            "  reviewer_role: ARCHITECT\n"
            "  separate_session_from_executor: true\n"
            "  exact_report_identity_verified: false\n"
        )
        text = text.replace(marker, independence + marker, 1)
        tail = (
            "\ngap_disposition:\n"
            "  - gap_id: GAP-001\n"
            "    decision: follow_up_task\n"
            '    rationale: ""\n'
            "\nfollow_up_tasks:\n"
            '  - task_id: ""\n'
            "    origin:\n"
            "      type: discovered_gap\n"
            "      task_id: TASK-0001\n"
            "      gap_id: GAP-001\n"
            "\npromotion_readiness:\n"
            "  eligible_for_candidate_capture: false\n"
            '  reason: ""\n'
            "\nnotes: []\n"
        )
        path.write_text(text.rstrip() + tail, encoding="utf-8")
        return path

    def run_validator(self, root: Path) -> subprocess.CompletedProcess[str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        original_root = VALIDATOR_MODULE.ROOT
        try:
            VALIDATOR_MODULE.ROOT = root
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                returncode = VALIDATOR_MODULE.main()
        finally:
            VALIDATOR_MODULE.ROOT = original_root
        return subprocess.CompletedProcess(
            args=["python3", str(root / VALIDATOR)],
            returncode=returncode,
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue(),
        )

    def assert_rejected(self, mutate) -> str:
        _, root = self.fixture()
        mutate(root)
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def test_canonical_library_passes(self) -> None:
        _, root = self.fixture()
        result = self.run_validator(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hidden_nested_sixteenth_skill_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / ".hidden" / "SKILL.md"
            path.parent.mkdir()
            path.write_text("---\nname: hidden\ndescription: Use when hidden.\n---\n", encoding="utf-8")
        output = self.assert_rejected(mutate)
        self.assertIn("unexpected=['.hidden/SKILL.md']", output)

    def test_duplicate_key_inside_sequence_mapping_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / "templates" / "task.yaml"
            text = path.read_text(encoding="utf-8")
            text = text.replace('    role: ""\n    precedence: 1', '    role: ""\n    source: duplicate\n    precedence: 1')
            path.write_text(text, encoding="utf-8")
        output = self.assert_rejected(mutate)
        self.assertIn("duplicate mapping key 'source'", output)

    def test_malformed_sequence_mapping_item_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / "templates" / "task.yaml"
            text = path.read_text(encoding="utf-8").replace('  - source: ""', '  - source ""', 1)
            path.write_text(text, encoding="utf-8")
        output = self.assert_rejected(mutate)
        self.assertIn("scalar sequence item cannot have nested content", output)

    def test_invalid_nested_sequence_structure_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / "templates" / "task.yaml"
            text = path.read_text(encoding="utf-8").replace('  required:\n    - executor', '  required:\n      - executor', 1)
            path.write_text(text, encoding="utf-8")
        output = self.assert_rejected(mutate)
        self.assertIn("must indent by two spaces", output)

    def test_missing_acceptance_criteria_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / "templates" / "task.yaml"
            text = path.read_text(encoding="utf-8").replace("acceptance_criteria:", "acceptance_missing:", 1)
            path.write_text(text, encoding="utf-8")
        output = self.assert_rejected(mutate)
        self.assertIn("missing required path 'acceptance_criteria'", output)

    def test_unexpected_skill_frontmatter_key_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / "architect" / "SKILL.md"
            text = path.read_text(encoding="utf-8").replace("description:", "version: 1\ndescription:", 1)
            path.write_text(text, encoding="utf-8")
        output = self.assert_rejected(mutate)
        self.assertIn("unexpected frontmatter key 'version'", output)

    def test_execution_ready_requires_report_commit_authority(self) -> None:
        def mutate(root: Path) -> None:
            path = root / "templates" / "task.yaml"
            text = path.read_text(encoding="utf-8")
            text = text.replace("status: UNRESOLVED", "status: NOT_APPLICABLE", 1)
            text = text.replace('rationale: ""', 'rationale: "structure unchanged"', 1)
            text = text.replace("execution_ready: false", "execution_ready: true", 1)
            path.write_text(text, encoding="utf-8")
        output = self.assert_rejected(mutate)
        self.assertIn("requires Executor git_authority.commit", output)

    def test_unterminated_quoted_scalar_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = root / "templates" / "task.yaml"
            text = path.read_text(encoding="utf-8")
            self.assertIn("task_id: TASK-0001", text)
            text = text.replace("task_id: TASK-0001", 'task_id: "TASK-0001', 1)
            path.write_text(text, encoding="utf-8")
        output = self.assert_rejected(mutate)
        self.assertIn("unterminated quoted scalar", output)

    def test_exact_execution_base_gate_is_required(self) -> None:
        def mutate(root: Path) -> None:
            path = root / "templates" / "task.yaml"
            text = path.read_text(encoding="utf-8")
            before = "  require_exact_match: true"
            self.assertIn(before, text)
            text = text.replace(before, "  require_exact_match_missing: true", 1)
            path.write_text(text, encoding="utf-8")
        output = self.assert_rejected(mutate)
        self.assertIn("missing required path 'execution_base.require_exact_match'", output)

    def test_structure_restriction_fields_are_required(self) -> None:
        cases = [
            ("structure_policy.unlisted_new_files.allowed", "    allowed: false", "    allowed_missing: false"),
            ("structure_policy.unlisted_new_files.max", "    max: 0", "    max_missing: 0"),
            ("structure_policy.unlisted_new_files.within", "    within: []", "    within_missing: []"),
            ("structure_policy.unlisted_new_files.purpose", '    purpose: ""', '    purpose_missing: ""'),
            ("structure_policy.allow_new_top_level_directories", "  allow_new_top_level_directories: false", "  allow_new_top_level_directories_missing: false"),
            ("structure_policy.allow_new_shared_modules", "  allow_new_shared_modules: false", "  allow_new_shared_modules_missing: false"),
        ]
        for dotted, before, after in cases:
            with self.subTest(path=dotted):
                def mutate(root: Path, before=before, after=after) -> None:
                    path = root / "templates" / "task.yaml"
                    legacy = root / ".agent" / "tasks" / "TASK-0001" / "task.yaml"
                    path.write_text(legacy.read_text(encoding="utf-8"), encoding="utf-8")
                    text = path.read_text(encoding="utf-8")
                    self.assertIn(before, text)
                    text = text.replace(before, after, 1)
                    path.write_text(text, encoding="utf-8")
                output = self.assert_rejected(mutate)
                self.assertIn(f"missing required path '{dotted}'", output)

    def test_report_pre_execution_evidence_fields_are_required(self) -> None:
        keys = [
            "handoff_type_confirmed", "task_identity_confirmed", "architect_binding_confirmed",
            "repository_confirmed", "branch_confirmed", "base_head_confirmed",
            "skill_revision_confirmed", "required_execution_skills_available",
            "structure_authority_confirmed", "working_tree_clean",
        ]
        for key in keys:
            with self.subTest(key=key):
                def mutate(root: Path, key=key) -> None:
                    path = self.materialize_expanded_report_template(root)
                    text = path.read_text(encoding="utf-8")
                    before = f"  {key}: false"
                    self.assertIn(before, text)
                    text = text.replace(before, f"  {key}_missing: false", 1)
                    path.write_text(text, encoding="utf-8")
                output = self.assert_rejected(mutate)
                self.assertIn(f"path 'pre_execution_checks' missing required fields ['{key}']", output)

    def test_review_identity_compliance_field_is_required(self) -> None:
        def mutate(root: Path) -> None:
            path = root / "templates" / "review.yaml"
            text = path.read_text(encoding="utf-8")
            before = "  identity: NOT_PROVEN"
            self.assertIn(before, text)
            text = text.replace(before, "  identity_missing: NOT_PROVEN", 1)
            path.write_text(text, encoding="utf-8")
        output = self.assert_rejected(mutate)
        self.assertIn("missing required path 'contract_compliance.identity'", output)

    def test_mapping_sequence_required_fields_and_types_are_enforced(self) -> None:
        cases = [
            ("templates/task.yaml", '  - id: AC-1\n    requirement: ""\n    evidence_required: ""', "  - banana: potato", "acceptance_criteria[0]"),
            ("templates/task.yaml", "    precedence: 1", '    precedence: "wrong"', "authority_sources[0].precedence"),
            ("templates/report.yaml", '  - type: file_growth\n    path: ""\n    evidence: ""\n    recommendation: split_candidate\n    action_taken: none', '  - path: ""\n    evidence: ""\n    recommendation: split_candidate\n    action_taken: none', "structural_observations[0]"),
            ("templates/report.yaml", '  - criterion_id: AC-1\n    status: NOT_PROVEN\n    evidence: ""', '  - status: NOT_PROVEN\n    evidence: ""', "acceptance_evidence[0]"),
        ]
        for relative, before, after, expected in cases:
            with self.subTest(path=relative, expected=expected):
                def mutate(root: Path, relative=relative, before=before, after=after) -> None:
                    path = root / relative
                    text = path.read_text(encoding="utf-8")
                    if relative == "templates/report.yaml" and before not in text:
                        path = self.materialize_expanded_report_template(root)
                        text = path.read_text(encoding="utf-8")
                    self.assertIn(before, text)
                    path.write_text(text.replace(before, after, 1), encoding="utf-8")
                output = self.assert_rejected(mutate)
                self.assertIn(expected, output)

    def test_mapping_sequence_closed_values_and_keys_are_enforced(self) -> None:
        cases = [
            ("templates/report.yaml", "    classification: FOLLOW_UP", "    classification: BANANA", "unsupported value 'BANANA'"),
            ("templates/report.yaml", '    message: ""', '    message: ""\n    path: not-a-commit-record', "unexpected fields ['path']"),
        ]
        for relative, before, after, expected in cases:
            with self.subTest(expected=expected):
                def mutate(root: Path, relative=relative, before=before, after=after) -> None:
                    path = root / relative
                    text = path.read_text(encoding="utf-8")
                    if relative == "templates/report.yaml" and before not in text:
                        path = self.materialize_expanded_report_template(root)
                        text = path.read_text(encoding="utf-8")
                    self.assertIn(before, text)
                    path.write_text(text.replace(before, after, 1), encoding="utf-8")
                output = self.assert_rejected(mutate)
                self.assertIn(expected, output)

    def test_review_gap_disposition_schema_is_enforced(self) -> None:
        def mutate(root: Path) -> None:
            path = self.materialize_expanded_review_template(root)
            text = path.read_text(encoding="utf-8")
            before = "  - gap_id: GAP-001\n    decision: follow_up_task\n    rationale: \"\""
            self.assertIn(before, text)
            path.write_text(text.replace(before, "  - wrong_key: true", 1), encoding="utf-8")
        output = self.assert_rejected(mutate)
        self.assertIn("gap_disposition[0]", output)

    def test_defined_gap_classification_remains_accepted(self) -> None:
        _, root = self.fixture()
        path = self.materialize_expanded_report_template(root)
        text = path.read_text(encoding="utf-8")
        self.assertIn("    classification: FOLLOW_UP", text)
        path.write_text(text.replace("    classification: FOLLOW_UP", "    classification: LOCAL", 1), encoding="utf-8")
        result = self.run_validator(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_newly_protected_canonical_fields_are_required(self) -> None:
        cases = [
            ("templates/task.yaml", "origin.type", "  type: user_request"),
            ("templates/task.yaml", "origin.task_id", '  task_id: ""'),
            ("templates/task.yaml", "origin.gap_id", '  gap_id: ""'),
            ("templates/task.yaml", "target.branch.role", "    role: integration"),
            ("templates/task.yaml", "execution_base.capture", "  capture: after_final_planning_commit"),
            ("templates/task.yaml", "architect_analysis_skills", "architect_analysis_skills: []"),
            ("templates/task.yaml", "external_skills.architect_analysis", "  architect_analysis: []"),
            ("templates/task.yaml", "external_skills.execution_required", "  execution_required: []"),
            ("templates/task.yaml", "external_skills.execution_recommended", "  execution_recommended: []"),
            ("templates/task.yaml", "objective", 'objective: ""'),
            ("templates/task.yaml", "scope.allowed_existing_files_or_components", '  allowed_existing_files_or_components:\n    - ""'),
            ("templates/task.yaml", "gap_policy.scope_expansion", "  scope_expansion: forbidden"),
            ("templates/task.yaml", "gap_policy.architecture_change", "  architecture_change: forbidden"),
            ("templates/task.yaml", "gap_policy.spec_change", "  spec_change: forbidden"),
            ("templates/task.yaml", "gap_policy.dependency_change", "  dependency_change: revised_contract_required"),
            ("templates/task.yaml", "gap_policy.public_contract_change", "  public_contract_change: revised_contract_required"),
            ("templates/task.yaml", "verification.authoritative_verification.required", "    required: false"),
            ("templates/task.yaml", "verification.authoritative_verification.mechanism", '    mechanism: ""'),
            ("templates/task.yaml", "verification.authoritative_verification.expected_signal", '    expected_signal: ""'),
            ("templates/report.yaml", "execution.branch.role", "    role: integration"),
            ("templates/report.yaml", "skill_library.repository", "  repository: phatnguyen03022001/agent-foundation"),
            ("templates/report.yaml", "execution_skills_used.recommended", "  recommended: []"),
            ("templates/report.yaml", "execution_skills_used.external", "  external: []"),
            ("templates/report.yaml", "pushed", "pushed: false"),
            ("templates/report.yaml", "authoritative_verification.required", "  required: false"),
            ("templates/report.yaml", "authoritative_verification.performed", "  performed: false"),
            ("templates/report.yaml", "authoritative_verification.result", '  result: ""'),
            ("templates/report.yaml", "authoritative_verification.evidence", '  evidence: ""'),
            ("templates/report.yaml", "working_tree_after.clean", "  clean: false"),
            ("templates/report.yaml", "working_tree_after.summary", '  summary: ""'),
            ("templates/review.yaml", "promotion_readiness.reason", '  reason: ""'),
        ]
        for relative, dotted, before in cases:
            with self.subTest(path=dotted):
                def mutate(root: Path, relative=relative, dotted=dotted, before=before) -> None:
                    path = root / relative
                    if relative == "templates/report.yaml" and dotted.startswith(("execution_skills_used.", "working_tree_after.")):
                        path = self.materialize_expanded_report_template(root)
                    elif relative == "templates/review.yaml" and dotted.startswith("promotion_readiness."):
                        path = self.materialize_expanded_review_template(root)
                    text = path.read_text(encoding="utf-8")
                    needle = f"\n{before}\n"
                    self.assertIn(needle, text)
                    path.write_text(text.replace(needle, "\n", 1), encoding="utf-8")
                output = self.assert_rejected(mutate)
                if dotted.startswith(("execution_skills_used.", "working_tree_after.", "promotion_readiness.")):
                    parent, field = dotted.rsplit(".", 1)
                    self.assertIn(f"path '{parent}' missing required fields ['{field}']", output)
                else:
                    self.assertIn(f"missing required path '{dotted}'", output)

    def test_review_ineligible_states_cannot_be_candidate_eligible(self) -> None:
        for state in ("REVISION_REQUIRED", "BLOCKED"):
            with self.subTest(state=state):
                _, root = self.fixture()
                path = self.materialize_expanded_review_template(root)
                text = path.read_text(encoding="utf-8")
                text = text.replace("state: REVISION_REQUIRED", f"state: {state}", 1)
                text = text.replace("  eligible_for_candidate_capture: false", "  eligible_for_candidate_capture: true", 1)
                path.write_text(text, encoding="utf-8")
                result = self.run_validator(root)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("only ACCEPTED review may be candidate-eligible", result.stdout + result.stderr)

    def test_review_accepted_eligibility_combinations_are_valid(self) -> None:
        for eligible in (True, False):
            with self.subTest(eligible=eligible):
                _, root = self.fixture()
                path = self.materialize_expanded_review_template(root)
                text = path.read_text(encoding="utf-8")
                text = text.replace("state: REVISION_REQUIRED", "state: ACCEPTED", 1)
                text = text.replace(
                    "  exact_report_identity_verified: false",
                    "  exact_report_identity_verified: true",
                    1,
                )
                if eligible:
                    text = text.replace("  eligible_for_candidate_capture: false", "  eligible_for_candidate_capture: true", 1)
                path.write_text(text, encoding="utf-8")
                result = self.run_validator(root)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_review_state_values_are_closed(self) -> None:
        _, root = self.fixture()
        path = root / "templates" / "review.yaml"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("state: REVISION_REQUIRED", "state: UNKNOWN", 1), encoding="utf-8")
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("unsupported review state", result.stdout + result.stderr)

    def test_internal_skill_taxonomy_is_derived_from_rationalization(self) -> None:
        document = json.loads((ROOT / ".agent" / "rationalization.json").read_text(encoding="utf-8"))
        expected = {
            record["skill_id"]
            for record in document["dispositions"]
            if record["disposition"] in VALIDATOR_MODULE.INTERNAL_DISPOSITIONS
        }
        discovered = {path.parent.name for path in ROOT.rglob("SKILL.md")}
        self.assertEqual(discovered, expected)
        self.assertEqual(tuple(document["starting_taxonomy"]), VALIDATOR_MODULE.STARTING_SKILLS)

    def test_retired_git_workflow_resolves_to_task_protocol(self) -> None:
        document = json.loads((ROOT / ".agent" / "rationalization.json").read_text(encoding="utf-8"))
        record = next(item for item in document["dispositions"] if item["skill_id"] == "github-workflow")
        self.assertEqual(record["disposition"], "RETIRE")
        self.assertEqual(record["surviving_semantic_owner"], "canonical:skills/protocols/TASK_PROTOCOL.md")
        self.assertFalse((ROOT / "github-workflow").exists())
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        catalog = readme.split("<!-- SKILL_CATALOG_START -->", 1)[1].split("<!-- SKILL_CATALOG_END -->", 1)[0]
        self.assertNotIn("`github-workflow`", catalog)
        self.assertIn("exact-pinned external capability seam", readme)

    def test_canonical_continuation_template_is_required_and_closed(self) -> None:
        _, root = self.fixture()
        path = root / "templates" / "continuation.yaml"
        self.assertTrue(path.is_file(), "missing canonical templates/continuation.yaml")
        text = path.read_text(encoding="utf-8")
        required = [
            "handoff_type: CONTINUATION", "phase: PROMOTION", "reviewed_report:",
            "promotion_candidate_head:", "expected_refs:", "expected_state:",
            "prior_result:", "prior_lifecycle_state:", "next_authorized_action:",
        ]
        for token in required:
            self.assertIn(token, text)
        result = self.run_validator(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        path.unlink()
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("missing required protocol template: templates/continuation.yaml", result.stdout + result.stderr)

    def test_continuation_modes_are_closed_and_auto_until_stop_is_legal(self) -> None:
        _, root = self.fixture()
        path = self.materialize_expanded_task_template(root)
        text = path.read_text(encoding="utf-8")
        self.assertIn("continuation_policy:\n  mode: MANUAL", text)
        path.write_text(text.replace("  mode: MANUAL", "  mode: AUTO_UNTIL_STOP", 1), encoding="utf-8")
        result = self.run_validator(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        _, root = self.fixture()
        path = self.materialize_expanded_task_template(root)
        text = path.read_text(encoding="utf-8")
        self.assertIn("continuation_policy:\n  mode: MANUAL", text)
        path.write_text(text.replace("  mode: MANUAL", "  mode: FOREVER", 1), encoding="utf-8")
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("unsupported continuation mode", result.stdout + result.stderr)

    def test_continuation_stop_conditions_are_non_waivable(self) -> None:
        def mutate(root: Path) -> None:
            path = self.materialize_expanded_task_template(root)
            text = path.read_text(encoding="utf-8")
            self.assertIn("    - STALE_STATE\n", text)
            path.write_text(text.replace("    - STALE_STATE\n", "", 1), encoding="utf-8")
        output = self.assert_rejected(mutate)
        self.assertIn("missing non-waivable continuation stop conditions", output)

    def test_malformed_continuation_policy_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            path = self.materialize_expanded_task_template(root)
            text = path.read_text(encoding="utf-8")
            before = "continuation_policy:\n  mode: MANUAL\n  stop_conditions:"
            self.assertIn(before, text)
            path.write_text(text.replace(before, "continuation_policy:\n  mode: MANUAL\n  stop_conditions: BLOCKED", 1), encoding="utf-8")
        output = self.assert_rejected(mutate)
        self.assertIn("stop_conditions", output)

    def test_capability_requirement_structure_is_phase_specific_and_closed(self) -> None:
        def mutate(root: Path) -> None:
            path = self.materialize_expanded_task_template(root)
            text = path.read_text(encoding="utf-8")
            before = "capability_requirements:\n  EXECUTION:\n    - repository_content_write"
            self.assertIn(before, text)
            path.write_text(text.replace(before, "capability_requirements:\n  EXECUTION: repository_content_write", 1), encoding="utf-8")
        output = self.assert_rejected(mutate)
        self.assertIn("capability_requirements.EXECUTION", output)

        def mutate_phase(root: Path) -> None:
            path = self.materialize_expanded_task_template(root)
            text = path.read_text(encoding="utf-8")
            self.assertIn("  EXECUTION:", text)
            path.write_text(text.replace("  EXECUTION:", "  BANANA:", 1), encoding="utf-8")
        output = self.assert_rejected(mutate_phase)
        self.assertIn("unsupported capability phase", output)

    def test_release_authority_is_independent_from_git_promotion_authority(self) -> None:
        _, root = self.fixture()
        path = self.materialize_expanded_task_template(root)
        text = path.read_text(encoding="utf-8")
        release_block = (
            "release_authority:\n"
            "  create_version_tag: false\n"
            "  mutate_repository_metadata: false\n"
            "  publish_release: false"
        )
        self.assertIn(release_block, text)
        self.assertIn("  promote_to_main: false", text)
        path.write_text(text.replace("  promote_to_main: false", "  promote_to_main: true", 1), encoding="utf-8")
        result = self.run_validator(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        _, root = self.fixture()
        path = self.materialize_expanded_task_template(root)
        text = path.read_text(encoding="utf-8")
        self.assertIn("  publish_release: false", text)
        path.write_text(text.replace("  publish_release: false", "  publish_release: no", 1), encoding="utf-8")
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("release_authority.publish_release", result.stdout + result.stderr)

    def test_legacy_expanded_protocol_v3_task_remains_valid(self) -> None:
        _, root = self.fixture()
        legacy = root / ".agent" / "tasks" / "TASK-0001" / "task.yaml"
        self.assertTrue(legacy.is_file())
        text = legacy.read_text(encoding="utf-8")
        self.assertNotIn("continuation_policy:", text)
        self.assertNotIn("release_authority:", text)
        (root / "templates" / "task.yaml").write_text(text, encoding="utf-8")
        result = self.run_validator(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_canonical_template_identity_consistency_includes_continuation(self) -> None:
        _, root = self.fixture()
        original_root = VALIDATOR_MODULE.ROOT
        try:
            VALIDATOR_MODULE.ROOT = root
            docs = {
                name: VALIDATOR_MODULE.load_protocol_document(f"templates/{name}.yaml")
                for name in ("task", "handoff", "report", "review", "continuation")
            }
        finally:
            VALIDATOR_MODULE.ROOT = original_root
        for name, doc in docs.items():
            self.assertIsNotNone(doc, name)
        task = docs["task"]
        handoff = docs["handoff"]
        report = docs["report"]
        review = docs["review"]
        continuation = docs["continuation"]
        assert task and handoff and report and review and continuation
        self.assertEqual(task["protocol_version"], 3)
        self.assertEqual(handoff["protocol_version"], 3)
        self.assertEqual(report["protocol_version"], 3)
        self.assertEqual(review["protocol_version"], 3)
        self.assertEqual(continuation["protocol_version"], 3)
        self.assertEqual(task["task_id"], handoff["task"]["id"])
        self.assertEqual(task["task_id"], report["task_id"])
        self.assertEqual(task["task_id"], review["task_id"])
        self.assertEqual(task["task_id"], continuation["task"]["id"])
        self.assertEqual(task["task_revision"], handoff["task"]["revision"])
        self.assertEqual(task["task_revision"], report["task_revision"])
        self.assertEqual(task["task_revision"], review["task_revision"])
        self.assertEqual(task["task_revision"], continuation["task"]["revision"])

    def test_task0002_durable_objective_and_material_decision_doctrine(self) -> None:
        architect = (ROOT / "architect" / "SKILL.md").read_text(encoding="utf-8")
        protocol = (ROOT / "protocols" / "TASK_PROTOCOL.md").read_text(encoding="utf-8")
        combined = architect + protocol
        for token in (
            "durable user objective",
            "governing, not infallible",
            "compatible",
            "trade-off",
            "regression",
            "explicit informed override",
            "casual assent",
        ):
            self.assertIn(token, combined)

    def test_task0002_current_capability_and_pre_mutation_verification_doctrine(self) -> None:
        protocol = (ROOT / "protocols" / "TASK_PROTOCOL.md").read_text(encoding="utf-8")
        executor = (ROOT / "executor" / "SKILL.md").read_text(encoding="utf-8")
        architect = (ROOT / "architect" / "SKILL.md").read_text(encoding="utf-8")
        combined = protocol + executor + architect
        for token in (
            "known capability",
            "currently available capability",
            "least-powerful",
            "bounded escalation",
            "before the first mutation",
            "native verification",
        ):
            self.assertIn(token, combined)

    def test_task0002_remote_truth_and_local_divergence_doctrine(self) -> None:
        executor = (ROOT / "executor" / "SKILL.md").read_text(encoding="utf-8")
        protocol = (ROOT / "protocols" / "TASK_PROTOCOL.md").read_text(encoding="utf-8")
        combined = (executor + protocol).lower()
        for token in (
            "authorized remote git state",
            "canonical repository truth",
            "local state is an execution copy",
            "local ahead",
            "local dirty",
            "remote drift",
            "auto-push",
            "reset",
            "adopt",
        ):
            self.assertIn(token, combined)

    def test_task0002_task_launch_is_architect_only_non_authority_ux(self) -> None:
        architect = (ROOT / "architect" / "SKILL.md").read_text(encoding="utf-8")
        protocol = (ROOT / "protocols" / "TASK_PROTOCOL.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        combined = architect + protocol + readme
        for token in (
            "TASK LAUNCH",
            "PROMPT TO COPY",
            "presentation only",
            "not persisted",
        ):
            self.assertIn(token, combined)
        self.assertFalse(any("launch" in path.name.lower() for path in (ROOT / "templates").iterdir()))

    def test_task0002_local_hygiene_results_are_closed(self) -> None:
        self.assertEqual(
            getattr(VALIDATOR_MODULE, "LOCAL_HYGIENE_RESULTS", frozenset()),
            frozenset({"PASS", "RETAINED_FOR_EVIDENCE", "BLOCKED"}),
        )
        report = (ROOT / "templates" / "report.yaml").read_text(encoding="utf-8")
        self.assertNotIn("local_hygiene:", report)

        _, root = self.fixture()
        path = self.materialize_expanded_report_template(root)
        text = path.read_text(encoding="utf-8")
        self.assertIn("  result: PASS", text)
        path.write_text(text.replace("  result: PASS", "  result: UNKNOWN", 1), encoding="utf-8")
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("unsupported local hygiene result", result.stdout + result.stderr)

    def test_task0002_local_hygiene_deletion_safety_markers(self) -> None:
        protocol = (ROOT / "protocols" / "TASK_PROTOCOL.md").read_text(encoding="utf-8")
        executor = (ROOT / "executor" / "SKILL.md").read_text(encoding="utf-8")
        combined = protocol + executor
        for token in (
            "run-owned root",
            "realpath",
            "symlink",
            "filesystem root",
            "home",
            "workspace root",
            "repository root",
            "pre-existing",
            "sibling project",
            "arbitrary user-supplied",
            "RETAINED_FOR_EVIDENCE",
            "BLOCKED",
        ):
            self.assertIn(token, combined)

    def test_task0002_legacy_v3_report_without_local_hygiene_remains_valid(self) -> None:
        _, root = self.fixture()
        path = self.materialize_expanded_report_template(root)
        text = path.read_text(encoding="utf-8")
        marker = "local_hygiene:\n"
        self.assertIn(marker, text)
        start = text.index(marker)
        end_marker = "\ncommits_created:\n"
        end = text.index(end_marker, start)
        path.write_text(text[:start] + text[end + 1 :], encoding="utf-8")
        result = self.run_validator(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_task0003_architect_sequential_repository_switching(self) -> None:
        architect = (ROOT / "architect" / "SKILL.md").read_text(encoding="utf-8")
        protocol = (ROOT / "protocols" / "TASK_PROTOCOL.md").read_text(encoding="utf-8")
        combined = architect + protocol
        self.assertNotIn("NEW_ARCHITECT_SESSION_REQUIRED", combined)
        for token in (
            "one active target repository",
            "close the current repository-specific phase",
            "explicitly identify the next `owner/repo`",
            "refresh canonical GitHub truth",
            "discard previous repository-specific assumptions",
            "simultaneous ambiguous active target is forbidden",
        ):
            self.assertIn(token, combined)

    def test_task0003_executor_rebind_requires_terminal_execution(self) -> None:
        executor = (ROOT / "executor" / "SKILL.md").read_text(encoding="utf-8")
        protocol = (ROOT / "protocols" / "TASK_PROTOCOL.md").read_text(encoding="utf-8")
        combined = executor + protocol
        for token in (
            "active task/repository binding remains immutable",
            "explicit terminal handoff/result",
            "previous evidence finalized",
            "no outstanding mutation authority carried forward",
            "fresh repository-local task",
            "fresh exact handoff",
            "fresh exact base HEAD",
        ):
            self.assertIn(token, combined)

    def test_task0003_authority_and_lineage_never_carry_between_repositories(self) -> None:
        executor = (ROOT / "executor" / "SKILL.md").read_text(encoding="utf-8")
        protocol = (ROOT / "protocols" / "TASK_PROTOCOL.md").read_text(encoding="utf-8")
        combined = executor + protocol
        for token in (
            "authority for repository A never grants authority for repository B",
            "report/review/verifier/promotion/release lineage remains repository-local",
            "repository identity",
            "branch identity",
            "task ID/revision",
            "base HEAD",
        ):
            self.assertIn(token, combined)

    def test_task0003_program_is_presentation_only(self) -> None:
        architect = (ROOT / "architect" / "SKILL.md").read_text(encoding="utf-8")
        protocol = (ROOT / "protocols" / "TASK_PROTOCOL.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        combined = architect + protocol + readme
        for token in (
            "PROGRAM",
            "ordered repository-local tasks",
            "presentation only",
            "not a universal multi-repository task authority",
            "shared mutable cross-repository authority",
        ):
            self.assertIn(token, combined)
        program = ROOT / "templates" / "program.generated.json"
        self.assertTrue(program.is_file())
        self.assertEqual(json.loads(program.read_text(encoding="utf-8"))["authority"], "NONE")

    def test_task0003_task_launch_does_not_prescribe_profile_fields(self) -> None:
        architect = (ROOT / "architect" / "SKILL.md").read_text(encoding="utf-8")
        protocol = (ROOT / "protocols" / "TASK_PROTOCOL.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        combined = architect + protocol + readme
        for token in (
            "PROMPT TO COPY",
            "presentation only",
            "does not prescribe TASK LAUNCH field names",
        ):
            self.assertIn(token, combined)

    def test_task0003_two_roles_and_no_orchestration_framework(self) -> None:
        architect = (ROOT / "architect" / "SKILL.md").read_text(encoding="utf-8")
        protocol = (ROOT / "protocols" / "TASK_PROTOCOL.md").read_text(encoding="utf-8")
        combined = architect + protocol
        for token in (
            "two organizational roles",
            "Architect and Executor",
            "Executor specializations",
            "no orchestrator",
            "no registry",
            "no queue",
            "no database",
            "no workflow engine",
        ):
            self.assertIn(token, combined)
        self.assertEqual(VALIDATOR_MODULE.MANDATORY_INTERNAL_ROLES, frozenset({"architect", "executor"}))
        self.assertIn("Supported protocol version: **3**", protocol)


class Task0006FoundationArchitectureTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_three_layer_contract_and_orthogonal_substrates(self) -> None:
        text = self.read("contracts/FOUNDATION_ARCHITECTURE.md")
        self.assertEqual(
            re.findall(r"^## L\d+ — .+$", text, flags=re.MULTILINE),
            ["## L0 — Governance Kernel", "## L1 — Control and Continuity", "## L2 — Capability and Knowledge"],
        )
        self.assertNotIn("## L3", text)
        for token in ("agent-runtime", "GitHub", "MCP", "native execution tools", "orthogonal substrates"):
            self.assertIn(token, text)

    def test_two_roles_and_specialization_boundary(self) -> None:
        text = self.read("contracts/FOUNDATION_ARCHITECTURE.md")
        for token in (
            "exactly two organizational roles: Architect and Executor",
            "Sync and read-only Researcher are Executor specializations",
            "no independent task, mutation, review, acceptance, rebinding, or architecture authority",
        ):
            self.assertIn(token, text)
        self.assertEqual(VALIDATOR_MODULE.MANDATORY_INTERNAL_ROLES, frozenset({"architect", "executor"}))

    def test_capability_state_non_equivalence(self) -> None:
        text = self.read("contracts/FOUNDATION_ARCHITECTURE.md")
        for token in (
            "INDEXED != LOADED", "PINNED != TRUSTED", "SYNCED != ADOPTED",
            "ADOPTED != AUTHORIZED", "LOADED != AUTHORIZED", "SNAPSHOT != AUTHORITY",
        ):
            self.assertIn(token, text)

    def test_research_and_cross_repository_continuity(self) -> None:
        text = self.read("contracts/FOUNDATION_ARCHITECTURE.md")
        for token in (
            "one exact target, base, and question", "minimum relevant context",
            "peer results are not visible", "compact evidence", "not by majority voting",
            "cannot mutate the owner repository", "create a task automatically", "freshly revalidated",
        ):
            self.assertIn(token, text)

    def test_role_kernels_delegate_l1_l2_detail(self) -> None:
        architect = self.read("architect/SKILL.md")
        executor = self.read("executor/SKILL.md")
        protocol = self.read("protocols/TASK_PROTOCOL.md")
        for text in (architect, executor, protocol):
            self.assertIn("FOUNDATION_ARCHITECTURE.md", text)
        self.assertNotIn("## External normative authority and execution environment", architect)
        self.assertNotIn("## Repository construction and acquisition", executor)
        self.assertNotIn("## Execution environment, operator attention, and surface selection", protocol)
        self.assertNotIn("## Deterministic execution bundling", protocol)

class CaseNavigationTests(unittest.TestCase):
    CASE_PATH = Path(".agent/case-router.yaml")
    CANONICAL_CASE = """authority: NONE
routes:
  - id: MATERIAL_JUDGMENT
    role: architect
    binding: generic
    specialization: none
    capabilities:
      - architect
    navigation: none
  - id: READ_ONLY_RESEARCH
    role: executor
    binding: generic
    specialization: researcher
    capabilities:
      - executor
    navigation:
      - research_request_contract
      - research_result_contract
  - id: TASK_EXECUTION
    role: executor
    binding: task
    specialization: none
    capabilities:
      - executor
      - task_protocol
    navigation: none
legacy_aliases:
  - from: EXECUTE
    to: TASK_EXECUTION
"""

    def fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name) / "repo"
        shutil.copytree(ROOT, root)
        self.addCleanup(temp.cleanup)
        return temp, root

    def write_case(self, root: Path, text: str) -> None:
        path = root / self.CASE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run_validator(self, root: Path) -> subprocess.CompletedProcess[str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        original_root = VALIDATOR_MODULE.ROOT
        try:
            VALIDATOR_MODULE.ROOT = root
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                returncode = VALIDATOR_MODULE.main()
        finally:
            VALIDATOR_MODULE.ROOT = original_root
        return subprocess.CompletedProcess(
            args=["python3", str(root / VALIDATOR)],
            returncode=returncode,
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue(),
        )

    def assert_case_rejected(self, text: str, expected: str) -> None:
        _, root = self.fixture()
        self.write_case(root, text)
        result = self.run_validator(root)
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        self.assertIn(expected, output)

    def test_canonical_router_has_exact_three_routes_and_execute_alias(self) -> None:
        _, root = self.fixture()
        path = root / self.CASE_PATH
        self.assertTrue(path.is_file(), f"missing canonical case artifact: {self.CASE_PATH}")
        original_root = VALIDATOR_MODULE.ROOT
        try:
            VALIDATOR_MODULE.ROOT = root
            document = VALIDATOR_MODULE.load_protocol_document(str(self.CASE_PATH))
        finally:
            VALIDATOR_MODULE.ROOT = original_root
        self.assertEqual(document, VALIDATOR_MODULE.EXPECTED_CASE_ROUTER)
        result = self.run_validator(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unknown_or_duplicate_route_class_fails_closed(self) -> None:
        self.assert_case_rejected(
            self.CANONICAL_CASE.replace("MATERIAL_JUDGMENT", "VERIFY", 1),
            "must exactly match canonical route MATERIAL_JUDGMENT",
        )
        duplicate = self.CANONICAL_CASE.replace(
            "legacy_aliases:",
            self.CANONICAL_CASE.split("  - id: TASK_EXECUTION", 1)[1]
            .split("legacy_aliases:", 1)[0]
            .join(["  - id: TASK_EXECUTION", ""]) + "legacy_aliases:",
            1,
        )
        self.assert_case_rejected(duplicate, "routes must contain exactly three canonical route classes")

    def test_wrong_route_binding_or_capabilities_fail_closed(self) -> None:
        wrong_binding = self.CANONICAL_CASE.replace(
            "  - id: READ_ONLY_RESEARCH\n    role: executor\n    binding: generic",
            "  - id: READ_ONLY_RESEARCH\n    role: executor\n    binding: task",
            1,
        )
        self.assert_case_rejected(
            wrong_binding,
            "routes[1] must exactly match canonical route READ_ONLY_RESEARCH",
        )
        wrong_capability = self.CANONICAL_CASE.replace(
            "  - id: MATERIAL_JUDGMENT\n    role: architect\n    binding: generic\n"
            "    specialization: none\n    capabilities:\n      - architect",
            "  - id: MATERIAL_JUDGMENT\n    role: architect\n    binding: generic\n"
            "    specialization: none\n    capabilities:\n      - executor",
            1,
        )
        self.assert_case_rejected(
            wrong_capability,
            "routes[0] must exactly match canonical route MATERIAL_JUDGMENT",
        )

    def test_legacy_execute_alias_and_authority_are_exact(self) -> None:
        self.assert_case_rejected(
            self.CANONICAL_CASE.replace("to: TASK_EXECUTION", "to: MATERIAL_JUDGMENT"),
            "legacy_aliases must map EXECUTE to TASK_EXECUTION exactly once",
        )
        self.assert_case_rejected(
            self.CANONICAL_CASE.replace("authority: NONE", "authority: EXECUTOR"),
            "authority must be NONE",
        )

    def test_router_rejects_extra_state_or_top_level_fields(self) -> None:
        self.assert_case_rejected(
            self.CANONICAL_CASE.replace("authority: NONE", "authority: NONE\nstate: READY"),
            "top-level fields must be exactly",
        )
        self.assert_case_rejected(
            self.CANONICAL_CASE.replace("  - id: TASK_EXECUTION", "    state: RUNNING\n  - id: TASK_EXECUTION", 1),
            "routes[1] must exactly match canonical route READ_ONLY_RESEARCH",
        )


class Task0004GovernanceTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_ac1_operator_profile_is_generic_context_not_authority(self) -> None:
        combined = self.read("architect/SKILL.md") + self.read("protocols/TASK_PROTOCOL.md")
        for token in (
            "optional operator profile",
            "host/session/operator",
            "durable preference/environment context",
            "not target-repository factual or mutation authority",
            "explicit current user decisions",
        ):
            self.assertIn(token, combined)
        for forbidden in ("architect-profile", "MacBook", "M3"):
            self.assertNotIn(forbidden, combined)

    def test_ac1_architect_role_is_provider_neutral(self) -> None:
        architect = self.read("architect/SKILL.md")
        for forbidden in (
            "Architect remains ChatGPT",
            "Architect is ChatGPT",
            "Architect must be ChatGPT",
            "Architect always uses ChatGPT",
        ):
            self.assertNotIn(forbidden, architect)

    def test_ac2_prompt_to_copy_is_compact_authority_locator(self) -> None:
        combined = (
            self.read("architect/SKILL.md")
            + self.read("protocols/TASK_PROTOCOL.md")
            + self.read("README.md")
        )
        for token in (
            "authority locator",
            "target owner/repo",
            "task ID/revision/path",
            "exact base HEAD",
            "current phase",
            "resolve canonical authority",
            "Do not duplicate",
        ):
            self.assertIn(token, combined)

    def test_ac3_executor_binding_terminal_is_not_task_lifecycle(self) -> None:
        combined = self.read("executor/SKILL.md") + self.read("protocols/TASK_PROTOCOL.md")
        for token in (
            "Executor-binding terminal",
            "whole-task lifecycle",
            "NEEDS_REVIEW",
            "STALE_STATE",
            "AUTHORITY_REQUIRED",
            "CURRENT_PHASE_CAPABILITY_UNAVAILABLE",
            "no mutation authority remains",
            "does not imply acceptance, promotion, or release",
        ):
            self.assertIn(token, combined)

    def test_ac4_one_current_architect_owns_final_judgment(self) -> None:
        combined = (
            self.read("architect/SKILL.md")
            + self.read("protocols/TASK_PROTOCOL.md")
            + self.read("contracts/ARCHITECT_REVIEW.md")
        )
        for token in (
            "one current governing Architect",
            "ACCEPT/REJECT/REVISE",
            "Executor specialization",
            "advisory evidence",
            "designated verifier",
        ):
            self.assertIn(token, combined)

    def test_ac5_execution_lanes_are_risk_proportional(self) -> None:
        combined = self.read("architect/SKILL.md") + self.read("protocols/TASK_PROTOCOL.md")
        for token in (
            "DIRECT",
            "BOUNDED",
            "HIGH_ASSURANCE",
            "small reversible low-risk",
            "normal task",
            "release-critical",
            "DIRECT never bypasses",
            "HIGH_ASSURANCE must not become the default",
        ):
            self.assertIn(token, combined)

    def test_ac6_git_topologies_are_target_authoritative(self) -> None:
        combined = self.read("protocols/TASK_PROTOCOL.md").lower()
        for token in (
            "main_only",
            "dev_main",
            "dev_staging_main",
            "explicitly activated",
            "never infer or create staging",
            "repository-specific branch policy",
        ):
            self.assertIn(token, combined)

    def test_ac7_normative_external_authority_is_immutable(self) -> None:
        combined = self.read("architect/SKILL.md") + self.read("protocols/TASK_PROTOCOL.md")
        for token in (
            "external repository used as normative authority",
            "immutable revision",
            "before mutation",
            "research/reference evidence",
            "does not become normative authority",
        ):
            self.assertIn(token, combined)

    def test_ac8_evidence_dedup_keeps_legacy_v3(self) -> None:
        protocol = self.read("protocols/TASK_PROTOCOL.md")
        for token in (
            "unconditional protocol boilerplate",
            "task-specific material authority",
            "record evidence once",
            "legacy inline evidence",
            "no parallel compact schema",
        ):
            self.assertIn(token, protocol)
        self.assertIn("Supported protocol version: **3**", protocol)

    def test_ac9_design_readiness_is_material_and_proportional(self) -> None:
        combined = self.read("architect/SKILL.md") + self.read("protocols/TASK_PROTOCOL.md")
        for token in (
            "material-design-readiness",
            "applicable target product/design authority",
            "material missing decisions",
            "consequential implementation",
            "trivial, mechanical, reversible, or well-specified",
        ):
            self.assertIn(token, combined)

    def test_ac10_operator_attention_is_constrained_resource(self) -> None:
        combined = self.read("architect/SKILL.md") + self.read("protocols/TASK_PROTOCOL.md") + self.read("contracts/FOUNDATION_ARCHITECTURE.md")
        for token in (
            "operator attention/manual labor",
            "constrained resource",
            "manual command/RPC bridge",
            "unavailable capability",
            "destructive/irreversible authority",
            "material paid-cost approval",
        ):
            self.assertIn(token, combined)

    def test_ac11_maintenance_defaults_to_no_change(self) -> None:
        combined = (
            self.read("architect/SKILL.md")
            + self.read("simplicity/SKILL.md")
            + self.read("protocols/TASK_PROTOCOL.md")
            + self.read("README.md")
        )
        for token in (
            "NO CHANGE REQUIRED",
            "evidence-backed defect",
            "recurring missing capability",
            "security or compatibility failure",
            "material cost/usability/maintainability regression",
            "smallest safe correction",
            "Preference, novelty, elegance, architectural fashion, and hypothetical future scale",
        ):
            self.assertIn(token, combined)

    def test_ac12_rationalization_derived_taxonomy_is_closed_to_ad_hoc_additions(self) -> None:
        combined = (
            self.read("architect/SKILL.md")
            + self.read("simplicity/SKILL.md")
            + self.read("README.md")
        )
        for token in (
            "rationalization",
            "closed to ad hoc additions",
            "materially distinct recurring responsibility",
            "exceptional correctness/security",
            "arbitrary numeric threshold",
        ):
            self.assertIn(token, combined)
        document = json.loads(self.read(".agent/rationalization.json"))
        expected = {
            record["skill_id"]
            for record in document["dispositions"]
            if record["disposition"] in VALIDATOR_MODULE.INTERNAL_DISPOSITIONS
        }
        self.assertEqual({path.parent.name for path in ROOT.rglob("SKILL.md")}, expected)


class Task0007ProtocolCorrectnessTests(unittest.TestCase):
    def fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name) / "repo"
        shutil.copytree(ROOT, root)
        self.addCleanup(temp.cleanup)
        return temp, root

    def run_validator(self, root: Path) -> subprocess.CompletedProcess[str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        original_root = VALIDATOR_MODULE.ROOT
        try:
            VALIDATOR_MODULE.ROOT = root
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                returncode = VALIDATOR_MODULE.main()
        finally:
            VALIDATOR_MODULE.ROOT = original_root
        return subprocess.CompletedProcess(
            args=["python3", str(root / VALIDATOR)],
            returncode=returncode,
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue(),
        )

    def write_continuation(
        self,
        root: Path,
        *,
        refs: list[tuple[str, str]] | None = None,
        legacy: bool = False,
        phase: str,
        action: str,
        target_ref: str | None = None,
        lifecycle: str = "ACCEPTED",
        prior_lifecycle: str = "ACCEPTED",
        prior_result: str = "ACCEPTED",
    ) -> None:
        if legacy:
            refs_yaml = (
                "expected_refs:\n"
                "  dev: \"<exact expected dev SHA>\"\n"
                "  main: \"<exact expected main SHA>\"\n"
            )
        elif refs:
            refs_yaml = "expected_refs:\n" + "".join(
                f"  - ref: {ref}\n    commit: \"{commit}\"\n" for ref, commit in refs
            )
        else:
            refs_yaml = "expected_refs: []\n"
        target_yaml = f"promotion_target_ref: {target_ref}\n\n" if target_ref is not None else ""
        text = (
            "protocol_version: 3\n"
            "handoff_type: CONTINUATION\n\n"
            "task:\n"
            "  id: TASK-0001\n"
            "  revision: 1\n"
            "  path: .agent/tasks/TASK-0001/task.yaml\n\n"
            f"phase: {phase}\n\n"
            "reviewed_report:\n"
            "  repository: owner/repo\n"
            "  path: .agent/tasks/TASK-0001/report.yaml\n"
            "  commit: \"<exact commit containing reviewed report>\"\n"
            "  report_revision: 1\n\n"
            "promotion_candidate_head: \"<exact accepted-lineage candidate SHA>\"\n\n"
            f"{refs_yaml}\n"
            f"{target_yaml}"
            "expected_state:\n"
            f"  lifecycle: {lifecycle}\n\n"
            f"prior_result: {prior_result}\n"
            f"prior_lifecycle_state: {prior_lifecycle}\n"
            f"next_authorized_action: {action}\n"
        )
        (root / "templates" / "continuation.yaml").write_text(text, encoding="utf-8")

    def assert_passes(self, root: Path) -> None:
        result = self.run_validator(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_rejected(self, root: Path, expected: str) -> None:
        result = self.run_validator(root)
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        self.assertIn(expected, output)

    def test_task0007_canonical_topologies_are_topology_neutral(self) -> None:
        cases = [
            ([], "REVIEW", "STOP", None),
            ([("refs/heads/trunk", "trunk-sha")], "PROMOTION", "PROMOTE_TARGET_REF", "refs/heads/trunk"),
            ([
                ("refs/heads/integration", "integration-sha"),
                ("refs/heads/stable", "stable-sha"),
            ], "PROMOTION", "PROMOTE_TARGET_REF", "refs/heads/stable"),
            ([
                ("refs/heads/build", "build-sha"),
                ("refs/heads/candidate", "candidate-sha"),
                ("refs/heads/production", "production-sha"),
            ], "PROMOTION", "PROMOTE_TARGET_REF", "refs/heads/production"),
        ]
        for refs, phase, action, target in cases:
            with self.subTest(refs=refs):
                _, root = self.fixture()
                self.write_continuation(
                    root,
                    refs=refs,
                    phase=phase,
                    action=action,
                    target_ref=target,
                )
                self.assert_passes(root)

    def test_task0007_legacy_expanded_v3_continuation_remains_valid(self) -> None:
        _, root = self.fixture()
        self.write_continuation(
            root,
            legacy=True,
            phase="PROMOTION",
            action="PROMOTE_TO_MAIN",
        )
        self.assert_passes(root)

    def test_task0007_canonical_promotion_requires_exact_target_ref(self) -> None:
        _, root = self.fixture()
        self.write_continuation(
            root,
            refs=[("refs/heads/stable", "stable-sha")],
            phase="PROMOTION",
            action="PROMOTE_TARGET_REF",
            target_ref="refs/heads/other",
        )
        self.assert_rejected(root, "promotion_target_ref must identify a ref present in expected_refs")

        _, root = self.fixture()
        self.write_continuation(
            root,
            refs=[("refs/heads/stable", "stable-sha")],
            phase="PROMOTION",
            action="PROMOTE_TO_MAIN",
        )
        self.assert_rejected(root, "PROMOTE_TO_MAIN is legacy compatibility input")

    def test_task0007_lifecycle_snapshot_mismatch_is_rejected(self) -> None:
        _, root = self.fixture()
        self.write_continuation(
            root,
            legacy=True,
            phase="REVIEW",
            action="REQUEST_ARCHITECT_REVIEW",
            lifecycle="ACCEPTED",
            prior_lifecycle="VERIFIED",
        )
        self.assert_rejected(root, "expected_state.lifecycle must equal prior_lifecycle_state")

    def test_task0007_prior_result_is_not_forced_to_lifecycle(self) -> None:
        _, root = self.fixture()
        self.write_continuation(
            root,
            refs=[],
            phase="REVIEW",
            action="STOP",
            prior_result="NEEDS_REVIEW",
        )
        self.assert_passes(root)

    def test_task0007_phase_action_pairs_are_relational(self) -> None:
        _, root = self.fixture()
        self.write_continuation(
            root,
            legacy=True,
            phase="REVIEW",
            action="PUBLISH_RELEASE",
        )
        self.assert_rejected(root, "is not valid for continuation phase")

        valid_pairs = [
            ("REVIEW", "REQUEST_ARCHITECT_REVIEW"),
            ("REVIEW", "STOP"),
            ("VERIFICATION", "RUN_AUTHORITATIVE_VERIFICATION"),
            ("VERIFICATION", "STOP"),
            ("RELEASE", "CREATE_VERSION_TAG"),
            ("RELEASE", "MUTATE_REPOSITORY_METADATA"),
            ("RELEASE", "PUBLISH_RELEASE"),
            ("RELEASE", "FINAL_VERIFY"),
            ("RELEASE", "STOP"),
        ]
        for phase, action in valid_pairs:
            with self.subTest(phase=phase, action=action):
                _, root = self.fixture()
                self.write_continuation(
                    root,
                    legacy=True,
                    phase=phase,
                    action=action,
                )
                self.assert_passes(root)

    def test_task0007_review_acceptance_requires_exact_report_identity(self) -> None:
        _, root = self.fixture()
        path = root / "templates" / "review.yaml"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("state: REVISION_REQUIRED", "state: ACCEPTED", 1), encoding="utf-8")
        self.assert_rejected(root, "ACCEPTED review requires independence.exact_report_identity_verified=true")

        _, root = self.fixture()
        path = root / "templates" / "review.yaml"
        text = path.read_text(encoding="utf-8")
        text = text.replace(
            "\ncontract_compliance:\n",
            "\nindependence:\n"
            "  reviewer_role: ARCHITECT\n"
            "  separate_session_from_executor: true\n"
            "  exact_report_identity_verified: false\n"
            "\ncontract_compliance:\n",
            1,
        )
        text = text.replace("state: REVISION_REQUIRED", "state: ACCEPTED", 1)
        text = text.replace(
            "  exact_report_identity_verified: false",
            "  exact_report_identity_verified: true",
            1,
        )
        path.write_text(text, encoding="utf-8")
        self.assert_passes(root)

        for state in ("REVISION_REQUIRED", "BLOCKED"):
            with self.subTest(nonaccepted=state):
                _, root = self.fixture()
                path = root / "templates" / "review.yaml"
                text = path.read_text(encoding="utf-8")
                if state == "BLOCKED":
                    text = text.replace("state: REVISION_REQUIRED", "state: BLOCKED", 1)
                path.write_text(text, encoding="utf-8")
                self.assert_passes(root)

    def test_task0007_canonical_docs_expose_topology_neutral_terms(self) -> None:
        continuation = (ROOT / "templates" / "continuation.yaml").read_text(encoding="utf-8")
        protocol = (ROOT / "protocols" / "TASK_PROTOCOL.md").read_text(encoding="utf-8")
        combined = continuation + protocol
        for token in (
            "PROMOTE_TARGET_REF",
            "promotion_target_ref",
            "target-authoritative",
            "compatibility input",
        ):
            self.assertIn(token, combined)
        self.assertIn("  - ref: refs/heads/integration", continuation)
        self.assertNotIn("expected_refs:\n  dev:", continuation)
        self.assertNotIn("next_authorized_action: PROMOTE_TO_MAIN", continuation)


class Task0011GeneratedProgramTests(unittest.TestCase):
    def fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name) / "repo"
        shutil.copytree(ROOT, root)
        self.addCleanup(temp.cleanup)
        return temp, root

    def run_validator(self, root: Path) -> subprocess.CompletedProcess[str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        original_root = VALIDATOR_MODULE.ROOT
        try:
            VALIDATOR_MODULE.ROOT = root
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                returncode = VALIDATOR_MODULE.main()
        finally:
            VALIDATOR_MODULE.ROOT = original_root
        return subprocess.CompletedProcess(
            args=["python3", str(root / VALIDATOR)],
            returncode=returncode,
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue(),
        )

    def mutate_program(self, root: Path, mutate) -> None:
        path = root / "templates" / "program.generated.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        mutate(document)
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    def assert_program_rejected(self, mutate, expected: str) -> None:
        _, root = self.fixture()
        self.mutate_program(root, mutate)
        result = self.run_validator(root)
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        self.assertIn(expected, output)

    def test_task0011_canonical_generated_program_is_non_authoritative_and_valid(self) -> None:
        _, root = self.fixture()
        path = root / "templates" / "program.generated.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(document["protocol_version"], 3)
        self.assertEqual(document["artifact_type"], "GENERATED_PROGRAM")
        self.assertEqual(document["authority"], "NONE")
        self.assertEqual(document["invalidation"], "FULL_REGENERATION_ON_MATERIAL_INPUT_CHANGE")
        result = self.run_validator(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_task0011_generated_program_rejects_invalid_graph_coverage_and_authority_shape(self) -> None:
        def duplicate_id(document) -> None:
            document["items"].append(json.loads(json.dumps(document["items"][0])))

        def broken_dependency(document) -> None:
            document["items"][0]["depends_on"] = ["ITEM-999"]

        def cycle(document) -> None:
            second = json.loads(json.dumps(document["items"][0]))
            second["id"] = "ITEM-002"
            second["depends_on"] = ["ITEM-001"]
            document["items"][0]["depends_on"] = ["ITEM-002"]
            document["items"].append(second)

        def missing_source_revision(document) -> None:
            document["synthesis"]["target"].pop("source_revision")

        def malformed_evidence(document) -> None:
            document["items"][0]["required_evidence"] = "not-a-list"

        def mutable_state(document) -> None:
            document["items"][0]["status"] = "READY"

        def uncovered_ref(document) -> None:
            document["coverage"]["required_refs"].append("TARGET:design#uncovered")

        def authority_escalation(document) -> None:
            document["authority"] = "TASK"

        cases = [
            (duplicate_id, "duplicate generated item id"),
            (broken_dependency, "depends on unknown item"),
            (cycle, "dependency graph must be acyclic"),
            (missing_source_revision, "synthesis.target"),
            (malformed_evidence, "required_evidence"),
            (mutable_state, "unexpected fields ['status']"),
            (uncovered_ref, "neither covered nor excluded"),
            (authority_escalation, "path 'authority' must equal 'NONE'"),
        ]
        for mutate, expected in cases:
            with self.subTest(expected=expected):
                self.assert_program_rejected(mutate, expected)

    def test_task0011_bounded_coverage_exclusion_is_valid(self) -> None:
        _, root = self.fixture()

        def mutate(document) -> None:
            ref = "TARGET:design#excluded"
            document["coverage"]["required_refs"].append(ref)
            document["coverage"]["exclusions"].append({
                "ref": ref,
                "rationale": "Explicitly outside this generated implementation program slice.",
            })

        self.mutate_program(root, mutate)
        result = self.run_validator(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_task0011_doctrine_preserves_judgment_full_regeneration_and_jit_task_authority(self) -> None:
        protocol = (ROOT / "protocols" / "TASK_PROTOCOL.md").read_text(encoding="utf-8")
        architect = (ROOT / "architect" / "SKILL.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        combined = protocol + architect + readme
        for token in (
            "authority: NONE",
            "mathematically unique DAG",
            "whole generated program stale",
            "full regeneration",
            "just in time",
            "one active Executor binding",
        ):
            self.assertIn(token, combined)
        for forbidden in (
            "affected-region recomputation",
            "dependency cache",
            "planner service",
        ):
            self.assertIn(forbidden, protocol)


class Task0020GovernanceOwnershipTests(unittest.TestCase):
    def fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name) / "repo"
        shutil.copytree(ROOT, root)
        self.addCleanup(temp.cleanup)
        return temp, root

    def run_validator(self, root: Path) -> subprocess.CompletedProcess[str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        original_root = VALIDATOR_MODULE.ROOT
        try:
            VALIDATOR_MODULE.ROOT = root
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                returncode = VALIDATOR_MODULE.main()
        finally:
            VALIDATOR_MODULE.ROOT = original_root
        return subprocess.CompletedProcess(
            args=["python3", str(root / VALIDATOR)],
            returncode=returncode,
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue(),
        )

    def load_task(self, root: Path) -> dict[str, object]:
        original_root = VALIDATOR_MODULE.ROOT
        try:
            VALIDATOR_MODULE.ROOT = root
            document = VALIDATOR_MODULE.load_protocol_document("templates/task.yaml")
        finally:
            VALIDATOR_MODULE.ROOT = original_root
        assert document is not None
        return document

    def remove_sparse_optional_controls(self, root: Path) -> None:
        path = root / "templates" / "task.yaml"
        lines = path.read_text(encoding="utf-8").splitlines()
        output: list[str] = []
        skip_structure = False
        skip_control = False
        for line in lines:
            if line == "  expected_files_are_restrictive: true":
                continue
            if line == "structure_policy:":
                skip_structure = True
                continue
            if skip_structure and line == "continuation_policy:":
                skip_structure = False
            if skip_structure:
                continue
            if line in {"continuation_policy:", "capability_requirements:", "release_authority:"}:
                skip_control = True
                continue
            if skip_control and line and not line.startswith(" "):
                skip_control = False
            if skip_control:
                continue
            output.append(line)
        path.write_text("\n".join(output) + "\n", encoding="utf-8")

    def test_sparse_implementation_controls_normalize_to_bounded_local_defaults(self) -> None:
        _, root = self.fixture()
        self.remove_sparse_optional_controls(root)
        document = self.load_task(root)
        normalized = VALIDATOR_MODULE.normalize_task_document(document)

        scope = normalized["scope"]
        structure = normalized["structure_policy"]
        unlisted = structure["unlisted_new_files"]
        self.assertFalse(scope["expected_files_are_restrictive"])
        self.assertEqual(structure["expected_new_files"], [])
        self.assertTrue(unlisted["allowed"])
        self.assertEqual(unlisted["max"], -1)
        self.assertEqual(unlisted["within"], [])
        self.assertFalse(structure["allow_new_top_level_directories"])
        self.assertFalse(structure["allow_new_shared_modules"])
        self.assertEqual(normalized["continuation_policy"]["mode"], "MANUAL")
        self.assertEqual(normalized["capability_requirements"], {})
        self.assertEqual(
            normalized["release_authority"],
            {
                "create_version_tag": False,
                "mutate_repository_metadata": False,
                "publish_release": False,
            },
        )
        result = self.run_validator(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_expanded_v3_restrictions_remain_restrictive_after_normalization(self) -> None:
        _, root = self.fixture()
        legacy = root / ".agent" / "tasks" / "TASK-0001" / "task.yaml"
        self.assertTrue(legacy.is_file())
        (root / "templates" / "task.yaml").write_text(legacy.read_text(encoding="utf-8"), encoding="utf-8")
        document = self.load_task(root)
        normalized = VALIDATOR_MODULE.normalize_task_document(document)
        self.assertTrue(normalized["scope"]["expected_files_are_restrictive"])
        self.assertFalse(normalized["structure_policy"]["unlisted_new_files"]["allowed"])
        self.assertEqual(normalized["structure_policy"]["unlisted_new_files"]["max"], 0)
        result = self.run_validator(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_positive_authority_still_fails_closed(self) -> None:
        _, root = self.fixture()
        self.remove_sparse_optional_controls(root)
        path = root / "templates" / "task.yaml"
        text = path.read_text(encoding="utf-8")
        text = text.replace(
            "  allowed_existing_files_or_components:\n    - \"\"\n",
            "  allowed_existing_files_or_components_missing:\n    - \"\"\n",
            1,
        )
        path.write_text(text, encoding="utf-8")
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("missing required path 'scope.allowed_existing_files_or_components'", result.stdout + result.stderr)

    def test_template_serializes_sparse_v3_without_a_second_task_dialect(self) -> None:
        _, root = self.fixture()
        path = root / "templates" / "task.yaml"
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("task-lite", text)
        self.assertNotIn("task-compact", text)
        self.assertNotIn("protocol_version: 4", text)
        self.assertNotIn("  expected_files_are_restrictive:", text)
        self.assertNotIn("structure_policy:", text)
        result = self.run_validator(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class Task0021EvidenceLifecycleTests(unittest.TestCase):
    def fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name) / "repo"
        shutil.copytree(ROOT, root)
        self.addCleanup(temp.cleanup)
        return temp, root

    def run_validator(self, root: Path) -> subprocess.CompletedProcess[str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        original_root = VALIDATOR_MODULE.ROOT
        try:
            VALIDATOR_MODULE.ROOT = root
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                returncode = VALIDATOR_MODULE.main()
        finally:
            VALIDATOR_MODULE.ROOT = original_root
        return subprocess.CompletedProcess(
            args=["python3", str(root / VALIDATOR)],
            returncode=returncode,
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue(),
        )

    def remove_top_level_block(self, text: str, key: str) -> str:
        lines = text.splitlines(keepends=True)
        matches = [index for index, line in enumerate(lines) if line == f"{key}:\n"]
        if not matches:
            return text
        start = matches[0]
        end = start + 1
        while end < len(lines) and (not lines[end].strip() or lines[end][0].isspace()):
            end += 1
        return "".join(lines[:start] + lines[end:])

    def test_compact_report_can_omit_changed_file_enumeration(self) -> None:
        _, root = self.fixture()
        path = root / "templates" / "report.yaml"
        text = path.read_text(encoding="utf-8")
        path.write_text(self.remove_top_level_block(text, "changed_files"), encoding="utf-8")

        result = self.run_validator(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_default_report_template_omits_operational_timing(self) -> None:
        _, root = self.fixture()
        path = root / "templates" / "report.yaml"
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("operational_timing:", text)
        document = VALIDATOR_MODULE.load_protocol_document("templates/report.yaml")
        assert document is not None
        self.assertNotIn("operational_timing", document)

        result = self.run_validator(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_report_accepts_explicit_two_timestamp_timing(self) -> None:
        _, root = self.fixture()
        path = root / "templates" / "report.yaml"
        text = self.remove_top_level_block(path.read_text(encoding="utf-8"), "operational_timing")
        text += (
            "\noperational_timing:\n"
            '  started_at_utc: "2026-09-03T10:00:00Z"\n'
            '  terminal_decision_at_utc: "2026-09-03T10:05:00Z"\n'
        )
        path.write_text(text, encoding="utf-8")

        result = self.run_validator(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_report_rejects_partial_operational_timing(self) -> None:
        _, root = self.fixture()
        path = root / "templates" / "report.yaml"
        text = self.remove_top_level_block(path.read_text(encoding="utf-8"), "operational_timing")
        text += '\noperational_timing:\n  started_at_utc: "2026-09-03T10:00:00Z"\n'
        path.write_text(text, encoding="utf-8")

        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("operational_timing", result.stdout + result.stderr)

    def test_report_rejects_non_utc_or_derived_timing_fields(self) -> None:
        _, root = self.fixture()
        path = root / "templates" / "report.yaml"
        text = self.remove_top_level_block(path.read_text(encoding="utf-8"), "operational_timing")
        text += (
            "\noperational_timing:\n"
            '  started_at_utc: "2026-09-03T17:00:00+07:00"\n'
            '  terminal_decision_at_utc: "2026-09-03T10:05:00Z"\n'
            "  elapsed_seconds: 300\n"
        )
        path.write_text(text, encoding="utf-8")

        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("operational_timing", result.stdout + result.stderr)

    def test_review_rejects_partial_operational_timing(self) -> None:
        _, root = self.fixture()
        path = root / "templates" / "review.yaml"
        text = path.read_text(encoding="utf-8")
        text += '\noperational_timing:\n  started_at_utc: "2026-09-03T10:00:00Z"\n'
        path.write_text(text, encoding="utf-8")

        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("operational_timing", result.stdout + result.stderr)

    def test_review_accepts_explicit_two_timestamp_timing(self) -> None:
        _, root = self.fixture()
        path = root / "templates" / "review.yaml"
        text = path.read_text(encoding="utf-8")
        text += (
            "\noperational_timing:\n"
            '  started_at_utc: "2026-09-03T10:00:00Z"\n'
            '  terminal_decision_at_utc: "2026-09-03T10:05:00Z"\n'
        )
        path.write_text(text, encoding="utf-8")

        result = self.run_validator(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_review_procedure_is_evidence_first_and_trigger_expanded(self) -> None:
        combined = (
            (ROOT / "architect" / "SKILL.md").read_text(encoding="utf-8")
            + (ROOT / "contracts" / "ARCHITECT_REVIEW.md").read_text(encoding="utf-8")
            + (ROOT / "protocols" / "TASK_PROTOCOL.md").read_text(encoding="utf-8")
        )
        for token in (
            "evidence-first",
            "exact report/task identity",
            "candidate diff boundary",
            "acceptance evidence",
            "deviations/gaps",
            "material risk triggers",
            "stop when material predicates are proven",
            "Deep implementation reconstruction occurs only for",
            "preference-only revision",
            "material consequence or contract/risk violation",
            "omitted by default",
            "explicitly requests",
        ):
            self.assertIn(token, combined)


EVAL_CORPUS = Path("scripts/fixtures/governance_eval_corpus.json")
EVAL_CASE_FIELDS = frozenset({
    "case_id",
    "pair_id",
    "scenario",
    "evaluation_kind",
    "expected_outcome",
    "rationale",
})
EVAL_KINDS = frozenset({"over_governance", "under_governance"})
EVAL_OUTCOMES = frozenset({"ALLOW_LOCAL", "ESCALATE_TO_ARCHITECT"})
EVAL_PAIR_MIN = 6
EVAL_PAIR_MAX = 8
TARGET_RULE_LEAKAGE = re.compile(r"\b(?:ielts|sf|salesforce)\b", re.IGNORECASE)


def eval_corpus_errors(document: object) -> list[str]:
    errors: list[str] = []
    if type(document) is not dict:
        return ["corpus must be an object"]
    if set(document) != {"cases"}:
        errors.append("corpus must contain only the cases field")
    cases = document.get("cases")
    if type(cases) is not list:
        return errors + ["cases must be a list"]

    case_ids: set[str] = set()
    pairs: dict[str, list[dict[str, object]]] = {}
    for index, case in enumerate(cases):
        label = f"cases[{index}]"
        if type(case) is not dict:
            errors.append(f"{label} must be an object")
            continue
        missing = sorted(EVAL_CASE_FIELDS - set(case))
        unexpected = sorted(set(case) - EVAL_CASE_FIELDS)
        if missing:
            errors.append(f"{label} missing fields {missing}")
        if unexpected:
            errors.append(f"{label} has unexpected fields {unexpected}")
        if missing or unexpected:
            continue
        for field in EVAL_CASE_FIELDS:
            value = case[field]
            if type(value) is not str or not value.strip():
                errors.append(f"{label}.{field} must be a non-empty string")
        case_id = case["case_id"]
        pair_id = case["pair_id"]
        kind = case["evaluation_kind"]
        outcome = case["expected_outcome"]
        if type(case_id) is str:
            if case_id in case_ids:
                errors.append(f"duplicate case_id {case_id!r}")
            case_ids.add(case_id)
        if type(pair_id) is str:
            pairs.setdefault(pair_id, []).append(case)
        if type(kind) is str and kind not in EVAL_KINDS:
            errors.append(f"{label}.evaluation_kind has unsupported value {kind!r}")
        if type(outcome) is str and outcome not in EVAL_OUTCOMES:
            errors.append(f"{label}.expected_outcome has unsupported value {outcome!r}")

    pair_count = len(pairs)
    if not EVAL_PAIR_MIN <= pair_count <= EVAL_PAIR_MAX:
        errors.append(f"pair count must be between {EVAL_PAIR_MIN} and {EVAL_PAIR_MAX}")
    for pair_id, pair_cases in pairs.items():
        if len(pair_cases) != 2:
            errors.append(f"pair {pair_id!r} must contain exactly two cases")
            continue
        kinds = {case["evaluation_kind"] for case in pair_cases}
        if kinds != EVAL_KINDS:
            errors.append(f"pair {pair_id!r} must contain one case of each evaluation kind")

    serialized = json.dumps(document, ensure_ascii=False)
    leaked = sorted({match.group(0).lower() for match in TARGET_RULE_LEAKAGE.finditer(serialized)})
    if leaked:
        errors.append(f"target-specific rule leakage: {leaked}")
    return errors


class Task0022GovernanceEvaluationTests(unittest.TestCase):
    def load_corpus(self, root: Path = ROOT) -> object:
        path = root / EVAL_CORPUS
        self.assertTrue(path.is_file(), f"missing evaluation corpus: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def assert_corpus_rejected(self, mutate, expected: str) -> None:
        document = json.loads(json.dumps(self.load_corpus()))
        mutate(document)
        errors = eval_corpus_errors(document)
        self.assertTrue(any(expected in error for error in errors), errors)

    def test_canonical_corpus_is_small_generic_and_integrity_valid(self) -> None:
        document = self.load_corpus()
        errors = eval_corpus_errors(document)
        self.assertEqual(errors, [])
        assert isinstance(document, dict)
        cases = document["cases"]
        assert isinstance(cases, list)
        self.assertEqual(len(cases), len({case["case_id"] for case in cases}))
        self.assertEqual({case["evaluation_kind"] for case in cases}, EVAL_KINDS)
        self.assertEqual({case["expected_outcome"] for case in cases}, EVAL_OUTCOMES)

    def test_integrity_rejects_duplicate_case_ids(self) -> None:
        self.assert_corpus_rejected(
            lambda document: document["cases"].__setitem__(1, document["cases"][0]),
            "duplicate case_id",
        )

    def test_integrity_rejects_incomplete_pairs(self) -> None:
        self.assert_corpus_rejected(
            lambda document: document["cases"].pop(),
            "must contain exactly two cases",
        )

    def test_integrity_rejects_unsupported_kind_and_outcome(self) -> None:
        def mutate(document: dict[str, object]) -> None:
            case = document["cases"][0]
            case["evaluation_kind"] = "materiality_classifier"
            case["expected_outcome"] = "PRESCRIBE_WORDING"

        self.assert_corpus_rejected(mutate, "unsupported value")

    def test_integrity_rejects_missing_required_fields(self) -> None:
        def mutate(document: dict[str, object]) -> None:
            document["cases"][0].pop("rationale")

        self.assert_corpus_rejected(mutate, "missing fields")

    def test_integrity_rejects_malformed_required_fields(self) -> None:
        def mutate(document: dict[str, object]) -> None:
            document["cases"][0]["scenario"] = "   "

        self.assert_corpus_rejected(mutate, "must be a non-empty string")

    def test_integrity_rejects_pair_count_drift(self) -> None:
        def mutate(document: dict[str, object]) -> None:
            document["cases"].extend(
                [
                    {
                        **document["cases"][0],
                        "case_id": "extra-local",
                        "pair_id": "extra-pair",
                        "evaluation_kind": "over_governance",
                    },
                    {
                        **document["cases"][1],
                        "case_id": "extra-material",
                        "pair_id": "extra-pair",
                        "evaluation_kind": "under_governance",
                    },
                    {
                        **document["cases"][0],
                        "case_id": "overflow-local",
                        "pair_id": "overflow-pair",
                        "evaluation_kind": "over_governance",
                    },
                    {
                        **document["cases"][1],
                        "case_id": "overflow-material",
                        "pair_id": "overflow-pair",
                        "evaluation_kind": "under_governance",
                    },
                ]
            )

        self.assert_corpus_rejected(mutate, "pair count")

    def test_integrity_rejects_target_specific_rule_leakage(self) -> None:
        def mutate(document: dict[str, object]) -> None:
            document["cases"][0]["scenario"] = "Use IELTS-specific product semantics."

        self.assert_corpus_rejected(mutate, "target-specific rule leakage")


class Task0024GitHubFirstLocalExecutionTests(unittest.TestCase):
    def test_executor_closes_designated_canonical_local_execution_generically(self) -> None:
        executor = (ROOT / "executor" / "SKILL.md").read_text(encoding="utf-8")
        normalized = executor.lower()
        for token in (
            "designated canonical local working copy",
            "exact owner/repo remote identity",
            "do not infer",
            "absent or safely empty",
            "clean/behind",
            "dirty/ahead/unknown",
            "identity mismatch",
            "stale remote",
            "Before local mutation",
            "After GitHub publication",
            "refresh canonical GitHub truth",
            "fast-forward/equivalent",
            "final canonical ref",
            "Temporary/reference/disposable checkouts",
            "cannot substitute",
            "phone-only or remote-only",
            "fail closed",
        ):
            self.assertIn(token.lower(), normalized)

        for forbidden in (
            "workspace registry",
            "repo registry",
            "sync engine",
            "state database",
            "/Users/tienphat",
            "Codex-specific command",
        ):
            self.assertNotIn(forbidden, executor)


class Task0025StableAdoptionGateTests(unittest.TestCase):
    def fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name) / "repo"
        shutil.copytree(ROOT, root)
        self.addCleanup(temp.cleanup)
        return temp, root

    def load_document(self, root: Path, relative: str) -> dict[str, object]:
        original_root = VALIDATOR_MODULE.ROOT
        try:
            VALIDATOR_MODULE.ROOT = root
            document = VALIDATOR_MODULE.load_protocol_document(relative)
        finally:
            VALIDATOR_MODULE.ROOT = original_root
        assert document is not None
        return document

    def run_validator(self, root: Path) -> subprocess.CompletedProcess[str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        original_root = VALIDATOR_MODULE.ROOT
        try:
            VALIDATOR_MODULE.ROOT = root
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                returncode = VALIDATOR_MODULE.main()
        finally:
            VALIDATOR_MODULE.ROOT = original_root
        return subprocess.CompletedProcess(
            args=["python3", str(root / VALIDATOR)],
            returncode=returncode,
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue(),
        )

    def copy_task(self, root: Path, relative: str) -> Path:
        target = root / "templates" / "task.yaml"
        target.write_text((root / relative).read_text(encoding="utf-8"), encoding="utf-8")
        return target

    def remove_optional_task_controls(self, path: Path) -> None:
        lines = path.read_text(encoding="utf-8").splitlines()
        optional_keys = {
            "structure_policy:",
            "continuation_policy:",
            "capability_requirements:",
            "release_authority:",
        }
        output: list[str] = []
        skipping = False
        for line in lines:
            if skipping:
                if line and not line.startswith(" "):
                    skipping = False
                else:
                    continue
            if line in optional_keys:
                skipping = True
                continue
            if line == "  expected_files_are_restrictive: true":
                continue
            output.append(line)
        path.write_text("\n".join(output) + "\n", encoding="utf-8")

    def test_expanded_and_sparse_v3_use_one_normalized_semantic_model(self) -> None:
        _, root = self.fixture()

        sparse_path = self.copy_task(root, ".agent/tasks/TASK-0001/task.yaml")
        self.remove_optional_task_controls(sparse_path)
        sparse = self.load_document(root, "templates/task.yaml")
        normalized_sparse = VALIDATOR_MODULE.normalize_task_document(sparse)
        for key in ("structure_policy", "continuation_policy", "capability_requirements", "release_authority"):
            self.assertEqual(
                normalized_sparse[key],
                VALIDATOR_MODULE.TASK_NORMALIZATION_DEFAULTS[key],
            )
        self.assertFalse(normalized_sparse["scope"]["expected_files_are_restrictive"])
        sparse_result = self.run_validator(root)
        self.assertEqual(sparse_result.returncode, 0, sparse_result.stdout + sparse_result.stderr)

        self.copy_task(root, ".agent/tasks/TASK-0001/task.yaml")
        expanded = self.load_document(root, "templates/task.yaml")
        normalized_expanded = VALIDATOR_MODULE.normalize_task_document(expanded)
        self.assertTrue(normalized_expanded["scope"]["expected_files_are_restrictive"])
        self.assertFalse(normalized_expanded["structure_policy"]["unlisted_new_files"]["allowed"])
        self.assertEqual(normalized_expanded["structure_policy"]["unlisted_new_files"]["max"], 0)
        expanded_result = self.run_validator(root)
        self.assertEqual(expanded_result.returncode, 0, expanded_result.stdout + expanded_result.stderr)

    def test_missing_authority_fails_closed_but_missing_how_preserves_discretion(self) -> None:
        _, authority_root = self.fixture()
        authority_path = self.copy_task(authority_root, ".agent/tasks/TASK-0001/task.yaml")
        authority_text = authority_path.read_text(encoding="utf-8")
        authority_text = authority_text.replace(
            "  allowed_existing_files_or_components:\n",
            "  allowed_existing_files_or_components_missing:\n",
            1,
        )
        authority_path.write_text(authority_text, encoding="utf-8")
        authority_result = self.run_validator(authority_root)
        authority_output = authority_result.stdout + authority_result.stderr
        self.assertNotEqual(authority_result.returncode, 0, authority_output)
        self.assertIn("missing required path 'scope.allowed_existing_files_or_components'", authority_output)

        _, sparse_root = self.fixture()
        sparse_path = self.copy_task(sparse_root, ".agent/tasks/TASK-0001/task.yaml")
        self.remove_optional_task_controls(sparse_path)
        sparse_result = self.run_validator(sparse_root)
        self.assertEqual(sparse_result.returncode, 0, sparse_result.stdout + sparse_result.stderr)
        normalized = self.load_document(sparse_root, "templates/task.yaml")
        normalized = VALIDATOR_MODULE.normalize_task_document(normalized)
        self.assertEqual(normalized["structure_policy"], VALIDATOR_MODULE.TASK_NORMALIZATION_DEFAULTS["structure_policy"])

        executor = (ROOT / "executor" / "SKILL.md").read_text(encoding="utf-8").lower()
        contract = (ROOT / "contracts" / "IMPLEMENTATION_CONTRACT.md").read_text(encoding="utf-8").lower()
        self.assertIn("implementation judgment belongs to executor by default", executor)
        self.assertIn("missing exact-file or local-structure prescription defaults to bounded executor discretion", contract)
        self.assertIn("missing authority fields never default to permission", contract)

    def test_materiality_scope_structure_gap_and_report_ownership_remain_closed(self) -> None:
        paths = (
            "protocols/TASK_PROTOCOL.md",
            "contracts/IMPLEMENTATION_CONTRACT.md",
            "contracts/IMPLEMENTATION_REPORT.md",
            "contracts/ARCHITECT_REVIEW.md",
            "architect/SKILL.md",
            "executor/SKILL.md",
        )
        combined = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in paths).lower()
        for phrase in (
            "trust, ownership, compatibility, durability, irreversibility, dependency, cost/topology, or architecture",
            "implementing an already-frozen api, security, data, migration, dependency, or structure decision",
            "public/shared contract",
            "prescribe local how only when the mechanism itself carries a material governing consequence",
            "executor discretion never expands authority or changes a material consequence",
            "scope owns semantic/component consequence by default",
            "structure is local when it consists of internal files or modules",
            "new or changed top-level ownership",
            "`local` is necessary for current acceptance criteria",
            "`follow_up` and `blocking` are consequence-based",
            "preference-only revision is not warranted",
            "reject local how only for material consequence or contract/risk violation",
            "executor owns report content. architect may review it but does not rewrite it.",
            "missing authority fields never default to permission",
        ):
            self.assertIn(phrase, combined)

    def git(self, cwd: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout.strip()

    def is_ancestor(self, cwd: Path, ancestor: str, descendant: str) -> bool:
        return subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=cwd,
            text=True,
            capture_output=True,
        ).returncode == 0

    def test_git_state_facts_distinguish_safe_fast_forward_from_local_authority_risks(self) -> None:
        """A future gate must not mistake Git facts for permission to reconcile."""
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)
            absent = fixture / "absent"
            self.assertFalse((absent / ".git").exists())

            empty = fixture / "empty"
            empty.mkdir()
            self.git(empty, "init", "--initial-branch=main")
            self.assertEqual(self.git(empty, "remote"), "")
            self.assertEqual(self.git(empty, "status", "--porcelain"), "")

            remote = fixture / "canonical.git"
            self.git(fixture, "init", "--bare", "--initial-branch=main", str(remote))
            seed = fixture / "seed"
            self.git(fixture, "clone", remote.as_uri(), str(seed))
            self.git(seed, "config", "user.name", "Regression")
            self.git(seed, "config", "user.email", "regression@example.invalid")
            (seed / "authority.txt").write_text("base\n", encoding="utf-8")
            self.git(seed, "add", "authority.txt")
            self.git(seed, "commit", "-m", "base")
            self.git(seed, "push", "origin", "main")

            local = fixture / "local"
            writer = fixture / "writer"
            temporary = fixture / "temporary"
            self.git(fixture, "clone", remote.as_uri(), str(local))
            self.git(fixture, "clone", remote.as_uri(), str(writer))
            self.git(fixture, "clone", remote.as_uri(), str(temporary))
            self.git(writer, "config", "user.name", "Regression")
            self.git(writer, "config", "user.email", "regression@example.invalid")
            self.assertEqual(self.git(local, "remote", "get-url", "origin"), remote.as_uri())
            self.assertEqual(self.git(temporary, "remote", "get-url", "origin"), remote.as_uri())
            self.assertNotEqual(local.resolve(), temporary.resolve())

            (writer / "authority.txt").write_text("remote-one\n", encoding="utf-8")
            self.git(writer, "add", "authority.txt")
            self.git(writer, "commit", "-m", "remote one")
            self.git(writer, "push", "origin", "main")
            cached_before_fetch = self.git(local, "rev-parse", "refs/remotes/origin/main")
            advertised_before_fetch = self.git(local, "ls-remote", "origin", "refs/heads/main").split()[0]
            self.assertNotEqual(cached_before_fetch, advertised_before_fetch)

            self.git(local, "fetch", "origin", "main")
            self.assertEqual(self.git(local, "rev-parse", "refs/remotes/origin/main"), advertised_before_fetch)
            self.assertEqual(self.git(local, "status", "--porcelain"), "")
            self.assertTrue(self.is_ancestor(local, "HEAD", "origin/main"))
            self.git(local, "merge", "--ff-only", "origin/main")
            self.assertEqual(self.git(local, "rev-parse", "HEAD"), advertised_before_fetch)

            (writer / "authority.txt").write_text("remote-two\n", encoding="utf-8")
            self.git(writer, "add", "authority.txt")
            self.git(writer, "commit", "-m", "remote two")
            self.git(writer, "push", "origin", "main")
            self.git(local, "fetch", "origin", "main")
            (local / "operator-owned.txt").write_text("retain\n", encoding="utf-8")
            self.assertIn("?? operator-owned.txt", self.git(local, "status", "--porcelain"))
            self.assertTrue(self.is_ancestor(local, "HEAD", "origin/main"))

            self.git(local, "config", "user.name", "Regression")
            self.git(local, "config", "user.email", "regression@example.invalid")
            (local / "local-only.txt").write_text("ahead\n", encoding="utf-8")
            self.git(local, "add", "local-only.txt")
            self.git(local, "commit", "-m", "local only")
            self.assertFalse(self.is_ancestor(local, "HEAD", "origin/main"))
            self.assertFalse(self.is_ancestor(local, "origin/main", "HEAD"))

            other = fixture / "other.git"
            self.git(fixture, "init", "--bare", "--initial-branch=main", str(other))
            self.git(local, "remote", "set-url", "origin", other.as_uri())
            self.assertNotEqual(self.git(local, "remote", "get-url", "origin"), remote.as_uri())

    def test_governance_corpus_pairs_preserve_hand_checked_consequence_outcomes(self) -> None:
        document = json.loads((ROOT / EVAL_CORPUS).read_text(encoding="utf-8"))
        self.assertEqual(eval_corpus_errors(document), [])
        cases = {case["case_id"]: case for case in document["cases"]}
        expected = {
            "route-contract": ("route-local", "route-public-contract"),
            "persistence-semantics": ("sql-mechanical", "persistence-semantics"),
            "ownership-boundary": ("module-local", "shared-ownership"),
            "dependency-topology": ("approved-dependency", "new-dependency"),
            "generated-contract": ("generated-local", "generated-public"),
            "auth-trust": ("frozen-auth", "trust-boundary"),
            "local-how": ("preference-how", "material-how"),
            "companion-ownership": ("local-companion", "cross-component-move"),
        }
        self.assertEqual(set(case["pair_id"] for case in cases.values()), set(expected))
        for pair_id, (local_case_id, material_case_id) in expected.items():
            with self.subTest(pair_id=pair_id):
                local_case = cases[local_case_id]
                material_case = cases[material_case_id]
                self.assertEqual(local_case["pair_id"], pair_id)
                self.assertEqual(local_case["evaluation_kind"], "over_governance")
                self.assertEqual(local_case["expected_outcome"], "ALLOW_LOCAL")
                self.assertEqual(material_case["pair_id"], pair_id)
                self.assertEqual(material_case["evaluation_kind"], "under_governance")
                self.assertEqual(material_case["expected_outcome"], "ESCALATE_TO_ARCHITECT")

    def test_historical_replay_and_fresh_pilots_keep_exact_accepted_identities(self) -> None:
        replay = (ROOT / ".agent" / "tasks" / "TASK-0023" / "replay.md").read_text(encoding="utf-8")
        for phrase in (
            "Revision 3 disappears.",
            "Revision 4 disappears.",
            "Revision 5 disappears as a task revision",
            "No verifier/stale/new-truth deletion claim",
            "public/trust/data/integrity consequences",
            "The historical evidence supports the accepted redesign without weakening material governance",
        ):
            self.assertIn(phrase, replay)

        task = (ROOT / ".agent" / "tasks" / "TASK-0025" / "task.yaml").read_text(encoding="utf-8")
        for identity in (
            ".agent/tasks/TASK-0024/review.yaml@16217bb78a578160efb68afc84acdeff9c36ed38",
            "phatnguyen03022001/ilets TASK-0045 accepted review@4b88bbde9558ae50de2c17941677c73fe7c504c8",
            "phatnguyen03022001/SF TASK-0008 accepted review@dd518fa0ae693f57befcedf341410d4cf28026d8",
            "phatnguyen03022001/architect-profile TASK-0015 accepted review@71921cde6228c21b4d2e3e6509e685d82981dc9c",
        ):
            self.assertIn(identity, task)

    def test_existing_validate_workflow_covers_live_validation_inputs_only(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "validate-skill-library.yml").read_text(encoding="utf-8")
        self.assertIn("branches:\n      - dev", workflow)
        path_block = workflow.split("    paths:\n", 1)[1].split("\n\npermissions:", 1)[0]
        paths = [line.strip()[2:].strip('"') for line in path_block.splitlines() if line.strip().startswith("- ")]
        self.assertEqual(
            paths,
            [
                "README.md",
                "**/SKILL.md",
                "contracts/**",
                "templates/**",
                "protocols/**",
                ".agent/case-router.yaml",
                "scripts/**",
                ".github/workflows/validate-skill-library.yml",
            ],
        )
        self.assertNotIn(".agent/tasks/**", paths)
        self.assertIn("python3 scripts/validate_skill_library.py", workflow)
        self.assertIn("python3 -m unittest scripts/test_validate_skill_library.py", workflow)
        self.assertIn("python3 -m unittest scripts.test_reconcile_env", workflow)

    def test_operator_preferences_stay_outside_generic_agent_skills(self) -> None:
        generic_paths = (
            "README.md",
            "protocols/TASK_PROTOCOL.md",
            "architect/SKILL.md",
            "executor/SKILL.md",
            "contracts/FOUNDATION_ARCHITECTURE.md",
        )
        generic = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in generic_paths)
        self.assertNotIn("/Users/tienphat", generic)
        self.assertNotIn("Developer/<repo-name>", generic)
        generic = generic.lower()
        self.assertIn("does not prescribe task launch field names", generic)
        self.assertIn("agent runtime remains an optional capability surface", generic)
        self.assertIn("mobile/chatgpt+github-only operation is first-class", generic)


class Task0029SparseSerializationTests(unittest.TestCase):
    def fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name) / "repo"
        shutil.copytree(ROOT, root)
        self.addCleanup(temp.cleanup)
        return temp, root

    def load_document(self, root: Path, relative: str) -> dict[str, object]:
        original_root = VALIDATOR_MODULE.ROOT
        try:
            VALIDATOR_MODULE.ROOT = root
            document = VALIDATOR_MODULE.load_protocol_document(relative)
        finally:
            VALIDATOR_MODULE.ROOT = original_root
        assert document is not None
        return document

    def validation_errors(self, root: Path, validator_name: str) -> list[str]:
        original_root = VALIDATOR_MODULE.ROOT
        try:
            VALIDATOR_MODULE.ROOT = root
            VALIDATOR_MODULE.errors.clear()
            getattr(VALIDATOR_MODULE, validator_name)()
            return list(VALIDATOR_MODULE.errors)
        finally:
            VALIDATOR_MODULE.errors.clear()
            VALIDATOR_MODULE.ROOT = original_root

    def remove_top_level(self, path: Path, keys: set[str]) -> None:
        lines = path.read_text(encoding="utf-8").splitlines()
        output: list[str] = []
        skipping = False
        for line in lines:
            if skipping:
                if line and not line.startswith((" ", "#")):
                    skipping = False
                else:
                    continue
            key = line.split(":", 1)[0] if line and not line.startswith((" ", "#")) else None
            if key in keys:
                skipping = True
                continue
            output.append(line)
        path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")

    def make_sparse_task(self, root: Path) -> Path:
        path = root / "templates" / "task.yaml"
        self.remove_top_level(path, {"continuation_policy", "capability_requirements", "release_authority"})
        return path

    def make_sparse_report(self, root: Path) -> Path:
        path = root / "templates" / "report.yaml"
        self.remove_top_level(
            path,
            {
                "execution_skills_used",
                "pre_execution_checks",
                "local_hygiene",
                "commits_created",
                "discovered_gaps",
                "structural_observations",
                "deviations_from_task",
                "blockers",
                "working_tree_after",
                "promoted_to_main",
            },
        )
        text = path.read_text(encoding="utf-8")
        text = text.replace('  pre_execution_head: ""\n', "", 1)
        text = text.replace('  observed_revision: ""\n', "", 1)
        path.write_text(text, encoding="utf-8")
        return path

    def make_sparse_review(self, root: Path) -> Path:
        path = root / "templates" / "review.yaml"
        self.remove_top_level(path, {"independence", "gap_disposition", "follow_up_tasks", "promotion_readiness", "notes"})
        return path

    def test_sparse_and_explicit_default_task_controls_normalize_equivalently(self) -> None:
        _, root = self.fixture()
        self.make_sparse_task(root)
        sparse = self.load_document(root, "templates/task.yaml")
        expanded = deepcopy(sparse)
        expanded_scope = expanded.setdefault("scope", {})
        assert isinstance(expanded_scope, dict)
        expanded_scope["expected_files_are_restrictive"] = False
        for key in ("structure_policy", "continuation_policy", "capability_requirements", "release_authority"):
            expanded[key] = deepcopy(VALIDATOR_MODULE.TASK_NORMALIZATION_DEFAULTS[key])

        self.assertEqual(
            VALIDATOR_MODULE.normalize_task_document(sparse),
            VALIDATOR_MODULE.normalize_task_document(expanded),
        )
        self.assertEqual(self.validation_errors(root, "validate_task_template"), [])

    def test_sparse_and_expanded_report_shapes_preserve_material_evidence(self) -> None:
        _, expanded_root = self.fixture()
        expanded_path = expanded_root / "templates" / "report.yaml"
        expanded_text = expanded_path.read_text(encoding="utf-8")
        expanded_path.write_text(
            expanded_text.replace(
                "\nresult: NEEDS_REVIEW\n",
                '\nexecutor_checks:\n  - check_id: CHECK-1\n    result: NOT_PROVEN\n    evidence: ""\n\nresult: NEEDS_REVIEW\n',
                1,
            ),
            encoding="utf-8",
        )
        expanded = self.load_document(expanded_root, "templates/report.yaml")
        self.assertEqual(self.validation_errors(expanded_root, "validate_report_template"), [])

        _, sparse_root = self.fixture()
        self.make_sparse_report(sparse_root)
        sparse = self.load_document(sparse_root, "templates/report.yaml")
        self.assertEqual(self.validation_errors(sparse_root, "validate_report_template"), [])

        for dotted in (
            "task_id",
            "task_revision",
            "report_revision",
            "state",
            "task_source.path",
            "execution.repository",
            "execution.branch.name",
            "execution.branch.role",
            "execution.authorized_base_head",
            "execution.final_execution_head",
            "skill_library.authorized_revision",
            "pushed",
            "acceptance_evidence",
            "result",
        ):
            self.assertEqual(
                VALIDATOR_MODULE.get_path(expanded, dotted),
                VALIDATOR_MODULE.get_path(sparse, dotted),
                dotted,
            )
        self.assertNotIn("executor_checks", sparse)
        self.assertIn("executor_checks", expanded)

    def test_sparse_and_expanded_review_shapes_preserve_durable_binding_and_judgment(self) -> None:
        _, expanded_root = self.fixture()
        expanded = self.load_document(expanded_root, "templates/review.yaml")
        self.assertEqual(self.validation_errors(expanded_root, "validate_review_template"), [])

        _, sparse_root = self.fixture()
        self.make_sparse_review(sparse_root)
        sparse = self.load_document(sparse_root, "templates/review.yaml")
        self.assertEqual(self.validation_errors(sparse_root, "validate_review_template"), [])

        for dotted in (
            "task_id",
            "task_revision",
            "review_revision",
            "state",
            "reviewed_report.repository",
            "reviewed_report.path",
            "reviewed_report.commit",
            "reviewed_report.report_revision",
            "contract_compliance.protocol_version",
            "contract_compliance.identity",
            "contract_compliance.execution_base",
            "contract_compliance.skill_rules",
            "contract_compliance.scope",
            "contract_compliance.structure_policy",
            "contract_compliance.git_authority",
            "contract_compliance.acceptance_criteria",
            "contract_compliance.verifier_evidence",
        ):
            self.assertEqual(
                VALIDATOR_MODULE.get_path(expanded, dotted),
                VALIDATOR_MODULE.get_path(sparse, dotted),
                dotted,
            )

    def test_sparse_report_still_rejects_missing_material_evidence(self) -> None:
        mutations = (
            ('  final_execution_head: ""', '  final_execution_head_missing: ""', "execution.final_execution_head"),
            ("acceptance_evidence:", "acceptance_evidence_missing:", "acceptance_evidence"),
            ("result: NEEDS_REVIEW", "result_missing: NEEDS_REVIEW", "result"),
        )
        for old, new, missing_path in mutations:
            with self.subTest(missing_path=missing_path):
                _, root = self.fixture()
                path = self.make_sparse_report(root)
                text = path.read_text(encoding="utf-8")
                self.assertIn(old, text)
                path.write_text(text.replace(old, new, 1), encoding="utf-8")
                errors = self.validation_errors(root, "validate_report_template")
                self.assertTrue(any(f"missing required path '{missing_path}'" in item for item in errors), errors)

    def test_distinct_executor_checks_are_optional_but_validated_when_present(self) -> None:
        _, root = self.fixture()
        task = self.load_document(root, "templates/task.yaml")
        report = self.load_document(root, "templates/report.yaml")
        self.assertNotIn("executor_checks", task["verification"])
        self.assertNotIn("executor_checks", report)
        self.assertEqual(self.validation_errors(root, "validate_task_template"), [])
        self.assertEqual(self.validation_errors(root, "validate_report_template"), [])

        path = root / "templates" / "report.yaml"
        text = path.read_text(encoding="utf-8")
        text = text.replace(
            "\nresult: NEEDS_REVIEW\n",
            '\nexecutor_checks:\n  - check_id: CHECK-1\n    result: NOT_PROVEN\n    evidence: ""\n\nresult: NEEDS_REVIEW\n',
            1,
        )
        path.write_text(text.replace("check_id: CHECK-1", "wrong_key: CHECK-1", 1), encoding="utf-8")
        errors = self.validation_errors(root, "validate_report_template")
        self.assertTrue(any("executor_checks[0]" in item and "check_id" in item for item in errors), errors)

    def test_sparse_review_still_rejects_missing_exact_report_identity(self) -> None:
        _, root = self.fixture()
        path = self.make_sparse_review(root)
        text = path.read_text(encoding="utf-8")
        old = '  commit: "<exact commit containing reviewed report>"'
        self.assertIn(old, text)
        path.write_text(text.replace(old, '  commit_missing: ""', 1), encoding="utf-8")
        errors = self.validation_errors(root, "validate_review_template")
        self.assertTrue(any("missing required path 'reviewed_report.commit'" in item for item in errors), errors)

    def test_role_and_contract_guidance_defaults_to_material_sparse_authoring(self) -> None:
        architect = (ROOT / "architect" / "SKILL.md").read_text(encoding="utf-8").lower()
        executor = (ROOT / "executor" / "SKILL.md").read_text(encoding="utf-8").lower()
        task_contract = (ROOT / "contracts" / "IMPLEMENTATION_CONTRACT.md").read_text(encoding="utf-8").lower()
        report_contract = (ROOT / "contracts" / "IMPLEMENTATION_REPORT.md").read_text(encoding="utf-8").lower()
        review_contract = (ROOT / "contracts" / "ARCHITECT_REVIEW.md").read_text(encoding="utf-8").lower()

        self.assertIn("material identity, what, boundary, proof, and only non-default controls", architect)
        self.assertIn("omit controls that equal the protocol-v3 defaults", task_contract)
        self.assertIn("omit reconstructible execution transcript", executor)
        self.assertIn("expanded-v3 report fields remain valid compatibility input", report_contract)
        self.assertIn("exact reviewed-report identity, material compliance, and final judgment", review_contract)
        self.assertIn("expanded-v3 review fields remain valid compatibility input", review_contract)


class Task0030ControlPlaneAccelerationTests(unittest.TestCase):
    def test_evidence_validity_classes_and_consequence_invalidation_are_explicit(self) -> None:
        protocol = (ROOT / "protocols" / "TASK_PROTOCOL.md").read_text(encoding="utf-8")
        for evidence_class in ("IMMUTABLE", "LOCAL_MUTABLE", "REMOTE_MUTABLE", "RUNTIME"):
            self.assertIn(f"`{evidence_class}`", protocol)
        for mutation_kind in (
            "observation mutation",
            "authorized target-ref mutation",
            "canonical publication mutation",
        ):
            self.assertIn(mutation_kind, protocol.lower())
        self.assertIn("consequence boundary", protocol.lower())
        self.assertIn("creates no persistent cache", protocol.lower())

    def test_execution_bundle_is_bounded_and_parallel_only_when_all_safety_predicates_hold(self) -> None:
        executor = (ROOT / "executor" / "SKILL.md").read_text(encoding="utf-8").lower()
        verification = (ROOT / "verification" / "SKILL.md").read_text(encoding="utf-8").lower()
        combined = "\n".join((executor, verification))
        self.assertIn("execution bundle", combined)
        for predicate in (
            "no shared mutable state",
            "no ordering dependency",
            "no conflicting externally rate-limited dependency",
            "no material resource contention",
            "independently attributable",
        ):
            self.assertIn(predicate, combined)
        self.assertIn("otherwise serialize", combined)
        self.assertIn("one bounded", combined)
        self.assertIn("compact", combined)
        self.assertIn("join", combined)

    def test_mandatory_full_suite_subsumes_focused_happy_path(self) -> None:
        verification = (ROOT / "verification" / "SKILL.md").read_text(encoding="utf-8").lower()
        self.assertIn("mandatory full suite", verification)
        self.assertIn("subsumes", verification)
        self.assertIn("happy path", verification)
        self.assertIn("diagnostic after failure", verification)
        self.assertIn("distinct acceptance authority", verification)

    def test_report_publication_closure_has_explicit_owners_without_self_reference(self) -> None:
        protocol = (ROOT / "protocols" / "TASK_PROTOCOL.md").read_text(encoding="utf-8").lower()
        report = (ROOT / "contracts" / "IMPLEMENTATION_REPORT.md").read_text(encoding="utf-8").lower()
        review = (ROOT / "contracts" / "ARCHITECT_REVIEW.md").read_text(encoding="utf-8").lower()
        combined = "\n".join((protocol, report, review))
        self.assertIn("same-commit post-publication", combined)
        self.assertIn("fresh remote publication proof", combined)
        self.assertIn("after push", combined)
        self.assertIn("review boundary", combined)
        self.assertIn("local mirror", combined)
        self.assertIn("local_mutable", combined)
        self.assertIn("not canonical remote authority", combined)


class Task0049ExecutorFitDecompositionTests(unittest.TestCase):
    def executor_fit_section(self) -> str:
        architect = (ROOT / "architect" / "SKILL.md").read_text(encoding="utf-8")
        heading = "## Executor-fit task-decomposition gate"
        self.assertIn(heading, architect)
        section = architect.split(heading, 1)[1].split("\n## ", 1)[0].lower()
        return section

    def test_executor_fit_gate_defines_exact_architect_local_outcomes(self) -> None:
        section = self.executor_fit_section()
        self.assertIn("before authorizing a normal canonical task", section)
        for outcome in ("`fit`", "`split_required`", "`capability_blocked`"):
            self.assertIn(outcome, section)
        self.assertIn("architect-local planning judgments", section)
        self.assertIn("not serialized task fields or lifecycle states", section)

    def test_fit_requires_one_coherent_review_and_evidence_boundary(self) -> None:
        section = self.executor_fit_section()
        for requirement in (
            "one coherent material outcome",
            "one repository/base binding",
            "one independently reviewable candidate boundary",
            "one coherent acceptance/evidence boundary",
            "required current-phase capabilities are currently satisfiable",
            "no sibling material outcome",
            "independently rejected",
        ):
            self.assertIn(requirement, section)

    def test_split_required_targets_independent_outcomes_not_implementation_ceremony(self) -> None:
        section = self.executor_fit_section()
        self.assertIn("materially independent sibling outcomes", section)
        self.assertIn("independently rejectable review/acceptance boundaries", section)
        self.assertIn("split those outcomes before canonical task authorization", section)
        for ceremony in ("multiple files", "steps", "components", "tests", "deterministic jobs"):
            self.assertIn(ceremony, section)
        self.assertIn("do not by themselves require splitting", section)

    def test_capability_blocked_does_not_add_scoring_schema_or_control_plane(self) -> None:
        section = self.executor_fit_section()
        self.assertIn("required current-phase capability cannot presently be satisfied", section)
        self.assertIn("capability blocking, not task splitting, scheduling, or provider orchestration", section)
        for prohibition in (
            "no complexity score",
            "token budget",
            "duration estimate",
            "task points",
            "queue",
            "scheduler",
            "planner service",
            "new schema",
            "task field",
            "lifecycle state",
            "additional organizational role",
        ):
            self.assertIn(prohibition, section)


class Task0052ExecutorProcessOwnershipBoundaryTests(unittest.TestCase):
    def executor_doctrine(self) -> str:
        return (
            (ROOT / "executor" / "SKILL.md").read_text(encoding="utf-8")
            + "\n"
            + (ROOT / "executor" / "references" / "ENGINEERING_HOW.md").read_text(encoding="utf-8")
        ).lower()

    def test_scenario_a_exact_task_owned_pid_pgid_cleanup_may_be_allowed(self) -> None:
        executor = self.executor_doctrine()
        for marker in (
            "ownership by the current authorized task/run is positively established",
            "current task authority permits that cleanup",
            "children, descendants, test servers",
            "explicitly task-owned local services/containers",
            "pid/pgid",
        ):
            self.assertIn(marker, executor)

    def test_scenario_b_unknown_port_occupant_must_not_be_signaled(self) -> None:
        executor = self.executor_doctrine()
        for marker in (
            "unknown ownership fails closed",
            "unknown process occupying a needed port",
            "must not be signaled",
            "process-name, tree, pid/pgid, port, service, container",
            "matching or apparent relevance is not ownership proof",
        ):
            self.assertIn(marker, executor)

    def test_scenario_c_ordinary_target_work_excludes_shared_execution_substrate(self) -> None:
        executor = self.executor_doctrine()
        for marker in (
            "agent runtime",
            "secure tunnel",
            "execution transport/controller ancestors",
            "shared operator execution infrastructure",
            "not task-owned merely because they carry, support, block, or appear related",
            "ordinary target-task authority",
            "does not authorize signaling, stopping, restarting, or reconfiguring",
        ):
            self.assertIn(marker, executor)

    def test_scenario_d_separate_runtime_maintenance_authority_remains_possible(self) -> None:
        executor = self.executor_doctrine()
        for marker in (
            "separately authorized infrastructure-maintenance task",
            "resolve its own exact authority",
            "bounded agent runtime/tunnel lifecycle action",
            "not an absolute never-terminate-runtime rule",
        ):
            self.assertIn(marker, executor)


class Task0053ExecutorRepositoryConstructionTests(unittest.TestCase):
    def executor_doctrine(self) -> str:
        return (
            (ROOT / "executor" / "SKILL.md").read_text(encoding="utf-8")
            + "\n"
            + (ROOT / "executor" / "references" / "ENGINEERING_HOW.md").read_text(encoding="utf-8")
        ).lower()

    def test_scenario_a_greenfield_resolves_current_official_scaffold_before_manual_baseline(self) -> None:
        executor = self.executor_doctrine()
        for marker in (
            "greenfield",
            "fresh-resolve",
            "current official",
            "scaffold/generator",
            "before manually recreating equivalent boilerplate",
        ):
            self.assertIn(marker, executor)

    def test_scenario_b_existing_repository_uses_pinned_native_toolchain_before_ambient_latest(self) -> None:
        executor = self.executor_doctrine()
        for marker in (
            "existing repository",
            "git state",
            "manifests",
            "lockfiles",
            "package-manager",
            "runtime pins",
            "scripts",
            "framework configuration",
            "generator/codegen configuration",
            ".gitignore",
            "repository-native verification",
            "take precedence over remembered, globally installed, or merely latest external tooling",
        ):
            self.assertIn(marker, executor)

    def test_scenario_c_generated_baseline_and_gitignore_scope_conflict_fail_closed(self) -> None:
        executor = self.executor_doctrine()
        for marker in (
            "inspect the generated diff before pruning or reshaping",
            "required companion files",
            ".gitignore",
            "official framework defaults",
            "generated source, migrations, or codegen output are not automatically ignored",
            "restrictive task",
            "blocking",
            "silent omission",
            "manual reconstruction",
        ):
            self.assertIn(marker, executor)

    def test_scenario_d_locked_dependency_hydration_is_not_dependency_redesign(self) -> None:
        executor = self.executor_doctrine()
        for marker in (
            "dependency hydration",
            "already-declared",
            "pinned/locked dependency contract",
            "authorized repository execution or verification",
            "not, by itself, dependency redesign",
            "intentionally adds/removes/changes dependencies",
            "unexpectedly rewrites the contract",
            "stop and classify the gap",
        ):
            self.assertIn(marker, executor)

    def test_scenario_e_one_shot_tooling_prefers_ephemeral_over_persistent_global_install(self) -> None:
        executor = self.executor_doctrine()
        for marker in (
            "least-persistent sufficient",
            "repo_local",
            "ephemeral",
            "global",
            "containerized",
            "one-shot",
            "persistence is unnecessary",
        ):
            self.assertIn(marker, executor)

    def test_scenario_f_machine_global_mutation_requires_separate_operator_authority(self) -> None:
        executor = self.executor_doctrine()
        for marker in (
            "homebrew",
            "global npm/pnpm installs",
            "persistent uv tool installs",
            "persistent go installs",
            "path or shell-profile changes",
            "runtime-manager changes",
            "docker-engine changes",
            "persistent service mutation",
            "agent runtime or tunnel lifecycle mutation",
            "separate machine/operator authority",
        ):
            self.assertIn(marker, executor)

    def test_scenario_g_existing_native_framework_and_mature_oss_precede_custom_rebuild(self) -> None:
        executor = self.executor_doctrine()
        for marker in (
            "target-repository implementation",
            "exact-pinned ecc generic harness",
            "ecc:search-first",
            "material ecc gap",
            "fast model-generated code is not itself justification for a custom replacement",
        ):
            self.assertIn(marker, executor)


class Task0054PlatformCompliantExecutionPublicationTests(unittest.TestCase):
    def doctrine(self, *paths: str) -> str:
        owned_paths = ("contracts/FOUNDATION_ARCHITECTURE.md",) + paths
        return "\n".join((ROOT / path).read_text(encoding="utf-8").lower() for path in owned_paths)

    def test_scenario_a_semantic_capability_routing_outranks_nonmaterial_provider_handoff(self) -> None:
        combined = self.doctrine("protocols/TASK_PROTOCOL.md", "executor/SKILL.md")
        for marker in (
            "required semantic capability",
            "current authority",
            "authorized available surface",
            "provider-specific handoff wording",
            "materially requires that surface identity",
        ):
            self.assertIn(marker, combined)

    def test_scenario_b_narrow_typed_consequence_is_preferred_only_when_equivalent(self) -> None:
        combined = self.doctrine("protocols/TASK_PROTOCOL.md", "executor/SKILL.md")
        for marker in (
            "narrowest explicit bounded action",
            "machine-checkable",
            "typed does not mean automatically safe",
            "equivalent evidence",
        ):
            self.assertIn(marker, combined)

    def test_scenario_c_generic_terminal_remains_legal_authorized_fallback(self) -> None:
        combined = self.doctrine("protocols/TASK_PROTOCOL.md", "executor/SKILL.md")
        for marker in (
            "generic terminal remains a valid fallback",
            "no sufficient narrower surface",
            "platform-permitted",
        ):
            self.assertIn(marker, combined)

    def test_scenario_d_platform_safety_block_fails_closed_without_evasion(self) -> None:
        combined = self.doctrine("protocols/TASK_PROTOCOL.md", "executor/SKILL.md")
        for marker in (
            "platform/tool safety block",
            "obfuscation",
            "encoding intent",
            "command splitting",
            "permission widening",
            "unchanged retry",
        ):
            self.assertIn(marker, combined)

    def test_scenario_e_surface_change_never_lowers_proof_quality(self) -> None:
        combined = self.doctrine("protocols/TASK_PROTOCOL.md", "executor/SKILL.md")
        for marker in (
            "platform compliance changes how",
            "never what must be proven",
            "acceptance criteria",
            "verifier requirements",
            "exact commit/content identity",
            "remote freshness",
            "evidence quality",
        ):
            self.assertIn(marker, combined)

    def test_scenario_f_immutable_publication_handoff_transfers_publication_not_editing(self) -> None:
        combined = self.doctrine("protocols/TASK_PROTOCOL.md", "executor/SKILL.md")
        for marker in (
            "immutable publication handoff",
            "prior writer is terminal",
            "publication authority transfer",
            "publish only",
            "may not edit",
            "recreate",
            "amend",
        ):
            self.assertIn(marker, combined)

    def test_scenario_g_exact_commit_and_content_identity_publication_are_distinct(self) -> None:
        protocol = self.doctrine("protocols/TASK_PROTOCOL.md")
        for marker in (
            "exact-commit publication",
            "content-identity publication",
            "different commit identity",
            "explicitly permits",
        ):
            self.assertIn(marker, protocol)

    def test_scenario_h_operator_fallback_is_explicit_last_resort_consequence(self) -> None:
        combined = self.doctrine("protocols/TASK_PROTOCOL.md", "executor/SKILL.md")
        for marker in (
            "operator fallback",
            "last-resort consequence",
            "automation is materially unavailable",
            "user-only/approval-bound",
            "preconditions",
            "post-publication remote proof",
        ):
            self.assertIn(marker, combined)

    def test_protocol_v3_single_publication_closure_preserves_candidate_report_identity(self) -> None:
        combined = self.doctrine(
            "protocols/TASK_PROTOCOL.md",
            "contracts/IMPLEMENTATION_REPORT.md",
            "executor/SKILL.md",
        )
        for marker in (
            "single-publication",
            "exact remote target ref still equals the authorized execution base",
            "immutable and fully verified",
            "report-only sole direct child",
            "one ordinary non-force cas",
            "fresh remote",
            "final_execution_head",
        ):
            self.assertIn(marker, combined)

    def test_protocol_v3_remote_candidate_dependencies_require_two_publications(self) -> None:
        combined = self.doctrine("protocols/TASK_PROTOCOL.md", "executor/SKILL.md")
        for marker in (
            "two-publication",
            "ci/external verifier",
            "cross-checkout",
            "promotion prerequisite",
            "explicit",
            "candidate publication",
        ):
            self.assertIn(marker, combined)

    def test_report_pushed_false_is_truthful_candidate_prepublication_state(self) -> None:
        template = (ROOT / "templates/report.yaml").read_text(encoding="utf-8")
        self.assertIn("\npushed: false\n", template)
        contract = self.doctrine("contracts/IMPLEMENTATION_REPORT.md", "executor/SKILL.md")
        for marker in (
            "pushed: false",
            "candidate-prepublication state",
            "not remotely visible before report authorship",
            "never predicts",
        ):
            self.assertIn(marker, contract)

    def test_single_publication_unknown_effect_requires_reconciliation_before_retry(self) -> None:
        combined = self.doctrine("protocols/TASK_PROTOCOL.md", "executor/SKILL.md")
        for marker in (
            "failed or ambiguous",
            "fresh remote reconciliation",
            "never blind retry",
            "outcome_unknown",
        ):
            self.assertIn(marker, combined)

    def test_scenario_i_report_and_review_publication_are_externally_proven(self) -> None:
        combined = self.doctrine(
            "protocols/TASK_PROTOCOL.md",
            "contracts/IMPLEMENTATION_REPORT.md",
            "contracts/ARCHITECT_REVIEW.md",
            "architect/SKILL.md",
        )
        for marker in (
            "same-commit post-publication",
            "externally proven",
            "typed repository-write action",
            "current_phase_capability_unavailable",
        ):
            self.assertIn(marker, combined)


class ActualArtifactCliTests(unittest.TestCase):
    def run_artifact_validator(self, kind: str, path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / VALIDATOR), "--artifact", kind, str(path)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def copy_external_artifact(self, relative_path: str) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / Path(relative_path).name
        path.write_text((ROOT / relative_path).read_text(encoding="utf-8"), encoding="utf-8")
        return temp, path

    def replace_follow_up_tasks(self, path: Path, replacement: str) -> None:
        text = path.read_text(encoding="utf-8")
        start = text.index("follow_up_tasks:\n")
        end = text.index("\n\nnotes:", start)
        path.write_text(text[:start] + replacement + text[end:], encoding="utf-8")

    def test_exact_task0050_legacy_follow_up_strings_are_compatible(self) -> None:
        path = ROOT / ".agent/tasks/TASK-0050/review.yaml"
        before = path.read_bytes()
        result = self.run_artifact_validator("review", path)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(path.read_bytes(), before)

    def test_exact_task0023_structured_follow_up_tasks_remain_compatible(self) -> None:
        path = ROOT / ".agent/tasks/TASK-0023/review.yaml"
        before = path.read_bytes()
        result = self.run_artifact_validator("review", path)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(path.read_bytes(), before)

    def test_follow_up_tasks_mixed_and_empty_string_forms_are_rejected(self) -> None:
        for replacement, expected in (
            (
                "follow_up_tasks:\n"
                '  - "legacy follow-up"\n'
                "  - task_id: TASK-0001\n"
                "    origin:\n"
                "      type: discovered_gap\n"
                "      task_id: TASK-0001\n"
                "      gap_id: GAP-001",
                "path 'follow_up_tasks[0]' must be mapping",
            ),
            (
                "follow_up_tasks:\n"
                '  - ""',
                "follow_up_tasks[0]' must be non-empty string",
            ),
        ):
            with self.subTest(expected=expected):
                _, path = self.copy_external_artifact(".agent/tasks/TASK-0050/review.yaml")
                before = path.read_bytes()
                self.replace_follow_up_tasks(path, replacement)
                result = self.run_artifact_validator("review", path)
                output = result.stdout + result.stderr
                self.assertEqual(result.returncode, 1, output)
                self.assertIn(expected, output)
                self.assertNotEqual(path.read_bytes(), before)

    def test_exact_task0014_unsupported_review_yaml_remains_inconclusive(self) -> None:
        path = ROOT / ".agent/tasks/TASK-0014/review.yaml"
        before = path.read_bytes()
        result = self.run_artifact_validator("review", path)
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 3, output)
        self.assertIn("UNSUPPORTED_SERIALIZATION", output)
        self.assertIn("validity not mechanically determined", output.lower())
        self.assertEqual(path.read_bytes(), before)

    def test_task0009_missing_review_is_reported_without_backfill(self) -> None:
        path = ROOT / ".agent/tasks/TASK-0009/review.yaml"
        self.assertFalse(path.exists())
        result = self.run_artifact_validator("review", path)
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 1, output)
        self.assertIn("file does not exist", output)
        self.assertFalse(path.exists())

    def test_artifact_cli_distinguishes_unsupported_serialization_from_protocol_invalidity(self) -> None:
        historical = ROOT / ".agent/tasks/TASK-0013/task.yaml"
        before = historical.read_bytes()
        unsupported = self.run_artifact_validator("task", historical)
        unsupported_output = unsupported.stdout + unsupported.stderr
        self.assertEqual(unsupported.returncode, 3, unsupported_output)
        self.assertIn("UNSUPPORTED_SERIALIZATION", unsupported_output)
        self.assertIn("validity not mechanically determined", unsupported_output.lower())
        self.assertNotIn("PROTOCOL_INVALID", unsupported_output)
        self.assertEqual(historical.read_bytes(), before)

        _, valid_path = self.copy_external_artifact("templates/task.yaml")
        valid = self.run_artifact_validator("task", valid_path)
        self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)

        _, invalid_path = self.copy_external_artifact("templates/task.yaml")
        text = invalid_path.read_text(encoding="utf-8")
        self.assertIn("protocol_version: 3", text)
        invalid_path.write_text(text.replace("protocol_version: 3", "protocol_version: 4", 1), encoding="utf-8")
        invalid = self.run_artifact_validator("task", invalid_path)
        invalid_output = invalid.stdout + invalid.stderr
        self.assertEqual(invalid.returncode, 1, invalid_output)
        self.assertNotIn("UNSUPPORTED_SERIALIZATION", invalid_output)

    def test_protocol_docs_separate_semantic_validity_from_validator_serialization_support(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
        protocol = (ROOT / "protocols/TASK_PROTOCOL.md").read_text(encoding="utf-8").lower()
        combined = readme + "\n" + protocol
        self.assertIn("semantic validity", combined)
        self.assertIn("serialization support", combined)
        self.assertIn("valid historical", combined)
        self.assertIn("need not be parseable", combined)

    def test_external_task_report_and_review_are_validated_read_only(self) -> None:
        for kind, relative_path in (
            ("task", "templates/task.yaml"),
            ("report", ".agent/tasks/TASK-0042/report.yaml"),
            ("review", "templates/review.yaml"),
        ):
            with self.subTest(kind=kind):
                _, path = self.copy_external_artifact(relative_path)
                before = path.read_bytes()
                result = self.run_artifact_validator(kind, path)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(path.read_bytes(), before)

    def test_actual_report_hygiene_failures_have_field_diagnostics(self) -> None:
        cases = (
            (
                "incomplete",
                "local_hygiene:\n  result: PASS\n",
                "path 'local_hygiene' missing required fields",
            ),
            (
                "retained-scalar",
                "local_hygiene:\n  result: RETAINED_FOR_EVIDENCE\n  run_root: /private/tmp/run\n"
                "  cleanup_performed: false\n  retained: [/private/tmp/evidence]\n  evidence: retained\n",
                "path 'local_hygiene.retained[0]' must be mapping",
            ),
            (
                "retained-path-not-identity",
                "local_hygiene:\n  result: RETAINED_FOR_EVIDENCE\n  run_root: /private/tmp/run\n"
                "  cleanup_performed: false\n  retained:\n    - path: /private/tmp/evidence\n"
                "      reason: retained\n  evidence: retained\n",
                "path 'local_hygiene.retained[0]' missing required fields ['identity']",
            ),
        )
        for name, hygiene, diagnostic in cases:
            with self.subTest(name=name):
                _, path = self.copy_external_artifact("templates/report.yaml")
                path.write_text(path.read_text(encoding="utf-8") + "\n" + hygiene, encoding="utf-8")
                result = self.run_artifact_validator("report", path)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(diagnostic, result.stdout + result.stderr)

    def test_flat_flow_lists_accept_bare_and_quoted_scalars(self) -> None:
        VALIDATOR_MODULE.errors.clear()
        canonical = VALIDATOR_MODULE.load_protocol_path(ROOT / ".agent/tasks/TASK-0042/task.yaml")
        self.assertIsNotNone(canonical, VALIDATOR_MODULE.errors)
        assert canonical is not None
        self.assertEqual(
            canonical["execution_skills"]["required"],
            ["executor", "verification", "simplicity", "github-workflow"],
        )

        cases = (
            "  required: [executor]",
            '  required: ["executor"]',
        )
        for replacement in cases:
            with self.subTest(replacement=replacement):
                _, path = self.copy_external_artifact("templates/task.yaml")
                text = path.read_text(encoding="utf-8")
                required = "  required:\n    - executor"
                self.assertIn(required, text)
                path.write_text(text.replace(required, replacement, 1), encoding="utf-8")
                result = self.run_artifact_validator("task", path)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        self.assertEqual(
            VALIDATOR_MODULE.parse_flat_flow_list('["[executor]"]', ROOT / "templates/task.yaml", 1),
            ["[executor]"],
        )

    def test_flat_flow_lists_reject_unsupported_or_malformed_syntax(self) -> None:
        invalid_values = (
            "[!tag executor]",
            "[&anchor executor]",
            "[*anchor]",
            "[executor,]",
            "[[executor]]",
            "[executor: value]",
        )
        for value in invalid_values:
            with self.subTest(value=value):
                _, path = self.copy_external_artifact("templates/task.yaml")
                text = path.read_text(encoding="utf-8")
                required = "  required:\n    - executor"
                path.write_text(text.replace(required, f"  required: {value}", 1), encoding="utf-8")
                result = self.run_artifact_validator("task", path)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("flow list", result.stdout + result.stderr)



class Task0016TargetRepositoryAuthorityTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_canonical_target_ownership_and_filename_neutral_precedence(self) -> None:
        architecture = self.read("contracts/FOUNDATION_ARCHITECTURE.md")
        protocol = self.read("protocols/TASK_PROTOCOL.md")
        combined = architecture + "\n" + protocol
        for marker in (
            "## Target repository product authority",
            "canonical owner of product truth and repository-native engineering contracts",
            "product architecture and domain behavior",
            "toolchain and dependency contracts",
            "build, test, lint, typecheck, format, and codegen",
            "runtime and deployment configuration",
            "authority class rather than filename",
            "AGENTS.md",
            "CLAUDE.md",
            "absence of a conventional instruction filename is not a blocker",
            "`task.yaml` owns the authorized WHAT/BOUNDARY/PROOF for one task",
            "does not replace the target repository's enduring product",
        ):
            self.assertIn(marker, combined)

    def test_roles_resolve_repo_native_truth_before_generic_how(self) -> None:
        combined = "\n".join(
            self.read(path)
            for path in (
                "contracts/FOUNDATION_ARCHITECTURE.md",
                "architect/SKILL.md",
                "executor/SKILL.md",
                "executor/references/ENGINEERING_HOW.md",
            )
        )
        for marker in (
            "bounded target-truth discovery",
            "Repository-owned commands and verifier profiles remain primary",
            "ECC examples are advisory patterns",
            "adapt to target-native commands and architecture",
            "execution transport only",
            "does not become the owner of target commands",
            "contradictory or missing product truth",
        ):
            self.assertIn(marker, combined)

    def test_contract_rejects_universal_manifest_and_platform_defaults(self) -> None:
        architecture = self.read("contracts/FOUNDATION_ARCHITECTURE.md")
        engineering = self.read("executor/references/ENGINEERING_HOW.md")
        combined = architecture + "\n" + engineering
        for marker in (
            "no universal target manifest",
            "no single package manager, language, framework",
            "no fixed build, test, lint, typecheck, or codegen command shape",
            "equivalent repository-native evidence",
        ):
            self.assertIn(marker, combined)


class Task0018ProductArchitectureBoundaryTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_target_product_architecture_is_distinct_and_filename_neutral(self) -> None:
        product = self.read("contracts/AGENT_FOUNDATION_PRODUCT_ARCHITECTURE.md")
        foundation = self.read("contracts/FOUNDATION_ARCHITECTURE.md")
        readme = self.read("README.md")
        for marker in (
            "canonical target-owned T1 product-architecture boundary",
            "distinct from [Foundation Architecture](FOUNDATION_ARCHITECTURE.md)",
            "features/",
            "shared/",
            "platform/",
            "app/",
            "They are not required physical directories",
            "does not invent fake business features",
            "profile/",
            "skills/",
            "documents/",
            "standards/",
        ):
            self.assertIn(marker, product)
        self.assertIn("AGENT_FOUNDATION_PRODUCT_ARCHITECTURE.md", foundation)
        self.assertIn("AGENT_FOUNDATION_PRODUCT_ARCHITECTURE.md", readme)

    def test_shared_platform_composition_and_private_dependency_boundaries(self) -> None:
        product = self.read("contracts/AGENT_FOUNDATION_PRODUCT_ARCHITECTURE.md")
        for marker in (
            "at least two independent product capabilities",
            "no capability-specific product semantics",
            "stable reusable contract",
            "Two files inside one capability are not two independent consumers",
            "must not own product or governance behavior",
            "Product/governance behavior must not accumulate in the composition root",
            "private internals is rejected by doctrine",
            "explicit public contract",
            "application interface",
            "event",
            "explicit orchestration boundary",
        ):
            self.assertIn(marker, product)

    def test_cross_cutting_and_telemetry_ownership_stays_separated(self) -> None:
        product = self.read("contracts/AGENT_FOUNDATION_PRODUCT_ARCHITECTURE.md")
        for marker in (
            "## Cross-cutting ownership",
            "Security",
            "Reliability",
            "Testing",
            "Configuration",
            "Delivery / operations",
            "Product-capability semantic events",
            "Shared instrumentation mechanics",
            "Platform observability infrastructure",
            "never becomes the owner of capability event meaning",
        ):
            self.assertIn(marker, product)

    def test_extraction_requires_evidence_and_t1_does_not_preimplement_later_state(self) -> None:
        product = self.read("contracts/AGENT_FOUNDATION_PRODUCT_ARCHITECTURE.md")
        for marker in (
            "independent scaling",
            "independent failure isolation",
            "independent deployment",
            "distinct security boundary",
            "distinct storage requirements",
            "distinct latency profile",
            "distinct organizational ownership",
            "The default remains a modular monolith",
            "release scope or a feature registry",
            "feature lifecycle, gates, or feature-state derivation",
            "global gates or project-phase derivation",
            "Architect progression integration",
            "execution or UI recovery redesign",
            "future task artifacts",
        ):
            self.assertIn(marker, product)


class Task0019ProductStateTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def load_state(self) -> dict:
        return json.loads((ROOT.parent / "product-state.json").read_text(encoding="utf-8"))

    def validate_state(self, document: dict) -> list[str]:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "product-state.json"
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        VALIDATOR_MODULE.errors.clear()
        VALIDATOR_MODULE.validate_agent_foundation_product_state(path, evidence_root=ROOT.parent)
        messages = list(VALIDATOR_MODULE.errors)
        VALIDATOR_MODULE.errors.clear()
        return messages

    def test_canonical_t2_contract_and_product_state_are_distinct_owners(self) -> None:
        contract = self.read("contracts/AGENT_FOUNDATION_PRODUCT_STATE.md")
        architecture = self.read("contracts/AGENT_FOUNDATION_PRODUCT_ARCHITECTURE.md")
        foundation = self.read("contracts/FOUNDATION_ARCHITECTURE.md")
        for marker in (
            "canonical target-owned T2 product-state contract",
            "product-state.json",
            "Product scope and release scope are separate",
            "PROGRAM remains derived planning data with authority `NONE`",
            "task lifecycle cannot manufacture product state",
            "not a universal Foundation manifest",
        ):
            self.assertIn(marker, contract)
        self.assertIn("canonical target-owned T1 product-architecture boundary", architecture)
        self.assertIn("single canonical generic owner", foundation)

    def test_current_product_state_is_exact_frozen_four_feature_inventory(self) -> None:
        state = self.load_state()
        self.assertEqual(self.validate_state(state), [])
        self.assertEqual(state["schema_version"], 3)
        self.assertEqual(state["target"]["repository"], "phatnguyen03022001/agent-foundation")
        scope = state["product_scope"]
        self.assertEqual(scope["revision"], 1)
        self.assertEqual(scope["scope_status"], "FROZEN")
        self.assertEqual(scope["features"]["total"], 4)
        self.assertEqual(
            [
                {key: feature[key] for key in ("id", "semantic_name", "owner")}
                for feature in scope["features"]["registered"]
            ],
            [
                {"id": "F001", "semantic_name": "operator-and-architect-configuration", "owner": "profile/"},
                {"id": "F002", "semantic_name": "governance-control-and-capability", "owner": "skills/"},
                {"id": "F003", "semantic_name": "documentation-model-and-closure", "owner": "documents/"},
                {"id": "F004", "semantic_name": "engineering-assurance", "owner": "standards/"},
            ],
        )

    def test_revision_one_rejects_count_duplicate_identity_name_and_owner_drift(self) -> None:
        cases = []
        state = self.load_state()
        changed = deepcopy(state)
        changed["product_scope"]["features"]["total"] = 3
        cases.append(changed)
        changed = deepcopy(state)
        changed["product_scope"]["features"]["registered"][1]["id"] = "F001"
        cases.append(changed)
        changed = deepcopy(state)
        changed["product_scope"]["features"]["registered"][1]["semantic_name"] = "operator-and-architect-configuration"
        cases.append(changed)
        changed = deepcopy(state)
        changed["product_scope"]["features"]["registered"][2]["owner"] = "skills/"
        cases.append(changed)
        changed = deepcopy(state)
        changed["product_scope"]["features"]["registered"].pop()
        cases.append(changed)
        for changed in cases:
            with self.subTest(changed=changed):
                self.assertTrue(self.validate_state(changed))

    def test_release_scope_is_open_and_unresolved_not_empty_or_invented(self) -> None:
        state = self.load_state()
        self.assertEqual(
            state["release"],
            {
                "status": "OPEN",
                "id": None,
                "id_resolution": "UNKNOWN",
                "required_feature_ids": None,
                "required_feature_ids_resolution": "UNKNOWN",
            },
        )
        mutations = (
            ("id", "R1"),
            ("id", "v1"),
            ("id_resolution", "KNOWN"),
            ("required_feature_ids", []),
            ("required_feature_ids", ["F001", "F002", "F003", "F004"]),
            ("required_feature_ids_resolution", "KNOWN"),
            ("status", "FROZEN"),
        )
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                changed = deepcopy(state)
                changed["release"][key] = value
                self.assertTrue(self.validate_state(changed))

    def test_feature_lifecycle_and_gate_fields_are_rejected(self) -> None:
        state = self.load_state()
        for key in ("state", "lifecycle_state", "gates", "gate_applicability", "verification_state"):
            with self.subTest(key=key):
                changed = deepcopy(state)
                changed["product_scope"]["features"]["registered"][0][key] = "FORBIDDEN"
                self.assertTrue(self.validate_state(changed))
        for key in ("global_gates", "project_phase", "completion_percentage", "release_readiness", "earliest_blocker"):
            with self.subTest(key=key):
                changed = deepcopy(state)
                changed[key] = "FORBIDDEN"
                self.assertTrue(self.validate_state(changed))

    def test_task_execution_chat_program_and_diary_fields_are_rejected(self) -> None:
        state = self.load_state()
        forbidden = (
            "task_refs",
            "report_refs",
            "review_refs",
            "execution_attempts",
            "process_ids",
            "raw_tool_output",
            "terminal_logs",
            "prompts",
            "chat_ids",
            "model_ids",
            "todos",
            "implementation_diary",
            "program",
        )
        for key in forbidden:
            with self.subTest(key=key):
                changed = deepcopy(state)
                changed[key] = []
                self.assertTrue(self.validate_state(changed))

    def test_unknown_fields_and_malformed_unresolved_representation_are_rejected(self) -> None:
        state = self.load_state()
        changed = deepcopy(state)
        changed["target"]["extra"] = True
        self.assertTrue(self.validate_state(changed))
        changed = deepcopy(state)
        changed["release"].pop("required_feature_ids_resolution")
        self.assertTrue(self.validate_state(changed))
        changed = deepcopy(state)
        changed["release"]["required_feature_ids"] = {}
        self.assertTrue(self.validate_state(changed))


class Task0021GlobalProgressionTests(unittest.TestCase):
    def load_state(self) -> dict:
        return json.loads((ROOT.parent / "product-state.json").read_text(encoding="utf-8"))

    def validate_state(self, document: dict) -> list[str]:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "product-state.json"
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        VALIDATOR_MODULE.errors.clear()
        VALIDATOR_MODULE.validate_agent_foundation_product_state(path, evidence_root=ROOT.parent)
        messages = list(VALIDATOR_MODULE.errors)
        VALIDATOR_MODULE.errors.clear()
        return messages

    def leaf(self, state: dict, group: str, name: str) -> dict:
        return next(leaf for leaf in state["system_gates"][group]["leaves"] if leaf["name"] == name)

    def set_system_leaf(
        self,
        state: dict,
        group: str,
        name: str,
        status: str,
        *,
        reason: str | None = None,
    ) -> None:
        leaf = self.leaf(state, group, name)
        leaf["status"] = status
        leaf["evidence_refs"] = (
            ["skills/contracts/AGENT_FOUNDATION_PRODUCT_ARCHITECTURE.md"]
            if status in {"PASS", "FAIL"}
            else []
        )
        leaf["reason"] = None if status == "PASS" else (reason or f"{name} is {status}.")
        key = "acceptance_status" if group == "production" else "status"
        state["system_gates"][group][key] = VALIDATOR_MODULE._derive_agent_foundation_group_status(state, group)

    def set_feature_prefix(self, state: dict, feature_id: str, pass_count: int) -> None:
        feature = next(
            feature
            for feature in state["product_scope"]["features"]["registered"]
            if feature["id"] == feature_id
        )
        for index, gate in enumerate(feature["lifecycle"]["gates"]):
            if index < pass_count:
                gate["status"] = "PASS"
                gate["evidence_refs"] = ["skills/contracts/AGENT_FOUNDATION_PRODUCT_ARCHITECTURE.md"]
                gate["reason"] = None
            else:
                gate["status"] = "UNKNOWN"
                gate["evidence_refs"] = []
                gate["reason"] = "Synthetic progression fixture."
        feature["lifecycle"]["derived_state"] = VALIDATOR_MODULE._derive_agent_foundation_feature_state(
            feature["lifecycle"]["gates"]
        )
        feature["lifecycle"]["regression"] = None

    def future_state(self) -> dict:
        state = self.load_state()
        state["release"] = {
            "status": "FROZEN",
            "id": "R-TEST",
            "id_resolution": "KNOWN",
            "required_feature_ids": ["F004", "F002", "F001", "F003"],
            "required_feature_ids_resolution": "KNOWN",
        }
        for group, names in VALIDATOR_MODULE.AGENT_FOUNDATION_SYSTEM_GATE_LEAVES:
            for name in names:
                self.set_system_leaf(state, group, name, "PASS")
        for feature_id, _, _ in VALIDATOR_MODULE.AGENT_FOUNDATION_PRODUCT_FEATURES:
            self.set_feature_prefix(state, feature_id, 7)
        state["derived_project"]["phase"] = "P7_LIVE"
        return state

    def test_canonical_state_is_schema3_with_current_p0_projection_and_blocker(self) -> None:
        state = self.load_state()
        self.assertEqual(self.validate_state(state), [])
        self.assertEqual(state["schema_version"], 3)
        self.assertEqual(state["derived_project"], {"phase": "P0_SCOPE"})
        self.assertEqual(VALIDATOR_MODULE._derive_agent_foundation_project_phase(state), "P0_SCOPE")
        self.assertEqual(VALIDATOR_MODULE._resolve_agent_foundation_earliest_blocker(state), "release.status")
        self.assertEqual(
            {feature["id"]: feature["lifecycle"]["derived_state"] for feature in state["product_scope"]["features"]["registered"]},
            {"F001": "INTEGRATED", "F002": "INTEGRATED", "F003": "VERIFIED", "F004": "INTEGRATED"},
        )

    def test_exact_global_leaf_inventory_and_current_aggregate_truth(self) -> None:
        state = self.load_state()
        self.assertEqual(list(state["system_gates"]), [name for name, _ in VALIDATOR_MODULE.AGENT_FOUNDATION_SYSTEM_GATE_LEAVES])
        for group, names in VALIDATOR_MODULE.AGENT_FOUNDATION_SYSTEM_GATE_LEAVES:
            self.assertEqual([leaf["name"] for leaf in state["system_gates"][group]["leaves"]], list(names))
            key = "acceptance_status" if group == "production" else "status"
            self.assertEqual(state["system_gates"][group][key], VALIDATOR_MODULE._derive_agent_foundation_group_status(state, group))
        self.assertEqual(
            [
                state["system_gates"]["foundation"]["status"],
                state["system_gates"]["integration"]["status"],
                state["system_gates"]["verification"]["status"],
                state["system_gates"]["hardening"]["status"],
                state["system_gates"]["production"]["acceptance_status"],
            ],
            ["UNKNOWN"] * 5,
        )

    def test_aggregate_precedence_na_exclusion_unknown_not_pass_and_all_na_rejected(self) -> None:
        names = ("a", "b", "c")

        def leaves(statuses: tuple[str, ...]) -> list[dict]:
            return [{"name": name, "status": status} for name, status in zip(names, statuses)]

        cases = (
            (("PASS", "PASS", "PASS"), "PASS"),
            (("PASS", "N/A", "PASS"), "PASS"),
            (("PASS", "PENDING", "N/A"), "PENDING"),
            (("PENDING", "UNKNOWN", "PASS"), "UNKNOWN"),
            (("FAIL", "UNKNOWN", "PENDING"), "FAIL"),
            (("N/A", "N/A", "N/A"), "N/A"),
        )
        for statuses, expected in cases:
            with self.subTest(statuses=statuses):
                self.assertEqual(
                    VALIDATOR_MODULE._derive_agent_foundation_gate_aggregate(leaves(statuses), names),
                    expected,
                )

        state = self.load_state()
        for name in VALIDATOR_MODULE.AGENT_FOUNDATION_SYSTEM_GATE_MAP["foundation"]:
            self.set_system_leaf(state, "foundation", name, "N/A", reason="Explicit synthetic inapplicability.")
        errors = self.validate_state(state)
        self.assertTrue(any("all-N/A aggregate is invalid" in message for message in errors))

        state = self.load_state()
        leaf = self.leaf(state, "foundation", "architecture")
        leaf["status"] = "N/A"
        leaf["evidence_refs"] = []
        leaf["reason"] = ""
        errors = self.validate_state(state)
        self.assertTrue(any("N/A requires a non-empty reason" in message for message in errors))

        state = self.load_state()
        state["system_gates"]["foundation"]["status"] = "PASS"
        errors = self.validate_state(state)
        self.assertTrue(any("expected recomputed status UNKNOWN" in message for message in errors))

    def test_all_p0_through_p7_phase_branches(self) -> None:
        state = self.future_state()
        self.assertEqual(VALIDATOR_MODULE._derive_agent_foundation_project_phase(state), "P7_LIVE")

        changed = deepcopy(state)
        changed["release"]["status"] = "OPEN"
        self.assertEqual(VALIDATOR_MODULE._derive_agent_foundation_project_phase(changed), "P0_SCOPE")

        changed = deepcopy(state)
        self.set_system_leaf(changed, "foundation", "telemetry", "UNKNOWN")
        self.assertEqual(VALIDATOR_MODULE._derive_agent_foundation_project_phase(changed), "P1_FOUNDATION")

        changed = deepcopy(state)
        self.set_feature_prefix(changed, "F001", 3)
        self.assertEqual(VALIDATOR_MODULE._derive_agent_foundation_project_phase(changed), "P2_FEATURE_BUILD")

        changed = deepcopy(state)
        self.set_system_leaf(changed, "integration", "cross_feature_flows", "UNKNOWN")
        self.assertEqual(VALIDATOR_MODULE._derive_agent_foundation_project_phase(changed), "P3_INTEGRATION")

        changed = deepcopy(state)
        self.set_feature_prefix(changed, "F001", 4)
        self.assertEqual(VALIDATOR_MODULE._derive_agent_foundation_project_phase(changed), "P4_VERIFICATION")

        changed = deepcopy(state)
        self.set_feature_prefix(changed, "F001", 5)
        self.assertEqual(VALIDATOR_MODULE._derive_agent_foundation_project_phase(changed), "P5_HARDENING")

        changed = deepcopy(state)
        self.set_feature_prefix(changed, "F001", 6)
        self.assertEqual(VALIDATOR_MODULE._derive_agent_foundation_project_phase(changed), "P6_RELEASE_READY")

    def test_system_phase_branches_and_production_readiness_are_separate(self) -> None:
        state = self.future_state()
        self.set_system_leaf(state, "verification", "contract", "UNKNOWN")
        self.assertEqual(VALIDATOR_MODULE._derive_agent_foundation_project_phase(state), "P4_VERIFICATION")

        state = self.future_state()
        self.set_system_leaf(state, "hardening", "security", "UNKNOWN")
        self.assertEqual(VALIDATOR_MODULE._derive_agent_foundation_project_phase(state), "P5_HARDENING")

        state = self.future_state()
        self.set_system_leaf(state, "production", "operational_readiness", "UNKNOWN")
        self.assertEqual(state["system_gates"]["production"]["acceptance_status"], "PASS")
        self.assertEqual(VALIDATOR_MODULE._derive_agent_foundation_project_phase(state), "P6_RELEASE_READY")

        state = self.future_state()
        self.set_system_leaf(state, "production", "deployment", "UNKNOWN")
        self.assertEqual(state["system_gates"]["production"]["acceptance_status"], "UNKNOWN")
        self.assertEqual(self.leaf(state, "production", "operational_readiness")["status"], "PASS")
        self.assertEqual(VALIDATOR_MODULE._derive_agent_foundation_project_phase(state), "P6_RELEASE_READY")

    def test_system_leaf_blocker_skips_na_before_actual_blockers(self) -> None:
        for blocking_status in ("UNKNOWN", "PENDING", "FAIL"):
            with self.subTest(blocking_status=blocking_status):
                state = self.future_state()
                self.set_system_leaf(
                    state,
                    "foundation",
                    "architecture",
                    "N/A",
                    reason="Synthetic inapplicable architecture gate.",
                )
                self.set_system_leaf(
                    state,
                    "foundation",
                    "dependency_rules",
                    blocking_status,
                )
                self.assertEqual(
                    state["system_gates"]["foundation"]["status"],
                    blocking_status,
                )
                self.assertEqual(
                    VALIDATOR_MODULE._derive_agent_foundation_project_phase(state),
                    "P1_FOUNDATION",
                )
                self.assertEqual(
                    VALIDATOR_MODULE._resolve_agent_foundation_earliest_blocker(state),
                    "system_gates.foundation.dependency_rules",
                )

    def test_system_leaf_blocker_preserves_canonical_order_among_actual_blockers(self) -> None:
        state = self.future_state()
        self.set_system_leaf(
            state,
            "foundation",
            "architecture",
            "N/A",
            reason="Synthetic inapplicable architecture gate.",
        )
        self.set_system_leaf(state, "foundation", "dependency_rules", "PENDING")
        self.set_system_leaf(state, "foundation", "test_infrastructure", "FAIL")
        self.assertEqual(
            VALIDATOR_MODULE._resolve_agent_foundation_earliest_blocker(state),
            "system_gates.foundation.dependency_rules",
        )

    def test_production_acceptance_blocker_skips_na_before_actual_blocker(self) -> None:
        for blocking_status in ("UNKNOWN", "PENDING", "FAIL"):
            with self.subTest(blocking_status=blocking_status):
                state = self.future_state()
                self.set_system_leaf(
                    state,
                    "production",
                    "deployment",
                    "N/A",
                    reason="Synthetic inapplicable deployment gate.",
                )
                self.set_system_leaf(
                    state,
                    "production",
                    "smoke_test",
                    blocking_status,
                )
                self.assertEqual(
                    VALIDATOR_MODULE._derive_agent_foundation_project_phase(state),
                    "P6_RELEASE_READY",
                )
                self.assertEqual(
                    VALIDATOR_MODULE._resolve_agent_foundation_earliest_blocker(state),
                    "system_gates.production.smoke_test",
                )

    def test_registry_and_leaf_order_deterministically_choose_earliest_blocker(self) -> None:
        state = self.load_state()
        state["release"]["status"] = "FROZEN"
        self.assertEqual(VALIDATOR_MODULE._resolve_agent_foundation_earliest_blocker(state), "required_feature_ids_resolution")

        state = self.future_state()
        self.set_system_leaf(state, "foundation", "dependency_rules", "UNKNOWN")
        self.set_system_leaf(state, "foundation", "telemetry", "UNKNOWN")
        self.assertEqual(VALIDATOR_MODULE._resolve_agent_foundation_earliest_blocker(state), "system_gates.foundation.dependency_rules")

        state = self.future_state()
        self.set_feature_prefix(state, "F004", 2)
        self.set_feature_prefix(state, "F001", 2)
        self.assertEqual(VALIDATOR_MODULE._resolve_agent_foundation_earliest_blocker(state), "features.F001.implementation")

        state = self.future_state()
        self.set_system_leaf(state, "integration", "contracts", "UNKNOWN")
        self.set_system_leaf(state, "integration", "data_consistency", "UNKNOWN")
        self.assertEqual(
            VALIDATOR_MODULE._resolve_agent_foundation_earliest_blocker(state),
            "system_gates.integration.contracts",
        )

        state = self.future_state()
        self.set_feature_prefix(state, "F004", 4)
        self.set_feature_prefix(state, "F002", 4)
        self.assertEqual(VALIDATOR_MODULE._resolve_agent_foundation_earliest_blocker(state), "features.F002.verification")

        state = self.future_state()
        self.set_system_leaf(state, "verification", "integration", "UNKNOWN")
        self.set_system_leaf(state, "verification", "security", "UNKNOWN")
        self.assertEqual(
            VALIDATOR_MODULE._resolve_agent_foundation_earliest_blocker(state),
            "system_gates.verification.integration",
        )

        state = self.future_state()
        self.set_feature_prefix(state, "F004", 5)
        self.set_feature_prefix(state, "F001", 5)
        self.assertEqual(VALIDATOR_MODULE._resolve_agent_foundation_earliest_blocker(state), "features.F001.release_readiness")

        state = self.future_state()
        self.set_system_leaf(state, "hardening", "capacity", "UNKNOWN")
        self.set_system_leaf(state, "hardening", "security", "UNKNOWN")
        self.assertEqual(
            VALIDATOR_MODULE._resolve_agent_foundation_earliest_blocker(state),
            "system_gates.hardening.capacity",
        )

        state = self.future_state()
        self.set_feature_prefix(state, "F004", 6)
        self.set_feature_prefix(state, "F001", 6)
        self.assertEqual(VALIDATOR_MODULE._resolve_agent_foundation_earliest_blocker(state), "features.F001.production_acceptance")

        state = self.future_state()
        self.set_system_leaf(state, "production", "smoke_test", "UNKNOWN")
        self.set_system_leaf(state, "production", "deployment", "UNKNOWN")
        self.assertEqual(VALIDATOR_MODULE._resolve_agent_foundation_earliest_blocker(state), "system_gates.production.deployment")

        state = self.future_state()
        self.set_system_leaf(state, "production", "operational_readiness", "UNKNOWN")
        self.assertEqual(
            VALIDATOR_MODULE._resolve_agent_foundation_earliest_blocker(state),
            "system_gates.production.operational_readiness",
        )

    def test_foreign_required_feature_ids_fail_closed_and_input_order_is_normalized(self) -> None:
        state = self.future_state()
        self.assertEqual(
            VALIDATOR_MODULE._normalize_agent_foundation_required_feature_ids(state),
            ["F001", "F002", "F003", "F004"],
        )
        state["release"]["required_feature_ids"] = ["F004", "F999", "F001"]
        with self.assertRaisesRegex(ValueError, "foreign IDs"):
            VALIDATOR_MODULE._derive_agent_foundation_project_phase(state)
        errors = self.validate_state(state)
        self.assertTrue(any("foreign IDs" in message for message in errors))

    def test_stored_phase_mismatch_and_task0021_self_evidence_are_rejected(self) -> None:
        state = self.load_state()
        state["derived_project"]["phase"] = "P1_FOUNDATION"
        errors = self.validate_state(state)
        self.assertTrue(any("expected recomputed phase P0_SCOPE" in message for message in errors))

        state = self.load_state()
        leaf = self.leaf(state, "foundation", "architecture")
        leaf["evidence_refs"] = [".agent/tasks/TASK-0021/task.yaml"]
        errors = self.validate_state(state)
        self.assertTrue(any("cannot evidence their own implementation candidate" in message for message in errors))


class Task0022ProgressionConsumptionTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def load_state(self) -> dict:
        return json.loads((ROOT.parent / "product-state.json").read_text(encoding="utf-8"))

    def test_architect_preplanning_read_order_is_exact(self) -> None:
        architect = self.read("architect/SKILL.md")
        markers = (
            "1. exact target repository",
            "2. exact canonical release identity when one exists",
            "3. release scope status",
            "4. required release feature set",
            "5. canonical feature registry",
            "6. feature states and supporting evidence",
            "7. global system gates",
            "8. derived project phase",
            "9. earliest materially blocking condition",
            "10. applicable target-native architecture/tooling/verifier contracts",
        )
        positions = [architect.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))

    def test_fresh_target_evidence_preserves_unknown_and_separates_task_lifecycle(self) -> None:
        combined = self.read("contracts/FOUNDATION_ARCHITECTURE.md") + "\n" + self.read("architect/SKILL.md")
        for marker in (
            "fresh target-owned evidence",
            "memory, previous chat, task status, report/review status, Runtime state",
            "Missing, contradictory, stale, or inaccessible",
            "preserve UNKNOWN",
            "must not invent",
            "Task lifecycle and product lifecycle remain distinct",
            "fresh target-owned evidence remains required",
        ):
            self.assertIn(marker, combined)

    def test_default_progression_override_and_bounded_handoff_are_explicit(self) -> None:
        architect = self.read("architect/SKILL.md")
        for marker in (
            "earliest materially blocking condition",
            "must not initiate later-phase work merely because it is useful",
            "explicit higher-priority override",
            "current, exact, and authoritative",
            "distinguishable",
            "one coherent progression objective",
            "bounded mutation scope",
            "explicit terminal proof boundary",
            "independently rejectable",
            "must not add a task-schema field",
        ):
            self.assertIn(marker, architect)

    def test_foundation_is_filename_neutral_progression_consumer_not_product_owner(self) -> None:
        architecture = self.read("contracts/FOUNDATION_ARCHITECTURE.md")
        for marker in (
            "## Target product progression consumption",
            "filename-neutral",
            "consume target-owned product progression truth",
            "verify target-defined derived phase",
            "select the target-defined earliest blocker",
            "create bounded task authority",
            "does not own release scope, feature registry, feature state, system gates, or project phase",
            "does not require product-state.json",
            "does not require agent-foundation schema 3",
            "no universal product manifest",
            "one language or validator implementation",
        ):
            self.assertIn(marker, architecture)

    def test_current_p0_consumption_uses_the_accepted_t4_resolver(self) -> None:
        state = self.load_state()
        self.assertEqual(VALIDATOR_MODULE._derive_agent_foundation_project_phase(state), "P0_SCOPE")
        self.assertEqual(VALIDATOR_MODULE._resolve_agent_foundation_earliest_blocker(state), "release.status")
        self.assertEqual(
            {
                feature["id"]: feature["lifecycle"]["derived_state"]
                for feature in state["product_scope"]["features"]["registered"]
            },
            {"F001": "INTEGRATED", "F002": "INTEGRATED", "F003": "VERIFIED", "F004": "INTEGRATED"},
        )

    def test_later_phase_fixtures_reuse_t4_resolver_and_earlier_blockers_win(self) -> None:
        helper = Task0021GlobalProgressionTests(methodName="runTest")

        foundation = helper.future_state()
        helper.set_system_leaf(foundation, "foundation", "security", "UNKNOWN")
        self.assertEqual(VALIDATOR_MODULE._derive_agent_foundation_project_phase(foundation), "P1_FOUNDATION")
        self.assertEqual(
            VALIDATOR_MODULE._resolve_agent_foundation_earliest_blocker(foundation),
            "system_gates.foundation.security",
        )

        verification = helper.future_state()
        helper.set_feature_prefix(verification, "F002", 4)
        self.assertEqual(VALIDATOR_MODULE._derive_agent_foundation_project_phase(verification), "P4_VERIFICATION")
        self.assertEqual(
            VALIDATOR_MODULE._resolve_agent_foundation_earliest_blocker(verification),
            "features.F002.verification",
        )

        current = self.load_state()
        helper.set_feature_prefix(current, "F002", 4)
        helper.set_feature_prefix(current, "F004", 4)
        self.assertEqual(VALIDATOR_MODULE._derive_agent_foundation_project_phase(current), "P0_SCOPE")
        self.assertEqual(VALIDATOR_MODULE._resolve_agent_foundation_earliest_blocker(current), "release.status")

    def test_stored_projection_must_match_target_derivation_before_planning(self) -> None:
        combined = self.read("contracts/FOUNDATION_ARCHITECTURE.md") + "\n" + self.read("architect/SKILL.md")
        for marker in (
            "stored and derived truth disagree",
            "fail closed",
            "deterministic derivation semantics",
        ):
            self.assertIn(marker, combined)


class Task0020FeatureLifecycleTests(unittest.TestCase):
    def load_state(self) -> dict:
        return json.loads((ROOT.parent / "product-state.json").read_text(encoding="utf-8"))

    def feature(self, state: dict, feature_id: str) -> dict:
        return next(
            feature
            for feature in state["product_scope"]["features"]["registered"]
            if feature["id"] == feature_id
        )

    def validate_state(self, document: dict) -> list[str]:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "product-state.json"
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        VALIDATOR_MODULE.errors.clear()
        VALIDATOR_MODULE.validate_agent_foundation_product_state(
            path,
            evidence_root=ROOT.parent,
        )
        messages = list(VALIDATOR_MODULE.errors)
        VALIDATOR_MODULE.errors.clear()
        return messages

    def transition_errors(self, previous: dict, current: dict) -> list[str]:
        VALIDATOR_MODULE.errors.clear()
        VALIDATOR_MODULE.validate_agent_foundation_product_state_transition(
            previous,
            current,
            evidence_root=ROOT.parent,
        )
        messages = list(VALIDATOR_MODULE.errors)
        VALIDATOR_MODULE.errors.clear()
        return messages

    def set_gate(
        self,
        feature: dict,
        gate_name: str,
        status: str,
        *,
        refs: list[str] | None = None,
        reason: str | None = None,
    ) -> None:
        gate = next(gate for gate in feature["lifecycle"]["gates"] if gate["name"] == gate_name)
        gate["status"] = status
        gate["evidence_refs"] = [] if refs is None else refs
        gate["reason"] = reason

    def test_canonical_schema3_preserves_exact_t3_gates_conservative_states_and_f001_regression(self) -> None:
        state = self.load_state()
        self.assertEqual(self.validate_state(state), [])
        self.assertEqual(state["schema_version"], 3)
        expected_states = {
            "F001": "INTEGRATED",
            "F002": "INTEGRATED",
            "F003": "VERIFIED",
            "F004": "INTEGRATED",
        }
        expected_f001_regression = {
            "from_state": "VERIFIED",
            "to_state": "INTEGRATED",
            "reason": "TASK-0015 final_execution_head f09c2df5e1affdd843af91d3dc70375269d255ab predates the three current profile/ bootstrap changes in TASK-0024; no persisted result verifies these exact current owner bytes.",
            "evidence_refs": [
                ".agent/tasks/TASK-0015/report.yaml",
                ".agent/tasks/TASK-0024/task.yaml",
                "profile/.agent/bootstrap/bootstrap.json",
                "profile/.agent/bootstrap/test_bootstrap.py",
                "profile/.agent/bootstrap/validate.py",
            ],
        }
        for feature in state["product_scope"]["features"]["registered"]:
            self.assertEqual(
                [gate["name"] for gate in feature["lifecycle"]["gates"]],
                list(VALIDATOR_MODULE.AGENT_FOUNDATION_LIFECYCLE_GATES),
            )
            self.assertEqual(feature["lifecycle"]["derived_state"], expected_states[feature["id"]])
            if feature["id"] == "F001":
                self.assertEqual(feature["lifecycle"]["regression"], expected_f001_regression)
            else:
                self.assertIsNone(feature["lifecycle"]["regression"])
            self.assertNotIn(feature["lifecycle"]["derived_state"], {"RELEASE_READY", "LIVE"})

    def test_all_seven_lifecycle_thresholds_are_derived_from_ordered_pass_prefix(self) -> None:
        for pass_count, expected in enumerate(
            VALIDATOR_MODULE.AGENT_FOUNDATION_LIFECYCLE_STATES,
            start=1,
        ):
            gates = []
            for index, name in enumerate(VALIDATOR_MODULE.AGENT_FOUNDATION_LIFECYCLE_GATES):
                gates.append(
                    {
                        "name": name,
                        "status": "PASS" if index < pass_count else "UNKNOWN",
                    }
                )
            self.assertEqual(
                VALIDATOR_MODULE._derive_agent_foundation_feature_state(gates),
                expected,
            )

    def test_unknown_pending_fail_and_na_never_advance(self) -> None:
        for status in ("UNKNOWN", "PENDING", "FAIL", "N/A"):
            gates = [
                {"name": name, "status": "PASS"}
                for name in VALIDATOR_MODULE.AGENT_FOUNDATION_LIFECYCLE_GATES
            ]
            gates[4]["status"] = status
            self.assertEqual(
                VALIDATOR_MODULE._derive_agent_foundation_feature_state(gates),
                "INTEGRATED",
            )

    def test_na_requires_justification_and_does_not_advance(self) -> None:
        state = self.load_state()
        feature = self.feature(state, "F002")
        self.set_gate(feature, "verification", "N/A", reason="")
        errors = self.validate_state(state)
        self.assertTrue(any("N/A requires a non-empty reason" in message for message in errors))

        self.set_gate(feature, "verification", "N/A", reason="Verification is demonstrably inapplicable.")
        feature["lifecycle"]["derived_state"] = "INTEGRATED"
        self.assertEqual(self.validate_state(state), [])

    def test_pass_requires_persisted_evidence_and_verification_result_not_definition(self) -> None:
        state = self.load_state()
        feature = self.feature(state, "F002")
        self.set_gate(feature, "verification", "PASS", refs=[], reason=None)
        feature["lifecycle"]["derived_state"] = "VERIFIED"
        errors = self.validate_state(state)
        self.assertTrue(any("PASS requires inspectable persisted evidence" in message for message in errors))

        self.set_gate(
            feature,
            "verification",
            "PASS",
            refs=["skills/scripts/test_validate_skill_library.py"],
            reason=None,
        )
        errors = self.validate_state(state)
        self.assertTrue(any("verification PASS requires persisted result evidence" in message for message in errors))

    def test_later_pass_without_prerequisite_and_derived_state_mismatch_are_rejected(self) -> None:
        state = self.load_state()
        feature = self.feature(state, "F002")
        self.set_gate(
            feature,
            "release_readiness",
            "PASS",
            refs=["skills/contracts/AGENT_FOUNDATION_PRODUCT_STATE.md"],
            reason=None,
        )
        errors = self.validate_state(state)
        self.assertTrue(any("later gate cannot PASS" in message for message in errors))
        self.assertTrue(any("unresolved OPEN release forbids PASS" in message for message in errors))

        state = self.load_state()
        self.feature(state, "F002")["lifecycle"]["derived_state"] = "VERIFIED"
        errors = self.validate_state(state)
        self.assertTrue(any("expected recomputed state INTEGRATED" in message for message in errors))

    def test_release_open_caps_every_feature_at_verified(self) -> None:
        state = self.load_state()
        feature = self.feature(state, "F003")
        self.set_gate(
            feature,
            "release_readiness",
            "PASS",
            refs=["skills/contracts/AGENT_FOUNDATION_PRODUCT_STATE.md"],
            reason=None,
        )
        feature["lifecycle"]["derived_state"] = "RELEASE_READY"
        errors = self.validate_state(state)
        self.assertTrue(any("unresolved OPEN release forbids PASS" in message for message in errors))
        self.assertTrue(any("caps state at VERIFIED" in message for message in errors))

    def test_self_future_missing_and_stale_evidence_are_rejected(self) -> None:
        state = self.load_state()
        feature = self.feature(state, "F001")
        scope = feature["lifecycle"]["gates"][0]
        scope["evidence_refs"] = ["product-state.json"]
        errors = self.validate_state(state)
        self.assertTrue(any("cannot self-attest" in message for message in errors))

        scope["evidence_refs"] = [".agent/tasks/TASK-0020/report.yaml"]
        errors = self.validate_state(state)
        self.assertTrue(any("cannot evidence their own implementation candidate" in message for message in errors))

        scope["evidence_refs"] = ["profile/does-not-exist.md"]
        errors = self.validate_state(state)
        self.assertTrue(any("missing or inaccessible" in message for message in errors))

        state = self.load_state()
        feature = self.feature(state, "F001")
        verification = feature["lifecycle"]["gates"][4]
        verification["status"] = "PASS"
        verification["reason"] = None
        verification["evidence_refs"] = [
            ".agent/tasks/TASK-0004/report.yaml",
            "profile/.agent/bootstrap/validate.py",
        ]
        feature["lifecycle"]["derived_state"] = "VERIFIED"
        feature["lifecycle"]["regression"] = None
        errors = self.validate_state(state)
        self.assertTrue(any("attributable to exact current owner bytes" in message for message in errors))

    def test_release_truth_and_exact_t2_feature_identity_remain_unchanged(self) -> None:
        state = self.load_state()
        self.assertEqual(
            state["release"],
            {
                "status": "OPEN",
                "id": None,
                "id_resolution": "UNKNOWN",
                "required_feature_ids": None,
                "required_feature_ids_resolution": "UNKNOWN",
            },
        )
        self.assertEqual(
            [
                (feature["id"], feature["semantic_name"], feature["owner"])
                for feature in state["product_scope"]["features"]["registered"]
            ],
            list(VALIDATOR_MODULE.AGENT_FOUNDATION_PRODUCT_FEATURES),
        )

    def test_downgrade_requires_exact_evidence_backed_regression_record(self) -> None:
        previous = self.load_state()
        previous_feature = self.feature(previous, "F001")
        self.set_gate(
            previous_feature,
            "verification",
            "PASS",
            refs=[".agent/tasks/TASK-0015/report.yaml"],
            reason=None,
        )
        previous_feature["lifecycle"]["derived_state"] = "VERIFIED"
        previous_feature["lifecycle"]["regression"] = None
        current = deepcopy(previous)
        feature = self.feature(current, "F001")
        self.set_gate(
            feature,
            "verification",
            "UNKNOWN",
            reason="Previously verified evidence is no longer sufficient.",
        )
        feature["lifecycle"]["derived_state"] = "INTEGRATED"
        self.assertTrue(
            any("downgrade requires explicit regression record" in message for message in self.transition_errors(previous, current))
        )

        feature["lifecycle"]["regression"] = {
            "from_state": "VERIFIED",
            "to_state": "INTEGRATED",
            "reason": "Previously verified evidence is no longer sufficient.",
            "evidence_refs": ["profile/.agent/bootstrap/validate.py"],
        }
        self.assertEqual(self.validate_state(current), [])
        self.assertEqual(self.transition_errors(previous, current), [])

        feature["lifecycle"]["regression"]["from_state"] = "INTEGRATED"
        self.assertTrue(
            any("must exactly match prior/current derived states" in message for message in self.transition_errors(previous, current))
        )

    def test_non_regression_transition_rejects_stale_regression_record(self) -> None:
        previous = self.load_state()
        self.feature(previous, "F001")["lifecycle"]["regression"] = None
        current = deepcopy(previous)
        feature = self.feature(current, "F002")
        feature["lifecycle"]["regression"] = {
            "from_state": "VERIFIED",
            "to_state": "INTEGRATED",
            "reason": "stale record",
            "evidence_refs": ["skills/contracts/FOUNDATION_ARCHITECTURE.md"],
        }
        errors = self.transition_errors(previous, current)
        self.assertTrue(any("non-regression transition must keep regression null" in message for message in errors))

    def test_initial_schema1_to_schema2_adoption_requires_null_regression(self) -> None:
        current = self.load_state()
        self.feature(current, "F001")["lifecycle"]["regression"] = None
        previous = deepcopy(current)
        previous["schema_version"] = 1
        for feature in previous["product_scope"]["features"]["registered"]:
            feature.pop("lifecycle")
        self.assertEqual(self.transition_errors(previous, current), [])

        feature = self.feature(current, "F002")
        feature["lifecycle"]["regression"] = {
            "from_state": "VERIFIED",
            "to_state": "INTEGRATED",
            "reason": "fabricated migration regression",
            "evidence_refs": ["skills/contracts/FOUNDATION_ARCHITECTURE.md"],
        }
        errors = self.transition_errors(previous, current)
        self.assertTrue(any("initial schema-1 to schema-2 adoption requires regression null" in message for message in errors))

    def test_f004_persisted_blocked_verifier_is_unknown_not_pass(self) -> None:
        state = self.load_state()
        feature = self.feature(state, "F004")
        verification = feature["lifecycle"]["gates"][4]
        self.assertEqual(verification["status"], "UNKNOWN")
        self.assertEqual(verification["evidence_refs"], [".agent/tasks/TASK-0004/report.yaml"])
        self.assertIn("capability-blocked", verification["reason"])
        self.assertEqual(feature["lifecycle"]["derived_state"], "INTEGRATED")




class Task0020Revision2EvidenceParserTests(unittest.TestCase):
    def synthetic_repo(self, owner: str, report_body: str) -> tuple[tempfile.TemporaryDirectory[str], Path, str]:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / "repo"
        root.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
        owner_path = root / owner
        owner_path.mkdir(parents=True)
        (owner_path / "owner.txt").write_text("current owner bytes\n", encoding="utf-8")
        subprocess.run(["git", "add", owner], cwd=root, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "owner"], cwd=root, check=True)
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        report = root / ".agent" / "tasks" / "TASK-9998" / "report.yaml"
        report.parent.mkdir(parents=True)
        report.write_text(report_body.replace("__HEAD__", head), encoding="utf-8")
        return temp, root, ".agent/tasks/TASK-9998/report.yaml"

    def covers(self, report_ref: str, owner: str, root: Path) -> bool:
        VALIDATOR_MODULE.errors.clear()
        try:
            return VALIDATOR_MODULE._verification_report_covers_owner(
                report_ref,
                owner=owner,
                evidence_root=root,
            )
        finally:
            VALIDATOR_MODULE.errors.clear()

    def test_architect_profile_false_fail_exploit_is_rejected(self) -> None:
        _, root, report_ref = self.synthetic_repo(
            "profile",
            """execution:
  final_execution_head: "__HEAD__"
verification:
  bootstrap_validator:
    signal: "OPM_BOOTSTRAP = FALSE"
    result: FAIL
""",
        )
        self.assertFalse(self.covers(report_ref, "profile/", root))

    def test_architect_documents_fail_plus_unrelated_pass_exploit_is_rejected(self) -> None:
        _, root, report_ref = self.synthetic_repo(
            "documents",
            """execution:
  final_execution_head: "__HEAD__"
verification:
  documents_tests:
    result: FAIL
  unrelated_check:
    result: PASS
""",
        )
        self.assertFalse(self.covers(report_ref, "documents/", root))

    def test_profile_contradictory_true_and_false_is_rejected(self) -> None:
        _, root, report_ref = self.synthetic_repo(
            "profile",
            """execution:
  final_execution_head: "__HEAD__"
verification:
  bootstrap_local:
    signal: "OPM_BOOTSTRAP = TRUE"
    result: PASS
  bootstrap_remote:
    signal: "OPM_BOOTSTRAP = FALSE"
    result: FAIL
""",
        )
        self.assertFalse(self.covers(report_ref, "profile/", root))

    def test_profile_unknown_or_failed_bootstrap_evidence_is_rejected(self) -> None:
        cases = (
            """execution:
  final_execution_head: "__HEAD__"
verification:
  bootstrap_validator:
    signal: "OPM_BOOTSTRAP = UNKNOWN"
    result: PASS
""",
            """execution:
  final_execution_head: "__HEAD__"
verification:
  bootstrap_validator:
    signal: "OPM_BOOTSTRAP = TRUE"
    result: PASS
  bootstrap_unit_tests:
    result: FAIL
""",
            """execution:
  final_execution_head: "__HEAD__"
verification:
  bootstrap_validator:
    signal: "OPM_BOOTSTRAP = TRUE"
""",
        )
        for body in cases:
            with self.subTest(body=body):
                _, root, report_ref = self.synthetic_repo("profile", body)
                self.assertFalse(self.covers(report_ref, "profile/", root))

    def test_documents_contradictory_owner_blocks_are_rejected(self) -> None:
        _, root, report_ref = self.synthetic_repo(
            "documents",
            """execution:
  final_execution_head: "__HEAD__"
first:
  documents_tests:
    result: PASS
second:
  documents_tests:
    result: FAIL
""",
        )
        self.assertFalse(self.covers(report_ref, "documents/", root))

    def test_standards_blocked_plus_unrelated_pass_is_rejected(self) -> None:
        _, root, report_ref = self.synthetic_repo(
            "standards",
            """execution:
  final_execution_head: "__HEAD__"
verification:
  standards_verifier:
    result: CAPABILITY_BLOCKED
  unrelated_check:
    result: PASS
""",
        )
        self.assertFalse(self.covers(report_ref, "standards/", root))

    def test_skills_generic_or_misscoped_pass_is_rejected(self) -> None:
        _, root, report_ref = self.synthetic_repo(
            "skills",
            """execution:
  final_execution_head: "__HEAD__"
verification:
  unrelated_check:
    result: PASS
summary: "skills checks mentioned here and something passed"
""",
        )
        self.assertFalse(self.covers(report_ref, "skills/", root))

    def test_skills_negative_owner_result_plus_unrelated_pass_is_rejected(self) -> None:
        _, root, report_ref = self.synthetic_repo(
            "skills",
            """execution:
  final_execution_head: "__HEAD__"
verification:
  skills_validator:
    result: FAIL
  unrelated_check:
    result: PASS
""",
        )
        self.assertFalse(self.covers(report_ref, "skills/", root))

    def test_scoped_positive_synthetic_owner_results_are_accepted(self) -> None:
        cases = (
            (
                "profile",
                "profile/",
                """execution:
  final_execution_head: "__HEAD__"
verification:
  bootstrap_validator:
    signal: "OPM_BOOTSTRAP = TRUE"
    result: PASS
""",
            ),
            (
                "documents",
                "documents/",
                """execution:
  final_execution_head: "__HEAD__"
verification:
  documents_tests:
    result: PASS
""",
            ),
            (
                "standards",
                "standards/",
                """execution:
  final_execution_head: "__HEAD__"
verification:
  standards_verifier:
    result: PASS
""",
            ),
            (
                "skills",
                "skills/",
                """execution:
  final_execution_head: "__HEAD__"
verification:
  skills_validator:
    result: PASS
  skills_validator_tests:
    result: PASS
""",
            ),
        )
        for owner_dir, owner, body in cases:
            with self.subTest(owner=owner):
                _, root, report_ref = self.synthetic_repo(owner_dir, body)
                self.assertTrue(self.covers(report_ref, owner, root))

    def test_profile_misscoped_true_narration_without_bootstrap_structure_is_rejected(self) -> None:
        _, root, report_ref = self.synthetic_repo(
            "profile",
            """execution:
  final_execution_head: "__HEAD__"
acceptance_evidence:
  - criterion_id: AC-X
    status: PASS
    evidence: "Unrelated narration mentions OPM_BOOTSTRAP = TRUE but is not bootstrap verification evidence."
""",
        )
        self.assertFalse(self.covers(report_ref, "profile/", root))

    def test_profile_scoped_bootstrap_true_block_is_accepted(self) -> None:
        _, root, report_ref = self.synthetic_repo(
            "profile",
            """execution:
  final_execution_head: "__HEAD__"
verification:
  bootstrap_validator:
    signal: "OPM_BOOTSTRAP = TRUE"
    result: PASS
""",
        )
        self.assertTrue(self.covers(report_ref, "profile/", root))

    def test_profile_scoped_positive_requires_exact_owner_bytes(self) -> None:
        _, root, report_ref = self.synthetic_repo(
            "profile",
            """execution:
  final_execution_head: "__HEAD__"
verification:
  bootstrap_validator:
    signal: "OPM_BOOTSTRAP = TRUE"
    result: PASS
""",
        )
        (root / "profile" / "owner.txt").write_text("changed profile bytes\n", encoding="utf-8")
        self.assertFalse(self.covers(report_ref, "profile/", root))

    def test_real_f001_evidence_is_stale_after_profile_changes_while_f003_stays_exact(self) -> None:
        root = ROOT.parent
        self.assertFalse(self.covers(".agent/tasks/TASK-0015/report.yaml", "profile/", root))
        self.assertTrue(self.covers(".agent/tasks/TASK-0004/report.yaml", "documents/", root))
        self.assertFalse(self.covers(".agent/tasks/TASK-0004/report.yaml", "standards/", root))


class Task0010RationalizationTests(unittest.TestCase):
    def fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name) / "repo"
        shutil.copytree(ROOT, root)
        self.addCleanup(temp.cleanup)
        return temp, root

    def run_validator(self, root: Path) -> subprocess.CompletedProcess[str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        original_root = VALIDATOR_MODULE.ROOT
        try:
            VALIDATOR_MODULE.ROOT = root
            VALIDATOR_MODULE.errors.clear()
            VALIDATOR_MODULE.warnings.clear()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                returncode = VALIDATOR_MODULE.main()
        finally:
            VALIDATOR_MODULE.ROOT = original_root
        return subprocess.CompletedProcess(
            args=["python3", str(root / VALIDATOR)],
            returncode=returncode,
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue(),
        )

    def read_map(self, root: Path) -> dict:
        return json.loads((root / ".agent" / "rationalization.json").read_text(encoding="utf-8"))

    def write_map(self, root: Path, document: dict) -> None:
        (root / ".agent" / "rationalization.json").write_text(
            json.dumps(document, indent=2) + "\n",
            encoding="utf-8",
        )

    def disposition(self, document: dict, skill_id: str) -> dict:
        return next(record for record in document["dispositions"] if record["skill_id"] == skill_id)

    def test_canonical_rationalization_passes_and_matches_filesystem(self) -> None:
        result = self.run_validator(ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        document = self.read_map(ROOT)
        expected = {
            record["skill_id"]
            for record in document["dispositions"]
            if record["disposition"] in VALIDATOR_MODULE.INTERNAL_DISPOSITIONS
        }
        self.assertEqual({path.parent.name for path in ROOT.rglob("SKILL.md")}, expected)
        self.assertEqual(
            {record["skill_id"] for record in document["dispositions"] if record["disposition"] == "KEEP_FOUNDATION_SPECIFIC"},
            {"adversarial-audit", "architect", "executor", "reliability", "simplicity"},
        )
        self.assertEqual(
            {record["skill_id"] for record in document["dispositions"] if record["disposition"] == "THIN_DELTA"},
            {"security-review", "verification"},
        )

    def test_task0015_external_routes_are_exact_and_ecc_first_except_proven_gap(self) -> None:
        document = self.read_map(ROOT)
        expected = {
            "debugging": ("superpowers:systematic-debugging", "5bf4e78011075bcfc0dc295f0724994cd123ee71"),
            "design-review": ("ecc:agent:architect", "bf70150eb2df8070024e5bdf08e4aa08959e2735"),
            "gap-analysis": ("ecc:intent-driven-development", "bf70150eb2df8070024e5bdf08e4aa08959e2735"),
            "optimization": ("ecc:benchmark-optimization-loop", "bf70150eb2df8070024e5bdf08e4aa08959e2735"),
            "research": ("ecc:research-ops", "bf70150eb2df8070024e5bdf08e4aa08959e2735"),
            "reuse-first": ("ecc:search-first", "bf70150eb2df8070024e5bdf08e4aa08959e2735"),
            "security-review": ("ecc:security-review", "bf70150eb2df8070024e5bdf08e4aa08959e2735"),
            "verification": ("ecc:verification-loop", "bf70150eb2df8070024e5bdf08e4aa08959e2735"),
        }
        for skill_id, (entry_id, revision) in expected.items():
            with self.subTest(skill_id=skill_id):
                record = self.disposition(document, skill_id)
                external = record["external_capability"]
                self.assertEqual(external["catalog_entry_id"], entry_id)
                self.assertEqual(external["revision"], revision)
                self.assertEqual(record["surviving_semantic_owner"], f"external:{entry_id}" if record["disposition"] == "REPLACE_BY_EXTERNAL" else f"internal:{skill_id}")

    def test_retired_skill_reappearance_is_rejected(self) -> None:
        _, root = self.fixture()
        path = root / "cloud-run-basics" / "SKILL.md"
        path.parent.mkdir(parents=True)
        path.write_text(
            "---\nname: cloud-run-basics\ndescription: stale retired skill\n---\n\n# stale\n",
            encoding="utf-8",
        )
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("curated skill locations mismatch", result.stdout + result.stderr)

    def test_missing_starting_skill_disposition_is_rejected(self) -> None:
        _, root = self.fixture()
        document = self.read_map(root)
        document["dispositions"] = document["dispositions"][:-1]
        self.write_map(root, document)
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("starting-skill disposition coverage mismatch", result.stdout + result.stderr)

    def test_duplicate_disposition_is_rejected(self) -> None:
        _, root = self.fixture()
        document = self.read_map(root)
        document["dispositions"].append(deepcopy(document["dispositions"][0]))
        self.write_map(root, document)
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate disposition for starting skill", result.stdout + result.stderr)

    def test_architect_and_executor_cannot_be_externalized_or_retired(self) -> None:
        for skill_id in ("architect", "executor"):
            with self.subTest(skill_id=skill_id):
                _, root = self.fixture()
                document = self.read_map(root)
                record = self.disposition(document, skill_id)
                record["disposition"] = "RETIRE"
                record["surviving_semantic_owner"] = "canonical:missing-owner"
                self.write_map(root, document)
                result = self.run_validator(root)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"{skill_id} must remain KEEP_FOUNDATION_SPECIFIC", result.stdout + result.stderr)

    def test_mutable_external_revision_is_rejected(self) -> None:
        _, root = self.fixture()
        document = self.read_map(root)
        self.disposition(document, "debugging")["external_capability"]["revision"] = "main"
        self.write_map(root, document)
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("external revision must be an exact immutable 40-hex SHA", result.stdout + result.stderr)

    def test_ecc_harness_source_is_admissible_but_discovery_source_is_not(self) -> None:
        canonical = self.run_validator(ROOT)
        self.assertEqual(canonical.returncode, 0, canonical.stdout + canonical.stderr)

        _, root = self.fixture()
        path = root / ".agent" / "external-capabilities" / "sources.json"
        sources = json.loads(path.read_text(encoding="utf-8"))
        ecc = next(item for item in sources["sources"] if item["id"] == "ecc")
        self.assertEqual(ecc["kind"], "harness_source")
        ecc["kind"] = "discovery_source"
        path.write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("discovery-only/Awesome entries cannot be adopted", result.stdout + result.stderr)

    def test_discovery_only_awesome_adoption_is_rejected(self) -> None:
        _, root = self.fixture()
        document = self.read_map(root)
        record = self.disposition(document, "adversarial-audit")
        record["disposition"] = "THIN_DELTA"
        record["external_capability"] = {
            "catalog_entry_id": "awesome:004fdb18ab5263ba",
            "repository": "sindresorhus/awesome",
            "revision": "bc98e517ddca672f55f9857d714fc3ea3c3540b2",
            "path": "readme.md",
        }
        self.write_map(root, document)
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("discovery-only/Awesome entries cannot be adopted", result.stdout + result.stderr)

    def test_missing_external_path_is_rejected(self) -> None:
        _, root = self.fixture()
        document = self.read_map(root)
        self.disposition(document, "optimization")["external_capability"]["path"] = ""
        self.write_map(root, document)
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("external capability identity fields must be non-empty strings", result.stdout + result.stderr)

    def test_missing_thin_delta_reference_is_rejected(self) -> None:
        _, root = self.fixture()
        path = root / "security-review" / "SKILL.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "bf70150eb2df8070024e5bdf08e4aa08959e2735",
                "PIN_REMOVED",
            ),
            encoding="utf-8",
        )
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("thin-delta skill is missing exact external reference token", result.stdout + result.stderr)

    def test_duplicate_semantic_owner_is_rejected(self) -> None:
        _, root = self.fixture()
        document = self.read_map(root)
        self.disposition(document, "design-review")["surviving_semantic_owner"] = "internal:adversarial-audit"
        self.write_map(root, document)
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate semantic owner", result.stdout + result.stderr)

    def test_target_repository_retire_owner_is_resolvable(self) -> None:
        document = self.read_map(ROOT)
        record = self.disposition(document, "cloud-run-basics")
        self.assertEqual(record["disposition"], "RETIRE")
        self.assertEqual(record["surviving_semantic_owner"], "target-repository:cloud-run")
        self.assertIsNone(record["external_capability"])
        result = self.run_validator(ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_malformed_target_repository_retire_owner_is_rejected(self) -> None:
        _, root = self.fixture()
        document = self.read_map(root)
        record = self.disposition(document, "cloud-run-basics")
        record["disposition"] = "RETIRE"
        record["surviving_semantic_owner"] = "target-repository:"
        record["external_capability"] = None
        self.write_map(root, document)
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RETIRE must identify a resolvable canonical or target-repository owner", result.stdout + result.stderr)

    def test_orphaned_retire_owner_is_rejected(self) -> None:
        _, root = self.fixture()
        document = self.read_map(root)
        record = self.disposition(document, "reliability")
        record["disposition"] = "RETIRE"
        record["surviving_semantic_owner"] = "canonical:missing-owner"
        self.write_map(root, document)
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("orphaned semantic capability", result.stdout + result.stderr)

    def test_rationalization_filesystem_disagreement_is_rejected(self) -> None:
        _, root = self.fixture()
        (root / "reliability" / "SKILL.md").unlink()
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("curated skill locations mismatch", result.stdout + result.stderr)

    def test_disposition_order_is_deterministic(self) -> None:
        _, root = self.fixture()
        document = self.read_map(root)
        document["dispositions"] = list(reversed(document["dispositions"]))
        self.write_map(root, document)
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("deterministic starting-taxonomy order", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
