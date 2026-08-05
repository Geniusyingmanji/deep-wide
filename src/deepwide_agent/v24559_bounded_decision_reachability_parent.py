"""Bounded parent for V2.45.57--58 decision-reachability evidence.

Remote-effect, worker, parent, and batch ceilings remain 150, 220, 245, and
255 seconds from one monotonic origin.  A successful task validates exactly one
V2.45.57 capability and projects it exactly once through V2.45.58.  Failure
tasks retain effect lower bounds and receive the exact content-free failure row.
"""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v24552_bounded_alias_joint_parent as parent
from . import v24557_proof_carrying_decision_reachability as proof
from . import v24558_total_decision_reachability_projection as total
from .v24308_child_exit_observability import validate_parent_receipt
from .v24309_runner_exit_integration import run_observed_subprocess
from .v24312_deadline_reliability import validate_receipt as validate_model_receipt
from .v24316_deadline_search import validate_transport_health
from .v24397_failure_observability import build_task_observation
from .v24399_failure_observable_runner import (
    MODEL_NAME,
    PARENT_NAME,
    RESULT_NAME,
    TRANSPORT_NAME,
    build_directory_observation,
)
from .v24461_proof_carrying_adaptive_timed_runner import (
    ProofCarryingAdaptiveTimedOutcome,
    build_timing_receipt,
)
from .v24470_bounded_adaptive_integration import (
    BoundedAdaptiveParentOutcome,
    _read_supervision_receipt,
)
from .v24480_separated_effect_validation_budget import (
    BATCH_WALL_CEILING_SECONDS,
    PARENT_TOTAL_SECONDS,
    REMOTE_EFFECT_SECONDS,
    WORKER_TOTAL_SECONDS,
    build_phase_deadlines,
    remaining_parent_seconds,
)
from .v24482_separated_budget_worker_integration import append_deadline_origin


POLICY_ID = "v24559_bounded_decision_reachability_parent_v1"
run_worker = proof.run_worker
supervise_worker_with_separated_budget = proof.supervise_worker_with_separated_budget


def run_timed_subprocess(
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
    capabilities: list[proof.ValidatedProofCarryingDecisionReachability] = []
    child_wall = 0.0
    child_started = 0.0
    certificate_wall = 0.0
    certificate_invocations = 0

    def result_validator(value: Mapping[str, Any]) -> object:
        nonlocal certificate_invocations, certificate_wall
        certificate_invocations += 1
        started = monotonic()
        try:
            capability = proof.validate_proof_carrying_decision_reachability_bundle(
                value,
                ordinal=ordinal,
                directory=directory,
                output_root=output_root,
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
    parent_receipt = validate_parent_receipt(outcome.receipt)
    success = parent_receipt["failure_taxonomy"] == "success"
    observation_started = monotonic()
    capability_observation = False
    failure_lower_bound = False
    try:
        if success:
            if certificate_invocations != 1 or len(capabilities) != 1:
                raise RuntimeError("V2.45.59 success lacks one capability")
            parent.bounded_parent._validate_success_surface(directory)
            receipts = capabilities[0].content_free_observation_receipts()
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

    projection = total.failure_projection(ordinal)
    projection_wall = 0.0
    projection_invocations = 0
    capability_projection = False
    if success:
        projection_invocations = 1
        started = monotonic()
        try:
            projection = total.task_projection(ordinal, capabilities[0])
            capability_projection = True
        finally:
            projection_wall = max(0.0, monotonic() - started)
    total.validate_total_row(projection)
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


def run_parent_with_separated_budget(
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
    timed = run_timed_subprocess(
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
        timeout_seconds=remaining_parent_seconds(deadlines, monotonic=monotonic),
        expected_model_cap=expected_model_cap,
        expected_validator_manifest_sha256=expected_validator_manifest_sha256,
        monotonic=monotonic,
    )
    supervision = _read_supervision_receipt(
        checkpoint_directory, ordinal=ordinal
    )
    success = timed.parent_receipt["failure_taxonomy"] == "success"
    if success is not (
        supervision["worker_hard_timeout"] is False
        and supervision["return_code"] == 0
        and supervision["last_stage"] == "worker_complete"
    ):
        raise RuntimeError("V2.45.59 proof/supervision outcome drifted")
    return BoundedAdaptiveParentOutcome(
        proof=timed, supervision_receipt=supervision
    )


def budget_vector_seconds() -> tuple[float, float, float, float]:
    value = (
        REMOTE_EFFECT_SECONDS,
        WORKER_TOTAL_SECONDS,
        PARENT_TOTAL_SECONDS,
        BATCH_WALL_CEILING_SECONDS,
    )
    if value != (150.0, 220.0, 245.0, 255.0):
        raise RuntimeError("V2.45.59 inherited budget vector drifted")
    return value


__all__ = [
    "POLICY_ID",
    "budget_vector_seconds",
    "run_parent_with_separated_budget",
    "run_timed_subprocess",
    "run_worker",
    "supervise_worker_with_separated_budget",
]
