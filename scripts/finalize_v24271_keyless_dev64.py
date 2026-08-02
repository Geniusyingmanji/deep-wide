#!/usr/bin/env python3
"""Post-freeze full64 evaluation of V2.42.71 control and candidate arms."""

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
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24259_deterministic_table_normalizer import (  # noqa: E402
    validate_v24259_result,
)
from deepwide_agent.v24271_forward_contract import (  # noqa: E402
    FORWARD_RESULT,
    PREDICTION_FREEZE,
    RUNTIME_PREDICTIONS,
    RUN_SUMMARY,
    SELECTED_COUNT,
    SOURCE_MANIFEST,
    FORWARD_PROTOCOL,
    validate_protocol as validate_forward_protocol,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.finalize_fullset_rollout import (  # noqa: E402
    _live_answer_corpus_manifest_sha256,
    _live_evaluator_source_manifest_sha256,
    prepare_rollout,
    read_jsonl,
    summarize_rollout,
    validate_evaluator_contract,
)
from scripts.preregister_v24271_keyless_dev64 import (  # noqa: E402
    CONTROL_OUTPUT_ROOT,
    CONTROL_POSTAUDIT,
    CONTROL_PREDICTION_FREEZE,
    CONTROL_PROTOCOL,
    CONTROL_RESULT,
    CONTROL_RUN_SUMMARY,
    CONTROL_RUNTIME,
    EVALUATOR_ROOT,
    FINAL_RESULT,
    MAPPING_PATH,
    OUTPUT,
    publish_new,
    selected_ids,
    validate_protocol,
)
from scripts.run_official_eval_local import validate_committed_eval_rows  # noqa: E402
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    read_object,
    sha256,
)
from scripts import run_v24267_exact220 as control_runner  # noqa: E402
from scripts.preregister_v24267_exact220 import (  # noqa: E402
    validate_protocol as validate_control_protocol,
)
from scripts import run_v24271_keyless_dev64 as candidate_runner  # noqa: E402


