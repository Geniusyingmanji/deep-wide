#!/usr/bin/env python3
"""Post-terminal evaluator join and paired decision for V2.42.65."""

from __future__ import annotations

import argparse
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

from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.finalize_fullset_rollout import (  # noqa: E402
    METRICS,
    _live_answer_corpus_manifest_sha256,
    _live_evaluator_source_manifest_sha256,
    prepare_rollout,
    read_jsonl,
    summarize_rollout,
    validate_evaluator_contract,
)
from scripts.preregister_v24265_paired_dev64 import (  # noqa: E402
    CANDIDATE_FREEZE,
    CANDIDATE_RUNTIME,
    CANDIDATE_SUMMARY,
    CONTROL_FREEZE,
    CONTROL_RUNTIME,
    CONTROL_SUMMARY,
    EVALUATOR_ROOT,
    FINAL_RESULT,
    ID_SOURCE,
    MAPPING_PATH,
    OUTPUT,
    SELECTED_COUNT,
    SOURCE_MANIFEST,
    validate_protocol,
)
from scripts import run_v24265_paired_dev64 as forward_runner  # noqa: E402
from scripts.run_official_eval_local import (  # noqa: E402
    validate_committed_eval_rows,
)
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    read_object,
    sha256,
)


QUALITY = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
FINAL_RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "status",
        "selected",
        "conservative_denominator",
        "failure_as_zero",
        "exact_terminal_both_arms_before_evaluator",
        "candidate_changed_predictions_evaluated",
        "candidate_identical_predictions_reused",
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
METRIC_KEYS = frozenset(
    {
        "runtime_completed",
        "runtime_failed",
        "evaluator_valid",
        "evaluator_invalid_or_not_run",
        "whole_table_successes",
        "system_total_tokens",
        *QUALITY,
        "quality_composite",
        "model_generated_tables",
    }
)
DECISION_KEYS = frozenset(
    {"status", "passed", "checks", "candidate_minus_control", "system_total_tokens_ratio"}
)
PROVENANCE_KEYS = frozenset(
    {
        "protocol_sha256",
        "forward_result_sha256",
        "control_freeze_sha256",
        "candidate_freeze_sha256",
        "mapping_sha256",
        "control_evaluator_contract_sha256",
        "candidate_changed_evaluator_contract_sha256",
        "query_data_sha256",
        "answer_corpus_manifest_sha256",
        "evaluator_source_manifest_sha256",
        "judge",
        "recovery_policy",
        "candidate_hybrid_eval_results_sha256",
    }
)


def _sealed(path: Path, role: str, field: str) -> dict[str, Any]:
    value = read_object(path)
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    if value.get("role") != role or seal != payload_sha256(unsigned):
        raise RuntimeError(f"V2.42.65 sealed artifact drifted: {path}")
    return value


