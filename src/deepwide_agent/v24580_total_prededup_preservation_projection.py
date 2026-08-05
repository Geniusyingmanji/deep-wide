"""Capability-only total projection for V2.45.79 preservation diagnostics.

The complete V2.45.74 validator-aligned projection is preserved and this
successor adds only counts attested by a V2.45.79 opaque capability.  It does
not replay task, lead, title, URL, query, page, value, projection, or selection
semantics.  Same-task preservation/replacement co-occurrence is observable,
but is not reported as lead-level causality or a quality effect.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24574_total_validator_aligned_selection_projection as parent
from . import v24578_prededup_candidate_preservation as preservation
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24579_proof_carrying_prededup_preservation import (
    ValidatedProofCarryingPrededupPreservation,
)


POLICY_ID = "v24580_capability_only_total_prededup_preservation_v1"
PREFIX = "prededup_preservation_"
PRESERVATION_COUNT_NAMES = preservation.COUNT_FIELDS
PRESERVATION_COUNT_FIELDS = tuple(
    f"{PREFIX}{name}" for name in PRESERVATION_COUNT_NAMES
)
ROW_KEYS = frozenset(
    {
        *parent.ROW_KEYS,
        *PRESERVATION_COUNT_FIELDS,
        "prededup_preservation_receipt_consumed_validated_capability",
        "prededup_preservation_additional_private_effects_known_zero",
        "prededup_preservation_private_task_content_emitted",
        "prededup_preservation_privileged_evaluator_content_read",
        "prededup_preservation_projection_claims_candidate_or_effect_causality",
        "prededup_preservation_preserved_url_received_credit",
        "prededup_preservation_query_search_fetch_or_page_budget_changed",
    }
)


def _name(name: str) -> str:
    return f"{PREFIX}{name}"


def _receipt_from_row(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "policy_id": preservation.POLICY_ID,
        "predecessor_policy_id": preservation.source_projection.POLICY_ID,
        "binding_count": preservation.EXPECTED_BINDING_COUNT,
        **{
            name: int(value[_name(name)])
            for name in PRESERVATION_COUNT_NAMES
        },
        "targeted_batch_ordinal": preservation.TARGETED_BATCH_ORDINAL,
        "only_targeted_stage_binding_changed": True,
        "only_valid_exact_url_distinct_visible_leads_preserved": True,
        "predecessor_projection_preserved_for_unique_source_vectors": True,
        "downstream_validator_aligned_source_selection_required": True,
        "logical_queries_search_batches_fetch_cap_and_page_cap_unchanged": True,
        "preserved_url_receives_evidence_source_entropy_epistemic_or_decision_credit": False,
        "cache_or_cross_task_state_used": False,
        "bindings_restored": True,
        "task_question_opaque_id_query_url_page_content_prediction_value_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }


def task_projection(
    ordinal: int,
    capability: ValidatedProofCarryingPrededupPreservation,
) -> dict[str, Any]:
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal < 1
        or not isinstance(
            capability, ValidatedProofCarryingPrededupPreservation
        )
    ):
        raise TypeError("V2.45.80 requires ordinal and pre-dedup capability")
    base = parent.task_projection(ordinal, capability.parent_capability())
    receipt = preservation.validate_receipt(
        capability.prededup_preservation_receipt()
    )
    value = {
        **base,
        **{
            _name(name): int(receipt[name])
            for name in PRESERVATION_COUNT_NAMES
        },
        "prededup_preservation_receipt_consumed_validated_capability": True,
        "prededup_preservation_additional_private_effects_known_zero": True,
        "prededup_preservation_private_task_content_emitted": False,
        "prededup_preservation_privileged_evaluator_content_read": False,
        "prededup_preservation_projection_claims_candidate_or_effect_causality": False,
        "prededup_preservation_preserved_url_received_credit": False,
        "prededup_preservation_query_search_fetch_or_page_budget_changed": False,
    }
    return validate_total_row(value)


def _failure_unchecked(ordinal: int) -> dict[str, Any]:
    return {
        **parent._failure_unchecked(ordinal),
        **{name: 0 for name in PRESERVATION_COUNT_FIELDS},
        "prededup_preservation_receipt_consumed_validated_capability": False,
        "prededup_preservation_additional_private_effects_known_zero": False,
        "prededup_preservation_private_task_content_emitted": False,
        "prededup_preservation_privileged_evaluator_content_read": False,
        "prededup_preservation_projection_claims_candidate_or_effect_causality": False,
        "prededup_preservation_preserved_url_received_credit": False,
        "prededup_preservation_query_search_fetch_or_page_budget_changed": False,
    }


def failure_projection(ordinal: int) -> dict[str, Any]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        raise ValueError("V2.45.80 failure ordinal is invalid")
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
            for name in PRESERVATION_COUNT_FIELDS
        )
        or preservation.validate_receipt(_receipt_from_row(copied))
        != _receipt_from_row(copied)
        or copied.get(
            "prededup_preservation_receipt_consumed_validated_capability"
        )
        is not success
        or copied.get(
            "prededup_preservation_additional_private_effects_known_zero"
        )
        is not success
        or copied.get("prededup_preservation_private_task_content_emitted")
        is not False
        or copied.get(
            "prededup_preservation_privileged_evaluator_content_read"
        )
        is not False
        or copied.get(
            "prededup_preservation_projection_claims_candidate_or_effect_causality"
        )
        is not False
        or copied.get("prededup_preservation_preserved_url_received_credit")
        is not False
        or copied.get(
            "prededup_preservation_query_search_fetch_or_page_budget_changed"
        )
        is not False
        or not success
        and copied != _failure_unchecked(copied["ordinal"])
    ):
        raise ValueError("V2.45.80 total pre-dedup row drifted")
    return copied


TASK_FIELDS = (
    "prededup_preservation_activity_tasks",
    "prededup_preserved_candidate_tasks",
    "prededup_same_source_additional_candidate_tasks",
    "prededup_and_source_replacement_cooccurrence_tasks",
    "prededup_and_title_replacement_cooccurrence_tasks",
)
AGGREGATE_KEYS = frozenset(
    {
        *parent.AGGREGATE_KEYS,
        *TASK_FIELDS,
        "total_prededup_preservation_count_fields",
        "all_prededup_preservation_success_rows_consumed_validated_capabilities",
        "all_prededup_preservation_failure_rows_are_content_free_zero_projections",
        "prededup_preservation_failure_rows_claim_zero_private_effects",
        "prededup_preservation_private_task_content_emitted",
        "prededup_preservation_privileged_evaluator_content_read",
        "prededup_preservation_projection_claims_candidate_or_effect_causality",
        "prededup_preservation_same_task_cooccurrence_claims_lead_level_causality",
        "prededup_preservation_preserved_url_received_credit",
        "prededup_preservation_query_search_fetch_or_page_budget_changed",
        "prededup_aggregate_payload_sha256",
    }
)


def aggregate_projections(
    values: Sequence[
        ValidatedProofCarryingPrededupPreservation | Mapping[str, Any]
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
        raise ValueError("V2.45.80 aggregate selection drifted")
    rows: list[dict[str, Any]] = []
    parent_inputs: list[Any] = []
    for ordinal, item in enumerate(values, start=1):
        if isinstance(item, ValidatedProofCarryingPrededupPreservation):
            rows.append(task_projection(ordinal, item))
            parent_inputs.append(item.parent_capability())
        elif isinstance(item, Mapping):
            row = validate_total_row(item)
            if row != _failure_unchecked(ordinal):
                raise ValueError(
                    "V2.45.80 public success row cannot be re-ingested as proof"
                )
            rows.append(row)
            parent_inputs.append(parent.failure_projection(ordinal))
        else:
            raise TypeError("V2.45.80 input is not proof or failure row")
    base = parent.aggregate_projections(parent_inputs, selected=selected)
    successes = [row for row in rows if row["status"] == "validated_capability"]
    failures = [row for row in rows if row["status"] == "failure_as_zero"]
    counts = {
        name: sum(row[_name(name)] for row in successes)
        for name in PRESERVATION_COUNT_NAMES
    }
    tasks = {
        "prededup_preservation_activity_tasks": sum(
            row[_name("projection_calls")] > 0 for row in successes
        ),
        "prededup_preserved_candidate_tasks": sum(
            row[_name("preserved_candidate_count")] > 0 for row in successes
        ),
        "prededup_same_source_additional_candidate_tasks": sum(
            row[_name("same_source_additional_candidate_count")] > 0
            for row in successes
        ),
        "prededup_and_source_replacement_cooccurrence_tasks": sum(
            row[_name("preserved_candidate_count")] > 0
            and row[
                "validator_aligned_selection_source_representative_replacement_count"
            ]
            > 0
            for row in successes
        ),
        "prededup_and_title_replacement_cooccurrence_tasks": sum(
            row[_name("preserved_candidate_count")] > 0
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
        "total_prededup_preservation_count_fields": counts,
        "all_prededup_preservation_success_rows_consumed_validated_capabilities": all(
            row[
                "prededup_preservation_receipt_consumed_validated_capability"
            ]
            for row in successes
        ),
        "all_prededup_preservation_failure_rows_are_content_free_zero_projections": all(
            row == _failure_unchecked(row["ordinal"]) for row in failures
        ),
        "prededup_preservation_failure_rows_claim_zero_private_effects": False,
        "prededup_preservation_private_task_content_emitted": False,
        "prededup_preservation_privileged_evaluator_content_read": False,
        "prededup_preservation_projection_claims_candidate_or_effect_causality": False,
        "prededup_preservation_same_task_cooccurrence_claims_lead_level_causality": False,
        "prededup_preservation_preserved_url_received_credit": False,
        "prededup_preservation_query_search_fetch_or_page_budget_changed": False,
    }
    value["prededup_aggregate_payload_sha256"] = payload_sha256(value)
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("prededup_aggregate_payload_sha256", None)
    base = {
        name: copied[name] for name in parent.AGGREGATE_KEYS if name in copied
    }
    counts = copied.get("total_prededup_preservation_count_fields")
    task_to_count = {
        "prededup_preservation_activity_tasks": "projection_calls",
        "prededup_preserved_candidate_tasks": "preserved_candidate_count",
        "prededup_same_source_additional_candidate_tasks": "same_source_additional_candidate_count",
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
        or set(counts) != set(PRESERVATION_COUNT_NAMES)
        or any(
            isinstance(counts.get(name), bool)
            or not isinstance(counts.get(name), int)
            or counts[name] < 0
            for name in PRESERVATION_COUNT_NAMES
        )
        or any(
            (counts[count_name] > 0) is not (copied[task_name] > 0)
            for task_name, count_name in task_to_count.items()
        )
        or copied["prededup_and_source_replacement_cooccurrence_tasks"]
        > copied["prededup_preserved_candidate_tasks"]
        or copied["prededup_and_source_replacement_cooccurrence_tasks"]
        > copied["validator_aligned_source_representative_replacement_tasks"]
        or copied["prededup_and_title_replacement_cooccurrence_tasks"]
        > copied["prededup_and_source_replacement_cooccurrence_tasks"]
        or copied["prededup_and_title_replacement_cooccurrence_tasks"]
        > copied["validator_aligned_title_replacement_tasks"]
        or copied.get(
            "all_prededup_preservation_success_rows_consumed_validated_capabilities"
        )
        is not True
        or copied.get(
            "all_prededup_preservation_failure_rows_are_content_free_zero_projections"
        )
        is not True
        or copied.get(
            "prededup_preservation_failure_rows_claim_zero_private_effects"
        )
        is not False
        or copied.get("prededup_preservation_private_task_content_emitted")
        is not False
        or copied.get(
            "prededup_preservation_privileged_evaluator_content_read"
        )
        is not False
        or copied.get(
            "prededup_preservation_projection_claims_candidate_or_effect_causality"
        )
        is not False
        or copied.get(
            "prededup_preservation_same_task_cooccurrence_claims_lead_level_causality"
        )
        is not False
        or copied.get("prededup_preservation_preserved_url_received_credit")
        is not False
        or copied.get(
            "prededup_preservation_query_search_fetch_or_page_budget_changed"
        )
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.45.80 total pre-dedup aggregate drifted")
    return copied


__all__ = [
    "AGGREGATE_KEYS",
    "POLICY_ID",
    "PRESERVATION_COUNT_FIELDS",
    "PRESERVATION_COUNT_NAMES",
    "ROW_KEYS",
    "TASK_FIELDS",
    "aggregate_projections",
    "failure_projection",
    "task_projection",
    "validate_aggregate",
    "validate_total_row",
]
