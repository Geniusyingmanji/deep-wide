"""Capability-only total projection for V2.45.90 title-query diagnostics.

The complete V2.45.80 projection is preserved.  This successor adds only
counts attested by the opaque V2.45.90 capability and same-task co-occurrence
counts.  It never emits or replays a row, query, title, URL, page, value, or
prediction and makes no causal or quality claim.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24580_total_prededup_preservation_projection as parent
from . import v24589_validator_aligned_title_query as query_policy
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24590_proof_carrying_validator_aligned_title_query import (
    ValidatedProofCarryingValidatorAlignedTitleQuery,
)


POLICY_ID = "v24591_capability_only_total_validator_aligned_title_query_v1"
PREFIX = "validator_aligned_title_query_"
QUERY_COUNT_NAMES = query_policy.COUNT_FIELDS
QUERY_COUNT_FIELDS = tuple(f"{PREFIX}{name}" for name in QUERY_COUNT_NAMES)
ROW_KEYS = frozenset(
    {
        *parent.ROW_KEYS,
        *QUERY_COUNT_FIELDS,
        "validator_aligned_title_query_receipt_consumed_validated_capability",
        "validator_aligned_title_query_additional_private_effects_known_zero",
        "validator_aligned_title_query_private_task_content_emitted",
        "validator_aligned_title_query_privileged_evaluator_content_read",
        "validator_aligned_title_query_projection_claims_retrieval_effect_or_causality",
        "validator_aligned_title_query_hint_received_credit",
        "validator_aligned_title_query_budget_changed",
    }
)


def _name(name: str) -> str:
    return f"{PREFIX}{name}"


def _receipt_from_row(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "policy_id": query_policy.POLICY_ID,
        "predecessor_policy_id": query_policy.acquisition.POLICY_ID,
        "binding_count": query_policy.EXPECTED_BINDING_COUNT,
        **{name: int(value[_name(name)]) for name in QUERY_COUNT_NAMES},
        "exactly_two_logical_queries_per_call": True,
        "first_query_seed_is_frozen_validator_full_surface": True,
        "second_query_seed_is_frozen_validator_core_else_initialism_else_full": True,
        "query_seed_surfaces_are_derived_only_from_visible_row_text": True,
        "column_and_visible_alternative_remain_query_only_inputs": True,
        "logical_query_search_batch_fetch_page_source_and_model_budgets_unchanged": True,
        "title_alias_validator_and_evidence_projection_unchanged": True,
        "query_hint_receives_evidence_source_entropy_epistemic_or_decision_credit": False,
        "source_posterior_margin_leave_one_out_safe_change_and_decision_credit_rules_unchanged": True,
        "cache_or_cross_task_state_used": False,
        "bindings_restored": True,
        "task_question_opaque_id_query_url_title_page_prediction_value_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }


def task_projection(
    ordinal: int,
    capability: ValidatedProofCarryingValidatorAlignedTitleQuery,
) -> dict[str, Any]:
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal < 1
        or not isinstance(
            capability, ValidatedProofCarryingValidatorAlignedTitleQuery
        )
    ):
        raise TypeError("V2.45.91 requires ordinal and title-query capability")
    base = parent.task_projection(ordinal, capability.parent_capability())
    receipt = query_policy.validate_receipt(
        capability.validator_aligned_title_query_receipt()
    )
    value = {
        **base,
        **{_name(name): int(receipt[name]) for name in QUERY_COUNT_NAMES},
        "validator_aligned_title_query_receipt_consumed_validated_capability": True,
        "validator_aligned_title_query_additional_private_effects_known_zero": True,
        "validator_aligned_title_query_private_task_content_emitted": False,
        "validator_aligned_title_query_privileged_evaluator_content_read": False,
        "validator_aligned_title_query_projection_claims_retrieval_effect_or_causality": False,
        "validator_aligned_title_query_hint_received_credit": False,
        "validator_aligned_title_query_budget_changed": False,
    }
    return validate_total_row(value)


def _failure_unchecked(ordinal: int) -> dict[str, Any]:
    return {
        **parent._failure_unchecked(ordinal),
        **{name: 0 for name in QUERY_COUNT_FIELDS},
        "validator_aligned_title_query_receipt_consumed_validated_capability": False,
        "validator_aligned_title_query_additional_private_effects_known_zero": False,
        "validator_aligned_title_query_private_task_content_emitted": False,
        "validator_aligned_title_query_privileged_evaluator_content_read": False,
        "validator_aligned_title_query_projection_claims_retrieval_effect_or_causality": False,
        "validator_aligned_title_query_hint_received_credit": False,
        "validator_aligned_title_query_budget_changed": False,
    }


def failure_projection(ordinal: int) -> dict[str, Any]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        raise ValueError("V2.45.91 failure ordinal is invalid")
    return validate_total_row(_failure_unchecked(ordinal))


def validate_total_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    base = {name: copied[name] for name in parent.ROW_KEYS if name in copied}
    success = copied.get("status") == "validated_capability"
    if (
        set(copied) != ROW_KEYS
        or set(base) != parent.ROW_KEYS
        or parent.validate_total_row(base) != base
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in QUERY_COUNT_FIELDS
        )
        or query_policy.validate_receipt(_receipt_from_row(copied))
        != _receipt_from_row(copied)
        or copied.get(
            "validator_aligned_title_query_receipt_consumed_validated_capability"
        )
        is not success
        or copied.get(
            "validator_aligned_title_query_additional_private_effects_known_zero"
        )
        is not success
        or copied.get("validator_aligned_title_query_private_task_content_emitted")
        is not False
        or copied.get(
            "validator_aligned_title_query_privileged_evaluator_content_read"
        )
        is not False
        or copied.get(
            "validator_aligned_title_query_projection_claims_retrieval_effect_or_causality"
        )
        is not False
        or copied.get("validator_aligned_title_query_hint_received_credit") is not False
        or copied.get("validator_aligned_title_query_budget_changed") is not False
        or not success
        and copied != _failure_unchecked(copied["ordinal"])
    ):
        raise ValueError("V2.45.91 total title-query row drifted")
    return copied


TASK_FIELDS = (
    "validator_aligned_title_query_activity_tasks",
    "validator_aligned_title_query_full_surface_tasks",
    "validator_aligned_title_query_core_surface_tasks",
    "validator_aligned_title_query_initialism_surface_tasks",
    "validator_aligned_title_query_and_title_replacement_cooccurrence_tasks",
)
AGGREGATE_KEYS = frozenset(
    {
        *parent.AGGREGATE_KEYS,
        *TASK_FIELDS,
        "total_validator_aligned_title_query_count_fields",
        "all_validator_aligned_title_query_success_rows_consumed_validated_capabilities",
        "all_validator_aligned_title_query_failure_rows_are_content_free_zero_projections",
        "validator_aligned_title_query_failure_rows_claim_zero_private_effects",
        "validator_aligned_title_query_private_task_content_emitted",
        "validator_aligned_title_query_privileged_evaluator_content_read",
        "validator_aligned_title_query_projection_claims_retrieval_effect_or_causality",
        "validator_aligned_title_query_same_task_cooccurrence_claims_query_or_lead_level_causality",
        "validator_aligned_title_query_hint_received_credit",
        "validator_aligned_title_query_budget_changed",
        "validator_aligned_title_query_aggregate_payload_sha256",
    }
)


def aggregate_projections(
    values: Sequence[
        ValidatedProofCarryingValidatorAlignedTitleQuery | Mapping[str, Any]
    ],
    *,
    selected: int,
) -> dict[str, Any]:
    if (
        isinstance(values, (str, bytes))
        or isinstance(selected, bool)
        or not isinstance(selected, int)
        or selected < 1
        or len(values) != selected
    ):
        raise ValueError("V2.45.91 aggregate selection drifted")
    rows: list[dict[str, Any]] = []
    parent_inputs: list[Any] = []
    for ordinal, item in enumerate(values, start=1):
        if isinstance(item, ValidatedProofCarryingValidatorAlignedTitleQuery):
            rows.append(task_projection(ordinal, item))
            parent_inputs.append(item.parent_capability())
        elif isinstance(item, Mapping):
            row = validate_total_row(item)
            if row != _failure_unchecked(ordinal):
                raise ValueError(
                    "V2.45.91 public success row cannot be re-ingested as proof"
                )
            rows.append(row)
            parent_inputs.append(parent.failure_projection(ordinal))
        else:
            raise TypeError("V2.45.91 input is not proof or failure row")
    base = parent.aggregate_projections(parent_inputs, selected=selected)
    successes = [row for row in rows if row["status"] == "validated_capability"]
    failures = [row for row in rows if row["status"] == "failure_as_zero"]
    counts = {
        name: sum(row[_name(name)] for row in successes)
        for name in QUERY_COUNT_NAMES
    }
    tasks = {
        "validator_aligned_title_query_activity_tasks": sum(
            row[_name("query_vector_calls")] > 0 for row in successes
        ),
        "validator_aligned_title_query_full_surface_tasks": sum(
            row[_name("full_surface_first_query_calls")] > 0 for row in successes
        ),
        "validator_aligned_title_query_core_surface_tasks": sum(
            row[_name("distinctive_core_second_query_calls")] > 0
            for row in successes
        ),
        "validator_aligned_title_query_initialism_surface_tasks": sum(
            row[_name("initialism_second_query_calls")] > 0 for row in successes
        ),
        "validator_aligned_title_query_and_title_replacement_cooccurrence_tasks": sum(
            row[_name("query_vector_calls")] > 0
            and row[
                "validator_aligned_selection_validator_aligned_title_replacement_count"
            ]
            > 0
            for row in successes
        ),
    }
    value = {
        **base,
        **tasks,
        "total_validator_aligned_title_query_count_fields": counts,
        "all_validator_aligned_title_query_success_rows_consumed_validated_capabilities": all(
            row[
                "validator_aligned_title_query_receipt_consumed_validated_capability"
            ]
            for row in successes
        ),
        "all_validator_aligned_title_query_failure_rows_are_content_free_zero_projections": all(
            row == _failure_unchecked(row["ordinal"]) for row in failures
        ),
        "validator_aligned_title_query_failure_rows_claim_zero_private_effects": False,
        "validator_aligned_title_query_private_task_content_emitted": False,
        "validator_aligned_title_query_privileged_evaluator_content_read": False,
        "validator_aligned_title_query_projection_claims_retrieval_effect_or_causality": False,
        "validator_aligned_title_query_same_task_cooccurrence_claims_query_or_lead_level_causality": False,
        "validator_aligned_title_query_hint_received_credit": False,
        "validator_aligned_title_query_budget_changed": False,
    }
    value["validator_aligned_title_query_aggregate_payload_sha256"] = (
        payload_sha256(value)
    )
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop(
        "validator_aligned_title_query_aggregate_payload_sha256", None
    )
    base = {name: copied[name] for name in parent.AGGREGATE_KEYS if name in copied}
    counts = copied.get("total_validator_aligned_title_query_count_fields")
    if (
        set(copied) != AGGREGATE_KEYS
        or set(base) != parent.AGGREGATE_KEYS
        or parent.validate_aggregate(base) != base
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            or copied[name] > copied["success_tasks"]
            for name in TASK_FIELDS
        )
        or not isinstance(counts, Mapping)
        or set(counts) != set(QUERY_COUNT_NAMES)
        or any(
            isinstance(counts.get(name), bool)
            or not isinstance(counts.get(name), int)
            or counts[name] < 0
            for name in QUERY_COUNT_NAMES
        )
        or (counts["query_vector_calls"] > 0)
        is not (copied["validator_aligned_title_query_activity_tasks"] > 0)
        or (counts["full_surface_first_query_calls"] > 0)
        is not (copied["validator_aligned_title_query_full_surface_tasks"] > 0)
        or (counts["distinctive_core_second_query_calls"] > 0)
        is not (copied["validator_aligned_title_query_core_surface_tasks"] > 0)
        or (counts["initialism_second_query_calls"] > 0)
        is not (copied["validator_aligned_title_query_initialism_surface_tasks"] > 0)
        or copied[
            "validator_aligned_title_query_and_title_replacement_cooccurrence_tasks"
        ]
        > copied["validator_aligned_title_query_activity_tasks"]
        or copied[
            "validator_aligned_title_query_and_title_replacement_cooccurrence_tasks"
        ]
        > copied["validator_aligned_title_replacement_tasks"]
        or copied.get(
            "all_validator_aligned_title_query_success_rows_consumed_validated_capabilities"
        )
        is not True
        or copied.get(
            "all_validator_aligned_title_query_failure_rows_are_content_free_zero_projections"
        )
        is not True
        or copied.get(
            "validator_aligned_title_query_failure_rows_claim_zero_private_effects"
        )
        is not False
        or copied.get("validator_aligned_title_query_private_task_content_emitted")
        is not False
        or copied.get(
            "validator_aligned_title_query_privileged_evaluator_content_read"
        )
        is not False
        or copied.get(
            "validator_aligned_title_query_projection_claims_retrieval_effect_or_causality"
        )
        is not False
        or copied.get(
            "validator_aligned_title_query_same_task_cooccurrence_claims_query_or_lead_level_causality"
        )
        is not False
        or copied.get("validator_aligned_title_query_hint_received_credit") is not False
        or copied.get("validator_aligned_title_query_budget_changed") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.45.91 total title-query aggregate drifted")
    return copied


__all__ = [
    "AGGREGATE_KEYS",
    "POLICY_ID",
    "QUERY_COUNT_FIELDS",
    "QUERY_COUNT_NAMES",
    "ROW_KEYS",
    "TASK_FIELDS",
    "aggregate_projections",
    "failure_projection",
    "task_projection",
    "validate_aggregate",
    "validate_total_row",
]
