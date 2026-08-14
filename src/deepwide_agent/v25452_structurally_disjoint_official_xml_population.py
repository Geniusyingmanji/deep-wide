"""Outcome-free RFC population for the official-XML shared candidate.

The V2.54.46 terminal forward consumed the previously frozen RFC 9080--9159
block.  This successor therefore selects the immediately preceding complete
80-identity block, RFC 9000--9079, using only structural ranges and terminal
denominators frozen at the selection-parent commit.  No endpoint, page,
field value, prediction, evaluator, score, or per-task outcome participates
in selection.  The vector is indivisible and grouped consecutively four
identities per task.

Questions preserve the visible schema and RFC Editor authority phrase used
by the label-blind production runtime.  This pure module performs no I/O and
authorizes neither forward execution nor evaluation.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


POLICY_ID = "v25452_structurally_disjoint_official_xml_population_v1"
SELECTION_PARENT_COMMIT = "8bfe64a59d2fd300d3dc4decf7155e2c575fea1a"
TASK_COUNT = 20
ROWS_PER_TASK = 4
RFC_NUMBERS = tuple(range(9000, 9080))
COLUMNS = ("RFC", "Title", "Authors", "Status", "Stream", "Published")
SELECTION_RULE = "immediately_preceding_whole_block"
CONSUMED_INTERVALS = (
    (9080, 9159),
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
    "648d138a3b2c5fa3639f8fda4c62e9ac36eb75422fb12417707efdde062448d8"
)
EXPECTED_GROUP_VECTOR_SHA256 = (
    "164074f14666b0da96bdfa71ce24f09ccfbabbcbe412d4b3e8f8be6f9ddf28a5"
)
EXPECTED_TASK_VECTOR_SHA256 = (
    "01b13ce11f3bd74304bff2ba9f728b292ab6cd4807484cb96e89bd4a77753f59"
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
        RFC_NUMBERS != tuple(range(9000, 9080))
        or len(values) != TASK_COUNT * ROWS_PER_TASK
        or len(set(values)) != len(values)
        or any(re.fullmatch(r"RFC 9[0-9]{3}", value) is None for value in values)
        or (
            EXPECTED_IDENTITY_VECTOR_SHA256 != "TO_BE_FROZEN"
            and observed != EXPECTED_IDENTITY_VECTOR_SHA256
        )
    ):
        raise RuntimeError("V2.54.52 RFC identity vector drifted")
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
            f"v25452:{task_index}:{question}".encode()
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
        raise RuntimeError("V2.54.52 group vector drifted")
    return checked


def task_vector() -> list[dict[str, str]]:
    values = [dict(group["task"]) for group in group_vector()]
    observed = payload_sha256(values)
    if (
        EXPECTED_TASK_VECTOR_SHA256 != "TO_BE_FROZEN"
        and observed != EXPECTED_TASK_VECTOR_SHA256
    ):
        raise RuntimeError("V2.54.52 task vector drifted")
    return values


def validate_group_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.54.52 task denominator drifted")
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
            raise ValueError("V2.54.52 group shape drifted")
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
            raise ValueError("V2.54.52 task binding drifted")
        opaque_ids.append(task["opaque_id"])
        output.append(
            {
                "task_index": task_index,
                "identity_count": ROWS_PER_TASK,
                "task": dict(task),
            }
        )
    if len(set(opaque_ids)) != TASK_COUNT:
        raise ValueError("V2.54.52 opaque identity collision")
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
        "candidate_additional_queries": 0,
        "candidate_additional_model_calls": 0,
        "candidate_maximum_additional_fetches": 4,
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
