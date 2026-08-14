"""Fresh public-index population for the generic visible row-key detail gate.

This pure module freezes one whole static block of twenty explicit ccTLD row
keys.  The identities are visible task inputs, not inferred labels.  The only
pre-effect structural qualification is that one public IANA Root Zone Database
index snapshot exposed each identity as visible anchor text on a same-origin
strict child URL.  No detail page, detail field, prediction, evaluator, score,
quality result, benchmark metadata, or historical per-task outcome was opened.

All previously authorized external task vectors count as consumed.  This
population has zero exact question or opaque-id overlap with them and grants
neither a forward nor an evaluator.  Entropy/information gain assigns no
signed credit.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from . import v25486_outcome_blind_iana_detail_population as prior


POLICY_ID = "v25494_fresh_visible_row_key_population_v1"
SELECTION_PARENT_COMMIT = "b8ea78f98a0fae5e604bdf1ccb19bb63aee6c86b"
TASK_COUNT = 20
COLUMNS = ("Domain", "Type", "TLD Manager")
INDEX_URL = "https://www.iana.org/domains/root/db"
SELECTION_RULE = "one_whole_static_twenty_identity_block_with_public_index_visible_link_structure"
PRIOR_TASK_VECTOR_SHA256 = prior.EXPECTED_TASK_VECTOR_SHA256
IDENTITIES = (
    ".ae",
    ".ai",
    ".as",
    ".ax",
    ".bm",
    ".bq",
    ".cc",
    ".ch",
    ".ck",
    ".cw",
    ".cx",
    ".es",
    ".fk",
    ".fm",
    ".fo",
    ".gg",
    ".gi",
    ".gl",
    ".hk",
    ".im",
)
EXPECTED_IDENTITY_VECTOR_SHA256 = (
    "027a0623fa1a07ada37d0cd30f619c0f178238be117a15df9fd9b7250e36e762"
)
EXPECTED_TASK_VECTOR_SHA256 = (
    "bc3d39df25817e38b43513207ea972f1ae8441d586450f4474c3b32e14fa298a"
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def identity_vector() -> list[str]:
    values = list(IDENTITIES)
    if (
        len(values) != TASK_COUNT
        or len(set(values)) != TASK_COUNT
        or any(re.fullmatch(r"\.[a-z]{2}", value) is None for value in values)
    ):
        raise RuntimeError("V2.54.94 identity vector drifted")
    observed = payload_sha256(values)
    if (
        EXPECTED_IDENTITY_VECTOR_SHA256 != "TO_BE_FROZEN"
        and observed != EXPECTED_IDENTITY_VECTOR_SHA256
    ):
        raise RuntimeError("V2.54.94 identity vector hash drifted")
    return values


def _question(identity: str) -> str:
    return (
        "Use public web search and the official IANA Root Zone Database index at "
        f"{INDEX_URL}. For the visible country-code top-level domain "
        f"<DOMAIN>{identity}</DOMAIN>, use the index and its visible detail link "
        "to return exactly one Markdown table and no prose. Columns exactly: "
        "Domain | Type | TLD Manager. Return exactly one row. Preserve exact "
        "spelling and use Domain, Type, and TLD Manager from the same "
        "identity-bound IANA source. Use Unknown only when same-forward fetched "
        "public pages do not establish a value."
    )


def task_vector() -> list[dict[str, str]]:
    values = []
    for index, identity in enumerate(identity_vector()):
        question = _question(identity)
        opaque = "task_" + hashlib.sha256(
            f"v25494:{index}:{question}".encode()
        ).hexdigest()[:24]
        values.append({"opaque_id": opaque, "question": question})
    checked = validate_task_vector(values)
    observed = payload_sha256(checked)
    if (
        EXPECTED_TASK_VECTOR_SHA256 != "TO_BE_FROZEN"
        and observed != EXPECTED_TASK_VECTOR_SHA256
    ):
        raise RuntimeError("V2.54.94 task vector hash drifted")
    return checked


def validate_task_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.54.94 task denominator drifted")
    output: list[dict[str, str]] = []
    ids: list[str] = []
    for raw, identity in zip(values, identity_vector(), strict=True):
        if not isinstance(raw, Mapping) or set(raw) != {"opaque_id", "question"}:
            raise ValueError("V2.54.94 runtime input shape drifted")
        opaque = raw.get("opaque_id")
        question = raw.get("question")
        if (
            not isinstance(opaque, str)
            or re.fullmatch(r"task_[0-9a-f]{24}", opaque) is None
            or not isinstance(question, str)
            or question != _question(identity)
            or f"<DOMAIN>{identity}</DOMAIN>" not in question
            or "Columns exactly: " + " | ".join(COLUMNS) not in question
            or question.count(INDEX_URL) != 1
        ):
            raise ValueError("V2.54.94 visible task binding drifted")
        ids.append(opaque)
        output.append({"opaque_id": opaque, "question": question})
    if len(set(ids)) != TASK_COUNT:
        raise ValueError("V2.54.94 opaque identity collision")
    return output


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "row_key_and_public_index_url_are_explicit_visible_task_inputs": True,
        "population_is_one_whole_static_identity_block": True,
        "all_prior_authorized_external_task_vectors_count_as_consumed": True,
        "public_index_structure_checked_before_protocol": True,
        "public_index_check_limited_to_anchor_text_and_child_url_shape": True,
        "detail_page_field_value_prediction_evaluator_score_or_quality_opened_for_selection": False,
        "historical_per_task_forward_page_prediction_score_metric_quality_or_outcome_read": False,
        "individual_task_retention_replacement_or_ranking": False,
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
        "minimum_raw_page_visible_link_tasks": 18,
        "minimum_joint_bound_link_tasks": 16,
        "minimum_logical_detail_request_tasks": 16,
        "minimum_admitted_detail_fetch_tasks": 16,
        "minimum_exact_nonredirected_detail_page_tasks": 12,
        "minimum_accepted_unique_identity_page_tasks": 10,
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
    "COLUMNS",
    "EXPECTED_IDENTITY_VECTOR_SHA256",
    "EXPECTED_TASK_VECTOR_SHA256",
    "IDENTITIES",
    "INDEX_URL",
    "POLICY_ID",
    "PRIOR_TASK_VECTOR_SHA256",
    "SELECTION_PARENT_COMMIT",
    "SELECTION_RULE",
    "TASK_COUNT",
    "identity_vector",
    "mechanism_gate",
    "payload_sha256",
    "source_policy",
    "task_vector",
    "validate_task_vector",
]
