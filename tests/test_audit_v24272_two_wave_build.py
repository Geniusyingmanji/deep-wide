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

from scripts import audit_v24272_two_wave_build as target  # noqa: E402
from scripts.run_v24257_score_first_smoke import payload_sha256  # noqa: E402


class AuditV24272TwoWaveBuildTests(unittest.TestCase):
    def test_real_build_audit_binds_no_go_and_authorizes_nothing(self):
        value = target.build_report(ROOT, now=1)
        target.validate_report(value)
        self.assertTrue(value["audit_valid"])
        self.assertFalse(value["parent_no_go_result"]["decision_passed"])
        self.assertTrue(value["static_audit"]["all_surfaces_passed"])
        self.assertFalse(any(value["authorization"].values()))

    def test_production_surfaces_have_no_privileged_or_secret_hits(self):
        value = target.build_report(ROOT, now=1)
        for result in value["static_audit"]["surfaces"].values():
            self.assertEqual(result["privileged_runtime_key_accesses"], [])
            self.assertEqual(result["forbidden_imports"], [])
            self.assertEqual(result["forbidden_direct_calls"], [])
            self.assertFalse(result["credential_literal_present"])
            self.assertFalse(result["concrete_opaque_id_present"])

    def test_resealed_authorization_or_parent_tamper_is_rejected(self):
        value = target.build_report(ROOT, now=1)
        for mutation in ("authorization", "parent"):
            altered = copy.deepcopy(value)
            if mutation == "authorization":
                altered["authorization"]["dev_benchmark_launch"] = True
            else:
                altered["parent_no_go_result"]["decision_passed"] = True
            unsigned = dict(altered)
            unsigned.pop("audit_payload_sha256")
            altered["audit_payload_sha256"] = payload_sha256(unsigned)
            with self.assertRaisesRegex(RuntimeError, "audit drifted"):
                target.validate_report(altered)


if __name__ == "__main__":
    unittest.main()
