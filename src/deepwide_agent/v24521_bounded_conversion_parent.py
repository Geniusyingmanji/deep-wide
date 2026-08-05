"""Bounded parent/supervisor/worker integration for V2.45.19–20.

This successor preserves the existing process-group supervisor and the
150/220/245-second separated budget.  Successful tasks validate exactly one
V2.45.19 outer certificate and project one V2.45.20 proof row.  Failed tasks
emit the V2.45.20 content-free failure-as-zero row while independent failure
observability retains effect lower bounds.
"""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from .v24308_child_exit_observability import validate_parent_receipt
from .v24309_runner_exit_integration import (
    run_child_with_terminal_receipt,
    run_observed_subprocess,
)
from .v24312_deadline_reliability import validate_receipt as validate_model_receipt
from .v24316_deadline_search import validate_transport_health
from .v24397_failure_observability import build_task_observation
from .v24399_failure_observable_runner import (
    MODEL_NAME,
    PARENT_NAME,
    RESULT_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
    build_directory_observation,
    persist_failure_artifacts,
)
from .v24461_proof_carrying_adaptive_timed_runner import (
    ProofCarryingAdaptiveTimedOutcome,
    build_timing_receipt,
)
from .v24470_bounded_adaptive_integration import (
    BoundedAdaptiveParentOutcome,
    _read_supervision_receipt,
    supervise_and_publish,
)
from .v24480_separated_effect_validation_budget import (
    build_phase_deadlines,
    remaining_parent_seconds,
    remaining_worker_seconds,
)
from .v24482_separated_budget_worker_integration import (
    append_deadline_origin,
    deadlines_from_origin,
)
from .v24519_proof_carrying_conversion_observability import (
    CERTIFICATE_NAME as OUTER_CERTIFICATE_NAME,
    RECEIPT_NAME,
    SUCCESS_NAMES,
    ValidatedProofCarryingConversionObservability,
    build_outer_certificate,
    validate_proof_carrying_conversion_bundle,
)
from . import v24504_proof_carrying_record_bound_reserve as parent_proof
from . import v24518_conversion_observability as conversion_observability
from .v24485_execution_scoped_validation_memo import ExecutionValidationMemo
from .v24486_memoized_worker_integration import validate_memo_receipt
from .v24508_execution_scoped_high_level_validation_memo import (
    HighLevelValidationMemo,
    validate_receipt as validate_high_level_receipt,
)
from .v24515_neutral_cell_discovery_planner import (
    NeutralCellDiscoveryPlanner,
    validate_receipt as validate_planner_receipt,
)
from .v24520_total_conversion_projection import (
    failure_projection,
    task_projection,
    validate_total_row,
)


POLICY_ID = "v24521_bounded_conversion_observability_parent_v1"
SUCCESS_SURFACE = frozenset({*SUCCESS_NAMES, PARENT_NAME})


def _validate_success_surface(directory: Path) -> None:
    if directory.is_symlink() or not directory.is_dir():
        raise RuntimeError("V2.45.21 successful directory is not ordinary")
    observed: set[str] = set()
    for path in directory.iterdir():
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("V2.45.21 successful surface is nonordinary")
        observed.add(path.name)
    if observed != SUCCESS_SURFACE:
        raise RuntimeError("V2.45.21 successful artifact surface drifted")


