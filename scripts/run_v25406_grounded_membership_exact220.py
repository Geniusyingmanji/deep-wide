#!/usr/bin/env python3
"""Run one grounded-membership label-blind exact-220 forward."""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
import sys

for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25375_schema_total_changed_safe_runtime as visible_schema  # noqa: E402
from deepwide_agent import v25401_grounded_record_membership_runtime as runtime  # noqa: E402
from deepwide_agent import v25406_grounded_membership_exact220_contract as contract  # noqa: E402
from scripts import run_v25267_production_only_exact220 as base  # noqa: E402


TASK_ROLE = "v25406_grounded_membership_exact220_task_result"
ATTEMPT_ROLE = "v25406_grounded_membership_exact220_attempt_claim"
START_ROLE = "v25406_grounded_membership_exact220_execution_start"
PROGRESS_ROLE = "v25406_grounded_membership_exact220_safe_progress"


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
        raise RuntimeError("V2.54.06 execution start drifted")
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
        raise RuntimeError("V2.54.06 execution-start commit boundary drifted")
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


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    configure()
    return base.validate_task_row(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    configure()
    checked = base.validate_aggregate(value)
    if checked["maximum_model_forwards_on_one_task"] > 3:
        raise ValueError("V2.54.06 three-model physical cap drifted")
    return checked


def validate_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    configure()
    return base.validate_summary(value)


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    configure()
    checked = base.validate_forward_result(value)
    validate_aggregate(checked["aggregate"])
    return checked


def validate_attempt_claim(value: Mapping[str, Any]) -> dict[str, Any]:
    configure()
    return base.validate_attempt_claim(value)


def run_one_task(task: Mapping[str, str]) -> dict[str, Any]:
    if set(task) != {"opaque_id", "question"}:
        raise ValueError("V2.54.06 runtime input must be opaque_id and question")
    configure()
    return base.run_one_task(task)


def aggregate_rows(
    rows: list[Mapping[str, Any]], *, wall_seconds: float
) -> dict[str, Any]:
    configure()
    return validate_aggregate(base.aggregate_rows(rows, wall_seconds=wall_seconds))


def run_forward() -> dict[str, Any]:
    configure()
    return validate_forward_result(base.run_forward())


AGGREGATE_INTS = base.AGGREGATE_INTS


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
