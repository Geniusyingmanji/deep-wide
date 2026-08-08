from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24884_mapping_recovery_exact220_contract as parent  # noqa: E402
from deepwide_agent import v24890_revision_envelope_mapping_bundle as bundle  # noqa: E402
from deepwide_agent import v24891_revision_envelope_child_runtime as child_runtime  # noqa: E402
from deepwide_agent import v24892_revision_envelope_subprocess_gate as gate  # noqa: E402
from deepwide_agent import v24894_revision_envelope_exact220_contract as contract  # noqa: E402
from scripts import control_v24894_revision_envelope_exact220 as control  # noqa: E402
from scripts import finalize_v24894_revision_envelope_exact220 as finalizer  # noqa: E402
from scripts import run_v24894_revision_envelope_exact220 as runner  # noqa: E402
from scripts import run_v24894_revision_envelope_exact220_task as child  # noqa: E402


class V24894RevisionEnvelopeExact220Tests(unittest.TestCase):
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

    def test_task_vector_is_exact220_label_blind(self) -> None:
        tasks = contract.task_vector(ROOT)
        self.assertEqual(len(tasks), 220)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))

    def test_reliability_gate_is_strict_go(self) -> None:
        value = contract.validate_reliability_gate(ROOT)
        self.assertEqual(value["status"], "go")
        self.assertEqual(value["valid_bundles"], 20)
        self.assertEqual(value["hard_timeouts"], 0)

    def test_dependency_manifest_binds_gate_result_and_audit(self) -> None:
        manifest = contract.dependency_manifest(ROOT)
        self.assertIn(str(contract.V24893_RESULT), manifest)
        self.assertIn(str(contract.V24893_POSTAUDIT), manifest)

    def test_policy_binds_revision_envelope_runtime(self) -> None:
        policy = contract.coverage_policy()
        self.assertEqual(policy["bundle_policy_id"], bundle.POLICY_ID)
        self.assertEqual(policy["child_policy_id"], child_runtime.POLICY_ID)
        self.assertEqual(policy["subprocess_gate_policy_id"], gate.POLICY_ID)
        self.assertTrue(policy["over_envelope_parent_prediction_identity_passthrough"])

    def test_child_uses_static_successor_contract(self) -> None:
        child.configure()
        self.assertIs(child.base.contract, contract)

    def test_child_uses_revision_envelope_runtime(self) -> None:
        child.configure()
        self.assertIs(child.base.run_child_bundle, child_runtime.run_child_bundle)

    def test_runner_uses_static_successor_contract(self) -> None:
        runner.configure()
        self.assertIs(runner.parent.base.contract, contract)
        self.assertEqual(
            runner.parent.base.FORWARD_ROLE,
            "v24894_revision_envelope_exact220_forward_result",
        )

    def test_runner_binds_corrected_bundle_validators(self) -> None:
        runner.configure()
        self.assertIs(runner.parent.base.validate_bundle, bundle.validate_bundle)
        self.assertIs(
            runner.parent.base.validate_effect_receipt,
            bundle.validate_effect_receipt,
        )

    def test_runner_binds_corrected_subprocess_gate(self) -> None:
        runner.configure()
        self.assertIs(
            runner.parent.base.run_observed_bundle_subprocess,
            gate.run_observed_bundle_subprocess,
        )

    def test_runner_environment_is_keyless(self) -> None:
        runner.configure()
        environment = runner.parent.base._child_env()
        self.assertNotIn("TAVILY_API_KEY", environment)
        self.assertNotIn("TAVILY_API_KEYS", environment)

    def test_control_includes_revision_envelope_regressions(self) -> None:
        control.configure()
        names = [
            path.name
            for path, _expected, _timeout in control.parent.parent.base.TEST_SUITES
        ]
        self.assertIn("test_v24886_revision_envelope_passthrough.py", names)
        self.assertIn("test_v24890_revision_envelope_mapping_bundle.py", names)

    def test_finalizer_uses_fresh_surface(self) -> None:
        finalizer.configure()
        self.assertIs(finalizer.parent.parent.contract, contract)
        self.assertTrue(
            str(finalizer.parent.parent.base.EVALUATOR_ROOT).startswith(
                str(contract.OUTPUT_ROOT)
            )
        )

    def test_entropy_information_gain_remain_shadow_only(self) -> None:
        policy = contract.coverage_policy()
        self.assertFalse(policy["entropy_or_information_gain_used_for_admission_or_routing"])
        self.assertTrue(policy["entropy_or_information_gain_shadow_measurement_only"])


if __name__ == "__main__":
    unittest.main()
