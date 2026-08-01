from __future__ import annotations

import copy
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

from deepwide_agent.runtime import add_search_batches  # noqa: E402
from deepwide_agent.v24233_webswarm_effect_preauthorization import (  # noqa: E402
    initialize_effect_preauthorization_state,
)
from deepwide_agent.v24232_webswarm_total_budget import object_sha256  # noqa: E402
from deepwide_agent.v24237_tavily_search_single_attempt import (  # noqa: E402
    TavilySearchSingleAttemptAdapter,
)
from deepwide_agent.v24239_azure_hosted_search_single_attempt import (  # noqa: E402
    AzureHostedSearchSingleAttemptAdapter,
)
from deepwide_agent.v24240_anthropic_server_search_single_attempt import (  # noqa: E402
    AnthropicServerSearchSingleAttemptAdapter,
)
from deepwide_agent.v24250_durable_action_outcome_ledger import (  # noqa: E402
    DurableActionOutcomeQuarantined,
)
from deepwide_agent.v24252_candidate_runner_package import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CREDENTIAL_PERSISTED_HASHED_OR_EMITTED,
    CREATE_EXCLUSIVE_INITIAL_AND_READY_RECEIPTS_IMPLEMENTED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    EPHEMERAL_CREDENTIAL_RUNTIME_ARGUMENTS_IMPLEMENTED,
    EXTERNAL_SIDE_EFFECT_AUTHORIZED,
    GLOBAL_DURABLE_ACTION_ORDINAL_CONTINUES_AFTER_RESTART,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    PRISTINE_SINGLE_PACKAGE_ROOT_IMPLEMENTED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    RESTARTABLE_PARENT_RECONSTRUCTION_IMPLEMENTED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    SOURCE_MANIFEST_REVALIDATED_BEFORE_EACH_RUNNER_OPERATION,
    SOURCE_RELATIVE_PATHS,
    CandidateRunnerCredentials,
    CandidateRunnerFrozenInputs,
    CandidateRunnerPackage,
    CandidateRunnerPackagePoisoned,
    CandidateRunnerTransportBundle,
    build_candidate_runner_package_contract,
    validate_candidate_runner_package_contract,
    validate_candidate_runner_package_initial,
    validate_candidate_runner_package_ready,
    validate_candidate_runner_source_manifest,
)
from tests import test_v24248_candidate_client_facade as parent_fixture  # noqa: E402


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


