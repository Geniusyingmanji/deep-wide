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
from deepwide_agent.v24505_record_bound_timed_parent import (  # noqa: E402
    failure_projection,
)
from scripts import v24506_record_bound_external_gate as target  # noqa: E402
import test_v24504_proof_carrying_record_bound_reserve as fixture  # noqa: E402


def reseal(value: dict, field: str) -> None:
    value.pop(field, None)
    value[field] = payload_sha256(value)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _cli_validator_smoke(command: str) -> int:
    protocol = target.build_protocol(now=0, require_pristine=False)

    def validate_in_process(args: argparse.Namespace) -> None:
        validated = target.base.validate_protocol(ROOT, value=protocol)
        if (
            validated.get("protocol_id") != target.PROTOCOL_ID
            or validated.get("record_bound_binding")
            != target._record_bound_binding()
            or target.base.RUNNER_MARKER != target.RUNNER_MARKER
            or target.base.run_targeted_worker is not target.run_record_bound_worker
        ):
            raise RuntimeError("V2.45.06 CLI validator context is incomplete")
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

    original_worker = target.base._worker
    original_supervisor = target.base._supervisor
    original_argv = sys.argv
    try:
        target.base._worker = validate_in_process
        target.base._supervisor = validate_in_process
        sys.argv = [str(ROOT / target.RUNNER_MARKER), command]
        target.main()
    finally:
        sys.argv = original_argv
        target.base._worker = original_worker
        target.base._supervisor = original_supervisor
    return 0