def validate_forward_freezes(root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    forward_path = root / protocol["execution"]["forward_result_path"]
    forward = _sealed(
        forward_path,
        "v24265_shared_prefix_paired_dev64_forward_result",
        "result_payload_sha256",
    )
    forward_runner.validate_forward_result(protocol, forward, root=root)
    if (
        forward.get("shared_model_receipts", {}).get(
            "all_acquisitions_match_actual_requests"
        )
        is not True
    ):
        raise RuntimeError("V2.42.65 forward model-slot receipts are incomplete")
    control = _sealed(
        root / CONTROL_FREEZE,
        "v24265_control_prediction_freeze",
        "freeze_payload_sha256",
    )
    candidate = _sealed(
        root / CANDIDATE_FREEZE,
        "v24265_candidate_prediction_freeze",
        "freeze_payload_sha256",
    )
    if (
        forward.get("selected") != SELECTED_COUNT
        or forward.get("terminal_pairs") != SELECTED_COUNT
        or forward.get("both_arms_exact_terminal_before_evaluator_open") is not True
        or forward.get("mapping_query_answer_gold_or_evaluator_opened_or_hashed")
        is not False
        or forward.get("official_evaluator_called") is not False
        or control.get("selected") != SELECTED_COUNT
        or control.get("terminal") != SELECTED_COUNT
        or candidate.get("selected") != SELECTED_COUNT
        or candidate.get("terminal") != SELECTED_COUNT
        or control.get(
            "exact_terminal_before_mapping_query_answer_gold_or_evaluator_open"
        )
        is not True
        or candidate.get(
            "exact_terminal_before_mapping_query_answer_gold_or_evaluator_open"
        )
        is not True
        or control.get("mapping_query_answer_gold_or_evaluator_opened_or_hashed")
        is not False
        or candidate.get("mapping_query_answer_gold_or_evaluator_opened_or_hashed")
        is not False
        or control.get("runtime_predictions_sha256") != sha256(root / CONTROL_RUNTIME)
        or candidate.get("runtime_predictions_sha256")
        != sha256(root / CANDIDATE_RUNTIME)
        or control.get("run_summary_sha256") != sha256(root / CONTROL_SUMMARY)
        or candidate.get("run_summary_sha256") != sha256(root / CANDIDATE_SUMMARY)
        or forward.get("control", {}).get("prediction_freeze_sha256")
        != sha256(root / CONTROL_FREEZE)
        or forward.get("candidate", {}).get("prediction_freeze_sha256")
        != sha256(root / CANDIDATE_FREEZE)
    ):
        raise RuntimeError("V2.42.65 exact terminal freeze barrier drifted")
    control_rows = read_jsonl(root / CONTROL_RUNTIME)
    candidate_rows = read_jsonl(root / CANDIDATE_RUNTIME)
    ids = [line for line in (root / ID_SOURCE).read_text().splitlines() if line]
    for rows in (control_rows, candidate_rows):
        if (
            len(rows) != SELECTED_COUNT
            or [row.get("opaque_id") for row in rows] != ids
            or any(row.get("status") != "completed" for row in rows)
        ):
            raise RuntimeError("V2.42.65 runtime exact64 barrier drifted")
        for row in rows:
            forward_runner.validate_runtime_row(row)
    forward_runner.validate_summary(read_object(root / CONTROL_SUMMARY), "control")
    forward_runner.validate_summary(read_object(root / CANDIDATE_SUMMARY), "candidate")
    return {
        "forward": forward,
        "control_freeze": control,
        "candidate_freeze": candidate,
        "control_rows": control_rows,
        "candidate_rows": candidate_rows,
        "ids": ids,
    }


def validate_live_evaluator_identity(
    root: Path, protocol: dict[str, Any]
) -> dict[str, Any]:
    """Open and hash evaluator-only resources only after both freezes validate."""

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
        or _live_answer_corpus_manifest_sha256(answer_root)
        != answers.get("manifest_sha256")
        or _live_evaluator_source_manifest_sha256()
        != source.get("manifest_sha256")
        or not isinstance(evaluator.get("judge"), dict)
        or not isinstance(evaluator.get("recovery_policy"), dict)
    ):
        raise RuntimeError("V2.42.65 live evaluator identity drifted")
    return {
        "query_data_sha256": query["sha256"],
        "answer_corpus_manifest_sha256": answers["manifest_sha256"],
        "evaluator_source_manifest_sha256": source["manifest_sha256"],
        "judge": dict(evaluator["judge"]),
        "recovery_policy": dict(evaluator["recovery_policy"]),
    }


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


