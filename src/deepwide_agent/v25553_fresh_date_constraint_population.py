"""Fresh outcome-blind population for visible date format and ordering.

The population is one indivisible static block of twenty two-project PyPI
tasks.  It is selected only by exact-literal zero occurrence in the repository
tree and all ancestor patches at ``SELECTION_PARENT_COMMIT``.  Selection does
not access PyPI endpoints, pages, versions, dates, models, predictions, truth,
evaluators, scores, quality results, or outcomes.

Every runtime-visible row contains only ``opaque_id`` and ``question``.  All
tasks request the same exact schema, complete Chinese date format, descending
date order, and explicit Unknown semantics.  No task may be filtered,
replaced, retried, resumed, or backfilled.  Entropy/information gain assigns
no signed credit and this module authorizes neither forward nor evaluator.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


POLICY_ID = "v25553_fresh_date_constraint_population_v1"
SELECTION_PARENT_COMMIT = "08619f0fb5436e3d5093744526492a755f461d20"
SELECTION_RULE = (
    "one_static_twenty_pair_block_with_selection_parent_tree_and_ancestry_patch_exact_literal_zero"
)
TASK_COUNT = 20
ROWS_PER_TASK = 2
DATE_TASK_COUNT = 20
SCALE_TASK_COUNT = 0
DATE_COLUMNS = ("Package", "Latest Stable Release Date")
SCALE_COLUMNS = ("Model", "Parameter Count")

PYPI_PAIRS = (
    ("boost-histogram", "coffea"),
    ("connectorx", "contextily"),
    ("country-converter", "decaylanguage"),
    ("hepunits", "lagom"),
    ("mapclassify", "mercantile"),
    ("movingpandas", "mplhep"),
    ("narwhals", "osmnx"),
    ("punq", "pyogrio"),
    ("python-socketio", "quart-schema"),
    ("scikit-hep", "sqlglot"),
    ("textdistance", "trackintel"),
    ("uproot", "xyzservices"),
    ("zfit", "blosc2"),
    ("cabinetry", "cappa"),
    ("cartopy", "colorcet"),
    ("correctionlib", "cramjam"),
    ("cubed", "dask-awkward"),
    ("dask-histogram", "datashader"),
    ("deltalake", "eemont"),
    ("h5netcdf", "flox"),
)
HUGGINGFACE_PAIRS: tuple[tuple[str, str], ...] = ()
PAIRS = PYPI_PAIRS

# Filled after the static vectors are mechanically materialized and tested.
EXPECTED_IDENTITY_VECTOR_SHA256 = (
    "973845273b49b5fb7ea38956a73f2b155d695ec3dc363786d9dfb1d69e28b9c6"
)
EXPECTED_TASK_VECTOR_SHA256 = (
    "5891cc753bef35cafc1c9aaa7efa428ce21080d4128a0abc27f0dea873ae84af"
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
        or HUGGINGFACE_PAIRS
        or any(len(pair) != ROWS_PER_TASK for pair in pairs)
        or len(identities) != TASK_COUNT * ROWS_PER_TASK
        or len(set(identities)) != len(identities)
        or any(
            re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,79}", identity) is None
            for identity in identities
        )
    ):
        raise RuntimeError("V2.55.53 identity vector drifted")
    if (
        EXPECTED_IDENTITY_VECTOR_SHA256 != "TO_BE_FROZEN"
        and payload_sha256(identities) != EXPECTED_IDENTITY_VECTOR_SHA256
    ):
        raise RuntimeError("V2.55.53 identity vector hash drifted")
    return identities


def pair_vector() -> list[tuple[str, str]]:
    identity_vector()
    return list(PAIRS)


def _question(first: str, second: str) -> str:
    return (
        "Use public web search and authoritative PyPI project metadata to return "
        "exactly one Markdown table and no prose for the two visible projects "
        f"<PROJECT>{first}</PROJECT> and <PROJECT>{second}</PROJECT>. Columns "
        "exactly: Package | Latest Stable Release Date. Return exactly two rows, "
        "one for each supplied project. Exclude pre-releases and use the earliest "
        "UTC upload calendar date among files of the latest stable release. Format "
        "Latest Stable Release Date as YYYY年M月D日. Sort by Latest Stable Release "
        "Date in descending order. A project with a valid authoritative identity "
        "but no stable release must use Unknown; place Unknown after known dates "
        "while preserving supplied order among Unknown rows. Use Unknown for any "
        "other value not established by same-forward fetched public pages."
    )


def task_vector() -> list[dict[str, str]]:
    values: list[dict[str, str]] = []
    for index, (first, second) in enumerate(pair_vector()):
        question = _question(first, second)
        opaque = "task_" + hashlib.sha256(
            f"v25553:{index}:{question}".encode()
        ).hexdigest()[:24]
        values.append({"opaque_id": opaque, "question": question})
    checked = validate_task_vector(values)
    if (
        EXPECTED_TASK_VECTOR_SHA256 != "TO_BE_FROZEN"
        and payload_sha256(checked) != EXPECTED_TASK_VECTOR_SHA256
    ):
        raise RuntimeError("V2.55.53 task vector hash drifted")
    return checked


def validate_task_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.55.53 task denominator drifted")
    output: list[dict[str, str]] = []
    ids: list[str] = []
    for raw, pair in zip(values, PAIRS, strict=True):
        expected_question = _question(*pair)
        if not isinstance(raw, Mapping) or set(raw) != {"opaque_id", "question"}:
            raise ValueError("V2.55.53 runtime input shape drifted")
        opaque = raw.get("opaque_id")
        question = raw.get("question")
        if (
            not isinstance(opaque, str)
            or re.fullmatch(r"task_[0-9a-f]{24}", opaque) is None
            or not isinstance(question, str)
            or question != expected_question
            or "https://" in question
            or "ground_truth" in question.casefold()
            or "evaluator" in question.casefold()
            or "score file" in question.casefold()
        ):
            raise ValueError("V2.55.53 visible task binding drifted")
        ids.append(opaque)
        output.append({"opaque_id": opaque, "question": question})
    if len(set(ids)) != TASK_COUNT:
        raise ValueError("V2.55.53 opaque identity collision")
    return output


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "one_indivisible_static_twenty_task_block": True,
        "selection_parent_commit": SELECTION_PARENT_COMMIT,
        "selection_rule": SELECTION_RULE,
        "identity_tree_and_ancestry_patch_exact_literal_occurrence_count": 0,
        "selection_reads_repository_history_only": True,
        "endpoint_page_version_date_model_prediction_mapping_truth_evaluator_score_quality_or_outcome_used_for_selection": False,
        "individual_task_filtering_ranking_retention_replacement_retry_resume_or_backfill": False,
        "all_tasks_expose_exact_project_identities_date_format_order_and_unknown_semantics": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "network_model_search_fetch_evaluator_or_benchmark_authorized": False,
    }


def mechanism_gate() -> dict[str, Any]:
    return {
        "fixed_task_denominator": TASK_COUNT,
        "required_terminal_tasks": TASK_COUNT,
        "required_completed_runtime_tasks": TASK_COUNT,
        "required_model_generated_tasks": TASK_COUNT,
        "maximum_failure_as_zero_tasks": 0,
        "maximum_outer_or_accounting_failure_tasks": 0,
        "maximum_naked_outer_failure_tasks": 0,
        "maximum_parent_prediction_loss_tasks": 0,
        "required_shared_parent_tasks": TASK_COUNT,
        "minimum_active_constraint_tasks": TASK_COUNT,
        "minimum_date_contract_tasks": TASK_COUNT,
        "minimum_scale_contract_tasks": 0,
        "minimum_explicit_order_contract_tasks": TASK_COUNT,
        "minimum_candidate_prediction_changed_tasks": 2,
        "minimum_date_changed_tasks": 1,
        "minimum_scale_changed_tasks": 0,
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
        "official_identity_bound_no_stable_release_is_valid_unknown": True,
        "known_dates_descending_then_unknown_stable_supplied_order": True,
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
