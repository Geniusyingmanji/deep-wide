from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24308_child_exit_observability import parent_receipt  # noqa: E402
from scripts import finalize_v24657_unknown_cell_targeted_dev64 as finalizer  # noqa: E402
from scripts import run_v24657_unknown_cell_targeted_dev64 as runner  # noqa: E402
from scripts import v24657_unknown_cell_targeted_dev64_control as control  # noqa: E402
from test_v24655_unknown_cell_targeted_runtime import TASK  # noqa: E402
from test_v24657_runner_integration import synthetic_outcome  # noqa: E402


def successful_parent():
    return parent_receipt(
        return_code=0,
        timed_out=False,
        elapsed_seconds=1.0,
        subprocess_exception=False,
        child_terminal_receipt_present=True,
        child_terminal_receipt_valid=True,
        result_envelope_present=True,
        result_envelope_valid=True,
        model_receipt_present=True,
        model_receipt_valid=True,
        transport_receipt_present=True,
        transport_receipt_valid=True,
    )


def pair_summary(testcase: unittest.TestCase):
    temporary, integrated = synthetic_outcome()
    testcase.addCleanup(temporary.cleanup)
    result = integrated.result
    outcomes = [
        runner.PairOutcome(
            position=index,
            task=TASK,
            rows={
                arm: runner._runtime_row(
                    TASK, arm=arm, result=result, parent_taxonomy="success"
                )
                for arm in runner.ARMS
            },
            parent_exit=successful_parent(),
            result=result,
            model_receipt=integrated.model_slot_receipt,
            transport_health=integrated.transport_health,
        )
        for index in range(1, runner.SELECTED_COUNT + 1)
    ]
    return runner._pair_summary(outcomes, 10.0)


def metrics(*, candidate_whole: int = 5, candidate_quality: float = 0.51):
    baseline = {
        "runtime_completed": 64,
        "runtime_failed": 0,
        "fallback_tables": 0,
        "evaluator_valid": 63,
        "evaluator_invalid_or_not_run": 1,
        "whole_table_successes": 4,
        "entity_acc": 0.50,
        "f1_by_row": 0.50,
        "f1_by_item": 0.50,
        "column_f1": 0.50,
        "quality_composite": 0.50,
        "score": 4 / 64,
    }
    candidate = {
        **baseline,
        "whole_table_successes": candidate_whole,
        "entity_acc": candidate_quality,
        "f1_by_row": candidate_quality,
        "f1_by_item": candidate_quality,
        "column_f1": candidate_quality,
        "quality_composite": candidate_quality,
        "score": candidate_whole / 64,
    }
    return {"baseline": baseline, "candidate": candidate}


def uncertainty():
    return {
        "task_count": 64,
        "bootstrap_unit": "paired_frozen_task",
        "seed": 24657,
        "resamples": 10_000,
        "estimand": "synthetic",
        "mean": 0.01,
        "median": 0.0,
        "positive": 1,
        "zero": 63,
        "negative": 0,
        "minimum": 0.0,
        "maximum": 0.64,
        "percentile_95_interval": [0.0, 0.04],
        "interval_width": 0.04,
        "fixed_denominator_failure_as_zero": True,
        "predictions_frozen_before_evaluator": True,
        "future_population_or_sota_inference": False,
    }


