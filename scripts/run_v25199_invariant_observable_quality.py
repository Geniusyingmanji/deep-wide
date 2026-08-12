#!/usr/bin/env python3
"""Run the single authorized V2.51.99 invariant-observable quality forward."""

from __future__ import annotations

import copy
import json
import math
import os
import socket
import sys
import threading
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

from deepwide_agent import (  # noqa: E402
    v25192_content_free_outer_failure_observer as failure_observer,
)
from deepwide_agent import (  # noqa: E402
    v25196_vertical_receipt_invariant_observer as invariant_observer,
)
from deepwide_agent import (  # noqa: E402
    v25197_vertical_receipt_failure_probe as failure_probe,
)
from deepwide_agent import (  # noqa: E402
    v25199_invariant_observable_quality_contract as contract,
)
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24468_total_wall_transport import (  # noqa: E402
    HardTotalWallResponsesClient,
)
from deepwide_agent.v24985_robust_late_page_fetch import (  # noqa: E402
    validate_search_class,
)
from scripts import run_v25183_quote_aware_external as accounting  # noqa: E402
from scripts import run_v25195_failure_observable_quality as parent  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


TASK_ROLE = "v25199_invariant_observable_quality_task_result"
_OBSERVATIONS: dict[str, dict[str, Any] | None] = {}
_OBSERVATION_LOCK = threading.Lock()


def _bind_parent() -> None:
    # Process-local specialization of behavior-frozen V2.51.95 utilities.
    parent.contract = contract
    parent.TASK_ROLE = TASK_ROLE


_bind_parent()
runtime = contract.runtime


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    _bind_parent()
    return parent._read(relative, tracked=tracked)


def _read_jsonl(
    relative: Path, *, tracked: bool = False
) -> list[dict[str, Any]]:
    _bind_parent()
    return parent._read_jsonl(relative, tracked=tracked)


def _publish_json(path: Path, value: Mapping[str, Any]) -> None:
    parent._publish_json(path, value)


def _publish_jsonl(
    path: Path, rows: Sequence[Mapping[str, Any]]
) -> None:
    parent._publish_jsonl(path, rows)


def _clean_pushed() -> None:
    _bind_parent()
    parent._clean_pushed()


def _validate_start() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    start = _read(contract.EXECUTION_START)
    if (
        start.get("role")
        != "v25199_invariant_observable_quality_execution_start"
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or start.get("protocol_sha256")
        != contract.sha256(ROOT / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256")
        != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("task_vector_sha256")
        != protocol["population"]["task_vector_sha256"]
        or start.get("protected_watchers") != contract.watcher_snapshot()
        or start.get("authorization")
        != {
            "one_external_forward": True,
            "external_evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_rerun": False,
        }
        or not contract.sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.51.99 execution start drifted")
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
                "role": "v25199_model_slot",
                "slot": index,
                "slot_cap": contract.MODEL_SLOT_CAP,
                "contains_credential_or_benchmark_content": False,
            },
        )


def _search(question: str, deadline: float) -> Any:
    if (
        contract.SEARCH != accounting.contract.SEARCH
        or contract.LIMITS != accounting.contract.LIMITS
    ):
        raise RuntimeError("V2.51.95 accounting search configuration drifted")
    return accounting._search(question, deadline)


def _from_runtime(*args: Any, **kwargs: Any) -> dict[str, Any]:
    _bind_parent()
    return parent._from_runtime(*args, **kwargs)


def _terminal_outer_failure(*args: Any, **kwargs: Any) -> dict[str, Any]:
    _bind_parent()
    return parent._terminal_outer_failure(*args, **kwargs)


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    _bind_parent()
    return parent.validate_task_row(value)


def run_one_task(task: Mapping[str, str]) -> dict[str, Any]:
    if set(task) != {"opaque_id", "question"}:
        raise ValueError("V2.51.99 runtime input must be opaque_id and question")
    token = failure_probe.begin_task()
    try:
        _bind_parent()
        row = parent.run_one_task(task)
        observation = failure_probe.failure_observation()
        if observation is not None:
            invariant_observer.validate_observation(observation)
        with _OBSERVATION_LOCK:
            _OBSERVATIONS[str(task["opaque_id"])] = copy.deepcopy(observation)
        return validate_task_row(row)
    finally:
        failure_probe.end_task(token)


