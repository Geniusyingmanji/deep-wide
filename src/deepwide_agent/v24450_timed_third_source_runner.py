"""Failure-observable parent runner with content-free stage timings.

The subprocess wall clock in V2.43.09 is sampled before result validation.
This successor preserves that child measurement and adds two non-overlapping
parent stages: exactly one complete serialized-envelope/terminal-artifact
validation, followed by one counts-only projection that can consume only the
validated V2.44.48 capability.  Failed children project an explicit zero row.

Per-task and aggregate timing receipts contain ordinals, counts, booleans, and
durations only.  They contain no task text, opaque identifier, query, URL,
page, source, value, prediction, candidate, content hash, credential,
benchmark label, gold answer, evaluator state, reward, or score.  Sums across
concurrent tasks are explicitly work totals and are not represented as batch
wall time.
"""

from __future__ import annotations

import copy
import json
import math
import statistics
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .v24308_child_exit_observability import validate_parent_receipt
from .v24309_runner_exit_integration import run_observed_subprocess
from .v24312_deadline_reliability import validate_receipt as validate_model_receipt
from .v24316_deadline_search import validate_transport_health
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24399_failure_observable_runner import (
    MODEL_NAME,
    RESULT_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
    build_directory_observation,
)
from .v24448_serialized_third_source_envelope import (
    ValidatedSerializedThirdSourceEnvelope,
    validate_serialized_observed_bundle,
)
from scripts.v24449_third_source_external_projection import (
    local_failure,
    task_projection,
    validate_task_projection,
)


POLICY_ID = "v24450_single_validation_timed_third_source_runner_v1"
TIMING_ROLE = "v24450_content_free_task_stage_timing"
AGGREGATE_ROLE = "v24450_content_free_stage_timing_aggregate"
TIMING_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "ordinal",
        "parent_taxonomy",
        "child_wall_seconds",
        "post_child_validation_wall_seconds",
        "projection_wall_seconds",
        "parent_post_child_wall_seconds",
        "validation_invocations",
        "projection_invocations",
        "complete_envelope_and_terminal_artifacts_validated_once",
        "projection_consumed_only_validated_capability",
        "child_wall_excludes_post_child_validation_and_projection",
        "task_question_opaque_id_query_url_page_source_value_prediction_candidate_or_content_hash_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "network_model_search_fetch_process_or_evaluator_called_by_timing_builder",
        "timing_payload_sha256",
    }
)
STAT_PREFIXES = (
    "child_wall",
    "post_child_validation_wall",
    "projection_wall",
    "parent_post_child_wall",
)
STAT_SUFFIXES = ("sum_seconds", "median_seconds", "p95_seconds", "max_seconds")
AGGREGATE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "selected",
        "exact_ordinal_vector",
        "parent_success_tasks",
        "validation_invocations",
        "projection_invocations",
        "complete_validation_once_tasks",
        "validated_capability_projection_tasks",
        *(
            f"{prefix}_{suffix}"
            for prefix in STAT_PREFIXES
            for suffix in STAT_SUFFIXES
        ),
        "parallel_task_work_sums_are_not_batch_wall_seconds",
        "task_question_opaque_id_query_url_page_source_value_prediction_candidate_or_content_hash_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "network_model_search_fetch_process_or_evaluator_called_by_aggregate_builder",
        "aggregate_payload_sha256",
    }
)


@dataclass(frozen=True)
class TimedThirdSourceOutcome:
    parent_receipt: dict[str, Any]
    mechanism_projection: dict[str, Any]
    observation: dict[str, Any]
    timing_receipt: dict[str, Any]


