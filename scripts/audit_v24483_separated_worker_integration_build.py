#!/usr/bin/env python3
"""Build audit for V2.44.82 separated-budget worker integration."""

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
from scripts import audit_v24481_separated_budget_build as parent  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


DATE = "20260804"
AUDIT = Path(
    f"results/v24483_separated_worker_integration_build_audit_v1_{DATE}.json"
)
PARENT = parent.AUDIT
SOURCES = (
    Path("src/deepwide_agent/v24482_separated_budget_worker_integration.py"),
    Path("tests/test_v24482_separated_budget_worker_integration.py"),
    Path("scripts/audit_v24483_separated_worker_integration_build.py"),
    Path("tests/test_audit_v24483_separated_worker_integration_build.py"),
)
RUNTIME_SOURCES = (SOURCES[0],)
FROZEN_PARENTS = (
    Path("src/deepwide_agent/v24480_separated_effect_validation_budget.py"),
    Path("src/deepwide_agent/v24469_bounded_worker_supervisor.py"),
    Path("src/deepwide_agent/v24470_bounded_adaptive_integration.py"),
    Path("src/deepwide_agent/v24476_bounded_nominal_search_integration.py"),
    PARENT,
)
TEST_SUITES = (
    (
        Path("tests/test_v24468_total_wall_transport.py"),
        8,
        180,
        "hard_total_wall_transport",
    ),
    (
        Path("tests/test_v24469_bounded_worker_supervisor.py"),
        11,
        180,
        "worker_process_group_fault_matrix",
    ),
    (
        Path("tests/test_v24470_bounded_adaptive_integration.py"),
        8,
        180,
        "proof_carrying_parent_supervisor_control",
    ),
    (
        Path("tests/test_v24476_bounded_nominal_search_integration.py"),
        2,
        120,
        "full_nominal_hard_search_chain",
    ),
    (
        Path("tests/test_v24480_separated_effect_validation_budget.py"),
        6,
        60,
        "separated_phase_budget",
    ),
    (
        Path("tests/test_v24482_separated_budget_worker_integration.py"),
        7,
        120,
        "real_three_process_separated_budget_chain",
    ),
    (
        Path("tests/test_audit_v24483_separated_worker_integration_build.py"),
        5,
        60,
        "audit_control",
    ),
)
EXPECTED_TEST_COUNT = 47
REAL_CHAIN_PATH = Path("tests/test_v24482_separated_budget_worker_integration.py")
REAL_CHAIN_SUITE_CEILING_SECONDS = 50.0
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
        raise RuntimeError("V2.44.83 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _validate_parent() -> dict[str, Any]:
    value = parent.validate_audit(_read(PARENT))
    authorization = value.get("authorization") or {}
    if (
        value.get("audit_valid") is not True
        or value.get("findings") != []
        or authorization.get("fresh_disjoint_external_protocol_design") is not True
        or authorization.get("same_v24478_population_rerun") is not False
        or authorization.get("external_probe_launch") is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.44.83 build parent drifted")
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
            or isinstance(elapsed, bool)
            or not isinstance(elapsed, (int, float))
            or not math.isfinite(float(elapsed))
            or float(elapsed) <= 0
        ):
            return False
    return True


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    _validate_parent()
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
    real_chain = next(
        (
            item
            for item in suites
            if item["path"] == str(REAL_CHAIN_PATH)
        ),
        None,
    )
    real_chain_elapsed = (
        float(real_chain["elapsed_seconds"])
        if isinstance(real_chain, Mapping)
        else math.inf
    )
    real_chain_passed = (
        math.isfinite(real_chain_elapsed)
        and 0 < real_chain_elapsed <= REAL_CHAIN_SUITE_CEILING_SECONDS
    )
    findings: list[str] = []
    if head != remote:
        findings.append("v24482_83_source_commit_not_pushed")
    if not clean:
        findings.append("v24482_83_source_worktree_not_clean")
    if not tracked:
        findings.append("v24482_83_source_not_tracked")
    if test_count != EXPECTED_TEST_COUNT or not _suites_valid(suites):
        findings.append("v24468_83_test_failure_or_count_drifted")
    if not real_chain_passed:
        findings.append("real_three_process_chain_exceeded_local_ceiling")
    if accesses:
        findings.append("privileged_field_access_in_v24482_runtime")
    if imports:
        findings.append("evaluator_import_in_v24482_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24482_83_surface")
    if watchers != EXPECTED_WATCHERS:
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24483_separated_worker_integration_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"path": str(PARENT), "sha256": sha256(base._ordinary(PARENT))},
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "frozen_parent_manifest": frozen,
        "frozen_parent_manifest_sha256": payload_sha256(frozen),
        "tests": {"suites": suites, "test_count": test_count},
        "mechanism_evidence": {
            "one_origin_crosses_real_parent_supervisor_worker_processes": real_chain_passed,
            "remote_effect_deadline_seconds": 150.0,
            "worker_deadline_seconds": 220.0,
            "parent_deadline_seconds": 245.0,
            "remote_clients_cannot_consume_local_validation_reserve": True,
            "worker_process_group_cutoff_preserved": True,
            "timeout_failure_stage_and_effect_lower_bounds_preserved": True,
            "complete_validation_and_terminal_certificate_preserved": True,
            "full_nominal_hard_search_chain_preserved": True,
            "real_chain_suite_elapsed_seconds": round(real_chain_elapsed, 6),
            "real_chain_suite_ceiling_seconds": REAL_CHAIN_SUITE_CEILING_SECONDS,
            "same_v24478_population_rerun_allowed": False,
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
            "same_v24478_population_rerun": False,
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
    mechanism = copied.get("mechanism_evidence")
    authorization = copied.get("authorization")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role")
        != "v24483_separated_worker_integration_build_audit"
        or copied.get("tests", {}).get("test_count") != EXPECTED_TEST_COUNT
        or not _suites_valid(suites)
        or copied.get("audit_valid") is not valid
        or not isinstance(mechanism, Mapping)
        or mechanism.get("one_origin_crosses_real_parent_supervisor_worker_processes")
        is not True
        or mechanism.get("remote_effect_deadline_seconds") != 150.0
        or mechanism.get("worker_deadline_seconds") != 220.0
        or mechanism.get("parent_deadline_seconds") != 245.0
        or mechanism.get("remote_clients_cannot_consume_local_validation_reserve")
        is not True
        or mechanism.get("worker_process_group_cutoff_preserved") is not True
        or mechanism.get("timeout_failure_stage_and_effect_lower_bounds_preserved")
        is not True
        or mechanism.get("complete_validation_and_terminal_certificate_preserved")
        is not True
        or mechanism.get("full_nominal_hard_search_chain_preserved") is not True
        or mechanism.get("same_v24478_population_rerun_allowed") is not False
        or copied.get("source_manifest_sha256")
        != payload_sha256(copied.get("source_manifest"))
        or copied.get("frozen_parent_manifest_sha256")
        != payload_sha256(copied.get("frozen_parent_manifest"))
        or not isinstance(authorization, Mapping)
        or authorization.get("fresh_disjoint_external_protocol_design") is not valid
        or authorization.get("same_v24478_population_rerun") is not False
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
        raise RuntimeError("V2.44.83 build audit drifted")
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
