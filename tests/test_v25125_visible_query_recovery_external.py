from __future__ import annotations

import ast
import copy
import hashlib
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25110_exact_visible_schema as parser  # noqa: E402
from deepwide_agent import v25125_visible_query_recovery_external_contract as contract  # noqa: E402
from scripts import control_v25125_visible_query_recovery_external as control  # noqa: E402
from scripts import run_v25125_visible_query_recovery_external as runner  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from test_v25123_visible_legacy_query_compatible_runtime import (  # noqa: E402
    CompatibleModel,
    GroundedFrontierSearch,
)


def effect(**changes: int) -> dict:
    value = runner._actual_effect_snapshot(None, {})
    value.update(changes)
    value.pop("snapshot_payload_sha256")
    return contract.seal(value, "snapshot_payload_sha256")


def ideal_aggregate() -> dict:
    return {
        "task_count": 20,
        "terminal_tasks": 20,
        "completed_runtime_tasks": 20,
        "failure_as_zero_tasks": 0,
        "both_arms_model_success_tasks": 20,
        "compatible_visible_query_seed_tasks": 20,
        "plan_model_effect_failures": 0,
        "plan_transport_failures": 0,
        "plan_output_validation_failures": 0,
        "shared_first_wave_completed_tasks": 20,
        "grounded_plan_attempted_tasks": 20,
        "grounded_plan_strategy_applied_tasks": 8,
        "shared_second_wave_completed_tasks": 20,
        "selection_strategy_eligible_tasks": 6,
        "selection_changed_tasks": 4,
        "positive_target_field_page_gain_tasks": 4,
        "positive_target_field_pair_gain_tasks": 4,
        "retrieval_mechanism_engaged_tasks": 4,
        "prediction_changed_tasks": 3,
        "attributable_prediction_changed_tasks": 3,
        "unattributable_prediction_changed_tasks": 0,
        "physical_queries": 80,
        "physical_fetches": 240,
        "physical_model_logical_calls": 80,
        "model_provider_requests": 80,
        "model_provider_attempts": 80,
        "observed_all_task_model_logical_requests": 80,
        "observed_all_task_model_provider_attempts": 80,
        "observed_all_task_model_provider_requests": 80,
        "observed_all_task_logical_queries": 80,
        "observed_all_task_fetch_requests": 240,
        "observed_outer_failure_model_logical_requests": 0,
        "observed_outer_failure_logical_queries": 0,
        "observed_outer_failure_fetch_requests": 0,
        "control_effective_model_logical_calls": 60,
        "candidate_effective_model_logical_calls": 60,
        "control_logical_fetches": 200,
        "candidate_logical_fetches": 200,
        "control_evidence_characters": 1000,
        "candidate_evidence_characters": 1000,
        "outer_or_accounting_failure_tasks": 0,
        "terminal_transport_timeout_helper_or_model_hard_failures": 0,
        "query_local_mapping_failure_rows": 0,
        "control_arm_model_failures": 0,
        "candidate_arm_model_failures": 0,
        "system_total_tokens": 1000,
        "batch_wall_seconds": 1.0,
        "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
    }


