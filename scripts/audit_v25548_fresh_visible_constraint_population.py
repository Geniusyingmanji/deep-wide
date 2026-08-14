#!/usr/bin/env python3
"""Outcome-blind freshness audit for the V2.55.47 population."""

from __future__ import annotations

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
from deepwide_agent import v25547_fresh_visible_constraint_population as population  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import audit_v25546_deterministic_visible_constraint_build as parent_audit  # noqa: E402


DATE = "20260814"
ROLE = "v25548_fresh_visible_constraint_population_audit"
POPULATION_COMMIT = "7afbf0f9cc6b3dea28d0e56c41a2d94a4dc85f27"
SOURCE = Path("scripts/audit_v25548_fresh_visible_constraint_population.py")
TEST = Path("tests/test_audit_v25548_fresh_visible_constraint_population.py")
POPULATION_SOURCE = Path(
    "src/deepwide_agent/v25547_fresh_visible_constraint_population.py"
)
POPULATION_TEST = Path(
    "tests/test_v25547_fresh_visible_constraint_population.py"
)
PARENT_AUDIT = Path(
    "results/v25546_deterministic_visible_constraint_build_audit_v1_20260814.json"
)
OUTPUT = Path(
    f"results/v25548_fresh_visible_constraint_population_audit_v1_{DATE}.json"
)
FIXED_HASHES = {
    POPULATION_SOURCE: "f51deaff7c9a67449742f3e32db902bbc092dcb7f8d2d215698c6f27c9a1e610",
    POPULATION_TEST: "303904ac19ca6defae888166cc16bebe6f33d2d0c44d2bbd94b3f483cd18b006",
    PARENT_AUDIT: "e1d781250a83f3e049cc1cf3ec709acee237c7e4928ab9de53516cddb942b0f6",
}
EXACT220_TASK_COUNT = 220
EXACT220_OPAQUE_VECTOR_SHA256 = (
    "3c4b3eeb6cadbc9ce8b22552f294a0322e820dbb4be29c3e7fb2f99a4f83665a"
)
EXACT220_QUESTION_VECTOR_SHA256 = (
    "d009f9f13b51e48e249f6698b3b1417d3a62c7100c8551b1cb025e726bcd82b7"
)
HISTORY_TIMEOUT_SECONDS = 180
CHECK_NAMES = frozenset(
    {
        "v25546_parent_hash_role_seal_and_population_design_authority_exact",
        "population_commit_in_head_history_and_selection_parent_exact",
        "population_audit_source_test_parent_and_population_files_tracked",
        "fixed_parent_population_hashes_exact",
        "one_indivisible_twenty_task_forty_identity_block",
        "selection_parent_tree_exact_literal_matches_zero",
        "selection_parent_ancestry_exact_literal_introduction_commits_zero",
        "fixed_exact220_visible_vector_hash_bound",
        "question_and_opaque_overlap_with_exact220_zero",
        "date_scale_and_order_contract_reach_exact_10_10_20",
        "runtime_boundary_exactly_opaque_id_question_same_forward_pages",
        "selection_is_repository_only_label_blind_and_outcome_free",
        "individual_filtering_replacement_retry_resume_or_backfill_forbidden",
        "mechanism_and_quality_gates_fixed_before_forward",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "network_model_search_fetch_evaluator_benchmark_or_api_not_called",
        "positive_signed_credit_zero",
    }
)


