#!/usr/bin/env python3
"""Content-free capacity diagnosis for the failed V2.47.27 population design."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24724_fresh_indicator_transport as runtime  # noqa: E402
from scripts import design_v24727_dual_namespace_population as design  # noqa: E402


DATE = "20260806"
OUTPUT = Path(f"results/v24728_v24727_population_capacity_diagnosis_v1_{DATE}.json")
FAILED_SURFACES = (design.PRIVATE_ROR, design.PRIVATE_WB, design.OUTPUT)
CAP_VECTOR = tuple(range(8, 17))
REQUIRED_COUNT = design.WB_SELECTED_COUNT
FAILED_CAP = design.WB_REGION_CAP


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
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


def capacity_curve(region_counts: Mapping[str, int]) -> dict[str, int]:
    if (
        not region_counts
        or any(
            not isinstance(region, str)
            or not region
            or isinstance(amount, bool)
            or not isinstance(amount, int)
            or amount <= 0
            for region, amount in region_counts.items()
        )
    ):
        raise ValueError("V2.47.28 invalid region-count vector")
    return {
        str(cap): sum(min(cap, amount) for amount in region_counts.values())
        for cap in CAP_VECTOR
    }


def minimum_feasible_cap(curve: Mapping[str, int]) -> int:
    values = [
        cap
        for cap in CAP_VECTOR
        if curve.get(str(cap), -1) >= REQUIRED_COUNT
    ]
    if not values:
        raise RuntimeError("V2.47.28 no feasible bounded cap")
    return min(values)


def build_diagnosis(
    *,
    countries: Mapping[str, Mapping[str, str]],
    snapshots: list[Mapping[str, Any]],
    catalog_sha256: str,
    snapshot_metadata: list[Mapping[str, Any]],
    now: int,
    git_head: str,
) -> dict[str, Any]:
    if len(snapshots) != len(design.WB_TARGETS):
        raise ValueError("V2.47.28 snapshot count drifted")
    excluded = design.prior_worldbank_iso3()
    counts: Counter[str] = Counter()
    for iso3, country in countries.items():
        if iso3 in excluded:
            continue
        if all(iso3 in snapshot and snapshot[iso3] is not None for snapshot in snapshots):
            counts[str(country["region_id"])] += 1
    curve = capacity_curve(counts)
    repaired_cap = minimum_feasible_cap(curve)
    if curve[str(FAILED_CAP)] >= REQUIRED_COUNT or repaired_cap <= FAILED_CAP:
        raise RuntimeError("V2.47.28 did not reproduce the capacity failure")
    value = {
        "artifact_version": 1,
        "role": "v24728_v24727_population_capacity_diagnosis",
        "created_at_unix": int(now),
        "git_head": git_head,
        "parents": {
            "v24727_design_source_sha256": sha256(
                ROOT / "scripts/design_v24727_dual_namespace_population.py"
            ),
            "v24726_decision_sha256": sha256(ROOT / design.PARENT_DECISION),
            "v24726_postresult_audit_sha256": sha256(ROOT / design.PARENT_AUDIT),
        },
        "failed_publication": {
            "stage": "worldbank_population_capacity_check",
            "all_v24727_output_surfaces_pristine": all(
                not (ROOT / path).exists() and not (ROOT / path).is_symlink()
                for path in FAILED_SURFACES
            ),
            "failed_region_cap": FAILED_CAP,
            "required_selected_country_count": REQUIRED_COUNT,
            "failed_cap_capacity": curve[str(FAILED_CAP)],
            "identity_value_gold_or_quality_emitted": False,
        },
        "content_free_capacity": {
            "eligible_country_count": sum(counts.values()),
            "eligible_region_count": len(counts),
            "largest_region_count": max(counts.values()),
            "cap_vector": list(CAP_VECTOR),
            "capacity_by_cap": curve,
            "minimum_feasible_cap": repaired_cap,
            "selection_rule_indicator_or_rank_changed": False,
        },
        "source_receipts": {
            "catalog_sha256": catalog_sha256,
            "snapshots": [dict(item) for item in snapshot_metadata],
            "prior_excluded_iso3_count": len(excluded),
            "country_identity_or_value_persisted": False,
        },
        "source_policy": {
            "benchmark_manifest_question_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "model_search_benchmark_forward_or_evaluator_called": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "quality_or_transport_outcome_used_for_capacity_repair": False,
        },
        "authorization": {
            "append_only_capacity_repaired_population_design": True,
            "repaired_region_cap": repaired_cap,
            "population_publication_only": True,
            "forward_launch": False,
            "evaluator": False,
            "benchmark_dev64_or_exact220": False,
            "entropy_or_credit_claim": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    validate_diagnosis(value)
    return value


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    failed = copied.get("failed_publication", {})
    capacity = copied.get("content_free_capacity", {})
    curve = capacity.get("capacity_by_cap", {})
    repaired = minimum_feasible_cap(curve) if isinstance(curve, Mapping) else -1
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    if (
        copied.get("role") != "v24728_v24727_population_capacity_diagnosis"
        or failed.get("stage") != "worldbank_population_capacity_check"
        or failed.get("all_v24727_output_surfaces_pristine") is not True
        or failed.get("failed_region_cap") != FAILED_CAP
        or failed.get("required_selected_country_count") != REQUIRED_COUNT
        or failed.get("failed_cap_capacity") != curve.get(str(FAILED_CAP))
        or failed.get("failed_cap_capacity", REQUIRED_COUNT) >= REQUIRED_COUNT
        or failed.get("identity_value_gold_or_quality_emitted") is not False
        or capacity.get("cap_vector") != list(CAP_VECTOR)
        or capacity.get("minimum_feasible_cap") != repaired
        or repaired != 10
        or capacity.get("selection_rule_indicator_or_rank_changed") is not False
        or any(copied.get("source_policy", {}).values())
        or copied.get("authorization")
        != {
            "append_only_capacity_repaired_population_design": True,
            "repaired_region_cap": repaired,
            "population_publication_only": True,
            "forward_launch": False,
            "evaluator": False,
            "benchmark_dev64_or_exact220": False,
            "entropy_or_credit_claim": False,
            "leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.28 capacity diagnosis drifted")
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
        raise RuntimeError("V2.47.28 requires clean pushed HEAD")
    if not design._parent_valid():
        raise RuntimeError("V2.47.28 parent chain drifted")
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in FAILED_SURFACES):
        raise RuntimeError("V2.47.28 failed surfaces are not pristine")

    catalog_raw = design._fetch(
        design.WB_CATALOG_URL, limit=design.MAX_WB_RESPONSE_BYTES
    )
    countries, _metadata = design.wb_base.parse_country_catalog(catalog_raw)
    snapshots = []
    receipts = []
    for target in runtime.TARGETS:
        url = runtime.endpoint_url(target, runtime.PRIMARY_REPRESENTATION)
        raw = design._fetch(url, limit=runtime.MAX_RESPONSE_BYTES)
        records, updated = runtime.parse_records(
            raw, target=target, representation=runtime.PRIMARY_REPRESENTATION
        )
        snapshots.append(records)
        receipts.append(
            {
                "indicator": target.indicator,
                "year": target.year,
                "url_sha256": hashlib.sha256(url.encode()).hexdigest(),
                "raw_sha256": hashlib.sha256(raw).hexdigest(),
                "semantic_sha256": runtime.semantic_sha256(records),
                "record_count": len(records),
                "non_null_count": sum(value is not None for value in records.values()),
                "last_updated": updated,
            }
        )
    diagnosis = build_diagnosis(
        countries=countries,
        snapshots=snapshots,
        catalog_sha256=hashlib.sha256(catalog_raw).hexdigest(),
        snapshot_metadata=receipts,
        now=int(time.time()),
        git_head=_git("rev-parse", "HEAD"),
    )
    _publish(ROOT / OUTPUT, diagnosis)


if __name__ == "__main__":
    main()
