"""Content-free observability for strict semantic projection conversion.

V2.47.80 recovered usable, independently attributable pages but produced no
projection-backed support set.  This append-only diagnostic runs inside a
future trusted child over a fully validated V2.43.65 private catalog.  It
partitions every page/target pair by the first failed conversion stage and
summarizes source closure from emitted projections to safe Unknown-cell
proposals.

Only fixed-vocabulary counts leave the private boundary.  The receipt contains
no task, question, identity, field, value, URL, host, page, prediction, or
private-content hash.  It changes no projector behavior, performs no external
effect, opens no benchmark label or evaluator surface, and assigns no entropy
or task credit.
"""

from __future__ import annotations

import copy
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Mapping
from typing import Any

from . import v24365_entity_segment_projection as segment
from . import v24743_generic_record_binding as binder
from .v24323_shared_prefix_cell_entropy import payload_sha256


POLICY_ID = "v24781_content_free_projection_conversion_funnel_v1"
ROLE = "v24781_projection_conversion_funnel_receipt"
REASONS = (
    "unsupported_column_kind",
    "exact_entity_anchor_absent",
    "target_segment_unavailable",
    "explicit_relation_absent",
    "relation_token_without_parsable_value",
    "parsable_relation_not_bound",
    "projection_emitted",
)
COUNT_FIELDS = (
    "target_count",
    "baseline_unknown_target_count",
    "core_page_count",
    "reserve_page_count",
    "input_page_count",
    "intact_page_count",
    "page_target_pair_count",
    "supported_column_pair_count",
    "exact_entity_anchor_pair_count",
    "target_segment_pair_count",
    "explicit_relation_token_pair_count",
    "parsable_relation_pair_count",
    "bound_relation_pair_count",
    "projection_emitted_pair_count",
    "semantic_projection_count",
    "distinct_target_value_projection_count",
    "projection_target_binding_count",
    "projection_unknown_target_value_group_count",
    "projection_single_source_group_count",
    "projection_two_or_more_source_group_count",
    "projection_conflicting_target_binding_count",
    "catalog_candidate_target_value_group_count",
    "catalog_eligible_support_set_count",
    "projection_backed_eligible_support_set_count",
    "unconflicted_projection_backed_unknown_proposal_count",
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        *COUNT_FIELDS,
        "reason_counts",
        "reason_partition_exact",
        "projection_source_partition_exact",
        "projection_receipt_replay_exact",
        "same_private_catalog_observed_without_projection_change",
        "frozen_projector_support_and_conflict_rules_unchanged",
        "counts_only_no_task_question_identity_field_value_query_url_host_page_prediction_or_private_content_hash",
        "positive_entropy_or_task_credit_assigned",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)


def _relation_token_present(text: str, kind: str) -> bool:
    if kind in segment.YEAR_RELATIONS:
        pattern = segment.YEAR_RELATIONS[kind]
    elif kind in {"headquarters_city", "headquarters_country", "city", "country"}:
        pattern = segment.LOCATION_RELATION
    elif kind == "elevation":
        pattern = (
            r"(?:architectural\s+height|elevation|height|above\s+sea\s+level|"
            r"海拔|高度)"
        )
    elif kind == "radius":
        pattern = r"(?:mean\s+radius|radius|平均半径|半径)"
    else:
        return False
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def _pair_reason(
    content: str,
    target: Any,
    all_mentions: list[Any],
) -> tuple[str, dict[str, bool]]:
    kind = segment._column_kind(target.column)
    anchor = any(
        item.target_binding_sha256 == target.binding_sha256
        for item in all_mentions
    )
    segments = (
        segment._segments_for_target(content, target, all_mentions)
        if anchor
        else []
    )
    token = bool(
        kind is not None
        and any(_relation_token_present(item.text, kind) for item in segments)
    )
    relations = (
        [relation for item in segments for relation in segment._relations(item.text, kind)]
        if kind is not None
        else []
    )
    bound = (
        [relation for item in segments for relation in segment._bound_relations(item, kind)]
        if kind is not None
        else []
    )
    if kind is None:
        reason = "unsupported_column_kind"
    elif not anchor:
        reason = "exact_entity_anchor_absent"
    elif not segments:
        reason = "target_segment_unavailable"
    elif bound:
        reason = "projection_emitted"
    elif relations:
        reason = "parsable_relation_not_bound"
    elif token:
        reason = "relation_token_without_parsable_value"
    else:
        reason = "explicit_relation_absent"
    return reason, {
        "supported_column": kind is not None,
        "exact_entity_anchor": anchor,
        "target_segment": bool(segments),
        "explicit_relation_token": token,
        "parsable_relation": bool(relations),
        "bound_relation": bool(bound),
    }


