from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import v24537_alias_action_credit_external_gate as target  # noqa: E402


def reseal(value: dict, field: str) -> None:
    value.pop(field, None)
    value[field] = payload_sha256(value)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def passing_mechanism() -> dict:
    return {
        "success_tasks": 8,
        "failure_as_zero_tasks": 0,
        "passed_success_tasks": 8,
        "acquisition_plan_tasks": 2,
        "acquisition_activity_tasks": 2,
        "acquisition_selected_alias_title_hit_tasks": 1,
        "acquisition_new_observation_tasks": 1,
        "acquisition_positive_information_gain_tasks": 1,
        "acquisition_positive_epistemic_credit_tasks": 1,
        "acquisition_positive_decision_credit_tasks": 1,
        "acquisition_safe_change_improvement_tasks": 1,
        "acquisition_safe_change_regression_tasks": 0,
        "acquisition_decision_credit_regression_tasks": 0,
        "total_acquisition_action_count_fields": {
            "targeted_new_observation_count": 1,
        },
        "total_acquisition_action_number_fields": {
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
        "all_acquisition_success_rows_consumed_validated_capabilities": True,
        "all_acquisition_failure_rows_are_content_free_zero_projections": True,
        "acquisition_failure_rows_claim_zero_private_effects": False,
        "acquisition_private_task_content_emitted": False,
        "acquisition_privileged_evaluator_content_read": False,
    }


def legacy_alias_mechanism() -> dict:
    """The exact aggregate family accidentally published by V2.45.37."""

    value = passing_mechanism()
    for name in (
        "acquisition_plan_tasks",
        "acquisition_activity_tasks",
        "acquisition_selected_alias_title_hit_tasks",
        "acquisition_new_observation_tasks",
        "acquisition_positive_information_gain_tasks",
        "acquisition_positive_epistemic_credit_tasks",
        "acquisition_positive_decision_credit_tasks",
        "acquisition_safe_change_improvement_tasks",
        "acquisition_safe_change_regression_tasks",
        "acquisition_decision_credit_regression_tasks",
        "total_acquisition_action_count_fields",
        "total_acquisition_action_number_fields",
        "all_acquisition_success_rows_consumed_validated_capabilities",
        "all_acquisition_failure_rows_are_content_free_zero_projections",
        "acquisition_failure_rows_claim_zero_private_effects",
        "acquisition_private_task_content_emitted",
        "acquisition_privileged_evaluator_content_read",
    ):
        value.pop(name)
    value.update(
        {
            "alias_anchor_tasks": 1,
            "alias_observation_tasks": 1,
            "alias_added_observation_tasks": 1,
            "total_alias_stage_number_fields": {},
            "all_alias_success_rows_consumed_validated_capabilities": True,
        }
    )
    return value


def cli_validator_smoke(command: str) -> int:
    protocol = target.build_protocol(now=0, require_pristine=False)
    base = target._base()

    def validate_in_process(args: argparse.Namespace) -> None:
        validated = target.validate_protocol(value=protocol)
        core = target._patched_core()
        if (
            validated["protocol_id"] != target.PROTOCOL_ID
            or validated["record_bound_binding"] != target._record_bound_binding()
            or core["RUNNER_MARKER"] != target.RUNNER_MARKER
            or core["run_targeted_worker"] is not target.proof.run_worker
            or core["run_targeted_parent_with_separated_budget"]
            is not target.proof.run_parent_with_separated_budget
            or core["aggregate_projections"]
            is not target.aggregate_action_projections
            or core["validate_targeted_aggregate"]
            is not target.total.validate_aggregate
            or base.run_targeted_worker is not target.proof.run_worker
            or base.run_targeted_parent_with_separated_budget
            is not target.proof.run_parent_with_separated_budget
        ):
            raise RuntimeError("V2.45.37 CLI validator context is incomplete")
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


class V24537AliasActionCreditExternalGateTests(unittest.TestCase):
    def test_population_is_fresh_and_alias_surfaces_are_rule_unique(self) -> None:
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertTrue(target._alias_surface_vector_valid())
        self.assertEqual(len(target._prior_questions()), 388)
        self.assertEqual(len(target.QUESTIONS), 8)
        self.assertEqual(sum(map(len, target.ENTITY_GROUPS)), 64)

    def test_v24531_and_v24532_populations_are_consumed_and_never_rerun(self) -> None:
        self.assertTrue(target._previous_closed())
        binding = target._record_bound_binding()
        self.assertFalse(
            binding["v24531_or_v24532_population_resume_retry_or_rerun"]
        )
        self.assertEqual(binding["prior_external_question_count"], 388)
        self.assertEqual(binding["prior_external_entity_count"], 3104)
        self.assertFalse(binding["new_population_reuses_prior_question_or_entity"])

    def test_build_parent_authorizes_protocol_design_only(self) -> None:
        value = target._parent(target.ROOT)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(
            value["authorization"][
                "fresh_disjoint_action_credit_external_protocol_design"
            ]
        )
        self.assertFalse(value["authorization"]["fresh_external_activation_or_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])

    def test_protocol_binds_action_capability_capacity_and_hard_gate(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        mechanism = value["mechanism"]
        self.assertEqual(
            mechanism["alias_acquisition_action_credit_policy"],
            target.action.POLICY_ID,
        )
        self.assertEqual(
            mechanism["proof_carrying_alias_acquisition_policy"],
            target.proof.POLICY_ID,
        )
        self.assertEqual(
            mechanism["total_alias_acquisition_projection_policy"],
            target.total.POLICY_ID,
        )
        self.assertTrue(
            mechanism[
                "action_credit_requires_target_plan_query_selection_new_observation_and_positive_posterior_delta"
            ]
        )
        self.assertTrue(mechanism["action_decision_credit_requires_safe_output_change"])
        self.assertFalse(
            mechanism[
                "same_run_action_credit_used_for_routing_training_or_policy_update"
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

    def test_protocol_contains_no_task_content_and_runtime_input_is_neutral(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        encoded = json.dumps(value, ensure_ascii=False)
        core = target._patched_core()
        for ordinal in range(1, 9):
            with target.configured_predecessor():
                task = target._base().neutral_task(ordinal)
            self.assertEqual(set(task), {"opaque_id", "question"})
            self.assertNotIn(task["opaque_id"], encoded)
            self.assertNotIn(task["question"], encoded)
        self.assertIs(core["run_targeted_worker"], target.proof.run_worker)
        self.assertIs(
            core["aggregate_projections"], target.aggregate_action_projections
        )

    def test_resealed_protocol_tamper_fails_closed(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        cases = (
            lambda item: item["record_bound_binding"].__setitem__(
                "v24531_or_v24532_population_resume_retry_or_rerun", True
            ),
            lambda item: item["mechanism"].__setitem__(
                "action_decision_credit_requires_safe_output_change", False
            ),
            lambda item: item["mechanism"].__setitem__(
                "same_run_action_credit_used_for_routing_training_or_policy_update",
                True,
            ),
            lambda item: item["task_contract"].__setitem__(
                "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_388_consumed_external_questions",
                False,
            ),
        )
        for alter in cases:
            changed = copy.deepcopy(value)
            alter(changed)
            reseal(changed, "protocol_payload_sha256")
            with self.assertRaises(RuntimeError):
                target.validate_protocol(value=changed)

    def test_mechanism_gate_requires_true_action_level_credit(self) -> None:
        value = passing_mechanism()
        self.assertTrue(target.mechanism_passed(value))
        for field in (
            "acquisition_plan_tasks",
            "acquisition_activity_tasks",
            "acquisition_selected_alias_title_hit_tasks",
            "acquisition_new_observation_tasks",
            "acquisition_positive_information_gain_tasks",
            "acquisition_positive_epistemic_credit_tasks",
            "acquisition_positive_decision_credit_tasks",
            "acquisition_safe_change_improvement_tasks",
        ):
            changed = copy.deepcopy(value)
            changed[field] = 0
            self.assertFalse(target.mechanism_passed(changed), field)
        changed = copy.deepcopy(value)
        changed["total_acquisition_action_number_fields"][
            "action_information_credit_nats"
        ] = 0.0
        self.assertFalse(target.mechanism_passed(changed))

    def test_regression_or_added_external_effect_fails_gate(self) -> None:
        value = passing_mechanism()
        for field in (
            "acquisition_safe_change_regression_tasks",
            "acquisition_decision_credit_regression_tasks",
        ):
            changed = copy.deepcopy(value)
            changed[field] = 1
            self.assertFalse(target.mechanism_passed(changed), field)
        changed = copy.deepcopy(value)
        changed["total_alias_stage_count_fields"]["additional_fetch_calls"] = 1
        self.assertFalse(target.mechanism_passed(changed))

    def test_diagnostic_route_resolves_exact_action_bottleneck(self) -> None:
        supervision = {"worker_hard_timeout_tasks": 0, "worker_nonzero_tasks": 0}
        value = passing_mechanism()
        self.assertEqual(
            target.diagnostic_route(
                value,
                supervision,
                diagnostic=True,
                reliability=True,
                parent_validation=True,
                latency=True,
            ),
            "fresh_paired_dev64_design",
        )
        changed = copy.deepcopy(value)
        changed["acquisition_new_observation_tasks"] = 0
        self.assertEqual(
            target.diagnostic_route(
                changed,
                supervision,
                diagnostic=False,
                reliability=True,
                parent_validation=True,
                latency=True,
            ),
            "targeted_observation_conversion_successor",
        )

    def test_capability_collector_is_one_shot_and_rejects_public_forgery(self) -> None:
        capability = object()
        success = {"ordinal": 1, "status": "validated_capability"}
        failure = {"ordinal": 2, "status": "failure_as_zero"}
        with (
            patch.object(
                target,
                "_ORIGINAL_TASK_PROJECTION",
                side_effect=lambda ordinal, _capability: {
                    "ordinal": ordinal,
                    "status": "validated_capability",
                },
            ),
            patch.object(
                target.total,
                "validate_total_row",
                side_effect=lambda value: dict(value),
            ),
            patch.object(
                target.total,
                "aggregate_projections",
                side_effect=lambda values, selected: {
                    "selected": selected,
                    "proof_input_count": len(values),
                },
            ),
        ):
            collector = target._CapabilityCollector()
            self.assertEqual(collector.project(1, capability), success)
            self.assertEqual(
                collector.aggregate([success, failure], selected=2),
                {"selected": 2, "proof_input_count": 2},
            )
            with self.assertRaises(RuntimeError):
                collector.aggregate([success, failure], selected=2)

    def test_bottom_level_run_probe_uses_action_aggregate_schema(self) -> None:
        """Exercise the real nested successor chain down to base.run_probe."""

        base = target._base()
        published: list[tuple[Path, dict]] = []

        def project(ordinal: int, _capability: object) -> dict:
            return {"ordinal": ordinal, "status": "validated_capability"}

        def run_one(
            _root: Path,
            _output_root: Path,
            _slots: Path,
            _directory: Path,
            _checkpoint: Path,
            ordinal: int,
        ) -> dict:
            collector = target._ACTIVE_COLLECTOR
            self.assertIsNotNone(collector)
            self.assertIs(
                base.run_targeted_worker,
                target.proof.run_worker,
            )
            self.assertIs(
                base.run_targeted_parent_with_separated_budget,
                target.proof.run_parent_with_separated_budget,
            )
            self.assertIs(
                base.aggregate_projections,
                target.aggregate_action_projections,
            )
            self.assertIs(
                base.validate_targeted_aggregate,
                target.total.validate_aggregate,
            )
            self.assertIs(base._mechanism_passed, target.mechanism_passed)
            return {
                "mechanism": target.total.task_projection(ordinal, object()),
                "observation": {},
                "timing": {},
                "supervision": {},
            }

        def aggregate_action(values: list[object], *, selected: int) -> dict:
            self.assertEqual(len(values), selected)
            self.assertEqual(selected, 8)
            return passing_mechanism()

        def validate_action(value: dict) -> dict:
            copied = copy.deepcopy(dict(value))
            self.assertTrue(
                target._REQUIRED_ACTION_AGGREGATE_KEYS.issubset(copied)
            )
            return copied

        def observation(_values: list[dict], *, selected: int) -> dict:
            return {
                "selected": selected,
                "slot_timeouts_lower_bound": 0,
                "provider_deadline_failures_lower_bound": 0,
                "hosted_search_deadline_failures_lower_bound": 0,
                "hard_fetch_deadline_failures_lower_bound": 0,
                "fetch_helper_failures_lower_bound": 0,
            }

        def timing(_values: list[dict], *, selected: int) -> dict:
            return {
                "selected": selected,
                "parent_success_tasks": selected,
                "certificate_validation_invocations": selected,
                "recursive_historical_semantic_replay_tasks": 0,
                "parent_certificate_validation_wall_p95_seconds": 0.01,
            }

        def supervision(_values: list[dict], *, selected: int) -> dict:
            return {
                "selected": selected,
                "worker_success_tasks": selected,
                "worker_hard_timeout_tasks": 0,
                "worker_nonzero_tasks": 0,
                "complete_validation_returned_tasks": selected,
                "worker_wall_max_seconds": 1.0,
            }

        @contextmanager
        def lease(*_args: object, **_kwargs: object):
            yield

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            temporary_root = Path(temporary).relative_to(ROOT)
            paths = {
                name: temporary_root / f"{name.lower()}.json"
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
                stack.enter_context(
                    patch.object(base, "_run_tests", return_value=tests)
                )
                stack.enter_context(
                    patch.object(base, "_all_sources_tracked", return_value=True)
                )
                stack.enter_context(
                    patch.object(base, "_port_listening", return_value=True)
                )
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
                activation = target.build_activation(now=0)
                write_json(ROOT / paths["ACTIVATION"], activation)
                start = target.build_execution_start(now=0)
                write_json(ROOT / paths["EXECUTION_START"], start)

                stack.enter_context(
                    patch.object(
                        target,
                        "_ORIGINAL_TASK_PROJECTION",
                        side_effect=project,
                    )
                )
                stack.enter_context(
                    patch.object(
                        target.total,
                        "validate_total_row",
                        side_effect=lambda value: dict(value),
                    )
                )
                stack.enter_context(
                    patch.object(
                        target.total,
                        "aggregate_projections",
                        side_effect=aggregate_action,
                    )
                )
                stack.enter_context(
                    patch.object(
                        target.total,
                        "validate_aggregate",
                        side_effect=validate_action,
                    )
                )
                stack.enter_context(patch.object(base, "_run_one", side_effect=run_one))
                stack.enter_context(
                    patch.object(base, "aggregate_observations", side_effect=observation)
                )
                stack.enter_context(
                    patch.object(base, "aggregate_stage_timings", side_effect=timing)
                )
                stack.enter_context(
                    patch.object(
                        base,
                        "aggregate_supervision_receipts",
                        side_effect=supervision,
                    )
                )
                stack.enter_context(
                    patch.object(
                        base,
                        "validate_observation_aggregate",
                        side_effect=lambda value, expected_selected: dict(value),
                    )
                )
                stack.enter_context(
                    patch.object(
                        base,
                        "validate_stage_timing_aggregate",
                        side_effect=lambda value: dict(value),
                    )
                )
                stack.enter_context(
                    patch.object(
                        base,
                        "validate_supervision_aggregate",
                        side_effect=lambda value: dict(value),
                    )
                )
                stack.enter_context(patch.object(base, "_git_ready", return_value=True))
                stack.enter_context(
                    patch.object(base, "acquire_deepwide_api_lease", lease)
                )
                stack.enter_context(
                    patch.object(
                        base,
                        "publish",
                        side_effect=lambda path, value: published.append(
                            (path, copy.deepcopy(value))
                        ),
                    )
                )
                value = target.run_probe()

        mechanism = value["mechanism_aggregate"]
        self.assertIn("acquisition_plan_tasks", mechanism)
        self.assertIn("total_acquisition_action_count_fields", mechanism)
        self.assertIn("total_acquisition_action_number_fields", mechanism)
        self.assertEqual(len(published), 1)

    def test_public_result_rejects_legacy_alias_aggregate_schema(self) -> None:
        legacy = {
            "mechanism_aggregate": legacy_alias_mechanism(),
        }
        with (
            patch.object(
                target,
                "_BASE_VALIDATE_PUBLIC_RESULT",
                side_effect=lambda value: dict(value),
            ),
            self.assertRaisesRegex(RuntimeError, "action aggregate schema is absent"),
        ):
            target.validate_public_result(legacy)

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
        self.assertEqual(preaudit["checks"]["focused_tests"]["test_count"], 159)
        self.assertFalse(start["benchmark_or_evaluator_authorized"])

    def test_worker_and_supervisor_cli_bind_action_runtime(self) -> None:
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
            self.assertTrue(receipt["validator_context_passed"])
            self.assertFalse(receipt["network_model_search_fetch_or_evaluator_called"])

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
            Path("scripts/v24537_alias_action_credit_external_gate.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--cli-validator-smoke":
        raise SystemExit(cli_validator_smoke(sys.argv[2]))
    unittest.main()
