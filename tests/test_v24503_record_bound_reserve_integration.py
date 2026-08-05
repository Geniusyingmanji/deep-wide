from __future__ import annotations

import copy
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
from deepwide_agent.v24503_record_bound_reserve_integration import (  # noqa: E402
    run_v24503_task,
    validate_cross_artifacts,
    validate_record_bound_receipt,
    validate_result,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24447_third_source_entropy_to_decision import (  # noqa: E402
    KNOWN_BASELINE,
    clients as parent_clients,
)
from test_v24496_targeted_reserve_contradiction import (  # noqa: E402
    ReserveTargetedSearch,
)


class RecordReserveSearch(ReserveTargetedSearch):
    def __init__(self, *args, record_mode: str, **kwargs):
        super().__init__(*args, reserve_mode="support", **kwargs)
        self.record_mode = record_mode

    def fetch_urls(self, requests_):
        batches = super().fetch_urls(requests_)
        if self.fetch_invocations == 5:
            for batch in batches:
                for result in batch["results"]:
                    if self.record_mode == "split_support":
                        content = "Established\n2025"
                    elif self.record_mode == "split_conflict":
                        content = "Established\n2026"
                    elif self.record_mode == "foreign_subject":
                        content = "Gamma was founded in 2025."
                    else:
                        content = "Alpha was founded in 2025."
                    result["raw_content"] = content
        return batches


def clients(output: Path, clock: AdvancingClock, *, mode: str):
    model, old_search = parent_clients(output, clock, third=False)
    model.inner.timeout = MAXIMUM_PROVIDER_EFFECT_SECONDS
    model.inner.baseline = KNOWN_BASELINE
    search = RecordReserveSearch(clock, deadline=300, record_mode=mode)
    search.timeout = MAXIMUM_PROVIDER_EFFECT_SECONDS
    search.static_search_timeout_seconds = MAXIMUM_PROVIDER_EFFECT_SECONDS
    del old_search
    return model, search


def execute(mode: str):
    temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
    clock = AdvancingClock()
    model, search = clients(Path(temporary.name), clock, mode=mode)
    outcome = run_v24503_task(
        TASK,
        model=model,
        search=search,
        partition_seed_sha256=SEED,
        limits=limits(),
        monotonic=clock,
    )
    return temporary, outcome, model, search


class V24503RecordBoundReserveIntegrationTests(unittest.TestCase):
    fixture: dict[str, tuple]

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = {
            mode: execute(mode)
            for mode in (
                "split_support",
                "split_conflict",
                "foreign_subject",
                "same_line_support",
            )
        }

    @classmethod
    def tearDownClass(cls) -> None:
        for temporary, *_ in cls.fixture.values():
            temporary.cleanup()

    def test_split_record_adds_observations_and_incremental_decision_credit(self) -> None:
        _, outcome, _, _ = self.fixture["split_support"]
        parent_receipt = outcome.parent.reserve_result["reserve_support_receipt"]
        receipt = outcome.record_bound_result["record_bound_receipt"]
        self.assertEqual(parent_receipt["reserve_new_observation_count"], 0)
        self.assertGreaterEqual(receipt["added_observation_count"], 1)
        self.assertEqual(receipt["removed_observation_count"], 0)
        self.assertEqual(receipt["safe_change_improvement_count"], 1)
        self.assertEqual(receipt["safe_change_regression_count"], 0)
        self.assertGreater(receipt["decision_credit_gain_nats"], 0)
        self.assertEqual(receipt["decision_credit_regression_nats"], 0)
        self.assertIn(
            "| Alpha | 2025 |",
            outcome.record_bound_result["candidate_prediction"],
        )

    def test_split_conflict_enters_posterior_without_false_credit(self) -> None:
        _, outcome, _, _ = self.fixture["split_conflict"]
        receipt = outcome.record_bound_result["record_bound_receipt"]
        self.assertGreaterEqual(receipt["added_observation_count"], 1)
        self.assertEqual(receipt["safe_change_improvement_count"], 0)
        self.assertEqual(receipt["decision_credit_gain_nats"], 0)

    def test_foreign_subject_removal_is_explicit_regression_accounting(self) -> None:
        _, outcome, _, _ = self.fixture["foreign_subject"]
        parent_receipt = outcome.parent.reserve_result["reserve_support_receipt"]
        receipt = outcome.record_bound_result["record_bound_receipt"]
        self.assertGreater(parent_receipt["reserve_new_observation_count"], 0)
        self.assertGreater(receipt["removed_observation_count"], 0)
        self.assertGreater(receipt["rejected_parent_narrative_projection_count"], 0)
        self.assertGreater(receipt["safe_change_regression_count"], 0)
        self.assertGreater(receipt["decision_credit_regression_nats"], 0)
        self.assertNotIn(
            "| Alpha | 2025 |",
            outcome.record_bound_result["candidate_prediction"],
        )

    def test_same_line_target_support_is_semantically_equivalent(self) -> None:
        _, outcome, _, _ = self.fixture["same_line_support"]
        receipt = outcome.record_bound_result["record_bound_receipt"]
        self.assertEqual(receipt["added_observation_count"], 0)
        self.assertEqual(receipt["removed_observation_count"], 0)
        self.assertEqual(receipt["safe_change_improvement_count"], 0)
        self.assertEqual(receipt["safe_change_regression_count"], 0)
        self.assertEqual(receipt["decision_credit_gain_nats"], 0)
        self.assertEqual(receipt["decision_credit_regression_nats"], 0)
        self.assertEqual(
            outcome.record_bound_result["candidate_prediction"],
            outcome.parent.reserve_result["candidate_prediction"],
        )

    def test_pure_recovery_has_no_additional_external_effect(self) -> None:
        for mode, (_, outcome, model, search) in self.fixture.items():
            with self.subTest(mode=mode):
                effect = outcome.effect_equivalence_receipt
                self.assertFalse(effect["external_effect_detected"])
                receipt = outcome.record_bound_result["record_bound_receipt"]
                self.assertEqual(receipt["additional_model_requests"], 0)
                self.assertEqual(receipt["additional_logical_queries"], 0)
                self.assertEqual(receipt["additional_search_batches"], 0)
                self.assertEqual(receipt["additional_provider_search_calls"], 0)
                self.assertEqual(receipt["additional_fetch_calls"], 0)
                self.assertEqual(model.acquisitions, 2)
                self.assertEqual(search.request_invocations, 4)
                self.assertEqual(search.fetch_invocations, 5)

    def test_result_receipt_and_cross_artifacts_validate(self) -> None:
        for mode, (_, outcome, _, _) in self.fixture.items():
            with self.subTest(mode=mode):
                validate_result(outcome.record_bound_result)
                validate_record_bound_receipt(
                    outcome.record_bound_result["record_bound_receipt"]
                )
                validate_cross_artifacts(
                    outcome.parent.reserve_result,
                    outcome.record_bound_result,
                    model_before=outcome.model_slot_receipt_before_record_projection,
                    transport_before=outcome.transport_health_before_record_projection,
                    search_before=outcome.search_single_shot_receipt_before_record_projection,
                    model_after=outcome.model_slot_receipt,
                    transport_after=outcome.transport_health,
                    search_after=outcome.search_single_shot_receipt,
                    effect_equivalence_receipt=outcome.effect_equivalence_receipt,
                    expected_model_cap=2,
                )

    def test_result_receipt_parent_and_effect_tamper_fail_closed(self) -> None:
        _, outcome, _, _ = self.fixture["split_support"]
        result = copy.deepcopy(outcome.record_bound_result)
        result["record_bound_projection"]["record_bound_projections"][0][
            "value"
        ] = "2026"
        result.pop("result_sha256")
        result["result_sha256"] = payload_sha256(result)
        with self.assertRaises(ValueError):
            validate_result(result)
        receipt = copy.deepcopy(
            outcome.record_bound_result["record_bound_receipt"]
        )
        receipt["removed_observation_count"] += 1
        receipt.pop("receipt_sha256")
        receipt["receipt_sha256"] = payload_sha256(receipt)
        with self.assertRaises(ValueError):
            validate_record_bound_receipt(receipt)
        effect = copy.deepcopy(outcome.effect_equivalence_receipt)
        effect["external_effect_detected"] = True
        effect.pop("receipt_sha256")
        effect["receipt_sha256"] = payload_sha256(effect)
        with self.assertRaises(ValueError):
            validate_cross_artifacts(
                outcome.parent.reserve_result,
                outcome.record_bound_result,
                model_before=outcome.model_slot_receipt_before_record_projection,
                transport_before=outcome.transport_health_before_record_projection,
                search_before=outcome.search_single_shot_receipt_before_record_projection,
                model_after=outcome.model_slot_receipt,
                transport_after=outcome.transport_health,
                search_after=outcome.search_single_shot_receipt,
                effect_equivalence_receipt=effect,
                expected_model_cap=2,
            )

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("src/deepwide_agent/v24503_record_bound_reserve_integration.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
