#!/usr/bin/env python3
"""Post-freeze audit for the V2.52.56 disjoint reliability population."""

from __future__ import annotations

import copy
import json
import re
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25140_targeted_revision_build as base  # noqa: E402
from scripts import audit_v25257_disjoint_observed_reliability_selector_build as parent_audit  # noqa: E402
from scripts import freeze_v25256_disjoint_observed_reliability_population as freeze  # noqa: E402
from scripts import run_v25248_header_totality_shadow_external as publisher  # noqa: E402


DATE = "20260812"
ROLE = "v25259_disjoint_observed_reliability_population_postfreeze_audit"
OUTPUT = Path(f"results/v25259_disjoint_observed_reliability_population_postfreeze_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25259_disjoint_observed_reliability_population.py")
TEST = Path("tests/test_audit_v25259_disjoint_observed_reliability_population.py")
CLAIM = freeze.ATTEMPT_CLAIM
POPULATION = freeze.OUTPUT
START = freeze.EXECUTION_START
EXPECTED_SELECTION_PARENT = "ddc0e97bd2876cbe41725ee8cb36912718929c9a"
EXPECTED_START_PARENT = "c597f5aa4c61524e782751c42109849bbf581a1e"
FIXED_HASHES = {
    CLAIM: "bf36040040c1711a9ffdce6850f34119441910be8624a8922a5adc5116304948",
    POPULATION: "f383ecf184174bb16dd757899a3c48fd9d3d2bc3e2fb58f2e804fb2d888dd31b",
    START: "340f9925476ad0fbec7b394e6f722342a852c8a8e3c4e8a60a4795cbc009866e",
    parent_audit.OUTPUT: "d432d8fa5ab05b867a0f20d44a07565a644d9e32e8da8cf4ebbb4a13e4e27932",
}
TEST_SUITES = (
    ("test_audit_v25259_disjoint_observed_reliability_population.py", 5),
    ("test_freeze_v25256_disjoint_observed_reliability_population.py", 9),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
CHECK_NAMES = {
    "claim_population_start_and_build_audit_hashes_exact",
    "claim_population_start_and_build_audit_validate",
    "selection_parent_is_pushed_execution_start_head",
    "claim_precedes_effect_and_binds_start_parent_and_result",
    "population_binds_claim_start_design_and_old_population",
    "source_count_and_history_probe_accounting_conserve",
    "all_485_candidates_completed_once_without_process_failure",
    "all_128_selected_entities_history_zero_and_old_disjoint",
    "task_vector_exact64_by2_globally_unique_and_visible_only",
    "stratum_selection_and_capacity_exact",
    "postfreeze_population_and_selector_tests_exact14",
    "all_audit_test_and_fixed_artifacts_tracked",
    "git_clean_head_equals_target_main",
    "protected_watchers_unchanged",
    "shared_api_lease_inactive",
    "no_network_model_search_fetch_evaluator_benchmark_or_api_called",
    "positive_entropy_or_information_gain_credit_zero",
}


def _fixed_hashes() -> dict[str, str]:
    return {str(path): base.sha256(path) for path in FIXED_HASHES}


def validate_start(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("start_payload_sha256", None)
    authority = copied.get("authority") or {}
    contract = copied.get("execution_contract") or {}
    parent = copied.get("git_parent") or {}
    runtime = copied.get("runtime_state") or {}
    authorization = copied.get("authorization") or {}
    expected_watchers = {
        str(pid): {"matches_frozen_identity": True, "start_ticks": ticks}
        for pid, ticks in parent_audit.runtime_audit.external.PROTECTED_WATCHERS.items()
    }
    if (
        set(copied)
        != {
            "artifact_version", "role", "created_at_unix", "authority",
            "execution_contract", "git_parent", "runtime_state", "source_manifest",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit", "authorization",
            "start_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25258_disjoint_observed_reliability_population_execution_start"
        or not isinstance(copied.get("created_at_unix"), int)
        or isinstance(copied.get("created_at_unix"), bool)
        or authority
        != {
            "population_design": {"path": str(freeze.DESIGN), "sha256": freeze.DESIGN_SHA256},
            "selector_build_audit": {"path": str(parent_audit.OUTPUT), "sha256": FIXED_HASHES[parent_audit.OUTPUT]},
        }
        or set(contract)
        != {
            "attempt_authority_is_create_exclusive_and_published_before_dpkg_or_history_effect",
            "attempt_claim_path", "caller_must_not_impose_wall_deadline_shorter_than_internal_240_seconds",
            "command_argv", "execute_exactly_once",
            "execution_start_sha256_is_bound_by_claim_and_result", "fixed_result_path",
            "history_parent_is_pushed_execution_start_head",
            "internal_whole_selection_wall_ceiling_seconds",
            "retry_resume_replacement_selective_backfill_or_second_freeze", "surfaces_pristine",
        }
        or contract.get("attempt_authority_is_create_exclusive_and_published_before_dpkg_or_history_effect") is not True
        or contract.get("attempt_claim_path") != str(CLAIM)
        or contract.get("caller_must_not_impose_wall_deadline_shorter_than_internal_240_seconds") is not True
        or contract.get("execute_exactly_once") is not True
        or contract.get("execution_start_sha256_is_bound_by_claim_and_result") is not True
        or contract.get("fixed_result_path") != str(POPULATION)
        or contract.get("history_parent_is_pushed_execution_start_head") is not True
        or contract.get("internal_whole_selection_wall_ceiling_seconds") != 240
        or contract.get("retry_resume_replacement_selective_backfill_or_second_freeze") is not False
        or contract.get("surfaces_pristine") is not True
        or not isinstance(contract.get("command_argv"), list)
        or contract["command_argv"][-4:] != [
            "--parent", "<pushed_execution_start_head>",
            "--execution-start-sha256", "<this_file_sha256>",
        ]
        or parent
        != {
            "clean": True, "equal": True,
            "head": EXPECTED_START_PARENT, "target_main": EXPECTED_START_PARENT,
        }
        or runtime
        != {"protected_watchers": expected_watchers, "shared_api_lease_inactive": True}
        or copied.get("source_manifest")
        != {
            str(freeze.SOURCE): "e8ed8da7e28ffcfed9d9f983204c9d4add187440215e8ae6068544c7726a0f64",
            str(freeze.TEST): "819a3e711f0691f54320920edbbd9bf670d31ff4a216962afca8192bf22f0f6e",
        }
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "network_model_search_fetch_evaluator_benchmark_or_api_called",
                "entropy_or_information_gain_assigns_signed_credit",
            )
        )
        or authorization
        != {
            "single_disjoint_population_freeze": True,
            "observed_reliability_protocol_design_after_valid_freeze": True,
            "external_activation_or_launch": False,
            "candidate_activation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != freeze.base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.58 execution start drifted")
    return copied


def _load() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    if _fixed_hashes() != {str(path): digest for path, digest in FIXED_HASHES.items()}:
        raise RuntimeError("V2.52.59 fixed artifact hash drifted")
    claim = freeze.validate_attempt_claim(json.loads(base._ordinary(CLAIM).read_text(encoding="utf-8")))
    population = freeze.validate_freeze(json.loads(base._ordinary(POPULATION).read_text(encoding="utf-8")))
    start = validate_start(json.loads(base._ordinary(START).read_text(encoding="utf-8")))
    parent = parent_audit.validate_audit(
        json.loads(base._ordinary(parent_audit.OUTPUT).read_text(encoding="utf-8"))
    )
    return claim, population, start, parent


def _tests() -> dict[str, Any]:
    suites = [base._test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in suites),
        "suites": suites,
    }


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    claim, population, start, parent = _load()
    tasks = freeze.validate_task_vector(population["population"]["task_vector"])
    selected = [
        package
        for task in tasks
        for package in freeze._packages_from_question(task["question"])
    ]
    old_entities = freeze._old_entities()
    counts = population["source_receipt"]["source_counts"]
    history = population["history_receipt"]
    probe = history["probe"]
    per_stratum = history["per_stratum"]
    tests = _tests()
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    explicit = {SOURCE, TEST, *FIXED_HASHES}
    untracked = sorted(str(path) for path in explicit if tracked and not base._tracked(path))
    watchers = parent_audit.runtime_audit.external.watcher_snapshot()
    lease_inactive = base._lease_inactive()
    claim_before_population = claim["created_at_unix"] <= population["created_at_unix"]
    checks = {
        "claim_population_start_and_build_audit_hashes_exact": _fixed_hashes() == {str(path): digest for path, digest in FIXED_HASHES.items()},
        "claim_population_start_and_build_audit_validate": parent["audit_valid"] is True,
        "selection_parent_is_pushed_execution_start_head": (
            claim["selection_parent_commit"] == population["selection_parent_commit"] == EXPECTED_SELECTION_PARENT
            and base._git("rev-parse", EXPECTED_SELECTION_PARENT + "^{commit}") == EXPECTED_SELECTION_PARENT
            and base._git("rev-parse", EXPECTED_SELECTION_PARENT + "^") == EXPECTED_START_PARENT
        ),
        "claim_precedes_effect_and_binds_start_parent_and_result": (
            claim_before_population
            and claim["attempt_authority_consumed_before_dpkg_or_history_effect"] is True
            and claim["execution_start"] == {"path": str(START), "sha256": FIXED_HASHES[START]}
            and claim["result_path"] == str(POPULATION)
        ),
        "population_binds_claim_start_design_and_old_population": (
            population["attempt_claim"] == {"path": str(CLAIM), "sha256": FIXED_HASHES[CLAIM]}
            and population["execution_start"] == {"path": str(START), "sha256": FIXED_HASHES[START]}
            and population["design"] == {"path": str(freeze.DESIGN), "sha256": freeze.DESIGN_SHA256}
            and population["old_population_exclusion_receipt"]["old_population_sha256"] == freeze.OLD_POPULATION_SHA256
        ),
        "source_count_and_history_probe_accounting_conserve": (
            counts["source_name_disjoint_from_all_installed_binary_names_count"]
            == sum(counts[name] for name in (*freeze.STRATA, "excluded_other"))
            and probe["submitted_count"] == sum(counts[name] for name in freeze.STRATA)
        ),
        "all_485_candidates_completed_once_without_process_failure": (
            probe["submitted_count"] == probe["completed_count"] == 485
            and probe["all_admitted_candidates_checked_exactly_once"] is True
            and probe["all_history_probes_succeeded_within_wall_ceiling"] is True
            and all(
                probe[name] == 0
                for name in (
                    "coordinator_cancelled_count", "subprocess_timeout_count",
                    "subprocess_nonzero_returncode_count", "subprocess_stderr_nonempty_count",
                    "subprocess_incomplete_or_exception_count",
                )
            )
        ),
        "all_128_selected_entities_history_zero_and_old_disjoint": (
            len(selected) == len(set(selected)) == 128
            and not set(selected).intersection(old_entities)
            and history["history_zero_disjoint_selected_total"] == 128
            and population["old_population_exclusion_receipt"]["selected_entity_overlap_count"] == 0
        ),
        "task_vector_exact64_by2_globally_unique_and_visible_only": (
            len(tasks) == 64
            and all(set(task) == {"opaque_id", "question"} for task in tasks)
            and population["population"]["runtime_keys_exactly_opaque_id_and_question"] is True
            and population["population"]["hidden_identity_list_stratum_mapping_or_item_hash_persisted"] is False
            and population["population"]["stratum_field_passed_to_runtime"] is False
        ),
        "stratum_selection_and_capacity_exact": all(
            row["selected_count"] == freeze.PACKAGES_BY_STRATUM[name]
            and row["disjoint_history_zero_capacity"] >= row["selected_count"]
            and row["candidate_capacity"]
            == row["history_positive_package_count"] + row["history_zero_capacity"]
            for name, row in per_stratum.items()
        ),
        "postfreeze_population_and_selector_tests_exact14": tests["passed"],
        "all_audit_test_and_fixed_artifacts_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target) if tracked else True,
        "protected_watchers_unchanged": all(row["matches_frozen_identity"] is True for row in watchers),
        "shared_api_lease_inactive": lease_inactive,
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": (
            population["network_model_search_fetch_evaluator_benchmark_or_api_called"] is False
        ),
        "positive_entropy_or_information_gain_credit_zero": (
            population["entropy_or_information_gain_assigns_signed_credit"] is False
        ),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target, "clean": clean},
        "fixed_hashes": _fixed_hashes(),
        "tests": tests,
        "selection_receipt": {
            "selection_parent_commit": population["selection_parent_commit"],
            "claim_created_at_unix": claim["created_at_unix"],
            "population_created_at_unix": population["created_at_unix"],
            "source_candidate_count": probe["submitted_count"],
            "completed_history_probe_count": probe["completed_count"],
            "selected_entity_count": len(selected),
            "old_visible_entity_count": len(old_entities),
            "selected_old_overlap_count": len(set(selected).intersection(old_entities)),
            "history_zero_capacity_by_stratum": {
                name: per_stratum[name]["disjoint_history_zero_capacity"] for name in freeze.STRATA
            },
            "selected_by_stratum": {
                name: per_stratum[name]["selected_count"] for name in freeze.STRATA
            },
            "task_count": len(tasks),
            "task_vector_sha256": population["population"]["task_vector_sha256"],
            "ordered_visible_package_vector_sha256": population["population"]["ordered_visible_package_vector_sha256"],
        },
        "untracked_sources": untracked,
        "runtime_state": {"shared_api_lease_inactive": lease_inactive, "protected_watchers": watchers},
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "fresh64_observed_reliability_protocol_design": not findings,
            "fresh64_external_activation_or_launch": False,
            "candidate_activation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    return parent_audit.runtime_audit.external.seal(value, "audit_payload_sha256")


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    git_value = copied.get("git") or {}
    tests = copied.get("tests") or {}
    suites = tests.get("suites") or []
    receipt = copied.get("selection_receipt") or {}
    runtime = copied.get("runtime_state") or {}
    checks = copied.get("checks") or {}
    if (
        set(copied)
        != {
            "artifact_version", "role", "created_at_unix", "git", "fixed_hashes",
            "tests", "selection_receipt", "untracked_sources", "runtime_state",
            "checks", "findings", "audit_valid",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit", "authorization",
            "audit_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or not isinstance(copied.get("created_at_unix"), int)
        or isinstance(copied.get("created_at_unix"), bool)
        or set(git_value) != {"head", "target_main", "equal", "clean"}
        or re.fullmatch(r"[0-9a-f]{40}", str(git_value.get("head"))) is None
        or git_value.get("head") != git_value.get("target_main")
        or git_value.get("equal") is not True
        or git_value.get("clean") is not True
        or copied.get("fixed_hashes") != {str(path): digest for path, digest in FIXED_HASHES.items()}
        or set(tests) != {"expected", "observed", "passed", "suites"}
        or tests.get("expected") != EXPECTED_TESTS
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("passed") is not True
        or len(suites) != len(TEST_SUITES)
        or any(
            not isinstance(row, Mapping)
            or set(row) != {"pattern", "expected", "observed", "returncode", "passed", "output_sha256"}
            or row.get("pattern") != pattern
            or row.get("expected") != expected
            or row.get("observed") != expected
            or row.get("returncode") != 0
            or row.get("passed") is not True
            or re.fullmatch(r"[0-9a-f]{64}", str(row.get("output_sha256"))) is None
            for row, (pattern, expected) in zip(suites, TEST_SUITES, strict=True)
        )
        or set(receipt)
        != {
            "selection_parent_commit", "claim_created_at_unix", "population_created_at_unix",
            "source_candidate_count", "completed_history_probe_count", "selected_entity_count",
            "old_visible_entity_count", "selected_old_overlap_count",
            "history_zero_capacity_by_stratum", "selected_by_stratum", "task_count",
            "task_vector_sha256", "ordered_visible_package_vector_sha256",
        }
        or receipt.get("selection_parent_commit") != EXPECTED_SELECTION_PARENT
        or receipt.get("claim_created_at_unix") != 1786571805
        or receipt.get("population_created_at_unix") != 1786571907
        or receipt.get("source_candidate_count") != 485
        or receipt.get("completed_history_probe_count") != 485
        or receipt.get("selected_entity_count") != 128
        or receipt.get("old_visible_entity_count") != 256
        or receipt.get("selected_old_overlap_count") != 0
        or receipt.get("history_zero_capacity_by_stratum")
        != {"short_alpha": 83, "long_alpha": 29, "single_hyphen_alpha": 51, "digit_bearing": 25}
        or receipt.get("selected_by_stratum") != freeze.PACKAGES_BY_STRATUM
        or receipt.get("task_count") != 64
        or re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("task_vector_sha256"))) is None
        or re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("ordered_visible_package_vector_sha256"))) is None
        or copied.get("untracked_sources") != []
        or set(runtime) != {"shared_api_lease_inactive", "protected_watchers"}
        or runtime.get("shared_api_lease_inactive") is not True
        or runtime.get("protected_watchers") != parent_audit.runtime_audit.external.watcher_snapshot()
        or set(checks) != CHECK_NAMES
        or any(passed is not True for passed in checks.values())
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "network_model_search_fetch_evaluator_benchmark_or_api_called",
                "entropy_or_information_gain_assigns_signed_credit",
            )
        )
        or copied.get("authorization")
        != {
            "fresh64_observed_reliability_protocol_design": True,
            "fresh64_external_activation_or_launch": False,
            "candidate_activation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or not parent_audit.runtime_audit.external.sealed(copied, "audit_payload_sha256")
    ):
        raise ValueError("V2.52.59 population audit drifted")
    return copied


def main() -> None:
    value = validate_audit(build_audit())
    publisher._publish_json(ROOT / OUTPUT, value)
    print(json.dumps({
        "path": str(OUTPUT), "audit_valid": value["audit_valid"],
        "tasks": value["selection_receipt"]["task_count"],
        "entities": value["selection_receipt"]["selected_entity_count"],
        "overlap": value["selection_receipt"]["selected_old_overlap_count"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
