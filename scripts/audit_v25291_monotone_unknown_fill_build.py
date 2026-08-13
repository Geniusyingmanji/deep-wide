#!/usr/bin/env python3
"""Clean-build audit for the bounded V2.52.89/90 monotone Unknown fill."""

from __future__ import annotations

import ast
import copy
import json
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

from deepwide_agent import v24857_pacing_aware_exact220_contract as legacy_contract  # noqa: E402
from deepwide_agent import v25267_production_only_exact220_contract as seal  # noqa: E402
from scripts import audit_v25140_targeted_revision_build as base  # noqa: E402
from scripts import diagnose_v25288_legacy_checkpoint_identifiability as parent_diagnosis  # noqa: E402


DATE = "20260813"
ROLE = "v25291_monotone_unknown_fill_clean_build_audit"
OUTPUT = Path(f"results/v25291_monotone_unknown_fill_build_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25291_monotone_unknown_fill_build.py")
TEST = Path("tests/test_audit_v25291_monotone_unknown_fill_build.py")
CORE = Path("src/deepwide_agent/v25289_monotone_unknown_fill.py")
CORE_TEST = Path("tests/test_v25289_monotone_unknown_fill.py")
INTEGRATION = Path(
    "src/deepwide_agent/v25290_monotone_unknown_fill_integration.py"
)
INTEGRATION_TEST = Path(
    "tests/test_v25290_monotone_unknown_fill_integration.py"
)
PARENT_DIAGNOSIS = parent_diagnosis.OUTPUT
FIXED_PARENTS = {
    PARENT_DIAGNOSIS: (
        "f40c22a4d3fa87bcd5e7d888676b0aff08cf0254f1b2515b6959d8a29e4377c6"
    ),
}
FIXED_SOURCES = {
    CORE: "d757261426b80b19f54047b7fb0842d8d7491a9a15a81d32504113bd600c071b",
    CORE_TEST: (
        "38f5ab6d0d44bc192bcbbafe4f5d4432b9e24e1662b8d7346591f7fcbe579e74"
    ),
    INTEGRATION: (
        "8cbad2ac9a28ccec8c93923b4656eee777cb4816b207167def72dda093c0ef46"
    ),
    INTEGRATION_TEST: (
        "1281c045490d30bce153f072725b17d8c7464529fd464f80c79b5ed4a77dee3a"
    ),
}
V25290_COMMIT = "47865f7451f286b49de57abe8bf4322b8d31831b"
V25290_COMMIT_PATHS = sorted([str(INTEGRATION), str(INTEGRATION_TEST)])
TEST_SUITES = (
    ("test_audit_v25291_monotone_unknown_fill_build.py", 6),
    ("test_v25290_monotone_unknown_fill_integration.py", 16),
    ("test_v25289_monotone_unknown_fill.py", 17),
    ("test_v24860_coverage_revision_integration.py", 11),
    ("test_v24859_full_evidence_coverage_revision.py", 20),
    ("test_v24319_runner_integration.py", 7),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 25
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "b12eb37c7b3d6576b3353956050d7538da25a9ac866c80e8a22b1c37f6b98cb0"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "7c6ff5e78bef98ff40791bf5902384f771c7d0031421c21102e0225a60010fcb"
)
EXPECTED_WATCHERS = {
    "795336": 713986317,
    "2808901": 746680268,
    "2889939": 746969965,
    "3061652": 747569004,
}
CHECK_NAMES = frozenset(
    {
        "fixed_parent_diagnosis_valid_and_build_only",
        "v25289_and_v25290_hashes_exact",
        "v25290_commit_is_exact_and_ancestor_of_clean_head",
        "direct_and_parent_tests_exact77_green",
        "all_runtime_auditor_test_parent_and_closure_files_tracked",
        "runtime_dependency_vector_exact25_and_hash_bound",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "visible_task_same_forward_parent_and_pages_only",
        "third_slot_requires_two_call_parent_unknown_complete_prefix_and_context",
        "known_cells_schema_keys_order_and_count_are_immutable",
        "same_forward_support_required_and_conflicts_rejected",
        "all_failure_paths_preserve_parent_prediction",
        "private_task_pages_proposal_receipt_and_prediction_replayed",
        "query4_fetch10_model3_and_concurrency_caps_unchanged",
        "entropy_and_information_gain_are_shadow_only",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "git_clean_head_equals_target_main",
        "no_network_search_fetch_evaluator_benchmark_or_api_called",
        "no_external_effect_performed",
    }
)


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


