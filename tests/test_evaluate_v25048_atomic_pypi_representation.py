from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25048_atomic_pypi_representation_contract as contract  # noqa: E402
from scripts import evaluate_v25048_atomic_pypi_representation as target  # noqa: E402


class V25048AtomicPyPIEvaluatorTests(unittest.TestCase):
    def _gold(self) -> dict[str, str]:
        return {
            "Package": "demo-package",
            "Latest version": "2.0.0",
            "Latest release date (YYYY-MM-DD)": "2026-08-01",
            "Requires-Python": ">=3.10",
        }

    def _prediction(self) -> str:
        return (
            "| Package | Latest version | Latest release date (YYYY-MM-DD) | Requires-Python |\n"
            "| --- | --- | --- | --- |\n"
            "| demo_package | 2.0.0 | 2026-08-01 | >= 3.10 |"
        )

    def test_exact_prediction_scores_one(self) -> None:
        value = target.evaluate_prediction(self._prediction(), self._gold())
        self.assertEqual(value["exact_table_success"], 1)
        self.assertEqual(value["composite"], 1.0)

    def test_wrong_date_loses_exact_and_item_credit(self) -> None:
        value = target.evaluate_prediction(
            self._prediction().replace("2026-08-01", "Unknown"), self._gold()
        )
        self.assertEqual(value["exact_table_success"], 0)
        self.assertLess(value["item_f1"], 1.0)
        self.assertEqual(value["entity_recall"], 1.0)

    def test_extra_row_prevents_exact_and_reduces_row_f1(self) -> None:
        value = target.evaluate_prediction(
            self._prediction() + "\n| other | 1 | 2026-01-01 | >=3.9 |",
            self._gold(),
        )
        self.assertEqual(value["exact_table_success"], 0)
        self.assertLess(value["row_f1"], 1.0)

    def test_quality_gate_requires_strict_exact_gain_and_nonregression(self) -> None:
        arms = {
            contract.CONTROL_ARM: {
                "tasks": 20, "evaluator_valid": 20,
                "evaluator_invalid_or_not_run": 0, "fallback_tasks": 0,
                "exact_table_successes": 2,
                **{metric: 0.7 for metric in target.METRICS},
            },
            contract.CANDIDATE_ARM: {
                "tasks": 20, "evaluator_valid": 20,
                "evaluator_invalid_or_not_run": 0, "fallback_tasks": 0,
                "exact_table_successes": 3,
                **{metric: 0.8 for metric in target.METRICS},
            },
        }
        keys = (
            "exact_table_successes", *target.METRICS,
            "evaluator_invalid_or_not_run", "fallback_tasks",
        )
        delta = {
            key: arms[contract.CANDIDATE_ARM][key]
            - arms[contract.CONTROL_ARM][key]
            for key in keys
        }
        metrics = {
            "arms": arms,
            f"{contract.CANDIDATE_ARM}_minus_{contract.CONTROL_ARM}": delta,
        }
        mechanism = {"mechanism_gate_passed": True}
        self.assertTrue(
            target.quality_decision(metrics, mechanism)[
                "pypi_current_record_representation_quality_gate_go"
            ]
        )
        delta["item_f1"] = -0.01
        self.assertFalse(
            target.quality_decision(metrics, mechanism)[
                "pypi_current_record_representation_quality_gate_go"
            ]
        )

    def test_quality_gate_rejects_tie_or_mechanism_no_go(self) -> None:
        empty = {
            "arms": {
                arm: {
                    "tasks": 20, "evaluator_valid": 20,
                    "evaluator_invalid_or_not_run": 0, "fallback_tasks": 0,
                    "exact_table_successes": 1,
                    **{metric: 1.0 for metric in target.METRICS},
                }
                for arm in contract.ARMS
            },
            f"{contract.CANDIDATE_ARM}_minus_{contract.CONTROL_ARM}": {
                "exact_table_successes": 0,
                **{metric: 0.0 for metric in target.METRICS},
                "evaluator_invalid_or_not_run": 0,
                "fallback_tasks": 0,
            },
        }
        self.assertFalse(
            target.quality_decision(empty, {"mechanism_gate_passed": True})[
                "pypi_current_record_representation_quality_gate_go"
            ]
        )
        empty[f"{contract.CANDIDATE_ARM}_minus_{contract.CONTROL_ARM}"][
            "exact_table_successes"
        ] = 1
        self.assertFalse(
            target.quality_decision(empty, {"mechanism_gate_passed": False})[
                "pypi_current_record_representation_quality_gate_go"
            ]
        )

    def test_forward_audit_tamper_fails_closed(self) -> None:
        value = target._read(contract.FORWARD_AUDIT, tracked=True)
        self.assertTrue(target.validate_forward_audit(value)["audit_valid"])
        changed = copy.deepcopy(value)
        changed["persistence_order_erratum"][
            "prediction_snapshot_or_forward_artifact_modified"
        ] = True
        changed = contract.seal(changed, "audit_payload_sha256")
        with self.assertRaises(RuntimeError):
            target.validate_forward_audit(changed)

    def test_evaluator_source_has_no_network_client_import(self) -> None:
        source = (ROOT / contract.EVALUATOR).read_text(encoding="utf-8")
        tree = ast.parse(source)
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(item.name.split(".", 1)[0] for item in node.names)
            elif isinstance(node, ast.ImportFrom):
                roots.add((node.module or "").split(".", 1)[0])
        self.assertFalse(
            roots.intersection({"requests", "httpx", "aiohttp", "urllib", "http", "socket"})
        )


if __name__ == "__main__":
    unittest.main()
