"""Pure label-blind consensus over three independently frozen table rollouts.

The selector accepts a visible question and exactly three Markdown tables.  It
has no filesystem, benchmark metadata, evaluator, score, reward, model, search,
or network capability.  Tables are aligned only by explicit visible columns,
normalized row identity, and normalized cell text.

The medoid rollout's full row set is preserved; a row absent from the medoid is
added only when at least two other rollouts support it.  A known cell value is
admitted only when at least two rollouts agree.  Otherwise the medoid rollout's
value is retained, except that an unknown medoid cell may be filled by any
single known value only when all other observed values are unknown.  This is a
deterministic structural ensemble, not a claim of evidence correctness.
"""

from __future__ import annotations

import copy
import math
from collections import Counter, OrderedDict
from collections.abc import Mapping, Sequence
from typing import Any

from .v24257_score_first_runtime import _normalize_column
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24325_shared_prefix_revision_runtime import _is_unknown, _support_normalize
from .v24675_expanded_visible_schema import extract_expanded_visible_columns
from .v24743_generic_record_binding import _render_table, _table_matrix


POLICY_ID = "v24816_three_rollout_label_blind_table_consensus_v1"
ROLE = "v24816_label_blind_consensus_result"
RECEIPT_ROLE = "v24816_label_blind_consensus_receipt"
SOURCE_COUNT = 3


def _columns_key(columns: Sequence[str]) -> tuple[str, ...]:
    return tuple(_normalize_column(str(column)) for column in columns)


def _row_key(value: object) -> str:
    return "" if _is_unknown(value) else _support_normalize(value)


def _value_key(value: object) -> str:
    return _support_normalize(value)


def _unknown_marker(question: str) -> str:
    return "未知" if any("\u4e00" <= character <= "\u9fff" for character in question) else "Unknown"


def _source_matrix(table: str) -> tuple[list[str], list[list[str]], OrderedDict[str, list[str]]]:
    columns, rows = _table_matrix(table)
    if not columns or any(len(row) != len(columns) for row in rows):
        raise ValueError("V2.48.16 source table width drifted")
    groups: OrderedDict[str, list[list[str]]] = OrderedDict()
    for row in rows:
        key = _row_key(row[0])
        if key:
            groups.setdefault(key, []).append(list(row))
    projected: OrderedDict[str, list[str]] = OrderedDict()
    for key, candidates in groups.items():
        projected[key] = min(
            candidates,
            key=lambda row: (
                -sum(not _is_unknown(value) for value in row[1:]),
                tuple(_value_key(value) for value in row),
            ),
        )
    return columns, rows, projected


def _pair_distance(left: Mapping[str, list[str]], right: Mapping[str, list[str]]) -> float:
    union = set(left) | set(right)
    if not union:
        return 1.0
    total = 0.0
    for key in union:
        if key not in left or key not in right:
            total += 1.0
            continue
        lrow, rrow = left[key], right[key]
        if len(lrow) != len(rrow):
            total += 1.0
            continue
        compared = max(1, len(lrow) - 1)
        mismatches = sum(
            _value_key(lrow[index]) != _value_key(rrow[index])
            for index in range(1, len(lrow))
        )
        total += mismatches / compared
    return total / len(union)


def _medoid(
    maps: Sequence[Mapping[str, list[str]]], predictions: Sequence[str]
) -> tuple[int, list[float]]:
    distances = [
        sum(_pair_distance(maps[index], maps[other]) for other in range(SOURCE_COUNT) if other != index)
        for index in range(SOURCE_COUNT)
    ]
    return min(
        range(SOURCE_COUNT),
        key=lambda index: (distances[index], payload_sha256(predictions[index])),
    ), distances


