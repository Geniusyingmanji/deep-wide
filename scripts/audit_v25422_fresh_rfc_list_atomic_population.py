#!/usr/bin/env python3
"""Aggregate-only history audit for the V2.54.21 fresh RFC population."""

from __future__ import annotations

import copy
import functools
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25421_fresh_rfc_list_atomic_population as population  # noqa: E402


DATE = "20260813"
ROLE = "v25422_fresh_rfc_list_atomic_population_aggregate_history_audit"
SOURCE = Path("scripts/audit_v25422_fresh_rfc_list_atomic_population.py")
TEST = Path("tests/test_audit_v25422_fresh_rfc_list_atomic_population.py")
OUTPUT = Path(
    f"results/v25422_fresh_rfc_list_atomic_population_audit_v1_{DATE}.json"
)
SEARCH_PATHS = (
    "src",
    "scripts",
    "tests",
    "results",
    "outputs",
    "plan.md",
    "survey.md",
)
CANDIDATE_INTERVALS = (
    (9480, 9559),
    (9560, 9639),
    (9640, 9719),
    (9720, 9799),
)
EXPECTED_COUNTS = {
    "RFC 9480-9559": {"tree_matches": 19, "history_introductions": 3},
    "RFC 9560-9639": {"tree_matches": 18, "history_introductions": 3},
    "RFC 9640-9719": {"tree_matches": 21, "history_introductions": 4},
    "RFC 9720-9799": {"tree_matches": 0, "history_introductions": 0},
}


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
        check=check,
    )


def _pattern(start: int, end: int) -> str:
    numbers = "|".join(str(value) for value in range(start, end + 1))
    return rf"(RFC ({numbers})|rfc-({numbers}))([^0-9]|$)"


@functools.lru_cache(maxsize=None)
def _aggregate_scan(start: int, end: int) -> dict[str, int]:
    pattern = _pattern(start, end)
    parent = population.FRESHNESS_PARENT_COMMIT
    tree = _git(
        "grep",
        "-E",
        "-n",
        pattern,
        parent,
        "--",
        *SEARCH_PATHS,
        check=False,
    )
    if tree.returncode not in {0, 1}:
        raise RuntimeError("V2.54.22 parent-tree identity scan failed")
    history = _git(
        "log",
        "--format=%H",
        f"-G{pattern}",
        parent,
        "--",
        *SEARCH_PATHS,
    )
    return {
        "tree_matches": sum(bool(line.strip()) for line in tree.stdout.splitlines()),
        "history_introductions": len(
            {line.strip() for line in history.stdout.splitlines() if line.strip()}
        ),
    }


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    parent = _git("rev-parse", population.FRESHNESS_PARENT_COMMIT).stdout.strip()
    identities = population.identity_vector()
    groups = population.group_vector()
    tasks = population.task_vector()
    counts = {
        f"RFC {start}-{end}": _aggregate_scan(start, end)
        for start, end in CANDIDATE_INTERVALS
    }
    first_zero = next(
        label
        for label, value in counts.items()
        if value == {"tree_matches": 0, "history_introductions": 0}
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "freshness_parent_commit": parent,
        "candidate_interval_order": [
            f"RFC {start}-{end}" for start, end in CANDIDATE_INTERVALS
        ],
        "candidate_interval_aggregate_counts": counts,
        "selected_first_zero_collision_interval": first_zero,
        "task_count": population.TASK_COUNT,
        "rows_per_task": population.ROWS_PER_TASK,
        "identity_count": len(identities),
        "identity_vector_sha256": population.payload_sha256(identities),
        "group_vector_sha256": population.payload_sha256(groups),
        "task_vector_sha256": population.payload_sha256(tasks),
        "selected_whole_group_tree_and_history_counts_all_zero": counts[first_zero]
        == {"tree_matches": 0, "history_introductions": 0},
        "lower_priority_candidate_intervals_scanned_after_first_zero": False,
        "individual_identity_or_task_retained_replaced_or_selected_using_scan_outcome": False,
        "candidate_page_endpoint_model_evaluator_or_quality_opened": False,
        "identity_selected_or_replaced_using_endpoint_or_outcome": False,
        "contains_identity_page_endpoint_prediction_answer_gold_metric_score_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "fresh_list_atomic_gate_protocol_design": True,
            "candidate_page_or_endpoint_preflight": False,
            "network_model_search_fetch_external_forward_or_evaluator": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        },
    }
    value["audit_payload_sha256"] = population.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    false_flags = (
        "lower_priority_candidate_intervals_scanned_after_first_zero",
        "individual_identity_or_task_retained_replaced_or_selected_using_scan_outcome",
        "candidate_page_endpoint_model_evaluator_or_quality_opened",
        "identity_selected_or_replaced_using_endpoint_or_outcome",
        "contains_identity_page_endpoint_prediction_answer_gold_metric_score_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
        "network_model_search_fetch_evaluator_benchmark_or_api_called",
        "entropy_or_information_gain_assigns_signed_credit",
    )
    if (
        copied.get("role") != ROLE
        or copied.get("freshness_parent_commit")
        != population.FRESHNESS_PARENT_COMMIT
        or copied.get("candidate_interval_order")
        != ["RFC 9480-9559", "RFC 9560-9639", "RFC 9640-9719", "RFC 9720-9799"]
        or copied.get("candidate_interval_aggregate_counts") != EXPECTED_COUNTS
        or copied.get("selected_first_zero_collision_interval") != "RFC 9720-9799"
        or copied.get("task_count") != 20
        or copied.get("rows_per_task") != 4
        or copied.get("identity_count") != 80
        or copied.get("identity_vector_sha256")
        != population.EXPECTED_IDENTITY_VECTOR_SHA256
        or copied.get("group_vector_sha256")
        != population.EXPECTED_GROUP_VECTOR_SHA256
        or copied.get("task_vector_sha256") != population.EXPECTED_TASK_VECTOR_SHA256
        or copied.get("selected_whole_group_tree_and_history_counts_all_zero")
        is not True
        or any(copied.get(name) is not False for name in false_flags)
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "fresh_list_atomic_gate_protocol_design": True,
            "candidate_page_or_endpoint_preflight": False,
            "network_model_search_fetch_external_forward_or_evaluator": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        }
        or seal != population.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.22 population history audit drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
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


def main() -> None:
    value = build_audit()
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "task_count": value["task_count"],
                "identity_count": value["identity_count"],
                "candidate_interval_aggregate_counts": value[
                    "candidate_interval_aggregate_counts"
                ],
                "selected": value["selected_first_zero_collision_interval"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
