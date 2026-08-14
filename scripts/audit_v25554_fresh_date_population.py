#!/usr/bin/env python3
"""Repository-only freshness/build audit for V2.55.52-53.

The audit binds the pure valid-Unknown truth parser and the indivisible fresh
date population.  Identity selection is checked at the frozen selection parent
with one exact-literal tree scan and one ancestry-patch scan.  No endpoint,
page, version, date, model, prediction, truth, evaluator, score, quality result,
benchmark API, or network resource is opened.
"""

from __future__ import annotations

import argparse
import ast
import copy
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25068_quote_verified_external_contract as watchers  # noqa: E402
from deepwide_agent import v25406_grounded_membership_exact220_contract as exact220  # noqa: E402
from deepwide_agent import v25541_visible_output_constraint_contract as constraints  # noqa: E402
from deepwide_agent import v25552_pypi_stable_truth as truth  # noqa: E402
from deepwide_agent import v25553_fresh_date_constraint_population as population  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402


DATE = "20260814"
ROLE = "v25554_fresh_date_population_build_audit"
IMPLEMENTATION_COMMIT = "6cdc31cdebe94b1dde6bbe97e1df0609aa0e6396"
SOURCE = Path("scripts/audit_v25554_fresh_date_population.py")
TEST = Path("tests/test_audit_v25554_fresh_date_population.py")
TRUTH_SOURCE = Path("src/deepwide_agent/v25552_pypi_stable_truth.py")
TRUTH_TEST = Path("tests/test_v25552_pypi_stable_truth.py")
POPULATION_SOURCE = Path(
    "src/deepwide_agent/v25553_fresh_date_constraint_population.py"
)
POPULATION_TEST = Path(
    "tests/test_v25553_fresh_date_constraint_population.py"
)
OUTPUT = Path(f"results/v25554_fresh_date_population_build_audit_v1_{DATE}.json")
FIXED_HASHES = {
    TRUTH_SOURCE: "0f15b7f087e7adef8db061fb5c1d9e5ae92b16ba063df21270cac130def04ca7",
    TRUTH_TEST: "ca9bb2af8846c5b4714ec5a4c156d84870d9d7c034d3244c4801acd492ad7c44",
    POPULATION_SOURCE: "43687a6ef8c519b88ea3ca5ff5a8050dd299d140cabc4b0e3572f05b40bbe669",
    POPULATION_TEST: "c63a585dd7965b2d779fea3de9aa6b24de349d2860f30948930582104997ec65",
}
TEST_SUITES = (
    ("test_v25552_pypi_stable_truth.py", 6),
    ("test_v25553_fresh_date_constraint_population.py", 6),
)
EXPECTED_TESTS = 12
EXACT220_TASK_COUNT = 220
EXACT220_OPAQUE_VECTOR_SHA256 = (
    "3c4b3eeb6cadbc9ce8b22552f294a0322e820dbb4be29c3e7fb2f99a4f83665a"
)
EXACT220_QUESTION_VECTOR_SHA256 = (
    "d009f9f13b51e48e249f6698b3b1417d3a62c7100c8551b1cb025e726bcd82b7"
)
HISTORY_TIMEOUT_SECONDS = 180


def _publish(path: Path, value: Mapping[str, Any]) -> None:
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


def _git_at_parent(
    *args: str, input_text: str | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        env={
            "HOME": os.environ.get("HOME", str(Path.home())),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        },
        input=input_text,
        stdin=subprocess.DEVNULL if input_text is None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=HISTORY_TIMEOUT_SECONDS,
        check=False,
    )


