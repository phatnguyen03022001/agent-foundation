#!/usr/bin/env python3
import copy
import base64
import io
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "profile" / ".agent" / "bootstrap"))

import validate  # noqa: E402

VALIDATOR = ROOT / "profile" / ".agent" / "bootstrap" / "validate.py"
PROFILE_REVISION = "707acfea1f749591621751785b87ae792355a0eb"


class BootstrapContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bootstrap, self.lock = validate.load_contract(ROOT)

    def test_validator_accepts_canonical_bootstrap(self) -> None:
        result = subprocess.run(
            [sys.executable, str(VALIDATOR)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_foundation_repository_contract_is_main_only(self) -> None:
        self.assertEqual(
            self.bootstrap["repository_contract"],
            {
                "repository": "phatnguyen03022001/agent-foundation",
                "topology": "MAIN_ONLY",
                "working_ref": "main",
                "stable_ref": "main",
                "local_policy": "MANAGED_MIRROR",
            },
        )
        self.assertEqual(self.bootstrap["authority_lock"], "profile/.agent/bootstrap/authority.lock.json")
        self.assertEqual(self.bootstrap["bootstrap_default_topology"], "DEV_MAIN")

    def test_legacy_architect_profile_self_identity_fails_closed(self) -> None:
        bootstrap = copy.deepcopy(self.bootstrap)
        bootstrap["repository_contract"].update(
            repository="phatnguyen03022001/architect-profile",
            topology="DEV_MAIN",
            working_ref="dev",
        )
        with self.assertRaisesRegex(ValueError, "agent-foundation MAIN_ONLY identity"):
            validate.validate_contract(bootstrap, self.lock)

    def test_foundation_dev_self_contract_fails_closed(self) -> None:
        bootstrap = copy.deepcopy(self.bootstrap)
        bootstrap["repository_contract"]["working_ref"] = "dev"
        with self.assertRaisesRegex(ValueError, "agent-foundation MAIN_ONLY identity"):
            validate.validate_contract(bootstrap, self.lock)

    def test_duplicate_capability_entrypoint_fails_closed(self) -> None:
        bootstrap = copy.deepcopy(self.bootstrap)
        bootstrap["capability_routes"].append(copy.deepcopy(bootstrap["capability_routes"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate capability"):
            validate.validate_contract(bootstrap, self.lock)

    def resolved_routes(self, foundation_revision: str = PROFILE_REVISION) -> dict:
        foundation_paths = set(validate.required_foundation_paths(self.bootstrap))
        runtime_revision = self.lock["repositories"]["agent-runtime"]["revision"]
        runtime_paths = {
            route["path"]
            for route in self.bootstrap["capability_routes"]
            if route["owner"] == "agent-runtime"
        }
        return {
            "agent-foundation": {
                "revision": foundation_revision,
                "paths": foundation_paths,
            },
            "agent-runtime": {
                "revision": runtime_revision,
                "paths": runtime_paths,
            },
        }

    def resolved_routes_with_router(
        self, router: str, foundation_revision: str = PROFILE_REVISION
    ) -> dict:
        resolved = self.resolved_routes(foundation_revision)
        path = "skills/.agent/case-router.yaml"
        resolved["agent-foundation"]["paths"].add(path)
        resolved["agent-foundation"]["contents"] = {path: router}
        return resolved

    def test_foundation_control_plane_locator_is_canonical(self) -> None:
        self.assertEqual(
            validate.foundation_control_plane_locator(self.bootstrap),
            {
                "owner": "skills",
                "path": "skills/contracts/FOUNDATION_ARCHITECTURE.md",
            },
        )

    def test_foundation_control_plane_locator_fails_closed(self) -> None:
        for value in (
            None,
            {"owner": "skills", "path": "skills/contracts/MISSING.md"},
            {"owner": "agent-skills", "path": "skills/contracts/FOUNDATION_ARCHITECTURE.md"},
        ):
            with self.subTest(value=value):
                bootstrap = copy.deepcopy(self.bootstrap)
                if value is None:
                    bootstrap.pop("foundation_control_plane", None)
                else:
                    bootstrap["foundation_control_plane"] = value
                with self.assertRaisesRegex(ValueError, "foundation_control_plane"):
                    validate.validate_contract(bootstrap, self.lock)

    def test_missing_foundation_control_plane_path_fails_closed(self) -> None:
        with patch.object(Path, "is_file", return_value=False):
            with self.assertRaisesRegex(ValueError, "missing Foundation control-plane path"):
                validate.validate_local_foundation_control_plane(ROOT, self.bootstrap)

    def test_l1_navigation_locators_are_canonical(self) -> None:
        self.assertEqual(
            {
                key: validate.l1_navigation_locator(self.bootstrap, key)
                for key in validate.L1_NAVIGATION
            },
            validate.L1_NAVIGATION,
        )

    def test_execution_continuity_navigation_is_canonical_and_local_state_is_not_bootstrap_authority(self) -> None:
        artifacts = validate.l1_navigation_artifacts(self.bootstrap, PROFILE_REVISION)
        self.assertEqual(
            artifacts["execution_continuity_contract"],
            {
                "repository": "phatnguyen03022001/agent-foundation",
                "revision": PROFILE_REVISION,
                "path": "skills/contracts/EXECUTION_CONTINUITY.md",
            },
        )
        self.assertEqual(
            artifacts["execution_continuity_tool"],
            {
                "repository": "phatnguyen03022001/agent-foundation",
                "revision": PROFILE_REVISION,
                "path": "skills/scripts/execution_attempt.py",
            },
        )
        self.assertFalse(
            any("agent-foundation/execution-attempts" in str(value) for value in self.bootstrap.values())
        )

    def test_l1_navigation_locators_fail_closed(self) -> None:
        for key, expected in validate.L1_NAVIGATION.items():
            with self.subTest(key=key):
                bootstrap = copy.deepcopy(self.bootstrap)
                bootstrap.pop(key, None)
                with self.assertRaisesRegex(ValueError, key):
                    validate.validate_contract(bootstrap, self.lock)

                bootstrap = copy.deepcopy(self.bootstrap)
                bootstrap[key] = dict(expected)
                bootstrap[key]["path"] = "/outside"
                with self.assertRaisesRegex(ValueError, key):
                    validate.validate_contract(bootstrap, self.lock)

    def test_missing_l1_navigation_path_fails_closed(self) -> None:
        with patch.object(Path, "is_file", return_value=False):
            with self.assertRaisesRegex(ValueError, "missing canonical L1 navigation path"):
                validate.validate_local_l1_navigation(ROOT, self.bootstrap)

    def test_missing_l1_navigation_remote_path_fails_closed(self) -> None:
        resolved = self.resolved_routes()
        resolved["agent-foundation"]["paths"].discard("skills/templates/research-request.yaml")
        with self.assertRaisesRegex(ValueError, "missing Foundation canonical path"):
            validate.validate_resolution(self.bootstrap, self.lock, resolved, PROFILE_REVISION)

    def test_external_capability_catalog_locator_is_canonical(self) -> None:
        self.assertEqual(
            validate.external_capability_catalog_locator(self.bootstrap),
            {
                "owner": "skills",
                "path": "skills/.agent/external-capabilities/catalog.json",
            },
        )
        self.assertEqual(
            validate.external_capability_catalog_artifact(self.bootstrap, PROFILE_REVISION),
            {
                "repository": "phatnguyen03022001/agent-foundation",
                "revision": PROFILE_REVISION,
                "path": "skills/.agent/external-capabilities/catalog.json",
            },
        )

    def test_external_capability_catalog_locator_fails_closed(self) -> None:
        for value in (
            None,
            {"owner": "skills", "path": "skills/.agent/external-capabilities/../catalog.json"},
            {"owner": "agent-skills", "path": "skills/.agent/external-capabilities/catalog.json"},
        ):
            with self.subTest(value=value):
                bootstrap = copy.deepcopy(self.bootstrap)
                if value is None:
                    bootstrap.pop("external_capability_catalog", None)
                else:
                    bootstrap["external_capability_catalog"] = value
                with self.assertRaisesRegex(ValueError, "external_capability_catalog"):
                    validate.validate_contract(bootstrap, self.lock)

    def test_missing_external_capability_catalog_path_fails_closed(self) -> None:
        with patch.object(Path, "is_file", return_value=False):
            with self.assertRaisesRegex(ValueError, "missing external capability catalog path"):
                validate.validate_local_external_capability_catalog(ROOT, self.bootstrap)

    def test_malformed_external_capability_catalog_fails_closed(self) -> None:
        with patch.object(Path, "is_file", return_value=True):
            with patch.object(
                validate,
                "load_json",
                return_value={"schema_version": 1, "authority": "ADOPTED", "entries": []},
            ):
                with self.assertRaisesRegex(ValueError, "malformed or authoritative"):
                    validate.validate_local_external_capability_catalog(ROOT, self.bootstrap)

    def test_unresolvable_locked_revision_fails_closed(self) -> None:
        resolved = self.resolved_routes()
        del resolved["agent-runtime"]
        with self.assertRaisesRegex(ValueError, "unresolvable locked revision"):
            validate.validate_resolution(self.bootstrap, self.lock, resolved, PROFILE_REVISION)

    def test_missing_routed_path_fails_closed(self) -> None:
        resolved = self.resolved_routes()
        resolved["agent-foundation"]["paths"].remove("skills/executor/SKILL.md")
        with self.assertRaisesRegex(ValueError, "missing Foundation canonical path"):
            validate.validate_resolution(self.bootstrap, self.lock, resolved, PROFILE_REVISION)

    def test_missing_case_router_path_fails_closed(self) -> None:
        resolved = self.resolved_routes()
        resolved["agent-foundation"]["paths"].discard("skills/.agent/case-router.yaml")
        with self.assertRaisesRegex(ValueError, "missing Foundation canonical path"):
            validate.validate_resolution(self.bootstrap, self.lock, resolved, PROFILE_REVISION)

    def test_missing_external_capability_catalog_remote_path_fails_closed(self) -> None:
        resolved = self.resolved_routes()
        resolved["agent-foundation"]["paths"].discard(
            "skills/.agent/external-capabilities/catalog.json"
        )
        with self.assertRaisesRegex(ValueError, "missing Foundation canonical path"):
            validate.validate_resolution(self.bootstrap, self.lock, resolved, PROFILE_REVISION)

    def test_malformed_case_router_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "malformed Case Router"):
            validate.validate_resolution(
                self.bootstrap,
                self.lock,
                self.resolved_routes_with_router('cases:\\n  - id: EXECUTE\\n    capabilities: executor\\n'),
                PROFILE_REVISION,
            )

    def test_case_router_rejects_unadmitted_case(self) -> None:
        with self.assertRaisesRegex(ValueError, "unauthorized Case Router semantics"):
            validate.validate_resolution(
                self.bootstrap,
                self.lock,
                self.resolved_routes_with_router('cases:\n  - id: REVIEW\n    capabilities:\n      - executor\n'),
                PROFILE_REVISION,
            )

    def test_case_router_rejects_lifecycle_or_dimension_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "malformed Case Router"):
            validate.validate_resolution(
                self.bootstrap,
                self.lock,
                self.resolved_routes_with_router('cases:\\n  - id: EXECUTE\\n    capabilities:\\n      - executor\\n    state: READY\\n'),
                PROFILE_REVISION,
            )

    def test_unknown_case_selection_fails_closed(self) -> None:
        router = {"cases": [{"id": "EXECUTE", "capabilities": ["executor"]}]}
        with self.assertRaisesRegex(ValueError, "unknown case"):
            validate.select_case_capability_routes(self.bootstrap, router, "VERIFY")

    def test_mutable_ref_in_lock_fails_closed(self) -> None:
        lock = copy.deepcopy(self.lock)
        lock["repositories"]["agent-runtime"]["revision"] = "main"
        with self.assertRaisesRegex(ValueError, "invalid immutable revision"):
            validate.validate_contract(self.bootstrap, lock)

    def test_github_json_adds_authorization_when_environment_token_exists(self) -> None:
        token = "bootstrap-test-token"
        with patch.dict(os.environ, {"GITHUB_TOKEN": token}, clear=True):
            with patch.object(
                validate.urllib.request,
                "urlopen",
                return_value=io.BytesIO(b"{}"),
            ) as mocked:
                validate._github_json("https://api.github.com/example")
        request = mocked.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), f"Bearer {token}")

    def test_github_json_omits_authorization_without_environment_token(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(
                validate.urllib.request,
                "urlopen",
                return_value=io.BytesIO(b"{}"),
            ) as mocked:
                validate._github_json("https://api.github.com/example")
        request = mocked.call_args.args[0]
        self.assertIsNone(request.get_header("Authorization"))

    def test_github_json_redacts_environment_token_from_errors(self) -> None:
        token = "bootstrap-never-leak-token"
        with patch.dict(os.environ, {"GITHUB_TOKEN": token}, clear=True):
            with patch.object(
                validate.urllib.request,
                "urlopen",
                side_effect=OSError(f"synthetic failure containing {token}"),
            ):
                with self.assertRaises(ValueError) as caught:
                    validate._github_json("https://api.github.com/example")
        self.assertNotIn(token, str(caught.exception))

    def test_remote_resolution_loads_router_bytes_from_the_locked_tree_blob(self) -> None:
        router = "cases:\n  - id: EXECUTE\n    capabilities:\n      - executor\n"
        router_blob = "c" * 40
        runtime_revision = self.lock["repositories"]["agent-runtime"]["revision"]

        def fake_github_json(url: str) -> dict:
            if f"/git/commits/{PROFILE_REVISION}" in url:
                return {"sha": PROFILE_REVISION, "tree": {"sha": "foundation-tree"}}
            if f"/git/commits/{runtime_revision}" in url:
                return {"sha": runtime_revision, "tree": {"sha": "runtime-tree"}}
            if "/git/trees/foundation-tree?" in url:
                entries = [
                    {"path": path, "sha": f"foundation-{index}"}
                    for index, path in enumerate(sorted(validate.required_foundation_paths(self.bootstrap)))
                ]
                for item in entries:
                    if item["path"] == "skills/.agent/case-router.yaml":
                        item["sha"] = router_blob
                return {"truncated": False, "tree": entries}
            if "/git/trees/runtime-tree?" in url:
                return {"truncated": False, "tree": [{"path": "README.md", "sha": "runtime-readme"}]}
            if url.endswith(f"/git/blobs/{router_blob}"):
                return {"encoding": "base64", "content": base64.b64encode(router.encode()).decode()}
            self.fail(f"unexpected GitHub request: {url}")

        with patch.object(validate, "_github_json", side_effect=fake_github_json):
            resolved = validate.resolve_remote(self.bootstrap, self.lock, PROFILE_REVISION)
        self.assertEqual(
            resolved["agent-foundation"]["contents"]["skills/.agent/case-router.yaml"],
            router,
        )
        self.assertEqual(resolved["agent-foundation"]["revision"], PROFILE_REVISION)
        self.assertEqual(resolved["agent-runtime"]["revision"], runtime_revision)

    def test_unknown_execution_surface_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown execution surface"):
            validate.normalize_surface(self.bootstrap, "CHATGPT", "CLOUD")

    def test_ambiguous_execution_surface_fails_closed(self) -> None:
        bootstrap = copy.deepcopy(self.bootstrap)
        bootstrap["execution_surfaces"][2]["controller"] = "CHATGPT"
        bootstrap["execution_surfaces"][2]["location"] = "LOCAL"
        with self.assertRaisesRegex(ValueError, "ambiguous execution surface"):
            validate.normalize_surface(bootstrap, "CHATGPT", "LOCAL")

    def test_agent_runtime_cannot_be_execution_mode(self) -> None:
        bootstrap = copy.deepcopy(self.bootstrap)
        bootstrap["execution_surfaces"][0]["id"] = "AGENT_RUNTIME"
        with self.assertRaises(ValueError):
            validate.validate_contract(bootstrap, self.lock)

    def test_execution_routes_match_opm02_exactly(self) -> None:
        self.assertEqual(
            {
                surface["id"]: (surface["model"], surface["effort"])
                for surface in self.bootstrap["execution_surfaces"]
            },
            {
                "CHATGPT_GITHUB": ("GPT-5.6 Sol", "HIGH"),
                "CHATGPT_LOCAL": ("GPT-5.6 Sol", "HIGH"),
                "CODEX_CLOUD": ("LUNA", "MEDIUM"),
                "CODEX_LOCAL": ("LUNA", "MEDIUM"),
            },
        )

    def test_unauthorized_model_or_effort_fails_closed(self) -> None:
        cases = (
            (1, "model", "OTHER"),
            (1, "effort", "LOW"),
            (2, "model", "OTHER"),
            (2, "effort", "XHIGH"),
            (3, "effort", "HIGH"),
        )
        for surface_index, field, value in cases:
            with self.subTest(surface_index=surface_index, field=field, value=value):
                bootstrap = copy.deepcopy(self.bootstrap)
                bootstrap["execution_surfaces"][surface_index][field] = value
                with self.assertRaisesRegex(ValueError, "unauthorized execution routing"):
                    validate.validate_contract(bootstrap, self.lock)

    def test_authority_lock_contains_only_external_runtime_authority(self) -> None:
        self.assertEqual(
            self.lock["repositories"],
            {
                "agent-runtime": {
                    "repository": "phatnguyen03022001/agent-runtime",
                    "revision": "ac33afadccf2b222ddf48d6c6b45de82951046a2",
                },
            },
        )

    def test_legacy_internal_revision_selection_aliases_fail_closed(self) -> None:
        for owner in ("architect-profile", "agent-skills", "agent-standards", "agent-documents"):
            with self.subTest(owner=owner):
                lock = copy.deepcopy(self.lock)
                lock["repositories"][owner] = {
                    "repository": "phatnguyen03022001/agent-foundation",
                    "revision": "a" * 40,
                }
                with self.assertRaisesRegex(ValueError, "must not be independently pinned"):
                    validate.validate_contract(self.bootstrap, lock)

    def test_foundation_domains_preserve_semantic_ownership_without_revision_pins(self) -> None:
        routes = {route["capability"]: route for route in self.bootstrap["capability_routes"]}
        self.assertEqual(routes["executor"]["owner"], "skills")
        self.assertEqual(routes["engineering_assurance"]["owner"], "standards")
        self.assertEqual(routes["documentation_closure"]["owner"], "documents")
        self.assertEqual(routes["local_execution_transport"]["owner"], "agent-runtime")
        self.assertEqual(set(self.lock["repositories"]), {"agent-runtime"})
        for capability in (
            "architect",
            "executor",
            "task_protocol",
            "simplicity",
            "github_workflow",
            "verification",
            "engineering_assurance",
            "documentation_closure",
        ):
            self.assertNotIn(routes[capability]["owner"], self.lock["repositories"])

    def test_all_four_surfaces_normalize_uniquely(self) -> None:
        expected = {
            ("CHATGPT", "GITHUB"): "CHATGPT_GITHUB",
            ("CHATGPT", "LOCAL"): "CHATGPT_LOCAL",
            ("CODEX", "CLOUD"): "CODEX_CLOUD",
            ("CODEX", "LOCAL"): "CODEX_LOCAL",
        }
        for key, surface_id in expected.items():
            with self.subTest(controller=key[0], location=key[1]):
                self.assertEqual(validate.normalize_surface(self.bootstrap, *key)["id"], surface_id)

    def test_authority_identity_uses_foundation_main_without_self_pin(self) -> None:
        identity = self.bootstrap["authority_set_identity"]
        self.assertEqual(identity["source"], "AGENT_FOUNDATION_COMMIT")
        self.assertFalse(identity["self_pin"])
        self.assertEqual(identity["evolution_ref"], "main")
        self.assertEqual(identity["activation_ref"], "main")
        self.assertEqual(identity["rollback"], "FORWARD_ACTIVATION_COMMIT")
        self.assertNotIn("architect-profile", self.lock["repositories"])

    def test_target_binding_requires_explicit_current_identity(self) -> None:
        self.assertEqual(
            self.bootstrap["target_binding"],
            {
                "source": "EXPLICIT_CURRENT_REQUEST_OR_EXACT_ACTIVE_BINDING",
                "fresh_github_resolution_required": True,
                "unresolved_action": "ASK_OPERATOR",
                "forbidden_inference_sources": [
                    "STALE_CHAT_HISTORY",
                    "MEMORY",
                    "CWD",
                    "LOCAL_DIRECTORY_NAME",
                ],
                "required_fields": [
                    "repository",
                    "branch",
                    "task_path",
                    "task_revision",
                    "base_head",
                    "phase",
                ],
            },
        )

    def test_prompt_is_rendered_only_from_canonical_locator_inputs(self) -> None:
        inputs = {
            "repository": "owner/repo",
            "branch": "dev",
            "task_path": ".agent/tasks/TASK-0001/task.yaml",
            "task_revision": 2,
            "base_head": "a" * 40,
            "phase": "EXECUTION",
            "surface": "CHATGPT_LOCAL",
        }
        prompt = validate.render_task_prompt(self.bootstrap, inputs)
        self.assertEqual(
            prompt,
            "Target: owner/repo\n"
            "Branch: dev\n"
            "Task: .agent/tasks/TASK-0001/task.yaml\n"
            "Task revision: 2\n"
            f"Exact base HEAD: {'a' * 40}\n"
            "Phase: EXECUTION\n"
            "Execution surface: CHATGPT_LOCAL\n"
            "Resolve the canonical task at the exact base and obey it exactly. "
            "Communicate with the operator in Vietnamese. Persist repository artifacts in English.",
        )

    def test_task_launch_fixtures_render_from_surface_contract(self) -> None:
        fixtures = self.bootstrap["task_launch"]["fixtures"]
        for surface_id, expected in fixtures.items():
            with self.subTest(surface=surface_id):
                self.assertEqual(validate.render_task_launch(self.bootstrap, surface_id, "NEW"), expected)

    def test_fresh_context_reconstruction_is_bounded_and_chat_free(self) -> None:
        target_locator = {
            "repository": "owner/repo",
            "branch": "dev",
            "task_path": ".agent/tasks/TASK-0001/task.yaml",
            "task_revision": 2,
            "base_head": "a" * 40,
            "phase": "EXECUTION",
        }
        result = validate.reconstruct_context(
            root=ROOT,
            profile_revision=PROFILE_REVISION,
            target_locator=target_locator,
            required_capabilities=["executor", "verification"],
            controller="CHATGPT",
            location="LOCAL",
        )
        self.assertEqual(result["authority_set_identity"], PROFILE_REVISION)
        self.assertEqual(result["target_binding"], target_locator)
        self.assertEqual(result["surface"]["id"], "CHATGPT_LOCAL")
        self.assertEqual(result["surface"]["transport"], "AGENT_RUNTIME")
        self.assertEqual(
            [route["capability"] for route in result["capability_routes"]],
            ["executor", "verification"],
        )
        self.assertNotIn("chat_history", result)
        self.assertEqual(
            result["repository_contract"],
            {
                "repository": "phatnguyen03022001/agent-foundation",
                "topology": "MAIN_ONLY",
                "working_ref": "main",
                "stable_ref": "main",
                "local_policy": "MANAGED_MIRROR",
            },
        )

    def test_fresh_context_reconstruction_exposes_the_pre_router_locator(self) -> None:
        target_locator = {
            "repository": "owner/repo",
            "branch": "dev",
            "task_path": ".agent/tasks/TASK-0001/task.yaml",
            "task_revision": 2,
            "base_head": "a" * 40,
            "phase": "EXECUTION",
        }
        result = validate.reconstruct_context(
            root=ROOT,
            profile_revision=PROFILE_REVISION,
            target_locator=target_locator,
            required_capabilities=["executor"],
            controller="CODEX",
            location="LOCAL",
        )
        self.assertIn("case_router", result)
        self.assertEqual(result["foundation_control_plane"]["revision"], PROFILE_REVISION)
        self.assertEqual(result["foundation_control_plane"]["path"], "skills/contracts/FOUNDATION_ARCHITECTURE.md")
        self.assertEqual(result["external_capability_catalog"]["revision"], PROFILE_REVISION)
        self.assertEqual(
            result["external_capability_catalog"]["path"],
            "skills/.agent/external-capabilities/catalog.json",
        )
        self.assertEqual(
            result["l1_navigation"]["research_request_contract"],
            {
                "repository": "phatnguyen03022001/agent-foundation",
                "revision": PROFILE_REVISION,
                "path": "skills/templates/research-request.yaml",
            },
        )
        self.assertEqual(
            result["l1_navigation"]["continuity_root"]["path"],
            "profile/.agent/continuity",
        )

    def test_execution_reconstruction_resolves_execute_from_one_foundation_revision(self) -> None:
        target_locator = {
            "repository": "owner/repo",
            "branch": "dev",
            "task_path": ".agent/tasks/TASK-0018/task.yaml",
            "task_revision": 1,
            "base_head": "a" * 40,
            "phase": "EXECUTION",
        }
        router = "cases:\n  - id: EXECUTE\n    capabilities:\n      - executor\n"
        foundation_revision = "b" * 40
        resolved = self.resolved_routes_with_router(router, foundation_revision)
        result = validate.reconstruct_execution_context(
            ROOT, foundation_revision, target_locator, "EXECUTE", resolved
        )
        self.assertEqual(
            result["bootstrap_trace"],
            ["PROFILE_REVISION", "AUTHORITY_LOCK", "FOUNDATION_CONTROL_PLANE", "CASE_ROUTER", "CASE", "CAPABILITY_ROUTE", "CANONICAL_ARTIFACT"],
        )
        self.assertEqual(result["case"], "EXECUTE")
        self.assertEqual(
            result["external_capability_catalog"],
            {
                "repository": "phatnguyen03022001/agent-foundation",
                "revision": foundation_revision,
                "path": "skills/.agent/external-capabilities/catalog.json",
            },
        )
        self.assertEqual(
            result["canonical_artifacts"],
            [{
                "capability": "executor",
                "repository": "phatnguyen03022001/agent-foundation",
                "revision": foundation_revision,
                "path": "skills/executor/SKILL.md",
            }],
        )
        self.assertNotIn("chat_history", result)
        self.assertNotIn("cwd", result)

    def test_ac9_internal_routes_share_foundation_identity_and_runtime_stays_external(self) -> None:
        foundation_revision = "d" * 40
        router = "cases:\n  - id: EXECUTE\n    capabilities:\n      - executor\n"
        resolved = self.resolved_routes_with_router(router, foundation_revision)
        artifacts = validate.canonical_artifacts(
            foundation_revision,
            self.lock,
            self.bootstrap["capability_routes"],
            resolved,
        )
        internal = [item for item in artifacts if item["repository"] == validate.FOUNDATION_REPOSITORY]
        external = [item for item in artifacts if item["repository"] != validate.FOUNDATION_REPOSITORY]
        self.assertTrue(internal)
        self.assertEqual({item["revision"] for item in internal}, {foundation_revision})
        self.assertEqual(
            {(item["repository"], item["revision"]) for item in external},
            {(
                "phatnguyen03022001/agent-runtime",
                self.lock["repositories"]["agent-runtime"]["revision"],
            )},
        )
        self.assertFalse(set(self.lock["repositories"]) & validate.LEGACY_INTERNAL_OWNER_ALIASES)

    def test_fresh_context_reconstruction_requires_exact_target_locator(self) -> None:
        with self.assertRaisesRegex(ValueError, "target locator"):
            validate.reconstruct_context(
                root=ROOT,
                profile_revision=PROFILE_REVISION,
                target_locator={
                    "branch": "dev",
                    "task_path": ".agent/tasks/TASK-0001/task.yaml",
                    "task_revision": 2,
                    "base_head": "a" * 40,
                    "phase": "EXECUTION",
                },
                required_capabilities=["executor"],
                controller="CHATGPT",
                location="LOCAL",
            )

    def test_generic_role_authority_remains_owned_by_foundation_skills_domain(self) -> None:
        routes = {route["capability"]: route for route in self.bootstrap["capability_routes"]}
        for capability in ("architect", "executor", "task_protocol"):
            with self.subTest(capability=capability):
                self.assertEqual(routes[capability]["owner"], "skills")
                self.assertTrue(routes[capability]["path"].startswith("skills/"))
        for forbidden_key in ("roles", "role_engine", "review_roles", "executor_specializations"):
            self.assertNotIn(forbidden_key, self.bootstrap)



if __name__ == "__main__":
    unittest.main(verbosity=2)
