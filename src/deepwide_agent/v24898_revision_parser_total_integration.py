"""V2.48.87 integration with total parent-valid parser passthrough."""

from __future__ import annotations

import copy
import types
from collections.abc import Mapping
from typing import Any

from . import v24887_revision_envelope_integration as frozen
from .v24897_revision_parser_totality import (
    apply_full_evidence_revision,
    revision_envelope_eligible,
    validate_receipt as validate_coverage_receipt,
)


POLICY_ID = "v24898_revision_parser_total_integration_v1"
RESULT_ROLE = "v24898_revision_parser_total_task_result"
RECEIPT_ROLE = "v24898_revision_parser_total_integration_receipt"
DISPOSITIONS = frozen.DISPOSITIONS
CoverageRevisionOutcome = frozen.CoverageRevisionOutcome


def _isolated_function(original: Any, **bindings: Any) -> Any:
    if original.__closure__:
        raise RuntimeError("V2.48.98 frozen integration function has closure state")
    namespace = dict(original.__globals__)
    namespace.update(bindings)
    value = types.FunctionType(
        original.__code__, namespace,
        name=f"v24898_isolated_{original.__name__}",
        argdefs=original.__defaults__, closure=None,
    )
    value.__kwdefaults__ = copy.deepcopy(original.__kwdefaults__)
    value.__annotations__ = copy.deepcopy(original.__annotations__)
    return value


def _parent_eligible(parent: Mapping[str, Any]) -> bool:
    return bool(
        frozen.frozen._parent_eligible(parent)
        and revision_envelope_eligible(str(parent.get("prediction") or ""))
    )


validate_integration_receipt = _isolated_function(
    frozen.validate_integration_receipt,
    POLICY_ID=POLICY_ID,
    RECEIPT_ROLE=RECEIPT_ROLE,
    validate_coverage_receipt=validate_coverage_receipt,
)
_BUILD_RECEIPT = _isolated_function(
    frozen._BUILD_RECEIPT,
    POLICY_ID=POLICY_ID,
    RECEIPT_ROLE=RECEIPT_ROLE,
    validate_integration_receipt=validate_integration_receipt,
)
_IDENTITY_COVERAGE = _isolated_function(
    frozen._IDENTITY_COVERAGE,
    apply_full_evidence_revision=apply_full_evidence_revision,
)
_RESULT_PROJECTION = _isolated_function(
    frozen._RESULT_PROJECTION,
    POLICY_ID=POLICY_ID,
    RESULT_ROLE=RESULT_ROLE,
)
validate_result = _isolated_function(
    frozen.validate_result,
    POLICY_ID=POLICY_ID,
    RESULT_ROLE=RESULT_ROLE,
    validate_integration_receipt=validate_integration_receipt,
    _result_projection=_RESULT_PROJECTION,
)
run_coverage_revision = _isolated_function(
    frozen.run_coverage_revision,
    POLICY_ID=POLICY_ID,
    _parent_eligible=_parent_eligible,
    _identity_coverage=_IDENTITY_COVERAGE,
    _build_receipt=_BUILD_RECEIPT,
    apply_full_evidence_revision=apply_full_evidence_revision,
    _result_projection=_RESULT_PROJECTION,
    validate_result=validate_result,
)


def validate_isolation() -> None:
    if (
        frozen.run_coverage_revision.__globals__["_parent_eligible"]
        is not frozen._parent_eligible
        or run_coverage_revision.__globals__["_parent_eligible"]
        is not _parent_eligible
        or run_coverage_revision.__globals__["_identity_coverage"]
        is not _IDENTITY_COVERAGE
        or run_coverage_revision.__globals__["validate_result"] is not validate_result
        or run_coverage_revision.__code__ is not frozen.run_coverage_revision.__code__
    ):
        raise RuntimeError("V2.48.98 isolated integration binding drifted")


__all__ = [
    "CoverageRevisionOutcome", "DISPOSITIONS", "POLICY_ID", "RECEIPT_ROLE",
    "RESULT_ROLE", "run_coverage_revision", "validate_integration_receipt",
    "validate_isolation", "validate_result",
]
