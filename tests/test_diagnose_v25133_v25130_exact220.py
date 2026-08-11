from __future__ import annotations

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

from scripts import diagnose_v25133_v25130_exact220 as target  # noqa: E402


class V25133V25130Exact220DiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_frozen_scores_and_cost_regression(self) -> None:
        runs = self.value["runs"]
        self.assertEqual(runs["v25130"]["whole_table_successes"], 1)
        self.assertEqual(runs["v24857"]["whole_table_successes"], 9)
        self.assertAlmostEqual(
            runs["v25130"]["quality_composite"], 0.3778654237910814
        )
        self.assertAlmostEqual(
            runs["v24857"]["quality_composite"], 0.45724897824812605
        )
        comparison = self.value["v25130_minus_v24857"]
        self.assertEqual(comparison["whole_table_success_delta"], -8)
        self.assertLess(comparison["quality_composite_delta"], 0)
        self.assertGreater(comparison["system_total_token_ratio"], 3.8)

    def test_outer_failure_decomposition_is_schema_totality_first(self) -> None:
        value = self.value["runtime_decomposition"]
        self.assertEqual(value["outer_failure_rows"], 27)
        self.assertEqual(value["outer_failure_types"], {"ValueError": 27})
        self.assertEqual(value["zero_effect_outer_failures"], 26)
        self.assertEqual(value["zero_effect_and_exact_schema_absent"], 26)
        self.assertEqual(value["nonzero_effect_outer_failures"], 1)
        self.assertEqual(value["nonzero_effect_and_exact_schema_present"], 1)
        self.assertEqual(value["runtime_completed_candidate_fallbacks"], 9)

    def test_dense_pairing_sparse_mechanism_funnel(self) -> None:
        value = self.value["mechanism_funnel"]
        self.assertEqual(value["runtime_completed_tasks"], 193)
        self.assertEqual(value["paired_synthesis_salience_tasks"], 193)
        self.assertEqual(value["prediction_identity_handoff_tasks"], 190)
        self.assertEqual(value["retrieval_mechanism_engaged_tasks"], 3)
        self.assertEqual(value["attributable_prediction_changed_tasks"], 3)
        self.assertEqual(value["unattributable_prediction_changed_tasks"], 0)

    def test_next_design_is_build_only_and_credit_remains_zero(self) -> None:
        diagnosis = self.value["diagnosis"]
        self.assertTrue(diagnosis["next_candidate_requires_schema_total_visible_fallback"])
        self.assertTrue(
            diagnosis["next_candidate_uses_one_production_synthesis_without_verified_gain"]
        )
        self.assertTrue(
            diagnosis["second_synthesis_allowed_only_after_same_forward_verified_gain"]
        )
        self.assertEqual(diagnosis["entropy_or_information_gain_signed_credit"], 0)
        self.assertFalse(self.value["authorization"]["new_exact220_launch"])
        self.assertFalse(self.value["authorization"]["fresh_external_protocol_or_launch"])
        self.assertFalse(self.value["authorization"]["evaluator_or_revaluation"])

    def test_output_is_aggregate_and_has_no_task_or_content_surface(self) -> None:
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
            "per_task",
            "ground_truth",
            "answer_key",
        ):
            self.assertNotIn(forbidden, observed_keys)
        self.assertEqual(
            target.RUNTIME_ROW_FIELDS,
            {
                "opaque_id",
                "runtime_completed",
                "failure_as_zero",
                "outer_failure_type",
                "model_success",
                "actual_effect_snapshot",
            },
        )

    def test_resealed_score_launch_credit_or_content_tamper_fails(self) -> None:
        for kind in ("score", "launch", "credit", "content"):
            changed = copy.deepcopy(self.value)
            if kind == "score":
                changed["runs"]["v25130"]["whole_table_successes"] = 9
            elif kind == "launch":
                changed["authorization"]["new_exact220_launch"] = True
            elif kind == "credit":
                changed["diagnosis"]["entropy_or_information_gain_signed_credit"] = 1
            else:
                changed["content_policy"][
                    "task_identifier_question_prediction_query_url_page_gold_category_split_or_per_task_score_emitted"
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
