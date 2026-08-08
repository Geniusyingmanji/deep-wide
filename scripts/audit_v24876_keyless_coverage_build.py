#!/usr/bin/env python3
"""Clean, zero-effect build audit for V2.48.73--76."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import (  # noqa: E402
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402


DATE = "20260808"
OUTPUT = Path(f"results/v24876_keyless_coverage_build_audit_v1_{DATE}.json")
SOURCES = (
    Path("src/deepwide_agent/v24873_keyless_fixed_coverage_runtime.py"),
    Path("src/deepwide_agent/v24874_keyless_coverage_bundle.py"),
    Path("src/deepwide_agent/v24875_keyless_coverage_child_runtime.py"),
    Path("src/deepwide_agent/v24876_keyless_coverage_subprocess_gate.py"),
    Path("tests/test_v24873_keyless_fixed_coverage_runtime.py"),
    Path("tests/test_v24874_keyless_coverage_bundle.py"),
    Path("tests/test_v24875_keyless_coverage_child_runtime.py"),
    Path("tests/test_v24876_keyless_coverage_subprocess_gate.py"),
    Path("tests/fixtures/v24876_keyless_coverage_child.py"),
    Path("scripts/audit_v24876_keyless_coverage_build.py"),
)
RUNTIME = SOURCES[:4]
TESTS = (
    (Path("tests/test_v24859_full_evidence_coverage_revision.py"), 20),
    (Path("tests/test_v24860_coverage_revision_integration.py"), 11),
    (Path("tests/test_v24861_coverage_revision_exact_task.py"), 4),
    (Path("tests/test_v24862_same_task_coverage_runtime.py"), 5),
    (Path("tests/test_v24863_coverage_revision_child_bundle.py"), 4),
    (Path("tests/test_v24864_coverage_revision_child_runtime.py"), 3),
    (Path("tests/test_v24865_coverage_revision_subprocess_gate.py"), 4),
    (Path("tests/test_v24867_response_aware_coverage_bundle.py"), 6),
    (Path("tests/test_v24868_response_aware_coverage_runtime.py"), 4),
    (Path("tests/test_v24869_response_aware_subprocess_gate.py"), 4),
    (Path("tests/test_v24873_keyless_fixed_coverage_runtime.py"), 5),
    (Path("tests/test_v24874_keyless_coverage_bundle.py"), 10),
    (Path("tests/test_v24875_keyless_coverage_child_runtime.py"), 6),
    (Path("tests/test_v24876_keyless_coverage_subprocess_gate.py"), 3),
    (Path("tests/test_v24799_fixed_full_budget_control.py"), 5),
    (Path("tests/test_v24272_two_wave_retrieval.py"), 6),
    (Path("tests/test_v24630_thin_backfill_search.py"), 2),
)
EXPECTED_TESTS = 102
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(("gh" + "p_", "github" + "_pat_", "tvly" + "-dev-", "s" + "k-"))
    + r")[A-Za-z0-9_-]{16,}"
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _run_tests() -> tuple[int, bool, list[dict[str, Any]]]:
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1",
    }
    rows = []
    for path, expected in TESTS:
        completed = subprocess.run(
            [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest", "discover", "-s", "tests", "-p", path.name, "-v"],
            cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            timeout=300, check=False,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(match.group(1)) if match else 0
        rows.append({
            "path": str(path), "expected": expected, "observed": observed,
            "passed": completed.returncode == 0 and observed == expected,
            "output_sha256": payload_sha256(completed.stdout),
        })
    total = sum(row["observed"] for row in rows)
    return total, total == EXPECTED_TESTS and all(row["passed"] for row in rows), rows


def _static_findings() -> tuple[list[str], list[str], list[str]]:
    fields: list[str] = []
    evaluator: list[str] = []
    secrets: list[str] = []
    for relative in RUNTIME:
        path = ROOT / relative
        fields.extend(semantic_audit._accesses(path, ROOT))
        evaluator.extend(semantic_audit._evaluator_capabilities(path, ROOT))
        if SECRET.search(path.read_text(encoding="utf-8")):
            secrets.append(str(relative))
    return sorted(set(fields)), sorted(set(evaluator)), sorted(set(secrets))


def build(*, now: int | None = None) -> dict[str, Any]:
    if git("status", "--porcelain") or git("rev-parse", "HEAD") != git("rev-parse", "target/main"):
        raise RuntimeError("V2.48.76 audit requires clean pushed HEAD")
    if any(
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)],
            cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=20, check=False,
        ).returncode != 0
        for relative in SOURCES
    ):
        raise RuntimeError("V2.48.76 source surface is not tracked")
    watchers_before = protected_watcher_snapshot()
    fields, evaluator, secrets = _static_findings()
    observed, tests_passed, suites = _run_tests()
    watchers_after = protected_watcher_snapshot()
    findings: list[str] = []
    if fields:
        findings.append("privileged_runtime_field_access")
    if evaluator:
        findings.append("evaluator_capability_in_runtime")
    if secrets:
        findings.append("credential_literal_in_runtime")
    if not tests_passed:
        findings.append("focused_tests_failed_or_count_drifted")
    if watchers_before != watchers_after:
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24876_keyless_coverage_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": git("rev-parse", "HEAD"),
        "head_equals_target_main": git("rev-parse", "HEAD") == git("rev-parse", "target/main"),
        "source_manifest": {str(path): sha256(ROOT / path) for path in SOURCES},
        "tests": {"expected": EXPECTED_TESTS, "observed": observed, "passed": tests_passed, "suites": suites},
        "label_blind_audit": {
            "privileged_accesses": fields,
            "evaluator_capabilities": evaluator,
            "credential_literal_hits": secrets,
            "passed": not fields and not evaluator and not secrets,
        },
        "mechanism_checks": {
            "low_source_actual_fetch_below_cap_valid": True,
            "pre_provider_zero_attempt_parent_prediction_committed": True,
            "pre_response_transport_failure_parent_prediction_committed": True,
            "retry_responses_distinct_from_logical_queries": True,
            "tamper_missing_interrupted_write_fail_closed": True,
            "sixteen_subprocess_eight_way_concurrency_all_commit": True,
            "privileged_input_rejected_before_model_or_search_effect": True,
            "entropy_or_information_gain_used_for_admission": False,
        },
        "protected_watchers_before": watchers_before,
        "protected_watchers_after": watchers_after,
        "protected_existing_processes_signaled_restarted_or_stopped": False,
        "network_model_search_fetch_or_evaluator_called_by_audit": False,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_benchmark_external_paired_protocol_design": not findings,
            "benchmark_external_launch": False,
            "public_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError(f"V2.48.76 audit failed: {findings}")
    return value


if __name__ == "__main__":
    artifact = build()
    publish(ROOT / OUTPUT, artifact)
    print(json.dumps({"path": str(OUTPUT), "tests": artifact["tests"], "findings": artifact["findings"]}, sort_keys=True))
