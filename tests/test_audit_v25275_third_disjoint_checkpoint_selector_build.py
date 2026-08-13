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

from scripts import audit_v25275_third_disjoint_checkpoint_selector_build as target  # noqa: E402


class V25275ThirdDisjointCheckpointSelectorBuildAuditTests(unittest.TestCase):
    @staticmethod
    def _clean_git(*args: str) -> str:
        if args == ("rev-parse", "HEAD") or args == ("rev-parse", "target/main"):
            return "a" * 40
        if args == ("status", "--porcelain"):
            return ""
        raise AssertionError(args)

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

    def test_fixed_hash_parent_and_dependency_authority_are_exact(self) -> None:
        self.assertEqual(
            target._fixed_hashes(),
            {str(path): digest for path, digest in target.FIXED_HASHES.items()},
        )
        self.assertTrue(target._parent_barrier())
        dependency = target._dependency_vector()
        self.assertEqual(len(dependency), 8)
        self.assertEqual(
            target.contract.payload_sha256(dependency),
            target.EXPECTED_DEPENDENCY_VECTOR_SHA256,
        )

    def test_capability_is_fixed_local_process_only_and_label_blind(self) -> None:
        value = target._capability_audit()
        self.assertEqual(value["process_call_count"], 3)
        self.assertTrue(value["all_process_methods_are_subprocess_run"])
        self.assertEqual(value["shell_true_lines"], [])
        self.assertEqual(value["forbidden_network_model_evaluator_imports"], [])
        self.assertEqual(
            value["effect_source_semantic"]["privileged_runtime_field_accesses"], []
        )
        self.assertEqual(
            value["closure_semantic"]["privileged_runtime_field_accesses"],
            target.EXPECTED_CLOSURE_PRIVILEGED_OFFLINE_DIAGNOSTIC,
        )
        self.assertEqual(value["closure_semantic"]["evaluator_capabilities"], [])
        self.assertEqual(value["closure_semantic"]["credential_literal_hits"], [])

    def test_build_audit_authorizes_one_freeze_only(self) -> None:
        with mock.patch.object(
            target.base, "_git", side_effect=self._clean_git
        ), mock.patch.object(target, "_tests", return_value=self._fake_tests()):
            value = target.build_audit(now=1, tracked=False)
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(
            value["authorization"][
                "single_third_disjoint_population_freeze_after_separate_execution_start"
            ]
        )
        self.assertFalse(value["authorization"]["external_activation_or_launch"])
        self.assertFalse(value["authorization"]["deepwidebench_forward_or_evaluator"])

    def test_resealed_launch_overlap_credit_or_hidden_tamper_fails(self) -> None:
        with mock.patch.object(
            target.base, "_git", side_effect=self._clean_git
        ), mock.patch.object(target, "_tests", return_value=self._fake_tests()):
            value = target.build_audit(now=1, tracked=False)
        for kind in (
            "launch",
            "overlap",
            "credit",
            "capability_hidden",
            "suite_hidden",
            "watcher_hidden",
            "watcher_identity",
            "dependency_hidden",
        ):
            changed = copy.deepcopy(value)
            if kind == "launch":
                changed["authorization"]["external_activation_or_launch"] = True
            elif kind == "overlap":
                changed["population_contract"]["prior_population_exact_overlap_required"] = 1
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            elif kind == "capability_hidden":
                changed["capability_audit"]["hidden_authority"] = True
            elif kind == "suite_hidden":
                changed["tests"]["suites"][0]["hidden_authority"] = True
            elif kind == "watcher_hidden":
                changed["runtime_state"]["protected_watchers"][0]["hidden_authority"] = True
            elif kind == "watcher_identity":
                changed["runtime_state"]["protected_watchers"][0]["start_ticks"] += 1
            else:
                changed["selector_dependency_vector"][0]["hidden_authority"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_auditor_does_not_call_network_model_or_evaluator(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        for forbidden in (
            "run_official_eval_local",
            "requests.",
            "urlopen(",
            "HardTotalWallResponsesClient(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
