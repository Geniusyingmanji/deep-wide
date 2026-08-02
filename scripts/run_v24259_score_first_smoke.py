#!/usr/bin/env python3
"""Hard-deadline single-owner executor for the V2.42.59 smoke16 gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24259_deterministic_table_normalizer import (  # noqa: E402
    ALL_KINDS,
    NORMALIZED_KINDS,
    build_v24259_fallback_result,
    validate_v24259_result,
)
from scripts import run_v24257_score_first_smoke as parent  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DEFAULT_PROTOCOL = Path(
    "results/v24259_deterministic_normalizer_smoke_preregistration_v1_20260802.json"
)
ROLE = "v24259_deterministic_normalizer_smoke_result"
RUNNER_MARKER = "scripts/run_v24259_score_first_smoke.py"


def validate_protocol(root: Path, value: dict[str, Any]) -> dict[str, Any]:
    if (
        value.get("role")
        != "v24259_deterministic_normalizer_smoke_preregistration"
        or value.get("protocol_id") != "v24259_deterministic_normalizer_smoke16_v1"
        or value.get("label_blind") is not True
        or not parent._sealed(value, "decision_contract_sha256")
        or value.get("source_policy", {}).get(
            "mapping_gold_category_question_type_evaluator_score_read"
        )
        is not False
    ):
        raise RuntimeError("V2.42.59 protocol identity drifted")
    manifest = value.get("control_surface", {}).get("manifest") or {}
    live: dict[str, str] = {}
    for name, expected in manifest.items():
        relative = parent._relative(name)
        path = root / relative
        if path.is_symlink() or not path.is_file() or parent.sha256(path) != expected:
            raise RuntimeError(f"V2.42.59 control source drifted: {relative}")
        live[str(relative)] = expected
    if parent.payload_sha256(live) != value["control_surface"].get("manifest_sha256"):
        raise RuntimeError("V2.42.59 control manifest drifted")
    ScoreFirstLimits(**dict(value.get("limits") or {})).validate()
    return value


def validate_activation(root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    path = root / parent._relative(protocol["execution"]["activation_path"])
    value = parent.read_object(path)
    if (
        value.get("role") != "v24259_deterministic_normalizer_smoke_activation"
        or value.get("status") != "active"
        or value.get("protocol_sha256") != parent.sha256(root / DEFAULT_PROTOCOL)
        or value.get("control_manifest_sha256")
        != protocol["control_surface"]["manifest_sha256"]
        or value.get(
            "benchmark_question_prediction_mapping_gold_category_evaluator_score_read"
        )
        is not False
        or not parent._sealed(value, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.42.59 activation drifted")
    return value


def _task_command(
    root: Path,
    protocol: dict[str, Any],
    task_path: Path,
    result_path: Path,
    progress_path: Path,
) -> list[str]:
    provider = protocol["provider_contract"]
    limits = protocol["limits"]
    return [
        str(root / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(root / "scripts/run_v24259_score_first_task.py"),
        "--task",
        str(task_path),
        "--result",
        str(result_path),
        "--progress",
        str(progress_path),
        "--proxy-url",
        provider["model"]["proxy_url"],
        "--model",
        provider["model"]["name"],
        "--reasoning-effort",
        provider["model"]["reasoning_effort"],
        "--service-tier",
        provider["model"]["service_tier"],
        "--model-timeout",
        str(provider["model"]["timeout_seconds"]),
        "--model-max-retries",
        str(provider["model"]["max_retries"]),
        "--search-model",
        provider["search"]["model"],
        "--search-timeout",
        str(provider["search"]["timeout_seconds"]),
        "--search-max-retries",
        str(provider["search"]["max_retries"]),
        "--search-workers",
        str(provider["search"]["workers"]),
        "--fetch-workers",
        str(provider["search"]["fetch_workers"]),
        "--fetch-timeout",
        str(provider["search"]["fetch_timeout_seconds"]),
        "--wall-seconds",
        str(limits["wall_seconds"]),
        "--model-calls",
        str(limits["model_calls"]),
        "--search-queries",
        str(limits["search_queries"]),
        "--fetch-targets",
        str(limits["fetch_targets"]),
        "--search-results-per-query",
        str(limits["search_results_per_query"]),
        "--evidence-chars",
        str(limits["evidence_chars"]),
        "--page-chars",
        str(limits["page_chars"]),
    ]


def run_one_task(
    root: Path,
    protocol: dict[str, Any],
    task: dict[str, str],
    task_root: Path,
    *,
    popen: Any = parent.subprocess.Popen,
) -> dict[str, Any]:
    task_root.mkdir(mode=0o700, parents=False, exist_ok=False)
    task_path = task_root / "visible_task.json"
    result_path = task_root / "result.json"
    progress_path = task_root / "safe_progress.json"
    parent._new_json(task_path, task)
    process = popen(
        _task_command(root, protocol, task_path, result_path, progress_path),
        cwd=root,
        env=parent._child_env(),
        stdin=parent.subprocess.DEVNULL,
        stdout=parent.subprocess.DEVNULL,
        stderr=parent.subprocess.DEVNULL,
        start_new_session=True,
    )
    started = parent.time.monotonic()
    timed_out = False
    try:
        return_code = process.wait(
            timeout=float(protocol["limits"]["wall_seconds"])
            + float(protocol["execution"]["parent_deadline_grace_seconds"])
        )
    except parent.subprocess.TimeoutExpired:
        timed_out = True
        parent._terminate_group(process)
        return_code = process.returncode
    elapsed = parent.time.monotonic() - started
    if not timed_out and return_code == 0 and result_path.is_file():
        result = parent.read_object(result_path)
        validate_v24259_result(result)
        return result
    progress = parent._safe_progress(progress_path)
    result = build_v24259_fallback_result(
        task,
        limits=ScoreFirstLimits(**dict(protocol["limits"])),
        completion_kind=(
            "hard_deadline_fallback" if timed_out else "worker_failure_fallback"
        ),
        failure_stage="parent_executor",
        failure_type=("HardDeadlineExceeded" if timed_out else "WorkerNonzeroExit"),
        elapsed_seconds=elapsed,
        last_progress=progress,
    )
    parent._new_json(result_path, result)
    return result


def aggregate_results(
    protocol: dict[str, Any], results: list[dict[str, Any]]
) -> dict[str, Any]:
    for result in results:
        validate_v24259_result(result)
    selected = int(protocol["task_contract"]["selected_count"])
    kinds: dict[str, int] = {}
    modes: dict[str, int] = {}
    for result in results:
        kind = str(result["completion_kind"])
        if kind not in ALL_KINDS:
            raise RuntimeError("V2.42.59 aggregate completion kind drifted")
        kinds[kind] = kinds.get(kind, 0) + 1
        for event in result["normalization"]["events"]:
            mode = str(event["mode"])
            modes[mode] = modes.get(mode, 0) + 1
    model_generated = sum(
        kinds.get(kind, 0)
        for kind in ("primary", "repaired", *sorted(NORMALIZED_KINDS))
    )
    fallback = selected - model_generated
    elapsed = [float(result["budget"]["elapsed_seconds"]) for result in results]
    tokens = [int(result["cost"]["system_total_tokens"]) for result in results]
    fetches = [int(result["cost"]["search"]["fetch_calls"]) for result in results]
    gate = protocol["gate_contract"]
    findings: list[str] = []
    if len(results) != selected:
        findings.append("not_exact_terminal_selected_count")
    if model_generated < int(gate["minimum_model_generated_tables"]):
        findings.append("model_generated_table_count_below_gate")
    if fallback > int(gate["maximum_fallback_tables"]):
        findings.append("fallback_table_count_above_gate")
    if kinds.get("hard_deadline_fallback", 0) > int(
        gate["maximum_hard_deadline_fallbacks"]
    ):
        findings.append("hard_deadline_fallback_count_above_gate")
    if parent._p95(elapsed) > float(gate["maximum_p95_wall_seconds"]):
        findings.append("p95_wall_seconds_above_gate")
    mean_tokens = sum(tokens) / max(1, len(tokens))
    mean_fetches = sum(fetches) / max(1, len(fetches))
    if mean_tokens > float(gate["maximum_mean_system_tokens"]):
        findings.append("mean_system_tokens_above_gate")
    if mean_fetches > float(gate["maximum_mean_fetch_calls"]):
        findings.append("mean_fetch_calls_above_gate")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": protocol["protocol_id"],
        "created_at_unix": int(parent.time.time()),
        "label_blind": True,
        "selected": selected,
        "terminal": len(results),
        "model_generated_tables": model_generated,
        "fallback_tables": fallback,
        "completion_kinds": kinds,
        "normalization_modes": modes,
        "p95_wall_seconds": round(parent._p95(elapsed), 3),
        "mean_wall_seconds": round(sum(elapsed) / max(1, len(elapsed)), 3),
        "mean_system_tokens": round(mean_tokens, 3),
        "mean_fetch_calls": round(mean_fetches, 3),
        "total_system_tokens": sum(tokens),
        "total_fetch_calls": sum(fetches),
        "engineering_gate": "go" if not findings else "no_go",
        "findings": findings,
        "prediction_hashes": [result["prediction_sha256"] for result in results],
        "mapping_gold_category_question_type_evaluator_score_read": False,
        "official_evaluator_called": False,
        "dev64_or_full220_authorized": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    value["result_payload_sha256"] = parent.payload_sha256(value)
    return value


def main() -> None:
    parser = parent.argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--protocol", default=str(DEFAULT_PROTOCOL))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    protocol_path = Path(args.protocol)
    if not protocol_path.is_absolute():
        protocol_path = root / protocol_path
    if root != ROOT or protocol_path.resolve() != (root / DEFAULT_PROTOCOL).resolve():
        raise RuntimeError("V2.42.59 executor path drifted")
    protocol = validate_protocol(root, parent.read_object(protocol_path))
    activation = validate_activation(root, protocol)
    tasks = parent._selected_tasks(root, protocol)
    execution = protocol["execution"]
    output_root = root / parent._relative(execution["output_root"])
    start_path = root / parent._relative(execution["execution_start_path"])
    result_path = root / parent._relative(execution["result_path"])
    predictions_path = output_root / "runtime_predictions.jsonl"
    if any(path.exists() or path.is_symlink() for path in (output_root, start_path, result_path)):
        raise RuntimeError("V2.42.59 execution surface is not pristine")
    start: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24259_deterministic_normalizer_smoke_execution_start",
        "created_at_unix": int(parent.time.time()),
        "protocol_sha256": parent.sha256(protocol_path),
        "activation_sha256": parent.sha256(
            root / parent._relative(execution["activation_path"])
        ),
        "selected_opaque_ids_sha256": protocol["task_contract"][
            "selected_opaque_ids_sha256"
        ],
        "runner": {
            "pid": parent.os.getpid(),
            "start_ticks": parent._start_ticks(parent.os.getpid()),
            "marker": RUNNER_MARKER,
        },
        "label_blind": True,
        "mapping_gold_category_question_type_evaluator_score_read": False,
        "api_called_before_execution_start": False,
    }
    start["execution_start_payload_sha256"] = parent.payload_sha256(start)
    parent._new_json(start_path, start)
    output_root.mkdir(mode=0o700, parents=True, exist_ok=False)
    task_parent = output_root / "tasks"
    task_parent.mkdir(mode=0o700)
    results: list[dict[str, Any]] = []
    lease = protocol["lease_contract"]
    with acquire_deepwide_api_lease(
        root,
        owner=lease["owner"],
        purpose=lease["purpose"],
        path=root / parent._relative(lease["path"]),
    ):
        for index, task in enumerate(tasks, start=1):
            result = run_one_task(
                root, protocol, task, task_parent / f"task_{index:04d}"
            )
            results.append(result)
            parent._append_jsonl(predictions_path, result)
    aggregate = aggregate_results(protocol, results)
    aggregate["execution_start_sha256"] = parent.sha256(start_path)
    aggregate["activation_payload_sha256"] = activation[
        "activation_payload_sha256"
    ]
    unsigned = dict(aggregate)
    unsigned.pop("result_payload_sha256", None)
    aggregate["result_payload_sha256"] = parent.payload_sha256(unsigned)
    parent._new_json(result_path, aggregate)
    print(
        json.dumps(
            {
                "result": str(result_path),
                "engineering_gate": aggregate["engineering_gate"],
                "terminal": aggregate["terminal"],
                "model_generated_tables": aggregate["model_generated_tables"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
