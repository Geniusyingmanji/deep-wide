#!/usr/bin/env python3
"""Run one canonical-column-total label-blind exact-220 forward."""

from __future__ import annotations

import json
import os
import re
import time
import copy
import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
import sys

for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25375_schema_total_changed_safe_runtime as visible_schema  # noqa: E402
from deepwide_agent import v25575_canonical_column_totality_runtime as runtime  # noqa: E402
from deepwide_agent import v25581_canonical_totality_exact220_contract as contract  # noqa: E402
from scripts import run_v25267_production_only_exact220 as base  # noqa: E402


TASK_ROLE = "v25581_canonical_totality_exact220_task_result"
ATTEMPT_ROLE = "v25581_canonical_totality_exact220_attempt_claim"
START_ROLE = "v25581_canonical_totality_exact220_execution_start"
PROGRESS_ROLE = "v25581_canonical_totality_exact220_safe_progress"
_INHERITED_TERMINAL_OUTER_FAILURE = base._terminal_outer_failure
_INHERITED_FROM_RUNTIME = base._from_runtime
_INHERITED_VALIDATE_TASK_ROW = base.validate_task_row
_INHERITED_AGGREGATE_ROWS = base.aggregate_rows
_INHERITED_VALIDATE_AGGREGATE = base.validate_aggregate

_TOTALITY_FIELDS = (
    "projection_mode",
    "canonical_projection",
    "canonical_column_handoff",
    "byte_exact_parent_handoff",
    "parent_prediction_byte_preserved",
    "safe_handoff",
    "unsafe_handoff_present",
    "nonadmission_reason",
    "handoff_date_scale_sort_modification_present",
)
_TOTALITY_AGGREGATE_FIELDS = (
    "canonical_projection_tasks",
    "canonical_column_handoff_tasks",
    "byte_exact_parent_handoff_tasks",
    "safe_handoff_tasks",
    "unsafe_handoff_tasks",
    "parent_prediction_byte_preserved_tasks",
    "handoff_date_scale_sort_modification_tasks",
)


def _terminal_outer_failure(
    task: Mapping[str, str],
    exc: BaseException,
    elapsed: float,
    budget: Any,
    model: Any,
    searches: Mapping[str, Any],
) -> dict[str, Any]:
    """Keep outer-failure totality across the V2.54.01/V2.55.69 boundary.

    V2.55.69 aliases its parent's V2.53.75 failure exception, whose attached
    receipt predates the V2.55.69 wrapper schema.  The receipt is private and
    optional on an outer-failure row; the physical budget and actual effect
    snapshots remain mandatory.  Drop only that incompatible private receipt.
    """

    configure()
    value = _INHERITED_TERMINAL_OUTER_FAILURE(
        task, exc, elapsed, budget, model, searches
    )
    copied = dict(value)
    copied.pop("result_payload_sha256", None)
    copied["content_free_stage_receipt"] = None
    return _extend_task_row(contract.seal(copied, "result_payload_sha256"))


def _validate_start() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = contract.validate_protocol(ROOT, base._read(contract.PROTOCOL))
    start = base._read(contract.EXECUTION_START)
    if (
        start.get("role") != START_ROLE
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or start.get("status") != "authorized_not_started"
        or re.fullmatch(r"[0-9a-f]{40}", str(start.get("git_head") or "")) is None
        or start.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256") != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("selected") != contract.TASK_COUNT
        or start.get("executor_concurrency") != contract.EXECUTOR_CONCURRENCY
        or start.get("model_slot_cap") != contract.MODEL_SLOT_CAP
        or start.get("runtime_input_contract") != ["opaque_id", "question"]
        or start.get("truthful_physical_caps") != contract.PHYSICAL_CAPS
        or start.get("protected_watchers") != contract.watcher_snapshot()
        or start.get("findings") != []
        or start.get("authorization")
        != {
            "single_exact220_forward": True,
            "postfreeze_official_evaluator": False,
            "retry_resume_skip_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or not contract.sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.55.81 execution start drifted")
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
        current != target
        or len(parents) != 2
        or parents[1] != start["git_head"]
        or changed != [str(contract.EXECUTION_START)]
    ):
        raise RuntimeError("V2.55.81 execution-start commit boundary drifted")
    return protocol, start


