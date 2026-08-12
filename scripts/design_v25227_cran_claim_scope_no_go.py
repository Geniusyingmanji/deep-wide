#!/usr/bin/env python3
"""Freeze the V2.52.27 same-endpoint claim-scope NO-GO decision."""

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
from scripts import audit_v25226_cran_semantic_transport_build as build_audit  # noqa: E402
from scripts import control_v25219_snapshot_population as old_control  # noqa: E402
from scripts import design_v25225_cran_semantic_transport as design  # noqa: E402


DATE = "20260812"
OUTPUT = Path(f"results/v25227_cran_claim_scope_no_go_v1_{DATE}.json")
SOURCE = Path("scripts/design_v25227_cran_claim_scope_no_go.py")
TEST = Path("tests/test_design_v25227_cran_claim_scope_no_go.py")
ATTEMPT_CLAIM = Path(
    "results/v25219_snapshot_population_attempt_claim_v1_20260812.json"
)
PREACTIVATION = Path(
    "results/v25219_snapshot_population_preactivation_audit_v1_20260812.json"
)
EXECUTION_START = Path(
    "results/v25219_snapshot_population_execution_start_v1_20260812.json"
)
NO_GO_RESULT = Path("results/v25219_snapshot_population_freeze_v1_20260812.json")
OLD_CONTROL_SOURCE = Path("scripts/control_v25219_snapshot_population.py")
OLD_CONTROL_TEST = Path("tests/test_control_v25219_snapshot_population.py")
OFFICIAL_EVIDENCE = Path(
    "results/v25221_cran_repository_format_evidence_v1_20260812.json"
)
SEMANTIC_DESIGN = design.OUTPUT
SEMANTIC_SOURCE = Path("src/deepwide_agent/v25226_cran_semantic_transport.py")
SEMANTIC_BUILD_AUDIT = build_audit.OUTPUT
FIXED_HASHES = {
    ATTEMPT_CLAIM: "815aa9bd1c29e6e128cde1e0cbdacf284cb6e7b6313213ae6cd753a35a1869fd",
    PREACTIVATION: "495453dec321687fef51318acf11a0e0f9a07502b3a45d10488578ed9ea5a0cc",
    EXECUTION_START: "5464e026b1d6bfadc05df69cc859c32d357b0ba3f09e454257b479d91f7648bb",
    NO_GO_RESULT: "d98abd021142f0f94b0afcf7f06ce4834c6337f04dbb51cccbd60fa5128617e1",
    OLD_CONTROL_SOURCE: "6c58d340d931663c13c9bd8cce490a3c3d566387fe550e2b576834682bfb4d68",
    OLD_CONTROL_TEST: "9c6851f4a54e5d3dbfd63a96f007e1a090e3c71cdf7b4c1aa5285bac5eadf139",
    OFFICIAL_EVIDENCE: "d3e106735d70f9c827a9727f37eb9ad5162c33d31da98d54fcb84d0990fa59b9",
    SEMANTIC_DESIGN: "d50633dbbe7b991533bf882f36072fc3e29f61ccf3655750c09596c024c4d50b",
    SEMANTIC_SOURCE: "5e3f160a015bf929b46b5d16207472c7aaa9e137a7a17aba0daaa13fcec5c639",
    SEMANTIC_BUILD_AUDIT: "78dab9fad93348ea5d3a244fddb9424ad43e2843ce858b30f0256b803ca7b0cb",
}
CRAN_ENDPOINT_SHA256 = (
    "93b3a9a765f3a0d1c89a73ab7f7ade5bfd49d2c6f9c5583a8c855ca21f6813e0"
)
payload_sha256 = base.payload_sha256


def _hash_barrier() -> bool:
    return all(base.base.sha256(path) == digest for path, digest in FIXED_HASHES.items())


