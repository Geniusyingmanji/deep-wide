#!/usr/bin/env python3
"""Run the one authorized V2.50.45 shared-evidence external forward."""

from __future__ import annotations

import fcntl
import json
import os
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25038_source_only_batching as batching  # noqa: E402
from deepwide_agent import v25044_evidence_constrained_synthesis as treatment  # noqa: E402
from deepwide_agent import v25045_evidence_constrained_external_contract as contract  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from deepwide_agent.v24468_total_wall_transport import HardTotalWallResponsesClient  # noqa: E402
from deepwide_agent.v24630_exact220_contract import (  # noqa: E402
    CLEANUP_RESERVE_SECONDS,
    MINIMUM_MODEL_ATTEMPT_SECONDS,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


MODEL_SLOT_DIRECTORY = contract.OUTPUT_ROOT / "model_slots"


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.45 expected JSON object")
    return value


def _read_jsonl(relative: Path) -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, relative, tracked=False)
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.50.45 expected JSONL objects")
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
        raise RuntimeError("V2.50.45 requires clean pushed HEAD")


def _lease_inactive() -> bool:
    path = ROOT / contract.LEASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def _prepare_output() -> None:
    root = ROOT / contract.OUTPUT_ROOT
    root.mkdir(parents=True, mode=0o700, exist_ok=False)
    slots = ROOT / MODEL_SLOT_DIRECTORY
    slots.mkdir(mode=0o700)
    for index in range(1, contract.MODEL_SLOT_CAP + 1):
        _publish_json(
            slots / f"slot_{index:02d}.lock",
            {
                "artifact_version": 1,
                "role": "v25045_model_slot",
                "slot": index,
                "slot_cap": contract.MODEL_SLOT_CAP,
                "contains_credential_or_benchmark_content": False,
            },
        )


def _search(question: str, deadline: float) -> Any:
    return batching.ActionQueryObservedSourceOnlySearchClient(
        contract.SEARCH["proxy_url"],
        contract.SEARCH["model"],
        visible_question=question,
        reasoning_effort=contract.MODEL["reasoning_effort"],
        service_tier=contract.MODEL["service_tier"],
        timeout=contract.SEARCH["timeout_seconds"],
        max_retries=contract.SEARCH["max_retries"],
        absolute_deadline=deadline,
        cleanup_reserve_seconds=CLEANUP_RESERVE_SECONDS,
        minimum_attempt_seconds=MINIMUM_MODEL_ATTEMPT_SECONDS,
        max_workers=1,
        batch_size=2,
        search_context_size=contract.SEARCH["context_size"],
        max_output_tokens=7_000,
        fetch_pages=False,
        fetch_workers=contract.SEARCH["fetch_workers"],
        fetch_timeout=contract.SEARCH["fetch_timeout_seconds"],
        max_page_chars=contract.SEARCH["max_page_chars"],
        hard_fetch_deadline_seconds=contract.SEARCH["hard_fetch_deadline_seconds"],
        stage_callback=lambda _event: None,
    )


def _model(deadline: float) -> tuple[Any, HardTotalWallResponsesClient]:
    inner = HardTotalWallResponsesClient(
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
    limited = DeadlineAwareGlobalModelSlotLimiter(
        inner,
        slot_directory=ROOT / MODEL_SLOT_DIRECTORY,
        output_root=ROOT / contract.OUTPUT_ROOT,
        slot_cap=contract.MODEL_SLOT_CAP,
        pool_id=POOL_ID,
        absolute_deadline=deadline,
        cleanup_reserve_seconds=CLEANUP_RESERVE_SECONDS,
        minimum_attempt_seconds=MINIMUM_MODEL_ATTEMPT_SECONDS,
    )
    return limited, inner


def _zero_usage(attempts: int = 0) -> dict[str, int]:
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "elapsed_milliseconds": 0,
        "provider_attempts": attempts,
    }


