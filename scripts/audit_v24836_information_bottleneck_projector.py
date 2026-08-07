#!/usr/bin/env python3
"""Clean-build audit for the V2.48.36 pure evidence projector."""

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

from deepwide_agent import v24836_information_bottleneck_projector as projector  # noqa: E402


OUTPUT = Path("results/v24836_information_bottleneck_projector_build_audit_v1_20260807.json")
SOURCE = Path("src/deepwide_agent/v24836_information_bottleneck_projector.py")
TEST = Path("tests/test_v24836_information_bottleneck_projector.py")
AUDIT = Path("scripts/audit_v24836_information_bottleneck_projector.py")
DIAGNOSIS = Path("results/v24835_v24831_v24834_evidence_budget_diagnosis_v1_20260807.json")
SOURCES = (SOURCE, TEST, AUDIT)
FORBIDDEN_FIELDS = frozenset(
    {"category", "question_type", "task_category", "split", "ground_truth", "gold", "answer_key", "mapping", "evaluator", "score", "reward"}
)
DANGEROUS_IMPORTS = frozenset(
    {"os", "subprocess", "socket", "requests", "httpx", "urllib.request", "aiohttp", "openai"}
)
DANGEROUS_CALLS = frozenset(
    {"open", "eval", "exec", "compile", "__import__", "subprocess.run", "subprocess.Popen", "os.system"}
)
SECRET = re.compile(r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}")


def _sha(path: Path) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def _name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _ast_findings(path: Path) -> dict[str, list[str]]:
    source = (ROOT / path).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    imports: list[str] = []
    calls: list[str] = []
    fields: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names if alias.name in DANGEROUS_IMPORTS)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module in DANGEROUS_IMPORTS:
                imports.append(module)
        elif isinstance(node, ast.Call):
            name = _name(node.func)
            if name in DANGEROUS_CALLS:
                calls.append(f"{name}:{node.lineno}")
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in {"get", "pop", "setdefault"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and node.args[0].value.casefold() in FORBIDDEN_FIELDS
            ):
                fields.append(f"{node.args[0].value}:{node.lineno}")
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
            and node.slice.value.casefold() in FORBIDDEN_FIELDS
        ):
            fields.append(f"{node.slice.value}:{node.lineno}")
    return {
        "dangerous_imports": sorted(set(imports)),
        "dangerous_calls": sorted(set(calls)),
        "privileged_runtime_field_accesses": sorted(set(fields)),
        "credential_literal_hits": [str(path)] if SECRET.search(source) else [],
    }


def _tests() -> dict[str, Any]:
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    completed = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest", "discover", "-s", "tests", "-p", TEST.name, "-v"],
        cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        timeout=180, check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(match.group(1)) if match else 0
    return {
        "path": str(TEST),
        "expected": 8,
        "observed": observed,
        "passed": completed.returncode == 0 and observed == 8,
        "output_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
    }


def build(*, now: int | None = None) -> dict[str, Any]:
    status = _git("status", "--porcelain")
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    ast_report = _ast_findings(SOURCE)
    tests = _tests()
    diagnosis = json.loads((ROOT / DIAGNOSIS).read_text(encoding="utf-8"))
    synthetic = projector.build_projection(
        [
            {"title": "one", "url": "https://one.example/a", "content": "A" * 5_000},
            {"title": "two", "url": "https://two.example/b", "content": "B" * 5_000},
            {"title": "three", "url": "https://three.example/c", "content": "C" * 5_000},
        ],
        policy=projector.ProjectionPolicy(
            total_character_cap=3_000,
            minimum_page_prefix_chars=800,
            round_robin_chunk_chars=200,
            maximum_page_chars=5_000,
        ),
    )
    checks = {
        "tracked_sources_clean_pushed_head": not status and head == remote,
        "focused_tests_exact8": tests["passed"],
        "runtime_ast_no_io_network_process_or_dynamic_execution": not ast_report["dangerous_imports"] and not ast_report["dangerous_calls"],
        "runtime_ast_no_privileged_field_access": not ast_report["privileged_runtime_field_accesses"],
        "source_secret_literal_zero": not ast_report["credential_literal_hits"],
        "diagnosis_valid_and_build_only_authorized": diagnosis.get("diagnosis_valid") is True and diagnosis.get("authorization", {}).get("information_bottleneck_projector_build") is True,
        "synthetic_all_three_pages_projected": synthetic["projected_page_count"] == 3,
        "synthetic_equal_round_robin_allocation": synthetic["per_page_allocated_characters"] == [1000, 1000, 1000],
        "synthetic_total_cap_exact": synthetic["allocated_content_characters"] == 3000,
        "entropy_credit_zero": synthetic["entropy_or_information_gain_assigns_credit"] is False,
    }
    value = {
        "artifact_version": 1,
        "role": "v24836_information_bottleneck_projector_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": remote, "head_equals_target_main": head == remote, "worktree_clean": not status},
        "parent": {"path": str(DIAGNOSIS), "sha256": _sha(DIAGNOSIS)},
        "source_manifest": {str(path): _sha(path) for path in SOURCES},
        "source_manifest_sha256": projector.payload_sha256({str(path): _sha(path) for path in SOURCES}),
        "tests": tests,
        "ast_audit": ast_report,
        "synthetic_gate": {
            "input_pages": synthetic["input_page_count"],
            "projected_pages": synthetic["projected_page_count"],
            "allocated_content_characters": synthetic["allocated_content_characters"],
            "per_page_allocated_characters": synthetic["per_page_allocated_characters"],
            "unique_hosts": synthetic["projected_unique_host_count"],
            "host_entropy_nats": synthetic["projected_host_entropy_nats"],
            "projection_sha256": synthetic["projection_sha256"],
        },
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "audit_valid": all(checks.values()),
        "source_policy": {
            "visible_question_or_benchmark_task_read_by_projector": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "network_model_search_fetch_process_or_evaluator_called_by_audit": False,
            "entropy_or_information_gain_assigns_credit": False,
        },
        "authorization": {
            "fresh_benchmark_external_shared_prefix_gate_design": all(checks.values()),
            "fresh_external_activation_or_launch": False,
            "public_dev64_or_exact220": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = projector.payload_sha256(value)
    return value


def publish(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    report = build()
    publish(ROOT / OUTPUT, report)
    print(json.dumps({"path": str(OUTPUT), "audit_valid": report["audit_valid"], "findings": report["findings"], "authorization": report["authorization"]}, sort_keys=True))
