"""Fourth fresh outcome-blind clue population for the IANA detail gate.

Every clue from V2.50.27, V2.54.69, V2.54.76, and V2.54.81 counts as
consumed in full, irrespective of whether its later mechanism gate passed.
This module selects the first whole static block of twenty clues with zero
exact overlap against that eighty-clue union.  It never reads a country/TLD
mapping, official endpoint, page, field value, prediction, evaluator, score,
metric, quality result, or per-task outcome.

Questions expose only a capital/currency clue, the public IANA authority
phrase, and the requested schema.  Country and ccTLD identities, URLs, and
membership labels remain hidden.  This pure module performs no I/O and
authorizes neither a forward nor an evaluator.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from . import v25479_outcome_blind_qualified_label_population as parent


POLICY_ID = "v25486_fourth_fresh_outcome_blind_iana_detail_population_v1"
SELECTION_PARENT_COMMIT = "fc5647c17cb884cb653190ce8a5905ba2c4722f2"
TASK_COUNT = 20
COLUMNS = ("Domain", "Type", "TLD Manager")
SELECTION_RULE = "first_whole_static_twenty_clue_block_with_zero_union_consumed_overlap"

V25027_CONSUMED_PUBLIC_CLUES = parent.V25027_CONSUMED_PUBLIC_CLUES
V25469_CONSUMED_PUBLIC_CLUES = parent.V25469_CONSUMED_PUBLIC_CLUES
V25476_CONSUMED_PUBLIC_CLUES = parent.V25476_CONSUMED_PUBLIC_CLUES
V25481_CONSUMED_PUBLIC_CLUES = parent.CLUES
CONSUMED_PUBLIC_CLUES = (
    V25027_CONSUMED_PUBLIC_CLUES
    + V25469_CONSUMED_PUBLIC_CLUES
    + V25476_CONSUMED_PUBLIC_CLUES
    + V25481_CONSUMED_PUBLIC_CLUES
)

CANDIDATE_BLOCKS = (
    V25481_CONSUMED_PUBLIC_CLUES,
    (
        ("Banjul", "GMD"),
        ("Tbilisi", "GEL"),
        ("Berlin", "EUR"),
        ("Accra", "GHS"),
        ("Athens", "EUR"),
        ("Saint George's", "XCD"),
        ("Guatemala City", "GTQ"),
        ("Conakry", "GNF"),
        ("Bissau", "XOF"),
        ("Georgetown", "GYD"),
        ("Port-au-Prince", "HTG"),
        ("Tegucigalpa", "HNL"),
        ("Budapest", "HUF"),
        ("Jakarta", "IDR"),
        ("Dublin", "EUR"),
        ("Jerusalem", "ILS"),
        ("Abidjan", "XOF"),
        ("Maseru", "LSL"),
        ("Monrovia", "LRD"),
        ("Tripoli", "LYD"),
    ),
)
SELECTED_BLOCK_INDEX = 1
CLUES = CANDIDATE_BLOCKS[SELECTED_BLOCK_INDEX]
EXPECTED_CLUE_VECTOR_SHA256 = "e443e78ef8e6a47f75be2adda89e47b200f894ed3861217fa40b91d876602134"
EXPECTED_TASK_VECTOR_SHA256 = "d5ecaae7f59a11193eed74fdc0012e218f03e089fb28c4d7eb1e5b7f7a267f83"


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def selected_clues() -> list[tuple[str, str]]:
    consumed = set(CONSUMED_PUBLIC_CLUES)
    overlaps = [
        len(set(block).intersection(consumed)) for block in CANDIDATE_BLOCKS
    ]
    selected = tuple(CANDIDATE_BLOCKS[SELECTED_BLOCK_INDEX])
    if (
        len(CONSUMED_PUBLIC_CLUES) != 80
        or len(set(CONSUMED_PUBLIC_CLUES)) != 80
        or any(
            len(block) != TASK_COUNT or len(set(block)) != TASK_COUNT
            for block in CANDIDATE_BLOCKS
        )
        or overlaps[SELECTED_BLOCK_INDEX] != 0
        or SELECTED_BLOCK_INDEX
        != next((i for i, overlap in enumerate(overlaps) if overlap == 0), -1)
        or selected != CLUES
    ):
        raise RuntimeError("V2.54.86 clue selection drifted")
    values = list(selected)
    observed = payload_sha256(values)
    if (
        EXPECTED_CLUE_VECTOR_SHA256 != "TO_BE_FROZEN"
        and observed != EXPECTED_CLUE_VECTOR_SHA256
    ):
        raise RuntimeError("V2.54.86 clue vector drifted")
    return values


def _question(capital: str, code: str) -> str:
    return (
        f"Identify the jurisdiction whose capital is {capital} and whose official "
        f"currency has ISO 4217 code {code}. Then use public web search and the "
        "official IANA Root Zone Database to return exactly one Markdown table "
        "and no prose for that jurisdiction's country-code top-level domain. "
        "Columns exactly: Domain | Type | TLD Manager. Return exactly one row. "
        "Preserve exact spelling and use Domain, Type, and TLD Manager from the "
        "same identity-bound IANA source. Use Unknown only when same-forward "
        "fetched public pages do not establish a value."
    )


def task_vector() -> list[dict[str, str]]:
    values = []
    for index, (capital, code) in enumerate(selected_clues()):
        question = _question(capital, code)
        opaque = "task_" + hashlib.sha256(
            f"v25486:{index}:{question}".encode()
        ).hexdigest()[:24]
        values.append({"opaque_id": opaque, "question": question})
    checked = validate_task_vector(values)
    observed = payload_sha256(checked)
    if (
        EXPECTED_TASK_VECTOR_SHA256 != "TO_BE_FROZEN"
        and observed != EXPECTED_TASK_VECTOR_SHA256
    ):
        raise RuntimeError("V2.54.86 task vector drifted")
    return checked


def validate_task_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.54.86 task denominator drifted")
    output = []
    ids = []
    for raw, (capital, code) in zip(values, selected_clues(), strict=True):
        if not isinstance(raw, Mapping) or set(raw) != {"opaque_id", "question"}:
            raise ValueError("V2.54.86 runtime input shape drifted")
        opaque = raw.get("opaque_id")
        question = raw.get("question")
        if (
            not isinstance(opaque, str)
            or re.fullmatch(r"task_[0-9a-f]{24}", opaque) is None
            or not isinstance(question, str)
            or question != _question(capital, code)
            or any(column not in question for column in COLUMNS)
            or "<ENTITIES>" in question
            or "https://" in question
            or re.search(r"\.[a-z]{2}\b", question.casefold()) is not None
        ):
            raise ValueError("V2.54.86 visible task binding drifted")
        ids.append(opaque)
        output.append({"opaque_id": opaque, "question": question})
    if len(set(ids)) != TASK_COUNT:
        raise ValueError("V2.54.86 opaque identity collision")
    return output


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": [
            "opaque_id",
            "question",
            "same_forward_public_pages",
        ],
        "visible_population_contains_capital_currency_clues_but_no_country_or_tld_mapping": True,
        "no_visible_membership_or_row_key_tag": True,
        "parent_completed_table_must_supply_candidate_row_key": True,
        "selection_is_first_whole_static_block_with_zero_union_consumed_public_clue_overlap": True,
        "all_four_prior_authorized_population_blocks_count_as_consumed": True,
        "v25481_mechanism_no_go_population_still_consumed": True,
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
        "minimum_logical_detail_request_tasks": 18,
        "minimum_admitted_detail_fetch_tasks": 18,
        "minimum_exact_nonredirected_detail_page_tasks": 12,
        "minimum_identity_surface_bound_detail_page_tasks": 10,
        "minimum_field_surface_tasks": 6,
        "minimum_evidence_closed_observation_tasks": 4,
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
    "mechanism_gate",
    "payload_sha256",
    "selected_clues",
    "source_policy",
    "task_vector",
    "validate_task_vector",
]
