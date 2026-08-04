"""Timed parent and bounded worker adapter for V2.44.91 capabilities.

The worker reuses the V2.44.70 stage journal, hard process-group supervision,
and content-free failure observation.  The successful parent replaces only
the adaptive certificate validator/projection with the V2.44.91 targeted
capability.  It validates exact terminal bytes once and never recursively
replays the historical semantic graph.
"""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from .v24308_child_exit_observability import validate_parent_receipt
from .v24309_runner_exit_integration import run_observed_subprocess
from .v24309_runner_exit_integration import run_child_with_terminal_receipt
from .v24312_deadline_reliability import validate_receipt as validate_model_receipt
from .v24316_deadline_search import validate_transport_health
from .v24397_failure_observability import build_task_observation
from .v24399_failure_observable_runner import (
    MODEL_NAME,
    PARENT_NAME,
    RESULT_NAME,
    TRANSPORT_NAME,
    build_directory_observation,
    persist_failure_artifacts,
)
from .v24461_proof_carrying_adaptive_timed_runner import (
    ProofCarryingAdaptiveTimedOutcome,
    build_timing_receipt,
)
from .v24469_bounded_worker_supervisor import StageJournal, bind_worker_to_parent
from .v24470_bounded_adaptive_integration import (
    BoundedAdaptiveParentOutcome,
    _read_supervision_receipt,
    _validate_layout,
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
from .v24464_single_validation_adaptive_persistence import (
    run_single_validation_v24457_task,
)
from .v24485_execution_scoped_validation_memo import ExecutionValidationMemo
from .v24486_memoized_worker_integration import validate_memo_receipt
from . import v24490_entropy_targeted_support_search as targeted
from .v24491_proof_carrying_targeted_support import (
    CERTIFICATE_NAME,
    ValidatedTargetedExecution,
    ValidatedProofCarryingTargetedEnvelope,
    _unvalidated_envelope,
    build_envelope_from_validated_execution,
    build_terminal_certificate,
    task_projection,
    validate_cross_artifacts,
    validate_proof_carrying_targeted_bundle,
    validate_task_projection,
)


POLICY_ID = "v24492_bounded_targeted_proof_parent_v1"
FAILURE_PROJECTION_KEYS = frozenset(
    {
        "ordinal",
        "status",
        "passed",
        "target_plan_present",
        "safe_change_count_before_targeted_search",
        "safe_change_count_after_targeted_search",
        "decision_credit_total_nats_after_targeted_search",
        "additional_fetch_effects",
        "additional_model_acquisitions",
        "validation_memo_misses",
        "validation_memo_hits",
        "validation_memo_mismatches",
        "projection_consumed_validated_capability",
        "private_task_content_emitted",
        "privileged_evaluator_content_read",
    }
)
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


def _validate_success_surface(directory: Path) -> None:
    if directory.is_symlink() or not directory.is_dir():
        raise RuntimeError("V2.44.92 successful task directory is not ordinary")
    observed: set[str] = set()
    for path in directory.iterdir():
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("V2.44.92 successful surface is nonordinary")
        observed.add(path.name)
    if observed != SUCCESS_SURFACE:
        raise RuntimeError("V2.44.92 successful artifact surface drifted")


def failure_projection(ordinal: int) -> dict[str, Any]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        raise ValueError("V2.44.92 failure ordinal is invalid")
    return {
        "ordinal": ordinal,
        "status": "failure_as_zero",
        "passed": False,
        "target_plan_present": False,
        "safe_change_count_before_targeted_search": 0,
        "safe_change_count_after_targeted_search": 0,
        "decision_credit_total_nats_after_targeted_search": 0.0,
        "additional_fetch_effects": 0,
        "additional_model_acquisitions": 0,
        "validation_memo_misses": 0,
        "validation_memo_hits": 0,
        "validation_memo_mismatches": 0,
        "projection_consumed_validated_capability": False,
        "private_task_content_emitted": False,
        "privileged_evaluator_content_read": False,
    }


def validate_failure_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    expected = failure_projection(int(copied.get("ordinal", 0)))
    if set(copied) != FAILURE_PROJECTION_KEYS or copied != expected:
        raise ValueError("V2.44.92 failure projection drifted")
    return copied


def run_targeted_timed_subprocess(
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
    capabilities: list[ValidatedProofCarryingTargetedEnvelope] = []
    child_wall = 0.0
    child_started = 0.0
    certificate_wall = 0.0
    certificate_invocations = 0

    def result_validator(value: Mapping[str, Any]) -> object:
        nonlocal certificate_invocations, certificate_wall
        certificate_invocations += 1
        started = monotonic()
        try:
            capability = validate_proof_carrying_targeted_bundle(
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
                raise RuntimeError("V2.44.92 successful child lacks one capability")
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

    projection: dict[str, Any] = failure_projection(ordinal)
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
    if success:
        validate_task_projection(projection)
    else:
        validate_failure_projection(projection)
    timing = build_timing_receipt(
        ordinal=ordinal,
        parent=parent,
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
        parent_receipt=parent,
        adaptive_projection=projection,
        observation=observation,
        timing_receipt=timing,
    )


def run_targeted_worker(
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
    output_root, directory, checkpoint_directory = _validate_layout(
        output_root, directory, checkpoint_directory
    )
    bind_worker_to_parent(expected_parent_pid=expected_supervisor_pid)
    journal = StageJournal(checkpoint_directory, ordinal=ordinal)
    journal.record("worker_entered")
    memo_receipt: dict[str, Any] | None = None
    model: Any = None
    search: Any = None

    def action() -> None:
        nonlocal memo_receipt, model, search
        stage = "model_construction"
        try:
            model = model_factory(journal.record)
            journal.record("model_constructed")
            stage = "search_construction"
            search = search_factory(journal.record)
            journal.record("search_constructed")
            stage = "runtime"
            journal.record("runtime_entered")
            memo = ExecutionValidationMemo()
            with memo:
                parent = run_single_validation_v24457_task(
                    task,
                    model=model,
                    search=search,
                    partition_seed_sha256=partition_seed_sha256,
                    limits=limits,
                    monotonic=monotonic,
                )
                journal.record("parent_runtime_returned")
                journal.record("adaptive_support_entered")
                outcome = targeted._run_targeted_stage_from_v24457_outcome(
                    parent._trusted_outcome(), model=model, search=search
                )
                journal.record("adaptive_support_returned")
                raw_envelope = _unvalidated_envelope(parent, outcome)
                journal.record("complete_validation_entered")
                envelope = validate_cross_artifacts(raw_envelope)
                journal.record("complete_validation_returned")
                validated = ValidatedTargetedExecution._create(
                    outcome, envelope=envelope
                )
            memo_receipt = validate_memo_receipt(memo.content_free_receipt())
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

        journal.record("artifact_persistence_entered")
        durable_envelope = build_envelope_from_validated_execution(validated)
        artifacts = {
            MODEL_NAME: outcome.model_slot_receipt,
            TRANSPORT_NAME: outcome.transport_health,
            "search_single_shot_receipt.json": outcome.search_single_shot_receipt,
            RESULT_NAME: durable_envelope,
        }
        try:
            for name in (
                MODEL_NAME,
                TRANSPORT_NAME,
                "search_single_shot_receipt.json",
                RESULT_NAME,
            ):
                writer(name, artifacts[name])
            journal.record("certificate_persistence_entered")
            certificate = build_terminal_certificate(
                directory,
                validated,
                memo_receipt=memo_receipt,
                validator_manifest_sha256=validator_manifest_sha256,
                expected_artifacts=artifacts,
            )
            writer(CERTIFICATE_NAME, certificate)
        except BaseException:
            # Durable partial artifacts are already content-free outside the
            # private result.  The child terminal receipt records failure;
            # no overwrite or selective retry is permitted.
            raise

    run_child_with_terminal_receipt(
        output_root=output_root,
        directory=directory,
        action=action,
        result_name=RESULT_NAME,
        model_receipt_name=MODEL_NAME,
        transport_receipt_name=TRANSPORT_NAME,
        terminal_name="child_terminal_receipt.json",
    )
    if memo_receipt is None:
        raise RuntimeError("V2.44.92 validation memo receipt is absent")
    journal.record("worker_complete")
    return dict(memo_receipt)


def supervise_targeted_worker_with_separated_budget(
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
    timeout = remaining_worker_seconds(deadlines, monotonic=monotonic)
    command = append_deadline_origin(worker_command, deadlines)
    return supervise_and_publish(
        ordinal=ordinal,
        cwd=cwd,
        output_root=output_root,
        directory=directory,
        checkpoint_directory=checkpoint_directory,
        command=command,
        timeout_seconds=timeout,
        expected_model_cap=expected_model_cap,
        writer=writer,
    )


def run_targeted_parent_with_separated_budget(
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
    command = append_deadline_origin(supervisor_command, deadlines)
    proof = run_targeted_timed_subprocess(
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
        timeout_seconds=remaining_parent_seconds(deadlines, monotonic=monotonic),
        expected_model_cap=expected_model_cap,
        expected_validator_manifest_sha256=expected_validator_manifest_sha256,
        monotonic=monotonic,
    )
    supervision = _read_supervision_receipt(checkpoint_directory, ordinal=ordinal)
    success = proof.parent_receipt["failure_taxonomy"] == "success"
    if success is not (
        supervision["worker_hard_timeout"] is False
        and supervision["return_code"] == 0
        and supervision["last_stage"] == "worker_complete"
    ):
        raise RuntimeError("V2.44.92 proof/supervision outcome drifted")
    return BoundedAdaptiveParentOutcome(
        proof=proof, supervision_receipt=supervision
    )


__all__ = [
    "POLICY_ID",
    "SUCCESS_SURFACE",
    "failure_projection",
    "run_targeted_parent_with_separated_budget",
    "run_targeted_timed_subprocess",
    "run_targeted_worker",
    "supervise_targeted_worker_with_separated_budget",
    "validate_failure_projection",
]
