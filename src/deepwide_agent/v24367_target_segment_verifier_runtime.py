"""8+2 target-segment hidden-verifier successor.

This append-only runtime executes the already-audited V2.43.62 two-batch,
eight-proposal/two-hidden-verifier path exactly once, then replaces only the
pure hidden-verifier decision with V2.43.65--66 target-segment attribution.
It adds no model, search, or fetch effect.  The sealed V2.43.62 result remains
the replay parent, including its frozen source partition and hidden pages.

Proposal entropy, verifier outcome, and final utility credit are accounted
separately.  Runtime inputs remain exactly ``{opaque_id, question}``; there is
no benchmark selection, mapping, label, gold, evaluator, reward, or score
access or launch capability.
"""

from __future__ import annotations

import copy
import math
from collections import Counter
from collections.abc import Callable, Mapping
from typing import Any

from . import v24325_shared_prefix_revision_runtime as table
from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24333_programmatic_support_catalog import _normalize as catalog_normalize
from .v24335_programmatic_support_runtime import _declaration_map
from .v24355_explicit_partition_runtime import _changed_cells, _plain_page
from .v24362_two_verifier_partition_runtime import (
    POLICY_ID as PARENT_POLICY_ID,
    run_v24362_task,
    validate_partition_receipt,
    validate_result as validate_parent_result,
)
from .v24365_entity_segment_projection import POLICY_ID as PROJECTOR_POLICY_ID
from .v24366_target_segment_utility import (
    DISPOSITIONS as UTILITY_DISPOSITIONS,
    POLICY_ID as UTILITY_POLICY_ID,
    VERIFICATION_STATUSES,
    build_target_segment_utility_catalog,
    resolve_target_segment_utility_selection,
    validate_target_segment_utility_catalog,
    validate_target_segment_utility_receipt,
)


