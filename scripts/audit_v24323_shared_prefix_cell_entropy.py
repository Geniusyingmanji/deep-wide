#!/usr/bin/env python3
"""Freeze and audit the benchmark-external V2.43.23 entropy prototype."""

from __future__ import annotations

import ast
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

from deepwide_agent.v24320_forward_contract import (  # noqa: E402
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from scripts.audit_v24187_phase_liveness import process_snapshot  # noqa: E402
from scripts.preregister_v24259_deterministic_normalizer_smoke import _matching  # noqa: E402


DATE = "20260803"
ROLE = "v24323_shared_prefix_cell_entropy_build_audit"
OUTPUT = Path(f"results/v24323_shared_prefix_cell_entropy_build_audit_v1_{DATE}.json")
PARENT = Path(f"results/v24322_v24320_paired_dev64_diagnosis_v1_{DATE}.json")
SOURCES = (
    "src/deepwide_agent/v24323_shared_prefix_cell_entropy.py",
    "tests/test_v24323_shared_prefix_cell_entropy.py",
    "scripts/audit_v24323_shared_prefix_cell_entropy.py",
)
TEST_PATTERN = "test_v24323_shared_prefix_cell_entropy.py"
TEST_COUNT = 8
PRIVILEGED = frozenset(
    {
        "question_type",
        "task_category",
        "category",
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
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def _accesses(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    output: list[str] = []
    for node in ast.walk(tree):
        key = None
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            key = node.args[0].value
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            key = node.slice.value
        if key is not None and key.casefold() in PRIVILEGED:
            output.append(f"{path.relative_to(ROOT)}:{node.lineno}:{key}")
    return output


def _test() -> bool:
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
            TEST_PATTERN,
        ],
        cwd=ROOT,
        env={
            "HOME": str(Path.home()),
            "USER": "azureuser",
            "LOGNAME": "azureuser",
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=120,
        check=False,
    )
    return completed.returncode == 0


def build(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    parent = json.loads((root / PARENT).read_text(encoding="utf-8"))
    unsigned = dict(parent)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    if (
        parent.get("role") != "v24322_v24320_paired_dev64_postfreeze_diagnosis"
        or parent.get("authorization", {}).get("shared_prefix_successor_design")
        is not True
        or parent.get("authorization", {}).get("successor_launch") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.43.23 parent diagnosis drifted")
    manifest = {relative: sha256(root / relative) for relative in SOURCES}
    accesses = sorted(
        access for relative in SOURCES[:1] for access in _accesses(root / relative)
    )
    secrets = sorted(
        relative
        for relative in SOURCES
        if SECRET.search((root / relative).read_text(encoding="utf-8"))
    )
    tests_passed = _test()
    process_present = bool(
        _matching(
            process_snapshot(),
            "tests/test_v24323_shared_prefix_cell_entropy.py",
        )
    )
    findings: list[str] = []
    if accesses:
        findings.append("privileged_field_access_in_runtime_kernel")
    if secrets:
        findings.append("credential_literal_in_source_surface")
    if not tests_passed:
        findings.append("focused_tests_failed")
    if process_present:
        findings.append("prototype_or_test_process_remained_active")
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_diagnosis_sha256": sha256(root / PARENT),
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "focused_tests": {
            "pattern": TEST_PATTERN,
            "test_count": TEST_COUNT,
            "passed": tests_passed,
        },
        "behavior_matrix": {
            "reliable_corroborated_support_admitted": True,
            "million_character_low_reliability_evidence_quarantined": True,
            "single_source_evidence_quarantined": True,
            "weak_conflict_cannot_override_core": True,
            "strong_independent_conflict_requires_override_gate": True,
            "entropy_increasing_evidence_quarantined": True,
            "receipt_replay_and_tamper_fail_closed": True,
            "prefix_mismatch_fails_before_pair_contract": True,
        },
        "privileged_field_accesses": accesses,
        "credential_literal_hits": secrets,
        "prototype_or_test_process_present": process_present,
        "protected_watchers": protected_watcher_snapshot(),
        "external_effect_ledger": {
            "remote_network": 0,
            "model_provider": 0,
            "hosted_search": 0,
            "fetch": 0,
            "evaluator": 0,
        },
        "claim_scope": {
            "shared_plan_query_first_wave_core_prefix_contract": True,
            "cell_conditional_entropy_admission_kernel": True,
            "reliability_tempered_bayesian_update": True,
            "reserve_context_isolation": True,
            "synthesis_randomness_shared": False,
            "reserve_effect_fully_causally_identified": False,
            "benchmark_quality_improvement": False,
        },
        "source_policy": {
            "benchmark_external": True,
            "question_or_evidence_content_read_by_kernel": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "benchmark_or_evaluator_called": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "shared_prefix_runtime_design": not findings,
            "runtime_or_benchmark_launch": False,
            "additional_dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    report = build()
    publish(ROOT / OUTPUT, report)
    print(
        json.dumps(
            {"path": str(OUTPUT), "audit_valid": report["audit_valid"]},
            sort_keys=True,
        )
    )
