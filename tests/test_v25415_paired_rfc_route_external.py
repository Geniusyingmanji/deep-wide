from __future__ import annotations

import ast
import copy
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25375_schema_total_changed_safe_runtime as stable  # noqa: E402
from deepwide_agent import v25401_grounded_record_membership_runtime as member  # noqa: E402
from deepwide_agent import v25411_visible_membership_route_runtime as route  # noqa: E402
from deepwide_agent import v25415_paired_rfc_route_external_contract as contract  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from scripts import audit_v25136_sparse_production_build as semantic  # noqa: E402
from scripts import run_v25415_paired_rfc_route_external as runner  # noqa: E402
from test_v25123_visible_legacy_query_compatible_runtime import QUESTION  # noqa: E402
from test_v25395_visible_membership_synthesis_runtime import (  # noqa: E402
    MEMBERSHIP_QUESTION,
)
from test_v25401_grounded_record_membership_runtime import (  # noqa: E402
    DualIdentitySearch,
    GroundedMembershipModel,
    run_runtime,
)


def _population_row(branch: str):
    task = next(
        task
        for task in contract.task_vector()
        if route.route_for_visible_question(task["question"]) == branch
    )
    model = GroundedMembershipModel()
    with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
        root = Path(raw)
        slots = root / "slots"
        slots.mkdir()
        for index in range(1, 5):
            (slots / f"slot_{index:02d}.lock").write_text("{}\n")
        bounded = DeadlineAwareGlobalModelSlotLimiter(
            model,
            slot_directory=slots,
            output_root=root,
            slot_cap=4,
            absolute_deadline=time.monotonic() + 240,
        )
        budget = cap.PhysicalEffectBudget()
        outer = cap.HardCappedModelLimiter(bounded, budget)
        searches = {
            phase: cap.HardCappedSearchClient(
                DualIdentitySearch(task["question"], phase),
                budget,
                phase=phase,
            )
            for phase in route.PHASES
        }
        result, stage = route.run_task(
            task,
            model=outer,
            searches=searches,
            limits=ScoreFirstLimits(**contract.LIMITS),
            budget=budget,
            monotonic=time.monotonic,
        )
        row = runner._from_runtime(
            task,
            result,
            stage,
            elapsed=1.0,
            budget=budget,
            health=runner._health(),
        )
    return model, runner.validate_task_row(row)


def passing_aggregate() -> dict:
    values = {name: 0 for name in runner.AGGREGATE_INTEGER_FIELDS}
    values.update(
        {
            "task_count": 40,
            "pair_count": 20,
            "terminal_tasks": 40,
            "membership_absent_tasks": 20,
            "membership_present_tasks": 20,
            "completed_runtime_tasks": 40,
            "failure_as_zero_tasks": 0,
            "membership_absent_completed_tasks": 20,
            "membership_present_completed_tasks": 20,
            "membership_absent_outer_failure_tasks": 0,
            "membership_present_outer_failure_tasks": 0,
            "outer_failure_stage_receipt_tasks": 0,
            "naked_outer_failure_tasks": 0,
            "membership_absent_parent_role_tasks": 20,
            "membership_present_parent_role_tasks": 20,
            "first_wave_completed_tasks": 40,
            "second_wave_completed_tasks": 40,
            "grounded_plan_provider_success_tasks": 40,
            "base_synthesis_success_tasks": 40,
            "exact_canonical_base_table_tasks": 40,
            "present_membership_constraint_applied_tasks": 20,
            "present_base_visible_membership_exact_tasks": 18,
            "present_grounded_record_constraint_applied_tasks": 20,
            "present_grounded_raw_record_tasks": 4,
            "present_grounded_raw_record_count": 4,
            "present_grounded_raw_membership_match_count": 4,
            "present_grounded_raw_membership_mismatch_count": 0,
            "present_grounded_raw_membership_unclassified_count": 0,
            "present_grounded_raw_membership_violation_count": 0,
            "present_verified_record_tasks": 2,
            "present_verified_record_count": 2,
            "present_verified_field_count": 2,
            "present_missing_row_rejected_field_count": 0,
            "present_changed_safe_coordinate_tasks": 2,
            "present_changed_safe_coordinate_count": 2,
            "attributable_prediction_changed_tasks": 2,
            "unattributable_prediction_changed_tasks": 0,
            "budget_rejection_tasks": 0,
            "all_physical_queries": 160,
            "all_physical_fetches": 400,
            "all_physical_model_forwards": 120,
            "completed_physical_queries": 160,
            "completed_physical_fetches": 400,
            "completed_physical_model_forwards": 120,
            "per_task_hard_cap_preserved_tasks": 40,
            "fallback_tasks": 0,
            "positive_signed_credit_count": 0,
            "system_total_tokens": 1,
        }
    )
    return runner.validate_aggregate(
        {
            **values,
            "batch_wall_seconds": 1.0,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "question_prediction_query_url_page_record_value_or_credential_persisted_in_aggregate": False,
        }
    )


