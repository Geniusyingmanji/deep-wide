"""Content-free post-terminal diagnosis of V2.44.93 targeted conversion.

Only frozen public aggregates and protocol/result/decision/audit identities are
read.  No task, question, identifier, query, URL, page, prediction, candidate,
private result, benchmark metadata, evaluator output, credential, or temporary
execution directory is opened.
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
RESULT = Path("results/v24493_total_targeted_external_result_v1_20260804.json")
DECISION = Path("results/v24493_total_targeted_external_decision_v1_20260804.json")
POSTAUDIT = Path("results/v24493_total_targeted_external_postresult_audit_v1_20260804.json")
OUTPUT = Path("results/v24494_v24493_targeted_conversion_diagnosis_v1_20260804.json")


def _read(path: Path) -> dict[str, Any]:
    full = ROOT / path
    if full.is_symlink() or not full.is_file():
        raise RuntimeError(f"V2.44.94 nonordinary input: {path}")
    value = json.loads(full.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.44.94 expected object")
    return value


def build_report(*, now: int | None = None) -> dict[str, Any]:
    from deepwide_agent.v24320_forward_contract import payload_sha256, sha256
    from scripts import v24493_total_targeted_external_gate as gate

    result = gate.validate_public_result(_read(RESULT))
    decision = _read(DECISION)
    audit = _read(POSTAUDIT)
    mechanism = result["mechanism_aggregate"]
    observation = result["observation_aggregate"]
    timing = result["stage_timing_aggregate"]
    supervision = result["supervision_aggregate"]
    if (
        decision.get("status") != "fresh_targeted_external_no_go"
        or decision.get("passed") is not False
        or decision.get("authorization", {}).get("fresh_paired_dev64_design")
        is not False
        or audit.get("findings") != []
        or audit.get("audit_valid") is not True
        or audit.get("shared_api_lease_active") is not False
    ):
        raise RuntimeError("V2.44.94 parent closure drifted")

    reliable = (
        mechanism["success_tasks"] == 8
        and observation["success_tasks"] == 8
        and timing["parent_success_tasks"] == 8
        and supervision["worker_success_tasks"] == 8
        and observation["slot_timeouts_lower_bound"] == 0
        and observation["provider_deadline_failures_lower_bound"] == 0
        and observation["hosted_search_deadline_failures_lower_bound"] == 0
        and observation["hard_fetch_deadline_failures_lower_bound"] == 0
        and observation["fetch_helper_failures_lower_bound"] == 0
    )
    targeted_effect_observed = (
        mechanism["target_plan_tasks"] == 1
        and mechanism["total_additional_fetch_effects_success_rows"] == 2
        and mechanism["total_additional_model_acquisitions_success_rows"] == 0
    )
    conversion_failed = (
        mechanism["safe_change_improvement_tasks"] == 0
        and mechanism["positive_decision_credit_tasks"] == 0
        and mechanism["total_decision_credit_nats"] == 0
    )
    missing = [
        "targeted_discovered_source_count",
        "targeted_selected_source_count",
        "targeted_usable_page_count",
        "targeted_new_observation_count",
        "support_deficit_before_targeted_search",
        "threshold_failure_partition_after_targeted_search",
        "positive_information_gain_total_nats_after_targeted_search",
        "epistemic_credit_total_nats_after_targeted_search",
    ]
    value = {
        "artifact_version": 1,
        "role": "v24494_v24493_targeted_conversion_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "result": {"path": str(RESULT), "sha256": sha256(ROOT / RESULT)},
            "decision": {"path": str(DECISION), "sha256": sha256(ROOT / DECISION)},
            "postaudit": {"path": str(POSTAUDIT), "sha256": sha256(ROOT / POSTAUDIT)},
        },
        "observed": {
            "selected": 8,
            "reliability_transport_validation_all_passed": reliable,
            "target_plan_tasks": mechanism["target_plan_tasks"],
            "additional_fetch_effects_success_rows": mechanism[
                "total_additional_fetch_effects_success_rows"
            ],
            "additional_model_acquisitions_success_rows": mechanism[
                "total_additional_model_acquisitions_success_rows"
            ],
            "safe_change_improvement_tasks": mechanism[
                "safe_change_improvement_tasks"
            ],
            "positive_decision_credit_tasks": mechanism[
                "positive_decision_credit_tasks"
            ],
            "total_decision_credit_nats": mechanism[
                "total_decision_credit_nats"
            ],
            "parent_certificate_validation_p95_seconds": timing[
                "parent_certificate_validation_wall_p95_seconds"
            ],
            "batch_wall_seconds": result["batch_wall_seconds"],
        },
        "inferences": {
            "targeted_stage_activated": targeted_effect_observed,
            "targeted_effect_failed_to_convert_to_safe_change_or_decision_credit": conversion_failed,
            "failure_is_not_explained_by_observed_transport_provider_or_validation_failure": reliable,
            "positive_information_gain_after_targeted_search_is_proven": False,
            "targeted_sources_produced_new_usable_observations_is_proven": False,
            "specific_threshold_failure_cause_is_proven": False,
        },
        "missing_content_free_fields": missing,
        "candidate_root_causes_not_distinguishable_from_frozen_public_surface": [
            "selected_sources_yielded_no_usable_page",
            "usable_pages_yielded_no_target_bound_observation",
            "observations_supported_conflicting_or_nonleading_values",
            "support_count_remained_below_required_threshold",
            "posterior_remained_below_0_8",
            "support_margin_remained_below_1",
        ],
        "diagnosis": "targeted_conversion_failed_but_specific_semantic_bottleneck_is_unidentifiable_from_current_content_free_projection",
        "source_policy": {
            "task_question_identifier_query_url_page_prediction_candidate_private_result_opened": False,
            "benchmark_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "network_model_search_fetch_process_or_evaluator_called": False,
            "temporary_execution_directory_opened": False,
        },
        "authorization": {
            "append_only_content_free_conversion_projection_design": True,
            "same_population_rerun_or_revaluation": False,
            "query_or_threshold_change_from_v24493_feedback": False,
            "new_external_probe_launch": False,
            "paired_dev64_or_exact220": False,
            "evaluator_leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return validate_report(value)


def validate_report(value: Mapping[str, Any]) -> dict[str, Any]:
    from deepwide_agent.v24320_forward_contract import payload_sha256

    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    observed = copied.get("observed")
    inferences = copied.get("inferences")
    source = copied.get("source_policy")
    authorization = copied.get("authorization")
    if (
        copied.get("role") != "v24494_v24493_targeted_conversion_diagnosis"
        or not isinstance(observed, Mapping)
        or observed.get("selected") != 8
        or observed.get("reliability_transport_validation_all_passed") is not True
        or observed.get("target_plan_tasks") != 1
        or observed.get("additional_fetch_effects_success_rows") != 2
        or observed.get("additional_model_acquisitions_success_rows") != 0
        or observed.get("safe_change_improvement_tasks") != 0
        or observed.get("positive_decision_credit_tasks") != 0
        or observed.get("total_decision_credit_nats") != 0
        or not isinstance(inferences, Mapping)
        or inferences.get("targeted_stage_activated") is not True
        or inferences.get(
            "targeted_effect_failed_to_convert_to_safe_change_or_decision_credit"
        )
        is not True
        or inferences.get(
            "failure_is_not_explained_by_observed_transport_provider_or_validation_failure"
        )
        is not True
        or any(
            inferences.get(name) is not False
            for name in (
                "positive_information_gain_after_targeted_search_is_proven",
                "targeted_sources_produced_new_usable_observations_is_proven",
                "specific_threshold_failure_cause_is_proven",
            )
        )
        or copied.get("diagnosis")
        != "targeted_conversion_failed_but_specific_semantic_bottleneck_is_unidentifiable_from_current_content_free_projection"
        or not isinstance(source, Mapping)
        or any(source.get(name) is not False for name in source)
        or not isinstance(authorization, Mapping)
        or authorization.get(
            "append_only_content_free_conversion_projection_design"
        )
        is not True
        or any(
            authorization.get(name) is not False
            for name in (
                "same_population_rerun_or_revaluation",
                "query_or_threshold_change_from_v24493_feedback",
                "new_external_probe_launch",
                "paired_dev64_or_exact220",
                "evaluator_leaderboard_or_sota",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.44.94 diagnosis drifted")
    return copied


if __name__ == "__main__":
    value = build_report()
    path = ROOT / OUTPUT
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
    print(json.dumps({"path": str(OUTPUT), "diagnosis": value["diagnosis"]}))
