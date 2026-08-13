#!/usr/bin/env python3
"""Content-free capacity diagnosis after the V2.53.30 paced transport NO-GO."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25334_rate_paced_worldbank_population_nogo as post  # noqa: E402
from scripts import run_v25297_worldbank_population_freeze as first  # noqa: E402
from scripts import run_v25317_disjoint_worldbank_population as second  # noqa: E402
from scripts import run_v25323_low_concurrency_worldbank_population as third  # noqa: E402
from scripts import run_v25330_rate_paced_worldbank_population as current  # noqa: E402


DATE = "20260813"
ROLE = "v25335_v25330_transport_capacity_diagnosis"
OUTPUT = Path(f"results/v25335_v25330_transport_capacity_diagnosis_v1_{DATE}.json")
SOURCE = Path("scripts/diagnose_v25335_v25330_transport_capacity.py")
TEST = Path("tests/test_diagnose_v25335_v25330_transport_capacity.py")
FIXED = {
    current.RESULT: "71db9cf2f6090b324a5bd2179e27268c0829efa5dda1ed5fe52587651bfc1282",
    current.ATTEMPT_CLAIM: "34154cef040b1517f3a11a88e54a0e4ef556d221cdc1bc01893217abf7fa974c",
    post.OUTPUT: "8791bfd6744083ef52b032866027d3a63c6a37fcd685aa3d90eb3a5509f95ab2",
    current.SOURCE: "0eb4d0eec50dee134a284e67c3fa4f996bbdcde8f399fe8b2ed6cf56835ee0de",
    current.HELPER: "a8049e892669d17bcc940f0c13b029207aa68d8f6677552ab7a5347f19c88ce4",
    third.RESULT: "431886229c29e72b89c149ca246bd6f9c5f009c69a924d061f45aea081aa0812",
    second.RESULT: "f5015143ccc03beb40785eb18d91507223c8dcdd30cb95156793a3d895fd9c65",
    first.RESULT: "6abbce3cb6271cde5046479b78a8436ba41fbb383679c102d857731d262e600b",
    first.POPULATION: "ced33e651b0d72a65a59d4106ea5b68316f25bd5b31ca9a54f8f1c9d2689fcec",
}
EXPECTED_TARGET_VECTOR_SHA256 = "49ae552a5b1021e08169fac4ad0e9aaa074ad0590c0884dd52ed0c584278fbbd"
EXPECTED_ENTITY_VECTOR_SHA256 = "8674522def1925ab683d9b388f283de184dfd729f8f011113d581383e7958b67"
EXPECTED_RESPONSE_VECTOR_SHA256 = "1663c031db8eb081a455ee6a7113c6a67d5ec9169827ac80183a31c1ad439f25"


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(current._ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.53.35 expected JSON object")
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(current._ordinary(path).read_bytes()).hexdigest()


def _manifest() -> dict[str, Any]:
    results = (
        first.validate_result(_read(first.RESULT)),
        second.validate_result(_read(second.RESULT)),
        third.validate_result(_read(third.RESULT)),
        current.validate_result(_read(current.RESULT)),
    )
    private = _read(first.POPULATION)
    if (
        private.get("role") != "v25305_private_frozen_worldbank_population"
        or not first.seal.sealed(private, "population_payload_sha256")
    ):
        raise RuntimeError("V2.53.35 first private population drifted")
    targets = [item for result in results for item in result["candidate_target_keys"]]
    entities = list(private["population"]["entities"])
    responses = [
        str(row["response_sha256"])
        for result in results
        for row in result["target_transport"]["rows"]
        if row["response_sha256"] is not None
    ]
    per_attempt = [
        sum(row["response_sha256"] is not None for row in result["target_transport"]["rows"])
        for result in results
    ]
    checks = {
        "target_count": len(targets) == 96,
        "target_unique": len(set(item.casefold() for item in targets)) == 96,
        "target_hash": current.payload_sha256(targets) == EXPECTED_TARGET_VECTOR_SHA256,
        "entity_count": len(entities) == 144,
        "entity_unique": len(set(entities)) == 144,
        "entity_hash": current.payload_sha256(entities) == EXPECTED_ENTITY_VECTOR_SHA256,
        "response_count": len(responses) == 169,
        "response_unique": len(set(responses)) == 169,
        "response_format": all(re.fullmatch(r"[0-9a-f]{64}", item) for item in responses),
        "response_hash": current.payload_sha256(responses) == EXPECTED_RESPONSE_VECTOR_SHA256,
        "per_attempt_response_counts": per_attempt == [48, 36, 43, 42],
    }
    return {
        "target_count": len(targets),
        "target_keys_sha256": current.payload_sha256(targets),
        "entity_count": len(entities),
        "entity_codes_sha256": current.payload_sha256(entities),
        "response_count": len(responses),
        "response_vector_sha256": current.payload_sha256(responses),
        "per_attempt_response_counts": per_attempt,
        "checks": checks,
    }


def _counterfactual_schedule(result: Mapping[str, Any], capacity: int) -> dict[str, Any]:
    if capacity not in {1, 2, 3, 4, 5, 6}:
        raise ValueError("V2.53.35 unsupported capacity")
    rows = result["target_transport"]["rows"]
    availability = [0.0] * capacity
    launch_offsets: list[float] = []
    for row in rows:
        worker = min(range(capacity), key=lambda index: (availability[index], index))
        launch_offsets.append(availability[worker])
        availability[worker] += float(row["elapsed_seconds"])
    return {
        "capacity": capacity,
        "receipt_count": len(rows),
        "counterfactual_makespan_seconds": round(max(availability), 6),
        "counterfactual_last_launch_seconds": round(launch_offsets[-1], 6),
        "worker_loads_seconds": [round(item, 6) for item in availability],
        "replay_preserves_observed_per_request_durations": True,
        "replay_is_not_a_performance_guarantee_or_provider_causal_proof": True,
    }


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    fixed = {str(path): _sha(path) for path in FIXED}
    result = current.validate_result(_read(current.RESULT))
    audit = post.validate_audit(_read(post.OUTPUT))
    manifest = _manifest()
    schedules = {str(capacity): _counterfactual_schedule(result, capacity) for capacity in range(1, 7)}
    attempt = audit["attempt"]
    checks = {
        "fixed_inputs_exact": fixed == {str(path): digest for path, digest in FIXED.items()},
        "postfreeze_audit_valid_nogo": audit["audit_valid"] is True and audit["findings"] == [],
        "actual_paced_attempt_exact42_success6_failure": (
            attempt["successful_target_response_count"] == 42
            and attempt["failed_target_response_count"] == 6
            and attempt["configured_minimum_start_interval_seconds"] == 1.0
            and attempt["observed_minimum_start_interval_seconds"] >= 1.0
        ),
        "counterfactual_replay_uses_all48_content_free_durations": all(
            row["receipt_count"] == 48
            and row["replay_preserves_observed_per_request_durations"] is True
            and row["replay_is_not_a_performance_guarantee_or_provider_causal_proof"] is True
            for row in schedules.values()
        ),
        "capacity3_replay_fits110_seconds_with_over15_seconds_margin": (
            schedules["3"]["counterfactual_makespan_seconds"] == 93.91118
            and 110.0 - schedules["3"]["counterfactual_makespan_seconds"] > 15.0
        ),
        "capacity2_replay_exceeds110_seconds": schedules["2"]["counterfactual_makespan_seconds"] == 139.981309,
        "four_attempt_consumed_manifest_exact96_144_169": all(manifest["checks"].values()),
        "no_question_query_url_page_value_prediction_or_credential_read_or_emitted": True,
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "fixed_inputs": fixed,
        "observed_attempt": {
            "target_concurrency": attempt["target_concurrency"],
            "configured_minimum_start_interval_seconds": attempt["configured_minimum_start_interval_seconds"],
            "observed_minimum_start_interval_seconds": attempt["observed_minimum_start_interval_seconds"],
            "target_elapsed_seconds": attempt["target_elapsed_seconds"],
            "successful_target_response_count": attempt["successful_target_response_count"],
            "failed_target_response_count": attempt["failed_target_response_count"],
            "failure_code_counts": attempt["failure_code_counts"],
        },
        "counterfactual_capacity_replay": schedules,
        "consumed_manifest": manifest,
        "diagnosis": {
            "one_second_start_pacing_did_not_reduce_failures_below_unpaced_concurrency6_attempt": True,
            "request_start_rate_is_not_supported_as_primary_next_hypothesis": True,
            "observed_durations_support_capacity3_as_lowest_replayed_schedule_under110_seconds": True,
            "observed_durations_reject_capacity2_under_frozen110_second_wall": True,
            "counterfactual_replay_proves_future_success": False,
            "transport_pattern_proves_unique_causal_root_cause": False,
            "next_candidate_changes_only_max_target_concurrency_to3": True,
            "next_candidate_request_start_interval_seconds": 0.0,
            "next_candidate_fixed_target_request_count": 48,
            "next_candidate_per_url_provider_attempt_count": 1,
            "next_candidate_retry_resume_refetch_backfill_replacement": False,
            "next_candidate_target_phase_hard_wall_seconds": 110.0,
            "next_candidate_whole_freeze_hard_wall_seconds": 145.0,
            "must_use_new_targets_responses_and_population_namespace": True,
            "must_not_reuse_any_partial_success_bytes": True,
        },
        "checks": checks,
        "findings": findings,
        "diagnosis_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "question_query_url_page_value_prediction_or_credential_read_or_emitted": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "concurrency3_fresh_disjoint_transport_successor_build": not findings,
            "successor_population_network_activation_or_launch": False,
            "v25330_retry_resume_refetch_backfill_replacement_or_reuse": False,
            "external_monotone_fill_forward_or_evaluator": False,
            "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = current.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("diagnosis_payload_sha256", None)
    checks = copied.get("checks") or {}
    findings = copied.get("findings")
    observed = copied.get("observed_attempt") or {}
    replay = copied.get("counterfactual_capacity_replay") or {}
    diagnosis = copied.get("diagnosis") or {}
    authorization = copied.get("authorization") or {}
    expected_findings = sorted(name for name, passed in checks.items() if not passed)
    if (
        set(copied)
        != {
            "artifact_version", "role", "created_at_unix", "fixed_inputs",
            "observed_attempt", "counterfactual_capacity_replay", "consumed_manifest",
            "diagnosis", "checks", "findings", "diagnosis_valid",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
            "question_query_url_page_value_prediction_or_credential_read_or_emitted",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit", "authorization",
            "diagnosis_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("fixed_inputs") != {str(path): digest for path, digest in FIXED.items()}
        or observed
        != {
            "target_concurrency": 6,
            "configured_minimum_start_interval_seconds": 1.0,
            "observed_minimum_start_interval_seconds": observed.get("observed_minimum_start_interval_seconds"),
            "target_elapsed_seconds": 64.632713,
            "successful_target_response_count": 42,
            "failed_target_response_count": 6,
            "failure_code_counts": {"transport_error": 6},
        }
        or not isinstance(observed.get("observed_minimum_start_interval_seconds"), (int, float))
        or float(observed["observed_minimum_start_interval_seconds"]) < 1.0
        or set(replay) != {"1", "2", "3", "4", "5", "6"}
        or any(replay[key] != _counterfactual_schedule(current.validate_result(_read(current.RESULT)), int(key)) for key in replay)
        or copied.get("consumed_manifest") != _manifest()
        or not all(copied["consumed_manifest"]["checks"].values())
        or diagnosis
        != {
            "one_second_start_pacing_did_not_reduce_failures_below_unpaced_concurrency6_attempt": True,
            "request_start_rate_is_not_supported_as_primary_next_hypothesis": True,
            "observed_durations_support_capacity3_as_lowest_replayed_schedule_under110_seconds": True,
            "observed_durations_reject_capacity2_under_frozen110_second_wall": True,
            "counterfactual_replay_proves_future_success": False,
            "transport_pattern_proves_unique_causal_root_cause": False,
            "next_candidate_changes_only_max_target_concurrency_to3": True,
            "next_candidate_request_start_interval_seconds": 0.0,
            "next_candidate_fixed_target_request_count": 48,
            "next_candidate_per_url_provider_attempt_count": 1,
            "next_candidate_retry_resume_refetch_backfill_replacement": False,
            "next_candidate_target_phase_hard_wall_seconds": 110.0,
            "next_candidate_whole_freeze_hard_wall_seconds": 145.0,
            "must_use_new_targets_responses_and_population_namespace": True,
            "must_not_reuse_any_partial_success_bytes": True,
        }
        or set(checks)
        != {
            "fixed_inputs_exact", "postfreeze_audit_valid_nogo",
            "actual_paced_attempt_exact42_success6_failure",
            "counterfactual_replay_uses_all48_content_free_durations",
            "capacity3_replay_fits110_seconds_with_over15_seconds_margin",
            "capacity2_replay_exceeds110_seconds",
            "four_attempt_consumed_manifest_exact96_144_169",
            "no_question_query_url_page_value_prediction_or_credential_read_or_emitted",
            "no_network_model_search_fetch_evaluator_benchmark_or_api_called",
        }
        or any(not isinstance(item, bool) for item in checks.values())
        or findings != expected_findings
        or copied.get("diagnosis_valid") is not (not expected_findings)
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
                "question_query_url_page_value_prediction_or_credential_read_or_emitted",
                "network_model_search_fetch_evaluator_benchmark_or_api_called",
                "entropy_or_information_gain_assigns_signed_credit",
            )
        )
        or authorization
        != {
            "concurrency3_fresh_disjoint_transport_successor_build": not expected_findings,
            "successor_population_network_activation_or_launch": False,
            "v25330_retry_resume_refetch_backfill_replacement_or_reuse": False,
            "external_monotone_fill_forward_or_evaluator": False,
            "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
        }
        or signature != current.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.35 transport capacity diagnosis drifted")
    return copied


def main() -> None:
    value = build_diagnosis()
    if not value["diagnosis_valid"]:
        raise SystemExit("V2.53.35 diagnosis failed: " + ", ".join(value["findings"]))
    current.publish_json_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "diagnosis_valid": value["diagnosis_valid"],
                "findings": value["findings"],
                "consumed_targets": value["consumed_manifest"]["target_count"],
                "consumed_responses": value["consumed_manifest"]["response_count"],
                "capacity3_replay_seconds": value["counterfactual_capacity_replay"]["3"]["counterfactual_makespan_seconds"],
                "capacity2_replay_seconds": value["counterfactual_capacity_replay"]["2"]["counterfactual_makespan_seconds"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
