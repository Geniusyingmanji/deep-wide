#!/usr/bin/env python3
"""Run the single authorized V2.51.13 schema-recovered external forward."""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25111_schema_recovered_paired_runtime as runtime  # noqa: E402
from deepwide_agent import v25113_schema_recovered_external_contract as contract  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from deepwide_agent.v24468_total_wall_transport import HardTotalWallResponsesClient  # noqa: E402
from deepwide_agent.v24985_robust_late_page_fetch import (  # noqa: E402
    RobustLatePageBoundSearchClient,
    validate_search_class,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


TASK_ROLE = "v25113_schema_recovered_external_task_result"


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.51.13 expected JSON object")
    return value


def _read_jsonl(relative: Path, *, tracked: bool = False) -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.51.13 expected JSONL objects")
    return rows


def _publish_json(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _publish_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
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
        raise RuntimeError("V2.51.13 requires clean pushed HEAD")


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
    markers = (
        str(contract.RUNNER),
        str(contract.EVALUATOR),
        "scripts/run_official_eval_local.py",
    )
    output: list[int] = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if (
            len(parts) == 3
            and int(parts[0]) != os.getpid()
            and "python" in parts[1].casefold()
            and any(marker in parts[2] for marker in markers)
        ):
            output.append(int(parts[0]))
    return sorted(output)


def _validate_start() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    start = _read(contract.EXECUTION_START)
    if (
        start.get("role") != "v25113_schema_recovered_external_execution_start"
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or start.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256")
        != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("task_vector_sha256")
        != protocol["population"]["task_vector_sha256"]
        or start.get("arm_order_vector_sha256")
        != protocol["population"]["arm_order_vector_sha256"]
        or start.get("protected_watchers") != contract.watcher_snapshot()
        or start.get("authorization")
        != {
            "one_external_forward": True,
            "evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_rerun": False,
        }
        or not contract.sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.51.13 execution start drifted")
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
                "role": "v25113_model_slot",
                "slot": index,
                "slot_cap": contract.MODEL_SLOT_CAP,
                "contains_credential_or_benchmark_content": False,
            },
        )


def _search(question: str, deadline: float) -> RobustLatePageBoundSearchClient:
    return RobustLatePageBoundSearchClient(
        contract.SEARCH["proxy_url"],
        contract.SEARCH["model"],
        visible_question=question,
        reasoning_effort=contract.SEARCH["reasoning_effort"],
        service_tier=contract.SEARCH["service_tier"],
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


_HEALTH_NAMES = (
    "model_request_failures",
    "model_hard_total_wall_timeouts",
    "search_transport_failures",
    "search_hard_total_wall_timeouts",
    "fetch_helper_failures",
    "fetch_hard_deadline_failures",
    "fetch_deadline_rejections",
    "query_local_mapping_failure_rows",
)


def _health(value: Mapping[str, int] | None = None) -> dict[str, int]:
    source = dict(value or {})
    output = {name: int(source.get(name, 0)) for name in _HEALTH_NAMES}
    if any(item < 0 for item in output.values()):
        raise ValueError("V2.51.13 health drifted")
    return output


def _health_snapshot(model: Any, searches: Mapping[str, Any]) -> dict[str, int]:
    def count(value: Any, name: str) -> int:
        observed = getattr(value, name, 0) if value is not None else 0
        return (
            int(observed)
            if isinstance(observed, int) and not isinstance(observed, bool)
            else 0
        )

    clients = list(searches.values())
    return _health(
        {
            "model_request_failures": count(model, "failures"),
            "model_hard_total_wall_timeouts": count(model, "hard_total_wall_timeouts"),
            "search_transport_failures": sum(
                count(client, "transport_failures") for client in clients
            ),
            "search_hard_total_wall_timeouts": sum(
                count(client, "hard_total_wall_timeouts") for client in clients
            ),
            "fetch_helper_failures": sum(
                count(client, "fetch_helper_failures") for client in clients
            ),
            "fetch_hard_deadline_failures": sum(
                count(client, "hard_fetch_deadline_failures") for client in clients
            ),
            "fetch_deadline_rejections": sum(
                count(client, "fetch_deadline_rejections") for client in clients
            ),
            "query_local_mapping_failure_rows": sum(
                count(client, "failures") for client in clients
            ),
        }
    )


def _fallback_table() -> str:
    return (
        "```markdown\n| "
        + " | ".join(contract.COLUMNS)
        + " |\n|"
        + "|".join("---" for _ in contract.COLUMNS)
        + "|\n| "
        + " | ".join("Unknown" for _ in contract.COLUMNS)
        + " |\n```"
    )


def _terminal_outer_failure(
    task: Mapping[str, str],
    arm_order: Sequence[str],
    exc: BaseException,
    elapsed: float,
    health: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    fallback = _fallback_table()
    row = {
        "artifact_version": 1,
        "role": TASK_ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "opaque_id": str(task["opaque_id"]),
        "runtime_input_keys": ["opaque_id", "question", "same_forward_public_pages"],
        "terminal": True,
        "runtime_completed": False,
        "failure_as_zero": True,
        "outer_failure_type": (type(exc).__name__ or "Exception")[:128],
        "arm_order": list(arm_order),
        "model_success": {arm: False for arm in contract.ARMS},
        "normalizer_status": {arm: "not_attempted" for arm in contract.ARMS},
        "predictions": {arm: fallback for arm in contract.ARMS},
        "prediction_sha256": {
            arm: hashlib.sha256(fallback.encode()).hexdigest() for arm in contract.ARMS
        },
        "prediction_changed": False,
        "candidate_evidence_changed": False,
        "content_free_receipt": None,
        "stage_failure_accounting": None,
        "runtime_result_payload_sha256": None,
        "cost": None,
        "failure_types": None,
        "post_synthesis_accounting_or_receipt_validation_failed": False,
        "effect_health": _health(health),
        "elapsed_seconds": round(max(0.0, float(elapsed)), 6),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "retry_resume_skip_population_replacement_or_selective_rerun": False,
        "contains_question_query_url_title_page_quote_anchor_identity_field_value_answer_or_credential": False,
    }
    return contract.seal(row, "result_payload_sha256")


def _from_runtime(
    task: Mapping[str, str],
    arm_order: Sequence[str],
    value: Mapping[str, Any],
    health: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    checked = runtime.validate_result(value)
    if checked["opaque_id"] != task["opaque_id"]:
        raise RuntimeError("V2.51.13 task identity drifted")
    accounting_failed = checked["status"] == "terminal_accounting_failure"
    stage = runtime.validate_stage_receipt(checked["stage_failure_accounting"])
    row = {
        "artifact_version": 1,
        "role": TASK_ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "opaque_id": checked["opaque_id"],
        "runtime_input_keys": ["opaque_id", "question", "same_forward_public_pages"],
        "terminal": True,
        "runtime_completed": not accounting_failed,
        "failure_as_zero": accounting_failed,
        "outer_failure_type": None,
        "arm_order": list(arm_order),
        "model_success": copy.deepcopy(checked["model_success"]),
        "normalizer_status": copy.deepcopy(checked["normalizer_status"]),
        "predictions": copy.deepcopy(checked["predictions"]),
        "prediction_sha256": copy.deepcopy(checked["prediction_sha256"]),
        "prediction_changed": bool(checked["prediction_changed"]),
        "candidate_evidence_changed": bool(checked["candidate_evidence_changed"]),
        "content_free_receipt": copy.deepcopy(checked["content_free_receipt"]),
        "stage_failure_accounting": copy.deepcopy(stage),
        "runtime_result_payload_sha256": str(checked["result_payload_sha256"]),
        "cost": copy.deepcopy(checked["cost"]),
        "failure_types": copy.deepcopy(checked["failure_types"]),
        "post_synthesis_accounting_or_receipt_validation_failed": accounting_failed,
        "effect_health": _health(health),
        "elapsed_seconds": float(checked["elapsed_seconds"]),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "retry_resume_skip_population_replacement_or_selective_rerun": False,
        "contains_question_query_url_title_page_quote_anchor_identity_field_value_answer_or_credential": False,
    }
    return contract.seal(row, "result_payload_sha256")


def _reconstruct_runtime(copied: Mapping[str, Any]) -> dict[str, Any]:
    accounting = copied["post_synthesis_accounting_or_receipt_validation_failed"]
    value = {
        "artifact_version": 1,
        "role": runtime.ROLE,
        "policy_id": runtime.POLICY_ID,
        "opaque_id": copied["opaque_id"],
        "status": "terminal_accounting_failure" if accounting else "terminal",
        "predictions": copy.deepcopy(copied["predictions"]),
        "prediction_sha256": copy.deepcopy(copied["prediction_sha256"]),
        "model_success": copy.deepcopy(copied["model_success"]),
        "normalizer_status": copy.deepcopy(copied["normalizer_status"]),
        "prediction_changed": copied["prediction_changed"],
        "candidate_evidence_changed": copied["candidate_evidence_changed"],
        "failure_types": copy.deepcopy(copied["failure_types"]),
        "elapsed_seconds": copied["elapsed_seconds"],
        "cost": copy.deepcopy(copied["cost"]),
        "content_free_receipt": copy.deepcopy(copied["content_free_receipt"]),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
        "stage_failure_accounting": copy.deepcopy(copied["stage_failure_accounting"]),
        "result_payload_sha256": copied["runtime_result_payload_sha256"],
    }
    if accounting:
        value["post_synthesis_accounting_or_receipt_validation_failed"] = True
    return value


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = {
        "artifact_version",
        "role",
        "protocol_id",
        "opaque_id",
        "runtime_input_keys",
        "terminal",
        "runtime_completed",
        "failure_as_zero",
        "outer_failure_type",
        "arm_order",
        "model_success",
        "normalizer_status",
        "predictions",
        "prediction_sha256",
        "prediction_changed",
        "candidate_evidence_changed",
        "content_free_receipt",
        "stage_failure_accounting",
        "runtime_result_payload_sha256",
        "cost",
        "failure_types",
        "post_synthesis_accounting_or_receipt_validation_failed",
        "effect_health",
        "elapsed_seconds",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "retry_resume_skip_population_replacement_or_selective_rerun",
        "contains_question_query_url_title_page_quote_anchor_identity_field_value_answer_or_credential",
        "result_payload_sha256",
    }
    predictions = copied.get("predictions") or {}
    hashes = copied.get("prediction_sha256") or {}
    successes = copied.get("model_success") or {}
    normalizers = copied.get("normalizer_status") or {}
    health = copied.get("effect_health") or {}
    completed = copied.get("runtime_completed") is True
    accounting = copied.get("post_synthesis_accounting_or_receipt_validation_failed")
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != TASK_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("runtime_input_keys")
        != ["opaque_id", "question", "same_forward_public_pages"]
        or copied.get("terminal") is not True
        or copied.get("failure_as_zero") is completed
        or list(copied.get("arm_order") or []) not in contract.arm_order_vector()
        or set(predictions) != set(contract.ARMS)
        or set(hashes) != set(contract.ARMS)
        or set(successes) != set(contract.ARMS)
        or set(normalizers) != set(contract.ARMS)
        or set(health) != set(_HEALTH_NAMES)
        or any(
            isinstance(item, bool) or not isinstance(item, int) or item < 0
            for item in health.values()
        )
        or any(
            not isinstance(predictions[arm], str) or not predictions[arm]
            for arm in contract.ARMS
        )
        or any(
            hashes[arm] != hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in contract.ARMS
        )
        or copied.get("prediction_changed")
        is not (predictions[contract.CONTROL_ARM] != predictions[contract.CANDIDATE_ARM])
        or not isinstance(accounting, bool)
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "retry_resume_skip_population_replacement_or_selective_rerun",
                "contains_question_query_url_title_page_quote_anchor_identity_field_value_answer_or_credential",
            )
        )
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.51.13 task row drifted")
    if completed or accounting is True:
        if (
            copied.get("outer_failure_type") is not None
            or not isinstance(copied.get("stage_failure_accounting"), Mapping)
            or not isinstance(copied.get("runtime_result_payload_sha256"), str)
            or len(copied["runtime_result_payload_sha256"]) != 64
            or runtime.validate_result(_reconstruct_runtime(copied))["opaque_id"]
            != copied["opaque_id"]
        ):
            raise RuntimeError("V2.51.13 bound runtime row drifted")
        if completed and accounting is not False:
            raise RuntimeError("V2.51.13 completed accounting state drifted")
        if accounting and (
            completed
            or copied.get("cost") is not None
            or copied.get("failure_types") is not None
            or any(successes.values())
            or copied.get("prediction_changed") is not False
            or copied.get("candidate_evidence_changed") is not False
        ):
            raise RuntimeError("V2.51.13 accounting failure row drifted")
    elif (
        not isinstance(copied.get("outer_failure_type"), str)
        or copied.get("content_free_receipt") is not None
        or copied.get("stage_failure_accounting") is not None
        or copied.get("runtime_result_payload_sha256") is not None
        or copied.get("cost") is not None
        or copied.get("failure_types") is not None
        or any(successes.values())
        or copied.get("prediction_changed") is not False
        or copied.get("candidate_evidence_changed") is not False
        or accounting is not False
    ):
        raise RuntimeError("V2.51.13 outer failure row drifted")
    return copied


def run_one_task(task: Mapping[str, str], arm_order: Sequence[str]) -> dict[str, Any]:
    if set(task) != {"opaque_id", "question"}:
        raise ValueError("V2.51.13 runtime input must be opaque_id and question")
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
        model = DeadlineAwareGlobalModelSlotLimiter(
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
            phase: _search(str(task["question"]), deadline) for phase in runtime.PHASES
        }
        result = runtime.run_paired_task(
            task,
            model=model,
            searches=searches,
            limits=ScoreFirstLimits(**contract.LIMITS),
            arm_order=arm_order,
            monotonic=time.monotonic,
        )
        row = _from_runtime(task, arm_order, result, _health_snapshot(model, searches))
    except BaseException as exc:
        row = _terminal_outer_failure(
            task,
            arm_order,
            exc,
            time.monotonic() - started,
            _health_snapshot(model, searches),
        )
    return validate_task_row(row)


def _row_effect_counts(row: Mapping[str, Any]) -> dict[str, int]:
    health = row["effect_health"]
    terminal_hard = sum(
        health[name] for name in _HEALTH_NAMES if name != "query_local_mapping_failure_rows"
    )
    if not row["runtime_completed"]:
        accounting_failed = bool(
            row["post_synthesis_accounting_or_receipt_validation_failed"]
        )
        return {
            "outer": int(not accounting_failed),
            "accounting": int(accounting_failed),
            "terminal_hard": terminal_hard,
            "query_local_coverage_failure_rows": health[
                "query_local_mapping_failure_rows"
            ],
            "control_model": 0,
            "candidate_model": 0,
            "usable_pages": 0,
        }
    return {
        "outer": 0,
        "accounting": 0,
        "terminal_hard": terminal_hard,
        "query_local_coverage_failure_rows": health["query_local_mapping_failure_rows"],
        "control_model": int(row["failure_types"][contract.CONTROL_ARM] is not None),
        "candidate_model": int(
            row["failure_types"][contract.CANDIDATE_ARM] is not None
        ),
        "usable_pages": int(row["content_free_receipt"]["usable_page_count"]),
    }


def aggregate_rows(
    rows: Sequence[Mapping[str, Any]], *, wall_seconds: float
) -> dict[str, Any]:
    checked = [validate_task_row(row) for row in rows]
    if (
        len(checked) != contract.TASK_COUNT
        or [row["opaque_id"] for row in checked]
        != [task["opaque_id"] for task in contract.task_vector()]
        or [row["arm_order"] for row in checked] != contract.arm_order_vector()
    ):
        raise RuntimeError("V2.51.13 fixed task vector drifted")
    effects = [_row_effect_counts(row) for row in checked]
    completed = [row for row in checked if row["runtime_completed"]]
    receipts = [row["content_free_receipt"] for row in completed]
    stages = [row["stage_failure_accounting"] for row in completed]
    return {
        "task_count": contract.TASK_COUNT,
        "terminal_tasks": len(checked),
        "completed_runtime_tasks": len(completed),
        "failure_as_zero_tasks": sum(row["failure_as_zero"] for row in checked),
        "both_arms_model_success_tasks": sum(
            all(row["model_success"].values()) for row in checked
        ),
        "tasks_with_usable_page": sum(value["usable_pages"] > 0 for value in effects),
        "verifier_exposure_tasks": sum(
            row["candidate_evidence_changed"] for row in checked
        ),
        "prediction_changed_tasks": sum(row["prediction_changed"] for row in checked),
        "exposed_and_prediction_changed_tasks": sum(
            row["candidate_evidence_changed"] and row["prediction_changed"]
            for row in checked
        ),
        "unexposed_and_prediction_changed_tasks": sum(
            not row["candidate_evidence_changed"] and row["prediction_changed"]
            for row in checked
        ),
        "plan_model_effect_failure_tasks": sum(
            stage["plan_model_effect_failed"] for stage in stages
        ),
        "plan_transport_failure_tasks": sum(
            stage["plan_transport_failed"] for stage in stages
        ),
        "plan_output_validation_failure_tasks": sum(
            stage["plan_output_validation_failed"] for stage in stages
        ),
        "proposal_model_effect_failure_tasks": sum(
            stage["proposal_model_effect_failed"] for stage in stages
        ),
        "proposal_transport_failure_tasks": sum(
            stage["proposal_transport_failed"] for stage in stages
        ),
        "representation_validation_failure_tasks": sum(
            stage["representation_validation_failed"] for stage in stages
        ),
        "post_synthesis_accounting_or_receipt_validation_failure_tasks": sum(
            value["accounting"] for value in effects
        ),
        "planned_queries": sum(receipt["planned_query_count"] for receipt in receipts),
        "physical_queries": sum(receipt["physical_query_count"] for receipt in receipts),
        "physical_fetches": sum(receipt["physical_fetch_count"] for receipt in receipts),
        "physical_model_logical_calls": sum(
            receipt["physical_model_logical_call_count"] for receipt in receipts
        ),
        "model_provider_requests": sum(
            receipt["model_provider_request_count"] for receipt in receipts
        ),
        "model_provider_attempts": sum(
            receipt["model_provider_attempt_count"] for receipt in receipts
        ),
        "control_effective_model_logical_calls": sum(
            receipt["arm_metrics"][contract.CONTROL_ARM][
                "effective_model_logical_call_count"
            ]
            for receipt in receipts
        ),
        "candidate_effective_model_logical_calls": sum(
            receipt["arm_metrics"][contract.CANDIDATE_ARM][
                "effective_model_logical_call_count"
            ]
            for receipt in receipts
        ),
        "control_evidence_characters": sum(
            receipt["control_evidence_characters"] for receipt in receipts
        ),
        "candidate_evidence_characters": sum(
            receipt["candidate_evidence_characters"] for receipt in receipts
        ),
        "outer_hard_failures": sum(value["outer"] for value in effects),
        "terminal_transport_timeout_helper_or_model_hard_failures": sum(
            value["terminal_hard"] for value in effects
        ),
        "query_local_mapping_failure_rows": sum(
            value["query_local_coverage_failure_rows"] for value in effects
        ),
        "control_arm_model_hard_failures": sum(
            value["control_model"] for value in effects
        ),
        "candidate_arm_model_hard_failures": sum(
            value["candidate_model"] for value in effects
        ),
        "system_total_tokens": sum(
            int(row["cost"]["system_total_tokens"]) for row in completed
        ),
        "batch_wall_seconds": round(max(0.0, float(wall_seconds)), 6),
        "contains_question_query_url_title_page_quote_anchor_identity_field_value_answer_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
    }


def mechanism_decision(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    gate = contract.mechanism_gate()
    completed = int(aggregate["completed_runtime_tasks"])
    checks = {
        "fixed_terminal_denominator": aggregate["task_count"]
        == gate["fixed_task_denominator"]
        and aggregate["terminal_tasks"] == gate["terminal_tasks"],
        "all_runtime_tasks_completed": completed == gate["completed_runtime_tasks"]
        and aggregate["failure_as_zero_tasks"] == 0,
        "both_arms_model_success": aggregate["both_arms_model_success_tasks"]
        == gate["both_arms_model_success_tasks"],
        "minimum_usable_page_tasks": aggregate["tasks_with_usable_page"]
        >= gate["minimum_tasks_with_usable_page"],
        "minimum_verifier_exposure": aggregate["verifier_exposure_tasks"]
        >= gate["minimum_verifier_exposure_tasks"],
        "minimum_prediction_change": aggregate["prediction_changed_tasks"]
        >= gate["minimum_prediction_changed_tasks"],
        "minimum_attributable_prediction_change": aggregate[
            "exposed_and_prediction_changed_tasks"
        ]
        >= gate["minimum_exposed_and_prediction_changed_tasks"],
        "zero_unexposed_prediction_change": aggregate[
            "unexposed_and_prediction_changed_tasks"
        ]
        <= gate["maximum_unexposed_and_prediction_changed_tasks"],
        "zero_plan_model_effect_failure": aggregate["plan_model_effect_failure_tasks"]
        <= gate["maximum_plan_model_effect_failures"],
        "zero_plan_transport_failure": aggregate["plan_transport_failure_tasks"]
        <= gate["maximum_plan_transport_failures"],
        "zero_plan_output_validation_failure": aggregate[
            "plan_output_validation_failure_tasks"
        ]
        <= gate["maximum_plan_output_validation_failures"],
        "zero_proposal_model_effect_failure": aggregate[
            "proposal_model_effect_failure_tasks"
        ]
        <= gate["maximum_proposal_model_effect_failures"],
        "zero_proposal_transport_failure": aggregate["proposal_transport_failure_tasks"]
        <= gate["maximum_proposal_transport_failures"],
        "zero_representation_validation_failure": aggregate[
            "representation_validation_failure_tasks"
        ]
        <= gate["maximum_representation_validation_failures"],
        "zero_post_synthesis_accounting_or_receipt_validation_failure": aggregate[
            "post_synthesis_accounting_or_receipt_validation_failure_tasks"
        ]
        <= gate["maximum_post_synthesis_accounting_or_receipt_validation_failures"],
        "exact_query_budget": aggregate["planned_queries"] == 4 * completed
        and aggregate["physical_queries"] == 4 * completed,
        "fetch_cap_preserved": aggregate["physical_fetches"] <= 10 * completed,
        "physical_model_budget_exact": aggregate["physical_model_logical_calls"]
        == 4 * completed,
        "effective_arm_model_budgets_exact_and_equal": aggregate[
            "control_effective_model_logical_calls"
        ]
        == aggregate["candidate_effective_model_logical_calls"]
        == 3 * completed,
        "evidence_lengths_equal": aggregate["control_evidence_characters"]
        == aggregate["candidate_evidence_characters"],
        "zero_terminal_effect_or_outer_hard_failure": aggregate["outer_hard_failures"]
        == 0
        and aggregate["terminal_transport_timeout_helper_or_model_hard_failures"] == 0,
        "candidate_model_failures_do_not_increase": aggregate[
            "candidate_arm_model_hard_failures"
        ]
        <= aggregate["control_arm_model_hard_failures"],
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "checks": checks,
        "failed_checks": failed,
        "mechanism_gate_passed": not failed,
        "postfreeze_external_evaluator_implementation_and_protocol": not failed,
        "query_local_mapping_failures_used_as_terminal_hard_failure": False,
        "deepwidebench_dev64_exact220_or_sota": False,
    }


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    aggregate = copied.get("aggregate")
    if (
        copied.get("role") != "v25113_schema_recovered_external_forward_result"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or not isinstance(aggregate, Mapping)
        or copied.get("mechanism_decision") != mechanism_decision(aggregate)
        or copied.get("authorization")
        != {
            "forward_audit": True,
            "postfreeze_external_evaluator_implementation_and_protocol": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_rerun": False,
        }
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.51.13 forward result drifted")
    return copied


def run_forward() -> dict[str, Any]:
    _clean_pushed()
    protocol, start = _validate_start()
    if not _lease_inactive() or _active_conflicts():
        raise RuntimeError("V2.51.13 shared runtime is not ready")
    with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
        pass
    future = (
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.EVALUATOR,
        contract.EVALUATOR_TEST,
        contract.EVALUATOR_PROTOCOL,
        contract.RESULT,
        contract.POSTAUDIT,
        contract.OUTPUT_ROOT,
    )
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.51.13 forward surface is not pristine")
    if contract.watcher_snapshot() != protocol["protected_watchers"]:
        raise RuntimeError("V2.51.13 protected watcher identity drifted")
    validate_search_class()
    tasks = contract.task_vector()
    orders = contract.arm_order_vector()
    _prepare_output()
    started = time.monotonic()
    values: list[dict[str, Any] | None] = [None] * contract.TASK_COUNT
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
            for future in as_completed(futures):
                values[futures[future]] = future.result()
    rows = [validate_task_row(row) for row in values if row is not None]
    if len(rows) != contract.TASK_COUNT:
        raise RuntimeError("V2.51.13 terminal denominator drifted")
    _publish_jsonl(ROOT / contract.TASK_ROWS, rows)
    freeze = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25113_schema_recovered_external_prediction_freeze",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "task_count": contract.TASK_COUNT,
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "prediction_hash_vector_sha256": contract.payload_sha256(
                [row["prediction_sha256"] for row in rows]
            ),
            "all_predictions_terminal_before_gold_evaluator_or_quality_decision": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        },
        "freeze_payload_sha256",
    )
    _publish_json(ROOT / contract.PREDICTION_FREEZE, freeze)
    aggregate = aggregate_rows(rows, wall_seconds=time.monotonic() - started)
    decision = mechanism_decision(aggregate)
    forward = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25113_schema_recovered_external_forward_result",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
            "execution_start_payload_sha256": start["execution_start_payload_sha256"],
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
            "aggregate": aggregate,
            "mechanism_decision": decision,
            "authorization": {
                "forward_audit": True,
                "postfreeze_external_evaluator_implementation_and_protocol": False,
                "deepwidebench_dev64_exact220_or_sota": False,
                "retry_resume_skip_population_replacement_or_selective_rerun": False,
            },
        },
        "result_payload_sha256",
    )
    _publish_json(ROOT / contract.FORWARD_RESULT, forward)
    return validate_forward_result(forward)


def main() -> None:
    value = run_forward()
    print(
        json.dumps(
            {
                "path": str(contract.FORWARD_RESULT),
                "aggregate": value["aggregate"],
                "mechanism_decision": value["mechanism_decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
