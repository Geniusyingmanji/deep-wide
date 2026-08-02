#!/usr/bin/env python3
"""Post-freeze official evaluator and conservative exact-220 release."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.finalize_fullset_rollout import (  # noqa: E402
    _live_answer_corpus_manifest_sha256,
    _live_evaluator_source_manifest_sha256,
    prepare_rollout,
    read_jsonl,
    summarize_rollout,
    validate_evaluator_contract,
)
from scripts.preregister_v24266_exact220 import (  # noqa: E402
    EVALUATOR_ROOT,
    FINAL_RESULT,
    FORWARD_RESULT,
    OUTPUT,
    PREDICTION_FREEZE,
    RUN_SUMMARY,
    RUNTIME_PREDICTIONS,
    SELECTED_COUNT,
    SOURCE_MANIFEST,
    selected_ids,
    validate_protocol,
)
from scripts.run_official_eval_local import validate_committed_eval_rows  # noqa: E402
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    read_object,
    sha256,
)
from scripts.run_v24266_exact220 import (  # noqa: E402
    validate_forward_result,
    validate_prediction_freeze,
)


MAPPING_PATH = Path("outputs/runtime_manifest_v1_repro/evaluator_mapping.jsonl")
PREPARE_ATTESTATION = EVALUATOR_ROOT / "prepare_attestation.json"
JOINED_OUTCOMES = EVALUATOR_ROOT / "terminal_outcomes_evaluator_joined.jsonl"
OFFICIAL_PREDICTIONS = EVALUATOR_ROOT / "official_predictions.jsonl"
EVALUATOR_RUN = EVALUATOR_ROOT / "official_eval"
EVALUATOR_LOG = EVALUATOR_ROOT / "evaluate.log"
SUMMARY = EVALUATOR_ROOT / "conservative_summary.json"
FINAL_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "status",
        "selected",
        "conservative_denominator",
        "failure_as_zero",
        "exact220_prediction_freeze_before_evaluator",
        "metrics",
        "provenance",
        "source_policy",
        "authorization",
        "claims",
        "result_payload_sha256",
    }
)
METRIC_KEYS = frozenset(
    {
        "runtime_completed",
        "runtime_failed",
        "evaluator_valid",
        "evaluator_invalid_or_not_run",
        "whole_table_successes",
        "entity_acc",
        "f1_by_row",
        "f1_by_item",
        "column_f1",
        "quality_composite",
        "score",
        "model_generated_tables",
        "fallback_tables",
        "system_total_tokens",
    }
)
PROVENANCE_KEYS = frozenset(
    {
        "protocol_sha256",
        "forward_result_sha256",
        "prediction_freeze_sha256",
        "mapping_sha256",
        "query_data_sha256",
        "answer_corpus_manifest_sha256",
        "evaluator_source_manifest_sha256",
        "judge",
        "recovery_policy",
        "evaluator_run_contract_sha256",
        "official_eval_results_sha256",
        "conservative_summary_sha256",
    }
)


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _write_jsonl_new(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _new_json(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def validate_forward_barrier(root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    forward = read_object(root / FORWARD_RESULT)
    validate_forward_result(root, protocol, forward)
    freeze = read_object(root / PREDICTION_FREEZE)
    rows = validate_prediction_freeze(root, protocol, freeze)
    if (
        forward.get("shared_model_receipts", {}).get("all_acquisitions_match_actual_requests")
        is not True
    ):
        raise RuntimeError("V2.42.66 exact-220 model-slot receipts are incomplete")
    return {"forward": forward, "freeze": freeze, "runtime_rows": rows}


def validate_live_evaluator_identity(root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    evaluator = protocol["evaluator_contract"]
    query = evaluator.get("query_data") or {}
    answers = evaluator.get("answer_corpus") or {}
    source = evaluator.get("evaluator_source") or {}
    query_path = root / Path(str(query.get("path", "")))
    answer_root = root / Path(str(answers.get("root", "")))
    if (
        query_path.is_symlink()
        or not query_path.is_file()
        or sha256(query_path) != query.get("sha256")
        or answer_root.is_symlink()
        or not answer_root.is_dir()
        or _live_answer_corpus_manifest_sha256(answer_root) != answers.get("manifest_sha256")
        or _live_evaluator_source_manifest_sha256() != source.get("manifest_sha256")
    ):
        raise RuntimeError("V2.42.66 live evaluator identity drifted")
    return {
        "query_data_sha256": query["sha256"],
        "answer_corpus_manifest_sha256": answers["manifest_sha256"],
        "evaluator_source_manifest_sha256": source["manifest_sha256"],
        "judge": dict(evaluator["judge"]),
        "recovery_policy": dict(evaluator["recovery_policy"]),
    }


def _expected_prepare(
    root: Path, protocol: dict[str, Any], barrier: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    mapping = root / MAPPING_PATH
    manifest = root / SOURCE_MANIFEST
    evaluator = protocol["evaluator_contract"]
    if (
        mapping.is_symlink()
        or not mapping.is_file()
        or sha256(mapping) != evaluator["mapping"]["sha256"]
        or manifest.is_symlink()
        or not manifest.is_file()
        or sha256(manifest) != protocol["task_contract"]["manifest"]["sha256"]
    ):
        raise RuntimeError("V2.42.66 evaluator join identity drifted")
    joined, official, base = prepare_rollout(
        manifest_rows=read_jsonl(manifest),
        mapping_rows=read_jsonl(mapping),
        shards=[
            (
                "all220",
                selected_ids(root),
                barrier["runtime_rows"],
                read_object(root / RUN_SUMMARY),
            )
        ],
        rollout_id=1,
    )
    if len(joined) != SELECTED_COUNT or len(official) != SELECTED_COUNT:
        raise RuntimeError("V2.42.66 evaluator prepare is not exact-220")
    attestation = {
        **base,
        "phase": "post_exact220_prediction_freeze_evaluator_prepare",
        "mapping_sha256": sha256(mapping),
        "manifest_sha256": sha256(manifest),
        "runtime_predictions_sha256": sha256(root / RUNTIME_PREDICTIONS),
        "prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
        "both_forward_and_freeze_exact220_before_mapping_open": True,
    }
    return joined, official, attestation


def prepare_evaluator_inputs(
    root: Path, protocol: dict[str, Any], barrier: dict[str, Any]
) -> dict[str, Any]:
    joined, official, attestation = _expected_prepare(root, protocol, barrier)
    (root / EVALUATOR_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
    _write_jsonl_new(root / JOINED_OUTCOMES, joined)
    _write_jsonl_new(root / OFFICIAL_PREDICTIONS, official)
    attestation.update(
        {
            "terminal_outcomes_sha256": sha256(root / JOINED_OUTCOMES),
            "official_predictions_sha256": sha256(root / OFFICIAL_PREDICTIONS),
        }
    )
    attestation["prepare_payload_sha256"] = payload_sha256(attestation)
    _new_json(root / PREPARE_ATTESTATION, attestation)
    return {"joined": joined, "official": official, "attestation": attestation}


def load_prepared_evaluator_inputs(
    root: Path, protocol: dict[str, Any], barrier: dict[str, Any]
) -> dict[str, Any]:
    joined, official, expected = _expected_prepare(root, protocol, barrier)
    if read_jsonl(root / JOINED_OUTCOMES) != joined or read_jsonl(root / OFFICIAL_PREDICTIONS) != official:
        raise RuntimeError("V2.42.66 recovery prepared rows drifted")
    expected.update(
        {
            "terminal_outcomes_sha256": sha256(root / JOINED_OUTCOMES),
            "official_predictions_sha256": sha256(root / OFFICIAL_PREDICTIONS),
        }
    )
    attestation = read_object(root / PREPARE_ATTESTATION)
    unsigned = dict(attestation)
    seal = unsigned.pop("prepare_payload_sha256", None)
    if unsigned != expected or seal != payload_sha256(unsigned):
        raise RuntimeError("V2.42.66 recovery prepare attestation drifted")
    return {"joined": joined, "official": official, "attestation": attestation}


def evaluator_command(
    root: Path, protocol: dict[str, Any], *, resume: bool = False
) -> list[str]:
    evaluator = protocol["evaluator_contract"]
    judge = evaluator["judge"]
    command = [
        str(root / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(root / "scripts/run_official_eval_local.py"),
        "--predictions",
        str(root / OFFICIAL_PREDICTIONS),
        "--out-dir",
        str(root / EVALUATOR_RUN),
        "--query-path",
        str(root / evaluator["query_data"]["path"]),
        "--answer-root",
        str(root / evaluator["answer_corpus"]["root"]),
        "--proxy-url",
        judge["proxy_url"],
        "--model",
        judge["model"],
        "--reasoning-effort",
        judge["reasoning_effort"],
        "--judge-max-output-tokens",
        str(judge["max_output_tokens"]),
        "--judge-timeout",
        str(judge["timeout_seconds"]),
        "--judge-max-retries",
        str(judge["max_retries"]),
    ]
    if resume:
        command.append("--resume")
    return command


def _run_logged(
    runner: Callable[..., subprocess.CompletedProcess[Any]],
    command: list[str],
    *,
    root: Path,
    log: Path,
) -> None:
    environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    environment.update(
        {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1"}
    )
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("ab") as handle:
        completed = runner(
            command,
            cwd=root,
            env=environment,
            stdout=handle,
            stderr=subprocess.STDOUT,
            check=False,
        )
        handle.flush()
        os.fsync(handle.fileno())
    if completed.returncode != 0:
        raise RuntimeError("V2.42.66 evaluator command failed")


def _metrics(summary: dict[str, Any]) -> dict[str, Any]:
    group = summary["groups"]["all_220"]
    conservative = group["conservative_all_selected"]
    return {
        "runtime_completed": group["runtime_completed"],
        "runtime_failed": group["runtime_failed"],
        "evaluator_valid": group["evaluator_valid"],
        "evaluator_invalid_or_not_run": group["evaluator_invalid_or_not_run"],
        "whole_table_successes": sum(
            row["evaluator_valid"] and row["metrics"]["score"] > 0
            for row in summary["per_task"]
        ),
        "entity_acc": float(conservative["entity_acc"]),
        "f1_by_row": float(conservative["f1_by_row"]),
        "f1_by_item": float(conservative["f1_by_item"]),
        "column_f1": float(conservative["column_f1"]),
        "quality_composite": sum(
            float(conservative[name])
            for name in ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
        )
        / 4,
        "score": float(conservative["score"]),
    }


def validate_final_result(
    root: Path, protocol: dict[str, Any], value: dict[str, Any]
) -> None:
    if (
        set(value) != FINAL_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24266_exact220_result"
        or value.get("protocol_id") != protocol["protocol_id"]
        or value.get("status") != "exact220_single_rollout_complete"
        or value.get("selected") != SELECTED_COUNT
        or value.get("conservative_denominator") != SELECTED_COUNT
        or value.get("failure_as_zero") is not True
        or value.get("exact220_prediction_freeze_before_evaluator") is not True
        or value.get("claims")
        != {
            "public_exact220_single_rollout": True,
            "cold_execution": True,
            "unseen_or_held_out": False,
            "avg_at_4": False,
            "leaderboard_submitted": False,
            "sota": False,
        }
        or not _sealed(value, "result_payload_sha256")
    ):
        raise RuntimeError("V2.42.66 final result identity drifted")
    validate_forward_barrier(root, protocol)
    metrics = value.get("metrics")
    if not isinstance(metrics, dict) or set(metrics) != METRIC_KEYS:
        raise RuntimeError("V2.42.66 final metric schema drifted")
    summary_metrics = _metrics(read_object(root / SUMMARY))
    forward = read_object(root / FORWARD_RESULT)
    summary_metrics.update(
        {
            "model_generated_tables": forward["model_generated_tables"],
            "fallback_tables": forward["fallback_tables"],
            "system_total_tokens": forward["system_total_tokens"],
        }
    )
    if metrics != summary_metrics:
        raise RuntimeError("V2.42.66 final metrics are not bound to the summary")
    provenance = value.get("provenance") or {}
    evaluator = protocol["evaluator_contract"]
    evaluator_provenance = validate_evaluator_contract(
        root / EVALUATOR_RUN / "run_config.json",
        expected_predictions_path=root / OFFICIAL_PREDICTIONS,
        expected_predictions_sha256=sha256(root / OFFICIAL_PREDICTIONS),
        expected_selected_count=SELECTED_COUNT,
    )
    if (
        not isinstance(provenance, dict)
        or set(provenance) != PROVENANCE_KEYS
        or provenance.get("protocol_sha256") != sha256(root / OUTPUT)
        or provenance.get("forward_result_sha256") != sha256(root / FORWARD_RESULT)
        or provenance.get("prediction_freeze_sha256") != sha256(root / PREDICTION_FREEZE)
        or provenance.get("mapping_sha256") != sha256(root / MAPPING_PATH)
        or provenance.get("query_data_sha256") != evaluator["query_data"]["sha256"]
        or provenance.get("answer_corpus_manifest_sha256")
        != evaluator["answer_corpus"]["manifest_sha256"]
        or provenance.get("evaluator_source_manifest_sha256")
        != evaluator["evaluator_source"]["manifest_sha256"]
        or provenance.get("judge") != evaluator["judge"]
        or provenance.get("recovery_policy") != evaluator["recovery_policy"]
        or provenance.get("evaluator_run_contract_sha256")
        != evaluator_provenance["run_contract_sha256"]
        or provenance.get("official_eval_results_sha256")
        != sha256(root / EVALUATOR_RUN / "official_eval_results.jsonl")
        or provenance.get("conservative_summary_sha256") != sha256(root / SUMMARY)
    ):
        raise RuntimeError("V2.42.66 final evaluator identity drifted")
    if value.get("source_policy") != {
        "runtime_boundary": ["opaque_id", "question"],
        "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False,
        "mapping_opened_only_after_exact220_prediction_freeze": True,
        "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
    }:
        raise RuntimeError("V2.42.66 final source policy drifted")
    if value.get("authorization") != {
        "additional_rollout_or_avg4": False,
        "leaderboard_submission": False,
        "sota_claim": False,
    }:
        raise RuntimeError("V2.42.66 final authorization drifted")


def finalize(
    root: Path = ROOT,
    *,
    command_runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
    resume_evaluator: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root, OUTPUT)
    if (root / FINAL_RESULT).exists() or (root / FINAL_RESULT).is_symlink():
        raise FileExistsError(root / FINAL_RESULT)
    barrier = validate_forward_barrier(root, protocol)
    live = validate_live_evaluator_identity(root, protocol)
    evaluator_exists = (root / EVALUATOR_ROOT).exists() or (root / EVALUATOR_ROOT).is_symlink()
    if evaluator_exists and not resume_evaluator:
        raise RuntimeError("V2.42.66 evaluator surface exists; explicit recovery required")
    if not evaluator_exists and resume_evaluator:
        raise RuntimeError("V2.42.66 evaluator recovery surface is absent")
    prepared = (
        load_prepared_evaluator_inputs(root, protocol, barrier)
        if resume_evaluator
        else prepare_evaluator_inputs(root, protocol, barrier)
    )
    lease = protocol["lease_contract"]
    with acquire_deepwide_api_lease(
        root,
        owner=lease["evaluator_owner"],
        purpose=lease["evaluator_purpose"],
        path=root / lease["path"],
    ):
        _run_logged(
            command_runner,
            evaluator_command(root, protocol, resume=resume_evaluator and (root / EVALUATOR_RUN).exists()),
            root=root,
            log=root / EVALUATOR_LOG,
        )
    eval_rows = read_jsonl(root / EVALUATOR_RUN / "official_eval_results.jsonl")
    expected_ids = [row["instance_id"] for row in prepared["official"]]
    validate_committed_eval_rows(eval_rows, expected_ids)
    if len(eval_rows) != SELECTED_COUNT:
        raise RuntimeError("V2.42.66 evaluator is not exact-220 terminal")
    evaluator_provenance = validate_evaluator_contract(
        root / EVALUATOR_RUN / "run_config.json",
        expected_predictions_path=root / OFFICIAL_PREDICTIONS,
        expected_predictions_sha256=sha256(root / OFFICIAL_PREDICTIONS),
        expected_selected_count=SELECTED_COUNT,
    )
    for key in (
        "query_data_sha256",
        "answer_corpus_manifest_sha256",
        "evaluator_source_manifest_sha256",
        "judge",
        "recovery_policy",
    ):
        if evaluator_provenance.get(key) != live.get(key):
            raise RuntimeError(f"V2.42.66 evaluator {key} drifted")
    summary = summarize_rollout(prepared["joined"], eval_rows, rollout_id=1)
    _new_json(root / SUMMARY, summary)
    metrics = _metrics(summary)
    metrics["model_generated_tables"] = barrier["forward"]["model_generated_tables"]
    metrics["fallback_tables"] = barrier["forward"]["fallback_tables"]
    metrics["system_total_tokens"] = barrier["forward"]["system_total_tokens"]
    result = {
        "artifact_version": 1,
        "role": "v24266_exact220_result",
        "protocol_id": protocol["protocol_id"],
        "created_at_unix": int(time.time()),
        "status": "exact220_single_rollout_complete",
        "selected": SELECTED_COUNT,
        "conservative_denominator": SELECTED_COUNT,
        "failure_as_zero": True,
        "exact220_prediction_freeze_before_evaluator": True,
        "metrics": metrics,
        "provenance": {
            "protocol_sha256": sha256(root / OUTPUT),
            "forward_result_sha256": sha256(root / FORWARD_RESULT),
            "prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
            "mapping_sha256": sha256(root / MAPPING_PATH),
            "query_data_sha256": live["query_data_sha256"],
            "answer_corpus_manifest_sha256": live["answer_corpus_manifest_sha256"],
            "evaluator_source_manifest_sha256": live["evaluator_source_manifest_sha256"],
            "judge": live["judge"],
            "recovery_policy": live["recovery_policy"],
            "evaluator_run_contract_sha256": evaluator_provenance["run_contract_sha256"],
            "official_eval_results_sha256": sha256(root / EVALUATOR_RUN / "official_eval_results.jsonl"),
            "conservative_summary_sha256": sha256(root / SUMMARY),
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "mapping_opened_only_after_exact220_prediction_freeze": True,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        },
        "authorization": {
            "additional_rollout_or_avg4": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
        "claims": {
            "public_exact220_single_rollout": True,
            "cold_execution": True,
            "unseen_or_held_out": False,
            "avg_at_4": False,
            "leaderboard_submitted": False,
            "sota": False,
        },
    }
    result["result_payload_sha256"] = payload_sha256(result)
    validate_final_result(root, protocol, result)
    _new_json(root / FINAL_RESULT, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--resume-evaluator", action="store_true")
    args = parser.parse_args()
    value = finalize(Path(args.root), resume_evaluator=args.resume_evaluator)
    print(json.dumps({"result": str(FINAL_RESULT), "status": value["status"]}, sort_keys=True))
