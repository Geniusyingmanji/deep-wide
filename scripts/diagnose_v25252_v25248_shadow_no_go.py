#!/usr/bin/env python3
"""Content-free diagnosis of the audited V2.52.48 fresh64 shadow NO-GO."""

from __future__ import annotations

import copy
import json
import re
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25248_header_totality_shadow_external_contract as contract  # noqa: E402
from scripts import audit_v25251_header_totality_shadow_no_go as parent  # noqa: E402
from scripts import run_v25248_header_totality_shadow_external as runner  # noqa: E402


SOURCE = Path("scripts/diagnose_v25252_v25248_shadow_no_go.py")
TEST = Path("tests/test_diagnose_v25252_v25248_shadow_no_go.py")
RESULT = Path(f"results/v25252_v25248_shadow_no_go_diagnosis_v1_{contract.DATE}.json")
PARENT_AUDIT_SHA256 = "19d674babd51ec0e17cb9a9f4fb991f371aac321283dc8f4bf4a61381f8a68b0"
TASK_ROWS_SHA256 = "aa65b9bf1cccc34c687f38e282c9273a11c7af43096408eb27a0edfe442d46c5"
FORWARD_RESULT_SHA256 = "41c5d604c247d05c2087859eafd70efbe1e03a4e41e53476aedee13cba5d0507"

SHADOW_RECEIPT_ROLE = "v25232_content_free_header_totality_shadow_receipt"
SAME_RESPONSE_RECEIPT_ROLE = "v25188_content_free_export_failure_tolerant_same_response_receipt"
QUOTE_RECEIPT_ROLE = "v25180_content_free_quote_aware_production_receipt"
OBSERVED_VERTICAL_RECEIPT_ROLE = "v25165_content_free_observed_vertical_key_value_receipt"
VERTICAL_RECEIPT_ROLE = "v25158_content_free_vertical_key_value_candidate_receipt"
SPARSE_RECEIPT_ROLE = "v25135_content_free_sparse_production_receipt"
PAIRED_RECEIPT_ROLE = "v25119_content_free_grounded_target_record_paired_receipt"


def _read_json(relative: Path) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.52.52 expected JSON object")
    return value


def _read_rows() -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, contract.TASK_ROWS, tracked=True)
    output: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            value = json.loads(line)
            if not isinstance(value, dict):
                raise RuntimeError("V2.52.52 expected JSONL objects")
            output.append(value)
    return output


def _receipt_by_role(runtime_result: Mapping[str, Any], role: str) -> dict[str, Any]:
    node: Any = runtime_result
    for _ in range(16):
        if not isinstance(node, Mapping):
            break
        receipt = node.get("content_free_receipt")
        if isinstance(receipt, Mapping) and receipt.get("role") == role:
            return copy.deepcopy(dict(receipt))
        node = node.get("parent_result")
    raise ValueError(f"V2.52.52 missing content-free receipt role: {role}")


def _counter_rows(counter: Counter[tuple[int, int]]) -> list[dict[str, int]]:
    return [
        {
            "model_logical_requests": model_calls,
            "fetch_requests": fetches,
            "task_count": count,
        }
        for (model_calls, fetches), count in sorted(counter.items())
    ]


