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
                "agents/reviewer.md",
                "commands/run.md",
                "hooks/session-start.sh",
                "scripts/install.sh",
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

    def test_ecc_indexes_only_skills_tree_skill_metadata(self) -> None:
        snapshot = sync.build_snapshot(self.source("ecc"), FakeClient())
        self.assertEqual(
            [item["source_path"] for item in snapshot["entries"]],
            ["skills/good/SKILL.md"],
        )
        self.assertEqual(snapshot["entries"][0]["kind"], "capability")
        serialized = sync.canonical_json(snapshot)
        for forbidden in (
            ".agents/skills/mirror/SKILL.md",
            "agents/reviewer.md",
            "commands/run.md",
            "hooks/session-start.sh",
            "scripts/install.sh",
        ):
            self.assertNotIn(forbidden, serialized)

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
