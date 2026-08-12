from __future__ import annotations

import ast
import copy
import hashlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25267_production_only_exact220_contract as contract  # noqa: E402
from scripts import control_v25267_production_only_exact220 as control  # noqa: E402
from scripts import finalize_v25267_production_only_exact220 as finalizer  # noqa: E402
from scripts import run_v25267_production_only_exact220 as runner  # noqa: E402


class V25267ProductionOnlyExact220Tests(unittest.TestCase):
    def test_public_exact220_vector_is_byte_bound(self) -> None:
        tasks = contract.task_vector(ROOT)
        self.assertEqual(tasks, contract.task_parent.task_vector(ROOT))
        self.assertEqual(len(tasks), 220)
        self.assertEqual(
            contract.payload_sha256([row["opaque_id"] for row in tasks]),
            "3c4b3eeb6cadbc9ce8b22552f294a0322e820dbb4be29c3e7fb2f99a4f83665a",
        )
        self.assertEqual(
            contract.payload_sha256([row["question"] for row in tasks]),
            "d009f9f13b51e48e249f6698b3b1417d3a62c7100c8551b1cb025e726bcd82b7",
        )

    def test_reliability_parents_are_hash_bound(self) -> None:
        value = contract.parent_receipts(ROOT, tracked=True)
        self.assertEqual(value["v25264_reliability_diagnosis"]["sha256"], contract.DIAGNOSIS_SHA256)
        self.assertEqual(value["v25254_cap_build_audit"]["sha256"], contract.CAP_BUILD_AUDIT_SHA256)

    def test_protocol_is_label_blind_production_only_and_not_preactivated(self) -> None:
        value = contract.build_protocol(
            ROOT,
            now=1,
            tracked=False,
            require_pristine=False,
            build_audit_sha256="0" * 64,
        )
        self.assertEqual(value["task_contract"]["selected_count"], 220)
        self.assertEqual(value["execution"]["executor_concurrency"], 40)
        self.assertEqual(value["execution"]["model_slot_cap"], 16)
        self.assertEqual(value["execution"]["truthful_physical_caps"], {"queries_per_task": 4, "fetches_per_task": 14, "model_forwards_per_task": 4})
        self.assertTrue(value["source_policy"]["first_validated_sparse_production_is_only_scored_prediction"])
        self.assertFalse(value["source_policy"]["header_quote_vertical_candidate_or_revision_prediction_used"])
        self.assertFalse(value["authorization"]["single_exact220_forward"])

    def test_visible_fallback_preserves_explicit_columns(self) -> None:
        value = runner._visible_fallback("Return columns exactly: Package | Version | License.")
        self.assertIn("| Package | Version | License |", value)
        self.assertIn("| Unknown | Unknown | Unknown |", value)

    def test_terminal_outer_failure_is_total_and_label_blind(self) -> None:
        task = contract.task_vector(ROOT)[0]
        budget = cap.PhysicalEffectBudget()
        value = runner._terminal_outer_failure(task, RuntimeError("secret"), 1.0, budget, None, {})
        checked = runner.validate_task_row(value)
        self.assertTrue(checked["failure_as_zero"])
        self.assertFalse(checked["runtime_completed"])
        self.assertNotIn("secret", str(checked))

    def test_summary_is_terminal_and_credit_zero(self) -> None:
        value = contract.seal(
            {
                "artifact_version": 1,
                "role": contract.SUMMARY_ROLE,
                "protocol_id": contract.PROTOCOL_ID,
                "selected": 220,
                "completed": 220,
                "failed": 0,
                "runtime_completed": 210,
                "failure_as_zero_tasks": 10,
                "model_generated_tables": 200,
                "fallback_tables": 20,
                "system_total_tokens": 1,
                "forward_wall_seconds": 2.0,
                "official_evaluator_called": False,
                "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
                "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
                "entropy_or_information_gain_assigns_signed_credit": False,
                "positive_signed_credit_count": 0,
            },
            "summary_payload_sha256",
        )
        self.assertEqual(runner.validate_summary(value), value)

    def test_attempt_claim_tamper_fails_closed(self) -> None:
        value = contract.seal(
            {
                "artifact_version": 1,
                "role": runner.ATTEMPT_ROLE,
                "protocol_id": contract.PROTOCOL_ID,
                "created_at_unix": 1,
                "protocol_sha256": "a" * 64,
                "execution_start_sha256": "b" * 64,
                "execution_start_payload_sha256": "c" * 64,
                "task_vector_sha256": "d" * 64,
                "selected": 220,
                "attempt_authority_consumed_before_endpoint_model_search_fetch_or_output_effect": True,
                "retry_resume_skip_backfill_replacement_selective_rerun_or_second_attempt": False,
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
                "entropy_or_information_gain_assigns_signed_credit": False,
                "evaluator_deepwidebench_avg4_leaderboard_or_sota": False,
            },
            "claim_payload_sha256",
        )
        self.assertEqual(runner.validate_attempt_claim(value), value)
        changed = copy.deepcopy(value)
        changed["retry_resume_skip_backfill_replacement_selective_rerun_or_second_attempt"] = True
        changed = contract.seal(changed, "claim_payload_sha256")
        with self.assertRaises(ValueError):
            runner.validate_attempt_claim(changed)

    def test_aggregate_enforces_truthful_caps_and_fixed_denominator(self) -> None:
        value = {
            **{name: 0 for name in runner.AGGREGATE_INTS},
            "task_count": 220,
            "terminal_tasks": 220,
            "completed_runtime_tasks": 220,
            "model_generated_tasks": 220,
            "budget_receipt_tasks": 220,
            "maximum_queries_on_one_task": 4,
            "maximum_fetches_on_one_task": 14,
            "maximum_model_forwards_on_one_task": 4,
            "batch_wall_seconds": 1.0,
            "contains_question_query_url_page_answer_prediction_or_credential": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "evaluator_or_quality_metric_called": False,
        }
        self.assertEqual(runner.validate_aggregate(value), value)
        changed = copy.deepcopy(value)
        changed["maximum_model_forwards_on_one_task"] = 5
        with self.assertRaises(ValueError):
            runner.validate_aggregate(changed)

    def test_finalizer_uses_fixed_32_worker_postfreeze_surface(self) -> None:
        finalizer.configure()
        self.assertIs(finalizer.base.contract, contract)
        self.assertEqual(finalizer.base.EVALUATOR_WORKERS, 32)
        self.assertEqual(finalizer.base.EVALUATOR_PROTOCOL, contract.EVALUATOR_PROTOCOL)
        self.assertEqual(finalizer.base.FINAL_RESULT, contract.RESULT)
        self.assertIs(finalizer.base._forward_barrier, finalizer._forward_barrier)

    def test_runtime_rejects_nonvisible_input_key(self) -> None:
        task = dict(contract.task_vector(ROOT)[0])
        task["category"] = "forbidden"
        with self.assertRaises(ValueError):
            runner.run_one_task(task)

    def test_direct_runtime_ast_has_no_privileged_access(self) -> None:
        self.assertEqual(control._runtime_direct_privileged_accesses(), [])
        for relative in (contract.CONTRACT, contract.RUNNER, contract.RUNTIME):
            self.assertIsInstance(ast.parse((ROOT / relative).read_text(encoding="utf-8")), ast.Module)


if __name__ == "__main__":
    unittest.main()
