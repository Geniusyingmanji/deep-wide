from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25045_evidence_constrained_external_contract as contract  # noqa: E402
from deepwide_agent import v25044_evidence_constrained_synthesis as treatment  # noqa: E402
from scripts import run_v25045_evidence_constrained_external as runner  # noqa: E402


def completed_row() -> dict:
    evidence = "x" * contract.EVIDENCE_CHARS
    receipts = {
        arm: treatment.synthesis_prompt(
            arm,
            question=contract.task_vector()[0]["question"],
            columns=contract.COLUMNS,
            evidence=evidence,
        )[2]
        for arm in contract.ARMS
    }
    prediction = contract.FALLBACK_TABLE.replace("Unknown", "value")
    row = {
        "artifact_version": 1,
        "role": "v25045_evidence_constrained_external_task_result",
        "protocol_id": contract.PROTOCOL_ID,
        "opaque_id": contract.task_vector()[0]["opaque_id"],
        "runtime_input_keys": ["opaque_id", "question", "same_forward_public_pages"],
        "terminal": True,
        "completed": True,
        "failure_as_zero": False,
        "failure_stage": None,
        "arm_order": list(contract.ARMS),
        "search": {
            "logical_query_count": 4,
            "raw_unrecoverable_failure_count": 0,
            "selected_lead_count": 10,
            "provider_calls": 2,
            "provider_attempts": 2,
            "input_tokens": 10,
            "output_tokens": 1,
            "total_tokens": 11,
            "observed_exact_action_query_count": 4,
            "recursive_split_requests": 0,
            "transport_failures": 0,
            "hard_total_wall_timeouts": 0,
        },
        "selected_leads": 10,
        "shared_fetch_attempts": 10,
        "shared_fetch_successes": 10,
        "fetch_health": {
            "hard_fetch_helper_calls": 10,
            "hard_fetch_deadline_failures": 0,
            "fetch_helper_failures": 0,
            "fetch_deadline_rejections": 0,
        },
        "shared_evidence": {
            "usable_pages": 10,
            "raw_characters": 20_000,
            "evidence_characters": contract.EVIDENCE_CHARS,
            "fixed_budget_filled": 1,
        },
        "treatment_receipts": receipts,
        "model_success": {arm: True for arm in contract.ARMS},
        "model_attempts": {arm: 1 for arm in contract.ARMS},
        "model_usage": {
            arm: {
                "input_tokens": 100,
                "output_tokens": 10,
                "total_tokens": 110,
                "elapsed_milliseconds": 1,
                "provider_attempts": 1,
            }
            for arm in contract.ARMS
        },
        "model_hard_total_wall_timeouts": 0,
        "normalizer_status": {arm: "exact" for arm in contract.ARMS},
        "predictions": {arm: prediction for arm in contract.ARMS},
        "prediction_sha256": {arm: contract.payload_sha256(prediction) for arm in contract.ARMS},
        "prediction_changed": False,
        "wall_seconds": 1.0,
        "one_shared_split_2_plus_2_search_and_fetch_prefix": True,
        "same_evidence_bytes_columns_model_output_cap_and_deadline": True,
        "only_treatment_identity_field_record_bound_synthesis_contract": True,
        "arm_order_balanced_by_preoutcome_opaque_hash": True,
        "provider_narrative_or_snippet_used_as_active_evidence": False,
        "query_url_host_title_page_provider_payload_or_credential_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "pypi_gold_endpoint_opened": False,
        "entropy_or_information_gain_assigns_credit_or_routes": False,
        "retry_resume_skip_or_selective_rerun": False,
    }
    return contract.seal(row, "result_payload_sha256")


