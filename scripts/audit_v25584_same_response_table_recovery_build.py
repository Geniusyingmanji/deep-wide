#!/usr/bin/env python3
"""Clean pushed-HEAD build audit for V2.55.83 table recovery.

The audit executes repository-only unit tests and static dependency checks.
It calls no model, search, fetch, network, evaluator, benchmark, mapping, or
truth surface and authorizes only local synthetic integration work plus design
of a future task-disjoint external gate.
"""

from __future__ import annotations

import argparse
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

from deepwide_agent import v25583_same_response_table_recovery as runtime  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import diagnose_v25582_v25581_exact220 as diagnosis  # noqa: E402


DATE = "20260818"
ROLE = "v25584_same_response_table_recovery_clean_build_audit"
SOURCE = Path("scripts/audit_v25584_same_response_table_recovery_build.py")
TEST = Path("tests/test_audit_v25584_same_response_table_recovery_build.py")
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25583_same_response_table_recovery.py"
)
RUNTIME_TEST = Path("tests/test_v25583_same_response_table_recovery.py")
DIAGNOSIS = diagnosis.OUTPUT
OUTPUT = Path(
    f"results/v25584_same_response_table_recovery_build_audit_v1_{DATE}.json"
)
IMPLEMENTATION_COMMIT = "8d5a647d15a6303e77312953d82b6fdbc5d5fda9"
FIXED_HASHES = {
    RUNTIME_SOURCE: "836dca51e5bbffcdaa4d8480de699211a3252ec5c944afa62746b9aee1dee4d9",
    RUNTIME_TEST: "e2fb2ad52614df4e1a3996e511bf51a475b974d9053fe64e0b5e6f61798127e5",
    DIAGNOSIS: "bc99b914f09b0de333a247d2ce6ab89f0492d5878ca2dc25901abe7d8f0020f4",
}
TEST_SUITES = (
    ("test_audit_v25584_same_response_table_recovery_build.py", 4),
    ("test_v25583_same_response_table_recovery.py", 9),
    ("test_v24986_robust_paired_runtime.py", 5),
    ("test_v24259_deterministic_table_normalizer.py", 11),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
EXPECTED_CLOSURE_COUNT = 45
EXPECTED_CLOSURE_VECTOR_SHA256 = (
    "7cb1993daf0f337af7d951695d02848808199f7c286fb38a9c118096583467e4"
)
EXPECTED_CLOSURE_PATH_SHA256 = (
    "a44a219b9d82efd716f4fb8829402acc5e4e009535265e66610293764aa27fc6"
)
CHECK_NAMES = frozenset(
    {
        "clean_pushed_implementation_commit_in_history",
        "audit_runtime_test_diagnosis_and_closure_tracked",
        "fixed_hashes_exact",
        "focused_recovery_and_parent_tests_exact29",
        "runtime_dependency_vector_exact45_and_hash_bound",
        "direct_runtime_effect_imports_zero",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "only_known_provider_rank_score_exception",
        "v25582_diagnosis_valid_and_design_only",
        "frozen_parent_always_runs_first",
        "same_response_zero_extra_effect_only",
        "strict_parser_modes_and_caps_bound",
        "all_rows_and_nonempty_cells_fail_closed",
        "membership_row_or_fact_inference_absent",
        "historical_per_task_outcome_runtime_routing_absent",
        "entropy_information_gain_positive_signed_credit_zero",
        "protected_watcher_not_restarted_or_replaced",
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
        timeout=300,
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
    fallback = value["fallback_diagnosis"]
    decision = value["decision"]
    authorization = value["authorization"]
    if (
        base.sha256(DIAGNOSIS) != FIXED_HASHES[DIAGNOSIS]
        or value.get("diagnosis_valid") is not True
        or value.get("findings") != []
        or fallback["failure_taxonomy"]
        != {
            "local_unrecoverable_table_normalization": 6,
            "plan_and_synthesis_model_request_error": 1,
            "synthesis_model_request_error": 3,
        }
        or fallback["joint_envelope_exact_tasks"] != 6
        or fallback["joint_table_normalizable_tasks"] != 0
        or decision["candidate_designs_for_fresh_task_disjoint_gate"][0]
        != "same_response_zero_extra_effect_robust_table_recovery"
        or authorization["fresh_task_disjoint_external_gate_design"] is not True
        or authorization["external_forward"] is not False
        or authorization["deepwidebench_forward_or_evaluator"] is not False
    ):
        raise RuntimeError("V2.55.84 diagnosis barrier drifted")
    return value


def _watcher_observation(proc_root: Path = Path("/proc")) -> dict[str, Any]:
    pid = 2808901
    expected_ticks = 746680268
    marker = "scripts/watch_v24215_joint_package_recovery.py"
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
        marker_present = marker in command
    replacement = present and (ticks != expected_ticks or not marker_present)
    return {
        "pid": pid,
        "expected_start_ticks": expected_ticks,
        "marker": marker,
        "present": present,
        "observed_start_ticks": ticks,
        "same_frozen_identity": present
        and ticks == expected_ticks
        and marker_present,
        "replacement_process_observed": replacement,
        "agent_signal_stop_restart_or_replacement_performed": False,
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
    integration = runtime.integration_contract()
    checks = {
        "clean_pushed_implementation_commit_in_history": (
            (clean if tracked else True)
            and head == target
            and IMPLEMENTATION_COMMIT in history
        ),
        "audit_runtime_test_diagnosis_and_closure_tracked": not untracked,
        "fixed_hashes_exact": fixed
        == {str(path): expected for path, expected in FIXED_HASHES.items()},
        "focused_recovery_and_parent_tests_exact29": tests["passed"],
        "runtime_dependency_vector_exact45_and_hash_bound": (
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
        "v25582_diagnosis_valid_and_design_only": diagnosed[
            "diagnosis_valid"
        ]
        is True,
        "frozen_parent_always_runs_first": integration[
            "frozen_parent_always_runs_first"
        ],
        "same_response_zero_extra_effect_only": integration[
            "same_response_bytes_only"
        ]
        and integration[
            "additional_model_search_fetch_token_context_wall_or_network_budget"
        ]
        is False,
        "strict_parser_modes_and_caps_bound": (
            integration["recovery_modes"] == sorted(runtime.RECOVERY_MODES)
            and integration["maximum_recovery_input_characters"] == 120_000
            and integration["maximum_rows"] == 512
            and integration["maximum_columns"] == 20
            and integration["maximum_cell_characters"] == 2_000
        ),
        "all_rows_and_nonempty_cells_fail_closed": integration[
            "all_rows_must_survive_in_order"
        ]
        and integration["required_header_mapping_must_be_injective"],
        "membership_row_or_fact_inference_absent": integration[
            "nonempty_fact_inference_or_page_completion"
        ]
        is False
        and integration["membership_inference_or_row_creation"] is False,
        "historical_per_task_outcome_runtime_routing_absent": integration[
            "historical_per_task_outcome_runtime_routing"
        ]
        is False,
        "entropy_information_gain_positive_signed_credit_zero": integration[
            "entropy_or_information_gain_assigns_signed_credit"
        ]
        is False
        and integration["positive_signed_credit_count"] == 0,
        "protected_watcher_not_restarted_or_replaced": watchers[
            "same_frozen_identity"
        ]
        and watchers["replacement_process_observed"] is False
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
            "same_response_local_failure_tasks": diagnosed[
                "fallback_diagnosis"
            ]["joint_envelope_exact_tasks"],
            "external_or_benchmark_authorized": False,
        },
        "integration_contract": integration,
        "protected_watcher_observation": watchers,
        "checks": checks,
        "findings": findings,
        "audit_valid": valid,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "external_network_or_provider_model_search_fetch_evaluator_benchmark_api_called": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "v25583_local_primitive_and_synthetic_integration": valid,
            "fresh_task_disjoint_population_and_gate_design": valid,
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
    watchers = copied.get("protected_watcher_observation") or {}
    expected_authorization = {
        "v25583_local_primitive_and_synthetic_integration": valid,
        "fresh_task_disjoint_population_and_gate_design": valid,
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
        or copied.get("semantic_audit", {}).get("evaluator_capabilities") != []
        or copied.get("semantic_audit", {}).get("credential_literal_hits") != []
        or copied.get("integration_contract") != runtime.integration_contract()
        or watchers.get("same_frozen_identity") is not True
        or watchers.get("replacement_process_observed") is not False
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
        raise ValueError("V2.55.84 table recovery build audit drifted")
    return copied


def _publish(value: Mapping[str, Any]) -> None:
    path = ROOT / OUTPUT
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.validate_only:
        value = validate_audit(
            json.loads(
                base._ordinary(OUTPUT).read_text(encoding="utf-8")
            )
        )
    else:
        value = build_audit()
        _publish(value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "tests": value["tests"]["observed"],
                "closure": len(value["runtime_dependency_vector"]),
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
