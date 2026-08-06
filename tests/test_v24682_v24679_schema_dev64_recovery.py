from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import run_v24682_v24679_schema_dev64_recovery as wrapper  # noqa: E402
from scripts import v24682_v24679_schema_dev64_recovery_control as control  # noqa: E402


class V24682RecoveryTests(unittest.TestCase):
    def test_frozen_runner_has_exactly_one_unbound_global(self) -> None:
        self.assertEqual(
            control._module_unbound_globals(control.FROZEN_RUNNER),
            ["FORWARD_AUDIT"],
        )

    def test_wrapper_contract_is_exact_two_private_bindings(self) -> None:
        self.assertTrue(control._wrapper_contract())

    def test_wrapper_injects_before_calling_frozen_main(self) -> None:
        events: list[str] = []
        sentinel_audit = object()
        sentinel_start = object()

        def validate() -> None:
            events.append("validate")

        def run() -> None:
            events.append("run")
            self.assertIs(wrapper.frozen.FORWARD_AUDIT, sentinel_audit)
            self.assertIs(wrapper.frozen.EXECUTION_START, sentinel_start)

        old_audit = getattr(wrapper.frozen, "FORWARD_AUDIT", None)
        old_start = wrapper.frozen.EXECUTION_START
        try:
            with (
                patch.object(wrapper.recovery, "validate_execution_start", side_effect=validate),
                patch.object(wrapper.contract, "FORWARD_AUDIT", sentinel_audit),
                patch.object(wrapper.recovery, "EXECUTION_START", sentinel_start),
                patch.object(wrapper.frozen, "main", side_effect=run),
            ):
                wrapper.main()
        finally:
            if old_audit is None and hasattr(wrapper.frozen, "FORWARD_AUDIT"):
                delattr(wrapper.frozen, "FORWARD_AUDIT")
            else:
                wrapper.frozen.FORWARD_AUDIT = old_audit
            wrapper.frozen.EXECUTION_START = old_start
        self.assertEqual(events, ["validate", "run"])

    def test_wrapper_validation_failure_prevents_frozen_main(self) -> None:
        with (
            patch.object(
                wrapper.recovery,
                "validate_execution_start",
                side_effect=RuntimeError("synthetic"),
            ),
            patch.object(wrapper.frozen, "main") as run,
        ):
            with self.assertRaises(RuntimeError):
                wrapper.main()
        run.assert_not_called()

    def test_recovery_build_authorizes_activation_only(self) -> None:
        value = {
            "role": "v24682_v24679_recovery_build_audit",
            "audit_valid": True,
            "findings": [],
            "parent": {"old_execution_start_reusable": False},
            "recovery": {
                "unbound_frozen_runner_globals": ["FORWARD_AUDIT"],
                "wrapper_contract_valid": True,
                "task_budget_model_search_fetch_parser_or_child_changed": False,
            },
            "tests": {"passed": True, "test_count": control.EXPECTED_TEST_COUNT},
            "runtime_state": {
                "shared_api_lease_active": False,
                "v24679_or_recovery_process_active": False,
                "future_surface_pristine": True,
            },
            "authorization": {
                "recovery_activation_design": True,
                "recovery_launch": False,
                "old_execution_start_reuse": False,
                "evaluator": False,
                "exact220": False,
            },
        }
        value["audit_payload_sha256"] = control.contract.payload_sha256(value)
        control.validate_audit(value)

    def test_resealed_old_start_reuse_fails_closed(self) -> None:
        value = {
            "role": "v24682_v24679_recovery_build_audit",
            "audit_valid": True,
            "findings": [],
            "parent": {"old_execution_start_reusable": False},
            "recovery": {
                "unbound_frozen_runner_globals": ["FORWARD_AUDIT"],
                "wrapper_contract_valid": True,
                "task_budget_model_search_fetch_parser_or_child_changed": False,
            },
            "tests": {"passed": True, "test_count": control.EXPECTED_TEST_COUNT},
            "runtime_state": {
                "shared_api_lease_active": False,
                "v24679_or_recovery_process_active": False,
                "future_surface_pristine": True,
            },
            "authorization": {
                "recovery_activation_design": True,
                "recovery_launch": False,
                "old_execution_start_reuse": True,
                "evaluator": False,
                "exact220": False,
            },
        }
        value["audit_payload_sha256"] = control.contract.payload_sha256(value)
        with self.assertRaises(RuntimeError):
            control.validate_audit(value)

    def test_recovery_start_uses_compatibility_role_but_successor_identity(self) -> None:
        source = (ROOT / control.CONTROL).read_text(encoding="utf-8")
        tree = ast.parse(source)
        literals = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        self.assertIn("v24679_schema_dev64_execution_start", literals)
        self.assertIn("v24682_v24679_recovery_execution_start", literals)

    def test_secret_pattern_detects_supported_prefix_without_literal(self) -> None:
        prefix = "github" + "_pat_"
        self.assertIsNotNone(control.SECRET.search(prefix + "a" * 20))
        self.assertIsNone(control.SECRET.search("ordinary-placeholder"))


if __name__ == "__main__":
    unittest.main()
