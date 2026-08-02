#!/usr/bin/env python3
"""Strict label-blind preactivation and post-result audit for V2.42.71."""

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
from scripts.finalize_v24271_keyless_dev64 import (  # noqa: E402
    validate_candidate_barrier,
    validate_final_result,
)
from scripts.preregister_v24259_deterministic_normalizer_smoke import _matching  # noqa: E402
from scripts.preregister_v24271_keyless_dev64 import (  # noqa: E402
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
    SELECTED_COUNT,
    publish_new,
    validate_protocol,
)
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    read_object,
    sha256,
)
from deepwide_agent.v24271_forward_contract import (  # noqa: E402
    FORWARD_PROTOCOL,
)
from scripts.run_v24271_keyless_dev64 import (  # noqa: E402
    validate_activation,
    validate_execution_start,
    validate_forward_result,
)


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
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
FORWARD_CAPABILITY_MARKERS = (
    "finalize_v24271_keyless_dev64",
    "preregister_v24271_keyless_dev64",
    "MAPPING_PATH",
    "CONTROL_RUNTIME",
    "CONTROL_RESULT",
    "CONTROL_POSTAUDIT",
    "evaluator_mapping",
    "overall_20250916",
)
RUNNER_FORBIDDEN_IMPORTS = (
    "preregister_v24271_keyless_dev64",
    "finalize_v24271_keyless_dev64",
    "audit_v24271_keyless_dev64",
)
DEPENDENCY_IMPORT_ALLOWLIST = frozenset(
    {
        "scripts.deepwide_api_lease",
    }
)


