#!/usr/bin/env python3
"""Clean-build audit for the V2.49.13 cap-bound long-page candidate."""

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

from deepwide_agent import v24913_cap_bound_long_page_fetch as fetch  # noqa: E402
from deepwide_agent import v24913_observable_long_page_packer as packer  # noqa: E402
from scripts.audit_v24635_exact220 import (  # noqa: E402
    _accesses,
    _evaluator_capabilities,
)


DATE = "20260808"
OUTPUT = Path(f"results/v24913_cap_bound_long_page_build_audit_v1_{DATE}.json")
PARENT = Path(f"results/v24912_v24911_nonengagement_diagnosis_v1_{DATE}.json")
SOURCE_FILES = (
    Path("src/deepwide_agent/v24913_cap_bound_long_page_fetch.py"),
    Path("scripts/run_v24913_long_page_fetch_helper.py"),
    Path("src/deepwide_agent/v24913_observable_long_page_packer.py"),
    Path("src/deepwide_agent/v24913_long_page_runtime_binding.py"),
    Path("scripts/run_v24913_cap_bound_long_page_task.py"),
    Path("tests/test_v24913_cap_bound_long_page_fetch.py"),
    Path("tests/test_v24913_observable_long_page_packer.py"),
    Path("tests/test_v24913_long_page_runtime_binding.py"),
    Path("scripts/audit_v24913_cap_bound_long_page_build.py"),
)
PURE_FILES = (
    Path("src/deepwide_agent/v24913_observable_long_page_packer.py"),
)
TESTS = (
    ("test_v24913_cap_bound_long_page_fetch.py", 6),
    ("test_v24913_observable_long_page_packer.py", 5),
    ("test_v24913_long_page_runtime_binding.py", 5),
    ("test_v24911_long_page_evidence_packer.py", 12),
    ("test_v24468_total_wall_transport.py", 8),
    ("test_v24316_deadline_search.py", 7),
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
PURE_DANGEROUS_CALLS = {"open", "eval", "exec", "compile", "__import__"}


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.49.13 expected ordinary file: {relative}")
    return path


def _sha(relative: Path) -> str:
    return hashlib.sha256(_ordinary(relative).read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


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


def _pure_ast(relative: Path) -> dict[str, list[str]]:
    source = _ordinary(relative).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(relative))
    imports: list[str] = []
    calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(
                alias.name
                for alias in node.names
                if alias.name.split(".")[0] in PURE_DANGEROUS_IMPORTS
            )
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".")[0]
            if module in PURE_DANGEROUS_IMPORTS:
                imports.append(node.module or "")
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in PURE_DANGEROUS_CALLS
        ):
            calls.append(f"{node.func.id}:{node.lineno}")
    return {"dangerous_imports": sorted(set(imports)), "dangerous_calls": sorted(set(calls))}


def _page(content: str) -> dict[str, str]:
    return {
        "title": "official",
        "url": "https://official.example/data",
        "content": content,
    }


