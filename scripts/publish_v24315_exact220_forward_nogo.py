#!/usr/bin/env python3
"""Publish the terminal, evaluator-blocking V2.43.15 forward NO-GO."""

from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24287_hard_deadline_fetch import (  # noqa: E402
    validate_transport_health,
)
from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    validate_child_receipt,
    validate_parent_receipt,
)
from deepwide_agent.v24310_paired_dev_runtime import (  # noqa: E402
    parent_exit_receipt as recovery_parent_exit_receipt,
)
from deepwide_agent.v24313_runner_integration import (  # noqa: E402
    validate_deadline_model_receipt,
)
from deepwide_agent.v24315_forward_contract import (  # noqa: E402
    ACTIVATION,
    EXECUTION_START,
    FORWARD_CONTRACT,
    FORWARD_RESULT,
    LIMITS,
    MODEL_SLOT_CAP,
    OUTPUT_ROOT,
    PREDICTION_FREEZE,
    PROTOCOL_ID,
    RUNTIME_PREDICTIONS,
    RUN_SUMMARY,
    SELECTED_COUNT,
    TASK_ROOT,
    payload_sha256,
    read_object,
    sha256,
    validate_forward_contract,
)
from scripts.preregister_v24315_exact220 import (  # noqa: E402
    EVALUATOR_ROOT,
    FINAL_RESULT,
    POSTAUDIT,
    PROTOCOL,
    publish_new,
    validate_protocol,
)
from scripts import run_v24315_exact220 as runner  # noqa: E402


RESULT = Path("results/v24315_exact220_forward_nogo_v1_20260803.json")
AUDIT = Path("results/v24315_exact220_forward_nogo_audit_v1_20260803.json")
RESULT_NAME = "result.json"
MODEL_NAME = "model_slot_receipt.json"
TRANSPORT_NAME = "transport_health.json"
CHILD_NAME = "child_terminal_receipt.json"
PARENT_NAME = "parent_exit_receipt.json"


