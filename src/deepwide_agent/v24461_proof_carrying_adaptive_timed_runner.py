"""Timed parent runner for proof-carrying adaptive support artifacts.

Successful children are projected only through the V2.44.59 opaque
capability.  Failed children retain the V2.43.99 partial-effect lower-bound
path.  Parent timing separates child wall, certificate validation,
observation projection, and adaptive capability projection, while explicitly
recording zero recursive historical semantic replay.
"""

from __future__ import annotations

import copy
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
from .v24397_failure_observability import build_task_observation
from .v24399_failure_observable_runner import (
    MODEL_NAME,
    PARENT_NAME,
    RESULT_NAME,
    TRANSPORT_NAME,
    build_directory_observation,
)
from .v24459_proof_carrying_adaptive_entropy_support import (
    CERTIFICATE_NAME,
    ValidatedProofCarryingAdaptiveEnvelope,
    validate_proof_carrying_adaptive_bundle,
)
from .v24460_adaptive_capability_projection import (
    local_failure,
    task_projection,
    validate_task_projection,
)


POLICY_ID = "v24461_proof_carrying_adaptive_timed_runner_v1"
TIMING_ROLE = "v24461_content_free_adaptive_task_stage_timing"
AGGREGATE_ROLE = "v24461_content_free_adaptive_stage_timing_aggregate"
SUCCESS_SURFACE = frozenset(
    {
        RESULT_NAME,
        MODEL_NAME,
        TRANSPORT_NAME,
        "search_single_shot_receipt.json",
        CERTIFICATE_NAME,
        "child_terminal_receipt.json",
        PARENT_NAME,
    }
)
TIMING_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "ordinal",
        "parent_taxonomy",
        "child_wall_seconds",
        "parent_certificate_validation_wall_seconds",
        "observation_projection_wall_seconds",
        "adaptive_projection_wall_seconds",
        "parent_post_child_wall_seconds",
        "certificate_validation_invocations",
        "observation_projection_invocations",
        "adaptive_projection_invocations",
        "child_complete_semantic_validation_attested",
        "parent_exact_surface_and_certificate_validated_once",
        "observation_consumed_only_validated_capability_receipts_on_success",
        "adaptive_projection_consumed_only_validated_capability",
        "failure_observation_uses_partial_effect_lower_bound_path",
        "parent_recursive_historical_semantic_replay_performed",
        "child_wall_excludes_parent_validation_and_projection",
        "task_question_opaque_id_query_url_page_source_value_prediction_candidate_or_content_hash_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "network_model_search_fetch_process_or_evaluator_called_by_timing_builder",
        "timing_payload_sha256",
    }
)
STAT_PREFIXES = (
    "child_wall",
    "parent_certificate_validation_wall",
    "observation_projection_wall",
    "adaptive_projection_wall",
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
        "parent_failure_tasks",
        "certificate_validation_invocations",
        "observation_projection_invocations",
        "adaptive_projection_invocations",
        "complete_child_validation_attested_tasks",
        "certificate_validated_once_tasks",
        "capability_observation_tasks",
        "capability_adaptive_projection_tasks",
        "failure_lower_bound_observation_tasks",
        "recursive_historical_semantic_replay_tasks",
        *(f"{prefix}_{suffix}" for prefix in STAT_PREFIXES for suffix in STAT_SUFFIXES),
        "parallel_task_work_sums_are_not_batch_wall_seconds",
        "task_question_opaque_id_query_url_page_source_value_prediction_candidate_or_content_hash_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "network_model_search_fetch_process_or_evaluator_called_by_aggregate_builder",
        "aggregate_payload_sha256",
    }
)


@dataclass(frozen=True)
class ProofCarryingAdaptiveTimedOutcome:
    parent_receipt: dict[str, Any]
    adaptive_projection: dict[str, Any]
    observation: dict[str, Any]
    timing_receipt: dict[str, Any]


