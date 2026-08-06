"""Fresh-target dual-representation resilience primitives.

This module has no filesystem, process, network, credential, benchmark-label,
gold, evaluator, reward, or score capability.  It validates caller-supplied
World Bank bytes in memory.  A target is admitted when at least one of its two
fixed representations is schema-valid.  If both are valid, every value on the
common ISO3 domain must agree.  Failure is isolated per target.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import re
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlencode

POLICY_ID = "v24740_fresh_dual_representation_resilience_v1"
WORLD_BANK_HOST = "api.worldbank.org"
REPRESENTATIONS = ("bulk_zip", "aggregate_json")
PREFERRED_REPRESENTATION = "bulk_zip"
FALLBACK_REPRESENTATION = "aggregate_json"
MAX_RESPONSE_BYTES = 4_000_000
MINIMUM_BULK_RECORD_COUNT = 260
MINIMUM_AGGREGATE_RECORD_COUNT = 200
MAX_ARCHIVE_MEMBER_COUNT = 8
MAX_MEMBER_BYTES = 4_000_000
_ISO3 = re.compile(r"[A-Z]{3}")
_DATE = re.compile(r"20\d{2}-\d{2}-\d{2}")
_YEAR = re.compile(r"(?:19|20)\d{2}")
_MAIN_MEMBER = re.compile(
    r"API_(?P<indicator>[A-Z0-9.]+)_DS2_en_csv_v\d+_\d+\.csv"
)


@dataclass(frozen=True)
class FreshTarget:
    indicator: str
    year: str


TARGETS = (
    FreshTarget("EG.ELC.ACCS.ZS", "2022"),
    FreshTarget("SH.H2O.BASW.ZS", "2022"),
)


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def target_key(target: FreshTarget) -> str:
    if target not in TARGETS:
        raise ValueError("V2.47.40 target is outside the frozen fresh vector")
    return f"{target.indicator}@{target.year}"


def resolve_target(indicator: object, year: object) -> FreshTarget:
    matches = [
        target
        for target in TARGETS
        if target.indicator == indicator and target.year == year
    ]
    if len(matches) != 1:
        raise ValueError("V2.47.40 target identity drifted")
    return matches[0]


def endpoint_url(target: FreshTarget, representation: str) -> str:
    target_key(target)
    if representation == PREFERRED_REPRESENTATION:
        return (
            f"https://{WORLD_BANK_HOST}/v2/en/indicator/{target.indicator}"
            "?downloadformat=csv"
        )
    if representation == FALLBACK_REPRESENTATION:
        query = urlencode(
            (("date", target.year), ("format", "json"), ("per_page", "400"))
        )
        return (
            f"https://{WORLD_BANK_HOST}/v2/country/all/indicator/"
            f"{target.indicator}?{query}"
        )
    raise ValueError("V2.47.40 representation drifted")


def _canonical_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    if not value.is_finite():
        raise ValueError("V2.47.40 non-finite value")
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def semantic_sha256(records: Mapping[str, Decimal | None]) -> str:
    vector = [[code, _canonical_decimal(records[code])] for code in sorted(records)]
    return hashlib.sha256(
        json.dumps(vector, ensure_ascii=True, separators=(",", ":")).encode()
    ).hexdigest()


def _reject_constant(value: str) -> None:
    raise ValueError(f"V2.47.40 invalid JSON constant: {value}")


def _integer(value: object) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, Decimal))
        or Decimal(value) != Decimal(value).to_integral_value()
    ):
        raise ValueError("V2.47.40 pagination drifted")
    return int(value)


def _aggregate_records(
    raw: bytes, target: FreshTarget
) -> tuple[dict[str, Decimal | None], str]:
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            parse_float=Decimal,
            parse_int=Decimal,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, InvalidOperation) as exc:
        raise ValueError("V2.47.40 invalid aggregate JSON") from exc
    if (
        not isinstance(payload, list)
        or len(payload) != 2
        or not isinstance(payload[0], Mapping)
        or not isinstance(payload[1], list)
    ):
        raise ValueError("V2.47.40 aggregate envelope drifted")
    metadata, rows = payload
    updated = str(metadata.get("lastupdated", ""))
    if (
        _integer(metadata.get("page")) != 1
        or _integer(metadata.get("pages")) != 1
        or _integer(metadata.get("per_page")) < len(rows)
        or _integer(metadata.get("total")) != len(rows)
        or _DATE.fullmatch(updated) is None
    ):
        raise ValueError("V2.47.40 aggregate metadata drifted")
    records: dict[str, Decimal | None] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("V2.47.40 aggregate row drifted")
        indicator = row.get("indicator")
        code = row.get("countryiso3code")
        value = row.get("value")
        if (
            not isinstance(indicator, Mapping)
            or indicator.get("id") != target.indicator
            or row.get("date") != target.year
            or isinstance(value, bool)
            or value is not None
            and not isinstance(value, Decimal)
        ):
            raise ValueError("V2.47.40 aggregate identity drifted")
        if not isinstance(code, str) or _ISO3.fullmatch(code) is None:
            continue
        if code in records:
            raise ValueError("V2.47.40 duplicate aggregate ISO3")
        if isinstance(value, Decimal) and not value.is_finite():
            raise ValueError("V2.47.40 aggregate value is non-finite")
        records[code] = value
    return records, updated


def _strip_trailing_empty(row: list[str]) -> list[str]:
    return row[:-1] if row and row[-1] == "" else row


def _bulk_records(raw: bytes, target: FreshTarget) -> dict[str, Decimal | None]:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_RESPONSE_BYTES:
        raise ValueError("V2.47.40 bulk archive size drifted")
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError("V2.47.40 invalid ZIP") from exc
    with archive:
        infos = archive.infolist()
        if (
            not 1 <= len(infos) <= MAX_ARCHIVE_MEMBER_COUNT
            or any(
                info.is_dir()
                or info.flag_bits & 0x1
                or info.file_size > MAX_MEMBER_BYTES
                or "/" in info.filename
                or "\\" in info.filename
                for info in infos
            )
        ):
            raise ValueError("V2.47.40 unsafe ZIP member surface")
        candidates = []
        for info in infos:
            match = _MAIN_MEMBER.fullmatch(info.filename)
            if match is not None and match.group("indicator") == target.indicator:
                candidates.append(info)
        if len(candidates) != 1:
            raise ValueError("V2.47.40 main CSV member drifted")
        try:
            text = archive.read(candidates[0]).decode("utf-8-sig")
        except (KeyError, RuntimeError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
            raise ValueError("V2.47.40 unreadable main CSV") from exc
    try:
        raw_rows = list(csv.reader(io.StringIO(text, newline="")))
    except csv.Error as exc:
        raise ValueError("V2.47.40 malformed main CSV") from exc
    if (
        len(raw_rows) < 6
        or _strip_trailing_empty(raw_rows[0])
        != ["Data Source", "World Development Indicators"]
        or raw_rows[1] != []
        or len(_strip_trailing_empty(raw_rows[2])) != 2
        or _strip_trailing_empty(raw_rows[2])[0] != "Last Updated Date"
        or _DATE.fullmatch(_strip_trailing_empty(raw_rows[2])[1]) is None
        or raw_rows[3] != []
    ):
        raise ValueError("V2.47.40 bulk dataset preamble drifted")
    header = _strip_trailing_empty(raw_rows[4])
    if (
        header[:4]
        != ["Country Name", "Country Code", "Indicator Name", "Indicator Code"]
        or len(header) < 5
        or any(_YEAR.fullmatch(value) is None for value in header[4:])
        or len(set(header)) != len(header)
        or header[4:] != sorted(header[4:])
        or target.year not in header
    ):
        raise ValueError("V2.47.40 bulk dataset header drifted")
    year_index = header.index(target.year)
    records: dict[str, Decimal | None] = {}
    for raw_row in raw_rows[5:]:
        if raw_row == []:
            continue
        row = _strip_trailing_empty(raw_row)
        if len(row) != len(header):
            raise ValueError("V2.47.40 bulk dataset row width drifted")
        country_name, code, indicator_name, indicator = row[:4]
        if not country_name or not indicator_name or indicator != target.indicator:
            raise ValueError("V2.47.40 bulk dataset identity drifted")
        if _ISO3.fullmatch(code) is None:
            continue
        if code in records:
            raise ValueError("V2.47.40 duplicate bulk ISO3")
        lexeme = row[year_index].strip()
        value: Decimal | None = None
        if lexeme:
            try:
                value = Decimal(lexeme)
            except InvalidOperation as exc:
                raise ValueError("V2.47.40 invalid bulk decimal") from exc
            if not value.is_finite():
                raise ValueError("V2.47.40 non-finite bulk decimal")
        records[code] = value
    if not records:
        raise ValueError("V2.47.40 empty bulk dataset")
    return records


def parse_records(
    raw: bytes, *, target: FreshTarget, representation: str
) -> tuple[dict[str, Decimal | None], str | None]:
    target_key(target)
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_RESPONSE_BYTES:
        raise ValueError("V2.47.40 response size drifted")
    updated: str | None = None
    if representation == PREFERRED_REPRESENTATION:
        records = _bulk_records(raw, target)
        minimum = MINIMUM_BULK_RECORD_COUNT
    elif representation == FALLBACK_REPRESENTATION:
        records, updated = _aggregate_records(raw, target)
        minimum = MINIMUM_AGGREGATE_RECORD_COUNT
    else:
        raise ValueError("V2.47.40 representation drifted")
    if (
        len(records) < minimum
        or any(_ISO3.fullmatch(code) is None for code in records)
        or not any(value is not None for value in records.values())
    ):
        raise ValueError("V2.47.40 official vector is incomplete")
    return records, updated


def compare_common_values(
    preferred: Mapping[str, Decimal | None],
    fallback: Mapping[str, Decimal | None],
) -> dict[str, Any]:
    if (
        len(preferred) < MINIMUM_BULK_RECORD_COUNT
        or len(fallback) < MINIMUM_AGGREGATE_RECORD_COUNT
        or any(_ISO3.fullmatch(code) is None for code in {*preferred, *fallback})
    ):
        raise ValueError("V2.47.40 comparison input drifted")
    common = sorted(set(preferred) & set(fallback))
    preferred_only = sorted(set(preferred) - set(fallback))
    fallback_only = sorted(set(fallback) - set(preferred))
    mismatches = sum(
        _canonical_decimal(preferred[code]) != _canonical_decimal(fallback[code])
        for code in common
    )
    return {
        "preferred_record_count": len(preferred),
        "fallback_record_count": len(fallback),
        "common_domain_count": len(common),
        "preferred_only_domain_count": len(preferred_only),
        "fallback_only_domain_count": len(fallback_only),
        "common_value_mismatch_count": mismatches,
        "common_domain_sha256": payload_sha256(common),
        "preferred_only_domain_sha256": payload_sha256(preferred_only),
        "fallback_only_domain_sha256": payload_sha256(fallback_only),
        "content_persisted": False,
    }


def _expected_urls(target: FreshTarget) -> dict[str, str]:
    return {
        representation: endpoint_url(target, representation)
        for representation in REPRESENTATIONS
    }


def reconcile_target(
    target: FreshTarget, responses: Mapping[str, bytes]
) -> dict[str, Any]:
    expected = _expected_urls(target)
    if (
        not isinstance(responses, Mapping)
        or set(responses) != set(expected.values())
        or any(not isinstance(raw, bytes) for raw in responses.values())
    ):
        raise ValueError("V2.47.40 response address vector drifted")
    valid: dict[str, dict[str, Decimal | None]] = {}
    failure_counts: dict[str, int] = {}
    representation_receipts = []
    for representation in REPRESENTATIONS:
        raw = responses[expected[representation]]
        try:
            records, _updated = parse_records(
                raw, target=target, representation=representation
            )
        except (TypeError, ValueError):
            records = {}
            failure = "schema_or_transport_invalid"
            failure_counts[failure] = failure_counts.get(failure, 0) + 1
            representation_receipts.append(
                {
                    "representation": representation,
                    "schema_valid": False,
                    "record_count": 0,
                    "semantic_sha256": None,
                    "response_content_persisted": False,
                }
            )
            continue
        valid[representation] = records
        representation_receipts.append(
            {
                "representation": representation,
                "schema_valid": True,
                "record_count": len(records),
                "semantic_sha256": semantic_sha256(records),
                "response_content_persisted": False,
            }
        )
    comparison = None
    consistency_failed = False
    agreement = False
    if set(valid) == set(REPRESENTATIONS):
        comparison = compare_common_values(
            valid[PREFERRED_REPRESENTATION], valid[FALLBACK_REPRESENTATION]
        )
        agreement = (
            comparison["common_domain_count"] >= MINIMUM_AGGREGATE_RECORD_COUNT
            and comparison["common_value_mismatch_count"] == 0
        )
        consistency_failed = not agreement
    admitted = bool(valid) and not consistency_failed
    selected = None
    records: dict[str, Decimal | None] = {}
    if admitted:
        selected = (
            PREFERRED_REPRESENTATION
            if PREFERRED_REPRESENTATION in valid
            else FALLBACK_REPRESENTATION
        )
        records = dict(valid[selected])
    receipt = {
        "artifact_version": 1,
        "role": "v24740_target_resilience_content_free_receipt",
        "policy_id": POLICY_ID,
        "target_key": target_key(target),
        "fixed_requested_representations": list(REPRESENTATIONS),
        "representation_receipts": representation_receipts,
        "schema_valid_representation_count": len(valid),
        "selected_representation": selected,
        "target_admitted": admitted,
        "dual_valid_common_value_agreement": agreement,
        "dual_valid_consistency_failed": consistency_failed,
        "comparison": comparison,
        "admitted_record_count": len(records),
        "failure_type_counts": failure_counts,
        "target_failure_isolated": True,
        "response_country_value_or_content_persisted": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    return {
        "target_key": target_key(target),
        "records": records,
        "receipt": validate_receipt(receipt),
    }


def reconcile_bundle(responses: Mapping[str, bytes]) -> dict[str, Any]:
    expected = {
        endpoint_url(target, representation)
        for target in TARGETS
        for representation in REPRESENTATIONS
    }
    if (
        not isinstance(responses, Mapping)
        or set(responses) != expected
        or any(not isinstance(raw, bytes) for raw in responses.values())
    ):
        raise ValueError("V2.47.40 bundle address vector drifted")
    records_by_target: dict[str, dict[str, Decimal | None]] = {}
    receipts = []
    for target in TARGETS:
        urls = _expected_urls(target)
        resolved = reconcile_target(
            target, {url: responses[url] for url in urls.values()}
        )
        receipts.append(resolved["receipt"])
        if resolved["receipt"]["target_admitted"]:
            records_by_target[target_key(target)] = resolved["records"]
    summary = {
        "artifact_version": 1,
        "role": "v24740_bundle_resilience_content_free_receipt",
        "policy_id": POLICY_ID,
        "target_count": len(TARGETS),
        "admitted_target_count": len(records_by_target),
        "abstained_target_count": len(TARGETS) - len(records_by_target),
        "all_target_failures_isolated": True,
        "retry_resume_or_selective_rerun": False,
        "response_country_value_or_content_persisted": False,
    }
    summary["receipt_payload_sha256"] = payload_sha256(summary)
    return {
        "records_by_target": records_by_target,
        "target_receipts": receipts,
        "receipt": validate_bundle_receipt(summary, target_receipts=receipts),
    }


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal_value = unsigned.pop("receipt_payload_sha256", None)
    rows = copied.get("representation_receipts")
    comparison = copied.get("comparison")
    valid_count = copied.get("schema_valid_representation_count")
    admitted = copied.get("target_admitted")
    selected = copied.get("selected_representation")
    row_valid = (
        isinstance(rows, Sequence)
        and not isinstance(rows, (str, bytes))
        and len(rows) == len(REPRESENTATIONS)
        and all(isinstance(row, Mapping) for row in rows)
    )
    valid_rows = {
        str(row.get("representation")): row
        for row in rows
        if isinstance(row, Mapping) and row.get("schema_valid") is True
    } if row_valid else {}
    comparison_valid = comparison is None or (
        isinstance(comparison, Mapping)
        and set(comparison)
        == {
            "preferred_record_count",
            "fallback_record_count",
            "common_domain_count",
            "preferred_only_domain_count",
            "fallback_only_domain_count",
            "common_value_mismatch_count",
            "common_domain_sha256",
            "preferred_only_domain_sha256",
            "fallback_only_domain_sha256",
            "content_persisted",
        }
        and all(
            isinstance(comparison.get(name), int)
            and not isinstance(comparison.get(name), bool)
            and comparison.get(name) >= 0
            for name in (
                "preferred_record_count",
                "fallback_record_count",
                "common_domain_count",
                "preferred_only_domain_count",
                "fallback_only_domain_count",
                "common_value_mismatch_count",
            )
        )
        and comparison.get("preferred_record_count")
        == comparison.get("common_domain_count")
        + comparison.get("preferred_only_domain_count")
        and comparison.get("fallback_record_count")
        == comparison.get("common_domain_count")
        + comparison.get("fallback_only_domain_count")
        and all(
            isinstance(comparison.get(name), str)
            and re.fullmatch(r"[0-9a-f]{64}", comparison.get(name)) is not None
            for name in (
                "common_domain_sha256",
                "preferred_only_domain_sha256",
                "fallback_only_domain_sha256",
            )
        )
        and comparison.get("content_persisted") is False
    )
    expected_agreement = (
        isinstance(comparison, Mapping)
        and comparison.get("common_domain_count", 0) >= MINIMUM_AGGREGATE_RECORD_COUNT
        and comparison.get("common_value_mismatch_count") == 0
    )
    expected_consistency_failed = valid_count == len(REPRESENTATIONS) and not expected_agreement
    expected_admitted = valid_count in {1, 2} and not expected_consistency_failed
    expected_selected = None
    if expected_admitted:
        expected_selected = (
            PREFERRED_REPRESENTATION
            if PREFERRED_REPRESENTATION in valid_rows
            else FALLBACK_REPRESENTATION
        )
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "target_key",
            "fixed_requested_representations",
            "representation_receipts",
            "schema_valid_representation_count",
            "selected_representation",
            "target_admitted",
            "dual_valid_common_value_agreement",
            "dual_valid_consistency_failed",
            "comparison",
            "admitted_record_count",
            "failure_type_counts",
            "target_failure_isolated",
            "response_country_value_or_content_persisted",
            "benchmark_launch_or_evaluator_authorized",
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v24740_target_resilience_content_free_receipt"
        or copied.get("policy_id") != POLICY_ID
        or copied.get("target_key") not in {target_key(target) for target in TARGETS}
        or copied.get("fixed_requested_representations") != list(REPRESENTATIONS)
        or not row_valid
        or [row.get("representation") for row in rows if isinstance(row, Mapping)]
        != list(REPRESENTATIONS)
        or any(
            set(row)
            != {
                "representation",
                "schema_valid",
                "record_count",
                "semantic_sha256",
                "response_content_persisted",
            }
            or not isinstance(row.get("schema_valid"), bool)
            or not isinstance(row.get("record_count"), int)
            or isinstance(row.get("record_count"), bool)
            or (
                row.get("record_count")
                < (
                    MINIMUM_BULK_RECORD_COUNT
                    if row.get("representation") == PREFERRED_REPRESENTATION
                    else MINIMUM_AGGREGATE_RECORD_COUNT
                )
                if row.get("schema_valid") is True
                else row.get("record_count") != 0
            )
            or (
                not isinstance(row.get("semantic_sha256"), str)
                or re.fullmatch(r"[0-9a-f]{64}", row.get("semantic_sha256")) is None
                if row.get("schema_valid") is True
                else row.get("semantic_sha256") is not None
            )
            or row.get("response_content_persisted") is not False
            for row in rows
        )
        or isinstance(valid_count, bool)
        or not isinstance(valid_count, int)
        or valid_count != sum(row.get("schema_valid") is True for row in rows)
        or not isinstance(admitted, bool)
        or selected != expected_selected
        or admitted is not expected_admitted
        or not comparison_valid
        or (comparison is not None) is not (valid_count == len(REPRESENTATIONS))
        or not isinstance(copied.get("admitted_record_count"), int)
        or isinstance(copied.get("admitted_record_count"), bool)
        or copied.get("admitted_record_count") < 0
        or (
            admitted
            and copied.get("admitted_record_count")
            != valid_rows[selected].get("record_count")
        )
        or (not admitted and copied.get("admitted_record_count") != 0)
        or copied.get("dual_valid_common_value_agreement")
        is not expected_agreement
        or copied.get("dual_valid_consistency_failed")
        is not expected_consistency_failed
        or copied.get("failure_type_counts")
        != ({"schema_or_transport_invalid": len(REPRESENTATIONS) - valid_count}
            if valid_count < len(REPRESENTATIONS) else {})
        or copied.get("target_failure_isolated") is not True
        or copied.get("response_country_value_or_content_persisted") is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal_value != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.40 target receipt drifted")
    return copied


def validate_bundle_receipt(
    value: Mapping[str, Any], *, target_receipts: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal_value = unsigned.pop("receipt_payload_sha256", None)
    if (
        not isinstance(target_receipts, Sequence)
        or isinstance(target_receipts, (str, bytes))
        or len(target_receipts) != len(TARGETS)
    ):
        raise ValueError("V2.47.40 bundle target receipts drifted")
    validated = [validate_receipt(item) for item in target_receipts]
    if [item["target_key"] for item in validated] != [
        target_key(target) for target in TARGETS
    ]:
        raise ValueError("V2.47.40 bundle target order drifted")
    admitted = sum(item["target_admitted"] is True for item in validated)
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "target_count",
            "admitted_target_count",
            "abstained_target_count",
            "all_target_failures_isolated",
            "retry_resume_or_selective_rerun",
            "response_country_value_or_content_persisted",
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role")
        != "v24740_bundle_resilience_content_free_receipt"
        or copied.get("policy_id") != POLICY_ID
        or copied.get("target_count") != len(TARGETS)
        or copied.get("admitted_target_count") != admitted
        or copied.get("abstained_target_count") != len(TARGETS) - admitted
        or copied.get("all_target_failures_isolated") is not True
        or copied.get("retry_resume_or_selective_rerun") is not False
        or copied.get("response_country_value_or_content_persisted") is not False
        or seal_value != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.40 bundle receipt drifted")
    return copied


__all__ = [
    "FALLBACK_REPRESENTATION",
    "FreshTarget",
    "MAX_RESPONSE_BYTES",
    "POLICY_ID",
    "PREFERRED_REPRESENTATION",
    "REPRESENTATIONS",
    "TARGETS",
    "compare_common_values",
    "endpoint_url",
    "parse_records",
    "reconcile_bundle",
    "reconcile_target",
    "resolve_target",
    "semantic_sha256",
    "target_key",
    "validate_receipt",
    "validate_bundle_receipt",
]
