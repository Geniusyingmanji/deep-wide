#!/usr/bin/env python3
"""Post-freeze audit for the V2.52.74 third disjoint population.

The auditor consumes only already-frozen local artifacts, aggregate receipts,
Git metadata, protected process identities, and the shared-lease state.  It
does not rerun dpkg/history selection and has no network, model, search,
fetch, evaluator, or benchmark capability.
"""

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

from deepwide_agent import v25267_production_only_exact220_contract as contract  # noqa: E402
from scripts import audit_v25140_targeted_revision_build as base  # noqa: E402
from scripts import audit_v25275_third_disjoint_checkpoint_selector_build as parent_audit  # noqa: E402
from scripts import freeze_v25274_third_disjoint_checkpoint_population as freeze  # noqa: E402


DATE = "20260813"
ROLE = "v25277_third_disjoint_checkpoint_population_postfreeze_audit"
OUTPUT = Path(
    f"results/v25277_third_disjoint_checkpoint_population_postfreeze_audit_v1_{DATE}.json"
)
SOURCE = Path("scripts/audit_v25277_third_disjoint_checkpoint_population.py")
TEST = Path("tests/test_audit_v25277_third_disjoint_checkpoint_population.py")
CLAIM = freeze.ATTEMPT_CLAIM
POPULATION = freeze.OUTPUT
START = freeze.EXECUTION_START
BUILD_AUDIT = parent_audit.OUTPUT
EXPECTED_START_PARENT = "09477546f0c9390f83a95272dad30e213414ee3b"
EXPECTED_SELECTION_PARENT = "63fb08e7e7e39090010c167996418e3c1a2eee45"
EXPECTED_FREEZE_COMMIT = "ec680793140df03786ab9a7c81178cf80be304c7"
FIXED_HASHES = {
    CLAIM: "bf829bdbd3ee1302084eaf49ba9b7734b5d40a63754c797e027b9bab3ddfbeb7",
    POPULATION: "f23c64907535ac2cd2bf57f30e51086f9247f36cd51bb5a1b1fff9df5155b5ad",
    START: "f1d6d331bef865a408c714cac85730168aa8213af8a9e23fd65923b709ca65a3",
    BUILD_AUDIT: "123bd8f24941bbdb0bebb4f5cefa3704a98561fd86b4977bfa44651e22cc7189",
}
TEST_SUITES = (
    ("test_audit_v25277_third_disjoint_checkpoint_population.py", 6),
    ("test_freeze_v25274_third_disjoint_checkpoint_population.py", 7),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CAPACITY = {
    "short_alpha": 35,
    "long_alpha": 5,
    "single_hyphen_alpha": 19,
}
EXPECTED_SELECTED = {
    "short_alpha": 20,
    "long_alpha": 4,
    "single_hyphen_alpha": 16,
}
EXPECTED_TASK_VECTOR_SHA256 = (
    "a9696499bd2a2ac5d9254027c8d03505f981219325299e2ca8938b0163ad8a04"
)
EXPECTED_PACKAGE_VECTOR_SHA256 = (
    "d452575e52bb9a1347e7d4e3a23b8e2ce618b8dd68669a510b5810b75834e195"
)
CHECK_NAMES = frozenset(
    {
        "claim_population_start_and_build_audit_hashes_exact",
        "claim_population_start_and_build_audit_validate",
        "start_is_unique_pushed_single_file_child",
        "freeze_is_unique_pushed_two_file_child",
        "selection_parent_is_pushed_execution_start_head",
        "claim_precedes_effect_and_binds_start_parent_and_result",
        "population_binds_claim_start_design_and_two_prior_populations",
        "source_count_and_history_probe_accounting_conserve",
        "all_564_candidates_completed_once_without_process_failure",
        "all_40_selected_entities_history_zero_and_prior384_disjoint",
        "task_vector_exact20_by2_globally_unique_and_visible_only",
        "stratum_selection_and_capacity_exact",
        "postfreeze_population_and_selector_tests_exact13",
        "all_audit_test_and_fixed_artifacts_tracked",
        "git_clean_head_equals_target_main",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called",
        "positive_entropy_or_information_gain_credit_zero",
    }
)


def _fixed_hashes() -> dict[str, str]:
    return {str(path): base.sha256(path) for path in FIXED_HASHES}


def validate_start(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("start_payload_sha256", None)
    authority = copied.get("authority") or {}
    execution = copied.get("execution_contract") or {}
    parent = copied.get("git_parent") or {}
    runtime = copied.get("runtime_state") or {}
    authorization = copied.get("authorization") or {}
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "authority",
            "execution_contract",
            "git_parent",
            "runtime_state",
            "source_manifest",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
            "authorization",
            "start_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25276_third_disjoint_checkpoint_population_execution_start"
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or authority
        != {
            "population_design": {
                "path": str(freeze.DESIGN),
                "sha256": freeze.DESIGN_SHA256,
            },
            "selector_build_audit": {
                "path": str(BUILD_AUDIT),
                "sha256": FIXED_HASHES[BUILD_AUDIT],
            },
        }
        or set(execution)
        != {
            "attempt_authority_is_create_exclusive_and_published_before_dpkg_or_history_effect",
            "attempt_claim_path",
            "caller_must_not_impose_wall_deadline_shorter_than_internal_240_seconds",
            "command_argv",
            "execute_exactly_once",
            "execution_start_sha256_is_bound_by_claim_and_result",
            "fixed_result_path",
            "history_parent_is_pushed_execution_start_head",
            "internal_whole_selection_wall_ceiling_seconds",
            "retry_resume_replacement_selective_backfill_or_second_freeze",
            "surfaces_pristine",
        }
        or execution.get(
            "attempt_authority_is_create_exclusive_and_published_before_dpkg_or_history_effect"
        )
        is not True
        or execution.get("attempt_claim_path") != str(CLAIM)
        or execution.get(
            "caller_must_not_impose_wall_deadline_shorter_than_internal_240_seconds"
        )
        is not True
        or execution.get("command_argv")
        != [
            ".venv-eval/bin/python",
            "-I",
            "-B",
            "<sealed_v25276_inline_single_freeze>",
            "--parent",
            "<pushed_execution_start_head>",
            "--execution-start-sha256",
            "<this_file_sha256>",
        ]
        or execution.get("execute_exactly_once") is not True
        or execution.get("execution_start_sha256_is_bound_by_claim_and_result")
        is not True
        or execution.get("fixed_result_path") != str(POPULATION)
        or execution.get("history_parent_is_pushed_execution_start_head") is not True
        or execution.get("internal_whole_selection_wall_ceiling_seconds") != 240
        or execution.get("retry_resume_replacement_selective_backfill_or_second_freeze")
        is not False
        or execution.get("surfaces_pristine") is not True
        or parent
        != {
            "clean": True,
            "equal": True,
            "head": EXPECTED_START_PARENT,
            "target_main": EXPECTED_START_PARENT,
        }
        or runtime
        != {
            "protected_watchers": parent_audit.EXPECTED_WATCHERS,
            "shared_api_lease_inactive": True,
        }
        or copied.get("source_manifest")
        != {
            str(freeze.SOURCE): "980a11c1dbf819d26ae5668c1f22673a9e5b0d2370c4114cc8756340f6ad0155",
            str(freeze.TEST): "24f5c5ac9ddec7ee132ed213c99bb6dff48bbf18fb6ad7e66607aa221cc53b37",
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
            "single_third_disjoint_population_freeze": True,
            "paired_checkpoint_reliability_protocol_design_after_valid_freeze": True,
            "external_activation_or_launch": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "deepwidebench_forward_or_evaluator": False,
            "avg_at_4_leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.76 execution start drifted")
    return copied


def _load() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    if _fixed_hashes() != {str(path): digest for path, digest in FIXED_HASHES.items()}:
        raise RuntimeError("V2.52.77 fixed artifact hash drifted")
    claim = freeze.validate_attempt_claim(
        json.loads(base._ordinary(CLAIM).read_text(encoding="utf-8"))
    )
    population = freeze.validate_freeze(
        json.loads(base._ordinary(POPULATION).read_text(encoding="utf-8"))
    )
    start = validate_start(json.loads(base._ordinary(START).read_text(encoding="utf-8")))
    parent = parent_audit.validate_audit(
        json.loads(base._ordinary(BUILD_AUDIT).read_text(encoding="utf-8"))
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


def _git_chain_exact() -> tuple[bool, bool]:
    start_files = base._git(
        "diff-tree", "--no-commit-id", "--name-only", "-r", EXPECTED_SELECTION_PARENT
    ).splitlines()
    freeze_files = base._git(
        "diff-tree", "--no-commit-id", "--name-only", "-r", EXPECTED_FREEZE_COMMIT
    ).splitlines()
    start_exact = bool(
        base._git("rev-parse", EXPECTED_SELECTION_PARENT + "^{commit}")
        == EXPECTED_SELECTION_PARENT
        and base._git("rev-parse", EXPECTED_SELECTION_PARENT + "^")
        == EXPECTED_START_PARENT
        and start_files == [str(START)]
    )
    freeze_exact = bool(
        base._git("rev-parse", EXPECTED_FREEZE_COMMIT + "^{commit}")
        == EXPECTED_FREEZE_COMMIT
        and base._git("rev-parse", EXPECTED_FREEZE_COMMIT + "^")
        == EXPECTED_SELECTION_PARENT
        and freeze_files == sorted((str(CLAIM), str(POPULATION)))
    )
    return start_exact, freeze_exact


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    claim, population, start, parent = _load()
    tasks = freeze.validate_task_vector(population["population"]["task_vector"])
    selected = [
        package
        for task in tasks
        for package in freeze._packages_from_question(task["question"])
    ]
    prior = freeze._prior_entities()
    counts = population["source_receipt"]["source_counts"]
    history = population["history_receipt"]
    probe = history["probe"]
    per_stratum = history["per_stratum"]
    tests = _tests()
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    explicit = {SOURCE, TEST, *FIXED_HASHES}
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    watchers = contract.watcher_snapshot()
    lease_inactive = base._lease_inactive()
    start_exact, freeze_exact = _git_chain_exact()
    claim_before_result = claim["created_at_unix"] <= population["created_at_unix"]
    failure_fields = (
        "coordinator_cancelled_count",
        "subprocess_timeout_count",
        "subprocess_nonzero_returncode_count",
        "subprocess_stderr_nonempty_count",
        "subprocess_incomplete_or_exception_count",
    )
    checks = {
        "claim_population_start_and_build_audit_hashes_exact": _fixed_hashes()
        == {str(path): digest for path, digest in FIXED_HASHES.items()},
        "claim_population_start_and_build_audit_validate": (
            parent["audit_valid"] is True and parent["findings"] == []
        ),
        "start_is_unique_pushed_single_file_child": start_exact,
        "freeze_is_unique_pushed_two_file_child": freeze_exact,
        "selection_parent_is_pushed_execution_start_head": (
            claim["selection_parent_commit"]
            == population["selection_parent_commit"]
            == EXPECTED_SELECTION_PARENT
        ),
        "claim_precedes_effect_and_binds_start_parent_and_result": (
            claim_before_result
            and claim[
                "attempt_authority_consumed_before_dpkg_or_history_effect"
            ]
            is True
            and claim["execution_start"]
            == {"path": str(START), "sha256": FIXED_HASHES[START]}
            and claim["result_path"] == str(POPULATION)
        ),
        "population_binds_claim_start_design_and_two_prior_populations": (
            population["attempt_claim"]
            == {"path": str(CLAIM), "sha256": FIXED_HASHES[CLAIM]}
            and population["execution_start"]
            == {"path": str(START), "sha256": FIXED_HASHES[START]}
            and population["design"]
            == {"path": str(freeze.DESIGN), "sha256": freeze.DESIGN_SHA256}
            and population["prior_population_exclusion_receipt"]
            == {
                "first_population_path": str(freeze.FIRST_POPULATION),
                "first_population_sha256": freeze.FIRST_POPULATION_SHA256,
                "second_population_path": str(freeze.SECOND_POPULATION),
                "second_population_sha256": freeze.SECOND_POPULATION_SHA256,
                "prior_visible_entity_count": 384,
                "selected_entity_overlap_count": 0,
                "prior_identity_list_or_per_item_hash_persisted": False,
            }
        ),
        "source_count_and_history_probe_accounting_conserve": (
            counts["source_name_disjoint_from_all_installed_binary_names_count"]
            == sum(
                counts[name]
                for name in (*freeze.STRATA, "digit_bearing", "excluded_other")
            )
            == probe["submitted_count"]
        ),
        "all_564_candidates_completed_once_without_process_failure": (
            probe["submitted_count"] == probe["completed_count"] == 564
            and probe["all_admitted_candidates_checked_exactly_once"] is True
            and probe["all_history_probes_succeeded_within_wall_ceiling"] is True
            and all(probe[name] == 0 for name in failure_fields)
        ),
        "all_40_selected_entities_history_zero_and_prior384_disjoint": (
            len(selected) == len(set(selected)) == 40
            and len(prior) == 384
            and not set(selected).intersection(prior)
            and history["history_zero_disjoint_selected_total"] == 40
        ),
        "task_vector_exact20_by2_globally_unique_and_visible_only": (
            len(tasks) == 20
            and all(set(task) == {"opaque_id", "question"} for task in tasks)
            and population["population"]["task_count"] == 20
            and population["population"]["package_count"] == 40
            and population["population"]["packages_per_task"] == 2
            and population["population"]["runtime_keys"]
            == ["opaque_id", "question"]
            and population["population"][
                "hidden_identity_mapping_or_stratum_field_persisted"
            ]
            is False
        ),
        "stratum_selection_and_capacity_exact": (
            {name: per_stratum[name]["disjoint_history_zero_capacity"] for name in freeze.STRATA}
            == EXPECTED_CAPACITY
            and {name: per_stratum[name]["selected_count"] for name in freeze.STRATA}
            == EXPECTED_SELECTED
        ),
        "postfreeze_population_and_selector_tests_exact13": tests["passed"],
        "all_audit_test_and_fixed_artifacts_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target)
        if tracked
        else True,
        "protected_watchers_unchanged": parent_audit._watchers_exact(watchers),
        "shared_api_lease_inactive": lease_inactive,
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": (
            population[
                "network_model_search_fetch_evaluator_benchmark_or_api_called"
            ]
            is False
        ),
        "positive_entropy_or_information_gain_credit_zero": (
            population["entropy_or_information_gain_assigns_signed_credit"] is False
        ),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": clean,
        },
        "fixed_hashes": _fixed_hashes(),
        "tests": tests,
        "selection_receipt": {
            "selection_parent_commit": population["selection_parent_commit"],
            "freeze_commit": EXPECTED_FREEZE_COMMIT,
            "claim_created_at_unix": claim["created_at_unix"],
            "population_created_at_unix": population["created_at_unix"],
            "source_candidate_count": probe["submitted_count"],
            "completed_history_probe_count": probe["completed_count"],
            "selected_entity_count": len(selected),
            "prior_visible_entity_count": len(prior),
            "selected_prior_overlap_count": len(set(selected).intersection(prior)),
            "history_zero_capacity_by_stratum": {
                name: per_stratum[name]["disjoint_history_zero_capacity"]
                for name in freeze.STRATA
            },
            "selected_by_stratum": {
                name: per_stratum[name]["selected_count"] for name in freeze.STRATA
            },
            "task_count": len(tasks),
            "task_vector_sha256": population["population"]["task_vector_sha256"],
            "ordered_visible_package_vector_sha256": population["population"][
                "ordered_visible_package_vector_sha256"
            ],
        },
        "untracked_sources": untracked,
        "runtime_state": {
            "shared_api_lease_inactive": lease_inactive,
            "protected_watchers": watchers,
        },
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "paired_checkpoint_reliability_protocol_design": not findings,
            "paired_checkpoint_reliability_external_activation_or_launch": False,
            "candidate_activation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    git = copied.get("git") or {}
    tests = copied.get("tests") or {}
    suites = tests.get("suites") or []
    receipt = copied.get("selection_receipt") or {}
    runtime = copied.get("runtime_state") or {}
    checks = copied.get("checks") or {}
    authorization = copied.get("authorization") or {}
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "git",
            "fixed_hashes",
            "tests",
            "selection_receipt",
            "untracked_sources",
            "runtime_state",
            "checks",
            "findings",
            "audit_valid",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
            "authorization",
            "audit_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or set(git) != {"head", "target_main", "equal", "clean"}
        or re.fullmatch(r"[0-9a-f]{40}", str(git.get("head"))) is None
        or git.get("head") != git.get("target_main")
        or git.get("equal") is not True
        or git.get("clean") is not True
        or copied.get("fixed_hashes")
        != {str(path): digest for path, digest in FIXED_HASHES.items()}
        or set(tests) != {"expected", "observed", "passed", "suites"}
        or tests.get("expected") != EXPECTED_TESTS
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("passed") is not True
        or len(suites) != len(TEST_SUITES)
        or any(
            not isinstance(row, Mapping)
            or set(row)
            != {
                "pattern",
                "expected",
                "observed",
                "returncode",
                "passed",
                "output_sha256",
            }
            or row.get("pattern") != pattern
            or row.get("expected") != expected
            or row.get("observed") != expected
            or row.get("returncode") != 0
            or row.get("passed") is not True
            or re.fullmatch(r"[0-9a-f]{64}", str(row.get("output_sha256"))) is None
            for row, (pattern, expected) in zip(suites, TEST_SUITES, strict=True)
        )
        or receipt
        != {
            "selection_parent_commit": EXPECTED_SELECTION_PARENT,
            "freeze_commit": EXPECTED_FREEZE_COMMIT,
            "claim_created_at_unix": 1786580402,
            "population_created_at_unix": 1786580527,
            "source_candidate_count": 564,
            "completed_history_probe_count": 564,
            "selected_entity_count": 40,
            "prior_visible_entity_count": 384,
            "selected_prior_overlap_count": 0,
            "history_zero_capacity_by_stratum": EXPECTED_CAPACITY,
            "selected_by_stratum": EXPECTED_SELECTED,
            "task_count": 20,
            "task_vector_sha256": EXPECTED_TASK_VECTOR_SHA256,
            "ordered_visible_package_vector_sha256": EXPECTED_PACKAGE_VECTOR_SHA256,
        }
        or copied.get("untracked_sources") != []
        or runtime
        != {
            "shared_api_lease_inactive": True,
            "protected_watchers": parent_audit.EXPECTED_WATCHERS,
        }
        or checks != {name: True for name in CHECK_NAMES}
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
        or authorization
        != {
            "paired_checkpoint_reliability_protocol_design": True,
            "paired_checkpoint_reliability_external_activation_or_launch": False,
            "candidate_activation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.77 population post-freeze audit drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    import os

    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_audit()
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "tasks": value["selection_receipt"]["task_count"],
                "entities": value["selection_receipt"]["selected_entity_count"],
                "overlap": value["selection_receipt"]["selected_prior_overlap_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