def _finite_nonnegative(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise ValueError(f"V2.44.61 {label} is not nonnegative and finite")
    return float(value)


def _validate_success_surface(directory: Path) -> None:
    if directory.is_symlink() or not directory.is_dir():
        raise RuntimeError("V2.44.61 successful task directory is not ordinary")
    observed: set[str] = set()
    for path in directory.iterdir():
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("V2.44.61 successful task surface is nonordinary")
        observed.add(path.name)
    if observed != SUCCESS_SURFACE:
        raise RuntimeError("V2.44.61 successful task artifact surface drifted")


def build_timing_receipt(
    *,
    ordinal: int,
    parent: Mapping[str, Any],
    child_wall_seconds: float,
    certificate_validation_wall_seconds: float,
    observation_projection_wall_seconds: float,
    adaptive_projection_wall_seconds: float,
    certificate_validation_invocations: int,
    observation_projection_invocations: int,
    adaptive_projection_invocations: int,
    child_complete_validation_attested: bool,
    certificate_validated_once: bool,
    capability_observation: bool,
    capability_adaptive_projection: bool,
    failure_lower_bound_observation: bool,
) -> dict[str, Any]:
    parent_value = validate_parent_receipt(parent)
    child = _finite_nonnegative(child_wall_seconds, "child wall")
    certificate = _finite_nonnegative(
        certificate_validation_wall_seconds, "certificate validation wall"
    )
    observation = _finite_nonnegative(
        observation_projection_wall_seconds, "observation projection wall"
    )
    adaptive = _finite_nonnegative(
        adaptive_projection_wall_seconds, "adaptive projection wall"
    )
    success = parent_value["failure_taxonomy"] == "success"
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal < 1
        or certificate_validation_invocations not in {0, 1}
        or observation_projection_invocations != 1
        or adaptive_projection_invocations not in {0, 1}
        or success
        and (
            certificate_validation_invocations != 1
            or adaptive_projection_invocations != 1
            or not child_complete_validation_attested
            or not certificate_validated_once
            or not capability_observation
            or not capability_adaptive_projection
            or failure_lower_bound_observation
        )
        or not success
        and (
            adaptive_projection_invocations != 0
            or child_complete_validation_attested
            or certificate_validated_once
            or capability_observation
            or capability_adaptive_projection
            or not failure_lower_bound_observation
        )
    ):
        raise ValueError("V2.44.61 task stage invocation contract drifted")
    value = {
        "artifact_version": 1,
        "role": TIMING_ROLE,
        "policy_id": POLICY_ID,
        "ordinal": ordinal,
        "parent_taxonomy": parent_value["failure_taxonomy"],
        "child_wall_seconds": round(child, 6),
        "parent_certificate_validation_wall_seconds": round(certificate, 6),
        "observation_projection_wall_seconds": round(observation, 6),
        "adaptive_projection_wall_seconds": round(adaptive, 6),
        "parent_post_child_wall_seconds": round(
            certificate + observation + adaptive, 6
        ),
        "certificate_validation_invocations": certificate_validation_invocations,
        "observation_projection_invocations": observation_projection_invocations,
        "adaptive_projection_invocations": adaptive_projection_invocations,
        "child_complete_semantic_validation_attested": bool(
            child_complete_validation_attested
        ),
        "parent_exact_surface_and_certificate_validated_once": bool(
            certificate_validated_once
        ),
        "observation_consumed_only_validated_capability_receipts_on_success": bool(
            capability_observation
        ),
        "adaptive_projection_consumed_only_validated_capability": bool(
            capability_adaptive_projection
        ),
        "failure_observation_uses_partial_effect_lower_bound_path": bool(
            failure_lower_bound_observation
        ),
        "parent_recursive_historical_semantic_replay_performed": False,
        "child_wall_excludes_parent_validation_and_projection": True,
        "task_question_opaque_id_query_url_page_source_value_prediction_candidate_or_content_hash_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "network_model_search_fetch_process_or_evaluator_called_by_timing_builder": False,
    }
    value["timing_payload_sha256"] = payload_sha256(value)
    return validate_timing_receipt(value)


