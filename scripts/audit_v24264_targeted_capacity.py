#!/usr/bin/env python3
"""Read-only preactivation and post-result audit for V2.42.64."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.audit_v24187_phase_liveness import process_snapshot  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.preregister_v24259_deterministic_normalizer_smoke import (  # noqa: E402
    _matching,
)
from scripts.preregister_v24264_targeted_capacity import (  # noqa: E402
    ACTIVATION,
    EXECUTION_START,
    LEVELS,
    MODEL_SLOT_CAP,
    OUTPUT,
    POSTAUDIT,
    PREAUDIT,
    RESULT,
    RUNNER_MARKER,
    WATCHER_MARKER,
    publish_new,
    validate_protocol,
)
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    read_object,
    sha256,
)
from scripts.run_v24264_targeted_capacity import validate_result  # noqa: E402


PRE_ROLE = "v24264_targeted_capacity_preactivation_audit"
POST_ROLE = "v24264_targeted_capacity_postresult_audit"
FORBIDDEN = frozenset(
    {
        "category",
        "question_type",
        "task_category",
        "split",
        "ground_truth",
        "gold",
        "answer_key",
        "mapping",
        "evaluator",
        "score",
        "reward",
    }
)
SECRET = re.compile(r"(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}")


def _field_accesses(path: Path, root: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    findings: list[str] = []
    for node in ast.walk(tree):
        value: str | None = None
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            value = node.args[0].value
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            value = node.slice.value
        if value is not None and value.casefold() in FORBIDDEN:
            findings.append(f"{path.relative_to(root)}:{node.lineno}:{value}")
    return findings


def build_preactivation_report(
    root: Path = ROOT, *, now: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root, OUTPUT)
    rows = process_snapshot()
    lease = lease_observation(root, Path("/proc"))
    accesses: list[str] = []
    secret_hits: list[str] = []
    for relative in protocol["forward_surface"]["manifest"]:
        path = root / relative
        accesses.extend(_field_accesses(path, root))
        if SECRET.search(path.read_text(encoding="utf-8")):
            secret_hits.append(relative)
    allowed = {"src/deepwide_agent/clients.py:565:score"}
    unexpected = sorted(set(accesses) - allowed)
    limiter_source = (
        root / "src/deepwide_agent/v24263_global_model_limiter.py"
    ).read_text(encoding="utf-8")
    task_source = (root / "scripts/run_v24263_score_first_task.py").read_text(
        encoding="utf-8"
    )
    findings: list[str] = []
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if _matching(rows, RUNNER_MARKER):
        findings.append("capacity_runner_already_active")
    if _matching(rows, WATCHER_MARKER):
        findings.append("capacity_watcher_already_active")
    if (root / ACTIVATION).exists() or (root / ACTIVATION).is_symlink():
        findings.append("activation_already_present")
    if unexpected:
        findings.append("unexpected_benchmark_privileged_field_access")
    if secret_hits:
        findings.append("credential_literal_in_forward_surface")
    if "fcntl.flock" not in limiter_source or "LOCK_NB" not in limiter_source:
        findings.append("kernel_model_slot_lock_absent")
    if (
        "search = AnthropicSearchClient" not in task_source
        or "model = GlobalModelSlotLimiter" not in task_source
    ):
        findings.append("model_limiter_or_unlocked_search_boundary_absent")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": PRE_ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / OUTPUT),
        "label_blind": True,
        "runtime_boundary": ["opaque_id", "question"],
        "target_levels": list(LEVELS),
        "global_model_slot_cap": MODEL_SLOT_CAP,
        "field_accesses": accesses,
        "allowed_provider_search_rank_accesses": sorted(
            set(accesses).intersection(allowed)
        ),
        "unexpected_benchmark_privileged_field_accesses_absent": not unexpected,
        "kernel_model_slot_lock_present": "fcntl.flock" in limiter_source,
        "search_and_fetch_outside_model_limiter": (
            "search = AnthropicSearchClient" in task_source
        ),
        "credential_literal_hits": secret_hits,
        "shared_api_lease_active": lease.get("active") is True,
        "protected_existing_processes_signaled_restarted_or_stopped": False,
        "network_model_search_fetch_or_evaluator_api_called_by_audit": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "prediction_question_query_url_page_answer_opaque_id_or_credential_read_or_emitted": False,
        "findings": findings,
        "launch_authorized": not findings,
        "official_evaluator_dev64_full220_or_leaderboard_authorized": False,
        "audit_valid": True,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def _sealed_file(root: Path, path: Path, role: str, seal_name: str) -> dict[str, Any]:
    value = read_object(root / path)
    unsigned = dict(value)
    seal = unsigned.pop(seal_name, None)
    if value.get("role") != role or seal != payload_sha256(unsigned):
        raise RuntimeError(f"V2.42.64 sealed artifact drifted: {path}")
    return value


def build_postresult_report(
    root: Path = ROOT, *, now: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root, OUTPUT)
    preaudit = _sealed_file(root, PREAUDIT, PRE_ROLE, "audit_payload_sha256")
    activation = _sealed_file(
        root, ACTIVATION, "v24264_targeted_capacity_activation", "activation_payload_sha256"
    )
    execution = _sealed_file(
        root,
        EXECUTION_START,
        "v24264_targeted_capacity_execution_start",
        "execution_start_payload_sha256",
    )
    result = read_object(root / RESULT)
    validate_result(protocol, result)
    rows = process_snapshot()
    lease = lease_observation(root, Path("/proc"))
    levels = result["levels"]
    task_rows = [
        row for level in levels for wave in level["waves"] for row in wave["tasks"]
    ]
    model_errors = sum(
        failure == "ModelRequestError"
        for row in task_rows
        for failure in row["failure_types"]
    )
    invalid_receipts = sum(
        not bool(row["model_slot_receipt_valid"]) for row in task_rows
    )
    stage_failures = sum(len(row["failure_types"]) for row in task_rows)
    infrastructure_fallbacks = sum(
        bool(row["infrastructure_fallback"]) for row in task_rows
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": POST_ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "protocol_sha256": sha256(root / OUTPUT),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "activation_sha256": sha256(root / ACTIVATION),
        "execution_start_sha256": sha256(root / EXECUTION_START),
        "result": {
            "path": str(RESULT),
            "sha256": sha256(root / RESULT),
            "capacity_gate": result["capacity_gate"],
            "selected_executor_concurrency": result[
                "selected_executor_concurrency"
            ],
            "total_executions": result["total_executions"],
            "stopped_after_first_failed_level": result[
                "stopped_after_first_failed_level"
            ],
            "levels": [
                {
                    key: level[key]
                    for key in (
                        "concurrency",
                        "executions",
                        "model_generated",
                        "stage_failures",
                        "infrastructure_fallbacks",
                        "model_request_error_count",
                        "model_slot_receipt_invalid_count",
                        "median_wall_seconds",
                        "p95_wall_seconds",
                        "effective_speedup",
                        "effective_tasks_per_second",
                        "passed",
                        "findings",
                    )
                }
                for level in levels
            ],
        },
        "mechanism_evidence": {
            "global_model_slot_cap": MODEL_SLOT_CAP,
            "valid_model_slot_receipts": len(task_rows) - invalid_receipts,
            "model_slot_receipt_invalid_count": invalid_receipts,
            "model_request_errors": model_errors,
            "stage_failures": stage_failures,
            "infrastructure_fallbacks": infrastructure_fallbacks,
            "matched_task_wall_ratios_diagnostic_only": True,
        },
        "execution_closure": {
            "runner_process_present_after_result": bool(
                _matching(rows, RUNNER_MARKER)
            ),
            "child_process_present_after_result": bool(
                _matching(rows, protocol["execution"]["task_runner_marker"])
            ),
            "watcher_process_present_after_result": bool(
                _matching(rows, WATCHER_MARKER)
            ),
            "shared_api_lease_active": lease.get("active") is True,
            "process_signal_restart_resume_skip_or_selective_retry": False,
            "active_run_killed_or_quarantined": False,
            "invalid_result_path": None,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
            "same_run_evaluator_feedback_used_for_forward_or_tuning": False,
            "prediction_question_query_url_page_answer_opaque_id_or_credential_emitted_by_result_or_audit": False,
            "network_model_search_fetch_or_evaluator_api_called_by_postresult_audit": False,
        },
        "authorization": {
            "paired_dev64_successor_design": result["capacity_gate"] == "go",
            "official_evaluator_call": False,
            "paired_dev64_launch": False,
            "full220_launch": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "claims": {
            "target_concurrency_four_stable": any(
                level["concurrency"] == 4 and level["passed"] for level in levels
            ),
            "benchmark_quality_improvement_observed": False,
            "paired_quality_result_available": False,
            "sota": False,
        },
        "audit_valid": (
            preaudit.get("launch_authorized") is True
            and activation.get("status") == "active"
            and execution.get("api_called_before_execution_start") is False
            and not _matching(rows, RUNNER_MARKER)
            and not _matching(rows, protocol["execution"]["task_runner_marker"])
            and not _matching(rows, WATCHER_MARKER)
            and lease.get("active") is False
        ),
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--postresult", action="store_true")
    args = parser.parse_args()
    path = POSTAUDIT if args.postresult else PREAUDIT
    report = (
        build_postresult_report() if args.postresult else build_preactivation_report()
    )
    publish_new(ROOT / path, report)
    print(json.dumps({"path": str(path), "sha256": sha256(ROOT / path)}))
