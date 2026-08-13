#!/usr/bin/env python3
"""Aggregate-only history audit for the V2.54.03 grounded-membership RFC population."""

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

from deepwide_agent import v25403_fresh_rfc_grounded_membership_population as population  # noqa: E402


DATE = "20260813"
ROLE = "v25404_fresh_rfc_grounded_membership_population_aggregate_history_audit"
OUTPUT = Path(
    f"results/v25404_fresh_rfc_grounded_membership_population_audit_v1_{DATE}.json"
)
SEARCH_PATHS = (
    "src", "scripts", "tests", "results", "outputs", "plan.md", "survey.md",
)


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        timeout=60, check=check,
    )


def _identity_pattern() -> str:
    numbers = "|".join(str(value) for value in population.RFC_NUMBERS)
    return rf"(RFC ({numbers})|rfc-({numbers}))"


@functools.lru_cache(maxsize=1)
def _aggregate_history_scan() -> tuple[int, int]:
    pattern = _identity_pattern()
    tree = _git(
        "grep", "-E", "-n", pattern, population.FRESHNESS_PARENT_COMMIT,
        "--", *SEARCH_PATHS, check=False,
    )
    if tree.returncode not in {0, 1}:
        raise RuntimeError("V2.54.04 parent-tree identity scan failed")
    history = _git(
        "log", "--format=%H", f"-G{pattern}", population.FRESHNESS_PARENT_COMMIT,
        "--", *SEARCH_PATHS,
    )
    return (
        sum(bool(line.strip()) for line in tree.stdout.splitlines()),
        len({line.strip() for line in history.stdout.splitlines() if line.strip()}),
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    parent = _git("rev-parse", population.FRESHNESS_PARENT_COMMIT).stdout.strip()
    identities = population.identity_vector()
    tree_count, history_count = _aggregate_history_scan()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "freshness_parent_commit": parent,
        "task_count": population.TASK_COUNT,
        "rows_per_task": population.ROWS_PER_TASK,
        "identity_count": len(identities),
        "identity_vector_sha256": population.payload_sha256(identities),
        "task_vector_sha256": population.payload_sha256(population.task_vector()),
        "canonical_identity_and_slug_tree_match_count": tree_count,
        "canonical_identity_and_slug_history_introduction_count": history_count,
        "whole_consecutive_group_tree_and_history_counts_all_zero": (
            tree_count == 0 and history_count == 0
        ),
        "individual_identity_or_task_retained_replaced_or_selected_using_scan_outcome": False,
        "candidate_page_endpoint_model_evaluator_or_quality_opened": False,
        "identity_selected_or_replaced_using_endpoint_or_outcome": False,
        "contains_identity_page_endpoint_prediction_answer_gold_metric_score_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "fresh_rfc_grounded_membership_protocol_design": True,
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
        "individual_identity_or_task_retained_replaced_or_selected_using_scan_outcome",
        "candidate_page_endpoint_model_evaluator_or_quality_opened",
        "identity_selected_or_replaced_using_endpoint_or_outcome",
        "contains_identity_page_endpoint_prediction_answer_gold_metric_score_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
        "network_model_search_fetch_evaluator_benchmark_or_api_called",
        "entropy_or_information_gain_assigns_signed_credit",
    )
    expected_authorization = {
        "fresh_rfc_grounded_membership_protocol_design": True,
        "candidate_page_or_endpoint_preflight": False,
        "network_model_search_fetch_external_forward_or_evaluator": False,
        "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
        "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
    }
    if (
        copied.get("role") != ROLE
        or copied.get("freshness_parent_commit") != population.FRESHNESS_PARENT_COMMIT
        or copied.get("task_count") != population.TASK_COUNT
        or copied.get("rows_per_task") != population.ROWS_PER_TASK
        or copied.get("identity_count") != population.TASK_COUNT * population.ROWS_PER_TASK
        or copied.get("identity_vector_sha256") != population.EXPECTED_IDENTITY_VECTOR_SHA256
        or copied.get("task_vector_sha256") != population.EXPECTED_TASK_VECTOR_SHA256
        or copied.get("canonical_identity_and_slug_tree_match_count") != 0
        or copied.get("canonical_identity_and_slug_history_introduction_count") != 0
        or copied.get("whole_consecutive_group_tree_and_history_counts_all_zero") is not True
        or any(copied.get(name) is not False for name in false_flags)
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization") != expected_authorization
        or seal != population.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.04 RFC population history audit drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
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
    print(json.dumps({
        "path": str(OUTPUT), "identity_count": value["identity_count"],
        "tree_matches": value["canonical_identity_and_slug_tree_match_count"],
        "history_introductions": value["canonical_identity_and_slug_history_introduction_count"],
        "authorization": value["authorization"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