def validate_timing_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("timing_payload_sha256", None)
    success = copied.get("parent_taxonomy") == "success"
    duration_names = (
        "child_wall_seconds",
        "parent_certificate_validation_wall_seconds",
        "observation_projection_wall_seconds",
        "adaptive_projection_wall_seconds",
        "parent_post_child_wall_seconds",
    )
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
            for name in duration_names
        )
        or not math.isclose(
            float(copied["parent_post_child_wall_seconds"]),
            float(copied["parent_certificate_validation_wall_seconds"])
            + float(copied["observation_projection_wall_seconds"])
            + float(copied["adaptive_projection_wall_seconds"]),
            abs_tol=3e-6,
        )
        or copied.get("certificate_validation_invocations") not in {0, 1}
        or copied.get("observation_projection_invocations") != 1
        or copied.get("adaptive_projection_invocations") not in {0, 1}
        or success
        and (
            copied.get("certificate_validation_invocations") != 1
            or copied.get("adaptive_projection_invocations") != 1
            or copied.get("child_complete_semantic_validation_attested") is not True
            or copied.get("parent_exact_surface_and_certificate_validated_once")
            is not True
            or copied.get(
                "observation_consumed_only_validated_capability_receipts_on_success"
            )
            is not True
            or copied.get(
                "adaptive_projection_consumed_only_validated_capability"
            )
            is not True
            or copied.get("failure_observation_uses_partial_effect_lower_bound_path")
            is not False
        )
        or not success
        and (
            copied.get("adaptive_projection_invocations") != 0
            or copied.get("child_complete_semantic_validation_attested") is not False
            or copied.get("parent_exact_surface_and_certificate_validated_once")
            is not False
            or copied.get(
                "observation_consumed_only_validated_capability_receipts_on_success"
            )
            is not False
            or copied.get(
                "adaptive_projection_consumed_only_validated_capability"
            )
            is not False
            or copied.get("failure_observation_uses_partial_effect_lower_bound_path")
            is not True
        )
        or copied.get("parent_recursive_historical_semantic_replay_performed")
        is not False
        or copied.get("child_wall_excludes_parent_validation_and_projection") is not True
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
        raise ValueError("V2.44.61 task timing receipt drifted")
    return copy.deepcopy(copied)


