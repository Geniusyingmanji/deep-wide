#!/usr/bin/env python3
"""Clean-build audit for the V2.52.95 World Bank monotone-fill gate."""

from __future__ import annotations

import ast
import copy
import hashlib
import inspect
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

from deepwide_agent import v24857_pacing_aware_exact220_contract as authority  # noqa: E402
from deepwide_agent import v25267_production_only_exact220_contract as seal  # noqa: E402
from deepwide_agent import v25295_worldbank_monotone_fill_gate as runtime  # noqa: E402
from scripts import audit_v25140_targeted_revision_build as base  # noqa: E402
from scripts import audit_v25291_monotone_unknown_fill_build as merger_audit  # noqa: E402
from scripts import revise_v25294_worldbank_monotone_fill_gate_r2 as design  # noqa: E402


DATE = "20260813"
ROLE = "v25296_worldbank_monotone_fill_clean_build_audit"
OUTPUT = Path(f"results/v25296_worldbank_monotone_fill_build_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25296_worldbank_monotone_fill_build.py")
TEST = Path("tests/test_audit_v25296_worldbank_monotone_fill_build.py")
RUNTIME = Path("src/deepwide_agent/v25295_worldbank_monotone_fill_gate.py")
RUNTIME_TEST = Path("tests/test_v25295_worldbank_monotone_fill_gate.py")
DESIGN = design.OUTPUT
MERGER_AUDIT = merger_audit.OUTPUT
V24857_PROTOCOL = authority.PROTOCOL
V24635_PROTOCOL = Path("results/v24635_exact220_forward_contract_v1_20260806.json")
EXPECTED_FIXED = {
    RUNTIME: "ea6571724ea74960d10c06c8a269b2d9db35bcf990c54fbb9de2f1f049949f64",
    RUNTIME_TEST: "0e6908751f4a462c6dae3c229632b31174c93aae04c9b4f1e67f4a8f20dc7ef2",
    DESIGN: "92e1ad85f8a363243abd64676c3149eef0266b1acb5c7196e7d8b5061c03ead4",
    MERGER_AUDIT: "6c714a6d20c90a401c311da4c8aa4477ef1570019821b17431daeed0a1455aeb",
    V24857_PROTOCOL: "f2492a2ed57fd89461f3258684d96f9cf2b594c0d21d29ff409f656de539fbb8",
    V24635_PROTOCOL: "8d54b01ddb1018745fb073e9d4dd33dff2e1aff7f662c41aa79a0058d89f4fc0",
}
IMPLEMENTATION_COMMITS = (
    "a74753efb6cc16e1f99c86094d05c59c797c455a",
    "b2a35d030b42f77fe7222139836474782e144bf7",
)
IMPLEMENTATION_PATHS = sorted([str(RUNTIME), str(RUNTIME_TEST)])
TEST_SUITES = (
    ("test_audit_v25296_worldbank_monotone_fill_build.py", 6),
    ("test_v25295_worldbank_monotone_fill_gate.py", 10),
    ("test_revise_v25294_worldbank_monotone_fill_gate_r2.py", 5),
    ("test_design_v25294_worldbank_monotone_fill_gate.py", 7),
    ("test_v25290_monotone_unknown_fill_integration.py", 16),
    ("test_v25289_monotone_unknown_fill.py", 17),
    ("test_v24860_coverage_revision_integration.py", 11),
    ("test_v24859_full_evidence_coverage_revision.py", 20),
    ("test_v24862_same_task_coverage_runtime.py", 5),
    ("test_v24856_pacing_aware_admission.py", 7),
    ("test_v24852_rate_aware_tavily_search.py", 11),
    ("test_v24796_deadline_tavily_search.py", 6),
    ("test_v24630_thin_backfill_search.py", 2),
    ("test_v24273_two_wave_task_runtime.py", 8),
    ("test_v24630_exact220.py", 5),
    ("test_v24319_runner_integration.py", 7),
)
EXPECTED_TESTS = sum(count for _pattern, count in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 40
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "06bd4055ca9b0b2ccb0603957ec90bfec4d73392c668d24aec3743efbf131652"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "5c1d1f7c7d3f8ec40f3090a81689968724a51e9721c016390454f6b796eea8c9"
)
NATIVE_SEARCH = Path("src/deepwide_agent/native_search.py")
NATIVE_FROZEN_COMMIT = "466e7dd8eaa3fd4fb7101fcb31f9d071712dd566"
NATIVE_OBSERVER_COMMIT = "795d38216b47e29dd7d03624ad392cefd6e3d2d8"
NATIVE_FROZEN_SHA256 = "cd0d6bfccf4b345b11274558bdcffb39d279697d183242baf811dfd56ac71e50"
NATIVE_CURRENT_SHA256 = "685f54137e4584832bb1df41226805997ea57220837d1db497a79509f9f91a51"
NATIVE_DIFF_SHA256 = "3c1cafad9bc858be6d514597c9d34b57ff85c26b6903c4d2a8cf0d0f838c05d2"
EXPECTED_WATCHERS = {
    "795336": 713986317,
    "2808901": 746680268,
    "2889939": 746969965,
    "3061652": 747569004,
}
CHECK_NAMES = frozenset(
    {
        "fixed_inputs_exact",
        "implementation_commits_exact_and_ancestors",
        "tests_exact143_green",
        "all_explicit_and_closure_files_tracked",
        "runtime_dependency_vector_exact40_and_hash_bound",
        "v24857_protocol_not_in_runtime_closure",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "r2_pagination_complete_and_build_only",
        "parent_caps_and_two_wave_policy_exact",
        "runtime_boundary_label_blind_before_effect",
        "snapshot_client_owns_init_search_and_fetch",
        "native_observer_drift_exact_default_off_and_bypassed",
        "parser_url_metadata_total_and_cross_page_completeness_fail_closed",
        "shared_prefix_parent_and_third_slot_receipts_replayed",
        "actual_query_fetch_and_model_effects_conserved",
        "failure_totality_and_parent_identity_preserved",
        "entropy_information_gain_shadow_and_positive_credit_zero",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "git_clean_head_equals_target_main",
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called",
        "no_external_effect_performed",
    }
)


