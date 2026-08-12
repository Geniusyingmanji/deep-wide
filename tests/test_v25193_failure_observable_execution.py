from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25193_failure_observable_execution as target  # noqa: E402


class V25193FailureObservableExecutionTests(unittest.TestCase):
    def _run(self, failing_stage: str | None) -> tuple[dict, dict[str, int]]:
        counts = {"runtime": 0, "conversion": 0, "row_validation": 0, "failure": 0}

        def runtime() -> dict:
            counts["runtime"] += 1
            if failing_stage == "runtime":
                raise ValueError("V2.51.80 result envelope drifted")
            return {"raw": True}

        def conversion(raw: dict) -> dict:
            counts["conversion"] += 1
            self.assertEqual(raw, {"raw": True})
            if failing_stage == "conversion":
                raise ValueError("V2.51.88 parent/counterfactual binding drifted")
            return {"terminal": True, "runtime_completed": True}

        def validate(row: dict) -> dict:
            counts["row_validation"] += 1
            if failing_stage == "row_validation" and row.get("runtime_completed"):
                raise RuntimeError("dynamic private row value")
            if set(row) not in (
                {"terminal", "runtime_completed"},
                {"terminal", "runtime_completed", "failure_observation"},
            ):
                raise AssertionError("test row drifted")
            return copy.deepcopy(row)

        def failure(observation: dict) -> dict:
            counts["failure"] += 1
            return {
                "terminal": True,
                "runtime_completed": False,
                "failure_observation": copy.deepcopy(observation),
            }

        value = target.execute_staged_once(
            runtime_stage=runtime,
            conversion_stage=conversion,
            row_validation_stage=validate,
            terminal_failure_factory=failure,
        )
        return value, counts

    def test_success_runs_each_stage_once_without_failure_factory(self) -> None:
        value, counts = self._run(None)
        self.assertTrue(value["runtime_completed"])
        self.assertEqual(
            counts,
            {"runtime": 1, "conversion": 1, "row_validation": 1, "failure": 0},
        )

    def test_runtime_failure_is_terminal_and_skips_later_success_stages(self) -> None:
        value, counts = self._run("runtime")
        self.assertFalse(value["runtime_completed"])
        self.assertEqual(
            value["failure_observation"]["outer_failure_stage"], "runtime"
        )
        self.assertEqual(
            value["failure_observation"]["failure_code"],
            "v25180_result_envelope_validation",
        )
        self.assertEqual(
            counts,
            {"runtime": 1, "conversion": 0, "row_validation": 1, "failure": 1},
        )

    def test_conversion_failure_is_terminal_and_static_mapped(self) -> None:
        value, counts = self._run("conversion")
        self.assertEqual(
            value["failure_observation"]["outer_failure_stage"], "conversion"
        )
        self.assertEqual(
            value["failure_observation"]["failure_code"],
            "v25188_parent_counterfactual_binding",
        )
        self.assertEqual(
            counts,
            {"runtime": 1, "conversion": 1, "row_validation": 1, "failure": 1},
        )

    def test_row_validation_failure_is_terminal_and_dynamic_text_absent(self) -> None:
        value, counts = self._run("row_validation")
        receipt = value["failure_observation"]
        self.assertEqual(receipt["outer_failure_stage"], "row_validation")
        self.assertEqual(receipt["failure_code"], "unclassified_runtime_error")
        self.assertNotIn("private row value", json.dumps(value))
        self.assertEqual(
            counts,
            {"runtime": 1, "conversion": 1, "row_validation": 2, "failure": 1},
        )

    def test_bad_callable_input_fails_before_any_stage(self) -> None:
        with self.assertRaises(TypeError):
            target.execute_staged_once(
                runtime_stage=None,  # type: ignore[arg-type]
                conversion_stage=lambda value: value,
                row_validation_stage=lambda value: value,
                terminal_failure_factory=lambda value: value,
            )

    def test_module_has_no_effect_or_privileged_field_access(self) -> None:
        path = ROOT / "src/deepwide_agent/v25193_failure_observable_execution.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        privileged = {
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
        hits = {
            str(node.slice.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value in privileged
        }
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertEqual(hits, set())
        self.assertTrue(
            calls.isdisjoint(
                {"complete", "search_many", "fetch_urls", "create_connection"}
            )
        )


if __name__ == "__main__":
    unittest.main()
