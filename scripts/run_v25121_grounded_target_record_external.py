#!/usr/bin/env python3
"""Run the single authorized V2.51.21 grounded-retrieval external forward."""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import re
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

from deepwide_agent import v25119_grounded_target_record_paired_runtime as runtime  # noqa: E402
from deepwide_agent import v25121_grounded_target_record_external_contract as contract  # noqa: E402
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
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


TASK_ROLE = "v25121_grounded_target_record_external_task_result"


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.51.21 expected JSON object")
    return value


def _read_jsonl(relative: Path, *, tracked: bool = False) -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.51.21 expected JSONL objects")
    return rows


def _publish_json(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
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
            handle.write(
                json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n"
            )
        handle.flush()
        os.fsync(handle.fileno())


def _clean_pushed() -> None:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(
        ROOT, "rev-parse", "HEAD"
    ) != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.51.21 requires clean pushed HEAD")


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
        start.get("role")
        != "v25121_grounded_target_record_external_execution_start"
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
        raise RuntimeError("V2.51.21 execution start drifted")
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
                "role": "v25121_model_slot",
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
        hard_fetch_deadline_seconds=contract.SEARCH[
            "hard_fetch_deadline_seconds"
        ],
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
)


def _health(value: Mapping[str, int] | None = None) -> dict[str, int]:
    source = dict(value or {})
    if set(source).difference(_HEALTH_NAMES) or any(
        isinstance(source.get(name, 0), bool)
        or not isinstance(source.get(name, 0), int)
        or source.get(name, 0) < 0
        for name in _HEALTH_NAMES
    ):
        raise ValueError("V2.51.21 health drifted")
    output = {name: int(source.get(name, 0)) for name in _HEALTH_NAMES}
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
            "model_hard_total_wall_timeouts": count(
                model, "hard_total_wall_timeouts"
            ),
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


_RUNTIME_FIELDS = (
    "predictions",
    "prediction_sha256",
    "model_success",
    "normalizer_status",
    "failure_types",
    "prediction_changed",
    "elapsed_seconds",
    "grounded_plan_receipt",
    "selection_receipt",
    "physical_wave_receipts",
    "physical_effects",
    "cost",
    "content_free_receipt",
)


