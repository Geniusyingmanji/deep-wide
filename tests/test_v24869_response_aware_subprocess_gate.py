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

from deepwide_agent import v24865_coverage_revision_subprocess_gate as frozen  # noqa: E402
from deepwide_agent import v24869_response_aware_subprocess_gate as repaired  # noqa: E402


FIXTURE = ROOT / "tests/fixtures/v24869_response_aware_coverage_child.py"


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


class V24869ResponseAwareSubprocessGateTests(unittest.TestCase):
    def run_scenario(self, scenario: str):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        output = Path(temporary.name)
        directory = output / "task"
        directory.mkdir()
        command = [
            str(ROOT / ".venv-eval/bin/python"),
            "-I",
            "-B",
            str(FIXTURE),
            "--scenario",
            scenario,
            "--output-root",
            str(output),
            "--directory",
            str(directory),
        ]
        observed, receipt = repaired.run_observed_bundle_subprocess(
            cwd=ROOT,
            output_root=output,
            directory=directory,
            command=command,
            environment=environment(),
            timeout_seconds=10.0,
            expected_model_slot_cap=2,
            expected_tavily_key_slot_cap=2,
        )
        repaired.validate_parent_bundle_receipt(receipt)
        return temporary, observed, receipt

    def test_pre_provider_failure_is_parent_gate_success(self) -> None:
        temporary, observed, receipt = self.run_scenario("pre_provider_failure")
        self.addCleanup(temporary.cleanup)
        self.assertEqual(observed.return_code, 0)
        self.assertEqual(observed.receipt["failure_taxonomy"], "success")
        self.assertEqual(receipt["disposition"], "success")
        self.assertTrue(receipt["bundle_valid"])

    def test_retry_is_parent_gate_success(self) -> None:
        temporary, observed, receipt = self.run_scenario("retry")
        self.addCleanup(temporary.cleanup)
        self.assertEqual(observed.return_code, 0)
        self.assertEqual(observed.receipt["failure_taxonomy"], "success")
        self.assertEqual(receipt["disposition"], "success")
        self.assertTrue(receipt["bundle_valid"])

    def test_concurrent_isolated_subprocesses_all_commit(self) -> None:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)

        def run_one(index: int):
            directory = output / f"task_{index:02d}"
            directory.mkdir()
            scenario = "pre_provider_failure" if index % 2 else "retry"
            command = [
                str(ROOT / ".venv-eval/bin/python"),
                "-I",
                "-B",
                str(FIXTURE),
                "--scenario",
                scenario,
                "--output-root",
                str(output),
                "--directory",
                str(directory),
            ]
            return repaired.run_observed_bundle_subprocess(
                cwd=ROOT,
                output_root=output,
                directory=directory,
                command=command,
                environment=environment(),
                timeout_seconds=10.0,
                expected_model_slot_cap=2,
                expected_tavily_key_slot_cap=2,
            )

        with ThreadPoolExecutor(max_workers=8) as pool:
            values = list(pool.map(run_one, range(1, 17)))
        self.assertEqual(len(values), 16)
        for observed, receipt in values:
            self.assertEqual(observed.return_code, 0)
            self.assertEqual(observed.receipt["failure_taxonomy"], "success")
            self.assertEqual(receipt["disposition"], "success")
            self.assertTrue(receipt["bundle_valid"])

    def test_isolated_successor_does_not_patch_frozen_parent_gate(self) -> None:
        repaired.validate_isolation()
        self.assertIs(
            frozen.run_observed_bundle_subprocess.__globals__["validate_bundle"],
            frozen.validate_bundle,
        )


if __name__ == "__main__":
    unittest.main()
