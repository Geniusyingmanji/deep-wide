#!/usr/bin/env python3
"""Run the single fresh V2.50.38 label-blind external batching forward."""

from __future__ import annotations

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

from deepwide_agent import v25038_batching_external_contract as contract  # noqa: E402
from deepwide_agent import v25038_source_only_batching as batching  # noqa: E402
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
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


MODEL_SLOT_DIRECTORY = contract.OUTPUT_ROOT / "model_slots"


def _read(relative: Path) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.38 expected JSON object")
    return value


def _read_jsonl(relative: Path) -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, relative, tracked=False)
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.50.38 expected JSONL objects")
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
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _clean_pushed() -> None:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(
        ROOT, "rev-parse", "HEAD"
    ) != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.50.38 requires clean pushed HEAD")


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
                "role": "v25038_model_slot",
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
        batch_size=8,
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


def _zero_model_usage(provider_attempts: int) -> dict[str, int]:
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "elapsed_milliseconds": 0,
        "provider_attempts": provider_attempts,
    }


def _run_task(index: int) -> dict[str, Any]:
    task = contract.task_vector()[index]
    queries = contract.query_vector()[index]
    order = contract.arm_order_vector()[index]
    started = time.monotonic()
    deadline = started + contract.TASK_DEADLINE_SECONDS
    searches = {arm: _search(task["question"], deadline) for arm in contract.ARMS}
    leads: dict[str, list[dict[str, str]]] = {arm: [] for arm in contract.ARMS}
    search_observations: dict[str, dict[str, Any]] = {}
    failure_stage: str | None = None
    for arm in order:
        try:
            leads[arm], search_observations[arm] = batching.run_search_arm(
                searches[arm], queries, arm, lead_cap=contract.LEAD_CAP
            )
        except Exception as exc:
            failure_stage = f"search:{type(exc).__name__}"
            break

    fetch_requests: list[dict[str, str]] = []
    fetched: dict[str, dict[str, Any]] = {}
    fetch_attempts = fetch_successes = 0
    fetch_health = {
        "hard_fetch_helper_calls": 0,
        "hard_fetch_deadline_failures": 0,
        "fetch_helper_failures": 0,
        "fetch_deadline_rejections": 0,
    }
    fetch_client = searches[contract.CONTROL_ARM]
    if failure_stage is None:
        fetch_requests = batching.shared_fetch_requests(leads, arm_order=order)
        try:
            batches = fetch_client.fetch_urls(fetch_requests)
            fetched = batching.fetched_page_map(batches)
            fetch_attempts = len(fetch_requests)
            fetch_successes = sum(
                bool(str(value.get("raw_content") or value.get("content") or "").strip())
                for value in fetched.values()
            )
        except Exception as exc:
            failure_stage = f"fetch:{type(exc).__name__}"
        health = fetch_client.transport_health()
        fetch_health = {
            name: int(health.get(name, 0) or 0) for name in fetch_health
        }

    evidence: dict[str, str] = {}
    evidence_observations: dict[str, dict[str, int]] = {
        arm: {
            "usable_pages": 0,
            "raw_characters": 0,
            "evidence_characters": 0,
            "fixed_budget_filled": 0,
        }
        for arm in contract.ARMS
    }
    if failure_stage is None:
        for arm in contract.ARMS:
            value, observation = batching.build_fixed_evidence(
                leads[arm],
                fetched,
                character_budget=contract.EVIDENCE_CHARS,
                minimum_usable_pages=contract.MINIMUM_USABLE_PAGES,
                minimum_raw_characters=contract.MINIMUM_RAW_CHARACTERS,
            )
            evidence_observations[arm] = observation
            if value is None:
                failure_stage = "evidence:insufficient"
                break
            evidence[arm] = value

    predictions = {arm: contract.FALLBACK_TABLE for arm in contract.ARMS}
    normalizer_status = {arm: "fallback" for arm in contract.ARMS}
    model_success = {arm: False for arm in contract.ARMS}
    model_usage = {arm: _zero_model_usage(0) for arm in contract.ARMS}
    model_attempts = {arm: 0 for arm in contract.ARMS}
    model_hard_timeouts = 0
    if failure_stage is None:
        for arm in order:
            provider, inner = _model(deadline)
            system, user = batching.synthesis_prompt(task["question"], evidence[arm])
            before_attempts = int(inner.attempts)
            started_model = time.monotonic()
            try:
                result = provider.complete(
                    system,
                    user,
                    max_output_tokens=contract.MODEL_OUTPUT_TOKENS,
                    json_mode=False,
                )
                attempts = int(inner.attempts) - before_attempts
                usage = result.usage if isinstance(result.usage, Mapping) else {}
                prediction, status = batching.normalize_prediction(
                    result.text,
                    contract.COLUMNS,
                    fallback=contract.FALLBACK_TABLE,
                )
                predictions[arm] = prediction
                normalizer_status[arm] = status
                model_success[arm] = status != "fallback"
                model_usage[arm] = {
                    "input_tokens": int(usage.get("input_tokens", 0) or 0),
                    "output_tokens": int(usage.get("output_tokens", 0) or 0),
                    "total_tokens": int(usage.get("total_tokens", 0) or 0),
                    "elapsed_milliseconds": int(
                        (time.monotonic() - started_model) * 1000
                    ),
                    "provider_attempts": attempts,
                }
                model_attempts[arm] = attempts
            except Exception:
                attempts = int(inner.attempts) - before_attempts
                model_attempts[arm] = attempts
                model_usage[arm] = _zero_model_usage(attempts)
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
        "role": "v25038_batching_external_task_result",
        "protocol_id": contract.PROTOCOL_ID,
        "opaque_id": task["opaque_id"],
        "runtime_input_keys": ["opaque_id", "question", "same_forward_public_pages"],
        "terminal": True,
        "completed": completed,
        "failure_as_zero": not completed,
        "failure_stage": failure_stage,
        "arm_order": order,
        "search": search_observations,
        "selected_leads": {arm: len(leads[arm]) for arm in contract.ARMS},
        "shared_fetch_attempts": fetch_attempts,
        "shared_fetch_successes": fetch_successes,
        "fetch_health": fetch_health,
        "evidence": evidence_observations,
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
        "same_four_visible_queries_per_arm": True,
        "only_treatment_split_2_plus_2_vs_one_shot_4": True,
        "search_and_model_arm_first_position_balanced_by_preoutcome_opaque_hash": True,
        "shared_fetch_union_uses_same_preoutcome_arm_order": True,
        "shared_task_local_union_fetch_for_both_arms": True,
        "same_fixed_evidence_budget_prompt_model_output_cap_and_deadline": True,
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
    if (
        set(copied)
        != {
            "artifact_version", "role", "protocol_id", "opaque_id",
            "runtime_input_keys", "terminal", "completed", "failure_as_zero",
            "failure_stage", "arm_order", "search", "selected_leads",
            "shared_fetch_attempts", "shared_fetch_successes", "evidence",
            "fetch_health",
            "model_success", "model_attempts", "model_usage",
            "model_hard_total_wall_timeouts", "normalizer_status", "predictions",
            "prediction_sha256", "prediction_changed", "wall_seconds",
            "same_four_visible_queries_per_arm",
            "only_treatment_split_2_plus_2_vs_one_shot_4",
            "search_and_model_arm_first_position_balanced_by_preoutcome_opaque_hash",
            "shared_fetch_union_uses_same_preoutcome_arm_order",
            "shared_task_local_union_fetch_for_both_arms",
            "same_fixed_evidence_budget_prompt_model_output_cap_and_deadline",
            "provider_narrative_or_snippet_used_as_active_evidence",
            "query_url_host_title_page_provider_payload_or_credential_persisted",
            "mapping_gold_category_question_type_split_evaluator_score_reward_read",
            "pypi_gold_endpoint_opened",
            "entropy_or_information_gain_assigns_credit_or_routes",
            "retry_resume_skip_or_selective_rerun", "result_payload_sha256",
        }
        or
        copied.get("role") != "v25038_batching_external_task_result"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("runtime_input_keys")
        != ["opaque_id", "question", "same_forward_public_pages"]
        or copied.get("terminal") is not True
        or not isinstance(predictions, Mapping)
        or set(predictions) != set(contract.ARMS)
        or any(not isinstance(predictions[arm], str) or not predictions[arm] for arm in contract.ARMS)
        or copied.get("completed") is not (not bool(copied.get("failure_as_zero")))
        or copied.get("completed") is True
        and (
            copied.get("failure_stage") is not None
            or not all((copied.get("model_success") or {}).values())
            or any(
                (copied.get("normalizer_status") or {}).get(arm) == "fallback"
                for arm in contract.ARMS
            )
        )
        or copied.get("failure_as_zero") is True
        and (
            copied.get("failure_stage") is None
            or predictions
            != {arm: contract.FALLBACK_TABLE for arm in contract.ARMS}
        )
        or copied.get("arm_order") not in [
            [contract.CONTROL_ARM, contract.CANDIDATE_ARM],
            [contract.CANDIDATE_ARM, contract.CONTROL_ARM],
        ]
        or any(
            copied.get(name) is not True
            for name in (
                "same_four_visible_queries_per_arm",
                "only_treatment_split_2_plus_2_vs_one_shot_4",
                "search_and_model_arm_first_position_balanced_by_preoutcome_opaque_hash",
                "shared_fetch_union_uses_same_preoutcome_arm_order",
                "shared_task_local_union_fetch_for_both_arms",
                "same_fixed_evidence_budget_prompt_model_output_cap_and_deadline",
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
        raise RuntimeError("V2.50.38 task result drifted")
    return copied


def aggregate_rows(
    rows: Sequence[Mapping[str, Any]], *, batch_wall_seconds: float
) -> dict[str, Any]:
    counters: Counter[str] = Counter()
    minimum_leads = {arm: [] for arm in contract.ARMS}
    for raw in rows:
        row = validate_task_row(raw)
        counters["terminal"] += int(row["terminal"])
        counters["completed"] += int(row["completed"])
        counters["failure_as_zero"] += int(row["failure_as_zero"])
        counters["prediction_changed"] += int(row["prediction_changed"])
        counters["shared_fetch_attempts"] += int(row["shared_fetch_attempts"])
        counters["shared_fetch_successes"] += int(row["shared_fetch_successes"])
        for name in (
            "hard_fetch_helper_calls", "hard_fetch_deadline_failures",
            "fetch_helper_failures", "fetch_deadline_rejections",
        ):
            counters[name] += int(row["fetch_health"][name])
        counters["model_hard_total_wall_timeouts"] += int(
            row["model_hard_total_wall_timeouts"]
        )
        for arm in contract.ARMS:
            minimum_leads[arm].append(int(row["selected_leads"][arm]))
            observation = row["search"].get(arm) or {}
            for name in (
                "logical_query_count", "raw_action_source_count",
                "raw_unrecoverable_failure_count", "union_source_count",
                "selected_lead_count", "provider_calls", "provider_attempts",
                "tool_calls", "input_tokens", "output_tokens", "total_tokens",
                "observed_exact_action_query_count",
                "fully_observed_request_query_vectors", "recursive_split_requests",
                "transport_failures", "hard_total_wall_timeouts",
            ):
                counters[f"{arm}_{name}"] += int(observation.get(name, 0))
            evidence = row["evidence"][arm]
            for name in (
                "usable_pages", "raw_characters", "evidence_characters",
                "fixed_budget_filled",
            ):
                counters[f"{arm}_{name}"] += int(evidence[name])
            counters[f"{arm}_model_success"] += int(row["model_success"][arm])
            counters[f"{arm}_model_attempts"] += int(row["model_attempts"][arm])
            counters[f"{arm}_normalizer_fallback"] += int(
                row["normalizer_status"][arm] == "fallback"
            )
    return {
        **{name: int(counters[name]) for name in sorted(counters)},
        "terminal_task_count": int(counters["terminal"]),
        "completed_task_count": int(counters["completed"]),
        "failure_as_zero_task_count": int(counters["failure_as_zero"]),
        "prediction_changed_task_count": int(counters["prediction_changed"]),
        "minimum_selected_leads_per_task": {
            arm: min(values, default=0) for arm, values in minimum_leads.items()
        },
        "batch_wall_seconds": round(max(0.0, float(batch_wall_seconds)), 6),
        "contains_query_url_host_title_page_answer_provider_payload_or_score": False,
    }


def _ratio(candidate: float, control: float) -> float | None:
    return round(candidate / control, 12) if control else None


def mechanism_decision(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    gate = contract.mechanism_gate()
    control = contract.CONTROL_ARM
    candidate = contract.CANDIDATE_ARM
    ratios = {
        name: _ratio(
            float(aggregate.get(f"{candidate}_{name}", 0)),
            float(aggregate.get(f"{control}_{name}", 0)),
        )
        for name in (
            "input_tokens", "total_tokens", "selected_lead_count",
            "usable_pages", "raw_characters",
        )
    }
    fetch_ratio = _ratio(
        float(aggregate.get("shared_fetch_successes", 0)),
        float(aggregate.get("shared_fetch_attempts", 0)),
    )
    checks = {
        "all_tasks_terminal": aggregate.get("terminal_task_count") == contract.TASK_COUNT,
        "failure_as_zero_bounded": aggregate.get("failure_as_zero_task_count", 999)
        <= gate["maximum_failure_as_zero_tasks"],
        "exact_logical_queries": all(
            aggregate.get(f"{arm}_logical_query_count") == contract.TASK_COUNT * 4
            for arm in contract.ARMS
        ),
        "exact_provider_calls": aggregate.get(f"{control}_provider_calls")
        == contract.TASK_COUNT * 2
        and aggregate.get(f"{candidate}_provider_calls") == contract.TASK_COUNT,
        "no_provider_retry": all(
            aggregate.get(f"{arm}_provider_attempts")
            == aggregate.get(f"{arm}_provider_calls")
            for arm in contract.ARMS
        ),
        "exact_action_query_coverage": all(
            aggregate.get(f"{arm}_observed_exact_action_query_count")
            == contract.TASK_COUNT * 4
            for arm in contract.ARMS
        ),
        "candidate_search_input_cost": ratios["input_tokens"] is not None
        and ratios["input_tokens"] <= gate[
            "maximum_candidate_over_control_search_input_tokens"
        ],
        "candidate_search_total_cost": ratios["total_tokens"] is not None
        and ratios["total_tokens"] <= gate[
            "maximum_candidate_over_control_search_total_tokens"
        ],
        "candidate_selected_lead_yield": ratios["selected_lead_count"] is not None
        and ratios["selected_lead_count"] >= gate[
            "minimum_candidate_over_control_selected_leads"
        ],
        "candidate_usable_page_yield": ratios["usable_pages"] is not None
        and ratios["usable_pages"] >= gate[
            "minimum_candidate_over_control_usable_pages"
        ],
        "candidate_raw_character_yield": ratios["raw_characters"] is not None
        and ratios["raw_characters"] >= gate[
            "minimum_candidate_over_control_raw_characters"
        ],
        "shared_fetch_success_ratio": fetch_ratio is not None
        and fetch_ratio >= gate["minimum_shared_fetch_success_rate"],
        "fixed_evidence_budget": all(
            aggregate.get(f"{arm}_evidence_characters")
            == aggregate.get("completed_task_count", 0) * contract.EVIDENCE_CHARS
            for arm in contract.ARMS
        ),
        "model_attempts_and_successes": all(
            aggregate.get(f"{arm}_model_attempts")
            == aggregate.get("completed_task_count", 0)
            and aggregate.get(f"{arm}_model_success")
            == aggregate.get("completed_task_count", 0)
            for arm in contract.ARMS
        ),
        "zero_transport_or_search_failure": all(
            sum(
                int(aggregate.get(f"{arm}_{name}", 0))
                for name in (
                    "raw_unrecoverable_failure_count", "recursive_split_requests",
                    "transport_failures", "hard_total_wall_timeouts",
                )
            )
            == 0
            for arm in contract.ARMS
        )
        and int(aggregate.get("model_hard_total_wall_timeouts", 0)) == 0,
        "planned_fetch_equals_helper_calls": aggregate.get("shared_fetch_attempts")
        == aggregate.get("hard_fetch_helper_calls"),
        "zero_fetch_deadline_or_helper_failure": all(
            int(aggregate.get(name, 1)) == 0
            for name in (
                "hard_fetch_deadline_failures", "fetch_helper_failures",
                "fetch_deadline_rejections",
            )
        ),
    }
    passed = all(checks.values())
    return {
        "checks": checks,
        "failed_checks": sorted(name for name, ok in checks.items() if not ok),
        "ratios": {**ratios, "shared_fetch_successes": fetch_ratio},
        "mechanism_gate_passed": passed,
        "postfreeze_external_evaluator_authorized": passed,
        "deepwidebench_dev64_exact220_or_sota": False,
    }


def run_forward() -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    start = _read(contract.EXECUTION_START)
    if (
        start.get("role") != "v25038_batching_external_execution_start"
        or start.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256")
        != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("protected_watchers") != contract.watcher_snapshot()
        or not contract.sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.50.38 execution start drifted")
    future = (
        contract.FORWARD_RESULT, contract.FORWARD_AUDIT,
        contract.EVALUATOR_PROTOCOL, contract.RESULT, contract.POSTAUDIT,
        contract.OUTPUT_ROOT, contract.EVALUATOR,
    )
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.50.38 forward/evaluator surface is not pristine")
    if protocol["protected_watchers"] != contract.watcher_snapshot():
        raise RuntimeError("V2.50.38 protected watcher drifted")
    _prepare_output()
    started = time.monotonic()
    results: list[dict[str, Any] | None] = [None] * contract.TASK_COUNT
    with acquire_deepwide_api_lease(
        ROOT,
        owner="v25038_batching_external_forward_v1",
        purpose="fresh_source_only_split2_vs_oneshot4_external_gate",
        path=ROOT / contract.LEASE_PATH,
    ):
        with ThreadPoolExecutor(max_workers=contract.EXECUTOR_CONCURRENCY) as pool:
            futures = {pool.submit(_run_task, index): index for index in range(contract.TASK_COUNT)}
            for future in as_completed(futures):
                results[futures[future]] = future.result()
    rows = [validate_task_row(row) for row in results if row is not None]
    if len(rows) != contract.TASK_COUNT:
        raise RuntimeError("V2.50.38 terminal denominator drifted")
    rows.sort(key=lambda row: str(row["opaque_id"]))
    aggregate = aggregate_rows(rows, batch_wall_seconds=time.monotonic() - started)
    decision = mechanism_decision(aggregate)
    _publish_jsonl(ROOT / contract.TASK_ROWS, rows)
    freeze = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25038_batching_external_prediction_freeze",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "terminal_tasks": len(rows),
            "terminal_arm_predictions": len(rows) * len(contract.ARMS),
            "all_predictions_terminal_before_pypi_gold_or_evaluator_open": True,
            "pypi_gold_endpoint_calls_before_freeze": 0,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "retry_resume_skip_or_selective_rerun": False,
        },
        "freeze_payload_sha256",
    )
    _publish_json(ROOT / contract.PREDICTION_FREEZE, freeze)
    value = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25038_batching_external_forward_result",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
            "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
            "aggregate": aggregate,
            "mechanism_decision": decision,
            "protected_watchers_before": protocol["protected_watchers"],
            "protected_watchers_after": contract.watcher_snapshot(),
            "all_predictions_terminal_before_pypi_gold_or_evaluator_open": True,
            "source_policy": protocol["source_policy"],
            "authorization": {
                "forward_audit_generation": True,
                "postfreeze_external_evaluator_protocol": False,
                "deepwidebench_dev64_exact220_or_sota": False,
                "retry_resume_selective_rerun_or_revaluation": False,
            },
        },
        "result_payload_sha256",
    )
    _publish_json(ROOT / contract.FORWARD_RESULT, value)
    return value


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v25038_batching_external_forward_result"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("protected_watchers_before") != contract.watcher_snapshot()
        or copied.get("protected_watchers_after") != contract.watcher_snapshot()
        or copied.get("mechanism_decision")
        != mechanism_decision(copied.get("aggregate") or {})
        or copied.get("authorization", {}).get(
            "deepwidebench_dev64_exact220_or_sota"
        )
        is not False
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.50.38 forward result drifted")
    return copied


def main() -> None:
    value = run_forward()
    print(json.dumps({
        "path": str(contract.FORWARD_RESULT),
        "aggregate": value["aggregate"],
        "decision": value["mechanism_decision"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
