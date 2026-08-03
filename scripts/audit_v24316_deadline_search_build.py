#!/usr/bin/env python3
"""Build-only audit for the benchmark-external V2.43.16 search deadline fix."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24315_forward_contract import (  # noqa: E402
    payload_sha256,
    protected_watcher_snapshot,
)


SOURCE = Path("src/deepwide_agent/v24316_deadline_search.py")
TEST = Path("tests/test_v24316_deadline_search.py")
FIXTURE = Path("tests/fixtures/v24316_slow_fetch_child.py")
PROBE_SCRIPT = Path("scripts/probe_v24316_deadline_search.py")
INVALIDATION_SCRIPT = Path("scripts/invalidate_v24316_deadline_search_build_v1.py")
V2_INVALIDATION_SCRIPT = Path("scripts/invalidate_v24316_deadline_search_build_v2.py")
PROBE = Path("results/v24316_deadline_search_probe_v2_20260803.json")
V1_AUDIT = Path("results/v24316_deadline_search_build_audit_v1_20260803.json")
V1_INVALIDATION = Path(
    "results/v24316_deadline_search_build_audit_v1_invalidation_20260803.json"
)
V2_AUDIT = Path("results/v24316_deadline_search_build_audit_v2_20260803.json")
V2_INVALIDATION = Path(
    "results/v24316_deadline_search_build_audit_v2_invalidation_20260803.json"
)
AUDIT = Path("results/v24316_deadline_search_build_audit_v3_20260803.json")
V24315_START = Path("results/v24315_exact220_execution_start_v1_20260803.json")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
FORBIDDEN_FIELDS = frozenset(
    {
        "question_type",
        "task_category",
        "category",
        "split",
        "ground_truth",
        "gold",
        "answer_key",
        "mapping",
        "evaluator",
        "score",
        "reward",
    }
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ordinary(relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.43.16 audit path is noncanonical")
    path = ROOT / relative
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
        raise RuntimeError(f"V2.43.16 expected ordinary file: {relative}")
    return path


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.43.16 expected JSON object: {relative}")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _field_accesses(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    output: list[str] = []
    for node in ast.walk(tree):
        key = None
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            key = node.args[0].value
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            key = node.slice.value
        if key is not None and key.casefold() in FORBIDDEN_FIELDS:
            output.append(f"{path.relative_to(ROOT)}:{node.lineno}:{key}")
    return output


def _current_runner_identity() -> dict[str, Any]:
    start = _read(V24315_START)
    runner = start.get("runner") or {}
    pid = runner.get("pid")
    marker = runner.get("marker")
    expected_ticks = runner.get("start_ticks")
    if not isinstance(pid, int) or not isinstance(marker, str) or not isinstance(expected_ticks, int):
        raise RuntimeError("V2.43.16 V2.43.15 runner identity is absent")
    stat_path = Path("/proc") / str(pid) / "stat"
    cmdline_path = Path("/proc") / str(pid) / "cmdline"
    if not stat_path.is_file() or not cmdline_path.is_file():
        return {
            "pid": pid,
            "marker": marker,
            "start_ticks": expected_ticks,
            "currently_present": False,
            "identity_matches": False,
        }
    raw = stat_path.read_text(encoding="utf-8")
    fields = raw[raw.rfind(")") + 2 :].split()
    command = cmdline_path.read_bytes().replace(b"\x00", b" ").decode(
        "utf-8", errors="replace"
    )
    live_ticks = int(fields[19])
    return {
        "pid": pid,
        "marker": marker,
        "start_ticks": expected_ticks,
        "currently_present": True,
        "identity_matches": live_ticks == expected_ticks and marker in command,
    }


def build_report(*, now: int | None = None) -> dict[str, Any]:
    files = (
        SOURCE,
        TEST,
        FIXTURE,
        PROBE_SCRIPT,
        INVALIDATION_SCRIPT,
        V2_INVALIDATION_SCRIPT,
    )
    manifest = {str(relative): sha256(_ordinary(relative)) for relative in files}
    sources = {str(relative): _ordinary(relative).read_text(encoding="utf-8") for relative in files}
    secret_hits = sorted(relative for relative, source in sources.items() if SECRET.search(source))
    accesses = sorted(
        access
        for relative in (SOURCE, PROBE_SCRIPT)
        for access in _field_accesses(ROOT / relative)
    )
    probe = _read(PROBE)
    v1_audit = _read(V1_AUDIT)
    invalidation = _read(V1_INVALIDATION)
    v2_audit = _read(V2_AUDIT)
    v2_invalidation = _read(V2_INVALIDATION)
    runner = _current_runner_identity()
    watchers = protected_watcher_snapshot()
    completed = subprocess.run(
        [
            str(ROOT / ".venv-eval/bin/python"),
            "-I",
            "-B",
            str(ROOT / TEST),
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
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=60,
        check=False,
    )
    findings: list[str] = []
    if accesses:
        findings.append("privileged_field_access_in_runtime_surface")
    if secret_hits:
        findings.append("credential_literal_in_build_surface")
    if completed.returncode != 0:
        findings.append("focused_tests_failed")
    if (
        v1_audit.get("audit_valid") is not False
        or v1_audit.get("findings") != ["focused_tests_failed"]
        or not _sealed(v1_audit, "audit_payload_sha256")
        or invalidation.get("role")
        != "v24316_deadline_search_build_audit_v1_invalidation"
        or invalidation.get("invalidated_artifact")
        != {"path": str(V1_AUDIT), "sha256": sha256(ROOT / V1_AUDIT)}
        or invalidation.get("v1_audit_valid_claim") is not False
        or invalidation.get("v1_future_integration_authority") is not False
        or invalidation.get("v1_benchmark_launch_authority") is not False
        or not _sealed(invalidation, "invalidation_payload_sha256")
    ):
        findings.append("v1_invalidation_invalid")
    if (
        v2_audit.get("role") != "v24316_deadline_search_build_audit_v2"
        or v2_audit.get("audit_valid") is not True
        or v2_audit.get("findings") != []
        or not _sealed(v2_audit, "audit_payload_sha256")
        or v2_invalidation.get("role")
        != "v24316_deadline_search_build_audit_v2_invalidation"
        or v2_invalidation.get("invalidated_artifact")
        != {"path": str(V2_AUDIT), "sha256": sha256(ROOT / V2_AUDIT)}
        or v2_invalidation.get("v2_audit_valid_claim") is not False
        or v2_invalidation.get("v2_future_integration_authority") is not False
        or v2_invalidation.get("v2_benchmark_launch_authority") is not False
        or not _sealed(v2_invalidation, "invalidation_payload_sha256")
    ):
        findings.append("v2_invalidation_invalid")
    if (
        probe.get("role") != "v24316_deadline_search_benchmark_external_probe_v2"
        or probe.get("source")
        != {"path": str(SOURCE), "sha256": sha256(ROOT / SOURCE)}
        or probe.get("passed") is not True
        or probe.get("findings") != []
        or not _sealed(probe, "report_payload_sha256")
        or probe.get("authorization", {}).get("benchmark_launch") is not False
    ):
        findings.append("benchmark_external_probe_invalid")
    if runner["currently_present"] and not runner["identity_matches"]:
        findings.append("active_v24315_runner_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24316_deadline_search_build_audit_v3",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "probe": {"path": str(PROBE), "sha256": sha256(ROOT / PROBE)},
        "invalidated_v1_audit": {
            "path": str(V1_AUDIT),
            "sha256": sha256(ROOT / V1_AUDIT),
            "invalidation_path": str(V1_INVALIDATION),
            "invalidation_sha256": sha256(ROOT / V1_INVALIDATION),
        },
        "invalidated_v2_audit": {
            "path": str(V2_AUDIT),
            "sha256": sha256(ROOT / V2_AUDIT),
            "invalidation_path": str(V2_INVALIDATION),
            "invalidation_sha256": sha256(ROOT / V2_INVALIDATION),
        },
        "focused_tests": {
            "command": "python -I -B /absolute/repository/tests/test_v24316_deadline_search.py",
            "passed": completed.returncode == 0,
            "test_count": 7,
            "network_model_search_fetch_or_evaluator_called_by_tests": False,
        },
        "privileged_field_accesses": accesses,
        "credential_literal_hits": secret_hits,
        "active_v24315_runner": runner,
        "protected_watchers": watchers,
        "current_v24315_run_signaled_restarted_resumed_rerun_or_modified": False,
        "benchmark_manifest_task_mapping_gold_category_question_type_split_evaluator_score_read": False,
        "network_model_hosted_search_remote_fetch_or_evaluator_called_by_audit": False,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "future_runner_integration_design": not findings,
            "active_v24315_modification": False,
            "benchmark_launch": False,
            "evaluator": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    report = build_report()
    publish_new(ROOT / AUDIT, report)
    print(json.dumps({"path": str(AUDIT), "audit_valid": report["audit_valid"]}, sort_keys=True))
