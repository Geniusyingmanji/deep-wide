"""Pure structural normalization before semantic target construction.

The V2.43.46 diagnosis found that a successful two-model trajectory can be
collapsed into a coarse ``ValidationError`` when the first table column has
duplicate identities after normalization.  This append-only component merges
only those duplicate identity groups.  It never chooses between conflicting
known cell values: conflicts become the caller-supplied unknown marker.

The component is benchmark-external and performs no file, environment,
network, model, search, fetch, process, evaluator, or scoring access.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24325_shared_prefix_revision_runtime as base
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24333_programmatic_support_catalog import CellTarget


POLICY_ID = "v24348_duplicate_identity_structural_normalizer_v1"
ROLE = "v24348_structural_normalization_result"
RECEIPT_ROLE = "v24348_structural_normalization_receipt"
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "unknown_marker",
        "input_table",
        "normalized_table",
        "normalization_receipt",
        "result_sha256",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "input_row_count",
        "output_row_count",
        "identity_group_count",
        "duplicate_identity_group_count",
        "merged_duplicate_row_count",
        "empty_identity_group_count",
        "empty_identity_row_count",
        "empty_identity_rows_quarantined_count",
        "unique_identity_row_count",
        "consensus_filled_unknown_cell_count",
        "conflicting_known_cell_count",
        "conflicting_known_cells_quarantined_to_unknown_count",
        "safe_semantic_target_count",
        "empty_identity_cells_excluded_from_semantic_targets",
        "all_output_normalized_identities_unique",
        "unique_nonempty_input_identity_preserved",
        "conflicting_known_value_selected_as_truth",
        "question_prompt_response_query_url_page_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)
STAGE_RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "stage",
        "reason",
        "effect_accounting_complete",
        "model_requests_lower_bound",
        "model_attempts_lower_bound",
        "search_calls_lower_bound",
        "fetch_calls_lower_bound",
        "free_form_exception_type_or_message_read_or_emitted",
        "question_prompt_response_query_url_page_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)
STAGE_RECEIPT_ROLE = "v24348_content_free_structural_stage_receipt"
STAGES = frozenset(
    {
        "baseline_table_parse",
        "duplicate_identity_normalization",
        "semantic_target_construction",
        "semantic_catalog_build",
        "result_validation",
    }
)
REASONS = frozenset(
    {
        "none",
        "table_parse_rejected",
        "duplicate_identity_detected",
        "empty_identity_excluded",
        "candidate_row_preservation_rejected",
        "structural_validation_rejected",
    }
)


def _unknown_marker(value: object) -> str:
    marker = str(value)
    if not marker.strip() or "|" in marker or "\n" in marker or "\r" in marker:
        raise ValueError("V2.43.48 unknown marker is unsafe")
    return marker.strip()


def _known(value: object) -> bool:
    return not base._is_unknown(value)


def _normalized(value: object) -> str:
    return base._support_normalize(value)


def _identity(value: object) -> str:
    return "" if base._is_unknown(value) else _normalized(value)


def _representative(group: Sequence[tuple[int, list[str]]]) -> tuple[int, list[str]]:
    if not group:
        raise ValueError("V2.43.48 identity group is empty")
    return min(
        group,
        key=lambda item: (
            -sum(_known(value) for value in item[1][1:]),
            item[0],
        ),
    )


def _compute(table: str, *, unknown_marker: str) -> dict[str, Any]:
    marker = _unknown_marker(unknown_marker)
    columns, raw_rows = base._table_matrix(table)
    if any(len(row) != len(columns) for row in raw_rows):
        raise ValueError("V2.43.48 input row width drifted")

    groups: OrderedDict[str, list[tuple[int, list[str]]]] = OrderedDict()
    for ordinal, row in enumerate(raw_rows):
        groups.setdefault(_identity(row[0]), []).append((ordinal, list(row)))

    output: list[list[str]] = []
    duplicate_groups = 0
    merged_rows = 0
    empty_groups = 0
    empty_rows = 0
    unique_rows = 0
    filled = 0
    conflicts = 0
    for identity, group in groups.items():
        if not identity:
            empty_groups += 1
            empty_rows += len(group)
            continue
        if len(group) > 1:
            duplicate_groups += 1
            merged_rows += len(group) - 1
        else:
            unique_rows += 1
        _, representative = _representative(group)
        row = list(representative)
        if len(group) > 1:
            for column_index in range(1, len(columns)):
                known_values = [
                    candidate[column_index]
                    for _, candidate in group
                    if _known(candidate[column_index])
                ]
                by_normalized: OrderedDict[str, list[str]] = OrderedDict()
                for value in known_values:
                    by_normalized.setdefault(_normalized(value), []).append(value)
                if len(by_normalized) == 1:
                    if not _known(row[column_index]):
                        row[column_index] = next(iter(by_normalized.values()))[0]
                        filled += 1
                elif len(by_normalized) > 1:
                    conflicts += 1
                    row[column_index] = marker
        output.append(row)

    normalized_table = base._render_table(columns, output)
    canonical, errors = base.extract_valid_markdown_table(normalized_table, columns)
    if canonical != normalized_table or errors:
        raise ValueError("V2.43.48 normalized table is not canonical")
    output_keys = [_identity(row[0]) for row in output]
    nonempty_unique_inputs = {
        identity for identity, group in groups.items() if identity and len(group) == 1
    }
    output_key_set = set(output_keys)
    safe_targets = sum(
        len(columns) - 1 for row in output if _identity(row[0])
    )
    receipt = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "input_row_count": len(raw_rows),
        "output_row_count": len(output),
        "identity_group_count": len(groups),
        "duplicate_identity_group_count": duplicate_groups,
        "merged_duplicate_row_count": merged_rows,
        "empty_identity_group_count": empty_groups,
        "empty_identity_row_count": empty_rows,
        "empty_identity_rows_quarantined_count": empty_rows,
        "unique_identity_row_count": unique_rows,
        "consensus_filled_unknown_cell_count": filled,
        "conflicting_known_cell_count": conflicts,
        "conflicting_known_cells_quarantined_to_unknown_count": conflicts,
        "safe_semantic_target_count": safe_targets,
        "empty_identity_cells_excluded_from_semantic_targets": empty_rows
        * (len(columns) - 1),
        "all_output_normalized_identities_unique": len(output_keys) == len(output_key_set),
        "unique_nonempty_input_identity_preserved": nonempty_unique_inputs.issubset(output_key_set),
        "conflicting_known_value_selected_as_truth": False,
        "question_prompt_response_query_url_page_prediction_answer_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_sha256"] = payload_sha256(receipt)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "unknown_marker": marker,
        "input_table": table,
        "normalized_table": normalized_table,
        "normalization_receipt": receipt,
    }
    value["result_sha256"] = payload_sha256(value)
    return value


def normalize_baseline_table(
    table: str,
    *,
    unknown_marker: str = "Unknown",
) -> dict[str, Any]:
    if not isinstance(table, str):
        raise ValueError("V2.43.48 input table is not text")
    value = _compute(table, unknown_marker=unknown_marker)
    validate_normalization_result(value, unknown_marker=unknown_marker)
    return value


def validate_normalization_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    counts = RECEIPT_KEYS - {
        "artifact_version",
        "role",
        "policy_id",
        "all_output_normalized_identities_unique",
        "unique_nonempty_input_identity_preserved",
        "conflicting_known_value_selected_as_truth",
        "question_prompt_response_query_url_page_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != RECEIPT_ROLE
        or value.get("policy_id") != POLICY_ID
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in counts
        )
        or value.get("input_row_count")
        != value.get("output_row_count")
        + value.get("merged_duplicate_row_count")
        + value.get("empty_identity_row_count")
        or value.get("identity_group_count")
        != value.get("output_row_count") + value.get("empty_identity_group_count")
        or value.get("duplicate_identity_group_count") > value.get("identity_group_count")
        or value.get("unique_identity_row_count")
        + value.get("duplicate_identity_group_count")
        + value.get("empty_identity_group_count")
        != value.get("identity_group_count")
        or value.get("empty_identity_row_count")
        != value.get("empty_identity_rows_quarantined_count")
        or value.get("conflicting_known_cell_count")
        != value.get("conflicting_known_cells_quarantined_to_unknown_count")
        or value.get("all_output_normalized_identities_unique") is not True
        or value.get("unique_nonempty_input_identity_preserved") is not True
        or value.get("conflicting_known_value_selected_as_truth") is not False
        or value.get("question_prompt_response_query_url_page_prediction_answer_opaque_id_or_credential_emitted") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("file_environment_network_model_search_fetch_process_or_evaluator_accessed") is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.48 normalization receipt drifted")
    return dict(value)


def validate_normalization_result(
    value: Mapping[str, Any],
    *,
    unknown_marker: str = "Unknown",
) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("result_sha256", None)
    if (
        set(value) != RESULT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(value.get("unknown_marker"), str)
        or _unknown_marker(value.get("unknown_marker")) != value.get("unknown_marker")
        or not isinstance(value.get("input_table"), str)
        or not isinstance(value.get("normalized_table"), str)
        or not isinstance(value.get("normalization_receipt"), Mapping)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.48 normalization result identity drifted")
    validate_normalization_receipt(value["normalization_receipt"])
    if _unknown_marker(unknown_marker) != value["unknown_marker"]:
        raise ValueError("V2.43.48 normalization marker drifted")
    expected = _compute(value["input_table"], unknown_marker=value["unknown_marker"])
    if dict(value) != expected:
        raise ValueError("V2.43.48 normalization replay drifted")
    return dict(value)


def semantic_targets(
    value: Mapping[str, Any],
    *,
    unknown_marker: str = "Unknown",
    maximum_targets: int = 512,
) -> list[CellTarget]:
    validated = validate_normalization_result(value, unknown_marker=unknown_marker)
    if (
        isinstance(maximum_targets, bool)
        or not isinstance(maximum_targets, int)
        or maximum_targets < 1
    ):
        raise ValueError("V2.43.48 maximum target count drifted")
    columns, rows = base._table_matrix(validated["normalized_table"])
    targets = [
        CellTarget(row[0], columns[column_index], row[column_index])
        for row in rows
        if _identity(row[0])
        for column_index in range(1, len(columns))
    ]
    targets.sort(
        key=lambda target: (
            not target.baseline_unknown,
            target.binding_sha256,
        )
    )
    output = targets[:maximum_targets]
    if len(output) != min(
        maximum_targets,
        int(validated["normalization_receipt"]["safe_semantic_target_count"]),
    ):
        raise ValueError("V2.43.48 semantic target accounting drifted")
    return output


def build_stage_receipt(
    *,
    stage: str,
    reason: str,
    effect_accounting_complete: bool,
    model_requests_lower_bound: int,
    model_attempts_lower_bound: int,
    search_calls_lower_bound: int,
    fetch_calls_lower_bound: int,
) -> dict[str, Any]:
    counts = {
        "model_requests_lower_bound": model_requests_lower_bound,
        "model_attempts_lower_bound": model_attempts_lower_bound,
        "search_calls_lower_bound": search_calls_lower_bound,
        "fetch_calls_lower_bound": fetch_calls_lower_bound,
    }
    if (
        stage not in STAGES
        or reason not in REASONS
        or not isinstance(effect_accounting_complete, bool)
        or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in counts.values()
        )
        or model_attempts_lower_bound < model_requests_lower_bound
    ):
        raise ValueError("V2.43.48 stage receipt input drifted")
    value = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "stage": stage,
        "reason": reason,
        "effect_accounting_complete": effect_accounting_complete,
        **counts,
        "free_form_exception_type_or_message_read_or_emitted": False,
        "question_prompt_response_query_url_page_prediction_answer_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    validate_stage_receipt(value)
    return value


def validate_stage_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    counts = (
        "model_requests_lower_bound",
        "model_attempts_lower_bound",
        "search_calls_lower_bound",
        "fetch_calls_lower_bound",
    )
    if (
        set(value) != STAGE_RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != STAGE_RECEIPT_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("stage") not in STAGES
        or value.get("reason") not in REASONS
        or not isinstance(value.get("effect_accounting_complete"), bool)
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in counts
        )
        or value.get("model_attempts_lower_bound", -1)
        < value.get("model_requests_lower_bound", 0)
        or value.get("free_form_exception_type_or_message_read_or_emitted") is not False
        or value.get("question_prompt_response_query_url_page_prediction_answer_opaque_id_or_credential_emitted") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("file_environment_network_model_search_fetch_process_or_evaluator_accessed") is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.48 stage receipt drifted")
    return dict(value)


__all__ = [
    "POLICY_ID",
    "REASONS",
    "ROLE",
    "STAGES",
    "build_stage_receipt",
    "normalize_baseline_table",
    "semantic_targets",
    "validate_normalization_receipt",
    "validate_normalization_result",
    "validate_stage_receipt",
]
