#!/usr/bin/env python3
"""Content-free diagnosis of the V2.54.38 source-candidate funnel."""

from __future__ import annotations

import copy
import json
import os
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25432_source_authoritative_field_candidate as candidates  # noqa: E402
from deepwide_agent import v25434_source_authoritative_shared_runtime as runtime  # noqa: E402
from deepwide_agent import v25438_source_authoritative_shared_effect_external_contract as contract  # noqa: E402
from scripts import run_v25438_source_authoritative_shared_effect_external as runner  # noqa: E402


DATE = "20260813"
ROLE = "v25439_v25438_content_free_source_candidate_funnel_diagnosis"
SOURCE = Path("scripts/diagnose_v25439_v25438_source_candidate_funnel.py")
TEST = Path("tests/test_diagnose_v25439_v25438_source_candidate_funnel.py")
OUTPUT = Path(
    f"results/v25439_v25438_source_candidate_funnel_diagnosis_v1_{DATE}.json"
)
FIXED_HASHES = {
    contract.FORWARD_RESULT: "e5e7c1c3cbafb3d5c766620943b709cd22d7520a3353381bdb570a73247b1a38",
    contract.FORWARD_AUDIT: "c3b41f17b6440a6dc683ebf9999d0c96abb930628940a206cef3a82a550ce213",
    contract.TASK_ROWS: "606c0885255890b3b124f5f5e95ebb8694c9e0043fe2a178f815ef7029e0543e",
    contract.PREDICTION_FREEZE: "5bb73648e3fb00f0e94f174e458343266d63f86fe8db99971dbab146001fa815",
}

REGISTRY_FIELDS = (
    "input_page_count",
    "accepted_page_count",
    "rejected_page_count",
    "accepted_page_character_count",
    "horizontal_table_surface_count",
    "vertical_record_surface_count",
    "labelled_record_surface_count",
    "json_record_surface_count",
    "raw_observation_attempt_count",
    "evidence_closed_observation_count",
    "nonunique_or_oversized_quote_rejected_count",
    "unknown_or_unsafe_value_rejected_count",
    "missing_row_rejected_count",
    "missing_or_key_field_rejected_count",
    "coordinate_group_count",
    "exact_duplicate_observation_count",
    "ambiguous_same_value_coordinate_count",
    "conflicting_value_coordinate_count",
    "unchanged_coordinate_count",
    "list_collapse_rejected_coordinate_count",
    "truncated_unique_candidate_count",
    "available_candidate_count",
)


def _read(relative: Path) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.54.39 expected JSON object")
    return value


def _rows() -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, contract.TASK_ROWS, tracked=True)
    values = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return [runner.validate_task_row(value) for value in values]


def _barrier() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    observed = {
        path: contract.sha256(contract.ordinary(ROOT, path, tracked=True))
        for path in FIXED_HASHES
    }
    forward = runner.validate_forward_result(_read(contract.FORWARD_RESULT))
    audit = _read(contract.FORWARD_AUDIT)
    rows = _rows()
    aggregate = runner.aggregate_rows(
        rows, wall_seconds=float(forward["aggregate"]["batch_wall_seconds"])
    )
    if (
        observed != FIXED_HASHES
        or audit.get("role")
        != "v25438_source_authoritative_shared_effect_forward_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get("postfreeze_quality_protocol")
        is not False
        or audit.get("authorization", {}).get("deepwidebench_successor_build")
        is not False
        or aggregate != forward["aggregate"]
        or forward["mechanism_decision"]["mechanism_gate_passed"] is not False
        or len(rows) != contract.TASK_COUNT
    ):
        raise RuntimeError("V2.54.39 audited forward barrier drifted")
    return forward, rows


def _strict_label(line: str) -> tuple[str, str] | None:
    raw = str(line).strip()
    raw = re.sub(r"^(?:[-*]\s+)", "", raw)
    match = re.fullmatch(r"([^:=：\t]{1,120})\s*[:=：\t]\s*(.+?)\s*", raw)
    if match is None:
        return None
    return match.group(1).strip(), match.group(2).strip()


def _registry_funnel(rows: list[dict[str, Any]]) -> tuple[Counter[str], Counter[str]]:
    totals: Counter[str] = Counter()
    tasks: Counter[str] = Counter()
    for row in rows:
        checked = runtime.validate_result(row["runtime_result"])
        application = candidates.validate_application(
            checked["private_source_authoritative_application"]
        )
        receipt = candidates.validate_registry_receipt(
            application["private_candidate_registry"]["content_free_receipt"]
        )
        for name in REGISTRY_FIELDS:
            totals[name] += int(receipt[name])
            tasks[name] += int(receipt[name] > 0)
    return totals, tasks


