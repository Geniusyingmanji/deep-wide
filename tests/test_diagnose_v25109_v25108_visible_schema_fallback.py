from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25108_verified_field_external_contract as contract  # noqa: E402
from scripts import diagnose_v25109_v25108_visible_schema_fallback as target  # noqa: E402


class V25109VisibleSchemaFallbackDiagnosisTests(unittest.TestCase):
    def test_frozen_failure_cooccurrence_and_parser_reproduction(self) -> None:
        value = target.build_diagnosis(now=1)
        reproduction = value["visible_only_parser_reproduction"]
        separation = value["failure_separation"]
        self.assertEqual(reproduction["legacy_visible_parser_empty_tasks"], 20)
        self.assertEqual(reproduction["empty_provider_fallback_result_only_tasks"], 20)
        self.assertEqual(separation["plan_transport_failure_tasks"], 8)
        self.assertEqual(separation["proposal_transport_failure_tasks"], 11)
        self.assertEqual(separation["representation_validation_failure_tasks"], 8)
        self.assertEqual(separation["plan_transport_and_representation_failure_tasks"], 8)
        self.assertEqual(
            separation[
                "proposal_only_transport_failure_without_representation_failure_tasks"
            ],
            3,
        )

    def test_diagnosis_is_label_blind_and_grants_build_only(self) -> None:
        value = target.build_diagnosis(now=1)
        self.assertFalse(
            value["content_policy"]
            ["mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"]
        )
        self.assertTrue(
            value["authorization"]["append_only_parser_and_runtime_successor_build"]
        )
        self.assertFalse(value["authorization"]["new_external_forward"])

    def test_resealed_root_count_credit_or_launch_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for kind in ("root", "count", "credit", "launch"):
            changed = copy.deepcopy(value)
            if kind == "root":
                changed["diagnosis"][
                    "root_cause_is_missing_columns_exactly_visible_anchor"
                ] = False
            elif kind == "count":
                changed["failure_separation"]["plan_transport_failure_tasks"] = 7
            elif kind == "credit":
                changed["diagnosis"]["entropy_or_information_gain_signed_credit"] = 1
            else:
                changed["authorization"]["new_external_forward"] = True
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
