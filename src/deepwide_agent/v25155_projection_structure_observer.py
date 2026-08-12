"""Content-free structure observer for the fetch-to-extractor boundary.

The observer receives three in-memory representations of the same public page:
decoded raw markup, visible text after HTML extraction, and the bounded text
after the production projector.  It emits only structural counts and boolean
layer transitions.  It never emits page text, labels, values, URLs, task
identity, predictions, hashes of semantic content, or evaluator information.

This module is pure and build-only.  It has no file, environment, process,
network, model, search, benchmark, or evaluator capability.  A structure
signal is diagnostic only: it is not an admissible observation and receives no
entropy/information-gain or task credit.
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping
from html.parser import HTMLParser
from typing import Any

from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25155_projection_structure_observer_v1"
ROLE = "v25155_content_free_projection_structure_observation"
PREPROJECTION_ROLE = "v25155_content_free_preprojection_structure_observation"
MAXIMUM_LAYER_CHARACTERS = 3_000_000

RAW_COUNT_NAMES = (
    "table_count",
    "table_row_count",
    "table_row_with_at_least_two_cells_count",
    "table_header_cell_count",
    "table_data_cell_count",
    "definition_list_count",
    "definition_term_count",
    "definition_description_count",
    "json_ld_script_count",
)
TEXT_COUNT_NAMES = (
    "pipe_line_count",
    "two_column_pipe_line_count",
    "key_value_pipe_line_count",
    "same_width_adjacent_pipe_pair_count",
    "json_object_line_count",
    "label_value_line_count",
    "contiguous_label_value_block_count",
    "heading_followed_by_label_value_block_count",
)
AGGREGATE_COUNT_NAMES = (
    "observed_page_count",
    "raw_structured_page_count",
    "extracted_structured_page_count",
    "projected_structured_page_count",
    "raw_to_extracted_total_structure_loss_page_count",
    "extracted_to_projected_total_structure_loss_page_count",
    "raw_table_and_extracted_pipe_page_count",
    "extracted_pipe_retained_after_projection_page_count",
    "extracted_key_value_pipe_retained_after_projection_page_count",
    *(f"raw_{name}" for name in RAW_COUNT_NAMES),
    *(f"extracted_{name}" for name in TEXT_COUNT_NAMES),
    *(f"projected_{name}" for name in TEXT_COUNT_NAMES),
)


class _RawStructureCounter(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.counts = {name: 0 for name in RAW_COUNT_NAMES}
        self.table_depth = 0
        self.row_depth = 0
        self.row_cells = 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        name = str(tag).casefold()
        if name == "table":
            self.counts["table_count"] += 1
            self.table_depth += 1
        elif name == "tr" and self.table_depth:
            self.counts["table_row_count"] += 1
            self.row_depth += 1
            if self.row_depth == 1:
                self.row_cells = 0
        elif name in {"th", "td"} and self.table_depth and self.row_depth:
            key = (
                "table_header_cell_count"
                if name == "th"
                else "table_data_cell_count"
            )
            self.counts[key] += 1
            if self.row_depth == 1:
                self.row_cells += 1
        elif name == "dl":
            self.counts["definition_list_count"] += 1
        elif name == "dt":
            self.counts["definition_term_count"] += 1
        elif name == "dd":
            self.counts["definition_description_count"] += 1
        elif name == "script":
            attributes = {
                str(key).casefold(): str(value or "").strip().casefold()
                for key, value in attrs
            }
            media = attributes.get("type", "").split(";", 1)[0].strip()
            if media == "application/ld+json":
                self.counts["json_ld_script_count"] += 1

    def handle_endtag(self, tag: str) -> None:
        name = str(tag).casefold()
        if name == "tr" and self.table_depth and self.row_depth:
            if self.row_depth == 1 and self.row_cells >= 2:
                self.counts["table_row_with_at_least_two_cells_count"] += 1
            self.row_depth -= 1
            if self.row_depth == 0:
                self.row_cells = 0
        elif name == "table" and self.table_depth:
            self.table_depth -= 1
            if self.table_depth == 0:
                self.row_depth = 0
                self.row_cells = 0


def _bounded_text(value: object, *, layer: str) -> str:
    if not isinstance(value, str) or "\x00" in value:
        raise ValueError(f"V2.51.55 {layer} layer is invalid")
    if len(value) > MAXIMUM_LAYER_CHARACTERS:
        raise ValueError(f"V2.51.55 {layer} layer exceeds inherited cap")
    return value


def _raw_counts(raw_markup: str) -> dict[str, int]:
    parser = _RawStructureCounter()
    try:
        parser.feed(raw_markup)
        parser.close()
    except (TypeError, ValueError):
        return {name: 0 for name in RAW_COUNT_NAMES}
    return {name: int(parser.counts[name]) for name in RAW_COUNT_NAMES}


def _pipe_width(line: str) -> int | None:
    text = str(line).strip()
    if "|" not in text:
        return None
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    cells = [" ".join(value.split()) for value in text.split("|")]
    return len(cells) if 2 <= len(cells) <= 64 else None


def _key_value_pipe(line: str) -> bool:
    text = str(line).strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    cells = [" ".join(value.split()) for value in text.split("|")]
    return bool(
        len(cells) == 2
        and cells[0]
        and cells[1]
        and (cells[0].endswith(":") or cells[0].endswith("="))
    )


_LABEL_VALUE = re.compile(
    r"^(?:[-*\u2022]\s*)?[^:=\n]{1,80}\s*[:=]\s*\S.*$"
)


def _text_counts(text: str) -> dict[str, int]:
    lines = text.splitlines()
    pipe_widths = [_pipe_width(line) for line in lines]
    label_flags = [bool(_LABEL_VALUE.fullmatch(line.strip())) for line in lines]
    json_objects = 0
    for line in lines:
        stripped = line.strip()
        if not (stripped.startswith("{") and stripped.endswith("}")):
            continue
        try:
            value = json.loads(stripped)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
        if isinstance(value, dict):
            json_objects += 1

    contiguous = 0
    heading_followed = 0
    index = 0
    while index < len(lines):
        if not label_flags[index]:
            index += 1
            continue
        start = index
        while index < len(lines) and label_flags[index]:
            index += 1
        if index - start >= 2:
            contiguous += 1
            previous = start - 1
            while previous >= 0 and not lines[previous].strip():
                previous -= 1
            if previous >= 0 and not label_flags[previous]:
                heading_followed += 1

    return {
        "pipe_line_count": sum(width is not None for width in pipe_widths),
        "two_column_pipe_line_count": sum(width == 2 for width in pipe_widths),
        "key_value_pipe_line_count": sum(
            width == 2 and _key_value_pipe(line)
            for line, width in zip(lines, pipe_widths, strict=True)
        ),
        "same_width_adjacent_pipe_pair_count": sum(
            left is not None and left == right
            for left, right in zip(pipe_widths, pipe_widths[1:])
        ),
        "json_object_line_count": json_objects,
        "label_value_line_count": sum(label_flags),
        "contiguous_label_value_block_count": contiguous,
        "heading_followed_by_label_value_block_count": heading_followed,
    }


def _raw_structured(counts: Mapping[str, int]) -> bool:
    return bool(
        counts["table_row_with_at_least_two_cells_count"]
        or (
            counts["definition_term_count"]
            and counts["definition_description_count"]
        )
        or counts["json_ld_script_count"]
    )


def _text_structured(counts: Mapping[str, int]) -> bool:
    return bool(
        counts["same_width_adjacent_pipe_pair_count"]
        or counts["key_value_pipe_line_count"]
        or counts["json_object_line_count"]
        or counts["contiguous_label_value_block_count"]
    )


def observe_preprojection(
    raw_markup: str,
    extracted_text: str,
) -> dict[str, Any]:
    """Seal raw-markup and extracted-text counts before projection."""

    raw = _bounded_text(raw_markup, layer="raw_markup")
    extracted = _bounded_text(extracted_text, layer="extracted_text")
    raw_counts = _raw_counts(raw)
    extracted_counts = _text_counts(extracted)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": PREPROJECTION_ROLE,
        "policy_id": POLICY_ID,
        "raw_markup_counts": raw_counts,
        "extracted_text_counts": extracted_counts,
        "raw_structured_surface_present": _raw_structured(raw_counts),
        "extracted_structured_surface_present": _text_structured(extracted_counts),
        "raw_to_extracted_total_structure_loss": bool(
            _raw_structured(raw_counts) and not _text_structured(extracted_counts)
        ),
        "raw_markup_or_extracted_text_label_value_url_question_identity_prediction_or_content_hash_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_preprojection_observation(value)


def validate_preprojection_observation(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    raw = copied.get("raw_markup_counts")
    extracted = copied.get("extracted_text_counts")
    false_flags = (
        "raw_markup_or_extracted_text_label_value_url_question_identity_prediction_or_content_hash_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "raw_markup_counts",
            "extracted_text_counts",
            "raw_structured_surface_present",
            "extracted_structured_surface_present",
            "raw_to_extracted_total_structure_loss",
            *false_flags,
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != PREPROJECTION_ROLE
        or copied.get("policy_id") != POLICY_ID
        or not _valid_raw_counts(raw)
        or not _valid_text_counts(extracted)
        or copied.get("raw_structured_surface_present")
        is not _raw_structured(raw)
        or copied.get("extracted_structured_surface_present")
        is not _text_structured(extracted)
        or copied.get("raw_to_extracted_total_structure_loss")
        is not bool(_raw_structured(raw) and not _text_structured(extracted))
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.55 preprojection observation drifted")
    return copied


def finalize_observation(
    preprojection: Mapping[str, Any],
    projected_text: str,
) -> dict[str, Any]:
    """Add projected-text counts without recovering raw semantic content."""

    pre = validate_preprojection_observation(preprojection)
    projected = _bounded_text(projected_text, layer="projected_text")
    return _build_observation(
        raw_counts=pre["raw_markup_counts"],
        extracted_counts=pre["extracted_text_counts"],
        projected_counts=_text_counts(projected),
    )


def observe_structure(
    raw_markup: str,
    extracted_text: str,
    projected_text: str,
) -> dict[str, Any]:
    """Return a sealed content-free three-layer structure receipt."""

    preprojection = observe_preprojection(raw_markup, extracted_text)
    return finalize_observation(preprojection, projected_text)


def _build_observation(
    *,
    raw_counts: Mapping[str, int],
    extracted_counts: Mapping[str, int],
    projected_counts: Mapping[str, int],
) -> dict[str, Any]:
    raw_present = _raw_structured(raw_counts)
    extracted_present = _text_structured(extracted_counts)
    projected_present = _text_structured(projected_counts)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "raw_markup_counts": raw_counts,
        "extracted_text_counts": extracted_counts,
        "projected_text_counts": projected_counts,
        "transitions": {
            "raw_structured_surface_present": raw_present,
            "extracted_structured_surface_present": extracted_present,
            "projected_structured_surface_present": projected_present,
            "raw_to_extracted_total_structure_loss": bool(
                raw_present and not extracted_present
            ),
            "extracted_to_projected_total_structure_loss": bool(
                extracted_present and not projected_present
            ),
            "raw_table_and_extracted_pipe_surface_present": bool(
                raw_counts["table_row_with_at_least_two_cells_count"]
                and extracted_counts["pipe_line_count"]
            ),
            "extracted_pipe_surface_retained_after_projection": bool(
                extracted_counts["pipe_line_count"]
                and projected_counts["pipe_line_count"]
            ),
            "extracted_key_value_pipe_surface_retained_after_projection": bool(
                extracted_counts["key_value_pipe_line_count"]
                and projected_counts["key_value_pipe_line_count"]
            ),
        },
        "structure_signal_is_diagnostic_not_admissible_evidence": True,
        "raw_markup_extracted_text_projected_text_label_value_url_question_identity_prediction_or_content_hash_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_observation(value)


def _valid_raw_counts(counts: object) -> bool:
    return bool(
        isinstance(counts, Mapping)
        and set(counts) == set(RAW_COUNT_NAMES)
        and all(
            not isinstance(count, bool) and isinstance(count, int) and count >= 0
            for count in counts.values()
        )
        and counts["table_row_with_at_least_two_cells_count"]
        <= counts["table_row_count"]
        and 2 * counts["table_row_with_at_least_two_cells_count"]
        <= counts["table_header_cell_count"] + counts["table_data_cell_count"]
    )


def _valid_text_counts(counts: object) -> bool:
    return bool(
        isinstance(counts, Mapping)
        and set(counts) == set(TEXT_COUNT_NAMES)
        and all(
            not isinstance(count, bool) and isinstance(count, int) and count >= 0
            for count in counts.values()
        )
        and counts["two_column_pipe_line_count"] <= counts["pipe_line_count"]
        and counts["key_value_pipe_line_count"]
        <= counts["two_column_pipe_line_count"]
        and counts["same_width_adjacent_pipe_pair_count"]
        <= max(0, counts["pipe_line_count"] - 1)
        and 2 * counts["contiguous_label_value_block_count"]
        <= counts["label_value_line_count"]
        and counts["heading_followed_by_label_value_block_count"]
        <= counts["contiguous_label_value_block_count"]
    )


def validate_observation(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    raw = copied.get("raw_markup_counts")
    extracted = copied.get("extracted_text_counts")
    projected = copied.get("projected_text_counts")
    transitions = copied.get("transitions")
    expected_transitions = {
        "raw_structured_surface_present",
        "extracted_structured_surface_present",
        "projected_structured_surface_present",
        "raw_to_extracted_total_structure_loss",
        "extracted_to_projected_total_structure_loss",
        "raw_table_and_extracted_pipe_surface_present",
        "extracted_pipe_surface_retained_after_projection",
        "extracted_key_value_pipe_surface_retained_after_projection",
    }
    false_flags = (
        "raw_markup_extracted_text_projected_text_label_value_url_question_identity_prediction_or_content_hash_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "raw_markup_counts",
            "extracted_text_counts",
            "projected_text_counts",
            "transitions",
            "structure_signal_is_diagnostic_not_admissible_evidence",
            *false_flags,
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(raw, Mapping)
        or set(raw) != set(RAW_COUNT_NAMES)
        or not isinstance(extracted, Mapping)
        or set(extracted) != set(TEXT_COUNT_NAMES)
        or not isinstance(projected, Mapping)
        or set(projected) != set(TEXT_COUNT_NAMES)
        or any(
            isinstance(count, bool) or not isinstance(count, int) or count < 0
            for counts in (raw, extracted, projected)
            for count in counts.values()
        )
        or not _valid_raw_counts(raw)
        or not _valid_text_counts(extracted)
        or not _valid_text_counts(projected)
        or not isinstance(transitions, Mapping)
        or set(transitions) != expected_transitions
        or any(not isinstance(flag, bool) for flag in transitions.values())
        or transitions["raw_structured_surface_present"]
        is not _raw_structured(raw)
        or transitions["extracted_structured_surface_present"]
        is not _text_structured(extracted)
        or transitions["projected_structured_surface_present"]
        is not _text_structured(projected)
        or transitions["raw_to_extracted_total_structure_loss"]
        is not bool(_raw_structured(raw) and not _text_structured(extracted))
        or transitions["extracted_to_projected_total_structure_loss"]
        is not bool(_text_structured(extracted) and not _text_structured(projected))
        or transitions["raw_table_and_extracted_pipe_surface_present"]
        is not bool(
            raw["table_row_with_at_least_two_cells_count"]
            and extracted["pipe_line_count"]
        )
        or transitions["extracted_pipe_surface_retained_after_projection"]
        is not bool(
            extracted["pipe_line_count"] and projected["pipe_line_count"]
        )
        or transitions[
            "extracted_key_value_pipe_surface_retained_after_projection"
        ]
        is not bool(
            extracted["key_value_pipe_line_count"]
            and projected["key_value_pipe_line_count"]
        )
        or copied.get("structure_signal_is_diagnostic_not_admissible_evidence")
        is not True
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.55 structure observation drifted")
    return copied


def aggregate_observations(values: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate sealed page receipts without page identity or content."""

    observations = [validate_observation(value) for value in values]
    counts = {name: 0 for name in AGGREGATE_COUNT_NAMES}
    counts["observed_page_count"] = len(observations)
    for value in observations:
        raw = value["raw_markup_counts"]
        extracted = value["extracted_text_counts"]
        projected = value["projected_text_counts"]
        transitions = value["transitions"]
        counts["raw_structured_page_count"] += int(
            transitions["raw_structured_surface_present"]
        )
        counts["extracted_structured_page_count"] += int(
            transitions["extracted_structured_surface_present"]
        )
        counts["projected_structured_page_count"] += int(
            transitions["projected_structured_surface_present"]
        )
        counts["raw_to_extracted_total_structure_loss_page_count"] += int(
            transitions["raw_to_extracted_total_structure_loss"]
        )
        counts["extracted_to_projected_total_structure_loss_page_count"] += int(
            transitions["extracted_to_projected_total_structure_loss"]
        )
        counts["raw_table_and_extracted_pipe_page_count"] += int(
            transitions["raw_table_and_extracted_pipe_surface_present"]
        )
        counts["extracted_pipe_retained_after_projection_page_count"] += int(
            transitions["extracted_pipe_surface_retained_after_projection"]
        )
        counts[
            "extracted_key_value_pipe_retained_after_projection_page_count"
        ] += int(
            transitions[
                "extracted_key_value_pipe_surface_retained_after_projection"
            ]
        )
        for name in RAW_COUNT_NAMES:
            counts[f"raw_{name}"] += int(raw[name])
        for name in TEXT_COUNT_NAMES:
            counts[f"extracted_{name}"] += int(extracted[name])
            counts[f"projected_{name}"] += int(projected[name])
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25155_content_free_projection_structure_aggregate",
        "policy_id": POLICY_ID,
        "counts": counts,
        "contains_page_identity_url_question_label_value_text_prediction_or_content_hash": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    counts = copied.get("counts")
    page = counts.get("observed_page_count", -1) if isinstance(counts, Mapping) else -1
    page_counts = (
        "raw_structured_page_count",
        "extracted_structured_page_count",
        "projected_structured_page_count",
        "raw_to_extracted_total_structure_loss_page_count",
        "extracted_to_projected_total_structure_loss_page_count",
        "raw_table_and_extracted_pipe_page_count",
        "extracted_pipe_retained_after_projection_page_count",
        "extracted_key_value_pipe_retained_after_projection_page_count",
    )
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "counts",
            "contains_page_identity_url_question_label_value_text_prediction_or_content_hash",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "benchmark_launch_or_evaluator_authorized",
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25155_content_free_projection_structure_aggregate"
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(counts, Mapping)
        or set(counts) != set(AGGREGATE_COUNT_NAMES)
        or any(
            isinstance(count, bool) or not isinstance(count, int) or count < 0
            for count in counts.values()
        )
        or any(counts[name] > page for name in page_counts)
        or any(
            copied.get(name) is not False
            for name in (
                "contains_page_identity_url_question_label_value_text_prediction_or_content_hash",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.55 structure aggregate drifted")
    return copied


__all__ = [
    "MAXIMUM_LAYER_CHARACTERS",
    "POLICY_ID",
    "PREPROJECTION_ROLE",
    "RAW_COUNT_NAMES",
    "ROLE",
    "TEXT_COUNT_NAMES",
    "AGGREGATE_COUNT_NAMES",
    "aggregate_observations",
    "finalize_observation",
    "observe_preprojection",
    "observe_structure",
    "validate_preprojection_observation",
    "validate_observation",
    "validate_aggregate",
]
