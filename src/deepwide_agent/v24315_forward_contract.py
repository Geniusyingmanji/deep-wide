"""Visible-only frozen contract for the V2.43.15 exact-220 forward pass."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROLE = "v24315_exact220_forward_contract"
PROTOCOL_ID = "v24315_v24314_deadline_aware_staged_reserve_exact220_v1"
FORWARD_CONTRACT = Path("results/v24315_exact220_forward_contract_v1_20260803.json")
PREAUDIT = Path("results/v24315_exact220_preactivation_audit_v1_20260803.json")
ACTIVATION = Path("results/v24315_exact220_activation_v1_20260803.json")
EXECUTION_START = Path("results/v24315_exact220_execution_start_v1_20260803.json")
FORWARD_RESULT = Path("results/v24315_exact220_forward_result_v1_20260803.json")
OUTPUT_ROOT = Path("outputs/v24315_exact220_v1_20260803")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24315_exact220_forward_v1"
LEASE_PURPOSE = "label_blind_v24314_candidate_deadline_aware_staged_reserve_exact220"

RUNNER_MARKER = "scripts/run_v24315_exact220.py"
CHILD_MARKER = "scripts/run_v24315_exact220_task.py"
CHILD_TERMINAL_NAME = "child_terminal_receipt.json"
PARENT_EXIT_NAME = "parent_exit_receipt.json"
FETCH_HELPER_MARKER = "scripts/run_v24287_fetch_helper.py"
SOURCE_MANIFEST = Path("outputs/runtime_manifest_v1_repro/manifest.jsonl")
ID_SOURCES = (
    ("test_s01", Path("configs/full220_v2403_r1_test_s01.ids"), 52),
    ("test_s02", Path("configs/full220_v2403_r1_test_s02.ids"), 52),
    ("test_s03", Path("configs/full220_v2403_r1_test_s03.ids"), 52),
    ("devval", Path("configs/full220_v2403_r1_devval_s04.ids"), 64),
)

EXECUTOR_CONCURRENCY = 8
MODEL_SLOT_CAP = 2
SELECTED_COUNT = 220
ARM = "candidate"
MODEL_SLOT_POOL_ID = "v24263_score_first_global_model_slots_v1"
CLEANUP_RESERVE_SECONDS = 5.0
MINIMUM_MODEL_ATTEMPT_SECONDS = 0.05
PARENT_DEADLINE_GRACE_SECONDS = 15.0
PROTECTED_WATCHERS = (
    (795336, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, "scripts/watch_v24218_exact220_executor.py"),
)
LIMITS = {
    "wall_seconds": 180,
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
RESERVE_POLICY = {
    "second_wave_observation_fetches": 2,
    "reserved_fetches": 2,
    "minimum_total_usable_pages": 4,
    "minimum_total_unique_hosts": 2,
    "content_chars_per_column": 1_200,
    "maximum_pre_reserved_retrieval_seconds": 60.0,
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
    "provider": "azure-native-keyless-v24314-candidate-deadline-aware-staged-reserve",
    "proxy_url": "http://127.0.0.1:9878/responses",
    "model": "gpt-5.6-sol",
    "batch_size": 8,
    "workers": 1,
    "context_size": "medium",
    "max_output_tokens": 7_000,
    "timeout_seconds": 180,
    "max_retries": 2,
    "fetch_workers": 8,
    "fetch_timeout_seconds": 20,
    "hard_fetch_deadline_seconds": 25,
    "server_auto_fetch_enabled": False,
}
OPAQUE = re.compile(r"task_[0-9a-f]{24}")


def protected_watcher_snapshot(
    proc_root: Path = Path("/proc"),
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for pid, marker in PROTECTED_WATCHERS:
        stat_path = proc_root / str(pid) / "stat"
        cmdline_path = proc_root / str(pid) / "cmdline"
        if not stat_path.is_file() or not cmdline_path.is_file():
            raise RuntimeError("V2.43.15 protected watcher is absent")
        raw = stat_path.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline_path.read_bytes().replace(b"\x00", b" ").decode(
            "utf-8", errors="replace"
        )
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.43.15 protected watcher identity drifted")
        output.append(
            {"pid": pid, "marker": marker, "start_ticks": int(suffix[19])}
        )
    return output


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.43.15 forward path is noncanonical")
    path = root / raw
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise RuntimeError(f"V2.43.15 expected ordinary forward file: {relative}")
    return path


def read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.43.15 expected ordinary JSON object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.43.15 expected JSON object: {path}")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def source_selected_shards(root: Path) -> list[tuple[str, list[str]]]:
    output: list[tuple[str, list[str]]] = []
    combined: list[str] = []
    for tag, relative, expected in ID_SOURCES:
        values = [
            line.strip()
            for line in _ordinary(root, relative).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if (
            len(values) != expected
            or len(set(values)) != expected
            or any(OPAQUE.fullmatch(value) is None for value in values)
        ):
            raise RuntimeError(f"V2.43.15 {tag} opaque-ID source drifted")
        output.append((tag, values))
        combined.extend(values)
    if len(combined) != SELECTED_COUNT or len(set(combined)) != SELECTED_COUNT:
        raise RuntimeError("V2.43.15 opaque-ID partition is not exact and disjoint")
    return output


def source_selected_ids(root: Path) -> list[str]:
    return [value for _, values in source_selected_shards(root) for value in values]


def selected_ids(contract: dict[str, Any]) -> list[str]:
    task = contract.get("task_contract") or {}
    values = task.get("selected_opaque_ids")
    if (
        not isinstance(values, list)
        or len(values) != SELECTED_COUNT
        or len(set(values)) != SELECTED_COUNT
        or any(not isinstance(value, str) or OPAQUE.fullmatch(value) is None for value in values)
        or payload_sha256(values) != task.get("selected_opaque_ids_sha256")
    ):
        raise RuntimeError("V2.43.15 frozen opaque-ID vector drifted")
    return list(values)


def _visible_manifest(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in _ordinary(root, SOURCE_MANIFEST).read_text(encoding="utf-8").splitlines():
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
            raise RuntimeError("V2.43.15 visible manifest schema drifted")
        rows.append({"opaque_id": raw["opaque_id"], "question": raw["question"]})
    if len({row["opaque_id"] for row in rows}) != len(rows):
        raise RuntimeError("V2.43.15 visible manifest has duplicate opaque IDs")
    return rows


def selected_tasks(root: Path, contract: dict[str, Any]) -> list[dict[str, str]]:
    ids = selected_ids(contract)
    task_contract = contract["task_contract"]
    if (
        payload_sha256(ids) != task_contract["selected_opaque_ids_sha256"]
        or sha256(_ordinary(root, SOURCE_MANIFEST)) != task_contract["manifest_sha256"]
    ):
        raise RuntimeError("V2.43.15 visible selection identity drifted")
    by_id = {row["opaque_id"]: row for row in _visible_manifest(root)}
    if any(value not in by_id for value in ids):
        raise RuntimeError("V2.43.15 selected visible task is absent")
    tasks = [by_id[value] for value in ids]
    if any(set(task) != {"opaque_id", "question"} for task in tasks):
        raise RuntimeError("V2.43.15 runtime boundary drifted")
    return tasks


def validate_forward_contract(
    root: Path, path: Path = FORWARD_CONTRACT
) -> dict[str, Any]:
    root = root.resolve()
    value = read_object(_ordinary(root, path))
    if (
        value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("label_blind") is not True
        or not _sealed(value, "forward_contract_payload_sha256")
        or value.get("task_contract", {}).get("runtime_boundary")
        != ["opaque_id", "question"]
        or value.get("task_contract", {}).get("selected_count") != SELECTED_COUNT
        or value.get("task_contract", {}).get(
            "mapping_split_category_gold_score_used_for_selection"
        )
        is not False
        or value.get("execution", {}).get("executor_concurrency")
        != EXECUTOR_CONCURRENCY
        or value.get("execution", {}).get("arm") != ARM
        or value.get("execution", {}).get("model_slot_cap") != MODEL_SLOT_CAP
        or value.get("execution", {}).get("child_terminal_receipt_name")
        != CHILD_TERMINAL_NAME
        or value.get("execution", {}).get("parent_exit_receipt_name")
        != PARENT_EXIT_NAME
        or value.get("execution", {}).get("protected_watchers")
        != protected_watcher_snapshot()
        or value.get("execution", {}).get("runner_marker") != RUNNER_MARKER
        or value.get("execution", {}).get("child_marker") != CHILD_MARKER
        or value.get("execution", {}).get("output_root") != str(OUTPUT_ROOT)
        or value.get("limits") != LIMITS
        or value.get("two_wave_policy") != TWO_WAVE_POLICY
        or value.get("reserve_policy") != RESERVE_POLICY
        or value.get("deadline_contract")
        != {
            "cleanup_reserve_seconds": CLEANUP_RESERVE_SECONDS,
            "minimum_model_attempt_seconds": MINIMUM_MODEL_ATTEMPT_SECONDS,
            "parent_deadline_grace_seconds": PARENT_DEADLINE_GRACE_SECONDS,
        }
        or value.get("model") != MODEL
        or value.get("search") != SEARCH
        or value.get("lease")
        != {
            "path": str(LEASE_PATH),
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
            "nonblocking_single_owner": True,
        }
        or value.get("authorization")
        != {"single_fresh_exact220_forward": True, "additional_rollout_or_rerun": False}
        or value.get("source_policy")
        != {
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "evaluator_surface_absent_from_forward_dependency_manifest": True,
            "all_220_predictions_frozen_before_evaluator_resources_open": True,
            "credential_value_persisted_hashed_or_emitted": False,
        }
        or value.get("forward_acceptance_gate")
        != {
            "required_terminal_predictions": SELECTED_COUNT,
            "required_parent_exit_receipts": SELECTED_COUNT,
            "required_valid_child_terminal_receipts": SELECTED_COUNT,
            "required_valid_model_slot_receipts": SELECTED_COUNT,
            "required_valid_transport_receipts": SELECTED_COUNT,
            "maximum_non_success_parent_exits": 0,
            "maximum_incomplete_effect_counts": 0,
            "maximum_fourth_model_effects": 0,
        }
    ):
        raise RuntimeError("V2.43.15 forward contract identity drifted")
    manifest = value.get("dependency_manifest")
    if (
        not isinstance(manifest, dict)
        or value.get("dependency_manifest_sha256") != payload_sha256(manifest)
    ):
        raise RuntimeError("V2.43.15 dependency manifest seal drifted")
    for relative, digest in manifest.items():
        if sha256(_ordinary(root, relative)) != digest:
            raise RuntimeError(f"V2.43.15 frozen forward dependency drifted: {relative}")
    ids = selected_ids(value)
    if payload_sha256(ids) != value["task_contract"]["selected_opaque_ids_sha256"]:
        raise RuntimeError("V2.43.15 exact-220 opaque-ID order drifted")
    if len(selected_tasks(root, value)) != SELECTED_COUNT:
        raise RuntimeError("V2.43.15 exact-220 visible task count drifted")
    return value


__all__ = [
    "ACTIVATION",
    "ARM",
    "CHILD_MARKER",
    "CHILD_TERMINAL_NAME",
    "CLEANUP_RESERVE_SECONDS",
    "EXECUTION_START",
    "EXECUTOR_CONCURRENCY",
    "FETCH_HELPER_MARKER",
    "FORWARD_CONTRACT",
    "FORWARD_RESULT",
    "ID_SOURCES",
    "LIMITS",
    "LEASE_OWNER",
    "LEASE_PATH",
    "LEASE_PURPOSE",
    "MODEL",
    "MODEL_SLOT_CAP",
    "MODEL_SLOT_DIRECTORY",
    "MODEL_SLOT_POOL_ID",
    "MINIMUM_MODEL_ATTEMPT_SECONDS",
    "OUTPUT_ROOT",
    "PARENT_DEADLINE_GRACE_SECONDS",
    "PARENT_EXIT_NAME",
    "PREDICTION_FREEZE",
    "PREAUDIT",
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
    "RESERVE_POLICY",
    "payload_sha256",
    "protected_watcher_snapshot",
    "read_object",
    "selected_ids",
    "source_selected_ids",
    "source_selected_shards",
    "selected_tasks",
    "sha256",
    "validate_forward_contract",
]
