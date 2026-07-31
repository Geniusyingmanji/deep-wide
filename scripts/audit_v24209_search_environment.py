#!/usr/bin/env python3
"""Freeze a label-blind search-environment audit for the current all-220.

This audit reads four config JSON files and the search/environment code hashes
they already attest.  It does not open benchmark manifests or selected-ID
files, inspect task content, read credentials, call a provider, or authorize a
benchmark launch.  Its result is a reusable environment-fingerprint mechanism
receipt plus a diagnostic fingerprint for the current R1 method.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24209_search_environment import (  # noqa: E402
    EXPECTED_SHARDS,
    build_all220_environment_attestation,
    payload_sha256,
)


ROLE = "v24209_search_environment_audit"
OUTPUT = Path("results/v24209_search_environment_audit_v1_20260731.json")
MODULE = Path("src/deepwide_agent/v24209_search_environment.py")
TEST = Path("tests/test_v24209_search_environment.py")
FREEZES = {
    "test_s01": Path("configs/full220_v2403_r1_test_s01_anthropic.json"),
    "test_s02": Path("configs/full220_v2403_r1_test_s02_anthropic.json"),
    "test_s03": Path("configs/full220_v2403_r1_test_s03_anthropic.json"),
    "devval": Path("configs/full220_v2403_r1_devval_s04_anthropic.json"),
}
CONTROL_FILES = (
    MODULE,
    Path("scripts/audit_v24209_search_environment.py"),
    TEST,
    Path("tests/test_audit_v24209_search_environment.py"),
)
FORBIDDEN_CAPABILITY_IMPORTS = frozenset(
    {
        "httpx",
        "multiprocessing",
        "requests",
        "socket",
        "subprocess",
    }
)
FORBIDDEN_URLLIB_IMPORTS = frozenset(
    {"urllib.error", "urllib.request", "urllib.response", "urllib.robotparser"}
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ordinary(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.42.09 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.42.09 expected an ordinary file: {relative}")
    return path


def _static_capability_audit(root: Path) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for relative in (MODULE, Path(__file__).resolve().relative_to(ROOT)):
        path = ordinary(root, relative)
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(relative))
        imported: set[str] = set()
        calls: set[str] = set()
        credential_environment_read = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "os"
                and node.attr == "environ"
            ):
                credential_environment_read = True
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
                and node.func.attr == "getenv"
            ):
                credential_environment_read = True
        if (
            {name.split(".")[0] for name in imported}
            & FORBIDDEN_CAPABILITY_IMPORTS
            or imported & FORBIDDEN_URLLIB_IMPORTS
            or "urllib" in imported
        ):
            raise RuntimeError("V2.42.09 forbidden network/process import appeared")
        if calls & {"eval", "exec", "compile"}:
            raise RuntimeError("V2.42.09 dynamic execution capability appeared")
        if credential_environment_read:
            raise RuntimeError("V2.42.09 credential environment read appeared")
        rows[str(relative)] = {
            "sha256": file_sha256(path),
            "forbidden_network_or_process_import": False,
            "credential_environment_read": False,
            "dynamic_execution": False,
        }
    return rows


def build_audit(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.09 may only audit the canonical workspace")
    ordinary(root, TEST)
    references = {
        tag: {
            "path": str(relative),
            "sha256": file_sha256(ordinary(root, relative)),
        }
        for tag, relative in FREEZES.items()
    }
    if tuple(references) != EXPECTED_SHARDS:
        raise RuntimeError("V2.42.09 shard order drifted")
    attestation = build_all220_environment_attestation(root, references)
    environment = attestation["search_environment"]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "label_blind": True,
        "current_r1_config_only_diagnostic": {
            "selected_total": attestation["selected_total"],
            "freeze_references": references,
            "environment_fingerprint_sha256": environment[
                "environment_fingerprint_sha256"
            ],
            "provider_runtime_identity": environment["provider"][
                "runtime_identity"
            ],
            "environment_code_file_count": len(
                environment["environment_code_sha256"]
            ),
            "one_environment_across_all_shards": attestation[
                "one_environment_across_all_shards"
            ],
            "provider_index_snapshot_pinned": attestation[
                "provider_index_snapshot_pinned"
            ],
            "not_a_fresh_candidate_or_quality_result": True,
        },
        "mechanism_contract": {
            "provider_model_endpoint_and_tool_schema_bound": True,
            "search_budget_and_query_isolation_bound": True,
            "observation_mapping_fetch_policy_and_submission_rule_bound": True,
            "transport_runtime_runner_and_launcher_bytes_bound": True,
            "all_four_shards_require_one_environment": True,
            "exact220_fixed_concurrency_no_resume_failure_as_zero_revalidated": True,
            "live_provider_index_shift_must_be_reported_separately": True,
            "future_environment_revalidation_before_executor_activation_required": True,
        },
        "static_capability_audit": _static_capability_audit(root),
        "control_surface": {
            "file_count": len(CONTROL_FILES),
            "manifest": {
                str(relative): file_sha256(ordinary(root, relative))
                for relative in CONTROL_FILES
            },
        },
        "runtime_task_manifest_or_selected_id_file_opened": False,
        "benchmark_question_answer_evidence_prediction_result_or_url_read": False,
        "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "active_process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        "active_benchmark_or_watcher_modified": False,
        "candidate_bundle_parallel_plan_or_output_root_materialized": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    value["control_surface"]["manifest_sha256"] = payload_sha256(
        value["control_surface"]["manifest"]
    )
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    if target != (ROOT / OUTPUT).resolve(strict=False):
        raise RuntimeError("V2.42.09 output path is noncanonical")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    target = target if target.is_absolute() else ROOT / target
    value = build_audit()
    publish_new(target, value)
    print(json.dumps({"path": str(target), "sha256": file_sha256(target)}))


if __name__ == "__main__":
    main()
