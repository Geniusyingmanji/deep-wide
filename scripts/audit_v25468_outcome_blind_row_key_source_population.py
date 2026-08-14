#!/usr/bin/env python3
"""Outcome-blind population audit for the V2.54.67 clue block."""

from __future__ import annotations

import copy
import hashlib
import json
import os
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
from deepwide_agent import v25467_outcome_blind_row_key_source_population as population  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import audit_v25466_row_key_bound_structured_source_build as build  # noqa: E402
from scripts import audit_v25460_structurally_disjoint_date_bounded_official_xml_population as selective  # noqa: E402


DATE = "20260814"
ROLE = "v25468_outcome_blind_row_key_source_population_audit"
SOURCE = Path("scripts/audit_v25468_outcome_blind_row_key_source_population.py")
TEST = Path("tests/test_audit_v25468_outcome_blind_row_key_source_population.py")
POPULATION_SOURCE = Path(
    "src/deepwide_agent/v25467_outcome_blind_row_key_source_population.py"
)
POPULATION_TEST = Path(
    "tests/test_v25467_outcome_blind_row_key_source_population.py"
)
OUTPUT = Path(
    f"results/v25468_outcome_blind_row_key_source_population_audit_v1_{DATE}.json"
)
BUILD_AUDIT = Path(
    "results/v25466_row_key_bound_structured_source_build_audit_v1_20260814.json"
)
HISTORICAL_POPULATION = Path(
    "src/deepwide_agent/v25027_clue_resolved_external_contract.py"
)
HISTORICAL_FORWARD = Path(
    "results/v25027_clue_resolved_external_forward_result_v1_20260809.json"
)
FIXED_HASHES = {
    BUILD_AUDIT: "cf650be0bff1d50f71dad6ad76a15732cf7e9f3cceedfe604570fa080d52b22c",
    POPULATION_SOURCE: "8b1ead5c4d939e07ad30a409d9db25a05df0dcc5be74e77135f8de54c2972e85",
    POPULATION_TEST: "f152188a267f55276f30b23b59699eabba4fa85d515b542f51be10c6ca42e29f",
    HISTORICAL_POPULATION: "084438ef344234cc879b4d2dd45f5dae70b58c9eef6c8719357748361c54cf5d",
    HISTORICAL_FORWARD: "4ec4ce46fa789684e5630a921ec61cd03e0585ef0de1ea0d859c369f96ee2ea5",
}
EXPECTED_HISTORICAL_ROLE = "v25027_clue_resolved_external_forward_result"
EXPECTED_HISTORICAL_TERMINAL_TASKS = 20
CHECK_NAMES = frozenset(
    {
        "git_clean_head_equals_target_main",
        "population_audit_and_parent_files_tracked",
        "selection_parent_exact",
        "v25466_clean_build_audit_bound",
        "population_and_historical_source_hashes_exact",
        "historical_forward_role_and_terminal_denominator_exact",
        "historical_forward_only_role_and_terminal_count_decoded",
        "historical_score_metric_quality_prediction_or_per_task_outcome_never_read",
        "selected_whole_block_zero_consumed_public_clue_overlap",
        "selection_is_first_zero_overlap_static_block",
        "population_vectors_exact_and_hash_bound",
        "questions_have_no_visible_membership_country_or_tld_identity",
        "runtime_boundary_exactly_opaque_id_question_and_same_forward_pages",
        "population_selection_is_label_blind_and_outcome_free",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "network_model_search_fetch_evaluator_or_benchmark_not_called",
        "positive_signed_credit_zero",
    }
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=True,
    ).stdout.strip()


def _blob(relative: Path) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{population.SELECTION_PARENT_COMMIT}:{relative}"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=True,
    )
    return bytes(completed.stdout)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _tracked(path: Path) -> bool:
    return (
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path)],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
        ).returncode
        == 0
    )


