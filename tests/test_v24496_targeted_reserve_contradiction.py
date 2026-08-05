from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24438_bounded_narrative_effect_runner import (  # noqa: E402
    MAXIMUM_PROVIDER_EFFECT_SECONDS,
)
from deepwide_agent.v24496_targeted_reserve_contradiction import (  # noqa: E402
    MAXIMUM_TOTAL_TARGETED_FETCHES,
    run_v24496_task,
    validate_effect_delta_receipt,
    validate_reserve_receipt,
    validate_result,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24447_third_source_entropy_to_decision import (  # noqa: E402
    KNOWN_BASELINE,
    clients as parent_clients,
)
from test_v24490_entropy_targeted_support_search import (  # noqa: E402
    TargetedSupportSearch,
)


class ReserveTargetedSearch(TargetedSupportSearch):
    def __init__(self, *args, reserve_mode: str, **kwargs):
        super().__init__(*args, targeted_mode="support", **kwargs)
        self.reserve_mode = reserve_mode
        self.reserve_urls: list[str] = []

    def _request(self, queries):  # type: ignore[override]
        payload = super()._request(queries)
        if self.request_invocations == 4:
            sources = payload["output"][0]["action"]["sources"]
            sources[-1]["title"] = "Alpha founding history independent archive"
        return payload

    def fetch_urls(self, requests_):
        batches = super().fetch_urls(requests_)
        if self.fetch_invocations == 4 and self.reserve_mode != "parent_success":
            # Force the original one-source V2.44.90 selection to have no
            # usable page, without changing the frozen discovery response.
            for batch in batches:
                for result in batch["results"]:
                    result["raw_content"] = ""
        elif self.fetch_invocations == 5:
            self.reserve_urls = [str(item["url"]) for item in requests_]
            for batch in batches:
                for index, result in enumerate(batch["results"]):
                    if self.reserve_mode == "support":
                        year = "2025"
                    elif self.reserve_mode == "conflict":
                        year = "2026"
                    else:
                        year = "2025" if index == 0 else "2026"
                    result["raw_content"] = (
                        f"Alpha was founded in {year} and later expanded."
                    )
        return batches


def clients(output: Path, clock: AdvancingClock, *, mode: str):
    model, old_search = parent_clients(output, clock, third=False)
    model.inner.timeout = MAXIMUM_PROVIDER_EFFECT_SECONDS
    model.inner.baseline = KNOWN_BASELINE
    search = ReserveTargetedSearch(clock, deadline=300, reserve_mode=mode)
    search.timeout = MAXIMUM_PROVIDER_EFFECT_SECONDS
    search.static_search_timeout_seconds = MAXIMUM_PROVIDER_EFFECT_SECONDS
    del old_search
    return model, search


def execute(mode: str):
    temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
    clock = AdvancingClock()
    model, search = clients(Path(temporary.name), clock, mode=mode)
    outcome = run_v24496_task(
        TASK,
        model=model,
        search=search,
        partition_seed_sha256=SEED,
        limits=limits(),
        monotonic=clock,
    )
    return temporary, outcome, model, search


class V24496TargetedReserveContradictionTests(unittest.TestCase):
    fixture: dict[str, tuple]

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = {
            mode: execute(mode)
            for mode in ("support", "conflict", "parent_success")
        }

    @classmethod
    def tearDownClass(cls) -> None:
        for temporary, *_ in cls.fixture.values():
            temporary.cleanup()

    def test_unusable_first_page_uses_frozen_reserve_and_gets_incremental_credit(self) -> None:
        _, outcome, model, search = self.fixture["support"]
        parent_receipt = outcome.parent.targeted_result["targeted_support_receipt"]
        receipt = outcome.reserve_result["reserve_support_receipt"]
        effect = outcome.effect_delta_receipt
        self.assertEqual(parent_receipt["targeted_discovered_source_count"], 3)
        self.assertEqual(parent_receipt["targeted_selected_source_count"], 1)
        self.assertEqual(parent_receipt["targeted_usable_page_count"], 0)
        self.assertEqual(receipt["reserve_candidate_source_count"], 2)
        self.assertEqual(receipt["reserve_selected_source_count"], 2)
        self.assertEqual(receipt["reserve_alternative_visible_source_count"], 1)
        self.assertEqual(receipt["reserve_alternative_blind_source_count"], 1)
        self.assertEqual(receipt["reserve_usable_page_count"], 2)
        self.assertEqual(receipt["total_targeted_selected_source_count"], 3)
        self.assertEqual(
            receipt["maximum_total_targeted_fetches"],
            MAXIMUM_TOTAL_TARGETED_FETCHES,
        )
        self.assertEqual(receipt["safe_change_improvement_count"], 1)
        self.assertEqual(receipt["safe_change_regression_count"], 0)
        self.assertGreater(receipt["decision_credit_gain_nats"], 0)
        self.assertEqual(receipt["decision_credit_regression_nats"], 0)
        self.assertEqual(receipt["additional_logical_queries"], 0)
        self.assertEqual(receipt["additional_search_batches"], 0)
        self.assertEqual(receipt["additional_model_requests"], 0)
        self.assertEqual(effect["additional_provider_search_attempts"], 0)
        self.assertEqual(effect["additional_fetch_attempts"], 2)
        self.assertEqual(effect["additional_model_acquisitions"], 0)
        self.assertEqual(model.acquisitions, 2)
        self.assertEqual(search.request_invocations, 4)
        self.assertEqual(search.fetch_invocations, 5)
        self.assertIn("| Alpha | 2025 |", outcome.reserve_result["candidate_prediction"])

    def test_conflicting_reserve_is_not_awarded_incremental_decision_credit(self) -> None:
        _, outcome, _, _ = self.fixture["conflict"]
        receipt = outcome.reserve_result["reserve_support_receipt"]
        self.assertGreater(receipt["reserve_conflicting_target_observation_count"], 0)
        self.assertEqual(receipt["safe_change_improvement_count"], 0)
        self.assertEqual(receipt["decision_credit_gain_nats"], 0)
        self.assertEqual(receipt["decision_credit_total_nats_after_reserve"], 0)
        self.assertNotIn("| Alpha | 2025 |", outcome.reserve_result["candidate_prediction"])

    def test_parent_safe_change_is_zero_reserve_effect(self) -> None:
        _, outcome, model, search = self.fixture["parent_success"]
        parent_receipt = outcome.parent.targeted_result["targeted_support_receipt"]
        receipt = outcome.reserve_result["reserve_support_receipt"]
        effect = outcome.effect_delta_receipt
        self.assertEqual(parent_receipt["safe_change_count_after_targeted_search"], 1)
        self.assertEqual(receipt["reserve_selected_source_count"], 0)
        self.assertEqual(receipt["reserve_usable_page_count"], 0)
        self.assertEqual(receipt["reserve_new_observation_count"], 0)
        self.assertEqual(receipt["decision_credit_gain_nats"], 0)
        self.assertEqual(receipt["decision_credit_regression_nats"], 0)
        self.assertEqual(effect["additional_fetch_effects"], 0)
        self.assertEqual(effect["additional_model_acquisitions"], 0)
        self.assertEqual(model.acquisitions, 2)
        self.assertEqual(search.request_invocations, 4)
        self.assertEqual(search.fetch_invocations, 4)

    def test_receipts_result_and_effect_validate(self) -> None:
        for mode in self.fixture:
            with self.subTest(mode=mode):
                _, outcome, _, _ = self.fixture[mode]
                # run_v24496_task already completed one full replay validation;
                # keep this assertion on its sealed return and independently
                # exercise the compact receipt/effect validators here.
                self.assertEqual(
                    outcome.reserve_result["result_sha256"],
                    payload_sha256(
                        {
                            key: value
                            for key, value in outcome.reserve_result.items()
                            if key != "result_sha256"
                        }
                    ),
                )
                validate_reserve_receipt(
                    outcome.reserve_result["reserve_support_receipt"]
                )
                validate_effect_delta_receipt(outcome.effect_delta_receipt)

    def test_coordinated_private_credit_threshold_and_effect_tamper_fail_closed(self) -> None:
        _, outcome, _, _ = self.fixture["support"]
        private = copy.deepcopy(outcome.reserve_result)
        private["reserve_private_state"]["selected_reserve_leads"][0]["title"] += " tamper"
        private.pop("result_sha256")
        private["result_sha256"] = payload_sha256(private)
        with self.assertRaises(ValueError):
            validate_result(private)
        receipt = copy.deepcopy(
            outcome.reserve_result["reserve_support_receipt"]
        )
        receipt["decision_credit_gain_nats"] = 0.0
        receipt.pop("receipt_sha256")
        receipt["receipt_sha256"] = payload_sha256(receipt)
        with self.assertRaises(ValueError):
            validate_reserve_receipt(receipt)
        receipt = copy.deepcopy(
            outcome.reserve_result["reserve_support_receipt"]
        )
        receipt["minimum_alternative_posterior"] = 0.7
        receipt.pop("receipt_sha256")
        receipt["receipt_sha256"] = payload_sha256(receipt)
        with self.assertRaises(ValueError):
            validate_reserve_receipt(receipt)
        effect = copy.deepcopy(outcome.effect_delta_receipt)
        effect["additional_provider_search_attempts"] = 1
        effect.pop("receipt_sha256")
        effect["receipt_sha256"] = payload_sha256(effect)
        with self.assertRaises(ValueError):
            validate_effect_delta_receipt(effect)

    def test_public_receipt_contains_no_private_content_and_runtime_is_label_blind(self) -> None:
        _, outcome, _, _ = self.fixture["support"]
        encoded = json.dumps(
            outcome.reserve_result["reserve_support_receipt"],
            ensure_ascii=False,
            sort_keys=True,
        )
        for prohibited in (
            TASK["question"],
            TASK["opaque_id"],
            "targeted-alpha-four.example",
            "2025",
            "query_vector",
            "raw_content",
            "candidate_prediction",
        ):
            self.assertNotIn(prohibited, encoded)
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("src/deepwide_agent/v24496_targeted_reserve_contradiction.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])

    def test_privileged_input_is_rejected_before_any_effect(self) -> None:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        clock = AdvancingClock()
        model, search = clients(Path(temporary.name), clock, mode="support")
        with self.assertRaises(ValueError):
            run_v24496_task(
                {**TASK, "category": "forbidden"},
                model=model,
                search=search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=clock,
            )
        self.assertEqual(model.acquisitions, 0)
        self.assertEqual(search.calls, 0)
        self.assertEqual(search.fetch_calls, 0)


if __name__ == "__main__":
    unittest.main()
