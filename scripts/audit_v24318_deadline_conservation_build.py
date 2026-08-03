#!/usr/bin/env python3
"""Build-only audit for V2.43.18 deadline-conserving accounting."""

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

from deepwide_agent.v24315_forward_contract import (  # noqa: E402
    payload_sha256,
    protected_watcher_snapshot,
)


AUDIT = Path("results/v24318_deadline_conservation_build_audit_v2_20260803.json")
V1_AUDIT = Path("results/v24318_deadline_conservation_build_audit_v1_20260803.json")
V1_INVALIDATION = Path(
    "results/v24318_deadline_conservation_build_audit_v1_invalidation_20260803.json"
)
DIAGNOSIS = Path("results/v24317_v24315_outer_totality_diagnosis_v1_20260803.json")
DIAGNOSIS_AUDIT = Path(
    "results/v24317_v24315_outer_totality_diagnosis_audit_v1_20260803.json"
)
SEARCH_AUDIT = Path("results/v24316_deadline_search_build_audit_v3_20260803.json")
SOURCE = Path("src/deepwide_agent/v24318_deadline_conservation_runtime.py")
TEST = Path("tests/test_v24318_deadline_conservation_runtime.py")
FILES = (SOURCE, TEST)
TESTS = (
    ("test_v24318_deadline_conservation_runtime.py", 8),
    ("test_v24273_two_wave_task_runtime.py", 8),
    ("test_v24296_staged_reserve_task_runtime.py", 7),
    ("test_v24310_paired_dev_runtime.py", 8),
    ("test_v24312_deadline_reliability.py", 7),
    ("test_v24316_deadline_search.py", 7),
)
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT)
    ):
        raise RuntimeError("V2.43.18 expected an ordinary repository file")
    return path


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.43.18 expected a JSON object")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _field_accesses(path: Path) -> list[str]:
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


def _run_test(filename: str) -> int:
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
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=180,
        check=False,
    )
    return int(completed.returncode)


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    diagnosis = _read(DIAGNOSIS)
    diagnosis_audit = _read(DIAGNOSIS_AUDIT)
    search_audit = _read(SEARCH_AUDIT)
    v1_audit = _read(V1_AUDIT)
    v1_invalidation = _read(V1_INVALIDATION)
    manifest = {str(relative): sha256(_ordinary(relative)) for relative in FILES}
    source_text = {str(relative): _ordinary(relative).read_text(encoding="utf-8") for relative in FILES}
    secret_hits = sorted(name for name, text in source_text.items() if SECRET.search(text))
    accesses = _field_accesses(_ordinary(SOURCE))
    test_results = [
        {"file": filename, "test_count": count, "passed": _run_test(filename) == 0}
        for filename, count in TESTS
    ]
    findings: list[str] = []
    if (
        diagnosis.get("diagnosis_valid") is not True
        or diagnosis.get("findings") != []
        or diagnosis.get("mechanical_cause_counts")
        != {
            "deadline_deferred_cached_pages": 1,
            "logical_model_admission_rejected_before_provider": 17,
        }
        or not _sealed(diagnosis, "diagnosis_payload_sha256")
    ):
        findings.append("parent_diagnosis_invalid")
    if (
        diagnosis_audit.get("audit_valid") is not True
        or diagnosis_audit.get("findings") != []
        or not _sealed(diagnosis_audit, "audit_payload_sha256")
    ):
        findings.append("parent_diagnosis_audit_invalid")
    if (
        search_audit.get("audit_valid") is not True
        or search_audit.get("findings") != []
        or not _sealed(search_audit, "audit_payload_sha256")
    ):
        findings.append("v24316_search_audit_invalid")
    if (
        v1_audit.get("audit_valid") is not False
        or v1_audit.get("findings") != ["conservation_or_budget_hook_absent"]
        or v1_invalidation.get("invalidated_artifact")
        != {"path": str(V1_AUDIT), "sha256": sha256(_ordinary(V1_AUDIT))}
        or v1_invalidation.get("cause")
        != "source_hook_whitespace_match_false_negative"
        or v1_invalidation.get("v1_audit_valid_claim") is not False
        or v1_invalidation.get("v1_future_runner_integration_authority") is not False
        or v1_invalidation.get("v1_benchmark_launch_authority") is not False
        or not _sealed(v1_invalidation, "invalidation_payload_sha256")
    ):
        findings.append("v1_invalidation_invalid")
    if accesses:
        findings.append("privileged_field_access_in_runtime")
    if secret_hits:
        findings.append("credential_literal_in_build_surface")
    if not all(item["passed"] for item in test_results):
        findings.append("focused_or_parent_regression_failed")
    source = "".join(source_text[str(SOURCE)].split())
    if (
        "receipt[\"logical_admissions_total\"]!=receipt[\"provider_requests_total\"]+receipt[\"pre_provider_rejections_total\"]"
        not in source
        or "cached!=returned+deferred" not in source
        or "model_call_cap!=3" not in source
        or "limits.model_calls!=3" not in source
    ):
        findings.append("conservation_or_budget_hook_absent")
    value = {
        "artifact_version": 1,
        "role": "v24318_deadline_conservation_build_audit_v2",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            str(DIAGNOSIS): sha256(_ordinary(DIAGNOSIS)),
            str(DIAGNOSIS_AUDIT): sha256(_ordinary(DIAGNOSIS_AUDIT)),
            str(SEARCH_AUDIT): sha256(_ordinary(SEARCH_AUDIT)),
            str(V1_AUDIT): sha256(_ordinary(V1_AUDIT)),
            str(V1_INVALIDATION): sha256(_ordinary(V1_INVALIDATION)),
        },
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "focused_and_parent_tests": test_results,
        "test_count": sum(count for _, count in TESTS),
        "external_effect_ledger": {
            "remote_network": 0,
            "model": 0,
            "hosted_search": 0,
            "fetch": 0,
            "evaluator": 0,
        },
        "privileged_field_accesses": accesses,
        "credential_literal_hits": secret_hits,
        "protected_watchers": protected_watcher_snapshot(),
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "question_prompt_response_prediction_query_url_page_or_credential_emitted_by_receipts": False,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
            "active_run_signaled_restarted_resumed_rerun_or_modified": False,
        },
        "claims": {
            "two_conservation_equations_mechanically_enforced": True,
            "prompt_model_search_or_budget_changed": False,
            "quality_or_sota_inferred": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "future_runner_integration_design": not findings,
            "benchmark_launch": False,
            "evaluator": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    report = build_audit()
    publish_new(ROOT / AUDIT, report)
    print(json.dumps({"path": str(AUDIT), "audit_valid": report["audit_valid"]}, sort_keys=True))
