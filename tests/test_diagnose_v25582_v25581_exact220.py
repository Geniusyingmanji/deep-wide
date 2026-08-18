from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25582_v25581_exact220 as target  # noqa: E402


class V25582V25581Exact220DiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_fallback_taxonomy_separates_search_from_terminal_failure(self) -> None:
        value = self.value["fallback_diagnosis"]
        self.assertEqual(value["fallback_tasks"], 10)
        self.assertTrue(value["all_completed_search_and_fetch"])
        self.assertEqual(
            value["query_fetch_model_histogram"],
            {"query4_fetch10_model3": 10},
        )
        self.assertEqual(
            value["failure_taxonomy"],
            {
                "local_unrecoverable_table_normalization": 6,
                "plan_and_synthesis_model_request_error": 1,
                "synthesis_model_request_error": 3,
            },
        )
        self.assertEqual(value["grounded_plan_model_success_tasks"], 10)
        self.assertEqual(value["base_synthesis_success_tasks"], 0)

    def test_quality_and_record_funnel_are_exact(self) -> None:
        quality = self.value["quality_diagnosis"]
        self.assertEqual(quality["evaluator_invalid_or_not_run"], 5)
        self.assertEqual(
            quality["evaluator_terminal_error_taxonomy"],
            {
                "official_internal_error": 4,
                "official_out_of_range_metrics": 1,
            },
        )
        self.assertEqual(
            quality["evaluator_valid_quality_bands"]["f1_by_row"],
            {"equal_zero": 125, "below_0_2": 147, "at_least_0_5": 41},
        )
        funnel = self.value["record_correction_funnel"]
        self.assertEqual(funnel["grounded_target_plan_strategy_tasks"], 63)
        self.assertEqual(funnel["target_record_frontier_engaged_tasks"], 9)
        self.assertEqual(funnel["grounded_record_source_tasks"], 8)
        self.assertEqual(funnel["verified_fields"], 3)
        self.assertEqual(funnel["missing_base_row_rejected_fields"], 3)
        self.assertEqual(funnel["changed_safe_coordinates"], 0)
        self.assertFalse(funnel["record_correction_identified_as_quality_treatment"])

    def test_membership_regression_is_aggregate_and_bounded(self) -> None:
        value = self.value["visible_membership_regression"]
        self.assertEqual(
            value["grammar_source_histogram"],
            {"explicit_row_phrase": 11, "none": 209},
        )
        self.assertEqual(value["constraint_applied_tasks"], 11)
        self.assertEqual(value["visible_member_count_histogram"], {"1": 11})
        self.assertEqual(value["base_table_row_count_histogram"], {"0": 2, "1": 9})
        self.assertEqual(
            value["same_fixed_grammar_subset_metrics"]["v25379"]["entity_acc"],
            0.8181818181818182,
        )
        for version in ("v25406", "v25573", "v25581"):
            for name in target.METRIC_NAMES:
                self.assertEqual(
                    value["same_fixed_grammar_subset_metrics"][version][name],
                    0.0,
                )
        self.assertTrue(
            value["cold_cross_version_metrics_are_regression_signal_not_causal_effect"]
        )

    def test_cross_version_recovery_is_not_overattributed(self) -> None:
        value = self.value["cross_version_descriptive_not_causal"]
        self.assertEqual(value["v25573_outer_failure_tasks"], 11)
        self.assertEqual(
            value["same_tasks_v25581_model_generated_canonical_handoff"], 10
        )
        self.assertEqual(value["same_tasks_v25581_fallback"], 1)
        self.assertEqual(
            value["same_tasks_metrics_v25581"]["whole_table_successes"], 1
        )
        self.assertEqual(
            value["exact_transition_histogram"], {"00": 215, "01": 1, "11": 4}
        )
        self.assertTrue(
            value["independent_cold_rollouts_do_not_identify_wrapper_causality"]
        )

    def test_resealed_tamper_or_authorization_fails(self) -> None:
        for path, replacement in (
            (("record_correction_funnel", "changed_safe_coordinates"), 1),
            (("authorization", "deepwidebench_forward_or_evaluator"), True),
        ):
            changed = copy.deepcopy(self.value)
            changed.pop("diagnosis_payload_sha256")
            cursor = changed
            for name in path[:-1]:
                cursor = cursor[name]
            cursor[path[-1]] = replacement
            changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(
                changed
            )
            with self.subTest(path=path), self.assertRaises(ValueError):
                target.validate_diagnosis(changed)

    def test_published_shape_has_no_per_task_material(self) -> None:
        forbidden = {
            "opaque_id",
            "instance_id",
            "question",
            "prediction",
            "answer",
            "evaluator_error",
            "per_task",
        }
        hits: list[str] = []

        def walk(value: object) -> None:
            if isinstance(value, dict):
                hits.extend(str(key) for key in value if key in forbidden)
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(self.value)
        self.assertEqual(hits, [])
        self.assertTrue(self.value["postfreeze_offline_analysis_only"])
        self.assertEqual(self.value["positive_signed_credit_count"], 0)

    def test_source_has_no_external_or_runtime_privileged_capability(self) -> None:
        tree = ast.parse((ROOT / target.SOURCE).read_text(encoding="utf-8"))
        imports: list[str] = []
        privileged = {
            "category",
            "question_type",
            "task_category",
            "ground_truth",
            "answer_key",
            "reward",
        }
        hits: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Subscript) and isinstance(
                node.slice, ast.Constant
            ):
                if node.slice.value in privileged:
                    hits.append(str(node.slice.value))
        self.assertEqual(hits, [])
        self.assertFalse(
            any(
                name in {"socket", "subprocess", "urllib", "requests", "httpx"}
                or "evaluator" in name
                for name in imports
            )
        )


if __name__ == "__main__":
    unittest.main()
