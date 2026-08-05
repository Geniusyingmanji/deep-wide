"""Capability-only total projection for V2.46.07 title provenance.

The full V2.46.00 projection is retained.  This successor adds only fixed
counts attested by an opaque V2.46.07 capability.  It never emits or replays a
task, query, URL, title, page, value, prediction, or provider payload.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24600_total_title_funnel_projection as parent
from . import v24606_content_free_title_provenance as provenance_policy
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24607_proof_carrying_title_provenance import (
    ValidatedProofCarryingContentFreeTitleProvenance,
)


POLICY_ID = "v24608_capability_only_total_title_provenance_v1"
PREFIX = "content_free_title_provenance_"
PROVENANCE_COUNT_NAMES = provenance_policy.COUNT_FIELDS
PROVENANCE_COUNT_FIELDS = tuple(
    f"{PREFIX}{name}" for name in PROVENANCE_COUNT_NAMES
)
ROW_KEYS = frozenset(
    {
        *parent.ROW_KEYS,
        *PROVENANCE_COUNT_FIELDS,
        "content_free_title_provenance_receipt_consumed_validated_capability",
        "content_free_title_provenance_additional_private_effects_known_zero",
        "content_free_title_provenance_private_content_emitted",
        "content_free_title_provenance_privileged_evaluator_content_read",
        "content_free_title_provenance_projection_claims_provider_or_transport_causality",
        "content_free_title_provenance_changes_effect_or_credit_surface",
    }
)


def _name(name: str) -> str:
    return f"{PREFIX}{name}"


def _receipt_from_row(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "policy_id": provenance_policy.POLICY_ID,
        "binding_count": provenance_policy.EXPECTED_BINDING_COUNT,
        **{name: int(value[_name(name)]) for name in PROVENANCE_COUNT_NAMES},
        "provider_payload_and_fetch_batches_returned_exactly": True,
        "successful_provider_payload_observed_once_after_frozen_request": True,
        "fetch_input_observed_before_and_output_after_frozen_fetch_urls": True,
        "same_url_alignment_uses_canonical_url_in_memory_only": True,
        "raw_task_question_query_url_title_page_prediction_or_credential_emitted": False,
        "query_search_fetch_model_process_or_evaluator_effect_added": False,
        "ranking_validator_evidence_posterior_entropy_or_credit_changed": False,
        "cache_or_cross_task_state_used": False,
        "bindings_restored": True,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }


def task_projection(
    ordinal: int,
    capability: ValidatedProofCarryingContentFreeTitleProvenance,
) -> dict[str, Any]:
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal < 1
        or not isinstance(
            capability, ValidatedProofCarryingContentFreeTitleProvenance
        )
    ):
        raise TypeError("V2.46.08 requires ordinal and provenance capability")
    base = parent.task_projection(ordinal, capability.parent_capability())
    receipt = provenance_policy.validate_receipt(
        capability.content_free_title_provenance_receipt()
    )
    value = {
        **base,
        **{_name(name): int(receipt[name]) for name in PROVENANCE_COUNT_NAMES},
        "content_free_title_provenance_receipt_consumed_validated_capability": True,
        "content_free_title_provenance_additional_private_effects_known_zero": True,
        "content_free_title_provenance_private_content_emitted": False,
        "content_free_title_provenance_privileged_evaluator_content_read": False,
        "content_free_title_provenance_projection_claims_provider_or_transport_causality": False,
        "content_free_title_provenance_changes_effect_or_credit_surface": False,
    }
    return validate_total_row(value)


def _failure_unchecked(ordinal: int) -> dict[str, Any]:
    return {
        **parent._failure_unchecked(ordinal),
        **{name: 0 for name in PROVENANCE_COUNT_FIELDS},
        "content_free_title_provenance_receipt_consumed_validated_capability": False,
        "content_free_title_provenance_additional_private_effects_known_zero": False,
        "content_free_title_provenance_private_content_emitted": False,
        "content_free_title_provenance_privileged_evaluator_content_read": False,
        "content_free_title_provenance_projection_claims_provider_or_transport_causality": False,
        "content_free_title_provenance_changes_effect_or_credit_surface": False,
    }


def failure_projection(ordinal: int) -> dict[str, Any]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        raise ValueError("V2.46.08 failure ordinal is invalid")
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
            for name in PROVENANCE_COUNT_FIELDS
        )
        or provenance_policy.validate_receipt(_receipt_from_row(copied))
        != _receipt_from_row(copied)
        or copied.get(
            "content_free_title_provenance_receipt_consumed_validated_capability"
        )
        is not success
        or copied.get(
            "content_free_title_provenance_additional_private_effects_known_zero"
        )
        is not success
        or copied.get("content_free_title_provenance_private_content_emitted")
        is not False
        or copied.get(
            "content_free_title_provenance_privileged_evaluator_content_read"
        )
        is not False
        or copied.get(
            "content_free_title_provenance_projection_claims_provider_or_transport_causality"
        )
        is not False
        or copied.get("content_free_title_provenance_changes_effect_or_credit_surface")
        is not False
        or not success
        and copied != _failure_unchecked(copied["ordinal"])
    ):
        raise ValueError("V2.46.08 total title-provenance row drifted")
    return copied


TASK_FIELDS = (
    "content_free_title_provenance_provider_activity_tasks",
    "content_free_title_provenance_action_nonempty_title_tasks",
    "content_free_title_provenance_citation_nonempty_title_tasks",
    "content_free_title_provenance_action_empty_citation_nonempty_tasks",
    "content_free_title_provenance_fetch_activity_tasks",
    "content_free_title_provenance_fetch_request_nonempty_title_tasks",
    "content_free_title_provenance_fetched_result_nonempty_title_tasks",
    "content_free_title_provenance_empty_request_page_title_recovery_tasks",
)
AGGREGATE_KEYS = frozenset(
    {
        *parent.AGGREGATE_KEYS,
        *TASK_FIELDS,
        "total_content_free_title_provenance_count_fields",
        "all_content_free_title_provenance_success_rows_consumed_validated_capabilities",
        "all_content_free_title_provenance_failure_rows_are_content_free_zero_projections",
        "content_free_title_provenance_failure_rows_claim_zero_private_effects",
        "content_free_title_provenance_private_content_emitted",
        "content_free_title_provenance_privileged_evaluator_content_read",
        "content_free_title_provenance_projection_claims_provider_or_transport_causality",
        "content_free_title_provenance_changes_effect_or_credit_surface",
        "content_free_title_provenance_aggregate_payload_sha256",
    }
)


def aggregate_projections(
    values: Sequence[
        ValidatedProofCarryingContentFreeTitleProvenance | Mapping[str, Any]
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
        raise ValueError("V2.46.08 aggregate selection drifted")
    rows: list[dict[str, Any]] = []
    parent_inputs: list[Any] = []
    for ordinal, item in enumerate(values, start=1):
        if isinstance(item, ValidatedProofCarryingContentFreeTitleProvenance):
            rows.append(task_projection(ordinal, item))
            parent_inputs.append(item.parent_capability())
        elif isinstance(item, Mapping):
            row = validate_total_row(item)
            if row != _failure_unchecked(ordinal):
                raise ValueError(
                    "V2.46.08 public success row cannot be re-ingested as proof"
                )
            rows.append(row)
            parent_inputs.append(parent.failure_projection(ordinal))
        else:
            raise TypeError("V2.46.08 input is not proof or failure row")
    base = parent.aggregate_projections(parent_inputs, selected=selected)
    successes = [row for row in rows if row["status"] == "validated_capability"]
    failures = [row for row in rows if row["status"] == "failure_as_zero"]
    counts = {
        name: sum(row[_name(name)] for row in successes)
        for name in PROVENANCE_COUNT_NAMES
    }
    task_to_count = {
        "content_free_title_provenance_provider_activity_tasks": "provider_response_count",
        "content_free_title_provenance_action_nonempty_title_tasks": "action_source_nonempty_title_count",
        "content_free_title_provenance_citation_nonempty_title_tasks": "query_local_citation_nonempty_title_count",
        "content_free_title_provenance_action_empty_citation_nonempty_tasks": "same_url_action_empty_citation_nonempty_count",
        "content_free_title_provenance_fetch_activity_tasks": "fetch_urls_call_count",
        "content_free_title_provenance_fetch_request_nonempty_title_tasks": "fetch_request_nonempty_title_count",
        "content_free_title_provenance_fetched_result_nonempty_title_tasks": "fetched_result_nonempty_title_count",
        "content_free_title_provenance_empty_request_page_title_recovery_tasks": "empty_fetch_request_to_nonempty_result_title_count",
    }
    tasks = {
        task_name: sum(row[_name(count_name)] > 0 for row in successes)
        for task_name, count_name in task_to_count.items()
    }
    value = {
        **base,
        **tasks,
        "total_content_free_title_provenance_count_fields": counts,
        "all_content_free_title_provenance_success_rows_consumed_validated_capabilities": all(
            row[
                "content_free_title_provenance_receipt_consumed_validated_capability"
            ]
            for row in successes
        ),
        "all_content_free_title_provenance_failure_rows_are_content_free_zero_projections": all(
            row == _failure_unchecked(row["ordinal"]) for row in failures
        ),
        "content_free_title_provenance_failure_rows_claim_zero_private_effects": False,
        "content_free_title_provenance_private_content_emitted": False,
        "content_free_title_provenance_privileged_evaluator_content_read": False,
        "content_free_title_provenance_projection_claims_provider_or_transport_causality": False,
        "content_free_title_provenance_changes_effect_or_credit_surface": False,
    }
    value["content_free_title_provenance_aggregate_payload_sha256"] = payload_sha256(
        value
    )
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("content_free_title_provenance_aggregate_payload_sha256", None)
    base = {name: copied[name] for name in parent.AGGREGATE_KEYS if name in copied}
    counts = copied.get("total_content_free_title_provenance_count_fields")
    task_to_count = {
        "content_free_title_provenance_provider_activity_tasks": "provider_response_count",
        "content_free_title_provenance_action_nonempty_title_tasks": "action_source_nonempty_title_count",
        "content_free_title_provenance_citation_nonempty_title_tasks": "query_local_citation_nonempty_title_count",
        "content_free_title_provenance_action_empty_citation_nonempty_tasks": "same_url_action_empty_citation_nonempty_count",
        "content_free_title_provenance_fetch_activity_tasks": "fetch_urls_call_count",
        "content_free_title_provenance_fetch_request_nonempty_title_tasks": "fetch_request_nonempty_title_count",
        "content_free_title_provenance_fetched_result_nonempty_title_tasks": "fetched_result_nonempty_title_count",
        "content_free_title_provenance_empty_request_page_title_recovery_tasks": "empty_fetch_request_to_nonempty_result_title_count",
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
        or set(counts) != set(PROVENANCE_COUNT_NAMES)
        or provenance_policy.validate_receipt(
            {
                "policy_id": provenance_policy.POLICY_ID,
                "binding_count": provenance_policy.EXPECTED_BINDING_COUNT,
                **dict(counts),
                "provider_payload_and_fetch_batches_returned_exactly": True,
                "successful_provider_payload_observed_once_after_frozen_request": True,
                "fetch_input_observed_before_and_output_after_frozen_fetch_urls": True,
                "same_url_alignment_uses_canonical_url_in_memory_only": True,
                "raw_task_question_query_url_title_page_prediction_or_credential_emitted": False,
                "query_search_fetch_model_process_or_evaluator_effect_added": False,
                "ranking_validator_evidence_posterior_entropy_or_credit_changed": False,
                "cache_or_cross_task_state_used": False,
                "bindings_restored": True,
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
                "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy": False,
                "benchmark_launch_or_evaluator_authorized": False,
            }
        )
        is None
        or any(
            (counts[count_name] > 0) is not (copied[task_name] > 0)
            for task_name, count_name in task_to_count.items()
        )
        or copied.get(
            "all_content_free_title_provenance_success_rows_consumed_validated_capabilities"
        )
        is not True
        or copied.get(
            "all_content_free_title_provenance_failure_rows_are_content_free_zero_projections"
        )
        is not True
        or copied.get(
            "content_free_title_provenance_failure_rows_claim_zero_private_effects"
        )
        is not False
        or copied.get("content_free_title_provenance_private_content_emitted")
        is not False
        or copied.get(
            "content_free_title_provenance_privileged_evaluator_content_read"
        )
        is not False
        or copied.get(
            "content_free_title_provenance_projection_claims_provider_or_transport_causality"
        )
        is not False
        or copied.get("content_free_title_provenance_changes_effect_or_credit_surface")
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.46.08 total title-provenance aggregate drifted")
    return copied


__all__ = [
    "AGGREGATE_KEYS",
    "POLICY_ID",
    "PROVENANCE_COUNT_FIELDS",
    "PROVENANCE_COUNT_NAMES",
    "ROW_KEYS",
    "TASK_FIELDS",
    "aggregate_projections",
    "failure_projection",
    "task_projection",
    "validate_aggregate",
    "validate_total_row",
]
