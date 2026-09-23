#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import continuity_findings as continuity

ROOT = Path(__file__).resolve().parents[1]


class ContinuityFindingTests(unittest.TestCase):
    def finding(self) -> dict:
        return continuity._load_yaml(ROOT / "templates" / "continuity-finding.yaml")

    def make_root(self, directory: str, *, authorized: bool = True) -> Path:
        root = Path(directory)
        (root / "profile" / ".agent" / "continuity").mkdir(parents=True)
        task_dir = root / ".agent" / "tasks" / "TASK-0008"
        task_dir.mkdir(parents=True)
        required = (
            '    - "Provide deterministic continuity store recording."\n'
            if authorized
            else '    - "Unrelated implementation change."\n'
        )
        (task_dir / "task.yaml").write_text(
            "state: APPROVED\n"
            "execution_ready: true\n"
            "target:\n"
            "  repository: phatnguyen03022001/agent-foundation\n"
            "scope:\n"
            "  required_changes:\n"
            + required,
            encoding="utf-8",
        )
        return root

    def test_template_is_non_authoritative_and_unvalidated(self) -> None:
        document = continuity.validate_finding(self.finding())
        self.assertEqual(document["authority"], "NONE")
        self.assertEqual(document["status"], "UNVALIDATED_FOR_OWNER")
        self.assertEqual(len(continuity.finding_key(document)), 64)

    def test_owner_key_is_deterministic_path_safe_and_isolated(self) -> None:
        first = continuity.owner_store_name("Owner/Repo")
        same = continuity.owner_store_name("owner/repo")
        other = continuity.owner_store_name("owner/other")
        self.assertEqual(first, same)
        self.assertNotEqual(first, other)
        self.assertNotIn("/", first)
        self.assertTrue(first.endswith(".json"))

    def test_record_deduplicates_without_mutating_task_or_owner_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_root(directory)
            task = ".agent/tasks/TASK-0008/task.yaml"
            task_before = (root / task).read_text(encoding="utf-8")
            path, key, created = continuity.record_finding(root, self.finding(), task)
            second_path, second_key, second_created = continuity.record_finding(
                root, self.finding(), task
            )
            self.assertTrue(created)
            self.assertFalse(second_created)
            self.assertEqual(path, second_path)
            self.assertEqual(key, second_key)
            store = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(store["authority"], "NONE")
            self.assertEqual(len(store["findings"]), 1)
            self.assertEqual(store["findings"][0]["status"], "UNVALIDATED_FOR_OWNER")
            self.assertEqual((root / task).read_text(encoding="utf-8"), task_before)
            self.assertFalse((root / "owner").exists())
            json_files = list((root / "profile" / ".agent" / "continuity").glob("*.json"))
            self.assertEqual([item.resolve() for item in json_files], [path.resolve()])

    def test_record_requires_explicit_current_continuity_authority(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_root(directory, authorized=False)
            with self.assertRaisesRegex(ValueError, "explicitly authorize continuity"):
                continuity.record_finding(
                    root, self.finding(), ".agent/tasks/TASK-0008/task.yaml"
                )

    def test_bound_owner_lookup_excludes_unrelated_owner_and_never_authorizes_action(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_root(directory)
            task = ".agent/tasks/TASK-0008/task.yaml"
            first = self.finding()
            second = copy.deepcopy(first)
            second["owner_repository"] = "owner/second"
            second["summary"] = "Second owner finding."
            _path1, key1, _ = continuity.record_finding(root, first, task)
            _path2, key2, _ = continuity.record_finding(root, second, task)
            result = continuity.load_for_binding(root, first["owner_repository"], "a" * 40)
            self.assertEqual(result["owner_repository"], "owner/owner-repo")
            self.assertEqual([item["finding_key"] for item in result["findings"]], [key1])
            self.assertNotIn(key2, json.dumps(result))
            self.assertFalse(result["consequence_authorized"])
            self.assertTrue(result["requires_fresh_revalidation"])
            self.assertEqual(result["status"], "UNVALIDATED_FOR_OWNER")

    def test_binding_requires_exact_fresh_revision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_root(directory)
            with self.assertRaisesRegex(ValueError, "fresh_owner_revision"):
                continuity.load_for_binding(root, "owner/repo", "main")
            result = continuity.load_for_binding(root, "owner/repo", "b" * 40)
            self.assertEqual(result["authority"], "NONE")
            self.assertFalse(result["consequence_authorized"])

    def test_invalid_owner_absolute_source_path_and_unbounded_metadata_fail_closed(self) -> None:
        bad = self.finding()
        bad["owner_repository"] = "invalid-owner"
        with self.assertRaises(ValueError):
            continuity.validate_finding(bad)

        bad = self.finding()
        bad["source"]["task_locator"] = "/absolute/task.yaml"
        with self.assertRaises(ValueError):
            continuity.validate_finding(bad)

        bad = self.finding()
        bad["summary"] = "x" * 501
        with self.assertRaises(ValueError):
            continuity.validate_finding(bad)


if __name__ == "__main__":
    unittest.main()
