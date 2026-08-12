"""Task-local, behavior-preserving probes for two frozen receipt validators.

The wrappers compute the pure V2.52.10 disposition first, then call the exact
frozen validator once.  An observation is retained only when that validator
raises its matching static receipt error.  The parent return value or exception
is never converted.  Importing this module does not install either wrapper.
"""

from __future__ import annotations

import copy
import contextvars
import threading
from collections.abc import Mapping
from typing import Any

from . import v25135_sparse_production_runtime as sparse
from . import v25180_quote_aware_production_runtime as quote
from . import v25210_receipt_disposition_observer as observer


POLICY_ID = "v25212_dual_receipt_failure_probe_v1"
SPARSE_FAILURE = "V2.51.35 sparse production receipt drifted"
QUOTE_FAILURE = "V2.51.80 quote-aware receipt drifted"

_FROZEN_SPARSE_VALIDATE = sparse.validate_receipt
_FROZEN_QUOTE_VALIDATE = quote.validate_receipt
_FAILURES: contextvars.ContextVar[dict[str, dict[str, Any]]] = (
    contextvars.ContextVar("v25212_dual_receipt_failures", default={})
)
_INSTALL_LOCK = threading.Lock()
_INSTALLED = False


def begin_task() -> contextvars.Token[dict[str, dict[str, Any]]]:
    return _FAILURES.set({})


def end_task(token: contextvars.Token[dict[str, dict[str, Any]]]) -> None:
    _FAILURES.reset(token)


def failure_observations() -> dict[str, dict[str, Any]]:
    return copy.deepcopy(_FAILURES.get())


def _retain(kind: str, value: Mapping[str, Any]) -> None:
    current = copy.deepcopy(_FAILURES.get())
    current[kind] = copy.deepcopy(dict(value))
    _FAILURES.set(current)


def _observed_sparse_validate(value: Mapping[str, Any]) -> dict[str, Any]:
    disposition: dict[str, Any] | None = None
    try:
        disposition = observer.observe_sparse_receipt(value)
    except BaseException:
        disposition = None
    try:
        return _FROZEN_SPARSE_VALIDATE(value)
    except ValueError as exc:
        if disposition is not None and str(exc) == SPARSE_FAILURE:
            _retain(observer.SPARSE_KIND, disposition)
        raise


def _observed_quote_validate(
    value: Mapping[str, Any],
    *,
    parent_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    disposition: dict[str, Any] | None = None
    try:
        disposition = observer.observe_quote_receipt(value)
    except BaseException:
        disposition = None
    try:
        return _FROZEN_QUOTE_VALIDATE(value, parent_result=parent_result)
    except ValueError as exc:
        if disposition is not None and str(exc) == QUOTE_FAILURE:
            _retain(observer.QUOTE_KIND, disposition)
        raise


def install_probe() -> None:
    global _INSTALLED
    with _INSTALL_LOCK:
        if not _INSTALLED:
            if (
                sparse.validate_receipt is not _FROZEN_SPARSE_VALIDATE
                or quote.validate_receipt is not _FROZEN_QUOTE_VALIDATE
            ):
                raise RuntimeError("V2.52.12 frozen validator identity drifted")
            sparse.validate_receipt = _observed_sparse_validate
            quote.validate_receipt = _observed_quote_validate
            _INSTALLED = True
        elif (
            sparse.validate_receipt is not _observed_sparse_validate
            or quote.validate_receipt is not _observed_quote_validate
        ):
            raise RuntimeError("V2.52.12 installed probe identity drifted")


__all__ = [
    "POLICY_ID",
    "begin_task",
    "end_task",
    "failure_observations",
    "install_probe",
]
