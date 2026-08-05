from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import v24500_reserve_external_gate as target  # noqa: E402


def reseal(value: dict, field: str) -> None:
    value.pop(field, None)
    value[field] = payload_sha256(value)


def _cli_validator_smoke(command: str) -> int:
    """Exercise the real successor CLI dispatch without any remote effect."""

    protocol = target.build_protocol(now=0, require_pristine=False)

    def validate_in_process(args: argparse.Namespace) -> None:
        validated = target.predecessor.base.validate_protocol(ROOT, value=protocol)
        if (
            validated.get("protocol_id") != target.PROTOCOL_ID
            or validated.get("validator_binding_successor")
            != target._successor_binding()
            or target.predecessor.base.RUNNER_MARKER != target.RUNNER_MARKER
            or target.predecessor.base.run_targeted_worker
            is not target.predecessor.run_reserve_worker
        ):
            raise RuntimeError("V2.45.00 CLI validator context is incomplete")
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

    original_worker = target.predecessor.base._worker
    original_supervisor = target.predecessor.base._supervisor
    original_argv = sys.argv
    try:
        target.predecessor.base._worker = validate_in_process
        target.predecessor.base._supervisor = validate_in_process
        sys.argv = [str(ROOT / target.RUNNER_MARKER), command]
        target.main()
    finally:
        sys.argv = original_argv
        target.predecessor.base._worker = original_worker
        target.predecessor.base._supervisor = original_supervisor
    return 0


class V24500ReserveExternalGateTests(unittest.TestCase):
    def test_predecessor_invalidation_is_sealed_and_population_is_unconsumed(self) -> None:
        value = target.validate_invalidation()
        self.assertFalse(value["same_population_consumed"])
        self.assertFalse(value["activation_created"])
        self.assertFalse(value["execution_start_created"])
        self.assertFalse(value["external_probe_launched"])
        self.assertFalse(value["network_model_search_fetch_or_evaluator_called"])
        for relative in (
            target.predecessor.ACTIVATION,
            target.predecessor.EXECUTION_START,
            target.predecessor.RESULT,
        ):
            self.assertFalse((ROOT / relative).exists(), relative)

    def test_successor_reuses_exact_population_mechanism_budget_and_gates(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        predecessor_protocol = target.predecessor._read(target.predecessor.PROTOCOL)
        for field in (
            "task_contract",
            "reserve_binding",
            "mechanism",
            "budget",
            "gates",
        ):
            self.assertEqual(value[field], predecessor_protocol[field], field)
        self.assertEqual(target.PREDECESSOR_PROTOCOL_ID, predecessor_protocol["protocol_id"])
        binding = value["validator_binding_successor"]
        self.assertTrue(binding["same_unconsumed_population_reused"])
        self.assertTrue(binding["mechanism_budget_gates_and_population_unchanged"])
        self.assertFalse(binding["additional_network_model_search_fetch_or_evaluator_effect"])
        self.assertFalse(value["authorization"]["external_probe_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])

    def test_resealed_successor_binding_tamper_fails_closed(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        cases = (
            ("same_unconsumed_population_reused", False),
            ("mechanism_budget_gates_and_population_unchanged", False),
            ("supervisor_validator_context_bound", False),
            ("worker_validator_context_bound", False),
            ("additional_network_model_search_fetch_or_evaluator_effect", True),
        )
        for field, replacement in cases:
            changed = copy.deepcopy(value)
            changed["validator_binding_successor"][field] = replacement
            reseal(changed, "protocol_payload_sha256")
            with self.assertRaises(RuntimeError, msg=field):
                target.validate_protocol(value=changed)

    def test_configured_predecessor_restores_configuration_and_validators(self) -> None:
        names = (
            "PROTOCOL_ID",
            "PROTOCOL",
            "RUNNER_MARKER",
            "_CORE_PATCHED",
            "validate_protocol",
            "validate_preaudit",
            "validate_activation",
            "validate_execution_start",
        )
        originals = {name: getattr(target.predecessor, name) for name in names}
        base_names = ("PROTOCOL_ID", "RUNNER_MARKER", "validate_protocol")
        base_originals = {
            name: getattr(target.predecessor.base, name) for name in base_names
        }
        with target.configured_predecessor(validators=True):
            self.assertEqual(target.predecessor.PROTOCOL_ID, target.PROTOCOL_ID)
            self.assertIs(target.predecessor.validate_protocol, target.validate_protocol)
            self.assertIs(target.predecessor.validate_preaudit, target.validate_preaudit)
            with (
                target.predecessor.configured_base(),
                target.predecessor._with_validator_patches(),
            ):
                self.assertEqual(target.predecessor.base.PROTOCOL_ID, target.PROTOCOL_ID)
                self.assertEqual(
                    target.predecessor.base.RUNNER_MARKER, target.RUNNER_MARKER
                )
                self.assertIs(
                    target.predecessor.base.run_targeted_worker,
                    target.predecessor.run_reserve_worker,
                )
        for name, value in originals.items():
            self.assertIs(getattr(target.predecessor, name), value, name)
        for name, value in base_originals.items():
            self.assertIs(getattr(target.predecessor.base, name), value, name)

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
            Path("scripts/v24500_reserve_external_gate.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--cli-validator-smoke":
        raise SystemExit(_cli_validator_smoke(sys.argv[2]))
    unittest.main()
