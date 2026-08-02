"""Shared-prefix paired runtime for deterministic table normalization.

One visible task executes planning, retrieval, page projection, and synthesis
exactly once.  The raw synthesis response then branches into the frozen
V2.42.57 control parser and the V2.42.59 deterministic-normalizer candidate.
If either branch still requires repair, one shared repair response is consumed;
each arm receives only the counterfactual cost and latency it would have paid.

The runtime accepts only ``opaque_id`` and ``question``.  Evaluator metadata is
neither accepted nor available, and no post-terminal score can affect either
prediction.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import re
import time
from collections.abc import Callable, Mapping
from typing import Any

from .v24257_score_first_runtime import (
    PLAN_SYSTEM,
    PLAN_USER,
    POLICY_ID as CONTROL_POLICY_ID,
    REPAIR_SYSTEM,
    REPAIR_USER,
    SYNTHESIS_SYSTEM,
    SYNTHESIS_USER,
    ScoreFirstLimits,
    _Budget,
    _counter_delta,
    _counter_snapshot,
    _evidence_projection,
    _lead_requests,
    _model_text,
    _safe_exception,
    _validated_plan,
    build_best_effort_prediction,
    build_score_first_fallback_result,
    extract_valid_markdown_table,
    extract_visible_columns,
    parse_json_object,
    validate_score_first_result,
    validate_visible_task,
)
from .v24259_deterministic_table_normalizer import (
    POLICY_ID as CANDIDATE_POLICY_ID,
    _promote_result,
    build_v24259_fallback_result,
    normalize_candidate_table,
    validate_v24259_result,
)


POLICY_ID = "v24265_shared_prefix_paired_normalizer_v1"
RESULT_ROLE = "v24265_shared_prefix_paired_task_result"
MODEL_COUNTERS = (
    "requests",
    "attempts",
    "input_tokens",
    "output_tokens",
    "total_tokens",
)
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
PAIR_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "opaque_id",
        "control",
        "candidate",
        "shared_execution",
        "label_blind",
        "mapping_gold_category_question_type_split_evaluator_score_read",
    }
)
CONTROL_ARM_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "opaque_id",
        "status",
        "completion_kind",
        "prediction",
        "prediction_sha256",
        "columns",
        "plan",
        "evidence",
        "budget",
        "cost",
        "failures",
        "contract_errors_before_fallback",
        "label_blind",
        "mapping_gold_evaluator_or_score_read",
    }
)
CANDIDATE_ARM_KEYS = CONTROL_ARM_KEYS | {"normalization"}
PLAN_KEYS = frozenset({"language", "row_target_hint", "query_count"})
EVIDENCE_KEYS = frozenset(
    {"search_batch_count", "fetch_target_count", "projected_chars"}
)
BUDGET_KEYS = frozenset(
    {
        "limits",
        "admitted_model_calls",
        "admitted_search_queries",
        "admitted_fetch_targets",
        "elapsed_seconds",
        "deadline_exceeded_at_return",
        "events",
    }
)
LIMIT_KEYS = frozenset(field.name for field in dataclasses.fields(ScoreFirstLimits))
COST_KEYS = frozenset({"model", "search", "system_total_tokens"})
NORMALIZATION_KEYS = frozenset(
    {
        "parent_policy_id",
        "events",
        "question_candidate_or_cell_content_emitted",
        "nonempty_factual_cell_rewritten",
        "mapping_gold_category_question_type_evaluator_score_read",
    }
)
SHARED_KEYS = frozenset(
    {
        "plan_search_fetch_and_synthesis_shared",
        "repair_response_shared_when_both_arms_require_repair",
        "actual_model_cost",
        "actual_search_cost",
        "raw_synthesis_sha256",
        "evidence_sha256",
        "control_needed_repair",
        "candidate_needed_repair",
        "evaluator_feedback_available_or_used",
    }
)


def _add_costs(*values: Mapping[str, int]) -> dict[str, int]:
    keys = set().union(*(value.keys() for value in values))
    return {key: sum(int(value.get(key, 0)) for value in values) for key in keys}


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _nonnegative_integer(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.42.65 {label} is not a nonnegative integer")
    return value


def _validate_counter_map(
    value: object, *, keys: tuple[str, ...], label: str
) -> dict[str, int]:
    if not isinstance(value, Mapping) or set(value) != set(keys):
        raise ValueError(f"V2.42.65 {label} counter schema drifted")
    return {
        key: _nonnegative_integer(value.get(key), label=f"{label}.{key}")
        for key in keys
    }


def _validate_arm_schema(value: Mapping[str, Any], *, candidate: bool) -> None:
    expected = CANDIDATE_ARM_KEYS if candidate else CONTROL_ARM_KEYS
    if set(value) != expected or value.get("artifact_version") != 1:
        raise ValueError("V2.42.65 paired arm schema drifted")
    if candidate:
        validate_v24259_result(value)
        normalization = value.get("normalization")
        if not isinstance(normalization, Mapping) or set(normalization) != NORMALIZATION_KEYS:
            raise ValueError("V2.42.65 candidate normalization schema drifted")
    else:
        validate_score_first_result(value)
    plan = value.get("plan")
    evidence = value.get("evidence")
    budget = value.get("budget")
    cost = value.get("cost")
    if not isinstance(plan, Mapping) or set(plan) != PLAN_KEYS:
        raise ValueError("V2.42.65 paired arm plan schema drifted")
    if not isinstance(evidence, Mapping) or set(evidence) != EVIDENCE_KEYS:
        raise ValueError("V2.42.65 paired arm evidence schema drifted")
    if not isinstance(budget, Mapping) or set(budget) != BUDGET_KEYS:
        raise ValueError("V2.42.65 paired arm budget schema drifted")
    if not isinstance(cost, Mapping) or set(cost) != COST_KEYS:
        raise ValueError("V2.42.65 paired arm cost schema drifted")
    if (
        not isinstance(plan.get("language"), str)
        or not isinstance(plan.get("row_target_hint"), str)
    ):
        raise ValueError("V2.42.65 paired arm plan value drifted")
    _nonnegative_integer(plan.get("query_count"), label="plan.query_count")
    for key in EVIDENCE_KEYS:
        _nonnegative_integer(evidence.get(key), label=f"evidence.{key}")
    limits = budget.get("limits")
    if not isinstance(limits, Mapping) or set(limits) != LIMIT_KEYS:
        raise ValueError("V2.42.65 paired arm limit schema drifted")
    ScoreFirstLimits(**dict(limits)).validate()
    for key in (
        "admitted_model_calls",
        "admitted_search_queries",
        "admitted_fetch_targets",
    ):
        _nonnegative_integer(budget.get(key), label=f"budget.{key}")
    elapsed = budget.get("elapsed_seconds")
    if (
        isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not math.isfinite(float(elapsed))
        or float(elapsed) < 0
        or not isinstance(budget.get("deadline_exceeded_at_return"), bool)
        or not isinstance(budget.get("events"), list)
    ):
        raise ValueError("V2.42.65 paired arm budget value drifted")
    for event in budget["events"]:
        if (
            not isinstance(event, Mapping)
            or set(event)
            not in (
                {"stage", "effect", "admitted"},
                {"stage", "effect", "requested", "admitted"},
            )
            or not isinstance(event.get("stage"), str)
            or not isinstance(event.get("effect"), str)
        ):
            raise ValueError("V2.42.65 paired arm budget event schema drifted")
        if "requested" in event:
            _nonnegative_integer(event.get("requested"), label="event.requested")
            _nonnegative_integer(event.get("admitted"), label="event.admitted")
        elif not isinstance(event.get("admitted"), bool):
            raise ValueError("V2.42.65 paired arm model admission drifted")
    model = _validate_counter_map(cost.get("model"), keys=MODEL_COUNTERS, label="model")
    search = _validate_counter_map(
        cost.get("search"), keys=SEARCH_COUNTERS, label="search"
    )
    system_total = _nonnegative_integer(
        cost.get("system_total_tokens"), label="system_total_tokens"
    )
    if system_total != model["total_tokens"] + search["total_tokens"]:
        raise ValueError("V2.42.65 paired arm total-token accounting drifted")
    errors = value.get("contract_errors_before_fallback")
    if not isinstance(errors, list) or any(not isinstance(item, str) for item in errors):
        raise ValueError("V2.42.65 paired arm contract-error schema drifted")


def _normalization_event(
    text: str, question: str, columns: list[str], stage: str
) -> tuple[str, dict[str, Any]]:
    if not extract_visible_columns(question):
        return text, {
            "stage": stage,
            "status": "unrecoverable",
            "mode": "no_explicit_visible_columns",
            "candidate_group_count": 0,
            "input_column_count": 0,
            "output_column_count": 0,
            "input_row_count": 0,
            "output_row_count": 0,
            "dropped_row_count": 0,
            "filled_empty_cell_count": 0,
        }
    marker = "未知" if re.search(r"[\u4e00-\u9fff]", question) else "Unknown"
    normalized, diagnostics = normalize_candidate_table(
        text, columns, unknown_marker=marker
    )
    return normalized if normalized is not None else text, {
        "stage": stage,
        **diagnostics,
    }


def _arm_result(
    *,
    visible: dict[str, str],
    policy: ScoreFirstLimits,
    plan: dict[str, Any],
    query_count: int,
    search_batch_count: int,
    fetch_count: int,
    evidence_chars: int,
    prediction: str | None,
    completion_kind: str,
    contract_errors: list[str],
    failures: list[dict[str, str]],
    elapsed: float,
    model_cost: Mapping[str, int],
    search_cost: Mapping[str, int],
    admitted_model_calls: int,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    columns = list(plan["columns"])
    if prediction is None:
        prediction = build_best_effort_prediction(visible["question"], columns)
        completion_kind = "best_effort_fallback"
    model = {name: int(model_cost.get(name, 0)) for name in MODEL_COUNTERS}
    search = {name: int(search_cost.get(name, 0)) for name in SEARCH_COUNTERS}
    value = {
        "artifact_version": 1,
        "role": "v24257_score_first_task_result",
        "policy_id": CONTROL_POLICY_ID,
        "opaque_id": visible["opaque_id"],
        "status": "completed",
        "completion_kind": completion_kind,
        "prediction": prediction,
        "prediction_sha256": hashlib.sha256(prediction.encode("utf-8")).hexdigest(),
        "columns": columns,
        "plan": {
            "language": plan["language"],
            "row_target_hint": plan["row_target_hint"],
            "query_count": query_count,
        },
        "evidence": {
            "search_batch_count": search_batch_count,
            "fetch_target_count": fetch_count,
            "projected_chars": evidence_chars,
        },
        "budget": {
            "limits": dataclasses.asdict(policy),
            "admitted_model_calls": admitted_model_calls,
            "admitted_search_queries": query_count,
            "admitted_fetch_targets": fetch_count,
            "elapsed_seconds": round(max(0.0, elapsed), 3),
            "deadline_exceeded_at_return": elapsed > policy.wall_seconds,
            "events": events,
        },
        "cost": {
            "model": model,
            "search": search,
            "system_total_tokens": model["total_tokens"] + search["total_tokens"],
        },
        "failures": [dict(item) for item in failures],
        "contract_errors_before_fallback": list(contract_errors),
        "label_blind": True,
        "mapping_gold_evaluator_or_score_read": False,
    }
    validate_score_first_result(value)
    return value


def run_paired_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    progress: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    policy = limits or ScoreFirstLimits()
    policy.validate()
    started = float(monotonic())
    budget = _Budget(policy, started, monotonic)
    model_start = _counter_snapshot(model, MODEL_COUNTERS)
    search_start = _counter_snapshot(search, SEARCH_COUNTERS)
    common_failures: list[dict[str, str]] = []

    def emit(stage: str, search_batches: int = 0, projected_chars: int = 0) -> None:
        if progress is None:
            return
        progress(
            {
                "artifact_version": 1,
                "role": "v24265_paired_safe_progress",
                "stage": stage,
                "elapsed_seconds": round(max(0.0, float(monotonic()) - started), 3),
                "admitted_shared_model_calls": budget.admitted_model_calls,
                "admitted_search_queries": budget.admitted_search_queries,
                "admitted_fetch_targets": budget.admitted_fetch_targets,
                "search_batch_count": int(search_batches),
                "projected_chars": int(projected_chars),
                "model_cost": _counter_delta(
                    _counter_snapshot(model, MODEL_COUNTERS), model_start
                ),
                "search_cost": _counter_delta(
                    _counter_snapshot(search, SEARCH_COUNTERS), search_start
                ),
                "contains_question_query_url_page_prediction_answer_or_opaque_id": False,
                "mapping_gold_category_question_type_split_evaluator_score_read": False,
            }
        )

    emit("started")
    before_plan = _counter_snapshot(model, MODEL_COUNTERS)
    plan_admitted = budget.admit_model("shared_plan")
    if plan_admitted:
        try:
            response = model.complete(
                PLAN_SYSTEM,
                PLAN_USER.format(
                    question=visible["question"], query_limit=policy.search_queries
                ),
                max_output_tokens=policy.plan_output_tokens,
                json_mode=True,
            )
            plan = _validated_plan(
                parse_json_object(_model_text(response)), visible["question"], policy
            )
        except BaseException as exc:
            common_failures.append({"stage": "plan", **_safe_exception(exc)})
            plan = _validated_plan({}, visible["question"], policy)
    else:
        plan = _validated_plan({}, visible["question"], policy)
    after_plan = _counter_snapshot(model, MODEL_COUNTERS)
    plan_cost = _counter_delta(after_plan, before_plan)
    emit("plan_terminal")

    query_count = budget.admit_search(len(plan["queries"]))
    queries = plan["queries"][:query_count]
    search_batches: list[dict[str, Any]] = []
    if queries:
        try:
            search_batches = search.search_many(
                queries,
                max_results=policy.search_results_per_query,
                search_depth="advanced",
                include_raw_content=False,
            )
        except BaseException as exc:
            common_failures.append({"stage": "retrieval", **_safe_exception(exc)})
    emit("retrieval_terminal", len(search_batches))

    leads = _lead_requests(search_batches, policy.fetch_targets)
    fetch_count = budget.admit_fetch(len(leads))
    page_batches: list[dict[str, Any]] = []
    if fetch_count:
        try:
            page_batches = search.fetch_urls(leads[:fetch_count])
        except BaseException as exc:
            common_failures.append(
                {"stage": "page_projection", **_safe_exception(exc)}
            )
    evidence = _evidence_projection(search_batches, page_batches, policy)
    after_search = _counter_snapshot(search, SEARCH_COUNTERS)
    search_cost = _counter_delta(after_search, search_start)
    emit("page_projection_terminal", len(search_batches), len(evidence))

    columns = list(plan["columns"])
    raw_candidate = ""
    before_synthesis = _counter_snapshot(model, MODEL_COUNTERS)
    synthesis_error = ["synthesis was not admitted"]
    synthesis_admitted = budget.admit_model("shared_synthesis")
    if synthesis_admitted:
        try:
            response = model.complete(
                SYNTHESIS_SYSTEM,
                SYNTHESIS_USER.format(
                    question=visible["question"],
                    columns=json.dumps(columns, ensure_ascii=False),
                    evidence=evidence,
                ),
                max_output_tokens=policy.synthesis_output_tokens,
                json_mode=False,
            )
            raw_candidate = _model_text(response)
        except BaseException as exc:
            common_failures.append({"stage": "synthesis", **_safe_exception(exc)})
            synthesis_error = ["synthesis provider failure"]
    after_synthesis = _counter_snapshot(model, MODEL_COUNTERS)
    synthesis_cost = _counter_delta(after_synthesis, before_synthesis)
    emit("synthesis_terminal", len(search_batches), len(evidence))

    control_prediction: str | None = None
    candidate_prediction: str | None = None
    control_errors = list(synthesis_error)
    candidate_errors = list(synthesis_error)
    control_kind = "best_effort_fallback"
    candidate_kind = "best_effort_fallback"
    normalization_events: list[dict[str, Any]] = []
    if raw_candidate:
        control_prediction, control_errors = extract_valid_markdown_table(
            raw_candidate, columns
        )
        if control_prediction is not None:
            control_kind = "primary"
        normalized_text, event = _normalization_event(
            raw_candidate, visible["question"], columns, "synthesis"
        )
        normalization_events.append(event)
        candidate_prediction, candidate_errors = extract_valid_markdown_table(
            normalized_text, columns
        )
        if candidate_prediction is not None:
            candidate_kind = "primary"
    synthesis_terminal = max(0.0, float(monotonic()) - started)

    control_needs_repair = control_prediction is None and bool(raw_candidate)
    candidate_needs_repair = candidate_prediction is None and bool(raw_candidate)
    repair_cost = {name: 0 for name in MODEL_COUNTERS}
    repair_failure: dict[str, str] | None = None
    repair_admitted = False
    if control_needs_repair or candidate_needs_repair:
        repair_admitted = budget.admit_model("shared_repair")
    if repair_admitted:
        before_repair = _counter_snapshot(model, MODEL_COUNTERS)
        try:
            response = model.complete(
                REPAIR_SYSTEM,
                REPAIR_USER.format(
                    question=visible["question"],
                    columns=json.dumps(columns, ensure_ascii=False),
                    candidate=raw_candidate[:80_000],
                    errors=json.dumps(control_errors, ensure_ascii=False),
                ),
                max_output_tokens=policy.repair_output_tokens,
                json_mode=False,
            )
            repaired = _model_text(response)
            if control_needs_repair:
                control_prediction, control_errors = extract_valid_markdown_table(
                    repaired, columns
                )
                if control_prediction is not None:
                    control_kind = "repaired"
            if candidate_needs_repair:
                normalized_repair, event = _normalization_event(
                    repaired, visible["question"], columns, "repair"
                )
                normalization_events.append(event)
                candidate_prediction, candidate_errors = extract_valid_markdown_table(
                    normalized_repair, columns
                )
                if candidate_prediction is not None:
                    candidate_kind = "repaired"
        except BaseException as exc:
            repair_failure = {"stage": "repair", **_safe_exception(exc)}
        repair_cost = _counter_delta(
            _counter_snapshot(model, MODEL_COUNTERS), before_repair
        )
    terminal_elapsed = max(0.0, float(monotonic()) - started)
    emit("terminal", len(search_batches), len(evidence))

    common_model_cost = _add_costs(plan_cost, synthesis_cost)
    control_failures = [*common_failures]
    candidate_failures = [*common_failures]
    if repair_failure is not None:
        if control_needs_repair:
            control_failures.append(repair_failure)
        if candidate_needs_repair:
            candidate_failures.append(repair_failure)
    common_events = [
        {"stage": "plan", "effect": "model", "admitted": plan_admitted},
        {
            "stage": "retrieval",
            "effect": "search_queries",
            "requested": len(plan["queries"]),
            "admitted": query_count,
        },
        {
            "stage": "page_projection",
            "effect": "fetch_targets",
            "requested": len(leads),
            "admitted": fetch_count,
        },
        {
            "stage": "synthesis",
            "effect": "model",
            "admitted": synthesis_admitted,
        },
    ]
    control_events = [*common_events]
    candidate_events = [*common_events]
    if control_needs_repair:
        control_events.append(
            {"stage": "repair", "effect": "model", "admitted": repair_admitted}
        )
    if candidate_needs_repair:
        candidate_events.append(
            {"stage": "repair", "effect": "model", "admitted": repair_admitted}
        )
    common_admitted = int(plan_admitted) + int(synthesis_admitted)
    control = _arm_result(
        visible=visible,
        policy=policy,
        plan=plan,
        query_count=query_count,
        search_batch_count=len(search_batches),
        fetch_count=fetch_count,
        evidence_chars=len(evidence),
        prediction=control_prediction,
        completion_kind=control_kind,
        contract_errors=control_errors,
        failures=control_failures,
        elapsed=terminal_elapsed if control_needs_repair else synthesis_terminal,
        model_cost=_add_costs(
            common_model_cost,
            repair_cost if control_needs_repair else {},
        ),
        search_cost=search_cost,
        admitted_model_calls=common_admitted
        + int(control_needs_repair and repair_admitted),
        events=control_events,
    )
    candidate_parent = _arm_result(
        visible=visible,
        policy=policy,
        plan=plan,
        query_count=query_count,
        search_batch_count=len(search_batches),
        fetch_count=fetch_count,
        evidence_chars=len(evidence),
        prediction=candidate_prediction,
        completion_kind=candidate_kind,
        contract_errors=candidate_errors,
        failures=candidate_failures,
        elapsed=terminal_elapsed if candidate_needs_repair else synthesis_terminal,
        model_cost=_add_costs(
            common_model_cost,
            repair_cost if candidate_needs_repair else {},
        ),
        search_cost=search_cost,
        admitted_model_calls=common_admitted
        + int(candidate_needs_repair and repair_admitted),
        events=candidate_events,
    )
    candidate = _promote_result(candidate_parent, normalization_events)
    validate_v24259_result(candidate)
    actual_model = _counter_delta(
        _counter_snapshot(model, MODEL_COUNTERS), model_start
    )
    value = {
        "artifact_version": 1,
        "role": RESULT_ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": visible["opaque_id"],
        "control": control,
        "candidate": candidate,
        "shared_execution": {
            "plan_search_fetch_and_synthesis_shared": True,
            "repair_response_shared_when_both_arms_require_repair": True,
            "actual_model_cost": actual_model,
            "actual_search_cost": search_cost,
            "raw_synthesis_sha256": hashlib.sha256(
                raw_candidate.encode("utf-8")
            ).hexdigest(),
            "evidence_sha256": hashlib.sha256(evidence.encode("utf-8")).hexdigest(),
            "control_needed_repair": control_needs_repair,
            "candidate_needed_repair": candidate_needs_repair,
            "evaluator_feedback_available_or_used": False,
        },
        "label_blind": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
    }
    validate_paired_result(value)
    return value


def build_paired_fallback_result(
    task: Mapping[str, Any],
    *,
    limits: ScoreFirstLimits,
    completion_kind: str,
    failure_stage: str,
    failure_type: str,
    elapsed_seconds: float,
    last_progress: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    progress = dict(last_progress or {})
    translated = {
        "admitted_model_calls": progress.get("admitted_shared_model_calls", 0),
        "admitted_search_queries": progress.get("admitted_search_queries", 0),
        "admitted_fetch_targets": progress.get("admitted_fetch_targets", 0),
        "search_batch_count": progress.get("search_batch_count", 0),
        "projected_chars": progress.get("projected_chars", 0),
        "events": [],
        "model_cost": progress.get("model_cost") or {},
        "search_cost": progress.get("search_cost") or {},
    }
    control = build_score_first_fallback_result(
        visible,
        limits=limits,
        completion_kind=completion_kind,
        failure_stage=failure_stage,
        failure_type=failure_type,
        elapsed_seconds=elapsed_seconds,
        last_progress=translated,
    )
    candidate = build_v24259_fallback_result(
        visible,
        limits=limits,
        completion_kind=completion_kind,
        failure_stage=failure_stage,
        failure_type=failure_type,
        elapsed_seconds=elapsed_seconds,
        last_progress=translated,
    )
    model_cost = {
        name: int((progress.get("model_cost") or {}).get(name, 0) or 0)
        for name in MODEL_COUNTERS
    }
    search_cost = {
        name: int((progress.get("search_cost") or {}).get(name, 0) or 0)
        for name in SEARCH_COUNTERS
    }
    value = {
        "artifact_version": 1,
        "role": RESULT_ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": visible["opaque_id"],
        "control": control,
        "candidate": candidate,
        "shared_execution": {
            "plan_search_fetch_and_synthesis_shared": True,
            "repair_response_shared_when_both_arms_require_repair": True,
            "actual_model_cost": model_cost,
            "actual_search_cost": search_cost,
            "raw_synthesis_sha256": hashlib.sha256(b"").hexdigest(),
            "evidence_sha256": hashlib.sha256(b"").hexdigest(),
            "control_needed_repair": False,
            "candidate_needed_repair": False,
            "evaluator_feedback_available_or_used": False,
        },
        "label_blind": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
    }
    validate_paired_result(value)
    return value


def validate_paired_result(value: Mapping[str, Any]) -> None:
    if (
        set(value) != PAIR_KEYS
        or value.get("role") != RESULT_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("label_blind") is not True
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
    ):
        raise ValueError("V2.42.65 paired result identity drifted")
    control = value.get("control")
    candidate = value.get("candidate")
    if not isinstance(control, Mapping) or not isinstance(candidate, Mapping):
        raise ValueError("V2.42.65 paired arms are absent")
    _validate_arm_schema(control, candidate=False)
    _validate_arm_schema(candidate, candidate=True)
    if (
        value.get("opaque_id") != control.get("opaque_id")
        or value.get("opaque_id") != candidate.get("opaque_id")
        or control.get("columns") != candidate.get("columns")
        or control.get("plan") != candidate.get("plan")
        or control.get("evidence") != candidate.get("evidence")
    ):
        raise ValueError("V2.42.65 paired arm identity drifted")
    shared = value.get("shared_execution")
    if (
        not isinstance(shared, Mapping)
        or set(shared) != SHARED_KEYS
        or shared.get("plan_search_fetch_and_synthesis_shared") is not True
        or shared.get("repair_response_shared_when_both_arms_require_repair")
        is not True
        or shared.get("evaluator_feedback_available_or_used") is not False
        or not isinstance(shared.get("control_needed_repair"), bool)
        or not isinstance(shared.get("candidate_needed_repair"), bool)
        or any(not _is_sha256(shared.get(name)) for name in ("raw_synthesis_sha256", "evidence_sha256"))
    ):
        raise ValueError("V2.42.65 shared execution receipt drifted")
    actual_model = _validate_counter_map(
        shared.get("actual_model_cost"), keys=MODEL_COUNTERS, label="actual_model"
    )
    actual_search = _validate_counter_map(
        shared.get("actual_search_cost"), keys=SEARCH_COUNTERS, label="actual_search"
    )
    if dict(control["cost"]["search"]) != actual_search or dict(
        candidate["cost"]["search"]
    ) != actual_search:
        raise ValueError("V2.42.65 shared search-cost accounting drifted")
    actual_requests = actual_model["requests"]
    if not 0 <= actual_requests <= 3:
        raise ValueError("V2.42.65 shared model request count drifted")
    control_model = dict(control["cost"]["model"])
    candidate_model = dict(candidate["cost"]["model"])
    expected_actual_model = {
        key: max(int(control_model[key]), int(candidate_model[key]))
        for key in MODEL_COUNTERS
    }
    if actual_model != expected_actual_model:
        raise ValueError("V2.42.65 counterfactual model-cost accounting drifted")
    for arm_name, arm, needed in (
        ("control", control, shared["control_needed_repair"]),
        ("candidate", candidate, shared["candidate_needed_repair"]),
    ):
        repair_events = [
            event
            for event in arm["budget"]["events"]
            if event.get("stage") == "repair" and event.get("effect") == "model"
        ]
        if len(repair_events) != int(needed):
            raise ValueError(f"V2.42.65 {arm_name} repair accounting drifted")
