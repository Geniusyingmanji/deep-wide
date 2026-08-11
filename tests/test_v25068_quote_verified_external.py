from __future__ import annotations

import ast
import copy
import hashlib
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25066_quote_verified_paired_runtime as runtime  # noqa: E402
from deepwide_agent import v25068_quote_verified_external_contract as contract  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256 as runtime_sha256  # noqa: E402
from scripts import run_v25068_quote_verified_external as runner  # noqa: E402
from test_v24990_query_vector_paired_runtime import SyntheticRobustSearch  # noqa: E402


def _record_receipt(*, exposed: bool) -> dict:
    value = {
        "artifact_version": 1,
        "role": "v25065_content_free_quote_verified_record_receipt",
        "policy_id": "v25065_model_proposed_quote_verified_source_record_binding_v1",
        "input_page_count": 2,
        "bounded_page_count": 2,
        "bounded_page_characters": 100,
        "parsed_record_count": int(exposed),
        "parsed_field_count": int(exposed),
        "verified_quote_record_count": int(exposed),
        "verified_field_count": int(exposed),
        "rejected_page_reference_count": 0,
        "rejected_nonunique_or_nonverbatim_quote_count": 0,
        "rejected_row_identity_binding_count": 0,
        "rejected_field_binding_count": 0,
        "ambiguous_same_quote_record_count": 0,
        "duplicate_field_proposal_count": 0,
        "rendered_record_count": int(exposed),
        "rendered_field_count": int(exposed),
        "compact_prefix_characters": 20 if exposed else 0,
        "control_evidence_characters": 1000,
        "candidate_evidence_characters": 1000,
        "proposal_input_character_cap": 12000,
        "proposal_output_token_cap": 1200,
        "record_prefix_character_cap": 12000,
        "model_call_attempted": True,
        "model_output_strictly_valid": True,
        "candidate_evidence_changed": exposed,
        "same_forward_fetched_pages_only": True,
        "one_canonical_contiguous_quote_from_exactly_one_page_required": True,
        "source_page_quote_row_source_field_and_value_atomically_bound": True,
        "visible_target_column_requires_deterministic_lexical_source_label_binding": True,
        "repeated_row_identity_at_distinct_quote_coordinates_preserved": True,
        "same_quote_coordinate_conflict_fails_closed": True,
        "candidate_and_control_evidence_character_counts_equal": True,
        "record_blocks_rendered_atomically_without_partial_block": True,
        "component_changes_no_query_fetch_model_context_token_wall_or_network_byte_cap": True,
        "page_text_treated_as_untrusted_data": True,
        "model_proposal_or_entropy_drop_assigns_signed_credit": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "contains_question_query_url_title_page_quote_record_identity_field_value_prediction_answer_hash_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = runtime_sha256(value)
    return value


def _wave_receipt(phase: str, fetches: int) -> dict:
    question = contract.task_vector()[0]["question"]
    search = SyntheticRobustSearch(question, "999")
    queries = [f"query {phase} {index}" for index in range(2)]
    from deepwide_agent import v24996_shared_first_wave_paired_runtime as wave

    result = wave._run_wave(
        queries,
        phase=phase,
        search=search,
        fetch_cap=fetches,
        search_results_per_query=3,
    )
    return result["receipt"]


def completed_row(index: int = 0, *, exposed: bool = True, changed: bool = True) -> dict:
    first = _wave_receipt(runtime.PHASES[0], 6)
    second = _wave_receipt(runtime.PHASES[1], 4)
    record = _record_receipt(exposed=exposed)
    arm_metrics = {
        arm: {
            "effective_model_logical_call_count": 3,
            "synthesis_attempted": True,
            "model_success": True,
            "normalizer_status": "exact",
        }
        for arm in contract.ARMS
    }
    receipt = {
        "artifact_version": 1,
        "role": runtime.RECEIPT_ROLE,
        "policy_id": runtime.POLICY_ID,
        "planned_query_count": 4,
        "physical_query_count": 4,
        "physical_fetch_count": first["fetch_attempts"] + second["fetch_attempts"],
        "usable_page_count": first["usable_pages"] + second["usable_pages"],
        "shared_model_logical_call_count": 2,
        "physical_model_logical_call_count": 4,
        "model_provider_request_count": 4,
        "model_provider_attempt_count": 4,
        "control_evidence_characters": 1000,
        "candidate_evidence_characters": 1000,
        "first_synthesis_arm": contract.arm_order_vector()[index][0],
        "proposal_model_call_attempted": True,
        "proposal_model_call_success": True,
        "candidate_evidence_changed": exposed,
        "prediction_changed": changed,
        "arm_metrics": arm_metrics,
        "phase_effect_counts": {
            runtime.PHASES[0]: {
                "attempted": True,
                "failed": False,
                "physical_query_count": 2,
                "physical_fetch_count": first["fetch_attempts"],
                "wave_receipt_present": True,
            },
            runtime.PHASES[1]: {
                "attempted": True,
                "failed": False,
                "physical_query_count": 2,
                "physical_fetch_count": second["fetch_attempts"],
                "wave_receipt_present": True,
            },
        },
        "record_binding_receipt": record,
        "first_wave_receipt": first,
        "second_wave_receipt": second,
        "both_arms_share_plan_queries_search_responses_fetched_pages_and_proposal_cost": True,
        "query_vector_is_visible_plan_only_and_shared_by_both_arms": True,
        "candidate_only_treatment_is_verified_same_length_record_representation": True,
        "each_arm_effective_model_call_cap": 3,
        "physical_paired_model_call_cap": 4,
        "query_cap": 4,
        "fetch_cap": 10,
        "evidence_character_cap": 60000,
        "wall_second_cap": 240,
        "page_text_treated_as_untrusted_data": True,
        "contains_question_query_url_title_page_quote_record_identity_field_value_prediction_answer_hash_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_payload_sha256"] = runtime_sha256(receipt)
    control = "| Package | Latest version | Latest release date (YYYY-MM-DD) | Requires-Python |\n|---|---|---|---|\n| x | 1 | 2026-01-01 | >=3.10 |"
    candidate = control + (" " if changed else "")
    row = {
        "artifact_version": 1,
        "role": "v25068_quote_verified_external_task_result",
        "protocol_id": contract.PROTOCOL_ID,
        "opaque_id": contract.task_vector()[index]["opaque_id"],
        "runtime_input_keys": ["opaque_id", "question", "same_forward_public_pages"],
        "terminal": True,
        "runtime_completed": True,
        "failure_as_zero": False,
        "outer_failure_type": None,
        "arm_order": contract.arm_order_vector()[index],
        "model_success": {arm: True for arm in contract.ARMS},
        "normalizer_status": {arm: "exact" for arm in contract.ARMS},
        "predictions": {
            contract.CONTROL_ARM: control,
            contract.CANDIDATE_ARM: candidate,
        },
        "prediction_sha256": {
            contract.CONTROL_ARM: hashlib.sha256(control.encode()).hexdigest(),
            contract.CANDIDATE_ARM: hashlib.sha256(candidate.encode()).hexdigest(),
        },
        "prediction_changed": changed,
        "candidate_evidence_changed": exposed,
        "content_free_receipt": receipt,
        "cost": {
            "model": {"requests": 4, "attempts": 4, "input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            "search": {
                phase: {"calls": 1, "failures": 0, "tool_calls": 0, "fetch_calls": 0, "fetch_failures": 0, "input_tokens": 1, "output_tokens": 1, "total_tokens": 2}
                for phase in runtime.PHASES
            },
            "system_total_tokens": 6,
        },
        "failure_types": {
            "plan": None,
            "retrieval": {phase: None for phase in runtime.PHASES},
            "proposal": None,
            **{arm: None for arm in contract.ARMS},
        },
        "hard_failure_health": runner._health(),
        "elapsed_seconds": 1.0,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "retry_resume_skip_population_replacement_or_selective_rerun": False,
        "contains_question_query_url_title_page_quote_record_identity_field_value_answer_or_credential": False,
    }
    return contract.seal(row, "result_payload_sha256")


class V25068QuoteVerifiedExternalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = [
            completed_row(index, exposed=index < 8, changed=index < 4)
            for index in range(contract.TASK_COUNT)
        ]

    def test_fixed_fresh_visible_population_and_balanced_arm_order(self) -> None:
        tasks = contract.task_vector()
        self.assertEqual(len(tasks), 20)
        self.assertTrue(all(set(row) == {"opaque_id", "question"} for row in tasks))
        self.assertEqual(len({row["opaque_id"] for row in tasks}), 20)
        self.assertEqual(sum(order[0] == contract.CANDIDATE_ARM for order in contract.arm_order_vector()), 10)

    def test_contract_freezes_shared_prefix_and_no_entropy_credit(self) -> None:
        policy = contract.source_policy()
        self.assertTrue(policy["both_arms_share_queries_search_responses_fetched_pages_and_record_proposal"])
        self.assertTrue(policy["only_treatment_is_same_length_quote_verified_record_representation"])
        self.assertFalse(policy["entropy_or_information_gain_assigns_signed_credit"])

    def test_completed_task_row_validates_and_has_equal_budget(self) -> None:
        row = runner.validate_task_row(self.rows[0])
        receipt = row["content_free_receipt"]
        self.assertEqual(receipt["physical_model_logical_call_count"], 4)
        self.assertEqual(receipt["control_evidence_characters"], receipt["candidate_evidence_characters"])
        for arm in contract.ARMS:
            self.assertEqual(receipt["arm_metrics"][arm]["effective_model_logical_call_count"], 3)

        task = contract.task_vector()[0]
        runtime_result = {
            "opaque_id": task["opaque_id"],
            "model_success": row["model_success"],
            "normalizer_status": row["normalizer_status"],
            "predictions": row["predictions"],
            "prediction_sha256": row["prediction_sha256"],
            "prediction_changed": row["prediction_changed"],
            "candidate_evidence_changed": row["candidate_evidence_changed"],
            "content_free_receipt": row["content_free_receipt"],
            "cost": row["cost"],
            "failure_types": row["failure_types"],
            "elapsed_seconds": row["elapsed_seconds"],
        }
        with mock.patch.object(runtime, "validate_result", return_value=runtime_result):
            wrapped = runner._from_runtime(
                task,
                contract.arm_order_vector()[0],
                runtime_result,
                runner._health(),
            )
        self.assertTrue(runner.validate_task_row(wrapped)["runtime_completed"])

    def test_mechanism_gate_requires_exposure_and_prediction_change(self) -> None:
        aggregate = runner.aggregate_rows(self.rows, wall_seconds=1.0)
        decision = runner.mechanism_decision(aggregate)
        self.assertTrue(decision["mechanism_gate_passed"])
        aggregate["verifier_exposure_tasks"] -= 1
        self.assertFalse(runner.mechanism_decision(aggregate)["mechanism_gate_passed"])
        aggregate["verifier_exposure_tasks"] += 1
        aggregate["prediction_changed_tasks"] -= 1
        self.assertFalse(runner.mechanism_decision(aggregate)["mechanism_gate_passed"])

    def test_mechanism_gate_fails_on_any_hard_failure_or_budget_drift(self) -> None:
        aggregate = runner.aggregate_rows(self.rows, wall_seconds=1.0)
        for field in ("outer_hard_failures", "transport_search_fetch_hard_failures", "model_hard_failures"):
            changed = copy.deepcopy(aggregate)
            changed[field] = 1
            with self.subTest(field=field):
                self.assertFalse(runner.mechanism_decision(changed)["mechanism_gate_passed"])
        changed = copy.deepcopy(aggregate)
        changed["physical_queries"] -= 1
        self.assertFalse(runner.mechanism_decision(changed)["mechanism_gate_passed"])

    def test_failure_as_zero_is_terminal_but_cannot_pass_mechanism(self) -> None:
        failure = runner._terminal_outer_failure(
            contract.task_vector()[0], contract.arm_order_vector()[0], RuntimeError("x"), 1.0
        )
        checked = runner.validate_task_row(failure)
        self.assertTrue(checked["terminal"])
        self.assertTrue(checked["failure_as_zero"])
        rows = [failure, *self.rows[1:]]
        aggregate = runner.aggregate_rows(rows, wall_seconds=1.0)
        self.assertFalse(runner.mechanism_decision(aggregate)["mechanism_gate_passed"])

    def test_extra_privileged_runtime_key_and_resealed_tamper_fail_closed(self) -> None:
        for key in ("category", "question_type", "gold", "score", "reward"):
            changed = copy.deepcopy(self.rows[0])
            changed[key] = "forbidden"
            changed.pop("result_payload_sha256")
            changed = contract.seal(changed, "result_payload_sha256")
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                runner.validate_task_row(changed)

    def test_forward_sources_are_label_blind_and_evaluator_is_postfreeze_absent(self) -> None:
        forbidden = {"category", "question_type", "ground_truth", "answer_key", "gold", "score", "reward"}
        accesses: list[str] = []
        for relative in (contract.RUNNER, Path("src/deepwide_agent/v25066_quote_verified_paired_runtime.py")):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                    if node.slice.value in forbidden:
                        accesses.append(str(node.slice.value))
        self.assertEqual(accesses, [])
        self.assertFalse((ROOT / contract.EVALUATOR).exists())
        self.assertFalse(contract.source_policy()["deepwidebench_dev64_exact220_leaderboard_or_sota_authorized"])


if __name__ == "__main__":
    unittest.main()
