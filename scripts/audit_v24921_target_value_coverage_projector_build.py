#!/usr/bin/env python3
"""Build audit for the V2.49.21 target--value coverage projector."""

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

from deepwide_agent import v24921_target_value_coverage_projector as projector  # noqa: E402
from scripts.audit_v24635_exact220 import (  # noqa: E402
    _accesses,
    _evaluator_capabilities,
)


DATE = "20260808"
ROLE = "v24921_target_value_coverage_projector_build_audit"
OUTPUT = Path(
    f"results/v24921_target_value_coverage_projector_build_audit_v1_{DATE}.json"
)
PARENT = Path(f"results/v24858_v24857_pacing_quality_diagnosis_v1_{DATE}.json")
SOURCE_FILES = (
    Path("src/deepwide_agent/v24921_target_value_coverage_projector.py"),
    Path("tests/test_v24921_target_value_coverage_projector.py"),
    Path("scripts/audit_v24921_target_value_coverage_projector_build.py"),
)
TESTS = (
    ("test_v24921_target_value_coverage_projector.py", 9),
    ("test_v24846_atomic_table_header_30k_profile.py", 9),
    ("test_v24842_atomic_table_header_closure.py", 11),
    ("test_v24839_structure_preserving_projector.py", 13),
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
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
        raise RuntimeError(f"V2.49.21 expected ordinary file: {relative}")
    return path


def _sha(relative: Path) -> str:
    return hashlib.sha256(_ordinary(relative).read_bytes()).hexdigest()


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == projector.payload_sha256(unsigned)


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


def _pure_source() -> bool:
    tree = ast.parse(
        _ordinary(SOURCE_FILES[0]).read_text(encoding="utf-8"),
        filename=str(SOURCE_FILES[0]),
    )
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
    return imports.isdisjoint(
        {"os", "pathlib", "socket", "subprocess", "requests", "httpx", "openai"}
    ) and calls.isdisjoint({"open", "eval", "exec", "compile", "__import__"})


def build(*, now: int | None = None) -> dict[str, Any]:
    parent = json.loads(_ordinary(PARENT).read_text(encoding="utf-8"))
    parent_valid = (
        parent.get("role") == "v24858_v24857_pacing_quality_aggregate_diagnosis"
        and parent.get("diagnosis_valid") is True
        and parent.get("findings") == []
        and parent.get("authorization", {}).get("coverage_utility_selector_build")
        is True
        and _sealed(parent, "diagnosis_payload_sha256")
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
    question = (
        "Column names: Country | Target Metric [TM] @2024.\n"
        "<COUNTRIES>\n1. Omega Republic [OMG]\n</COUNTRIES>"
    )
    pages = [
        {
            "title": "Official",
            "url": "https://example.invalid/data",
            "content": (
                "| Country | Target Metric [TM] @2024 |\n|---|---:|\n"
                "| Omega Republic | 999 |"
            ),
        }
    ]
    mechanism = projector.build_projection(question, pages)
    receipt = mechanism["content_free_receipt"]
    checks = {
        "parent_pacing_quality_diagnosis_valid": parent_valid,
        "focused_tests_exact42": all(row["passed"] for row in tests)
        and sum(row["observed"] for row in tests) == 42,
        "runtime_privileged_field_access_zero": not accesses,
        "runtime_evaluator_capability_zero": not evaluator,
        "source_secret_literal_zero": not secrets,
        "pure_component_has_no_io_network_process_model_or_dynamic_execution": _pure_source(),
        "target_value_pair_mechanism_naturally_engaged": receipt[
            "supported_target_value_pair_count"
        ]
        > 0
        and receipt["missed_target_value_pair_count"] == 0,
        "fixed_30k_total_and_5k_page_caps": (
            receipt["projected_rendered_characters"] <= 30_000
            and all(value <= 5_000 for value in mechanism["per_page_allocated_characters"])
        ),
        "atomic_table_header_closure_preserved": receipt[
            "orphan_selected_table_continuation_block_count"
        ]
        == 0,
        "additional_effect_or_cap_zero": receipt[
            "additional_search_fetch_model_call_token_context_or_wall_cap"
        ]
        is False,
        "entropy_assigns_no_credit": receipt[
            "entropy_or_information_gain_assigns_credit"
        ]
        is False,
    }
    manifest = {str(path): _sha(path) for path in (*SOURCE_FILES, PARENT)}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"path": str(PARENT), "sha256": _sha(PARENT)},
        "source_manifest": manifest,
        "source_manifest_sha256": projector.payload_sha256(manifest),
        "tests": tests,
        "runtime_semantic_audit": {
            "privileged_runtime_field_accesses": sorted(set(accesses)),
            "evaluator_capabilities": sorted(set(evaluator)),
            "credential_literal_hits": sorted(set(secrets)),
        },
        "mechanism": {
            "input": "visible_question_and_same_forward_fetched_pages_only",
            "treatment": "joint_visible_row_and_value_target_coverage_before_independent_phrase_coverage",
            "total_character_cap": 30_000,
            "per_page_character_cap": 5_000,
            "atomic_table_header_closure": True,
            "stable_page_and_block_output_order": True,
            "source_diversity_safety": True,
            "additional_network_search_fetch_model_token_context_or_wall_cap": False,
        },
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "audit_valid": all(checks.values()),
        "source_policy": {
            "mapping_gold_category_question_type_split_evaluator_score_reward_historical_result_read": False,
            "entropy_information_gain_shadow_only": True,
            "entropy_or_information_gain_assigns_signed_credit": False,
        },
        "authorization": {
            "fresh_benchmark_external_three_arm_gate_design": all(checks.values()),
            "external_launch": False,
            "public_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = projector.payload_sha256(value)
    return value


def validate(value: dict[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    signature = unsigned.pop("audit_payload_sha256", None)
    if (
        value.get("role") != ROLE
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or signature != projector.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.49.21 build audit drifted")
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


def main() -> None:
    report = validate(build())
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


if __name__ == "__main__":
    main()
