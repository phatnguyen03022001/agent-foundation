#!/usr/bin/env python3
"""Regression tests for inert external capability indexing and synchronization."""

from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "scripts"))

import sync_external_capabilities as sync  # noqa: E402


class FakeClient:
    def __init__(self) -> None:
        self.fail_tree_for: str | None = None

    def tree(self, repository: str, revision: str) -> list[str]:
        if repository == self.fail_tree_for:
            raise sync.SourceError("synthetic source failure")
        if repository == "affaan-m/ECC":
            return [
                ".agents/skills/mirror/SKILL.md",
                ".claude-plugin/plugin.json",
                "AGENTS.md",
                "CLAUDE.md",
                "agents/reviewer.md",
                "commands/run.md",
                "docs/COMMAND-REGISTRY.json",
                "hooks/session-start.sh",
                "install.sh",
                "manifests/install-components.json",
                "manifests/install-modules.json",
                "manifests/install-profiles.json",
                "scripts/install.js",
                "skills/good/SKILL.md",
            ]
        if repository == "obra/superpowers":
            return [
                ".claude-plugin/plugin.json",
                "hooks/session-start.sh",
                "lib/bootstrap.js",
                "skills/ordinary/SKILL.md",
            ]
        if repository == "mattpocock/skills":
            return [
                ".claude-plugin/plugin.json",
                "skills/engineering/promoted/SKILL.md",
                "skills/misc/not-promoted/SKILL.md",
            ]
        if repository == "sindresorhus/awesome":
            return ["license", "readme.md"]
        raise AssertionError(repository)

    def text(self, repository: str, revision: str, path: str) -> str:
        if repository == "affaan-m/ECC" and path == "skills/good/SKILL.md":
            return "---\nname: good\ndescription: Good ECC capability.\nmetadata:\n  origin: ECC\n---\nbody\n"
        if repository == "affaan-m/ECC" and path == "agents/reviewer.md":
            return "---\nname: reviewer\ndescription: Review implementation evidence.\ntools: Read\n---\nbody\n"
        if repository == "affaan-m/ECC" and path == ".claude-plugin/plugin.json":
            return json.dumps({
                "name": "ecc",
                "version": "2.2.2",
                "description": "fixture",
                "license": "MIT",
                "skills": ["./skills/"],
                "commands": ["./commands/"],
                "userConfig": {"hooks_enabled": {"default": True}},
            })
        if repository == "affaan-m/ECC" and path == "docs/COMMAND-REGISTRY.json":
            return json.dumps({
                "schemaVersion": 1,
                "totalCommands": 1,
                "commands": [{
                    "command": "run",
                    "description": "Run the bounded fixture workflow.",
                    "type": "testing",
                    "primaryAgents": ["reviewer"],
                    "allAgents": ["reviewer"],
                    "skills": ["good"],
                    "path": "commands/run.md",
                }],
            })
        if repository == "affaan-m/ECC" and path == "manifests/install-components.json":
            return json.dumps({
                "version": 1,
                "components": [{
                    "id": "baseline:agents",
                    "family": "baseline",
                    "description": "fixture",
                    "modules": ["agents-core"],
                }],
            })
        if repository == "affaan-m/ECC" and path == "manifests/install-modules.json":
            return json.dumps({
                "version": 1,
                "modules": [{
                    "id": "agents-core",
                    "kind": "agents",
                    "description": "fixture",
                    "paths": ["agents"],
                    "targets": ["codex"],
                    "dependencies": [],
                    "defaultInstall": True,
                    "cost": "light",
                    "stability": "stable",
                }],
            })
        if repository == "affaan-m/ECC" and path == "manifests/install-profiles.json":
            return json.dumps({
                "version": 1,
                "profiles": {
                    "minimal": {
                        "description": "fixture",
                        "modules": ["agents-core"],
                    }
                },
            })
        if repository == "obra/superpowers" and path == ".claude-plugin/plugin.json":
            return json.dumps({
                "name": "superpowers",
                "version": "1.0.0",
                "description": "fixture",
                "license": "MIT",
            })
        if repository == "obra/superpowers" and path == "skills/ordinary/SKILL.md":
            return "---\nname: ordinary\ndescription: Ordinary Superpowers skill.\n---\nbody\n"
        if repository == "mattpocock/skills" and path == ".claude-plugin/plugin.json":
            return json.dumps({
                "name": "mattpocock-skills",
                "version": "1.0.0",
                "license": "MIT",
                "skills": ["./skills/engineering/promoted"],
            })
        if repository == "mattpocock/skills" and path == "skills/engineering/promoted/SKILL.md":
            return "---\nname: promoted\ndescription: Promoted Matt skill.\n---\nbody\n"
        if repository == "sindresorhus/awesome" and path == "readme.md":
            return (
                "# Awesome\n\n"
                "## Testing\n\n"
                "- [Playwright](https://github.com/mxschmitt/awesome-playwright#readme) - Browser testing.\n"
                "## Security\n\n"
                "- [AppSec](https://github.com/paragonie/awesome-appsec#readme)\n"
            )
        raise AssertionError((repository, path))

    def resolve_ref(self, repository: str, tracking_ref: str) -> str:
        mapping = {
            "affaan-m/ECC": "1" * 40,
            "obra/superpowers": "2" * 40,
            "mattpocock/skills": "3" * 40,
            "sindresorhus/awesome": "4" * 40,
        }
        return mapping[repository]


