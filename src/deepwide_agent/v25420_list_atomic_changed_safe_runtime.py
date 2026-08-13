"""List-atomic guard over one V2.53.75 shared-base changed-safe forward.

V2.54.19 found that the deterministic V2.53.69 editor changed fourteen
coordinates on the frozen RFC mechanism population: eleven correct Authors
cells became incorrect when a scalar quote value removed list separators and
mixed organization text into the author sequence; the other three edits were
truth-neutral.  This successor does not route to a different runtime and does
not create a second sampling effect.  It calls V2.53.75 exactly once, obtains
the shared base and changed-safe candidate already present in that result, and
applies a pure local guard:

* only columns whose visible name has explicit list semantics are considered;
* only coordinates changed by the frozen editor are considered;
* a candidate list value must retain at least the base list cardinality; and
* a rejected coordinate reuses the exact base cell while every other candidate
  coordinate is preserved.

The guard has no filesystem, environment, process, network, model, search,
fetch, evaluator, benchmark-label, mapping, gold, score, reward, credential,
or historical-result capability.  Runtime inputs remain visible
``opaque_id``/``question`` plus injected same-forward clients.  Entropy and
information gain remain shadow-only and assign no signed credit.
"""

from __future__ import annotations

import copy
import hashlib
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import v24257_score_first_runtime as score
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25369_changed_safe_verified_coordinate_edit as editor
from . import v25375_schema_total_changed_safe_runtime as parent
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25420_list_atomic_changed_safe_runtime_v1"
ROLE = "v25420_list_atomic_changed_safe_runtime_result"
RECEIPT_ROLE = "v25420_content_free_list_atomic_guard_receipt"
STAGE_RECEIPT_ROLE = "v25420_content_free_list_atomic_stage_receipt"
PHASES = parent.PHASES

LIST_COLUMN_KEYS = frozenset(
    {
        "author",
        "authors",
        "contributor",
        "contributors",
        "member",
        "members",
        "participant",
        "participants",
        "owner",
        "owners",
        "creator",
        "creators",
    }
)
LIST_SEPARATOR = re.compile(r"\s*(?:;|,|\band\b|&)\s*", re.I)


class ProductionOnlyStageError(RuntimeError):
    """Finite content-free outer failure for the list-atomic wrapper."""

    def __init__(self, receipt: Mapping[str, Any]) -> None:
        self.stage_receipt = validate_stage_receipt(receipt)
        super().__init__("V2.54.20 list-atomic changed-safe stage failed")


def _column_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def _list_cardinality(value: object) -> int:
    text = " ".join(str(value or "").split())
    if not text:
        return 0
    return len([part for part in LIST_SEPARATOR.split(text) if part])