def run_proof_carrying_adaptive_timed_subprocess(
    *,
    ordinal: int,
    cwd: Path,
    output_root: Path,
    directory: Path,
    command: Sequence[str],
    environment: Mapping[str, str],
    timeout_seconds: float,
    expected_model_cap: int,
    expected_validator_manifest_sha256: str,
    monotonic: Callable[[], float] = time.monotonic,
    popen: Any = None,
) -> ProofCarryingAdaptiveTimedOutcome:
    capabilities: list[ValidatedProofCarryingAdaptiveEnvelope] = []
    child_wall = 0.0
    child_started = 0.0
    certificate_wall = 0.0
    certificate_invocations = 0

    def result_validator(value: Mapping[str, Any]) -> object:
        nonlocal certificate_invocations, certificate_wall
        certificate_invocations += 1
        started = monotonic()
        try:
            capability = validate_proof_carrying_adaptive_bundle(
                value,
                directory=directory,
                expected_model_cap=expected_model_cap,
                expected_validator_manifest_sha256=expected_validator_manifest_sha256,
            )
            capabilities.append(capability)
            return capability
        finally:
            certificate_wall += max(0.0, monotonic() - started)

    def model_validator(value: Mapping[str, Any]) -> object:
        nonlocal certificate_wall
        started = monotonic()
        try:
            return validate_model_receipt(dict(value), expected_cap=expected_model_cap)
        finally:
            certificate_wall += max(0.0, monotonic() - started)

    def transport_validator(value: Mapping[str, Any]) -> object:
        nonlocal certificate_wall
        started = monotonic()
        try:
            return validate_transport_health(value)
        finally:
            certificate_wall += max(0.0, monotonic() - started)

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
        parent_name=PARENT_NAME,
        popen=timed_popen,
    )
    parent = validate_parent_receipt(outcome.receipt)
    success = parent["failure_taxonomy"] == "success"
    observation_started = monotonic()
    capability_observation = False
    failure_lower_bound = False
    try:
        if success:
            if certificate_invocations != 1 or len(capabilities) != 1:
                raise RuntimeError("V2.44.61 successful child lacks one capability")
            _validate_success_surface(directory)
            receipts = capabilities[0].content_free_observation_receipts()
            observation = build_task_observation(
                ordinal,
                parent,
                child=receipts["child"],
                failure_snapshot=None,
                model_receipt=receipts["model"],
                transport_health=receipts["transport"],
                search_receipt=receipts["search"],
                expected_model_cap=expected_model_cap,
            )
            capability_observation = True
        else:
            observation = build_directory_observation(
                ordinal,
                parent,
                directory=directory,
                expected_model_cap=expected_model_cap,
            )
            failure_lower_bound = True
    finally:
        observation_wall = max(0.0, monotonic() - observation_started)

    adaptive = local_failure(ordinal)
    adaptive_wall = 0.0
    adaptive_invocations = 0
    capability_projection = False
    if success:
        adaptive_invocations = 1
        started = monotonic()
        try:
            adaptive = task_projection(ordinal, capabilities[0])
            capability_projection = True
        finally:
            adaptive_wall += max(0.0, monotonic() - started)
    validate_task_projection(adaptive)
    timing = build_timing_receipt(
        ordinal=ordinal,
        parent=parent,
        child_wall_seconds=child_wall,
        certificate_validation_wall_seconds=certificate_wall,
        observation_projection_wall_seconds=observation_wall,
        adaptive_projection_wall_seconds=adaptive_wall,
        certificate_validation_invocations=certificate_invocations,
        observation_projection_invocations=1,
        adaptive_projection_invocations=adaptive_invocations,
        child_complete_validation_attested=success,
        certificate_validated_once=success and len(capabilities) == 1,
        capability_observation=capability_observation,
        capability_adaptive_projection=capability_projection,
        failure_lower_bound_observation=failure_lower_bound,
    )
    return ProofCarryingAdaptiveTimedOutcome(
        parent_receipt=parent,
        adaptive_projection=adaptive,
        observation=observation,
        timing_receipt=timing,
    )


