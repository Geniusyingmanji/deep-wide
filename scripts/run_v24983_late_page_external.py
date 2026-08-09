#!/usr/bin/env python3
"""Run the single authorized V2.49.83 paired external forward."""

from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24983_late_page_external_contract as contract  # noqa: E402
from deepwide_agent import v24982_paired_production_runtime as runtime  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from deepwide_agent.v24468_total_wall_transport import (  # noqa: E402
    HardTotalWallResponsesClient,
)
from deepwide_agent.v24630_exact220_contract import (  # noqa: E402
    CLEANUP_RESERVE_SECONDS,
    MINIMUM_MODEL_ATTEMPT_SECONDS,
)
from deepwide_agent.v24981_late_page_bound_fetch import (  # noqa: E402
    LatePageBoundSearchClient,
    validate_search_class,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


def _read(relative: Path) -> dict[str, Any]:
    path = ROOT / relative
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
        raise RuntimeError("V2.49.83 runner expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.83 runner expected JSON object")
    return value


def _publish_json(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _publish_jsonl(path: Path, rows: list[Mapping[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _clean_pushed() -> None:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(
        ROOT, "rev-parse", "HEAD"
    ) != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.49.83 forward requires clean pushed HEAD")


def _validate_start() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    start = _read(contract.EXECUTION_START)
    if (
        start.get("role") != "v24983_late_page_external_execution_start"
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or start.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256") != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("task_vector_sha256") != protocol["population"]["task_vector_sha256"]
        or start.get("protected_watchers") != contract.watcher_snapshot()
        or start.get("authorization")
        != {
            "one_external_forward": True,
            "evaluator": False,
            "public_exact220_or_sota": False,
            "retry_resume_selective_rerun": False,
        }
        or not contract.sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.49.83 execution start drifted")
    return protocol, start


def _prepare_output() -> None:
    root = ROOT / contract.OUTPUT_ROOT
    if root.exists() or root.is_symlink():
        raise FileExistsError(root)
    root.mkdir(parents=True, mode=0o700)
    slots = ROOT / contract.MODEL_SLOT_DIRECTORY
    slots.mkdir(mode=0o700)
    for index in range(1, contract.MODEL_SLOT_CAP + 1):
        _publish_json(
            slots / f"slot_{index:02d}.lock",
            {
                "artifact_version": 1,
                "role": "v24983_model_slot",
                "slot": index,
                "slot_cap": contract.MODEL_SLOT_CAP,
                "contains_credential_or_benchmark_content": False,
            },
        )


def _task(index: int, task: Mapping[str, str]) -> dict[str, Any]:
    started = time.monotonic()
    deadline = started + float(contract.LIMITS["wall_seconds"])
    inner_model = HardTotalWallResponsesClient(
        contract.MODEL["proxy_url"],
        contract.MODEL["name"],
        reasoning_effort=contract.MODEL["reasoning_effort"],
        service_tier=contract.MODEL["service_tier"],
        timeout=contract.MODEL["timeout_seconds"],
        max_retries=contract.MODEL["max_retries"],
        absolute_deadline=deadline,
        cleanup_reserve_seconds=CLEANUP_RESERVE_SECONDS,
        minimum_attempt_seconds=MINIMUM_MODEL_ATTEMPT_SECONDS,
        stage_callback=lambda _event: None,
    )
    model = DeadlineAwareGlobalModelSlotLimiter(
        inner_model,
        slot_directory=ROOT / contract.MODEL_SLOT_DIRECTORY,
        output_root=ROOT / contract.OUTPUT_ROOT,
        slot_cap=contract.MODEL_SLOT_CAP,
        pool_id=POOL_ID,
        absolute_deadline=deadline,
        cleanup_reserve_seconds=CLEANUP_RESERVE_SECONDS,
        minimum_attempt_seconds=MINIMUM_MODEL_ATTEMPT_SECONDS,
    )
    search = LatePageBoundSearchClient(
        contract.SEARCH["proxy_url"],
        contract.SEARCH["model"],
        visible_question=str(task["question"]),
        reasoning_effort=contract.MODEL["reasoning_effort"],
        service_tier=contract.MODEL["service_tier"],
        timeout=contract.SEARCH["timeout_seconds"],
        max_retries=contract.SEARCH["max_retries"],
        absolute_deadline=deadline,
        cleanup_reserve_seconds=CLEANUP_RESERVE_SECONDS,
        minimum_attempt_seconds=MINIMUM_MODEL_ATTEMPT_SECONDS,
        max_workers=contract.SEARCH["workers"],
        batch_size=contract.SEARCH["batch_size"],
        search_context_size=contract.SEARCH["context_size"],
        max_output_tokens=contract.SEARCH["max_output_tokens"],
        fetch_pages=False,
        fetch_workers=contract.SEARCH["fetch_workers"],
        fetch_timeout=contract.SEARCH["fetch_timeout_seconds"],
        max_page_chars=contract.LIMITS["page_chars"],
        hard_fetch_deadline_seconds=contract.SEARCH["hard_fetch_deadline_seconds"],
        stage_callback=lambda _event: None,
    )
    result = runtime.run_paired_task(
        task,
        model=model,
        search=search,
        limits=ScoreFirstLimits(**contract.LIMITS),
        monotonic=time.monotonic,
    )
    checked = runtime.validate_result(result)
    if checked["opaque_id"] != task["opaque_id"]:
        raise RuntimeError("V2.49.83 task identity drifted")
    return checked


def run_forward() -> dict[str, Any]:
    _clean_pushed()
    protocol, start = _validate_start()
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (
            contract.FORWARD_RESULT,
            contract.FORWARD_AUDIT,
            contract.EVALUATOR_PROTOCOL,
            contract.RESULT,
            contract.POSTAUDIT,
            contract.OUTPUT_ROOT,
        )
    ):
        raise RuntimeError("V2.49.83 forward surface is not pristine")
    if protocol["execution"]["protected_watchers"] != contract.watcher_snapshot():
        raise RuntimeError("V2.49.83 protected watcher identity drifted")
    validate_search_class()
    tasks = contract.task_vector()
    _prepare_output()
    started = time.monotonic()
    results: list[dict[str, Any] | None] = [None] * len(tasks)
    with acquire_deepwide_api_lease(
        ROOT,
        owner=contract.LEASE_OWNER,
        purpose=contract.LEASE_PURPOSE,
        path=ROOT / contract.LEASE_PATH,
    ):
        with ThreadPoolExecutor(max_workers=contract.EXECUTOR_CONCURRENCY) as pool:
            futures = {
                pool.submit(_task, index, task): index
                for index, task in enumerate(tasks)
            }
            for future in as_completed(futures):
                index = futures[future]
                results[index] = future.result()
    rows = [runtime.validate_result(value) for value in results if value is not None]
    if len(rows) != contract.TASK_COUNT:
        raise RuntimeError("V2.49.83 terminal task denominator drifted")
    _publish_jsonl(ROOT / contract.TASK_RESULTS, rows)
    prediction_hashes = [
        {
            arm: contract.payload_sha256(row["predictions"][arm])
            for arm in contract.ARMS
        }
        for row in rows
    ]
    freeze = contract.seal(
        {
            "artifact_version": 1,
            "role": "v24983_late_page_external_prediction_freeze",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "task_count": contract.TASK_COUNT,
            "task_results_sha256": contract.sha256(ROOT / contract.TASK_RESULTS),
            "prediction_hash_vector_sha256": contract.payload_sha256(prediction_hashes),
            "all_predictions_terminal_before_gold_fetch_or_quality_decision": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        },
        "freeze_payload_sha256",
    )
    _publish_json(ROOT / contract.PREDICTION_FREEZE, freeze)
    aggregate = {
        "terminal_tasks": len(rows),
        "both_arms_model_success_tasks": sum(all(row["model_success"].values()) for row in rows),
        "tasks_with_usable_page": sum(row["content_free_receipt"]["usable_page_count"] > 0 for row in rows),
        "tasks_with_changed_page": sum(row["content_free_receipt"]["candidate_changed_page_count"] > 0 for row in rows),
        "tasks_with_mechanism_engaged": sum(row["content_free_receipt"]["mechanism_engaged_page_count"] > 0 for row in rows),
        "prediction_changed_tasks": sum(row["prediction_changed"] for row in rows),
        "model_logical_calls": sum(row["content_free_receipt"]["model_logical_call_count"] for row in rows),
        "model_provider_requests": sum(row["content_free_receipt"]["model_provider_request_count"] for row in rows),
        "executed_queries": sum(row["content_free_receipt"]["executed_query_count"] for row in rows),
        "fetch_attempts": sum(row["content_free_receipt"]["fetch_attempt_count"] for row in rows),
        "usable_pages": sum(row["content_free_receipt"]["usable_page_count"] for row in rows),
        "control_evidence_characters": sum(row["evidence_characters"][contract.CONTROL_ARM] for row in rows),
        "candidate_evidence_characters": sum(row["evidence_characters"][contract.CANDIDATE_ARM] for row in rows),
    }
    value = contract.seal(
        {
            "artifact_version": 1,
            "role": "v24983_late_page_external_forward_result",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
            "task_results_sha256": contract.sha256(ROOT / contract.TASK_RESULTS),
            "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
            "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
            "execution_start_payload_sha256": start["execution_start_payload_sha256"],
            "aggregate": aggregate,
            "all_predictions_terminal_before_gold_fetch_or_quality_decision": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "authorization": {
                "forward_audit": True,
                "evaluator": False,
                "public_exact220_or_sota": False,
                "retry_resume_selective_rerun": False,
            },
        },
        "result_payload_sha256",
    )
    _publish_json(ROOT / contract.FORWARD_RESULT, value)
    return value


def main() -> None:
    value = run_forward()
    print(json.dumps({"path": str(contract.FORWARD_RESULT), "aggregate": value["aggregate"], "wall_seconds": value["wall_seconds"]}, sort_keys=True))


if __name__ == "__main__":
    main()
