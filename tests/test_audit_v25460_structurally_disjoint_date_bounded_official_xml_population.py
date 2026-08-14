from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25460_structurally_disjoint_date_bounded_official_xml_population as target  # noqa: E402


class V25460StructurallyDisjointDateBoundedPopulationAuditTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_audit(now=1, require_clean=False)

    def test_consumed_bindings_require_eleven_exact_terminal_pairs(self) -> None:
        consumed = self.value["consumed_bindings"]
        self.assertEqual(len(consumed), 11)
        self.assertIn("RFC 9000-9079", {row["interval"] for row in consumed})
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
        valid = b"RFC_NUMBERS = tuple(range(8920, 9000))\n"
        self.assertEqual(target.structural_rfc_range(valid), (8920, 8999))
        for source in (
            b"RFC_NUMBERS = tuple(range(8920, 8999))\n",
            b"RFC_NUMBERS = [x for x in range(8920, 9000)]\n",
            b"RFC_NUMBERS = tuple(range(8920, 9000))\nRFC_NUMBERS = tuple(range(9000, 9080))\n",
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                target.structural_rfc_range(source)

    def test_forward_parser_decodes_only_role_and_terminal_denominators(self) -> None:
        secret = "OUTCOME_VALUE_MUST_NOT_BE_DECODED"
        blob = (
            '{"role":"terminal_role","tasks":[{"prediction":"'
            + secret
            + '"}],"aggregate":{"task_count":20,"score":"'
            + secret
            + '","terminal_tasks":20}}'
        ).encode()
        decoded_inputs: list[object] = []
        original = target.json.loads

        def observed(value: object, *args: object, **kwargs: object) -> object:
            decoded_inputs.append(value)
            return original(value, *args, **kwargs)

        with mock.patch.object(target.json, "loads", side_effect=observed):
            self.assertEqual(
                target._forward_identity_and_terminal_counts(blob),
                ("terminal_role", 20, 20),
            )
        self.assertTrue(decoded_inputs)
        self.assertTrue(all(secret not in str(value) for value in decoded_inputs))
        self.assertEqual(
            self.value["historical_forward_decoded_fields"],
            ["role", "aggregate.task_count", "aggregate.terminal_tasks"],
        )
        self.assertFalse(
            self.value["historical_forward_unselected_values_decoded"]
        )

    def test_selected_block_is_zero_overlap_and_immediately_preceding(self) -> None:
        self.assertEqual(self.value["lower_most_consumed_interval_start"], 9000)
        self.assertEqual(self.value["selected_interval"], "RFC 8920-8999")
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
        self.assertTrue(
            authorization["date_bounded_official_xml_external_protocol_design"]
        )
        self.assertFalse(authorization["candidate_page_endpoint_or_field_preflight"])
        self.assertFalse(
            authorization["network_model_search_fetch_external_forward_or_evaluator"]
        )
        self.assertFalse(
            authorization["deepwidebench_forward_evaluator_leaderboard_or_sota"]
        )
        self.assertFalse(authorization["reuse_v25454_population_or_forward"])

    def test_audit_replay_and_tamper_fail_closed(self) -> None:
        self.assertEqual(target.validate_audit(self.value), self.value)
        for kind in ("overlap", "selection", "authorization"):
            changed = copy.deepcopy(self.value)
            if kind == "overlap":
                changed["selected_consumed_overlap_identity_count"] = 1
            elif kind == "selection":
                changed["selected_interval"] = "RFC 9000-9079"
            else:
                changed["authorization"]["reuse_v25454_population_or_forward"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.population.payload_sha256(
                changed
            )
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
