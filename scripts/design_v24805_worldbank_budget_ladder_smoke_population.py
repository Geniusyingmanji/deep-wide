#!/usr/bin/env python3
"""Design a fresh 16-task World Bank budget-ladder smoke population.

Selection uses one public country catalogue and two public bulk indicator
snapshots.  Every historical World Bank ISO3 present in tracked evaluator-only
artifacts is excluded before ranking.  The task-stratum vector is frozen before
any model/search forward: ten complete groups, four missing groups, and two
mixed 2+2 groups.  This is a smoke population, not the preregistered
128/64/256 calibration/validation/confirmatory population.
"""

from __future__ import annotations

import dataclasses
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

from deepwide_agent.v24804_shared_prefix_budget_ladder import (  # noqa: E402
    AdaptivePolicy,
)
from scripts.audit_v24804_shared_prefix_budget_ladder import (  # noqa: E402
    payload_sha256,
)


DATE = "20260807"
AUTHORIZATION = Path(
    f"results/v24805_worldbank_budget_ladder_smoke_population_build_audit_v1_{DATE}.json"
)
PRIVATE = Path(
    f"evaluation/v24805_worldbank_budget_ladder_smoke_population_private_v1_{DATE}.json"
)
OUTPUT = Path(
    f"results/v24805_worldbank_budget_ladder_smoke_population_design_v1_{DATE}.json"
)
PARENT = Path(f"results/v24804_shared_prefix_budget_ladder_build_audit_v1_{DATE}.json")
HISTORICAL_PRIVATE = (
    Path("evaluation/v24690_worldbank_population_private_v1_20260806.json"),
    Path("evaluation/v24694_worldbank_gold_provenance_v1.json"),
    Path("evaluation/v24729_worldbank_population_private_v1_20260806.json"),
    Path("evaluation/v24733_dual_namespace_gold_provenance_v1.json"),
)
COUNTRY_CATALOG_URL = "https://api.worldbank.org/v2/country?format=json&per_page=400"
TARGETS = (
    {
        "label": "Male unemployment rate (%)",
        "indicator": "SL.UEM.TOTL.MA.ZS",
        "year": "2023",
    },
    {
        "label": "Female unemployment rate (%)",
        "indicator": "SL.UEM.TOTL.FE.ZS",
        "year": "2023",
    },
)
TASK_SIZE = 4
STRATUM_VECTOR = (
    *("complete" for _ in range(10)),
    *("missing" for _ in range(4)),
    "mixed",
    "mixed",
)
TASK_COUNT = len(STRATUM_VECTOR)
SELECTED_COUNT = TASK_COUNT * TASK_SIZE
COMPLETE_SELECTED = 44
MISSING_SELECTED = 20
REGION_CAP = 16
POLICY = AdaptivePolicy(
    calibration_ref_sha256=hashlib.sha256(
        b"v24805-smoke-policy-not-main-calibration"
    ).hexdigest(),
    calibration_complete=True,
    per_lookup_cost=0.04,
)


class _DecimalLexeme(str):
    pass


def _parse_decimal(value: str) -> _DecimalLexeme:
    if not Decimal(value).is_finite():
        raise ValueError("V2.48.05 non-finite decimal")
    return _DecimalLexeme(value)


def _reject_constant(value: str) -> None:
    raise ValueError(f"V2.48.05 non-standard JSON number: {value}")


def _decode(raw: bytes) -> Any:
    return json.loads(
        raw.decode("utf-8"),
        parse_float=_parse_decimal,
        parse_constant=_reject_constant,
    )


def indicator_url(indicator: str, year: str) -> str:
    query = urlencode((("date", year), ("format", "json"), ("per_page", "400")))
    return (
        "https://api.worldbank.org/v2/country/all/indicator/"
        f"{indicator}?{query}"
    )


