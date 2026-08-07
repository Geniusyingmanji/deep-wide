#!/usr/bin/env python3
"""Freeze a fresh target-cell-disjoint World Bank external population.

The two targets are the deterministic unrequested remainder of the four-item
V2.47.39 pre-outcome candidate vector after subtracting the target vector
frozen in the V2.47.42 transport protocol.  They are not selected from any
transport outcome.  Freshness is checked against every tracked evaluator-only
World Bank population through V2.48.22 (five artifacts, eight target/year
pairs, 217 entities, and 672 unique gold cells).

The evaluator-only artifact contains public World Bank values.  The public
design contains only counts, hashes, provenance metadata, and content-free
transport receipts.  Neither artifact authorizes forward execution or
evaluator access.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v24805_worldbank_budget_ladder_smoke_population as base  # noqa: E402


DATE = "20260807"
AUTHORIZATION = Path(
    f"results/v24829_target_cell_disjoint_population_build_audit_v1_{DATE}.json"
)
PRIVATE = Path(
    f"evaluation/v24829_target_cell_disjoint_worldbank_population_private_v1_{DATE}.json"
)
OUTPUT = Path(
    f"results/v24829_target_cell_disjoint_worldbank_population_design_v1_{DATE}.json"
)
ACCOUNTING_AUDIT = Path(
    f"results/v24828_dedicated_exact_accounting_build_audit_v1_{DATE}.json"
)
CANDIDATE_DESIGN = Path(
    "results/v24739_fresh_resilience_population_design_v1_20260806.json"
)
REQUEST_PROTOCOL = Path(
    "results/v24742_fresh_resilience_preregistration_v1_20260806.json"
)
HISTORICAL_POPULATIONS = (
    Path("evaluation/v24690_worldbank_population_private_v1_20260806.json"),
    Path("evaluation/v24729_worldbank_population_private_v1_20260806.json"),
    Path(
        "evaluation/v24806_worldbank_budget_ladder_smoke_population_private_v1_20260807.json"
    ),
    Path(
        "evaluation/v24814_fresh_worldbank_population_private_v1_20260807.json"
    ),
    Path(
        "evaluation/v24822_cell_disjoint_worldbank_population_private_v1_20260807.json"
    ),
)
TARGETS = (
    {
        "label": "People using at least basic sanitation services (% of population)",
        "indicator": "SH.STA.BASS.ZS",
        "year": "2022",
    },
    {
        "label": "Unemployment, total (% of total labor force)",
        "indicator": "SL.UEM.TOTL.ZS",
        "year": "2023",
    },
)
TASK_SIZE = 4
TASK_COUNT = 32
SELECTED_COUNT = TASK_SIZE * TASK_COUNT
ATTEMPT_TIMEOUT_SECONDS = 90
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (0.5, 1.0)
MAX_RESPONSE_BYTES = 32 * 1024 * 1024
EXPECTED_HISTORICAL_ENTITY_COUNT = 217
EXPECTED_HISTORICAL_CELL_COUNT = 672
EXPECTED_HISTORICAL_TARGET_COUNT = 8


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _ordinary(root: Path, relative: Path) -> Path:
    path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.48.29 expected repository object: {relative}")
    return path


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.29 expected JSON object")
    return value


def _sha256(root: Path, relative: Path) -> str:
    digest = hashlib.sha256()
    with _ordinary(root, relative).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


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


def target_key(target: Mapping[str, Any]) -> str:
    indicator = str(target.get("indicator", ""))
    year = str(target.get("year", ""))
    if re.fullmatch(r"[A-Z][A-Z0-9.]{4,40}", indicator) is None or re.fullmatch(
        r"20[0-3][0-9]", year
    ) is None:
        raise ValueError("V2.48.29 target key drifted")
    return f"{indicator}@{year}"


def target_selection_contract(root: Path = ROOT) -> dict[str, Any]:
    """Select the never-requested remainder without reading request outcomes."""

    design = _read(root, CANDIDATE_DESIGN)
    protocol = _read(root, REQUEST_PROTOCOL)
    if (
        design.get("role") != "v24739_fresh_resilience_population_design"
        or not _sealed(design, "design_payload_sha256")
        or protocol.get("role") != "v24742_fresh_resilience_preregistration"
        or not _sealed(protocol, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.48.29 frozen target-selection parent drifted")
    selection = design.get("selection")
    target_contract = protocol.get("target_contract")
    if not isinstance(selection, Mapping) or not isinstance(target_contract, Mapping):
        raise RuntimeError("V2.48.29 target-selection surface absent")
    candidates = selection.get("candidate_vector")
    requested = target_contract.get("target_key_vector")
    if (
        not isinstance(candidates, list)
        or len(candidates) != 4
        or not isinstance(requested, list)
        or len(requested) != 2
        or selection.get("pre_outcome_commit")
        != "1c798a0d9462c3bc44becd2c27bff7ae1bd8745a"
        or selection.get("network_or_transport_outcome_used_for_selection") is not False
    ):
        raise RuntimeError("V2.48.29 pre-outcome candidate vector drifted")
    candidate_keys = [str(item.get("target_key", "")) for item in candidates]
    if candidate_keys != [
        "EG.ELC.ACCS.ZS@2022",
        "SH.H2O.BASW.ZS@2022",
        "SH.STA.BASS.ZS@2022",
        "SL.UEM.TOTL.ZS@2023",
    ] or requested != candidate_keys[:2]:
        raise RuntimeError("V2.48.29 candidate/request identity drifted")
    expected_labels = {target_key(item): str(item["label"]) for item in TARGETS}
    remaining = [item for item in candidates if item["target_key"] not in requested]
    if [item["target_key"] for item in remaining] != list(expected_labels):
        raise RuntimeError("V2.48.29 unrequested remainder drifted")
    for item in remaining:
        if item.get("label_sha256") != hashlib.sha256(
            expected_labels[item["target_key"]].encode()
        ).hexdigest():
            raise RuntimeError("V2.48.29 target label binding drifted")
    return {
        "rule": "fixed_v24739_candidate_vector_minus_v24742_preregistered_request_vector",
        "network_or_transport_outcome_field_read_for_selection": False,
        "candidate_design_path": str(CANDIDATE_DESIGN),
        "candidate_design_sha256": _sha256(root, CANDIDATE_DESIGN),
        "request_protocol_path": str(REQUEST_PROTOCOL),
        "request_protocol_sha256": _sha256(root, REQUEST_PROTOCOL),
        "pre_outcome_commit": selection["pre_outcome_commit"],
        "candidate_target_key_vector": candidate_keys,
        "already_requested_target_key_vector": list(requested),
        "selected_unrequested_target_key_vector": [
            item["target_key"] for item in remaining
        ],
    }


def historical_boundary(
    root: Path = ROOT,
) -> tuple[
    set[str],
    set[tuple[str, str, str]],
    set[tuple[str, str]],
    dict[str, str],
]:
    """Read only identity and target keys from prior evaluator populations."""

    entities: set[str] = set()
    cells: set[tuple[str, str, str]] = set()
    targets: set[tuple[str, str]] = set()
    manifest: dict[str, str] = {}
    for relative in HISTORICAL_POPULATIONS:
        path = _ordinary(root, relative)
        raw = path.read_bytes()
        value = json.loads(raw)
        if (
            not isinstance(value, Mapping)
            or "worldbank" not in str(value.get("role", ""))
            or not _sealed(value, "private_payload_sha256")
        ):
            raise RuntimeError("V2.48.29 historical population seal drifted")
        artifact_targets = value.get("targets")
        groups = value.get("groups")
        if (
            not isinstance(artifact_targets, list)
            or len(artifact_targets) != 2
            or not isinstance(groups, list)
            or not groups
        ):
            raise RuntimeError("V2.48.29 historical population schema drifted")
        local_targets: list[tuple[str, str]] = []
        for target in artifact_targets:
            if not isinstance(target, Mapping):
                raise RuntimeError("V2.48.29 historical target drifted")
            key = (str(target.get("indicator", "")), str(target.get("year", "")))
            target_key({"indicator": key[0], "year": key[1]})
            local_targets.append(key)
        if len(set(local_targets)) != 2:
            raise RuntimeError("V2.48.29 historical target cardinality drifted")
        for group in groups:
            if not isinstance(group, list) or not group:
                raise RuntimeError("V2.48.29 historical group drifted")
            for item in group:
                if not isinstance(item, Mapping):
                    raise RuntimeError("V2.48.29 historical entity drifted")
                iso3 = str(item.get("iso3", ""))
                if re.fullmatch(r"[A-Z]{3}", iso3) is None:
                    raise RuntimeError("V2.48.29 historical ISO3 drifted")
                entities.add(iso3)
                records = item.get("records")
                if isinstance(records, list):
                    record_keys = {
                        (str(record.get("indicator", "")), str(record.get("year", "")))
                        for record in records
                        if isinstance(record, Mapping)
                    }
                    if record_keys != set(local_targets):
                        raise RuntimeError("V2.48.29 historical record binding drifted")
                cells.update((iso3, indicator, year) for indicator, year in local_targets)
        targets.update(local_targets)
        manifest[str(relative)] = hashlib.sha256(raw).hexdigest()
    if (
        len(manifest) != len(HISTORICAL_POPULATIONS)
        or len(entities) != EXPECTED_HISTORICAL_ENTITY_COUNT
        or len(cells) != EXPECTED_HISTORICAL_CELL_COUNT
        or len(targets) != EXPECTED_HISTORICAL_TARGET_COUNT
    ):
        raise RuntimeError("V2.48.29 cumulative historical boundary drifted")
    return entities, cells, targets, dict(sorted(manifest.items()))


def _rank(iso3: str) -> str:
    return hashlib.sha256(f"v24829:target-cell-disjoint:{iso3}".encode()).hexdigest()


def select_population(
    countries: Mapping[str, Mapping[str, str]],
    snapshots: Sequence[Mapping[str, Mapping[str, Any]]],
    historical_entities: set[str],
    historical_cells: set[tuple[str, str, str]],
    historical_targets: set[tuple[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if len(snapshots) != len(TARGETS):
        raise ValueError("V2.48.29 snapshot vector drifted")
    target_pairs = {(item["indicator"], item["year"]) for item in TARGETS}
    if target_pairs & historical_targets:
        raise RuntimeError("V2.48.29 target/year overlaps evaluated history")
    candidates: list[dict[str, Any]] = []
    for iso3, country in countries.items():
        if any(iso3 not in snapshot for snapshot in snapshots):
            continue
        records = [copy.deepcopy(dict(snapshot[iso3])) for snapshot in snapshots]
        if not all(record.get("value") is not None for record in records):
            continue
        candidate_cells = {
            (iso3, str(record["indicator"]), str(record["year"]))
            for record in records
        }
        if candidate_cells & historical_cells:
            raise RuntimeError("V2.48.29 candidate gold cell overlaps history")
        candidates.append({**dict(country), "records": records})
    ordered = sorted(
        candidates,
        key=lambda item: (
            str(item["iso3"]) in historical_entities,
            _rank(str(item["iso3"])),
            str(item["iso3"]),
        ),
    )
    selected = ordered[:SELECTED_COUNT]
    selected_entities = {str(item["iso3"]) for item in selected}
    selected_cells = {
        (str(item["iso3"]), str(record["indicator"]), str(record["year"]))
        for item in selected
        for record in item["records"]
    }
    overlap = selected_entities & historical_entities
    if (
        len(selected) != SELECTED_COUNT
        or len(selected_entities) != SELECTED_COUNT
        or len(selected_cells) != SELECTED_COUNT * len(TARGETS)
        or selected_cells & historical_cells
    ):
        raise RuntimeError("V2.48.29 population capacity or disjointness failed")
    return selected, {
        "complete_candidate_count": len(candidates),
        "selected_country_count": len(selected_entities),
        "task_count": TASK_COUNT,
        "task_size": TASK_SIZE,
        "selected_gold_cell_count": len(selected_cells),
        "historical_population_count": len(HISTORICAL_POPULATIONS),
        "historical_entity_count": len(historical_entities),
        "historical_target_pair_count": len(historical_targets),
        "historical_gold_cell_key_count": len(historical_cells),
        "selected_entity_overlap_count": len(overlap),
        "selected_entity_novel_count": len(selected_entities - historical_entities),
        "selected_entity_overlap_rate": round(len(overlap) / SELECTED_COUNT, 12),
        "selected_target_pair_overlap_count": len(target_pairs & historical_targets),
        "selected_gold_cell_overlap_count": len(selected_cells & historical_cells),
        "region_count": len({str(item["region_id"]) for item in selected}),
    }


def fetch_bytes_bounded(
    url: str,
    *,
    opener: Callable[..., Any] = urllib.request.urlopen,
    sleeper: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> tuple[bytes, dict[str, Any]]:
    if not isinstance(url, str) or not url.startswith("https://api.worldbank.org/"):
        raise ValueError("V2.48.29 public snapshot URL drifted")
    attempts: list[dict[str, Any]] = []
    started = float(monotonic())
    for index in range(1, MAX_ATTEMPTS + 1):
        attempt_started = float(monotonic())
        status: int | None = None
        error_type: str | None = None
        retryable = False
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "deepwide-v24829/1"}
            )
            with opener(request, timeout=ATTEMPT_TIMEOUT_SECONDS) as response:
                status = int(getattr(response, "status", 200))
                if status != 200:
                    raise urllib.error.HTTPError(
                        url, status, "unexpected status", {}, None
                    )
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            if not raw or len(raw) > MAX_RESPONSE_BYTES:
                raise ValueError("V2.48.29 snapshot response size drifted")
            attempts.append(
                {
                    "attempt": index,
                    "status": status,
                    "outcome": "success",
                    "error_type": None,
                    "retryable": False,
                    "elapsed_seconds": round(
                        max(0.0, float(monotonic()) - attempt_started), 6
                    ),
                    "response_bytes": len(raw),
                    "response_sha256": hashlib.sha256(raw).hexdigest(),
                }
            )
            receipt = {
                "url_sha256": hashlib.sha256(url.encode()).hexdigest(),
                "attempt_timeout_seconds": ATTEMPT_TIMEOUT_SECONDS,
                "maximum_attempts": MAX_ATTEMPTS,
                "attempt_count": len(attempts),
                "attempts": attempts,
                "terminal_outcome": "success",
                "elapsed_seconds": round(max(0.0, float(monotonic()) - started), 6),
                "response_bytes": len(raw),
                "response_sha256": hashlib.sha256(raw).hexdigest(),
                "url_or_response_content_emitted": False,
            }
            receipt["receipt_sha256"] = payload_sha256(receipt)
            return raw, receipt
        except urllib.error.HTTPError as exc:
            status = int(exc.code)
            error_type = type(exc).__name__
            retryable = status in {408, 425, 429} or 500 <= status <= 599
        except (TimeoutError, socket.timeout, urllib.error.URLError) as exc:
            error_type = type(exc).__name__
            retryable = True
        attempts.append(
            {
                "attempt": index,
                "status": status,
                "outcome": "failure",
                "error_type": error_type,
                "retryable": retryable,
                "elapsed_seconds": round(
                    max(0.0, float(monotonic()) - attempt_started), 6
                ),
                "response_bytes": 0,
                "response_sha256": None,
            }
        )
        if not retryable or index == MAX_ATTEMPTS:
            break
        sleeper(BACKOFF_SECONDS[index - 1])
    raise RuntimeError(
        "V2.48.29 bounded public snapshot acquisition exhausted: "
        + payload_sha256(attempts)
    )


def build_artifacts(
    selected: Sequence[Mapping[str, Any]],
    *,
    transport_receipts: Sequence[Mapping[str, Any]],
    catalog_metadata: Mapping[str, Any],
    snapshot_metadata: Sequence[Mapping[str, Any]],
    historical_manifest: Mapping[str, str],
    selection_contract: Mapping[str, Any],
    metrics: Mapping[str, Any],
    created_at: int,
    git_head: str,
    authorization_audit_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if (
        re.fullmatch(r"[0-9a-f]{64}", authorization_audit_sha256) is None
        or len(transport_receipts) != 3
        or any(
            receipt.get("terminal_outcome") != "success"
            or receipt.get("url_or_response_content_emitted") is not False
            or not _sealed(receipt, "receipt_sha256")
            for receipt in transport_receipts
        )
    ):
        raise ValueError("V2.48.29 authorization or transport receipt drifted")
    groups = [
        [copy.deepcopy(dict(item)) for item in selected[index : index + TASK_SIZE]]
        for index in range(0, len(selected), TASK_SIZE)
    ]
    if len(groups) != TASK_COUNT or any(len(group) != TASK_SIZE for group in groups):
        raise RuntimeError("V2.48.29 group denominator drifted")
    private = {
        "artifact_version": 1,
        "role": "v24829_target_cell_disjoint_worldbank_evaluator_only_population",
        "created_at_unix": int(created_at),
        "targets": [dict(target) for target in TARGETS],
        "groups": groups,
        "catalog": dict(catalog_metadata),
        "indicator_snapshots": [dict(item) for item in snapshot_metadata],
        "historical_boundary_manifest": dict(historical_manifest),
        "target_selection_contract": dict(selection_contract),
        "selection_rule": (
            "preoutcome_candidate_remainder_then_complete_values_then_entity_"
            "novelty_then_v24829_hash_rank_select_128"
        ),
        "disjointness_scope": {
            "task_question_vector_disjoint": True,
            "indicator_year_target_pairs_disjoint": True,
            "country_indicator_year_gold_cells_disjoint": True,
            "country_entities_disjoint": False,
            "country_entity_overlap_reported_in_public_design": True,
            "targets_never_previously_requested_or_evaluated": True,
        },
        "forward_import_or_runtime_read_authorized": False,
        "gold_provenance_or_evaluator_read_before_prediction_freeze_authorized": False,
        "mechanism_validation_only_not_calibration_lock_validation_or_confirmatory": True,
    }
    private["private_payload_sha256"] = payload_sha256(private)
    visible = [
        {"name": str(item["name"]), "iso3": str(item["iso3"])}
        for item in selected
    ]
    value_vector = [
        {
            "iso3": str(item["iso3"]),
            "records": [
                {
                    "indicator": str(record["indicator"]),
                    "year": str(record["year"]),
                    "value": record["value"],
                    "response_sha256": str(record["response_sha256"]),
                }
                for record in item["records"]
            ],
        }
        for item in selected
    ]
    public = {
        "artifact_version": 1,
        "role": "v24829_target_cell_disjoint_worldbank_population_design",
        "created_at_unix": int(created_at),
        "git_head": git_head,
        "accounting_build_audit_sha256": _sha256(ROOT, ACCOUNTING_AUDIT),
        "authorization_audit_sha256": authorization_audit_sha256,
        "target_selection_contract": dict(selection_contract),
        "catalog_response_sha256": str(catalog_metadata["response_sha256"]),
        "indicator_snapshot_metadata": [dict(item) for item in snapshot_metadata],
        "historical_boundary_manifest_sha256": payload_sha256(historical_manifest),
        **dict(metrics),
        "selected_visible_vector_sha256": payload_sha256(visible),
        "selected_value_and_provenance_vector_sha256": payload_sha256(value_vector),
        "private_population_file_sha256": None,
        "transport": {
            "attempt_timeout_seconds": ATTEMPT_TIMEOUT_SECONDS,
            "maximum_attempts_per_url": MAX_ATTEMPTS,
            "maximum_response_bytes": MAX_RESPONSE_BYTES,
            "url_count": 3,
            "total_attempt_count": sum(
                int(receipt["attempt_count"]) for receipt in transport_receipts
            ),
            "receipts": [copy.deepcopy(dict(item)) for item in transport_receipts],
        },
        "network": {
            "worldbank_country_catalog_reads": 1,
            "worldbank_indicator_snapshot_reads": 2,
            "model_search_benchmark_or_evaluator_calls": 0,
        },
        "privacy": {
            "selected_country_name_iso3_value_or_gold_emitted": False,
            "private_vector_under_evaluation_directory": True,
            "forward_import_or_runtime_read_authorized": False,
        },
        "scope": {
            "mechanism_validation_task_count": TASK_COUNT,
            "entity_disjoint_claim": False,
            "target_cell_disjoint_claim": True,
            "never_requested_target_claim": True,
        },
        "authorization": {
            "fresh_external_protocol_design": True,
            "external_launch": False,
            "evaluator_access": False,
            "public_dev64_or_exact220": False,
        },
    }
    return private, public


def _authorized(root: Path = ROOT) -> bool:
    value = _read(root, AUTHORIZATION)
    return bool(
        value.get("role")
        == "v24829_target_cell_disjoint_population_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("authorization", {}).get("one_population_publication") is True
        and value.get("authorization", {}).get("external_launch") is False
        and _sealed(value, "audit_payload_sha256")
    )


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    target = ROOT / path
    if target.exists() or target.is_symlink():
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
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
        raise RuntimeError("V2.48.29 publication requires clean pushed HEAD")
    if not _authorized():
        raise RuntimeError("V2.48.29 population publication is not authorized")
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (PRIVATE, OUTPUT)
    ):
        raise FileExistsError("V2.48.29 population surface is not pristine")
    selection_contract = target_selection_contract()
    historical_entities, historical_cells, historical_targets, manifest = (
        historical_boundary()
    )
    catalog_raw, catalog_receipt = fetch_bytes_bounded(base.COUNTRY_CATALOG_URL)
    countries, catalog_metadata = base.parse_country_catalog(catalog_raw)
    snapshots: list[dict[str, dict[str, Any]]] = []
    snapshot_metadata: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = [catalog_receipt]
    for target in TARGETS:
        url = base.indicator_url(target["indicator"], target["year"])
        raw, receipt = fetch_bytes_bounded(url)
        records, metadata = base.parse_indicator_snapshot(
            raw,
            indicator=target["indicator"],
            year=target["year"],
            source_url=url,
        )
        snapshots.append(records)
        snapshot_metadata.append(metadata)
        receipts.append(receipt)
    selected, metrics = select_population(
        countries,
        snapshots,
        historical_entities,
        historical_cells,
        historical_targets,
    )
    private, public = build_artifacts(
        selected,
        transport_receipts=receipts,
        catalog_metadata=catalog_metadata,
        snapshot_metadata=snapshot_metadata,
        historical_manifest=manifest,
        selection_contract=selection_contract,
        metrics=metrics,
        created_at=int(time.time()),
        git_head=_git("rev-parse", "HEAD"),
        authorization_audit_sha256=_sha256(ROOT, AUTHORIZATION),
    )
    _publish(PRIVATE, private)
    public["private_population_file_sha256"] = hashlib.sha256(
        (ROOT / PRIVATE).read_bytes()
    ).hexdigest()
    public["design_payload_sha256"] = payload_sha256(public)
    _publish(OUTPUT, public)
    print(
        json.dumps(
            {
                "private": str(PRIVATE),
                "output": str(OUTPUT),
                "selected_country_count": metrics["selected_country_count"],
                "selected_gold_cell_count": metrics["selected_gold_cell_count"],
                "selected_target_pair_overlap_count": metrics[
                    "selected_target_pair_overlap_count"
                ],
                "selected_gold_cell_overlap_count": metrics[
                    "selected_gold_cell_overlap_count"
                ],
                "total_transport_attempts": public["transport"][
                    "total_attempt_count"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
