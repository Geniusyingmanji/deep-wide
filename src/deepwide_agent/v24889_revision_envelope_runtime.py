"""V2.48.73 runtime bound to revision-envelope-aware integration."""

from __future__ import annotations

import copy
import types
from typing import Any

from . import v24873_keyless_fixed_coverage_runtime as frozen
from .v24887_revision_envelope_integration import run_coverage_revision
from .v24888_revision_envelope_exact_task import integrate_parent_outcome


POLICY_ID = "v24889_revision_envelope_aware_keyless_runtime_v1"
PAGE_ATTRIBUTE = frozen.PAGE_ATTRIBUTE
KeylessFixedCoverageCachingSearchClient = frozen.KeylessFixedCoverageCachingSearchClient


def _isolated_function(original: Any, **bindings: Any) -> Any:
    if original.__closure__:
        raise RuntimeError("V2.48.89 frozen runtime function has closure state")
    namespace = dict(original.__globals__)
    namespace.update(bindings)
    value = types.FunctionType(
        original.__code__, namespace, name=f"v24889_isolated_{original.__name__}",
        argdefs=original.__defaults__, closure=None,
    )
    value.__kwdefaults__ = copy.deepcopy(original.__kwdefaults__)
    value.__annotations__ = copy.deepcopy(original.__annotations__)
    return value


def validate_isolation() -> None:
    frozen.validate_isolation()
    if (
        frozen.run_v24873_task.__globals__["run_coverage_revision"]
        is not frozen.run_coverage_revision
        or run_v24889_task.__globals__["run_coverage_revision"]
        is not run_coverage_revision
        or run_v24889_task.__globals__["integrate_parent_outcome"]
        is not integrate_parent_outcome
    ):
        raise RuntimeError("V2.48.89 isolated runtime binding drifted")


run_v24889_task = _isolated_function(
    frozen.run_v24873_task,
    POLICY_ID=POLICY_ID,
    run_coverage_revision=run_coverage_revision,
    integrate_parent_outcome=integrate_parent_outcome,
    validate_isolation=lambda: frozen.validate_isolation(),
)


__all__ = [
    "KeylessFixedCoverageCachingSearchClient",
    "PAGE_ATTRIBUTE",
    "POLICY_ID",
    "run_v24889_task",
    "validate_isolation",
]
