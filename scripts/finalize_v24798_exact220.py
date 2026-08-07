#!/usr/bin/env python3
"""Audit and evaluate the frozen V2.47.98 exact-220 predictions."""

from __future__ import annotations

import argparse
import copy
import fcntl
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

from deepwide_agent import v24635_exact220_contract as parent_contract  # noqa: E402
from deepwide_agent import v24798_exact220_contract as contract  # noqa: E402
from scripts import finalize_v24287_exact220 as evaluator  # noqa: E402
from scripts.finalize_fullset_rollout import (  # noqa: E402
    _live_answer_corpus_manifest_sha256,
    _live_evaluator_source_manifest_sha256,
    summarize_rollout,
)


FORWARD_AUDIT = contract.FORWARD_AUDIT
EVALUATOR_PROTOCOL = Path(f"results/v24798_exact220_evaluator_preregistration_v1_{contract.DATE}.json")
FINAL_RESULT = Path(f"results/v24798_exact220_result_v1_{contract.DATE}.json")
POSTAUDIT = Path(f"results/v24798_exact220_postresult_audit_v1_{contract.DATE}.json")
EVALUATOR_ROOT = contract.OUTPUT_ROOT / "evaluator"
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
SOURCE_MANIFEST = parent_contract.SOURCE_MANIFEST
PARENT_EVALUATOR_PROTOCOL = Path("results/v24635_exact220_evaluator_preregistration_v1_20260806.json")
PREPARE_ATTESTATION = EVALUATOR_ROOT / "prepare_attestation.json"
JOINED_OUTCOMES = EVALUATOR_ROOT / "terminal_outcomes_evaluator_joined.jsonl"
OFFICIAL_PREDICTIONS = EVALUATOR_ROOT / "official_predictions.jsonl"
EVALUATOR_RUNS = EVALUATOR_ROOT / "official_eval_workers"
EVALUATOR_LOGS = EVALUATOR_ROOT / "logs"
MERGED_RESULTS = EVALUATOR_ROOT / "official_eval_results.jsonl"
MERGE_ATTESTATION = EVALUATOR_ROOT / "merge_attestation.json"
SUMMARY = EVALUATOR_ROOT / "conservative_summary.json"
EVALUATOR_OWNER = "v24798_exact220_evaluator_v1"
EVALUATOR_PURPOSE = "postfreeze_fixed_partition_parallel_exact220_official_evaluator"
CONTROL_FILES = (
    "scripts/finalize_v24798_exact220.py",
    "scripts/run_official_eval_local.py",
    "scripts/finalize_v24287_exact220.py",
    "scripts/finalize_fullset_rollout.py",
    "scripts/deepwide_api_lease.py",
    "tests/test_finalize_v24798_exact220.py",
)
REFERENCES = {
    "v24267": Path("results/v24267_exact220_result_v1_20260802.json"),
    "v24287": Path("results/v24287_exact220_result_v1_20260803.json"),
    "v24630": Path("results/v24630_exact220_result_v1_20260806.json"),
    "v24635": Path("results/v24635_exact220_result_v1_20260806.json"),
}
QUALITY_METRICS = (
    "score", "entity_acc", "precision_by_row", "recall_by_row", "f1_by_row",
    "precision_by_item", "recall_by_item", "f1_by_item", "column_precision",
    "column_recall", "column_f1",
)
RESULT_CLAIMS = {
    "public_exact220_single_rollout": True,
    "cold_execution": True,
    "unseen_or_held_out": False,
    "new_or_disjoint_task_population": False,
    "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
    "avg_at_4": False,
    "leaderboard_submitted": False,
    "sota": False,
}
RESULT_AUTHORIZATION = {
    "additional_rollout_or_avg4": False,
    "selective_retry_or_revaluation": False,
    "leaderboard_submission": False,
    "sota_claim": False,
}


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError(f"V2.47.98 evaluator expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.98 evaluator expected JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.47.98 evaluator expected ordinary JSONL: {path}")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.47.98 evaluator expected JSON objects")
    return rows


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def _tracked(path: str | Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)], cwd=ROOT,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, timeout=20, check=False,
    ).returncode == 0


def _lease_inactive() -> bool:
    path = ROOT / contract.LEASE_PATH
    if path.is_symlink():
        return False
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def _active(markers: tuple[str, ...]) -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="], stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=False,
    )
    output = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if (
            len(parts) >= 3
            and int(parts[0]) != os.getpid()
            and "python" in parts[1].casefold()
            and any(marker in parts[2] for marker in markers)
        ):
            output.append(int(parts[0]))
    return sorted(output)


