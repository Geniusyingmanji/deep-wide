from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepwide_agent.v24249_durable_action_registry import (  # noqa: E402
    DurableCandidateActionRegistry,
)
from deepwide_agent.v24250_durable_action_outcome_ledger import (  # noqa: E402
    ACTION_CLAIM_ORDER_EQUALS_SUCCESS_OUTCOME_ORDER_VERIFIED,
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    ADAPTER_CODE_IDENTITY_INDEPENDENTLY_ATTESTED,
    AUTOMATIC_RETRY_OR_RESUME_IMPLEMENTED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CALLER_SINGLE_LEDGER_OWNERSHIP_INDEPENDENTLY_VERIFIED,
    CLAIMED_BUT_UNSTARTED_ACTION_RECOVERY_IMPLEMENTED,
    CLAIM_TO_SUCCESS_OUTCOME_DURABLE_BINDING_IMPLEMENTED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    DIRECT_PARENT_REGISTRY_OR_FACADE_BYPASS_GLOBALLY_EXCLUDED,
    DURABLE_CLAIM_BEFORE_EFFECT_IMPLEMENTED,
    DURABLE_SUCCESS_OUTCOME_AFTER_EFFECT_IMPLEMENTED,
    EPHEMERAL_REQUEST_CONTENT_USED_FOR_OUTCOME_IDENTITY,
    EQUAL_EPHEMERAL_REQUEST_DEDUPLICATION_IMPLEMENTED,
    EXTERNAL_SIDE_EFFECT_AUTHORIZED,
    FAILURE_OUTCOME_DURABLE_BINDING_IMPLEMENTED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    MALICIOUS_SAME_USER_RESEALING_EXCLUDED,
    NETWORK_OR_DISTRIBUTED_FILESYSTEM_SEMANTICS_PROVEN,
    OUTCOME_PUBLICATION_CRASH_AUTOMATIC_RECOVERY_IMPLEMENTED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    SEARCH_LEADS_OR_PAGE_TEXT_ACTIVE_EVIDENCE_ELIGIBILITY_GRANTED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    SINGLE_INFLIGHT_LOCAL_POSIX_EFFECT_IMPLEMENTED,
    DurableActionOutcomeError,
    DurableActionOutcomeLedger,
    DurableActionOutcomePoisoned,
    DurableActionOutcomeQuarantined,
    validate_durable_action_success_outcome,
)
from tests import test_v24248_candidate_client_facade as parent_fixture  # noqa: E402