def _parent_barrier() -> bool:
    if not _hash_barrier():
        return False
    claim = json.loads(base.base._ordinary(ATTEMPT_CLAIM).read_text(encoding="utf-8"))
    preactivation = old_control.validate_preactivation(
        json.loads(base.base._ordinary(PREACTIVATION).read_text(encoding="utf-8"))
    )
    result = json.loads(base.base._ordinary(NO_GO_RESULT).read_text(encoding="utf-8"))
    semantic_design = design.validate_design(
        json.loads(base.base._ordinary(SEMANTIC_DESIGN).read_text(encoding="utf-8"))
    )
    audit = build_audit.validate_audit(
        json.loads(
            base.base._ordinary(SEMANTIC_BUILD_AUDIT).read_text(encoding="utf-8")
        )
    )
    cran = result["batch_receipt"]["children"][
        "single_authority_multivalue_record"
    ]["transport_receipt"]
    return bool(
        claim["claim_created_before_public_snapshot_network_or_api_call"] is True
        and claim["claim_is_permanent_even_if_process_crashes_or_result_write_fails"]
        is True
        and claim["retry_refetch_backfill_replacement_or_second_batch_authorized"]
        is False
        and preactivation["audit_valid"] is True
        and preactivation["findings"] == []
        and preactivation["tests"]["expected"] == 47
        and preactivation["tests"]["observed"] == 47
        and preactivation["tests"]["passed"] is True
        and preactivation["checks"]["execution_start_and_result_surfaces_pristine"]
        is True
        and all(
            base.base._ordinary(path).is_file()
            for path in (ATTEMPT_CLAIM, EXECUTION_START, NO_GO_RESULT)
        )
        and result["status"] == "no_go"
        and result["public_snapshot_network_or_api_called"] is True
        and cran["url_sha256"] == CRAN_ENDPOINT_SHA256
        and cran["provider_attempt_count"] == 1
        and cran["retry_count"] == 0
        and semantic_design["fixed_endpoint"]["url_sha256"]
        == CRAN_ENDPOINT_SHA256
        and audit["audit_valid"] is True
        and audit["findings"] == []
        and audit["authorization"]["fresh_semantic_transport_protocol_design"]
        is True
        and audit["authorization"]["public_snapshot_network_access_or_execution_start"]
        is False
    )