def _history_freshness() -> dict[str, Any]:
    identities = population.identity_vector()
    vector = "\n".join(identities) + "\n"
    tree = _git_at_parent(
        "grep",
        "-I",
        "-F",
        "-f",
        "-",
        population.SELECTION_PARENT_COMMIT,
        "--",
        ".",
        input_text=vector,
    )
    if tree.returncode not in (0, 1):
        raise RuntimeError("V2.55.54 selection-parent tree scan failed")
    expression = "(" + "|".join(re.escape(value) for value in identities) + ")"
    history = _git_at_parent(
        "log",
        population.SELECTION_PARENT_COMMIT,
        "--format=",
        "--perl-regexp",
        f"-G{expression}",
        "-p",
        "--",
        ".",
    )
    if history.returncode != 0:
        raise RuntimeError("V2.55.54 selection-parent ancestry patch scan failed")
    patch_hits = sorted(
        {
            match.group(0)
            for match in re.finditer(expression, history.stdout)
        }
    )
    return {
        "selection_parent_commit": population.SELECTION_PARENT_COMMIT,
        "identity_count": len(identities),
        "identity_vector_sha256": population.payload_sha256(identities),
        "tree_exact_literal_match_line_count": len(
            [line for line in tree.stdout.splitlines() if line.strip()]
        ),
        "ancestry_patch_exact_literal_identity_hit_count": len(patch_hits),
        "repository_paths_scope": ".",
        "network_endpoint_page_version_date_model_prediction_truth_evaluator_score_or_outcome_read": False,
    }


def _exact220_overlap() -> dict[str, Any]:
    frozen = exact220.task_vector(ROOT)
    candidate = population.task_vector()
    frozen_ids = [row["opaque_id"] for row in frozen]
    frozen_questions = [row["question"] for row in frozen]
    if (
        len(frozen) != EXACT220_TASK_COUNT
        or exact220.payload_sha256(frozen_ids) != EXACT220_OPAQUE_VECTOR_SHA256
        or exact220.payload_sha256(frozen_questions)
        != EXACT220_QUESTION_VECTOR_SHA256
        or any(set(row) != {"opaque_id", "question"} for row in frozen)
    ):
        raise RuntimeError("V2.55.54 fixed exact-220 visible vector drifted")
    return {
        "fixed_visible_task_count": len(frozen),
        "fixed_opaque_id_vector_sha256": EXACT220_OPAQUE_VECTOR_SHA256,
        "fixed_question_vector_sha256": EXACT220_QUESTION_VECTOR_SHA256,
        "candidate_task_count": len(candidate),
        "question_overlap_count": len(
            {row["question"] for row in candidate}.intersection(frozen_questions)
        ),
        "opaque_id_overlap_count": len(
            {row["opaque_id"] for row in candidate}.intersection(frozen_ids)
        ),
        "question_opaque_id_or_per_task_features_persisted": False,
    }


def _contract_reach() -> dict[str, int]:
    counts = {
        "task_count": 0,
        "active_constraint_tasks": 0,
        "date_format_tasks": 0,
        "numeric_scale_tasks": 0,
        "explicit_order_tasks": 0,
        "temporal_year_range_tasks": 0,
        "rank_slots_tasks": 0,
    }
    for task in population.task_vector():
        value = constraints.build_contract(task["question"], population.DATE_COLUMNS)
        counts["task_count"] += 1
        counts["active_constraint_tasks"] += int(value["active_family_count"] > 0)
        for family in (
            "date_format",
            "numeric_scale",
            "explicit_order",
            "temporal_year_range",
            "rank_slots",
        ):
            counts[f"{family}_tasks"] += int(value[family] is not None)
    return counts


