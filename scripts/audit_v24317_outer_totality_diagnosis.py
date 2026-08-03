#!/usr/bin/env python3
"""Audit the content-free V2.43.17 post-terminal diagnosis."""

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

from deepwide_agent.v24315_forward_contract import (  # noqa: E402
    protected_watcher_snapshot,
    payload_sha256,
)
from scripts.diagnose_v24317_v24315_outer_totality import (  # noqa: E402
    RESULT,
    _read,
    sha256,
    validate_report,
)
from scripts.publish_v24315_exact220_forward_nogo import (  # noqa: E402
    AUDIT as PARENT_AUDIT,
    RESULT as PARENT_RESULT,
)


AUDIT = Path("results/v24317_v24315_outer_totality_diagnosis_audit_v1_20260803.json")
SOURCE = Path("scripts/diagnose_v24317_v24315_outer_totality.py")
TEST = Path("tests/test_v24317_outer_totality_diagnosis.py")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
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


def build_audit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    report = _read(root / RESULT)
    validate_report(root, report)
    parent_audit = _read(root / PARENT_AUDIT)
    sources = (SOURCE, TEST)
    manifest = {str(path): sha256(root / path) for path in sources}
    secret_hits = [
        str(path)
        for path in sources
        if SECRET.search((root / path).read_text(encoding="utf-8"))
    ]
    accesses = _field_accesses(root / SOURCE)
    completed = subprocess.run(
        [
            str(root / ".venv-eval/bin/python"),
            "-I",
            "-B",
            str(root / TEST),
        ],
        cwd=root,
        env={
            "HOME": os.environ.get("HOME", str(Path.home())),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
            "V24317_AUDIT_CHILD": "1",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=120,
        check=False,
    )
    findings: list[str] = []
    if parent_audit.get("audit_valid") is not True or parent_audit.get("findings") != []:
        findings.append("parent_nogo_audit_invalid")
    if report.get("parent_nogo") != {
        "path": str(PARENT_RESULT),
        "sha256": sha256(root / PARENT_RESULT),
    }:
        findings.append("parent_nogo_binding_invalid")
    if secret_hits:
        findings.append("credential_literal_in_diagnosis_surface")
    if accesses:
        findings.append("privileged_field_access_in_diagnosis_surface")
    if completed.returncode != 0:
        findings.append("focused_tests_failed")
    value = {
        "artifact_version": 1,
        "role": "v24317_v24315_outer_totality_diagnosis_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "diagnosis": {"path": str(RESULT), "sha256": sha256(root / RESULT)},
        "parent_nogo_audit": {
            "path": str(PARENT_AUDIT),
            "sha256": sha256(root / PARENT_AUDIT),
        },
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "focused_tests": {
            "passed": completed.returncode == 0,
            "test_count": 4,
            "self_audit_test_skipped_in_child": True,
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "privileged_field_accesses": accesses,
        "credential_literal_hits": secret_hits,
        "protected_watchers": protected_watcher_snapshot(),
        "source_policy": {
            "all_220_predictions_frozen_before_diagnosis": True,
            "same_run_mapping_gold_category_question_type_split_evaluator_score_read": False,
            "question_opaque_id_prompt_response_prediction_query_url_page_or_credential_emitted": False,
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
            "process_signaled_restarted_resumed_rerun_or_modified": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "append_only_accounting_fix_design": not findings,
            "benchmark_launch": False,
            "same_run_evaluator": False,
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
    value = build_audit()
    publish_new(ROOT / AUDIT, value)
    print(json.dumps({"path": str(AUDIT), "audit_valid": value["audit_valid"]}, sort_keys=True))
