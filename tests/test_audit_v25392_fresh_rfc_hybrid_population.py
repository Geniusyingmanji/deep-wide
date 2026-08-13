from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25392_fresh_rfc_hybrid_population as target  # noqa: E402


class V25392FreshRfcHybridPopulationAuditTests(unittest.TestCase):
    def test_parent_tree_and_history_scan_are_zero(self) -> None:
        self.assertEqual(target._aggregate_history_scan(), (0, 0))

    def test_valid_audit_is_aggregate_only_and_effect_free(self) -> None:
        value = target.build_audit(now=1)
        self.assertEqual(target.validate_audit(value), value)
        self.assertEqual(value["identity_count"], 80)
        self.assertFalse(value["candidate_page_endpoint_model_evaluator_or_quality_opened"])
        self.assertFalse(value["network_model_search_fetch_evaluator_benchmark_or_api_called"])
        self.assertFalse(value["entropy_or_information_gain_assigns_signed_credit"])

    def test_nonzero_tree_or_history_collision_fails_closed(self) -> None:
        for counts in ((1, 0), (0, 1)):
            with self.subTest(counts=counts), mock.patch.object(
                target, "_aggregate_history_scan", return_value=counts
            ):
                with self.assertRaises(ValueError):
                    target.build_audit(now=1)

    def test_resealed_privileged_effect_or_replacement_tamper_fails(self) -> None:
        original = target.build_audit(now=1)
        for kind in ("privileged", "effect", "replacement"):
            changed = copy.deepcopy(original)
            if kind == "privileged":
                changed[
                    "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read"
                ] = True
            elif kind == "effect":
                changed["authorization"][
                    "network_model_search_fetch_external_forward_or_evaluator"
                ] = True
            else:
                changed[
                    "individual_identity_or_task_retained_replaced_or_selected_using_scan_outcome"
                ] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.population.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