def _finite_nonnegative(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise ValueError(f"V2.44.50 {label} is not nonnegative and finite")
    return float(value)


def _ordinary_object(directory: Path, name: str) -> dict[str, Any]:
    base = directory.resolve()
    path = directory / name
    if (
        directory.is_symlink()
        or not directory.is_dir()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(base)
    ):
        raise RuntimeError("V2.44.50 terminal artifact is not ordinary")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.44.50 terminal artifact is not an object")
    return value


def build_timing_receipt(
    *,
    ordinal: int,
    parent: Mapping[str, Any],
    child_wall_seconds: float,
    validation_wall_seconds: float,
    projection_wall_seconds: float,
    validation_invocations: int,
    projection_invocations: int,
    validated_capability: bool,
    projected_validated_capability: bool,
) -> dict[str, Any]:
    validated_parent = validate_parent_receipt(parent)
    child = _finite_nonnegative(child_wall_seconds, "child wall")
    validation = _finite_nonnegative(
        validation_wall_seconds, "validation wall"
    )
    projection = _finite_nonnegative(projection_wall_seconds, "projection wall")
    success = validated_parent["failure_taxonomy"] == "success"
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal < 1
        or validation_invocations not in {0, 1}
        or projection_invocations not in {0, 1}
        or success
        and (
            validation_invocations != 1
            or projection_invocations != 1
            or not validated_capability
            or not projected_validated_capability
        )
        or not success
        and (projection_invocations != 0 or projected_validated_capability)
    ):
        raise ValueError("V2.44.50 task stage invocation contract drifted")
    value = {
        "artifact_version": 1,
        "role": TIMING_ROLE,
        "policy_id": POLICY_ID,
        "ordinal": ordinal,
        "parent_taxonomy": validated_parent["failure_taxonomy"],
        "child_wall_seconds": round(child, 6),
        "post_child_validation_wall_seconds": round(validation, 6),
        "projection_wall_seconds": round(projection, 6),
        "parent_post_child_wall_seconds": round(validation + projection, 6),
        "validation_invocations": validation_invocations,
        "projection_invocations": projection_invocations,
        "complete_envelope_and_terminal_artifacts_validated_once": bool(
            validated_capability
        ),
        "projection_consumed_only_validated_capability": bool(
            projected_validated_capability
        ),
        "child_wall_excludes_post_child_validation_and_projection": True,
        "task_question_opaque_id_query_url_page_source_value_prediction_candidate_or_content_hash_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "network_model_search_fetch_process_or_evaluator_called_by_timing_builder": False,
    }
    value["timing_payload_sha256"] = payload_sha256(value)
    validate_timing_receipt(value)
    return value


