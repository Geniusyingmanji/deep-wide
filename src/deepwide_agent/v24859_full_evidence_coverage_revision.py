"""Conservative full-evidence table coverage revision.

This pure kernel addresses the evidence-to-table conversion bottleneck found
after V2.48.57.  A model may propose a larger or corrected table, but the
kernel independently scans same-forward fetched pages and admits only changes
with repeated row-local support from independent registrable sources.

Baseline rows are immutable and never deleted.  Unknown fills require two
independent sources, known-value overrides require three, and every cell of a
new row must pass the two-source gate.  Entropy reduction is recorded only as
a shadow measurement after the source-count decision; it never controls
admission.  The kernel has no file, environment, process, network, model,
benchmark-label, gold, evaluator, score, reward, or historical-result access.
"""

from __future__ import annotations

import copy
import hashlib
import ipaddress
import json
import math
import re
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


POLICY_ID = "v24859_full_evidence_source_threshold_coverage_revision_v1"
ROLE = "v24859_full_evidence_coverage_revision_receipt"
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
        "not available",
        "not found",
        "未知",
        "不详",
        "无法确认",
    }
)
MINIMUM_UNKNOWN_SOURCES = 2
MINIMUM_OVERRIDE_SOURCES = 3
MINIMUM_NEW_ROW_SOURCES = 2
LOCAL_WINDOW_RADIUS = 384
MAXIMUM_RECORD_CHARS = 1_200
MAXIMUM_PAGES = 32
MAXIMUM_ROWS = 512
MAXIMUM_COLUMNS = 32
MAXIMUM_BINDING_SPAN = 320

