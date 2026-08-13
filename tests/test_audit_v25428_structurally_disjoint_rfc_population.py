from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25428_structurally_disjoint_rfc_population as target  # noqa: E402


class V25428StructurallyDisjointRfcPopulationAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_audit(now=1)

    def test_consumed_bindings_require_exact_source_forward_pairs(self) -> None:
        consumed = self.value["consumed_bindings"]
        self.assertEqual(len(consumed), 7)
        self.assertEqual(
            {row["interval"] for row in consumed},
            {
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
            all(row["forward_score_metric_or_quality_read"] is False for row in consumed)
        )

    def test_structural_parser_rejects_non_eighty_or_nonrange(self) -> None:
        valid = b"RFC_NUMBERS = tuple(range(9240, 9320))\n"
        self.assertEqual(target.structural_rfc_range(valid), (9240, 9319))
        for source in (
            b"RFC_NUMBERS = tuple(range(9240, 9319))\n",
            b"RFC_NUMBERS = [x for x in range(9240, 9320)]\n",
            b"RFC_NUMBERS = tuple(range(9240, 9320))\nRFC_NUMBERS = tuple(range(9160, 9240))\n",
        ):
            with self.assertRaises(ValueError):
                target.structural_rfc_range(source)

    def test_first_zero_intersection_selection_is_fixed(self) -> None:
        self.assertEqual(
            self.value["candidate_interval_order"],
            ["RFC 9320-9399", "RFC 9240-9319", "RFC 9160-9239"],
        )
        self.assertEqual(
            self.value["candidate_consumed_overlap_identity_counts"],
            {"RFC 9320-9399": 80, "RFC 9240-9319": 0, "RFC 9160-9239": 0},
        )
        self.assertEqual(
            self.value["selected_first_zero_intersection_interval"],
            "RFC 9240-9319",
        )

    def test_presence_is_disclosed_but_not_a_selection_input(self) -> None:
        self.assertTrue(
            self.value[
                "aggregate_candidate_identity_presence_observed_before_freeze"
            ]
        )
        self.assertEqual(
            self.value["aggregate_candidate_identity_presence_count"], 80
        )
        self.assertFalse(
            self.value["aggregate_presence_used_for_selection_replacement_or_ranking"]
        )
        self.assertFalse(
            self.value[
                "candidate_field_value_page_quality_prediction_evaluator_or_per_task_outcome_read_for_selection"
            ]
        )

    def test_audit_authorizes_only_protocol_design_and_tamper_fails(self) -> None:
        self.assertEqual(target.validate_audit(self.value), self.value)
        authorization = self.value["authorization"]
        self.assertTrue(
            authorization["combined_membership_list_atomic_external_protocol_design"]
        )
        self.assertFalse(authorization["candidate_page_endpoint_or_field_preflight"])
        self.assertFalse(
            authorization["network_model_search_fetch_external_forward_or_evaluator"]
        )
        changed = copy.deepcopy(self.value)
        changed["candidate_consumed_overlap_identity_counts"]["RFC 9240-9319"] = 1
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = target.population.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