def _present(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def _task_directories(root: Path) -> list[Path]:
    task_root = root / TASK_ROOT
    if task_root.is_symlink() or not task_root.is_dir():
        raise RuntimeError("V2.43.15 terminal task root is absent")
    output = [task_root / f"task_{position:04d}" for position in range(1, SELECTED_COUNT + 1)]
    if any(path.is_symlink() or not path.is_dir() for path in output):
        raise RuntimeError("V2.43.15 terminal task partition is incomplete")
    present = sorted(path for path in task_root.glob("task_*") if path.is_dir())
    if present != output:
        raise RuntimeError("V2.43.15 terminal task partition drifted")
    return output


def _validate_prediction_barrier(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    contract = validate_forward_contract(root)
    validate_protocol(root, PROTOCOL)
    freeze = read_object(root / PREDICTION_FREEZE)
    rows = runner.validate_prediction_freeze(root, contract, freeze)
    if len(rows) != SELECTED_COUNT:
        raise RuntimeError("V2.43.15 terminal prediction barrier is not exact-220")
    summary = read_object(root / RUN_SUMMARY)
    runner.validate_summary(summary)
    return freeze, summary


def _replay_timeout_fallback(
    directory: Path, parent: dict[str, Any]
) -> dict[str, Any]:
    progress = runner._safe_progress(directory / "safe_progress.json")
    model = progress.get("model_cost")
    model = model if isinstance(model, dict) else {}
    requests = int(model.get("requests", 0) or 0)
    attempts = max(requests, int(model.get("attempts", 0) or 0))
    projected = dict(progress)
    projected["admitted_model_calls"] = requests
    projected["model_cost"] = {
        **{
            name: int(model.get(name, 0) or 0)
            for name in (
                "requests",
                "attempts",
                "input_tokens",
                "output_tokens",
                "total_tokens",
            )
        },
        "requests": requests,
        "attempts": attempts,
    }
    recovery = recovery_parent_exit_receipt(
        "candidate",
        provider_requests_lower_bound=requests,
        provider_attempts_lower_bound=attempts,
        admitted_model_effects_upper_bound=int(LIMITS["model_calls"]),
        effect_count_complete=False,
        provider_attempt_count_complete=False,
    )
    task = read_object(directory / "visible_task.json")
    try:
        runner._fallback(
            task,
            kind="hard_deadline_fallback",
            failure=str(parent["failure_taxonomy"]),
            elapsed=float(parent["elapsed_seconds"]),
            progress=projected,
            recovery_receipt=recovery,
        )
    except BaseException as error:
        return {
            "replay_failed": True,
            "exception_type": type(error).__name__,
            "failure_class": (
                "admission_provider_accounting_drift"
                if str(error) == "V2.43.10 admission/provider accounting drifted"
                else "other_validation_failure"
            ),
            "network_model_search_fetch_or_evaluator_called": False,
        }
    return {
        "replay_failed": False,
        "exception_type": None,
        "failure_class": None,
        "network_model_search_fetch_or_evaluator_called": False,
    }


def _disk_observability(root: Path) -> dict[str, Any]:
    taxonomy: Counter[str] = Counter()
    counts: Counter[str] = Counter()
    timeout_stages: Counter[str] = Counter()
    timeout_progress_elapsed: list[float] = []
    timeout_parent_elapsed: list[float] = []
    timeout_replays: Counter[str] = Counter()
    result_failure_stages: Counter[str] = Counter()
    result_failure_types: Counter[str] = Counter()
    result_completion_kinds: Counter[str] = Counter()
    for directory in _task_directories(root):
        parent_path = directory / PARENT_NAME
        if not _present(parent_path):
            raise RuntimeError("V2.43.15 sealed parent receipt is absent")
        parent = validate_parent_receipt(read_object(parent_path))
        counts["parent_receipts_present"] += 1
        counts["parent_receipts_valid"] += 1
        taxonomy[str(parent["failure_taxonomy"])] += 1

        child_path = directory / CHILD_NAME
        if _present(child_path):
            counts["child_receipts_present"] += 1
            validate_child_receipt(read_object(child_path))
            counts["child_receipts_valid"] += 1
        model_path = directory / MODEL_NAME
        if _present(model_path):
            counts["model_receipts_present"] += 1
            validate_deadline_model_receipt(
                read_object(model_path), expected_cap=MODEL_SLOT_CAP
            )
            counts["model_receipts_valid"] += 1
        transport_path = directory / TRANSPORT_NAME
        if _present(transport_path):
            counts["transport_receipts_present"] += 1
            validate_transport_health(read_object(transport_path))
            counts["transport_receipts_valid"] += 1
        result_path = directory / RESULT_NAME
        if _present(result_path):
            counts["result_envelopes_present"] += 1
            envelope = read_object(result_path)
            runner._validate_task_envelope(envelope, directory)
            counts["result_envelopes_valid"] += 1
            result = envelope["result"]
            result_completion_kinds[str(result.get("completion_kind"))] += 1
            failures = result.get("failures")
            if isinstance(failures, list):
                for failure in failures:
                    if not isinstance(failure, dict):
                        continue
                    result_failure_stages[str(failure.get("stage"))] += 1
                    result_failure_types[str(failure.get("type"))] += 1

        if parent["failure_taxonomy"] == "hard_deadline_timeout":
            progress = runner._safe_progress(directory / "safe_progress.json")
            timeout_stages[str(progress.get("stage"))] += 1
            timeout_progress_elapsed.append(float(progress.get("elapsed_seconds", 0.0)))
            timeout_parent_elapsed.append(float(parent["elapsed_seconds"]))
            replay = _replay_timeout_fallback(directory, parent)
            timeout_replays[str(replay["failure_class"])] += 1
    return {
        **{name: int(counts[name]) for name in sorted(counts)},
        "parent_taxonomy": {name: int(taxonomy[name]) for name in sorted(taxonomy)},
        "timeout_content_free_progress": {
            "count": int(taxonomy["hard_deadline_timeout"]),
            "stage_counts": {name: int(timeout_stages[name]) for name in sorted(timeout_stages)},
            "progress_elapsed_seconds_min": min(timeout_progress_elapsed, default=0.0),
            "progress_elapsed_seconds_max": max(timeout_progress_elapsed, default=0.0),
            "parent_elapsed_seconds_min": min(timeout_parent_elapsed, default=0.0),
            "parent_elapsed_seconds_max": max(timeout_parent_elapsed, default=0.0),
            "model_requests_before_stall_per_task": 1,
            "hosted_search_terminal_calls_before_stall_per_task": 0,
            "contains_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
        },
        "timeout_fallback_replay": {
            "count": sum(timeout_replays.values()),
            "failure_classes": {
                name: int(timeout_replays[name]) for name in sorted(timeout_replays)
            },
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "result_envelope_completion_kinds": {
            name: int(result_completion_kinds[name])
            for name in sorted(result_completion_kinds)
        },
        "result_envelope_failure_events": {
            "stage_counts": {
                name: int(result_failure_stages[name])
                for name in sorted(result_failure_stages)
            },
            "coarse_type_counts": {
                name: int(result_failure_types[name])
                for name in sorted(result_failure_types)
            },
        },
    }


def validate_result(root: Path, value: dict[str, Any]) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    freeze, summary = _validate_prediction_barrier(root)
    disk = value.get("disk_observability") or {}
    expected_disk = _disk_observability(root)
    summary_observability = summary["parent_exit_observability"]
    gate = value.get("forward_gate") or {}
    checks = gate.get("checks") or {}
    expected_checks = {
        "terminal_predictions": True,
        "parent_exit_receipts": disk.get("parent_receipts_valid") == SELECTED_COUNT,
        "valid_child_terminal_receipts": disk.get("child_receipts_valid") == SELECTED_COUNT,
        "valid_model_slot_receipts": disk.get("model_receipts_valid") == SELECTED_COUNT,
        "valid_transport_receipts": disk.get("transport_receipts_valid") == SELECTED_COUNT,
        "non_success_parent_exits": disk.get("parent_taxonomy", {}).get("success", 0) == SELECTED_COUNT,
        "incomplete_effect_counts": summary_observability.get("incomplete_effect_counts") == 0,
        "fourth_model_effects": summary["mechanism_totals"].get("fourth_model_effect") == 0,
    }
    failed = sorted(name for name, passed in expected_checks.items() if not passed)
    if (
        value.get("role") != "v24315_exact220_forward_nogo"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("status") != "terminal_forward_gate_no_go"
        or value.get("selected") != SELECTED_COUNT
        or value.get("terminal_predictions") != SELECTED_COUNT
        or value.get("prediction_freeze_sha256") != sha256(root / PREDICTION_FREEZE)
        or value.get("runtime_predictions_sha256") != sha256(root / RUNTIME_PREDICTIONS)
        or value.get("run_summary_sha256") != sha256(root / RUN_SUMMARY)
        or value.get("provenance")
        != {
            "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
            "protocol_sha256": sha256(root / PROTOCOL),
            "activation_sha256": sha256(root / ACTIVATION),
            "execution_start_sha256": sha256(root / EXECUTION_START),
        }
        or disk != expected_disk
        or value.get("forward_summary")
        != {
            name: summary[name]
            for name in (
                "model_generated_tables",
                "fallback_tables",
                "completion_kinds",
                "system_total_tokens",
                "task_wall_seconds_sum",
                "forward_wall_seconds",
                "hard_fetch_helper_calls",
                "hard_fetch_deadline_failures",
                "fetch_helper_failures",
                "parent_exit_observability",
                "mechanism_totals",
            )
        }
        or checks != expected_checks
        or gate.get("failed_checks") != failed
        or gate.get("passed") is not False
        or value.get("evaluation_authorized") is not False
        or value.get("official_evaluator_called") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
        or value.get("benchmark_score_available") is not False
        or value.get("authorization")
        != {
            "postterminal_diagnosis": True,
            "v24316_runner_integration_design": True,
            "same_run_evaluator": False,
            "same_run_retry_resume_or_selective_rerun": False,
            "additional_rollout": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        }
        or freeze.get("mapping_gold_or_evaluator_opened_or_hashed") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.43.15 forward NO-GO result drifted")


def build_result(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    if (root / RESULT).exists() or (root / RESULT).is_symlink():
        raise FileExistsError(root / RESULT)
    if (root / FORWARD_RESULT).exists() or (root / FORWARD_RESULT).is_symlink():
        raise RuntimeError("V2.43.15 success forward result unexpectedly exists")
    if any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (EVALUATOR_ROOT, FINAL_RESULT, POSTAUDIT)
    ):
        raise RuntimeError("V2.43.15 evaluator-side surface unexpectedly exists")
    freeze, summary = _validate_prediction_barrier(root)
    disk = _disk_observability(root)
    summary_observability = summary["parent_exit_observability"]
    checks = {
        "terminal_predictions": freeze["terminal"] == SELECTED_COUNT,
        "parent_exit_receipts": disk["parent_receipts_valid"] == SELECTED_COUNT,
        "valid_child_terminal_receipts": disk.get("child_receipts_valid", 0) == SELECTED_COUNT,
        "valid_model_slot_receipts": disk.get("model_receipts_valid", 0) == SELECTED_COUNT,
        "valid_transport_receipts": disk.get("transport_receipts_valid", 0) == SELECTED_COUNT,
        "non_success_parent_exits": disk["parent_taxonomy"].get("success", 0) == SELECTED_COUNT,
        "incomplete_effect_counts": summary_observability["incomplete_effect_counts"] == 0,
        "fourth_model_effects": summary["mechanism_totals"]["fourth_model_effect"] == 0,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v24315_exact220_forward_nogo",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "terminal_forward_gate_no_go",
        "selected": SELECTED_COUNT,
        "terminal_predictions": SELECTED_COUNT,
        "provenance": {
            "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
            "protocol_sha256": sha256(root / PROTOCOL),
            "activation_sha256": sha256(root / ACTIVATION),
            "execution_start_sha256": sha256(root / EXECUTION_START),
        },
        "prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
        "runtime_predictions_sha256": sha256(root / RUNTIME_PREDICTIONS),
        "run_summary_sha256": sha256(root / RUN_SUMMARY),
        "forward_summary": {
            name: summary[name]
            for name in (
                "model_generated_tables",
                "fallback_tables",
                "completion_kinds",
                "system_total_tokens",
                "task_wall_seconds_sum",
                "forward_wall_seconds",
                "hard_fetch_helper_calls",
                "hard_fetch_deadline_failures",
                "fetch_helper_failures",
                "parent_exit_observability",
                "mechanism_totals",
            )
        },
        "disk_observability": disk,
        "summary_disk_discrepancy": {
            "disk_parent_receipts_valid": disk["parent_receipts_valid"],
            "frozen_summary_parent_receipts_valid": summary_observability["receipts_valid"],
            "difference": disk["parent_receipts_valid"] - summary_observability["receipts_valid"],
            "timeout_parent_receipts_lost_from_in_memory_outcome_projection": disk[
                "timeout_fallback_replay"
            ]["failure_classes"].get("admission_provider_accounting_drift", 0),
            "frozen_summary_or_predictions_modified": False,
        },
        "forward_gate": {
            "checks": checks,
            "failed_checks": failed,
            "passed": False,
        },
        "failure_as_zero_predictions_frozen": True,
        "evaluation_authorized": False,
        "official_evaluator_called": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "benchmark_score_available": False,
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "all_220_predictions_frozen_before_postterminal_diagnosis": True,
            "question_opaque_id_prediction_url_page_or_credential_emitted_by_publication": False,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
        },
        "authorization": {
            "postterminal_diagnosis": True,
            "v24316_runner_integration_design": True,
            "same_run_evaluator": False,
            "same_run_retry_resume_or_selective_rerun": False,
            "additional_rollout": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
    validate_result(root, value)
    return value


if __name__ == "__main__":
    result = build_result()
    publish_new(ROOT / RESULT, result)
    print(
        json.dumps(
            {
                "path": str(RESULT),
                "status": result["status"],
                "failed_checks": result["forward_gate"]["failed_checks"],
            },
            sort_keys=True,
        )
    )
