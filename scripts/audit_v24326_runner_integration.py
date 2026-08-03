#!/usr/bin/env python3
"""Freeze the benchmark-external V2.43.26 deadline runner integration."""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import (  # noqa: E402
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from scripts.audit_v24187_phase_liveness import process_snapshot  # noqa: E402
from scripts.preregister_v24259_deterministic_normalizer_smoke import (  # noqa: E402
    _matching,
)
from test_v24326_subprocess_integration import MODES, run_matrix  # noqa: E402


DATE = "20260803"
ROLE = "v24326_runner_integration_build_audit"
OUTPUT = Path(f"results/v24326_runner_integration_build_audit_v1_{DATE}.json")
PARENT = Path(
    f"results/v24325_shared_prefix_revision_runtime_build_audit_v1_{DATE}.json"
)
SOURCE_FILES = (
    "src/deepwide_agent/v24309_runner_exit_integration.py",
    "src/deepwide_agent/v24312_deadline_reliability.py",
    "src/deepwide_agent/v24313_runner_integration.py",
    "src/deepwide_agent/v24316_deadline_search.py",
    "src/deepwide_agent/v24325_shared_prefix_revision_runtime.py",
    "src/deepwide_agent/v24326_runner_integration.py",
    "tests/fixtures/v24326_synthetic_child.py",
    "tests/test_v24326_runner_integration.py",
    "tests/test_v24326_subprocess_integration.py",
    "scripts/audit_v24326_runner_integration.py",
)
RUNTIME_FILES = (
    "src/deepwide_agent/v24325_shared_prefix_revision_runtime.py",
    "src/deepwide_agent/v24326_runner_integration.py",
    "tests/fixtures/v24326_synthetic_child.py",
)
TESTS = (
    ("test_v24326_runner_integration.py", 4),
    ("test_v24326_subprocess_integration.py", 3),
    ("test_v24325_shared_prefix_revision_runtime.py", 13),
    ("test_v24316_deadline_search.py", 7),
    ("test_v24312_deadline_reliability.py", 7),
    ("test_v24309_runner_exit_integration.py", 5),
    ("test_v24308_child_exit_observability.py", 9),
)
EXPECTED_TAXONOMY = dict(MODES)
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


def _ordinary(root: Path, relative: str | Path) -> Path:
    relative = Path(relative)
    path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError("V2.43.26 expected an ordinary repository file")
    return path


def _read(root: Path, relative: str | Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.43.26 expected a JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
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


def _run_test(filename: str) -> bool:
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
            "HOME": str(Path.home()),
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
    return completed.returncode == 0


def build(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    parent = _read(root, PARENT)
    if (
        parent.get("role")
        != "v24325_shared_prefix_revision_runtime_build_audit"
        or parent.get("audit_valid") is not True
        or parent.get("findings") != []
        or parent.get("authorization", {}).get(
            "production_runner_integration_design"
        )
        is not True
        or parent.get("authorization", {}).get("benchmark_launch") is not False
        or not _sealed(parent, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.26 parent audit drifted")

    manifest = {
        relative: sha256(_ordinary(root, relative)) for relative in SOURCE_FILES
    }
    source_text = {
        relative: _ordinary(root, relative).read_text(encoding="utf-8")
        for relative in SOURCE_FILES
    }
    accesses = sorted(
        access
        for relative in RUNTIME_FILES
        for access in _field_accesses(_ordinary(root, relative))
    )
    secret_hits = sorted(
        relative for relative, text in source_text.items() if SECRET.search(text)
    )
    test_results = [
        {"file": filename, "test_count": count, "passed": _run_test(filename)}
        for filename, count in TESTS
    ]
    raw = run_matrix()
    observed = {
        mode: raw[mode]["parent"]["failure_taxonomy"] for mode in MODES
    }
    success = raw["success"]["envelope"]
    slot = raw["slot_reject"]["envelope"]
    reserve = raw["reserve_failure"]["envelope"]
    success_receipt = success["result"]["shared_prefix_revision_receipt"]
    slot_receipt = slot["result"]["shared_prefix_revision_receipt"]
    reserve_receipt = reserve["result"]["shared_prefix_revision_receipt"]
    behavior = {
        "success": {
            "admitted_cell_changes": success_receipt["admitted_cell_changes"],
            "model_conservation": success_receipt["logical_model_admissions"]
            == success["model_slot_receipt"]["acquisitions"]
            + success["model_slot_receipt"]["slot_timeouts"],
            "fetch_conservation": success["result"]["cost"]["search"][
                "fetch_calls"
            ]
            == success["transport_health"]["hard_fetch_helper_calls"]
            + success["transport_health"]["fetch_deadline_rejections"],
        },
        "slot_reject": {
            "complete_result": raw["slot_reject"]["parent"][
                "failure_taxonomy"
            ]
            == "success",
            "pre_provider_rejections": slot_receipt[
                "pre_provider_model_rejections"
            ],
            "slot_timeouts": slot["model_slot_receipt"]["slot_timeouts"],
            "identity_handoff": slot_receipt["candidate_identity_handoff"],
        },
        "reserve_failure": {
            "complete_result": raw["reserve_failure"]["parent"][
                "failure_taxonomy"
            ]
            == "success",
            "identity_handoff": reserve_receipt["candidate_identity_handoff"],
            "fetch_helper_failures": reserve["transport_health"][
                "fetch_helper_failures"
            ],
        },
        "independent_receipt_drift_fail_closed": {
            "model": observed["drift_model"] == "result_envelope_invalid",
            "transport": observed["drift_transport"]
            == "result_envelope_invalid",
        },
    }
    watchers = protected_watcher_snapshot()
    process_present = bool(
        _matching(process_snapshot(), "tests/fixtures/v24326_synthetic_child.py")
        or _matching(process_snapshot(), "test_v24326_subprocess_integration.py")
    )
    findings: list[str] = []
    if accesses:
        findings.append("privileged_field_access_in_runtime_surface")
    if secret_hits:
        findings.append("credential_literal_in_source_surface")
    if not all(item["passed"] for item in test_results):
        findings.append("focused_or_dependency_regression_failed")
    if observed != EXPECTED_TAXONOMY:
        findings.append("parent_taxonomy_mismatch")
    if behavior != {
        "success": {
            "admitted_cell_changes": 1,
            "model_conservation": True,
            "fetch_conservation": True,
        },
        "slot_reject": {
            "complete_result": True,
            "pre_provider_rejections": 3,
            "slot_timeouts": 3,
            "identity_handoff": True,
        },
        "reserve_failure": {
            "complete_result": True,
            "identity_handoff": True,
            "fetch_helper_failures": 3,
        },
        "independent_receipt_drift_fail_closed": {
            "model": True,
            "transport": True,
        },
    }:
        findings.append("runner_behavior_drifted")
    if watchers != parent.get("protected_watchers"):
        findings.append("protected_watcher_identity_drifted")
    if process_present:
        findings.append("subprocess_or_test_process_remained_active")

    value = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_audit": {"path": str(PARENT), "sha256": sha256(root / PARENT)},
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "focused_and_dependency_tests": test_results,
        "test_count": sum(count for _, count in TESTS),
        "subprocess_fault_matrix": {
            "expected_taxonomy": EXPECTED_TAXONOMY,
            "observed_taxonomy": observed,
            "exact_taxonomy_match": observed == EXPECTED_TAXONOMY,
            "authoritative_local_children": len(MODES),
            "test_local_children": len(MODES),
            "total_local_children_this_audit": len(MODES) * 2,
            "temporary_directories_remaining": False,
        },
        "behavior_observation": behavior,
        "privileged_field_accesses": accesses,
        "credential_literal_hits": secret_hits,
        "subprocess_or_test_process_present": process_present,
        "protected_watchers": watchers,
        "external_effect_ledger": {
            "remote_network": 0,
            "model_provider": 0,
            "hosted_search": 0,
            "fetch": 0,
            "evaluator": 0,
            "local_subprocess_children": len(MODES) * 2,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "deadline_model_and_search_required_by_type": True,
            "shared_absolute_deadline_required": True,
            "independent_receipt_files_cross_checked_with_envelope": True,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "active_benchmark_or_watcher_signaled_restarted_or_modified": False,
        },
        "claim_scope": {
            "real_local_subprocess_boundary": True,
            "model_slot_and_fetch_health_cross_artifact_conservation": True,
            "slot_and_reserve_failures_return_complete_identity_results": True,
            "real_remote_model_or_search_transport_tested": False,
            "benchmark_quality_improvement": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "one_benchmark_external_neutral_transport_smoke_design": not findings,
            "neutral_transport_smoke_launch": False,
            "benchmark_launch": False,
            "additional_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate(value)
    return value


def validate(value: Mapping[str, Any]) -> None:
    if (
        value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or value.get("test_count") != 48
        or not all(
            item.get("passed") is True
            for item in value.get("focused_and_dependency_tests", [])
        )
        or value.get("subprocess_fault_matrix", {}).get("exact_taxonomy_match")
        is not True
        or value.get("privileged_field_accesses") != []
        or value.get("credential_literal_hits") != []
        or value.get("subprocess_or_test_process_present") is not False
        or value.get("external_effect_ledger", {}).get("remote_network") != 0
        or value.get("external_effect_ledger", {}).get("model_provider") != 0
        or value.get("authorization", {}).get(
            "one_benchmark_external_neutral_transport_smoke_design"
        )
        is not True
        or value.get("authorization", {}).get("benchmark_launch") is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.26 audit drifted")


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
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
