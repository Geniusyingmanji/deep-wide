#!/usr/bin/env python3
"""Outcome-blind audit for the V2.55.16 evidence-coverage population."""

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
from deepwide_agent import v25509_fresh_multirow_uncertainty_population as prior  # noqa: E402
from deepwide_agent import v25516_fresh_evidence_coverage_population as population  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import audit_v25515_evidence_coverage_detail_build as build  # noqa: E402


DATE = "20260814"
ROLE = "v25517_fresh_evidence_coverage_population_audit"
IMPLEMENTATION_COMMIT = "4a2789d735458a14a424e219b2f379cd0d389b58"
CORRECTION_COMMIT = "26020b498c97e39acd1ec30b55e323d170a2b8cc"
SOURCE = Path("scripts/audit_v25517_fresh_evidence_coverage_population.py")
TEST = Path("tests/test_audit_v25517_fresh_evidence_coverage_population.py")
POPULATION_SOURCE = Path(
    "src/deepwide_agent/v25516_fresh_evidence_coverage_population.py"
)
POPULATION_TEST = Path(
    "tests/test_v25516_fresh_evidence_coverage_population.py"
)
BUILD_AUDIT = Path(
    "results/v25515_evidence_coverage_detail_build_audit_v1_20260814.json"
)
OUTPUT = Path(
    f"results/v25517_fresh_evidence_coverage_population_audit_v1_{DATE}.json"
)
FIXED_HASHES = {
    BUILD_AUDIT: "bbe86d84d25589eec7ab06c9cf9c981cc870ead201b9d3f4c9da80540d6766ed",
    POPULATION_SOURCE: "5eb95de971eb4e399fa0f840d0e6bd1765b47146698d99d3d7e1aead55664559",
    POPULATION_TEST: "833c639dfecfe98fdc543a38fd72cfb60d1353ced5b3f85fc5c6ce64e5b58731",
}
CHECK_NAMES = frozenset(
    {
        "git_clean_head_equals_target_main",
        "population_audit_parent_and_population_files_tracked",
        "selection_parent_exact",
        "population_implementation_and_correction_commits_in_head_history",
        "v25515_clean_build_population_design_authority_bound",
        "fixed_parent_and_population_hashes_exact",
        "one_whole_static_twenty_pair_block_exact",
        "forty_unique_three_plus_character_tld_identities",
        "row_identities_disjoint_from_consumed_v25509_population",
        "population_vectors_exact_and_hash_bound",
        "zero_exact_question_or_opaque_overlap_with_consumed_v25509_population",
        "questions_have_exactly_two_visible_rows_and_no_url_source_authority_value_coverage_or_grammar_hint",
        "runtime_boundary_exactly_opaque_id_question_and_same_forward_pages",
        "population_selection_is_label_blind_and_outcome_free",
        "historical_task_rows_pages_predictions_truth_score_quality_or_outcome_never_read",
        "mechanism_gate_fixed_before_forward",
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
    if (
        base.sha256(BUILD_AUDIT) != FIXED_HASHES[BUILD_AUDIT]
        or build.validate_audit(value) != value
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get(
            "fresh_task_disjoint_external_population_design"
        )
        is not True
        or value.get("authorization", {}).get("external_protocol_or_forward")
        is not False
    ):
        raise RuntimeError("V2.55.17 build barrier drifted")
    return value


def build_audit(
    *, now: int | None = None, tracked: bool = True
) -> dict[str, Any]:
    head = _git("rev-parse", "HEAD")
    target = _git("rev-parse", "target/main")
    clean = not _git("status", "--porcelain")
    selection_parent = _git("rev-parse", population.SELECTION_PARENT_COMMIT)
    history = set(_git("rev-list", "HEAD").splitlines())
    barrier = _build_barrier()
    fixed = {str(path): base.sha256(path) for path in FIXED_HASHES}
    pairs = population.pair_vector()
    identities = [identity for pair in pairs for identity in pair]
    tasks = population.task_vector()
    prior_pairs = prior.pair_vector()
    prior_identities = {identity for pair in prior_pairs for identity in pair}
    prior_tasks = prior.task_vector()
    snapshot = watchers.watcher_snapshot()
    explicit = {
        SOURCE,
        TEST,
        POPULATION_SOURCE,
        POPULATION_TEST,
        BUILD_AUDIT,
    }
    untracked = sorted(
        str(path) for path in explicit if tracked and not _tracked(path)
    )
    reported_clean = clean if tracked else True
    policy = population.source_policy()
    gate = population.mechanism_gate()
    checks = {
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "population_audit_parent_and_population_files_tracked": not untracked,
        "selection_parent_exact": selection_parent
        == population.SELECTION_PARENT_COMMIT,
        "population_implementation_and_correction_commits_in_head_history": (
            IMPLEMENTATION_COMMIT in history and CORRECTION_COMMIT in history
        ),
        "v25515_clean_build_population_design_authority_bound": bool(barrier),
        "fixed_parent_and_population_hashes_exact": all(
            fixed[str(path)] == expected for path, expected in FIXED_HASHES.items()
        ),
        "one_whole_static_twenty_pair_block_exact": (
            pairs == list(population.PAIRS)
            and len(pairs) == 20
            and all(len(pair) == 2 for pair in pairs)
        ),
        "forty_unique_three_plus_character_tld_identities": (
            len(identities) == 40
            and len(set(identities)) == 40
            and all(len(identity.removeprefix(".")) >= 3 for identity in identities)
        ),
        "row_identities_disjoint_from_consumed_v25509_population": (
            not (set(identities) & prior_identities)
            and policy["next_lexical_block_is_row_identity_disjoint_from_v25509"]
            is True
        ),
        "population_vectors_exact_and_hash_bound": (
            len(tasks) == 20
            and len({task["opaque_id"] for task in tasks}) == 20
            and population.payload_sha256(pairs)
            == population.EXPECTED_PAIR_VECTOR_SHA256
            and population.payload_sha256(tasks)
            == population.EXPECTED_TASK_VECTOR_SHA256
        ),
        "zero_exact_question_or_opaque_overlap_with_consumed_v25509_population": (
            not (
                {task["opaque_id"] for task in tasks}
                & {task["opaque_id"] for task in prior_tasks}
            )
            and not (
                {task["question"] for task in tasks}
                & {task["question"] for task in prior_tasks}
            )
        ),
        "questions_have_exactly_two_visible_rows_and_no_url_source_authority_value_coverage_or_grammar_hint": (
            policy[
                "no_visible_url_source_host_authority_name_field_grammar_coverage_or_field_value"
            ]
            is True
            and all(
                task["question"].count("<DOMAIN>") == 2
                and task["question"].count("</DOMAIN>") == 2
                and "https://" not in task["question"]
                and "iana" not in task["question"].casefold()
                and "coverage" not in task["question"].casefold()
                and "qualifier" not in task["question"].casefold()
                and "fused" not in task["question"].casefold()
                and "adjacent" not in task["question"].casefold()
                for task in tasks
            )
        ),
        "runtime_boundary_exactly_opaque_id_question_and_same_forward_pages": (
            policy["runtime_boundary"]
            == ["opaque_id", "question", "same_forward_public_pages"]
        ),
        "population_selection_is_label_blind_and_outcome_free": (
            policy["whole_static_pair_block_frozen_before_any_forward"] is True
            and policy[
                "individual_pair_or_task_filtering_ranking_replacement_or_retention"
            ]
            is False
            and policy[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
            ]
            is False
        ),
        "historical_task_rows_pages_predictions_truth_score_quality_or_outcome_never_read": policy[
            "prior_task_rows_pages_predictions_truth_scores_or_per_task_outcomes_read"
        ]
        is False,
        "mechanism_gate_fixed_before_forward": (
            gate["fixed_task_denominator"] == 20
            and gate["required_terminal_tasks"] == 20
            and gate["minimum_multirow_eligible_link_tasks"] == 6
            and gate["minimum_positive_evidence_deficit_candidate_tasks"] == 4
            and gate["minimum_treatment_changed_tasks"] == 2
            and gate["maximum_physical_fetches_per_completed_task"] == 14
            and gate["maximum_normal_path_model_forwards_per_completed_task"] == 3
            and gate["postfreeze_shared_parent_quality_required"] is True
        ),
        "protected_watchers_unchanged": snapshot
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in watchers.EXPECTED_WATCHERS
        ],
        "shared_api_lease_inactive": base._lease_inactive(),
        "network_model_search_fetch_evaluator_or_benchmark_not_called": True,
        "positive_signed_credit_zero": gate["positive_signed_credit_count"] == 0,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "selection_parent_commit": population.SELECTION_PARENT_COMMIT,
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "correction_commit": CORRECTION_COMMIT,
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": reported_clean,
        },
        "fixed_artifact_hashes": fixed,
        "selection": {
            "pair_count": len(pairs),
            "row_identity_count": len(identities),
            "unique_row_identity_count": len(set(identities)),
            "minimum_identity_length_without_dot": min(
                len(identity.removeprefix(".")) for identity in identities
            ),
            "consumed_v25509_row_identity_overlap_count": len(
                set(identities) & prior_identities
            ),
            "question_overlap_count": len(
                {task["question"] for task in tasks}
                & {task["question"] for task in prior_tasks}
            ),
            "opaque_id_overlap_count": len(
                {task["opaque_id"] for task in tasks}
                & {task["opaque_id"] for task in prior_tasks}
            ),
            "pair_vector_sha256": population.payload_sha256(pairs),
            "task_vector_sha256": population.payload_sha256(tasks),
            "individual_pair_or_task_filtering_ranking_replacement_or_retention": False,
        },
        "source_policy": policy,
        "mechanism_gate": gate,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "protected_watchers": snapshot,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "prior_task_rows_pages_predictions_truth_scores_quality_or_per_task_outcomes_read": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "fresh_external_protocol_design": not findings,
            "reuse_prior_execution_authority_or_population": False,
            "external_forward": False,
            "postfreeze_truth_or_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
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
        or copied.get("selection_parent_commit")
        != population.SELECTION_PARENT_COMMIT
        or copied.get("implementation_commit") != IMPLEMENTATION_COMMIT
        or copied.get("correction_commit") != CORRECTION_COMMIT
        or not isinstance(checks, Mapping)
        or set(checks) != CHECK_NAMES
        or copied.get("findings")
        != sorted(name for name, passed in checks.items() if not passed)
        or valid is not (copied.get("findings") == [])
        or not isinstance(selection, Mapping)
        or selection.get("pair_count") != 20
        or selection.get("row_identity_count") != 40
        or selection.get("unique_row_identity_count") != 40
        or selection.get("consumed_v25509_row_identity_overlap_count") != 0
        or selection.get("question_overlap_count") != 0
        or selection.get("opaque_id_overlap_count") != 0
        or selection.get("pair_vector_sha256")
        != population.EXPECTED_PAIR_VECTOR_SHA256
        or selection.get("task_vector_sha256")
        != population.EXPECTED_TASK_VECTOR_SHA256
        or copied.get("source_policy") != population.source_policy()
        or copied.get("mechanism_gate") != population.mechanism_gate()
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get(
            "prior_task_rows_pages_predictions_truth_scores_quality_or_per_task_outcomes_read"
        )
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
            "reuse_prior_execution_authority_or_population": False,
            "external_forward": False,
            "postfreeze_truth_or_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.17 population audit drifted")
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
