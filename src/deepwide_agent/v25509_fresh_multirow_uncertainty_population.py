"""Fresh task-disjoint population for visible multi-row uncertainty routing.

The prior external populations all target country-code top-level domains,
whose visible or latent row identities have exactly two ASCII letters after
the dot.  This module freezes one whole static block of twenty pairs drawn
from top-level-domain identities with at least three characters after the dot.
The forty row identities are therefore structurally disjoint from every prior
ccTLD identity without opening any prior task row, page, prediction, truth, or
per-task outcome.

Each question exposes exactly two row keys and the requested schema, but no
URL, source host/name, field grammar, Type value, TLD Manager value, prediction,
or evaluator signal.  The same-forward search pages and completed control table
must establish any visible link, uncertainty priority, detail page, and edit.
The whole block is frozen before any forward and cannot be filtered, ranked,
replaced, retried, or backfilled using outcomes.

This pure module performs no I/O, assigns zero entropy/IG signed credit, and
authorizes neither a forward nor an evaluator.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


POLICY_ID = "v25509_fresh_multirow_uncertainty_population_v1"
SELECTION_PARENT_COMMIT = "dc816532e8af09393875ffa35eb9885b15df2299"
TASK_COUNT = 20
ROWS_PER_TASK = 2
COLUMNS = ("Domain", "Type", "TLD Manager")
SELECTION_RULE = (
    "one_whole_static_twenty_pair_block_of_three_plus_character_tld_identities"
)

PAIRS = (
    (".aaa", ".aarp"),
    (".abb", ".abbott"),
    (".abbvie", ".abc"),
    (".able", ".abogado"),
    (".abudhabi", ".academy"),
    (".accenture", ".accountant"),
    (".accountants", ".aco"),
    (".actor", ".ads"),
    (".adult", ".aeg"),
    (".aero", ".aetna"),
    (".afl", ".africa"),
    (".agakhan", ".agency"),
    (".aig", ".airbus"),
    (".airforce", ".airtel"),
    (".akdn", ".alfaromeo"),
    (".alibaba", ".alipay"),
    (".allfinanz", ".allstate"),
    (".ally", ".alsace"),
    (".alstom", ".amazon"),
    (".americanexpress", ".americanfamily"),
)
EXPECTED_PAIR_VECTOR_SHA256 = (
    "c10f23631c2b2820f95446945c5f61e40a610fc84068c544e87c16b060bc7dff"
)
EXPECTED_TASK_VECTOR_SHA256 = (
    "161a751cfbff9ef4dbcdaf031a84002ea3b9f4d36527852ba08afc11c2665b5e"
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def pair_vector() -> list[tuple[str, str]]:
    values = list(PAIRS)
    flattened = [identity for pair in values for identity in pair]
    if (
        len(values) != TASK_COUNT
        or any(len(pair) != ROWS_PER_TASK for pair in values)
        or len(flattened) != TASK_COUNT * ROWS_PER_TASK
        or len(set(flattened)) != len(flattened)
        or any(
            re.fullmatch(r"\.[a-z][a-z0-9-]{2,62}", identity) is None
            or len(identity.removeprefix(".")) < 3
            for identity in flattened
        )
    ):
        raise RuntimeError("V2.55.09 pair vector drifted")
    observed = payload_sha256(values)
    if (
        EXPECTED_PAIR_VECTOR_SHA256 != "TO_BE_FROZEN"
        and observed != EXPECTED_PAIR_VECTOR_SHA256
    ):
        raise RuntimeError("V2.55.09 pair vector hash drifted")
    return values


def _question(first: str, second: str) -> str:
    return (
        "Use public web search and authoritative public sources to return exactly "
        "one Markdown table and no prose for the two visible top-level domains "
        f"<DOMAIN>{first}</DOMAIN> and <DOMAIN>{second}</DOMAIN>. Columns exactly: "
        "Domain | Type | TLD Manager. Return exactly two rows, one for each "
        "supplied domain, in the supplied order. Preserve exact spelling and use "
        "Domain, Type, and TLD Manager from the same identity-bound public source "
        "for each row. Use Unknown only when same-forward fetched public pages do "
        "not establish a value."
    )


def task_vector() -> list[dict[str, str]]:
    values: list[dict[str, str]] = []
    for index, (first, second) in enumerate(pair_vector()):
        question = _question(first, second)
        opaque = "task_" + hashlib.sha256(
            f"v25509:{index}:{question}".encode()
        ).hexdigest()[:24]
        values.append({"opaque_id": opaque, "question": question})
    checked = validate_task_vector(values)
    observed = payload_sha256(checked)
    if (
        EXPECTED_TASK_VECTOR_SHA256 != "TO_BE_FROZEN"
        and observed != EXPECTED_TASK_VECTOR_SHA256
    ):
        raise RuntimeError("V2.55.09 task vector hash drifted")
    return checked


def validate_task_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.55.09 task denominator drifted")
    output: list[dict[str, str]] = []
    ids: list[str] = []
    for raw, (first, second) in zip(values, pair_vector(), strict=True):
        if not isinstance(raw, Mapping) or set(raw) != {"opaque_id", "question"}:
            raise ValueError("V2.55.09 runtime input shape drifted")
        opaque = raw.get("opaque_id")
        question = raw.get("question")
        if (
            not isinstance(opaque, str)
            or re.fullmatch(r"task_[0-9a-f]{24}", opaque) is None
            or not isinstance(question, str)
            or question != _question(first, second)
            or question.count(f"<DOMAIN>{first}</DOMAIN>") != 1
            or question.count(f"<DOMAIN>{second}</DOMAIN>") != 1
            or "Columns exactly: " + " | ".join(COLUMNS) not in question
            or "https://" in question
            or "iana" in question.casefold()
            or "qualifier" in question.casefold()
            or "adjacent" in question.casefold()
            or "fused" in question.casefold()
        ):
            raise ValueError("V2.55.09 visible task binding drifted")
        ids.append(opaque)
        output.append({"opaque_id": opaque, "question": question})
    if len(set(ids)) != TASK_COUNT:
        raise ValueError("V2.55.09 opaque identity collision")
    return output


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": [
            "opaque_id",
            "question",
            "same_forward_public_pages",
        ],
        "visible_task_input_contains_exactly_two_row_keys_and_requested_schema": True,
        "no_visible_url_source_host_authority_name_field_grammar_or_field_value": True,
        "whole_static_pair_block_frozen_before_any_forward": True,
        "three_plus_character_identifiers_are_structurally_disjoint_from_prior_two_letter_cctlds": True,
        "prior_task_rows_pages_predictions_truth_scores_or_per_task_outcomes_read": False,
        "individual_pair_or_task_filtering_ranking_replacement_or_retention": False,
        "detail_page_type_manager_prediction_evaluator_or_quality_used_for_selection": False,
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
        "required_exact_canonical_control_tasks": TASK_COUNT,
        "minimum_multirow_eligible_link_tasks": 6,
        "minimum_positive_uncertainty_candidate_tasks": 4,
        "minimum_logical_detail_request_tasks": 4,
        "minimum_admitted_detail_fetch_tasks": 4,
        "minimum_exact_nonredirected_detail_page_tasks": 3,
        "minimum_combined_generic_observation_tasks": 3,
        "minimum_treatment_changed_tasks": 2,
        "minimum_treatment_changed_coordinate_count_total": 2,
        "maximum_control_application_failure_tasks": 0,
        "maximum_candidate_application_failure_tasks": 0,
        "exact_physical_queries_per_completed_task": 4,
        "maximum_physical_fetches_per_completed_task": 14,
        "maximum_normal_path_model_forwards_per_completed_task": 3,
        "one_parent_forward_per_task": True,
        "candidate_additional_queries": 0,
        "candidate_additional_model_calls": 0,
        "maximum_candidate_additional_fetches": 1,
        "control_and_candidate_predictions_frozen_per_task": True,
        "positive_signed_credit_count": 0,
        "postfreeze_shared_parent_quality_required": True,
    }


__all__ = [
    "COLUMNS",
    "EXPECTED_PAIR_VECTOR_SHA256",
    "EXPECTED_TASK_VECTOR_SHA256",
    "PAIRS",
    "POLICY_ID",
    "ROWS_PER_TASK",
    "SELECTION_PARENT_COMMIT",
    "SELECTION_RULE",
    "TASK_COUNT",
    "mechanism_gate",
    "pair_vector",
    "payload_sha256",
    "source_policy",
    "task_vector",
    "validate_task_vector",
]
