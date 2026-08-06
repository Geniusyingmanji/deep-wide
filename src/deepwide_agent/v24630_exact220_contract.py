"""Frozen visible-only contract for the V2.46.30 DeepWideBench exact-220."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROLE = "v24630_exact220_forward_contract"
PROTOCOL_ID = "v24630_bounded_same_response_title_backfill_exact220_v1"
FORWARD_CONTRACT = Path("results/v24630_exact220_forward_contract_v1_20260806.json")
PREAUDIT = Path("results/v24630_exact220_preactivation_audit_v1_20260806.json")
ACTIVATION = Path("results/v24630_exact220_activation_v1_20260806.json")
EXECUTION_START = Path("results/v24630_exact220_execution_start_v1_20260806.json")
FORWARD_RESULT = Path("results/v24630_exact220_forward_result_v1_20260806.json")
OUTPUT_ROOT = Path("outputs/v24630_exact220_v1_20260806")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24630_exact220_forward_v1"
LEASE_PURPOSE = "label_blind_bounded_same_response_title_backfill_exact220"

RUNNER_MARKER = "scripts/run_v24630_exact220.py"
CHILD_MARKER = "scripts/run_v24630_exact220_task.py"
CHILD_TERMINAL_NAME = "child_terminal_receipt.json"
PARENT_EXIT_NAME = "parent_exit_receipt.json"
RECEIPT_NAME = "model_slot_receipt.json"
TRANSPORT_NAME = "transport_health.json"
SOURCE_MANIFEST = Path("outputs/runtime_manifest_v1_repro/manifest.jsonl")
ID_SOURCES = (
    ("test_s01", Path("configs/full220_v2403_r1_test_s01.ids"), 52),
    ("test_s02", Path("configs/full220_v2403_r1_test_s02.ids"), 52),
    ("test_s03", Path("configs/full220_v2403_r1_test_s03.ids"), 52),
    ("devval", Path("configs/full220_v2403_r1_devval_s04.ids"), 64),
)

SELECTED_COUNT = 220
ARM = "baseline"
EXECUTOR_CONCURRENCY = 32
MODEL_SLOT_CAP = 8
MODEL_SLOT_POOL_ID = "v24263_score_first_global_model_slots_v1"
CLEANUP_RESERVE_SECONDS = 5.0
MINIMUM_MODEL_ATTEMPT_SECONDS = 0.05
PARENT_DEADLINE_GRACE_SECONDS = 15.0
PROTECTED_WATCHERS = (
    (795336, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, "scripts/watch_v24218_exact220_executor.py"),
)
LIMITS = {
    "wall_seconds": 150,
    "model_calls": 3,
    "search_queries": 4,
    "fetch_targets": 10,
    "search_results_per_query": 3,
    "evidence_chars": 60_000,
    "page_chars": 5_000,
    "plan_output_tokens": 4_000,
    "synthesis_output_tokens": 30_000,
    "repair_output_tokens": 12_000,
}
TWO_WAVE_POLICY = {
    "wave1_queries": 2,
    "wave1_fetches": 6,
    "wave2_queries": 2,
    "wave2_fetches": 4,
    "minimum_usable_pages": 3,
    "minimum_novel_pages": 3,
    "minimum_unique_hosts": 2,
    "content_chars_per_column": 1_200,
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
    "timeout_seconds": 65,
    "max_retries": 2,
}
SEARCH = {
    "provider": "azure-native-keyless-bounded-same-response-title-backfill",
    "proxy_url": "http://127.0.0.1:9878/responses",
    "model": "gpt-5.6-sol",
    "batch_size": 8,
    "workers": 1,
    "context_size": "medium",
    "max_output_tokens": 7_000,
    "timeout_seconds": 65,
    "max_retries": 2,
    "fetch_workers": 8,
    "fetch_timeout_seconds": 20,
    "hard_fetch_deadline_seconds": 25,
    "server_auto_fetch_enabled": False,
}
OPAQUE = re.compile(r"task_[0-9a-f]{24}")


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.46.30 expected ordinary JSON object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.30 expected JSON object")
    return value


def protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for pid, marker in PROTECTED_WATCHERS:
        stat = proc_root / str(pid) / "stat"
        cmdline = proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.46.30 protected watcher is absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\x00", b" ").decode(errors="replace")
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.46.30 protected watcher identity drifted")
        output.append({"pid": pid, "marker": marker, "start_ticks": int(suffix[19])})
    return output


def source_selected_ids(root: Path) -> list[str]:
    values: list[str] = []
    for tag, relative, expected in ID_SOURCES:
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"V2.46.30 {tag} ID source is absent")
        current = [line.strip() for line in path.read_text().splitlines() if line.strip()]
        if (
            len(current) != expected
            or len(set(current)) != expected
            or any(OPAQUE.fullmatch(item) is None for item in current)
        ):
            raise RuntimeError(f"V2.46.30 {tag} opaque IDs drifted")
        values.extend(current)
    if len(values) != SELECTED_COUNT or len(set(values)) != SELECTED_COUNT:
        raise RuntimeError("V2.46.30 selected ID partition is not exact-220")
    return values


def selected_ids(contract: dict[str, Any]) -> list[str]:
    values = contract.get("task_contract", {}).get("selected_opaque_ids")
    if (
        not isinstance(values, list)
        or len(values) != SELECTED_COUNT
        or len(set(values)) != SELECTED_COUNT
        or any(not isinstance(item, str) or OPAQUE.fullmatch(item) is None for item in values)
        or payload_sha256(values)
        != contract.get("task_contract", {}).get("selected_opaque_ids_sha256")
    ):
        raise RuntimeError("V2.46.30 frozen ID vector drifted")
    return list(values)


def selected_tasks(root: Path, contract: dict[str, Any]) -> list[dict[str, str]]:
    path = root / SOURCE_MANIFEST
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.46.30 visible manifest is absent")
    rows: dict[str, dict[str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = json.loads(line)
        if (
            not isinstance(raw, dict)
            or set(raw) != {"opaque_id", "question"}
            or OPAQUE.fullmatch(str(raw.get("opaque_id", ""))) is None
            or not isinstance(raw.get("question"), str)
            or not raw["question"].strip()
            or raw["opaque_id"] in rows
        ):
            raise RuntimeError("V2.46.30 visible manifest schema drifted")
        rows[raw["opaque_id"]] = {
            "opaque_id": raw["opaque_id"],
            "question": raw["question"],
        }
    ids = selected_ids(contract)
    if any(item not in rows for item in ids):
        raise RuntimeError("V2.46.30 selected visible task is absent")
    tasks = [rows[item] for item in ids]
    if any(set(task) != {"opaque_id", "question"} for task in tasks):
        raise RuntimeError("V2.46.30 runtime boundary drifted")
    return tasks


def validate_forward_contract(root: Path, path: Path = FORWARD_CONTRACT) -> dict[str, Any]:
    value = read_object(root / path)
    unsigned = dict(value)
    seal = unsigned.pop("forward_contract_payload_sha256", None)
    if (
        value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("label_blind") is not True
        or seal != payload_sha256(unsigned)
        or value.get("task_contract", {}).get("runtime_boundary") != ["opaque_id", "question"]
        or value.get("task_contract", {}).get("selected_count") != SELECTED_COUNT
        or value.get("task_contract", {}).get("mapping_split_category_gold_score_used_for_selection")
        is not False
        or selected_ids(value) != source_selected_ids(root)
        or value.get("execution", {}).get("arm") != ARM
        or value.get("execution", {}).get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or value.get("execution", {}).get("model_slot_cap") != MODEL_SLOT_CAP
        or value.get("execution", {}).get("protected_watchers") != protected_watcher_snapshot()
        or value.get("limits") != LIMITS
        or value.get("two_wave_policy") != TWO_WAVE_POLICY
        or value.get("model") != MODEL
        or value.get("search") != SEARCH
        or value.get("authorization")
        != {"single_fresh_exact220_forward": True, "resume_retry_skip_or_rerun": False}
    ):
        raise RuntimeError("V2.46.30 forward contract identity drifted")
    manifest = value.get("dependency_manifest")
    if not isinstance(manifest, dict) or value.get("dependency_manifest_sha256") != payload_sha256(manifest):
        raise RuntimeError("V2.46.30 dependency manifest drifted")
    for relative, digest in manifest.items():
        candidate = root / relative
        if candidate.is_symlink() or not candidate.is_file() or sha256(candidate) != digest:
            raise RuntimeError(f"V2.46.30 frozen dependency drifted: {relative}")
    if sha256(root / SOURCE_MANIFEST) != value["task_contract"]["manifest_sha256"]:
        raise RuntimeError("V2.46.30 visible manifest hash drifted")
    if len(selected_tasks(root, value)) != SELECTED_COUNT:
        raise RuntimeError("V2.46.30 task count drifted")
    return value


__all__ = [name for name in globals() if name.isupper()] + [
    "payload_sha256",
    "protected_watcher_snapshot",
    "read_object",
    "selected_ids",
    "selected_tasks",
    "sha256",
    "source_selected_ids",
    "validate_forward_contract",
]
