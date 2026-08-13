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

from scripts import audit_v25287_legacy_outcome_checkpoint_build as target  # noqa: E402


REAL_GIT = target.base._git


class V25287LegacyOutcomeCheckpointBuildAuditTests(unittest.TestCase):
    @staticmethod
    def _fake_direct_tests() -> dict:
        return {
            "expected": target.EXPECTED_DIRECT_TESTS,
            "observed": target.EXPECTED_DIRECT_TESTS,
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
                for pattern, expected in target.DIRECT_TEST_SUITES
            ],
        }

    @staticmethod
    def _fake_historical_test() -> dict:
        return {
            "pattern": target.HISTORICAL_TEST,
            "expected": target.HISTORICAL_TEST_COUNT,
            "observed": target.HISTORICAL_TEST_COUNT,
            "returncode": 1,
            "passed": False,
            "ok_count": target.HISTORICAL_OK_COUNT,
            "failure_count": 0,
            "error_count": 1,
            "traceback_error_count": 1,
            "only_nonpassing_test": target.HISTORICAL_ERROR_TEST,
            "only_nonpassing_error": target.HISTORICAL_ERROR,
            "exact_registered_shape": True,
            "classified_as_current_green": False,
            "output_contains_credential_literal": False,
            "output_sha256": "b" * 64,
        }

    @staticmethod
    def _clean_git(*args: str) -> str:
        if args in {("rev-parse", "HEAD"), ("rev-parse", "target/main")}:
            return target.V25286_COMMIT
        if args == ("status", "--porcelain"):
            return ""
        return REAL_GIT(*args)

    def test_fixed_parents_runtime_hashes_and_dependency_closure_are_exact(self) -> None:
        self.assertEqual(
            target._fixed_parents(),
            {str(path): digest for path, digest in target.FIXED_PARENTS.items()},
        )
        self.assertTrue(target._parent_barrier())
        self.assertEqual(target.base.sha256(target.RUNTIME), target.EXPECTED_RUNTIME_SHA256)
        self.assertEqual(
            target.base.sha256(target.RUNTIME_TEST),
            target.EXPECTED_RUNTIME_TEST_SHA256,
        )
        closure, vector = target._closure()
        self.assertEqual(len(closure), target.EXPECTED_CLOSURE_COUNT)
        self.assertEqual(
            target.seal.payload_sha256(vector),
            target.EXPECTED_CLOSURE_VECTOR_SHA256,
        )
        self.assertEqual(
            target.seal.payload_sha256([row["path"] for row in vector]),
            target.EXPECTED_CLOSURE_PATH_SHA256,
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

    def test_historical_dependency_drift_is_exact_and_predates_v25286(self) -> None:
        drift = target._historical_drift(target.V25286_COMMIT)
        self.assertTrue(target._historical_drift_exact(drift))
        self.assertFalse(drift["historical_contract_live_validation_green"])
        self.assertFalse(drift["v25286_commit_touches_dependency"])
        self.assertEqual(
            drift["classification"],
            "historical_protocol_closure_drift_not_v25286_behavior_regression",
        )

    def test_build_audit_authorizes_protocol_design_only(self) -> None:
        with mock.patch.object(
            target.base, "_git", side_effect=self._clean_git
        ), mock.patch.object(
            target, "_direct_tests", return_value=self._fake_direct_tests()
        ), mock.patch.object(
            target,
            "_historical_contract_test",
            return_value=self._fake_historical_test(),
        ):
            value = target.build_audit(now=1, tracked=False)
        self.assertEqual(target.validate_audit(value), value)
        authorization = value["authorization"]
        self.assertTrue(
            authorization[
                "fresh_disjoint_legacy_checkpoint_quality_population_and_protocol_design"
            ]
        )
        self.assertFalse(authorization["external_activation_or_launch"])
        self.assertFalse(authorization["postfreeze_evaluator"])
        self.assertFalse(
            authorization["deepwidebench_dev64_exact220_forward_or_evaluator"]
        )
        self.assertFalse(
            value["historical_contract_test"]["classified_as_current_green"]
        )

    def test_resealed_history_protocol_launch_credit_nested_or_check_tamper_fails(self) -> None:
        with mock.patch.object(
            target.base, "_git", side_effect=self._clean_git
        ), mock.patch.object(
            target, "_direct_tests", return_value=self._fake_direct_tests()
        ), mock.patch.object(
            target,
            "_historical_contract_test",
            return_value=self._fake_historical_test(),
        ):
            value = target.build_audit(now=1, tracked=False)
        for kind in (
            "history_green",
            "history_commit",
            "protocol",
            "launch",
            "credit",
            "suite_hidden",
            "watcher_hidden",
            "dependency_hidden",
            "check_hidden",
        ):
            changed = copy.deepcopy(value)
            if kind == "history_green":
                changed["historical_contract_test"][
                    "classified_as_current_green"
                ] = True
            elif kind == "history_commit":
                changed["historical_dependency_drift"][
                    "v25286_commit_touches_dependency"
                ] = True
            elif kind == "protocol":
                changed["future_protocol_requirements"][
                    "direct_public_220_after_build"
                ] = True
            elif kind == "launch":
                changed["authorization"]["external_activation_or_launch"] = True
            elif kind == "credit":
                changed[
                    "entropy_or_information_gain_assigns_signed_credit"
                ] = True
            elif kind == "suite_hidden":
                changed["direct_tests"]["suites"][0]["hidden"] = True
            elif kind == "watcher_hidden":
                changed["protected_watchers"]["795336"]["hidden"] = True
            elif kind == "dependency_hidden":
                changed["runtime_dependency_vector"][0]["hidden"] = True
            else:
                changed["checks"]["hidden"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.seal.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_auditor_does_not_call_network_model_search_or_evaluator(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        for forbidden in (
            "HardTotalWallResponsesClient(",
            "AzureNativeSearchClient(",
            "requests.",
            "urlopen(",
            "run_official_eval_local",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
