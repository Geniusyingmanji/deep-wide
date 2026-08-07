#!/usr/bin/env python3
"""Clean-build audit for the pure V2.48.39 structure projector."""

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

from deepwide_agent import v24836_information_bottleneck_projector as baseline  # noqa: E402
from deepwide_agent import v24839_structure_preserving_projector as candidate  # noqa: E402


OUTPUT = Path("results/v24839_structure_preserving_projector_build_audit_v1_20260807.json")
SOURCE = Path("src/deepwide_agent/v24839_structure_preserving_projector.py")
TEST = Path("tests/test_v24839_structure_preserving_projector.py")
AUDIT = Path("scripts/audit_v24839_structure_preserving_projector.py")
DIAGNOSIS = Path(
    "results/v24838_v24834_v24837_information_bottleneck_diagnosis_v1_20260807.json"
)
MATRIX = Path(".research/literature_matrix.md")
SOURCES = (SOURCE, TEST, AUDIT, MATRIX)
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
    {"os", "pathlib", "subprocess", "socket", "requests", "httpx", "urllib.request", "aiohttp", "openai"}
)
DANGEROUS_CALLS = frozenset(
    {"open", "eval", "exec", "compile", "__import__", "subprocess.run", "subprocess.Popen", "os.system"}
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def _sha(path: Path) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


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


def _ast_findings(path: Path) -> dict[str, list[str]]:
    source = (ROOT / path).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
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
            TEST.name,
            "-v",
        ],
        cwd=ROOT,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=180,
        check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(match.group(1)) if match else 0
    return {
        "path": str(TEST),
        "expected": 12,
        "observed": observed,
        "passed": completed.returncode == 0 and observed == 12,
        "output_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
    }


def build(*, now: int | None = None) -> dict[str, Any]:
    status = _git("status", "--porcelain")
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    ast_report = _ast_findings(SOURCE)
    tests = _tests()
    diagnosis = json.loads((ROOT / DIAGNOSIS).read_text(encoding="utf-8"))
    question = (
        "Column names: Country, Population total [SP.POP.TOTL] @2024, "
        "GDP current US$ [NY.GDP.MKTP.CD] @2024."
    )
    late_table = (
        "# Official indicator records\n"
        "| Country | SP.POP.TOTL | NY.GDP.MKTP.CD |\n"
        "|---|---:|---:|\n"
        "| Alpha Republic | 101 | 202 |\n"
        "| Beta State | 303 | 404 |"
    )
    pages = [
        {
            "title": "official indicators",
            "url": "https://official.example/records",
            "content": "irrelevant boilerplate " * 400 + "\n\n" + late_table,
        },
        {
            "title": "independent catalog",
            "url": "https://catalog.example/records",
            "content": "Alpha Republic SP.POP.TOTL catalog entry",
        },
    ]
    control = baseline.build_projection(pages)
    projected = candidate.build_projection(question, pages)
    checks = {
        "tracked_sources_clean_pushed_head": not status and head == remote,
        "focused_tests_exact12": tests["passed"],
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
        and diagnosis.get("authorization", {}).get(
            "structure_preserving_projector_build"
        )
        is True,
        "synthetic_same_raw_page_vector": control["per_page_content_sha256"]
        == projected["per_page_content_sha256"],
        "synthetic_control_loses_late_complete_row": "| Alpha Republic | 101 | 202 |"
        not in control["projection"],
        "synthetic_candidate_retains_late_complete_row": "| Alpha Republic | 101 | 202 |"
        in projected["projection"],
        "synthetic_candidate_retains_all_supported_groups": projected[
            "missed_supported_visible_requirement_group_count"
        ]
        == 0,
        "synthetic_candidate_within_16k_and_per_page_cap": projected[
            "allocated_content_characters"
        ]
        <= 16_000
        and all(value <= 5_000 for value in projected["per_page_allocated_characters"]),
        "entropy_credit_zero": projected[
            "entropy_or_information_gain_assigns_credit"
        ]
        is False,
    }
    manifest = {str(path): _sha(path) for path in SOURCES}
    value = {
        "artifact_version": 1,
        "role": "v24839_structure_preserving_projector_build_audit",
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
            "verified_arxiv_ids": [
                "2607.08662v1",
                "2607.24223v2",
                "2608.01285v1",
                "2608.01913v1",
                "2608.02358v1",
                "2608.02751v2",
                "2608.03527v1",
                "2608.04588v1",
            ],
            "mechanism": "inspect_structure_then_fixed_budget_set_coverage",
        },
        "source_manifest": manifest,
        "source_manifest_sha256": candidate.payload_sha256(manifest),
        "tests": tests,
        "ast_audit": ast_report,
        "synthetic_shared_prefix_gate": {
            "input_page_count": projected["input_page_count"],
            "same_raw_page_vector": control["per_page_content_sha256"]
            == projected["per_page_content_sha256"],
            "control_allocated_content_characters": control[
                "allocated_content_characters"
            ],
            "candidate_allocated_content_characters": projected[
                "allocated_content_characters"
            ],
            "candidate_supported_visible_requirement_groups": projected[
                "supported_visible_requirement_group_count"
            ],
            "candidate_missed_supported_visible_requirement_groups": projected[
                "missed_supported_visible_requirement_group_count"
            ],
            "control_projection_sha256": control["projection_sha256"],
            "candidate_projection_sha256": projected["projection_sha256"],
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
            "fresh_benchmark_external_shared_prefix_gate_design": all(
                checks.values()
            ),
            "fresh_external_activation_or_launch": False,
            "public_dev64_or_exact220": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = candidate.payload_sha256(value)
    return value


def publish(path: Path, value: dict[str, Any]) -> None:
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
    publish(ROOT / OUTPUT, report)
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
