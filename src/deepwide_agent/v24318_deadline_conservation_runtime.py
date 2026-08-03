"""Deadline-conserving model and cache accounting for future paired runs.

V2.43.17 established two valid terminal states that the older strict-equality
validators could not represent:

* a logical model call may be admitted, then rejected by the global slot/deadline
  boundary before the provider client is invoked; and
* retrieval may cache usable public pages, then the task wall budget may expire
  before the cache-only evidence projection is admitted.

This append-only runtime records both differences explicitly.  It does not
change prompts or the three-model/four-query/ten-fetch envelope, and it grants
no benchmark or evaluator authority.
"""

from __future__ import annotations

import copy
import hashlib
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
from .v24268_keyless_batched_runtime import (
    POLICY_ID as V24268_POLICY_ID,
    RESULT_ROLE as V24268_RESULT_ROLE,
    run_v24268_task,
    validate_v24268_result,
)
from .v24272_two_wave_entropy_voc import TwoWavePolicy
from .v24272_two_wave_retrieval import validate_retrieval_receipt
from .v24273_two_wave_task_runtime import (
    TwoWaveCachingSearchClient,
)
from .v24286_visible_schema_runtime import (
    VisibleSchemaModel,
    _schema_receipt,
    _schema_safe_question,
    _timing_receipt as baseline_timing_receipt,
    extract_robust_visible_columns,
    validate_schema_receipt,
    validate_timing_receipt,
)
from .v24294_staged_reserve import (
    StagedReservePolicy,
    validate_receipt as validate_staged_receipt,
)
from .v24296_staged_reserve_task_runtime import (
    StagedReserveCachingSearchClient,
    _timing_receipt as candidate_timing_receipt,
)
from .v24308_child_exit_observability import coarse_exception_type


POLICY_ID = "v24318_deadline_conservation_runtime_v1"
PARENT_ROLE = "v24318_deadline_conserving_parent_result"
MODEL_ROLE = "v24318_model_admission_conservation_receipt"
CACHE_ROLE = "v24318_cache_deadline_conservation_receipt"
MODEL_FIELD = "v24318_model_conservation"
CACHE_FIELD = "v24318_cache_conservation"
ARMS = ("baseline", "candidate")
STAGES = ("plan", "synthesis_initial", "synthesis_recovery", "repair")
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
MODEL_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "arm",
        "model_call_cap",
        "logical_admissions_by_stage",
        "provider_requests_by_stage",
        "provider_attempts_by_stage",
        "pre_provider_rejections_by_stage",
        "logical_admissions_total",
        "provider_requests_total",
        "provider_attempts_total",
        "pre_provider_rejections_total",
        "synthesis_initial_model_request_error",
        "synthesis_recovery_attempted",
        "synthesis_recovery_succeeded",
        "synthesis_recovery_model_request_error",
        "repair_blocked_after_recovery",
        "effect_count_complete",
        "effect_attribution_complete",
        "fourth_model_effect",
        "question_prompt_response_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    }
)
CACHE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "arm",
        "status",
        "cached_usable_pages",
        "cache_requested_pages",
        "cache_returned_pages",
        "cache_misses",
        "deadline_deferred_pages",
        "cache_serve_invocations",
        "inner_fetch_attempts",
        "network_fetches_during_cache_serve",
        "deadline_expired_before_cache_serve",
        "conservation_complete",
        "question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    }
)


def _snapshot(client: Any, names: tuple[str, ...]) -> dict[str, int]:
    try:
        return _counter_snapshot(client, names)
    except BaseException:
        return {name: 0 for name in names}


