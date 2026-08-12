#!/usr/bin/env python3
"""Append-only correction to one V2.52.14 snapshot predicate."""

from __future__ import annotations

import copy
import json
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25210_receipt_disposition_observer_build as base  # noqa: E402
from scripts import design_v25214_candidate_preselection_protocol as v1  # noqa: E402


DATE = "20260812"
OUTPUT = Path(f"results/v25214_candidate_preselection_protocol_design_r2_{DATE}.json")
PARENT = v1.OUTPUT
EXPECTED_PARENT_SHA256 = (
    "e54ce2aa7adcdf37afa2dbf85dd2d9455c9eb32a0ba13b8597133f741b8ea785"
)
CORRECTED_CRATES_PREDICATE = "nonempty_max_version_and_nonempty_description"
payload_sha256 = base.payload_sha256


def build_revision(*, now: int | None = None) -> dict[str, Any]:
    parent_raw = json.loads(base.base._ordinary(PARENT).read_text(encoding="utf-8"))
    parent = v1.validate_design(parent_raw)
    if base.base.sha256(PARENT) != EXPECTED_PARENT_SHA256:
        raise RuntimeError("V2.52.14 R2 parent hash drifted")
    value = copy.deepcopy(parent)
    value["role"] = "v25214_candidate_preselection_protocol_design_r2"
    value["created_at_unix"] = int(time.time()) if now is None else int(now)
    value["parent_design"] = {
        "path": str(PARENT),
        "sha256": base.base.sha256(PARENT),
    }
    value["correction"] = {
        "field": "source_specs.single_authority_exact_record.selection_predicate",
        "old_predicate": "non_yanked_current_version_and_nonempty_description",
        "new_predicate": CORRECTED_CRATES_PREDICATE,
        "reason": "crates_io_list_snapshot_exposes_max_version_and_description_but_not_selected_version_yanked_state",
        "all_other_fields_and_authority_unchanged": True,
    }
    value["source_specs"]["single_authority_exact_record"][
        "selection_predicate"
    ] = CORRECTED_CRATES_PREDICATE
    value.pop("design_payload_sha256")
    value["design_payload_sha256"] = payload_sha256(value)
    return validate_revision(value)


def validate_revision(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("design_payload_sha256", None)
    correction = copied.get("correction") or {}
    source_specs = copied.get("source_specs") or {}
    authorization = copied.get("authorization") or {}
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != "v25214_candidate_preselection_protocol_design_r2"
        or copied.get("parent_design", {}).get("sha256") != EXPECTED_PARENT_SHA256
        or correction
        != {
            "field": "source_specs.single_authority_exact_record.selection_predicate",
            "old_predicate": "non_yanked_current_version_and_nonempty_description",
            "new_predicate": CORRECTED_CRATES_PREDICATE,
            "reason": "crates_io_list_snapshot_exposes_max_version_and_description_but_not_selected_version_yanked_state",
            "all_other_fields_and_authority_unchanged": True,
        }
        or source_specs.get("single_authority_exact_record", {}).get(
            "selection_predicate"
        )
        != CORRECTED_CRATES_PREDICATE
        or copied.get("sampling_strata") != list(v1.SAMPLING_STRATA)
        or copied.get("epistemic_risk_variables")
        != list(v1.EPISTEMIC_RISK_VARIABLES)
        or copied.get(
            "sampling_strata_are_not_epistemic_risk_estimates_or_benchmark_labels"
        )
        is not True
        or copied.get("sampling_contract", {}).get(
            "http_redirects_retries_and_conditional_refetches"
        )
        != 0
        or copied.get("separation_contract", {}).get(
            "A_M_Re_Yec_not_estimated_calibrated_routed_or_credited_by_this_gate"
        )
        is not True
        or authorization
        != {
            "deterministic_candidate_discovery_implementation_build_only": True,
            "public_index_snapshot_network_access": False,
            "real_identity_selection_or_population_freeze": False,
            "probe_runtime_integration_external_forward_or_activation": False,
            "runtime_compatibility_validator_relaxation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.14 R2 candidate design drifted")
    return copied


def main() -> None:
    value = build_revision()
    base.base.publish(ROOT / OUTPUT, value)
    print(json.dumps({"path": str(OUTPUT), "revision": "R2"}, sort_keys=True))


if __name__ == "__main__":
    main()
