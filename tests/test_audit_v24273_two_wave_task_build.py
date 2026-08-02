from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts import audit_v24273_two_wave_task_build as target  # noqa: E402
from scripts.run_v24257_score_first_smoke import payload_sha256  # noqa: E402


class AuditV24273TwoWaveTaskBuildTests(unittest.TestCase):
    def test_real_build_audit_binds_no_go_and_parent_audit(self):
        value = target.build_report(ROOT, now=1)
        target.validate_report(value)
        self.assertTrue(value["audit_valid"])
        self.assertFalse(value["parent_no_go_result"]["decision_passed"])
        self.assertTrue(value["parent_build_audit"]["audit_valid"])
        self.assertFalse(any(value["authorization"].values()))

    def test_surfaces_have_no_effect_capability_or_privileged_exact_keys(self):
        value = target.build_report(ROOT, now=1)
        for result in value["static_audit"]["surfaces"].values():
            self.assertTrue(result["passed"])
            self.assertEqual(result["forbidden_imports"], [])
            self.assertEqual(result["forbidden_direct_calls"], [])
            self.assertEqual(result["privileged_exact_key_accesses"], [])
            self.assertFalse(result["credential_literal_present"])
            self.assertFalse(result["concrete_opaque_id_present"])

    def test_resealed_authority_or_runtime_boundary_tamper_fails(self):
        value = target.build_report(ROOT, now=1)
        for mutation in ("authority", "boundary"):
            altered = copy.deepcopy(value)
            if mutation == "authority":
                altered["authorization"]["dev_benchmark_launch"] = True
            else:
                altered["integration_contract"]["runtime_boundary"].append("category")
            unsigned = dict(altered)
            unsigned.pop("audit_payload_sha256")
            altered["audit_payload_sha256"] = payload_sha256(unsigned)
            with self.assertRaisesRegex(RuntimeError, "audit drifted"):
                target.validate_report(altered)


if __name__ == "__main__":
    unittest.main()