def build_consensus(question: str, predictions: Sequence[str]) -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.48.16 visible question is absent")
    if (
        not isinstance(predictions, Sequence) or isinstance(predictions, (str, bytes))
        or len(predictions) != SOURCE_COUNT
        or any(not isinstance(value, str) or not value.strip() for value in predictions)
    ):
        raise ValueError("V2.48.16 requires exactly three table predictions")
    parsed = [_source_matrix(value) for value in predictions]
    columns = [item[0] for item in parsed]
    keys = [_columns_key(item) for item in columns]
    visible = extract_expanded_visible_columns(question)
    visible_key = _columns_key(visible) if visible else ()
    if keys[0] != keys[1] or keys[0] != keys[2]:
        raise ValueError("V2.48.16 source headers disagree")
    if visible_key and keys[0] != visible_key:
        raise ValueError("V2.48.16 source header disagrees with visible question")
    maps = [item[2] for item in parsed]
    medoid, distances = _medoid(maps, predictions)
    ordered_keys: list[str] = []
    for row in parsed[medoid][1]:
        key = _row_key(row[0])
        if key and key not in ordered_keys:
            ordered_keys.append(key)
    remaining_keys = sorted(set().union(*(set(value) for value in maps)) - set(ordered_keys))
    ordered_keys.extend(remaining_keys)

    output: list[list[str]] = []
    supported_rows = 0
    excluded_singletons = 0
    medoid_only_rows = 0
    majority_cells = 0
    single_known_fills = 0
    unresolved_conflicts = 0
    medoid_cells = 0
    marker = _unknown_marker(question)
    for key in ordered_keys:
        present = [(index, maps[index][key]) for index in range(SOURCE_COUNT) if key in maps[index]]
        in_medoid = key in maps[medoid]
        if len(present) < 2 and not in_medoid:
            excluded_singletons += 1
            continue
        if len(present) >= 2:
            supported_rows += 1
        else:
            medoid_only_rows += 1
        representative = maps[medoid].get(
            key,
            min(
                (candidate for _index, candidate in present),
                key=lambda candidate: (
                    -sum(not _is_unknown(value) for value in candidate[1:]),
                    payload_sha256(candidate),
                ),
            ),
        )
        row = [representative[0]]
        for column_index in range(1, len(columns[0])):
            values = [candidate[column_index] for _, candidate in present]
            known = [value for value in values if not _is_unknown(value)]
            counts = Counter(_value_key(value) for value in known)
            majority = [name for name, count in counts.items() if name and count >= 2]
            if majority:
                selected_key = min(majority)
                value = next(value for value in known if _value_key(value) == selected_key)
                majority_cells += 1
            else:
                medoid_value = representative[column_index]
                if _is_unknown(medoid_value) and len(set(counts)) == 1 and known:
                    value = known[0]
                    single_known_fills += 1
                else:
                    value = medoid_value
                    medoid_cells += 1
                    if len(counts) > 1:
                        unresolved_conflicts += 1
                if not str(value).strip():
                    value = marker
            row.append(str(value))
        output.append(row)
    if not output:
        raise ValueError("V2.48.16 consensus has no two-source-supported rows")
    result_table = _render_table(columns[medoid], output)
    check_columns, check_rows, check_map = _source_matrix(result_table)
    if (
        _columns_key(check_columns) != keys[medoid]
        or len(check_rows) != len(output)
        or len(check_map) != len(output)
    ):
        raise ValueError("V2.48.16 rendered consensus drifted")
    receipt = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "source_count": SOURCE_COUNT,
        "source_row_counts": [len(item[1]) for item in parsed],
        "source_unique_identity_counts": [len(item[2]) for item in parsed],
        "visible_explicit_column_count": len(visible),
        "header_consensus": True,
        "visible_header_match_when_explicit": not visible or keys[0] == visible_key,
        "medoid_source_index": medoid,
        "medoid_distance_sums": [round(value, 12) for value in distances],
        "two_source_supported_output_rows": supported_rows,
        "medoid_only_rows_preserved": medoid_only_rows,
        "single_source_rows_excluded": excluded_singletons,
        "majority_supported_cells": majority_cells,
        "single_known_unknown_fills": single_known_fills,
        "medoid_fallback_cells": medoid_cells,
        "unresolved_known_conflict_cells": unresolved_conflicts,
        "output_row_count": len(output),
        "all_output_normalized_identities_unique": len(check_map) == len(output),
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_sha256"] = payload_sha256(receipt)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "prediction": result_table,
        "prediction_sha256": payload_sha256(result_table),
        "receipt": receipt,
    }
    value["result_sha256"] = payload_sha256(value)
    return validate_consensus(value, question=question, predictions=predictions, replay=False)


