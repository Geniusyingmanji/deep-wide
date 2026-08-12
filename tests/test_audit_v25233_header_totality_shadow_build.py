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

from scripts import audit_v25233_header_totality_shadow_build as target  # noqa: E402


class V25233HeaderTotalityShadowBuildAuditTests(unittest.TestCase):
    def test_fixed_runtime_test_and_parent_hashes_match(self) -> None:
        self.assertTrue(target._fixed_hash_barrier())
        self.assertEqual(
            target._fixed_hashes(),
            {str(path): expected for path, expected in target.FIXED_HASHES.items()},
        )

    def test_helper_design_and_diagnosis_authority_is_bound(self) -> None:
        self.assertTrue(target._authority_barrier())

    def test_full_parent_dependency_vector_is_hash_bound(self) -> None:
        closure, vector = target._closure()
        self.assertEqual(len(closure), target.EXPECTED_CLOSURE_COUNT)
        self.assertEqual(
            target.payload_sha256(vector), target.EXPECTED_CLOSURE_VECTOR_SHA256
        )
        self.assertEqual(
            target.payload_sha256([row["path"] for row in vector]),
            target.EXPECTED_CLOSURE_PATH_SHA256,
        )
        self.assertTrue(target._closure_barrier())

    def test_semantic_audit_is_label_blind_secret_and_evaluator_free(self) -> None:
        closure, _vector = target._closure()
        semantic = target.base._semantic_findings(closure)
        self.assertEqual(semantic["privileged_runtime_field_accesses"], [])
        self.assertEqual(semantic["evaluator_capabilities"], [])
        self.assertEqual(semantic["credential_literal_hits"], [])
        self.assertEqual(
            semantic["allowed_provider_rank_access"],
            ["src/deepwide_agent/clients.py:565:score"],
        )

    def test_expected_suite_total_is_fixed(self) -> None:
        self.assertEqual(target.EXPECTED_TESTS, 62)

    @staticmethod
    def _mocked_audit() -> dict:
        fake_tests = {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
        }

        def same(*args: str) -> str:
            return (
                "same"
                if args[:2] in {("rev-parse", "HEAD"), ("rev-parse", "target/main")}
                else ""
            )

        closure, vector = target._closure()
        semantic = {
            "privileged_runtime_field_accesses": [],
            "evaluator_capabilities": [],
            "credential_literal_hits": [],
            "allowed_provider_rank_access": [
                "src/deepwide_agent/clients.py:565:score"
            ],
        }
        with mock.patch.object(target.base, "_git", side_effect=same), mock.patch.object(
            target, "_tests", return_value=fake_tests
        ), mock.patch.object(target, "_closure", return_value=(closure, vector)), mock.patch.object(
            target.base, "_semantic_findings", return_value=semantic
        ), mock.patch.object(
            target.base,
            "_watchers",
            return_value={
                str(pid): {"matches_frozen_identity": True}
                for pid in target.base.PROTECTED_WATCHERS
            },
        ), mock.patch.object(target.base, "_lease_inactive", return_value=True), mock.patch.object(
            target.base, "_tracked", return_value=True
        ):
            return target.build_audit(now=1, tracked=False)

    def test_fully_mocked_clean_build_validates(self) -> None:
        value = self._mocked_audit()
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertFalse(value["authorization"]["candidate_activation_or_prediction_change"])

    def test_resealed_authorization_test_closure_or_semantic_tamper_fails(self) -> None:
        value = self._mocked_audit()
        for kind in ("authorization", "test", "closure", "semantic"):
            changed = copy.deepcopy(value)
            if kind == "authorization":
                changed["authorization"]["candidate_activation_or_prediction_change"] = True
            elif kind == "test":
                changed["tests"]["observed"] -= 1
            elif kind == "closure":
                changed["runtime_dependency_closure"]["count"] -= 1
            else:
                changed["runtime_semantic_audit"]["evaluator_capabilities"] = [
                    "unsafe"
                ]
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