class DeadlineConservingRecoveryModel:
    """Bounded synthesis recovery with explicit pre-provider rejections."""

    def __init__(self, inner: Any, *, arm: str, model_call_cap: int = 3) -> None:
        if arm not in ARMS or model_call_cap != 3:
            raise ValueError("V2.43.18 requires a known arm and exact three-call cap")
        self.inner = inner
        self.arm = arm
        self.model_call_cap = model_call_cap
        self._start = _snapshot(inner, MODEL_COUNTERS)
        self._plan_seen = False
        self._synthesis_seen = False
        self.logical = {stage: 0 for stage in STAGES}
        self.requests_by_stage = {stage: 0 for stage in STAGES}
        self.attempts_by_stage = {stage: 0 for stage in STAGES}
        self.rejections_by_stage = {stage: 0 for stage in STAGES}
        self.synthesis_initial_model_request_error = False
        self.synthesis_recovery_attempted = False
        self.synthesis_recovery_succeeded = False
        self.synthesis_recovery_model_request_error = False
        self.repair_blocked_after_recovery = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    @property
    def logical_total(self) -> int:
        return sum(self.logical.values())

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
        if self.logical_total >= self.model_call_cap:
            if stage == "repair" and self.synthesis_recovery_attempted:
                self.repair_blocked_after_recovery = True
            raise ModelRequestError("V2.43.18 logical model-call cap exhausted")
        before = _snapshot(self.inner, MODEL_COUNTERS)
        self.logical[stage] += 1
        returned = False
        try:
            value = self.inner.complete(
                system,
                user,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )
            returned = True
            return value
        finally:
            delta = _counter_delta(_snapshot(self.inner, MODEL_COUNTERS), before)
            requests = int(delta["requests"])
            attempts = int(delta["attempts"])
            if requests not in {0, 1}:
                raise ValueError("V2.43.18 one logical call changed multiple provider requests")
            if requests == 0:
                self.rejections_by_stage[stage] += 1
                if returned:
                    raise ValueError("V2.43.18 provider-free model return is forbidden")
            self.requests_by_stage[stage] += requests
            self.attempts_by_stage[stage] += attempts

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
            # A slot/deadline rejection before provider invocation means the
            # shared effect window is already unavailable.  Do not issue a
            # second doomed logical recovery call inside cleanup reserve.
            if self.requests_by_stage[stage] != 1 or self.logical_total >= self.model_call_cap:
                raise
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
            "role": MODEL_ROLE,
            "policy_id": POLICY_ID,
            "arm": self.arm,
            "model_call_cap": self.model_call_cap,
            "logical_admissions_by_stage": dict(self.logical),
            "provider_requests_by_stage": dict(self.requests_by_stage),
            "provider_attempts_by_stage": dict(self.attempts_by_stage),
            "pre_provider_rejections_by_stage": dict(self.rejections_by_stage),
            "logical_admissions_total": self.logical_total,
            "provider_requests_total": int(delta["requests"]),
            "provider_attempts_total": int(delta["attempts"]),
            "pre_provider_rejections_total": sum(self.rejections_by_stage.values()),
            "synthesis_initial_model_request_error": self.synthesis_initial_model_request_error,
            "synthesis_recovery_attempted": self.synthesis_recovery_attempted,
            "synthesis_recovery_succeeded": self.synthesis_recovery_succeeded,
            "synthesis_recovery_model_request_error": self.synthesis_recovery_model_request_error,
            "repair_blocked_after_recovery": self.repair_blocked_after_recovery,
            "effect_count_complete": True,
            "effect_attribution_complete": True,
            "fourth_model_effect": False,
            "question_prompt_response_prediction_answer_opaque_id_or_credential_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }
        validate_model_receipt(value)
        return value


def validate_model_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    logical = value.get("logical_admissions_by_stage")
    requests = value.get("provider_requests_by_stage")
    attempts = value.get("provider_attempts_by_stage")
    rejected = value.get("pre_provider_rejections_by_stage")
    maps = (logical, requests, attempts, rejected)
    flags = (
        "synthesis_initial_model_request_error",
        "synthesis_recovery_attempted",
        "synthesis_recovery_succeeded",
        "synthesis_recovery_model_request_error",
        "repair_blocked_after_recovery",
        "effect_count_complete",
        "effect_attribution_complete",
        "fourth_model_effect",
    )
    if (
        set(value) != MODEL_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != MODEL_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("arm") not in ARMS
        or value.get("model_call_cap") != 3
        or any(not isinstance(item, Mapping) or set(item) != set(STAGES) for item in maps)
        or any(
            isinstance(number, bool) or not isinstance(number, int) or number < 0
            for item in maps
            for number in item.values()
        )
        or any(logical[stage] not in {0, 1} for stage in STAGES)
        or any(requests[stage] not in {0, 1} for stage in STAGES)
        or any(rejected[stage] not in {0, 1} for stage in STAGES)
        or any(logical[stage] != requests[stage] + rejected[stage] for stage in STAGES)
        or any(attempts[stage] and not requests[stage] for stage in STAGES)
        or any(not isinstance(value.get(name), bool) for name in flags)
        or value.get("effect_count_complete") is not True
        or value.get("effect_attribution_complete") is not True
        or value.get("fourth_model_effect") is not False
        or value.get("question_prompt_response_prediction_answer_opaque_id_or_credential_emitted")
        is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read")
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
    ):
        raise ValueError("V2.43.18 model conservation receipt drifted")
    logical_total = sum(logical.values())
    request_total = sum(requests.values())
    attempt_total = sum(attempts.values())
    rejected_total = sum(rejected.values())
    if (
        not 0 <= logical_total <= 3
        or value.get("logical_admissions_total") != logical_total
        or value.get("provider_requests_total") != request_total
        or value.get("provider_attempts_total") != attempt_total
        or value.get("pre_provider_rejections_total") != rejected_total
        or logical_total != request_total + rejected_total
        or value["synthesis_recovery_attempted"] != bool(logical["synthesis_recovery"])
        or value["synthesis_recovery_succeeded"]
        and value["synthesis_recovery_model_request_error"]
        or value["synthesis_recovery_succeeded"]
        and not value["synthesis_recovery_attempted"]
        or value["synthesis_recovery_model_request_error"]
        and not value["synthesis_recovery_attempted"]
        or value["repair_blocked_after_recovery"]
        and not value["synthesis_recovery_attempted"]
    ):
        raise ValueError("V2.43.18 model conservation invariant failed")
    return dict(value)


