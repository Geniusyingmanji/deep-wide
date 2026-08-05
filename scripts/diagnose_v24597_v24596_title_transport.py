#!/usr/bin/env python3
"""Content-free diagnosis of V2.45.96's title acquisition boundary.

Only the sealed public result, decision, and post-result audit are opened.
No task, query, URL, title, page, prediction, private execution directory,
benchmark mapping, gold data, evaluator output, or credential is read.

The aggregate proves that the validator-aligned query policy ran, candidates
survived exact-URL de-duplication, and same-source representatives changed.
It does not distinguish an empty search-result title from a non-empty title
whose row surface is absent, late, or type-incompatible.  The next safe step
is therefore content-free title-funnel observability, not another query or
validator change.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256, sha256  # noqa: E402
from scripts import v24596_validator_aligned_title_query_external_gate as run  # noqa: E402


DATE = "20260805"
OUTPUT = Path(f"results/v24597_v24596_title_transport_diagnosis_v1_{DATE}.json")


def _read(path: Path) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.45.97 expected public object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _public_chain() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    result = _read(run.RESULT)
    decision = _read(run.DECISION)
    postaudit = _read(run.POSTAUDIT)
    if (
        not _sealed(result, "result_payload_sha256")
        or not _sealed(decision, "decision_payload_sha256")
        or not _sealed(postaudit, "audit_payload_sha256")
        or result.get("protocol_id") != run.PROTOCOL_ID
        or result.get("selected") != 8
        or result.get("passed") is not False
        or result.get("mechanism_passed") is not False
        or result.get("reliability_passed") is not True
        or result.get("parent_validation_passed") is not True
        or result.get("latency_passed") is not True
        or decision.get("status") != "fresh_validator_aligned_title_query_no_go"
        or decision.get("result_sha256") != sha256(ROOT / run.RESULT)
        or decision.get("diagnostic_route")
        != "validator_aligned_title_acquisition_successor"
        or decision.get("authorization", {}).get("fresh_paired_dev64_design")
        is not False
        or decision.get("authorization", {}).get("new_exact220") is not False
        or postaudit.get("result_sha256") != sha256(ROOT / run.RESULT)
        or postaudit.get("decision_sha256") != sha256(ROOT / run.DECISION)
        or postaudit.get("audit_valid") is not True
        or postaudit.get("findings") != []
        or postaudit.get("shared_api_lease_active") is not False
    ):
        raise RuntimeError("V2.45.97 public chain drifted")
    return result, decision, postaudit


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    result, decision, postaudit = _public_chain()
    mechanism = result["mechanism_aggregate"]
    alias = mechanism["total_alias_surface_count_fields"]
    selection = mechanism["total_validator_aligned_selection_count_fields"]
    preservation = mechanism["total_prededup_preservation_count_fields"]
    query = mechanism["total_validator_aligned_title_query_count_fields"]
    supervision = result["supervision_aggregate"]

    if not (
        mechanism["success_tasks"] == 8
        and mechanism["failure_as_zero_tasks"] == 0
        and supervision["worker_success_tasks"] == 8
        and supervision["worker_hard_timeout_tasks"] == 0
        and supervision["worker_nonzero_tasks"] == 0
        and mechanism["target_plan_tasks"] == 7
        and mechanism["validator_aligned_title_query_activity_tasks"] == 7
        and mechanism["validator_aligned_title_query_full_surface_tasks"] == 7
        and mechanism["validator_aligned_title_query_core_surface_tasks"] == 7
        and query["query_vector_calls"] > 0
        and query["logical_query_count"] == 2 * query["query_vector_calls"]
        and alias["visible_lead_count"] > 0
        and alias["url_alias_surface_hit_lead_count"] > 0
        and alias["title_alias_surface_hit_lead_count"] == 0
        and alias["selected_title_alias_surface_hit_lead_count"] == 0
        and preservation["exact_url_distinct_lead_count"] > 0
        and preservation["preserved_candidate_count"] > 0
        and selection["source_representative_replacement_count"] > 0
        and selection["validator_aligned_title_replacement_count"] == 0
        and mechanism[
            "validator_aligned_title_query_and_title_replacement_cooccurrence_tasks"
        ]
        == 0
        and postaudit["mapping_gold_category_question_type_split_evaluator_score_read"]
        is False
        and postaudit["private_task_or_web_content_persisted"] is False
    ):
        raise RuntimeError("V2.45.97 diagnosis premises drifted")

    value = {
        "artifact_version": 1,
        "role": "v24597_v24596_title_transport_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "query_and_candidate_paths_reached_strict_title_surface_still_absent",
        "public_chain": {
            "result_path": str(run.RESULT),
            "result_sha256": sha256(ROOT / run.RESULT),
            "decision_path": str(run.DECISION),
            "decision_sha256": sha256(ROOT / run.DECISION),
            "postaudit_path": str(run.POSTAUDIT),
            "postaudit_sha256": sha256(ROOT / run.POSTAUDIT),
            "decision_status": decision["status"],
            "diagnostic_route": decision["diagnostic_route"],
        },
        "engineering_outcome": {
            "selected": int(result["selected"]),
            "success_tasks": int(mechanism["success_tasks"]),
            "failure_as_zero_tasks": int(mechanism["failure_as_zero_tasks"]),
            "worker_success_tasks": int(supervision["worker_success_tasks"]),
            "worker_hard_timeout_tasks": int(
                supervision["worker_hard_timeout_tasks"]
            ),
            "worker_nonzero_tasks": int(supervision["worker_nonzero_tasks"]),
            "batch_wall_seconds": float(result["batch_wall_seconds"]),
            "reliability_passed": True,
            "parent_validation_passed": True,
            "latency_passed": True,
        },
        "acquisition_funnel": {
            "target_plan_tasks": int(mechanism["target_plan_tasks"]),
            "title_query_activity_tasks": int(
                mechanism["validator_aligned_title_query_activity_tasks"]
            ),
            "title_query_full_surface_tasks": int(
                mechanism["validator_aligned_title_query_full_surface_tasks"]
            ),
            "title_query_core_surface_tasks": int(
                mechanism["validator_aligned_title_query_core_surface_tasks"]
            ),
            "query_vector_calls": int(query["query_vector_calls"]),
            "logical_query_count": int(query["logical_query_count"]),
            "visible_lead_count": int(alias["visible_lead_count"]),
            "url_alias_surface_hit_lead_count": int(
                alias["url_alias_surface_hit_lead_count"]
            ),
            "selected_url_alias_surface_hit_lead_count": int(
                alias["selected_url_alias_surface_hit_lead_count"]
            ),
            "title_alias_surface_hit_lead_count": int(
                alias["title_alias_surface_hit_lead_count"]
            ),
            "selected_title_alias_surface_hit_lead_count": int(
                alias["selected_title_alias_surface_hit_lead_count"]
            ),
            "exact_url_distinct_lead_count": int(
                preservation["exact_url_distinct_lead_count"]
            ),
            "registrable_source_count": int(
                preservation["registrable_source_count"]
            ),
            "preserved_candidate_count": int(
                preservation["preserved_candidate_count"]
            ),
            "source_representative_replacement_count": int(
                selection["source_representative_replacement_count"]
            ),
            "validator_aligned_title_replacement_count": int(
                selection["validator_aligned_title_replacement_count"]
            ),
            "title_query_and_title_replacement_cooccurrence_tasks": int(
                mechanism[
                    "validator_aligned_title_query_and_title_replacement_cooccurrence_tasks"
                ]
            ),
        },
        "conclusions": {
            "query_policy_executed": True,
            "aggregate_query_activity_task_count_equals_target_plan_task_count": True,
            "exactly_two_logical_queries_per_query_vector_call_observed": True,
            "candidate_discovery_and_prededup_preservation_reached": True,
            "same_source_representative_selection_reached": True,
            "strict_title_alias_surface_reached": False,
            "url_surface_retrieval_reached": True,
            "zero_strict_title_hits_proves_search_result_titles_are_empty": False,
            "zero_strict_title_hits_proves_row_tokens_are_absent_from_titles": False,
            "zero_strict_title_hits_proves_alias_match_start_limit_is_too_strict": False,
            "zero_strict_title_hits_proves_type_compatibility_is_too_strict": False,
            "public_aggregate_distinguishes_empty_absent_late_and_type_incompatible_title_failure": False,
            "cross_population_comparison_proves_v24589_query_policy_hurt_recall": False,
            "next_successor_must_measure_content_free_title_funnel": True,
            "next_successor_should_change_query_or_validator_before_title_funnel_measurement": False,
            "query_search_fetch_model_page_source_or_evaluator_budget_increase_allowed": False,
            "title_or_url_hint_may_receive_evidence_entropy_or_decision_credit": False,
            "benchmark_quality_or_sota_improvement_measured": False,
        },
        "required_next_observability": {
            "distinct_visible_lead_count": True,
            "nonempty_title_lead_count": True,
            "canonical_row_token_anywhere_title_count": True,
            "full_or_core_surface_anywhere_title_count": True,
            "surface_rejected_only_by_maximum_start_count": True,
            "surface_rejected_only_by_type_compatibility_count": True,
            "strict_validator_aligned_title_count": True,
            "raw_title_query_url_or_page_text_emitted": False,
        },
        "source_policy": {
            "sealed_public_aggregate_decision_and_postaudit_only": True,
            "task_question_query_url_title_page_prediction_candidate_value_or_private_directory_opened": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "network_model_search_fetch_process_or_evaluator_called": False,
            "credential_read_hashed_persisted_or_emitted": False,
        },
        "authorization": {
            "content_free_title_transport_observability_design": True,
            "query_policy_or_title_validator_change": False,
            "fresh_external_protocol_design": False,
            "fresh_external_activation_or_launch": False,
            "paired_dev64_or_exact220": False,
            "evaluator_access_authorized": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = json.loads(json.dumps(dict(value)))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    engineering = copied.get("engineering_outcome", {})
    funnel = copied.get("acquisition_funnel", {})
    conclusions = copied.get("conclusions", {})
    required = copied.get("required_next_observability", {})
    authorization = copied.get("authorization", {})
    if (
        copied.get("role") != "v24597_v24596_title_transport_diagnosis"
        or copied.get("status")
        != "query_and_candidate_paths_reached_strict_title_surface_still_absent"
        or engineering.get("success_tasks") != 8
        or engineering.get("failure_as_zero_tasks") != 0
        or engineering.get("worker_hard_timeout_tasks") != 0
        or engineering.get("worker_nonzero_tasks") != 0
        or funnel.get("title_query_activity_tasks")
        != funnel.get("target_plan_tasks")
        or funnel.get("query_vector_calls", 0) <= 0
        or funnel.get("logical_query_count") != 2 * funnel.get("query_vector_calls", 0)
        or funnel.get("visible_lead_count", 0) <= 0
        or funnel.get("url_alias_surface_hit_lead_count", 0) <= 0
        or funnel.get("title_alias_surface_hit_lead_count") != 0
        or funnel.get("preserved_candidate_count", 0) <= 0
        or funnel.get("source_representative_replacement_count", 0) <= 0
        or funnel.get("validator_aligned_title_replacement_count") != 0
        or conclusions.get("query_policy_executed") is not True
        or conclusions.get("strict_title_alias_surface_reached") is not False
        or conclusions.get(
            "public_aggregate_distinguishes_empty_absent_late_and_type_incompatible_title_failure"
        )
        is not False
        or conclusions.get("next_successor_must_measure_content_free_title_funnel")
        is not True
        or conclusions.get(
            "next_successor_should_change_query_or_validator_before_title_funnel_measurement"
        )
        is not False
        or any(required.get(name) is not True for name in required if name != "raw_title_query_url_or_page_text_emitted")
        or required.get("raw_title_query_url_or_page_text_emitted") is not False
        or authorization.get("content_free_title_transport_observability_design")
        is not True
        or authorization.get("query_policy_or_title_validator_change") is not False
        or authorization.get("fresh_external_protocol_design") is not False
        or authorization.get("fresh_external_activation_or_launch") is not False
        or authorization.get("paired_dev64_or_exact220") is not False
        or authorization.get("evaluator_access_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.45.97 diagnosis drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    diagnosis = build_diagnosis()
    publish_new(ROOT / OUTPUT, diagnosis)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "status": diagnosis["status"],
                "observability_design_authorized": diagnosis["authorization"][
                    "content_free_title_transport_observability_design"
                ],
            },
            sort_keys=True,
        )
    )
