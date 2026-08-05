"""Bounded parent for the V2.45.64 strict conversion joint.

The audited V2.45.62 functions are copied with private frozen globals.  Only
the projection module and the parent-to-timed-function binding differ.  No
module global is mutated, so concurrent parents share no patch context and the
V2.45.62 projector remains byte-for-byte and identity stable.
"""

from __future__ import annotations

from types import FunctionType
from typing import Any, Callable

from . import v24562_bounded_reachability_conversion_joint_parent as parent
from . import v24564_strict_reachability_conversion_joint as total


POLICY_ID = "v24565_bounded_strict_reachability_conversion_parent_v1"
run_worker = parent.run_worker
supervise_worker_with_separated_budget = parent.supervise_worker_with_separated_budget


def _frozen_function(
    function: Callable[..., Any], **overrides: Any
) -> Callable[..., Any]:
    if not isinstance(function, FunctionType) or function.__closure__ is not None:
        raise TypeError("V2.45.65 requires a closure-free Python function")
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


run_timed_subprocess = _frozen_function(parent.run_timed_subprocess, total=total)
run_parent_with_separated_budget = _frozen_function(
    parent.run_parent_with_separated_budget,
    run_timed_subprocess=run_timed_subprocess,
)


def budget_vector_seconds() -> tuple[float, float, float, float]:
    value = parent.budget_vector_seconds()
    if value != (150.0, 220.0, 245.0, 255.0):
        raise RuntimeError("V2.45.65 inherited budget vector drifted")
    return value


def binding_is_private_and_stable() -> bool:
    return (
        run_timed_subprocess is not parent.run_timed_subprocess
        and run_timed_subprocess.__globals__["total"] is total
        and parent.run_timed_subprocess.__globals__["total"] is not total
        and run_parent_with_separated_budget.__globals__["run_timed_subprocess"]
        is run_timed_subprocess
        and parent.run_parent_with_separated_budget.__globals__[
            "run_timed_subprocess"
        ]
        is parent.run_timed_subprocess
    )


if not binding_is_private_and_stable():
    raise RuntimeError("V2.45.65 private frozen binding drifted")


__all__ = [
    "POLICY_ID",
    "binding_is_private_and_stable",
    "budget_vector_seconds",
    "run_parent_with_separated_budget",
    "run_timed_subprocess",
    "run_worker",
    "supervise_worker_with_separated_budget",
]
