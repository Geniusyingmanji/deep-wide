#!/usr/bin/env python3
"""Read-only preactivation and post-result audit for V2.42.67."""

from __future__ import annotations

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
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.finalize_v24267_exact220 import (  # noqa: E402
    validate_final_result,
    validate_forward_barrier,
)
from scripts.preregister_v24259_deterministic_normalizer_smoke import _matching  # noqa: E402
from scripts.preregister_v24267_exact220 import (  # noqa: E402
    ACTIVATION,
    CHILD_MARKER,
    EXECUTION_START,
    FINALIZER_MARKER,
    FINAL_RESULT,
    FORWARD_RESULT,
    OUTPUT,
    POSTAUDIT,
    PREAUDIT,
    RUNNER_MARKER,
    publish_new,
    validate_protocol,
)
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402
from scripts.run_v24267_exact220 import (  # noqa: E402
    validate_activation,
    validate_execution_start,
    validate_forward_result,
)


FORBIDDEN = frozenset(
    {"category", "question_type", "task_category", "split", "ground_truth", "gold", "answer_key", "mapping", "evaluator", "score", "reward"}
)
SECRET = re.compile(r"(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}")


def _accesses(path: Path, root: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: list[str] = []
    for node in ast.walk(tree):
        value = None
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get" and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            value = node.args[0].value
        elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
            value = node.slice.value
        if value is not None and value.casefold() in FORBIDDEN:
            values.append(f"{path.relative_to(root)}:{node.lineno}:{value}")
    return values


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root, OUTPUT)
    rows = process_snapshot()
    lease = lease_observation(root, Path("/proc"))
    accesses: list[str] = []
    secrets: list[str] = []
    for relative in protocol["forward_surface"]["manifest"]:
        path = root / relative
        accesses.extend(_accesses(path, root))
        if SECRET.search(path.read_text(encoding="utf-8")):
            secrets.append(relative)
    allowed = {"src/deepwide_agent/clients.py:565:score"}
    unexpected = sorted(set(accesses) - allowed)
    runner_source = (root / "scripts/run_v24267_exact220.py").read_text(encoding="utf-8")
    findings: list[str] = []
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if _matching(rows, RUNNER_MARKER):
        findings.append("exact220_runner_already_active")
    if _matching(rows, FINALIZER_MARKER):
        findings.append("exact220_finalizer_already_active")
    if (root / ACTIVATION).exists() or (root / ACTIVATION).is_symlink():
        findings.append("activation_already_present")
    if unexpected:
        findings.append("unexpected_benchmark_privileged_field_access")
    if secrets:
        findings.append("credential_literal_in_forward_surface")
    if "finalize_v24267_exact220" in runner_source or "MAPPING_PATH" in runner_source or "evaluator_mapping" in runner_source:
        findings.append("forward_runner_has_evaluator_side_capability")
    value = {
        "artifact_version": 1,
        "role": "v24267_exact220_preactivation_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / OUTPUT),
        "label_blind": True,
        "runtime_boundary": ["opaque_id", "question"],
        "selected_count": 220,
        "field_accesses": accesses,
        "allowed_provider_search_rank_accesses": sorted(set(accesses).intersection(allowed)),
        "unexpected_benchmark_privileged_field_accesses_absent": not unexpected,
        "credential_literal_hits": secrets,
        "forward_runner_evaluator_side_capability_absent": not any(value in runner_source for value in ("finalize_v24267_exact220", "MAPPING_PATH", "evaluator_mapping")),
        "shared_api_lease_active": lease.get("active") is True,
        "protected_existing_processes_signaled_restarted_or_stopped": False,
        "network_model_search_fetch_or_evaluator_api_called_by_audit": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "findings": findings,
        "launch_authorized": not findings,
        "additional_rollout_avg4_leaderboard_or_sota_authorized": False,
        "audit_valid": True,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def _sealed_file(path: Path, role: str, field: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    if value.get("role") != role or seal != payload_sha256(unsigned):
        raise RuntimeError(f"V2.42.67 sealed artifact drifted: {path}")
    return value


def build_postresult_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root, OUTPUT)
    preaudit = _sealed_file(root / PREAUDIT, "v24267_exact220_preactivation_audit", "audit_payload_sha256")
    activation = validate_activation(root, protocol)
    execution = validate_execution_start(root, protocol, activation)
    forward = json.loads((root / FORWARD_RESULT).read_text(encoding="utf-8"))
    validate_forward_result(root, protocol, forward)
    validate_forward_barrier(root, protocol)
    result = json.loads((root / FINAL_RESULT).read_text(encoding="utf-8"))
    validate_final_result(root, protocol, result)
    rows = process_snapshot()
    lease = lease_observation(root, Path("/proc"))
    runner_present = bool(_matching(rows, RUNNER_MARKER))
    child_present = bool(_matching(rows, CHILD_MARKER))
    finalizer_present = bool(_matching(rows, FINALIZER_MARKER))
    lease_active = lease.get("active") is True
    findings = []
    if runner_present:
        findings.append("forward_runner_present_after_result")
    if child_present:
        findings.append("forward_child_present_after_result")
    if finalizer_present:
        findings.append("finalizer_present_after_result")
    if lease_active:
        findings.append("shared_api_lease_active_after_result")
    value = {
        "artifact_version": 1,
        "role": "v24267_exact220_postresult_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "protocol_sha256": sha256(root / OUTPUT),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "activation_sha256": sha256(root / ACTIVATION),
        "execution_start_sha256": sha256(root / EXECUTION_START),
        "forward_result_sha256": sha256(root / FORWARD_RESULT),
        "final_result_sha256": sha256(root / FINAL_RESULT),
        "forward": {key: forward[key] for key in ("selected", "terminal_predictions", "model_generated_tables", "fallback_tables", "system_total_tokens", "shared_model_receipts")},
        "result": {"selected": result["selected"], "conservative_denominator": result["conservative_denominator"], "metrics": result["metrics"], "claims": result["claims"]},
        "execution_closure": {
            "runner_process_present_after_result": runner_present,
            "child_process_present_after_result": child_present,
            "finalizer_process_present_after_result": finalizer_present,
            "shared_api_lease_active": lease_active,
            "process_signal_restart_skip_selective_retry_or_error_revaluation": False,
            "active_run_killed_or_quarantined": False,
            "invalid_result_path": None,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "exact220_prediction_freeze_before_evaluator_side_open": True,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
            "credential_value_persisted_hashed_or_emitted": False,
        },
        "authorization": {"additional_rollout_or_avg4": False, "leaderboard_submission": False, "sota_claim": False},
        "findings": findings,
        "audit_valid": not findings and preaudit.get("launch_authorized") is True and execution.get("api_called_before_execution_start") is False,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    post = "--post-result" in sys.argv
    path = POSTAUDIT if post else PREAUDIT
    report = build_postresult_report() if post else build_report()
    publish_new(ROOT / path, report)
    print(json.dumps({"path": str(path), "sha256": sha256(ROOT / path)}))
