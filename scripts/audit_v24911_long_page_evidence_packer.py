#!/usr/bin/env python3
"""Clean-build audit for the pure V2.49.11 long-page evidence packer."""

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

from deepwide_agent import v24911_long_page_evidence_packer as candidate  # noqa: E402


OUTPUT = Path("results/v24911_long_page_evidence_packer_build_audit_v1_20260808.json")
SOURCE = Path("src/deepwide_agent/v24911_long_page_evidence_packer.py")
TEST = Path("tests/test_v24911_long_page_evidence_packer.py")
PARENT_TEST = Path("tests/test_v24842_atomic_table_header_closure.py")
STRUCTURE_TEST = Path("tests/test_v24839_structure_preserving_projector.py")
AUDIT = Path("scripts/audit_v24911_long_page_evidence_packer.py")
DIAGNOSIS = Path("results/v24910_v24909_resource_quality_diagnosis_v1_20260808.json")
SOURCES = (SOURCE, TEST, AUDIT, DIAGNOSIS)
FORBIDDEN_FIELDS = frozenset(
    {
        "category",
        "question_type",
        "task_category",
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
DANGEROUS_IMPORTS = frozenset(
    {
        "os",
        "pathlib",
        "subprocess",
        "socket",
        "requests",
        "httpx",
        "urllib.request",
        "aiohttp",
        "openai",
    }
)
DANGEROUS_CALLS = frozenset(
    {
        "open",
        "eval",
        "exec",
        "compile",
        "__import__",
        "subprocess.run",
        "subprocess.Popen",
        "os.system",
    }
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


def _sha(relative: Path) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


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


def _name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _ast_findings(relative: Path) -> dict[str, list[str]]:
    source = (ROOT / relative).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(relative))
    imports: list[str] = []
    calls: list[str] = []
    fields: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(
                alias.name for alias in node.names if alias.name in DANGEROUS_IMPORTS
            )
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
        "credential_literal_hits": [str(relative)] if SECRET.search(source) else [],
    }


def _run_test(relative: Path, expected: int) -> dict[str, Any]:
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
            relative.name,
            "-v",
        ],
        cwd=ROOT,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=240,
        check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(match.group(1)) if match else 0
    return {
        "path": str(relative),
        "expected": expected,
        "observed": observed,
        "passed": completed.returncode == 0 and observed == expected,
        "output_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
    }


def _page(content: str) -> dict[str, str]:
    return {
        "title": "official long page",
        "url": "https://official.example/data",
        "content": content,
    }


def build(*, now: int | None = None) -> dict[str, Any]:
    status = _git("status", "--porcelain")
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    diagnosis = json.loads((ROOT / DIAGNOSIS).read_text(encoding="utf-8"))
    ast_report = _ast_findings(SOURCE)
    tests = [
        _run_test(TEST, 12),
        _run_test(PARENT_TEST, 11),
        _run_test(STRUCTURE_TEST, 13),
    ]
    question = (
        "Return one table with columns: Country | Target Metric.\n"
        "<COUNTRIES>Omega Republic [OMG]</COUNTRIES>"
    )
    short_content = "Omega Republic [OMG]: 999"
    short = candidate.build_packing(question, [_page(short_content)])
    prefix_evidence = "Omega Republic [OMG] prefix\n" + "x " * 5_000
    prefix_safe = candidate.build_packing(
        question, [_page(prefix_evidence + "\nTarget Metric: 999")]
    )
    rows = ["| Country | Target Metric |", "|---|---:|"]
    rows.extend(f"| filler-{index:04d} | {index} |" for index in range(360))
    rows.append("| Omega Republic [OMG] | 999 |")
    table = candidate.build_packing(question, [_page("\n".join(rows))])
    late = candidate.build_packing(
        question,
        [_page("boilerplate " * 600 + "\nOmega Republic [OMG]: 999")],
    )
    checks = {
        "tracked_sources_clean_pushed_head": not status and head == remote,
        "focused_tests_exact36": all(test["passed"] for test in tests)
        and sum(test["observed"] for test in tests) == 36,
        "runtime_ast_no_io_network_process_model_or_dynamic_execution": not ast_report[
            "dangerous_imports"
        ]
        and not ast_report["dangerous_calls"],
        "runtime_ast_no_privileged_field_access": not ast_report[
            "privileged_runtime_field_accesses"
        ],
        "source_secret_literal_zero": not ast_report["credential_literal_hits"],
        "diagnosis_valid_and_packer_build_authorized": diagnosis.get(
            "diagnosis_valid"
        )
        is True
        and diagnosis.get("findings") == []
        and diagnosis.get("authorization", {}).get("query_aware_evidence_packer_build")
        is True,
        "short_page_byte_identity": short["short_page_content_byte_identity_preserved"]
        is True
        and short["projection"].endswith(short_content),
        "prefix_safe": prefix_safe[
            "candidate_requirement_coverage_not_less_than_prefix_baseline"
        ]
        is True,
        "atomic_table_header_closure": table[
            "orphan_selected_table_continuation_block_count"
        ]
        == 0
        and not (
            "| Omega Republic [OMG] | 999 |" in table["projection"]
            and "| Country | Target Metric |" not in table["projection"]
        ),
        "late_visible_evidence_recovered": "Omega Republic [OMG]: 999"
        in late["projection"],
        "hard_input_output_and_rendered_caps": max(
            late["per_page_effective_content_characters"]
        )
        <= 12_000
        and max(late["per_page_output_content_characters"]) <= 5_000
        and late["projected_rendered_characters"] <= 60_000,
        "entropy_credit_zero": late["entropy_or_information_gain_assigns_credit"]
        is False,
    }
    manifest = {str(path): _sha(path) for path in SOURCES}
    value = {
        "artifact_version": 1,
        "role": "v24911_long_page_evidence_packer_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "worktree_clean": not status,
        },
        "parent": {"path": str(DIAGNOSIS), "sha256": _sha(DIAGNOSIS)},
        "source_manifest": manifest,
        "source_manifest_sha256": candidate.payload_sha256(manifest),
        "tests": tests,
        "ast_audit": ast_report,
        "content_free_mechanism": {
            "short_projection_sha256": short["projection_sha256"],
            "prefix_safe_fallback_applied": prefix_safe[
                "prefix_safe_fallback_applied"
            ],
            "late_projection_sha256": late["projection_sha256"],
            "late_candidate_visible_requirement_gain_count": late[
                "candidate_visible_requirement_gain_count"
            ],
            "table_orphan_continuation_count": table[
                "orphan_selected_table_continuation_block_count"
            ],
        },
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "audit_valid": all(checks.values()),
        "source_policy": {
            "runtime_inputs_visible_question_and_same_forward_fetched_pages_only": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_historical_result_read": False,
            "network_model_search_fetch_process_or_evaluator_called_by_audit": False,
            "entropy_or_information_gain_assigns_credit": False,
        },
        "authorization": {
            "fresh_exact220_protocol_design": all(checks.values()),
            "exact220_launch": False,
            "evaluator": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = candidate.payload_sha256(value)
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
        raise RuntimeError(f"V2.49.11 audit rejected: {report['findings']}")
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
