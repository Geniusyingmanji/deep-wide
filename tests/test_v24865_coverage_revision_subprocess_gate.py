from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24865_coverage_revision_subprocess_gate import (  # noqa: E402
    BASE_PARENT_NAME,
    PARENT_NAME,
    run_observed_bundle_subprocess,
    validate_parent_bundle_receipt,
)


FIXTURE = ROOT / "tests/fixtures/v24865_coverage_revision_child.py"


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


class V24865CoverageRevisionSubprocessGateTests(unittest.TestCase):
    def run_mode(self, mode: str, timeout: float = 10.0):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        output = Path(temporary.name)
        directory = output / "task"
        directory.mkdir()
        command = [
            str(ROOT / ".venv-eval/bin/python"),
            "-I",
            "-B",
            str(FIXTURE),
            "--mode",
            mode,
            "--output-root",
            str(output),
            "--directory",
            str(directory),
        ]
        observed, receipt = run_observed_bundle_subprocess(
            cwd=ROOT,
            output_root=output,
            directory=directory,
            command=command,
            environment=environment(),
            timeout_seconds=timeout,
            expected_model_slot_cap=2,
            expected_tavily_key_slot_cap=2,
        )
        validate_parent_bundle_receipt(receipt)
        return temporary, output, directory, observed, receipt

    def test_success_requires_valid_committed_bundle(self) -> None:
        temporary, _output, directory, observed, receipt = self.run_mode("success")
        self.addCleanup(temporary.cleanup)
        self.assertEqual(observed.return_code, 0)
        self.assertFalse(observed.timed_out)
        self.assertEqual(observed.receipt["failure_taxonomy"], "success")
        self.assertEqual(receipt["disposition"], "success")
        self.assertTrue(receipt["bundle_commit_marker_present"])
        self.assertTrue(receipt["bundle_valid"])
        self.assertEqual(receipt["data_artifact_count_present"], 10)
        self.assertTrue((directory / BASE_PARENT_NAME).is_file())
        self.assertTrue((directory / PARENT_NAME).is_file())

    def test_child_nonzero_with_terminal_is_not_success(self) -> None:
        temporary, _output, _directory, observed, receipt = self.run_mode("nonzero")
        self.addCleanup(temporary.cleanup)
        self.assertNotEqual(observed.return_code, 0)
        self.assertEqual(
            observed.receipt["failure_taxonomy"],
            "child_nonzero_with_terminal_receipt",
        )
        self.assertEqual(receipt["disposition"], "child_nonzero")
        self.assertFalse(receipt["bundle_valid"])

    def test_parent_timeout_is_terminal_and_not_bundle_success(self) -> None:
        temporary, _output, _directory, observed, receipt = self.run_mode(
            "timeout", timeout=0.2
        )
        self.addCleanup(temporary.cleanup)
        self.assertTrue(observed.timed_out)
        self.assertEqual(observed.receipt["failure_taxonomy"], "hard_deadline_timeout")
        self.assertEqual(receipt["disposition"], "hard_deadline_timeout")
        self.assertFalse(receipt["bundle_valid"])

    def test_zero_exit_after_bundle_marker_deletion_is_invalid(self) -> None:
        temporary, _output, _directory, observed, receipt = self.run_mode(
            "delete_bundle"
        )
        self.addCleanup(temporary.cleanup)
        self.assertEqual(observed.return_code, 0)
        self.assertEqual(observed.receipt["failure_taxonomy"], "result_envelope_invalid")
        self.assertEqual(receipt["disposition"], "bundle_missing_or_invalid")
        self.assertFalse(receipt["bundle_commit_marker_present"])
        self.assertFalse(receipt["bundle_valid"])
        self.assertEqual(receipt["data_artifact_count_present"], 10)


if __name__ == "__main__":
    unittest.main()
