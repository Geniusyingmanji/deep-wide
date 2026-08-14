"""Fresh outcome-blind clue population for the V2.54.72 successor.

Two public capital/currency clue blocks have already been consumed: V2.50.27
and V2.54.69.  This module selects the first whole static block of twenty with
zero exact clue overlap against their union.  It does not inspect a country to
TLD mapping, endpoint, page, field value, prediction, evaluator, score, metric,
or per-task outcome.

Questions expose only one capital/currency clue, the IANA authority phrase,
and the requested schema.  They omit country and ccTLD identities, membership
tags, and URLs.  This pure module performs no I/O and authorizes neither a
forward nor an evaluator.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


POLICY_ID = "v25474_fresh_outcome_blind_qualified_label_population_v1"
SELECTION_PARENT_COMMIT = "fd2c1fa3e1e92172a032662c61d9a929139d90ff"
TASK_COUNT = 20
COLUMNS = ("Domain", "Type", "TLD Manager")
SELECTION_RULE = "first_whole_static_twenty_clue_block_with_zero_union_consumed_overlap"

V25027_CONSUMED_PUBLIC_CLUES = (
    ("New Delhi", "INR"), ("Baghdad", "IQD"), ("Tehran", "IRR"),
    ("Reykjavik", "ISK"), ("Rome", "EUR"), ("Saint Helier", "GBP"),
    ("Kingston", "JMD"), ("Amman", "JOD"), ("Tokyo", "JPY"),
    ("Nairobi", "KES"), ("Bishkek", "KGS"), ("Phnom Penh", "KHR"),
    ("South Tarawa", "AUD"), ("Moroni", "KMF"), ("Basseterre", "XCD"),
    ("Seoul", "KRW"), ("Kuwait City", "KWD"), ("George Town", "KYD"),
    ("Astana", "KZT"), ("Vientiane", "LAK"),
)
V25469_CONSUMED_PUBLIC_CLUES = (
    ("Kabul", "AFN"), ("Tirana", "ALL"), ("Algiers", "DZD"),
    ("Andorra la Vella", "EUR"), ("Luanda", "AOA"), ("Saint John's", "XCD"),
    ("Buenos Aires", "ARS"), ("Yerevan", "AMD"), ("Canberra", "AUD"),
    ("Vienna", "EUR"), ("Baku", "AZN"), ("Nassau", "BSD"),
    ("Manama", "BHD"), ("Dhaka", "BDT"), ("Bridgetown", "BBD"),
    ("Minsk", "BYN"), ("Brussels", "EUR"), ("Belmopan", "BZD"),
    ("Porto-Novo", "XOF"), ("Thimphu", "BTN"),
)
CONSUMED_PUBLIC_CLUES = V25027_CONSUMED_PUBLIC_CLUES + V25469_CONSUMED_PUBLIC_CLUES

CANDIDATE_BLOCKS = (
    V25469_CONSUMED_PUBLIC_CLUES,
    (
        ("Sucre", "BOB"), ("Sarajevo", "BAM"), ("Gaborone", "BWP"),
        ("Brasilia", "BRL"), ("Bandar Seri Begawan", "BND"), ("Sofia", "BGN"),
        ("Ouagadougou", "XOF"), ("Gitega", "BIF"), ("Praia", "CVE"),
        ("Yaounde", "XAF"), ("Ottawa", "CAD"), ("Bangui", "XAF"),
        ("N'Djamena", "XAF"), ("Santiago", "CLP"), ("Beijing", "CNY"),
        ("Bogota", "COP"), ("Mitsamiouli", "KMF"), ("Kinshasa", "CDF"),
        ("Brazzaville", "XAF"), ("San Jose", "CRC"),
    ),
)
SELECTED_BLOCK_INDEX = 1
CLUES = CANDIDATE_BLOCKS[SELECTED_BLOCK_INDEX]
EXPECTED_CLUE_VECTOR_SHA256 = "102e906458e660bc23e325d93f153221741e1a15727b33dbc300db60e856783d"
EXPECTED_TASK_VECTOR_SHA256 = "b11dfb5a659224393c4a207cb9f7f59c3b7069444511fa23564ebebff53bf7d1"


def payload_sha256(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def selected_clues() -> list[tuple[str, str]]:
    consumed=set(CONSUMED_PUBLIC_CLUES);overlaps=[len(set(block).intersection(consumed)) for block in CANDIDATE_BLOCKS];selected=tuple(CANDIDATE_BLOCKS[SELECTED_BLOCK_INDEX])
    if len(CONSUMED_PUBLIC_CLUES)!=40 or len(set(CONSUMED_PUBLIC_CLUES))!=40 or any(len(block)!=TASK_COUNT or len(set(block))!=TASK_COUNT for block in CANDIDATE_BLOCKS) or overlaps[SELECTED_BLOCK_INDEX]!=0 or SELECTED_BLOCK_INDEX!=next((index for index,overlap in enumerate(overlaps) if overlap==0),-1) or selected!=CLUES:raise RuntimeError("V2.54.74 clue selection drifted")
    values=list(selected);observed=payload_sha256(values)
    if EXPECTED_CLUE_VECTOR_SHA256!="TO_BE_FROZEN" and observed!=EXPECTED_CLUE_VECTOR_SHA256:raise RuntimeError("V2.54.74 clue vector drifted")
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
    values=[]
    for index,(capital,code) in enumerate(selected_clues()):
        question=_question(capital,code);opaque="task_"+hashlib.sha256(f"v25474:{index}:{question}".encode()).hexdigest()[:24];values.append({"opaque_id":opaque,"question":question})
    checked=validate_task_vector(values);observed=payload_sha256(checked)
    if EXPECTED_TASK_VECTOR_SHA256!="TO_BE_FROZEN" and observed!=EXPECTED_TASK_VECTOR_SHA256:raise RuntimeError("V2.54.74 task vector drifted")
    return checked


def validate_task_vector(values: Sequence[Mapping[str, Any]]) -> list[dict[str,str]]:
    if isinstance(values,(str,bytes)) or len(values)!=TASK_COUNT:raise ValueError("V2.54.74 task denominator drifted")
    output=[];ids=[]
    for raw,(capital,code) in zip(values,selected_clues(),strict=True):
        if not isinstance(raw,Mapping) or set(raw)!={"opaque_id","question"}:raise ValueError("V2.54.74 runtime input shape drifted")
        opaque=raw.get("opaque_id");question=raw.get("question")
        if not isinstance(opaque,str) or re.fullmatch(r"task_[0-9a-f]{24}",opaque) is None or not isinstance(question,str) or question!=_question(capital,code) or any(column not in question for column in COLUMNS) or "<ENTITIES>" in question or "https://" in question or re.search(r"\.[a-z]{2}\b",question.casefold()) is not None:raise ValueError("V2.54.74 visible task binding drifted")
        ids.append(opaque);output.append({"opaque_id":opaque,"question":question})
    if len(set(ids))!=TASK_COUNT:raise ValueError("V2.54.74 opaque identity collision")
    return output


def source_policy() -> dict[str,Any]:
    return {"runtime_boundary":["opaque_id","question","same_forward_public_pages"],"visible_population_contains_capital_currency_clues_but_no_country_or_tld_mapping":True,"no_visible_membership_or_row_key_tag":True,"parent_completed_table_must_supply_candidate_row_key":True,"selection_is_first_whole_static_block_with_zero_union_consumed_public_clue_overlap":True,"individual_clue_or_task_retention_replacement_or_ranking":False,"country_tld_mapping_endpoint_page_field_value_prediction_or_evaluator_used_for_selection":False,"historical_population_forward_page_prediction_score_metric_quality_or_per_task_outcome_read":False,"mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read":False,"entropy_or_information_gain_assigns_signed_credit":False,"network_model_search_fetch_evaluator_or_benchmark_authorized":False}


def mechanism_gate() -> dict[str,Any]:
    return {"fixed_task_denominator":TASK_COUNT,"required_terminal_tasks":TASK_COUNT,"required_completed_runtime_tasks":TASK_COUNT,"maximum_failure_as_zero_tasks":0,"maximum_outer_failure_tasks":0,"maximum_budget_rejection_tasks":0,"required_parent_role_tasks":TASK_COUNT,"required_synthesis_capture_valid_tasks":TASK_COUNT,"minimum_accepted_unique_identity_page_tasks":3,"minimum_available_candidate_tasks":2,"minimum_applied_candidate_tasks":2,"minimum_prediction_changed_tasks":2,"maximum_application_failure_tasks":0,"exact_physical_queries_per_completed_task":4,"maximum_physical_fetches_per_completed_task":14,"maximum_normal_path_model_forwards_per_completed_task":3,"one_parent_forward_per_task":True,"candidate_additional_queries":0,"candidate_additional_model_calls":0,"candidate_additional_fetches":0,"base_and_candidate_predictions_frozen_per_task":True,"all_content_free_receipts_valid":True,"positive_signed_credit_count":0,"postfreeze_shared_parent_quality_required":True}


__all__=["CANDIDATE_BLOCKS","CLUES","COLUMNS","CONSUMED_PUBLIC_CLUES","EXPECTED_CLUE_VECTOR_SHA256","EXPECTED_TASK_VECTOR_SHA256","POLICY_ID","SELECTED_BLOCK_INDEX","SELECTION_PARENT_COMMIT","SELECTION_RULE","TASK_COUNT","V25027_CONSUMED_PUBLIC_CLUES","V25469_CONSUMED_PUBLIC_CLUES","mechanism_gate","payload_sha256","selected_clues","source_policy","task_vector","validate_task_vector"]
