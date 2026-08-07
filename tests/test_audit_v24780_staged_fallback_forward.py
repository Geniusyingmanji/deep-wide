from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24780_staged_fallback_execution_contract as contract  # noqa: E402
from scripts import audit_v24780_staged_fallback_forward as audit  # noqa: E402


def _task_receipt(
    ordinal: int,
    *,
    acquisitions: int = 2,
    slot_timeouts: int = 0,
    hosted_attempts: int = 1,
    hard_fetches: int = 10,
    deadline_rejections: int = 0,
) -> dict:
    return {
        "ordinal": ordinal,
        "parent_receipt_sha256": f"{ordinal:064x}",
        "parent_receipt_valid": True,
        "failure_taxonomy": "success",
        "model_receipt_sha256": f"{ordinal + 8:064x}",
        "model_receipt_present": True,
        "model_receipt_valid": True,
        "model_acquisitions": acquisitions,
        "model_slot_timeouts": slot_timeouts,
        "transport_receipt_sha256": f"{ordinal + 16:064x}",
        "transport_receipt_present": True,
        "transport_receipt_valid": True,
        "hosted_search_attempts": hosted_attempts,
        "hard_fetch_helper_calls": hard_fetches,
        "fetch_deadline_rejections": deadline_rejections,
        "parent_effect_receipt_flags_match": True,
    }


def _metrics(receipts: list[dict]) -> dict[str, int]:
    values = {
        "content_free_effect_receipt_pair_count": len(receipts),
        "valid_model_receipt_count": sum(row["model_receipt_valid"] for row in receipts),
        "valid_transport_receipt_count": sum(
            row["transport_receipt_valid"] for row in receipts
        ),
        "model_acquisition_count": sum(row["model_acquisitions"] or 0 for row in receipts),
        "model_slot_timeout_count": sum(row["model_slot_timeouts"] or 0 for row in receipts),
        "hosted_search_attempt_count": sum(row["hosted_search_attempts"] or 0 for row in receipts),
        "hard_fetch_helper_call_count": sum(row["hard_fetch_helper_calls"] or 0 for row in receipts),
        "fetch_deadline_rejection_count": sum(
            row["fetch_deadline_rejections"] or 0 for row in receipts
        ),
    }
    values["all_task_fetch_request_count"] = (
        values["hard_fetch_helper_call_count"]
        + values["fetch_deadline_rejection_count"]
    )
    return values