class V24252CandidateRunnerPackageTests(unittest.TestCase):
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

    def runtime(
        self,
        provider: str = "tavily_search_api",
        *,
        model_text: str = '{"ready":true,"value":"package"}',
        credentials: CandidateRunnerCredentials | None = None,
    ):
        model_post = parent_fixture.ModelPost(
            parent_fixture.ModelResponse(
                200,
                parent_fixture.model_response_bytes(text=model_text),
            )
        )
        if provider == "tavily_search_api":
            search_post = parent_fixture.TavilyPost(
                parent_fixture.TavilyResponse(
                    200,
                    parent_fixture.tavily_response_bytes(
                        answer="discard provider synthesis",
                        results=[
                            {
                                "title": "Package source",
                                "url": "https://example.com/package",
                                "content": "discard provider snippet",
                                "raw_content": "discard provider raw content",
                                "score": 0.99,
                            }
                        ],
                    ),
                )
            )
            supplied_credentials = credentials or CandidateRunnerCredentials(
                tavily_credentials=("synthetic-package-credential",)
            )
        elif provider == "azure_responses_web_search":
            search_post = parent_fixture.HostedPost(
                parent_fixture.HostedResponse(
                    200,
                    parent_fixture.hosted_response_bytes(),
                )
            )
            supplied_credentials = credentials or CandidateRunnerCredentials()
        else:
            search_post = parent_fixture.AnthropicPost(
                parent_fixture.AnthropicResponse(
                    200,
                    parent_fixture.anthropic_response_bytes(),
                )
            )
            supplied_credentials = credentials or CandidateRunnerCredentials(
                anthropic_credential="synthetic-anthropic-package-credential"
            )
        fetch_factory = parent_fixture.RecordingPoolFactory(
            parent_fixture.FetchResponse(
                200,
                [b"<html><body>admitted package page</body></html>"],
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
        return supplied_credentials, transports, model_post, search_post, fetch_factory

    def package(
        self,
        provider: str = "tavily_search_api",
        *,
        source_root: Path | None = None,
        credentials: CandidateRunnerCredentials | None = None,
    ):
        frozen = self.frozen(provider)
        source = source_root or (ROOT / "src")
        contract = build_candidate_runner_package_contract(
            source_root=source,
            frozen=frozen,
            journal_namespace_sha256=digest(f"v24252-{provider}"),
        )
        runtime = self.runtime(provider, credentials=credentials)
        package_root = Path(tempfile.mkdtemp(dir=self.parent.root)).resolve()
        package = CandidateRunnerPackage.initialize(
            root=package_root,
            source_root=source,
            contract=contract,
            frozen=frozen,
            credentials=runtime[0],
            transports=runtime[1],
        )
        return package, contract, frozen, runtime

    def test_candidate_scope_and_package_capabilities_are_exact(self) -> None:
        for value in (
            PRODUCTION_PACKAGE_AUTHORIZED,
            ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
            ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
            EXTERNAL_SIDE_EFFECT_AUTHORIZED,
            BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
            DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
            SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
            LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
            CREDENTIAL_PERSISTED_HASHED_OR_EMITTED,
        ):
            self.assertFalse(value)
        for value in (
            PRISTINE_SINGLE_PACKAGE_ROOT_IMPLEMENTED,
            CREATE_EXCLUSIVE_INITIAL_AND_READY_RECEIPTS_IMPLEMENTED,
            RESTARTABLE_PARENT_RECONSTRUCTION_IMPLEMENTED,
            SOURCE_MANIFEST_REVALIDATED_BEFORE_EACH_RUNNER_OPERATION,
            GLOBAL_DURABLE_ACTION_ORDINAL_CONTINUES_AFTER_RESTART,
            EPHEMERAL_CREDENTIAL_RUNTIME_ARGUMENTS_IMPLEMENTED,
        ):
            self.assertTrue(value)

    def test_fake_model_search_fetch_reaches_legacy_ingestion(self) -> None:
        package, contract, _, runtime = self.package()
        validate_candidate_runner_package_contract(contract)
        validate_candidate_runner_source_manifest(contract["source_manifest"])
        validate_candidate_runner_package_initial(package._initial)
        validate_candidate_runner_package_ready(package._ready)
        value, traces = package.model_client.complete_json(
            "visible package system",
            "visible package user",
            max_output_tokens=200,
        )
        self.assertEqual(value, {"ready": True, "value": "package"})
        self.assertTrue(traces[0]["success"])
        batches = package.search_client.search_many(
            ["visible package query"],
            max_results=1,
        )
        evidence = add_search_batches([], batches, item_chars=1000)
        self.assertEqual([item["kind"] for item in evidence], ["page"])
        self.assertEqual(evidence[0]["text"], "admitted package page")
        encoded = json.dumps(batches, sort_keys=True)
        self.assertNotIn("provider synthesis", encoded)
        self.assertNotIn("provider snippet", encoded)
        self.assertNotIn("provider raw content", encoded)
        status = package.preflight()
        self.assertEqual(status["registry_claim_count"], 3)
        self.assertEqual(status["durable_success_outcome_count"], 3)
        self.assertEqual(status["unresolved_claim_count"], 0)
        self.assertEqual(len(runtime[2].calls), 1)
        self.assertEqual(len(runtime[3].calls), 1)
        self.assertEqual(len(runtime[4].pools), 1)

    def test_initialize_open_restart_preserves_contract_and_action_ordinal(self) -> None:
        package, contract, frozen, runtime = self.package()
        package.model_client.complete_json(
            "first system", "first user", max_output_tokens=200
        )
        second_runtime = self.runtime(
            model_text='{ "after_restart": true }'.replace(" ", "")
        )
        reopened = CandidateRunnerPackage.open(
            root=package.root,
            source_root=ROOT / "src",
            contract=contract,
            frozen=frozen,
            credentials=second_runtime[0],
            transports=second_runtime[1],
        )
        value, _ = reopened.model_client.complete_json(
            "second system", "second user", max_output_tokens=200
        )
        self.assertEqual(value, {"after_restart": True})
        claims = reopened._registry.load_claims()
        self.assertEqual([item["action_ordinal"] for item in claims], [1, 2])
        self.assertEqual(reopened.preflight()["durable_success_outcome_count"], 2)
        self.assertEqual(len(runtime[2].calls), 1)
        self.assertEqual(len(second_runtime[2].calls), 1)

    def test_credentials_are_ephemeral_and_absent_from_files_receipts_and_hash_input(self) -> None:
        sentinel = "SENTINEL_EPHEMERAL_CREDENTIAL_7f20e91a"
        credentials = CandidateRunnerCredentials(tavily_credentials=(sentinel,))
        package, contract, _, _ = self.package(credentials=credentials)
        self.assertNotIn(sentinel, json.dumps(contract, sort_keys=True))
        self.assertNotIn(sentinel, json.dumps(package._initial, sort_keys=True))
        self.assertNotIn(sentinel, json.dumps(package._ready, sort_keys=True))
        for path in package.root.rglob("*"):
            if path.is_file():
                self.assertNotIn(sentinel.encode("ascii"), path.read_bytes())
        status = package.preflight()
        self.assertFalse(status["credential_persisted_hashed_or_emitted"])

    def test_three_search_providers_get_exact_adapter_pairing(self) -> None:
        expected = {
            "tavily_search_api": TavilySearchSingleAttemptAdapter,
            "azure_responses_web_search": AzureHostedSearchSingleAttemptAdapter,
            "anthropic_server_web_search": AnthropicServerSearchSingleAttemptAdapter,
        }
        for provider, adapter_type in expected.items():
            with self.subTest(provider=provider):
                package, contract, _, _ = self.package(provider)
                self.assertIs(type(package._facade._search_adapter), adapter_type)
                self.assertEqual(
                    contract["provider_configuration"]["search_provider_kind"],
                    provider,
                )

    def test_wrong_provider_credential_pairing_rejects_before_root_reservation(self) -> None:
        frozen = self.frozen("anthropic_server_web_search")
        contract = build_candidate_runner_package_contract(
            source_root=ROOT / "src",
            frozen=frozen,
            journal_namespace_sha256=digest("bad-pairing"),
        )
        root = Path(tempfile.mkdtemp(dir=self.parent.root)).resolve()
        _, transports, _, _, _ = self.runtime("anthropic_server_web_search")
        with self.assertRaisesRegex(ValueError, "pairing"):
            CandidateRunnerPackage.initialize(
                root=root,
                source_root=ROOT / "src",
                contract=contract,
                frozen=frozen,
                credentials=CandidateRunnerCredentials(
                    tavily_credentials=("wrong-provider-credential",)
                ),
                transports=transports,
            )
        self.assertEqual(list(root.iterdir()), [])

    def test_default_hardened_transports_construct_without_network_effect(self) -> None:
        frozen = self.frozen()
        contract = build_candidate_runner_package_contract(
            source_root=ROOT / "src",
            frozen=frozen,
            journal_namespace_sha256=digest("default-transports"),
        )
        root = Path(tempfile.mkdtemp(dir=self.parent.root)).resolve()
        package = CandidateRunnerPackage.initialize(
            root=root,
            source_root=ROOT / "src",
            contract=contract,
            frozen=frozen,
            credentials=CandidateRunnerCredentials(
                tavily_credentials=("default-transport-credential",)
            ),
        )
        self.assertFalse(package.preflight()["active_provider_traffic_authorized"])
        self.assertFalse(package._facade._model_adapter._session.trust_env)
        self.assertFalse(package._facade._search_adapter._session.trust_env)

    def test_nonpristine_overlap_symlink_and_partial_initialization_fail_closed(self) -> None:
        frozen = self.frozen()
        contract = build_candidate_runner_package_contract(
            source_root=ROOT / "src",
            frozen=frozen,
            journal_namespace_sha256=digest("layout-failures"),
        )
        credentials, transports, _, _, _ = self.runtime()
        nonpristine = Path(tempfile.mkdtemp(dir=self.parent.root)).resolve()
        (nonpristine / "residue").mkdir()
        with self.assertRaises(FileExistsError):
            CandidateRunnerPackage.initialize(
                root=nonpristine,
                source_root=ROOT / "src",
                contract=contract,
                frozen=frozen,
                credentials=credentials,
                transports=transports,
            )
        with self.assertRaisesRegex(ValueError, "overlap"):
            CandidateRunnerPackage.initialize(
                root=ROOT / "src",
                source_root=ROOT / "src",
                contract=contract,
                frozen=frozen,
                credentials=credentials,
                transports=transports,
            )
        real = Path(tempfile.mkdtemp(dir=self.parent.root)).resolve()
        link = self.parent.root / "package-symlink"
        link.symlink_to(real, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "ordinary"):
            CandidateRunnerPackage.initialize(
                root=link,
                source_root=ROOT / "src",
                contract=contract,
                frozen=frozen,
                credentials=credentials,
                transports=transports,
            )
        partial = Path(tempfile.mkdtemp(dir=self.parent.root)).resolve()
        with mock.patch.object(
            CandidateRunnerPackage,
            "_runtime_chain",
            side_effect=RuntimeError("synthetic partial initialization"),
        ):
            with self.assertRaisesRegex(RuntimeError, "partial initialization"):
                CandidateRunnerPackage.initialize(
                    root=partial,
                    source_root=ROOT / "src",
                    contract=contract,
                    frozen=frozen,
                    credentials=credentials,
                    transports=transports,
                )
        self.assertTrue(any(partial.iterdir()))
        with self.assertRaises(FileExistsError):
            CandidateRunnerPackage.initialize(
                root=partial,
                source_root=ROOT / "src",
                contract=contract,
                frozen=frozen,
                credentials=credentials,
                transports=transports,
            )

    def test_source_and_configuration_tamper_reject_before_effect(self) -> None:
        package, _, _, runtime = self.package()
        with mock.patch(
            "deepwide_agent.v24252_candidate_runner_package._read_source_file",
            return_value=(1, "0" * 64),
        ):
            with self.assertRaises(CandidateRunnerPackagePoisoned):
                package.model_client.complete_json(
                    "visible system", "visible user", max_output_tokens=200
                )
        self.assertEqual(runtime[2].calls, [])

        clean, _, _, clean_runtime = self.package()
        clean._contract["facade_contract"]["model_maximum_output_tokens"] += 1
        with self.assertRaises(CandidateRunnerPackagePoisoned):
            clean.model_client.complete_json(
                "visible system", "visible user", max_output_tokens=200
            )
        self.assertEqual(clean_runtime[2].calls, [])

    def test_unresolved_claim_remains_quarantined_after_restart(self) -> None:
        package, contract, frozen, _ = self.package()
        package._registry._claim("model_json")
        second_runtime = self.runtime()
        reopened = CandidateRunnerPackage.open(
            root=package.root,
            source_root=ROOT / "src",
            contract=contract,
            frozen=frozen,
            credentials=second_runtime[0],
            transports=second_runtime[1],
        )
        status = reopened.preflight()
        self.assertEqual(status["state"], "quarantined_uncertain_effect")
        self.assertEqual(status["unresolved_claim_count"], 1)
        with self.assertRaises(DurableActionOutcomeQuarantined):
            reopened.model_client.complete_json(
                "visible system", "visible user", max_output_tokens=200
            )
        self.assertEqual(second_runtime[2].calls, [])

    def test_contract_and_status_are_strictly_label_blind(self) -> None:
        package, contract, _, _ = self.package()
        encoded = json.dumps(
            {"contract": contract, "status": package.preflight()},
            sort_keys=True,
        ).casefold()
        for forbidden in (
            '"question_type"',
            '"category"',
            '"task_category"',
            '"ground_truth"',
            '"answer_key"',
            '"mapping"',
            '"evaluator_score"',
            '"score"',
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertTrue(contract["label_blind_runtime"])
        self.assertFalse(
            contract["benchmark_or_evaluator_metadata_used_for_routing"]
        )

    def test_resealed_receipts_and_root_residue_fail_closed(self) -> None:
        package, _, _, runtime = self.package()
        tampered = copy.deepcopy(package._ready)
        tampered["active_provider_traffic_authorized"] = True
        unsigned = dict(tampered)
        unsigned.pop("package_ready_sha256")
        tampered["package_ready_sha256"] = object_sha256(unsigned)
        package.ready_path.write_text(
            json.dumps(tampered, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(CandidateRunnerPackagePoisoned):
            package.model_client.complete_json(
                "visible system", "visible user", max_output_tokens=200
            )
        self.assertEqual(runtime[2].calls, [])

        clean, _, _, clean_runtime = self.package()
        (clean.root / "unexpected-residue").mkdir()
        with self.assertRaises(CandidateRunnerPackagePoisoned):
            clean.model_client.complete_json(
                "visible system", "visible user", max_output_tokens=200
            )
        self.assertEqual(clean_runtime[2].calls, [])


if __name__ == "__main__":
    unittest.main()
