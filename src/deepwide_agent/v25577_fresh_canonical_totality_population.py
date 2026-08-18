"""Fresh outcome-blind population for canonical-column totality.

The forty PyPI project identities form one indivisible twenty-task block.
Selection is frozen against the repository tree and ancestry patches at
``SELECTION_PARENT_COMMIT``.  Selection opens no endpoint, page, version,
prediction, truth, evaluator, score, or outcome.

Ten tasks expose a visible NFKC-only column spelling drift and ten tasks use
ordinary ASCII spellings as negative controls.  Both groups request the same
public fact and use the same runtime budget.  Exposure is determined only by
the pre-registered visible column bytes; it never depends on provider output
or correctness.  Runtime input is exactly ``opaque_id`` and ``question``.
Entropy/information gain assigns zero signed credit.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


POLICY_ID = "v25577_fresh_canonical_column_totality_population_v1"
SELECTION_PARENT_COMMIT = "babfd33dfc8a0300df5b5f53b20c6e9e9453a96b"
SELECTION_RULE = (
    "one_static_twenty_pair_block_with_selection_parent_tree_and_ancestry_patch_exact_literal_zero"
)
TASK_COUNT = 20
ROWS_PER_TASK = 2
DRIFT_TASK_COUNT = 10
ORDINARY_TASK_COUNT = 10
DRIFT_COLUMNS = ("Ｐackage", "Latest Stable Ｖersion")
ORDINARY_COLUMNS = ("Package", "Latest Stable Version")

DRIFT_PAIRS = (
    ("fasteners", "portalocker"),
    ("lockfile", "flufl.lock"),
    ("flufl.enum", "ansicolors"),
    ("blessings", "rfc3986-validator"),
    ("pytomlpp", "configupdater"),
    ("dynaconf", "environs"),
    ("python-decouple", "jeepney"),
    ("findpython", "dep-logic"),
    ("unearth", "pyproject-metadata"),
    ("pyproject-parser", "pycln"),
)
ORDINARY_PAIRS = (
    ("eradicate", "refurb"),
    ("flynt", "unimport"),
    ("yesqa", "codespell"),
    ("docformatter", "interrogate"),
    ("xenon", "radon"),
    ("darglint", "pydocstyle"),
    ("doc8", "rstcheck"),
    ("yamllint", "nitpick"),
    ("detect-secrets", "pip-audit"),
    ("pip-run", "pip-api"),
)
PAIRS = DRIFT_PAIRS + ORDINARY_PAIRS
EXPECTED_IDENTITY_VECTOR_SHA256 = (
    "547d9653b39da50b489e02da8a71bd05ee2a432d7403d8dd89e50e647e17623a"
)
EXPECTED_TASK_VECTOR_SHA256 = (
    "bcdc904936891f3acd0b0db4364a964077ad9508d4d650c84df81bd1a8cee49c"
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
    identities = [identity for pair in PAIRS for identity in pair]
    if (
        len(PAIRS) != TASK_COUNT
        or len(DRIFT_PAIRS) != DRIFT_TASK_COUNT
        or len(ORDINARY_PAIRS) != ORDINARY_TASK_COUNT
        or any(len(pair) != ROWS_PER_TASK for pair in PAIRS)
        or len(identities) != TASK_COUNT * ROWS_PER_TASK
        or len(set(identities)) != len(identities)
        or any(
            re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,79}", identity) is None
            for identity in identities
        )
    ):
        raise RuntimeError("V2.55.77 identity vector drifted")
    if (
        EXPECTED_IDENTITY_VECTOR_SHA256 != "TO_BE_FROZEN"
        and payload_sha256(identities) != EXPECTED_IDENTITY_VECTOR_SHA256
    ):
        raise RuntimeError("V2.55.77 identity vector hash drifted")
    return identities


def pair_vector() -> list[tuple[str, str]]:
    identity_vector()
    return list(PAIRS)


def columns_for_index(index: int) -> tuple[str, str]:
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < TASK_COUNT:
        raise ValueError("V2.55.77 task index drifted")
    return DRIFT_COLUMNS if index < DRIFT_TASK_COUNT else ORDINARY_COLUMNS


def exposure_for_index(index: int) -> str:
    columns = columns_for_index(index)
    return "canonical_drift" if columns == DRIFT_COLUMNS else "ordinary_ascii"


def _question(index: int, first: str, second: str) -> str:
    columns = columns_for_index(index)
    spelling = (
        "Preserve the supplied column spellings byte-for-byte, including each "
        "full-width character. "
        if index < DRIFT_TASK_COUNT
        else "Preserve the supplied ASCII column spellings byte-for-byte. "
    )
    return (
        "Use public web search and authoritative PyPI project metadata to return "
        "exactly one Markdown table and no prose for the two visible projects "
        f"<PROJECT>{first}</PROJECT> and <PROJECT>{second}</PROJECT>. Columns "
        f"exactly: {columns[0]} | {columns[1]}. "
        + spelling
        + "Return exactly two rows in the supplied project order, one for each "
        "project. The second column means the highest PEP 440 release with at "
        "least one published file that is neither a pre-release nor a development "
        "release. Use the canonical PyPI project name in the first column. Use "
        "Unknown only when same-forward fetched public pages do not establish a "
        "requested value."
    )


def task_vector() -> list[dict[str, str]]:
    values: list[dict[str, str]] = []
    for index, (first, second) in enumerate(pair_vector()):
        question = _question(index, first, second)
        opaque = "task_" + hashlib.sha256(
            f"v25577:{index}:{question}".encode()
        ).hexdigest()[:24]
        values.append({"opaque_id": opaque, "question": question})
    checked = validate_task_vector(values)
    if (
        EXPECTED_TASK_VECTOR_SHA256 != "TO_BE_FROZEN"
        and payload_sha256(checked) != EXPECTED_TASK_VECTOR_SHA256
    ):
        raise RuntimeError("V2.55.77 task vector hash drifted")
    return checked


def validate_task_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.55.77 task denominator drifted")
    output: list[dict[str, str]] = []
    identities: list[str] = []
    for index, (raw, pair) in enumerate(zip(values, PAIRS, strict=True)):
        expected_question = _question(index, *pair)
        if not isinstance(raw, Mapping) or set(raw) != {"opaque_id", "question"}:
            raise ValueError("V2.55.77 runtime input shape drifted")
        opaque = raw.get("opaque_id")
        question = raw.get("question")
        if (
            not isinstance(opaque, str)
            or re.fullmatch(r"task_[0-9a-f]{24}", opaque) is None
            or question != expected_question
            or "https://" in str(question)
            or any(
                token in str(question).casefold()
                for token in (
                    "ground_truth",
                    "question_type",
                    "task_category",
                    "evaluator",
                    "score file",
                    "answer key",
                )
            )
        ):
            raise ValueError("V2.55.77 visible task binding drifted")
        identities.append(opaque)
        output.append({"opaque_id": opaque, "question": expected_question})
    if len(set(identities)) != TASK_COUNT:
        raise ValueError("V2.55.77 opaque identity collision")
    return output


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "one_indivisible_static_twenty_task_block": True,
        "selection_parent_commit": SELECTION_PARENT_COMMIT,
        "selection_rule": SELECTION_RULE,
        "identity_tree_and_ancestry_patch_exact_literal_occurrence_count": 0,
        "selection_reads_repository_history_only": True,
        "endpoint_page_version_model_prediction_mapping_truth_evaluator_score_quality_or_outcome_used_for_selection": False,
        "individual_task_filtering_ranking_retention_replacement_retry_resume_or_backfill": False,
        "visible_column_bytes_preassign_exposure_before_any_forward_effect": True,
        "canonical_drift_and_ordinary_negative_control_task_counts": [10, 10],
        "historical_parent_replay_routes_or_selects_fresh_forward_tasks": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "network_model_search_fetch_evaluator_or_benchmark_authorized": False,
    }


def mechanism_gate() -> dict[str, Any]:
    return {
        "fixed_task_denominator": TASK_COUNT,
        "required_terminal_tasks": TASK_COUNT,
        "required_successor_runtime_completed_tasks": TASK_COUNT,
        "required_successor_model_generated_tasks": TASK_COUNT,
        "maximum_successor_fallback_tasks": 0,
        "maximum_successor_outer_failure_tasks": 0,
        "required_preassigned_canonical_drift_tasks": DRIFT_TASK_COUNT,
        "required_preassigned_ordinary_ascii_tasks": ORDINARY_TASK_COUNT,
        "required_predecessor_counterfactual_failure_tasks": DRIFT_TASK_COUNT,
        "required_successor_canonical_column_handoff_tasks": DRIFT_TASK_COUNT,
        "required_successor_ordinary_canonical_projection_tasks": ORDINARY_TASK_COUNT,
        "required_ordinary_control_candidate_byte_equal_tasks": ORDINARY_TASK_COUNT,
        "maximum_candidate_parent_prediction_loss_tasks": 0,
        "maximum_result_stage_binding_failure_tasks": 0,
        "maximum_unsafe_handoff_tasks": 0,
        "minimum_drift_candidate_prediction_changed_from_failure_fallback_tasks": 8,
        "exact_physical_queries_per_completed_task": 4,
        "maximum_physical_fetches_per_completed_task": 14,
        "exact_normal_path_model_forwards_per_completed_task": 3,
        "one_successor_parent_forward_per_task": True,
        "control_and_candidate_share_all_provider_retrieval_and_sampling_effects": True,
        "candidate_additional_queries_fetches_model_calls_or_sampling_effects": 0,
        "both_prediction_vectors_frozen_before_truth_or_quality": True,
        "positive_signed_credit_count": 0,
        "postfreeze_paired_quality_required": True,
    }


def quality_gate() -> dict[str, Any]:
    return {
        "fixed_task_denominator": TASK_COUNT,
        "each_control_and_candidate_prediction_evaluated_exactly_once": True,
        "fixed20_failure_as_zero_metrics_reported": True,
        "minimum_arm_blind_paired_complete_tasks": 18,
        "paired_complete_selection_uses_only_truth_availability": True,
        "prediction_arm_outcome_or_score_used_for_completeness_selection": False,
        "candidate_exact_strictly_greater_than_control_on_fixed20": True,
        "minimum_candidate_exact_wins_on_paired_complete": 6,
        "maximum_candidate_exact_losses_on_paired_complete": 0,
        "maximum_two_sided_exact_sign_test_p": 0.05,
        "candidate_entity_row_item_column_and_composite_nonregression_on_fixed20": True,
        "candidate_invalid_and_fallback_nonincrease_on_fixed20": True,
        "ordinary_negative_control_predictions_byte_equal": True,
        "same_forward_provider_retrieval_and_sampling_effects": True,
        "official_identity_bound_latest_stable_version_truth": True,
        "positive_signed_credit_count": 0,
    }


__all__ = [name for name in globals() if name.isupper()] + [
    "columns_for_index",
    "exposure_for_index",
    "identity_vector",
    "mechanism_gate",
    "pair_vector",
    "payload_sha256",
    "quality_gate",
    "source_policy",
    "task_vector",
    "validate_task_vector",
]
