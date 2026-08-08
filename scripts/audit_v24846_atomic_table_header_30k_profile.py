#!/usr/bin/env python3
"""Clean-build audit for the pure V2.48.46 atomic-header 30k profile."""

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

from deepwide_agent import v24842_atomic_table_header_closure as control  # noqa: E402
from deepwide_agent import v24846_atomic_table_header_30k_profile as candidate  # noqa: E402


OUTPUT = Path("results/v24846_atomic_table_header_30k_profile_build_audit_v1_20260808.json")
SOURCE = Path("src/deepwide_agent/v24846_atomic_table_header_30k_profile.py")
TEST = Path("tests/test_v24846_atomic_table_header_30k_profile.py")
PARENT_TEST = Path("tests/test_v24842_atomic_table_header_closure.py")
AUDIT = Path("scripts/audit_v24846_atomic_table_header_30k_profile.py")
DIAGNOSIS = Path("results/v24845_v24844_evidence_supply_diagnosis_v1_20260808.json")
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
    {"os", "pathlib", "subprocess", "socket", "requests", "httpx", "urllib.request", "aiohttp", "openai"}
)
DANGEROUS_CALLS = frozenset(
    {"open", "eval", "exec", "compile", "__import__", "subprocess.run", "subprocess.Popen", "os.system"}
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def _sha(relative: Path) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


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


def _ast_findings() -> dict[str, list[str]]:
    source = (ROOT / SOURCE).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SOURCE))
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
        "credential_literal_hits": [str(SOURCE)] if SECRET.search(source) else [],
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
            str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest",
            "discover", "-s", "tests", "-p", relative.name, "-v",
        ],
        cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        timeout=240, check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(match.group(1)) if match else 0
    return {
        "path": str(relative), "expected": expected, "observed": observed,
        "passed": completed.returncode == 0 and observed == expected,
        "output_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
    }


def _pages() -> list[dict[str, str]]:
    output = []
    for page_index in range(1, 9):
        lines = ["| Country | Target Metric |", "|---|---:|"]
        lines.extend(
            f"| filler-{page_index}-{row:03d} | {page_index * 1000 + row} |"
            for row in range(180)
        )
        if page_index == 8:
            lines.append("| Omega Republic | 999 |")
        output.append(
            {
                "title": f"Official page {page_index}",
                "url": f"https://official{page_index}.example/table",
                "content": "\n".join(lines),
            }
        )
    return output


def build(*, now: int | None = None) -> dict[str, Any]:
    status = _git("status", "--porcelain")
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    diagnosis = json.loads((ROOT / DIAGNOSIS).read_text(encoding="utf-8"))
    ast_report = _ast_findings()
    tests = [_run_test(TEST, 9), _run_test(PARENT_TEST, 11)]
    question = "Column names: Country | Target Metric. Return the row for Omega Republic."
    pages = _pages()
    baseline = control.build_projection(question, pages)
    expanded = candidate.build_projection(question, pages)
    receipt = expanded["content_free_receipt"]
    encoded_receipt = json.dumps(receipt, ensure_ascii=False, sort_keys=True)
    checks = {
        "tracked_sources_clean_pushed_head": not status and head == remote,
        "focused_tests_exact20": all(test["passed"] for test in tests)
        and sum(test["observed"] for test in tests) == 20,
        "runtime_ast_no_io_network_process_or_dynamic_execution": not ast_report["dangerous_imports"]
        and not ast_report["dangerous_calls"],
        "runtime_ast_no_privileged_field_access": not ast_report["privileged_runtime_field_accesses"],
        "source_secret_literal_zero": not ast_report["credential_literal_hits"],
        "diagnosis_valid_and_build_authorized": diagnosis.get("diagnosis_valid") is True
        and diagnosis.get("findings") == []
        and diagnosis.get("authorization", {}).get("thirty_k_atomic_projector_and_observability_build") is True,
        "single_behavior_change_is_total_cap_16k_to_30k": expanded["single_change"]
        == {
            "total_character_cap_from_to": [16_000, 30_000],
            "maximum_page_chars_unchanged": True,
            "block_character_cap_unchanged": True,
            "relevance_structure_order_and_closure_logic_unchanged": True,
        },
        "candidate_uses_more_context_under_same_raw_pages": receipt["projected_rendered_characters"]
        > baseline["projected_rendered_characters"],
        "candidate_rendered_and_per_page_caps_hard": receipt["projected_rendered_characters"] <= 30_000
        and receipt["policy"]["maximum_page_chars"] == 5_000,
        "candidate_orphan_continuations_zero": receipt["orphan_selected_table_continuation_block_count"] == 0,
        "content_free_receipt_has_required_trigger_counters": all(
            key in receipt
            for key in (
                "selected_table_continuation_block_count",
                "table_header_dependency_addition_count",
                "orphan_selected_table_continuation_block_count",
                "supported_visible_requirement_group_count",
                "retained_supported_visible_requirement_group_count",
            )
        ),
        "content_free_receipt_has_no_raw_content_or_hashes": all(
            token not in encoded_receipt
            for token in ("Omega Republic", "official1.example", "filler-1-001", "content_sha256", "projection_sha256", "visible_question_sha256")
        ),
        "entropy_credit_zero": expanded["entropy_or_information_gain_assigns_credit"] is False,
    }
    manifest = {str(path): _sha(path) for path in SOURCES}
    value = {
        "artifact_version": 1,
        "role": "v24846_atomic_table_header_30k_profile_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": head, "target_main": remote,
            "head_equals_target_main": head == remote, "worktree_clean": not status,
        },
        "parent": {"path": str(DIAGNOSIS), "sha256": _sha(DIAGNOSIS)},
        "source_manifest": manifest,
        "source_manifest_sha256": candidate.payload_sha256(manifest),
        "tests": tests,
        "ast_audit": ast_report,
        "synthetic_shared_input": {
            "control_rendered_characters": baseline["projected_rendered_characters"],
            "candidate_rendered_characters": receipt["projected_rendered_characters"],
            "candidate_selected_table_continuations": receipt["selected_table_continuation_block_count"],
            "candidate_dependency_additions": receipt["table_header_dependency_addition_count"],
            "candidate_orphan_continuations": receipt["orphan_selected_table_continuation_block_count"],
            "same_visible_question_and_raw_pages": True,
        },
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "source_policy": {
            "runtime_inputs_visible_question_and_same_forward_fetched_pages_only": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_historical_result_read": False,
            "entropy_or_information_gain_assigns_credit": False,
            "network_model_search_fetch_process_or_evaluator_called_by_audit": False,
        },
        "authorization": {
            "fresh_external_shared_prefix_protocol_design": all(checks.values()),
            "external_launch": False,
            "public_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_valid"] = not value["findings"]
    value["audit_payload_sha256"] = candidate.payload_sha256(value)
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
    artifact = build()
    if not artifact["audit_valid"]:
        raise RuntimeError(f"V2.48.46 build audit failed: {artifact['findings']}")
    publish(ROOT / OUTPUT, artifact)
    print(json.dumps({"path": str(OUTPUT), "audit_valid": True, "authorization": artifact["authorization"]}, sort_keys=True))
