from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import run_v24877_keyless_coverage_exact220 as runner  # noqa: E402


class V24878KeylessCoverageRunnerFixTests(unittest.TestCase):
    def test_child_environment_is_concrete_and_nonrecursive(self) -> None:
        environment = runner._child_env()
        self.assertEqual(
            set(environment),
            {
                "HOME",
                "USER",
                "LOGNAME",
                "PATH",
                "TERM",
                "PYTHONDONTWRITEBYTECODE",
                "PYTHONNOUSERSITE",
                "PYTHONSAFEPATH",
            },
        )
        self.assertNotIn("TAVILY_API_KEY", environment)

    def test_configure_algorithm_keeps_concrete_child_environment(self) -> None:
        original = runner.algorithm._child_env
        try:
            runner.configure_algorithm()
            self.assertIs(runner.algorithm._child_env, runner._child_env)
            self.assertIsInstance(runner.algorithm._child_env(), dict)
        finally:
            runner.algorithm._child_env = original

    def test_one_task_reaches_subprocess_gate(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            directory = output / "task"
            task = {
                "opaque_id": "task_0123456789abcdef01234567",
                "question": "Return a table with columns: Item, Value.",
            }
            receipt = {
                "failure_taxonomy": "parent_subprocess_exception",
                "elapsed_seconds": 0.0,
            }
            observed = mock.Mock(
                receipt=receipt,
                return_code=None,
                timed_out=False,
                subprocess_exception=True,
            )
            gate = {"disposition": "parent_subprocess_exception"}
            with mock.patch.object(
                runner,
                "run_observed_bundle_subprocess",
                return_value=(observed, gate),
            ) as called, mock.patch.object(
                runner, "validate_parent_bundle_receipt", return_value=gate
            ), mock.patch.object(
                runner.algorithm,
                "_fallback",
                return_value={"opaque_id": task["opaque_id"]},
            ):
                value = runner._run_one_task(ROOT, {}, 1, task, directory)
            self.assertTrue(called.called)
            self.assertEqual(value.position, 1)


if __name__ == "__main__":
    unittest.main()