def _p95(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("V2.44.61 cannot summarize an empty timing vector")
    ordered = sorted(float(value) for value in values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def _stats(values: Sequence[float]) -> dict[str, float]:
    finite = [_finite_nonnegative(value, "aggregate timing") for value in values]
    if not finite:
        raise ValueError("V2.44.61 cannot summarize an empty timing vector")
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
        (validate_timing_receipt(item) for item in receipts),
        key=lambda item: item["ordinal"],
    )
    if (
        isinstance(selected, bool)
        or not isinstance(selected, int)
        or selected < 1
        or len(values) != selected
        or [item["ordinal"] for item in values] != list(range(1, selected + 1))
    ):
        raise ValueError("V2.44.61 timing aggregate selection drifted")
    success = sum(item["parent_taxonomy"] == "success" for item in values)
    result: dict[str, Any] = {
        "artifact_version": 1,
        "role": AGGREGATE_ROLE,
        "policy_id": POLICY_ID,
        "selected": selected,
        "exact_ordinal_vector": True,
        "parent_success_tasks": success,
        "parent_failure_tasks": selected - success,
        "certificate_validation_invocations": sum(
            item["certificate_validation_invocations"] for item in values
        ),
        "observation_projection_invocations": sum(
            item["observation_projection_invocations"] for item in values
        ),
        "adaptive_projection_invocations": sum(
            item["adaptive_projection_invocations"] for item in values
        ),
        "complete_child_validation_attested_tasks": sum(
            item["child_complete_semantic_validation_attested"] for item in values
        ),
        "certificate_validated_once_tasks": sum(
            item["parent_exact_surface_and_certificate_validated_once"]
            for item in values
        ),
        "capability_observation_tasks": sum(
            item[
                "observation_consumed_only_validated_capability_receipts_on_success"
            ]
            for item in values
        ),
        "capability_adaptive_projection_tasks": sum(
            item["adaptive_projection_consumed_only_validated_capability"]
            for item in values
        ),
        "failure_lower_bound_observation_tasks": sum(
            item["failure_observation_uses_partial_effect_lower_bound_path"]
            for item in values
        ),
        "recursive_historical_semantic_replay_tasks": sum(
            item["parent_recursive_historical_semantic_replay_performed"]
            for item in values
        ),
    }
    fields = {
        "child_wall": "child_wall_seconds",
        "parent_certificate_validation_wall": "parent_certificate_validation_wall_seconds",
        "observation_projection_wall": "observation_projection_wall_seconds",
        "adaptive_projection_wall": "adaptive_projection_wall_seconds",
        "parent_post_child_wall": "parent_post_child_wall_seconds",
    }
    for prefix, field in fields.items():
        for suffix, number in _stats([item[field] for item in values]).items():
            result[f"{prefix}_{suffix}"] = number
    result.update(
        {
            "parallel_task_work_sums_are_not_batch_wall_seconds": True,
            "task_question_opaque_id_query_url_page_source_value_prediction_candidate_or_content_hash_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "network_model_search_fetch_process_or_evaluator_called_by_aggregate_builder": False,
        }
    )
    result["aggregate_payload_sha256"] = payload_sha256(result)
    return validate_stage_timing_aggregate(result)


def validate_stage_timing_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("aggregate_payload_sha256", None)
    selected = copied.get("selected")
    count_fields = (
        "parent_success_tasks",
        "parent_failure_tasks",
        "certificate_validation_invocations",
        "observation_projection_invocations",
        "adaptive_projection_invocations",
        "complete_child_validation_attested_tasks",
        "certificate_validated_once_tasks",
        "capability_observation_tasks",
        "capability_adaptive_projection_tasks",
        "failure_lower_bound_observation_tasks",
        "recursive_historical_semantic_replay_tasks",
    )
    timing_fields = tuple(
        f"{prefix}_{suffix}" for prefix in STAT_PREFIXES for suffix in STAT_SUFFIXES
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
            or copied[name] < 0
            for name in count_fields
        )
        or copied["parent_success_tasks"] + copied["parent_failure_tasks"]
        != selected
        or not (
            copied["parent_success_tasks"]
            <= copied["certificate_validation_invocations"]
            <= selected
        )
        or copied["observation_projection_invocations"] != selected
        or copied["adaptive_projection_invocations"]
        != copied["parent_success_tasks"]
        or any(
            copied[name] != copied["parent_success_tasks"]
            for name in (
                "complete_child_validation_attested_tasks",
                "certificate_validated_once_tasks",
                "capability_observation_tasks",
                "capability_adaptive_projection_tasks",
            )
        )
        or copied["failure_lower_bound_observation_tasks"]
        != copied["parent_failure_tasks"]
        or copied["recursive_historical_semantic_replay_tasks"] != 0
        or any(
            _finite_nonnegative(copied.get(name), name) < 0
            for name in timing_fields
        )
        or copied.get("parallel_task_work_sums_are_not_batch_wall_seconds") is not True
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
        raise ValueError("V2.44.61 timing aggregate drifted")
    return copy.deepcopy(copied)


__all__ = [
    "AGGREGATE_ROLE",
    "POLICY_ID",
    "ProofCarryingAdaptiveTimedOutcome",
    "TIMING_ROLE",
    "aggregate_stage_timings",
    "build_timing_receipt",
    "run_proof_carrying_adaptive_timed_subprocess",
    "validate_stage_timing_aggregate",
    "validate_timing_receipt",
]