def _accesses(path: Path, root: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: list[str] = []
    for node in ast.walk(tree):
        value = None
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
            values.append(f"{path.relative_to(root)}:{node.lineno}:{value}")
    return values


def _script_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            values.extend(alias.name for alias in node.names if alias.name.startswith("scripts"))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith("scripts"):
                values.append(module)
    return values


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root, OUTPUT)
    rows = process_snapshot()
    lease = lease_observation(root, Path("/proc"))
    accesses: list[str] = []
    secrets: list[str] = []
    capability_hits: list[str] = []
    unexpected_script_imports: list[str] = []
    for relative in protocol["forward_surface"]["dependency_manifest"]:
        path = root / relative
        source = path.read_text(encoding="utf-8")
        accesses.extend(_accesses(path, root))
        if SECRET.search(source):
            secrets.append(relative)
        for marker in FORWARD_CAPABILITY_MARKERS:
            if marker in source:
                capability_hits.append(f"{relative}:{marker}")
        for module in _script_imports(path):
            if module not in DEPENDENCY_IMPORT_ALLOWLIST:
                unexpected_script_imports.append(f"{relative}:{module}")
    runner_path = root / "scripts/run_v24271_keyless_dev64.py"
    runner_source = runner_path.read_text(encoding="utf-8")
    runner_digest = protocol["forward_surface"]["entry_manifest"].get(
        "scripts/run_v24271_keyless_dev64.py"
    )
    if sha256(runner_path) != runner_digest:
        capability_hits.append("scripts/run_v24271_keyless_dev64.py:hash_drift")
    for marker in RUNNER_FORBIDDEN_IMPORTS:
        if marker in runner_source:
            capability_hits.append(f"scripts/run_v24271_keyless_dev64.py:{marker}")
    for module in _script_imports(runner_path):
        if module not in DEPENDENCY_IMPORT_ALLOWLIST:
            unexpected_script_imports.append(
                f"scripts/run_v24271_keyless_dev64.py:{module}"
            )
    # Provider-internal score is a relevance field, not benchmark score.
    allowed = {"src/deepwide_agent/clients.py:565:score"}
    unexpected = sorted(set(accesses) - allowed)
    findings: list[str] = []
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if _matching(rows, RUNNER_MARKER):
        findings.append("dev64_runner_already_active")
    if _matching(rows, FINALIZER_MARKER):
        findings.append("dev64_finalizer_already_active")
    if (root / ACTIVATION).exists() or (root / ACTIVATION).is_symlink():
        findings.append("activation_already_present")
    if unexpected:
        findings.append("unexpected_benchmark_privileged_field_access")
    if secrets:
        findings.append("credential_literal_in_forward_surface")
    if capability_hits:
        findings.append("forward_import_closure_has_evaluator_side_capability")
    if unexpected_script_imports:
        findings.append("forward_import_closure_has_unfrozen_script_dependency")
    value = {
        "artifact_version": 1,
        "role": "v24271_keyless_dev64_preactivation_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / OUTPUT),
        "forward_contract_sha256": sha256(root / FORWARD_PROTOCOL),
        "forward_contract_payload_sha256": protocol["forward_runtime_contract"][
            "payload_sha256"
        ],
        "label_blind": True,
        "runtime_boundary": ["opaque_id", "question"],
        "selected_count": SELECTED_COUNT,
        "frozen_opaque_allowlist_without_label_fields": True,
        "field_accesses": accesses,
        "allowed_provider_search_rank_accesses": sorted(
            set(accesses).intersection(allowed)
        ),
        "unexpected_benchmark_privileged_field_accesses_absent": not unexpected,
        "credential_literal_hits": secrets,
        "forward_evaluator_side_capability_hits": capability_hits,
        "forward_import_closure_evaluator_side_capability_absent": not capability_hits,
        "unexpected_script_imports": unexpected_script_imports,
        "forward_import_closure_unfrozen_script_dependency_absent": not unexpected_script_imports,
        "shared_api_lease_active": lease.get("active") is True,
        "protected_existing_processes_signaled_restarted_or_stopped": False,
        "network_model_search_fetch_or_evaluator_api_called_by_audit": False,
        "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read": False,
        "findings": findings,
        "launch_authorized": not findings,
        "new_exact220_or_sota_authorized": False,
        "audit_valid": True,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def _sealed_file(path: Path, role: str, field: str) -> dict[str, Any]:
    value = read_object(path)
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    if value.get("role") != role or seal != payload_sha256(unsigned):
        raise RuntimeError(f"V2.42.71 sealed artifact drifted: {path}")
    return value


def build_postresult_report(
    root: Path = ROOT, *, now: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root, OUTPUT)
    preaudit = _sealed_file(
        root / PREAUDIT,
        "v24271_keyless_dev64_preactivation_audit",
        "audit_payload_sha256",
    )
    activation = validate_activation(root, protocol)
    execution = validate_execution_start(root, protocol, activation)
    forward = read_object(root / FORWARD_RESULT)
    validate_forward_result(root, protocol, forward)
    validate_candidate_barrier(root)
    result = read_object(root / FINAL_RESULT)
    validate_final_result(root, protocol, result)
    rows = process_snapshot()
    lease = lease_observation(root, Path("/proc"))
    runner_present = bool(_matching(rows, RUNNER_MARKER))
    child_present = bool(_matching(rows, CHILD_MARKER))
    finalizer_present = bool(_matching(rows, FINALIZER_MARKER))
    lease_active = lease.get("active") is True
    findings: list[str] = []
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
        "role": "v24271_keyless_dev64_postresult_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "protocol_sha256": sha256(root / OUTPUT),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "activation_sha256": sha256(root / ACTIVATION),
        "execution_start_sha256": sha256(root / EXECUTION_START),
        "forward_result_sha256": sha256(root / FORWARD_RESULT),
        "final_result_sha256": sha256(root / FINAL_RESULT),
        "forward": {
            key: forward[key]
            for key in (
                "selected",
                "terminal_predictions",
                "model_generated_tables",
                "fallback_tables",
                "cost_totals",
                "stage_seconds_sum",
                "wall_seconds_sum",
                "shared_model_receipts",
            )
        },
        "result": {
            "status": result["status"],
            "selected_per_arm": result["selected_per_arm"],
            "control": result["control"],
            "candidate": result["candidate"],
            "decision": result["decision"],
            "claims": result["claims"],
        },
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
            "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "candidate_exact64_freeze_before_control_mapping_gold_or_evaluator_open": True,
            "both_arms_fully_evaluated_with_same_current_judge": True,
            "old_evaluator_rows_reused": False,
            "selective_changed_prediction_evaluation": False,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
            "credential_value_persisted_hashed_or_emitted": False,
        },
        "authorization": {
            "entropy_voc_successor_design": result["decision"]["passed"],
            "new_exact220_launch": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "findings": findings,
        "audit_valid": not findings
        and preaudit.get("launch_authorized") is True
        and execution.get("api_called_before_execution_start") is False,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    post = "--post-result" in sys.argv
    path = POSTAUDIT if post else PREAUDIT
    report = build_postresult_report() if post else build_report()
    publish_new(ROOT / path, report)
    print(json.dumps({"path": str(path), "sha256": sha256(ROOT / path)}))
