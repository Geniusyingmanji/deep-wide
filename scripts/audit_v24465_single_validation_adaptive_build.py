#!/usr/bin/env python3
"""Build-only audit of V2.44.64 single-validation persistence.

The audit binds the V2.44.63 all-timeout NO-GO, verifies that V2.44.57 already
performs complete cross-artifact validation before returning, proves the new
mechanical envelope equals the frozen recursive builder, measures both paths
on a local synthetic fixture, and freezes a minimum future terminal reserve.

It performs no network, model endpoint, search provider, fetch, benchmark, or
evaluator call.  Passing authorizes only design of a new benchmark-external
protocol with a disjoint population; it never authorizes launch, dev64,
exact220, evaluation, leaderboard submission, or SOTA claims.
"""

from __future__ import annotations

import copy
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import (  # noqa: E402
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from deepwide_agent.v24457_adaptive_entropy_support import (  # noqa: E402
    build_envelope as build_recursive_envelope,
)
from deepwide_agent.v24464_single_validation_adaptive_persistence import (  # noqa: E402
    build_envelope_from_validated_execution,
    run_single_validation_v24457_task,
)
from scripts import audit_v24398_failure_observability_build as base  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


DATE = "20260804"
AUDIT = Path(f"results/v24465_single_validation_adaptive_build_audit_v1_{DATE}.json")
PARENT = Path(f"results/v24462_proof_carrying_adaptive_build_audit_v1_{DATE}.json")
FAILED_RESULT = Path(f"results/v24463_adaptive_proof_external_result_v1_{DATE}.json")
FAILED_DECISION = Path(f"results/v24463_adaptive_proof_external_decision_v1_{DATE}.json")
FAILED_POSTAUDIT = Path(
    f"results/v24463_adaptive_proof_external_postresult_audit_v1_{DATE}.json"
)
SOURCES = (
    Path("src/deepwide_agent/v24457_adaptive_entropy_support.py"),
    Path("src/deepwide_agent/v24459_proof_carrying_adaptive_entropy_support.py"),
    Path("src/deepwide_agent/v24464_single_validation_adaptive_persistence.py"),
    Path("tests/test_v24457_adaptive_entropy_support.py"),
    Path("tests/test_v24459_proof_carrying_adaptive_entropy_support.py"),
    Path("tests/test_v24464_single_validation_adaptive_persistence.py"),
    Path("scripts/audit_v24465_single_validation_adaptive_build.py"),
    Path("tests/test_audit_v24465_single_validation_adaptive_build.py"),
)
RUNTIME_SOURCES = (SOURCES[2],)
TEST_SUITES = (
    (SOURCES[3], 6, "adaptive_semantic_regression", 900),
    (SOURCES[4], 7, "adaptive_proof_regression", 360),
    (SOURCES[5], 5, "single_validation_persistence", 360),
    (SOURCES[7], 5, "audit_control", 360),
)
EXPECTED_MECHANISM_TEST_COUNT = 18
EXPECTED_CONTROL_TEST_COUNT = 5
EXPECTED_TEST_COUNT = 23
PERFORMANCE_REPETITIONS = 3
FAST_ENVELOPE_P95_CEILING_SECONDS = 1.0
MINIMUM_FUTURE_TERMINAL_RESERVE_SECONDS = 45.0
EXPECTED_WATCHERS = base.EXPECTED_WATCHERS
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(base._ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.44.65 expected object")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _validate_parents() -> dict[str, Any]:
    parent = _read(PARENT)
    result = _read(FAILED_RESULT)
    decision = _read(FAILED_DECISION)
    post = _read(FAILED_POSTAUDIT)
    observation = result.get("observation_aggregate") or {}
    timing = result.get("stage_timing_aggregate") or {}
    if (
        parent.get("role") != "v24462_proof_carrying_adaptive_build_audit"
        or parent.get("audit_valid") is not True
        or parent.get("findings") != []
        or not _sealed(parent, "audit_payload_sha256")
        or result.get("role") != "v24463_adaptive_proof_external_result"
        or result.get("passed") is not False
        or result.get("selected") != 16
        or result.get("batch_wall_seconds", 0) <= 480
        or observation.get("parent_taxonomy_counts") != {"hard_deadline_timeout": 16}
        or observation.get("success_tasks") != 0
        or observation.get("failure_tasks") != 16
        or observation.get("unobserved_effect_tasks") != 16
        or timing.get("certificate_validation_invocations") != 0
        or timing.get("complete_child_validation_attested_tasks") != 0
        or timing.get("recursive_historical_semantic_replay_tasks") != 0
        or not _sealed(result, "result_payload_sha256")
        or decision.get("status") != "fresh_adaptive_proof_external_no_go"
        or decision.get("diagnostic_route")
        != "runtime_validation_or_observability_repair"
        or decision.get("authorization", {}).get("diagnostic_successor_design")
        is not True
        or not _sealed(decision, "decision_payload_sha256")
        or post.get("audit_valid") is not True
        or post.get("findings") != []
        or post.get("shared_api_lease_active") is not False
        or post.get("authorization", {}).get("diagnostic_successor_design")
        is not True
        or not _sealed(post, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.44.65 parent or failed-run evidence drifted")
    return result


def _run_test(relative: Path, *, timeout_seconds: int) -> bool:
    completed = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(ROOT / relative), "-q"],
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
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=timeout_seconds,
        check=False,
    )
    return completed.returncode == 0


def _p95(values: list[float]) -> float:
    return sorted(values)[max(0, int(0.95 * len(values) + 0.999999) - 1)]


def _measure_builders() -> dict[str, Any]:
    from test_v24342_semantic_active_runtime import limits
    from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK
    from test_v24412_receipt_snapshot_diagnosis import AdvancingClock
    from test_v24447_third_source_entropy_to_decision import clients

    with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
        clock = AdvancingClock()
        model, search = clients(Path(temporary), clock, third=True)
        started = time.perf_counter()
        validated = run_single_validation_v24457_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        complete_validation_wall = time.perf_counter() - started
    fast: list[float] = []
    recursive: list[float] = []
    fast_value: dict[str, Any] | None = None
    recursive_value: dict[str, Any] | None = None
    for _ in range(PERFORMANCE_REPETITIONS):
        started = time.perf_counter()
        current_fast = build_envelope_from_validated_execution(validated)
        fast.append(time.perf_counter() - started)
        started = time.perf_counter()
        current_recursive = build_recursive_envelope(validated._trusted_outcome())
        recursive.append(time.perf_counter() - started)
        if fast_value is None:
            fast_value = current_fast
            recursive_value = current_recursive
        elif current_fast != fast_value or current_recursive != recursive_value:
            raise RuntimeError("V2.44.65 repeated envelope value drifted")
    equal = fast_value == recursive_value
    return {
        "scope": "synthetic_test_fixture_only",
        "repetitions": PERFORMANCE_REPETITIONS,
        "complete_validation_wall_seconds": round(complete_validation_wall, 6),
        "recursive_envelope_seconds": [round(value, 6) for value in recursive],
        "recursive_envelope_median_seconds": round(
            float(statistics.median(recursive)), 6
        ),
        "recursive_envelope_p95_seconds": round(_p95(recursive), 6),
        "fast_envelope_seconds": [round(value, 6) for value in fast],
        "fast_envelope_median_seconds": round(float(statistics.median(fast)), 6),
        "fast_envelope_p95_seconds": round(_p95(fast), 6),
        "fast_envelope_p95_ceiling_seconds": FAST_ENVELOPE_P95_CEILING_SECONDS,
        "fast_envelope_ceiling_passed": _p95(fast)
        <= FAST_ENVELOPE_P95_CEILING_SECONDS,
        "fast_and_recursive_envelope_values_equal": equal,
        "minimum_future_terminal_reserve_seconds": MINIMUM_FUTURE_TERMINAL_RESERVE_SECONDS,
        "terminal_reserve_exceeds_fast_p95_seconds": MINIMUM_FUTURE_TERMINAL_RESERVE_SECONDS
        > _p95(fast),
        "network_model_search_fetch_or_evaluator_called": False,
        "profile_is_not_external_latency_estimate": True,
    }


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    failed = _validate_parents()
    manifest = {str(path): sha256(base._ordinary(path)) for path in SOURCES}
    accesses: list[str] = []
    imports: list[str] = []
    for path in RUNTIME_SOURCES:
        current_accesses, current_imports = base._ast_findings(path)
        accesses.extend(current_accesses)
        imports.extend(current_imports)
    suites = [
        {
            "path": str(path),
            "passed": _run_test(path, timeout_seconds=timeout_seconds),
            "test_count": count,
            "scope": scope,
            "timeout_seconds": timeout_seconds,
        }
        for path, count, scope, timeout_seconds in TEST_SUITES
    ]
    test_count = sum(item["test_count"] for item in suites)
    performance = _measure_builders()
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
    findings: list[str] = []
    if head != remote:
        findings.append("v24464_65_source_commit_not_pushed")
    if not clean:
        findings.append("v24464_65_source_worktree_not_clean")
    if not tracked:
        findings.append("v24464_65_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24457_65_regression_failed_or_count_drifted")
    if (
        performance.get("fast_and_recursive_envelope_values_equal") is not True
        or performance.get("fast_envelope_ceiling_passed") is not True
        or performance.get("terminal_reserve_exceeds_fast_p95_seconds") is not True
    ):
        findings.append("single_validation_equivalence_or_latency_gate_failed")
    if accesses:
        findings.append("privileged_field_access_in_v24464_runtime")
    if imports:
        findings.append("evaluator_import_in_v24464_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24464_65_surface")
    if watchers != EXPECTED_WATCHERS:
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24465_single_validation_adaptive_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "proof_build": {"path": str(PARENT), "sha256": sha256(base._ordinary(PARENT))},
            "failed_external_result": {
                "path": str(FAILED_RESULT),
                "sha256": sha256(base._ordinary(FAILED_RESULT)),
            },
            "failed_external_decision": {
                "path": str(FAILED_DECISION),
                "sha256": sha256(base._ordinary(FAILED_DECISION)),
            },
            "failed_external_postaudit": {
                "path": str(FAILED_POSTAUDIT),
                "sha256": sha256(base._ordinary(FAILED_POSTAUDIT)),
            },
        },
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "worktree_clean": clean,
            "all_sources_tracked": tracked,
        },
        "tests": {
            "suites": suites,
            "passed": all(item["passed"] for item in suites)
            and test_count == EXPECTED_TEST_COUNT,
            "test_count": test_count,
            "mechanism_test_count": EXPECTED_MECHANISM_TEST_COUNT,
            "audit_control_test_count": EXPECTED_CONTROL_TEST_COUNT,
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "failed_run_evidence": {
            "selected": failed["selected"],
            "parent_hard_timeout_tasks": 16,
            "success_tasks": 0,
            "unobserved_effect_tasks": 16,
            "certificate_validation_invocations": 0,
            "batch_wall_seconds": failed["batch_wall_seconds"],
            "frozen_batch_wall_ceiling_seconds": 480.0,
            "mechanism_quality_was_not_evaluable": True,
            "same_population_rerun_authorized": False,
        },
        "performance_evidence": performance,
        "single_validation_evidence": {
            "frozen_v24457_complete_cross_artifact_validation_preserved": True,
            "complete_semantic_validation_count_per_successful_child": 1,
            "second_recursive_envelope_validation_removed": True,
            "mechanical_envelope_equals_frozen_recursive_envelope": True,
            "compact_outer_shell_and_receipts_still_validated": True,
            "v24459_exact_byte_certificate_preserved": True,
            "v24459_parent_capability_validation_preserved": True,
            "future_effect_deadline_must_precede_parent_timeout_by_at_least_seconds": MINIMUM_FUTURE_TERMINAL_RESERVE_SECONDS,
        },
        "trust_boundary": {
            "pinned_local_child_source_and_launch_manifest_are_trusted": True,
            "certificate_is_independently_signed": False,
            "certificate_is_remote_attestation": False,
            "malicious_child_resistance_claimed": False,
        },
        "privileged_field_accesses": sorted(accesses),
        "evaluator_imports": sorted(imports),
        "credential_literal_hits": sorted(secret_hits),
        "closure": {
            "shared_api_lease_active": lease.get("active"),
            "protected_watchers": watchers,
            "protected_watchers_unchanged": watchers == EXPECTED_WATCHERS,
            "external_probe_launched": False,
            "benchmark_or_watcher_signaled_restarted_or_modified": False,
            "active_run_killed_or_quarantined": False,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "task_query_url_page_prediction_value_or_content_hash_emitted": False,
            "remote_network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_external_protocol_design": not findings,
            "same_v24463_population_rerun": False,
            "external_probe_launch": False,
            "paired_dev64": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def validate_audit(value: dict[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(value)
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    authorization = copied.get("authorization")
    evidence = copied.get("single_validation_evidence")
    performance = copied.get("performance_evidence")
    failed = copied.get("failed_run_evidence")
    trust = copied.get("trust_boundary")
    if (
        copied.get("role") != "v24465_single_validation_adaptive_build_audit"
        or not isinstance(authorization, dict)
        or authorization.get("fresh_external_protocol_design")
        is not copied.get("audit_valid")
        or any(
            authorization.get(name) is not False
            for name in (
                "same_v24463_population_rerun",
                "external_probe_launch",
                "paired_dev64",
                "exact220",
                "evaluator",
                "leaderboard_or_sota",
            )
        )
        or not isinstance(evidence, dict)
        or evidence.get("complete_semantic_validation_count_per_successful_child") != 1
        or evidence.get("second_recursive_envelope_validation_removed") is not True
        or evidence.get(
            "future_effect_deadline_must_precede_parent_timeout_by_at_least_seconds"
        )
        != MINIMUM_FUTURE_TERMINAL_RESERVE_SECONDS
        or not isinstance(performance, dict)
        or performance.get("fast_and_recursive_envelope_values_equal") is not True
        or performance.get("fast_envelope_ceiling_passed") is not True
        or not isinstance(failed, dict)
        or failed.get("mechanism_quality_was_not_evaluable") is not True
        or failed.get("same_population_rerun_authorized") is not False
        or not isinstance(trust, dict)
        or trust.get("certificate_is_independently_signed") is not False
        or trust.get("certificate_is_remote_attestation") is not False
        or trust.get("malicious_child_resistance_claimed") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.44.65 build audit drifted")
    return copied


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    audit = build_audit()
    validate_audit(audit)
    publish_new(ROOT / AUDIT, audit)
    print(json.dumps({"path": str(AUDIT), "audit_valid": audit["audit_valid"]}))
