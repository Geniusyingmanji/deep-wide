from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24895_control_binding_exact220_contract as parent  # noqa: E402
from deepwide_agent import v24905_revision_parser_total_exact220_contract as contract  # noqa: E402
from deepwide_agent import v24901_revision_parser_total_mapping_bundle as bundle  # noqa: E402
from deepwide_agent import v24902_revision_parser_total_child_runtime as child_runtime  # noqa: E402
from deepwide_agent import v24903_revision_parser_total_subprocess_gate as gate  # noqa: E402
from deepwide_agent.v24898_revision_parser_total_integration import (  # noqa: E402
    RESULT_ROLE,
    validate_integration_receipt,
)
from deepwide_agent.v24899_revision_parser_total_exact_task import validate_envelope  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import control_v24905_revision_parser_total_exact220 as control  # noqa: E402
from scripts import finalize_v24905_revision_parser_total_exact220 as finalizer  # noqa: E402
from scripts import run_v24905_revision_parser_total_exact220 as runner  # noqa: E402
from scripts import run_v24905_revision_parser_total_exact220_task as child  # noqa: E402


class V24905RevisionParserTotalExact220Tests(unittest.TestCase):
    def test_algorithm_and_resource_values_are_unchanged(self) -> None:
        self.assertEqual(contract.LIMITS, parent.LIMITS)
        self.assertEqual(contract.MODEL, parent.MODEL)
        self.assertEqual(contract.SEARCH, parent.SEARCH)
        self.assertEqual(contract.TWO_WAVE_POLICY, parent.TWO_WAVE_POLICY)
        self.assertEqual((contract.EXECUTOR_CONCURRENCY, contract.MODEL_SLOT_CAP), (20, 8))

    def test_surfaces_are_fresh(self) -> None:
        self.assertNotEqual(contract.PROTOCOL, parent.PROTOCOL)
        self.assertNotEqual(contract.OUTPUT_ROOT, parent.OUTPUT_ROOT)

    def test_task_vector_is_complete_and_label_blind(self) -> None:
        tasks = contract.task_vector(ROOT)
        self.assertEqual(len(tasks), 220)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))

    def test_reliability_gate_is_strict_go(self) -> None:
        value = contract.validate_reliability_gate(ROOT)
        self.assertEqual(value["valid_bundles"], 20)
        self.assertEqual(value["hard_timeouts"], 0)

    def test_policy_binds_parser_totality_and_collector_fix(self) -> None:
        policy = contract.coverage_policy()
        self.assertTrue(policy["parent_valid_revision_parser_mismatch_identity_passthrough"])
        self.assertTrue(policy["collector_exact_task_envelope_binding_corrected"])
        self.assertFalse(policy["parser_mismatch_third_model_slot_admitted"])

    def test_child_uses_parser_total_runtime(self) -> None:
        child.configure()
        self.assertIs(child.base.contract, contract)
        self.assertIs(child.base.run_child_bundle, child_runtime.run_child_bundle)

    def test_runner_uses_fresh_contract_and_roles(self) -> None:
        runner.configure()
        self.assertIs(runner.base.contract, contract)
        self.assertEqual(
            runner.base.FORWARD_ROLE,
            "v24905_revision_parser_total_exact220_forward_result",
        )

    def test_runner_binds_exact_envelope_receipt_and_result_role(self) -> None:
        runner.configure()
        self.assertIs(runner.base.validate_envelope, validate_envelope)
        self.assertIs(
            runner.base.validate_integration_receipt,
            validate_integration_receipt,
        )
        self.assertEqual(runner.base.COVERAGE_RESULT_ROLE, RESULT_ROLE)

    def test_runner_binds_parser_total_bundle(self) -> None:
        runner.configure()
        self.assertIs(runner.base.validate_bundle, bundle.validate_bundle)
        self.assertIs(
            runner.base.validate_effect_receipt, bundle.validate_effect_receipt
        )

    def test_runner_binds_parser_total_subprocess_gate(self) -> None:
        runner.configure()
        self.assertIs(
            runner.base.run_observed_bundle_subprocess,
            gate.run_observed_bundle_subprocess,
        )

    def test_collector_helpers_are_isolated_with_new_validators(self) -> None:
        runner.configure()
        for function in (
            runner.base._validate_scheduler_result,
            runner.base._coverage_totals,
            runner.base._effect_totals,
        ):
            self.assertIs(function.__globals__["contract"], contract)
            self.assertIs(function.__globals__["validate_envelope"], validate_envelope)
            self.assertIs(
                function.__globals__["validate_integration_receipt"],
                validate_integration_receipt,
            )
            self.assertEqual(function.__globals__["COVERAGE_RESULT_ROLE"], RESULT_ROLE)

    def test_runner_environment_is_keyless(self) -> None:
        runner.configure()
        environment = runner.base._child_env()
        self.assertNotIn("TAVILY_API_KEY", environment)
        self.assertNotIn("TAVILY_API_KEYS", environment)

    def test_control_includes_parser_total_regressions(self) -> None:
        control.configure()
        names = [
            path.name
            for path, _count, _timeout in control.base.base.base.TEST_SUITES
        ]
        self.assertIn("test_v24897_revision_parser_totality.py", names)
        self.assertIn("test_v24898_revision_parser_total_integration.py", names)
        self.assertIn("test_v24903_revision_parser_total_production_seam.py", names)

    def test_finalizer_uses_fresh_surface_and_control(self) -> None:
        finalizer.configure()
        self.assertIs(finalizer.parent.contract, contract)
        self.assertTrue(
            str(finalizer.parent.base.EVALUATOR_ROOT).startswith(
                str(contract.OUTPUT_ROOT)
            )
        )
        self.assertIn(str(contract.FINALIZER), finalizer.parent.base.CONTROL_FILES)

    def test_runtime_sources_are_label_blind_and_evaluator_free(self) -> None:
        for relative in (*contract.CORRECTED_SOURCES, contract.RUNNER, contract.CHILD):
            path = (ROOT / relative).resolve()
            with self.subTest(relative=str(relative)):
                self.assertEqual(semantic_audit._accesses(path, ROOT), [])
                self.assertEqual(semantic_audit._evaluator_capabilities(path, ROOT), [])


if __name__ == "__main__":
    unittest.main()
