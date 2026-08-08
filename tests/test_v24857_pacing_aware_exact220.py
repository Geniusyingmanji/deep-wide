from __future__ import annotations

import ast
import io
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24854_rate_aware_exact220_contract as parent  # noqa: E402
from deepwide_agent import v24857_pacing_aware_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24852_rate_aware_tavily_search import RateAwareDeadlineTavilyThinCompatibilityClient  # noqa: E402
from deepwide_agent.v24856_pacing_aware_admission import POLICY_ID as ADMISSION_POLICY_ID  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import control_v24857_pacing_aware_exact220 as control  # noqa: E402
from scripts import finalize_v24857_pacing_aware_exact220 as finalizer  # noqa: E402
from scripts import run_v24800_exact220 as parent_runner  # noqa: E402
from scripts import run_v24857_pacing_aware_exact220 as runner  # noqa: E402
from scripts import run_v24857_pacing_aware_exact220_task as child  # noqa: E402


class V24857PacingAwareExact220Tests(unittest.TestCase):
    def test_parent_algorithm_budgets_are_equal(self) -> None:
        self.assertEqual(contract.LIMITS, parent.LIMITS)
        self.assertEqual(contract.MODEL, parent.MODEL)
        self.assertEqual(contract.SEARCH, parent.SEARCH)
        self.assertEqual(contract.TWO_WAVE_POLICY, parent.TWO_WAVE_POLICY)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 8)
        self.assertEqual(contract.TAVILY_KEY_SLOT_CAP, 12)

    def test_only_declared_change_is_pacing_admission(self) -> None:
        policy = contract.pacing_policy()
        self.assertEqual(policy["policy_id"], ADMISSION_POLICY_ID)
        self.assertEqual(policy["maximum_provider_wait_credit_seconds"], 30.0)
        self.assertFalse(policy["absolute_task_deadline_changed"])
        self.assertFalse(policy["query_fetch_model_token_or_context_cap_changed"])

    def test_visible_vector_is_exact220_and_label_blind(self) -> None:
        tasks = contract.task_vector(ROOT)
        self.assertEqual(len(tasks), 220)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))

    def test_surfaces_are_fresh(self) -> None:
        self.assertNotEqual(contract.PROTOCOL, parent.PROTOCOL)
        self.assertNotEqual(contract.OUTPUT_ROOT, parent.OUTPUT_ROOT)
        self.assertNotEqual(contract.RUNNER_MARKER, parent.RUNNER_MARKER)
        self.assertNotEqual(contract.CHILD_MARKER, parent.CHILD_MARKER)

    def test_child_uses_rate_transport_and_pacing_runner(self) -> None:
        source = (ROOT / contract.CHILD).read_text(encoding="utf-8")
        self.assertIn("RateAwareDeadlineTavilyThinCompatibilityClient", source)
        self.assertIn("run_pacing_aware_two_wave_retrieval", source)
        self.assertIn('os.environ.pop(_CREDENTIAL_ENVIRONMENT, "")', source)
        self.assertIsNotNone(RateAwareDeadlineTavilyThinCompatibilityClient)

    def test_runner_rebinds_transport_contract_and_pacing_validation(self) -> None:
        original_contract = parent_runner.contract
        original_prepare = parent_runner.prepare_key_slots
        try:
            runner.configure()
            self.assertIs(parent_runner.contract, contract)
            self.assertEqual(parent_runner.prepare_key_slots.__name__, "prepare_rate_aware_key_slots")
        finally:
            parent_runner.contract = original_contract
            parent_runner.prepare_key_slots = original_prepare

    def test_control_audits_new_runtime_and_expected_tests(self) -> None:
        original = (control.base.contract, control.base.RUNTIME_SOURCES, control.base.TEST_SUITES, control.base.EXPECTED_TESTS)
        try:
            control.configure()
            self.assertEqual(control.base.EXPECTED_TESTS, 92)
            self.assertIn(contract.ADMISSION_SOURCE, control.base.RUNTIME_SOURCES)
            fields, evaluator, secrets = control.base._runtime_findings()
            self.assertEqual((fields, evaluator, secrets), ([], [], []))
        finally:
            (control.base.contract, control.base.RUNTIME_SOURCES, control.base.TEST_SUITES, control.base.EXPECTED_TESTS) = original

    def test_finalizer_uses_fresh_complete_evaluator_surface(self) -> None:
        finalizer.configure()
        self.assertIs(finalizer.base.contract, contract)
        self.assertTrue(str(finalizer.base.EVALUATOR_ROOT).startswith(str(contract.OUTPUT_ROOT)))
        self.assertIn("v24854", finalizer.base.REFERENCES)

    def test_runtime_sources_have_no_evaluator_import(self) -> None:
        for path in (contract.RUNNER, contract.CHILD, contract.ADMISSION_SOURCE):
            source = (ROOT / path).read_text(encoding="utf-8")
            tree = ast.parse(source)
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
            self.assertFalse(any("evaluator" in name or "finalize" in name for name in imports))
            self.assertEqual(semantic_audit._accesses((ROOT / path).resolve(), ROOT), [])

    def test_child_rejects_missing_credential_pool_before_effect(self) -> None:
        with mock.patch.dict(child.os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                child._credentials_from_environment()

    def test_pacing_total_is_content_free(self) -> None:
        with mock.patch.object(contract, "SELECTED_COUNT", 0):
            value = runner._pacing_totals(ROOT)
        self.assertFalse(value["mapping_gold_category_question_type_split_evaluator_score_reward_read"])
        self.assertTrue(value["same_pass_content_free_transport_telemetry_only"])

    def test_child_never_writes_pacing_receipt_without_admission(self) -> None:
        source = (ROOT / contract.CHILD).read_text(encoding="utf-8")
        self.assertIn("pacing_receipt is not None", source)

    def test_child_uses_isolated_parent_bindings(self) -> None:
        child.validate_isolation()
        source = (ROOT / contract.CHILD).read_text(encoding="utf-8")
        self.assertNotIn(
            "retrieval_runtime.run_two_wave_retrieval =", source
        )



if __name__ == "__main__":
    unittest.main()