def _forward_barrier() -> dict[str, Any]:
    protocol = contract.validate_protocol(ROOT, _read(ROOT / contract.PROTOCOL))
    forward = _read(ROOT / contract.FORWARD_RESULT)
    summary = _read(ROOT / contract.RUN_SUMMARY)
    freeze = _read(ROOT / contract.PREDICTION_FREEZE)
    rows = _read_jsonl(ROOT / contract.RUNTIME_PREDICTIONS)
    tasks = contract.task_vector(ROOT, protocol)
    row_hashes = [row.get("prediction_sha256") for row in rows]
    if (
        forward.get("role") != "v24798_exact220_forward_result"
        or forward.get("protocol_id") != contract.PROTOCOL_ID
        or forward.get("selected") != 220 or forward.get("terminal_predictions") != 220
        or forward.get("official_evaluator_called") is not False
        or forward.get("all_220_predictions_terminal_before_mapping_or_evaluator_open") is not True
        or forward.get("mapping_gold_category_question_type_split_evaluator_score_reward_read") is not False
        or not _sealed(forward, "result_payload_sha256")
        or summary.get("role") != "v24798_exact220_run_summary"
        or summary.get("selected") != 220 or summary.get("completed") != 220
        or summary.get("failed") != 0
        or int(summary.get("model_generated_tables", -1)) + int(summary.get("fallback_tables", -1)) != 220
        or not _sealed(summary, "summary_payload_sha256")
        or freeze.get("role") != "v24798_exact220_prediction_freeze"
        or freeze.get("selected") != 220 or freeze.get("terminal") != 220
        or freeze.get("mapping_gold_or_evaluator_opened_or_hashed") is not False
        or freeze.get("runtime_predictions_sha256") != contract.sha256(ROOT / contract.RUNTIME_PREDICTIONS)
        or freeze.get("run_summary_sha256") != contract.sha256(ROOT / contract.RUN_SUMMARY)
        or freeze.get("prediction_hashes_sha256") != contract.payload_sha256(row_hashes)
        or not _sealed(freeze, "freeze_payload_sha256")
        or len(rows) != 220
        or [row.get("opaque_id") for row in rows] != [task["opaque_id"] for task in tasks]
        or any(
            row.get("status") != "completed" or row.get("label_blind") is not True
            or row.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
            or not isinstance(row.get("prediction"), str) or not row["prediction"]
            for row in rows
        )
    ):
        raise RuntimeError("V2.47.98 frozen forward barrier drifted")
    return {"protocol": protocol, "forward": forward, "summary": summary, "freeze": freeze, "runtime_rows": rows}


