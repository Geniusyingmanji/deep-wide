"""Frozen paths and validators for the V2.47.11 sparse full-220 forward.

This module contains no network, benchmark evaluator, mapping, gold, score,
or reward capability.  Forward code receives only ``{opaque_id, question}``
plus a previously frozen control prediction for the same opaque identity.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


DATE = "20260806"
PROTOCOL_ID = "v24711_sparse_worldbank_control_reuse_full220_v1"
ROLE = "v24711_sparse_full220_preregistration"
SELECTED_COUNT = 220
EXPECTED_ROUTE_ELIGIBLE = 1
EXPECTED_APPLIED_TASKS = 1
EXPECTED_UNCHANGED_TASKS = 219
EXPECTED_TARGET_VALUES = 212
DOWNLOAD_WORKERS = 4
DOWNLOAD_TIMEOUT_SECONDS = 30
DOWNLOAD_CAP = 4

PROTOCOL = Path(f"results/v24711_sparse_full220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24711_sparse_full220_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24711_sparse_full220_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24711_sparse_full220_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24711_sparse_full220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24711_sparse_full220_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24711_sparse_full220_v1_{DATE}")
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
DOWNLOAD_RECEIPT = OUTPUT_ROOT / "bulk_download_receipt.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"

VISIBLE_MANIFEST = Path("outputs/runtime_manifest_v1_repro/manifest.jsonl")
CONTROL_PREDICTIONS = Path(
    "outputs/v24267_exact220_v1_20260802/runtime_predictions.jsonl"
)
CONTROL_FREEZE = Path("outputs/v24267_exact220_v1_20260802/prediction_freeze.json")
CONTROL_RUN_SUMMARY = Path("outputs/v24267_exact220_v1_20260802/run_summary.json")
BUILD_AUDIT = Path(f"results/v24710_sparse_worldbank_build_audit_v1_{DATE}.json")
DESIGN = Path(f"results/v24708_sparse_full220_exploratory_design_v1_{DATE}.json")
INCIDENT = Path(
    f"results/v24707_preimplementation_probe_contamination_audit_v1_{DATE}.json"
)
AUTHORITY_SCOPE = Path(
    f"results/v24706_full220_visible_authority_scope_audit_v1_{DATE}.json"
)

RUNNER_MARKER = "scripts/run_v24711_sparse_full220.py"
CONTROL_MARKER = "scripts/control_v24711_sparse_full220.py"
FORWARD_AUDIT_MARKER = "scripts/audit_v24711_sparse_full220_forward.py"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24711_sparse_full220_forward_v1"
LEASE_PURPOSE = "label_blind_sparse_worldbank_control_reuse_full220"
PROTECTED_WATCHERS = (
    (795336, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, "scripts/watch_v24218_exact220_executor.py"),
)
PREAUDIT_AUTHORIZATION = {
    "activation_publication": True,
    "forward_launch": False,
    "evaluator": False,
    "leaderboard_or_sota": False,
}
ACTIVATION_AUTHORIZATION = {
    "execution_start_publication": True,
    "forward_launch": False,
    "evaluator": False,
    "leaderboard_or_sota": False,
}
START_AUTHORIZATION = {
    "one_sparse_full220_forward": True,
    "evaluator": False,
    "leaderboard_or_sota": False,
}


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.47.11 expected ordinary JSON object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.11 expected JSON object")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.47.11 expected ordinary JSONL: {path}")
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.47.11 expected JSONL objects")
    return rows


def sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def protected_watcher_snapshot(
    proc_root: Path = Path("/proc"),
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for pid, marker in PROTECTED_WATCHERS:
        stat = proc_root / str(pid) / "stat"
        command = proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not command.is_file():
            raise RuntimeError("V2.47.11 protected watcher is absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        cmdline = command.read_bytes().replace(b"\x00", b" ").decode(
            errors="replace"
        )
        if len(suffix) <= 19 or marker not in cmdline:
            raise RuntimeError("V2.47.11 protected watcher identity drifted")
        output.append(
            {"pid": pid, "marker": marker, "start_ticks": int(suffix[19])}
        )
    return output


def validate_control_freeze(root: Path) -> dict[str, Any]:
    freeze = read_object(root / CONTROL_FREEZE)
    summary = read_object(root / CONTROL_RUN_SUMMARY)
    if (
        freeze.get("role") != "v24267_exact220_prediction_freeze"
        or freeze.get("selected") != SELECTED_COUNT
        or freeze.get("terminal") != SELECTED_COUNT
        or freeze.get("runtime_predictions_sha256")
        != sha256(root / CONTROL_PREDICTIONS)
        or freeze.get("run_summary_sha256") != sha256(root / CONTROL_RUN_SUMMARY)
        or freeze.get("mapping_query_answer_gold_or_evaluator_opened_or_hashed")
        is not False
        or freeze.get(
            "exact_terminal_before_mapping_query_answer_gold_or_evaluator_open"
        )
        is not True
        or not sealed(freeze, "freeze_payload_sha256")
        or summary.get("role") != "v24267_exact220_run_summary"
        or summary.get("selected") != SELECTED_COUNT
        or summary.get("completed") != SELECTED_COUNT
        or summary.get("failed") != 0
        or summary.get("official_evaluator_called") is not False
        or summary.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
    ):
        raise RuntimeError("V2.47.11 control prediction freeze drifted")
    return freeze


def validate_control_rows(root: Path) -> list[dict[str, Any]]:
    validate_control_freeze(root)
    rows = read_jsonl(root / CONTROL_PREDICTIONS)
    if (
        len(rows) != SELECTED_COUNT
        or len({row.get("opaque_id") for row in rows}) != SELECTED_COUNT
        or any(
            not isinstance(row.get("opaque_id"), str)
            or row.get("status") != "completed"
            or not isinstance(row.get("prediction"), str)
            or not row["prediction"].strip()
            or hashlib.sha256(row["prediction"].encode("utf-8")).hexdigest()
            != row.get("prediction_sha256")
            or row.get("label_blind") is not True
            or row.get(
                "mapping_gold_category_question_type_split_evaluator_score_read"
            )
            is not False
            for row in rows
        )
    ):
        raise RuntimeError("V2.47.11 control prediction rows drifted")
    return rows


def validate_visible_rows(root: Path) -> list[dict[str, str]]:
    rows = read_jsonl(root / VISIBLE_MANIFEST)
    if (
        len(rows) != SELECTED_COUNT
        or len({row.get("opaque_id") for row in rows}) != SELECTED_COUNT
        or any(
            set(row) != {"opaque_id", "question"}
            or not isinstance(row.get("opaque_id"), str)
            or not isinstance(row.get("question"), str)
            or not row["question"].strip()
            for row in rows
        )
    ):
        raise RuntimeError("V2.47.11 visible manifest drifted")
    return [{"opaque_id": row["opaque_id"], "question": row["question"]} for row in rows]


def validate_protocol(root: Path, path: Path = PROTOCOL) -> dict[str, Any]:
    value = read_object(root / path)
    manifest = value.get("dependency_manifest")
    task = value.get("task_contract", {})
    execution = value.get("execution", {})
    if (
        value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or not sealed(value, "protocol_payload_sha256")
        or not isinstance(manifest, dict)
        or value.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or any(sha256(root / relative) != digest for relative, digest in manifest.items())
        or task.get("runtime_boundary") != ["opaque_id", "question"]
        or task.get("selected_count") != SELECTED_COUNT
        or task.get("visible_manifest_sha256") != sha256(root / VISIBLE_MANIFEST)
        or task.get("control_predictions_sha256")
        != sha256(root / CONTROL_PREDICTIONS)
        or task.get("control_freeze_sha256") != sha256(root / CONTROL_FREEZE)
        or execution.get("download_cap") != DOWNLOAD_CAP
        or execution.get("download_workers") != DOWNLOAD_WORKERS
        or execution.get("download_timeout_seconds") != DOWNLOAD_TIMEOUT_SECONDS
        or execution.get("protected_watchers") != protected_watcher_snapshot()
        or value.get("authorization")
        != {
            "preactivation_audit_generation": True,
            "activation_or_forward_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
    ):
        raise RuntimeError("V2.47.11 protocol drifted")
    return value


def validate_stage(
    root: Path,
    path: Path,
    *,
    role: str,
    seal_field: str,
    authorization: Mapping[str, bool],
) -> dict[str, Any]:
    value = read_object(root / path)
    if (
        value.get("artifact_version") != 1
        or value.get("role") != role
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("protocol_sha256") != sha256(root / PROTOCOL)
        or value.get("authorization") != dict(authorization)
        or not sealed(value, seal_field)
    ):
        raise RuntimeError(f"V2.47.11 {role} drifted")
    return value


__all__ = [
    "ACTIVATION",
    "ACTIVATION_AUTHORIZATION",
    "AUTHORITY_SCOPE",
    "BUILD_AUDIT",
    "CONTROL_FREEZE",
    "CONTROL_PREDICTIONS",
    "CONTROL_RUN_SUMMARY",
    "DATE",
    "DESIGN",
    "DOWNLOAD_CAP",
    "DOWNLOAD_RECEIPT",
    "DOWNLOAD_TIMEOUT_SECONDS",
    "DOWNLOAD_WORKERS",
    "EXECUTION_START",
    "EXPECTED_APPLIED_TASKS",
    "EXPECTED_ROUTE_ELIGIBLE",
    "EXPECTED_TARGET_VALUES",
    "EXPECTED_UNCHANGED_TASKS",
    "FORWARD_AUDIT",
    "FORWARD_AUDIT_MARKER",
    "FORWARD_RESULT",
    "INCIDENT",
    "LEASE_OWNER",
    "LEASE_PATH",
    "LEASE_PURPOSE",
    "OUTPUT_ROOT",
    "PREAUDIT",
    "PREAUDIT_AUTHORIZATION",
    "PREDICTION_FREEZE",
    "PROTOCOL",
    "PROTOCOL_ID",
    "ROLE",
    "RUNNER_MARKER",
    "RUN_SUMMARY",
    "RUNTIME_PREDICTIONS",
    "SELECTED_COUNT",
    "START_AUTHORIZATION",
    "VISIBLE_MANIFEST",
    "payload_sha256",
    "protected_watcher_snapshot",
    "read_jsonl",
    "read_object",
    "sealed",
    "sha256",
    "validate_control_freeze",
    "validate_control_rows",
    "validate_protocol",
    "validate_stage",
    "validate_visible_rows",
]