def symmetric_medoid_fallback(
    question: str, predictions: Sequence[str]
) -> dict[str, Any]:
    """Select a source-identity-agnostic medoid when strict consensus cannot run."""

    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.48.16 visible question is absent")
    if (
        not isinstance(predictions, Sequence)
        or isinstance(predictions, (str, bytes))
        or len(predictions) != SOURCE_COUNT
    ):
        raise ValueError("V2.48.16 fallback requires exactly three predictions")
    parsed = [_source_matrix(value) for value in predictions]
    maps = [item[2] for item in parsed]
    medoid, distances = _medoid(maps, predictions)
    selected = predictions[medoid]
    receipt = {
        "artifact_version": 1,
        "role": "v24816_symmetric_medoid_fallback_receipt",
        "policy_id": POLICY_ID,
        "reason": "strict_header_consensus_unavailable",
        "source_count": SOURCE_COUNT,
        "selected_prediction_sha256": payload_sha256(selected),
        "medoid_distance_sums": [round(value, 12) for value in distances],
        "source_order_or_historical_score_used_for_tie_break": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_sha256"] = payload_sha256(receipt)
    value = {
        "artifact_version": 1,
        "role": "v24816_symmetric_medoid_fallback_result",
        "policy_id": POLICY_ID,
        "prediction": selected,
        "prediction_sha256": payload_sha256(selected),
        "receipt": receipt,
    }
    value["result_sha256"] = payload_sha256(value)
    return value


def validate_consensus(
    value: Mapping[str, Any], *, question: str, predictions: Sequence[str],
    replay: bool = True,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_sha256", None)
    receipt = copied.get("receipt")
    if not isinstance(receipt, Mapping):
        raise ValueError("V2.48.16 receipt absent")
    receipt_unsigned = dict(receipt)
    receipt_seal = receipt_unsigned.pop("receipt_sha256", None)
    numbers = (
        "source_count", "visible_explicit_column_count", "medoid_source_index",
        "two_source_supported_output_rows", "medoid_only_rows_preserved",
        "single_source_rows_excluded",
        "majority_supported_cells", "single_known_unknown_fills",
        "medoid_fallback_cells", "unresolved_known_conflict_cells",
        "output_row_count",
    )
    if (
        copied.get("role") != ROLE or copied.get("policy_id") != POLICY_ID
        or not isinstance(copied.get("prediction"), str)
        or copied.get("prediction_sha256") != payload_sha256(copied["prediction"])
        or seal != payload_sha256(unsigned)
        or receipt.get("role") != RECEIPT_ROLE
        or receipt.get("policy_id") != POLICY_ID
        or any(isinstance(receipt.get(name), bool) or not isinstance(receipt.get(name), int) or receipt[name] < 0 for name in numbers)
        or receipt.get("source_count") != SOURCE_COUNT
        or receipt.get("medoid_source_index") not in range(SOURCE_COUNT)
        or not isinstance(receipt.get("source_row_counts"), list)
        or len(receipt["source_row_counts"]) != SOURCE_COUNT
        or not isinstance(receipt.get("source_unique_identity_counts"), list)
        or len(receipt["source_unique_identity_counts"]) != SOURCE_COUNT
        or not isinstance(receipt.get("medoid_distance_sums"), list)
        or len(receipt["medoid_distance_sums"]) != SOURCE_COUNT
        or any(not isinstance(number, (int, float)) or not math.isfinite(float(number)) or number < 0 for number in receipt["medoid_distance_sums"])
        or receipt.get("header_consensus") is not True
        or receipt.get("visible_header_match_when_explicit") is not True
        or receipt.get("two_source_supported_output_rows")
        + receipt.get("medoid_only_rows_preserved")
        != receipt.get("output_row_count")
        or receipt.get("all_output_normalized_identities_unique") is not True
        or receipt.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or receipt.get("file_environment_network_model_search_fetch_process_or_evaluator_accessed") is not False
        or receipt.get("benchmark_launch_or_evaluator_authorized") is not False
        or receipt_seal != payload_sha256(receipt_unsigned)
    ):
        raise ValueError("V2.48.16 consensus result drifted")
    if replay and copied != build_consensus(question, predictions):
        raise ValueError("V2.48.16 consensus replay drifted")
    return copied


__all__ = [
    "POLICY_ID", "ROLE", "build_consensus", "symmetric_medoid_fallback",
    "validate_consensus",
]