def _fetch_requests(leads: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "url": str(lead.get("fetch_url") or lead.get("url") or ""),
            "query": "shared evidence constrained synthesis external fetch",
            "title": str(lead.get("title") or "")[:500],
            "member_label": "",
        }
        for lead in leads
    ]


def run_task(index: int) -> dict[str, Any]:
    task = contract.task_vector()[index]
    queries = contract.query_vector()[index]
    order = contract.arm_order_vector()[index]
    started = time.monotonic()
    deadline = started + contract.TASK_DEADLINE_SECONDS
    search = _search(task["question"], deadline)
    leads: list[dict[str, str]] = []
    search_observation: dict[str, Any] = {}
    failure_stage: str | None = None
    try:
        leads, search_observation = batching.run_search_arm(
            search,
            queries,
            "split_2_plus_2",
            lead_cap=contract.LEAD_CAP,
        )
    except Exception as exc:
        failure_stage = f"search:{type(exc).__name__}"

    fetch_requests: list[dict[str, str]] = []
    fetched: dict[str, dict[str, Any]] = {}
    fetch_attempts = fetch_successes = 0
    fetch_health = {
        "hard_fetch_helper_calls": 0,
        "hard_fetch_deadline_failures": 0,
        "fetch_helper_failures": 0,
        "fetch_deadline_rejections": 0,
    }
    if failure_stage is None:
        fetch_requests = _fetch_requests(leads)
        try:
            batches = search.fetch_urls(fetch_requests)
            fetched = batching.fetched_page_map(batches)
            fetch_attempts = len(fetch_requests)
            fetch_successes = sum(
                bool(str(value.get("raw_content") or value.get("content") or "").strip())
                for value in fetched.values()
            )
        except Exception as exc:
            failure_stage = f"fetch:{type(exc).__name__}"
        health = search.transport_health()
        fetch_health = {name: int(health.get(name, 0) or 0) for name in fetch_health}

    evidence = ""
    evidence_observation = {
        "usable_pages": 0,
        "raw_characters": 0,
        "evidence_characters": 0,
        "fixed_budget_filled": 0,
    }
    if failure_stage is None:
        value, evidence_observation = batching.build_fixed_evidence(
            leads,
            fetched,
            character_budget=contract.EVIDENCE_CHARS,
            minimum_usable_pages=contract.MINIMUM_USABLE_PAGES,
            minimum_raw_characters=contract.MINIMUM_RAW_CHARACTERS,
        )
        if value is None:
            failure_stage = "evidence:insufficient"
        else:
            evidence = value

    predictions = {arm: contract.FALLBACK_TABLE for arm in contract.ARMS}
    normalizer_status = {arm: "fallback" for arm in contract.ARMS}
    model_success = {arm: False for arm in contract.ARMS}
    model_attempts = {arm: 0 for arm in contract.ARMS}
    model_usage = {arm: _zero_usage() for arm in contract.ARMS}
    treatment_receipts: dict[str, dict[str, Any]] = {}
    model_hard_timeouts = 0
    if failure_stage is None:
        for arm in order:
            system, user, receipt = treatment.synthesis_prompt(
                arm,
                question=task["question"],
                columns=contract.COLUMNS,
                evidence=evidence,
            )
            treatment_receipts[arm] = receipt
            provider, inner = _model(deadline)
            before_attempts = int(inner.attempts)
            started_model = time.monotonic()
            try:
                response = provider.complete(
                    system,
                    user,
                    max_output_tokens=contract.MODEL_OUTPUT_TOKENS,
                    json_mode=False,
                )
                attempts = int(inner.attempts) - before_attempts
                usage = response.usage if isinstance(response.usage, Mapping) else {}
                prediction, status = batching.normalize_prediction(
                    response.text,
                    contract.COLUMNS,
                    fallback=contract.FALLBACK_TABLE,
                )
                predictions[arm] = prediction
                normalizer_status[arm] = status
                model_success[arm] = status != "fallback"
                model_attempts[arm] = attempts
                model_usage[arm] = {
                    "input_tokens": int(usage.get("input_tokens", 0) or 0),
                    "output_tokens": int(usage.get("output_tokens", 0) or 0),
                    "total_tokens": int(usage.get("total_tokens", 0) or 0),
                    "elapsed_milliseconds": int((time.monotonic() - started_model) * 1000),
                    "provider_attempts": attempts,
                }
            except Exception:
                attempts = int(inner.attempts) - before_attempts
                model_attempts[arm] = attempts
                model_usage[arm] = _zero_usage(attempts)
            model_hard_timeouts += int(inner.hard_total_wall_timeouts)

    completed = failure_stage is None and all(model_success.values())
    if not completed:
        if failure_stage is None:
            failure_stage = "model_or_normalizer_failure"
        predictions = {arm: contract.FALLBACK_TABLE for arm in contract.ARMS}
        normalizer_status = {arm: "fallback" for arm in contract.ARMS}
        model_success = {arm: False for arm in contract.ARMS}
    row = {
        "artifact_version": 1,
        "role": "v25045_evidence_constrained_external_task_result",
        "protocol_id": contract.PROTOCOL_ID,
        "opaque_id": task["opaque_id"],
        "runtime_input_keys": ["opaque_id", "question", "same_forward_public_pages"],
        "terminal": True,
        "completed": completed,
        "failure_as_zero": not completed,
        "failure_stage": failure_stage,
        "arm_order": order,
        "search": search_observation,
        "selected_leads": len(leads),
        "shared_fetch_attempts": fetch_attempts,
        "shared_fetch_successes": fetch_successes,
        "fetch_health": fetch_health,
        "shared_evidence": evidence_observation,
        "treatment_receipts": treatment_receipts,
        "model_success": model_success,
        "model_attempts": model_attempts,
        "model_usage": model_usage,
        "model_hard_total_wall_timeouts": model_hard_timeouts,
        "normalizer_status": normalizer_status,
        "predictions": predictions,
        "prediction_sha256": {
            arm: contract.payload_sha256(predictions[arm]) for arm in contract.ARMS
        },
        "prediction_changed": predictions[contract.CONTROL_ARM]
        != predictions[contract.CANDIDATE_ARM],
        "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
        "one_shared_split_2_plus_2_search_and_fetch_prefix": True,
        "same_evidence_bytes_columns_model_output_cap_and_deadline": True,
        "only_treatment_identity_field_record_bound_synthesis_contract": True,
        "arm_order_balanced_by_preoutcome_opaque_hash": True,
        "provider_narrative_or_snippet_used_as_active_evidence": False,
        "query_url_host_title_page_provider_payload_or_credential_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "pypi_gold_endpoint_opened": False,
        "entropy_or_information_gain_assigns_credit_or_routes": False,
        "retry_resume_skip_or_selective_rerun": False,
    }
    return validate_task_row(contract.seal(row, "result_payload_sha256"))


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    predictions = copied.get("predictions")
    receipts = copied.get("treatment_receipts")
    completed = copied.get("completed") is True
    expected = {
        "artifact_version", "role", "protocol_id", "opaque_id",
        "runtime_input_keys", "terminal", "completed", "failure_as_zero",
        "failure_stage", "arm_order", "search", "selected_leads",
        "shared_fetch_attempts", "shared_fetch_successes", "fetch_health",
        "shared_evidence", "treatment_receipts", "model_success",
        "model_attempts", "model_usage", "model_hard_total_wall_timeouts",
        "normalizer_status", "predictions", "prediction_sha256",
        "prediction_changed", "wall_seconds",
        "one_shared_split_2_plus_2_search_and_fetch_prefix",
        "same_evidence_bytes_columns_model_output_cap_and_deadline",
        "only_treatment_identity_field_record_bound_synthesis_contract",
        "arm_order_balanced_by_preoutcome_opaque_hash",
        "provider_narrative_or_snippet_used_as_active_evidence",
        "query_url_host_title_page_provider_payload_or_credential_persisted",
        "mapping_gold_category_question_type_split_evaluator_score_reward_read",
        "pypi_gold_endpoint_opened",
        "entropy_or_information_gain_assigns_credit_or_routes",
        "retry_resume_skip_or_selective_rerun", "result_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("role") != "v25045_evidence_constrained_external_task_result"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("runtime_input_keys") != ["opaque_id", "question", "same_forward_public_pages"]
        or copied.get("terminal") is not True
        or copied.get("completed") is not (copied.get("failure_as_zero") is False)
        or not isinstance(predictions, Mapping)
        or set(predictions) != set(contract.ARMS)
        or any(not isinstance(predictions[arm], str) or not predictions[arm] for arm in contract.ARMS)
        or copied.get("prediction_sha256")
        != {arm: contract.payload_sha256(predictions[arm]) for arm in contract.ARMS}
        or copied.get("prediction_changed") is not (
            predictions[contract.CONTROL_ARM]
            != predictions[contract.CANDIDATE_ARM]
        )
        or copied.get("arm_order") not in [list(contract.ARMS), list(contract.ARMS[::-1])]
        or completed
        and (
            copied.get("failure_stage") is not None
            or not all((copied.get("model_success") or {}).values())
            or not isinstance(receipts, Mapping)
            or set(receipts) != set(contract.ARMS)
            or any(treatment.validate_receipt(receipts[arm]) != receipts[arm] for arm in contract.ARMS)
            or len({receipts[arm]["evidence_characters"] for arm in contract.ARMS}) != 1
        )
        or not completed
        and (
            copied.get("failure_stage") is None
            or predictions != {arm: contract.FALLBACK_TABLE for arm in contract.ARMS}
        )
        or any(
            copied.get(name) is not True
            for name in (
                "one_shared_split_2_plus_2_search_and_fetch_prefix",
                "same_evidence_bytes_columns_model_output_cap_and_deadline",
                "only_treatment_identity_field_record_bound_synthesis_contract",
                "arm_order_balanced_by_preoutcome_opaque_hash",
            )
        )
        or any(
            copied.get(name) is not False
            for name in (
                "provider_narrative_or_snippet_used_as_active_evidence",
                "query_url_host_title_page_provider_payload_or_credential_persisted",
                "mapping_gold_category_question_type_split_evaluator_score_reward_read",
                "pypi_gold_endpoint_opened",
                "entropy_or_information_gain_assigns_credit_or_routes",
                "retry_resume_skip_or_selective_rerun",
            )
        )
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.50.45 task result drifted")
    return copied


def aggregate_rows(
    rows: Sequence[Mapping[str, Any]], *, batch_wall_seconds: float
) -> dict[str, Any]:
    counters: Counter[str] = Counter()
    minimum_leads: list[int] = []
    for raw in rows:
        row = validate_task_row(raw)
        counters["terminal"] += int(row["terminal"])
        counters["completed"] += int(row["completed"])
        counters["failure_as_zero"] += int(row["failure_as_zero"])
        counters["prediction_changed"] += int(row["prediction_changed"])
        minimum_leads.append(int(row["selected_leads"]))
        counters["shared_fetch_attempts"] += int(row["shared_fetch_attempts"])
        counters["shared_fetch_successes"] += int(row["shared_fetch_successes"])
        for name, value in row["fetch_health"].items():
            counters[name] += int(value)
        counters["model_hard_total_wall_timeouts"] += int(row["model_hard_total_wall_timeouts"])
        for name in (
            "logical_query_count", "raw_unrecoverable_failure_count",
            "selected_lead_count", "provider_calls", "provider_attempts",
            "input_tokens", "output_tokens", "total_tokens",
            "observed_exact_action_query_count", "recursive_split_requests",
            "transport_failures", "hard_total_wall_timeouts",
        ):
            counters[f"search_{name}"] += int((row.get("search") or {}).get(name, 0))
        for name, value in row["shared_evidence"].items():
            counters[f"evidence_{name}"] += int(value)
        for arm in contract.ARMS:
            counters[f"{arm}_model_success"] += int(row["model_success"][arm])
            counters[f"{arm}_model_attempts"] += int(row["model_attempts"][arm])
            counters[f"{arm}_input_tokens"] += int(row["model_usage"][arm]["input_tokens"])
            counters[f"{arm}_total_tokens"] += int(row["model_usage"][arm]["total_tokens"])
            counters[f"{arm}_normalizer_fallback"] += int(row["normalizer_status"][arm] == "fallback")
    return {
        **{name: int(counters[name]) for name in sorted(counters)},
        "terminal_task_count": int(counters["terminal"]),
        "completed_task_count": int(counters["completed"]),
        "failure_as_zero_task_count": int(counters["failure_as_zero"]),
        "prediction_changed_task_count": int(counters["prediction_changed"]),
        "minimum_selected_leads_per_task": min(minimum_leads, default=0),
        "batch_wall_seconds": round(max(0.0, float(batch_wall_seconds)), 6),
        "contains_query_url_host_title_page_answer_provider_payload_or_score": False,
    }


def mechanism_decision(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    completed = int(aggregate.get("completed_task_count", 0))
    fetch_attempts = int(aggregate.get("shared_fetch_attempts", 0))
    fetch_success = int(aggregate.get("shared_fetch_successes", 0))
    checks = {
        "all_tasks_terminal": aggregate.get("terminal_task_count") == contract.TASK_COUNT,
        "failure_as_zero_bounded": int(aggregate.get("failure_as_zero_task_count", 999))
        <= contract.mechanism_gate()["maximum_failure_as_zero_tasks"],
        "exact_shared_logical_queries": aggregate.get("search_logical_query_count")
        == contract.TASK_COUNT * 4,
        "exact_shared_provider_calls": aggregate.get("search_provider_calls")
        == contract.TASK_COUNT * 2,
        "no_provider_retry": aggregate.get("search_provider_attempts")
        == aggregate.get("search_provider_calls"),
        "exact_action_query_coverage": aggregate.get("search_observed_exact_action_query_count")
        == contract.TASK_COUNT * 4,
        "shared_fetch_success_ratio": fetch_attempts > 0
        and fetch_success / fetch_attempts
        >= contract.mechanism_gate()["minimum_shared_fetch_success_rate"],
        "fixed_shared_evidence_budget": aggregate.get("evidence_evidence_characters")
        == completed * contract.EVIDENCE_CHARS,
        "model_attempts_and_successes": all(
            aggregate.get(f"{arm}_model_attempts") == completed
            and aggregate.get(f"{arm}_model_success") == completed
            for arm in contract.ARMS
        ),
        "minimum_prediction_change": aggregate.get("prediction_changed_task_count", 0)
        >= contract.MINIMUM_PREDICTION_CHANGES,
        "zero_transport_search_fetch_or_model_hard_failure": all(
            int(aggregate.get(name, 0)) == 0
            for name in (
                "search_raw_unrecoverable_failure_count",
                "search_recursive_split_requests",
                "search_transport_failures",
                "search_hard_total_wall_timeouts",
                "hard_fetch_deadline_failures",
                "fetch_helper_failures",
                "fetch_deadline_rejections",
                "model_hard_total_wall_timeouts",
            )
        ),
        "planned_fetch_equals_helper_calls": aggregate.get("shared_fetch_attempts")
        == aggregate.get("hard_fetch_helper_calls"),
    }
    passed = all(checks.values())
    return {
        "checks": checks,
        "failed_checks": sorted(name for name, ok in checks.items() if not ok),
        "mechanism_gate_passed": passed,
        "postfreeze_external_evaluator_authorized": passed,
        "deepwidebench_dev64_exact220_or_sota": False,
    }


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v25045_evidence_constrained_external_forward_result"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("terminal_tasks") != contract.TASK_COUNT
        or not isinstance(copied.get("aggregate"), Mapping)
        or copied.get("mechanism_decision") != mechanism_decision(copied["aggregate"])
        or copied.get("authorization", {}).get("deepwidebench_dev64_exact220_or_sota") is not False
        or not contract.sealed(copied, "forward_result_payload_sha256")
    ):
        raise RuntimeError("V2.50.45 forward result drifted")
    return copied


def run_forward() -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    start = _read(contract.EXECUTION_START)
    if (
        start.get("role") != "v25045_evidence_constrained_execution_start"
        or start.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256") != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("protected_watchers") != contract.watcher_snapshot()
        or not contract.sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.50.45 execution start drifted")
    future = (
        contract.FORWARD_RESULT, contract.FORWARD_AUDIT, contract.EVALUATOR,
        contract.EVALUATOR_TEST, contract.EVALUATOR_PROTOCOL, contract.RESULT,
        contract.POSTAUDIT, contract.OUTPUT_ROOT,
    )
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.50.45 forward/evaluator surface is not pristine")
    if protocol["protected_watchers"] != contract.watcher_snapshot() or not _lease_inactive():
        raise RuntimeError("V2.50.45 watcher or lease drifted")
    _prepare_output()
    started = time.monotonic()
    results: list[dict[str, Any] | None] = [None] * contract.TASK_COUNT
    with acquire_deepwide_api_lease(
        ROOT,
        owner="v25045_evidence_constrained_external_forward_v1",
        purpose="fresh_shared_evidence_constrained_synthesis_gate",
        path=ROOT / contract.LEASE_PATH,
    ):
        with ThreadPoolExecutor(max_workers=contract.EXECUTOR_CONCURRENCY) as pool:
            futures = {pool.submit(run_task, index): index for index in range(contract.TASK_COUNT)}
            for future in as_completed(futures):
                results[futures[future]] = future.result()
    rows = [validate_task_row(row) for row in results if row is not None]
    if len(rows) != contract.TASK_COUNT:
        raise RuntimeError("V2.50.45 terminal denominator drifted")
    rows.sort(key=lambda row: str(row["opaque_id"]))
    aggregate = aggregate_rows(rows, batch_wall_seconds=time.monotonic() - started)
    decision = mechanism_decision(aggregate)
    _publish_jsonl(ROOT / contract.TASK_ROWS, rows)
    freeze = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25045_evidence_constrained_prediction_freeze",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "terminal_tasks": len(rows),
            "all_predictions_terminal_before_pypi_gold_or_evaluator_open": True,
            "pypi_gold_endpoint_calls_before_freeze": 0,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        },
        "freeze_payload_sha256",
    )
    _publish_json(ROOT / contract.PREDICTION_FREEZE, freeze)
    value = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25045_evidence_constrained_external_forward_result",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "terminal_tasks": len(rows),
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
            "aggregate": aggregate,
            "mechanism_decision": decision,
            "source_policy": contract.source_policy(),
            "authorization": {
                "postfreeze_external_evaluator_implementation_and_protocol": decision[
                    "postfreeze_external_evaluator_authorized"
                ],
                "deepwidebench_dev64_exact220_or_sota": False,
                "retry_resume_selective_rerun_or_revaluation": False,
            },
        },
        "forward_result_payload_sha256",
    )
    _publish_json(ROOT / contract.FORWARD_RESULT, value)
    return validate_forward_result(value)


def main() -> None:
    value = run_forward()
    print(
        json.dumps(
            {
                "path": str(contract.FORWARD_RESULT),
                "aggregate": value["aggregate"],
                "decision": value["mechanism_decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
