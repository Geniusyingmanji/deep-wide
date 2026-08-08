"""Mapping-recovery-aware validator for the V2.48.74 bundle format.

The frozen V2.48.74 validator equated parent failed query-local rows with
task-union unrecoverable search failures.  Hosted search can omit all
query-local citation spans while still exposing action-level sources.  The
task-union layer then recovers usable public pages, so these counters describe
different events.  This append-only successor keeps both counters and requires
only that unrecoverable failures are a subset of failed logical rows.

All artifact bytes, source-support gates, budgets, and fail-closed checks stay
unchanged.  The module has no benchmark, evaluator, environment, process,
credential, model, search, fetch, or network capability.
"""

from __future__ import annotations

import copy
import types
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from . import v24874_keyless_coverage_bundle as frozen
from .v24263_global_model_limiter import payload_sha256
from .v24861_coverage_revision_exact_task import (
    IntegratedCoverageRevisionTaskOutcome,
)


POLICY_ID = "v24879_mapping_recovery_aware_effect_bundle_validator_v1"

ALL_NAMES = frozen.ALL_NAMES
BACKFILL_NAME = frozen.BACKFILL_NAME
BUNDLE_NAME = frozen.BUNDLE_NAME
COVERAGE_NAME = frozen.COVERAGE_NAME
DATA_NAMES = frozen.DATA_NAMES
EFFECT_NAME = frozen.EFFECT_NAME
FINAL_MODEL_NAME = frozen.FINAL_MODEL_NAME
PARENT_MODEL_NAME = frozen.PARENT_MODEL_NAME
RESULT_NAME = frozen.RESULT_NAME
SINGLE_NAME = frozen.SINGLE_NAME
STATUS_BUCKETS = frozen.STATUS_BUCKETS
TRANSPORT_NAME = frozen.TRANSPORT_NAME


