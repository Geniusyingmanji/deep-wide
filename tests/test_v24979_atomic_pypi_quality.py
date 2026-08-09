from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24979_atomic_pypi_quality_contract as contract  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import control_v24979_atomic_pypi_quality as control  # noqa: E402
from scripts import finalize_v24979_atomic_pypi_quality as finalizer  # noqa: E402
from scripts import run_v24979_atomic_pypi_quality as runner  # noqa: E402


class V24979AtomicPyPIQualityTests(unittest.TestCase):
    def test_population_is_fresh_fixed_and_unprobed(self) -> None:
        self.assertEqual(len(contract.PROJECTS), 20)
        self.assertEqual(len(set(contract.PROJECTS)), 20)
        self.assertFalse(set(contract.PROJECTS) & contract.PRIOR_PROJECTS)
        self.assertTrue(all(set(row) == {"opaque_id", "question"} for row in contract.task_vector()))

    def test_protocol_freezes_one_authority_and_atomic_barrier(self) -> None:
        value = contract.validate_protocol_untracked(
            ROOT, contract.build_protocol_untracked(ROOT, now=1)
        )
        self.assertEqual(value["execution"]["fetch_targets_per_task"], 1)
        self.assertEqual(value["atomic_parser_readiness"]["parser_ready_unique_fields"], 100)
        self.assertEqual(value["atomic_parser_readiness"]["model_calls_if_parser_no_go"], 0)
        self.assertFalse(value["authorization"]["public_exact220_or_sota"])

    def _prepared(self, count: int = 20) -> list[dict]:
        return [
            {
                "index": index,
                "opaque_id": contract.task_vector()[index]["opaque_id"],
                "ready": True,
                "fetch_attempts": 1,
                "fetch_successes": 1,
                "receipt": {"unique_bound_field_count": 5, "conflicting_field_count": 0},
            }
            for index in range(count)
        ]

    def test_readiness_requires_twenty_tasks_and_one_hundred_fields(self) -> None:
        value = runner.parser_readiness(self._prepared())
        self.assertTrue(value["passed"])
        bad = self._prepared()
        bad[0]["ready"] = False
        bad[0]["receipt"]["unique_bound_field_count"] = 0
        value = runner.parser_readiness(bad)
        self.assertFalse(value["passed"])
        self.assertFalse(value["authorization"]["paired_model_forward"])

    def test_readiness_receipt_is_counts_only(self) -> None:
        value = runner.parser_readiness(self._prepared())
        self.assertFalse(value["contains_identity_question_value_url_page_prediction_or_credential"])
        self.assertNotIn("rows", value)

    def test_prepare_failure_never_calls_model(self) -> None:
        with mock.patch.object(runner.transport, "_fetch_exact", side_effect=ValueError("failed")), mock.patch.object(runner.schema_runner, "_synthesize") as model:
            value = runner._prepare(0)
        self.assertFalse(value["ready"])
        self.assertNotIn("question", value)
        model.assert_not_called()

    def test_raw_evidence_is_fixed_prefix_not_projected_record(self) -> None:
        page = {"text": '{"noise":"' + "x" * 20_000}
        value = runner._raw_evidence(page)
        self.assertEqual(len(value), contract.EVIDENCE_CHARS)
        self.assertTrue(value.startswith("[PYPI JSON]\n"))
        self.assertNotIn("IDENTITY-BOUND", value)

    def test_mechanism_gate_requires_prediction_change_and_all_fields(self) -> None:
        expected = contract.gates()["mechanism"]
        value = {
            "terminal_tasks": 20, "completed_tasks": 20, "fallback_tasks": 0,
            "fetch_attempts": 20, "successful_shared_fetches": 20,
            "admitted_compact_records": 20, "candidate_evidence_changed_tasks": 20,
            "prediction_changed_tasks": 9, "unique_bound_fields": 100,
            "field_conflicts": 0,
            "evidence_chars": {arm: expected["evidence_chars_per_arm"] for arm in contract.ARMS},
        }
        for arm in contract.ARMS:
            value[f"{arm}_model_successes"] = 20
            value[f"{arm}_model_attempts"] = 20
        self.assertFalse(runner.mechanism_decision(value)["mechanism_gate_passed"])
        value["prediction_changed_tasks"] = 10
        self.assertTrue(runner.mechanism_decision(value)["mechanism_gate_passed"])

    def test_evaluator_exact_and_partial_metrics(self) -> None:
        gold = {
            "package": "demo-pkg", "latest_version": "2.0", "requires_python": ">=3.10",
            "release_file_count": "2", "first_upload_date": "2026-08-01",
            "largest_file_size_bytes": "450",
        }
        prediction = (
            "| Package | Latest version | Requires-Python | Current-version file count | Current-version first upload date (YYYY-MM-DD) | Current-version largest file size (bytes) |\n"
            "|---|---|---|---|---|---|\n| demo_pkg | 2.0 | >= 3.10 | 2 | 2026-08-01 | 450 |"
        )
        value = finalizer.evaluate_prediction(prediction, gold)
        self.assertEqual(value["exact_table_success"], 1)
        self.assertEqual(value["composite"], 1.0)
        value = finalizer.evaluate_prediction(prediction.replace("450", "451"), gold)
        self.assertEqual(value["exact_table_success"], 0)
        self.assertLess(value["composite"], 1.0)

    def test_quality_gate_requires_strict_exact_and_nonregression(self) -> None:
        keys = ("entity_recall", "row_f1", "item_f1", "column_f1", "composite")
        arms = {
            contract.CONTROL_ARM: {"evaluator_valid": 20, "exact_table_successes": 5, "evaluator_invalid_or_not_run": 0, "fallback_tasks": 0, **{k: 0.8 for k in keys}},
            contract.CANDIDATE_ARM: {"evaluator_valid": 20, "exact_table_successes": 6, "evaluator_invalid_or_not_run": 0, "fallback_tasks": 0, **{k: 0.81 for k in keys}},
        }
        delta = {k: arms[contract.CANDIDATE_ARM][k] - arms[contract.CONTROL_ARM][k] for k in ("exact_table_successes", *keys, "evaluator_invalid_or_not_run", "fallback_tasks")}
        metrics = {"arms": arms, f"{contract.CANDIDATE_ARM}_minus_{contract.CONTROL_ARM}": delta}
        self.assertTrue(finalizer.quality_decision(metrics, {"mechanism_gate_passed": True})["pypi_release_file_quality_gate_go"])
        delta["item_f1"] = -0.01
        self.assertFalse(finalizer.quality_decision(metrics, {"mechanism_gate_passed": True})["pypi_release_file_quality_gate_go"])

    def test_control_audit_covers_transitive_sources(self) -> None:
        control.configure()
        for source in (contract.SOURCE, contract.EXTRACTOR, contract.RUNTIME, contract.ATOMIC_CONTRACT, contract.SCHEMA_RUNTIME):
            self.assertIn(source, control.base.FORWARD_SOURCES)
        self.assertEqual(control.base.EXPECTED_TESTS, 62)

    def test_forward_sources_are_label_blind_and_evaluator_free(self) -> None:
        control.configure()
        for relative in control.base.FORWARD_SOURCES:
            path = ROOT / relative
            self.assertEqual(semantic_audit._accesses(path, ROOT), [])
            self.assertEqual(semantic_audit._evaluator_capabilities(path, ROOT), [])

    def test_arm_order_is_balanced_and_deterministic(self) -> None:
        orders = contract.arm_order_vector()
        self.assertEqual(sum(order[0] == contract.CANDIDATE_ARM for order in orders), 10)
        self.assertTrue(all(set(order) == set(contract.ARMS) for order in orders))

    def test_finalizer_uses_same_exact_extractor_for_gold(self) -> None:
        source = (ROOT / contract.FINALIZER).read_text(encoding="utf-8")
        tree = ast.parse(source)
        fetch = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_fetch_gold")
        calls = [node for node in ast.walk(fetch) if isinstance(node, ast.Call)]
        self.assertTrue(any(isinstance(call.func, ast.Attribute) and call.func.attr == "extract_record" for call in calls))


if __name__ == "__main__":
    unittest.main()
