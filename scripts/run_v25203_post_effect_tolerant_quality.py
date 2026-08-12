#!/usr/bin/env python3
"""Run the single authorized V2.52.03 post-effect-tolerant forward."""

from __future__ import annotations

import copy
import json
import socket
import sys
import threading
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import (  # noqa: E402
    v25158_vertical_key_value_candidate_runtime as receipt_parent,
)
from deepwide_agent import (  # noqa: E402
    v25196_vertical_receipt_invariant_observer as invariant_observer,
)
from deepwide_agent import (  # noqa: E402
    v25197_vertical_receipt_failure_probe as failure_probe,
)
from deepwide_agent import (  # noqa: E402
    v25200_post_effect_tolerant_vertical_receipt as compatibility,
)
from deepwide_agent import (  # noqa: E402
    v25203_post_effect_tolerant_quality_contract as contract,
)
from deepwide_agent.v24985_robust_late_page_fetch import (  # noqa: E402
    validate_search_class,
)
from scripts import run_v25199_invariant_observable_quality as parent  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


TASK_ROLE = "v25203_post_effect_tolerant_quality_task_result"
_APPLICATIONS: dict[str, bool] = {}
_APPLICATION_LOCK = threading.Lock()
_INSTALL_LOCK = threading.Lock()


def _bind_parent() -> None:
    """Specialize the frozen V2.51.99 accounting helpers in this process."""

    parent.contract = contract
    parent.TASK_ROLE = TASK_ROLE
    parent.runtime = contract.runtime
    parent._bind_parent()


_bind_parent()
runtime = contract.runtime
accounting = parent.accounting


def _ensure_compatibility_validation() -> None:
    """Install only the exact V2.52.00 validator when needed."""

    with _INSTALL_LOCK:
        if failure_probe._INSTALLED:  # type: ignore[attr-defined]
            if (
                receipt_parent.validate_receipt
                is not failure_probe._observed_validate  # type: ignore[attr-defined]
                or failure_probe._FROZEN_VALIDATE  # type: ignore[attr-defined]
                is not compatibility.validate_receipt
            ):
                raise RuntimeError("V2.52.03 composed validator identity drifted")
            return
        if compatibility._INSTALLED:  # type: ignore[attr-defined]
            if receipt_parent.validate_receipt is not compatibility.validate_receipt:
                raise RuntimeError("V2.52.03 compatibility identity drifted")
            return
        compatibility.install_compatibility()


def install_runtime_observers() -> None:
    """Compose residual failure observation outside the exact compatibility."""

    with _INSTALL_LOCK:
        if failure_probe._INSTALLED:  # type: ignore[attr-defined]
            if (
                receipt_parent.validate_receipt
                is not failure_probe._observed_validate  # type: ignore[attr-defined]
                or failure_probe._FROZEN_VALIDATE  # type: ignore[attr-defined]
                is not compatibility.validate_receipt
            ):
                raise RuntimeError("V2.52.03 installed observer identity drifted")
            return
        if not compatibility._INSTALLED:  # type: ignore[attr-defined]
            compatibility.install_compatibility()
        elif receipt_parent.validate_receipt is not compatibility.validate_receipt:
            raise RuntimeError("V2.52.03 precomposed validator identity drifted")
        if (
            failure_probe._FROZEN_VALIDATE  # type: ignore[attr-defined]
            is not compatibility._FROZEN_VALIDATE  # type: ignore[attr-defined]
        ):
            raise RuntimeError("V2.52.03 frozen validator identity drifted")
        failure_probe._FROZEN_VALIDATE = compatibility.validate_receipt  # type: ignore[attr-defined]
        failure_probe.install_probe()


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    _bind_parent()
    return parent._read(relative, tracked=tracked)


def _read_jsonl(relative: Path, *, tracked: bool = False) -> list[dict[str, Any]]:
    _bind_parent()
    return parent._read_jsonl(relative, tracked=tracked)


def _publish_json(path: Path, value: Mapping[str, Any]) -> None:
    parent._publish_json(path, value)


def _publish_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    parent._publish_jsonl(path, rows)


