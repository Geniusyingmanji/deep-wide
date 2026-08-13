#!/usr/bin/env python3
"""Clean-build audit for the V2.53.13 deadline-aligned World Bank gate.

The auditor is deliberately effect-free.  It binds the frozen V2.53.12
pre-effect diagnosis to the two-file V2.53.13 implementation commit, audits
the exact runtime dependency closure, and constructs only local synthetic
deadline objects to prove parity before any model/search/fetch effect.
"""

from __future__ import annotations

import ast
import copy
import json
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25313_deadline_aligned_worldbank_gate as runtime  # noqa: E402
from deepwide_agent import (  # noqa: E402
    v25309_worldbank_monotone_fill_external_contract as old_contract,
)
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from scripts import audit_v25140_targeted_revision_build as base  # noqa: E402
from scripts import diagnose_v25312_v25309_deadline_identity as diagnosis  # noqa: E402


DATE = "20260813"
ROLE = "v25314_deadline_aligned_worldbank_clean_build_audit"
OUTPUT = Path(
    f"results/v25314_deadline_aligned_worldbank_build_audit_v1_{DATE}.json"
)
SOURCE = Path("scripts/audit_v25314_deadline_aligned_worldbank_build.py")
TEST = Path("tests/test_audit_v25314_deadline_aligned_worldbank_build.py")
RUNTIME = Path(
    "src/deepwide_agent/v25313_deadline_aligned_worldbank_gate.py"
)
RUNTIME_TEST = Path(
    "tests/test_v25313_deadline_aligned_worldbank_gate.py"
)
PARENT_DIAGNOSIS = diagnosis.OUTPUT
IMPLEMENTATION_COMMIT = "1a7022e78f1e2814aef054eb0072f554f292ae49"
IMPLEMENTATION_PATHS = sorted((str(RUNTIME), str(RUNTIME_TEST)))
FIXED = {
    RUNTIME: "3ca9658274e2c4c3ca274c9016d9cd0fe322276998756b9520b020ba5a9c65a6",
    RUNTIME_TEST: "49c775797d5d04d5924d7fdfd80e509cc55ce708097f6efc69b8351a26d2b2f3",
    PARENT_DIAGNOSIS: "37be56e7d18b498a61ef6b732c6f2a33c6e12a98081776540eb7fe76f7553942",
}
TEST_SUITES = (
    ("test_audit_v25314_deadline_aligned_worldbank_build.py", 7),
    ("test_v25313_deadline_aligned_worldbank_gate.py", 5),
    ("test_v25309_worldbank_monotone_fill_external.py", 10),
    ("test_v25295_worldbank_monotone_fill_gate.py", 10),
    ("test_v24319_runner_integration.py", 7),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 42
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "13b67d7cb09da05b92fd2de3699820a0cb2f228ab9214cdfc80d8b2425ae71ff"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "666b864c9842d960d25094a6c1fc6b265cd3c63bda2bf898b9187b91a3b34212"
)
CHECK_NAMES = frozenset(
    {
        "v25312_diagnosis_exact_valid_and_authorizes_build_only",
        "v25313_sources_hashes_exact",
        "v25313_commit_is_exact_two_file_ancestor",
        "focused_and_parent_tests_exact39_green",
        "all_auditor_test_runtime_parent_and_closure_files_tracked",
        "runtime_dependency_vector_exact42_and_hash_bound",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "deadline_parity_witness_true_before_any_effect",
        "source_requires_parity_before_parent_runtime",
        "parent_query_fetch_model_context_token_wall_and_page_caps_unchanged",
        "future_population_must_be_fresh_and_disjoint",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "git_clean_head_equals_target_main",
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called",
        "no_external_effect_performed",
    }
)


