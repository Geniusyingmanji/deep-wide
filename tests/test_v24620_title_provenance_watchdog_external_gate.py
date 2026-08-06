from __future__ import annotations

import argparse
import ast
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
from scripts import v24620_title_provenance_watchdog_external_gate as target  # noqa: E402


def reseal(value: dict, field: str) -> None:
    value.pop(field, None)
    value[field] = payload_sha256(value)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def cli_validator_smoke(command: str) -> int:
    protocol = target.build_protocol(now=0, require_pristine=False)

    def validate_in_process(args: argparse.Namespace) -> None:
        validated = target.validate_runtime_protocol()
        if (
            validated["protocol_id"] != target.PROTOCOL_ID
            or target.controller.PROTOCOL_ID != target.PROTOCOL_ID
            or target.controller.proof is not target.proof
            or target.runtime.proof is not target.proof
            or target.runtime.total is not target.total
            or target.runtime.bounded is not target.bounded
            or target.base.run_targeted_worker is not target.bounded.run_worker
            or target.base.run_targeted_parent_with_separated_budget
            is not target.bounded.run_parent_with_separated_budget
            or not target.binding.invariant_valid()
        ):
            raise RuntimeError("V2.46.20 CLI execution context is incomplete")
        print(
            json.dumps(
                {
                    "command": args.command,
                    "protocol_id": validated["protocol_id"],
                    "concurrent_runtime_context_passed": True,
                    "network_model_search_fetch_or_evaluator_called": False,
                },
                sort_keys=True,
            )
        )

    original_worker, original_supervisor, original_argv = (
        target.base._worker,
        target.base._supervisor,
        sys.argv,
    )
    with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
        root = Path(temporary).relative_to(ROOT)
        protocol_path = root / "protocol.json"
        preaudit_path = root / "preaudit.json"
        activation_path = root / "activation.json"
        start_path = root / "start.json"
        write_json(ROOT / protocol_path, protocol)
        preaudit = {
            "protocol_id": target.PROTOCOL_ID,
            "audit_valid": True,
        }
        reseal(preaudit, "audit_payload_sha256")
        write_json(ROOT / preaudit_path, preaudit)
        activation = {
            "protocol_id": target.PROTOCOL_ID,
            "protocol_sha256": target.sha256(ROOT / protocol_path),
            "preactivation_audit_sha256": target.sha256(ROOT / preaudit_path),
            "surface_manifest_sha256": protocol["surface_manifest_sha256"],
            "launch_authorized": True,
        }
        reseal(activation, "activation_payload_sha256")
        write_json(ROOT / activation_path, activation)
        start = {
            "protocol_id": target.PROTOCOL_ID,
            "protocol_sha256": target.sha256(ROOT / protocol_path),
            "activation_sha256": target.sha256(ROOT / activation_path),
            "selected": 8,
            "executor_count": 8,
            "model_slot_cap": 2,
            "execution_authorized": True,
            "benchmark_or_evaluator_authorized": False,
        }
        reseal(start, "execution_start_payload_sha256")
        write_json(ROOT / start_path, start)
        try:
            target.base._worker = validate_in_process
            target.base._supervisor = validate_in_process
            sys.argv = [str(ROOT / target.RUNNER_MARKER), command]
            with (
                patch.object(target, "PROTOCOL", protocol_path),
                patch.object(target, "PREAUDIT", preaudit_path),
                patch.object(target, "ACTIVATION", activation_path),
                patch.object(target, "EXECUTION_START", start_path),
            ):
                target.main()
        finally:
            sys.argv = original_argv
            target.base._worker, target.base._supervisor = (
                original_worker,
                original_supervisor,
            )
    return 0