def _clean_pushed() -> None:
    _bind_parent()
    parent._clean_pushed()


def _lease_inactive() -> bool:
    _bind_parent()
    return parent.parent._lease_inactive()


def _active_conflicts() -> list[int]:
    _bind_parent()
    return parent.parent._active_conflicts()


def _validate_start() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    start = _read(contract.EXECUTION_START)
    if (
        start.get("role")
        != "v25203_post_effect_tolerant_quality_execution_start"
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or start.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
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
        raise RuntimeError("V2.52.03 execution start drifted")
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
                "role": "v25203_model_slot",
                "slot": index,
                "slot_cap": contract.MODEL_SLOT_CAP,
                "contains_credential_or_benchmark_content": False,
            },
        )


def _from_runtime(*args: Any, **kwargs: Any) -> dict[str, Any]:
    _bind_parent()
    _ensure_compatibility_validation()
    return parent._from_runtime(*args, **kwargs)


def _terminal_outer_failure(*args: Any, **kwargs: Any) -> dict[str, Any]:
    _bind_parent()
    return parent._terminal_outer_failure(*args, **kwargs)


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    _bind_parent()
    _ensure_compatibility_validation()
    return parent.validate_task_row(value)


def run_one_task(task: Mapping[str, str]) -> dict[str, Any]:
    if set(task) != {"opaque_id", "question"}:
        raise ValueError("V2.52.03 runtime input must be opaque_id and question")
    _bind_parent()
    token = compatibility.begin_task()
    try:
        row = parent.run_one_task(task)
        checked = validate_task_row(row)
        applied = compatibility.compatibility_applied()
        with _APPLICATION_LOCK:
            _APPLICATIONS[str(task["opaque_id"])] = applied
        return checked
    finally:
        compatibility.end_task(token)


