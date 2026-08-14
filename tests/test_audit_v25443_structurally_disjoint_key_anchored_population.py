from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25443_structurally_disjoint_key_anchored_population as target  # noqa: E402


class V25443StructurallyDisjointKeyAnchoredPopulationAuditTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_audit(now=1)

    def test_consumed_bindings_require_nine_exact_terminal_pairs(self) -> None:
        consumed = self.value["consumed_bindings"]
        self.assertEqual(len(consumed), 9)
        self.assertIn("RFC 9160-9239", {row["interval"] for row in consumed})
        self.assertTrue(
            all(
                row["forward_task_count"] == row["forward_terminal_tasks"]
                for row in consumed
            )
        )
        self.assertTrue(
            all(
                row["forward_score_metric_quality_or_per_task_outcome_read"]
                is False
                for row in consumed
            )
        )

    def test_structural_parser_rejects_non_eighty_or_ambiguous_source(self) -> None:
        valid = b"RFC_NUMBERS = tuple(range(9080, 9160))\n"
        self.assertEqual(target.structural_rfc_range(valid), (9080, 9159))
        for source in (
            b"RFC_NUMBERS = tuple(range(9080, 9159))\n",
            b"RFC_NUMBERS = [x for x in range(9080, 9160)]\n",
            b"RFC_NUMBERS = tuple(range(9080, 9160))\nRFC_NUMBERS = tuple(range(9160, 9240))\n",
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                target.structural_rfc_range(source)

    def test_selected_block_is_zero_overlap_and_immediately_preceding(self) -> None:
        self.assertEqual(self.value["lower_most_consumed_interval_start"], 9160)
        self.assertEqual(self.value["selected_interval"], "RFC 9080-9159")
        self.assertEqual(
            self.value["selected_consumed_overlap_identity_count"], 0
        )
        self.assertEqual(
            self.value["selection_rule"], "immediately_preceding_whole_block"
        )

    def test_selection_is_label_blind_and_has_no_endpoint_preflight(self) -> None:
        self.assertFalse(
            self.value[
                "candidate_endpoint_page_field_value_prediction_evaluator_or_per_task_outcome_read_for_selection"
            ]
        )
        self.assertFalse(
            self.value[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read"
            ]
        )
        self.assertFalse(
            self.value["individual_identity_or_task_retained_replaced_or_ranked"]
        )
        self.assertEqual(self.value["positive_signed_credit_count"], 0)

    def test_only_external_protocol_design_is_authorized(self) -> None:
        authorization = self.value["authorization"]
        self.assertTrue(authorization["key_anchored_external_protocol_design"])
        self.assertFalse(authorization["candidate_page_endpoint_or_field_preflight"])
        self.assertFalse(
            authorization["network_model_search_fetch_external_forward_or_evaluator"]
        )
        self.assertFalse(
            authorization["deepwidebench_forward_evaluator_leaderboard_or_sota"]
        )
        self.assertFalse(authorization["reuse_v25438_population_or_forward"])

    def test_audit_replay_and_tamper_fail_closed(self) -> None:
        self.assertEqual(target.validate_audit(self.value), self.value)
        for kind in ("overlap", "selection", "authorization"):
            changed = copy.deepcopy(self.value)
            if kind == "overlap":
                changed["selected_consumed_overlap_identity_count"] = 1
            elif kind == "selection":
                changed["selected_interval"] = "RFC 9160-9239"
            else:
                changed["authorization"]["reuse_v25438_population_or_forward"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.population.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
