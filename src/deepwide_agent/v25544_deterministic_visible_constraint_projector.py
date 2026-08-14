"""Deterministic semantic-preserving projection for visible constraints.

V2.55.42 can place a visible constraint in the final synthesis prompt, but a
second sampled generation would confound the constraint effect with sampling
noise.  This pure projector instead transforms one already-produced exact
canonical table and exposes a shared-parent control/candidate pair.

Only three operations are permitted:

* reformat a complete, valid date into one unambiguous requested date style;
* convert one scalar with exactly one explicit source scale into one requested
  scale, preserving currency/prefix/suffix text; and
* stably sort all rows by one exact, fully comparable requested column.

Temporal ranges and rank-slot contracts are observed but never enforced by
row deletion, insertion, or relabeling.  Unknowns, partial dates, invalid
dates, ranges, percentages, multiple numbers/scales, mixed sort types, or
ambiguous values are byte-exact no-ops.  Schema, row count, row cells outside
the targeted transform, and all factual tokens are otherwise preserved.

The module is pure and has no file, environment, process, network, model,
search, fetch, evaluator, benchmark-label, mapping, gold, score, reward,
credential, or historical-result capability.  Entropy/information gain is
shadow-only and assigns no signed credit.  This build grants no launch.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from . import v24257_score_first_runtime as score
from . import v25369_changed_safe_verified_coordinate_edit as renderer
from . import v25541_visible_output_constraint_contract as contract_parent
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25544_deterministic_visible_constraint_projector_v1"
ROLE = "v25544_deterministic_visible_constraint_projection"
RECEIPT_ROLE = "v25544_content_free_visible_constraint_projection_receipt"
_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
_MONTHS.update({name[:3]: value for name, value in list(_MONTHS.items())})
_SCALE_FACTORS = {
    "thousand": Decimal("1e3"),
    "million": Decimal("1e6"),
    "billion": Decimal("1e9"),
    "trillion": Decimal("1e12"),
}
_SOURCE_SCALE = {
    "thousand": re.compile(r"\bthousand\b|千", re.IGNORECASE),
    "million": re.compile(r"\bmillion\b|百万", re.IGNORECASE),
    "billion": re.compile(r"\bbillion\b|十亿", re.IGNORECASE),
    "trillion": re.compile(r"\btrillion\b|万亿", re.IGNORECASE),
}
_NUMBER = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?![\w.])")


def _matrix(prediction: object, columns: Sequence[str]) -> list[list[str]]:
    required = tuple(str(value).strip() for value in columns)
    canonical, _errors = score.extract_valid_markdown_table(
        str(prediction), required
    )
    if canonical is None or canonical != str(prediction):
        raise ValueError("V2.55.44 expected exact canonical parent table")
    lines = [
        line.strip()
        for line in canonical.splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    matrix = [score._split_table_row(line) for line in lines]
    if (
        len(matrix) < 3
        or matrix[0] != list(required)
        or any(len(row) != len(required) for row in matrix)
    ):
        raise ValueError("V2.55.44 canonical matrix drifted")
    return matrix


def _parse_complete_date(value: object) -> date | None:
    text = " ".join(str(value or "").split())
    numeric = re.fullmatch(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", text)
    chinese = re.fullmatch(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", text)
    english = re.fullmatch(
        r"([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})", text
    )
    try:
        if numeric:
            return date(*(int(numeric.group(index)) for index in (1, 2, 3)))
        if chinese:
            return date(*(int(chinese.group(index)) for index in (1, 2, 3)))
        if english:
            month = _MONTHS.get(english.group(1).casefold())
            return (
                date(int(english.group(3)), int(month), int(english.group(2)))
                if month is not None
                else None
            )
    except ValueError:
        return None
    return None


def _render_date(value: date, style: str) -> str:
    if style == "iso_dash":
        return value.strftime("%Y-%m-%d")
    if style == "iso_slash":
        return value.strftime("%Y/%m/%d")
    if style == "iso_dot":
        return value.strftime("%Y.%m.%d")
    if style == "chinese_ymd":
        return f"{value.year:04d}年{value.month:02d}月{value.day:02d}日"
    if style == "chinese_ymd_unpadded":
        return f"{value.year:04d}年{value.month}月{value.day}日"
    if style == "english_long":
        return value.strftime("%B %d, %Y")
    if style == "english_short":
        return value.strftime("%b %d, %Y")
    raise ValueError("V2.55.44 unknown date style")


def _decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        return ""
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in {"", "-0"} else text


def _convert_scale(value: object, target: str) -> str | None:
    text = " ".join(str(value or "").split())
    if (
        not text
        or target not in _SCALE_FACTORS
        or re.search(r"%|(?:^|\s)[–—-](?:\s|$)|\bto\b|至|到", text, re.I)
    ):
        return None
    numbers = list(_NUMBER.finditer(text))
    scales = [
        (name, match)
        for name, pattern in _SOURCE_SCALE.items()
        for match in pattern.finditer(text)
    ]
    if len(numbers) != 1 or len(scales) != 1:
        return None
    source, scale_match = scales[0]
    number_match = numbers[0]
    try:
        number = Decimal(number_match.group(0).replace(",", ""))
    except InvalidOperation:
        return None
    converted = number * _SCALE_FACTORS[source] / _SCALE_FACTORS[target]
    scalar = _decimal_text(converted)
    if not scalar:
        return None
    start = min(number_match.start(), scale_match.start())
    end = max(number_match.end(), scale_match.end())
    replacement = scalar + " " + target
    output = (text[:start] + replacement + text[end:]).strip()
    return output if output and "|" not in output else None


def _sort_value(value: object, kind: str) -> tuple[int, Any] | None:
    text = " ".join(str(value or "").split())
    if not text or re.fullmatch(
        r"(?:unknown|n/?a|none|null|-|—|未知|不详|暂无)", text, re.I
    ):
        return None
    if kind == "date":
        parsed = _parse_complete_date(text)
        return (1, parsed.toordinal()) if parsed is not None else None
    numeric = re.fullmatch(r"[-+]?\d[\d,]*(?:\.\d+)?%?", text)
    if numeric:
        try:
            return 0, Decimal(text.replace(",", "").rstrip("%"))
        except InvalidOperation:
            return None
    if kind == "rank":
        return None
    return 2, text.casefold()


def apply_projection(
    base_prediction: object, contract: Mapping[str, Any]
) -> dict[str, Any]:
    """Return one shared-parent deterministic projection and private counts."""

    checked = contract_parent.validate_contract(contract)
    columns = tuple(checked["columns"])
    matrix = _matrix(base_prediction, columns)
    rows = copy.deepcopy(matrix[2:])
    column_index = {column: index for index, column in enumerate(columns)}
    date_examined = date_changed = date_rejected = 0
    scale_examined = scale_changed = scale_rejected = 0
    sort_attempted = sort_applied = sort_already_satisfied = sort_rejected = 0

    date_contract = checked["date_format"]
    if date_contract is not None:
        for column in date_contract["target_columns"]:
            index = column_index[column]
            for row in rows:
                before = row[index]
                if not before or re.fullmatch(
                    r"(?:unknown|n/?a|none|null|-|—|未知|不详|暂无)", before, re.I
                ):
                    continue
                date_examined += 1
                parsed = _parse_complete_date(before)
                if parsed is None:
                    date_rejected += 1
                    continue
                after = _render_date(parsed, date_contract["style"])
                if after != before:
                    row[index] = after
                    date_changed += 1

    scale_contract = checked["numeric_scale"]
    if scale_contract is not None:
        targets = list(scale_contract["target_columns"])
        if not targets:
            targets = list(columns[1:])
        for column in targets:
            index = column_index[column]
            for row in rows:
                before = row[index]
                if not re.search(r"\d", before):
                    continue
                scale_examined += 1
                after = _convert_scale(before, scale_contract["scale"])
                if after is None:
                    scale_rejected += 1
                    continue
                if after != before:
                    row[index] = after
                    scale_changed += 1

    order_contract = checked["explicit_order"]
    if order_contract is not None:
        sort_attempted = 1
        index = column_index[order_contract["target_column"]]
        values = [
            _sort_value(row[index], order_contract["value_kind"])
            for row in rows
        ]
        if (
            not values
            or any(value is None for value in values)
            or len({value[0] for value in values if value is not None}) != 1
        ):
            sort_rejected = 1
        else:
            paired = list(zip(rows, values, strict=True))
            ordered = sorted(
                paired,
                key=lambda item: item[1][1] if item[1] is not None else None,
                reverse=order_contract["direction"] == "descending",
            )
            projected = [copy.deepcopy(item[0]) for item in ordered]
            if projected != rows:
                rows = projected
                sort_applied = 1
            else:
                sort_already_satisfied = 1

    candidate = renderer._render(columns, rows)
    _matrix(candidate, columns)
    return {
        "control_prediction": str(base_prediction),
        "candidate_prediction": candidate,
        "date_cell_examined_count": date_examined,
        "date_cell_changed_count": date_changed,
        "date_cell_rejected_count": date_rejected,
        "scale_cell_examined_count": scale_examined,
        "scale_cell_changed_count": scale_changed,
        "scale_cell_rejected_count": scale_rejected,
        "sort_attempted_count": sort_attempted,
        "sort_applied_count": sort_applied,
        "sort_already_satisfied_count": sort_already_satisfied,
        "sort_rejected_count": sort_rejected,
        "row_count": len(rows),
        "candidate_prediction_changed": candidate != str(base_prediction),
    }


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    count_fields = (
        "date_cell_examined_count",
        "date_cell_changed_count",
        "date_cell_rejected_count",
        "scale_cell_examined_count",
        "scale_cell_changed_count",
        "scale_cell_rejected_count",
        "sort_attempted_count",
        "sort_applied_count",
        "sort_already_satisfied_count",
        "sort_rejected_count",
        "row_count",
        "positive_signed_credit_count",
    )
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(value.get(name, 0)) for name in count_fields},
        "candidate_prediction_changed": bool(value["candidate_prediction_changed"]),
        "only_complete_valid_dates_are_reformatted": True,
        "only_single_number_single_explicit_source_scale_cells_are_converted": True,
        "only_fully_comparable_single_kind_columns_are_sorted": True,
        "temporal_ranges_and_rank_slots_never_delete_insert_or_relabel_rows": True,
        "schema_row_count_and_non_targeted_cell_values_preserved": True,
        "one_shared_parent_prediction_and_zero_provider_effects": True,
        "contains_question_column_value_prediction_answer_hash_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    output["receipt_payload_sha256"] = payload_sha256(output)
    return validate_receipt(output)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    counts = (
        "date_cell_examined_count",
        "date_cell_changed_count",
        "date_cell_rejected_count",
        "scale_cell_examined_count",
        "scale_cell_changed_count",
        "scale_cell_rejected_count",
        "sort_attempted_count",
        "sort_applied_count",
        "sort_already_satisfied_count",
        "sort_rejected_count",
        "row_count",
        "positive_signed_credit_count",
    )
    true_flags = (
        "only_complete_valid_dates_are_reformatted",
        "only_single_number_single_explicit_source_scale_cells_are_converted",
        "only_fully_comparable_single_kind_columns_are_sorted",
        "temporal_ranges_and_rank_slots_never_delete_insert_or_relabel_rows",
        "schema_row_count_and_non_targeted_cell_values_preserved",
        "one_shared_parent_prediction_and_zero_provider_effects",
    )
    false_flags = (
        "contains_question_column_value_prediction_answer_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *counts,
        "candidate_prediction_changed",
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or copied["date_cell_changed_count"]
        + copied["date_cell_rejected_count"]
        > copied["date_cell_examined_count"]
        or copied["scale_cell_changed_count"]
        + copied["scale_cell_rejected_count"]
        > copied["scale_cell_examined_count"]
        or copied["sort_applied_count"]
        + copied["sort_already_satisfied_count"]
        + copied["sort_rejected_count"]
        != copied["sort_attempted_count"]
        or copied["sort_attempted_count"] > 1
        or copied["positive_signed_credit_count"] != 0
        or not isinstance(copied.get("candidate_prediction_changed"), bool)
        or copied["candidate_prediction_changed"]
        is not (
            copied["date_cell_changed_count"] > 0
            or copied["scale_cell_changed_count"] > 0
            or copied["sort_applied_count"] > 0
        )
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.44 projection receipt drifted")
    return copied


def build_projection(
    base_prediction: object, contract: Mapping[str, Any]
) -> dict[str, Any]:
    checked = contract_parent.validate_contract(contract)
    observed = apply_projection(base_prediction, checked)
    receipt = _receipt({**observed, "positive_signed_credit_count": 0})
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "control_prediction": observed["control_prediction"],
        "candidate_prediction": observed["candidate_prediction"],
        "candidate_prediction_changed": observed["candidate_prediction_changed"],
        "constraint_contract_payload_sha256": checked["contract_payload_sha256"],
        "content_free_receipt": receipt,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["artifact_payload_sha256"] = payload_sha256(value)
    return validate_projection(value, contract=checked)


def validate_projection(
    value: Mapping[str, Any], *, contract: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("artifact_payload_sha256", None)
    receipt = copied.get("content_free_receipt")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "control_prediction",
            "candidate_prediction",
            "candidate_prediction_changed",
            "constraint_contract_payload_sha256",
            "content_free_receipt",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "positive_signed_credit_count",
            "benchmark_launch_or_evaluator_authorized",
            "artifact_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(copied.get("control_prediction"), str)
        or not isinstance(copied.get("candidate_prediction"), str)
        or copied.get("candidate_prediction_changed")
        is not (copied["control_prediction"] != copied["candidate_prediction"])
        or not isinstance(copied.get("constraint_contract_payload_sha256"), str)
        or len(copied["constraint_contract_payload_sha256"]) != 64
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt["candidate_prediction_changed"]
        is not copied["candidate_prediction_changed"]
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.44 projection artifact drifted")
    if contract is not None:
        checked = contract_parent.validate_contract(contract)
        expected = apply_projection(copied["control_prediction"], checked)
        if (
            copied["constraint_contract_payload_sha256"]
            != checked["contract_payload_sha256"]
            or copied["candidate_prediction"] != expected["candidate_prediction"]
            or dict(receipt)
            != _receipt({**expected, "positive_signed_credit_count": 0})
        ):
            raise ValueError("V2.55.44 projection/contract binding drifted")
    return copied


def integration_contract() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "parent_contract_policy_id": contract_parent.POLICY_ID,
        "operations": ["complete_date_reformat", "explicit_scale_conversion", "stable_total_sort"],
        "temporal_range_row_filtering": False,
        "rank_slot_row_insertion_deletion_or_relabeling": False,
        "partial_date_precision_invention": False,
        "ambiguous_value_or_mixed_sort_type_mutation": False,
        "schema_or_row_count_mutation": False,
        "additional_model_search_fetch_token_context_wall_or_network_budget": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "benchmark_launch_or_evaluator_authorized": False,
    }


__all__ = [
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "apply_projection",
    "build_projection",
    "integration_contract",
    "validate_projection",
    "validate_receipt",
]
