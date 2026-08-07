#!/usr/bin/env python3
"""Run one fresh label-blind V2.48.00 Tavily exact-220 forward."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24800_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24796_deadline_tavily_search import (  # noqa: E402
    prepare_key_slots,
    validate_receipt as validate_direct_receipt,
)
from scripts import run_v24635_exact220 as algorithm  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


_CREDENTIAL_ENVIRONMENT = "TAVILY_API_KEYS"
_credentials: tuple[str, ...] = ()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError(f"V2.48.00 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.00 expected JSON object")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _read_credentials(stream: Any = sys.stdin) -> tuple[str, ...]:
    serialized = stream.read()
    try:
        values = tuple(line.strip() for line in serialized.splitlines() if line.strip())
    finally:
        serialized = ""
    if len(values) != contract.TAVILY_KEY_SLOT_CAP or len(set(values)) != len(values):
        raise RuntimeError("V2.48.00 requires exactly 12 distinct credentials on stdin")
    return values


def validate_execution_start(root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    audit = _read(root / contract.PREAUDIT)
    start = _read(root / contract.EXECUTION_START)
    if (
        audit.get("role") != "v24800_exact220_preactivation_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get("execution_start_generation") is not True
        or not _sealed(audit, "audit_payload_sha256")
        or start.get("role") != "v24800_exact220_execution_start"
        or start.get("status") != "authorized_not_started"
        or start.get("protocol_sha256") != contract.sha256(root / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256") != contract.sha256(root / contract.PREAUDIT)
        or start.get("dependency_manifest_sha256") != protocol["dependency_manifest_sha256"]
        or start.get("protected_watchers") != protocol["execution"]["protected_watchers"]
        or start.get("authorization") != {
            "single_fresh_exact220_forward": True,
            "evaluator_call": False,
            "retry_resume_skip_or_selective_rerun": False,
        }
        or start.get("first_network_model_search_or_fetch_effect_started") is not False
        or not _sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.48.00 execution authorization drifted")
    return start


def _active_conflicts() -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="], stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=False,
    )
    markers = (
        contract.RUNNER_MARKER,
        contract.CHILD_MARKER,
        "scripts/run_v24791_exact220.py",
        "scripts/run_v24791_exact220_task.py",
        "scripts/run_v24792_exact220.py",
        "scripts/run_v24792_exact220_task.py",
        "scripts/run_v24798_exact220.py",
        "scripts/run_v24798_exact220_task.py",
        "scripts/run_v24635_exact220.py",
        "scripts/run_v24635_exact220_task.py",
        "scripts/run_official_eval_local.py",
    )
    output = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3 or "python" not in parts[1].casefold():
            continue
        pid = int(parts[0])
        if pid != os.getpid() and any(marker in parts[2] for marker in markers):
            output.append(pid)
    return sorted(output)


def _validate_bundle(value: dict[str, Any], directory: Path) -> None:
    algorithm._v24800_parent_validate_bundle(value, directory)
    validate_direct_receipt(_read(directory / contract.DIRECT_RECEIPT_NAME))


def _child_env() -> dict[str, str]:
    if len(_credentials) != contract.TAVILY_KEY_SLOT_CAP:
        raise RuntimeError("V2.48.00 in-memory credential pool absent")
    value = algorithm._v24800_parent_child_env()
    value[_CREDENTIAL_ENVIRONMENT] = "\n".join(_credentials)
    return value


def configure_algorithm(credentials: tuple[str, ...]) -> None:
    global _credentials
    _credentials = tuple(credentials)
    if not hasattr(algorithm, "_v24800_parent_validate_bundle"):
        algorithm._v24800_parent_validate_bundle = algorithm._validate_bundle
    if not hasattr(algorithm, "_v24800_parent_child_env"):
        algorithm._v24800_parent_child_env = algorithm._child_env
    bindings = {
        "PROTOCOL_ID": contract.PROTOCOL_ID,
        "CHILD_MARKER": contract.CHILD_MARKER,
        "OUTPUT_ROOT": contract.OUTPUT_ROOT,
        "MODEL_SLOT_DIRECTORY": contract.MODEL_SLOT_DIRECTORY,
        "TASK_ROOT": contract.TASK_ROOT,
        "RUNTIME_PREDICTIONS": contract.RUNTIME_PREDICTIONS,
        "RUN_SUMMARY": contract.RUN_SUMMARY,
        "PREDICTION_FREEZE": contract.PREDICTION_FREEZE,
        "SAFE_PROGRESS": contract.SAFE_PROGRESS,
        "EXECUTOR_CONCURRENCY": contract.EXECUTOR_CONCURRENCY,
        "MODEL_SLOT_CAP": contract.MODEL_SLOT_CAP,
        "LIMITS": contract.LIMITS,
        "PARENT_DEADLINE_GRACE_SECONDS": 30.0,
        "_validate_bundle": _validate_bundle,
        "_child_env": _child_env,
    }
    for name, value in bindings.items():
        setattr(algorithm, name, value)


def _progress(completed: int) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": "v24800_exact220_safe_forward_progress",
        "created_at_unix": int(time.time()),
        "selected": contract.SELECTED_COUNT,
        "completed": completed,
        "unfinished": contract.SELECTED_COUNT - completed,
        "executor_concurrency": contract.EXECUTOR_CONCURRENCY,
        "model_slot_cap": contract.MODEL_SLOT_CAP,
        "tavily_key_slot_cap": contract.TAVILY_KEY_SLOT_CAP,
        "contains_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }
    value["progress_payload_sha256"] = contract.payload_sha256(value)
    return value


def _direct_search_totals(root: Path) -> dict[str, Any]:
    receipts: list[dict[str, Any]] = []
    missing = 0
    invalid = 0
    for position in range(1, contract.SELECTED_COUNT + 1):
        path = (
            root
            / contract.TASK_ROOT
            / f"task_{position:04d}"
            / contract.DIRECT_RECEIPT_NAME
        )
        if not path.exists() and not path.is_symlink():
            missing += 1
            continue
        try:
            receipts.append(validate_direct_receipt(_read(path)))
        except (OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            invalid += 1
    integer_fields = (
        "provider_attempts", "successful_queries", "failed_queries",
        "slot_acquisitions", "slot_timeouts", "key_local_disables",
        "retryable_responses", "transport_failures", "invalid_payloads",
        "credential_echo_rejections", "projected_url_leads",
        "invalid_or_duplicate_results", "status_2xx", "status_401",
        "status_403", "status_408", "status_409", "status_429",
        "status_432", "status_5xx", "status_other",
    )
    totals: dict[str, Any] = {
        "task_receipts": contract.SELECTED_COUNT,
        "valid_receipts": len(receipts),
        "invalid_or_missing_receipts": invalid + missing,
        "invalid_receipts": invalid,
        "missing_receipts": missing,
        "key_slot_cap": contract.TAVILY_KEY_SLOT_CAP,
        **{name: sum(int(item[name]) for item in receipts) for name in integer_fields},
        "total_slot_wait_seconds": round(sum(float(item["total_slot_wait_seconds"]) for item in receipts), 6),
        "max_slot_wait_seconds": max(
            (float(item["max_slot_wait_seconds"]) for item in receipts), default=0.0
        ),
    }
    return totals


def _fixed_full_budget_totals(outcomes: list[Any]) -> dict[str, Any]:
    def bounded_integer(value: object, maximum: int) -> bool:
        return (
            not isinstance(value, bool)
            and isinstance(value, int)
            and 0 <= value <= maximum
        )

    def numeric_zero(value: object) -> bool:
        return (
            not isinstance(value, bool)
            and isinstance(value, (int, float))
            and float(value) == 0.0
        )

    decisions: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    valid = 0
    second_wave = 0
    zero_entropy = 0
    total_queries = 0
    total_fetches = 0
    for item in outcomes:
        result = item.result
        retrieval = result.get("two_wave_retrieval") or {}
        receipt = retrieval.get("receipt") or {}
        controller = receipt.get("controller") or {}
        wave2 = receipt.get("wave2") or {}
        total = receipt.get("total") or {}
        policy = controller.get("policy") or {}
        reason = controller.get("reason")
        decision = controller.get("decision")
        policy_is_fixed_control = (
            policy.get("information_gain_weight") == 0
            and policy.get("latency_loss_per_second") == 0
            and policy.get("minimum_net_value") == -1.0
            and policy.get("maximum_wave1_seconds") == 30.0
            and bounded_integer(policy.get("wave1_queries"), 2)
            and bounded_integer(policy.get("wave1_fetches"), 6)
            and bounded_integer(policy.get("wave2_queries"), 2)
            and bounded_integer(policy.get("wave2_fetches"), 4)
        )
        decision_is_consistent = (
            decision == "expand"
            and reason == "positive_entropy_voc"
            and wave2.get("executed") is True
        ) or (
            decision == "stop"
            and reason in {"latency_ceiling", "no_delta_budget"}
            and wave2.get("executed") is False
        )
        if (
            retrieval.get("status") != "completed"
            or not policy_is_fixed_control
            or controller.get(
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            )
            is not False
            or controller.get("question_text_or_content_read_by_kernel") is not False
            or not decision_is_consistent
            or not isinstance(wave2.get("executed"), bool)
            or not numeric_zero(controller.get("entropy_value"))
            or not numeric_zero(controller.get("latency_cost"))
            or not bounded_integer(total.get("queries_executed"), 4)
            or not bounded_integer(total.get("fetches_attempted"), 10)
        ):
            continue
        valid += 1
        decisions[str(decision)] += 1
        reasons[str(reason)] += 1
        second_wave += int(wave2["executed"])
        zero_entropy += int(numeric_zero(controller["entropy_value"]))
        total_queries += int(total["queries_executed"])
        total_fetches += int(total["fetches_attempted"])
    return {
        "task_results": len(outcomes),
        "valid_control_receipts": valid,
        "invalid_or_missing_control_receipts": len(outcomes) - valid,
        "decision_counts": dict(sorted(decisions.items())),
        "reason_counts": dict(sorted(reasons.items())),
        "second_wave_executed_tasks": second_wave,
        "zero_entropy_value_tasks": zero_entropy,
        "total_queries_executed": total_queries,
        "total_fetches_attempted": total_fetches,
        "entropy_or_information_gain_used_for_admission": False,
        "question_query_url_page_prediction_answer_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }


def main() -> None:
    credentials = _read_credentials()
    configure_algorithm(credentials)
    root = ROOT
    protocol = contract.validate_protocol(root, _read(root / contract.PROTOCOL))
    start = validate_execution_start(root, protocol)
    tasks = contract.task_vector(root, protocol)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True).stdout.strip()
    remote = subprocess.run(["git", "rev-parse", "target/main"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True).stdout.strip()
    if head != remote or dirty:
        raise RuntimeError("V2.48.00 launch requires clean pushed HEAD")
    required = (contract.PROTOCOL, contract.PREAUDIT, contract.EXECUTION_START, *map(Path, protocol["dependency_manifest"]))
    if any(subprocess.run(["git", "ls-files", "--error-unmatch", str(path)], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False).returncode != 0 for path in required):
        raise RuntimeError("V2.48.00 launch dependency is not tracked")
    conflicts = _active_conflicts()
    if conflicts:
        raise RuntimeError(f"V2.48.00 conflicting benchmark/evaluator active: {conflicts}")
    with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
        pass
    for path in (root / contract.FORWARD_RESULT, root / contract.OUTPUT_ROOT):
        if path.exists() or path.is_symlink():
            raise RuntimeError("V2.48.00 forward surface is not pristine")
    with acquire_deepwide_api_lease(root, owner=contract.LEASE_OWNER, purpose=contract.LEASE_PURPOSE, path=root / contract.LEASE_PATH):
        if contract.protected_watcher_snapshot() != protocol["execution"]["protected_watchers"]:
            raise RuntimeError("V2.48.00 protected watcher drifted before effect")
        (root / contract.OUTPUT_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
        algorithm._prepare_slots(root)
        prepare_key_slots(root / contract.KEY_SLOT_DIRECTORY, contract.TAVILY_KEY_SLOT_CAP)
        (root / contract.TASK_ROOT).mkdir(mode=0o700)
        started = time.monotonic()
        outcomes = algorithm.execute_forward(
            root, protocol, tasks,
            progress_writer=lambda value: algorithm._atomic_json(
                root / contract.SAFE_PROGRESS, _progress(int(value["completed"]))
            ),
        )
        wall = max(0.0, time.monotonic() - started)
    rows = [algorithm._runtime_row(item.result) for item in outcomes]
    algorithm._write_jsonl_new(root / contract.RUNTIME_PREDICTIONS, rows)
    summary = algorithm._summary(outcomes, wall)
    summary["role"] = "v24800_exact220_run_summary"
    summary["protocol_id"] = contract.PROTOCOL_ID
    summary["executor_concurrency"] = contract.EXECUTOR_CONCURRENCY
    summary["direct_search_totals"] = _direct_search_totals(root)
    summary["fixed_full_budget_control_totals"] = _fixed_full_budget_totals(
        outcomes
    )
    summary.pop("summary_payload_sha256", None)
    summary["summary_payload_sha256"] = contract.payload_sha256(summary)
    algorithm._new_json(root / contract.RUN_SUMMARY, summary)
    freeze = {
        "artifact_version": 1,
        "role": "v24800_exact220_prediction_freeze",
        "protocol_id": contract.PROTOCOL_ID,
        "selected": contract.SELECTED_COUNT,
        "terminal": contract.SELECTED_COUNT,
        "runtime_predictions_sha256": contract.sha256(root / contract.RUNTIME_PREDICTIONS),
        "run_summary_sha256": contract.sha256(root / contract.RUN_SUMMARY),
        "prediction_hashes_sha256": contract.payload_sha256([row["prediction_sha256"] for row in rows]),
        "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
        "mapping_gold_or_evaluator_opened_or_hashed": False,
        "label_blind": True,
    }
    freeze["freeze_payload_sha256"] = contract.payload_sha256(freeze)
    algorithm._new_json(root / contract.PREDICTION_FREEZE, freeze)
    forward = {
        "artifact_version": 1,
        "role": "v24800_exact220_forward_result",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "selected": contract.SELECTED_COUNT,
        "terminal_predictions": contract.SELECTED_COUNT,
        "model_generated_tables": summary["model_generated_tables"],
        "fallback_tables": summary["fallback_tables"],
        "system_total_tokens": summary["system_total_tokens"],
        "forward_wall_seconds": summary["forward_wall_seconds"],
        "direct_search_totals": summary["direct_search_totals"],
        "fixed_full_budget_control_totals": summary[
            "fixed_full_budget_control_totals"
        ],
        "prediction_freeze_sha256": contract.sha256(root / contract.PREDICTION_FREEZE),
        "run_summary_sha256": contract.sha256(root / contract.RUN_SUMMARY),
        "execution_start_sha256": contract.sha256(root / contract.EXECUTION_START),
        "execution_start_payload_sha256": start["execution_start_payload_sha256"],
        "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "official_evaluator_called": False,
        "retry_resume_skip_or_selective_rerun_launched": False,
    }
    forward["result_payload_sha256"] = contract.payload_sha256(forward)
    algorithm._new_json(root / contract.FORWARD_RESULT, forward)
    algorithm._atomic_json(root / contract.SAFE_PROGRESS, _progress(contract.SELECTED_COUNT))
    print(json.dumps({
        "terminal": contract.SELECTED_COUNT,
        "wall_seconds": wall,
        "fallback_tables": summary["fallback_tables"],
        "direct_search_totals": summary["direct_search_totals"],
        "fixed_full_budget_control_totals": summary[
            "fixed_full_budget_control_totals"
        ],
        "forward_result": str(contract.FORWARD_RESULT),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