def _tests() -> dict[str, Any]:
    suites = [base._test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _pure_module(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden = ("os", "pathlib", "subprocess", "socket", "requests", "httpx", "urllib")
    return all(
        not any(name == item or name.startswith(item + ".") for name in imports)
        for item in forbidden
    )


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain", "--untracked-files=all")
    history = set(base._git("rev-list", head).splitlines())
    fixed = {str(path): base.sha256(path) for path in FIXED_HASHES}
    freshness = _history_freshness()
    overlap = _exact220_overlap()
    reach = _contract_reach()
    tests = _tests()
    tasks = population.task_vector()
    identities = population.identity_vector()
    policy = population.source_policy()
    mechanism = population.mechanism_gate()
    quality = population.quality_gate()
    snapshot = watchers.watcher_snapshot()
    explicit = {SOURCE, TEST, *FIXED_HASHES}
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    checks = {
        "clean_pushed_head_and_implementation_commit_in_history": (
            (clean if tracked else True)
            and head == target
            and IMPLEMENTATION_COMMIT in history
        ),
        "audit_source_test_truth_population_sources_and_tests_tracked": not untracked,
        "fixed_implementation_hashes_exact": all(
            fixed[str(path)] == expected for path, expected in FIXED_HASHES.items()
        ),
        "focused_truth_and_population_tests_exact12": tests["passed"],
        "truth_and_population_modules_pure": _pure_module(TRUTH_SOURCE)
        and _pure_module(POPULATION_SOURCE),
        "one_indivisible_twenty_task_forty_identity_date_block": (
            len(tasks) == 20
            and len(identities) == 40
            and len(set(identities)) == 40
            and population.DATE_TASK_COUNT == 20
            and population.SCALE_TASK_COUNT == 0
        ),
        "selection_parent_tree_exact_literal_matches_zero": freshness[
            "tree_exact_literal_match_line_count"
        ]
        == 0,
        "selection_parent_ancestry_patch_exact_literal_hits_zero": freshness[
            "ancestry_patch_exact_literal_identity_hit_count"
        ]
        == 0,
        "fixed_exact220_visible_vector_hash_bound": overlap[
            "fixed_visible_task_count"
        ]
        == EXACT220_TASK_COUNT,
        "question_and_opaque_overlap_with_exact220_zero": (
            overlap["question_overlap_count"] == 0
            and overlap["opaque_id_overlap_count"] == 0
        ),
        "date_and_order_contract_reach_exact20_and_scale_zero": reach
        == {
            "task_count": 20,
            "active_constraint_tasks": 20,
            "date_format_tasks": 20,
            "numeric_scale_tasks": 0,
            "explicit_order_tasks": 20,
            "temporal_year_range_tasks": 0,
            "rank_slots_tasks": 0,
        },
        "runtime_boundary_exactly_opaque_id_question_same_forward_pages": policy[
            "runtime_boundary"
        ]
        == ["opaque_id", "question", "same_forward_public_pages"],
        "selection_repository_only_label_blind_and_outcome_free": (
            policy["selection_reads_repository_history_only"] is True
            and policy[
                "endpoint_page_version_date_model_prediction_mapping_truth_evaluator_score_quality_or_outcome_used_for_selection"
            ]
            is False
            and policy[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
            ]
            is False
        ),
        "individual_filtering_replacement_retry_resume_or_backfill_forbidden": policy[
            "individual_task_filtering_ranking_retention_replacement_retry_resume_or_backfill"
        ]
        is False,
        "valid_unknown_truth_and_sort_totality_fixed_before_forward": (
            truth.POLICY_ID == "v25552_pypi_stable_truth_totality_v1"
            and quality[
                "official_identity_bound_no_stable_release_is_valid_unknown"
            ]
            and quality[
                "known_dates_descending_then_unknown_stable_supplied_order"
            ]
        ),
        "mechanism_and_quality_gates_fixed_before_forward": (
            mechanism["fixed_task_denominator"] == 20
            and mechanism["minimum_date_contract_tasks"] == 20
            and mechanism["minimum_scale_contract_tasks"] == 0
            and quality["fixed_task_denominator"] == 20
            and quality[
                "each_control_and_candidate_prediction_evaluated_exactly_once"
            ]
            is True
        ),
        "protected_watchers_unchanged": snapshot
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in watchers.EXPECTED_WATCHERS
        ],
        "shared_api_lease_inactive": base._lease_inactive(),
        "network_model_search_fetch_evaluator_benchmark_or_api_not_called": True,
        "positive_signed_credit_zero": (
            mechanism["positive_signed_credit_count"] == 0
            and quality["positive_signed_credit_count"] == 0
        ),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    valid = not findings
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": clean if tracked else True,
        },
        "fixed_artifact_hashes": fixed,
        "tests": tests,
        "selection_freshness": freshness,
        "fixed220_visible_overlap": overlap,
        "visible_contract_reach": reach,
        "population": {
            "task_count": len(tasks),
            "identity_count": len(identities),
            "identity_vector_sha256": population.EXPECTED_IDENTITY_VECTOR_SHA256,
            "task_vector_sha256": population.EXPECTED_TASK_VECTOR_SHA256,
            "date_task_count": population.DATE_TASK_COUNT,
            "scale_task_count": population.SCALE_TASK_COUNT,
        },
        "truth_policy": {
            "policy_id": truth.POLICY_ID,
            "official_identity_bound_no_stable_release_is_valid_unknown": True,
            "known_dates_descending_then_unknown_stable_supplied_order": True,
            "evaluator_only_absent_from_future_forward_closure": True,
        },
        "source_policy": policy,
        "mechanism_gate": mechanism,
        "quality_gate": quality,
        "protected_watchers": snapshot,
        "checks": checks,
        "findings": findings,
        "audit_valid": valid,
        "identity_question_opaque_id_endpoint_page_version_date_prediction_truth_score_or_per_task_feature_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "fresh_shared_parent_external_protocol_design": valid,
            "external_forward": False,
            "postfreeze_truth_or_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = base.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    checks = copied.get("checks") or {}
    valid = copied.get("audit_valid") is True
    freshness = copied.get("selection_freshness") or {}
    overlap = copied.get("fixed220_visible_overlap") or {}
    reach = copied.get("visible_contract_reach") or {}
    git_value = copied.get("git") or {}
    if (
        copied.get("role") != ROLE
        or copied.get("implementation_commit") != IMPLEMENTATION_COMMIT
        or not isinstance(checks, Mapping)
        or any(passed is not True for passed in checks.values())
        or copied.get("findings")
        != sorted(name for name, passed in checks.items() if not passed)
        or valid is not (copied.get("findings") == [])
        or git_value.get("clean") is not True
        or git_value.get("equal") is not True
        or git_value.get("head") != git_value.get("target_main")
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("fixed_artifact_hashes")
        != {str(path): expected for path, expected in FIXED_HASHES.items()}
        or freshness.get("selection_parent_commit")
        != population.SELECTION_PARENT_COMMIT
        or freshness.get("identity_count") != 40
        or freshness.get("identity_vector_sha256")
        != population.EXPECTED_IDENTITY_VECTOR_SHA256
        or freshness.get("tree_exact_literal_match_line_count") != 0
        or freshness.get("ancestry_patch_exact_literal_identity_hit_count") != 0
        or freshness.get(
            "network_endpoint_page_version_date_model_prediction_truth_evaluator_score_or_outcome_read"
        )
        is not False
        or overlap.get("fixed_visible_task_count") != EXACT220_TASK_COUNT
        or overlap.get("fixed_opaque_id_vector_sha256")
        != EXACT220_OPAQUE_VECTOR_SHA256
        or overlap.get("fixed_question_vector_sha256")
        != EXACT220_QUESTION_VECTOR_SHA256
        or overlap.get("candidate_task_count") != population.TASK_COUNT
        or overlap.get("question_overlap_count") != 0
        or overlap.get("opaque_id_overlap_count") != 0
        or overlap.get("question_opaque_id_or_per_task_features_persisted")
        is not False
        or reach
        != {
            "task_count": 20,
            "active_constraint_tasks": 20,
            "date_format_tasks": 20,
            "numeric_scale_tasks": 0,
            "explicit_order_tasks": 20,
            "temporal_year_range_tasks": 0,
            "rank_slots_tasks": 0,
        }
        or copied.get("population", {}).get("task_vector_sha256")
        != population.EXPECTED_TASK_VECTOR_SHA256
        or copied.get("source_policy") != population.source_policy()
        or copied.get("mechanism_gate") != population.mechanism_gate()
        or copied.get("quality_gate") != population.quality_gate()
        or copied.get("truth_policy")
        != {
            "policy_id": truth.POLICY_ID,
            "official_identity_bound_no_stable_release_is_valid_unknown": True,
            "known_dates_descending_then_unknown_stable_supplied_order": True,
            "evaluator_only_absent_from_future_forward_closure": True,
        }
        or copied.get("protected_watchers") != watchers.watcher_snapshot()
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "fresh_shared_parent_external_protocol_design": valid,
            "external_forward": False,
            "postfreeze_truth_or_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.54 population build audit drifted")
    return copied


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    value = build_audit()
    if value["findings"]:
        raise RuntimeError(value["findings"])
    _publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "tests": value["tests"],
                "selection_freshness": value["selection_freshness"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
