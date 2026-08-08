from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24257_score_first_runtime as runtime  # noqa: E402
from deepwide_agent import v24922_target_value_exact220_contract as contract  # noqa: E402
from scripts import control_v24922_target_value_exact220 as control  # noqa: E402
from scripts import finalize_v24922_target_value_exact220 as finalizer  # noqa: E402
from scripts import run_v24800_exact220 as engine  # noqa: E402
from scripts import run_v24857_pacing_aware_exact220 as parent_runner  # noqa: E402
from scripts import run_v24857_pacing_aware_exact220_task as parent_child  # noqa: E402
from scripts import run_v24922_target_value_exact220 as runner  # noqa: E402
from scripts import run_v24922_target_value_exact220_task as child  # noqa: E402


class Limits:
    evidence_chars = 60_000
    page_chars = 5_000


QUESTION = """Return one Markdown table.
<COUNTRIES>
1. Alpha Republic [ALP]
</COUNTRIES>
Column names: Country | Target Metric [TM] @2024."""


class V24922TargetValueExact220Tests(unittest.TestCase):
    def setUp(self) -> None:
        child._VISIBLE_QUESTION = QUESTION

    def tearDown(self) -> None:
        child._VISIBLE_QUESTION = None

    def test_exact220_vector_is_label_blind(self) -> None:
        tasks = contract.task_vector(ROOT)
        self.assertEqual(len(tasks), 220)
        self.assertEqual(len({task["opaque_id"] for task in tasks}), 220)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))

    def test_parent_budgets_model_transport_and_concurrency_are_equal(self) -> None:
        parent = contract.parent
        self.assertEqual(contract.LIMITS, parent.LIMITS)
        self.assertEqual(contract.MODEL, parent.MODEL)
        self.assertEqual(contract.SEARCH, parent.SEARCH)
        self.assertEqual(contract.TWO_WAVE_POLICY, parent.TWO_WAVE_POLICY)
        self.assertEqual(
            (contract.EXECUTOR_CONCURRENCY, contract.MODEL_SLOT_CAP, contract.TAVILY_KEY_SLOT_CAP),
            (20, 8, 12),
        )

    def test_treatment_is_complete_projector_component(self) -> None:
        change = contract._single_change()
        self.assertEqual(change["field"], "evidence_projector_component")
        self.assertTrue(
            change[
                "joint_visible_row_value_target_coverage_precedes_independent_phrase_coverage"
            ]
        )
        self.assertEqual(change["total_projection_character_cap_from_to"], [60_000, 30_000])
        self.assertTrue(change["per_page_character_cap_unchanged"])
        self.assertTrue(
            change["selection_rule_and_total_cap_sub_effects_not_separately_identified"]
        )
        self.assertFalse(change["additional_search_fetch_model_token_context_or_wall_cap"])
        self.assertFalse(change["entropy_or_information_gain_assigns_credit_or_routes"])

    def test_projection_uses_fetched_pages_not_search_narrative(self) -> None:
        evidence = child.target_value_evidence_projection(
            [{"results": [{"content": "SEARCH_NARRATIVE"}]}],
            [{"results": [{
                "title": "official",
                "url": "https://official.example/table",
                "raw_content": "| Country | Target Metric |\n|---|---:|\n| Alpha Republic | 999 |",
            }]}],
            Limits(),
        )
        self.assertIn("Alpha Republic", evidence)
        self.assertNotIn("SEARCH_NARRATIVE", evidence)
        self.assertIsNotNone(child._LAST_PROJECTION_RECEIPT)

    def test_target_value_receipt_is_content_free_and_credit_zero(self) -> None:
        child.target_value_evidence_projection(
            [],
            [{"results": [{
                "title": "official",
                "url": "https://official.example/table",
                "content": "Alpha Republic Target Metric: 999",
            }]}],
            Limits(),
        )
        receipt = child._LAST_PROJECTION_RECEIPT
        self.assertIsNotNone(receipt)
        self.assertFalse(receipt["entropy_or_information_gain_assigns_credit"])
        self.assertFalse(
            receipt[
                "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read"
            ]
        )

    def test_unbound_question_and_cap_drift_fail_closed(self) -> None:
        child._VISIBLE_QUESTION = None
        with self.assertRaises(RuntimeError):
            child.target_value_evidence_projection([], [], Limits())
        child._VISIBLE_QUESTION = QUESTION

        class BadLimits:
            evidence_chars = 29_999
            page_chars = 5_000

        with self.assertRaises(RuntimeError):
            child.target_value_evidence_projection([], [], BadLimits())

    def test_child_rebinds_parent_contract_and_runtime_projection(self) -> None:
        original_contract = parent_child.contract
        original_projection = runtime._evidence_projection
        try:
            argv = [
                "child",
                "--result",
                str(ROOT / contract.TASK_ROOT / "task_0001" / "result.json"),
            ]
            with self.assertRaises(RuntimeError):
                child.configure(argv)
            self.assertIs(parent_child.contract, contract)
        finally:
            parent_child.contract = original_contract
            runtime._evidence_projection = original_projection

    def test_runner_rebinds_pacing_parent_and_engine(self) -> None:
        old_parent_contract = parent_runner.contract
        old_engine_contract = engine.contract
        old_summary = engine._direct_search_totals
        try:
            runner.configure()
            self.assertIs(parent_runner.contract, contract)
            self.assertIs(engine.contract, contract)
        finally:
            parent_runner.contract = old_parent_contract
            engine.contract = old_engine_contract
            engine._direct_search_totals = old_summary

    def test_runner_reseals_all_forward_hash_links(self) -> None:
        source = contract.RUNNER.read_text(encoding="utf-8")
        self.assertIn("v24922_target_value_exact220_run_summary", source)
        self.assertIn("v24922_target_value_exact220_prediction_freeze", source)
        self.assertIn("v24922_target_value_exact220_forward_result", source)
        self.assertIn('freeze["run_summary_sha256"]', source)
        self.assertIn('forward["prediction_freeze_sha256"]', source)

    def test_control_audit_surface_has_no_privileged_or_evaluator_capability(self) -> None:
        old = (
            control.base.contract,
            control.base.RUNTIME_SOURCES,
            control.base.TEST_SUITES,
            control.base.EXPECTED_TESTS,
        )
        try:
            control.configure()
            self.assertEqual(control.base.EXPECTED_TESTS, sum(item[1] for item in control.base.TEST_SUITES))
            self.assertEqual(control.base._runtime_findings(), ([], [], []))
        finally:
            (
                control.base.contract,
                control.base.RUNTIME_SOURCES,
                control.base.TEST_SUITES,
                control.base.EXPECTED_TESTS,
            ) = old

    def test_finalizer_uses_fresh_complete_surface(self) -> None:
        finalizer.configure()
        self.assertIs(finalizer.base.contract, contract)
        self.assertTrue(str(finalizer.base.EVALUATOR_ROOT).startswith(str(contract.OUTPUT_ROOT)))
        self.assertIn("v24857", finalizer.base.REFERENCES)

    def test_runtime_sources_have_no_evaluator_import(self) -> None:
        for relative in (contract.RUNNER, contract.CHILD, contract.PROJECTOR_SOURCE):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
            self.assertFalse(any("evaluator" in name or "finalize" in name for name in imports))

    def test_all_four_watchers_are_protected(self) -> None:
        self.assertEqual(
            [item["pid"] for item in contract.protected_watcher_snapshot()],
            [795336, 3061652, 2808901, 2889939],
        )

    def test_build_audit_is_clean_and_entropy_shadow_only(self) -> None:
        audit = contract._validate_build_audit(ROOT)
        self.assertTrue(audit["audit_valid"])
        self.assertEqual(audit["findings"], [])
        self.assertFalse(
            audit["source_policy"]["entropy_or_information_gain_assigns_signed_credit"]
        )

    def test_projection_summary_empty_denominator_is_well_formed(self) -> None:
        original = contract.SELECTED_COUNT
        try:
            contract.SELECTED_COUNT = 0
            summary = contract.projection_receipt_summary(ROOT)
        finally:
            contract.SELECTED_COUNT = original
        self.assertEqual(summary["expected_receipts"], 0)
        self.assertFalse(summary["mapping_gold_category_question_type_split_evaluator_score_reward_read"])


if __name__ == "__main__":
    unittest.main()
