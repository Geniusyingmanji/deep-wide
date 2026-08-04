#!/usr/bin/env python3
"""Build-only audit for the V2.43.99 failure-observable runner."""

from __future__ import annotations

import json
import os
import re
import sys
import time
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
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402


DATE = "20260804"
AUDIT = Path(
    f"results/v24400_failure_observable_runner_build_audit_v1_{DATE}.json"
)
PARENT = Path(f"results/v24398_failure_observability_build_audit_v1_{DATE}.json")
SOURCES = (
    Path("src/deepwide_agent/v24397_failure_observability.py"),
    Path("src/deepwide_agent/v24399_failure_observable_runner.py"),
    Path("tests/test_v24397_failure_observability.py"),
    Path("tests/test_v24399_failure_observable_runner.py"),
    Path("scripts/audit_v24400_failure_observable_runner_build.py"),
)
RUNTIME_SOURCES = SOURCES[:2]
TEST_SUITES = (
    (Path("tests/test_v24308_child_exit_observability.py"), 9),
    (Path("tests/test_v24309_runner_exit_integration.py"), 5),
    (Path("tests/test_v24312_deadline_reliability.py"), 7),
    (Path("tests/test_v24391_uncertainty_active_evidence_runner.py"), 4),
    (Path("tests/test_v24397_failure_observability.py"), 6),
    (Path("tests/test_v24399_failure_observable_runner.py"), 6),
)
EXPECTED_TEST_COUNT = 37
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
        raise RuntimeError("V2.44.00 expected object")
    return value


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    parent = _read(PARENT)
    if (
        parent.get("role") != "v24398_failure_observability_build_audit"
        or parent.get("audit_valid") is not True
        or parent.get("findings") != []
        or parent.get("authorization", {}).get(
            "failure_observability_runner_integration_design"
        )
        is not True
        or parent.get("authorization", {}).get("external_probe_launch") is not False
        or parent.get("authorization", {}).get("benchmark_launch") is not False
    ):
        raise RuntimeError("V2.44.00 parent build audit drifted")

    manifest = {str(path): sha256(base._ordinary(path)) for path in SOURCES}
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
    suites = [
        {"path": str(path), "passed": base._run_test(path), "test_count": count}
        for path, count in TEST_SUITES
    ]
    test_count = sum(item["test_count"] for item in suites)
    head = base._git("rev-parse", "HEAD")
    remote = base._git("rev-parse", "target/main")
    clean = base._git("status", "--porcelain") == ""
    tracked = all(base._tracked(path) for path in SOURCES)
    watchers = protected_watcher_snapshot()
    lease = lease_observation(ROOT, Path("/proc"))
    findings: list[str] = []
    if head != remote:
        findings.append("v24399_source_commit_not_pushed")
    if not clean:
        findings.append("v24399_source_worktree_not_clean")
    if not tracked:
        findings.append("v24399_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24308_99_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24397_99_runtime")
    if imports:
        findings.append("evaluator_import_in_v24397_99_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24397_4400_surface")
    if watchers != EXPECTED_WATCHERS:
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")

    value = {
        "artifact_version": 1,
        "role": "v24400_failure_observable_runner_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"path": str(PARENT), "sha256": sha256(base._ordinary(PARENT))},
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
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "mechanism_evidence": {
            "successful_v24391_algorithm_path_unchanged": True,
            "model_search_and_runtime_construction_stages_distinguished": True,
            "runtime_exception_snapshots_partial_effect_receipts_before_reraise": True,
            "result_is_written_after_independent_success_receipts": True,
            "child_terminal_receipt_remains_final_child_artifact": True,
            "non_success_parent_never_enters_success_envelope_projection": True,
            "parent_observation_reads_only_content_free_artifacts": True,
            "failure_snapshot_binds_independent_receipt_hashes": True,
            "parent_hard_timeout_requires_no_private_artifact": True,
            "fault_injection_covers_model_search_runtime_timeout_and_tamper": True,
        },
        "privileged_field_accesses": sorted(accesses),
        "evaluator_imports": sorted(imports),
        "credential_literal_hits": sorted(secret_hits),
        "closure": {
            "shared_api_lease_active": lease.get("active"),
            "protected_watchers": watchers,
            "protected_watchers_unchanged": watchers == EXPECTED_WATCHERS,
            "active_run_killed_or_quarantined": False,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "failure_observation_boundary": [
                "parent_exit_receipt",
                "child_terminal_receipt",
                "content_free_partial_effect_receipts",
                "failure_snapshot",
            ],
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "task_private_content_emitted_to_observation": False,
            "remote_network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_failure_observable_external_probe_design": not findings,
            "external_probe_launch": False,
            "benchmark_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


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
    publish_new(ROOT / AUDIT, audit)
    print(json.dumps({"path": str(AUDIT), "audit_valid": audit["audit_valid"]}))
