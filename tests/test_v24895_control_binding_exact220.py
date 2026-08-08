from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24894_revision_envelope_exact220_contract as parent  # noqa: E402
from deepwide_agent import v24895_control_binding_exact220_contract as contract  # noqa: E402
from deepwide_agent import v24890_revision_envelope_mapping_bundle as bundle  # noqa: E402
from deepwide_agent import v24891_revision_envelope_child_runtime as child_runtime  # noqa: E402
from deepwide_agent import v24892_revision_envelope_subprocess_gate as gate  # noqa: E402
from scripts import control_v24895_control_binding_exact220 as control  # noqa: E402
from scripts import finalize_v24895_control_binding_exact220 as finalizer  # noqa: E402
from scripts import run_v24895_control_binding_exact220 as runner  # noqa: E402
from scripts import run_v24895_control_binding_exact220_task as child  # noqa: E402


class V24895ControlBindingExact220Tests(unittest.TestCase):
    def test_algorithm_values_are_unchanged(self) -> None:
        self.assertEqual(contract.LIMITS, parent.LIMITS)
        self.assertEqual(contract.MODEL, parent.MODEL)
        self.assertEqual(contract.SEARCH, parent.SEARCH)
        self.assertEqual(contract.TWO_WAVE_POLICY, parent.TWO_WAVE_POLICY)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 8)

    def test_surfaces_are_fresh(self) -> None:
        self.assertNotEqual(contract.PROTOCOL, parent.PROTOCOL)
        self.assertNotEqual(contract.OUTPUT_ROOT, parent.OUTPUT_ROOT)

    def test_invalid_parent_audit_is_bound(self) -> None:
        value = json.loads((ROOT / contract.V24894_INVALID_AUDIT).read_text())
        self.assertEqual(value["role"], "v24884_mapping_recovery_exact220_preactivation_audit")
        self.assertTrue(value["audit_valid"])

    def test_task_vector_is_exact220_label_blind(self) -> None:
        tasks = contract.task_vector(ROOT)
        self.assertEqual(len(tasks), 220)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))

    def test_reliability_gate_remains_strict_go(self) -> None:
        self.assertEqual(contract.validate_reliability_gate(ROOT)["valid_bundles"], 20)

    def test_child_uses_fresh_contract_and_fixed_runtime(self) -> None:
        child.configure()
        self.assertIs(child.base.contract, contract)
        self.assertIs(child.base.run_child_bundle, child_runtime.run_child_bundle)

    def test_runner_uses_fresh_contract(self) -> None:
        runner.configure()
        self.assertIs(runner.base.contract, contract)
        self.assertEqual(runner.base.FORWARD_ROLE, "v24895_control_binding_exact220_forward_result")

    def test_runner_binds_fixed_bundle(self) -> None:
        runner.configure()
        self.assertIs(runner.base.validate_bundle, bundle.validate_bundle)
        self.assertIs(runner.base.validate_effect_receipt, bundle.validate_effect_receipt)

    def test_runner_binds_fixed_gate(self) -> None:
        runner.configure()
        self.assertIs(runner.base.run_observed_bundle_subprocess, gate.run_observed_bundle_subprocess)

    def test_runner_environment_is_keyless(self) -> None:
        runner.configure()
        environment = runner.base._child_env()
        self.assertNotIn("TAVILY_API_KEY", environment)
        self.assertNotIn("TAVILY_API_KEYS", environment)

    def test_control_roles_are_fresh(self) -> None:
        control.configure()
        self.assertEqual(control.base.PREAUDIT_ROLE, "v24895_control_binding_exact220_preactivation_audit")
        self.assertEqual(control.base.START_ROLE, "v24895_control_binding_exact220_execution_start")

    def test_control_tests_include_envelope_regressions(self) -> None:
        control.configure()
        names = [p.name for p, _n, _t in control.base.base.TEST_SUITES]
        self.assertIn("test_v24886_revision_envelope_passthrough.py", names)
        self.assertIn("test_v24890_revision_envelope_mapping_bundle.py", names)

    def test_finalizer_uses_fresh_surface(self) -> None:
        finalizer.configure()
        self.assertIs(finalizer.parent.contract, contract)
        self.assertTrue(str(finalizer.parent.base.EVALUATOR_ROOT).startswith(str(contract.OUTPUT_ROOT)))

    def test_entropy_information_gain_remain_shadow_only(self) -> None:
        policy = contract.coverage_policy()
        self.assertFalse(policy["entropy_or_information_gain_used_for_admission_or_routing"])
        self.assertTrue(policy["entropy_or_information_gain_shadow_measurement_only"])

    def test_single_change_is_control_only(self) -> None:
        self.assertIn("control_binding_corrected", contract._patch(ROOT, parent._read(ROOT / parent.PROTOCOL))["execution"])


if __name__ == "__main__":
    unittest.main()
