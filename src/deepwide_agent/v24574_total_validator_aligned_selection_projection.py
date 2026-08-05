"""Capability-only total projection for V2.45.73 selection diagnostics.

The projection preserves the complete V2.45.64 strict conversion surface and
adds only content-free counts already attested by a V2.45.73 opaque
capability.  It does not replay task, lead, title, URL, query, page, value, or
selection semantics and does not claim that a replacement caused an
observation, safe change, or decision credit.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24564_strict_reachability_conversion_joint as parent
from . import v24572_validator_aligned_alias_lead_selection as selection
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24573_proof_carrying_validator_aligned_selection import (
    ValidatedProofCarryingValidatorAlignedSelection,
)


POLICY_ID = "v24574_capability_only_total_validator_aligned_selection_v1"
PREFIX = "validator_aligned_selection_"
SELECTION_COUNT_NAMES = selection.COUNT_FIELDS
SELECTION_COUNT_FIELDS = tuple(f"{PREFIX}{name}" for name in SELECTION_COUNT_NAMES)
ROW_KEYS = frozenset(
    {
        *parent.ROW_KEYS,
        *SELECTION_COUNT_FIELDS,
        "validator_aligned_selection_receipt_consumed_validated_capability",
        "validator_aligned_selection_additional_private_effects_known_zero",
        "validator_aligned_selection_private_task_content_emitted",
        "validator_aligned_selection_privileged_evaluator_content_read",
        "validator_aligned_selection_projection_claims_lead_or_effect_causality",
        "validator_aligned_selection_url_alias_hint_received_credit",
    }
)


def _name(name: str) -> str:
    return f"{PREFIX}{name}"


def _receipt_from_row(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "policy_id": selection.POLICY_ID,
        "predecessor_policy_id": selection.surface.POLICY_ID,
        "binding_count": selection.EXPECTED_BINDING_COUNT,
        **{name: int(value[_name(name)]) for name in SELECTION_COUNT_NAMES},
        "source_representative_selected_before_global_budget_cut": True,
        "within_source_selection_prefers_title_surface_validator_alignment": True,
        "within_source_selection_is_input_order_invariant": True,
        "frozen_global_surface_target_coverage_and_source_ranking_preserved": True,
        "logical_queries_search_batches_and_fetch_cap_unchanged": True,
        "url_alias_hint_receives_evidence_source_entropy_or_decision_credit": False,
        "exact_and_alias_title_evidence_validators_unchanged": True,
        "source_posterior_margin_leave_one_out_safe_change_and_decision_credit_rules_unchanged": True,
        "cache_or_cross_task_state_used": False,
        "bindings_restored": True,
        "task_question_opaque_id_query_url_page_content_prediction_value_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }


def task_projection(
    ordinal: int,
    capability: ValidatedProofCarryingValidatorAlignedSelection,
) -> dict[str, Any]:
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal < 1
        or not isinstance(
            capability, ValidatedProofCarryingValidatorAlignedSelection
        )
    ):
        raise TypeError("V2.45.74 requires ordinal and aligned-selection capability")
    base = parent.task_projection(ordinal, capability.parent_capability())
    receipt = selection.validate_receipt(
        capability.validator_aligned_selection_receipt()
    )
    value = {
        **base,
        **{_name(name): int(receipt[name]) for name in SELECTION_COUNT_NAMES},
        "validator_aligned_selection_receipt_consumed_validated_capability": True,
        "validator_aligned_selection_additional_private_effects_known_zero": True,
        "validator_aligned_selection_private_task_content_emitted": False,
        "validator_aligned_selection_privileged_evaluator_content_read": False,
        "validator_aligned_selection_projection_claims_lead_or_effect_causality": False,
        "validator_aligned_selection_url_alias_hint_received_credit": False,
    }
    return validate_total_row(value)


def _failure_unchecked(ordinal: int) -> dict[str, Any]:
    return {
        **parent._failure_unchecked(ordinal),
        **{name: 0 for name in SELECTION_COUNT_FIELDS},
        "validator_aligned_selection_receipt_consumed_validated_capability": False,
        "validator_aligned_selection_additional_private_effects_known_zero": False,
        "validator_aligned_selection_private_task_content_emitted": False,
        "validator_aligned_selection_privileged_evaluator_content_read": False,
        "validator_aligned_selection_projection_claims_lead_or_effect_causality": False,
        "validator_aligned_selection_url_alias_hint_received_credit": False,
    }


def failure_projection(ordinal: int) -> dict[str, Any]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        raise ValueError("V2.45.74 failure ordinal is invalid")
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
            for name in SELECTION_COUNT_FIELDS
        )
        or selection.validate_receipt(_receipt_from_row(copied))
        != _receipt_from_row(copied)
        or copied.get(
            "validator_aligned_selection_receipt_consumed_validated_capability"
        )
        is not success
        or copied.get(
            "validator_aligned_selection_additional_private_effects_known_zero"
        )
        is not success
        or copied.get("validator_aligned_selection_private_task_content_emitted")
        is not False
        or copied.get(
            "validator_aligned_selection_privileged_evaluator_content_read"
        )
        is not False
        or copied.get(
            "validator_aligned_selection_projection_claims_lead_or_effect_causality"
        )
        is not False
        or copied.get("validator_aligned_selection_url_alias_hint_received_credit")
        is not False
        or not success
        and copied != _failure_unchecked(copied["ordinal"])
    ):
        raise ValueError("V2.45.74 total aligned-selection row drifted")
    return copied


TASK_FIELDS = (
    "validator_aligned_selection_activity_tasks",
    "validator_aligned_duplicate_source_tasks",
    "validator_aligned_source_representative_replacement_tasks",
    "validator_aligned_title_replacement_tasks",
    "validator_aligned_url_only_first_representative_avoided_tasks",
    "validator_aligned_excluded_title_alias_hit_tasks",
    "validator_aligned_selected_title_alias_hit_tasks",
)
AGGREGATE_KEYS = frozenset(
    {
        *parent.AGGREGATE_KEYS,
        *TASK_FIELDS,
        "total_validator_aligned_selection_count_fields",
        "all_validator_aligned_selection_success_rows_consumed_validated_capabilities",
        "all_validator_aligned_selection_failure_rows_are_content_free_zero_projections",
        "validator_aligned_selection_failure_rows_claim_zero_private_effects",
        "validator_aligned_selection_private_task_content_emitted",
        "validator_aligned_selection_privileged_evaluator_content_read",
        "validator_aligned_selection_projection_claims_lead_or_effect_causality",
        "validator_aligned_selection_url_alias_hint_received_credit",
        "aggregate_payload_sha256",
    }
)


def aggregate_projections(
    values: Sequence[
        ValidatedProofCarryingValidatorAlignedSelection | Mapping[str, Any]
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
        raise ValueError("V2.45.74 aggregate selection drifted")
    rows: list[dict[str, Any]] = []
    parent_inputs: list[Any] = []
    for ordinal, item in enumerate(values, start=1):
        if isinstance(item, ValidatedProofCarryingValidatorAlignedSelection):
            rows.append(task_projection(ordinal, item))
            parent_inputs.append(item.parent_capability())
        elif isinstance(item, Mapping):
            row = validate_total_row(item)
            if row != _failure_unchecked(ordinal):
                raise ValueError(
                    "V2.45.74 public success row cannot be re-ingested as proof"
                )
            rows.append(row)
            parent_inputs.append(parent.failure_projection(ordinal))
        else:
            raise TypeError("V2.45.74 input is not proof or failure row")
    base = parent.aggregate_projections(parent_inputs, selected=selected)
    successes = [row for row in rows if row["status"] == "validated_capability"]
    failures = [row for row in rows if row["status"] == "failure_as_zero"]
    counts = {
        name: sum(row[_name(name)] for row in successes)
        for name in SELECTION_COUNT_NAMES
    }
    tasks = {
        "validator_aligned_selection_activity_tasks": sum(
            row[_name("selection_calls")] > 0 for row in successes
        ),
        "validator_aligned_duplicate_source_tasks": sum(
            row[_name("duplicate_source_lead_count")] > 0 for row in successes
        ),
        "validator_aligned_source_representative_replacement_tasks": sum(
            row[_name("source_representative_replacement_count")] > 0
            for row in successes
        ),
        "validator_aligned_title_replacement_tasks": sum(
            row[_name("validator_aligned_title_replacement_count")] > 0
            for row in successes
        ),
        "validator_aligned_url_only_first_representative_avoided_tasks": sum(
            row[_name("url_only_first_representative_avoided_count")] > 0
            for row in successes
        ),
        "validator_aligned_excluded_title_alias_hit_tasks": sum(
            row[_name("excluded_title_alias_surface_hit_lead_count")] > 0
            for row in successes
        ),
        "validator_aligned_selected_title_alias_hit_tasks": sum(
            row[_name("selected_title_alias_surface_hit_lead_count")] > 0
            for row in successes
        ),
    }
    value = {
        **base,
        **tasks,
        "total_validator_aligned_selection_count_fields": counts,
        "all_validator_aligned_selection_success_rows_consumed_validated_capabilities": all(
            row[
                "validator_aligned_selection_receipt_consumed_validated_capability"
            ]
            for row in successes
        ),
        "all_validator_aligned_selection_failure_rows_are_content_free_zero_projections": all(
            row == _failure_unchecked(row["ordinal"]) for row in failures
        ),
        "validator_aligned_selection_failure_rows_claim_zero_private_effects": False,
        "validator_aligned_selection_private_task_content_emitted": False,
        "validator_aligned_selection_privileged_evaluator_content_read": False,
        "validator_aligned_selection_projection_claims_lead_or_effect_causality": False,
        "validator_aligned_selection_url_alias_hint_received_credit": False,
    }
    value["aggregate_payload_sha256"] = payload_sha256(value)
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("aggregate_payload_sha256", None)
    base = {
        name: copied[name] for name in parent.AGGREGATE_KEYS if name in copied
    }
    counts = copied.get("total_validator_aligned_selection_count_fields")
    task_to_count = {
        "validator_aligned_selection_activity_tasks": "selection_calls",
        "validator_aligned_duplicate_source_tasks": "duplicate_source_lead_count",
        "validator_aligned_source_representative_replacement_tasks": "source_representative_replacement_count",
        "validator_aligned_title_replacement_tasks": "validator_aligned_title_replacement_count",
        "validator_aligned_url_only_first_representative_avoided_tasks": "url_only_first_representative_avoided_count",
        "validator_aligned_excluded_title_alias_hit_tasks": "excluded_title_alias_surface_hit_lead_count",
        "validator_aligned_selected_title_alias_hit_tasks": "selected_title_alias_surface_hit_lead_count",
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
        or set(counts) != set(SELECTION_COUNT_NAMES)
        or any(
            isinstance(counts.get(name), bool)
            or not isinstance(counts.get(name), int)
            or counts[name] < 0
            for name in SELECTION_COUNT_NAMES
        )
        or any(
            (counts[count_name] > 0) is not (copied[task_name] > 0)
            for task_name, count_name in task_to_count.items()
        )
        or copied.get(
            "all_validator_aligned_selection_success_rows_consumed_validated_capabilities"
        )
        is not True
        or copied.get(
            "all_validator_aligned_selection_failure_rows_are_content_free_zero_projections"
        )
        is not True
        or copied.get(
            "validator_aligned_selection_failure_rows_claim_zero_private_effects"
        )
        is not False
        or copied.get("validator_aligned_selection_private_task_content_emitted")
        is not False
        or copied.get(
            "validator_aligned_selection_privileged_evaluator_content_read"
        )
        is not False
        or copied.get(
            "validator_aligned_selection_projection_claims_lead_or_effect_causality"
        )
        is not False
        or copied.get("validator_aligned_selection_url_alias_hint_received_credit")
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.45.74 total aligned-selection aggregate drifted")
    return copied


__all__ = [
    "AGGREGATE_KEYS",
    "POLICY_ID",
    "ROW_KEYS",
    "SELECTION_COUNT_FIELDS",
    "SELECTION_COUNT_NAMES",
    "TASK_FIELDS",
    "aggregate_projections",
    "failure_projection",
    "task_projection",
    "validate_aggregate",
    "validate_total_row",
]
