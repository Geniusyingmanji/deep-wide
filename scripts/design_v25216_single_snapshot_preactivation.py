#!/usr/bin/env python3
"""Freeze the build-only design for four one-shot public snapshots."""

from __future__ import annotations

import copy
import hashlib
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
from scripts import audit_v25215_offline_candidate_discovery_build as parent  # noqa: E402


DATE = "20260812"
OUTPUT = Path(f"results/v25216_single_snapshot_preactivation_design_v1_{DATE}.json")
PARENT_AUDIT = parent.OUTPUT
EXPECTED_PARENT_AUDIT_SHA256 = (
    "0793a619b853e2a69096bd199aa1c558da7299f704b8a201236fe3332ad171a5"
)
ENDPOINTS = {
    "single_authority_exact_record": {
        "url": "https://crates.io/api/v1/crates?page=1&per_page=100&sort=recent-downloads",
        "maximum_response_bytes": 4 * 1024 * 1024,
        "accepted_content_types": ["application/json"],
    },
    "single_authority_multivalue_record": {
        "url": "https://cran.r-project.org/src/contrib/PACKAGES",
        "maximum_response_bytes": 32 * 1024 * 1024,
        "accepted_content_types": ["text/plain"],
    },
    "same_identity_multipage_record": {
        "url": "https://api.crossref.org/works?filter=type:journal-article&select=DOI,title,publisher,container-title&sort=published&order=desc&rows=100",
        "maximum_response_bytes": 8 * 1024 * 1024,
        "accepted_content_types": ["application/json"],
    },
    "sparse_ambiguous_open_web_record": {
        "url": "https://pypi.org/simple/",
        "maximum_response_bytes": 128 * 1024 * 1024,
        "accepted_content_types": ["text/html", "application/vnd.pypi.simple.v1+html"],
    },
}
CONNECT_TIMEOUT_SECONDS = 10.0
READ_TIMEOUT_SECONDS = 120.0
TOTAL_WALL_SECONDS = 180.0
SNAPSHOT_CONCURRENCY = 4
USER_AGENT = "DeepWideResearch/2.52.16 (public snapshot reliability study)"
payload_sha256 = base.payload_sha256


def _parent_barrier() -> bool:
    raw = json.loads(base.base._ordinary(PARENT_AUDIT).read_text(encoding="utf-8"))
    value = parent.validate_audit(raw)
    authorization = value["authorization"]
    return bool(
        base.base.sha256(PARENT_AUDIT) == EXPECTED_PARENT_AUDIT_SHA256
        and value["audit_valid"] is True
        and value["findings"] == []
        and value["tests"]["expected"] == 30
        and value["tests"]["observed"] == 30
        and value["dependency_closure"]
        == ["src/deepwide_agent/v25215_offline_candidate_discovery.py"]
        and authorization["single_snapshot_preactivation_design"] is True
        and authorization["public_index_snapshot_network_access"] is False
        and authorization["real_identity_selection_or_population_freeze"] is False
    )


def _endpoint_rows() -> dict[str, dict[str, Any]]:
    return {
        stratum: {
            **copy.deepcopy(spec),
            "url_sha256": hashlib.sha256(spec["url"].encode()).hexdigest(),
        }
        for stratum, spec in ENDPOINTS.items()
    }