def validate_timing_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("timing_payload_sha256", None)
    success = copied.get("parent_taxonomy") == "success"
    if (
        set(copied) != TIMING_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != TIMING_ROLE
        or copied.get("policy_id") != POLICY_ID
        or isinstance(copied.get("ordinal"), bool)
        or not isinstance(copied.get("ordinal"), int)
        or copied["ordinal"] < 1
        or not isinstance(copied.get("parent_taxonomy"), str)
        or any(
            _finite_nonnegative(copied.get(name), name) < 0
            for name in (
                "child_wall_seconds",
                "post_child_validation_wall_seconds",
                "projection_wall_seconds",
                "parent_post_child_wall_seconds",
            )
        )
        or not math.isclose(
            float(copied["parent_post_child_wall_seconds"]),
            float(copied["post_child_validation_wall_seconds"])
            + float(copied["projection_wall_seconds"]),
            abs_tol=2e-6,
        )
        or copied.get("validation_invocations") not in {0, 1}
        or copied.get("projection_invocations") not in {0, 1}
        or success
        and (
            copied.get("validation_invocations") != 1
            or copied.get("projection_invocations") != 1
            or copied.get(
                "complete_envelope_and_terminal_artifacts_validated_once"
            )
            is not True
            or copied.get("projection_consumed_only_validated_capability")
            is not True
        )
        or not success
        and (
            copied.get("projection_invocations") != 0
            or copied.get("projection_consumed_only_validated_capability")
            is not False
        )
        or copied.get("child_wall_excludes_post_child_validation_and_projection")
        is not True
        or copied.get(
            "task_question_opaque_id_query_url_page_source_value_prediction_candidate_or_content_hash_emitted"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get(
            "network_model_search_fetch_process_or_evaluator_called_by_timing_builder"
        )
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.50 task timing receipt drifted")
    return copy.deepcopy(copied)


def run_timed_observed_subprocess(
    *,
    ordinal: int,
    cwd: Path,
    output_root: Path,
    directory: Path,
    command: Sequence[str],
    environment: Mapping[str, str],
    timeout_seconds: float,
    expected_model_cap: int,
    monotonic: Callable[[], float] = time.monotonic,
    popen: Any = None,
) -> TimedThirdSourceOutcome:
    """Run one child, strongly validate once, then project content-free counts."""

    capabilities: list[ValidatedSerializedThirdSourceEnvelope] = []
    child_wall = 0.0
    child_started = 0.0
    validation_wall = 0.0
    validation_invocations = 0

    def result_validator(value: Mapping[str, Any]) -> object:
        nonlocal validation_invocations, validation_wall
        validation_invocations += 1
        started = monotonic()
        try:
            capability = validate_serialized_observed_bundle(
                value,
                model_slot_receipt=_ordinary_object(directory, MODEL_NAME),
                transport_health=_ordinary_object(directory, TRANSPORT_NAME),
                search_single_shot_receipt=_ordinary_object(directory, SEARCH_NAME),
                expected_cap=expected_model_cap,
            )
            capabilities.append(capability)
            return capability
        finally:
            validation_wall += max(0.0, monotonic() - started)

    def model_validator(value: Mapping[str, Any]) -> object:
        nonlocal validation_wall
        started = monotonic()
        try:
            return validate_model_receipt(
                dict(value), expected_cap=expected_model_cap
            )
        finally:
            validation_wall += max(0.0, monotonic() - started)

    def transport_validator(value: Mapping[str, Any]) -> object:
        nonlocal validation_wall
        started = monotonic()
        try:
            return validate_transport_health(value)
        finally:
            validation_wall += max(0.0, monotonic() - started)

    base_popen = subprocess.Popen if popen is None else popen

    class TimedProcess:
        def __init__(self, inner: Any) -> None:
            self.inner = inner

        @property
        def pid(self) -> int:
            return int(self.inner.pid)

        @property
        def returncode(self) -> int | None:
            return self.inner.returncode

        def wait(self, timeout: float | None = None) -> int:
            nonlocal child_wall
            try:
                return int(self.inner.wait(timeout=timeout))
            finally:
                if self.inner.returncode is not None:
                    child_wall = max(0.0, monotonic() - child_started)

    def timed_popen(*args: Any, **kwargs: Any) -> TimedProcess:
        nonlocal child_started, child_wall
        child_started = monotonic()
        try:
            return TimedProcess(base_popen(*args, **kwargs))
        except BaseException:
            child_wall = max(0.0, monotonic() - child_started)
            raise

    outcome = run_observed_subprocess(
        cwd=cwd,
        output_root=output_root,
        directory=directory,
        command=command,
        environment=environment,
        timeout_seconds=timeout_seconds,
        result_validator=result_validator,
        model_receipt_validator=model_validator,
        transport_receipt_validator=transport_validator,
        result_name=RESULT_NAME,
        model_receipt_name=MODEL_NAME,
        transport_receipt_name=TRANSPORT_NAME,
        terminal_name="child_terminal_receipt.json",
        parent_name="parent_exit_receipt.json",
        popen=timed_popen,
    )
    parent = validate_parent_receipt(outcome.receipt)
    started = monotonic()
    try:
        observation = build_directory_observation(
            ordinal,
            parent,
            directory=directory,
            expected_model_cap=expected_model_cap,
        )
    finally:
        validation_wall += max(0.0, monotonic() - started)
    mechanism = local_failure(ordinal)
    projection_wall = 0.0
    projection_invocations = 0
    projected_validated_capability = False
    if parent["failure_taxonomy"] == "success":
        if validation_invocations != 1 or len(capabilities) != 1:
            raise RuntimeError("V2.44.50 successful child lacks one capability")
        projection_invocations = 1
        started = monotonic()
        try:
            mechanism = task_projection(ordinal, capabilities[0])
            projected_validated_capability = True
        finally:
            projection_wall += max(0.0, monotonic() - started)
    validate_task_projection(mechanism)
    timing = build_timing_receipt(
        ordinal=ordinal,
        parent=parent,
        child_wall_seconds=child_wall,
        validation_wall_seconds=validation_wall,
        projection_wall_seconds=projection_wall,
        validation_invocations=validation_invocations,
        projection_invocations=projection_invocations,
        validated_capability=(len(capabilities) == 1),
        projected_validated_capability=projected_validated_capability,
    )
    return TimedThirdSourceOutcome(
        parent_receipt=parent,
        mechanism_projection=mechanism,
        observation=observation,
        timing_receipt=timing,
    )


def _p95(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("V2.44.50 cannot summarize an empty timing vector")
    ordered = sorted(float(value) for value in values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def _stats(values: Sequence[float]) -> dict[str, float]:
    if not values:
        raise ValueError("V2.44.50 cannot summarize an empty timing vector")
    finite = [_finite_nonnegative(value, "aggregate timing") for value in values]
    return {
        "sum_seconds": round(sum(finite), 6),
        "median_seconds": round(float(statistics.median(finite)), 6),
        "p95_seconds": round(_p95(finite), 6),
        "max_seconds": round(max(finite), 6),
    }


def aggregate_stage_timings(
    receipts: Sequence[Mapping[str, Any]], *, selected: int
) -> dict[str, Any]:
    values = sorted(
        (validate_timing_receipt(value) for value in receipts),
        key=lambda value: value["ordinal"],
    )
    if (
        isinstance(selected, bool)
        or not isinstance(selected, int)
        or selected < 1
        or len(values) != selected
    ):
        raise ValueError("V2.44.50 timing aggregate selection drifted")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": AGGREGATE_ROLE,
        "policy_id": POLICY_ID,
        "selected": selected,
        "exact_ordinal_vector": [item["ordinal"] for item in values]
        == list(range(1, selected + 1)),
        "parent_success_tasks": sum(
            item["parent_taxonomy"] == "success" for item in values
        ),
        "validation_invocations": sum(
            item["validation_invocations"] for item in values
        ),
        "projection_invocations": sum(
            item["projection_invocations"] for item in values
        ),
        "complete_validation_once_tasks": sum(
            item["complete_envelope_and_terminal_artifacts_validated_once"]
            for item in values
        ),
        "validated_capability_projection_tasks": sum(
            item["projection_consumed_only_validated_capability"]
            for item in values
        ),
    }
    fields = {
        "child_wall": "child_wall_seconds",
        "post_child_validation_wall": "post_child_validation_wall_seconds",
        "projection_wall": "projection_wall_seconds",
        "parent_post_child_wall": "parent_post_child_wall_seconds",
    }
    for prefix, field in fields.items():
        for suffix, number in _stats([float(item[field]) for item in values]).items():
            value[f"{prefix}_{suffix}"] = number
    value.update(
        {
            "parallel_task_work_sums_are_not_batch_wall_seconds": True,
            "task_question_opaque_id_query_url_page_source_value_prediction_candidate_or_content_hash_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "network_model_search_fetch_process_or_evaluator_called_by_aggregate_builder": False,
        }
    )
    value["aggregate_payload_sha256"] = payload_sha256(value)
    validate_stage_timing_aggregate(value)
    return value


def validate_stage_timing_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("aggregate_payload_sha256", None)
    selected = copied.get("selected")
    count_fields = (
        "parent_success_tasks",
        "validation_invocations",
        "projection_invocations",
        "complete_validation_once_tasks",
        "validated_capability_projection_tasks",
    )
    timing_fields = tuple(
        f"{prefix}_{suffix}"
        for prefix in STAT_PREFIXES
        for suffix in STAT_SUFFIXES
    )
    if (
        set(copied) != AGGREGATE_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != AGGREGATE_ROLE
        or copied.get("policy_id") != POLICY_ID
        or isinstance(selected, bool)
        or not isinstance(selected, int)
        or selected < 1
        or copied.get("exact_ordinal_vector") is not True
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or not 0 <= copied[name] <= selected
            for name in count_fields
        )
        or copied.get("projection_invocations")
        != copied.get("parent_success_tasks")
        or copied.get("complete_validation_once_tasks")
        != copied.get("parent_success_tasks")
        or copied.get("validated_capability_projection_tasks")
        != copied.get("parent_success_tasks")
        or any(
            _finite_nonnegative(copied.get(name), name) < 0
            for name in timing_fields
        )
        or any(
            float(copied[f"{prefix}_max_seconds"])
            < float(copied[f"{prefix}_median_seconds"])
            or float(copied[f"{prefix}_max_seconds"])
            < float(copied[f"{prefix}_p95_seconds"])
            for prefix in STAT_PREFIXES
        )
        or copied.get("parallel_task_work_sums_are_not_batch_wall_seconds")
        is not True
        or copied.get(
            "task_question_opaque_id_query_url_page_source_value_prediction_candidate_or_content_hash_emitted"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get(
            "network_model_search_fetch_process_or_evaluator_called_by_aggregate_builder"
        )
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.50 timing aggregate drifted")
    return copy.deepcopy(copied)


__all__ = [
    "AGGREGATE_KEYS",
    "AGGREGATE_ROLE",
    "POLICY_ID",
    "TIMING_KEYS",
    "TIMING_ROLE",
    "TimedThirdSourceOutcome",
    "aggregate_stage_timings",
    "build_timing_receipt",
    "run_timed_observed_subprocess",
    "validate_stage_timing_aggregate",
    "validate_timing_receipt",
]
