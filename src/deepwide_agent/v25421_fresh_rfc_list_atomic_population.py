"""Fresh outcome-blind RFC population for the list-atomic shared-effect gate.

At the frozen parent commit, complete consecutive 80-identity blocks were
checked in ascending priority order after the previously discussed RFC 9400
block.  RFC 9480--9559, 9560--9639, and 9640--9719 had canonical identity or
slug collisions in the parent tree/history; RFC 9720--9799 was the first block
with zero tree and zero history collisions.  The selected block is indivisible:
no identity or task is retained, replaced, removed, or ranked using an RFC
page, endpoint, model response, evaluator, score, or quality observation.

Each group of four identities creates one task.  A single V2.54.20 forward
will expose a shared base, raw changed-safe candidate, and guarded candidate;
there are no independently sampled arms.  This pure data module grants no
model, network, search, fetch, evaluator, benchmark, retry, replacement, or
signed-credit authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


POLICY_ID = "v25421_fresh_outcome_blind_rfc_list_atomic_population_v1"
FRESHNESS_PARENT_COMMIT = "ae307bf577e20b220ae142b497f75afdb20844b2"
TASK_COUNT = 20
ROWS_PER_TASK = 4
RFC_NUMBERS = tuple(range(9720, 9800))
COLUMNS = ("RFC", "Title", "Authors", "Status", "Stream", "Published")
EXPECTED_IDENTITY_VECTOR_SHA256 = (
    "42943a5ea382a24060fae030452822e923872552ed3cff4968a309ff9f8f8912"
)
EXPECTED_TASK_VECTOR_SHA256 = (
    "53d0020188d8d12e987ee90f5b957c41a2ef4a1fa2b19b64382c6a27235fd1fa"
)
EXPECTED_GROUP_VECTOR_SHA256 = (
    "822173f16ceeda1e3f14c2cedeecfd7c94ae327eccd2198b9a09e8c77bcc4a75"
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
        RFC_NUMBERS != tuple(range(9720, 9800))
        or len(values) != TASK_COUNT * ROWS_PER_TASK
        or len(set(values)) != len(values)
        or any(re.fullmatch(r"RFC 97[2-9][0-9]", value) is None for value in values)
        or (
            EXPECTED_IDENTITY_VECTOR_SHA256 != "TO_BE_FROZEN"
            and observed != EXPECTED_IDENTITY_VECTOR_SHA256
        )
    ):
        raise RuntimeError("V2.54.21 RFC identity vector drifted")
    return values


def _group(task_index: int) -> tuple[str, ...]:
    identities = identity_vector()
    start = task_index * ROWS_PER_TASK
    return tuple(identities[start : start + ROWS_PER_TASK])


def _question(group: Sequence[str]) -> str:
    vector = "; ".join(group)
    return (
        "Use public web sources and the official RFC Editor index/detail "
        "pages to return exactly one Markdown table and no prose for the "
        f"four visible document identities {vector}. Columns exactly: "
        + " | ".join(COLUMNS)
        + ". The table must contain exactly four data records in the same "
        "identifier order shown above and no other data records. The RFC cell "
        "must use the visible `RFC NNNN` form. Title, Authors, Status, Stream, "
        "and Published must all belong to that same RFC Editor metadata "
        "record. Preserve official spelling, list separators, and ordering; "
        "render Published as shown by the official source. Use Unknown only "
        "when same-forward fetched public pages do not establish a value."
    )


def group_vector() -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for task_index in range(TASK_COUNT):
        group = _group(task_index)
        question = _question(group)
        opaque = "task_" + hashlib.sha256(
            f"v25421:{task_index}:{question}".encode()
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
        raise RuntimeError("V2.54.21 group vector hash drifted")
    return checked


def task_vector() -> list[dict[str, str]]:
    rows = [dict(group["task"]) for group in group_vector()]
    observed = payload_sha256(rows)
    if (
        EXPECTED_TASK_VECTOR_SHA256 != "TO_BE_FROZEN"
        and observed != EXPECTED_TASK_VECTOR_SHA256
    ):
        raise RuntimeError("V2.54.21 task vector hash drifted")
    return rows


def validate_group_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.54.21 task denominator drifted")
    output: list[dict[str, Any]] = []
    opaque_ids: list[str] = []
    all_identities = identity_vector()
    for task_index, raw in enumerate(values):
        if (
            not isinstance(raw, Mapping)
            or set(raw) != {"task_index", "identity_count", "task"}
            or raw.get("task_index") != task_index
            or raw.get("identity_count") != ROWS_PER_TASK
            or not isinstance(raw.get("task"), Mapping)
        ):
            raise ValueError("V2.54.21 group shape drifted")
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
                for identity in all_identities
                if identity not in group
            )
            or "https://" in expected_question
        ):
            raise ValueError("V2.54.21 task binding drifted")
        opaque_ids.append(task["opaque_id"])
        output.append(
            {
                "task_index": task_index,
                "identity_count": ROWS_PER_TASK,
                "task": dict(task),
            }
        )
    if len(opaque_ids) != TASK_COUNT or len(set(opaque_ids)) != TASK_COUNT:
        raise ValueError("V2.54.21 opaque identity collision")
    return output


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "twenty_fixed_tasks_and_eighty_fixed_identities": True,
        "four_visible_rfc_identities_per_task": True,
        "one_parent_forward_exposes_shared_base_raw_and_guarded_candidate": True,
        "independent_sampling_between_quality_arms": False,
        "population_is_one_consecutive_indivisible_eighty_identity_vector": True,
        "population_fixed_before_candidate_page_endpoint_model_or_evaluator_access": True,
        "freshness_bound_to_parent_tree_and_ancestor_history_zero_match": True,
        "official_rfc_metadata_surface_not_used_to_select_or_replace_tasks": True,
        "fixed_failure_as_zero_denominator_no_retry_resume_or_replacement": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "deepwidebench_forward_evaluator_leaderboard_or_sota_authorized": False,
    }


def mechanism_gate() -> dict[str, Any]:
    return {
        "fixed_task_denominator": TASK_COUNT,
        "required_terminal_tasks": TASK_COUNT,
        "required_completed_runtime_tasks": TASK_COUNT,
        "maximum_outer_failure_tasks": 0,
        "maximum_naked_outer_failure_tasks": 0,
        "maximum_budget_rejection_tasks": 0,
        "exact_physical_queries_per_completed_task": 4,
        "maximum_physical_fetches_per_completed_task": 14,
        "exact_normal_path_model_forwards_per_completed_task": 3,
        "all_content_free_receipts_valid": True,
        "one_parent_forward_per_task": True,
        "zero_additional_guard_provider_effects": True,
        "base_raw_candidate_and_guarded_candidate_frozen_per_task": True,
        "maximum_unattributable_prediction_changed_tasks": 0,
        "positive_signed_credit_count": 0,
        "postfreeze_shared_effect_quality_required_after_mechanism_gate_go": True,
    }


__all__ = [
    "COLUMNS",
    "EXPECTED_GROUP_VECTOR_SHA256",
    "EXPECTED_IDENTITY_VECTOR_SHA256",
    "EXPECTED_TASK_VECTOR_SHA256",
    "FRESHNESS_PARENT_COMMIT",
    "POLICY_ID",
    "RFC_NUMBERS",
    "ROWS_PER_TASK",
    "TASK_COUNT",
    "group_vector",
    "identity_vector",
    "mechanism_gate",
    "payload_sha256",
    "source_policy",
    "task_vector",
    "validate_group_vector",
]
