"""Content-free rejection taxonomy for V2.44.05 structured projection.

The V2.44.19 external gate observed 26 active pages but no incremental
structured projection.  Its private pages were correctly deleted, so the
public result cannot distinguish unavailable structured patterns from parser
false negatives.  This pure successor classifies every page/selected-target
pair while the private catalog is still in memory.  Only aggregate counts are
returned; no entity, page, source, value, URL, text, or content hash is emitted.

The five reasons are mutually exclusive and collectively exhaustive relative
to the exact V2.44.05 grammar.  A prose mention such as ``Alpha was founded in
2007`` can still be a legacy observation, but it has no *structured exact
entity anchor* and is therefore classified separately from a parser-emitted
infobox/table projection.  The component performs no file, environment,
network, model, search, fetch, process, benchmark, evaluator, reward, or score
access.
"""

from __future__ import annotations

import copy
import re
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24405_structured_label_projection as base
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24390_uncertainty_active_evidence_runtime import _baseline_cells


POLICY_ID = "v24421_content_free_structured_projection_observability_v1"
ROLE = "v24421_structured_projection_observability"
REASONS = (
    "unsupported_column_kind",
    "exact_structured_entity_anchor_absent",
    "exact_label_absent_in_entity_scope",
    "exact_label_value_year_absent",
    "structured_projection_emitted",
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "page_count",
        "selected_target_count",
        "page_target_pair_count",
        "reason_counts",
        "structured_projection_pair_count",
        "structured_projection_count",
        "structured_observation_count",
        "novel_structured_observation_count",
        "structured_observation_duplicate_legacy_count",
        "legacy_observation_count",
        "combined_observation_count",
        "reason_partition_exact",
        "counts_only_no_task_page_entity_source_value_or_hash",
        "exact_v24405_grammar_replayed",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)


def _label_present(line: str, labels: frozenset[str]) -> bool:
    cells = base._cells(line)
    if cells is not None and len(cells) == 2:
        return base._label_equal(cells[0], labels)
    match = re.fullmatch(r"\s*([^:：\t]{1,120})\s*[:：\t]\s*(.*?)\s*", line)
    return match is not None and base._label_equal(match.group(1), labels)


def _pair_signals(
    lines: Sequence[str], target: Any, all_targets: Sequence[Any]
) -> tuple[bool, bool, bool, int]:
    """Return exact anchor, scoped label, labelled year, projection count."""

    labels = base._accepted_labels(target)
    if not labels:
        return False, False, False, 0
    anchor = False
    label = False
    year = False
    for index, line in enumerate(lines):
        cells = base._cells(line)
        if cells is not None and len(cells) >= 2 and base._entity_equal(
            cells[0], target.row_key
        ):
            anchor = True
        if cells is not None and len(cells) >= 3 and base._entity_equal(
            cells[0], target.row_key
        ):
            for label_index in range(1, len(cells) - 1):
                if not base._label_equal(cells[label_index], labels):
                    continue
                label = True
                if base._year(cells[label_index + 1]) is not None:
                    year = True
        if not base._entity_equal(line, target.row_key):
            continue
        anchor = True
        for next_index in range(
            index + 1,
            min(len(lines), index + 1 + base.MAXIMUM_ENTITY_RECORD_LINES),
        ):
            current = lines[next_index]
            if not current.strip():
                break
            if any(
                base._entity_equal(current, other.row_key)
                for other in all_targets
                if other.binding_sha256 != target.binding_sha256
            ):
                break
            if _label_present(current, labels):
                label = True
                if base._label_value(current, labels) is not None:
                    year = True
    for header_index, header_line in enumerate(lines):
        header = base._cells(header_line)
        if header is None or base._is_rule_row(header):
            continue
        label_indexes = [
            index
            for index, value in enumerate(header)
            if index > 0 and base._label_equal(value, labels)
        ]
        if not label_indexes:
            continue
        for row_index in range(
            header_index + 1,
            min(len(lines), header_index + 1 + base.MAXIMUM_TABLE_ROWS),
        ):
            if not lines[row_index].strip():
                break
            row = base._cells(lines[row_index])
            if row is None:
                break
            if base._is_rule_row(row):
                continue
            if len(row) != len(header) or not base._entity_equal(
                row[0], target.row_key
            ):
                continue
            anchor = True
            label = True
            if any(base._year(row[index]) is not None for index in label_indexes):
                year = True
    projections = [
        *base._entity_block_projections(
            lines, target, all_targets=all_targets, source="private.invalid"
        ),
        *base._table_projections(lines, target, source="private.invalid"),
    ]
    if bool(projections) != year:
        raise ValueError("V2.44.21 grammar signal drifted from V2.44.05")
    return anchor, label, year, len(projections)


