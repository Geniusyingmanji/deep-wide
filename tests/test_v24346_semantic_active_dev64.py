from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24308_child_exit_observability import parent_receipt  # noqa: E402
from deepwide_agent.v24342_semantic_active_runtime import run_v24342_task  # noqa: E402
from scripts import finalize_v24346_semantic_active_dev64 as finalizer  # noqa: E402
from scripts import run_v24346_semantic_active_dev64 as runner  # noqa: E402
from scripts import v24346_semantic_active_dev64_control as control  # noqa: E402
from test_v24342_semantic_active_runtime import (  # noqa: E402
    Clock,
    Model,
    Search,
    TASK,
    limits,
)


def synthetic_result():
    return run_v24342_task(
        TASK, model=Model(), search=Search(), limits=limits(), monotonic=Clock()
    )


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


def pair_summary():
    result = synthetic_result()
    receipt = result["core_result"]["shared_prefix_revision_receipt"]
    model = {
        "acquisitions": receipt["provider_model_requests"],
        "slot_timeouts": receipt["pre_provider_model_rejections"],
        "provider_deadline_failures": 0,
    }
    transport = {
        "hard_fetch_deadline_failures": 0,
        "fetch_helper_failures": 0,
        "hosted_search_deadline_failures": 0,
        "fetch_deadline_rejections": 0,
        "deadline_exhausted": False,
    }
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
            model_receipt=model,
            transport_health=transport,
        )
        for index in range(1, runner.SELECTED_COUNT + 1)
    ]
    return runner._pair_summary(outcomes, 10.0)


def metrics(value: float = 0.5):
    return {
        arm: {
            "runtime_completed": 64,
            "runtime_failed": 0,
            "evaluator_valid": 64,
            "evaluator_invalid_or_not_run": 0,
            "whole_table_successes": 1,
            "entity_acc": value,
            "f1_by_row": value,
            "f1_by_item": value,
            "column_f1": value,
            "quality_composite": value,
            "score": 1 / 64,
        }
        for arm in runner.ARMS
    }


def uncertainty():
    return {
        "task_count": 64,
        "bootstrap_unit": "paired_frozen_task",
        "seed": 24346,
        "resamples": 10_000,
        "estimand": "synthetic",
        "mean": 0.0,
        "median": 0.0,
        "positive": 0,
        "zero": 64,
        "negative": 0,
        "minimum": 0.0,
        "maximum": 0.0,
        "percentile_95_interval": [0.0, 0.0],
        "interval_width": 0.0,
        "fixed_denominator_failure_as_zero": True,
        "predictions_frozen_before_evaluator": True,
        "future_population_or_sota_inference": False,
    }


