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

from scripts import diagnose_v25410_v25406_grounded_membership_exact220 as target  # noqa: E402


class V25410V25406DiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_authoritative_aggregate_recomputes(self) -> None:
        value = self.value
        counts = value["funnel"]["counts"]
        self.assertEqual(counts["task_count"], 220)
        self.assertEqual(counts["runtime_completed_tasks"], 209)
        self.assertEqual(counts["outer_failure_as_zero_tasks"], 11)
        self.assertEqual(counts["visible_membership_task_count"], 11)
        self.assertEqual(
            counts["completed_grounded_record_constraint_applied_tasks"], 9
        )
        self.assertEqual(
            counts["grounded_record_constraint_applied_with_raw_record_tasks"],
            0,
        )
        self.assertEqual(counts["grounded_raw_record_count"], 14)
        self.assertEqual(counts["raw_records_outside_membership_constraint"], 14)
        self.assertEqual(counts["selected_raw_record_count"], 18)
        self.assertEqual(counts["verified_record_count"], 3)
        self.assertEqual(counts["changed_safe_tasks"], 1)

    def test_failure_comparison_and_no_go_recompute(self) -> None:
        value = self.value
        counts = value["funnel"]["counts"]
        self.assertEqual(counts["outer_value_error_tasks"], 11)
        self.assertEqual(counts["outer_three_provider_success_tasks"], 11)
        self.assertEqual(counts["outer_effect_health_event_count"], 0)
        self.assertEqual(counts["matched_v25379_runtime_completed_tasks"], 11)
        self.assertEqual(counts["matched_v25379_model_generated_tasks"], 11)
        self.assertEqual(value["decision"]["v25406_quality"], "no_go")
        self.assertFalse(value["decision"]["public_exact220_successor_authorized"])
        self.assertFalse(
            value["decision"][
                "historical_score_correctness_or_evaluator_feedback_runtime_routing"
            ]
        )

    def test_resealed_count_or_authorization_tamper_fails(self) -> None:
        value = self.value
        for path, replacement in (
            (("funnel", "counts", "visible_membership_task_count"), 12),
            (("authorization", "new_external_forward"), True),
        ):
            changed = copy.deepcopy(value)
            changed.pop("diagnosis_payload_sha256")
            cursor = changed
            for key in path[:-1]:
                cursor = cursor[key]
            cursor[path[-1]] = replacement
            changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(
                changed
            )
            with self.assertRaises(ValueError):
                target.validate_diagnosis(changed)

    def test_source_has_no_external_or_privileged_capability(self) -> None:
        tree = ast.parse((ROOT / target.SOURCE).read_text(encoding="utf-8"))
        imports: list[str] = []
        privileged = {
            "category",
            "question_type",
            "task_category",
            "ground_truth",
            "answer_key",
            "split",
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