def _reason(
    lines: Sequence[str], target: Any, all_targets: Sequence[Any]
) -> tuple[str, int]:
    if not base._accepted_labels(target):
        return "unsupported_column_kind", 0
    anchor, label, year, projection_count = _pair_signals(
        lines, target, all_targets
    )
    if not anchor:
        return "exact_structured_entity_anchor_absent", 0
    if not label:
        return "exact_label_absent_in_entity_scope", 0
    if not year:
        return "exact_label_value_year_absent", 0
    if projection_count < 1:
        raise ValueError("V2.44.21 labelled year lacks projection")
    return "structured_projection_emitted", projection_count


def _structured_observations(catalog: Mapping[str, Any]) -> list[dict[str, Any]]:
    return base._canonical_observations(catalog["structured_projections"])


def _compute(catalog: Mapping[str, Any]) -> dict[str, Any]:
    validated = base.validate_structured_label_projection(catalog)
    all_targets = _baseline_cells(validated["baseline_prediction"])
    targets = [
        target
        for target in all_targets
        if target.binding_sha256
        in set(validated["selected_target_binding_sha256s"])
    ]
    pages = list(validated["pages"])
    reasons: Counter[str] = Counter()
    projection_pairs = 0
    for page in pages:
        if page.get("fetch_integrity") is not True:
            raise ValueError("V2.44.21 expected integrity-validated private page")
        lines = unicodedata.normalize("NFKC", str(page["content"])).splitlines()
        for target in targets:
            reason, count = _reason(lines, target, all_targets)
            reasons[reason] += 1
            if reason == "structured_projection_emitted":
                projection_pairs += 1
            if (reason == "structured_projection_emitted") is not (count > 0):
                raise ValueError("V2.44.21 pair projection classification drifted")
    structured_observations = _structured_observations(validated)
    reason_counts = {name: int(reasons[name]) for name in REASONS}
    pair_count = len(pages) * len(targets)
    if (
        sum(reason_counts.values()) != pair_count
        or projection_pairs != reason_counts["structured_projection_emitted"]
    ):
        raise ValueError("V2.44.21 rejection partition drifted")
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "page_count": len(pages),
        "selected_target_count": len(targets),
        "page_target_pair_count": pair_count,
        "reason_counts": reason_counts,
        "structured_projection_pair_count": projection_pairs,
        "structured_projection_count": validated["structured_projection_count"],
        "structured_observation_count": len(structured_observations),
        "novel_structured_observation_count": validated[
            "novel_structured_observation_count"
        ],
        "structured_observation_duplicate_legacy_count": (
            len(structured_observations)
            - validated["novel_structured_observation_count"]
        ),
        "legacy_observation_count": validated["legacy_observation_count"],
        "combined_observation_count": validated["combined_observation_count"],
        "reason_partition_exact": True,
        "counts_only_no_task_page_entity_source_value_or_hash": True,
        "exact_v24405_grammar_replayed": True,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    return value


def build_projection_observability(
    catalog: Mapping[str, Any],
) -> dict[str, Any]:
    value = _compute(catalog)
    validate_projection_observability(value, catalog=catalog)
    return value


def validate_projection_observability(
    value: Mapping[str, Any], *, catalog: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    reasons = value.get("reason_counts")
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("policy_id") != POLICY_ID
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in (
                "page_count",
                "selected_target_count",
                "page_target_pair_count",
                "structured_projection_pair_count",
                "structured_projection_count",
                "structured_observation_count",
                "novel_structured_observation_count",
                "structured_observation_duplicate_legacy_count",
                "legacy_observation_count",
                "combined_observation_count",
            )
        )
        or not isinstance(reasons, Mapping)
        or set(reasons) != set(REASONS)
        or any(
            isinstance(reasons.get(name), bool)
            or not isinstance(reasons.get(name), int)
            or reasons[name] < 0
            for name in REASONS
        )
        or sum(reasons.values()) != value.get("page_target_pair_count")
        or value.get("page_target_pair_count")
        != value.get("page_count") * value.get("selected_target_count")
        or value.get("structured_projection_pair_count")
        != reasons.get("structured_projection_emitted")
        or value.get("structured_observation_count")
        != value.get("novel_structured_observation_count")
        + value.get("structured_observation_duplicate_legacy_count")
        or value.get("reason_partition_exact") is not True
        or value.get("counts_only_no_task_page_entity_source_value_or_hash")
        is not True
        or value.get("exact_v24405_grammar_replayed") is not True
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get(
            "file_environment_network_model_search_fetch_process_or_evaluator_accessed"
        )
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.21 projection observability identity drifted")
    if catalog is not None and dict(value) != _compute(catalog):
        raise ValueError("V2.44.21 projection observability replay drifted")
    return copy.deepcopy(dict(value))


__all__ = [
    "POLICY_ID",
    "REASONS",
    "ROLE",
    "build_projection_observability",
    "validate_projection_observability",
]
