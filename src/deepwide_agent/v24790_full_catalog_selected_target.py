"""Selected-Unknown cross-tab view over an intact full-target catalog.

The target is chosen from the frozen baseline table in canonical row-major
order.  The original V2.43.65 full-target catalog is validated and retained so
every other visible entity continues to delimit semantic segments.  This
module filters projection/support/change groups for the selected binding; it
never rebuilds a one-target catalog.

Only fixed-vocabulary counts and safety attestations leave the private
boundary.  The module has no file, environment, process, network, model,
search, benchmark-label, evaluator, score, reward, or credential capability.
"""

from __future__ import annotations

import copy
from collections import Counter, defaultdict
from collections.abc import Mapping
from typing import Any

from . import v24333_programmatic_support_catalog as support
from . import v24365_entity_segment_projection as segment
from . import v24743_generic_record_binding as binder
from . import v24786_projection_support_cross_tab_observer as observer
from .v24323_shared_prefix_cell_entropy import payload_sha256


POLICY_ID = "v24790_full_catalog_selected_unknown_cross_tab_v1"
ROLE = "v24790_full_catalog_selected_unknown_cross_tab_receipt"
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "full_catalog_target_count",
        "full_catalog_unknown_target_count",
        "selected_target_count",
        "selected_target_is_baseline_unknown",
        "selected_by_canonical_row_major_order",
        "full_target_catalog_validated",
        "full_target_catalog_and_projection_vector_mutated",
        "single_target_catalog_rebuilt",
        "other_visible_entities_retained_as_segment_boundaries",
        "cross_tab_receipt",
        "prediction_bytes_changed_by_observer",
        "positive_entropy_or_task_credit_assigned",
        "question_task_identity_field_value_query_url_host_page_prediction_or_private_content_hash_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)


def select_first_unknown_target(baseline: str) -> support.CellTarget | None:
    columns, rows = binder._baseline_matrix(baseline)
    for row in rows:
        for column_index in range(1, len(columns)):
            target = support.CellTarget(
                row[0], columns[column_index], row[column_index]
            )
            if target.baseline_unknown:
                return target
    return None


