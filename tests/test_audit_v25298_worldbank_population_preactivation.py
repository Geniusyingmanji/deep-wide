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

from scripts import audit_v25298_worldbank_population_preactivation as target  # noqa: E402


REAL_GIT = target.base._git


class V25298WorldBankPopulationPreactivationAuditTests(unittest.TestCase):
    @staticmethod
    def _fake_tests() -> dict:
        return {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [
                {"pattern": pattern, "expected": count, "observed": count, "returncode": 0, "passed": True, "output_sha256": "a" * 64}
                for pattern, count in target.TEST_SUITES
            ],
        }

    @staticmethod
    def _clean_git(*args: str) -> str:
        if args in {("rev-parse", "HEAD"), ("rev-parse", "target/main")}:
            return target.SUPERVISOR_REPAIR_COMMIT
        if args == ("status", "--porcelain"):
            return ""
        return REAL_GIT(*args)

    def _audit(self) -> dict:
        with mock.patch.object(target.base, "_git", side_effect=self._clean_git), mock.patch.object(
            target, "_tests", return_value=self._fake_tests()
        ), mock.patch.object(target, "_ancestor", return_value=True):
            return target.build_audit(now=1, tracked=False)

    def test_fixed_inputs_commit_and_dependency_closure_are_exact(self) -> None:
        self.assertEqual(target._fixed_inputs(), {str(path): digest for path, digest in target.EXPECTED_FIXED.items()})
        self.assertEqual(
            target._changed_paths(target.INITIAL_IMPLEMENTATION_COMMIT),
            target.INITIAL_IMPLEMENTATION_PATHS,
        )
        self.assertEqual(target._changed_paths(target.REPAIR_COMMIT), target.REPAIR_PATHS)
        self.assertEqual(
            target._changed_paths(target.SUPERVISOR_REPAIR_COMMIT),
            target.SUPERVISOR_REPAIR_PATHS,
        )
        closure, vector = target._closure()
        self.assertEqual(len(closure), target.EXPECTED_CLOSURE_COUNT)
        self.assertEqual(target.runner.payload_sha256(vector), target.EXPECTED_CLOSURE_VECTOR_SHA256)

    def test_source_invariants_bind_one_catalog_48_targets_and_claim_before_effect(self) -> None:
        self.assertTrue(all(target._source_invariants().values()))
        historical, rows = target.runner.historical_indicator_manifest()
        self.assertEqual(len(historical), 35)
        self.assertEqual(len(rows), 11)
        self.assertTrue(target.runner._revocation_barrier())
        self.assertTrue(target.runner._prior_nogo_barrier())

    def test_closure_is_label_blind_without_evaluator_or_credentials(self) -> None:
        closure, _vector = target._closure()
        semantic = target.base._semantic_findings(closure)
        self.assertEqual(semantic["privileged_runtime_field_accesses"], [])
        self.assertEqual(semantic["evaluator_capabilities"], [])
        self.assertEqual(semantic["credential_literal_hits"], [])
        self.assertEqual(semantic["allowed_provider_rank_access"], ["src/deepwide_agent/clients.py:565:score"])

    def test_audit_only_authorizes_execution_start_generation(self) -> None:
        value = self._audit()
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["authorization"]["execution_start_generation"])
        self.assertFalse(value["authorization"]["single_worldbank_population_freeze"])
        self.assertFalse(value["authorization"]["external_monotone_fill_forward_or_postfreeze_evaluator"])

    def test_resealed_closure_credit_authority_future_or_hidden_tamper_fails(self) -> None:
        value = self._audit()
        for kind in ("closure", "credit", "authority", "future", "hidden"):
            changed = copy.deepcopy(value)
            if kind == "closure":
                changed["runtime_dependency_vector"][0]["sha256"] = "0" * 64
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            elif kind == "authority":
                changed["authorization"]["single_worldbank_population_freeze"] = True
            elif kind == "future":
                changed["future_surfaces_pristine"] = False
            else:
                changed["checks"]["hidden"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.runner.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_auditor_has_no_external_effect_capability(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        for forbidden in ("requests.", "urlopen(", "runner.invoke_helper(", "runner.execute_freeze(", "run_official_eval_local", ".complete(system"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
