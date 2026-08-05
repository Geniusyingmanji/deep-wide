#!/usr/bin/env python3
"""Freeze the terminal, non-retryable V2.46.12 controller failure.

This finalizer reads only committed control artifacts and live process/lease
metadata.  It never opens the deleted temporary execution tree, task, query,
URL, title, page, prediction, mapping, gold, score, reward, or evaluator data,
and it performs no network/model/search/fetch/evaluator effect.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256, sha256  # noqa: E402
from scripts import v24612_title_provenance_external_gate as failed  # noqa: E402


DATE = "20260805"
FAILURE = Path(f"results/v24613_v24612_terminal_failure_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24613_v24612_postfailure_audit_v1_{DATE}.json")


def _publish(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _runner_pids() -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,args="],
        cwd=ROOT,
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=10,
    )
    return [
        int(line.strip().split(maxsplit=1)[0])
        for line in completed.stdout.splitlines()
        if failed.RUNNER_MARKER in line and "finalize_v24613" not in line
    ]


def _control_chain() -> dict[str, str]:
    for path in (
        failed.PROTOCOL,
        failed.PREAUDIT,
        failed.ACTIVATION,
        failed.EXECUTION_START,
    ):
        if not (ROOT / path).is_file() or (ROOT / path).is_symlink():
            raise RuntimeError("V2.46.13 control chain is absent")
    failed.validate_protocol()
    failed.validate_preaudit()
    failed.validate_activation()
    failed.validate_execution_start()
    return {
        "protocol_sha256": sha256(ROOT / failed.PROTOCOL),
        "preactivation_audit_sha256": sha256(ROOT / failed.PREAUDIT),
        "activation_sha256": sha256(ROOT / failed.ACTIVATION),
        "execution_start_sha256": sha256(ROOT / failed.EXECUTION_START),
    }


def build_failure(*, now: int | None = None) -> dict[str, Any]:
    provenance = _control_chain()
    if any((ROOT / path).exists() for path in (failed.RESULT, failed.DECISION, failed.POSTAUDIT)):
        raise RuntimeError("V2.46.13 unexpected V2.46.12 public result surface")
    value = {
        "artifact_version": 1,
        "role": "v24613_v24612_terminal_failure",
        "protocol_id": failed.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "terminal_controller_binding_failure_no_result",
        "selected": 8,
        "external_wave_started": True,
        "external_wave_count": 1,
        "external_population_consumed": True,
        "result_created": False,
        "decision_created": False,
        "official_evaluator_called": False,
        "benchmark_score_available": False,
        "failure_stage": "parent_capability_validation",
        "failure_class": "controller_compatibility_binding_contaminated_runtime_proof_module",
        "failure_detail_content_free": (
            "the protocol-compatibility view rebound the V2.46.07 parent proof "
            "module to V2.45.90 during real parent capability validation"
        ),
        "same_population_resume_retry_skip_selective_rerun_or_evaluation_authorized": False,
        "fresh_disjoint_successor_required": True,
        "provenance": provenance,
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "private_task_query_url_title_page_prediction_or_provider_payload_opened_by_finalizer": False,
            "network_model_search_fetch_process_or_evaluator_called_by_finalizer": False,
        },
        "claims": {
            "title_provenance_measured": False,
            "provider_transport_or_quality_cause_established": False,
            "benchmark_quality_measured": False,
            "sota": False,
        },
        "authorization": {
            "same_population_retry_resume_or_evaluation": False,
            "controller_binding_repair_design": True,
            "fresh_disjoint_successor_protocol_design_after_clean_build_audit": True,
            "fresh_external_launch": False,
            "paired_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["failure_payload_sha256"] = payload_sha256(value)
    return validate_failure(value)


def validate_failure(value: dict[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24613_v24612_terminal_failure"
        or copied.get("protocol_id") != failed.PROTOCOL_ID
        or copied.get("status") != "terminal_controller_binding_failure_no_result"
        or copied.get("selected") != 8
        or copied.get("external_wave_started") is not True
        or copied.get("external_wave_count") != 1
        or copied.get("external_population_consumed") is not True
        or copied.get("result_created") is not False
        or copied.get("decision_created") is not False
        or copied.get("official_evaluator_called") is not False
        or copied.get("benchmark_score_available") is not False
        or copied.get("same_population_resume_retry_skip_selective_rerun_or_evaluation_authorized")
        is not False
        or copied.get("fresh_disjoint_successor_required") is not True
        or copied.get("provenance") != _control_chain()
        or copied.get("source_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get("claims", {}).get("title_provenance_measured") is not False
        or copied.get("authorization", {}).get("same_population_retry_resume_or_evaluation")
        is not False
        or copied.get("authorization", {}).get("fresh_external_launch") is not False
        or copied.get("authorization", {}).get("paired_dev64_or_exact220") is not False
        or not _sealed(copied, "failure_payload_sha256")
    ):
        raise RuntimeError("V2.46.13 terminal failure drifted")
    return copied


def build_postaudit(*, now: int | None = None) -> dict[str, Any]:
    failure = validate_failure(json.loads((ROOT / FAILURE).read_text(encoding="utf-8")))
    lease = failed.base.lease_observation(ROOT, Path("/proc"))
    watchers = failed.base.protected_watcher_snapshot()
    expected = failed._read(failed.EXECUTION_START)["protected_watchers"]
    runners = _runner_pids()
    findings: list[str] = []
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if watchers != expected:
        findings.append("protected_watcher_identity_drifted")
    if runners:
        findings.append("v24612_runner_present")
    if any((ROOT / path).exists() for path in (failed.RESULT, failed.DECISION, failed.POSTAUDIT)):
        findings.append("unexpected_v24612_public_result_surface")
    value = {
        "artifact_version": 1,
        "role": "v24613_v24612_postfailure_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "failure_sha256": sha256(ROOT / FAILURE),
        "failure_status": failure["status"],
        "shared_api_lease_active": lease.get("active") is not False,
        "protected_watchers": watchers,
        "v24612_runner_present": bool(runners),
        "temporary_execution_directory_remaining": False,
        "v24612_result_decision_or_postaudit_present": False,
        "same_population_retry_resume_skip_selective_rerun_or_evaluation_performed": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "private_task_query_url_title_page_prediction_or_provider_payload_opened_by_audit": False,
        "network_model_search_fetch_or_evaluator_called_by_audit": False,
        "findings": findings,
        "audit_valid": not findings,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_postaudit(value)


def validate_postaudit(value: dict[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24613_v24612_postfailure_audit"
        or copied.get("failure_sha256") != sha256(ROOT / FAILURE)
        or copied.get("failure_status") != "terminal_controller_binding_failure_no_result"
        or copied.get("shared_api_lease_active") is not False
        or copied.get("protected_watchers") != failed.base.protected_watcher_snapshot()
        or copied.get("v24612_runner_present") is not False
        or copied.get("temporary_execution_directory_remaining") is not False
        or copied.get("v24612_result_decision_or_postaudit_present") is not False
        or copied.get(
            "same_population_retry_resume_skip_selective_rerun_or_evaluation_performed"
        )
        is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read")
        is not False
        or copied.get("network_model_search_fetch_or_evaluator_called_by_audit")
        is not False
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.13 postfailure audit drifted")
    return copied


def main() -> None:
    failure = build_failure()
    _publish(ROOT / FAILURE, failure)
    audit = build_postaudit()
    _publish(ROOT / POSTAUDIT, audit)
    print(
        json.dumps(
            {
                "failure": str(FAILURE),
                "postaudit": str(POSTAUDIT),
                "status": failure["status"],
                "audit_valid": audit["audit_valid"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
