#!/usr/bin/env python3
"""Run the single authorized V2.55.71 fresh constraint-totality gate."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25558_model_pool_contract as model_pool  # noqa: E402
from deepwide_agent import v25569_constraint_totality_safe_handoff_runtime as runtime  # noqa: E402
from deepwide_agent import v25571_fresh_totality_external_contract as contract  # noqa: E402
from scripts import run_v25550_visible_constraint_external as parent  # noqa: E402
from scripts import v25478_clone_safe_runner_namespace as clone_safe  # noqa: E402


TASK_ROLE = "v25571_fresh_totality_frozen_task_result"
FORWARD_ROLE = "v25571_fresh_totality_forward_result"
FREEZE_ROLE = "v25571_fresh_totality_prediction_freeze"
ARMS = runtime.ARMS


_BASE_SOURCE_NAMES = (
    "_terminal_outer_failure",
    "_from_runtime",
    "validate_task_row",
    "validate_aggregate",
    "aggregate_rows",
    "mechanism_decision",
)
_BASE_SOURCES = {name: getattr(parent, name) for name in _BASE_SOURCE_NAMES}
_BASE_NAMESPACE, _BASE_CLONES = clone_safe.clone_group(
    _BASE_SOURCES,
    visible_globals=parent.__dict__,
    overrides={
        "contract": contract,
        "runtime": runtime,
        "cap": cap,
        "TASK_ROLE": TASK_ROLE,
        "FORWARD_ROLE": FORWARD_ROLE,
        "FREEZE_ROLE": FREEZE_ROLE,
        "ARMS": ARMS,
    },
    rename_from="v25550",
    rename_to="v25571",
)

_RUN_SOURCE_NAMES = (
    "_read",
    "_publish_json",
    "_publish_jsonl",
    "_clean_pushed",
    "_lease_inactive",
    "_active_conflicts",
    "_search",
    "_empty_effect_snapshot",
    "_effect_snapshot",
    "_health",
    "_health_snapshot",
    "_validate_cost",
    "run_one_task",
    "run_forward",
)
_RUN_SOURCES = {name: getattr(parent, name) for name in _RUN_SOURCE_NAMES}
_RUN_NAMESPACE, _RUN_CLONES = clone_safe.clone_group(
    _RUN_SOURCES,
    visible_globals=parent.__dict__,
    overrides={
        "contract": contract,
        "runtime": runtime,
        "cap": cap,
        "TASK_ROLE": TASK_ROLE,
        "FORWARD_ROLE": FORWARD_ROLE,
        "FREEZE_ROLE": FREEZE_ROLE,
        "ARMS": ARMS,
        "POOL_ID": model_pool.MODEL_POOL_ID,
    },
    rename_from="v25550",
    rename_to="v25571",
)
_CLONE_NAMESPACE_RECEIPT = clone_safe.content_free_receipt(
    _RUN_SOURCES, _RUN_NAMESPACE
)
if (
    _CLONE_NAMESPACE_RECEIPT["unresolved_function_count"] != 0
    or _CLONE_NAMESPACE_RECEIPT["unresolved_global_name_count"] != 0
    or not all(
        _CLONE_NAMESPACE_RECEIPT[name]
        for name in (
            "fcntl_resolved",
            "socket_resolved",
            "subprocess_resolved",
            "thread_pool_executor_resolved",
            "as_completed_resolved",
            "lease_helper_resolved",
        )
    )
):
    raise RuntimeError("V2.55.71 clone namespace is incomplete")

for _name in (
    "_read",
    "_publish_json",
    "_publish_jsonl",
    "_clean_pushed",
    "_lease_inactive",
    "_active_conflicts",
    "_search",
    "_empty_effect_snapshot",
    "_effect_snapshot",
    "_health",
    "_health_snapshot",
    "_validate_cost",
):
    globals()[_name] = _RUN_CLONES[_name]


def clone_namespace_receipt() -> dict[str, Any]:
    return copy.deepcopy(_CLONE_NAMESPACE_RECEIPT)


def model_pool_contract() -> dict[str, Any]:
    value = model_pool.contract()
    if _RUN_NAMESPACE.get("POOL_ID") != value["model_pool_id"]:
        raise RuntimeError("V2.55.71 runner model pool wiring drifted")
    return value


def _validate_start() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    start = _read(contract.EXECUTION_START)
    expected = {
        "one_external_forward": True,
        "postfreeze_quality": False,
        "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
        "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
    }
    current = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    parents = contract.git(ROOT, "rev-list", "--parents", "-n", "1", current).split()
    changed = sorted(
        line.strip()
        for line in contract.git(
            ROOT, "diff-tree", "--no-commit-id", "--name-only", "-r", current
        ).splitlines()
        if line.strip()
    )
    if (
        start.get("role") != "v25571_fresh_totality_execution_start"
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or start.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256")
        != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("task_vector_sha256")
        != protocol["population"]["task_vector_sha256"]
        or start.get("identity_vector_sha256")
        != protocol["population"]["identity_vector_sha256"]
        or start.get("protected_watchers") != contract.watcher_snapshot()
        or start.get("authorization") != expected
        or not contract.sealed(start, "execution_start_payload_sha256")
        or current != target
        or len(parents) != 2
        or parents[1] != start.get("git_head")
        or changed != [str(contract.EXECUTION_START)]
    ):
        raise RuntimeError("V2.55.71 execution start drifted")
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
                "role": "v25571_model_slot",
                "slot": index,
                "slot_cap": contract.MODEL_SLOT_CAP,
                "contains_credential_or_benchmark_content": False,
            },
        )


def _columns(_question: str) -> tuple[str, ...]:
    return contract.population.DATE_COLUMNS


def _fallback_prediction(question: str) -> str:
    del question
    columns = contract.population.DATE_COLUMNS
    return (
        "```markdown\n| "
        + " | ".join(columns)
        + " |\n| "
        + " | ".join("---" for _ in columns)
        + " |\n| "
        + " | ".join("Unknown" for _ in columns)
        + " |\n| "
        + " | ".join("Unknown" for _ in columns)
        + " |\n```"
    )


def _task_metadata() -> dict[str, int]:
    output = {
        task["opaque_id"]: index for index, task in enumerate(contract.task_vector())
    }
    if len(output) != contract.TASK_COUNT:
        raise RuntimeError("V2.55.71 task metadata drifted")
    return output


def _metadata(task: Mapping[str, str]) -> int:
    index = _task_metadata().get(str(task.get("opaque_id")))
    if index is None or dict(task) != contract.task_vector()[index]:
        raise ValueError("V2.55.71 task is outside frozen population")
    return index


_BASE_NAMESPACE.update(
    {
        "_fallback_prediction": _fallback_prediction,
        "_task_metadata": _task_metadata,
        "_metadata": _metadata,
    }
)


def _decode_completed(
    result: Mapping[str, Any], stage: Mapping[str, Any]
) -> dict[str, Any]:
    checked = runtime.validate_result(result)
    checked_stage = runtime.validate_stage_receipt(stage)
    parent_result = runtime.parent.validate_result(checked["private_parent_result"])
    parent_stage = runtime.parent.validate_stage_receipt(
        checked_stage["parent_stage_receipt"]
    )
    raw_constrained = checked.get("private_constrained_result")
    constrained_result = (
        runtime.constrained.validate_result(raw_constrained)
        if isinstance(raw_constrained, Mapping)
        else None
    )
    receipt = runtime.validate_receipt(
        checked["constraint_totality_receipt"],
        parent_result=parent_result,
        constrained_result=constrained_result,
    )
    budget = cap.validate_budget_receipt(
        checked_stage["outer_physical_budget_receipt"]
    )
    predictions = copy.deepcopy(checked["predictions"])
    admitted = checked["mode"] == runtime.CANONICAL_PROJECTION
    if admitted:
        if constrained_result is None:
            raise ValueError("V2.55.71 canonical projection is absent")
        visible = runtime.contracts.validate_contract(
            constrained_result["private_visible_constraint_contract"]
        )
        native_receipt = runtime.constrained.validate_receipt(
            constrained_result["deterministic_visible_constraint_receipt"],
            parent_result=parent_result,
            contract=visible,
            projection=runtime.constrained.projector.build_projection(
                predictions[runtime.CONTROL_ARM], visible
            ),
        )
        projection = runtime.constrained.projector.validate_receipt(
            native_receipt["projection_receipt"]
        )
        constrained_stage = runtime.constrained.validate_stage_receipt(
            checked_stage["constrained_stage_receipt"]
        )
        if (
            constrained_stage["runtime_result_payload_sha256"]
            != constrained_result["result_payload_sha256"]
            or constrained_stage["parent_stage_receipt"] != parent_stage
        ):
            raise ValueError("V2.55.71 constrained stage binding drifted")
    else:
        visible = {
            "active_family_count": 0,
            "date_format": None,
            "numeric_scale": None,
            "explicit_order": None,
        }
        projection = {
            "candidate_prediction_changed": False,
            "date_cell_changed_count": 0,
            "scale_cell_changed_count": 0,
            "sort_applied_count": 0,
            "sort_already_satisfied_count": 0,
            "sort_rejected_count": 0,
        }
        constrained_stage = None
    adapted_receipt = {
        **copy.deepcopy(receipt),
        "constraint_active": receipt["active_family_count"] > 0,
    }
    safe_handoff = bool(
        not admitted
        and checked["byte_exact_parent_handoff"]
        and constrained_result is None
        and constrained_stage is None
        and predictions[runtime.CONTROL_ARM] == parent_result["prediction"]
        and predictions[runtime.CANDIDATE_ARM] == parent_result["prediction"]
        and not checked["candidate_prediction_changed"]
        and all(
            receipt[name] == 0
            for name in (
                "active_family_count",
                "date_cell_changed_count",
                "scale_cell_changed_count",
                "sort_applied_count",
            )
        )
    )
    if (
        parent_result["result_payload_sha256"]
        != checked["private_parent_result_payload_sha256"]
        or checked_stage["parent_runtime_result_payload_sha256"]
        != parent_result["result_payload_sha256"]
        or checked_stage["runtime_result_payload_sha256"]
        != checked["result_payload_sha256"]
        or parent_stage["outer_physical_budget_receipt"] != budget
        or predictions[runtime.CONTROL_ARM] != parent_result["prediction"]
        or predictions[runtime.CANDIDATE_ARM] != checked["prediction"]
        or checked["candidate_prediction_changed"]
        is not (
            predictions[runtime.CONTROL_ARM]
            != predictions[runtime.CANDIDATE_ARM]
        )
        or receipt["mode"] != checked["mode"]
        or (not admitted and not safe_handoff)
    ):
        raise ValueError("V2.55.71 shared-parent totality chain drifted")
    return {
        "result": checked,
        "stage": checked_stage,
        "parent_result": parent_result,
        "parent_stage": parent_stage,
        "visible_contract": visible,
        "runtime_receipt": adapted_receipt,
        "projection_receipt": projection,
        "budget": budget,
        "predictions": predictions,
        "mode": checked["mode"],
        "canonical_projection": admitted,
        "byte_exact_parent_handoff": not admitted,
        "safe_handoff": safe_handoff,
        "nonadmission_reason": checked["nonadmission_reason"],
    }


_BASE_NAMESPACE["_decode_completed"] = _decode_completed

_TOTALITY_FIELDS = (
    "projection_mode",
    "canonical_projection",
    "byte_exact_parent_handoff",
    "parent_prediction_byte_preserved",
    "safe_handoff",
    "unsafe_handoff_present",
    "nonadmission_reason",
    "handoff_date_scale_sort_modification_present",
)


def _base_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    base = copy.deepcopy(dict(value))
    for name in _TOTALITY_FIELDS:
        base.pop(name, None)
    base.pop("result_payload_sha256", None)
    return contract.seal(base, "result_payload_sha256")


def _totality_fields_for_row(base: Mapping[str, Any]) -> dict[str, Any]:
    if base["runtime_completed"]:
        decoded = _decode_completed(
            base["runtime_result"], base["content_free_stage_receipt"]
        )
        handoff = decoded["byte_exact_parent_handoff"]
        modification = handoff and any(
            int(base[name]) > 0
            for name in (
                "date_cell_changed_count",
                "scale_cell_changed_count",
                "sort_applied_count",
                "sort_already_satisfied_count",
                "sort_rejected_count",
            )
        )
        return {
            "projection_mode": decoded["mode"],
            "canonical_projection": decoded["canonical_projection"],
            "byte_exact_parent_handoff": handoff,
            "parent_prediction_byte_preserved": (
                decoded["predictions"][runtime.CONTROL_ARM]
                == decoded["parent_result"]["prediction"]
            ),
            "safe_handoff": decoded["safe_handoff"],
            "unsafe_handoff_present": handoff and not decoded["safe_handoff"],
            "nonadmission_reason": decoded["nonadmission_reason"],
            "handoff_date_scale_sort_modification_present": modification,
        }
    return {
        "projection_mode": None,
        "canonical_projection": False,
        "byte_exact_parent_handoff": False,
        "parent_prediction_byte_preserved": False,
        "safe_handoff": False,
        "unsafe_handoff_present": False,
        "nonadmission_reason": None,
        "handoff_date_scale_sort_modification_present": False,
    }


def _extend_task_row(base: Mapping[str, Any]) -> dict[str, Any]:
    checked_base = _BASE_CLONES["validate_task_row"](_base_task_row(base))
    value = copy.deepcopy(checked_base)
    value.pop("result_payload_sha256")
    value.update(_totality_fields_for_row(checked_base))
    return contract.seal(value, "result_payload_sha256")


def _terminal_outer_failure(
    task: Mapping[str, str],
    exc: BaseException,
    elapsed: float,
    *,
    budget: cap.PhysicalEffectBudget | None,
    health: Mapping[str, int] | None,
) -> dict[str, Any]:
    base = _BASE_CLONES["_terminal_outer_failure"](
        task, exc, elapsed, budget=budget, health=health
    )
    return validate_task_row(_extend_task_row(base))


def _from_runtime(
    task: Mapping[str, str],
    value: Mapping[str, Any],
    stage: Mapping[str, Any],
    *,
    elapsed: float,
    budget: cap.PhysicalEffectBudget,
    health: Mapping[str, int] | None,
) -> dict[str, Any]:
    base = _BASE_CLONES["_from_runtime"](
        task,
        value,
        stage,
        elapsed=elapsed,
        budget=budget,
        health=health,
    )
    return validate_task_row(_extend_task_row(base))


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    base = _BASE_CLONES["validate_task_row"](_base_task_row(copied))
    expected_fields = _totality_fields_for_row(base)
    if (
        set(copied) != set(base) | set(_TOTALITY_FIELDS)
        or any(copied.get(name) != expected for name, expected in expected_fields.items())
        or copied.get("unsafe_handoff_present") is not False
        or copied.get("handoff_date_scale_sort_modification_present") is not False
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise ValueError("V2.55.71 task row drifted")
    return copied


_TOTALITY_AGGREGATE_FIELDS = (
    "canonical_projection_tasks",
    "byte_exact_parent_handoff_tasks",
    "safe_handoff_tasks",
    "unsafe_handoff_tasks",
    "parent_prediction_byte_preserved_tasks",
    "handoff_date_scale_sort_modification_tasks",
)


def _base_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    base = copy.deepcopy(dict(value))
    for name in _TOTALITY_AGGREGATE_FIELDS:
        base.pop(name, None)
    return base


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    base = _BASE_CLONES["validate_aggregate"](_base_aggregate(copied))
    completed = base["completed_runtime_tasks"]
    if (
        set(copied) != set(base) | set(_TOTALITY_AGGREGATE_FIELDS)
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in _TOTALITY_AGGREGATE_FIELDS
        )
        or copied["canonical_projection_tasks"]
        + copied["byte_exact_parent_handoff_tasks"]
        != completed
        or copied["safe_handoff_tasks"]
        + copied["unsafe_handoff_tasks"]
        != copied["byte_exact_parent_handoff_tasks"]
        or copied["parent_prediction_byte_preserved_tasks"] != completed
        or copied["unsafe_handoff_tasks"] != 0
        or copied["handoff_date_scale_sort_modification_tasks"] != 0
    ):
        raise ValueError("V2.55.71 aggregate drifted")
    return copied


def aggregate_rows(
    rows: Sequence[Mapping[str, Any]], *, wall_seconds: float
) -> dict[str, Any]:
    checked = [validate_task_row(row) for row in rows]
    base_rows = [_base_task_row(row) for row in checked]
    value = _BASE_CLONES["aggregate_rows"](
        base_rows, wall_seconds=wall_seconds
    )
    value.update(
        {
            "canonical_projection_tasks": sum(
                row["canonical_projection"] for row in checked
            ),
            "byte_exact_parent_handoff_tasks": sum(
                row["byte_exact_parent_handoff"] for row in checked
            ),
            "safe_handoff_tasks": sum(row["safe_handoff"] for row in checked),
            "unsafe_handoff_tasks": sum(
                row["unsafe_handoff_present"] for row in checked
            ),
            "parent_prediction_byte_preserved_tasks": sum(
                row["parent_prediction_byte_preserved"] for row in checked
            ),
            "handoff_date_scale_sort_modification_tasks": sum(
                row["handoff_date_scale_sort_modification_present"]
                for row in checked
            ),
        }
    )
    return validate_aggregate(value)


def mechanism_decision(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    value = validate_aggregate(aggregate)
    decision = _BASE_CLONES["mechanism_decision"](_base_aggregate(value))
    gate = contract.mechanism_gate()
    totality_checks = {
        "completed_mode_accounting_exact": (
            value["canonical_projection_tasks"]
            + value["byte_exact_parent_handoff_tasks"]
            == value["completed_runtime_tasks"]
        ),
        "minimum_canonical_projection_tasks": value["canonical_projection_tasks"]
        >= gate["minimum_canonical_projection_tasks"],
        "all_completed_parent_predictions_byte_preserved": value[
            "parent_prediction_byte_preserved_tasks"
        ]
        == value["completed_runtime_tasks"],
        "all_handoffs_safe": value["safe_handoff_tasks"]
        == value["byte_exact_parent_handoff_tasks"],
        "zero_unsafe_handoff": value["unsafe_handoff_tasks"]
        <= gate["maximum_unsafe_handoff_tasks"],
        "handoff_never_reports_date_scale_or_sort_modification": value[
            "handoff_date_scale_sort_modification_tasks"
        ]
        == 0,
    }
    checks = {**decision["checks"], **totality_checks}
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        **decision,
        "checks": checks,
        "failed_checks": failed,
        "mechanism_gate_passed": not failed,
        "postfreeze_quality_protocol_authorized": not failed,
    }


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    aggregate = copied.get("aggregate")
    if (
        copied.get("role") != FORWARD_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or not isinstance(aggregate, Mapping)
        or validate_aggregate(aggregate) != dict(aggregate)
        or copied.get("mechanism_decision") != mechanism_decision(aggregate)
        or copied.get("authorization")
        != {
            "forward_audit": True,
            "postfreeze_quality_protocol": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        }
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise ValueError("V2.55.71 forward result drifted")
    return copied


_RUN_NAMESPACE.update(
    {
        "_validate_start": _validate_start,
        "_prepare_output": _prepare_output,
        "_fallback_prediction": _fallback_prediction,
        "_task_metadata": _task_metadata,
        "_metadata": _metadata,
        "_decode_completed": _decode_completed,
        "_terminal_outer_failure": _terminal_outer_failure,
        "_from_runtime": _from_runtime,
        "validate_task_row": validate_task_row,
        "validate_aggregate": validate_aggregate,
        "aggregate_rows": aggregate_rows,
        "mechanism_decision": mechanism_decision,
        "validate_forward_result": validate_forward_result,
    }
)
run_one_task = _RUN_CLONES["run_one_task"]
run_forward = _RUN_CLONES["run_forward"]


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