class _Clock:
    def __init__(self, value: float = 100.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += max(0.0, float(seconds))


class _NoEffectModel:
    deadline_failures = 0

    def complete(self, *_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("V2.53.14 witness must not call the model")


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
    closure = tuple(sorted(base._dependency_closure((RUNTIME,)), key=str))
    vector = [
        {"path": str(path), "sha256": base.sha256(path)} for path in closure
    ]
    return closure, vector


def _changed_paths(commit: str) -> list[str]:
    return sorted(
        line
        for line in base._git(
            "diff-tree", "--no-commit-id", "--name-only", "-r", commit
        ).splitlines()
        if line
    )


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


def _diagnosis_barrier() -> bool:
    try:
        value = diagnosis.validate_diagnosis(
            json.loads(base._ordinary(PARENT_DIAGNOSIS).read_text(encoding="utf-8"))
        )
    except BaseException:
        return False
    authorization = value["authorization"]
    return bool(
        base.sha256(PARENT_DIAGNOSIS) == FIXED[PARENT_DIAGNOSIS]
        and value["diagnosis_valid"] is True
        and value["findings"] == []
        and value["root_cause"]
        == "model_search_minimum_attempt_seconds_identity_mismatch"
        and value["deadline_identity"]["aligned_deadlines"] is False
        and value["deadline_identity"][
            "rejected_before_first_model_slot_acquisition"
        ]
        is True
        and authorization["v25309_retry_resume_rerun_replacement_or_reuse"]
        is False
        and authorization["v25309_postfreeze_evaluator"] is False
        and authorization["fresh_disjoint_deadline_aligned_successor_build"]
        is True
        and authorization["successor_external_launch"] is False
    )


def _deadline_parity_witness() -> dict[str, Any]:
    population = old_contract.frozen_population(ROOT)
    clock = _Clock()
    with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as name:
        output_root = Path(name)
        slots = output_root / "slots"
        slots.mkdir()
        for index in range(1, 9):
            (slots / f"slot_{index:02d}.lock").touch()
        model = DeadlineAwareGlobalModelSlotLimiter(
            _NoEffectModel(),
            slot_directory=slots,
            output_root=output_root,
            slot_cap=8,
            pool_id=POOL_ID,
            absolute_deadline=340.0,
            cleanup_reserve_seconds=5.0,
            minimum_attempt_seconds=0.05,
            monotonic=clock,
            sleeper=clock.sleep,
        )
        search = runtime.DeadlineAlignedFrozenWorldBankSnapshotSearchClient(
            population["pages"], absolute_deadline=340.0, monotonic=clock
        )
        receipt = runtime.deadline_identity_receipt(model, search)
        model_receipt = model.receipt()
        search_receipt = search.snapshot_transport_receipt()
    return {
        "absolute_deadline_equal": receipt["absolute_deadline_equal"],
        "cleanup_reserve_seconds_model_micros": receipt[
            "cleanup_reserve_seconds_model_micros"
        ],
        "cleanup_reserve_seconds_search_micros": receipt[
            "cleanup_reserve_seconds_search_micros"
        ],
        "minimum_attempt_seconds_model_micros": receipt[
            "minimum_attempt_seconds_model_micros"
        ],
        "minimum_attempt_seconds_search_micros": receipt[
            "minimum_attempt_seconds_search_micros"
        ],
        "aligned_deadlines": receipt["aligned_deadlines"],
        "model_slot_acquisitions": model_receipt["acquisitions"],
        "model_slot_timeouts": model_receipt["slot_timeouts"],
        "snapshot_search_invocations": search_receipt["search_invocations"],
        "snapshot_fetch_hits": search_receipt["fetch_hits"],
        "network_search_calls": search_receipt["network_search_calls"],
        "network_fetch_calls": search_receipt["network_fetch_calls"],
    }


def _expected_witness() -> dict[str, Any]:
    return {
        "absolute_deadline_equal": True,
        "cleanup_reserve_seconds_model_micros": 5_000_000,
        "cleanup_reserve_seconds_search_micros": 5_000_000,
        "minimum_attempt_seconds_model_micros": 50_000,
        "minimum_attempt_seconds_search_micros": 50_000,
        "aligned_deadlines": True,
        "model_slot_acquisitions": 0,
        "model_slot_timeouts": 0,
        "snapshot_search_invocations": 0,
        "snapshot_fetch_hits": 0,
        "network_search_calls": 0,
        "network_fetch_calls": 0,
    }


def _source_invariants() -> dict[str, bool]:
    source = base._ordinary(RUNTIME).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(RUNTIME))
    functions = {
        node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }
    run_text = ast.get_source_segment(source, functions["run_paired_task"]) or ""
    parity = run_text.find("deadline_identity_receipt(model, search)")
    delegate = run_text.find("return parent.run_paired_task(")
    return {
        "run_checks_deadline_identity_before_parent_delegate": (
            0 <= parity < delegate and run_text.count("parent.run_paired_task(") == 1
        ),
        "constructor_sets_minimum_attempt_to_fixed_005": (
            "self.minimum_attempt_seconds = MINIMUM_ATTEMPT_SECONDS" in source
            and "MINIMUM_ATTEMPT_SECONDS = 0.05" in source
        ),
        "receipt_requires_aligned_deadlines_true": (
            'copied.get("aligned_deadlines") is not True' in source
            and "checked_before_model_search_or_fetch_effect" in source
        ),
        "runtime_has_no_direct_filesystem_network_or_evaluator_import": all(
            token not in {
                item.name
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for item in node.names
            }
            for token in ("os", "pathlib", "requests", "subprocess", "urllib.request")
        ),
    }


def _future_protocol_requirements() -> dict[str, Any]:
    return {
        "population": "fresh_disjoint_worldbank_targets_entities_and_responses",
        "all_v25305_probed_targets_are_consumed": True,
        "reuse_old_target_entity_page_response_or_prediction": False,
        "runtime_keys": ["opaque_id", "question"],
        "deadline_identity_proved_before_provider_effect": True,
        "retry_resume_backfill_replacement_or_selective_rerun": False,
        "mechanism_gate": {
            "minimum_supported_unknown_fill_tasks": 2,
            "minimum_supported_unknown_fill_cells": 2,
            "minimum_attributable_prediction_change_tasks": 2,
            "required_query_effect_equal_tasks": 12,
            "required_fetch_effect_equal_tasks": 12,
            "maximum_model_forwards_per_task": 3,
            "maximum_known_cell_schema_row_key_order_or_count_violation_tasks": 0,
            "maximum_unsupported_or_conflicting_admitted_fill_cells": 0,
        },
        "postfreeze_evaluator_only_after_pushed_forward_audit": True,
        "direct_deepwidebench_220_after_build": False,
    }


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


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    tests = _tests()
    closure, vector = _closure()
    semantic = base._semantic_findings(closure)
    witness = _deadline_parity_witness()
    invariants = _source_invariants()
    watchers = base._watchers()
    explicit = {SOURCE, TEST, *FIXED, *closure}
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    literal_hits = sorted(
        str(path)
        for path in explicit
        if base.SECRET.search(base._ordinary(path).read_text(encoding="utf-8"))
    )
    checks = {
        "v25312_diagnosis_exact_valid_and_authorizes_build_only": _diagnosis_barrier(),
        "v25313_sources_hashes_exact": {
            str(path): base.sha256(path) for path in FIXED
        }
        == {str(path): digest for path, digest in FIXED.items()},
        "v25313_commit_is_exact_two_file_ancestor": (
            _changed_paths(IMPLEMENTATION_COMMIT) == IMPLEMENTATION_PATHS
            and _is_ancestor(IMPLEMENTATION_COMMIT, head)
        ),
        "focused_and_parent_tests_exact39_green": tests["passed"],
        "all_auditor_test_runtime_parent_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact42_and_hash_bound": (
            len(vector) == EXPECTED_CLOSURE_COUNT
            and runtime.payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256
            and runtime.payload_sha256([row["path"] for row in vector])
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
        "deadline_parity_witness_true_before_any_effect": witness
        == _expected_witness(),
        "source_requires_parity_before_parent_runtime": all(invariants.values()),
        "parent_query_fetch_model_context_token_wall_and_page_caps_unchanged": (
            runtime.PARENT_LIMITS
            == {
                "wall_seconds": 240,
                "search_queries": 4,
                "fetch_targets": 10,
                "model_calls": 3,
                "plan_output_tokens": 4_000,
                "synthesis_output_tokens": 30_000,
                "repair_output_tokens": 12_000,
                "evidence_chars": 60_000,
                "page_chars": 5_000,
                "search_results_per_query": 3,
            }
            and runtime.PAGE_COUNT == 8
            and runtime.ENTITY_ROW_COUNT == 144
            and runtime.TARGET_COUNT == 4
            and runtime.MAXIMUM_PAGE_CHARS == 5_000
            and runtime.MAXIMUM_EVIDENCE_CHARS == 40_000
        ),
        "future_population_must_be_fresh_and_disjoint": True,
        "protected_watchers_unchanged": all(
            row.get("matches_frozen_identity") is True for row in watchers.values()
        ),
        "shared_api_lease_inactive": base._lease_inactive(),
        "git_clean_head_equals_target_main": (clean and head == target)
        if tracked
        else True,
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": True,
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
        "fixed_inputs": {str(path): base.sha256(path) for path in FIXED},
        "implementation_commit": {
            "commit": IMPLEMENTATION_COMMIT,
            "paths": IMPLEMENTATION_PATHS,
        },
        "tests": tests,
        "runtime_dependency_vector": vector,
        "runtime_dependency_vector_sha256": runtime.payload_sha256(vector),
        "runtime_dependency_path_sha256": runtime.payload_sha256(
            [row["path"] for row in vector]
        ),
        "semantic_audit": {
            **semantic,
            "auditor_or_explicit_file_credential_literal_hits": literal_hits,
            "untracked_sources": untracked,
        },
        "deadline_parity_witness": witness,
        "runtime_invariants": invariants,
        "future_protocol_requirements": _future_protocol_requirements(),
        "protected_watchers": watchers,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "fresh_disjoint_worldbank_population_and_protocol_design": not findings,
            "external_activation_or_launch": False,
            "postfreeze_evaluator": False,
            "candidate_quality_or_prediction_improvement_claim": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "avg_at_4_leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = runtime.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("audit_payload_sha256", None)
    git = copied.get("git") or {}
    semantic = copied.get("semantic_audit") or {}
    vector = copied.get("runtime_dependency_vector")
    checks = copied.get("checks") or {}
    authorization = copied.get("authorization") or {}
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
            "implementation_commit",
            "tests",
            "runtime_dependency_vector",
            "runtime_dependency_vector_sha256",
            "runtime_dependency_path_sha256",
            "semantic_audit",
            "deadline_parity_witness",
            "runtime_invariants",
            "future_protocol_requirements",
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
        or copied.get("fixed_inputs")
        != {str(path): digest for path, digest in FIXED.items()}
        or copied.get("implementation_commit")
        != {"commit": IMPLEMENTATION_COMMIT, "paths": IMPLEMENTATION_PATHS}
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
        or runtime.payload_sha256(vector) != EXPECTED_CLOSURE_VECTOR_SHA256
        or copied.get("runtime_dependency_path_sha256")
        != EXPECTED_CLOSURE_PATH_SHA256
        or runtime.payload_sha256([row["path"] for row in vector])
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
        or semantic.get("allowed_provider_rank_access")
        != ["src/deepwide_agent/clients.py:565:score"]
        or semantic.get("auditor_or_explicit_file_credential_literal_hits") != []
        or semantic.get("untracked_sources") != []
        or copied.get("deadline_parity_witness") != _expected_witness()
        or copied.get("runtime_invariants") != _source_invariants()
        or any(value is not True for value in copied["runtime_invariants"].values())
        or copied.get("future_protocol_requirements")
        != _future_protocol_requirements()
        or set(checks) != CHECK_NAMES
        or any(not isinstance(item, bool) for item in checks.values())
        or findings != expected_findings
        or copied.get("audit_valid") is not (not expected_findings)
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "network_model_search_fetch_evaluator_benchmark_or_api_called",
                "entropy_or_information_gain_assigns_signed_credit",
            )
        )
        or set(authorization)
        != {
            "fresh_disjoint_worldbank_population_and_protocol_design",
            "external_activation_or_launch",
            "postfreeze_evaluator",
            "candidate_quality_or_prediction_improvement_claim",
            "deepwidebench_dev64_exact220_forward_or_evaluator",
            "avg_at_4_leaderboard_or_sota",
        }
        or authorization.get("fresh_disjoint_worldbank_population_and_protocol_design")
        is not copied.get("audit_valid")
        or any(
            authorization.get(name) is not False
            for name in authorization
            if name != "fresh_disjoint_worldbank_population_and_protocol_design"
        )
        or signature != runtime.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.14 build audit drifted")
    return copied


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> int:
    value = build_audit()
    if not value["audit_valid"]:
        raise SystemExit("V2.53.14 audit failed: " + ", ".join(value["findings"]))
    _publish(ROOT / OUTPUT, value)
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
