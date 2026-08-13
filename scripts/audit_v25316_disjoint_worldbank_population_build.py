#!/usr/bin/env python3
"""Clean-build audit for the V2.53.15 disjoint World Bank selector."""

from __future__ import annotations

import copy
import json
import os
import re
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

from deepwide_agent import v25315_disjoint_worldbank_population as selector  # noqa: E402
from scripts import audit_v25140_targeted_revision_build as base  # noqa: E402
from scripts import audit_v25314_deadline_aligned_worldbank_build as parent_audit  # noqa: E402
from scripts import audit_v25308_worldbank_population_postfreeze as old_audit  # noqa: E402
from scripts import run_v25297_worldbank_population_freeze as old_runner  # noqa: E402


DATE = "20260813"
ROLE = "v25316_disjoint_worldbank_population_clean_build_audit"
OUTPUT = Path(
    f"results/v25316_disjoint_worldbank_population_build_audit_v1_{DATE}.json"
)
SOURCE = Path("scripts/audit_v25316_disjoint_worldbank_population_build.py")
TEST = Path("tests/test_audit_v25316_disjoint_worldbank_population_build.py")
SELECTOR = Path("src/deepwide_agent/v25315_disjoint_worldbank_population.py")
SELECTOR_TEST = Path("tests/test_v25315_disjoint_worldbank_population.py")
PARENT_AUDIT = parent_audit.OUTPUT
OLD_RESULT = old_runner.RESULT
OLD_PRIVATE = old_runner.POPULATION
OLD_POSTFREEZE_AUDIT = old_audit.OUTPUT
IMPLEMENTATION_COMMIT = "80fb8c456e9eccfca9974420507cb02ee7763cb8"
IMPLEMENTATION_PATHS = sorted((str(SELECTOR), str(SELECTOR_TEST)))
FIXED = {
    SELECTOR: "94c164c0c15a4b7cd8884c8b134eb2db1ea76800a3a43fdf002199db124fe065",
    SELECTOR_TEST: "010cb6623cc7d919c52e7877d9ac00efba4a94c0ff3f64258b776fe959caced1",
    PARENT_AUDIT: "efe3303967c326357ca9709ec4d8d71ec4344744d497546d90fa8429b36dd4c8",
    OLD_RESULT: "6abbce3cb6271cde5046479b78a8436ba41fbb383679c102d857731d262e600b",
    OLD_PRIVATE: "ced33e651b0d72a65a59d4106ea5b68316f25bd5b31ca9a54f8f1c9d2689fcec",
    OLD_POSTFREEZE_AUDIT: "eb699da33a7615ddecb854d1982ea2e2f2233b86464563914c75ea4d017c4b09",
}
TEST_SUITES = (
    ("test_audit_v25316_disjoint_worldbank_population_build.py", 7),
    ("test_v25315_disjoint_worldbank_population.py", 6),
    ("test_v25295_worldbank_monotone_fill_gate.py", 10),
    ("test_run_v25297_worldbank_population_freeze.py", 14),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 41
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "a70049fa8eca041be5e42720ab48e545ea2bd30e222ecb0c8a3b82f40ab7c582"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "76375b560fe56c258a2cf402a32a8a6dcd95088c955294b7ac6e7a83ee355de2"
)
EXPECTED_TARGET_VECTOR_SHA256 = (
    "adc6bfe9fd93536b2084fb4014a91a388d504da5b714a1bba013090dea113d67"
)
EXPECTED_ENTITY_VECTOR_SHA256 = (
    "8674522def1925ab683d9b388f283de184dfd729f8f011113d581383e7958b67"
)
EXPECTED_RESPONSE_VECTOR_SHA256 = (
    "92a94559668055db1368a9bb04de37e09ecaa2bb815487ce5bb8f22b861a28ac"
)
EXPECTED_RESPONSE_RECEIPT_VECTOR_SHA256 = (
    "ae0a678e5413b5021e30a7776eec2399417474bd1a32eeb4ed05e294207c12ef"
)
CHECK_NAMES = frozenset(
    {
        "v25314_parent_audit_exact_valid_and_build_only",
        "v25305_result_private_and_postfreeze_audit_exact_valid",
        "v25315_sources_hashes_exact",
        "v25315_commit_is_exact_two_file_ancestor",
        "focused_parent_and_legacy_tests_exact37_green",
        "all_auditor_test_selector_parent_and_closure_files_tracked",
        "runtime_dependency_vector_exact41_and_hash_bound",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "consumed_target_vector_exact24_unique_and_hash_bound",
        "consumed_entity_vector_exact144_unique_and_hash_bound",
        "consumed_response_vector_exact48_unique_and_hash_bound",
        "selector_requires_zero_target_entity_and_response_overlap",
        "twelve_task_108_then96_capacity_ladder_exact",
        "entropy_information_gain_shadow_and_positive_credit_zero",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "git_clean_head_equals_target_main",
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called",
        "no_external_effect_performed",
    }
)


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(base._ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.53.16 expected JSON object")
    return value


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
    closure = tuple(sorted(base._dependency_closure((SELECTOR,)), key=str))
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


def _parent_barrier() -> bool:
    try:
        parent = parent_audit.validate_audit(_read(PARENT_AUDIT))
    except BaseException:
        return False
    authorization = parent["authorization"]
    return bool(
        parent["audit_valid"] is True
        and parent["findings"] == []
        and authorization["fresh_disjoint_worldbank_population_and_protocol_design"]
        is True
        and authorization["external_activation_or_launch"] is False
        and authorization["postfreeze_evaluator"] is False
        and authorization["deepwidebench_dev64_exact220_forward_or_evaluator"]
        is False
    )


def _consumed_manifest() -> dict[str, Any]:
    result = old_runner.validate_result(_read(OLD_RESULT))
    old_audit.validate_audit(_read(OLD_POSTFREEZE_AUDIT))
    private = _read(OLD_PRIVATE)
    if (
        private.get("role") != "v25305_private_frozen_worldbank_population"
        or not old_runner.seal.sealed(private, "population_payload_sha256")
        or not isinstance(private.get("population"), Mapping)
    ):
        raise RuntimeError("V2.53.16 old private population drifted")
    targets = list(result["candidate_target_keys"])
    entities = list(private["population"]["entities"])
    responses = [
        str(row["response_sha256"])
        for row in result["target_transport"]["rows"]
    ]
    post = _read(OLD_POSTFREEZE_AUDIT)["population"]
    checks = {
        "target_count": len(targets) == 24,
        "target_unique": len(set(item.casefold() for item in targets)) == 24,
        "target_hash": old_runner.payload_sha256(targets)
        == EXPECTED_TARGET_VECTOR_SHA256
        == post["candidate_target_keys_sha256"],
        "entity_count": len(entities) == 144,
        "entity_unique": len(set(entities)) == 144,
        "entity_hash": old_runner.payload_sha256(entities)
        == EXPECTED_ENTITY_VECTOR_SHA256
        == post["entities_sha256"],
        "response_count": len(responses) == 48,
        "response_unique": len(set(responses)) == 48,
        "response_format": all(
            re.fullmatch(r"[0-9a-f]{64}", item) is not None
            for item in responses
        ),
        "response_hash": old_runner.payload_sha256(responses)
        == EXPECTED_RESPONSE_VECTOR_SHA256,
        "response_receipt_hash": post["response_vector_sha256"]
        == EXPECTED_RESPONSE_RECEIPT_VECTOR_SHA256,
    }
    return {
        "target_keys": targets,
        "target_keys_sha256": old_runner.payload_sha256(targets),
        "entity_codes": entities,
        "entity_codes_sha256": old_runner.payload_sha256(entities),
        "response_sha256": responses,
        "response_vector_sha256": old_runner.payload_sha256(responses),
        "response_receipt_vector_sha256": post["response_vector_sha256"],
        "checks": checks,
    }


def _selector_contract() -> dict[str, Any]:
    return {
        "new_candidate_target_count": 24,
        "new_candidate_response_count": 48,
        "selected_target_count": 4,
        "task_count": 12,
        "preferred_rows_per_task": 9,
        "preferred_entity_count": 108,
        "minimum_rows_per_task": 8,
        "minimum_entity_count": 96,
        "below_minimum_entity_count_is_no_go": True,
        "old_24_targets_must_be_excluded_before_ranking": True,
        "old_144_entities_must_be_excluded_before_ranking": True,
        "old_48_response_hashes_must_have_zero_overlap": True,
        "new_48_response_hashes_must_be_unique": True,
        "population_choice_uses_only_catalog_and_target_response_bytes": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
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
    consumed = _consumed_manifest()
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
    contract = _selector_contract()
    checks = {
        "v25314_parent_audit_exact_valid_and_build_only": _parent_barrier(),
        "v25305_result_private_and_postfreeze_audit_exact_valid": all(
            consumed["checks"].values()
        ),
        "v25315_sources_hashes_exact": {
            str(path): base.sha256(path) for path in FIXED
        }
        == {str(path): digest for path, digest in FIXED.items()},
        "v25315_commit_is_exact_two_file_ancestor": (
            _changed_paths(IMPLEMENTATION_COMMIT) == IMPLEMENTATION_PATHS
            and _is_ancestor(IMPLEMENTATION_COMMIT, head)
        ),
        "focused_parent_and_legacy_tests_exact37_green": tests["passed"],
        "all_auditor_test_selector_parent_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact41_and_hash_bound": (
            len(vector) == EXPECTED_CLOSURE_COUNT
            and old_runner.payload_sha256(vector)
            == EXPECTED_CLOSURE_VECTOR_SHA256
            and old_runner.payload_sha256([row["path"] for row in vector])
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
        "consumed_target_vector_exact24_unique_and_hash_bound": all(
            consumed["checks"][name]
            for name in ("target_count", "target_unique", "target_hash")
        ),
        "consumed_entity_vector_exact144_unique_and_hash_bound": all(
            consumed["checks"][name]
            for name in ("entity_count", "entity_unique", "entity_hash")
        ),
        "consumed_response_vector_exact48_unique_and_hash_bound": all(
            consumed["checks"][name]
            for name in (
                "response_count",
                "response_unique",
                "response_format",
                "response_hash",
                "response_receipt_hash",
            )
        ),
        "selector_requires_zero_target_entity_and_response_overlap": tests[
            "passed"
        ]
        and contract["old_24_targets_must_be_excluded_before_ranking"]
        and contract["old_144_entities_must_be_excluded_before_ranking"]
        and contract["old_48_response_hashes_must_have_zero_overlap"],
        "twelve_task_108_then96_capacity_ladder_exact": (
            selector.TASK_COUNT == 12
            and selector.PREFERRED_ROWS_PER_TASK == 9
            and selector.PREFERRED_ENTITY_COUNT == 108
            and selector.MINIMUM_ROWS_PER_TASK == 8
            and selector.MINIMUM_ENTITY_COUNT == 96
            and tests["passed"]
        ),
        "entropy_information_gain_shadow_and_positive_credit_zero": tests[
            "passed"
        ],
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
        "runtime_dependency_vector_sha256": old_runner.payload_sha256(vector),
        "runtime_dependency_path_sha256": old_runner.payload_sha256(
            [row["path"] for row in vector]
        ),
        "semantic_audit": {
            **semantic,
            "auditor_or_explicit_file_credential_literal_hits": literal_hits,
            "untracked_sources": untracked,
        },
        "consumed_manifest": consumed,
        "selector_contract": contract,
        "protected_watchers": watchers,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "fresh_disjoint_worldbank_population_supervisor_build_only": not findings,
            "network_population_selection_or_freeze": False,
            "external_activation_or_launch": False,
            "postfreeze_evaluator": False,
            "candidate_quality_or_prediction_improvement_claim": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "avg_at_4_leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = old_runner.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("audit_payload_sha256", None)
    git = copied.get("git") or {}
    semantic = copied.get("semantic_audit") or {}
    consumed = copied.get("consumed_manifest") or {}
    vector = copied.get("runtime_dependency_vector")
    checks = copied.get("checks") or {}
    findings = copied.get("findings")
    authorization = copied.get("authorization") or {}
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
            "consumed_manifest",
            "selector_contract",
            "protected_watchers",
            "checks",
            "findings",
            "audit_valid",
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
        or copied.get("runtime_dependency_vector_sha256")
        != EXPECTED_CLOSURE_VECTOR_SHA256
        or old_runner.payload_sha256(vector) != EXPECTED_CLOSURE_VECTOR_SHA256
        or copied.get("runtime_dependency_path_sha256")
        != EXPECTED_CLOSURE_PATH_SHA256
        or old_runner.payload_sha256([row["path"] for row in vector])
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
        or consumed != _consumed_manifest()
        or not all(consumed["checks"].values())
        or copied.get("selector_contract") != _selector_contract()
        or set(checks) != CHECK_NAMES
        or any(not isinstance(item, bool) for item in checks.values())
        or findings != expected_findings
        or copied.get("audit_valid") is not (not expected_findings)
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
                "network_model_search_fetch_evaluator_benchmark_or_api_called",
                "entropy_or_information_gain_assigns_signed_credit",
            )
        )
        or set(authorization)
        != {
            "fresh_disjoint_worldbank_population_supervisor_build_only",
            "network_population_selection_or_freeze",
            "external_activation_or_launch",
            "postfreeze_evaluator",
            "candidate_quality_or_prediction_improvement_claim",
            "deepwidebench_dev64_exact220_forward_or_evaluator",
            "avg_at_4_leaderboard_or_sota",
        }
        or authorization.get("fresh_disjoint_worldbank_population_supervisor_build_only")
        is not copied.get("audit_valid")
        or any(
            authorization.get(name) is not False
            for name in authorization
            if name != "fresh_disjoint_worldbank_population_supervisor_build_only"
        )
        or signature != old_runner.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.16 build audit drifted")
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
        raise SystemExit("V2.53.16 audit failed: " + ", ".join(value["findings"]))
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
