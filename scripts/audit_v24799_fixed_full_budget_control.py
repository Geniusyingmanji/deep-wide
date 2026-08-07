#!/usr/bin/env python3
"""Publish a clean-build synthetic gate for V2.47.99 full-budget control."""

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

from deepwide_agent import v24798_exact220_contract as parent  # noqa: E402
from deepwide_agent import v24799_fixed_full_budget_control as control  # noqa: E402
from scripts.diagnose_v24798_exact220_postresult import (  # noqa: E402
    OUTPUT as DIAGNOSIS,
    validate_diagnosis,
)


DATE = "20260807"
OUTPUT = Path(f"results/v24799_fixed_full_budget_control_build_audit_v1_{DATE}.json")
SOURCE = Path("src/deepwide_agent/v24799_fixed_full_budget_control.py")
TEST = Path("tests/test_v24799_fixed_full_budget_control.py")
SCRIPT = Path("scripts/audit_v24799_fixed_full_budget_control.py")
SECRET = re.compile(r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}")


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.47.99 build audit expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.99 build audit expected object")
    return value


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def _test() -> tuple[bool, int, str]:
    completed = subprocess.run(
        [
            str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest",
            "discover", "-s", "tests", "-p", TEST.name, "-v",
        ],
        cwd=ROOT,
        env={
            "HOME": os.environ.get("HOME", str(Path.home())),
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
    return completed.returncode == 0 and observed == 5, observed, control.payload_sha256(completed.stdout)


def _pure_source() -> bool:
    tree = ast.parse((ROOT / SOURCE).read_text(encoding="utf-8"))
    forbidden_imports = {"os", "pathlib", "subprocess", "requests", "socket", "urllib"}
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
    return imports.isdisjoint(forbidden_imports)


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main"):
        raise RuntimeError("V2.47.99 build audit requires clean pushed HEAD")
    diagnosis = validate_diagnosis(_read(ROOT / DIAGNOSIS))
    gate = control.build_synthetic_gate()
    passed, observed, output_hash = _test()
    secret_hits = [
        str(path)
        for path in (SOURCE, TEST, SCRIPT)
        if SECRET.search((ROOT / path).read_text(encoding="utf-8"))
    ]
    checks = {
        "v24798_diagnosis_authorizes_synthetic_design": diagnosis[
            "authorization"
        ]["synthetic_full_budget_control_design"]
        is True,
        "synthetic_grid_nonempty": gate["synthetic_observation_count"] > 1_000,
        "all_presafety_ceiling_cases_expand": gate[
            "pre_synthesis_safety_ceiling_expand_count"
        ]
        == gate["synthetic_observation_count"],
        "entropy_value_zero_for_all_cases": gate["zero_entropy_value_count"]
        == gate["synthetic_observation_count"],
        "deadline_boundary_stops": gate["deadline_boundary_reason"]
        == "latency_ceiling",
        "hard_caps_unchanged": gate["hard_query_cap"] == 4
        and gate["hard_fetch_cap"] == 10,
        "focused_tests_5_of_5": passed and observed == 5,
        "pure_source_has_no_io_import": _pure_source(),
        "credential_literals_absent": secret_hits == [],
        "future_artifact_pristine": not (ROOT / OUTPUT).exists()
        and not (ROOT / OUTPUT).is_symlink(),
    }
    findings = sorted(name for name, value in checks.items() if not value)
    value = {
        "artifact_version": 1,
        "role": "v24799_fixed_full_budget_control_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": _git("rev-parse", "HEAD"),
            "target_main": _git("rev-parse", "target/main"),
            "clean": True,
            "head_equals_target_main": True,
        },
        "parents": {
            "v24798_diagnosis_sha256": parent.sha256(ROOT / DIAGNOSIS),
        },
        "source_manifest": {
            str(path): parent.sha256(ROOT / path) for path in (SOURCE, TEST, SCRIPT)
        },
        "synthetic_gate": gate,
        "tests": {"expected": 5, "observed": observed, "passed": passed, "output_sha256": output_hash},
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "source_policy": {
            "visible_question_task_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "entropy_or_information_gain_used_for_admission": False,
        },
        "authorization": {
            "next_fresh_exact220_protocol_design": not findings,
            "exact220_launch": False,
            "evaluator": False,
            "retry_resume_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = control.payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    audit = build_audit()
    if not audit["audit_valid"]:
        raise RuntimeError(f"V2.47.99 build audit failed: {audit['findings']}")
    publish_new(ROOT / OUTPUT, audit)
    print(json.dumps({"path": str(OUTPUT), "audit_valid": True, "findings": []}, sort_keys=True))
