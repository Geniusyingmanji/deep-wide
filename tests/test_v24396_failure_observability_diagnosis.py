from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import diagnose_v24396_v24395_failure_observability as target  # noqa: E402


class V24396FailureObservabilityDiagnosisTests(unittest.TestCase):
    def test_controlled_reproduction_proves_taxonomy_collapse(self) -> None:
        value = target.reproduce_projection_collapse(ROOT)
        self.assertEqual(
            value["injected_parent_taxonomy"],
            "child_nonzero_with_terminal_receipt",
        )
        self.assertEqual(value["run_one_raised_exception_type"], "ValueError")
        self.assertEqual(
            value["outer_replacement_taxonomy"], "local_projection_failure"
        )
        self.assertTrue(value["outer_replacement_deadline_exhausted"])
        self.assertTrue(value["outer_replacement_effect_counts_zero"])
        self.assertFalse(value["underlying_taxonomy_preserved"])

    def test_report_separates_valid_nogo_from_unsupported_root_cause(self) -> None:
        report = target.build_report(ROOT, now=0)
        target.validate_report(ROOT, value=report)
        self.assertTrue(
            report["mechanical_conclusion"]["v24395_no_go_remains_valid"]
        )
        self.assertIn(
            "model_slot_capacity_is_the_root_cause",
            report["claim_audit"]["not_supported"],
        )
        self.assertEqual(
            report["observed"]["synthetic_local_failure_rows"], 15
        )
        self.assertFalse(report["authorization"]["new_external_probe"])

    def test_resealed_claim_tamper_fails_closed(self) -> None:
        report = target.build_report(ROOT, now=0)
        altered = copy.deepcopy(report)
        altered["authorization"]["new_external_probe"] = True
        altered.pop("diagnosis_payload_sha256")
        altered["diagnosis_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(RuntimeError):
            target.validate_report(ROOT, value=altered)


if __name__ == "__main__":
    unittest.main()
