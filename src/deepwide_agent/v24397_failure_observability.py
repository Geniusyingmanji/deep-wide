"""Content-free failure and partial-effect observability for external gates.

This module never reads task text, benchmark metadata, predictions, pages, or
evaluator data.  It preserves only sealed exit taxonomy, coarse exception
classes, artifact presence, and already-content-free effect receipts.
"""

from __future__ import annotations

import copy
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from .v24263_global_model_limiter import payload_sha256
from .v24280_task_union_single_shot import validate_receipt as validate_search_receipt
from .v24308_child_exit_observability import (
    COARSE_EXCEPTION_TYPES,
    TAXONOMY,
    coarse_exception_type,
    validate_child_receipt,
    validate_parent_receipt,
)
from .v24312_deadline_reliability import validate_receipt as validate_model_receipt
from .v24316_deadline_search import validate_transport_health


POLICY_ID = "v24397_content_free_failure_observability_v1"
SNAPSHOT_ROLE = "v24397_partial_effect_failure_snapshot"
TASK_ROLE = "v24397_content_free_task_observation"
AGGREGATE_ROLE = "v24397_content_free_observation_aggregate"
FAILURE_STAGES = frozenset(
    {
        "model_construction",
        "search_construction",
        "runtime",
        "artifact_serialization",
    }
)
DEADLINE_EVIDENCE = frozenset(
    {
        "parent_hard_timeout",
        "partial_receipt_exhausted",
        "observed_not_exhausted",
        "unobserved",
    }
)
EFFECT_SCOPES = frozenset(
    {
        "successful_terminal_receipts",
        "failure_partial_receipts",
        "unobserved_lower_bound",
    }
)
SNAPSHOT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "failure_stage",
        "exception_type",
        "model_receipt_present",
        "transport_receipt_present",
        "search_receipt_present",
        "model_receipt_payload_sha256",
        "transport_receipt_payload_sha256",
        "search_receipt_payload_sha256",
        "contains_task_question_prompt_response_prediction_query_url_page_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "receipt_builder_called_network_model_search_fetch_or_evaluator",
        "snapshot_payload_sha256",
    }
)
TASK_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "ordinal",
        "parent_taxonomy",
        "parent_elapsed_seconds",
        "parent_timed_out",
        "parent_subprocess_exception",
        "child_terminal_receipt_present",
        "child_terminal_receipt_valid",
        "result_envelope_present",
        "result_envelope_valid",
        "model_receipt_present",
        "model_receipt_valid",
        "transport_receipt_present",
        "transport_receipt_valid",
        "child_stage",
        "child_exception_type",
        "failure_snapshot_present",
        "failure_snapshot_valid",
        "failure_stage",
        "failure_exception_type",
        "effect_scope",
        "model_effects_observed",
        "transport_effects_observed",
        "search_shape_observed",
        "model_acquisitions",
        "slot_timeouts",
        "provider_deadline_failures",
        "slot_total_wait_seconds",
        "slot_max_wait_seconds",
        "hosted_search_attempts",
        "hosted_search_deadline_failures",
        "hard_fetch_helper_calls",
        "hard_fetch_deadline_failures",
        "fetch_deadline_rejections",
        "fetch_helper_failures",
        "multi_query_chunks",
        "incomplete_mapping_chunks",
        "recursive_split_requests",
        "deadline_evidence",
        "partial_effect_counts_are_lower_bounds",
        "contains_task_question_prompt_response_prediction_query_url_page_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "observation_payload_sha256",
    }
)
AGGREGATE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "selected",
        "exact_ordinal_vector",
        "parent_taxonomy_counts",
        "child_stage_counts",
        "child_exception_type_counts",
        "failure_stage_counts",
        "failure_exception_type_counts",
        "effect_scope_counts",
        "deadline_evidence_counts",
        "success_tasks",
        "failure_tasks",
        "failure_snapshot_tasks",
        "fully_observed_effect_tasks",
        "unobserved_effect_tasks",
        "model_acquisitions_lower_bound",
        "slot_timeouts_lower_bound",
        "provider_deadline_failures_lower_bound",
        "slot_total_wait_seconds_lower_bound",
        "slot_max_wait_seconds_observed",
        "hosted_search_attempts_lower_bound",
        "hosted_search_deadline_failures_lower_bound",
        "hard_fetch_helper_calls_lower_bound",
        "hard_fetch_deadline_failures_lower_bound",
        "fetch_deadline_rejections_lower_bound",
        "fetch_helper_failures_lower_bound",
        "multi_query_chunks_lower_bound",
        "incomplete_mapping_chunks_lower_bound",
        "recursive_split_requests_lower_bound",
        "contains_task_question_prompt_response_prediction_query_url_page_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "aggregate_payload_sha256",
    }
)


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _receipt_hash(value: Mapping[str, Any] | None) -> str | None:
    return payload_sha256(dict(value)) if isinstance(value, Mapping) else None


