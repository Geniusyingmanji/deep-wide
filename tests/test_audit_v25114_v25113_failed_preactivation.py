from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25114_v25113_failed_preactivation as target  # noqa: E402


class V25114FailedPreactivationAuditTests(unittest.TestCase):
    def test_live_failure_is_exactly_two_phase_stability_errors(self) -> None:
        value = target.build_audit(now=1)
        reproduction = value["failure"]["test_reproduction"]
        self.assertEqual(reproduction["observed_tests"], 12)
        self.assertEqual(reproduction["observed_errors"], 2)
        self.assertNotEqual(reproduction["returncode"], 0)

    def test_failure_is_zero_runtime_effect_and_recovery_only(self) -> None:
        value = target.build_audit(now=1)
        self.assertTrue(all(value["absent_surfaces"].values()))
        self.assertFalse(value["effects"]["model_search_fetch_evaluator_or_benchmark_api_called"])
        self.assertTrue(value["authorization"]["append_only_phase_stable_test_fix"])
        self.assertFalse(value["authorization"]["v25113_protocol_overwrite_activation_or_forward"])

    def test_resealed_effect_launch_or_count_tamper_fails(self) -> None:
        value = target.build_audit(now=1)
        for kind in ("effect", "launch", "count"):
            changed = copy.deepcopy(value)
            if kind == "effect":
                changed["effects"]["model_search_fetch_evaluator_or_benchmark_api_called"] = True
            elif kind == "launch":
                changed["authorization"]["v25113_protocol_overwrite_activation_or_forward"] = True
            else:
                changed["failure"]["test_reproduction"]["observed_errors"] = 1
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
