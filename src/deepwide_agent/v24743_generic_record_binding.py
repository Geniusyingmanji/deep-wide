"""Generic, label-blind structured-record binding for Unknown table cells.

This I/O-free primitive reverses the unsafe ``model guesses, page verifies``
order used by earlier missing-cell experiments.  An audited adapter first
projects a fetched response into one exact primary identity and explicit
field/value pairs.  This module then binds those records to the visible first
column and visible table headers.  It never invents a value and never mutates a
non-Unknown cell.

One official exact-address record is sufficient only when the adapter attests
that the request address, response schema, and primary identity were bound.
Ordinary structured pages require the same value from at least two
registrably-independent sources.  Any value conflict makes the cell abstain.

The module has no file, environment, process, network, model, search,
benchmark-label, gold, evaluator, reward, or score capability.  Entropy is not
used to determine the sign of task credit.
"""

from __future__ import annotations

import copy
import hashlib
import ipaddress
import json
import re
import unicodedata
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit


POLICY_ID = "v24743_generic_primary_identity_field_value_binding_v1"
ROLE = "v24743_generic_record_binding_result"
RECEIPT_ROLE = "v24743_generic_record_binding_content_free_receipt"
RECORD_ROLE = "v24743_audited_structured_record"
AUTHORITIES = frozenset({"official_exact_record", "ordinary_structured_page"})
MAX_RECORDS = 256
MAX_FIELDS_PER_RECORD = 32
MAX_TEXT_CHARS = 512
UNKNOWN = frozenset(
    {
        "",
        "-",
        "—",
        "?",
        "n/a",
        "na",
        "none",
        "null",
        "unknown",
        "未知",
        "不详",
        "无法确认",
    }
)
COMMON_SECOND_LEVEL_SUFFIXES = frozenset(
    {
        "ac.uk",
        "co.uk",
        "gov.uk",
        "org.uk",
        "com.au",
        "edu.au",
        "gov.au",
        "com.cn",
        "edu.cn",
        "gov.cn",
        "org.cn",
        "co.jp",
        "ac.jp",
        "go.jp",
        "co.kr",
        "ac.kr",
        "go.kr",
        "com.br",
        "com.mx",
        "co.nz",
        "co.in",
    }
)
RECORD_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "record_id",
        "source_host",
        "source_url",
        "authority",
        "exact_address_and_primary_identity_bound",
        "primary_identity",
        "fields",
        "fetch_integrity",
        "adapter_used_visible_identity_and_field_names_only",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "record_payload_sha256",
    }
)
FIELD_KEYS = frozenset({"label", "value"})
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "table_row_count",
        "table_value_cell_count",
        "baseline_unknown_cell_count",
        "record_count",
        "official_record_count",
        "ordinary_record_count",
        "identity_bound_record_count",
        "unmatched_record_count",
        "field_bound_observation_count",
        "unmatched_field_count",
        "candidate_cell_count",
        "official_admitted_cell_count",
        "corroborated_admitted_cell_count",
        "conflicting_cell_count",
        "insufficient_corroboration_cell_count",
        "nonunknown_immutable_proposal_count",
        "changed_cell_count",
        "only_unknown_cells_mutated",
        "ordinary_records_require_two_independent_sources",
        "any_value_conflict_abstains",
        "positive_entropy_or_task_credit_assigned",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_payload_sha256",
    }
)


def _canonical_text(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).split())


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _visible_key(value: object) -> str:
    """Preserve visible case and punctuation; normalize only Unicode/spacing."""

    return _canonical_text(value)


def _safe_text(value: object, *, allow_unknown: bool = False) -> str:
    text = _canonical_text(value)
    if (
        not text
        or len(text) > MAX_TEXT_CHARS
        or any(character in text for character in "\r\n|\0")
        or (not allow_unknown and _is_unknown(text))
    ):
        raise ValueError("V2.47.43 structured text is unsafe or empty")
    return text


