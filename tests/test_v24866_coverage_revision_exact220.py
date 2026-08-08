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

from deepwide_agent import v24857_pacing_aware_exact220_contract as parent  # noqa: E402
from deepwide_agent import v24866_coverage_revision_exact220_contract as contract  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import control_v24866_coverage_revision_exact220 as control  # noqa: E402
from scripts import finalize_v24866_coverage_revision_exact220 as finalizer  # noqa: E402
from scripts import run_v24866_coverage_revision_exact220 as runner  # noqa: E402
from scripts import run_v24866_coverage_revision_exact220_task as child  # noqa: E402


class V24866CoverageRevisionExact220Tests(unittest.TestCase):
    def test_all_parent_budgets_and_concurrency_are_equal(self) -> None:
        self.assertEqual(contract.LIMITS, parent.LIMITS)
        self.assertEqual(contract.MODEL, parent.MODEL)
        self.assertEqual(contract.SEARCH, parent.SEARCH)
        self.assertEqual(contract.TWO_WAVE_POLICY, parent.TWO_WAVE_POLICY)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 8)
        self.assertEqual(contract.TAVILY_KEY_SLOT_CAP, 12)

    def test_visible_vector_is_exact220_and_label_blind(self) -> None:
        tasks = contract.task_vector(ROOT)
        self.assertEqual(len(tasks), 220)
        self.assertTrue(
            all(set(task) == {"opaque_id", "question"} for task in tasks)
        )

    def test_coverage_policy_is_source_gated_and_entropy_shadow_only(self) -> None:
        policy = contract.coverage_policy()
        self.assertEqual(
            policy["unknown_fill_minimum_independent_sources"], 2
        )
        self.assertEqual(
            policy["known_override_minimum_independent_sources"], 3
        )
        self.assertFalse(
            policy["entropy_or_information_gain_used_for_admission_or_routing"]
        )
        self.assertTrue(
            policy["entropy_or_information_gain_shadow_measurement_only"]
        )

    def test_surfaces_are_fresh(self) -> None:
        self.assertNotEqual(contract.PROTOCOL, parent.PROTOCOL)
        self.assertNotEqual(contract.OUTPUT_ROOT, parent.OUTPUT_ROOT)
        self.assertNotEqual(contract.RUNNER_MARKER, parent.RUNNER_MARKER)
        self.assertNotEqual(contract.CHILD_MARKER, parent.CHILD_MARKER)

    def test_child_credentials_are_memory_only_and_required(self) -> None:
        source = (ROOT / contract.CHILD).read_text(encoding="utf-8")
        self.assertIn('os.environ.pop(_CREDENTIAL_ENVIRONMENT, "")', source)
        with mock.patch.dict(child.os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                child._credentials_from_environment()

    def test_runner_requires_exactly_twelve_credentials(self) -> None:
        with self.assertRaises(RuntimeError):
            runner._read_credentials(io.StringIO("one\n"))

    def test_control_audits_all_new_runtime_surfaces(self) -> None:
        original = (
            control.base.contract,
            control.base.RUNTIME_SOURCES,
            control.base.TEST_SUITES,
            control.base.EXPECTED_TESTS,
        )
        try:
            control.configure()
            for path in contract.COVERAGE_SOURCES:
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
        for path in (contract.RUNNER, contract.CHILD, *contract.COVERAGE_SOURCES):
            source = (ROOT / path).read_text(encoding="utf-8")
            tree = ast.parse(source)
            imports = []
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

    def test_child_builds_real_bounded_runtime(self) -> None:
        source = (ROOT / contract.CHILD).read_text(encoding="utf-8")
        self.assertIn("run_child_bundle", source)
        self.assertIn("RateAwareDeadlineTavilyThinCompatibilityClient", source)
        self.assertIn("DeadlineAwareGlobalModelSlotLimiter", source)

    def test_finalizer_uses_fresh_complete_evaluator_surface(self) -> None:
        finalizer.configure()
        self.assertIs(finalizer.base.contract, contract)
        self.assertTrue(
            str(finalizer.base.EVALUATOR_ROOT).startswith(
                str(contract.OUTPUT_ROOT)
            )
        )
        self.assertIn("v24857", finalizer.base.REFERENCES)


if __name__ == "__main__":
    unittest.main()
