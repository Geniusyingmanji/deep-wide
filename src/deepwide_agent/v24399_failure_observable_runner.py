"""Failure-observable integration for the V2.43.91 uncertainty runner.

The successful algorithm is unchanged.  On construction/runtime failure this
wrapper snapshots only already-content-free receipts before re-raising, so the
existing child terminal receipt remains the final artifact.  Parent-side
projection reads no task, query, URL, page, response, prediction, or result.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .v24257_score_first_runtime import ScoreFirstLimits
from .v24280_task_union_single_shot import validate_receipt as validate_search_receipt
from .v24308_child_exit_observability import (
    validate_child_receipt,
    validate_parent_receipt,
)
from .v24312_deadline_reliability import validate_receipt as validate_model_receipt
from .v24316_deadline_search import validate_transport_health
from .v24391_uncertainty_active_evidence_runner import (
    IntegratedUncertaintyActiveEvidenceOutcome,
    build_envelope,
    run_v24391_task,
    validate_envelope,
)
from .v24397_failure_observability import (
    build_failure_snapshot,
    build_task_observation,
    validate_failure_snapshot,
    validate_task_observation,
)


POLICY_ID = "v24399_failure_observable_uncertainty_runner_v1"
RESULT_NAME = "result.json"
MODEL_NAME = "model_slot_receipt.json"
TRANSPORT_NAME = "transport_health.json"
SEARCH_NAME = "search_single_shot_receipt.json"
FAILURE_NAME = "failure_snapshot.json"
CHILD_NAME = "child_terminal_receipt.json"
PARENT_NAME = "parent_exit_receipt.json"
ARTIFACT_NAMES = frozenset(
    {
        RESULT_NAME,
        MODEL_NAME,
        TRANSPORT_NAME,
        SEARCH_NAME,
        FAILURE_NAME,
        CHILD_NAME,
        PARENT_NAME,
    }
)


def _capture_model(model: Any, expected_cap: int) -> dict[str, Any] | None:
    if model is None or not callable(getattr(model, "receipt", None)):
        return None
    try:
        value = model.receipt()
        return validate_model_receipt(dict(value), expected_cap=expected_cap)
    except (KeyError, RuntimeError, TypeError, ValueError):
        return None


def _capture_transport(search: Any) -> dict[str, Any] | None:
    if search is None or not callable(getattr(search, "transport_health", None)):
        return None
    try:
        return validate_transport_health(search.transport_health())
    except (KeyError, RuntimeError, TypeError, ValueError):
        return None


def _capture_search(search: Any) -> dict[str, Any] | None:
    if search is None or not callable(getattr(search, "single_shot_receipt", None)):
        return None
    try:
        value = dict(search.single_shot_receipt())
        validate_search_receipt(value)
        return value
    except (KeyError, RuntimeError, TypeError, ValueError):
        return None


def persist_failure_artifacts(
    error: BaseException,
    *,
    failure_stage: str,
    model: Any,
    search: Any,
    expected_model_cap: int,
    writer: Callable[[str, Mapping[str, Any]], None],
) -> dict[str, Any]:
    """Persist content-free lower-bound effects and one bound snapshot."""

    model_receipt = _capture_model(model, expected_model_cap)
    transport = _capture_transport(search)
    search_receipt = _capture_search(search)
    snapshot = build_failure_snapshot(
        error,
        failure_stage=failure_stage,
        model_receipt=model_receipt,
        transport_health=transport,
        search_receipt=search_receipt,
        expected_model_cap=expected_model_cap,
    )
    if model_receipt is not None:
        writer(MODEL_NAME, model_receipt)
    if transport is not None:
        writer(TRANSPORT_NAME, transport)
    if search_receipt is not None:
        writer(SEARCH_NAME, search_receipt)
    writer(FAILURE_NAME, snapshot)
    return snapshot


def run_and_persist_uncertainty_task(
    task: Mapping[str, Any],
    *,
    model_factory: Callable[[], Any],
    search_factory: Callable[[], Any],
    partition_seed_sha256: str,
    limits: ScoreFirstLimits,
    monotonic: Callable[[], float],
    expected_model_cap: int,
    writer: Callable[[str, Mapping[str, Any]], None],
) -> IntegratedUncertaintyActiveEvidenceOutcome:
    """Run unchanged V2.43.91 and persist exact or partial receipts."""

    model: Any = None
    search: Any = None
    stage = "model_construction"
    try:
        model = model_factory()
        stage = "search_construction"
        search = search_factory()
        stage = "runtime"
        outcome = run_v24391_task(
            task,
            model=model,
            search=search,
            partition_seed_sha256=partition_seed_sha256,
            limits=limits,
            monotonic=monotonic,
        )
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

    envelope = build_envelope(outcome)
    validate_envelope(envelope)
    # Result is written last.  A mid-serialization failure binds exactly the
    # independent receipts that were already made durable, never hypothetical
    # effects that existed only in memory.
    model_written = False
    transport_written = False
    search_written = False
    try:
        writer(MODEL_NAME, outcome.model_slot_receipt)
        model_written = True
        writer(TRANSPORT_NAME, outcome.transport_health)
        transport_written = True
        writer(SEARCH_NAME, outcome.search_single_shot_receipt)
        search_written = True
        writer(RESULT_NAME, envelope)
    except BaseException as error:
        snapshot = build_failure_snapshot(
            error,
            failure_stage="artifact_serialization",
            model_receipt=(outcome.model_slot_receipt if model_written else None),
            transport_health=(outcome.transport_health if transport_written else None),
            search_receipt=(
                outcome.search_single_shot_receipt if search_written else None
            ),
            expected_model_cap=expected_model_cap,
        )
        writer(FAILURE_NAME, snapshot)
        raise
    return outcome


def _ordinary_directory(directory: Path) -> Path:
    if directory.is_symlink() or not directory.is_dir():
        raise RuntimeError("V2.43.99 task directory is not ordinary")
    return directory.resolve()


def _read_optional(directory: Path, name: str) -> dict[str, Any] | None:
    if name not in ARTIFACT_NAMES:
        raise ValueError("V2.43.99 artifact name is not allowed")
    base = _ordinary_directory(directory)
    path = directory / name
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(base):
        raise RuntimeError("V2.43.99 artifact is not an ordinary task file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.43.99 artifact is not an object")
    return value


def build_directory_observation(
    ordinal: int,
    parent: Mapping[str, Any],
    *,
    directory: Path,
    expected_model_cap: int,
) -> dict[str, Any]:
    """Project only content-free exit and effect artifacts from one task."""

    validated_parent = validate_parent_receipt(parent)
    child_raw = _read_optional(directory, CHILD_NAME)
    child = validate_child_receipt(child_raw) if child_raw is not None else None

    model_raw = _read_optional(directory, MODEL_NAME)
    model = None
    if model_raw is not None and validated_parent["model_receipt_valid"]:
        model = validate_model_receipt(
            model_raw, expected_cap=expected_model_cap
        )

    transport_raw = _read_optional(directory, TRANSPORT_NAME)
    transport = None
    if transport_raw is not None and validated_parent["transport_receipt_valid"]:
        transport = validate_transport_health(transport_raw)

    search_raw = _read_optional(directory, SEARCH_NAME)
    search = None
    if search_raw is not None:
        validate_search_receipt(search_raw)
        search = search_raw

    failure_raw = _read_optional(directory, FAILURE_NAME)
    failure = None
    if failure_raw is not None:
        failure = validate_failure_snapshot(
            failure_raw,
            model_receipt=model,
            transport_health=transport,
            search_receipt=search,
            expected_model_cap=expected_model_cap,
        )

    value = build_task_observation(
        ordinal,
        validated_parent,
        child=child,
        failure_snapshot=failure,
        model_receipt=model,
        transport_health=transport,
        search_receipt=search,
        expected_model_cap=expected_model_cap,
    )
    validate_task_observation(value)
    return value


__all__ = [
    "ARTIFACT_NAMES",
    "CHILD_NAME",
    "FAILURE_NAME",
    "MODEL_NAME",
    "PARENT_NAME",
    "POLICY_ID",
    "RESULT_NAME",
    "SEARCH_NAME",
    "TRANSPORT_NAME",
    "build_directory_observation",
    "persist_failure_artifacts",
    "run_and_persist_uncertainty_task",
]
