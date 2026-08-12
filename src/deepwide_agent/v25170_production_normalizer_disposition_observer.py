"""Pure content-free observer for production Markdown normalization.

The observer mirrors the frozen V2.51.35 production acceptance path without
changing it.  It emits one mutually-exclusive structural disposition plus
aggregate parser counts.  Response text, cells, columns, question, identity,
URL, page, prediction, semantic hashes, and credentials are never emitted.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from . import v24257_score_first_runtime as score
from . import v24259_deterministic_table_normalizer as normalizer
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25170_production_normalizer_disposition_observer_v1"
ROLE = "v25170_content_free_production_normalizer_disposition_observation"
DISPOSITION_NAMES = (
    "exact_table_accepted",
    "normalized_table_accepted",
    "invalid_required_columns_reject",
    "no_pipe_group_reject",
    "no_separator_row_reject",
    "no_bindable_header_reject",
    "separator_width_mismatch_reject",
    "missing_data_rows_reject",
    "malformed_row_or_escaped_pipe_reject",
)
COUNT_NAMES = (
    "pipe_group_count",
    "separator_row_count",
    "header_bound_separator_count",
    "width_bound_separator_count",
    "data_bearing_separator_count",
    "malformed_candidate_count",
    "normalizer_candidate_count",
)


def _valid_required(columns: Sequence[str]) -> bool:
    required = [str(value).strip() for value in columns if str(value).strip()]
    normalized = [score._normalize_column(value) for value in required]
    return bool(
        required
        and len(required) <= 20
        and len(set(normalized)) == len(required)
        and all(normalized)
    )


def _structural_counts(
    text: str, columns: Sequence[str]
) -> dict[str, int]:
    required = [str(value).strip() for value in columns if str(value).strip()]
    groups = normalizer._groups(text)
    counts = {name: 0 for name in COUNT_NAMES}
    counts["pipe_group_count"] = len(groups)
    for group in groups:
        for separator_index, separator in enumerate(group):
            if not normalizer._is_separator(separator):
                continue
            counts["separator_row_count"] += 1
            if separator_index < 1:
                continue
            header = group[separator_index - 1]
            plan = normalizer._header_plan(header, required)
            if plan is None:
                continue
            counts["header_bound_separator_count"] += 1
            if len(separator) != len(header):
                continue
            counts["width_bound_separator_count"] += 1
            source_rows = [
                row
                for row in group[separator_index + 1 :]
                if not normalizer._is_separator(row)
            ]
            if not source_rows:
                continue
            counts["data_bearing_separator_count"] += 1
            mode, mapping, _rank = plan
            normalized_rows = 0
            dropped = 0
            for row in source_rows:
                if len(row) == len(header):
                    values = [row[index].strip() for index in mapping]
                elif mode.startswith("drop_index") and len(row) == len(required):
                    values = [row[index - 1].strip() for index in mapping]
                else:
                    dropped += 1
                    continue
                if any("\\|" in value for value in values):
                    dropped += 1
                    continue
                normalized_rows += 1
            if normalized_rows and not dropped:
                counts["normalizer_candidate_count"] += 1
            else:
                counts["malformed_candidate_count"] += 1
    return counts


def observe_production_normalization(
    text: str,
    *,
    columns: Sequence[str],
    provider_output_truncated: bool,
) -> dict[str, Any]:
    """Return one content-free disposition with frozen-parser parity."""

    if not isinstance(text, str) or not isinstance(provider_output_truncated, bool):
        raise TypeError("V2.51.70 observer input drifted")
    if isinstance(columns, (str, bytes)):
        raise TypeError("V2.51.70 columns must be a sequence")
    required = tuple(str(value).strip() for value in columns if str(value).strip())
    exact, _errors = score.extract_valid_markdown_table(text, required)
    normalized: str | None = None
    if exact is None:
        normalized, _diagnostics = normalizer.normalize_candidate_table(
            text, required, unknown_marker="Unknown"
        )
    counts = _structural_counts(text, required)
    valid_required = _valid_required(required)
    if normalized is not None and counts["normalizer_candidate_count"] == 0:
        raise ValueError("V2.51.70 frozen normalizer positive parity drifted")
    if (
        exact is None
        and normalized is None
        and counts["normalizer_candidate_count"] != 0
    ):
        raise ValueError("V2.51.70 frozen normalizer negative parity drifted")

    if exact is not None:
        disposition = "exact_table_accepted"
    elif normalized is not None:
        disposition = "normalized_table_accepted"
    elif not valid_required:
        disposition = "invalid_required_columns_reject"
    elif counts["pipe_group_count"] == 0:
        disposition = "no_pipe_group_reject"
    elif counts["separator_row_count"] == 0:
        disposition = "no_separator_row_reject"
    elif counts["header_bound_separator_count"] == 0:
        disposition = "no_bindable_header_reject"
    elif counts["width_bound_separator_count"] == 0:
        disposition = "separator_width_mismatch_reject"
    elif counts["data_bearing_separator_count"] == 0:
        disposition = "missing_data_rows_reject"
    else:
        disposition = "malformed_row_or_escaped_pipe_reject"

    dispositions = {name: int(name == disposition) for name in DISPOSITION_NAMES}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "required_column_count": len(required),
        **counts,
        "disposition_counts": dispositions,
        "exact_parser_accepted": exact is not None,
        "normalizer_accepted_after_exact_failure": normalized is not None,
        "frozen_synthesis_contract_accepted": exact is not None
        or normalized is not None,
        "provider_output_truncated": provider_output_truncated,
        "observer_changes_response_fallback_prediction_candidate_routing_or_budget": False,
        "contains_response_cell_column_question_identity_url_page_key_value_prediction_semantic_hash_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_observation(value)


def validate_observation(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    dispositions = copied.get("disposition_counts")
    count_names = ("required_column_count", *COUNT_NAMES)
    true_names = ()
    false_names = (
        "observer_changes_response_fallback_prediction_candidate_routing_or_budget",
        "contains_response_cell_column_question_identity_url_page_key_value_prediction_semantic_hash_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    booleans = (
        "exact_parser_accepted",
        "normalizer_accepted_after_exact_failure",
        "frozen_synthesis_contract_accepted",
        "provider_output_truncated",
        *true_names,
        *false_names,
    )
    accepted_dispositions = {
        "exact_table_accepted",
        "normalized_table_accepted",
    }
    active = (
        {name for name, count in dispositions.items() if count == 1}
        if isinstance(dispositions, Mapping)
        else set()
    )
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            *count_names,
            "disposition_counts",
            *booleans,
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in count_names
        )
        or not isinstance(dispositions, Mapping)
        or set(dispositions) != set(DISPOSITION_NAMES)
        or any(
            isinstance(count, bool) or not isinstance(count, int) or count not in {0, 1}
            for count in dispositions.values()
        )
        or sum(dispositions.values()) != 1
        or any(not isinstance(copied.get(name), bool) for name in booleans)
        or copied["exact_parser_accepted"]
        is not (active == {"exact_table_accepted"})
        or copied["normalizer_accepted_after_exact_failure"]
        is not (active == {"normalized_table_accepted"})
        or copied["frozen_synthesis_contract_accepted"]
        is not bool(active.intersection(accepted_dispositions))
        or copied["normalizer_accepted_after_exact_failure"]
        and copied["normalizer_candidate_count"] == 0
        or active == {"no_pipe_group_reject"}
        and copied["pipe_group_count"] != 0
        or active == {"no_separator_row_reject"}
        and copied["separator_row_count"] != 0
        or active == {"no_bindable_header_reject"}
        and copied["header_bound_separator_count"] != 0
        or active == {"separator_width_mismatch_reject"}
        and copied["width_bound_separator_count"] != 0
        or active == {"missing_data_rows_reject"}
        and copied["data_bearing_separator_count"] != 0
        or active == {"malformed_row_or_escaped_pipe_reject"}
        and copied["data_bearing_separator_count"] == 0
        or any(copied.get(name) is not True for name in true_names)
        or any(copied.get(name) is not False for name in false_names)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.70 normalizer disposition observation drifted")
    return copied


__all__ = [
    "COUNT_NAMES",
    "DISPOSITION_NAMES",
    "POLICY_ID",
    "ROLE",
    "observe_production_normalization",
    "validate_observation",
]