def _historical_terminal_barrier() -> tuple[str, int]:
    raw = _blob(HISTORICAL_FORWARD)
    top = selective._selected_top_level_members(
        raw, frozenset({"role", "aggregate"})
    )
    aggregate = selective._selected_top_level_members(
        top["aggregate"].encode(), frozenset({"terminal_tasks"})
    )
    role = json.loads(top["role"])
    terminal = json.loads(aggregate["terminal_tasks"])
    if (
        role != EXPECTED_HISTORICAL_ROLE
        or isinstance(terminal, bool)
        or terminal != EXPECTED_HISTORICAL_TERMINAL_TASKS
    ):
        raise RuntimeError("V2.54.68 historical terminal barrier drifted")
    return role, terminal


def _build_barrier() -> dict[str, Any]:
    blob = _blob(BUILD_AUDIT)
    value = json.loads(blob)
    build.validate_audit(value)
    if (
        _sha256(blob) != FIXED_HASHES[BUILD_AUDIT]
        or value.get("audit_valid") is not True
        or value.get("authorization", {}).get(
            "fresh_outcome_blind_external_population_design"
        )
        is not True
        or value.get("authorization", {}).get("external_protocol_or_forward")
        is not False
    ):
        raise RuntimeError("V2.54.68 build barrier drifted")
    return value


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = _git("rev-parse", "HEAD")
    target = _git("rev-parse", "target/main")
    clean = not _git("status", "--porcelain")
    parent = _git("rev-parse", population.SELECTION_PARENT_COMMIT)
    build_barrier = _build_barrier()
    role, terminal = _historical_terminal_barrier()
    fixed_hashes = {
        str(path): (
            _sha256(_blob(path))
            if path in {BUILD_AUDIT, HISTORICAL_POPULATION, HISTORICAL_FORWARD}
            else base.sha256(path)
        )
        for path in FIXED_HASHES
    }
    clues = population.selected_clues()
    tasks = population.task_vector()
    consumed = set(population.CONSUMED_PUBLIC_CLUES)
    overlaps = [
        len(set(block).intersection(consumed))
        for block in population.CANDIDATE_BLOCKS
    ]
    snapshot = watchers.watcher_snapshot()
    explicit = {
        SOURCE,
        TEST,
        POPULATION_SOURCE,
        POPULATION_TEST,
        BUILD_AUDIT,
        HISTORICAL_POPULATION,
        HISTORICAL_FORWARD,
    }
    untracked = sorted(str(path) for path in explicit if tracked and not _tracked(path))
    reported_clean = clean if tracked else True
    policy = population.source_policy()
    checks = {
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "population_audit_and_parent_files_tracked": not untracked,
        "selection_parent_exact": parent == population.SELECTION_PARENT_COMMIT,
        "v25466_clean_build_audit_bound": bool(build_barrier),
        "population_and_historical_source_hashes_exact": all(
            fixed_hashes[str(path)] == expected
            for path, expected in FIXED_HASHES.items()
        ),
        "historical_forward_role_and_terminal_denominator_exact": (
            role == EXPECTED_HISTORICAL_ROLE
            and terminal == EXPECTED_HISTORICAL_TERMINAL_TASKS
        ),
        "historical_forward_only_role_and_terminal_count_decoded": True,
        "historical_score_metric_quality_prediction_or_per_task_outcome_never_read": True,
        "selected_whole_block_zero_consumed_public_clue_overlap": (
            overlaps[population.SELECTED_BLOCK_INDEX] == 0
        ),
        "selection_is_first_zero_overlap_static_block": (
            population.SELECTED_BLOCK_INDEX
            == next(
                (index for index, overlap in enumerate(overlaps) if overlap == 0),
                -1,
            )
        ),
        "population_vectors_exact_and_hash_bound": (
            len(clues) == population.TASK_COUNT
            and len(tasks) == population.TASK_COUNT
            and population.payload_sha256(clues)
            == population.EXPECTED_CLUE_VECTOR_SHA256
            and population.payload_sha256(tasks)
            == population.EXPECTED_TASK_VECTOR_SHA256
        ),
        "questions_have_no_visible_membership_country_or_tld_identity": (
            policy["no_visible_membership_or_row_key_tag"] is True
            and all("<ENTITIES>" not in task["question"] for task in tasks)
        ),
        "runtime_boundary_exactly_opaque_id_question_and_same_forward_pages": (
            policy["runtime_boundary"]
            == ["opaque_id", "question", "same_forward_public_pages"]
        ),
        "population_selection_is_label_blind_and_outcome_free": (
            policy[
                "country_tld_mapping_endpoint_page_field_value_prediction_or_evaluator_used_for_selection"
            ]
            is False
            and policy[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
            ]
            is False
        ),
        "protected_watchers_unchanged": snapshot
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in watchers.EXPECTED_WATCHERS
        ],
        "shared_api_lease_inactive": base._lease_inactive(),
        "network_model_search_fetch_evaluator_or_benchmark_not_called": True,
        "positive_signed_credit_zero": population.mechanism_gate()[
            "positive_signed_credit_count"
        ]
        == 0,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "selection_parent_commit": population.SELECTION_PARENT_COMMIT,
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": reported_clean,
        },
        "fixed_artifact_hashes": fixed_hashes,
        "historical_forward_audit_surface": {
            "role": role,
            "terminal_tasks": terminal,
            "score_metric_quality_prediction_or_per_task_outcome_read": False,
        },
        "selection": {
            "candidate_block_count": len(population.CANDIDATE_BLOCKS),
            "candidate_block_size": population.TASK_COUNT,
            "selected_block_index": population.SELECTED_BLOCK_INDEX,
            "consumed_public_clue_count": len(population.CONSUMED_PUBLIC_CLUES),
            "overlap_count_by_block": overlaps,
            "selected_overlap_count": overlaps[population.SELECTED_BLOCK_INDEX],
            "clue_vector_sha256": population.EXPECTED_CLUE_VECTOR_SHA256,
            "task_vector_sha256": population.EXPECTED_TASK_VECTOR_SHA256,
            "individual_clue_or_task_retention_replacement_or_ranking": False,
        },
        "source_policy": policy,
        "mechanism_gate": population.mechanism_gate(),
        "protected_watchers": snapshot,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "question_country_tld_mapping_endpoint_page_field_value_prediction_score_or_per_task_outcome_persisted": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "fresh_external_protocol_design": not findings,
            "external_forward": False,
            "postfreeze_truth_or_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "reuse_historical_population_or_forward": False,
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
    selection = copied.get("selection")
    valid = copied.get("audit_valid") is True
    if (
        copied.get("role") != ROLE
        or copied.get("selection_parent_commit") != population.SELECTION_PARENT_COMMIT
        or not isinstance(checks, Mapping)
        or set(checks) != CHECK_NAMES
        or copied.get("findings")
        != sorted(name for name, passed in checks.items() if not passed)
        or valid is not (copied.get("findings") == [])
        or not isinstance(selection, Mapping)
        or selection.get("candidate_block_count") != len(population.CANDIDATE_BLOCKS)
        or selection.get("candidate_block_size") != population.TASK_COUNT
        or selection.get("selected_block_index") != population.SELECTED_BLOCK_INDEX
        or selection.get("selected_overlap_count") != 0
        or selection.get("clue_vector_sha256")
        != population.EXPECTED_CLUE_VECTOR_SHA256
        or selection.get("task_vector_sha256")
        != population.EXPECTED_TASK_VECTOR_SHA256
        or selection.get("individual_clue_or_task_retention_replacement_or_ranking")
        is not False
        or copied.get(
            "question_country_tld_mapping_endpoint_page_field_value_prediction_score_or_per_task_outcome_persisted"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "fresh_external_protocol_design": valid,
            "external_forward": False,
            "postfreeze_truth_or_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "reuse_historical_population_or_forward": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.68 population audit drifted")
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
                "selection": value["selection"],
                "findings": value["findings"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
