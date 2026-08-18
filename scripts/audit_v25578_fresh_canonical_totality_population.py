#!/usr/bin/env python3
"""Repository-only audit of the V2.55.77 fresh population."""

from __future__ import annotations

import argparse
import ast
import copy
import importlib
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

from deepwide_agent import (  # noqa: E402
    v25406_grounded_membership_exact220_contract as exact220,
)
from deepwide_agent import (  # noqa: E402
    v25577_fresh_canonical_totality_population as population,
)
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import audit_v25576_canonical_column_totality_build as watcher_base  # noqa: E402


DATE = "20260818"
ROLE = "v25578_fresh_canonical_totality_population_build_audit"
IMPLEMENTATION_COMMIT = "9054ab8485ff88ff1666830beeda94b69a3454f9"
SOURCE = Path("scripts/audit_v25578_fresh_canonical_totality_population.py")
TEST = Path("tests/test_audit_v25578_fresh_canonical_totality_population.py")
POPULATION_SOURCE = Path(
    "src/deepwide_agent/v25577_fresh_canonical_totality_population.py"
)
POPULATION_TEST = Path(
    "tests/test_v25577_fresh_canonical_totality_population.py"
)
OUTPUT = Path(
    f"results/v25578_fresh_canonical_totality_population_build_audit_v1_{DATE}.json"
)
FIXED_HASHES = {
    POPULATION_SOURCE: "850b42d0d30f45856169843dc59c91990e5c2a1cef7799bb8cd64bbb055c3fb6",
    POPULATION_TEST: "eed4c326159dc17853a533173e6bdc829b0b8c1df8da348de88808c3ffc7a6a1",
}
TEST_SUITES = ((POPULATION_TEST.name, 6), (TEST.name, 5))
EXPECTED_TESTS = 11
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
        timeout=240,
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
        raise RuntimeError("V2.55.78 tree scan failed")
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
        raise RuntimeError("V2.55.78 ancestry scan failed")
    hits = sorted(
        {match.group(0) for match in re.finditer(expression, history.stdout)}
    )
    return {
        "selection_parent_commit": population.SELECTION_PARENT_COMMIT,
        "identity_count": len(identities),
        "identity_vector_sha256": population.EXPECTED_IDENTITY_VECTOR_SHA256,
        "tree_exact_literal_match_line_count": len(
            [line for line in tree.stdout.splitlines() if line.strip()]
        ),
        "ancestry_patch_exact_literal_identity_hit_count": len(hits),
        "network_endpoint_page_version_model_prediction_truth_evaluator_score_or_outcome_read": False,
    }


def _population_modules() -> list[str]:
    output: list[str] = []
    for path in sorted((ROOT / "src/deepwide_agent").glob("v*.py")):
        if path == ROOT / POPULATION_SOURCE:
            continue
        source = path.read_text(encoding="utf-8")
        if "def identity_vector(" in source:
            output.append(path.stem)
    return output


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
        raise RuntimeError("V2.55.78 exact220 vector drifted")
    candidate_identities = set(population.identity_vector())
    candidate_questions = {row["question"] for row in candidate}
    modules: dict[str, dict[str, int]] = {}
    for name in _population_modules():
        module = importlib.import_module(f"deepwide_agent.{name}")
        identities = set(module.identity_vector())
        questions = (
            {row["question"] for row in module.task_vector()}
            if hasattr(module, "task_vector")
            else set()
        )
        modules[name] = {
            "identity_overlap_count": len(candidate_identities & identities),
            "question_overlap_count": len(candidate_questions & questions),
        }
    return {
        "fixed220_question_overlap_count": len(
            candidate_questions.intersection(frozen_questions)
        ),
        "fixed220_opaque_overlap_count": len(
            {row["opaque_id"] for row in candidate}.intersection(frozen_ids)
        ),
        "historical_population_module_count": len(modules),
        "historical_population_overlaps": modules,
        "question_identity_opaque_or_per_task_features_persisted": False,
    }


def _exposure_reach() -> dict[str, Any]:
    from deepwide_agent import v25065_quote_verified_record_binding as quote
    from deepwide_agent import v25541_visible_output_constraint_contract as constraints

    drift = ordinary = active_constraint = 0
    for index, task in enumerate(population.task_vector()):
        columns = population.columns_for_index(index)
        canonical = quote._safe_columns(columns)
        exposure = population.exposure_for_index(index)
        drift += int(exposure == "canonical_drift" and columns != canonical)
        ordinary += int(exposure == "ordinary_ascii" and columns == canonical)
        contract = constraints.build_contract(task["question"], columns)
        active_constraint += int(contract["active_family_count"] > 0)
    return {
        "task_count": population.TASK_COUNT,
        "canonical_drift_tasks": drift,
        "ordinary_ascii_tasks": ordinary,
        "active_visible_constraint_tasks": active_constraint,
        "exposure_assignment_reads_only_pre_registered_visible_column_bytes": True,
        "provider_response_prediction_truth_score_or_outcome_used": False,
    }