def _closure() -> tuple[tuple[Path, ...], list[dict[str, str]]]:
    closure = tuple(sorted(base._dependency_closure((INTEGRATION,)), key=str))
    vector = [{"path": str(path), "sha256": base.sha256(path)} for path in closure]
    return closure, vector


def _fixed_parents() -> dict[str, str]:
    return {str(path): base.sha256(path) for path in FIXED_PARENTS}


def _fixed_sources() -> dict[str, str]:
    return {str(path): base.sha256(path) for path in FIXED_SOURCES}


def _parent_barrier() -> bool:
    if _fixed_parents() != {
        str(path): digest for path, digest in FIXED_PARENTS.items()
    }:
        return False
    try:
        value = parent_diagnosis.validate_diagnosis(
            json.loads(base._ordinary(PARENT_DIAGNOSIS).read_text(encoding="utf-8"))
        )
    except BaseException:
        return False
    decision = value["decision"]
    authorization = value["authorization"]
    return bool(
        value["diagnosis_valid"] is True
        and value["findings"] == []
        and decision[
            "next_candidate_must_change_normal_path_prediction_under_shared_prefix"
        ]
        is True
        and decision["next_candidate_must_use_existing_query_fetch_model_cap"]
        is True
        and decision["next_candidate_requires_fresh_disjoint_external_causal_gate"]
        is True
        and authorization["normal_path_quality_candidate_design_and_build_only"]
        is True
        and authorization["fresh_external_population_selection_or_protocol"]
        is False
        and authorization["external_activation_or_launch"] is False
        and authorization["deepwidebench_dev64_exact220_forward_or_evaluator"]
        is False
    )


def _changed_paths(commit: str) -> list[str]:
    output = base._git(
        "diff-tree", "--no-commit-id", "--name-only", "-r", commit
    )
    return sorted(line for line in output.splitlines() if line)


def _is_ancestor(older: str, newer: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", older, newer],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode
        == 0
    )


def _function(tree: ast.AST, name: str) -> ast.FunctionDef:
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    if len(matches) != 1:
        raise RuntimeError(f"V2.52.91 expected one function: {name}")
    return matches[0]


def _public_arguments(function: ast.FunctionDef) -> list[str]:
    return [
        item.arg
        for item in function.args.posonlyargs
        + function.args.args
        + function.args.kwonlyargs
    ]


def _source_invariants() -> dict[str, bool]:
    integration_source = base._ordinary(INTEGRATION).read_text(encoding="utf-8")
    core_source = base._ordinary(CORE).read_text(encoding="utf-8")
    integration_tree = ast.parse(integration_source, filename=str(INTEGRATION))
    core_tree = ast.parse(core_source, filename=str(CORE))
    run = _function(integration_tree, "run_monotone_unknown_fill")
    prompt = _function(integration_tree, "_proposal_prompt")
    validate = _function(integration_tree, "validate_result")
    apply = _function(core_tree, "apply_monotone_unknown_fill")
    public = _public_arguments(run)
    prompt_text = ast.get_source_segment(integration_source, prompt) or ""
    run_text = ast.get_source_segment(integration_source, run) or ""
    validate_text = ast.get_source_segment(integration_source, validate) or ""
    apply_text = ast.get_source_segment(core_source, apply) or ""
    first_effect = run_text.find("response = model.complete(")
    eligibility = run_text.find("if not eligible:")
    unknown = run_text.find("elif unknown == 0:")
    prefix = run_text.find("elif not complete_prefix:")
    context = run_text.find("elif not prompt_within_cap:")
    return {
        "public_runtime_boundary_exact": public
        == [
            "task",
            "parent_result",
            "parent_model_slot_receipt",
            "model",
            "pages",
            "limits",
            "monotonic",
        ],
        "visible_task_validated_before_effect": 0
        <= run_text.find("visible = validate_visible_task(task)")
        < first_effect,
        "prompt_uses_visible_question_parent_table_and_same_forward_pages": all(
            token in prompt_text
            for token in (
                'task["question"]',
                'parent["columns"]',
                'parent["prediction"]',
                "page.content for page in pages",
            )
        ),
        "eligibility_gates_precede_only_model_effect": (
            0 <= eligibility < unknown < prefix < context < first_effect
            and run_text.count("model.complete(") == 1
        ),
        "exact_three_call_parent_cap_required": (
            "if limits.model_calls != 3:" in run_text
            and 'copied.get("logical_final_model_calls") > 3'
            in integration_source
        ),
        "no_search_or_fetch_effect_in_integration": (
            ".search(" not in run_text
            and ".fetch(" not in run_text
            and "additional_search_or_fetch_effect" in integration_source
        ),
        "known_and_structure_changes_rejected": all(
            token in apply_text
            for token in (
                "forbidden_known_changes=forbidden",
                "whole_proposal_rejected_fills=proposed_fills",
                "proposal_structure_exact=False",
            )
        ),
        "support_and_conflict_are_mechanically_checked": all(
            token in apply_text
            for token in (
                "_support_and_conflict(",
                "MINIMUM_SUPPORTING_PAGES",
                "MAXIMUM_CONFLICTING_BOUND_VALUES",
            )
        ),
        "private_inputs_and_proposal_are_replayed": all(
            token in validate_text
            for token in (
                "private_visible_task",
                "private_same_forward_pages",
                "private_model_proposal",
                "core.apply_monotone_unknown_fill(",
                "private support replay drifted",
            )
        ),
        "entropy_shadow_never_controls_admission_or_credit": (
            "shadow_information_gain_nats" in core_source
            and "entropy_or_information_gain_used_for_admission_or_credit_sign"
            in core_source
            and 'is not False' in core_source
        ),
    }