def _integer_distribution(values: Sequence[int], key: str) -> list[dict[str, int]]:
    return [{key: value, "task_count": count} for value, count in sorted(Counter(values).items())]


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    if (
        contract.git(ROOT, "status", "--porcelain")
        or contract.git(ROOT, "rev-parse", "HEAD")
        != contract.git(ROOT, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.52.52 requires clean pushed HEAD")
    if (
        contract.sha256(ROOT / contract.FORWARD_AUDIT) != PARENT_AUDIT_SHA256
        or contract.sha256(ROOT / contract.TASK_ROWS) != TASK_ROWS_SHA256
        or contract.sha256(ROOT / contract.FORWARD_RESULT) != FORWARD_RESULT_SHA256
    ):
        raise RuntimeError("V2.52.52 frozen parent hash drifted")
    audit = parent.validate_audit(_read_json(contract.FORWARD_AUDIT))
    forward = runner.validate_forward_result(_read_json(contract.FORWARD_RESULT))
    rows = _read_rows()
    if len(rows) != contract.TASK_COUNT:
        raise RuntimeError("V2.52.52 task denominator drifted")

    completed: list[dict[str, Any]] = []
    outer_failures: list[dict[str, Any]] = []
    effect_pairs: Counter[tuple[int, int]] = Counter()
    health_totals: Counter[str] = Counter()
    for raw in rows:
        required = {
            "runtime_completed", "failure_as_zero", "prediction_kind",
            "outer_failure_type", "runtime_result", "content_free_shadow_receipt",
            "effect_health", "actual_effect_snapshot", "parent_behavior_drift",
            "shadow_prediction_changed",
        }
        if not required.issubset(raw):
            raise RuntimeError("V2.52.52 task row surface drifted")
        effect = raw["actual_effect_snapshot"]
        health = raw["effect_health"]
        if not isinstance(effect, Mapping) or not isinstance(health, Mapping):
            raise RuntimeError("V2.52.52 content-free effect surface drifted")
        pair = (effect.get("model_logical_requests"), effect.get("fetch_requests"))
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in pair):
            raise RuntimeError("V2.52.52 effect count drifted")
        effect_pairs[pair] += 1
        for name, value in health.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise RuntimeError("V2.52.52 effect health drifted")
            health_totals[str(name)] += value
        if raw["runtime_completed"] is True:
            if raw["failure_as_zero"] is not False or not isinstance(raw["runtime_result"], Mapping):
                raise RuntimeError("V2.52.52 completed row drifted")
            completed.append(raw)
        else:
            if raw["failure_as_zero"] is not True or raw["runtime_result"] is not None:
                raise RuntimeError("V2.52.52 outer failure row drifted")
            outer_failures.append(raw)

    receipts: dict[str, list[dict[str, Any]]] = {
        role: []
        for role in (
            SHADOW_RECEIPT_ROLE,
            SAME_RESPONSE_RECEIPT_ROLE,
            QUOTE_RECEIPT_ROLE,
            OBSERVED_VERTICAL_RECEIPT_ROLE,
            VERTICAL_RECEIPT_ROLE,
            SPARSE_RECEIPT_ROLE,
            PAIRED_RECEIPT_ROLE,
        )
    }
    for row in completed:
        runtime_result = row["runtime_result"]
        for role in receipts:
            receipts[role].append(_receipt_by_role(runtime_result, role))

    shadow = receipts[SHADOW_RECEIPT_ROLE]
    same_response = receipts[SAME_RESPONSE_RECEIPT_ROLE]
    quote = receipts[QUOTE_RECEIPT_ROLE]
    observed_vertical = receipts[OBSERVED_VERTICAL_RECEIPT_ROLE]
    vertical = receipts[VERTICAL_RECEIPT_ROLE]
    sparse = receipts[SPARSE_RECEIPT_ROLE]
    paired = receipts[PAIRED_RECEIPT_ROLE]
    overshoot = [
        (row, sparse_receipt, paired_receipt)
        for row, sparse_receipt, paired_receipt in zip(completed, sparse, paired, strict=True)
        if row["actual_effect_snapshot"]["model_logical_requests"] > 3
        or row["actual_effect_snapshot"]["fetch_requests"] > 10
    ]
    exact_intersection = all(
        sparse_receipt["verified_source_identity_field_gain"] is True
        and sparse_receipt["revision_eligible"] is True
        and sparse_receipt["revision_synthesis_provider_forward_count"] == 1
        and sparse_receipt["revision_provider_output_valid"] is True
        and sparse_receipt["final_prediction_changed_from_production"] is False
        and paired_receipt["attributable_prediction_change"] is False
        for _row, sparse_receipt, paired_receipt in overshoot
    ) and sum(receipt["revision_eligible"] for receipt in sparse) == len(overshoot)

    diagnosis = {
        "fixed_task_denominator": len(rows),
        "completed_runtime_tasks": len(completed),
        "failure_as_zero_tasks": len(outer_failures),
        "model_generated_tasks": sum(row["prediction_kind"] == "model_generated" for row in rows),
        "fallback_tasks": sum(row["prediction_kind"] == "fallback" for row in rows),
        "outer_failure_type_counts": dict(sorted(Counter(str(row["outer_failure_type"]) for row in outer_failures).items())),
        "terminal_effect_health_totals": dict(sorted(health_totals.items())),
        "physical_effect_cross_distribution": _counter_rows(effect_pairs),
        "tasks_exceeding_declared_model3_or_fetch10": len(overshoot),
        "overshoot_tasks_exactly_sparse_verified_gain_revision_eligible": exact_intersection,
        "overshoot_revision_provider_valid_tasks": sum(item[1]["revision_provider_output_valid"] for item in overshoot),
        "overshoot_final_prediction_changed_from_production_tasks": sum(item[1]["final_prediction_changed_from_production"] for item in overshoot),
        "overshoot_attributable_prediction_change_tasks": sum(item[2]["attributable_prediction_change"] for item in overshoot),
        "sparse_verified_gain_tasks": sum(receipt["verified_source_identity_field_gain"] for receipt in sparse),
        "sparse_revision_eligible_tasks": sum(receipt["revision_eligible"] for receipt in sparse),
        "sparse_revision_provider_forward_tasks": sum(receipt["revision_synthesis_provider_forward_count"] for receipt in sparse),
        "sparse_final_prediction_changed_from_production_tasks": sum(receipt["final_prediction_changed_from_production"] for receipt in sparse),
        "sparse_fetch_count_distribution": _integer_distribution([receipt["physical_fetch_count"] for receipt in sparse], "physical_fetch_count"),
        "sparse_provider_forward_count_distribution": _integer_distribution([receipt["provider_forward_count"] for receipt in sparse], "provider_forward_count"),
        "paired_prediction_changed_tasks": sum(receipt["prediction_changed"] for receipt in paired),
        "paired_attributable_prediction_change_tasks": sum(receipt["attributable_prediction_change"] for receipt in paired),
        "vertical_revision_entry_tasks": sum(receipt["candidate_revision_entry_count"] for receipt in vertical),
        "vertical_available_candidate_tasks": sum(receipt["available_candidate_count"] > 0 for receipt in vertical),
        "vertical_applied_edit_tasks": sum(receipt["applied_edit_count"] > 0 for receipt in vertical),
        "observed_vertical_entry_tasks": sum(receipt["disposition_observer_entry_count"] for receipt in observed_vertical),
        "quote_aware_repair_applied_tasks": sum(receipt["quote_aware_repair_applied_count"] for receipt in quote),
        "same_response_counterfactual_active_tasks": sum(receipt["same_raw_counterfactual_active"] for receipt in same_response),
        "header_totality_parent_no_bindable_header_tasks": sum(receipt["parent_raw_no_bindable_header_reject"] for receipt in shadow),
        "header_totality_shadow_entry_tasks": sum(receipt["shadow_entry_count"] for receipt in shadow),
        "header_totality_safe_candidate_tasks": sum(receipt["shadow_candidate_available_count"] for receipt in shadow),
        "parent_behavior_drift_tasks": sum(row["parent_behavior_drift"] for row in rows),
        "shadow_prediction_change_tasks": sum(row["shadow_prediction_changed"] for row in rows),
        "positive_signed_credit_count": 0,
    }
    conclusions = {
        "header_totality_has_zero_natural_entry_on_all_63_completed_tasks": (
            len(completed) == 63
            and diagnosis["header_totality_parent_no_bindable_header_tasks"] == 0
            and diagnosis["header_totality_shadow_entry_tasks"] == 0
        ),
        "header_totality_population_should_not_be_retried_replaced_or_threshold_relaxed": True,
        "declared_3_model_10_fetch_cap_mismatches_frozen_parent_4_model_14_fetch_cap": (
            all(receipt["physical_model_forward_cap"] == 4 and receipt["physical_fetch_cap"] == 14 for receipt in sparse)
            and diagnosis["tasks_exceeding_declared_model3_or_fetch10"] == 3
        ),
        "all_observed_overshoot_revisions_have_zero_final_or_attributable_prediction_change": (
            exact_intersection
            and diagnosis["overshoot_final_prediction_changed_from_production_tasks"] == 0
            and diagnosis["overshoot_attributable_prediction_change_tasks"] == 0
        ),
        "one_value_error_occurs_after_nominal_3_model_10_fetch_with_zero_effect_health_failure": (
            len(outer_failures) == 1
            and outer_failures[0]["outer_failure_type"] == "ValueError"
            and outer_failures[0]["actual_effect_snapshot"]["model_logical_requests"] == 3
            and outer_failures[0]["actual_effect_snapshot"]["fetch_requests"] == 10
            and sum(outer_failures[0]["effect_health"].values()) == 0
        ),
        "value_error_exact_post_effect_stage_remains_unidentified": True,
        "next_build_requires_outer_physical_hard_cap_and_content_free_stage_observer": True,
        "observed_association_does_not_prove_quality_neutrality_on_unseen_tasks": True,
        "no_activation_quality_evaluator_or_deepwidebench_220_authorized": True,
    }
    value = {
        "artifact_version": 1,
        "role": "v25252_v25248_shadow_no_go_content_free_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            str(contract.FORWARD_AUDIT): PARENT_AUDIT_SHA256,
            str(contract.FORWARD_RESULT): FORWARD_RESULT_SHA256,
            str(contract.TASK_ROWS): TASK_ROWS_SHA256,
        },
        "parent_status": audit["status"],
        "parent_mechanism_gate_passed": audit["mechanism_gate_passed"],
        "forward_aggregate_sha256": contract.payload_sha256(forward["aggregate"]),
        "diagnosis": diagnosis,
        "conclusions": conclusions,
        "contains_opaque_id_question_package_query_url_host_title_page_prediction_answer_gold_score_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "outer_physical_hard_cap_and_content_free_stage_observer_build_only": True,
            "fresh_external_protocol_design": False,
            "retry_resume_reuse_or_replacement_of_v25248_population": False,
            "candidate_activation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "diagnosis_payload_sha256")


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    diagnosis = copied.get("diagnosis") or {}
    conclusions = copied.get("conclusions") or {}
    if (
        set(copied)
        != {
            "artifact_version", "role", "created_at_unix", "parents", "parent_status",
            "parent_mechanism_gate_passed", "forward_aggregate_sha256", "diagnosis",
            "conclusions",
            "contains_opaque_id_question_package_query_url_host_title_page_prediction_answer_gold_score_or_credential",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit", "authorization",
            "diagnosis_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25252_v25248_shadow_no_go_content_free_diagnosis"
        or copied.get("parents")
        != {
            str(contract.FORWARD_AUDIT): PARENT_AUDIT_SHA256,
            str(contract.FORWARD_RESULT): FORWARD_RESULT_SHA256,
            str(contract.TASK_ROWS): TASK_ROWS_SHA256,
        }
        or copied.get("parent_status") != "audited_mechanism_no_go"
        or copied.get("parent_mechanism_gate_passed") is not False
        or re.fullmatch(r"[0-9a-f]{64}", str(copied.get("forward_aggregate_sha256") or "")) is None
        or diagnosis.get("fixed_task_denominator") != 64
        or diagnosis.get("completed_runtime_tasks") != 63
        or diagnosis.get("failure_as_zero_tasks") != 1
        or diagnosis.get("outer_failure_type_counts") != {"ValueError": 1}
        or diagnosis.get("physical_effect_cross_distribution")
        != [
            {"model_logical_requests": 3, "fetch_requests": 10, "task_count": 61},
            {"model_logical_requests": 4, "fetch_requests": 11, "task_count": 2},
            {"model_logical_requests": 4, "fetch_requests": 14, "task_count": 1},
        ]
        or diagnosis.get("tasks_exceeding_declared_model3_or_fetch10") != 3
        or diagnosis.get("overshoot_tasks_exactly_sparse_verified_gain_revision_eligible") is not True
        or diagnosis.get("overshoot_revision_provider_valid_tasks") != 3
        or diagnosis.get("overshoot_final_prediction_changed_from_production_tasks") != 0
        or diagnosis.get("overshoot_attributable_prediction_change_tasks") != 0
        or diagnosis.get("header_totality_parent_no_bindable_header_tasks") != 0
        or diagnosis.get("header_totality_shadow_entry_tasks") != 0
        or diagnosis.get("header_totality_safe_candidate_tasks") != 0
        or diagnosis.get("positive_signed_credit_count") != 0
        or not conclusions
        or not all(conclusions.values())
        or any(
            copied.get(name) is not False
            for name in (
                "contains_opaque_id_question_package_query_url_host_title_page_prediction_answer_gold_score_or_credential",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "network_model_search_fetch_evaluator_benchmark_or_api_called",
                "entropy_or_information_gain_assigns_signed_credit",
            )
        )
        or copied.get("authorization")
        != {
            "outer_physical_hard_cap_and_content_free_stage_observer_build_only": True,
            "fresh_external_protocol_design": False,
            "retry_resume_reuse_or_replacement_of_v25248_population": False,
            "candidate_activation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or not contract.sealed(copied, "diagnosis_payload_sha256")
    ):
        raise ValueError("V2.52.52 diagnosis drifted")
    return copied


def main() -> None:
    value = validate_diagnosis(build_diagnosis())
    runner._publish_json(ROOT / RESULT, value)
    print(json.dumps({"path": str(RESULT), "role": value["role"]}, sort_keys=True))


if __name__ == "__main__":
    main()