_TRACKING_QUERY_KEYS = frozenset(
    {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "ref_src"}
)
_COMMON_SECOND_LEVEL_SUFFIXES = frozenset(
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

_HTML_RECORD_BOUNDARY = re.compile(
    r"</?(?:article|br|dd|div|dt|h[1-6]|li|p|section|td|th|tr)\b[^>]*>",
    flags=re.IGNORECASE,
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


def _clean(value: object) -> str:
    return " ".join(
        unicodedata.normalize("NFKC", "" if value is None else str(value))
        .replace("\x00", " ")
        .casefold()
        .split()
    )


def _support_normalize(value: object) -> str:
    return "".join(
        character
        for character in _clean(value)
        if character.isalnum() or "\u4e00" <= character <= "\u9fff"
    )


def _identity_key(value: object) -> str:
    """Normalize case and spacing without erasing identity punctuation."""

    return _clean(value)


def _is_unknown(value: object) -> bool:
    return _clean(value) in UNKNOWN


def _entropy(probability: float) -> float:
    if probability <= 0 or probability >= 1:
        return 0.0
    return -probability * math.log(probability) - (
        1 - probability
    ) * math.log(1 - probability)


def _shadow_information_gain(*, support_count: int, override: bool) -> float:
    prior = 0.30 if override else 0.45
    likelihood_ratio = 4.0 ** max(0, support_count)
    odds = prior / (1 - prior) * likelihood_ratio
    posterior = odds / (1 + odds)
    return round(max(0.0, _entropy(prior) - _entropy(posterior)), 12)


def _canonicalize_url(value: object) -> str:
    """Return a credential-free canonical HTTP(S) URL using stdlib only."""

    if not isinstance(value, str):
        return ""
    raw = value.strip()
    if not raw:
        return ""
    try:
        split = urlsplit(raw)
        host = split.hostname
        port = split.port
    except ValueError:
        return ""
    if (
        split.scheme.casefold() not in {"http", "https"}
        or not host
        or split.username is not None
        or split.password is not None
    ):
        return ""
    hostname = host.casefold().rstrip(".")
    try:
        hostname.encode("ascii")
    except UnicodeEncodeError:
        return ""
    default_port = (split.scheme.casefold() == "http" and port == 80) or (
        split.scheme.casefold() == "https" and port == 443
    )
    netloc = hostname if port is None or default_port else f"{hostname}:{port}"
    try:
        query = [
            (key, item)
            for key, item in parse_qsl(split.query, keep_blank_values=True)
            if not key.casefold().startswith("utm_")
            and key.casefold() not in _TRACKING_QUERY_KEYS
        ]
    except ValueError:
        return ""
    path = split.path.rstrip("/") or "/"
    return urlunsplit(
        (split.scheme.casefold(), netloc, path, urlencode(query), "")
    )


def _split_pipe_row(line: str) -> list[str]:
    """Split one Markdown row while preserving escaped literal pipes."""

    raw = str(line).strip()
    if not (raw.startswith("|") and raw.endswith("|")):
        return []
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for character in raw:
        if character == "|" and not escaped:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(character)
        if character == "\\" and not escaped:
            escaped = True
        else:
            escaped = False
    cells.append("".join(current).strip())
    if cells and cells[0] == "":
        cells.pop(0)
    if cells and cells[-1] == "":
        cells.pop()
    return cells if len(cells) >= 1 else []


def _normalize_column(value: object) -> str:
    return re.sub(r"[\s`*_：:]+", "", str(value or "")).casefold()


def _extract_valid_markdown_table(
    text: str, columns: Sequence[str]
) -> tuple[str | None, list[str]]:
    lines = str(text or "").replace("\r\n", "\n").splitlines()
    groups: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            current.append(stripped)
        elif current:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    for group in groups:
        if len(group) < 3:
            continue
        header = _split_pipe_row(group[0])
        separator = _split_pipe_row(group[1])
        rows = [_split_pipe_row(line) for line in group[2:]]
        if not header or len(header) != len(columns):
            continue
        if [_normalize_column(item) for item in header] != [
            _normalize_column(item) for item in columns
        ]:
            continue
        if len(separator) != len(header) or not _separator_row(separator):
            continue
        valid_rows = [
            row for row in rows if len(row) == len(header) and all(row)
        ]
        if not valid_rows:
            continue
        return _render(header, valid_rows), []
    return None, [
        "no table with the exact required header was found",
        "a table requires a separator and at least one non-empty data row",
    ]


@dataclass(frozen=True)
class EvidencePage:
    evidence_id: str
    url: str
    content: str
    fetch_integrity: bool = False

    def validate(self) -> None:
        if re.fullmatch(r"E\d{4}", self.evidence_id) is None:
            raise ValueError("V2.48.59 evidence ID is invalid")
        canonical = _canonicalize_url(self.url)
        host = (urlsplit(canonical).hostname or "").casefold()
        if not canonical or not host:
            raise ValueError("V2.48.59 evidence URL is invalid")
        _registrable_source(host)
        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("V2.48.59 evidence content is empty")
        if not isinstance(self.fetch_integrity, bool):
            raise ValueError("V2.48.59 fetch integrity is not boolean")

    @property
    def source(self) -> str:
        self.validate()
        host = (urlsplit(_canonicalize_url(self.url)).hostname or "").casefold()
        return _registrable_source(host)


def _registrable_source(host: str) -> str:
    value = str(host).strip(".").casefold()
    if (
        not value
        or len(value) > 253
        or re.fullmatch(r"[a-z0-9.-]+", value) is None
        or ".." in value
    ):
        raise ValueError("V2.48.59 source host is invalid")
    try:
        ipaddress.ip_address(value)
    except ValueError:
        pass
    else:
        raise ValueError("V2.48.59 numeric host is not an attributable source")
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
        raise ValueError("V2.48.59 source host is not attributable")
    last_two = ".".join(labels[-2:])
    if last_two in _COMMON_SECOND_LEVEL_SUFFIXES:
        if len(labels) < 3:
            raise ValueError("V2.48.59 source host lacks a registrable label")
        return ".".join(labels[-3:])
    return last_two


def _coerce_page(value: EvidencePage | Mapping[str, Any], ordinal: int) -> EvidencePage:
    if isinstance(value, EvidencePage):
        page = value
    elif isinstance(value, Mapping):
        url = str(
            value.get("requested_url")
            or value.get("fetch_url")
            or value.get("url")
            or ""
        )
        page = EvidencePage(
            evidence_id=str(value.get("evidence_id") or f"E{ordinal:04d}"),
            url=url,
            content=str(value.get("raw_content") or value.get("content") or ""),
            fetch_integrity=value.get("fetch_integrity", False),
        )
    else:
        raise ValueError("V2.48.59 evidence page schema drifted")
    page.validate()
    return page


def _stable_pages(
    values: Sequence[EvidencePage | Mapping[str, Any]],
) -> list[EvidencePage]:
    if isinstance(values, (str, bytes)) or len(values) > MAXIMUM_PAGES:
        raise ValueError("V2.48.59 evidence vector is invalid")
    output: list[EvidencePage] = []
    seen_urls: set[str] = set()
    seen_ids: set[str] = set()
    for ordinal, raw in enumerate(values, 1):
        page = _coerce_page(raw, ordinal)
        canonical = _canonicalize_url(page.url)
        if page.evidence_id in seen_ids:
            raise ValueError("V2.48.59 duplicate evidence ID")
        seen_ids.add(page.evidence_id)
        if canonical in seen_urls:
            continue
        seen_urls.add(canonical)
        output.append(page)
    return output


def prepare_evidence_pages(
    values: Sequence[EvidencePage | Mapping[str, Any]],
) -> tuple[EvidencePage, ...]:
    """Validate and deterministically deduplicate one same-forward page vector."""

    return tuple(_stable_pages(values))


def _matrix(table: str) -> tuple[list[str], list[list[str]]]:
    groups = _markdown_groups(table)
    if len(groups) != 1:
        raise ValueError("V2.48.59 canonical table grouping drifted")
    rows = groups[0]
    if not 3 <= len(rows) <= MAXIMUM_ROWS + 2:
        raise ValueError("V2.48.59 canonical table row count drifted")
    columns = rows[0]
    if not 1 <= len(columns) <= MAXIMUM_COLUMNS:
        raise ValueError("V2.48.59 canonical table width drifted")
    if any(len(row) != len(columns) for row in rows):
        raise ValueError("V2.48.59 table row width drifted")
    if any(
        re.fullmatch(r":?-{3,}:?", value.replace(" ", "")) is None
        for value in rows[1]
    ):
        raise ValueError("V2.48.59 table separator drifted")
    return list(columns), [list(row) for row in rows[2:]]


def _render(columns: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    return (
        "```markdown\n| "
        + " | ".join(columns)
        + " |\n| "
        + " | ".join("---" for _ in columns)
        + " |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
        + "\n```"
    )


def _canonical_candidate(proposed: str, columns: Sequence[str]) -> str | None:
    value, _errors = _extract_valid_markdown_table(proposed, columns)
    return value


def _column_tokens(column: str) -> tuple[str, ...]:
    values = [
        match.group(0)
        for match in re.finditer(
            r"[a-z0-9]{3,}|[\u4e00-\u9fff]{2,}", _clean(column)
        )
        if match.group(0)
        not in {"name", "value", "result", "名称", "结果", "数据"}
    ]
    exact = _support_normalize(column)
    if exact and exact not in values:
        values.append(exact)
    return tuple(dict.fromkeys(values))


def _term_pattern(value: object) -> re.Pattern[str] | None:
    term = _clean(value)
    if len(_support_normalize(term)) < 2:
        return None
    body = r"\s+".join(re.escape(part) for part in term.split())
    ascii_left = bool(term and term[0].isascii() and term[0].isalnum())
    ascii_right = bool(term and term[-1].isascii() and term[-1].isalnum())
    return re.compile(
        (r"(?<![\w])" if ascii_left else "")
        + body
        + (r"(?![\w])" if ascii_right else ""),
        flags=re.IGNORECASE,
    )


def _term_matches(text: str, value: object) -> list[re.Match[str]]:
    pattern = _term_pattern(value)
    return [] if pattern is None else list(pattern.finditer(text))


def _logical_records(content: str) -> list[str]:
    text = unicodedata.normalize("NFKC", content).replace("\r\n", "\n")
    text = _HTML_RECORD_BOUNDARY.sub("\n", text)
    output: list[str] = []
    for raw_line in text.splitlines():
        line = " ".join(raw_line.casefold().split())
        if not line:
            continue
        # Lines and HTML blocks are record boundaries.  Markdown rows therefore
        # cannot lend cells across rows, while short prose blocks retain common
        # ``Entity. Field: value.`` layouts used by fetched pages.
        output.append(line)
    return output


def _row_windows(content: str, row_key: str) -> list[str]:
    output: list[str] = []
    for record in _logical_records(content):
        for match in _term_matches(record, row_key):
            if len(record) <= MAXIMUM_RECORD_CHARS:
                output.append(record)
            else:
                output.append(
                    record[
                        max(0, match.start() - LOCAL_WINDOW_RADIUS) : min(
                            len(record), match.end() + LOCAL_WINDOW_RADIUS
                        )
                    ]
                )
    return output


def _markdown_groups(content: str) -> list[list[list[str]]]:
    groups: list[list[list[str]]] = []
    current: list[list[str]] = []
    for raw in unicodedata.normalize("NFKC", content).replace("\r\n", "\n").splitlines():
        stripped = raw.strip()
        cells = _split_pipe_row(stripped) if stripped.startswith("|") and stripped.endswith("|") else []
        if cells:
            current.append(cells)
        elif current:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def _separator_row(row: Sequence[str]) -> bool:
    return bool(row) and all(
        re.fullmatch(r":?-{3,}:?", value.replace(" ", "")) is not None
        for value in row
    )


def _table_supports_row(content: str, row_key: str) -> bool:
    target = _identity_key(row_key)
    if not target:
        return False
    for group in _markdown_groups(content):
        for index, row in enumerate(group):
            if index <= 1 or _separator_row(row):
                continue
            if row and _identity_key(row[0]) == target:
                return True
    return False


def _table_supports_cell(
    content: str, row_key: str, column: str, value: str
) -> bool:
    target_row = _identity_key(row_key)
    target_column = _identity_key(column)
    target_value = _identity_key(value)
    if not target_row or not target_column or not target_value:
        return False
    for group in _markdown_groups(content):
        if len(group) < 3:
            continue
        for header_index in range(len(group) - 2):
            header = group[header_index]
            separator = group[header_index + 1]
            if len(separator) != len(header) or not _separator_row(separator):
                continue
            matching_columns = [
                index
                for index, header_cell in enumerate(header)
                if _identity_key(header_cell) == target_column
            ]
            for row in group[header_index + 2 :]:
                if len(row) != len(header) or _separator_row(row):
                    continue
                if not row or _identity_key(row[0]) != target_row:
                    continue
                if any(_identity_key(row[index]) == target_value for index in matching_columns):
                    return True
    return False


def _supports_cell(page: EvidencePage, row_key: str, column: str, value: str) -> bool:
    if not page.fetch_integrity or _is_unknown(value):
        return False
    normalized_value = _identity_key(value)
    if not normalized_value or normalized_value in {
        _identity_key(row_key),
        _identity_key(column),
    }:
        return False
    if _table_supports_cell(page.content, row_key, column, value):
        return True
    tokens = _column_tokens(column)
    for window in _row_windows(page.content, row_key):
        row_matches = _term_matches(window, row_key)
        value_matches = _term_matches(window, value)
        column_matches = [
            match for token in tokens for match in _term_matches(window, token)
        ]
        for row_match in row_matches:
            for value_match in value_matches:
                for column_match in column_matches:
                    starts = (
                        row_match.start(),
                        column_match.start(),
                        value_match.start(),
                    )
                    if max(starts) - min(starts) <= MAXIMUM_BINDING_SPAN:
                        return True
    return False


def _row_sources(pages: Sequence[EvidencePage], row_key: str) -> dict[str, str]:
    output: dict[str, str] = {}
    for page in pages:
        if page.fetch_integrity and (
            _table_supports_row(page.content, row_key)
            or _row_windows(page.content, row_key)
        ):
            output.setdefault(page.source, page.evidence_id)
    return output


def _cell_sources(
    pages: Sequence[EvidencePage], row_key: str, column: str, value: str
) -> dict[str, str]:
    output: dict[str, str] = {}
    for page in pages:
        if _supports_cell(page, row_key, column, value):
            output.setdefault(page.source, page.evidence_id)
    return output


def _receipt(
    *,
    baseline_rows: int,
    proposed_rows: int,
    final_rows: int,
    table_column_count: int,
    proposed_existing_cell_changes: int,
    admitted_unknown_fills: int,
    admitted_overrides: int,
    proposed_new_rows: int,
    admitted_new_rows: int,
    rejected_partial_new_rows: int,
    support_counts: Sequence[int],
    admitted_unknown_support_counts: Sequence[int],
    admitted_override_support_counts: Sequence[int],
    admitted_new_row_support_counts: Sequence[int],
    shadow_information_gain_nats: float,
) -> dict[str, Any]:
    distribution = Counter(int(value) for value in support_counts)
    unknown_distribution = Counter(
        int(value) for value in admitted_unknown_support_counts
    )
    override_distribution = Counter(
        int(value) for value in admitted_override_support_counts
    )
    new_row_distribution = Counter(
        int(value) for value in admitted_new_row_support_counts
    )
    admitted_distribution = unknown_distribution + override_distribution + new_row_distribution
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "baseline_row_count": baseline_rows,
        "proposed_row_count": proposed_rows,
        "final_row_count": final_rows,
        "table_column_count": table_column_count,
        "proposed_existing_cell_changes": proposed_existing_cell_changes,
        "admitted_existing_unknown_fills": admitted_unknown_fills,
        "admitted_existing_overrides": admitted_overrides,
        "proposed_new_rows": proposed_new_rows,
        "admitted_new_rows": admitted_new_rows,
        "rejected_partial_new_rows": rejected_partial_new_rows,
        "support_checks": len(support_counts),
        "admitted_support_checks": (
            len(admitted_unknown_support_counts)
            + len(admitted_override_support_counts)
            + len(admitted_new_row_support_counts)
        ),
        "support_source_count_distribution": {
            str(key): distribution[key] for key in sorted(distribution)
        },
        "admitted_support_source_count_distribution": {
            str(key): admitted_distribution[key]
            for key in sorted(admitted_distribution)
        },
        "admitted_unknown_fill_support_source_count_distribution": {
            str(key): unknown_distribution[key]
            for key in sorted(unknown_distribution)
        },
        "admitted_override_support_source_count_distribution": {
            str(key): override_distribution[key]
            for key in sorted(override_distribution)
        },
        "admitted_new_row_support_source_count_distribution": {
            str(key): new_row_distribution[key]
            for key in sorted(new_row_distribution)
        },
        "minimum_unknown_sources": MINIMUM_UNKNOWN_SOURCES,
        "minimum_override_sources": MINIMUM_OVERRIDE_SOURCES,
        "minimum_new_row_sources": MINIMUM_NEW_ROW_SOURCES,
        "baseline_rows_deleted": 0,
        "unsupported_changes_reverted_to_baseline": True,
        "candidate_identity_handoff": final_rows == baseline_rows
        and admitted_unknown_fills == 0
        and admitted_overrides == 0,
        "shadow_information_gain_nats": round(
            float(shadow_information_gain_nats), 12
        ),
        "entropy_or_information_gain_used_for_admission": False,
        "source_thresholds_only_used_for_admission": True,
        "model_declared_evidence_membership_trusted": False,
        "question_query_url_host_page_candidate_value_evidence_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def apply_full_evidence_revision(
    *,
    baseline: str,
    proposed: str,
    pages: Sequence[EvidencePage | Mapping[str, Any]],
) -> dict[str, Any]:
    """Apply a candidate revision using source thresholds, never model citations."""

    columns, baseline_rows = _matrix(baseline)
    canonical = _canonical_candidate(proposed, columns)
    evidence = _stable_pages(pages)
    if canonical is None:
        receipt = _receipt(
            baseline_rows=len(baseline_rows),
            proposed_rows=0,
            final_rows=len(baseline_rows),
            table_column_count=len(columns),
            proposed_existing_cell_changes=0,
            admitted_unknown_fills=0,
            admitted_overrides=0,
            proposed_new_rows=0,
            admitted_new_rows=0,
            rejected_partial_new_rows=0,
            support_counts=(),
            admitted_unknown_support_counts=(),
            admitted_override_support_counts=(),
            admitted_new_row_support_counts=(),
            shadow_information_gain_nats=0.0,
        )
        return {"candidate_table": baseline, "receipt": receipt}
    candidate_columns, candidate_rows = _matrix(canonical)
    if [_clean(value) for value in candidate_columns] != [
        _clean(value) for value in columns
    ]:
        raise ValueError("V2.48.59 candidate columns drifted")

    baseline_by_key: dict[str, list[str]] = {}
    for row in baseline_rows:
        key = _identity_key(row[0])
        if not key or key in baseline_by_key:
            raise ValueError("V2.48.59 baseline row-key identity drifted")
        baseline_by_key[key] = row
    candidate_by_key: dict[str, list[str]] = {}
    candidate_order: list[str] = []
    for row in candidate_rows:
        key = _identity_key(row[0])
        if not key or key in candidate_by_key:
            raise ValueError("V2.48.59 candidate row-key identity drifted")
        candidate_by_key[key] = row
        candidate_order.append(key)

    output = [list(row) for row in baseline_rows]
    output_index = {
        _identity_key(row[0]): index for index, row in enumerate(output)
    }
    proposed_existing = 0
    unknown_fills = 0
    overrides = 0
    proposed_new = 0
    admitted_new = 0
    rejected_new = 0
    support_counts: list[int] = []
    admitted_unknown_support_counts: list[int] = []
    admitted_override_support_counts: list[int] = []
    admitted_new_row_support_counts: list[int] = []
    shadow_gain = 0.0

    for key, old_row in baseline_by_key.items():
        new_row = candidate_by_key.get(key)
        if new_row is None:
            continue
        target = output[output_index[key]]
        for column_index in range(1, len(columns)):
            old = old_row[column_index]
            new = new_row[column_index]
            if _identity_key(old) == _identity_key(new):
                continue
            proposed_existing += 1
            sources = _cell_sources(evidence, old_row[0], columns[column_index], new)
            count = len(sources)
            support_counts.append(count)
            override = not _is_unknown(old)
            required = (
                MINIMUM_OVERRIDE_SOURCES if override else MINIMUM_UNKNOWN_SOURCES
            )
            if count < required:
                continue
            target[column_index] = new
            shadow_gain += _shadow_information_gain(
                support_count=count, override=override
            )
            if override:
                overrides += 1
                admitted_override_support_counts.append(count)
            else:
                unknown_fills += 1
                admitted_unknown_support_counts.append(count)

    for key in candidate_order:
        if key in baseline_by_key:
            continue
        proposed_new += 1
        row = candidate_by_key[key]
        membership = len(_row_sources(evidence, row[0]))
        row_support = [membership]
        complete = (
            membership >= MINIMUM_NEW_ROW_SOURCES
            and all(not _is_unknown(value) for value in row)
        )
        for column_index in range(1, len(columns)):
            count = len(
                _cell_sources(evidence, row[0], columns[column_index], row[column_index])
            )
            row_support.append(count)
            complete = complete and count >= MINIMUM_NEW_ROW_SOURCES
        support_counts.extend(row_support)
        if not complete or len(output) >= MAXIMUM_ROWS:
            rejected_new += 1
            continue
        output.append(list(row))
        admitted_new += 1
        admitted_new_row_support_counts.extend(row_support)
        shadow_gain += sum(
            _shadow_information_gain(support_count=count, override=False)
            for count in row_support
        )

    candidate = _render(columns, output)
    canonical_output, errors = _extract_valid_markdown_table(candidate, columns)
    if canonical_output != candidate or errors:
        raise RuntimeError("V2.48.59 admitted table is not canonical")
    receipt = _receipt(
        baseline_rows=len(baseline_rows),
        proposed_rows=len(candidate_rows),
        final_rows=len(output),
        table_column_count=len(columns),
        proposed_existing_cell_changes=proposed_existing,
        admitted_unknown_fills=unknown_fills,
        admitted_overrides=overrides,
        proposed_new_rows=proposed_new,
        admitted_new_rows=admitted_new,
        rejected_partial_new_rows=rejected_new,
        support_counts=support_counts,
        admitted_unknown_support_counts=admitted_unknown_support_counts,
        admitted_override_support_counts=admitted_override_support_counts,
        admitted_new_row_support_counts=admitted_new_row_support_counts,
        shadow_information_gain_nats=shadow_gain,
    )
    return {"candidate_table": candidate, "receipt": receipt}


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    integers = (
        "artifact_version",
        "baseline_row_count",
        "proposed_row_count",
        "final_row_count",
        "table_column_count",
        "proposed_existing_cell_changes",
        "admitted_existing_unknown_fills",
        "admitted_existing_overrides",
        "proposed_new_rows",
        "admitted_new_rows",
        "rejected_partial_new_rows",
        "support_checks",
        "admitted_support_checks",
        "minimum_unknown_sources",
        "minimum_override_sources",
        "minimum_new_row_sources",
        "baseline_rows_deleted",
    )
    booleans = (
        "unsupported_changes_reverted_to_baseline",
        "candidate_identity_handoff",
        "entropy_or_information_gain_used_for_admission",
        "source_thresholds_only_used_for_admission",
        "model_declared_evidence_membership_trusted",
        "question_query_url_host_page_candidate_value_evidence_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = set(integers) | set(booleans) | {
        "role",
        "policy_id",
        "support_source_count_distribution",
        "admitted_support_source_count_distribution",
        "admitted_unknown_fill_support_source_count_distribution",
        "admitted_override_support_source_count_distribution",
        "admitted_new_row_support_source_count_distribution",
        "shadow_information_gain_nats",
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integers
        )
        or any(not isinstance(copied.get(name), bool) for name in booleans)
        or copied.get("minimum_unknown_sources") != MINIMUM_UNKNOWN_SOURCES
        or copied.get("minimum_override_sources") != MINIMUM_OVERRIDE_SOURCES
        or copied.get("minimum_new_row_sources") != MINIMUM_NEW_ROW_SOURCES
        or copied.get("baseline_rows_deleted") != 0
        or copied.get("unsupported_changes_reverted_to_baseline") is not True
        or copied.get("entropy_or_information_gain_used_for_admission") is not False
        or copied.get("source_thresholds_only_used_for_admission") is not True
        or copied.get("model_declared_evidence_membership_trusted") is not False
        or copied.get(
            "question_query_url_host_page_candidate_value_evidence_id_or_credential_emitted"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get("file_environment_network_model_search_fetch_or_process_accessed")
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.59 receipt identity drifted")
    gain = copied.get("shadow_information_gain_nats")
    distribution_names = (
        "support_source_count_distribution",
        "admitted_support_source_count_distribution",
        "admitted_unknown_fill_support_source_count_distribution",
        "admitted_override_support_source_count_distribution",
        "admitted_new_row_support_source_count_distribution",
    )
    distributions = tuple(copied.get(name) for name in distribution_names)
    if (
        isinstance(gain, bool)
        or not isinstance(gain, (int, float))
        or not math.isfinite(float(gain))
        or float(gain) < 0
        or any(not isinstance(item, Mapping) for item in distributions)
        or any(
            not isinstance(key, str)
            or not key.isdigit()
            or isinstance(number, bool)
            or not isinstance(number, int)
            or number < 0
            for item in distributions
            for key, number in item.items()
        )
    ):
        raise ValueError("V2.48.59 receipt metric drifted")
    support_total = sum(copied["support_source_count_distribution"].values())
    admitted_total = sum(
        copied["admitted_support_source_count_distribution"].values()
    )
    unknown_distribution = copied[
        "admitted_unknown_fill_support_source_count_distribution"
    ]
    override_distribution = copied[
        "admitted_override_support_source_count_distribution"
    ]
    new_row_distribution = copied[
        "admitted_new_row_support_source_count_distribution"
    ]
    reconstructed_admitted = Counter()
    for distribution in (unknown_distribution, override_distribution, new_row_distribution):
        reconstructed_admitted.update(distribution)
    changed = (
        copied["admitted_existing_unknown_fills"]
        + copied["admitted_existing_overrides"]
    )
    if (
        copied["final_row_count"]
        != copied["baseline_row_count"] + copied["admitted_new_rows"]
        or not 1 <= copied["table_column_count"] <= MAXIMUM_COLUMNS
        or not 1 <= copied["baseline_row_count"] <= MAXIMUM_ROWS
        or not 0 <= copied["proposed_row_count"] <= MAXIMUM_ROWS
        or copied["final_row_count"] > MAXIMUM_ROWS
        or copied["proposed_new_rows"] > copied["proposed_row_count"]
        or copied["admitted_new_rows"] > copied["proposed_new_rows"]
        or copied["rejected_partial_new_rows"]
        != copied["proposed_new_rows"] - copied["admitted_new_rows"]
        or copied["admitted_existing_unknown_fills"]
        + copied["admitted_existing_overrides"]
        > copied["proposed_existing_cell_changes"]
        or copied["support_checks"] != support_total
        or copied["admitted_support_checks"] != admitted_total
        or copied["support_checks"]
        != copied["proposed_existing_cell_changes"]
        + copied["proposed_new_rows"] * copied["table_column_count"]
        or copied["admitted_support_checks"]
        != changed
        + copied["admitted_new_rows"] * copied["table_column_count"]
        or dict(reconstructed_admitted)
        != copied["admitted_support_source_count_distribution"]
        or any(
            int(count) > MAXIMUM_PAGES
            for distribution in distributions
            for count in distribution
        )
        or any(
            number
            > copied["support_source_count_distribution"].get(count, 0)
            for count, number in copied[
                "admitted_support_source_count_distribution"
            ].items()
        )
        or sum(unknown_distribution.values())
        != copied["admitted_existing_unknown_fills"]
        or sum(override_distribution.values())
        != copied["admitted_existing_overrides"]
        or sum(new_row_distribution.values())
        != copied["admitted_new_rows"] * copied["table_column_count"]
        or any(
            int(count) < MINIMUM_UNKNOWN_SOURCES
            for count in unknown_distribution
        )
        or any(
            int(count) < MINIMUM_OVERRIDE_SOURCES
            for count in override_distribution
        )
        or any(
            int(count) < MINIMUM_NEW_ROW_SOURCES
            for count in new_row_distribution
        )
        or copied["proposed_existing_cell_changes"]
        > copied["baseline_row_count"] * (copied["table_column_count"] - 1)
        or copied["candidate_identity_handoff"]
        != (changed == 0 and copied["admitted_new_rows"] == 0)
    ):
        raise ValueError("V2.48.59 receipt conservation drifted")
    expected_gain = 0.0
    for count, number in unknown_distribution.items():
        expected_gain += _shadow_information_gain(
            support_count=int(count), override=False
        ) * number
    for count, number in override_distribution.items():
        expected_gain += _shadow_information_gain(
            support_count=int(count), override=True
        ) * number
    for count, number in new_row_distribution.items():
        expected_gain += _shadow_information_gain(
            support_count=int(count), override=False
        ) * number
    if not math.isclose(
        float(gain), round(expected_gain, 12), rel_tol=0.0, abs_tol=1e-9
    ):
        raise ValueError("V2.48.59 receipt shadow metric drifted")
    return copied


__all__ = [
    "EvidencePage",
    "MINIMUM_NEW_ROW_SOURCES",
    "MINIMUM_OVERRIDE_SOURCES",
    "MINIMUM_UNKNOWN_SOURCES",
    "POLICY_ID",
    "ROLE",
    "apply_full_evidence_revision",
    "payload_sha256",
    "prepare_evidence_pages",
    "validate_receipt",
]