def _matrix(prediction: str, columns: Sequence[str]) -> list[list[str]]:
    canonical, _errors = score.extract_valid_markdown_table(prediction, columns)
    if canonical is None or canonical != prediction:
        raise ValueError("V2.54.20 expected exact canonical table")
    lines = [
        line.strip()
        for line in canonical.splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    matrix = [score._split_table_row(line) for line in lines]
    if (
        len(matrix) < 3
        or matrix[0] != list(columns)
        or any(len(row) != len(columns) for row in matrix)
    ):
        raise ValueError("V2.54.20 canonical matrix drifted")
    return matrix


def _visible_columns(prediction: str) -> tuple[str, ...]:
    lines = [
        line.strip()
        for line in str(prediction).splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    if not lines:
        raise ValueError("V2.54.20 visible table header is absent")
    columns = tuple(score._split_table_row(lines[0]))
    _matrix(str(prediction), columns)
    return columns


def apply_list_atomic_guard(
    base_prediction: str,
    candidate_prediction: str,
    columns: Sequence[str],
) -> dict[str, Any]:
    """Roll back only changed list coordinates whose cardinality decreases."""

    required = tuple(str(column).strip() for column in columns)
    if (
        len(required) < 2
        or any(not column for column in required)
        or len({_column_key(column) for column in required}) != len(required)
    ):
        raise ValueError("V2.54.20 visible column vector drifted")
    base = _matrix(str(base_prediction), required)
    candidate = _matrix(str(candidate_prediction), required)
    if (
        len(base) != len(candidate)
        or [row[0] for row in base[2:]] != [row[0] for row in candidate[2:]]
    ):
        raise ValueError("V2.54.20 shared table shape or identity drifted")
    rows = copy.deepcopy(candidate[2:])
    changed = retained = rejected = list_changed = 0
    by_column: dict[str, dict[str, int]] = {}
    for row_index, (left, right) in enumerate(
        zip(base[2:], candidate[2:], strict=True)
    ):
        for column_index, column in enumerate(required[1:], 1):
            if left[column_index] == right[column_index]:
                continue
            changed += 1
            key = _column_key(column)
            disposition = by_column.setdefault(
                column, {"changed": 0, "list_changed": 0, "retained": 0, "rejected": 0}
            )
            disposition["changed"] += 1
            if key not in LIST_COLUMN_KEYS:
                retained += 1
                disposition["retained"] += 1
                continue
            list_changed += 1
            disposition["list_changed"] += 1
            base_count = _list_cardinality(left[column_index])
            candidate_count = _list_cardinality(right[column_index])
            if base_count >= 2 and candidate_count < base_count:
                rows[row_index][column_index] = left[column_index]
                rejected += 1
                disposition["rejected"] += 1
            else:
                retained += 1
                disposition["retained"] += 1
    guarded = editor._render(required, rows)
    reparsed = _matrix(guarded, required)
    if (
        [row[0] for row in reparsed[2:]] != [row[0] for row in base[2:]]
        or changed != retained + rejected
        or list_changed < rejected
    ):
        raise RuntimeError("V2.54.20 guarded table preservation drifted")
    return {
        "prediction": guarded,
        "changed_coordinate_count": changed,
        "list_semantic_changed_coordinate_count": list_changed,
        "retained_candidate_coordinate_count": retained,
        "rejected_list_cardinality_decrease_count": rejected,
        "guard_changed_candidate": guarded != str(candidate_prediction),
        "guarded_prediction_equals_base": guarded == str(base_prediction),
        "by_column": by_column,
    }


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    by_column = copy.deepcopy(dict(value["by_column"]))
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "changed_coordinate_count": int(value["changed_coordinate_count"]),
        "list_semantic_changed_coordinate_count": int(
            value["list_semantic_changed_coordinate_count"]
        ),
        "retained_candidate_coordinate_count": int(
            value["retained_candidate_coordinate_count"]
        ),
        "rejected_list_cardinality_decrease_count": int(
            value["rejected_list_cardinality_decrease_count"]
        ),
        "guard_changed_candidate": bool(value["guard_changed_candidate"]),
        "guarded_prediction_equals_base": bool(value["guarded_prediction_equals_base"]),
        "column_disposition_counts": by_column,
        "visible_list_column_names_only": True,
        "candidate_list_cardinality_must_not_decrease": True,
        "only_rejected_coordinates_reuse_exact_base_cells": True,
        "other_candidate_cells_schema_rows_order_and_keys_preserved": True,
        "one_parent_forward_and_zero_additional_provider_effects": True,
        "shared_base_and_candidate_have_identical_sampling_effects": True,
        "contains_question_query_url_page_quote_identity_field_value_prediction_answer_hash_opaque_id_or_credential": False,
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
        "changed_coordinate_count",
        "list_semantic_changed_coordinate_count",
        "retained_candidate_coordinate_count",
        "rejected_list_cardinality_decrease_count",
    )
    true_flags = (
        "visible_list_column_names_only",
        "candidate_list_cardinality_must_not_decrease",
        "only_rejected_coordinates_reuse_exact_base_cells",
        "other_candidate_cells_schema_rows_order_and_keys_preserved",
        "one_parent_forward_and_zero_additional_provider_effects",
        "shared_base_and_candidate_have_identical_sampling_effects",
    )
    false_flags = (
        "contains_question_query_url_page_quote_identity_field_value_prediction_answer_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *counts,
        "guard_changed_candidate",
        "guarded_prediction_equals_base",
        "column_disposition_counts",
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    by_column = copied.get("column_disposition_counts")
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
        or copied["changed_coordinate_count"]
        != copied["retained_candidate_coordinate_count"]
        + copied["rejected_list_cardinality_decrease_count"]
        or copied["list_semantic_changed_coordinate_count"]
        < copied["rejected_list_cardinality_decrease_count"]
        or copied.get("guard_changed_candidate")
        is not (copied["rejected_list_cardinality_decrease_count"] > 0)
        or not isinstance(copied.get("guarded_prediction_equals_base"), bool)
        or not isinstance(by_column, Mapping)
        or any(
            not isinstance(name, str)
            or set(item) != {"changed", "list_changed", "retained", "rejected"}
            or any(
                isinstance(number, bool) or not isinstance(number, int) or number < 0
                for number in item.values()
            )
            or item["changed"] != item["retained"] + item["rejected"]
            or item["list_changed"] < item["rejected"]
            for name, item in by_column.items()
        )
        or sum(item["changed"] for item in by_column.values())
        != copied["changed_coordinate_count"]
        or sum(item["list_changed"] for item in by_column.values())
        != copied["list_semantic_changed_coordinate_count"]
        or sum(item["retained"] for item in by_column.values())
        != copied["retained_candidate_coordinate_count"]
        or sum(item["rejected"] for item in by_column.values())
        != copied["rejected_list_cardinality_decrease_count"]
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.20 list-atomic guard receipt drifted")
    return copied


def _wrap_result(parent_result: Mapping[str, Any]) -> dict[str, Any]:
    checked = parent.validate_result(parent_result)
    raw_parent = parent.parent.validate_result(checked["private_parent_result"])
    base = raw_parent["predictions"][parent.CONTROL_ARM]
    candidate = raw_parent["predictions"][parent.CANDIDATE_ARM]
    observed = apply_list_atomic_guard(
        base, candidate, _visible_columns(base)
    )
    prediction = str(observed["prediction"])
    receipt = _receipt(observed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": checked["opaque_id"],
        "status": "terminal",
        "prediction": prediction,
        "prediction_sha256": hashlib.sha256(prediction.encode()).hexdigest(),
        "prediction_kind": checked["prediction_kind"],
        "base_prediction_sha256": hashlib.sha256(base.encode()).hexdigest(),
        "raw_candidate_prediction_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        "raw_candidate_changed": base != candidate,
        "guarded_prediction_changed_from_base": base != prediction,
        "list_atomic_guard_receipt": copy.deepcopy(receipt),
        "private_parent_result": copy.deepcopy(checked),
        "private_parent_result_payload_sha256": checked["result_payload_sha256"],
        "cost": copy.deepcopy(checked["cost"]),
        "scored_prediction_is_shared_effect_list_atomic_candidate": True,
        "raw_candidate_and_base_retained_only_in_private_parent_result": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return value


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    raw = copied.get("private_parent_result")
    receipt = copied.get("list_atomic_guard_receipt")
    if not isinstance(raw, Mapping) or not isinstance(receipt, Mapping):
        raise ValueError("V2.54.20 private parent or guard receipt is absent")
    expected = _wrap_result(raw)
    if copied != expected:
        raise ValueError("V2.54.20 result adapter drifted")
    return copied


def _stage_receipt(
    result: Mapping[str, Any], parent_stage: Mapping[str, Any]
) -> dict[str, Any]:
    checked = validate_result(result)
    stage = parent.validate_stage_receipt(parent_stage)
    receipt = validate_receipt(checked["list_atomic_guard_receipt"])
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "failure_present": False,
        "failure_stage": None,
        "failure_type": None,
        "list_atomic_guard_receipt": copy.deepcopy(receipt),
        "parent_stage_receipt": copy.deepcopy(stage),
        "parent_runtime_result_payload_sha256": checked[
            "private_parent_result_payload_sha256"
        ],
        "runtime_result_payload_sha256": checked["result_payload_sha256"],
        "outer_physical_budget_receipt": copy.deepcopy(
            stage["outer_physical_budget_receipt"]
        ),
        "one_parent_forward_and_pure_local_guard": True,
        "query_fetch_model_token_context_and_wall_caps_unchanged": True,
        "contains_question_column_query_url_page_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_stage_receipt(value)


def validate_stage_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    receipt = copied.get("list_atomic_guard_receipt")
    stage = copied.get("parent_stage_receipt")
    budget = copied.get("outer_physical_budget_receipt")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "failure_present",
        "failure_stage",
        "failure_type",
        "list_atomic_guard_receipt",
        "parent_stage_receipt",
        "parent_runtime_result_payload_sha256",
        "runtime_result_payload_sha256",
        "outer_physical_budget_receipt",
        "one_parent_forward_and_pure_local_guard",
        "query_fetch_model_token_context_and_wall_caps_unchanged",
        "contains_question_column_query_url_page_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != STAGE_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("failure_present") is not False
        or copied.get("failure_stage") is not None
        or copied.get("failure_type") is not None
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or not isinstance(stage, Mapping)
        or parent.validate_stage_receipt(stage) != dict(stage)
        or not isinstance(budget, Mapping)
        or cap.validate_budget_receipt(budget) != dict(budget)
        or stage["outer_physical_budget_receipt"] != budget
        or not isinstance(copied.get("parent_runtime_result_payload_sha256"), str)
        or len(copied["parent_runtime_result_payload_sha256"]) != 64
        or not isinstance(copied.get("runtime_result_payload_sha256"), str)
        or len(copied["runtime_result_payload_sha256"]) != 64
        or copied.get("one_parent_forward_and_pure_local_guard") is not True
        or copied.get("query_fetch_model_token_context_and_wall_caps_unchanged")
        is not True
        or any(
            copied.get(name) is not False
            for name in (
                "contains_question_column_query_url_page_prediction_answer_opaque_id_or_credential",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.20 stage receipt drifted")
    return copied


def run_task(
    task: Mapping[str, Any],
    *,
    model: cap.HardCappedModelLimiter,
    searches: Mapping[str, cap.HardCappedSearchClient],
    limits: score.ScoreFirstLimits,
    budget: cap.PhysicalEffectBudget,
    monotonic: Callable[[], float],
) -> tuple[dict[str, Any], dict[str, Any]]:
    visible = score.validate_visible_task(task)
    parent_result, parent_stage = parent.run_task(
        visible,
        model=model,
        searches=searches,
        limits=limits,
        budget=budget,
        monotonic=monotonic,
    )
    checked = parent.validate_result(parent_result)
    result = _wrap_result(checked)
    return validate_result(result), _stage_receipt(result, parent_stage)


__all__ = [
    "LIST_COLUMN_KEYS",
    "PHASES",
    "POLICY_ID",
    "ProductionOnlyStageError",
    "RECEIPT_ROLE",
    "ROLE",
    "STAGE_RECEIPT_ROLE",
    "apply_list_atomic_guard",
    "run_task",
    "validate_receipt",
    "validate_result",
    "validate_stage_receipt",
]
