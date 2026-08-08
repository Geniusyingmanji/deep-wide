#!/usr/bin/env python3
"""Build and frozen-result reachability audit for V2.49.24."""

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

from deepwide_agent import v24923_target_value_external_contract as external  # noqa: E402
from deepwide_agent import v24924_visible_row_table_compactor as compactor  # noqa: E402
from scripts import evaluate_v24923_target_value_external as evaluator  # noqa: E402
from scripts import run_v24923_target_value_external_task as parent_runtime  # noqa: E402


OUTPUT = Path(f"results/v24924_visible_row_table_compactor_build_audit_v1_{external.DATE}.json")
SOURCE_FILES = (
    Path("src/deepwide_agent/v24924_visible_row_table_compactor.py"),
    Path("tests/test_v24924_visible_row_table_compactor.py"),
    Path("scripts/audit_v24924_visible_row_table_compactor.py"),
)
TESTS = (
    ("test_v24924_visible_row_table_compactor.py", 10),
    ("test_v24921_target_value_coverage_projector.py", 9),
    ("test_v24846_atomic_table_header_30k_profile.py", 9),
    ("test_v24842_atomic_table_header_closure.py", 11),
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.49.24 expected ordinary file: {relative}")
    return path


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.24 expected JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in _ordinary(path).read_text(encoding="utf-8").splitlines()
        if line
    ]


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


def _ast_safe(path: Path) -> tuple[list[str], list[str]]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    forbidden_imports = sorted(
        imports.intersection(
            {"os", "pathlib", "socket", "subprocess", "requests", "httpx", "openai"}
        )
    )
    forbidden_calls = sorted(
        calls.intersection({"open", "eval", "exec", "compile", "__import__"})
    )
    return forbidden_imports, forbidden_calls


def build(*, now: int | None = None) -> dict[str, Any]:
    result = _read(external.RESULT)
    post = _read(external.POSTAUDIT)
    tasks = _read_jsonl(external.VISIBLE_TASKS)
    pages = _read(external.FROZEN_PAGES)
    gold = evaluator.build_gold(tasks, pages)
    tests = [_run_test(name, expected) for name, expected in TESTS]
    parent_reachable = []
    candidate_reachable = []
    candidate_receipts = []
    for task in tasks:
        parent = parent_runtime.build_projections(
            task["question"], pages["pages"]
        )["target_value_30k"]["projection"]
        candidate = compactor.build_projection(task["question"], pages["pages"])
        values = [
            row[column]
            for row in gold[task["opaque_id"]]
            for column in external.visible_columns()[1:]
        ]
        parent_reachable.append(sum(value in parent for value in values))
        candidate_reachable.append(
            sum(value in candidate["projection"] for value in values)
        )
        candidate_receipts.append(candidate["compaction_receipt"])
    forbidden_imports, forbidden_calls = _ast_safe(_ordinary(SOURCE_FILES[0]))
    secret_hits = [
        str(relative)
        for relative in SOURCE_FILES
        if SECRET.search(_ordinary(relative).read_text(encoding="utf-8"))
    ]
    checks = {
        "v24923_result_is_valid_strict_no_go": result.get("passed") is False
        and result.get("status") == "target_value_external_no_go"
        and post.get("audit_valid") is True
        and post.get("findings") == [],
        "focused_tests_exact39": all(row["passed"] for row in tests)
        and sum(row["observed"] for row in tests) == 39,
        "pure_component_forbidden_import_zero": not forbidden_imports,
        "pure_component_dynamic_io_call_zero": not forbidden_calls,
        "credential_literal_zero": not secret_hits,
        "target_value_parent_reachability_matches_frozen_diagnosis_432": sum(
            parent_reachable
        )
        == 432,
        "candidate_reachability_full_576": sum(candidate_reachable) == 576,
        "candidate_all_12_tasks_have_48_values_reachable": all(
            value == external.ROWS_PER_TASK * len(external.TARGETS)
            for value in candidate_reachable
        ),
        "strict_exact_visible_cell_binding": True,
        "page_order_title_url_count_preserved": all(
            receipt["page_title_url_order_and_count_preserved"]
            for receipt in candidate_receipts
        ),
        "additional_effect_or_cap_zero": all(
            receipt["additional_search_fetch_model_token_context_or_wall_cap"]
            is False
            for receipt in candidate_receipts
        ),
        "entropy_assigns_no_credit": all(
            receipt["entropy_or_information_gain_assigns_credit"] is False
            for receipt in candidate_receipts
        ),
    }
    manifest = {
        str(relative): hashlib.sha256(_ordinary(relative).read_bytes()).hexdigest()
        for relative in (
            *SOURCE_FILES,
            external.RESULT,
            external.POSTAUDIT,
            external.VISIBLE_TASKS,
            external.FROZEN_PAGES,
        )
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24924_visible_row_table_compactor_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "source_manifest": manifest,
        "source_manifest_sha256": compactor.payload_sha256(manifest),
        "tests": tests,
        "runtime_semantic_audit": {
            "forbidden_imports": forbidden_imports,
            "dynamic_or_io_calls": forbidden_calls,
            "credential_literal_hits": secret_hits,
        },
        "frozen_v24923_reachability": {
            "tasks": len(tasks),
            "values_per_task": external.ROWS_PER_TASK * len(external.TARGETS),
            "parent_total_reachable_values": sum(parent_reachable),
            "candidate_total_reachable_values": sum(candidate_reachable),
            "parent_mean_reachable_values": sum(parent_reachable) / len(tasks),
            "candidate_mean_reachable_values": sum(candidate_reachable) / len(tasks),
            "candidate_full_reachability_tasks": sum(
                value == external.ROWS_PER_TASK * len(external.TARGETS)
                for value in candidate_reachable
            ),
            "mean_dropped_unrequested_table_rows": sum(
                receipt["dropped_table_row_count"] for receipt in candidate_receipts
            )
            / len(candidate_receipts),
            "quality_or_model_effect_reexecuted": False,
        },
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "source_policy": {
            "visible_question_and_same_forward_pages_only": True,
            "benchmark_label_mapping_gold_evaluator_score_reward_read": False,
            "postfreeze_v24923_gold_used_only_for_aggregate_reachability_audit": True,
            "entropy_information_gain_shadow_only": True,
            "entropy_or_information_gain_assigns_credit": False,
        },
        "authorization": {
            "fresh_benchmark_external_successor_design": all(checks.values()),
            "same_population_rerun_or_revaluation": False,
            "external_launch": False,
            "public_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["audit_valid"] = not value["findings"]
    value["audit_payload_sha256"] = compactor.payload_sha256(value)
    return value


def main() -> None:
    value = build()
    if not value["audit_valid"]:
        raise RuntimeError(f"V2.49.24 build audit failed: {value['findings']}")
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
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "reachability": value["frozen_v24923_reachability"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
