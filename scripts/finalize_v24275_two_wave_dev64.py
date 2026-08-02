#!/usr/bin/env python3
"""Post-freeze full64 evaluation for the V2.42.75 two-wave candidate.

The first operation is validation of the minimal forward-only exact64 barrier.
Only after that succeeds may this process import the full experiment protocol,
open the historical V2.42.71 control predictions, or read mapping/gold/evaluator
resources.  Both arms are then evaluated from fresh rows with one current judge.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24275_forward_contract import (  # noqa: E402
    FORWARD_PROTOCOL,
    FORWARD_RESULT,
    PREDICTION_FREEZE,
    RUNTIME_PREDICTIONS,
    RUN_SUMMARY,
    SELECTED_COUNT,
    SOURCE_MANIFEST,
    payload_sha256,
    read_object,
    sha256,
    validate_protocol as validate_forward_protocol,
)
from scripts import run_v24275_two_wave_dev64 as candidate_runner  # noqa: E402


FULL_PROTOCOL = Path("results/v24275_two_wave_dev64_preregistration_v2_20260802.json")
FINAL_RESULT = Path("results/v24275_two_wave_dev64_result_v2_20260802.json")
OUTPUT_ROOT = Path("outputs/v24275_two_wave_dev64_v2_20260802")
EVALUATOR_ROOT = OUTPUT_ROOT / "evaluator"
MAPPING_PATH = Path("outputs/runtime_manifest_v1_repro/evaluator_mapping.jsonl")
QUALITY = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
ARMS = ("control", "candidate")
ARM_ROOTS = {arm: EVALUATOR_ROOT / arm for arm in ARMS}
JOINED = {
    arm: ARM_ROOTS[arm] / "terminal_outcomes_evaluator_joined.jsonl"
    for arm in ARMS
}
OFFICIAL = {arm: ARM_ROOTS[arm] / "official_predictions.jsonl" for arm in ARMS}
PREPARE = {arm: ARM_ROOTS[arm] / "prepare_attestation.json" for arm in ARMS}
EVAL_RUN = {arm: ARM_ROOTS[arm] / "official_eval" for arm in ARMS}
EVAL_LOG = {arm: ARM_ROOTS[arm] / "evaluate.log" for arm in ARMS}
SUMMARY = {arm: ARM_ROOTS[arm] / "conservative_summary.json" for arm in ARMS}

ARM_METRIC_KEYS = frozenset(
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
        "search_total_tokens",
        "task_wall_sum_seconds",
    }
)
HEALTH_KEYS = frozenset(
    {
        "retrieval_completed",
        "retrieval_failed",
        "unrecoverable_search_failures",
        "cache_misses",
        "cache_serve_network_fetches",
        "hard_fetch_deadline_failures",
        "fetch_helper_failures",
    }
)
FINAL_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "status",
        "selected_per_arm",
        "conservative_denominator_per_arm",
        "failure_as_zero",
        "candidate_exact64_before_control_or_evaluator_open",
        "both_arms_fully_evaluated_with_same_current_judge",
        "control",
        "candidate",
        "candidate_retrieval_health",
        "decision",
        "provenance",
        "source_policy",
        "authorization",
        "claims",
        "result_payload_sha256",
    }
)


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _write_jsonl_new(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _new_json(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def validate_candidate_barrier(root: Path) -> dict[str, Any]:
    """Validate candidate exact64 without importing the full/control side."""

    protocol = validate_forward_protocol(root, FORWARD_PROTOCOL)
    forward = read_object(root / FORWARD_RESULT)
    candidate_runner.validate_forward_result(root, protocol, forward)
    freeze = read_object(root / PREDICTION_FREEZE)
    rows = candidate_runner.validate_prediction_freeze(root, protocol, freeze)
    summary = read_object(root / RUN_SUMMARY)
    candidate_runner.validate_summary(summary)
    receipts = forward.get("shared_model_receipts") or {}
    if (
        len(rows) != SELECTED_COUNT
        or receipts.get("all_acquisitions_match_actual_requests") is not True
        or forward.get("candidate_exact64_before_control_or_evaluator_open")
        is not True
        or freeze.get(
            "exact_terminal_before_control_prediction_mapping_gold_or_evaluator_open"
        )
        is not True
        or freeze.get("control_prediction_mapping_gold_or_evaluator_opened_or_hashed")
        is not False
    ):
        raise RuntimeError("V2.42.75 candidate freeze barrier is incomplete")
    return {
        "forward_protocol": protocol,
        "forward": forward,
        "freeze": freeze,
        "rows": rows,
        "summary": summary,
    }


def load_full_protocol_after_candidate(
    root: Path, candidate: Mapping[str, Any]
) -> tuple[Any, dict[str, Any]]:
    if len(candidate.get("rows") or []) != SELECTED_COUNT:
        raise RuntimeError("V2.42.75 candidate barrier was not supplied")
    from scripts import preregister_v24275_two_wave_dev64 as prereg

    protocol = prereg.validate_protocol(root, prereg.OUTPUT)
    forward = candidate["forward_protocol"]
    expected = protocol.get("forward_runtime_contract") or {}
    if (
        expected.get("path") != str(FORWARD_PROTOCOL)
        or expected.get("payload_sha256")
        != forward.get("forward_contract_payload_sha256")
        or expected.get("contains_control_mapping_gold_evaluator_or_score_path")
        is not False
        or protocol.get("protocol_id") != forward.get("protocol_id")
        or protocol.get("task_contract", {}).get("selected_opaque_ids_sha256")
        != forward.get("task_contract", {}).get("selected_opaque_ids_sha256")
    ):
        raise RuntimeError("V2.42.75 full/forward protocol binding drifted")
    return prereg, protocol


def load_frozen_control_after_candidate(
    root: Path,
    prereg: Any,
    protocol: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    """First operation permitted to open historical per-task predictions."""

    if len(candidate.get("rows") or []) != SELECTED_COUNT:
        raise RuntimeError("V2.42.75 candidate barrier was not supplied")
    from scripts.validate_v24271_forward_erratum import (
        validate_committed_erratum,
        validate_forward_barrier,
    )

    validate_committed_erratum(root)
    barrier = validate_forward_barrier(root)
    result = read_object(root / prereg.CONTROL_RESULT)
    audit = read_object(root / prereg.CONTROL_POSTAUDIT)
    freeze_path = root / prereg.CONTROL_PREDICTION_FREEZE
    runtime_path = root / prereg.CONTROL_RUNTIME
    summary_path = root / prereg.CONTROL_RUN_SUMMARY
    provenance = result.get("provenance") or {}
    ids = list(protocol["task_contract"]["selected_opaque_ids"])
    rows = barrier["rows"]
    if (
        result.get("role") != "v24271_keyless_dev64_result"
        or not _sealed(result, "result_payload_sha256")
        or audit.get("role")
        != "v24271_keyless_dev64_postresult_erratum_audit"
        or audit.get("audit_valid") is not True
        or not _sealed(audit, "audit_payload_sha256")
        or audit.get("final_result_sha256") != sha256(root / prereg.CONTROL_RESULT)
        or provenance.get("candidate_prediction_freeze_sha256")
        != sha256(freeze_path)
        or provenance.get("forward_result_sha256")
        != sha256(root / "results/v24271_keyless_dev64_forward_result_v1_20260802.json")
        or len(rows) != SELECTED_COUNT
        or [row["opaque_id"] for row in rows] != ids
        or [row["opaque_id"] for row in candidate["rows"]] != ids
        or barrier["summary"].get("selected") != SELECTED_COUNT
        or sha256(runtime_path)
        != barrier["freeze"].get("runtime_predictions_sha256")
        or sha256(summary_path) != barrier["freeze"].get("run_summary_sha256")
    ):
        raise RuntimeError("V2.42.75 frozen control provenance drifted")
    return {
        "rows": rows,
        "summary": barrier["summary"],
        "freeze": barrier["freeze"],
        "ids": ids,
        "source_hashes": {
            "runtime_sha256": sha256(runtime_path),
            "summary_sha256": sha256(summary_path),
            "prediction_freeze_sha256": sha256(freeze_path),
        },
    }


def validate_live_evaluator_identity(
    root: Path, protocol: Mapping[str, Any]
) -> dict[str, Any]:
    from scripts.finalize_fullset_rollout import (
        _live_answer_corpus_manifest_sha256,
        _live_evaluator_source_manifest_sha256,
    )

    evaluator = protocol["evaluator_contract"]
    query = evaluator["query_data"]
    answers = evaluator["answer_corpus"]
    source = evaluator["evaluator_source"]
    query_path = root / query["path"]
    answer_root = root / answers["root"]
    mapping = root / MAPPING_PATH
    manifest = root / SOURCE_MANIFEST
    if (
        query_path.is_symlink()
        or not query_path.is_file()
        or sha256(query_path) != query["sha256"]
        or answer_root.is_symlink()
        or not answer_root.is_dir()
        or _live_answer_corpus_manifest_sha256(answer_root)
        != answers["manifest_sha256"]
        or _live_evaluator_source_manifest_sha256() != source["manifest_sha256"]
        or mapping.is_symlink()
        or not mapping.is_file()
        or sha256(mapping) != evaluator["mapping"]["sha256"]
        or manifest.is_symlink()
        or not manifest.is_file()
        or sha256(manifest) != protocol["task_contract"]["manifest"]["sha256"]
    ):
        raise RuntimeError("V2.42.75 live evaluator identity drifted")
    return {
        "mapping_sha256": sha256(mapping),
        "query_data_sha256": query["sha256"],
        "answer_corpus_manifest_sha256": answers["manifest_sha256"],
        "evaluator_source_manifest_sha256": source["manifest_sha256"],
        "judge": dict(evaluator["judge"]),
        "recovery_policy": dict(evaluator["recovery_policy"]),
    }


def _expected_prepare(
    root: Path,
    protocol: Mapping[str, Any],
    arm: str,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    ids: list[str],
    source_hashes: Mapping[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    from scripts.finalize_fullset_rollout import prepare_rollout, read_jsonl

    joined, official, base = prepare_rollout(
        manifest_rows=read_jsonl(root / SOURCE_MANIFEST),
        mapping_rows=read_jsonl(root / MAPPING_PATH),
        shards=[("devval", ids, rows, summary)],
        rollout_id=1,
    )
    if len(joined) != SELECTED_COUNT or len(official) != SELECTED_COUNT:
        raise RuntimeError(f"V2.42.75 {arm} evaluator prepare is not full64")
    attestation = {
        **base,
        "phase": "post_candidate_exact64_freeze_fresh_full_arm_evaluator_prepare",
        "arm": arm,
        "protocol_sha256": sha256(root / FULL_PROTOCOL),
        "candidate_prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
        "candidate_exact64_before_control_mapping_gold_or_evaluator_open": True,
        "selective_changed_prediction_evaluation": False,
        "old_evaluator_rows_reused": False,
        "mapping_sha256": sha256(root / MAPPING_PATH),
        "manifest_sha256": sha256(root / SOURCE_MANIFEST),
        "source_hashes": dict(source_hashes),
    }
    return joined, official, attestation


def prepare_arm(
    root: Path,
    protocol: Mapping[str, Any],
    arm: str,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    ids: list[str],
    source_hashes: Mapping[str, str],
) -> dict[str, Any]:
    joined, official, attestation = _expected_prepare(
        root, protocol, arm, rows, summary, ids, source_hashes
    )
    (root / ARM_ROOTS[arm]).mkdir(mode=0o700, parents=True, exist_ok=False)
    _write_jsonl_new(root / JOINED[arm], joined)
    _write_jsonl_new(root / OFFICIAL[arm], official)
    attestation.update(
        {
            "terminal_outcomes_sha256": sha256(root / JOINED[arm]),
            "official_predictions_sha256": sha256(root / OFFICIAL[arm]),
        }
    )
    attestation["prepare_payload_sha256"] = payload_sha256(attestation)
    _new_json(root / PREPARE[arm], attestation)
    return {"joined": joined, "official": official, "attestation": attestation}


def load_prepared_arm(
    root: Path,
    protocol: Mapping[str, Any],
    arm: str,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    ids: list[str],
    source_hashes: Mapping[str, str],
) -> dict[str, Any]:
    from scripts.finalize_fullset_rollout import read_jsonl

    joined, official, expected = _expected_prepare(
        root, protocol, arm, rows, summary, ids, source_hashes
    )
    if (
        read_jsonl(root / JOINED[arm]) != joined
        or read_jsonl(root / OFFICIAL[arm]) != official
    ):
        raise RuntimeError(f"V2.42.75 {arm} prepared evaluator rows drifted")
    expected.update(
        {
            "terminal_outcomes_sha256": sha256(root / JOINED[arm]),
            "official_predictions_sha256": sha256(root / OFFICIAL[arm]),
        }
    )
    attestation = read_object(root / PREPARE[arm])
    unsigned = dict(attestation)
    seal = unsigned.pop("prepare_payload_sha256", None)
    if unsigned != expected or seal != payload_sha256(unsigned):
        raise RuntimeError(f"V2.42.75 {arm} prepare attestation drifted")
    return {"joined": joined, "official": official, "attestation": attestation}


def evaluator_command(
    root: Path, protocol: Mapping[str, Any], arm: str, *, resume: bool
) -> list[str]:
    judge = protocol["evaluator_contract"]["judge"]
    evaluator = protocol["evaluator_contract"]
    command = [
        str(root / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(root / "scripts/run_official_eval_local.py"),
        "--predictions",
        str(root / OFFICIAL[arm]),
        "--out-dir",
        str(root / EVAL_RUN[arm]),
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
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        }
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
        raise RuntimeError("V2.42.75 evaluator command failed")


def _evaluate_both(
    root: Path,
    protocol: Mapping[str, Any],
    command_runner: Callable[..., subprocess.CompletedProcess[Any]],
    *,
    resume: bool,
) -> None:
    from scripts.deepwide_api_lease import acquire_deepwide_api_lease

    lease = protocol["lease_contract"]
    with acquire_deepwide_api_lease(
        root,
        owner=lease["evaluator_owner"],
        purpose=lease["evaluator_purpose"],
        path=root / lease["path"],
    ):
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="v24275-evaluator"
        ) as executor:
            futures = [
                executor.submit(
                    _run_logged,
                    command_runner,
                    evaluator_command(
                        root,
                        protocol,
                        arm,
                        resume=resume and (root / EVAL_RUN[arm]).exists(),
                    ),
                    root=root,
                    log=root / EVAL_LOG[arm],
                )
                for arm in ARMS
            ]
            for future in concurrent.futures.as_completed(futures):
                future.result()


def _arm_metrics(
    summary: Mapping[str, Any],
    *,
    model_generated: int,
    search_tokens: int,
    wall_seconds: float,
) -> dict[str, Any]:
    group = summary["groups"]["dev_validation_64"]
    conservative = group["conservative_all_selected"]
    value = {
        "runtime_completed": int(group["runtime_completed"]),
        "runtime_failed": int(group["runtime_failed"]),
        "evaluator_valid": int(group["evaluator_valid"]),
        "evaluator_invalid_or_not_run": int(group["evaluator_invalid_or_not_run"]),
        "whole_table_successes": sum(
            row["evaluator_valid"] and float(row["metrics"]["score"]) > 0
            for row in summary["per_task"]
        ),
        **{name: float(conservative[name]) for name in QUALITY},
        "quality_composite": sum(float(conservative[name]) for name in QUALITY)
        / len(QUALITY),
        "score": float(conservative["score"]),
        "model_generated_tables": int(model_generated),
        "fallback_tables": SELECTED_COUNT - int(model_generated),
        "search_total_tokens": int(search_tokens),
        "task_wall_sum_seconds": round(float(wall_seconds), 6),
    }
    validate_arm_metrics(value)
    return value


def validate_arm_metrics(value: Mapping[str, Any]) -> None:
    if set(value) != ARM_METRIC_KEYS:
        raise RuntimeError("V2.42.75 arm metric schema drifted")
    counts = ARM_METRIC_KEYS - set(QUALITY) - {
        "quality_composite",
        "score",
        "task_wall_sum_seconds",
    }
    if any(
        isinstance(value[name], bool)
        or not isinstance(value[name], int)
        or value[name] < 0
        for name in counts
    ):
        raise RuntimeError("V2.42.75 arm count metric drifted")
    if (
        value["runtime_completed"] + value["runtime_failed"] != SELECTED_COUNT
        or value["evaluator_valid"] + value["evaluator_invalid_or_not_run"]
        != SELECTED_COUNT
        or value["model_generated_tables"] + value["fallback_tables"]
        != SELECTED_COUNT
    ):
        raise RuntimeError("V2.42.75 arm denominator drifted")
    for name in (*QUALITY, "quality_composite", "score"):
        number = value[name]
        if (
            isinstance(number, bool)
            or not isinstance(number, (int, float))
            or not math.isfinite(float(number))
            or not 0 <= float(number) <= 1
        ):
            raise RuntimeError("V2.42.75 arm quality metric drifted")
    wall = value["task_wall_sum_seconds"]
    if (
        isinstance(wall, bool)
        or not isinstance(wall, (int, float))
        or not math.isfinite(float(wall))
        or wall < 0
    ):
        raise RuntimeError("V2.42.75 arm wall metric drifted")


def candidate_health(summary: Mapping[str, Any]) -> dict[str, int]:
    telemetry = summary["telemetry_totals"]
    value = {
        "retrieval_completed": int(telemetry["retrieval_completed"]),
        "retrieval_failed": int(telemetry["retrieval_failed"]),
        "unrecoverable_search_failures": int(
            telemetry["raw_unrecoverable_failure_count"]
        ),
        "cache_misses": int(telemetry["cache_miss_count"]),
        "cache_serve_network_fetches": int(
            telemetry["cache_serve_network_fetches"]
        ),
        "hard_fetch_deadline_failures": int(
            telemetry["hard_fetch_deadline_failures"]
        ),
        "fetch_helper_failures": int(telemetry["fetch_helper_failures"]),
    }
    if (
        set(value) != HEALTH_KEYS
        or any(isinstance(number, bool) or number < 0 for number in value.values())
        or value["retrieval_completed"] + value["retrieval_failed"]
        != SELECTED_COUNT
    ):
        raise RuntimeError("V2.42.75 candidate retrieval health drifted")
    return value


def decision(
    protocol: Mapping[str, Any],
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    health: Mapping[str, int],
) -> dict[str, Any]:
    gate = protocol["decision_contract"]
    search_ratio = candidate["search_total_tokens"] / max(
        1, control["search_total_tokens"]
    )
    wall_ratio = candidate["task_wall_sum_seconds"] / max(
        1e-9, control["task_wall_sum_seconds"]
    )
    deltas = {
        name: candidate[name] - control[name]
        for name in (
            "quality_composite",
            "entity_acc",
            "f1_by_row",
            "f1_by_item",
            "column_f1",
            "whole_table_successes",
            "model_generated_tables",
        )
    }
    checks = {
        "search_token_ratio": search_ratio <= gate["maximum_search_token_ratio"],
        "task_wall_sum_ratio": wall_ratio <= gate["maximum_task_wall_sum_ratio"],
        "quality_composite_delta": deltas["quality_composite"]
        >= gate["minimum_quality_composite_delta"],
        "entity_acc_delta": deltas["entity_acc"]
        >= gate["minimum_entity_acc_delta"],
        "f1_by_row_delta": deltas["f1_by_row"]
        >= gate["minimum_f1_by_row_delta"],
        "f1_by_item_delta": deltas["f1_by_item"]
        >= gate["minimum_f1_by_item_delta"],
        "column_f1_delta": deltas["column_f1"]
        >= gate["minimum_column_f1_delta"],
        "whole_table_success_delta": deltas["whole_table_successes"]
        >= gate["minimum_whole_table_success_delta"],
        "model_generated_table_delta": deltas["model_generated_tables"]
        >= gate["minimum_model_generated_table_delta"],
        "candidate_retrieval_failures": health["retrieval_failed"]
        <= gate["candidate_retrieval_failures_maximum"],
        "candidate_unrecoverable_search_failures": health[
            "unrecoverable_search_failures"
        ]
        <= gate["candidate_unrecoverable_search_failures_maximum"],
        "candidate_cache_misses": health["cache_misses"]
        <= gate["candidate_cache_misses_maximum"],
        "candidate_cache_serve_network_fetches": health[
            "cache_serve_network_fetches"
        ]
        <= gate["candidate_cache_serve_network_fetches_maximum"],
        "candidate_hard_fetch_deadline_failures": health[
            "hard_fetch_deadline_failures"
        ]
        <= gate["candidate_hard_fetch_deadline_failures_maximum"],
        "candidate_fetch_helper_failures": health["fetch_helper_failures"]
        <= gate["candidate_fetch_helper_failures_maximum"],
    }
    passed = all(checks.values())
    return {
        "status": "go" if passed else "no_go",
        "passed": passed,
        "checks": checks,
        "candidate_minus_control": deltas,
        "search_token_ratio": search_ratio,
        "task_wall_sum_ratio": wall_ratio,
        "gate": dict(gate),
        "go_scope": "exact220_design_only_not_launch",
    }


def validate_final_result(
    root: Path, protocol: Mapping[str, Any], value: Mapping[str, Any]
) -> None:
    if (
        set(value) != FINAL_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24275_two_wave_dev64_result"
        or value.get("protocol_id") != protocol["protocol_id"]
        or value.get("status")
        not in {"development_gate_go", "development_gate_no_go"}
        or value.get("selected_per_arm") != SELECTED_COUNT
        or value.get("conservative_denominator_per_arm") != SELECTED_COUNT
        or value.get("failure_as_zero") is not True
        or value.get("candidate_exact64_before_control_or_evaluator_open")
        is not True
        or value.get("both_arms_fully_evaluated_with_same_current_judge")
        is not True
        or not _sealed(value, "result_payload_sha256")
    ):
        raise RuntimeError("V2.42.75 final result identity drifted")
    for arm in ARMS:
        validate_arm_metrics(value[arm])
    health = value.get("candidate_retrieval_health")
    if not isinstance(health, Mapping) or set(health) != HEALTH_KEYS:
        raise RuntimeError("V2.42.75 final retrieval health drifted")
    expected = decision(protocol, value["control"], value["candidate"], health)
    if value.get("decision") != expected:
        raise RuntimeError("V2.42.75 final decision drifted")
    from scripts.finalize_fullset_rollout import validate_evaluator_contract

    provenance = value.get("provenance") or {}
    for arm in ARMS:
        contract = validate_evaluator_contract(
            root / EVAL_RUN[arm] / "run_config.json",
            expected_predictions_path=root / OFFICIAL[arm],
            expected_predictions_sha256=sha256(root / OFFICIAL[arm]),
            expected_selected_count=SELECTED_COUNT,
        )
        if (
            provenance.get(f"{arm}_evaluator_contract_sha256")
            != contract["run_contract_sha256"]
            or provenance.get(f"{arm}_eval_results_sha256")
            != sha256(root / EVAL_RUN[arm] / "official_eval_results.jsonl")
            or provenance.get(f"{arm}_conservative_summary_sha256")
            != sha256(root / SUMMARY[arm])
        ):
            raise RuntimeError(f"V2.42.75 {arm} evaluator provenance drifted")
    claims = {
        "development_gate_only": True,
        "independent_candidate_rollout_vs_frozen_control": True,
        "strict_shared_random_prefix_causal_ablation": False,
        "public_full220_result": False,
        "avg_at_4": False,
        "leaderboard_submitted": False,
        "sota": False,
    }
    if value.get("claims") != claims:
        raise RuntimeError("V2.42.75 final claims drifted")


def finalize(
    root: Path = ROOT,
    *,
    command_runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
    resume_evaluator: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    if (root / FINAL_RESULT).exists() or (root / FINAL_RESULT).is_symlink():
        raise FileExistsError(root / FINAL_RESULT)

    candidate = validate_candidate_barrier(root)
    prereg, protocol = load_full_protocol_after_candidate(root, candidate)
    control = load_frozen_control_after_candidate(
        root, prereg, protocol, candidate
    )
    live = validate_live_evaluator_identity(root, protocol)

    evaluator_exists = (root / EVALUATOR_ROOT).exists() or (
        root / EVALUATOR_ROOT
    ).is_symlink()
    if evaluator_exists != resume_evaluator:
        reason = (
            "exists; explicit recovery required"
            if evaluator_exists
            else "recovery surface is absent"
        )
        raise RuntimeError(f"V2.42.75 evaluator {reason}")

    candidate_sources = {
        "runtime_sha256": sha256(root / RUNTIME_PREDICTIONS),
        "summary_sha256": sha256(root / RUN_SUMMARY),
        "prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
    }
    arms = {
        "control": (
            control["rows"],
            control["summary"],
            control["source_hashes"],
        ),
        "candidate": (
            candidate["rows"],
            candidate["summary"],
            candidate_sources,
        ),
    }
    prepared: dict[str, dict[str, Any]] = {}
    for arm, (rows, summary, source_hashes) in arms.items():
        prepared[arm] = (
            load_prepared_arm(
                root,
                protocol,
                arm,
                rows,
                summary,
                control["ids"],
                source_hashes,
            )
            if resume_evaluator
            else prepare_arm(
                root,
                protocol,
                arm,
                rows,
                summary,
                control["ids"],
                source_hashes,
            )
        )

    _evaluate_both(root, protocol, command_runner, resume=resume_evaluator)
    from scripts.finalize_fullset_rollout import (
        read_jsonl,
        summarize_rollout,
        validate_evaluator_contract,
    )
    from scripts.run_official_eval_local import validate_committed_eval_rows

    arm_summaries: dict[str, dict[str, Any]] = {}
    evaluator_contracts: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        eval_rows = read_jsonl(
            root / EVAL_RUN[arm] / "official_eval_results.jsonl"
        )
        expected_ids = [row["instance_id"] for row in prepared[arm]["official"]]
        validate_committed_eval_rows(eval_rows, expected_ids)
        if len(eval_rows) != SELECTED_COUNT:
            raise RuntimeError(f"V2.42.75 {arm} evaluator is not full64 terminal")
        evaluator_contracts[arm] = validate_evaluator_contract(
            root / EVAL_RUN[arm] / "run_config.json",
            expected_predictions_path=root / OFFICIAL[arm],
            expected_predictions_sha256=sha256(root / OFFICIAL[arm]),
            expected_selected_count=SELECTED_COUNT,
        )
        for key in (
            "query_data_sha256",
            "answer_corpus_manifest_sha256",
            "evaluator_source_manifest_sha256",
            "judge",
            "recovery_policy",
        ):
            if evaluator_contracts[arm].get(key) != live.get(key):
                raise RuntimeError(f"V2.42.75 {arm} evaluator {key} drifted")
        arm_summaries[arm] = summarize_rollout(
            prepared[arm]["joined"], eval_rows, rollout_id=1
        )
        _new_json(root / SUMMARY[arm], arm_summaries[arm])

    control_summary = control["summary"]
    candidate_summary = candidate["summary"]
    control_metrics = _arm_metrics(
        arm_summaries["control"],
        model_generated=control_summary["model_generated_tables"],
        search_tokens=control_summary["cost_totals"]["search_total_tokens"],
        wall_seconds=control_summary["wall_seconds_sum"],
    )
    candidate_metrics = _arm_metrics(
        arm_summaries["candidate"],
        model_generated=candidate_summary["model_generated_tables"],
        search_tokens=candidate_summary["cost_totals"]["search_total_tokens"],
        wall_seconds=candidate_summary["wall_seconds_sum"],
    )
    health = candidate_health(candidate_summary)
    gate = decision(protocol, control_metrics, candidate_metrics, health)
    result = {
        "artifact_version": 1,
        "role": "v24275_two_wave_dev64_result",
        "protocol_id": protocol["protocol_id"],
        "created_at_unix": int(time.time()),
        "status": (
            "development_gate_go"
            if gate["passed"]
            else "development_gate_no_go"
        ),
        "selected_per_arm": SELECTED_COUNT,
        "conservative_denominator_per_arm": SELECTED_COUNT,
        "failure_as_zero": True,
        "candidate_exact64_before_control_or_evaluator_open": True,
        "both_arms_fully_evaluated_with_same_current_judge": True,
        "control": control_metrics,
        "candidate": candidate_metrics,
        "candidate_retrieval_health": health,
        "decision": gate,
        "provenance": {
            "protocol_sha256": sha256(root / FULL_PROTOCOL),
            "forward_result_sha256": sha256(root / FORWARD_RESULT),
            "candidate_prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
            "historical_control_result_sha256": sha256(
                root / prereg.CONTROL_RESULT
            ),
            "historical_control_prediction_freeze_sha256": control[
                "source_hashes"
            ]["prediction_freeze_sha256"],
            "historical_control_runtime_sha256": control["source_hashes"][
                "runtime_sha256"
            ],
            "historical_control_summary_sha256": control["source_hashes"][
                "summary_sha256"
            ],
            "mapping_sha256": live["mapping_sha256"],
            "query_data_sha256": live["query_data_sha256"],
            "answer_corpus_manifest_sha256": live[
                "answer_corpus_manifest_sha256"
            ],
            "evaluator_source_manifest_sha256": live[
                "evaluator_source_manifest_sha256"
            ],
            "judge": live["judge"],
            "recovery_policy": live["recovery_policy"],
            **{
                f"{arm}_evaluator_contract_sha256": evaluator_contracts[arm][
                    "run_contract_sha256"
                ]
                for arm in ARMS
            },
            **{
                f"{arm}_eval_results_sha256": sha256(
                    root / EVAL_RUN[arm] / "official_eval_results.jsonl"
                )
                for arm in ARMS
            },
            **{
                f"{arm}_conservative_summary_sha256": sha256(root / SUMMARY[arm])
                for arm in ARMS
            },
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "historical_control_predictions_opened_only_after_candidate_exact64_freeze": True,
            "mapping_gold_and_evaluator_opened_only_after_candidate_exact64_freeze": True,
            "both_arms_fully_evaluated_with_same_current_judge": True,
            "old_evaluator_rows_reused": False,
            "selective_changed_prediction_evaluation": False,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        },
        "authorization": {
            "exact220_design": gate["passed"],
            "new_exact220_launch": False,
            "additional_rollout_or_avg4": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "claims": {
            "development_gate_only": True,
            "independent_candidate_rollout_vs_frozen_control": True,
            "strict_shared_random_prefix_causal_ablation": False,
            "public_full220_result": False,
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
    print(
        json.dumps(
            {"result": str(FINAL_RESULT), "status": value["status"]},
            sort_keys=True,
        )
    )
