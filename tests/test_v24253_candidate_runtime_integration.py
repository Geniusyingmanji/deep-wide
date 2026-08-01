from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepwide_agent.runtime import RuntimeConfig  # noqa: E402
from deepwide_agent.v24233_webswarm_effect_preauthorization import (  # noqa: E402
    initialize_effect_preauthorization_state,
)
from deepwide_agent.v24252_candidate_runner_package import (  # noqa: E402
    CandidateRunnerCredentials,
    CandidateRunnerFrozenInputs,
    CandidateRunnerPackage,
    CandidateRunnerTransportBundle,
    build_candidate_runner_package_contract,
)
from deepwide_agent.v24253_candidate_runtime_integration import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    ACTIVE_RUNNER_CONSTRUCTOR_PATCH_IMPLEMENTED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CANDIDATE_DEEPWIDE_RUNTIME_CONSTRUCTOR_IMPLEMENTED,
    CHECKPOINT_PACKAGE_AND_SOURCE_BINDING_IMPLEMENTED,
    DEV64_GATE_LAUNCH_AUTHORIZED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    EXACT_VISIBLE_TASK_SCHEMA_ENFORCED,
    EXTERNAL_SIDE_EFFECT_AUTHORIZED,
    GLOBAL_ADMISSION_DERIVED_PAGE_SOURCE_ENFORCED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    OFFICIAL_EVALUATOR_OPENED,
    OUTPUT_ROOT_PRISTINE_AT_CONSTRUCTION_REQUIRED,
    PACKAGE_PREFLIGHT_BEFORE_TASK_AND_SEARCH_STAGE,
    PROSPECTIVE_DEV64_GATE_CONTRACT_FROZEN,
    PRODUCTION_PACKAGE_AUTHORIZED,
    PROSPECTIVE_DEV64_PAIR_MATERIALIZED,
    RUNTIME_RESUME_OR_SELECTIVE_RERUN_IMPLEMENTED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    CandidateDev64Identity,
    CandidatePackageDeepWideRuntime,
    CandidateRuntimeIntegrationError,
    CandidateRuntimeIntegrationPoisoned,
    CandidateRuntimeLaunchLimits,
    build_candidate_runtime_integration_contract,
    validate_candidate_runtime_integration_contract,
    validate_candidate_runtime_integration_source_manifest,
    validate_visible_runtime_task,
)
from tests import test_v24248_candidate_client_facade as parent_fixture  # noqa: E402


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


