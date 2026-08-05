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
from scripts import v24554_alias_joint_external_gate as target  # noqa: E402
from test_v24550_total_alias_joint_projection import (  # noqa: E402
    positive_capability,
)
from test_v24549_proof_carrying_alias_joint import populate, validate  # noqa: E402


def reseal(value: dict, field: str) -> None:
    value.pop(field, None)
    value[field] = payload_sha256(value)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def passing_mechanism() -> dict:
    triple = (
        "selected_alias_surface_hit_new_observation_and_positive_information_gain_count"
    )
    return {
        "success_tasks": 8,
        "failure_as_zero_tasks": 0,
        "passed_success_tasks": 8,
        "alias_joint_plan_tasks": 1,
        "alias_joint_activity_tasks": 1,
        "selected_alias_surface_hit_tasks": 1,
        "alias_joint_new_observation_tasks": 1,
        "alias_joint_raw_positive_information_gain_tasks": 1,
        f"{triple}_tasks": 1,
        "alias_joint_action_positive_information_credit_tasks": 1,
        "alias_joint_action_positive_epistemic_credit_tasks": 1,
        "alias_joint_action_positive_decision_credit_tasks": 1,
        "alias_joint_safe_change_improvement_tasks": 1,
        "alias_joint_safe_change_regression_tasks": 0,
        "alias_joint_decision_credit_regression_tasks": 0,
        "total_alias_surface_count_fields": {
            "selected_alias_surface_hit_lead_count": 1
        },
        "total_alias_joint_count_fields": {triple: 1},
        "total_alias_joint_number_fields": {
            "information_gain_gain_nats": 0.6,
            "action_information_credit_nats": 0.6,
            "action_epistemic_credit_nats": 0.5,
            "action_decision_credit_nats": 0.4,
            "action_decision_credit_regression_nats": 0.0,
        },
        "total_alias_stage_count_fields": {
            "additional_model_requests": 0,
            "additional_logical_queries": 0,
            "additional_search_batches": 0,
            "additional_provider_search_calls": 0,
            "additional_fetch_calls": 0,
        },
        "all_alias_joint_success_rows_consumed_validated_capabilities": True,
        "all_alias_joint_failure_rows_are_content_free_zero_projections": True,
        "alias_joint_failure_rows_claim_zero_private_effects": False,
        "alias_joint_private_task_content_emitted": False,
        "alias_joint_privileged_evaluator_content_read": False,
        "alias_joint_same_task_counts_claim_lead_level_causality": False,
    }


def cli_validator_smoke(command: str) -> int:
    protocol = target.build_protocol(now=0, require_pristine=False)

    def validate_in_process(args: argparse.Namespace) -> None:
        validated = target.validate_protocol(value=protocol)
        if (
            validated["protocol_id"] != target.PROTOCOL_ID
            or target.base.PROTOCOL_ID != target.PROTOCOL_ID
            or target.base.RUNNER_MARKER != target.RUNNER_MARKER
            or target.base.run_targeted_worker is not target.bounded.run_worker
            or target.base.run_targeted_parent_with_separated_budget
            is not target.bounded.run_parent_with_separated_budget
            or target.base.aggregate_projections
            is not target.aggregate_alias_joint_projections
            or target.base.validate_targeted_aggregate
            is not target.total.validate_aggregate
        ):
            raise RuntimeError("V2.45.54 CLI execution-base context is incomplete")
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
        target.base._worker,
        target.base._supervisor,
        sys.argv,
    )
    try:
        target.base._worker = validate_in_process
        target.base._supervisor = validate_in_process
        sys.argv = [str(ROOT / target.RUNNER_MARKER), command]
        target.main()
    finally:
        sys.argv = original_argv
        target.base._worker, target.base._supervisor = original_worker, original_supervisor
    return 0