POLICY_ID = "v24367_target_segment_two_verifier_runtime_v1"
ROLE = "v24367_target_segment_two_verifier_task_result"
RECEIPT_ROLE = "v24367_target_segment_two_verifier_receipt"
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_result",
        "baseline_prediction",
        "candidate_prediction",
        "target_segment_verifier_receipt",
        "private_replay_state",
        "result_sha256",
    }
)
PRIVATE_KEYS = frozenset(
    {
        "target_segment_utility_catalog",
        "cell_utility_resolutions",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_policy_id",
        "target_segment_projection_policy_id",
        "target_segment_utility_policy_id",
        "partition_receipt",
        "observed_pages_respect_frozen_partition",
        "parent_semantic_catalog_present",
        "parent_proposal_page_count",
        "hidden_verifier_page_count",
        "parent_fetch_calls",
        "hidden_verifier_fetch_calls",
        "total_fetch_calls",
        "parent_model_requests",
        "candidate_changed_cells_before_hidden_verifier",
        "legacy_candidate_changed_cells_after_hidden_verifier",
        "candidate_changed_cells_after_hidden_verifier",
        "target_segment_recovered_cells",
        "target_segment_reverted_legacy_cells",
        "selection_resolution_count",
        "candidate_changes_without_declaration",
        "selected_exactly_bound_candidate_changes",
        "hidden_verifier_admitted_cells",
        "hidden_verifier_reverted_cells",
        "verification_record_count",
        "verification_status_counts",
        "selected_verification_status_counts",
        "selected_disposition_counts",
        "verifier_semantic_projection_count",
        "proposal_support_entropy_total_nats",
        "selected_proposal_conditional_entropy_reduction_nats",
        "utility_aligned_entropy_credit_nats",
        "hidden_verifier_pages_used_for_candidate_generation_or_model_prompt",
        "new_candidate_value_generated_by_hidden_verifier",
        "parent_support_set_ids_reused_without_rebuild",
        "target_segment_entity_boundary_enforced",
        "legacy_character_window_projector_used_for_final_decision",
        "question_prompt_response_query_url_host_page_candidate_value_evidence_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)


def _filter_candidate(
    parent: Mapping[str, Any],
    utility_catalog: Mapping[str, Any],
) -> tuple[str, list[dict[str, Any]], int, int, float, float, int]:
    semantic = parent["semantic_result"]
    core = semantic["core_result"]
    baseline = str(core["baseline_prediction"])
    candidate = str(core["candidate_prediction"])
    changes = _changed_cells(baseline, candidate)
    columns, _ = table._table_matrix(baseline)
    _, candidate_rows = table._table_matrix(candidate)
    output_rows = [list(row) for row in candidate_rows]
    declarations = _declaration_map(
        semantic["semantic_active_private_state"]["cell_support"], columns
    )
    proposal_credit = 0.0
    aligned_credit = 0.0
    missing_declarations = 0
    resolutions: list[dict[str, Any]] = []
    for change in changes:
        declaration = declarations.get(
            (
                table._support_normalize(change["row_key"]),
                int(change["column_index"]),
            )
        )
        if declaration is None:
            missing_declarations += 1
            output_rows[int(change["row_index"])][int(change["column_index"])] = str(
                change["old_value"]
            )
            continue
        receipt = resolve_target_segment_utility_selection(
            utility_catalog,
            row_key=str(change["row_key"]),
            column=str(change["column"]),
            new_value=str(change["new_value"]),
            proposal_support_set_id=str(declaration["support_set_id"]),
            declared_proposal_evidence_ids=declaration["evidence_ids"],
        )
        validate_target_segment_utility_receipt(receipt)
        resolutions.append(receipt)
        proposal_credit += float(
            receipt["proposal_conditional_entropy_reduction_nats"]
        )
        if receipt["admitted"]:
            aligned_credit += float(
                receipt["utility_aligned_entropy_credit_nats"]
            )
        else:
            output_rows[int(change["row_index"])][int(change["column_index"])] = str(
                change["old_value"]
            )
    filtered = table._render_table(columns, output_rows)
    canonical, errors = table.extract_valid_markdown_table(filtered, columns)
    if canonical != filtered or errors:
        raise ValueError("V2.43.67 filtered candidate is not canonical")
    retained = len(_changed_cells(baseline, filtered))
    return (
        filtered,
        resolutions,
        len(changes),
        retained,
        round(proposal_credit, 12),
        round(aligned_credit, 12),
        missing_declarations,
    )


def _change_identities(baseline: str, candidate: str) -> set[tuple[str, str, str]]:
    return {
        (
            table._support_normalize(change["row_key"]),
            table._normalize_column(change["column"]),
            table._support_normalize(change["new_value"]),
        )
        for change in _changed_cells(baseline, candidate)
    }


def _receipt(
    parent_result: Mapping[str, Any],
    utility_catalog: Mapping[str, Any],
    candidate: str,
    resolutions: list[dict[str, Any]],
    *,
    before: int,
    after: int,
    selected_proposal_credit: float,
    aligned_credit: float,
    missing_declarations: int,
) -> dict[str, Any]:
    parent_runtime = parent_result["hidden_verifier_receipt"]
    partition = parent_runtime["partition_receipt"]
    baseline = str(parent_result["baseline_prediction"])
    legacy = str(parent_result["candidate_prediction"])
    legacy_changes = _change_identities(baseline, legacy)
    target_segment_changes = _change_identities(baseline, candidate)
    selected_statuses = Counter(
        str(item["verification_status"])
        for item in resolutions
        if item["verification_status"] is not None
    )
    selected_dispositions = Counter(str(item["disposition"]) for item in resolutions)
    exact_bindings = sum(
        all(
            item[name] is True
            for name in (
                "target_binding_matches",
                "value_binding_matches",
                "proposal_support_set_binding_matches",
                "proposal_evidence_binding_matches",
                "proposal_and_verifier_sources_disjoint",
            )
        )
        for item in resolutions
    )
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": PARENT_POLICY_ID,
        "target_segment_projection_policy_id": PROJECTOR_POLICY_ID,
        "target_segment_utility_policy_id": UTILITY_POLICY_ID,
        "partition_receipt": copy.deepcopy(dict(partition)),
        "observed_pages_respect_frozen_partition": utility_catalog[
            "observed_pages_respect_frozen_partition"
        ],
        "parent_semantic_catalog_present": True,
        "parent_proposal_page_count": int(
            parent_runtime["parent_proposal_page_count"]
        ),
        "hidden_verifier_page_count": int(
            parent_runtime["hidden_verifier_page_count"]
        ),
        "parent_fetch_calls": int(parent_runtime["parent_fetch_calls"]),
        "hidden_verifier_fetch_calls": int(
            parent_runtime["hidden_verifier_fetch_calls"]
        ),
        "total_fetch_calls": int(parent_runtime["total_fetch_calls"]),
        "parent_model_requests": int(parent_runtime["parent_model_requests"]),
        "candidate_changed_cells_before_hidden_verifier": before,
        "legacy_candidate_changed_cells_after_hidden_verifier": len(legacy_changes),
        "candidate_changed_cells_after_hidden_verifier": after,
        "target_segment_recovered_cells": len(
            target_segment_changes - legacy_changes
        ),
        "target_segment_reverted_legacy_cells": len(
            legacy_changes - target_segment_changes
        ),
        "selection_resolution_count": len(resolutions),
        "candidate_changes_without_declaration": missing_declarations,
        "selected_exactly_bound_candidate_changes": exact_bindings,
        "hidden_verifier_admitted_cells": sum(
            item["admitted"] is True for item in resolutions
        ),
        "hidden_verifier_reverted_cells": before - after,
        "verification_record_count": int(
            utility_catalog["verification_record_count"]
        ),
        "verification_status_counts": dict(
            utility_catalog["verification_status_counts"]
        ),
        "selected_verification_status_counts": dict(sorted(selected_statuses.items())),
        "selected_disposition_counts": dict(sorted(selected_dispositions.items())),
        "verifier_semantic_projection_count": int(
            utility_catalog["verifier_semantic_projection_count"]
        ),
        "proposal_support_entropy_total_nats": float(
            utility_catalog["proposal_support_entropy_total_nats"]
        ),
        "selected_proposal_conditional_entropy_reduction_nats": round(
            selected_proposal_credit, 12
        ),
        "utility_aligned_entropy_credit_nats": round(aligned_credit, 12),
        "hidden_verifier_pages_used_for_candidate_generation_or_model_prompt": False,
        "new_candidate_value_generated_by_hidden_verifier": False,
        "parent_support_set_ids_reused_without_rebuild": True,
        "target_segment_entity_boundary_enforced": True,
        "legacy_character_window_projector_used_for_final_decision": False,
        "question_prompt_response_query_url_host_page_candidate_value_evidence_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    validate_receipt(value)
    return value


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    partition = value.get("partition_receipt")
    status_counts = value.get("verification_status_counts")
    selected_statuses = value.get("selected_verification_status_counts")
    dispositions = value.get("selected_disposition_counts")
    count_fields = (
        "parent_proposal_page_count",
        "hidden_verifier_page_count",
        "parent_fetch_calls",
        "hidden_verifier_fetch_calls",
        "total_fetch_calls",
        "parent_model_requests",
        "candidate_changed_cells_before_hidden_verifier",
        "legacy_candidate_changed_cells_after_hidden_verifier",
        "candidate_changed_cells_after_hidden_verifier",
        "target_segment_recovered_cells",
        "target_segment_reverted_legacy_cells",
        "selection_resolution_count",
        "candidate_changes_without_declaration",
        "selected_exactly_bound_candidate_changes",
        "hidden_verifier_admitted_cells",
        "hidden_verifier_reverted_cells",
        "verification_record_count",
        "verifier_semantic_projection_count",
    )
    numeric_fields = (
        "proposal_support_entropy_total_nats",
        "selected_proposal_conditional_entropy_reduction_nats",
        "utility_aligned_entropy_credit_nats",
    )
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != RECEIPT_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("parent_policy_id") != PARENT_POLICY_ID
        or value.get("target_segment_projection_policy_id") != PROJECTOR_POLICY_ID
        or value.get("target_segment_utility_policy_id") != UTILITY_POLICY_ID
        or not isinstance(partition, Mapping)
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in count_fields
        )
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), (int, float))
            or not math.isfinite(float(value[name]))
            or float(value[name]) < 0
            for name in numeric_fields
        )
        or not isinstance(status_counts, Mapping)
        or not isinstance(selected_statuses, Mapping)
        or not isinstance(dispositions, Mapping)
        or any(
            name not in (
                VERIFICATION_STATUSES
                if mapping is not dispositions
                else UTILITY_DISPOSITIONS
            )
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
            for mapping in (status_counts, selected_statuses, dispositions)
            for name, count in mapping.items()
        )
        or sum(status_counts.values()) != value["verification_record_count"]
        or sum(selected_statuses.values())
        != value["selected_exactly_bound_candidate_changes"]
        or sum(dispositions.values()) != value["selection_resolution_count"]
        or value["candidate_changed_cells_after_hidden_verifier"]
        > value["candidate_changed_cells_before_hidden_verifier"]
        or value["legacy_candidate_changed_cells_after_hidden_verifier"]
        > value["candidate_changed_cells_before_hidden_verifier"]
        or value["target_segment_recovered_cells"]
        > value["candidate_changed_cells_after_hidden_verifier"]
        or value["target_segment_reverted_legacy_cells"]
        > value["legacy_candidate_changed_cells_after_hidden_verifier"]
        or value["candidate_changed_cells_after_hidden_verifier"]
        != value["legacy_candidate_changed_cells_after_hidden_verifier"]
        + value["target_segment_recovered_cells"]
        - value["target_segment_reverted_legacy_cells"]
        or value["hidden_verifier_reverted_cells"]
        != value["candidate_changed_cells_before_hidden_verifier"]
        - value["candidate_changed_cells_after_hidden_verifier"]
        or value["hidden_verifier_admitted_cells"]
        != value["candidate_changed_cells_after_hidden_verifier"]
        or value["selection_resolution_count"]
        + value["candidate_changes_without_declaration"]
        != value["candidate_changed_cells_before_hidden_verifier"]
        or value["selected_exactly_bound_candidate_changes"]
        > value["selection_resolution_count"]
        or value["selected_proposal_conditional_entropy_reduction_nats"]
        > value["proposal_support_entropy_total_nats"] + 1e-12
        or value["utility_aligned_entropy_credit_nats"]
        > value["selected_proposal_conditional_entropy_reduction_nats"] + 1e-12
        or value["hidden_verifier_fetch_calls"]
        != partition.get("verifier_source_count")
        or value["total_fetch_calls"]
        != value["parent_fetch_calls"] + value["hidden_verifier_fetch_calls"]
        or value.get("observed_pages_respect_frozen_partition") is not True
        or value.get("parent_semantic_catalog_present") is not True
        or value.get("hidden_verifier_pages_used_for_candidate_generation_or_model_prompt")
        is not False
        or value.get("new_candidate_value_generated_by_hidden_verifier") is not False
        or value.get("parent_support_set_ids_reused_without_rebuild") is not True
        or value.get("target_segment_entity_boundary_enforced") is not True
        or value.get("legacy_character_window_projector_used_for_final_decision")
        is not False
        or value.get("question_prompt_response_query_url_host_page_candidate_value_evidence_id_or_credential_emitted")
        is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read")
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.67 verifier receipt drifted")
    validate_partition_receipt(partition)
    return copy.deepcopy(dict(value))


