#!/usr/bin/env python3
"""Preactivation audit for the V2.46.37 external forward."""

from __future__ import annotations

import ast
import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24637_external_contract import (  # noqa: E402
    ACTIVATION, EXECUTION_START, FORWARD_RESULT, OUTPUT_ROOT, PREAUDIT, PROTOCOL,
    PROTOCOL_ID, payload_sha256, protected_watcher_snapshot, sha256,
)
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402


SECRET_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9])(?:gh" + "p_|github_" + "pat_)[A-Za-z0-9_-]{16,}"),
    re.compile(r"(?<![A-Za-z0-9])tvly-" + "dev-[A-Za-z0-9_-]{16,}"),
    re.compile(r"(?<![A-Za-z0-9])s" + "k-[A-Za-z0-9_-]{16,}"),
)
FORBIDDEN_FORWARD_IMPORTS = ("v24637_external_evaluator", "run_official_eval_local")
FORWARD_FILES = (
    "src/deepwide_agent/v24637_objective_alignment_runtime.py",
    "src/deepwide_agent/v24637_external_contract.py",
    "scripts/run_v24637_objective_alignment_task.py",
    "scripts/run_v24637_objective_alignment.py",
)


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.37 audit expected an object")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    output = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            output.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            output.append(node.module or "")
    return output


def _test() -> bool:
    completed = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(ROOT / "tests/test_v24637_objective_alignment.py"), "-v"],
        cwd=ROOT, env={"HOME": str(Path.home()), "USER": os.environ.get("USER", "azureuser"), "LOGNAME": os.environ.get("LOGNAME", "azureuser"), "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1"},
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        timeout=120, check=False,
    )
    return completed.returncode == 0


def build(*, now: int | None = None) -> dict[str, Any]:
    protocol = _read(ROOT / PROTOCOL)
    findings: list[str] = []
    if protocol.get("protocol_id") != PROTOCOL_ID or not _sealed(protocol, "protocol_sha256"):
        findings.append("protocol_invalid")
    manifest = protocol.get("dependency_manifest", {})
    if not isinstance(manifest, dict) or any(sha256(ROOT / path) != digest for path, digest in manifest.items()):
        findings.append("dependency_manifest_drifted")
    future_pristine = all(not (ROOT / path).exists() and not (ROOT / path).is_symlink() for path in (ACTIVATION, EXECUTION_START, FORWARD_RESULT, OUTPUT_ROOT))
    if not future_pristine:
        findings.append("future_surface_not_pristine")
    source_text = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in manifest)
    secret_free = not any(pattern.search(source_text) for pattern in SECRET_PATTERNS)
    if not secret_free:
        findings.append("credential_literal_present")
    imports = {path: _imports(ROOT / path) for path in FORWARD_FILES}
    evaluator_absent = not any(any(marker in name for marker in FORBIDDEN_FORWARD_IMPORTS) for names in imports.values() for name in names)
    gold_literal_absent = all("evaluation/v24637_ourairports_gold" not in (ROOT / path).read_text(encoding="utf-8") and "OURAIRPORTS_" not in (ROOT / path).read_text(encoding="utf-8") for path in FORWARD_FILES)
    if not evaluator_absent or not gold_literal_absent:
        findings.append("forward_evaluator_or_gold_capability_present")
    tests = _test()
    if not tests:
        findings.append("focused_tests_failed")
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=1):
            endpoint = True
    except OSError:
        endpoint = False
        findings.append("gpt56_endpoint_unreachable")
    lease = lease_observation(ROOT, Path("/proc"))
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    watchers = protected_watcher_snapshot()
    if watchers != protocol.get("execution", {}).get("protected_watchers"):
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24637_objective_alignment_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "checks": {
            "protocol_valid_and_sealed": "protocol_invalid" not in findings,
            "dependency_manifest_live": "dependency_manifest_drifted" not in findings,
            "future_surface_pristine": future_pristine,
            "focused_tests_passed": tests,
            "forward_evaluator_import_or_call_capability_absent": evaluator_absent,
            "forward_gold_path_snapshot_or_parser_capability_absent": gold_literal_absent,
            "credential_literal_absent": secret_free,
            "gpt56_endpoint_reachable_without_provider_request": endpoint,
            "shared_api_lease_inactive": lease.get("active") is False,
            "protected_watchers_unchanged": watchers == protocol.get("execution", {}).get("protected_watchers"),
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        },
        "protected_watchers": watchers,
        "findings": findings,
        "audit_valid": not findings,
        "launch_authorized": not findings,
        "protocol_file_sha256": sha256(ROOT / PROTOCOL),
        "authorization": {"one_external_forward_launch": not findings, "evaluator": False, "dev64": False, "exact220": False},
    }
    value["audit_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.46.37 preactivation audit failed: " + ",".join(findings))
    return value


def publish(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    value = build()
    publish(ROOT / PREAUDIT, value)
    print(json.dumps({"audit_valid": value["audit_valid"], "findings": value["findings"]}, sort_keys=True))
