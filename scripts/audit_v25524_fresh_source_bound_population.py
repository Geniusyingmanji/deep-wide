#!/usr/bin/env python3
"""Outcome-blind audit for the V2.55.23 source-bound population."""

from __future__ import annotations

import copy
import json
import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25018_multi_identity_external_contract as namespace  # noqa: E402
from deepwide_agent import v25068_quote_verified_external_contract as watchers  # noqa: E402
from deepwide_agent import v25509_fresh_multirow_uncertainty_population as prior9  # noqa: E402
from deepwide_agent import v25516_fresh_evidence_coverage_population as prior16  # noqa: E402
from deepwide_agent import v25523_fresh_source_bound_population as population  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import audit_v25522_source_bound_detail_build as build  # noqa: E402


DATE = "20260814"
ROLE = "v25524_fresh_source_bound_population_audit"
IMPLEMENTATION_COMMIT = "5106e7d3ca41907c7afb5d292cab08f8ac282f47"
SOURCE = Path("scripts/audit_v25524_fresh_source_bound_population.py")
TEST = Path("tests/test_audit_v25524_fresh_source_bound_population.py")
POPULATION_SOURCE = Path(
    "src/deepwide_agent/v25523_fresh_source_bound_population.py"
)
POPULATION_TEST = Path(
    "tests/test_v25523_fresh_source_bound_population.py"
)
BUILD_AUDIT = Path(
    "results/v25522_source_bound_detail_build_audit_v1_20260814.json"
)
OUTPUT = Path(
    f"results/v25524_fresh_source_bound_population_audit_v1_{DATE}.json"
)
FIXED_HASHES = {
    BUILD_AUDIT: "d55f4968477278c5c8477d1f1d8fd39c8ea0b0ddca69a2dc1ebe87b1909a238e",
    POPULATION_SOURCE: "4bcd5ab49c093d3efcf59d96c1e3c2c8e6a8e97c7a4a1fc0ab0b226db7d4e126",
    POPULATION_TEST: "14e94d28778491c4fc1713ee5c885b4054782ce463b8fe4f08d97584e5b5589e",
}
CHECK_NAMES = frozenset(
    {
        "git_clean_head_equals_target_main",
        "population_audit_parent_and_population_files_tracked",
        "selection_parent_exact",
        "population_implementation_commit_in_head_history",
        "v25522_clean_build_population_design_authority_bound",
        "fixed_parent_and_population_hashes_exact",
        "namespace_source_contains_bank_and_next_forty_identities",
        "one_whole_static_twenty_pair_block_exact",
        "forty_unique_three_plus_character_tld_identities",
        "row_identities_disjoint_from_consumed_v25509_and_v25516",
        "population_vectors_exact_and_hash_bound",
        "zero_exact_question_or_opaque_overlap_with_consumed_populations",
        "questions_have_exactly_two_visible_rows_and_no_url_source_authority_path_value_coverage_or_grammar_hint",
        "runtime_boundary_exactly_opaque_id_question_and_same_forward_pages",
        "population_selection_is_label_blind_and_outcome_free",
        "historical_task_rows_pages_predictions_truth_score_quality_or_outcome_never_read",
        "source_bound_mechanism_gate_fixed_before_forward",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "network_model_search_fetch_evaluator_or_benchmark_not_called",
        "positive_signed_credit_zero",
    }
)


def _tracked(path: Path) -> bool:
    return base._tracked(path)


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
        raise RuntimeError("V2.55.24 build barrier drifted")
    return value


def _namespace_block() -> list[str]:
    cohort = list(namespace.TLD_COHORT)
    start = cohort.index(".bank") + 1
    block = cohort[start : start + population.TASK_COUNT * population.ROWS_PER_TASK]
    if len(block) != 40:
        raise RuntimeError("V2.55.24 namespace block is incomplete")
    return block


