#!/usr/bin/env python3
"""Clean-build audit for the V2.49.16 prefix-total repair."""

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

from deepwide_agent import v24911_long_page_evidence_packer as seal  # noqa: E402
from deepwide_agent import v24916_prefix_total_long_page_packer as packer  # noqa: E402
from scripts.audit_v24635_exact220 import (  # noqa: E402
    _accesses,
    _evaluator_capabilities,
)


DATE = "20260808"
OUTPUT = Path(f"results/v24916_prefix_total_long_page_build_audit_v1_{DATE}.json")
PARENT = Path(f"results/v24915_v24914_projection_cap_failure_diagnosis_v1_{DATE}.json")
SOURCE_FILES = (
    Path("src/deepwide_agent/v24916_prefix_total_long_page_packer.py"),
    Path("src/deepwide_agent/v24916_prefix_total_runtime_binding.py"),
    Path("scripts/run_v24916_prefix_total_long_page_task.py"),
    Path("tests/test_v24916_prefix_total_long_page_packer.py"),
    Path("tests/test_v24916_prefix_total_runtime_binding.py"),
    Path("scripts/audit_v24916_prefix_total_long_page_build.py"),
)
PURE_FILES = (Path("src/deepwide_agent/v24916_prefix_total_long_page_packer.py"),)
TESTS = (
    ("test_v24916_prefix_total_long_page_packer.py", 6),
    ("test_v24916_prefix_total_runtime_binding.py", 4),
    ("test_v24913_cap_bound_long_page_fetch.py", 6),
    ("test_v24913_observable_long_page_packer.py", 5),
    ("test_v24911_long_page_evidence_packer.py", 12),
    ("test_v24842_atomic_table_header_closure.py", 11),
    ("test_v24635_exact220.py", 10),
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)
PURE_DANGEROUS_IMPORTS = {
    "os",
    "pathlib",
    "socket",
    "subprocess",
    "requests",
    "httpx",
    "aiohttp",
    "openai",
}


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.49.16 expected ordinary file: {relative}")
    return path


def _sha(relative: Path) -> str:
    return hashlib.sha256(_ordinary(relative).read_bytes()).hexdigest()


def _run_test(filename: str, expected: int) -> dict[str, Any]:
    completed = subprocess.run(
        [
            str(ROOT / ".venv-eval/bin/python"),
            "-I",
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            filename,
            "-v",
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
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=300,
        check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(match.group(1)) if match else 0
    return {
        "path": f"tests/{filename}",
        "expected": expected,
        "observed": observed,
        "passed": completed.returncode == 0 and observed == expected,
        "output_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
    }


def _pure_imports(relative: Path) -> list[str]:
    tree = ast.parse(_ordinary(relative).read_text(encoding="utf-8"))
    values = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    values.update(
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    return sorted(values.intersection(PURE_DANGEROUS_IMPORTS))


def build(*, now: int | None = None) -> dict[str, Any]:
    parent = json.loads(_ordinary(PARENT).read_text(encoding="utf-8"))
    unsigned = dict(parent)
    parent_seal = unsigned.pop("diagnosis_payload_sha256", None)
    parent_valid = (
        parent.get("role")
        == "v24915_v24914_projection_cap_failure_aggregate_diagnosis"
        and parent.get("diagnosis_valid") is True
        and parent.get("findings") == []
        and parent.get("authorization", {}).get("prefix_totality_repair_build")
        is True
        and parent_seal == seal.payload_sha256(unsigned)
    )
    tests = [_run_test(name, expected) for name, expected in TESTS]
    accesses: list[str] = []
    evaluator: list[str] = []
    secrets: list[str] = []
    for relative in SOURCE_FILES:
        path = _ordinary(relative)
        accesses.extend(_accesses(path, ROOT))
        evaluator.extend(_evaluator_capabilities(path, ROOT))
        if SECRET.search(path.read_text(encoding="utf-8")):
            secrets.append(str(relative))
    content = (("Entity Value " + "x" * 40) + "\n\n") * 200
    fallback = packer.build_prefix_total_packing(
        "Return one table. Columns: Entity, Value",
        [{"title": "Official", "url": "https://example.invalid/a", "content": content}],
    )
    engaged = packer.build_prefix_total_packing(
        "Return Omega Republic [OMG] Value",
        [
            {
                "title": "Official",
                "url": "https://example.invalid/b",
                "content": "boilerplate " * 600 + "\nOmega Republic [OMG]: 999",
            }
        ],
    )
    fallback_receipt = fallback["content_free_receipt"]
    engaged_receipt = engaged["content_free_receipt"]
    checks = {
        "parent_projection_cap_diagnosis_valid": parent_valid,
        "focused_tests_exact54": all(row["passed"] for row in tests)
        and sum(row["observed"] for row in tests) == 54,
        "runtime_privileged_field_access_zero": not accesses,
        "runtime_evaluator_capability_zero": not evaluator,
        "source_secret_literal_zero": not secrets,
        "pure_packer_has_no_io_network_process_or_model_import": all(
            not _pure_imports(path) for path in PURE_FILES
        ),
        "diagnosed_overflow_is_totalized": fallback_receipt[
            "structural_cap_totality_fallback_applied"
        ]
        is True,
        "fallback_is_exact_stable_5k_prefix": fallback_receipt[
            "fallback_projection_is_exact_stable_5k_prefix"
        ]
        is True,
        "fallback_adds_no_effect": fallback_receipt[
            "additional_search_fetch_model_call_or_wall_cap"
        ]
        is False,
        "nonoverflow_query_aware_mechanism_preserved": engaged_receipt[
            "long_page_mechanism_engaged"
        ]
        is True,
        "entropy_assigns_no_credit": fallback_receipt[
            "entropy_or_information_gain_assigns_credit"
        ]
        is False,
    }
    manifest = {str(path): _sha(path) for path in (*SOURCE_FILES, PARENT)}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24916_prefix_total_long_page_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"path": str(PARENT), "sha256": _sha(PARENT)},
        "source_manifest": manifest,
        "source_manifest_sha256": seal.payload_sha256(manifest),
        "tests": tests,
        "runtime_semantic_audit": {
            "privileged_runtime_field_accesses": sorted(set(accesses)),
            "evaluator_capabilities": sorted(set(evaluator)),
            "credential_literal_hits": sorted(set(secrets)),
        },
        "mechanism": {
            "input_page_cap": 12_000,
            "output_page_cap": 5_000,
            "overflow_fallback_is_exact_prefix": True,
            "unrelated_exception_swallowed": False,
            "query_aware_mechanism_preserved_when_safe": True,
            "additional_network_or_model_effect": False,
        },
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "audit_valid": all(checks.values()),
        "source_policy": {
            "runtime_visible_question_and_same_forward_pages_only": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_historical_result_read": False,
            "entropy_or_information_gain_assigns_credit": False,
        },
        "authorization": {
            "benchmark_external_gate_design": all(checks.values()),
            "external_gate_launch": False,
            "public_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = seal.payload_sha256(value)
    return value


def publish(value: dict[str, Any]) -> None:
    path = ROOT / OUTPUT
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    report = build()
    if report["findings"]:
        raise RuntimeError(f"V2.49.16 audit rejected: {report['findings']}")
    publish(report)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": report["audit_valid"],
                "findings": report["findings"],
                "authorization": report["authorization"],
            },
            sort_keys=True,
        )
    )
