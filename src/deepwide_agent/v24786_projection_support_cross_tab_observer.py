"""Pure task-local cross-tab observer for projection/support closure.

V2.47.84 exposed only separate aggregate margins: one projected Unknown
target/value group and two multi-source groups.  Those margins do not reveal
whether the same group had both properties.  This append-only observer runs
inside a future trusted child over one already validated private semantic
catalog and the two already materialized arm predictions.  It jointly counts,
for each exact target/value projection group:

* whether the baseline cell is Unknown;
* whether the projection has one or at least two registrable sources;
* the exact frozen support-catalog admission/quarantine disposition;
* whether it becomes an unconflicted projection-backed proposal; and
* whether the final candidate changed to that exact projected value.

Targets with no projection are retained in a separate target-level cross-tab.
Only fixed-vocabulary counts leave the private boundary.  The observer changes
no prediction or catalog, performs no I/O or external effect, assigns no
entropy/task credit, and has no benchmark-label or evaluator capability.
"""

from __future__ import annotations

import copy
from collections import Counter, defaultdict
from collections.abc import Mapping
from typing import Any

from . import v24333_programmatic_support_catalog as support
from . import v24365_entity_segment_projection as segment
from . import v24743_generic_record_binding as binder
from .v24323_shared_prefix_cell_entropy import payload_sha256


POLICY_ID = "v24786_task_local_projection_support_cross_tab_v1"
ROLE = "v24786_projection_support_cross_tab_receipt"
MAXIMUM_SUPPORT_SETS_PER_TARGET = 32

