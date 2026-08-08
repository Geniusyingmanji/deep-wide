"""Response-aware validator for the frozen V2.48.63 bundle format.

V2.48.63 incorrectly equated logical search queries with HTTP responses.  A
logical query can fail before a provider request, or it can receive multiple
responses while retrying.  This append-only successor keeps the committed
bundle byte format and every frozen artifact validator, but replaces that one
cross-artifact equation with the actual counter semantics:

* logical queries equal terminal successful plus failed logical queries;
* parent search calls equal direct-search HTTP status responses;
* parent search failures equal terminal failed logical queries;
* parent fetch calls equal retrieval fetch attempts; and
* provider attempts equal provider-gate start reservations.

The frozen module is not monkey patched.  Its closure-free functions are
cloned with isolated globals that bind only the corrected runtime equation.
This module has no benchmark, evaluator, environment, process, credential, or
network capability.
"""

from __future__ import annotations

import copy
import math
import types
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

from . import v24863_coverage_revision_child_bundle as frozen
from .v24796_deadline_tavily_search import STATUS_BUCKETS
from .v24861_coverage_revision_exact_task import (
    IntegratedCoverageRevisionTaskOutcome,
)


POLICY_ID = "v24867_response_aware_coverage_bundle_validator_v1"

ALL_NAMES = frozen.ALL_NAMES
BACKFILL_NAME = frozen.BACKFILL_NAME
BUNDLE_NAME = frozen.BUNDLE_NAME
COVERAGE_NAME = frozen.COVERAGE_NAME
DATA_NAMES = frozen.DATA_NAMES
DIRECT_NAME = frozen.DIRECT_NAME
FINAL_MODEL_NAME = frozen.FINAL_MODEL_NAME
PACING_NAME = frozen.PACING_NAME
PARENT_MODEL_NAME = frozen.PARENT_MODEL_NAME
RATE_NAME = frozen.RATE_NAME
RESULT_NAME = frozen.RESULT_NAME
SINGLE_NAME = frozen.SINGLE_NAME
TRANSPORT_NAME = frozen.TRANSPORT_NAME