def partition_candidate_predictions(
    control_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    expected = {"instance_id", "question", "rollout_id", "prediction", "messages"}
    if (
        len(control_rows) != len(candidate_rows)
        or any(set(row) != expected for row in [*control_rows, *candidate_rows])
    ):
        raise RuntimeError("V2.42.65 paired evaluator row schema drifted")
    control_by_id = {row["instance_id"]: row for row in control_rows}
    if len(control_by_id) != len(control_rows):
        raise RuntimeError("V2.42.65 duplicate control evaluator identity")
    changed: list[dict[str, Any]] = []
    identical: list[str] = []
    for row in candidate_rows:
        control = control_by_id.get(row["instance_id"])
        if control is None:
            raise RuntimeError("V2.42.65 candidate evaluator identity is unpaired")
        if (
            row["question"] != control["question"]
            or row["messages"][0] != control["messages"][0]
        ):
            raise RuntimeError("V2.42.65 paired evaluator question drifted")
        if row["prediction"] == control["prediction"]:
            if row != control:
                raise RuntimeError(
                    "V2.42.65 identical prediction evaluator identity drifted"
                )
            identical.append(row["instance_id"])
        else:
            changed.append(row)
    if len(changed) + len(identical) != len(candidate_rows):
        raise RuntimeError("V2.42.65 candidate evaluator partition drifted")
    return changed, identical


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


def prepare_evaluator_inputs(
    root: Path, protocol: dict[str, Any], frozen: dict[str, Any]
) -> dict[str, Any]:
    # This is the first point where mapping bytes are permitted to open.
    evaluator = protocol["evaluator_contract"]
    mapping = root / MAPPING_PATH
    if mapping.is_symlink() or not mapping.is_file() or sha256(mapping) != evaluator["mapping"]["sha256"]:
        raise RuntimeError("V2.42.65 evaluator mapping drifted")
    manifest = root / SOURCE_MANIFEST
    manifest_rows = read_jsonl(manifest)
    mapping_rows = read_jsonl(mapping)
    outputs: dict[str, Any] = {}
    for arm in ("control", "candidate"):
        runtime_rows = frozen[f"{arm}_rows"]
        summary = read_object(root / (CONTROL_SUMMARY if arm == "control" else CANDIDATE_SUMMARY))
        joined, official, base = prepare_rollout(
            manifest_rows=manifest_rows,
            mapping_rows=mapping_rows,
            shards=[("devval", frozen["ids"], runtime_rows, summary)],
            rollout_id=1,
        )
        if len(joined) != SELECTED_COUNT or len(official) != SELECTED_COUNT:
            raise RuntimeError("V2.42.65 evaluator join is not exact64")
        arm_root = root / EVALUATOR_ROOT / arm
        arm_root.mkdir(mode=0o700, parents=True, exist_ok=False)
        outcomes = arm_root / "terminal_outcomes_evaluator_joined.jsonl"
        predictions = arm_root / "official_predictions.jsonl"
        _write_jsonl_new(outcomes, joined)
        _write_jsonl_new(predictions, official)
        outputs[arm] = {
            "joined": joined,
            "official": official,
            "outcomes": outcomes,
            "predictions": predictions,
            "prepare": {
                **base,
                "phase": "post_both_freezes_paired_dev64_evaluator_prepare",
                "mapping_sha256": sha256(mapping),
                "manifest_sha256": sha256(manifest),
                "runtime_predictions_sha256": sha256(
                    root / (CONTROL_RUNTIME if arm == "control" else CANDIDATE_RUNTIME)
                ),
                "prediction_freeze_sha256": sha256(
                    root / (CONTROL_FREEZE if arm == "control" else CANDIDATE_FREEZE)
                ),
                "terminal_outcomes_sha256": sha256(outcomes),
                "official_predictions_sha256": sha256(predictions),
                "both_arms_exact_terminal_before_mapping_open": True,
            },
        }
        outputs[arm]["prepare"]["prepare_payload_sha256"] = payload_sha256(
            outputs[arm]["prepare"]
        )
        _new_json(arm_root / "prepare_attestation.json", outputs[arm]["prepare"])
    changed, identical = partition_candidate_predictions(
        outputs["control"]["official"], outputs["candidate"]["official"]
    )
    changed_path = root / EVALUATOR_ROOT / "candidate" / "changed_predictions.jsonl"
    _write_jsonl_new(changed_path, changed)
    outputs["candidate_changed"] = changed
    outputs["candidate_identical_ids"] = identical
    outputs["candidate_changed_path"] = changed_path
    return outputs


def load_prepared_evaluator_inputs(
    root: Path, protocol: dict[str, Any], frozen: dict[str, Any]
) -> dict[str, Any]:
    """Rebuild expected joins and validate a crash-recovery prepare prefix."""

    evaluator = protocol["evaluator_contract"]
    mapping = root / MAPPING_PATH
    manifest = root / SOURCE_MANIFEST
    if (
        mapping.is_symlink()
        or not mapping.is_file()
        or sha256(mapping) != evaluator["mapping"]["sha256"]
        or manifest.is_symlink()
        or not manifest.is_file()
    ):
        raise RuntimeError("V2.42.65 recovery evaluator inputs drifted")
    manifest_rows = read_jsonl(manifest)
    mapping_rows = read_jsonl(mapping)
    outputs: dict[str, Any] = {}
    for arm in ("control", "candidate"):
        runtime_path = root / (
            CONTROL_RUNTIME if arm == "control" else CANDIDATE_RUNTIME
        )
        summary_path = root / (
            CONTROL_SUMMARY if arm == "control" else CANDIDATE_SUMMARY
        )
        freeze_path = root / (
            CONTROL_FREEZE if arm == "control" else CANDIDATE_FREEZE
        )
        expected_joined, expected_official, base = prepare_rollout(
            manifest_rows=manifest_rows,
            mapping_rows=mapping_rows,
            shards=[
                (
                    "devval",
                    frozen["ids"],
                    frozen[f"{arm}_rows"],
                    read_object(summary_path),
                )
            ],
            rollout_id=1,
        )
        arm_root = root / EVALUATOR_ROOT / arm
        outcomes = arm_root / "terminal_outcomes_evaluator_joined.jsonl"
        predictions = arm_root / "official_predictions.jsonl"
        attestation_path = arm_root / "prepare_attestation.json"
        if (
            read_jsonl(outcomes) != expected_joined
            or read_jsonl(predictions) != expected_official
        ):
            raise RuntimeError("V2.42.65 recovery prepared rows drifted")
        attestation = read_object(attestation_path)
        seal = dict(attestation)
        digest = seal.pop("prepare_payload_sha256", None)
        expected_prepare = {
            **base,
            "phase": "post_both_freezes_paired_dev64_evaluator_prepare",
            "mapping_sha256": sha256(mapping),
            "manifest_sha256": sha256(manifest),
            "runtime_predictions_sha256": sha256(runtime_path),
            "prediction_freeze_sha256": sha256(freeze_path),
            "terminal_outcomes_sha256": sha256(outcomes),
            "official_predictions_sha256": sha256(predictions),
            "both_arms_exact_terminal_before_mapping_open": True,
        }
        if seal != expected_prepare or digest != payload_sha256(seal):
            raise RuntimeError("V2.42.65 recovery prepare attestation drifted")
        outputs[arm] = {
            "joined": expected_joined,
            "official": expected_official,
            "outcomes": outcomes,
            "predictions": predictions,
            "prepare": attestation,
        }
    expected_changed, identical = partition_candidate_predictions(
        outputs["control"]["official"], outputs["candidate"]["official"]
    )
    changed_path = root / EVALUATOR_ROOT / "candidate" / "changed_predictions.jsonl"
    if read_jsonl(changed_path) != expected_changed:
        raise RuntimeError("V2.42.65 recovery changed prediction set drifted")
    outputs["candidate_changed"] = expected_changed
    outputs["candidate_identical_ids"] = identical
    outputs["candidate_changed_path"] = changed_path
    return outputs


def _validate_provenance_identity(
    provenance: dict[str, Any], expected: dict[str, Any]
) -> None:
    for key in (
        "query_data_sha256",
        "answer_corpus_manifest_sha256",
        "evaluator_source_manifest_sha256",
        "judge",
        "recovery_policy",
    ):
        if provenance.get(key) != expected.get(key):
            raise RuntimeError(f"V2.42.65 evaluator {key} drifted")


def _run_logged(
    command_runner: Callable[..., subprocess.CompletedProcess[Any]],
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
        completed = command_runner(
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
        raise RuntimeError(f"V2.42.65 evaluator command failed: {log}")


def evaluator_command(
    root: Path,
    protocol: dict[str, Any],
    predictions: Path,
    output: Path,
    *,
    resume: bool = False,
) -> list[str]:
    judge = protocol["evaluator_contract"]["judge"]
    command = [
        str(root / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(root / "scripts/run_official_eval_local.py"),
        "--predictions",
        str(predictions),
        "--out-dir",
        str(output),
        "--query-path",
        str(root / protocol["evaluator_contract"]["query_data"]["path"]),
        "--answer-root",
        str(root / protocol["evaluator_contract"]["answer_corpus"]["root"]),
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


def _metrics(summary: dict[str, Any]) -> dict[str, Any]:
    group = summary["groups"]["dev_validation_64"]
    metrics = group["conservative_all_selected"]
    return {
        "runtime_completed": group["runtime_completed"],
        "runtime_failed": group["runtime_failed"],
        "evaluator_valid": group["evaluator_valid"],
        "evaluator_invalid_or_not_run": group["evaluator_invalid_or_not_run"],
        "whole_table_successes": sum(
            row["evaluator_valid"] and row["metrics"]["score"] > 0
            for row in summary["per_task"]
            if row["split"] in {"dev", "validation"}
        ),
        "system_total_tokens": group["cost_totals"]["system_total_tokens"],
        **{name: float(metrics[name]) for name in QUALITY},
        "quality_composite": sum(float(metrics[name]) for name in QUALITY)
        / len(QUALITY),
    }


def paired_decision(
    protocol: dict[str, Any], control: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    gate = protocol["paired_gate"]
    delta = {
        name: candidate[name] - control[name]
        for name in (
            "runtime_completed",
            "whole_table_successes",
            *QUALITY,
            "quality_composite",
        )
    }
    token_ratio = (
        candidate["system_total_tokens"] / control["system_total_tokens"]
        if control["system_total_tokens"] > 0
        else math.inf
    )
    directional = gate["directional_gain_any"]
    checks = {
        "model_generated_non_decrease": candidate["model_generated_tables"]
        - control["model_generated_tables"]
        >= gate["model_generated_table_delta_minimum"],
        "whole_table_non_decrease": delta["whole_table_successes"]
        >= gate["whole_table_success_delta_minimum"],
        "quality_component_safety": all(
            delta[name] >= gate["each_quality_component_delta_minimum"]
            for name in QUALITY
        ),
        "token_ratio": token_ratio <= gate["system_total_tokens_ratio_maximum"],
        "directional_gain": (
            candidate["model_generated_tables"]
            - control["model_generated_tables"]
            >= directional["model_generated_table_delta_minimum"]
            or delta["whole_table_successes"]
            >= directional["whole_table_success_delta_minimum"]
            or delta["quality_composite"]
            >= directional["quality_composite_delta_minimum"]
        ),
    }
    return {
        "status": "go" if all(checks.values()) else "no_go",
        "passed": all(checks.values()),
        "checks": checks,
        "candidate_minus_control": delta,
        "system_total_tokens_ratio": token_ratio,
    }


def validate_final_result(
    protocol: dict[str, Any], value: dict[str, Any], *, root: Path = ROOT
) -> None:
    if (
        set(value) != FINAL_RESULT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24265_shared_prefix_paired_dev64_result"
        or value.get("protocol_id") != protocol["protocol_id"]
        or value.get("status") not in {"go", "no_go"}
        or value.get("selected") != SELECTED_COUNT
        or value.get("conservative_denominator") != SELECTED_COUNT
        or value.get("failure_as_zero") is not True
        or value.get("exact_terminal_both_arms_before_evaluator") is not True
    ):
        raise RuntimeError("V2.42.65 final result identity drifted")
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    if seal != payload_sha256(unsigned):
        raise RuntimeError("V2.42.65 final result seal drifted")
    changed = value.get("candidate_changed_predictions_evaluated")
    identical = value.get("candidate_identical_predictions_reused")
    if (
        isinstance(changed, bool)
        or not isinstance(changed, int)
        or changed < 0
        or isinstance(identical, bool)
        or not isinstance(identical, int)
        or identical < 0
        or changed + identical != SELECTED_COUNT
    ):
        raise RuntimeError("V2.42.65 evaluator partition accounting drifted")
    for arm in ("control", "candidate"):
        metrics = value.get(arm)
        if not isinstance(metrics, dict) or set(metrics) != METRIC_KEYS:
            raise RuntimeError("V2.42.65 final arm metric schema drifted")
    decision = value.get("decision")
    if not isinstance(decision, dict) or set(decision) != DECISION_KEYS:
        raise RuntimeError("V2.42.65 final decision schema drifted")
    if decision != paired_decision(protocol, value["control"], value["candidate"]):
        raise RuntimeError("V2.42.65 final decision binding drifted")
    if value["status"] != decision["status"]:
        raise RuntimeError("V2.42.65 final status binding drifted")
    provenance = value.get("provenance")
    if not isinstance(provenance, dict) or set(provenance) != PROVENANCE_KEYS:
        raise RuntimeError("V2.42.65 final provenance schema drifted")
    expected_hashes = {
        "protocol_sha256": sha256(root / OUTPUT),
        "forward_result_sha256": sha256(
            root / protocol["execution"]["forward_result_path"]
        ),
        "control_freeze_sha256": sha256(root / CONTROL_FREEZE),
        "candidate_freeze_sha256": sha256(root / CANDIDATE_FREEZE),
        "mapping_sha256": sha256(root / MAPPING_PATH),
        "candidate_hybrid_eval_results_sha256": sha256(
            root / EVALUATOR_ROOT / "candidate_hybrid_eval_results.jsonl"
        ),
    }
    if any(provenance.get(key) != digest for key, digest in expected_hashes.items()):
        raise RuntimeError("V2.42.65 final provenance binding drifted")
    evaluator = protocol["evaluator_contract"]
    if (
        provenance.get("query_data_sha256")
        != evaluator["query_data"]["sha256"]
        or provenance.get("answer_corpus_manifest_sha256")
        != evaluator["answer_corpus"]["manifest_sha256"]
        or provenance.get("evaluator_source_manifest_sha256")
        != evaluator["evaluator_source"]["manifest_sha256"]
        or provenance.get("judge") != evaluator["judge"]
        or provenance.get("recovery_policy") != evaluator["recovery_policy"]
    ):
        raise RuntimeError("V2.42.65 final evaluator identity drifted")
    source = value.get("source_policy")
    authorization = value.get("authorization")
    claims = value.get("claims")
    if (
        not isinstance(source, dict)
        or set(source)
        != {
            "runtime_boundary",
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward",
            "mapping_opened_only_after_both_exact64_freezes",
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection",
        }
        or source.get("runtime_boundary") != ["opaque_id", "question"]
        or source.get(
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward"
        )
        is not False
        or source.get("mapping_opened_only_after_both_exact64_freezes") is not True
        or source.get(
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection"
        )
        is not False
        or not isinstance(authorization, dict)
        or authorization.get("exact220_launch") is not False
        or authorization.get("leaderboard_submission_or_sota_claim") is not False
        or authorization.get("successor_exact220_design") is not decision["passed"]
        or not isinstance(claims, dict)
        or claims
        != {
            "development_ablation_only": True,
            "fresh_or_held_out": False,
            "full220_result": False,
            "avg_at_4": False,
            "sota": False,
        }
    ):
        raise RuntimeError("V2.42.65 final source or claim policy drifted")


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
    frozen = validate_forward_freezes(root, protocol)
    live_evaluator = validate_live_evaluator_identity(root, protocol)
    evaluator_exists = (root / EVALUATOR_ROOT).exists() or (
        root / EVALUATOR_ROOT
    ).is_symlink()
    if evaluator_exists and not resume_evaluator:
        raise RuntimeError(
            "V2.42.65 evaluator surface exists; explicit recovery is required"
        )
    if not evaluator_exists and resume_evaluator:
        raise RuntimeError("V2.42.65 evaluator recovery surface is absent")
    prepared = (
        load_prepared_evaluator_inputs(root, protocol, frozen)
        if resume_evaluator
        else prepare_evaluator_inputs(root, protocol, frozen)
    )
    lease = protocol["lease_contract"]
    control_eval = root / EVALUATOR_ROOT / "control_eval"
    changed_eval = root / EVALUATOR_ROOT / "candidate_changed_eval"
    with acquire_deepwide_api_lease(
        root,
        owner=lease["evaluator_owner"],
        purpose=lease["evaluator_purpose"],
        path=root / lease["path"],
    ):
        _run_logged(
            command_runner,
            evaluator_command(
                root,
                protocol,
                prepared["control"]["predictions"],
                control_eval,
                resume=resume_evaluator and control_eval.exists(),
            ),
            root=root,
            log=root / EVALUATOR_ROOT / "control_evaluate.log",
        )
        if prepared["candidate_changed"]:
            _run_logged(
                command_runner,
                evaluator_command(
                    root,
                    protocol,
                    prepared["candidate_changed_path"],
                    changed_eval,
                    resume=resume_evaluator and changed_eval.exists(),
                ),
                root=root,
                log=root / EVALUATOR_ROOT / "candidate_changed_evaluate.log",
            )
    control_rows = read_jsonl(control_eval / "official_eval_results.jsonl")
    control_ids = [row["instance_id"] for row in prepared["control"]["official"]]
    validate_committed_eval_rows(control_rows, control_ids)
    if len(control_rows) != SELECTED_COUNT:
        raise RuntimeError("V2.42.65 control evaluator is not exact64 terminal")
    changed_rows = (
        read_jsonl(changed_eval / "official_eval_results.jsonl")
        if prepared["candidate_changed"]
        else []
    )
    changed_ids = [row["instance_id"] for row in prepared["candidate_changed"]]
    validate_committed_eval_rows(changed_rows, changed_ids)
    if len(changed_rows) != len(changed_ids):
        raise RuntimeError("V2.42.65 changed candidate evaluator is incomplete")
    control_by_id = {row["instance_id"]: row for row in control_rows}
    changed_by_id = {row["instance_id"]: row for row in changed_rows}
    candidate_rows = [
        changed_by_id.get(row["instance_id"], control_by_id[row["instance_id"]])
        for row in prepared["candidate"]["official"]
    ]
    candidate_ids = [row["instance_id"] for row in prepared["candidate"]["official"]]
    validate_committed_eval_rows(candidate_rows, candidate_ids)
    hybrid = root / EVALUATOR_ROOT / "candidate_hybrid_eval_results.jsonl"
    _write_jsonl_new(hybrid, candidate_rows)
    control_summary = summarize_rollout(
        prepared["control"]["joined"], control_rows, rollout_id=1
    )
    candidate_summary = summarize_rollout(
        prepared["candidate"]["joined"], candidate_rows, rollout_id=1
    )
    control_metrics = _metrics(control_summary)
    candidate_metrics = _metrics(candidate_summary)
    control_metrics["model_generated_tables"] = frozen["forward"]["control"][
        "model_generated_tables"
    ]
    candidate_metrics["model_generated_tables"] = frozen["forward"]["candidate"][
        "model_generated_tables"
    ]
    control_provenance = validate_evaluator_contract(
        control_eval / "run_config.json",
        expected_predictions_path=prepared["control"]["predictions"],
        expected_predictions_sha256=sha256(prepared["control"]["predictions"]),
        expected_selected_count=SELECTED_COUNT,
    )
    _validate_provenance_identity(control_provenance, live_evaluator)
    candidate_changed_provenance = None
    if changed_ids:
        candidate_changed_provenance = validate_evaluator_contract(
            changed_eval / "run_config.json",
            expected_predictions_path=prepared["candidate_changed_path"],
            expected_predictions_sha256=sha256(prepared["candidate_changed_path"]),
            expected_selected_count=len(changed_ids),
        )
        _validate_provenance_identity(candidate_changed_provenance, live_evaluator)
    decision = paired_decision(protocol, control_metrics, candidate_metrics)
    result = {
        "artifact_version": 1,
        "role": "v24265_shared_prefix_paired_dev64_result",
        "protocol_id": protocol["protocol_id"],
        "created_at_unix": int(time.time()),
        "status": decision["status"],
        "selected": SELECTED_COUNT,
        "conservative_denominator": SELECTED_COUNT,
        "failure_as_zero": True,
        "exact_terminal_both_arms_before_evaluator": True,
        "candidate_changed_predictions_evaluated": len(changed_ids),
        "candidate_identical_predictions_reused": len(
            prepared["candidate_identical_ids"]
        ),
        "control": control_metrics,
        "candidate": candidate_metrics,
        "decision": decision,
        "provenance": {
            "protocol_sha256": sha256(root / OUTPUT),
            "forward_result_sha256": sha256(
                root / protocol["execution"]["forward_result_path"]
            ),
            "control_freeze_sha256": sha256(root / CONTROL_FREEZE),
            "candidate_freeze_sha256": sha256(root / CANDIDATE_FREEZE),
            "mapping_sha256": sha256(root / MAPPING_PATH),
            "control_evaluator_contract_sha256": control_provenance[
                "run_contract_sha256"
            ],
            "candidate_changed_evaluator_contract_sha256": (
                candidate_changed_provenance["run_contract_sha256"]
                if candidate_changed_provenance is not None
                else None
            ),
            "query_data_sha256": live_evaluator["query_data_sha256"],
            "answer_corpus_manifest_sha256": live_evaluator[
                "answer_corpus_manifest_sha256"
            ],
            "evaluator_source_manifest_sha256": live_evaluator[
                "evaluator_source_manifest_sha256"
            ],
            "judge": live_evaluator["judge"],
            "recovery_policy": live_evaluator["recovery_policy"],
            "candidate_hybrid_eval_results_sha256": sha256(hybrid),
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "mapping_opened_only_after_both_exact64_freezes": True,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        },
        "authorization": {
            "successor_exact220_design": decision["passed"],
            "exact220_launch": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "claims": {
            "development_ablation_only": True,
            "fresh_or_held_out": False,
            "full220_result": False,
            "avg_at_4": False,
            "sota": False,
        },
    }
    result["result_payload_sha256"] = payload_sha256(result)
    validate_final_result(protocol, result, root=root)
    _new_json(root / FINAL_RESULT, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--resume-evaluator", action="store_true")
    args = parser.parse_args()
    value = finalize(Path(args.root), resume_evaluator=args.resume_evaluator)
    print(json.dumps({"result": str(FINAL_RESULT), "status": value["status"]}, sort_keys=True))
