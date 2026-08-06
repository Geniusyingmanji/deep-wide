from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24319_runner_integration import (  # noqa: E402
    validate_projected_parent_result,
)
from deepwide_agent.v24679_schema_dev64_contract import (  # noqa: E402
    EXECUTOR_CONCURRENCY,
    EXPECTED_TREATED_COUNT,
    SELECTED_COUNT,
    TOTAL_CHILD_RUNS,
    is_treated_task,
)
from scripts import run_v24679_schema_dev64 as runner  # noqa: E402


def visible(position: int, *, treated: bool = False) -> dict[str, str]:
    declaration = (
        "Please output one Markdown table with the columns, in this exact order:\n"
        "Name | Date\nDo not omit cells."
        if treated
        else "Return one table. The column names are: Name, Date."
    )
    return {"opaque_id": f"task_{position:024x}", "question": declaration}


def tasks() -> list[dict[str, str]]:
    return [
        visible(position, treated=position <= EXPECTED_TREATED_COUNT)
        for position in range(1, SELECTED_COUNT + 1)
    ]


def fallback(task: dict[str, str], *, arm: str, position: int) -> runner.TaskOutcome:
    result = runner._fallback(
        task,
        failure="SyntheticFailure",
        elapsed=0.01,
        progress={},
        model_receipt=None,
        timed_out=False,
    )
    validate_projected_parent_result(result)
    return runner.TaskOutcome(
        arm,
        position,
        dict(task),
        result,
        None,
        False,
        False,
        0,
        0,
        False,
        runner._empty_transport(),
        False,
        False,
    )


class V24679SchemaDev64Tests(unittest.TestCase):
    def test_contract_shape_is_fixed_64_plus_8(self) -> None:
        population = tasks()
        self.assertEqual(len(population), SELECTED_COUNT)
        self.assertEqual(sum(is_treated_task(task) for task in population), 8)
        self.assertEqual(TOTAL_CHILD_RUNS, 72)
        self.assertEqual(EXECUTOR_CONCURRENCY, 20)

    def test_execute_forward_runs_64_control_and_only_8_candidate_children(self) -> None:
        population = tasks()
        calls: list[tuple[int, str]] = []
        lock = threading.Lock()

        def fake(_root, position, task, arm, _directory):
            with lock:
                calls.append((position, arm))
            return fallback(task, arm=arm, position=position)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / runner.OUTPUT_ROOT).mkdir(parents=True)
            baseline, candidate = runner.execute_forward(
                root, population, task_runner=fake
            )
        self.assertEqual(len(calls), TOTAL_CHILD_RUNS)
        self.assertEqual(sum(arm == "baseline" for _, arm in calls), 64)
        self.assertEqual(sum(arm == "candidate" for _, arm in calls), 8)
        self.assertEqual(len(baseline), 64)
        self.assertEqual(len(candidate), 64)
        self.assertEqual([item.position for item in baseline], list(range(1, 65)))
        self.assertEqual([item.position for item in candidate], list(range(1, 65)))
        self.assertEqual(
            sum(
                item.arm == "candidate" and is_treated_task(item.task)
                for item in candidate
            ),
            EXPECTED_TREATED_COUNT,
        )

    def test_untreated_candidate_reuses_same_control_result_object(self) -> None:
        population = tasks()

        def fake(_root, position, task, arm, _directory):
            return fallback(task, arm=arm, position=position)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / runner.OUTPUT_ROOT).mkdir(parents=True)
            baseline, candidate = runner.execute_forward(
                root, population, task_runner=fake
            )
        for task, control, treatment in zip(
            population, baseline, candidate, strict=True
        ):
            if is_treated_task(task):
                self.assertIsNot(treatment.result, control.result)
                self.assertEqual(treatment.arm, "candidate")
            else:
                self.assertIs(treatment.result, control.result)
                self.assertIs(treatment.parent_exit, control.parent_exit)
                self.assertEqual(treatment.arm, "candidate")

    def test_failure_projects_nonempty_terminal_row_for_fixed_denominator(self) -> None:
        outcome = fallback(visible(1), arm="baseline", position=1)
        row = runner._runtime_row(outcome, reused=False)
        self.assertEqual(row["status"], "completed")
        self.assertFalse(row["forward_success"])
        self.assertTrue(row["prediction"])
        self.assertEqual(
            row["prediction_sha256"],
            hashlib.sha256(row["prediction"].encode()).hexdigest(),
        )
        rows = []
        for position in range(1, SELECTED_COUNT + 1):
            item = fallback(visible(position), arm="baseline", position=position)
            rows.append(runner._runtime_row(item, reused=False))
        summary = runner._summary("baseline", rows, 1.0)
        self.assertEqual(summary["selected"], 64)
        self.assertEqual(summary["completed"], 64)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["runtime_failures"], 64)
        self.assertEqual(summary["fallback_tables"], 64)

    def test_scheduler_exception_is_terminal_fallback_without_retry(self) -> None:
        population = tasks()
        attempted: list[int] = []

        def fake(_root, position, task, arm, _directory):
            attempted.append(position)
            if position == 1:
                raise RuntimeError("synthetic")
            return fallback(task, arm=arm, position=position)

        jobs = [
            (position, task, "baseline")
            for position, task in enumerate(population, start=1)
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / runner.OUTPUT_ROOT).mkdir(parents=True)
            outcomes = runner.execute_batch(root, population, jobs, task_runner=fake)
        self.assertEqual(len(attempted), SELECTED_COUNT)
        self.assertEqual(attempted.count(1), 1)
        validate_projected_parent_result(outcomes[1].result)
        self.assertFalse(outcomes[1].accepted_parent_success)

    def test_runtime_row_rejects_reuse_on_treated_task(self) -> None:
        outcome = fallback(visible(1, treated=True), arm="candidate", position=1)
        with self.assertRaisesRegex(ValueError, "runtime row drifted"):
            runner._runtime_row(outcome, reused=True)

    def test_child_command_contains_no_evaluator_or_privileged_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            command = runner.task_command(ROOT, directory, "baseline")
        serialized = json.dumps(command).casefold()
        for forbidden in (
            "question_type",
            "category",
            "ground_truth",
            "answer_key",
            "evaluator_mapping",
            "official_eval",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_execute_forward_does_not_mutate_task_inputs(self) -> None:
        population = tasks()
        before = copy.deepcopy(population)

        def fake(_root, position, task, arm, _directory):
            return fallback(task, arm=arm, position=position)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / runner.OUTPUT_ROOT).mkdir(parents=True)
            runner.execute_forward(root, population, task_runner=fake)
        self.assertEqual(population, before)

    def test_execute_forward_uses_full_frozen_concurrency(self) -> None:
        population = tasks()
        recorded: list[int] = []

        class RecordingExecutor:
            def __init__(self, *, max_workers, thread_name_prefix):
                del thread_name_prefix
                recorded.append(max_workers)

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def submit(self, function, *args):
                future = runner.concurrent.futures.Future()
                try:
                    future.set_result(function(*args))
                except BaseException as error:
                    future.set_exception(error)
                return future

        def fake(_root, position, task, arm, _directory):
            return fallback(task, arm=arm, position=position)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / runner.OUTPUT_ROOT).mkdir(parents=True)
            with patch.object(
                runner.concurrent.futures,
                "ThreadPoolExecutor",
                RecordingExecutor,
            ):
                runner.execute_forward(root, population, task_runner=fake)
        self.assertEqual(recorded, [EXECUTOR_CONCURRENCY, EXECUTOR_CONCURRENCY])


if __name__ == "__main__":
    unittest.main()