def _label_surface_diagnosis(rows: list[dict[str, Any]]) -> dict[str, int]:
    output: Counter[str] = Counter()
    for row in rows:
        checked = runtime.validate_result(row["runtime_result"])
        columns = tuple(checked["private_source_columns"])
        required, base_rows = candidates._canonical_table(
            checked["predictions"][runtime.BASE_ARM], columns
        )
        row_map: defaultdict[str, list[int]] = defaultdict(list)
        column_map: defaultdict[str, list[int]] = defaultdict(list)
        for index, base_row in enumerate(base_rows):
            row_map[candidates._key(base_row[0])].append(index)
        for index, field in enumerate(required):
            column_map[candidates._key(field)].append(index)
        for page in checked["private_same_forward_authority_pages"]:
            lines = candidates._line_spans(page["content"])
            index = 0
            while index < len(lines):
                first = candidates._label_pair(
                    lines[index][2], required, column_map
                )
                if first is None or first[0] != 0:
                    index += 1
                    continue
                output["key_anchored_label_blocks"] += 1
                key_label, key_value = first[1], first[2]
                exact = row_map.get(candidates._key(key_value), [])
                qualified = row_map.get(
                    candidates._key(f"{key_label} {key_value}"), []
                )
                if len(exact) == 1:
                    output["raw_identity_unique_blocks"] += 1
                elif len(qualified) == 1:
                    output["key_qualified_identity_unique_blocks"] += 1
                elif len(qualified) > 1:
                    output["key_qualified_identity_ambiguous_blocks"] += 1
                else:
                    output["key_qualified_identity_unmatched_blocks"] += 1
                cursor = index
                block: list[tuple[str, str]] = []
                while cursor < len(lines) and cursor - index < 16:
                    pair = _strict_label(lines[cursor][2])
                    if pair is None:
                        break
                    block.append(pair)
                    cursor += 1
                output["minimum_block_line_count"] = (
                    len(block)
                    if output["minimum_block_line_count"] == 0
                    else min(output["minimum_block_line_count"], len(block))
                )
                output["maximum_block_line_count"] = max(
                    output["maximum_block_line_count"], len(block)
                )
                known_fields = []
                for label, raw_value in block:
                    matches = column_map.get(candidates._key(label), [])
                    if len(matches) != 1 or matches[0] == 0:
                        continue
                    field = required[matches[0]]
                    known_fields.append(field)
                    output[f"exact_visible_field_lines__{field}"] += 1
                    value = candidates._safe_cell(raw_value)
                    if value is None:
                        output[f"strict_safe_cell_rejected__{field}"] += 1
                        normalized = " ".join(
                            unicodedata.normalize("NFKC", raw_value).split()
                        )
                        if (
                            normalized
                            and normalized != raw_value
                            and len(normalized) <= candidates.MAXIMUM_CELL_CHARACTERS
                            and not any(ord(character) < 32 for character in normalized)
                            and "|" not in normalized
                            and "```" not in normalized
                            and not candidates.table_parent._is_unknown(normalized)
                        ):
                            output[
                                f"whitespace_only_normalizable__{field}"
                            ] += 1
                if "Published" in known_fields:
                    output["blocks_with_exact_published"] += 1
                if "Authors" in known_fields:
                    output["blocks_with_exact_authors"] += 1
                if any(label.casefold() == "author" for label, _ in block):
                    output["blocks_with_nonexact_singular_author"] += 1
                if "Title" in known_fields:
                    output["blocks_with_exact_title"] += 1
                index = max(index + 1, cursor)
    return dict(sorted(output.items()))


