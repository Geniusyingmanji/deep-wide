#!/usr/bin/env python3
"""Append-only capacity repair for the V2.47.27 dual-namespace population."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24724_fresh_indicator_transport as wb_runtime  # noqa: E402
from scripts import design_v24727_dual_namespace_population as base  # noqa: E402
from scripts import diagnose_v24728_v24727_population_capacity as diagnosis  # noqa: E402


DATE = "20260806"
PARENT = diagnosis.OUTPUT
OUTPUT = Path(f"results/v24729_dual_namespace_population_design_v1_{DATE}.json")
PRIVATE_ROR = Path(f"evaluation/v24729_ror_population_private_v1_{DATE}.json")
PRIVATE_WB = Path(f"evaluation/v24729_worldbank_population_private_v1_{DATE}.json")
REPAIRED_REGION_CAP = 10
FAILED_SURFACES = (base.PRIVATE_ROR, base.PRIVATE_WB, base.OUTPUT)


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


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.47.29 expected ordinary parent")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.29 expected object")
    return value


def _parent_valid() -> bool:
    value = _read(ROOT / PARENT)
    try:
        diagnosis.validate_diagnosis(value)
    except (RuntimeError, TypeError, ValueError):
        return False
    return (
        value.get("authorization", {}).get(
            "append_only_capacity_repaired_population_design"
        )
        is True
        and value.get("authorization", {}).get("repaired_region_cap")
        == REPAIRED_REGION_CAP
        and value.get("authorization", {}).get("forward_launch") is False
        and value.get("authorization", {}).get("evaluator") is False
        and value.get("authorization", {}).get("benchmark_dev64_or_exact220")
        is False
        and value.get("failed_publication", {}).get(
            "all_v24727_output_surfaces_pristine"
        )
        is True
        and value.get("content_free_capacity", {}).get("minimum_feasible_cap")
        == REPAIRED_REGION_CAP
    )


def repair_artifacts(
    private_ror: Mapping[str, Any],
    private_wb: Mapping[str, Any],
    public: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    ror = dict(private_ror)
    wb = dict(private_wb)
    design = json.loads(json.dumps(public))
    ror.pop("private_payload_sha256", None)
    wb.pop("private_payload_sha256", None)
    design.pop("design_payload_sha256", None)
    ror["role"] = "v24729_ror_evaluator_only_population"
    wb["role"] = "v24729_worldbank_evaluator_only_population"
    wb["selection_rule"] = (
        "complete_two_fresh_indicator_values_prior_external_iso3_exclusion_"
        "v24727_sha256_rank_region_cap10_round_robin_groups4"
    )
    ror["private_payload_sha256"] = payload_sha256(ror)
    wb["private_payload_sha256"] = payload_sha256(wb)
    design["role"] = "v24729_dual_namespace_population_design"
    design["parents"]["v24728_capacity_diagnosis_sha256"] = sha256(ROOT / PARENT)
    design["capacity_repair"] = {
        "predecessor_v24727_output_surfaces_pristine": all(
            not (ROOT / path).exists() and not (ROOT / path).is_symlink()
            for path in FAILED_SURFACES
        ),
        "failed_region_cap": base.WB_REGION_CAP,
        "failed_cap_capacity": 46,
        "minimum_feasible_region_cap": REPAIRED_REGION_CAP,
        "minimum_feasible_cap_capacity": 51,
        "indicator_rank_exclusion_or_grouping_rule_changed": False,
        "only_region_cap_changed": True,
    }
    worldbank = design["clusters"]["worldbank"]
    worldbank["selection_rule"] = wb["selection_rule"]
    worldbank["region_cap"] = REPAIRED_REGION_CAP
    worldbank["private_population_file_sha256"] = None
    design["clusters"]["ror"]["private_population_file_sha256"] = None
    design["authorization"] = {
        "dual_namespace_reachability_protocol_design": True,
        "population_publication_only": True,
        "forward_launch": False,
        "evaluator": False,
        "benchmark_dev64_or_exact220": False,
        "entropy_or_credit_claim": False,
        "leaderboard_or_sota": False,
    }
    return ror, wb, design


def validate_public(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    repair = copied.get("capacity_repair", {})
    worldbank = copied.get("clusters", {}).get("worldbank", {})
    unsigned = dict(copied)
    seal = unsigned.pop("design_payload_sha256", None)
    if (
        copied.get("role") != "v24729_dual_namespace_population_design"
        or copied.get("parents", {}).get("v24728_capacity_diagnosis_sha256")
        != sha256(ROOT / PARENT)
        or repair
        != {
            "predecessor_v24727_output_surfaces_pristine": True,
            "failed_region_cap": base.WB_REGION_CAP,
            "failed_cap_capacity": 46,
            "minimum_feasible_region_cap": REPAIRED_REGION_CAP,
            "minimum_feasible_cap_capacity": 51,
            "indicator_rank_exclusion_or_grouping_rule_changed": False,
            "only_region_cap_changed": True,
        }
        or worldbank.get("region_cap") != REPAIRED_REGION_CAP
        or worldbank.get("selected_country_count") != base.WB_SELECTED_COUNT
        or worldbank.get("task_count") != base.WB_SELECTED_COUNT // base.WB_TASK_SIZE
        or worldbank.get("selected_region_max", REPAIRED_REGION_CAP + 1)
        > REPAIRED_REGION_CAP
        or worldbank.get("selection_rule")
        != "complete_two_fresh_indicator_values_prior_external_iso3_exclusion_v24727_sha256_rank_region_cap10_round_robin_groups4"
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
        raise RuntimeError("V2.47.29 repaired public design drifted")
    return copied


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
        raise RuntimeError("V2.47.29 requires clean pushed HEAD")
    if not _parent_valid() or not base._parent_valid():
        raise RuntimeError("V2.47.29 parent chain drifted")
    new_surfaces = (ROOT / PRIVATE_ROR, ROOT / PRIVATE_WB, ROOT / OUTPUT)
    if any(path.exists() or path.is_symlink() for path in new_surfaces):
        raise FileExistsError("V2.47.29 repaired surface exists")
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in FAILED_SURFACES):
        raise RuntimeError("V2.47.29 predecessor failed surface is not pristine")

    tree_raw = base._fetch(base.ROR_TREE_URL, limit=base.MAX_ROR_TREE_BYTES)
    ror_entries = base.parse_ror_tree(tree_raw)
    ror_source = base.fetch_ror_records(ror_entries)
    _history, historical_canonical = base.prior_ror_entities()
    ror_selected, ror_metrics = base.select_ror_records(
        ror_source,
        historical_canonical=historical_canonical,
        canonical=base.ror_base.history.population._canonical_entity,
    )

    catalog_raw = base._fetch(base.WB_CATALOG_URL, limit=base.MAX_WB_RESPONSE_BYTES)
    countries, _catalog_metadata = base.wb_base.parse_country_catalog(catalog_raw)
    snapshots = []
    snapshot_metadata = []
    for target, runtime_target in zip(base.WB_TARGETS, wb_runtime.TARGETS, strict=True):
        if target["indicator"] != runtime_target.indicator or target["year"] != runtime_target.year:
            raise RuntimeError("V2.47.29 World Bank target binding drifted")
        url = wb_runtime.endpoint_url(runtime_target, wb_runtime.PRIMARY_REPRESENTATION)
        raw = base._fetch(url, limit=wb_runtime.MAX_RESPONSE_BYTES)
        records, updated = wb_runtime.parse_records(
            raw, target=runtime_target, representation=wb_runtime.PRIMARY_REPRESENTATION
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
    wb_selected, wb_metrics = base.select_worldbank_records(
        countries,
        snapshots,
        excluded=base.prior_worldbank_iso3(),
        region_cap=REPAIRED_REGION_CAP,
    )
    for item in wb_selected:
        item["values"] = [
            base._canonical_decimal(snapshots[index][item["iso3"]])
            for index in range(len(snapshots))
        ]

    private_ror, private_wb, public = base.build_artifacts(
        ror_records=ror_selected,
        ror_metrics=ror_metrics,
        wb_records=wb_selected,
        wb_metrics=wb_metrics,
        ror_tree_response_sha256=hashlib.sha256(tree_raw).hexdigest(),
        ror_record_vector_sha256=base.payload_sha256(
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
        now=int(time.time()),
        git_head=_git("rev-parse", "HEAD"),
    )
    private_ror, private_wb, public = repair_artifacts(
        private_ror, private_wb, public
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


if __name__ == "__main__":
    main()
