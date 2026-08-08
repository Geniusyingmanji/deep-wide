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

from deepwide_agent import v24850_v24800_replication_exact220_contract as parent  # noqa: E402
from deepwide_agent import v24854_rate_aware_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24852_rate_aware_tavily_search import (  # noqa: E402
    RateAwareDeadlineTavilyThinCompatibilityClient,
)
from scripts import control_v24854_rate_aware_exact220 as control  # noqa: E402
from scripts import finalize_v24854_rate_aware_exact220 as finalizer  # noqa: E402
from scripts import run_v24800_exact220 as parent_runner  # noqa: E402
from scripts import run_v24854_rate_aware_exact220 as runner  # noqa: E402
from scripts import run_v24854_rate_aware_exact220_task as child  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402


class V24854RateAwareExact220Tests(unittest.TestCase):
    def test_parent_algorithm_budget_and_policy_are_equal(self) -> None:
        self.assertEqual(contract.LIMITS, parent.LIMITS)
        self.assertEqual(contract.MODEL, parent.MODEL)
        self.assertEqual(contract.SEARCH, parent.SEARCH)
        self.assertEqual(contract.TWO_WAVE_POLICY, parent.TWO_WAVE_POLICY)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 8)
        self.assertEqual(contract.TAVILY_KEY_SLOT_CAP, 12)

    def test_only_declared_algorithm_change_is_rate_transport(self) -> None:
        policy = contract.rate_policy()
        self.assertEqual(
            policy["transport_class"],
            "RateAwareDeadlineTavilyThinCompatibilityClient",
        )
        self.assertEqual(
            policy[
                "provider_non_key_local_attempt_cap_per_logical_query"
            ],
            2,
        )
        self.assertFalse(
            policy["provider_wide_429_rotates_all_keys_immediately"]
        )

    def test_neutral_transport_gate_is_live_valid(self) -> None:
        gate = contract.validate_transport_gate(ROOT)
        self.assertEqual(gate["successful_query_rows"], 4)
        self.assertEqual(gate["failed_query_rows"], 0)
        self.assertFalse(
            gate["provider_wide_429_rotates_all_keys_immediately"]
        )

    def test_visible_vector_is_exact220_and_label_blind(self) -> None:
        tasks = contract.task_vector(ROOT)
        self.assertEqual(len(tasks), 220)
        self.assertTrue(
            all(set(task) == {"opaque_id", "question"} for task in tasks)
        )

    def test_surfaces_are_fresh(self) -> None:
        self.assertNotEqual(contract.PROTOCOL, parent.PROTOCOL)
        self.assertNotEqual(contract.OUTPUT_ROOT, parent.OUTPUT_ROOT)
        self.assertNotEqual(contract.RUNNER_MARKER, parent.RUNNER_MARKER)
        self.assertNotEqual(contract.CHILD_MARKER, parent.CHILD_MARKER)

    def test_child_uses_rate_aware_class_and_ephemeral_credentials(self) -> None:
        source = (ROOT / contract.CHILD).read_text(encoding="utf-8")
        self.assertIn("RateAwareDeadlineTavilyThinCompatibilityClient", source)
        self.assertIn('os.environ.pop(_CREDENTIAL_ENVIRONMENT, "")', source)
        self.assertIsNotNone(RateAwareDeadlineTavilyThinCompatibilityClient)

    def test_runner_rebinds_transport_and_contract(self) -> None:
        original_contract = parent_runner.contract
        original_prepare = parent_runner.prepare_key_slots
        try:
            runner.configure()
            self.assertIs(parent_runner.contract, contract)
            self.assertEqual(
                parent_runner.prepare_key_slots.__name__,
                "prepare_rate_aware_key_slots",
            )
        finally:
            parent_runner.contract = original_contract
            parent_runner.prepare_key_slots = original_prepare

    def test_control_audits_new_runtime_and_expected_tests(self) -> None:
        original = (
            control.base.contract,
            control.base.RUNTIME_SOURCES,
            control.base.TEST_SUITES,
            control.base.EXPECTED_TESTS,
        )
        try:
            control.configure()
            self.assertEqual(control.base.EXPECTED_TESTS, 82)
            self.assertIn(contract.TRANSPORT_SOURCE, control.base.RUNTIME_SOURCES)
            fields, evaluator, secrets = control.base._runtime_findings()
            self.assertEqual((fields, evaluator, secrets), ([], [], []))
        finally:
            (
                control.base.contract,
                control.base.RUNTIME_SOURCES,
                control.base.TEST_SUITES,
                control.base.EXPECTED_TESTS,
            ) = original

    def test_finalizer_uses_fresh_complete_evaluator_surface(self) -> None:
        finalizer.configure()
        self.assertIs(finalizer.base.contract, contract)
        self.assertTrue(
            str(finalizer.base.EVALUATOR_ROOT).startswith(
                str(contract.OUTPUT_ROOT)
            )
        )
        self.assertIn("v24850", finalizer.base.REFERENCES)

    def test_runtime_sources_have_no_evaluator_import(self) -> None:
        for path in (contract.RUNNER, contract.CHILD):
            source = (ROOT / path).read_text(encoding="utf-8")
            tree = ast.parse(source)
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
            self.assertFalse(
                any("evaluator" in name or "finalize" in name for name in imports)
            )
            self.assertEqual(
                semantic_audit._accesses((ROOT / path).resolve(), ROOT), []
            )

    def test_child_rejects_missing_credential_pool_before_effect(self) -> None:
        with mock.patch.dict(child.os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                child._credentials_from_environment()


if __name__ == "__main__":
    unittest.main()
