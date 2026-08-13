#!/usr/bin/env python3
"""Append-only pagination correction for the V2.52.94 World Bank gate.

The V1 design fixed two ``per_page=120`` responses for a World Bank surface
whose already-frozen official responses report 265 records.  That shape needs
three pages, so V1 cannot establish a complete snapshot.  R2 changes only the
page size and adds explicit completeness invariants; it does not select a
population or perform a network, model, benchmark, or evaluator effect.
"""

from __future__ import annotations

import copy
import json
import math
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v25294_worldbank_monotone_fill_gate as parent  # noqa: E402


DATE = "20260813"
ROLE = "v25294_worldbank_monotone_fill_gate_design_r2"
OUTPUT = Path(f"results/v25294_worldbank_monotone_fill_gate_design_r2_{DATE}.json")
SOURCE = Path("scripts/revise_v25294_worldbank_monotone_fill_gate_r2.py")
TEST = Path("tests/test_revise_v25294_worldbank_monotone_fill_gate_r2.py")
PARENT = parent.OUTPUT
PARENT_SHA256 = "54e403acc2ea29750da01b103e994951846cb46db54f347fb4a3820a2112a248"
OLD_PER_PAGE = 120
CORRECTED_PER_PAGE = 200
EXPECTED_OBSERVED_TOTAL = 265
RAW_RESPONSES = {
    Path(
        "outputs/v24923_target_value_external_v1_20260808/"
        f"snapshot/target_responses/response_{index:02d}.bin"
    ): digest
    for index, digest in enumerate(
        (
            "e717d221f235269e77fdbad4e154d822b2ab1346edf0a88bfb04583d5bb4429b",
            "6e5cc7250a4206e9ddab0a6ba632eda50124649e6d26bf4dfc64507a7f760af0",
            "49e8efc1d1c06ea3c02118e1843ffe727e181094ace2f081f9d5e8940dd9368d",
            "e3719c8fa9a6d68eef3bf97a603232c21ee077c9b1159594824396db27e826f2",
        ),
        1,
    )
}
payload_sha256 = parent.payload_sha256


def _parent_design() -> dict[str, Any]:
    if parent.base.sha256(PARENT) != PARENT_SHA256:
        raise RuntimeError("V2.52.94 R2 parent hash drifted")
    raw = json.loads(parent.base._ordinary(PARENT).read_text(encoding="utf-8"))
    return parent.validate_design(raw)


def _metadata_evidence() -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for path, digest in RAW_RESPONSES.items():
        ordinary = parent.base._ordinary(path)
        if parent.base.sha256(path) != digest:
            raise RuntimeError("V2.52.94 R2 raw response hash drifted")
        value = json.loads(ordinary.read_bytes())
        if (
            not isinstance(value, list)
            or len(value) != 2
            or not isinstance(value[0], Mapping)
            or not isinstance(value[1], list)
        ):
            raise RuntimeError("V2.52.94 R2 raw response envelope drifted")
        metadata = value[0]
        observed = {
            "path": str(path),
            "sha256": digest,
            "page": int(metadata.get("page", -1)),
            "pages": int(metadata.get("pages", -1)),
            "per_page": int(metadata.get("per_page", -1)),
            "total": int(metadata.get("total", -1)),
            "record_count": len(value[1]),
        }
        if observed != {
            "path": str(path),
            "sha256": digest,
            "page": 1,
            "pages": 1,
            "per_page": 400,
            "total": EXPECTED_OBSERVED_TOTAL,
            "record_count": EXPECTED_OBSERVED_TOTAL,
        }:
            raise RuntimeError("V2.52.94 R2 metadata evidence drifted")
        evidence.append(observed)
    return evidence


def _source_hashes() -> dict[str, str]:
    return {str(path): parent.base.sha256(path) for path in (SOURCE, TEST)}


def _expected_revision(*, now: int) -> dict[str, Any]:
    value = copy.deepcopy(_parent_design())
    evidence = _metadata_evidence()
    value["role"] = ROLE
    value["created_at_unix"] = int(now)
    value["parent_design"] = {"path": str(PARENT), "sha256": PARENT_SHA256}
    value["revision_source_hashes"] = _source_hashes()
    value["correction"] = {
        "fields": [
            "snapshot_and_representation_contract.world_bank_per_page",
            "snapshot_and_representation_contract.complete_official_record_coverage_required",
            "snapshot_and_representation_contract.metadata_total_must_equal_sum_page_record_counts",
            "snapshot_and_representation_contract.metadata_pages_must_equal_ceiling_total_over_per_page",
        ],
        "old_per_page": OLD_PER_PAGE,
        "corrected_per_page": CORRECTED_PER_PAGE,
        "observed_prior_official_total": EXPECTED_OBSERVED_TOTAL,
        "old_page_count_for_observed_total": math.ceil(
            EXPECTED_OBSERVED_TOTAL / OLD_PER_PAGE
        ),
        "corrected_page_count_for_observed_total": math.ceil(
            EXPECTED_OBSERVED_TOTAL / CORRECTED_PER_PAGE
        ),
        "reason": "frozen_official_metadata_reports_265_records_so_per_page_120_requires_three_pages_and_cannot_satisfy_the_two_page_snapshot_contract",
        "historical_metadata_evidence": evidence,
        "record_identity_or_value_used_for_correction": False,
        "population_selected_or_frozen": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "all_other_v1_contracts_and_authority_unchanged": True,
    }
    snapshot = value["snapshot_and_representation_contract"]
    snapshot["world_bank_per_page"] = CORRECTED_PER_PAGE
    snapshot["complete_official_record_coverage_required"] = True
    snapshot["metadata_total_must_equal_sum_page_record_counts"] = True
    snapshot[
        "metadata_pages_must_equal_ceiling_total_over_per_page"
    ] = True
    value.pop("design_payload_sha256")
    value["design_payload_sha256"] = payload_sha256(value)
    return value


def build_revision(*, now: int | None = None) -> dict[str, Any]:
    value = _expected_revision(
        now=int(time.time()) if now is None else int(now)
    )
    return validate_revision(value)


def validate_revision(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    created = copied.get("created_at_unix")
    if isinstance(created, bool) or not isinstance(created, int):
        raise ValueError("V2.52.94 R2 created-at drifted")
    expected = _expected_revision(now=created)
    if copied != expected:
        raise ValueError("V2.52.94 R2 World Bank gate design drifted")
    return copied


def main() -> None:
    value = build_revision()
    parent.base.publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "revision": "R2",
                "world_bank_per_page": CORRECTED_PER_PAGE,
                "population_freeze_authorized": value["authorization"]
                ["network_population_selection_or_freeze"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
