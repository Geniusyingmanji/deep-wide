#!/usr/bin/env python3
"""Run the single authorized V2.51.30 label-blind exact-220 forward."""

from __future__ import annotations

import fcntl
import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25127_causally_coupled_target_record_runtime as runtime  # noqa: E402
from deepwide_agent import v25130_causal_salience_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from deepwide_agent.v24468_total_wall_transport import (  # noqa: E402
    HardTotalWallResponsesClient,
)
from deepwide_agent.v24985_robust_late_page_fetch import (  # noqa: E402
    RobustLatePageBoundSearchClient,
    validate_search_class,
)
from scripts import run_v25129_causal_salience_external as engine  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


def _read(path: Path) -> dict[str, Any]:
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.51.30 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.51.30 expected JSON object")
    return value


def _publish_json(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _publish_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _atomic_progress(completed: int) -> None:
    value = contract.seal(
        {
            "artifact_version": 1,
            "role": contract.PROGRESS_ROLE,
            "created_at_unix": int(time.time()),
            "selected": contract.SELECTED_COUNT,
            "completed": int(completed),
            "unfinished": contract.SELECTED_COUNT - int(completed),
            "contains_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        },
        "progress_payload_sha256",
    )
    path = ROOT / contract.SAFE_PROGRESS
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _clean_pushed() -> None:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(
        ROOT, "rev-parse", "HEAD"
    ) != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.51.30 forward requires clean pushed HEAD")


def _lease_inactive() -> bool:
    path = ROOT / contract.LEASE_PATH
    if path.is_symlink():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def _active_conflicts() -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    markers = (contract.RUNNER_MARKER, "scripts/run_official_eval_local.py")
    output: list[int] = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if (
            len(parts) >= 3
            and int(parts[0]) != os.getpid()
            and "python" in parts[1].casefold()
            and any(marker in parts[2] for marker in markers)
        ):
            output.append(int(parts[0]))
    return sorted(output)


def _validate_start() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = contract.validate_protocol(ROOT, _read(ROOT / contract.PROTOCOL))
    start = _read(ROOT / contract.EXECUTION_START)
    expected_authorization = {
        "single_exact220_forward": True,
        "postfreeze_official_evaluator": False,
        "retry_resume_skip_or_selective_rerun": False,
        "leaderboard_or_sota": False,
    }
    if (
        start.get("role") != contract.START_ROLE
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or start.get("status") != "authorized_not_started"
        or start.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256")
        != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("selected") != contract.SELECTED_COUNT
        or start.get("executor_concurrency") != contract.EXECUTOR_CONCURRENCY
        or start.get("model_slot_cap") != contract.MODEL_SLOT_CAP
        or start.get("runtime_input_contract") != ["opaque_id", "question"]
        or start.get("protected_watchers") != contract.protected_watcher_snapshot()
        or start.get("findings") != []
        or start.get("authorization") != expected_authorization
        or not contract.sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.51.30 execution start drifted")
    return protocol, start


def _prepare_output() -> None:
    root = ROOT / contract.OUTPUT_ROOT
    root.mkdir(parents=True, mode=0o700, exist_ok=False)
    slots = ROOT / contract.MODEL_SLOT_DIRECTORY
    slots.mkdir(mode=0o700)
    for index in range(1, contract.MODEL_SLOT_CAP + 1):
        _publish_json(
            slots / f"slot_{index:02d}.lock",
            {
                "artifact_version": 1,
                "role": contract.SLOT_ROLE,
                "slot": index,
                "slot_cap": contract.MODEL_SLOT_CAP,
                "contains_credential_or_benchmark_content": False,
            },
        )


def _search(question: str, deadline: float) -> RobustLatePageBoundSearchClient:
    return engine._EffectAccountingSearchClient(
        contract.SEARCH["proxy_url"],
        contract.SEARCH["model"],
        visible_question=question,
        reasoning_effort=contract.MODEL["reasoning_effort"],
        service_tier=contract.MODEL["service_tier"],
        timeout=contract.SEARCH["timeout_seconds"],
        max_retries=contract.SEARCH["max_retries"],
        absolute_deadline=deadline,
        cleanup_reserve_seconds=contract.CLEANUP_RESERVE_SECONDS,
        minimum_attempt_seconds=contract.MINIMUM_MODEL_ATTEMPT_SECONDS,
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


def run_one_task(
    task: Mapping[str, str], arm_order: Sequence[str]
) -> dict[str, Any]:
    if set(task) != {"opaque_id", "question"}:
        raise ValueError("V2.51.30 runtime input must be opaque_id and question")
    started = time.monotonic()
    model: Any = None
    searches: dict[str, Any] = {}
    try:
        deadline = started + float(contract.LIMITS["wall_seconds"])
        inner = HardTotalWallResponsesClient(
            contract.MODEL["proxy_url"],
            contract.MODEL["name"],
            reasoning_effort=contract.MODEL["reasoning_effort"],
            service_tier=contract.MODEL["service_tier"],
            timeout=contract.MODEL["timeout_seconds"],
            max_retries=contract.MODEL["max_retries"],
            absolute_deadline=deadline,
            cleanup_reserve_seconds=contract.CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=contract.MINIMUM_MODEL_ATTEMPT_SECONDS,
            stage_callback=lambda _event: None,
        )
        model = engine._EffectAccountingModelSlotLimiter(
            inner,
            slot_directory=ROOT / contract.MODEL_SLOT_DIRECTORY,
            output_root=ROOT / contract.OUTPUT_ROOT,
            slot_cap=contract.MODEL_SLOT_CAP,
            pool_id=POOL_ID,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=contract.CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=contract.MINIMUM_MODEL_ATTEMPT_SECONDS,
        )
        searches = {
            phase: _search(str(task["question"]), deadline)
            for phase in runtime.PHASES
        }
        result = runtime.run_paired_task(
            task,
            model=model,
            searches=searches,
            limits=ScoreFirstLimits(**contract.LIMITS),
            arm_order=arm_order,
            monotonic=time.monotonic,
        )
        row = engine._from_runtime(
            task,
            arm_order,
            result,
            engine._health_snapshot(model, searches),
            engine._actual_effect_snapshot(model, searches),
        )
    except BaseException as exc:
        row = engine._terminal_outer_failure(
            task,
            arm_order,
            exc,
            time.monotonic() - started,
            engine._health_snapshot(model, searches),
            engine._actual_effect_snapshot(model, searches),
        )
    # V2.51.29 validates the full causal envelope. Protocol and role are then
    # projected to this exact-220 namespace and resealed without changing any
    # runtime receipt or prediction.
    row = engine.validate_task_row(row)
    projected = dict(row)
    projected["role"] = "v25130_causal_salience_exact220_task_result"
    projected["protocol_id"] = contract.PROTOCOL_ID
    projected.pop("result_payload_sha256")
    return contract.seal(projected, "result_payload_sha256")


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v25130_causal_salience_exact220_task_result"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.51.30 task envelope drifted")
    projected = dict(copied)
    projected["role"] = engine.TASK_ROLE
    projected["protocol_id"] = engine.contract.PROTOCOL_ID
    projected.pop("result_payload_sha256")
    projected = engine.contract.seal(projected, "result_payload_sha256")
    engine.validate_task_row(projected)
    return copied


def _aggregate(rows: Sequence[Mapping[str, Any]], wall: float) -> dict[str, Any]:
    checked = [validate_task_row(row) for row in rows]
    completed = [row for row in checked if row["runtime_completed"]]
    receipts = [row["content_free_receipt"] for row in completed]
    couplings = [row["causal_coupling_receipt"] for row in completed]
    saliences = [row["prompt_salience_receipt"] for row in couplings]
    effects = [row["actual_effect_snapshot"] for row in checked]
    value = {
        "artifact_version": 1,
        "role": contract.SUMMARY_ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "selected": contract.SELECTED_COUNT,
        "completed": len(checked),
        "runtime_completed": len(completed),
        "failure_as_zero_tasks": sum(row["failure_as_zero"] for row in checked),
        "model_generated_tables": sum(
            row["model_success"][contract.CANDIDATE_ARM] for row in checked
        ),
        "fallback_tables": sum(
            not row["model_success"][contract.CANDIDATE_ARM] for row in checked
        ),
        "both_arms_model_success_tasks": sum(
            all(row["model_success"].values()) for row in checked
        ),
        "grounded_plan_strategy_applied_tasks": sum(
            receipt["grounded_plan_strategy_applied"] for receipt in receipts
        ),
        "selection_changed_tasks": sum(
            receipt["selection_changed"] for receipt in receipts
        ),
        "positive_target_field_page_gain_tasks": sum(
            receipt["target_field_page_gain"] > 0 for receipt in receipts
        ),
        "retrieval_mechanism_engaged_tasks": sum(
            receipt["retrieval_mechanism_engaged"] for receipt in receipts
        ),
        "prediction_changed_tasks": sum(row["prediction_changed"] for row in checked),
        "attributable_prediction_changed_tasks": sum(
            receipt["attributable_prediction_change"] for receipt in receipts
        ),
        "unattributable_prediction_changed_tasks": sum(
            row["prediction_changed"]
            and not row["content_free_receipt"]["attributable_prediction_change"]
            for row in completed
        ),
        "prediction_identity_handoff_tasks": sum(
            receipt["prediction_identity_handoff_applied"] for receipt in couplings
        ),
        "identity_handoff_prediction_changed_tasks": sum(
            receipt["prediction_identity_handoff_applied"]
            and receipt["projected_prediction_changed"]
            for receipt in couplings
        ),
        "causal_identity_partition_valid_tasks": sum(
            receipt["prediction_identity_handoff_applied"]
            is (not receipt["retrieval_mechanism_engaged"])
            for receipt in couplings
        ),
        "causal_coupling_receipt_valid_tasks": len(couplings),
        "grounded_prompt_checklist_tasks": sum(
            receipt["grounded_prompt_checklist_count"] == 1
            for receipt in saliences
        ),
        "paired_synthesis_salience_tasks": sum(
            receipt["synthesis_prompt_count"] == 2 for receipt in saliences
        ),
        "prompt_length_preserved_tasks": sum(
            receipt["synthesis_prompt_character_counts_unchanged"]
            for receipt in saliences
        ),
        "physical_query_count": sum(
            receipt["physical_query_count"] for receipt in receipts
        ),
        "physical_fetch_count": sum(
            receipt["physical_fetch_count"] for receipt in receipts
        ),
        "physical_model_logical_call_count": sum(
            receipt["physical_model_logical_call_count"] for receipt in receipts
        ),
        "model_provider_request_count": sum(
            receipt["model_provider_request_count"] for receipt in receipts
        ),
        "observed_model_logical_requests": sum(
            effect["model_logical_requests"] for effect in effects
        ),
        "observed_logical_queries": sum(effect["logical_queries"] for effect in effects),
        "observed_fetch_requests": sum(effect["fetch_requests"] for effect in effects),
        "system_total_tokens": sum(
            int(row["cost"]["system_total_tokens"]) for row in completed
        ),
        "task_wall_sum_seconds": round(
            sum(float(row["elapsed_seconds"]) for row in checked), 6
        ),
        "forward_wall_seconds": round(max(0.0, wall), 6),
        "all_tasks_within_resource_caps": all(
            receipt["physical_query_count"] <= 4
            and receipt["physical_fetch_count"] <= 14
            and receipt["physical_model_logical_call_count"] <= 4
            and receipt["arm_metrics"][contract.CANDIDATE_ARM][
                "evidence_characters"
            ]
            <= 60_000
            for receipt in receipts
        ),
        "causal_invariants_hold": bool(
            len(checked) == contract.SELECTED_COUNT
            and len(completed) == contract.SELECTED_COUNT
            and len(couplings) == contract.SELECTED_COUNT
            and sum(
                receipt["prediction_identity_handoff_applied"]
                is (not receipt["retrieval_mechanism_engaged"])
                for receipt in couplings
            )
            == contract.SELECTED_COUNT
            and not any(row["prediction_changed"] and not row["content_free_receipt"]["attributable_prediction_change"] for row in completed)
            and not any(receipt["prediction_identity_handoff_applied"] and receipt["projected_prediction_changed"] for receipt in couplings)
        ),
        "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "official_evaluator_called": False,
    }
    return contract.seal(value, "summary_payload_sha256")


def main() -> None:
    _clean_pushed()
    protocol, start = _validate_start()
    if not _lease_inactive() or _active_conflicts():
        raise RuntimeError("V2.51.30 shared runtime is not ready")
    with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
        pass
    future = (
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.EVALUATOR_PROTOCOL,
        contract.RESULT,
        contract.POSTAUDIT,
        contract.OUTPUT_ROOT,
    )
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.51.30 forward surface is not pristine")
    if protocol["execution"]["protected_watchers"] != contract.protected_watcher_snapshot():
        raise RuntimeError("V2.51.30 protected watcher identity drifted")
    validate_search_class()
    tasks = contract.task_vector(ROOT, protocol)
    orders = contract.arm_order_vector()
    _prepare_output()
    started = time.monotonic()
    results: list[dict[str, Any] | None] = [None] * contract.SELECTED_COUNT
    with acquire_deepwide_api_lease(
        ROOT,
        owner=contract.LEASE_OWNER,
        purpose=contract.LEASE_PURPOSE,
        path=ROOT / contract.LEASE_PATH,
    ):
        with ThreadPoolExecutor(max_workers=contract.EXECUTOR_CONCURRENCY) as pool:
            futures = {
                pool.submit(run_one_task, task, orders[index]): index
                for index, task in enumerate(tasks)
            }
            completed = 0
            for future in as_completed(futures):
                index = futures[future]
                results[index] = validate_task_row(future.result())
                completed += 1
                _atomic_progress(completed)
    rows = [validate_task_row(row) for row in results if row is not None]
    if (
        len(rows) != contract.SELECTED_COUNT
        or [row["opaque_id"] for row in rows]
        != [task["opaque_id"] for task in tasks]
    ):
        raise RuntimeError("V2.51.30 exact-220 terminal denominator drifted")
    wall = time.monotonic() - started
    _publish_jsonl(ROOT / contract.RUNTIME_RESULTS, rows)
    _publish_jsonl(
        ROOT / contract.TASK_RECEIPTS,
        [
            {
                "opaque_id": row["opaque_id"],
                "content_free_receipt": row["content_free_receipt"],
                "causal_coupling_receipt": row["causal_coupling_receipt"],
                "stage_failure_accounting": row["stage_failure_accounting"],
                "actual_effect_snapshot": row["actual_effect_snapshot"],
            }
            for row in rows
        ],
    )
    prediction_rows = [
        {
            "opaque_id": row["opaque_id"],
            "status": "completed",
            "prediction": row["predictions"][contract.CANDIDATE_ARM],
            "prediction_sha256": row["prediction_sha256"][contract.CANDIDATE_ARM],
            "completion_kind": (
                "model_generated"
                if row["model_success"][contract.CANDIDATE_ARM]
                else "best_effort_fallback"
            ),
            "elapsed_seconds": row["elapsed_seconds"],
            "cost": row["cost"],
            "label_blind": True,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
        }
        for row in rows
    ]
    _publish_jsonl(ROOT / contract.RUNTIME_PREDICTIONS, prediction_rows)
    summary = _aggregate(rows, wall)
    _publish_json(ROOT / contract.RUN_SUMMARY, summary)
    freeze = contract.seal(
        {
            "artifact_version": 1,
            "role": contract.FREEZE_ROLE,
            "protocol_id": contract.PROTOCOL_ID,
            "selected": contract.SELECTED_COUNT,
            "terminal": contract.SELECTED_COUNT,
            "runtime_results_sha256": contract.sha256(ROOT / contract.RUNTIME_RESULTS),
            "content_free_task_receipts_sha256": contract.sha256(
                ROOT / contract.TASK_RECEIPTS
            ),
            "runtime_predictions_sha256": contract.sha256(
                ROOT / contract.RUNTIME_PREDICTIONS
            ),
            "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
            "prediction_hashes_sha256": contract.payload_sha256(
                [row["prediction_sha256"] for row in prediction_rows]
            ),
            "all_220_predictions_terminal_before_mapping_query_answer_or_evaluator_open": True,
            "mapping_gold_or_evaluator_opened_or_hashed": False,
            "label_blind": True,
        },
        "freeze_payload_sha256",
    )
    _publish_json(ROOT / contract.PREDICTION_FREEZE, freeze)
    forward = contract.seal(
        {
            "artifact_version": 1,
            "role": contract.FORWARD_ROLE,
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "selected": contract.SELECTED_COUNT,
            "terminal_predictions": contract.SELECTED_COUNT,
            "model_generated_tables": summary["model_generated_tables"],
            "fallback_tables": summary["fallback_tables"],
            "system_total_tokens": summary["system_total_tokens"],
            "forward_wall_seconds": summary["forward_wall_seconds"],
            "retrieval_mechanism_engaged_tasks": summary[
                "retrieval_mechanism_engaged_tasks"
            ],
            "attributable_prediction_changed_tasks": summary[
                "attributable_prediction_changed_tasks"
            ],
            "unattributable_prediction_changed_tasks": summary[
                "unattributable_prediction_changed_tasks"
            ],
            "causal_invariants_hold": summary["causal_invariants_hold"],
            "all_tasks_within_resource_caps": summary[
                "all_tasks_within_resource_caps"
            ],
            "prediction_freeze_sha256": contract.sha256(
                ROOT / contract.PREDICTION_FREEZE
            ),
            "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
            "runtime_results_sha256": contract.sha256(ROOT / contract.RUNTIME_RESULTS),
            "execution_start_sha256": contract.sha256(
                ROOT / contract.EXECUTION_START
            ),
            "execution_start_payload_sha256": start[
                "execution_start_payload_sha256"
            ],
            "all_220_predictions_terminal_before_mapping_query_answer_or_evaluator_open": True,
            "mapping_gold_category_question_type_split_answer_evaluator_score_reward_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "official_evaluator_called": False,
            "retry_resume_skip_or_selective_rerun_launched": False,
        },
        "result_payload_sha256",
    )
    _publish_json(ROOT / contract.FORWARD_RESULT, forward)
    _atomic_progress(contract.SELECTED_COUNT)
    print(
        json.dumps(
            {
                "terminal": contract.SELECTED_COUNT,
                "wall_seconds": summary["forward_wall_seconds"],
                "model_generated_tables": summary["model_generated_tables"],
                "fallback_tables": summary["fallback_tables"],
                "retrieval_mechanism_engaged_tasks": summary[
                    "retrieval_mechanism_engaged_tasks"
                ],
                "attributable_prediction_changed_tasks": summary[
                    "attributable_prediction_changed_tasks"
                ],
                "forward_result": str(contract.FORWARD_RESULT),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