def _atomic_progress(completed: int) -> None:
    value = contract.seal(
        {
            "artifact_version": 1,
            "role": PROGRESS_ROLE,
            "created_at_unix": int(time.time()),
            "selected": contract.TASK_COUNT,
            "completed": int(completed),
            "unfinished": contract.TASK_COUNT - int(completed),
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


def configure() -> None:
    base.contract = contract
    base.runtime = runtime
    # The inherited fixed-denominator shell uses ``visible_schema`` only for
    # its conservative outer-failure table.  V2.53.75 is a runtime adapter;
    # its frozen exact parser lives in ``exact_schema``.
    base.visible_schema = visible_schema.exact_schema
    base.TASK_ROLE = TASK_ROLE
    base.ATTEMPT_ROLE = ATTEMPT_ROLE
    base._validate_start = _validate_start
    base._atomic_progress = _atomic_progress
    base._terminal_outer_failure = _terminal_outer_failure


def _base_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    for name in _TOTALITY_FIELDS:
        copied.pop(name, None)
    copied.pop("result_payload_sha256", None)
    return contract.seal(copied, "result_payload_sha256")


def _decode_totality(result: Mapping[str, Any], stage: Mapping[str, Any]) -> dict[str, Any]:
    checked, checked_stage = runtime.validate_runtime_pair(result, stage)
    canonical_column = checked["role"] == runtime.HANDOFF_ROLE
    if canonical_column:
        parent = runtime.membership_parent.validate_result(
            checked["private_parent_result"]
        )
        receipt = runtime.validate_handoff_receipt(
            checked["canonical_column_handoff_receipt"], parent_result=parent
        )
    else:
        parent = runtime.totality.parent.validate_result(
            checked["private_parent_result"]
        )
        receipt = runtime.totality.validate_receipt(
            checked["constraint_totality_receipt"],
            parent_result=parent,
            constrained_result=checked.get("private_constrained_result"),
        )
    predictions = checked["predictions"]
    admitted = checked["mode"] == runtime.CANONICAL_PROJECTION
    handoff = checked["mode"] == runtime.BYTE_EXACT_PARENT_HANDOFF
    safe = bool(
        handoff
        and predictions[runtime.CONTROL_ARM] == parent["prediction"]
        and predictions[runtime.CANDIDATE_ARM] == parent["prediction"]
        and checked["prediction"] == parent["prediction"]
        and checked["candidate_prediction_changed"] is False
        and (
            canonical_column
            or (
                checked["private_constrained_result"] is None
                and checked_stage["constrained_stage_receipt"] is None
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
        )
    )
    if (
        checked_stage["runtime_result_payload_sha256"]
        != checked["result_payload_sha256"]
        or checked_stage["parent_runtime_result_payload_sha256"]
        != parent["result_payload_sha256"]
        or predictions[runtime.CONTROL_ARM] != parent["prediction"]
        or predictions[runtime.CANDIDATE_ARM] != checked["prediction"]
        or admitted is handoff
        or (handoff and not safe)
    ):
        raise ValueError("V2.55.81 totality chain drifted")
    modification = handoff and not canonical_column and any(
        receipt[name] > 0
        for name in (
            "date_cell_changed_count",
            "scale_cell_changed_count",
            "sort_applied_count",
        )
    )
    return {
        "projection_mode": checked["mode"],
        "canonical_projection": admitted,
        "canonical_column_handoff": canonical_column,
        "byte_exact_parent_handoff": handoff,
        "parent_prediction_byte_preserved": (
            predictions[runtime.CONTROL_ARM] == parent["prediction"]
        ),
        "safe_handoff": safe,
        "unsafe_handoff_present": handoff and not safe,
        "nonadmission_reason": checked["nonadmission_reason"],
        "handoff_date_scale_sort_modification_present": modification,
    }


def _totality_fields(value: Mapping[str, Any]) -> dict[str, Any]:
    if value["runtime_completed"]:
        return _decode_totality(
            value["runtime_result"], value["content_free_stage_receipt"]
        )
    return {
        "projection_mode": None,
        "canonical_projection": False,
        "canonical_column_handoff": False,
        "byte_exact_parent_handoff": False,
        "parent_prediction_byte_preserved": False,
        "safe_handoff": False,
        "unsafe_handoff_present": False,
        "nonadmission_reason": None,
        "handoff_date_scale_sort_modification_present": False,
    }


def _extend_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    base_row = _INHERITED_VALIDATE_TASK_ROW(_base_task_row(value))
    copied = copy.deepcopy(base_row)
    copied.pop("result_payload_sha256")
    copied.update(_totality_fields(base_row))
    return contract.seal(copied, "result_payload_sha256")


def _from_runtime(
    task: Mapping[str, str], result: Mapping[str, Any], stage: Mapping[str, Any],
    elapsed: float, budget: Any, model: Any, searches: Mapping[str, Any],
) -> dict[str, Any]:
    configure()
    value = _INHERITED_FROM_RUNTIME(
        task, result, stage, elapsed, budget, model, searches
    )
    return validate_task_row(_extend_task_row(value))


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    configure()
    copied = copy.deepcopy(dict(value))
    base_row = _INHERITED_VALIDATE_TASK_ROW(_base_task_row(copied))
    expected = _totality_fields(base_row)
    if (
        set(copied) != set(base_row) | set(_TOTALITY_FIELDS)
        or any(copied.get(name) != item for name, item in expected.items())
        or copied.get("unsafe_handoff_present") is not False
        or copied.get("handoff_date_scale_sort_modification_present") is not False
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise ValueError("V2.55.81 totality task row drifted")
    return copied


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    configure()
    copied = copy.deepcopy(dict(value))
    inherited = {
        name: item
        for name, item in copied.items()
        if name not in _TOTALITY_AGGREGATE_FIELDS
    }
    checked_base = _INHERITED_VALIDATE_AGGREGATE(inherited)
    checked = {**checked_base, **{name: copied.get(name) for name in _TOTALITY_AGGREGATE_FIELDS}}
    if checked["maximum_model_forwards_on_one_task"] > 3:
        raise ValueError("V2.55.81 three-model physical cap drifted")
    completed = checked["completed_runtime_tasks"]
    if (
        set(copied) != set(checked_base) | set(_TOTALITY_AGGREGATE_FIELDS)
        or any(
            isinstance(checked.get(name), bool)
            or not isinstance(checked.get(name), int)
            or checked[name] < 0
            for name in _TOTALITY_AGGREGATE_FIELDS
        )
        or checked["canonical_projection_tasks"]
        + checked["byte_exact_parent_handoff_tasks"]
        != completed
        or checked["canonical_column_handoff_tasks"]
        > checked["byte_exact_parent_handoff_tasks"]
        or checked["safe_handoff_tasks"] + checked["unsafe_handoff_tasks"]
        != checked["byte_exact_parent_handoff_tasks"]
        or checked["parent_prediction_byte_preserved_tasks"] != completed
        or checked["unsafe_handoff_tasks"] != 0
        or checked["handoff_date_scale_sort_modification_tasks"] != 0
    ):
        raise ValueError("V2.55.81 totality aggregate drifted")
    return checked


def validate_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    configure()
    return base.validate_summary(value)


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    configure()
    base.validate_aggregate = validate_aggregate
    checked = base.validate_forward_result(value)
    validate_aggregate(checked["aggregate"])
    return checked


def validate_attempt_claim(value: Mapping[str, Any]) -> dict[str, Any]:
    configure()
    return base.validate_attempt_claim(value)


def run_one_task(task: Mapping[str, str]) -> dict[str, Any]:
    if set(task) != {"opaque_id", "question"}:
        raise ValueError("V2.55.81 runtime input must be opaque_id and question")
    configure()
    base._from_runtime = _from_runtime
    base.validate_task_row = validate_task_row
    return base.run_one_task(task)


def aggregate_rows(
    rows: list[Mapping[str, Any]], *, wall_seconds: float
) -> dict[str, Any]:
    configure()
    checked = [validate_task_row(row) for row in rows]
    inherited_rows = [_base_task_row(row) for row in checked]
    previous_task_validator = base.validate_task_row
    previous_aggregate_validator = base.validate_aggregate
    try:
        # The inherited aggregation resolves validators through module globals.
        # Isolate the frozen base schema, then enrich and validate below.
        base.validate_task_row = _INHERITED_VALIDATE_TASK_ROW
        base.validate_aggregate = _INHERITED_VALIDATE_AGGREGATE
        value = _INHERITED_AGGREGATE_ROWS(
            inherited_rows, wall_seconds=wall_seconds
        )
    finally:
        base.validate_task_row = previous_task_validator
        base.validate_aggregate = previous_aggregate_validator
    value.update(
        {
            "canonical_projection_tasks": sum(row["canonical_projection"] for row in checked),
            "canonical_column_handoff_tasks": sum(row["canonical_column_handoff"] for row in checked),
            "byte_exact_parent_handoff_tasks": sum(row["byte_exact_parent_handoff"] for row in checked),
            "safe_handoff_tasks": sum(row["safe_handoff"] for row in checked),
            "unsafe_handoff_tasks": sum(row["unsafe_handoff_present"] for row in checked),
            "parent_prediction_byte_preserved_tasks": sum(row["parent_prediction_byte_preserved"] for row in checked),
            "handoff_date_scale_sort_modification_tasks": sum(
                row["handoff_date_scale_sort_modification_present"] for row in checked
            ),
        }
    )
    return validate_aggregate(value)


def run_forward() -> dict[str, Any]:
    configure()
    base._from_runtime = _from_runtime
    base.validate_task_row = validate_task_row
    base.aggregate_rows = aggregate_rows
    base.validate_aggregate = validate_aggregate
    return validate_forward_result(base.run_forward())


AGGREGATE_INTS = (*base.AGGREGATE_INTS, *_TOTALITY_AGGREGATE_FIELDS)


def main() -> None:
    value = run_forward()
    print(
        json.dumps(
            {
                "path": str(contract.FORWARD_RESULT),
                "selected": value["selected"],
                "terminal_predictions": value["terminal_predictions"],
                "model_generated_tables": value["model_generated_tables"],
                "fallback_tables": value["fallback_tables"],
                "forward_wall_seconds": value["forward_wall_seconds"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
