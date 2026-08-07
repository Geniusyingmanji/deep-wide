from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import correct_v24768_forward_audit_roundtrip as correction  # noqa: E402


class V24768ForwardAuditRoundtripCorrectionTests(unittest.TestCase):
    def test_original_strict_validator_failure_is_order_only(self) -> None:
        value = json.loads((ROOT / correction.ORIGINAL_AUDIT).read_text())
        with self.assertRaises(RuntimeError):
            correction.original.validate_audit(value)
        self.assertEqual(correction.validate_original_audit(value), value)
        self.assertEqual(
            sorted(value["findings"]),
            sorted(name for name, passed in value["gate_checks"].items() if not passed),
        )

    def test_correction_binds_healthy_no_go_without_private_truth(self) -> None:
        value = correction.build_correction(now=0)
        correction.validate_correction(value)
        conclusion = value["forward_conclusion"]
        self.assertTrue(conclusion["forward_health_go"])
        self.assertFalse(conclusion["mechanism_go"])
        self.assertEqual(conclusion["valid_task_results"], 8)
        self.assertEqual(conclusion["changed_cell_count"], 0)
        self.assertEqual(conclusion["ordinary_record_count"], 0)
        self.assertFalse(
            value["source_policy"][
                "private_population_truth_provenance_or_quality_opened_or_hashed"
            ]
        )

    def test_resealed_rerun_or_private_surface_tamper_fails(self) -> None:
        value = correction.build_correction(now=0)
        for field in (
            "additional_forward_retry_resume_or_rerun",
            "private_truth_or_quality_surface_open",
        ):
            altered = copy.deepcopy(value)
            altered["authorization"][field] = True
            altered.pop("correction_payload_sha256")
            altered["correction_payload_sha256"] = correction.contract.payload_sha256(
                altered
            )
            with self.assertRaises(RuntimeError):
                correction.validate_correction(altered)

    def test_parent_hash_or_conclusion_tamper_breaks_seal(self) -> None:
        value = correction.build_correction(now=0)
        altered = copy.deepcopy(value)
        altered["parents"]["original_forward_audit_sha256"] = "0" * 64
        with self.assertRaises(RuntimeError):
            correction.validate_correction(altered)
        altered = copy.deepcopy(value)
        altered["forward_conclusion"]["mechanism_go"] = True
        with self.assertRaises(RuntimeError):
            correction.validate_correction(altered)


if __name__ == "__main__":
    unittest.main()
