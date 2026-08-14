"""Fifth fresh outcome-blind population for the generic grammar gate.

Every capital/currency clue from the four V2.54.86 consumed blocks and the
V2.54.86 selected block counts as consumed in full.  This module freezes the
first whole static block of twenty clues with zero overlap against that
hundred-clue union.  It never reads a country/TLD mapping, URL, page, field
value, prediction, evaluator, score, quality result, or per-task outcome.

Questions expose only a capital/currency clue, a public source request, and
the requested schema.  Country and ccTLD identities, URLs, membership tags,
field grammar hints, and source-shape hints remain hidden.  The completed
parent table and same-forward pages must establish any candidate.  This pure
module performs no I/O, assigns zero entropy/IG credit, and authorizes neither
a forward nor an evaluator.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from . import v25486_outcome_blind_iana_detail_population as prior


POLICY_ID = "v25502_fifth_fresh_generic_mechanical_population_v1"
SELECTION_PARENT_COMMIT = "7eb8332d317f7b312571e0e02c3eac3b909fe0c2"
TASK_COUNT = 20
COLUMNS = ("Domain", "Type", "TLD Manager")
SELECTION_RULE = "first_whole_static_twenty_clue_block_with_zero_hundred_clue_union_overlap"

V25027_CONSUMED_PUBLIC_CLUES = prior.V25027_CONSUMED_PUBLIC_CLUES
V25469_CONSUMED_PUBLIC_CLUES = prior.V25469_CONSUMED_PUBLIC_CLUES
V25476_CONSUMED_PUBLIC_CLUES = prior.V25476_CONSUMED_PUBLIC_CLUES
V25481_CONSUMED_PUBLIC_CLUES = prior.V25481_CONSUMED_PUBLIC_CLUES
V25488_CONSUMED_PUBLIC_CLUES = prior.CLUES
CONSUMED_PUBLIC_CLUES = (
    V25027_CONSUMED_PUBLIC_CLUES
    + V25469_CONSUMED_PUBLIC_CLUES
    + V25476_CONSUMED_PUBLIC_CLUES
    + V25481_CONSUMED_PUBLIC_CLUES
    + V25488_CONSUMED_PUBLIC_CLUES
)

CANDIDATE_BLOCKS = (
    V25488_CONSUMED_PUBLIC_CLUES,
    (
        ("Vaduz", "CHF"),
        ("Vilnius", "EUR"),
        ("Luxembourg", "EUR"),
        ("Antananarivo", "MGA"),
        ("Lilongwe", "MWK"),
        ("Kuala Lumpur", "MYR"),
        ("Male", "MVR"),
        ("Bamako", "XOF"),
        ("Valletta", "EUR"),
        ("Majuro", "USD"),
        ("Nouakchott", "MRU"),
        ("Port Louis", "MUR"),
        ("Mexico City", "MXN"),
        ("Palikir", "USD"),
        ("Chisinau", "MDL"),
        ("Monaco", "EUR"),
        ("Ulaanbaatar", "MNT"),
        ("Podgorica", "EUR"),
        ("Rabat", "MAD"),
        ("Maputo", "MZN"),
    ),
)
SELECTED_BLOCK_INDEX = 1
CLUES = CANDIDATE_BLOCKS[SELECTED_BLOCK_INDEX]
EXPECTED_CLUE_VECTOR_SHA256 = (
    "fe9e9f6e6ac26274d19e12c2e35da59d07b33fe1c794b666fa67698a81e149ea"
)
EXPECTED_TASK_VECTOR_SHA256 = (
    "66d166203cc4660553832fb7e082468d82067c021ec275969cfcb0a5c9ee95af"
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def selected_clues() -> list[tuple[str, str]]:
    consumed = set(CONSUMED_PUBLIC_CLUES)
    overlaps = [
        len(set(block).intersection(consumed)) for block in CANDIDATE_BLOCKS
    ]
    selected = tuple(CANDIDATE_BLOCKS[SELECTED_BLOCK_INDEX])
    if (
        len(CONSUMED_PUBLIC_CLUES) != 100
        or len(set(CONSUMED_PUBLIC_CLUES)) != 100
        or any(
            len(block) != TASK_COUNT or len(set(block)) != TASK_COUNT
            for block in CANDIDATE_BLOCKS
        )
        or overlaps[SELECTED_BLOCK_INDEX] != 0
        or SELECTED_BLOCK_INDEX
        != next((index for index, overlap in enumerate(overlaps) if overlap == 0), -1)
        or selected != CLUES
    ):
        raise RuntimeError("V2.55.02 clue selection drifted")
    values = list(selected)
    observed = payload_sha256(values)
    if (
        EXPECTED_CLUE_VECTOR_SHA256 != "TO_BE_FROZEN"
        and observed != EXPECTED_CLUE_VECTOR_SHA256
    ):
        raise RuntimeError("V2.55.02 clue vector hash drifted")
    return values


def _question(capital: str, code: str) -> str:
    return (
        f"Identify the jurisdiction whose capital is {capital} and whose official "
        f"currency has ISO 4217 code {code}. Then use public web search and "
        "authoritative public sources to return exactly one Markdown table and "
        "no prose for that jurisdiction's country-code top-level domain. Columns "
        "exactly: Domain | Type | TLD Manager. Return exactly one row. Preserve "
        "exact spelling and use Domain, Type, and TLD Manager from the same "
        "identity-bound public source. Use Unknown only when same-forward fetched "
        "public pages do not establish a value."
    )


def task_vector() -> list[dict[str, str]]:
    values = []
    for index, (capital, code) in enumerate(selected_clues()):
        question = _question(capital, code)
        opaque = "task_" + hashlib.sha256(
            f"v25502:{index}:{question}".encode()
        ).hexdigest()[:24]
        values.append({"opaque_id": opaque, "question": question})
    checked = validate_task_vector(values)
    observed = payload_sha256(checked)
    if (
        EXPECTED_TASK_VECTOR_SHA256 != "TO_BE_FROZEN"
        and observed != EXPECTED_TASK_VECTOR_SHA256
    ):
        raise RuntimeError("V2.55.02 task vector hash drifted")
    return checked


def validate_task_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.55.02 task denominator drifted")
    output: list[dict[str, str]] = []
    ids: list[str] = []
    for raw, (capital, code) in zip(values, selected_clues(), strict=True):
        if not isinstance(raw, Mapping) or set(raw) != {"opaque_id", "question"}:
            raise ValueError("V2.55.02 runtime input shape drifted")
        opaque = raw.get("opaque_id")
        question = raw.get("question")
        if (
            not isinstance(opaque, str)
            or re.fullmatch(r"task_[0-9a-f]{24}", opaque) is None
            or not isinstance(question, str)
            or question != _question(capital, code)
            or any(column not in question for column in COLUMNS)
            or "<ENTITIES>" in question
            or "<DOMAIN>" in question
            or "https://" in question
            or "iana" in question.casefold()
            or re.search(r"\.[a-z]{2}\b", question.casefold()) is not None
        ):
            raise ValueError("V2.55.02 visible task binding drifted")
        ids.append(opaque)
        output.append({"opaque_id": opaque, "question": question})
    if len(set(ids)) != TASK_COUNT:
        raise ValueError("V2.55.02 opaque identity collision")
    return output


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": [
            "opaque_id",
            "question",
            "same_forward_public_pages",
        ],
        "visible_population_contains_capital_currency_clues_but_no_country_or_tld_mapping": True,
        "no_visible_membership_row_key_url_authority_host_or_field_grammar_hint": True,
        "parent_completed_table_must_supply_candidate_row_key": True,
        "selection_is_first_whole_static_block_with_zero_hundred_clue_union_overlap": True,
        "all_five_prior_authorized_population_blocks_count_as_consumed": True,
        "prior_mechanism_no_go_population_still_consumed": True,
        "individual_clue_or_task_retention_replacement_or_ranking": False,
        "country_tld_mapping_endpoint_page_field_value_prediction_or_evaluator_used_for_selection": False,
        "historical_population_forward_page_prediction_score_metric_quality_or_per_task_outcome_read": False,
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
        "minimum_combined_candidate_page_tasks": 18,
        "minimum_generic_mechanical_field_surface_tasks": 6,
        "minimum_generic_mechanical_observation_tasks": 4,
        "minimum_available_candidate_tasks": 2,
        "minimum_applied_candidate_tasks": 2,
        "minimum_prediction_changed_tasks": 2,
        "maximum_application_failure_tasks": 0,
        "exact_physical_queries_per_completed_task": 4,
        "maximum_physical_fetches_per_completed_task": 14,
        "maximum_normal_path_model_forwards_per_completed_task": 3,
        "one_parent_forward_per_task": True,
        "candidate_additional_queries": 0,
        "candidate_additional_model_calls": 0,
        "maximum_candidate_additional_fetches": 1,
        "base_and_candidate_predictions_frozen_per_task": True,
        "positive_signed_credit_count": 0,
        "postfreeze_shared_parent_quality_required": True,
    }


__all__ = [
    "CANDIDATE_BLOCKS",
    "CLUES",
    "COLUMNS",
    "CONSUMED_PUBLIC_CLUES",
    "EXPECTED_CLUE_VECTOR_SHA256",
    "EXPECTED_TASK_VECTOR_SHA256",
    "POLICY_ID",
    "SELECTED_BLOCK_INDEX",
    "SELECTION_PARENT_COMMIT",
    "SELECTION_RULE",
    "TASK_COUNT",
    "V25027_CONSUMED_PUBLIC_CLUES",
    "V25469_CONSUMED_PUBLIC_CLUES",
    "V25476_CONSUMED_PUBLIC_CLUES",
    "V25481_CONSUMED_PUBLIC_CLUES",
    "V25488_CONSUMED_PUBLIC_CLUES",
    "mechanism_gate",
    "payload_sha256",
    "selected_clues",
    "source_policy",
    "task_vector",
    "validate_task_vector",
]
