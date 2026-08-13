"""Structurally disjoint RFC population for V2.54.34.

The interval priority was frozen before the current candidate generator:
``9320--9399``, ``9240--9319``, then ``9160--9239``.  The first two blocks now
have frozen terminal forwards.  V2.54.37 structurally replays every tracked
RFC population/forward pair and therefore selects the first remaining zero-
intersection block, RFC 9160--9239.  The block is indivisible; no endpoint,
page, candidate reach, model output, field value, prediction, evaluator, or
per-task outcome participates in selection.

Questions explicitly name the official RFC Editor database so the existing
visible-only authority parser can bind the authority to source URLs.  This
pure module performs no I/O and grants no forward/evaluator authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


POLICY_ID = "v25436_structurally_disjoint_source_authoritative_population_v1"
SELECTION_PARENT_COMMIT = "cec4dd5d67df4b2af71ed19be9240d086cb182fb"
TASK_COUNT = 20
ROWS_PER_TASK = 4
RFC_NUMBERS = tuple(range(9160, 9240))
COLUMNS = ("RFC", "Title", "Authors", "Status", "Stream", "Published")
CANDIDATE_INTERVAL_ORDER = (
    (9320, 9399),
    (9240, 9319),
    (9160, 9239),
)
EXPECTED_IDENTITY_VECTOR_SHA256 = (
    "78708ef0ad5980d146a4daf4a9a848e61813afdc1d4bb20418b1f1bcfa88664e"
)
EXPECTED_GROUP_VECTOR_SHA256 = (
    "f7e6063b69897efd750295120dfc6f0ee3db3d113e190b280617d6ffd56836d6"
)
EXPECTED_TASK_VECTOR_SHA256 = (
    "e2e5f488511ecf8125399d302232ad751a14376aa10856148e44eba22b45228e"
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def identity_vector() -> list[str]:
    values = [f"RFC {number}" for number in RFC_NUMBERS]
    observed = payload_sha256(values)
    if (
        RFC_NUMBERS != tuple(range(9160, 9240))
        or len(values) != TASK_COUNT * ROWS_PER_TASK
        or len(set(values)) != len(values)
        or any(re.fullmatch(r"RFC 9[0-9]{3}", value) is None for value in values)
        or (
            EXPECTED_IDENTITY_VECTOR_SHA256 != "TO_BE_FROZEN"
            and observed != EXPECTED_IDENTITY_VECTOR_SHA256
        )
    ):
        raise RuntimeError("V2.54.36 RFC identity vector drifted")
    return values


def _group(task_index: int) -> tuple[str, ...]:
    identities = identity_vector()
    start = task_index * ROWS_PER_TASK
    return tuple(identities[start : start + ROWS_PER_TASK])


def _question(group: Sequence[str]) -> str:
    visible = "; ".join(group)
    return (
        "Use public web sources and the official RFC Editor database to "
        "return exactly one Markdown table and no prose for the four visible "
        f"document identities <RFCS>{visible}</RFCS>. Columns exactly: "
        + " | ".join(COLUMNS)
        + ". Return exactly four rows in the same RFC order shown above. "
        "The RFC cell must use the visible `RFC NNNN` form. Title, Authors, "
        "Status, Stream, and Published must all come from the same identity-"
        "bound RFC Editor source record. Preserve official spelling, list "
        "separators, ordering, and the displayed Published value. Use Unknown "
        "only when same-forward fetched public pages do not establish a value."
    )


def group_vector() -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for task_index in range(TASK_COUNT):
        group = _group(task_index)
        question = _question(group)
        opaque = "task_" + hashlib.sha256(
            f"v25436:{task_index}:{question}".encode()
        ).hexdigest()[:24]
        values.append(
            {
                "task_index": task_index,
                "identity_count": len(group),
                "task": {"opaque_id": opaque, "question": question},
            }
        )
    checked = validate_group_vector(values)
    observed = payload_sha256(checked)
    if (
        EXPECTED_GROUP_VECTOR_SHA256 != "TO_BE_FROZEN"
        and observed != EXPECTED_GROUP_VECTOR_SHA256
    ):
        raise RuntimeError("V2.54.36 group vector drifted")
    return checked


def task_vector() -> list[dict[str, str]]:
    values = [dict(group["task"]) for group in group_vector()]
    observed = payload_sha256(values)
    if (
        EXPECTED_TASK_VECTOR_SHA256 != "TO_BE_FROZEN"
        and observed != EXPECTED_TASK_VECTOR_SHA256
    ):
        raise RuntimeError("V2.54.36 task vector drifted")
    return values


def validate_group_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.54.36 task denominator drifted")
    output: list[dict[str, Any]] = []
    opaque_ids: list[str] = []
    identities = identity_vector()
    for task_index, raw in enumerate(values):
        if (
            not isinstance(raw, Mapping)
            or set(raw) != {"task_index", "identity_count", "task"}
            or raw.get("task_index") != task_index
            or raw.get("identity_count") != ROWS_PER_TASK
            or not isinstance(raw.get("task"), Mapping)
        ):
            raise ValueError("V2.54.36 group shape drifted")
        task = raw["task"]
        group = _group(task_index)
        expected_question = _question(group)
        if (
            set(task) != {"opaque_id", "question"}
            or not isinstance(task.get("opaque_id"), str)
            or re.fullmatch(r"task_[0-9a-f]{24}", task["opaque_id"]) is None
            or task.get("question") != expected_question
            or any(
                identity in expected_question
                for identity in identities
                if identity not in group
            )
            or "https://" in expected_question
        ):
            raise ValueError("V2.54.36 task binding drifted")
        opaque_ids.append(task["opaque_id"])
        output.append(
            {
                "task_index": task_index,
                "identity_count": ROWS_PER_TASK,
                "task": dict(task),
            }
        )
    if len(set(opaque_ids)) != TASK_COUNT:
        raise ValueError("V2.54.36 opaque identity collision")
    return output


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "four_rfc_identities_directly_visible_per_question": True,
        "official_rfc_editor_database_phrase_directly_visible": True,
        "population_is_one_consecutive_indivisible_eighty_identity_vector": True,
        "selected_first_candidate_with_zero_consumed_range_intersection": True,
        "individual_identity_or_task_retention_replacement_or_ranking": False,
        "candidate_endpoint_page_field_value_prediction_or_evaluator_used_for_selection": False,
        "membership_comes_only_from_visible_question": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "network_model_search_fetch_evaluator_or_benchmark_authorized": False,
    }


def mechanism_gate() -> dict[str, Any]:
    return {
        "fixed_task_denominator": TASK_COUNT,
        "required_terminal_tasks": TASK_COUNT,
        "required_completed_runtime_tasks": TASK_COUNT,
        "maximum_failure_as_zero_tasks": 0,
        "maximum_outer_failure_tasks": 0,
        "maximum_budget_rejection_tasks": 0,
        "required_parent_role_tasks": TASK_COUNT,
        "required_synthesis_capture_valid_tasks": TASK_COUNT,
        "minimum_accepted_authority_page_tasks": 4,
        "minimum_available_candidate_tasks": 2,
        "minimum_applied_candidate_tasks": 2,
        "minimum_prediction_changed_tasks": 2,
        "maximum_application_failure_tasks": 0,
        "exact_physical_queries_per_completed_task": 4,
        "maximum_physical_fetches_per_completed_task": 14,
        "exact_normal_path_model_forwards_per_completed_task": 3,
        "one_parent_forward_per_task": True,
        "zero_additional_candidate_provider_effects": True,
        "base_and_candidate_predictions_frozen_per_task": True,
        "all_content_free_receipts_valid": True,
        "positive_signed_credit_count": 0,
        "postfreeze_shared_effect_quality_required": True,
    }


__all__ = [
    "CANDIDATE_INTERVAL_ORDER",
    "COLUMNS",
    "EXPECTED_GROUP_VECTOR_SHA256",
    "EXPECTED_IDENTITY_VECTOR_SHA256",
    "EXPECTED_TASK_VECTOR_SHA256",
    "POLICY_ID",
    "RFC_NUMBERS",
    "ROWS_PER_TASK",
    "SELECTION_PARENT_COMMIT",
    "TASK_COUNT",
    "group_vector",
    "identity_vector",
    "mechanism_gate",
    "payload_sha256",
    "source_policy",
    "task_vector",
    "validate_group_vector",
]