def _projection_closure(
    catalog: Mapping[str, Any], targets: list[Any]
) -> dict[str, int]:
    projections = catalog["projections"]
    pages_by_scope = {
        "core": catalog["original_core_pages"],
        "reserve": catalog["original_reserve_pages"],
    }
    sources: dict[tuple[str, str], set[str]] = defaultdict(set)
    values_by_target: dict[str, set[str]] = defaultdict(set)
    for item in projections:
        pages = pages_by_scope[str(item["scope"])]
        ordinal = int(item["page_ordinal"])
        if not 1 <= ordinal <= len(pages):
            raise ValueError("V2.47.81 projection page binding drifted")
        pair = (
            str(item["target_binding_sha256"]),
            str(item["normalized_value_sha256"]),
        )
        sources[pair].add(binder._source_key(str(pages[ordinal - 1]["host"])))
        values_by_target[pair[0]].add(pair[1])

    unknown_bindings = {
        target.binding_sha256 for target in targets if target.baseline_unknown
    }
    base = catalog["active_catalog"]["base_catalog"]
    projection_pairs = set(sources)
    grouped: dict[str, set[str]] = defaultdict(set)
    projection_backed = 0
    for support in base["support_sets"]:
        if support["baseline_cell_unknown"] is not True:
            continue
        pair = (
            str(support["target_binding_sha256"]),
            str(support["candidate_value_sha256"]),
        )
        if pair not in projection_pairs:
            continue
        support_sources = {
            str(item["source_key_sha256"])
            for item in support["evidence_source_bindings"]
        }
        projected_source_hashes = {
            segment._sha256_text(source) for source in sources[pair]
        }
        if (
            len(support_sources) < 2
            or not support_sources.issubset(projected_source_hashes)
        ):
            continue
        if (
            int(support["independent_source_count"]) < 2
            or int(support["required_source_count"]) < 2
        ):
            raise ValueError("V2.47.81 eligible support source count drifted")
        try:
            safe = binder._safe_text(support["candidate_value"])
        except ValueError:
            continue
        projection_backed += 1
        grouped[str(support["target_binding_sha256"])].add(
            binder._canonical_text(safe).casefold()
        )

    conflicts = {
        binding for binding, values in values_by_target.items() if len(values) > 1
    }
    proposals = sum(
        binding not in conflicts and len(values) == 1
        for binding, values in grouped.items()
    )
    return {
        "semantic_projection_count": len(projections),
        "distinct_target_value_projection_count": len(projection_pairs),
        "projection_target_binding_count": len(values_by_target),
        "projection_unknown_target_value_group_count": sum(
            binding in unknown_bindings for binding, _value in projection_pairs
        ),
        "projection_single_source_group_count": sum(
            len(group) == 1 for group in sources.values()
        ),
        "projection_two_or_more_source_group_count": sum(
            len(group) >= 2 for group in sources.values()
        ),
        "projection_conflicting_target_binding_count": len(conflicts),
        "catalog_candidate_target_value_group_count": int(
            base["candidate_groups_considered"]
        ),
        "catalog_eligible_support_set_count": int(
            base["eligible_support_set_count"]
        ),
        "projection_backed_eligible_support_set_count": projection_backed,
        "unconflicted_projection_backed_unknown_proposal_count": proposals,
    }


def _compute(catalog: Mapping[str, Any]) -> dict[str, Any]:
    validated = segment.validate_target_segment_catalog(catalog)
    targets = [segment._target(item) for item in validated["targets"]]
    reasons: Counter[str] = Counter()
    signals: Counter[str] = Counter()
    projection_pairs = {
        (
            str(item["scope"]),
            int(item["page_ordinal"]),
            str(item["target_binding_sha256"]),
        )
        for item in validated["projections"]
    }
    observed_projection_pairs: set[tuple[str, int, str]] = set()
    page_count = 0
    intact_pages = 0
    for scope, pages in (
        ("core", validated["original_core_pages"]),
        ("reserve", validated["original_reserve_pages"]),
    ):
        for ordinal, page in enumerate(pages, 1):
            page_count += 1
            intact_pages += int(page["fetch_integrity"] is True)
            content = unicodedata.normalize("NFKC", str(page["content"]))
            mentions = segment._mentions(content, targets)
            for target in targets:
                reason, pair_signals = _pair_reason(content, target, mentions)
                reasons[reason] += 1
                for name, present in pair_signals.items():
                    signals[name] += int(present)
                pair = (scope, ordinal, target.binding_sha256)
                emitted = pair in projection_pairs
                if emitted:
                    observed_projection_pairs.add(pair)
                if emitted is not (reason == "projection_emitted"):
                    raise ValueError("V2.47.81 projection pair replay drifted")

    closure = _projection_closure(validated, targets)
    reason_counts = {name: int(reasons[name]) for name in REASONS}
    pair_count = page_count * len(targets)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "target_count": len(targets),
        "baseline_unknown_target_count": sum(
            target.baseline_unknown for target in targets
        ),
        "core_page_count": len(validated["original_core_pages"]),
        "reserve_page_count": len(validated["original_reserve_pages"]),
        "input_page_count": page_count,
        "intact_page_count": intact_pages,
        "page_target_pair_count": pair_count,
        "supported_column_pair_count": int(signals["supported_column"]),
        "exact_entity_anchor_pair_count": int(signals["exact_entity_anchor"]),
        "target_segment_pair_count": int(signals["target_segment"]),
        "explicit_relation_token_pair_count": int(
            signals["explicit_relation_token"]
        ),
        "parsable_relation_pair_count": int(signals["parsable_relation"]),
        "bound_relation_pair_count": int(signals["bound_relation"]),
        "projection_emitted_pair_count": len(observed_projection_pairs),
        **closure,
        "reason_counts": reason_counts,
        "reason_partition_exact": sum(reason_counts.values()) == pair_count,
        "projection_source_partition_exact": (
            closure["projection_single_source_group_count"]
            + closure["projection_two_or_more_source_group_count"]
            == closure["distinct_target_value_projection_count"]
        ),
        "projection_receipt_replay_exact": observed_projection_pairs
        == projection_pairs,
        "same_private_catalog_observed_without_projection_change": True,
        "frozen_projector_support_and_conflict_rules_unchanged": True,
        "counts_only_no_task_question_identity_field_value_query_url_host_page_prediction_or_private_content_hash": True,
        "positive_entropy_or_task_credit_assigned": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    return value


