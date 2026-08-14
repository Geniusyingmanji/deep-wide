"""Fresh task-disjoint population for the IANA delegation-layout treatment.

The pair vector is copied exactly from the pushed V2.55.35 official-name
selection snapshot: the first forty unconsumed identities after
``.bradesco`` in IANA alphabetic order, from ``.bridgestone`` through
``.cbre``.  Seven historical ccTLDs were mechanically skipped by the frozen
name-only rule.  No detail endpoint, page, field value, question, prediction,
quality, or outcome was used for selection.

Each question exposes exactly two row keys and the requested schema, but no
URL, authority name, host, path, IANA layout grammar, field value, coverage,
prediction, or evaluator signal.  Runtime input remains exactly
``{opaque_id, question}`` plus same-forward public pages.  This pure module
performs no I/O, assigns zero entropy/IG signed credit, and authorizes neither
a forward nor an evaluator.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


POLICY_ID = "v25536_fresh_iana_delegation_layout_population_v1"
SELECTION_PARENT_COMMIT = "58d14c197260604b1db6e6f57ecfa014625dfc90"
SELECTION_SNAPSHOT = "results/v25535_skip_consumed_tld_selection_v1_20260814.json"
SELECTION_SNAPSHOT_SHA256 = (
    "c64cc6a5bb79fd37e7ee0837e17d9911e649c5ea0e9061e95385bd69afe8a6d7"
)
SELECTION_RULE = (
    "first_forty_unconsumed_official_names_after_bradesco_in_alphabetic_order"
)
TASK_COUNT = 20
ROWS_PER_TASK = 2
COLUMNS = ("Domain", "Type", "TLD Manager")
PAIRS = (
    (".bridgestone", ".broadway"),
    (".broker", ".brother"),
    (".brussels", ".build"),
    (".builders", ".business"),
    (".buy", ".buzz"),
    (".bzh", ".cab"),
    (".cafe", ".cal"),
    (".call", ".calvinklein"),
    (".cam", ".camera"),
    (".camp", ".canon"),
    (".capetown", ".capital"),
    (".capitalone", ".car"),
    (".caravan", ".cards"),
    (".care", ".career"),
    (".careers", ".cars"),
    (".casa", ".case"),
    (".cash", ".casino"),
    (".cat", ".catering"),
    (".catholic", ".cba"),
    (".cbn", ".cbre"),
)
EXPECTED_PAIR_VECTOR_SHA256 = (
    "703c3961d249476d8b6bc6440fbb835378cf04ffc97d2465abf6d0b6196bd0f9"
)
EXPECTED_IDENTITY_VECTOR_SHA256 = (
    "d2e0ba474cf5d3a57d8f7190a3a7dff8988c6e751548d027513d55ed1e834457"
)
EXPECTED_TASK_VECTOR_SHA256 = (
    "fe6fc87bc35c7f91f0b94d8d8dc413e62ede56892df0beea7d5920400b7ea096"
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


def pair_vector() -> list[tuple[str, str]]:
    values = list(PAIRS)
    flattened = [identity for pair in values for identity in pair]
    if (
        len(values) != TASK_COUNT
        or any(len(pair) != ROWS_PER_TASK for pair in values)
        or len(flattened) != TASK_COUNT * ROWS_PER_TASK
        or len(set(flattened)) != len(flattened)
        or flattened != sorted(flattened)
        or flattened[0] != ".bridgestone"
        or flattened[-1] != ".cbre"
        or any(
            re.fullmatch(r"\.[a-z][a-z0-9-]{2,62}", identity) is None
            or len(identity.removeprefix(".")) < 3
            for identity in flattened
        )
        or payload_sha256(values) != EXPECTED_PAIR_VECTOR_SHA256
        or payload_sha256(flattened) != EXPECTED_IDENTITY_VECTOR_SHA256
    ):
        raise RuntimeError("V2.55.36 pair vector drifted")
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
            f"v25536:{index}:{question}".encode()
        ).hexdigest()[:24]
        values.append({"opaque_id": opaque, "question": question})
    checked = validate_task_vector(values)
    observed = payload_sha256(checked)
    if (
        EXPECTED_TASK_VECTOR_SHA256 != "TO_BE_FROZEN"
        and observed != EXPECTED_TASK_VECTOR_SHA256
    ):
        raise RuntimeError("V2.55.36 task vector hash drifted")
    return checked


def validate_task_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.55.36 task denominator drifted")
    output: list[dict[str, str]] = []
    ids: list[str] = []
    for raw, (first, second) in zip(values, pair_vector(), strict=True):
        if not isinstance(raw, Mapping) or set(raw) != {"opaque_id", "question"}:
            raise ValueError("V2.55.36 runtime input shape drifted")
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
            or "delegation" in question.casefold()
            or "sponsoring organisation" in question.casefold()
            or "parenthetical" in question.casefold()
            or "coverage" in question.casefold()
        ):
            raise ValueError("V2.55.36 visible task binding drifted")
        ids.append(opaque)
        output.append({"opaque_id": opaque, "question": question})
    if len(set(ids)) != TASK_COUNT:
        raise ValueError("V2.55.36 opaque identity collision")
    return output


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": [
            "opaque_id",
            "question",
            "same_forward_public_pages",
        ],
        "selection_snapshot": SELECTION_SNAPSHOT,
        "selection_rule": SELECTION_RULE,
        "visible_task_input_contains_exactly_two_row_keys_and_requested_schema": True,
        "no_visible_url_source_host_authority_name_path_layout_grammar_coverage_or_field_value": True,
        "whole_static_pair_block_frozen_before_any_forward": True,
        "all_prior_tld_populations_and_v25527_research_identities_excluded": True,
        "prior_task_rows_pages_predictions_truth_scores_quality_or_per_task_outcomes_read": False,
        "individual_pair_or_task_filtering_ranking_replacement_or_retention": False,
        "detail_page_layout_type_manager_prediction_evaluator_or_quality_used_for_selection": False,
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
        "maximum_naked_outer_failure_tasks": 0,
        "maximum_budget_rejection_tasks": 0,
        "required_parent_role_tasks": TASK_COUNT,
        "required_exact_canonical_control_tasks": TASK_COUNT,
        "minimum_multirow_eligible_link_tasks": 6,
        "minimum_positive_evidence_deficit_candidate_tasks": 4,
        "minimum_logical_detail_request_tasks": 4,
        "minimum_admitted_detail_fetch_tasks": 4,
        "minimum_exact_nonredirected_detail_page_tasks": 3,
        "minimum_exact_iana_url_page_tasks": 3,
        "minimum_url_row_key_bound_page_tasks": 3,
        "minimum_identity_surface_bound_page_tasks": 3,
        "minimum_iana_delegation_heading_surface_tasks": 3,
        "minimum_iana_parenthetical_type_surface_tasks": 3,
        "minimum_iana_sponsoring_organisation_surface_tasks": 3,
        "minimum_iana_layout_complete_page_tasks": 2,
        "minimum_raw_field_surface_tasks": 4,
        "minimum_evidence_closed_observation_tasks": 4,
        "minimum_material_candidate_tasks": 2,
        "minimum_applied_coordinate_count_total": 4,
        "minimum_treatment_changed_tasks": 2,
        "minimum_treatment_changed_coordinate_count_total": 4,
        "maximum_candidate_application_failure_tasks": 0,
        "exact_physical_queries_per_completed_task": 4,
        "maximum_physical_fetches_per_completed_task": 14,
        "maximum_normal_path_model_forwards_per_completed_task": 3,
        "one_parent_forward_per_task": True,
        "candidate_additional_queries_beyond_parent": 0,
        "candidate_additional_fetches_beyond_parent": 0,
        "candidate_additional_model_calls_beyond_parent": 0,
        "control_and_candidate_predictions_frozen_per_task": True,
        "positive_signed_credit_count": 0,
        "postfreeze_shared_parent_quality_required": True,
    }


__all__ = [
    "COLUMNS",
    "EXPECTED_IDENTITY_VECTOR_SHA256",
    "EXPECTED_PAIR_VECTOR_SHA256",
    "EXPECTED_TASK_VECTOR_SHA256",
    "PAIRS",
    "POLICY_ID",
    "ROWS_PER_TASK",
    "SELECTION_PARENT_COMMIT",
    "SELECTION_RULE",
    "SELECTION_SNAPSHOT",
    "SELECTION_SNAPSHOT_SHA256",
    "TASK_COUNT",
    "mechanism_gate",
    "pair_vector",
    "payload_sha256",
    "source_policy",
    "task_vector",
    "validate_task_vector",
]