def _derive(parent_result: Mapping[str, Any]) -> dict[str, Any]:
    parent = validate_parent_result(parent_result)
    semantic = parent["parent_result"]["semantic_result"]
    proposal_catalog = semantic["semantic_active_private_state"][
        "semantic_active_catalog"
    ]
    if not isinstance(proposal_catalog, Mapping):
        raise ValueError("V2.43.67 parent semantic catalog is absent")
    partition = parent["hidden_verifier_receipt"]["partition_receipt"]
    verifier_pages = parent["private_replay_state"]["verifier_pages"]
    utility_catalog = build_target_segment_utility_catalog(
        proposal_catalog,
        [_plain_page(page) for page in verifier_pages],
        partition_seed_sha256=partition["partition_seed_sha256"],
        expected_proposal_source_key_sha256s=partition[
            "proposal_source_key_sha256s"
        ],
        expected_verifier_source_key_sha256s=partition[
            "verifier_source_key_sha256s"
        ],
    )
    validate_target_segment_utility_catalog(utility_catalog)
    (
        candidate,
        resolutions,
        before,
        after,
        selected_proposal_credit,
        aligned_credit,
        missing_declarations,
    ) = _filter_candidate(parent["parent_result"], utility_catalog)
    receipt = _receipt(
        parent,
        utility_catalog,
        candidate,
        resolutions,
        before=before,
        after=after,
        selected_proposal_credit=selected_proposal_credit,
        aligned_credit=aligned_credit,
        missing_declarations=missing_declarations,
    )
    return {
        "baseline_prediction": str(parent["baseline_prediction"]),
        "candidate_prediction": candidate,
        "receipt": receipt,
        "private": {
            "target_segment_utility_catalog": utility_catalog,
            "cell_utility_resolutions": resolutions,
        },
    }


