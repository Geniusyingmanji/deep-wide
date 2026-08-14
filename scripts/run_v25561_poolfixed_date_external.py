#!/usr/bin/env python3
"""Run the single authorized V2.55.61 fresh visible-date gate."""

from __future__ import annotations

import copy
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25545_deterministic_visible_constraint_runtime as runtime  # noqa: E402
from deepwide_agent import v25558_model_pool_contract as model_pool  # noqa: E402
from deepwide_agent import v25561_poolfixed_date_external_contract as contract  # noqa: E402
from scripts import run_v25550_visible_constraint_external as parent  # noqa: E402
from scripts import v25478_clone_safe_runner_namespace as clone_safe  # noqa: E402


TASK_ROLE = "v25561_fresh_date_frozen_task_result"
FORWARD_ROLE = "v25561_poolfixed_date_forward_result"
FREEZE_ROLE = "v25561_fresh_date_prediction_freeze"
ARMS = runtime.ARMS

_SOURCE_NAMES = (
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
    "_decode_completed",
    "_terminal_outer_failure",
    "_from_runtime",
    "validate_task_row",
    "validate_aggregate",
    "aggregate_rows",
    "mechanism_decision",
    "validate_forward_result",
)
_SOURCE_FUNCTIONS = {name: getattr(parent, name) for name in _SOURCE_NAMES}
_NAMESPACE, _CLONES = clone_safe.clone_group(
    _SOURCE_FUNCTIONS,
    visible_globals=parent.__dict__,
    overrides={
        "contract": contract,
        "runtime": runtime,
        "TASK_ROLE": TASK_ROLE,
        "FORWARD_ROLE": FORWARD_ROLE,
        "FREEZE_ROLE": FREEZE_ROLE,
        "ARMS": ARMS,
        "POOL_ID": model_pool.MODEL_POOL_ID,
    },
    rename_from="v25550",
    rename_to="v25561",
)
_CLONE_NAMESPACE_RECEIPT = clone_safe.content_free_receipt(
    _SOURCE_FUNCTIONS, _NAMESPACE
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
    raise RuntimeError("V2.55.61 clone namespace is incomplete")

globals().update(_CLONES)


def clone_namespace_receipt() -> dict[str, Any]:
    return copy.deepcopy(_CLONE_NAMESPACE_RECEIPT)


def model_pool_contract() -> dict[str, Any]:
    value = model_pool.contract()
    if _NAMESPACE.get("POOL_ID") != value["model_pool_id"]:
        raise RuntimeError("V2.55.61 runner model pool wiring drifted")
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
        start.get("role") != "v25561_poolfixed_date_execution_start"
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
        raise RuntimeError("V2.55.61 execution start drifted")
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
                "role": "v25561_model_slot",
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
        raise RuntimeError("V2.55.61 task metadata drifted")
    return output


def _metadata(task: Mapping[str, str]) -> int:
    index = _task_metadata().get(str(task.get("opaque_id")))
    if index is None or dict(task) != contract.task_vector()[index]:
        raise ValueError("V2.55.61 task is outside frozen population")
    return index


_NAMESPACE.update(
    {
        "_validate_start": _validate_start,
        "_prepare_output": _prepare_output,
        "_columns": _columns,
        "_fallback_prediction": _fallback_prediction,
        "_task_metadata": _task_metadata,
        "_metadata": _metadata,
        **{
            name: _CLONES[name]
            for name in (
                "_decode_completed",
                "_terminal_outer_failure",
                "_from_runtime",
                "validate_task_row",
                "validate_aggregate",
                "aggregate_rows",
                "mechanism_decision",
                "validate_forward_result",
            )
        },
    }
)
globals().update(
    {
        name: _NAMESPACE[name]
        for name in (
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
            "_decode_completed",
            "_terminal_outer_failure",
            "_from_runtime",
            "validate_task_row",
            "validate_aggregate",
            "aggregate_rows",
            "mechanism_decision",
            "validate_forward_result",
        )
    }
)
run_one_task = _CLONES["run_one_task"]
run_forward = _CLONES["run_forward"]


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
