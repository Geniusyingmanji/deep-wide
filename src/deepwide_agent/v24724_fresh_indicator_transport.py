"""Fresh-indicator dual-representation transport primitives.

The two targets come from the sealed V2.47.23 pre-outcome design.  This module
has no filesystem, process, network, benchmark, evaluator, or credential
capability.  It validates caller-supplied World Bank bytes in memory and emits
content-free metadata only.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping
from urllib.parse import urlencode

from .v24709_sparse_worldbank_adapter import TargetSpec, parse_bulk_archive


POLICY_ID = "v24724_fresh_indicator_dual_transport_v1"
WORLD_BANK_HOST = "api.worldbank.org"
REPRESENTATIONS = ("bulk_zip", "aggregate_json")
PRIMARY_REPRESENTATION = "bulk_zip"
COMPARATOR_REPRESENTATION = "aggregate_json"
MAX_RESPONSE_BYTES = 4_000_000
MINIMUM_PRIMARY_RECORD_COUNT = 260
MINIMUM_COMPARATOR_RECORD_COUNT = 200
_ISO3 = re.compile(r"[A-Z]{3}")
_DATE = re.compile(r"20\d{2}-\d{2}-\d{2}")


@dataclass(frozen=True)
class FreshTarget:
    indicator: str
    year: str


TARGETS = (
    FreshTarget("IT.NET.USER.ZS", "2022"),
    FreshTarget("SP.DYN.LE00.IN", "2022"),
)


def target_key(target: FreshTarget) -> str:
    if target not in TARGETS:
        raise ValueError("V2.47.24 target is outside the fresh vector")
    return f"{target.indicator}@{target.year}"


def resolve_target(indicator: object, year: object) -> FreshTarget:
    matches = [
        target
        for target in TARGETS
        if target.indicator == indicator and target.year == year
    ]
    if len(matches) != 1:
        raise ValueError("V2.47.24 target identity drifted")
    return matches[0]


def endpoint_url(target: FreshTarget, representation: str) -> str:
    target_key(target)
    if representation == PRIMARY_REPRESENTATION:
        return (
            f"https://{WORLD_BANK_HOST}/v2/en/indicator/{target.indicator}"
            "?downloadformat=csv"
        )
    if representation == COMPARATOR_REPRESENTATION:
        query = urlencode(
            (("date", target.year), ("format", "json"), ("per_page", "400"))
        )
        return (
            f"https://{WORLD_BANK_HOST}/v2/country/all/indicator/"
            f"{target.indicator}?{query}"
        )
    raise ValueError("V2.47.24 representation drifted")


def _canonical_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    if not value.is_finite():
        raise ValueError("V2.47.24 non-finite value")
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def semantic_sha256(records: Mapping[str, Decimal | None]) -> str:
    vector = [
        [code, _canonical_decimal(records[code])]
        for code in sorted(records)
    ]
    return hashlib.sha256(
        json.dumps(vector, ensure_ascii=True, separators=(",", ":")).encode()
    ).hexdigest()


def _reject_constant(value: str) -> None:
    raise ValueError(f"V2.47.24 invalid JSON constant: {value}")


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
        raise ValueError("V2.47.24 invalid aggregate JSON") from exc
    if (
        not isinstance(payload, list)
        or len(payload) != 2
        or not isinstance(payload[0], Mapping)
        or not isinstance(payload[1], list)
    ):
        raise ValueError("V2.47.24 aggregate envelope drifted")
    metadata, rows = payload

    def integer(name: str) -> int:
        value = metadata.get(name)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, Decimal))
            or Decimal(value) != Decimal(value).to_integral_value()
        ):
            raise ValueError("V2.47.24 pagination drifted")
        return int(value)

    updated = str(metadata.get("lastupdated", ""))
    if (
        integer("page") != 1
        or integer("pages") != 1
        or integer("per_page") < len(rows)
        or integer("total") != len(rows)
        or _DATE.fullmatch(updated) is None
    ):
        raise ValueError("V2.47.24 aggregate metadata drifted")
    records: dict[str, Decimal | None] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("V2.47.24 aggregate row drifted")
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
            raise ValueError("V2.47.24 aggregate identity drifted")
        if not isinstance(code, str) or _ISO3.fullmatch(code) is None:
            continue
        if code in records:
            raise ValueError("V2.47.24 duplicate aggregate ISO3")
        if isinstance(value, Decimal) and not value.is_finite():
            raise ValueError("V2.47.24 aggregate value is non-finite")
        records[code] = value
    return records, updated


def parse_records(
    raw: bytes, *, target: FreshTarget, representation: str
) -> tuple[dict[str, Decimal | None], str | None]:
    target_key(target)
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_RESPONSE_BYTES:
        raise ValueError("V2.47.24 response size drifted")
    updated: str | None = None
    if representation == PRIMARY_REPRESENTATION:
        parsed = parse_bulk_archive(
            raw, TargetSpec(target.indicator, target.year, "identity", 0)
        )
        records = {code: row.value for code, row in parsed.items()}
        minimum = MINIMUM_PRIMARY_RECORD_COUNT
    elif representation == COMPARATOR_REPRESENTATION:
        records, updated = _aggregate_records(raw, target)
        minimum = MINIMUM_COMPARATOR_RECORD_COUNT
    else:
        raise ValueError("V2.47.24 representation drifted")
    if len(records) < minimum or not any(value is not None for value in records.values()):
        raise ValueError("V2.47.24 official vector is incomplete")
    return records, updated


def parse_response(
    raw: bytes, *, target: FreshTarget, representation: str
) -> dict[str, Any]:
    records, updated = parse_records(
        raw, target=target, representation=representation
    )
    return {
        "target_key": target_key(target),
        "indicator": target.indicator,
        "year": target.year,
        "representation": representation,
        "response_bytes": len(raw),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "semantic_sha256": semantic_sha256(records),
        "record_count": len(records),
        "non_null_count": sum(value is not None for value in records.values()),
        "last_updated": updated,
        "response_content_persisted": False,
    }


def compare_domains(
    primary: Mapping[str, Decimal | None],
    comparator: Mapping[str, Decimal | None],
) -> dict[str, Any]:
    if (
        len(primary) < MINIMUM_PRIMARY_RECORD_COUNT
        or len(comparator) < MINIMUM_COMPARATOR_RECORD_COUNT
        or any(_ISO3.fullmatch(code) is None for code in {*primary, *comparator})
    ):
        raise ValueError("V2.47.24 comparison input drifted")
    common = sorted(set(primary) & set(comparator))
    primary_only = sorted(set(primary) - set(comparator))
    comparator_only = sorted(set(comparator) - set(primary))
    mismatches = sum(
        _canonical_decimal(primary[code]) != _canonical_decimal(comparator[code])
        for code in common
    )
    return {
        "primary_record_count": len(primary),
        "comparator_record_count": len(comparator),
        "common_domain_count": len(common),
        "primary_only_domain_count": len(primary_only),
        "comparator_only_domain_count": len(comparator_only),
        "common_value_mismatch_count": mismatches,
        "common_domain_sha256": hashlib.sha256(
            json.dumps(common, separators=(",", ":")).encode()
        ).hexdigest(),
        "primary_only_domain_sha256": hashlib.sha256(
            json.dumps(primary_only, separators=(",", ":")).encode()
        ).hexdigest(),
        "comparator_only_domain_sha256": hashlib.sha256(
            json.dumps(comparator_only, separators=(",", ":")).encode()
        ).hexdigest(),
        "content_persisted": False,
    }


__all__ = [
    "COMPARATOR_REPRESENTATION",
    "MAX_RESPONSE_BYTES",
    "MINIMUM_COMPARATOR_RECORD_COUNT",
    "MINIMUM_PRIMARY_RECORD_COUNT",
    "POLICY_ID",
    "PRIMARY_REPRESENTATION",
    "REPRESENTATIONS",
    "TARGETS",
    "FreshTarget",
    "compare_domains",
    "endpoint_url",
    "parse_records",
    "parse_response",
    "resolve_target",
    "semantic_sha256",
    "target_key",
]
