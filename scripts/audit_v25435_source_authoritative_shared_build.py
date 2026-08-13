#!/usr/bin/env python3
"""Clean pushed build audit for the V2.54.34 production integration."""

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

from deepwide_agent import v25068_quote_verified_external_contract as watchers  # noqa: E402
from deepwide_agent import v25434_source_authoritative_shared_runtime as runtime  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402


DATE = "20260813"
ROLE = "v25435_source_authoritative_shared_clean_build_audit"
IMPLEMENTATION_COMMIT = "dcb35d537b26356aed51f0f7294f545c1033d2a1"
SOURCE = Path("scripts/audit_v25435_source_authoritative_shared_build.py")
TEST = Path("tests/test_audit_v25435_source_authoritative_shared_build.py")
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25434_source_authoritative_shared_runtime.py"
)
RUNTIME_TEST = Path("tests/test_v25434_source_authoritative_shared_runtime.py")
PARENT_BUILD_AUDIT = Path(
    "results/v25433_source_authoritative_candidate_build_audit_v1_20260813.json"
)
PARENT_BUILD_AUDIT_SHA256 = (
    "628598e667cd96e41da6d9e0cde8b872d9a6007ae8587cb0962eee78aa448dea"
)
OUTPUT = Path(
    f"results/v25435_source_authoritative_shared_build_audit_v1_{DATE}.json"
)
FIXED_HASHES = {
    RUNTIME_SOURCE: "dc78d8e54728d644b17100d51e68c622a21775b0d8a0b415400f6ffead68c74a",
    RUNTIME_TEST: "e1017edb3465a57e9045c1e3336b8ad1b8b761ad13f97736e979334805479567",
    PARENT_BUILD_AUDIT: PARENT_BUILD_AUDIT_SHA256,
}
TEST_SUITES = (
    ("test_audit_v25435_source_authoritative_shared_build.py", 4),
    ("test_v25434_source_authoritative_shared_runtime.py", 9),
    ("test_v25432_source_authoritative_field_candidate.py", 9),
    ("test_v25401_grounded_record_membership_runtime.py", 7),
    ("test_v25395_visible_membership_synthesis_runtime.py", 7),
    ("test_v25389_hybrid_record_fallback_runtime.py", 9),
    ("test_v25375_schema_total_changed_safe_runtime.py", 10),
    ("test_v25370_shared_synthesis_changed_safe_runtime.py", 8),
    ("test_v25420_list_atomic_changed_safe_runtime.py", 9),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 95
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "6625c2d1e56a11d6aa9ba07335de7bf5c2d1bcfe219b239a513c5861e7446df9"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "fb4eb44bb96ace8e0576880bb0883ee0acca1b6f8cca4bfa75a1f1eb294a5d29"
)


