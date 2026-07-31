from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


class AuditV24200SuccessorWaitActivationTests(unittest.TestCase):
    def test_source_is_wait_only_and_label_blind(self) -> None:
        source = (
            Path(__file__).parents[1]
            / "scripts/audit_v24200_successor_wait_activation.py"
        ).read_text()
        for forbidden in (
            "os.kill",
            "signal.",
            "requests.",
            "urllib",
            "socket.",
            "runtime_predictions.jsonl",
            "evaluator_mapping.jsonl",
            "--resume",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn('str(ROOT / "src")', source)
        self.assertIn("numeric_metrics_reports_predictions_or_aggregates_read", source)
        self.assertIn("package_gate_evaluated_or_launched", source)

    def test_real_isolated_cli_bootstrap_reaches_help(self) -> None:
        root = Path(__file__).parents[1]
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                "scripts/audit_v24200_successor_wait_activation.py",
                "--help",
            ],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("usage:", completed.stdout)


if __name__ == "__main__":
    unittest.main()