class V24554AliasJointExternalGateTests(unittest.TestCase):
    def test_population_is_fresh_and_alias_surfaces_are_query_blind(self) -> None:
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertTrue(target._alias_surface_vector_valid())
        self.assertEqual(len(target._prior_questions()), 428)
        self.assertEqual(len(target.QUESTIONS), 8)
        self.assertEqual(sum(map(len, target.ENTITY_GROUPS)), 64)
        surfaces = [
            target.acquisition.primary_alias_surface(entity)
            for group in target.ENTITY_GROUPS
            for entity in group
        ]
        self.assertEqual(len({value.casefold() for value in surfaces if value}), 64)

    def test_v24545_closure_and_v24553_parent_authorize_design_only(self) -> None:
        self.assertTrue(target._previous_closed())
        parent = target._parent(target.ROOT)
        self.assertTrue(parent["audit_valid"])
        self.assertEqual(parent["tests"]["test_count"], 25)
        self.assertTrue(
            parent["authorization"][
                "fresh_disjoint_bounded_alias_joint_external_protocol_design"
            ]
        )
        self.assertFalse(parent["authorization"]["fresh_external_activation_or_launch"])

    def test_protocol_binds_population_joint_credit_and_budget(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        mechanism = value["mechanism"]
        self.assertEqual(mechanism["alias_surface_policy"], target.surface.POLICY_ID)
        self.assertEqual(mechanism["alias_action_joint_policy"], target.joint.POLICY_ID)
        self.assertFalse(mechanism["query_text_used_to_establish_alias_hit"])
        self.assertFalse(mechanism["same_task_joint_counts_claim_lead_level_causality"])
        self.assertTrue(
            mechanism[
                "selected_alias_surface_new_observation_and_positive_gain_same_task_required"
            ]
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
        self.assertTrue(set(target.base.SOURCE_FILES).issubset(target.SOURCE_FILES))
        self.assertTrue(
            set(target.predecessor.SOURCE_FILES).issubset(target.SOURCE_FILES)
        )
        self.assertTrue(
            set(target.base.SOURCE_FILES).issubset(value["surface_manifest"])
        )
        self.assertTrue(
            set(target.predecessor.SOURCE_FILES).issubset(
                value["surface_manifest"]
            )
        )

    def test_protocol_contains_no_task_content_and_runtime_input_is_neutral(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        encoded = json.dumps(value, ensure_ascii=False)
        with target.configured_base(validators=False):
            for ordinal in range(1, 9):
                task = target.base.neutral_task(ordinal)
                self.assertEqual(set(task), {"opaque_id", "question"})
                self.assertNotIn(task["opaque_id"], encoded)
                self.assertNotIn(task["question"], encoded)

    def test_resealed_protocol_tamper_fails_closed(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        cases = (
            lambda item: item["successor_binding"].__setitem__(
                "same_or_prior_population_resume_retry_or_rerun", True
            ),
            lambda item: item["mechanism"].__setitem__(
                "query_text_used_to_establish_alias_hit", True
            ),
            lambda item: item["mechanism"].__setitem__(
                "same_task_joint_counts_claim_lead_level_causality", True
            ),
            lambda item: item["task_contract"].__setitem__(
                "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_428_consumed_external_questions",
                False,
            ),
        )
        for alter in cases:
            changed = copy.deepcopy(value)
            alter(changed)
            reseal(changed, "protocol_payload_sha256")
            with self.assertRaises(RuntimeError):
                target.validate_protocol(value=changed)

    def test_mechanism_requires_same_task_triple_and_action_credit(self) -> None:
        value = passing_mechanism()
        self.assertTrue(target.mechanism_passed(value))
        triple = (
            "selected_alias_surface_hit_new_observation_and_positive_information_gain_count_tasks"
        )
        changed = copy.deepcopy(value)
        changed[triple] = 0
        changed["total_alias_joint_count_fields"][triple.removesuffix("_tasks")] = 0
        self.assertFalse(target.mechanism_passed(changed))
        self.assertEqual(
            target.diagnostic_route(
                changed,
                {"worker_hard_timeout_tasks": 0, "worker_nonzero_tasks": 0},
                diagnostic=False,
                reliability=True,
                parent_validation=True,
                latency=True,
            ),
            "alias_observation_gain_joint_successor",
        )

    def test_capability_collector_aggregates_once_and_restores_pure_projector(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            source = Path(temporary) / "source"
            source.mkdir()
            populate(source)
            positive_root = Path(temporary) / "positive"
            capability = positive_capability(source, positive_root)
            with target.capability_collection() as collector:
                row = target.total.task_projection(1, capability)
                aggregate = target.aggregate_alias_joint_projections([row], selected=1)
                self.assertEqual(aggregate["success_tasks"], 1)
                self.assertEqual(
                    aggregate[
                        "selected_alias_surface_hit_new_observation_and_positive_information_gain_count_tasks"
                    ],
                    1,
                )
                with self.assertRaisesRegex(RuntimeError, "already consumed"):
                    collector.aggregate([row], selected=1)
            self.assertIs(target.total.task_projection, target._ORIGINAL_TASK_PROJECTION)

    def test_collector_duplicate_failure_and_missing_context_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            root = Path(temporary)
            populate(root)
            capability = validate(root)
            with target.capability_collection():
                target.total.task_projection(1, capability)
                with self.assertRaisesRegex(RuntimeError, "duplicate or late"):
                    target.total.task_projection(1, capability)
        with self.assertRaisesRegex(RuntimeError, "collector is absent"):
            target.aggregate_alias_joint_projections(
                [target.total.failure_projection(1)], selected=1
            )

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
                stack.enter_context(
                    patch.object(target.base, "_all_sources_tracked", return_value=True)
                )
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
                self.assertTrue(target.validate_preaudit(value=preaudit)["audit_valid"])
                activation = target.build_activation(now=0)
                self.assertEqual(
                    activation["authorization"], target._activation_authorization()
                )
                self.assertNotIn(
                    "one_fresh_targeted_external_probe_launch",
                    activation["authorization"],
                )
                write_json(ROOT / paths["ACTIVATION"], activation)
                self.assertTrue(target.validate_activation()["launch_authorized"])
                start = target.build_execution_start(now=0)
                write_json(ROOT / paths["EXECUTION_START"], start)
                self.assertTrue(target.validate_execution_start()["execution_authorized"])
        self.assertEqual(preaudit["checks"]["focused_tests"]["test_count"], 49)
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
                timeout=60,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            receipt = json.loads(completed.stdout.strip())
            self.assertTrue(receipt["execution_base_context_passed"])
            self.assertFalse(receipt["network_model_search_fetch_or_evaluator_called"])

    def test_configuration_restores_base_bindings(self) -> None:
        before = (
            target.base.PROTOCOL_ID,
            target.base.run_targeted_worker,
            target.base.aggregate_projections,
        )
        with target.configured_base(validators=True):
            self.assertEqual(target.base.PROTOCOL_ID, target.PROTOCOL_ID)
            self.assertIs(target.base.run_targeted_worker, target.bounded.run_worker)
            self.assertIs(
                target.base.aggregate_projections,
                target.aggregate_alias_joint_projections,
            )
        self.assertEqual(
            (
                target.base.PROTOCOL_ID,
                target.base.run_targeted_worker,
                target.base.aggregate_projections,
            ),
            before,
        )

    def test_runtime_source_is_label_blind_and_benchmark_never_authorized(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        self.assertFalse(value["authorization"]["benchmark_launch"])
        self.assertFalse(value["authorization"]["evaluator"])
        self.assertFalse(value["authorization"]["leaderboard_or_sota"])
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("scripts/v24554_alias_joint_external_gate.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--cli-validator-smoke":
        raise SystemExit(cli_validator_smoke(sys.argv[2]))
    unittest.main()