def _nonnegative_integer(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.48.67 {label} is not a nonnegative integer")
    return value


def _runtime_binding(
    envelope: Mapping[str, Any],
    *,
    direct: Mapping[str, Any],
    rate: Mapping[str, Any],
    pacing: Mapping[str, Any],
    expected_model_slot_cap: int,
    expected_tavily_key_slot_cap: int,
) -> None:
    """Bind logical, response, attempt, and fetch counters without aliasing."""

    result = envelope["result"]
    parent = result["parent_result"]
    retrieval = parent.get("two_wave_retrieval")
    if not isinstance(retrieval, Mapping) or retrieval.get("status") != "completed":
        raise ValueError("V2.48.67 successful bundle lacks completed retrieval")
    nested = retrieval.get("receipt")
    if not isinstance(nested, Mapping):
        raise ValueError("V2.48.67 retrieval receipt is absent")
    controller = nested.get("controller")
    total = nested.get("total")
    if not isinstance(controller, Mapping) or not isinstance(total, Mapping):
        raise ValueError("V2.48.67 retrieval accounting is absent")
    first = controller.get("first_wave")
    policy = controller.get("policy")
    if not isinstance(first, Mapping) or not isinstance(policy, Mapping):
        raise ValueError("V2.48.67 controller binding is absent")
    cost = parent.get("cost")
    search_cost = cost.get("search") if isinstance(cost, Mapping) else None
    if not isinstance(search_cost, Mapping):
        raise ValueError("V2.48.67 parent search accounting is absent")

    logical_queries = _nonnegative_integer(
        total.get("queries_executed"), label="logical query count"
    )
    fetches_attempted = _nonnegative_integer(
        total.get("fetches_attempted"), label="retrieval fetch count"
    )
    parent_response_calls = _nonnegative_integer(
        search_cost.get("calls"), label="parent response count"
    )
    parent_failed_queries = _nonnegative_integer(
        search_cost.get("failures"), label="parent failed-query count"
    )
    parent_fetch_calls = _nonnegative_integer(
        search_cost.get("fetch_calls"), label="parent fetch count"
    )
    direct_successes = _nonnegative_integer(
        direct.get("successful_queries"), label="direct successful-query count"
    )
    direct_failures = _nonnegative_integer(
        direct.get("failed_queries"), label="direct failed-query count"
    )
    provider_attempts = _nonnegative_integer(
        direct.get("provider_attempts"), label="direct provider-attempt count"
    )
    direct_response_calls = sum(
        _nonnegative_integer(direct.get(name), label=name)
        for name in STATUS_BUCKETS
    )
    raw_first = float(first.get("search_seconds", -1)) + float(
        first.get("fetch_seconds", -1)
    )

    if (
        envelope["model_slot_receipt"].get("slot_cap")
        != expected_model_slot_cap
        or envelope["parent_model_slot_receipt"].get("slot_cap")
        != expected_model_slot_cap
        or direct.get("key_slot_cap") != expected_tavily_key_slot_cap
        or direct_successes + direct_failures != logical_queries
        or direct_successes > provider_attempts
        or direct_successes > direct.get("status_2xx", -1)
        or parent_response_calls != direct_response_calls
        or parent_failed_queries != direct_failures
        or parent_fetch_calls != fetches_attempted
        or provider_attempts != rate.get("provider_start_reservations")
        or direct.get("status_429") != rate.get("provider_429_responses")
        or pacing.get("provider_start_reservations_at_admission", -1)
        > rate.get("provider_start_reservations", -1)
        or pacing.get("pacing_aware_decision") != controller.get("decision")
        or pacing.get("pacing_aware_reason") != controller.get("reason")
        or not math.isclose(
            float(pacing.get("raw_wave1_elapsed_seconds", -1)),
            raw_first,
            rel_tol=0.0,
            abs_tol=1e-6,
        )
        or not math.isclose(
            float(pacing.get("effective_wave1_ceiling_seconds", -1)),
            float(policy.get("maximum_wave1_seconds", -2)),
            rel_tol=0.0,
            abs_tol=1e-6,
        )
    ):
        raise ValueError("V2.48.67 response-aware runtime binding drifted")


def _isolated_function(original: Any, **bindings: Any) -> Any:
    if original.__closure__:
        raise RuntimeError("V2.48.67 frozen bundle function has closure state")
    namespace = dict(original.__globals__)
    namespace.update(bindings)
    value = types.FunctionType(
        original.__code__,
        namespace,
        name=f"v24867_isolated_{original.__name__}",
        argdefs=original.__defaults__,
        closure=None,
    )
    value.__kwdefaults__ = copy.deepcopy(original.__kwdefaults__)
    value.__annotations__ = copy.deepcopy(original.__annotations__)
    return value


_VALIDATE_VALUES = _isolated_function(
    frozen._validate_values,
    _runtime_binding=_runtime_binding,
)
_VALIDATE_BUNDLE = _isolated_function(
    frozen.validate_bundle,
    _validate_values=_VALIDATE_VALUES,
)
_WRITE_BUNDLE = _isolated_function(
    frozen.write_bundle,
    _validate_values=_VALIDATE_VALUES,
    validate_bundle=_VALIDATE_BUNDLE,
)


def write_bundle(
    *,
    output_root: Path,
    directory: Path,
    outcome: IntegratedCoverageRevisionTaskOutcome,
    direct_receipt: Mapping[str, Any],
    rate_receipt: Mapping[str, Any],
    pacing_receipt: Mapping[str, Any],
    expected_model_slot_cap: int,
    expected_tavily_key_slot_cap: int,
    writer: Callable[[Path, Mapping[str, Any]], None] = frozen._atomic_new,
) -> dict[str, Any]:
    return _WRITE_BUNDLE(
        output_root=output_root,
        directory=directory,
        outcome=outcome,
        direct_receipt=direct_receipt,
        rate_receipt=rate_receipt,
        pacing_receipt=pacing_receipt,
        expected_model_slot_cap=expected_model_slot_cap,
        expected_tavily_key_slot_cap=expected_tavily_key_slot_cap,
        writer=writer,
    )


def validate_bundle(
    *,
    output_root: Path,
    directory: Path,
    expected_model_slot_cap: int,
    expected_tavily_key_slot_cap: int,
) -> dict[str, Any]:
    return _VALIDATE_BUNDLE(
        output_root=output_root,
        directory=directory,
        expected_model_slot_cap=expected_model_slot_cap,
        expected_tavily_key_slot_cap=expected_tavily_key_slot_cap,
    )


def validate_isolation() -> None:
    if (
        frozen._validate_values.__globals__["_runtime_binding"]
        is not frozen._runtime_binding
        or _VALIDATE_VALUES.__globals__["_runtime_binding"] is not _runtime_binding
        or _VALIDATE_BUNDLE.__globals__["_validate_values"] is not _VALIDATE_VALUES
        or _WRITE_BUNDLE.__globals__["_validate_values"] is not _VALIDATE_VALUES
        or _WRITE_BUNDLE.__globals__["validate_bundle"] is not _VALIDATE_BUNDLE
        or _VALIDATE_VALUES.__code__ is not frozen._validate_values.__code__
        or _VALIDATE_BUNDLE.__code__ is not frozen.validate_bundle.__code__
        or _WRITE_BUNDLE.__code__ is not frozen.write_bundle.__code__
    ):
        raise RuntimeError("V2.48.67 isolated bundle binding drifted")


__all__ = [
    "ALL_NAMES",
    "BACKFILL_NAME",
    "BUNDLE_NAME",
    "COVERAGE_NAME",
    "DATA_NAMES",
    "DIRECT_NAME",
    "FINAL_MODEL_NAME",
    "PACING_NAME",
    "PARENT_MODEL_NAME",
    "POLICY_ID",
    "RATE_NAME",
    "RESULT_NAME",
    "SINGLE_NAME",
    "TRANSPORT_NAME",
    "validate_bundle",
    "validate_isolation",
    "write_bundle",
]
