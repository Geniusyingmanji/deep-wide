from __future__ import annotations

import unittest
from pathlib import Path


class AuditV24197ParallelAll220WaitActivationTests(unittest.TestCase):
    def test_source_is_wait_only_and_label_blind(self) -> None:
        source = (
            Path(__file__).parents[1]
            / "scripts/audit_v24197_parallel_all220_wait_activation.py"
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
        self.assertIn("shared_api_lease_acquired", source)
        self.assertIn("benchmark_forward_or_full220_launch_allowed", source)
        self.assertIn("future_executor_requires_separate_preregistration", source)
        self.assertIn("protected_processes(proc_root)", source)
        self.assertIn("live_processes != frozen_processes", source)
        self.assertIn("all_protocol_protected_process_identities_preserved", source)


if __name__ == "__main__":
    unittest.main()