def build_projection_conversion_funnel(
    catalog: Mapping[str, Any],
) -> dict[str, Any]:
    return validate_receipt(_compute(catalog))


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    counts = {name: copied.get(name) for name in COUNT_FIELDS}
    reasons = copied.get("reason_counts")
    pair_count = counts.get("page_target_pair_count")
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(amount, bool) or not isinstance(amount, int) or amount < 0
            for amount in counts.values()
        )
        or not isinstance(reasons, Mapping)
        or set(reasons) != set(REASONS)
        or any(
            isinstance(amount, bool) or not isinstance(amount, int) or amount < 0
            for amount in reasons.values()
        )
        or copied["input_page_count"]
        != copied["core_page_count"] + copied["reserve_page_count"]
        or copied["intact_page_count"] > copied["input_page_count"]
        or copied["baseline_unknown_target_count"] > copied["target_count"]
        or pair_count != copied["input_page_count"] * copied["target_count"]
        or sum(reasons.values()) != pair_count
        or copied.get("reason_partition_exact") is not True
        or copied["supported_column_pair_count"]
        != pair_count - reasons["unsupported_column_kind"]
        or copied["exact_entity_anchor_pair_count"]
        < copied["target_segment_pair_count"]
        or copied["target_segment_pair_count"]
        < copied["explicit_relation_token_pair_count"]
        or copied["target_segment_pair_count"]
        < copied["parsable_relation_pair_count"]
        or copied["parsable_relation_pair_count"]
        < copied["bound_relation_pair_count"]
        or copied["bound_relation_pair_count"]
        != copied["projection_emitted_pair_count"]
        or copied["projection_emitted_pair_count"]
        > copied["semantic_projection_count"]
        or copied["distinct_target_value_projection_count"]
        > copied["semantic_projection_count"]
        or copied["projection_target_binding_count"]
        > copied["distinct_target_value_projection_count"]
        or copied["projection_unknown_target_value_group_count"]
        > copied["distinct_target_value_projection_count"]
        or copied["projection_single_source_group_count"]
        + copied["projection_two_or_more_source_group_count"]
        != copied["distinct_target_value_projection_count"]
        or copied.get("projection_source_partition_exact") is not True
        or copied["projection_conflicting_target_binding_count"]
        > copied["projection_target_binding_count"]
        or copied["catalog_eligible_support_set_count"]
        > copied["catalog_candidate_target_value_group_count"]
        or copied["projection_backed_eligible_support_set_count"]
        > copied["catalog_eligible_support_set_count"]
        or copied["unconflicted_projection_backed_unknown_proposal_count"]
        > copied["projection_backed_eligible_support_set_count"]
        or copied.get("projection_receipt_replay_exact") is not True
        or copied.get("same_private_catalog_observed_without_projection_change")
        is not True
        or copied.get("frozen_projector_support_and_conflict_rules_unchanged")
        is not True
        or copied.get(
            "counts_only_no_task_question_identity_field_value_query_url_host_page_prediction_or_private_content_hash"
        )
        is not True
        or copied.get("positive_entropy_or_task_credit_assigned") is not False
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
        raise ValueError("V2.47.81 projection conversion receipt drifted")
    return copied


__all__ = [
    "COUNT_FIELDS",
    "POLICY_ID",
    "REASONS",
    "ROLE",
    "build_projection_conversion_funnel",
    "validate_receipt",
]
