"""Zero-additional-effect integration of V2.47.54 after a frozen baseline.

One visible ``{opaque_id, question}`` task executes the ordinary bounded
``plan -> search -> fetch -> baseline synthesis`` prefix.  The candidate then
replays only those successfully fetched pages that were already projected into
the baseline synthesis evidence.  It adds no model, query, search, fetch, or
token effect.

The pure V2.47.54 adapter binds exact structured records to exact first-column
identities and exact field labels in the frozen baseline.  V2.47.43 therefore
still requires two registrably-independent ordinary sources with the same
value, abstains on conflicts, and changes only Unknown cells.  Entropy and
prediction change receive no task credit.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .clients import parse_json_object
from .v24257_score_first_runtime import (
    PLAN_SYSTEM,
    PLAN_USER,
    SYNTHESIS_SYSTEM,
    SYNTHESIS_USER,
    ScoreFirstLimits,
    _counter_delta,
    _counter_snapshot,
    _lead_requests,
    _model_text,
    _validated_plan,
    build_best_effort_prediction,
    extract_valid_markdown_table,
    validate_visible_task,
)
from .v24259_deterministic_table_normalizer import normalize_candidate_table
from .v24269_task_union_discovery import TaskUnionDiscoverySearchClient
from .v24286_visible_schema_runtime import extract_robust_visible_columns
from .v24308_child_exit_observability import coarse_exception_type
from .v24325_shared_prefix_revision_runtime import (
    _complete_query_vector,
    _format_evidence,
    _page_vector,
)
from .v24743_generic_record_binding import _baseline_matrix
from .v24754_generic_structured_page_adapter import (
    build_generic_structured_page_binding,
    validate_receipt as validate_adapter_receipt,
    validate_result as validate_adapter_result,
)


POLICY_ID = "v24756_zero_effect_generic_structured_integration_v1"
ROLE = "v24756_zero_effect_structured_task_result"
RECEIPT_ROLE = "v24756_zero_effect_structured_content_free_receipt"
ARMS = ("baseline", "generic_structured")
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
UNKNOWN = frozenset(
    {"", "-", "—", "?", "n/a", "na", "none", "null", "unknown", "未知", "不详"}
)
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "opaque_id",
        "columns",
        "predictions",
        "prediction_sha256",
        "adapter_result",
        "private_synthesis_evidence_pages",
        "private_replay_pages",
        "receipt",
        "elapsed_seconds",
        "private_visible_task_or_page_content_present",
        "private_content_emitted_to_public_aggregate",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "result_sha256",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "shared_plan_search_fetch_baseline_prefix",
        "baseline_frozen_before_adapter",
        "model_stage_vector",
        "admitted_search_queries",
        "admitted_fetch_targets",
        "search_batch_count",
        "synthesis_evidence_page_count",
        "adapter_replay_page_count",
        "adapter_pages_are_subset_of_synthesis_evidence",
        "model_cost_before_adapter",
        "model_cost_after_adapter",
        "search_cost_before_adapter",
        "search_cost_after_adapter",
        "adapter_additional_model_requests",
        "adapter_additional_model_attempts",
        "adapter_additional_model_tokens",
        "adapter_additional_search_calls",
        "adapter_additional_fetch_calls",
        "adapter_effect_equivalence_passed",
        "baseline_table",
        "candidate_table",
        "adapter_content_free_receipt",
        "recoverable_failure_count",
        "recoverable_failure_type_counts",
        "candidate_changes_only_unknown_cells",
        "ordinary_records_require_two_independent_sources",
        "candidate_additional_query_fetch_or_model_effect",
        "entropy_or_prediction_change_used_for_positive_task_credit",
        "question_prompt_query_url_page_prediction_answer_value_or_opaque_id_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)


class _Budget:
    def __init__(
        self,
        limits: ScoreFirstLimits,
        started: float,
        monotonic: Callable[[], float],
    ) -> None:
        self.limits = limits
        self.started = float(started)
        self.monotonic = monotonic
        self.model_stages: list[str] = []
        self.search_queries = 0
        self.fetch_targets = 0

    def remaining(self) -> float:
        return max(
            0.0,
            float(self.limits.wall_seconds)
            - (float(self.monotonic()) - self.started),
        )

    def admit_model(self, stage: str) -> bool:
        if self.remaining() <= 0 or len(self.model_stages) >= self.limits.model_calls:
            return False
        self.model_stages.append(stage)
        return True

    def admit_search(self, requested: int) -> int:
        remaining = max(0, self.limits.search_queries - self.search_queries)
        amount = min(max(0, int(requested)), remaining) if self.remaining() > 0 else 0
        self.search_queries += amount
        return amount

    def admit_fetch(self, requested: int) -> int:
        remaining = max(0, self.limits.fetch_targets - self.fetch_targets)
        amount = min(max(0, int(requested)), remaining) if self.remaining() > 0 else 0
        self.fetch_targets += amount
        return amount


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _canonical(raw: str, columns: Sequence[str], question: str) -> str | None:
    table, _errors = extract_valid_markdown_table(raw, columns)
    if table is not None:
        return table
    marker = "未知" if re.search(r"[\u4e00-\u9fff]", question) else "Unknown"
    normalized, _ = normalize_candidate_table(
        raw, list(columns), unknown_marker=marker
    )
    if normalized is None:
        return None
    table, _errors = extract_valid_markdown_table(normalized, columns)
    return table


def _table_stats(table: str) -> dict[str, Any]:
    columns, rows = _baseline_matrix(table)
    value_count = len(rows) * max(0, len(columns) - 1)
    unknown = sum(
        str(value).strip().casefold() in UNKNOWN
        for row in rows
        for value in row[1:]
    )
    return {
        "row_count": len(rows),
        "column_count": len(columns),
        "value_cell_count": value_count,
        "unknown_value_cell_count": unknown,
        "completion_ratio": (
            round((value_count - unknown) / value_count, 12)
            if value_count
            else 0.0
        ),
    }


TABLE_STAT_KEYS = frozenset(
    {
        "row_count",
        "column_count",
        "value_cell_count",
        "unknown_value_cell_count",
        "completion_ratio",
    }
)


def _validate_table_stats(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != TABLE_STAT_KEYS:
        raise ValueError("V2.47.56 table statistics schema drifted")
    copied = dict(value)
    for name in TABLE_STAT_KEYS - {"completion_ratio"}:
        number = copied.get(name)
        if isinstance(number, bool) or not isinstance(number, int) or number < 0:
            raise ValueError("V2.47.56 table statistics count drifted")
    ratio = copied.get("completion_ratio")
    if (
        isinstance(ratio, bool)
        or not isinstance(ratio, (int, float))
        or not 0.0 <= float(ratio) <= 1.0
        or copied["unknown_value_cell_count"] > copied["value_cell_count"]
        or copied["value_cell_count"]
        != copied["row_count"] * max(0, copied["column_count"] - 1)
        or float(ratio)
        != (
            round(
                (
                    copied["value_cell_count"]
                    - copied["unknown_value_cell_count"]
                )
                / copied["value_cell_count"],
                12,
            )
            if copied["value_cell_count"]
            else 0.0
        )
    ):
        raise ValueError("V2.47.56 table statistics invariant drifted")
    return copied


def _adapter_pages(
    batches: object, *, page_chars: int
) -> list[dict[str, Any]]:
    """Use only successful fetched text and its redirect-resolved final URL."""

    if not isinstance(batches, Sequence) or isinstance(batches, (str, bytes)):
        return []
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for batch in batches:
        if not isinstance(batch, Mapping):
            continue
        results = batch.get("results")
        if not isinstance(results, Sequence) or isinstance(results, (str, bytes)):
            continue
        for result in results:
            if not isinstance(result, Mapping) or result.get("fetch_status") != "ok":
                continue
            final_url = str(result.get("url", "")).strip()
            content = str(result.get("raw_content") or "").replace("\x00", "").strip()
            if not final_url or not content or final_url in seen:
                continue
            page = {
                "final_url": final_url,
                "content": content[:page_chars],
                "fetch_integrity": True,
            }
            # Validation happens inside the adapter.  Drop malformed pages
            # rather than converting requested URLs or snippets into evidence.
            try:
                build_generic_structured_page_binding(
                    "```markdown\n| Identity | Value |\n| --- | --- |\n"
                    "| Probe | Unknown |\n```",
                    [page],
                )
            except ValueError:
                continue
            output.append(page)
            seen.add(final_url)
    return output


def _page_content_multiset(
    pages: Sequence[Mapping[str, Any]], *, adapter: bool
) -> Counter[str]:
    output: Counter[str] = Counter()
    for page in pages:
        content = str(page.get("content", ""))
        if not content:
            continue
        if adapter and set(page) != {"final_url", "content", "fetch_integrity"}:
            raise ValueError("V2.47.56 adapter replay page schema drifted")
        output[hashlib.sha256(content.encode("utf-8")).hexdigest()] += 1
    return output


def _pages_are_evidence_subset(
    evidence_pages: Sequence[Mapping[str, Any]],
    adapter_pages: Sequence[Mapping[str, Any]],
) -> bool:
    evidence = _page_content_multiset(evidence_pages, adapter=False)
    replay = _page_content_multiset(adapter_pages, adapter=True)
    return all(replay[key] <= evidence[key] for key in replay)


def _receipt(
    *,
    budget: _Budget,
    evidence_pages: Sequence[Mapping[str, Any]],
    adapter_pages: Sequence[Mapping[str, Any]],
    model_before: Mapping[str, int],
    model_after: Mapping[str, int],
    search_before: Mapping[str, int],
    search_after: Mapping[str, int],
    baseline_stats: Mapping[str, Any],
    candidate_stats: Mapping[str, Any],
    adapter_result: Mapping[str, Any],
    failures: Sequence[Mapping[str, str]],
    search_batch_count: int,
) -> dict[str, Any]:
    model_delta = {
        name: int(model_after[name]) - int(model_before[name]) for name in MODEL_COUNTERS
    }
    search_delta = {
        name: int(search_after[name]) - int(search_before[name])
        for name in SEARCH_COUNTERS
    }
    effect_equivalent = not any(model_delta.values()) and not any(
        search_delta.values()
    )
    adapter_receipt = adapter_result["receipt"]
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "shared_plan_search_fetch_baseline_prefix": True,
        "baseline_frozen_before_adapter": True,
        "model_stage_vector": list(budget.model_stages),
        "admitted_search_queries": budget.search_queries,
        "admitted_fetch_targets": budget.fetch_targets,
        "search_batch_count": int(search_batch_count),
        "synthesis_evidence_page_count": len(evidence_pages),
        "adapter_replay_page_count": len(adapter_pages),
        "adapter_pages_are_subset_of_synthesis_evidence": _pages_are_evidence_subset(
            evidence_pages, adapter_pages
        ),
        "model_cost_before_adapter": dict(model_before),
        "model_cost_after_adapter": dict(model_after),
        "search_cost_before_adapter": dict(search_before),
        "search_cost_after_adapter": dict(search_after),
        "adapter_additional_model_requests": model_delta["requests"],
        "adapter_additional_model_attempts": model_delta["attempts"],
        "adapter_additional_model_tokens": model_delta["total_tokens"],
        "adapter_additional_search_calls": search_delta["calls"],
        "adapter_additional_fetch_calls": search_delta["fetch_calls"],
        "adapter_effect_equivalence_passed": effect_equivalent,
        "baseline_table": dict(baseline_stats),
        "candidate_table": dict(candidate_stats),
        "adapter_content_free_receipt": copy.deepcopy(adapter_receipt),
        "recoverable_failure_count": len(failures),
        "recoverable_failure_type_counts": {
            name: sum(item.get("type") == name for item in failures)
            for name in sorted({str(item.get("type")) for item in failures})
        },
        "candidate_changes_only_unknown_cells": adapter_receipt[
            "binding_receipt"
        ]["only_unknown_cells_mutated"],
        "ordinary_records_require_two_independent_sources": adapter_receipt[
            "binding_receipt"
        ]["ordinary_records_require_two_independent_sources"],
        "candidate_additional_query_fetch_or_model_effect": not effect_equivalent,
        "entropy_or_prediction_change_used_for_positive_task_credit": False,
        "question_prompt_query_url_page_prediction_answer_value_or_opaque_id_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    adapter_receipt = copied.get("adapter_content_free_receipt")
    model_before = copied.get("model_cost_before_adapter")
    model_after = copied.get("model_cost_after_adapter")
    search_before = copied.get("search_cost_before_adapter")
    search_after = copied.get("search_cost_after_adapter")
    baseline_stats = copied.get("baseline_table")
    candidate_stats = copied.get("candidate_table")
    failures = copied.get("recoverable_failure_type_counts")
    count_names = (
        "admitted_search_queries",
        "admitted_fetch_targets",
        "search_batch_count",
        "synthesis_evidence_page_count",
        "adapter_replay_page_count",
        "adapter_additional_model_requests",
        "adapter_additional_model_attempts",
        "adapter_additional_model_tokens",
        "adapter_additional_search_calls",
        "adapter_additional_fetch_calls",
        "recoverable_failure_count",
    )
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("shared_plan_search_fetch_baseline_prefix") is not True
        or copied.get("baseline_frozen_before_adapter") is not True
        or copied.get("model_stage_vector") != ["shared_plan", "baseline_synthesis"]
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in count_names
        )
        or copied.get("admitted_search_queries") not in range(5)
        or copied.get("admitted_fetch_targets") not in range(11)
        or copied.get("synthesis_evidence_page_count")
        > copied.get("admitted_fetch_targets")
        or copied.get("adapter_replay_page_count")
        > copied.get("synthesis_evidence_page_count")
        or copied.get("adapter_pages_are_subset_of_synthesis_evidence") is not True
        or not all(
            isinstance(item, Mapping)
            for item in (model_before, model_after, search_before, search_after)
        )
        or set(model_before) != set(MODEL_COUNTERS)
        or set(model_after) != set(MODEL_COUNTERS)
        or set(search_before) != set(SEARCH_COUNTERS)
        or set(search_after) != set(SEARCH_COUNTERS)
        or any(
            isinstance(number, bool) or not isinstance(number, int) or number < 0
            for item in (model_before, model_after, search_before, search_after)
            for number in item.values()
        )
        or dict(model_before) != dict(model_after)
        or dict(search_before) != dict(search_after)
        or copied.get("adapter_additional_model_requests") != 0
        or copied.get("adapter_additional_model_attempts") != 0
        or copied.get("adapter_additional_model_tokens") != 0
        or copied.get("adapter_additional_search_calls") != 0
        or copied.get("adapter_additional_fetch_calls") != 0
        or copied.get("adapter_effect_equivalence_passed") is not True
        or not isinstance(adapter_receipt, Mapping)
        or validate_adapter_receipt(adapter_receipt) != dict(adapter_receipt)
        or _validate_table_stats(baseline_stats) != dict(baseline_stats)
        or _validate_table_stats(candidate_stats) != dict(candidate_stats)
        or baseline_stats.get("row_count") != candidate_stats.get("row_count")
        or baseline_stats.get("column_count")
        != candidate_stats.get("column_count")
        or baseline_stats.get("value_cell_count")
        != candidate_stats.get("value_cell_count")
        or baseline_stats.get("unknown_value_cell_count")
        - candidate_stats.get("unknown_value_cell_count")
        != adapter_receipt.get("binding_receipt", {}).get("changed_cell_count")
        or not isinstance(failures, Mapping)
        or any(
            not isinstance(name, str)
            or not name
            or isinstance(number, bool)
            or not isinstance(number, int)
            or number <= 0
            for name, number in failures.items()
        )
        or sum(failures.values()) != copied.get("recoverable_failure_count")
        or copied.get("candidate_changes_only_unknown_cells") is not True
        or copied.get("ordinary_records_require_two_independent_sources") is not True
        or copied.get("candidate_additional_query_fetch_or_model_effect") is not False
        or copied.get("entropy_or_prediction_change_used_for_positive_task_credit")
        is not False
        or copied.get(
            "question_prompt_query_url_page_prediction_answer_value_or_opaque_id_emitted"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.56 integration receipt drifted")
    return copied


def run_v24756_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    limits.validate()
    if (
        limits.model_calls != 2
        or limits.search_queries != 4
        or limits.fetch_targets != 10
        or limits.evidence_chars < limits.fetch_targets * limits.page_chars
    ):
        raise ValueError("V2.47.56 fixed effect envelope drifted")
    started = float(monotonic())
    budget = _Budget(limits, started, monotonic)
    model_origin = _counter_snapshot(model, MODEL_COUNTERS)
    search_origin = _counter_snapshot(search, SEARCH_COUNTERS)
    failures: list[dict[str, str]] = []

    def recovered(stage: str, error: BaseException) -> None:
        failures.append({"stage": stage, "type": coarse_exception_type(error)})

    if not budget.admit_model("shared_plan"):
        raise RuntimeError("V2.47.56 shared plan was not admitted")
    try:
        response = model.complete(
            PLAN_SYSTEM,
            PLAN_USER.format(
                question=visible["question"], query_limit=limits.search_queries
            ),
            max_output_tokens=limits.plan_output_tokens,
            json_mode=True,
        )
        plan = _validated_plan(
            parse_json_object(_model_text(response)), visible["question"], limits
        )
    except Exception as error:
        recovered("shared_plan", error)
        plan = _validated_plan({}, visible["question"], limits)
    columns = extract_robust_visible_columns(visible["question"]) or list(
        plan["columns"]
    )
    queries = _complete_query_vector(
        visible["question"], plan["queries"], limits.search_queries
    )
    query_count = budget.admit_search(len(queries))
    union = TaskUnionDiscoverySearchClient(search)
    try:
        batches = (
            union.search_many(
                queries[:query_count],
                max_results=limits.search_results_per_query,
                search_depth="advanced",
                include_raw_content=False,
            )
            if query_count
            else []
        )
    except Exception as error:
        recovered("shared_search", error)
        batches = []
    leads = _lead_requests(batches, limits.fetch_targets)
    fetch_count = budget.admit_fetch(len(leads))
    try:
        pages_raw = union.fetch_urls(leads[:fetch_count]) if fetch_count else []
    except Exception as error:
        recovered("shared_fetch", error)
        pages_raw = []
    evidence_pages = _page_vector(
        pages_raw, prefix="E", page_chars=limits.page_chars
    )
    evidence = _format_evidence(
        evidence_pages, character_cap=limits.evidence_chars
    )
    if not budget.admit_model("baseline_synthesis"):
        baseline = build_best_effort_prediction(visible["question"], columns)
    else:
        try:
            response = model.complete(
                SYNTHESIS_SYSTEM,
                SYNTHESIS_USER.format(
                    question=visible["question"],
                    columns=json.dumps(columns, ensure_ascii=False),
                    evidence=evidence,
                ),
                max_output_tokens=limits.synthesis_output_tokens,
                json_mode=False,
            )
            baseline = _canonical(
                _model_text(response), columns, visible["question"]
            ) or build_best_effort_prediction(visible["question"], columns)
        except Exception as error:
            recovered("baseline_synthesis", error)
            baseline = build_best_effort_prediction(visible["question"], columns)

    replay_pages = _adapter_pages(pages_raw, page_chars=limits.page_chars)
    model_before_adapter = _counter_snapshot(model, MODEL_COUNTERS)
    search_before_adapter = _counter_snapshot(search, SEARCH_COUNTERS)
    adapter_result = build_generic_structured_page_binding(baseline, replay_pages)
    model_after_adapter = _counter_snapshot(model, MODEL_COUNTERS)
    search_after_adapter = _counter_snapshot(search, SEARCH_COUNTERS)
    candidate = adapter_result["candidate"]
    baseline_stats = _table_stats(baseline)
    candidate_stats = _table_stats(candidate)
    receipt = _receipt(
        budget=budget,
        evidence_pages=evidence_pages,
        adapter_pages=replay_pages,
        model_before=model_before_adapter,
        model_after=model_after_adapter,
        search_before=search_before_adapter,
        search_after=search_after_adapter,
        baseline_stats=baseline_stats,
        candidate_stats=candidate_stats,
        adapter_result=adapter_result,
        failures=failures,
        search_batch_count=len(batches),
    )
    # Overall costs are not persisted in the public receipt, but this verifies
    # the parent prefix stayed inside the actual observed client counters.
    _counter_delta(_counter_snapshot(model, MODEL_COUNTERS), model_origin)
    _counter_delta(_counter_snapshot(search, SEARCH_COUNTERS), search_origin)
    predictions = {"baseline": baseline, "generic_structured": candidate}
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": visible["opaque_id"],
        "columns": list(columns),
        "predictions": predictions,
        "prediction_sha256": {
            arm: hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        },
        "adapter_result": adapter_result,
        "private_synthesis_evidence_pages": copy.deepcopy(evidence_pages),
        "private_replay_pages": replay_pages,
        "receipt": receipt,
        "elapsed_seconds": round(max(0.0, float(monotonic()) - started), 6),
        "private_visible_task_or_page_content_present": True,
        "private_content_emitted_to_public_aggregate": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    value["result_sha256"] = payload_sha256(value)
    return validate_result(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_sha256", None)
    predictions = copied.get("predictions")
    hashes = copied.get("prediction_sha256")
    adapter_result = copied.get("adapter_result")
    evidence_pages = copied.get("private_synthesis_evidence_pages")
    pages = copied.get("private_replay_pages")
    receipt = copied.get("receipt")
    columns = copied.get("columns")
    if (
        set(copied) != RESULT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(predictions, Mapping)
        or set(predictions) != set(ARMS)
        or not isinstance(hashes, Mapping)
        or set(hashes) != set(ARMS)
        or any(not isinstance(predictions[arm], str) for arm in ARMS)
        or any(
            hashes[arm] != hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        )
        or not isinstance(columns, list)
        or not columns
        or _baseline_matrix(predictions["baseline"])[0] != columns
        or _baseline_matrix(predictions["generic_structured"])[0] != columns
        or not isinstance(adapter_result, Mapping)
        or not isinstance(evidence_pages, list)
        or not isinstance(pages, list)
        or not _pages_are_evidence_subset(evidence_pages, pages)
        or receipt.get("synthesis_evidence_page_count") != len(evidence_pages)
        or receipt.get("adapter_replay_page_count") != len(pages)
        or adapter_result.get("candidate") != predictions["generic_structured"]
        or adapter_result.get("baseline_sha256")
        != hashlib.sha256(predictions["baseline"].encode()).hexdigest()
        or validate_adapter_result(
            adapter_result,
            baseline=predictions["baseline"],
            pages=pages,
        )
        != dict(adapter_result)
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt.get("adapter_content_free_receipt")
        != adapter_result.get("receipt")
        or receipt.get("baseline_table") != _table_stats(predictions["baseline"])
        or receipt.get("candidate_table")
        != _table_stats(predictions["generic_structured"])
        or copied.get("private_visible_task_or_page_content_present") is not True
        or copied.get("private_content_emitted_to_public_aggregate") is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.56 task result drifted")
    validate_visible_task(
        {"opaque_id": str(copied.get("opaque_id", "")), "question": "private"}
    )
    return copied


__all__ = [
    "ARMS",
    "POLICY_ID",
    "ROLE",
    "run_v24756_task",
    "validate_receipt",
    "validate_result",
]
