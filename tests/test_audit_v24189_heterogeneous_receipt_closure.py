from __future__ import annotations

import unittest
from pathlib import Path

from scripts.audit_v24189_heterogeneous_receipt_closure import payload_seal
from scripts.preregister_v24189_heterogeneous_receipt_closure import payload_sha


class AuditV24189HeterogeneousReceiptClosureTests(unittest.TestCase):
    def test_payload_seal_tamper_detection(self) -> None:
        value = {"role": "x"}
        value["audit_payload_sha256"] = payload_sha(value)
        self.assertTrue(payload_seal(value, "audit_payload_sha256"))
        value["role"] = "y"
        self.assertFalse(payload_seal(value, "audit_payload_sha256"))

    def test_source_distinguishes_receipt_contracts(self) -> None:
        source = (
            Path(__file__).parents[1]
            / "scripts/audit_v24189_heterogeneous_receipt_closure.py"
        ).read_text(encoding="utf-8")
        self.assertIn('receipt_contract == "standalone_payload_seal"', source)
        self.assertIn('receipt_contract == "activation_content_addressed"', source)
        self.assertIn('"receipt_payload_sha256" in receipt_value', source)

    def test_source_has_no_runtime_content_network_or_mutation_surface(self) -> None:
        source = (
            Path(__file__).parents[1]
            / "scripts/audit_v24189_heterogeneous_receipt_closure.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "runtime_predictions.jsonl",
            "evaluator_mapping.jsonl",
            "ANTHROPIC_API_KEY",
            "TAVILY_API_KEY",
            "subprocess",
            "os.kill",
            "requests.",
            "urllib",
            "socket.",
            "--resume",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
