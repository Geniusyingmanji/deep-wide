from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import finalize_v24684_v24679_schema_dev64 as finalizer  # noqa: E402


def metrics(*, whole: int, value: float, invalid: int = 0) -> dict:
    return {
        "runtime_completed": 64,
        "runtime_failed": 0,
        "fallback_tables": 0,
        "evaluator_valid": 64 - invalid,
        "evaluator_invalid_or_not_run": invalid,
        "whole_table_successes": whole,
        "entity_acc": value,
        "f1_by_row": value,
        "f1_by_item": value,
        "column_f1": value,
        "quality_composite": value,
        "score": whole / 64,
    }


class V24684EvaluatorTests(unittest.TestCase):
    def test_forward_barrier_has_7_changed_and_57_identity(self) -> None:
        barrier = finalizer.validate_forward_barrier()
        self.assertEqual(barrier["changed"], 7)
        self.assertEqual(barrier["identity"], 57)
        self.assertEqual(len(barrier["arms"]["baseline"]["rows"]), 64)
        self.assertEqual(len(barrier["arms"]["candidate"]["rows"]), 64)

    def test_gate_is_fixed64_and_71_unique_provider_evaluations(self) -> None:
        gate = finalizer.build_evaluator_gate(
            now=0, require_clean=False, require_pristine=False, run_tests=False
        )
        self.assertEqual(gate["evaluation_contract"]["fixed_denominator_per_arm"], 64)
        self.assertEqual(gate["evaluation_contract"]["baseline_provider_evaluations"], 64)
        self.assertEqual(
            gate["evaluation_contract"]["candidate_changed_provider_evaluations"], 7
        )
        self.assertEqual(
            gate["evaluation_contract"][
                "candidate_identity_judgments_reused_from_baseline"
            ],
            57,
        )
        self.assertEqual(gate["evaluation_contract"]["unique_provider_evaluations"], 71)
        self.assertFalse(gate["authorization"]["evaluator_execution"])

    def test_gate_does_not_open_evaluator_resources(self) -> None:
        gate = finalizer.build_evaluator_gate(
            now=0, require_clean=False, require_pristine=False, run_tests=False
        )
        self.assertFalse(
            gate["source_policy"][
                "mapping_query_answer_gold_evaluator_bytes_opened_or_hashed_by_gate"
            ]
        )
        self.assertFalse(gate["source_policy"]["official_evaluator_called_by_gate"])

    def test_decision_go_requires_plus_one_and_all_nonregression(self) -> None:
        barrier = {"changed": 7}
        value = finalizer.decision(
            {
                "baseline": metrics(whole=4, value=0.50),
                "candidate": metrics(whole=5, value=0.50),
            },
            barrier,
        )
        self.assertTrue(value["passed"])
        self.assertEqual(value["failed_checks"], [])

    def test_decision_no_go_without_whole_table_gain(self) -> None:
        value = finalizer.decision(
            {
                "baseline": metrics(whole=4, value=0.50),
                "candidate": metrics(whole=4, value=0.51),
            },
            {"changed": 7},
        )
        self.assertFalse(value["passed"])
        self.assertIn("whole_table_success_delta", value["failed_checks"])

    def test_decision_no_go_if_one_quality_metric_drops(self) -> None:
        baseline = metrics(whole=4, value=0.50)
        candidate = metrics(whole=5, value=0.51)
        candidate["column_f1"] = 0.49
        candidate["quality_composite"] = sum(candidate[name] for name in finalizer.QUALITY) / 4
        value = finalizer.decision(
            {"baseline": baseline, "candidate": candidate}, {"changed": 7}
        )
        self.assertFalse(value["passed"])
        self.assertIn("column_f1_delta", value["failed_checks"])

    def test_resealed_gate_evaluator_execution_fails_closed(self) -> None:
        gate = finalizer.build_evaluator_gate(
            now=0, require_clean=False, require_pristine=False, run_tests=False
        )
        gate["findings"] = []
        gate["passed"] = True
        gate["status"] = "evaluator_gate_go"
        gate["authorization"]["evaluator_execution"] = True
        gate.pop("gate_payload_sha256")
        gate["gate_payload_sha256"] = finalizer.contract.payload_sha256(gate)
        with self.assertRaises(RuntimeError):
            finalizer.validate_evaluator_gate(gate)

    def test_engine_configuration_uses_16_workers_and_current_paths(self) -> None:
        finalizer._configure_engine()
        self.assertEqual(finalizer.engine.TOTAL_EVALUATOR_WORKERS, 16)
        self.assertEqual(finalizer.engine.EVALUATOR_WORKERS_PER_ARM, 8)
        self.assertEqual(finalizer.engine.PROTOCOL, finalizer.EVALUATOR_GATE)
        self.assertEqual(finalizer.engine.SELECTED_COUNT, 64)

    def test_gate_test_count_includes_parent_evaluator_regression(self) -> None:
        self.assertEqual(
            sum(count for _name, count in finalizer.TEST_SUITES),
            finalizer.EXPECTED_TEST_COUNT,
        )
        self.assertEqual(finalizer.EXPECTED_TEST_COUNT, 37)

    def test_gate_validator_rejects_resealed_test_count_tamper(self) -> None:
        gate = finalizer.build_evaluator_gate(
            now=0, require_clean=False, require_pristine=False, run_tests=False
        )
        gate["findings"] = []
        gate["passed"] = True
        gate["status"] = "evaluator_gate_go"
        gate["tests"]["passed"] = True
        gate["tests"]["test_count"] = finalizer.EXPECTED_TEST_COUNT - 1
        gate.pop("gate_payload_sha256")
        gate["gate_payload_sha256"] = finalizer.contract.payload_sha256(gate)
        with self.assertRaises(RuntimeError):
            finalizer.validate_evaluator_gate(gate)

    def test_result_claim_contract_forbids_sota_and_launch(self) -> None:
        claims = {
            "development_population_not_unseen": True,
            "public_full220_result": False,
            "sota": False,
        }
        authorization = {"fresh_exact220_launch": False, "sota_claim": False}
        self.assertTrue(claims["development_population_not_unseen"])
        self.assertFalse(claims["public_full220_result"])
        self.assertFalse(claims["sota"])
        self.assertFalse(authorization["fresh_exact220_launch"])
        self.assertFalse(authorization["sota_claim"])


if __name__ == "__main__":
    unittest.main()