def build_design(*, now: int | None = None) -> dict[str, Any]:
    if not _parent_barrier():
        raise RuntimeError("V2.52.16 parent discovery audit barrier failed")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25216_single_snapshot_preactivation_design",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_discovery_build_audit": {
            "path": str(PARENT_AUDIT),
            "sha256": base.base.sha256(PARENT_AUDIT),
        },
        "endpoints": _endpoint_rows(),
        "transport_contract": {
            "method": "GET",
            "snapshot_count": 4,
            "snapshot_concurrency": SNAPSHOT_CONCURRENCY,
            "attempts_per_endpoint": 1,
            "redirects_per_endpoint": 0,
            "retries_per_endpoint": 0,
            "conditional_refetches_per_endpoint": 0,
            "connect_timeout_seconds": CONNECT_TIMEOUT_SECONDS,
            "read_timeout_seconds": READ_TIMEOUT_SECONDS,
            "total_wall_seconds": TOTAL_WALL_SECONDS,
            "maximum_total_response_bytes": sum(
                row["maximum_response_bytes"] for row in ENDPOINTS.values()
            ),
            "tls_verification_required": True,
            "requests_trust_env_disabled": True,
            "public_address_dns_preflight_required": True,
            "dns_preflight_result_pinned_to_transport": False,
            "user_agent": USER_AGENT,
            "authorization_header_cookie_query_secret_or_credential": False,
        },
        "execution_contract": {
            "raw_snapshot_bytes_exist_in_memory_only": True,
            "raw_snapshot_file_persistence": False,
            "each_snapshot_flows_once_to_v25215_offline_parser": True,
            "candidate_identities_exist_in_memory_only_until_history_scan": True,
            "transport_receipt_persists_only_url_hash_status_bytes_body_hash_elapsed_and_error_class": True,
            "all_four_parsers_must_complete_and_each_yield_at_least_64_distinct_candidates": True,
            "deterministic_rank_then_v25213_history_scan_in_same_process": True,
            "any_history_hit_stops_whole_population_without_backfill": True,
            "risk_stratum_removed_before_any_future_runtime_task": True,
            "no_model_hosted_search_tavily_evaluator_or_benchmark_access": True,
        },
        "failure_policy": {
            "transport_failure_http_non200_redirect_timeout_oversize_or_content_type": "whole_batch_no_go",
            "parser_failure_or_fewer_than_64_candidates": "whole_batch_no_go",
            "history_hit_or_cross_stratum_collision": "whole_batch_no_go",
            "retry_refetch_alternate_endpoint_or_manual_replacement": "quarantine_as_invalid",
            "partial_population_freeze": "forbidden",
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "single_snapshot_transport_implementation_build_only": True,
            "public_snapshot_preactivation_audit_design": True,
            "public_snapshot_network_access_or_execution_start": False,
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
    transport = copied.get("transport_contract") or {}
    execution = copied.get("execution_contract") or {}
    authorization = copied.get("authorization") or {}
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != "v25216_single_snapshot_preactivation_design"
        or copied.get("parent_discovery_build_audit", {}).get("sha256")
        != EXPECTED_PARENT_AUDIT_SHA256
        or copied.get("endpoints") != _endpoint_rows()
        or transport.get("method") != "GET"
        or transport.get("snapshot_count") != 4
        or transport.get("snapshot_concurrency") != SNAPSHOT_CONCURRENCY
        or transport.get("attempts_per_endpoint") != 1
        or transport.get("redirects_per_endpoint") != 0
        or transport.get("retries_per_endpoint") != 0
        or transport.get("conditional_refetches_per_endpoint") != 0
        or transport.get("connect_timeout_seconds") != CONNECT_TIMEOUT_SECONDS
        or transport.get("read_timeout_seconds") != READ_TIMEOUT_SECONDS
        or transport.get("total_wall_seconds") != TOTAL_WALL_SECONDS
        or transport.get("maximum_total_response_bytes")
        != sum(row["maximum_response_bytes"] for row in ENDPOINTS.values())
        or transport.get("authorization_header_cookie_query_secret_or_credential")
        is not False
        or execution.get("raw_snapshot_file_persistence") is not False
        or execution.get("no_model_hosted_search_tavily_evaluator_or_benchmark_access")
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
            "single_snapshot_transport_implementation_build_only": True,
            "public_snapshot_preactivation_audit_design": True,
            "public_snapshot_network_access_or_execution_start": False,
            "real_identity_selection_or_population_freeze": False,
            "probe_runtime_integration_external_forward_or_activation": False,
            "runtime_compatibility_validator_relaxation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.16 single snapshot design drifted")
    return copied


def main() -> None:
    value = build_design()
    base.base.publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "snapshot_count": value["transport_contract"]["snapshot_count"],
                "transport_build_only": value["authorization"][
                    "single_snapshot_transport_implementation_build_only"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