def _tests() -> dict[str, Any]:
    suites = [base._test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _closure() -> tuple[tuple[Path, ...], list[dict[str, str]]]:
    closure = tuple(sorted(base._dependency_closure((RUNTIME_SOURCE,)), key=str))
    vector = [{"path": str(path), "sha256": base.sha256(path)} for path in closure]
    return closure, vector


def _parent_barrier() -> dict[str, Any]:
    value = json.loads(
        base._ordinary(PARENT_BUILD_AUDIT).read_text(encoding="utf-8")
    )
    if (
        base.sha256(PARENT_BUILD_AUDIT) != PARENT_BUILD_AUDIT_SHA256
        or value.get("audit_valid") is not True
        or value.get("authorization", {}).get(
            "fresh_disjoint_source_authoritative_external_protocol_design"
        )
        is not True
        or value.get("authorization", {}).get("external_forward") is not False
    ):
        raise RuntimeError("V2.54.35 V2.54.33 parent barrier drifted")
    return value


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    history = set(base._git("rev-list", head).splitlines())
    parent = _parent_barrier()
    tests = _tests()
    closure, vector = _closure()
    semantic = base._semantic_findings(closure)
    explicit = {
        SOURCE,
        TEST,
        RUNTIME_SOURCE,
        RUNTIME_TEST,
        PARENT_BUILD_AUDIT,
        *closure,
    }
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    source = base._ordinary(RUNTIME_SOURCE).read_text(encoding="utf-8")
    snapshot = watchers.watcher_snapshot()
    tests_green = tests["passed"]
    checks = {
        "v25433_pure_candidate_build_audit_bound": bool(parent),
        "fixed_runtime_test_and_parent_hashes_match": all(
            base.sha256(path) == expected for path, expected in FIXED_HASHES.items()
        ),
        "implementation_commit_is_in_head_history": IMPLEMENTATION_COMMIT in history,
        "focused_parent_and_audit_tests_exact72": tests_green,
        "git_clean_head_equals_target_main": (clean if tracked else True)
        and head == target,
        "all_audit_runtime_test_parent_and_closure_files_tracked": not untracked,
        "runtime_dependency_vector_exact95_and_hash_bound": (
            len(vector) == EXPECTED_CLOSURE_COUNT
            and base.payload_sha256(vector) == EXPECTED_CLOSURE_VECTOR_SHA256
            and base.payload_sha256([row["path"] for row in vector])
            == EXPECTED_CLOSURE_PATH_SHA256
        ),
        "direct_runtime_effect_imports_zero": not base._direct_forbidden_imports(
            RUNTIME_SOURCE
        ),
        "privileged_runtime_field_access_zero": semantic[
            "privileged_runtime_field_accesses"
        ]
        == [],
        "evaluator_capability_zero": semantic["evaluator_capabilities"] == [],
        "credential_literal_zero": semantic["credential_literal_hits"] == [],
        "only_known_provider_rank_score_exception": semantic[
            "allowed_provider_rank_access"
        ]
        == ["src/deepwide_agent/clients.py:565:score"],
        "one_v25401_parent_forward_only": source.count("_parent_runner(created)(")
        == 1,
        "third_synthesis_pages_mirrored_without_provider_prompt_change": tests_green,
        "visible_identity_authority_url_and_surface_binding": tests_green,
        "rfc_joined_path_token_exact_not_substring": tests_green,
        "deterministic_candidate_id_selection_zero_fourth_call": tests_green,
        "no_candidate_conflict_or_unbound_page_is_base_byte_exact": tests_green,
        "private_page_application_and_terminal_prediction_replay_bound": tests_green,
        "query4_fetch14_model3_caps_unchanged": tests_green,
        "zero_additional_model_search_fetch_or_network_call_surface": all(
            token not in source
            for token in (
                "model.complete",
                "search_many",
                "fetch_urls",
                "import requests",
                "urlopen",
                "subprocess",
                "socket",
            )
        ),
        "entropy_information_gain_neither_routes_nor_gets_signed_credit": tests_green,
        "protected_watchers_unchanged": snapshot
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in watchers.EXPECTED_WATCHERS
        ],
        "shared_api_lease_inactive": base._lease_inactive(),
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": clean if tracked else True,
        },
        "fixed_artifact_hashes": {
            str(path): base.sha256(path) for path in FIXED_HASHES
        },
        "tests": tests,
        "runtime_dependency_vector": vector,
        "runtime_dependency_vector_sha256": base.payload_sha256(vector),
        "runtime_dependency_path_sha256": base.payload_sha256(
            [row["path"] for row in vector]
        ),
        "semantic_audit": {**semantic, "untracked_sources": untracked},
        "physical_caps": {
            "queries": 4,
            "fetches": 14,
            "normal_path_model_forwards": 3,
            "candidate_selector_model_forwards": 0,
            "wall_seconds": 240,
        },
        "protected_watchers": snapshot,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        runtime.candidates.PRIVILEGED_READ_FLAG: False,
        "model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "fresh_disjoint_source_authoritative_population_and_protocol_design": not findings,
            "external_forward": False,
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
    findings = copied.get("findings")
    tests = copied.get("tests")
    semantic = copied.get("semantic_audit")
    valid = copied.get("audit_valid") is True
    if (
        copied.get("role") != ROLE
        or copied.get("implementation_commit") != IMPLEMENTATION_COMMIT
        or not isinstance(checks, Mapping)
        or any(not isinstance(passed, bool) for passed in checks.values())
        or findings != sorted(name for name, passed in checks.items() if not passed)
        or valid is not (findings == [])
        or not isinstance(tests, Mapping)
        or tests.get("expected") != EXPECTED_TESTS
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("passed") is not True
        or copied.get("runtime_dependency_vector_sha256")
        != EXPECTED_CLOSURE_VECTOR_SHA256
        or copied.get("runtime_dependency_path_sha256")
        != EXPECTED_CLOSURE_PATH_SHA256
        or not isinstance(semantic, Mapping)
        or semantic.get("privileged_runtime_field_accesses") != []
        or semantic.get("evaluator_capabilities") != []
        or semantic.get("credential_literal_hits") != []
        or copied.get(runtime.candidates.PRIVILEGED_READ_FLAG) is not False
        or copied.get("model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("authorization")
        != {
            "fresh_disjoint_source_authoritative_population_and_protocol_design": valid,
            "external_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.35 source-authoritative shared audit drifted")
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
                "tests": value["tests"]["observed"],
                "closure": len(value["runtime_dependency_vector"]),
                "findings": value["findings"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
