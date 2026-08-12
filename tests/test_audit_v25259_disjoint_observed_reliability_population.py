from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25259_disjoint_observed_reliability_population as target  # noqa: E402


class V25259DisjointObservedReliabilityPopulationAuditTests(unittest.TestCase):
    @staticmethod
    def _fake_tests() -> dict:
        return {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [
                {
                    "pattern": pattern, "expected": expected, "observed": expected,
                    "returncode": 0, "passed": True, "output_sha256": "a" * 64,
                }
                for pattern, expected in target.TEST_SUITES
            ],
        }

    def test_fixed_chain_and_execution_start_validate(self) -> None:
        self.assertEqual(
            target._fixed_hashes(),
            {str(path): digest for path, digest in target.FIXED_HASHES.items()},
        )
        start = json.loads((ROOT / target.START).read_text(encoding="utf-8"))
        self.assertEqual(target.validate_start(start), start)

    def test_population_is_exact64_by2_history_zero_and_old_disjoint(self) -> None:
        _claim, population, _start, _parent = target._load()
        tasks = target.freeze.validate_task_vector(population["population"]["task_vector"])
        selected = {
            package
            for task in tasks
            for package in target.freeze._packages_from_question(task["question"])
        }
        self.assertEqual(len(tasks), 64)
        self.assertEqual(len(selected), 128)
        self.assertFalse(selected.intersection(target.freeze._old_entities()))
        self.assertEqual(population["history_receipt"]["history_zero_disjoint_selected_total"], 128)

    def test_build_audit_authorizes_protocol_design_only(self) -> None:
        with mock.patch.object(target, "_tests", return_value=self._fake_tests()):
            value = target.build_audit(now=1, tracked=False)
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["authorization"]["fresh64_observed_reliability_protocol_design"])
        self.assertFalse(value["authorization"]["fresh64_external_activation_or_launch"])

    def test_resealed_nested_hidden_overlap_launch_or_credit_tamper_fails(self) -> None:
        with mock.patch.object(target, "_tests", return_value=self._fake_tests()):
            value = target.build_audit(now=1, tracked=False)
        for kind in ("suite_hidden", "watcher_hidden", "receipt_hidden", "overlap", "launch", "credit"):
            changed = copy.deepcopy(value)
            if kind == "suite_hidden":
                changed["tests"]["suites"][0]["hidden"] = True
            elif kind == "watcher_hidden":
                changed["runtime_state"]["protected_watchers"][0]["hidden"] = True
            elif kind == "receipt_hidden":
                changed["selection_receipt"]["hidden"] = True
            elif kind == "overlap":
                changed["selection_receipt"]["selected_old_overlap_count"] = 1
            elif kind == "launch":
                changed["authorization"]["fresh64_external_activation_or_launch"] = True
            else:
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.parent_audit.runtime_audit.external.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_auditor_has_no_dpkg_history_network_model_or_evaluator_effect(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        self.assertNotIn("dpkg-query", source)
        self.assertNotIn("git log", source)
        self.assertNotIn("requests.", source)
        self.assertNotIn("openai", source.casefold())
        self.assertNotIn("official_eval", source)


if __name__ == "__main__":
    unittest.main()
