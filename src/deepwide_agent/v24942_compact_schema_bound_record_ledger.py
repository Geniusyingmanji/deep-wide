"""Compact rendering successor for the V2.49.39 schema-bound ledger.

V2.49.39 repeats source, binding, row-key-label and target-label strings in
every rendered record.  Under the unchanged 5k/page cap this left 117/864
otherwise admissible observations outside the V2.49.41 external projection.
This pure successor keeps V2.49.39 discovery, conflict gates, record seals and
observation seals unchanged, but renders one page-level schema/source header
followed by short, record-atomic rows.  Each row retains its sealed record ID,
row key, target indexes and values; target labels are declared once in the
header.  No record is split across projection blocks.

Inputs remain limited to the visible question and same-forward fetched pages.
The component has no file, environment, process, network, model, search,
benchmark metadata, answer, evaluator, score, reward or historical-result
capability.  Entropy/IG is shadow-only and never assigns signed credit.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24839_structure_preserving_projector as structure
from . import v24928_unicode_total_visible_row_compactor as unicode_total
from . import v24933_contextual_record_value_projector as projector_parent
from . import v24939_schema_bound_record_ledger as parent


POLICY_ID = "v24942_compact_schema_bound_open_world_record_ledger_v1"
ROLE = "v24942_compact_schema_bound_record_ledger_projection"
RECEIPT_ROLE = "v24942_content_free_compact_schema_bound_record_ledger_receipt"
TOTAL_CHARACTER_CAP = parent.TOTAL_CHARACTER_CAP
MAXIMUM_PAGE_CHARS = parent.MAXIMUM_PAGE_CHARS
BLOCK_CHARACTER_CAP = parent.BLOCK_CHARACTER_CAP
MAXIMUM_VISIBLE_GROUPS = parent.MAXIMUM_VISIBLE_GROUPS
MAXIMUM_QUERY_TERMS = parent.MAXIMUM_QUERY_TERMS
payload_sha256 = parent.payload_sha256


def _compact_header(
    page: Mapping[str, Any], schema: Sequence[Mapping[str, Any]]
) -> str:
    return "[SBCL-SCHEMA] " + json.dumps(
        {
            "source_host": page["host"],
            "row_key_label": schema[0]["display"],
            "targets": [
                [int(column["index"]), str(column["display"])]
                for column in schema[1:]
            ],
            "binding": "exact_header_or_identity_label",
            "conflicts": "omitted",
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _compact_line(
    record: Mapping[str, Any], fields: Sequence[Mapping[str, Any]]
) -> tuple[str, str]:
    token = f"[SBCL:{record['record_id']}]"
    line = token + " " + json.dumps(
        {
            "row": record["row_key"],
            "cells": [
                [int(field["target_index"]), str(field["value"])]
                for field in fields
            ],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return token, line


def _compact_augment_pages(
    pages: Sequence[Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    conflicts: set[tuple[str, int]],
    schema: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, int]:
    lines_by_page: dict[int, list[str]] = defaultdict(list)
    observations: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int, str]] = set()
    maximum_line = 0
    compact_characters = 0
    for record in records:
        row = parent._canonical(record["row_key"])
        eligible: list[Mapping[str, Any]] = []
        for field in record["fields"]:
            target = int(field["target_index"])
            identity = (
                str(record["source_url"]),
                row,
                target,
                parent._canonical(field["value"]),
            )
            if (row, target) in conflicts or identity in seen:
                continue
            eligible.append(field)
            seen.add(identity)
        if not eligible:
            continue
        token, line = _compact_line(record, eligible)
        if len(line) > BLOCK_CHARACTER_CAP:
            raise ValueError("V2.49.42 compact record exceeds atomic block cap")
        maximum_line = max(maximum_line, len(line))
        compact_characters += len(line)
        lines_by_page[int(record["source_page_ordinal"])].append(line)
        for field in eligible:
            observation = {
                "token": token,
                "record_id": record["record_id"],
                "source_page_ordinal": record["source_page_ordinal"],
                "source_url": record["source_url"],
                "source_host": record["source_host"],
                "binding_kind": record["binding_kind"],
                "row_key": record["row_key"],
                "target_index": int(field["target_index"]),
                "target_label": field["target_label"],
                "value": field["value"],
            }
            observation["observation_payload_sha256"] = payload_sha256(observation)
            observations.append(observation)

    output: list[dict[str, Any]] = []
    for page in pages:
        copied = {
            "title": str(page["title"]),
            "url": str(page["url"]),
            "content": str(page["content"]),
        }
        lines = lines_by_page.get(int(page["ordinal"]), [])
        if lines:
            header = _compact_header(page, schema)
            compact_characters += len(header)
            copied["content"] = header + "\n" + "\n".join(lines) + "\n\n" + copied["content"]
        output.append(copied)
    return output, observations, maximum_line, compact_characters


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    names = (
        "input_page_count",
        "visible_schema_column_count",
        "discovered_record_count",
        "discovered_row_key_count",
        "conflicting_coordinate_count",
        "admissible_bound_observation_count",
        "retained_admissible_bound_observation_count",
        "missed_admissible_bound_observation_count",
        "admissible_record_count",
        "retained_admissible_record_count",
        "source_url_count",
        "source_host_count",
        "compact_ledger_characters",
        "maximum_compact_record_line_characters",
        "projected_rendered_characters",
        "positive_signed_credit_count",
        "unbound_observation_positive_credit_count",
    )
    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        **{name: int(value[name]) for name in names},
        "discovery_records_and_observation_seals_inherited_unchanged": True,
        "one_schema_and_source_header_per_projected_page": True,
        "record_rows_atomic_and_never_split_across_blocks": True,
        "stable_source_and_record_order_preserved": True,
        "inherited_total_and_per_page_caps_preserved": True,
        "same_forward_page_bytes_only": True,
        "entropy_information_gain_shadow_only": True,
        "unbound_observation_credit_forced_zero": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_metadata_answer_evaluator_score_reward_or_historical_result_read": False,
        "additional_search_fetch_model_call_token_context_or_wall_cap": False,
    }
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    return validate_receipt(receipt)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    counts = (
        "input_page_count",
        "visible_schema_column_count",
        "discovered_record_count",
        "discovered_row_key_count",
        "conflicting_coordinate_count",
        "admissible_bound_observation_count",
        "retained_admissible_bound_observation_count",
        "missed_admissible_bound_observation_count",
        "admissible_record_count",
        "retained_admissible_record_count",
        "source_url_count",
        "source_host_count",
        "compact_ledger_characters",
        "maximum_compact_record_line_characters",
        "projected_rendered_characters",
        "positive_signed_credit_count",
        "unbound_observation_positive_credit_count",
    )
    true_flags = (
        "discovery_records_and_observation_seals_inherited_unchanged",
        "one_schema_and_source_header_per_projected_page",
        "record_rows_atomic_and_never_split_across_blocks",
        "stable_source_and_record_order_preserved",
        "inherited_total_and_per_page_caps_preserved",
        "same_forward_page_bytes_only",
        "entropy_information_gain_shadow_only",
        "unbound_observation_credit_forced_zero",
    )
    false_flags = (
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_metadata_answer_evaluator_score_reward_or_historical_result_read",
        "additional_search_fetch_model_call_token_context_or_wall_cap",
    )
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_policy_id") != parent.POLICY_ID
        or any(isinstance(copied.get(name), bool) or not isinstance(copied.get(name), int) or copied[name] < 0 for name in counts)
        or copied["retained_admissible_bound_observation_count"] > copied["admissible_bound_observation_count"]
        or copied["missed_admissible_bound_observation_count"] != copied["admissible_bound_observation_count"] - copied["retained_admissible_bound_observation_count"]
        or copied["retained_admissible_record_count"] > copied["admissible_record_count"]
        or copied["maximum_compact_record_line_characters"] > BLOCK_CHARACTER_CAP
        or copied["projected_rendered_characters"] > TOTAL_CHARACTER_CAP
        or copied["positive_signed_credit_count"] != 0
        or copied["unbound_observation_positive_credit_count"] != 0
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.42 compact ledger receipt drifted")
    return copied


def build_projection(
    question: str,
    pages: Sequence[Mapping[str, Any]],
    *,
    explicit_groups: Sequence[str] | None = None,
) -> dict[str, Any]:
    discovery_pages = structure._stable_pages(pages)
    compacted_pages, compaction = unicode_total.compact_pages(question, pages)
    stable = structure._stable_pages(compacted_pages)
    if [page["url"] for page in discovery_pages] != [page["url"] for page in stable]:
        raise ValueError("V2.49.42 normalized/compacted page identity drifted")
    schema = parent._visible_schema(question)
    records, discovery_counts = parent._discover(discovery_pages, schema) if schema else ([], {
        "header_bound_table_count": 0,
        "candidate_table_row_count": 0,
        "malformed_table_row_count": 0,
        "identity_label_bound_record_count": 0,
        "duplicate_field_conflict_count": 0,
    })
    conflicts, coordinate_hosts, coordinate_urls = parent._coordinate_summary(records)
    augmented, observations, maximum_line, ledger_chars = _compact_augment_pages(
        stable, records, conflicts, schema
    )
    inherited = projector_parent.build_projection(
        question, augmented, explicit_groups=explicit_groups
    )
    projection = str(inherited["projection"])
    retained_tokens = {
        observation["token"] for observation in observations
        if observation["token"] in projection
    }
    retained = [
        observation for observation in observations
        if observation["token"] in retained_tokens
    ]
    record_ids = {str(value["record_id"]) for value in observations}
    retained_ids = {str(value["record_id"]) for value in retained}
    receipt_input = {
        "input_page_count": len(discovery_pages),
        "visible_schema_column_count": len(schema),
        "discovered_record_count": len(records),
        "discovered_row_key_count": len({parent._canonical(record["row_key"]) for record in records}),
        "conflicting_coordinate_count": len(conflicts),
        "admissible_bound_observation_count": len(observations),
        "retained_admissible_bound_observation_count": len(retained),
        "missed_admissible_bound_observation_count": len(observations) - len(retained),
        "admissible_record_count": len(record_ids),
        "retained_admissible_record_count": len(retained_ids),
        "source_url_count": len({url for values in coordinate_urls.values() for url in values}),
        "source_host_count": len({host for values in coordinate_hosts.values() for host in values}),
        "compact_ledger_characters": ledger_chars,
        "maximum_compact_record_line_characters": maximum_line,
        "projected_rendered_characters": len(projection),
        "positive_signed_credit_count": 0,
        "unbound_observation_positive_credit_count": 0,
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "visible_question_sha256": hashlib.sha256(question.encode("utf-8")).hexdigest(),
        "visible_schema_sha256": payload_sha256(schema),
        "source_manifest_sha256": payload_sha256([
            {"ordinal": page["ordinal"], "url": page["url"], "host": page["host"], "content_sha256": page["content_sha256"]}
            for page in discovery_pages
        ]),
        **discovery_counts,
        **receipt_input,
        "record_ledger": records,
        "admissible_observations": observations,
        "projection": projection,
        "projection_sha256": hashlib.sha256(projection.encode()).hexdigest(),
        "content_free_receipt": {},
        "original_unicode_total_compaction_receipt": compaction,
        "parent_projection_receipt": copy.deepcopy(inherited["content_free_receipt"]),
        "parent_augmented_unicode_total_compaction_receipt": copy.deepcopy(inherited["unicode_total_compaction_receipt"]),
        "same_forward_page_bytes_only": True,
        "entropy_information_gain_shadow_only": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_metadata_answer_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
    }
    value["content_free_receipt"] = _receipt(value)
    value["artifact_payload_sha256"] = payload_sha256(value)
    return validate_projection(value, question=question, pages=pages, explicit_groups=explicit_groups, replay=False)


def validate_projection(
    value: Mapping[str, Any],
    *,
    question: str,
    pages: Sequence[Mapping[str, Any]],
    explicit_groups: Sequence[str] | None = None,
    replay: bool = True,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("artifact_payload_sha256", None)
    projection = copied.get("projection")
    receipt = copied.get("content_free_receipt")
    records = copied.get("record_ledger")
    observations = copied.get("admissible_observations")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_policy_id") != parent.POLICY_ID
        or not isinstance(projection, str)
        or copied.get("projection_sha256") != hashlib.sha256(projection.encode()).hexdigest()
        or copied.get("projected_rendered_characters") != len(projection)
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or not isinstance(records, list)
        or len(records) != copied.get("discovered_record_count")
        or not isinstance(observations, list)
        or len(observations) != copied.get("admissible_bound_observation_count")
        or any(record.get("record_payload_sha256") != payload_sha256({key: item for key, item in record.items() if key != "record_payload_sha256"}) for record in records)
        or any(observation.get("observation_payload_sha256") != payload_sha256({key: item for key, item in observation.items() if key != "observation_payload_sha256"}) for observation in observations)
        or copied.get("same_forward_page_bytes_only") is not True
        or copied.get("entropy_information_gain_shadow_only") is not True
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or copied.get("benchmark_metadata_answer_evaluator_score_reward_or_historical_result_read") is not False
        or copied.get("file_environment_network_model_search_fetch_or_process_accessed") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.42 compact ledger projection drifted")
    compacted, _ = unicode_total.compact_pages(question, pages)
    stable = structure._stable_pages(compacted)
    if copied.get("visible_question_sha256") != hashlib.sha256(question.encode()).hexdigest() or copied.get("visible_schema_sha256") != payload_sha256(parent._visible_schema(question)) or copied.get("input_page_count") != len(stable):
        raise ValueError("V2.49.42 visible input binding drifted")
    if replay and copied != build_projection(question, pages, explicit_groups=explicit_groups):
        raise ValueError("V2.49.42 compact ledger is not reproducible")
    return copied


__all__ = [
    "BLOCK_CHARACTER_CAP",
    "MAXIMUM_PAGE_CHARS",
    "MAXIMUM_QUERY_TERMS",
    "MAXIMUM_VISIBLE_GROUPS",
    "POLICY_ID",
    "ROLE",
    "TOTAL_CHARACTER_CAP",
    "build_projection",
    "payload_sha256",
    "validate_projection",
    "validate_receipt",
]
