"""Common-recovery 6+4 versus 6+2+2 runtime for the next paired gate.

Both arms reuse the audited V2.42.99 bounded synthesis recovery.  The only
intended arm difference remains the retrieval allocation already encoded by
V2.42.99: baseline uses V2.42.86 ``6+4`` while candidate uses V2.42.96
``6+2+2``.  This adapter adds one uniform experiment receipt and a total
fallback boundary without changing the three-model-call envelope.
"""

from __future__ import annotations

import copy
import time
from collections.abc import Callable, Mapping
from typing import Any

from .v24257_score_first_runtime import (
    ScoreFirstLimits,
    _counter_delta,
    _counter_snapshot,
    validate_visible_task,
)
from .v24259_deterministic_table_normalizer import validate_v24259_result
from .v24267_total_fallback import build_total_fallback_result
from .v24272_two_wave_entropy_voc import TwoWavePolicy
from .v24294_staged_reserve import StagedReservePolicy
from .v24299_synthesis_recovery import (
    BoundedSynthesisRecoveryModel,
    _reconcile_accounting,
    validate_recovery_receipt,
)
from .v24286_visible_schema_runtime import run_v24286_task, validate_v24286_result
from .v24296_staged_reserve_task_runtime import (
    run_v24296_task,
    validate_v24296_result,
)
from .v24308_child_exit_observability import coarse_exception_type


POLICY_ID = "v24310_common_recovery_retrieval_allocation_ablation_v1"
RECEIPT_ROLE = "v24310_common_synthesis_recovery_receipt"
RECEIPT_FIELD = "v24310_common_synthesis_recovery"
ARMS = ("baseline", "candidate")
MODEL_COUNTERS = ("requests", "attempts", "input_tokens", "output_tokens", "total_tokens")
SEARCH_COUNTERS = (
    "calls",
    "failures",
    "tool_calls",
    "fetch_calls",
    "fetch_failures",
    "input_tokens",
    "output_tokens",
    "total_tokens",
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "arm",
        "recovery_enabled",
        "model_call_cap",
        "effect_attribution_complete",
        "unattributed_model_effects",
        "effects_by_stage",
        "total_effects_admitted",
        "synthesis_initial_model_request_error",
        "synthesis_recovery_attempted",
        "synthesis_recovery_succeeded",
        "synthesis_recovery_model_request_error",
        "repair_blocked_after_recovery",
        "provider_requests_delta",
        "provider_attempts_delta",
        "fourth_model_effect",
        "question_prompt_response_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    }
)


def _snapshot(client: Any, names: tuple[str, ...]) -> dict[str, int]:
    try:
        return _counter_snapshot(client, names)
    except BaseException:
        return {name: 0 for name in names}


def _project(arm: str, parent: Mapping[str, Any]) -> dict[str, Any]:
    validate_recovery_receipt(parent)
    if parent.get("arm") != arm:
        raise ValueError("V2.43.10 parent recovery arm drifted")
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "arm": arm,
        "recovery_enabled": True,
        "model_call_cap": 3,
        "effect_attribution_complete": True,
        "unattributed_model_effects": 0,
        "effects_by_stage": dict(parent["effects_by_stage"]),
        "total_effects_admitted": int(parent["total_effects_admitted"]),
        "synthesis_initial_model_request_error": bool(
            parent["synthesis_initial_model_request_error"]
        ),
        "synthesis_recovery_attempted": bool(
            parent["synthesis_recovery_attempted"]
        ),
        "synthesis_recovery_succeeded": bool(
            parent["synthesis_recovery_succeeded"]
        ),
        "synthesis_recovery_model_request_error": bool(
            parent["synthesis_recovery_model_request_error"]
        ),
        "repair_blocked_after_recovery": bool(
            parent["repair_blocked_after_recovery"]
        ),
        "provider_requests_delta": int(parent["provider_requests_delta"]),
        "provider_attempts_delta": int(parent["provider_attempts_delta"]),
        "fourth_model_effect": int(parent["total_effects_admitted"]) > 3,
        "question_prompt_response_prediction_answer_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    validate_receipt(value)
    return value


def zero_effect_receipt(arm: str) -> dict[str, Any]:
    if arm not in ARMS:
        raise ValueError("V2.43.10 zero-effect arm is invalid")
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "arm": arm,
        "recovery_enabled": True,
        "model_call_cap": 3,
        "effect_attribution_complete": True,
        "unattributed_model_effects": 0,
        "effects_by_stage": {
            "plan": 0,
            "synthesis_initial": 0,
            "synthesis_recovery": 0,
            "repair": 0,
        },
        "total_effects_admitted": 0,
        "synthesis_initial_model_request_error": False,
        "synthesis_recovery_attempted": False,
        "synthesis_recovery_succeeded": False,
        "synthesis_recovery_model_request_error": False,
        "repair_blocked_after_recovery": False,
        "provider_requests_delta": 0,
        "provider_attempts_delta": 0,
        "fourth_model_effect": False,
        "question_prompt_response_prediction_answer_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    validate_receipt(value)
    return value


