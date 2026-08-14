"""Outcome-free RFC population following the consumed V2.54.38 block.

All tracked terminal RFC populations through V2.54.38 use fixed 80-identity
blocks.  The lower-most consumed block is RFC 9160--9239.  This successor uses
the immediately preceding whole block, RFC 9080--9159, without endpoint,
page, candidate, model, prediction, evaluator, score, or per-task inspection.
The vector is indivisible and grouped consecutively four identities per task.

The questions retain the exact visible schema and official RFC Editor phrase
required by the existing label-blind membership and authority binders.  This
pure module performs no I/O and authorizes neither forward nor evaluation.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


POLICY_ID = "v25442_structurally_disjoint_key_anchored_population_v1"
SELECTION_PARENT_COMMIT = "b14c43db2022d00035b310016d038e9a26d1a8fa"
TASK_COUNT = 20
ROWS_PER_TASK = 4
RFC_NUMBERS = tuple(range(9080, 9160))
COLUMNS = ("RFC", "Title", "Authors", "Status", "Stream", "Published")
SELECTION_RULE = "immediately_preceding_whole_block"
CONSUMED_INTERVALS = (
    (9160, 9239),
    (9240, 9319),
    (9320, 9399),
    (9400, 9479),
    (9480, 9559),
    (9600, 9679),
    (9680, 9759),
    (9720, 9799),
    (9800, 9879),
)
EXPECTED_IDENTITY_VECTOR_SHA256 = (
    "653b9eff246dbd77c2549bd5b5764ba9ee8a28abb091fd550a3b1bee7b45e7e0"
)
EXPECTED_GROUP_VECTOR_SHA256 = (
    "aa4c063a533840f6dc0ca0c3a69ef91c02caaeaa9e5e461ea7b30633b6a76f4c"
)
EXPECTED_TASK_VECTOR_SHA256 = (
    "af469413b7079fa5d764415548433bf62954586d6f68786ac0d00b27bb644dee"
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
        RFC_NUMBERS != tuple(range(9080, 9160))
        or len(values) != TASK_COUNT * ROWS_PER_TASK
        or len(set(values)) != len(values)
        or any(re.fullmatch(r"RFC 9[0-9]{3}", value) is None for value in values)
        or (
            EXPECTED_IDENTITY_VECTOR_SHA256 != "TO_BE_FROZEN"
            and observed != EXPECTED_IDENTITY_VECTOR_SHA256
        )
    ):
        raise RuntimeError("V2.54.42 RFC identity vector drifted")
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
            f"v25442:{task_index}:{question}".encode()
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
        raise RuntimeError("V2.54.42 group vector drifted")
    return checked


def task_vector() -> list[dict[str, str]]:
    values = [dict(group["task"]) for group in group_vector()]
    observed = payload_sha256(values)
    if (
        EXPECTED_TASK_VECTOR_SHA256 != "TO_BE_FROZEN"
        and observed != EXPECTED_TASK_VECTOR_SHA256
    ):
        raise RuntimeError("V2.54.42 task vector drifted")
    return values


def validate_group_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.54.42 task denominator drifted")
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
            raise ValueError("V2.54.42 group shape drifted")
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
            raise ValueError("V2.54.42 task binding drifted")
        opaque_ids.append(task["opaque_id"])
        output.append(
            {
                "task_index": task_index,
                "identity_count": ROWS_PER_TASK,
                "task": dict(task),
            }
        )
    if len(set(opaque_ids)) != TASK_COUNT:
        raise ValueError("V2.54.42 opaque identity collision")
    return output


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "four_rfc_identities_directly_visible_per_question": True,
        "official_rfc_editor_database_phrase_directly_visible": True,
        "population_is_one_consecutive_indivisible_eighty_identity_vector": True,
        "selection_is_immediately_preceding_whole_structural_block": True,
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
    "COLUMNS",
    "CONSUMED_INTERVALS",
    "EXPECTED_GROUP_VECTOR_SHA256",
    "EXPECTED_IDENTITY_VECTOR_SHA256",
    "EXPECTED_TASK_VECTOR_SHA256",
    "POLICY_ID",
    "RFC_NUMBERS",
    "ROWS_PER_TASK",
    "SELECTION_PARENT_COMMIT",
    "SELECTION_RULE",
    "TASK_COUNT",
    "group_vector",
    "identity_vector",
    "mechanism_gate",
    "payload_sha256",
    "source_policy",
    "task_vector",
    "validate_group_vector",
]
