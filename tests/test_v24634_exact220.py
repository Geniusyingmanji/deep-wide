from __future__ import annotations

import ast
import copy
import sys
import threading
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24634_exact220_contract import (  # noqa: E402
    ARM, CROSS_VERSION_POPULATION_POLICY, EXECUTOR_CONCURRENCY, LIMITS,
    MODEL_SLOT_CAP, SELECTED_COUNT, SINGLE_CHANGE_CONTRACT, selected_tasks,
    validate_capacity_parent,
)
from deepwide_agent import v24630_exact220_contract as parent_contract  # noqa: E402
from scripts import preregister_v24634_exact220 as prereg  # noqa: E402
from scripts import run_v24634_exact220 as runner  # noqa: E402


def visible(position: int) -> dict[str, str]:
    return {
        "opaque_id": f"task_{position:024x}",
        "question": "Return one table. The column names are: Name, Date.",
    }


class V24634Exact220Tests(unittest.TestCase):
    def test_contract_is_exact220_visible_only_and_fixed_denominator(self) -> None:
        value = prereg.build_forward_contract(ROOT, now=1, require_pristine=False)
        self.assertEqual(value["task_contract"]["runtime_boundary"], ["opaque_id", "question"])
        self.assertEqual(value["task_contract"]["selected_count"], 220)
        self.assertEqual(len(value["task_contract"]["selected_opaque_ids"]), 220)
        self.assertEqual(value["execution"]["arm"], ARM)
        self.assertEqual(value["execution"]["executor_concurrency"], 20)
        self.assertEqual(value["execution"]["model_slot_cap"], 8)
        self.assertTrue(value["fixed_denominator_contract"]["parent_timeout_or_failure_projects_fallback"])
        self.assertTrue(value["fixed_denominator_contract"]["child_success_or_receipt_completeness_not_required_for_postfreeze_evaluator"])
        self.assertNotIn("scripts/run_official_eval_local.py", value["dependency_manifest"])
        self.assertNotIn("outputs/runtime_manifest_v1_repro/evaluator_mapping.jsonl", value["dependency_manifest"])
        self.assertEqual(value["single_change_contract"], SINGLE_CHANGE_CONTRACT)
        self.assertEqual(
            value["cross_version_population_policy"],
            CROSS_VERSION_POPULATION_POLICY,
        )
        self.assertTrue(value["authorization"]["preactivation_audit_design"])
        self.assertFalse(value["authorization"]["single_fresh_exact220_forward"])

    def test_selected_tasks_are_exact_visible_220(self) -> None:
        value = prereg.build_forward_contract(ROOT, now=1, require_pristine=False)
        tasks = selected_tasks(ROOT, value)
        self.assertEqual(len(tasks), SELECTED_COUNT)
        self.assertEqual(len({task["opaque_id"] for task in tasks}), SELECTED_COUNT)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))

    def test_scheduler_uses_full_20_task_concurrency_and_fixed_order(self) -> None:
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
            visible(1), failure="hard_deadline_timeout", elapsed=255,
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
        self.assertEqual(LIMITS["wall_seconds"], 240)
        self.assertEqual(EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(MODEL_SLOT_CAP, 8)

    def test_only_scheduling_constants_change_from_v24630_contract(self) -> None:
        from deepwide_agent import v24634_exact220_contract as current

        self.assertEqual(parent_contract.EXECUTOR_CONCURRENCY, 32)
        self.assertEqual(current.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(parent_contract.LIMITS["wall_seconds"], 150)
        self.assertEqual(current.LIMITS["wall_seconds"], 240)
        self.assertEqual(
            {key: value for key, value in parent_contract.LIMITS.items() if key != "wall_seconds"},
            {key: value for key, value in current.LIMITS.items() if key != "wall_seconds"},
        )
        for name in (
            "ARM",
            "SELECTED_COUNT",
            "MODEL_SLOT_CAP",
            "MODEL_SLOT_POOL_ID",
            "CLEANUP_RESERVE_SECONDS",
            "MINIMUM_MODEL_ATTEMPT_SECONDS",
            "PARENT_DEADLINE_GRACE_SECONDS",
            "SOURCE_MANIFEST",
            "ID_SOURCES",
            "TWO_WAVE_POLICY",
            "MODEL",
            "SEARCH",
        ):
            self.assertEqual(getattr(current, name), getattr(parent_contract, name))
        self.assertEqual(current.source_selected_ids(ROOT), parent_contract.source_selected_ids(ROOT))
        self.assertIn(
            "src/deepwide_agent/v24630_exact220_task_integration.py",
            prereg.DEPENDENCIES,
        )
        self.assertNotIn("scripts/run_official_eval_local.py", prereg.DEPENDENCIES)

    def test_forward_algorithm_functions_equal_v24630_after_identity_normalization(self) -> None:
        names = {
            "task_command",
            "_safe_progress",
            "_fallback",
            "_validate_bundle",
            "run_one_task",
            "_progress",
            "execute_forward",
            "_runtime_row",
            "_summary",
            "_prepare_slots",
        }

        def functions(path: str, *, normalize: bool) -> dict[str, str]:
            source = (ROOT / path).read_text(encoding="utf-8")
            if normalize:
                source = source.replace("v24634", "v24630").replace(
                    "V2.46.34", "V2.46.30"
                )
            tree = ast.parse(source)
            return {
                node.name: ast.dump(node, include_attributes=False)
                for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name in names
            }

        old = functions("scripts/run_v24630_exact220.py", normalize=False)
        new = functions("scripts/run_v24634_exact220.py", normalize=True)
        self.assertEqual(set(old), names)
        self.assertEqual(new, old)

        old_child = (ROOT / "scripts/run_v24630_exact220_task.py").read_text(
            encoding="utf-8"
        )
        new_child = (
            (ROOT / "scripts/run_v24634_exact220_task.py")
            .read_text(encoding="utf-8")
            .replace("v24634", "v24630")
            .replace("V2.46.34", "V2.46.30")
        )
        self.assertEqual(
            ast.dump(ast.parse(new_child), include_attributes=False),
            ast.dump(ast.parse(old_child), include_attributes=False),
        )

    def test_capacity_parent_is_sealed_and_tamper_rejected(self) -> None:
        value = validate_capacity_parent(ROOT)
        self.assertEqual(value["selected_arm"], "selected_20_active_8_slots_240s_fifo")
        self.assertEqual(value["control_failed_jobs"], 20)
        self.assertEqual(value["selected_failed_jobs"], 0)
        altered = copy.deepcopy(CROSS_VERSION_POPULATION_POLICY)
        altered["new_or_disjoint_task_population_claimed"] = True
        self.assertNotEqual(altered, CROSS_VERSION_POPULATION_POLICY)


if __name__ == "__main__":
    unittest.main()
