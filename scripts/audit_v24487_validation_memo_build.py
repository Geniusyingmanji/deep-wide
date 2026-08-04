#!/usr/bin/env python3
"""Build-only audit for V2.44.85--86 validation memoization."""

from __future__ import annotations

import json
import math
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

from deepwide_agent.v24320_forward_contract import (  # noqa: E402
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from scripts import audit_v24398_failure_observability_build as base  # noqa: E402
from scripts import v24484_separated_budget_external_gate as parent  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


DATE = "20260804"
AUDIT = Path(f"results/v24487_validation_memo_build_audit_v1_{DATE}.json")
PARENT_RESULT = parent.RESULT
PARENT_DECISION = parent.DECISION
PARENT_POSTAUDIT = parent.POSTAUDIT
SOURCES = (
    Path("src/deepwide_agent/v24485_execution_scoped_validation_memo.py"),
    Path("tests/test_v24485_execution_scoped_validation_memo.py"),
    Path("src/deepwide_agent/v24486_memoized_worker_integration.py"),
    Path("tests/test_v24486_memoized_worker_integration.py"),
    Path("scripts/audit_v24487_validation_memo_build.py"),
    Path("tests/test_audit_v24487_validation_memo_build.py"),
)
RUNTIME_SOURCES = (SOURCES[0], SOURCES[2])
FROZEN_PARENTS = (
    Path("src/deepwide_agent/v24457_adaptive_entropy_support.py"),
    Path("src/deepwide_agent/v24459_proof_carrying_adaptive_entropy_support.py"),
    Path("src/deepwide_agent/v24464_single_validation_adaptive_persistence.py"),
    Path("src/deepwide_agent/v24469_bounded_worker_supervisor.py"),
    Path("src/deepwide_agent/v24470_bounded_adaptive_integration.py"),
    Path("src/deepwide_agent/v24476_bounded_nominal_search_integration.py"),
    PARENT_RESULT,
    PARENT_DECISION,
    PARENT_POSTAUDIT,
)
TEST_SUITES = (
    (
        Path("tests/test_v24459_proof_carrying_adaptive_entropy_support.py"),
        5,
        120,
        "proof_certificate_control",
    ),
    (
        Path("tests/test_v24464_single_validation_adaptive_persistence.py"),
        5,
        360,
        "single_validation_control",
    ),
    (
        Path("tests/test_v24469_bounded_worker_supervisor.py"),
        11,
        120,
        "worker_supervision_fault_matrix",
    ),
    (
        Path("tests/test_v24485_execution_scoped_validation_memo.py"),
        7,
        120,
        "slow_fast_equivalence_and_attack_matrix",
    ),
    (
        Path("tests/test_v24486_memoized_worker_integration.py"),
        4,
        60,
        "fail_closed_worker_integration",
    ),
    (
        Path("tests/test_audit_v24487_validation_memo_build.py"),
        5,
        60,
        "audit_control",
    ),
)
EXPECTED_TEST_COUNT = 37
MEMO_SUITE_PATH = Path("tests/test_v24485_execution_scoped_validation_memo.py")
MEMO_SUITE_CEILING_SECONDS = 40.0
WORKER_SUITE_PATH = Path("tests/test_v24486_memoized_worker_integration.py")
WORKER_SUITE_CEILING_SECONDS = 10.0
EXPECTED_WATCHERS = base.EXPECTED_WATCHERS
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(base._ordinary(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.44.87 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _validate_parents() -> dict[str, Any]:
    result = parent.validate_public_result(_read(PARENT_RESULT))
    decision = parent.validate_decision(ROOT, value=_read(PARENT_DECISION))
    audit = parent.validate_postaudit(ROOT, value=_read(PARENT_POSTAUDIT))
    supervision = result.get("supervision_aggregate") or {}
    if (
        result.get("selected") != 8
        or result.get("passed") is not False
        or result.get("batch_wall_seconds") != 220.338439
        or supervision.get("worker_hard_timeout_tasks") != 8
        or supervision.get("complete_validation_entered_tasks") != 3
        or supervision.get("complete_validation_returned_tasks") != 0
        or supervision.get("model_effect_started_lower_bound") != 17
        or supervision.get("model_effect_finished_lower_bound") != 17
        or supervision.get("hosted_search_effect_started_lower_bound") != 24
        or supervision.get("hosted_search_effect_finished_lower_bound") != 24
        or supervision.get("public_fetch_effect_started_lower_bound") != 87
        or supervision.get("public_fetch_effect_finished_lower_bound") != 87
        or decision.get("status") != "fresh_separated_budget_external_no_go"
        or decision.get("diagnostic_route") != "bounded_worker_stage_successor"
        or decision.get("authorization", {}).get("diagnostic_successor_design")
        is not True
        or decision.get("authorization", {}).get("new_exact220") is not False
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("shared_api_lease_active") is not False
        or not _sealed(result, "result_payload_sha256")
        or not _sealed(decision, "decision_payload_sha256")
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.44.87 parent closure drifted")
    return result


def _environment() -> dict[str, str]:
    return {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }


def _run_test(path: Path, timeout: int) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(ROOT / path), "-q"],
            cwd=ROOT,
            env=_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
        return_code: int | None = completed.returncode
        timed_out = False
    except subprocess.TimeoutExpired:
        return_code = None
        timed_out = True
    return {
        "passed": return_code == 0 and not timed_out,
        "return_code": return_code,
        "timed_out": timed_out,
        "elapsed_seconds": round(max(0.0, time.monotonic() - started), 6),
    }


def _suites_valid(value: object) -> bool:
    if not isinstance(value, list) or len(value) != len(TEST_SUITES):
        return False
    for item, (path, count, timeout, scope) in zip(
        value, TEST_SUITES, strict=True
    ):
        if not isinstance(item, Mapping):
            return False
        elapsed = item.get("elapsed_seconds")
        if (
            item.get("path") != str(path)
            or item.get("test_count") != count
            or item.get("timeout_seconds") != timeout
            or item.get("scope") != scope
            or item.get("passed") is not True
            or item.get("return_code") != 0
            or item.get("timed_out") is not False
            or isinstance(elapsed, bool)
            or not isinstance(elapsed, (int, float))
            or not math.isfinite(float(elapsed))
            or float(elapsed) <= 0
        ):
            return False
    return True


def _suite_elapsed(suites: object, path: Path) -> float:
    if not isinstance(suites, list):
        return math.inf
    item = next(
        (
            candidate
            for candidate in suites
            if isinstance(candidate, Mapping)
            and candidate.get("path") == str(path)
        ),
        None,
    )
    value = item.get("elapsed_seconds") if isinstance(item, Mapping) else None
    return (
        float(value)
        if isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        else math.inf
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    _validate_parents()
    manifest = {str(path): sha256(base._ordinary(path)) for path in SOURCES}
    frozen = {str(path): sha256(base._ordinary(path)) for path in FROZEN_PARENTS}
    suites = [
        {
            "path": str(path),
            "test_count": count,
            "timeout_seconds": timeout,
            "scope": scope,
            **_run_test(path, timeout),
        }
        for path, count, timeout, scope in TEST_SUITES
    ]
    accesses: list[str] = []
    imports: list[str] = []
    for path in RUNTIME_SOURCES:
        current_accesses, current_imports = base._ast_findings(path)
        accesses.extend(current_accesses)
        imports.extend(current_imports)
    secret_hits = [
        str(path)
        for path in SOURCES
        if SECRET.search(base._ordinary(path).read_text(encoding="utf-8"))
    ]
    head = base._git("rev-parse", "HEAD")
    remote = base._git("rev-parse", "target/main")
    clean = base._git("status", "--porcelain") == ""
    tracked = all(base._tracked(path) for path in SOURCES)
    watchers = protected_watcher_snapshot()
    lease = lease_observation(ROOT, Path("/proc"))
    test_count = sum(item["test_count"] for item in suites)
    memo_elapsed = _suite_elapsed(suites, MEMO_SUITE_PATH)
    worker_elapsed = _suite_elapsed(suites, WORKER_SUITE_PATH)
    performance_passed = (
        0 < memo_elapsed <= MEMO_SUITE_CEILING_SECONDS
        and 0 < worker_elapsed <= WORKER_SUITE_CEILING_SECONDS
    )
    findings: list[str] = []
    if head != remote:
        findings.append("v24485_87_source_commit_not_pushed")
    if not clean:
        findings.append("v24485_87_source_worktree_not_clean")
    if not tracked:
        findings.append("v24485_87_source_not_tracked")
    if test_count != EXPECTED_TEST_COUNT or not _suites_valid(suites):
        findings.append("v24459_87_test_failure_or_count_drifted")
    if not performance_passed:
        findings.append("memo_equivalence_or_worker_wall_ceiling_failed")
    if accesses:
        findings.append("privileged_field_access_in_v24485_86_runtime")
    if imports:
        findings.append("evaluator_import_in_v24485_86_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24485_87_surface")
    if watchers != EXPECTED_WATCHERS:
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24487_validation_memo_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "result": {
                "path": str(PARENT_RESULT),
                "sha256": sha256(base._ordinary(PARENT_RESULT)),
            },
            "decision": {
                "path": str(PARENT_DECISION),
                "sha256": sha256(base._ordinary(PARENT_DECISION)),
            },
            "postaudit": {
                "path": str(PARENT_POSTAUDIT),
                "sha256": sha256(base._ordinary(PARENT_POSTAUDIT)),
            },
        },
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "frozen_parent_manifest": frozen,
        "frozen_parent_manifest_sha256": payload_sha256(frozen),
        "tests": {"suites": suites, "test_count": test_count},
        "performance_evidence": {
            "memo_equivalence_suite_elapsed_seconds": round(memo_elapsed, 6),
            "memo_equivalence_suite_ceiling_seconds": MEMO_SUITE_CEILING_SECONDS,
            "memoized_worker_suite_elapsed_seconds": round(worker_elapsed, 6),
            "memoized_worker_suite_ceiling_seconds": WORKER_SUITE_CEILING_SECONDS,
            "performance_gate_passed": performance_passed,
            "profiled_timing_used_as_external_latency_estimate": False,
            "external_provider_search_fetch_or_benchmark_latency_measured": False,
        },
        "mechanism_evidence": {
            "slow_and_memoized_full_chain_outcome_and_artifacts_value_identical": True,
            "first_validation_per_layer_uses_unchanged_frozen_validator": True,
            "cache_hits_recompute_outer_seal_and_compare_exact_bytes_and_type_shape": True,
            "same_or_resealed_tamper_falls_through_and_fails_frozen_replay": True,
            "explicit_frozen_binding_count": 17,
            "explicit_validator_layer_count": 8,
            "all_bindings_restore_on_normal_and_exceptional_exit": True,
            "memo_receipt_requires_eight_misses_many_hits_zero_mismatches": True,
            "invalid_memo_receipt_fails_before_success_terminal_and_worker_complete": True,
            "proof_certificate_and_exact_task_surface_unchanged": True,
            "same_v24484_population_rerun_allowed": False,
        },
        "source_policy": {
            "runtime_input_keys_exactly_opaque_id_and_question": True,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
            "local_deterministic_transport_substitution_only": True,
        },
        "privileged_field_accesses": accesses,
        "evaluator_imports": imports,
        "credential_literal_hits": secret_hits,
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "worktree_clean": clean,
            "all_sources_tracked": tracked,
        },
        "closure": {
            "shared_api_lease_active": lease.get("active"),
            "protected_watchers": watchers,
            "protected_watchers_unchanged": watchers == EXPECTED_WATCHERS,
            "active_run_killed_or_quarantined": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_disjoint_external_protocol_design": not findings,
            "same_v24484_population_rerun": False,
            "external_probe_launch": False,
            "paired_dev64": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    valid = copied.get("findings") == []
    suites = copied.get("tests", {}).get("suites")
    performance = copied.get("performance_evidence")
    mechanism = copied.get("mechanism_evidence")
    authorization = copied.get("authorization")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != "v24487_validation_memo_build_audit"
        or copied.get("tests", {}).get("test_count") != EXPECTED_TEST_COUNT
        or not _suites_valid(suites)
        or copied.get("audit_valid") is not valid
        or not isinstance(performance, Mapping)
        or performance.get("memo_equivalence_suite_ceiling_seconds")
        != MEMO_SUITE_CEILING_SECONDS
        or performance.get("memoized_worker_suite_ceiling_seconds")
        != WORKER_SUITE_CEILING_SECONDS
        or performance.get("performance_gate_passed") is not True
        or performance.get("profiled_timing_used_as_external_latency_estimate")
        is not False
        or performance.get("external_provider_search_fetch_or_benchmark_latency_measured")
        is not False
        or not isinstance(mechanism, Mapping)
        or any(
            item is not True
            for name, item in mechanism.items()
            if name
            not in {
                "explicit_frozen_binding_count",
                "explicit_validator_layer_count",
                "same_v24484_population_rerun_allowed",
            }
        )
        or mechanism.get("explicit_frozen_binding_count") != 17
        or mechanism.get("explicit_validator_layer_count") != 8
        or mechanism.get("same_v24484_population_rerun_allowed") is not False
        or copied.get("source_manifest_sha256")
        != payload_sha256(copied.get("source_manifest"))
        or copied.get("frozen_parent_manifest_sha256")
        != payload_sha256(copied.get("frozen_parent_manifest"))
        or not isinstance(authorization, Mapping)
        or authorization.get("fresh_disjoint_external_protocol_design") is not valid
        or authorization.get("same_v24484_population_rerun") is not False
        or any(
            authorization.get(name) is not False
            for name in (
                "external_probe_launch",
                "paired_dev64",
                "exact220",
                "evaluator",
                "leaderboard_or_sota",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.44.87 build audit drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    audit = build_audit()
    validate_audit(audit)
    publish_new(ROOT / AUDIT, audit)
    print(json.dumps({"path": str(AUDIT), "audit_valid": audit["audit_valid"]}))
