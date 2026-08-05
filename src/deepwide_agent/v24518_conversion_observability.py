"""Content-free observability for usable-page to observation conversion.

V2.45.17 produced usable targeted/reserve pages but no target-bound
observation.  The historical private pages were correctly deleted, so that
run cannot distinguish source-selection failure from conservative projection
rejection.  This pure successor classifies each newly fetched
page/selected-target pair while the private, fully validated V2.45.03 result
is still in the trusted child.

Only fixed-vocabulary counts leave the private boundary.  No task, question,
opaque id, row, column, value, query, URL, host, page text, source identity,
prediction, or private-content hash is emitted.  The classifier does not
alter the parent result, perform an external effect, or relax any projection,
source-count, posterior, margin, leave-one-out, or decision-credit rule.
"""

from __future__ import annotations

import copy
import re
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24365_entity_segment_projection as segment
from . import v24390_uncertainty_active_evidence_runtime as runtime
from . import v24405_structured_label_projection as structured
from . import v24428_unique_title_anchor_projection as title
from . import v24436_narrative_title_anchor_projection as narrative
from . import v24457_adaptive_entropy_support as adaptive
from . import v24490_entropy_targeted_support_search as targeted
from . import v24496_targeted_reserve_contradiction as reserve
from . import v24502_record_bound_title_projection as record
from . import v24503_record_bound_reserve_integration as integration
from . import v24504_proof_carrying_record_bound_reserve as proof
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24333_programmatic_support_catalog import CellTarget, _normalize, _source_key


POLICY_ID = "v24518_content_free_page_observation_conversion_observability_v1"
ROLE = "v24518_page_observation_conversion_receipt"
SCOPES = ("targeted", "reserve")
REASONS = (
    "new_observation_emitted",
    "projection_duplicate_parent_observation",
    "projection_rejected_source_ambiguity",
    "projection_rejected_post_projection_safety",
    "no_projection_unsupported_column_kind",
    "no_projection_multiple_distinct_candidate_years",
    "no_projection_unique_title_anchor_bound_to_other_visible_row",
    "no_projection_exact_entity_and_unique_title_anchor_absent_or_ambiguous",
    "no_projection_explicit_relation_absent",
    "no_projection_relation_present_but_candidate_year_absent",
    "no_projection_candidate_year_present_but_safety_rejected",
)
ROUTES = (
    "entity_segment",
    "structured_label_value",
    "unique_title_label_value",
    "unique_title_narrative",
    "unique_title_split_record",
)
SIGNAL_COUNT_FIELDS = (
    "exact_body_entity_anchor_pair_count",
    "unique_target_title_anchor_pair_count",
    "unique_other_row_title_anchor_pair_count",
    "ambiguous_or_absent_title_anchor_pair_count",
    "target_anchor_pair_count",
    "explicit_relation_signal_pair_count",
    "multiple_distinct_candidate_year_pair_count",
    "grammar_projection_pair_count",
    "new_observation_pair_count",
    "zero_projection_pair_count",
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "targeted_usable_page_count",
        "reserve_usable_page_count",
        "usable_page_count",
        "selected_target_count",
        "page_target_pair_count",
        "scope_pair_counts",
        "reason_counts",
        "route_pair_counts",
        *SIGNAL_COUNT_FIELDS,
        "reason_partition_exact",
        "route_counts_are_marginal_not_partition",
        "same_frozen_targeted_and_reserve_pages_replayed",
        "parent_prediction_and_decision_state_unchanged",
        "projection_source_posterior_margin_and_credit_rules_unchanged",
        "counts_only_no_task_question_opaque_id_entity_column_value_query_url_page_source_prediction_or_private_content_hash",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)


def _pair_identity(target: CellTarget) -> tuple[str, str]:
    return runtime._target_identity(target.row_key, target.column)


