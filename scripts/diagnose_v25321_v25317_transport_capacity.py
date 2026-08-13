#!/usr/bin/env python3
"""Content-free diagnosis of the V2.53.17 target transport NO-GO."""

from __future__ import annotations

import ast
import copy
import json
import os
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

from scripts import audit_v25320_disjoint_worldbank_population_nogo as post  # noqa: E402
from scripts import run_v25317_disjoint_worldbank_population as runner  # noqa: E402


DATE = "20260813"
ROLE = "v25321_v25317_transport_capacity_diagnosis"
OUTPUT = Path(f"results/v25321_v25317_transport_capacity_diagnosis_v1_{DATE}.json")
SOURCE = Path("scripts/diagnose_v25321_v25317_transport_capacity.py")
TEST = Path("tests/test_diagnose_v25321_v25317_transport_capacity.py")
FIXED = {
    runner.RESULT: "f5015143ccc03beb40785eb18d91507223c8dcdd30cb95156793a3d895fd9c65",
    runner.ATTEMPT_CLAIM: "b0c5bb8635d7cb42683dca0d1e76b2fd8a418cfd9f74307c9eeb4a3bdc2cb18b",
    post.OUTPUT: "ac9614e2948263382621f8d25404d491b31cec96874827045b2df9d7e7dff2e1",
    runner.SOURCE: "16bd593dd7dcec23069bc012c5e1a535ea20cacf3c2cb4f678e23da2aab6dc8f",
    runner.HELPER: "a8049e892669d17bcc940f0c13b029207aa68d8f6677552ab7a5347f19c88ce4",
}


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(runner._ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.53.21 expected JSON object")
    return value


def _static_transport_barrier() -> dict[str, bool]:
    source = runner._ordinary(runner.SOURCE).read_text(encoding="utf-8")
    parent = runner._ordinary(runner.PARENT_TRANSPORT).read_text(encoding="utf-8")
    tree = ast.parse(parent, filename=str(runner.PARENT_TRANSPORT))
    request = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_request_target_pages"
    )
    request_text = ast.get_source_segment(parent, request) or ""
    return {
        "fixed_target_concurrency_was_12": (
            runner.TARGET_CONCURRENCY == 12
            and "ThreadPoolExecutor(max_workers=TARGET_CONCURRENCY)"
            in request_text
        ),
        "work_order_is_target_then_page": (
            "for index, target in enumerate(targets, 1) for page in (1, 2)"
            in request_text
        ),
        "target_socket_window_was_15_seconds": (
            runner.TARGET_SOCKET_TIMEOUT_SECONDS == 15.0
            and "TARGET_SOCKET_TIMEOUT_SECONDS = 15.0" in parent
        ),
        "one_provider_attempt_per_url_no_retry": (
            "provider_attempt_count=attempted" in runner._ordinary(
                runner.HELPER
            ).read_text(encoding="utf-8")
            and "allow_redirects=False" in runner._ordinary(
                runner.HELPER
            ).read_text(encoding="utf-8")
            and '"redirect_retry_refetch_resume_backfill_replacement_count": 0'
            in source
        ),
    }


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    if any(runner.sha256(ROOT / path) != digest for path, digest in FIXED.items()):
        raise RuntimeError("V2.53.21 fixed input hash drifted")
    result = runner.validate_result(_read(runner.RESULT))
    audit = post.validate_audit(_read(post.OUTPUT))
    rows = result["target_transport"]["rows"]
    successful = [row for row in rows if row["outcome"] == "success"]
    failed = [row for row in rows if row["outcome"] == "failure"]
    success_elapsed = [float(row["elapsed_seconds"]) for row in successful]
    failure_elapsed = [float(row["elapsed_seconds"]) for row in failed]
    static = _static_transport_barrier()
    failed_pairs = sorted(
        [int(row["candidate_ordinal"]), int(row["page"])] for row in failed
    )
    expected_pairs = [
        [ordinal, page] for ordinal in range(7, 13) for page in (1, 2)
    ]
    checks = {
        "fixed_inputs_exact": True,
        "frozen_result_and_postaudit_valid_nogo": (
            result["decision"] == "no_go"
            and result["failure_code"] == "target_transport_or_hard_wall"
            and audit["audit_valid"] is True
            and audit["findings"] == []
        ),
        "effect_count_exact_one_catalog_plus48_target": (
            result["effect_accounting"]["catalog_provider_attempt_count"] == 1
            and result["effect_accounting"]["target_provider_attempt_count"]
            == 48
        ),
        "success36_fast_and_nonempty": (
            len(successful) == 36
            and max(success_elapsed) < 3.2
            and all(int(row["response_bytes"]) > 0 for row in successful)
        ),
        "failure12_exact_socket_window_and_zero_bytes": (
            len(failed) == 12
            and Counter(row["failure_code"] for row in failed)
            == {"transport_error": 12}
            and min(failure_elapsed) >= 15.18
            and max(failure_elapsed) < 15.20
            and all(
                row["http_status"] is None
                and row["provider_attempt_count"] == 1
                and row["response_bytes"] == 0
                for row in failed
            )
        ),
        "failure_is_exact_contiguous_work_order_block7_through12": failed_pairs
        == expected_pairs,
        "later_work_order_block13_through24_recovers": all(
            row["outcome"] == "success"
            for row in rows
            if int(row["candidate_ordinal"]) >= 13
        ),
        "static_transport_contract_exact": all(static.values()),
        "no_population_model_evaluator_or_benchmark_effect": (
            result["population"]["task_count"] == 0
            and result["effect_accounting"][
                "model_search_evaluator_or_benchmark_effect_count"
            ]
            == 0
            and result["authorization"]["external_forward_or_evaluator"]
            is False
        ),
        "no_task_page_value_prediction_or_credential_read": True,
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "fixed_inputs": {str(path): runner.sha256(ROOT / path) for path in FIXED},
        "aggregate": {
            "target_receipt_count": len(rows),
            "successful_target_response_count": len(successful),
            "failed_target_response_count": len(failed),
            "failure_code_counts": dict(
                sorted(Counter(row["failure_code"] for row in failed).items())
            ),
            "failed_ordinal_pages": failed_pairs,
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
            "successful_response_bytes": {
                "minimum": min(int(row["response_bytes"]) for row in successful),
                "maximum": max(int(row["response_bytes"]) for row in successful),
            },
        },
        "static_transport_contract": static,
        "diagnosis": {
            "observed_pattern": "contiguous_work_order_block_hits_socket_window_then_later_block_recovers",
            "pattern_is_consistent_with_transient_burst_or_connection_capacity": True,
            "pattern_proves_unique_causal_root_cause": False,
            "endpoint_content_or_response_size_explains_failures": False,
            "next_candidate_changes_only_transport_scheduling": True,
            "next_candidate_target_concurrency": 6,
            "per_url_provider_attempt_count": 1,
            "fixed_target_request_count": 48,
            "whole_freeze_hard_wall_seconds": 145.0,
            "retry_resume_refetch_backfill_replacement": False,
            "must_use_new_targets_responses_and_population_namespace": True,
            "must_not_reuse_v25317_partial_success_bytes": True,
        },
        "checks": checks,
        "findings": findings,
        "diagnosis_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "question_query_url_page_value_prediction_or_credential_read_or_emitted": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "v25317_retry_resume_refetch_backfill_replacement_or_reuse": False,
            "low_concurrency_fresh_disjoint_transport_successor_build": not findings,
            "successor_population_network_activation_or_launch": False,
            "external_monotone_fill_forward_or_evaluator": False,
            "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = runner.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("diagnosis_payload_sha256", None)
    checks = copied.get("checks") or {}
    findings = copied.get("findings")
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
            "aggregate",
            "static_transport_contract",
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
        or copied.get("static_transport_contract") != _static_transport_barrier()
        or set(checks)
        != {
            "fixed_inputs_exact",
            "frozen_result_and_postaudit_valid_nogo",
            "effect_count_exact_one_catalog_plus48_target",
            "success36_fast_and_nonempty",
            "failure12_exact_socket_window_and_zero_bytes",
            "failure_is_exact_contiguous_work_order_block7_through12",
            "later_work_order_block13_through24_recovers",
            "static_transport_contract_exact",
            "no_population_model_evaluator_or_benchmark_effect",
            "no_task_page_value_prediction_or_credential_read",
            "no_network_model_search_fetch_evaluator_benchmark_or_api_called",
        }
        or any(not isinstance(item, bool) for item in checks.values())
        or findings != expected_findings
        or copied.get("diagnosis_valid") is not (not expected_findings)
        or diagnosis
        != {
            "observed_pattern": "contiguous_work_order_block_hits_socket_window_then_later_block_recovers",
            "pattern_is_consistent_with_transient_burst_or_connection_capacity": True,
            "pattern_proves_unique_causal_root_cause": False,
            "endpoint_content_or_response_size_explains_failures": False,
            "next_candidate_changes_only_transport_scheduling": True,
            "next_candidate_target_concurrency": 6,
            "per_url_provider_attempt_count": 1,
            "fixed_target_request_count": 48,
            "whole_freeze_hard_wall_seconds": 145.0,
            "retry_resume_refetch_backfill_replacement": False,
            "must_use_new_targets_responses_and_population_namespace": True,
            "must_not_reuse_v25317_partial_success_bytes": True,
        }
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
            "v25317_retry_resume_refetch_backfill_replacement_or_reuse": False,
            "low_concurrency_fresh_disjoint_transport_successor_build": not expected_findings,
            "successor_population_network_activation_or_launch": False,
            "external_monotone_fill_forward_or_evaluator": False,
            "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
        }
        or signature != runner.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.21 transport diagnosis drifted")
    return copied


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_diagnosis()
    if not value["diagnosis_valid"]:
        raise SystemExit("V2.53.21 diagnosis failed: " + ", ".join(value["findings"]))
    _publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "diagnosis_valid": value["diagnosis_valid"],
                "findings": value["findings"],
                "successful": value["aggregate"]["successful_target_response_count"],
                "failed": value["aggregate"]["failed_target_response_count"],
                "next_concurrency": value["diagnosis"]["next_candidate_target_concurrency"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
