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

from scripts import audit_v25279_paired_checkpoint_reliability_build as target  # noqa: E402


class V25279PairedCheckpointReliabilityBuildAuditTests(unittest.TestCase):
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
        if args == ("rev-parse", "HEAD") or args == ("rev-parse", "target/main"):
            return "a" * 40
        if args == ("status", "--porcelain"):
            return ""
        raise AssertionError(args)

    def test_fixed_parent_authorities_and_dependency_closure_are_exact(self) -> None:
        self.assertEqual(
            target._fixed_parents(),
            {str(path): digest for path, digest in target.FIXED_PARENTS.items()},
        )
        self.assertTrue(target._parent_barrier())
        closure, vector = target._closure()
        self.assertEqual(len(closure), target.EXPECTED_CLOSURE_COUNT)
        self.assertEqual(
            target.contract.payload_sha256(vector),
            target.EXPECTED_CLOSURE_VECTOR_SHA256,
        )
        self.assertEqual(
            target.contract.payload_sha256([row["path"] for row in vector]),
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

    def test_build_audit_authorizes_protocol_build_only(self) -> None:
        with mock.patch.object(
            target.base, "_git", side_effect=self._clean_git
        ), mock.patch.object(target, "_tests", return_value=self._fake_tests()):
            value = target.build_audit(now=1, tracked=False)
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(
            value["authorization"]["paired_checkpoint_reliability_protocol_build"]
        )
        self.assertFalse(value["authorization"]["external_activation_or_launch"])
        self.assertFalse(value["authorization"]["deepwidebench_forward_or_evaluator"])

    def test_resealed_estimand_launch_credit_nested_or_check_tamper_fails(self) -> None:
        with mock.patch.object(
            target.base, "_git", side_effect=self._clean_git
        ), mock.patch.object(target, "_tests", return_value=self._fake_tests()):
            value = target.build_audit(now=1, tracked=False)
        for kind in (
            "estimand",
            "launch",
            "credit",
            "suite_hidden",
            "watcher_hidden",
            "dependency_hidden",
            "check_hidden",
        ):
            changed = copy.deepcopy(value)
            if kind == "estimand":
                changed["paired_estimand"]["candidate_additional_model_forwards"] = 1
            elif kind == "launch":
                changed["authorization"]["external_activation_or_launch"] = True
            elif kind == "credit":
                changed[
                    "entropy_or_information_gain_assigns_signed_credit"
                ] = True
            elif kind == "suite_hidden":
                changed["tests"]["suites"][0]["hidden"] = True
            elif kind == "watcher_hidden":
                changed["protected_watchers"][0]["hidden"] = True
            elif kind == "dependency_hidden":
                changed["runtime_dependency_vector"][0]["hidden"] = True
            else:
                changed["checks"]["hidden"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.contract.payload_sha256(changed)
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
