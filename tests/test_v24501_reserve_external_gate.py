from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import v24501_reserve_external_gate as target  # noqa: E402


def reseal(value: dict, field: str) -> None:
    value.pop(field, None)
    value[field] = payload_sha256(value)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _cli_validator_smoke(command: str) -> int:
    protocol = target.build_protocol(now=0, require_pristine=False)

    def validate_in_process(args: argparse.Namespace) -> None:
        base = target.predecessor.predecessor.base
        validated = base.validate_protocol(ROOT, value=protocol)
        if (
            validated.get("protocol_id") != target.PROTOCOL_ID
            or validated.get("validator_binding_successor")
            != target._validator_binding()
            or validated.get("preaudit_builder_ordering_successor")
            != target._ordering_binding()
            or base.RUNNER_MARKER != target.RUNNER_MARKER
            or base.run_targeted_worker
            is not target.predecessor.predecessor.run_reserve_worker
        ):
            raise RuntimeError("V2.45.01 CLI validator context is incomplete")
        print(
            json.dumps(
                {
                    "command": args.command,
                    "protocol_id": validated["protocol_id"],
                    "validator_context_passed": True,
                    "network_model_search_fetch_or_evaluator_called": False,
                },
                sort_keys=True,
            )
        )

    base = target.predecessor.predecessor.base
    original_worker = base._worker
    original_supervisor = base._supervisor
    original_argv = sys.argv
    try:
        base._worker = validate_in_process
        base._supervisor = validate_in_process
        sys.argv = [str(ROOT / target.RUNNER_MARKER), command]
        target.main()
    finally:
        sys.argv = original_argv
        base._worker = original_worker
        base._supervisor = original_supervisor
    return 0