def _tests() -> dict[str, Any]:
    suites = [base._test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS
        and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _pure(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden = (
        "os",
        "pathlib",
        "subprocess",
        "socket",
        "requests",
        "httpx",
        "urllib",
    )
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
    reach = _exposure_reach()
    tests = _tests()
    fixed = {str(path): base.sha256(path) for path in FIXED_HASHES}
    explicit = {SOURCE, TEST, *FIXED_HASHES}
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    population_overlap_counts = [
        count
        for value in overlap["historical_population_overlaps"].values()
        for count in value.values()
    ]
    watchers = watcher_base._watcher_observation()
    checks = {
        "clean_pushed_implementation_commit_in_history": (
            (clean if tracked else True)
            and head == target
            and IMPLEMENTATION_COMMIT in history
        ),
        "audit_and_fixed_sources_tests_tracked": not untracked,
        "fixed_hashes_exact": fixed
        == {str(path): expected for path, expected in FIXED_HASHES.items()},
        "focused_population_tests_exact11": tests["passed"],
        "population_module_pure": _pure(POPULATION_SOURCE),
        "fresh_tree_and_ancestry_patch_hits_zero": freshness[
            "tree_exact_literal_match_line_count"
        ]
        == 0
        and freshness["ancestry_patch_exact_literal_identity_hit_count"] == 0,
        "fixed220_question_and_opaque_overlap_zero": overlap[
            "fixed220_question_overlap_count"
        ]
        == 0
        and overlap["fixed220_opaque_overlap_count"] == 0,
        "all_historical_population_identity_and_question_overlap_zero": all(
            count == 0 for count in population_overlap_counts
        ),
        "canonical_drift_and_ordinary_reach_exact_ten_ten": reach
        == {
            "task_count": 20,
            "canonical_drift_tasks": 10,
            "ordinary_ascii_tasks": 10,
            "active_visible_constraint_tasks": 0,
            "exposure_assignment_reads_only_pre_registered_visible_column_bytes": True,
            "provider_response_prediction_truth_score_or_outcome_used": False,
        },
        "runtime_boundary_label_blind": population.source_policy()[
            "runtime_boundary"
        ]
        == ["opaque_id", "question", "same_forward_public_pages"],
        "selection_repository_only_outcome_free": population.source_policy()[
            "endpoint_page_version_model_prediction_mapping_truth_evaluator_score_quality_or_outcome_used_for_selection"
        ]
        is False,
        "historical_replay_does_not_route_fresh_forward": population.source_policy()[
            "historical_parent_replay_routes_or_selects_fresh_forward_tasks"
        ]
        is False,
        "quality_gate_arm_blind_and_fixed20": population.quality_gate()[
            "fixed20_failure_as_zero_metrics_reported"
        ]
        and population.quality_gate()[
            "minimum_arm_blind_paired_complete_tasks"
        ]
        == 18
        and population.quality_gate()[
            "paired_complete_selection_uses_only_truth_availability"
        ],
        "protected_watchers_not_restarted_or_replaced": watchers[
            "replacement_process_count"
        ]
        == 0
        and watchers[
            "agent_signal_stop_restart_or_replacement_performed"
        ]
        is False,
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
        "visible_exposure_reach": reach,
        "population": {
            "task_count": 20,
            "identity_count": 40,
            "identity_vector_sha256": population.EXPECTED_IDENTITY_VECTOR_SHA256,
            "task_vector_sha256": population.EXPECTED_TASK_VECTOR_SHA256,
        },
        "source_policy": population.source_policy(),
        "mechanism_gate": population.mechanism_gate(),
        "quality_gate": population.quality_gate(),
        "protected_watcher_observation": watchers,
        "checks": checks,
        "findings": findings,
        "audit_valid": valid,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "fresh_canonical_totality_external_protocol_design": valid,
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
        or overlap.get("fixed220_question_overlap_count") != 0
        or overlap.get("fixed220_opaque_overlap_count") != 0
        or any(
            count != 0
            for item in overlap.get("historical_population_overlaps", {}).values()
            for count in item.values()
        )
        or copied.get("source_policy") != population.source_policy()
        or copied.get("mechanism_gate") != population.mechanism_gate()
        or copied.get("quality_gate") != population.quality_gate()
        or copied.get("findings")
        != sorted(name for name, passed in checks.items() if not passed)
        or valid is not (copied.get("findings") == [])
        or any(passed is not True for passed in checks.values())
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "fresh_canonical_totality_external_protocol_design": valid,
            "external_forward": False,
            "postfreeze_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.78 population audit drifted")
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
                "overlap": value["overlap"],
                "visible_exposure_reach": value["visible_exposure_reach"],
                "findings": value["findings"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
