from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25541_visible_output_constraint_contract as constraints  # noqa: E402
from deepwide_agent import v25570_fresh_totality_population as target  # noqa: E402


class V25570FreshTotalityPopulationTests(unittest.TestCase):
    def test_static_population_is_unique_hash_bound_and_date_only(self) -> None:
        identities = target.identity_vector()
        tasks = target.task_vector()
        self.assertEqual(len(identities), 40)
        self.assertEqual(len(set(identities)), 40)
        self.assertEqual(len(tasks), 20)
        self.assertEqual(target.DATE_TASK_COUNT, 20)
        self.assertEqual(target.SCALE_TASK_COUNT, 0)
        self.assertEqual(
            target.payload_sha256(identities), target.EXPECTED_IDENTITY_VECTOR_SHA256
        )
        self.assertEqual(
            target.payload_sha256(tasks), target.EXPECTED_TASK_VECTOR_SHA256
        )

    def test_all_tasks_activate_date_and_order_only(self) -> None:
        for row in target.task_vector():
            value = constraints.build_contract(row["question"], target.DATE_COLUMNS)
            self.assertEqual(value["active_family_count"], 2)
            self.assertEqual(value["date_format"]["style"], "chinese_ymd_unpadded")
            self.assertEqual(value["explicit_order"]["direction"], "descending")
            self.assertIsNone(value["numeric_scale"])
            self.assertIsNone(value["rank_slots"])

    def test_visible_unknown_semantics_and_task_tamper_fail_closed(self) -> None:
        values = target.task_vector()
        self.assertTrue(
            all("no stable release must use Unknown" in row["question"] for row in values)
        )
        self.assertEqual(target.validate_task_vector(values), values)
        for kind in ("question", "opaque", "denominator"):
            changed = copy.deepcopy(values)
            if kind == "question":
                changed[0]["question"] += " altered"
            elif kind == "opaque":
                changed[0]["opaque_id"] = changed[1]["opaque_id"]
            else:
                changed.pop()
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_task_vector(changed)

    def test_quality_gate_is_arm_blind_fixed20_and_zero_credit(self) -> None:
        policy = target.source_policy()
        gate = target.quality_gate()
        mechanism = target.mechanism_gate()
        self.assertTrue(gate["fixed20_failure_as_zero_metrics_reported"])
        self.assertEqual(gate["minimum_arm_blind_paired_complete_tasks"], 18)
        self.assertTrue(gate["paired_complete_selection_uses_only_truth_availability"])
        self.assertFalse(
            gate["prediction_arm_outcome_or_score_used_for_completeness_selection"]
        )
        self.assertFalse(
            policy[
                "endpoint_page_version_date_model_prediction_mapping_truth_evaluator_score_quality_or_outcome_used_for_selection"
            ]
        )
        self.assertFalse(
            policy["historical_parent_replay_routes_or_selects_fresh_forward_tasks"]
        )
        self.assertEqual(mechanism["positive_signed_credit_count"], 0)
        self.assertEqual(gate["positive_signed_credit_count"], 0)

    def test_population_module_has_no_io_or_privileged_capability(self) -> None:
        source = Path(target.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        privileged: list[str] = []
        forbidden_fields = {
            "category",
            "question_type",
            "task_category",
            "split",
            "ground_truth",
            "answer_key",
            "score",
            "reward",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and node.slice.value in forbidden_fields
            ):
                privileged.append(str(node.slice.value))
        self.assertEqual(privileged, [])
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
                any(name == forbidden or name.startswith(forbidden + ".") for name in imports)
            )


if __name__ == "__main__":
    unittest.main()
