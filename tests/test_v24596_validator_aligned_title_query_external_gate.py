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
from scripts import v24596_validator_aligned_title_query_external_gate as target  # noqa: E402
from test_v24590_proof_carrying_validator_aligned_title_query import (  # noqa: E402
    populate,
    validate,
)


def reseal(value: dict, field: str) -> None:
    value.pop(field, None)
    value[field] = payload_sha256(value)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def cli_validator_smoke(command: str) -> int:
    protocol = target.build_protocol(now=0, require_pristine=False)

    def validate_in_process(args: argparse.Namespace) -> None:
        validated = target.validate_protocol(value=protocol)
        if (
            validated["protocol_id"] != target.PROTOCOL_ID
            or target.previous.PROTOCOL_ID != target.PROTOCOL_ID
            or target.runtime.PROTOCOL_ID != target.PROTOCOL_ID
            or target.base.PROTOCOL_ID != target.PROTOCOL_ID
            or target.runtime.proof is not target.proof
            or target.runtime.total is not target.total
            or target.runtime.bounded is not target.bounded
            or target.runtime.capability_collection
            is not target.collector_repair.capability_collection
            or target.runtime.aggregate_strict_projections
            is not target.collector_repair.aggregate_projections
            or target.base.run_targeted_worker is not target.bounded.run_worker
            or target.base.run_targeted_parent_with_separated_budget
            is not target.bounded.run_parent_with_separated_budget
            or target.base.aggregate_projections
            is not target.collector_repair.aggregate_projections
            or target.base.validate_targeted_aggregate
            is not target.total.validate_aggregate
            or target.runtime._ORIGINAL_TASK_PROJECTION
            is not target._INHERITED_ORIGINAL_TASK_PROJECTION
        ):
            raise RuntimeError("V2.45.96 CLI execution context is incomplete")
        print(
            json.dumps(
                {
                    "command": args.command,
                    "protocol_id": validated["protocol_id"],
                    "immutable_collector_context_passed": True,
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
        target.base._worker, target.base._supervisor = (
            original_worker,
            original_supervisor,
        )
    return 0


class V24596ValidatorAlignedTitleQueryExternalGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        cls.root = Path(cls.temporary.name)
        populate(cls.root)
        cls.capability = validate(cls.root)
        cls.passing = target.total.aggregate_projections(
            [cls.capability] * 8, selected=8
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_population_is_fresh_and_both_query_surfaces_are_reachable(self) -> None:
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertTrue(target._title_query_surface_vector_valid())
        self.assertTrue(target._alias_surface_vector_valid())
        self.assertEqual(len(target._prior_questions()), 468)
        self.assertEqual(len(target.QUESTIONS), 8)
        self.assertEqual(sum(map(len, target.ENTITY_GROUPS)), 64)
        surfaces = [
            target.acquisition.primary_alias_surface(entity)
            for group in target.ENTITY_GROUPS
            for entity in group
        ]
        self.assertEqual(sum(value is not None for value in surfaces), 64)
        self.assertEqual(len({value.casefold() for value in surfaces if value}), 64)

    def test_v24587_is_closed_and_v24595_authorizes_design_only(self) -> None:
        self.assertTrue(target._previous_closed())
        parent = target._parent(target.ROOT)
        self.assertTrue(parent["audit_valid"])
        self.assertEqual(parent["tests"]["test_count"], 49)
        self.assertEqual(parent["repair"]["stress"]["validations"], 8)
        self.assertTrue(
            parent["authorization"][
                "fresh_disjoint_validator_aligned_title_query_external_protocol_design"
            ]
        )
        self.assertFalse(parent["authorization"]["fresh_external_activation_or_launch"])

    def test_protocol_binds_title_query_chain_and_preserves_budget(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        mechanism = value["mechanism"]
        self.assertEqual(mechanism["targeted_proof_policy"], target.proof.POLICY_ID)
        self.assertEqual(mechanism["targeted_parent_policy"], target.bounded.POLICY_ID)
        self.assertEqual(
            mechanism["validator_aligned_title_query_policy"],
            target.query_policy.POLICY_ID,
        )
        self.assertEqual(
            mechanism["immutable_title_query_collector_policy"],
            target.collector_repair.POLICY_ID,
        )
        self.assertTrue(
            mechanism["collector_projector_is_module_load_unbound_v24591_function"]
        )
        self.assertFalse(
            mechanism["controller_rebinds_inherited_original_task_projection"]
        )
        self.assertFalse(
            mechanism[
                "logical_query_search_batch_fetch_page_source_or_model_budget_changed"
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
        self.assertEqual(value["budget"]["maximum_targeted_logical_queries_per_task"], 2)
        self.assertEqual(value["budget"]["maximum_targeted_fetches_per_task"], 3)

    def test_protocol_contains_no_task_content_and_runtime_input_is_neutral(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        encoded = json.dumps(value, ensure_ascii=False)
        with target.configured_previous(), target.runtime.configured_base(
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
                "new_population_reuses_prior_question_or_entity", True
            ),
            lambda item: item["mechanism"].__setitem__(
                "collector_projector_is_module_load_unbound_v24591_function", False
            ),
            lambda item: item["mechanism"].__setitem__(
                "controller_rebinds_inherited_original_task_projection", True
            ),
            lambda item: item["task_contract"].__setitem__(
                "all_64_full_surfaces_uniquely_reachable_by_unchanged_exact_title_parent",
                False,
            ),
        )
        for alter in cases:
            changed = copy.deepcopy(value)
            alter(changed)
            reseal(changed, "protocol_payload_sha256")
            with self.assertRaises(RuntimeError):
                target.validate_protocol(value=changed)

    def test_mechanism_requires_title_query_activity_and_replacement(self) -> None:
        cases = (
            (
                "validator_aligned_title_query_activity_tasks",
                "validator_aligned_title_query_runtime_successor",
            ),
            (
                "validator_aligned_title_query_full_surface_tasks",
                "validator_aligned_full_surface_successor",
            ),
            (
                "validator_aligned_title_query_and_title_replacement_cooccurrence_tasks",
                "validator_aligned_title_acquisition_successor",
            ),
        )
        with patch.object(
            target, "_INHERITED_MECHANISM_PASSED", return_value=True
        ):
            self.assertTrue(target.mechanism_passed(self.passing))
            for field, route in cases:
                with self.subTest(field=field):
                    changed = copy.deepcopy(self.passing)
                    changed[field] = 0
                    self.assertFalse(target.mechanism_passed(changed))
                    self.assertEqual(
                        target.diagnostic_route(
                            changed,
                            {
                                "worker_hard_timeout_tasks": 0,
                                "worker_nonzero_tasks": 0,
                            },
                            diagnostic=False,
                            reliability=True,
                            parent_validation=True,
                            latency=True,
                        ),
                        route,
                    )

    def test_real_collector_projects_and_aggregates_eight_capabilities(self) -> None:
        before = target.runtime._ORIGINAL_TASK_PROJECTION
        with target.configured_previous():
            self.assertIs(
                target.runtime.capability_collection,
                target.collector_repair.capability_collection,
            )
            with target.runtime.capability_collection():
                rows = [
                    target.total.task_projection(ordinal, self.capability)
                    for ordinal in range(1, 9)
                ]
                value = target.runtime.aggregate_strict_projections(rows, selected=8)
        self.assertIs(target.runtime._ORIGINAL_TASK_PROJECTION, before)
        self.assertEqual(value["success_tasks"], 8)
        self.assertEqual(value["failure_as_zero_tasks"], 0)
        self.assertEqual(value["validator_aligned_title_query_activity_tasks"], 8)
        self.assertEqual(value["validator_aligned_title_query_full_surface_tasks"], 8)

    def test_run_probe_wraps_parent_in_title_query_collector_context(self) -> None:
        before = target.runtime._ORIGINAL_TASK_PROJECTION

        def fake_probe() -> dict:
            self.assertIs(
                target.runtime.capability_collection,
                target.collector_repair.capability_collection,
            )
            self.assertIs(
                target.runtime.aggregate_strict_projections,
                target.collector_repair.aggregate_projections,
            )
            self.assertIs(target.runtime._ORIGINAL_TASK_PROJECTION, before)
            return {"wrapped": True}

        with patch.object(target, "_PREVIOUS_RUN_PROBE", side_effect=fake_probe):
            self.assertEqual(target.run_probe(), {"wrapped": True})
        self.assertIs(target.runtime._ORIGINAL_TASK_PROJECTION, before)

    def test_inherited_original_projector_drift_fails_before_context(self) -> None:
        before = target.runtime._ORIGINAL_TASK_PROJECTION
        target.runtime._ORIGINAL_TASK_PROJECTION = lambda *_args: {}
        try:
            with self.assertRaisesRegex(RuntimeError, "original projector drifted"):
                with target.configured_previous():
                    pass
        finally:
            target.runtime._ORIGINAL_TASK_PROJECTION = before

    def test_configuration_binds_and_restores_runtime_and_base(self) -> None:
        before = (
            target.previous.PROTOCOL_ID,
            target.runtime.proof,
            target.runtime.total,
            target.runtime.bounded,
            target.runtime.capability_collection,
            target.runtime.aggregate_strict_projections,
            target.runtime._ORIGINAL_TASK_PROJECTION,
            target.base.PROTOCOL_ID,
        )
        with target.configured_previous(validator_names=target._ALL_VALIDATORS):
            self.assertEqual(target.previous.PROTOCOL_ID, target.PROTOCOL_ID)
            self.assertIs(target.runtime.proof, target.proof)
            self.assertIs(target.runtime.total, target.total)
            self.assertIs(target.runtime.bounded, target.bounded)
            self.assertIs(
                target.runtime.capability_collection,
                target.collector_repair.capability_collection,
            )
            with target.previous.configured_predecessor(validators=True):
                with target.runtime.configured_base(validators=True):
                    self.assertEqual(target.base.PROTOCOL_ID, target.PROTOCOL_ID)
                    self.assertIs(target.base.run_targeted_worker, target.bounded.run_worker)
                    self.assertIs(
                        target.base.aggregate_projections,
                        target.collector_repair.aggregate_projections,
                    )
                    self.assertIs(
                        target.base.validate_targeted_aggregate,
                        target.total.validate_aggregate,
                    )
        self.assertEqual(
            (
                target.previous.PROTOCOL_ID,
                target.runtime.proof,
                target.runtime.total,
                target.runtime.bounded,
                target.runtime.capability_collection,
                target.runtime.aggregate_strict_projections,
                target.runtime._ORIGINAL_TASK_PROJECTION,
                target.base.PROTOCOL_ID,
            ),
            before,
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
                preaudit = target.build_preaudit(now=0)
                write_json(ROOT / paths["PREAUDIT"], preaudit)
                self.assertTrue(target.validate_preaudit(value=preaudit)["audit_valid"])
                activation = target.build_activation(now=0)
                write_json(ROOT / paths["ACTIVATION"], activation)
                self.assertTrue(target.validate_activation()["launch_authorized"])
                start = target.build_execution_start(now=0)
                write_json(ROOT / paths["EXECUTION_START"], start)
                self.assertTrue(target.validate_execution_start()["execution_authorized"])
        self.assertEqual(preaudit["checks"]["focused_tests"]["test_count"], 285)
        self.assertFalse(start["benchmark_or_evaluator_authorized"])

    def test_worker_and_supervisor_cli_bind_title_query_execution_base(self) -> None:
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
            self.assertTrue(receipt["immutable_collector_context_passed"])
            self.assertFalse(receipt["network_model_search_fetch_or_evaluator_called"])

    def test_protocol_design_does_not_authorize_launch_or_benchmark(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        self.assertTrue(
            value["authorization"][
                "one_fresh_validator_aligned_title_query_probe_design"
            ]
        )
        self.assertFalse(value["authorization"]["external_probe_launch"])
        self.assertFalse(value["authorization"]["benchmark_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])
        self.assertFalse(value["authorization"]["evaluator"])
        self.assertFalse(value["authorization"]["leaderboard_or_sota"])

    def test_runtime_source_is_label_blind_and_never_writes_shared_projector(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        source = Path("scripts/v24596_validator_aligned_title_query_external_gate.py")
        accesses, imports = audit.ast_findings(source)
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])
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
                    and item.value.id == "runtime"
                    and item.attr == "_ORIGINAL_TASK_PROJECTION"
                ):
                    writes.append(item.lineno)
        self.assertEqual(writes, [])

    def test_source_manifest_contains_title_query_chain_and_closure(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        self.assertTrue(set(target.previous_run.SOURCE_FILES).issubset(target.SOURCE_FILES))
        self.assertTrue(
            set(target.previous_run.SOURCE_FILES).issubset(value["surface_manifest"])
        )
        for path in (
            target.PREVIOUS_RESULT,
            target.PREVIOUS_DECISION,
            target.PREVIOUS_POSTAUDIT,
            target.PARENT,
            Path("src/deepwide_agent/v24589_validator_aligned_title_query.py"),
            Path("src/deepwide_agent/v24590_proof_carrying_validator_aligned_title_query.py"),
            Path("src/deepwide_agent/v24591_total_validator_aligned_title_query_projection.py"),
            Path("src/deepwide_agent/v24592_bounded_validator_aligned_title_query_parent.py"),
            Path("scripts/v24594_title_query_collector_repair.py"),
        ):
            self.assertIn(str(path), value["surface_manifest"])

    def test_result_schema_rejects_missing_title_query_aggregate(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "title-query aggregate schema"):
            target.validate_public_result({"mechanism_aggregate": {}})


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--cli-validator-smoke":
        raise SystemExit(cli_validator_smoke(sys.argv[2]))
    unittest.main()