def run_conversion_timed_subprocess(
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
    capabilities: list[ValidatedProofCarryingConversionObservability] = []
    child_wall = 0.0
    child_started = 0.0
    certificate_wall = 0.0
    certificate_invocations = 0

    def result_validator(value: Mapping[str, Any]) -> object:
        nonlocal certificate_invocations, certificate_wall
        certificate_invocations += 1
        started = monotonic()
        try:
            capability = validate_proof_carrying_conversion_bundle(
                value,
                directory=directory,
                expected_model_cap=expected_model_cap,
                expected_validator_manifest_sha256=(
                    expected_validator_manifest_sha256
                ),
            )
            capabilities.append(capability)
            return capability
        finally:
            certificate_wall += max(0.0, monotonic() - started)

    def model_validator(value: Mapping[str, Any]) -> object:
        nonlocal certificate_wall
        started = monotonic()
        try:
            return validate_model_receipt(
                dict(value), expected_cap=expected_model_cap
            )
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
    parent_receipt = validate_parent_receipt(outcome.receipt)
    success = parent_receipt["failure_taxonomy"] == "success"
    observation_started = monotonic()
    capability_observation = False
    failure_lower_bound = False
    try:
        if success:
            if certificate_invocations != 1 or len(capabilities) != 1:
                raise RuntimeError("V2.45.21 successful child lacks one capability")
            _validate_success_surface(directory)
            receipts = capabilities[0].parent_capability().content_free_observation_receipts()
            observation = build_task_observation(
                ordinal,
                parent_receipt,
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
                parent_receipt,
                directory=directory,
                expected_model_cap=expected_model_cap,
            )
            failure_lower_bound = True
    finally:
        observation_wall = max(0.0, monotonic() - observation_started)
    projection = failure_projection(ordinal)
    projection_wall = 0.0
    projection_invocations = 0
    capability_projection = False
    if success:
        projection_invocations = 1
        started = monotonic()
        try:
            projection = task_projection(ordinal, capabilities[0])
            capability_projection = True
        finally:
            projection_wall = max(0.0, monotonic() - started)
    validate_total_row(projection)
    timing = build_timing_receipt(
        ordinal=ordinal,
        parent=parent_receipt,
        child_wall_seconds=child_wall,
        certificate_validation_wall_seconds=certificate_wall,
        observation_projection_wall_seconds=observation_wall,
        adaptive_projection_wall_seconds=projection_wall,
        certificate_validation_invocations=certificate_invocations,
        observation_projection_invocations=1,
        adaptive_projection_invocations=projection_invocations,
        child_complete_validation_attested=success,
        certificate_validated_once=success and len(capabilities) == 1,
        capability_observation=capability_observation,
        capability_adaptive_projection=capability_projection,
        failure_lower_bound_observation=failure_lower_bound,
    )
    return ProofCarryingAdaptiveTimedOutcome(
        parent_receipt=parent_receipt,
        adaptive_projection=projection,
        observation=observation,
        timing_receipt=timing,
    )


def run_conversion_worker(
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
) -> dict[str, Any]:
    # Reuse the unchanged layout, parent-death binding and stage journal from
    # the frozen neutral worker, but place the new proof writer in its action.
    from .v24469_bounded_worker_supervisor import StageJournal, bind_worker_to_parent
    from .v24470_bounded_adaptive_integration import _validate_layout

    _validate_layout(output_root, directory, checkpoint_directory)
    bind_worker_to_parent(expected_parent_pid=expected_supervisor_pid)
    journal = StageJournal(checkpoint_directory, ordinal=ordinal)
    journal.record("worker_entered")
    completed: dict[str, Any] | None = None
    model: Any = None
    search: Any = None

    def action() -> None:
        nonlocal completed, model, search
        stage = "model_construction"
        try:
            model = model_factory(journal.record)
            journal.record("model_constructed")
            stage = "search_construction"
            search = search_factory(journal.record)
            journal.record("search_constructed")
            stage = "runtime"
            journal.record("runtime_entered")
            low = ExecutionValidationMemo()
            high = HighLevelValidationMemo()
            planner = NeutralCellDiscoveryPlanner()
            with low, high, planner:
                validated = parent_proof.run_single_validation_v24503_task(
                    task,
                    model=model,
                    search=search,
                    partition_seed_sha256=partition_seed_sha256,
                    limits=limits,
                    monotonic=monotonic,
                )
                conversion = (
                    conversion_observability.build_from_validated_execution(
                        validated
                    )
                )
            low_receipt = validate_memo_receipt(low.content_free_receipt())
            high_receipt = validate_high_level_receipt(
                high.content_free_receipt()
            )
            planner_receipt = validate_planner_receipt(
                planner.content_free_receipt()
            )
            journal.record("parent_runtime_returned")
            journal.record("adaptive_support_entered")
            journal.record("adaptive_support_returned")
            journal.record("complete_validation_entered")
            journal.record("complete_validation_returned")
        except BaseException as error:
            persist_failure_artifacts(
                error,
                failure_stage=stage,
                model=model,
                search=search,
                expected_model_cap=expected_model_cap,
                writer=writer,
            )
            raise
        outcome = validated._trusted_outcome()
        artifacts = {
            MODEL_NAME: outcome.model_slot_receipt,
            TRANSPORT_NAME: outcome.transport_health,
            SEARCH_NAME: outcome.search_single_shot_receipt,
            RESULT_NAME: parent_proof.build_envelope_from_validated_execution(
                validated
            ),
        }
        journal.record("artifact_persistence_entered")
        for name in parent_proof.ARTIFACT_NAMES:
            writer(name, artifacts[name])
        journal.record("certificate_persistence_entered")
        parent_certificate = parent_proof.build_terminal_certificate(
            directory,
            validated,
            memo_receipt=low_receipt,
            validator_manifest_sha256=validator_manifest_sha256,
            expected_artifacts=artifacts,
        )
        writer(parent_proof.CERTIFICATE_NAME, parent_certificate)
        writer(RECEIPT_NAME, conversion)
        outer = build_outer_certificate(
            directory,
            conversion_receipt=conversion,
            low_memo_receipt=low_receipt,
            high_memo_receipt=high_receipt,
            planner_receipt=planner_receipt,
            validator_manifest_sha256=validator_manifest_sha256,
        )
        writer(OUTER_CERTIFICATE_NAME, outer)
        completed = conversion

    run_child_with_terminal_receipt(
        output_root=output_root,
        directory=directory,
        action=action,
        result_name=RESULT_NAME,
        model_receipt_name=MODEL_NAME,
        transport_receipt_name=TRANSPORT_NAME,
        terminal_name="child_terminal_receipt.json",
    )
    if completed is None:
        raise RuntimeError("V2.45.21 conversion observability outcome is absent")
    journal.record("worker_complete")
    return dict(completed)


def supervise_conversion_worker_with_separated_budget(
    *,
    ordinal: int,
    cwd: Path,
    output_root: Path,
    directory: Path,
    checkpoint_directory: Path,
    worker_command: Sequence[str],
    deadline_origin: object,
    expected_model_cap: int,
    writer: Callable[[str, Mapping[str, Any]], None],
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    deadlines = deadlines_from_origin(deadline_origin)
    return supervise_and_publish(
        ordinal=ordinal,
        cwd=cwd,
        output_root=output_root,
        directory=directory,
        checkpoint_directory=checkpoint_directory,
        command=append_deadline_origin(worker_command, deadlines),
        timeout_seconds=remaining_worker_seconds(deadlines, monotonic=monotonic),
        expected_model_cap=expected_model_cap,
        writer=writer,
    )


def run_conversion_parent_with_separated_budget(
    *,
    ordinal: int,
    cwd: Path,
    output_root: Path,
    directory: Path,
    checkpoint_directory: Path,
    supervisor_command: Sequence[str],
    expected_model_cap: int,
    expected_validator_manifest_sha256: str,
    monotonic: Callable[[], float] = time.monotonic,
) -> BoundedAdaptiveParentOutcome:
    deadlines = build_phase_deadlines(monotonic=monotonic)
    proof = run_conversion_timed_subprocess(
        ordinal=ordinal,
        cwd=cwd,
        output_root=output_root,
        directory=directory,
        command=append_deadline_origin(supervisor_command, deadlines),
        environment={
            "HOME": os.environ.get("HOME", str(Path.home())),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        timeout_seconds=remaining_parent_seconds(
            deadlines, monotonic=monotonic
        ),
        expected_model_cap=expected_model_cap,
        expected_validator_manifest_sha256=expected_validator_manifest_sha256,
        monotonic=monotonic,
    )
    supervision = _read_supervision_receipt(
        checkpoint_directory, ordinal=ordinal
    )
    success = proof.parent_receipt["failure_taxonomy"] == "success"
    if success is not (
        supervision["worker_hard_timeout"] is False
        and supervision["return_code"] == 0
        and supervision["last_stage"] == "worker_complete"
    ):
        raise RuntimeError("V2.45.21 proof/supervision outcome drifted")
    return BoundedAdaptiveParentOutcome(
        proof=proof, supervision_receipt=supervision
    )


__all__ = [
    "POLICY_ID",
    "SUCCESS_SURFACE",
    "run_conversion_parent_with_separated_budget",
    "run_conversion_timed_subprocess",
    "run_conversion_worker",
    "supervise_conversion_worker_with_separated_budget",
]
