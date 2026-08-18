from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25065_quote_verified_record_binding as quote  # noqa: E402
from deepwide_agent import v25541_visible_output_constraint_contract as constraints  # noqa: E402
from deepwide_agent import v25577_fresh_canonical_totality_population as target  # noqa: E402


class V25577FreshCanonicalTotalityPopulationTests(unittest.TestCase):
    def test_population_is_unique_split_and_hash_bound(self) -> None:
        identities = target.identity_vector()
        tasks = target.task_vector()
        self.assertEqual(len(identities), 40)
        self.assertEqual(len(set(identities)), 40)
        self.assertEqual(len(tasks), 20)
        self.assertEqual(target.DRIFT_TASK_COUNT, 10)
        self.assertEqual(target.ORDINARY_TASK_COUNT, 10)
        self.assertEqual(
            target.payload_sha256(identities),
            target.EXPECTED_IDENTITY_VECTOR_SHA256,
        )
        self.assertEqual(
            target.payload_sha256(tasks),
            target.EXPECTED_TASK_VECTOR_SHA256,
        )

    def test_visible_column_exposure_is_exact_ten_ten(self) -> None:
        drift = ordinary = 0
        for index in range(target.TASK_COUNT):
            columns = target.columns_for_index(index)
            canonical = quote._safe_columns(columns)
            if target.exposure_for_index(index) == "canonical_drift":
                drift += 1
                self.assertNotEqual(columns, canonical)
                self.assertEqual(canonical, target.ORDINARY_COLUMNS)
            else:
                ordinary += 1
                self.assertEqual(columns, canonical)
        self.assertEqual((drift, ordinary), (10, 10))

    def test_no_visible_constraint_family_confounds_totality(self) -> None:
        for index, task in enumerate(target.task_vector()):
            value = constraints.build_contract(
                task["question"], target.columns_for_index(index)
            )
            self.assertEqual(value["active_family_count"], 0)
            self.assertIsNone(value["date_format"])
            self.assertIsNone(value["numeric_scale"])
            self.assertIsNone(value["temporal_year_range"])
            self.assertIsNone(value["rank_slots"])
            self.assertIsNone(value["explicit_order"])

    def test_runtime_input_and_population_tamper_fail_closed(self) -> None:
        values = target.task_vector()
        self.assertEqual(target.validate_task_vector(values), values)
        for kind in ("question", "opaque", "extra", "denominator"):
            changed = copy.deepcopy(values)
            if kind == "question":
                changed[0]["question"] += " altered"
            elif kind == "opaque":
                changed[0]["opaque_id"] = changed[1]["opaque_id"]
            elif kind == "extra":
                changed[0]["category"] = "forbidden"
            else:
                changed.pop()
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_task_vector(changed)

    def test_gates_are_fixed_arm_blind_and_zero_credit(self) -> None:
        policy = target.source_policy()
        mechanism = target.mechanism_gate()
        quality = target.quality_gate()
        self.assertEqual(
            mechanism["required_predecessor_counterfactual_failure_tasks"], 10
        )
        self.assertEqual(
            mechanism["required_successor_canonical_column_handoff_tasks"], 10
        )
        self.assertEqual(
            mechanism["required_successor_ordinary_canonical_projection_tasks"],
            10,
        )
        self.assertEqual(quality["minimum_arm_blind_paired_complete_tasks"], 18)
        self.assertFalse(
            quality[
                "prediction_arm_outcome_or_score_used_for_completeness_selection"
            ]
        )
        self.assertFalse(
            policy[
                "endpoint_page_version_model_prediction_mapping_truth_evaluator_score_quality_or_outcome_used_for_selection"
            ]
        )
        self.assertEqual(mechanism["positive_signed_credit_count"], 0)
        self.assertEqual(quality["positive_signed_credit_count"], 0)

    def test_population_module_has_no_io_or_privileged_capability(self) -> None:
        source = Path(target.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        hits: list[str] = []
        forbidden_fields = {
            "category",
            "question_type",
            "task_category",
            "split",
            "ground_truth",
            "gold",
            "answer_key",
            "score",
            "reward",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Subscript) and isinstance(
                node.slice, ast.Constant
            ):
                if node.slice.value in forbidden_fields:
                    hits.append(str(node.slice.value))
        self.assertEqual(hits, [])
        for forbidden in (
            "os",
            "pathlib",
            "subprocess",
            "socket",
            "requests",
            "httpx",
            "urllib",
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )


if __name__ == "__main__":
    unittest.main()
