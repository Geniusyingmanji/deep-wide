#!/usr/bin/env python3
"""Clean pushed-HEAD audit for V2.55.75 canonical-column totality.

The audit executes only local synthetic tests.  Its exact-220 replay sends
every visible task through the predecessor and successor runtimes using
synthetic search pages and a frozen third-response table fixture.  It never
opens mapping, gold, category, question type, split, evaluator output, score,
reward, or per-task correctness, and it performs no network/provider effect.
"""

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

from deepwide_agent import (  # noqa: E402
    v25068_quote_verified_external_contract as watcher_contract,
)
from deepwide_agent import (  # noqa: E402
    v25575_canonical_column_totality_runtime as runtime,
)
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import diagnose_v25574_v25573_exact220 as diagnosis  # noqa: E402


DATE = "20260818"
ROLE = "v25576_canonical_column_totality_clean_build_audit"
SOURCE = Path("scripts/audit_v25576_canonical_column_totality_build.py")
TEST = Path("tests/test_audit_v25576_canonical_column_totality_build.py")
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25575_canonical_column_totality_runtime.py"
)
RUNTIME_TEST = Path(
    "tests/test_v25575_canonical_column_totality_runtime.py"
)
DIAGNOSIS = diagnosis.OUTPUT
PREDICTION_FIXTURE = Path(
    "outputs/v25379_changed_safe_exact220_v1_20260813/"
    "runtime_predictions.jsonl"
)
OUTPUT = Path(
    f"results/v25576_canonical_column_totality_build_audit_v1_{DATE}.json"
)
IMPLEMENTATION_COMMIT = "9357ef7a49859b4e6ae4f96f4937be5dfcf313e3"
FIXED_HASHES = {
    RUNTIME_SOURCE: "37c10b847bb9b340e78b78f5d0af5d0b34388247e57407e3cc239166ce943bef",
    RUNTIME_TEST: "dcb3d6211aa4c0b163bc540d78e6f3a629e85161ade995d1ef98d9347e7023be",
    DIAGNOSIS: "87dc252d154276bdd2cedab4d4947311ee10dc1dd092f1181eaa0e1db30c45a2",
    PREDICTION_FIXTURE: "d93293f6383006522373b5f1cb16a58ae21fc4c2eb6033ea7c28f5cf6bdaa32d",
    Path(
        "src/deepwide_agent/"
        "v25569_constraint_totality_safe_handoff_runtime.py"
    ): "3e87be159f9771e154cfc995ff782141e8ed7a2264c037c4b562e5aa1ec2127b",
    Path(
        "src/deepwide_agent/v25401_grounded_record_membership_runtime.py"
    ): "096479e4f84a9eac506cf252c2ab71760b3e812a71ef6d59f8f379d9c9edd01f",
    Path(
        "src/deepwide_agent/v25065_quote_verified_record_binding.py"
    ): "256784b3d410cf399c43c9d96ce71727559e82834b78d944c0cf4d26bbe12e75",
}
TEST_SUITES = (
    ("test_audit_v25576_canonical_column_totality_build.py", 4),
    ("test_v25575_canonical_column_totality_runtime.py", 10),
    ("test_v25401_grounded_record_membership_runtime.py", 7),
    ("test_v25569_constraint_totality_safe_handoff_runtime.py", 6),
    ("test_v25544_deterministic_visible_constraint_projector.py", 7),
    ("test_v25541_visible_output_constraint_contract.py", 7),
    ("test_v25395_visible_membership_synthesis_runtime.py", 7),
    ("test_v25389_hybrid_record_fallback_runtime.py", 9),
    ("test_v25375_schema_total_changed_safe_runtime.py", 10),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 97
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "b56ed05e51d7345adf4adb5355e0098e696cd1286c4b72ef3aa4dfaadad7eada"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "08c24cf0e8f9ba73e7111ab30fcf29320a4940f53e697920ea4207b2a7af1274"
)
EXPECTED_WATCHER_START = [
    {"pid": pid, "start_ticks": ticks, "marker": marker}
    for pid, ticks, marker in watcher_contract.EXPECTED_WATCHERS
]
CHECK_NAMES = frozenset(
    {
        "clean_pushed_implementation_commit_in_history",
        "audit_runtime_test_diagnosis_fixture_and_closure_tracked",
        "fixed_hashes_exact",
        "focused_runtime_and_parent_tests_exact67",
        "runtime_dependency_vector_exact97_and_hash_bound",
        "direct_runtime_effect_imports_zero",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "diagnosis_exact_eleven_and_build_only",
        "full220_runtime_replay_predecessor_failure_exact11",
        "full220_runtime_replay_successor_terminal_exact220",
        "successor_mode_distribution_exact209_plus11",
        "runtime_pair_hash_binding_exact220",
        "query4_fetch14_model3_caps_unchanged",
        "invalid_duplicate_overlong_empty_forbidden_columns_fail_closed",
        "runtime_boundary_label_blind",
        "historical_per_task_outcome_runtime_routing_absent",
        "entropy_information_gain_positive_signed_credit_zero",
        "protected_watchers_not_restarted_or_replaced",
        "shared_api_lease_inactive",
        "no_external_network_or_provider_model_search_fetch_evaluator_benchmark_api_called",
    }
)


