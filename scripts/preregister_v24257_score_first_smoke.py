#!/usr/bin/env python3
"""Freeze the bounded, label-blind V2.42.57 smoke16 experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24257_score_first_runtime import (  # noqa: E402
    ScoreFirstLimits,
)
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    sha256,
)


ROLE = "v24257_score_first_smoke_preregistration"
PROTOCOL_ID = "v24257_score_first_smoke16_v1"
OUTPUT = Path("results/v24257_score_first_smoke_preregistration_v1_20260802.json")
ACTIVATION = Path("results/v24257_score_first_smoke_activation_v1_20260802.json")
EXECUTION_START = Path(
    "results/v24257_score_first_smoke_execution_start_v1_20260802.json"
)
OUTPUT_ROOT = Path("outputs/v24257_score_first_smoke16_v1_20260802")
RESULT = Path("results/v24257_score_first_smoke_result_v1_20260802.json")
STATE = Path("outputs/v24257_score_first_smoke_watcher_state_v1_20260802.json")
MANIFEST = Path("outputs/runtime_manifest_v1_repro/manifest.jsonl")
ID_SOURCE = Path("configs/full220_v2403_r1_devval_s04.ids")
BASELINE = Path("results/full220_v2403_r1_20260725.json")
BASELINE_SEAL = Path("results/full220_v2403_r1_20260725_finalize_seal.json")
LEASE = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24257_score_first_smoke16_v1"
LEASE_PURPOSE = "bounded_label_blind_score_first_smoke16_engineering_gate"
RUNNER_MARKER = "scripts/run_v24257_score_first_smoke.py"
WATCHER_MARKER = "scripts/watch_v24257_score_first_smoke.py"
PARENT_COMPATIBILITY = Path(
    "results/v24195_lease_owner_compatibility_preregistration_v1_20260731.json"
)
PARENT_COMPATIBILITY_SHA256 = (
    "60d431acda5a95a0ee8d5ea75b970fcdd42ca3190d6d6e6c6b30a0e79978b4d7"
)
EXPECTED_LEGACY_ACTIVE_FINDING = "v24195:unknown_lease_owner"

CONTROL_FILES = (
    Path("src/deepwide_agent/v24257_score_first_runtime.py"),
    Path("scripts/run_v24257_score_first_task.py"),
    Path("scripts/run_v24257_score_first_smoke.py"),
    Path("scripts/preregister_v24257_score_first_smoke.py"),
    Path("scripts/activate_v24257_score_first_smoke.py"),
    Path("scripts/audit_v24257_score_first_smoke.py"),
    Path("scripts/watch_v24257_score_first_smoke.py"),
    Path("tests/test_v24257_score_first_runtime.py"),
    Path("tests/test_run_v24257_score_first_smoke.py"),
    Path("tests/test_preregister_v24257_score_first_smoke.py"),
    Path("tests/test_activate_v24257_score_first_smoke.py"),
    Path("tests/test_audit_v24257_score_first_smoke.py"),
    Path("tests/test_watch_v24257_score_first_smoke.py"),
)

FUTURE_PATHS = (ACTIVATION, EXECUTION_START, OUTPUT_ROOT, RESULT, STATE)
SECRET_LITERAL = re.compile(
    r"(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
OPAQUE_LITERAL = re.compile(r"task_[0-9a-f]{24}")


def _ordinary(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.42.57 path is noncanonical")
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.42.57 expected ordinary file: {relative}")
    return path


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected object: {path}")
    return value


def _selected_ids(root: Path, count: int = 16) -> list[str]:
    values = [
        line
        for line in _ordinary(root, ID_SOURCE).read_text(encoding="utf-8").splitlines()
        if line
    ]
    selected = values[:count]
    if (
        len(selected) != count
        or len(set(selected)) != count
        or any(re.fullmatch(r"task_[0-9a-f]{24}", value) is None for value in selected)
    ):
        raise RuntimeError("V2.42.57 selected opaque-ID prefix is invalid")
    return selected


def _baseline_summary(root: Path) -> dict[str, Any]:
    baseline_path = _ordinary(root, BASELINE)
    seal_path = _ordinary(root, BASELINE_SEAL)
    value = _read_object(baseline_path)
    seal = _read_object(seal_path)
    group = (value.get("groups") or {}).get("all_220") or {}
    metrics = group.get("conservative_all_selected") or {}
    completed = group.get("completed_valid_only") or {}
    if (
        value.get("rollout_id") != 1
        or value.get("status")
        != "public_fullset_single_rollout_complete_not_avg_at_4_not_sota"
        or group.get("selected") != 220
        or group.get("runtime_completed") != 47
        or group.get("runtime_failed") != 173
        or seal.get("role") != "full220_rollout1_finalization_seal"
        or seal.get("claims", {}).get("single_rollout") is not True
        or seal.get("claims", {}).get("leaderboard_or_sota") is not False
    ):
        raise RuntimeError("V2.42.57 baseline release pair drifted")
    return {
        "result": {"path": str(BASELINE), "sha256": sha256(baseline_path)},
        "seal": {"path": str(BASELINE_SEAL), "sha256": sha256(seal_path)},
        "selected": 220,
        "runtime_completed": 47,
        "runtime_failed": 173,
        "conservative_score": metrics.get("score"),
        "conservative_row_f1": metrics.get("f1_by_row"),
        "conservative_item_f1": metrics.get("f1_by_item"),
        "completed_valid_only_item_f1": completed.get("f1_by_item"),
        "consumed_public_engineering_result_not_independent_test": True,
    }


def build_protocol(
    root: Path = ROOT,
    *,
    created_at_unix: int | None = None,
    proc_root: Path = Path("/proc"),
    require_pristine: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    created = int(time.time()) if created_at_unix is None else int(created_at_unix)
    if sha256(_ordinary(root, PARENT_COMPATIBILITY)) != PARENT_COMPATIBILITY_SHA256:
        raise RuntimeError("V2.42.57 parent lease compatibility drifted")
    future_present = [
        str(path)
        for path in FUTURE_PATHS
        if (root / path).exists() or (root / path).is_symlink()
    ]
    if require_pristine and future_present:
        raise RuntimeError("V2.42.57 future execution surface is not pristine")
    selected = _selected_ids(root)
    lease = lease_observation(root, proc_root)
    if lease.get("active") is not False or lease.get("ordinary") is not True:
        raise RuntimeError("V2.42.57 shared API lease is active or invalid")
    limits = ScoreFirstLimits(
        wall_seconds=600,
        model_calls=3,
        search_queries=8,
        fetch_targets=16,
        search_results_per_query=3,
        evidence_chars=100_000,
        page_chars=5_000,
        plan_output_tokens=4_000,
        synthesis_output_tokens=30_000,
        repair_output_tokens=12_000,
    )
    limits.validate()
    manifest: dict[str, str] = {}
    for relative in CONTROL_FILES:
        path = _ordinary(root, relative)
        source = path.read_text(encoding="utf-8")
        if SECRET_LITERAL.search(source):
            raise RuntimeError(f"V2.42.57 control source contains a credential: {relative}")
        # Test fixtures may contain a synthetic opaque ID; production controls may not.
        if not str(relative).startswith("tests/") and OPAQUE_LITERAL.search(source):
            raise RuntimeError(f"V2.42.57 control source contains an opaque ID: {relative}")
        manifest[str(relative)] = sha256(path)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": created,
        "label_blind": True,
        "baseline": _baseline_summary(root),
        "task_contract": {
            "manifest": {
                "path": str(MANIFEST),
                "sha256": sha256(_ordinary(root, MANIFEST)),
                "row_schema": ["opaque_id", "question"],
            },
            "id_source": {
                "path": str(ID_SOURCE),
                "sha256": sha256(_ordinary(root, ID_SOURCE)),
            },
            "selection_rule": "first_16_in_frozen_devval_id_order",
            "selected_count": 16,
            "selected_opaque_ids_sha256": payload_sha256(selected),
            "selected_opaque_ids_persisted_or_emitted": False,
            "runtime_boundary": ["opaque_id", "question"],
            "already_consumed_engineering_smoke_not_independent_evaluation": True,
            "category_question_type_split_mapping_gold_score_used_for_selection": False,
        },
        "limits": {
            "wall_seconds": limits.wall_seconds,
            "model_calls": limits.model_calls,
            "search_queries": limits.search_queries,
            "fetch_targets": limits.fetch_targets,
            "search_results_per_query": limits.search_results_per_query,
            "evidence_chars": limits.evidence_chars,
            "page_chars": limits.page_chars,
            "plan_output_tokens": limits.plan_output_tokens,
            "synthesis_output_tokens": limits.synthesis_output_tokens,
            "repair_output_tokens": limits.repair_output_tokens,
        },
        "provider_contract": {
            "model": {
                "proxy_url": "http://127.0.0.1:9878/responses",
                "name": "gpt-5.6-sol",
                "reasoning_effort": "low",
                "service_tier": "priority",
                "timeout_seconds": 180,
                "max_retries": 2,
            },
            "search": {
                "provider": "anthropic-server-web-search",
                "model": "claude-haiku-4-5-20251001",
                "timeout_seconds": 90,
                "max_retries": 2,
                "workers": 4,
                "fetch_workers": 8,
                "fetch_timeout_seconds": 20,
                "server_search_max_uses_per_query": 1,
                "server_search_auto_fetch_disabled": True,
                "explicit_page_fetches_share_task_cap": True,
            },
            "credentials_environment_only_not_persisted_hashed_or_emitted": True,
        },
        "gate_contract": {
            "minimum_model_generated_tables": 15,
            "maximum_fallback_tables": 1,
            "maximum_hard_deadline_fallbacks": 1,
            "maximum_p95_wall_seconds": 600,
            "maximum_mean_system_tokens": 750_000,
            "maximum_mean_fetch_calls": 200,
            "primary_or_repaired_only_counts_as_model_generated": True,
            "schema_only_fallback_does_not_count_as_completion_improvement": True,
            "go_authorizes_paired_dev64_design_only": True,
            "go_does_not_authorize_dev64_full220_evaluator_or_leaderboard": True,
        },
        "lease_contract": {
            "path": str(LEASE),
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
            "nonblocking_posix_flock_required": True,
            "single_owner_across_all_16_tasks": True,
            "parent_compatibility": {
                "path": str(PARENT_COMPATIBILITY),
                "sha256": PARENT_COMPATIBILITY_SHA256,
                "legacy_expected_active_finding": EXPECTED_LEGACY_ACTIVE_FINDING,
                "append_only_overlay_may_suppress_only_exact_unknown_owner_finding": True,
                "exact_live_runner_pid_owner_purpose_and_lock_holder_required": True,
            },
        },
        "execution": {
            "runner_marker": RUNNER_MARKER,
            "task_runner_marker": "scripts/run_v24257_score_first_task.py",
            "watcher_marker": WATCHER_MARKER,
            "python_flags": ["-I", "-B"],
            "activation_path": str(ACTIVATION),
            "execution_start_path": str(EXECUTION_START),
            "output_root": str(OUTPUT_ROOT),
            "result_path": str(RESULT),
            "watcher_state_path": str(STATE),
            "executor_concurrency": 1,
            "parent_deadline_grace_seconds": 5,
            "child_process_group_terminated_at_hard_deadline": True,
            "forward_resume_or_selective_rerun_allowed": False,
            "result_overwrite_allowed": False,
        },
        "source_policy": {
            "visible_question_and_same_pass_tool_results_only": True,
            "mapping_gold_category_question_type_evaluator_score_read": False,
            "same_run_evaluator_feedback_used_for_forward_or_tuning": False,
            "question_query_url_page_prediction_or_answer_in_safe_progress": False,
            "credential_value_persisted_hashed_or_emitted": False,
        },
        "authorization": {
            "activation_publish_after_protocol_freeze": True,
            "single_smoke16_forward_after_activation_and_shared_lease": True,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
            "official_evaluator_call": False,
            "paired_dev64_or_full220_launch": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "safe_freeze_boundary": {
            "future_paths_present": future_present,
            "shared_api_lease_active": False,
            "existing_benchmark_or_watcher_signaled_restarted_modified_or_terminated": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
        },
        "control_surface": {
            "file_count": len(manifest),
            "manifest": manifest,
            "manifest_sha256": payload_sha256(manifest),
        },
    }
    value["decision_contract_sha256"] = payload_sha256(value)
    return value


def validate_protocol(root: Path, path: Path = OUTPUT) -> dict[str, Any]:
    target = _ordinary(root.resolve(), path)
    value = _read_object(target)
    unsigned = dict(value)
    seal = unsigned.pop("decision_contract_sha256", None)
    if (
        value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("label_blind") is not True
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.57 protocol seal or identity drifted")
    manifest = value.get("control_surface", {}).get("manifest")
    if (
        not isinstance(manifest, dict)
        or value["control_surface"].get("file_count") != len(manifest)
        or value["control_surface"].get("manifest_sha256")
        != payload_sha256(manifest)
    ):
        raise RuntimeError("V2.42.57 control manifest drifted")
    for relative, digest in manifest.items():
        if sha256(_ordinary(root.resolve(), Path(relative))) != digest:
            raise RuntimeError(f"V2.42.57 control source drifted: {relative}")
    ScoreFirstLimits(**dict(value["limits"])).validate()
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to((ROOT / "results").resolve()):
        raise RuntimeError("V2.42.57 protocol output is noncanonical")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        parent = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    output = Path(args.output)
    output = output if output.is_absolute() else ROOT / output
    value = build_protocol()
    publish_new(output, value)
    print(json.dumps({"path": str(output), "sha256": sha256(output)}))


if __name__ == "__main__":
    main()
