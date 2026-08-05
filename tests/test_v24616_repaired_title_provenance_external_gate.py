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
from scripts import v24616_repaired_title_provenance_external_gate as target  # noqa: E402
from test_v24607_proof_carrying_title_provenance import populate, validate  # noqa: E402


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
            or target.controller.PROTOCOL_ID != target.PROTOCOL_ID
            or target.runtime.PROTOCOL_ID != target.PROTOCOL_ID
            or target.base.PROTOCOL_ID != target.PROTOCOL_ID
            or target.controller.proof is not target.proof
            or target.runtime.proof is not target.proof
            or target.runtime.total is not target.total
            or target.runtime.bounded is not target.bounded
            or target.runtime.capability_collection
            is not target.collector.capability_collection
            or target.runtime.aggregate_strict_projections
            is not target.collector.aggregate_projections
            or target.base.run_targeted_worker is not target.bounded.run_worker
            or target.base.run_targeted_parent_with_separated_budget
            is not target.bounded.run_parent_with_separated_budget
            or target.base.aggregate_projections
            is not target.collector.aggregate_projections
            or target.base.validate_targeted_aggregate
            is not target.total.validate_aggregate
            or not target.binding.invariant_valid()
        ):
            raise RuntimeError("V2.46.16 CLI execution context is incomplete")
        print(
            json.dumps(
                {
                    "command": args.command,
                    "protocol_id": validated["protocol_id"],
                    "noncontaminating_runtime_context_passed": True,
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


class V24616RepairedTitleProvenanceExternalGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        cls.root = Path(cls.temporary.name)
        populate(cls.root)
        cls.capability = validate(cls.root)
        receipt = cls.capability.content_free_title_provenance_receipt()
        receipt["provider_response_count"] = 1
        cls.provider_capability = (
            target.proof.ValidatedProofCarryingContentFreeTitleProvenance._create(
                parent=cls.capability.parent_capability(), receipt=receipt
            )
        )
        cls.passing = target.total.aggregate_projections(
            [cls.provider_capability] * 8, selected=8
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_population_is_fresh_and_query_surfaces_are_reachable(self) -> None:
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertTrue(target._title_query_surface_vector_valid())
        self.assertEqual(len(target._prior_questions()), 492)
        self.assertEqual(len(target.QUESTIONS), 8)
        self.assertEqual(sum(map(len, target.ENTITY_GROUPS)), 64)
        surfaces = [
            target.acquisition.primary_alias_surface(entity)
            for group in target.ENTITY_GROUPS
            for entity in group
        ]
        self.assertEqual(sum(value is not None for value in surfaces), 64)
        self.assertEqual(len({value.casefold() for value in surfaces if value}), 64)

    def test_v24612_is_terminal_consumed_and_v24615_authorizes_design_only(self) -> None:
        self.assertTrue(target._previous_closed())
        parent = target._parent(target.ROOT)
        self.assertTrue(parent["audit_valid"])
        self.assertEqual(parent["tests"]["test_count"], 57)
        self.assertEqual(parent["freshness_baseline"]["prior_external_question_count"], 492)
        self.assertTrue(parent["binding_repair"]["binding_valid"])
        self.assertFalse(parent["authorization"]["fresh_external_activation_or_launch"])

    def test_protocol_binds_runtime_provenance_and_preserves_budget(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        mechanism = value["mechanism"]
        self.assertEqual(mechanism["targeted_proof_policy"], target.proof.POLICY_ID)
        self.assertEqual(mechanism["targeted_parent_policy"], target.bounded.POLICY_ID)
        self.assertEqual(mechanism["controller_binding_policy"], target.binding.POLICY_ID)
        self.assertEqual(
            mechanism["immutable_title_provenance_collector_policy"],
            target.collector.POLICY_ID,
        )
        self.assertFalse(mechanism["v24607_parent_proof_module_mutated"])
        self.assertFalse(mechanism["v24607_parent_validator_mutated"])
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

    def test_protocol_build_uses_native_title_funnel_view_only(self) -> None:
        runtime_parent = target.proof.parent_proof
        runtime_validator = target.proof.validate_proof_carrying_title_provenance_bundle
        with patch.object(
            target,
            "_BASE_BUILD_PROTOCOL",
            wraps=target._BASE_BUILD_PROTOCOL,
        ) as called:
            target.build_protocol(now=0, require_pristine=False)
            self.assertEqual(called.call_count, 1)
        self.assertIs(target.proof.parent_proof, runtime_parent)
        self.assertIs(
            target.proof.validate_proof_carrying_title_provenance_bundle,
            runtime_validator,
        )
        self.assertTrue(target.binding.invariant_valid())

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
                "new_population_reuses_prior_question_or_entity", True
            ),
            lambda item: item["mechanism"].__setitem__(
                "v24607_parent_proof_module_mutated", True
            ),
            lambda item: item["mechanism"].__setitem__(
                "action_source_title_count_observed", False
            ),
            lambda item: item["task_contract"].__setitem__(
                "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_492_consumed_external_questions",
                False,
            ),
        )
        for alter in cases:
            changed = copy.deepcopy(value)
            alter(changed)
            reseal(changed, "protocol_payload_sha256")
            with self.assertRaises(RuntimeError):
                target.validate_protocol(value=changed)

    def test_mechanism_requires_provider_observation(self) -> None:
        self.assertTrue(target.mechanism_passed(self.passing))
        changed = copy.deepcopy(self.passing)
        changed["content_free_title_provenance_provider_activity_tasks"] = 0
        self.assertFalse(target.mechanism_passed(changed))
        self.assertEqual(
            target.diagnostic_route(
                changed,
                {},
                diagnostic=False,
                reliability=True,
                parent_validation=True,
                latency=True,
            ),
            "title_provenance_runtime_successor",
        )

    def route(self, **counts: int) -> str:
        value = copy.deepcopy(self.passing)
        projected = value["total_content_free_title_provenance_count_fields"]
        for name in target.total.PROVENANCE_COUNT_NAMES:
            projected[name] = 0
        projected.update(counts)
        value["content_free_title_provenance_provider_activity_tasks"] = 8
        return target.diagnostic_route(
            value,
            {},
            diagnostic=True,
            reliability=True,
            parent_validation=True,
            latency=True,
        )

    def test_action_title_routes_to_transport_projection_bug(self) -> None:
        self.assertEqual(
            self.route(action_source_nonempty_title_count=1),
            "title_transport_projection_bug_successor",
        )

    def test_same_url_citation_backfill_route(self) -> None:
        self.assertEqual(
            self.route(
                query_local_citation_nonempty_title_count=1,
                same_url_action_empty_citation_nonempty_count=1,
            ),
            "same_response_citation_title_backfill_successor",
        )

    def test_post_fetch_title_integration_route(self) -> None:
        self.assertEqual(
            self.route(fetched_result_nonempty_title_count=1),
            "post_fetch_title_integration_successor",
        )

    def test_all_empty_routes_to_provider_title_acquisition(self) -> None:
        self.assertEqual(self.route(), "provider_title_acquisition_successor")

    def test_real_collector_aggregates_eight_provenance_capabilities(self) -> None:
        with target.configured_controller(protocol_compatibility=False):
            with target.runtime.capability_collection():
                rows = [
                    target.total.task_projection(ordinal, self.provider_capability)
                    for ordinal in range(1, 9)
                ]
                value = target.runtime.aggregate_strict_projections(rows, selected=8)
        self.assertEqual(value["success_tasks"], 8)
        self.assertEqual(value["content_free_title_provenance_provider_activity_tasks"], 8)
        self.assertTrue(target.binding.invariant_valid())

    def test_run_probe_uses_runtime_view_and_restores(self) -> None:
        def fake_probe() -> dict:
            self.assertIs(target.controller.proof, target.proof)
            self.assertIs(target.controller.total, target.total)
            self.assertIs(target.controller.bounded, target.bounded)
            self.assertTrue(target.binding.invariant_valid())
            return {"wrapped": True}

        with patch.object(target, "_BASE_RUN_PROBE", side_effect=fake_probe):
            self.assertEqual(target.run_probe(), {"wrapped": True})
        self.assertTrue(target.binding.invariant_valid())

    def test_runtime_view_validates_real_capability_without_contamination(self) -> None:
        parent = target.proof.parent_proof
        with target.configured_controller(protocol_compatibility=False):
            capability = validate(self.root)
            self.assertIsInstance(
                capability,
                target.proof.ValidatedProofCarryingContentFreeTitleProvenance,
            )
            self.assertIs(target.proof.parent_proof, parent)
        self.assertTrue(target.binding.invariant_valid())

    def test_controller_exception_restores_runtime_and_proof_bindings(self) -> None:
        before = (
            target.controller.proof,
            target.runtime.proof,
            target.runtime.total,
            target.runtime.bounded,
            target.runtime.capability_collection,
            target.runtime.aggregate_strict_projections,
        )
        with self.assertRaisesRegex(RuntimeError, "synthetic stop"):
            with target.configured_controller(protocol_compatibility=False):
                self.assertIs(target.controller.proof, target.proof)
                self.assertIs(target.runtime.proof, target.proof)
                raise RuntimeError("synthetic stop")
        self.assertEqual(
            (
                target.controller.proof,
                target.runtime.proof,
                target.runtime.total,
                target.runtime.bounded,
                target.runtime.capability_collection,
                target.runtime.aggregate_strict_projections,
            ),
            before,
        )
        self.assertTrue(target.binding.invariant_valid())

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
        self.assertEqual(
            preaudit["checks"]["focused_tests"]["test_count"],
            target.EXPECTED_TEST_COUNT,
        )
        self.assertFalse(start["benchmark_or_evaluator_authorized"])
        self.assertTrue(target.binding.invariant_valid())

    def test_worker_and_supervisor_cli_bind_noncontaminating_runtime(self) -> None:
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
            self.assertTrue(receipt["noncontaminating_runtime_context_passed"])
            self.assertFalse(receipt["network_model_search_fetch_or_evaluator_called"])

    def test_protocol_design_does_not_authorize_launch_or_benchmark(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        self.assertTrue(
            value["authorization"]["one_fresh_repaired_title_provenance_probe_design"]
        )
        self.assertFalse(value["authorization"]["external_probe_launch"])
        self.assertFalse(value["authorization"]["benchmark_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])
        self.assertFalse(value["authorization"]["evaluator"])

    def test_runtime_source_is_label_blind_and_never_writes_shared_projector(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        source = Path("scripts/v24616_repaired_title_provenance_external_gate.py")
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
                    and item.value.id in {"runtime", "proof"}
                    and item.attr in {"_ORIGINAL_TASK_PROJECTION", "parent_proof"}
                ):
                    writes.append(item.lineno)
        self.assertEqual(writes, [])

    def test_result_schema_rejects_missing_provenance_aggregate(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "title-provenance aggregate schema"):
            target.validate_public_result({"mechanism_aggregate": {}})


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--cli-validator-smoke":
        raise SystemExit(cli_validator_smoke(sys.argv[2]))
    unittest.main()
