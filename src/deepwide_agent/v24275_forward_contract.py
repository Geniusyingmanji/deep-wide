"""Strict forward-only contract for the V2.42.75 consumed-dev64 gate.

The forward process can open only this projection, its frozen source closure,
and the visible manifest whose rows are exactly ``opaque_id`` plus ``question``.
Historical control predictions, mapping, gold, evaluator code/data, and score
artifacts are deliberately absent from this module and projection.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROLE = "v24275_two_wave_dev64_forward_contract"
PROTOCOL_ID = "v24275_v24273_two_wave_vs_v24271_frozen_candidate_dev64_v1"
FORWARD_PROTOCOL = Path(
    "results/v24275_two_wave_dev64_forward_contract_v1_20260802.json"
)
PREAUDIT = Path(
    "results/v24275_two_wave_dev64_preactivation_audit_v1_20260802.json"
)
ACTIVATION = Path(
    "results/v24275_two_wave_dev64_activation_v1_20260802.json"
)
EXECUTION_START = Path(
    "results/v24275_two_wave_dev64_execution_start_v1_20260802.json"
)
FORWARD_RESULT = Path(
    "results/v24275_two_wave_dev64_forward_result_v1_20260802.json"
)
OUTPUT_ROOT = Path("outputs/v24275_two_wave_dev64_v1_20260802")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "candidate_runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "candidate_run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "candidate_prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"

RUNNER_MARKER = "scripts/run_v24275_two_wave_dev64.py"
CHILD_MARKER = "scripts/run_v24275_two_wave_task.py"
FETCH_HELPER_MARKER = "scripts/run_v24275_fetch_helper.py"
EXECUTOR_CONCURRENCY = 8
MODEL_SLOT_CAP = 8
SELECTED_COUNT = 64
MODEL_SLOT_POOL_ID = "v24263_score_first_global_model_slots_v1"
SOURCE_MANIFEST = Path("outputs/runtime_manifest_v1_repro/manifest.jsonl")

LIMITS = {
    "wall_seconds": 180,
    "model_calls": 3,
    "search_queries": 4,
    "fetch_targets": 10,
    "search_results_per_query": 3,
    "evidence_chars": 60000,
    "page_chars": 5000,
    "plan_output_tokens": 4000,
    "synthesis_output_tokens": 30000,
    "repair_output_tokens": 12000,
}
TWO_WAVE_POLICY = {
    "wave1_queries": 2,
    "wave1_fetches": 6,
    "wave2_queries": 2,
    "wave2_fetches": 4,
    "minimum_usable_pages": 3,
    "minimum_novel_pages": 3,
    "minimum_unique_hosts": 2,
    "content_chars_per_column": 1200,
    "maximum_wave1_seconds": 30.0,
    "latency_loss_per_second": 0.005,
    "information_gain_weight": 0.25,
    "minimum_net_value": 0.0,
    "beta_prior_alpha": 1.0,
    "beta_prior_beta": 1.0,
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
    "provider": "azure-native-keyless-two-wave-cached",
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
    "hard_fetch_deadline_seconds": 25,
    "fetch_helper_marker": FETCH_HELPER_MARKER,
    "server_auto_fetch_enabled": False,
}

OPAQUE = re.compile(r"task_[0-9a-f]{24}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.42.75 forward path is noncanonical")
    path = root / raw
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.42.75 expected ordinary forward file: {relative}")
    return path


def read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.42.75 expected ordinary JSON file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.42.75 expected JSON object: {path}")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


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
            raise RuntimeError("V2.42.75 visible manifest schema drifted")
        rows.append({"opaque_id": raw["opaque_id"], "question": raw["question"]})
    if (
        len(rows) < SELECTED_COUNT
        or len({row["opaque_id"] for row in rows}) != len(rows)
    ):
        raise RuntimeError("V2.42.75 visible manifest identity drifted")
    return rows


def selected_ids(protocol: dict[str, Any]) -> list[str]:
    contract = protocol.get("task_contract") or {}
    values = contract.get("selected_opaque_ids")
    if (
        not isinstance(values, list)
        or len(values) != SELECTED_COUNT
        or len(set(values)) != SELECTED_COUNT
        or any(
            not isinstance(value, str) or OPAQUE.fullmatch(value) is None
            for value in values
        )
        or payload_sha256(values) != contract.get("selected_opaque_ids_sha256")
    ):
        raise RuntimeError("V2.42.75 frozen opaque selection drifted")
    return list(values)


def selected_tasks(root: Path, protocol: dict[str, Any]) -> list[dict[str, str]]:
    rows = visible_manifest_rows(root)
    identities = selected_ids(protocol)
    by_id = {row["opaque_id"]: row for row in rows}
    if any(identity not in by_id for identity in identities):
        raise RuntimeError("V2.42.75 selected task is absent from visible manifest")
    tasks = [by_id[identity] for identity in identities]
    task_contract = protocol["task_contract"]
    if (
        sha256(_ordinary(root.resolve(), SOURCE_MANIFEST))
        != task_contract["manifest"]["sha256"]
        or task_contract.get("selection_rule")
        != "frozen opaque-ID allowlist; no category, question_type, or split metadata"
    ):
        raise RuntimeError("V2.42.75 visible-only selection drifted")
    return tasks


def validate_protocol(
    root: Path, path: Path = FORWARD_PROTOCOL
) -> dict[str, Any]:
    root = root.resolve()
    value = read_object(_ordinary(root, path))
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
        or value.get("limits") != LIMITS
        or value.get("two_wave_policy") != TWO_WAVE_POLICY
        or value.get("provider_contract", {}).get("model") != MODEL
        or value.get("provider_contract", {}).get("search") != SEARCH
        or value.get("authorization", {}).get("new_exact220_launch") is not False
        or value.get("authorization", {}).get("leaderboard_submission_or_sota_claim")
        is not False
        or value.get("source_policy", {}).get(
            "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read_by_forward"
        )
        is not False
    ):
        raise RuntimeError("V2.42.75 forward contract identity drifted")
    manifest = value.get("forward_surface", {}).get("dependency_manifest")
    if (
        not isinstance(manifest, dict)
        or payload_sha256(manifest)
        != value["forward_surface"].get("dependency_manifest_sha256")
    ):
        raise RuntimeError("V2.42.75 forward dependency manifest drifted")
    for relative, expected in manifest.items():
        if sha256(_ordinary(root, relative)) != expected:
            raise RuntimeError(f"V2.42.75 forward dependency drifted: {relative}")
    runner = value["forward_surface"].get("runner_entry") or {}
    contract = value["forward_surface"].get("contract_source") or {}
    if (
        runner.get("path") != RUNNER_MARKER
        or sha256(_ordinary(root, RUNNER_MARKER)) != runner.get("sha256")
        or contract.get("path")
        != "src/deepwide_agent/v24275_forward_contract.py"
        or sha256(_ordinary(root, contract["path"])) != contract.get("sha256")
        or value["execution"].get("runner_marker") != RUNNER_MARKER
        or value["execution"].get("child_marker") != CHILD_MARKER
        or value["execution"].get("fetch_helper_marker") != FETCH_HELPER_MARKER
        or value["execution"].get("output_root") != str(OUTPUT_ROOT)
    ):
        raise RuntimeError("V2.42.75 forward entry binding drifted")
    selected_ids(value)
    if sha256(_ordinary(root, SOURCE_MANIFEST)) != value["task_contract"][
        "manifest"
    ]["sha256"]:
        raise RuntimeError("V2.42.75 visible manifest hash drifted")
    return value


__all__ = [
    "ACTIVATION",
    "CHILD_MARKER",
    "EXECUTION_START",
    "EXECUTOR_CONCURRENCY",
    "FORWARD_PROTOCOL",
    "FORWARD_RESULT",
    "FETCH_HELPER_MARKER",
    "LIMITS",
    "MODEL",
    "MODEL_SLOT_CAP",
    "MODEL_SLOT_DIRECTORY",
    "MODEL_SLOT_POOL_ID",
    "OUTPUT_ROOT",
    "PREAUDIT",
    "PREDICTION_FREEZE",
    "PROTOCOL_ID",
    "RUNTIME_PREDICTIONS",
    "RUNNER_MARKER",
    "RUN_SUMMARY",
    "SAFE_PROGRESS",
    "SEARCH",
    "SELECTED_COUNT",
    "SOURCE_MANIFEST",
    "TASK_ROOT",
    "TWO_WAVE_POLICY",
    "payload_sha256",
    "read_object",
    "selected_ids",
    "selected_tasks",
    "sha256",
    "validate_protocol",
]
