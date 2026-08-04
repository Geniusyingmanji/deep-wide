"""Process-boundary integration for the V2.44.80 separated budget.

This append-only adapter wires one monotonic origin through the existing
proof-carrying parent, worker-group supervisor, and worker command.  Remote
model/search/fetch clients receive only the 150-second effect deadline.  The
supervisor receives the 220-second worker cutoff, and the proof-carrying
parent retains a 245-second cutoff.

The module does not select tasks or inspect task content.  It has no access to
benchmark labels, mapping, gold answers, evaluator state, rewards, scores, or
credentials.  Subprocess execution occurs only when an explicitly supplied
command is passed by a separately audited runner.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from .v24470_bounded_adaptive_integration import (
    BoundedAdaptiveParentOutcome,
    run_bounded_parent_subprocess,
    supervise_and_publish,
)
from .v24480_separated_effect_validation_budget import (
    PARENT_TOTAL_SECONDS,
    POLICY_ID as BUDGET_POLICY_ID,
    REMOTE_EFFECT_SECONDS,
    WORKER_TOTAL_SECONDS,
    PhaseDeadlines,
    build_phase_deadlines,
    remaining_parent_seconds,
    remaining_remote_effect_seconds,
    remaining_worker_seconds,
    validate_phase_deadlines,
)


POLICY_ID = "v24482_separated_budget_worker_integration_v1"
DEADLINE_ORIGIN_ARGUMENT = "--deadline-origin-monotonic"


def _finite(value: object, *, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float, str))
    ):
        raise ValueError(f"V2.44.82 {label} is invalid")
    try:
        converted = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"V2.44.82 {label} is invalid") from error
    if not math.isfinite(converted):
        raise ValueError(f"V2.44.82 {label} is invalid")
    return converted


def deadlines_from_origin(value: object) -> PhaseDeadlines:
    return build_phase_deadlines(origin=_finite(value, label="deadline origin"))


def append_deadline_origin(
    command: Sequence[str], deadlines: PhaseDeadlines
) -> list[str]:
    validated = validate_phase_deadlines(deadlines)
    copied = [str(item) for item in command]
    if (
        not copied
        or any(not item for item in copied)
        or DEADLINE_ORIGIN_ARGUMENT in copied
    ):
        raise ValueError("V2.44.82 command surface is invalid")
    return [*copied, DEADLINE_ORIGIN_ARGUMENT, repr(validated.origin)]


def remote_effect_deadline(
    deadline_origin: object,
    *,
    monotonic: Callable[[], float] = time.monotonic,
) -> float:
    deadlines = deadlines_from_origin(deadline_origin)
    remaining_remote_effect_seconds(deadlines, monotonic=monotonic)
    return deadlines.remote_effect


def supervise_worker_with_separated_budget(
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
    """Apply only the worker deadline to an already-frozen worker command."""

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
    """Start one bounded parent with the shared frozen deadline origin."""

    deadlines = build_phase_deadlines(monotonic=monotonic)
    command = append_deadline_origin(supervisor_command, deadlines)
    timeout = remaining_parent_seconds(deadlines, monotonic=monotonic)
    return run_bounded_parent_subprocess(
        ordinal=ordinal,
        cwd=cwd,
        output_root=output_root,
        directory=directory,
        checkpoint_directory=checkpoint_directory,
        command=command,
        parent_timeout_seconds=timeout,
        expected_model_cap=expected_model_cap,
        expected_validator_manifest_sha256=expected_validator_manifest_sha256,
    )


def integration_contract() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "budget_policy_id": BUDGET_POLICY_ID,
        "deadline_origin_argument": DEADLINE_ORIGIN_ARGUMENT,
        "remote_effect_seconds": REMOTE_EFFECT_SECONDS,
        "worker_total_seconds": WORKER_TOTAL_SECONDS,
        "parent_total_seconds": PARENT_TOTAL_SECONDS,
        "one_monotonic_origin_crosses_parent_supervisor_worker_boundaries": True,
        "remote_clients_receive_only_remote_effect_deadline": True,
        "worker_group_cutoff_excludes_parent_closure_reserve": True,
        "parent_cutoff_includes_final_closure_reserve": True,
        "task_question_opaque_id_query_url_page_prediction_or_value_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }


__all__ = [
    "DEADLINE_ORIGIN_ARGUMENT",
    "POLICY_ID",
    "append_deadline_origin",
    "deadlines_from_origin",
    "integration_contract",
    "remote_effect_deadline",
    "run_parent_with_separated_budget",
    "supervise_worker_with_separated_budget",
]
