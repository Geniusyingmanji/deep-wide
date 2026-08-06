from __future__ import annotations

import sys
import threading
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24630_exact220_contract import (  # noqa: E402
    ARM, EXECUTOR_CONCURRENCY, LIMITS, MODEL_SLOT_CAP, SELECTED_COUNT,
    selected_tasks,
)
from scripts import preregister_v24630_exact220 as prereg  # noqa: E402
from scripts import run_v24630_exact220 as runner  # noqa: E402


def visible(position: int) -> dict[str, str]:
    return {
        "opaque_id": f"task_{position:024x}",
        "question": "Return one table. The column names are: Name, Date.",
    }


class V24630Exact220Tests(unittest.TestCase):
    def test_contract_is_exact220_visible_only_and_fixed_denominator(self) -> None:
        value = prereg.build_forward_contract(ROOT, now=1, require_pristine=False)
        self.assertEqual(value["task_contract"]["runtime_boundary"], ["opaque_id", "question"])
        self.assertEqual(value["task_contract"]["selected_count"], 220)
        self.assertEqual(len(value["task_contract"]["selected_opaque_ids"]), 220)
        self.assertEqual(value["execution"]["arm"], ARM)
        self.assertEqual(value["execution"]["executor_concurrency"], 32)
        self.assertEqual(value["execution"]["model_slot_cap"], 8)
        self.assertTrue(value["fixed_denominator_contract"]["parent_timeout_or_failure_projects_fallback"])
        self.assertTrue(value["fixed_denominator_contract"]["child_success_or_receipt_completeness_not_required_for_postfreeze_evaluator"])
        self.assertNotIn("scripts/run_official_eval_local.py", value["dependency_manifest"])
        self.assertNotIn("outputs/runtime_manifest_v1_repro/evaluator_mapping.jsonl", value["dependency_manifest"])

    def test_selected_tasks_are_exact_visible_220(self) -> None:
        value = prereg.build_forward_contract(ROOT, now=1, require_pristine=False)
        tasks = selected_tasks(ROOT, value)
        self.assertEqual(len(tasks), SELECTED_COUNT)
        self.assertEqual(len({task["opaque_id"] for task in tasks}), SELECTED_COUNT)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))

    def test_scheduler_uses_full_32_task_concurrency_and_fixed_order(self) -> None:
        tasks = [visible(position) for position in range(1, SELECTED_COUNT + 1)]
        lock = threading.Lock()
        active = maximum = 0
        saturated = threading.Event()

        def fake(_root, _contract, position, task, _directory):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
                if active == EXECUTOR_CONCURRENCY:
                    saturated.set()
            self.assertTrue(saturated.wait(timeout=2))
            with lock:
                active -= 1
            result = runner._fallback(
                task, failure="Synthetic", elapsed=0.01, progress={},
                model_receipt=None, timed_out=False,
            )
            return runner.TaskOutcome(
                position, result, None, False, False, False, 0, 0, False,
                runner._empty_transport(), False, None, False, None,
            )

        outcomes = runner.execute_forward(ROOT, {}, tasks, task_runner=fake)
        self.assertEqual(len(outcomes), 220)
        self.assertEqual(maximum, EXECUTOR_CONCURRENCY)
        self.assertEqual([item.result["opaque_id"] for item in outcomes], [task["opaque_id"] for task in tasks])
        self.assertTrue(all(runner.PARENT_BOUNDS_FIELD in item.result for item in outcomes))

    def test_runtime_row_marks_fallback_terminal_completed_for_evaluator(self) -> None:
        result = runner._fallback(
            visible(1), failure="hard_deadline_timeout", elapsed=165,
            progress={}, model_receipt=None, timed_out=True,
        )
        row = runner._runtime_row(result)
        self.assertEqual(row["status"], "completed")
        self.assertEqual(row["completion_kind"], "hard_deadline_fallback")
        self.assertTrue(row["prediction"])
        summary = runner._summary(
            [
                runner.TaskOutcome(
                    1, result, None, False, False, False, 0, 0, False,
                    runner._empty_transport(), False, None, False, None,
                )
            ]
            * SELECTED_COUNT,
            1.0,
        )
        self.assertEqual(summary["completed"], 220)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["fallback_tables"], 220)

    def test_budget_and_concurrency_are_not_legacy_slow_defaults(self) -> None:
        self.assertEqual(LIMITS["wall_seconds"], 150)
        self.assertEqual(EXECUTOR_CONCURRENCY, 32)
        self.assertEqual(MODEL_SLOT_CAP, 8)


if __name__ == "__main__":
    unittest.main()
