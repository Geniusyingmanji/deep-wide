from __future__ import annotations

import unittest
from pathlib import Path


class AuditV24198CandidateBundleWaitActivationTests(unittest.TestCase):
    def test_source_is_wait_only_and_label_blind(self) -> None:
        source = (
            Path(__file__).parents[1]
            / "scripts/audit_v24198_candidate_bundle_wait_activation.py"
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
        self.assertIn("candidate_selection_or_gate_evaluated", source)
        self.assertIn("benchmark_forward_or_full220_launch_allowed", source)
        self.assertIn("future_executor_requires_separate_preregistration", source)
        self.assertIn("protected_processes(proc_root)", source)


if __name__ == "__main__":
    unittest.main()