def build_invariant_observation_aggregate(
    rows: Sequence[Mapping[str, Any]],
    observations: Sequence[Mapping[str, Any] | None],
) -> dict[str, Any]:
    checked = [validate_task_row(row) for row in rows]
    if len(checked) != contract.TASK_COUNT or len(observations) != len(checked):
        raise RuntimeError("V2.51.99 invariant observation denominator drifted")
    v25158_failures = [
        index
        for index, row in enumerate(checked)
        if not row["runtime_completed"]
        and row["failure_observation"]["failure_code"]
        == "v25158_receipt_validation"
    ]
    observed_indices = [
        index for index, observation in enumerate(observations) if observation is not None
    ]
    if any(index not in v25158_failures for index in observed_indices):
        raise RuntimeError("V2.51.99 invariant observation task binding drifted")
    validated: list[dict[str, Any]] = []
    for observation in observations:
        if observation is not None:
            validated.append(
                invariant_observer.validate_observation(observation)
            )
    code_counts = Counter(
        code
        for observation in validated
        for code in observation["violation_codes"]
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25199_invariant_observation_aggregate",
        "protocol_id": contract.PROTOCOL_ID,
        "task_count": contract.TASK_COUNT,
        "v25158_receipt_failure_tasks": len(v25158_failures),
        "v25158_invariant_observed_failure_tasks": len(validated),
        "v25158_invariant_observer_missing_tasks": max(
            0, len(v25158_failures) - len(observed_indices)
        ),
        "violation_code_counts": dict(sorted(code_counts.items())),
        "violation_event_count": sum(code_counts.values()),
        "per_task_observation_identity_or_order_persisted": False,
        "contains_receipt_value_task_question_query_url_title_page_identity_column_key_value_prediction_semantic_hash_exception_message_traceback_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["aggregate_payload_sha256"] = contract.payload_sha256(value)
    return validate_invariant_observation_aggregate(value)


def validate_invariant_observation_aggregate(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("aggregate_payload_sha256", None)
    counts = (
        "task_count",
        "v25158_receipt_failure_tasks",
        "v25158_invariant_observed_failure_tasks",
        "v25158_invariant_observer_missing_tasks",
        "violation_event_count",
    )
    false_flags = (
        "per_task_observation_identity_or_order_persisted",
        "contains_receipt_value_task_question_query_url_title_page_identity_column_key_value_prediction_semantic_hash_exception_message_traceback_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    codes = copied.get("violation_code_counts")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "protocol_id",
            *counts,
            "violation_code_counts",
            *false_flags,
            "aggregate_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25199_invariant_observation_aggregate"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or copied["task_count"] != contract.TASK_COUNT
        or copied["v25158_invariant_observed_failure_tasks"]
        + copied["v25158_invariant_observer_missing_tasks"]
        != copied["v25158_receipt_failure_tasks"]
        or not isinstance(codes, Mapping)
        or not set(codes).issubset(invariant_observer.VIOLATION_CODES)
        or any(
            isinstance(count, bool)
            or not isinstance(count, int)
            or count <= 0
            for count in codes.values()
        )
        or sum(codes.values()) != copied["violation_event_count"]
        or copied["v25158_invariant_observed_failure_tasks"] > 0
        and copied["violation_event_count"] == 0
        or any(copied.get(name) is not False for name in false_flags)
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.51.99 invariant observation aggregate drifted")
    return copied


_BASE_AGGREGATE_KEYS = {
    *parent._INTEGER_NAMES,
    "batch_wall_seconds",
    "outer_failure_stage_counts",
    "outer_failure_code_counts",
    "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions",
    "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
    "entropy_or_information_gain_assigns_signed_credit",
}


def _base_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(value[key]) for key in _BASE_AGGREGATE_KEYS}


def aggregate_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    wall_seconds: float,
    invariant_aggregate: Mapping[str, Any],
) -> dict[str, Any]:
    _bind_parent()
    base = parent.aggregate_rows(rows, wall_seconds=wall_seconds)
    invariant = validate_invariant_observation_aggregate(invariant_aggregate)
    value = {
        **base,
        "v25158_receipt_failure_tasks": invariant[
            "v25158_receipt_failure_tasks"
        ],
        "v25158_invariant_observed_failure_tasks": invariant[
            "v25158_invariant_observed_failure_tasks"
        ],
        "v25158_invariant_observer_missing_tasks": invariant[
            "v25158_invariant_observer_missing_tasks"
        ],
        "v25158_invariant_violation_code_counts": copy.deepcopy(
            invariant["violation_code_counts"]
        ),
        "v25158_invariant_violation_event_count": invariant[
            "violation_event_count"
        ],
    }
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    extra_counts = (
        "v25158_receipt_failure_tasks",
        "v25158_invariant_observed_failure_tasks",
        "v25158_invariant_observer_missing_tasks",
        "v25158_invariant_violation_event_count",
    )
    codes = copied.get("v25158_invariant_violation_code_counts")
    if (
        set(copied)
        != {
            *_BASE_AGGREGATE_KEYS,
            *extra_counts,
            "v25158_invariant_violation_code_counts",
        }
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in extra_counts
        )
        or not isinstance(codes, Mapping)
        or not set(codes).issubset(invariant_observer.VIOLATION_CODES)
        or any(
            isinstance(count, bool)
            or not isinstance(count, int)
            or count <= 0
            for count in codes.values()
        )
        or sum(codes.values())
        != copied["v25158_invariant_violation_event_count"]
        or copied["v25158_invariant_observed_failure_tasks"]
        + copied["v25158_invariant_observer_missing_tasks"]
        != copied["v25158_receipt_failure_tasks"]
        or copied["v25158_receipt_failure_tasks"]
        != copied["outer_failure_code_counts"].get(
            "v25158_receipt_validation", 0
        )
        or copied["v25158_invariant_observed_failure_tasks"] > 0
        and copied["v25158_invariant_violation_event_count"] == 0
    ):
        raise RuntimeError("V2.51.99 aggregate drifted")
    parent.validate_aggregate(_base_aggregate(copied))
    return copied


