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
from scripts import v24522_conversion_diagnostic_external_gate as target  # noqa: E402


def reseal(value: dict, field: str) -> None:
    value.pop(field, None)
    value[field] = payload_sha256(value)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def passing_mechanism() -> dict:
    reasons = {name: 0 for name in target.observability.REASONS}
    reasons[
        "no_projection_exact_entity_and_unique_title_anchor_absent_or_ambiguous"
    ] = 4
    return {
        "success_tasks": 8,
        "failure_as_zero_tasks": 0,
        "passed_success_tasks": 8,
        "conversion_any_usable_page_tasks": 4,
        "total_conversion_page_target_pair_count": 4,
        "conversion_reason_pair_counts": reasons,
        "total_conversion_signal_counts": {
            **{name: 0 for name in target.observability.SIGNAL_COUNT_FIELDS},
            "zero_projection_pair_count": 4,
        },
        "all_success_rows_consumed_conversion_capabilities": True,
        "all_failure_rows_are_content_free_conversion_zero_projections": True,
        "conversion_failure_rows_claim_zero_private_effects": False,
        "all_terminal_states_consumed_validated_capabilities": True,
        "total_additional_external_effects_success_rows": 0,
        "total_validation_memo_mismatches": 0,
        "conversion_private_task_content_emitted": False,
        "conversion_privileged_evaluator_content_read": False,
    }


def cli_validator_smoke(command: str) -> int:
    protocol = target.build_protocol(now=0, require_pristine=False)
    base = target._base()

    def validate_in_process(args: argparse.Namespace) -> None:
        validated = target.validate_protocol(value=protocol)
        if (
            validated["protocol_id"] != target.PROTOCOL_ID
            or validated["record_bound_binding"] != target._record_bound_binding()
            or base.RUNNER_MARKER != target.RUNNER_MARKER
            or base.run_targeted_worker is not target.conversion_parent.run_conversion_worker
            or base.run_targeted_parent_with_separated_budget
            is not target.conversion_parent.run_conversion_parent_with_separated_budget
            or base.aggregate_projections is not target.aggregate_conversion_projections
        ):
            raise RuntimeError("V2.45.22 CLI validator context is incomplete")
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


