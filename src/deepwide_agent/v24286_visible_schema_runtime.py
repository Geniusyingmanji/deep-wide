"""Label-blind visible-schema and timing successor for two-wave retrieval.

This append-only candidate fixes two structural problems without reading any
benchmark-private field.  First, visible column declarations are parsed with
sentence, quote, and bracket awareness, so formatting prose and commas inside
parentheses do not become columns.  Second, the nested two-wave timing receipt
is reconciled with the outer telemetry, separating hosted search, real network
fetch, cache serving, controller/adapter overhead, and model stages.

The runtime input remains exactly ``{opaque_id, question}``.  Persisted
receipts contain counts and timings only; they never contain question text,
field names, queries, URLs, page text, candidates, predictions, or evaluator
metadata.  This module grants no benchmark/evaluator/leaderboard authority.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

from .clients import parse_json_object
from .v24257_score_first_runtime import (
    ScoreFirstLimits,
    _model_text,
    _normalize_column,
    validate_visible_task,
)
from .v24259_deterministic_table_normalizer import (
    _replace_text,
    normalize_candidate_table,
)
from .v24268_keyless_batched_runtime import run_v24268_task
from .v24272_two_wave_entropy_voc import TwoWavePolicy
from .v24273_two_wave_task_runtime import (
    DEFAULT_VISIBLE_COLUMN_PROXY,
    POLICY_ID as PARENT_POLICY_ID,
    RESULT_ROLE as PARENT_RESULT_ROLE,
    TwoWaveCachingSearchClient,
    validate_v24273_result,
)


POLICY_ID = "v24286_label_blind_visible_schema_timing_v1"
RESULT_ROLE = "v24286_visible_schema_timing_task_result"
RECEIPT_ROLE = "v24286_visible_schema_receipt"
TIMING_ROLE = "v24286_attributed_stage_timing"

_ANCHORS = (
    re.compile(
        r"(?:表格中的)?(?:列名|栏名)(?:依次)?(?:为|是)\s*[：:]\s*",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:the\s+)?column\s+(?:names?|headers?)[^:\n]{0,180}[：:]\s*",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:with|using|provide|include)\s+(?:the\s+)?following\s+columns?"
        r"(?:\s*\([^\n)]*\))?[^:\n]{0,80}[：:]\s*",
        re.IGNORECASE,
    ),
    re.compile(
        r"columns?\s*(?:are|is|should\s+be|must\s+be|as\s+follows)"
        r"[^:\n]{0,120}[：:]\s*",
        re.IGNORECASE,
    ),
)
_INSTRUCTION_CUE = re.compile(
    r"(?:[-*•]\s*)?(?:the\s+|if\s+|please\s+|do\s+not\s+|don't\s+|format\s+|"
    r"note\s*:|notes\s*:|for\s+|list\s+|use\s+|awards?\s+only\b|"
    r"不要|请直接|输出格式|时间类型|若|如果)",
    re.IGNORECASE,
)
_SEGMENT_INSTRUCTION_CUE = re.compile(
    r"(?:[-*•]\s*)?(?:if\s+|please\s+|do\s+not\s+|don't\s+|format\s+|"
    r"note\s*:|notes\s*:|instructions?\s*:|as\s+for\s+|each\s+row\b|"
    r"不要|请直接|输出格式|时间类型|若|如果|无法统计|输出采用)",
    re.IGNORECASE,
)


def _column_clause(raw: str) -> str:
    """Return the declaration prefix before top-level instruction prose."""

    text = str(raw).lstrip()
    stack: list[str] = []
    quote: str | None = None
    quote_start = -1
    closing = {"(": ")", "（": "）", "[": "]", "【": "】", "{": "}"}
    for index, char in enumerate(text):
        if quote is not None:
            if char == quote:
                quote = None
                quote_start = -1
            elif char == "\n" or (
                char in "。；;" and _INSTRUCTION_CUE.match(text[index + 1 :].lstrip())
            ):
                # A column clause should not consume paragraphs merely because
                # later formatting prose contains an unmatched ASCII quote.
                if quote_start >= 0:
                    return text[:quote_start].rstrip(" .。；;")
            continue
        if char in {'"', "“", "‘"}:
            quote = {"“": "”", "‘": "’"}.get(char, char)
            quote_start = index
            continue
        if char in closing:
            stack.append(closing[char])
            continue
        if stack and char == stack[-1]:
            stack.pop()
            continue
        if stack:
            continue
        if char == "\n":
            return text[:index].strip()
        if re.match(r"(?:注|注意|说明|instructions?)\s*[:：]", text[index:], re.IGNORECASE):
            return text[:index].rstrip(" ,，.。；;")
        if char in "。；;":
            return text[:index].strip()
        if char == ".":
            suffix = text[index + 1 :].lstrip()
            immediate = text[index + 1 :]
            if (
                _INSTRUCTION_CUE.match(suffix)
                or (suffix and (suffix[0].isupper() or re.match(r"[\u4e00-\u9fff]", suffix)))
                or not suffix
            ):
                return text[:index].strip()
    return text.strip().strip("。.;；")


def _top_level_split(raw: str) -> list[str]:
    values: list[str] = []
    current: list[str] = []
    stack: list[str] = []
    quote: str | None = None
    escaped = False
    closing = {"(": ")", "（": "）", "[": "]", "【": "】", "{": "}"}
    for char in str(raw):
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\":
            current.append(char)
            escaped = True
            continue
        if quote is not None:
            current.append(char)
            if char == quote:
                quote = None
            continue
        if char in {'"', "“", "‘"}:
            quote = {"“": "”", "‘": "’"}.get(char, char)
            current.append(char)
            continue
        if char in closing:
            stack.append(closing[char])
            current.append(char)
            continue
        if stack and char == stack[-1]:
            stack.pop()
            current.append(char)
            continue
        if char in {",", "，", "、", "|", "\n"} and not stack:
            values.append("".join(current))
            current = []
            continue
        current.append(char)
    values.append("".join(current))
    # Some Chinese prompts use spaces rather than punctuation between fields.
    # This is unambiguous only when every token contains CJK text; never apply
    # it to English multi-word field names.
    if len(values) == 1:
        tokens = str(raw).split()
        if 2 <= len(tokens) <= 20 and all(
            re.search(r"[\u4e00-\u9fff]", token) for token in tokens
        ):
            return tokens
    return values


def _clean_column(value: str) -> str:
    text = str(value).strip().replace("\u00a0", " ")
    # Only punctuated ordinals are decoration.  A bare leading digit may be a
    # meaningful field name, for example ``1/16赛-对手``.
    text = re.sub(r"^\s*(?:[-*•]+\s*|\(?\d+\)?[.、)]\s*)", "", text)
    text = re.sub(r"[\s`。.;；]+$", "", text)
    text = re.sub(r"^(?:and|以及|及)\s+", "", text, flags=re.IGNORECASE)
    return text.strip()


def extract_robust_visible_columns(question: str) -> list[str]:
    """Parse only an explicit, unambiguous visible column declaration."""

    visible = str(question or "")
    matches: list[tuple[int, int]] = []
    for pattern in _ANCHORS:
        matches.extend((match.start(), match.end()) for match in pattern.finditer(visible))
    for _, end in sorted(matches):
        clause = _column_clause(visible[end:])
        columns: list[str] = []
        for raw_value in _top_level_split(clause):
            value = _clean_column(raw_value)
            if not value:
                continue
            if _SEGMENT_INSTRUCTION_CUE.match(value):
                break
            columns.append(value)
        normalized = [_normalize_column(value) for value in columns]
        if (
            1 <= len(columns) <= 20
            and all(len(value) <= 80 for value in columns)
            and all(normalized)
            and len(set(normalized)) == len(normalized)
        ):
            return columns
    return []


def _schema_safe_question(question: str, columns: Sequence[str]) -> str:
    """Keep visible semantics while hiding declarations from the frozen parser."""

    text = re.sub(r"列名|栏名", "字段名称", str(question), flags=re.IGNORECASE)
    text = re.sub(r"\bcolumns?\b", "fields", text, flags=re.IGNORECASE)
    if not columns:
        return text
    exact = json.dumps(list(columns), ensure_ascii=False, separators=(",", ":"))
    return f"{text}\n\nExact output fields in order (parsed from the visible request): {exact}"


class VisibleSchemaModel:
    """Force visible fields into planning and canonicalize generated tables."""

    def __init__(self, inner: Any, *, columns: Sequence[str], question: str) -> None:
        self.inner = inner
        self.columns = list(columns)
        self.question = str(question)
        self.events: list[dict[str, Any]] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        if json_mode:
            provider_failed = False
            try:
                value = self.inner.complete(
                    system,
                    user,
                    max_output_tokens=max_output_tokens,
                    json_mode=True,
                )
            except Exception:
                # The visible schema is already known before the model effect.
                # Recover only the plan envelope; synthesis still observes the
                # provider failure through counters and may itself fail/fallback.
                value = _replace_text("", "{}")
                provider_failed = True
            parsed = True
            try:
                plan = parse_json_object(_model_text(value))
            except (TypeError, ValueError):
                plan = {}
                parsed = False
            plan["columns"] = list(self.columns)
            self.events.append(
                {
                    "stage": "plan",
                    "status": (
                        "forced_visible_schema_after_provider_failure"
                        if provider_failed
                        else "forced_visible_schema"
                    ),
                    "input_parse_valid": parsed and not provider_failed,
                    "column_count": len(self.columns),
                    "escaped_pipe_entities": 0,
                    "quote_entities": 0,
                }
            )
            text = json.dumps(plan, ensure_ascii=False, separators=(",", ":"))
            return _replace_text(value, text)

        value = self.inner.complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=False,
        )
        stage = "synthesis" if not any(e["stage"] == "synthesis" for e in self.events) else "repair"
        raw = _model_text(value)
        escaped_pipes = raw.count("\\|")
        safe_input = raw.replace("\\|", "&#124;")
        marker = "未知" if re.search(r"[\u4e00-\u9fff]", self.question) else "Unknown"
        normalized, diagnostics = normalize_candidate_table(
            safe_input,
            self.columns,
            unknown_marker=marker,
        )
        quotes = 0
        if normalized is not None:
            quotes = normalized.count('"')
            normalized = normalized.replace('"', "&quot;")
        self.events.append(
            {
                "stage": stage,
                "status": str(diagnostics["status"]),
                "input_parse_valid": normalized is not None,
                "column_count": len(self.columns),
                "escaped_pipe_entities": escaped_pipes,
                "quote_entities": quotes,
            }
        )
        return _replace_text(value, normalized) if normalized is not None else value


def _schema_receipt(
    *, columns: Sequence[str], applied: bool, events: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "status": "applied" if applied else "no_unambiguous_visible_schema",
        "column_count": len(columns),
        "question_rewrite_applied": bool(applied),
        "events": [dict(event) for event in events],
        "question_field_query_url_page_candidate_prediction_answer_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    validate_schema_receipt(value)
    return value


def validate_schema_receipt(value: Mapping[str, Any]) -> None:
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "status",
        "column_count",
        "question_rewrite_applied",
        "events",
        "question_field_query_url_page_candidate_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
    }
    if (
        set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != RECEIPT_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("status") not in {"applied", "no_unambiguous_visible_schema"}
        or value.get(
            "question_field_query_url_page_candidate_prediction_answer_opaque_id_or_credential_emitted"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
    ):
        raise ValueError("V2.42.86 visible-schema receipt drifted")
    count = value.get("column_count")
    if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= 20:
        raise ValueError("V2.42.86 visible-schema column count is invalid")
    applied = value.get("question_rewrite_applied")
    if not isinstance(applied, bool) or applied != (value["status"] == "applied"):
        raise ValueError("V2.42.86 visible-schema status is inconsistent")
    events = value.get("events")
    if not isinstance(events, list):
        raise ValueError("V2.42.86 visible-schema events are absent")
    event_keys = {
        "stage",
        "status",
        "input_parse_valid",
        "column_count",
        "escaped_pipe_entities",
        "quote_entities",
    }
    for event in events:
        if (
            not isinstance(event, Mapping)
            or set(event) != event_keys
            or event.get("stage") not in {"plan", "synthesis", "repair"}
            or not isinstance(event.get("status"), str)
            or not isinstance(event.get("input_parse_valid"), bool)
        ):
            raise ValueError("V2.42.86 visible-schema event drifted")
        for name in ("column_count", "escaped_pipe_entities", "quote_entities"):
            number = event.get(name)
            if isinstance(number, bool) or not isinstance(number, int) or number < 0:
                raise ValueError("V2.42.86 visible-schema event count is invalid")
        if event["column_count"] != count:
            raise ValueError("V2.42.86 visible-schema event binding drifted")
    if value["status"] == "applied" and (not events or events[0]["stage"] != "plan"):
        raise ValueError("V2.42.86 applied schema lacks a plan event")
    if not applied and (count != 0 or events):
        raise ValueError("V2.42.86 absent schema retained forced-schema effects")


def _nonnegative_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"V2.42.86 {label} is not numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"V2.42.86 {label} is invalid")
    return number


def _timing_receipt(parent: Mapping[str, Any]) -> dict[str, Any]:
    telemetry = parent["telemetry"]
    model_events = telemetry["model_events"]
    search_events = telemetry["search_events"]
    model_by_stage = {
        stage: round(
            sum(float(event["elapsed_seconds"]) for event in model_events if event["stage"] == stage),
            6,
        )
        for stage in ("plan", "synthesis", "repair")
    }
    retrieval_envelope = round(
        sum(float(event["elapsed_seconds"]) for event in search_events if event["stage"] == "search"),
        6,
    )
    cache_serve = round(
        sum(float(event["elapsed_seconds"]) for event in search_events if event["stage"] == "fetch"),
        6,
    )
    retrieval = parent["two_wave_retrieval"]
    if retrieval["status"] == "completed":
        total = retrieval["receipt"]["total"]
        provider_search = round(float(total["search_seconds"]), 6)
        network_fetch = round(float(total["fetch_seconds"]), 6)
        status = "complete"
    else:
        provider_search = 0.0
        network_fetch = 0.0
        status = "retrieval_failed_coarse_only"
    adapter = round(max(0.0, retrieval_envelope - provider_search - network_fetch), 6)
    instrumented = round(float(telemetry["instrumented_seconds"]), 6)
    task_wall = round(float(parent["budget"]["elapsed_seconds"]), 6)
    value = {
        "artifact_version": 1,
        "role": TIMING_ROLE,
        "status": status,
        "model_seconds": model_by_stage,
        "provider_search_seconds": provider_search,
        "network_fetch_seconds": network_fetch,
        "controller_and_adapter_seconds": adapter,
        "cache_serve_seconds": cache_serve,
        "retrieval_envelope_seconds": retrieval_envelope,
        "instrumented_seconds": instrumented,
        "task_wall_seconds": task_wall,
        "unattributed_runtime_seconds": round(max(0.0, task_wall - instrumented), 6),
        "timings_are_additive_not_parallel_work_sum": True,
        "question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    validate_timing_receipt(value)
    return value


def validate_timing_receipt(value: Mapping[str, Any]) -> None:
    expected = {
        "artifact_version",
        "role",
        "status",
        "model_seconds",
        "provider_search_seconds",
        "network_fetch_seconds",
        "controller_and_adapter_seconds",
        "cache_serve_seconds",
        "retrieval_envelope_seconds",
        "instrumented_seconds",
        "task_wall_seconds",
        "unattributed_runtime_seconds",
        "timings_are_additive_not_parallel_work_sum",
        "question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
    }
    if (
        set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != TIMING_ROLE
        or value.get("status") not in {"complete", "retrieval_failed_coarse_only"}
        or value.get("timings_are_additive_not_parallel_work_sum") is not True
        or value.get(
            "question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential_emitted"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
    ):
        raise ValueError("V2.42.86 attributed timing drifted")
    model = value.get("model_seconds")
    if not isinstance(model, Mapping) or set(model) != {"plan", "synthesis", "repair"}:
        raise ValueError("V2.42.86 model timing schema drifted")
    for name, number in model.items():
        _nonnegative_number(number, f"model {name}")
    numeric = expected - {
        "artifact_version",
        "role",
        "status",
        "model_seconds",
        "timings_are_additive_not_parallel_work_sum",
        "question_query_url_host_page_candidate_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
    }
    for name in numeric:
        _nonnegative_number(value.get(name), name)
    inner = float(value["provider_search_seconds"]) + float(value["network_fetch_seconds"])
    envelope = float(value["retrieval_envelope_seconds"])
    adapter = float(value["controller_and_adapter_seconds"])
    if inner > envelope + 1e-3:
        raise ValueError("V2.42.86 nested retrieval timing exceeds its envelope")
    if not math.isclose(inner + adapter, envelope, abs_tol=2e-6):
        raise ValueError("V2.42.86 retrieval attribution does not add up")
    event_sum = sum(float(number) for number in model.values()) + envelope + float(
        value["cache_serve_seconds"]
    )
    if not math.isclose(event_sum, float(value["instrumented_seconds"]), abs_tol=3e-6):
        raise ValueError("V2.42.86 instrumented timing does not add up")


def run_v24286_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits | None = None,
    policy: TwoWavePolicy | None = None,
    monotonic: Any = None,
    progress: Any = None,
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    chosen_limits = limits or ScoreFirstLimits(
        wall_seconds=180,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
    )
    chosen_limits.validate()
    if chosen_limits.search_queries > 4 or chosen_limits.fetch_targets > 10:
        raise ValueError("V2.42.86 two-wave retrieval envelope exceeded")
    columns = extract_robust_visible_columns(visible["question"])
    applied = bool(columns)
    forward_task = visible
    forward_model = model
    schema_model: VisibleSchemaModel | None = None
    if applied:
        forward_task = {
            "opaque_id": visible["opaque_id"],
            "question": _schema_safe_question(visible["question"], columns),
        }
        schema_model = VisibleSchemaModel(
            model,
            columns=columns,
            question=visible["question"],
        )
        forward_model = schema_model
    proxy = TwoWaveCachingSearchClient(
        search,
        required_column_count=len(columns) or DEFAULT_VISIBLE_COLUMN_PROXY,
        policy=policy,
        monotonic=monotonic,
    )
    kwargs: dict[str, Any] = {
        "model": forward_model,
        "search": proxy,
        "limits": chosen_limits,
        "progress": progress,
    }
    if monotonic is not None:
        kwargs["monotonic"] = monotonic
    parent68 = run_v24268_task(forward_task, **kwargs)
    if proxy.failure_type == "KeyboardInterrupt":
        raise KeyboardInterrupt
    if proxy.failure_type == "SystemExit":
        raise SystemExit
    if proxy.failure_type == "GeneratorExit":
        raise GeneratorExit
    parent = dict(parent68)
    parent["role"] = PARENT_RESULT_ROLE
    parent["policy_id"] = PARENT_POLICY_ID
    parent["two_wave_retrieval"] = proxy.receipt()
    validate_v24273_result(parent)
    result = dict(parent)
    result["role"] = RESULT_ROLE
    result["policy_id"] = POLICY_ID
    result["visible_schema"] = _schema_receipt(
        columns=columns,
        applied=applied,
        events=schema_model.events if schema_model is not None else [],
    )
    result["attributed_timing"] = _timing_receipt(parent)
    result["prediction_sha256"] = hashlib.sha256(
        str(result["prediction"]).encode("utf-8")
    ).hexdigest()
    validate_v24286_result(result)
    return result


def validate_v24286_result(value: Mapping[str, Any]) -> None:
    if value.get("role") != RESULT_ROLE or value.get("policy_id") != POLICY_ID:
        raise ValueError("V2.42.86 result identity drifted")
    schema = value.get("visible_schema")
    timing = value.get("attributed_timing")
    if not isinstance(schema, Mapping) or not isinstance(timing, Mapping):
        raise ValueError("V2.42.86 receipts are absent")
    validate_schema_receipt(schema)
    validate_timing_receipt(timing)
    parent = copy.deepcopy(dict(value))
    parent.pop("visible_schema", None)
    parent.pop("attributed_timing", None)
    parent["role"] = PARENT_RESULT_ROLE
    parent["policy_id"] = PARENT_POLICY_ID
    validate_v24273_result(parent)
    if schema["status"] == "applied" and schema["column_count"] != len(parent["columns"]):
        raise ValueError("V2.42.86 visible schema did not reach the parent result")
    if not math.isclose(
        float(timing["task_wall_seconds"]),
        float(parent["budget"]["elapsed_seconds"]),
        abs_tol=1e-6,
    ):
        raise ValueError("V2.42.86 task timing is not bound to the parent")


__all__ = [
    "POLICY_ID",
    "RESULT_ROLE",
    "VisibleSchemaModel",
    "extract_robust_visible_columns",
    "run_v24286_task",
    "validate_schema_receipt",
    "validate_timing_receipt",
    "validate_v24286_result",
]
