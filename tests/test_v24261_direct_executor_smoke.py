from __future__ import annotations

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

from scripts import run_v24261_score_first_smoke as runner  # noqa: E402


TASK = {
    "opaque_id": "task_0123456789abcdef01234567",
    "question": "表格中的列名依次为：名称、年份。",
}


def protocol() -> dict:
    return {
        "provider_contract": {
            "model": {
                "proxy_url": "u",
                "name": "m",
                "reasoning_effort": "low",
                "service_tier": "p",
                "timeout_seconds": 1,
                "max_retries": 1,
            },
            "search": {
                "model": "s",
                "timeout_seconds": 1,
                "max_retries": 1,
                "workers": 1,
                "fetch_workers": 1,
                "fetch_timeout_seconds": 1,
            },
        },
        "limits": {
            "wall_seconds": 600,
            "model_calls": 3,
            "search_queries": 8,
            "fetch_targets": 16,
            "search_results_per_query": 3,
            "evidence_chars": 100000,
            "page_chars": 5000,
            "plan_output_tokens": 4000,
            "synthesis_output_tokens": 30000,
            "repair_output_tokens": 12000,
        },
        "execution": {"parent_deadline_grace_seconds": 5},
    }


class FakeProcess:
    pid = 123
    returncode = 1

    def wait(self, timeout=None):
        return self.returncode


class V24261DirectExecutorTests(unittest.TestCase):
    def test_task_command_changes_only_isolated_child_path(self) -> None:
        paths = [Path("a"), Path("b"), Path("c")]
        original = runner.scientific._task_command(ROOT, protocol(), *paths)
        successor = runner.task_command(ROOT, protocol(), *paths)
        self.assertEqual(original[:3], successor[:3])
        self.assertEqual(successor[3], str(ROOT / runner.CHILD))
        self.assertEqual(original[4:], successor[4:])

    def test_run_one_task_calls_popen_once_without_monkeypatch_recursion(self) -> None:
        calls = []

        def popen(command, **kwargs):
            calls.append((command, kwargs))
            return FakeProcess()

        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            task_root = Path(directory) / "task"
            with mock.patch.object(runner.scientific.parent, "_child_env", return_value={}):
                value = runner.run_one_task(
                    ROOT, protocol(), TASK, task_root, popen=popen
                )
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0][3], str(ROOT / runner.CHILD))
        self.assertEqual(value["completion_kind"], "worker_failure_fallback")
        self.assertEqual(value["failures"][0]["type"], "WorkerNonzeroExit")

    def test_executor_source_contains_no_runtime_monkeypatch(self) -> None:
        source = (ROOT / "scripts/run_v24261_score_first_smoke.py").read_text()
        self.assertNotIn("parent._task_command =", source)
        self.assertNotIn("scientific._task_command =", source)


if __name__ == "__main__":
    unittest.main()
