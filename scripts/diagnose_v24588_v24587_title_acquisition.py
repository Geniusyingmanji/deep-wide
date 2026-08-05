#!/usr/bin/env python3
"""Content-free diagnosis of V2.45.87's title-replacement boundary.

Only the sealed public aggregate, decision, and post-result audit are opened.
No task, query, URL, page, prediction, candidate value, benchmark mapping,
gold data, evaluator output, credential, or private execution directory is
read.  The diagnosis separates the successful collector/pre-dedup repair from
the still-unmet title-validatable acquisition gate.
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
from scripts import v24587_repaired_prededup_preservation_external_gate as run  # noqa: E402


DATE = "20260805"
OUTPUT = Path(f"results/v24588_v24587_title_acquisition_diagnosis_v1_{DATE}.json")


def _read(path: Path) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.45.88 expected public object")
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
        or decision.get("status")
        != "fresh_repaired_prededup_preservation_no_go"
        or decision.get("result_sha256") != sha256(ROOT / run.RESULT)
        or decision.get("diagnostic_route")
        != "validator_aligned_title_replacement_successor"
        or decision.get("authorization", {}).get("fresh_paired_dev64_design")
        is not False
        or decision.get("authorization", {}).get("new_exact220") is not False
        or postaudit.get("result_sha256") != sha256(ROOT / run.RESULT)
        or postaudit.get("decision_sha256") != sha256(ROOT / run.DECISION)
        or postaudit.get("audit_valid") is not True
        or postaudit.get("findings") != []
    ):
        raise RuntimeError("V2.45.88 public chain drifted")
    return result, decision, postaudit


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    result, decision, postaudit = _public_chain()
    mechanism = result["mechanism_aggregate"]
    preservation = mechanism["total_prededup_preservation_count_fields"]
    selection = mechanism["total_validator_aligned_selection_count_fields"]
    alias = mechanism["total_alias_surface_count_fields"]
    supervision = result["supervision_aggregate"]
    observations = result["observation_aggregate"]
    timing = result["stage_timing_aggregate"]
    title_hits = int(alias["title_alias_surface_hit_lead_count"])
    excluded_title_hits = int(
        selection["excluded_title_alias_surface_hit_lead_count"]
    )
    selected_title_hits = int(
        selection["selected_title_alias_surface_hit_lead_count"]
    )
    if not (
        mechanism["success_tasks"] == 8
        and mechanism["failure_as_zero_tasks"] == 0
        and mechanism["prededup_preservation_activity_tasks"] == 8
        and mechanism["prededup_preserved_candidate_tasks"] == 8
        and preservation["preserved_candidate_count"] > 0
        and mechanism["prededup_and_source_replacement_cooccurrence_tasks"] > 0
        and mechanism["prededup_and_title_replacement_cooccurrence_tasks"] == 0
        and selection["source_representative_replacement_count"] > 0
        and selection["validator_aligned_title_replacement_count"] == 0
        and title_hits > 0
        and excluded_title_hits == title_hits
        and selected_title_hits == 0
        and result["reliability_passed"] is True
        and result["parent_validation_passed"] is True
        and result["latency_passed"] is True
        and postaudit["inherited_original_task_projection_rebound"] is False
    ):
        raise RuntimeError("V2.45.88 diagnosis premises drifted")
    value = {
        "artifact_version": 1,
        "role": "v24588_v24587_title_acquisition_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "collector_and_prededup_repaired_title_validatable_acquisition_absent",
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
            "batch_wall_seconds": float(result["batch_wall_seconds"]),
            "worker_success_tasks": int(supervision["worker_success_tasks"]),
            "worker_hard_timeout_tasks": int(
                supervision["worker_hard_timeout_tasks"]
            ),
            "worker_nonzero_tasks": int(supervision["worker_nonzero_tasks"]),
            "provider_deadline_failures_lower_bound": int(
                observations["provider_deadline_failures_lower_bound"]
            ),
            "hosted_search_deadline_failures_lower_bound": int(
                observations["hosted_search_deadline_failures_lower_bound"]
            ),
            "hard_fetch_deadline_failures_lower_bound": int(
                observations["hard_fetch_deadline_failures_lower_bound"]
            ),
            "parent_success_tasks": int(timing["parent_success_tasks"]),
            "inherited_original_task_projection_rebound": False,
            "immutable_collector_repair_observed_successfully": True,
        },
        "mechanism_boundary": {
            "exact_url_distinct_lead_count": int(
                preservation["exact_url_distinct_lead_count"]
            ),
            "registrable_source_count": int(
                preservation["registrable_source_count"]
            ),
            "same_source_additional_candidate_count": int(
                preservation["same_source_additional_candidate_count"]
            ),
            "preserved_candidate_count": int(
                preservation["preserved_candidate_count"]
            ),
            "prededup_preservation_activity_tasks": int(
                mechanism["prededup_preservation_activity_tasks"]
            ),
            "prededup_preserved_candidate_tasks": int(
                mechanism["prededup_preserved_candidate_tasks"]
            ),
            "source_representative_replacement_count": int(
                selection["source_representative_replacement_count"]
            ),
            "source_replacement_cooccurrence_tasks": int(
                mechanism["prededup_and_source_replacement_cooccurrence_tasks"]
            ),
            "visible_lead_count": int(alias["visible_lead_count"]),
            "title_alias_surface_hit_lead_count": title_hits,
            "excluded_title_alias_surface_hit_lead_count": excluded_title_hits,
            "selected_title_alias_surface_hit_lead_count": selected_title_hits,
            "validator_aligned_title_replacement_count": int(
                selection["validator_aligned_title_replacement_count"]
            ),
            "title_replacement_cooccurrence_tasks": int(
                mechanism["prededup_and_title_replacement_cooccurrence_tasks"]
            ),
        },
        "conclusions": {
            "v24585_immutable_collector_failure_mode_repaired": True,
            "pre_dedup_candidate_preservation_is_runtime_reachable": True,
            "same_source_representative_replacement_is_runtime_reachable": True,
            "usable_title_validatable_candidate_was_observed": False,
            "validator_aligned_title_replacement_is_runtime_reachable_on_this_population": False,
            "absence_proves_title_validator_is_too_strict": False,
            "absence_proves_search_provider_cannot_return_title_hits": False,
            "population_specific_surface_mismatch_or_source_exclusion_ruled_out": False,
            "benchmark_quality_or_entropy_credit_improvement_measured": False,
            "next_successor_must_align_query_surfaces_to_unchanged_title_validator": True,
            "next_successor_must_use_new_literal_and_canonical_disjoint_population": True,
            "query_search_fetch_model_page_source_and_evaluator_budget_increase_allowed": False,
            "title_url_alias_hint_may_receive_evidence_entropy_or_decision_credit": False,
        },
        "source_policy": {
            "sealed_public_aggregate_decision_and_postaudit_only": True,
            "task_question_query_url_page_prediction_candidate_value_or_private_directory_opened": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "network_model_search_fetch_process_or_evaluator_called": False,
            "credential_read_hashed_persisted_or_emitted": False,
        },
        "authorization": {
            "validator_aligned_title_query_policy_design": True,
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
    mechanism = copied.get("mechanism_boundary", {})
    conclusions = copied.get("conclusions", {})
    authorization = copied.get("authorization", {})
    if (
        copied.get("role") != "v24588_v24587_title_acquisition_diagnosis"
        or copied.get("status")
        != "collector_and_prededup_repaired_title_validatable_acquisition_absent"
        or engineering.get("success_tasks") != 8
        or engineering.get("failure_as_zero_tasks") != 0
        or engineering.get("immutable_collector_repair_observed_successfully")
        is not True
        or mechanism.get("preserved_candidate_count", 0) <= 0
        or mechanism.get("source_representative_replacement_count", 0) <= 0
        or mechanism.get("title_alias_surface_hit_lead_count")
        != mechanism.get("excluded_title_alias_surface_hit_lead_count")
        or mechanism.get("selected_title_alias_surface_hit_lead_count") != 0
        or mechanism.get("validator_aligned_title_replacement_count") != 0
        or conclusions.get("pre_dedup_candidate_preservation_is_runtime_reachable")
        is not True
        or conclusions.get("usable_title_validatable_candidate_was_observed")
        is not False
        or conclusions.get("absence_proves_title_validator_is_too_strict")
        is not False
        or conclusions.get(
            "next_successor_must_align_query_surfaces_to_unchanged_title_validator"
        )
        is not True
        or conclusions.get(
            "query_search_fetch_model_page_source_and_evaluator_budget_increase_allowed"
        )
        is not False
        or authorization.get("validator_aligned_title_query_policy_design")
        is not True
        or authorization.get("fresh_external_protocol_design") is not False
        or authorization.get("fresh_external_activation_or_launch") is not False
        or authorization.get("paired_dev64_or_exact220") is not False
        or authorization.get("evaluator_access_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.45.88 diagnosis drifted")
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
                "policy_design_authorized": diagnosis["authorization"][
                    "validator_aligned_title_query_policy_design"
                ],
            },
            sort_keys=True,
        )
    )
