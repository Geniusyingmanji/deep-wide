"""Mapping-recovery bundle bound to the V2.48.88 result envelope.

This append-only successor changes only the exact-task envelope validator and
builder used by V2.48.79.  Artifact names, bytes, effect accounting, mapping
recovery semantics, write ordering, and all query/fetch/model budgets remain
unchanged.
"""

from __future__ import annotations

import copy
import types
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from . import v24879_mapping_recovery_effect_bundle as frozen
from .v24888_revision_envelope_exact_task import (
    IntegratedCoverageRevisionTaskOutcome,
    build_envelope,
    validate_envelope,
)


POLICY_ID = "v24890_revision_envelope_mapping_bundle_v1"
ALL_NAMES = frozen.ALL_NAMES
BACKFILL_NAME = frozen.BACKFILL_NAME
BUNDLE_NAME = frozen.BUNDLE_NAME
COVERAGE_NAME = frozen.COVERAGE_NAME
DATA_NAMES = frozen.DATA_NAMES
EFFECT_NAME = frozen.EFFECT_NAME
FINAL_MODEL_NAME = frozen.FINAL_MODEL_NAME
PARENT_MODEL_NAME = frozen.PARENT_MODEL_NAME
RESULT_NAME = frozen.RESULT_NAME
SINGLE_NAME = frozen.SINGLE_NAME
TRANSPORT_NAME = frozen.TRANSPORT_NAME


def _isolated_function(original: Any, **bindings: Any) -> Any:
    if original.__closure__:
        raise RuntimeError("V2.48.90 frozen bundle function has closure state")
    namespace = dict(original.__globals__)
    namespace.update(bindings)
    value = types.FunctionType(
        original.__code__,
        namespace,
        name=f"v24890_isolated_{original.__name__}",
        argdefs=original.__defaults__,
        closure=None,
    )
    value.__kwdefaults__ = copy.deepcopy(original.__kwdefaults__)
    value.__annotations__ = copy.deepcopy(original.__annotations__)
    return value


_EFFECT_PROJECTION = _isolated_function(
    frozen.frozen._effect_projection,
    validate_envelope=validate_envelope,
)
_EFFECT_VALIDATOR_FROZEN = types.SimpleNamespace(
    _effect_projection=_EFFECT_PROJECTION,
    EFFECT_ROLE=frozen.frozen.EFFECT_ROLE,
    POLICY_ID=frozen.frozen.POLICY_ID,
)
validate_effect_receipt = _isolated_function(
    frozen.validate_effect_receipt,
    frozen=_EFFECT_VALIDATOR_FROZEN,
)
_BUILD_EFFECT_RECEIPT = _isolated_function(
    frozen.frozen.build_effect_receipt,
    _effect_projection=_EFFECT_PROJECTION,
    validate_effect_receipt=validate_effect_receipt,
)
_VALIDATE_VALUES = _isolated_function(
    frozen.frozen._validate_values,
    validate_envelope=validate_envelope,
    validate_effect_receipt=validate_effect_receipt,
)
_VALIDATE_BUNDLE = _isolated_function(
    frozen.frozen.validate_bundle,
    _validate_values=_VALIDATE_VALUES,
)
_WRITE_BUNDLE = _isolated_function(
    frozen.frozen.write_bundle,
    build_envelope=build_envelope,
    build_effect_receipt=_BUILD_EFFECT_RECEIPT,
    _validate_values=_VALIDATE_VALUES,
    validate_bundle=_VALIDATE_BUNDLE,
)


def write_bundle(
    *,
    output_root: Path,
    directory: Path,
    outcome: IntegratedCoverageRevisionTaskOutcome,
    status_counts: Mapping[object, object],
    transport_failures: int,
    hard_total_wall_timeouts: int,
    expected_model_slot_cap: int,
    writer: Callable[[Path, Mapping[str, Any]], None] = frozen.frozen._atomic_new,
) -> dict[str, Any]:
    return _WRITE_BUNDLE(
        output_root=output_root,
        directory=directory,
        outcome=outcome,
        status_counts=status_counts,
        transport_failures=transport_failures,
        hard_total_wall_timeouts=hard_total_wall_timeouts,
        expected_model_slot_cap=expected_model_slot_cap,
        writer=writer,
    )


def validate_bundle(
    *, output_root: Path, directory: Path, expected_model_slot_cap: int
) -> dict[str, Any]:
    return _VALIDATE_BUNDLE(
        output_root=output_root,
        directory=directory,
        expected_model_slot_cap=expected_model_slot_cap,
    )


def validate_isolation() -> None:
    frozen.validate_isolation()
    if (
        frozen.frozen._effect_projection.__globals__["validate_envelope"]
        is not frozen.frozen.validate_envelope
        or _EFFECT_PROJECTION.__globals__["validate_envelope"]
        is not validate_envelope
        or validate_effect_receipt.__globals__["frozen"]
        is not _EFFECT_VALIDATOR_FROZEN
        or _VALIDATE_VALUES.__globals__["validate_envelope"]
        is not validate_envelope
        or _WRITE_BUNDLE.__globals__["build_envelope"] is not build_envelope
        or _WRITE_BUNDLE.__globals__["validate_bundle"] is not _VALIDATE_BUNDLE
        or _WRITE_BUNDLE.__code__ is not frozen.frozen.write_bundle.__code__
    ):
        raise RuntimeError("V2.48.90 isolated bundle binding drifted")


__all__ = [
    "ALL_NAMES",
    "BACKFILL_NAME",
    "BUNDLE_NAME",
    "COVERAGE_NAME",
    "DATA_NAMES",
    "EFFECT_NAME",
    "FINAL_MODEL_NAME",
    "PARENT_MODEL_NAME",
    "POLICY_ID",
    "RESULT_NAME",
    "SINGLE_NAME",
    "TRANSPORT_NAME",
    "validate_bundle",
    "validate_effect_receipt",
    "validate_isolation",
    "write_bundle",
]
