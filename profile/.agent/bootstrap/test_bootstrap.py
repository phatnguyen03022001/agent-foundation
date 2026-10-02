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

    def test_legacy_execute_case_router_normalizes_only_to_task_execution(self) -> None:
        router = validate.parse_case_router(
            "cases:\n  - id: EXECUTE\n    capabilities:\n      - executor\n"
        )
        validate.validate_case_router(router)
        selected = validate.select_semantic_route(router, "EXECUTE")
        self.assertEqual(selected["route"]["id"], "TASK_EXECUTION")
        self.assertEqual(selected["disposition"], "LEGACY_EXECUTE_COMPATIBILITY")
        with self.assertRaisesRegex(ValueError, "supports only EXECUTE task compatibility"):
            validate.select_semantic_route(router, "MATERIAL_JUDGMENT")

    def test_malformed_case_router_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "malformed Case Router"):
            validate.validate_resolution(
                self.bootstrap,
                self.lock,
                self.resolved_routes_with_router('cases:\\n  - id: EXECUTE\\n    capabilities: executor\\n'),
                PROFILE_REVISION,
            )

    def test_case_router_rejects_unadmitted_case(self) -> None:
        router = (ROOT / "skills/.agent/case-router.yaml").read_text(encoding="utf-8")
        router = router.replace("id: MATERIAL_JUDGMENT", "id: REVIEW", 1)
        with self.assertRaisesRegex(ValueError, "unauthorized Case Router semantics"):
            validate.validate_resolution(
                self.bootstrap,
                self.lock,
                self.resolved_routes_with_router(router),
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
        router = validate.parse_case_router(
            (ROOT / "skills/.agent/case-router.yaml").read_text(encoding="utf-8")
        )
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
        legacy_router = validate.parse_case_router(router)
        validate.validate_case_router(legacy_router)
        self.assertEqual(
            validate.select_semantic_route(legacy_router, "EXECUTE")["route"]["id"],
            "TASK_EXECUTION",
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
                    "revision": "2044df229a278bc36f9244cd2add54c9a0b28061",
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
                "generic_required_fields": ["repository", "branch"],
                "task_bound_required_fields": ["task_path", "task_revision", "base_head", "phase"],
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

    def test_task_launch_fixtures_render_all_chat_task_pairs_from_surface_contract(self) -> None:
        fixtures = self.bootstrap["task_launch"]["fixtures"]
        rendered = 0
        for surface_id, chat_fixtures in fixtures.items():
            for chat_action, task_fixtures in chat_fixtures.items():
                for task_action, expected in task_fixtures.items():
                    with self.subTest(
                        surface=surface_id,
                        chat_action=chat_action,
                        task_action=task_action,
                    ):
                        self.assertEqual(
                            validate.render_task_launch(
                                self.bootstrap,
                                surface_id,
                                chat_action,
                                task_action,
                            ),
                            expected,
                        )
                        rendered += 1
        self.assertEqual(rendered, 16)

    def test_task_launch_rejects_bare_crossed_and_unknown_action_axes(self) -> None:
        invalid_pairs = (
            ("NEW", "NEW TASK"),
            ("NEW CHAT", "CONTINUE"),
            ("NEW TASK", "NEW CHAT"),
            ("CONTINUE TASK", "CONTINUE CHAT"),
            ("UNKNOWN CHAT", "NEW TASK"),
            ("NEW CHAT", "UNKNOWN TASK"),
        )
        for chat_action, task_action in invalid_pairs:
            with self.subTest(chat_action=chat_action, task_action=task_action):
                with self.assertRaisesRegex(ValueError, "action"):
                    validate.render_task_launch(
                        self.bootstrap,
                        "CHATGPT_LOCAL",
                        chat_action,
                        task_action,
                    )

    def test_task_launch_malformed_action_configuration_fails_closed(self) -> None:
        bootstrap = copy.deepcopy(self.bootstrap)
        bootstrap["task_launch"]["chat_actions"] = ["NEW", "CONTINUE"]
        with self.assertRaisesRegex(ValueError, "chat_actions"):
            validate.validate_contract(bootstrap, self.lock)

        bootstrap = copy.deepcopy(self.bootstrap)
        del bootstrap["task_launch"]["fixtures"]["CHATGPT_LOCAL"]["NEW CHAT"]["NEW TASK"]
        with self.assertRaisesRegex(ValueError, "fixture"):
            validate.validate_contract(bootstrap, self.lock)

    def test_fresh_context_reconstruction_is_bounded_and_chat_free(self) -> None:
        target_binding = {"repository": "owner/repo", "branch": "dev"}
        result = self._resolve_entry(target_binding, "READ_ONLY_RESEARCH")
        self.assertEqual(result["authority_set_identity"], PROFILE_REVISION)
        self.assertEqual(result["authority"], "NONE")
        self.assertEqual(result["target_binding"], target_binding)
        self.assertEqual(result["surface"]["id"], "CHATGPT_LOCAL")
        self.assertEqual(result["surface"]["transport"], "AGENT_RUNTIME")
        self.assertEqual(
            [route["capability"] for route in result["capability_routes"]],
            ["executor"],
        )
        self.assertEqual(
            set(result["l1_navigation"]),
            {"research_request_contract", "research_result_contract"},
        )
        self.assertNotIn("chat_history", result)
        self.assertNotIn("external_capability_catalog", result)

    def test_fresh_context_reconstruction_exposes_only_the_selected_route(self) -> None:
        target_binding = {"repository": "owner/repo", "branch": "dev"}
        result = self._resolve_entry(target_binding, "MATERIAL_JUDGMENT")
        self.assertIn("case_router", result)
        self.assertEqual(result["entry_route"], "MATERIAL_JUDGMENT")
        self.assertEqual(result["role"], "architect")
        self.assertEqual(
            [route["capability"] for route in result["capability_routes"]],
            ["architect"],
        )
        self.assertEqual(result["l1_navigation"], {})
        self.assertNotIn("foundation_control_plane", result)
        self.assertNotIn("external_capability_catalog", result)
        self.assertNotIn("repository_contract", result)

    def test_execution_reconstruction_resolves_execute_from_one_foundation_revision(self) -> None:
        target_locator = {
            "repository": "owner/repo",
            "branch": "dev",
            "task_path": ".agent/tasks/TASK-0018/task.yaml",
            "task_revision": 1,
            "base_head": "a" * 40,
            "phase": "EXECUTION",
        }
        router = (ROOT / "skills/.agent/case-router.yaml").read_text(encoding="utf-8")
        foundation_revision = "b" * 40
        resolved = self.resolved_routes_with_router(router, foundation_revision)
        with patch.object(validate, "resolve_target_branch", return_value={
            "repository": "owner/repo", "branch": "dev", "head": target_locator["base_head"]
        }):
            result = validate.reconstruct_execution_context(
                ROOT, foundation_revision, target_locator, "EXECUTE", resolved
            )
        self.assertEqual(
            result["bootstrap_trace"],
            ["PROFILE_REVISION", "AUTHORITY_LOCK", "TARGET_BINDING", "CASE_ROUTER", "SEMANTIC_ROUTE", "CAPABILITY_ROUTE", "CANONICAL_ARTIFACT"],
        )
        self.assertEqual(result["case"], "TASK_EXECUTION")
        self.assertEqual(result["entry_route"], "TASK_EXECUTION")
        self.assertEqual(result["role"], "executor")
        self.assertNotIn("external_capability_catalog", result)
        self.assertEqual(
            [item["capability"] for item in result["capability_routes"]],
            ["executor", "task_protocol"],
        )
        self.assertEqual(
            result["canonical_artifacts"],
            [
                {
                    "capability": "executor",
                    "repository": "phatnguyen03022001/agent-foundation",
                    "revision": foundation_revision,
                    "path": "skills/executor/SKILL.md",
                },
                {
                    "capability": "task_protocol",
                    "repository": "phatnguyen03022001/agent-foundation",
                    "revision": foundation_revision,
                    "path": "skills/protocols/TASK_PROTOCOL.md",
                },
            ],
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

    def test_fresh_context_reconstruction_requires_generic_target_identity(self) -> None:
        with self.assertRaisesRegex(ValueError, "generic target binding"):
            validate.reconstruct_entry_context(
                root=ROOT,
                profile_revision=PROFILE_REVISION,
                target_binding={"branch": "dev"},
                request_identity="request-1",
                entry_intent="MATERIAL_JUDGMENT",
                resolved=self._entry_resolved(),
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



    def _entry_resolved(self, foundation_revision: str = PROFILE_REVISION) -> dict:
        router = (ROOT / "skills/.agent/case-router.yaml").read_text(encoding="utf-8")
        return self.resolved_routes_with_router(router, foundation_revision)

    def _resolve_entry(
        self,
        target_binding: dict,
        entry_intent: object,
        request_identity: str | None = "request-1",
    ) -> dict:
        resolved_head = target_binding.get("base_head", "c" * 40)
        resolved_target = {
            "repository": target_binding["repository"],
            "branch": target_binding["branch"],
            "head": resolved_head,
        }
        with patch.object(validate, "resolve_target_branch", return_value=resolved_target):
            return validate.reconstruct_entry_context(
                root=ROOT,
                profile_revision=PROFILE_REVISION,
                target_binding=target_binding,
                request_identity=request_identity,
                entry_intent=entry_intent,
                controller="CHATGPT",
                location="LOCAL",
                resolved=self._entry_resolved(),
            )

    def test_material_judgment_uses_generic_binding_and_loads_only_architect_route(self) -> None:
        target = {"repository": "owner/repo", "branch": "main"}
        resolved = self._entry_resolved()
        target_head = "c" * 40
        loaded: list[str] = []
        original_load_json = validate.load_json

        def observe_json(path: Path) -> dict:
            loaded.append(path.relative_to(ROOT).as_posix())
            return original_load_json(path)

        with patch.object(validate, "resolve_target_branch", return_value={
            "repository": "owner/repo", "branch": "main", "head": target_head
        }) as target_resolver, patch.object(
            validate, "validate_local_external_capability_catalog",
            side_effect=AssertionError("route selection must not read the external catalog")
        ), patch.object(
            validate, "validate_local_foundation_control_plane",
            side_effect=AssertionError("route selection must not load Foundation Architecture")
        ), patch.object(
            validate, "validate_local_l1_navigation",
            side_effect=AssertionError("route selection must not load unrelated navigation bodies")
        ), patch.object(validate, "load_json", side_effect=observe_json):
            result = validate.reconstruct_entry_context(
                root=ROOT,
                profile_revision=PROFILE_REVISION,
                target_binding=target,
                request_identity="request-1",
                entry_intent="MATERIAL_JUDGMENT",
                controller="CHATGPT",
                location="LOCAL",
                resolved=resolved,
            )

        self.assertEqual(result["authority"], "NONE")
        self.assertEqual(result["entry_route"], "MATERIAL_JUDGMENT")
        self.assertEqual(result["role"], "architect")
        self.assertIsNone(result["specialization"])
        self.assertEqual([item["capability"] for item in result["capability_routes"]], ["architect"])
        self.assertEqual(result["l1_navigation"], {})
        self.assertEqual(result["target_binding"], target)
        self.assertEqual(result["target_resolution"]["head"], target_head)
        target_resolver.assert_called_once_with("owner/repo", "main")
        self.assertCountEqual(
            loaded,
            [
                "profile/.agent/bootstrap/bootstrap.json",
                "profile/.agent/bootstrap/authority.lock.json",
            ],
        )

    def test_read_only_research_uses_generic_binding_without_task_protocol_or_external_how(self) -> None:
        target = {"repository": "owner/repo", "branch": "main"}
        result = self._resolve_entry(target, "READ_ONLY_RESEARCH")
        self.assertEqual(result["authority"], "NONE")
        self.assertEqual(result["entry_route"], "READ_ONLY_RESEARCH")
        self.assertEqual(result["role"], "executor")
        self.assertEqual(result["specialization"], "researcher")
        self.assertEqual([item["capability"] for item in result["capability_routes"]], ["executor"])
        self.assertEqual(
            set(result["l1_navigation"]),
            {"research_request_contract", "research_result_contract"},
        )
        self.assertNotIn("task_protocol", {item["capability"] for item in result["capability_routes"]})
        self.assertNotIn("external_capability_catalog", result)
        self.assertNotIn("task_path", result["target_binding"])
        self.assertNotIn("base_head", result["target_binding"])

    def test_task_execution_and_legacy_execute_select_executor_without_architect(self) -> None:
        target = {
            "repository": "owner/repo",
            "branch": "main",
            "task_path": ".agent/tasks/TASK-0001/task.yaml",
            "task_revision": 1,
            "base_head": "d" * 40,
            "phase": "EXECUTION",
        }
        resolved = self._entry_resolved()
        with patch.object(validate, "resolve_target_branch", return_value={
            "repository": "owner/repo", "branch": "main", "head": target["base_head"]
        }):
            result = validate.reconstruct_execution_context(
                ROOT, PROFILE_REVISION, target, "EXECUTE", resolved
            )
        self.assertEqual(result["entry_route"], "TASK_EXECUTION")
        self.assertEqual(result["case"], "TASK_EXECUTION")
        self.assertEqual(result["role"], "executor")
        self.assertEqual(
            [item["capability"] for item in result["capability_routes"]],
            ["executor", "task_protocol"],
        )
        self.assertNotIn("architect", {item["capability"] for item in result["capability_routes"]})
        self.assertEqual(result["target_binding"], target)

    def test_task_execution_rejects_missing_task_binding_fields(self) -> None:
        target = {
            "repository": "owner/repo",
            "branch": "main",
            "task_path": ".agent/tasks/TASK-0001/task.yaml",
        }
        with patch.object(validate, "resolve_target_branch", return_value={
            "repository": "owner/repo", "branch": "main", "head": "c" * 40
        }):
            with self.assertRaisesRegex(ValueError, "task-bound"):
                validate.reconstruct_entry_context(
                    root=ROOT,
                    profile_revision=PROFILE_REVISION,
                    target_binding=target,
                    request_identity=None,
                    entry_intent="TASK_EXECUTION",
                    controller="CHATGPT",
                    location="LOCAL",
                    resolved=self._entry_resolved(),
                )

    def test_unknown_entry_intent_fails_closed_to_architect_and_ambiguity_errors(self) -> None:
        target = {"repository": "owner/repo", "branch": "main"}
        result = self._resolve_entry(target, "UNRECOGNIZED")
        self.assertEqual(result["entry_route"], "MATERIAL_JUDGMENT")
        self.assertEqual(result["route_disposition"], "DEFAULTED_TO_MATERIAL_JUDGMENT")
        with self.assertRaisesRegex(ValueError, "entry intent"):
            self._resolve_entry(target, ["READ_ONLY_RESEARCH", "TASK_EXECUTION"])

    def test_target_branch_resolution_uses_fresh_exact_github_branch(self) -> None:
        head = "e" * 40
        with patch.object(validate, "_github_json", return_value={
            "name": "feature/topic",
            "commit": {"sha": head},
        }) as github:
            result = validate.resolve_target_branch("owner/repo", "feature/topic")
        self.assertEqual(
            result,
            {"repository": "owner/repo", "branch": "feature/topic", "head": head},
        )
        self.assertEqual(
            github.call_args.args[0],
            "https://api.github.com/repos/owner/repo/branches/feature%2Ftopic",
        )

    def test_micro_maintenance_remains_architect_owned_and_outside_router_classes(self) -> None:
        architect = (ROOT / "skills/architect/SKILL.md").read_text(encoding="utf-8")
        protocol = (ROOT / "skills/protocols/TASK_PROTOCOL.md").read_text(encoding="utf-8")
        router = validate.parse_case_router(
            (ROOT / "skills/.agent/case-router.yaml").read_text(encoding="utf-8")
        )
        self.assertIn(
            "taskless micro-maintenance exception remains Architect-owned only after this route",
            architect,
        )
        self.assertIn("only after proving every eligibility predicate before mutation", architect)
        self.assertIn("Eligibility must be proven before mutation.", protocol)
        self.assertIn("Supported protocol version: **3**", protocol)
        self.assertNotIn("micro-maintenance", [route["id"] for route in router["routes"]])

    def test_case_router_has_exactly_three_routes_and_two_organizational_roles(self) -> None:
        router_text = (ROOT / "skills/.agent/case-router.yaml").read_text(encoding="utf-8")
        router = validate.parse_case_router(router_text)
        validate.validate_case_router(router)
        self.assertEqual(router["authority"], "NONE")
        self.assertEqual(
            [route["id"] for route in router["routes"]],
            ["MATERIAL_JUDGMENT", "READ_ONLY_RESEARCH", "TASK_EXECUTION"],
        )
        self.assertEqual({route["role"] for route in router["routes"]}, {"architect", "executor"})
        self.assertEqual(router["legacy_aliases"], {"EXECUTE": "TASK_EXECUTION"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
