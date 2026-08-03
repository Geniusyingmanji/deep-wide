"""Single-treatment staged-reserve paired runtime for V2.43.03.

Both arms execute the same V2.42.96 visible-schema ``6+2+2`` staged-reserve
runtime under the same three-model-call task budget.  The baseline observes a
synthesis provider failure and propagates it unchanged.  The candidate alone
may spend the already-unused third call on V2.42.99 bounded full-synthesis
recovery.  No fourth call is possible.
"""

from __future__ import annotations

import copy
import time
from collections.abc import Callable, Mapping
from typing import Any

from .clients import ModelRequestError
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
from .v24296_staged_reserve_task_runtime import (
    run_v24296_task,
    validate_v24296_result,
)
from .v24299_synthesis_recovery import (
    BoundedSynthesisRecoveryModel,
    _reconcile_accounting,
    validate_recovery_receipt,
)


POLICY_ID = "v24303_staged_reserve_synthesis_recovery_ablation_v1"
RECEIPT_ROLE = "v24303_synthesis_recovery_ablation_receipt"
RECEIPT_FIELD = "v24303_synthesis_recovery"
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


class SynthesisRecoveryControlModel:
    """Observe the same stages while propagating synthesis failure unchanged."""

    def __init__(self, inner: Any, *, model_call_cap: int) -> None:
        if model_call_cap != 3:
            raise ValueError("V2.43.03 control requires the exact three-call cap")
        self.inner = inner
        self.model_call_cap = model_call_cap
        self._start = _snapshot(inner, MODEL_COUNTERS)
        self._plan_seen = False
        self._synthesis_seen = False
        self.effects_by_stage = {
            "plan": 0,
            "synthesis_initial": 0,
            "synthesis_recovery": 0,
            "repair": 0,
        }
        self.synthesis_initial_model_request_error = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    @property
    def total_effects_admitted(self) -> int:
        return sum(self.effects_by_stage.values())

    def _stage(self, json_mode: bool) -> str:
        if json_mode and not self._plan_seen:
            self._plan_seen = True
            return "plan"
        if not self._synthesis_seen:
            self._synthesis_seen = True
            return "synthesis_initial"
        return "repair"

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        stage = self._stage(json_mode)
        if self.total_effects_admitted >= self.model_call_cap:
            raise RuntimeError("V2.43.03 baseline model-call cap exhausted")
        self.effects_by_stage[stage] += 1
        try:
            return self.inner.complete(
                system,
                user,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )
        except ModelRequestError:
            if stage == "synthesis_initial":
                self.synthesis_initial_model_request_error = True
            raise

    def raw_receipt(self) -> dict[str, Any]:
        delta = _counter_delta(_snapshot(self.inner, MODEL_COUNTERS), self._start)
        return {
            "effects_by_stage": dict(self.effects_by_stage),
            "total_effects_admitted": self.total_effects_admitted,
            "synthesis_initial_model_request_error": self.synthesis_initial_model_request_error,
            "synthesis_recovery_attempted": False,
            "synthesis_recovery_succeeded": False,
            "synthesis_recovery_model_request_error": False,
            "repair_blocked_after_recovery": False,
            "provider_requests_delta": delta["requests"],
            "provider_attempts_delta": delta["attempts"],
        }


def _treatment_raw_receipt(model: BoundedSynthesisRecoveryModel) -> dict[str, Any]:
    value = model.receipt()
    validate_recovery_receipt(value)
    return {
        "effects_by_stage": dict(value["effects_by_stage"]),
        "total_effects_admitted": value["total_effects_admitted"],
        "synthesis_initial_model_request_error": value[
            "synthesis_initial_model_request_error"
        ],
        "synthesis_recovery_attempted": value["synthesis_recovery_attempted"],
        "synthesis_recovery_succeeded": value["synthesis_recovery_succeeded"],
        "synthesis_recovery_model_request_error": value[
            "synthesis_recovery_model_request_error"
        ],
        "repair_blocked_after_recovery": value["repair_blocked_after_recovery"],
        "provider_requests_delta": value["provider_requests_delta"],
        "provider_attempts_delta": value["provider_attempts_delta"],
    }


