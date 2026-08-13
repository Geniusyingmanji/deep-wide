from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25312_v25309_deadline_identity as target  # noqa: E402


class V25312DeadlineIdentityDiagnosisTests(unittest.TestCase):
    def test_build_and_validate_diagnosis(self) -> None:
        value = target.build_diagnosis(now=1)
        self.assertEqual(target.validate_diagnosis(value), value)
        self.assertEqual(
            value["root_cause"],
            "model_search_minimum_attempt_seconds_identity_mismatch",
        )

    def test_effects_are_exactly_zero(self) -> None:
        aggregate = target.build_diagnosis(now=1)["aggregate"]
        for name in (
            "model_requests", "model_attempts", "physical_queries", "physical_fetches",
            "system_total_tokens", "model_slot_acquisitions", "model_slot_timeouts",
        ):
            self.assertEqual(aggregate[name], 0)
        self.assertEqual(aggregate["failure_type_counts"], {"ValidationError": 12})

    def test_deadline_identity_mismatch_is_exact(self) -> None:
        value = target.build_diagnosis(now=1)["deadline_identity"]
        self.assertTrue(value["absolute_deadline_equal"])
        self.assertEqual(value["cleanup_reserve_seconds_model"], value["cleanup_reserve_seconds_search"])
        self.assertEqual(value["minimum_attempt_seconds_model"], 0.05)
        self.assertEqual(value["minimum_attempt_seconds_search"], 0.01)
        self.assertFalse(value["aligned_deadlines"])

    def test_tamper_fails_closed(self) -> None:
        value = target.build_diagnosis(now=1)
        changed = copy.deepcopy(value)
        changed["authorization"]["v25309_postfreeze_evaluator"] = True
        changed.pop("diagnosis_payload_sha256")
        changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_diagnosis(changed)

    def test_static_call_chain_barrier(self) -> None:
        self.assertTrue(target._call_chain_barrier())


if __name__ == "__main__":
    unittest.main()