def build_forward_audit(*, now: int | None = None) -> dict[str, Any]:
    barrier = _forward_barrier()
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    checks = {
        "exact220_barrier_valid": True,
        "forward_result_commit_pushed": head == remote and _tracked(contract.FORWARD_RESULT),
        "worktree_clean": _git("status", "--porcelain") == "",
        "shared_api_lease_released": _lease_inactive(),
        "forward_runner_and_children_absent": not _active((contract.RUNNER_MARKER, contract.CHILD_MARKER)),
        "protected_watchers_unchanged": contract.protected_watcher_snapshot() == barrier["protocol"]["execution"]["protected_watchers"],
        "future_evaluator_surface_pristine": all(
            not (ROOT / path).exists() and not (ROOT / path).is_symlink()
            for path in (FORWARD_AUDIT, EVALUATOR_PROTOCOL, FINAL_RESULT, POSTAUDIT, EVALUATOR_ROOT)
        ),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v24798_exact220_forward_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "runtime_predictions_sha256": contract.sha256(ROOT / contract.RUNTIME_PREDICTIONS),
        "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
        "selected": 220,
        "terminal_predictions": barrier["forward"]["terminal_predictions"],
        "model_generated_tables": barrier["forward"]["model_generated_tables"],
        "fallback_tables": barrier["forward"]["fallback_tables"],
        "forward_wall_seconds": barrier["forward"]["forward_wall_seconds"],
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "postfreeze_exact220_evaluator_protocol": not findings,
            "forward_retry_resume_skip_or_rerun": False,
            "selective_evaluation_or_revaluation": False,
            "leaderboard_or_sota": False,
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_audit": False,
        "network_model_search_fetch_or_evaluator_called_by_audit": False,
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_forward_audit(value: dict[str, Any]) -> dict[str, Any]:
    if (
        value.get("role") != "v24798_exact220_forward_audit"
        or value.get("protocol_id") != contract.PROTOCOL_ID
        or value.get("audit_valid") is not True or value.get("findings") != []
        or value.get("forward_result_sha256") != contract.sha256(ROOT / contract.FORWARD_RESULT)
        or value.get("prediction_freeze_sha256") != contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        or value.get("authorization", {}).get("postfreeze_exact220_evaluator_protocol") is not True
        or value.get("authorization", {}).get("selective_evaluation_or_revaluation") is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.98 forward audit drifted")
    return value


def _parent_evaluator_contract() -> dict[str, Any]:
    parent = _read(ROOT / PARENT_EVALUATOR_PROTOCOL)
    value = copy.deepcopy(parent.get("evaluator_contract"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.98 parent evaluator contract absent")
    value.pop("opened_only_after_v24635_exact220_prediction_freeze", None)
    value["opened_only_after_v24798_exact220_prediction_freeze"] = True
    value["mapping_query_answer_or_gold_bytes_opened_or_hashed"] = True
    return value


def build_evaluator_protocol(*, now: int | None = None) -> dict[str, Any]:
    barrier = _forward_barrier()
    audit = validate_forward_audit(_read(ROOT / FORWARD_AUDIT))
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main"):
        raise RuntimeError("V2.47.98 evaluator protocol requires clean pushed HEAD")
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (EVALUATOR_PROTOCOL, FINAL_RESULT, POSTAUDIT, EVALUATOR_ROOT)):
        raise RuntimeError("V2.47.98 evaluator future surface not pristine")
    if not all(_tracked(path) for path in CONTROL_FILES):
        raise RuntimeError("V2.47.98 evaluator controls are not tracked")
    mapping = ROOT / MAPPING_PATH
    query = ROOT / QUERY_PATH
    answers = ROOT / ANSWER_ROOT
    if mapping.is_symlink() or not mapping.is_file() or query.is_symlink() or not query.is_file() or answers.is_symlink() or not answers.is_dir():
        raise RuntimeError("V2.47.98 evaluator resource is nonordinary")
    evaluator_contract = _parent_evaluator_contract()
    evaluator_contract["mapping"] = {"path": str(MAPPING_PATH), "sha256": contract.sha256(mapping)}
    evaluator_contract["query_data"] = {"path": str(QUERY_PATH), "sha256": contract.sha256(query)}
    evaluator_contract["answer_corpus"] = {"root": str(ANSWER_ROOT), "manifest_sha256": _live_answer_corpus_manifest_sha256(answers)}
    evaluator_contract["evaluator_source"] = {"manifest_sha256": _live_evaluator_source_manifest_sha256()}
    controls = {str(path): contract.sha256(ROOT / path) for path in CONTROL_FILES}
    value = {
        "artifact_version": 1,
        "role": "v24798_exact220_evaluator_preregistration",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "selected": 220,
        "evaluator_workers": EVALUATOR_WORKERS,
        "forward_barrier": {
            "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
            "forward_audit_sha256": contract.sha256(ROOT / FORWARD_AUDIT),
            "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
            "runtime_predictions_sha256": contract.sha256(ROOT / contract.RUNTIME_PREDICTIONS),
            "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
            "terminal_predictions": barrier["forward"]["terminal_predictions"],
            "mapping_or_evaluator_opened_during_forward": False,
        },
        "evaluator_contract": evaluator_contract,
        "evaluation_contract": {
            "all_220_predictions_frozen_before_mapping_query_answer_or_evaluator_open": True,
            "fixed_contiguous_32_way_partition_in_prediction_order": True,
            "official_evaluator_on_every_frozen_prediction_exactly_once": True,
            "worker_error_rows_are_terminal_failure_as_zero": True,
            "selective_retry_revaluation_or_prediction_selection": False,
            "conservative_denominators": {"test_156": 156, "all_220": 220},
        },
        "outputs": {"evaluator_root": str(EVALUATOR_ROOT), "final_result": str(FINAL_RESULT), "postresult_audit": str(POSTAUDIT)},
        "lease": {"path": str(contract.LEASE_PATH), "owner": EVALUATOR_OWNER, "purpose": EVALUATOR_PURPOSE, "nonblocking_single_owner": True},
        "control_manifest": controls,
        "control_manifest_sha256": contract.payload_sha256(controls),
        "forward_audit_payload_sha256": audit["audit_payload_sha256"],
        "source_policy": {
            "mapping_opened_only_after_exact220_prediction_freeze_and_pushed_audit": True,
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
    value["protocol_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_evaluator_protocol(value: dict[str, Any]) -> dict[str, Any]:
    evaluator_contract = value.get("evaluator_contract") or {}
    controls = value.get("control_manifest")
    if (
        value.get("role") != "v24798_exact220_evaluator_preregistration"
        or value.get("protocol_id") != contract.PROTOCOL_ID
        or value.get("selected") != 220 or value.get("evaluator_workers") != 32
        or value.get("forward_barrier", {}).get("forward_result_sha256") != contract.sha256(ROOT / contract.FORWARD_RESULT)
        or value.get("forward_barrier", {}).get("forward_audit_sha256") != contract.sha256(ROOT / FORWARD_AUDIT)
        or value.get("forward_barrier", {}).get("prediction_freeze_sha256") != contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        or evaluator_contract.get("mapping", {}).get("sha256") != contract.sha256(ROOT / MAPPING_PATH)
        or evaluator_contract.get("query_data", {}).get("sha256") != contract.sha256(ROOT / QUERY_PATH)
        or evaluator_contract.get("answer_corpus", {}).get("manifest_sha256") != _live_answer_corpus_manifest_sha256(ROOT / ANSWER_ROOT)
        or evaluator_contract.get("evaluator_source", {}).get("manifest_sha256") != _live_evaluator_source_manifest_sha256()
        or evaluator_contract.get("opened_only_after_v24798_exact220_prediction_freeze") is not True
        or not isinstance(controls, dict) or value.get("control_manifest_sha256") != contract.payload_sha256(controls)
        or any(contract.sha256(ROOT / path) != digest for path, digest in controls.items())
        or value.get("authorization") != {"postfreeze_exact220_evaluation": True, "selective_retry_or_revaluation": False, "additional_rollout_avg4_leaderboard_or_sota": False}
        or not _sealed(value, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.47.98 evaluator protocol drifted")
    _forward_barrier()
    validate_forward_audit(_read(ROOT / FORWARD_AUDIT))
    return value


def fixed_partitions() -> list[tuple[int, int]]:
    base, remainder = divmod(220, EVALUATOR_WORKERS)
    output = []
    start = 0
    for index in range(EVALUATOR_WORKERS):
        size = base + (1 if index < remainder else 0)
        output.append((start, start + size))
        start += size
    if start != 220 or len(output) != 32:
        raise RuntimeError("V2.47.98 evaluator partition drifted")
    return output


def _algorithm_contract() -> dict[str, Any]:
    return {"task_contract": {"manifest_sha256": contract.sha256(ROOT / SOURCE_MANIFEST)}}


def selected_ids(_value: dict[str, Any]) -> list[str]:
    return [task["opaque_id"] for task in contract.task_vector(ROOT)]


def configure_evaluator() -> None:
    assignments = {
        "PROTOCOL": EVALUATOR_PROTOCOL, "FINAL_RESULT": FINAL_RESULT,
        "EVALUATOR_ROOT": EVALUATOR_ROOT, "EVALUATOR_WORKERS": EVALUATOR_WORKERS,
        "MAPPING_PATH": MAPPING_PATH, "PREPARE_ATTESTATION": PREPARE_ATTESTATION,
        "JOINED_OUTCOMES": JOINED_OUTCOMES, "OFFICIAL_PREDICTIONS": OFFICIAL_PREDICTIONS,
        "EVALUATOR_RUNS": EVALUATOR_RUNS, "EVALUATOR_LOGS": EVALUATOR_LOGS,
        "MERGED_RESULTS": MERGED_RESULTS, "MERGE_ATTESTATION": MERGE_ATTESTATION,
        "SUMMARY": SUMMARY, "EVALUATOR_OWNER": EVALUATOR_OWNER,
        "EVALUATOR_PURPOSE": EVALUATOR_PURPOSE, "FORWARD_CONTRACT": contract.PROTOCOL,
        "FORWARD_RESULT": contract.FORWARD_RESULT, "OUTPUT_ROOT": contract.OUTPUT_ROOT,
        "PREDICTION_FREEZE": contract.PREDICTION_FREEZE,
        "RUNTIME_PREDICTIONS": contract.RUNTIME_PREDICTIONS,
        "RUN_SUMMARY": contract.RUN_SUMMARY, "SOURCE_MANIFEST": SOURCE_MANIFEST,
        "SELECTED_COUNT": 220, "PROTOCOL_ID": contract.PROTOCOL_ID,
        "LEASE_PATH": contract.LEASE_PATH,
    }
    for name, value in assignments.items():
        setattr(evaluator, name, value)
    evaluator.validate_protocol = lambda _root, _path=EVALUATOR_PROTOCOL: validate_evaluator_protocol(_read(ROOT / _path))
    evaluator.validate_forward_contract = lambda _root: _algorithm_contract()
    evaluator.validate_forward_barrier = lambda _root, _contract: _forward_barrier()
    evaluator.selected_ids = selected_ids
    evaluator.fixed_partitions = fixed_partitions


def _group_metrics(summary: dict[str, Any], name: str) -> dict[str, Any]:
    if name == "test_156":
        rows = [row for row in summary["per_task"] if row["split"] == "test"]
    elif name == "all_220":
        rows = list(summary["per_task"])
    else:
        raise ValueError(f"V2.47.98 unsupported metric group: {name}")
    group = summary["groups"][name]
    conservative = group["conservative_all_selected"]
    return {
        "selected": group["selected"],
        "evaluator_valid": group["evaluator_valid"],
        "evaluator_invalid_or_not_run": group["evaluator_invalid_or_not_run"],
        "whole_table_successes": sum(row["evaluator_valid"] and row["metrics"]["score"] > 0 for row in rows),
        "entity_acc": float(conservative["entity_acc"]),
        "f1_by_row": float(conservative["f1_by_row"]),
        "f1_by_item": float(conservative["f1_by_item"]),
        "column_f1": float(conservative["column_f1"]),
        "quality_composite": sum(float(conservative[key]) for key in ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")) / 4,
        "score": float(conservative["score"]),
    }


def _comparison(current: dict[str, Any], path: Path) -> dict[str, Any]:
    parent = _read(ROOT / path)
    metrics = parent["metrics"].get("all_220", parent["metrics"])
    return {
        "reference_result_sha256": contract.sha256(ROOT / path),
        "whole_table_success_delta": current["whole_table_successes"] - metrics["whole_table_successes"],
        "score_delta": current["score"] - metrics["score"],
        "quality_composite_delta": current["quality_composite"] - metrics["quality_composite"],
    }


def _expected_partitions() -> list[dict[str, int]]:
    return [
        {"worker": index + 1, "start": start, "end": end}
        for index, (start, end) in enumerate(fixed_partitions())
    ]


def validate_evaluation_artifacts(protocol: dict[str, Any]) -> dict[str, Any]:
    """Prove fixed-order, exactly-once evaluator coverage before trusting metrics."""
    validate_evaluator_protocol(protocol)
    configure_evaluator()
    prepare = _read(ROOT / PREPARE_ATTESTATION)
    merge = _read(ROOT / MERGE_ATTESTATION)
    summary = _read(ROOT / SUMMARY)
    joined = _read_jsonl(ROOT / JOINED_OUTCOMES)
    official = _read_jsonl(ROOT / OFFICIAL_PREDICTIONS)
    merged = _read_jsonl(ROOT / MERGED_RESULTS)
    expected_opaque_ids = selected_ids({})
    joined_opaque_ids = [str(row.get("opaque_id")) for row in joined]
    joined_ids = [str(row.get("instance_id")) for row in joined]
    official_ids = [str(row.get("instance_id")) for row in official]
    merged_ids = [str(row.get("instance_id")) for row in merged]
    partitions = _expected_partitions()
    reports = merge.get("worker_reports") or []
    worker_ids: list[str] = []
    worker_errors = 0
    worker_rows = 0
    for index, partition in enumerate(partitions):
        worker = partition["worker"]
        start, end = partition["start"], partition["end"]
        shard_path = ROOT / EVALUATOR_RUNS / f"worker_{worker:02d}_predictions.jsonl"
        run_root = ROOT / EVALUATOR_RUNS / f"worker_{worker:02d}"
        result_path = run_root / "official_eval_results.jsonl"
        config_path = run_root / "run_config.json"
        log_path = ROOT / EVALUATOR_LOGS / f"worker_{worker:02d}.log"
        shard = _read_jsonl(shard_path)
        rows = _read_jsonl(result_path)
        shard_ids = [str(row.get("instance_id")) for row in shard]
        row_ids = [str(row.get("instance_id")) for row in rows]
        report = reports[index] if index < len(reports) else {}
        run_summary = _read(run_root / "summary.json")
        if (
            shard_ids != official_ids[start:end]
            or row_ids != shard_ids
            or report.get("worker") != worker
            or report.get("returncode") != 0
            or report.get("start") != start
            or report.get("end") != end
            or report.get("selected") != end - start
            or report.get("prediction_shard_sha256") != contract.sha256(shard_path)
            or report.get("results_sha256") != contract.sha256(result_path)
            or report.get("run_config_sha256") != contract.sha256(config_path)
            or report.get("log_sha256") != contract.sha256(log_path)
            or run_summary.get("n") != end - start
            or int(run_summary.get("valid_n", -1)) + int(run_summary.get("errors", -1)) != end - start
        ):
            raise RuntimeError(f"V2.47.98 evaluator worker {worker} artifact drifted")
        evaluator.validate_evaluator_contract(
            config_path,
            expected_predictions_path=shard_path,
            expected_predictions_sha256=contract.sha256(shard_path),
            expected_selected_count=end - start,
        )
        worker_ids.extend(row_ids)
        worker_rows += len(rows)
        worker_errors += int(run_summary["errors"])

    prepare_unsigned = dict(prepare)
    prepare_seal = prepare_unsigned.pop("prepare_payload_sha256", None)
    merge_unsigned = dict(merge)
    merge_seal = merge_unsigned.pop("merge_payload_sha256", None)
    per_task = summary.get("per_task") or []
    invalid = [row for row in per_task if row.get("evaluator_valid") is not True]
    all_group = (summary.get("groups") or {}).get("all_220") or {}
    test_group = (summary.get("groups") or {}).get("test_156") or {}
    if (
        len(joined) != len(official) or len(official) != len(merged) or len(merged) != 220
        or joined_opaque_ids != expected_opaque_ids
        or len(set(joined_opaque_ids)) != 220
        or joined_ids != official_ids or official_ids != worker_ids or worker_ids != merged_ids
        or len(set(official_ids)) != 220 or worker_rows != 220
        or any(row.get("status") != "completed" for row in joined)
        or prepare.get("terminal_outcomes_sha256") != contract.sha256(ROOT / JOINED_OUTCOMES)
        or prepare.get("official_predictions_sha256") != contract.sha256(ROOT / OFFICIAL_PREDICTIONS)
        or prepare.get("runtime_predictions_sha256") != contract.sha256(ROOT / contract.RUNTIME_PREDICTIONS)
        or prepare.get("prediction_freeze_sha256") != contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        or prepare.get("both_forward_and_freeze_exact220_before_mapping_open") is not True
        or prepare_seal != contract.payload_sha256(prepare_unsigned)
        or merge.get("selected") != 220 or merge.get("workers") != 32
        or merge.get("fixed_contiguous_partitions") != partitions
        or len(reports) != 32
        or merge.get("all_frozen_predictions_evaluated_exactly_once") is not True
        or merge.get("selective_retry_or_revaluation") is not False
        or merge.get("merged_results_sha256") != contract.sha256(ROOT / MERGED_RESULTS)
        or merge_seal != contract.payload_sha256(merge_unsigned)
        or len(per_task) != 220
        or [str(row.get("opaque_id")) for row in per_task] != expected_opaque_ids
        or [str(row.get("instance_id")) for row in per_task] != official_ids
        or all_group.get("selected") != 220
        or (all_group.get("conservative_all_selected") or {}).get("denominator") != 220
        or test_group.get("selected") != 156
        or (test_group.get("conservative_all_selected") or {}).get("denominator") != 156
        or len(invalid) != all_group.get("evaluator_invalid_or_not_run")
        or len(invalid) != worker_errors
        or any(
            any(float((row.get("metrics") or {}).get(metric, 1.0)) != 0.0 for metric in QUALITY_METRICS)
            for row in invalid
        )
    ):
        raise RuntimeError("V2.47.98 exact-220 evaluator coverage or conservative summary drifted")
    return {
        "joined_rows": len(joined),
        "official_rows": len(official),
        "merged_rows": len(merged),
        "unique_instance_ids": len(set(official_ids)),
        "workers": len(partitions),
        "worker_returncodes_zero": True,
        "worker_errors_terminal_zero": len(invalid),
        "all220_conservative_denominator": 220,
        "test156_conservative_denominator": 156,
    }


def validate_final_result(value: dict[str, Any], protocol: dict[str, Any]) -> dict[str, Any]:
    artifacts = validate_evaluation_artifacts(protocol)
    barrier = _forward_barrier()
    summary = _read(ROOT / SUMMARY)
    merge = _read(ROOT / MERGE_ATTESTATION)
    live = evaluator.validate_live_evaluator_identity(ROOT, protocol)
    expected_metrics = {
        "test_156": _group_metrics(summary, "test_156"),
        "all_220": _group_metrics(summary, "all_220"),
    }
    expected_metrics["all_220"].update({
        "model_generated_tables": barrier["forward"]["model_generated_tables"],
        "fallback_tables": barrier["forward"]["fallback_tables"],
        "system_total_tokens": barrier["forward"]["system_total_tokens"],
    })
    expected_comparisons = {
        name: _comparison(expected_metrics["all_220"], path)
        for name, path in REFERENCES.items()
    }
    expected_provenance = {
        "evaluator_protocol_sha256": contract.sha256(ROOT / EVALUATOR_PROTOCOL),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "forward_audit_sha256": contract.sha256(ROOT / FORWARD_AUDIT),
        "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "mapping_sha256": contract.sha256(ROOT / MAPPING_PATH),
        "query_data_sha256": live["query_data_sha256"],
        "answer_corpus_manifest_sha256": live["answer_corpus_manifest_sha256"],
        "evaluator_source_manifest_sha256": live["evaluator_source_manifest_sha256"],
        "judge": live["judge"],
        "recovery_policy": live["recovery_policy"],
        "merged_official_eval_results_sha256": contract.sha256(ROOT / MERGED_RESULTS),
        "parallel_merge_attestation_sha256": contract.sha256(ROOT / MERGE_ATTESTATION),
        "conservative_summary_sha256": contract.sha256(ROOT / SUMMARY),
    }
    expected_source_policy = {
        "runtime_boundary": ["opaque_id", "question"],
        "mapping_opened_only_after_exact220_prediction_freeze_and_pushed_audit": True,
        "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        "fixed_public_exact220_task_set_reexecuted": True,
        "new_or_disjoint_task_population_claimed": False,
        "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
    }
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    if (
        value.get("role") != "v24798_exact220_result"
        or value.get("protocol_id") != contract.PROTOCOL_ID
        or value.get("status") != "exact220_single_rollout_complete"
        or value.get("selected") != 220
        or value.get("failure_as_zero") is not True
        or value.get("exact220_prediction_freeze_before_evaluator") is not True
        or value.get("metrics") != expected_metrics
        or value.get("comparisons") != expected_comparisons
        or value.get("efficiency") != {
            "forward_wall_seconds": barrier["forward"]["forward_wall_seconds"],
            "evaluator_parallel_wall_seconds": merge["parallel_wall_seconds"],
            "evaluator_workers": 32,
        }
        or value.get("provenance") != expected_provenance
        or value.get("source_policy") != expected_source_policy
        or value.get("authorization") != RESULT_AUTHORIZATION
        or value.get("claims") != RESULT_CLAIMS
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.98 final result drifted")
    return artifacts


def build_postresult_audit(*, now: int | None = None) -> dict[str, Any]:
    protocol = validate_evaluator_protocol(_read(ROOT / EVALUATOR_PROTOCOL))
    result = _read(ROOT / FINAL_RESULT)
    artifacts = validate_final_result(result, protocol)
    barrier = _forward_barrier()
    checks = {
        "forward_barrier_exact220": barrier["forward"].get("terminal_predictions") == 220,
        "mapping_and_evaluator_closed_during_forward": barrier["freeze"].get(
            "mapping_gold_or_evaluator_opened_or_hashed"
        ) is False,
        "joined_official_merged_rows_exact220": artifacts["joined_rows"]
        == artifacts["official_rows"] == artifacts["merged_rows"] == 220,
        "unique_instance_ids_exact220": artifacts["unique_instance_ids"] == 220,
        "fixed_contiguous_worker_count_32": artifacts["workers"] == 32,
        "all_worker_returncodes_zero": artifacts["worker_returncodes_zero"] is True,
        "all220_conservative_denominator": artifacts["all220_conservative_denominator"] == 220,
        "test156_conservative_denominator": artifacts["test156_conservative_denominator"] == 156,
        "evaluator_errors_terminal_zero": artifacts["worker_errors_terminal_zero"]
        == result["metrics"]["all_220"]["evaluator_invalid_or_not_run"],
        "final_result_sealed": _sealed(result, "result_payload_sha256"),
        "result_forbids_sota_avg4_or_leaderboard": result.get("claims") == RESULT_CLAIMS,
        "no_selective_retry_or_revaluation": result.get("authorization") == RESULT_AUTHORIZATION,
        "forward_and_evaluator_processes_absent": not _active(
            (contract.RUNNER_MARKER, contract.CHILD_MARKER, "scripts/run_official_eval_local.py")
        ),
        "shared_api_lease_released": _lease_inactive(),
        "protected_watchers_unchanged": contract.protected_watcher_snapshot()
        == barrier["protocol"]["execution"]["protected_watchers"],
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v24798_exact220_postresult_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "provenance": {
            "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
            "forward_audit_sha256": contract.sha256(ROOT / FORWARD_AUDIT),
            "evaluator_protocol_sha256": contract.sha256(ROOT / EVALUATOR_PROTOCOL),
            "prepare_attestation_sha256": contract.sha256(ROOT / PREPARE_ATTESTATION),
            "merge_attestation_sha256": contract.sha256(ROOT / MERGE_ATTESTATION),
            "merged_results_sha256": contract.sha256(ROOT / MERGED_RESULTS),
            "conservative_summary_sha256": contract.sha256(ROOT / SUMMARY),
            "final_result_sha256": contract.sha256(ROOT / FINAL_RESULT),
        },
        "checks": checks,
        "forward": {
            "selected": 220,
            "terminal_predictions": barrier["forward"]["terminal_predictions"],
            "model_generated_tables": barrier["forward"]["model_generated_tables"],
            "fallback_tables": barrier["forward"]["fallback_tables"],
            "forward_wall_seconds": barrier["forward"]["forward_wall_seconds"],
        },
        "evaluation": {
            **artifacts,
            "evaluator_valid": result["metrics"]["all_220"]["evaluator_valid"],
            "parallel_wall_seconds": result["efficiency"]["evaluator_parallel_wall_seconds"],
        },
        "result": {
            "metrics": result["metrics"],
            "comparisons": result["comparisons"],
            "claims": result["claims"],
        },
        "source_policy": {
            **result["source_policy"],
            "audit_is_read_only_except_new_postresult_artifact": True,
            "credential_value_output_persisted_or_hashed_by_audit": False,
        },
        "authorization": dict(RESULT_AUTHORIZATION),
        "findings": findings,
        "audit_valid": not findings,
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_postresult_audit(value: dict[str, Any]) -> dict[str, Any]:
    if (
        value.get("role") != "v24798_exact220_postresult_audit"
        or value.get("protocol_id") != contract.PROTOCOL_ID
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or not all((value.get("checks") or {}).values())
        or value.get("provenance", {}).get("final_result_sha256")
        != contract.sha256(ROOT / FINAL_RESULT)
        or value.get("authorization") != RESULT_AUTHORIZATION
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.98 postresult audit drifted")
    return value


def evaluate() -> dict[str, Any]:
    protocol = validate_evaluator_protocol(_read(ROOT / EVALUATOR_PROTOCOL))
    barrier = _forward_barrier()
    if (ROOT / FINAL_RESULT).exists() or (ROOT / FINAL_RESULT).is_symlink() or (ROOT / EVALUATOR_ROOT).exists() or (ROOT / EVALUATOR_ROOT).is_symlink():
        raise RuntimeError("V2.47.98 evaluator surface is not pristine")
    configure_evaluator()
    live = evaluator.validate_live_evaluator_identity(ROOT, protocol)
    prepared = evaluator.prepare_evaluator_inputs(ROOT, protocol, barrier)
    with evaluator.acquire_deepwide_api_lease(ROOT, owner=EVALUATOR_OWNER, purpose=EVALUATOR_PURPOSE, path=ROOT / contract.LEASE_PATH):
        eval_rows, parallel = evaluator.run_parallel_evaluator(ROOT, protocol, prepared["official"])
    summary = summarize_rollout(prepared["joined"], eval_rows, rollout_id=1)
    evaluator._new_json(ROOT / SUMMARY, summary)
    metrics = {"test_156": _group_metrics(summary, "test_156"), "all_220": _group_metrics(summary, "all_220")}
    metrics["all_220"].update({
        "model_generated_tables": barrier["forward"]["model_generated_tables"],
        "fallback_tables": barrier["forward"]["fallback_tables"],
        "system_total_tokens": barrier["forward"]["system_total_tokens"],
    })
    result = {
        "artifact_version": 1, "role": "v24798_exact220_result",
        "protocol_id": contract.PROTOCOL_ID, "created_at_unix": int(time.time()),
        "status": "exact220_single_rollout_complete", "selected": 220,
        "failure_as_zero": True, "exact220_prediction_freeze_before_evaluator": True,
        "metrics": metrics,
        "efficiency": {"forward_wall_seconds": barrier["forward"]["forward_wall_seconds"], "evaluator_parallel_wall_seconds": parallel["attestation"]["parallel_wall_seconds"], "evaluator_workers": 32},
        "comparisons": {name: _comparison(metrics["all_220"], path) for name, path in REFERENCES.items()},
        "provenance": {
            "evaluator_protocol_sha256": contract.sha256(ROOT / EVALUATOR_PROTOCOL),
            "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
            "forward_audit_sha256": contract.sha256(ROOT / FORWARD_AUDIT),
            "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
            "mapping_sha256": contract.sha256(ROOT / MAPPING_PATH),
            "query_data_sha256": live["query_data_sha256"],
            "answer_corpus_manifest_sha256": live["answer_corpus_manifest_sha256"],
            "evaluator_source_manifest_sha256": live["evaluator_source_manifest_sha256"],
            "judge": live["judge"],
            "recovery_policy": live["recovery_policy"],
            "merged_official_eval_results_sha256": contract.sha256(ROOT / MERGED_RESULTS),
            "parallel_merge_attestation_sha256": contract.sha256(ROOT / MERGE_ATTESTATION),
            "conservative_summary_sha256": contract.sha256(ROOT / SUMMARY),
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_opened_only_after_exact220_prediction_freeze_and_pushed_audit": True,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
            "fixed_public_exact220_task_set_reexecuted": True,
            "new_or_disjoint_task_population_claimed": False,
            "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
        },
        "authorization": dict(RESULT_AUTHORIZATION),
        "claims": dict(RESULT_CLAIMS),
    }
    result["result_payload_sha256"] = contract.payload_sha256(result)
    validate_final_result(result, protocol)
    evaluator._new_json(ROOT / FINAL_RESULT, result)
    return result


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("audit", "protocol", "evaluate", "postaudit"))
    args = parser.parse_args()
    if args.command == "audit":
        value = build_forward_audit(); path = FORWARD_AUDIT; publish_new(ROOT / path, value)
        output = {"path": str(path), "audit_valid": value["audit_valid"], "findings": value["findings"]}
    elif args.command == "protocol":
        value = build_evaluator_protocol(); path = EVALUATOR_PROTOCOL; publish_new(ROOT / path, value)
        output = {"path": str(path), "authorization": value["authorization"]}
    elif args.command == "evaluate":
        value = evaluate()
        output = {"path": str(FINAL_RESULT), "status": value["status"], "metrics": value["metrics"]["all_220"]}
    else:
        value = build_postresult_audit()
        validate_postresult_audit(value)
        publish_new(ROOT / POSTAUDIT, value)
        output = {"path": str(POSTAUDIT), "audit_valid": value["audit_valid"], "findings": value["findings"]}
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