def run_v24367_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    partition_seed_sha256: str,
    limits: ScoreFirstLimits | None = None,
    monotonic: Callable[[], float],
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    parent = run_v24362_task(
        visible,
        model=model,
        search=search,
        partition_seed_sha256=partition_seed_sha256,
        limits=limits,
        monotonic=monotonic,
    )
    derived = _derive(parent)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "parent_result": copy.deepcopy(parent),
        "baseline_prediction": derived["baseline_prediction"],
        "candidate_prediction": derived["candidate_prediction"],
        "target_segment_verifier_receipt": derived["receipt"],
        "private_replay_state": derived["private"],
    }
    value["result_sha256"] = payload_sha256(value)
    validate_result(value)
    return value


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("result_sha256", None)
    parent = value.get("parent_result")
    receipt = value.get("target_segment_verifier_receipt")
    private = value.get("private_replay_state")
    if (
        set(value) != RESULT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(parent, Mapping)
        or not isinstance(receipt, Mapping)
        or not isinstance(private, Mapping)
        or set(private) != PRIVATE_KEYS
        or not isinstance(value.get("baseline_prediction"), str)
        or not isinstance(value.get("candidate_prediction"), str)
        or not isinstance(private.get("target_segment_utility_catalog"), Mapping)
        or not isinstance(private.get("cell_utility_resolutions"), list)
        or any(
            not isinstance(item, Mapping)
            for item in private["cell_utility_resolutions"]
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.67 result identity drifted")
    validate_parent_result(parent)
    validate_receipt(receipt)
    validate_target_segment_utility_catalog(
        private["target_segment_utility_catalog"]
    )
    for item in private["cell_utility_resolutions"]:
        validate_target_segment_utility_receipt(item)
    expected = _derive(parent)
    if (
        value["baseline_prediction"] != expected["baseline_prediction"]
        or value["candidate_prediction"] != expected["candidate_prediction"]
        or dict(receipt) != expected["receipt"]
        or dict(private) != expected["private"]
    ):
        raise ValueError("V2.43.67 deterministic replay drifted")
    return copy.deepcopy(dict(value))


__all__ = [
    "POLICY_ID",
    "ROLE",
    "run_v24367_task",
    "validate_receipt",
    "validate_result",
]