def build(*, now: int | None = None) -> dict[str, Any]:
    parent = json.loads(_ordinary(PARENT).read_text(encoding="utf-8"))
    parent_unsigned = dict(parent)
    parent_seal = parent_unsigned.pop("diagnosis_payload_sha256", None)
    parent_valid = (
        parent.get("role")
        == "v24912_v24911_long_page_nonengagement_aggregate_diagnosis"
        and parent.get("diagnosis_valid") is True
        and parent.get("findings") == []
        and parent.get("authorization", {}).get(
            "fetch_cap_binding_and_projection_receipt_build"
        )
        is True
        and parent_seal == packer.parent.payload_sha256(parent_unsigned)
    )
    tests = [_run_test(name, expected) for name, expected in TESTS]
    accesses: list[str] = []
    evaluator: list[str] = []
    secrets: list[str] = []
    for relative in SOURCE_FILES:
        path = _ordinary(relative)
        if path.suffix == ".py":
            accesses.extend(_accesses(path, ROOT))
            evaluator.extend(_evaluator_capabilities(path, ROOT))
        if SECRET.search(path.read_text(encoding="utf-8")):
            secrets.append(str(relative))
    allowed_forbidden_literal_accesses: set[str] = set()
    unexpected_accesses = sorted(set(accesses) - allowed_forbidden_literal_accesses)
    pure_ast = {str(path): _pure_ast(path) for path in PURE_FILES}
    question = (
        "Return one table with columns: Country | Target Metric.\n"
        "<COUNTRIES>Omega Republic [OMG]</COUNTRIES>"
    )
    long = packer.build_observable_packing(
        question,
        [_page("boilerplate " * 600 + "\nOmega Republic [OMG]: 999")],
    )
    short = packer.build_observable_packing(
        question, [_page("Omega Republic [OMG]: 999")]
    )
    accepted = fetch.validate_fetch_result(
        {"status": "ok", "url": "", "title": "", "text": "x" * 12_000, "links": []}
    )
    rejected = False
    try:
        fetch.validate_fetch_result(
            {"status": "ok", "url": "", "title": "", "text": "x" * 12_001, "links": []}
        )
    except ValueError:
        rejected = True
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    status = _git("status", "--porcelain")
    checks = {
        "tracked_clean_pushed_head": not status and head == remote,
        "parent_nonengagement_diagnosis_valid": parent_valid,
        "focused_tests_exact53": all(item["passed"] for item in tests)
        and sum(item["observed"] for item in tests) == 53,
        "runtime_privileged_field_access_zero": not unexpected_accesses,
        "runtime_evaluator_capability_zero": not evaluator,
        "source_secret_literal_zero": not secrets,
        "pure_packer_has_no_io_network_process_model_or_dynamic_execution": all(
            not report["dangerous_imports"] and not report["dangerous_calls"]
            for report in pure_ast.values()
        ),
        "transport_fetch_cap_accepts_exact_12000": len(accepted["text"]) == 12_000,
        "transport_fetch_cap_rejects_12001": rejected,
        "long_page_mechanism_engaged": long["content_free_receipt"][
            "long_page_mechanism_engaged"
        ]
        is True,
        "late_visible_evidence_recovered": "Omega Republic [OMG]: 999"
        in long["projection"],
        "short_page_byte_identity_preserved": short["content_free_receipt"][
            "short_page_content_byte_identity_preserved"
        ]
        is True,
        "projection_receipt_content_free": short["content_free_receipt"][
            "contains_question_query_url_host_page_content_projection_hash_opaque_id_or_credential"
        ]
        is False,
        "entropy_credit_zero": long["content_free_receipt"][
            "entropy_or_information_gain_assigns_credit"
        ]
        is False,
    }
    manifest = {str(path): _sha(path) for path in (*SOURCE_FILES, PARENT)}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24913_cap_bound_long_page_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"path": str(PARENT), "sha256": _sha(PARENT)},
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "worktree_clean": not status,
        },
        "source_manifest": manifest,
        "source_manifest_sha256": packer.parent.payload_sha256(manifest),
        "tests": tests,
        "runtime_semantic_audit": {
            "privileged_runtime_field_accesses": unexpected_accesses,
            "evaluator_capabilities": evaluator,
            "credential_literal_hits": secrets,
        },
        "pure_component_ast_audit": pure_ast,
        "content_free_mechanism": {
            "fetch_input_cap": 12_000,
            "active_output_per_page_cap": 5_000,
            "long_input_characters_beyond_output_page_cap": long[
                "content_free_receipt"
            ]["input_characters_beyond_output_page_cap"],
            "long_page_mechanism_engaged": long["content_free_receipt"][
                "long_page_mechanism_engaged"
            ],
            "short_page_identity_count": short["content_free_receipt"][
                "short_page_identity_count"
            ],
            "receipt_contains_private_content": False,
        },
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "audit_valid": all(checks.values()),
        "source_policy": {
            "runtime_inputs_visible_question_and_same_forward_fetched_pages_only": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_historical_result_read": False,
            "additional_search_fetch_model_call_or_wall_cap": False,
            "entropy_or_information_gain_assigns_credit": False,
        },
        "authorization": {
            "benchmark_external_shared_prefix_gate_design": all(checks.values()),
            "external_gate_launch": False,
            "public_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = packer.parent.payload_sha256(value)
    return value


def publish(path: Path, value: dict[str, Any]) -> None:
    target = ROOT / path
    if target.exists() or target.is_symlink():
        raise FileExistsError(target)
    descriptor = os.open(
        target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    report = build()
    if report["findings"]:
        raise RuntimeError(f"V2.49.13 audit rejected: {report['findings']}")
    publish(OUTPUT, report)
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
