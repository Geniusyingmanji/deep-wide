"""Content-free World Bank transport reliability primitives.

The fixed target vector is the union of indicators already frozen by the
V2.47.09 sparse adapter and the V2.46.90 benchmark-external population.  This
module has no filesystem, process, network, benchmark, evaluator, credential,
or scoring capability.  It validates caller-supplied public response bytes and
returns only hashes and aggregate counts.
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


POLICY_ID = "v24719_worldbank_dual_transport_reliability_v1"
WORLD_BANK_HOST = "api.worldbank.org"
REPRESENTATIONS = ("bulk_zip", "aggregate_json")
MAX_RESPONSE_BYTES = 4_000_000
MINIMUM_RECORD_COUNT = 200
_ISO3 = re.compile(r"[A-Z]{3}")
_DATE = re.compile(r"20\d{2}-\d{2}-\d{2}")


@dataclass(frozen=True)
class TransportTarget:
    indicator: str
    year: str


# Four V2.47.09 targets plus the two V2.46.90 external-population targets.
TARGETS = (
    TransportTarget("AG.SRF.TOTL.K2", "2022"),
    TransportTarget("EN.POP.DNST", "2022"),
    TransportTarget("SP.POP.TOTL", "2023"),
    TransportTarget("TG.VAL.TOTL.GD.ZS", "2023"),
    TransportTarget("NY.GDP.PCAP.CD", "2023"),
    TransportTarget("SP.URB.TOTL.IN.ZS", "2023"),
)


def target_key(target: TransportTarget) -> str:
    if target not in TARGETS:
        raise ValueError("V2.47.19 target is outside the frozen vector")
    return f"{target.indicator}@{target.year}"


def endpoint_url(target: TransportTarget, representation: str) -> str:
    target_key(target)
    if representation == "bulk_zip":
        return (
            f"https://{WORLD_BANK_HOST}/v2/en/indicator/{target.indicator}"
            "?downloadformat=csv"
        )
    if representation == "aggregate_json":
        query = urlencode(
            (
                ("date", target.year),
                ("format", "json"),
                ("per_page", "400"),
            )
        )
        return (
            f"https://{WORLD_BANK_HOST}/v2/country/all/indicator/"
            f"{target.indicator}?{query}"
        )
    raise ValueError("V2.47.19 representation is invalid")


def resolve_target(indicator: object, year: object) -> TransportTarget:
    matches = [
        target
        for target in TARGETS
        if target.indicator == indicator and target.year == year
    ]
    if len(matches) != 1:
        raise ValueError("V2.47.19 target identity drifted")
    return matches[0]


def _canonical_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    if not value.is_finite():
        raise ValueError("V2.47.19 non-finite value")
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _semantic_digest(records: Mapping[str, Decimal | None]) -> str:
    vector = [
        [code, _canonical_decimal(records[code])]
        for code in sorted(records)
    ]
    return hashlib.sha256(
        json.dumps(vector, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _reject_constant(value: str) -> None:
    raise ValueError(f"V2.47.19 invalid JSON constant: {value}")


def _parse_aggregate_json(
    raw: bytes, target: TransportTarget
) -> tuple[dict[str, Decimal | None], str]:
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            parse_float=Decimal,
            parse_int=Decimal,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, InvalidOperation) as exc:
        raise ValueError("V2.47.19 invalid aggregate JSON") from exc
    if (
        not isinstance(payload, list)
        or len(payload) != 2
        or not isinstance(payload[0], Mapping)
        or not isinstance(payload[1], list)
    ):
        raise ValueError("V2.47.19 aggregate response shape drifted")
    metadata = payload[0]
    rows = payload[1]

    def integer(name: str) -> int:
        value = metadata.get(name)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, Decimal))
            or Decimal(value) != Decimal(value).to_integral_value()
        ):
            raise ValueError("V2.47.19 aggregate pagination drifted")
        return int(value)

    last_updated = str(metadata.get("lastupdated", ""))
    if (
        integer("page") != 1
        or integer("pages") != 1
        or integer("per_page") < len(rows)
        or integer("total") != len(rows)
        or _DATE.fullmatch(last_updated) is None
    ):
        raise ValueError("V2.47.19 aggregate metadata drifted")
    records: dict[str, Decimal | None] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("V2.47.19 aggregate row is invalid")
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
            raise ValueError("V2.47.19 aggregate record identity drifted")
        # ``country/all`` also returns aggregate rows whose ISO3 surface is
        # empty.  The official bulk CSV follows the same convention and the
        # frozen V2.47.09 parser excludes those rows.  Skip them symmetrically.
        if not isinstance(code, str) or _ISO3.fullmatch(code) is None:
            continue
        if code in records:
            raise ValueError("V2.47.19 duplicate aggregate ISO3")
        if isinstance(value, Decimal) and not value.is_finite():
            raise ValueError("V2.47.19 aggregate value is non-finite")
        records[code] = value
    return records, last_updated


def parse_response(
    raw: bytes,
    *,
    target: TransportTarget,
    representation: str,
) -> dict[str, Any]:
    """Validate one response and return content-free semantic metadata."""

    target_key(target)
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_RESPONSE_BYTES:
        raise ValueError("V2.47.19 response size drifted")
    records, last_updated = parse_records(
        raw, target=target, representation=representation
    )
    return summarize_records(
        raw,
        target=target,
        representation=representation,
        records=records,
        last_updated=last_updated,
    )


def parse_records(
    raw: bytes,
    *,
    target: TransportTarget,
    representation: str,
) -> tuple[dict[str, Decimal | None], str | None]:
    """Return the in-memory official vector; callers must not persist it."""

    target_key(target)
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_RESPONSE_BYTES:
        raise ValueError("V2.47.19 response size drifted")
    last_updated: str | None = None
    if representation == "bulk_zip":
        spec = TargetSpec(target.indicator, target.year, "identity", 0)
        parsed = parse_bulk_archive(raw, spec)
        records = {code: row.value for code, row in parsed.items()}
    elif representation == "aggregate_json":
        records, last_updated = _parse_aggregate_json(raw, target)
    else:
        raise ValueError("V2.47.19 representation is invalid")
    if len(records) < MINIMUM_RECORD_COUNT:
        raise ValueError("V2.47.19 official record vector is incomplete")
    non_null = sum(value is not None for value in records.values())
    if non_null < 1:
        raise ValueError("V2.47.19 official value vector is empty")
    return records, last_updated


def summarize_records(
    raw: bytes,
    *,
    target: TransportTarget,
    representation: str,
    records: Mapping[str, Decimal | None],
    last_updated: str | None,
) -> dict[str, Any]:
    """Project an already validated vector to content-free metadata."""

    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_RESPONSE_BYTES:
        raise ValueError("V2.47.19 response size drifted")
    target_key(target)
    if representation not in REPRESENTATIONS or len(records) < MINIMUM_RECORD_COUNT:
        raise ValueError("V2.47.19 record summary input drifted")
    if any(_ISO3.fullmatch(code) is None for code in records):
        raise ValueError("V2.47.19 record summary identity drifted")
    non_null = sum(value is not None for value in records.values())
    if non_null < 1:
        raise ValueError("V2.47.19 record summary is empty")
    return {
        "target_key": target_key(target),
        "indicator": target.indicator,
        "year": target.year,
        "representation": representation,
        "response_bytes": len(raw),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "semantic_sha256": _semantic_digest(records),
        "record_count": len(records),
        "non_null_count": non_null,
        "last_updated": last_updated,
        "schema_valid": True,
        "response_content_persisted": False,
    }


def compare_record_vectors(
    left: Mapping[str, Decimal | None],
    right: Mapping[str, Decimal | None],
) -> dict[str, Any]:
    """Compare two official vectors without exposing any code or value."""

    if (
        len(left) < MINIMUM_RECORD_COUNT
        or len(right) < MINIMUM_RECORD_COUNT
        or any(_ISO3.fullmatch(code) is None for code in {*left, *right})
    ):
        raise ValueError("V2.47.19 comparison vector drifted")
    common = sorted(set(left) & set(right))
    mismatches = sum(
        _canonical_decimal(left[code]) != _canonical_decimal(right[code])
        for code in common
    )
    return {
        "left_record_count": len(left),
        "right_record_count": len(right),
        "common_record_count": len(common),
        "symmetric_difference_count": len(set(left) ^ set(right)),
        "common_value_mismatch_count": mismatches,
        "common_semantic_sha256": _semantic_digest(
            {code: left[code] for code in common}
        ),
        "content_persisted": False,
    }


PARSED_KEYS = frozenset(
    {
        "target_key",
        "indicator",
        "year",
        "representation",
        "response_bytes",
        "raw_sha256",
        "semantic_sha256",
        "record_count",
        "non_null_count",
        "last_updated",
        "schema_valid",
        "response_content_persisted",
    }
)


def validate_parsed(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    target = resolve_target(copied.get("indicator"), copied.get("year"))
    representation = copied.get("representation")
    if (
        set(copied) != PARSED_KEYS
        or copied.get("target_key") != target_key(target)
        or representation not in REPRESENTATIONS
        or isinstance(copied.get("response_bytes"), bool)
        or not isinstance(copied.get("response_bytes"), int)
        or not 0 < copied["response_bytes"] <= MAX_RESPONSE_BYTES
        or not isinstance(copied.get("raw_sha256"), str)
        or len(copied["raw_sha256"]) != 64
        or not isinstance(copied.get("semantic_sha256"), str)
        or len(copied["semantic_sha256"]) != 64
        or isinstance(copied.get("record_count"), bool)
        or not isinstance(copied.get("record_count"), int)
        or copied["record_count"] < MINIMUM_RECORD_COUNT
        or isinstance(copied.get("non_null_count"), bool)
        or not isinstance(copied.get("non_null_count"), int)
        or not 1 <= copied["non_null_count"] <= copied["record_count"]
        or copied.get("last_updated") is not None
        and (
            not isinstance(copied.get("last_updated"), str)
            or _DATE.fullmatch(copied["last_updated"]) is None
        )
        or representation == "bulk_zip"
        and copied.get("last_updated") is not None
        or copied.get("schema_valid") is not True
        or copied.get("response_content_persisted") is not False
    ):
        raise ValueError("V2.47.19 parsed response drifted")
    return copied


__all__ = [
    "MAX_RESPONSE_BYTES",
    "MINIMUM_RECORD_COUNT",
    "PARSED_KEYS",
    "POLICY_ID",
    "REPRESENTATIONS",
    "TARGETS",
    "TransportTarget",
    "endpoint_url",
    "compare_record_vectors",
    "parse_records",
    "parse_response",
    "resolve_target",
    "summarize_records",
    "target_key",
    "validate_parsed",
]