def _project_receipt(arm: str, raw: Mapping[str, Any]) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "arm": arm,
        "recovery_enabled": arm == "candidate",
        "model_call_cap": 3,
        "effects_by_stage": dict(raw["effects_by_stage"]),
        "total_effects_admitted": int(raw["total_effects_admitted"]),
        "synthesis_initial_model_request_error": bool(
            raw["synthesis_initial_model_request_error"]
        ),
        "synthesis_recovery_attempted": bool(raw["synthesis_recovery_attempted"]),
        "synthesis_recovery_succeeded": bool(raw["synthesis_recovery_succeeded"]),
        "synthesis_recovery_model_request_error": bool(
            raw["synthesis_recovery_model_request_error"]
        ),
        "repair_blocked_after_recovery": bool(raw["repair_blocked_after_recovery"]),
        "provider_requests_delta": int(raw["provider_requests_delta"]),
        "provider_attempts_delta": int(raw["provider_attempts_delta"]),
        "fourth_model_effect": int(raw["total_effects_admitted"]) > 3,
        "question_prompt_response_prediction_answer_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    validate_receipt(value)
    return value


def zero_effect_receipt(arm: str) -> dict[str, Any]:
    if arm not in ARMS:
        raise ValueError("V2.43.03 zero-effect receipt arm is invalid")
    return _project_receipt(
        arm,
        {
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
        },
    )


def _reconcile_control_accounting(
    value: Mapping[str, Any], raw: Mapping[str, Any]
) -> dict[str, Any]:
    output = copy.deepcopy(dict(value))
    budget = dict(output["budget"])
    events = [dict(event) for event in budget.get("events") or []]
    admitted = [
        event
        for event in events
        if event.get("effect") == "model" and event.get("admitted") is True
    ]
    expected = int(raw["total_effects_admitted"])
    for stage in ("plan", "synthesis_initial", "repair"):
        event_stage = "synthesis" if stage == "synthesis_initial" else stage
        have = sum(
            event.get("stage") == event_stage and event.get("effect") == "model"
            for event in admitted
        )
        need = int(raw["effects_by_stage"][stage])
        for _ in range(max(0, need - have)):
            events.append({"stage": event_stage, "effect": "model", "admitted": True})
    budget["events"] = events
    budget["admitted_model_calls"] = expected
    output["budget"] = budget
    return output


def validate_receipt(value: Mapping[str, Any]) -> None:
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != RECEIPT_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("arm") not in ARMS
        or value.get("recovery_enabled") is not (value.get("arm") == "candidate")
        or value.get("model_call_cap") != 3
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
    ):
        raise ValueError("V2.43.03 recovery receipt identity drifted")
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
    if (
        not isinstance(effects, Mapping)
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
        or total != sum(effects.values())
        or not 0 <= total <= 3
        or requests != total
        or isinstance(attempts, bool)
        or not isinstance(attempts, int)
        or attempts < requests
        or effects["synthesis_recovery"] != int(value["synthesis_recovery_attempted"])
        or value["synthesis_recovery_succeeded"]
        and value["synthesis_recovery_model_request_error"]
        or value["synthesis_recovery_succeeded"]
        and not value["synthesis_recovery_attempted"]
        or value["synthesis_recovery_model_request_error"]
        and not value["synthesis_recovery_attempted"]
        or value["repair_blocked_after_recovery"]
        and not value["synthesis_recovery_attempted"]
        or value["arm"] == "baseline"
        and (
            effects["synthesis_recovery"]
            or value["synthesis_recovery_attempted"]
            or value["synthesis_recovery_succeeded"]
            or value["synthesis_recovery_model_request_error"]
            or value["repair_blocked_after_recovery"]
        )
        or value["arm"] == "candidate"
        and value["synthesis_recovery_attempted"]
        != value["synthesis_initial_model_request_error"]
    ):
        raise ValueError("V2.43.03 recovery receipt accounting drifted")


