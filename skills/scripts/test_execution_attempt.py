#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import execution_attempt as attempts  # noqa: E402


class ExecutionAttemptTests(unittest.TestCase):
    repository = "acme/example"
    task_id = "TASK-0009"
    task_revision = 1
    t0 = datetime(2026, 9, 23, 12, 0, 0, tzinfo=timezone.utc)
    attempt_id = "0123456789abcdef0123456789abcdef"

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Execution Attempt Test")
        self.git("config", "user.email", "execution-attempt@example.invalid")
        self.git("remote", "add", "origin", f"https://github.com/{self.repository}.git")
        task = self.root / ".agent" / "tasks" / self.task_id
        task.mkdir(parents=True)
        (task / "task.yaml").write_text(
            "protocol_version: 3\n"
            f"task_id: {self.task_id}\n"
            f"task_revision: {self.task_revision}\n"
            "state: APPROVED\n",
            encoding="utf-8",
        )
        (self.root / "tracked.txt").write_text("baseline\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-m", "baseline")
        self.base = self.git("rev-parse", "HEAD").strip()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def git(self, *args: str, check: bool = True) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )
        if check and result.returncode != 0:
            self.fail(result.stdout + result.stderr)
        return result.stdout

    def start(self, **overrides):
        values = {
            "root": self.root,
            "repository": self.repository,
            "task_id": self.task_id,
            "task_revision": self.task_revision,
            "execution_base": self.base,
            "lease_seconds": 60,
            "now": self.t0,
            "attempt_id": self.attempt_id,
        }
        values.update(overrides)
        return attempts.start_attempt(**values)

    def record_path(self) -> Path:
        raw = self.git(
            "rev-parse", "--git-path", "agent-foundation/execution-attempts"
        ).strip()
        path = Path(raw)
        if not path.is_absolute():
            path = self.root / path
        return path / f"{self.attempt_id}.json"

    def test_start_binds_exact_repository_task_revision_and_base(self) -> None:
        record = self.start()
        self.assertEqual(record["repository"], self.repository)
        self.assertEqual(record["task_id"], self.task_id)
        self.assertEqual(record["task_revision"], self.task_revision)
        self.assertEqual(record["execution_base"], self.base)
        self.assertEqual(record["state"], "RUNNING")
        self.assertEqual(record["authority"], "NONE")

        with self.assertRaisesRegex(ValueError, "repository binding"):
            self.start(
                repository="other/example",
                attempt_id="1123456789abcdef0123456789abcdef",
            )
        with self.assertRaisesRegex(ValueError, "execution_base"):
            self.start(
                execution_base="a" * 40,
                attempt_id="2123456789abcdef0123456789abcdef",
            )
        with self.assertRaisesRegex(ValueError, "task binding"):
            self.start(
                task_revision=2,
                attempt_id="3123456789abcdef0123456789abcdef",
            )

    def test_storage_is_inside_git_metadata_and_does_not_pollute_worktree(self) -> None:
        before = self.git("status", "--porcelain=v1")
        self.start()
        after = self.git("status", "--porcelain=v1")
        git_dir = Path(self.git("rev-parse", "--absolute-git-dir").strip()).resolve()
        path = self.record_path().resolve()
        self.assertEqual(before, "")
        self.assertEqual(after, "")
        self.assertTrue(path.is_file())
        self.assertTrue(path.is_relative_to(git_dir))
        self.assertFalse((self.root / ".gitignore").exists())

    def test_heartbeat_only_refreshes_last_seen(self) -> None:
        original = self.start()
        updated = attempts.heartbeat_attempt(
            self.root, self.attempt_id, now=self.t0 + timedelta(seconds=10)
        )
        changed = {
            key for key in original if original[key] != updated[key]
        }
        self.assertEqual(changed, {"last_seen_at_utc"})
        self.assertEqual(updated["state"], "RUNNING")
        self.assertEqual(updated["authority"], "NONE")

    def test_checkpoint_records_bounded_recovery_hints(self) -> None:
        self.start()
        (self.root / "tracked.txt").write_text("changed\n", encoding="utf-8")
        (self.root / "untracked.txt").write_text("hint\n", encoding="utf-8")
        updated = attempts.checkpoint_attempt(
            self.root,
            self.attempt_id,
            "focused-tests",
            now=self.t0 + timedelta(seconds=15),
        )
        checkpoint = updated["last_checkpoint"]
        self.assertEqual(set(checkpoint), attempts.CHECKPOINT_KEYS)
        self.assertEqual(checkpoint["kind"], "focused-tests")
        self.assertEqual(checkpoint["local_head"], self.base)
        self.assertTrue(checkpoint["tracked_dirty"])
        self.assertEqual(checkpoint["untracked_count"], 1)
        serialized = json.dumps(updated, sort_keys=True).lower()
        for forbidden in (
            "tracked.txt",
            "untracked.txt",
            "diff",
            "prompt",
            "conversation",
            "tool_logs",
            "file_contents",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_active_lease_includes_exact_boundary(self) -> None:
        record = self.start()
        at_boundary = attempts.inspect_record(
            record, now=self.t0 + timedelta(seconds=60)
        )
        self.assertEqual(at_boundary["classification"], "ACTIVE_LEASE")
        self.assertEqual(at_boundary["authority"], "NONE")

    def test_stale_running_attempt_is_interrupted_unknown_only(self) -> None:
        record = self.start()
        stale = attempts.inspect_record(
            record, now=self.t0 + timedelta(seconds=60, microseconds=1)
        )
        self.assertEqual(stale["classification"], "INTERRUPTED_UNKNOWN")
        self.assertEqual(stale["last_seen_at_utc"], record["last_seen_at_utc"])
        self.assertIsNone(stale["terminal_result"])
        self.assertIsNone(stale["terminal_at_utc"])
        lowered = json.dumps(stale, sort_keys=True).lower()
        self.assertNotIn("death_at", lowered)
        self.assertNotIn('"dead"', lowered)
        self.assertNotIn('"failed"', lowered)

    def test_terminal_requires_explicit_marker_and_is_idempotent(self) -> None:
        self.start()
        first = attempts.terminal_attempt(
            self.root,
            self.attempt_id,
            "NEEDS_REVIEW",
            now=self.t0 + timedelta(seconds=20),
        )
        first_bytes = self.record_path().read_bytes()
        second = attempts.terminal_attempt(
            self.root,
            self.attempt_id,
            "NEEDS_REVIEW",
            now=self.t0 + timedelta(seconds=40),
        )
        second_bytes = self.record_path().read_bytes()
        self.assertEqual(first, second)
        self.assertEqual(first_bytes, second_bytes)
        inspected = attempts.inspect_attempt(
            self.root, self.attempt_id, now=self.t0 + timedelta(days=1)
        )
        self.assertEqual(inspected["classification"], "TERMINAL_CONFIRMED")
        self.assertEqual(inspected["terminal_result"], "NEEDS_REVIEW")
        self.assertEqual(
            inspected["terminal_at_utc"], "2026-09-23T12:00:20Z"
        )

        with self.assertRaisesRegex(ValueError, "immutable"):
            attempts.terminal_attempt(
                self.root,
                self.attempt_id,
                "BLOCKED",
                now=self.t0 + timedelta(seconds=50),
            )

    def test_terminal_attempt_never_transitions_back_to_running(self) -> None:
        self.start()
        attempts.terminal_attempt(
            self.root,
            self.attempt_id,
            "NEEDS_REVIEW",
            now=self.t0 + timedelta(seconds=10),
        )
        with self.assertRaisesRegex(ValueError, "cannot return to RUNNING"):
            attempts.heartbeat_attempt(
                self.root, self.attempt_id, now=self.t0 + timedelta(seconds=20)
            )
        with self.assertRaisesRegex(ValueError, "cannot return to RUNNING"):
            attempts.checkpoint_attempt(
                self.root,
                self.attempt_id,
                "later",
                now=self.t0 + timedelta(seconds=20),
            )

    def test_inspect_is_read_only(self) -> None:
        self.start()
        before = self.record_path().read_bytes()
        attempts.inspect_attempt(
            self.root, self.attempt_id, now=self.t0 + timedelta(seconds=10)
        )
        after = self.record_path().read_bytes()
        self.assertEqual(before, after)

    def test_list_current_task_is_exact_and_bounded(self) -> None:
        self.start()
        matches = attempts.list_current_task(
            self.root,
            self.repository,
            self.task_id,
            self.task_revision,
            self.base,
            now=self.t0 + timedelta(seconds=10),
        )
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["attempt_id"], self.attempt_id)
        self.assertEqual(matches[0]["classification"], "ACTIVE_LEASE")
        self.assertEqual(
            attempts.list_current_task(
                self.root,
                self.repository,
                self.task_id,
                self.task_revision,
                "a" * 40,
                now=self.t0,
            ),
            [],
        )

    def test_path_traversal_and_malformed_identity_are_rejected(self) -> None:
        self.start()
        for value in (
            "../" + self.attempt_id,
            self.attempt_id + "/x",
            "not-an-attempt",
            "f" * 33,
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "invalid attempt_id"):
                    attempts.inspect_attempt(self.root, value)

    def test_forbidden_payload_fields_are_rejected(self) -> None:
        record = self.start()
        for field in (
            "secret",
            "token",
            "prompt",
            "conversation",
            "logs",
            "tool_logs",
            "diff",
            "file_contents",
            "file_inventory",
            "report_body",
            "death_at",
        ):
            with self.subTest(field=field):
                bad = copy.deepcopy(record)
                bad[field] = "forbidden"
                with self.assertRaisesRegex(ValueError, "forbidden"):
                    attempts.validate_record(bad)

    def test_authority_none_is_enforced(self) -> None:
        record = self.start()
        bad = copy.deepcopy(record)
        bad["authority"] = "TASK"
        with self.assertRaisesRegex(ValueError, "authority must be NONE"):
            attempts.validate_record(bad)

    def test_backward_time_is_rejected(self) -> None:
        self.start()
        with self.assertRaisesRegex(ValueError, "precedes last_seen"):
            attempts.heartbeat_attempt(
                self.root, self.attempt_id, now=self.t0 - timedelta(seconds=1)
            )

    def test_lease_is_bounded(self) -> None:
        with self.assertRaisesRegex(ValueError, "lease_seconds"):
            self.start(
                lease_seconds=attempts.MIN_LEASE_SECONDS - 1,
                attempt_id="4123456789abcdef0123456789abcdef",
            )
        with self.assertRaisesRegex(ValueError, "lease_seconds"):
            self.start(
                lease_seconds=attempts.MAX_LEASE_SECONDS + 1,
                attempt_id="5123456789abcdef0123456789abcdef",
            )

    def test_cli_inspect_returns_truth_preserving_classification(self) -> None:
        self.start()
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "execution_attempt.py"),
                "--root",
                str(self.root),
                "inspect",
                "--attempt-id",
                self.attempt_id,
            ],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["authority"], "NONE")
        self.assertIn(
            payload["classification"],
            {"ACTIVE_LEASE", "INTERRUPTED_UNKNOWN"},
        )
        self.assertNotIn("death_at", payload)


if __name__ == "__main__":
    unittest.main()