def _is_unknown(value: object) -> bool:
    return _canonical_text(value).casefold() in UNKNOWN


def _source_key(host: str) -> str:
    value = str(host).casefold().strip(".")
    if (
        not value
        or len(value) > 253
        or re.fullmatch(r"[a-z0-9.-]+", value) is None
        or ".." in value
    ):
        raise ValueError("V2.47.43 source host is invalid")
    try:
        ipaddress.ip_address(value)
    except ValueError:
        pass
    else:
        raise ValueError("V2.47.43 source host is not registrably attributable")
    labels = value.split(".")
    if (
        len(labels) < 2
        or any(
            not label
            or len(label) > 63
            or label.startswith("-")
            or label.endswith("-")
            for label in labels
        )
    ):
        raise ValueError("V2.47.43 source host is not registrably attributable")
    last_two = ".".join(labels[-2:])
    if last_two in COMMON_SECOND_LEVEL_SUFFIXES:
        if len(labels) < 3:
            raise ValueError("V2.47.43 source host lacks a registrable label")
        return ".".join(labels[-3:])
    return last_two


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        raise ValueError("V2.47.43 table row is malformed")
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def _table_matrix(table: str) -> tuple[list[str], list[list[str]]]:
    lines = [
        line.strip()
        for line in str(table).replace("\r\n", "\n").replace("\r", "\n").splitlines()
        if line.strip()
    ]
    if lines and lines[0] in {"```", "```markdown"}:
        if len(lines) < 5 or lines[-1] != "```":
            raise ValueError("V2.47.43 table fence is malformed")
        lines = lines[1:-1]
    if len(lines) < 3 or any(
        not line.startswith("|") or not line.endswith("|") for line in lines
    ):
        raise ValueError("V2.47.43 canonical table matrix is absent")
    parsed = [_split_table_row(line) for line in lines]
    columns = parsed[0]
    if not columns or any(len(row) != len(columns) for row in parsed):
        raise ValueError("V2.47.43 table width drifted")
    if any(re.fullmatch(r":?-{3,}:?", cell) is None for cell in parsed[1]):
        raise ValueError("V2.47.43 table separator drifted")
    return columns, parsed[2:]