def validate_v24303_result(value: Mapping[str, Any], arm: str) -> str:
    if arm not in ARMS:
        raise ValueError("V2.43.03 arm is invalid")
    receipt = value.get(RECEIPT_FIELD)
    if not isinstance(receipt, Mapping) or receipt.get("arm") != arm:
        raise ValueError("V2.43.03 recovery receipt is absent")
    validate_receipt(receipt)
    parent = copy.deepcopy(dict(value))
    parent.pop(RECEIPT_FIELD, None)
    kind = "candidate"
    try:
        validate_v24296_result(parent)
    except (KeyError, TypeError, ValueError):
        kind = "fallback"
        try:
            validate_v24259_result(parent)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("V2.43.03 result is neither staged reserve nor fallback") from exc
        if parent.get("completion_kind") not in {
            "worker_failure_fallback",
            "hard_deadline_fallback",
        }:
            raise ValueError("V2.43.03 non-candidate result is not a total fallback")
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
        or value["cost"]["model"]["requests"] != receipt["provider_requests_delta"]
        or value["cost"]["model"]["attempts"] != receipt["provider_attempts_delta"]
    ):
        raise ValueError("V2.43.03 admission/provider accounting drifted")
    recovery_events = [
        event
        for event in budget["events"]
        if event.get("stage") == "synthesis_provider_recovery"
        and event.get("admitted") is True
    ]
    if len(recovery_events) != receipt["effects_by_stage"]["synthesis_recovery"]:
        raise ValueError("V2.43.03 recovery budget event drifted")
    telemetry = value.get("telemetry", {}).get("model_events", [])
    if kind == "candidate":
        if (
            not isinstance(telemetry, list)
            or sum(int(event["requests_delta"]) for event in telemetry)
            != receipt["provider_requests_delta"]
            or sum(int(event["attempts_delta"]) for event in telemetry)
            != receipt["provider_attempts_delta"]
        ):
            raise ValueError("V2.43.03 provider telemetry accounting drifted")
        if receipt["synthesis_recovery_attempted"]:
            synthesis = [event for event in telemetry if event.get("stage") == "synthesis"]
            if len(synthesis) != 1 or synthesis[0]["requests_delta"] != 2:
                raise ValueError("V2.43.03 recovery synthesis telemetry drifted")
    return kind


def run_v24303_task(
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
    if arm not in ARMS or limits.model_calls != 3 or reserve_policy is None:
        raise ValueError("V2.43.03 arm, exact cap, or shared reserve policy drifted")
    limits.validate()
    two_wave_policy.validate()
    reserve_policy.validate()
    control: SynthesisRecoveryControlModel | None = None
    treatment: BoundedSynthesisRecoveryModel | None = None
    if arm == "baseline":
        control = SynthesisRecoveryControlModel(model, model_call_cap=3)
        wrapped: Any = control
    else:
        treatment = BoundedSynthesisRecoveryModel(
            model, arm="candidate", model_call_cap=3
        )
        wrapped = treatment
    try:
        started = float(monotonic())
    except BaseException:
        started = 0.0
    model_start = _snapshot(model, MODEL_COUNTERS)
    search_start = _snapshot(search, SEARCH_COUNTERS)
    last_progress: dict[str, Any] = {}

    def raw_receipt() -> dict[str, Any]:
        if control is not None:
            return control.raw_receipt()
        assert treatment is not None
        return _treatment_raw_receipt(treatment)

    def capture(value: Mapping[str, Any]) -> None:
        nonlocal last_progress
        projected = dict(value)
        if treatment is not None:
            projected = _reconcile_accounting(projected, treatment.receipt())
        last_progress = projected
        if progress is not None:
            progress(projected)

    try:
        parent = run_v24296_task(
            visible,
            model=wrapped,
            search=search,
            limits=limits,
            two_wave_policy=two_wave_policy,
            reserve_policy=reserve_policy,
            monotonic=monotonic,
            progress=capture,
        )
    except BaseException as exc:
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
            failure_stage=f"v24303_{arm}_runtime_totality",
            failure_type=type(exc).__name__,
            elapsed_seconds=elapsed,
            last_progress=current,
        )
    raw = raw_receipt()
    result = copy.deepcopy(dict(parent))
    if treatment is not None:
        result = _reconcile_accounting(result, treatment.receipt())
    result = _reconcile_control_accounting(result, raw)
    result[RECEIPT_FIELD] = _project_receipt(arm, raw)
    validate_v24303_result(result, arm)
    return result


__all__ = [
    "ARMS",
    "POLICY_ID",
    "RECEIPT_FIELD",
    "SynthesisRecoveryControlModel",
    "run_v24303_task",
    "validate_receipt",
    "validate_v24303_result",
    "zero_effect_receipt",
]
