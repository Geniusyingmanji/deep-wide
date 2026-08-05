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
from scripts import v24583_prededup_preservation_external_gate as target  # noqa: E402
import test_v24567_strict_reachability_conversion_external_gate as strict_fixture  # noqa: E402
import test_v24579_proof_carrying_prededup_preservation as preservation_fixture  # noqa: E402


def reseal(value: dict, field: str) -> None:
    value.pop(field, None)
    value[field] = payload_sha256(value)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def positive_capability(root: Path):
    strict_root = root / "strict"
    strict_root.mkdir()
    strict = strict_fixture.positive_strict_capability(strict_root)
    observed_root = root / "observed"
    observed_root.mkdir()
    preservation_fixture.populate(observed_root)
    observed = preservation_fixture.validate(observed_root)
    aligned = target.proof.parent_proof.ValidatedProofCarryingValidatorAlignedSelection._create(
        parent=strict,
        receipt=observed.validator_aligned_selection_receipt(),
    )
    return target.proof.ValidatedProofCarryingPrededupPreservation._create(
        parent=aligned,
        receipt=observed.prededup_preservation_receipt(),
    )


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
            or target.base.run_targeted_worker is not target.bounded.run_worker
            or target.base.run_targeted_parent_with_separated_budget
            is not target.bounded.run_parent_with_separated_budget
            or target.base.aggregate_projections
            is not target.runtime.aggregate_strict_projections
            or target.base.validate_targeted_aggregate
            is not target.total.validate_aggregate
        ):
            raise RuntimeError("V2.45.83 CLI execution-base context is incomplete")
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
        target.base._worker, target.base._supervisor = (
            original_worker,
            original_supervisor,
        )
    return 0


