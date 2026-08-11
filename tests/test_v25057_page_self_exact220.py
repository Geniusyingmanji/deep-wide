from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25056_page_self_exact220_contract as predecessor  # noqa: E402
from deepwide_agent import v25057_page_self_exact220_contract as contract  # noqa: E402
from scripts import control_v25057_page_self_exact220 as control  # noqa: E402
from scripts import finalize_v25057_page_self_exact220 as finalizer  # noqa: E402
from scripts import run_v25057_page_self_exact220 as runner  # noqa: E402


class PageSelfExact220R2Tests(unittest.TestCase):
    def test_predecessor_failed_before_any_effect_and_is_not_reused(self) -> None:
        disposition = contract._predecessor_disposition(ROOT)
        self.assertEqual(
            disposition["failure_stage"],
            "preactivation_focused_test_validation_before_publication",
        )
        self.assertEqual(disposition["observed_tests"], 64)
        self.assertEqual(disposition["stage_unstable_test_errors"], 2)
        self.assertFalse(
            disposition["network_model_search_fetch_evaluator_or_api_called"]
        )
        self.assertTrue(disposition["all_effect_surfaces_absent"])
        self.assertFalse(disposition["old_protocol_or_output_reused_by_r2"])

    def test_r2_paths_and_roles_are_disjoint_from_predecessor(self) -> None:
        for current, old in (
            (contract.PROTOCOL, predecessor.PROTOCOL),
            (contract.PREAUDIT, predecessor.PREAUDIT),
            (contract.EXECUTION_START, predecessor.EXECUTION_START),
            (contract.OUTPUT_ROOT, predecessor.OUTPUT_ROOT),
            (contract.FORWARD_RESULT, predecessor.FORWARD_RESULT),
            (contract.RESULT, predecessor.RESULT),
        ):
            self.assertNotEqual(current, old)
        self.assertNotEqual(contract.PROTOCOL_ID, predecessor.PROTOCOL_ID)
        self.assertNotEqual(contract.START_ROLE, predecessor.START_ROLE)

    def test_protocol_is_stage_stable_and_binds_predecessor_disposition(self) -> None:
        value = contract.build_protocol(
            ROOT,
            now=1,
            tracked=False,
            require_clean=False,
            require_pristine=False,
        )
        self.assertEqual(
            contract.validate_protocol(ROOT, value, tracked=False), value
        )
        self.assertEqual(
            value["predecessor_disposition"],
            contract._predecessor_disposition(ROOT),
        )
        self.assertTrue(
            value["treatment_scope"][
                "v25056_preactivation_failed_before_any_effect"
            ]
        )
        self.assertFalse(
            value["treatment_scope"]["v25056_protocol_or_outputs_reused"]
        )

    def test_resealed_predecessor_disposition_tamper_fails(self) -> None:
        value = contract.build_protocol(
            ROOT,
            now=1,
            tracked=False,
            require_clean=False,
            require_pristine=False,
        )
        changed = copy.deepcopy(value)
        changed["predecessor_disposition"][
            "network_model_search_fetch_evaluator_or_api_called"
        ] = True
        changed.pop("protocol_payload_sha256")
        changed["protocol_payload_sha256"] = contract.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            contract.validate_protocol(ROOT, changed, tracked=False)

    def test_wrappers_configure_only_fresh_contract_and_namespaces(self) -> None:
        fields = (
            (runner.parent, "contract"),
            (runner.parent.parent, "contract"),
            (runner.parent.parent, "runtime"),
            (runner.parent.parent, "RobustLatePageBoundSearchClient"),
            (runner.parent.parent, "validate_search_class"),
            (runner.parent.parent, "_validate_start"),
            (runner.parent.parent, "_prepare_output"),
            (runner.parent.parent, "_aggregate"),
            (control.parent, "contract"),
            (control.parent, "TEST_SUITES"),
            (control.parent, "EXPECTED_TESTS"),
            (control.parent.parent, "contract"),
            (control.parent.parent, "TEST_SUITES"),
            (control.parent.parent, "EXPECTED_TESTS"),
            (control.parent.parent, "PREAUDIT_AUTH"),
            (control.parent.parent, "START_AUTH"),
            (control.parent.parent, "validate_preaudit"),
            (control.parent.parent, "validate_start"),
            (finalizer.parent, "contract"),
            (finalizer.parent, "EVALUATOR_ROOT"),
            (finalizer.parent.parent, "contract"),
        )
        saved = [(module, name, getattr(module, name)) for module, name in fields]
        try:
            runner.configure()
            self.assertIs(runner.parent.contract, contract)
            self.assertIs(runner.parent.parent.contract, contract)
            control.configure()
            self.assertIs(control.parent.contract, contract)
            self.assertIs(control.parent.parent.contract, contract)
            finalizer.configure()
            self.assertIs(finalizer.parent.contract, contract)
            self.assertIs(finalizer.parent.parent.contract, contract)
        finally:
            for module, name, value in reversed(saved):
                setattr(module, name, value)

    def test_exact220_resources_treatment_and_evaluation_remain_frozen(self) -> None:
        self.assertEqual(contract.task_vector(ROOT), predecessor.task_vector(ROOT))
        self.assertEqual(contract.LIMITS, predecessor.LIMITS)
        self.assertEqual(contract.MODEL, predecessor.MODEL)
        value = contract.build_protocol(
            ROOT,
            now=1,
            tracked=False,
            require_clean=False,
            require_pristine=False,
        )
        self.assertEqual(value["task_contract"]["selected_count"], 220)
        self.assertEqual(value["execution"]["executor_concurrency"], 20)
        self.assertEqual(value["execution"]["model_slot_cap"], 8)
        self.assertTrue(
            value["treatment_scope"][
                "sole_forward_treatment_is_v25055_page_self_fetch_projection"
            ]
        )
        self.assertTrue(
            value["mechanism_gate"][
                "postfreeze_evaluator_unconditional_on_mechanism_gate"
            ]
        )


if __name__ == "__main__":
    unittest.main()
