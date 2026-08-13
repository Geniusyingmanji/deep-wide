#!/usr/bin/env python3
"""Content-free scheduler diagnosis after the V2.53.23 transport NO-GO."""

from __future__ import annotations

import ast
import copy
import json
import os
import re
import statistics
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

from scripts import audit_v25327_low_concurrency_worldbank_population_nogo as post  # noqa: E402
from scripts import run_v25297_worldbank_population_freeze as first  # noqa: E402
from scripts import run_v25317_disjoint_worldbank_population as second  # noqa: E402
from scripts import run_v25323_low_concurrency_worldbank_population as current  # noqa: E402


DATE = "20260813"
ROLE = "v25328_v25323_transport_scheduler_diagnosis"
OUTPUT = Path(f"results/v25328_v25323_transport_scheduler_diagnosis_v1_{DATE}.json")
SOURCE = Path("scripts/diagnose_v25328_v25323_transport_scheduler.py")
TEST = Path("tests/test_diagnose_v25328_v25323_transport_scheduler.py")
FIXED = {
    current.RESULT: "431886229c29e72b89c149ca246bd6f9c5f009c69a924d061f45aea081aa0812",
    current.ATTEMPT_CLAIM: "6eec78ead82e930c1825ccd1c7dc79a8b35e48aa5e1edcf656f0a588be6c32d7",
    post.OUTPUT: "70b928d833b2b18a168d94665515c1ec229a0be3dea77a61c975f9a154540b9a",
    current.SOURCE: "9871626a6121aca242f0e99cbea405ff5d785e8e686a3a7570f367081e1543dd",
    current.HELPER: "a8049e892669d17bcc940f0c13b029207aa68d8f6677552ab7a5347f19c88ce4",
    second.RESULT: "f5015143ccc03beb40785eb18d91507223c8dcdd30cb95156793a3d895fd9c65",
    first.RESULT: "6abbce3cb6271cde5046479b78a8436ba41fbb383679c102d857731d262e600b",
    first.POPULATION: "ced33e651b0d72a65a59d4106ea5b68316f25bd5b31ca9a54f8f1c9d2689fcec",
}
EXPECTED_TARGET_VECTOR_SHA256 = (
    "61ef9ffe36666f043412723b8acd2c4dfbcb7ba32a1b1c7626369237829ed962"
)
EXPECTED_ENTITY_VECTOR_SHA256 = (
    "8674522def1925ab683d9b388f283de184dfd729f8f011113d581383e7958b67"
)
EXPECTED_RESPONSE_VECTOR_SHA256 = (
    "c8e38ffcaf046e7e57e133309275fc8696af777f4c0c922925c9736a07cba937"
)


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(current._ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.53.28 expected JSON object")
    return value


def _attempt(result: Mapping[str, Any]) -> dict[str, Any]:
    rows = result["target_transport"]["rows"]
    successful = [row for row in rows if row["outcome"] == "success"]
    failed = [row for row in rows if row["outcome"] == "failure"]
    success_elapsed = [float(row["elapsed_seconds"]) for row in successful]
    failure_elapsed = [float(row["elapsed_seconds"]) for row in failed]
    return {
        "target_concurrency": int(result["target_transport"]["concurrency"]),
        "target_receipt_count": len(rows),
        "successful_target_response_count": len(successful),
        "failed_target_response_count": len(failed),
        "failure_code_counts": dict(
            sorted(Counter(row["failure_code"] for row in failed).items())
        ),
        "failed_ordinal_pages": sorted(
            [int(row["candidate_ordinal"]), int(row["page"])] for row in failed
        ),
        "success_elapsed_seconds": {
            "minimum": min(success_elapsed),
            "median": statistics.median(success_elapsed),
            "maximum": max(success_elapsed),
        },
        "failure_elapsed_seconds": {
            "minimum": min(failure_elapsed),
            "median": statistics.median(failure_elapsed),
            "maximum": max(failure_elapsed),
        },
    }


def _manifest() -> dict[str, Any]:
    first_result = first.validate_result(_read(first.RESULT))
    second_result = second.validate_result(_read(second.RESULT))
    current_result = current.validate_result(_read(current.RESULT))
    private = _read(first.POPULATION)
    if (
        private.get("role") != "v25305_private_frozen_worldbank_population"
        or not first.seal.sealed(private, "population_payload_sha256")
    ):
        raise RuntimeError("V2.53.28 first private population drifted")
    targets = [
        *first_result["candidate_target_keys"],
        *second_result["candidate_target_keys"],
        *current_result["candidate_target_keys"],
    ]
    entities = list(private["population"]["entities"])
    responses = [
        str(row["response_sha256"])
        for result in (first_result, second_result, current_result)
        for row in result["target_transport"]["rows"]
        if row["response_sha256"] is not None
    ]
    checks = {
        "target_count": len(targets) == 72,
        "target_unique": len(set(item.casefold() for item in targets)) == 72,
        "target_hash": first.payload_sha256(targets)
        == EXPECTED_TARGET_VECTOR_SHA256,
        "entity_count": len(entities) == 144,
        "entity_unique": len(set(entities)) == 144,
        "entity_hash": first.payload_sha256(entities)
        == EXPECTED_ENTITY_VECTOR_SHA256,
        "response_count": len(responses) == 127,
        "response_unique": len(set(responses)) == 127,
        "response_format": all(
            re.fullmatch(r"[0-9a-f]{64}", item) is not None
            for item in responses
        ),
        "response_hash": first.payload_sha256(responses)
        == EXPECTED_RESPONSE_VECTOR_SHA256,
        "per_attempt_response_counts": [
            sum(
                row["response_sha256"] is not None
                for row in result["target_transport"]["rows"]
            )
            for result in (first_result, second_result, current_result)
        ]
        == [48, 36, 43],
    }
    return {
        "target_count": len(targets),
        "target_keys_sha256": first.payload_sha256(targets),
        "entity_count": len(entities),
        "entity_codes_sha256": first.payload_sha256(entities),
        "response_count": len(responses),
        "response_vector_sha256": first.payload_sha256(responses),
        "per_attempt_response_counts": [48, 36, 43],
        "checks": checks,
    }


def _static_barrier() -> dict[str, bool]:
    source = current._ordinary(current.SOURCE).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(current.SOURCE))
    request = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_request_target_pages"
    )
    text = ast.get_source_segment(source, request) or ""
    helper = current._ordinary(current.HELPER).read_text(encoding="utf-8")
    return {
        "current_executor_concurrency_exact6": (
            current.TARGET_CONCURRENCY == 6
            and "ThreadPoolExecutor(max_workers=TARGET_CONCURRENCY)" in text
        ),
        "current_submits_all48_without_launch_spacing": (
            "futures = {" in text
            and "executor.submit(" in text
            and "time.sleep(" not in text
            and "request_start_interval" not in text.casefold()
        ),
        "work_order_is_target_then_page": (
            "for index, target in enumerate(targets, 1)" in text
            and "for page in (1, 2)" in text
        ),
        "one_provider_attempt_per_url_no_retry": (
            "provider_attempt_count=attempted" in helper
            and "allow_redirects=False" in helper
            and "max_retries" not in helper
        ),
    }


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    if any(base_sha(path) != digest for path, digest in FIXED.items()):
        raise RuntimeError("V2.53.28 fixed input hash drifted")
    previous = second.validate_result(_read(second.RESULT))
    present = current.validate_result(_read(current.RESULT))
    audit = post.validate_audit(_read(post.OUTPUT))
    before = _attempt(previous)
    after = _attempt(present)
    manifest = _manifest()
    static = _static_barrier()
    first42 = [
        row
        for row in present["target_transport"]["rows"]
        if int(row["candidate_ordinal"]) <= 21
    ]
    last6 = [
        row
        for row in present["target_transport"]["rows"]
        if int(row["candidate_ordinal"]) >= 22
    ]
    checks = {
        "fixed_inputs_exact": True,
        "frozen_result_and_postaudit_valid_nogo": (
            present["decision"] == "no_go"
            and present["failure_code"] == "target_transport_or_hard_wall"
            and audit["audit_valid"] is True
            and audit["findings"] == []
        ),
        "effect_count_exact_one_catalog_plus48_target": (
            present["effect_accounting"]["catalog_provider_attempt_count"] == 1
            and present["effect_accounting"]["target_provider_attempt_count"] == 48
        ),
        "concurrency12_to6_failure12_to5_exact": (
            before["target_concurrency"] == 12
            and before["failed_target_response_count"] == 12
            and after["target_concurrency"] == 6
            and after["failed_target_response_count"] == 5
        ),
        "first42_work_items_all_succeed": len(first42) == 42
        and all(row["outcome"] == "success" for row in first42),
        "last6_work_items_contain_exact5_socket_window_failures": (
            len(last6) == 6
            and sum(row["outcome"] == "failure" for row in last6) == 5
            and all(
                row["failure_code"] == "transport_error"
                and row["provider_attempt_count"] == 1
                and row["response_bytes"] == 0
                and 15.18 <= float(row["elapsed_seconds"]) < 15.20
                for row in last6
                if row["outcome"] == "failure"
            )
        ),
        "static_scheduler_contract_exact": all(static.values()),
        "three_attempt_consumed_manifest_exact72_144_127": all(
            manifest["checks"].values()
        ),
        "no_population_model_evaluator_or_benchmark_effect": (
            present["population"]["task_count"] == 0
            and present["effect_accounting"][
                "model_search_evaluator_or_benchmark_effect_count"
            ]
            == 0
        ),
        "no_task_page_value_prediction_or_credential_read": True,
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "fixed_inputs": {str(path): base_sha(path) for path in FIXED},
        "before_v25317": before,
        "after_v25323": after,
        "static_scheduler_contract": static,
        "consumed_manifest": manifest,
        "diagnosis": {
            "observed_pattern": "all_first_42_work_items_succeed_then_five_of_final_six_hit_socket_window",
            "concurrency_reduction_reduced_but_did_not_eliminate_failures": True,
            "pattern_is_consistent_with_burst_or_connection_rate_capacity": True,
            "pattern_proves_unique_causal_root_cause": False,
            "endpoint_content_response_size_selector_model_entropy_or_quality_explains_failures": False,
            "next_candidate_changes_only_transport_start_scheduling": True,
            "next_candidate_max_target_concurrency": 6,
            "next_candidate_minimum_request_start_interval_seconds": 1.0,
            "next_candidate_fixed_target_request_count": 48,
            "next_candidate_per_url_provider_attempt_count": 1,
            "next_candidate_retry_resume_refetch_backfill_replacement": False,
            "next_candidate_target_phase_hard_wall_seconds": 110,
            "next_candidate_whole_freeze_hard_wall_seconds": 145,
            "minimum_47_second_launch_span_plus_25_second_helper_timeout_fits_target_wall": True,
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
            "rate_paced_fresh_disjoint_transport_successor_build": not findings,
            "successor_population_network_activation_or_launch": False,
            "v25323_retry_resume_refetch_backfill_replacement_or_reuse": False,
            "external_monotone_fill_forward_or_evaluator": False,
            "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = current.payload_sha256(value)
    return validate_diagnosis(value)


def base_sha(path: Path) -> str:
    return current.sha256(ROOT / path)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("diagnosis_payload_sha256", None)
    checks = copied.get("checks") or {}
    findings = copied.get("findings")
    manifest = copied.get("consumed_manifest") or {}
    diagnosis = copied.get("diagnosis") or {}
    authorization = copied.get("authorization") or {}
    expected_findings = sorted(name for name, passed in checks.items() if not passed)
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "fixed_inputs",
            "before_v25317",
            "after_v25323",
            "static_scheduler_contract",
            "consumed_manifest",
            "diagnosis",
            "checks",
            "findings",
            "diagnosis_valid",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
            "question_query_url_page_value_prediction_or_credential_read_or_emitted",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
            "authorization",
            "diagnosis_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("fixed_inputs")
        != {str(path): digest for path, digest in FIXED.items()}
        or copied.get("before_v25317", {}).get("target_concurrency") != 12
        or copied.get("before_v25317", {}).get("failed_target_response_count") != 12
        or copied.get("after_v25323", {}).get("target_concurrency") != 6
        or copied.get("after_v25323", {}).get("failed_target_response_count") != 5
        or copied.get("static_scheduler_contract") != _static_barrier()
        or manifest != _manifest()
        or not all(manifest["checks"].values())
        or diagnosis
        != {
            "observed_pattern": "all_first_42_work_items_succeed_then_five_of_final_six_hit_socket_window",
            "concurrency_reduction_reduced_but_did_not_eliminate_failures": True,
            "pattern_is_consistent_with_burst_or_connection_rate_capacity": True,
            "pattern_proves_unique_causal_root_cause": False,
            "endpoint_content_response_size_selector_model_entropy_or_quality_explains_failures": False,
            "next_candidate_changes_only_transport_start_scheduling": True,
            "next_candidate_max_target_concurrency": 6,
            "next_candidate_minimum_request_start_interval_seconds": 1.0,
            "next_candidate_fixed_target_request_count": 48,
            "next_candidate_per_url_provider_attempt_count": 1,
            "next_candidate_retry_resume_refetch_backfill_replacement": False,
            "next_candidate_target_phase_hard_wall_seconds": 110,
            "next_candidate_whole_freeze_hard_wall_seconds": 145,
            "minimum_47_second_launch_span_plus_25_second_helper_timeout_fits_target_wall": True,
            "must_use_new_targets_responses_and_population_namespace": True,
            "must_not_reuse_any_partial_success_bytes": True,
        }
        or set(checks)
        != {
            "fixed_inputs_exact",
            "frozen_result_and_postaudit_valid_nogo",
            "effect_count_exact_one_catalog_plus48_target",
            "concurrency12_to6_failure12_to5_exact",
            "first42_work_items_all_succeed",
            "last6_work_items_contain_exact5_socket_window_failures",
            "static_scheduler_contract_exact",
            "three_attempt_consumed_manifest_exact72_144_127",
            "no_population_model_evaluator_or_benchmark_effect",
            "no_task_page_value_prediction_or_credential_read",
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
            "rate_paced_fresh_disjoint_transport_successor_build": not expected_findings,
            "successor_population_network_activation_or_launch": False,
            "v25323_retry_resume_refetch_backfill_replacement_or_reuse": False,
            "external_monotone_fill_forward_or_evaluator": False,
            "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
        }
        or signature != current.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.28 transport scheduler diagnosis drifted")
    return copied


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    current.publish_json_exclusive(ROOT / path, value)


def main() -> None:
    value = build_diagnosis()
    if not value["diagnosis_valid"]:
        raise SystemExit("V2.53.28 diagnosis failed: " + ", ".join(value["findings"]))
    _publish(OUTPUT, value)
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "diagnosis_valid": value["diagnosis_valid"],
                "findings": value["findings"],
                "consumed_targets": value["consumed_manifest"]["target_count"],
                "consumed_responses": value["consumed_manifest"]["response_count"],
                "next_start_interval_seconds": value["diagnosis"][
                    "next_candidate_minimum_request_start_interval_seconds"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
