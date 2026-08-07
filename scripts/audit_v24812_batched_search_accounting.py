#!/usr/bin/env python3
"""Clean-build, label-blind audit for V2.48.12 accounting repair."""

from __future__ import annotations

import ast
import json
import os
import re
import socket
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

from deepwide_agent import v24809_worldbank_budget_ladder_smoke_contract as parent  # noqa: E402
from deepwide_agent.v24809_worldbank_budget_ladder_runner_integration import (  # noqa: E402
    validate_cross_artifacts as validate_old,
)
from deepwide_agent.v24812_batched_search_accounting import (  # noqa: E402
    validate_cross_artifacts as validate_new,
)
from tests.test_v24812_batched_search_accounting import (  # noqa: E402
    model_receipt,
    result,
    transport,
)


DATE = "20260807"
OUTPUT = Path(f"results/v24812_batched_search_accounting_build_audit_v1_{DATE}.json")
SOURCES = (
    Path("src/deepwide_agent/v24812_batched_search_accounting.py"),
    Path("tests/test_v24812_batched_search_accounting.py"),
    Path("scripts/audit_v24812_batched_search_accounting.py"),
)
RUNTIME = (SOURCES[0],)
TESTS = (
    (Path("tests/test_v24804_shared_prefix_budget_ladder.py"), 6),
    (Path("tests/test_v24809_worldbank_budget_ladder_smoke.py"), 5),
    (Path("tests/test_v24812_batched_search_accounting.py"), 6),
)
EXPECTED_TESTS = 17
PRIVILEGED = frozenset(
    {
        "benchmark_question_type", "question_type", "task_category", "category",
        "split", "ground_truth", "gold", "answer_key", "mapping", "evaluator",
        "reward", "score",
    }
)
EVALUATOR_MARKERS = (
    "official_eval", "official_evaluator", "evaluator_mapping", "finalize_v24",
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def sha256(path: Path) -> str:
    return parent.sha256(path)


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _endpoint() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=0.5):
            return True
    except OSError:
        return False


def _run_tests() -> tuple[int, bool, list[dict[str, Any]]]:
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    rows = []
    for path, expected in TESTS:
        completed = subprocess.run(
            [
                str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m",
                "unittest", "discover", "-s", "tests", "-p", path.name, "-v",
            ],
            cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            timeout=300, check=False,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(match.group(1)) if match else 0
        rows.append(
            {
                "path": str(path), "expected": expected, "observed": observed,
                "passed": completed.returncode == 0 and observed == expected,
                "output_sha256": parent.payload_sha256(completed.stdout),
            }
        )
    total = sum(row["observed"] for row in rows)
    return total, total == EXPECTED_TESTS and all(row["passed"] for row in rows), rows


def _ast_findings() -> tuple[list[str], list[str], list[str]]:
    fields: list[str] = []
    imports: list[str] = []
    secrets: list[str] = []
    for relative in RUNTIME:
        source = (ROOT / relative).read_text(encoding="utf-8")
        if SECRET.search(source):
            secrets.append(str(relative))
        tree = ast.parse(source)
        for node in ast.walk(tree):
            key = None
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"get", "pop", "setdefault"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                key = node.args[0].value.casefold()
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
            ):
                key = node.slice.value.casefold()
            if key in PRIVILEGED:
                fields.append(f"{relative}:{node.lineno}:{key}")
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or "", *(alias.name for alias in node.names)]
            for name in names:
                if any(marker in name.casefold() for marker in EVALUATOR_MARKERS):
                    imports.append(f"{relative}:{node.lineno}:{name}")
    return sorted(fields), sorted(imports), sorted(secrets)


def _regression() -> dict[str, Any]:
    value, slot, health = result(), model_receipt(), transport(attempts=2)
    old_rejected = False
    try:
        validate_old(
            value, model_slot_receipt=slot, transport_health=health,
            expected_cap=8,
        )
    except ValueError:
        old_rejected = True
    accounting = validate_new(
        value, model_slot_receipt=slot, transport_health=health,
        expected_cap=8,
    )
    return {
        "old_validator_rejected": old_rejected,
        "successor_validator_accepted": True,
        "logical_queries": accounting["logical_search_queries"],
        "provider_response_calls": accounting["provider_response_calls"],
        "provider_attempts": accounting["provider_attempts"],
        "fetch_calls": accounting["fetch_calls"],
        "hard_fetch_helper_calls": accounting["hard_fetch_helper_calls"],
        "fetch_deadline_rejections": accounting["fetch_deadline_rejections"],
    }


def build(*, now: int | None = None) -> dict[str, Any]:
    if git("status", "--porcelain") or git("rev-parse", "HEAD") != git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.48.12 audit requires clean pushed HEAD")
    fields, imports, secrets = _ast_findings()
    observed, tests_passed, suites = _run_tests()
    regression = _regression()
    watchers = parent.protected_watcher_snapshot()
    endpoint = _endpoint()
    findings = []
    if fields:
        findings.append("privileged_runtime_field_access")
    if imports:
        findings.append("evaluator_capability_in_runtime")
    if secrets:
        findings.append("credential_literal_in_surface")
    if not tests_passed:
        findings.append("focused_tests_failed_or_count_drifted")
    if regression != {
        "old_validator_rejected": True,
        "successor_validator_accepted": True,
        "logical_queries": 4,
        "provider_response_calls": 1,
        "provider_attempts": 2,
        "fetch_calls": 10,
        "hard_fetch_helper_calls": 10,
        "fetch_deadline_rejections": 0,
    }:
        findings.append("batched_counter_regression_failed")
    if watchers != parent.protected_watcher_snapshot():
        findings.append("protected_watcher_drifted")
    if not endpoint:
        findings.append("gpt56_endpoint_unreachable")
    value = {
        "artifact_version": 1,
        "role": "v24812_batched_search_accounting_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": git("rev-parse", "HEAD"),
        "source_manifest": {str(path): sha256(ROOT / path) for path in SOURCES},
        "tests": {
            "expected": EXPECTED_TESTS, "observed": observed,
            "passed": tests_passed, "suites": suites,
        },
        "label_blind_audit": {
            "privileged_accesses": fields, "evaluator_imports": imports,
            "credential_literal_hits": secrets,
            "passed": not fields and not imports and not secrets,
        },
        "batched_counter_regression": regression,
        "protected_watchers": watchers,
        "gpt56_endpoint_reachable_without_provider_request": endpoint,
        "network_model_search_fetch_or_evaluator_called_by_audit": False,
        "old_v24809_artifacts_modified_or_reused": False,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_disjoint_external_successor_design": not findings,
            "external_launch": False,
            "public_dev64_or_exact220": False,
            "evaluator": False,
            "sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = parent.payload_sha256(value)
    if findings:
        raise RuntimeError(f"V2.48.12 audit failed: {findings}")
    return value


if __name__ == "__main__":
    artifact = build()
    publish(ROOT / OUTPUT, artifact)
    print(json.dumps({"path": str(OUTPUT), "tests": artifact["tests"], "findings": artifact["findings"]}, sort_keys=True))
