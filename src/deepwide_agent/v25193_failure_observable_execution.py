"""Single-pass staged execution with content-free outer failure receipts.

This helper adds no retries, effects, routing, or policy.  It only separates
the runtime, conversion, and final row-validation boundaries so an outer
failure can be converted to one terminal failure row with the V2.51.92 finite
receipt.  The original exception object is never passed to the row factory.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, TypeVar

from . import v25192_content_free_outer_failure_observer as observer


RawT = TypeVar("RawT")
RowT = TypeVar("RowT", bound=Mapping[str, Any])


def execute_staged_once(
    *,
    runtime_stage: Callable[[], RawT],
    conversion_stage: Callable[[RawT], RowT],
    row_validation_stage: Callable[[RowT], RowT],
    terminal_failure_factory: Callable[[Mapping[str, Any]], RowT],
) -> RowT:
    """Execute each success stage once and fail closed to one terminal row."""

    if not all(
        callable(value)
        for value in (
            runtime_stage,
            conversion_stage,
            row_validation_stage,
            terminal_failure_factory,
        )
    ):
        raise TypeError("V2.51.93 staged execution requires callables")

    def terminal(exc: BaseException, stage: str) -> RowT:
        receipt = observer.observe_outer_failure(
            exc, outer_failure_stage=stage
        )
        # The raw exception deliberately does not cross this boundary.
        failure = terminal_failure_factory(receipt)
        return row_validation_stage(failure)

    try:
        raw = runtime_stage()
    except BaseException as exc:
        return terminal(exc, "runtime")
    try:
        row = conversion_stage(raw)
    except BaseException as exc:
        return terminal(exc, "conversion")
    try:
        return row_validation_stage(row)
    except BaseException as exc:
        return terminal(exc, "row_validation")


__all__ = ["execute_staged_once"]
