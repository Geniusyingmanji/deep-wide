"""Outcome-independent V2.42.16 same-dev64 package gate.

The gate consumes only sealed aggregate results after both label-blind forward
passes and their evaluators are terminal.  It never receives task identities,
questions, benchmark labels, mappings, gold answers, per-task scores, or tool
traces.  A GO authorizes only design/freezing of a later exact-220 run.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

from deepwide_agent.v24200_successor import PACKAGE_GATE_CONTRACT


QUALITY_COMPONENTS = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
METRIC_FIELDS = (
    "runtime_completed",
    "runtime_failed",
    "evaluator_valid",
    "evaluator_invalid_or_not_run",
    "whole_table_successes",
    *QUALITY_COMPONENTS,
    "system_total_tokens",
)
FORBIDDEN_CONTENT_KEYS = frozenset(
    {
        "answer",
        "answer_key",
        "answers",
        "category",
        "gold",
        "ground_truth",
        "instance_id",
        "mapping",
        "opaque_id",
        "prediction",
        "predictions",
        "question",
        "questions",
        "question_type",
        "score",
        "scores",
        "split",
        "task_category",
        "url",
        "urls",
    }
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def reject_task_content(value: object) -> None:
    """Reject task-level or evaluator-only content from aggregate gate inputs."""

    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if normalized in FORBIDDEN_CONTENT_KEYS:
                raise RuntimeError("V2.42.16 task/evaluator content appeared")
            reject_task_content(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            reject_task_content(item)


def _number(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise RuntimeError(f"V2.42.16 invalid numeric metric: {label}")
    return float(value)


def validate_arm_result(value: Mapping[str, Any], *, arm: str) -> dict[str, float]:
    """Validate one exact-64 aggregate without exposing per-task material."""

    if arm not in {"baseline", "candidate"} or not isinstance(value, Mapping):
        raise RuntimeError("V2.42.16 arm result is invalid")
    reject_task_content(value)
    metrics = value.get("metrics")
    provenance = value.get("provenance")
    if (
        value.get("artifact_version") != 1
        or value.get("role") != "v24216_package_gate_dev64_arm_result"
        or value.get("arm") != arm
        or value.get("status") != "exact64_released_not_full220_not_sota"
        or value.get("selected") != 64
        or value.get("conservative_denominator") != 64
        or value.get("exact_terminal_before_mapping") is not True
        or value.get("other_arm_exact_terminal_before_mapping") is not True
        or value.get("failure_as_zero") is not True
        or value.get("resume_or_selective_rerun_used") is not False
        or value.get("full220_launch_allowed") is not False
        or value.get("leaderboard_submission_or_sota_claim") is not False
        or not isinstance(metrics, Mapping)
        or set(metrics) != set(METRIC_FIELDS)
        or not isinstance(provenance, Mapping)
        or not provenance
        or any(
            not isinstance(item, str) or len(item) != 64
            for item in provenance.values()
        )
    ):
        raise RuntimeError("V2.42.16 arm aggregate contract drifted")
    numbers = {name: _number(metrics[name], f"{arm}.{name}") for name in METRIC_FIELDS}
    integer_fields = (
        "runtime_completed",
        "runtime_failed",
        "evaluator_valid",
        "evaluator_invalid_or_not_run",
        "whole_table_successes",
    )
    if any(not numbers[name].is_integer() for name in integer_fields):
        raise RuntimeError("V2.42.16 count metric is not integral")
    if (
        numbers["runtime_completed"] + numbers["runtime_failed"] != 64
        or numbers["evaluator_valid"]
        + numbers["evaluator_invalid_or_not_run"]
        != 64
        or not 0 <= numbers["whole_table_successes"] <= 64
        or any(not 0.0 <= numbers[name] <= 1.0 for name in QUALITY_COMPONENTS)
        or numbers["system_total_tokens"] < 0.0
    ):
        raise RuntimeError("V2.42.16 aggregate denominator drifted")
    numbers["quality_composite"] = sum(numbers[name] for name in QUALITY_COMPONENTS) / len(
        QUALITY_COMPONENTS
    )
    return numbers


def evaluate_package_gate(
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    package_activation: Mapping[str, Any],
    evaluator_identity: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply the frozen gate to two exact same-ID aggregate results."""

    reject_task_content(package_activation)
    reject_task_content(evaluator_identity)
    if (
        package_activation.get("identity_handoff_only") is not False
        or package_activation.get("eligible_component_count", 0) < 1
        or package_activation.get("all_selected_components_covered_exactly_once")
        is not True
        or package_activation.get("single_deepest_cumulative_graph_used") is not True
        or package_activation.get("component_directory_overlay_used") is not False
        or package_activation.get("complete_parent_and_component_regression_rerun")
        is not True
        or package_activation.get("strict_component_activation_validated") is not True
        or package_activation.get("silent_component_drop_or_baseline_fallback_used")
        is not False
    ):
        raise RuntimeError("V2.42.16 strict package activation is absent")
    if (
        evaluator_identity.get("same_opaque_dev64_ids") is not True
        or evaluator_identity.get("same_execution_contract") is not True
        or evaluator_identity.get("same_evaluator_contract") is not True
        or evaluator_identity.get("both_exact_terminal_before_mapping") is not True
        or evaluator_identity.get("mapping_join_after_both_terminal") is not True
        or evaluator_identity.get("outcome_or_score_used_for_execution") is not False
    ):
        raise RuntimeError("V2.42.16 paired evaluator identity drifted")

    base = validate_arm_result(baseline, arm="baseline")
    cand = validate_arm_result(candidate, arm="candidate")
    delta_fields = (
        "runtime_completed",
        "whole_table_successes",
        *QUALITY_COMPONENTS,
        "quality_composite",
    )
    deltas = {name: cand[name] - base[name] for name in delta_fields}
    token_ratio = (
        cand["system_total_tokens"] / base["system_total_tokens"]
        if base["system_total_tokens"] > 0
        else (0.0 if cand["system_total_tokens"] == 0 else math.inf)
    )
    contract = PACKAGE_GATE_CONTRACT
    directional = contract["minimum_material_improvement_any"]
    checks = {
        "completion_non_decrease": deltas["runtime_completed"] >= 0,
        "whole_table_non_decrease": deltas["whole_table_successes"] >= 0,
        "each_quality_component_safety_floor": all(
            deltas[name] >= float(contract["each_quality_component_min_delta"])
            for name in QUALITY_COMPONENTS
        ),
        "candidate_token_ratio": token_ratio
        <= float(contract["candidate_token_ratio_max"]),
        "strict_component_activation": True,
        "material_improvement_any": (
            deltas["runtime_completed"]
            >= int(directional["completion_count_delta"])
            or deltas["whole_table_successes"]
            >= int(directional["whole_table_count_delta"])
            or deltas["quality_composite"]
            >= float(directional["quality_composite_delta"])
        ),
    }
    passed = all(checks.values())
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24216_joint_package_same_dev64_gate_decision",
        "status": "go" if passed else "no_go",
        "gate_id": contract["gate_id"],
        "denominator": 64,
        "failure_as_zero": True,
        "baseline": base,
        "candidate": cand,
        "candidate_minus_baseline": deltas,
        "candidate_token_ratio": token_ratio,
        "package_activation": dict(package_activation),
        "evaluator_identity": dict(evaluator_identity),
        "checks": checks,
        "passed": passed,
        "all220_freeze_design_allowed": passed,
        "capacity_measurement_allowed": passed,
        "full220_launch_allowed": False,
        "resume_or_selective_rerun_allowed": False,
        "threshold_code_prompt_model_search_or_budget_change_allowed": False,
        "mapping_gold_category_question_type_or_per_task_score_emitted": False,
        "claims": {
            "development_resource_gate_only": True,
            "full220_result": False,
            "avg_at_4": False,
            "leaderboard_submission_or_sota": False,
            "entropy_or_credit_causal_effect": False,
        },
    }
    value["decision_payload_sha256"] = payload_sha256(value)
    return value


__all__ = [
    "FORBIDDEN_CONTENT_KEYS",
    "METRIC_FIELDS",
    "QUALITY_COMPONENTS",
    "evaluate_package_gate",
    "payload_sha256",
    "reject_task_content",
    "validate_arm_result",
]