def _render_table(columns: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    return (
        "```markdown\n"
        + "| "
        + " | ".join(columns)
        + " |\n| "
        + " | ".join("---" for _ in columns)
        + " |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
        + "\n```"
    )


def _https_source(url: object, host: object) -> tuple[str, str]:
    try:
        parsed = urlsplit(str(url))
        port = parsed.port
    except ValueError as exc:
        raise ValueError("V2.47.43 structured record URL is invalid") from exc
    hostname = (parsed.hostname or "").casefold().strip(".")
    declared = str(host).casefold().strip(".")
    if (
        parsed.scheme.casefold() != "https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or port is not None
        or ":" in hostname
        or hostname != declared
    ):
        raise ValueError("V2.47.43 structured record source binding drifted")
    canonical_url = parsed._replace(scheme="https", netloc=hostname).geturl()
    return hostname, canonical_url


def build_record(
    *,
    record_id: str,
    source_host: str,
    source_url: str,
    authority: str,
    exact_address_and_primary_identity_bound: bool,
    primary_identity: str,
    fields: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    """Build and seal one adapter-validated structured record."""

    canonical_host, canonical_url = _https_source(source_url, source_host)
    canonical_identity = _safe_text(primary_identity, allow_unknown=False)
    if (
        not isinstance(fields, Sequence)
        or isinstance(fields, (str, bytes))
        or not 1 <= len(fields) <= MAX_FIELDS_PER_RECORD
    ):
        raise ValueError("V2.47.43 structured field vector drifted")
    canonical_fields: list[dict[str, str]] = []
    for item in fields:
        if not isinstance(item, Mapping) or set(item) != FIELD_KEYS:
            raise ValueError("V2.47.43 structured field schema drifted")
        canonical_fields.append(
            {
                "label": _safe_text(item.get("label"), allow_unknown=False),
                "value": _safe_text(item.get("value"), allow_unknown=False),
            }
        )
    value = {
        "artifact_version": 1,
        "role": RECORD_ROLE,
        "policy_id": POLICY_ID,
        "record_id": str(record_id),
        "source_host": canonical_host,
        "source_url": canonical_url,
        "authority": str(authority),
        "exact_address_and_primary_identity_bound": bool(
            exact_address_and_primary_identity_bound
        ),
        "primary_identity": canonical_identity,
        "fields": canonical_fields,
        "fetch_integrity": True,
        "adapter_used_visible_identity_and_field_names_only": True,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    value["record_payload_sha256"] = payload_sha256(value)
    return validate_record(value)


def validate_record(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("record_payload_sha256", None)
    fields = copied.get("fields")
    authority = copied.get("authority")
    try:
        source_host, source_url = _https_source(
            copied.get("source_url"), copied.get("source_host")
        )
        _source_key(source_host)
        identity = _safe_text(copied.get("primary_identity"), allow_unknown=False)
    except ValueError as exc:
        raise ValueError("V2.47.43 structured record identity drifted") from exc
    if (
        set(copied) != RECORD_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECORD_ROLE
        or copied.get("policy_id") != POLICY_ID
        or re.fullmatch(r"S[0-9]{4}", str(copied.get("record_id", ""))) is None
        or authority not in AUTHORITIES
        or not isinstance(
            copied.get("exact_address_and_primary_identity_bound"), bool
        )
        or copied.get("exact_address_and_primary_identity_bound")
        is not (authority == "official_exact_record")
        or not isinstance(fields, Sequence)
        or isinstance(fields, (str, bytes))
        or not 1 <= len(fields) <= MAX_FIELDS_PER_RECORD
        or copied.get("fetch_integrity") is not True
        or copied.get("adapter_used_visible_identity_and_field_names_only")
        is not True
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.43 structured record schema drifted")
    normalized_labels: set[str] = set()
    canonical_fields: list[dict[str, str]] = []
    for raw in fields:
        if not isinstance(raw, Mapping) or set(raw) != FIELD_KEYS:
            raise ValueError("V2.47.43 structured field schema drifted")
        label = _safe_text(raw.get("label"), allow_unknown=False)
        field_value = _safe_text(raw.get("value"), allow_unknown=False)
        normalized = _visible_key(label)
        if not normalized or normalized in normalized_labels:
            raise ValueError("V2.47.43 structured field label is ambiguous")
        normalized_labels.add(normalized)
        canonical_fields.append({"label": label, "value": field_value})
    if (
        copied.get("source_host") != source_host
        or copied.get("source_url") != source_url
        or copied.get("primary_identity") != identity
        or fields != canonical_fields
    ):
        raise ValueError("V2.47.43 structured record is not canonically sealed")
    return copied


def _baseline_matrix(baseline: str) -> tuple[list[str], list[list[str]]]:
    columns, rows = _table_matrix(str(baseline))
    if (
        not 2 <= len(columns) <= 32
        or not rows
        or any(len(row) != len(columns) for row in rows)
        or any(not _canonical_text(value) for value in columns)
    ):
        raise ValueError("V2.47.43 baseline table shape drifted")
    column_keys = [_visible_key(value) for value in columns]
    row_keys = [_visible_key(row[0]) for row in rows]
    if (
        any(not value for value in column_keys)
        or len(set(column_keys)) != len(column_keys)
        or any(not value for value in row_keys)
        or len(set(row_keys)) != len(row_keys)
    ):
        raise ValueError("V2.47.43 baseline identity surface is ambiguous")
    return columns, rows


def bind_records(
    baseline: str, records: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Bind structured records to visible Unknown cells and return a candidate."""

    if (
        not isinstance(records, Sequence)
        or isinstance(records, (str, bytes))
        or len(records) > MAX_RECORDS
    ):
        raise ValueError("V2.47.43 structured record vector drifted")
    validated = [validate_record(item) for item in records]
    record_ids = [item["record_id"] for item in validated]
    if len(set(record_ids)) != len(record_ids):
        raise ValueError("V2.47.43 structured record IDs are not unique")

    columns, rows = _baseline_matrix(baseline)
    column_map = {
        _visible_key(value): index for index, value in enumerate(columns)
    }
    row_map = {
        _visible_key(row[0]): index for index, row in enumerate(rows)
    }
    # coordinate -> exact canonical value -> list[(source, official)]
    support: dict[
        tuple[int, int], dict[str, list[tuple[str, bool]]]
    ] = defaultdict(lambda: defaultdict(list))
    identity_bound_records = field_bound = unmatched_records = unmatched_fields = 0
    official_records = ordinary_records = 0
    for record in validated:
        official = record["authority"] == "official_exact_record"
        official_records += int(official)
        ordinary_records += int(not official)
        row_index = row_map.get(_visible_key(record["primary_identity"]))
        if row_index is None:
            unmatched_records += 1
            continue
        identity_bound_records += 1
        source = _source_key(record["source_host"])
        for raw in record["fields"]:
            column_index = column_map.get(_visible_key(raw["label"]))
            if column_index is None or column_index == 0:
                unmatched_fields += 1
                continue
            value = _safe_text(raw["value"], allow_unknown=False)
            support[(row_index, column_index)][value].append((source, official))
            field_bound += 1

    output = [list(row) for row in rows]
    official_admitted = corroborated_admitted = conflicts = ambiguous = immutable = 0
    considered = 0
    for coordinate, candidates in sorted(support.items()):
        row_index, column_index = coordinate
        considered += 1
        if not _is_unknown(rows[row_index][column_index]):
            immutable += 1
            continue
        if len(candidates) != 1:
            conflicts += 1
            continue
        value, observations = next(iter(candidates.items()))
        sources = {source for source, _official in observations}
        has_official = any(official for _source, official in observations)
        if has_official:
            output[row_index][column_index] = value
            official_admitted += 1
        elif len(sources) >= 2:
            output[row_index][column_index] = value
            corroborated_admitted += 1
        else:
            ambiguous += 1

    candidate = _render_table(columns, output)
    changed = sum(
        before != after
        for source, target in zip(rows, output)
        for before, after in zip(source[1:], target[1:])
    )
    receipt = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "table_row_count": len(rows),
        "table_value_cell_count": len(rows) * (len(columns) - 1),
        "baseline_unknown_cell_count": sum(
            _is_unknown(value) for row in rows for value in row[1:]
        ),
        "record_count": len(validated),
        "official_record_count": official_records,
        "ordinary_record_count": ordinary_records,
        "identity_bound_record_count": identity_bound_records,
        "unmatched_record_count": unmatched_records,
        "field_bound_observation_count": field_bound,
        "unmatched_field_count": unmatched_fields,
        "candidate_cell_count": considered,
        "official_admitted_cell_count": official_admitted,
        "corroborated_admitted_cell_count": corroborated_admitted,
        "conflicting_cell_count": conflicts,
        "insufficient_corroboration_cell_count": ambiguous,
        "nonunknown_immutable_proposal_count": immutable,
        "changed_cell_count": changed,
        "only_unknown_cells_mutated": True,
        "ordinary_records_require_two_independent_sources": True,
        "any_value_conflict_abstains": True,
        "positive_entropy_or_task_credit_assigned": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    result = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "baseline_sha256": hashlib.sha256(str(baseline).encode()).hexdigest(),
        "candidate": candidate,
        "candidate_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        "receipt": receipt,
    }
    result["result_payload_sha256"] = payload_sha256(result)
    return validate_result(result, baseline=baseline)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    count_fields = (
        "table_row_count",
        "table_value_cell_count",
        "baseline_unknown_cell_count",
        "record_count",
        "official_record_count",
        "ordinary_record_count",
        "identity_bound_record_count",
        "unmatched_record_count",
        "field_bound_observation_count",
        "unmatched_field_count",
        "candidate_cell_count",
        "official_admitted_cell_count",
        "corroborated_admitted_cell_count",
        "conflicting_cell_count",
        "insufficient_corroboration_cell_count",
        "nonunknown_immutable_proposal_count",
        "changed_cell_count",
    )
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in count_fields
        )
        or copied.get("record_count")
        != copied.get("official_record_count") + copied.get("ordinary_record_count")
        or copied.get("identity_bound_record_count")
        + copied.get("unmatched_record_count")
        != copied.get("record_count")
        or copied.get("changed_cell_count")
        != copied.get("official_admitted_cell_count")
        + copied.get("corroborated_admitted_cell_count")
        or copied.get("candidate_cell_count")
        != copied.get("official_admitted_cell_count")
        + copied.get("corroborated_admitted_cell_count")
        + copied.get("conflicting_cell_count")
        + copied.get("insufficient_corroboration_cell_count")
        + copied.get("nonunknown_immutable_proposal_count")
        or copied.get("only_unknown_cells_mutated") is not True
        or copied.get("ordinary_records_require_two_independent_sources") is not True
        or copied.get("any_value_conflict_abstains") is not True
        or copied.get("positive_entropy_or_task_credit_assigned") is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get(
            "file_environment_network_model_search_fetch_or_process_accessed"
        )
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.43 binding receipt drifted")
    return copied


def validate_result(
    value: Mapping[str, Any],
    *,
    baseline: str | None = None,
    records: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    candidate = copied.get("candidate")
    receipt = validate_receipt(copied.get("receipt", {}))
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "baseline_sha256",
            "candidate",
            "candidate_sha256",
            "receipt",
            "result_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(candidate, str)
        or copied.get("candidate_sha256")
        != hashlib.sha256(candidate.encode()).hexdigest()
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.43 binding result drifted")
    if baseline is not None:
        if copied.get("baseline_sha256") != hashlib.sha256(
            str(baseline).encode()
        ).hexdigest():
            raise ValueError("V2.47.43 baseline binding drifted")
        baseline_columns, baseline_rows = _baseline_matrix(baseline)
        candidate_columns, candidate_rows = _baseline_matrix(candidate)
        if (
            candidate_columns != baseline_columns
            or len(candidate_rows) != len(baseline_rows)
            or receipt.get("table_row_count") != len(baseline_rows)
            or receipt.get("table_value_cell_count")
            != len(baseline_rows) * (len(baseline_columns) - 1)
            or receipt.get("baseline_unknown_cell_count")
            != sum(
                _is_unknown(value) for row in baseline_rows for value in row[1:]
            )
            or any(
                source[0] != target[0]
                for source, target in zip(baseline_rows, candidate_rows)
            )
            or any(
                not _is_unknown(before) and before != after
                for source, target in zip(baseline_rows, candidate_rows)
                for before, after in zip(source[1:], target[1:])
            )
            or receipt.get("changed_cell_count")
            != sum(
                before != after
                for source, target in zip(baseline_rows, candidate_rows)
                for before, after in zip(source[1:], target[1:])
            )
        ):
            raise ValueError("V2.47.43 candidate changed immutable table structure")
    if records is not None:
        # Recompute only after the structural checks above.  Avoid recursion by
        # comparing against a call without forwarding the replay arguments.
        replay = bind_records(baseline or "", records) if baseline is not None else None
        if replay is None or replay != copied:
            raise ValueError("V2.47.43 binding replay drifted")
    return copied


__all__ = [
    "AUTHORITIES",
    "POLICY_ID",
    "RECORD_ROLE",
    "bind_records",
    "build_record",
    "validate_receipt",
    "validate_record",
    "validate_result",
]