BASELINE_STATES = ("known", "unknown")
SOURCE_MULTIPLICITIES = ("one", "two_or_more")
TARGET_PROJECTION_BUCKETS = ("zero", "one", "two_or_more")
CATALOG_DISPOSITIONS = (
    "catalog_candidate_absent",
    "eligible_support",
    "quarantine_catalog_capacity",
    "quarantine_conflict",
    "quarantine_fetch_integrity",
    "quarantine_insufficient_corroboration",
    "quarantine_insufficient_independence",
    "quarantine_low_reliability",
    "quarantine_nonpositive_conditional_gain",
)
CATALOG_QUARANTINE_DISPOSITIONS = tuple(
    name for name in CATALOG_DISPOSITIONS if name.startswith("quarantine_")
)
PROPOSAL_DISPOSITIONS = (
    "catalog_blocked",
    "eligible_not_projection_backed",
    "not_unknown",
    "projection_value_conflict",
    "unconflicted_projection_backed_unknown_proposal",
)
GROUP_CHANGE_DISPOSITIONS = (
    "changed_to_other_value",
    "changed_to_this_projection_value",
    "unchanged",
)
TARGET_CHANGE_DISPOSITIONS = (
    "changed_other",
    "changed_to_unconflicted_proposal",
    "unchanged",
)
COUNT_FIELDS = (
    "target_count",
    "unknown_target_count",
    "zero_projection_target_count",
    "projection_group_count",
    "unknown_projection_group_count",
    "unknown_single_source_projection_group_count",
    "unknown_two_or_more_source_projection_group_count",
    "catalog_candidate_group_count",
    "catalog_eligible_support_set_count",
    "projection_backed_support_group_count",
    "unconflicted_unknown_proposal_group_count",
    "changed_target_count",
    "changed_to_projected_value_group_count",
    "strict_joint_safe_change_group_count",
)
TARGET_ROW_KEYS = frozenset(
    {
        "baseline_state",
        "projected_value_group_count",
        "maximum_projection_source_multiplicity",
        "projection_backed_support_group_count",
        "unconflicted_proposal_group_count",
        "candidate_change",
        "count",
    }
)
GROUP_ROW_KEYS = frozenset(
    {
        "baseline_state",
        "projection_source_multiplicity",
        "catalog_disposition",
        "proposal_disposition",
        "candidate_change",
        "count",
    }
)
TASK_LOCAL_JOINT_KEYS = frozenset(
    {
        "has_unknown_target",
        "has_unknown_projection_group",
        "has_unknown_two_or_more_source_projection_group",
        "has_projection_backed_support_group",
        "has_unconflicted_unknown_proposal_group",
        "has_changed_target",
        "has_strict_joint_safe_change_group",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        *COUNT_FIELDS,
        "catalog_disposition_counts",
        "catalog_quarantine_disposition_counts",
        "proposal_disposition_counts",
        "group_change_disposition_counts",
        "target_cross_tab",
        "projection_group_cross_tab",
        "task_local_joint",
        "catalog_candidate_and_quarantine_replay_exact",
        "projection_group_partition_exact",
        "target_partition_exact",
        "candidate_changes_only_baseline_unknown_cells",
        "same_catalog_and_predictions_observed_without_mutation",
        "cross_task_or_cross_group_margins_used_as_joint",
        "positive_entropy_or_task_credit_assigned",
        "question_task_identity_field_value_query_url_host_page_prediction_or_private_content_hash_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)


def _bucket(amount: int) -> str:
    if amount < 0:
        raise ValueError("V2.47.86 count is negative")
    return "zero" if amount == 0 else "one" if amount == 1 else "two_or_more"


def _candidate_value_sha256(value: object) -> str:
    return support._sha256_text(support._normalize(value))


def _catalog_group_dispositions(
    validated: Mapping[str, Any], targets: list[support.CellTarget]
) -> tuple[dict[tuple[str, str], str], dict[tuple[str, str], dict[str, Any]]]:
    """Replay the frozen catalog and retain per-group private dispositions."""

    active = validated["active_catalog"]
    base = active["base_catalog"]
    pages = [support._coerce_page(item) for item in active["active_pages"]]
    dispositions: dict[tuple[str, str], str] = {}
    eligible_by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    quarantined: Counter[str] = Counter()
    selected_support_sets: list[dict[str, Any]] = []
    considered = 0

    for target in sorted(targets, key=lambda item: item.binding_sha256):
        groups, old_sources = support._candidate_support(target, pages)
        required = (
            int(base["minimum_unknown_sources"])
            if target.baseline_unknown
            else int(base["minimum_override_sources"])
        )
        ranked = sorted(
            groups.items(),
            key=lambda item: (-len(item[1]), support._candidate_priority(item[0])),
        )
        eligible_for_target: list[
            tuple[tuple[str, str], dict[str, Any]]
        ] = []
        for candidate, sources in ranked:
            considered += 1
            pair = (target.binding_sha256, _candidate_value_sha256(candidate))
            if pair in dispositions or any(
                pair == existing for existing, _item in eligible_for_target
            ):
                raise ValueError("V2.47.86 duplicate catalog target/value group")
            if len(sources) < required:
                disposition = "quarantine_insufficient_independence"
                dispositions[pair] = disposition
                quarantined[disposition] += 1
                continue
            item = support._support_set(
                target,
                candidate,
                sources,
                old_sources,
                required_sources=required,
            )
            admission_disposition = str(item["admission_receipt"]["disposition"])
            if item["admission_receipt"]["context_action"] == "core_only":
                if admission_disposition not in CATALOG_DISPOSITIONS:
                    raise ValueError("V2.47.86 unknown catalog quarantine")
                dispositions[pair] = admission_disposition
                quarantined[admission_disposition] += 1
                continue
            eligible_for_target.append((pair, item))

        selected = eligible_for_target[:MAXIMUM_SUPPORT_SETS_PER_TARGET]
        overflow = eligible_for_target[MAXIMUM_SUPPORT_SETS_PER_TARGET:]
        for pair, item in selected:
            if pair in dispositions:
                raise ValueError("V2.47.86 catalog group disposition collision")
            dispositions[pair] = "eligible_support"
            eligible_by_pair[pair] = item
            selected_support_sets.append(item)
        for pair, _item in overflow:
            if pair in dispositions:
                raise ValueError("V2.47.86 catalog capacity collision")
            dispositions[pair] = "quarantine_catalog_capacity"
            quarantined["quarantine_catalog_capacity"] += 1

    selected_support_sets.sort(key=lambda item: item["support_set_id"])
    if (
        considered != int(base["candidate_groups_considered"])
        or dict(sorted(quarantined.items()))
        != dict(base["quarantined_candidate_groups"])
        or selected_support_sets != list(base["support_sets"])
        or len(eligible_by_pair) != int(base["eligible_support_set_count"])
    ):
        raise ValueError("V2.47.86 frozen support catalog replay drifted")
    return dispositions, eligible_by_pair


def _projection_groups(
    validated: Mapping[str, Any], target_bindings: set[str]
) -> dict[tuple[str, str], set[str]]:
    pages_by_scope = {
        "core": validated["original_core_pages"],
        "reserve": validated["original_reserve_pages"],
    }
    output: dict[tuple[str, str], set[str]] = defaultdict(set)
    for item in validated["projections"]:
        binding = str(item["target_binding_sha256"])
        if binding not in target_bindings:
            raise ValueError("V2.47.86 projection target escaped catalog")
        pages = pages_by_scope[str(item["scope"])]
        ordinal = int(item["page_ordinal"])
        if not 1 <= ordinal <= len(pages):
            raise ValueError("V2.47.86 projection page binding drifted")
        source = binder._source_key(str(pages[ordinal - 1]["host"]))
        output[(binding, str(item["normalized_value_sha256"]))].add(source)
    return dict(output)


def _table_changes(
    baseline: str,
    candidate: str,
    targets: list[support.CellTarget],
) -> dict[str, str]:
    baseline_columns, baseline_rows = binder._baseline_matrix(baseline)
    candidate_columns, candidate_rows = binder._baseline_matrix(candidate)
    if (
        candidate_columns != baseline_columns
        or len(candidate_rows) != len(baseline_rows)
        or any(
            before[0] != after[0]
            for before, after in zip(baseline_rows, candidate_rows, strict=True)
        )
    ):
        raise ValueError("V2.47.86 prediction table shape drifted")

    expected: dict[str, tuple[int, int]] = {}
    for row_index, row in enumerate(baseline_rows):
        for column_index in range(1, len(baseline_columns)):
            target = support.CellTarget(
                row[0], baseline_columns[column_index], row[column_index]
            )
            if target.binding_sha256 in expected:
                raise ValueError("V2.47.86 duplicate table target binding")
            expected[target.binding_sha256] = (row_index, column_index)
    observed = {target.binding_sha256 for target in targets}
    if observed != set(expected) or len(targets) != len(expected):
        raise ValueError("V2.47.86 catalog targets do not match baseline table")

    changes: dict[str, str] = {}
    for target in targets:
        row_index, column_index = expected[target.binding_sha256]
        before = baseline_rows[row_index][column_index]
        after = candidate_rows[row_index][column_index]
        if binder._canonical_text(before).casefold() == binder._canonical_text(
            after
        ).casefold():
            continue
        if not target.baseline_unknown or binder._is_unknown(after):
            raise ValueError("V2.47.86 candidate changed a non-Unknown cell unsafely")
        changes[target.binding_sha256] = _candidate_value_sha256(after)
    return changes


def _projection_backed_support_pairs(
    groups: Mapping[tuple[str, str], set[str]],
    eligible: Mapping[tuple[str, str], Mapping[str, Any]],
) -> set[tuple[str, str]]:
    output: set[tuple[str, str]] = set()
    for pair, item in eligible.items():
        if item["baseline_cell_unknown"] is not True or pair not in groups:
            continue
        support_sources = {
            str(binding["source_key_sha256"])
            for binding in item["evidence_source_bindings"]
        }
        projected_source_hashes = {
            segment._sha256_text(source) for source in groups[pair]
        }
        if (
            len(support_sources) < 2
            or not support_sources.issubset(projected_source_hashes)
        ):
            continue
        if (
            int(item["independent_source_count"]) < 2
            or int(item["required_source_count"]) < 2
        ):
            raise ValueError("V2.47.86 eligible support source count drifted")
        try:
            binder._safe_text(item["candidate_value"])
        except ValueError:
            continue
        output.add(pair)
    return output


def _sorted_rows(counter: Counter[tuple[str, ...]], names: tuple[str, ...]) -> list[dict[str, Any]]:
    return [
        {**dict(zip(names, key, strict=True)), "count": int(amount)}
        for key, amount in sorted(counter.items())
        if amount > 0
    ]


def _compute(catalog: Mapping[str, Any], baseline: str, candidate: str) -> dict[str, Any]:
    validated = segment.validate_target_segment_catalog(catalog)
    targets = [segment._target(item) for item in validated["targets"]]
    target_by_binding = {target.binding_sha256: target for target in targets}
    if len(target_by_binding) != len(targets):
        raise ValueError("V2.47.86 duplicate semantic target")
    changes = _table_changes(baseline, candidate, targets)
    groups = _projection_groups(validated, set(target_by_binding))
    catalog_dispositions, eligible = _catalog_group_dispositions(
        validated, targets
    )
    projection_backed = _projection_backed_support_pairs(groups, eligible)

    values_by_target: dict[str, set[str]] = defaultdict(set)
    groups_by_target: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for pair in groups:
        values_by_target[pair[0]].add(pair[1])
        groups_by_target[pair[0]].append(pair)
    proposal_pairs = {
        pair
        for pair in projection_backed
        if target_by_binding[pair[0]].baseline_unknown
        and len(values_by_target[pair[0]]) == 1
    }

    group_rows: Counter[tuple[str, ...]] = Counter()
    catalog_counts: Counter[str] = Counter()
    proposal_counts: Counter[str] = Counter()
    group_change_counts: Counter[str] = Counter()
    changed_to_projected = 0
    strict_joint = 0
    for pair, sources in groups.items():
        target = target_by_binding[pair[0]]
        baseline_state = "unknown" if target.baseline_unknown else "known"
        source_multiplicity = "one" if len(sources) == 1 else "two_or_more"
        catalog_disposition = catalog_dispositions.get(
            pair, "catalog_candidate_absent"
        )
        if not target.baseline_unknown:
            proposal_disposition = "not_unknown"
        elif catalog_disposition != "eligible_support":
            proposal_disposition = "catalog_blocked"
        elif pair not in projection_backed:
            proposal_disposition = "eligible_not_projection_backed"
        elif len(values_by_target[pair[0]]) > 1:
            proposal_disposition = "projection_value_conflict"
        else:
            proposal_disposition = (
                "unconflicted_projection_backed_unknown_proposal"
            )
        changed_value = changes.get(pair[0])
        if changed_value is None:
            group_change = "unchanged"
        elif changed_value == pair[1]:
            group_change = "changed_to_this_projection_value"
            changed_to_projected += 1
        else:
            group_change = "changed_to_other_value"
        row = (
            baseline_state,
            source_multiplicity,
            catalog_disposition,
            proposal_disposition,
            group_change,
        )
        group_rows[row] += 1
        catalog_counts[catalog_disposition] += 1
        proposal_counts[proposal_disposition] += 1
        group_change_counts[group_change] += 1
        if (
            baseline_state == "unknown"
            and source_multiplicity == "two_or_more"
            and catalog_disposition == "eligible_support"
            and proposal_disposition
            == "unconflicted_projection_backed_unknown_proposal"
            and group_change == "changed_to_this_projection_value"
        ):
            strict_joint += 1

    target_rows: Counter[tuple[str, ...]] = Counter()
    for binding, target in target_by_binding.items():
        target_groups = groups_by_target.get(binding, [])
        maximum_sources = max(
            (len(groups[pair]) for pair in target_groups), default=0
        )
        backed = sum(pair in projection_backed for pair in target_groups)
        proposals = sum(pair in proposal_pairs for pair in target_groups)
        changed_value = changes.get(binding)
        if changed_value is None:
            target_change = "unchanged"
        elif any(
            pair in proposal_pairs and pair[1] == changed_value
            for pair in target_groups
        ):
            target_change = "changed_to_unconflicted_proposal"
        else:
            target_change = "changed_other"
        target_rows[
            (
                "unknown" if target.baseline_unknown else "known",
                _bucket(len(target_groups)),
                _bucket(maximum_sources),
                _bucket(backed),
                _bucket(proposals),
                target_change,
            )
        ] += 1

    unknown_groups = sum(
        target_by_binding[pair[0]].baseline_unknown for pair in groups
    )
    unknown_single = sum(
        target_by_binding[pair[0]].baseline_unknown and len(sources) == 1
        for pair, sources in groups.items()
    )
    unknown_multi = sum(
        target_by_binding[pair[0]].baseline_unknown and len(sources) >= 2
        for pair, sources in groups.items()
    )
    counts = {
        "target_count": len(targets),
        "unknown_target_count": sum(target.baseline_unknown for target in targets),
        "zero_projection_target_count": sum(
            not groups_by_target.get(binding) for binding in target_by_binding
        ),
        "projection_group_count": len(groups),
        "unknown_projection_group_count": unknown_groups,
        "unknown_single_source_projection_group_count": unknown_single,
        "unknown_two_or_more_source_projection_group_count": unknown_multi,
        "catalog_candidate_group_count": int(
            validated["active_catalog"]["base_catalog"][
                "candidate_groups_considered"
            ]
        ),
        "catalog_eligible_support_set_count": int(
            validated["active_catalog"]["base_catalog"][
                "eligible_support_set_count"
            ]
        ),
        "projection_backed_support_group_count": len(projection_backed),
        "unconflicted_unknown_proposal_group_count": len(proposal_pairs),
        "changed_target_count": len(changes),
        "changed_to_projected_value_group_count": changed_to_projected,
        "strict_joint_safe_change_group_count": strict_joint,
    }
    task_local = {
        "has_unknown_target": counts["unknown_target_count"] > 0,
        "has_unknown_projection_group": unknown_groups > 0,
        "has_unknown_two_or_more_source_projection_group": unknown_multi > 0,
        "has_projection_backed_support_group": len(projection_backed) > 0,
        "has_unconflicted_unknown_proposal_group": len(proposal_pairs) > 0,
        "has_changed_target": len(changes) > 0,
        "has_strict_joint_safe_change_group": strict_joint > 0,
    }
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        **counts,
        "catalog_disposition_counts": {
            name: int(catalog_counts[name]) for name in CATALOG_DISPOSITIONS
        },
        "catalog_quarantine_disposition_counts": {
            name: int(
                validated["active_catalog"]["base_catalog"][
                    "quarantined_candidate_groups"
                ].get(name, 0)
            )
            for name in CATALOG_QUARANTINE_DISPOSITIONS
        },
        "proposal_disposition_counts": {
            name: int(proposal_counts[name]) for name in PROPOSAL_DISPOSITIONS
        },
        "group_change_disposition_counts": {
            name: int(group_change_counts[name])
            for name in GROUP_CHANGE_DISPOSITIONS
        },
        "target_cross_tab": _sorted_rows(
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
        "projection_group_cross_tab": _sorted_rows(
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
        "projection_group_partition_exact": sum(group_rows.values())
        == len(groups),
        "target_partition_exact": sum(target_rows.values()) == len(targets),
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
    return value


def build_projection_support_cross_tab(
    catalog: Mapping[str, Any], baseline: str, candidate: str
) -> dict[str, Any]:
    frozen_catalog = copy.deepcopy(dict(catalog))
    baseline_before = str(baseline)
    candidate_before = str(candidate)
    value = validate_receipt(_compute(catalog, baseline, candidate))
    if (
        dict(catalog) != frozen_catalog
        or str(baseline) != baseline_before
        or str(candidate) != candidate_before
    ):
        raise RuntimeError("V2.47.86 observer mutated its private inputs")
    return value


def _valid_count_map(value: object, names: tuple[str, ...]) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == set(names)
        and all(
            not isinstance(amount, bool)
            and isinstance(amount, int)
            and amount >= 0
            for amount in value.values()
        )
    )


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    counts = {name: copied.get(name) for name in COUNT_FIELDS}
    target_rows = copied.get("target_cross_tab")
    group_rows = copied.get("projection_group_cross_tab")
    task_local = copied.get("task_local_joint")
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(amount, bool)
            or not isinstance(amount, int)
            or amount < 0
            for amount in counts.values()
        )
        or not _valid_count_map(
            copied.get("catalog_disposition_counts"), CATALOG_DISPOSITIONS
        )
        or not _valid_count_map(
            copied.get("catalog_quarantine_disposition_counts"),
            CATALOG_QUARANTINE_DISPOSITIONS,
        )
        or not _valid_count_map(
            copied.get("proposal_disposition_counts"), PROPOSAL_DISPOSITIONS
        )
        or not _valid_count_map(
            copied.get("group_change_disposition_counts"),
            GROUP_CHANGE_DISPOSITIONS,
        )
        or not isinstance(target_rows, list)
        or not isinstance(group_rows, list)
        or not isinstance(task_local, Mapping)
        or set(task_local) != TASK_LOCAL_JOINT_KEYS
        or any(not isinstance(flag, bool) for flag in task_local.values())
        or copied.get("catalog_candidate_and_quarantine_replay_exact") is not True
        or copied.get("projection_group_partition_exact") is not True
        or copied.get("target_partition_exact") is not True
        or copied.get("candidate_changes_only_baseline_unknown_cells") is not True
        or copied.get("same_catalog_and_predictions_observed_without_mutation")
        is not True
        or copied.get("cross_task_or_cross_group_margins_used_as_joint") is not False
        or copied.get("positive_entropy_or_task_credit_assigned") is not False
        or copied.get(
            "question_task_identity_field_value_query_url_host_page_prediction_or_private_content_hash_emitted"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get(
            "file_environment_network_model_search_fetch_process_or_evaluator_accessed"
        )
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.86 cross-tab receipt drifted")

    seen_target_rows: set[tuple[Any, ...]] = set()
    for row in target_rows:
        if (
            not isinstance(row, Mapping)
            or set(row) != TARGET_ROW_KEYS
            or row.get("baseline_state") not in BASELINE_STATES
            or row.get("projected_value_group_count")
            not in TARGET_PROJECTION_BUCKETS
            or row.get("maximum_projection_source_multiplicity")
            not in TARGET_PROJECTION_BUCKETS
            or row.get("projection_backed_support_group_count")
            not in TARGET_PROJECTION_BUCKETS
            or row.get("unconflicted_proposal_group_count")
            not in TARGET_PROJECTION_BUCKETS
            or row.get("candidate_change") not in TARGET_CHANGE_DISPOSITIONS
            or isinstance(row.get("count"), bool)
            or not isinstance(row.get("count"), int)
            or row["count"] <= 0
        ):
            raise ValueError("V2.47.86 target cross-tab row drifted")
        identity = tuple(row[name] for name in sorted(TARGET_ROW_KEYS - {"count"}))
        if identity in seen_target_rows:
            raise ValueError("V2.47.86 duplicate target cross-tab row")
        seen_target_rows.add(identity)
        if (
            row["projected_value_group_count"] == "zero"
            and any(
                row[name] != "zero"
                for name in (
                    "maximum_projection_source_multiplicity",
                    "projection_backed_support_group_count",
                    "unconflicted_proposal_group_count",
                )
            )
            or row["baseline_state"] == "known"
            and row["unconflicted_proposal_group_count"] != "zero"
            or row["baseline_state"] == "known"
            and row["candidate_change"] != "unchanged"
            or row["projection_backed_support_group_count"] == "zero"
            and row["unconflicted_proposal_group_count"] != "zero"
            or row["candidate_change"] == "changed_to_unconflicted_proposal"
            and (
                row["baseline_state"] != "unknown"
                or row["unconflicted_proposal_group_count"] == "zero"
            )
        ):
            raise ValueError("V2.47.86 target cross-tab semantics drifted")

    seen_group_rows: set[tuple[Any, ...]] = set()
    for row in group_rows:
        if (
            not isinstance(row, Mapping)
            or set(row) != GROUP_ROW_KEYS
            or row.get("baseline_state") not in BASELINE_STATES
            or row.get("projection_source_multiplicity")
            not in SOURCE_MULTIPLICITIES
            or row.get("catalog_disposition") not in CATALOG_DISPOSITIONS
            or row.get("proposal_disposition") not in PROPOSAL_DISPOSITIONS
            or row.get("candidate_change") not in GROUP_CHANGE_DISPOSITIONS
            or isinstance(row.get("count"), bool)
            or not isinstance(row.get("count"), int)
            or row["count"] <= 0
        ):
            raise ValueError("V2.47.86 projection cross-tab row drifted")
        identity = tuple(row[name] for name in sorted(GROUP_ROW_KEYS - {"count"}))
        if identity in seen_group_rows:
            raise ValueError("V2.47.86 duplicate projection cross-tab row")
        seen_group_rows.add(identity)
        proposal = row["proposal_disposition"]
        if (
            (proposal == "not_unknown") != (row["baseline_state"] == "known")
            or proposal == "catalog_blocked"
            and row["catalog_disposition"] == "eligible_support"
            or proposal
            in {
                "eligible_not_projection_backed",
                "projection_value_conflict",
                "unconflicted_projection_backed_unknown_proposal",
            }
            and row["catalog_disposition"] != "eligible_support"
            or proposal
            in {
                "projection_value_conflict",
                "unconflicted_projection_backed_unknown_proposal",
            }
            and row["projection_source_multiplicity"] != "two_or_more"
        ):
            raise ValueError("V2.47.86 projection cross-tab semantics drifted")

    target_total = sum(row["count"] for row in target_rows)
    group_total = sum(row["count"] for row in group_rows)
    catalog_from_rows = Counter()
    proposal_from_rows = Counter()
    group_change_from_rows = Counter()
    for row in group_rows:
        catalog_from_rows[row["catalog_disposition"]] += row["count"]
        proposal_from_rows[row["proposal_disposition"]] += row["count"]
        group_change_from_rows[row["candidate_change"]] += row["count"]
    strict_joint = sum(
        row["count"]
        for row in group_rows
        if row["baseline_state"] == "unknown"
        and row["projection_source_multiplicity"] == "two_or_more"
        and row["catalog_disposition"] == "eligible_support"
        and row["proposal_disposition"]
        == "unconflicted_projection_backed_unknown_proposal"
        and row["candidate_change"] == "changed_to_this_projection_value"
    )
    changed_targets = sum(
        row["count"] for row in target_rows if row["candidate_change"] != "unchanged"
    )
    zero_targets = sum(
        row["count"]
        for row in target_rows
        if row["projected_value_group_count"] == "zero"
    )
    unknown_groups = sum(
        row["count"]
        for row in group_rows
        if row["baseline_state"] == "unknown"
    )
    unknown_single = sum(
        row["count"]
        for row in group_rows
        if row["baseline_state"] == "unknown"
        and row["projection_source_multiplicity"] == "one"
    )
    unknown_multi = sum(
        row["count"]
        for row in group_rows
        if row["baseline_state"] == "unknown"
        and row["projection_source_multiplicity"] == "two_or_more"
    )
    unknown_targets = sum(
        row["count"]
        for row in target_rows
        if row["baseline_state"] == "unknown"
    )
    projection_backed = sum(
        row["count"]
        for row in group_rows
        if row["baseline_state"] == "unknown"
        and row["catalog_disposition"] == "eligible_support"
        and row["proposal_disposition"]
        in {
            "projection_value_conflict",
            "unconflicted_projection_backed_unknown_proposal",
        }
    )
    full_quarantine_total = sum(
        copied["catalog_quarantine_disposition_counts"].values()
    )
    if (
        target_total != copied["target_count"]
        or group_total != copied["projection_group_count"]
        or unknown_targets != copied["unknown_target_count"]
        or unknown_groups != copied["unknown_projection_group_count"]
        or unknown_single
        != copied["unknown_single_source_projection_group_count"]
        or unknown_multi
        != copied["unknown_two_or_more_source_projection_group_count"]
        or zero_targets != copied["zero_projection_target_count"]
        or changed_targets != copied["changed_target_count"]
        or sum(copied["catalog_disposition_counts"].values()) != group_total
        or sum(copied["proposal_disposition_counts"].values()) != group_total
        or sum(copied["group_change_disposition_counts"].values()) != group_total
        or any(
            copied["catalog_disposition_counts"][name] != catalog_from_rows[name]
            for name in CATALOG_DISPOSITIONS
        )
        or any(
            copied["proposal_disposition_counts"][name] != proposal_from_rows[name]
            for name in PROPOSAL_DISPOSITIONS
        )
        or any(
            copied["group_change_disposition_counts"][name]
            != group_change_from_rows[name]
            for name in GROUP_CHANGE_DISPOSITIONS
        )
        or copied["catalog_candidate_group_count"]
        != copied["catalog_eligible_support_set_count"] + full_quarantine_total
        or projection_backed != copied["projection_backed_support_group_count"]
        or copied["unknown_target_count"] > copied["target_count"]
        or copied["zero_projection_target_count"] > copied["target_count"]
        or copied["unknown_projection_group_count"]
        > copied["projection_group_count"]
        or copied["projection_backed_support_group_count"]
        > min(
            copied["projection_group_count"],
            copied["catalog_eligible_support_set_count"],
        )
        or copied["unconflicted_unknown_proposal_group_count"]
        != copied["proposal_disposition_counts"][
            "unconflicted_projection_backed_unknown_proposal"
        ]
        or copied["unconflicted_unknown_proposal_group_count"]
        > copied["projection_backed_support_group_count"]
        or copied["changed_to_projected_value_group_count"]
        != copied["group_change_disposition_counts"][
            "changed_to_this_projection_value"
        ]
        or copied["changed_target_count"] > copied["unknown_target_count"]
        or copied["changed_to_projected_value_group_count"]
        > copied["changed_target_count"]
        or copied["strict_joint_safe_change_group_count"] != strict_joint
        or copied["strict_joint_safe_change_group_count"]
        > min(
            copied["changed_to_projected_value_group_count"],
            copied["unconflicted_unknown_proposal_group_count"],
        )
        or task_local
        != {
            "has_unknown_target": copied["unknown_target_count"] > 0,
            "has_unknown_projection_group": copied[
                "unknown_projection_group_count"
            ]
            > 0,
            "has_unknown_two_or_more_source_projection_group": copied[
                "unknown_two_or_more_source_projection_group_count"
            ]
            > 0,
            "has_projection_backed_support_group": copied[
                "projection_backed_support_group_count"
            ]
            > 0,
            "has_unconflicted_unknown_proposal_group": copied[
                "unconflicted_unknown_proposal_group_count"
            ]
            > 0,
            "has_changed_target": copied["changed_target_count"] > 0,
            "has_strict_joint_safe_change_group": strict_joint > 0,
        }
    ):
        raise ValueError("V2.47.86 cross-tab conservation drifted")
    return copied


__all__ = [
    "CATALOG_DISPOSITIONS",
    "CATALOG_QUARANTINE_DISPOSITIONS",
    "GROUP_CHANGE_DISPOSITIONS",
    "POLICY_ID",
    "PROPOSAL_DISPOSITIONS",
    "ROLE",
    "build_projection_support_cross_tab",
    "validate_receipt",
]