def validate_effect_receipt(
    value: Mapping[str, Any], *, envelope: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate exact effects while separating local and union failures."""

    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    projected = frozen._effect_projection(envelope)
    transport = projected.pop("transport_health")
    integer_fields = {
        "artifact_version",
        "admitted_logical_queries",
        "executed_logical_queries",
        "actual_fetches",
        "usable_pages",
        "unrecoverable_search_failures",
        "parent_response_calls",
        "parent_failed_query_rows",
        "parent_fetch_calls",
        "parent_fetch_failures",
        "parent_admitted_fetch_targets",
        "parent_evidence_pages",
        "provider_attempts",
        "transport_failures",
        "hard_total_wall_timeouts",
        *STATUS_BUCKETS,
        "hard_fetch_helper_calls",
        "hard_fetch_deadline_failures",
        "fetch_deadline_rejections",
        "fetch_helper_failures",
        "query_cap",
        "fetch_cap",
    }
    boolean_fields = {
        "executed_logical_queries_observed",
        "usable_pages_observed",
        "logical_queries_equal_http_responses_required",
        "fetch_cap_equal_actual_fetches_required",
        "entropy_or_information_gain_used_for_admission",
        "question_query_url_page_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    }
    expected = {
        "role",
        "policy_id",
        "retrieval_status",
        "receipt_payload_sha256",
        *integer_fields,
        *boolean_fields,
    }
    response_sum = sum(int(copied.get(name, 0)) for name in STATUS_BUCKETS)
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != frozen.EFFECT_ROLE
        or copied.get("policy_id") != frozen.POLICY_ID
        or copied.get("retrieval_status") not in {"completed", "failed"}
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integer_fields
        )
        or any(not isinstance(copied.get(name), bool) for name in boolean_fields)
        or any(copied.get(name) != amount for name, amount in projected.items())
        or copied.get("provider_attempts")
        != int(transport["hosted_search_attempts"])
        or copied.get("hard_fetch_helper_calls")
        != int(transport["hard_fetch_helper_calls"])
        or copied.get("hard_fetch_deadline_failures")
        != int(transport["hard_fetch_deadline_failures"])
        or copied.get("fetch_deadline_rejections")
        != int(transport["fetch_deadline_rejections"])
        or copied.get("fetch_helper_failures")
        != int(transport["fetch_helper_failures"])
        or response_sum != copied.get("parent_response_calls")
        or copied.get("provider_attempts")
        != copied.get("parent_response_calls")
        + copied.get("transport_failures")
        + copied.get("hard_total_wall_timeouts")
        or copied.get("parent_fetch_calls") != copied.get("actual_fetches")
        or copied.get("hard_fetch_helper_calls")
        + copied.get("fetch_deadline_rejections")
        != copied.get("actual_fetches")
        or copied.get("hard_fetch_deadline_failures")
        + copied.get("fetch_helper_failures")
        > copied.get("parent_fetch_failures")
        or copied.get("admitted_logical_queries") > copied.get("query_cap")
        or copied.get("executed_logical_queries")
        > copied.get("admitted_logical_queries")
        or copied.get("actual_fetches") > copied.get("fetch_cap")
        or copied.get("usable_pages") > copied.get("actual_fetches")
        or copied.get("parent_failed_query_rows")
        > copied.get("admitted_logical_queries")
        or copied.get("unrecoverable_search_failures")
        > copied.get("executed_logical_queries")
        or copied.get("unrecoverable_search_failures")
        > copied.get("parent_failed_query_rows")
        or copied.get("usable_pages", 0) > 0
        and copied.get("status_2xx", 0) <= 0
        or copied.get("query_cap") != 4
        or copied.get("fetch_cap") != 10
        or copied.get("logical_queries_equal_http_responses_required") is not False
        or copied.get("fetch_cap_equal_actual_fetches_required") is not False
        or copied.get("entropy_or_information_gain_used_for_admission") is not False
        or copied.get(
            "question_query_url_page_prediction_answer_opaque_id_or_credential_emitted"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read"
        )
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.79 mapping-recovery effect receipt drifted")
    if copied["retrieval_status"] == "completed":
        if (
            copied["executed_logical_queries_observed"] is not True
            or copied["usable_pages_observed"] is not True
            or copied["parent_admitted_fetch_targets"] != copied["usable_pages"]
            or copied["parent_evidence_pages"] != copied["usable_pages"]
            or copied["parent_fetch_failures"]
            != copied["actual_fetches"] - copied["usable_pages"]
        ):
            raise ValueError("V2.48.79 completed retrieval binding drifted")
    elif (
        copied["executed_logical_queries_observed"] is not False
        or copied["usable_pages_observed"] is not False
        or copied["executed_logical_queries"] != 0
        or copied["usable_pages"] != 0
        or copied["parent_admitted_fetch_targets"] != 0
        or copied["parent_evidence_pages"] != 0
    ):
        raise ValueError("V2.48.79 failed retrieval binding drifted")
    return copied


def _isolated_function(original: Any, **bindings: Any) -> Any:
    if original.__closure__:
        raise RuntimeError("V2.48.79 frozen bundle function has closure state")
    namespace = dict(original.__globals__)
    namespace.update(bindings)
    value = types.FunctionType(
        original.__code__,
        namespace,
        name=f"v24879_isolated_{original.__name__}",
        argdefs=original.__defaults__,
        closure=None,
    )
    value.__kwdefaults__ = copy.deepcopy(original.__kwdefaults__)
    value.__annotations__ = copy.deepcopy(original.__annotations__)
    return value


_BUILD_EFFECT_RECEIPT = _isolated_function(
    frozen.build_effect_receipt,
    validate_effect_receipt=validate_effect_receipt,
)
_VALIDATE_VALUES = _isolated_function(
    frozen._validate_values,
    validate_effect_receipt=validate_effect_receipt,
)
_VALIDATE_BUNDLE = _isolated_function(
    frozen.validate_bundle,
    _validate_values=_VALIDATE_VALUES,
)
_WRITE_BUNDLE = _isolated_function(
    frozen.write_bundle,
    build_effect_receipt=_BUILD_EFFECT_RECEIPT,
    _validate_values=_VALIDATE_VALUES,
    validate_bundle=_VALIDATE_BUNDLE,
)


def write_bundle(
    *,
    output_root: Path,
    directory: Path,
    outcome: IntegratedCoverageRevisionTaskOutcome,
    status_counts: Mapping[object, object],
    transport_failures: int,
    hard_total_wall_timeouts: int,
    expected_model_slot_cap: int,
    writer: Callable[[Path, Mapping[str, Any]], None] = frozen._atomic_new,
) -> dict[str, Any]:
    return _WRITE_BUNDLE(
        output_root=output_root,
        directory=directory,
        outcome=outcome,
        status_counts=status_counts,
        transport_failures=transport_failures,
        hard_total_wall_timeouts=hard_total_wall_timeouts,
        expected_model_slot_cap=expected_model_slot_cap,
        writer=writer,
    )


def validate_bundle(
    *, output_root: Path, directory: Path, expected_model_slot_cap: int
) -> dict[str, Any]:
    return _VALIDATE_BUNDLE(
        output_root=output_root,
        directory=directory,
        expected_model_slot_cap=expected_model_slot_cap,
    )


def validate_isolation() -> None:
    if (
        frozen.build_effect_receipt.__globals__["validate_effect_receipt"]
        is not frozen.validate_effect_receipt
        or frozen._validate_values.__globals__["validate_effect_receipt"]
        is not frozen.validate_effect_receipt
        or _BUILD_EFFECT_RECEIPT.__globals__["validate_effect_receipt"]
        is not validate_effect_receipt
        or _VALIDATE_VALUES.__globals__["validate_effect_receipt"]
        is not validate_effect_receipt
        or _VALIDATE_BUNDLE.__globals__["_validate_values"]
        is not _VALIDATE_VALUES
        or _WRITE_BUNDLE.__globals__["build_effect_receipt"]
        is not _BUILD_EFFECT_RECEIPT
        or _WRITE_BUNDLE.__globals__["_validate_values"] is not _VALIDATE_VALUES
        or _WRITE_BUNDLE.__globals__["validate_bundle"] is not _VALIDATE_BUNDLE
        or _VALIDATE_VALUES.__code__ is not frozen._validate_values.__code__
        or _VALIDATE_BUNDLE.__code__ is not frozen.validate_bundle.__code__
        or _WRITE_BUNDLE.__code__ is not frozen.write_bundle.__code__
    ):
        raise RuntimeError("V2.48.79 isolated bundle binding drifted")


__all__ = [
    "ALL_NAMES",
    "BACKFILL_NAME",
    "BUNDLE_NAME",
    "COVERAGE_NAME",
    "DATA_NAMES",
    "EFFECT_NAME",
    "FINAL_MODEL_NAME",
    "PARENT_MODEL_NAME",
    "POLICY_ID",
    "RESULT_NAME",
    "SINGLE_NAME",
    "TRANSPORT_NAME",
    "validate_bundle",
    "validate_effect_receipt",
    "validate_isolation",
    "write_bundle",
]
