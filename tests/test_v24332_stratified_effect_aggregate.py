from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24332_stratified_effect_aggregate import (  # noqa: E402
    build_aggregate,
    build_task_receipt,
    payload_sha256,
    validate_aggregate,
    validate_task_receipt,
)


def complete_success():
    return build_task_receipt(
        terminal_kind="complete_success",
        effect_accounting_complete=True,
        logical_model_admissions=3,
        provider_model_requests=3,
        provider_model_attempts=3,
        slot_acquisitions=3,
        hosted_search_attempts=1,
        hard_fetch_helper_calls=10,
    )


def complete_fallback():
    return build_task_receipt(
        terminal_kind="complete_fallback",
        effect_accounting_complete=True,
        logical_model_admissions=3,
        provider_model_requests=2,
        provider_model_attempts=2,
        pre_provider_model_rejections=1,
        slot_acquisitions=2,
        slot_timeouts=1,
        deadline_exhausted_tasks=1,
    )


def incomplete_fallback():
    return build_task_receipt(
        terminal_kind="incomplete_fallback",
        effect_accounting_complete=False,
        slot_acquisitions=2,
        slot_timeouts=1,
        hosted_search_attempts=1,
        hard_fetch_helper_calls=7,
        deadline_exhausted_tasks=1,
        unattributed_model_effects_lower_bound=2,
        unattributed_model_attempts_lower_bound=3,
        unattributed_search_effects_lower_bound=1,
        unattributed_fetch_effects_lower_bound=7,
    )


class V24332StratifiedEffectAggregateTests(unittest.TestCase):
    def test_complete_success_has_strict_conservation(self) -> None:
        value = build_aggregate([complete_success()])
        validate_aggregate(value)
        self.assertTrue(value["complete_subset_conservation_verified"])
        self.assertEqual(value["complete_tasks"], 1)
        self.assertEqual(value["incomplete_tasks"], 0)
        self.assertTrue(value["promotion_passed"])

    def test_complete_fallback_can_conserve_with_preprovider_rejection(self) -> None:
        value = build_aggregate([complete_success(), complete_fallback()])
        complete = value["complete_task_totals"]
        self.assertEqual(complete["logical_model_admissions"], 6)
        self.assertEqual(complete["provider_model_requests"], 5)
        self.assertEqual(complete["pre_provider_model_rejections"], 1)
        self.assertEqual(complete["slot_acquisitions"], 5)
        self.assertEqual(complete["slot_timeouts"], 1)
        self.assertTrue(value["promotion_passed"])

    def test_incomplete_fallback_preserves_lower_bounds_but_fails_frozen_gate(self) -> None:
        value = build_aggregate(
            [complete_success(), incomplete_fallback()],
            maximum_incomplete_tasks=0,
        )
        self.assertTrue(value["incomplete_lower_bounds_verified"])
        self.assertFalse(value["global_equality_asserted_across_incomplete_lower_bounds"])
        self.assertFalse(value["promotion_checks"]["incomplete_task_count"])
        self.assertFalse(value["promotion_passed"])

    def test_tampered_incomplete_lower_bound_is_rejected(self) -> None:
        altered = copy.deepcopy(incomplete_fallback())
        altered["unattributed_fetch_effects_lower_bound"] = 6
        with self.assertRaisesRegex(ValueError, "lower bound drifted"):
            validate_task_receipt(altered)

    def test_resealed_aggregate_promotion_tamper_is_rejected(self) -> None:
        value = build_aggregate(
            [complete_success(), incomplete_fallback()],
            maximum_incomplete_tasks=0,
        )
        altered = copy.deepcopy(value)
        altered["promotion_passed"] = True
        altered.pop("aggregate_payload_sha256")
        altered["aggregate_payload_sha256"] = payload_sha256(altered)
        with self.assertRaisesRegex(ValueError, "aggregate identity drifted"):
            validate_aggregate(altered)


if __name__ == "__main__":
    unittest.main()
