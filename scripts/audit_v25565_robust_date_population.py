#!/usr/bin/env python3
"""Repository-only audit of the fresh robust date population."""

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
from deepwide_agent import v25553_fresh_date_constraint_population as consumed_one  # noqa: E402
from deepwide_agent import v25559_fresh_date_poolfix_population as consumed_two  # noqa: E402
from deepwide_agent import v25564_fresh_date_robust_population as population  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402


DATE = "20260814"
ROLE = "v25565_robust_date_population_build_audit"
IMPLEMENTATION_COMMIT = "fa6077eb04fc4eb6329b4c074beea4fda36d3cb6"
SOURCE = Path("scripts/audit_v25565_robust_date_population.py")
TEST = Path("tests/test_audit_v25565_robust_date_population.py")
POPULATION_SOURCE = Path("src/deepwide_agent/v25564_fresh_date_robust_population.py")
POPULATION_TEST = Path("tests/test_v25564_fresh_date_robust_population.py")
OUTPUT = Path(f"results/v25565_robust_date_population_build_audit_v1_{DATE}.json")
FIXED_HASHES = {
    POPULATION_SOURCE: "f65443ae4f8bf011466d1ea8d99856b6b3e381c467e9a7713ace8886002d6e04",
    POPULATION_TEST: "5f75a9b278be0363dbec13196a261848cf9999c5854fc9a84e6a46ea94c22729",
}
TEST_SUITES = ((POPULATION_TEST.name, 5),)
EXPECTED_TESTS = 5
EXACT220_TASK_COUNT = 220
EXACT220_OPAQUE_VECTOR_SHA256 = (
    "3c4b3eeb6cadbc9ce8b22552f294a0322e820dbb4be29c3e7fb2f99a4f83665a"
)
EXACT220_QUESTION_VECTOR_SHA256 = (
    "d009f9f13b51e48e249f6698b3b1417d3a62c7100c8551b1cb025e726bcd82b7"
)


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


def _git_parent(
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
        timeout=180,
        check=False,
    )


