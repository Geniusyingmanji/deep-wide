"""Contract for a target-cell-disjoint 16k/30k shared-prefix gate."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


DATE = "20260808"
PROTOCOL_ID = "v24847_target_cell_disjoint_projection_budget_shared_prefix_v1"
SELECTED_COUNT = 32
ARMS = ("atomic_16k", "atomic_30k")
TARGETS = (
    {
        "label": "People using at least basic sanitation services (% of population)",
        "indicator": "SH.STA.BASS.ZS",
        "year": "2022",
    },
    {
        "label": "Unemployment, total (% of total labor force)",
        "indicator": "SL.UEM.TOTL.ZS",
        "year": "2023",
    },
)
MODEL = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "name": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 65,
    "max_retries": 2,
    "max_output_tokens": 8_000,
}
MODEL_SLOT_CAP = 8
EXECUTOR_CONCURRENCY = 16
TASK_WALL_SECONDS = 180
LEASE_PATH = Path("outputs/deepwide_api_effect.lock")
PROTECTED_WATCHERS = (
    (795336, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, "scripts/watch_v24218_exact220_executor.py"),
    (2808901, "scripts/watch_v24215_joint_package_recovery.py"),
    (2889939, "scripts/watch_v24216_package_gate.py"),
)
PROTOCOL = Path(f"results/v24847_projection_budget_external_preregistration_v1_{DATE}.json")
VISIBLE_TASK_ARTIFACT = Path(
    f"results/v24847_projection_budget_external_visible_tasks_v1_{DATE}.jsonl"
)
PREAUDIT = Path(f"results/v24847_projection_budget_external_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24847_projection_budget_external_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24847_projection_budget_external_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24847_projection_budget_external_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24847_projection_budget_external_v1_{DATE}")
VISIBLE_TASKS = OUTPUT_ROOT / "visible_tasks.jsonl"
RAW_PAGE_ROOT = OUTPUT_ROOT / "raw_pages"
RAW_PAGE_FREEZE = OUTPUT_ROOT / "raw_page_freeze.json"
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
PREDICTIONS = OUTPUT_ROOT / "frozen_predictions.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
RUNNER_MARKER = "scripts/run_v24847_projection_budget_external_forward.py"
CHILD_MARKER = "scripts/run_v24847_projection_budget_external_task.py"


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


def validate_task_vector(tasks: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if isinstance(tasks, (str, bytes)) or len(tasks) != SELECTED_COUNT:
        raise ValueError("V2.48.47 task denominator drifted")
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    expected_columns = [
        "Country",
        *(f"{target['label']} [{target['indicator']}] @{target['year']}" for target in TARGETS),
    ]
    for item in tasks:
        if not isinstance(item, Mapping) or set(item) != {"opaque_id", "question"}:
            raise ValueError("V2.48.47 visible task schema drifted")
        opaque = item["opaque_id"]
        question = item["question"]
        if (
            not isinstance(opaque, str)
            or not opaque.startswith("task_")
            or len(opaque) != 29
            or opaque in seen
            or not isinstance(question, str)
            or not question.strip()
            or "<COUNTRIES>" not in question
            or "</COUNTRIES>" not in question
            or not all(column in question for column in expected_columns)
        ):
            raise ValueError("V2.48.47 visible task binding drifted")
        seen.add(opaque)
        output.append({"opaque_id": opaque, "question": question})
    return output


def protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    output = []
    for pid, marker in PROTECTED_WATCHERS:
        stat = proc_root / str(pid) / "stat"
        cmdline = proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.48.47 protected watcher absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.48.47 protected watcher identity drifted")
        output.append({"pid": pid, "marker": marker, "start_ticks": int(suffix[19])})
    return output


__all__ = [name for name in globals() if name.isupper()] + [
    "payload_sha256", "protected_watcher_snapshot", "sha256", "validate_task_vector"
]
