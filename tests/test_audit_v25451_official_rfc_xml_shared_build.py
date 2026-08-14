from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25451_official_rfc_xml_shared_build as target  # noqa: E402


class V25451OfficialRfcXmlSharedBuildAuditTests(unittest.TestCase):
    def test_hashes_closure_semantics_and_diagnosis_are_exact(self) -> None:
        diagnosis = target._diagnosis_barrier()
        self.assertFalse(diagnosis["formal_result"]["quality_gate_passed"])
        self.assertTrue(
            all(
                target.base.sha256(path) == expected
                for path, expected in target.FIXED_HASHES.items()
            )
        )
        closure, vector = target._closure()
        self.assertEqual(len(closure), target.EXPECTED_CLOSURE_COUNT)
        self.assertEqual(
            target.base.payload_sha256(vector),
            target.EXPECTED_CLOSURE_VECTOR_SHA256,
        )
        semantic = target.base._semantic_findings(closure)
        self.assertEqual(semantic["privileged_runtime_field_accesses"], [])
        self.assertEqual(semantic["evaluator_capabilities"], [])
        self.assertEqual(semantic["credential_literal_hits"], [])

    def test_build_authorizes_only_fresh_population_design(self) -> None:
        tests = {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
        }
        with mock.patch.object(target, "_tests", return_value=tests):
            value = target.build_audit(now=1, tracked=False)
        self.assertEqual(target.validate_audit(value), value)
        authorization = value["authorization"]
        self.assertTrue(authorization["fresh_structurally_disjoint_population_design"])
        self.assertFalse(authorization["external_protocol_design"])
        self.assertFalse(authorization["external_forward"])
        self.assertFalse(authorization["deepwidebench_forward_or_evaluator"])

    def test_resealed_semantic_effect_check_or_authorization_tamper_fails(self) -> None:
        tests = {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
        }
        with mock.patch.object(target, "_tests", return_value=tests):
            value = target.build_audit(now=1, tracked=False)
        for kind in ("semantic", "effect", "check", "authorization"):
            changed = copy.deepcopy(value)
            if kind == "semantic":
                changed["semantic_audit"]["evaluator_capabilities"] = ["x"]
            elif kind == "effect":
                changed["effect_envelope"]["final_maximum_fetches"] = 15
            elif kind == "check":
                changed["checks"]["query4_fetch14_model3_final_caps"] = False
            else:
                changed["authorization"]["external_forward"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_denominators_and_no_launch_scope_are_frozen(self) -> None:
        self.assertEqual(target.EXPECTED_TESTS, 90)
        self.assertEqual(target.EXPECTED_CLOSURE_COUNT, 99)
        self.assertIn("build_audit", str(target.OUTPUT))
        self.assertNotIn("external", str(target.OUTPUT))
        self.assertNotIn("exact220", str(target.OUTPUT))

if __name__ == "__main__":
    unittest.main()
