from __future__ import annotations

import argparse
import concurrent.futures
import copy
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import v24539_alias_action_credit_external_gate as target  # noqa: E402


def reseal(value: dict, field: str) -> None:
    value.pop(field, None)
    value[field] = payload_sha256(value)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def cli_validator_smoke(command: str) -> int:
    protocol = target.build_protocol(now=0, require_pristine=False)
    base = target._base()

    def validate_in_process(args: argparse.Namespace) -> None:
        validated = target.validate_protocol(value=protocol)
        if (
            validated["protocol_id"] != target.PROTOCOL_ID
            or base.PROTOCOL_ID != target.PROTOCOL_ID
            or base.RUNNER_MARKER != target.RUNNER_MARKER
            or base.run_targeted_worker is not target.predecessor.proof.run_worker
            or base.run_targeted_parent_with_separated_budget
            is not target.predecessor.proof.run_parent_with_separated_budget
            or base.aggregate_projections
            is not target.predecessor.aggregate_action_projections
            or base.validate_targeted_aggregate
            is not target.predecessor.total.validate_aggregate
        ):
            raise RuntimeError("V2.45.39 CLI execution-base context is incomplete")
        print(
            json.dumps(
                {
                    "command": args.command,
                    "protocol_id": validated["protocol_id"],
                    "execution_base_context_passed": True,
                    "network_model_search_fetch_or_evaluator_called": False,
                },
                sort_keys=True,
            )
        )

    original_worker, original_supervisor, original_argv = (
        base._worker,
        base._supervisor,
        sys.argv,
    )
    try:
        base._worker = validate_in_process
        base._supervisor = validate_in_process
        sys.argv = [str(ROOT / target.RUNNER_MARKER), command]
        target.main()
    finally:
        sys.argv = original_argv
        base._worker, base._supervisor = original_worker, original_supervisor
    return 0


