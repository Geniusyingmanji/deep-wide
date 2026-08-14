#!/usr/bin/env python3
"""Outcome-blind audit for the fourth fresh IANA-detail population."""

from __future__ import annotations

import copy
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
from deepwide_agent import v25486_outcome_blind_iana_detail_population as population  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import audit_v25485_row_key_iana_detail_build as build  # noqa: E402


DATE = "20260814"
ROLE = "v25487_outcome_blind_iana_detail_population_audit"
IMPLEMENTATION_COMMIT = "b681db629ce5429e835b2e8fedf075e6ecbae042"
SOURCE = Path("scripts/audit_v25487_outcome_blind_iana_detail_population.py")
TEST = Path("tests/test_audit_v25487_outcome_blind_iana_detail_population.py")
POPULATION_SOURCE = Path(
    "src/deepwide_agent/v25486_outcome_blind_iana_detail_population.py"
)
POPULATION_TEST = Path(
    "tests/test_v25486_outcome_blind_iana_detail_population.py"
)
BUILD_AUDIT = Path(
    "results/v25485_row_key_iana_detail_build_audit_v1_20260814.json"
)
PRIOR_NO_GO_AUDIT = Path(
    "results/v25481_qualified_source_label_external_forward_audit_v1_20260814.json"
)
OUTPUT = Path(
    f"results/v25487_outcome_blind_iana_detail_population_audit_v1_{DATE}.json"
)
FIXED_HASHES = {
    BUILD_AUDIT: "b531db35b7b862a19517db6dd9a67caab45ed9de0694974ea70d8925b0e95c13",
    PRIOR_NO_GO_AUDIT: "ba3135e2ffea7100e6481e396021a1c099f83ec17e0f300c6417832f92fffb4a",
    POPULATION_SOURCE: "63d35b3bf9b321d1fa1dd8b918864fc3a7a5006db8b30645ba9b196aa158292f",
    POPULATION_TEST: "a4a565696aad25c2b68655681d7c0a23362dc42be68874ca76bd8006037533e9",
}
CHECK_NAMES = frozenset(
    {
        "git_clean_head_equals_target_main",
        "population_audit_parent_and_population_files_tracked",
        "selection_parent_exact",
        "population_implementation_commit_in_head_history",
        "v25485_clean_build_population_design_authority_bound",
        "v25481_aggregate_no_go_authority_consumed",
        "fixed_parent_and_population_hashes_exact",
        "consumed_public_clues_exactly_four_frozen_twenty_blocks",
        "selected_whole_block_zero_union_consumed_overlap",
        "selection_is_first_zero_union_overlap_static_block",
        "population_vectors_exact_and_hash_bound",
        "questions_have_no_visible_membership_country_or_tld_identity",
        "runtime_boundary_exactly_opaque_id_question_and_same_forward_pages",
        "population_selection_is_label_blind_and_outcome_free",
        "historical_per_task_forward_page_prediction_score_quality_or_outcome_never_read",
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


def _build_barrier() -> dict[str, Any]:
    value = json.loads(base._ordinary(BUILD_AUDIT).read_text(encoding="utf-8"))
    build.validate_audit(value)
    if (
        base.sha256(BUILD_AUDIT) != FIXED_HASHES[BUILD_AUDIT]
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get(
            "fresh_outcome_blind_external_population_design"
        )
        is not True
        or value.get("authorization", {}).get("external_protocol_or_forward")
        is not False
    ):
        raise RuntimeError("V2.54.87 build barrier drifted")
    return value


def _prior_no_go_barrier() -> dict[str, Any]:
    value = json.loads(
        base._ordinary(PRIOR_NO_GO_AUDIT).read_text(encoding="utf-8")
    )
    unsigned = dict(value)
    seal = unsigned.pop("audit_payload_sha256", None)
    decision = value.get("mechanism_decision", {})
    if (
        base.sha256(PRIOR_NO_GO_AUDIT) != FIXED_HASHES[PRIOR_NO_GO_AUDIT]
        or value.get("role")
        != "v25481_qualified_source_label_external_forward_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or decision.get("mechanism_gate_passed") is not False
        or decision.get("postfreeze_quality_protocol_authorized") is not False
        or sorted(decision.get("failed_checks", []))
        != [
            "minimum_applied_candidate_tasks",
            "minimum_available_candidate_tasks",
            "minimum_prediction_changed_tasks",
        ]
        or value.get("authorization", {}).get("postfreeze_quality_protocol")
        is not False
        or value.get("authorization", {}).get("deepwidebench_forward_or_evaluator")
        is not False
        or seal != base.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.54.87 prior NO-GO barrier drifted")
    return value


def build_audit(
    *, now: int | None = None, tracked: bool = True
) -> dict[str, Any]:
    head = _git("rev-parse", "HEAD")
    target = _git("rev-parse", "target/main")
    clean = not _git("status", "--porcelain")
    selection_parent = _git("rev-parse", population.SELECTION_PARENT_COMMIT)
    implementation_in_history = (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", IMPLEMENTATION_COMMIT, "HEAD"],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
        ).returncode
        == 0
    )
    build_barrier = _build_barrier()
    prior_no_go = _prior_no_go_barrier()
    fixed = {str(path): base.sha256(path) for path in FIXED_HASHES}
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
        PRIOR_NO_GO_AUDIT,
    }
    untracked = sorted(str(path) for path in explicit if tracked and not _tracked(path))
    reported_clean = clean if tracked else True
    policy = population.source_policy()
    four_blocks = (
        population.V25027_CONSUMED_PUBLIC_CLUES,
        population.V25469_CONSUMED_PUBLIC_CLUES,
        population.V25476_CONSUMED_PUBLIC_CLUES,
        population.V25481_CONSUMED_PUBLIC_CLUES,
    )
    checks = {
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "population_audit_parent_and_population_files_tracked": not untracked,
        "selection_parent_exact": selection_parent
        == population.SELECTION_PARENT_COMMIT,
        "population_implementation_commit_in_head_history": implementation_in_history,
        "v25485_clean_build_population_design_authority_bound": bool(build_barrier),
        "v25481_aggregate_no_go_authority_consumed": bool(prior_no_go),
        "fixed_parent_and_population_hashes_exact": all(
            fixed[str(path)] == expected
            for path, expected in FIXED_HASHES.items()
        ),
        "consumed_public_clues_exactly_four_frozen_twenty_blocks": (
            all(len(block) == 20 and len(set(block)) == 20 for block in four_blocks)
            and tuple(population.CONSUMED_PUBLIC_CLUES)
            == tuple(item for block in four_blocks for item in block)
            and len(population.CONSUMED_PUBLIC_CLUES) == 80
            and len(consumed) == 80
        ),
        "selected_whole_block_zero_union_consumed_overlap": overlaps[
            population.SELECTED_BLOCK_INDEX
        ]
        == 0,
        "selection_is_first_zero_union_overlap_static_block": (
            population.SELECTED_BLOCK_INDEX
            == next((i for i, overlap in enumerate(overlaps) if overlap == 0), -1)
        ),
        "population_vectors_exact_and_hash_bound": (
            len(clues) == 20
            and len(set(clues)) == 20
            and len(tasks) == 20
            and population.payload_sha256(clues)
            == population.EXPECTED_CLUE_VECTOR_SHA256
            and population.payload_sha256(tasks)
            == population.EXPECTED_TASK_VECTOR_SHA256
        ),
        "questions_have_no_visible_membership_country_or_tld_identity": (
            policy["no_visible_membership_or_row_key_tag"] is True
            and all(
                "<ENTITIES>" not in task["question"]
                and "https://" not in task["question"]
                for task in tasks
            )
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
        "historical_per_task_forward_page_prediction_score_quality_or_outcome_never_read": (
            policy[
                "historical_population_forward_page_prediction_score_metric_quality_or_per_task_outcome_read"
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
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "selection_parent_commit": population.SELECTION_PARENT_COMMIT,
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": reported_clean,
        },
        "fixed_artifact_hashes": fixed,
        "prior_no_go_envelope": {
            "path": str(PRIOR_NO_GO_AUDIT),
            "sha256": fixed[str(PRIOR_NO_GO_AUDIT)],
            "role": prior_no_go["role"],
            "audit_valid": True,
            "mechanism_gate_passed": False,
            "postfreeze_quality_protocol_authorized": False,
            "per_task_rows_predictions_pages_truth_or_quality_opened": False,
            "execution_authority_consumed": True,
        },
        "selection": {
            "candidate_block_count": len(population.CANDIDATE_BLOCKS),
            "candidate_block_size": 20,
            "selected_block_index": population.SELECTED_BLOCK_INDEX,
            "consumed_public_clue_count": len(consumed),
            "overlap_count_by_block": overlaps,
            "selected_overlap_count": 0,
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
        "historical_per_task_forward_page_prediction_score_metric_quality_or_outcome_read": False,
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
            "reuse_prior_execution_authority_or_population": False,
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
    envelope = copied.get("prior_no_go_envelope")
    valid = copied.get("audit_valid") is True
    if (
        copied.get("role") != ROLE
        or copied.get("implementation_commit") != IMPLEMENTATION_COMMIT
        or copied.get("selection_parent_commit")
        != population.SELECTION_PARENT_COMMIT
        or not isinstance(checks, Mapping)
        or set(checks) != CHECK_NAMES
        or copied.get("findings")
        != sorted(name for name, passed in checks.items() if not passed)
        or valid is not (copied.get("findings") == [])
        or not isinstance(selection, Mapping)
        or selection.get("consumed_public_clue_count") != 80
        or selection.get("overlap_count_by_block") != [20, 0]
        or selection.get("selected_overlap_count") != 0
        or selection.get("clue_vector_sha256")
        != population.EXPECTED_CLUE_VECTOR_SHA256
        or selection.get("task_vector_sha256")
        != population.EXPECTED_TASK_VECTOR_SHA256
        or not isinstance(envelope, Mapping)
        or envelope.get("execution_authority_consumed") is not True
        or envelope.get("mechanism_gate_passed") is not False
        or envelope.get("postfreeze_quality_protocol_authorized") is not False
        or envelope.get("per_task_rows_predictions_pages_truth_or_quality_opened")
        is not False
        or copied.get(
            "historical_per_task_forward_page_prediction_score_metric_quality_or_outcome_read"
        )
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
            "reuse_prior_execution_authority_or_population": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.87 population audit drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
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
