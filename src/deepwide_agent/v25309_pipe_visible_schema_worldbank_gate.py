"""Pipe-delimited visible-schema adapter for the frozen World Bank gate.

V2.52.95 inherited the general V2.42.86 visible-schema parser.  The frozen
World Bank questions declare columns with exact `` | `` delimiters, while
three public indicator labels contain top-level commas and exceed 80
characters.  The general parser therefore split five visible columns into
nine and made the parent synthesis structurally unreachable.

This append-only adapter changes only that visible-question parser inside an
isolated copy of the already-frozen parent call chain.  It does not alter the
question, pages, queries, search/fetch effects, model budget, candidate gate,
or result/receipt formats.  It has no filesystem, network, evaluator, label,
gold, or historical-result capability.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from typing import Any, Callable

from . import v24257_score_first_runtime as score_runtime
from . import v24259_deterministic_table_normalizer as normalizer_runtime
from . import v24267_total_fallback as total_runtime
from . import v24268_keyless_batched_runtime as batched_runtime
from . import v24318_deadline_conservation_runtime as conservation_runtime
from . import v24319_runner_integration as runner_integration
from . import v24630_exact220_task_integration as task_integration
from . import v25295_worldbank_monotone_fill_gate as parent
from .v24257_score_first_runtime import _normalize_column


POLICY_ID = "v25309_pipe_delimited_visible_schema_worldbank_gate_v1"
VISIBLE_PREFIX = "Column names: "
VISIBLE_SUFFIX = ". Include exactly these entity-code rows in this order: "
SAFE_SCHEMA_PREFIX = "Exact output fields in order (parsed from the visible request): "


def extract_pipe_delimited_visible_columns(question: str) -> list[str]:
    """Parse one explicit visible `` | `` declaration without semantic labels."""

    visible = str(question or "")
    if visible.count(VISIBLE_PREFIX) != 1 or visible.count(VISIBLE_SUFFIX) != 1:
        return []
    prefix_index = visible.index(VISIBLE_PREFIX) + len(VISIBLE_PREFIX)
    suffix_index = visible.index(VISIBLE_SUFFIX, prefix_index)
    if suffix_index <= prefix_index:
        return []
    clause = visible[prefix_index:suffix_index]
    if not clause or "\n" in clause or "\r" in clause or "`" in clause:
        return []
    columns = [value.strip() for value in clause.split(" | ")]
    normalized = [_normalize_column(value) for value in columns]
    if (
        len(columns) != parent.TARGET_COUNT + 1
        or any(not value or len(value) > 160 or "|" in value for value in columns)
        or any(not value for value in normalized)
        or len(set(normalized)) != len(normalized)
    ):
        return []
    return columns


def _safe_question_columns(question: str) -> list[str]:
    """Decode only the exact visible-schema projection made by V2.42.86."""

    lines = str(question or "").splitlines()
    matches = [line for line in lines if line.startswith(SAFE_SCHEMA_PREFIX)]
    if len(matches) != 1:
        return []
    raw = matches[0][len(SAFE_SCHEMA_PREFIX) :]
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(value, list):
        return []
    columns = [str(item).strip() for item in value if isinstance(item, str)]
    normalized = [_normalize_column(item) for item in columns]
    if (
        len(columns) != len(value)
        or len(columns) != parent.TARGET_COUNT + 1
        or any(not item or len(item) > 160 or "|" in item for item in columns)
        or any(not item for item in normalized)
        or len(set(normalized)) != len(normalized)
    ):
        return []
    return columns


def _validated_pipe_plan(value: Mapping[str, Any], question: str, limits: Any) -> dict[str, Any]:
    """Accept the long schema only when it exactly matches the safe projection."""

    plan = score_runtime._validated_plan(value, question, limits)
    declared = _safe_question_columns(question)
    raw = value.get("columns")
    proposed = (
        [score_runtime._normalize_text(item) for item in raw]
        if isinstance(raw, list) and all(isinstance(item, str) for item in raw)
        else []
    )
    if declared and proposed == declared:
        plan["columns"] = declared
    return plan


_PIPE_RUN_SCORE_FIRST_TASK = parent._isolated_function(
    score_runtime.run_score_first_task,
    _validated_plan=_validated_pipe_plan,
)
_PIPE_RUN_V24259_TASK = parent._isolated_function(
    normalizer_runtime.run_v24259_task,
    run_score_first_task=_PIPE_RUN_SCORE_FIRST_TASK,
)
_PIPE_RUN_TOTAL_TASK = parent._isolated_function(
    total_runtime.run_total_task,
    run_v24259_task=_PIPE_RUN_V24259_TASK,
)
_PIPE_RUN_V24268_TASK = parent._isolated_function(
    batched_runtime.run_v24268_task,
    run_total_task=_PIPE_RUN_TOTAL_TASK,
)


_PIPE_RUN_PARENT = parent._isolated_function(
    conservation_runtime._run_parent,
    TwoWaveCachingSearchClient=parent.MonotoneFillCachingSearchClient,
    extract_robust_visible_columns=extract_pipe_delimited_visible_columns,
    run_v24268_task=_PIPE_RUN_V24268_TASK,
)
_PIPE_RUN_V24318_TASK = parent._isolated_function(
    conservation_runtime.run_v24318_task,
    _run_parent=_PIPE_RUN_PARENT,
)
_PIPE_RUN_V24319_TASK = parent._isolated_function(
    runner_integration.run_v24319_task,
    run_v24318_task=_PIPE_RUN_V24318_TASK,
)
_PIPE_PARENT_RUN_TASK = parent._isolated_function(
    task_integration.run_v24630_task,
    run_v24319_task=_PIPE_RUN_V24319_TASK,
)


def validate_isolation() -> None:
    parent.validate_isolation()
    if (
        conservation_runtime._run_parent is _PIPE_RUN_PARENT
        or runner_integration.run_v24319_task is _PIPE_RUN_V24319_TASK
        or task_integration.run_v24630_task is _PIPE_PARENT_RUN_TASK
        or _PIPE_RUN_PARENT.__globals__["extract_robust_visible_columns"]
        is not extract_pipe_delimited_visible_columns
        or _PIPE_RUN_PARENT.__globals__["TwoWaveCachingSearchClient"]
        is not parent.MonotoneFillCachingSearchClient
        or _PIPE_RUN_PARENT.__globals__["run_v24268_task"]
        is not _PIPE_RUN_V24268_TASK
        or _PIPE_RUN_V24268_TASK.__globals__["run_total_task"]
        is not _PIPE_RUN_TOTAL_TASK
        or _PIPE_RUN_TOTAL_TASK.__globals__["run_v24259_task"]
        is not _PIPE_RUN_V24259_TASK
        or _PIPE_RUN_V24259_TASK.__globals__["run_score_first_task"]
        is not _PIPE_RUN_SCORE_FIRST_TASK
        or _PIPE_RUN_SCORE_FIRST_TASK.__globals__["_validated_plan"]
        is not _validated_pipe_plan
        or _PIPE_RUN_V24318_TASK.__globals__["_run_parent"] is not _PIPE_RUN_PARENT
        or _PIPE_RUN_V24319_TASK.__globals__["run_v24318_task"]
        is not _PIPE_RUN_V24318_TASK
        or _PIPE_PARENT_RUN_TASK.__globals__["run_v24319_task"]
        is not _PIPE_RUN_V24319_TASK
    ):
        raise RuntimeError("V2.53.09 pipe-schema isolated integration drifted")


_RUN_PAIRED_TASK = parent._isolated_function(
    parent.run_paired_task,
    _PARENT_RUN_TASK=_PIPE_PARENT_RUN_TASK,
    validate_isolation=validate_isolation,
)


def run_paired_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: Any,
    two_wave_policy: Any,
    monotonic: Callable[[], float],
    progress: Any = None,
) -> dict[str, Any]:
    validate_isolation()
    return _RUN_PAIRED_TASK(
        task,
        model=model,
        search=search,
        limits=limits,
        two_wave_policy=two_wave_policy,
        monotonic=monotonic,
        progress=progress,
    )


candidate = parent.candidate
FrozenWorldBankSnapshotSearchClient = parent.FrozenWorldBankSnapshotSearchClient
MonotoneFillCachingSearchClient = parent.MonotoneFillCachingSearchClient
PAGE_COUNT = parent.PAGE_COUNT
ENTITY_ROW_COUNT = parent.ENTITY_ROW_COUNT
TARGET_COUNT = parent.TARGET_COUNT
MAXIMUM_PAGE_CHARS = parent.MAXIMUM_PAGE_CHARS
MAXIMUM_EVIDENCE_CHARS = parent.MAXIMUM_EVIDENCE_CHARS
PARENT_LIMITS = copy.deepcopy(parent.PARENT_LIMITS)
PARENT_TWO_WAVE_POLICY = copy.deepcopy(parent.PARENT_TWO_WAVE_POLICY)
PARENT_TAVILY_KEY_SLOT_CAP = parent.PARENT_TAVILY_KEY_SLOT_CAP
validate_paired_receipt = parent.validate_paired_receipt
validate_result = parent.validate_result
validate_snapshot_receipt = parent.validate_snapshot_receipt
payload_sha256 = parent.payload_sha256


__all__ = [
    "ENTITY_ROW_COUNT",
    "FrozenWorldBankSnapshotSearchClient",
    "MAXIMUM_EVIDENCE_CHARS",
    "MAXIMUM_PAGE_CHARS",
    "PAGE_COUNT",
    "PARENT_LIMITS",
    "PARENT_TAVILY_KEY_SLOT_CAP",
    "PARENT_TWO_WAVE_POLICY",
    "POLICY_ID",
    "TARGET_COUNT",
    "candidate",
    "extract_pipe_delimited_visible_columns",
    "payload_sha256",
    "run_paired_task",
    "validate_isolation",
    "validate_paired_receipt",
    "validate_result",
    "validate_snapshot_receipt",
]