QUALITY = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
ARMS = ("control", "candidate")
ARM_ROOTS = {arm: EVALUATOR_ROOT / arm for arm in ARMS}
JOINED = {arm: ARM_ROOTS[arm] / "terminal_outcomes_evaluator_joined.jsonl" for arm in ARMS}
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
        "unrecoverable_provider_failures",
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
        "decision",
        "provenance",
        "source_policy",
        "authorization",
        "claims",
        "result_payload_sha256",
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
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _new_json(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def validate_candidate_barrier(root: Path) -> dict[str, Any]:
    """Validate candidate exact64 before any historical prediction is opened."""

    forward_protocol = validate_forward_protocol(root, FORWARD_PROTOCOL)
    forward = read_object(root / FORWARD_RESULT)
    candidate_runner.validate_forward_result(root, forward_protocol, forward)
    freeze = read_object(root / PREDICTION_FREEZE)
    rows = candidate_runner.validate_prediction_freeze(root, forward_protocol, freeze)
    if (
        forward.get("shared_model_receipts", {}).get(
            "all_acquisitions_match_actual_requests"
        )
        is not True
        or forward.get("candidate_exact64_before_control_or_evaluator_open")
        is not True
        or freeze.get(
            "exact_terminal_before_control_prediction_mapping_gold_or_evaluator_open"
        )
        is not True
    ):
        raise RuntimeError("V2.42.71 candidate freeze barrier is incomplete")
    return {
        "forward": forward,
        "freeze": freeze,
        "rows": rows,
        "summary": read_object(root / RUN_SUMMARY),
        "forward_protocol": forward_protocol,
    }


def validate_full_forward_binding(
    protocol: dict[str, Any], candidate: dict[str, Any]
) -> None:
    expected = protocol.get("forward_runtime_contract") or {}
    forward_protocol = candidate.get("forward_protocol") or {}
    if (
        expected.get("path") != str(FORWARD_PROTOCOL)
        or expected.get("payload_sha256")
        != forward_protocol.get("forward_contract_payload_sha256")
        or expected.get("contains_control_mapping_gold_evaluator_or_score_path")
        is not False
        or protocol.get("protocol_id") != forward_protocol.get("protocol_id")
        or protocol.get("task_contract", {}).get("selected_opaque_ids_sha256")
        != forward_protocol.get("task_contract", {}).get(
            "selected_opaque_ids_sha256"
        )
    ):
        raise RuntimeError("V2.42.71 full/forward protocol binding drifted")


def _control_task_results(
    root: Path, ids: list[str], full_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    start = len(full_rows) - SELECTED_COUNT + 1
    results: list[dict[str, Any]] = []
    for offset, opaque_id in enumerate(ids):
        position = start + offset
        path = root / CONTROL_OUTPUT_ROOT / "tasks" / f"task_{position:04d}" / "result.json"
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("V2.42.71 historical control task result is missing")
        value = read_object(path)
        validate_v24259_result(value)
        if value.get("opaque_id") != opaque_id:
            raise RuntimeError("V2.42.71 historical control task order drifted")
        results.append(value)
    return results


def load_frozen_control_after_candidate(
    root: Path, protocol: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    """This is the first function allowed to open historical predictions."""

    if len(candidate.get("rows") or []) != SELECTED_COUNT:
        raise RuntimeError("V2.42.71 candidate barrier was not supplied")
    parent = protocol["parents"]
    for key, path in (
        ("frozen_control_protocol", CONTROL_PROTOCOL),
        ("frozen_control_result", CONTROL_RESULT),
        ("frozen_control_postresult_audit", CONTROL_POSTAUDIT),
        ("frozen_control_prediction_freeze", CONTROL_PREDICTION_FREEZE),
    ):
        if sha256(root / path) != parent[key]["sha256"]:
            raise RuntimeError(f"V2.42.71 historical {key} drifted")
    control_protocol = validate_control_protocol(root, CONTROL_PROTOCOL)
    freeze = read_object(root / CONTROL_PREDICTION_FREEZE)
    full_rows = control_runner.validate_prediction_freeze(
        root, control_protocol, freeze
    )
    ids = selected_ids(root)
    rows = full_rows[-SELECTED_COUNT:]
    if (
        [row["opaque_id"] for row in rows] != ids
        or [row["opaque_id"] for row in candidate["rows"]] != ids
    ):
        raise RuntimeError("V2.42.71 control/candidate identity order drifted")
    results = _control_task_results(root, ids, full_rows)
    summary = {
        "selected": SELECTED_COUNT,
        "completed": SELECTED_COUNT,
        "failed": 0,
        "model_generated_tables": sum(
            row["completion_kind"] in candidate_runner.MODEL_GENERATED for row in rows
        ),
        "fallback_tables": sum(
            row["completion_kind"] not in candidate_runner.MODEL_GENERATED
            for row in rows
        ),
    }
    return {"rows": rows, "results": results, "summary": summary, "ids": ids}


def validate_live_evaluator_identity(
    root: Path, protocol: dict[str, Any]
) -> dict[str, Any]:
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
        raise RuntimeError("V2.42.71 live evaluator identity drifted")
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
    protocol: dict[str, Any],
    arm: str,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    ids: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    joined, official, base = prepare_rollout(
        manifest_rows=read_jsonl(root / SOURCE_MANIFEST),
        mapping_rows=read_jsonl(root / MAPPING_PATH),
        shards=[("devval", ids, rows, summary)],
        rollout_id=1,
    )
    if len(joined) != SELECTED_COUNT or len(official) != SELECTED_COUNT:
        raise RuntimeError(f"V2.42.71 {arm} evaluator prepare is not full64")
    attestation = {
        **base,
        "phase": "post_candidate_exact64_freeze_full_arm_evaluator_prepare",
        "arm": arm,
        "protocol_sha256": sha256(root / OUTPUT),
        "candidate_prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
        "candidate_exact64_before_control_mapping_gold_or_evaluator_open": True,
        "selective_changed_prediction_evaluation": False,
        "mapping_sha256": sha256(root / MAPPING_PATH),
        "manifest_sha256": sha256(root / SOURCE_MANIFEST),
    }
    return joined, official, attestation


def prepare_arm(
    root: Path,
    protocol: dict[str, Any],
    arm: str,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    ids: list[str],
) -> dict[str, Any]:
    joined, official, attestation = _expected_prepare(
        root, protocol, arm, rows, summary, ids
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
    protocol: dict[str, Any],
    arm: str,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    ids: list[str],
) -> dict[str, Any]:
    joined, official, expected = _expected_prepare(
        root, protocol, arm, rows, summary, ids
    )
    if (
        read_jsonl(root / JOINED[arm]) != joined
        or read_jsonl(root / OFFICIAL[arm]) != official
    ):
        raise RuntimeError(f"V2.42.71 {arm} prepared evaluator rows drifted")
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
        raise RuntimeError(f"V2.42.71 {arm} prepare attestation drifted")
    return {"joined": joined, "official": official, "attestation": attestation}


def evaluator_command(
    root: Path, protocol: dict[str, Any], arm: str, *, resume: bool
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
        raise RuntimeError("V2.42.71 evaluator command failed")


def _evaluate_both(
    root: Path,
    protocol: dict[str, Any],
    command_runner: Callable[..., subprocess.CompletedProcess[Any]],
    *,
    resume: bool,
) -> None:
    lease = protocol["lease_contract"]
    with acquire_deepwide_api_lease(
        root,
        owner=lease["evaluator_owner"],
        purpose=lease["evaluator_purpose"],
        path=root / lease["path"],
    ):
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="v24271-evaluator"
        ) as executor:
            futures = {
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
                ): arm
                for arm in ARMS
            }
            for future in concurrent.futures.as_completed(futures):
                future.result()


def _arm_metrics(
    summary: dict[str, Any],
    *,
    model_generated: int,
    search_tokens: int,
    wall_seconds: float,
    unrecoverable: int,
) -> dict[str, Any]:
    group = summary["groups"]["dev_validation_64"]
    conservative = group["conservative_all_selected"]
    metrics = {
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
        "unrecoverable_provider_failures": int(unrecoverable),
    }
    validate_arm_metrics(metrics)
    return metrics


def validate_arm_metrics(value: dict[str, Any]) -> None:
    if set(value) != ARM_METRIC_KEYS:
        raise RuntimeError("V2.42.71 arm metric schema drifted")
    counts = (
        "runtime_completed",
        "runtime_failed",
        "evaluator_valid",
        "evaluator_invalid_or_not_run",
        "whole_table_successes",
        "model_generated_tables",
        "fallback_tables",
        "search_total_tokens",
        "unrecoverable_provider_failures",
    )
    if any(
        isinstance(value[name], bool)
        or not isinstance(value[name], int)
        or value[name] < 0
        for name in counts
    ):
        raise RuntimeError("V2.42.71 arm count metric drifted")
    if (
        value["runtime_completed"] + value["runtime_failed"] != SELECTED_COUNT
        or value["evaluator_valid"] + value["evaluator_invalid_or_not_run"]
        != SELECTED_COUNT
        or value["model_generated_tables"] + value["fallback_tables"]
        != SELECTED_COUNT
    ):
        raise RuntimeError("V2.42.71 arm denominator drifted")
    for name in (*QUALITY, "quality_composite", "score"):
        number = value[name]
        if (
            isinstance(number, bool)
            or not isinstance(number, (int, float))
            or not math.isfinite(float(number))
            or not 0 <= float(number) <= 1
        ):
            raise RuntimeError("V2.42.71 arm quality metric drifted")
    wall = value["task_wall_sum_seconds"]
    if (
        isinstance(wall, bool)
        or not isinstance(wall, (int, float))
        or not math.isfinite(float(wall))
        or wall < 0
    ):
        raise RuntimeError("V2.42.71 arm wall metric drifted")


def decision(
    protocol: dict[str, Any], control: dict[str, Any], candidate: dict[str, Any]
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
        "candidate_unrecoverable_provider_failures": candidate[
            "unrecoverable_provider_failures"
        ]
        <= gate["candidate_unrecoverable_provider_failures_maximum"],
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
        "go_scope": "entropy_voc_successor_design_only",
    }


def validate_final_result(
    root: Path, protocol: dict[str, Any], value: dict[str, Any]
) -> None:
    if (
        set(value) != FINAL_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24271_keyless_dev64_result"
        or value.get("protocol_id") != protocol["protocol_id"]
        or value.get("status") not in {"development_gate_go", "development_gate_no_go"}
        or value.get("selected_per_arm") != SELECTED_COUNT
        or value.get("conservative_denominator_per_arm") != SELECTED_COUNT
        or value.get("failure_as_zero") is not True
        or value.get("candidate_exact64_before_control_or_evaluator_open") is not True
        or value.get("both_arms_fully_evaluated_with_same_current_judge") is not True
        or not _sealed(value, "result_payload_sha256")
    ):
        raise RuntimeError("V2.42.71 final result identity drifted")
    for arm in ARMS:
        validate_arm_metrics(value[arm])
    expected = decision(protocol, value["control"], value["candidate"])
    if value.get("decision") != expected:
        raise RuntimeError("V2.42.71 final decision drifted")
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
            raise RuntimeError(f"V2.42.71 {arm} evaluator provenance drifted")
    if value.get("claims") != {
        "development_gate_only": True,
        "independent_candidate_rollout_vs_frozen_control": True,
        "strict_shared_random_prefix_causal_ablation": False,
        "public_full220_result": False,
        "avg_at_4": False,
        "leaderboard_submitted": False,
        "sota": False,
    }:
        raise RuntimeError("V2.42.71 final claims drifted")


def finalize(
    root: Path = ROOT,
    *,
    command_runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
    resume_evaluator: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    if (root / FINAL_RESULT).exists() or (root / FINAL_RESULT).is_symlink():
        raise FileExistsError(root / FINAL_RESULT)

    # This ordering is the central leakage barrier.  No full experiment
    # protocol, historical control, mapping, gold, or evaluator resource is
    # opened until the minimal forward-only contract proves exact64 terminal.
    candidate = validate_candidate_barrier(root)
    protocol = validate_protocol(root, OUTPUT)
    validate_full_forward_binding(protocol, candidate)
    control = load_frozen_control_after_candidate(root, protocol, candidate)
    live = validate_live_evaluator_identity(root, protocol)

    evaluator_exists = (root / EVALUATOR_ROOT).exists() or (root / EVALUATOR_ROOT).is_symlink()
    if evaluator_exists != resume_evaluator:
        reason = "exists; explicit recovery required" if evaluator_exists else "recovery surface is absent"
        raise RuntimeError(f"V2.42.71 evaluator {reason}")
    ids = control["ids"]
    prepared: dict[str, dict[str, Any]] = {}
    arms = {
        "control": (control["rows"], control["summary"]),
        "candidate": (candidate["rows"], candidate["summary"]),
    }
    for arm, (rows, summary) in arms.items():
        prepared[arm] = (
            load_prepared_arm(root, protocol, arm, rows, summary, ids)
            if resume_evaluator
            else prepare_arm(root, protocol, arm, rows, summary, ids)
        )

    _evaluate_both(
        root, protocol, command_runner, resume=resume_evaluator
    )
    arm_summaries: dict[str, dict[str, Any]] = {}
    evaluator_contracts: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        eval_rows = read_jsonl(root / EVAL_RUN[arm] / "official_eval_results.jsonl")
        expected_ids = [row["instance_id"] for row in prepared[arm]["official"]]
        validate_committed_eval_rows(eval_rows, expected_ids)
        if len(eval_rows) != SELECTED_COUNT:
            raise RuntimeError(f"V2.42.71 {arm} evaluator is not full64 terminal")
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
                raise RuntimeError(f"V2.42.71 {arm} evaluator {key} drifted")
        arm_summaries[arm] = summarize_rollout(
            prepared[arm]["joined"], eval_rows, rollout_id=1
        )
        _new_json(root / SUMMARY[arm], arm_summaries[arm])

    control_search_tokens = sum(
        int(result["cost"]["search"]["total_tokens"])
        for result in control["results"]
    )
    control_wall = sum(float(row["elapsed_seconds"]) for row in control["rows"])
    candidate_summary = candidate["summary"]
    candidate_unrecoverable = sum(
        int(row["telemetry"]["raw_unrecoverable_failure_count"])
        for row in candidate["rows"]
    )
    control_metrics = _arm_metrics(
        arm_summaries["control"],
        model_generated=control["summary"]["model_generated_tables"],
        search_tokens=control_search_tokens,
        wall_seconds=control_wall,
        unrecoverable=0,
    )
    candidate_metrics = _arm_metrics(
        arm_summaries["candidate"],
        model_generated=candidate_summary["model_generated_tables"],
        search_tokens=candidate_summary["cost_totals"]["search_total_tokens"],
        wall_seconds=candidate_summary["wall_seconds_sum"],
        unrecoverable=candidate_unrecoverable,
    )
    gate = decision(protocol, control_metrics, candidate_metrics)
    result = {
        "artifact_version": 1,
        "role": "v24271_keyless_dev64_result",
        "protocol_id": protocol["protocol_id"],
        "created_at_unix": int(time.time()),
        "status": "development_gate_go" if gate["passed"] else "development_gate_no_go",
        "selected_per_arm": SELECTED_COUNT,
        "conservative_denominator_per_arm": SELECTED_COUNT,
        "failure_as_zero": True,
        "candidate_exact64_before_control_or_evaluator_open": True,
        "both_arms_fully_evaluated_with_same_current_judge": True,
        "control": control_metrics,
        "candidate": candidate_metrics,
        "decision": gate,
        "provenance": {
            "protocol_sha256": sha256(root / OUTPUT),
            "forward_result_sha256": sha256(root / FORWARD_RESULT),
            "candidate_prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
            "historical_control_protocol_sha256": sha256(root / CONTROL_PROTOCOL),
            "historical_control_prediction_freeze_sha256": sha256(
                root / CONTROL_PREDICTION_FREEZE
            ),
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
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
            "old_evaluator_rows_reused": False,
            "selective_changed_prediction_evaluation": False,
        },
        "authorization": {
            "entropy_voc_successor_design": gate["passed"],
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
    publish_new(root / FINAL_RESULT, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--resume-evaluator", action="store_true")
    args = parser.parse_args()
    value = finalize(
        Path(args.root), resume_evaluator=args.resume_evaluator
    )
    print(
        json.dumps(
            {"result": str(FINAL_RESULT), "status": value["status"]},
            sort_keys=True,
        )
    )
