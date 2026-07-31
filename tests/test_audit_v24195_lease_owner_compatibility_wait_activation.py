from __future__ import annotations

import unittest
from pathlib import Path


class AuditV24195LeaseOwnerCompatibilityWaitActivationTests(unittest.TestCase):
    def test_source_is_wait_only_and_label_blind(self) -> None:
        source = (
            Path(__file__).parents[1]
            / "scripts/audit_v24195_lease_owner_compatibility_wait_activation.py"
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
        self.assertIn("successor_executor_absent", source)
        self.assertIn("shared_api_lease_acquired", source)


if __name__ == "__main__":
    unittest.main()