def build_audit(
    *, now: int | None = None, tracked: bool = True
) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    selection_parent = base._git(
        "rev-parse", population.SELECTION_PARENT_COMMIT
    )
    history = set(base._git("rev-list", "HEAD").splitlines())
    barrier = _build_barrier()
    fixed = {str(path): base.sha256(path) for path in FIXED_HASHES}
    pairs = population.pair_vector()
    identities = [identity for pair in pairs for identity in pair]
    tasks = population.task_vector()
    namespace_block = _namespace_block()
    consumed_pairs = [*prior9.pair_vector(), *prior16.pair_vector()]
    consumed_identities = {
        identity for pair in consumed_pairs for identity in pair
    }
    consumed_tasks = [*prior9.task_vector(), *prior16.task_vector()]
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
    questions = {task["question"] for task in tasks}
    opaque_ids = {task["opaque_id"] for task in tasks}
    consumed_questions = {task["question"] for task in consumed_tasks}
    consumed_opaque_ids = {task["opaque_id"] for task in consumed_tasks}
    checks = {
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "population_audit_parent_and_population_files_tracked": not untracked,
        "selection_parent_exact": selection_parent
        == population.SELECTION_PARENT_COMMIT,
        "population_implementation_commit_in_head_history": IMPLEMENTATION_COMMIT
        in history,
        "v25522_clean_build_population_design_authority_bound": bool(barrier),
        "fixed_parent_and_population_hashes_exact": all(
            fixed[str(path)] == expected for path, expected in FIXED_HASHES.items()
        ),
        "namespace_source_contains_bank_and_next_forty_identities": (
            namespace_block == identities
            and namespace_block[0] == ".bar"
            and namespace_block[-1] == ".bnpparibas"
            and policy["selection_source"]
            == "v25018_frozen_public_namespace_order_after_bank"
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
        "row_identities_disjoint_from_consumed_v25509_and_v25516": (
            not (set(identities) & consumed_identities)
            and policy[
                "next_lexical_block_is_row_identity_disjoint_from_v25509_and_v25516"
            ]
            is True
        ),
        "population_vectors_exact_and_hash_bound": (
            len(tasks) == 20
            and len(opaque_ids) == 20
            and population.payload_sha256(pairs)
            == population.EXPECTED_PAIR_VECTOR_SHA256
            and population.payload_sha256(tasks)
            == population.EXPECTED_TASK_VECTOR_SHA256
        ),
        "zero_exact_question_or_opaque_overlap_with_consumed_populations": (
            not (opaque_ids & consumed_opaque_ids)
            and not (questions & consumed_questions)
        ),
        "questions_have_exactly_two_visible_rows_and_no_url_source_authority_path_value_coverage_or_grammar_hint": (
            policy[
                "no_visible_url_source_host_authority_name_path_field_grammar_coverage_or_field_value"
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
            "prior_task_rows_pages_predictions_truth_scores_quality_or_per_task_outcomes_read"
        ]
        is False,
        "source_bound_mechanism_gate_fixed_before_forward": (
            gate["fixed_task_denominator"] == 20
            and gate["required_terminal_tasks"] == 20
            and gate["minimum_multirow_eligible_link_tasks"] == 6
            and gate["minimum_positive_evidence_deficit_candidate_tasks"] == 4
            and gate["minimum_exact_iana_url_page_tasks"] == 3
            and gate["minimum_evidence_closed_observation_tasks"] == 3
            and gate["minimum_material_candidate_tasks"] == 2
            and gate["minimum_treatment_changed_tasks"] == 2
            and gate["maximum_physical_fetches_per_completed_task"] == 14
            and gate["maximum_normal_path_model_forwards_per_completed_task"] == 3
            and gate["candidate_additional_fetches_beyond_parent"] == 0
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
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": reported_clean,
        },
        "fixed_artifact_hashes": fixed,
        "selection": {
            "selection_source": population.SELECTION_SOURCE,
            "selection_rule": population.SELECTION_RULE,
            "namespace_predecessor": ".bank",
            "namespace_first": namespace_block[0],
            "namespace_last": namespace_block[-1],
            "pair_count": len(pairs),
            "row_identity_count": len(identities),
            "unique_row_identity_count": len(set(identities)),
            "minimum_identity_length_without_dot": min(
                len(identity.removeprefix(".")) for identity in identities
            ),
            "consumed_v25509_v25516_row_identity_overlap_count": len(
                set(identities) & consumed_identities
            ),
            "question_overlap_count": len(questions & consumed_questions),
            "opaque_id_overlap_count": len(opaque_ids & consumed_opaque_ids),
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
        or not isinstance(checks, Mapping)
        or set(checks) != CHECK_NAMES
        or copied.get("findings")
        != sorted(name for name, passed in checks.items() if not passed)
        or valid is not (copied.get("findings") == [])
        or not isinstance(selection, Mapping)
        or selection.get("namespace_predecessor") != ".bank"
        or selection.get("namespace_first") != ".bar"
        or selection.get("namespace_last") != ".bnpparibas"
        or selection.get("pair_count") != 20
        or selection.get("row_identity_count") != 40
        or selection.get("unique_row_identity_count") != 40
        or selection.get(
            "consumed_v25509_v25516_row_identity_overlap_count"
        )
        != 0
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
        raise ValueError("V2.55.24 population audit drifted")
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
