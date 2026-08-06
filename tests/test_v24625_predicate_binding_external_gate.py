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
from scripts import v24625_predicate_binding_external_gate as target  # noqa: E402


def reseal(value: dict, field: str) -> None:
    value.pop(field, None)
    value[field] = payload_sha256(value)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def build_protocol(*, now: int = 0) -> dict:
    return target.build_protocol(
        now=now, require_pristine=False, require_build_audit=False
    )


def synthetic_mechanism_aggregate() -> dict:
    from test_v24607_proof_carrying_title_provenance import populate, validate

    with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
        root = Path(directory)
        populate(root)
        capability = validate(root)
        receipt = capability.content_free_title_provenance_receipt()
        receipt["provider_response_count"] = 1
        capability = (
            target.proof.ValidatedProofCarryingContentFreeTitleProvenance._create(
                parent=capability.parent_capability(), receipt=receipt
            )
        )
        with target.collector.capability_collection():
            rows = [
                target.total.task_projection(ordinal, capability)
                for ordinal in range(1, 9)
            ]
            return target.collector.aggregate_projections(rows, selected=8)


def synthetic_public_result(mechanism: dict) -> dict:
    value = json.loads(
        (ROOT / target.SYNTHETIC_RESULT_TEMPLATE).read_text(encoding="utf-8")
    )
    value["protocol_id"] = target.PROTOCOL_ID
    value["mechanism_aggregate"] = copy.deepcopy(mechanism)
    value["mechanism_passed"] = target.mechanism_passed(mechanism)
    value["passed"] = (
        value["mechanism_passed"]
        and value["reliability_passed"]
        and value["parent_validation_passed"]
        and value["latency_passed"]
    )
    value["runtime_fast_control_validation_passed"] = True
    value["runtime_complete_protocol_revalidation_per_task"] = False
    value["batch_watchdog_receipt"] = {
        "policy_id": target.watchdog.POLICY_ID,
        "timeout_seconds": 255.0,
        "started": True,
        "closed": True,
        "triggered": False,
        "signal_failure_count": 0,
        "process_identifier_or_command_line_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    reseal(value, "result_payload_sha256")
    return value


def cli_validator_smoke(command: str) -> int:
    protocol = build_protocol()

    def validate_in_process(args: argparse.Namespace) -> None:
        validated = target.validate_runtime_protocol()
        if (
            validated["protocol_id"] != target.PROTOCOL_ID
            or target.frozen.PROTOCOL_ID != target.PROTOCOL_ID
            or target.controller.PROTOCOL_ID != target.PROTOCOL_ID
            or target.controller.proof is not target.proof
            or target.runtime.proof is not target.proof
            or target.runtime.total is not target.total
            or target.runtime.bounded is not target.bounded
            or target.base.run_targeted_worker is not target.bounded.run_worker
            or target.base.run_targeted_parent_with_separated_budget
            is not target.bounded.run_parent_with_separated_budget
            or target.base._mechanism_passed is not target.mechanism_passed
            or target.controller.mechanism_passed is not target.mechanism_passed
            or not target.binding.invariant_valid()
            or not target.collector.binding_valid()
        ):
            raise RuntimeError("V2.46.25 CLI execution context is incomplete")
        print(
            json.dumps(
                {
                    "command": args.command,
                    "protocol_id": validated["protocol_id"],
                    "finite_predicate_runtime_context_passed": True,
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
        paths = {
            name: root / f"{name.lower()}.json"
            for name in ("PROTOCOL", "PREAUDIT", "ACTIVATION", "EXECUTION_START")
        }
        write_json(ROOT / paths["PROTOCOL"], protocol)
        preaudit = {"protocol_id": target.PROTOCOL_ID, "audit_valid": True}
        reseal(preaudit, "audit_payload_sha256")
        write_json(ROOT / paths["PREAUDIT"], preaudit)
        activation = {
            "protocol_id": target.PROTOCOL_ID,
            "protocol_sha256": target.sha256(ROOT / paths["PROTOCOL"]),
            "preactivation_audit_sha256": target.sha256(ROOT / paths["PREAUDIT"]),
            "surface_manifest_sha256": protocol["surface_manifest_sha256"],
            "launch_authorized": True,
        }
        reseal(activation, "activation_payload_sha256")
        write_json(ROOT / paths["ACTIVATION"], activation)
        start = {
            "protocol_id": target.PROTOCOL_ID,
            "protocol_sha256": target.sha256(ROOT / paths["PROTOCOL"]),
            "activation_sha256": target.sha256(ROOT / paths["ACTIVATION"]),
            "selected": 8,
            "executor_count": 8,
            "model_slot_cap": 2,
            "execution_authorized": True,
            "benchmark_or_evaluator_authorized": False,
        }
        reseal(start, "execution_start_payload_sha256")
        write_json(ROOT / paths["EXECUTION_START"], start)
        try:
            target.base._worker = validate_in_process
            target.base._supervisor = validate_in_process
            sys.argv = [str(ROOT / target.RUNNER_MARKER), command]
            with ExitStack() as stack:
                for name, path in paths.items():
                    stack.enter_context(patch.object(target, name, path))
                target.main()
        finally:
            sys.argv = original_argv
            target.base._worker, target.base._supervisor = (
                original_worker,
                original_supervisor,
            )
    return 0


class V24625PredicateBindingExternalGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.aggregate = synthetic_mechanism_aggregate()

    def test_population_is_fresh_and_query_surfaces_are_reachable(self) -> None:
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertTrue(target._title_query_surface_vector_valid())
        self.assertEqual(len(target._prior_questions()), 516)
        self.assertEqual(len(target.QUESTIONS), 8)
        self.assertEqual(sum(map(len, target.ENTITY_GROUPS)), 64)
        self.assertEqual(
            len(
                {
                    target.acquisition.primary_alias_surface(entity).casefold()
                    for group in target.ENTITY_GROUPS
                    for entity in group
                }
            ),
            64,
        )

    def test_v24622_is_terminal_consumed_and_nonretryable(self) -> None:
        self.assertTrue(target._previous_closed())
        failure = target._read(target.PREVIOUS_FAILURE)
        self.assertTrue(failure["external_population_consumed"])
        self.assertEqual(failure["external_wave_count"], 1)
        self.assertTrue(failure["collector_context_covered_task_and_aggregate_lifetime"])
        self.assertEqual(
            failure["failure_class"], "self_referential_mechanism_predicate_binding"
        )
        self.assertFalse(
            failure["authorization"]["same_population_retry_resume_or_evaluation"]
        )

    def test_protocol_adds_only_predicate_binding_repair(self) -> None:
        value = build_protocol()
        mechanism = value["mechanism"]
        self.assertEqual(
            mechanism["mechanism_predicate_binding_repair_policy"],
            target.PREDICATE_POLICY_ID,
        )
        self.assertTrue(
            mechanism["predicate_baseline_is_import_time_v24604_title_funnel_gate"]
        )
        self.assertTrue(mechanism["predicate_provenance_tail_is_unchanged_v24616_gate"])
        self.assertTrue(mechanism["runtime_base_and_controller_use_same_safe_predicate"])
        self.assertTrue(mechanism["dynamic_controller_predicate_read_removed"])
        self.assertTrue(mechanism["collector_context_enters_before_task_futures"])
        self.assertTrue(mechanism["maximum_batch_wall_is_enforcing_watchdog"])

    def test_protocol_preserves_budget_and_does_not_authorize_launch(self) -> None:
        value = build_protocol()
        self.assertEqual(
            [
                value["budget"]["effect_deadline_seconds"],
                value["budget"]["worker_timeout_seconds"],
                value["budget"]["parent_timeout_seconds"],
                value["budget"]["maximum_batch_wall_seconds"],
                value["budget"]["maximum_targeted_search_batches_per_task"],
                value["budget"]["maximum_targeted_logical_queries_per_task"],
                value["budget"]["maximum_targeted_fetches_per_task"],
            ],
            [150.0, 220.0, 245.0, 255.0, 1, 2, 3],
        )
        self.assertFalse(value["authorization"]["external_probe_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])
        self.assertFalse(value["authorization"]["evaluator"])

    def test_resealed_protocol_tamper_fails_closed(self) -> None:
        value = build_protocol()
        for field in (
            "predicate_baseline_is_import_time_v24604_title_funnel_gate",
            "predicate_provenance_tail_is_unchanged_v24616_gate",
            "runtime_base_and_controller_use_same_safe_predicate",
            "dynamic_controller_predicate_read_removed",
        ):
            changed = copy.deepcopy(value)
            changed["mechanism"][field] = False
            reseal(changed, "protocol_payload_sha256")
            with self.assertRaises(RuntimeError):
                target.validate_protocol(value=changed, require_build_audit=False)

    def test_predicate_binding_is_frozen_by_function_identity(self) -> None:
        self.assertTrue(target._predicate_binding_valid())
        self.assertIsNot(
            target._FROZEN_V24604_BASELINE_PREDICATE,
            target._FAILED_V24616_DYNAMIC_PREDICATE,
        )
        self.assertNotIn("controller", target.mechanism_passed.__code__.co_names)

    def test_safe_predicate_terminates_on_real_synthetic_aggregate(self) -> None:
        self.assertTrue(target.mechanism_passed(self.aggregate))
        changed = copy.deepcopy(self.aggregate)
        changed["content_free_title_provenance_provider_activity_tasks"] = 0
        self.assertFalse(target.mechanism_passed(changed))
        changed = copy.deepcopy(self.aggregate)
        changed["content_free_title_funnel_activity_tasks"] = 0
        self.assertFalse(target.mechanism_passed(changed))

    def test_safe_predicate_is_exact_old_gate_with_frozen_baseline(self) -> None:
        cases = [copy.deepcopy(self.aggregate)]
        for field, changed_value in (
            ("content_free_title_provenance_provider_activity_tasks", 0),
            (
                "all_content_free_title_provenance_success_rows_consumed_validated_capabilities",
                False,
            ),
            ("content_free_title_provenance_private_content_emitted", True),
            ("content_free_title_funnel_activity_tasks", 0),
        ):
            changed = copy.deepcopy(self.aggregate)
            changed[field] = changed_value
            cases.append(changed)
        with patch.object(
            target.controller,
            "mechanism_passed",
            target._FROZEN_V24604_BASELINE_PREDICATE,
        ):
            self.assertEqual(
                [target.mechanism_passed(value) for value in cases],
                [target._FAILED_V24616_DYNAMIC_PREDICATE(value) for value in cases],
            )

    def test_runtime_stack_installs_safe_predicate_and_restores_identity(self) -> None:
        before_base = target.base._mechanism_passed
        before_controller = target.controller.mechanism_passed
        with target.configured_runtime_stack():
            self.assertIs(target.base._mechanism_passed, target.mechanism_passed)
            self.assertIs(target.controller.mechanism_passed, target.mechanism_passed)
            self.assertTrue(target.base._mechanism_passed(self.aggregate))
        self.assertIs(target.base._mechanism_passed, before_base)
        self.assertIs(target.controller.mechanism_passed, before_controller)

    def test_nested_public_result_validator_keeps_safe_predicate(self) -> None:
        value = synthetic_public_result(self.aggregate)
        validated = target.validate_public_result(value)
        self.assertTrue(validated["mechanism_passed"])
        self.assertTrue(validated["passed"])
        self.assertIs(
            target.controller.mechanism_passed,
            target._FROZEN_V24604_BASELINE_PREDICATE,
        )

    def test_run_probe_wraps_fast_loop_with_collector_and_safe_predicate(self) -> None:
        protocol = {"protocol_id": target.PROTOCOL_ID}
        activation = {"launch_authorized": True}
        control = {"runtime_input_keys": ["opaque_id", "question"]}
        state = {"runtime": False, "collector": False}

        from contextlib import contextmanager

        @contextmanager
        def runtime():
            state["runtime"] = True
            try:
                yield
            finally:
                state["runtime"] = False

        @contextmanager
        def collection():
            state["collector"] = True
            try:
                yield
            finally:
                state["collector"] = False

        def fast(**_kwargs):
            self.assertTrue(state["runtime"])
            self.assertTrue(state["collector"])
            return {"ok": True}

        with (
            patch.object(target, "validate_protocol", return_value=protocol),
            patch.object(target, "validate_preaudit", return_value={}),
            patch.object(target, "validate_activation", return_value=activation),
            patch.object(target, "validate_execution_start", return_value={}),
            patch.object(target, "_control_receipt", return_value=control),
            patch.object(target, "validate_runtime_control_receipt", return_value=control),
            patch.object(target, "configured_runtime_stack", side_effect=runtime),
            patch.object(target.collector, "capability_collection", side_effect=collection),
            patch.object(target, "_BASE_RUN_PROBE_FAST", side_effect=fast),
        ):
            self.assertEqual(target.run_probe(), {"ok": True})
        self.assertFalse(state["runtime"])
        self.assertFalse(state["collector"])

    def test_runtime_and_collector_exit_on_fast_loop_exception(self) -> None:
        state = {"runtime": False, "collector": False}
        from contextlib import contextmanager

        @contextmanager
        def runtime():
            state["runtime"] = True
            try:
                yield
            finally:
                state["runtime"] = False

        @contextmanager
        def collection():
            state["collector"] = True
            try:
                yield
            finally:
                state["collector"] = False

        with (
            patch.object(target, "validate_protocol", return_value={}),
            patch.object(target, "validate_preaudit", return_value={}),
            patch.object(target, "validate_activation", return_value={}),
            patch.object(target, "validate_execution_start", return_value={}),
            patch.object(target, "_control_receipt", return_value={}),
            patch.object(target, "validate_runtime_control_receipt", return_value={}),
            patch.object(target, "configured_runtime_stack", side_effect=runtime),
            patch.object(target.collector, "capability_collection", side_effect=collection),
            patch.object(target, "_BASE_RUN_PROBE_FAST", side_effect=RuntimeError("stop")),
        ):
            with self.assertRaisesRegex(RuntimeError, "stop"):
                target.run_probe()
        self.assertFalse(state["runtime"])
        self.assertFalse(state["collector"])

    def test_runtime_input_remains_opaque_id_and_question(self) -> None:
        value = build_protocol()
        encoded = json.dumps(value, ensure_ascii=False)
        with target.configured_frozen(), target.frozen.configured_frozen(), target.frozen.frozen.configured_controller(
            protocol_compatibility=False
        ), target.runtime.configured_base(validators=False):
            for ordinal in range(1, 9):
                task = target.base.neutral_task(ordinal)
                self.assertEqual(set(task), {"opaque_id", "question"})
                self.assertNotIn(task["opaque_id"], encoded)
                self.assertNotIn(task["question"], encoded)

    def test_build_preaudit_chain_with_synthetic_tests(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            root = Path(directory).relative_to(ROOT)
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
            original_validate_protocol = target.validate_protocol
            with ExitStack() as stack:
                for name, path in paths.items():
                    stack.enter_context(patch.object(target, name, path))
                protocol = build_protocol()
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
                for name, value in (
                    ("_run_tests", tests),
                    ("_all_sources_tracked", True),
                    ("_port_listening", True),
                    ("_future", True),
                ):
                    stack.enter_context(
                        patch.object(target.base, name, return_value=value)
                    )
                stack.enter_context(
                    patch.object(
                        target.base, "lease_observation", return_value={"active": False}
                    )
                )
                stack.enter_context(
                    patch.object(
                        target.base,
                        "_git",
                        side_effect=lambda _root, *args: ""
                        if args == ("status", "--porcelain")
                        else "a" * 40,
                    )
                )
                stack.enter_context(
                    patch.object(
                        target,
                        "validate_protocol",
                        side_effect=lambda *args, **kwargs: original_validate_protocol(
                            *args, **kwargs, require_build_audit=False
                        ),
                    )
                )
                preaudit = target.build_preaudit(now=0)
        self.assertTrue(preaudit["audit_valid"])
        self.assertTrue(
            preaudit["checks"]
            ["v24625_runtime_predicate_binding_is_finite_and_nonrecursive"]
        )

    def test_worker_and_supervisor_cli_bind_safe_predicate_runtime(self) -> None:
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
            self.assertTrue(receipt["finite_predicate_runtime_context_passed"])
            self.assertFalse(
                receipt["network_model_search_fetch_or_evaluator_called"]
            )

    def test_protocol_requires_sealed_build_audit_by_default(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            missing = Path(directory).relative_to(ROOT) / "missing-build-audit.json"
            with patch.object(target, "BUILD_AUDIT", missing):
                with self.assertRaises((FileNotFoundError, RuntimeError)):
                    target.build_protocol(now=0, require_pristine=False)

    def test_protocol_rejects_build_audit_without_complete_tests(self) -> None:
        audit = {
            "role": "v24626_predicate_binding_build_audit",
            "audit_valid": True,
            "findings": [],
            "authorization": {
                "v24625_protocol_publication": True,
                "fresh_external_activation_or_launch": False,
            },
            "label_blind_audit": {"passed": True},
            "tests": {
                "passed": True,
                "test_count": 37,
                "network_model_search_fetch_or_evaluator_called": False,
            },
            "predicate_binding_repair": {
                "policy": target.PREDICATE_POLICY_ID,
                "frozen_v24604_baseline": True,
                "unchanged_v24616_provenance_tail": True,
                "direct_and_nested_runtime_predicate_tested": True,
                "design_valid": True,
            },
            "runtime_state": {
                "benchmark_launched": False,
                "external_population_launched_by_audit": False,
                "evaluator_called": False,
                "shared_api_lease_inactive": True,
                "future_surface_pristine": True,
            },
            "git": {
                "head": "a" * 40,
                "target_main": "a" * 40,
                "head_equals_target_main": True,
                "worktree_clean": True,
                "all_sources_tracked": True,
            },
            "source_manifest": {},
            "source_manifest_sha256": payload_sha256({}),
        }
        reseal(audit, "audit_payload_sha256")
        with patch.object(target, "_read", return_value=audit):
            with self.assertRaisesRegex(RuntimeError, "build audit drifted"):
                target._validated_build_audit()

    def test_runtime_source_is_label_blind_and_secret_free(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        path = Path("scripts/v24625_predicate_binding_external_gate.py")
        accesses, imports = audit.ast_findings(path)
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])
        self.assertIsNone(audit.SECRET.search((ROOT / path).read_text(encoding="utf-8")))

    def test_source_contains_no_proof_total_runtime_or_baseline_mutation(self) -> None:
        source = (ROOT / target.RUNNER_MARKER).read_text(encoding="utf-8")
        tree = ast.parse(source)
        writes = []
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for item in targets:
                if isinstance(item, ast.Attribute) and isinstance(item.value, ast.Name):
                    if item.value.id in {"proof", "total", "runtime", "controller", "base"}:
                        writes.append((item.value.id, item.attr, item.lineno))
        self.assertEqual(writes, [])

    def test_decision_and_evaluator_remain_unauthorized(self) -> None:
        authorization = target._protocol_authorization()
        self.assertFalse(authorization["paired_dev64_or_exact220"])
        self.assertFalse(authorization["evaluator"])
        self.assertFalse(authorization["leaderboard_or_sota"])

    def test_successor_decision_and_postaudit_roles_are_specific(self) -> None:
        source = (ROOT / target.RUNNER_MARKER).read_text(encoding="utf-8")
        self.assertIn(target.DECISION_ROLE, source)
        self.assertIn(target.POSTAUDIT_ROLE, source)
        self.assertNotIn(
            '"role": "v24622_collector_lifetime_external_decision"', source
        )
        self.assertNotIn(
            '"role": "v24622_collector_lifetime_external_postresult_audit"', source
        )

    def test_configured_frozen_restores_after_exception(self) -> None:
        before = target.frozen.PROTOCOL_ID
        with self.assertRaisesRegex(RuntimeError, "synthetic"):
            with target.configured_frozen():
                self.assertEqual(target.frozen.PROTOCOL_ID, target.PROTOCOL_ID)
                raise RuntimeError("synthetic")
        self.assertEqual(target.frozen.PROTOCOL_ID, before)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--cli-validator-smoke":
        raise SystemExit(cli_validator_smoke(sys.argv[2]))
    unittest.main()