def parse_country_catalog(
    raw: bytes,
) -> tuple[dict[str, dict[str, str]], dict[str, Any]]:
    payload = _decode(raw)
    if (
        not isinstance(payload, list) or len(payload) != 2
        or not isinstance(payload[0], Mapping) or payload[0].get("page") != 1
        or payload[0].get("pages") != 1 or not isinstance(payload[1], list)
    ):
        raise ValueError("V2.48.05 country catalogue envelope drifted")
    countries: dict[str, dict[str, str]] = {}
    for row in payload[1]:
        if not isinstance(row, Mapping):
            continue
        iso3 = str(row.get("id", ""))
        name = str(row.get("name", "")).strip()
        region = row.get("region")
        region_id = str(region.get("id", "")) if isinstance(region, Mapping) else ""
        region_name = (
            str(region.get("value", "")).strip() if isinstance(region, Mapping) else ""
        )
        if (
            len(iso3) != 3 or not iso3.isupper() or not iso3.isalpha()
            or region_id in {"", "NA"} or not region_name or not name
            or len(name) > 80 or any(character in name for character in "[]|\r\n")
        ):
            continue
        if iso3 in countries:
            raise ValueError("V2.48.05 duplicate catalogue ISO3")
        countries[iso3] = {
            "iso3": iso3, "name": name, "region_id": region_id,
            "region_name": region_name,
        }
    if len(countries) < SELECTED_COUNT:
        raise ValueError("V2.48.05 country catalogue lacks capacity")
    return countries, {
        "response_sha256": hashlib.sha256(raw).hexdigest(),
        "reported_total": int(payload[0].get("total", 0) or 0),
        "eligible_country_count": len(countries),
    }


def _value_text(value: object) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, _DecimalLexeme):
        return str(value)
    return None


def parse_indicator_snapshot(
    raw: bytes, *, indicator: str, year: str, source_url: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    if source_url != indicator_url(indicator, year):
        raise ValueError("V2.48.05 indicator URL drifted")
    payload = _decode(raw)
    if (
        not isinstance(payload, list) or len(payload) != 2
        or not isinstance(payload[0], Mapping) or payload[0].get("page") != 1
        or payload[0].get("pages") != 1 or not isinstance(payload[1], list)
    ):
        raise ValueError("V2.48.05 indicator snapshot envelope drifted")
    records: dict[str, dict[str, Any]] = {}
    for row in payload[1]:
        if not isinstance(row, Mapping):
            continue
        indicator_object = row.get("indicator")
        iso3 = str(row.get("countryiso3code", ""))
        if (
            not isinstance(indicator_object, Mapping)
            or indicator_object.get("id") != indicator
            or str(row.get("date", "")) != year
            or len(iso3) != 3 or not iso3.isupper() or iso3 in records
        ):
            continue
        records[iso3] = {
            "indicator": indicator,
            "year": year,
            "value": _value_text(row.get("value")),
            "source_url": source_url,
            "response_sha256": hashlib.sha256(raw).hexdigest(),
        }
    return records, {
        "indicator": indicator,
        "year": year,
        "source_url": source_url,
        "response_sha256": hashlib.sha256(raw).hexdigest(),
        "lastupdated": str(payload[0].get("lastupdated", "")),
        "reported_total": int(payload[0].get("total", 0) or 0),
        "non_null_country_count": sum(
            record["value"] is not None for record in records.values()
        ),
        "null_country_count": sum(
            record["value"] is None for record in records.values()
        ),
    }


def _iso3_values(value: object) -> set[str]:
    output: set[str] = set()
    if isinstance(value, Mapping):
        iso3 = value.get("iso3")
        if isinstance(iso3, str) and len(iso3) == 3 and iso3.isupper():
            output.add(iso3)
        for nested in value.values():
            output.update(_iso3_values(nested))
    elif isinstance(value, list):
        for nested in value:
            output.update(_iso3_values(nested))
    return output


def historical_iso3(root: Path = ROOT) -> tuple[set[str], dict[str, str]]:
    output: set[str] = set()
    manifest: dict[str, str] = {}
    for relative in HISTORICAL_PRIVATE:
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"V2.48.05 historical artifact absent: {relative}")
        raw = path.read_bytes()
        value = json.loads(raw)
        output.update(_iso3_values(value))
        manifest[str(relative)] = hashlib.sha256(raw).hexdigest()
    if len(output) != 96:
        raise RuntimeError("V2.48.05 historical ISO3 exclusion drifted")
    return output, manifest


def _rank(stratum: str, iso3: str) -> str:
    return hashlib.sha256(f"v24805:{stratum}:{iso3}".encode()).hexdigest()


def _select(
    candidates: Sequence[Mapping[str, Any]], *, count: int, stratum: str,
) -> list[dict[str, Any]]:
    ordered = sorted(
        (dict(item) for item in candidates),
        key=lambda item: (_rank(stratum, str(item["iso3"])), str(item["iso3"])),
    )
    selected: list[dict[str, Any]] = []
    regions: Counter[str] = Counter()
    for item in ordered:
        region = str(item["region_id"])
        if regions[region] >= REGION_CAP:
            continue
        selected.append(item)
        regions[region] += 1
        if len(selected) == count:
            break
    if len(selected) != count:
        raise RuntimeError(f"V2.48.05 {stratum} capacity is insufficient")
    return selected


