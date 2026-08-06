from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import evaluate_v24645_primary_identity_pair as evaluator


class EvaluatorControlTests(unittest.TestCase):
    @staticmethod
    def unpublished_sha256(path: Path, real_sha256):
        unpublished = {
            evaluator.ROOT / evaluator.EVALUATOR_PROTOCOL: "a" * 64,
            evaluator.ROOT / evaluator.RESULT: "b" * 64,
        }
        if path in unpublished:
            return unpublished[path]
        return real_sha256(path)

    @staticmethod
    def equal_metrics() -> dict:
        arm = {
            "tasks": 12,
            "exact_table_successes": 0,
            "entity_recall": 0.0,
            "row_f1": 0.0,
            "item_f1": 0.0,
            "column_f1": 0.0,
            "composite": 0.0,
            "unknown_value_cells": 0,
        }
        return {
            "arms": {"baseline": dict(arm), "deterministic_pair": dict(arm)},
            "candidate_minus_baseline": {
                "exact_table_successes": 0,
                "entity_recall": 0.0,
                "row_f1": 0.0,
                "item_f1": 0.0,
                "column_f1": 0.0,
                "composite": 0.0,
            },
            "gate_passed": False,
        }

    def evaluate_with_synthetic_metrics(self, protocol: dict) -> dict:
        real_sha256 = evaluator.sha256
        with patch.object(evaluator, "read", return_value=protocol), patch.object(
            evaluator,
            "sha256",
            side_effect=lambda path: self.unpublished_sha256(path, real_sha256),
        ), patch.object(
            evaluator, "gold_rows", return_value=[]
        ), patch.object(
            evaluator,
            "evaluate_frozen_rows",
            return_value=self.equal_metrics(),
        ):
            return evaluator.evaluate(now=0)

    def test_preregister_binds_frozen_forward_and_gold(self) -> None:
        value = evaluator.preregister(now=0)
        self.assertEqual(value["selected_tasks"], 12)
        self.assertEqual(value["gold_rows"], 48)
        self.assertFalse(
            value[
                "forward_activation_and_execution_controls_opened_or_hashed_gold"
            ]
        )
        self.assertTrue(
            value[
                "external_quality_evaluation_authorized_only_after_prediction_freeze"
            ]
        )
        self.assertFalse(value["official_deepwidebench_evaluator_called"])
        self.assertTrue(value["authorization"]["one_external_evaluation"])
        self.assertFalse(value["authorization"]["dev64"])
        unsigned = dict(value)
        seal = unsigned.pop("protocol_sha256")
        self.assertEqual(evaluator.payload_sha256(unsigned), seal)

    def test_equal_arms_are_strict_no_go(self) -> None:
        protocol = evaluator.preregister(now=0)
        value = self.evaluate_with_synthetic_metrics(protocol)
        self.assertFalse(value["passed"])
        self.assertEqual(value["status"], "primary_identity_pair_external_no_go")
        self.assertEqual(
            value["metrics"]["candidate_minus_baseline"]["exact_table_successes"],
            0,
        )
        self.assertTrue(value["quality_evaluation_executed_after_prediction_freeze"])
        self.assertFalse(value["authorization"]["fresh_dev64_design"])

    def test_result_claim_scope_never_claims_deepwidebench_or_entropy(self) -> None:
        protocol = evaluator.preregister(now=0)
        value = self.evaluate_with_synthetic_metrics(protocol)
        self.assertFalse(value["claim_scope"]["deepwidebench_quality_measured"])
        self.assertFalse(value["claim_scope"]["entropy_or_credit_assignment_validated"])
        self.assertFalse(value["claim_scope"]["sota_supported"])

    def test_postaudit_rejects_gate_tamper(self) -> None:
        protocol = evaluator.preregister(now=0)
        real_sha256 = evaluator.sha256
        result = self.evaluate_with_synthetic_metrics(protocol)
        tampered = copy.deepcopy(result)
        tampered["passed"] = not result["passed"]
        tampered.pop("result_sha256")
        tampered["result_sha256"] = evaluator.payload_sha256(tampered)
        with patch.object(
            evaluator, "read", side_effect=[tampered, protocol]
        ), patch.object(
            evaluator,
            "sha256",
            side_effect=lambda path: self.unpublished_sha256(path, real_sha256),
        ), patch.object(evaluator, "protected_watcher_snapshot", return_value=[]):
            with self.assertRaisesRegex(RuntimeError, "postresult audit failed"):
                evaluator.postaudit(now=0)

    def test_clean_guard_precedes_evaluation_publication(self) -> None:
        with patch.object(
            evaluator.subprocess,
            "run",
            return_value=type("Completed", (), {"stdout": "dirty\n"})(),
        ):
            with self.assertRaisesRegex(RuntimeError, "clean HEAD"):
                evaluator.clean()


if __name__ == "__main__":
    unittest.main()
