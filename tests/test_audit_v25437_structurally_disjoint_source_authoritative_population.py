from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25437_structurally_disjoint_source_authoritative_population as target  # noqa: E402


class V25437StructurallyDisjointSourceAuthoritativeAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_audit(now=1)

    def test_consumed_bindings_require_eight_exact_terminal_pairs(self) -> None:
        consumed = self.value["consumed_bindings"]
        self.assertEqual(len(consumed), 8)
        self.assertEqual(
            {row["interval"] for row in consumed},
            {
                "RFC 9240-9319",
                "RFC 9320-9399",
                "RFC 9400-9479",
                "RFC 9480-9559",
                "RFC 9600-9679",
                "RFC 9680-9759",
                "RFC 9720-9799",
                "RFC 9800-9879",
            },
        )
        self.assertTrue(
            all(
                row["forward_task_count"] == row["forward_terminal_tasks"]
                for row in consumed
            )
        )
        self.assertTrue(
            all(
                row["forward_score_metric_or_quality_read"] is False
                for row in consumed
            )
        )

    def test_structural_parser_rejects_non_eighty_or_ambiguous_source(self) -> None:
        valid = b"RFC_NUMBERS = tuple(range(9160, 9240))\n"
        self.assertEqual(target.structural_rfc_range(valid), (9160, 9239))
        for source in (
            b"RFC_NUMBERS = tuple(range(9160, 9239))\n",
            b"RFC_NUMBERS = [x for x in range(9160, 9240)]\n",
            b"RFC_NUMBERS = tuple(range(9160, 9240))\nRFC_NUMBERS = tuple(range(9240, 9320))\n",
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                target.structural_rfc_range(source)

    def test_first_remaining_zero_intersection_block_is_fixed(self) -> None:
        self.assertEqual(
            self.value["candidate_interval_order"],
            ["RFC 9320-9399", "RFC 9240-9319", "RFC 9160-9239"],
        )
        self.assertEqual(
            self.value["candidate_consumed_overlap_identity_counts"],
            {"RFC 9320-9399": 80, "RFC 9240-9319": 80, "RFC 9160-9239": 0},
        )
        self.assertEqual(
            self.value["selected_first_zero_intersection_interval"],
            "RFC 9160-9239",
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
        self.assertTrue(authorization["source_authoritative_external_protocol_design"])
        self.assertFalse(authorization["candidate_page_endpoint_or_field_preflight"])
        self.assertFalse(
            authorization["network_model_search_fetch_external_forward_or_evaluator"]
        )
        self.assertFalse(
            authorization["deepwidebench_forward_evaluator_leaderboard_or_sota"]
        )

    def test_audit_replay_and_tamper_fail_closed(self) -> None:
        self.assertEqual(target.validate_audit(self.value), self.value)
        changed = copy.deepcopy(self.value)
        changed["candidate_consumed_overlap_identity_counts"]["RFC 9160-9239"] = 1
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = target.population.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
