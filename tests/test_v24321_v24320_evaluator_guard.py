from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import ARMS, SELECTED_COUNT  # noqa: E402
from deepwide_agent.v24321_v24320_evaluator_guard import integrity_checks  # noqa: E402
from scripts import finalize_v24320_guarded_by_v24321 as guarded  # noqa: E402


def fixtures():
    summaries = {}
    shared = {}
    for arm in ARMS:
        summaries[arm] = {
            "selected": 64,
            "completed": 64,
            "failed": 0,
            "parent_exit_observability": {
                "receipts_present": 64,
                "receipts_valid": 64,
                "valid_child_terminal_receipts": 64,
                "valid_model_slot_receipts": 64,
                "valid_transport_receipts": 64,
                "accepted_parent_successes": 64,
                "non_success_parent_exits": 0,
                "incomplete_effect_counts": 0,
            },
            "mechanism_totals": {
                "effect_count_complete": 64,
                "effect_attribution_complete": 64,
                "provider_attempt_count_complete": 64,
                "fourth_model_effect": 0,
            },
        }
        shared[arm] = {
            "valid": 64,
            "invalid": 0,
            "all_complete_counts_match": True,
            "logical_admissions_lower_bound": 130,
            "provider_requests_lower_bound": 128,
            "pre_provider_rejections_lower_bound": 2,
            "slot_acquisitions_from_valid_receipts": 128,
            "slot_timeouts_from_valid_receipts": 2,
        }
    forward = {
        "terminal_predictions_per_arm": {arm: SELECTED_COUNT for arm in ARMS},
        "both_arms_exact64_before_mapping_gold_or_evaluator_open": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "official_evaluator_called": False,
        "shared_model_receipts": shared,
    }
    return forward, summaries


class V24321EvaluatorGuardTests(unittest.TestCase):
    def test_exact_complete_forward_is_positive(self) -> None:
        forward, summaries = fixtures()
        checks = integrity_checks(forward, summaries)
        self.assertTrue(checks)
        self.assertTrue(all(checks.values()))

    def test_each_incomplete_class_fails_closed(self) -> None:
        mutations = (
            lambda f, s: s["baseline"]["parent_exit_observability"].__setitem__(
                "non_success_parent_exits", 1
            ),
            lambda f, s: s["candidate"]["parent_exit_observability"].__setitem__(
                "incomplete_effect_counts", 1
            ),
            lambda f, s: f["shared_model_receipts"]["baseline"].__setitem__(
                "all_complete_counts_match", False
            ),
            lambda f, s: f["shared_model_receipts"]["candidate"].__setitem__(
                "slot_timeouts_from_valid_receipts", 1
            ),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                forward, summaries = fixtures()
                mutate(forward, summaries)
                self.assertFalse(all(integrity_checks(forward, summaries).values()))

    def test_guarded_entrypoint_checks_before_finalizer_import(self) -> None:
        source = inspect.getsource(guarded.main)
        self.assertLess(source.index("validate_live_decision"), source.index("import finalize"))
        self.assertLess(source.index("decision.get(\"passed\")"), source.index("import finalize"))
        self.assertLess(source.index("lease_observation"), source.index("import finalize"))
        self.assertLess(source.index("protected_watcher_snapshot"), source.index("import finalize"))


if __name__ == "__main__":
    unittest.main()
