from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24831_keyless_exact220_contract as parent  # noqa: E402
from deepwide_agent import v24877_keyless_coverage_exact220_contract as contract  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import control_v24877_keyless_coverage_exact220 as control  # noqa: E402
from scripts import finalize_v24877_keyless_coverage_exact220 as finalizer  # noqa: E402
from scripts import run_v24877_keyless_coverage_exact220 as runner  # noqa: E402
from scripts import run_v24877_keyless_coverage_exact220_task as child  # noqa: E402


class V24877KeylessCoverageExact220Tests(unittest.TestCase):
    def test_parent_budgets_and_keyless_transport_are_equal(self) -> None:
        self.assertEqual(contract.LIMITS, parent.LIMITS)
        self.assertEqual(contract.MODEL, parent.MODEL)
        self.assertEqual(contract.SEARCH, parent.SEARCH)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 8)

    def test_fixed_full_budget_control_is_no_entropy(self) -> None:
        policy = contract.TWO_WAVE_POLICY
        self.assertEqual(policy["information_gain_weight"], 0.0)
        self.assertEqual(policy["latency_loss_per_second"], 0.0)
        self.assertEqual(policy["minimum_net_value"], -1.0)
        self.assertEqual(policy["wave1_queries"] + policy["wave2_queries"], 4)
        self.assertEqual(policy["wave1_fetches"] + policy["wave2_fetches"], 10)

    def test_visible_vector_is_exact220_and_label_blind(self) -> None:
        tasks = contract.task_vector(ROOT)
        self.assertEqual(len(tasks), 220)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))

    def test_coverage_policy_is_source_gated_and_entropy_shadow_only(self) -> None:
        policy = contract.coverage_policy()
        self.assertEqual(policy["unknown_fill_minimum_independent_sources"], 2)
        self.assertEqual(policy["known_override_minimum_independent_sources"], 3)
        self.assertFalse(policy["logical_query_count_equal_http_response_count_required"])
        self.assertFalse(policy["actual_fetch_count_equal_fetch_cap_required"])
        self.assertFalse(policy["entropy_or_information_gain_used_for_admission_or_routing"])
        self.assertTrue(policy["entropy_or_information_gain_shadow_measurement_only"])

    def test_surfaces_are_fresh(self) -> None:
        self.assertNotEqual(contract.PROTOCOL, parent.PROTOCOL)
        self.assertNotEqual(contract.OUTPUT_ROOT, parent.OUTPUT_ROOT)
        self.assertNotEqual(contract.RUNNER_MARKER, parent.RUNNER_MARKER)
        self.assertNotEqual(contract.CHILD_MARKER, parent.CHILD_MARKER)

    def test_child_builds_real_keyless_bounded_runtime(self) -> None:
        source = (ROOT / contract.CHILD).read_text(encoding="utf-8")
        self.assertIn("run_child_bundle", source)
        self.assertIn("ThinSameResponseCitationTitleBackfillSearchClient", source)
        self.assertIn("DeadlineAwareGlobalModelSlotLimiter", source)
        self.assertNotIn("TAVILY_API", source)

    def test_runner_uses_response_aware_bundle_gate(self) -> None:
        source = (ROOT / contract.RUNNER).read_text(encoding="utf-8")
        self.assertIn("run_observed_bundle_subprocess", source)
        self.assertIn("validate_effect_receipt", source)
        self.assertNotIn("_read_credentials", source)

    def test_control_audits_all_runtime_surfaces(self) -> None:
        original = (
            control.base.contract,
            control.base.RUNTIME_SOURCES,
            control.base.TEST_SUITES,
            control.base.EXPECTED_TESTS,
        )
        try:
            control.configure()
            for path in contract.SEAM_SOURCES:
                self.assertIn(path, control.base.RUNTIME_SOURCES)
            fields, evaluator, secrets = control.base._runtime_findings()
            self.assertEqual((fields, evaluator, secrets), ([], [], []))
        finally:
            (
                control.base.contract,
                control.base.RUNTIME_SOURCES,
                control.base.TEST_SUITES,
                control.base.EXPECTED_TESTS,
            ) = original

    def test_forward_sources_have_no_evaluator_capability(self) -> None:
        for relative in (contract.RUNNER, contract.CHILD, *contract.SEAM_SOURCES):
            path = ROOT / relative
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
            self.assertFalse(any("evaluator" in name or "finalize" in name for name in imports))
            self.assertEqual(semantic_audit._accesses(path.resolve(), ROOT), [])

    def test_runner_and_child_modules_import(self) -> None:
        self.assertEqual(runner.PREAUDIT_ROLE, control.PREAUDIT_ROLE)
        self.assertTrue(callable(child.main))

    def test_finalizer_uses_fresh_complete_evaluator_surface(self) -> None:
        original = finalizer.base.contract
        try:
            finalizer.configure()
            self.assertIs(finalizer.base.contract, contract)
            self.assertTrue(str(finalizer.base.EVALUATOR_ROOT).startswith(str(contract.OUTPUT_ROOT)))
            self.assertIn("v24857", finalizer.base.REFERENCES)
        finally:
            finalizer.base.contract = original


if __name__ == "__main__":
    unittest.main()
