#!/usr/bin/env python3
"""Content-free failure-domain diagnosis of the frozen V2.47.37 NO-GO."""

from __future__ import annotations

import hashlib
import json
import os
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

from scripts import v24737_dual_namespace_reachability_gate as parent  # noqa: E402


DATE = "20260806"
OUTPUT = Path(f"results/v24738_v24737_failure_domain_diagnosis_v1_{DATE}.json")
RESULT = parent.RESULT
DECISION = parent.DECISION
POSTAUDIT = parent.POSTAUDIT


def _read(path: Path) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.38 expected object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def _parent_chain() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    result = _read(RESULT)
    decision = _read(DECISION)
    audit = _read(POSTAUDIT)
    if (
        result.get("role") != "v24737_dual_namespace_reachability_forward_result"
        or result.get("protocol_id") != parent.PROTOCOL_ID
        or not parent._sealed(result, "result_payload_sha256")
        or decision.get("role") != "v24737_dual_namespace_reachability_decision"
        or decision.get("protocol_id") != parent.PROTOCOL_ID
        or decision.get("result_payload_sha256")
        != result.get("result_payload_sha256")
        or decision.get("status") != "dual_namespace_reachability_no_go"
        or not parent._sealed(decision, "decision_payload_sha256")
        or audit.get("role")
        != "v24737_dual_namespace_reachability_postresult_audit"
        or audit.get("protocol_id") != parent.PROTOCOL_ID
        or audit.get("result_sha256") != _sha256(RESULT)
        or audit.get("decision_sha256") != _sha256(DECISION)
        or audit.get("decision_status") != "dual_namespace_reachability_no_go"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("gold_provenance_or_evaluator_opened_by_audit") is not False
        or audit.get("network_model_search_or_api_called_by_audit") is not False
        or audit.get("authorization", {}).get("additional_forward_retry_or_rerun")
        is not False
        or not parent._sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.38 frozen parent chain drifted")
    return result, decision, audit


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    result, _decision, _audit = _parent_chain()
    requests = result.get("request_receipts")
    tasks = result.get("task_receipts")
    if not isinstance(requests, list) or not isinstance(tasks, list):
        raise RuntimeError("V2.47.38 parent receipts absent")
    request_counts = Counter(str(item.get("namespace")) for item in requests)
    request_successes = Counter(
        str(item.get("namespace"))
        for item in requests
        if item.get("transport_success") is True
    )
    failures = [item for item in requests if item.get("transport_success") is not True]
    task_counts = Counter(str(item.get("namespace")) for item in tasks)
    changing_tasks = Counter(
        str(item.get("namespace"))
        for item in tasks
        if item.get("prediction_changed") is True
    )
    value = {
        "artifact_version": 1,
        "role": "v24738_v24737_failure_domain_postterminal_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "result_sha256": _sha256(RESULT),
            "decision_sha256": _sha256(DECISION),
            "postresult_audit_sha256": _sha256(POSTAUDIT),
        },
        "transport": {
            "requests": len(requests),
            "successes": sum(
                item.get("transport_success") is True for item in requests
            ),
            "failures": len(failures),
            "failure_type_counts": dict(
                sorted(Counter(str(item.get("failure_type")) for item in failures).items())
            ),
            "failures_at_socket_wall": sum(
                float(item.get("elapsed_seconds", 0))
                >= parent.SOCKET_TIMEOUT_SECONDS - 0.25
                for item in failures
            ),
            "ror_requests": request_counts["ror"],
            "ror_successes": request_successes["ror"],
            "worldbank_requests": request_counts["worldbank"],
            "worldbank_successes": request_successes["worldbank"],
            "fixed_attempts_per_url": all(item.get("attempts") == 1 for item in requests),
            "experiment_wall_seconds": result.get("experiment_wall_seconds"),
        },
        "propagation": {
            "tasks": len(tasks),
            "ror_tasks": task_counts["ror"],
            "ror_prediction_changing_tasks": changing_tasks["ror"],
            "worldbank_tasks": task_counts["worldbank"],
            "worldbank_prediction_changing_tasks": changing_tasks["worldbank"],
            "nonchanging_tasks": sum(
                item.get("prediction_changed") is not True for item in tasks
            ),
            "failed_request_fraction": {"numerator": len(failures), "denominator": len(requests)},
            "nonchanging_task_fraction": {
                "numerator": sum(
                    item.get("prediction_changed") is not True for item in tasks
                ),
                "denominator": len(tasks),
            },
            "shared_worldbank_target_request_fanout_tasks": parent.TASKS_PER_CLUSTER,
            "complete_target_tuple_policy": True,
            "target_failure_isolation": False,
        },
        "diagnosis": {
            "ror_independent_request_topology_reached_all_tasks": True,
            "worldbank_one_of_two_shared_requests_failed": True,
            "one_shared_target_failure_coincided_with_all_worldbank_tasks_abstaining": True,
            "request_failure_to_task_nonchange_amplification_observed": True,
            "transport_reliability_is_not_sufficient_for_quality_evaluation": True,
            "same_population_retry_resume_or_selective_rerun_authorized": False,
            "timeout_only_tuning_supported": False,
            "next_requirement": "fresh_target_fixed_dual_representation_or_availability_with_target_granular_abstention",
        },
        "source_policy": {
            "frozen_prediction_content_opened_or_read": False,
            "response_body_identity_or_value_opened_or_read": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called": False,
            "same_population_retry_resume_or_selective_rerun": False,
        },
        "authorization": {
            "fresh_target_dual_representation_resilience_design": True,
            "same_population_forward_retry_or_rerun": False,
            "evaluator_execution": False,
            "benchmark_dev64_or_exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = parent.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    transport = copied.get("transport", {})
    propagation = copied.get("propagation", {})
    diagnosis = copied.get("diagnosis", {})
    if (
        copied.get("role")
        != "v24738_v24737_failure_domain_postterminal_diagnosis"
        or copied.get("parents")
        != {
            "result_sha256": _sha256(RESULT),
            "decision_sha256": _sha256(DECISION),
            "postresult_audit_sha256": _sha256(POSTAUDIT),
        }
        or transport
        != {
            "requests": 50,
            "successes": 49,
            "failures": 1,
            "failure_type_counts": {"transport_error": 1},
            "failures_at_socket_wall": 1,
            "ror_requests": 48,
            "ror_successes": 48,
            "worldbank_requests": 2,
            "worldbank_successes": 1,
            "fixed_attempts_per_url": True,
            "experiment_wall_seconds": 16.384839,
        }
        or propagation
        != {
            "tasks": 24,
            "ror_tasks": 12,
            "ror_prediction_changing_tasks": 12,
            "worldbank_tasks": 12,
            "worldbank_prediction_changing_tasks": 0,
            "nonchanging_tasks": 12,
            "failed_request_fraction": {"numerator": 1, "denominator": 50},
            "nonchanging_task_fraction": {"numerator": 12, "denominator": 24},
            "shared_worldbank_target_request_fanout_tasks": 12,
            "complete_target_tuple_policy": True,
            "target_failure_isolation": False,
        }
        or diagnosis.get("same_population_retry_resume_or_selective_rerun_authorized")
        is not False
        or diagnosis.get("timeout_only_tuning_supported") is not False
        or diagnosis.get("next_requirement")
        != "fresh_target_fixed_dual_representation_or_availability_with_target_granular_abstention"
        or any(copied.get("source_policy", {}).values())
        or copied.get("authorization")
        != {
            "fresh_target_dual_representation_resilience_design": True,
            "same_population_forward_retry_or_rerun": False,
            "evaluator_execution": False,
            "benchmark_dev64_or_exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or seal != parent.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.38 diagnosis drifted")
    return copied


def main() -> None:
    if (ROOT / OUTPUT).exists() or (ROOT / OUTPUT).is_symlink():
        raise FileExistsError(OUTPUT)
    value = build_diagnosis()
    descriptor = os.open(
        ROOT / OUTPUT,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    main()