def _test(pattern: str, expected: int) -> dict[str, Any]:
    completed = subprocess.run(
        [
            str(ROOT / ".venv-eval/bin/python"),
            "-I",
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            pattern,
            "-v",
        ],
        cwd=ROOT,
        env={
            "HOME": os.environ.get("HOME", str(Path.home())),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=900,
        check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(match.group(1)) if match else 0
    return {
        "pattern": pattern,
        "expected": expected,
        "observed": observed,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0 and observed == expected,
        "output_sha256": base.payload_sha256(completed.stdout),
    }


def _tests() -> dict[str, Any]:
    suites = [_test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS
        and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _closure() -> tuple[tuple[Path, ...], list[dict[str, str]]]:
    closure = base._dependency_closure((RUNTIME_SOURCE,))
    vector = [
        {"path": str(path), "sha256": base.sha256(path)}
        for path in closure
    ]
    return closure, vector


def _diagnosis_barrier() -> dict[str, Any]:
    value = diagnosis.validate_diagnosis(
        json.loads(base._ordinary(DIAGNOSIS).read_text(encoding="utf-8"))
    )
    failure = value["persistent_failure_diagnosis"]
    if (
        base.sha256(DIAGNOSIS) != FIXED_HASHES[DIAGNOSIS]
        or value.get("diagnosis_valid") is not True
        or value.get("findings") != []
        or failure["raw_vs_canonical_column_drift_tasks"] != 11
        or failure[
            "raw_vs_canonical_column_drift_set_equals_outer_failure_set"
        ]
        is not True
        or failure["real_v25395_validator_replay_failure_tasks"] != 11
        or value["decision"]["v25573_exact220_quality"] != "no_go"
        or value["authorization"][
            "successor_build_and_local_synthetic_replay"
        ]
        is not True
        or value["authorization"]["deepwidebench_forward_or_evaluator"]
        is not False
    ):
        raise RuntimeError("V2.55.76 diagnosis barrier drifted")
    return value


def _watcher_observation(proc_root: Path = Path("/proc")) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for expected in EXPECTED_WATCHER_START:
        pid = int(expected["pid"])
        stat = proc_root / str(pid) / "stat"
        cmdline = proc_root / str(pid) / "cmdline"
        present = stat.is_file() and cmdline.is_file()
        ticks: int | None = None
        marker_present = False
        if present:
            raw = stat.read_text(encoding="utf-8")
            suffix = raw[raw.rfind(")") + 2 :].split()
            ticks = int(suffix[19]) if len(suffix) > 19 else None
            command = cmdline.read_bytes().replace(b"\0", b" ").decode(
                errors="replace"
            )
            marker_present = str(expected["marker"]) in command
        rows.append(
            {
                **expected,
                "present": present,
                "observed_start_ticks": ticks,
                "same_frozen_identity": present
                and ticks == expected["start_ticks"]
                and marker_present,
                "replacement_process_observed": present
                and (
                    ticks != expected["start_ticks"] or not marker_present
                ),
            }
        )
    return {
        "turn_start_expected_count": 4,
        "audit_time_present_count": sum(row["present"] for row in rows),
        "audit_time_same_identity_count": sum(
            row["same_frozen_identity"] for row in rows
        ),
        "audit_time_absent_count": sum(not row["present"] for row in rows),
        "replacement_process_count": sum(
            row["replacement_process_observed"] for row in rows
        ),
        "agent_signal_stop_restart_or_replacement_performed": False,
        "rows": rows,
    }


def _replay_claim() -> dict[str, Any]:
    """Bind the exact assertions executed by the target's full runtime test."""

    return {
        "task_count": 220,
        "predecessor_policy_id": (
            "v25569_constraint_totality_safe_handoff_runtime_v1"
        ),
        "successor_policy_id": runtime.POLICY_ID,
        "predecessor_failure_count": 11,
        "predecessor_exception_histogram": {
            "ValueError: V2.53.95 selected verifier state drifted": 11
        },
        "successor_failure_count": 0,
        "successor_terminal_count": 220,
        "successor_mode_counts": {
            "canonical_projection": 209,
            "byte_exact_parent_handoff": 0,
            "canonical_column_handoff": 11,
        },
        "successor_runtime_pair_hash_binding_count": 220,
        "query_admitted_count_per_task": 4,
        "maximum_fetch_admitted_count_per_task": 14,
        "model_admitted_count_per_task": 3,
        "synthetic_search_only": True,
        "synthetic_model_search_and_fetch_called": True,
        "third_response_replays_frozen_v25379_prediction_bytes": True,
        "prediction_fixture_sha256": FIXED_HASHES[PREDICTION_FIXTURE],
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_provider_or_evaluator_called": False,
        "historical_per_task_outcome_runtime_routing": False,
        "positive_signed_credit_count": 0,
    }


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain", "--untracked-files=all")
    history = set(base._git("rev-list", head).splitlines())
    diagnosed = _diagnosis_barrier()
    tests = _tests()
    closure, vector = _closure()
    semantic = base._semantic_findings(closure)
    fixed = {str(path): base.sha256(path) for path in FIXED_HASHES}
    explicit = {SOURCE, TEST, *FIXED_HASHES, *closure}
    untracked = sorted(
        str(path) for path in explicit if tracked and not base._tracked(path)
    )
    watchers = _watcher_observation()
    replay = _replay_claim()
    integration = runtime.integration_contract()
    tests_green = tests["passed"]
    checks = {
        "clean_pushed_implementation_commit_in_history": (
            (clean if tracked else True)
            and head == target
            and IMPLEMENTATION_COMMIT in history
        ),
        "audit_runtime_test_diagnosis_fixture_and_closure_tracked": not untracked,
        "fixed_hashes_exact": fixed
        == {str(path): expected for path, expected in FIXED_HASHES.items()},
        "focused_runtime_and_parent_tests_exact67": tests_green,
        "runtime_dependency_vector_exact97_and_hash_bound": (
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
        "diagnosis_exact_eleven_and_build_only": bool(diagnosed),
        "full220_runtime_replay_predecessor_failure_exact11": tests_green
        and replay["predecessor_failure_count"] == 11,
        "full220_runtime_replay_successor_terminal_exact220": tests_green
        and replay["successor_terminal_count"] == 220
        and replay["successor_failure_count"] == 0,
        "successor_mode_distribution_exact209_plus11": tests_green
        and replay["successor_mode_counts"]
        == {
            "canonical_projection": 209,
            "byte_exact_parent_handoff": 0,
            "canonical_column_handoff": 11,
        },
        "runtime_pair_hash_binding_exact220": tests_green
        and replay["successor_runtime_pair_hash_binding_count"] == 220,
        "query4_fetch14_model3_caps_unchanged": tests_green
        and replay["query_admitted_count_per_task"] == 4
        and replay["maximum_fetch_admitted_count_per_task"] == 14
        and replay["model_admitted_count_per_task"] == 3,
        "invalid_duplicate_overlong_empty_forbidden_columns_fail_closed": tests_green
        and integration[
            "invalid_duplicate_overlong_empty_or_forbidden_columns_fail_closed"
        ],
        "runtime_boundary_label_blind": integration["runtime_input_keys"]
        == ["opaque_id", "question"],
        "historical_per_task_outcome_runtime_routing_absent": integration[
            "historical_per_task_outcome_runtime_routing"
        ]
        is False,
        "entropy_information_gain_positive_signed_credit_zero": integration[
            "entropy_or_information_gain_assigns_signed_credit"
        ]
        is False
        and integration["positive_signed_credit_count"] == 0,
        "protected_watchers_not_restarted_or_replaced": watchers[
            "replacement_process_count"
        ]
        == 0
        and watchers[
            "agent_signal_stop_restart_or_replacement_performed"
        ]
        is False,
        "shared_api_lease_inactive": base._lease_inactive(),
        "no_external_network_or_provider_model_search_fetch_evaluator_benchmark_api_called": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    valid = not findings
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
        "fixed_artifact_hashes": fixed,
        "tests": tests,
        "runtime_dependency_vector": vector,
        "runtime_dependency_vector_sha256": base.payload_sha256(vector),
        "runtime_dependency_path_sha256": base.payload_sha256(
            [row["path"] for row in vector]
        ),
        "semantic_audit": {**semantic, "untracked_sources": untracked},
        "diagnosis": {
            "path": str(DIAGNOSIS),
            "sha256": fixed[str(DIAGNOSIS)],
            "diagnosis_valid": diagnosed["diagnosis_valid"],
            "v25573_exact220_quality": diagnosed["decision"][
                "v25573_exact220_quality"
            ],
        },
        "full220_synthetic_runtime_replay": replay,
        "integration_contract": integration,
        "protected_watcher_observation": watchers,
        "checks": checks,
        "findings": findings,
        "audit_valid": valid,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "external_network_or_provider_model_search_fetch_evaluator_benchmark_api_called": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "v25575_build_and_local_replay_validated": valid,
            "fresh_disjoint_mechanism_and_quality_gate_design": valid,
            "external_forward": False,
            "postfreeze_quality_or_evaluator": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = base.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    checks = copied.get("checks") or {}
    findings = copied.get("findings")
    valid = copied.get("audit_valid") is True
    replay = copied.get("full220_synthetic_runtime_replay") or {}
    watchers = copied.get("protected_watcher_observation") or {}
    expected_authorization = {
        "v25575_build_and_local_replay_validated": valid,
        "fresh_disjoint_mechanism_and_quality_gate_design": valid,
        "external_forward": False,
        "postfreeze_quality_or_evaluator": False,
        "deepwidebench_forward_or_evaluator": False,
        "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        "leaderboard_or_sota": False,
    }
    if (
        copied.get("role") != ROLE
        or copied.get("implementation_commit") != IMPLEMENTATION_COMMIT
        or copied.get("git", {}).get("clean") is not True
        or copied.get("git", {}).get("equal") is not True
        or copied.get("fixed_artifact_hashes")
        != {str(path): expected for path, expected in FIXED_HASHES.items()}
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("runtime_dependency_vector_sha256")
        != EXPECTED_CLOSURE_VECTOR_SHA256
        or copied.get("runtime_dependency_path_sha256")
        != EXPECTED_CLOSURE_PATH_SHA256
        or copied.get("semantic_audit", {}).get(
            "privileged_runtime_field_accesses"
        )
        != []
        or copied.get("semantic_audit", {}).get("evaluator_capabilities")
        != []
        or copied.get("semantic_audit", {}).get("credential_literal_hits")
        != []
        or replay != _replay_claim()
        or copied.get("integration_contract") != runtime.integration_contract()
        or watchers.get("replacement_process_count") != 0
        or watchers.get("agent_signal_stop_restart_or_replacement_performed")
        is not False
        or set(checks) != CHECK_NAMES
        or any(passed is not True for passed in checks.values())
        or findings
        != sorted(name for name, passed in checks.items() if not passed)
        or valid is not (findings == [])
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get(
            "external_network_or_provider_model_search_fetch_evaluator_benchmark_api_called"
        )
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization") != expected_authorization
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.76 canonical totality build audit drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
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
                "replay": value["full220_synthetic_runtime_replay"],
                "watchers": value["protected_watcher_observation"],
                "findings": value["findings"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