class V24657UnknownCellTargetedDev64Tests(unittest.TestCase):
    def test_forward_contract_is_visible_only_and_high_concurrency(self) -> None:
        value = control.build_forward_contract(ROOT, now=0, require_pristine=False)
        execution = value["execution"]
        self.assertEqual(value["task_contract"]["runtime_boundary"], ["opaque_id", "question"])
        self.assertEqual(value["task_contract"]["selected_count"], 64)
        self.assertTrue(
            value["task_contract"][
                "preexisting_frozen_opaque_id_vector_reused_without_current_label_access"
            ]
        )
        self.assertEqual(execution["executor_concurrency"], 16)
        self.assertEqual(execution["model_slot_cap"], 8)
        self.assertEqual(
            str(control.EVALUATOR_IDENTITY_PARENT),
            "results/v24320_paired_dev64_preregistration_v1_20260803.json",
        )
        self.assertTrue(execution["shared_generic_prefix_before_baseline"])
        self.assertTrue(
            execution[
                "candidate_only_unknown_cell_targeted_search_and_deterministic_support_gate"
            ]
        )
        self.assertFalse(
            value["source_policy"][
                "mapping_gold_category_question_type_split_evaluator_score_read_by_forward"
            ]
        )

    def test_resealed_forward_contract_concurrency_tamper_fails_closed(self) -> None:
        value = control.build_forward_contract(ROOT, now=0, require_pristine=False)
        value["execution"]["model_slot_cap"] = 9
        value.pop("forward_contract_payload_sha256")
        value["forward_contract_payload_sha256"] = control.payload_sha256(value)
        with tempfile.TemporaryDirectory(dir=ROOT / "results") as directory:
            path = Path(directory) / "contract.json"
            path.write_text(json.dumps(value) + "\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                control.validate_forward_contract(ROOT, path.relative_to(ROOT))

    def test_protocol_freezes_pareto_not_entropy_treatment_and_exact220_false(
        self,
    ) -> None:
        contract = control.build_forward_contract(
            ROOT, now=0, require_pristine=False
        )
        real_sha256 = control.sha256

        def frozen_sha256(path):
            return (
                "a" * 64
                if Path(path) == ROOT / control.FORWARD_CONTRACT
                else real_sha256(path)
            )

        with patch.object(
            control, "validate_forward_contract", return_value=contract
        ), patch.object(control, "sha256", side_effect=frozen_sha256):
            protocol = control.build_protocol(
                ROOT, now=0, require_pristine=False
            )
            treatment = protocol["causal_treatment"]
            self.assertTrue(treatment["quality_cost_pareto_comparison"])
            self.assertFalse(treatment["algorithmic_credit_assignment_ablation"])
            self.assertFalse(treatment["entropy_routes_or_assigns_positive_credit"])
            self.assertFalse(protocol["authorization"]["exact220_launch"])

            tampered = copy.deepcopy(protocol)
            tampered["causal_treatment"]["algorithmic_credit_assignment_ablation"] = True
            tampered.pop("protocol_payload_sha256")
            tampered["protocol_payload_sha256"] = control.payload_sha256(tampered)
            with self.assertRaises(RuntimeError):
                control.validate_protocol(ROOT, value=tampered)

    def test_forward_ast_has_no_privileged_access_or_evaluator_import(self) -> None:
        self.assertEqual(control._field_accesses(ROOT), [])
        self.assertEqual(control._import_hits(ROOT), [])

    def test_exact64_pair_summary_conserves_effects_without_entropy_credit(self) -> None:
        value = pair_summary(self)
        runner.validate_pair_summary(value)
        self.assertEqual(value["selected_pair_tasks"], 64)
        self.assertEqual(value["effect_accounting_complete_tasks"], 64)
        self.assertEqual(value["shared_generic_prefix_tasks"], 64)
        self.assertEqual(value["slot_timeouts"], 0)
        self.assertGreater(value["admitted_cell_changes"], 0)
        self.assertEqual(value["entropy_task_credit_nats"], 0.0)

    def test_go_requires_strict_whole_table_gain_and_quality_nonregression(self) -> None:
        pair = pair_summary(self)
        protocol = {"decision_contract": control.DECISION_CONTRACT}
        go = finalizer.decision(protocol, metrics(), uncertainty(), pair)
        self.assertTrue(go["passed"])

        no_exact_gain = finalizer.decision(
            protocol, metrics(candidate_whole=4), uncertainty(), pair
        )
        self.assertFalse(no_exact_gain["passed"])
        self.assertIn("whole_table_success_delta", no_exact_gain["failed_checks"])

        quality_regression = finalizer.decision(
            protocol, metrics(candidate_quality=0.49), uncertainty(), pair
        )
        self.assertFalse(quality_regression["passed"])
        self.assertIn("f1_by_item_delta", quality_regression["failed_checks"])
        self.assertIn("quality_composite_delta", quality_regression["failed_checks"])

    def test_runtime_failure_fallback_or_entropy_credit_fails_closed(self) -> None:
        pair = pair_summary(self)
        protocol = {"decision_contract": control.DECISION_CONTRACT}
        bad_metrics = metrics()
        bad_metrics["candidate"]["runtime_completed"] = 63
        bad_metrics["candidate"]["runtime_failed"] = 1
        bad_metrics["candidate"]["fallback_tables"] = 1
        failed = finalizer.decision(protocol, bad_metrics, uncertainty(), pair)
        self.assertFalse(failed["passed"])
        self.assertIn("candidate_minus_baseline_runtime_failed", failed["failed_checks"])
        self.assertIn("candidate_minus_baseline_fallback_tables", failed["failed_checks"])

        credited = copy.deepcopy(pair)
        credited["entropy_task_credit_nats"] = 0.1
        failed = finalizer.decision(protocol, metrics(), uncertainty(), credited)
        self.assertFalse(failed["passed"])
        self.assertIn("zero_entropy_task_credit", failed["failed_checks"])

    def test_evaluator_pairing_routes_only_by_identity_and_prediction_hash(self) -> None:
        baseline_rows = []
        candidate_rows = []
        baseline_official = []
        candidate_official = []
        for index in range(64):
            opaque = f"task_{index:024x}"
            baseline_hash = f"{index:064x}"[-64:]
            candidate_hash = "f" * 64 if index == 0 else baseline_hash
            baseline_rows.append(
                {"opaque_id": opaque, "status": "completed", "prediction_sha256": baseline_hash}
            )
            candidate_rows.append(
                {"opaque_id": opaque, "status": "completed", "prediction_sha256": candidate_hash}
            )
            baseline_official.append({"instance_id": f"instance-{index}"})
            candidate_official.append({"instance_id": f"instance-{index}"})
        plan = finalizer.build_evaluation_plan(
            {"arms": {"baseline": {"rows": baseline_rows}, "candidate": {"rows": candidate_rows}}},
            {"baseline": {"official": baseline_official}, "candidate": {"official": candidate_official}},
        )
        self.assertEqual(len(plan["identity_instance_ids"]), 63)
        self.assertEqual(len(plan["changed_instance_ids"]), 1)
        self.assertFalse(
            plan[
                "mapping_gold_category_question_type_split_score_or_reward_used_for_routing"
            ]
        )

    def test_resealed_evaluator_gate_role_or_authorization_tamper_fails_closed(
        self,
    ) -> None:
        value = {
            "artifact_version": 1,
            "role": "v24657_unknown_cell_targeted_paired_dev64_evaluator_gate",
            "protocol_id": control.PROTOCOL_ID,
            "created_at_unix": 0,
            "status": "evaluator_gate_go",
            "findings": [],
            "passed": True,
            "selected_pair_tasks": 64,
            "prediction_rows_per_arm": {arm: 64 for arm in control.ARMS},
            "failed_pair_tasks": 0,
            "both_arm_prediction_freeze_sha256": {
                arm: f"{index:064x}"
                for index, arm in enumerate(control.ARMS, start=1)
            },
            "forward_result_sha256": "3" * 64,
            "pair_summary_sha256": "4" * 64,
            "forward_result_base_commit": "a" * 40,
            "target_main_at_gate": "a" * 40,
            "git_worktree_clean_before_gate": True,
            "forward_result_tracked": True,
            "forward_runner_present": False,
            "shared_api_lease_active": False,
            "protected_watchers_unchanged": True,
            "mapping_query_answer_gold_evaluator_score_opened_or_hashed": False,
            "official_evaluator_called": False,
            "authorization": dict(finalizer.GATE_AUTHORIZATION),
            "protocol_sha256": "5" * 64,
        }

        def fake_sha256(path):
            relative = Path(path).relative_to(ROOT)
            if relative == control.FORWARD_RESULT:
                return "3" * 64
            if relative == control.PAIR_SUMMARY:
                return "4" * 64
            if relative == control.PROTOCOL:
                return "5" * 64
            for index, arm in enumerate(control.ARMS, start=1):
                if relative == control.PREDICTION_FREEZE[arm]:
                    return f"{index:064x}"
            raise AssertionError(relative)

        barrier = {"pair": {"failed_pair_tasks": 0}}
        for field, replacement in (
            ("role", "v24657_wrong_evaluator_gate"),
            (
                "authorization",
                {
                    **finalizer.GATE_AUTHORIZATION,
                    "evaluator_execution": True,
                },
            ),
        ):
            tampered = copy.deepcopy(value)
            tampered[field] = replacement
            tampered["gate_payload_sha256"] = control.payload_sha256(tampered)
            with tempfile.TemporaryDirectory(dir=ROOT / "results") as directory:
                gate = Path(directory) / "gate.json"
                gate.write_text(json.dumps(tampered) + "\n", encoding="utf-8")
                with patch.object(finalizer, "EVALUATOR_GATE", gate.relative_to(ROOT)), patch.object(
                    finalizer, "validate_forward_barrier", return_value=barrier
                ), patch.object(finalizer, "validate_protocol", return_value={}), patch.object(
                    finalizer, "sha256", side_effect=fake_sha256
                ):
                    with self.assertRaises(RuntimeError):
                        finalizer.validate_evaluator_gate(ROOT)

    def test_resealed_evaluator_start_role_or_authorization_tamper_fails_closed(
        self,
    ) -> None:
        value = {
            "artifact_version": 1,
            "role": "v24657_unknown_cell_targeted_paired_dev64_evaluator_start",
            "protocol_id": control.PROTOCOL_ID,
            "created_at_unix": 0,
            "status": "evaluator_ready",
            "findings": [],
            "execution_authorized": True,
            "gate_base_commit": "a" * 40,
            "target_main_at_start": "a" * 40,
            "git_worktree_clean_before_start": True,
            "evaluator_gate_tracked": True,
            "evaluator_gate_sha256": "1" * 64,
            "protocol_sha256": "2" * 64,
            "forward_result_sha256": "3" * 64,
            "both_arm_prediction_freeze_sha256": {
                arm: f"{index + 3:064x}"
                for index, arm in enumerate(control.ARMS)
            },
            "evaluator_workers_per_arm": finalizer.EVALUATOR_WORKERS_PER_ARM,
            "total_evaluator_workers": finalizer.TOTAL_EVALUATOR_WORKERS,
            "shared_api_lease_active_before_start": False,
            "mapping_query_answer_gold_evaluator_score_opened_or_hashed_before_start": False,
            "official_evaluator_called_before_start": False,
            "additional_forward_resume_retry_or_rerun": False,
            "authorization": dict(finalizer.START_AUTHORIZATION),
        }

        def fake_sha256(path):
            relative = Path(path).relative_to(ROOT)
            values = {
                control.EVALUATOR_GATE: "1" * 64,
                control.PROTOCOL: "2" * 64,
                control.FORWARD_RESULT: "3" * 64,
                control.PREDICTION_FREEZE["baseline"]: f"{3:064x}",
                control.PREDICTION_FREEZE["candidate"]: f"{4:064x}",
            }
            return values[relative]

        for field, replacement in (
            ("role", "v24657_wrong_evaluator_start"),
            (
                "authorization",
                {
                    **finalizer.START_AUTHORIZATION,
                    "exact220": True,
                },
            ),
        ):
            tampered = copy.deepcopy(value)
            tampered[field] = replacement
            tampered["start_payload_sha256"] = control.payload_sha256(tampered)
            with tempfile.TemporaryDirectory(dir=ROOT / "results") as directory:
                start = Path(directory) / "start.json"
                start.write_text(json.dumps(tampered) + "\n", encoding="utf-8")
                with patch.object(finalizer, "EVALUATOR_START", start.relative_to(ROOT)), patch.object(
                    finalizer, "validate_evaluator_gate", return_value={}
                ), patch.object(finalizer, "validate_protocol", return_value={}), patch.object(
                    finalizer, "sha256", side_effect=fake_sha256
                ):
                    with self.assertRaises(RuntimeError):
                        finalizer.validate_evaluator_start(ROOT)

    def test_postaudit_records_live_lease_and_resealed_false_tamper_fails_closed(
        self,
    ) -> None:
        result = {
            "status": "development_gate_go",
            "decision": {"passed": True},
        }
        contract = {
            "execution": {
                "protected_watchers": [
                    {"pid": 1, "marker": "watcher.py", "start_ticks": 2}
                ]
            }
        }
        active = {"active": True}
        with patch.object(
            finalizer, "validate_final_result", return_value=result
        ), patch.object(
            finalizer, "lease_observation", return_value=active
        ), patch.object(
            finalizer,
            "protected_watcher_snapshot",
            return_value=contract["execution"]["protected_watchers"],
        ), patch.object(
            finalizer, "validate_forward_contract", return_value=contract
        ), patch.object(finalizer, "sha256", return_value="a" * 64), patch.object(
            finalizer, "validate_postaudit", return_value={}
        ):
            audit = finalizer.build_postaudit(ROOT, result)
        self.assertTrue(audit["shared_api_lease_active"])
        self.assertEqual(audit["findings"], ["shared_api_lease_active"])
        self.assertFalse(audit["audit_valid"])

        tampered = copy.deepcopy(audit)
        tampered["shared_api_lease_active"] = False
        tampered["findings"] = []
        tampered["audit_valid"] = True
        tampered["authorization"]["fresh_exact220_design"] = True
        tampered.pop("audit_payload_sha256")
        tampered["audit_payload_sha256"] = control.payload_sha256(tampered)
        with patch.object(
            finalizer, "validate_final_result", return_value=result
        ), patch.object(
            finalizer, "lease_observation", return_value=active
        ), patch.object(
            finalizer,
            "protected_watcher_snapshot",
            return_value=contract["execution"]["protected_watchers"],
        ), patch.object(
            finalizer, "validate_forward_contract", return_value=contract
        ), patch.object(finalizer, "sha256", return_value="a" * 64):
            with self.assertRaises(RuntimeError):
                finalizer.validate_postaudit(ROOT, value=tampered, result=result)

    def test_resealed_final_result_authorization_tamper_fails_closed(self) -> None:
        frozen_metrics = metrics()
        frozen_uncertainty = uncertainty()
        frozen_pair = pair_summary(self)
        protocol = {"decision_contract": control.DECISION_CONTRACT}
        gate = finalizer.decision(
            protocol, frozen_metrics, frozen_uncertainty, frozen_pair
        )
        live = {
            "mapping_sha256": "a" * 64,
            "query_data_sha256": "a" * 64,
            "answer_corpus_manifest_sha256": "a" * 64,
            "evaluator_source_manifest_sha256": "a" * 64,
            "judge": {"model": "synthetic"},
            "recovery_policy": {"selective_error_retry_allowed": False},
        }
        result = {
            "artifact_version": 1,
            "role": "v24657_unknown_cell_targeted_paired_dev64_result",
            "protocol_id": control.PROTOCOL_ID,
            "created_at_unix": 0,
            "status": "development_gate_go",
            "selected_per_arm": 64,
            "conservative_denominator_per_arm": 64,
            "failure_as_zero": True,
            "both_arms_exact64_before_mapping_or_evaluator_open": True,
            "both_arms_fully_evaluated_with_same_current_judge": True,
            "baseline": frozen_metrics["baseline"],
            "candidate": frozen_metrics["candidate"],
            "mechanism": frozen_pair,
            "paired_uncertainty": frozen_uncertainty,
            "decision": gate,
            "efficiency": {
                "shared_both_arm_forward_wall_seconds": 10.0,
                "both_arm_evaluator_parallel_wall_seconds": 2.0,
                "evaluator_workers_total": finalizer.TOTAL_EVALUATOR_WORKERS,
            },
            "provenance": {
                "protocol_sha256": "a" * 64,
                "forward_contract_sha256": "a" * 64,
                "forward_result_sha256": "a" * 64,
                "prediction_freeze_sha256": {
                    arm: "a" * 64 for arm in control.ARMS
                },
                **live,
                **{
                    f"{arm}_merged_eval_results_sha256": "a" * 64
                    for arm in control.ARMS
                },
            },
            "source_policy": dict(finalizer.RESULT_SOURCE_POLICY),
            "authorization": {
                "fresh_exact220_design": True,
                "fresh_exact220_launch": False,
                "additional_dev64_or_avg4": False,
                "leaderboard_submission": False,
                "sota_claim": False,
            },
            "claims": dict(finalizer.RESULT_CLAIMS),
        }
        result["result_payload_sha256"] = control.payload_sha256(result)
        stored = ({"parallel_wall_seconds": 2.0}, {"baseline": {}, "candidate": {}})
        with patch.object(finalizer, "validate_protocol", return_value=protocol), patch.object(
            finalizer,
            "validate_forward_barrier",
            return_value={"pair": frozen_pair, "forward": {"forward_wall_seconds": 10.0}},
        ), patch.object(finalizer, "_stored_final_inputs", return_value=stored), patch.object(
            finalizer,
            "_arm_metrics",
            side_effect=[frozen_metrics["baseline"], frozen_metrics["candidate"]],
        ), patch.object(
            finalizer, "paired_uncertainty", return_value=frozen_uncertainty
        ), patch.object(
            finalizer, "validate_live_evaluator_identity", return_value=live
        ), patch.object(finalizer, "sha256", return_value="a" * 64):
            self.assertEqual(
                finalizer.validate_final_result(ROOT, value=result), result
            )

        tampered = copy.deepcopy(result)
        tampered["authorization"]["sota_claim"] = True
        tampered.pop("result_payload_sha256")
        tampered["result_payload_sha256"] = control.payload_sha256(tampered)
        with patch.object(finalizer, "validate_protocol", return_value=protocol), patch.object(
            finalizer,
            "validate_forward_barrier",
            return_value={"pair": frozen_pair, "forward": {"forward_wall_seconds": 10.0}},
        ), patch.object(finalizer, "_stored_final_inputs", return_value=stored), patch.object(
            finalizer,
            "_arm_metrics",
            side_effect=[frozen_metrics["baseline"], frozen_metrics["candidate"]],
        ), patch.object(
            finalizer, "paired_uncertainty", return_value=frozen_uncertainty
        ), patch.object(
            finalizer, "validate_live_evaluator_identity", return_value=live
        ), patch.object(finalizer, "sha256", return_value="a" * 64):
            with self.assertRaises(RuntimeError):
                finalizer.validate_final_result(ROOT, value=tampered)


if __name__ == "__main__":
    unittest.main()
