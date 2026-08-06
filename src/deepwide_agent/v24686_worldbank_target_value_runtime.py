"""Three-arm, label-blind World Bank target-value mechanism gate.

The runtime is benchmark-external.  It accepts only ``{opaque_id, question}``
and parses an exact visible contract containing four country identities, two
World Bank indicator identifiers, and the requested years.  A frozen-parser
arm and an expanded-parser arm share one plan plus one generic search/fetch
prefix, then receive one synthesis effect each in opaque-ID-balanced order.
The target-value arm is derived deterministically from the expanded-parser
prediction and public World Bank API responses for exact
``country x indicator x year`` addresses.

This is a quality-cost Pareto mechanism gate, not an equal-effect causal
ablation.  Entropy is shadow-only and cannot route effects or assign credit.
The module has no file, process, benchmark, gold, evaluator, reward, score, or
network capability; all effects are supplied by caller-owned clients.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit

from .clients import parse_json_object
from .v24257_score_first_runtime import (
    PLAN_SYSTEM,
    PLAN_USER,
    SYNTHESIS_SYSTEM,
    SYNTHESIS_USER,
    ScoreFirstLimits,
    _counter_delta,
    _counter_snapshot,
    _model_text,
    _normalize_column,
    _validated_plan,
    build_best_effort_prediction,
    extract_valid_markdown_table,
    validate_visible_task,
)
from .v24259_deterministic_table_normalizer import normalize_candidate_table
from .v24269_task_union_discovery import TaskUnionDiscoverySearchClient
from .v24286_visible_schema_runtime import extract_robust_visible_columns
from .v24308_child_exit_observability import coarse_exception_type
from .v24325_shared_prefix_revision_runtime import _format_evidence
from .v24637_objective_alignment_runtime import (
    MODEL_COUNTERS,
    SEARCH_COUNTERS,
    _Budget,
    payload_sha256,
)
from .v24640_evidence_constrained_runtime import UNKNOWN
from .v24644_primary_identity_pair_runtime import (
    _final_url_page_vector,
    _page_title_only_lead_requests,
)
from .v24675_expanded_visible_schema import extract_expanded_visible_columns


POLICY_ID = "v24686_worldbank_expanded_schema_target_value_v1"
ROLE = "v24686_worldbank_three_arm_task_result"
RECEIPT_ROLE = "v24686_worldbank_content_free_receipt"
ARMS = ("frozen_parser", "expanded_parser", "target_value")
GENERIC_FETCH_CAP = 2
TARGETED_LOOKUP_CAP = 8
COUNTRY_COUNT = 4
TARGET_COLUMN_COUNT = 2
EXPECTED_COLUMN_COUNT = 3
WORLD_BANK_HOST = "api.worldbank.org"
LOOKUP_STAT_KEYS = frozenset(
    {
        "requested_target_count",
        "returned_result_count",
        "valid_exact_record_count",
        "null_value_record_count",
        "invalid_exact_response_count",
        "unmatched_or_duplicate_result_count",
        "missing_response_count",
    }
)

_QUESTION = re.compile(
    r"Use public web sources to return one Markdown table about these countries:\n"
    r"<COUNTRIES>\n(?P<countries>.*?)\n</COUNTRIES>\n"
    r"Please output one Markdown table with the columns, in this exact order:\n"
    r"(?P<columns>[^\n]+)\n"
    r"Use the World Bank API values\. Preserve the decimal representation returned by "
    r"the official API\. Use Unknown when unavailable\. Return one table only\.",
    flags=re.DOTALL,
)
_COUNTRY = re.compile(r"(?P<ordinal>[1-4])\. (?P<name>[^\[\]|\r\n]+) \[(?P<iso3>[A-Z]{3})\]")
_TARGET_COLUMN = re.compile(
    r"(?P<label>[^|\[\]\r\n]{1,80})\s*"
    r"\[(?P<indicator>[A-Z][A-Z0-9.]{4,40})\]\s*@(?P<year>20[0-3][0-9])"
)


class _DecimalLexeme(str):
    """A validated JSON decimal token whose original spelling is retained."""


def _parse_decimal_lexeme(value: str) -> _DecimalLexeme:
    parsed = Decimal(value)
    if not parsed.is_finite():
        raise ValueError("V2.46.86 non-finite decimal")
    return _DecimalLexeme(value)


def _reject_nonfinite_constant(value: str) -> None:
    raise ValueError(f"V2.46.86 non-standard JSON number: {value}")


def _visible_contract(question: str) -> dict[str, Any]:
    """Parse the exact visible task surface without benchmark metadata."""

    visible = str(question or "").strip()
    match = _QUESTION.fullmatch(visible)
    if match is None:
        raise ValueError("V2.46.86 visible World Bank task syntax drifted")
    country_lines = match.group("countries").splitlines()
    countries: list[dict[str, str]] = []
    for expected, line in enumerate(country_lines, 1):
        parsed = _COUNTRY.fullmatch(line)
        if parsed is None or int(parsed.group("ordinal")) != expected:
            raise ValueError("V2.46.86 visible country vector drifted")
        name = parsed.group("name").strip()
        iso3 = parsed.group("iso3")
        if not name or any(character in name for character in "\r\n|[]"):
            raise ValueError("V2.46.86 visible country identity drifted")
        countries.append({"name": name, "iso3": iso3})
    if (
        len(countries) != COUNTRY_COUNT
        or len({item["name"].casefold() for item in countries}) != COUNTRY_COUNT
        or len({item["iso3"] for item in countries}) != COUNTRY_COUNT
    ):
        raise ValueError("V2.46.86 visible country uniqueness drifted")

    columns = [value.strip() for value in match.group("columns").split("|")]
    if len(columns) != EXPECTED_COLUMN_COUNT or columns[0] != "Country":
        raise ValueError("V2.46.86 visible column vector drifted")
    targets: list[dict[str, Any]] = []
    for column_index, column in enumerate(columns[1:], 1):
        parsed = _TARGET_COLUMN.fullmatch(column)
        if parsed is None:
            raise ValueError("V2.46.86 visible indicator address drifted")
        targets.append(
            {
                "column_index": column_index,
                "column": column,
                "label": parsed.group("label").strip(),
                "indicator": parsed.group("indicator"),
                "year": parsed.group("year"),
            }
        )
    if (
        len(targets) != TARGET_COLUMN_COUNT
        or len({(item["indicator"], item["year"]) for item in targets})
        != TARGET_COLUMN_COUNT
    ):
        raise ValueError("V2.46.86 visible target uniqueness drifted")

    frozen = extract_robust_visible_columns(visible)
    expanded = extract_expanded_visible_columns(visible)
    if frozen or expanded != columns:
        raise ValueError("V2.46.86 parser-gap contract drifted")
    return {
        "countries": countries,
        "columns": columns,
        "targets": targets,
        "frozen_parser_columns": frozen,
        "expanded_parser_columns": expanded,
    }


def validate_visible_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    countries = copied.get("countries")
    columns = copied.get("columns")
    targets = copied.get("targets")
    if (
        set(copied)
        != {
            "countries",
            "columns",
            "targets",
            "frozen_parser_columns",
            "expanded_parser_columns",
        }
        or not isinstance(countries, list)
        or len(countries) != COUNTRY_COUNT
        or any(
            not isinstance(item, Mapping)
            or set(item) != {"name", "iso3"}
            or not isinstance(item.get("name"), str)
            or item.get("name") != str(item.get("name", "")).strip()
            or not item.get("name")
            or any(character in str(item.get("name")) for character in "\r\n|[]")
            or not isinstance(item.get("iso3"), str)
            or re.fullmatch(r"[A-Z]{3}", str(item.get("iso3", ""))) is None
            for item in countries
        )
        or len({str(item["name"]).casefold() for item in countries})
        != COUNTRY_COUNT
        or len({str(item["iso3"]) for item in countries}) != COUNTRY_COUNT
        or not isinstance(columns, list)
        or len(columns) != EXPECTED_COLUMN_COUNT
        or columns[0] != "Country"
        or not isinstance(targets, list)
        or len(targets) != TARGET_COLUMN_COUNT
        or copied.get("frozen_parser_columns") != []
        or copied.get("expanded_parser_columns") != columns
    ):
        raise ValueError("V2.46.86 visible contract drifted")
    for expected_index, target in enumerate(targets, 1):
        parsed = (
            _TARGET_COLUMN.fullmatch(str(target.get("column", "")))
            if isinstance(target, Mapping)
            else None
        )
        if (
            not isinstance(target, Mapping)
            or set(target)
            != {"column_index", "column", "label", "indicator", "year"}
            or type(target.get("column_index")) is not int
            or target.get("column_index") != expected_index
            or not isinstance(target.get("column"), str)
            or target.get("column") != columns[expected_index]
            or parsed is None
            or not isinstance(target.get("label"), str)
            or target.get("label") != parsed.group("label").strip()
            or not isinstance(target.get("indicator"), str)
            or target.get("indicator") != parsed.group("indicator")
            or not isinstance(target.get("year"), str)
            or target.get("year") != parsed.group("year")
        ):
            raise ValueError("V2.46.86 visible target contract drifted")
    if (
        len(
            {
                (str(target["indicator"]), str(target["year"]))
                for target in targets
            }
        )
        != TARGET_COLUMN_COUNT
    ):
        raise ValueError("V2.46.86 visible target uniqueness drifted")
    return copied


def visible_query_vector(question: str, limit: int) -> list[str]:
    """Build four value-free, visible-address queries in country order."""

    if limit != COUNTRY_COUNT:
        raise ValueError("V2.46.86 requires the frozen four-query cap")
    contract = _visible_contract(question)
    target = " ".join(
        f'{item["indicator"]} {item["year"]}' for item in contract["targets"]
    )
    return [
        f'"{country["name"]}" {country["iso3"]} World Bank {target}'
        for country in contract["countries"]
    ]


def exact_lookup_url(iso3: str, indicator: str, year: str) -> str:
    """Build one exact public World Bank target-value address."""

    country = str(iso3)
    metric = str(indicator)
    date = str(year)
    if (
        re.fullmatch(r"[A-Z]{3}", country) is None
        or re.fullmatch(r"[A-Z][A-Z0-9.]{4,40}", metric) is None
        or re.fullmatch(r"20[0-3][0-9]", date) is None
    ):
        raise ValueError("V2.46.86 lookup address drifted")
    query = urlencode((("date", date), ("format", "json"), ("per_page", "100")))
    return (
        f"https://{WORLD_BANK_HOST}/v2/country/{country}/indicator/{metric}?{query}"
    )


def target_lookup_requests(contract: Mapping[str, Any]) -> list[dict[str, str]]:
    validated = validate_visible_contract(contract)
    requests: list[dict[str, str]] = []
    for country in validated["countries"]:
        for target in validated["targets"]:
            key = f'{country["iso3"]}|{target["indicator"]}|{target["year"]}'
            requests.append(
                {
                    "url": exact_lookup_url(
                        country["iso3"], target["indicator"], target["year"]
                    ),
                    "title": "",
                    "query": "world-bank target-value lookup",
                    "member_label": key,
                }
            )
    if len(requests) != TARGETED_LOOKUP_CAP:
        raise ValueError("V2.46.86 target lookup count drifted")
    return requests


def _canonical_target_from_url(
    url: object, expected: Mapping[str, tuple[str, str, str]]
) -> tuple[str, str, str] | None:
    """Return a target only for the exact URL generated by this policy."""

    try:
        parsed = urlsplit(str(url))
    except ValueError:
        return None
    parts = parsed.path.strip("/").split("/")
    if (
        parsed.scheme.casefold() != "https"
        or (parsed.hostname or "").casefold() != WORLD_BANK_HOST
        or len(parts) != 5
        or parts[0] != "v2"
        or parts[1] != "country"
        or parts[3] != "indicator"
        or parsed.fragment
    ):
        return None
    iso3, indicator = parts[2], parts[4]
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    parameters = dict(pairs)
    if pairs != [
        ("date", parameters.get("date", "")),
        ("format", "json"),
        ("per_page", "100"),
    ]:
        return None
    year = parameters.get("date", "")
    key = f"{iso3}|{indicator}|{year}"
    target = expected.get(key)
    if target is None or exact_lookup_url(*target) != str(url):
        return None
    return target


def _decimal_text(value: object) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, _DecimalLexeme):
        return str(value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            return None
        # ``parse_float=Decimal`` retains the scale in the JSON number.  Fixed
        # formatting avoids exponent output while preserving decimal zeros.
        return format(value, "f")
    return None


def project_exact_lookup_responses(
    batches: object, contract: Mapping[str, Any]
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """Validate and project exact official API responses into target records."""

    validated = validate_visible_contract(contract)
    expected = {
        f'{country["iso3"]}|{target["indicator"]}|{target["year"]}': (
            country["iso3"],
            target["indicator"],
            target["year"],
        )
        for country in validated["countries"]
        for target in validated["targets"]
    }
    stats: Counter[str] = Counter(
        {
            "requested_target_count": len(expected),
            "returned_result_count": 0,
            "valid_exact_record_count": 0,
            "null_value_record_count": 0,
            "invalid_exact_response_count": 0,
            "unmatched_or_duplicate_result_count": 0,
            "missing_response_count": 0,
        }
    )
    records: list[dict[str, str]] = []
    returned_target_keys: set[str] = set()
    seen: set[str] = set()
    classified_targets: set[str] = set()
    if not isinstance(batches, Sequence) or isinstance(batches, (str, bytes)):
        stats["missing_response_count"] = len(expected)
        return records, dict(stats)
    for batch in batches:
        if not isinstance(batch, Mapping):
            continue
        results = batch.get("results")
        if not isinstance(results, Sequence) or isinstance(results, (str, bytes)):
            continue
        for result in results:
            if not isinstance(result, Mapping):
                continue
            stats["returned_result_count"] += 1
            target = _canonical_target_from_url(result.get("url"), expected)
            if target is None:
                stats["unmatched_or_duplicate_result_count"] += 1
                continue
            iso3, indicator, year = target
            key = f"{iso3}|{indicator}|{year}"
            returned_target_keys.add(key)
            if key in seen:
                stats["unmatched_or_duplicate_result_count"] += 1
                continue
            seen.add(key)
            raw = str(result.get("raw_content") or result.get("content") or "")
            try:
                payload = json.loads(
                    raw,
                    parse_float=_parse_decimal_lexeme,
                    parse_constant=_reject_nonfinite_constant,
                )
            except (json.JSONDecodeError, InvalidOperation, TypeError, ValueError):
                stats["invalid_exact_response_count"] += 1
                classified_targets.add(key)
                continue
            if (
                not isinstance(payload, list)
                or len(payload) != 2
                or not isinstance(payload[0], Mapping)
                or not isinstance(payload[1], list)
                or len(payload[1]) != 1
                or payload[0].get("page") != 1
                or payload[0].get("pages") != 1
                or payload[0].get("total") != 1
                or not isinstance(payload[1][0], Mapping)
            ):
                stats["invalid_exact_response_count"] += 1
                classified_targets.add(key)
                continue
            row = payload[1][0]
            indicator_object = row.get("indicator")
            if (
                not isinstance(indicator_object, Mapping)
                or indicator_object.get("id") != indicator
                or row.get("countryiso3code") != iso3
                or str(row.get("date", "")) != year
            ):
                stats["invalid_exact_response_count"] += 1
                classified_targets.add(key)
                continue
            raw_value = row.get("value")
            value = _decimal_text(raw_value)
            if raw_value is None:
                stats["null_value_record_count"] += 1
                classified_targets.add(key)
                continue
            if value is None:
                stats["invalid_exact_response_count"] += 1
                classified_targets.add(key)
                continue
            records.append(
                {
                    "target_key": key,
                    "country_iso3": iso3,
                    "indicator": indicator,
                    "year": year,
                    "value": value,
                    "request_url": str(result.get("url")),
                    "response_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                    "raw_content": raw,
                }
            )
            stats["valid_exact_record_count"] += 1
            classified_targets.add(key)
    missing = set(expected) - returned_target_keys
    unclassified = returned_target_keys - classified_targets
    if unclassified:
        raise ValueError("V2.46.86 target response classification drifted")
    stats["missing_response_count"] = len(missing)
    records.sort(key=lambda item: item["target_key"])
    return records, dict(stats)


def validate_official_records(
    records: object, contract: Mapping[str, Any]
) -> list[dict[str, str]]:
    """Replay every retained record through the exact response projector."""

    if not isinstance(records, list):
        raise ValueError("V2.46.86 official record vector drifted")
    replay_batches: list[dict[str, Any]] = []
    for record in records:
        if (
            not isinstance(record, Mapping)
            or set(record)
            != {
                "target_key",
                "country_iso3",
                "indicator",
                "year",
                "value",
                "request_url",
                "response_sha256",
                "raw_content",
            }
            or any(not isinstance(record.get(key), str) for key in record)
        ):
            raise ValueError("V2.46.86 official record shape drifted")
        replay_batches.append(
            {
                "results": [
                    {
                        "url": record["request_url"],
                        "raw_content": record["raw_content"],
                    }
                ]
            }
        )
    projected, stats = project_exact_lookup_responses(replay_batches, contract)
    if (
        projected != records
        or stats["returned_result_count"] != len(records)
        or stats["valid_exact_record_count"] != len(records)
        or stats["null_value_record_count"] != 0
        or stats["invalid_exact_response_count"] != 0
        or stats["unmatched_or_duplicate_result_count"] != 0
        or stats["missing_response_count"] != TARGETED_LOOKUP_CAP - len(records)
    ):
        raise ValueError("V2.46.86 official record replay drifted")
    return projected


def _matrix(table: str, columns: Sequence[str]) -> tuple[list[str], list[list[str]]]:
    canonical, _ = extract_valid_markdown_table(table, columns)
    if canonical is None:
        return list(columns), []
    lines = [
        line.strip()
        for line in canonical.splitlines()
        if line.strip().startswith("|")
    ]
    return (
        [cell.strip() for cell in lines[0][1:-1].split("|")],
        [[cell.strip() for cell in line[1:-1].split("|")] for line in lines[2:]],
    )


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


def _unknown_table(contract: Mapping[str, Any]) -> str:
    validated = validate_visible_contract(contract)
    return _render(
        validated["columns"],
        [
            [country["name"], *("Unknown" for _ in validated["targets"])]
            for country in validated["countries"]
        ],
    )


def _identity_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def project_visible_rows(table: str, contract: Mapping[str, Any]) -> str:
    """Project a valid expanded-schema table onto the visible country order."""

    validated = validate_visible_contract(contract)
    columns, rows = _matrix(table, validated["columns"])
    if columns != validated["columns"]:
        return _unknown_table(validated)
    expected: dict[str, int] = {}
    for ordinal, country in enumerate(validated["countries"]):
        expected[_identity_key(country["name"])] = ordinal
        expected[_identity_key(country["iso3"])] = ordinal
    selected: dict[int, list[str]] = {}
    duplicate: set[int] = set()
    for row in rows:
        if len(row) != EXPECTED_COLUMN_COUNT:
            continue
        ordinal = expected.get(_identity_key(row[0]))
        if ordinal is None:
            continue
        if ordinal in selected:
            duplicate.add(ordinal)
            continue
        selected[ordinal] = row
    output: list[list[str]] = []
    for ordinal, country in enumerate(validated["countries"]):
        row = selected.get(ordinal) if ordinal not in duplicate else None
        values = row[1:] if row is not None else ["Unknown"] * TARGET_COLUMN_COUNT
        output.append(
            [
                country["name"],
                *(
                    value
                    if value and value.casefold() not in {"none", "null"}
                    else "Unknown"
                    for value in values
                ),
            ]
        )
    return _render(validated["columns"], output)


def _canonical(raw: str, columns: Sequence[str], question: str) -> str | None:
    table, _ = extract_valid_markdown_table(raw, columns)
    if table is not None:
        return table
    marker = "未知" if re.search(r"[\u4e00-\u9fff]", question) else "Unknown"
    normalized, _ = normalize_candidate_table(raw, columns, unknown_marker=marker)
    if normalized is None:
        return None
    table, _ = extract_valid_markdown_table(normalized, columns)
    return table


def apply_target_values(
    expanded_prediction: str,
    contract: Mapping[str, Any],
    records: Sequence[Mapping[str, str]],
) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    """Build an official-only target-value table and independent check."""

    validated = validate_visible_contract(contract)
    expanded_prediction = project_visible_rows(expanded_prediction, validated)
    _columns, expanded_rows = _matrix(expanded_prediction, validated["columns"])
    verified_records = validate_official_records(list(records), validated)
    by_key: dict[str, Mapping[str, str]] = {}
    for record in verified_records:
        key = str(record.get("target_key", ""))
        if not key or key in by_key:
            raise ValueError("V2.46.86 duplicate official target record")
        by_key[key] = record
    rows: list[list[str]] = []
    admissions: list[dict[str, Any]] = []
    counts: Counter[str] = Counter(
        {
            "admitted_target_count": 0,
            "missing_target_count": 0,
            "confirmed_equal_count": 0,
            "filled_unknown_count": 0,
            "corrected_nonunknown_count": 0,
            "missing_preserved_unknown_count": 0,
            "cleared_unsupported_nonunknown_count": 0,
            "changed_target_count": 0,
        }
    )
    for row_index, (country, prior_row) in enumerate(
        zip(validated["countries"], expanded_rows, strict=True)
    ):
        row = [country["name"]]
        for target in validated["targets"]:
            column_index = int(target["column_index"])
            key = f'{country["iso3"]}|{target["indicator"]}|{target["year"]}'
            record = by_key.get(key)
            prior = prior_row[column_index]
            if record is None:
                value = "Unknown"
                counts["missing_target_count"] += 1
                if prior.casefold() in UNKNOWN:
                    counts["missing_preserved_unknown_count"] += 1
                else:
                    counts["cleared_unsupported_nonunknown_count"] += 1
            else:
                value = str(record["value"])
                counts["admitted_target_count"] += 1
                if prior == value:
                    counts["confirmed_equal_count"] += 1
                elif prior.casefold() in UNKNOWN:
                    counts["filled_unknown_count"] += 1
                else:
                    counts["corrected_nonunknown_count"] += 1
                admissions.append(
                    {
                        "row_index": row_index,
                        "column_index": column_index,
                        "target_key": key,
                        "value": value,
                        "request_url": record["request_url"],
                        "response_sha256": record["response_sha256"],
                        "prior_was_unknown": prior.casefold() in UNKNOWN,
                    }
                )
            counts["changed_target_count"] += int(prior != value)
            row.append(value)
        rows.append(row)
    candidate = _render(validated["columns"], rows)
    check = independent_completion_check(candidate, validated, verified_records)
    check.update({name: int(counts[name]) for name in sorted(counts)})
    return candidate, admissions, check


def independent_completion_check(
    candidate: str,
    contract: Mapping[str, Any],
    records: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    validated = validate_visible_contract(contract)
    columns, rows = _matrix(candidate, validated["columns"])
    verified_records = validate_official_records(list(records), validated)
    by_key = {
        str(record.get("target_key", "")): record for record in verified_records
    }
    expected_target_count = COUNTRY_COUNT * TARGET_COLUMN_COUNT
    exact_identity = (
        len(rows) == COUNTRY_COUNT
        and [row[0] for row in rows]
        == [country["name"] for country in validated["countries"]]
    )
    bound = 0
    values_match = exact_identity and columns == validated["columns"]
    if values_match:
        for country, row in zip(validated["countries"], rows, strict=True):
            for target in validated["targets"]:
                key = f'{country["iso3"]}|{target["indicator"]}|{target["year"]}'
                record = by_key.get(key)
                if record is None or row[int(target["column_index"])] != record.get("value"):
                    values_match = False
                else:
                    bound += 1
    return {
        "expected_row_count": COUNTRY_COUNT,
        "observed_row_count": len(rows),
        "expected_target_count": expected_target_count,
        "evidence_bound_target_count": bound,
        "exact_header": columns == validated["columns"],
        "exact_visible_identity_order": exact_identity,
        "all_target_values_match_unique_official_records": values_match,
        "passed": bool(
            columns == validated["columns"]
            and exact_identity
            and values_match
            and bound == expected_target_count
            and len(by_key) == expected_target_count
        ),
    }


def _arm_order(opaque_id: str) -> tuple[str, str]:
    return (
        ("frozen_parser", "expanded_parser")
        if int(str(opaque_id)[-1], 16) % 2
        else ("expanded_parser", "frozen_parser")
    )


def _receipt(
    *,
    budget: _Budget,
    model_cost: Mapping[str, int],
    search_cost: Mapping[str, int],
    generic_fetch_count: int,
    generic_page_count: int,
    lookup_fetch_count: int,
    lookup_stats: Mapping[str, int],
    plan_columns_match_expanded: bool,
    synthesis_order: Sequence[str],
    completion: Mapping[str, Any],
    failures: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "three_arm_design": list(ARMS),
        "shared_plan_search_generic_fetch_evidence_prefix": True,
        "synthesis_order": list(synthesis_order),
        "model_stage_vector": list(budget.model_stages),
        "logical_model_admission_count": len(budget.model_stages),
        "admitted_hosted_search_queries": int(budget.search_queries),
        "admitted_total_fetch_targets": int(budget.fetch_targets),
        "generic_fetch_cap": GENERIC_FETCH_CAP,
        "targeted_lookup_cap": TARGETED_LOOKUP_CAP,
        "generic_fetch_targets": int(generic_fetch_count),
        "generic_model_visible_page_count": int(generic_page_count),
        "targeted_lookup_fetch_targets": int(lookup_fetch_count),
        "lookup": dict(lookup_stats),
        "completion_check": dict(completion),
        "frozen_parser_column_count": 0,
        "expanded_parser_column_count": EXPECTED_COLUMN_COUNT,
        "model_plan_columns_match_expanded_schema": bool(plan_columns_match_expanded),
        "model_cost": {key: int(amount) for key, amount in model_cost.items()},
        "search_cost": {key: int(amount) for key, amount in search_cost.items()},
        "recoverable_failure_count": len(failures),
        "recoverable_failure_type_counts": {
            name: sum(str(item.get("type")) == name for item in failures)
            for name in sorted({str(item.get("type")) for item in failures})
        },
        "target_value_candidate_uses_only_exact_official_address_records": True,
        "target_value_candidate_may_correct_nonunknown_values": True,
        "unsupported_target_cells_project_to_unknown": True,
        "country_identity_cells_immutable": True,
        "independent_completion_check_after_cell_admission": True,
        "quality_cost_pareto_not_equal_effect_causal_ablation": True,
        "entropy_shadow": {
            "conditional_information_gain_computed": False,
            "routes_or_changes_forward_effects": False,
            "positive_credit_assigned": False,
            "requires_postfreeze_outer_utility_validation": True,
        },
        "positive_task_credit_assigned": False,
        "question_query_url_page_prediction_answer_value_country_indicator_or_"
        "opaque_id_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    lookup = copied.get("lookup")
    completion = copied.get("completion_check")
    model_cost = copied.get("model_cost")
    stages = copied.get("model_stage_vector")
    order = copied.get("synthesis_order")
    lookup_stats_are_integers = isinstance(lookup, Mapping) and all(
        type(lookup.get(name)) is int and int(lookup[name]) >= 0
        for name in LOOKUP_STAT_KEYS
    )
    lookup_result_conservation = lookup_stats_are_integers and (
        lookup["returned_result_count"]
        == lookup["valid_exact_record_count"]
        + lookup["null_value_record_count"]
        + lookup["invalid_exact_response_count"]
        + lookup["unmatched_or_duplicate_result_count"]
    )
    lookup_target_conservation = lookup_stats_are_integers and (
        lookup["requested_target_count"]
        == lookup["valid_exact_record_count"]
        + lookup["null_value_record_count"]
        + lookup["invalid_exact_response_count"]
        + lookup["missing_response_count"]
    )
    completion_count_names = (
        "expected_row_count",
        "observed_row_count",
        "expected_target_count",
        "evidence_bound_target_count",
        "admitted_target_count",
        "missing_target_count",
        "confirmed_equal_count",
        "filled_unknown_count",
        "corrected_nonunknown_count",
        "missing_preserved_unknown_count",
        "cleared_unsupported_nonunknown_count",
        "changed_target_count",
    )
    completion_counts_are_integers = isinstance(completion, Mapping) and all(
        type(completion.get(name)) is int and int(completion[name]) >= 0
        for name in completion_count_names
    )
    completion_conservation = completion_counts_are_integers and (
        completion["admitted_target_count"] + completion["missing_target_count"]
        == completion["expected_target_count"]
        and completion["confirmed_equal_count"]
        + completion["filled_unknown_count"]
        + completion["corrected_nonunknown_count"]
        == completion["admitted_target_count"]
        and completion["missing_preserved_unknown_count"]
        + completion["cleared_unsupported_nonunknown_count"]
        == completion["missing_target_count"]
        and completion["changed_target_count"]
        == completion["filled_unknown_count"]
        + completion["corrected_nonunknown_count"]
        + completion["cleared_unsupported_nonunknown_count"]
        and completion["evidence_bound_target_count"]
        == completion["admitted_target_count"]
    )
    failure_types = copied.get("recoverable_failure_type_counts")
    failure_count = copied.get("recoverable_failure_count")
    failure_conservation = (
        type(failure_count) is int
        and failure_count >= 0
        and isinstance(failure_types, Mapping)
        and all(
            isinstance(name, str)
            and name
            and type(amount) is int
            and amount > 0
            for name, amount in failure_types.items()
        )
        and sum(failure_types.values()) == failure_count
    )
    expected_entropy_shadow = {
        "conditional_information_gain_computed": False,
        "routes_or_changes_forward_effects": False,
        "positive_credit_assigned": False,
        "requires_postfreeze_outer_utility_validation": True,
    }
    expected_fields = {
        "artifact_version",
        "role",
        "policy_id",
        "three_arm_design",
        "shared_plan_search_generic_fetch_evidence_prefix",
        "synthesis_order",
        "model_stage_vector",
        "logical_model_admission_count",
        "admitted_hosted_search_queries",
        "admitted_total_fetch_targets",
        "generic_fetch_cap",
        "targeted_lookup_cap",
        "generic_fetch_targets",
        "generic_model_visible_page_count",
        "targeted_lookup_fetch_targets",
        "lookup",
        "completion_check",
        "frozen_parser_column_count",
        "expanded_parser_column_count",
        "model_plan_columns_match_expanded_schema",
        "model_cost",
        "search_cost",
        "recoverable_failure_count",
        "recoverable_failure_type_counts",
        "target_value_candidate_uses_only_exact_official_address_records",
        "target_value_candidate_may_correct_nonunknown_values",
        "unsupported_target_cells_project_to_unknown",
        "country_identity_cells_immutable",
        "independent_completion_check_after_cell_admission",
        "quality_cost_pareto_not_equal_effect_causal_ablation",
        "entropy_shadow",
        "positive_task_credit_assigned",
        "question_query_url_page_prediction_answer_value_country_indicator_or_opaque_id_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
    if (
        set(copied) != expected_fields
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("three_arm_design") != list(ARMS)
        or copied.get("shared_plan_search_generic_fetch_evidence_prefix") is not True
        or order
        not in (
            ["frozen_parser", "expanded_parser"],
            ["expanded_parser", "frozen_parser"],
        )
        or stages != ["shared_plan", *(f"{arm}_synthesis" for arm in order)]
        or copied.get("logical_model_admission_count") != 3
        or type(copied.get("admitted_hosted_search_queries")) is not int
        or copied.get("admitted_hosted_search_queries") != COUNTRY_COUNT
        or copied.get("generic_fetch_cap") != GENERIC_FETCH_CAP
        or copied.get("targeted_lookup_cap") != TARGETED_LOOKUP_CAP
        or type(copied.get("generic_fetch_targets")) is not int
        or copied.get("generic_fetch_targets", -1) not in range(GENERIC_FETCH_CAP + 1)
        or type(copied.get("targeted_lookup_fetch_targets")) is not int
        or copied.get("targeted_lookup_fetch_targets", -1)
        not in range(TARGETED_LOOKUP_CAP + 1)
        or type(copied.get("admitted_total_fetch_targets")) is not int
        or copied.get("generic_fetch_targets", 0)
        + copied.get("targeted_lookup_fetch_targets", 0)
        != copied.get("admitted_total_fetch_targets")
        or type(copied.get("generic_model_visible_page_count")) is not int
        or copied.get("generic_model_visible_page_count", -1) < 0
        or not isinstance(lookup, Mapping)
        or set(lookup) != LOOKUP_STAT_KEYS
        or lookup.get("requested_target_count") != TARGETED_LOOKUP_CAP
        or not lookup_result_conservation
        or not lookup_target_conservation
        or not isinstance(completion, Mapping)
        or completion.get("expected_row_count") != COUNTRY_COUNT
        or completion.get("expected_target_count") != TARGETED_LOOKUP_CAP
        or not completion_conservation
        or completion.get("admitted_target_count")
        != lookup.get("valid_exact_record_count")
        or copied.get("frozen_parser_column_count") != 0
        or copied.get("expanded_parser_column_count") != EXPECTED_COLUMN_COUNT
        or not isinstance(copied.get("model_plan_columns_match_expanded_schema"), bool)
        or not failure_conservation
        or not isinstance(model_cost, Mapping)
        or set(model_cost) != set(MODEL_COUNTERS)
        or model_cost.get("requests", -1) not in range(4)
        or model_cost.get("attempts", -1) < model_cost.get("requests", -1)
        or any(
            type(model_cost.get(name)) is not int or model_cost[name] < 0
            for name in MODEL_COUNTERS
        )
        or not isinstance(copied.get("search_cost"), Mapping)
        or set(copied["search_cost"]) != set(SEARCH_COUNTERS)
        or any(
            type(copied["search_cost"].get(name)) is not int
            or copied["search_cost"][name] < 0
            for name in SEARCH_COUNTERS
        )
        or copied.get("target_value_candidate_uses_only_exact_official_address_records")
        is not True
        or copied.get("target_value_candidate_may_correct_nonunknown_values") is not True
        or copied.get("unsupported_target_cells_project_to_unknown") is not True
        or copied.get("country_identity_cells_immutable") is not True
        or copied.get("independent_completion_check_after_cell_admission") is not True
        or copied.get("quality_cost_pareto_not_equal_effect_causal_ablation")
        is not True
        or copied.get("entropy_shadow") != expected_entropy_shadow
        or copied.get("positive_task_credit_assigned") is not False
        or copied.get(
            "question_query_url_page_prediction_answer_value_country_indicator_or_opaque_id_emitted"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.46.86 content-free receipt drifted")
    return copied


def run_v24686_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    contract = _visible_contract(visible["question"])
    limits.validate()
    if (
        limits.model_calls != 3
        or limits.search_queries != COUNTRY_COUNT
        or limits.fetch_targets != GENERIC_FETCH_CAP + TARGETED_LOOKUP_CAP
    ):
        raise ValueError("V2.46.86 fixed effect envelope drifted")
    started = float(monotonic())
    budget = _Budget(limits, started, monotonic)
    model_before = _counter_snapshot(model, MODEL_COUNTERS)
    search_before = _counter_snapshot(search, SEARCH_COUNTERS)
    failures: list[dict[str, str]] = []

    def recovered(stage: str, error: BaseException) -> None:
        failures.append({"stage": stage, "type": coarse_exception_type(error)})

    if not budget.admit_model("shared_plan"):
        raise RuntimeError("V2.46.86 shared plan was not admitted")
    try:
        response = model.complete(
            PLAN_SYSTEM,
            PLAN_USER.format(
                question=visible["question"], query_limit=limits.search_queries
            ),
            max_output_tokens=limits.plan_output_tokens,
            json_mode=True,
        )
        plan = _validated_plan(
            parse_json_object(_model_text(response)), visible["question"], limits
        )
    except Exception as error:
        recovered("shared_plan", error)
        plan = _validated_plan({}, visible["question"], limits)

    queries = visible_query_vector(visible["question"], limits.search_queries)
    query_count = budget.admit_search(len(queries))
    union = TaskUnionDiscoverySearchClient(search)
    try:
        batches = (
            union.search_many(
                queries[:query_count],
                max_results=limits.search_results_per_query,
                search_depth="advanced",
                include_raw_content=False,
            )
            if query_count
            else []
        )
    except Exception as error:
        recovered("shared_search", error)
        batches = []
    leads = _page_title_only_lead_requests(batches, GENERIC_FETCH_CAP)
    generic_fetch_count = budget.admit_fetch(len(leads))
    try:
        generic_raw = (
            union.fetch_urls(leads[:generic_fetch_count])
            if generic_fetch_count
            else []
        )
    except Exception as error:
        recovered("generic_fetch", error)
        generic_raw = []
    generic_pages = _final_url_page_vector(
        generic_raw, prefix="E", page_chars=limits.page_chars
    )
    evidence = _format_evidence(generic_pages, character_cap=limits.evidence_chars)

    expected_columns = list(contract["columns"])
    plan_columns = list(plan["columns"])
    frozen_columns = list(contract["frozen_parser_columns"] or plan_columns)
    order = _arm_order(visible["opaque_id"])
    predictions: dict[str, str] = {}
    for arm in order:
        columns = frozen_columns if arm == "frozen_parser" else expected_columns
        if not budget.admit_model(f"{arm}_synthesis"):
            raw_prediction = build_best_effort_prediction(visible["question"], columns)
        else:
            try:
                response = model.complete(
                    SYNTHESIS_SYSTEM,
                    SYNTHESIS_USER.format(
                        question=visible["question"],
                        columns=json.dumps(columns, ensure_ascii=False),
                        evidence=evidence,
                    ),
                    max_output_tokens=limits.synthesis_output_tokens,
                    json_mode=False,
                )
                raw_prediction = _canonical(
                    _model_text(response), columns, visible["question"]
                ) or build_best_effort_prediction(visible["question"], columns)
            except Exception as error:
                recovered(f"{arm}_synthesis", error)
                raw_prediction = build_best_effort_prediction(
                    visible["question"], columns
                )
        if arm == "expanded_parser":
            raw_prediction = project_visible_rows(raw_prediction, contract)
        elif [_normalize_column(value) for value in columns] == [
            _normalize_column(value) for value in expected_columns
        ]:
            raw_prediction = project_visible_rows(raw_prediction, contract)
        predictions[arm] = raw_prediction

    lookup_requests = target_lookup_requests(contract)
    lookup_fetch_count = budget.admit_fetch(len(lookup_requests))
    try:
        lookup_raw = (
            union.fetch_urls(lookup_requests[:lookup_fetch_count])
            if lookup_fetch_count
            else []
        )
    except Exception as error:
        recovered("target_value_lookup", error)
        lookup_raw = []
    records, lookup_stats = project_exact_lookup_responses(lookup_raw, contract)
    candidate, admissions, completion = apply_target_values(
        predictions["expanded_parser"], contract, records
    )
    predictions["target_value"] = candidate

    model_cost = _counter_delta(
        _counter_snapshot(model, MODEL_COUNTERS), model_before
    )
    search_cost = _counter_delta(
        _counter_snapshot(search, SEARCH_COUNTERS), search_before
    )
    receipt = _receipt(
        budget=budget,
        model_cost=model_cost,
        search_cost=search_cost,
        generic_fetch_count=generic_fetch_count,
        generic_page_count=len(generic_pages),
        lookup_fetch_count=lookup_fetch_count,
        lookup_stats=lookup_stats,
        plan_columns_match_expanded=[_normalize_column(value) for value in plan_columns]
        == [_normalize_column(value) for value in expected_columns],
        synthesis_order=order,
        completion=completion,
        failures=failures,
    )
    result = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": visible["opaque_id"],
        "visible_contract": contract,
        "predictions": predictions,
        "prediction_sha256": {
            arm: hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        },
        "official_lookup_records": records,
        "cell_admissions": admissions,
        "receipt": receipt,
        "elapsed_seconds": round(max(0.0, float(monotonic()) - started), 6),
        "private_visible_provider_and_prediction_content_present": True,
        "private_content_emitted_to_public_aggregate": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    result["result_sha256"] = payload_sha256(result)
    return validate_result(result)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_sha256", None)
    predictions = copied.get("predictions")
    hashes = copied.get("prediction_sha256")
    records = copied.get("official_lookup_records")
    admissions = copied.get("cell_admissions")
    elapsed = copied.get("elapsed_seconds")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "opaque_id",
            "visible_contract",
            "predictions",
            "prediction_sha256",
            "official_lookup_records",
            "cell_admissions",
            "receipt",
            "elapsed_seconds",
            "private_visible_provider_and_prediction_content_present",
            "private_content_emitted_to_public_aggregate",
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
            "result_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or re.fullmatch(r"task_[0-9a-f]{24}", str(copied.get("opaque_id", "")))
        is None
        or not isinstance(predictions, Mapping)
        or set(predictions) != set(ARMS)
        or not isinstance(hashes, Mapping)
        or set(hashes) != set(ARMS)
        or any(not isinstance(predictions[arm], str) for arm in ARMS)
        or any(
            hashes[arm] != hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        )
        or not isinstance(records, list)
        or not isinstance(admissions, list)
        or isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not math.isfinite(float(elapsed))
        or elapsed < 0
        or copied.get("private_visible_provider_and_prediction_content_present")
        is not True
        or copied.get("private_content_emitted_to_public_aggregate") is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.46.86 task result drifted")
    contract = validate_visible_contract(copied.get("visible_contract", {}))
    receipt = validate_receipt(copied.get("receipt", {}))
    if receipt["synthesis_order"] != list(_arm_order(copied["opaque_id"])):
        raise ValueError("V2.46.86 opaque-ID arm order drifted")
    records = validate_official_records(records, contract)
    expanded = project_visible_rows(predictions["expanded_parser"], contract)
    if expanded != predictions["expanded_parser"]:
        raise ValueError("V2.46.86 expanded prediction projection drifted")
    candidate, expected_admissions, completion = apply_target_values(
        predictions["expanded_parser"], contract, records
    )
    if (
        candidate != predictions["target_value"]
        or expected_admissions != admissions
        or completion != copied["receipt"]["completion_check"]
        or len(admissions)
        != copied["receipt"]["lookup"]["valid_exact_record_count"]
    ):
        raise ValueError("V2.46.86 target-value binding drifted")
    return copied


__all__ = [
    "ARMS",
    "GENERIC_FETCH_CAP",
    "POLICY_ID",
    "ROLE",
    "TARGETED_LOOKUP_CAP",
    "apply_target_values",
    "exact_lookup_url",
    "independent_completion_check",
    "project_exact_lookup_responses",
    "project_visible_rows",
    "run_v24686_task",
    "target_lookup_requests",
    "validate_official_records",
    "validate_receipt",
    "validate_result",
    "validate_visible_contract",
    "visible_query_vector",
]