def _observation_key(value: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return integration._observation_key(value)


def _target_observations(
    values: Sequence[Mapping[str, Any]], target: CellTarget
) -> list[dict[str, Any]]:
    identity = _pair_identity(target)
    return [
        copy.deepcopy(dict(item))
        for item in values
        if runtime._target_identity(item["row_key"], item["column"]) == identity
    ]


def _body_signals(
    page: Mapping[str, Any], target: CellTarget, cells: Sequence[CellTarget]
) -> tuple[bool, bool, bool, set[str]]:
    content = unicodedata.normalize("NFKC", str(page["content"]))
    mentions = segment._mentions(content, cells)
    exact_anchor = any(
        item.target_binding_sha256 == target.binding_sha256 for item in mentions
    )
    kind = segment._column_kind(target.column)
    values: set[str] = set()
    relation_token = False
    if kind is not None:
        for current in segment._segments_for_target(content, target, mentions):
            pattern = segment.YEAR_RELATIONS.get(kind)
            if pattern is not None and re.search(
                pattern, current.text, flags=re.IGNORECASE
            ):
                relation_token = True
            for relation, _direction, _distance in segment._bound_relations(
                current, kind
            ):
                normalized = _normalize(relation.value)
                if normalized:
                    values.add(normalized)
    return exact_anchor, relation_token, bool(values), values


def _record_signals(
    page: Mapping[str, Any],
    target: CellTarget,
    *,
    rows: Sequence[tuple[str, tuple[str, ...]]],
) -> tuple[bool, set[str]]:
    """Return exact-label signal and all adjacent candidate years.

    This is diagnostic only.  Admission still belongs exclusively to the
    frozen V2.45.02 projector.  Reading every year after an accepted label
    lets the receipt distinguish an absent relation from a conservative
    multiple-year or record-safety rejection without admitting that value.
    """

    anchor = title._unique_title_row(
        str(page["title"]), record._row_cells(rows)
    )
    if anchor is None or runtime._target_identity(anchor[0], "")[0] != _pair_identity(
        target
    )[0]:
        return False, set()
    labels = structured._accepted_labels(target)
    if not labels:
        return False, set()
    lines = unicodedata.normalize("NFKC", str(page["content"])).splitlines()
    label_signal = False
    values: set[str] = set()
    for index, line in enumerate(lines[: title.MAXIMUM_TITLE_RECORD_LINES]):
        if record._other_visible_row_present(
            line, anchored_row=anchor[0], rows=rows
        ):
            break
        label = record._label_only(line, labels)
        if label is None:
            continue
        label_signal = True
        stop = min(
            len(lines),
            index + 1 + record.MAXIMUM_RECORD_LINE_GAP,
            title.MAXIMUM_TITLE_RECORD_LINES,
        )
        for value_index in range(index + 1, stop):
            value_line = lines[value_index]
            if not value_line.strip():
                continue
            if record._other_visible_row_present(
                value_line, anchored_row=anchor[0], rows=rows
            ) or record._label_only(value_line, labels) is not None:
                break
            values.update(
                _normalize(match.group(1))
                for match in structured.YEAR.finditer(value_line)
            )
            break
    return label_signal, {value for value in values if value}


def _route_pairs(
    catalog: Mapping[str, Any],
    target: CellTarget,
    *,
    body_relation: bool,
) -> dict[str, bool]:
    binding = target.binding_sha256
    parent_narrative = catalog["parent_projection"]
    parent_title = parent_narrative["parent_projection"]
    parent_structured = parent_title["parent_projection"]
    return {
        "entity_segment": body_relation,
        "structured_label_value": any(
            item["target_binding_sha256"] == binding
            for item in parent_structured["structured_projections"]
        ),
        "unique_title_label_value": any(
            item["target_binding_sha256"] == binding
            for item in parent_title["title_anchor_projections"]
        ),
        "unique_title_narrative": any(
            item["target_binding_sha256"] == binding
            for item in catalog["admitted_parent_narrative_projections"]
        ),
        "unique_title_split_record": any(
            item["target_binding_sha256"] == binding
            for item in catalog["record_bound_projections"]
        ),
    }


def _pair_diagnosis(
    page: Mapping[str, Any],
    target: CellTarget,
    *,
    cells: Sequence[CellTarget],
    rows: Sequence[tuple[str, tuple[str, ...]]],
    page_catalog: Mapping[str, Any],
    before_keys: set[tuple[str, str, str, str]],
    after_keys: set[tuple[str, str, str, str]],
    full_title_source_counts: Counter[tuple[str, str]],
) -> tuple[str, dict[str, bool], dict[str, bool]]:
    identity = _pair_identity(target)
    exact_body, body_relation_token, body_relation, body_values = _body_signals(
        page, target, cells
    )
    title_anchor = title._unique_title_row(str(page["title"]), cells)
    target_title = (
        title_anchor is not None
        and runtime._target_identity(title_anchor[0], "")[0] == identity[0]
    )
    other_title = title_anchor is not None and not target_title
    narrative_reason, narrative_relations, _tokens = narrative._narrative_relations(
        page, target, all_rows=rows
    )
    record_label, record_values = _record_signals(page, target, rows=rows)
    narrative_values = {
        _normalize(value) for value, _ordinal, _kind in narrative_relations
    }
    candidate_values = body_values | record_values | narrative_values
    relation_signal = (
        body_relation_token or record_label or bool(narrative_relations)
    )
    routes = _route_pairs(page_catalog, target, body_relation=body_relation)
    relation_signal = relation_signal or any(routes.values())
    observations = _target_observations(page_catalog["observations"], target)
    candidate_keys = {_observation_key(item) for item in observations}
    protected = _target_observations(
        [
            *page_catalog["admitted_parent_narrative_projections"],
            *page_catalog["record_bound_projections"],
        ],
        target,
    )
    protected_keys = {_observation_key(item) for item in protected}
    new_keys = after_keys - before_keys
    source_identity = (_source_key(str(page["host"])), identity[0])
    source_ambiguous = (
        bool(candidate_keys & protected_keys)
        and full_title_source_counts[source_identity] != 1
    )
    kind_supported = (
        segment._column_kind(target.column) in segment.YEAR_RELATIONS
        and bool(structured._accepted_labels(target))
    )

    if candidate_keys & new_keys:
        reason = "new_observation_emitted"
    elif candidate_keys & before_keys:
        reason = "projection_duplicate_parent_observation"
    elif candidate_keys and source_ambiguous:
        reason = "projection_rejected_source_ambiguity"
    elif candidate_keys:
        reason = "projection_rejected_post_projection_safety"
    elif not kind_supported:
        reason = "no_projection_unsupported_column_kind"
    elif len(candidate_values) > 1 or narrative_reason == (
        "multiple_distinct_narrative_years"
    ):
        reason = "no_projection_multiple_distinct_candidate_years"
    elif not exact_body and other_title:
        reason = "no_projection_unique_title_anchor_bound_to_other_visible_row"
    elif not exact_body and not target_title:
        reason = (
            "no_projection_exact_entity_and_unique_title_anchor_absent_or_ambiguous"
        )
    elif not relation_signal:
        reason = "no_projection_explicit_relation_absent"
    elif not candidate_values:
        reason = "no_projection_relation_present_but_candidate_year_absent"
    else:
        reason = "no_projection_candidate_year_present_but_safety_rejected"

    signals = {
        "exact_body_entity_anchor": exact_body,
        "unique_target_title_anchor": target_title,
        "unique_other_row_title_anchor": other_title,
        "ambiguous_or_absent_title_anchor": title_anchor is None,
        "target_anchor": exact_body or target_title,
        "explicit_relation_signal": relation_signal,
        "multiple_distinct_candidate_year": len(candidate_values) > 1,
        "grammar_projection": bool(candidate_keys),
        "new_observation": bool(candidate_keys & new_keys),
        "zero_projection": not candidate_keys,
    }
    return reason, routes, signals


def _private_inputs(
    validated: Mapping[str, Any],
) -> tuple[
    str,
    list[CellTarget],
    list[tuple[str, dict[str, Any]]],
    set[tuple[str, str, str, str]],
    set[tuple[str, str, str, str]],
    Counter[tuple[str, str]],
]:
    # The caller must supply the result owned by one already-completed typed
    # V2.45.03 validation.  Do not recursively invoke V2.45.03 here: doing so
    # would duplicate the complete semantic validation that the capability is
    # specifically designed to attest.  The three parent layers below still
    # pass through the execution-scoped high-level memo and therefore compare
    # exact bytes and recursive type shape against their first validation.
    unsigned = dict(validated)
    seal = unsigned.pop("result_sha256", None)
    if (
        set(validated) != integration.RESULT_KEYS
        or validated.get("artifact_version") != 1
        or validated.get("role") != integration.RESULT_ROLE
        or validated.get("policy_id") != integration.POLICY_ID
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.45.18 typed record-bound result shell drifted")
    validated_parent = reserve.validate_result(validated["parent_result"])
    targeted_result = targeted.validate_result(validated_parent["parent_result"])
    adaptive_result = adaptive.validate_result(targeted_result["parent_result"])
    original = adaptive._original_parent_result(adaptive_result["parent_result"])
    anchored = original["parent_result"]
    structured_result = anchored["parent_result"]
    legacy = structured_result["parent_result"]
    baseline = str(legacy["baseline_prediction"])
    catalog = integration.validate_uncertainty_catalog(
        legacy["private_replay_state"]["uncertainty_catalog"]
    )
    selected_identities = adaptive._selected_identities(catalog)
    all_cells = runtime._baseline_cells(baseline)
    selected = [
        cell for cell in all_cells if _pair_identity(cell) in selected_identities
    ]
    pages: list[tuple[str, dict[str, Any]]] = []
    for scope, raw_pages in (
        ("targeted", targeted_result["targeted_private_state"]["targeted_pages"]),
        ("reserve", validated_parent["reserve_private_state"]["reserve_pages"]),
    ):
        for page in raw_pages:
            pages.append((scope, title._plain_titled_page(page)))
    before = validated_parent["reserve_active_evidence_result"][
        "active_observations"
    ]
    after = validated["record_bound_active_evidence_result"][
        "active_observations"
    ]
    before_keys = {_observation_key(item) for item in before}
    after_keys = {_observation_key(item) for item in after}
    title_counts = integration._title_source_counts(
        validated["record_bound_projection"], baseline
    )
    return baseline, selected, pages, before_keys, after_keys, title_counts


def _compute_from_validated(validated: Mapping[str, Any]) -> dict[str, Any]:
    (
        baseline,
        selected,
        pages,
        before_keys,
        after_keys,
        title_counts,
    ) = _private_inputs(validated)
    cells = runtime._baseline_cells(baseline)
    rows = title._visible_rows(cells)
    selected_identities = {_pair_identity(cell) for cell in selected}
    reasons: Counter[str] = Counter()
    route_counts: Counter[str] = Counter()
    signal_counts: Counter[str] = Counter()
    scope_counts: Counter[str] = Counter()
    for scope, page in pages:
        page_catalog = record.build_record_bound_title_projection(
            baseline,
            [page],
            selected_identities=selected_identities,
        )
        for target in selected:
            reason, routes, signals = _pair_diagnosis(
                page,
                target,
                cells=cells,
                rows=rows,
                page_catalog=page_catalog,
                before_keys=before_keys,
                after_keys=after_keys,
                full_title_source_counts=title_counts,
            )
            reasons[reason] += 1
            scope_counts[scope] += 1
            for name, present in routes.items():
                route_counts[name] += int(present)
            for name, present in signals.items():
                signal_counts[name] += int(present)
    reason_counts = {name: int(reasons[name]) for name in REASONS}
    route_pair_counts = {name: int(route_counts[name]) for name in ROUTES}
    scope_pair_counts = {name: int(scope_counts[name]) for name in SCOPES}
    page_count = len(pages)
    pair_count = page_count * len(selected)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "targeted_usable_page_count": sum(
            scope == "targeted" for scope, _page in pages
        ),
        "reserve_usable_page_count": sum(
            scope == "reserve" for scope, _page in pages
        ),
        "usable_page_count": page_count,
        "selected_target_count": len(selected),
        "page_target_pair_count": pair_count,
        "scope_pair_counts": scope_pair_counts,
        "reason_counts": reason_counts,
        "route_pair_counts": route_pair_counts,
        "exact_body_entity_anchor_pair_count": int(
            signal_counts["exact_body_entity_anchor"]
        ),
        "unique_target_title_anchor_pair_count": int(
            signal_counts["unique_target_title_anchor"]
        ),
        "unique_other_row_title_anchor_pair_count": int(
            signal_counts["unique_other_row_title_anchor"]
        ),
        "ambiguous_or_absent_title_anchor_pair_count": int(
            signal_counts["ambiguous_or_absent_title_anchor"]
        ),
        "target_anchor_pair_count": int(signal_counts["target_anchor"]),
        "explicit_relation_signal_pair_count": int(
            signal_counts["explicit_relation_signal"]
        ),
        "multiple_distinct_candidate_year_pair_count": int(
            signal_counts["multiple_distinct_candidate_year"]
        ),
        "grammar_projection_pair_count": int(
            signal_counts["grammar_projection"]
        ),
        "new_observation_pair_count": int(signal_counts["new_observation"]),
        "zero_projection_pair_count": int(signal_counts["zero_projection"]),
        "reason_partition_exact": sum(reason_counts.values()) == pair_count,
        "route_counts_are_marginal_not_partition": True,
        "same_frozen_targeted_and_reserve_pages_replayed": True,
        "parent_prediction_and_decision_state_unchanged": True,
        "projection_source_posterior_margin_and_credit_rules_unchanged": True,
        "counts_only_no_task_question_opaque_id_entity_column_value_query_url_page_source_prediction_or_private_content_hash": True,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    return value


def build_from_validated_execution(
    completed: proof.ValidatedRecordBoundExecution,
) -> dict[str, Any]:
    """Trusted-child entry after V2.45.03 complete validation already ran."""

    if not isinstance(completed, proof.ValidatedRecordBoundExecution):
        raise TypeError("V2.45.18 requires a validated record-bound execution")
    value = _compute_from_validated(
        completed._trusted_outcome().record_bound_result
    )
    validate_conversion_observability(value)
    return value


def validate_conversion_observability(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    reasons = copied.get("reason_counts")
    routes = copied.get("route_pair_counts")
    scopes = copied.get("scope_pair_counts")
    count_fields = (
        "targeted_usable_page_count",
        "reserve_usable_page_count",
        "usable_page_count",
        "selected_target_count",
        "page_target_pair_count",
        *SIGNAL_COUNT_FIELDS,
    )
    true_fields = (
        "reason_partition_exact",
        "route_counts_are_marginal_not_partition",
        "same_frozen_targeted_and_reserve_pages_replayed",
        "parent_prediction_and_decision_state_unchanged",
        "projection_source_posterior_margin_and_credit_rules_unchanged",
        "counts_only_no_task_question_opaque_id_entity_column_value_query_url_page_source_prediction_or_private_content_hash",
    )
    false_fields = (
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in count_fields
        )
        or not isinstance(reasons, Mapping)
        or set(reasons) != set(REASONS)
        or any(
            isinstance(reasons.get(name), bool)
            or not isinstance(reasons.get(name), int)
            or reasons[name] < 0
            for name in REASONS
        )
        or not isinstance(routes, Mapping)
        or set(routes) != set(ROUTES)
        or any(
            isinstance(routes.get(name), bool)
            or not isinstance(routes.get(name), int)
            or routes[name] < 0
            or routes[name] > copied.get("page_target_pair_count", -1)
            for name in ROUTES
        )
        or not isinstance(scopes, Mapping)
        or set(scopes) != set(SCOPES)
        or any(
            isinstance(scopes.get(name), bool)
            or not isinstance(scopes.get(name), int)
            or scopes[name] < 0
            for name in SCOPES
        )
        or copied["usable_page_count"]
        != copied["targeted_usable_page_count"]
        + copied["reserve_usable_page_count"]
        or copied["page_target_pair_count"]
        != copied["usable_page_count"] * copied["selected_target_count"]
        or scopes["targeted"]
        != copied["targeted_usable_page_count"] * copied["selected_target_count"]
        or scopes["reserve"]
        != copied["reserve_usable_page_count"] * copied["selected_target_count"]
        or sum(reasons.values()) != copied["page_target_pair_count"]
        or copied["grammar_projection_pair_count"]
        + copied["zero_projection_pair_count"]
        != copied["page_target_pair_count"]
        or copied["new_observation_pair_count"]
        != reasons["new_observation_emitted"]
        or copied["grammar_projection_pair_count"]
        != sum(
            reasons[name]
            for name in REASONS
            if not name.startswith("no_projection_")
        )
        or any(
            copied[name] > copied["page_target_pair_count"]
            for name in SIGNAL_COUNT_FIELDS
        )
        or copied["target_anchor_pair_count"]
        < copied["exact_body_entity_anchor_pair_count"]
        or copied["target_anchor_pair_count"]
        < copied["unique_target_title_anchor_pair_count"]
        or copied["unique_target_title_anchor_pair_count"]
        + copied["unique_other_row_title_anchor_pair_count"]
        + copied["ambiguous_or_absent_title_anchor_pair_count"]
        != copied["page_target_pair_count"]
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
        or not isinstance(seal, str)
        or re.fullmatch(r"[0-9a-f]{64}", seal) is None
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.45.18 conversion observability receipt drifted")
    return copied


__all__ = [
    "POLICY_ID",
    "REASONS",
    "RECEIPT_KEYS",
    "ROLE",
    "ROUTES",
    "SCOPES",
    "build_from_validated_execution",
    "validate_conversion_observability",
]