def _git_at_parent(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
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


def _parent_barrier() -> dict[str, Any]:
    value = json.loads(base._ordinary(PARENT_AUDIT).read_text(encoding="utf-8"))
    parent_audit.validate_audit(value)
    authorization = value.get("authorization") or {}
    if (
        base.sha256(PARENT_AUDIT) != FIXED_HASHES[PARENT_AUDIT]
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or authorization.get("fresh_task_disjoint_shared_parent_population_design")
        is not True
        or authorization.get("external_population_protocol_or_forward") is not False
        or authorization.get("deepwidebench_forward_or_evaluator") is not False
    ):
        raise RuntimeError("V2.55.48 parent build barrier drifted")
    return value


def _history_freshness() -> dict[str, Any]:
    identities = population.identity_vector()
    stdin = "\n".join(identities) + "\n"
    tree = _git_at_parent(
        "grep",
        "-I",
        "-F",
        "-f",
        "-",
        population.SELECTION_PARENT_COMMIT,
        "--",
        ".",
        input_text=stdin,
    )
    # git grep returns 1 for no matches and 0 for matches.
    if tree.returncode not in (0, 1):
        raise RuntimeError("V2.55.48 selection-parent tree scan failed")
    expression = "(" + "|".join(re.escape(value) for value in identities) + ")"
    history = _git_at_parent(
        "log",
        population.SELECTION_PARENT_COMMIT,
        "--format=%H",
        "--perl-regexp",
        f"-G{expression}",
        "--",
        ".",
    )
    if history.returncode != 0:
        raise RuntimeError("V2.55.48 selection-parent ancestry scan failed")
    tree_lines = [line for line in tree.stdout.splitlines() if line.strip()]
    commits = [line for line in history.stdout.splitlines() if line.strip()]
    return {
        "selection_parent_commit": population.SELECTION_PARENT_COMMIT,
        "identity_count": len(identities),
        "identity_vector_sha256": population.payload_sha256(identities),
        "tree_exact_literal_match_count": len(tree_lines),
        "ancestry_exact_literal_introduction_commit_count": len(set(commits)),
        "repository_paths_scope": ".",
        "network_endpoint_page_model_prediction_truth_evaluator_or_outcome_read": False,
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
        raise RuntimeError("V2.55.48 fixed exact-220 visible vector drifted")
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
    for index, task in enumerate(population.task_vector()):
        columns = (
            population.DATE_COLUMNS
            if index < population.DATE_TASK_COUNT
            else population.SCALE_COLUMNS
        )
        value = constraints.build_contract(task["question"], columns)
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


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    parent = _parent_barrier()
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain", "--untracked-files=all")
    history = set(base._git("rev-list", head).splitlines())
    fixed = {str(path): base.sha256(path) for path in FIXED_HASHES}
    freshness = _history_freshness()
    overlap = _exact220_overlap()
    reach = _contract_reach()
    tasks = population.task_vector()
    identities = population.identity_vector()
    policy = population.source_policy()
    mechanism = population.mechanism_gate()
    quality = population.quality_gate()
    snapshot = watchers.watcher_snapshot()
    explicit = {SOURCE, TEST, POPULATION_SOURCE, POPULATION_TEST, PARENT_AUDIT}
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    reported_clean = clean if tracked else True
    checks = {
        "v25546_parent_hash_role_seal_and_population_design_authority_exact": bool(parent),
        "population_commit_in_head_history_and_selection_parent_exact": (
            POPULATION_COMMIT in history
            and base._git("rev-parse", population.SELECTION_PARENT_COMMIT)
            == population.SELECTION_PARENT_COMMIT
        ),
        "population_audit_source_test_parent_and_population_files_tracked": not untracked,
        "fixed_parent_population_hashes_exact": all(
            fixed[str(path)] == expected for path, expected in FIXED_HASHES.items()
        ),
        "one_indivisible_twenty_task_forty_identity_block": (
            len(tasks) == 20
            and len(identities) == 40
            and len(set(identities)) == 40
            and policy["one_indivisible_static_twenty_task_block"] is True
        ),
        "selection_parent_tree_exact_literal_matches_zero": freshness[
            "tree_exact_literal_match_count"
        ]
        == 0,
        "selection_parent_ancestry_exact_literal_introduction_commits_zero": freshness[
            "ancestry_exact_literal_introduction_commit_count"
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
        "date_scale_and_order_contract_reach_exact_10_10_20": reach
        == {
            "task_count": 20,
            "active_constraint_tasks": 20,
            "date_format_tasks": 10,
            "numeric_scale_tasks": 10,
            "explicit_order_tasks": 20,
            "temporal_year_range_tasks": 0,
            "rank_slots_tasks": 0,
        },
        "runtime_boundary_exactly_opaque_id_question_same_forward_pages": policy[
            "runtime_boundary"
        ]
        == ["opaque_id", "question", "same_forward_public_pages"],
        "selection_is_repository_only_label_blind_and_outcome_free": (
            policy["selection_reads_repository_history_only"] is True
            and policy[
                "endpoint_page_model_prediction_mapping_truth_evaluator_score_quality_or_outcome_used_for_selection"
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
        "mechanism_and_quality_gates_fixed_before_forward": (
            mechanism["fixed_task_denominator"] == 20
            and mechanism["required_terminal_tasks"] == 20
            and quality["fixed_task_denominator"] == 20
            and quality["each_control_and_candidate_prediction_evaluated_exactly_once"]
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
        "population_commit": POPULATION_COMMIT,
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": reported_clean,
        },
        "fixed_artifact_hashes": fixed,
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
        "source_policy": policy,
        "mechanism_gate": mechanism,
        "quality_gate": quality,
        "protected_watchers": snapshot,
        "checks": checks,
        "findings": findings,
        "audit_valid": valid,
        "identity_question_opaque_id_page_prediction_truth_evaluator_score_or_per_task_feature_persisted": False,
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
    checks = copied.get("checks")
    valid = copied.get("audit_valid") is True
    expected_watchers = [
        {"pid": pid, "start_ticks": ticks, "marker": marker}
        for pid, ticks, marker in watchers.EXPECTED_WATCHERS
    ]
    git = copied.get("git")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("population_commit") != POPULATION_COMMIT
        or not isinstance(git, Mapping)
        or git.get("head") != git.get("target_main")
        or git.get("equal") is not True
        or git.get("clean") is not True
        or copied.get("fixed_artifact_hashes")
        != {str(path): expected for path, expected in FIXED_HASHES.items()}
        or not isinstance(checks, Mapping)
        or set(checks) != CHECK_NAMES
        or any(passed is not True for passed in checks.values())
        or copied.get("findings") != []
        or not valid
        or copied.get("selection_freshness")
        != {
            "selection_parent_commit": population.SELECTION_PARENT_COMMIT,
            "identity_count": 40,
            "identity_vector_sha256": population.EXPECTED_IDENTITY_VECTOR_SHA256,
            "tree_exact_literal_match_count": 0,
            "ancestry_exact_literal_introduction_commit_count": 0,
            "repository_paths_scope": ".",
            "network_endpoint_page_model_prediction_truth_evaluator_or_outcome_read": False,
        }
        or copied.get("fixed220_visible_overlap")
        != {
            "fixed_visible_task_count": 220,
            "fixed_opaque_id_vector_sha256": EXACT220_OPAQUE_VECTOR_SHA256,
            "fixed_question_vector_sha256": EXACT220_QUESTION_VECTOR_SHA256,
            "candidate_task_count": 20,
            "question_overlap_count": 0,
            "opaque_id_overlap_count": 0,
            "question_opaque_id_or_per_task_features_persisted": False,
        }
        or copied.get("visible_contract_reach") != _contract_reach()
        or copied.get("population")
        != {
            "task_count": 20,
            "identity_count": 40,
            "identity_vector_sha256": population.EXPECTED_IDENTITY_VECTOR_SHA256,
            "task_vector_sha256": population.EXPECTED_TASK_VECTOR_SHA256,
            "date_task_count": 10,
            "scale_task_count": 10,
        }
        or copied.get("source_policy") != population.source_policy()
        or copied.get("mechanism_gate") != population.mechanism_gate()
        or copied.get("quality_gate") != population.quality_gate()
        or copied.get("protected_watchers") != expected_watchers
        or copied.get(
            "identity_question_opaque_id_page_prediction_truth_evaluator_score_or_per_task_feature_persisted"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
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
        raise ValueError("V2.55.48 visible constraint population audit drifted")
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
    if value["findings"]:
        raise RuntimeError(value["findings"])
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "selection_freshness": value["selection_freshness"],
                "fixed220_visible_overlap": value["fixed220_visible_overlap"],
                "visible_contract_reach": value["visible_contract_reach"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
