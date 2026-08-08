from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24877_keyless_coverage_exact220_contract as parent  # noqa: E402
from deepwide_agent import v24878_keyless_coverage_exact220_contract as contract  # noqa: E402
from scripts import control_v24878_keyless_coverage_exact220 as control  # noqa: E402
from scripts import finalize_v24878_keyless_coverage_exact220 as finalizer  # noqa: E402
from scripts import run_v24878_keyless_coverage_exact220 as runner  # noqa: E402
from scripts import run_v24878_keyless_coverage_exact220_task as child  # noqa: E402


class V24878KeylessCoverageExact220Tests(unittest.TestCase):
    def test_all_algorithm_budgets_are_unchanged(self) -> None:
        self.assertEqual(contract.LIMITS, parent.LIMITS)
        self.assertEqual(contract.MODEL, parent.MODEL)
        self.assertEqual(contract.SEARCH, parent.SEARCH)
        self.assertEqual(contract.TWO_WAVE_POLICY, parent.TWO_WAVE_POLICY)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 8)

    def test_all_surfaces_are_fresh(self) -> None:
        self.assertNotEqual(contract.PROTOCOL, parent.PROTOCOL)
        self.assertNotEqual(contract.OUTPUT_ROOT, parent.OUTPUT_ROOT)
        self.assertNotEqual(contract.RUNNER_MARKER, parent.RUNNER_MARKER)
        self.assertNotEqual(contract.CHILD_MARKER, parent.CHILD_MARKER)

    def test_v24877_failure_is_bound(self) -> None:
        self.assertTrue((ROOT / contract.LAUNCH_FAILURE).is_file())

    def test_child_uses_static_successor_contract(self) -> None:
        self.assertIs(child.contract, contract)
        source = (ROOT / contract.CHILD).read_text(encoding="utf-8")
        self.assertIn("base.contract = contract", source)

    def test_runner_uses_static_successor_contract(self) -> None:
        runner.configure()
        self.assertIs(runner.base.contract, contract)
        self.assertEqual(runner.base.FORWARD_ROLE, "v24878_keyless_coverage_exact220_forward_result")

    def test_runner_child_environment_is_concrete(self) -> None:
        runner.configure()
        self.assertIsInstance(runner.base._child_env(), dict)
        self.assertNotIn("TAVILY_API_KEYS", runner.base._child_env())

    def test_task_vector_remains_exact220_label_blind(self) -> None:
        tasks = contract.task_vector(ROOT)
        self.assertEqual(len(tasks), 220)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))

    def test_control_includes_runner_fix_regression(self) -> None:
        control.configure()
        names = [path.name for path, _expected, _timeout in control.parent.base.TEST_SUITES]
        self.assertIn("test_v24878_keyless_coverage_runner_fix.py", names)

    def test_finalizer_uses_fresh_surface(self) -> None:
        finalizer.configure()
        self.assertIs(finalizer.parent.base.contract, contract)
        self.assertTrue(str(finalizer.parent.base.EVALUATOR_ROOT).startswith(str(contract.OUTPUT_ROOT)))

    def test_entropy_information_gain_remain_shadow_only(self) -> None:
        policy = contract.coverage_policy()
        self.assertFalse(policy["entropy_or_information_gain_used_for_admission_or_routing"])
        self.assertTrue(policy["entropy_or_information_gain_shadow_measurement_only"])


if __name__ == "__main__":
    unittest.main()