def _audit_value(receipts: list[dict]) -> dict:
    metrics: dict[str, int | float] = {
        **_metrics(receipts),
        "valid_task_results": 8,
        "projected_failure_tasks": 0,
        "forward_wall_seconds": 12.5,
        "changed_task_count": 1,
        "changed_cell_count": 1,
        "founded_changed_cell_count": 1,
        "country_changed_cell_count": 0,
        "nonunknown_changed_cell_count": 0,
        "projection_backed_support_set_count": 1,
        "initial_fetch_request_count": 64,
        "reserve_fetch_request_count": 8,
        "actual_fetch_request_count": 72,
        "initial_usable_page_count": 40,
        "reserve_usable_page_count": 4,
        "actual_usable_page_count": 44,
        "final_entity_slots_with_two_usable_identity_sources": 4,
        "entity_slots_brought_to_two_sources_by_reserve": 1,
        "reserve_target_entity_count": 8,
        "failed_url_retry_count": 0,
        "scheduler_contract_failed_task_count": 0,
    }
    checks = {name: True for name in audit.GATE_CHECK_NAMES}
    value = {
        "artifact_version": 1,
        "role": "v24780_staged_fallback_forward_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": 0,
        "protocol_sha256": "a" * 64,
        "forward_result_sha256": "b" * 64,
        "prediction_freeze_sha256": "c" * 64,
        "run_summary_sha256": "d" * 64,
        "task_effect_receipts": receipts,
        "parent_failure_taxonomy_counts": {"success": 8},
        "content_free_metrics": metrics,
        "gate_checks": checks,
        "forward_health_go": True,
        "mechanism_go": True,
        "findings": [],
        "protected_watchers": [],
        "source_policy": {
            "prediction_jsonl_opened_or_parsed": False,
            "prediction_jsonl_bytes_hashed_for_freeze_integrity": True,
            "private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "authorization": {
            "quality_preregistration_design": True,
            "private_truth_or_quality_surface_open": False,
            "additional_forward_retry_resume_or_rerun": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def _reseal(value: dict) -> dict:
    value.pop("audit_payload_sha256", None)
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


class V24780StagedFallbackForwardAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.receipts = [_task_receipt(index) for index in range(1, 9)]

    def test_synthetic_content_free_audit_round_trip(self) -> None:
        value = _audit_value(copy.deepcopy(self.receipts))
        self.assertEqual(audit.validate_audit(value), value)
        self.assertEqual(value["content_free_metrics"]["model_acquisition_count"], 16)
        self.assertEqual(value["content_free_metrics"]["hard_fetch_helper_call_count"], 80)

    def test_effect_cap_helper_enforces_fixed_eight_task_denominator(self) -> None:
        receipts = copy.deepcopy(self.receipts[:-1])
        checks = audit._effect_cap_checks(
            receipts, _metrics(receipts), successful_result_fetches=63
        )
        self.assertFalse(
            checks["eight_of_eight_content_free_effect_receipt_pairs_valid"]
        )
        value = _audit_value(receipts)
        with self.assertRaises(RuntimeError):
            audit.validate_audit(value)

    def test_model_acquisition_or_slot_timeout_over_cap_fails_closed(self) -> None:
        for field, value in (("model_acquisitions", 3), ("model_slot_timeouts", 1)):
            receipts = copy.deepcopy(self.receipts)
            receipts[0][field] = value
            checks = audit._effect_cap_checks(
                receipts, _metrics(receipts), successful_result_fetches=72
            )
            self.assertFalse(
                checks[
                    "model_acquisitions_within_frozen_caps"
                    if field == "model_acquisitions"
                    else "model_logical_attempts_within_frozen_caps"
                ]
            )

    def test_failed_task_cannot_hide_fetch_effect_over_cap(self) -> None:
        receipts = copy.deepcopy(self.receipts)
        receipts[0]["failure_taxonomy"] = "result_envelope_invalid"
        receipts[0]["hard_fetch_helper_calls"] = 11
        checks = audit._effect_cap_checks(
            receipts, _metrics(receipts), successful_result_fetches=60
        )
        self.assertFalse(checks["physical_fetch_helpers_within_frozen_caps"])
        self.assertFalse(checks["all_task_fetch_requests_within_frozen_caps"])

    def test_deadline_rejected_fetch_still_counts_against_request_cap(self) -> None:
        receipts = copy.deepcopy(self.receipts)
        receipts[0]["hard_fetch_helper_calls"] = 10
        receipts[0]["fetch_deadline_rejections"] = 1
        checks = audit._effect_cap_checks(
            receipts, _metrics(receipts), successful_result_fetches=72
        )
        self.assertTrue(checks["physical_fetch_helpers_within_frozen_caps"])
        self.assertFalse(checks["all_task_fetch_requests_within_frozen_caps"])

    def test_resealed_receipt_metric_or_gate_tamper_is_rejected(self) -> None:
        for mutate in (
            lambda value: value["task_effect_receipts"][0].__setitem__(
                "hard_fetch_helper_calls", 11
            ),
            lambda value: value["content_free_metrics"].__setitem__(
                "hard_fetch_helper_call_count", 79
            ),
            lambda value: value["gate_checks"].__setitem__(
                "physical_fetch_helpers_within_frozen_caps", False
            ),
        ):
            value = _audit_value(copy.deepcopy(self.receipts))
            mutate(value)
            _reseal(value)
            with self.assertRaises(RuntimeError):
                audit.validate_audit(value)

    def test_source_policy_is_content_free_and_does_not_open_predictions(self) -> None:
        source = Path(audit.__file__).read_text(encoding="utf-8")
        self.assertNotIn("read_text(encoding=\"utf-8\").splitlines", source)
        value = _audit_value(copy.deepcopy(self.receipts))
        self.assertFalse(value["source_policy"]["prediction_jsonl_opened_or_parsed"])
        self.assertFalse(
            value["source_policy"][
                "mapping_gold_category_question_type_split_evaluator_score_reward_read"
            ]
        )


if __name__ == "__main__":
    unittest.main()