class V24522ConversionDiagnosticExternalGateTests(unittest.TestCase):
    def test_population_is_fresh_against_356_questions_and_2848_entities(self) -> None:
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertEqual(len(target._prior_questions()), 356)
        self.assertEqual(len(target.QUESTIONS), 8)
        self.assertEqual(sum(map(len, target.ENTITY_GROUPS)), 64)

    def test_v24517_is_closed_and_never_rerun(self) -> None:
        self.assertTrue(target._previous_closed())
        binding = target._record_bound_binding()
        self.assertFalse(binding["v24517_population_rerun"])
        self.assertEqual(binding["prior_external_question_count"], 356)
        self.assertEqual(binding["prior_external_entity_count"], 2848)
        self.assertFalse(binding["new_population_reuses_prior_question_or_entity"])

    def test_parent_is_valid_and_authorizes_design_only(self) -> None:
        value = target._parent(ROOT)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["label_blind_audit"]["passed"])
        self.assertTrue(
            value["authorization"][
                "fresh_disjoint_conversion_diagnostic_external_protocol_design"
            ]
        )
        self.assertFalse(value["authorization"]["fresh_external_activation_or_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])

    def test_protocol_binds_conversion_pipeline_and_frozen_capacity(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        binding = value["record_bound_binding"]
        mechanism = value["mechanism"]
        self.assertEqual(
            binding["conversion_observability_policy"],
            target.observability.POLICY_ID,
        )
        self.assertEqual(
            binding["proof_carrying_conversion_observability_policy"],
            target.conversion_proof.POLICY_ID,
        )
        self.assertEqual(
            binding["total_conversion_projection_policy"], target.total.POLICY_ID
        )
        self.assertEqual(
            binding["bounded_conversion_parent_policy"],
            target.conversion_parent.POLICY_ID,
        )
        self.assertTrue(mechanism["diagnostic_complete_not_quality_threshold"])
        self.assertFalse(mechanism["public_success_row_reingestion_allowed"])
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
        with target.configured_predecessor(validators=True):
            with target.predecessor.configured_predecessor(validators=True):
                with target.predecessor.predecessor.configured_predecessor(
                    validators=True
                ):
                    with target.predecessor.predecessor.predecessor.configured_predecessor(
                        validators=True
                    ):
                        for ordinal in range(1, 9):
                            task = target._base().neutral_task(ordinal)
                            self.assertEqual(set(task), {"opaque_id", "question"})
                            self.assertNotIn(task["opaque_id"], encoded)
                            self.assertNotIn(task["question"], encoded)

    def test_resealed_protocol_tamper_fails_closed(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        cases = (
            lambda item: item["record_bound_binding"].__setitem__(
                "v24517_population_rerun", True
            ),
            lambda item: item["record_bound_binding"].__setitem__(
                "expanded_public_success_row_reingestion_allowed", True
            ),
            lambda item: item["record_bound_binding"].__setitem__(
                "paired_dev64_or_exact220_directly_authorized", True
            ),
            lambda item: item["mechanism"].__setitem__(
                "public_success_row_reingestion_allowed", True
            ),
        )
        for alter in cases:
            changed = copy.deepcopy(value)
            alter(changed)
            reseal(changed, "protocol_payload_sha256")
            with self.assertRaises(RuntimeError):
                target.validate_protocol(value=changed)

    def test_mechanism_gate_requires_complete_conserved_diagnostic(self) -> None:
        value = passing_mechanism()
        self.assertTrue(target.mechanism_passed(value))
        for field in (
            "success_tasks",
            "conversion_any_usable_page_tasks",
            "total_conversion_page_target_pair_count",
            "total_additional_external_effects_success_rows",
        ):
            changed = copy.deepcopy(value)
            changed[field] = (
                7
                if field == "success_tasks"
                else 1
                if field == "total_additional_external_effects_success_rows"
                else 0
            )
            self.assertFalse(target.mechanism_passed(changed), field)
        changed = copy.deepcopy(value)
        changed["conversion_reason_pair_counts"][
            "no_projection_exact_entity_and_unique_title_anchor_absent_or_ambiguous"
        ] = 3
        self.assertFalse(target.mechanism_passed(changed))

    def test_reason_family_routes_are_deterministic_and_reliability_precedes_mechanism(self) -> None:
        supervision = {"worker_hard_timeout_tasks": 0, "worker_nonzero_tasks": 0}
        families = {
            "anchor_absence_or_misbinding": "conservative_alias_title_anchoring_successor",
            "relation_or_year_absence": "source_ranking_fetch_selection_successor",
            "conservative_safety_rejection": "conservative_parser_grammar_successor",
            "source_ambiguity": "dedup_source_selection_successor",
            "observation_or_parent_duplicate": "observation_support_credit_successor",
        }
        for family, expected in families.items():
            mechanism = passing_mechanism()
            mechanism["conversion_reason_pair_counts"] = {
                name: 0 for name in target.observability.REASONS
            }
            mechanism["conversion_reason_pair_counts"][
                target.REASON_FAMILIES[family][0]
            ] = 4
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
        self.assertEqual(
            target.diagnostic_route(
                passing_mechanism(),
                {"worker_hard_timeout_tasks": 1, "worker_nonzero_tasks": 0},
                diagnostic=True,
                reliability=False,
                parent_validation=False,
                latency=False,
            ),
            "bounded_worker_stage_successor",
        )

    def test_opaque_capability_collector_aggregates_once_and_rejects_public_reingestion(self) -> None:
        capability = object()
        success = {"ordinal": 1, "status": "validated_capability"}
        captured: list[object] = []

        def aggregate(values, *, selected):
            captured.extend(values)
            return {"selected": selected}

        with (
            patch.object(
                target,
                "_ORIGINAL_TASK_PROJECTION",
                side_effect=lambda ordinal, current: {
                    **success,
                    "ordinal": ordinal,
                },
            ),
            patch.object(target.total, "validate_total_row", side_effect=dict),
            patch.object(target.total, "aggregate_projections", side_effect=aggregate),
        ):
            collector = target._CapabilityCollector()
            row = collector.project(1, capability)
            self.assertEqual(collector.aggregate([row], selected=1), {"selected": 1})
            self.assertEqual(captured, [capability])
            with self.assertRaises(RuntimeError):
                collector.aggregate([row], selected=1)
            missing = target._CapabilityCollector()
            with self.assertRaises(RuntimeError):
                missing.aggregate([row], selected=1)

    def test_capability_collection_restores_parent_projection_after_exception(self) -> None:
        original = target.conversion_parent.task_projection
        with self.assertRaisesRegex(RuntimeError, "stop"):
            with target.capability_collection():
                self.assertIsNot(target.conversion_parent.task_projection, original)
                raise RuntimeError("stop")
        self.assertIs(target.conversion_parent.task_projection, original)
        self.assertIsNone(target._ACTIVE_COLLECTOR)

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
        self.assertEqual(preaudit["checks"]["focused_tests"]["test_count"], 69)
        self.assertFalse(start["benchmark_or_evaluator_authorized"])

    def test_worker_supervisor_cli_and_runtime_are_label_blind(self) -> None:
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
                timeout=40,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            receipt = json.loads(completed.stdout.strip())
            self.assertTrue(receipt["validator_context_passed"])
            self.assertFalse(receipt["network_model_search_fetch_or_evaluator_called"])
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("scripts/v24522_conversion_diagnostic_external_gate.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--cli-validator-smoke":
        raise SystemExit(cli_validator_smoke(sys.argv[2]))
    unittest.main()
