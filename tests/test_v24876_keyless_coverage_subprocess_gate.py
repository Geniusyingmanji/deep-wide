from __future__ import annotations

import os
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24876_keyless_coverage_subprocess_gate import (  # noqa: E402
    run_observed_bundle_subprocess,
    validate_parent_bundle_receipt,
)


FIXTURE = ROOT / "tests/fixtures/v24876_keyless_coverage_child.py"


def environment() -> dict[str, str]:
    return {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "TERM": "xterm-256color",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }


class V24876KeylessCoverageSubprocessGateTests(unittest.TestCase):
    def run_mode(self, mode: str, *, timeout: float = 10.0):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        output = Path(temporary.name)
        directory = output / "task"
        directory.mkdir()
        command = [
            str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(FIXTURE),
            "--mode", mode, "--output-root", str(output), "--directory", str(directory),
        ]
        observed, receipt = run_observed_bundle_subprocess(
            cwd=ROOT, output_root=output, directory=directory, command=command,
            environment=environment(), timeout_seconds=timeout,
            expected_model_slot_cap=2,
        )
        validate_parent_bundle_receipt(receipt)
        return temporary, observed, receipt

    def test_low_source_pre_provider_and_retry_are_success(self) -> None:
        for mode in ("low", "pre_provider", "retry"):
            with self.subTest(mode=mode):
                temporary, observed, receipt = self.run_mode(mode)
                self.addCleanup(temporary.cleanup)
                self.assertEqual(observed.return_code, 0)
                self.assertEqual(observed.receipt["failure_taxonomy"], "success")
                self.assertEqual(receipt["disposition"], "success")
                self.assertTrue(receipt["bundle_valid"])

    def test_nonzero_timeout_and_deleted_marker_are_not_success(self) -> None:
        temporary, observed, receipt = self.run_mode("nonzero")
        self.addCleanup(temporary.cleanup)
        self.assertNotEqual(observed.return_code, 0)
        self.assertEqual(receipt["disposition"], "child_nonzero")
        temporary, observed, receipt = self.run_mode("timeout", timeout=0.2)
        self.addCleanup(temporary.cleanup)
        self.assertTrue(observed.timed_out)
        self.assertEqual(receipt["disposition"], "hard_deadline_timeout")
        temporary, observed, receipt = self.run_mode("delete_bundle")
        self.addCleanup(temporary.cleanup)
        self.assertEqual(observed.return_code, 0)
        self.assertEqual(receipt["disposition"], "bundle_missing_or_invalid")

    def test_sixteen_concurrent_mixed_successes_all_commit(self) -> None:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)

        def run_one(index: int):
            directory = output / f"task_{index:02d}"
            directory.mkdir()
            mode = ("low", "pre_provider", "retry")[index % 3]
            command = [
                str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(FIXTURE),
                "--mode", mode, "--output-root", str(output), "--directory", str(directory),
            ]
            return run_observed_bundle_subprocess(
                cwd=ROOT, output_root=output, directory=directory, command=command,
                environment=environment(), timeout_seconds=10.0,
                expected_model_slot_cap=2,
            )

        with ThreadPoolExecutor(max_workers=8) as pool:
            values = list(pool.map(run_one, range(16)))
        for observed, receipt in values:
            self.assertEqual(observed.return_code, 0)
            self.assertEqual(observed.receipt["failure_taxonomy"], "success")
            self.assertEqual(receipt["disposition"], "success")


if __name__ == "__main__":
    unittest.main()