def parent_exit_receipt(
    arm: str, *, provider_requests: int, provider_attempts: int
) -> dict[str, Any]:
    if (
        arm not in ARMS
        or isinstance(provider_requests, bool)
        or not isinstance(provider_requests, int)
        or not 0 <= provider_requests <= 3
        or isinstance(provider_attempts, bool)
        or not isinstance(provider_attempts, int)
        or provider_attempts < provider_requests
    ):
        raise ValueError("V2.43.10 parent-exit accounting is invalid")
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "arm": arm,
        "recovery_enabled": True,
        "model_call_cap": 3,
        "effect_attribution_complete": False,
        "unattributed_model_effects": provider_requests,
        "effects_by_stage": {
            "plan": 0,
            "synthesis_initial": 0,
            "synthesis_recovery": 0,
            "repair": 0,
        },
        "total_effects_admitted": provider_requests,
        "synthesis_initial_model_request_error": False,
        "synthesis_recovery_attempted": False,
        "synthesis_recovery_succeeded": False,
        "synthesis_recovery_model_request_error": False,
        "repair_blocked_after_recovery": False,
        "provider_requests_delta": provider_requests,
        "provider_attempts_delta": provider_attempts,
        "fourth_model_effect": False,
        "question_prompt_response_prediction_answer_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    validate_receipt(value)
    return value


def validate_receipt(value: Mapping[str, Any]) -> None:
    effects = value.get("effects_by_stage")
    flags = (
        "synthesis_initial_model_request_error",
        "synthesis_recovery_attempted",
        "synthesis_recovery_succeeded",
        "synthesis_recovery_model_request_error",
        "repair_blocked_after_recovery",
    )
    total = value.get("total_effects_admitted")
    requests = value.get("provider_requests_delta")
    attempts = value.get("provider_attempts_delta")
    unattributed = value.get("unattributed_model_effects")
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != RECEIPT_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("arm") not in ARMS
        or value.get("recovery_enabled") is not True
        or value.get("model_call_cap") != 3
        or not isinstance(value.get("effect_attribution_complete"), bool)
        or value.get("fourth_model_effect") is not False
        or value.get(
            "question_prompt_response_prediction_answer_opaque_id_or_credential_emitted"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or not isinstance(effects, Mapping)
        or set(effects) != {"plan", "synthesis_initial", "synthesis_recovery", "repair"}
        or any(
            isinstance(number, bool)
            or not isinstance(number, int)
            or number not in {0, 1}
            for number in effects.values()
        )
        or any(not isinstance(value.get(name), bool) for name in flags)
        or isinstance(total, bool)
        or not isinstance(total, int)
        or isinstance(unattributed, bool)
        or not isinstance(unattributed, int)
        or unattributed < 0
        or total != sum(effects.values()) + unattributed
        or not 0 <= total <= 3
        or value["effect_attribution_complete"]
        and unattributed != 0
        or not value["effect_attribution_complete"]
        and (
            unattributed != total
            or any(effects.values())
            or any(value.get(name) for name in flags)
        )
        or isinstance(requests, bool)
        or not isinstance(requests, int)
        or requests != total
        or isinstance(attempts, bool)
        or not isinstance(attempts, int)
        or attempts < requests
        or effects["synthesis_recovery"]
        != int(value["synthesis_recovery_attempted"])
        or value["synthesis_recovery_succeeded"]
        and value["synthesis_recovery_model_request_error"]
        or value["synthesis_recovery_succeeded"]
        and not value["synthesis_recovery_attempted"]
        or value["synthesis_recovery_model_request_error"]
        and not value["synthesis_recovery_attempted"]
        or value["repair_blocked_after_recovery"]
        and not value["synthesis_recovery_attempted"]
    ):
        raise ValueError("V2.43.10 common recovery receipt drifted")