class V24250DurableActionOutcomeLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parent = parent_fixture.V24248CandidateClientFacadeTests(
            methodName="runTest"
        )
        self.parent.setUp()
        self.root = self.parent.root

    def tearDown(self) -> None:
        self.parent.tearDown()

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

    def build(self, *, facade=None):
        selected = facade or self.parent.build_facade(
            model_post=self.json_model_post(4)
        )[0]
        registry_root = Path(tempfile.mkdtemp(dir=self.root)).resolve()
        outcome_root = Path(tempfile.mkdtemp(dir=self.root)).resolve()
        registry = DurableCandidateActionRegistry.initialize(
            root=registry_root,
            facade=selected,
        )
        ledger = DurableActionOutcomeLedger.initialize(
            root=outcome_root,
            registry=registry,
        )
        return ledger, registry, selected

    def test_constants_keep_scope_precise(self) -> None:
        for value in (
            PRODUCTION_PACKAGE_AUTHORIZED,
            ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
            ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
            EXTERNAL_SIDE_EFFECT_AUTHORIZED,
            BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
            DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
            SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
            LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
            AUTOMATIC_RETRY_OR_RESUME_IMPLEMENTED,
            FAILURE_OUTCOME_DURABLE_BINDING_IMPLEMENTED,
            CLAIMED_BUT_UNSTARTED_ACTION_RECOVERY_IMPLEMENTED,
            OUTCOME_PUBLICATION_CRASH_AUTOMATIC_RECOVERY_IMPLEMENTED,
            CALLER_SINGLE_LEDGER_OWNERSHIP_INDEPENDENTLY_VERIFIED,
            DIRECT_PARENT_REGISTRY_OR_FACADE_BYPASS_GLOBALLY_EXCLUDED,
            EQUAL_EPHEMERAL_REQUEST_DEDUPLICATION_IMPLEMENTED,
            EPHEMERAL_REQUEST_CONTENT_USED_FOR_OUTCOME_IDENTITY,
            ADAPTER_CODE_IDENTITY_INDEPENDENTLY_ATTESTED,
            MALICIOUS_SAME_USER_RESEALING_EXCLUDED,
            NETWORK_OR_DISTRIBUTED_FILESYSTEM_SEMANTICS_PROVEN,
            SEARCH_LEADS_OR_PAGE_TEXT_ACTIVE_EVIDENCE_ELIGIBILITY_GRANTED,
        ):
            self.assertFalse(value)
        for value in (
            SINGLE_INFLIGHT_LOCAL_POSIX_EFFECT_IMPLEMENTED,
            DURABLE_CLAIM_BEFORE_EFFECT_IMPLEMENTED,
            DURABLE_SUCCESS_OUTCOME_AFTER_EFFECT_IMPLEMENTED,
            CLAIM_TO_SUCCESS_OUTCOME_DURABLE_BINDING_IMPLEMENTED,
            ACTION_CLAIM_ORDER_EQUALS_SUCCESS_OUTCOME_ORDER_VERIFIED,
        ):
            self.assertTrue(value)

    def test_three_successes_form_exact_claim_and_outcome_prefix(self) -> None:
        facade, _, model, search, fetch = self.parent.build_facade(
            model_post=self.json_model_post()
        )
        ledger, registry, _ = self.build(facade=facade)
        model_result = ledger.run_model_json(
            system="private system",
            user="private user",
            max_output_tokens=200,
        )
        search_result = ledger.run_search_leads(
            query="private query",
            max_results=1,
        )
        page_result = ledger.run_fetched_page(url="https://example.test/page")
        outcomes = ledger.load_outcomes()
        claims = registry.load_claims()
        self.assertEqual([value["action_ordinal"] for value in outcomes], [1, 2, 3])
        self.assertEqual(
            [value["action_claim_sha256"] for value in outcomes],
            [value["claim_sha256"] for value in claims],
        )
        self.assertIsNone(outcomes[0]["previous_outcome_sha256"])
        self.assertEqual(
            outcomes[1]["previous_outcome_sha256"], outcomes[0]["outcome_sha256"]
        )
        self.assertEqual(
            outcomes[2]["previous_outcome_sha256"], outcomes[1]["outcome_sha256"]
        )
        for result in (model_result, search_result, page_result):
            validate_durable_action_success_outcome(result.receipt)
            validation = ledger.validate_outcome_against_ledger(result.receipt)
            self.assertTrue(
                validation["claim_to_success_outcome_durable_binding_replayed"]
            )
        encoded = json.dumps(
            [model_result.receipt, search_result.receipt, page_result.receipt],
            ensure_ascii=False,
        )
        for private in (
            "private system",
            "private user",
            "private query",
            "https://example.test/page",
            "synthetic page",
        ):
            self.assertNotIn(private, encoded)
        self.assertEqual(len(model._post.calls), 1)
        self.assertEqual(len(search._post.calls), 1)
        self.assertEqual(len(fetch.pools[0].urlopen_calls), 1)
        self.assertEqual(ledger.status()["state"], "clean")

    def test_transport_sees_claim_without_outcome_then_success_is_published(self) -> None:
        class ObservingPost:
            def __init__(self) -> None:
                self.registry = None
                self.ledger = None
                self.snapshots = []

            def __call__(self, _url, **_kwargs):
                self.snapshots.append(
                    (
                        self.registry.status()["allocated_action_count"],
                        len(tuple(self.ledger.outcomes_directory.iterdir())),
                    )
                )
                return parent_fixture.ModelResponse(
                    200,
                    parent_fixture.model_response_bytes(
                        text='{"ready":true,"value":"synthetic"}'
                    ),
                )

        post = ObservingPost()
        facade = self.parent.build_facade(model_post=post)[0]
        ledger, registry, _ = self.build(facade=facade)
        post.registry = registry
        post.ledger = ledger
        result = ledger.run_model_json(
            system="system", user="user", max_output_tokens=200
        )
        self.assertEqual(post.snapshots, [(1, 0)])
        self.assertEqual(result.receipt["action_ordinal"], 1)
        self.assertEqual(ledger.status()["durable_success_outcome_count"], 1)

    def test_invalid_request_or_transport_failure_quarantines_without_retry(self) -> None:
        ledger, registry, facade = self.build()
        with self.assertRaisesRegex(Exception, "exceeds facade limits"):
            ledger.run_model_json(
                system="x" * 5000,
                user="y",
                max_output_tokens=200,
            )
        self.assertEqual(registry.status()["allocated_action_count"], 1)
        self.assertEqual(ledger.status()["state"], "quarantined_uncertain_effect")
        with self.assertRaises(DurableActionOutcomeQuarantined):
            ledger.run_search_leads(query="next", max_results=1)
        self.assertEqual(registry.status()["allocated_action_count"], 1)
        self.assertEqual(len(facade._model_adapter._post.calls), 0)

        class FailingPost:
            def __init__(self) -> None:
                self.calls = 0

            def __call__(self, _url, **_kwargs):
                self.calls += 1
                raise RuntimeError("synthetic transport failure")

        failing = FailingPost()
        facade2 = self.parent.build_facade(model_post=failing)[0]
        ledger2, registry2, _ = self.build(facade=facade2)
        with self.assertRaises(Exception):
            ledger2.run_model_json(system="a", user="b", max_output_tokens=200)
        self.assertEqual(failing.calls, 1)
        self.assertEqual(registry2.status()["allocated_action_count"], 1)
        with self.assertRaises(DurableActionOutcomeQuarantined):
            ledger2.run_model_json(system="c", user="d", max_output_tokens=200)
        self.assertEqual(failing.calls, 1)

    def test_direct_parent_claim_is_detected_and_quarantined(self) -> None:
        ledger, registry, _ = self.build()
        registry._claim("search_leads")
        self.assertEqual(ledger.status()["unresolved_claim_count"], 1)
        with self.assertRaises(DurableActionOutcomeQuarantined):
            ledger.run_search_leads(query="query", max_results=1)

    def test_successful_effect_with_outcome_publish_failure_is_quarantined(self) -> None:
        facade, _, model, _, _ = self.parent.build_facade(
            model_post=self.json_model_post(2)
        )
        ledger, registry, _ = self.build(facade=facade)
        with mock.patch(
            "deepwide_agent.v24250_durable_action_outcome_ledger._publish_new",
            side_effect=RuntimeError("synthetic outcome publication failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "publication failure"):
                ledger.run_model_json(
                    system="a", user="b", max_output_tokens=200
                )
        self.assertEqual(len(model._post.calls), 1)
        self.assertEqual(registry.status()["allocated_action_count"], 1)
        self.assertEqual(ledger.status()["durable_success_outcome_count"], 0)
        self.assertEqual(ledger.status()["state"], "quarantined_uncertain_effect")
        with self.assertRaises(DurableActionOutcomeQuarantined):
            ledger.run_model_json(system="c", user="d", max_output_tokens=200)
        self.assertEqual(len(model._post.calls), 1)

    def test_reopen_continues_success_prefix(self) -> None:
        ledger, registry, facade = self.build()
        first = ledger.run_model_json(system="a", user="b", max_output_tokens=200)
        reopened_registry = DurableCandidateActionRegistry.open(
            root=registry.root,
            facade=facade,
        )
        reopened = DurableActionOutcomeLedger.open(
            root=ledger.root,
            registry=reopened_registry,
        )
        second = reopened.run_model_json(system="c", user="d", max_output_tokens=200)
        self.assertEqual(first.receipt["action_ordinal"], 1)
        self.assertEqual(second.receipt["action_ordinal"], 2)
        self.assertEqual(reopened.status()["durable_success_outcome_count"], 2)

    def test_single_inflight_lock_serializes_effect_and_success_order(self) -> None:
        class BlockingPost:
            def __init__(self) -> None:
                self.calls = 0
                self.active = 0
                self.max_active = 0
                self.lock = threading.Lock()

            def __call__(self, _url, **_kwargs):
                with self.lock:
                    self.calls += 1
                    self.active += 1
                    self.max_active = max(self.max_active, self.active)
                time.sleep(0.05)
                with self.lock:
                    self.active -= 1
                return parent_fixture.ModelResponse(
                    200,
                    parent_fixture.model_response_bytes(
                        text='{"ready":true,"value":"synthetic"}'
                    ),
                )

        post = BlockingPost()
        facade = self.parent.build_facade(model_post=post)[0]
        ledger, _, _ = self.build(facade=facade)
        barrier = threading.Barrier(2)
        ordinals = []
        errors = []

        def worker(label: str) -> None:
            try:
                barrier.wait()
                result = ledger.run_model_json(
                    system=label,
                    user=label,
                    max_output_tokens=200,
                )
                ordinals.append(result.receipt["action_ordinal"])
            except BaseException as error:
                errors.append(error)

        threads = [threading.Thread(target=worker, args=(str(index),)) for index in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(sorted(ordinals), [1, 2])
        self.assertEqual(post.calls, 2)
        self.assertEqual(post.max_active, 1)

    def test_outcome_tamper_residue_gap_symlink_hardlink_fail_closed(self) -> None:
        cases = ("tamper", "residue", "gap", "symlink", "hardlink")
        for case in cases:
            with self.subTest(case=case):
                ledger, _, _ = self.build()
                result = ledger.run_model_json(
                    system="a", user="b", max_output_tokens=200
                )
                path = ledger.outcomes_directory / "00000000000000000001.json"
                if case == "tamper":
                    value = copy.deepcopy(result.receipt)
                    value["terminal_status"] = "failure"
                    path.write_text(json.dumps(value), encoding="utf-8")
                elif case == "residue":
                    (ledger.outcomes_directory / "unexpected").write_text("x")
                elif case == "gap":
                    path.rename(ledger.outcomes_directory / "00000000000000000002.json")
                elif case == "symlink":
                    path.unlink()
                    path.symlink_to(ledger.initial_path)
                else:
                    os.link(path, ledger.outcomes_directory / "00000000000000000002.json")
                with self.assertRaises(DurableActionOutcomePoisoned):
                    ledger.load_outcomes()

    def test_initialization_requires_pristine_registry_and_disjoint_roots(self) -> None:
        facade = self.parent.build_facade(model_post=self.json_model_post())[0]
        root = Path(tempfile.mkdtemp(dir=self.root)).resolve()
        registry = DurableCandidateActionRegistry.initialize(root=root, facade=facade)
        registry._claim("model_json")
        outcome = Path(tempfile.mkdtemp(dir=self.root)).resolve()
        with self.assertRaisesRegex(ValueError, "not pristine"):
            DurableActionOutcomeLedger.initialize(root=outcome, registry=registry)

        root2 = Path(tempfile.mkdtemp(dir=self.root)).resolve()
        registry2 = DurableCandidateActionRegistry.initialize(root=root2, facade=facade)
        with self.assertRaisesRegex(ValueError, "overlap"):
            DurableActionOutcomeLedger.initialize(root=root2, registry=registry2)

    def test_registry_binding_drift_is_rejected(self) -> None:
        ledger, registry, _ = self.build()
        registry._facade._contract["model_maximum_output_tokens"] += 1
        with self.assertRaises(DurableActionOutcomeError):
            ledger.run_model_json(system="a", user="b", max_output_tokens=200)


if __name__ == "__main__":
    unittest.main()
