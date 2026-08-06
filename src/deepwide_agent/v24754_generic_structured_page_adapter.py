"""Pure generic structured-page adapter for V2.47.43 record binding.

The adapter consumes a canonical baseline table and already-fetched public
pages supplied by its caller.  It recognizes only two replayable structures:

* a Markdown table whose first header is the exact visible identity column and
  whose remaining headers are exact visible value-column labels; or
* an exact visible identity on its own line followed by bounded exact
  ``label: value`` or ``label | value`` records.

Every observation becomes an ordinary V2.47.43 record.  Consequently a cell
can change only when two registrably-independent hosts support the same value;
one source abstains and any value conflict abstains.  This module has no file,
environment, process, network, model, search, benchmark-label, evaluator,
reward, score, or credential capability.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

from . import v24743_generic_record_binding as binder


POLICY_ID = "v24754_generic_exact_structured_page_adapter_v1"
ROLE = "v24754_generic_structured_page_binding_result"
RECEIPT_ROLE = "v24754_generic_structured_page_content_free_receipt"
MAX_PAGES = 32
MAX_PAGE_CHARACTERS = 100_000
MAX_TABLE_ROWS_PER_PAGE = 256
MAX_ENTITY_BLOCK_LINES = 16
PAGE_KEYS = frozenset({"final_url", "content", "fetch_integrity"})
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "baseline_sha256",
        "records",
        "binding_result",
        "candidate",
        "candidate_sha256",
        "receipt",
        "result_payload_sha256",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "input_page_count",
        "accepted_fetch_integrity_page_count",
        "page_with_exact_record_count",
        "exact_markdown_table_count",
        "exact_entity_block_count",
        "exact_identity_observation_count",
        "exact_field_value_observation_count",
        "ambiguous_same_page_field_count",
        "ordinary_record_count",
        "registrable_record_source_count",
        "binding_receipt",
        "only_final_fetch_url_accepted",
        "exact_visible_identity_required",
        "exact_visible_field_label_required",
        "semantic_alias_or_nearby_value_inference_used",
        "all_records_are_ordinary_structured_pages",
        "additional_model_requests",
        "additional_logical_queries",
        "additional_search_batches",
        "additional_provider_search_calls",
        "additional_fetch_calls",
        "positive_entropy_or_task_credit_assigned",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_payload_sha256",
    }
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _canonical(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).split())


def _page(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or set(raw) != PAGE_KEYS:
        raise ValueError("V2.47.54 fetched-page schema drifted")
    final_url = str(raw.get("final_url", ""))
    content = str(raw.get("content", ""))
    try:
        parsed = urlsplit(final_url)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("V2.47.54 final URL drifted") from exc
    host = (parsed.hostname or "").casefold().strip(".")
    if (
        raw.get("fetch_integrity") is not True
        or parsed.scheme.casefold() != "https"
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.fragment
        or not content.strip()
        or len(content) > MAX_PAGE_CHARACTERS
        or "\x00" in content
    ):
        raise ValueError("V2.47.54 fetched page is not integrity-bound")
    canonical_url = parsed._replace(scheme="https", netloc=host).geturl()
    # Reuse the binder's stricter host and URL validation before parsing text.
    binder._source_key(host)
    binder._https_source(canonical_url, host)
    return {
        "final_url": canonical_url,
        "source_host": host,
        "content": unicodedata.normalize("NFKC", content),
    }


def _cells(line: str) -> list[str] | None:
    raw = unicodedata.normalize("NFKC", str(line)).strip()
    if not (raw.startswith("|") and raw.endswith("|")):
        return None
    values = [_canonical(value) for value in raw[1:-1].split("|")]
    return values if values else None


def _rule(values: Sequence[str]) -> bool:
    return bool(values) and all(
        re.fullmatch(r":?-{3,}:?", value.replace(" ", "")) is not None
        for value in values
    )


def _safe_value(value: object) -> str | None:
    try:
        return binder._safe_text(value, allow_unknown=False)
    except ValueError:
        return None


def _table_observations(
    lines: Sequence[str],
    *,
    columns: Sequence[str],
    identities: set[str],
) -> tuple[dict[tuple[str, str], set[str]], int]:
    column_set = set(columns[1:])
    observations: dict[tuple[str, str], set[str]] = defaultdict(set)
    tables = 0
    rows_seen = 0
    index = 0
    while index + 1 < len(lines):
        header = _cells(lines[index])
        separator = _cells(lines[index + 1])
        if (
            header is None
            or separator is None
            or len(header) < 2
            or len(separator) != len(header)
            or not _rule(separator)
            or header[0] != columns[0]
            or len(set(header)) != len(header)
            or any(label not in column_set for label in header[1:])
        ):
            index += 1
            continue
        tables += 1
        row_index = index + 2
        while row_index < len(lines):
            row = _cells(lines[row_index])
            if row is None or len(row) != len(header) or _rule(row):
                break
            rows_seen += 1
            if rows_seen > MAX_TABLE_ROWS_PER_PAGE:
                raise ValueError("V2.47.54 structured table row cap exceeded")
            identity = row[0]
            if identity in identities:
                for label, raw_value in zip(header[1:], row[1:], strict=True):
                    value = _safe_value(raw_value)
                    if value is not None:
                        observations[(identity, label)].add(value)
            row_index += 1
        index = max(index + 1, row_index)
    return observations, tables


def _label_value(
    line: str, *, value_columns: set[str]
) -> tuple[str, str] | None:
    cells = _cells(line)
    if cells is not None and len(cells) == 2:
        label, raw_value = cells
    elif str(line).count("|") == 1:
        label, raw_value = (_canonical(value) for value in str(line).split("|", 1))
    else:
        match = re.fullmatch(r"\s*([^:：\t|]{1,120})\s*[:：\t]\s*(.+?)\s*", line)
        if match is None:
            return None
        label, raw_value = _canonical(match.group(1)), _canonical(match.group(2))
    if label not in value_columns:
        return None
    value = _safe_value(raw_value)
    return (label, value) if value is not None else None


def _block_observations(
    lines: Sequence[str],
    *,
    columns: Sequence[str],
    identities: set[str],
) -> tuple[dict[tuple[str, str], set[str]], int]:
    observations: dict[tuple[str, str], set[str]] = defaultdict(set)
    value_columns = set(columns[1:])
    blocks = 0
    for index, raw_identity in enumerate(lines):
        identity = _canonical(raw_identity)
        if identity not in identities or _cells(raw_identity) is not None:
            continue
        block_observed = False
        for following in lines[
            index + 1 : index + 1 + MAX_ENTITY_BLOCK_LINES
        ]:
            if not following.strip():
                break
            canonical = _canonical(following)
            if canonical in identities:
                break
            bound = _label_value(following, value_columns=value_columns)
            if bound is None:
                # Exact records must be contiguous after the identity line;
                # prose or an unknown label terminates the record scope.
                break
            label, value = bound
            observations[(identity, label)].add(value)
            block_observed = True
        blocks += int(block_observed)
    return observations, blocks


def _merge_observations(
    *values: Mapping[tuple[str, str], set[str]],
) -> dict[tuple[str, str], set[str]]:
    output: dict[tuple[str, str], set[str]] = defaultdict(set)
    for value in values:
        for coordinate, candidates in value.items():
            output[coordinate].update(candidates)
    return output


def _compute(
    baseline: str, pages: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    if (
        not isinstance(pages, Sequence)
        or isinstance(pages, (str, bytes))
        or len(pages) > MAX_PAGES
    ):
        raise ValueError("V2.47.54 fetched-page vector drifted")
    columns, rows = binder._baseline_matrix(baseline)
    identities = {row[0] for row in rows}
    records: list[dict[str, Any]] = []
    table_count = block_count = pages_with_records = 0
    exact_identity_observations = exact_field_observations = ambiguous = 0
    sources: set[str] = set()
    for raw in pages:
        page = _page(raw)
        lines = page["content"].replace("\r\n", "\n").replace("\r", "\n").split("\n")
        table, tables = _table_observations(
            lines, columns=columns, identities=identities
        )
        block, blocks = _block_observations(
            lines, columns=columns, identities=identities
        )
        observations = _merge_observations(table, block)
        table_count += tables
        block_count += blocks
        pages_with_records += int(bool(observations))
        exact_identity_observations += len(
            {identity for identity, _label in observations}
        )
        ambiguous += sum(len(candidates) > 1 for candidates in observations.values())
        for (identity, label), candidates in sorted(observations.items()):
            for candidate in sorted(candidates):
                exact_field_observations += 1
                if len(records) >= binder.MAX_RECORDS:
                    raise ValueError("V2.47.54 ordinary record cap exceeded")
                records.append(
                    binder.build_record(
                        record_id=f"S{len(records) + 1:04d}",
                        source_host=page["source_host"],
                        source_url=page["final_url"],
                        authority="ordinary_structured_page",
                        exact_address_and_primary_identity_bound=False,
                        primary_identity=identity,
                        fields=[{"label": label, "value": candidate}],
                    )
                )
                sources.add(binder._source_key(page["source_host"]))
    binding = binder.bind_records(baseline, records)
    receipt = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "input_page_count": len(pages),
        "accepted_fetch_integrity_page_count": len(pages),
        "page_with_exact_record_count": pages_with_records,
        "exact_markdown_table_count": table_count,
        "exact_entity_block_count": block_count,
        "exact_identity_observation_count": exact_identity_observations,
        "exact_field_value_observation_count": exact_field_observations,
        "ambiguous_same_page_field_count": ambiguous,
        "ordinary_record_count": len(records),
        "registrable_record_source_count": len(sources),
        "binding_receipt": copy.deepcopy(binding["receipt"]),
        "only_final_fetch_url_accepted": True,
        "exact_visible_identity_required": True,
        "exact_visible_field_label_required": True,
        "semantic_alias_or_nearby_value_inference_used": False,
        "all_records_are_ordinary_structured_pages": True,
        "additional_model_requests": 0,
        "additional_logical_queries": 0,
        "additional_search_batches": 0,
        "additional_provider_search_calls": 0,
        "additional_fetch_calls": 0,
        "positive_entropy_or_task_credit_assigned": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    candidate = binding["candidate"]
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "baseline_sha256": hashlib.sha256(str(baseline).encode()).hexdigest(),
        "records": records,
        "binding_result": binding,
        "candidate": candidate,
        "candidate_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        "receipt": receipt,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return value


def build_generic_structured_page_binding(
    baseline: str, pages: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    value = _compute(baseline, pages)
    return validate_result(value, baseline=baseline)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    counts = (
        "input_page_count",
        "accepted_fetch_integrity_page_count",
        "page_with_exact_record_count",
        "exact_markdown_table_count",
        "exact_entity_block_count",
        "exact_identity_observation_count",
        "exact_field_value_observation_count",
        "ambiguous_same_page_field_count",
        "ordinary_record_count",
        "registrable_record_source_count",
        "additional_model_requests",
        "additional_logical_queries",
        "additional_search_batches",
        "additional_provider_search_calls",
        "additional_fetch_calls",
    )
    binding_receipt = copied.get("binding_receipt")
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or copied.get("accepted_fetch_integrity_page_count")
        != copied.get("input_page_count")
        or copied.get("page_with_exact_record_count")
        > copied.get("input_page_count")
        or copied.get("ordinary_record_count")
        != copied.get("exact_field_value_observation_count")
        or not isinstance(binding_receipt, Mapping)
        or binder.validate_receipt(binding_receipt) != dict(binding_receipt)
        or binding_receipt.get("record_count")
        != copied.get("ordinary_record_count")
        or binding_receipt.get("official_record_count") != 0
        or binding_receipt.get("ordinary_record_count")
        != copied.get("ordinary_record_count")
        or copied.get("only_final_fetch_url_accepted") is not True
        or copied.get("exact_visible_identity_required") is not True
        or copied.get("exact_visible_field_label_required") is not True
        or copied.get("semantic_alias_or_nearby_value_inference_used") is not False
        or copied.get("all_records_are_ordinary_structured_pages") is not True
        or any(copied.get(name) != 0 for name in counts[-5:])
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
        raise ValueError("V2.47.54 adapter receipt drifted")
    return copied


def validate_result(
    value: Mapping[str, Any],
    *,
    baseline: str | None = None,
    pages: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    records = copied.get("records")
    binding = copied.get("binding_result")
    candidate = copied.get("candidate")
    receipt = validate_receipt(copied.get("receipt", {}))
    if (
        set(copied) != RESULT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(records, list)
        or any(binder.validate_record(record) != record for record in records)
        or not isinstance(binding, Mapping)
        or binder.validate_result(binding) != dict(binding)
        or not isinstance(candidate, str)
        or copied.get("candidate_sha256")
        != hashlib.sha256(candidate.encode()).hexdigest()
        or candidate != binding.get("candidate")
        or copied.get("baseline_sha256") != binding.get("baseline_sha256")
        or receipt.get("ordinary_record_count") != len(records)
        or receipt.get("binding_receipt") != binding.get("receipt")
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.54 adapter result drifted")
    if baseline is not None:
        if copied.get("baseline_sha256") != hashlib.sha256(
            str(baseline).encode()
        ).hexdigest():
            raise ValueError("V2.47.54 baseline binding drifted")
        binder.validate_result(binding, baseline=baseline, records=records)
    if pages is not None:
        if baseline is None or _compute(baseline, pages) != copied:
            raise ValueError("V2.47.54 adapter replay drifted")
    return copied


__all__ = [
    "PAGE_KEYS",
    "POLICY_ID",
    "build_generic_structured_page_binding",
    "validate_receipt",
    "validate_result",
]