def _parent_invariant(value: Mapping[str, Any]) -> dict[str, Any]:
    converted = {
        "artifact_version": 1,
        "role": "v25199_invariant_observation_aggregate",
        "protocol_id": contract.PROTOCOL_ID,
        "task_count": int(value["task_count"]),
        "v25158_receipt_failure_tasks": int(
            value["residual_v25158_receipt_failure_tasks"]
        ),
        "v25158_invariant_observed_failure_tasks": int(
            value["residual_v25158_invariant_observed_failure_tasks"]
        ),
        "v25158_invariant_observer_missing_tasks": int(
            value["residual_v25158_invariant_observer_missing_tasks"]
        ),
        "violation_code_counts": copy.deepcopy(
            value["residual_v25158_violation_code_counts"]
        ),
        "violation_event_count": int(
            value["residual_v25158_violation_event_count"]
        ),
        "per_task_observation_identity_or_order_persisted": False,
        "contains_receipt_value_task_question_query_url_title_page_identity_column_key_value_prediction_semantic_hash_exception_message_traceback_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    converted["aggregate_payload_sha256"] = contract.payload_sha256(converted)
    _bind_parent()
    return parent.validate_invariant_observation_aggregate(converted)


def build_compatibility_aggregate(
    rows: Sequence[Mapping[str, Any]],
    observations: Sequence[Mapping[str, Any] | None],
    applications: Sequence[bool],
) -> dict[str, Any]:
    checked = [validate_task_row(row) for row in rows]
    if (
        len(checked) != contract.TASK_COUNT
        or len(observations) != contract.TASK_COUNT
        or len(applications) != contract.TASK_COUNT
        or any(not isinstance(applied, bool) for applied in applications)
    ):
        raise RuntimeError("V2.52.03 compatibility denominator drifted")
    _bind_parent()
    residual = parent.build_invariant_observation_aggregate(checked, observations)
    completed_applied = sum(
        applied and row["runtime_completed"]
        for row, applied in zip(checked, applications, strict=True)
    )
    outer_applied = sum(applications) - completed_applied
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25203_post_effect_compatibility_aggregate",
        "protocol_id": contract.PROTOCOL_ID,
        "task_count": contract.TASK_COUNT,
        "compatibility_applied_tasks": sum(applications),
        "compatibility_applied_runtime_completed_tasks": completed_applied,
        "compatibility_applied_outer_failure_tasks": outer_applied,
        "residual_v25158_receipt_failure_tasks": residual[
            "v25158_receipt_failure_tasks"
        ],
        "residual_v25158_invariant_observed_failure_tasks": residual[
            "v25158_invariant_observed_failure_tasks"
        ],
        "residual_v25158_invariant_observer_missing_tasks": residual[
            "v25158_invariant_observer_missing_tasks"
        ],
        "residual_v25158_violation_code_counts": copy.deepcopy(
            residual["violation_code_counts"]
        ),
        "residual_v25158_violation_event_count": residual[
            "violation_event_count"
        ],
        "per_task_compatibility_identity_or_order_persisted": False,
        "contains_receipt_value_task_question_query_url_title_page_identity_column_key_value_prediction_semantic_hash_exception_message_traceback_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["aggregate_payload_sha256"] = contract.payload_sha256(value)
    return validate_compatibility_aggregate(value)


def validate_compatibility_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("aggregate_payload_sha256", None)
    counts = (
        "task_count",
        "compatibility_applied_tasks",
        "compatibility_applied_runtime_completed_tasks",
        "compatibility_applied_outer_failure_tasks",
        "residual_v25158_receipt_failure_tasks",
        "residual_v25158_invariant_observed_failure_tasks",
        "residual_v25158_invariant_observer_missing_tasks",
        "residual_v25158_violation_event_count",
    )
    false_flags = (
        "per_task_compatibility_identity_or_order_persisted",
        "contains_receipt_value_task_question_query_url_title_page_identity_column_key_value_prediction_semantic_hash_exception_message_traceback_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    codes = copied.get("residual_v25158_violation_code_counts")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "protocol_id",
            *counts,
            "residual_v25158_violation_code_counts",
            *false_flags,
            "aggregate_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25203_post_effect_compatibility_aggregate"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or copied["task_count"] != contract.TASK_COUNT
        or copied["compatibility_applied_tasks"]
        != copied["compatibility_applied_runtime_completed_tasks"]
        + copied["compatibility_applied_outer_failure_tasks"]
        or copied["compatibility_applied_tasks"] > copied["task_count"]
        or not isinstance(codes, Mapping)
        or not set(codes).issubset(invariant_observer.VIOLATION_CODES)
        or any(
            isinstance(count, bool) or not isinstance(count, int) or count <= 0
            for count in codes.values()
        )
        or sum(codes.values())
        != copied["residual_v25158_violation_event_count"]
        or any(copied.get(name) is not False for name in false_flags)
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.52.03 compatibility aggregate drifted")
    _parent_invariant(copied)
    return copied


_COMPATIBILITY_AGGREGATE_KEYS = {
    "post_effect_compatibility_applied_tasks",
    "post_effect_compatibility_applied_runtime_completed_tasks",
    "post_effect_compatibility_applied_outer_failure_tasks",
}


def _parent_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(child)
        for key, child in value.items()
        if key not in _COMPATIBILITY_AGGREGATE_KEYS
    }


def aggregate_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    wall_seconds: float,
    compatibility_aggregate: Mapping[str, Any],
) -> dict[str, Any]:
    sidecar = validate_compatibility_aggregate(compatibility_aggregate)
    _bind_parent()
    base = parent.aggregate_rows(
        rows,
        wall_seconds=wall_seconds,
        invariant_aggregate=_parent_invariant(sidecar),
    )
    value = {
        **base,
        "post_effect_compatibility_applied_tasks": sidecar[
            "compatibility_applied_tasks"
        ],
        "post_effect_compatibility_applied_runtime_completed_tasks": sidecar[
            "compatibility_applied_runtime_completed_tasks"
        ],
        "post_effect_compatibility_applied_outer_failure_tasks": sidecar[
            "compatibility_applied_outer_failure_tasks"
        ],
    }
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if set(copied) != set(_parent_aggregate(copied)) | _COMPATIBILITY_AGGREGATE_KEYS:
        raise RuntimeError("V2.52.03 aggregate key drifted")
    for name in _COMPATIBILITY_AGGREGATE_KEYS:
        if (
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
        ):
            raise RuntimeError("V2.52.03 aggregate count drifted")
    if (
        copied["post_effect_compatibility_applied_tasks"]
        != copied["post_effect_compatibility_applied_runtime_completed_tasks"]
        + copied["post_effect_compatibility_applied_outer_failure_tasks"]
        or copied["post_effect_compatibility_applied_tasks"]
        > copied["task_count"]
    ):
        raise RuntimeError("V2.52.03 aggregate compatibility drifted")
    _bind_parent()
    parent.validate_aggregate(_parent_aggregate(copied))
    return copied


