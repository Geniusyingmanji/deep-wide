"""Bounded adaptive worker integration for V2.44.70.

This append-only module leaves the frozen V2.44.64 implementation byte-for-
byte unchanged.  It reproduces its single complete validation and mechanical
persistence while emitting a content-free V2.44.69 stage chain outside the
proof artifact directory.  Model and hosted-search effects use V2.44.68 hard
total-wall helpers.  An outer supervisor hard-stops the worker before the
parent deadline and publishes a sealed supervision receipt in a sibling
directory.

Successful workers retain the exact V2.44.59 proof surface.  Failed or timed
out workers retain the existing failure/terminal surface plus conservative
effect lower bounds.  No benchmark labels, mapping, gold, evaluator state,
reward, score, or credentials are available to this module.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .v24263_global_model_limiter import POOL_ID
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24280_task_union_single_shot import TaskUnionSingleShotMixin
from .v24309_runner_exit_integration import (
    run_child_with_terminal_receipt,
    _new_json,
)
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24399_failure_observable_runner import (
    FAILURE_NAME,
    MODEL_NAME,
    RESULT_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
    persist_failure_artifacts,
)
from . import v24457_adaptive_entropy_support as adaptive
from .v24459_proof_carrying_adaptive_entropy_support import (
    CERTIFICATE_NAME,
    build_terminal_certificate,
)
from .v24461_proof_carrying_adaptive_timed_runner import (
    ProofCarryingAdaptiveTimedOutcome,
    run_proof_carrying_adaptive_timed_subprocess,
)
from . import v24464_single_validation_adaptive_persistence as frozen
from .v24468_total_wall_transport import (
    HardTotalWallNativeSearchClient,
    HardTotalWallResponsesClient,
)
from .v24469_bounded_worker_supervisor import (
    STAGES,
    WORKER_RECEIPT_NAME,
    StageJournal,
    bind_worker_to_parent,
    supervise_worker,
    validate_worker_receipt,
)


POLICY_ID = "v24470_bounded_single_validation_adaptive_integration_v1"
SUPERVISION_RECEIPT_NAME = "bounded_worker_supervision_receipt.json"
SUPERVISION_AGGREGATE_ROLE = "v24470_content_free_supervision_aggregate"
SUPERVISION_AGGREGATE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "selected",
        "exact_ordinal_vector",
        "worker_success_tasks",
        "worker_hard_timeout_tasks",
        "worker_nonzero_tasks",
        "checkpoint_chain_valid_tasks",
        "last_stage_counts",
        "model_effect_started_lower_bound",
        "model_effect_finished_lower_bound",
        "hosted_search_effect_started_lower_bound",
        "hosted_search_effect_finished_lower_bound",
        "public_fetch_effect_started_lower_bound",
        "public_fetch_effect_finished_lower_bound",
        "complete_validation_entered_tasks",
        "complete_validation_returned_tasks",
        "worker_wall_sum_seconds",
        "worker_wall_max_seconds",
        "contains_task_question_opaque_id_prompt_response_query_url_page_prediction_candidate_value_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "network_model_search_fetch_or_evaluator_called_by_aggregate_builder",
        "aggregate_payload_sha256",
    }
)


class HardTotalWallUncertaintyNativeSearchClient(
    TaskUnionSingleShotMixin, HardTotalWallNativeSearchClient
):
    """Task-union search with hard total-wall hosted requests."""


@dataclass(frozen=True)
class BoundedAdaptiveParentOutcome:
    proof: ProofCarryingAdaptiveTimedOutcome
    supervision_receipt: dict[str, Any]


class WorkerSupervisionFailure(RuntimeError):
    """Content-free child-supervisor failure used only for nonzero exit."""


def _validate_layout(
    output_root: Path, directory: Path, checkpoint_directory: Path
) -> tuple[Path, Path, Path]:
    if (
        output_root.is_symlink()
        or not output_root.is_dir()
        or directory.is_symlink()
        or not directory.is_dir()
        or checkpoint_directory.is_symlink()
        or not checkpoint_directory.is_dir()
    ):
        raise RuntimeError("V2.44.70 output layout contains a nonordinary directory")
    root = output_root.resolve()
    task = directory.resolve()
    checkpoint = checkpoint_directory.resolve()
    if (
        task == checkpoint
        or task.parent != root
        or checkpoint.parent != root
    ):
        raise RuntimeError("V2.44.70 task/checkpoint directories must be siblings")
    return root, task, checkpoint


def validate_bounded_supervision_receipt(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    receipt = validate_worker_receipt(value)
    count_fields = (
        "model_effect_started_lower_bound",
        "model_effect_finished_lower_bound",
        "hosted_search_effect_started_lower_bound",
        "hosted_search_effect_finished_lower_bound",
        "public_fetch_effect_started_lower_bound",
        "public_fetch_effect_finished_lower_bound",
    )
    hard = receipt["worker_hard_timeout"]
    code = receipt["return_code"]
    chain = receipt["checkpoint_chain_valid"]
    success = not hard and code == 0
    if (
        not chain
        and (
            receipt["last_stage"] is not None
            or receipt["last_stage_sequence"] != 0
            or any(receipt[name] != 0 for name in count_fields)
            or receipt["complete_validation_entered"] is not False
            or receipt["complete_validation_returned"] is not False
        )
        or hard and code is not None
        or not hard and code is None
        or success
        and (
            not chain
            or receipt["last_stage"] != "worker_complete"
            or receipt["failure_snapshot_written"] is not False
        )
        or hard and receipt["last_stage"] == "worker_complete"
    ):
        raise ValueError("V2.44.70 bounded supervision receipt drifted")
    return receipt


def build_hard_total_wall_model(
    *,
    url: str,
    model_name: str,
    reasoning_effort: str,
    service_tier: str,
    static_timeout_seconds: float,
    max_retries: int,
    slot_directory: Path,
    output_root: Path,
    slot_cap: int,
    absolute_deadline: float,
    cleanup_reserve_seconds: float,
    minimum_attempt_seconds: float,
    stage_callback: Callable[[str], None],
    monotonic: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> DeadlineAwareGlobalModelSlotLimiter:
    inner = HardTotalWallResponsesClient(
        url,
        model_name,
        reasoning_effort=reasoning_effort,
        service_tier=service_tier,
        timeout=static_timeout_seconds,
        max_retries=max_retries,
        absolute_deadline=absolute_deadline,
        cleanup_reserve_seconds=cleanup_reserve_seconds,
        minimum_attempt_seconds=minimum_attempt_seconds,
        monotonic=monotonic,
        sleeper=sleeper,
        stage_callback=stage_callback,
    )
    return DeadlineAwareGlobalModelSlotLimiter(
        inner,
        slot_directory=slot_directory,
        output_root=output_root,
        absolute_deadline=absolute_deadline,
        slot_cap=slot_cap,
        pool_id=POOL_ID,
        cleanup_reserve_seconds=cleanup_reserve_seconds,
        minimum_attempt_seconds=minimum_attempt_seconds,
        monotonic=monotonic,
        sleeper=sleeper,
    )


def build_hard_total_wall_search(
    *,
    url: str,
    model_name: str,
    reasoning_effort: str,
    service_tier: str,
    static_timeout_seconds: float,
    max_retries: int,
    absolute_deadline: float,
    cleanup_reserve_seconds: float,
    minimum_attempt_seconds: float,
    stage_callback: Callable[[str], None],
    max_workers: int = 1,
    batch_size: int = 8,
    search_context_size: str = "medium",
    max_output_tokens: int = 4_000,
    fetch_pages: bool = False,
    fetch_workers: int = 8,
    fetch_timeout: float = 20,
    max_page_chars: int = 5_000,
    hard_fetch_deadline_seconds: float = 25,
    monotonic: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> HardTotalWallUncertaintyNativeSearchClient:
    return HardTotalWallUncertaintyNativeSearchClient(
        url,
        model_name,
        reasoning_effort=reasoning_effort,
        service_tier=service_tier,
        timeout=static_timeout_seconds,
        max_retries=max_retries,
        max_workers=max_workers,
        batch_size=batch_size,
        search_context_size=search_context_size,
        max_output_tokens=max_output_tokens,
        fetch_pages=fetch_pages,
        fetch_workers=fetch_workers,
        fetch_timeout=fetch_timeout,
        max_page_chars=max_page_chars,
        hard_fetch_deadline_seconds=hard_fetch_deadline_seconds,
        absolute_deadline=absolute_deadline,
        cleanup_reserve_seconds=cleanup_reserve_seconds,
        minimum_attempt_seconds=minimum_attempt_seconds,
        monotonic=monotonic,
        sleeper=sleeper,
        stage_callback=stage_callback,
    )


def run_stage_hooked_single_validation(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    partition_seed_sha256: str,
    limits: Any,
    monotonic: Callable[[], float],
    stage_callback: Callable[[str], None],
) -> frozen.ValidatedAdaptiveExecution:
    """Run the frozen complete validator once with content-free boundaries."""

    captured: list[dict[str, Any]] = []
    parent_returns = 0
    with frozen._CAPTURE_LOCK:
        original_run = adaptive.parent.run_v24447_task
        original_build = adaptive.parent.build_envelope

        def capture_run(*args: Any, **kwargs: Any) -> Any:
            nonlocal parent_returns
            result = original_run(*args, **kwargs)
            parent_returns += 1
            stage_callback("parent_runtime_returned")
            stage_callback("adaptive_support_entered")
            return result

        def capture_build(outcome: Any) -> dict[str, Any]:
            stage_callback("adaptive_support_returned")
            stage_callback("complete_validation_entered")
            value = original_build(outcome)
            captured.append(copy.deepcopy(value))
            return value

        adaptive.parent.run_v24447_task = capture_run
        adaptive.parent.build_envelope = capture_build
        try:
            outcome = adaptive.run_v24457_task(
                task,
                model=model,
                search=search,
                partition_seed_sha256=partition_seed_sha256,
                limits=limits,
                monotonic=monotonic,
            )
            stage_callback("complete_validation_returned")
        finally:
            adaptive.parent.run_v24447_task = original_run
            adaptive.parent.build_envelope = original_build
    if parent_returns != 1 or len(captured) != 1:
        raise RuntimeError("V2.44.70 complete validation boundary drifted")
    return frozen.ValidatedAdaptiveExecution._create(
        outcome, parent_envelope=captured[0]
    )


def run_and_persist_stage_hooked_task(
    task: Mapping[str, Any],
    *,
    model_factory: Callable[[], Any],
    search_factory: Callable[[], Any],
    partition_seed_sha256: str,
    limits: Any,
    monotonic: Callable[[], float],
    expected_model_cap: int,
    directory: Path,
    writer: Callable[[str, Mapping[str, Any]], None],
    validator_manifest_sha256: str,
    stage_callback: Callable[[str], None],
) -> adaptive.IntegratedAdaptiveEntropySupportOutcome:
    model: Any = None
    search: Any = None
    failure_stage = "model_construction"
    try:
        model = model_factory()
        stage_callback("model_constructed")
        failure_stage = "search_construction"
        search = search_factory()
        stage_callback("search_constructed")
        failure_stage = "runtime"
        stage_callback("runtime_entered")
        validated = run_stage_hooked_single_validation(
            task,
            model=model,
            search=search,
            partition_seed_sha256=partition_seed_sha256,
            limits=limits,
            monotonic=monotonic,
            stage_callback=stage_callback,
        )
    except BaseException as error:
        persist_failure_artifacts(
            error,
            failure_stage=failure_stage,
            model=model,
            search=search,
            expected_model_cap=expected_model_cap,
            writer=writer,
        )
        raise

    outcome = validated._trusted_outcome()
    stage_callback("artifact_persistence_entered")
    envelope = frozen.build_envelope_from_validated_execution(validated)
    artifacts = {
        MODEL_NAME: copy.deepcopy(outcome.model_slot_receipt),
        TRANSPORT_NAME: copy.deepcopy(outcome.transport_health),
        SEARCH_NAME: copy.deepcopy(outcome.search_single_shot_receipt),
        RESULT_NAME: envelope,
    }
    written: set[str] = set()
    try:
        for name in (MODEL_NAME, TRANSPORT_NAME, SEARCH_NAME, RESULT_NAME):
            writer(name, artifacts[name])
            written.add(name)
    except BaseException as error:
        from .v24397_failure_observability import build_failure_snapshot

        snapshot = build_failure_snapshot(
            error,
            failure_stage="artifact_serialization",
            model_receipt=(
                outcome.model_slot_receipt if MODEL_NAME in written else None
            ),
            transport_health=(
                outcome.transport_health if TRANSPORT_NAME in written else None
            ),
            search_receipt=(
                outcome.search_single_shot_receipt if SEARCH_NAME in written else None
            ),
            expected_model_cap=expected_model_cap,
        )
        writer(FAILURE_NAME, snapshot)
        raise

    stage_callback("certificate_persistence_entered")
    certificate = build_terminal_certificate(
        directory,
        outcome,
        validator_manifest_sha256=validator_manifest_sha256,
        expected_artifacts=artifacts,
    )
    writer(CERTIFICATE_NAME, certificate)
    return outcome


def run_worker(
    task: Mapping[str, Any],
    *,
    ordinal: int,
    expected_supervisor_pid: int,
    checkpoint_directory: Path,
    output_root: Path,
    directory: Path,
    model_factory: Callable[[Callable[[str], None]], Any],
    search_factory: Callable[[Callable[[str], None]], Any],
    partition_seed_sha256: str,
    limits: Any,
    monotonic: Callable[[], float],
    expected_model_cap: int,
    writer: Callable[[str, Mapping[str, Any]], None],
    validator_manifest_sha256: str,
) -> None:
    output_root, directory, checkpoint_directory = _validate_layout(
        output_root, directory, checkpoint_directory
    )
    bind_worker_to_parent(expected_parent_pid=expected_supervisor_pid)
    journal = StageJournal(checkpoint_directory, ordinal=ordinal)
    journal.record("worker_entered")

    def action() -> None:
        run_and_persist_stage_hooked_task(
            task,
            model_factory=lambda: model_factory(journal.record),
            search_factory=lambda: search_factory(journal.record),
            partition_seed_sha256=partition_seed_sha256,
            limits=limits,
            monotonic=monotonic,
            expected_model_cap=expected_model_cap,
            directory=directory,
            writer=writer,
            validator_manifest_sha256=validator_manifest_sha256,
            stage_callback=journal.record,
        )

    run_child_with_terminal_receipt(
        output_root=output_root,
        directory=directory,
        action=action,
        result_name=RESULT_NAME,
        model_receipt_name=MODEL_NAME,
        transport_receipt_name=TRANSPORT_NAME,
        terminal_name="child_terminal_receipt.json",
    )
    journal.record("worker_complete")


def _read_supervision_receipt(
    checkpoint_directory: Path, *, ordinal: int
) -> dict[str, Any]:
    if checkpoint_directory.is_symlink() or not checkpoint_directory.is_dir():
        raise RuntimeError("V2.44.70 checkpoint directory is not ordinary")
    path = checkpoint_directory / SUPERVISION_RECEIPT_NAME
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.44.70 supervision receipt is absent")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise RuntimeError("V2.44.70 supervision receipt is not an object")
    validated = validate_bounded_supervision_receipt(value)
    if validated["ordinal"] != ordinal:
        raise RuntimeError("V2.44.70 supervision ordinal drifted")
    return validated


def supervise_and_publish(
    *,
    ordinal: int,
    cwd: Path,
    output_root: Path,
    directory: Path,
    checkpoint_directory: Path,
    command: Sequence[str],
    timeout_seconds: float,
    expected_model_cap: int,
    writer: Callable[[str, Mapping[str, Any]], None],
) -> dict[str, Any]:
    output_root, directory, checkpoint_directory = _validate_layout(
        output_root, directory, checkpoint_directory
    )
    receipt = supervise_worker(
        ordinal=ordinal,
        cwd=cwd,
        directory=directory,
        checkpoint_directory=checkpoint_directory,
        command=command,
        timeout_seconds=timeout_seconds,
        expected_model_cap=expected_model_cap,
        writer=writer,
    )
    _new_json(checkpoint_directory / SUPERVISION_RECEIPT_NAME, receipt)
    if receipt["worker_hard_timeout"] or receipt["return_code"] != 0:
        raise WorkerSupervisionFailure("V2.44.70 bounded worker failed")
    return receipt


def run_bounded_parent_subprocess(
    *,
    ordinal: int,
    cwd: Path,
    output_root: Path,
    directory: Path,
    checkpoint_directory: Path,
    command: Sequence[str],
    parent_timeout_seconds: float,
    expected_model_cap: int,
    expected_validator_manifest_sha256: str,
) -> BoundedAdaptiveParentOutcome:
    output_root, directory, checkpoint_directory = _validate_layout(
        output_root, directory, checkpoint_directory
    )
    proof = run_proof_carrying_adaptive_timed_subprocess(
        ordinal=ordinal,
        cwd=cwd,
        output_root=output_root,
        directory=directory,
        command=command,
        environment={
            "HOME": os.environ.get("HOME", str(Path.home())),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        timeout_seconds=parent_timeout_seconds,
        expected_model_cap=expected_model_cap,
        expected_validator_manifest_sha256=expected_validator_manifest_sha256,
    )
    supervision = _read_supervision_receipt(
        checkpoint_directory, ordinal=ordinal
    )
    success = proof.parent_receipt["failure_taxonomy"] == "success"
    if (
        success
        is not (
            supervision["worker_hard_timeout"] is False
            and supervision["return_code"] == 0
            and supervision["last_stage"] == "worker_complete"
        )
        or success and supervision["failure_snapshot_written"] is not False
        or not success
        and supervision["return_code"] == 0
        and supervision["worker_hard_timeout"] is False
    ):
        raise RuntimeError("V2.44.70 proof/supervision outcome drifted")
    return BoundedAdaptiveParentOutcome(proof=proof, supervision_receipt=supervision)


def aggregate_supervision_receipts(
    receipts: Sequence[Mapping[str, Any]], *, selected: int
) -> dict[str, Any]:
    values = sorted(
        (validate_bounded_supervision_receipt(value) for value in receipts),
        key=lambda value: value["ordinal"],
    )
    if (
        isinstance(selected, bool)
        or not isinstance(selected, int)
        or selected < 1
        or len(values) != selected
        or [value["ordinal"] for value in values]
        != list(range(1, selected + 1))
    ):
        raise ValueError("V2.44.70 supervision selection drifted")
    stages = Counter(
        str(value["last_stage"])
        if value["last_stage"] is not None
        else "unobserved"
        for value in values
    )
    value = {
        "artifact_version": 1,
        "role": SUPERVISION_AGGREGATE_ROLE,
        "policy_id": POLICY_ID,
        "selected": selected,
        "exact_ordinal_vector": True,
        "worker_success_tasks": sum(
            value["worker_hard_timeout"] is False and value["return_code"] == 0
            for value in values
        ),
        "worker_hard_timeout_tasks": sum(
            value["worker_hard_timeout"] is True for value in values
        ),
        "worker_nonzero_tasks": sum(
            value["worker_hard_timeout"] is False
            and value["return_code"] not in (None, 0)
            for value in values
        ),
        "checkpoint_chain_valid_tasks": sum(
            value["checkpoint_chain_valid"] is True for value in values
        ),
        "last_stage_counts": dict(sorted(stages.items())),
        "model_effect_started_lower_bound": sum(
            value["model_effect_started_lower_bound"] for value in values
        ),
        "model_effect_finished_lower_bound": sum(
            value["model_effect_finished_lower_bound"] for value in values
        ),
        "hosted_search_effect_started_lower_bound": sum(
            value["hosted_search_effect_started_lower_bound"] for value in values
        ),
        "hosted_search_effect_finished_lower_bound": sum(
            value["hosted_search_effect_finished_lower_bound"] for value in values
        ),
        "public_fetch_effect_started_lower_bound": sum(
            value["public_fetch_effect_started_lower_bound"] for value in values
        ),
        "public_fetch_effect_finished_lower_bound": sum(
            value["public_fetch_effect_finished_lower_bound"] for value in values
        ),
        "complete_validation_entered_tasks": sum(
            value["complete_validation_entered"] is True for value in values
        ),
        "complete_validation_returned_tasks": sum(
            value["complete_validation_returned"] is True for value in values
        ),
        "worker_wall_sum_seconds": round(
            sum(float(value["elapsed_seconds"]) for value in values), 6
        ),
        "worker_wall_max_seconds": round(
            max(float(value["elapsed_seconds"]) for value in values), 6
        ),
        "contains_task_question_opaque_id_prompt_response_query_url_page_prediction_candidate_value_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "network_model_search_fetch_or_evaluator_called_by_aggregate_builder": False,
    }
    value["aggregate_payload_sha256"] = payload_sha256(value)
    return validate_supervision_aggregate(value)


def validate_supervision_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("aggregate_payload_sha256", None)
    selected = copied.get("selected")
    count_fields = (
        "worker_success_tasks",
        "worker_hard_timeout_tasks",
        "worker_nonzero_tasks",
        "checkpoint_chain_valid_tasks",
        "model_effect_started_lower_bound",
        "model_effect_finished_lower_bound",
        "hosted_search_effect_started_lower_bound",
        "hosted_search_effect_finished_lower_bound",
        "public_fetch_effect_started_lower_bound",
        "public_fetch_effect_finished_lower_bound",
        "complete_validation_entered_tasks",
        "complete_validation_returned_tasks",
    )
    stages = copied.get("last_stage_counts")
    if (
        set(copied) != SUPERVISION_AGGREGATE_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != SUPERVISION_AGGREGATE_ROLE
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
        or copied["worker_success_tasks"]
        + copied["worker_hard_timeout_tasks"]
        + copied["worker_nonzero_tasks"]
        != selected
        or copied["checkpoint_chain_valid_tasks"] > selected
        or copied["model_effect_finished_lower_bound"]
        > copied["model_effect_started_lower_bound"]
        or copied["hosted_search_effect_finished_lower_bound"]
        > copied["hosted_search_effect_started_lower_bound"]
        or copied["public_fetch_effect_finished_lower_bound"]
        > copied["public_fetch_effect_started_lower_bound"]
        or copied["complete_validation_returned_tasks"]
        > copied["complete_validation_entered_tasks"]
        or not isinstance(stages, Mapping)
        or not stages
        or any(
            not isinstance(stage, str)
            or not stage
            or stage not in {*STAGES, "unobserved"}
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 1
            for stage, count in stages.items()
        )
        or sum(stages.values()) != selected
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), (int, float))
            or float(copied[name]) < 0
            for name in ("worker_wall_sum_seconds", "worker_wall_max_seconds")
        )
        or copied["worker_wall_max_seconds"]
        > copied["worker_wall_sum_seconds"] + 1e-6
        or any(
            copied.get(name) is not False
            for name in (
                "contains_task_question_opaque_id_prompt_response_query_url_page_prediction_candidate_value_or_credential",
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
                "network_model_search_fetch_or_evaluator_called_by_aggregate_builder",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.70 supervision aggregate drifted")
    return copied


__all__ = [
    "BoundedAdaptiveParentOutcome",
    "HardTotalWallUncertaintyNativeSearchClient",
    "POLICY_ID",
    "SUPERVISION_RECEIPT_NAME",
    "WorkerSupervisionFailure",
    "aggregate_supervision_receipts",
    "build_hard_total_wall_model",
    "build_hard_total_wall_search",
    "run_and_persist_stage_hooked_task",
    "run_bounded_parent_subprocess",
    "run_stage_hooked_single_validation",
    "run_worker",
    "supervise_and_publish",
    "validate_supervision_aggregate",
    "validate_bounded_supervision_receipt",
]
