#!/usr/bin/env python3
"""Freeze a no-model candidate-preselection protocol for V2.52.14."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25210_receipt_disposition_observer_build as base  # noqa: E402
from scripts import audit_v25213_population_selection as selector  # noqa: E402
from scripts import audit_v25213_population_selector_build as selector_audit  # noqa: E402


DATE = "20260812"
OUTPUT = Path(f"results/v25214_candidate_preselection_protocol_design_v1_{DATE}.json")
SOURCE = Path("scripts/design_v25214_candidate_preselection_protocol.py")
TEST = Path("tests/test_design_v25214_candidate_preselection_protocol.py")
PARENT_AUDIT = selector_audit.OUTPUT
EXPECTED_PARENT_AUDIT_SHA256 = (
    "7a052cb9c2d976862701167b58047beb53d7d05f18b00a33fa2f125629b93154"
)
SAMPLING_STRATA = selector.RISK_STRATA
EPISTEMIC_RISK_VARIABLES = (
    "hidden_anchor_A",
    "unseen_mass_M",
    "row_eligibility_Re",
    "cell_value_uncertainty_Yec",
)
SOURCE_SPECS = {
    "single_authority_exact_record": {
        "index": "crates_io_public_crates_index_snapshot",
        "identity_type": "crate_name",
        "selection_predicate": "non_yanked_current_version_and_nonempty_description",
        "topology": "single_canonical_registry_record",
    },
    "single_authority_multivalue_record": {
        "index": "cran_public_packages_index_snapshot",
        "identity_type": "package_name",
        "selection_predicate": "nonempty_license_and_system_requirements_or_suggests",
        "topology": "single_registry_record_with_multivalue_fields",
    },
    "same_identity_multipage_record": {
        "index": "crossref_public_works_snapshot",
        "identity_type": "doi",
        "selection_predicate": "doi_title_publisher_and_container_title_nonempty",
        "topology": "registry_record_plus_publisher_landing_page",
    },
    "sparse_ambiguous_open_web_record": {
        "index": "pypi_public_simple_index_snapshot",
        "identity_type": "project_name",
        "selection_predicate": "normalized_name_length_3_to_8_and_valid_pep503_project_anchor",
        "topology": "short_visible_identity_with_open_web_name_collision_risk",
    },
}
TASKS_PER_STRATUM = selector.TASKS_PER_STRATUM
TASK_COUNT = selector.TASK_COUNT
OVERSAMPLE_PER_STRATUM = 64
payload_sha256 = base.payload_sha256


def _parent_barrier() -> bool:
    raw = json.loads(base.base._ordinary(PARENT_AUDIT).read_text(encoding="utf-8"))
    value = selector_audit.validate_audit(raw)
    authorization = value["authorization"]
    return bool(
        base.base.sha256(PARENT_AUDIT) == EXPECTED_PARENT_AUDIT_SHA256
        and value["audit_valid"] is True
        and value["findings"] == []
        and value["tests"]["expected"] == 23
        and value["tests"]["observed"] == 23
        and authorization["candidate_preselection_protocol_design"] is True
        and authorization["candidate_preselection_network_or_external_access"] is False
        and authorization["real_identity_selection_or_population_freeze"] is False
        and authorization[
            "probe_runtime_integration_external_forward_or_activation"
        ]
        is False
    )


def deterministic_rank(
    stratum: str,
    identity: str,
    *,
    snapshot_sha256: str,
) -> str:
    if stratum not in SAMPLING_STRATA:
        raise ValueError("V2.52.14 sampling stratum drifted")
    normalized = "-".join(str(identity).casefold().split())
    if not normalized or len(normalized) > 100:
        raise ValueError("V2.52.14 candidate identity drifted")
    if (
        not isinstance(snapshot_sha256, str)
        or len(snapshot_sha256) != 64
        or any(character not in "0123456789abcdef" for character in snapshot_sha256)
    ):
        raise ValueError("V2.52.14 snapshot hash drifted")
    return hashlib.sha256(
        f"v25214\0{stratum}\0{snapshot_sha256}\0{normalized}".encode()
    ).hexdigest()


def select_candidates(
    candidates: Mapping[str, Sequence[str]],
    *,
    snapshot_hashes: Mapping[str, str],
) -> dict[str, list[str]]:
    if set(candidates) != set(SAMPLING_STRATA) or set(snapshot_hashes) != set(
        SAMPLING_STRATA
    ):
        raise RuntimeError("V2.52.14 candidate or snapshot stratum drifted")
    output: dict[str, list[str]] = {}
    global_seen: set[str] = set()
    for stratum in SAMPLING_STRATA:
        normalized = [
            "-".join(str(value).casefold().split())
            for value in candidates[stratum]
        ]
        if (
            len(normalized) < OVERSAMPLE_PER_STRATUM
            or len(set(normalized)) != len(normalized)
            or any(not value or len(value) > 100 for value in normalized)
        ):
            raise RuntimeError("V2.52.14 oversample candidate pool drifted")
        ranked = sorted(
            normalized,
            key=lambda identity: (
                deterministic_rank(
                    stratum,
                    identity,
                    snapshot_sha256=snapshot_hashes[stratum],
                ),
                identity,
            ),
        )
        selected = ranked[:TASKS_PER_STRATUM]
        if global_seen.intersection(selected):
            raise RuntimeError("V2.52.14 cross-stratum identity collision")
        global_seen.update(selected)
        output[stratum] = selected
    selector._validate_candidates(output)
    return output


def build_design(*, now: int | None = None) -> dict[str, Any]:
    if not _parent_barrier():
        raise RuntimeError("V2.52.14 parent selector audit barrier failed")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25214_candidate_preselection_protocol_design",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_selector_build_audit": {
            "path": str(PARENT_AUDIT),
            "sha256": base.base.sha256(PARENT_AUDIT),
        },
        "sampling_strata": list(SAMPLING_STRATA),
        "epistemic_risk_variables": list(EPISTEMIC_RISK_VARIABLES),
        "sampling_strata_are_not_epistemic_risk_estimates_or_benchmark_labels": True,
        "source_specs": copy.deepcopy(SOURCE_SPECS),
        "sampling_contract": {
            "tasks_per_stratum": TASKS_PER_STRATUM,
            "task_count": TASK_COUNT,
            "minimum_predicate_valid_oversample_per_stratum": OVERSAMPLE_PER_STRATUM,
            "one_get_only_per_frozen_public_index_snapshot": True,
            "http_redirects_retries_and_conditional_refetches": 0,
            "snapshot_bytes_sha256_and_retrieval_receipt_required": True,
            "snapshot_selected_before_identity_history_scan": True,
            "selection_order": "sha256_v25214_stratum_snapshot_identity_then_identity",
            "manual_reordering_replacement_or_selective_backfill": False,
            "predicate_may_read_only_public_index_record_fields": True,
            "predicate_may_not_read_model_prediction_evaluator_quality_or_benchmark": True,
            "cross_stratum_identity_collision_fails_closed": True,
        },
        "separation_contract": {
            "candidate_discovery_may_persist_snapshot_hash_counts_and_transport_status_only": True,
            "candidate_discovery_artifact_persists_no_identity_plaintext_or_item_hash": True,
            "selector_receives_candidates_in_memory_then_persists_aggregate_only": True,
            "selector_proves_repository_history_disjointness_not_candidate_provenance": True,
            "risk_stratum_removed_before_runtime_task_vector": True,
            "runtime_boundary_future_exactly_opaque_id_and_visible_question": True,
            "A_M_Re_Yec_not_estimated_calibrated_routed_or_credited_by_this_gate": True,
        },
        "stop_rules": {
            "transport_or_snapshot_failure": "no_population_selection_and_no_refetch",
            "fewer_than_64_predicate_valid_candidates_in_any_stratum": "no_population_selection",
            "history_hit_after_deterministic_selection": "entire_population_no_go_no_backfill",
            "identity_collision_across_strata": "entire_population_no_go",
            "model_search_api_evaluator_or_quality_access": "quarantine_as_invalid",
            "manual_identity_choice_after_snapshot_read": "quarantine_as_invalid",
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "deterministic_candidate_discovery_implementation_build_only": True,
            "public_index_snapshot_network_access": False,
            "real_identity_selection_or_population_freeze": False,
            "probe_runtime_integration_external_forward_or_activation": False,
            "runtime_compatibility_validator_relaxation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    value["design_payload_sha256"] = payload_sha256(value)
    return validate_design(value)


def validate_design(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("design_payload_sha256", None)
    sampling = copied.get("sampling_contract") or {}
    separation = copied.get("separation_contract") or {}
    authorization = copied.get("authorization") or {}
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != "v25214_candidate_preselection_protocol_design"
        or copied.get("parent_selector_build_audit", {}).get("sha256")
        != EXPECTED_PARENT_AUDIT_SHA256
        or copied.get("sampling_strata") != list(SAMPLING_STRATA)
        or copied.get("epistemic_risk_variables") != list(EPISTEMIC_RISK_VARIABLES)
        or copied.get(
            "sampling_strata_are_not_epistemic_risk_estimates_or_benchmark_labels"
        )
        is not True
        or copied.get("source_specs") != SOURCE_SPECS
        or sampling.get("tasks_per_stratum") != TASKS_PER_STRATUM
        or sampling.get("task_count") != TASK_COUNT
        or sampling.get("minimum_predicate_valid_oversample_per_stratum")
        != OVERSAMPLE_PER_STRATUM
        or sampling.get("http_redirects_retries_and_conditional_refetches") != 0
        or sampling.get("manual_reordering_replacement_or_selective_backfill")
        is not False
        or separation.get("risk_stratum_removed_before_runtime_task_vector") is not True
        or separation.get("A_M_Re_Yec_not_estimated_calibrated_routed_or_credited_by_this_gate")
        is not True
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
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
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.14 candidate preselection design drifted")
    return copied


def main() -> None:
    value = build_design()
    base.base.publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "task_count": value["sampling_contract"]["task_count"],
                "discovery_build_only": value["authorization"][
                    "deterministic_candidate_discovery_implementation_build_only"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
