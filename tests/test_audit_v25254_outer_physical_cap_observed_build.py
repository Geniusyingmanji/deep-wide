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

from scripts import audit_v25254_outer_physical_cap_observed_build as target  # noqa: E402


class V25254OuterPhysicalCapObservedBuildAuditTests(unittest.TestCase):
    def test_closure_caps_and_stage_surface_are_exact(self) -> None:
        closure, vector = target._closure()
        self.assertEqual(len(closure), target.EXPECTED_CLOSURE_COUNT)
        self.assertEqual(target.external.payload_sha256(vector), target.EXPECTED_CLOSURE_VECTOR_SHA256)
        self.assertEqual(
            target.external.payload_sha256([row["path"] for row in vector]),
            target.EXPECTED_CLOSURE_PATH_SHA256,
        )
        self.assertEqual((target.runtime.QUERY_CAP, target.runtime.FETCH_CAP, target.runtime.MODEL_CAP), (4, 14, 4))
        self.assertTrue(target._stage_surface_present())

    def test_build_audit_authorizes_protocol_design_only(self) -> None:
        fake_tests = {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [
                {"pattern": pattern, "expected": expected, "observed": expected, "returncode": 0, "passed": True, "output_sha256": "a" * 64}
                for pattern, expected in target.TEST_SUITES
            ],
        }
        with mock.patch.object(target, "_tests", return_value=fake_tests):
            value = target.build_audit(now=1, tracked=False)
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["authorization"]["fresh_artifact_disjoint_observed_reliability_protocol_design"])
        self.assertFalse(value["authorization"]["fresh_external_activation_or_launch"])

    def test_resealed_launch_credit_or_cap_tamper_fails(self) -> None:
        fake_tests = {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [
                {"pattern": pattern, "expected": expected, "observed": expected, "returncode": 0, "passed": True, "output_sha256": "b" * 64}
                for pattern, expected in target.TEST_SUITES
            ],
        }
        with mock.patch.object(target, "_tests", return_value=fake_tests):
            value = target.build_audit(now=1, tracked=False)
        for kind in ("launch", "credit", "cap"):
            changed = copy.deepcopy(value)
            if kind == "launch":
                changed["authorization"]["fresh_external_activation_or_launch"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["physical_caps"]["model_forwards"] = 3
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.external.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_auditor_source_has_no_evaluator_or_effect_call(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        self.assertNotIn("official_eval", source)
        self.assertNotIn("evaluate_", source)
        self.assertNotIn("requests.", source)


if __name__ == "__main__":
    unittest.main()