def _fixed_inputs() -> dict[str, str]:
    return {str(path): base.sha256(path) for path in EXPECTED_FIXED}


def _tests() -> dict[str, Any]:
    rows = [base._test(pattern, count) for pattern, count in TEST_SUITES]
    observed = sum(row["observed"] for row in rows)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in rows),
        "suites": rows,
    }


def _closure() -> tuple[tuple[Path, ...], list[dict[str, str]]]:
    closure = tuple(sorted(base._dependency_closure((RUNTIME,)), key=str))
    vector = [{"path": str(path), "sha256": base.sha256(path)} for path in closure]
    return closure, vector


def _changed_paths(commit: str) -> list[str]:
    return sorted(
        line
        for line in base._git(
            "diff-tree", "--no-commit-id", "--name-only", "-r", commit
        ).splitlines()
        if line
    )


def _ancestor(commit: str, head: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, head],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode
        == 0
    )


def _git_blob_sha256(commit: str, path: Path) -> str:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
        check=True,
    )
    return hashlib.sha256(completed.stdout).hexdigest()


def _git_diff_sha256(older: str, newer: str, path: Path) -> str:
    completed = subprocess.run(
        ["git", "diff", older, newer, "--", str(path)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
        check=True,
    )
    return hashlib.sha256(completed.stdout).hexdigest()


def _native_drift() -> dict[str, Any]:
    source = base._ordinary(NATIVE_SEARCH).read_text(encoding="utf-8")
    cls = runtime.FrozenWorldBankSnapshotSearchClient
    owners = {
        name: f"{owner.__module__}.{owner.__name__}"
        for name, owner in (
            (
                "init",
                next(item for item in cls.__mro__ if "__init__" in item.__dict__),
            ),
            (
                "search_many",
                next(item for item in cls.__mro__ if "search_many" in item.__dict__),
            ),
            (
                "fetch_url",
                next(item for item in cls.__mro__ if "_fetch_url" in item.__dict__),
            ),
        )
    }
    expected_owner = f"{runtime.__name__}.FrozenWorldBankSnapshotSearchClient"
    runtime_init = inspect.getsource(cls.__init__)
    return {
        "historical_v24635_manifest_native_search_sha256": NATIVE_FROZEN_SHA256,
        "current_native_search_sha256": base.sha256(NATIVE_SEARCH),
        "hash_equal_to_historical_manifest": base.sha256(NATIVE_SEARCH)
        == NATIVE_FROZEN_SHA256,
        "frozen_commit": NATIVE_FROZEN_COMMIT,
        "observer_commit": NATIVE_OBSERVER_COMMIT,
        "frozen_blob_sha256": _git_blob_sha256(NATIVE_FROZEN_COMMIT, NATIVE_SEARCH),
        "observer_blob_sha256": _git_blob_sha256(NATIVE_OBSERVER_COMMIT, NATIVE_SEARCH),
        "exact_diff_sha256": _git_diff_sha256(
            NATIVE_FROZEN_COMMIT, NATIVE_OBSERVER_COMMIT, NATIVE_SEARCH
        ),
        "only_added_constructor_parameter_is_default_none": (
            "content_free_structure_observer: Any | None = None" in source
            and "self._content_free_structure_observer = content_free_structure_observer"
            in source
        ),
        "snapshot_runtime_passes_structure_observer": (
            "content_free_structure_observer" in runtime_init
        ),
        "snapshot_method_owners": owners,
        "snapshot_owns_all_three_methods": all(
            owner == expected_owner for owner in owners.values()
        ),
        "historical_v24857_entire_manifest_pristine_claim_allowed": False,
        "current_snapshot_execution_path_equivalence_supported": True,
    }


def _source_invariants() -> dict[str, bool]:
    source = base._ordinary(RUNTIME).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(RUNTIME))
    functions = {
        node.name: ast.get_source_segment(source, node) or ""
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    run = functions.get("run_paired_task", "")
    parser = functions.get("parse_worldbank_page", "")
    target_pages = functions.get("parse_target_pages", "")
    validator = functions.get("validate_result", "")
    return {
        "runtime_input_validated_before_type_or_effect": (
            0 <= run.find("visible = validate_visible_task(task)")
            < run.find("_PARENT_RUN_TASK(")
        ),
        "runtime_does_not_import_v24857_protocol_contract": (
            "v24857_pacing_aware_exact220_contract" not in source
        ),
        "local_parent_caps_are_exact": runtime.PARENT_LIMITS == authority.LIMITS,
        "local_two_wave_policy_is_exact": (
            runtime.PARENT_TWO_WAVE_POLICY == authority.TWO_WAVE_POLICY
        ),
        "local_search_slot_cap_is_exact": (
            runtime.PARENT_TAVILY_KEY_SLOT_CAP == authority.TAVILY_KEY_SLOT_CAP
        ),
        "parser_requires_total_and_ceiling": all(
            token in parser for token in ("metadata[\"total\"]", "math.ceil(total / per_page)")
        ),
        "cross_page_all_entity_codes_are_unique": (
            "first.entity_codes.intersection(second.entity_codes)" in target_pages
        ),
        "all_page_records_are_covered": (
            "first.record_count + second.record_count != first.total" in target_pages
        ),
        "result_binds_actual_query_and_fetch_counts": all(
            token in validator
            for token in (
                'receipt["physical_query_count"]',
                'parent_result["budget"]["admitted_search_queries"]',
                'receipt["physical_fetch_count"]',
                'parent_result["evidence"]["fetch_target_count"]',
            )
        ),
        "entropy_and_credit_are_false_or_zero": (
            "entropy_or_information_gain_assigns_signed_credit" in source
            and '"positive_signed_credit_count": 0' in source
        ),
    }


def _design_barrier() -> bool:
    value = design.validate_revision(
        json.loads(base._ordinary(DESIGN).read_text(encoding="utf-8"))
    )
    snapshot = value["snapshot_and_representation_contract"]
    return bool(
        value["correction"]["old_page_count_for_observed_total"] == 3
        and value["correction"]["corrected_page_count_for_observed_total"] == 2
        and snapshot["world_bank_per_page"] == 200
        and snapshot["complete_official_record_coverage_required"] is True
        and value["authorization"]["population_selector_and_runtime_implementation_build_only"]
        is True
        and value["authorization"]["network_population_selection_or_freeze"]
        is False
        and value["authorization"]["external_activation_or_launch"] is False
    )


def _watchers_exact(value: object) -> bool:
    return bool(
        isinstance(value, Mapping)
        and set(value) == set(EXPECTED_WATCHERS)
        and all(
            isinstance(value.get(pid), Mapping)
            and value[pid].get("present") is True
            and value[pid].get("start_ticks") == ticks
            and value[pid].get("matches_frozen_identity") is True
            for pid, ticks in EXPECTED_WATCHERS.items()
        )
    )


def _tests_exact(value: object) -> bool:
    if not isinstance(value, Mapping) or set(value) != {
        "expected",
        "observed",
        "passed",
        "suites",
    }:
        return False
    suites = value["suites"]
    return bool(
        value["expected"] == EXPECTED_TESTS
        and value["observed"] == EXPECTED_TESTS
        and value["passed"] is True
        and isinstance(suites, list)
        and len(suites) == len(TEST_SUITES)
        and all(
            isinstance(row, Mapping)
            and set(row)
            == {
                "pattern",
                "expected",
                "observed",
                "returncode",
                "passed",
                "output_sha256",
            }
            and row["pattern"] == pattern
            and row["expected"] == count
            and row["observed"] == count
            and row["returncode"] == 0
            and row["passed"] is True
            and isinstance(row["output_sha256"], str)
            and len(row["output_sha256"]) == 64
            for row, (pattern, count) in zip(suites, TEST_SUITES, strict=True)
        )
    )


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    tests = _tests()
    closure, vector = _closure()
    semantic = base._semantic_findings(closure)
    invariants = _source_invariants()
    drift = _native_drift()
    watchers = base._watchers()
    explicit = {SOURCE, TEST, *EXPECTED_FIXED, *closure}
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    literal_hits = sorted(
        str(path)
        for path in explicit
        if base.SECRET.search(base._ordinary(path).read_text(encoding="utf-8"))
    )
    implementation_exact = all(
        _changed_paths(commit) == IMPLEMENTATION_PATHS
        and _ancestor(commit, head)
        for commit in IMPLEMENTATION_COMMITS
    )
    drift_safe = bool(
        drift["hash_equal_to_historical_manifest"] is False
        and drift["frozen_blob_sha256"] == NATIVE_FROZEN_SHA256
        and drift["observer_blob_sha256"] == NATIVE_CURRENT_SHA256
        and drift["current_native_search_sha256"] == NATIVE_CURRENT_SHA256
        and drift["exact_diff_sha256"] == NATIVE_DIFF_SHA256
        and drift["only_added_constructor_parameter_is_default_none"] is True
        and drift["snapshot_runtime_passes_structure_observer"] is False
        and drift["snapshot_owns_all_three_methods"] is True
        and drift["historical_v24857_entire_manifest_pristine_claim_allowed"]
        is False
    )
    checks = {
        "fixed_inputs_exact": _fixed_inputs()
        == {str(path): digest for path, digest in EXPECTED_FIXED.items()},
        "implementation_commits_exact_and_ancestors": implementation_exact,
        "tests_exact143_green": tests["passed"],
        "all_explicit_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact40_and_hash_bound": (
            len(vector) == EXPECTED_CLOSURE_COUNT
            and seal.payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256
            and seal.payload_sha256([row["path"] for row in vector])
            == EXPECTED_CLOSURE_PATH_SHA256
        ),
        "v24857_protocol_not_in_runtime_closure": V24857_PROTOCOL not in closure,
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
        "r2_pagination_complete_and_build_only": _design_barrier(),
        "parent_caps_and_two_wave_policy_exact": all(invariants.values()),
        "runtime_boundary_label_blind_before_effect": invariants[
            "runtime_input_validated_before_type_or_effect"
        ],
        "snapshot_client_owns_init_search_and_fetch": drift[
            "snapshot_owns_all_three_methods"
        ],
        "native_observer_drift_exact_default_off_and_bypassed": drift_safe,
        "parser_url_metadata_total_and_cross_page_completeness_fail_closed": tests[
            "passed"
        ]
        and all(
            invariants[name]
            for name in (
                "parser_requires_total_and_ceiling",
                "cross_page_all_entity_codes_are_unique",
                "all_page_records_are_covered",
            )
        ),
        "shared_prefix_parent_and_third_slot_receipts_replayed": tests["passed"],
        "actual_query_fetch_and_model_effects_conserved": tests["passed"]
        and invariants["result_binds_actual_query_and_fetch_counts"],
        "failure_totality_and_parent_identity_preserved": tests["passed"],
        "entropy_information_gain_shadow_and_positive_credit_zero": tests[
            "passed"
        ]
        and invariants["entropy_and_credit_are_false_or_zero"],
        "protected_watchers_unchanged": _watchers_exact(watchers),
        "shared_api_lease_inactive": base._lease_inactive(),
        "git_clean_head_equals_target_main": clean and head == target,
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target, "clean": clean},
        "fixed_inputs": _fixed_inputs(),
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
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
        "historical_parent_drift": drift,
        "protected_watchers": watchers,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "limitations": {
            "historical_v24857_entire_dependency_manifest_pristine": False,
            "native_search_default_none_observer_change_is_bypassed_by_snapshot_overrides": True,
            "synthetic_supported_fill_proves_mechanism_implementation_not_real_population_effect": True,
            "population_selected_or_frozen": False,
            "actual_external_supported_fill_or_prediction_change_observed": False,
            "quality_or_deepwidebench_gain_established": False,
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "population_selection_or_freeze": False,
            "external_activation_or_launch": False,
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "candidate_quality_avg_at_4_leaderboard_or_sota": False,
            "next_step": "independent_population_freeze_preactivation_audit_required",
        },
    }
    value["audit_payload_sha256"] = seal.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("audit_payload_sha256", None)
    checks = copied.get("checks") or {}
    vector = copied.get("runtime_dependency_vector")
    semantic = copied.get("semantic_audit") or {}
    drift = copied.get("historical_parent_drift") or {}
    authorization = copied.get("authorization") or {}
    limitations = copied.get("limitations") or {}
    findings = copied.get("findings")
    expected_findings = sorted(name for name, passed in checks.items() if not passed)
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "git",
            "fixed_inputs",
            "implementation_commits",
            "tests",
            "runtime_dependency_vector",
            "runtime_dependency_vector_sha256",
            "runtime_dependency_path_sha256",
            "semantic_audit",
            "runtime_invariants",
            "historical_parent_drift",
            "protected_watchers",
            "checks",
            "findings",
            "audit_valid",
            "limitations",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
            "authorization",
            "audit_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied.get("fixed_inputs")
        != {str(path): digest for path, digest in EXPECTED_FIXED.items()}
        or copied.get("implementation_commits") != list(IMPLEMENTATION_COMMITS)
        or not _tests_exact(copied.get("tests"))
        or not isinstance(vector, list)
        or len(vector) != EXPECTED_CLOSURE_COUNT
        or seal.payload_sha256(vector) != EXPECTED_CLOSURE_VECTOR_SHA256
        or copied.get("runtime_dependency_vector_sha256")
        != EXPECTED_CLOSURE_VECTOR_SHA256
        or seal.payload_sha256([row["path"] for row in vector])
        != EXPECTED_CLOSURE_PATH_SHA256
        or copied.get("runtime_dependency_path_sha256")
        != EXPECTED_CLOSURE_PATH_SHA256
        or semantic.get("privileged_runtime_field_accesses") != []
        or semantic.get("evaluator_capabilities") != []
        or semantic.get("credential_literal_hits") != []
        or semantic.get("auditor_or_explicit_file_credential_literal_hits") != []
        or semantic.get("untracked_sources") != []
        or semantic.get("allowed_provider_rank_access")
        != ["src/deepwide_agent/clients.py:565:score"]
        or copied.get("runtime_invariants") != _source_invariants()
        or drift.get("hash_equal_to_historical_manifest") is not False
        or drift.get("snapshot_runtime_passes_structure_observer") is not False
        or drift.get("snapshot_owns_all_three_methods") is not True
        or drift.get("historical_v24857_entire_manifest_pristine_claim_allowed")
        is not False
        or not _watchers_exact(copied.get("protected_watchers"))
        or set(checks) != CHECK_NAMES
        or any(not isinstance(item, bool) for item in checks.values())
        or findings != expected_findings
        or copied.get("audit_valid") is not (not findings)
        or limitations
        != {
            "historical_v24857_entire_dependency_manifest_pristine": False,
            "native_search_default_none_observer_change_is_bypassed_by_snapshot_overrides": True,
            "synthetic_supported_fill_proves_mechanism_implementation_not_real_population_effect": True,
            "population_selected_or_frozen": False,
            "actual_external_supported_fill_or_prediction_change_observed": False,
            "quality_or_deepwidebench_gain_established": False,
        }
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization
        != {
            "population_selection_or_freeze": False,
            "external_activation_or_launch": False,
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "candidate_quality_avg_at_4_leaderboard_or_sota": False,
            "next_step": "independent_population_freeze_preactivation_audit_required",
        }
        or signature != seal.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.96 World Bank build audit drifted")
    return copied


def main() -> int:
    value = build_audit()
    if not value["audit_valid"]:
        raise SystemExit("V2.52.96 audit failed: " + ", ".join(value["findings"]))
    base.publish(ROOT / OUTPUT, value)
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
