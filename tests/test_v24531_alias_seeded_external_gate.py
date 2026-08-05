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
from scripts import v24531_alias_seeded_external_gate as target  # noqa: E402


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
        "alias_anchor_tasks": 1,
        "alias_observation_tasks": 1,
        "alias_added_observation_tasks": 1,
        "alias_safe_change_improvement_tasks": 1,
        "alias_safe_change_regression_tasks": 0,
        "alias_positive_information_gain_tasks": 1,
        "alias_epistemic_credit_gain_tasks": 1,
        "alias_decision_credit_gain_tasks": 1,
        "alias_decision_credit_regression_tasks": 0,
        "alias_terminal_safe_change_tasks": 1,
        "total_alias_stage_count_fields": {
            "additional_model_requests": 0,
            "additional_logical_queries": 0,
            "additional_search_batches": 0,
            "additional_provider_search_calls": 0,
            "additional_fetch_calls": 0,
        },
        "total_alias_stage_number_fields": {
            "positive_information_gain_gain_nats": 0.5,
            "epistemic_credit_gain_nats": 0.4,
            "decision_credit_gain_nats": 0.3,
            "decision_credit_regression_nats": 0.0,
        },
        "all_alias_success_rows_consumed_validated_capabilities": True,
        "all_alias_failure_rows_are_content_free_zero_projections": True,
        "alias_failure_rows_claim_zero_private_effects": False,
        "alias_private_task_content_emitted": False,
        "alias_privileged_evaluator_content_read": False,
    }


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
            or core["run_targeted_worker"]
            is not target.seeded.run_alias_seeded_worker
            or core["run_targeted_parent_with_separated_budget"]
            is not target.seeded.run_alias_seeded_parent_with_separated_budget
            or base.run_targeted_worker
            is not target.seeded.run_alias_seeded_worker
            or base.run_targeted_parent_with_separated_budget
            is not target.seeded.run_alias_seeded_parent_with_separated_budget
            or base.aggregate_projections
            is not target.predecessor.aggregate_alias_projections
        ):
            raise RuntimeError("V2.45.31 CLI validator context is incomplete")
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


class V24531AliasSeededExternalGateTests(unittest.TestCase):
    def test_population_is_fresh_and_alias_surfaces_are_rule_unique(self) -> None:
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertTrue(target._alias_surface_vector_valid())
        self.assertEqual(len(target._prior_questions()), 372)
        self.assertEqual(len(target.QUESTIONS), 8)
        self.assertEqual(sum(map(len, target.ENTITY_GROUPS)), 64)

    def test_v24528_no_go_is_closed_and_population_never_rerun(self) -> None:
        self.assertTrue(target._previous_closed())
        binding = target._record_bound_binding()
        self.assertFalse(binding["v24528_population_rerun"])
        self.assertEqual(binding["prior_external_question_count"], 372)
        self.assertEqual(binding["prior_external_entity_count"], 2976)
        self.assertFalse(binding["new_population_reuses_prior_question_or_entity"])

    def test_parent_is_valid_and_authorizes_design_only(self) -> None:
        value = target._parent(target.ROOT)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["label_blind_audit"]["passed"])
        self.assertTrue(
            value["authorization"][
                "fresh_disjoint_alias_seeded_external_protocol_design"
            ]
        )
        self.assertFalse(
            value["authorization"]["fresh_external_activation_or_launch"]
        )
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])

    def test_protocol_binds_seeded_worker_capacity_and_hard_go_gate(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        mechanism = value["mechanism"]
        self.assertEqual(
            mechanism["alias_seeded_target_acquisition_policy"],
            target.acquisition.POLICY_ID,
        )
        self.assertEqual(
            mechanism["alias_seeded_bounded_worker_policy"],
            target.seeded.POLICY_ID,
        )
        self.assertEqual(mechanism["targeted_parent_policy"], target.seeded.POLICY_ID)
        self.assertTrue(mechanism["alias_seed_derived_only_from_visible_row_text"])
        self.assertTrue(
            mechanism[
                "visible_title_alias_hit_priority_before_frozen_target_coverage_order"
            ]
        )
        self.assertFalse(
            mechanism["alias_hint_receives_vote_source_entropy_or_decision_credit"]
        )
        self.assertFalse(mechanism["logical_query_search_batch_and_fetch_caps_changed"])
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
        self.assertFalse(value["authorization"]["external_probe_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])

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
        self.assertIs(
            core["run_targeted_worker"], target.seeded.run_alias_seeded_worker
        )

    def test_resealed_protocol_tamper_fails_closed(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        cases = (
            lambda item: item["record_bound_binding"].__setitem__(
                "v24528_population_rerun", True
            ),
            lambda item: item["mechanism"].__setitem__(
                "alias_hint_receives_vote_source_entropy_or_decision_credit", True
            ),
            lambda item: item["mechanism"].__setitem__(
                "logical_query_search_batch_and_fetch_caps_changed", True
            ),
            lambda item: item["task_contract"].__setitem__(
                "all_64_preregistered_alias_title_surfaces_uniquely_match_under_frozen_rule",
                False,
            ),
        )
        for alter in cases:
            changed = copy.deepcopy(value)
            alter(changed)
            reseal(changed, "protocol_payload_sha256")
            with self.assertRaises(RuntimeError):
                target.validate_protocol(value=changed)

    def test_mechanism_gate_requires_alias_entropy_and_decision_credit(self) -> None:
        value = passing_mechanism()
        self.assertTrue(target.mechanism_passed(value))
        for field in (
            "success_tasks",
            "alias_anchor_tasks",
            "alias_observation_tasks",
            "alias_added_observation_tasks",
            "alias_safe_change_improvement_tasks",
            "alias_positive_information_gain_tasks",
            "alias_epistemic_credit_gain_tasks",
            "alias_decision_credit_gain_tasks",
        ):
            changed = copy.deepcopy(value)
            changed[field] = 7 if field == "success_tasks" else 0
            self.assertFalse(target.mechanism_passed(changed), field)
        changed = copy.deepcopy(value)
        changed["alias_safe_change_regression_tasks"] = 1
        self.assertFalse(target.mechanism_passed(changed))
        changed = copy.deepcopy(value)
        changed["total_alias_stage_count_fields"]["additional_fetch_calls"] = 1
        self.assertFalse(target.mechanism_passed(changed))

    def test_diagnostic_route_orders_alias_failure_stages(self) -> None:
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
        changed["alias_anchor_tasks"] = 0
        self.assertEqual(
            target.diagnostic_route(
                changed,
                supervision,
                diagnostic=False,
                reliability=True,
                parent_validation=True,
                latency=True,
            ),
            "alias_source_title_coverage_successor",
        )

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
        self.assertEqual(preaudit["checks"]["focused_tests"]["test_count"], 99)
        self.assertFalse(start["benchmark_or_evaluator_authorized"])

    def test_worker_and_supervisor_cli_bind_seeded_runtime(self) -> None:
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
            Path("scripts/v24531_alias_seeded_external_gate.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--cli-validator-smoke":
        raise SystemExit(cli_validator_smoke(sys.argv[2]))
    unittest.main()
