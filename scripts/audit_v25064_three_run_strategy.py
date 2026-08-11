#!/usr/bin/env python3
"""Clean-tree audit for the frozen V2.50.64 aggregate diagnosis."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import diagnose_v25064_three_run_strategy as diagnosis  # noqa: E402


DATE = "20260811"
OUTPUT = Path(f"results/v25064_three_run_strategy_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25064_three_run_strategy.py")
TEST = Path("tests/test_audit_v25064_three_run_strategy.py")
PROTECTED_WATCHERS = {
    795336: 713986317,
    2808901: 746680268,
    2889939: 746969965,
    3061652: 747569004,
}


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.50.64 audit expected ordinary repository file")
    return path


def sha256(relative: Path) -> str:
    digest = hashlib.sha256()
    with _ordinary(relative).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _tracked(relative: Path) -> bool:
    return (
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode
        == 0
    )


def _watchers() -> dict[str, Any]:
    observed: dict[str, Any] = {}
    for pid, expected_start in PROTECTED_WATCHERS.items():
        path = Path("/proc") / str(pid) / "stat"
        if not path.is_file():
            observed[str(pid)] = {"present": False, "start_ticks": None}
            continue
        fields = path.read_text(encoding="utf-8").split()
        start = int(fields[21]) if len(fields) >= 22 else None
        observed[str(pid)] = {
            "present": True,
            "start_ticks": start,
            "matches_frozen_identity": start == expected_start,
        }
    return observed


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    result = diagnosis.validate_diagnosis(
        json.loads(_ordinary(diagnosis.OUTPUT).read_text(encoding="utf-8"))
    )
    head = _git("rev-parse", "HEAD")
    target = _git("rev-parse", "target/main")
    clean = not _git("status", "--porcelain")
    watchers = _watchers()
    tracked = all(
        _tracked(path)
        for path in (
            diagnosis.SOURCE,
            diagnosis.TEST,
            diagnosis.OUTPUT,
            SOURCE,
            TEST,
        )
    )
    content_policy = result["content_policy"]
    authorization = result["authorization"]
    checks = {
        "diagnosis_valid_and_sealed": True,
        "all_parent_hashes_bound": result["parents"] == diagnosis.EXPECTED_SHA256,
        "fixed_three_by_220_aggregate_scope": result["fixed_denominator"]
        == {"runs": 3, "tasks_per_run": 220},
        "generator_tests_result_auditor_tests_tracked": tracked,
        "git_clean_head_equals_target_main": clean and head == target,
        "aggregate_only_no_task_identifier_or_cross_run_join": content_policy[
            "task_identifier_materialized_or_cross_run_per_task_joined"
        ]
        is False,
        "no_sensitive_runtime_or_evaluator_content_decoded": content_policy[
            "task_question_query_url_page_prediction_evaluator_row_gold_category_split_or_per_task_score_decoded"
        ]
        is False,
        "no_external_effect_or_credential_access": content_policy[
            "network_model_search_fetch_evaluator_benchmark_or_credential_accessed"
        ]
        is False,
        "build_design_only_no_external_or_exact220_authority": authorization[
            "source_record_binding_build_design"
        ]
        is True
        and authorization["fresh_external_protocol_publication"] is False
        and authorization["fresh_external_launch"] is False
        and authorization["new_exact220_launch"] is False,
        "entropy_signed_credit_zero": result["diagnosis"][
            "entropy_or_information_gain_signed_credit"
        ]
        == 0,
        "protected_watcher_identity_unchanged": all(
            row.get("matches_frozen_identity") is True for row in watchers.values()
        ),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25064_three_run_content_free_strategy_diagnosis_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target, "clean": clean},
        "artifacts": {
            "diagnosis_generator_sha256": sha256(diagnosis.SOURCE),
            "diagnosis_test_sha256": sha256(diagnosis.TEST),
            "diagnosis_result_sha256": sha256(diagnosis.OUTPUT),
            "audit_source_sha256": sha256(SOURCE),
            "audit_test_sha256": sha256(TEST),
        },
        "protected_watchers": watchers,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": copy.deepcopy(authorization),
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    authorization = copied.get("authorization") or {}
    if (
        copied.get("role")
        != "v25064_three_run_content_free_strategy_diagnosis_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or authorization.get("source_record_binding_build_design") is not True
        or any(
            authorization.get(name) is not False
            for name in authorization
            if name != "source_record_binding_build_design"
        )
        or any(
            row.get("matches_frozen_identity") is not True
            for row in (copied.get("protected_watchers") or {}).values()
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.64 strategy audit drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    payload = (json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
        0o600,
    )
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("V2.50.64 audit publication made no progress")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> None:
    value = build_audit()
    publish_exclusive(ROOT / OUTPUT, value)
    print(json.dumps({"path": str(OUTPUT), "role": value["role"]}, sort_keys=True))


if __name__ == "__main__":
    main()
