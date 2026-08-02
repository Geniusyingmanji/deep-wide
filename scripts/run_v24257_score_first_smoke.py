#!/usr/bin/env python3
"""Single-owner hard-deadline executor for the V2.42.57 smoke16 run."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent.runtime import load_manifest  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import (  # noqa: E402
    ScoreFirstLimits,
    build_score_first_fallback_result,
    validate_score_first_result,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DEFAULT_PROTOCOL = Path(
    "results/v24257_score_first_smoke_preregistration_v1_20260802.json"
)
ROLE = "v24257_score_first_smoke_result"


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"expected an ordinary file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected a JSON object: {path}")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    expected = unsigned.pop(field, None)
    return isinstance(expected, str) and expected == payload_sha256(unsigned)


def _relative(path: object) -> Path:
    value = Path(str(path))
    if value.is_absolute() or ".." in value.parts:
        raise RuntimeError("V2.42.57 protocol path is noncanonical")
    return value


def _new_json(path: Path, value: dict[str, Any], *, mode: int = 0o600) -> None:
    target = path.resolve(strict=False)
    if path.is_symlink() or target.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        mode,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        parent = os.open(
            target.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def validate_protocol(root: Path, value: dict[str, Any]) -> dict[str, Any]:
    if (
        value.get("role") != "v24257_score_first_smoke_preregistration"
        or value.get("protocol_id") != "v24257_score_first_smoke16_v1"
        or value.get("label_blind") is not True
        or not _sealed(value, "decision_contract_sha256")
    ):
        raise RuntimeError("V2.42.57 smoke protocol identity drifted")
    if value.get("task_contract", {}).get("runtime_boundary") != [
        "opaque_id",
        "question",
    ]:
        raise RuntimeError("V2.42.57 visible task boundary drifted")
    if value.get("source_policy", {}).get(
        "mapping_gold_category_question_type_evaluator_score_read"
    ) is not False:
        raise RuntimeError("V2.42.57 protocol is not label-blind")
    control = value.get("control_surface") or {}
    manifest = control.get("manifest") or {}
    if not isinstance(manifest, dict) or not manifest:
        raise RuntimeError("V2.42.57 control manifest is absent")
    live: dict[str, str] = {}
    for name, expected in manifest.items():
        relative = _relative(name)
        path = root / relative
        if path.is_symlink() or not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"V2.42.57 control source drifted: {relative}")
        live[str(relative)] = expected
    if payload_sha256(live) != control.get("manifest_sha256"):
        raise RuntimeError("V2.42.57 control manifest seal drifted")
    limits = ScoreFirstLimits(**dict(value.get("limits") or {}))
    limits.validate()
    return value


def validate_activation(root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    activation_path = root / _relative(protocol["execution"]["activation_path"])
    activation = read_object(activation_path)
    if (
        activation.get("role") != "v24257_score_first_smoke_activation"
        or activation.get("status") != "active"
        or activation.get("protocol_sha256")
        != sha256(root / DEFAULT_PROTOCOL)
        or activation.get("control_manifest_sha256")
        != protocol["control_surface"]["manifest_sha256"]
        or activation.get("benchmark_question_prediction_mapping_gold_score_read")
        is not False
        or not _sealed(activation, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.42.57 activation drifted")
    return activation


def _selected_tasks(root: Path, protocol: dict[str, Any]) -> list[dict[str, str]]:
    contract = protocol["task_contract"]
    manifest_path = root / _relative(contract["manifest"]["path"])
    ids_path = root / _relative(contract["id_source"]["path"])
    if sha256(manifest_path) != contract["manifest"]["sha256"]:
        raise RuntimeError("V2.42.57 manifest bytes drifted")
    if sha256(ids_path) != contract["id_source"]["sha256"]:
        raise RuntimeError("V2.42.57 ID source bytes drifted")
    ordered_ids = [line for line in ids_path.read_text().splitlines() if line]
    selected_ids = ordered_ids[: int(contract["selected_count"])]
    selected_sha = payload_sha256(selected_ids)
    if selected_sha != contract["selected_opaque_ids_sha256"]:
        raise RuntimeError("V2.42.57 selected ID order drifted")
    by_id = {task["opaque_id"]: task for task in load_manifest(manifest_path)}
    if len(selected_ids) != int(contract["selected_count"]) or any(
        opaque_id not in by_id for opaque_id in selected_ids
    ):
        raise RuntimeError("V2.42.57 selected task set is incomplete")
    return [by_id[opaque_id] for opaque_id in selected_ids]


def _safe_progress(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        return {}
    value = read_object(path)
    allowed = {
        "artifact_version",
        "role",
        "stage",
        "elapsed_seconds",
        "admitted_model_calls",
        "admitted_search_queries",
        "admitted_fetch_targets",
        "search_batch_count",
        "projected_chars",
        "events",
        "model_cost",
        "search_cost",
        "contains_question_query_url_page_prediction_or_answer",
        "mapping_gold_evaluator_or_score_read",
    }
    if (
        set(value) != allowed
        or value.get("role") != "v24257_score_first_safe_progress"
        or value.get("contains_question_query_url_page_prediction_or_answer")
        is not False
        or value.get("mapping_gold_evaluator_or_score_read") is not False
    ):
        raise RuntimeError("V2.42.57 safe progress schema drifted")
    return value


def _terminate_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    process.wait(timeout=5)


def _start_ticks(pid: int, proc_root: Path = Path("/proc")) -> int:
    raw = (proc_root / str(pid) / "stat").read_text(encoding="utf-8")
    suffix = raw[raw.rfind(")") + 2 :].split()
    if len(suffix) <= 19:
        raise RuntimeError("V2.42.57 process stat is truncated")
    return int(suffix[19])


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
        str(root / "scripts/run_v24257_score_first_task.py"),
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


def _child_env() -> dict[str, str]:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is unavailable")
    return {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "TERM": "xterm-256color",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
        "ANTHROPIC_API_KEY": key,
    }


def run_one_task(
    root: Path,
    protocol: dict[str, Any],
    task: dict[str, str],
    task_root: Path,
    *,
    popen: Any = subprocess.Popen,
) -> dict[str, Any]:
    task_root.mkdir(mode=0o700, parents=False, exist_ok=False)
    task_path = task_root / "visible_task.json"
    result_path = task_root / "result.json"
    progress_path = task_root / "safe_progress.json"
    _new_json(task_path, task)
    command = _task_command(root, protocol, task_path, result_path, progress_path)
    started = time.monotonic()
    process = popen(
        command,
        cwd=root,
        env=_child_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    wall = float(protocol["limits"]["wall_seconds"])
    grace = float(protocol["execution"]["parent_deadline_grace_seconds"])
    timed_out = False
    try:
        return_code = process.wait(timeout=wall + grace)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_group(process)
        return_code = process.returncode
    elapsed = time.monotonic() - started
    if not timed_out and return_code == 0 and result_path.is_file():
        result = read_object(result_path)
        validate_score_first_result(result)
        return result
    progress = _safe_progress(progress_path)
    limits = ScoreFirstLimits(**dict(protocol["limits"]))
    result = build_score_first_fallback_result(
        task,
        limits=limits,
        completion_kind=(
            "hard_deadline_fallback" if timed_out else "worker_failure_fallback"
        ),
        failure_stage="parent_executor",
        failure_type=("HardDeadlineExceeded" if timed_out else "WorkerNonzeroExit"),
        elapsed_seconds=elapsed,
        last_progress=progress,
    )
    validate_score_first_result(result)
    _new_json(result_path, result)
    return result


def _p95(values: list[float]) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def aggregate_results(
    protocol: dict[str, Any], results: list[dict[str, Any]]
) -> dict[str, Any]:
    for result in results:
        validate_score_first_result(result)
    kinds: dict[str, int] = {}
    for result in results:
        kind = str(result["completion_kind"])
        kinds[kind] = kinds.get(kind, 0) + 1
    elapsed = [float(result["budget"]["elapsed_seconds"]) for result in results]
    tokens = [int(result["cost"]["system_total_tokens"]) for result in results]
    fetches = [int(result["cost"]["search"]["fetch_calls"]) for result in results]
    selected = int(protocol["task_contract"]["selected_count"])
    model_generated = kinds.get("primary", 0) + kinds.get("repaired", 0)
    fallbacks = selected - model_generated
    gate = protocol["gate_contract"]
    findings: list[str] = []
    if len(results) != selected:
        findings.append("not_exact_terminal_selected_count")
    if model_generated < int(gate["minimum_model_generated_tables"]):
        findings.append("model_generated_table_count_below_gate")
    if fallbacks > int(gate["maximum_fallback_tables"]):
        findings.append("fallback_table_count_above_gate")
    if kinds.get("hard_deadline_fallback", 0) > int(
        gate["maximum_hard_deadline_fallbacks"]
    ):
        findings.append("hard_deadline_fallback_count_above_gate")
    if _p95(elapsed) > float(gate["maximum_p95_wall_seconds"]):
        findings.append("p95_wall_seconds_above_gate")
    mean_tokens = sum(tokens) / max(1, len(tokens))
    mean_fetches = sum(fetches) / max(1, len(fetches))
    if mean_tokens > float(gate["maximum_mean_system_tokens"]):
        findings.append("mean_system_tokens_above_gate")
    if mean_fetches > float(gate["maximum_mean_fetch_calls"]):
        findings.append("mean_fetch_calls_above_gate")
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": protocol["protocol_id"],
        "created_at_unix": int(time.time()),
        "label_blind": True,
        "selected": selected,
        "terminal": len(results),
        "model_generated_tables": model_generated,
        "fallback_tables": fallbacks,
        "completion_kinds": kinds,
        "p95_wall_seconds": round(_p95(elapsed), 3),
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
    value["result_payload_sha256"] = payload_sha256(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--protocol", default=str(DEFAULT_PROTOCOL))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if root != ROOT:
        raise RuntimeError("V2.42.57 executor root drifted")
    protocol_path = Path(args.protocol)
    if not protocol_path.is_absolute():
        protocol_path = root / protocol_path
    if protocol_path.resolve() != (root / DEFAULT_PROTOCOL).resolve():
        raise RuntimeError("V2.42.57 protocol path drifted")
    protocol = validate_protocol(root, read_object(protocol_path))
    activation = validate_activation(root, protocol)
    tasks = _selected_tasks(root, protocol)
    execution = protocol["execution"]
    output_root = root / _relative(execution["output_root"])
    start_path = root / _relative(execution["execution_start_path"])
    result_path = root / _relative(execution["result_path"])
    predictions_path = output_root / "runtime_predictions.jsonl"
    if any(
        path.exists() or path.is_symlink()
        for path in (output_root, start_path, result_path)
    ):
        raise RuntimeError("V2.42.57 execution surface is not pristine")
    start = {
        "artifact_version": 1,
        "role": "v24257_score_first_smoke_execution_start",
        "created_at_unix": int(time.time()),
        "protocol_sha256": sha256(protocol_path),
        "activation_sha256": sha256(
            root / _relative(execution["activation_path"])
        ),
        "selected_opaque_ids_sha256": protocol["task_contract"]
        ["selected_opaque_ids_sha256"],
        "runner": {
            "pid": os.getpid(),
            "start_ticks": _start_ticks(os.getpid()),
            "marker": RUNNER_MARKER,
        },
        "label_blind": True,
        "mapping_gold_evaluator_or_score_read": False,
        "api_called_before_execution_start": False,
    }
    start["execution_start_payload_sha256"] = payload_sha256(start)
    _new_json(start_path, start)
    output_root.mkdir(mode=0o700, parents=True, exist_ok=False)
    task_parent = output_root / "tasks"
    task_parent.mkdir(mode=0o700)

    lease = protocol["lease_contract"]
    results: list[dict[str, Any]] = []
    with acquire_deepwide_api_lease(
        root,
        owner=lease["owner"],
        purpose=lease["purpose"],
        path=root / _relative(lease["path"]),
    ):
        for index, task in enumerate(tasks, start=1):
            task_root = task_parent / f"task_{index:04d}"
            result = run_one_task(root, protocol, task, task_root)
            results.append(result)
            _append_jsonl(predictions_path, result)
    aggregate = aggregate_results(protocol, results)
    aggregate["execution_start_sha256"] = sha256(start_path)
    aggregate["activation_payload_sha256"] = activation[
        "activation_payload_sha256"
    ]
    unsigned = dict(aggregate)
    unsigned.pop("result_payload_sha256", None)
    aggregate["result_payload_sha256"] = payload_sha256(unsigned)
    _new_json(result_path, aggregate)
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
