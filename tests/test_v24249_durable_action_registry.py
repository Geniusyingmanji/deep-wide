from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepwide_agent.v24249_durable_action_registry import (  # noqa: E402
    ACTION_CLAIM_ORDER_EQUALS_EFFECT_COMPLETION_ORDER_VERIFIED,
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    ADAPTER_CODE_IDENTITY_INDEPENDENTLY_ATTESTED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CALLER_SINGLE_REGISTRY_OWNERSHIP_INDEPENDENTLY_VERIFIED,
    CALLER_SUPPLIED_ACTION_REF_ACCEPTED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    DIRECT_PARENT_FACADE_BYPASS_GLOBALLY_EXCLUDED,
    DURABLE_CLAIM_BEFORE_FACADE_EFFECT_IMPLEMENTED,
    EPHEMERAL_REQUEST_CONTENT_USED_FOR_ACTION_IDENTITY,
    EQUAL_EPHEMERAL_REQUEST_DEDUPLICATION_IMPLEMENTED,
    EXTERNAL_SIDE_EFFECT_AUTHORIZED,
    FILE_AND_DIRECTORY_FSYNC_IMPLEMENTED,
    FIXED_OPERATION_STAGE_REFS_IMPLEMENTED,
    GLOBAL_MONOTONIC_ACTION_ORDINAL_IMPLEMENTED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    LOCAL_POSIX_ADVISORY_LOCK_IMPLEMENTED,
    MALICIOUS_SAME_USER_RESEALING_EXCLUDED,
    NETWORK_OR_DISTRIBUTED_FILESYSTEM_SEMANTICS_PROVEN,
    OS_CSPRNG_INSTANCE_DOMAIN_IMPLEMENTED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    SEARCH_LEADS_OR_PAGE_TEXT_ACTIVE_EVIDENCE_ELIGIBILITY_GRANTED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    DurableActionRegistryError,
    DurableActionRegistryPoisoned,
    DurableCandidateActionRegistry,
    validate_registered_facade_receipt,
)
from tests import test_v24248_candidate_client_facade as parent_fixture  # noqa: E402