class V24253CandidateRuntimeIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parent = parent_fixture.V24248CandidateClientFacadeTests(
            methodName="runTest"
        )
        self.parent.setUp()

    def tearDown(self) -> None:
        self.parent.tearDown()

    def frozen(self, provider: str = "tavily_search_api") -> CandidateRunnerFrozenInputs:
        facade = self.parent.facade_contract(provider)
        initial = initialize_effect_preauthorization_state(
            initial_budget_ledger=parent_fixture.ledger(
                self.parent.guidance_contract,
                self.parent.policy,
                self.parent.arm,
                self.parent.source,
            ),
            **self.parent.shared,
        )
        return CandidateRunnerFrozenInputs(
            guidance_contract=self.parent.guidance_contract,
            guidance_policy=self.parent.policy,
            guidance_arm=self.parent.arm,
            scouts=self.parent.source["scouts"],
            probe=self.parent.source["probe"],
            experience=self.parent.source["experience"],
            pristine_initial_state=initial,
            facade_contract=facade,
        )

    def runtime_config(self) -> RuntimeConfig:
        return RuntimeConfig(
            model_name="gpt-5.6-sol",
            model_reasoning_effort="high",
            model_service_tier="priority",
            search_provider="tavily",
            search_workers=1,
            native_fetch_workers=1,
            tavily_results=2,
            evidence_item_chars=500,
            evidence_context_chars=500,
            mention_gap_context_chars=500,
            mention_gap_item_chars=500,
            row_evidence_context_chars=500,
            row_refinement_context_chars=500,
            final_evidence_context_chars=500,
            plan_tokens=200,
            belief_tokens=200,
            anchor_tokens=200,
            scope_tokens=200,
            candidate_tokens=200,
            row_tokens=200,
            row_refinement_tokens=200,
            draft_tokens=200,
            audit_tokens=200,
            revision_tokens=200,
            final_tokens=200,
        )

    def provider_runtime_config(self, provider: str) -> RuntimeConfig:
        value = self.runtime_config()
        if provider == "azure_responses_web_search":
            value.search_provider = "azure-native"
        elif provider == "anthropic_server_web_search":
            value.search_provider = "anthropic"
            value.anthropic_search_model = "claude-haiku-4-5-20251001"
            value.anthropic_search_max_uses = 2
            value.anthropic_search_max_output_tokens = 200
        return value

    def limits(self) -> CandidateRuntimeLaunchLimits:
        return CandidateRuntimeLaunchLimits(
            model_timeout_seconds=1,
            model_max_attempts=1,
            search_timeout_seconds=1,
            search_max_attempts=1,
            fetch_timeout_seconds=1,
            fetch_max_attempts=1,
            minimum_model_prompt_utf8_bytes=4000,
            provider_execution_parallelism=1,
        )

    def dev64(self) -> CandidateDev64Identity:
        return CandidateDev64Identity(
            selected_count=64,
            opaque_id_file_sha256=digest("opaque-dev64-id-file"),
            runtime_manifest_sha256=digest("runtime-manifest"),
        )

    def package_and_runtime(self):
        frozen = self.frozen()
        package_contract = build_candidate_runner_package_contract(
            source_root=ROOT / "src",
            frozen=frozen,
            journal_namespace_sha256=digest("v24253-journal"),
        )
        model_post = parent_fixture.ModelPost(
            parent_fixture.ModelResponse(
                200,
                parent_fixture.model_response_bytes(text='{"ready":true}'),
            )
        )
        search_post = parent_fixture.TavilyPost(
            parent_fixture.TavilyResponse(
                200,
                parent_fixture.tavily_response_bytes(
                    answer="provider answer discarded",
                    results=[
                        {
                            "title": "Integrated page",
                            "url": "https://example.com/integrated",
                            "content": "provider snippet discarded",
                            "raw_content": "provider raw discarded",
                            "score": 0.9,
                        }
                    ],
                ),
            )
        )
        fetch_factory = parent_fixture.RecordingPoolFactory(
            parent_fixture.FetchResponse(
                200,
                [b"<html><body>integrated admitted page</body></html>"],
                headers={"Content-Type": "text/html; charset=utf-8"},
            )
        )
        clock = parent_fixture.VirtualClock()
        transports = CandidateRunnerTransportBundle(
            model_post=model_post,
            search_post=search_post,
            fetch_resolve=parent_fixture.RecordingResolver(("93.184.216.34",)),
            fetch_pool_factory=fetch_factory,
            monotonic_ns=clock.monotonic_ns,
            sleeper=clock.sleep,
        )
        package_root = Path(tempfile.mkdtemp(dir=self.parent.root)).resolve()
        package = CandidateRunnerPackage.initialize(
            root=package_root,
            source_root=ROOT / "src",
            contract=package_contract,
            frozen=frozen,
            credentials=CandidateRunnerCredentials(
                tavily_credentials=("synthetic-v24253-credential",)
            ),
            transports=transports,
        )
        config = self.runtime_config()
        integration = build_candidate_runtime_integration_contract(
            repository_root=ROOT,
            package_contract=package_contract,
            runtime_config=config,
            launch_limits=self.limits(),
            dev64_identity=self.dev64(),
        )
        output = Path(tempfile.mkdtemp(dir=self.parent.root)).resolve()
        runtime = CandidatePackageDeepWideRuntime(
            package=package,
            runtime_config=config,
            launch_limits=self.limits(),
            integration_contract=integration,
            out_dir=output,
        )
        return runtime, package, integration, model_post, search_post, fetch_factory

    def test_scope_and_authorization_constants_are_exact(self) -> None:
        for value in (
            PRODUCTION_PACKAGE_AUTHORIZED,
            ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
            ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
            EXTERNAL_SIDE_EFFECT_AUTHORIZED,
            BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
            DEV64_GATE_LAUNCH_AUTHORIZED,
            DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
            SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
            LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
            RUNTIME_RESUME_OR_SELECTIVE_RERUN_IMPLEMENTED,
            ACTIVE_RUNNER_CONSTRUCTOR_PATCH_IMPLEMENTED,
            PROSPECTIVE_DEV64_PAIR_MATERIALIZED,
            OFFICIAL_EVALUATOR_OPENED,
        ):
            self.assertFalse(value)
        for value in (
            CANDIDATE_DEEPWIDE_RUNTIME_CONSTRUCTOR_IMPLEMENTED,
            EXACT_VISIBLE_TASK_SCHEMA_ENFORCED,
            PACKAGE_PREFLIGHT_BEFORE_TASK_AND_SEARCH_STAGE,
            GLOBAL_ADMISSION_DERIVED_PAGE_SOURCE_ENFORCED,
            CHECKPOINT_PACKAGE_AND_SOURCE_BINDING_IMPLEMENTED,
            OUTPUT_ROOT_PRISTINE_AT_CONSTRUCTION_REQUIRED,
            PROSPECTIVE_DEV64_GATE_CONTRACT_FROZEN,
        ):
            self.assertTrue(value)

    def test_contract_binds_package_runtime_limits_and_dev64_identity(self) -> None:
        runtime, package, value, _, _, _ = self.package_and_runtime()
        validate_candidate_runtime_integration_contract(value)
        validate_candidate_runtime_integration_source_manifest(
            value["source_manifest"]
        )
        self.assertEqual(
            value["package_contract_sha256"],
            package._contract["package_contract_sha256"],
        )
        self.assertEqual(value["dev64_identity"]["selected_count"], 64)
        self.assertFalse(value["dev64_identity"]["raw_opaque_ids_embedded"])
        self.assertFalse(value["dev64_identity"]["questions_embedded"])
        self.assertFalse(
            value["dev64_identity"]["mapping_gold_evaluator_or_score_read"]
        )
        gate = value["paired_dev64_gate_contract"]
        self.assertTrue(gate["both_forwards_exact_terminal_before_mapping_or_evaluator"])
        self.assertTrue(gate["failure_as_zero"])
        self.assertFalse(gate["forward_or_evaluator_resume_allowed"])
        self.assertFalse(gate["dev64_launch_authorized"])
        self.assertFalse(gate["exact220_launch_authorized"])
        self.assertEqual(runtime.integration_status()["tasks_started_in_this_process"], 0)

    def test_visible_task_schema_rejects_every_privileged_or_extra_field(self) -> None:
        base = {"opaque_id": "task_" + "a" * 24, "question": "Visible question"}
        self.assertEqual(validate_visible_runtime_task(base), base)
        for key in (
            "question_type",
            "category",
            "task_category",
            "split",
            "mapping",
            "gold",
            "ground_truth",
            "answer_key",
            "evaluator_score",
            "score",
        ):
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, "schema"):
                    validate_visible_runtime_task({**base, key: "forbidden"})

    def test_inherited_search_stage_accepts_only_admission_pages_and_binds_checkpoint(self) -> None:
        runtime, package, integration, _, search_post, fetch_factory = (
            self.package_and_runtime()
        )
        state = {
            "opaque_id": "task_" + "d" * 24,
            "search_batches": {},
            "evidence": [],
            "search_stage_stats": {},
        }
        runtime._search_stage(state, "synthetic", ["visible synthetic query"])
        self.assertEqual(len(state["evidence"]), 1)
        page = state["evidence"][0]
        self.assertEqual(page["kind"], "page")
        self.assertTrue(page["untrusted_data"])
        self.assertFalse(page["instruction_authority"])
        self.assertTrue(page["active_evidence_eligible"])
        self.assertTrue(
            page["source_type"].startswith("v24251_explicit_page_ingress:")
        )
        self.assertEqual(
            state["candidate_package_contract_sha256"],
            package._contract["package_contract_sha256"],
        )
        self.assertEqual(
            state["candidate_runtime_integration_contract_sha256"],
            integration["integration_contract_sha256"],
        )
        self.assertTrue(state["candidate_page_evidence_requires_explicit_admission"])
        self.assertFalse(state["benchmark_or_evaluator_metadata_used_for_routing"])
        self.assertEqual(len(search_post.calls), 1)
        self.assertEqual(len(fetch_factory.pools), 1)

    def test_search_batch_tamper_is_rejected_before_inherited_ingestion(self) -> None:
        runtime, package, _, _, _, _ = self.package_and_runtime()
        original = package.search_client.search_many

        def tampered(*args, **kwargs):
            batches = original(*args, **kwargs)
            batches[0]["results"][0]["raw_content"] += " altered"
            return batches

        with mock.patch.object(package.search_client, "search_many", side_effect=tampered):
            state = {
                "opaque_id": "task_" + "e" * 24,
                "search_batches": {},
                "evidence": [],
                "search_stage_stats": {},
            }
            with self.assertRaises(Exception):
                runtime._search_stage(state, "synthetic", ["visible query"])
            self.assertEqual(state["evidence"], [])

    def test_every_checkpoint_revalidates_all_page_admission(self) -> None:
        runtime, _, _, _, _, _ = self.package_and_runtime()
        state = {
            "opaque_id": "task_" + "9" * 24,
            "evidence": [
                {
                    "kind": "page",
                    "source_type": "unadmitted-provider-page",
                    "untrusted_data": True,
                    "instruction_authority": False,
                }
            ],
        }
        with self.assertRaisesRegex(
            CandidateRuntimeIntegrationPoisoned, "explicit admission"
        ):
            runtime._save(state)
        self.assertFalse(runtime._state_path(state["opaque_id"]).exists())

    def test_directory_fetch_surface_validates_admission_before_return(self) -> None:
        runtime, package, _, _, _, _ = self.package_and_runtime()
        package.search_client._inner._search_contexts("visible lead query", 1)
        request_url = next(iter(package.search_client._inner._lead_cache))
        batches = runtime.search.fetch_urls(
            [{"url": request_url, "query": "visible direct fetch"}]
        )
        self.assertEqual(len(batches), 1)
        self.assertEqual(len(batches[0]["results"]), 1)
        self.assertTrue(
            batches[0]["results"][0]["source_type"].startswith(
                "v24251_explicit_page_ingress:"
            )
        )

        original = package.search_client.fetch_urls

        def tampered(*args, **kwargs):
            value = original(*args, **kwargs)
            value[0]["results"][0]["instruction_authority"] = True
            return value

        with mock.patch.object(package.search_client, "fetch_urls", side_effect=tampered):
            with self.assertRaises(Exception):
                runtime.search.fetch_urls(
                    [{"url": request_url, "query": "visible direct fetch"}]
                )

    def test_task_run_path_is_label_blind_and_resume_fails_before_forward(self) -> None:
        runtime, _, _, model_post, _, _ = self.package_and_runtime()
        task = {"opaque_id": "task_" + "b" * 24, "question": "Visible task"}
        with mock.patch.object(
            runtime,
            "_run_task_stages",
            return_value={
                "opaque_id": task["opaque_id"],
                "prediction": "synthetic",
                "status": "completed",
            },
        ):
            value = runtime.run_task(task)
        self.assertEqual(value["status"], "completed")
        with self.assertRaisesRegex(CandidateRuntimeIntegrationError, "rerun"):
            runtime.run_task(task)
        self.assertEqual(model_post.calls, [])
        state = json.loads(runtime._state_path(task["opaque_id"]).read_text())
        self.assertFalse(state["benchmark_or_evaluator_metadata_used_for_routing"])

    def test_source_contract_package_and_output_residue_fail_before_effect(self) -> None:
        runtime, package, integration, model_post, _, _ = self.package_and_runtime()
        with mock.patch(
            "deepwide_agent.v24253_candidate_runtime_integration._read_source_file",
            return_value=(1, "0" * 64),
        ):
            with self.assertRaises(CandidateRuntimeIntegrationPoisoned):
                runtime.run_task(
                    {"opaque_id": "task_" + "c" * 24, "question": "Visible"}
                )
        self.assertEqual(model_post.calls, [])

        package._contract["facade_contract"]["model_maximum_output_tokens"] += 1
        with self.assertRaises(CandidateRuntimeIntegrationPoisoned):
            runtime.integration_status()
        package._contract = copy.deepcopy(integration["package_contract"])

        residue = Path(tempfile.mkdtemp(dir=self.parent.root)).resolve()
        (residue / "unexpected").mkdir()
        with self.assertRaises(FileExistsError):
            CandidatePackageDeepWideRuntime(
                package=package,
                runtime_config=self.runtime_config(),
                launch_limits=self.limits(),
                integration_contract=integration,
                out_dir=residue,
            )

    def test_runtime_limit_or_dev64_tamper_is_rejected(self) -> None:
        frozen = self.frozen()
        package_contract = build_candidate_runner_package_contract(
            source_root=ROOT / "src",
            frozen=frozen,
            journal_namespace_sha256=digest("v24253-invalid"),
        )
        too_large = self.runtime_config()
        too_large.final_tokens = 201
        with self.assertRaisesRegex(ValueError, "compatibility"):
            build_candidate_runtime_integration_contract(
                repository_root=ROOT,
                package_contract=package_contract,
                runtime_config=too_large,
                launch_limits=self.limits(),
                dev64_identity=self.dev64(),
            )
        with self.assertRaisesRegex(ValueError, "dev64"):
            build_candidate_runtime_integration_contract(
                repository_root=ROOT,
                package_contract=package_contract,
                runtime_config=self.runtime_config(),
                launch_limits=self.limits(),
                dev64_identity=dataclasses.replace(self.dev64(), selected_count=63),
            )

    def test_three_provider_runtime_mappings_are_exact(self) -> None:
        expected = {
            "tavily_search_api": "tavily",
            "azure_responses_web_search": "azure-native",
            "anthropic_server_web_search": "anthropic",
        }
        for provider, runtime_name in expected.items():
            with self.subTest(provider=provider):
                frozen = self.frozen(provider)
                package_contract = build_candidate_runner_package_contract(
                    source_root=ROOT / "src",
                    frozen=frozen,
                    journal_namespace_sha256=digest(f"provider-{provider}"),
                )
                value = build_candidate_runtime_integration_contract(
                    repository_root=ROOT,
                    package_contract=package_contract,
                    runtime_config=self.provider_runtime_config(provider),
                    launch_limits=self.limits(),
                    dev64_identity=self.dev64(),
                )
                self.assertEqual(
                    value["search_provider_mapping"],
                    {"package": provider, "runtime": runtime_name},
                )

    def test_contract_contains_no_raw_ids_questions_or_evaluator_material(self) -> None:
        _, _, contract, _, _, _ = self.package_and_runtime()
        encoded = json.dumps(contract, sort_keys=True).casefold()
        self.assertNotRegex(encoded, r'"task_[0-9a-f]{24}"')
        for forbidden in (
            '"question_type"',
            '"category"',
            '"task_category"',
            '"ground_truth"',
            '"answer_key"',
            '"evaluator_score"',
            '"score"',
        ):
            self.assertNotIn(forbidden, encoded)


if __name__ == "__main__":
    unittest.main()