def build_failure_snapshot(
    error: BaseException,
    *,
    failure_stage: str,
    model_receipt: Mapping[str, Any] | None,
    transport_health: Mapping[str, Any] | None,
    search_receipt: Mapping[str, Any] | None,
    expected_model_cap: int,
) -> dict[str, Any]:
    if failure_stage not in FAILURE_STAGES:
        raise ValueError("V2.43.97 failure stage is invalid")
    if model_receipt is not None:
        validate_model_receipt(dict(model_receipt), expected_cap=expected_model_cap)
    if transport_health is not None:
        validate_transport_health(transport_health)
    if search_receipt is not None:
        validate_search_receipt(search_receipt)
    value = {
        "artifact_version": 1,
        "role": SNAPSHOT_ROLE,
        "policy_id": POLICY_ID,
        "failure_stage": failure_stage,
        "exception_type": coarse_exception_type(error),
        "model_receipt_present": model_receipt is not None,
        "transport_receipt_present": transport_health is not None,
        "search_receipt_present": search_receipt is not None,
        "model_receipt_payload_sha256": _receipt_hash(model_receipt),
        "transport_receipt_payload_sha256": _receipt_hash(transport_health),
        "search_receipt_payload_sha256": _receipt_hash(search_receipt),
        "contains_task_question_prompt_response_prediction_query_url_page_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "receipt_builder_called_network_model_search_fetch_or_evaluator": False,
    }
    value["snapshot_payload_sha256"] = payload_sha256(value)
    validate_failure_snapshot(
        value,
        model_receipt=model_receipt,
        transport_health=transport_health,
        search_receipt=search_receipt,
        expected_model_cap=expected_model_cap,
    )
    return value