def _selected_cross_tab(
    validated: Mapping[str, Any],
    baseline: str,
    candidate: str,
    targets: list[support.CellTarget],
    selected: support.CellTarget,
) -> dict[str, Any]:
    target_by_binding = {target.binding_sha256: target for target in targets}
    if (
        len(target_by_binding) != len(targets)
        or selected.binding_sha256 not in target_by_binding
    ):
        raise ValueError("V2.47.90 selected target escaped full catalog")

    changes = observer._table_changes(baseline, candidate, targets)
    all_groups = observer._projection_groups(validated, set(target_by_binding))
    all_dispositions, all_eligible = observer._catalog_group_dispositions(
        validated, targets
    )
    all_projection_backed = observer._projection_backed_support_pairs(
        all_groups, all_eligible
    )
    binding = selected.binding_sha256
    groups = {pair: sources for pair, sources in all_groups.items() if pair[0] == binding}
    catalog_dispositions = {
        pair: disposition
        for pair, disposition in all_dispositions.items()
        if pair[0] == binding
    }
    eligible = {pair: item for pair, item in all_eligible.items() if pair[0] == binding}
    projection_backed = {pair for pair in all_projection_backed if pair[0] == binding}
    values = {pair[1] for pair in groups}
    proposal_pairs = projection_backed if len(values) == 1 else set()
    changed_value = changes.get(binding)

    group_rows: Counter[tuple[str, ...]] = Counter()
    catalog_counts: Counter[str] = Counter()
    proposal_counts: Counter[str] = Counter()
    change_counts: Counter[str] = Counter()
    changed_to_projected = 0
    strict_joint = 0
    for pair, sources in groups.items():
        source_multiplicity = "one" if len(sources) == 1 else "two_or_more"
        catalog_disposition = catalog_dispositions.get(
            pair, "catalog_candidate_absent"
        )
        if catalog_disposition != "eligible_support":
            proposal_disposition = "catalog_blocked"
        elif pair not in projection_backed:
            proposal_disposition = "eligible_not_projection_backed"
        elif len(values) > 1:
            proposal_disposition = "projection_value_conflict"
        else:
            proposal_disposition = (
                "unconflicted_projection_backed_unknown_proposal"
            )
        if changed_value is None:
            change = "unchanged"
        elif changed_value == pair[1]:
            change = "changed_to_this_projection_value"
            changed_to_projected += 1
        else:
            change = "changed_to_other_value"
        group_rows[
            (
                "unknown",
                source_multiplicity,
                catalog_disposition,
                proposal_disposition,
                change,
            )
        ] += 1
        catalog_counts[catalog_disposition] += 1
        proposal_counts[proposal_disposition] += 1
        change_counts[change] += 1
        if (
            source_multiplicity == "two_or_more"
            and catalog_disposition == "eligible_support"
            and proposal_disposition
            == "unconflicted_projection_backed_unknown_proposal"
            and change == "changed_to_this_projection_value"
        ):
            strict_joint += 1

    maximum_sources = max((len(sources) for sources in groups.values()), default=0)
    target_change = (
        "unchanged"
        if changed_value is None
        else "changed_to_unconflicted_proposal"
        if any(pair in proposal_pairs and pair[1] == changed_value for pair in groups)
        else "changed_other"
    )
    target_rows: Counter[tuple[str, ...]] = Counter(
        {
            (
                "unknown",
                observer._bucket(len(groups)),
                observer._bucket(maximum_sources),
                observer._bucket(len(projection_backed)),
                observer._bucket(len(proposal_pairs)),
                target_change,
            ): 1
        }
    )
    quarantine_counts = Counter(
        disposition
        for disposition in catalog_dispositions.values()
        if disposition in observer.CATALOG_QUARANTINE_DISPOSITIONS
    )
    counts = {
        "target_count": 1,
        "unknown_target_count": 1,
        "zero_projection_target_count": int(not groups),
        "projection_group_count": len(groups),
        "unknown_projection_group_count": len(groups),
        "unknown_single_source_projection_group_count": sum(
            len(sources) == 1 for sources in groups.values()
        ),
        "unknown_two_or_more_source_projection_group_count": sum(
            len(sources) >= 2 for sources in groups.values()
        ),
        "catalog_candidate_group_count": len(catalog_dispositions),
        "catalog_eligible_support_set_count": len(eligible),
        "projection_backed_support_group_count": len(projection_backed),
        "unconflicted_unknown_proposal_group_count": len(proposal_pairs),
        "changed_target_count": int(changed_value is not None),
        "changed_to_projected_value_group_count": changed_to_projected,
        "strict_joint_safe_change_group_count": strict_joint,
    }
    task_local = {
        "has_unknown_target": True,
        "has_unknown_projection_group": bool(groups),
        "has_unknown_two_or_more_source_projection_group": any(
            len(sources) >= 2 for sources in groups.values()
        ),
        "has_projection_backed_support_group": bool(projection_backed),
        "has_unconflicted_unknown_proposal_group": bool(proposal_pairs),
        "has_changed_target": changed_value is not None,
        "has_strict_joint_safe_change_group": strict_joint > 0,
    }
    value = {
        "artifact_version": 1,
        "role": observer.ROLE,
        "policy_id": observer.POLICY_ID,
        **counts,
        "catalog_disposition_counts": {
            name: int(catalog_counts[name]) for name in observer.CATALOG_DISPOSITIONS
        },
        "catalog_quarantine_disposition_counts": {
            name: int(quarantine_counts[name])
            for name in observer.CATALOG_QUARANTINE_DISPOSITIONS
        },
        "proposal_disposition_counts": {
            name: int(proposal_counts[name])
            for name in observer.PROPOSAL_DISPOSITIONS
        },
        "group_change_disposition_counts": {
            name: int(change_counts[name])
            for name in observer.GROUP_CHANGE_DISPOSITIONS
        },
        "target_cross_tab": observer._sorted_rows(
            target_rows,
            (
                "baseline_state",
                "projected_value_group_count",
                "maximum_projection_source_multiplicity",
                "projection_backed_support_group_count",
                "unconflicted_proposal_group_count",
                "candidate_change",
            ),
        ),
        "projection_group_cross_tab": observer._sorted_rows(
            group_rows,
            (
                "baseline_state",
                "projection_source_multiplicity",
                "catalog_disposition",
                "proposal_disposition",
                "candidate_change",
            ),
        ),
        "task_local_joint": task_local,
        "catalog_candidate_and_quarantine_replay_exact": True,
        "projection_group_partition_exact": sum(group_rows.values()) == len(groups),
        "target_partition_exact": True,
        "candidate_changes_only_baseline_unknown_cells": True,
        "same_catalog_and_predictions_observed_without_mutation": True,
        "cross_task_or_cross_group_margins_used_as_joint": False,
        "positive_entropy_or_task_credit_assigned": False,
        "question_task_identity_field_value_query_url_host_page_prediction_or_private_content_hash_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    return observer.validate_receipt(value)


def build_selected_target_cross_tab(
    catalog: Mapping[str, Any], baseline: str, candidate: str
) -> dict[str, Any] | None:
    frozen_catalog = copy.deepcopy(dict(catalog))
    validated = segment.validate_target_segment_catalog(catalog)
    targets = [segment._target(item) for item in validated["targets"]]
    # Full-table replay validates that every catalog target matches its exact
    # baseline coordinate and that candidate changes are Unknown-only.
    observer._table_changes(baseline, candidate, targets)
    selected = select_first_unknown_target(baseline)
    if selected is None:
        return None
    cross_tab = _selected_cross_tab(
        validated, baseline, candidate, targets, selected
    )
    if dict(catalog) != frozen_catalog:
        raise RuntimeError("V2.47.90 full catalog was mutated")
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "full_catalog_target_count": len(targets),
        "full_catalog_unknown_target_count": sum(
            target.baseline_unknown for target in targets
        ),
        "selected_target_count": 1,
        "selected_target_is_baseline_unknown": True,
        "selected_by_canonical_row_major_order": True,
        "full_target_catalog_validated": True,
        "full_target_catalog_and_projection_vector_mutated": False,
        "single_target_catalog_rebuilt": False,
        "other_visible_entities_retained_as_segment_boundaries": True,
        "cross_tab_receipt": cross_tab,
        "prediction_bytes_changed_by_observer": False,
        "positive_entropy_or_task_credit_assigned": False,
        "question_task_identity_field_value_query_url_host_page_prediction_or_private_content_hash_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    cross_tab = copied.get("cross_tab_receipt")
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or isinstance(copied.get("full_catalog_target_count"), bool)
        or not isinstance(copied.get("full_catalog_target_count"), int)
        or copied["full_catalog_target_count"] < 1
        or isinstance(copied.get("full_catalog_unknown_target_count"), bool)
        or not isinstance(copied.get("full_catalog_unknown_target_count"), int)
        or not 1 <= copied["full_catalog_unknown_target_count"] <= copied["full_catalog_target_count"]
        or copied.get("selected_target_count") != 1
        or copied.get("selected_target_is_baseline_unknown") is not True
        or copied.get("selected_by_canonical_row_major_order") is not True
        or copied.get("full_target_catalog_validated") is not True
        or copied.get("full_target_catalog_and_projection_vector_mutated") is not False
        or copied.get("single_target_catalog_rebuilt") is not False
        or copied.get("other_visible_entities_retained_as_segment_boundaries") is not True
        or not isinstance(cross_tab, Mapping)
        or copied.get("prediction_bytes_changed_by_observer") is not False
        or copied.get("positive_entropy_or_task_credit_assigned") is not False
        or copied.get("question_task_identity_field_value_query_url_host_page_prediction_or_private_content_hash_emitted") is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or copied.get("file_environment_network_model_search_fetch_process_or_evaluator_accessed") is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.90 selected-target receipt drifted")
    validated = observer.validate_receipt(cross_tab)
    if validated["target_count"] != 1 or validated["unknown_target_count"] != 1:
        raise ValueError("V2.47.90 selected-target cross-tab denominator drifted")
    return copied


__all__ = [
    "POLICY_ID",
    "ROLE",
    "build_selected_target_cross_tab",
    "select_first_unknown_target",
    "validate_receipt",
]
