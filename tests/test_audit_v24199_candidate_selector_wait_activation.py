from __future__ import annotations

import unittest
import subprocess
import sys
from pathlib import Path


class AuditV24199CandidateSelectorWaitActivationTests(unittest.TestCase):
    def test_source_is_wait_only_label_blind_and_isolated_bootstrap_safe(self) -> None:
        source = (
            Path(__file__).parents[1]
            / "scripts/audit_v24199_candidate_selector_wait_activation.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "subprocess",
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
        self.assertIn("quality_status_envelopes_opened", source)
        self.assertIn("candidate_built_merged_or_frozen_by_selector", source)
        self.assertIn("benchmark_forward_or_full220_launch_allowed", source)

    def test_real_isolated_cli_bootstrap_reaches_help(self) -> None:
        root = Path(__file__).parents[1]
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                "scripts/audit_v24199_candidate_selector_wait_activation.py",
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
