"""Frozen visible-only contract constants for V2.43.11 paired dev64."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROLE = "v24311_paired_dev64_forward_contract"
PROTOCOL_ID = "v24311_fresh_common_recovery_6_4_vs_6_2_2_lowcap_observed_dev64_v1"
DATE = "20260803"
FORWARD_CONTRACT = Path(f"results/v24311_paired_dev64_forward_contract_v1_{DATE}.json")
FULL_PROTOCOL = Path(f"results/v24311_paired_dev64_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24311_paired_dev64_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24311_paired_dev64_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24311_paired_dev64_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24311_paired_dev64_forward_result_v1_{DATE}.json")
FINAL_RESULT = Path(f"results/v24311_paired_dev64_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24311_paired_dev64_postresult_audit_v1_{DATE}.json")
INTEGRATION_PARENT_DECISION = Path(
    "results/v24309_runner_exit_integration_decision_v1_20260803.json"
)
INTEGRATION_PARENT_POSTAUDIT = Path(
    "results/v24309_runner_exit_integration_postresult_audit_v1_20260803.json"
)
PREDECESSOR_FORWARD_RESULT = Path(
    "results/v24306_paired_dev64_forward_result_v1_20260803.json"
)
EVALUATOR_IDENTITY_PARENT = Path(
    "results/v24306_paired_dev64_preregistration_v1_20260803.json"
)
PREDECESSOR_FORWARD_WALL_SECONDS = 1660.434161
OUTPUT_ROOT = Path(f"outputs/v24311_paired_dev64_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
ARMS = ("baseline", "candidate")
RUNTIME_PREDICTIONS = {
    arm: OUTPUT_ROOT / f"{arm}_runtime_predictions.jsonl" for arm in ARMS
}
RUN_SUMMARY = {arm: OUTPUT_ROOT / f"{arm}_run_summary.json" for arm in ARMS}
PREDICTION_FREEZE = {
    arm: OUTPUT_ROOT / f"{arm}_prediction_freeze.json" for arm in ARMS
}
EVALUATOR_ROOT = OUTPUT_ROOT / "fresh_both_arm_evaluator"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24311_paired_dev64_forward_v1"
LEASE_PURPOSE = "label_blind_common_recovery_lowcap_observed_6_4_vs_6_2_2_dev64"
RUNNER_MARKER = "scripts/run_v24311_paired_dev64.py"
CHILD_MARKER = "scripts/run_v24311_paired_dev64_task.py"
CHILD_TERMINAL_NAME = "child_terminal_receipt.json"
PARENT_EXIT_NAME = "parent_exit_receipt.json"
FETCH_HELPER_MARKER = "scripts/run_v24287_fetch_helper.py"
SOURCE_MANIFEST = Path("outputs/runtime_manifest_v1_repro/manifest.jsonl")
ID_SOURCE = Path("configs/full220_v2403_r1_devval_s04.ids")
SELECTED_COUNT = 64
TOTAL_TASK_COUNT = SELECTED_COUNT * len(ARMS)
EXECUTOR_CONCURRENCY_PER_ARM = 4
TOTAL_EXECUTOR_CONCURRENCY = 8
MODEL_SLOT_CAP = 2
MODEL_SLOT_POOL_ID = "v24263_score_first_global_model_slots_v1"
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
    "provider": "azure-native-keyless-paired-staged-reserve",
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
            raise RuntimeError("V2.43.11 protected watcher is absent")
        raw = stat_path.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline_path.read_bytes().replace(b"\x00", b" ").decode(
            "utf-8", errors="replace"
        )
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.43.11 protected watcher identity drifted")
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
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.43.11 path is noncanonical")
    path = root / raw
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.43.11 expected ordinary file: {relative}")
    return path


def read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.43.11 expected ordinary JSON object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.43.11 expected JSON object: {path}")
    return value


def selected_source_ids(root: Path) -> list[str]:
    values = [
        line.strip()
        for line in _ordinary(root, ID_SOURCE).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if (
        len(values) != SELECTED_COUNT
        or len(set(values)) != SELECTED_COUNT
        or any(OPAQUE.fullmatch(value) is None for value in values)
    ):
        raise RuntimeError("V2.43.11 dev64 opaque-ID source drifted")
    return values


def selected_ids(contract: dict[str, Any]) -> list[str]:
    task = contract.get("task_contract") or {}
    values = task.get("selected_opaque_ids")
    if (
        not isinstance(values, list)
        or len(values) != SELECTED_COUNT
        or len(set(values)) != SELECTED_COUNT
        or any(
            not isinstance(value, str) or OPAQUE.fullmatch(value) is None
            for value in values
        )
        or payload_sha256(values) != task.get("selected_opaque_ids_sha256")
    ):
        raise RuntimeError("V2.43.11 frozen opaque-ID vector drifted")
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
            raise RuntimeError("V2.43.11 visible manifest schema drifted")
        rows.append({"opaque_id": raw["opaque_id"], "question": raw["question"]})
    if len({row["opaque_id"] for row in rows}) != len(rows):
        raise RuntimeError("V2.43.11 visible manifest has duplicate opaque IDs")
    return rows


def selected_tasks(root: Path, contract: dict[str, Any]) -> list[dict[str, str]]:
    ids = selected_ids(contract)
    by_id = {row["opaque_id"]: row for row in _visible_manifest(root)}
    if any(value not in by_id for value in ids):
        raise RuntimeError("V2.43.11 selected visible task is absent")
    tasks = [by_id[value] for value in ids]
    if any(set(task) != {"opaque_id", "question"} for task in tasks):
        raise RuntimeError("V2.43.11 runtime boundary drifted")
    return tasks


def validate_forward_contract(
    root: Path, path: Path = FORWARD_CONTRACT
) -> dict[str, Any]:
    root = root.resolve()
    value = read_object(_ordinary(root, path))
    unsigned = dict(value)
    seal = unsigned.pop("forward_contract_payload_sha256", None)
    if (
        value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("label_blind") is not True
        or seal != payload_sha256(unsigned)
        or value.get("task_contract", {}).get("runtime_boundary")
        != ["opaque_id", "question"]
        or value.get("task_contract", {}).get("selected_count") != SELECTED_COUNT
        or value.get("task_contract", {}).get(
            "mapping_split_category_gold_score_used_for_selection"
        )
        is not False
        or value.get("execution", {}).get("arms") != list(ARMS)
        or value.get("execution", {}).get("executor_concurrency_per_arm")
        != EXECUTOR_CONCURRENCY_PER_ARM
        or value.get("execution", {}).get("total_executor_concurrency")
        != TOTAL_EXECUTOR_CONCURRENCY
        or value.get("execution", {}).get("model_slot_cap") != MODEL_SLOT_CAP
        or value.get("execution", {}).get("child_terminal_receipt_name")
        != CHILD_TERMINAL_NAME
        or value.get("execution", {}).get("parent_exit_receipt_name")
        != PARENT_EXIT_NAME
        or value.get("execution", {}).get("interleaved_fresh_pairing") is not True
        or value.get("execution", {}).get("protected_watchers")
        != protected_watcher_snapshot()
        or value.get("limits") != LIMITS
        or value.get("two_wave_policy") != TWO_WAVE_POLICY
        or value.get("reserve_policy") != RESERVE_POLICY
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
        != {
            "single_fresh_paired_dev64_forward": True,
            "additional_rollout_resume_skip_or_rerun": False,
            "exact220_launch": False,
        }
    ):
        raise RuntimeError("V2.43.11 forward contract identity drifted")
    manifest = value.get("dependency_manifest")
    if (
        not isinstance(manifest, dict)
        or value.get("dependency_manifest_sha256") != payload_sha256(manifest)
    ):
        raise RuntimeError("V2.43.11 dependency manifest seal drifted")
    for relative, digest in manifest.items():
        if sha256(_ordinary(root, relative)) != digest:
            raise RuntimeError(f"V2.43.11 frozen dependency drifted: {relative}")
    if selected_ids(value) != selected_source_ids(root):
        raise RuntimeError("V2.43.11 dev64 selection drifted")
    if len(selected_tasks(root, value)) != SELECTED_COUNT:
        raise RuntimeError("V2.43.11 visible task count drifted")
    return value


__all__ = [name for name in globals() if name.isupper()] + [
    "payload_sha256",
    "protected_watcher_snapshot",
    "read_object",
    "selected_ids",
    "selected_source_ids",
    "selected_tasks",
    "sha256",
    "validate_forward_contract",
]