class V24506RecordBoundExternalGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixture.V24504ProofCarryingRecordBoundReserveTests.setUpClass()
        owner = fixture.V24504ProofCarryingRecordBoundReserveTests()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            owner.populate(directory)
            capability = owner.validate(directory)
            from deepwide_agent.v24504_proof_carrying_record_bound_reserve import (
                task_projection,
            )

            cls.success = task_projection(1, capability)

    @classmethod
    def tearDownClass(cls) -> None:
        fixture.V24504ProofCarryingRecordBoundReserveTests.tearDownClass()

    def test_population_is_fresh_against_324_questions_and_2592_entities(self) -> None:
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertEqual(len(target._prior_questions()), 324)
        self.assertEqual(len(target.QUESTIONS), 8)
        self.assertEqual(sum(map(len, target.ENTITY_GROUPS)), 64)

    def test_protocol_is_design_only_and_contains_no_task_content(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        encoded = json.dumps(value, ensure_ascii=False)
        with target.configured_base():
            for ordinal in range(1, 9):
                task = target.base.neutral_task(ordinal)
                self.assertNotIn(task["opaque_id"], encoded)
                self.assertNotIn(task["question"], encoded)
        binding = value["record_bound_binding"]
        self.assertEqual(binding["prior_external_question_count"], 324)
        self.assertEqual(binding["prior_external_entity_count"], 2592)
        self.assertFalse(binding["new_population_reuses_prior_question_or_entity"])
        self.assertFalse(value["authorization"]["external_probe_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])

    def test_resealed_protocol_tamper_fails_closed(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        cases = (
            lambda item: item["record_bound_binding"].__setitem__(
                "new_population_reuses_prior_question_or_entity", True
            ),
            lambda item: item["record_bound_binding"].__setitem__(
                "same_frozen_page_vector_replayed", False
            ),
            lambda item: item["mechanism"].__setitem__(
                "record_bound_additional_external_effect", True
            ),
            lambda item: item["authorization"].__setitem__(
                "external_probe_launch", True
            ),
        )
        for alter in cases:
            changed = copy.deepcopy(value)
            alter(changed)
            reseal(changed, "protocol_payload_sha256")
            with self.assertRaises(RuntimeError):
                target.validate_protocol(value=changed)

    def test_mechanism_gate_requires_complete_record_bound_conversion(self) -> None:
        rows = []
        for ordinal in range(1, 9):
            row = copy.deepcopy(self.success)
            row["ordinal"] = ordinal
            rows.append(row)
        passing = target.total.aggregate_projections(rows, selected=8)
        self.assertTrue(target.mechanism_passed(passing))
        for field in (
            "reserve_engaged_tasks",
            "reserve_usable_page_tasks",
            "record_bound_added_observation_tasks",
            "record_bound_projection_tasks",
            "safe_change_improvement_tasks",
            "positive_decision_credit_gain_tasks",
            "total_decision_credit_gain_nats",
        ):
            changed = copy.deepcopy(passing)
            changed[field] = 0
            self.assertFalse(target.mechanism_passed(changed), field)
        mixed = target.total.aggregate_projections(
            [*rows[:7], failure_projection(8)], selected=8
        )
        self.assertFalse(target.mechanism_passed(mixed))

    def test_diagnostic_route_preserves_record_bound_funnel(self) -> None:
        supervision = {"worker_hard_timeout_tasks": 0, "worker_nonzero_tasks": 0}
        cases = (
            ({"target_plan_tasks": 0}, "target_plan_coverage_successor"),
            (
                {"target_plan_tasks": 1, "reserve_engaged_tasks": 0},
                "reserve_engagement_successor",
            ),
            (
                {
                    "target_plan_tasks": 1,
                    "reserve_engaged_tasks": 1,
                    "reserve_usable_page_tasks": 0,
                },
                "reserve_fetch_yield_successor",
            ),
            (
                {
                    "target_plan_tasks": 1,
                    "reserve_engaged_tasks": 1,
                    "reserve_usable_page_tasks": 1,
                    "record_bound_projection_tasks": 0,
                },
                "record_bound_projection_coverage_successor",
            ),
            (
                {
                    "target_plan_tasks": 1,
                    "reserve_engaged_tasks": 1,
                    "reserve_usable_page_tasks": 1,
                    "record_bound_projection_tasks": 1,
                    "record_bound_added_observation_tasks": 0,
                },
                "record_bound_observation_conversion_successor",
            ),
        )
        for mechanism, expected in cases:
            self.assertEqual(
                target.diagnostic_route(
                    mechanism,
                    supervision,
                    diagnostic=True,
                    reliability=True,
                    parent_validation=True,
                    latency=True,
                ),
                expected,
            )

    def test_configured_base_restores_all_bindings(self) -> None:
        missing = object()
        original = {
            name: getattr(target.base, name, missing)
            for name in target._CORE_PATCHED
        }
        with target.configured_base():
            self.assertEqual(target.base.PROTOCOL_ID, target.PROTOCOL_ID)
            self.assertIs(
                target.base.aggregate_projections,
                target.total.aggregate_projections,
            )
            self.assertIs(
                target.base.run_targeted_worker,
                target.run_record_bound_worker,
            )
        for name, value in original.items():
            if value is missing:
                self.assertFalse(hasattr(target.base, name))
            else:
                self.assertIs(getattr(target.base, name), value)

    def test_frozen_protocol_builds_preaudit_activation_and_start(self) -> None:
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
                stack.enter_context(
                    patch.object(target.base, "_run_tests", return_value=tests)
                )
                stack.enter_context(
                    patch.object(target.base, "_all_sources_tracked", return_value=True)
                )
                stack.enter_context(
                    patch.object(target.base, "_port_listening", return_value=True)
                )
                stack.enter_context(
                    patch.object(
                        target.base, "lease_observation", return_value={"active": False}
                    )
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
        self.assertEqual(
            validated["checks"]["focused_tests"]["test_count"],
            target.EXPECTED_TEST_COUNT,
        )
        self.assertTrue(validated_activation["launch_authorized"])
        self.assertTrue(validated_start["execution_authorized"])
        self.assertFalse(validated_start["benchmark_or_evaluator_authorized"])

    def test_worker_and_supervisor_cli_bind_record_validator(self) -> None:
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
            self.assertEqual(receipt["protocol_id"], target.PROTOCOL_ID)
            self.assertTrue(receipt["validator_context_passed"])
            self.assertFalse(
                receipt["network_model_search_fetch_or_evaluator_called"]
            )

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("scripts/v24506_record_bound_external_gate.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--cli-validator-smoke":
        raise SystemExit(_cli_validator_smoke(sys.argv[2]))
    unittest.main()
