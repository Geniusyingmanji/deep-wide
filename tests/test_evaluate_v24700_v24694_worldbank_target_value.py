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

from scripts import evaluate_v24700_v24694_worldbank_target_value as evaluator  # noqa: E402


class V24700WorldBankEvaluatorTests(unittest.TestCase):
    @staticmethod
    def metrics(*, target_exact_gain: int = 0) -> dict:
        base = {
            "tasks": 12,
            "exact_table_successes": 0,
            "entity_recall": 1.0,
            "row_f1": 1.0,
            "item_f1": 0.0,
            "column_f1": 1.0,
            "composite": 0.75,
            "unknown_value_cells": 96,
        }
        expanded = dict(base)
        target = dict(base)
        target["exact_table_successes"] = target_exact_gain
        target["item_f1"] = 0.5 if target_exact_gain else 0.0
        target["composite"] = 0.875 if target_exact_gain else 0.75
        keys = (
            "exact_table_successes",
            "entity_recall",
            "row_f1",
            "item_f1",
            "column_f1",
            "composite",
        )
        return {
            "arms": {
                "frozen_parser": dict(base),
                "expanded_parser": expanded,
                "target_value": target,
            },
            "expanded_minus_frozen": {
                key: expanded[key] - base[key] for key in keys
            },
            "target_value_minus_expanded": {
                key: target[key] - expanded[key] for key in keys
            },
            "gate_passed": target_exact_gain > 0,
        }

    def test_preregister_binds_frozen_parent_and_evaluator_surfaces(self) -> None:
        audit = {
            "checks": {
                "target_value_differs_from_expanded_tasks": 11,
                "valid_exact_record_count": 66,
                "missing_response_count": 30,
            }
        }
        with patch.object(evaluator, "absent"), patch.object(
            evaluator, "_validate_parent", return_value=({}, audit, {})
        ), patch.object(
            evaluator, "_validate_evaluator_surfaces", return_value=([{}] * 48, {"records": [{}] * 96})
        ), patch.object(
            evaluator, "source_manifest", return_value={"x": "a" * 64}
        ), patch.object(evaluator, "sha256", return_value="b" * 64), patch.object(
            evaluator, "git", return_value="c" * 40
        ):
            value = evaluator.preregister(now=0)
        self.assertEqual(value["selected_tasks"], 12)
        self.assertEqual(value["gold_rows"], 48)
        self.assertEqual(value["provenance_records"], 96)
        self.assertEqual(value["mechanism_changed_task_count"], 11)
        self.assertTrue(value["authorization"]["one_external_evaluation"])
        self.assertFalse(value["authorization"]["exact220_launch"])
        unsigned = dict(value)
        seal = unsigned.pop("protocol_sha256")
        self.assertEqual(seal, evaluator.payload_sha256(unsigned))

    def test_strict_target_gain_is_go(self) -> None:
        metrics = self.metrics(target_exact_gain=3)
        self.assertTrue(evaluator._metrics_valid(metrics))
        with patch.object(evaluator, "absent"), patch.object(
            evaluator, "_validate_evaluator_protocol", return_value={}
        ), patch.object(
            evaluator, "_validate_evaluator_surfaces", return_value=([], {})
        ), patch.object(
            evaluator, "evaluate_frozen_rows", return_value=metrics
        ), patch.object(evaluator, "sha256", return_value="a" * 64), patch.object(
            evaluator.Path, "read_text", return_value=""
        ):
            value = evaluator.evaluate(now=0)
        self.assertTrue(value["passed"])
        self.assertEqual(value["status"], "worldbank_target_value_external_go")
        self.assertTrue(value["authorization"]["fresh_deepwidebench_candidate_design"])
        self.assertFalse(value["authorization"]["exact220_launch"])

    def test_equal_target_and_expanded_is_no_go(self) -> None:
        metrics = self.metrics(target_exact_gain=0)
        self.assertTrue(evaluator._metrics_valid(metrics))
        self.assertFalse(metrics["gate_passed"])

    def test_metric_delta_or_gate_tamper_is_rejected(self) -> None:
        changed = copy.deepcopy(self.metrics(target_exact_gain=3))
        changed["target_value_minus_expanded"]["composite"] = 999.0
        self.assertFalse(evaluator._metrics_valid(changed))
        changed = self.metrics(target_exact_gain=3)
        changed["gate_passed"] = False
        self.assertFalse(evaluator._metrics_valid(changed))

    def test_claim_scope_never_claims_deepwidebench_entropy_or_sota(self) -> None:
        metrics = self.metrics(target_exact_gain=0)
        with patch.object(evaluator, "absent"), patch.object(
            evaluator, "_validate_evaluator_protocol", return_value={}
        ), patch.object(
            evaluator, "_validate_evaluator_surfaces", return_value=([], {})
        ), patch.object(
            evaluator, "evaluate_frozen_rows", return_value=metrics
        ), patch.object(evaluator, "sha256", return_value="a" * 64), patch.object(
            evaluator.Path, "read_text", return_value=""
        ):
            value = evaluator.evaluate(now=0)
        self.assertFalse(value["claim_scope"]["deepwidebench_quality_measured"])
        self.assertFalse(value["claim_scope"]["entropy_or_credit_assignment_validated"])
        self.assertFalse(value["claim_scope"]["sota_supported"])

    def test_clean_guard_precedes_publication(self) -> None:
        with patch.object(evaluator, "git", return_value="dirty"):
            with self.assertRaisesRegex(RuntimeError, "clean HEAD"):
                evaluator.clean()


if __name__ == "__main__":
    unittest.main()