class ExternalCapabilitySyncTests(unittest.TestCase):
    class _Response:
        def __init__(self, body: bytes = b"{}") -> None:
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            return self.body

    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = sync.load_json(sync.REGISTRY_PATH)

    def source(self, source_id: str) -> dict:
        for source in sync.validate_registry(self.registry):
            if source["id"] == source_id:
                return source
        self.fail(source_id)

    def fake_catalog(self) -> dict:
        outputs = sync.build_outputs(self.registry, FakeClient())
        return json.loads(outputs["skills/.agent/external-capabilities/catalog.json"])

    def query_catalog(self, count: int = 6) -> dict:
        catalog = self.fake_catalog()
        template = next(
            entry for entry in catalog["entries"] if entry["id"] == "ecc:good"
        )
        catalog["entries"] = [
            entry for entry in catalog["entries"] if entry["id"] != "ecc:good"
        ]
        for index in range(count):
            entry = copy.deepcopy(template)
            entry["id"] = f"ecc:react-testing-{index}"
            entry["title"] = f"react-testing-{index}"
            entry["description"] = "React component testing patterns."
            entry["source_path"] = f"skills/react-testing-{index}/SKILL.md"
            catalog["entries"].append(entry)
        return catalog

    def test_foundation_routes_generic_how_target_then_ecc_without_authority_transfer(self) -> None:
        architecture = (
            ROOT / "skills" / "contracts" / "FOUNDATION_ARCHITECTURE.md"
        ).read_text(encoding="utf-8")
        architect = (ROOT / "skills" / "architect" / "SKILL.md").read_text(encoding="utf-8")
        executor = (ROOT / "skills" / "executor" / "SKILL.md").read_text(encoding="utf-8")

        ordered = [
            "exact target-repository truth and repo-native conventions;",
            "the exact-pinned ECC harness source",
            "another independently admitted exact external capability",
            "Foundation-internal generic implementation",
        ]
        positions = [architecture.index(token) for token in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("ECC is a reusable L2 harness source, never L0 authority", architecture)
        self.assertIn(
            "only when ECC is materially insufficient or inapplicable;",
            architecture,
        )
        self.assertIn(
            "Load only the minimum relevant surface for the current task.",
            architecture,
        )
        self.assertIn(
            "are never activated merely because ECC is indexed or selected.",
            architecture,
        )
        self.assertIn("The ECC CLI is an optional resolution convenience", architecture)
        self.assertIn(
            "no global install, update, repair, or configuration is required.",
            architecture,
        )
        self.assertIn("Matt skills, Superpowers, and Awesome retain", architecture)

        capability_owner = (
            "[Foundation Architecture — Capability control]"
            "(../contracts/FOUNDATION_ARCHITECTURE.md#capability-control)"
        )
        self.assertIn(capability_owner, architect)
        self.assertIn(
            "after target truth is known and before loading reusable HOW",
            architect,
        )
        self.assertIn(
            "Exact-pinned ECC generic HOW is preferred after target-native conventions; "
            "another exact admitted capability is justified only for a material gap.",
            architect,
        )
        self.assertIn("ECC supplies reusable HOW, never authority.", architect)

        self.assertIn(capability_owner, executor)
        self.assertIn(
            "after target truth establishes a material need",
            executor,
        )
        self.assertIn(
            "load only the minimum exact-pinned capability",
            executor,
        )
        self.assertIn(
            "Exact-pinned ECC is default generic HOW after repo-native conventions; "
            "another admitted capability requires a material ECC gap.",
            executor,
        )
        self.assertIn(
            "Never install/update/repair/configure ECC merely for routing.",
            executor,
        )

    def test_github_client_adds_authorization_when_environment_token_exists(self) -> None:
        token = "test-token-value"
        requests = []

        def fake_urlopen(request, timeout):
            requests.append(request)
            self.assertEqual(timeout, 30)
            return self._Response()

        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": token}, clear=True):
            with mock.patch.object(sync.urllib.request, "urlopen", side_effect=fake_urlopen):
                sync.GitHubClient()._request("https://api.github.com/example")

        self.assertEqual(requests[0].get_header("Authorization"), f"Bearer {token}")

    def test_github_client_omits_authorization_without_environment_token(self) -> None:
        requests = []

        def fake_urlopen(request, timeout):
            requests.append(request)
            self.assertEqual(timeout, 30)
            return self._Response()

        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(sync.urllib.request, "urlopen", side_effect=fake_urlopen):
                sync.GitHubClient()._request("https://api.github.com/example")

        self.assertIsNone(requests[0].get_header("Authorization"))

    def test_github_token_is_redacted_from_errors_and_absent_from_generated_outputs(self) -> None:
        token = "never-persist-this-token"

        def fail_urlopen(request, timeout):
            raise OSError(f"synthetic failure containing {token}")

        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": token}, clear=True):
            with mock.patch.object(sync.urllib.request, "urlopen", side_effect=fail_urlopen):
                with self.assertRaises(sync.SourceError) as caught:
                    sync.GitHubClient()._request("https://api.github.com/example")
            outputs = sync.build_outputs(self.registry, FakeClient())

        self.assertNotIn(token, str(caught.exception))
        self.assertNotIn(token, "".join(outputs.values()))

    def test_registry_is_exactly_the_four_authorized_baselines(self) -> None:
        sources = {item["id"]: item for item in sync.validate_registry(self.registry)}
        self.assertEqual(set(sources), {"ecc", "superpowers", "matt-skills", "awesome"})
        self.assertEqual(
            sources["ecc"]["snapshot_revision"],
            "bf70150eb2df8070024e5bdf08e4aa08959e2735",
        )
        self.assertEqual(sources["ecc"]["kind"], "harness_source")
        self.assertEqual(sources["ecc"]["indexing_policy"], sync.ECC_INDEXING_POLICY)
        self.assertEqual(
            sources["superpowers"]["snapshot_revision"],
            "5bf4e78011075bcfc0dc295f0724994cd123ee71",
        )
        self.assertEqual(
            sources["matt-skills"]["snapshot_revision"],
            "c55ee46073ed923f86ce59a5eb3b6d895095d1b7",
        )
        self.assertEqual(
            sources["awesome"]["snapshot_revision"],
            "bc98e517ddca672f55f9857d714fc3ea3c3540b2",
        )

    def test_ecc_indexes_deterministic_harness_surfaces_without_activation(self) -> None:
        snapshot = sync.build_snapshot(self.source("ecc"), FakeClient())
        entries = {item["id"]: item for item in snapshot["entries"]}
        self.assertEqual(
            {
                entry["surface"]
                for entry in entries.values()
            },
            {"skill", "command", "agent"},
        )
        self.assertEqual(entries["ecc:good"]["source_path"], "skills/good/SKILL.md")
        self.assertEqual(entries["ecc:good"]["surface"], "skill")
        self.assertEqual(entries["ecc:command:run"]["source_path"], "commands/run.md")
        self.assertEqual(entries["ecc:command:run"]["surface"], "command")
        self.assertEqual(
            entries["ecc:command:run"]["invocation"]["declared_by"],
            "docs/COMMAND-REGISTRY.json",
        )
        self.assertEqual(entries["ecc:agent:reviewer"]["source_path"], "agents/reviewer.md")
        self.assertEqual(entries["ecc:agent:reviewer"]["surface"], "agent")

        harness = snapshot["source_metadata"]["harness"]
        self.assertEqual(
            harness["surface_counts"],
            {"agents": 1, "commands": 1, "skills": 1},
        )
        self.assertFalse(harness["cli_required"])
        self.assertEqual(harness["activation"], "inert_metadata_only")
        self.assertEqual(
            harness["plugin_manifest"]["declared_surfaces"],
            {"commands": ["./commands/"], "skills": ["./skills/"]},
        )
        self.assertEqual(harness["command_registry"]["total_commands"], 1)
        self.assertEqual(
            set(harness["install_metadata"]),
            {"components", "modules", "profiles"},
        )

        serialized_entries = sync.canonical_json(snapshot["entries"])
        for forbidden in (
            ".agents/skills/mirror/SKILL.md",
            "AGENTS.md",
            "CLAUDE.md",
            "hooks/session-start.sh",
            "install.sh",
            "scripts/install.js",
        ):
            self.assertNotIn(forbidden, serialized_entries)

    def test_ecc_registry_rejects_mutable_incomplete_or_activation_policy(self) -> None:
        mutable = copy.deepcopy(self.registry)
        ecc = next(item for item in mutable["sources"] if item["id"] == "ecc")
        ecc["snapshot_revision"] = "main"
        with self.assertRaisesRegex(sync.SourceError, "immutable 40-hex"):
            sync.validate_registry(mutable)

        incomplete = copy.deepcopy(self.registry)
        ecc = next(item for item in incomplete["sources"] if item["id"] == "ecc")
        ecc["indexing_policy"]["metadata"] = ecc["indexing_policy"]["metadata"][:-1]
        with self.assertRaisesRegex(sync.SourceError, "unauthorized indexing policy"):
            sync.validate_registry(incomplete)

        activating = copy.deepcopy(self.registry)
        ecc = next(item for item in activating["sources"] if item["id"] == "ecc")
        ecc["indexing_policy"]["activate_hooks"] = True
        with self.assertRaisesRegex(sync.SourceError, "unauthorized indexing policy"):
            sync.validate_registry(activating)

    def test_ecc_resolution_uses_exact_pinned_metadata_without_cli(self) -> None:
        outputs = sync.build_outputs(self.registry, FakeClient())
        catalog = json.loads(outputs["skills/.agent/external-capabilities/catalog.json"])
        with mock.patch.dict(os.environ, {"PATH": ""}, clear=False):
            resolved = sync.resolve_harness_entry(
                self.registry,
                catalog,
                source_id="ecc",
                surface="command",
                title="run",
            )
        self.assertEqual(resolved["id"], "ecc:command:run")
        self.assertEqual(
            resolved["revision"],
            "bf70150eb2df8070024e5bdf08e4aa08959e2735",
        )

    def test_ecc_resolution_fails_closed_for_missing_or_wrong_surface(self) -> None:
        outputs = sync.build_outputs(self.registry, FakeClient())
        catalog = json.loads(outputs["skills/.agent/external-capabilities/catalog.json"])
        with self.assertRaisesRegex(sync.SourceError, "exactly one pinned harness entry"):
            sync.resolve_harness_entry(
                self.registry,
                catalog,
                source_id="ecc",
                surface="skill",
                title="missing",
            )
        with self.assertRaisesRegex(sync.SourceError, "exactly one pinned harness entry"):
            sync.resolve_harness_entry(
                self.registry,
                catalog,
                source_id="ecc",
                surface="agent",
                title="run",
            )

    def test_ecc_query_returns_bounded_deterministic_inert_metadata(self) -> None:
        query = getattr(sync, "query_harness_entries", None)
        self.assertIsNotNone(query, "query_harness_entries must expose bounded discovery")
        catalog = self.query_catalog()
        result = query(
            self.registry,
            catalog,
            source_id="ecc",
            terms=["ReAcT", "testing"],
            surface="skill",
            limit=5,
        )
        self.assertEqual(result["authority"], "NONE")
        self.assertEqual(
            result["source"],
            {
                "id": "ecc",
                "repository": "affaan-m/ECC",
                "revision": "bf70150eb2df8070024e5bdf08e4aa08959e2735",
            },
        )
        self.assertEqual(
            result["query"],
            {"terms": ["ReAcT", "testing"], "surface": "skill", "limit": 5},
        )
        self.assertEqual(result["total_matches"], 6)
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["entries"]), 5)
        self.assertEqual(
            [entry["title"] for entry in result["entries"]],
            [f"react-testing-{index}" for index in range(5)],
        )
        self.assertEqual(
            result["entries"][0],
            next(
                entry
                for entry in catalog["entries"]
                if entry["id"] == "ecc:react-testing-0"
            ),
        )

    def test_ecc_query_reports_zero_and_multiple_matches_without_selection(self) -> None:
        catalog = self.query_catalog(count=2)
        multiple = sync.query_harness_entries(
            self.registry,
            catalog,
            source_id="ecc",
            terms=["react"],
            surface=None,
            limit=5,
        )
        self.assertEqual(multiple["total_matches"], 2)
        self.assertFalse(multiple["truncated"])
        self.assertNotIn("selected", multiple)

        empty = sync.query_harness_entries(
            self.registry,
            catalog,
            source_id="ecc",
            terms=["does-not-exist"],
            surface="skill",
            limit=5,
        )
        self.assertEqual(empty["total_matches"], 0)
        self.assertEqual(empty["entries"], [])
        self.assertFalse(empty["truncated"])

    def test_ecc_query_rejects_invalid_input(self) -> None:
        catalog = self.query_catalog()
        cases = [
            {"terms": [], "surface": None, "limit": 5},
            {"terms": [""], "surface": None, "limit": 5},
            {"terms": ["react"], "surface": "unknown", "limit": 5},
            {"terms": ["react"], "surface": None, "limit": 0},
            {"terms": ["react"], "surface": None, "limit": 11},
        ]
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(sync.SourceError):
                    sync.query_harness_entries(
                        self.registry,
                        catalog,
                        source_id="ecc",
                        **case,
                    )
        with self.assertRaises(sync.SourceError):
            sync.query_harness_entries(
                self.registry,
                catalog,
                source_id="awesome",
                terms=["testing"],
                surface=None,
                limit=5,
            )

    def test_ecc_query_and_resolution_fail_closed_on_bad_relevant_metadata(self) -> None:
        base = self.query_catalog(count=2)
        mutations = []

        stale_provenance = copy.deepcopy(base)
        next(
            item
            for item in stale_provenance["generated_from"]
            if item["id"] == "ecc"
        )["revision"] = "0" * 40
        mutations.append(stale_provenance)

        stale_entry = copy.deepcopy(base)
        next(
            item for item in stale_entry["entries"] if item["source"] == "ecc"
        )["revision"] = "0" * 40
        mutations.append(stale_entry)

        unsafe_path = copy.deepcopy(base)
        next(
            item for item in unsafe_path["entries"] if item["source"] == "ecc"
        )["source_path"] = "../escape.md"
        mutations.append(unsafe_path)

        malformed = copy.deepcopy(base)
        next(
            item for item in malformed["entries"] if item["source"] == "ecc"
        )["description"] = None
        mutations.append(malformed)

        duplicate = copy.deepcopy(base)
        duplicate["entries"].append(copy.deepcopy(
            next(item for item in duplicate["entries"] if item["source"] == "ecc")
        ))
        mutations.append(duplicate)

        for catalog in mutations:
            with self.subTest(catalog=catalog):
                with self.assertRaises(sync.SourceError):
                    sync.query_harness_entries(
                        self.registry,
                        catalog,
                        source_id="ecc",
                        terms=["react"],
                        surface=None,
                        limit=5,
                    )
                with self.assertRaises(sync.SourceError):
                    sync.resolve_harness_entry(
                        self.registry,
                        catalog,
                        source_id="ecc",
                        surface="skill",
                        title="react-testing-0",
                    )

    def test_query_and_resolve_cli_are_offline_read_only(self) -> None:
        catalog = self.query_catalog(count=2)

        def fake_load(path):
            if path == sync.REGISTRY_PATH:
                return copy.deepcopy(self.registry)
            if path == sync.CATALOG_PATH:
                return copy.deepcopy(catalog)
            raise AssertionError(path)

        with mock.patch.dict(os.environ, {"PATH": ""}, clear=False):
            with mock.patch.object(sync, "load_json", side_effect=fake_load):
                with mock.patch.object(
                    sync, "GitHubClient", side_effect=AssertionError("network forbidden")
                ):
                    with mock.patch.object(
                        sync.urllib.request,
                        "urlopen",
                        side_effect=AssertionError("network forbidden"),
                    ):
                        with mock.patch.object(
                            Path,
                            "write_text",
                            side_effect=AssertionError("write forbidden"),
                        ):
                            with mock.patch("builtins.print") as printer:
                                self.assertEqual(
                                    sync.main([
                                        "--query",
                                        "react",
                                        "testing",
                                        "--surface",
                                        "skill",
                                        "--limit",
                                        "1",
                                    ]),
                                    0,
                                )
                                query_payload = json.loads(printer.call_args.args[0])
                                self.assertEqual(query_payload["total_matches"], 2)
                                self.assertTrue(query_payload["truncated"])

                            with mock.patch("builtins.print") as printer:
                                self.assertEqual(
                                    sync.main([
                                        "--resolve",
                                        "--source",
                                        "ecc",
                                        "--surface",
                                        "skill",
                                        "--title",
                                        "react-testing-0",
                                    ]),
                                    0,
                                )
                                resolved = json.loads(printer.call_args.args[0])
                                self.assertEqual(
                                    resolved["id"],
                                    "ecc:react-testing-0",
                                )

    def test_cli_distinguishes_omitted_defaults_from_explicit_empty_options(self) -> None:
        catalog = self.query_catalog(count=2)

        def fake_load(path):
            if path == sync.REGISTRY_PATH:
                return copy.deepcopy(self.registry)
            if path == sync.CATALOG_PATH:
                return copy.deepcopy(catalog)
            raise AssertionError(path)

        with mock.patch.dict(os.environ, {"PATH": ""}, clear=False):
            with mock.patch.object(sync, "load_json", side_effect=fake_load):
                with mock.patch.object(
                    sync, "GitHubClient", side_effect=AssertionError("network forbidden")
                ):
                    with mock.patch.object(
                        Path,
                        "write_text",
                        side_effect=AssertionError("write forbidden"),
                    ):
                        valid_cases = [
                            ["--query", "react"],
                            ["--query", "react", "--source", "ecc"],
                            [
                                "--resolve",
                                "--surface",
                                "skill",
                                "--title",
                                "react-testing-0",
                            ],
                            [
                                "--resolve",
                                "--source",
                                "ecc",
                                "--surface",
                                "skill",
                                "--title",
                                "react-testing-0",
                            ],
                        ]
                        for argv in valid_cases:
                            with self.subTest(valid=argv):
                                with mock.patch("builtins.print"):
                                    self.assertEqual(sync.main(argv), 0)

                        invalid_cases = [
                            ["--query", "react", "--source", ""],
                            [
                                "--resolve",
                                "--source",
                                "",
                                "--surface",
                                "skill",
                                "--title",
                                "react-testing-0",
                            ],
                            ["--query", "react", "--title", ""],
                            ["--check", "--task", ""],
                            ["--query", "react", "--task", ""],
                            [
                                "--resolve",
                                "--surface",
                                "skill",
                                "--title",
                                "react-testing-0",
                                "--task",
                                "",
                            ],
                        ]
                        for argv in invalid_cases:
                            with self.subTest(invalid=argv):
                                with mock.patch("builtins.print") as printer:
                                    self.assertEqual(sync.main(argv), 2)
                                    self.assertFalse(
                                        any(
                                            call.args
                                            and isinstance(call.args[0], str)
                                            and call.args[0].lstrip().startswith("{")
                                            for call in printer.call_args_list
                                        )
                                    )

    def test_new_cli_modes_preserve_refresh_authorization_gate(self) -> None:
        with mock.patch.object(sync, "GitHubClient", return_value=FakeClient()):
            self.assertEqual(sync.main(["--refresh"]), 2)
            self.assertEqual(
                sync.main(["--check", "--task", ".agent/tasks/TASK-0029/task.yaml"]),
                2,
            )

    def test_superpowers_preserves_plugin_and_behavioral_surface_facts_without_indexing_them(self) -> None:
        snapshot = sync.build_snapshot(self.source("superpowers"), FakeClient())
        self.assertEqual(
            [item["source_path"] for item in snapshot["entries"]],
            ["skills/ordinary/SKILL.md"],
        )
        self.assertEqual(snapshot["source_metadata"]["plugin_manifest"]["name"], "superpowers")
        self.assertEqual(
            snapshot["source_metadata"]["non_capability_behavioral_surfaces"],
            ["hooks/session-start.sh", "lib/bootstrap.js"],
        )

    def test_matt_indexes_only_manifest_promoted_inventory(self) -> None:
        snapshot = sync.build_snapshot(self.source("matt-skills"), FakeClient())
        self.assertEqual(
            [item["source_path"] for item in snapshot["entries"]],
            ["skills/engineering/promoted/SKILL.md"],
        )
        self.assertEqual(snapshot["entries"][0]["status"], "promoted")
        self.assertEqual(
            snapshot["entries"][0]["invocation"],
            {"declared_by": ".claude-plugin/plugin.json"},
        )

    def test_awesome_is_discovery_only_and_rejected_as_capability(self) -> None:
        snapshot = sync.build_snapshot(self.source("awesome"), FakeClient())
        self.assertEqual({item["kind"] for item in snapshot["entries"]}, {"discovery"})
        self.assertEqual({item["category"] for item in snapshot["entries"]}, {"Testing", "Security"})
        with self.assertRaisesRegex(sync.SourceError, "not an admitted capability"):
            sync.require_capability_entry(snapshot["entries"][0])

    def test_aggregate_generation_is_deterministic_and_separates_entry_kinds(self) -> None:
        first = sync.build_outputs(self.registry, FakeClient())
        second = sync.build_outputs(copy.deepcopy(self.registry), FakeClient())
        self.assertEqual(first, second)
        catalog = json.loads(first["skills/.agent/external-capabilities/catalog.json"])
        self.assertEqual(catalog["authority"], "NONE")
        self.assertEqual(
            {item["kind"] for item in catalog["entries"]},
            {"capability", "discovery"},
        )
        self.assertEqual(
            [item["id"] for item in catalog["entries"]],
            sorted(item["id"] for item in catalog["entries"]),
        )

    def test_refresh_resolves_all_tracking_refs_without_changing_source_authority_shape(self) -> None:
        refreshed = sync.refreshed_registry(self.registry, FakeClient())
        sources = {item["id"]: item for item in sync.validate_registry(refreshed)}
        self.assertEqual(sources["ecc"]["snapshot_revision"], "1" * 40)
        self.assertEqual(sources["superpowers"]["snapshot_revision"], "2" * 40)
        self.assertEqual(sources["matt-skills"]["snapshot_revision"], "3" * 40)
        self.assertEqual(sources["awesome"]["snapshot_revision"], "4" * 40)
        self.assertEqual(set(refreshed), {"schema_version", "sources"})

    def test_refresh_authority_fails_closed_without_exact_foundation_scope(self) -> None:
        valid = {
            "state": "APPROVED",
            "execution_ready": True,
            "target": {
                "repository": "phatnguyen03022001/agent-foundation",
                "branch": {"name": "main"},
            },
            "scope": {
                "required_changes": [
                    "Refresh skills/.agent/external-capabilities metadata."
                ]
            },
        }
        sync.validate_refresh_authority(valid)
        with self.assertRaises(sync.SourceError):
            sync.validate_refresh_authority(
                {
                    **valid,
                    "target": {
                        "repository": "other/repo",
                        "branch": {"name": "main"},
                    },
                },
            )
        unrelated = copy.deepcopy(valid)
        unrelated["scope"]["required_changes"] = ["Update unrelated documentation."]
        with self.assertRaises(sync.SourceError):
            sync.validate_refresh_authority(unrelated)

    def test_network_or_source_failure_is_fail_closed_before_write(self) -> None:
        client = FakeClient()
        client.fail_tree_for = "affaan-m/ECC"
        with self.assertRaisesRegex(sync.SourceError, "synthetic source failure"):
            sync.build_outputs(self.registry, client)

    def test_malformed_skill_metadata_fails_closed(self) -> None:
        with self.assertRaisesRegex(sync.SourceError, "requires name and description"):
            sync.parse_frontmatter("---\nname: missing-description\n---\n", "skills/x/SKILL.md")

    def test_write_boundary_rejects_any_unlisted_output(self) -> None:
        outputs = sync.build_outputs(self.registry, FakeClient())
        outputs["README.md"] = "forbidden"
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(sync.SourceError, "escaped"):
                sync.write_outputs(outputs, Path(temp))

    def test_committed_catalog_rejects_awesome_as_capability_candidate(self) -> None:
        catalog = json.loads(sync.CATALOG_PATH.read_text(encoding="utf-8"))
        awesome = next(item for item in catalog["entries"] if item["source"] == "awesome")
        with self.assertRaises(sync.SourceError):
            sync.require_capability_entry(awesome)


if __name__ == "__main__":
    unittest.main(verbosity=2)
