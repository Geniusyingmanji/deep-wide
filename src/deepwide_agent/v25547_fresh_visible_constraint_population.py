"""Fresh outcome-blind population for deterministic visible constraints.

The population is one indivisible static block of twenty two-row tasks.  The
first ten use public PyPI project identities and request complete release
dates in an explicit visible format and order.  The second ten use public
Hugging Face model identities and request parameter counts in one explicit
scale and order.  These are exactly the three deterministic V2.55.44
operations: complete-date reformatting, explicit-scale conversion, and stable
total sorting.

Selection is frozen at ``SELECTION_PARENT_COMMIT`` using repository-only
exact-literal scans.  Every selected identity has zero occurrence in that
tree and zero introduction in its repository ancestry.  No endpoint, page,
model, prediction, mapping, truth, evaluator, score, quality result, or
per-task outcome is consulted.  The whole block is consumed regardless of
future reach or quality; no task may be filtered, replaced, retried, resumed,
or backfilled.

This module is pure.  Runtime-visible rows contain only ``opaque_id`` and
``question``.  It assigns zero entropy/information-gain signed credit and
authorizes neither a forward nor an evaluator.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


POLICY_ID = "v25547_fresh_visible_constraint_population_v1"
SELECTION_PARENT_COMMIT = "6263834b74d166e67e98d1f0f2f9abe6fd8c0e6a"
TASK_COUNT = 20
ROWS_PER_TASK = 2
DATE_TASK_COUNT = 10
SCALE_TASK_COUNT = 10
DATE_COLUMNS = ("Package", "Latest Stable Release Date")
SCALE_COLUMNS = ("Model", "Parameter Count")
SELECTION_RULE = (
    "one_static_twenty_pair_block_with_repo_tree_and_ancestry_exact_literal_zero"
)

PYPI_PAIRS = (
    ("marimo", "solara"),
    ("nicegui", "robyn"),
    ("faststream", "dishka"),
    ("adaptix", "pydantic-extra-types"),
    ("eval-type-backport", "pyupgrade"),
    ("arro3-core", "arro3-compute"),
    ("arro3-io", "geoarrow-pyarrow"),
    ("geoarrow-rust-core", "lonboard"),
    ("leafmap", "great-tables"),
    ("pygwalker", "vegafusion"),
)

HUGGINGFACE_PAIRS = (
    (
        "HuggingFaceTB/SmolLM2-135M-Instruct",
        "HuggingFaceTB/SmolLM2-360M-Instruct",
    ),
    (
        "HuggingFaceTB/SmolLM2-1.7B-Instruct",
        "allenai/OLMo-2-0425-1B",
    ),
    (
        "allenai/OLMo-2-1124-7B-Instruct",
        "ibm-granite/granite-3.3-2b-instruct",
    ),
    (
        "ibm-granite/granite-3.3-8b-instruct",
        "tiiuae/Falcon3-1B-Instruct",
    ),
    ("tiiuae/Falcon3-3B-Instruct", "tiiuae/Falcon3-7B-Instruct"),
    ("microsoft/Phi-4-mini-instruct", "microsoft/Phi-4-multimodal-instruct"),
    ("google/gemma-3-1b-it", "google/gemma-3-4b-it"),
    ("Qwen/Qwen3-0.6B", "Qwen/Qwen3-1.7B"),
    ("Qwen/Qwen3-4B", "Qwen/Qwen3-8B"),
    (
        "meta-llama/Llama-3.2-1B-Instruct",
        "meta-llama/Llama-3.2-3B-Instruct",
    ),
)

PAIRS = PYPI_PAIRS + HUGGINGFACE_PAIRS
EXPECTED_IDENTITY_VECTOR_SHA256 = (
    "e015b72bf4f04cea41bd99ff8d7a63d10b4b4fd33c91cd5717140edbae250ce8"
)
EXPECTED_TASK_VECTOR_SHA256 = (
    "05260a94a83529948be04a1e0c6fe8c1f27a614e7ee8be54ac6f36d6268743b1"
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def identity_vector() -> list[str]:
    pairs = tuple(PAIRS)
    identities = [identity for pair in pairs for identity in pair]
    if (
        len(pairs) != TASK_COUNT
        or len(PYPI_PAIRS) != DATE_TASK_COUNT
        or len(HUGGINGFACE_PAIRS) != SCALE_TASK_COUNT
        or any(len(pair) != ROWS_PER_TASK for pair in pairs)
        or len(identities) != TASK_COUNT * ROWS_PER_TASK
        or len(set(identities)) != len(identities)
        or any(
            re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,79}", identity) is None
            for pair in PYPI_PAIRS
            for identity in pair
        )
        or any(
            re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}/[A-Za-z0-9][A-Za-z0-9._-]{1,119}",
                identity,
            )
            is None
            for pair in HUGGINGFACE_PAIRS
            for identity in pair
        )
    ):
        raise RuntimeError("V2.55.47 identity vector drifted")
    if (
        EXPECTED_IDENTITY_VECTOR_SHA256 != "TO_BE_FROZEN"
        and payload_sha256(identities) != EXPECTED_IDENTITY_VECTOR_SHA256
    ):
        raise RuntimeError("V2.55.47 identity vector hash drifted")
    return identities


def pair_vector() -> list[tuple[str, str]]:
    identity_vector()
    return list(PAIRS)


def _date_question(first: str, second: str) -> str:
    return (
        "Use public web search and authoritative PyPI project metadata to return "
        "exactly one Markdown table and no prose for the two visible projects "
        f"<PROJECT>{first}</PROJECT> and <PROJECT>{second}</PROJECT>. Columns "
        "exactly: Package | Latest Stable Release Date. Return exactly two rows, "
        "one for each supplied project. Exclude pre-releases and use the upload "
        "date of the latest stable release. Format Latest Stable Release Date as "
        "YYYY年M月D日. Sort by Latest Stable Release Date in descending order. "
        "Use Unknown only when same-forward fetched public pages do not establish "
        "a complete date."
    )


def _scale_question(first: str, second: str) -> str:
    return (
        "Use public web search and authoritative public Hugging Face model metadata "
        "to return exactly one Markdown table and no prose for the two visible "
        f"models <MODEL>{first}</MODEL> and <MODEL>{second}</MODEL>. Columns exactly: "
        "Model | Parameter Count. Return exactly two rows, one for each supplied "
        "model. Express Parameter Count in millions. Sort by Parameter Count in "
        "descending order. Preserve each exact repository identifier. Use Unknown "
        "only when same-forward fetched public pages do not establish the value."
    )


def task_vector() -> list[dict[str, str]]:
    values: list[dict[str, str]] = []
    for index, (first, second) in enumerate(pair_vector()):
        question = (
            _date_question(first, second)
            if index < DATE_TASK_COUNT
            else _scale_question(first, second)
        )
        opaque = "task_" + hashlib.sha256(
            f"v25547:{index}:{question}".encode()
        ).hexdigest()[:24]
        values.append({"opaque_id": opaque, "question": question})
    checked = validate_task_vector(values)
    if (
        EXPECTED_TASK_VECTOR_SHA256 != "TO_BE_FROZEN"
        and payload_sha256(checked) != EXPECTED_TASK_VECTOR_SHA256
    ):
        raise RuntimeError("V2.55.47 task vector hash drifted")
    return checked


def validate_task_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.55.47 task denominator drifted")
    output: list[dict[str, str]] = []
    ids: list[str] = []
    for index, (raw, pair) in enumerate(zip(values, PAIRS, strict=True)):
        first, second = pair
        expected_question = (
            _date_question(first, second)
            if index < DATE_TASK_COUNT
            else _scale_question(first, second)
        )
        if not isinstance(raw, Mapping) or set(raw) != {"opaque_id", "question"}:
            raise ValueError("V2.55.47 runtime input shape drifted")
        opaque = raw.get("opaque_id")
        question = raw.get("question")
        if (
            not isinstance(opaque, str)
            or re.fullmatch(r"task_[0-9a-f]{24}", opaque) is None
            or not isinstance(question, str)
            or question != expected_question
            or "https://" in question
            or question.casefold().count("ground_truth")
            or question.casefold().count("evaluator")
            or question.casefold().count("score file")
        ):
            raise ValueError("V2.55.47 visible task binding drifted")
        ids.append(opaque)
        output.append({"opaque_id": opaque, "question": question})
    if len(set(ids)) != TASK_COUNT:
        raise ValueError("V2.55.47 opaque identity collision")
    return output


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": [
            "opaque_id",
            "question",
            "same_forward_public_pages",
        ],
        "one_indivisible_static_twenty_task_block": True,
        "selection_parent_commit": SELECTION_PARENT_COMMIT,
        "selection_rule": SELECTION_RULE,
        "identity_tree_and_ancestry_exact_literal_occurrence_count": 0,
        "selection_reads_repository_history_only": True,
        "endpoint_page_model_prediction_mapping_truth_evaluator_score_quality_or_outcome_used_for_selection": False,
        "individual_task_filtering_ranking_retention_replacement_retry_resume_or_backfill": False,
        "date_tasks_expose_exact_project_identities_format_and_order": True,
        "scale_tasks_expose_exact_model_identities_scale_and_order": True,
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
        "maximum_outer_or_accounting_failure_tasks": 0,
        "maximum_parent_prediction_loss_tasks": 0,
        "required_shared_parent_tasks": TASK_COUNT,
        "minimum_active_constraint_tasks": 12,
        "minimum_date_contract_tasks": 8,
        "minimum_scale_contract_tasks": 8,
        "minimum_explicit_order_contract_tasks": 16,
        "minimum_candidate_prediction_changed_tasks": 2,
        "minimum_date_changed_tasks": 1,
        "minimum_scale_changed_tasks": 1,
        "minimum_sort_applied_tasks": 1,
        "maximum_unattributable_prediction_changed_tasks": 0,
        "exact_physical_queries_per_completed_task": 4,
        "maximum_physical_fetches_per_completed_task": 14,
        "maximum_normal_path_model_forwards_per_completed_task": 3,
        "one_parent_forward_per_task": True,
        "candidate_additional_queries_fetches_model_calls_or_sampling_effects": 0,
        "control_and_candidate_predictions_frozen_per_task": True,
        "positive_signed_credit_count": 0,
        "postfreeze_paired_quality_required": True,
    }


def quality_gate() -> dict[str, Any]:
    return {
        "fixed_task_denominator": TASK_COUNT,
        "each_control_and_candidate_prediction_evaluated_exactly_once": True,
        "candidate_exact_strictly_greater_than_control": True,
        "candidate_entity_row_item_column_and_composite_nonregression": True,
        "candidate_invalid_and_fallback_nonincrease": True,
        "same_forward_provider_retrieval_and_sampling_effects": True,
        "positive_signed_credit_count": 0,
    }


__all__ = [
    "DATE_COLUMNS",
    "DATE_TASK_COUNT",
    "EXPECTED_IDENTITY_VECTOR_SHA256",
    "EXPECTED_TASK_VECTOR_SHA256",
    "HUGGINGFACE_PAIRS",
    "PAIRS",
    "POLICY_ID",
    "PYPI_PAIRS",
    "ROWS_PER_TASK",
    "SCALE_COLUMNS",
    "SCALE_TASK_COUNT",
    "SELECTION_PARENT_COMMIT",
    "SELECTION_RULE",
    "TASK_COUNT",
    "identity_vector",
    "mechanism_gate",
    "pair_vector",
    "payload_sha256",
    "quality_gate",
    "source_policy",
    "task_vector",
    "validate_task_vector",
]
