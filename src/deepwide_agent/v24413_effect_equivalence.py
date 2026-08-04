"""Effect-equivalence for deadline receipt snapshots.

Deadline-aware receipts mix three different classes of state:

* external-effect identity, such as model acquisitions and fetch attempts;
* static execution contract, such as slot capacity and cleanup reserve; and
* observation-time state, such as remaining seconds at the instant a receipt
  is sampled.

V2.44.09 compared whole snapshots around a pure in-process recovery step.  A
real monotonic clock therefore made the snapshots unequal even when no model,
search, or fetch effect occurred.  This pure successor compares the classes
explicitly.  Every effect and static field must remain equal.  Remaining time
may only decrease and deadline flags may only move from false to true.  Search
shape receipts contain no observation-time state and remain byte-equivalent.

The module has no file, environment, network, model, search, fetch, process,
benchmark, evaluator, reward, or score access.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping
from typing import Any

from .v24280_task_union_single_shot import validate_receipt as validate_search_receipt
from .v24312_deadline_reliability import validate_receipt as validate_model_receipt
from .v24316_deadline_search import validate_transport_health
from .v24323_shared_prefix_cell_entropy import payload_sha256


POLICY_ID = "v24413_deadline_receipt_effect_equivalence_v1"
ROLE = "v24413_effect_equivalence_receipt"
MODEL_OBSERVATION_FIELDS = frozenset(
    {"remaining_seconds_at_receipt", "deadline_exhausted", "receipt_payload_sha256"}
)
TRANSPORT_OBSERVATION_FIELDS = frozenset({"deadline_exhausted"})
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "model_effect_and_static_fields_equal",
        "transport_effect_fields_equal",
        "search_shape_fields_equal",
        "model_remaining_seconds_before",
        "model_remaining_seconds_after",
        "model_remaining_seconds_nonincreasing",
        "model_deadline_exhausted_before",
        "model_deadline_exhausted_after",
        "model_deadline_state_monotonic",
        "transport_deadline_exhausted_before",
        "transport_deadline_exhausted_after",
        "transport_deadline_state_monotonic",
        "observation_time_state_only_change_allowed",
        "external_effect_detected",
        "question_prompt_response_query_url_page_prediction_candidate_value_or_source_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)


def _without(value: Mapping[str, Any], names: frozenset[str]) -> dict[str, Any]:
    return {key: copy.deepcopy(item) for key, item in value.items() if key not in names}


def _nonincreasing(before: object, after: object) -> bool:
    if (
        isinstance(before, bool)
        or isinstance(after, bool)
        or not isinstance(before, (int, float))
        or not isinstance(after, (int, float))
        or not math.isfinite(float(before))
        or not math.isfinite(float(after))
    ):
        return False
    return 0.0 <= float(after) <= float(before) + 1e-6


def _boolean_monotonic(before: object, after: object) -> bool:
    return isinstance(before, bool) and isinstance(after, bool) and not (
        before is True and after is False
    )


def compare_effect_snapshots(
    *,
    model_before: Mapping[str, Any],
    model_after: Mapping[str, Any],
    transport_before: Mapping[str, Any],
    transport_after: Mapping[str, Any],
    search_before: Mapping[str, Any],
    search_after: Mapping[str, Any],
    expected_model_cap: int,
) -> dict[str, Any]:
    before_model = validate_model_receipt(
        dict(model_before), expected_cap=expected_model_cap
    )
    after_model = validate_model_receipt(
        dict(model_after), expected_cap=expected_model_cap
    )
    before_transport = validate_transport_health(transport_before)
    after_transport = validate_transport_health(transport_after)
    before_search = dict(search_before)
    after_search = dict(search_after)
    validate_search_receipt(before_search)
    validate_search_receipt(after_search)

    model_equal = _without(before_model, MODEL_OBSERVATION_FIELDS) == _without(
        after_model, MODEL_OBSERVATION_FIELDS
    )
    transport_equal = _without(
        before_transport, TRANSPORT_OBSERVATION_FIELDS
    ) == _without(after_transport, TRANSPORT_OBSERVATION_FIELDS)
    search_equal = before_search == after_search
    remaining_monotonic = _nonincreasing(
        before_model["remaining_seconds_at_receipt"],
        after_model["remaining_seconds_at_receipt"],
    )
    model_deadline_monotonic = _boolean_monotonic(
        before_model["deadline_exhausted"], after_model["deadline_exhausted"]
    )
    transport_deadline_monotonic = _boolean_monotonic(
        before_transport["deadline_exhausted"],
        after_transport["deadline_exhausted"],
    )
    external_effect = not (model_equal and transport_equal and search_equal)
    if (
        external_effect
        or not remaining_monotonic
        or not model_deadline_monotonic
        or not transport_deadline_monotonic
    ):
        raise ValueError("V2.44.13 receipt snapshots are not effect-equivalent")
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "model_effect_and_static_fields_equal": model_equal,
        "transport_effect_fields_equal": transport_equal,
        "search_shape_fields_equal": search_equal,
        "model_remaining_seconds_before": float(
            before_model["remaining_seconds_at_receipt"]
        ),
        "model_remaining_seconds_after": float(
            after_model["remaining_seconds_at_receipt"]
        ),
        "model_remaining_seconds_nonincreasing": remaining_monotonic,
        "model_deadline_exhausted_before": before_model["deadline_exhausted"],
        "model_deadline_exhausted_after": after_model["deadline_exhausted"],
        "model_deadline_state_monotonic": model_deadline_monotonic,
        "transport_deadline_exhausted_before": before_transport[
            "deadline_exhausted"
        ],
        "transport_deadline_exhausted_after": after_transport[
            "deadline_exhausted"
        ],
        "transport_deadline_state_monotonic": transport_deadline_monotonic,
        "observation_time_state_only_change_allowed": True,
        "external_effect_detected": external_effect,
        "question_prompt_response_query_url_page_prediction_candidate_value_or_source_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    validate_effect_equivalence_receipt(value)
    return value


def validate_effect_equivalence_receipt(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    numeric = (
        "model_remaining_seconds_before",
        "model_remaining_seconds_after",
    )
    true_fields = (
        "model_effect_and_static_fields_equal",
        "transport_effect_fields_equal",
        "search_shape_fields_equal",
        "model_remaining_seconds_nonincreasing",
        "model_deadline_state_monotonic",
        "transport_deadline_state_monotonic",
        "observation_time_state_only_change_allowed",
    )
    false_fields = (
        "external_effect_detected",
        "question_prompt_response_query_url_page_prediction_candidate_value_or_source_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), (int, float))
            or not math.isfinite(float(copied[name]))
            or float(copied[name]) < 0
            for name in numeric
        )
        or copied["model_remaining_seconds_after"]
        > copied["model_remaining_seconds_before"] + 1e-6
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
        or not isinstance(copied.get("model_deadline_exhausted_before"), bool)
        or not isinstance(copied.get("model_deadline_exhausted_after"), bool)
        or not isinstance(copied.get("transport_deadline_exhausted_before"), bool)
        or not isinstance(copied.get("transport_deadline_exhausted_after"), bool)
        or (
            copied["model_deadline_exhausted_before"] is True
            and copied["model_deadline_exhausted_after"] is False
        )
        or (
            copied["transport_deadline_exhausted_before"] is True
            and copied["transport_deadline_exhausted_after"] is False
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.13 effect-equivalence receipt drifted")
    return copy.deepcopy(copied)


__all__ = [
    "POLICY_ID",
    "ROLE",
    "compare_effect_snapshots",
    "validate_effect_equivalence_receipt",
]