def _qualified_identity_counterfactual(rows: list[dict[str, Any]]) -> dict[str, int]:
    output: Counter[str] = Counter()
    task_with_available = 0
    for row in rows:
        checked = runtime.validate_result(row["runtime_result"])
        columns = tuple(checked["private_source_columns"])
        required, base_rows = candidates._canonical_table(
            checked["predictions"][runtime.BASE_ARM], columns
        )
        row_map: defaultdict[str, list[int]] = defaultdict(list)
        column_map: defaultdict[str, list[int]] = defaultdict(list)
        for index, base_row in enumerate(base_rows):
            row_map[candidates._key(base_row[0])].append(index)
        for index, field in enumerate(required):
            column_map[candidates._key(field)].append(index)
        observations: list[tuple[int, int, str, str]] = []
        for page_ordinal, page in enumerate(
            checked["private_same_forward_authority_pages"], 1
        ):
            content = page["content"]
            lines = candidates._line_spans(content)
            index = 0
            while index < len(lines):
                first = candidates._label_pair(
                    lines[index][2], required, column_map
                )
                if first is None:
                    index += 1
                    continue
                cursor = index
                pairs: list[tuple[int, str, str]] = []
                while cursor < len(lines):
                    pair = candidates._label_pair(
                        lines[cursor][2], required, column_map
                    )
                    if pair is None:
                        break
                    pairs.append(pair)
                    cursor += 1
                identity_pairs = [pair for pair in pairs if pair[0] == 0]
                targets = [pair for pair in pairs if pair[0] > 0]
                if len(identity_pairs) != 1 or not targets:
                    index += 1
                    continue
                identity_field, identity_label, identity = identity_pairs[0]
                assert identity_field == 0
                matches = row_map.get(candidates._key(identity), [])
                if len(matches) != 1:
                    matches = row_map.get(
                        candidates._key(f"{identity_label} {identity}"), []
                    )
                if len(matches) == 1:
                    for field_index, _label, raw_value in targets:
                        value = candidates._safe_cell(raw_value)
                        if value is None:
                            continue
                        observations.append(
                            (
                                matches[0],
                                field_index,
                                value,
                                str(base_rows[matches[0]][field_index]),
                            )
                        )
                index = max(index + 1, cursor)
        grouped: defaultdict[tuple[int, int], list[tuple[str, str]]] = defaultdict(
            list
        )
        for row_index, field_index, value, old in observations:
            grouped[(row_index, field_index)].append((value, old))
        local_available = 0
        for values in grouped.values():
            if len(values) != 1:
                if len({candidates._key(value) for value, _old in values}) > 1:
                    output["conflicting_coordinate_count"] += 1
                else:
                    output["ambiguous_same_value_coordinate_count"] += 1
                continue
            value, old = values[0]
            if candidates._key(value) == candidates._key(old):
                output["unchanged_coordinate_count"] += 1
                continue
            local_available += 1
        output["coordinate_group_count"] += len(grouped)
        output["available_candidate_count"] += local_available
        task_with_available += int(local_available > 0)
    output["tasks_with_available_candidate"] = task_with_available
    return dict(sorted(output.items()))


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    forward, rows = _barrier()
    funnel, task_flags = _registry_funnel(rows)
    layout = _label_surface_diagnosis(rows)
    identity_only = _qualified_identity_counterfactual(rows)
    checks = {
        "audited_forward_is_strict_mechanism_no_go": forward[
            "mechanism_decision"
        ]["mechanism_gate_passed"]
        is False,
        "accepted_authority_pages_nonzero": funnel["accepted_page_count"] == 107,
        "existing_parser_funnel_exact": (
            funnel["labelled_record_surface_count"] == 29
            and funnel["raw_observation_attempt_count"] == 29
            and funnel["missing_row_rejected_count"] == 29
            and funnel["evidence_closed_observation_count"] == 0
            and funnel["available_candidate_count"] == 0
        ),
        "all_observed_key_values_uniquely_bind_when_key_label_is_qualified": (
            layout["key_anchored_label_blocks"] == 29
            and layout["key_qualified_identity_unique_blocks"] == 29
            and layout.get("key_qualified_identity_ambiguous_blocks", 0) == 0
            and layout.get("key_qualified_identity_unmatched_blocks", 0) == 0
        ),
        "identity_qualification_alone_still_yields_zero_candidate": (
            identity_only["coordinate_group_count"] == 29
            and identity_only["unchanged_coordinate_count"] == 29
            and identity_only["available_candidate_count"] == 0
            and identity_only["tasks_with_available_candidate"] == 0
        ),
        "metadata_blocks_are_bounded_and_non_target_labels_split_existing_parser": (
            layout["minimum_block_line_count"] == 5
            and layout["maximum_block_line_count"] == 7
            and layout["blocks_with_exact_published"] == 29
            and layout["blocks_with_exact_authors"] == 18
            and layout["blocks_with_nonexact_singular_author"] == 11
            and layout.get("blocks_with_exact_title", 0) == 0
        ),
        "strict_safe_cell_rejections_are_whitespace_only_authors": (
            layout["strict_safe_cell_rejected__Authors"] == 17
            and layout["whitespace_only_normalizable__Authors"] == 17
        ),
        "no_truth_score_or_per_task_metric_used": True,
        "positive_signed_credit_zero": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "source_bindings": {
            str(path): contract.sha256(ROOT / path) for path in FIXED_HASHES
        },
        "forward_aggregate": copy.deepcopy(forward["aggregate"]),
        "existing_registry_funnel_counts": {
            name: int(funnel[name]) for name in REGISTRY_FIELDS
        },
        "existing_registry_task_nonzero_counts": {
            name: int(task_flags[name]) for name in REGISTRY_FIELDS
        },
        "key_anchored_layout_counts": layout,
        "identity_qualification_only_counterfactual": identity_only,
        "diagnosis": {
            "search_or_authority_page_reach_is_current_primary_failure": False,
            "existing_contiguous_exact_label_parser_is_layout_incomplete": True,
            "raw_numeric_identity_requires_exact_key_label_qualification": True,
            "identity_qualification_alone_creates_candidate_reach": False,
            "key_anchored_bounded_metadata_block_parser_is_supported": True,
            "non_target_metadata_labels_may_be_skipped_not_interpreted": True,
            "singular_author_to_authors_alias_is_supported": False,
            "category_to_status_alias_is_supported": False,
            "title_from_heading_or_prose_is_supported": False,
            "source_raw_span_must_remain_bound_before_whitespace_normalization": True,
            "quality_or_deepwidebench_improvement_established": False,
            "entropy_information_gain_signed_credit_evidence_present": False,
        },
        "contains_question_query_url_page_quote_identity_field_value_prediction_answer_or_per_task_metric": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "checks": checks,
        "findings": findings,
        "diagnosis_valid": not findings,
        "authorization": {
            "key_anchored_bounded_metadata_parser_build_only": not findings,
            "reuse_v25438_population_or_forward": False,
            "new_external_forward_or_evaluator": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    expected_funnel = {
        "input_page_count": 107,
        "accepted_page_count": 107,
        "rejected_page_count": 0,
        "accepted_page_character_count": 534912,
        "horizontal_table_surface_count": 0,
        "vertical_record_surface_count": 0,
        "labelled_record_surface_count": 29,
        "json_record_surface_count": 0,
        "raw_observation_attempt_count": 29,
        "evidence_closed_observation_count": 0,
        "nonunique_or_oversized_quote_rejected_count": 0,
        "unknown_or_unsafe_value_rejected_count": 0,
        "missing_row_rejected_count": 29,
        "missing_or_key_field_rejected_count": 0,
        "coordinate_group_count": 0,
        "exact_duplicate_observation_count": 0,
        "ambiguous_same_value_coordinate_count": 0,
        "conflicting_value_coordinate_count": 0,
        "unchanged_coordinate_count": 0,
        "list_collapse_rejected_coordinate_count": 0,
        "truncated_unique_candidate_count": 0,
        "available_candidate_count": 0,
    }
    expected_layout = {
        "blocks_with_exact_authors": 18,
        "blocks_with_exact_published": 29,
        "blocks_with_nonexact_singular_author": 11,
        "exact_visible_field_lines__Authors": 18,
        "exact_visible_field_lines__Published": 29,
        "key_anchored_label_blocks": 29,
        "key_qualified_identity_unique_blocks": 29,
        "maximum_block_line_count": 7,
        "minimum_block_line_count": 5,
        "strict_safe_cell_rejected__Authors": 17,
        "whitespace_only_normalizable__Authors": 17,
    }
    expected_identity_only = {
        "available_candidate_count": 0,
        "coordinate_group_count": 29,
        "tasks_with_available_candidate": 0,
        "unchanged_coordinate_count": 29,
    }
    if (
        copied.get("role") != ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("source_bindings")
        != {str(path): expected for path, expected in FIXED_HASHES.items()}
        or copied.get("existing_registry_funnel_counts") != expected_funnel
        or copied.get("key_anchored_layout_counts") != expected_layout
        or copied.get("identity_qualification_only_counterfactual")
        != expected_identity_only
        or copied.get("findings") != []
        or copied.get("diagnosis_valid") is not True
        or not all((copied.get("checks") or {}).values())
        or copied.get(
            "contains_question_query_url_page_quote_identity_field_value_prediction_answer_or_per_task_metric"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read"
        )
        is not False
        or copied.get("model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "key_anchored_bounded_metadata_parser_build_only": True,
            "reuse_v25438_population_or_forward": False,
            "new_external_forward_or_evaluator": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.39 source-candidate funnel diagnosis drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_diagnosis()
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "diagnosis_valid": value["diagnosis_valid"],
                "findings": value["findings"],
                "existing_registry_funnel_counts": value[
                    "existing_registry_funnel_counts"
                ],
                "identity_qualification_only_counterfactual": value[
                    "identity_qualification_only_counterfactual"
                ],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
