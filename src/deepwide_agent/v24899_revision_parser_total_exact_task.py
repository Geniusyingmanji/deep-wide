"""Exact-task envelope bound to the V2.48.98 parser-total integration."""

from __future__ import annotations

import copy
import types
from typing import Any

from . import v24888_revision_envelope_exact_task as frozen
from .v24898_revision_parser_total_integration import (
    validate_integration_receipt,
    validate_result,
)


POLICY_ID = "v24899_revision_parser_total_exact_task_v1"
ENVELOPE_ROLE = "v24899_revision_parser_total_exact_task_envelope"
PARENT_ARM = frozen.PARENT_ARM
IntegratedCoverageRevisionTaskOutcome = frozen.IntegratedCoverageRevisionTaskOutcome


def _isolated_function(original: Any, **bindings: Any) -> Any:
    if original.__closure__:
        raise RuntimeError("V2.48.99 frozen exact-task function has closure state")
    namespace = dict(original.__globals__)
    namespace.update(bindings)
    value = types.FunctionType(
        original.__code__, namespace, name=f"v24899_isolated_{original.__name__}",
        argdefs=original.__defaults__, closure=None,
    )
    value.__kwdefaults__ = copy.deepcopy(original.__kwdefaults__)
    value.__annotations__ = copy.deepcopy(original.__annotations__)
    return value


validate_cross_artifacts = _isolated_function(
    frozen.validate_cross_artifacts,
    validate_result=validate_result,
    validate_integration_receipt=validate_integration_receipt,
)
integrate_parent_outcome = _isolated_function(
    frozen.integrate_parent_outcome,
    validate_cross_artifacts=validate_cross_artifacts,
)
validate_envelope = _isolated_function(
    frozen.validate_envelope,
    POLICY_ID=POLICY_ID,
    ENVELOPE_ROLE=ENVELOPE_ROLE,
    validate_cross_artifacts=validate_cross_artifacts,
)
build_envelope = _isolated_function(
    frozen.build_envelope,
    POLICY_ID=POLICY_ID,
    ENVELOPE_ROLE=ENVELOPE_ROLE,
    validate_cross_artifacts=validate_cross_artifacts,
    validate_envelope=validate_envelope,
)


def validate_isolation() -> None:
    if (
        frozen.validate_cross_artifacts.__globals__["validate_result"]
        is not frozen.validate_result
        or validate_cross_artifacts.__globals__["validate_result"] is not validate_result
        or validate_cross_artifacts.__globals__["validate_integration_receipt"]
        is not validate_integration_receipt
        or validate_envelope.__globals__["validate_cross_artifacts"]
        is not validate_cross_artifacts
        or build_envelope.__globals__["validate_envelope"] is not validate_envelope
    ):
        raise RuntimeError("V2.48.99 isolated exact-task binding drifted")


__all__ = [
    "ENVELOPE_ROLE", "IntegratedCoverageRevisionTaskOutcome", "POLICY_ID",
    "build_envelope", "integrate_parent_outcome", "validate_cross_artifacts",
    "validate_envelope", "validate_isolation",
]
