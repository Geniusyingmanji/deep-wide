"""Keyless fixed-budget runtime bound to the parser-total revision seam."""

from __future__ import annotations

import copy
import types
from typing import Any

from . import v24889_revision_envelope_runtime as frozen
from .v24898_revision_parser_total_integration import run_coverage_revision
from .v24899_revision_parser_total_exact_task import integrate_parent_outcome


POLICY_ID = "v24900_revision_parser_total_keyless_runtime_v1"
PAGE_ATTRIBUTE = frozen.PAGE_ATTRIBUTE
KeylessFixedCoverageCachingSearchClient = frozen.KeylessFixedCoverageCachingSearchClient


def _isolated_function(original: Any, **bindings: Any) -> Any:
    if original.__closure__:
        raise RuntimeError("V2.49.00 frozen runtime function has closure state")
    namespace = dict(original.__globals__)
    namespace.update(bindings)
    value = types.FunctionType(
        original.__code__, namespace, name=f"v24900_isolated_{original.__name__}",
        argdefs=original.__defaults__, closure=None,
    )
    value.__kwdefaults__ = copy.deepcopy(original.__kwdefaults__)
    value.__annotations__ = copy.deepcopy(original.__annotations__)
    return value


run_v24900_task = _isolated_function(
    frozen.run_v24889_task,
    POLICY_ID=POLICY_ID,
    run_coverage_revision=run_coverage_revision,
    integrate_parent_outcome=integrate_parent_outcome,
    validate_isolation=lambda: frozen.frozen.validate_isolation(),
)


def validate_isolation() -> None:
    frozen.validate_isolation()
    if (
        frozen.run_v24889_task.__globals__["run_coverage_revision"]
        is not frozen.run_coverage_revision
        or run_v24900_task.__globals__["run_coverage_revision"]
        is not run_coverage_revision
        or run_v24900_task.__globals__["integrate_parent_outcome"]
        is not integrate_parent_outcome
        or run_v24900_task.__code__ is not frozen.run_v24889_task.__code__
    ):
        raise RuntimeError("V2.49.00 isolated runtime binding drifted")


__all__ = [
    "KeylessFixedCoverageCachingSearchClient", "PAGE_ATTRIBUTE", "POLICY_ID",
    "run_v24900_task", "validate_isolation",
]