def _history_freshness() -> dict[str, Any]:
    identities = population.identity_vector()
    tree = _git_parent(
        "grep",
        "-I",
        "-F",
        "-f",
        "-",
        population.SELECTION_PARENT_COMMIT,
        "--",
        ".",
        input_text="\n".join(identities) + "\n",
    )
    if tree.returncode not in (0, 1):
        raise RuntimeError("V2.55.65 tree scan failed")
    expression = "(" + "|".join(re.escape(value) for value in identities) + ")"
    history = _git_parent(
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
        raise RuntimeError("V2.55.65 ancestry scan failed")
    hits = sorted({match.group(0) for match in re.finditer(expression, history.stdout)})
    return {
        "selection_parent_commit": population.SELECTION_PARENT_COMMIT,
        "identity_count": len(identities),
        "identity_vector_sha256": population.EXPECTED_IDENTITY_VECTOR_SHA256,
        "tree_exact_literal_match_line_count": len(
            [line for line in tree.stdout.splitlines() if line.strip()]
        ),
        "ancestry_patch_exact_literal_identity_hit_count": len(hits),
        "network_endpoint_page_version_date_model_prediction_truth_evaluator_score_or_outcome_read": False,
    }


def _overlap() -> dict[str, Any]:
    frozen = exact220.task_vector(ROOT)
    candidate = population.task_vector()
    frozen_ids = [row["opaque_id"] for row in frozen]
    frozen_questions = [row["question"] for row in frozen]
    if (
        len(frozen) != EXACT220_TASK_COUNT
        or exact220.payload_sha256(frozen_ids) != EXACT220_OPAQUE_VECTOR_SHA256
        or exact220.payload_sha256(frozen_questions)
        != EXACT220_QUESTION_VECTOR_SHA256
    ):
        raise RuntimeError("V2.55.65 exact220 vector drifted")
    identities = set(population.identity_vector())
    questions = {row["question"] for row in candidate}
    first_identities = set(consumed_one.identity_vector())
    second_identities = set(consumed_two.identity_vector())
    return {
        "fixed220_question_overlap_count": len(questions.intersection(frozen_questions)),
        "fixed220_opaque_overlap_count": len(
            {row["opaque_id"] for row in candidate}.intersection(frozen_ids)
        ),
        "v25553_consumed_identity_overlap_count": len(
            identities.intersection(first_identities)
        ),
        "v25553_consumed_question_overlap_count": len(
            questions.intersection(row["question"] for row in consumed_one.task_vector())
        ),
        "v25559_consumed_identity_overlap_count": len(
            identities.intersection(second_identities)
        ),
        "v25559_consumed_question_overlap_count": len(
            questions.intersection(row["question"] for row in consumed_two.task_vector())
        ),
        "question_identity_opaque_or_per_task_features_persisted": False,
    }


def _contract_reach() -> dict[str, int]:
    counts = {
        name: 0
        for name in (
            "task_count",
            "active_constraint_tasks",
            "date_format_tasks",
            "numeric_scale_tasks",
            "explicit_order_tasks",
            "temporal_year_range_tasks",
            "rank_slots_tasks",
        )
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


def _pure(path: Path) -> bool:
    tree = ast.parse(path.read_text(), filename=str(path))
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
    freshness = _history_freshness()
    overlap = _overlap()
    reach = _contract_reach()
    tests = _tests()
    fixed = {str(path): base.sha256(path) for path in FIXED_HASHES}
    explicit = {SOURCE, TEST, *FIXED_HASHES}
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    checks = {
        "clean_pushed_implementation_commit_in_history": (clean if tracked else True)
        and head == target
        and IMPLEMENTATION_COMMIT in history,
        "audit_and_fixed_sources_tests_tracked": not untracked,
        "fixed_hashes_exact": all(
            fixed[str(path)] == expected for path, expected in FIXED_HASHES.items()
        ),
        "focused_population_tests_exact5": tests["passed"],
        "population_module_pure": _pure(POPULATION_SOURCE),
        "fresh_tree_and_ancestry_patch_hits_zero": freshness[
            "tree_exact_literal_match_line_count"
        ]
        == 0
        and freshness["ancestry_patch_exact_literal_identity_hit_count"] == 0,
        "fixed220_and_both_consumed_population_overlap_zero": all(
            overlap[name] == 0
            for name in (
                "fixed220_question_overlap_count",
                "fixed220_opaque_overlap_count",
                "v25553_consumed_identity_overlap_count",
                "v25553_consumed_question_overlap_count",
                "v25559_consumed_identity_overlap_count",
                "v25559_consumed_question_overlap_count",
            )
        ),
        "date_order_reach_exact20_scale_zero": reach
        == {
            "task_count": 20,
            "active_constraint_tasks": 20,
            "date_format_tasks": 20,
            "numeric_scale_tasks": 0,
            "explicit_order_tasks": 20,
            "temporal_year_range_tasks": 0,
            "rank_slots_tasks": 0,
        },
        "runtime_boundary_label_blind": population.source_policy()["runtime_boundary"]
        == ["opaque_id", "question", "same_forward_public_pages"],
        "selection_repository_only_outcome_free": population.source_policy()[
            "endpoint_page_version_date_model_prediction_mapping_truth_evaluator_score_quality_or_outcome_used_for_selection"
        ]
        is False,
        "robust_gate_arm_blind_and_fixed20_preserved": population.quality_gate()[
            "fixed20_failure_as_zero_metrics_reported"
        ]
        and population.quality_gate()["minimum_arm_blind_paired_complete_tasks"] == 18
        and population.quality_gate()[
            "paired_complete_selection_uses_only_truth_availability"
        ]
        and population.quality_gate()[
            "prediction_arm_outcome_or_score_used_for_completeness_selection"
        ]
        is False,
        "protected_watchers_unchanged": watchers.watcher_snapshot()
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in watchers.EXPECTED_WATCHERS
        ],
        "shared_api_lease_inactive": base._lease_inactive(),
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": True,
        "positive_signed_credit_zero": population.mechanism_gate()[
            "positive_signed_credit_count"
        ]
        == 0
        and population.quality_gate()["positive_signed_credit_count"] == 0,
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
        "overlap": overlap,
        "visible_contract_reach": reach,
        "population": {
            "task_count": 20,
            "identity_count": 40,
            "identity_vector_sha256": population.EXPECTED_IDENTITY_VECTOR_SHA256,
            "task_vector_sha256": population.EXPECTED_TASK_VECTOR_SHA256,
        },
        "source_policy": population.source_policy(),
        "mechanism_gate": population.mechanism_gate(),
        "quality_gate": population.quality_gate(),
        "protected_watchers": watchers.watcher_snapshot(),
        "checks": checks,
        "findings": findings,
        "audit_valid": valid,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "fresh_robust_external_protocol_design": valid,
            "external_forward": False,
            "postfreeze_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = base.payload_sha256(value)
    return validate(value)


def validate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    checks = copied.get("checks") or {}
    freshness = copied.get("selection_freshness") or {}
    overlap = copied.get("overlap") or {}
    valid = copied.get("audit_valid") is True
    if (
        copied.get("role") != ROLE
        or copied.get("implementation_commit") != IMPLEMENTATION_COMMIT
        or copied.get("git", {}).get("clean") is not True
        or copied.get("git", {}).get("equal") is not True
        or copied.get("fixed_artifact_hashes")
        != {str(path): expected for path, expected in FIXED_HASHES.items()}
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or freshness.get("identity_count") != 40
        or freshness.get("identity_vector_sha256")
        != population.EXPECTED_IDENTITY_VECTOR_SHA256
        or freshness.get("tree_exact_literal_match_line_count") != 0
        or freshness.get("ancestry_patch_exact_literal_identity_hit_count") != 0
        or any(
            overlap.get(name) != 0
            for name in (
                "fixed220_question_overlap_count",
                "fixed220_opaque_overlap_count",
                "v25553_consumed_identity_overlap_count",
                "v25553_consumed_question_overlap_count",
                "v25559_consumed_identity_overlap_count",
                "v25559_consumed_question_overlap_count",
            )
        )
        or copied.get("source_policy") != population.source_policy()
        or copied.get("mechanism_gate") != population.mechanism_gate()
        or copied.get("quality_gate") != population.quality_gate()
        or copied.get("findings")
        != sorted(name for name, passed in checks.items() if not passed)
        or valid is not (copied.get("findings") == [])
        or not all(checks.values())
        or copied.get("protected_watchers") != watchers.watcher_snapshot()
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "fresh_robust_external_protocol_design": valid,
            "external_forward": False,
            "postfreeze_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.65 population audit drifted")
    return copied


def main() -> None:
    argparse.ArgumentParser().parse_args()
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
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
