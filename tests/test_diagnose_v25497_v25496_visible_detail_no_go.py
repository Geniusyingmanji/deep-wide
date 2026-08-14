from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25497_v25496_visible_detail_no_go as target  # noqa: E402


class V25497VisibleDetailDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_frozen_aggregate_diagnosis_is_valid_no_go(self) -> None:
        value = target.validate_diagnosis(self.value)
        self.assertTrue(value["audit_valid"])
        self.assertFalse(value["diagnosis"]["mechanism_gate_passed"])
        self.assertTrue(value["content_free_aggregate_only"])

    def test_reach_and_parse_bottlenecks_are_both_frozen(self) -> None:
        diagnosis = self.value["diagnosis"]
        self.assertEqual(diagnosis["tasks_without_unique_detail_request"], 16)
        self.assertEqual(
            diagnosis["identity_bound_detail_pages_without_field_surface"], 4
        )
        self.assertTrue(diagnosis["two_stage_bottleneck_frozen"])

    def test_runtime_failure_and_capacity_are_not_observed_cause(self) -> None:
        diagnosis = self.value["diagnosis"]
        self.assertTrue(
            diagnosis["runtime_failure_budget_or_capacity_is_not_the_observed_cause"]
        )
        self.assertEqual(
            diagnosis["unused_fetch_capacity_under_existing_hard_cap_aggregate"],
            76,
        )

    def test_only_design_and_question_only_audit_are_authorized(self) -> None:
        authorization = self.value["authorization"]
        self.assertTrue(
            authorization["exact220_question_only_visible_signal_transfer_audit"]
        )
        self.assertTrue(
            authorization["generic_visible_schema_successor_build_design"]
        )
        self.assertFalse(authorization["external_protocol_or_forward"])
        self.assertFalse(authorization["deepwidebench_forward_or_evaluator"])
        self.assertEqual(self.value["positive_signed_credit_count"], 0)

    def test_resealed_funnel_launch_or_credit_tamper_fails(self) -> None:
        for kind in ("funnel", "launch", "credit"):
            changed = copy.deepcopy(self.value)
            if kind == "funnel":
                changed["diagnosis"]["funnel_task_counts"][
                    "logical_detail_request_tasks"
                ] = 5
            elif kind == "launch":
                changed["authorization"]["external_protocol_or_forward"] = True
            else:
                changed["positive_signed_credit_count"] = 1
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(
                changed
            )
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
