#!/usr/bin/env python3
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

import research_fanout as research

ROOT = Path(__file__).resolve().parents[1]


class ResearchFanoutTests(unittest.TestCase):
    def request(self) -> dict:
        return research._load_yaml(ROOT / "templates" / "research-request.yaml")

    def result(self) -> dict:
        return research._load_yaml(ROOT / "templates" / "research-result.yaml")

    def write_request(self, root: Path, name: str, document: dict) -> Path:
        source = (ROOT / "templates" / "research-request.yaml").read_text(encoding="utf-8")
        source = source.replace("One bounded research question.", document["question"])
        source = source.replace("README.md", document["context_refs"][0].split(":", 1)[1])
        path = root / name
        path.write_text(source, encoding="utf-8")
        return path

    def test_request_template_is_non_authoritative_and_exactly_bound(self) -> None:
        document = research.validate_request(self.request())
        self.assertEqual(document["authority"], "NONE")
        self.assertTrue(document["read_only"])
        self.assertEqual(document["mutation_authority"], "NONE")
        self.assertEqual(document["decision_authority"], "NONE")
        self.assertEqual(document["peer_results"], [])
        self.assertEqual(len(document["target"]["base_revision"]), 40)
        self.assertEqual(len(research.request_digest(document)), 64)

    def test_request_rejects_peer_results_and_non_exact_base(self) -> None:
        for mutate in (
            lambda doc: doc.update(peer_results=["peer output"]),
            lambda doc: doc["target"].update(base_revision="main"),
            lambda doc: doc.update(mutation_authority="WRITE"),
            lambda doc: doc.update(decision_authority="FINAL"),
        ):
            document = copy.deepcopy(self.request())
            mutate(document)
            with self.assertRaises(ValueError):
                research.validate_request(document)

    def test_context_references_are_bounded_exact_locators(self) -> None:
        document = copy.deepcopy(self.request())
        document["context_refs"] = ["chat history dump"]
        with self.assertRaises(ValueError):
            research.validate_request(document)
        document["context_refs"] = ["owner/repo@0000000000000000000000000000000000000000:../secret"]
        with self.assertRaises(ValueError):
            research.validate_request(document)

    def test_result_template_requires_fact_evidence_and_authority_none(self) -> None:
        document = research.validate_result(self.result())
        self.assertEqual(document["authority"], "NONE")
        self.assertEqual(document["facts"][0]["evidence"], ["E1"])
        broken = copy.deepcopy(document)
        broken["facts"][0]["evidence"] = ["MISSING"]
        with self.assertRaises(ValueError):
            research.validate_result(broken)
        broken = copy.deepcopy(document)
        broken["authority"] = "ADVISORY"
        with self.assertRaises(ValueError):
            research.validate_result(broken)

    def test_three_way_renderer_is_exactly_three_and_standalone(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths: list[Path] = []
            questions = [
                "SENTINEL_ALPHA research question.",
                "SENTINEL_BRAVO research question.",
                "SENTINEL_CHARLIE research question.",
            ]
            for index, question in enumerate(questions, 1):
                document = copy.deepcopy(self.request())
                document["question"] = question
                document["context_refs"] = [
                    f"owner/repo@0000000000000000000000000000000000000000:docs/context-{index}.md"
                ]
                paths.append(self.write_request(root, f"request-{index}.yaml", document))

            packets = research.render_three(paths)
            self.assertEqual(len(packets), 3)
            for index, packet in enumerate(packets):
                self.assertIn(questions[index], packet)
                self.assertIn("Authority: NONE", packet)
                self.assertIn("Architect alone performs final evidence synthesis", packet)
                for other_index, other in enumerate(questions):
                    if other_index != index:
                        self.assertNotIn(other, packet)

            with self.assertRaisesRegex(ValueError, "exactly three"):
                research.render_three(paths[:2])

    def test_repository_role_contract_stays_two_role_and_architect_synthesized(self) -> None:
        architecture = (ROOT / "contracts" / "FOUNDATION_ARCHITECTURE.md").read_text(encoding="utf-8")
        protocol = (ROOT / "protocols" / "TASK_PROTOCOL.md").read_text(encoding="utf-8")
        self.assertIn("exactly two organizational roles: Architect and Executor", architecture)
        self.assertIn("Researcher", architecture)
        self.assertIn("Executor specializations", protocol)
        self.assertNotIn("Researcher role", architecture)


if __name__ == "__main__":
    unittest.main()
