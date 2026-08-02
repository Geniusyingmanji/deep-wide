from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent.v24257_score_first_runtime import (  # noqa: E402
    ScoreFirstLimits,
    build_score_first_fallback_result,
)
from scripts import run_v24257_score_first_smoke as runner  # noqa: E402


TASK = {
    "opaque_id": "task_0123456789abcdef01234567",
    "question": "表格中的列名依次为：名称、年份。",
}


def result(kind: str, *, wall: float = 10, tokens: int = 100, fetches: int = 2) -> dict:
    value = build_score_first_fallback_result(
        TASK,
        limits=ScoreFirstLimits(
            wall_seconds=600,
            model_calls=3,
            search_queries=8,
            fetch_targets=16,
        ),
        completion_kind=(
            kind if kind not in {"primary", "repaired"} else "worker_failure_fallback"
        ),
        elapsed_seconds=wall,
        last_progress={
            "model_cost": {"total_tokens": tokens},
            "search_cost": {"fetch_calls": fetches, "total_tokens": 0},
        },
    )
    value["completion_kind"] = kind
    if kind in {"primary", "repaired"}:
        value["failures"] = []
        value["budget"]["deadline_exceeded_at_return"] = False
    return value


def protocol() -> dict:
    return {
        "protocol_id": "v24257_score_first_smoke16_v1",
        "task_contract": {"selected_count": 16},
        "limits": {
            "wall_seconds": 600,
            "model_calls": 3,
            "search_queries": 8,
            "fetch_targets": 16,
            "search_results_per_query": 3,
            "evidence_chars": 100_000,
            "page_chars": 5_000,
            "plan_output_tokens": 4_000,
            "synthesis_output_tokens": 30_000,
            "repair_output_tokens": 12_000,
        },
        "gate_contract": {
            "minimum_model_generated_tables": 15,
            "maximum_fallback_tables": 1,
            "maximum_hard_deadline_fallbacks": 1,
            "maximum_p95_wall_seconds": 600,
            "maximum_mean_system_tokens": 750_000,
            "maximum_mean_fetch_calls": 200,
        },
        "execution": {"parent_deadline_grace_seconds": 5},
    }


class FakeProcess:
    def __init__(self, *, returncode: int = 1, timeout: bool = False) -> None:
        self.returncode = None
        self.final_returncode = returncode
        self.timeout = timeout
        self.pid = 12345

    def wait(self, timeout: float | None = None) -> int:
        if self.timeout and self.returncode is None:
            raise runner.subprocess.TimeoutExpired(["child"], timeout)
        self.returncode = self.final_returncode
        return self.returncode


class ScoreFirstSmokeExecutorTests(unittest.TestCase):
    def test_gate_requires_model_generated_tables_not_merely_terminal_rows(self) -> None:
        rows = [result("primary") for _ in range(15)] + [
            result("worker_failure_fallback")
        ]
        value = runner.aggregate_results(protocol(), rows)
        self.assertEqual(value["engineering_gate"], "go")
        self.assertEqual(value["model_generated_tables"], 15)
        rows = [result("worker_failure_fallback") for _ in range(16)]
        value = runner.aggregate_results(protocol(), rows)
        self.assertEqual(value["engineering_gate"], "no_go")
        self.assertIn("model_generated_table_count_below_gate", value["findings"])

    def test_gate_checks_wall_token_fetch_and_hard_deadline(self) -> None:
        rows = [result("primary") for _ in range(15)] + [
            result(
                "hard_deadline_fallback",
                wall=700,
                tokens=900_000,
                fetches=300,
            )
        ]
        value = runner.aggregate_results(protocol(), rows)
        self.assertEqual(value["engineering_gate"], "no_go")
        self.assertIn("p95_wall_seconds_above_gate", value["findings"])

    def test_nonzero_child_exit_creates_content_free_fallback(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            base = Path(temporary)
            task_root = base / "task"
            fake = FakeProcess(returncode=1)
            with mock.patch.object(runner, "_task_command", return_value=["child"]), mock.patch.object(
                runner, "_child_env", return_value={}
            ):
                value = runner.run_one_task(
                    ROOT,
                    protocol(),
                    TASK,
                    task_root,
                    popen=lambda *args, **kwargs: fake,
                )
            self.assertEqual(value["completion_kind"], "worker_failure_fallback")
            self.assertEqual(
                value["failures"],
                [{"stage": "parent_executor", "type": "WorkerNonzeroExit"}],
            )
            self.assertNotIn(TASK["question"], json.dumps(value, ensure_ascii=False))

    def test_timeout_terminates_group_and_uses_last_safe_progress(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            task_root = Path(temporary) / "task"
            fake = FakeProcess(timeout=True)

            def popen(*args, **kwargs):
                progress = task_root / "safe_progress.json"
                progress.write_text(
                    json.dumps(
                        {
                            "artifact_version": 1,
                            "role": "v24257_score_first_safe_progress",
                            "stage": "retrieval_terminal",
                            "elapsed_seconds": 5,
                            "admitted_model_calls": 1,
                            "admitted_search_queries": 2,
                            "admitted_fetch_targets": 0,
                            "search_batch_count": 2,
                            "projected_chars": 0,
                            "events": [],
                            "model_cost": {
                                "requests": 1,
                                "attempts": 1,
                                "input_tokens": 3,
                                "output_tokens": 2,
                                "total_tokens": 5,
                            },
                            "search_cost": {
                                "calls": 2,
                                "failures": 0,
                                "tool_calls": 2,
                                "fetch_calls": 0,
                                "fetch_failures": 0,
                                "input_tokens": 4,
                                "output_tokens": 1,
                                "total_tokens": 5,
                            },
                            "contains_question_query_url_page_prediction_or_answer": False,
                            "mapping_gold_evaluator_or_score_read": False,
                        }
                    ),
                    encoding="utf-8",
                )
                return fake

            with mock.patch.object(runner, "_task_command", return_value=["child"]), mock.patch.object(
                runner, "_child_env", return_value={}
            ), mock.patch.object(runner, "_terminate_group", side_effect=lambda process: setattr(process, "returncode", -15)) as terminated:
                value = runner.run_one_task(
                    ROOT, protocol(), TASK, task_root, popen=popen
                )
            terminated.assert_called_once_with(fake)
            self.assertEqual(value["completion_kind"], "hard_deadline_fallback")
            self.assertEqual(value["cost"]["system_total_tokens"], 10)
            self.assertEqual(value["budget"]["admitted_search_queries"], 2)

    def test_payload_hash_is_order_independent(self) -> None:
        self.assertEqual(
            runner.payload_sha256({"b": 2, "a": 1}),
            runner.payload_sha256({"a": 1, "b": 2}),
        )


if __name__ == "__main__":
    unittest.main()