class V25045EvidenceConstrainedExternalTests(unittest.TestCase):
    def test_fresh_visible_task_query_and_balanced_order_vectors(self) -> None:
        tasks = contract.task_vector()
        self.assertEqual(len(tasks), contract.TASK_COUNT)
        self.assertEqual(len({row["opaque_id"] for row in tasks}), contract.TASK_COUNT)
        self.assertTrue(all(set(row) == {"opaque_id", "question"} for row in tasks))
        self.assertTrue(all(len(queries) == 4 for queries in contract.query_vector()))
        orders = contract.arm_order_vector()
        self.assertEqual(sum(order[0] == contract.CANDIDATE_ARM for order in orders), 10)

    def test_only_synthesis_contract_changes_after_shared_prefix(self) -> None:
        policy = contract.source_policy()
        self.assertTrue(policy["one_shared_production_shaped_split_2_plus_2_search_prefix"])
        self.assertTrue(policy["one_shared_task_local_union_fetch_and_evidence_prefix"])
        self.assertTrue(policy["only_treatment_identity_field_record_bound_synthesis_contract"])
        self.assertFalse(policy["entropy_or_information_gain_assigns_credit_or_routes"])

    def test_completed_task_receipts_share_exact_evidence_count(self) -> None:
        row = runner.validate_task_row(completed_row())
        counts = {
            row["treatment_receipts"][arm]["evidence_characters"]
            for arm in contract.ARMS
        }
        self.assertEqual(counts, {contract.EVIDENCE_CHARS})
        self.assertTrue(
            row["treatment_receipts"][contract.CANDIDATE_ARM][
                "candidate_requires_exact_row_identity_field_value_binding"
            ]
        )

    def test_aggregate_and_gate_require_natural_prediction_change(self) -> None:
        rows = []
        for index in range(contract.TASK_COUNT):
            row = completed_row()
            row["opaque_id"] = contract.task_vector()[index]["opaque_id"]
            row.pop("result_payload_sha256")
            if index < contract.MINIMUM_PREDICTION_CHANGES:
                row["predictions"][contract.CANDIDATE_ARM] += " "
                row["prediction_changed"] = True
                row["prediction_sha256"][contract.CANDIDATE_ARM] = (
                    contract.payload_sha256(
                        row["predictions"][contract.CANDIDATE_ARM]
                    )
                )
            row = contract.seal(row, "result_payload_sha256")
            rows.append(row)
        aggregate = runner.aggregate_rows(rows, batch_wall_seconds=1.0)
        self.assertTrue(runner.mechanism_decision(aggregate)["mechanism_gate_passed"])
        aggregate["prediction_changed_task_count"] -= 1
        self.assertFalse(runner.mechanism_decision(aggregate)["mechanism_gate_passed"])

    def test_extra_runtime_metadata_or_tamper_fails_closed(self) -> None:
        for mutation in ("category", "gold", "score", "question_type"):
            row = completed_row()
            row[mutation] = "forbidden"
            row.pop("result_payload_sha256")
            row = contract.seal(row, "result_payload_sha256")
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                runner.validate_task_row(row)
        row = completed_row()
        row["treatment_receipts"][contract.CANDIDATE_ARM][
            "candidate_forbids_general_knowledge_completion"
        ] = False
        row.pop("result_payload_sha256")
        row = contract.seal(row, "result_payload_sha256")
        with self.assertRaises((RuntimeError, ValueError)):
            runner.validate_task_row(row)

    def test_failure_as_zero_cannot_preserve_one_arm_prediction(self) -> None:
        row = completed_row()
        row["completed"] = False
        row["failure_as_zero"] = True
        row["failure_stage"] = "synthetic"
        row.pop("result_payload_sha256")
        row = contract.seal(row, "result_payload_sha256")
        with self.assertRaises(RuntimeError):
            runner.validate_task_row(row)

    def test_contract_withholds_benchmark_and_quality_requires_strict_exact_gain(self) -> None:
        self.assertFalse(
            contract.source_policy()[
                "deepwidebench_dev64_exact220_leaderboard_or_sota_authorized"
            ]
        )
        self.assertTrue(contract.quality_gate()["candidate_exact_strict_gain"])
        self.assertTrue(contract.quality_gate()["entity_row_item_column_nonregression"])


if __name__ == "__main__":
    unittest.main()