def _terminal_outer_failure(
    task: Mapping[str, str],
    arm_order: Sequence[str],
    exc: BaseException,
    elapsed: float,
    health: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    fallback = _fallback_table()
    row: dict[str, Any] = {
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
        "predictions": {arm: fallback for arm in contract.ARMS},
        "prediction_sha256": {
            arm: hashlib.sha256(fallback.encode()).hexdigest()
            for arm in contract.ARMS
        },
        "model_success": {arm: False for arm in contract.ARMS},
        "normalizer_status": {arm: "not_attempted" for arm in contract.ARMS},
        "failure_types": None,
        "prediction_changed": False,
        "elapsed_seconds": round(max(0.0, float(elapsed)), 6),
        "grounded_plan_receipt": None,
        "selection_receipt": None,
        "physical_wave_receipts": None,
        "physical_effects": None,
        "cost": None,
        "content_free_receipt": None,
        "runtime_result_payload_sha256": None,
        "effect_health": _health(health),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "retry_resume_skip_population_replacement_or_selective_rerun": False,
        "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions": False,
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
        raise RuntimeError("V2.51.21 task identity drifted")
    row: dict[str, Any] = {
        "artifact_version": 1,
        "role": TASK_ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "opaque_id": checked["opaque_id"],
        "runtime_input_keys": ["opaque_id", "question", "same_forward_public_pages"],
        "terminal": True,
        "runtime_completed": True,
        "failure_as_zero": False,
        "outer_failure_type": None,
        "arm_order": list(arm_order),
        **{name: copy.deepcopy(checked[name]) for name in _RUNTIME_FIELDS},
        "runtime_result_payload_sha256": str(checked["result_payload_sha256"]),
        "effect_health": _health(health),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "retry_resume_skip_population_replacement_or_selective_rerun": False,
        "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions": False,
    }
    return contract.seal(row, "result_payload_sha256")


def _reconstruct_runtime(copied: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "artifact_version": 1,
        "role": runtime.ROLE,
        "policy_id": runtime.POLICY_ID,
        "opaque_id": copied["opaque_id"],
        "status": "terminal",
        **{name: copy.deepcopy(copied[name]) for name in _RUNTIME_FIELDS},
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
        "result_payload_sha256": copied["runtime_result_payload_sha256"],
    }


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
        *_RUNTIME_FIELDS,
        "runtime_result_payload_sha256",
        "effect_health",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "retry_resume_skip_population_replacement_or_selective_rerun",
        "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions",
        "result_payload_sha256",
    }
    predictions = copied.get("predictions") or {}
    hashes = copied.get("prediction_sha256") or {}
    successes = copied.get("model_success") or {}
    normalizers = copied.get("normalizer_status") or {}
    completed = copied.get("runtime_completed") is True
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != TASK_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("runtime_input_keys")
        != ["opaque_id", "question", "same_forward_public_pages"]
        or copied.get("terminal") is not True
        or not isinstance(copied.get("runtime_completed"), bool)
        or not isinstance(copied.get("failure_as_zero"), bool)
        or copied.get("failure_as_zero") is completed
        or re.fullmatch(r"task_[0-9a-f]{24}", str(copied.get("opaque_id") or ""))
        is None
        or list(copied.get("arm_order") or []) not in contract.arm_order_vector()
        or set(predictions) != set(contract.ARMS)
        or set(hashes) != set(contract.ARMS)
        or set(successes) != set(contract.ARMS)
        or set(normalizers) != set(contract.ARMS)
        or any(
            not isinstance(predictions[arm], str)
            or not predictions[arm]
            or hashes[arm]
            != hashlib.sha256(predictions[arm].encode()).hexdigest()
            or not isinstance(successes[arm], bool)
            or normalizers[arm]
            not in {"not_attempted", "exact", "normalized", "unrecoverable"}
            for arm in contract.ARMS
        )
        or copied.get("prediction_changed")
        is not (predictions[contract.CONTROL_ARM] != predictions[contract.CANDIDATE_ARM])
        or isinstance(copied.get("elapsed_seconds"), bool)
        or not isinstance(copied.get("elapsed_seconds"), (int, float))
        or copied["elapsed_seconds"] < 0
        or _health(copied.get("effect_health")) != copied.get("effect_health")
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "retry_resume_skip_population_replacement_or_selective_rerun",
                "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions",
            )
        )
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.51.21 task row drifted")
    if completed:
        if (
            copied.get("outer_failure_type") is not None
            or not isinstance(copied.get("runtime_result_payload_sha256"), str)
            or len(copied["runtime_result_payload_sha256"]) != 64
            or runtime.validate_result(_reconstruct_runtime(copied))["opaque_id"]
            != copied["opaque_id"]
        ):
            raise RuntimeError("V2.51.21 bound runtime row drifted")
    elif (
        not isinstance(copied.get("outer_failure_type"), str)
        or not copied["outer_failure_type"]
        or len(copied["outer_failure_type"]) > 128
        or any(
            copied.get(name) is not None
            for name in (
                "failure_types",
                "grounded_plan_receipt",
                "selection_receipt",
                "physical_wave_receipts",
                "physical_effects",
                "cost",
                "content_free_receipt",
                "runtime_result_payload_sha256",
            )
        )
        or any(successes.values())
        or copied.get("prediction_changed") is not False
    ):
        raise RuntimeError("V2.51.21 outer failure row drifted")
    return copied


def run_one_task(
    task: Mapping[str, str], arm_order: Sequence[str]
) -> dict[str, Any]:
    if set(task) != {"opaque_id", "question"}:
        raise ValueError("V2.51.21 runtime input must be opaque_id and question")
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
        row = _from_runtime(
            task, arm_order, result, _health_snapshot(model, searches)
        )
    except BaseException as exc:
        row = _terminal_outer_failure(
            task,
            arm_order,
            exc,
            time.monotonic() - started,
            _health_snapshot(model, searches),
        )
    return validate_task_row(row)


