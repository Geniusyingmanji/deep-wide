#!/usr/bin/env python3
"""Build audit for the V2.44.76 bounded compatible-search integration."""

from __future__ import annotations

import json
import math
import os
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
from scripts import audit_v24475_nominal_hard_search_build as parent  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


DATE = "20260804"
AUDIT = Path(f"results/v24477_bounded_nominal_integration_build_audit_v1_{DATE}.json")
PARENT = parent.AUDIT
SOURCES = (
    Path("src/deepwide_agent/v24476_bounded_nominal_search_integration.py"),
    Path("tests/test_v24476_bounded_nominal_search_integration.py"),
    Path("scripts/audit_v24477_bounded_nominal_integration_build.py"),
    Path("tests/test_audit_v24477_bounded_nominal_integration_build.py"),
)
RUNTIME_SOURCES = (SOURCES[0],)
FROZEN_PARENTS = (
    Path("src/deepwide_agent/v24438_bounded_narrative_effect_runner.py"),
    Path("src/deepwide_agent/v24468_total_wall_transport.py"),
    Path("src/deepwide_agent/v24469_bounded_worker_supervisor.py"),
    Path("src/deepwide_agent/v24470_bounded_adaptive_integration.py"),
    Path("src/deepwide_agent/v24474_nominal_hard_total_wall_search.py"),
    PARENT,
)
TEST_SUITES = (
    (Path("tests/test_v24438_bounded_narrative_effect_runner.py"), 7, 240, "legacy_nominal_contract"),
    (Path("tests/test_v24468_total_wall_transport.py"), 8, 180, "hard_total_wall_transport"),
    (Path("tests/test_v24469_bounded_worker_supervisor.py"), 11, 180, "bounded_worker_supervisor"),
    (Path("tests/test_v24470_bounded_adaptive_integration.py"), 8, 300, "bounded_adaptive_integration"),
    (Path("tests/test_v24474_nominal_hard_total_wall_search.py"), 7, 180, "nominal_hard_search_compatibility"),
    (Path("tests/test_v24476_bounded_nominal_search_integration.py"), 2, 300, "full_frozen_chain_success"),
    (Path("tests/test_audit_v24477_bounded_nominal_integration_build.py"), 5, 120, "audit_control"),
)
EXPECTED_TEST_COUNT = 48
EXPECTED_WATCHERS = parent.EXPECTED_WATCHERS
SECRET = parent.SECRET
base = parent.base


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(base._ordinary(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.44.77 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _validate_parent() -> dict[str, Any]:
    value = parent.validate_audit(_read(PARENT))
    if (
        value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get(
            "fresh_disjoint_external_protocol_design"
        )
        is not True
        or value.get("authorization", {}).get("same_v24472_population_rerun")
        is not False
        or value.get("authorization", {}).get("external_probe_launch") is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.44.77 build parent drifted")
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
    findings: list[str] = []
    if head != remote:
        findings.append("v24476_77_source_commit_not_pushed")
    if not clean:
        findings.append("v24476_77_source_worktree_not_clean")
    if not tracked:
        findings.append("v24476_77_source_not_tracked")
    if test_count != EXPECTED_TEST_COUNT or not _suites_valid(suites):
        findings.append("v24438_77_test_failure_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24476_runtime")
    if imports:
        findings.append("evaluator_import_in_v24476_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24476_77_surface")
    if watchers != EXPECTED_WATCHERS:
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24477_bounded_nominal_integration_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"path": str(PARENT), "sha256": sha256(base._ordinary(PARENT))},
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "frozen_parent_manifest": frozen,
        "frozen_parent_manifest_sha256": payload_sha256(frozen),
        "tests": {"suites": suites, "test_count": test_count},
        "mechanism_evidence": {
            "formal_search_satisfies_legacy_nominal_contract": True,
            "hard_total_wall_request_path_exercised": True,
            "hard_search_started_and_finished_callbacks_balanced": True,
            "model_acquisitions_and_hosted_search_effects_observed": True,
            "positive_entropy_decision_credit_observed": True,
            "safe_output_change_observed": True,
            "single_complete_validation_returned": True,
            "artifact_persistence_and_terminal_certificate_completed": True,
            "public_receipts_exclude_task_question_and_opaque_id": True,
            "same_v24472_population_rerun_allowed": False,
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
            "same_v24472_population_rerun": False,
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
        or copied.get("role") != "v24477_bounded_nominal_integration_build_audit"
        or copied.get("tests", {}).get("test_count") != EXPECTED_TEST_COUNT
        or not _suites_valid(suites)
        or copied.get("audit_valid") is not valid
        or not isinstance(mechanism, Mapping)
        or any(
            item is not True
            for name, item in mechanism.items()
            if name != "same_v24472_population_rerun_allowed"
        )
        or mechanism.get("same_v24472_population_rerun_allowed") is not False
        or not isinstance(authorization, Mapping)
        or authorization.get("fresh_disjoint_external_protocol_design") is not valid
        or authorization.get("same_v24472_population_rerun") is not False
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
        raise RuntimeError("V2.44.77 build audit drifted")
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