class V24249DurableActionRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parent = parent_fixture.V24248CandidateClientFacadeTests(
            methodName="runTest"
        )
        self.parent.setUp()
        self.root = self.parent.root

    def tearDown(self) -> None:
        self.parent.tearDown()

    def build_facade(self, **kwargs):
        return self.parent.build_facade(**kwargs)

    def json_model_post(self, count: int = 1):
        return parent_fixture.ModelPost(
            *(
                parent_fixture.ModelResponse(
                    200,
                    parent_fixture.model_response_bytes(
                        text='{"ready":true,"value":"synthetic"}'
                    ),
                )
                for _ in range(count)
            )
        )

    def registry(self, facade=None):
        selected = facade or self.build_facade()[0]
        directory = Path(tempfile.mkdtemp(dir=self.root)).resolve()
        return DurableCandidateActionRegistry.initialize(
            root=directory,
            facade=selected,
        )

    def test_constants_keep_candidate_authority_false(self) -> None:
        for value in (
            PRODUCTION_PACKAGE_AUTHORIZED,
            ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
            ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
            EXTERNAL_SIDE_EFFECT_AUTHORIZED,
            BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
            DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
            SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
            LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
            CALLER_SUPPLIED_ACTION_REF_ACCEPTED,
            EPHEMERAL_REQUEST_CONTENT_USED_FOR_ACTION_IDENTITY,
            EQUAL_EPHEMERAL_REQUEST_DEDUPLICATION_IMPLEMENTED,
            CALLER_SINGLE_REGISTRY_OWNERSHIP_INDEPENDENTLY_VERIFIED,
            DIRECT_PARENT_FACADE_BYPASS_GLOBALLY_EXCLUDED,
            ACTION_CLAIM_ORDER_EQUALS_EFFECT_COMPLETION_ORDER_VERIFIED,
            ADAPTER_CODE_IDENTITY_INDEPENDENTLY_ATTESTED,
            MALICIOUS_SAME_USER_RESEALING_EXCLUDED,
            NETWORK_OR_DISTRIBUTED_FILESYSTEM_SEMANTICS_PROVEN,
            SEARCH_LEADS_OR_PAGE_TEXT_ACTIVE_EVIDENCE_ELIGIBILITY_GRANTED,
        ):
            self.assertFalse(value)
        for value in (
            OS_CSPRNG_INSTANCE_DOMAIN_IMPLEMENTED,
            FIXED_OPERATION_STAGE_REFS_IMPLEMENTED,
            GLOBAL_MONOTONIC_ACTION_ORDINAL_IMPLEMENTED,
            DURABLE_CLAIM_BEFORE_FACADE_EFFECT_IMPLEMENTED,
            LOCAL_POSIX_ADVISORY_LOCK_IMPLEMENTED,
            FILE_AND_DIRECTORY_FSYNC_IMPLEMENTED,
        ):
            self.assertTrue(value)

    def test_three_effects_allocate_global_content_free_prefix(self) -> None:
        facade, _, model, search, fetch = self.build_facade(
            model_post=self.json_model_post()
        )
        registry = self.registry(facade)
        model_result = registry.run_model_json(
            system="private system value",
            user="private user value",
            max_output_tokens=200,
        )
        search_result = registry.run_search_leads(
            query="private search query",
            max_results=1,
        )
        page_result = registry.run_fetched_page(url="https://example.test/page")
        claims = registry.load_claims()
        self.assertEqual([claim["action_ordinal"] for claim in claims], [1, 2, 3])
        self.assertEqual(
            [claim["operation_kind"] for claim in claims],
            ["model_json", "search_leads", "fetched_page"],
        )
        self.assertIsNone(claims[0]["previous_claim_sha256"])
        self.assertEqual(
            claims[1]["previous_claim_sha256"], claims[0]["claim_sha256"]
        )
        self.assertEqual(
            claims[2]["previous_claim_sha256"], claims[1]["claim_sha256"]
        )
        for result in (model_result, search_result, page_result):
            validate_registered_facade_receipt(result.receipt)
            validation = registry.validate_receipt_against_registry(result.receipt)
            self.assertTrue(validation["claim_prefix_replayed_from_store"])
        encoded = json.dumps(
            [model_result.receipt, search_result.receipt, page_result.receipt],
            ensure_ascii=False,
        )
        for private in (
            "private system value",
            "private user value",
            "private search query",
            "https://example.test/page",
            "synthetic page",
        ):
            self.assertNotIn(private, encoded)
        self.assertEqual(len(model._post.calls), 1)
        self.assertEqual(len(search._post.calls), 1)
        self.assertEqual(len(fetch.pools[0].urlopen_calls), 1)

    def test_invalid_request_is_claimed_before_zero_effect_and_not_reused(self) -> None:
        facade, _, model, _, _ = self.build_facade(
            model_post=self.json_model_post()
        )
        registry = self.registry(facade)
        with self.assertRaisesRegex(Exception, "exceeds facade limits"):
            registry.run_model_json(
                system="x" * 5000,
                user="y",
                max_output_tokens=200,
            )
        self.assertEqual(len(model._post.calls), 0)
        self.assertEqual(registry.status()["allocated_action_count"], 1)
        result = registry.run_model_json(
            system="next system",
            user="next user",
            max_output_tokens=200,
        )
        self.assertEqual(result.receipt["action_claim"]["action_ordinal"], 2)
        self.assertEqual(len(model._post.calls), 1)

    def test_transport_observes_durable_claim_before_first_effect(self) -> None:
        class ClaimObservingPost:
            def __init__(self) -> None:
                self.registry = None
                self.observed_counts: list[int] = []

            def __call__(self, _url, **_kwargs):
                if self.registry is None:
                    raise AssertionError("registry was not bound")
                self.observed_counts.append(
                    self.registry.status()["allocated_action_count"]
                )
                return parent_fixture.ModelResponse(
                    200,
                    parent_fixture.model_response_bytes(
                        text='{"ready":true,"value":"synthetic"}'
                    ),
                )

        post = ClaimObservingPost()
        facade = self.build_facade(model_post=post)[0]
        registry = self.registry(facade)
        post.registry = registry
        result = registry.run_model_json(
            system="system", user="user", max_output_tokens=200
        )
        self.assertEqual(post.observed_counts, [1])
        self.assertEqual(result.receipt["action_claim"]["action_ordinal"], 1)

    def test_equal_requests_remain_distinct_actions_and_no_false_dedup_claim(self) -> None:
        post = self.json_model_post(2)
        facade, _, _, _, _ = self.build_facade(model_post=post)
        registry = self.registry(facade)
        first = registry.run_model_json(
            system="same", user="same", max_output_tokens=200
        )
        second = registry.run_model_json(
            system="same", user="same", max_output_tokens=200
        )
        self.assertNotEqual(
            first.receipt["action_claim_sha256"],
            second.receipt["action_claim_sha256"],
        )
        self.assertFalse(
            second.receipt["equal_ephemeral_request_deduplication_implemented"]
        )
        self.assertEqual(len(post.calls), 2)

    def test_reopen_continues_prefix_and_new_registry_has_new_domain(self) -> None:
        post = self.json_model_post(3)
        facade, _, _, _, _ = self.build_facade(model_post=post)
        registry = self.registry(facade)
        first = registry.run_model_json(system="a", user="b", max_output_tokens=200)
        reopened = DurableCandidateActionRegistry.open(
            root=registry.root,
            facade=facade,
        )
        second = reopened.run_model_json(system="c", user="d", max_output_tokens=200)
        other = self.registry(facade)
        third = other.run_model_json(system="e", user="f", max_output_tokens=200)
        self.assertEqual(second.receipt["action_claim"]["action_ordinal"], 2)
        self.assertNotEqual(
            first.receipt["registry_initial_sha256"],
            third.receipt["registry_initial_sha256"],
        )
        self.assertFalse(
            third.receipt["caller_single_registry_ownership_independently_verified"]
        )

    def test_concurrent_claims_are_unique_contiguous_and_chain_bound(self) -> None:
        facade, _, _, _, _ = self.build_facade()
        registry = self.registry(facade)
        barrier = threading.Barrier(8)
        ordinals: list[int] = []
        errors: list[BaseException] = []

        def worker() -> None:
            try:
                barrier.wait()
                _, claim = registry._claim("search_leads")
                ordinals.append(claim["action_ordinal"])
            except BaseException as error:
                errors.append(error)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(sorted(ordinals), list(range(1, 9)))
        claims = registry.load_claims()
        self.assertEqual(len({claim["claim_sha256"] for claim in claims}), 8)

    def test_registry_rejects_residue_gap_symlink_hardlink_and_tamper(self) -> None:
        cases = ("residue", "gap", "symlink", "hardlink", "tamper")
        for case in cases:
            with self.subTest(case=case):
                facade = self.build_facade()[0]
                registry = self.registry(facade)
                _, claim = registry._claim("model_json")
                path = registry.claims_directory / "00000000000000000001.json"
                if case == "residue":
                    (registry.claims_directory / "unexpected").write_text("x")
                elif case == "gap":
                    path.rename(registry.claims_directory / "00000000000000000002.json")
                elif case == "symlink":
                    path.unlink()
                    path.symlink_to(registry.initial_path)
                elif case == "hardlink":
                    os.link(path, registry.claims_directory / "00000000000000000002.json")
                else:
                    tampered = copy.deepcopy(claim)
                    tampered["operation_kind"] = "search_leads"
                    path.write_text(json.dumps(tampered), encoding="utf-8")
                with self.assertRaises(DurableActionRegistryPoisoned):
                    registry.load_claims()

    def test_receipt_requires_exact_durable_claim_not_only_resealed_schema(self) -> None:
        facade = self.build_facade(model_post=self.json_model_post())[0]
        registry = self.registry(facade)
        result = registry.run_model_json(
            system="system", user="user", max_output_tokens=200
        )
        other = self.registry(facade)
        with self.assertRaises(DurableActionRegistryPoisoned):
            other.validate_receipt_against_registry(result.receipt)

    def test_facade_binding_and_initialization_are_fail_closed(self) -> None:
        facade = self.build_facade()[0]
        registry = self.registry(facade)
        with self.assertRaises(FileExistsError):
            DurableCandidateActionRegistry.initialize(root=registry.root, facade=facade)
        facade._contract["model_maximum_output_tokens"] += 1
        with self.assertRaises(DurableActionRegistryError):
            registry._claim("model_json")

    def test_initialization_uses_exactly_one_random_nonce_and_fsyncs(self) -> None:
        facade = self.build_facade()[0]
        directory = Path(tempfile.mkdtemp(dir=self.root)).resolve()
        nonce = b"n" * 32
        with (
            mock.patch(
                "deepwide_agent.v24249_durable_action_registry.secrets.token_bytes",
                return_value=nonce,
            ) as random_mock,
            mock.patch(
                "deepwide_agent.v24249_durable_action_registry.os.fsync",
                wraps=os.fsync,
            ) as fsync_mock,
        ):
            registry = DurableCandidateActionRegistry.initialize(
                root=directory,
                facade=facade,
            )
        random_mock.assert_called_once_with(32)
        self.assertGreaterEqual(fsync_mock.call_count, 3)
        self.assertTrue(registry.status()["clean_contiguous_prefix"])


if __name__ == "__main__":
    unittest.main()
