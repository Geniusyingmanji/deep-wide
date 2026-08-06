#!/usr/bin/env python3
"""Design two fresh populations for a dual-namespace reachability gate.

This design-time program selects one ROR population and one World Bank
population without reading DeepWideBench, an evaluator, or prior task
outcomes.  ROR records come from an immutable repository snapshot after all
previously consumed entity surfaces are excluded.  World Bank countries are
selected by a frozen hash rank from the two indicators fixed before the
V2.47.26 transport outcome.  Private records are evaluator-only; the public
artifact contains hashes and counts only and grants no launch authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import concurrent.futures
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24724_fresh_indicator_transport as wb_runtime  # noqa: E402
from deepwide_agent.v24671_ror_external_contract import (  # noqa: E402
    ENTITY_GROUPS as V24671_ROR_GROUPS,
)
from scripts import design_v24645_ror_population as ror_base  # noqa: E402
from scripts import design_v24670_ror_population as ror_prior  # noqa: E402
from scripts import design_v24688_worldbank_population as wb_base  # noqa: E402
from deepwide_agent.v24694_worldbank_external_contract import (  # noqa: E402
    COUNTRY_GROUPS as V24694_WB_GROUPS,
)


DATE = "20260806"
OUTPUT = Path(f"results/v24727_dual_namespace_population_design_v1_{DATE}.json")
PRIVATE_ROR = Path(f"evaluation/v24727_ror_population_private_v1_{DATE}.json")
PRIVATE_WB = Path(f"evaluation/v24727_worldbank_population_private_v1_{DATE}.json")
PARENT_DECISION = Path(f"results/v24726_fresh_bulk_transport_decision_v1_{DATE}.json")
PARENT_AUDIT = Path(
    f"results/v24726_fresh_bulk_transport_postresult_audit_v1_{DATE}.json"
)
PARENT_FRESH_DESIGN = Path(
    f"results/v24723_fresh_indicator_population_design_v1_{DATE}.json"
)

ROR_COMMIT = ror_prior.COMMIT
ROR_VERSION = ror_prior.VERSION
ROR_TREE_SHA1 = ror_prior.DIRECTORY_TREE_SHA1
ROR_TREE_SHA256 = "0fd37f3ad5b588c71d3509ce94a5316025d8b12d03455b208c6d966b25981107"
ROR_TREE_URL = (
    "https://api.github.com/repos/ror-community/ror-records/git/trees/"
    + ROR_TREE_SHA1
)
ROR_RAW_PREFIX = (
    "https://raw.githubusercontent.com/ror-community/ror-records/"
    f"{ROR_COMMIT}/{ROR_VERSION}/"
)
ROR_SELECTED_COUNT = 48
ROR_TASK_SIZE = 4
ROR_COUNTRY_CAP = 4
MAX_ROR_TREE_BYTES = 4_000_000
MAX_ROR_RECORD_BYTES = 2_000_000
ROR_FETCH_WORKERS = 24

WB_CATALOG_URL = wb_base.COUNTRY_CATALOG_URL
WB_TARGETS = (
    {
        "label": "Individuals using the Internet (% of population)",
        "indicator": "IT.NET.USER.ZS",
        "year": "2022",
    },
    {
        "label": "Life expectancy at birth, total (years)",
        "indicator": "SP.DYN.LE00.IN",
        "year": "2022",
    },
)
WB_SELECTED_COUNT = 48
WB_TASK_SIZE = 4
WB_REGION_CAP = 9
EXPECTED_PRIOR_ROR_COUNT = 4_624
EXPECTED_PRIOR_WB_COUNT = len(wb_base.EXCLUDED_ISO3) + sum(
    len(group) for group in V24694_WB_GROUPS
)
MAX_WB_RESPONSE_BYTES = 5_000_000
USER_AGENT = "deepwide-v24727-population-design/1"


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.47.27 expected ordinary file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.27 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    decision = _read(ROOT / PARENT_DECISION)
    audit = _read(ROOT / PARENT_AUDIT)
    fresh = _read(ROOT / PARENT_FRESH_DESIGN)
    selected = [
        item.get("target_key")
        for item in fresh.get("selection", {}).get("selected_targets", [])
        if isinstance(item, Mapping)
    ]
    return (
        decision.get("role") == "v24726_fresh_bulk_transport_decision"
        and decision.get("status") == "transport_go"
        and decision.get("authorization", {}).get(
            "generic_reachability_candidate_design"
        )
        is True
        and decision.get("authorization", {}).get("benchmark_dev64_or_exact220")
        is False
        and decision.get("authorization", {}).get("evaluator") is False
        and decision.get("authorization", {}).get(
            "additional_transport_retry_or_rerun"
        )
        is False
        and _sealed(decision, "decision_payload_sha256")
        and audit.get("role")
        == "v24726_fresh_bulk_transport_postresult_audit"
        and audit.get("audit_valid") is True
        and audit.get("findings") == []
        and audit.get("decision_status") == "transport_go"
        and audit.get("authorization", {}).get("benchmark_dev64_or_exact220")
        is False
        and _sealed(audit, "audit_payload_sha256")
        and fresh.get("role") == "v24723_fresh_indicator_population_design"
        and selected
        == [f"{item['indicator']}@{item['year']}" for item in WB_TARGETS]
        and fresh.get("selection", {}).get(
            "network_or_transport_outcome_used_for_selection"
        )
        is False
        and _sealed(fresh, "design_payload_sha256")
    )


def _fetch(url: str, *, limit: int) -> bytes:
    if not url.startswith("https://") or isinstance(limit, bool) or limit <= 0:
        raise ValueError("V2.47.27 fetch input drifted")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=35) as response:
        raw = response.read(limit + 1)
    if not raw or len(raw) > limit:
        raise RuntimeError("V2.47.27 bounded response drifted")
    return raw


def prior_ror_entities() -> tuple[set[str], set[str]]:
    visible, _canonical = ror_prior.historical_entities()
    latest = {entity for group in V24671_ROR_GROUPS for entity in group}
    if len(latest) != ROR_SELECTED_COUNT:
        raise RuntimeError("V2.47.27 prior ROR vector drifted")
    visible.update(latest)
    normalizer = ror_base.history.population._canonical_entity
    canonical = {normalizer(entity) for entity in visible}
    if (
        len(visible) != EXPECTED_PRIOR_ROR_COUNT
        or len(canonical) != EXPECTED_PRIOR_ROR_COUNT
        or "" in canonical
    ):
        raise RuntimeError("V2.47.27 ROR history drifted")
    return visible, canonical


def _ror_candidate(
    *,
    path: str,
    blob_sha1: str,
    raw: bytes,
    value: Mapping[str, Any],
    historical_canonical: set[str],
    canonical: Callable[[str], str],
) -> dict[str, str] | None:
    record_id = path[:-5] if path.endswith(".json") else ""
    names = value.get("names")
    locations = value.get("locations") or []
    displays = [
        str(item.get("value", "")).strip()
        for item in names
        if isinstance(item, Mapping)
        and "ror_display" in item.get("types", [])
        and str(item.get("value", "")).strip()
    ] if isinstance(names, list) else []
    country = (
        (locations[0].get("geonames_details") or {}).get("country_code")
        if locations and isinstance(locations[0], Mapping)
        else None
    )
    label = displays[0] if len(displays) == 1 else ""
    folded = canonical(label) if label else ""
    if (
        not record_id
        or value.get("status") != "active"
        or value.get("id") != f"https://ror.org/{record_id}"
        or not folded
        or folded in historical_canonical
        or not isinstance(country, str)
        or len(country) != 2
        or not country.isalpha()
        or any(character in label for character in "()|\r\n\"\\")
        or len(label) > 160
    ):
        return None
    computed_blob = hashlib.sha1(
        f"blob {len(raw)}\0".encode("ascii") + raw,
        usedforsecurity=False,
    ).hexdigest()
    if computed_blob != blob_sha1:
        raise RuntimeError("V2.47.27 immutable ROR blob drifted")
    return {
        "rank": hashlib.sha256(
            f"{ROR_COMMIT}:v24727:{record_id}".encode()
        ).hexdigest(),
        "label": label,
        "canonical": folded,
        "record_id": record_id,
        "git_blob_sha1": blob_sha1,
        "country": country.upper(),
        "record_bytes_sha256": hashlib.sha256(raw).hexdigest(),
    }


def select_ror_records(
    records: Sequence[tuple[str, str, bytes, Mapping[str, Any]]],
    *,
    historical_canonical: set[str],
    canonical: Callable[[str], str],
    selected_count: int = ROR_SELECTED_COUNT,
    country_cap: int = ROR_COUNTRY_CAP,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    if (
        isinstance(selected_count, bool)
        or selected_count <= 0
        or selected_count % ROR_TASK_SIZE
        or isinstance(country_cap, bool)
        or country_cap <= 0
    ):
        raise ValueError("V2.47.27 ROR selection envelope drifted")
    eligible = [
        item
        for path, blob, raw, value in records
        if (
            item := _ror_candidate(
                path=path,
                blob_sha1=blob,
                raw=raw,
                value=value,
                historical_canonical=historical_canonical,
                canonical=canonical,
            )
        )
        is not None
    ]
    counts = Counter(item["canonical"] for item in eligible)
    candidates = [item for item in eligible if counts[item["canonical"]] == 1]
    candidates.sort(key=lambda item: (item["rank"], item["record_id"]))
    selected: list[dict[str, str]] = []
    countries: Counter[str] = Counter()
    for item in candidates:
        if countries[item["country"]] >= country_cap:
            continue
        selected.append(item)
        countries[item["country"]] += 1
        if len(selected) == selected_count:
            break
    if len(selected) != selected_count:
        raise RuntimeError("V2.47.27 ROR population lacks capacity")
    quarter = selected_count // ROR_TASK_SIZE
    ordered = [
        item
        for group in zip(
            selected[:quarter],
            selected[quarter : 2 * quarter],
            selected[2 * quarter : 3 * quarter],
            selected[3 * quarter :],
            strict=True,
        )
        for item in group
    ]
    if (
        len({item["label"] for item in ordered}) != selected_count
        or len({item["canonical"] for item in ordered}) != selected_count
        or any(item["canonical"] in historical_canonical for item in ordered)
    ):
        raise RuntimeError("V2.47.27 selected ROR identity drifted")
    return ordered, {
        "eligible_record_count": len(eligible),
        "candidate_count": len(candidates),
        "candidate_country_count": len({item["country"] for item in candidates}),
        "selected_country_count": len(countries),
        "selected_country_max": max(countries.values(), default=0),
    }


def parse_ror_tree(tree_raw: bytes) -> list[tuple[str, str]]:
    if hashlib.sha256(tree_raw).hexdigest() != ROR_TREE_SHA256:
        raise RuntimeError("V2.47.27 ROR tree bytes drifted")
    tree = json.loads(tree_raw)
    entries = [
        item
        for item in tree.get("tree", [])
        if isinstance(item, Mapping)
        and item.get("type") == "blob"
        and str(item.get("path", "")).endswith(".json")
    ] if isinstance(tree, Mapping) else []
    if (
        tree.get("truncated") is not False
        or len(entries) != 3_482
        or len({str(item["path"]) for item in entries}) != len(entries)
    ):
        raise RuntimeError("V2.47.27 ROR tree envelope drifted")
    output = []
    for entry in entries:
        path = str(entry["path"])
        blob = str(entry.get("sha", ""))
        if re.fullmatch(r"[0-9a-z]{9}\.json", path) is None or re.fullmatch(
            r"[0-9a-f]{40}", blob
        ) is None:
            raise RuntimeError("V2.47.27 ROR tree member drifted")
        output.append((path, blob))
    return output


def validate_ror_blob(
    path: str, blob_sha1: str, raw: bytes
) -> tuple[str, str, bytes, Mapping[str, Any]]:
    if (
        re.fullmatch(r"[0-9a-z]{9}\.json", path) is None
        or re.fullmatch(r"[0-9a-f]{40}", blob_sha1) is None
        or not isinstance(raw, bytes)
        or not 0 < len(raw) <= MAX_ROR_RECORD_BYTES
    ):
        raise RuntimeError("V2.47.27 ROR blob envelope drifted")
    computed_blob = hashlib.sha1(
        f"blob {len(raw)}\0".encode("ascii") + raw,
        usedforsecurity=False,
    ).hexdigest()
    if computed_blob != blob_sha1:
        raise RuntimeError("V2.47.27 ROR blob content drifted")
    value = json.loads(raw)
    if not isinstance(value, Mapping):
        raise RuntimeError("V2.47.27 ROR record drifted")
    return path, blob_sha1, raw, value


def fetch_ror_records(
    entries: Sequence[tuple[str, str]],
) -> list[tuple[str, str, bytes, Mapping[str, Any]]]:
    if len(entries) != 3_482 or len({path for path, _blob in entries}) != len(entries):
        raise RuntimeError("V2.47.27 ROR fetch vector drifted")

    def fetch_one(entry: tuple[str, str]):
        path, blob = entry
        raw = _fetch(ROR_RAW_PREFIX + path, limit=MAX_ROR_RECORD_BYTES)
        return validate_ror_blob(path, blob, raw)

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=ROR_FETCH_WORKERS
    ) as executor:
        return list(executor.map(fetch_one, entries))


def prior_worldbank_iso3() -> set[str]:
    previous = set(wb_base.EXCLUDED_ISO3)
    previous.update(iso3 for group in V24694_WB_GROUPS for _name, iso3 in group)
    if len(previous) != EXPECTED_PRIOR_WB_COUNT:
        raise RuntimeError("V2.47.27 prior World Bank population drifted")
    return previous


def select_worldbank_records(
    countries: Mapping[str, Mapping[str, str]],
    snapshots: Sequence[Mapping[str, Any]],
    *,
    excluded: set[str],
    selected_count: int = WB_SELECTED_COUNT,
    region_cap: int = WB_REGION_CAP,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if (
        len(snapshots) != len(WB_TARGETS)
        or isinstance(selected_count, bool)
        or selected_count <= 0
        or selected_count % WB_TASK_SIZE
        or isinstance(region_cap, bool)
        or region_cap <= 0
    ):
        raise ValueError("V2.47.27 World Bank selection envelope drifted")
    candidates = []
    for iso3, country in countries.items():
        if iso3 in excluded or any(iso3 not in snapshot for snapshot in snapshots):
            continue
        values = [snapshot[iso3] for snapshot in snapshots]
        if any(value is None for value in values):
            continue
        candidates.append(
            {
                "rank": hashlib.sha256(f"v24727-worldbank:{iso3}".encode()).hexdigest(),
                "iso3": iso3,
                "name": str(country["name"]),
                "region_id": str(country["region_id"]),
                "region_name": str(country["region_name"]),
                "values": [str(value) for value in values],
            }
        )
    candidates.sort(key=lambda item: (item["rank"], item["iso3"]))
    selected = []
    region_counts: Counter[str] = Counter()
    for item in candidates:
        if region_counts[item["region_id"]] >= region_cap:
            continue
        selected.append(item)
        region_counts[item["region_id"]] += 1
        if len(selected) == selected_count:
            break
    if len(selected) != selected_count:
        raise RuntimeError("V2.47.27 World Bank population lacks capacity")
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in selected:
        buckets[item["region_id"]].append(item)
    region_order = sorted(
        buckets,
        key=lambda region: hashlib.sha256(
            f"v24727-worldbank-region:{region}".encode()
        ).hexdigest(),
    )
    ordered = []
    while len(ordered) < selected_count:
        progressed = False
        for region in region_order:
            if buckets[region]:
                ordered.append(buckets[region].pop(0))
                progressed = True
        if not progressed:
            break
    groups = [
        ordered[index : index + WB_TASK_SIZE]
        for index in range(0, selected_count, WB_TASK_SIZE)
    ]
    minimum_regions = min(len({item["region_id"] for item in group}) for group in groups)
    if (
        len(ordered) != selected_count
        or len({item["iso3"] for item in ordered}) != selected_count
        or any(len(group) != WB_TASK_SIZE for group in groups)
        or minimum_regions < 3
    ):
        raise RuntimeError("V2.47.27 World Bank grouping drifted")
    return ordered, {
        "candidate_count": len(candidates),
        "candidate_region_count": len({item["region_id"] for item in candidates}),
        "selected_region_count": len(region_counts),
        "selected_region_max": max(region_counts.values(), default=0),
        "minimum_distinct_regions_per_task": minimum_regions,
    }


def _canonical_decimal(value: Any) -> str:
    normalized = value.normalize()
    return "0" if normalized == 0 else format(normalized, "f")


def build_artifacts(
    *,
    ror_records: Sequence[Mapping[str, Any]],
    ror_metrics: Mapping[str, int],
    wb_records: Sequence[Mapping[str, Any]],
    wb_metrics: Mapping[str, int],
    ror_tree_response_sha256: str,
    ror_record_vector_sha256: str,
    wb_catalog_response_sha256: str,
    wb_snapshot_metadata: Sequence[Mapping[str, Any]],
    now: int,
    git_head: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if len(ror_records) != ROR_SELECTED_COUNT or len(wb_records) != WB_SELECTED_COUNT:
        raise ValueError("V2.47.27 selected population count drifted")
    ror_groups = [
        [dict(item) for item in ror_records[index : index + ROR_TASK_SIZE]]
        for index in range(0, len(ror_records), ROR_TASK_SIZE)
    ]
    wb_groups = [
        [dict(item) for item in wb_records[index : index + WB_TASK_SIZE]]
        for index in range(0, len(wb_records), WB_TASK_SIZE)
    ]
    private_ror = {
        "artifact_version": 1,
        "role": "v24727_ror_evaluator_only_population",
        "created_at_unix": int(now),
        "commit": ROR_COMMIT,
        "version": ROR_VERSION,
        "directory_tree_sha1": ROR_TREE_SHA1,
        "selection_rule": "full_immutable_tree_prior_4624_entity_disjoint_v24727_sha256_rank_country_cap4_quartile_interleaved",
        "groups": ror_groups,
        "forward_import_or_runtime_read_authorized": False,
        "gold_provenance_or_evaluator_read_before_prediction_freeze_authorized": False,
    }
    private_ror["private_payload_sha256"] = payload_sha256(private_ror)
    private_wb = {
        "artifact_version": 1,
        "role": "v24727_worldbank_evaluator_only_population",
        "created_at_unix": int(now),
        "targets": [dict(item) for item in WB_TARGETS],
        "selection_rule": "complete_two_fresh_indicator_values_prior_external_iso3_exclusion_v24727_sha256_rank_region_cap9_round_robin_groups4",
        "groups": wb_groups,
        "forward_import_or_runtime_read_authorized": False,
        "gold_provenance_or_evaluator_read_before_prediction_freeze_authorized": False,
    }
    private_wb["private_payload_sha256"] = payload_sha256(private_wb)
    ror_visible = [[item["label"] for item in group] for group in ror_groups]
    ror_gold = [
        [
            {
                "record_id": item["record_id"],
                "country": item["country"],
                "record_bytes_sha256": item["record_bytes_sha256"],
            }
            for item in group
        ]
        for group in ror_groups
    ]
    wb_visible = [
        [{"name": item["name"], "iso3": item["iso3"]} for item in group]
        for group in wb_groups
    ]
    wb_gold = [
        [{"iso3": item["iso3"], "values": item["values"]} for item in group]
        for group in wb_groups
    ]
    public = {
        "artifact_version": 1,
        "role": "v24727_dual_namespace_population_design",
        "created_at_unix": int(now),
        "git_head": git_head,
        "parents": {
            "v24723_fresh_design_sha256": sha256(ROOT / PARENT_FRESH_DESIGN),
            "v24726_decision_sha256": sha256(ROOT / PARENT_DECISION),
            "v24726_postresult_audit_sha256": sha256(ROOT / PARENT_AUDIT),
        },
        "selection_timing": {
            "ror_and_worldbank_selection_code_frozen_before_v24727_outcome": True,
            "prior_task_quality_or_transport_outcome_used_to_rank_members": False,
            "deepwidebench_or_evaluator_content_used": False,
        },
        "clusters": {
            "ror": {
                "namespace": "ror_v2",
                "source_commit": ROR_COMMIT,
                "source_tree_sha1": ROR_TREE_SHA1,
                "tree_response_sha256": ror_tree_response_sha256,
                "record_vector_sha256": ror_record_vector_sha256,
                "historical_entity_count": EXPECTED_PRIOR_ROR_COUNT,
                "selected_entity_count": ROR_SELECTED_COUNT,
                "task_count": ROR_SELECTED_COUNT // ROR_TASK_SIZE,
                "entities_per_task": ROR_TASK_SIZE,
                **dict(ror_metrics),
                "visible_vector_sha256": payload_sha256(ror_visible),
                "gold_and_provenance_vector_sha256": payload_sha256(ror_gold),
                "private_population_file_sha256": None,
            },
            "worldbank": {
                "namespace": "worldbank_indicator",
                "targets": [dict(item) for item in WB_TARGETS],
                "catalog_response_sha256": wb_catalog_response_sha256,
                "snapshot_metadata": [dict(item) for item in wb_snapshot_metadata],
                "prior_excluded_iso3_count": EXPECTED_PRIOR_WB_COUNT,
                "selected_country_count": WB_SELECTED_COUNT,
                "task_count": WB_SELECTED_COUNT // WB_TASK_SIZE,
                "countries_per_task": WB_TASK_SIZE,
                **dict(wb_metrics),
                "visible_vector_sha256": payload_sha256(wb_visible),
                "gold_and_provenance_vector_sha256": payload_sha256(wb_gold),
                "private_population_file_sha256": None,
            },
        },
        "source_policy": {
            "benchmark_manifest_question_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "model_search_benchmark_forward_or_evaluator_called": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "private_population_available_to_future_forward": False,
        },
        "authorization": {
            "dual_namespace_reachability_protocol_design": True,
            "population_publication_only": True,
            "forward_launch": False,
            "evaluator": False,
            "benchmark_dev64_or_exact220": False,
            "entropy_or_credit_claim": False,
            "leaderboard_or_sota": False,
        },
    }
    return private_ror, private_wb, public


def validate_public(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    clusters = copied.get("clusters", {})
    ror = clusters.get("ror", {}) if isinstance(clusters, Mapping) else {}
    wb = clusters.get("worldbank", {}) if isinstance(clusters, Mapping) else {}
    unsigned = dict(copied)
    seal = unsigned.pop("design_payload_sha256", None)
    if (
        copied.get("role") != "v24727_dual_namespace_population_design"
        or copied.get("parents")
        != {
            "v24723_fresh_design_sha256": sha256(ROOT / PARENT_FRESH_DESIGN),
            "v24726_decision_sha256": sha256(ROOT / PARENT_DECISION),
            "v24726_postresult_audit_sha256": sha256(ROOT / PARENT_AUDIT),
        }
        or copied.get("selection_timing")
        != {
            "ror_and_worldbank_selection_code_frozen_before_v24727_outcome": True,
            "prior_task_quality_or_transport_outcome_used_to_rank_members": False,
            "deepwidebench_or_evaluator_content_used": False,
        }
        or ror.get("historical_entity_count") != EXPECTED_PRIOR_ROR_COUNT
        or ror.get("selected_entity_count") != ROR_SELECTED_COUNT
        or ror.get("task_count") != ROR_SELECTED_COUNT // ROR_TASK_SIZE
        or ror.get("entities_per_task") != ROR_TASK_SIZE
        or wb.get("targets") != [dict(item) for item in WB_TARGETS]
        or wb.get("prior_excluded_iso3_count") != EXPECTED_PRIOR_WB_COUNT
        or wb.get("selected_country_count") != WB_SELECTED_COUNT
        or wb.get("task_count") != WB_SELECTED_COUNT // WB_TASK_SIZE
        or wb.get("countries_per_task") != WB_TASK_SIZE
        or any(copied.get("source_policy", {}).values())
        or copied.get("authorization")
        != {
            "dual_namespace_reachability_protocol_design": True,
            "population_publication_only": True,
            "forward_launch": False,
            "evaluator": False,
            "benchmark_dev64_or_exact220": False,
            "entropy_or_credit_claim": False,
            "leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.27 public design drifted")
    return copied


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.47.27 requires clean pushed HEAD")
    if not _parent_valid():
        raise RuntimeError("V2.47.27 parent chain drifted")
    surfaces = (ROOT / PRIVATE_ROR, ROOT / PRIVATE_WB, ROOT / OUTPUT)
    if any(path.exists() or path.is_symlink() for path in surfaces):
        raise FileExistsError("V2.47.27 population surface exists")

    tree_raw = _fetch(ROR_TREE_URL, limit=MAX_ROR_TREE_BYTES)
    ror_entries = parse_ror_tree(tree_raw)
    ror_source = fetch_ror_records(ror_entries)
    _history, historical_canonical = prior_ror_entities()
    ror_selected, ror_metrics = select_ror_records(
        ror_source,
        historical_canonical=historical_canonical,
        canonical=ror_base.history.population._canonical_entity,
    )

    catalog_raw = _fetch(WB_CATALOG_URL, limit=MAX_WB_RESPONSE_BYTES)
    countries, _catalog_meta = wb_base.parse_country_catalog(catalog_raw)
    snapshots = []
    snapshot_metadata = []
    for target, runtime_target in zip(WB_TARGETS, wb_runtime.TARGETS, strict=True):
        if (
            target["indicator"] != runtime_target.indicator
            or target["year"] != runtime_target.year
        ):
            raise RuntimeError("V2.47.27 World Bank target binding drifted")
        url = wb_runtime.endpoint_url(runtime_target, wb_runtime.PRIMARY_REPRESENTATION)
        raw = _fetch(url, limit=wb_runtime.MAX_RESPONSE_BYTES)
        records, updated = wb_runtime.parse_records(
            raw,
            target=runtime_target,
            representation=wb_runtime.PRIMARY_REPRESENTATION,
        )
        snapshots.append(records)
        snapshot_metadata.append(
            {
                "indicator": runtime_target.indicator,
                "year": runtime_target.year,
                "url_sha256": hashlib.sha256(url.encode()).hexdigest(),
                "raw_sha256": hashlib.sha256(raw).hexdigest(),
                "semantic_sha256": wb_runtime.semantic_sha256(records),
                "record_count": len(records),
                "non_null_count": sum(value is not None for value in records.values()),
                "last_updated": updated,
            }
        )
    wb_selected, wb_metrics = select_worldbank_records(
        countries,
        snapshots,
        excluded=prior_worldbank_iso3(),
    )
    for item in wb_selected:
        item["values"] = [
            _canonical_decimal(snapshots[index][item["iso3"]])
            for index in range(len(snapshots))
        ]

    now = int(time.time())
    private_ror, private_wb, public = build_artifacts(
        ror_records=ror_selected,
        ror_metrics=ror_metrics,
        wb_records=wb_selected,
        wb_metrics=wb_metrics,
        ror_tree_response_sha256=hashlib.sha256(tree_raw).hexdigest(),
        ror_record_vector_sha256=payload_sha256(
            [
                {
                    "path": path,
                    "blob_sha1": blob,
                    "record_bytes_sha256": hashlib.sha256(raw).hexdigest(),
                }
                for path, blob, raw, _value in ror_source
            ]
        ),
        wb_catalog_response_sha256=hashlib.sha256(catalog_raw).hexdigest(),
        wb_snapshot_metadata=snapshot_metadata,
        now=now,
        git_head=_git("rev-parse", "HEAD"),
    )
    created = []
    try:
        _publish(ROOT / PRIVATE_ROR, private_ror)
        created.append(ROOT / PRIVATE_ROR)
        _publish(ROOT / PRIVATE_WB, private_wb)
        created.append(ROOT / PRIVATE_WB)
        public["clusters"]["ror"]["private_population_file_sha256"] = sha256(
            ROOT / PRIVATE_ROR
        )
        public["clusters"]["worldbank"]["private_population_file_sha256"] = sha256(
            ROOT / PRIVATE_WB
        )
        public["design_payload_sha256"] = payload_sha256(public)
        validate_public(public)
        _publish(ROOT / OUTPUT, public)
        created.append(ROOT / OUTPUT)
    except BaseException:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "ror_private": str(PRIVATE_ROR),
                "worldbank_private": str(PRIVATE_WB),
                "ror_tasks": ROR_SELECTED_COUNT // ROR_TASK_SIZE,
                "worldbank_tasks": WB_SELECTED_COUNT // WB_TASK_SIZE,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