class V24583PrededupPreservationExternalGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        cls.capability = positive_capability(Path(cls.temporary.name))
        cls.passing = target.total.aggregate_projections(
            [cls.capability] * 8, selected=8
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_population_is_fresh_and_alias_surfaces_are_query_blind(self) -> None:
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertTrue(target._alias_surface_vector_valid())
        self.assertEqual(len(target._prior_questions()), 452)
        self.assertEqual(len(target.QUESTIONS), 8)
        self.assertEqual(sum(map(len, target.ENTITY_GROUPS)), 64)
        surfaces = [
            target.acquisition.primary_alias_surface(entity)
            for group in target.ENTITY_GROUPS
            for entity in group
        ]
        self.assertEqual(len({value.casefold() for value in surfaces if value}), 64)

    def test_v24571_closure_and_v24582_parent_authorize_design_only(self) -> None:
        self.assertTrue(target._previous_closed())
        parent = target._parent(target.ROOT)
        self.assertTrue(parent["audit_valid"])
        self.assertEqual(parent["tests"]["test_count"], 63)
        self.assertTrue(
            parent["authorization"][
                "fresh_disjoint_prededup_preservation_external_protocol_design"
            ]
        )
        self.assertFalse(parent["authorization"]["fresh_external_activation_or_launch"])

    def test_protocol_binds_prededup_chain_and_unchanged_budget(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        mechanism = value["mechanism"]
        self.assertEqual(mechanism["targeted_proof_policy"], target.proof.POLICY_ID)
        self.assertEqual(mechanism["targeted_parent_policy"], target.bounded.POLICY_ID)
        self.assertEqual(
            mechanism["total_prededup_preservation_projection_policy"],
            target.total.POLICY_ID,
        )
        self.assertTrue(
            mechanism[
                "exact_url_distinct_candidates_preserved_before_registrable_source_selection"
            ]
        )
        self.assertFalse(
            mechanism["logical_query_search_batch_fetch_source_or_page_cap_changed"]
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
                "exact_url_distinct_candidates_preserved_before_registrable_source_selection",
                False,
            ),
            lambda item: item["mechanism"].__setitem__(
                "same_task_preservation_and_replacement_claim_lead_level_causality",
                True,
            ),
            lambda item: item["task_contract"].__setitem__(
                "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_452_consumed_external_questions",
                False,
            ),
        )
        for alter in cases:
            changed = copy.deepcopy(value)
            alter(changed)
            reseal(changed, "protocol_payload_sha256")
            with self.assertRaises(RuntimeError):
                target.validate_protocol(value=changed)

    def test_mechanism_requires_preservation_and_title_replacement(self) -> None:
        self.assertTrue(target.mechanism_passed(self.passing))
        cases = (
            ("prededup_preservation_activity_tasks", "prededup_projection_reachability_successor"),
            ("prededup_preserved_candidate_tasks", "same_source_candidate_coverage_successor"),
            (
                "prededup_and_title_replacement_cooccurrence_tasks",
                "validator_aligned_title_replacement_successor",
            ),
        )
        for field, route in cases:
            with self.subTest(field=field):
                changed = copy.deepcopy(self.passing)
                changed[field] = 0
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
                    route,
                )

    def test_opaque_capability_collector_projects_v24580_once(self) -> None:
        with target.configured_previous():
            with target.runtime.capability_collection():
                row = target.total.task_projection(1, self.capability)
                value = target.runtime.aggregate_strict_projections(
                    [row], selected=1
                )
        self.assertEqual(value["success_tasks"], 1)
        self.assertEqual(value["prededup_preserved_candidate_tasks"], 1)
        self.assertEqual(
            value["prededup_and_title_replacement_cooccurrence_tasks"], 1
        )
        self.assertFalse(
            value[
                "prededup_preservation_same_task_cooccurrence_claims_lead_level_causality"
            ]
        )

    def test_configuration_binds_and_restores_previous_runtime_and_base(self) -> None:
        before = (
            target.previous.PROTOCOL_ID,
            target.runtime.proof,
            target.runtime.total,
            target.runtime.bounded,
            target.base.PROTOCOL_ID,
        )
        with target.configured_previous(validator_names=target._ALL_VALIDATORS):
            self.assertEqual(target.previous.PROTOCOL_ID, target.PROTOCOL_ID)
            self.assertIs(target.runtime.proof, target.proof)
            self.assertIs(target.runtime.total, target.total)
            self.assertIs(target.runtime.bounded, target.bounded)
            with target.previous.configured_predecessor(validators=True):
                self.assertEqual(target.runtime.PROTOCOL_ID, target.PROTOCOL_ID)
                with target.runtime.configured_base(validators=True):
                    self.assertEqual(target.base.PROTOCOL_ID, target.PROTOCOL_ID)
                    self.assertIs(
                        target.base.run_targeted_worker, target.bounded.run_worker
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
                        target.base,
                        "lease_observation",
                        return_value={"active": False},
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
        self.assertEqual(preaudit["checks"]["focused_tests"]["test_count"], 189)
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

    def test_protocol_design_does_not_authorize_launch_benchmark_or_evaluator(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        self.assertTrue(
            value["authorization"]["one_fresh_prededup_preservation_probe_design"]
        )
        self.assertFalse(value["authorization"]["external_probe_launch"])
        self.assertFalse(value["authorization"]["benchmark_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])
        self.assertFalse(value["authorization"]["evaluator"])
        self.assertFalse(value["authorization"]["leaderboard_or_sota"])

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("scripts/v24583_prededup_preservation_external_gate.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])

    def test_source_manifest_contains_full_predecessor_and_build_chain(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        self.assertTrue(set(target.previous.SOURCE_FILES).issubset(target.SOURCE_FILES))
        self.assertTrue(
            set(target.previous.SOURCE_FILES).issubset(value["surface_manifest"])
        )
        for path in (
            target.PARENT,
            Path("src/deepwide_agent/v24578_prededup_candidate_preservation.py"),
            Path("src/deepwide_agent/v24579_proof_carrying_prededup_preservation.py"),
            Path("src/deepwide_agent/v24580_total_prededup_preservation_projection.py"),
            Path("src/deepwide_agent/v24581_bounded_prededup_preservation_parent.py"),
        ):
            self.assertIn(str(path), value["surface_manifest"])

    def test_result_schema_rejects_missing_prededup_aggregate(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "pre-dedup aggregate schema"):
            target.validate_public_result({"mechanism_aggregate": {}})


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--cli-validator-smoke":
        raise SystemExit(cli_validator_smoke(sys.argv[2]))
    unittest.main()
