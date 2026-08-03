"""Bounded, label-blind recovery for a failed synthesis provider request.

The V2.42.98 post-terminal diagnosis found that the V2.42.97 candidate's five
extra fallbacks were synthesis/repair model-request failures, not retrieval
transport failures.  This build-only successor uses the already frozen third
logical model-call slot only when the first synthesis request raises the
content-free :class:`ModelRequestError`.  It does not recover plan failures,
semantic/format errors, arbitrary exceptions, or a failed repair request.

The wrapper explicitly reconciles the parent budget event, provider request
counter, and global-slot acquisition boundary.  If recovery consumed the
third slot and its output still needs repair, repair is denied before a fourth
provider effect.  Search, fetch, token, and wall-clock limits are unchanged.
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
from .v24286_visible_schema_runtime import run_v24286_task, validate_v24286_result
from .v24294_staged_reserve import StagedReservePolicy
from .v24296_staged_reserve_task_runtime import (
    run_v24296_task,
    validate_v24296_result,
)


POLICY_ID = "v24299_label_blind_bounded_synthesis_provider_recovery_v1"
RESULT_ROLE = "v24299_synthesis_recovery_task_result"
RECEIPT_ROLE = "v24299_synthesis_recovery_receipt"
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
        "model_call_cap",
        "effects_by_stage",
        "total_effects_admitted",
        "synthesis_initial_model_request_error",
        "synthesis_recovery_eligible",
        "synthesis_recovery_admitted",
        "synthesis_recovery_attempted",
        "synthesis_recovery_succeeded",
        "synthesis_recovery_model_request_error",
        "repair_blocked_after_recovery",
        "provider_requests_delta",
        "provider_attempts_delta",
        "question_prompt_response_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    }
)


class SynthesisRecoveryBudgetExhausted(RuntimeError):
    """A repair call was denied because recovery used the final frozen slot."""


def _snapshot(client: Any, names: tuple[str, ...]) -> dict[str, int]:
    try:
        return _counter_snapshot(client, names)
    except BaseException:
        return {name: 0 for name in names}


class BoundedSynthesisRecoveryModel:
    """Admit at most one exact synthesis replay inside a three-call cap."""

    def __init__(self, inner: Any, *, arm: str, model_call_cap: int) -> None:
        if arm not in ARMS or model_call_cap != 3:
            raise ValueError("V2.42.99 requires a known arm and exact three-call cap")
        self.inner = inner
        self.arm = arm
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
        self.synthesis_recovery_eligible = False
        self.synthesis_recovery_admitted = False
        self.synthesis_recovery_attempted = False
        self.synthesis_recovery_succeeded = False
        self.synthesis_recovery_model_request_error = False
        self.repair_blocked_after_recovery = False

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

    def _effect(
        self,
        stage: str,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool,
    ) -> Any:
        if self.total_effects_admitted >= self.model_call_cap:
            if stage == "repair" and self.synthesis_recovery_admitted:
                self.repair_blocked_after_recovery = True
                raise SynthesisRecoveryBudgetExhausted(
                    "V2.42.99 repair denied after synthesis recovery"
                )
            raise SynthesisRecoveryBudgetExhausted("V2.42.99 model-call cap exhausted")
        self.effects_by_stage[stage] += 1
        return self.inner.complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        stage = self._stage(json_mode)
        try:
            return self._effect(
                stage,
                system,
                user,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )
        except ModelRequestError:
            if stage != "synthesis_initial":
                raise
            self.synthesis_initial_model_request_error = True
            self.synthesis_recovery_eligible = True
            if self.total_effects_admitted >= self.model_call_cap:
                raise
            self.synthesis_recovery_admitted = True
            self.synthesis_recovery_attempted = True
            try:
                value = self._effect(
                    "synthesis_recovery",
                    system,
                    user,
                    max_output_tokens=max_output_tokens,
                    json_mode=json_mode,
                )
                self.synthesis_recovery_succeeded = True
                return value
            except ModelRequestError:
                self.synthesis_recovery_model_request_error = True
                raise

    def receipt(self) -> dict[str, Any]:
        delta = _counter_delta(_snapshot(self.inner, MODEL_COUNTERS), self._start)
        value = {
            "artifact_version": 1,
            "role": RECEIPT_ROLE,
            "policy_id": POLICY_ID,
            "arm": self.arm,
            "model_call_cap": self.model_call_cap,
            "effects_by_stage": dict(self.effects_by_stage),
            "total_effects_admitted": self.total_effects_admitted,
            "synthesis_initial_model_request_error": self.synthesis_initial_model_request_error,
            "synthesis_recovery_eligible": self.synthesis_recovery_eligible,
            "synthesis_recovery_admitted": self.synthesis_recovery_admitted,
            "synthesis_recovery_attempted": self.synthesis_recovery_attempted,
            "synthesis_recovery_succeeded": self.synthesis_recovery_succeeded,
            "synthesis_recovery_model_request_error": self.synthesis_recovery_model_request_error,
            "repair_blocked_after_recovery": self.repair_blocked_after_recovery,
            "provider_requests_delta": delta["requests"],
            "provider_attempts_delta": delta["attempts"],
            "question_prompt_response_prediction_answer_opaque_id_or_credential_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }
        validate_recovery_receipt(value)
        return value


def validate_recovery_receipt(value: Mapping[str, Any]) -> None:
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != RECEIPT_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("arm") not in ARMS
        or value.get("model_call_cap") != 3
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
        raise ValueError("V2.42.99 recovery receipt identity drifted")
    effects = value.get("effects_by_stage")
    if (
        not isinstance(effects, Mapping)
        or set(effects) != {"plan", "synthesis_initial", "synthesis_recovery", "repair"}
        or any(
            isinstance(number, bool)
            or not isinstance(number, int)
            or number not in {0, 1}
            for number in effects.values()
        )
    ):
        raise ValueError("V2.42.99 recovery effect accounting drifted")
    total = value.get("total_effects_admitted")
    requests = value.get("provider_requests_delta")
    attempts = value.get("provider_attempts_delta")
    flags = (
        "synthesis_initial_model_request_error",
        "synthesis_recovery_eligible",
        "synthesis_recovery_admitted",
        "synthesis_recovery_attempted",
        "synthesis_recovery_succeeded",
        "synthesis_recovery_model_request_error",
        "repair_blocked_after_recovery",
    )
    if (
        any(not isinstance(value.get(name), bool) for name in flags)
        or isinstance(total, bool)
        or not isinstance(total, int)
        or total != sum(effects.values())
        or not 0 <= total <= 3
        or isinstance(requests, bool)
        or not isinstance(requests, int)
        or requests != total
        or isinstance(attempts, bool)
        or not isinstance(attempts, int)
        or attempts < requests
        or effects["synthesis_recovery"] != int(value["synthesis_recovery_admitted"])
        or value["synthesis_recovery_admitted"]
        != value["synthesis_recovery_attempted"]
        or value["synthesis_recovery_eligible"]
        != value["synthesis_initial_model_request_error"]
        or value["synthesis_recovery_succeeded"]
        and value["synthesis_recovery_model_request_error"]
        or value["synthesis_recovery_succeeded"]
        and not value["synthesis_recovery_attempted"]
        or value["synthesis_recovery_model_request_error"]
        and not value["synthesis_recovery_attempted"]
        or value["repair_blocked_after_recovery"]
        and not value["synthesis_recovery_admitted"]
        or effects["repair"]
        and value["repair_blocked_after_recovery"]
    ):
        raise ValueError("V2.42.99 recovery receipt is inconsistent")


def _reconcile_accounting(
    value: Mapping[str, Any], receipt: Mapping[str, Any]
) -> dict[str, Any]:
    """Bind parent admission events to actual provider/slot effects."""

    output = copy.deepcopy(dict(value))
    container = output.get("budget") if isinstance(output.get("budget"), Mapping) else output
    container = dict(container)
    events = [dict(event) for event in (container.get("events") or [])]
    if receipt["synthesis_recovery_admitted"]:
        index = next(
            (
                position + 1
                for position, event in enumerate(events)
                if event.get("stage") == "synthesis" and event.get("effect") == "model"
            ),
            len(events),
        )
        events.insert(
            index,
            {
                "stage": "synthesis_provider_recovery",
                "effect": "model",
                "admitted": True,
            },
        )
    if receipt["repair_blocked_after_recovery"]:
        for event in events:
            if event.get("stage") == "repair" and event.get("effect") == "model":
                event["admitted"] = False
    container["events"] = events
    container["admitted_model_calls"] = receipt["total_effects_admitted"]
    if isinstance(output.get("budget"), Mapping):
        output["budget"] = container
    else:
        output.update(container)
    return output


def _run_parent(
    visible: Mapping[str, Any],
    *,
    arm: str,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits,
    two_wave_policy: TwoWavePolicy,
    reserve_policy: StagedReservePolicy | None,
    monotonic: Callable[[], float],
    progress: Callable[[Mapping[str, Any]], None] | None,
) -> dict[str, Any]:
    wrapper = BoundedSynthesisRecoveryModel(
        model, arm=arm, model_call_cap=limits.model_calls
    )

    def capture(value: Mapping[str, Any]) -> None:
        if progress is not None:
            progress(_reconcile_accounting(value, wrapper.receipt()))

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
        if reserve_policy is None:
            raise ValueError("V2.42.99 candidate reserve policy is absent")
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
    receipt = wrapper.receipt()
    result = _reconcile_accounting(parent, receipt)
    result["role"] = RESULT_ROLE
    result["policy_id"] = POLICY_ID
    result["synthesis_recovery"] = receipt
    validate_v24299_result(result, arm)
    return result


def run_v24299_task(
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
        raise ValueError("V2.42.99 arm or exact model-call cap drifted")
    limits.validate()
    two_wave_policy.validate()
    if reserve_policy is not None:
        reserve_policy.validate()
    return _run_parent(
        visible,
        arm=arm,
        model=model,
        search=search,
        limits=limits,
        two_wave_policy=two_wave_policy,
        reserve_policy=reserve_policy,
        monotonic=monotonic,
        progress=progress,
    )


def validate_v24299_result(value: Mapping[str, Any], arm: str) -> None:
    if (
        arm not in ARMS
        or value.get("role") != RESULT_ROLE
        or value.get("policy_id") != POLICY_ID
    ):
        raise ValueError("V2.42.99 result identity drifted")
    receipt = value.get("synthesis_recovery")
    if not isinstance(receipt, Mapping) or receipt.get("arm") != arm:
        raise ValueError("V2.42.99 recovery receipt is absent")
    validate_recovery_receipt(receipt)
    parent = copy.deepcopy(dict(value))
    parent.pop("synthesis_recovery", None)
    if arm == "baseline":
        parent["role"] = "v24286_visible_schema_timing_task_result"
        parent["policy_id"] = "v24286_label_blind_visible_schema_timing_v1"
        validate_v24286_result(parent)
    else:
        parent["role"] = "v24296_staged_reserve_task_result"
        parent["policy_id"] = "v24296_label_blind_visible_schema_staged_reserve_total_v1"
        validate_v24296_result(parent)
    budget = value["budget"]
    model_events = [
        event
        for event in budget["events"]
        if event.get("effect") == "model" and event.get("admitted") is True
    ]
    telemetry = value["telemetry"]["model_events"]
    if (
        budget["limits"]["model_calls"] != 3
        or budget["admitted_model_calls"] != receipt["total_effects_admitted"]
        or len(model_events) != receipt["total_effects_admitted"]
        or value["cost"]["model"]["requests"] != receipt["provider_requests_delta"]
        or value["cost"]["model"]["attempts"] != receipt["provider_attempts_delta"]
        or sum(int(event["requests_delta"]) for event in telemetry)
        != receipt["provider_requests_delta"]
        or sum(int(event["attempts_delta"]) for event in telemetry)
        != receipt["provider_attempts_delta"]
    ):
        raise ValueError("V2.42.99 admission/provider accounting drifted")
    recovery_events = [
        event for event in budget["events"] if event.get("stage") == "synthesis_provider_recovery"
    ]
    if len(recovery_events) != int(receipt["synthesis_recovery_admitted"]):
        raise ValueError("V2.42.99 recovery budget event drifted")
    if receipt["synthesis_recovery_admitted"]:
        synthesis = [event for event in telemetry if event["stage"] == "synthesis"]
        if len(synthesis) != 1 or synthesis[0]["requests_delta"] != 2:
            raise ValueError("V2.42.99 recovery telemetry drifted")
    if receipt["repair_blocked_after_recovery"]:
        repair_budget = [
            event
            for event in budget["events"]
            if event.get("stage") == "repair" and event.get("effect") == "model"
        ]
        repair_telemetry = [event for event in telemetry if event["stage"] == "repair"]
        if (
            len(repair_budget) != 1
            or repair_budget[0].get("admitted") is not False
            or len(repair_telemetry) != 1
            or repair_telemetry[0]["requests_delta"] != 0
            or repair_telemetry[0]["success"] is not False
        ):
            raise ValueError("V2.42.99 blocked repair accounting drifted")


def validate_v24299_total_result(value: Mapping[str, Any], arm: str) -> str:
    try:
        validate_v24299_result(value, arm)
        return "candidate"
    except (KeyError, TypeError, ValueError):
        try:
            validate_v24259_result(value)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("V2.42.99 result is neither candidate nor fallback") from exc
        if value.get("completion_kind") not in {
            "worker_failure_fallback",
            "hard_deadline_fallback",
        }:
            raise ValueError("V2.42.99 non-candidate result is not a total fallback")
        return "fallback"


def run_v24299_total_task(
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
    try:
        started = float(monotonic())
    except BaseException:
        started = 0.0
    model_start = _snapshot(model, MODEL_COUNTERS)
    search_start = _snapshot(search, SEARCH_COUNTERS)
    last_progress: dict[str, Any] = {}

    def capture(value: Mapping[str, Any]) -> None:
        nonlocal last_progress
        last_progress = dict(value)
        if progress is not None:
            progress(value)

    try:
        return run_v24299_task(
            visible,
            arm=arm,
            model=model,
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
        result = build_total_fallback_result(
            visible,
            limits=limits,
            completion_kind="worker_failure_fallback",
            failure_stage="v24299_runtime_totality",
            failure_type=type(exc).__name__,
            elapsed_seconds=elapsed,
            last_progress=current,
        )
        validate_v24299_total_result(result, arm)
        return result


__all__ = [
    "ARMS",
    "BoundedSynthesisRecoveryModel",
    "POLICY_ID",
    "RESULT_ROLE",
    "SynthesisRecoveryBudgetExhausted",
    "run_v24299_task",
    "run_v24299_total_task",
    "validate_recovery_receipt",
    "validate_v24299_result",
    "validate_v24299_total_result",
]
