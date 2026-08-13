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

from scripts import audit_v25331_rate_paced_worldbank_population_build as target  # noqa: E402


REAL_GIT = target.base._git


class V25331RatePacedWorldBankPopulationBuildTests(unittest.TestCase):
    @staticmethod
    def _fake_tests() -> dict:
        return {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [
                {
                    "pattern": pattern,
                    "expected": expected,
                    "observed": expected,
                    "returncode": 0,
                    "passed": True,
                    "output_sha256": "a" * 64,
                }
                for pattern, expected in target.TEST_SUITES
            ],
        }

    @staticmethod
    def _clean_git(*args: str) -> str:
        if args in {("rev-parse", "HEAD"), ("rev-parse", "target/main")}:
            return target.IMPLEMENTATION_COMMIT
        if args == ("status", "--porcelain"):
            return ""
        return REAL_GIT(*args)

    def _audit(self) -> dict:
        with mock.patch.object(target.base, "_git", side_effect=self._clean_git), mock.patch.object(
            target, "_tests", return_value=self._fake_tests()
        ), mock.patch.object(target, "_future_pristine", return_value=True):
            return target.build_audit(now=1, tracked=False)

    def test_fixed_sources_commit_and_diagnosis_are_exact(self) -> None:
        self.assertEqual(
            {str(path): target.base.sha256(path) for path in target.FIXED},
            {str(path): digest for path, digest in target.FIXED.items()},
        )
        self.assertEqual(target._changed_paths(target.IMPLEMENTATION_COMMIT), target.IMPLEMENTATION_PATHS)
        self.assertTrue(target._diagnosis_barrier())

    def test_manifest_binds_exact_72_144_127(self) -> None:
        value = target._manifest()
        self.assertTrue(all(value["checks"].values()))
        self.assertEqual(value["target_count"], 72)
        self.assertEqual(value["entity_count"], 144)
        self.assertEqual(value["response_count"], 127)

    def test_transport_policy_paces_actual_starts_and_blocks_synthetic_effect(self) -> None:
        value = target._transport_policy_contract()
        self.assertTrue(target._transport_policy_exact(value))
        self.assertEqual(value["target_concurrency"], 6)
        self.assertEqual(value["request_start_interval_seconds"], 1.0)
        self.assertTrue(value["actual_provider_starts_are_ticket_ordered"])
        self.assertTrue(value["actual_provider_starts_are_one_second_paced"])
        self.assertTrue(value["synthetic_clock_rejected_for_persistent_execution_before_authority_or_provider"])

    def test_runtime_closure_is_label_blind_without_evaluator_or_credentials(self) -> None:
        closure, vector = target._closure()
        self.assertTrue(closure)
        self.assertEqual(
            target.runner.payload_sha256(vector),
            target.runner.payload_sha256([{"path": row["path"], "sha256": row["sha256"]} for row in vector]),
        )
        semantic = target.base._semantic_findings(closure)
        self.assertEqual(semantic["privileged_runtime_field_accesses"], [])
        self.assertEqual(semantic["evaluator_capabilities"], [])
        self.assertEqual(semantic["credential_literal_hits"], [])

    def test_build_audit_authorizes_only_preactivation_design(self) -> None:
        value = self._audit()
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["authorization"]["rate_paced_population_preactivation_design"])
        self.assertFalse(value["authorization"]["network_population_selection_or_freeze"])
        self.assertFalse(value["authorization"]["external_forward_or_evaluator"])

    def test_resealed_manifest_policy_or_authority_tamper_fails(self) -> None:
        value = self._audit()
        for kind in ("manifest", "policy", "network", "credit", "hidden"):
            changed = copy.deepcopy(value)
            if kind == "manifest":
                changed["consumed_manifest"]["response_count"] = 126
            elif kind == "policy":
                changed["transport_policy_contract"]["request_start_interval_seconds"] = 0.0
            elif kind == "network":
                changed["authorization"]["network_population_selection_or_freeze"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["checks"]["hidden"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.runner.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_auditor_has_no_live_provider_or_evaluator_constructor(self) -> None:
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
