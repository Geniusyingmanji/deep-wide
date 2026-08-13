"""Fresh outcome-blind paired RFC population for the V2.54.11 route gate.

The complete RFC 9320--9399 interval was selected as the first whole
predeclared candidate interval whose parent tree and ancestor history had no
canonical identity or slug match.  The interval is indivisible: no identity,
pair, or task is retained, removed, replaced, or ranked using a page,
endpoint, model response, evaluator, score, or quality observation.

Each four-identity group produces one fixed pair.  The membership-absent task
states the same visible identities without a parser-recognized tag; the
membership-present task adds only the strict plural ``RFCS`` wrapper.  Both
members otherwise have the same source request, schema, identity order, row
cardinality, and rendering contract.  V2.54.11 must route the first to the
frozen V2.53.75 runtime and the second to V2.54.01 using visible text only.

This pure data module grants no model, network, search, fetch, evaluator,
benchmark, retry, replacement, or signed-credit authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from . import v25395_visible_membership_synthesis_runtime as membership
from . import v25411_visible_membership_route_runtime as route


POLICY_ID = "v25413_fresh_outcome_blind_paired_rfc_route_population_v1"
FRESHNESS_PARENT_COMMIT = "01944cc529e8ba22acd6ca337d1baccd53a9bfd0"
PAIR_COUNT = 20
TASK_COUNT = 40
ROWS_PER_PAIR = 4
ARMS = (route.STABLE_BRANCH, route.MEMBERSHIP_BRANCH)
RFC_NUMBERS = tuple(range(9320, 9400))
COLUMNS = ("RFC", "Title", "Authors", "Status", "Stream", "Published")
EXPECTED_IDENTITY_VECTOR_SHA256 = (
    "e65617aa236e8344843b5424850a420700a0f6c44f8f05487c54f7ae591b65bd"
)
EXPECTED_TASK_VECTOR_SHA256 = (
    "19d47d056bcf8ba59eb5d8479c59317a7d144e6a67efbe0807c25130fe3fb758"
)
EXPECTED_PAIR_VECTOR_SHA256 = (
    "36fa1c8f7981156469918d5c9dbe889fcf2ad59a6bfd1e9c8d7386de38f30ed9"
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
        RFC_NUMBERS != tuple(range(9320, 9400))
        or len(values) != PAIR_COUNT * ROWS_PER_PAIR
        or len(set(values)) != len(values)
        or any(re.fullmatch(r"RFC 93[2-9][0-9]", value) is None for value in values)
        or (
            EXPECTED_IDENTITY_VECTOR_SHA256 != "TO_BE_FROZEN"
            and observed != EXPECTED_IDENTITY_VECTOR_SHA256
        )
    ):
        raise RuntimeError("V2.54.13 RFC identity vector drifted")
    return values


def _group(pair_index: int) -> tuple[str, ...]:
    identities = identity_vector()
    start = pair_index * ROWS_PER_PAIR
    return tuple(identities[start : start + ROWS_PER_PAIR])


def _question(group: Sequence[str], branch: str) -> str:
    vector = "; ".join(group)
    if branch == route.STABLE_BRANCH:
        visible = vector
    elif branch == route.MEMBERSHIP_BRANCH:
        visible = f"<RFCS>{vector}</RFCS>"
    else:
        raise ValueError("V2.54.13 branch is unknown")
    return (
        "Use public web sources and the official RFC Editor index/detail "
        "pages to return exactly one Markdown table and no prose for the "
        f"four visible document identities {visible}. Columns exactly: "
        + " | ".join(COLUMNS)
        + ". The table must contain exactly four data records in the same "
        "identifier order shown above and no other data records. The RFC cell "
        "must use the visible `RFC NNNN` form. Title, Authors, Status, Stream, "
        "and Published must all belong to that same RFC Editor metadata "
        "record. Preserve official spelling and ordering; render Published as "
        "shown by the official source. Use Unknown only when same-forward "
        "fetched public pages do not establish a value."
    )


def pair_vector() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for pair_index in range(PAIR_COUNT):
        group = _group(pair_index)
        tasks: dict[str, dict[str, str]] = {}
        for branch in ARMS:
            question = _question(group, branch)
            opaque = "task_" + hashlib.sha256(
                f"v25413:{pair_index}:{branch}:{question}".encode()
            ).hexdigest()[:24]
            tasks[branch] = {"opaque_id": opaque, "question": question}
        output.append(
            {
                "pair_index": pair_index,
                "identity_count": len(group),
                "tasks": tasks,
            }
        )
    checked = validate_pair_vector(output)
    observed = payload_sha256(checked)
    if (
        EXPECTED_PAIR_VECTOR_SHA256 != "TO_BE_FROZEN"
        and observed != EXPECTED_PAIR_VECTOR_SHA256
    ):
        raise RuntimeError("V2.54.13 pair vector hash drifted")
    return checked


def task_vector() -> list[dict[str, str]]:
    rows = [
        dict(pair["tasks"][branch])
        for pair in pair_vector()
        for branch in ARMS
    ]
    observed = payload_sha256(rows)
    if (
        EXPECTED_TASK_VECTOR_SHA256 != "TO_BE_FROZEN"
        and observed != EXPECTED_TASK_VECTOR_SHA256
    ):
        raise RuntimeError("V2.54.13 task vector hash drifted")
    return rows


def validate_pair_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if isinstance(values, (str, bytes)) or len(values) != PAIR_COUNT:
        raise ValueError("V2.54.13 pair denominator drifted")
    output: list[dict[str, Any]] = []
    opaque_ids: list[str] = []
    all_identities = identity_vector()
    for pair_index, raw in enumerate(values):
        if (
            not isinstance(raw, Mapping)
            or set(raw) != {"pair_index", "identity_count", "tasks"}
            or raw.get("pair_index") != pair_index
            or raw.get("identity_count") != ROWS_PER_PAIR
            or not isinstance(raw.get("tasks"), Mapping)
            or set(raw["tasks"]) != set(ARMS)
        ):
            raise ValueError("V2.54.13 pair shape drifted")
        group = _group(pair_index)
        checked_tasks: dict[str, dict[str, str]] = {}
        for branch in ARMS:
            task = raw["tasks"][branch]
            expected_question = _question(group, branch)
            if (
                not isinstance(task, Mapping)
                or set(task) != {"opaque_id", "question"}
                or not isinstance(task.get("opaque_id"), str)
                or re.fullmatch(r"task_[0-9a-f]{24}", task["opaque_id"])
                is None
                or task.get("question") != expected_question
                or route.route_for_visible_question(expected_question) != branch
                or any(
                    identity in expected_question
                    for identity in all_identities
                    if identity not in group
                )
                or "https://" in expected_question
            ):
                raise ValueError("V2.54.13 paired task binding drifted")
            members, source = membership.visible_membership(expected_question)
            if branch == route.STABLE_BRANCH:
                if members or source != "none" or "<RFCS>" in expected_question:
                    raise ValueError("V2.54.13 absent route drifted")
            elif members != group or source != "plural_inline_tag_vector":
                raise ValueError("V2.54.13 present route drifted")
            opaque_ids.append(task["opaque_id"])
            checked_tasks[branch] = dict(task)
        absent = checked_tasks[route.STABLE_BRANCH]["question"]
        present = checked_tasks[route.MEMBERSHIP_BRANCH]["question"]
        vector = "; ".join(group)
        if present.replace(f"<RFCS>{vector}</RFCS>", vector) != absent:
            raise ValueError("V2.54.13 pair differs beyond membership wrapper")
        output.append(
            {
                "pair_index": pair_index,
                "identity_count": ROWS_PER_PAIR,
                "tasks": checked_tasks,
            }
        )
    if len(opaque_ids) != TASK_COUNT or len(set(opaque_ids)) != TASK_COUNT:
        raise ValueError("V2.54.13 opaque identity collision")
    return output


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "twenty_fixed_pairs_and_forty_fixed_tasks": True,
        "four_identical_visible_rfc_identities_per_pair": True,
        "only_pair_difference_is_strict_plural_membership_wrapper": True,
        "same_source_schema_identity_order_cardinality_and_rendering_contract_per_pair": True,
        "membership_absent_route_is_v25375": True,
        "membership_present_route_is_v25401": True,
        "route_uses_only_visible_question_membership": True,
        "population_is_one_consecutive_indivisible_eighty_identity_vector": True,
        "population_fixed_before_candidate_page_endpoint_model_or_evaluator_access": True,
        "freshness_bound_to_parent_tree_and_ancestor_history_zero_match": True,
        "official_rfc_metadata_surface_not_used_to_select_or_replace_tasks": True,
        "fixed_failure_as_zero_denominator_no_retry_resume_or_replacement": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "deepwidebench_forward_evaluator_leaderboard_or_sota_authorized": False,
    }


def route_gate() -> dict[str, Any]:
    return {
        "fixed_pair_denominator": PAIR_COUNT,
        "fixed_task_denominator": TASK_COUNT,
        "required_terminal_tasks": TASK_COUNT,
        "required_membership_absent_tasks": PAIR_COUNT,
        "required_membership_present_tasks": PAIR_COUNT,
        "required_membership_absent_completed_tasks": PAIR_COUNT,
        "minimum_membership_present_completed_tasks": 18,
        "maximum_membership_absent_outer_failure_tasks": 0,
        "maximum_membership_present_outer_failure_tasks": 2,
        "required_membership_absent_parent_role_tasks": PAIR_COUNT,
        "minimum_membership_present_parent_role_tasks": 18,
        "required_failure_stage_receipts_for_every_outer_failure": True,
        "maximum_naked_outer_failure_tasks": 0,
        "minimum_present_grounded_record_constraint_applied_tasks": 18,
        "minimum_present_grounded_raw_record_tasks": 4,
        "minimum_present_grounded_raw_record_count": 4,
        "maximum_present_grounded_membership_violation_count": 2,
        "minimum_present_verified_record_tasks": 2,
        "maximum_unattributable_prediction_changed_tasks": 0,
        "maximum_budget_rejection_tasks": 0,
        "exact_physical_queries_per_completed_task": 4,
        "maximum_physical_fetches_per_completed_task": 14,
        "exact_normal_path_model_forwards_per_completed_task": 3,
        "all_content_free_receipts_valid": True,
        "positive_signed_credit_count": 0,
        "postfreeze_matched_quality_required_after_route_gate_go": True,
    }


__all__ = [
    "ARMS",
    "COLUMNS",
    "EXPECTED_IDENTITY_VECTOR_SHA256",
    "EXPECTED_PAIR_VECTOR_SHA256",
    "EXPECTED_TASK_VECTOR_SHA256",
    "FRESHNESS_PARENT_COMMIT",
    "PAIR_COUNT",
    "POLICY_ID",
    "RFC_NUMBERS",
    "ROWS_PER_PAIR",
    "TASK_COUNT",
    "identity_vector",
    "pair_vector",
    "payload_sha256",
    "route_gate",
    "source_policy",
    "task_vector",
    "validate_pair_vector",
]
