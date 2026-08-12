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

from scripts import audit_v25257_disjoint_observed_reliability_selector_build as target  # noqa: E402


class V25257DisjointObservedReliabilitySelectorBuildAuditTests(unittest.TestCase):
    @staticmethod
    def _fake_tests() -> dict:
        return {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [
                {"pattern": pattern, "expected": expected, "observed": expected, "returncode": 0, "passed": True, "output_sha256": "a" * 64}
                for pattern, expected in target.TEST_SUITES
            ],
        }

    def test_fixed_hash_and_parent_authority_are_exact(self) -> None:
        self.assertEqual(target._fixed_hashes(), {str(path): digest for path, digest in target.FIXED_HASHES.items()})
        self.assertTrue(target._parent_barrier())
        self.assertEqual(
            tuple(Path(row["path"]) for row in target._dependency_vector()),
            target.EXPECTED_DEPENDENCY_PATHS,
        )

    def test_capability_is_fixed_process_only_and_label_blind(self) -> None:
        value = target._capability_audit()
        self.assertTrue(value["all_process_methods_are_subprocess_run"])
        self.assertEqual(len(value["subprocess_calls"]), 4)
        self.assertEqual(value["inherited_selector_audit"]["process_call_count"], 3)
        self.assertEqual(value["shell_true_lines"], [])
        self.assertEqual(value["forbidden_network_model_evaluator_imports"], [])
        self.assertEqual(value["privileged_runtime_field_accesses"], [])
        self.assertEqual(value["semantic_privileged_runtime_field_accesses"], [])
        self.assertEqual(value["evaluator_capabilities"], [])
        self.assertEqual(value["credential_literal_hits"], [])

    def test_build_audit_authorizes_one_freeze_only(self) -> None:
        with mock.patch.object(target, "_tests", return_value=self._fake_tests()):
            value = target.build_audit(now=1, tracked=False)
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["authorization"]["single_disjoint_population_freeze_after_separate_execution_start"])
        self.assertFalse(value["authorization"]["external_activation_or_launch"])

    def test_resealed_launch_overlap_credit_or_hidden_tamper_fails(self) -> None:
        with mock.patch.object(target, "_tests", return_value=self._fake_tests()):
            value = target.build_audit(now=1, tracked=False)
        for kind in (
            "launch", "overlap", "credit", "capability_hidden", "suite_hidden",
            "process_hidden", "watcher_hidden", "dependency_hidden",
            "inherited_hidden",
        ):
            changed = copy.deepcopy(value)
            if kind == "launch":
                changed["authorization"]["external_activation_or_launch"] = True
            elif kind == "overlap":
                changed["population_contract"]["old_population_exact_overlap_required"] = 1
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            elif kind == "capability_hidden":
                changed["capability_audit"]["hidden_authority"] = True
            elif kind == "suite_hidden":
                changed["tests"]["suites"][0]["hidden_authority"] = True
            elif kind == "process_hidden":
                changed["capability_audit"]["subprocess_calls"][0]["hidden_authority"] = True
            elif kind == "watcher_hidden":
                changed["runtime_state"]["protected_watchers"][0]["hidden_authority"] = True
            elif kind == "dependency_hidden":
                changed["selector_dependency_vector"][0]["hidden_authority"] = True
            else:
                changed["capability_audit"]["inherited_selector_audit"]["hidden_authority"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.runtime_audit.external.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_auditor_does_not_call_network_model_or_evaluator(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        self.assertNotIn("official_eval", source)
        self.assertNotIn("evaluate_", source)
        self.assertNotIn("requests.", source)


if __name__ == "__main__":
    unittest.main()