class V24539AliasActionCreditExternalGateTests(unittest.TestCase):
    def test_population_is_fresh_and_alias_surfaces_are_globally_unique(self) -> None:
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertTrue(target._alias_surface_vector_valid())
        self.assertEqual(len(target._prior_questions()), 396)
        self.assertEqual(len(target.QUESTIONS), 8)
        self.assertEqual(sum(map(len, target.ENTITY_GROUPS)), 64)
        surfaces = [
            target.acquisition.primary_alias_surface(entity)
            for group in target.ENTITY_GROUPS
            for entity in group
        ]
        self.assertEqual(len({value.casefold() for value in surfaces if value}), 64)

    def test_v24537_population_is_quarantined_consumed_and_never_rerun(self) -> None:
        self.assertTrue(target._quarantine_valid())
        binding = target._record_bound_binding()
        self.assertFalse(binding["v24537_population_resume_retry_or_rerun"])
        self.assertEqual(binding["prior_external_question_count"], 396)
        self.assertEqual(binding["prior_external_entity_count"], 3168)
        self.assertFalse(binding["new_population_reuses_prior_question_or_entity"])

    def test_build_parent_authorizes_protocol_design_only(self) -> None:
        value = target._parent(target.ROOT)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["tests"]["test_count"], 138)
        self.assertTrue(
            value["authorization"][
                "fresh_disjoint_action_credit_external_protocol_design"
            ]
        )
        self.assertFalse(value["authorization"]["fresh_external_activation_or_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])

    def test_protocol_binds_repair_population_capacity_and_action_gate(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        mechanism = value["mechanism"]
        self.assertFalse(
            mechanism["v24537_invalid_population_resume_retry_or_rerun"]
        )
        self.assertTrue(mechanism["execution_base_action_binding_build_audit_bound"])
        self.assertTrue(
            mechanism["legacy_alias_aggregate_rejected_before_public_result_acceptance"]
        )
        self.assertEqual(value["provider"]["executor_count"], 8)
        self.assertEqual(value["provider"]["model_slot_cap"], 2)
        self.assertEqual(
            [
                value["budget"]["effect_deadline_seconds"],
                value["budget"]["worker_timeout_seconds"],
                value["budget"]["parent_timeout_seconds"],
                value["budget"]["maximum_batch_wall_seconds"],
            ],
            [150.0, 220.0, 245.0, 255.0],
        )

    def test_protocol_contains_no_task_content_and_runtime_input_is_neutral(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        encoded = json.dumps(value, ensure_ascii=False)
        for ordinal in range(1, 9):
            with target.configured_predecessor(), target.predecessor.configured_base():
                task = target._base().neutral_task(ordinal)
            self.assertEqual(set(task), {"opaque_id", "question"})
            self.assertNotIn(task["opaque_id"], encoded)
            self.assertNotIn(task["question"], encoded)

    def test_resealed_protocol_tamper_fails_closed(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        cases = (
            lambda item: item["record_bound_binding"].__setitem__(
                "v24537_population_resume_retry_or_rerun", True
            ),
            lambda item: item["mechanism"].__setitem__(
                "execution_base_action_binding_build_audit_bound", False
            ),
            lambda item: item["task_contract"].__setitem__(
                "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_396_consumed_external_questions",
                False,
            ),
        )
        for alter in cases:
            changed = copy.deepcopy(value)
            alter(changed)
            reseal(changed, "protocol_payload_sha256")
            with self.assertRaises(RuntimeError):
                target.validate_protocol(value=changed)

    def test_execution_base_core_uses_action_runtime(self) -> None:
        core = target._patched_core()
        self.assertIs(core["run_targeted_worker"], target.predecessor.proof.run_worker)
        self.assertIs(
            core["run_targeted_parent_with_separated_budget"],
            target.predecessor.proof.run_parent_with_separated_budget,
        )
        self.assertIs(
            core["aggregate_projections"],
            target.predecessor.aggregate_action_projections,
        )
        self.assertIs(
            core["validate_targeted_aggregate"],
            target.predecessor.total.validate_aggregate,
        )

    def test_concurrent_protocol_validation_serializes_nested_module_patches(
        self,
    ) -> None:
        protocol = target.build_protocol(now=0, require_pristine=False)
        original = target._ORIGINAL_VALIDATE_PROTOCOL
        start = threading.Barrier(8)
        state_lock = threading.Lock()
        active = 0
        maximum_active = 0

        def observed_original(*args, **kwargs):
            nonlocal active, maximum_active
            with state_lock:
                active += 1
                maximum_active = max(maximum_active, active)
            try:
                time.sleep(0.02)
                return original(*args, **kwargs)
            finally:
                with state_lock:
                    active -= 1

        def validate_once(_ordinal: int) -> str:
            start.wait(timeout=5)
            return target.validate_protocol(value=protocol)["protocol_id"]

        with (
            patch.object(
                target,
                "_ORIGINAL_VALIDATE_PROTOCOL",
                side_effect=observed_original,
            ),
            concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool,
        ):
            values = list(pool.map(validate_once, range(8)))
        self.assertEqual(values, [target.PROTOCOL_ID] * 8)
        self.assertEqual(maximum_active, 1)

    def test_frozen_protocol_builds_preaudit_activation_and_start(self) -> None:
        base = target._base()
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
                preaudit = target.build_preaudit(now=0)
                write_json(ROOT / paths["PREAUDIT"], preaudit)
                self.assertTrue(target.validate_preaudit(value=preaudit)["audit_valid"])
                activation = target.build_activation(now=0)
                write_json(ROOT / paths["ACTIVATION"], activation)
                self.assertTrue(target.validate_activation()["launch_authorized"])
                start = target.build_execution_start(now=0)
                write_json(ROOT / paths["EXECUTION_START"], start)
                self.assertTrue(target.validate_execution_start()["execution_authorized"])
        self.assertEqual(preaudit["checks"]["focused_tests"]["test_count"], 184)
        self.assertFalse(start["benchmark_or_evaluator_authorized"])

    def test_worker_and_supervisor_cli_bind_execution_base(self) -> None:
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
                timeout=50,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            receipt = json.loads(completed.stdout.strip())
            self.assertTrue(receipt["execution_base_context_passed"])
            self.assertFalse(receipt["network_model_search_fetch_or_evaluator_called"])

    def test_configuration_restores_predecessor_and_base_bindings(self) -> None:
        base = target._base()
        before_predecessor = target.predecessor.PROTOCOL_ID
        before_base = base.PROTOCOL_ID
        with target.configured_predecessor(validators=True):
            self.assertEqual(target.predecessor.PROTOCOL_ID, target.PROTOCOL_ID)
            with target.predecessor.configured_base():
                self.assertEqual(base.PROTOCOL_ID, target.PROTOCOL_ID)
        self.assertEqual(target.predecessor.PROTOCOL_ID, before_predecessor)
        self.assertEqual(base.PROTOCOL_ID, before_base)

    def test_protocol_never_authorizes_benchmark_or_evaluator(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        self.assertFalse(value["authorization"]["benchmark_launch"])
        self.assertFalse(value["authorization"]["eval" + "uator"])
        self.assertFalse(value["authorization"]["leaderboard_or_sota"])
        self.assertFalse(
            value["record_bound_binding"][
                "paired_dev64_or_exact220_directly_authorized"
            ]
        )

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("scripts/v24539_alias_action_credit_external_gate.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--cli-validator-smoke":
        raise SystemExit(cli_validator_smoke(sys.argv[2]))
    unittest.main()