def _mapping_failures(row: Mapping[str, Any]) -> int:
    if not row["runtime_completed"]:
        return 0
    waves = row["physical_wave_receipts"]
    return sum(
        int(waves[phase]["query_local_mapping_failure_count"])
        for phase in runtime.PHASES
        if isinstance(waves[phase], Mapping)
    )


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
        raise RuntimeError("V2.51.21 fixed task vector drifted")
    completed = [row for row in checked if row["runtime_completed"]]
    receipts = [row["content_free_receipt"] for row in completed]
    hard_failures = sum(
        sum(row["effect_health"].values()) for row in checked
    )
    return {
        "task_count": contract.TASK_COUNT,
        "terminal_tasks": len(checked),
        "completed_runtime_tasks": len(completed),
        "failure_as_zero_tasks": sum(row["failure_as_zero"] for row in checked),
        "both_arms_model_success_tasks": sum(
            all(row["model_success"].values()) for row in checked
        ),
        "shared_first_wave_completed_tasks": sum(
            receipt["shared_first_wave_completed"] for receipt in receipts
        ),
        "grounded_plan_attempted_tasks": sum(
            receipt["grounded_plan_model_call_attempted"] for receipt in receipts
        ),
        "grounded_plan_strategy_applied_tasks": sum(
            receipt["grounded_plan_strategy_applied"] for receipt in receipts
        ),
        "shared_second_wave_completed_tasks": sum(
            receipt["shared_second_wave_completed"] for receipt in receipts
        ),
        "selection_strategy_eligible_tasks": sum(
            receipt["selection_strategy_eligible"] for receipt in receipts
        ),
        "selection_changed_tasks": sum(
            receipt["selection_changed"] for receipt in receipts
        ),
        "positive_target_field_page_gain_tasks": sum(
            receipt["target_field_page_gain"] > 0 for receipt in receipts
        ),
        "positive_target_field_pair_gain_tasks": sum(
            receipt["target_field_pair_gain"] > 0 for receipt in receipts
        ),
        "retrieval_mechanism_engaged_tasks": sum(
            receipt["retrieval_mechanism_engaged"] for receipt in receipts
        ),
        "prediction_changed_tasks": sum(
            row["prediction_changed"] for row in checked
        ),
        "attributable_prediction_changed_tasks": sum(
            receipt["attributable_prediction_change"] for receipt in receipts
        ),
        "unattributable_prediction_changed_tasks": sum(
            row["prediction_changed"]
            and not row["content_free_receipt"]["attributable_prediction_change"]
            for row in completed
        ),
        "physical_queries": sum(
            receipt["physical_query_count"] for receipt in receipts
        ),
        "physical_fetches": sum(
            receipt["physical_fetch_count"] for receipt in receipts
        ),
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
        "control_logical_fetches": sum(
            receipt["arm_metrics"][contract.CONTROL_ARM]["logical_fetch_count"]
            for receipt in receipts
        ),
        "candidate_logical_fetches": sum(
            receipt["arm_metrics"][contract.CANDIDATE_ARM]["logical_fetch_count"]
            for receipt in receipts
        ),
        "control_evidence_characters": sum(
            receipt["control_evidence_characters"] for receipt in receipts
        ),
        "candidate_evidence_characters": sum(
            receipt["candidate_evidence_characters"] for receipt in receipts
        ),
        "outer_or_accounting_failure_tasks": sum(
            not row["runtime_completed"] for row in checked
        ),
        "terminal_transport_timeout_helper_or_model_hard_failures": hard_failures,
        "query_local_mapping_failure_rows": sum(
            _mapping_failures(row) for row in completed
        ),
        "control_arm_model_failures": sum(
            not row["model_success"][contract.CONTROL_ARM] for row in checked
        ),
        "candidate_arm_model_failures": sum(
            not row["model_success"][contract.CANDIDATE_ARM] for row in checked
        ),
        "system_total_tokens": sum(
            int(row["cost"]["system_total_tokens"]) for row in completed
        ),
        "batch_wall_seconds": round(max(0.0, float(wall_seconds)), 6),
        "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions": False,
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
        "minimum_first_wave_completed": aggregate[
            "shared_first_wave_completed_tasks"
        ]
        >= gate["minimum_first_wave_completed_tasks"],
        "minimum_grounded_plan_attempted": aggregate[
            "grounded_plan_attempted_tasks"
        ]
        >= gate["minimum_grounded_plan_attempted_tasks"],
        "minimum_grounded_plan_strategy_applied": aggregate[
            "grounded_plan_strategy_applied_tasks"
        ]
        >= gate["minimum_grounded_plan_strategy_applied_tasks"],
        "minimum_second_wave_completed": aggregate[
            "shared_second_wave_completed_tasks"
        ]
        >= gate["minimum_second_wave_completed_tasks"],
        "minimum_selection_strategy_eligible": aggregate[
            "selection_strategy_eligible_tasks"
        ]
        >= gate["minimum_selection_strategy_eligible_tasks"],
        "minimum_selection_changed": aggregate["selection_changed_tasks"]
        >= gate["minimum_selection_changed_tasks"],
        "minimum_positive_target_field_page_gain": aggregate[
            "positive_target_field_page_gain_tasks"
        ]
        >= gate["minimum_positive_target_field_page_gain_tasks"],
        "minimum_positive_target_field_pair_gain": aggregate[
            "positive_target_field_pair_gain_tasks"
        ]
        >= gate["minimum_positive_target_field_pair_gain_tasks"],
        "minimum_retrieval_mechanism_engaged": aggregate[
            "retrieval_mechanism_engaged_tasks"
        ]
        >= gate["minimum_retrieval_mechanism_engaged_tasks"],
        "minimum_prediction_changed": aggregate["prediction_changed_tasks"]
        >= gate["minimum_prediction_changed_tasks"],
        "minimum_attributable_prediction_changed": aggregate[
            "attributable_prediction_changed_tasks"
        ]
        >= gate["minimum_attributable_prediction_changed_tasks"],
        "zero_unattributable_prediction_change": aggregate[
            "unattributable_prediction_changed_tasks"
        ]
        == 0,
        "zero_outer_or_accounting_failure": aggregate[
            "outer_or_accounting_failure_tasks"
        ]
        <= gate["maximum_outer_or_accounting_failure_tasks"],
        "zero_terminal_effect_hard_failure": aggregate[
            "terminal_transport_timeout_helper_or_model_hard_failures"
        ]
        <= gate[
            "maximum_terminal_transport_timeout_helper_or_model_hard_failures"
        ],
        "candidate_model_failures_do_not_increase": aggregate[
            "candidate_arm_model_failures"
        ]
        - aggregate["control_arm_model_failures"]
        <= gate["maximum_candidate_arm_model_failures_over_control"],
        "exact_physical_query_budget": aggregate["physical_queries"]
        == gate["exact_physical_queries_per_completed_task"] * completed,
        "physical_fetch_cap_preserved": aggregate["physical_fetches"]
        <= gate["maximum_physical_fetches_per_completed_task"] * completed,
        "physical_model_budget_exact": aggregate["physical_model_logical_calls"]
        == gate["maximum_physical_model_logical_calls_per_completed_task"]
        * completed,
        "effective_arm_model_budgets_exact_and_equal": aggregate[
            "control_effective_model_logical_calls"
        ]
        == aggregate["candidate_effective_model_logical_calls"]
        == gate["maximum_effective_model_logical_calls_per_completed_arm"]
        * completed,
        "logical_fetch_caps_preserved": aggregate["control_logical_fetches"]
        <= 10 * completed
        and aggregate["candidate_logical_fetches"] <= 10 * completed,
        "evidence_lengths_equal": aggregate["control_evidence_characters"]
        == aggregate["candidate_evidence_characters"],
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
        copied.get("role")
        != "v25121_grounded_target_record_external_forward_result"
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
        raise RuntimeError("V2.51.21 forward result drifted")
    return copied


def run_forward() -> dict[str, Any]:
    _clean_pushed()
    protocol, start = _validate_start()
    if not _lease_inactive() or _active_conflicts():
        raise RuntimeError("V2.51.21 shared runtime is not ready")
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
        raise RuntimeError("V2.51.21 forward surface is not pristine")
    if contract.watcher_snapshot() != protocol["protected_watchers"]:
        raise RuntimeError("V2.51.21 protected watcher identity drifted")
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
        raise RuntimeError("V2.51.21 terminal denominator drifted")
    _publish_jsonl(ROOT / contract.TASK_ROWS, rows)
    freeze = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25121_grounded_target_record_external_prediction_freeze",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "task_count": contract.TASK_COUNT,
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "prediction_hash_vector_sha256": contract.payload_sha256(
                [row["prediction_sha256"] for row in rows]
            ),
            "all_predictions_terminal_before_hidden_mapping_gold_evaluator_or_quality_decision": True,
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
            "role": "v25121_grounded_target_record_external_forward_result",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "execution_start_sha256": contract.sha256(
                ROOT / contract.EXECUTION_START
            ),
            "execution_start_payload_sha256": start[
                "execution_start_payload_sha256"
            ],
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "prediction_freeze_sha256": contract.sha256(
                ROOT / contract.PREDICTION_FREEZE
            ),
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