def build_decision(*, now: int | None = None) -> dict[str, Any]:
    if not _parent_barrier():
        raise RuntimeError("V2.52.27 parent barrier failed")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25227_cran_same_endpoint_claim_scope_no_go",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "fixed_artifact_hashes": {
            str(path): base.base.sha256(path) for path in FIXED_HASHES
        },
        "same_endpoint_evidence": {
            "v25219_cran_url_sha256": CRAN_ENDPOINT_SHA256,
            "v25226_cran_url_sha256": CRAN_ENDPOINT_SHA256,
            "same_physical_endpoint": True,
            "v25219_provider_attempt_count": 1,
            "v25219_public_snapshot_network_or_api_called": True,
        },
        "historical_stage_evidence": {
            "frozen_preactivation_audit_valid": True,
            "frozen_preactivation_tests_expected": 47,
            "frozen_preactivation_tests_observed": 47,
            "frozen_preactivation_tests_passed": True,
            "frozen_preactivation_required_future_surfaces_pristine": True,
            "current_attempt_claim_surface_exists": True,
            "current_execution_start_surface_exists": True,
            "current_result_surface_exists": True,
            "rebuilding_old_preactivation_after_consumed_effect_is_stage_invalid": True,
            "current_old_control_suite_stage_sensitive_errors_observed": 3,
            "v25219_runner_semantic_tests_currently_passed": 13,
            "classification": "historical_preactivation_absence_assertion_after_authorized_effect",
            "v25227_regression": False,
        },
        "claim_scope": {
            "v25219_claim_is_permanent": True,
            "v25219_retry_refetch_backfill_replacement_or_second_batch_authorized": False,
            "new_version_or_namespace_does_not_change_same_endpoint_physical_effect": True,
            "another_GET_to_same_endpoint_would_be_refetch": True,
            "semantic_policy_change_does_not_retroactively_restore_effect_authority": True,
        },
        "decision": {
            "v25226_same_endpoint_effect": "no_go",
            "v25219_endpoint_refetch": False,
            "v25219_retry_resume_backfill_replacement_or_second_batch": False,
            "v25226_build_artifact_remains_valid_synthetic_evidence": True,
            "alternative_official_endpoint_or_surface_may_be_designed": True,
            "alternative_endpoint_network_access": False,
            "return_to_non_endpoint_reliability_work": True,
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "same_cran_endpoint_protocol_preactivation_or_execution_start": False,
            "alternative_endpoint_or_non_endpoint_design_only": True,
            "public_snapshot_network_access": False,
            "v25219_retry_refetch_backfill_replacement_or_second_batch": False,
            "real_identity_selection_or_population_freeze": False,
            "probe_runtime_integration_external_forward_or_activation": False,
            "runtime_compatibility_validator_relaxation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    value["decision_payload_sha256"] = payload_sha256(value)
    return validate_decision(value)


def validate_decision(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("decision_payload_sha256", None)
    expected_top = {
        "artifact_version",
        "role",
        "created_at_unix",
        "fixed_artifact_hashes",
        "same_endpoint_evidence",
        "historical_stage_evidence",
        "claim_scope",
        "decision",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "network_model_search_fetch_evaluator_benchmark_or_api_called",
        "entropy_or_information_gain_assigns_signed_credit",
        "authorization",
        "decision_payload_sha256",
    }
    expected_endpoint = {
        "v25219_cran_url_sha256": CRAN_ENDPOINT_SHA256,
        "v25226_cran_url_sha256": CRAN_ENDPOINT_SHA256,
        "same_physical_endpoint": True,
        "v25219_provider_attempt_count": 1,
        "v25219_public_snapshot_network_or_api_called": True,
    }
    expected_scope = {
        "v25219_claim_is_permanent": True,
        "v25219_retry_refetch_backfill_replacement_or_second_batch_authorized": False,
        "new_version_or_namespace_does_not_change_same_endpoint_physical_effect": True,
        "another_GET_to_same_endpoint_would_be_refetch": True,
        "semantic_policy_change_does_not_retroactively_restore_effect_authority": True,
    }
    expected_stage = {
        "frozen_preactivation_audit_valid": True,
        "frozen_preactivation_tests_expected": 47,
        "frozen_preactivation_tests_observed": 47,
        "frozen_preactivation_tests_passed": True,
        "frozen_preactivation_required_future_surfaces_pristine": True,
        "current_attempt_claim_surface_exists": True,
        "current_execution_start_surface_exists": True,
        "current_result_surface_exists": True,
        "rebuilding_old_preactivation_after_consumed_effect_is_stage_invalid": True,
        "current_old_control_suite_stage_sensitive_errors_observed": 3,
        "v25219_runner_semantic_tests_currently_passed": 13,
        "classification": "historical_preactivation_absence_assertion_after_authorized_effect",
        "v25227_regression": False,
    }
    expected_decision = {
        "v25226_same_endpoint_effect": "no_go",
        "v25219_endpoint_refetch": False,
        "v25219_retry_resume_backfill_replacement_or_second_batch": False,
        "v25226_build_artifact_remains_valid_synthetic_evidence": True,
        "alternative_official_endpoint_or_surface_may_be_designed": True,
        "alternative_endpoint_network_access": False,
        "return_to_non_endpoint_reliability_work": True,
    }
    expected_authorization = {
        "same_cran_endpoint_protocol_preactivation_or_execution_start": False,
        "alternative_endpoint_or_non_endpoint_design_only": True,
        "public_snapshot_network_access": False,
        "v25219_retry_refetch_backfill_replacement_or_second_batch": False,
        "real_identity_selection_or_population_freeze": False,
        "probe_runtime_integration_external_forward_or_activation": False,
        "runtime_compatibility_validator_relaxation_or_prediction_change": False,
        "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
    }
    if (
        set(copied) != expected_top
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25227_cran_same_endpoint_claim_scope_no_go"
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied.get("created_at_unix") < 0
        or copied.get("fixed_artifact_hashes")
        != {str(path): digest for path, digest in FIXED_HASHES.items()}
        or copied.get("same_endpoint_evidence") != expected_endpoint
        or copied.get("historical_stage_evidence") != expected_stage
        or copied.get("claim_scope") != expected_scope
        or copied.get("decision") != expected_decision
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or copied.get("authorization") != expected_authorization
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.27 claim-scope decision drifted")
    return copied


def main() -> None:
    value = build_decision()
    base.base.publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "same_endpoint_effect": value["decision"][
                    "v25226_same_endpoint_effect"
                ],
                "network_authorized": value["authorization"][
                    "public_snapshot_network_access"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
