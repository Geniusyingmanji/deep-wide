"""Strict label-blind forward contract for the V2.42.71 dev64 gate.

This module is the only protocol module imported by the forward runner.  It
deliberately has no historical-control, mapping, gold, evaluator, or score
paths.  Selection is the final 64 rows of the frozen visible manifest, using
row position only; every selected row contains exactly ``opaque_id`` and
``question``.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROLE = "v24271_keyless_dev64_forward_contract"
PROTOCOL_ID = "v24271_v24270_candidate_vs_v24267_frozen_control_dev64_v1"
FORWARD_PROTOCOL = Path(
    "results/v24271_keyless_dev64_forward_contract_v1_20260802.json"
)
PREAUDIT = Path("results/v24271_keyless_dev64_preactivation_audit_v1_20260802.json")
ACTIVATION = Path("results/v24271_keyless_dev64_activation_v1_20260802.json")
EXECUTION_START = Path("results/v24271_keyless_dev64_execution_start_v1_20260802.json")
FORWARD_RESULT = Path("results/v24271_keyless_dev64_forward_result_v1_20260802.json")
OUTPUT_ROOT = Path("outputs/v24271_keyless_dev64_v1_20260802")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "candidate_runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "candidate_run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "candidate_prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"

RUNNER_MARKER = "scripts/run_v24271_keyless_dev64.py"
CHILD_MARKER = "scripts/run_v24270_budget_equivalent_task.py"
EXECUTOR_CONCURRENCY = 2
MODEL_SLOT_CAP = 2
SELECTED_COUNT = 64
MODEL_SLOT_POOL_ID = "v24263_score_first_global_model_slots_v1"
SOURCE_MANIFEST = Path("outputs/runtime_manifest_v1_repro/manifest.jsonl")

LIMITS = {
    "wall_seconds": 600,
    "model_calls": 3,
    "search_queries": 8,
    "fetch_targets": 16,
    "search_results_per_query": 3,
    "evidence_chars": 100000,
    "page_chars": 5000,
    "plan_output_tokens": 4000,
    "synthesis_output_tokens": 30000,
    "repair_output_tokens": 12000,
}
MODEL = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "name": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 180,
    "max_retries": 2,
}
SEARCH = {
    "provider": "azure-native-keyless-batched-budget-equivalent-task-union",
    "proxy_url": "http://127.0.0.1:9878/responses",
    "model": "gpt-5.6-sol",
    "batch_size": 8,
    "workers": 1,
    "context_size": "medium",
    "max_output_tokens": 7000,
    "timeout_seconds": 180,
    "max_retries": 2,
    "fetch_workers": 8,
    "fetch_timeout_seconds": 20,
    "server_auto_fetch_enabled": False,
}

OPAQUE = re.compile(r"task_[0-9a-f]{24}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _payload_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.42.71 forward path is noncanonical")
    path = root / raw
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise RuntimeError(f"V2.42.71 expected ordinary forward file: {relative}")
    return path


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.42.71 expected JSON object: {path}")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == _payload_sha256(unsigned)


def visible_manifest_rows(root: Path) -> list[dict[str, str]]:
    path = _ordinary(root.resolve(), SOURCE_MANIFEST)
    rows: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        if (
            not isinstance(raw, dict)
            or set(raw) != {"opaque_id", "question"}
            or not isinstance(raw.get("opaque_id"), str)
            or OPAQUE.fullmatch(raw["opaque_id"]) is None
            or not isinstance(raw.get("question"), str)
            or not raw["question"].strip()
        ):
            raise RuntimeError("V2.42.71 visible manifest schema drifted")
        rows.append({"opaque_id": raw["opaque_id"], "question": raw["question"]})
    if len(rows) < SELECTED_COUNT or len({row["opaque_id"] for row in rows}) != len(rows):
        raise RuntimeError("V2.42.71 visible manifest count or identity drifted")
    return rows


def selected_ids(protocol: dict[str, Any]) -> list[str]:
    """Read the frozen opaque allowlist without any category or split metadata."""

    contract = protocol.get("task_contract") or {}
    values = contract.get("selected_opaque_ids")
    if (
        not isinstance(values, list)
        or len(values) != SELECTED_COUNT
        or len(set(values)) != SELECTED_COUNT
        or any(not isinstance(value, str) or OPAQUE.fullmatch(value) is None for value in values)
        or _payload_sha256(values) != contract.get("selected_opaque_ids_sha256")
    ):
        raise RuntimeError("V2.42.71 frozen opaque selection drifted")
    return list(values)


def selected_tasks(root: Path, protocol: dict[str, Any]) -> list[dict[str, str]]:
    rows = visible_manifest_rows(root)
    identities = selected_ids(protocol)
    by_id = {row["opaque_id"]: row for row in rows}
    if any(value not in by_id for value in identities):
        raise RuntimeError("V2.42.71 frozen opaque selection is absent from manifest")
    tasks = [by_id[value] for value in identities]
    contract = protocol.get("task_contract") or {}
    manifest = contract.get("manifest") or {}
    if (
        _sha256(_ordinary(root.resolve(), SOURCE_MANIFEST)) != manifest.get("sha256")
        or contract.get("selection_rule")
        != "frozen opaque-ID allowlist; no category, question_type, or split metadata"
    ):
        raise RuntimeError("V2.42.71 visible-only selection drifted")
    return tasks


def validate_protocol(root: Path, path: Path = FORWARD_PROTOCOL) -> dict[str, Any]:
    """Validate only the frozen protocol, forward sources, and visible inputs.

    Historical control and evaluator-side resources are intentionally outside
    this function so the forward import closure cannot open them.
    """

    root = root.resolve()
    value = _read_object(_ordinary(root, path))
    if (
        value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("label_blind") is not True
        or not _sealed(value, "forward_contract_payload_sha256")
        or value.get("task_contract", {}).get("selected_count") != SELECTED_COUNT
        or value.get("task_contract", {}).get("runtime_boundary")
        != ["opaque_id", "question"]
        or value.get("task_contract", {}).get(
            "mapping_split_category_gold_evaluator_or_score_used_for_selection"
        )
        is not False
        or value.get("forward_contract", {}).get("executor_concurrency")
        != EXECUTOR_CONCURRENCY
        or value.get("forward_contract", {}).get("global_model_slot_cap")
        != MODEL_SLOT_CAP
        or value.get("source_policy", {}).get(
            "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read_by_forward"
        )
        is not False
        or value.get("authorization", {}).get("new_exact220_launch") is not False
        or value.get("authorization", {}).get("leaderboard_submission_or_sota_claim")
        is not False
        or set(value)
        != {
            "artifact_version",
            "role",
            "protocol_id",
            "created_at_unix",
            "label_blind",
            "task_contract",
            "forward_contract",
            "limits",
            "provider_contract",
            "model_slot_contract",
            "lease_contract",
            "execution",
            "source_policy",
            "authorization",
            "forward_surface",
            "forward_contract_payload_sha256",
        }
    ):
        raise RuntimeError("V2.42.71 forward protocol identity drifted")
    surface = value.get("forward_surface") or {}
    manifest = surface.get("dependency_manifest")
    if not isinstance(manifest, dict) or _payload_sha256(manifest) != surface.get(
        "dependency_manifest_sha256"
    ):
        raise RuntimeError("V2.42.71 forward manifest seal drifted")
    for relative, digest in manifest.items():
        if not isinstance(relative, str) or _sha256(_ordinary(root, relative)) != digest:
            raise RuntimeError(f"V2.42.71 frozen forward source drifted: {relative}")
    runner = surface.get("runner_entry") or {}
    if (
        runner.get("path") != "scripts/run_v24271_keyless_dev64.py"
        or _sha256(_ordinary(root, runner["path"])) != runner.get("sha256")
    ):
        raise RuntimeError("V2.42.71 frozen forward runner drifted")
    source = surface.get("contract_source") or {}
    if (
        source.get("path") != "src/deepwide_agent/v24271_forward_contract.py"
        or _sha256(_ordinary(root, source["path"])) != source.get("sha256")
    ):
        raise RuntimeError("V2.42.71 frozen forward contract source drifted")
    tasks = selected_tasks(root, value)
    if len(tasks) != SELECTED_COUNT:
        raise RuntimeError("V2.42.71 visible task count drifted")
    return value


__all__ = [
    "ACTIVATION",
    "CHILD_MARKER",
    "EXECUTION_START",
    "EXECUTOR_CONCURRENCY",
    "FORWARD_RESULT",
    "LIMITS",
    "MODEL",
    "MODEL_SLOT_CAP",
    "MODEL_SLOT_DIRECTORY",
    "MODEL_SLOT_POOL_ID",
    "FORWARD_PROTOCOL",
    "OUTPUT_ROOT",
    "PREAUDIT",
    "PREDICTION_FREEZE",
    "PROTOCOL_ID",
    "ROLE",
    "RUNTIME_PREDICTIONS",
    "RUNNER_MARKER",
    "RUN_SUMMARY",
    "SAFE_PROGRESS",
    "SEARCH",
    "SELECTED_COUNT",
    "SOURCE_MANIFEST",
    "TASK_ROOT",
    "selected_ids",
    "selected_tasks",
    "validate_protocol",
    "visible_manifest_rows",
]
