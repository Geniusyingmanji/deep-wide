#!/usr/bin/env python3
"""Read-only preactivation audit for V2.42.63."""

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
from scripts.preregister_v24259_deterministic_normalizer_smoke import _matching  # noqa: E402
from scripts.preregister_v24263_model_limited_capacity import (  # noqa: E402
    ACTIVATION,
    MODEL_SLOT_CAP,
    OUTPUT,
    PREAUDIT,
    RUNNER_MARKER,
    WATCHER_MARKER,
    publish_new,
    validate_protocol,
)
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402


ROLE = "v24263_model_limited_capacity_preactivation_audit"
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


def _field_accesses(path: Path) -> list[str]:
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
            findings.append(f"{path.relative_to(ROOT)}:{node.lineno}:{value}")
    return findings


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root, OUTPUT)
    rows = process_snapshot()
    lease = lease_observation(root, Path("/proc"))
    accesses: list[str] = []
    secret_hits: list[str] = []
    for relative in protocol["forward_surface"]["manifest"]:
        path = root / relative
        accesses.extend(_field_accesses(path))
        if SECRET.search(path.read_text(encoding="utf-8")):
            secret_hits.append(relative)
    # The generic provider client copies an untrusted search ranking score.
    # It is not a benchmark label or evaluator score and does not route work.
    allowed = {"src/deepwide_agent/clients.py:565:score"}
    unexpected = sorted(set(accesses) - allowed)
    limiter_source = (root / "src/deepwide_agent/v24263_global_model_limiter.py").read_text(encoding="utf-8")
    task_source = (root / "scripts/run_v24263_score_first_task.py").read_text(encoding="utf-8")
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
    if "search = AnthropicSearchClient" not in task_source or "model = GlobalModelSlotLimiter" not in task_source:
        findings.append("model_limiter_or_unlocked_search_boundary_absent")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / OUTPUT),
        "label_blind": True,
        "runtime_boundary": ["opaque_id", "question"],
        "global_model_slot_cap": MODEL_SLOT_CAP,
        "field_accesses": accesses,
        "allowed_provider_search_rank_accesses": sorted(set(accesses).intersection(allowed)),
        "unexpected_benchmark_privileged_field_accesses_absent": not unexpected,
        "kernel_model_slot_lock_present": "fcntl.flock" in limiter_source,
        "search_and_fetch_outside_model_limiter": "search = AnthropicSearchClient" in task_source,
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


if __name__ == "__main__":
    publish_new(ROOT / PREAUDIT, build_report())
    print(json.dumps({"path": str(PREAUDIT), "sha256": sha256(ROOT / PREAUDIT)}))
