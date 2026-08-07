"""Visible-only execution contract for the V2.48.09 shared-prefix smoke."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .v24686_worldbank_target_value_runtime import _visible_contract
from .v24804_shared_prefix_budget_ladder import AdaptivePolicy


DATE = "20260807"
PROTOCOL_ID = "v24809_worldbank_shared_prefix_budget_ladder_smoke_v1"
PROTOCOL = Path(f"results/v24809_worldbank_budget_ladder_smoke_preregistration_v1_{DATE}.json")
BUILD_AUDIT = Path(f"results/v24809_worldbank_budget_ladder_smoke_build_audit_v2_{DATE}.json")
PREAUDIT = Path(f"results/v24809_worldbank_budget_ladder_smoke_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24809_worldbank_budget_ladder_smoke_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24809_worldbank_budget_ladder_smoke_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24809_worldbank_budget_ladder_smoke_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24809_worldbank_budget_ladder_smoke_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24809_worldbank_budget_ladder_smoke_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
PREDICTIONS = OUTPUT_ROOT / "frozen_predictions.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24809_worldbank_budget_ladder_smoke_forward_v1"
LEASE_PURPOSE = "benchmark_external_shared_prefix_budget_ladder_smoke"
RUNNER_MARKER = "scripts/run_v24809_worldbank_budget_ladder_smoke_forward.py"
CHILD_MARKER = "scripts/run_v24809_worldbank_budget_ladder_smoke_task.py"
SELECTED_COUNT = 16
ARM_COUNT = 3
EXECUTOR_CONCURRENCY = 16
MODEL_SLOT_CAP = 8
PARENT_TIMEOUT_SECONDS = 255.0
TASK_WALL_SECONDS = 240.0
CLEANUP_RESERVE_SECONDS = 5.0
MINIMUM_ATTEMPT_SECONDS = 0.05
MODEL_SLOT_POOL_ID = "v24263_score_first_global_model_slots_v1"
PROTECTED_WATCHERS = (
    (795336, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, "scripts/watch_v24218_exact220_executor.py"),
    (2808901, "scripts/watch_v24215_joint_package_recovery.py"),
    (2889939, "scripts/watch_v24216_package_gate.py"),
)
MODEL = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "name": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 65,
    "max_retries": 2,
}
SEARCH = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "model": "gpt-5.6-sol",
    "workers": 1,
    "batch_size": 8,
    "context_size": "medium",
    "max_output_tokens": 7_000,
    "timeout_seconds": 65,
    "max_retries": 2,
    "fetch_workers": 10,
    "fetch_timeout_seconds": 35,
    "hard_fetch_deadline_seconds": 40,
}
LIMITS = {
    "wall_seconds": 240,
    "model_calls": 2,
    "search_queries": 4,
    "fetch_targets": 10,
    "search_results_per_query": 3,
    "evidence_chars": 60_000,
    "page_chars": 5_000,
    "plan_output_tokens": 4_000,
    "synthesis_output_tokens": 30_000,
    "repair_output_tokens": 12_000,
}
TARGETS = (
    {
        "label": "Male unemployment rate (%)",
        "indicator": "SL.UEM.TOTL.MA.ZS",
        "year": "2023",
    },
    {
        "label": "Female unemployment rate (%)",
        "indicator": "SL.UEM.TOTL.FE.ZS",
        "year": "2023",
    },
)
ADAPTIVE_POLICY = AdaptivePolicy(
    calibration_ref_sha256=hashlib.sha256(
        b"v24805-smoke-policy-not-main-calibration"
    ).hexdigest(),
    calibration_complete=True,
    per_lookup_cost=0.04,
)
RUNTIME_SOURCES = (
    Path("src/deepwide_agent/v24809_worldbank_budget_ladder_smoke_contract.py"),
    Path("src/deepwide_agent/v24809_worldbank_budget_ladder_runner_integration.py"),
    Path("scripts/run_v24809_worldbank_budget_ladder_smoke_forward.py"),
    Path("scripts/run_v24809_worldbank_budget_ladder_smoke_task.py"),
    Path("src/deepwide_agent/v24804_shared_prefix_budget_ladder.py"),
    Path("src/deepwide_agent/v24696_worldbank_search_transport.py"),
    Path("src/deepwide_agent/v24686_worldbank_target_value_runtime.py"),
    Path("src/deepwide_agent/v24468_total_wall_transport.py"),
    Path("src/deepwide_agent/v24316_deadline_search.py"),
    Path("src/deepwide_agent/v24312_deadline_reliability.py"),
    Path("src/deepwide_agent/v24309_runner_exit_integration.py"),
    Path("src/deepwide_agent/v24325_shared_prefix_revision_runtime.py"),
    Path("src/deepwide_agent/v24272_two_wave_entropy_voc.py"),
    Path("src/deepwide_agent/v24269_task_union_discovery.py"),
    Path("src/deepwide_agent/v24263_global_model_limiter.py"),
    Path("src/deepwide_agent/v24257_score_first_runtime.py"),
    Path("src/deepwide_agent/v24637_objective_alignment_runtime.py"),
    Path("src/deepwide_agent/v24644_primary_identity_pair_runtime.py"),
    Path("src/deepwide_agent/clients.py"),
    Path("scripts/deepwide_api_lease.py"),
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for pid, marker in PROTECTED_WATCHERS:
        stat = proc_root / str(pid) / "stat"
        cmdline = proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.48.09 protected watcher is absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.48.09 protected watcher identity drifted")
        output.append({"pid": pid, "marker": marker, "start_ticks": int(suffix[19])})
    return output


def validate_task_vector(tasks: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if not isinstance(tasks, Sequence) or isinstance(tasks, (str, bytes)) or len(tasks) != SELECTED_COUNT:
        raise ValueError("V2.48.09 task denominator drifted")
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    expected_columns = [
        "Country",
        *(f"{target['label']} [{target['indicator']}] @{target['year']}" for target in TARGETS),
    ]
    for item in tasks:
        if not isinstance(item, Mapping) or set(item) != {"opaque_id", "question"}:
            raise ValueError("V2.48.09 visible task schema drifted")
        opaque_id, question = item.get("opaque_id"), item.get("question")
        if (
            not isinstance(opaque_id, str)
            or not opaque_id.startswith("task_")
            or len(opaque_id) != 29
            or opaque_id in seen
            or not isinstance(question, str)
        ):
            raise ValueError("V2.48.09 visible task identity drifted")
        visible = _visible_contract(question)
        if len(visible["countries"]) != 4 or visible["columns"] != expected_columns:
            raise ValueError("V2.48.09 visible task contract drifted")
        seen.add(opaque_id)
        output.append({"opaque_id": opaque_id, "question": question})
    return output


def dependency_manifest(root: Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in RUNTIME_SOURCES:
        path = root / relative
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or relative.parts[:1] in {("evaluation",), ("outputs",)}
            or path.is_symlink()
            or not path.is_file()
            or not path.resolve().is_relative_to(root.resolve())
            or subprocess.run(
                ["git", "ls-files", "--error-unmatch", str(relative)], cwd=root,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, timeout=20, check=False,
            ).returncode != 0
        ):
            raise RuntimeError(f"V2.48.09 runtime source drifted: {relative}")
        output[str(relative)] = sha256(path)
    return dict(sorted(output.items()))


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("protocol_payload_sha256", None)
    tasks = validate_task_vector(copied.get("visible_tasks") or [])
    manifest = dependency_manifest(root)
    execution = copied.get("execution") or {}
    if (
        copied.get("role") != "v24809_worldbank_budget_ladder_smoke_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or seal != payload_sha256(unsigned)
        or copied.get("dependency_manifest") != manifest
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or copied.get("build_audit_sha256") != sha256(root / BUILD_AUDIT)
        or copied.get("task_contract") != {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": SELECTED_COUNT,
            "arm_count": ARM_COUNT,
            "opaque_id_vector_sha256": payload_sha256([task["opaque_id"] for task in tasks]),
            "visible_question_vector_sha256": payload_sha256([task["question"] for task in tasks]),
        }
        or execution.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or execution.get("model_slot_cap") != MODEL_SLOT_CAP
        or execution.get("model") != MODEL
        or execution.get("search") != SEARCH
        or execution.get("limits") != LIMITS
        or execution.get("protected_watchers") != protected_watcher_snapshot()
        or copied.get("authorization") != {
            "preactivation_audit_generation": True,
            "activation": False,
            "single_smoke_forward": False,
            "evaluator": False,
            "main_calibration_lock_validation_or_confirmatory": False,
            "public_dev64_or_exact220": False,
        }
    ):
        raise RuntimeError("V2.48.09 protocol drifted")
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "dependency_manifest", "payload_sha256", "protected_watcher_snapshot",
    "sha256", "validate_protocol", "validate_task_vector",
]