def mechanism_decision(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    checked = validate_aggregate(aggregate)
    _bind_parent()
    decision = parent.mechanism_decision(_parent_aggregate(checked))
    checks = copy.deepcopy(decision["checks"])
    checks["post_effect_compatibility_observability_complete"] = (
        checked["post_effect_compatibility_applied_outer_failure_tasks"] == 0
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
            "compatibility_aggregate_sha256",
            "aggregate",
            "mechanism_decision",
            "authorization",
            "result_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25203_post_effect_tolerant_quality_forward_result"
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
        raise RuntimeError("V2.52.03 forward result drifted")
    return copied


def run_forward() -> dict[str, Any]:
    _clean_pushed()
    protocol, start = _validate_start()
    if not _lease_inactive() or _active_conflicts():
        raise RuntimeError("V2.52.03 shared runtime is not ready")
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
        raise RuntimeError("V2.52.03 forward surface is not pristine")
    if contract.watcher_snapshot() != protocol["protected_watchers"]:
        raise RuntimeError("V2.52.03 watcher identity drifted")
    validate_search_class()
    install_runtime_observers()
    tasks = contract.task_vector()
    _prepare_output()
    with parent._OBSERVATION_LOCK:
        parent._OBSERVATIONS.clear()
    with _APPLICATION_LOCK:
        _APPLICATIONS.clear()
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
                pool.submit(run_one_task, task): index
                for index, task in enumerate(tasks)
            }
            for future in as_completed(futures):
                values[futures[future]] = future.result()
    rows = [validate_task_row(row) for row in values if row is not None]
    if len(rows) != contract.TASK_COUNT:
        raise RuntimeError("V2.52.03 terminal denominator drifted")
    with parent._OBSERVATION_LOCK:
        observations = [
            copy.deepcopy(parent._OBSERVATIONS.get(task["opaque_id"]))
            for task in tasks
        ]
    with _APPLICATION_LOCK:
        applications = [
            bool(_APPLICATIONS.get(task["opaque_id"], False)) for task in tasks
        ]
        if set(_APPLICATIONS) != {task["opaque_id"] for task in tasks}:
            raise RuntimeError("V2.52.03 compatibility observation incomplete")
    sidecar = build_compatibility_aggregate(rows, observations, applications)
    _publish_json(ROOT / contract.COMPATIBILITY_AGGREGATE, sidecar)
    _publish_jsonl(ROOT / contract.TASK_ROWS, rows)
    sidecar_sha = contract.sha256(ROOT / contract.COMPATIBILITY_AGGREGATE)
    freeze = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25203_post_effect_tolerant_quality_prediction_freeze",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "task_count": contract.TASK_COUNT,
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "compatibility_aggregate_sha256": sidecar_sha,
            "control_prediction_hash_vector_sha256": contract.payload_sha256(
                [row["prediction_sha256"][contract.CONTROL_ARM] for row in rows]
            ),
            "candidate_prediction_hash_vector_sha256": contract.payload_sha256(
                [row["prediction_sha256"][contract.CANDIDATE_ARM] for row in rows]
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
        compatibility_aggregate=sidecar,
    )
    decision = mechanism_decision(aggregate)
    forward = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25203_post_effect_tolerant_quality_forward_result",
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
            "compatibility_aggregate_sha256": sidecar_sha,
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