def validate_failure_snapshot(
    value: Mapping[str, Any],
    *,
    model_receipt: Mapping[str, Any] | None,
    transport_health: Mapping[str, Any] | None,
    search_receipt: Mapping[str, Any] | None,
    expected_model_cap: int,
) -> dict[str, Any]:
    copied = dict(value)
    if model_receipt is not None:
        validate_model_receipt(dict(model_receipt), expected_cap=expected_model_cap)
    if transport_health is not None:
        validate_transport_health(transport_health)
    if search_receipt is not None:
        validate_search_receipt(search_receipt)
    expected_presence = {
        "model_receipt_present": model_receipt is not None,
        "transport_receipt_present": transport_health is not None,
        "search_receipt_present": search_receipt is not None,
    }
    expected_hashes = {
        "model_receipt_payload_sha256": _receipt_hash(model_receipt),
        "transport_receipt_payload_sha256": _receipt_hash(transport_health),
        "search_receipt_payload_sha256": _receipt_hash(search_receipt),
    }
    if (
        set(copied) != SNAPSHOT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != SNAPSHOT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("failure_stage") not in FAILURE_STAGES
        or copied.get("exception_type") not in COARSE_EXCEPTION_TYPES
        or any(copied.get(name) is not expected for name, expected in expected_presence.items())
        or any(copied.get(name) != expected for name, expected in expected_hashes.items())
        or copied.get(
            "contains_task_question_prompt_response_prediction_query_url_page_or_credential"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get("receipt_builder_called_network_model_search_fetch_or_evaluator")
        is not False
        or not _sealed(copied, "snapshot_payload_sha256")
    ):
        raise ValueError("V2.43.97 failure snapshot drifted")
    return copy.deepcopy(copied)


def _nonnegative_int(value: Mapping[str, Any], name: str) -> int:
    item = value.get(name)
    if isinstance(item, bool) or not isinstance(item, int) or item < 0:
        raise ValueError(f"V2.43.97 invalid counter: {name}")
    return item


def _nonnegative_number(value: Mapping[str, Any], name: str) -> float:
    item = value.get(name)
    if (
        isinstance(item, bool)
        or not isinstance(item, (int, float))
        or not math.isfinite(float(item))
        or float(item) < 0
    ):
        raise ValueError(f"V2.43.97 invalid number: {name}")
    return float(item)


def build_task_observation(
    ordinal: int,
    parent: Mapping[str, Any],
    *,
    child: Mapping[str, Any] | None,
    failure_snapshot: Mapping[str, Any] | None,
    model_receipt: Mapping[str, Any] | None,
    transport_health: Mapping[str, Any] | None,
    search_receipt: Mapping[str, Any] | None,
    expected_model_cap: int,
) -> dict[str, Any]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal <= 0:
        raise ValueError("V2.43.97 ordinal is invalid")
    validated_parent = validate_parent_receipt(parent)
    validated_child = validate_child_receipt(child) if child is not None else None
    validated_model = (
        validate_model_receipt(dict(model_receipt), expected_cap=expected_model_cap)
        if model_receipt is not None
        else None
    )
    validated_transport = (
        validate_transport_health(transport_health)
        if transport_health is not None
        else None
    )
    if search_receipt is not None:
        validate_search_receipt(search_receipt)
    validated_snapshot = (
        validate_failure_snapshot(
            failure_snapshot,
            model_receipt=model_receipt,
            transport_health=transport_health,
            search_receipt=search_receipt,
            expected_model_cap=expected_model_cap,
        )
        if failure_snapshot is not None
        else None
    )
    taxonomy = str(validated_parent["failure_taxonomy"])
    success = taxonomy == "success"
    all_effects = (
        validated_model is not None
        and validated_transport is not None
        and search_receipt is not None
    )
    if success:
        if validated_snapshot is not None or not all_effects:
            raise ValueError("V2.43.97 successful task lacks terminal receipts")
        effect_scope = "successful_terminal_receipts"
    elif validated_snapshot is not None and all_effects:
        effect_scope = "failure_partial_receipts"
    else:
        effect_scope = "unobserved_lower_bound"
    model = validated_model or {}
    transport = validated_transport or {}
    search = dict(search_receipt) if search_receipt is not None else {}
    if taxonomy == "hard_deadline_timeout":
        deadline = "parent_hard_timeout"
    elif (
        model.get("deadline_exhausted") is True
        or transport.get("deadline_exhausted") is True
    ):
        deadline = "partial_receipt_exhausted"
    elif validated_model is not None or validated_transport is not None:
        deadline = "observed_not_exhausted"
    else:
        deadline = "unobserved"
    value = {
        "artifact_version": 1,
        "role": TASK_ROLE,
        "policy_id": POLICY_ID,
        "ordinal": ordinal,
        "parent_taxonomy": taxonomy,
        "parent_elapsed_seconds": float(validated_parent["elapsed_seconds"]),
        "parent_timed_out": bool(validated_parent["timed_out"]),
        "parent_subprocess_exception": bool(validated_parent["subprocess_exception"]),
        "child_terminal_receipt_present": bool(
            validated_parent["child_terminal_receipt_present"]
        ),
        "child_terminal_receipt_valid": bool(
            validated_parent["child_terminal_receipt_valid"]
        ),
        "result_envelope_present": bool(validated_parent["result_envelope_present"]),
        "result_envelope_valid": bool(validated_parent["result_envelope_valid"]),
        "model_receipt_present": bool(validated_parent["model_receipt_present"]),
        "model_receipt_valid": bool(validated_parent["model_receipt_valid"]),
        "transport_receipt_present": bool(
            validated_parent["transport_receipt_present"]
        ),
        "transport_receipt_valid": bool(validated_parent["transport_receipt_valid"]),
        "child_stage": (
            str(validated_child["stage"]) if validated_child is not None else None
        ),
        "child_exception_type": (
            validated_child["exception_type"] if validated_child is not None else None
        ),
        "failure_snapshot_present": validated_snapshot is not None,
        "failure_snapshot_valid": validated_snapshot is not None,
        "failure_stage": (
            str(validated_snapshot["failure_stage"])
            if validated_snapshot is not None
            else None
        ),
        "failure_exception_type": (
            validated_snapshot["exception_type"]
            if validated_snapshot is not None
            else None
        ),
        "effect_scope": effect_scope,
        "model_effects_observed": validated_model is not None,
        "transport_effects_observed": validated_transport is not None,
        "search_shape_observed": search_receipt is not None,
        "model_acquisitions": int(model.get("acquisitions", 0)),
        "slot_timeouts": int(model.get("slot_timeouts", 0)),
        "provider_deadline_failures": int(model.get("provider_deadline_failures", 0)),
        "slot_total_wait_seconds": float(model.get("total_wait_seconds", 0.0)),
        "slot_max_wait_seconds": float(model.get("max_wait_seconds", 0.0)),
        "hosted_search_attempts": int(transport.get("hosted_search_attempts", 0)),
        "hosted_search_deadline_failures": int(
            transport.get("hosted_search_deadline_failures", 0)
        ),
        "hard_fetch_helper_calls": int(transport.get("hard_fetch_helper_calls", 0)),
        "hard_fetch_deadline_failures": int(
            transport.get("hard_fetch_deadline_failures", 0)
        ),
        "fetch_deadline_rejections": int(
            transport.get("fetch_deadline_rejections", 0)
        ),
        "fetch_helper_failures": int(transport.get("fetch_helper_failures", 0)),
        "multi_query_chunks": int(search.get("multi_query_chunks", 0)),
        "incomplete_mapping_chunks": int(
            search.get("incomplete_mapping_chunks", 0)
        ),
        "recursive_split_requests": int(search.get("recursive_split_requests", 0)),
        "deadline_evidence": deadline,
        "partial_effect_counts_are_lower_bounds": not success,
        "contains_task_question_prompt_response_prediction_query_url_page_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    value["observation_payload_sha256"] = payload_sha256(value)
    validate_task_observation(value)
    return value


def validate_task_observation(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    integer_fields = (
        "model_acquisitions",
        "slot_timeouts",
        "provider_deadline_failures",
        "hosted_search_attempts",
        "hosted_search_deadline_failures",
        "hard_fetch_helper_calls",
        "hard_fetch_deadline_failures",
        "fetch_deadline_rejections",
        "fetch_helper_failures",
        "multi_query_chunks",
        "incomplete_mapping_chunks",
        "recursive_split_requests",
    )
    boolean_fields = (
        "parent_timed_out",
        "parent_subprocess_exception",
        "child_terminal_receipt_present",
        "child_terminal_receipt_valid",
        "result_envelope_present",
        "result_envelope_valid",
        "model_receipt_present",
        "model_receipt_valid",
        "transport_receipt_present",
        "transport_receipt_valid",
        "failure_snapshot_present",
        "failure_snapshot_valid",
        "model_effects_observed",
        "transport_effects_observed",
        "search_shape_observed",
        "partial_effect_counts_are_lower_bounds",
        "contains_task_question_prompt_response_prediction_query_url_page_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
    )
    taxonomy = copied.get("parent_taxonomy")
    success = taxonomy == "success"
    if (
        set(copied) != TASK_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != TASK_ROLE
        or copied.get("policy_id") != POLICY_ID
        or isinstance(copied.get("ordinal"), bool)
        or not isinstance(copied.get("ordinal"), int)
        or copied["ordinal"] <= 0
        or taxonomy not in TAXONOMY
        or _nonnegative_number(copied, "parent_elapsed_seconds") < 0
        or any(not isinstance(copied.get(name), bool) for name in boolean_fields)
        or any(_nonnegative_int(copied, name) < 0 for name in integer_fields)
        or _nonnegative_number(copied, "slot_total_wait_seconds") < 0
        or _nonnegative_number(copied, "slot_max_wait_seconds") < 0
        or copied["slot_max_wait_seconds"] > copied["slot_total_wait_seconds"] + 1e-6
        or copied.get("child_stage") is not None
        and not isinstance(copied.get("child_stage"), str)
        or copied.get("child_exception_type") is not None
        and copied.get("child_exception_type") not in COARSE_EXCEPTION_TYPES
        or copied.get("failure_stage") is not None
        and copied.get("failure_stage") not in FAILURE_STAGES
        or copied.get("failure_exception_type") is not None
        and copied.get("failure_exception_type") not in COARSE_EXCEPTION_TYPES
        or copied.get("effect_scope") not in EFFECT_SCOPES
        or copied.get("deadline_evidence") not in DEADLINE_EVIDENCE
        or (copied.get("child_stage") is not None)
        is not copied.get("child_terminal_receipt_valid")
        or copied.get("failure_snapshot_present")
        is not copied.get("failure_snapshot_valid")
        or copied.get("failure_snapshot_present")
        is not (copied.get("failure_stage") is not None)
        or copied.get("failure_snapshot_present")
        is not (copied.get("failure_exception_type") is not None)
        or success
        and (
            copied.get("effect_scope") != "successful_terminal_receipts"
            or copied.get("partial_effect_counts_are_lower_bounds") is not False
            or copied.get("failure_snapshot_present") is not False
            or copied.get("model_effects_observed") is not True
            or copied.get("transport_effects_observed") is not True
            or copied.get("search_shape_observed") is not True
        )
        or not success
        and copied.get("partial_effect_counts_are_lower_bounds") is not True
        or copied.get("effect_scope") == "failure_partial_receipts"
        and (
            success
            or copied.get("failure_snapshot_present") is not True
            or copied.get("model_effects_observed") is not True
            or copied.get("transport_effects_observed") is not True
            or copied.get("search_shape_observed") is not True
        )
        or copied.get("effect_scope") == "unobserved_lower_bound"
        and (
            success
            or (
                copied.get("failure_snapshot_present") is True
                and copied.get("model_effects_observed") is True
                and copied.get("transport_effects_observed") is True
                and copied.get("search_shape_observed") is True
            )
        )
        or copied.get("model_effects_observed")
        is not copied.get("model_receipt_valid")
        or copied.get("transport_effects_observed")
        is not copied.get("transport_receipt_valid")
        or copied.get(
            "contains_task_question_prompt_response_prediction_query_url_page_or_credential"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or not _sealed(copied, "observation_payload_sha256")
    ):
        raise ValueError("V2.43.97 task observation drifted")
    return copy.deepcopy(copied)


def aggregate_observations(
    values: Sequence[Mapping[str, Any]], *, selected: int
) -> dict[str, Any]:
    tasks = [validate_task_observation(item) for item in values]
    tasks.sort(key=lambda item: item["ordinal"])
    taxonomy = Counter(str(item["parent_taxonomy"]) for item in tasks)
    child_stages = Counter(str(item["child_stage"]) for item in tasks)
    child_errors = Counter(str(item["child_exception_type"]) for item in tasks)
    failure_stages = Counter(str(item["failure_stage"]) for item in tasks)
    failure_errors = Counter(str(item["failure_exception_type"]) for item in tasks)
    scopes = Counter(str(item["effect_scope"]) for item in tasks)
    deadlines = Counter(str(item["deadline_evidence"]) for item in tasks)
    output = {
        "artifact_version": 1,
        "role": AGGREGATE_ROLE,
        "policy_id": POLICY_ID,
        "selected": len(tasks),
        "exact_ordinal_vector": [item["ordinal"] for item in tasks]
        == list(range(1, selected + 1)),
        "parent_taxonomy_counts": dict(sorted(taxonomy.items())),
        "child_stage_counts": dict(sorted(child_stages.items())),
        "child_exception_type_counts": dict(sorted(child_errors.items())),
        "failure_stage_counts": dict(sorted(failure_stages.items())),
        "failure_exception_type_counts": dict(sorted(failure_errors.items())),
        "effect_scope_counts": dict(sorted(scopes.items())),
        "deadline_evidence_counts": dict(sorted(deadlines.items())),
        "success_tasks": taxonomy.get("success", 0),
        "failure_tasks": len(tasks) - taxonomy.get("success", 0),
        "failure_snapshot_tasks": sum(item["failure_snapshot_valid"] for item in tasks),
        "fully_observed_effect_tasks": sum(
            item["model_effects_observed"]
            and item["transport_effects_observed"]
            and item["search_shape_observed"]
            for item in tasks
        ),
        "unobserved_effect_tasks": sum(
            item["effect_scope"] == "unobserved_lower_bound" for item in tasks
        ),
        "model_acquisitions_lower_bound": sum(
            item["model_acquisitions"] for item in tasks
        ),
        "slot_timeouts_lower_bound": sum(item["slot_timeouts"] for item in tasks),
        "provider_deadline_failures_lower_bound": sum(
            item["provider_deadline_failures"] for item in tasks
        ),
        "slot_total_wait_seconds_lower_bound": round(
            sum(item["slot_total_wait_seconds"] for item in tasks), 6
        ),
        "slot_max_wait_seconds_observed": round(
            max((item["slot_max_wait_seconds"] for item in tasks), default=0.0), 6
        ),
        "hosted_search_attempts_lower_bound": sum(
            item["hosted_search_attempts"] for item in tasks
        ),
        "hosted_search_deadline_failures_lower_bound": sum(
            item["hosted_search_deadline_failures"] for item in tasks
        ),
        "hard_fetch_helper_calls_lower_bound": sum(
            item["hard_fetch_helper_calls"] for item in tasks
        ),
        "hard_fetch_deadline_failures_lower_bound": sum(
            item["hard_fetch_deadline_failures"] for item in tasks
        ),
        "fetch_deadline_rejections_lower_bound": sum(
            item["fetch_deadline_rejections"] for item in tasks
        ),
        "fetch_helper_failures_lower_bound": sum(
            item["fetch_helper_failures"] for item in tasks
        ),
        "multi_query_chunks_lower_bound": sum(
            item["multi_query_chunks"] for item in tasks
        ),
        "incomplete_mapping_chunks_lower_bound": sum(
            item["incomplete_mapping_chunks"] for item in tasks
        ),
        "recursive_split_requests_lower_bound": sum(
            item["recursive_split_requests"] for item in tasks
        ),
        "contains_task_question_prompt_response_prediction_query_url_page_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    output["aggregate_payload_sha256"] = payload_sha256(output)
    validate_observation_aggregate(output, expected_selected=selected)
    return output


def validate_observation_aggregate(
    value: Mapping[str, Any], *, expected_selected: int
) -> dict[str, Any]:
    copied = dict(value)
    count_maps = (
        "parent_taxonomy_counts",
        "child_stage_counts",
        "child_exception_type_counts",
        "failure_stage_counts",
        "failure_exception_type_counts",
        "effect_scope_counts",
        "deadline_evidence_counts",
    )
    count_fields = (
        "selected",
        "success_tasks",
        "failure_tasks",
        "failure_snapshot_tasks",
        "fully_observed_effect_tasks",
        "unobserved_effect_tasks",
        "model_acquisitions_lower_bound",
        "slot_timeouts_lower_bound",
        "provider_deadline_failures_lower_bound",
        "hosted_search_attempts_lower_bound",
        "hosted_search_deadline_failures_lower_bound",
        "hard_fetch_helper_calls_lower_bound",
        "hard_fetch_deadline_failures_lower_bound",
        "fetch_deadline_rejections_lower_bound",
        "fetch_helper_failures_lower_bound",
        "multi_query_chunks_lower_bound",
        "incomplete_mapping_chunks_lower_bound",
        "recursive_split_requests_lower_bound",
    )
    if (
        set(copied) != AGGREGATE_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != AGGREGATE_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(_nonnegative_int(copied, name) < 0 for name in count_fields)
        or copied.get("selected") != expected_selected
        or copied.get("exact_ordinal_vector") is not True
        or any(
            not isinstance(copied.get(name), Mapping)
            or any(
                not isinstance(key, str)
                or isinstance(count, bool)
                or not isinstance(count, int)
                or count < 0
                for key, count in copied[name].items()
            )
            or sum(copied[name].values()) != expected_selected
            for name in count_maps
        )
        or copied["success_tasks"] + copied["failure_tasks"] != expected_selected
        or any(
            copied[name] > expected_selected
            for name in (
                "failure_snapshot_tasks",
                "fully_observed_effect_tasks",
                "unobserved_effect_tasks",
            )
        )
        or _nonnegative_number(copied, "slot_total_wait_seconds_lower_bound") < 0
        or _nonnegative_number(copied, "slot_max_wait_seconds_observed") < 0
        or copied["slot_max_wait_seconds_observed"]
        > copied["slot_total_wait_seconds_lower_bound"] + 1e-6
        or copied.get(
            "contains_task_question_prompt_response_prediction_query_url_page_or_credential"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or not _sealed(copied, "aggregate_payload_sha256")
    ):
        raise ValueError("V2.43.97 observation aggregate drifted")
    return copy.deepcopy(copied)


__all__ = [
    "AGGREGATE_ROLE",
    "EFFECT_SCOPES",
    "FAILURE_STAGES",
    "POLICY_ID",
    "SNAPSHOT_ROLE",
    "TASK_ROLE",
    "aggregate_observations",
    "build_failure_snapshot",
    "build_task_observation",
    "validate_failure_snapshot",
    "validate_observation_aggregate",
    "validate_task_observation",
]
