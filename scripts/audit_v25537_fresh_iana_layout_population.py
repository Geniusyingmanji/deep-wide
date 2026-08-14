#!/usr/bin/env python3
"""Label-blind audit for the V2.55.36 fresh IANA-layout population."""

from __future__ import annotations

import copy
import importlib
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

from deepwide_agent import v25068_quote_verified_external_contract as watchers  # noqa: E402
from deepwide_agent import v25527_independent_iana_shape_study as research  # noqa: E402
from deepwide_agent import v25532_official_tld_population_selection as consumed  # noqa: E402
from deepwide_agent import v25536_fresh_iana_layout_population as population  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import audit_v25531_iana_layout_build as build  # noqa: E402
from scripts import run_v25535_skip_consumed_tld_selection as selection_runner  # noqa: E402


DATE = "20260814"
ROLE = "v25537_fresh_iana_layout_population_audit"
POPULATION_COMMIT = "69e109527258c898b122b2e48eee12b9df218d5b"
SOURCE = Path("scripts/audit_v25537_fresh_iana_layout_population.py")
TEST = Path("tests/test_audit_v25537_fresh_iana_layout_population.py")
POPULATION_SOURCE = Path(
    "src/deepwide_agent/v25536_fresh_iana_layout_population.py"
)
POPULATION_TEST = Path(
    "tests/test_v25536_fresh_iana_layout_population.py"
)
BUILD_AUDIT = Path(
    "results/v25531_iana_layout_build_audit_v1_20260814.json"
)
SELECTION_SNAPSHOT = Path(
    "results/v25535_skip_consumed_tld_selection_v1_20260814.json"
)
SELECTION_SOURCE = Path(
    "src/deepwide_agent/v25534_skip_consumed_tld_selection.py"
)
SELECTION_RUNNER = Path(
    "scripts/run_v25535_skip_consumed_tld_selection.py"
)
OUTPUT = Path(
    f"results/v25537_fresh_iana_layout_population_audit_v1_{DATE}.json"
)
FIXED_HASHES = {
    BUILD_AUDIT: "d38ab902a0474fd1a6852582b04d89cdb18a440602312f7d761ec6ba0f421405",
    SELECTION_SNAPSHOT: "c64cc6a5bb79fd37e7ee0837e17d9911e649c5ea0e9061e95385bd69afe8a6d7",
    SELECTION_SOURCE: "c99b7a3d8fff9626acbc932533c4c5ed379800545e5a8fd9dc63dfaa1545ea6b",
    SELECTION_RUNNER: "2a0f69b399a53cf0996361f5df5dd2b0ecbf850831ffb2ec2ab6443db56fca34",
    POPULATION_SOURCE: "03606b5661380b26d0c931fcb100b8ec58730b417b489ce8d970e0f977b75f44",
    POPULATION_TEST: "27efcd39e57a3784d2430a8d3442aa3161974b6ec80414d0f8cfd02addffaa73",
}
HISTORICAL_TASK_MODULES = (
    "v24789_cross_tab_population_contract",
    "v25351_fresh_pep_grounded_fact_population",
    "v25356_second_fresh_pep_grounded_fact_population",
    "v25364_third_fresh_pep_partial_field_population",
    "v25372_fresh_rfc_multiline_population",
    "v25385_fresh_rfc_joint_population",
    "v25391_fresh_rfc_hybrid_population",
    "v25397_fresh_rfc_visible_membership_population",
    "v25403_fresh_rfc_grounded_membership_population",
    "v25413_fresh_paired_rfc_route_population",
    "v25421_fresh_rfc_list_atomic_population",
    "v25427_structurally_disjoint_rfc_population",
    "v25436_structurally_disjoint_source_authoritative_population",
    "v25442_structurally_disjoint_key_anchored_population",
    "v25452_structurally_disjoint_official_xml_population",
    "v25459_structurally_disjoint_date_bounded_official_xml_population",
    "v25467_outcome_blind_row_key_source_population",
    "v25474_outcome_blind_qualified_label_population",
    "v25479_outcome_blind_qualified_label_population",
    "v25486_outcome_blind_iana_detail_population",
    "v25494_fresh_visible_row_key_population",
    "v25502_fresh_generic_mechanical_population",
    "v25509_fresh_multirow_uncertainty_population",
    "v25516_fresh_evidence_coverage_population",
    "v25523_fresh_source_bound_population",
)
EXPECTED_HISTORICAL_PATH_VECTOR_SHA256 = (
    "33164b6d5a9890443a4ef61296d1092ec5dffda55b9e356e24ca6869497eec34"
)
EXPECTED_HISTORICAL_MANIFEST_SHA256 = (
    "4e7bbcbf871d63bfd5ba64adcf1d82b9cb6191a9c708160e9f579be564a1c36f"
)
EXPECTED_HISTORICAL_TASK_VECTOR_SHA256 = (
    "f3b8f30256c57409a0ea67c2315b666f0f378b58e95f5b48e29da51abca2e76e"
)
EXPECTED_CONSUMED_IDENTITY_COUNT = 260
EXPECTED_CONSUMED_IDENTITY_VECTOR_SHA256 = (
    "4cf1138cd6343170746159c6684d9214bd36f27a482bcbfe7dbeb1470d4f27bc"
)
CHECK_NAMES = frozenset(
    {
        "git_clean_head_equals_target_main",
        "audit_population_and_barrier_files_tracked",
        "selection_parent_exact_and_population_commit_in_history",
        "v25531_clean_build_population_design_authority_bound",
        "v25535_selection_snapshot_population_exact",
        "fixed_barrier_selection_population_hashes_exact",
        "one_whole_static_twenty_pair_block_exact",
        "forty_unique_three_plus_character_tld_identities",
        "complete_consumed_identity_closure_exact_and_disjoint",
        "v25527_research_identities_permanently_excluded",
        "all_historical_task_population_modules_exact_and_unique",
        "zero_exact_question_or_opaque_overlap_with_all_historical_populations",
        "population_vectors_exact_and_hash_bound",
        "questions_expose_only_two_rows_and_schema_without_layout_hint",
        "runtime_boundary_exactly_opaque_id_question_and_same_forward_pages",
        "population_selection_is_label_blind_and_outcome_free",
        "historical_rows_pages_predictions_truth_score_quality_or_outcome_never_read",
        "atomic_iana_layout_mechanism_gate_fixed_before_forward",
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
        raise RuntimeError("V2.55.37 build barrier drifted")
    return value


def _selection_barrier() -> dict[str, Any]:
    value = json.loads(
        base._ordinary(SELECTION_SNAPSHOT).read_text(encoding="utf-8")
    )
    selection_runner.validate_snapshot(value)
    selected = value["selection"]["selected_identities"]
    pairs = value["selection"]["pairs"]
    if (
        base.sha256(SELECTION_SNAPSHOT) != FIXED_HASHES[SELECTION_SNAPSHOT]
        or selected
        != [identity for pair in population.PAIRS for identity in pair]
        or pairs != [list(pair) for pair in population.PAIRS]
        or value["selection"]["consumed_identity_overlap_count"] != 0
        or value["selection"]["first_forty_unconsumed_in_official_order"]
        is not True
        or value["authorization"]["materialize_selected_population_module"]
        is not True
        or value["authorization"]["external_mechanism_or_quality_forward"]
        is not False
    ):
        raise RuntimeError("V2.55.37 selection barrier drifted")
    return value


def _historical_task_closure() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    manifest: list[dict[str, Any]] = []
    tasks: list[dict[str, str]] = []
    paths = [
        f"src/deepwide_agent/{module_name}.py"
        for module_name in HISTORICAL_TASK_MODULES
    ]
    for module_name, relative in zip(HISTORICAL_TASK_MODULES, paths, strict=True):
        module = importlib.import_module(f"deepwide_agent.{module_name}")
        vector = module.task_vector()
        if not isinstance(vector, list) or any(
            not isinstance(row, Mapping)
            or set(row) != {"opaque_id", "question"}
            for row in vector
        ):
            raise RuntimeError(f"V2.55.37 invalid historical vector: {relative}")
        copied = [
            {"opaque_id": str(row["opaque_id"]), "question": str(row["question"])}
            for row in vector
        ]
        manifest.append(
            {
                "path": relative,
                "policy_id": module.POLICY_ID,
                "task_count": len(copied),
                "task_vector_sha256": base.payload_sha256(copied),
            }
        )
        tasks.extend(copied)
    if (
        len(manifest) != 25
        or len(tasks) != 508
        or len({row["question"] for row in tasks}) != 508
        or len({row["opaque_id"] for row in tasks}) != 508
        or base.payload_sha256(paths) != EXPECTED_HISTORICAL_PATH_VECTOR_SHA256
        or base.payload_sha256(manifest) != EXPECTED_HISTORICAL_MANIFEST_SHA256
        or base.payload_sha256(tasks) != EXPECTED_HISTORICAL_TASK_VECTOR_SHA256
    ):
        raise RuntimeError("V2.55.37 historical task closure drifted")
    return manifest, tasks


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
    build_barrier = _build_barrier()
    selection_barrier = _selection_barrier()
    fixed = {str(path): base.sha256(path) for path in FIXED_HASHES}
    pairs = population.pair_vector()
    identities = [identity for pair in pairs for identity in pair]
    tasks = population.task_vector()
    consumed_identities = sorted(consumed.consumed_identities())
    research_identities = research.identity_vector()
    historical_manifest, historical_tasks = _historical_task_closure()
    questions = {row["question"] for row in tasks}
    opaque_ids = {row["opaque_id"] for row in tasks}
    historical_questions = {row["question"] for row in historical_tasks}
    historical_opaque_ids = {row["opaque_id"] for row in historical_tasks}
    snapshot = watchers.watcher_snapshot()
    explicit = {
        SOURCE,
        TEST,
        POPULATION_SOURCE,
        POPULATION_TEST,
        BUILD_AUDIT,
        SELECTION_SNAPSHOT,
        SELECTION_SOURCE,
        SELECTION_RUNNER,
    }
    untracked = sorted(
        str(path) for path in explicit if tracked and not _tracked(path)
    )
    reported_clean = clean if tracked else True
    policy = population.source_policy()
    gate = population.mechanism_gate()
    consumed_sha = population.payload_sha256(consumed_identities)
    checks = {
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "audit_population_and_barrier_files_tracked": not untracked,
        "selection_parent_exact_and_population_commit_in_history": (
            selection_parent == population.SELECTION_PARENT_COMMIT
            and POPULATION_COMMIT in history
        ),
        "v25531_clean_build_population_design_authority_bound": bool(
            build_barrier
        ),
        "v25535_selection_snapshot_population_exact": bool(selection_barrier),
        "fixed_barrier_selection_population_hashes_exact": all(
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
        "complete_consumed_identity_closure_exact_and_disjoint": (
            len(consumed_identities) == EXPECTED_CONSUMED_IDENTITY_COUNT
            and consumed_sha == EXPECTED_CONSUMED_IDENTITY_VECTOR_SHA256
            and not (set(identities) & set(consumed_identities))
        ),
        "v25527_research_identities_permanently_excluded": (
            set(research_identities).issubset(consumed_identities)
            and not (set(identities) & set(research_identities))
            and policy[
                "all_prior_tld_populations_and_v25527_research_identities_excluded"
            ]
            is True
        ),
        "all_historical_task_population_modules_exact_and_unique": (
            len(historical_manifest) == 25
            and len(historical_tasks) == 508
            and len(historical_questions) == 508
            and len(historical_opaque_ids) == 508
            and base.payload_sha256(historical_manifest)
            == EXPECTED_HISTORICAL_MANIFEST_SHA256
            and base.payload_sha256(historical_tasks)
            == EXPECTED_HISTORICAL_TASK_VECTOR_SHA256
        ),
        "zero_exact_question_or_opaque_overlap_with_all_historical_populations": (
            not (questions & historical_questions)
            and not (opaque_ids & historical_opaque_ids)
        ),
        "population_vectors_exact_and_hash_bound": (
            population.payload_sha256(pairs)
            == population.EXPECTED_PAIR_VECTOR_SHA256
            and population.payload_sha256(identities)
            == population.EXPECTED_IDENTITY_VECTOR_SHA256
            and population.payload_sha256(tasks)
            == population.EXPECTED_TASK_VECTOR_SHA256
            and len(tasks) == 20
            and len(questions) == 20
            and len(opaque_ids) == 20
        ),
        "questions_expose_only_two_rows_and_schema_without_layout_hint": (
            policy[
                "no_visible_url_source_host_authority_name_path_layout_grammar_coverage_or_field_value"
            ]
            is True
            and all(
                row["question"].count("<DOMAIN>") == 2
                and row["question"].count("</DOMAIN>") == 2
                and "https://" not in row["question"]
                and "iana" not in row["question"].casefold()
                and "delegation" not in row["question"].casefold()
                and "sponsoring organisation" not in row["question"].casefold()
                and "parenthetical" not in row["question"].casefold()
                for row in tasks
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
        "historical_rows_pages_predictions_truth_score_quality_or_outcome_never_read": policy[
            "prior_task_rows_pages_predictions_truth_scores_quality_or_per_task_outcomes_read"
        ]
        is False,
        "atomic_iana_layout_mechanism_gate_fixed_before_forward": (
            gate["fixed_task_denominator"] == 20
            and gate["required_terminal_tasks"] == 20
            and gate["required_completed_runtime_tasks"] == 20
            and gate["minimum_iana_layout_complete_page_tasks"] == 2
            and gate["minimum_raw_field_surface_tasks"] == 4
            and gate["minimum_evidence_closed_observation_tasks"] == 4
            and gate["minimum_material_candidate_tasks"] == 2
            and gate["minimum_applied_coordinate_count_total"] == 4
            and gate["minimum_treatment_changed_tasks"] == 2
            and gate["minimum_treatment_changed_coordinate_count_total"] == 4
            and gate["maximum_physical_fetches_per_completed_task"] == 14
            and gate["maximum_normal_path_model_forwards_per_completed_task"] == 3
            and gate["candidate_additional_queries_beyond_parent"] == 0
            and gate["candidate_additional_fetches_beyond_parent"] == 0
            and gate["candidate_additional_model_calls_beyond_parent"] == 0
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
        "population_commit": POPULATION_COMMIT,
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": reported_clean,
        },
        "fixed_artifact_hashes": fixed,
        "barriers": {
            "v25531_build_audit_sha256": fixed[str(BUILD_AUDIT)],
            "v25535_selection_snapshot_sha256": fixed[str(SELECTION_SNAPSHOT)],
        },
        "selection": {
            "selection_rule": population.SELECTION_RULE,
            "predecessor": ".bradesco",
            "first_identity": identities[0],
            "last_identity": identities[-1],
            "pair_count": len(pairs),
            "row_identity_count": len(identities),
            "unique_row_identity_count": len(set(identities)),
            "consumed_identity_count": len(consumed_identities),
            "consumed_identity_vector_sha256": consumed_sha,
            "consumed_identity_overlap_count": len(
                set(identities) & set(consumed_identities)
            ),
            "research_identity_count": len(research_identities),
            "research_identity_overlap_count": len(
                set(identities) & set(research_identities)
            ),
            "pair_vector_sha256": population.payload_sha256(pairs),
            "identity_vector_sha256": population.payload_sha256(identities),
            "task_vector_sha256": population.payload_sha256(tasks),
            "individual_pair_or_task_filtering_ranking_replacement_or_retention": False,
        },
        "historical_task_closure": {
            "module_count": len(historical_manifest),
            "task_count": len(historical_tasks),
            "unique_question_count": len(historical_questions),
            "unique_opaque_id_count": len(historical_opaque_ids),
            "question_overlap_count": len(questions & historical_questions),
            "opaque_id_overlap_count": len(opaque_ids & historical_opaque_ids),
            "path_vector_sha256": EXPECTED_HISTORICAL_PATH_VECTOR_SHA256,
            "manifest_sha256": base.payload_sha256(historical_manifest),
            "task_vector_sha256": base.payload_sha256(historical_tasks),
            "manifest": historical_manifest,
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
            "reuse_prior_execution_authority_population_or_research_identity": False,
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
    closure = copied.get("historical_task_closure")
    valid = copied.get("audit_valid") is True
    expected_watchers = [
        {"pid": pid, "start_ticks": ticks, "marker": marker}
        for pid, ticks, marker in watchers.EXPECTED_WATCHERS
    ]
    expected_fixed = {
        str(path): expected for path, expected in FIXED_HASHES.items()
    }
    if (
        copied.get("role") != ROLE
        or copied.get("selection_parent_commit")
        != population.SELECTION_PARENT_COMMIT
        or copied.get("population_commit") != POPULATION_COMMIT
        or not isinstance(checks, Mapping)
        or set(checks) != CHECK_NAMES
        or any(not isinstance(passed, bool) for passed in checks.values())
        or copied.get("findings")
        != sorted(name for name, passed in checks.items() if not passed)
        or valid is not (copied.get("findings") == [])
        or valid is not all(checks.values())
        or copied.get("fixed_artifact_hashes") != expected_fixed
        or copied.get("barriers")
        != {
            "v25531_build_audit_sha256": expected_fixed[str(BUILD_AUDIT)],
            "v25535_selection_snapshot_sha256": expected_fixed[
                str(SELECTION_SNAPSHOT)
            ],
        }
        or not isinstance(selection, Mapping)
        or selection.get("selection_rule") != population.SELECTION_RULE
        or selection.get("predecessor") != ".bradesco"
        or selection.get("first_identity") != ".bridgestone"
        or selection.get("last_identity") != ".cbre"
        or selection.get("pair_count") != 20
        or selection.get("row_identity_count") != 40
        or selection.get("unique_row_identity_count") != 40
        or selection.get("consumed_identity_count")
        != EXPECTED_CONSUMED_IDENTITY_COUNT
        or selection.get("consumed_identity_vector_sha256")
        != EXPECTED_CONSUMED_IDENTITY_VECTOR_SHA256
        or selection.get("consumed_identity_overlap_count") != 0
        or selection.get("research_identity_count") != 8
        or selection.get("research_identity_overlap_count") != 0
        or selection.get("pair_vector_sha256")
        != population.EXPECTED_PAIR_VECTOR_SHA256
        or selection.get("identity_vector_sha256")
        != population.EXPECTED_IDENTITY_VECTOR_SHA256
        or selection.get("task_vector_sha256")
        != population.EXPECTED_TASK_VECTOR_SHA256
        or selection.get(
            "individual_pair_or_task_filtering_ranking_replacement_or_retention"
        )
        is not False
        or not isinstance(closure, Mapping)
        or closure.get("module_count") != 25
        or closure.get("task_count") != 508
        or closure.get("unique_question_count") != 508
        or closure.get("unique_opaque_id_count") != 508
        or closure.get("question_overlap_count") != 0
        or closure.get("opaque_id_overlap_count") != 0
        or closure.get("path_vector_sha256")
        != EXPECTED_HISTORICAL_PATH_VECTOR_SHA256
        or closure.get("manifest_sha256")
        != EXPECTED_HISTORICAL_MANIFEST_SHA256
        or closure.get("task_vector_sha256")
        != EXPECTED_HISTORICAL_TASK_VECTOR_SHA256
        or not isinstance(closure.get("manifest"), list)
        or len(closure["manifest"]) != 25
        or copied.get("source_policy") != population.source_policy()
        or copied.get("mechanism_gate") != population.mechanism_gate()
        or copied.get("protected_watchers") != expected_watchers
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
            "reuse_prior_execution_authority_population_or_research_identity": False,
            "external_forward": False,
            "postfreeze_truth_or_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.37 population audit drifted")
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
                "historical_task_closure": {
                    key: item
                    for key, item in value["historical_task_closure"].items()
                    if key != "manifest"
                },
                "findings": value["findings"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