def _legacy_cache_receipt(proxy: Any) -> dict[str, Any]:
    observed = max(
        0,
        int(getattr(proxy.inner, "fetch_calls", 0) or 0)
        - int(proxy.initial_inner_fetch_calls),
    )
    if proxy._receipt is None:
        if proxy.failure_type is None:
            raise RuntimeError("V2.43.18 retrieval receipt is unavailable")
        return {
            "status": "failed",
            "failure_type": str(proxy.failure_type),
            "receipt": None,
            "cache_requested_source_count": 0,
            "cache_returned_page_count": 0,
            "cache_miss_count": 0,
            "observed_inner_fetch_calls": observed,
            "network_fetches_during_cache_serve": 0,
            "question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }
    return {
        "status": "completed",
        "failure_type": None,
        "receipt": copy.deepcopy(proxy._receipt),
        "cache_requested_source_count": int(proxy.cache_requested_source_count),
        "cache_returned_page_count": int(proxy.cache_returned_page_count),
        "cache_miss_count": int(proxy.cache_miss_count),
        "observed_inner_fetch_calls": observed,
        "network_fetches_during_cache_serve": max(
            0,
            int(proxy.network_fetches_after_cache_serve)
            - int(proxy.network_fetches_before_cache_serve),
        ),
        "question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }


def _cache_receipt(
    arm: str,
    legacy: Mapping[str, Any],
    *,
    elapsed_seconds: float,
    wall_seconds: float,
    cache_serve_invocations: int,
) -> dict[str, Any]:
    nested = legacy.get("receipt")
    cached = (
        int(nested["total"]["usable_pages"])
        if isinstance(nested, Mapping)
        else 0
    )
    requested = int(legacy.get("cache_requested_source_count", 0))
    returned = int(legacy.get("cache_returned_page_count", 0))
    misses = int(legacy.get("cache_miss_count", 0))
    expired = float(elapsed_seconds) >= float(wall_seconds)
    deferred = cached - requested if expired and requested <= cached else 0
    value = {
        "artifact_version": 1,
        "role": CACHE_ROLE,
        "policy_id": POLICY_ID,
        "arm": arm,
        "status": str(legacy.get("status")),
        "cached_usable_pages": cached,
        "cache_requested_pages": requested,
        "cache_returned_pages": returned,
        "cache_misses": misses,
        "deadline_deferred_pages": deferred,
        "cache_serve_invocations": int(cache_serve_invocations),
        "inner_fetch_attempts": int(legacy.get("observed_inner_fetch_calls", 0)),
        "network_fetches_during_cache_serve": int(
            legacy.get("network_fetches_during_cache_serve", 0)
        ),
        "deadline_expired_before_cache_serve": bool(deferred),
        "conservation_complete": True,
        "question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    validate_cache_receipt(value)
    return value


def validate_cache_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    numeric = CACHE_KEYS - {
        "artifact_version",
        "role",
        "policy_id",
        "arm",
        "status",
        "deadline_expired_before_cache_serve",
        "conservation_complete",
        "question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    }
    if (
        set(value) != CACHE_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != CACHE_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("arm") not in ARMS
        or value.get("status") not in {"completed", "failed"}
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in numeric
        )
        or not isinstance(value.get("deadline_expired_before_cache_serve"), bool)
        or value.get("conservation_complete") is not True
        or value.get("question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted")
        is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read")
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
    ):
        raise ValueError("V2.43.18 cache conservation receipt drifted")
    cached = value["cached_usable_pages"]
    requested = value["cache_requested_pages"]
    returned = value["cache_returned_pages"]
    misses = value["cache_misses"]
    deferred = value["deadline_deferred_pages"]
    if (
        requested != returned + misses
        or cached != returned + deferred
        or value["network_fetches_during_cache_serve"] != 0
        or bool(deferred) != value["deadline_expired_before_cache_serve"]
        or deferred and (requested != 0 or value["cache_serve_invocations"] != 0)
        or not deferred and value["status"] == "completed" and requested != cached
        or value["status"] == "failed"
        and any((cached, requested, returned, misses, deferred, value["cache_serve_invocations"]))
    ):
        raise ValueError("V2.43.18 cache conservation invariant failed")
    return dict(value)


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
    columns = extract_robust_visible_columns(str(visible["question"]))
    applied = bool(columns)
    forward_task: Mapping[str, Any] = visible
    forward_model = model
    schema_model: VisibleSchemaModel | None = None
    if applied:
        forward_task = {
            "opaque_id": visible["opaque_id"],
            "question": _schema_safe_question(str(visible["question"]), columns),
        }
        schema_model = VisibleSchemaModel(
            model, columns=columns, question=str(visible["question"])
        )
        forward_model = schema_model
    if arm == "baseline":
        proxy: Any = TwoWaveCachingSearchClient(
            search,
            required_column_count=len(columns) or 3,
            policy=two_wave_policy,
            monotonic=monotonic,
        )
        retrieval_field = "two_wave_retrieval"
    else:
        if reserve_policy is None:
            raise ValueError("V2.43.18 candidate reserve policy is absent")
        proxy = StagedReserveCachingSearchClient(
            search,
            required_column_count=len(columns) or 3,
            two_wave_policy=two_wave_policy,
            reserve_policy=reserve_policy,
            monotonic=monotonic,
        )
        retrieval_field = "staged_reserve_retrieval"
    parent68 = run_v24268_task(
        forward_task,
        model=forward_model,
        search=proxy,
        limits=limits,
        monotonic=monotonic,
        progress=progress,
    )
    if proxy.failure_type == "KeyboardInterrupt":
        raise KeyboardInterrupt
    if proxy.failure_type == "SystemExit":
        raise SystemExit
    if proxy.failure_type == "GeneratorExit":
        raise GeneratorExit
    legacy = _legacy_cache_receipt(proxy)
    result = dict(parent68)
    result["role"] = PARENT_ROLE
    result["policy_id"] = POLICY_ID
    result["arm"] = arm
    result[retrieval_field] = legacy
    result["visible_schema"] = _schema_receipt(
        columns=columns,
        applied=applied,
        events=schema_model.events if schema_model is not None else [],
    )
    result[CACHE_FIELD] = _cache_receipt(
        arm,
        legacy,
        elapsed_seconds=float(result["budget"]["elapsed_seconds"]),
        wall_seconds=float(limits.wall_seconds),
        cache_serve_invocations=int(proxy.cache_serve_invocations),
    )
    result["attributed_timing"] = (
        baseline_timing_receipt(result)
        if arm == "baseline"
        else candidate_timing_receipt(result)
    )
    result["prediction_sha256"] = hashlib.sha256(
        str(result["prediction"]).encode("utf-8")
    ).hexdigest()
    validate_parent_result(result, arm)
    return result


def validate_parent_result(value: Mapping[str, Any], arm: str) -> None:
    retrieval_field = "two_wave_retrieval" if arm == "baseline" else "staged_reserve_retrieval"
    if (
        arm not in ARMS
        or value.get("role") != PARENT_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("arm") != arm
        or not isinstance(value.get(retrieval_field), Mapping)
        or not isinstance(value.get("visible_schema"), Mapping)
        or not isinstance(value.get("attributed_timing"), Mapping)
        or not isinstance(value.get(CACHE_FIELD), Mapping)
    ):
        raise ValueError("V2.43.18 parent identity drifted")
    retrieval = value[retrieval_field]
    cache = validate_cache_receipt(value[CACHE_FIELD])
    validate_schema_receipt(value["visible_schema"])
    validate_timing_receipt(value["attributed_timing"])
    parent = copy.deepcopy(dict(value))
    for name in (
        retrieval_field,
        "visible_schema",
        "attributed_timing",
        CACHE_FIELD,
        "arm",
    ):
        parent.pop(name, None)
    parent["role"] = V24268_RESULT_ROLE
    parent["policy_id"] = V24268_POLICY_ID
    validate_v24268_result(parent)
    if (
        value["visible_schema"]["status"] == "applied"
        and value["visible_schema"]["column_count"] != len(parent["columns"])
    ):
        raise ValueError("V2.43.18 visible schema did not reach result")
    if abs(
        float(value["attributed_timing"]["task_wall_seconds"])
        - float(parent["budget"]["elapsed_seconds"])
    ) > 1e-6:
        raise ValueError("V2.43.18 timing is not bound to task")
    if retrieval.get("status") == "failed":
        if (
            cache["status"] != "failed"
            or parent["budget"]["admitted_fetch_targets"] != 0
            or parent["evidence"]["fetch_target_count"] != 0
            or cache["inner_fetch_attempts"] != parent["cost"]["search"]["fetch_calls"]
        ):
            raise ValueError("V2.43.18 failed retrieval accounting drifted")
        return
    nested = retrieval.get("receipt")
    if not isinstance(nested, Mapping):
        raise ValueError("V2.43.18 nested retrieval receipt is absent")
    if arm == "baseline":
        validate_retrieval_receipt(nested)
    else:
        validate_staged_receipt(nested)
    total = nested["total"]
    if (
        cache["status"] != "completed"
        or cache["cached_usable_pages"] != total["usable_pages"]
        or cache["cache_requested_pages"] != retrieval["cache_requested_source_count"]
        or cache["cache_returned_pages"] != retrieval["cache_returned_page_count"]
        or cache["cache_misses"] != retrieval["cache_miss_count"]
        or cache["inner_fetch_attempts"] != retrieval["observed_inner_fetch_calls"]
        or cache["inner_fetch_attempts"] != total["fetches_attempted"]
        or total["queries_executed"] > parent["budget"]["admitted_search_queries"]
        or cache["cache_returned_pages"] != parent["budget"]["admitted_fetch_targets"]
        or cache["cache_returned_pages"] != parent["evidence"]["fetch_target_count"]
        or total["fetches_attempted"] != parent["cost"]["search"]["fetch_calls"]
        or cache["deadline_deferred_pages"]
        and float(parent["budget"]["elapsed_seconds"])
        < float(parent["budget"]["limits"]["wall_seconds"])
    ):
        raise ValueError("V2.43.18 parent/cache effect conservation drifted")


def _reconcile(value: Mapping[str, Any], receipt: Mapping[str, Any]) -> dict[str, Any]:
    validate_model_receipt(receipt)
    output = copy.deepcopy(dict(value))
    nested = isinstance(output.get("budget"), Mapping)
    budget = dict(output["budget"] if nested else output)
    events = [dict(event) for event in budget.get("events") or []]
    if receipt["logical_admissions_by_stage"]["synthesis_recovery"]:
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
            {"stage": "synthesis_provider_recovery", "effect": "model", "admitted": True},
        )
    if receipt["repair_blocked_after_recovery"]:
        for event in events:
            if event.get("stage") == "repair" and event.get("effect") == "model":
                event["admitted"] = False
    budget["events"] = events
    budget["admitted_model_calls"] = receipt["logical_admissions_total"]
    if nested:
        output["budget"] = budget
    else:
        output.update(budget)
    output[MODEL_FIELD] = copy.deepcopy(dict(receipt))
    return output


def _fallback_events(receipt: Mapping[str, Any]) -> list[dict[str, Any]]:
    names = {
        "plan": "plan",
        "synthesis_initial": "synthesis",
        "synthesis_recovery": "synthesis_provider_recovery",
        "repair": "repair",
    }
    return [
        {"stage": names[stage], "effect": "model", "admitted": True}
        for stage in STAGES
        if receipt["logical_admissions_by_stage"][stage]
    ]


def run_v24318_task(
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
        raise ValueError("V2.43.18 arm or model-call cap drifted")
    if arm == "baseline" and reserve_policy is not None:
        raise ValueError("V2.43.18 baseline must not receive reserve policy")
    if arm == "candidate" and reserve_policy is None:
        raise ValueError("V2.43.18 candidate reserve policy is absent")
    limits.validate()
    two_wave_policy.validate()
    if reserve_policy is not None:
        reserve_policy.validate()
    started = float(monotonic())
    model_start = _snapshot(model, MODEL_COUNTERS)
    search_start = _snapshot(search, SEARCH_COUNTERS)
    wrapper = DeadlineConservingRecoveryModel(model, arm=arm, model_call_cap=3)
    last_progress: dict[str, Any] = {}

    def capture(value: Mapping[str, Any]) -> None:
        nonlocal last_progress
        last_progress = _reconcile(value, wrapper.receipt())
        if progress is not None:
            progress(last_progress)

    try:
        parent = _run_parent(
            visible,
            arm=arm,
            model=wrapper,
            search=search,
            limits=limits,
            two_wave_policy=two_wave_policy,
            reserve_policy=reserve_policy,
            monotonic=monotonic,
            progress=capture,
        )
        result = _reconcile(parent, wrapper.receipt())
        validate_v24318_result(result, arm)
        return result
    except BaseException as error:
        receipt = wrapper.receipt()
        current = dict(last_progress)
        current["model_cost"] = _counter_delta(
            _snapshot(model, MODEL_COUNTERS), model_start
        )
        current["search_cost"] = _counter_delta(
            _snapshot(search, SEARCH_COUNTERS), search_start
        )
        current["admitted_model_calls"] = receipt["logical_admissions_total"]
        value = build_total_fallback_result(
            visible,
            limits=limits,
            completion_kind="worker_failure_fallback",
            failure_stage="v24318_deadline_totality",
            failure_type=coarse_exception_type(error),
            elapsed_seconds=max(0.0, float(monotonic()) - started),
            last_progress=current,
        )
        value["budget"]["events"] = _fallback_events(receipt)
        value["budget"]["admitted_model_calls"] = receipt["logical_admissions_total"]
        value[MODEL_FIELD] = receipt
        validate_v24318_result(value, arm)
        return value


def validate_v24318_result(value: Mapping[str, Any], arm: str) -> str:
    if arm not in ARMS:
        raise ValueError("V2.43.18 arm is invalid")
    receipt = value.get(MODEL_FIELD)
    if not isinstance(receipt, Mapping) or receipt.get("arm") != arm:
        raise ValueError("V2.43.18 model conservation receipt is absent")
    validate_model_receipt(receipt)
    parent = copy.deepcopy(dict(value))
    parent.pop(MODEL_FIELD, None)
    kind = "candidate"
    try:
        validate_parent_result(parent, arm)
    except (KeyError, TypeError, ValueError):
        kind = "fallback"
        validate_v24259_result(parent)
        if parent.get("completion_kind") not in {
            "worker_failure_fallback",
            "hard_deadline_fallback",
        }:
            raise ValueError("V2.43.18 fallback boundary drifted")
    budget = value["budget"]
    admitted = [
        event
        for event in budget["events"]
        if event.get("effect") == "model" and event.get("admitted") is True
    ]
    if (
        budget["limits"]["model_calls"] != 3
        or budget["admitted_model_calls"] != receipt["logical_admissions_total"]
        or len(admitted) != receipt["logical_admissions_total"]
        or value["cost"]["model"]["requests"] != receipt["provider_requests_total"]
        or value["cost"]["model"]["attempts"] != receipt["provider_attempts_total"]
        or receipt["logical_admissions_total"]
        != receipt["provider_requests_total"] + receipt["pre_provider_rejections_total"]
    ):
        raise ValueError("V2.43.18 model effect conservation drifted")
    recovery_events = [
        event
        for event in admitted
        if event.get("stage") == "synthesis_provider_recovery"
    ]
    if len(recovery_events) != receipt["logical_admissions_by_stage"]["synthesis_recovery"]:
        raise ValueError("V2.43.18 recovery event accounting drifted")
    if kind == "candidate":
        telemetry = value.get("telemetry", {}).get("model_events", [])
        if (
            not isinstance(telemetry, list)
            or sum(int(event["requests_delta"]) for event in telemetry)
            != receipt["provider_requests_total"]
            or sum(int(event["attempts_delta"]) for event in telemetry)
            != receipt["provider_attempts_total"]
        ):
            raise ValueError("V2.43.18 provider telemetry accounting drifted")
    return kind


__all__ = [
    "ARMS",
    "CACHE_FIELD",
    "DeadlineConservingRecoveryModel",
    "MODEL_FIELD",
    "POLICY_ID",
    "run_v24318_task",
    "validate_cache_receipt",
    "validate_model_receipt",
    "validate_parent_result",
    "validate_v24318_result",
]