def validate_v24310_result(value: Mapping[str, Any], arm: str) -> str:
    if arm not in ARMS:
        raise ValueError("V2.43.10 arm is invalid")
    receipt = value.get(RECEIPT_FIELD)
    if not isinstance(receipt, Mapping) or receipt.get("arm") != arm:
        raise ValueError("V2.43.10 experiment receipt is absent")
    validate_receipt(receipt)
    parent = copy.deepcopy(dict(value))
    parent.pop(RECEIPT_FIELD, None)
    kind = "candidate"
    try:
        if arm == "baseline":
            validate_v24286_result(parent)
        else:
            validate_v24296_result(parent)
    except (KeyError, TypeError, ValueError):
        kind = "fallback"
        try:
            validate_v24259_result(parent)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("V2.43.10 result is neither parent nor fallback") from exc
        if parent.get("completion_kind") not in {
            "worker_failure_fallback",
            "hard_deadline_fallback",
        }:
            raise ValueError("V2.43.10 fallback boundary drifted")
    budget = value["budget"]
    admitted = [
        event
        for event in budget["events"]
        if event.get("effect") == "model" and event.get("admitted") is True
    ]
    if (
        budget["limits"]["model_calls"] != 3
        or budget["admitted_model_calls"] != receipt["total_effects_admitted"]
        or len(admitted) != receipt["total_effects_admitted"]
        or value["cost"]["model"]["requests"]
        != receipt["provider_requests_delta"]
        or value["cost"]["model"]["attempts"]
        != receipt["provider_attempts_delta"]
    ):
        raise ValueError("V2.43.10 admission/provider accounting drifted")
    recovery_events = [
        event
        for event in budget["events"]
        if event.get("stage") == "synthesis_provider_recovery"
        and event.get("admitted") is True
    ]
    if len(recovery_events) != receipt["effects_by_stage"]["synthesis_recovery"]:
        raise ValueError("V2.43.10 recovery event accounting drifted")
    if kind == "candidate":
        telemetry = value.get("telemetry", {}).get("model_events", [])
        if (
            not isinstance(telemetry, list)
            or sum(int(event["requests_delta"]) for event in telemetry)
            != receipt["provider_requests_delta"]
            or sum(int(event["attempts_delta"]) for event in telemetry)
            != receipt["provider_attempts_delta"]
        ):
            raise ValueError("V2.43.10 provider telemetry accounting drifted")
        if receipt["synthesis_recovery_attempted"]:
            synthesis = [
                event for event in telemetry if event.get("stage") == "synthesis"
            ]
            if len(synthesis) != 1 or synthesis[0]["requests_delta"] != 2:
                raise ValueError("V2.43.10 recovery telemetry drifted")
    return kind


def run_v24310_task(
    task: Mapping[str, Any],
    *,
    arm: str,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits,
    two_wave_policy: TwoWavePolicy,
    reserve_policy: StagedReservePolicy | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    progress: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    if arm not in ARMS or limits.model_calls != 3:
        raise ValueError("V2.43.10 arm or model-call cap drifted")
    if arm == "baseline" and reserve_policy is not None:
        raise ValueError("V2.43.10 baseline must not receive reserve policy")
    if arm == "candidate" and reserve_policy is None:
        raise ValueError("V2.43.10 candidate reserve policy is absent")
    limits.validate()
    two_wave_policy.validate()
    if reserve_policy is not None:
        reserve_policy.validate()
    try:
        started = float(monotonic())
    except BaseException:
        started = 0.0
    model_start = _snapshot(model, MODEL_COUNTERS)
    search_start = _snapshot(search, SEARCH_COUNTERS)
    last_progress: dict[str, Any] = {}
    wrapper = BoundedSynthesisRecoveryModel(
        model, arm=arm, model_call_cap=limits.model_calls
    )

    def capture(value: Mapping[str, Any]) -> None:
        nonlocal last_progress
        last_progress = _reconcile_accounting(value, wrapper.receipt())
        if progress is not None:
            progress(last_progress)

    try:
        if arm == "baseline":
            parent = run_v24286_task(
                visible,
                model=wrapper,
                search=search,
                limits=limits,
                policy=two_wave_policy,
                monotonic=monotonic,
                progress=capture,
            )
        else:
            parent = run_v24296_task(
                visible,
                model=wrapper,
                search=search,
                limits=limits,
                two_wave_policy=two_wave_policy,
                reserve_policy=reserve_policy,
                monotonic=monotonic,
                progress=capture,
            )
    except BaseException as error:
        current = dict(last_progress)
        current["model_cost"] = _counter_delta(
            _snapshot(model, MODEL_COUNTERS), model_start
        )
        current["search_cost"] = _counter_delta(
            _snapshot(search, SEARCH_COUNTERS), search_start
        )
        try:
            elapsed = max(0.0, float(monotonic()) - started)
        except BaseException:
            elapsed = 0.0
        parent = build_total_fallback_result(
            visible,
            limits=limits,
            completion_kind="worker_failure_fallback",
            failure_stage=f"v24310_{arm}_runtime_totality",
            failure_type=coarse_exception_type(error),
            elapsed_seconds=elapsed,
            last_progress=current,
        )
    raw = wrapper.receipt()
    parent = _reconcile_accounting(parent, raw)
    result = copy.deepcopy(dict(parent))
    result[RECEIPT_FIELD] = _project(arm, raw)
    validate_v24310_result(result, arm)
    return result


__all__ = [
    "ARMS",
    "POLICY_ID",
    "RECEIPT_FIELD",
    "RECEIPT_ROLE",
    "parent_exit_receipt",
    "run_v24310_task",
    "validate_receipt",
    "validate_v24310_result",
    "zero_effect_receipt",
]