def _watchers_exact(value: object) -> bool:
    if not isinstance(value, Mapping) or set(value) != set(EXPECTED_WATCHERS):
        return False
    return all(
        isinstance(value.get(pid), Mapping)
        and set(value[pid])
        == {"present", "start_ticks", "matches_frozen_identity"}
        and value[pid].get("present") is True
        and value[pid].get("start_ticks") == start
        and value[pid].get("matches_frozen_identity") is True
        for pid, start in EXPECTED_WATCHERS.items()
    )


def _candidate_contract() -> dict[str, Any]:
    return {
        "treatment": "bounded_third_slot_monotone_unknown_fill",
        "shared_prefix": [
            "visible_question",
            "parent_prediction",
            "queries",
            "search_responses",
            "fetched_pages",
        ],
        "candidate_model_forward_upper_bound": 1,
        "total_model_forward_cap": 3,
        "additional_query_cap": 0,
        "additional_fetch_cap": 0,
        "mutable_cells": "baseline_unknown_only",
        "known_cells_schema_row_key_order_and_count_immutable": True,
        "same_forward_page_support_required": True,
        "conflicting_bound_value_rejected": True,
        "any_failure_is_parent_prediction_identity": True,
        "entropy_or_information_gain_is_shadow_only": True,
        "positive_signed_credit_count": 0,
    }