class V24620TitleProvenanceWatchdogExternalGateTests(unittest.TestCase):
    def test_population_is_fresh_and_surfaces_are_reachable(self) -> None:
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertTrue(target._title_query_surface_vector_valid())
        self.assertEqual(len(target._prior_questions()), 500)
        self.assertEqual(len(target.QUESTIONS), 8)
        self.assertEqual(sum(map(len, target.ENTITY_GROUPS)), 64)

    def test_v24616_is_consumed_and_v24619_authorizes_design_only(self) -> None:
        self.assertTrue(target._previous_closed())
        parent = target._parent(target.ROOT)
        self.assertEqual(parent["tests"]["test_count"], 44)
        self.assertEqual(parent["freshness_baseline"]["prior_external_question_count"], 500)
        self.assertTrue(parent["binding_repair"]["eight_runtime_holders_overlap"])
        self.assertFalse(parent["authorization"]["fresh_external_activation_or_launch"])

    def test_protocol_freezes_fast_validator_and_enforcing_watchdog(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        mechanism = value["mechanism"]
        self.assertEqual(mechanism["controller_binding_policy"], target.binding.POLICY_ID)
        self.assertTrue(mechanism["same_mode_concurrent_holders_share_binding"])
        self.assertTrue(mechanism["runtime_fast_control_validator"])
        self.assertFalse(mechanism["runtime_complete_protocol_revalidation"])
        self.assertEqual(
            mechanism["enforcing_batch_watchdog_policy"], target.watchdog.POLICY_ID
        )
        self.assertTrue(mechanism["maximum_batch_wall_is_enforcing_watchdog"])
        self.assertEqual(value["budget"]["maximum_batch_wall_seconds"], 255.0)

    def test_protocol_preserves_search_and_model_budget(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        self.assertEqual(value["provider"]["executor_count"], 8)
        self.assertEqual(value["provider"]["model_slot_cap"], 2)
        self.assertEqual(
            [
                value["budget"]["effect_deadline_seconds"],
                value["budget"]["worker_timeout_seconds"],
                value["budget"]["parent_timeout_seconds"],
                value["budget"]["maximum_targeted_search_batches_per_task"],
                value["budget"]["maximum_targeted_logical_queries_per_task"],
                value["budget"]["maximum_targeted_fetches_per_task"],
            ],
            [150.0, 220.0, 245.0, 1, 2, 3],
        )

    def test_protocol_contains_no_task_content_and_runtime_input_is_neutral(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        encoded = json.dumps(value, ensure_ascii=False)
        with target.configured_controller(protocol_compatibility=False), target.runtime.configured_base(
            validators=False
        ):
            for ordinal in range(1, 9):
                task = target.base.neutral_task(ordinal)
                self.assertEqual(set(task), {"opaque_id", "question"})
                self.assertNotIn(task["opaque_id"], encoded)
                self.assertNotIn(task["question"], encoded)

    def test_resealed_protocol_tamper_fails_closed(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        cases = (
            lambda item: item["successor_binding"].__setitem__(
                "runtime_task_performs_complete_protocol_validation", True
            ),
            lambda item: item["mechanism"].__setitem__(
                "maximum_batch_wall_is_enforcing_watchdog", False
            ),
            lambda item: item["mechanism"].__setitem__(
                "runtime_complete_protocol_revalidation", True
            ),
            lambda item: item["task_contract"].__setitem__(
                "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_500_consumed_external_questions",
                False,
            ),
        )
        for alter in cases:
            changed = copy.deepcopy(value)
            alter(changed)
            reseal(changed, "protocol_payload_sha256")
            with self.assertRaises(RuntimeError):
                target.validate_protocol(value=changed)

    def test_control_receipt_validates_hashes_without_full_protocol(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            root = Path(temporary).relative_to(ROOT)
            paths = {
                name: root / f"{name.lower()}.json"
                for name in ("PROTOCOL", "PREAUDIT", "ACTIVATION", "EXECUTION_START")
            }
            protocol = target.build_protocol(now=0, require_pristine=False)
            activation = {
                "protocol_id": target.PROTOCOL_ID,
                "protocol_sha256": "",
                "surface_manifest_sha256": protocol["surface_manifest_sha256"],
                "launch_authorized": True,
            }
            start = {
                "protocol_id": target.PROTOCOL_ID,
                "protocol_sha256": "",
                "activation_sha256": "",
                "selected": 8,
                "executor_count": 8,
                "model_slot_cap": 2,
                "execution_authorized": True,
                "benchmark_or_evaluator_authorized": False,
            }
            with ExitStack() as stack:
                for name, path in paths.items():
                    stack.enter_context(patch.object(target, name, path))
                write_json(ROOT / paths["PROTOCOL"], protocol)
                preaudit = {
                    "protocol_id": target.PROTOCOL_ID,
                    "audit_valid": True,
                }
                reseal(preaudit, "audit_payload_sha256")
                write_json(ROOT / paths["PREAUDIT"], preaudit)
                activation["protocol_sha256"] = target.sha256(
                    ROOT / paths["PROTOCOL"]
                )
                activation["preactivation_audit_sha256"] = target.sha256(
                    ROOT / paths["PREAUDIT"]
                )
                reseal(activation, "activation_payload_sha256")
                write_json(ROOT / paths["ACTIVATION"], activation)
                start["protocol_sha256"] = target.sha256(ROOT / paths["PROTOCOL"])
                start["activation_sha256"] = target.sha256(
                    ROOT / paths["ACTIVATION"]
                )
                reseal(start, "execution_start_payload_sha256")
                write_json(ROOT / paths["EXECUTION_START"], start)
                receipt = target._control_receipt()
                self.assertEqual(target.validate_runtime_control_receipt(receipt), receipt)
                changed = dict(receipt)
                changed["selected"] = 7
                with self.assertRaises(RuntimeError):
                    target.validate_runtime_control_receipt(changed)

    def test_fast_run_one_does_not_call_complete_protocol_validator(self) -> None:
        control = {"surface_manifest_sha256": "a" * 64}
        proof = argparse.Namespace(
            adaptive_projection={"p": 1},
            observation={"o": 1},
            timing_receipt={"t": 1},
        )
        outcome = argparse.Namespace(proof=proof, supervision_receipt={"s": 1})
        with (
            patch.object(target, "validate_runtime_control_receipt", return_value=control),
            patch.object(
                target.base,
                "run_targeted_parent_with_separated_budget",
                return_value=outcome,
            ) as parent,
            patch.object(target, "validate_protocol", side_effect=AssertionError),
        ):
            value = target._fast_run_one(
                ROOT,
                ROOT / "outputs",
                ROOT / "outputs",
                ROOT / "outputs",
                ROOT / "outputs",
                1,
                control,
            )
        self.assertEqual(value["mechanism"], {"p": 1})
        self.assertEqual(parent.call_count, 1)

    def test_run_probe_completes_preflight_before_runtime_binding(self) -> None:
        events: list[str] = []
        protocol = {"protocol_id": target.PROTOCOL_ID}
        activation = {"launch_authorized": True}
        control = {"runtime_input_keys": ["opaque_id", "question"]}

        from contextlib import contextmanager

        @contextmanager
        def runtime_context():
            events.append("enter:runtime")
            yield

        with (
            patch.object(target, "validate_protocol", side_effect=lambda: events.append("protocol") or protocol),
            patch.object(target, "validate_preaudit", side_effect=lambda: events.append("preaudit") or {}),
            patch.object(target, "validate_activation", side_effect=lambda: events.append("activation") or activation),
            patch.object(target, "validate_execution_start", side_effect=lambda: events.append("start") or {}),
            patch.object(target, "_control_receipt", return_value=control),
            patch.object(target, "validate_runtime_control_receipt", side_effect=lambda value: events.append("control") or value),
            patch.object(target, "configured_runtime_stack", side_effect=runtime_context),
            patch.object(target, "_run_probe_fast", return_value={"ok": True}) as run,
        ):
            self.assertEqual(target.run_probe(), {"ok": True})
        self.assertEqual(events[:5], ["protocol", "preaudit", "activation", "start", "control"])
        self.assertNotIn("enter:runtime", events[:5])
        run.assert_called_once_with(
            protocol=protocol, activation=activation, control=control
        )

    def test_eight_fast_run_one_calls_overlap_shared_binding(self) -> None:
        with target.configured_controller(protocol_compatibility=False):
            self.assertEqual(target.binding.content_free_snapshot()["holder_count"], 1)
        self.assertEqual(target.binding.content_free_snapshot()["holder_count"], 0)

    def test_runtime_stack_propagates_fast_validator_to_base(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            root = Path(temporary).relative_to(ROOT)
            protocol_path = root / "protocol.json"
            preaudit_path = root / "preaudit.json"
            activation_path = root / "activation.json"
            start_path = root / "start.json"
            protocol = target.build_protocol(now=0, require_pristine=False)
            write_json(ROOT / protocol_path, protocol)
            preaudit = {"protocol_id": target.PROTOCOL_ID, "audit_valid": True}
            reseal(preaudit, "audit_payload_sha256")
            write_json(ROOT / preaudit_path, preaudit)
            activation = {
                "protocol_id": target.PROTOCOL_ID,
                "protocol_sha256": target.sha256(ROOT / protocol_path),
                "preactivation_audit_sha256": target.sha256(ROOT / preaudit_path),
                "surface_manifest_sha256": protocol["surface_manifest_sha256"],
                "launch_authorized": True,
            }
            reseal(activation, "activation_payload_sha256")
            write_json(ROOT / activation_path, activation)
            start = {
                "protocol_id": target.PROTOCOL_ID,
                "protocol_sha256": target.sha256(ROOT / protocol_path),
                "activation_sha256": target.sha256(ROOT / activation_path),
                "selected": 8,
                "executor_count": 8,
                "model_slot_cap": 2,
                "execution_authorized": True,
                "benchmark_or_evaluator_authorized": False,
            }
            reseal(start, "execution_start_payload_sha256")
            write_json(ROOT / start_path, start)
            with (
                patch.object(target, "PROTOCOL", protocol_path),
                patch.object(target, "PREAUDIT", preaudit_path),
                patch.object(target, "ACTIVATION", activation_path),
                patch.object(target, "EXECUTION_START", start_path),
                target.configured_runtime_stack(),
            ):
                self.assertIs(target.base.validate_protocol, target.validate_runtime_protocol)
                self.assertEqual(
                    target.base.validate_protocol()["protocol_id"], target.PROTOCOL_ID
                )

    def test_watchdog_timeout_is_active_not_postcompletion_only(self) -> None:
        source = (ROOT / "scripts/v24620_title_provenance_watchdog_external_gate.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "EnforcingBatchWatchdog"
        ]
        self.assertEqual(len(calls), 1)
        self.assertIn("timeout_seconds=BATCH_WALL_CEILING_SECONDS", source)
        self.assertIn("guard.close()", source)

    def test_result_schema_requires_quiet_watchdog_and_fast_validation(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "aggregate schema"):
            target.validate_public_result({"mechanism_aggregate": {}})

    def test_diagnostic_routes_are_preserved(self) -> None:
        self.assertIs(target.diagnostic_route, target.frozen.diagnostic_route)
        self.assertIs(target.mechanism_passed, target.frozen.mechanism_passed)

    def test_frozen_protocol_builds_preaudit_activation_and_start(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            root = Path(temporary).relative_to(ROOT)
            paths = {
                name: root / f"{name.lower()}.json"
                for name in (
                    "PROTOCOL",
                    "PREAUDIT",
                    "ACTIVATION",
                    "EXECUTION_START",
                    "RESULT",
                    "DECISION",
                    "POSTAUDIT",
                )
            }
            with ExitStack() as stack:
                for name, path in paths.items():
                    stack.enter_context(patch.object(target, name, path))
                protocol = target.build_protocol(now=0, require_pristine=False)
                write_json(ROOT / paths["PROTOCOL"], protocol)
                tests = {
                    "suites": [
                        {"path": path, "test_count": count, "passed": True}
                        for path, count, _timeout in target.TEST_SUITES
                    ],
                    "test_count": target.EXPECTED_TEST_COUNT,
                    "passed": True,
                    "network_model_search_fetch_or_evaluator_called": False,
                }
                stack.enter_context(patch.object(target.base, "_run_tests", return_value=tests))
                stack.enter_context(patch.object(target.base, "_all_sources_tracked", return_value=True))
                stack.enter_context(patch.object(target.base, "_port_listening", return_value=True))
                stack.enter_context(
                    patch.object(target.base, "lease_observation", return_value={"active": False})
                )
                stack.enter_context(patch.object(target.base, "_future", return_value=True))
                stack.enter_context(
                    patch.object(
                        target.base,
                        "_git",
                        side_effect=lambda _root, *args: ""
                        if args == ("status", "--porcelain")
                        else "a" * 40,
                    )
                )
                preaudit = target.build_preaudit(now=0)
                write_json(ROOT / paths["PREAUDIT"], preaudit)
                activation = target.build_activation(now=0)
                write_json(ROOT / paths["ACTIVATION"], activation)
                start = target.build_execution_start(now=0)
                write_json(ROOT / paths["EXECUTION_START"], start)
                self.assertTrue(target.validate_execution_start()["execution_authorized"])
        self.assertTrue(
            preaudit["checks"]
            ["runtime_fast_control_receipt_replaces_per_task_complete_protocol_validation"]
        )
        self.assertFalse(start["benchmark_or_evaluator_authorized"])

    def test_worker_and_supervisor_cli_bind_concurrent_runtime(self) -> None:
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
                timeout=90,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            receipt = json.loads(completed.stdout.strip())
            self.assertTrue(receipt["concurrent_runtime_context_passed"])
            self.assertFalse(receipt["network_model_search_fetch_or_evaluator_called"])

    def test_protocol_design_does_not_authorize_launch_or_benchmark(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        authorization = value["authorization"]
        self.assertTrue(authorization["one_fresh_title_provenance_watchdog_probe_design"])
        self.assertFalse(authorization["external_probe_launch"])
        self.assertFalse(authorization["benchmark_launch"])
        self.assertFalse(authorization["paired_dev64_or_exact220"])
        self.assertFalse(authorization["evaluator"])

    def test_runtime_source_is_label_blind_and_does_not_mutate_proof(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        source = Path("scripts/v24620_title_provenance_watchdog_external_gate.py")
        accesses, imports = audit.ast_findings(source)
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])
        self.assertIsNone(audit.SECRET.search((ROOT / source).read_text(encoding="utf-8")))
        tree = ast.parse((ROOT / source).read_text(encoding="utf-8"))
        writes = []
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for item in targets:
                if (
                    isinstance(item, ast.Attribute)
                    and isinstance(item.value, ast.Name)
                    and item.value.id in {"runtime", "proof"}
                    and item.attr in {"_ORIGINAL_TASK_PROJECTION", "parent_proof"}
                ):
                    writes.append(item.lineno)
        self.assertEqual(writes, [])

    def test_no_existing_runner_or_watcher_is_restarted(self) -> None:
        source = (ROOT / "scripts/v24620_title_provenance_watchdog_external_gate.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("restart", source.casefold())
        self.assertNotIn("resume", source.casefold().replace("resume_retry", ""))

    def test_binding_restores_after_exception(self) -> None:
        before = target.binding.content_free_snapshot()
        with self.assertRaisesRegex(RuntimeError, "synthetic"):
            with target.configured_controller(protocol_compatibility=False):
                raise RuntimeError("synthetic")
        after = target.binding.content_free_snapshot()
        self.assertEqual(after["holder_count"], before["holder_count"])
        self.assertTrue(after["runtime_module_invariant_valid"])


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--cli-validator-smoke":
        raise SystemExit(cli_validator_smoke(sys.argv[2]))
    unittest.main()