def mechanism_decision(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    checked = validate_aggregate(aggregate)
    _bind_parent()
    decision = parent.mechanism_decision(_base_aggregate(checked))
    checks = copy.deepcopy(decision["checks"])
    checks["v25158_invariant_observability_complete"] = (
        checked["v25158_invariant_observer_missing_tasks"] == 0
        and checked["v25158_invariant_observed_failure_tasks"]
        == checked["v25158_receipt_failure_tasks"]
    )
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "checks": checks,
        "failed_checks": failed,
        "same_response_mechanism_gate_passed": not failed,
        "postfreeze_external_evaluator_design": not failed,
        "external_evaluator_now": False,
        "deepwidebench_dev64_exact220_or_sota": False,
    }


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    aggregate = copied.get("aggregate")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "protocol_id",
            "created_at_unix",
            "execution_start_sha256",
            "execution_start_payload_sha256",
            "task_rows_sha256",
            "prediction_freeze_sha256",
            "invariant_observation_aggregate_sha256",
            "aggregate",
            "mechanism_decision",
            "authorization",
            "result_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25199_invariant_observable_quality_forward_result"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or not isinstance(aggregate, Mapping)
        or validate_aggregate(aggregate) != dict(aggregate)
        or copied.get("mechanism_decision") != mechanism_decision(aggregate)
        or copied.get("authorization")
        != {
            "forward_audit": True,
            "postfreeze_evaluator_implementation_only_after_pushed_forward_audit_go": True,
            "external_evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_rerun": False,
        }
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.51.99 forward result drifted")
    return copied


def run_forward() -> dict[str, Any]:
    _clean_pushed()
    protocol, start = _validate_start()
    _bind_parent()
    if not parent._lease_inactive() or parent._active_conflicts():
        raise RuntimeError("V2.51.99 shared runtime is not ready")
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
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink() for path in future
    ):
        raise RuntimeError("V2.51.99 forward surface is not pristine")
    if contract.watcher_snapshot() != protocol["protected_watchers"]:
        raise RuntimeError("V2.51.99 watcher identity drifted")
    validate_search_class()
    failure_probe.install_probe()
    tasks = contract.task_vector()
    _prepare_output()
    with _OBSERVATION_LOCK:
        _OBSERVATIONS.clear()
    started = time.monotonic()
    values: list[dict[str, Any] | None] = [None] * contract.TASK_COUNT
    with acquire_deepwide_api_lease(
        ROOT,
        owner=contract.LEASE_OWNER,
        purpose=contract.LEASE_PURPOSE,
        path=ROOT / contract.LEASE_PATH,
    ):
        with ThreadPoolExecutor(
            max_workers=contract.EXECUTOR_CONCURRENCY
        ) as pool:
            futures = {
                pool.submit(run_one_task, task): index
                for index, task in enumerate(tasks)
            }
            for future in as_completed(futures):
                values[futures[future]] = future.result()
    rows = [validate_task_row(row) for row in values if row is not None]
    if len(rows) != contract.TASK_COUNT:
        raise RuntimeError("V2.51.99 terminal denominator drifted")
    with _OBSERVATION_LOCK:
        observations = [
            copy.deepcopy(_OBSERVATIONS.get(task["opaque_id"])) for task in tasks
        ]
    invariant = build_invariant_observation_aggregate(rows, observations)
    _publish_json(ROOT / contract.INVARIANT_OBSERVATION_AGGREGATE, invariant)
    _publish_jsonl(ROOT / contract.TASK_ROWS, rows)
    freeze = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25199_invariant_observable_quality_prediction_freeze",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "task_count": contract.TASK_COUNT,
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "invariant_observation_aggregate_sha256": contract.sha256(
                ROOT / contract.INVARIANT_OBSERVATION_AGGREGATE
            ),
            "control_prediction_hash_vector_sha256": contract.payload_sha256(
                [
                    row["prediction_sha256"][contract.CONTROL_ARM]
                    for row in rows
                ]
            ),
            "candidate_prediction_hash_vector_sha256": contract.payload_sha256(
                [
                    row["prediction_sha256"][contract.CANDIDATE_ARM]
                    for row in rows
                ]
            ),
            "all_predictions_terminal_before_gold_evaluator_or_quality_decision": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        },
        "freeze_payload_sha256",
    )
    _publish_json(ROOT / contract.PREDICTION_FREEZE, freeze)
    aggregate = aggregate_rows(
        rows,
        wall_seconds=time.monotonic() - started,
        invariant_aggregate=invariant,
    )
    decision = mechanism_decision(aggregate)
    forward = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25199_invariant_observable_quality_forward_result",
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
            "invariant_observation_aggregate_sha256": contract.sha256(
                ROOT / contract.INVARIANT_OBSERVATION_AGGREGATE
            ),
            "aggregate": aggregate,
            "mechanism_decision": decision,
            "authorization": {
                "forward_audit": True,
                "postfreeze_evaluator_implementation_only_after_pushed_forward_audit_go": True,
                "external_evaluator": False,
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
