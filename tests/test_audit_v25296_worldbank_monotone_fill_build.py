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

from scripts import audit_v25296_worldbank_monotone_fill_build as target  # noqa: E402


REAL_GIT = target.base._git


class V25296WorldBankMonotoneFillBuildAuditTests(unittest.TestCase):
    @staticmethod
    def _fake_tests() -> dict:
        return {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [
                {
                    "pattern": pattern,
                    "expected": count,
                    "observed": count,
                    "returncode": 0,
                    "passed": True,
                    "output_sha256": "a" * 64,
                }
                for pattern, count in target.TEST_SUITES
            ],
        }

    @staticmethod
    def _clean_git(*args: str) -> str:
        if args in {("rev-parse", "HEAD"), ("rev-parse", "target/main")}:
            return target.IMPLEMENTATION_COMMITS[-1]
        if args == ("status", "--porcelain"):
            return ""
        return REAL_GIT(*args)

    def _audit(self) -> dict:
        with mock.patch.object(target.base, "_git", side_effect=self._clean_git), mock.patch.object(
            target, "_tests", return_value=self._fake_tests()
        ):
            return target.build_audit(now=1, tracked=False)

    def test_fixed_inputs_commits_and_closure_are_exact(self) -> None:
        self.assertEqual(
            target._fixed_inputs(),
            {str(path): digest for path, digest in target.EXPECTED_FIXED.items()},
        )
        for commit in target.IMPLEMENTATION_COMMITS:
            self.assertEqual(target._changed_paths(commit), target.IMPLEMENTATION_PATHS)
        closure, vector = target._closure()
        self.assertEqual(len(closure), target.EXPECTED_CLOSURE_COUNT)
        self.assertNotIn(target.V24857_PROTOCOL, closure)
        self.assertEqual(
            target.seal.payload_sha256(vector), target.EXPECTED_CLOSURE_VECTOR_SHA256
        )

    def test_closure_is_label_blind_without_evaluator_or_credentials(self) -> None:
        closure, _vector = target._closure()
        semantic = target.base._semantic_findings(closure)
        self.assertEqual(semantic["privileged_runtime_field_accesses"], [])
        self.assertEqual(semantic["evaluator_capabilities"], [])
        self.assertEqual(semantic["credential_literal_hits"], [])
        self.assertEqual(
            semantic["allowed_provider_rank_access"],
            ["src/deepwide_agent/clients.py:565:score"],
        )

    def test_native_drift_is_exact_default_off_and_snapshot_bypassed(self) -> None:
        value = target._native_drift()
        self.assertFalse(value["hash_equal_to_historical_manifest"])
        self.assertEqual(value["frozen_blob_sha256"], target.NATIVE_FROZEN_SHA256)
        self.assertEqual(value["observer_blob_sha256"], target.NATIVE_CURRENT_SHA256)
        self.assertEqual(value["exact_diff_sha256"], target.NATIVE_DIFF_SHA256)
        self.assertFalse(value["snapshot_runtime_passes_structure_observer"])
        self.assertTrue(value["snapshot_owns_all_three_methods"])
        self.assertFalse(value["historical_v24857_entire_manifest_pristine_claim_allowed"])

    def test_runtime_invariants_design_barrier_and_build_only_authority(self) -> None:
        self.assertTrue(all(target._source_invariants().values()))
        self.assertTrue(target._design_barrier())
        value = self._audit()
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertFalse(value["authorization"]["population_selection_or_freeze"])
        self.assertFalse(value["authorization"]["external_activation_or_launch"])
        self.assertFalse(value["authorization"]["postfreeze_evaluator"])

    def test_resealed_drift_closure_credit_authority_or_check_tamper_fails(self) -> None:
        value = self._audit()
        for kind in ("drift", "closure", "credit", "authority", "check"):
            changed = copy.deepcopy(value)
            if kind == "drift":
                changed["historical_parent_drift"][
                    "historical_v24857_entire_manifest_pristine_claim_allowed"
                ] = True
            elif kind == "closure":
                changed["runtime_dependency_vector"][0]["sha256"] = "0" * 64
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            elif kind == "authority":
                changed["authorization"]["external_activation_or_launch"] = True
            else:
                changed["checks"]["hidden"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.seal.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_auditor_has_no_external_effect_capability(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        for forbidden in (
            "HardTotalWallResponsesClient(",
            "AzureNativeSearchClient(",
            "requests.",
            "urlopen(",
            "run_official_eval_local",
            ".complete(system",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
