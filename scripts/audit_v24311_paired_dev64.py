#!/usr/bin/env python3
"""Strict label-blind preactivation/post-result audit for V2.43.11."""

from __future__ import annotations

import ast
import json
import re
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24311_forward_contract import (  # noqa: E402
    ACTIVATION,
    CHILD_MARKER,
    EXECUTION_START,
    FORWARD_CONTRACT,
    FORWARD_RESULT,
    FULL_PROTOCOL,
    OUTPUT_ROOT,
    POSTAUDIT,
    PREAUDIT,
    protected_watcher_snapshot,
    RUNNER_MARKER,
    payload_sha256,
    sha256,
    validate_forward_contract,
)
from scripts.audit_v24187_phase_liveness import process_snapshot  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.preregister_v24259_deterministic_normalizer_smoke import (  # noqa: E402
    _matching,
)
from scripts.preregister_v24311_paired_dev64 import (  # noqa: E402
    publish_new,
    validate_protocol,
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


def _accesses(path: Path, root: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: list[str] = []
    for node in ast.walk(tree):
        key = None
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            key = node.args[0].value
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            key = node.slice.value
        if key is not None and key.casefold() in FORBIDDEN:
            values.append(f"{path.relative_to(root)}:{node.lineno}:{key}")
    return values


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    contract = validate_forward_contract(root)
    protocol = validate_protocol(root)
    rows = process_snapshot()
    lease = lease_observation(root, Path("/proc"))
    accesses: list[str] = []
    secrets: list[str] = []
    for relative in contract["dependency_manifest"]:
        path = root / relative
        accesses.extend(_accesses(path, root))
        if SECRET.search(path.read_text(encoding="utf-8")):
            secrets.append(relative)
    allowed = {"src/deepwide_agent/clients.py:565:score"}
    unexpected = sorted(set(accesses) - allowed)
    runner_source = (root / RUNNER_MARKER).read_text(encoding="utf-8")
    child_source = (root / CHILD_MARKER).read_text(encoding="utf-8")
    evaluator_markers = (
        "run_official_eval_local",
        "finalize_v24311_paired_dev64",
        "evaluator_mapping",
        "MAPPING_PATH",
        "EVALUATOR_ROOT",
    )
    findings: list[str] = []
    try:
        protected = protected_watcher_snapshot()
    except RuntimeError:
        protected = []
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if _matching(rows, RUNNER_MARKER):
        findings.append("paired_dev64_runner_already_active")
    if _matching(rows, CHILD_MARKER):
        findings.append("paired_dev64_child_already_active")
    if (root / ACTIVATION).exists() or (root / ACTIVATION).is_symlink():
        findings.append("activation_already_present")
    if any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (EXECUTION_START, FORWARD_RESULT, OUTPUT_ROOT)
    ):
        findings.append("forward_future_surface_not_pristine")
    if unexpected:
        findings.append("unexpected_benchmark_privileged_field_access")
    if secrets:
        findings.append("credential_literal_in_forward_surface")
    if any(marker in runner_source or marker in child_source for marker in evaluator_markers):
        findings.append("forward_has_evaluator_side_capability")
    value = {
        "artifact_version": 1,
        "role": "v24311_paired_dev64_preactivation_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "protocol_sha256": sha256(root / FULL_PROTOCOL),
        "dependency_manifest_sha256": contract["dependency_manifest_sha256"],
        "control_manifest_sha256": protocol["control_manifest_sha256"],
        "runtime_boundary": ["opaque_id", "question"],
        "selected_per_arm": 64,
        "fresh_both_arms": True,
        "field_accesses": accesses,
        "allowed_provider_result_rank_accesses": sorted(
            set(accesses).intersection(allowed)
        ),
        "unexpected_benchmark_privileged_field_accesses_absent": not unexpected,
        "credential_literal_hits": secrets,
        "forward_evaluator_side_capability_absent": not any(
            marker in runner_source or marker in child_source
            for marker in evaluator_markers
        ),
        "shared_api_lease_active": lease.get("active") is True,
        "protected_watchers": protected,
        "protected_existing_processes_signaled_restarted_or_stopped": False,
        "network_model_search_fetch_or_evaluator_api_called_by_audit": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "findings": findings,
        "launch_authorized": not findings,
        "audit_valid": True,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def build_postresult_report(
    root: Path = ROOT, *, now: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    from scripts.finalize_v24311_paired_dev64 import validate_final_result
    from scripts.run_v24311_paired_dev64 import validate_forward_result

    contract = validate_forward_contract(root)
    protocol = validate_protocol(root)
    forward = json.loads((root / FORWARD_RESULT).read_text(encoding="utf-8"))
    validate_forward_result(root, contract, forward)
    result_path = root / protocol["result_paths"]["final_result"]
    result = json.loads(result_path.read_text(encoding="utf-8"))
    validate_final_result(root, protocol, result)
    rows = process_snapshot()
    lease = lease_observation(root, Path("/proc"))
    runner = bool(_matching(rows, RUNNER_MARKER))
    child = bool(_matching(rows, CHILD_MARKER))
    active = lease.get("active") is True
    findings: list[str] = []
    if runner:
        findings.append("forward_runner_present_after_result")
    if child:
        findings.append("forward_child_present_after_result")
    if active:
        findings.append("shared_api_lease_active_after_result")
    value = {
        "artifact_version": 1,
        "role": "v24311_paired_dev64_postresult_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / FULL_PROTOCOL),
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "activation_sha256": sha256(root / ACTIVATION),
        "execution_start_sha256": sha256(root / EXECUTION_START),
        "forward_result_sha256": sha256(root / FORWARD_RESULT),
        "final_result_sha256": sha256(result_path),
        "execution_closure": {
            "runner_process_present_after_result": runner,
            "child_process_present_after_result": child,
            "shared_api_lease_active": active,
            "process_signal_restart_resume_skip_selective_retry_or_error_revaluation": False,
            "active_run_killed_or_quarantined": False,
            "invalid_result_path": None,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "both_arm_prediction_freezes_before_mapping_or_evaluator_open": True,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        },
        "authorization": {
            "additional_dev64_or_exact220": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
        "findings": findings,
        "audit_valid": not findings,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    post = "--post-result" in sys.argv
    report = build_postresult_report() if post else build_report()
    path = POSTAUDIT if post else PREAUDIT
    publish_new(ROOT / path, report)
    print(
        json.dumps(
            {"path": str(path), "audit_valid": report["audit_valid"]},
            sort_keys=True,
        )
    )
