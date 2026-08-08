#!/usr/bin/env python3
"""Run the V2.48.47 external shared-prefix projection-budget gate."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24847_projection_budget_external_contract as contract  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


URLS = (
    "https://api.worldbank.org/v2/country/all/indicator/SH.STA.BASS.ZS?date=2022&format=json&per_page=400",
    "https://api.worldbank.org/v2/country/all/indicator/SL.UEM.TOTL.ZS?date=2023&format=json&per_page=400",
)


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.48.47 runner expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.47 runner expected object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.48.47 runner expected ordinary JSONL")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _new(path: Path, value: Any) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _new_bytes(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "deepwide-v24847/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise RuntimeError("V2.48.47 official snapshot fetch failed")
        data = response.read(2 * 1024 * 1024 + 1)
    if not data or len(data) > 2 * 1024 * 1024:
        raise RuntimeError("V2.48.47 official snapshot size drifted")
    return data


def _raw_pages(blobs: list[bytes]) -> dict[str, Any]:
    pages = []
    hashes = []
    for index, blob in enumerate(blobs):
        hashes.append(hashlib.sha256(blob).hexdigest())
        value = json.loads(blob)
        records = value[1] if isinstance(value, list) and len(value) == 2 else None
        if not isinstance(records, list):
            raise RuntimeError("V2.48.47 World Bank response drifted")
        target = contract.TARGETS[index]
        valid_records = []
        for record in records:
            if not isinstance(record, dict) or record.get("value") is None:
                continue
            valid_records.append(record)
        chunk_size = (len(valid_records) + 3) // 4
        for chunk_index in range(4):
            current = valid_records[
                chunk_index * chunk_size : (chunk_index + 1) * chunk_size
            ]
            lines = [
                f"| Country | ISO3 | {target['label']} [{target['indicator']}] @{target['year']} |",
                "|---|---|---:|",
            ]
            for record in current:
                country = record.get("country") or {}
                lines.append(
                    f"| {country.get('value', '')} | {record.get('countryiso3code', '')} | {record.get('value')} |"
                )
            pages.append(
                {
                    "title": (
                        f"World Bank official indicator {target['indicator']} "
                        f"{target['year']} partition {chunk_index + 1}/4"
                    ),
                    "url": URLS[index] + f"&deepwide_partition={chunk_index + 1}",
                    "content": "\n".join(lines),
                }
            )
    value = {
        "artifact_version": 1, "role": "v24847_frozen_raw_page_prefix",
        "source_count": 2, "structural_page_count": 8,
        "fixed_records_per_partition_rule": "ceil(valid_records/4)",
        "response_sha256": hashes, "pages": pages,
        "fetched_once_before_arm_branch": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }
    value["freeze_payload_sha256"] = contract.payload_sha256(value)
    return value


def build_forward_audit(*, now: int | None = None) -> dict[str, Any]:
    protocol = _read(ROOT / contract.PROTOCOL)
    forward = _read(ROOT / contract.FORWARD_RESULT)
    freeze = _read(ROOT / contract.PREDICTION_FREEZE)
    summary = _read(ROOT / contract.RUN_SUMMARY)
    rows = [
        json.loads(line)
        for line in (ROOT / contract.PREDICTIONS).read_text(encoding="utf-8").splitlines()
        if line
    ]
    checks = {
        "forward_result_sealed": (
            lambda unsigned: unsigned.pop("result_payload_sha256", None)
            == contract.payload_sha256(unsigned)
        )(dict(forward)),
        "prediction_freeze_sealed": (
            lambda unsigned: unsigned.pop("freeze_payload_sha256", None)
            == contract.payload_sha256(unsigned)
        )(dict(freeze)),
        "run_summary_sealed": (
            lambda unsigned: unsigned.pop("summary_payload_sha256", None)
            == contract.payload_sha256(unsigned)
        )(dict(summary)),
        "prediction_denominator_32x2": len(rows) == 32
        and all(set(row.get("predictions") or {}) == set(contract.ARMS) for row in rows),
        "all_predictions_terminal_before_private_evaluator_open": forward.get(
            "all_predictions_terminal_before_private_evaluator_open"
        )
        is True,
        "prediction_hashes_valid": all(
            row.get("prediction_sha256", {}).get(arm)
            == contract.payload_sha256(row["predictions"][arm])
            for row in rows
            for arm in contract.ARMS
        ),
        "raw_prefix_hash_bound": freeze.get("raw_page_freeze_sha256")
        == contract.sha256(ROOT / contract.RAW_PAGE_FREEZE),
        "no_retry_resume_or_selective_rerun": all(
            row.get("retry_resume_skip_or_selective_rerun") is False for row in rows
        ),
        "candidate_orphans_zero": summary.get("projection_trigger_counts", {})
        .get("atomic_30k", {})
        .get("orphans")
        == 0,
        "protected_watchers_unchanged": contract.protected_watcher_snapshot()
        == protocol["execution"]["protected_watchers"],
    }
    value = {
        "artifact_version": 1,
        "role": "v24847_projection_budget_external_forward_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "predictions_sha256": contract.sha256(ROOT / contract.PREDICTIONS),
        "raw_page_freeze_sha256": contract.sha256(ROOT / contract.RAW_PAGE_FREEZE),
        "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
        "checks": checks,
        "findings": sorted(name for name, okay in checks.items() if not okay),
        "private_population_gold_or_evaluator_opened_or_hashed": False,
        "network_model_fetch_or_evaluator_called_by_audit": False,
        "authorization": {
            "postfreeze_external_evaluator_protocol": all(checks.values()),
            "same_population_retry_resume_or_rerun": False,
            "public_dev64_or_exact220": False,
        },
    }
    value["audit_valid"] = not value["findings"]
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] == "audit":
        value = build_forward_audit()
        if not value["audit_valid"]:
            raise RuntimeError(f"V2.48.47 forward audit failed: {value['findings']}")
        _new(ROOT / contract.FORWARD_AUDIT, value)
        print(json.dumps({"path": str(contract.FORWARD_AUDIT), "audit_valid": True}, sort_keys=True))
        return
    protocol = _read(ROOT / contract.PROTOCOL)
    start = _read(ROOT / contract.EXECUTION_START)
    if (
        start.get("status") != "authorized_not_started"
        or start.get("authorization", {}).get("single_external_forward") is not True
        or protocol.get("protocol_id") != contract.PROTOCOL_ID
        or protocol.get("source_policy", {}).get("mapping_category_question_type_split_score_reward_read_by_forward") is not False
    ):
        raise RuntimeError("V2.48.47 execution authorization drifted")
    if subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, stdout=subprocess.PIPE, text=True, check=True).stdout.strip():
        raise RuntimeError("V2.48.47 forward requires clean worktree")
    if (ROOT / contract.OUTPUT_ROOT).exists():
        raise RuntimeError("V2.48.47 output root not pristine")
    tasks = contract.validate_task_vector(
        _read_jsonl(ROOT / contract.VISIBLE_TASK_ARTIFACT)
    )
    if protocol.get("visible_task_artifact", {}).get("sha256") != contract.sha256(
        ROOT / contract.VISIBLE_TASK_ARTIFACT
    ):
        raise RuntimeError("V2.48.47 visible task artifact drifted")
    with acquire_deepwide_api_lease(
        ROOT, owner="v24847_projection_budget_external_forward_v1",
        purpose="target_cell_disjoint_projection_budget_shared_prefix_gate",
        path=ROOT / contract.LEASE_PATH,
    ):
        if contract.protected_watcher_snapshot() != protocol["execution"]["protected_watchers"]:
            raise RuntimeError("V2.48.47 protected watcher drifted")
        (ROOT / contract.OUTPUT_ROOT).mkdir(parents=True, mode=0o700)
        (ROOT / contract.TASK_ROOT).mkdir(mode=0o700)
        (ROOT / contract.MODEL_SLOT_DIRECTORY).mkdir(mode=0o700)
        _jsonl(ROOT / contract.VISIBLE_TASKS, tasks)
        started = time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            blobs = list(pool.map(_fetch, URLS))
        expected = protocol["shared_prefix"]["expected_response_sha256"]
        observed = [hashlib.sha256(blob).hexdigest() for blob in blobs]
        if observed != expected:
            raise RuntimeError("V2.48.47 public snapshot bytes drifted from preregistration")
        for index, blob in enumerate(blobs, 1):
            _new_bytes(
                ROOT / contract.RAW_PAGE_ROOT / f"response_{index:02d}.bin", blob
            )
        raw = _raw_pages(blobs)
        _new(ROOT / contract.RAW_PAGE_FREEZE, raw)
        outcomes: dict[int, dict[str, Any]] = {}

        def run(index: int, task: dict[str, str]) -> tuple[int, dict[str, Any]]:
            directory = ROOT / contract.TASK_ROOT / f"task_{index:04d}"
            directory.mkdir(mode=0o700)
            task_path = directory / "visible_task.json"
            raw_path = directory / "raw_pages.json"
            result_path = directory / "result.json"
            _new(task_path, task)
            _new(raw_path, raw)
            completed = subprocess.run(
                [
                    str(ROOT / ".venv-eval/bin/python"), "-I", "-B",
                    str(ROOT / contract.CHILD_MARKER), "--task", str(task_path),
                    "--raw-pages", str(raw_path), "--result", str(result_path),
                ],
                cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, timeout=contract.TASK_WALL_SECONDS, check=False,
            )
            if completed.returncode == 0 and result_path.is_file():
                return index, _read(result_path)
            fallback = {
                arm: "| Country | Value |\n|---|---|\n| Unknown | Unknown |"
                for arm in contract.ARMS
            }
            return index, {
                "artifact_version": 1, "role": "v24847_projection_budget_task_result",
                "opaque_id": task["opaque_id"], "status": "failure_as_zero_projection",
                "label_blind": True, "runtime_input_keys": ["opaque_id", "question"],
                "raw_page_freeze_sha256": contract.sha256(raw_path), "predictions": fallback,
                "prediction_sha256": {arm: contract.payload_sha256(fallback[arm]) for arm in contract.ARMS},
                "projection_receipts": {}, "model_usage": {},
                "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
                "retry_resume_skip_or_selective_rerun": False,
                "result_payload_sha256": "failure-as-zero",
            }

        with concurrent.futures.ThreadPoolExecutor(max_workers=contract.EXECUTOR_CONCURRENCY) as pool:
            futures = [pool.submit(run, index, task) for index, task in enumerate(tasks, 1)]
            for future in concurrent.futures.as_completed(futures):
                index, result = future.result()
                outcomes[index] = result
                _atomic_json(
                    ROOT / contract.SAFE_PROGRESS,
                    {
                        "artifact_version": 1, "role": "v24847_safe_progress",
                        "selected": 32, "completed": len(outcomes), "unfinished": 32 - len(outcomes),
                        "contains_question_prediction_url_page_value_or_credential": False,
                    },
                )
        wall = time.monotonic() - started
    rows = [outcomes[index] for index in range(1, 33)]
    _jsonl(ROOT / contract.PREDICTIONS, rows)
    freeze = {
        "artifact_version": 1, "role": "v24847_prediction_freeze", "selected": 32,
        "arm_predictions": 64, "predictions_sha256": contract.sha256(ROOT / contract.PREDICTIONS),
        "raw_page_freeze_sha256": contract.sha256(ROOT / contract.RAW_PAGE_FREEZE),
        "private_population_gold_or_evaluator_opened_or_hashed": False,
        "retry_resume_skip_or_selective_rerun": False,
    }
    freeze["freeze_payload_sha256"] = contract.payload_sha256(freeze)
    _new(ROOT / contract.PREDICTION_FREEZE, freeze)
    valid = sum(row["status"] == "completed" for row in rows)
    summary = {
        "artifact_version": 1, "role": "v24847_forward_run_summary", "selected": 32,
        "valid_task_results": valid, "failure_as_zero_tasks": 32-valid,
        "forward_wall_seconds": wall,
        "projection_trigger_counts": {
            arm: {
                "selected_table_continuations": sum(int((row.get("projection_receipts") or {}).get(arm, {}).get("selected_table_continuation_block_count", 0)) for row in rows),
                "dependency_additions": sum(int((row.get("projection_receipts") or {}).get(arm, {}).get("table_header_dependency_addition_count", 0)) for row in rows),
                "orphans": sum(int((row.get("projection_receipts") or {}).get(arm, {}).get("orphan_selected_table_continuation_block_count", 0)) for row in rows),
                "rendered_chars": sum(int((row.get("projection_receipts") or {}).get(arm, {}).get("projected_rendered_characters", 0)) for row in rows),
            }
            for arm in contract.ARMS
        },
    }
    summary["summary_payload_sha256"] = contract.payload_sha256(summary)
    _new(ROOT / contract.RUN_SUMMARY, summary)
    forward = {
        "artifact_version": 1, "role": "v24847_projection_budget_external_forward_result",
        "protocol_id": contract.PROTOCOL_ID, "selected": 32, "arm_predictions": 64,
        "valid_task_results": valid, "failure_as_zero_tasks": 32-valid,
        "forward_wall_seconds": wall, "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "raw_page_freeze_sha256": contract.sha256(ROOT / contract.RAW_PAGE_FREEZE),
        "all_predictions_terminal_before_private_evaluator_open": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "retry_resume_skip_or_selective_rerun": False,
    }
    forward["result_payload_sha256"] = contract.payload_sha256(forward)
    _new(ROOT / contract.FORWARD_RESULT, forward)
    print(json.dumps(forward, sort_keys=True))


if __name__ == "__main__":
    main()