class V25415PairedRfcRouteExternalTests(unittest.TestCase):
    def test_contract_population_branches_budget_and_gates_are_frozen(self) -> None:
        self.assertEqual(len(contract.task_vector()), 40)
        self.assertEqual(contract.population.RFC_NUMBERS, tuple(range(9320, 9400)))
        self.assertEqual(contract.PAIR_COUNT, 20)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 40)
        self.assertEqual(contract.MODEL_SLOT_CAP, 16)
        self.assertEqual(
            [
                route.route_for_visible_question(task["question"])
                for task in contract.task_vector()
            ].count(route.STABLE_BRANCH),
            20,
        )
        gate = contract.mechanism_gate()
        self.assertEqual(gate["required_membership_absent_completed_tasks"], 20)
        self.assertEqual(gate["minimum_membership_present_completed_tasks"], 18)
        self.assertEqual(gate["maximum_naked_outer_failure_tasks"], 0)
        self.assertEqual(gate["minimum_present_grounded_raw_record_tasks"], 4)
        self.assertEqual(gate["minimum_present_verified_record_tasks"], 2)
        quality = contract.quality_gate()
        self.assertTrue(
            quality["membership_present_whole_table_exact_strictly_greater_than_absent"]
        )
        self.assertTrue(
            quality["paired_task_quality_is_not_claimed_as_shared_sampling_causal_effect"]
        )

    def test_union_decoder_accepts_both_frozen_parent_surfaces(self) -> None:
        for branch, module, question in (
            (route.STABLE_BRANCH, stable, QUESTION),
            (route.MEMBERSHIP_BRANCH, member, MEMBERSHIP_QUESTION),
        ):
            result, stage, _ = run_runtime(
                module, GroundedMembershipModel(), question=question
            )
            decoded = runner._decode_completed(result, stage, branch)
            with self.subTest(branch=branch):
                self.assertEqual(decoded["result"], result)
                self.assertEqual(decoded["stage"], stage)
                self.assertEqual(decoded["budget"]["model_admitted_count"], 3)
                if branch == route.STABLE_BRANCH:
                    self.assertIsNone(decoded["grounded_membership"])
                    self.assertIsNone(decoded["hybrid"])
                else:
                    self.assertTrue(
                        decoded["grounded_membership"][
                            "grounded_record_membership_constraint_applied"
                        ]
                    )
                    self.assertIsNotNone(decoded["hybrid"])

    def test_cross_branch_union_decode_fails_closed(self) -> None:
        stable_result, stable_stage, _ = run_runtime(
            stable, GroundedMembershipModel(), question=QUESTION
        )
        member_result, member_stage, _ = run_runtime(
            member, GroundedMembershipModel(), question=MEMBERSHIP_QUESTION
        )
        for result, stage, branch in (
            (stable_result, member_stage, route.STABLE_BRANCH),
            (member_result, stable_stage, route.MEMBERSHIP_BRANCH),
            (stable_result, stable_stage, route.MEMBERSHIP_BRANCH),
            (member_result, member_stage, route.STABLE_BRANCH),
        ):
            with self.subTest(branch=branch), self.assertRaises(ValueError):
                runner._decode_completed(result, stage, branch)

    def test_real_population_tasks_freeze_and_replay_both_branch_rows(self) -> None:
        for branch, expected_role in (
            (route.STABLE_BRANCH, stable.ROLE),
            (route.MEMBERSHIP_BRANCH, member.ROLE),
        ):
            model, row = _population_row(branch)
            with self.subTest(branch=branch):
                self.assertEqual(model.logical_calls, 3)
                self.assertTrue(row["runtime_completed"])
                self.assertEqual(row["route_branch"], branch)
                self.assertEqual(row["route_parent_role"], expected_role)
                self.assertEqual(
                    row["runtime_result_payload_sha256"],
                    row["runtime_result"]["result_payload_sha256"],
                )
                self.assertEqual(
                    row["actual_effect_snapshot"]["query_admitted_count"], 4
                )
                self.assertLessEqual(
                    row["actual_effect_snapshot"]["fetch_admitted_count"], 14
                )
                self.assertEqual(
                    row["actual_effect_snapshot"]["model_admitted_count"], 3
                )

    def test_failure_stage_is_retained_and_naked_failure_is_distinguished(self) -> None:
        task = contract.task_vector()[0]
        budget = cap.PhysicalEffectBudget()
        receipt = route._failure_stage_receipt(
            branch=route.STABLE_BRANCH,
            failure_stage="selected_parent_runtime",
            exc=ValueError("synthetic"),
            budget=budget,
        )
        row = runner._terminal_outer_failure(
            task,
            route.ProductionOnlyStageError(receipt),
            1.0,
            budget=budget,
            health=runner._health(),
        )
        self.assertIsNotNone(row["content_free_stage_receipt"])
        naked = runner._terminal_outer_failure(
            task,
            ValueError("synthetic"),
            1.0,
            budget=budget,
            health=runner._health(),
        )
        self.assertIsNone(naked["content_free_stage_receipt"])

    def test_passing_route_gate_and_each_critical_threshold_fail_closed(self) -> None:
        aggregate = passing_aggregate()
        self.assertTrue(runner.mechanism_decision(aggregate)["route_gate_passed"])
        cases = (
            ("membership_absent_completed_tasks", 19),
            ("membership_present_completed_tasks", 17),
            ("membership_absent_parent_role_tasks", 19),
            ("membership_present_parent_role_tasks", 17),
            ("naked_outer_failure_tasks", 1),
            ("present_grounded_record_constraint_applied_tasks", 17),
            ("present_grounded_raw_record_tasks", 3),
            ("present_grounded_raw_record_count", 3),
            ("present_grounded_raw_membership_violation_count", 3),
            ("present_verified_record_tasks", 1),
            ("completed_physical_model_forwards", 119),
        )
        for field, value in cases:
            changed = copy.deepcopy(aggregate)
            changed[field] = value
            if field == "naked_outer_failure_tasks":
                changed["failure_as_zero_tasks"] = 1
                changed["outer_failure_stage_receipt_tasks"] = 0
                changed["membership_present_completed_tasks"] = 19
                changed["membership_present_outer_failure_tasks"] = 1
            if field == "present_grounded_raw_membership_violation_count":
                changed["present_grounded_raw_membership_mismatch_count"] = 3
                changed["present_grounded_raw_membership_match_count"] = 1
            with self.subTest(field=field):
                try:
                    decision = runner.mechanism_decision(changed)
                except ValueError:
                    decision = {"route_gate_passed": False}
                self.assertFalse(decision["route_gate_passed"])

    def test_aggregate_shape_and_credit_tamper_fail_closed(self) -> None:
        aggregate = passing_aggregate()
        for kind in ("denominator", "raw_partition", "credit", "privileged"):
            changed = copy.deepcopy(aggregate)
            if kind == "denominator":
                changed["task_count"] = 39
            elif kind == "raw_partition":
                changed["present_grounded_raw_membership_match_count"] = 3
            elif kind == "credit":
                changed["positive_signed_credit_count"] = 1
            else:
                changed["category"] = "forbidden"
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                runner.validate_aggregate(changed)

    def test_forward_result_only_authorizes_audit_not_quality_or_benchmark(self) -> None:
        aggregate = passing_aggregate()
        value = contract.seal(
            {
                "artifact_version": 1,
                "role": runner.FORWARD_ROLE,
                "protocol_id": contract.PROTOCOL_ID,
                "created_at_unix": 1,
                "execution_start_sha256": "a" * 64,
                "execution_start_payload_sha256": "b" * 64,
                "task_rows_sha256": "c" * 64,
                "prediction_freeze_sha256": "d" * 64,
                "aggregate": aggregate,
                "mechanism_decision": runner.mechanism_decision(aggregate),
                "authorization": {
                    "forward_audit": True,
                    "postfreeze_quality_protocol": False,
                    "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
                    "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
                },
            },
            "result_payload_sha256",
        )
        self.assertEqual(runner.validate_forward_result(value), value)
        changed = copy.deepcopy(value)
        changed["authorization"]["postfreeze_quality_protocol"] = True
        changed.pop("result_payload_sha256")
        changed = contract.seal(changed, "result_payload_sha256")
        with self.assertRaises(ValueError):
            runner.validate_forward_result(changed)

    def test_privileged_task_rejected_before_effect(self) -> None:
        task = dict(contract.task_vector()[0])
        task["question_type"] = "forbidden"
        for effect_name in (
            "HardTotalWallResponsesClient",
            "RobustLatePageBoundSearchClient",
        ):
            with self.subTest(effect=effect_name), mock.patch.object(
                runner,
                effect_name,
                side_effect=AssertionError("effect boundary crossed"),
            ), self.assertRaises(ValueError):
                runner.run_one_task(task)

    def test_forward_closure_is_label_blind_and_evaluator_free(self) -> None:
        closure = contract.forward_dependency_closure(ROOT)
        findings = semantic._semantic_findings(closure)
        self.assertEqual(findings["privileged_runtime_field_accesses"], [])
        self.assertEqual(findings["evaluator_capabilities"], [])
        self.assertEqual(findings["credential_literal_hits"], [])
        source = (ROOT / contract.RUNNER).read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden = {
            "category",
            "question_type",
            "task_category",
            "split",
            "ground_truth",
            "gold",
            "answer_key",
            "score",
            "reward",
        }
        accesses = [
            node.slice.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value in forbidden
        ]
        self.assertEqual(accesses, [])


if __name__ == "__main__":
    unittest.main()