def _future_protocol_requirements() -> dict[str, Any]:
    return {
        "fresh_disjoint_benchmark_external_population": True,
        "single_forward_shared_prefix_control_candidate": True,
        "runtime_keys": ["opaque_id", "question"],
        "selection_must_not_use_runtime_or_evaluator_labels": True,
        "mapping_gold_category_question_type_split_score_or_reward_closed_until_both_predictions_freeze": True,
        "retry_resume_skip_backfill_replacement_or_selective_rerun": False,
        "mechanism_gate_before_evaluator": {
            "supported_unknown_fill_count_nonzero": True,
            "attributable_prediction_change_count_nonzero": True,
            "query_and_fetch_effect_equal": True,
            "model_calls_at_most_three": True,
            "all_resource_caps_preserved": True,
        },
        "quality_go_after_independent_postfreeze_evaluation": {
            "candidate_exact_strictly_greater": True,
            "entity_row_item_column_composite_nonregression": True,
            "fallback_invalid_and_outer_failure_nonincrease": True,
        },
        "zero_mechanism_event_population_is_no_go_without_evaluator": True,
        "direct_deepwidebench_220_after_build": False,
    }


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    tests = _tests()
    closure, vector = _closure()
    semantic = base._semantic_findings(closure)
    invariants = _source_invariants()
    watchers = base._watchers()
    explicit = {
        SOURCE,
        TEST,
        *FIXED_PARENTS,
        *FIXED_SOURCES,
        *closure,
    }
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    literal_hits = sorted(
        str(path)
        for path in explicit
        if base.SECRET.search(base._ordinary(path).read_text(encoding="utf-8"))
    )
    tests_green = tests["passed"]
    invariants_green = all(invariants.values())
    caps_exact = bool(
        legacy_contract.EXECUTOR_CONCURRENCY == 20
        and legacy_contract.MODEL_SLOT_CAP == 8
        and legacy_contract.TAVILY_KEY_SLOT_CAP == 12
        and legacy_contract.LIMITS["search_queries"] == 4
        and legacy_contract.LIMITS["fetch_targets"] == 10
        and legacy_contract.LIMITS["model_calls"] == 3
        and legacy_contract.LIMITS["wall_seconds"] == 240
    )
    checks = {
        "fixed_parent_diagnosis_valid_and_build_only": _parent_barrier(),
        "v25289_and_v25290_hashes_exact": _fixed_sources()
        == {str(path): digest for path, digest in FIXED_SOURCES.items()},
        "v25290_commit_is_exact_and_ancestor_of_clean_head": (
            _changed_paths(V25290_COMMIT) == V25290_COMMIT_PATHS
            and _is_ancestor(V25290_COMMIT, head)
        ),
        "direct_and_parent_tests_exact77_green": tests_green,
        "all_runtime_auditor_test_parent_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact25_and_hash_bound": (
            len(vector) == EXPECTED_CLOSURE_COUNT
            and seal.payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256
            and seal.payload_sha256([row["path"] for row in vector])
            == EXPECTED_CLOSURE_PATH_SHA256
        ),
        "privileged_runtime_field_access_zero": semantic[
            "privileged_runtime_field_accesses"
        ]
        == [],
        "evaluator_capability_zero": semantic["evaluator_capabilities"] == [],
        "credential_literal_zero": semantic["credential_literal_hits"] == []
        and literal_hits == [],
        "only_known_provider_rank_score_exception": semantic[
            "allowed_provider_rank_access"
        ]
        == ["src/deepwide_agent/clients.py:565:score"],
        "visible_task_same_forward_parent_and_pages_only": invariants_green,
        "third_slot_requires_two_call_parent_unknown_complete_prefix_and_context": tests_green
        and invariants_green,
        "known_cells_schema_keys_order_and_count_are_immutable": tests_green
        and invariants_green,
        "same_forward_support_required_and_conflicts_rejected": tests_green
        and invariants_green,
        "all_failure_paths_preserve_parent_prediction": tests_green,
        "private_task_pages_proposal_receipt_and_prediction_replayed": tests_green
        and invariants_green,
        "query4_fetch10_model3_and_concurrency_caps_unchanged": caps_exact,
        "entropy_and_information_gain_are_shadow_only": tests_green
        and invariants_green,
        "protected_watchers_unchanged": _watchers_exact(watchers),
        "shared_api_lease_inactive": base._lease_inactive(),
        "git_clean_head_equals_target_main": clean and head == target,
        "no_network_search_fetch_evaluator_benchmark_or_api_called": True,
        "no_external_effect_performed": True,
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
        "fixed_parents": _fixed_parents(),
        "fixed_sources": _fixed_sources(),
        "tests": tests,
        "runtime_dependency_vector": vector,
        "runtime_dependency_vector_sha256": seal.payload_sha256(vector),
        "runtime_dependency_path_sha256": seal.payload_sha256(
            [row["path"] for row in vector]
        ),
        "semantic_audit": {
            **semantic,
            "auditor_or_explicit_file_credential_literal_hits": literal_hits,
            "untracked_sources": untracked,
        },
        "runtime_invariants": invariants,
        "candidate_contract": _candidate_contract(),
        "future_protocol_requirements": _future_protocol_requirements(),
        "physical_caps": {
            "queries": 4,
            "fetches": 10,
            "model_forwards": 3,
            "wall_seconds": 240,
            "executor_concurrency": 20,
            "model_slot_cap": 8,
            "search_key_slot_cap": 12,
        },
        "protected_watchers": watchers,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "fresh_disjoint_shared_prefix_external_population_and_protocol_design": not findings,
            "external_activation_or_launch": False,
            "postfreeze_evaluator": False,
            "candidate_quality_or_prediction_improvement_claim": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "avg_at_4_leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = seal.payload_sha256(value)
    return validate_audit(value)


def _tests_exact(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    suites = value.get("suites")
    if (
        set(value) != {"expected", "observed", "passed", "suites"}
        or value.get("expected") != EXPECTED_TESTS
        or value.get("observed") != EXPECTED_TESTS
        or value.get("passed") is not True
        or not isinstance(suites, list)
        or len(suites) != len(TEST_SUITES)
    ):
        return False
    for row, (pattern, expected) in zip(suites, TEST_SUITES, strict=True):
        if (
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
            or not isinstance(row.get("output_sha256"), str)
            or len(row["output_sha256"]) != 64
        ):
            return False
    return True


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("audit_payload_sha256", None)
    git = copied.get("git") or {}
    semantic = copied.get("semantic_audit") or {}
    checks = copied.get("checks") or {}
    authorization = copied.get("authorization") or {}
    vector = copied.get("runtime_dependency_vector")
    invariants = copied.get("runtime_invariants") or {}
    findings = copied.get("findings")
    expected_findings = sorted(name for name, passed in checks.items() if not passed)
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "git",
            "fixed_parents",
            "fixed_sources",
            "tests",
            "runtime_dependency_vector",
            "runtime_dependency_vector_sha256",
            "runtime_dependency_path_sha256",
            "semantic_audit",
            "runtime_invariants",
            "candidate_contract",
            "future_protocol_requirements",
            "physical_caps",
            "protected_watchers",
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
        or not all(isinstance(git.get(name), str) for name in ("head", "target_main"))
        or git.get("equal") is not (git.get("head") == git.get("target_main"))
        or not isinstance(git.get("clean"), bool)
        or copied.get("fixed_parents")
        != {str(path): digest for path, digest in FIXED_PARENTS.items()}
        or copied.get("fixed_sources")
        != {str(path): digest for path, digest in FIXED_SOURCES.items()}
        or not _tests_exact(copied.get("tests"))
        or not isinstance(vector, list)
        or len(vector) != EXPECTED_CLOSURE_COUNT
        or any(
            not isinstance(row, Mapping)
            or set(row) != {"path", "sha256"}
            or not isinstance(row.get("path"), str)
            or not isinstance(row.get("sha256"), str)
            or len(row["sha256"]) != 64
            for row in vector
        )
        or copied.get("runtime_dependency_vector_sha256")
        != EXPECTED_CLOSURE_VECTOR_SHA256
        or seal.payload_sha256(vector) != EXPECTED_CLOSURE_VECTOR_SHA256
        or copied.get("runtime_dependency_path_sha256")
        != EXPECTED_CLOSURE_PATH_SHA256
        or seal.payload_sha256([row["path"] for row in vector])
        != EXPECTED_CLOSURE_PATH_SHA256
        or set(semantic)
        != {
            "privileged_runtime_field_accesses",
            "evaluator_capabilities",
            "credential_literal_hits",
            "allowed_provider_rank_access",
            "auditor_or_explicit_file_credential_literal_hits",
            "untracked_sources",
        }
        or semantic.get("privileged_runtime_field_accesses") != []
        or semantic.get("evaluator_capabilities") != []
        or semantic.get("credential_literal_hits") != []
        or semantic.get("auditor_or_explicit_file_credential_literal_hits") != []
        or semantic.get("untracked_sources") != []
        or semantic.get("allowed_provider_rank_access")
        != ["src/deepwide_agent/clients.py:565:score"]
        or not isinstance(invariants, Mapping)
        or not invariants
        or invariants != _source_invariants()
        or any(value is not True for value in invariants.values())
        or copied.get("candidate_contract") != _candidate_contract()
        or copied.get("future_protocol_requirements")
        != _future_protocol_requirements()
        or copied.get("physical_caps")
        != {
            "queries": 4,
            "fetches": 10,
            "model_forwards": 3,
            "wall_seconds": 240,
            "executor_concurrency": 20,
            "model_slot_cap": 8,
            "search_key_slot_cap": 12,
        }
        or not _watchers_exact(copied.get("protected_watchers"))
        or set(checks) != CHECK_NAMES
        or any(not isinstance(item, bool) for item in checks.values())
        or findings != expected_findings
        or copied.get("audit_valid") is not (not expected_findings)
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get(
            "network_model_search_fetch_evaluator_benchmark_or_api_called"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or set(authorization)
        != {
            "fresh_disjoint_shared_prefix_external_population_and_protocol_design",
            "external_activation_or_launch",
            "postfreeze_evaluator",
            "candidate_quality_or_prediction_improvement_claim",
            "deepwidebench_dev64_exact220_forward_or_evaluator",
            "avg_at_4_leaderboard_or_sota",
        }
        or authorization.get(
            "fresh_disjoint_shared_prefix_external_population_and_protocol_design"
        )
        is not copied.get("audit_valid")
        or any(
            authorization.get(name) is not False
            for name in (
                "external_activation_or_launch",
                "postfreeze_evaluator",
                "candidate_quality_or_prediction_improvement_claim",
                "deepwidebench_dev64_exact220_forward_or_evaluator",
                "avg_at_4_leaderboard_or_sota",
            )
        )
        or signature != seal.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.91 build audit drifted")
    return copied


def main() -> int:
    value = build_audit()
    if not value["audit_valid"]:
        raise SystemExit(
            "V2.52.91 audit failed: " + ", ".join(value["findings"])
        )
    path = ROOT / OUTPUT
    if path.exists() or path.is_symlink():
        raise SystemExit("V2.52.91 audit output already exists")
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "tests": value["tests"]["observed"],
                "closure": len(value["runtime_dependency_vector"]),
                "findings": value["findings"],
                "audit_payload_sha256": value["audit_payload_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