def select_population(
    countries: Mapping[str, Mapping[str, str]],
    snapshots: Sequence[Mapping[str, Mapping[str, Any]]],
    excluded: set[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if len(snapshots) != 2:
        raise ValueError("V2.48.05 requires two frozen snapshots")
    complete: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for iso3, country in countries.items():
        if iso3 in excluded or any(iso3 not in snapshot for snapshot in snapshots):
            continue
        records = [dict(snapshot[iso3]) for snapshot in snapshots]
        flags = tuple(record["value"] is not None for record in records)
        item = {**dict(country), "records": records}
        if flags == (True, True):
            complete.append(item)
        elif flags == (False, False):
            missing.append(item)
    selected_complete = _select(
        complete, count=COMPLETE_SELECTED, stratum="complete"
    )
    selected_missing = _select(
        missing, count=MISSING_SELECTED, stratum="missing"
    )
    complete_groups = [
        selected_complete[index : index + TASK_SIZE]
        for index in range(0, 40, TASK_SIZE)
    ]
    missing_groups = [
        selected_missing[index : index + TASK_SIZE]
        for index in range(0, 16, TASK_SIZE)
    ]
    mixed_complete = selected_complete[40:44]
    mixed_missing = selected_missing[16:20]
    mixed_groups = [
        [*mixed_complete[0:2], *mixed_missing[0:2]],
        [*mixed_complete[2:4], *mixed_missing[2:4]],
    ]
    groups = [*complete_groups, *missing_groups, *mixed_groups]
    if (
        len(groups) != TASK_COUNT or any(len(group) != TASK_SIZE for group in groups)
        or len({item["iso3"] for group in groups for item in group})
        != SELECTED_COUNT
        or tuple(
            "complete" if all(item["records"][0]["value"] is not None for item in group)
            else "missing" if all(item["records"][0]["value"] is None for item in group)
            else "mixed"
            for group in groups
        ) != STRATUM_VECTOR
    ):
        raise RuntimeError("V2.48.05 task-stratum grouping drifted")
    return [item for group in groups for item in group], {
        "complete_candidate_count": len(complete),
        "missing_candidate_count": len(missing),
        "selected_complete_country_count": 44,
        "selected_missing_country_count": 20,
        "selected_country_count": SELECTED_COUNT,
        "task_count": TASK_COUNT,
        "task_size": TASK_SIZE,
        "task_stratum_counts": dict(Counter(STRATUM_VECTOR)),
        "region_count": len(
            {item["region_id"] for group in groups for item in group}
        ),
    }


def build_artifacts(
    selected: Sequence[Mapping[str, Any]], *,
    catalog_metadata: Mapping[str, Any],
    snapshot_metadata: Sequence[Mapping[str, Any]],
    historical_manifest: Mapping[str, str],
    metrics: Mapping[str, Any], created_at: int, git_head: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    groups = [
        [dict(item) for item in selected[index : index + TASK_SIZE]]
        for index in range(0, len(selected), TASK_SIZE)
    ]
    private = {
        "artifact_version": 1,
        "role": "v24805_worldbank_budget_ladder_smoke_evaluator_only_population",
        "created_at_unix": int(created_at),
        "targets": [dict(target) for target in TARGETS],
        "adaptive_policy": dataclasses.asdict(POLICY),
        "task_stratum_vector": list(STRATUM_VECTOR),
        "groups": groups,
        "catalog": dict(catalog_metadata),
        "indicator_snapshots": [dict(item) for item in snapshot_metadata],
        "historical_exclusion_manifest": dict(historical_manifest),
        "selection_rule": (
            "all_tracked_historical_worldbank_iso3_excluded_then_"
            "v24805_hash_rank_region_cap16_complete10_missing4_mixed2"
        ),
        "forward_import_or_runtime_read_authorized": False,
        "gold_provenance_or_evaluator_read_before_prediction_freeze_authorized": False,
        "smoke_only_not_main_calibration_lock_validation_or_confirmatory": True,
    }
    private["private_payload_sha256"] = payload_sha256(private)
    visible = [
        {"name": item["name"], "iso3": item["iso3"]} for item in selected
    ]
    value_vector = [
        {
            "iso3": item["iso3"],
            "records": [
                {
                    "indicator": record["indicator"],
                    "year": record["year"],
                    "value": record["value"],
                    "response_sha256": record["response_sha256"],
                }
                for record in item["records"]
            ],
        }
        for item in selected
    ]
    public = {
        "artifact_version": 1,
        "role": "v24805_worldbank_budget_ladder_smoke_population_design",
        "created_at_unix": int(created_at),
        "git_head": git_head,
        "parent_build_audit_sha256": _sha256(ROOT / PARENT),
        "authorization_audit_sha256": _sha256(ROOT / AUTHORIZATION),
        "catalog_response_sha256": catalog_metadata["response_sha256"],
        "indicator_snapshot_metadata": [dict(item) for item in snapshot_metadata],
        "historical_exclusion_manifest_sha256": payload_sha256(
            historical_manifest
        ),
        "historical_excluded_iso3_count": 96,
        **dict(metrics),
        "task_stratum_vector_sha256": payload_sha256(list(STRATUM_VECTOR)),
        "selected_visible_vector_sha256": payload_sha256(visible),
        "selected_value_and_provenance_vector_sha256": payload_sha256(value_vector),
        "adaptive_policy_sha256": payload_sha256(dataclasses.asdict(POLICY)),
        "private_population_file_sha256": None,
        "network": {
            "worldbank_country_catalog_reads": 1,
            "worldbank_bulk_indicator_reads": 2,
            "model_search_benchmark_or_evaluator_calls": 0,
        },
        "privacy": {
            "selected_country_name_iso3_value_or_gold_emitted": False,
            "private_vector_under_evaluation_directory": True,
            "forward_import_or_runtime_read_authorized": False,
        },
        "scope": {
            "smoke_task_count": TASK_COUNT,
            "main_calibration_task_count": 128,
            "lock_validation_task_count": 64,
            "confirmatory_task_count": 256,
            "this_population_satisfies_main_sample_size": False,
        },
        "authorization": {
            "isolated_smoke_forward_contract_and_evaluator_design": True,
            "smoke_protocol_design": True,
            "smoke_launch": False,
            "main_calibration_or_confirmatory_launch": False,
            "public_dev64_or_exact220": False,
            "evaluator_access": False,
        },
    }
    return private, public


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20,
    ).stdout.strip()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.05 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _authorized() -> bool:
    path = ROOT / AUTHORIZATION
    if path.is_symlink() or not path.is_file():
        return False
    value = _read(path)
    return (
        value.get("role")
        == "v24805_worldbank_budget_ladder_smoke_population_build_audit"
        and value.get("audit_valid") is True and value.get("findings") == []
        and value.get("authorization", {}).get("one_smoke_population_publication")
        is True
        and value.get("authorization", {}).get("smoke_launch") is False
        and _sealed(value, "audit_payload_sha256")
    )


def _fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "deepwide-v24805/1"})
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
        raise RuntimeError("V2.48.05 population publication requires clean pushed HEAD")
    if not _authorized():
        raise RuntimeError("V2.48.05 population publication is not authorized")
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (PRIVATE, OUTPUT)
    ):
        raise FileExistsError("V2.48.05 population surface exists")
    excluded, historical_manifest = historical_iso3()
    catalog_raw = _fetch_bytes(COUNTRY_CATALOG_URL)
    countries, catalog_metadata = parse_country_catalog(catalog_raw)
    snapshots: list[dict[str, dict[str, Any]]] = []
    snapshot_metadata: list[dict[str, Any]] = []
    for target in TARGETS:
        url = indicator_url(target["indicator"], target["year"])
        raw = _fetch_bytes(url)
        records, metadata = parse_indicator_snapshot(
            raw,
            indicator=target["indicator"],
            year=target["year"],
            source_url=url,
        )
        snapshots.append(records)
        snapshot_metadata.append(metadata)
    selected, metrics = select_population(countries, snapshots, excluded)
    private, public = build_artifacts(
        selected,
        catalog_metadata=catalog_metadata,
        snapshot_metadata=snapshot_metadata,
        historical_manifest=historical_manifest,
        metrics=metrics,
        created_at=int(time.time()),
        git_head=_git("rev-parse", "HEAD"),
    )
    _publish(ROOT / PRIVATE, private)
    public["private_population_file_sha256"] = _sha256(ROOT / PRIVATE)
    public["design_payload_sha256"] = payload_sha256(public)
    _publish(ROOT / OUTPUT, public)
    print(json.dumps({
        "private": str(PRIVATE), "output": str(OUTPUT),
        "selected_count": metrics["selected_country_count"],
        "task_count": metrics["task_count"],
        "task_stratum_counts": metrics["task_stratum_counts"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
