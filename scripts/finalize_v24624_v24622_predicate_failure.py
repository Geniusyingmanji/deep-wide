#!/usr/bin/env python3
"""Freeze the terminal V2.46.22 mechanism-predicate recursion failure.

The only external wave reached content-free mechanism aggregation after all
eight task futures returned.  Result construction then entered the inherited
mechanism predicate while both its caller and its internal controller target
were bound to the same V2.46.16 function, causing deterministic self-recursion.

This finalizer reads committed control artifacts plus content-free process,
lease, watcher, function-identity, and immediate ``outputs/tmp*`` metadata.  It
does not open task/query/URL/title/page/prediction/provider/evaluator content
and performs no network, model, search, fetch, benchmark, or evaluator effect.
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
from scripts import v24622_collector_lifetime_external_gate as failed  # noqa: E402


DATE = "20260806"
FAILURE = Path(f"results/v24624_v24622_terminal_predicate_failure_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24624_v24622_postfailure_audit_v1_{DATE}.json")


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


def _control_chain() -> dict[str, str]:
    for path in (
        failed.BUILD_AUDIT,
        failed.PROTOCOL,
        failed.PREAUDIT,
        failed.ACTIVATION,
        failed.EXECUTION_START,
    ):
        if not (ROOT / path).is_file() or (ROOT / path).is_symlink():
            raise RuntimeError("V2.46.24 control chain is absent")
    failed._validated_build_audit()
    failed.validate_protocol()
    failed.validate_preaudit()
    failed.validate_activation()
    failed.validate_execution_start()
    return {
        "build_audit_sha256": sha256(ROOT / failed.BUILD_AUDIT),
        "protocol_sha256": sha256(ROOT / failed.PROTOCOL),
        "preactivation_audit_sha256": sha256(ROOT / failed.PREAUDIT),
        "activation_sha256": sha256(ROOT / failed.ACTIVATION),
        "execution_start_sha256": sha256(ROOT / failed.EXECUTION_START),
    }


def binding_diagnosis() -> dict[str, Any]:
    predicate = failed.mechanism_passed
    names = set(predicate.__code__.co_names)
    with failed.configured_runtime_stack():
        value = {
            "predicate_module": predicate.__module__,
            "predicate_qualname": predicate.__qualname__,
            "base_mechanism_predicate_is_v24616_predicate": (
                failed.base._mechanism_passed is predicate
            ),
            "controller_mechanism_predicate_is_v24616_predicate": (
                failed.controller.mechanism_passed is predicate
            ),
            "predicate_global_controller_is_runtime_controller": (
                predicate.__globals__.get("controller") is failed.controller
            ),
            "predicate_bytecode_references_controller_mechanism_passed": (
                {"controller", "mechanism_passed"}.issubset(names)
            ),
        }
    value["self_referential_binding_proven"] = all(
        item is True
        for key, item in value.items()
        if key not in {"predicate_module", "predicate_qualname"}
    )
    if (
        value["predicate_module"]
        != "scripts.v24616_repaired_title_provenance_external_gate"
        or value["predicate_qualname"] != "mechanism_passed"
        or value["self_referential_binding_proven"] is not True
    ):
        raise RuntimeError("V2.46.24 predicate diagnosis drifted")
    return value


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
        if failed.RUNNER_MARKER in line and "finalize_v24624" not in line
    ]


def _recent_temporary_directories() -> list[str]:
    threshold = int(failed._read(failed.EXECUTION_START)["created_at_unix"])
    output = ROOT / "outputs"
    return sorted(
        path.name
        for path in output.iterdir()
        if path.name.startswith("tmp")
        and path.is_dir()
        and not path.is_symlink()
        and int(path.stat().st_mtime) >= threshold
    )


def build_failure(*, now: int | None = None) -> dict[str, Any]:
    provenance = _control_chain()
    diagnosis = binding_diagnosis()
    if any(
        (ROOT / path).exists()
        for path in (failed.RESULT, failed.DECISION, failed.POSTAUDIT)
    ):
        raise RuntimeError("V2.46.24 unexpected V2.46.22 public result surface")
    value = {
        "artifact_version": 1,
        "role": "v24624_v24622_terminal_predicate_failure",
        "protocol_id": failed.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "terminal_postaggregate_mechanism_predicate_recursion_no_result",
        "selected": 8,
        "external_wave_started": True,
        "external_wave_count": 1,
        "external_population_consumed": True,
        "result_created": False,
        "decision_created": False,
        "official_evaluator_called": False,
        "benchmark_score_available": False,
        "failure_stage": "postaggregate_content_free_mechanism_gate_evaluation",
        "failure_class": "self_referential_mechanism_predicate_binding",
        "failure_detail_content_free": (
            "all eight task futures returned, the collector remained active through "
            "content-free mechanism aggregation, and result construction then failed "
            "closed because the inherited mechanism predicate called the controller "
            "predicate while both names referenced that same function"
        ),
        "concurrent_parent_supervisor_worker_launch_observed": True,
        "all_task_futures_returned": True,
        "collector_context_covered_task_and_aggregate_lifetime": True,
        "content_free_mechanism_aggregate_completed": True,
        "mechanism_gate_evaluation_completed": False,
        "preworker_controller_deadlock_recurred": False,
        "collector_absent_failure_recurred": False,
        "batch_watchdog_expiry_established": False,
        "provider_search_or_fetch_latency_established_as_failure_cause": False,
        "temporary_execution_tree_cleaned_by_context_manager": True,
        "same_population_resume_retry_skip_selective_rerun_or_evaluation_authorized": False,
        "fresh_disjoint_successor_required": True,
        "binding_diagnosis": diagnosis,
        "provenance": provenance,
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "private_task_query_url_title_page_prediction_or_provider_payload_opened_by_finalizer": False,
            "network_model_search_fetch_process_or_evaluator_called_by_finalizer": False,
        },
        "claims": {
            "collector_lifetime_repair_reached_aggregate": True,
            "title_provenance_measured": False,
            "provider_transport_or_quality_cause_established": False,
            "benchmark_quality_measured": False,
            "sota": False,
        },
        "authorization": {
            "same_population_retry_resume_or_evaluation": False,
            "predicate_binding_successor_design": True,
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
        copied.get("role") != "v24624_v24622_terminal_predicate_failure"
        or copied.get("protocol_id") != failed.PROTOCOL_ID
        or copied.get("status")
        != "terminal_postaggregate_mechanism_predicate_recursion_no_result"
        or copied.get("selected") != 8
        or copied.get("external_wave_started") is not True
        or copied.get("external_wave_count") != 1
        or copied.get("external_population_consumed") is not True
        or copied.get("result_created") is not False
        or copied.get("official_evaluator_called") is not False
        or copied.get("failure_stage")
        != "postaggregate_content_free_mechanism_gate_evaluation"
        or copied.get("failure_class")
        != "self_referential_mechanism_predicate_binding"
        or copied.get("all_task_futures_returned") is not True
        or copied.get("collector_context_covered_task_and_aggregate_lifetime") is not True
        or copied.get("content_free_mechanism_aggregate_completed") is not True
        or copied.get("mechanism_gate_evaluation_completed") is not False
        or copied.get("preworker_controller_deadlock_recurred") is not False
        or copied.get("collector_absent_failure_recurred") is not False
        or copied.get("binding_diagnosis") != binding_diagnosis()
        or copied.get("provenance") != _control_chain()
        or copied.get(
            "same_population_resume_retry_skip_selective_rerun_or_evaluation_authorized"
        )
        is not False
        or copied.get("fresh_disjoint_successor_required") is not True
        or copied.get("authorization", {}).get("same_population_retry_resume_or_evaluation")
        is not False
        or copied.get("authorization", {}).get("fresh_external_launch") is not False
        or copied.get("authorization", {}).get("paired_dev64_or_exact220") is not False
        or not _sealed(copied, "failure_payload_sha256")
    ):
        raise RuntimeError("V2.46.24 terminal failure drifted")
    return copied


def build_postaudit(*, now: int | None = None) -> dict[str, Any]:
    failure = validate_failure(json.loads((ROOT / FAILURE).read_text(encoding="utf-8")))
    lease = failed.base.lease_observation(ROOT, Path("/proc"))
    watchers = failed.base.protected_watcher_snapshot()
    expected = failed._read(failed.EXECUTION_START)["protected_watchers"]
    runners = _runner_pids()
    temporary = _recent_temporary_directories()
    findings: list[str] = []
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if watchers != expected:
        findings.append("protected_watcher_identity_drifted")
    if runners:
        findings.append("v24622_runner_present")
    if temporary:
        findings.append("v24622_temporary_execution_directory_remaining")
    if any(
        (ROOT / path).exists()
        for path in (failed.RESULT, failed.DECISION, failed.POSTAUDIT)
    ):
        findings.append("unexpected_v24622_public_result_surface")
    if binding_diagnosis() != failure["binding_diagnosis"]:
        findings.append("predicate_binding_diagnosis_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24624_v24622_postfailure_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "failure_sha256": sha256(ROOT / FAILURE),
        "failure_status": failure["status"],
        "shared_api_lease_active": lease.get("active") is not False,
        "protected_watchers": watchers,
        "v24622_runner_present": bool(runners),
        "temporary_execution_directory_remaining": bool(temporary),
        "v24622_result_decision_or_postaudit_present": False,
        "predicate_binding_diagnosis_valid": True,
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
        copied.get("role") != "v24624_v24622_postfailure_audit"
        or copied.get("failure_sha256") != sha256(ROOT / FAILURE)
        or copied.get("failure_status")
        != "terminal_postaggregate_mechanism_predicate_recursion_no_result"
        or copied.get("shared_api_lease_active") is not False
        or copied.get("protected_watchers") != failed.base.protected_watcher_snapshot()
        or copied.get("v24622_runner_present") is not False
        or copied.get("temporary_execution_directory_remaining") is not False
        or copied.get("v24622_result_decision_or_postaudit_present") is not False
        or copied.get("predicate_binding_diagnosis_valid") is not True
        or copied.get(
            "same_population_retry_resume_skip_selective_rerun_or_evaluation_performed"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get("network_model_search_fetch_or_evaluator_called_by_audit")
        is not False
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.24 postfailure audit drifted")
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
