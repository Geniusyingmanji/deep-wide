#!/usr/bin/env python3
"""Design an evaluator-isolated World Bank target-value population.

The design is deterministic over three public World Bank responses: one
country catalogue and two bulk indicator snapshots.  It excludes all fixture
countries and a conservative set of countries used by earlier repository
World Bank diagnostics, requires two non-null official values per country,
and selects countries by a frozen hash rank under a region cap.

This module is not a forward runtime.  Its command-line entry point remains
inert until a separate clean-build audit explicitly authorizes one population
publication.  It never calls a model, hosted search, benchmark, or evaluator.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402


DATE = "20260806"
PARENT = Path(f"results/v24687_worldbank_target_value_build_audit_v1_{DATE}.json")
AUTHORIZATION = Path(
    f"results/v24689_worldbank_population_design_build_audit_v1_{DATE}.json"
)
PRIVATE = Path(f"evaluation/v24688_worldbank_population_private_v1_{DATE}.json")
OUTPUT = Path(f"results/v24688_worldbank_population_design_v1_{DATE}.json")
COUNTRY_CATALOG_URL = (
    "https://api.worldbank.org/v2/country?format=json&per_page=400"
)
TARGETS = (
    {
        "label": "GDP per capita (current US$)",
        "indicator": "NY.GDP.PCAP.CD",
        "year": "2023",
    },
    {
        "label": "Urban population (%)",
        "indicator": "SP.URB.TOTL.IN.ZS",
        "year": "2023",
    },
)
SELECTED_COUNT = 48
TASK_SIZE = 4
TASK_COUNT = SELECTED_COUNT // TASK_SIZE
REGION_CAP = 8
EXCLUDED_ISO3 = frozenset(
    {
        # V2.46.86 test fixtures.
        "BTN",
        "LIE",
        "MCO",
        "SMR",
        # Conservative exclusion of countries visible in earlier repository
        # World Bank/GDP diagnostics and their common comparison cohort.
        "ARG",
        "AUS",
        "BRA",
        "CAN",
        "CHN",
        "DEU",
        "FRA",
        "GBR",
        "IDN",
        "IND",
        "ITA",
        "JPN",
        "KOR",
        "MEX",
        "RUS",
        "SAU",
        "TUR",
        "USA",
        "ZAF",
    }
)


class _DecimalLexeme(str):
    """A finite JSON decimal token retaining its source spelling."""


def _parse_decimal(value: str) -> _DecimalLexeme:
    parsed = Decimal(value)
    if not parsed.is_finite():
        raise ValueError("V2.46.88 non-finite decimal")
    return _DecimalLexeme(value)


def _reject_constant(value: str) -> None:
    raise ValueError(f"V2.46.88 non-standard JSON number: {value}")


def indicator_url(indicator: str, year: str) -> str:
    metric = str(indicator)
    date = str(year)
    if not metric or not date.isdigit() or len(date) != 4:
        raise ValueError("V2.46.88 indicator address drifted")
    query = urlencode((("date", date), ("format", "json"), ("per_page", "400")))
    return (
        "https://api.worldbank.org/v2/country/all/indicator/"
        f"{metric}?{query}"
    )


def _decode(raw: bytes) -> Any:
    return json.loads(
        raw.decode("utf-8"),
        parse_float=_parse_decimal,
        parse_constant=_reject_constant,
    )


def parse_country_catalog(raw: bytes) -> tuple[dict[str, dict[str, str]], dict[str, Any]]:
    payload = _decode(raw)
    if (
        not isinstance(payload, list)
        or len(payload) != 2
        or not isinstance(payload[0], Mapping)
        or payload[0].get("page") != 1
        or payload[0].get("pages") != 1
        or not isinstance(payload[1], list)
    ):
        raise ValueError("V2.46.88 country catalogue envelope drifted")
    countries: dict[str, dict[str, str]] = {}
    for row in payload[1]:
        if not isinstance(row, Mapping):
            continue
        iso3 = str(row.get("id", ""))
        name = str(row.get("name", "")).strip()
        region = row.get("region")
        region_id = str(region.get("id", "")) if isinstance(region, Mapping) else ""
        region_name = (
            str(region.get("value", "")).strip()
            if isinstance(region, Mapping)
            else ""
        )
        if (
            len(iso3) != 3
            or not iso3.isalpha()
            or not iso3.isupper()
            or region_id in {"", "NA"}
            or not region_name
            or not name
            or len(name) > 80
            or any(character in name for character in "[]|\r\n")
        ):
            continue
        if iso3 in countries:
            raise ValueError("V2.46.88 duplicate catalogue ISO3")
        countries[iso3] = {
            "iso3": iso3,
            "name": name,
            "region_id": region_id,
            "region_name": region_name,
        }
    if len(countries) < SELECTED_COUNT:
        raise ValueError("V2.46.88 country catalogue lacks capacity")
    metadata = {
        "response_sha256": hashlib.sha256(raw).hexdigest(),
        "reported_total": int(payload[0].get("total", 0) or 0),
        "eligible_country_count": len(countries),
    }
    return countries, metadata


def _value_text(value: object) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, _DecimalLexeme):
        return str(value)
    return None


def parse_indicator_snapshot(
    raw: bytes, *, indicator: str, year: str, source_url: str
) -> tuple[dict[str, dict[str, str]], dict[str, Any]]:
    if source_url != indicator_url(indicator, year):
        raise ValueError("V2.46.88 indicator URL drifted")
    payload = _decode(raw)
    if (
        not isinstance(payload, list)
        or len(payload) != 2
        or not isinstance(payload[0], Mapping)
        or payload[0].get("page") != 1
        or payload[0].get("pages") != 1
        or not isinstance(payload[1], list)
    ):
        raise ValueError("V2.46.88 indicator snapshot envelope drifted")
    values: dict[str, dict[str, str]] = {}
    null_count = 0
    for row in payload[1]:
        if not isinstance(row, Mapping):
            continue
        indicator_object = row.get("indicator")
        iso3 = str(row.get("countryiso3code", ""))
        if (
            not isinstance(indicator_object, Mapping)
            or indicator_object.get("id") != indicator
            or str(row.get("date", "")) != year
            or len(iso3) != 3
            or not iso3.isupper()
        ):
            continue
        value = _value_text(row.get("value"))
        if value is None:
            null_count += 1
            continue
        if iso3 in values:
            raise ValueError("V2.46.88 duplicate indicator ISO3")
        values[iso3] = {
            "indicator": indicator,
            "year": year,
            "value": value,
            "source_url": source_url,
            "response_sha256": hashlib.sha256(raw).hexdigest(),
        }
    metadata = {
        "indicator": indicator,
        "year": year,
        "source_url": source_url,
        "response_sha256": hashlib.sha256(raw).hexdigest(),
        "lastupdated": str(payload[0].get("lastupdated", "")),
        "reported_total": int(payload[0].get("total", 0) or 0),
        "non_null_country_count": len(values),
        "null_record_count": null_count,
    }
    return values, metadata


def select_records(
    countries: Mapping[str, Mapping[str, str]],
    snapshots: Sequence[Mapping[str, Mapping[str, str]]],
    *,
    selected_count: int = SELECTED_COUNT,
    region_cap: int = REGION_CAP,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if (
        isinstance(selected_count, bool)
        or selected_count <= 0
        or selected_count % TASK_SIZE
        or isinstance(region_cap, bool)
        or region_cap <= 0
        or len(snapshots) != len(TARGETS)
    ):
        raise ValueError("V2.46.88 selection envelope drifted")
    candidates: list[dict[str, Any]] = []
    for iso3, country in countries.items():
        if iso3 in EXCLUDED_ISO3 or any(iso3 not in snapshot for snapshot in snapshots):
            continue
        values = [dict(snapshot[iso3]) for snapshot in snapshots]
        candidates.append(
            {
                "rank": hashlib.sha256(f"v24688:{iso3}".encode()).hexdigest(),
                "iso3": iso3,
                "name": str(country["name"]),
                "region_id": str(country["region_id"]),
                "region_name": str(country["region_name"]),
                "values": values,
            }
        )
    candidates.sort(key=lambda item: (item["rank"], item["iso3"]))
    selected: list[dict[str, Any]] = []
    region_counts: Counter[str] = Counter()
    for item in candidates:
        if region_counts[item["region_id"]] >= region_cap:
            continue
        selected.append(item)
        region_counts[item["region_id"]] += 1
        if len(selected) == selected_count:
            break
    if len(selected) != selected_count:
        raise RuntimeError("V2.46.88 complete-value region-capped capacity is insufficient")

    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in selected:
        buckets[item["region_id"]].append(item)
    region_order = sorted(
        buckets,
        key=lambda region: hashlib.sha256(f"v24688-region:{region}".encode()).hexdigest(),
    )
    ordered: list[dict[str, Any]] = []
    while len(ordered) < selected_count:
        progressed = False
        for region in region_order:
            if buckets[region]:
                ordered.append(buckets[region].pop(0))
                progressed = True
        if not progressed:
            break
    groups = [
        ordered[index : index + TASK_SIZE]
        for index in range(0, selected_count, TASK_SIZE)
    ]
    if (
        len(ordered) != selected_count
        or len({item["iso3"] for item in ordered}) != selected_count
        or any(len(group) != TASK_SIZE for group in groups)
        or min(len({item["region_id"] for item in group}) for group in groups) < 3
    ):
        raise RuntimeError("V2.46.88 selected task grouping drifted")
    metrics = {
        "candidate_count": len(candidates),
        "candidate_region_count": len({item["region_id"] for item in candidates}),
        "selected_region_count": len(region_counts),
        "selected_region_max": max(region_counts.values(), default=0),
        "minimum_distinct_regions_per_task": min(
            len({item["region_id"] for item in group}) for group in groups
        ),
    }
    return ordered, metrics


def build_artifacts(
    selected: Sequence[Mapping[str, Any]],
    *,
    catalog_metadata: Mapping[str, Any],
    snapshot_metadata: Sequence[Mapping[str, Any]],
    metrics: Mapping[str, Any],
    created_at: int,
    git_head: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    groups = [
        [dict(item) for item in selected[index : index + TASK_SIZE]]
        for index in range(0, len(selected), TASK_SIZE)
    ]
    private = {
        "artifact_version": 1,
        "role": "v24688_worldbank_evaluator_only_population",
        "created_at_unix": int(created_at),
        "targets": [dict(item) for item in TARGETS],
        "groups": groups,
        "catalog": dict(catalog_metadata),
        "indicator_snapshots": [dict(item) for item in snapshot_metadata],
        "selection_rule": (
            "complete_two_target_values_fixture_and_prior_worldbank_exclusion_"
            "sha256_iso3_rank_region_cap8_region_round_robin_groups4"
        ),
        "forward_import_or_runtime_read_authorized": False,
        "gold_provenance_or_evaluator_read_before_prediction_freeze_authorized": False,
    }
    private["private_payload_sha256"] = payload_sha256(private)
    visible_vector = [
        {"name": item["name"], "iso3": item["iso3"]} for item in selected
    ]
    value_vector = [
        {
            "iso3": item["iso3"],
            "values": [
                {
                    "indicator": value["indicator"],
                    "year": value["year"],
                    "value": value["value"],
                    "response_sha256": value["response_sha256"],
                }
                for value in item["values"]
            ],
        }
        for item in selected
    ]
    public = {
        "artifact_version": 1,
        "role": "v24688_worldbank_population_design",
        "created_at_unix": int(created_at),
        "git_head": git_head,
        "parent_build_audit_sha256": _sha256(ROOT / PARENT),
        "authorization_audit_sha256": _sha256(ROOT / AUTHORIZATION),
        "catalog_response_sha256": catalog_metadata["response_sha256"],
        "indicator_snapshot_metadata": [dict(item) for item in snapshot_metadata],
        "excluded_iso3_count": len(EXCLUDED_ISO3),
        "excluded_iso3_sha256": payload_sha256(sorted(EXCLUDED_ISO3)),
        "selected_count": len(selected),
        "task_count": len(groups),
        "task_size": TASK_SIZE,
        **dict(metrics),
        "selected_visible_vector_sha256": payload_sha256(visible_vector),
        "selected_value_and_provenance_vector_sha256": payload_sha256(value_vector),
        "private_population_file_sha256": None,
        "network": {
            "worldbank_country_catalog_reads": 1,
            "worldbank_bulk_indicator_reads": len(TARGETS),
            "model_search_benchmark_or_evaluator_calls": 0,
        },
        "privacy": {
            "selected_country_name_iso3_value_or_gold_emitted": False,
            "private_vector_under_evaluation_directory": True,
            "forward_import_or_runtime_read_authorized": False,
        },
        "authorization": {
            "isolated_forward_contract_gold_provenance_and_evaluator_design": True,
            "external_protocol_design": True,
            "activation_or_launch": False,
            "dev64_or_exact220": False,
            "evaluator_access": False,
        },
    }
    return private, public


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.88 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = _read(ROOT / PARENT)
    return (
        value.get("role") == "v24687_worldbank_target_value_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("authorization", {}).get(
            "fresh_disjoint_worldbank_population_and_protocol_design"
        )
        is True
        and value.get("authorization", {}).get(
            "population_gold_or_provenance_publication"
        )
        is False
        and value.get("authorization", {}).get("preactivation_or_launch") is False
        and _sealed(value, "audit_payload_sha256")
    )


def _authorization_valid() -> bool:
    if not (ROOT / AUTHORIZATION).is_file() or (ROOT / AUTHORIZATION).is_symlink():
        return False
    value = _read(ROOT / AUTHORIZATION)
    return (
        value.get("role") == "v24689_worldbank_population_design_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("authorization")
        == {
            "one_population_design_publication": True,
            "forward_or_evaluator_surface_publication": False,
            "preactivation_or_launch": False,
            "dev64_or_exact220": False,
            "evaluator_access": False,
            "leaderboard_or_sota": False,
        }
        and _sealed(value, "audit_payload_sha256")
    )


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "deepwide-v24688-population-design/1"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.46.88 population design requires clean pushed HEAD")
    if not _parent_valid():
        raise RuntimeError("V2.46.88 parent build audit drifted")
    if not _authorization_valid():
        raise RuntimeError("V2.46.88 population publication is not authorized")
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (PRIVATE, OUTPUT)
    ):
        raise FileExistsError("V2.46.88 population design surface exists")

    catalog_raw = _fetch_bytes(COUNTRY_CATALOG_URL)
    countries, catalog_metadata = parse_country_catalog(catalog_raw)
    snapshots: list[dict[str, dict[str, str]]] = []
    snapshot_metadata: list[dict[str, Any]] = []
    for target in TARGETS:
        url = indicator_url(target["indicator"], target["year"])
        raw = _fetch_bytes(url)
        values, metadata = parse_indicator_snapshot(
            raw,
            indicator=target["indicator"],
            year=target["year"],
            source_url=url,
        )
        snapshots.append(values)
        snapshot_metadata.append(metadata)
    selected, metrics = select_records(countries, snapshots)
    created_at = int(time.time())
    private, public = build_artifacts(
        selected,
        catalog_metadata=catalog_metadata,
        snapshot_metadata=snapshot_metadata,
        metrics=metrics,
        created_at=created_at,
        git_head=_git("rev-parse", "HEAD"),
    )
    _publish(ROOT / PRIVATE, private)
    public["private_population_file_sha256"] = _sha256(ROOT / PRIVATE)
    public["design_sha256"] = payload_sha256(public)
    _publish(ROOT / OUTPUT, public)
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "private": str(PRIVATE),
                "selected_count": len(selected),
                "task_count": len(selected) // TASK_SIZE,
                "design_sha256": public["design_sha256"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
