"""Capability-only total projection for the V2.45.98 title funnel.

The complete V2.45.91 projection is preserved.  This successor adds only
fixed-vocabulary counts attested by the opaque V2.45.99 capability.  It never
emits or replays a task, row, title, query, URL, source, page, value, or
prediction and makes no retrieval, causal, quality, or benchmark claim.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24591_total_validator_aligned_title_query_projection as parent
from . import v24598_content_free_title_funnel as funnel_policy
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24599_proof_carrying_title_funnel import (
    ValidatedProofCarryingContentFreeTitleFunnel,
)


POLICY_ID = "v24600_capability_only_total_content_free_title_funnel_v1"
PREFIX = "content_free_title_funnel_"
FUNNEL_COUNT_NAMES = funnel_policy.COUNT_FIELDS
FUNNEL_COUNT_FIELDS = tuple(f"{PREFIX}{name}" for name in FUNNEL_COUNT_NAMES)
ROW_KEYS = frozenset(
    {
        *parent.ROW_KEYS,
        *FUNNEL_COUNT_FIELDS,
        "content_free_title_funnel_receipt_consumed_validated_capability",
        "content_free_title_funnel_additional_private_effects_known_zero",
        "content_free_title_funnel_private_content_emitted",
        "content_free_title_funnel_privileged_evaluator_content_read",
        "content_free_title_funnel_projection_claims_retrieval_effect_or_causality",
        "content_free_title_funnel_changes_effect_or_credit_surface",
    }
)


def _name(name: str) -> str:
    return f"{PREFIX}{name}"


def _receipt_from_row(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "policy_id": funnel_policy.POLICY_ID,
        "predecessor_policy_id": funnel_policy.selection.POLICY_ID,
        "binding_count": funnel_policy.EXPECTED_BINDING_COUNT,
        **{name: int(value[_name(name)]) for name in FUNNEL_COUNT_NAMES},
        "observed_once_before_source_dedup_ranking_and_budget_cut": True,
        "selection_output_preserved_exactly": True,
        "classification_uses_visible_row_and_search_result_title_only": True,
        "empty_absent_late_type_incompatible_and_strict_stages_separated": True,
        "raw_row_title_query_url_source_page_value_prediction_or_credential_emitted": False,
        "query_search_fetch_ranking_validator_evidence_posterior_entropy_and_credit_changed": False,
        "cache_or_cross_task_state_used": False,
        "bindings_restored": True,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }


def task_projection(
    ordinal: int,
    capability: ValidatedProofCarryingContentFreeTitleFunnel,
) -> dict[str, Any]:
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal < 1
        or not isinstance(capability, ValidatedProofCarryingContentFreeTitleFunnel)
    ):
        raise TypeError("V2.46.00 requires ordinal and title-funnel capability")
    base = parent.task_projection(ordinal, capability.parent_capability())
    receipt = funnel_policy.validate_receipt(
        capability.content_free_title_funnel_receipt()
    )
    value = {
        **base,
        **{_name(name): int(receipt[name]) for name in FUNNEL_COUNT_NAMES},
        "content_free_title_funnel_receipt_consumed_validated_capability": True,
        "content_free_title_funnel_additional_private_effects_known_zero": True,
        "content_free_title_funnel_private_content_emitted": False,
        "content_free_title_funnel_privileged_evaluator_content_read": False,
        "content_free_title_funnel_projection_claims_retrieval_effect_or_causality": False,
        "content_free_title_funnel_changes_effect_or_credit_surface": False,
    }
    return validate_total_row(value)


def _failure_unchecked(ordinal: int) -> dict[str, Any]:
    return {
        **parent._failure_unchecked(ordinal),
        **{name: 0 for name in FUNNEL_COUNT_FIELDS},
        "content_free_title_funnel_receipt_consumed_validated_capability": False,
        "content_free_title_funnel_additional_private_effects_known_zero": False,
        "content_free_title_funnel_private_content_emitted": False,
        "content_free_title_funnel_privileged_evaluator_content_read": False,
        "content_free_title_funnel_projection_claims_retrieval_effect_or_causality": False,
        "content_free_title_funnel_changes_effect_or_credit_surface": False,
    }


def failure_projection(ordinal: int) -> dict[str, Any]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        raise ValueError("V2.46.00 failure ordinal is invalid")
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
            for name in FUNNEL_COUNT_FIELDS
        )
        or funnel_policy.validate_receipt(_receipt_from_row(copied))
        != _receipt_from_row(copied)
        or copied.get(
            "content_free_title_funnel_receipt_consumed_validated_capability"
        )
        is not success
        or copied.get("content_free_title_funnel_additional_private_effects_known_zero")
        is not success
        or copied.get("content_free_title_funnel_private_content_emitted") is not False
        or copied.get("content_free_title_funnel_privileged_evaluator_content_read")
        is not False
        or copied.get(
            "content_free_title_funnel_projection_claims_retrieval_effect_or_causality"
        )
        is not False
        or copied.get("content_free_title_funnel_changes_effect_or_credit_surface")
        is not False
        or not success
        and copied != _failure_unchecked(copied["ordinal"])
    ):
        raise ValueError("V2.46.00 total title-funnel row drifted")
    return copied


TASK_FIELDS = (
    "content_free_title_funnel_activity_tasks",
    "content_free_title_funnel_nonempty_title_tasks",
    "content_free_title_funnel_canonical_row_token_tasks",
    "content_free_title_funnel_alias_surface_anywhere_tasks",
    "content_free_title_funnel_strict_validator_aligned_tasks",
    "content_free_title_funnel_maximum_start_rejection_tasks",
    "content_free_title_funnel_type_compatibility_rejection_tasks",
)
AGGREGATE_KEYS = frozenset(
    {
        *parent.AGGREGATE_KEYS,
        *TASK_FIELDS,
        "total_content_free_title_funnel_count_fields",
        "all_content_free_title_funnel_success_rows_consumed_validated_capabilities",
        "all_content_free_title_funnel_failure_rows_are_content_free_zero_projections",
        "content_free_title_funnel_failure_rows_claim_zero_private_effects",
        "content_free_title_funnel_private_content_emitted",
        "content_free_title_funnel_privileged_evaluator_content_read",
        "content_free_title_funnel_projection_claims_retrieval_effect_or_causality",
        "content_free_title_funnel_changes_effect_or_credit_surface",
        "content_free_title_funnel_aggregate_payload_sha256",
    }
)


def aggregate_projections(
    values: Sequence[
        ValidatedProofCarryingContentFreeTitleFunnel | Mapping[str, Any]
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
        raise ValueError("V2.46.00 aggregate selection drifted")
    rows: list[dict[str, Any]] = []
    parent_inputs: list[Any] = []
    for ordinal, item in enumerate(values, start=1):
        if isinstance(item, ValidatedProofCarryingContentFreeTitleFunnel):
            rows.append(task_projection(ordinal, item))
            parent_inputs.append(item.parent_capability())
        elif isinstance(item, Mapping):
            row = validate_total_row(item)
            if row != _failure_unchecked(ordinal):
                raise ValueError(
                    "V2.46.00 public success row cannot be re-ingested as proof"
                )
            rows.append(row)
            parent_inputs.append(parent.failure_projection(ordinal))
        else:
            raise TypeError("V2.46.00 input is not proof or failure row")
    base = parent.aggregate_projections(parent_inputs, selected=selected)
    successes = [row for row in rows if row["status"] == "validated_capability"]
    failures = [row for row in rows if row["status"] == "failure_as_zero"]
    counts = {
        name: sum(row[_name(name)] for row in successes)
        for name in FUNNEL_COUNT_NAMES
    }
    tasks = {
        "content_free_title_funnel_activity_tasks": sum(
            row[_name("selection_calls")] > 0 for row in successes
        ),
        "content_free_title_funnel_nonempty_title_tasks": sum(
            row[_name("nonempty_title_lead_count")] > 0 for row in successes
        ),
        "content_free_title_funnel_canonical_row_token_tasks": sum(
            row[_name("canonical_row_token_anywhere_title_lead_count")] > 0
            for row in successes
        ),
        "content_free_title_funnel_alias_surface_anywhere_tasks": sum(
            row[_name("alias_surface_anywhere_title_lead_count")] > 0
            for row in successes
        ),
        "content_free_title_funnel_strict_validator_aligned_tasks": sum(
            row[_name("strict_validator_aligned_title_lead_count")] > 0
            for row in successes
        ),
        "content_free_title_funnel_maximum_start_rejection_tasks": sum(
            row[_name("surface_rejected_only_by_maximum_start_lead_count")] > 0
            for row in successes
        ),
        "content_free_title_funnel_type_compatibility_rejection_tasks": sum(
            row[_name("surface_rejected_only_by_type_compatibility_lead_count")]
            > 0
            for row in successes
        ),
    }
    value = {
        **base,
        **tasks,
        "total_content_free_title_funnel_count_fields": counts,
        "all_content_free_title_funnel_success_rows_consumed_validated_capabilities": all(
            row["content_free_title_funnel_receipt_consumed_validated_capability"]
            for row in successes
        ),
        "all_content_free_title_funnel_failure_rows_are_content_free_zero_projections": all(
            row == _failure_unchecked(row["ordinal"]) for row in failures
        ),
        "content_free_title_funnel_failure_rows_claim_zero_private_effects": False,
        "content_free_title_funnel_private_content_emitted": False,
        "content_free_title_funnel_privileged_evaluator_content_read": False,
        "content_free_title_funnel_projection_claims_retrieval_effect_or_causality": False,
        "content_free_title_funnel_changes_effect_or_credit_surface": False,
    }
    value["content_free_title_funnel_aggregate_payload_sha256"] = payload_sha256(
        value
    )
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("content_free_title_funnel_aggregate_payload_sha256", None)
    base = {name: copied[name] for name in parent.AGGREGATE_KEYS if name in copied}
    counts = copied.get("total_content_free_title_funnel_count_fields")
    task_to_count = {
        "content_free_title_funnel_activity_tasks": "selection_calls",
        "content_free_title_funnel_nonempty_title_tasks": "nonempty_title_lead_count",
        "content_free_title_funnel_canonical_row_token_tasks": "canonical_row_token_anywhere_title_lead_count",
        "content_free_title_funnel_alias_surface_anywhere_tasks": "alias_surface_anywhere_title_lead_count",
        "content_free_title_funnel_strict_validator_aligned_tasks": "strict_validator_aligned_title_lead_count",
        "content_free_title_funnel_maximum_start_rejection_tasks": "surface_rejected_only_by_maximum_start_lead_count",
        "content_free_title_funnel_type_compatibility_rejection_tasks": "surface_rejected_only_by_type_compatibility_lead_count",
    }
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
        or set(counts) != set(FUNNEL_COUNT_NAMES)
        or any(
            isinstance(counts.get(name), bool)
            or not isinstance(counts.get(name), int)
            or counts[name] < 0
            for name in FUNNEL_COUNT_NAMES
        )
        or any(
            (counts[count_name] > 0) is not (copied[task_name] > 0)
            for task_name, count_name in task_to_count.items()
        )
        or counts["empty_title_lead_count"] + counts["nonempty_title_lead_count"]
        != counts["visible_input_lead_count"]
        or counts["nonempty_title_without_canonical_row_token_lead_count"]
        + counts["canonical_row_token_anywhere_title_lead_count"]
        != counts["nonempty_title_lead_count"]
        or copied.get(
            "all_content_free_title_funnel_success_rows_consumed_validated_capabilities"
        )
        is not True
        or copied.get(
            "all_content_free_title_funnel_failure_rows_are_content_free_zero_projections"
        )
        is not True
        or copied.get("content_free_title_funnel_failure_rows_claim_zero_private_effects")
        is not False
        or copied.get("content_free_title_funnel_private_content_emitted") is not False
        or copied.get("content_free_title_funnel_privileged_evaluator_content_read")
        is not False
        or copied.get(
            "content_free_title_funnel_projection_claims_retrieval_effect_or_causality"
        )
        is not False
        or copied.get("content_free_title_funnel_changes_effect_or_credit_surface")
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.46.00 total title-funnel aggregate drifted")
    return copied


__all__ = [
    "AGGREGATE_KEYS",
    "FUNNEL_COUNT_FIELDS",
    "FUNNEL_COUNT_NAMES",
    "POLICY_ID",
    "ROW_KEYS",
    "TASK_FIELDS",
    "aggregate_projections",
    "failure_projection",
    "task_projection",
    "validate_aggregate",
    "validate_total_row",
]
