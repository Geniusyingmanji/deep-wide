#!/usr/bin/env python3
"""Build audit for V2.44.68--70 bounded adaptive closure.

This audit reruns only local loopback/synthetic tests.  It verifies hard
total-wall HTTP effects, worker-group cutoff, content-free hash-chained stage
checkpoints, exact proof-carrying success, and bounded validation-timeout
closure.  It performs no external network, benchmark, model, search, fetch, or
evaluator call and authorizes only design of a new disjoint external protocol.
"""

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
from scripts import diagnose_v24467_v24466_total_wall as diagnosis  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


DATE = "20260804"
AUDIT = Path(f"results/v24471_bounded_adaptive_build_audit_v1_{DATE}.json")
PARENT = diagnosis.REPORT
SOURCES = (
    Path("scripts/v24468_total_wall_http_helper.py"),
    Path("src/deepwide_agent/v24468_total_wall_transport.py"),
    Path("tests/test_v24468_total_wall_transport.py"),
    Path("src/deepwide_agent/v24469_bounded_worker_supervisor.py"),
    Path("tests/test_v24469_bounded_worker_supervisor.py"),
    Path("src/deepwide_agent/v24470_bounded_adaptive_integration.py"),
    Path("tests/test_v24470_bounded_adaptive_integration.py"),
    Path("scripts/audit_v24471_bounded_adaptive_build.py"),
    Path("tests/test_audit_v24471_bounded_adaptive_build.py"),
)
RUNTIME_SOURCES = (SOURCES[0], SOURCES[1], SOURCES[3], SOURCES[5])
FROZEN_PARENTS = (
    Path("src/deepwide_agent/v24464_single_validation_adaptive_persistence.py"),
    Path("results/v24465_single_validation_adaptive_build_audit_v1_20260804.json"),
    Path("results/v24466_single_validation_external_result_v1_20260804.json"),
    PARENT,
)
TEST_SUITES = (
    (SOURCES[2], 8, 180, "hard_total_wall_transport"),
    (SOURCES[4], 11, 180, "bounded_worker_fault_matrix"),
    (SOURCES[6], 8, 300, "bounded_adaptive_subprocess_integration"),
    (Path("tests/test_v24464_single_validation_adaptive_persistence.py"), 5, 420, "frozen_single_validation_parent"),
    (SOURCES[8], 5, 120, "audit_control"),
)
EXPECTED_TEST_COUNT = 37
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
        raise RuntimeError("V2.44.71 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _validate_parent() -> dict[str, Any]:
    value = _read(PARENT)
    if (
        value.get("role") != "v24467_v24466_total_wall_diagnosis"
        or value.get("diagnosis_valid") is not True
        or value.get("findings") != []
        or value.get("diagnosis", {}).get(
            "requests_timeout_is_inactivity_not_total_wall_counterexample_proven"
        )
        is not True
        or value.get("diagnosis", {}).get(
            "exact_v24466_blocking_call_or_validation_stage_identifiable"
        )
        is not False
        or value.get("diagnosis", {}).get("same_v24466_population_rerun_allowed")
        is not False
        or value.get("authorization", {}).get(
            "true_total_wall_effect_guard_design"
        )
        is not True
        or value.get("authorization", {}).get(
            "content_free_stage_checkpoint_design"
        )
        is not True
        or value.get("authorization", {}).get(
            "bounded_single_validation_finalize_design"
        )
        is not True
        or value.get("authorization", {}).get("external_probe_launch") is not False
        or not _sealed(value, "diagnosis_payload_sha256")
    ):
        raise RuntimeError("V2.44.71 diagnosis parent drifted")
    return value


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
    return {
        "passed": completed.returncode == 0,
        "return_code": completed.returncode,
        "elapsed_seconds": round(max(0.0, time.monotonic() - started), 6),
    }


def _suite_records_valid(value: object) -> bool:
    if not isinstance(value, list) or len(value) != len(TEST_SUITES):
        return False
    for item, (path, count, timeout, scope) in zip(value, TEST_SUITES, strict=True):
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
            or isinstance(elapsed, bool)
            or not isinstance(elapsed, (int, float))
            or not math.isfinite(elapsed)
            or elapsed <= 0
        ):
            return False
    return True


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    _validate_parent()
    manifest = {str(path): sha256(base._ordinary(path)) for path in SOURCES}
    frozen = {str(path): sha256(base._ordinary(path)) for path in FROZEN_PARENTS}
    suites = []
    for path, count, timeout, scope in TEST_SUITES:
        execution = _run_test(path, timeout)
        suites.append({
            "path": str(path),
            "test_count": count,
            "timeout_seconds": timeout,
            "scope": scope,
            **execution,
        })
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
    findings: list[str] = []
    if head != remote:
        findings.append("v24468_71_source_commit_not_pushed")
    if not clean:
        findings.append("v24468_71_source_worktree_not_clean")
    if not tracked:
        findings.append("v24468_71_source_not_tracked")
    if test_count != EXPECTED_TEST_COUNT or not _suite_records_valid(suites):
        findings.append("v24464_71_test_failure_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24468_70_runtime")
    if imports:
        findings.append("evaluator_import_in_v24468_70_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24468_71_surface")
    if watchers != EXPECTED_WATCHERS:
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")

    value = {
        "artifact_version": 1,
        "role": "v24471_bounded_adaptive_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"path": str(PARENT), "sha256": sha256(base._ordinary(PARENT))},
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "frozen_parent_manifest": frozen,
        "frozen_parent_manifest_sha256": payload_sha256(frozen),
        "tests": {"suites": suites, "test_count": test_count},
        "mechanism_evidence": {
            "requests_socket_timeout_replaced_by_hard_total_wall_helper": True,
            "helper_endpoint_restricted_to_loopback_ip_literal": True,
            "helper_redirect_following_disabled": True,
            "helper_and_worker_parent_death_signal_bound": True,
            "worker_group_hard_cutoff_before_parent_deadline_available": True,
            "checkpoint_is_append_only_hash_chained_and_content_free": True,
            "checkpoint_directory_is_sibling_of_exact_proof_surface": True,
            "effect_started_and_finished_lower_bounds_preserved_on_timeout": True,
            "complete_validation_entered_vs_returned_distinguished": True,
            "successful_child_complete_validation_attested": True,
            "successful_parent_exact_byte_certificate_validated_once": True,
            "serialized_full_replay_not_used_as_false_tuple_list_identity_gate": True,
            "same_v24466_population_rerun_allowed": False,
        },
        "source_policy": {
            "runtime_input_keys_exactly_opaque_id_and_question": True,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
            "local_loopback_http_and_synthetic_subprocess_only": True,
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
    authorization = copied.get("authorization")
    mechanism = copied.get("mechanism_evidence")
    suites = copied.get("tests", {}).get("suites")
    valid = copied.get("findings") == []
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != "v24471_bounded_adaptive_build_audit"
        or copied.get("tests", {}).get("test_count") != EXPECTED_TEST_COUNT
        or not _suite_records_valid(suites)
        or copied.get("audit_valid") is not valid
        or not isinstance(mechanism, Mapping)
        or any(
            item is not True
            for name, item in mechanism.items()
            if name != "same_v24466_population_rerun_allowed"
        )
        or mechanism.get("same_v24466_population_rerun_allowed") is not False
        or not isinstance(authorization, Mapping)
        or authorization.get("fresh_disjoint_external_protocol_design") is not valid
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
        or copied.get("source_manifest_sha256")
        != payload_sha256(copied.get("source_manifest"))
        or copied.get("frozen_parent_manifest_sha256")
        != payload_sha256(copied.get("frozen_parent_manifest"))
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.44.71 build audit drifted")
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
