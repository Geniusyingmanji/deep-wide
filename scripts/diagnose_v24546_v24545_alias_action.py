#!/usr/bin/env python3
"""Content-free diagnosis of the V2.45.45 alias-action NO-GO.

Only the frozen public result, decision, and post-result audit are read.  The
public aggregate proves that one task added an observation and that the batch
gained information, but it does not retain the task-level joint distribution.
Consequently those two facts cannot be attributed to the same acquisition
action after the opaque capabilities have been destroyed.

No task, question, identifier, query, URL, page, source, value, prediction,
temporary execution directory, benchmark metadata, evaluator output, or
credential is opened.
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

DATE = "20260805"
RESULT = Path(f"results/v24545_alias_action_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24545_alias_action_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v24545_alias_action_external_postresult_audit_v1_{DATE}.json"
)
OUTPUT = Path(
    f"results/v24546_v24545_alias_action_correlation_diagnosis_v1_{DATE}.json"
)


def _read(path: Path) -> dict[str, Any]:
    full = ROOT / path
    if full.is_symlink() or not full.is_file():
        raise RuntimeError(f"V2.45.46 nonordinary input: {path}")
    value = json.loads(full.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.45.46 expected object")
    return value


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    from deepwide_agent.v24320_forward_contract import payload_sha256, sha256
    from scripts import v24545_alias_action_credit_external_gate as gate

    result = gate.validate_public_result(_read(RESULT))
    decision = gate.validate_decision(value=_read(DECISION))
    audit = gate.validate_postaudit(value=_read(POSTAUDIT))
    mechanism = result["mechanism_aggregate"]
    counts = mechanism["total_acquisition_action_count_fields"]
    numbers = mechanism["total_acquisition_action_number_fields"]
    reliable = (
        result["reliability_passed"] is True
        and result["parent_validation_passed"] is True
        and result["latency_passed"] is True
        and mechanism["success_tasks"] == 8
        and mechanism["failure_as_zero_tasks"] == 0
    )
    if (
        decision.get("status")
        != "fresh_post_capability_quarantine_alias_action_credit_no_go"
        or decision.get("passed") is not False
        or decision.get("diagnostic_route") != "alias_title_selection_successor"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("shared_api_lease_active") is not False
        or not reliable
    ):
        raise RuntimeError("V2.45.46 parent closure drifted")

    value = {
        "artifact_version": 1,
        "role": "v24546_v24545_alias_action_correlation_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "result": {"path": str(RESULT), "sha256": sha256(ROOT / RESULT)},
            "decision": {
                "path": str(DECISION),
                "sha256": sha256(ROOT / DECISION),
            },
            "postaudit": {
                "path": str(POSTAUDIT),
                "sha256": sha256(ROOT / POSTAUDIT),
            },
        },
        "observed": {
            "selected": int(result["selected"]),
            "reliability_parent_validation_and_latency_passed": reliable,
            "target_plan_tasks": int(mechanism["acquisition_plan_tasks"]),
            "acquisition_activity_tasks": int(
                mechanism["acquisition_activity_tasks"]
            ),
            "targeted_usable_page_count": int(
                counts["targeted_usable_page_count"]
            ),
            "targeted_new_observation_count": int(
                counts["targeted_new_observation_count"]
            ),
            "acquisition_new_observation_tasks": int(
                mechanism["acquisition_new_observation_tasks"]
            ),
            "visible_lead_count": int(counts["visible_lead_count"]),
            "selected_lead_count": int(counts["selected_lead_count"]),
            "alias_title_hit_lead_count": int(
                counts["alias_title_hit_lead_count"]
            ),
            "selected_alias_title_hit_lead_count": int(
                counts["selected_alias_title_hit_lead_count"]
            ),
            "raw_information_gain_nats": float(
                numbers["information_gain_gain_nats"]
            ),
            "raw_epistemic_gain_nats": float(
                numbers["epistemic_credit_gain_nats"]
            ),
            "action_information_credit_nats": float(
                numbers["action_information_credit_nats"]
            ),
            "action_epistemic_credit_nats": float(
                numbers["action_epistemic_credit_nats"]
            ),
            "action_decision_credit_nats": float(
                numbers["action_decision_credit_nats"]
            ),
            "safe_change_improvement_tasks": int(
                mechanism["acquisition_safe_change_improvement_tasks"]
            ),
        },
        "proved_inferences": {
            "at_least_one_task_added_a_targeted_observation": (
                mechanism["acquisition_new_observation_tasks"] > 0
            ),
            "at_least_one_task_had_positive_raw_information_gain": (
                numbers["information_gain_gain_nats"] > 0
            ),
            "legacy_title_alias_matcher_observed_no_hit": (
                counts["alias_title_hit_lead_count"] == 0
                and counts["selected_alias_title_hit_lead_count"] == 0
            ),
            "no_action_credit_or_safe_output_improvement": (
                numbers["action_information_credit_nats"] == 0
                and numbers["action_epistemic_credit_nats"] == 0
                and numbers["action_decision_credit_nats"] == 0
                and mechanism["acquisition_safe_change_improvement_tasks"] == 0
            ),
        },
        "unrecoverable_from_frozen_public_aggregate": {
            "new_observation_and_positive_raw_gain_occurred_on_same_task": False,
            "new_observation_and_alias_surface_hit_occurred_on_same_task": False,
            "selected_alias_surface_hit_and_positive_raw_gain_occurred_on_same_task": False,
            "positive_raw_gain_came_from_alias_seeded_acquisition": False,
            "which_title_alias_mode_was_present": False,
            "whether_normalized_url_contained_a_visible_row_alias": False,
        },
        "missing_future_content_free_fields": [
            "title_full_surface_hit_lead_count",
            "title_core_surface_hit_lead_count",
            "title_initialism_hit_lead_count",
            "url_full_surface_hit_lead_count",
            "url_core_surface_hit_lead_count",
            "url_initialism_hit_lead_count",
            "selected_alias_surface_hit_lead_count",
            "acquisition_active_and_positive_information_gain_count",
            "new_observation_and_alias_surface_hit_count",
            "new_observation_and_selected_alias_surface_hit_count",
            "selected_alias_surface_hit_and_positive_information_gain_count",
        ],
        "successor_contract": {
            "append_only_new_version": True,
            "preserve_runtime_boundary_exactly_opaque_id_and_question": True,
            "match_only_visible_title_and_normalized_url": True,
            "query_text_must_not_establish_alias_hit": True,
            "alias_hint_itself_receives_vote_source_entropy_or_decision_credit": False,
            "preserve_source_posterior_margin_leave_one_out_safe_change_and_decision_credit_thresholds": True,
            "publish_mode_counts_and_task_level_joint_counts_only": True,
            "same_population_recovery_or_rerun": False,
            "next_population_prior_question_count": 428,
            "next_population_prior_entity_count": 3424,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "task_question_identifier_query_url_page_source_value_prediction_private_result_opened": False,
            "benchmark_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "temporary_execution_directory_opened": False,
            "network_model_search_fetch_process_or_evaluator_called": False,
        },
        "claims": {
            "task_level_correlation_recovered": False,
            "alias_action_caused_information_gain": False,
            "benchmark_quality_measured": False,
            "sota": False,
        },
        "authorization": {
            "append_only_alias_observability_successor_design": True,
            "same_population_rerun_retry_resume_or_revaluation": False,
            "fresh_external_probe_launch": False,
            "paired_dev64_or_exact220": False,
            "evaluator_leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    from deepwide_agent.v24320_forward_contract import payload_sha256

    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    observed = copied.get("observed")
    proved = copied.get("proved_inferences")
    unavailable = copied.get("unrecoverable_from_frozen_public_aggregate")
    successor = copied.get("successor_contract")
    source = copied.get("source_policy")
    claims = copied.get("claims")
    authorization = copied.get("authorization")
    if (
        copied.get("role")
        != "v24546_v24545_alias_action_correlation_diagnosis"
        or not isinstance(observed, Mapping)
        or observed.get("selected") != 8
        or observed.get(
            "reliability_parent_validation_and_latency_passed"
        )
        is not True
        or observed.get("target_plan_tasks") != 7
        or observed.get("acquisition_activity_tasks") != 6
        or observed.get("targeted_usable_page_count") != 17
        or observed.get("targeted_new_observation_count") != 1
        or observed.get("acquisition_new_observation_tasks") != 1
        or observed.get("visible_lead_count") != 423
        or observed.get("selected_lead_count") != 63
        or observed.get("alias_title_hit_lead_count") != 0
        or observed.get("selected_alias_title_hit_lead_count") != 0
        or abs(float(observed.get("raw_information_gain_nats", -1)) - 0.209371236041)
        > 1e-12
        or observed.get("action_information_credit_nats") != 0
        or observed.get("action_epistemic_credit_nats") != 0
        or observed.get("action_decision_credit_nats") != 0
        or observed.get("safe_change_improvement_tasks") != 0
        or not isinstance(proved, Mapping)
        or any(item is not True for item in proved.values())
        or not isinstance(unavailable, Mapping)
        or any(item is not False for item in unavailable.values())
        or not isinstance(successor, Mapping)
        or successor.get("append_only_new_version") is not True
        or successor.get(
            "preserve_runtime_boundary_exactly_opaque_id_and_question"
        )
        is not True
        or successor.get("match_only_visible_title_and_normalized_url") is not True
        or successor.get("query_text_must_not_establish_alias_hit") is not True
        or successor.get(
            "alias_hint_itself_receives_vote_source_entropy_or_decision_credit"
        )
        is not False
        or successor.get(
            "preserve_source_posterior_margin_leave_one_out_safe_change_and_decision_credit_thresholds"
        )
        is not True
        or successor.get("same_population_recovery_or_rerun") is not False
        or successor.get("next_population_prior_question_count") != 428
        or successor.get("next_population_prior_entity_count") != 3424
        or not isinstance(source, Mapping)
        or source.get("runtime_boundary") != ["opaque_id", "question"]
        or any(
            source.get(name) is not False
            for name in source
            if name != "runtime_boundary"
        )
        or not isinstance(claims, Mapping)
        or any(item is not False for item in claims.values())
        or not isinstance(authorization, Mapping)
        or authorization.get("append_only_alias_observability_successor_design")
        is not True
        or any(
            authorization.get(name) is not False
            for name in authorization
            if name != "append_only_alias_observability_successor_design"
        )
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.45.46 diagnosis drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    diagnosis = build_diagnosis()
    publish_new(ROOT / OUTPUT, diagnosis)
    print(json.dumps({"path": str(OUTPUT), "valid": True}))
