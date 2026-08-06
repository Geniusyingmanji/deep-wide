#!/usr/bin/env python3
"""Freeze the post-prediction V2.46.35 exact-220 evaluator protocol."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24635_exact220_contract import (  # noqa: E402
    FORWARD_CONTRACT,
    FORWARD_RESULT,
    LEASE_PATH,
    OUTPUT_ROOT,
    PREDICTION_FREEZE,
    PROTOCOL_ID,
    RUNTIME_PREDICTIONS,
    RUN_SUMMARY,
    SELECTED_COUNT,
    SOURCE_MANIFEST,
    payload_sha256,
    read_object,
    sha256,
    validate_forward_contract,
)
from scripts.finalize_fullset_rollout import (  # noqa: E402
    _live_answer_corpus_manifest_sha256,
    _live_evaluator_source_manifest_sha256,
)
from scripts.preregister_v24635_exact220 import publish_new  # noqa: E402


PROTOCOL = Path("results/v24635_exact220_evaluator_preregistration_v1_20260806.json")
FORWARD_AUDIT = Path("results/v24635_exact220_forward_audit_v1_20260806.json")
FINAL_RESULT = Path("results/v24635_exact220_result_v1_20260806.json")
POSTAUDIT = Path("results/v24635_exact220_postresult_audit_v1_20260806.json")
EVALUATOR_ROOT = OUTPUT_ROOT / "evaluator"
EVALUATOR_WORKERS = 32
MAPPING_PATH = Path("outputs/runtime_manifest_v1_repro/evaluator_mapping.jsonl")
QUERY_PATH = Path(
    "external/Marco-Search-Agent/Marco-DeepResearch-Family/DeepWideSearch/"
    "data/overall_20250916.jsonl"
)
ANSWER_ROOT = Path(
    "external/Marco-Search-Agent/Marco-DeepResearch-Family/DeepWideSearch/"
    "data/overall_20250916_tables"
)
PARENT_EVALUATOR_PROTOCOL = Path(
    "results/v24287_exact220_preregistration_v1_20260803.json"
)
CONTROL_FILES = (
    "scripts/preregister_v24635_exact220_evaluator.py",
    "scripts/finalize_v24635_exact220.py",
    "scripts/run_official_eval_local.py",
    "scripts/finalize_fullset_rollout.py",
    "scripts/finalize_v24287_exact220.py",
    "scripts/deepwide_api_lease.py",
)


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, check=True, timeout=20,
    ).stdout.strip()


def _tracked(root: Path, relative: str | Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)], cwd=root,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        check=False, timeout=20,
    ).returncode == 0


def _forward_barrier(root: Path) -> dict[str, Any]:
    contract = validate_forward_contract(root)
    audit = read_object(root / FORWARD_AUDIT)
    forward = read_object(root / FORWARD_RESULT)
    freeze = read_object(root / PREDICTION_FREEZE)
    if (
        audit.get("role") != "v24635_exact220_forward_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get("postfreeze_exact220_evaluator") is not True
        or audit.get("forward_result_sha256") != sha256(root / FORWARD_RESULT)
        or audit.get("prediction_freeze_sha256") != sha256(root / PREDICTION_FREEZE)
        or not _sealed(audit, "audit_payload_sha256")
        or forward.get("terminal_predictions") != SELECTED_COUNT
        or forward.get("official_evaluator_called") is not False
        or freeze.get("terminal") != SELECTED_COUNT
        or freeze.get("mapping_gold_or_evaluator_opened_or_hashed") is not False
        or freeze.get("runtime_predictions_sha256") != sha256(root / RUNTIME_PREDICTIONS)
        or freeze.get("run_summary_sha256") != sha256(root / RUN_SUMMARY)
        or not _sealed(forward, "result_payload_sha256")
        or not _sealed(freeze, "freeze_payload_sha256")
    ):
        raise RuntimeError("V2.46.35 exact-220 forward barrier drifted")
    return {"contract": contract, "audit": audit, "forward": forward, "freeze": freeze}


def _parent_evaluator(root: Path) -> dict[str, Any]:
    parent = read_object(root / PARENT_EVALUATOR_PROTOCOL)
    evaluator = parent.get("evaluator_contract")
    if not isinstance(evaluator, dict):
        raise RuntimeError("V2.46.35 parent evaluator contract is absent")
    copied = json.loads(json.dumps(evaluator))
    copied["mapping_query_answer_or_gold_bytes_opened_or_hashed"] = True
    copied["opened_only_after_v24635_exact220_prediction_freeze"] = True
    return copied


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_clean: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    barrier = _forward_barrier(root)
    head = _git(root, "rev-parse", "HEAD")
    target = _git(root, "rev-parse", "target/main")
    status = _git(root, "status", "--porcelain")
    controls_tracked = all(_tracked(root, relative) for relative in CONTROL_FILES)
    if require_clean and (head != target or status or not controls_tracked):
        raise RuntimeError(
            "V2.46.35 evaluator protocol requires clean pushed tracked controls"
        )
    if any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (PROTOCOL, FINAL_RESULT, POSTAUDIT, EVALUATOR_ROOT)
    ):
        raise RuntimeError("V2.46.35 evaluator future surface is not pristine")
    evaluator = _parent_evaluator(root)
    mapping = root / MAPPING_PATH
    query = root / QUERY_PATH
    answers = root / ANSWER_ROOT
    if (
        mapping.is_symlink() or not mapping.is_file()
        or query.is_symlink() or not query.is_file()
        or answers.is_symlink() or not answers.is_dir()
    ):
        raise RuntimeError("V2.46.35 evaluator resource is nonordinary")
    evaluator["mapping"] = {"path": str(MAPPING_PATH), "sha256": sha256(mapping)}
    evaluator["query_data"] = {"path": str(QUERY_PATH), "sha256": sha256(query)}
    evaluator["answer_corpus"] = {
        "root": str(ANSWER_ROOT),
        "manifest_sha256": _live_answer_corpus_manifest_sha256(answers),
    }
    evaluator["evaluator_source"] = {
        "manifest_sha256": _live_evaluator_source_manifest_sha256()
    }
    controls = {relative: sha256(root / relative) for relative in CONTROL_FILES}
    value = {
        "artifact_version": 1,
        "role": "v24635_exact220_evaluator_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "selected": SELECTED_COUNT,
        "evaluator_workers": EVALUATOR_WORKERS,
        "forward_barrier": {
            "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
            "forward_result_sha256": sha256(root / FORWARD_RESULT),
            "forward_audit_sha256": sha256(root / FORWARD_AUDIT),
            "prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
            "runtime_predictions_sha256": sha256(root / RUNTIME_PREDICTIONS),
            "run_summary_sha256": sha256(root / RUN_SUMMARY),
            "terminal_predictions": barrier["forward"]["terminal_predictions"],
            "mapping_or_evaluator_opened_during_forward": False,
        },
        "evaluator_contract": evaluator,
        "evaluation_contract": {
            "all_220_predictions_frozen_before_mapping_query_answer_or_evaluator_open": True,
            "fixed_contiguous_32_way_partition_in_prediction_order": True,
            "official_evaluator_on_every_frozen_prediction_exactly_once": True,
            "worker_error_rows_are_terminal_failure_as_zero": True,
            "selective_retry_revaluation_or_prediction_selection": False,
            "conservative_denominators": {"test_156": 156, "all_220": 220},
        },
        "outputs": {
            "evaluator_root": str(EVALUATOR_ROOT),
            "final_result": str(FINAL_RESULT),
            "postresult_audit": str(POSTAUDIT),
        },
        "lease": {
            "path": str(LEASE_PATH),
            "owner": "v24635_exact220_evaluator_v1",
            "purpose": "postfreeze_fixed_partition_parallel_exact220_official_evaluator",
            "nonblocking_single_owner": True,
        },
        "control_manifest": controls,
        "control_manifest_sha256": payload_sha256(controls),
        "git": {
            "source_head": head,
            "target_main": target,
            "source_head_equals_target_main": head == target,
            "worktree_clean_before_protocol": not status,
            "control_files_tracked": controls_tracked,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "mapping_opened_only_after_exact220_prediction_freeze": True,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
            "fixed_public_exact220_task_set_reexecuted": True,
            "new_or_disjoint_task_population_claimed": False,
            "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
        },
        "authorization": {
            "postfreeze_exact220_evaluation": True,
            "selective_retry_or_revaluation": False,
            "additional_rollout_avg4_leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return value


def validate_protocol(root: Path = ROOT, path: Path = PROTOCOL) -> dict[str, Any]:
    root = root.resolve()
    value = read_object(root / path)
    unsigned = dict(value)
    seal = unsigned.pop("protocol_payload_sha256", None)
    barrier = _forward_barrier(root)
    evaluator = value.get("evaluator_contract") or {}
    controls = value.get("control_manifest")
    if (
        value.get("role") != "v24635_exact220_evaluator_preregistration"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("selected") != SELECTED_COUNT
        or value.get("evaluator_workers") != EVALUATOR_WORKERS
        or value.get("forward_barrier", {}).get("forward_result_sha256")
        != sha256(root / FORWARD_RESULT)
        or value.get("forward_barrier", {}).get("prediction_freeze_sha256")
        != sha256(root / PREDICTION_FREEZE)
        or value.get("evaluation_contract", {}).get(
            "official_evaluator_on_every_frozen_prediction_exactly_once"
        )
        is not True
        or value.get("authorization", {}).get("selective_retry_or_revaluation") is not False
        or value.get("authorization", {}).get(
            "additional_rollout_avg4_leaderboard_or_sota"
        )
        is not False
        or evaluator.get("mapping", {}).get("sha256") != sha256(root / MAPPING_PATH)
        or evaluator.get("query_data", {}).get("sha256") != sha256(root / QUERY_PATH)
        or evaluator.get("answer_corpus", {}).get("manifest_sha256")
        != _live_answer_corpus_manifest_sha256(root / ANSWER_ROOT)
        or evaluator.get("evaluator_source", {}).get("manifest_sha256")
        != _live_evaluator_source_manifest_sha256()
        or evaluator.get("opened_only_after_v24635_exact220_prediction_freeze") is not True
        or value.get("source_policy", {}).get("fixed_public_exact220_task_set_reexecuted") is not True
        or value.get("source_policy", {}).get("new_or_disjoint_task_population_claimed") is not False
        or value.get("source_policy", {}).get(
            "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation"
        )
        is not True
        or not isinstance(controls, dict)
        or value.get("control_manifest_sha256") != payload_sha256(controls)
        or value.get("git", {}).get("source_head_equals_target_main") is not True
        or value.get("git", {}).get("worktree_clean_before_protocol") is not True
        or value.get("git", {}).get("control_files_tracked") is not True
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.46.35 evaluator protocol drifted")
    del barrier
    for relative, digest in controls.items():
        if sha256(root / relative) != digest:
            raise RuntimeError(f"V2.46.35 evaluator control drifted: {relative}")
    return value


if __name__ == "__main__":
    value = build_protocol()
    publish_new(ROOT / PROTOCOL, value)
    print(json.dumps({"path": str(PROTOCOL), "selected": SELECTED_COUNT, "workers": EVALUATOR_WORKERS}, sort_keys=True))