class V25125VisibleQueryRecoveryExternalTests(unittest.TestCase):
    def test_fresh_population_exact_schema_and_balanced_order(self) -> None:
        tasks = contract.task_vector()
        self.assertEqual(len(tasks), 20)
        self.assertEqual(len(set(contract.CLUES)), 20)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 4)
        self.assertEqual(
            sum(order[0] == contract.CANDIDATE_ARM for order in contract.arm_order_vector()),
            10,
        )
        self.assertTrue(
            all(
                parser.extract_exact_visible_columns(task["question"])
                == list(contract.COLUMNS)
                for task in tasks
            )
        )

    def test_recovery_policy_and_gate_are_explicit(self) -> None:
        policy = contract.source_policy()
        gate = contract.mechanism_gate()
        self.assertTrue(policy["v25121_population_is_consumed_and_never_reused_resumed_or_completed"])
        self.assertTrue(policy["visible_legacy_query_seeds_are_deterministically_compatible_before_first_wave"])
        self.assertTrue(policy["outer_failure_rows_retain_content_free_actual_effect_counts"])
        self.assertFalse(policy["entropy_or_information_gain_assigns_signed_credit"])
        self.assertEqual(gate["minimum_tasks_with_compatible_visible_query_seed"], 20)
        self.assertEqual(gate["maximum_plan_transport_failures"], 0)
        self.assertEqual(gate["maximum_plan_output_validation_failures"], 0)

    def test_actual_effect_snapshot_is_content_free_and_sealed(self) -> None:
        checked = runner._validate_actual_effect_snapshot(
            effect(
                model_logical_requests=1,
                model_provider_requests=1,
                model_provider_attempts=1,
                model_provider_successes=1,
                model_slot_acquisitions=1,
                search_invocations=1,
                logical_queries=2,
                search_provider_attempts=1,
                search_provider_responses=1,
                web_search_tool_calls=1,
                fetch_invocations=1,
                fetch_requests=6,
                fetch_calls=6,
                fetch_helper_calls=6,
            )
        )
        self.assertEqual(checked["logical_queries"], 2)
        self.assertNotIn("query", checked)
        changed = copy.deepcopy(checked)
        changed["logical_queries"] = 3
        with self.assertRaises(ValueError):
            runner._validate_actual_effect_snapshot(changed)

    def test_outer_failure_retains_actual_effect_counts_and_fails_gate(self) -> None:
        observed = effect(
            model_logical_requests=1,
            model_provider_requests=1,
            model_provider_attempts=1,
            model_provider_successes=1,
            model_slot_acquisitions=1,
            search_invocations=1,
            logical_queries=2,
            search_provider_attempts=1,
            search_provider_responses=1,
            web_search_tool_calls=1,
            fetch_invocations=1,
            fetch_requests=6,
            fetch_calls=6,
            fetch_helper_calls=6,
        )
        row = runner._terminal_outer_failure(
            contract.task_vector()[0],
            contract.arm_order_vector()[0],
            ValueError("hidden message"),
            1.0,
            runner._health(),
            observed,
        )
        checked = runner.validate_task_row(row)
        self.assertFalse(checked["runtime_completed"])
        self.assertEqual(checked["actual_effect_snapshot"]["fetch_requests"], 6)

    def test_ideal_gate_requires_new_recovery_checks(self) -> None:
        aggregate = ideal_aggregate()
        self.assertTrue(runner.mechanism_decision(aggregate)["mechanism_gate_passed"])
        for name, value in (
            ("compatible_visible_query_seed_tasks", 19),
            ("plan_model_effect_failures", 1),
            ("plan_transport_failures", 1),
            ("plan_output_validation_failures", 1),
            ("attributable_prediction_changed_tasks", 0),
        ):
            changed = copy.deepcopy(aggregate)
            changed[name] = value
            with self.subTest(name=name):
                self.assertFalse(runner.mechanism_decision(changed)["mechanism_gate_passed"])

    def test_success_row_binds_stage_receipt_and_actual_effect_snapshot(self) -> None:
        task = contract.task_vector()[0]
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, contract.MODEL_SLOT_CAP + 1):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
            inner = CompatibleModel()
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=contract.MODEL_SLOT_CAP,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: GroundedFrontierSearch(task["question"], phase)
                for phase in contract.runtime.PHASES
            }
            value = contract.runtime.run_paired_task(
                task,
                model=model,
                searches=searches,
                limits=runner.ScoreFirstLimits(**contract.LIMITS),
                arm_order=contract.arm_order_vector()[0],
            )
            receipt = value["content_free_receipt"]
            actual = effect(
                model_logical_requests=receipt["physical_model_logical_call_count"],
                model_provider_requests=receipt["model_provider_request_count"],
                model_provider_attempts=receipt["model_provider_attempt_count"],
                model_provider_successes=receipt["model_provider_request_count"],
                model_slot_acquisitions=receipt["physical_model_logical_call_count"],
                search_invocations=2,
                logical_queries=receipt["physical_query_count"],
                fetch_invocations=2,
                fetch_requests=receipt["physical_fetch_count"],
                fetch_calls=receipt["physical_fetch_count"],
                fetch_helper_calls=receipt["physical_fetch_count"],
            )
            row = runner._from_runtime(
                task,
                contract.arm_order_vector()[0],
                value,
                runner._health(),
                actual,
            )
        checked = runner.validate_task_row(row)
        self.assertTrue(checked["runtime_completed"])
        self.assertGreater(
            checked["stage_failure_accounting"]["emitted_query_seed_count"], 0
        )
        self.assertEqual(
            checked["actual_effect_snapshot"]["logical_queries"],
            checked["content_free_receipt"]["physical_query_count"],
        )

    def test_task_row_rejects_effect_or_privileged_tamper(self) -> None:
        row = runner._terminal_outer_failure(
            contract.task_vector()[0],
            contract.arm_order_vector()[0],
            ValueError("x"),
            1.0,
            runner._health(),
            effect(
                model_logical_requests=1,
                model_provider_requests=1,
                model_provider_attempts=1,
            ),
        )
        for kind in ("effect", "privileged"):
            changed = copy.deepcopy(row)
            if kind == "effect":
                changed["actual_effect_snapshot"]["model_logical_requests"] += 1
            else:
                changed["category"] = "forbidden"
            changed.pop("result_payload_sha256")
            changed = contract.seal(changed, "result_payload_sha256")
            with self.subTest(kind=kind), self.assertRaises((RuntimeError, ValueError)):
                runner.validate_task_row(changed)

    def test_forward_sources_are_label_blind_and_evaluator_absent(self) -> None:
        forbidden = {"category", "question_type", "ground_truth", "answer_key", "gold", "score", "reward"}
        accesses: list[str] = []
        for relative in contract.forward_dependency_closure(ROOT):
            path = ROOT / relative
            if path.suffix != ".py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Subscript)
                    and isinstance(node.slice, ast.Constant)
                    and node.slice.value in forbidden
                ):
                    accesses.append(str(node.slice.value))
        self.assertEqual(accesses, [])
        self.assertFalse((ROOT / contract.EVALUATOR).exists())
        self.assertFalse((ROOT / contract.POSTFREEZE_GOLD).exists())

    def test_build_audit_authorizes_protocol_only(self) -> None:
        fake_tests = {
            "expected": control.EXPECTED_TESTS,
            "observed": control.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
        }
        fake_semantic = {
            "dependency_closure": [],
            "dependency_closure_sha256": "0" * 64,
            "privileged_runtime_field_accesses": [],
            "allowed_provider_rank_access": [],
            "evaluator_capabilities": [],
            "credential_literal_hits": [],
        }
        fake_freshness = {
            "parent_commit": contract.FRESHNESS_PARENT_COMMIT,
            "clue_count": 20,
            "all_exact_literal_zero_hit": True,
            "rows": [],
            "network_endpoint_page_value_model_or_evaluator_access": False,
        }
        frozen_watchers = [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in contract.EXPECTED_WATCHERS
        ]
        with mock.patch.object(control, "_tests", return_value=fake_tests), mock.patch.object(
            control, "_semantic_audit", return_value=fake_semantic
        ), mock.patch.object(control, "_history_freshness", return_value=fake_freshness), mock.patch.object(
            control, "_parent_valid", return_value=True
        ), mock.patch.object(control, "_lease_inactive", return_value=True), mock.patch.object(
            control, "_future_pristine", return_value=True
        ), mock.patch.object(contract, "watcher_snapshot", return_value=frozen_watchers):
            value = control.build_audit(now=1, require_clean=False)
        checked = control.validate_build(value)
        self.assertTrue(checked["authorization"]["protocol_generation_after_build_commit_push"])
        self.assertFalse(checked["authorization"]["external_forward"])
        self.assertFalse(checked["authorization"]["evaluator"])


if __name__ == "__main__":
    unittest.main()
