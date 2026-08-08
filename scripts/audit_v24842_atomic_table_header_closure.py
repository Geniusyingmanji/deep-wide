#!/usr/bin/env python3
"""Clean-build audit for the pure V2.48.42 atomic table-header projector."""

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

from deepwide_agent import v24839_structure_preserving_projector as control  # noqa: E402
from deepwide_agent import v24842_atomic_table_header_closure as candidate  # noqa: E402


OUTPUT = Path("results/v24842_atomic_table_header_closure_build_audit_v1_20260808.json")
SOURCE = Path("src/deepwide_agent/v24842_atomic_table_header_closure.py")
TEST = Path("tests/test_v24842_atomic_table_header_closure.py")
PARENT_TEST = Path("tests/test_v24839_structure_preserving_projector.py")
AUDIT = Path("scripts/audit_v24842_atomic_table_header_closure.py")
DIAGNOSIS = Path("results/v24841_four_run_structure_closure_diagnosis_v1_20260808.json")
MATRIX = Path(".research/literature_matrix.md")
SOURCES = (SOURCE, TEST, AUDIT, DIAGNOSIS, MATRIX)
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
                alias.name
                for alias in node.names
                if alias.name in DANGEROUS_IMPORTS
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
        "title": "long official table",
        "url": "https://official.example/table",
        "content": content,
    }


def _long_table() -> str:
    lines = ["| Country | Target Metric |", "|---|---:|"]
    lines.extend(f"| filler-{index:03d} | {index} |" for index in range(60))
    lines.append("| Omega Republic | 999 |")
    return "\n".join(lines)


def build(*, now: int | None = None) -> dict[str, Any]:
    status = _git("status", "--porcelain")
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    diagnosis = json.loads((ROOT / DIAGNOSIS).read_text(encoding="utf-8"))
    ast_report = _ast_findings(SOURCE)
    tests = [_run_test(TEST, 11), _run_test(PARENT_TEST, 13)]
    tight = control.ProjectionPolicy(
        total_character_cap=260,
        maximum_page_chars=260,
        block_character_cap=180,
    )
    fit = control.ProjectionPolicy(
        total_character_cap=320,
        maximum_page_chars=320,
        block_character_cap=180,
    )
    question = "Column names: Country | Target Metric. Return the row for Omega Republic."
    target_only = "Return the row for Omega Republic."
    pages = [_page(_long_table())]
    control_tight = control.build_projection(question, pages, policy=tight)
    candidate_tight = candidate.build_projection(question, pages, policy=tight)
    candidate_fit = candidate.build_projection(target_only, pages, policy=fit)
    non_table = [
        _page("Omega Republic Target Metric: 999\n\nOther independent evidence.")
    ]
    control_non_table = control.build_projection(question, non_table)
    candidate_non_table = candidate.build_projection(question, non_table)
    checks = {
        "tracked_sources_clean_pushed_head": not status and head == remote,
        "focused_tests_exact24": all(test["passed"] for test in tests)
        and sum(test["observed"] for test in tests) == 24,
        "runtime_ast_no_io_network_process_or_dynamic_execution": not ast_report[
            "dangerous_imports"
        ]
        and not ast_report["dangerous_calls"],
        "runtime_ast_no_privileged_field_access": not ast_report[
            "privileged_runtime_field_accesses"
        ],
        "source_secret_literal_zero": not ast_report["credential_literal_hits"],
        "diagnosis_valid_and_build_authorized": diagnosis.get("diagnosis_valid")
        is True
        and diagnosis.get("findings") == []
        and diagnosis.get("authorization", {}).get(
            "table_header_closure_projector_build"
        )
        is True,
        "tight_same_raw_page_vector": control_tight["per_page_content_sha256"]
        == candidate_tight["per_page_content_sha256"],
        "tight_control_reproduces_orphan": "| Omega Republic | 999 |"
        in control_tight["projection"]
        and "| Country | Target Metric |" not in control_tight["projection"],
        "tight_candidate_has_no_orphan": not (
            "| Omega Republic | 999 |" in candidate_tight["projection"]
            and "| Country | Target Metric |" not in candidate_tight["projection"]
        )
        and candidate_tight["orphan_selected_table_continuation_block_count"] == 0,
        "fit_candidate_atomically_retains_header_and_target": "| Omega Republic | 999 |"
        in candidate_fit["projection"]
        and "| Country | Target Metric |" in candidate_fit["projection"]
        and candidate_fit["table_header_dependency_addition_count"] >= 1
        and candidate_fit["orphan_selected_table_continuation_block_count"] == 0,
        "candidate_rendered_caps_hard": candidate_tight[
            "projected_rendered_characters"
        ]
        <= 260
        and candidate_fit["projected_rendered_characters"] <= 320,
        "non_table_projection_byte_identical": control_non_table["projection_sha256"]
        == candidate_non_table["projection_sha256"],
        "entropy_credit_zero": candidate_fit[
            "entropy_or_information_gain_assigns_credit"
        ]
        is False,
    }
    manifest = {str(path): _sha(path) for path in SOURCES}
    value = {
        "artifact_version": 1,
        "role": "v24842_atomic_table_header_closure_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "worktree_clean": not status,
        },
        "parent": {"path": str(DIAGNOSIS), "sha256": _sha(DIAGNOSIS)},
        "literature_grounding": {
            "matrix_path": str(MATRIX),
            "matrix_sha256": _sha(MATRIX),
            "mechanism": "atomic_table_header_dependency_under_fixed_rendered_budget",
            "related_principles": [
                "SIEVE structure-aware section preservation",
                "RubricRanker document-set coverage and evidence utilization",
            ],
        },
        "source_manifest": manifest,
        "source_manifest_sha256": candidate.payload_sha256(manifest),
        "tests": tests,
        "ast_audit": ast_report,
        "synthetic_shared_input": {
            "tight_control_projection_sha256": control_tight["projection_sha256"],
            "tight_candidate_projection_sha256": candidate_tight["projection_sha256"],
            "fit_candidate_projection_sha256": candidate_fit["projection_sha256"],
            "tight_control_rendered_characters": control_tight[
                "projected_rendered_characters"
            ],
            "tight_candidate_rendered_characters": candidate_tight[
                "projected_rendered_characters"
            ],
            "fit_candidate_rendered_characters": candidate_fit[
                "projected_rendered_characters"
            ],
            "fit_dependency_additions": candidate_fit[
                "table_header_dependency_addition_count"
            ],
            "candidate_orphan_continuations": candidate_fit[
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
            "fresh_external_shared_prefix_protocol_design": all(checks.values()),
            "external_launch": False,
            "public_dev64_or_exact220": False,
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
        raise RuntimeError(f"V2.48.42 audit rejected: {report['findings']}")
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