class V24346SemanticActiveDev64Tests(unittest.TestCase):
    def test_forward_contract_is_visible_only_and_evaluator_free(self) -> None:
        value = control.build_forward_contract(ROOT, now=0, require_pristine=False)
        self.assertEqual(value["task_contract"]["runtime_boundary"], ["opaque_id", "question"])
        self.assertEqual(value["task_contract"]["selected_count"], 64)
        self.assertTrue(value["execution"]["same_raw_pages_for_both_predictions"])
        self.assertTrue(value["execution"]["candidate_only_semantic_catalog_and_entropy_gate"])
        self.assertFalse(
            value["source_policy"][
                "mapping_gold_category_question_type_split_evaluator_score_read_by_forward"
            ]
        )
        self.assertFalse(any("finalize" in name or "official_eval" in name for name in value["dependency_manifest"]))

        real_sha256 = control.sha256

        def frozen_sha256(path):
            return (
                "a" * 64
                if Path(path) == ROOT / control.FORWARD_CONTRACT
                else real_sha256(path)
            )

        with patch.object(
            control, "validate_forward_contract", return_value=value
        ), patch.object(control, "sha256", side_effect=frozen_sha256):
            protocol = control.build_protocol(
                ROOT, now=0, require_pristine=False
            )
        pairing = protocol["evaluator_pairing_policy"]
        self.assertTrue(
            pairing[
                "candidate_exact_prediction_hash_identity_reuses_baseline_evaluator_row"
            ]
        )
        self.assertFalse(
            pairing[
                "routing_uses_mapping_gold_category_question_type_split_score_or_reward"
            ]
        )

    def test_forward_ast_has_no_privileged_access_or_evaluator_import(self) -> None:
        self.assertEqual(control._field_accesses(ROOT), [])
        self.assertEqual(control._import_hits(ROOT), [])

    def test_one_shared_result_projects_aligned_baseline_and_candidate(self) -> None:
        result = synthetic_result()
        baseline = runner._runtime_row(
            TASK, arm="baseline", result=result, parent_taxonomy="success"
        )
        candidate = runner._runtime_row(
            TASK, arm="candidate", result=result, parent_taxonomy="success"
        )
        self.assertEqual(baseline["opaque_id"], candidate["opaque_id"])
        self.assertEqual(baseline["cost"], candidate["cost"])
        self.assertFalse(candidate["candidate_identity_handoff"])
        self.assertGreater(candidate["semantic_projection_count"], 0)
        self.assertGreater(candidate["admitted_cell_changes"], 0)
        self.assertGreater(candidate["credited_conditional_entropy_reduction_nats"], 0)

    def test_exact64_pair_summary_conserves_effects_and_mechanism(self) -> None:
        value = pair_summary()
        runner.validate_pair_summary(value)
        self.assertEqual(value["selected_pair_tasks"], 64)
        self.assertEqual(value["effect_accounting_complete_tasks"], 64)
        self.assertEqual(value["shared_raw_page_tasks"], 64)
        self.assertEqual(value["fetch_before_baseline_tasks"], 64)
        self.assertTrue(value["model_conservation_on_complete_tasks"])
        self.assertGreater(value["candidate_nonidentity_tasks"], 0)

    def test_mechanism_and_quality_gate_go_only_with_real_activation(self) -> None:
        protocol = {"decision_contract": control.DECISION_CONTRACT}
        pair = pair_summary()
        decision = finalizer.decision(protocol, metrics(), uncertainty(), pair)
        self.assertTrue(decision["passed"])
        self.assertEqual(decision["failed_checks"], [])

        inactive = copy.deepcopy(pair)
        inactive.update(
            {
                "semantic_projection_tasks": 0,
                "eligible_support_tasks": 0,
                "revision_model_admitted_tasks": 0,
                "revision_gate_tasks": 0,
                "candidate_nonidentity_tasks": 0,
                "admitted_cell_changes": 0,
                "credited_conditional_entropy_reduction_nats": 0.0,
            }
        )
        failed = finalizer.decision(protocol, metrics(), uncertainty(), inactive)
        self.assertFalse(failed["passed"])
        self.assertIn("candidate_nonidentity_tasks", failed["failed_checks"])
        self.assertIn("positive_entropy_credit", failed["failed_checks"])

    def test_quality_regression_is_no_go_even_when_mechanism_activates(self) -> None:
        values = metrics()
        values["candidate"].update(
            {
                "entity_acc": 0.40,
                "f1_by_row": 0.40,
                "f1_by_item": 0.40,
                "column_f1": 0.40,
                "quality_composite": 0.40,
            }
        )
        decision = finalizer.decision(
            {"decision_contract": control.DECISION_CONTRACT},
            values,
            uncertainty(),
            pair_summary(),
        )
        self.assertFalse(decision["passed"])
        self.assertIn("quality_composite_delta", decision["failed_checks"])

    def test_evaluator_pairing_reuses_identical_predictions_without_scores(self) -> None:
        baseline_rows = []
        candidate_rows = []
        baseline_official = []
        candidate_official = []
        for index in range(64):
            opaque = f"task_{index:024x}"
            baseline_hash = f"{index:064x}"[-64:]
            candidate_hash = (
                "f" * 64 if index == 0 else baseline_hash
            )
            baseline_rows.append(
                {
                    "opaque_id": opaque,
                    "status": "completed",
                    "prediction_sha256": baseline_hash,
                }
            )
            candidate_rows.append(
                {
                    "opaque_id": opaque,
                    "status": "completed",
                    "prediction_sha256": candidate_hash,
                }
            )
            baseline_official.append({"instance_id": f"instance-{index}"})
            candidate_official.append({"instance_id": f"instance-{index}"})
        plan = finalizer.build_evaluation_plan(
            {
                "arms": {
                    "baseline": {"rows": baseline_rows},
                    "candidate": {"rows": candidate_rows},
                }
            },
            {
                "baseline": {"official": baseline_official},
                "candidate": {"official": candidate_official},
            },
        )
        self.assertEqual(len(plan["identity_instance_ids"]), 63)
        self.assertEqual(len(plan["changed_instance_ids"]), 1)
        self.assertEqual(len(plan["candidate_evaluate"]), 1)
        self.assertFalse(
            plan[
                "mapping_gold_category_question_type_split_score_or_reward_used_for_routing"
            ]
        )


if __name__ == "__main__":
    unittest.main()
