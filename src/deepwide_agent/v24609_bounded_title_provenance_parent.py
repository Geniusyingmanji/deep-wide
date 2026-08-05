"""Bounded parent for V2.46.07--08 title provenance observability.

The audited V2.46.01 parent functions are copied with private frozen globals.
Only the proof validator/worker and total projection bindings differ.  The
inherited effect, worker, parent, and batch ceilings remain 150, 220, 245, and
255 seconds from one origin.
"""

from __future__ import annotations

from types import FunctionType
from typing import Any, Callable

from . import v24601_bounded_title_funnel_parent as frozen
from . import v24607_proof_carrying_title_provenance as proof
from . import v24608_total_title_provenance_projection as total


POLICY_ID = "v24609_bounded_content_free_title_provenance_parent_v1"
run_worker = proof.run_worker
supervise_worker_with_separated_budget = proof.supervise_worker_with_separated_budget


def _frozen_function(
    function: Callable[..., Any], **overrides: Any
) -> Callable[..., Any]:
    if not isinstance(function, FunctionType) or function.__closure__ is not None:
        raise TypeError("V2.46.09 requires a closure-free Python function")
    namespace = dict(function.__globals__)
    namespace.update(overrides)
    copied = FunctionType(
        function.__code__,
        namespace,
        name=function.__name__,
        argdefs=function.__defaults__,
        closure=None,
    )
    copied.__kwdefaults__ = dict(function.__kwdefaults__ or {})
    copied.__annotations__ = dict(function.__annotations__)
    copied.__doc__ = function.__doc__
    copied.__module__ = __name__
    return copied


run_timed_subprocess = _frozen_function(
    frozen.run_timed_subprocess,
    proof=proof,
    total=total,
)
run_parent_with_separated_budget = _frozen_function(
    frozen.run_parent_with_separated_budget,
    run_timed_subprocess=run_timed_subprocess,
)


def budget_vector_seconds() -> tuple[float, float, float, float]:
    value = frozen.budget_vector_seconds()
    if value != (150.0, 220.0, 245.0, 255.0):
        raise RuntimeError("V2.46.09 inherited budget vector drifted")
    return value


def binding_is_private_and_stable() -> bool:
    return (
        run_timed_subprocess is not frozen.run_timed_subprocess
        and run_timed_subprocess.__globals__["proof"] is proof
        and run_timed_subprocess.__globals__["total"] is total
        and frozen.run_timed_subprocess.__globals__["proof"] is not proof
        and frozen.run_timed_subprocess.__globals__["total"] is not total
        and run_parent_with_separated_budget.__globals__["run_timed_subprocess"]
        is run_timed_subprocess
        and frozen.run_parent_with_separated_budget.__globals__["run_timed_subprocess"]
        is frozen.run_timed_subprocess
    )


if not binding_is_private_and_stable():
    raise RuntimeError("V2.46.09 private frozen binding drifted")


__all__ = [
    "POLICY_ID",
    "binding_is_private_and_stable",
    "budget_vector_seconds",
    "run_parent_with_separated_budget",
    "run_timed_subprocess",
    "run_worker",
    "supervise_worker_with_separated_budget",
]
