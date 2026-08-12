"""Thread-local, behavior-preserving probe for frozen V2.51.58 validation.

Installation replaces the module-level validator with a wrapper that first
computes a pure V2.51.96 observation and then calls the exact frozen validator
once.  Only when the frozen validator raises its static aggregate error is the
content-free observation retained in the current task context.  The original
return value or exception is preserved.
"""

from __future__ import annotations

import copy
import contextvars
import threading
from collections.abc import Mapping
from typing import Any

from . import v25158_vertical_key_value_candidate_runtime as parent
from . import v25196_vertical_receipt_invariant_observer as observer


_FROZEN_VALIDATE = parent.validate_receipt
_FAILURE: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "v25197_vertical_receipt_failure", default=None
)
_INSTALL_LOCK = threading.Lock()
_INSTALLED = False


def begin_task() -> contextvars.Token[dict[str, Any] | None]:
    return _FAILURE.set(None)


def end_task(token: contextvars.Token[dict[str, Any] | None]) -> None:
    _FAILURE.reset(token)


def failure_observation() -> dict[str, Any] | None:
    value = _FAILURE.get()
    return copy.deepcopy(value) if value is not None else None


def _observed_validate(value: Mapping[str, Any]) -> dict[str, Any]:
    disposition: dict[str, Any] | None = None
    try:
        disposition = observer.observe_receipt_invariants(value)
    except BaseException:
        # Observability is strictly subordinate to the frozen validator.
        disposition = None
    try:
        return _FROZEN_VALIDATE(value)
    except ValueError as exc:
        if (
            disposition is not None
            and str(exc)
            == "V2.51.58 vertical key-value candidate receipt drifted"
        ):
            _FAILURE.set(disposition)
        raise


def install_probe() -> None:
    global _INSTALLED
    with _INSTALL_LOCK:
        if not _INSTALLED:
            if parent.validate_receipt is not _FROZEN_VALIDATE:
                raise RuntimeError("V2.51.97 frozen validator identity drifted")
            parent.validate_receipt = _observed_validate
            _INSTALLED = True
        elif parent.validate_receipt is not _observed_validate:
            raise RuntimeError("V2.51.97 installed probe identity drifted")


__all__ = [
    "begin_task",
    "end_task",
    "failure_observation",
    "install_probe",
]