class V24501ReserveExternalGateTests(unittest.TestCase):
    def test_predecessor_invalidation_is_sealed_and_population_is_unconsumed(self) -> None:
        value = target.validate_invalidation()
        self.assertEqual(value["local_preaudit_build_attempts"], 2)
        self.assertFalse(value["preaudit_created"])
        self.assertFalse(value["activation_created"])
        self.assertFalse(value["execution_start_created"])
        self.assertFalse(value["external_probe_launched"])
        self.assertFalse(value["network_model_search_fetch_or_evaluator_called"])
        self.assertFalse(value["same_population_consumed"])

    def test_successor_changes_only_protocol_identity_and_ordering_binding(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        predecessor_protocol = target.predecessor._read(target.predecessor.PROTOCOL)
        for field in (
            "task_contract",
            "reserve_binding",
            "mechanism",
            "budget",
            "gates",
            "validator_binding_successor",
        ):
            self.assertEqual(value[field], predecessor_protocol[field], field)
        ordering = value["preaudit_builder_ordering_successor"]
        self.assertTrue(ordering["same_unconsumed_population_reused"])
        self.assertTrue(
            ordering[
                "population_mechanism_budget_gates_and_source_selection_unchanged"
            ]
        )
        self.assertTrue(
            ordering["v24500_parent_supervisor_worker_validator_binding_preserved"]
        )
        self.assertFalse(
            ordering["additional_network_model_search_fetch_or_evaluator_effect"]
        )
        self.assertFalse(value["authorization"]["external_probe_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])

    def test_resealed_ordering_binding_tamper_fails_closed(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        cases = (
            ("same_unconsumed_population_reused", False),
            (
                "population_mechanism_budget_gates_and_source_selection_unchanged",
                False,
            ),
            (
                "v24500_parent_supervisor_worker_validator_binding_preserved",
                False,
            ),
            ("core_preaudit_validated_before_successor_bindings_attached", False),
            ("additional_network_model_search_fetch_or_evaluator_effect", True),
        )
        for field, replacement in cases:
            changed = copy.deepcopy(value)
            changed["preaudit_builder_ordering_successor"][field] = replacement
            reseal(changed, "protocol_payload_sha256")
            with self.assertRaises(RuntimeError, msg=field):
                target.validate_protocol(value=changed)

    def test_configured_predecessor_restores_configuration_and_validators(self) -> None:
        names = (
            "PROTOCOL_ID",
            "PROTOCOL",
            "RUNNER_MARKER",
            "_patched_core",
            "validate_protocol",
            "validate_preaudit",
            "validate_activation",
            "validate_execution_start",
        )
        originals = {name: getattr(target.predecessor, name) for name in names}
        with target.configured_predecessor(validators=True):
            self.assertEqual(target.predecessor.PROTOCOL_ID, target.PROTOCOL_ID)
            self.assertIs(target.predecessor.validate_protocol, target.validate_protocol)
            self.assertIs(target.predecessor.validate_preaudit, target.validate_preaudit)
            with target.predecessor.configured_predecessor(validators=True):
                module = target.predecessor.predecessor
                self.assertEqual(module.PROTOCOL_ID, target.PROTOCOL_ID)
                self.assertIs(module.validate_protocol, target.validate_protocol)
                self.assertIs(module.validate_preaudit, target.validate_preaudit)
        for name, value in originals.items():
            self.assertIs(getattr(target.predecessor, name), value, name)

    def test_frozen_protocol_builds_complete_preaudit_activation_and_start(self) -> None:
        base = target.predecessor.predecessor.base
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            root = Path(temporary).relative_to(ROOT)
            paths = {
                "PROTOCOL": root / "protocol.json",
                "PREAUDIT": root / "preaudit.json",
                "ACTIVATION": root / "activation.json",
                "EXECUTION_START": root / "start.json",
                "RESULT": root / "result.json",
                "DECISION": root / "decision.json",
                "POSTAUDIT": root / "postaudit.json",
            }
            with ExitStack() as stack:
                for name, value in paths.items():
                    stack.enter_context(patch.object(target, name, value))
                protocol = target.build_protocol(now=0, require_pristine=False)
                _write_json(ROOT / paths["PROTOCOL"], protocol)
                tests = {
                    "suites": [
                        {"path": path, "test_count": count, "passed": True}
                        for path, count, _timeout in target.TEST_SUITES
                    ],
                    "test_count": target.EXPECTED_TEST_COUNT,
                    "passed": True,
                    "network_model_search_fetch_or_evaluator_called": False,
                }
                stack.enter_context(patch.object(base, "_run_tests", return_value=tests))
                stack.enter_context(
                    patch.object(base, "_all_sources_tracked", return_value=True)
                )
                stack.enter_context(patch.object(base, "_port_listening", return_value=True))
                stack.enter_context(
                    patch.object(base, "lease_observation", return_value={"active": False})
                )
                stack.enter_context(patch.object(base, "_future", return_value=True))
                stack.enter_context(
                    patch.object(
                        base,
                        "_git",
                        side_effect=lambda _root, *args: ""
                        if args == ("status", "--porcelain")
                        else "a" * 40,
                    )
                )
                value = target.build_preaudit(now=0)
                validated = target.validate_preaudit(value=value)
                _write_json(ROOT / paths["PREAUDIT"], validated)
                activation = target.build_activation(now=0)
                _write_json(ROOT / paths["ACTIVATION"], activation)
                validated_activation = target.validate_activation()
                execution_start = target.build_execution_start(now=0)
                _write_json(ROOT / paths["EXECUTION_START"], execution_start)
                validated_start = target.validate_execution_start()
        self.assertTrue(validated["audit_valid"])
        self.assertTrue(validated["launch_authorized"])
        self.assertEqual(validated["findings"], [])
        self.assertEqual(
            validated["checks"]["focused_tests"]["test_count"],
            target.EXPECTED_TEST_COUNT,
        )
        self.assertEqual(
            validated["validator_binding_successor"], target._validator_binding()
        )
        self.assertEqual(
            validated["preaudit_builder_ordering_successor"],
            target._ordering_binding(),
        )
        self.assertTrue(validated_activation["launch_authorized"])
        self.assertEqual(validated_activation["status"], "active")
        self.assertFalse(
            validated_activation[
                "network_model_search_fetch_evaluator_or_api_called"
            ]
        )
        self.assertTrue(validated_start["execution_authorized"])
        self.assertEqual(validated_start["status"], "ready")
        self.assertFalse(validated_start["api_called_before_execution_start"])
        self.assertFalse(validated_start["benchmark_or_evaluator_authorized"])

    def test_worker_and_supervisor_cli_subprocesses_bind_successor_validator(self) -> None:
        for command in ("worker", "supervisor"):
            completed = subprocess.run(
                [
                    str(ROOT / ".venv-eval/bin/python"),
                    "-I",
                    "-B",
                    str(Path(__file__).resolve()),
                    "--cli-validator-smoke",
                    command,
                ],
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            receipt = json.loads(completed.stdout.strip())
            self.assertEqual(receipt["command"], command)
            self.assertEqual(receipt["protocol_id"], target.PROTOCOL_ID)
            self.assertTrue(receipt["validator_context_passed"])
            self.assertFalse(
                receipt["network_model_search_fetch_or_evaluator_called"]
            )

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("scripts/v24501_reserve_external_gate.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--cli-validator-smoke":
        raise SystemExit(_cli_validator_smoke(sys.argv[2]))
    unittest.main()
