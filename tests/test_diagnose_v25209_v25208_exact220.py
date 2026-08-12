from __future__ import annotations

import ast
import copy
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25209_v25208_exact220 as target  # noqa: E402


class V25209V25208Exact220DiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_complete_score_is_current_but_not_best(self) -> None:
        value = self.value["benchmark_result"]
        self.assertEqual(value["selected"], 220)
        self.assertEqual(value["whole_table_successes"], 5)
        self.assertAlmostEqual(value["quality_composite"], 0.39866919974486725)
        self.assertEqual(value["v25130_whole_table_success_delta"], 4)
        self.assertEqual(value["v24857_whole_table_success_delta"], -4)
        self.assertFalse(value["sota"])
        self.assertFalse(value["avg_at_4"])

    def test_fallbacks_are_partitioned_by_failure_layer(self) -> None:
        value = self.value["runtime_reliability"]
        self.assertEqual(value["runtime_completed_tasks"], 209)
        self.assertEqual(value["failure_as_zero_tasks"], 11)
        self.assertEqual(value["fallback_tables"], 16)
        self.assertEqual(value["outer_failure_fallback_tables"], 11)
        self.assertEqual(value["completed_production_fallback_tables"], 5)
        self.assertEqual(
            value["outer_failure_code_counts"],
            {"v25135_receipt_validation": 10, "v25180_receipt_validation": 1},
        )
        self.assertEqual(
            value["completed_failure_type_counts"],
            {"post_effect:ValueError": 1, "production:ValueError": 5},
        )

    def test_evaluator_errors_are_separate_from_forward_failures(self) -> None:
        value = self.value["evaluator_reliability"]
        self.assertEqual(value["evaluator_rows"], 220)
        self.assertEqual(value["valid_rows"], 214)
        self.assertEqual(value["invalid_rows"], 6)
        self.assertEqual(
            value["invalid_code_counts"],
            {"internal_error": 5, "out_of_range_metric": 1},
        )

    def test_quote_aware_and_entropy_effects_are_zero(self) -> None:
        value = self.value["mechanism"]
        self.assertEqual(value["quote_aware_repair_applied_count"], 0)
        self.assertEqual(value["same_raw_counterfactual_active_tasks"], 0)
        self.assertEqual(value["prediction_changed_tasks"], 0)
        self.assertEqual(value["positive_signed_credit_count"], 0)
        self.assertFalse(value["fullset_score_attributable_to_quote_aware_repair"])
        self.assertFalse(value["entropy_or_information_gain_policy_effect"])

    def test_next_authority_is_build_only(self) -> None:
        diagnosis = self.value["diagnosis"]
        self.assertTrue(diagnosis["reliability_precedes_new_search_or_credit_treatment"])
        self.assertTrue(diagnosis["first_reliability_target_is_receipt_validation"])
        self.assertTrue(
            diagnosis["next_candidate_is_content_free_receipt_disposition_observer_build_only"]
        )
        authorization = self.value["authorization"]
        self.assertTrue(authorization["content_free_receipt_disposition_observer_build_only"])
        self.assertFalse(authorization["runtime_policy_or_prediction_change"])
        self.assertFalse(authorization["new_exact220_launch"])
        self.assertFalse(authorization["evaluator_or_revaluation"])

    def test_output_is_aggregate_only_and_source_reads_no_privileged_fields(self) -> None:
        encoded = json.dumps(self.value, ensure_ascii=False, sort_keys=True)
        self.assertIsNone(re.search(r"task_[0-9a-f]{24}", encoded))
        observed_keys: set[str] = set()

        def visit(value):
            if isinstance(value, dict):
                observed_keys.update(value)
                for item in value.values():
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        visit(self.value)
        for forbidden in (
            "opaque_id",
            "question",
            "prediction",
            "query",
            "url",
            "page",
            "gold",
            "category",
            "split",
            "ground_truth",
            "answer_key",
            "instance_id",
            "per_task",
        ):
            self.assertNotIn(forbidden, observed_keys)
        self.assertEqual(
            target.RUNTIME_ROW_FIELDS,
            {
                "runtime_completed",
                "failure_as_zero",
                "prediction_kind",
                "failure_types",
                "failure_observation",
                "effect_health",
                "content_free_receipt",
            },
        )
        tree = ast.parse((ROOT / target.SOURCE).read_text(encoding="utf-8"))
        subscript_keys = {
            node.slice.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        }
        self.assertTrue(
            subscript_keys.isdisjoint(
                {
                    "opaque_id",
                    "question",
                    "category",
                    "question_type",
                    "split",
                    "ground_truth",
                    "gold",
                    "answer_key",
                    "instance_id",
                }
            )
        )

    def test_resealed_result_launch_credit_or_content_tamper_fails(self) -> None:
        for kind in ("result", "launch", "credit", "content"):
            changed = copy.deepcopy(self.value)
            if kind == "result":
                changed["benchmark_result"]["whole_table_successes"] = 9
            elif kind == "launch":
                changed["authorization"]["new_exact220_launch"] = True
            elif kind == "credit":
                changed["mechanism"]["positive_signed_credit_count"] = 1
            else:
                changed["content_policy"][
                    "historical_outcome_used_as_future_runtime_router_signal"
                ] = True
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_diagnosis(changed)

    def test_publication_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "diagnosis.json"
            target.publish_exclusive(path, self.value)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), self.value)
            with self.assertRaises(FileExistsError):
                target.publish_exclusive(path, self.value)


if __name__ == "__main__":
    unittest.main()
