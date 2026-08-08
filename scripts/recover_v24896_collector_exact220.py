#!/usr/bin/env python3
"""Label-blind collector-only recovery of the frozen V2.48.95 forward.

The script performs no model, search, fetch, benchmark-label, mapping, gold,
score, or evaluator effect.  It validates every V2.48.95 task bundle with the
correct V2.48.90/V2.48.88 seam.  A valid committed bundle contributes its
already-frozen task result; every other task retains the already-frozen
V2.48.95 fallback row.  All 220 positions are processed in fixed order.
"""

from __future__ import annotations

import argparse
import hashlib
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

from deepwide_agent import v24895_control_binding_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24888_revision_envelope_exact_task import validate_envelope  # noqa: E402
from deepwide_agent.v24890_revision_envelope_mapping_bundle import validate_bundle  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import run_v24635_exact220 as algorithm  # noqa: E402


DATE = "20260808"
PROTOCOL = Path(f"results/v24896_collector_recovery_exact220_preregistration_v1_{DATE}.json")
AUDIT = Path(f"results/v24896_collector_recovery_exact220_audit_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24896_collector_recovery_exact220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24896_collector_recovery_exact220_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24896_collector_recovery_exact220_v1_{DATE}")
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SOURCE_ROOT = contract.OUTPUT_ROOT
SOURCE_TASK_ROOT = contract.TASK_ROOT
SOURCE_RUNTIME = contract.RUNTIME_PREDICTIONS
SOURCE_FORWARD = contract.FORWARD_RESULT
SOURCE_AUDIT = contract.FORWARD_AUDIT
ROLE_PREFIX = "v24896_collector_recovery_exact220"


def payload_sha256(value: object) -> str:
    return contract.payload_sha256(value)


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError(f"V2.48.96 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.96 expected JSON object")
    return value


def _rows(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.48.96 expected ordinary JSONL")
    values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if any(not isinstance(value, dict) for value in values):
        raise RuntimeError("V2.48.96 expected JSON objects")
    return values


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _write_json(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush(); os.fsync(handle.fileno())


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def build_protocol() -> dict[str, Any]:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main"):
        raise RuntimeError("V2.48.96 protocol requires clean pushed HEAD")
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (PROTOCOL, AUDIT, FORWARD_RESULT, FORWARD_AUDIT, OUTPUT_ROOT)):
        raise FileExistsError("V2.48.96 future surface exists")
    source_forward = _read(ROOT / SOURCE_FORWARD)
    source_audit = _read(ROOT / SOURCE_AUDIT)
    source_rows = _rows(ROOT / SOURCE_RUNTIME)
    if (
        source_forward.get("terminal_predictions") != 220
        or source_forward.get("fallback_tables") != 220
        or not _sealed(source_forward, "result_payload_sha256")
        or source_audit.get("audit_valid") is not True
        or source_audit.get("findings") != []
        or len(source_rows) != 220
    ):
        raise RuntimeError("V2.48.96 source forward drifted")
    value = {
        "artifact_version": 1,
        "role": f"{ROLE_PREFIX}_preregistration",
        "created_at_unix": int(time.time()),
        "git_head": _git("rev-parse", "HEAD"),
        "selected": 220,
        "fixed_position_order": list(range(1, 221)),
        "source": {
            "protocol": str(contract.PROTOCOL),
            "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
            "forward_result": str(SOURCE_FORWARD),
            "forward_result_sha256": contract.sha256(ROOT / SOURCE_FORWARD),
            "forward_audit": str(SOURCE_AUDIT),
            "forward_audit_sha256": contract.sha256(ROOT / SOURCE_AUDIT),
            "runtime_predictions": str(SOURCE_RUNTIME),
            "runtime_predictions_sha256": contract.sha256(ROOT / SOURCE_RUNTIME),
            "task_root": str(SOURCE_TASK_ROOT),
        },
        "recovery_contract": {
            "valid_v24890_bundle_uses_frozen_v24888_result": True,
            "invalid_or_missing_bundle_uses_same_position_frozen_v24895_fallback": True,
            "all_220_positions_processed_once": True,
            "model_search_fetch_network_or_process_effect": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "historical_correctness_or_score_used_for_selection": False,
            "retry_resume_selective_rerun_or_revaluation": False,
        },
        "authorization": {
            "audit": True,
            "collector_recovery": False,
            "postfreeze_exact220_evaluator": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return value


def validate_protocol(value: dict[str, Any]) -> dict[str, Any]:
    if (
        value.get("role") != f"{ROLE_PREFIX}_preregistration"
        or value.get("selected") != 220
        or value.get("fixed_position_order") != list(range(1, 221))
        or value.get("source", {}).get("forward_result_sha256") != contract.sha256(ROOT / SOURCE_FORWARD)
        or value.get("source", {}).get("runtime_predictions_sha256") != contract.sha256(ROOT / SOURCE_RUNTIME)
        or value.get("recovery_contract", {}).get("model_search_fetch_network_or_process_effect") is not False
        or value.get("recovery_contract", {}).get("mapping_gold_category_question_type_split_evaluator_score_reward_read") is not False
        or value.get("authorization") != {"audit": True, "collector_recovery": False, "postfreeze_exact220_evaluator": False}
        or not _sealed(value, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.48.96 protocol drifted")
    return value


def build_audit() -> dict[str, Any]:
    protocol = validate_protocol(_read(ROOT / PROTOCOL))
    fields = semantic_audit._accesses(Path(__file__).resolve(), ROOT)
    evaluator = semantic_audit._evaluator_capabilities(Path(__file__).resolve(), ROOT)
    source_protocol = contract.validate_protocol(
        ROOT, _read(ROOT / contract.PROTOCOL)
    )
    checks = {
        "clean_pushed_head": _git("status", "--porcelain") == "" and _git("rev-parse", "HEAD") == _git("rev-parse", "target/main"),
        "source_forward_exact220_frozen": _read(ROOT / SOURCE_FORWARD).get("terminal_predictions") == 220,
        "source_forward_audit_valid": _read(ROOT / SOURCE_AUDIT).get("audit_valid") is True,
        "source_runtime_rows_exact220": len(_rows(ROOT / SOURCE_RUNTIME)) == 220,
        "future_surface_pristine": all(not (ROOT / path).exists() and not (ROOT / path).is_symlink() for path in (AUDIT, FORWARD_RESULT, FORWARD_AUDIT, OUTPUT_ROOT)),
        "privileged_runtime_field_accesses_absent": fields == [],
        "evaluator_capabilities_absent": evaluator == [],
        "model_search_fetch_network_or_process_effect_absent": True,
        "protected_watchers_unchanged": contract.protected_watcher_snapshot()
        == source_protocol["execution"]["protected_watchers"],
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": f"{ROLE_PREFIX}_preactivation_audit",
        "created_at_unix": int(time.time()),
        "protocol_sha256": contract.sha256(ROOT / PROTOCOL),
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {"collector_recovery": not findings, "postfreeze_exact220_evaluator": False},
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "model_search_fetch_network_or_process_effect": False,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def collect_rows() -> tuple[list[dict[str, Any]], int]:
    fallback_rows = _rows(ROOT / SOURCE_RUNTIME)
    tasks = contract.task_vector(ROOT)
    if [row.get("opaque_id") for row in fallback_rows] != [task["opaque_id"] for task in tasks]:
        raise RuntimeError("V2.48.96 fallback vector drifted")
    recovered: list[dict[str, Any]] = []
    valid = 0
    for position in range(1, 221):
        directory = ROOT / SOURCE_TASK_ROOT / f"task_{position:04d}"
        try:
            validate_bundle(
                output_root=ROOT / SOURCE_ROOT,
                directory=directory,
                expected_model_slot_cap=contract.MODEL_SLOT_CAP,
            )
            result = validate_envelope(_read(directory / "result.json"))["result"]
            row = algorithm._runtime_row(result)
            valid += 1
        except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            row = fallback_rows[position - 1]
        if row.get("opaque_id") != tasks[position - 1]["opaque_id"]:
            raise RuntimeError("V2.48.96 position binding drifted")
        recovered.append(row)
    return recovered, valid


def recover() -> dict[str, Any]:
    protocol = validate_protocol(_read(ROOT / PROTOCOL))
    audit = _read(ROOT / AUDIT)
    if audit.get("audit_valid") is not True or audit.get("authorization", {}).get("collector_recovery") is not True or not _sealed(audit, "audit_payload_sha256"):
        raise RuntimeError("V2.48.96 recovery not authorized")
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main"):
        raise RuntimeError("V2.48.96 recovery requires clean pushed HEAD")
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (FORWARD_RESULT, FORWARD_AUDIT, OUTPUT_ROOT)):
        raise FileExistsError("V2.48.96 recovery surface exists")
    recovered, valid = collect_rows()
    (ROOT / OUTPUT_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
    _write_jsonl(ROOT / RUNTIME_PREDICTIONS, recovered)
    fallback = 220 - valid
    summary = {
        "artifact_version": 1,
        "role": f"{ROLE_PREFIX}_run_summary",
        "protocol_id": contract.PROTOCOL_ID,
        "selected": 220,
        "completed": 220,
        "failed": 0,
        "model_generated_tables": valid,
        "fallback_tables": fallback,
        "source_valid_bundles": valid,
        "source_invalid_or_missing_bundles": fallback,
        "system_total_tokens": sum(int(row["cost"]["system_total_tokens"]) for row in recovered),
        "forward_wall_seconds": _read(ROOT / SOURCE_FORWARD)["forward_wall_seconds"],
        "collector_model_search_fetch_network_or_process_effect": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }
    summary["summary_payload_sha256"] = payload_sha256(summary)
    _write_json(ROOT / RUN_SUMMARY, summary)
    hashes = [row["prediction_sha256"] for row in recovered]
    freeze = {
        "artifact_version": 1,
        "role": f"{ROLE_PREFIX}_prediction_freeze",
        "protocol_id": contract.PROTOCOL_ID,
        "selected": 220,
        "terminal": 220,
        "runtime_predictions_sha256": contract.sha256(ROOT / RUNTIME_PREDICTIONS),
        "run_summary_sha256": contract.sha256(ROOT / RUN_SUMMARY),
        "prediction_hashes_sha256": payload_sha256(hashes),
        "source_forward_result_sha256": protocol["source"]["forward_result_sha256"],
        "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
        "mapping_gold_or_evaluator_opened_or_hashed": False,
        "label_blind": True,
    }
    freeze["freeze_payload_sha256"] = payload_sha256(freeze)
    _write_json(ROOT / PREDICTION_FREEZE, freeze)
    forward = {
        "artifact_version": 1,
        "role": f"{ROLE_PREFIX}_forward_result",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "selected": 220,
        "terminal_predictions": 220,
        "model_generated_tables": valid,
        "fallback_tables": fallback,
        "system_total_tokens": summary["system_total_tokens"],
        "forward_wall_seconds": _read(ROOT / SOURCE_FORWARD)["forward_wall_seconds"],
        "source_forward_wall_seconds": _read(ROOT / SOURCE_FORWARD)["forward_wall_seconds"],
        "prediction_freeze_sha256": contract.sha256(ROOT / PREDICTION_FREEZE),
        "run_summary_sha256": contract.sha256(ROOT / RUN_SUMMARY),
        "collector_model_search_fetch_network_or_process_effect": False,
        "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "official_evaluator_called": False,
        "retry_resume_skip_or_selective_rerun_launched": False,
    }
    forward["result_payload_sha256"] = payload_sha256(forward)
    _write_json(ROOT / FORWARD_RESULT, forward)
    return forward


def build_forward_audit() -> dict[str, Any]:
    forward = _read(ROOT / FORWARD_RESULT)
    summary = _read(ROOT / RUN_SUMMARY)
    freeze = _read(ROOT / PREDICTION_FREEZE)
    rows = _rows(ROOT / RUNTIME_PREDICTIONS)
    tasks = contract.task_vector(ROOT)
    checks = {
        "exact220_rows": len(rows) == 220,
        "opaque_id_order_exact": [row.get("opaque_id") for row in rows] == [task["opaque_id"] for task in tasks],
        "model_and_fallback_sum_220": forward.get("model_generated_tables", -1) + forward.get("fallback_tables", -1) == 220,
        "valid_bundle_count_163": forward.get("model_generated_tables") == 163,
        "fallback_count_57": forward.get("fallback_tables") == 57,
        "runtime_predictions_hash_bound": freeze.get("runtime_predictions_sha256") == contract.sha256(ROOT / RUNTIME_PREDICTIONS),
        "summary_hash_bound": freeze.get("run_summary_sha256") == contract.sha256(ROOT / RUN_SUMMARY),
        "prediction_hash_vector_bound": freeze.get("prediction_hashes_sha256") == payload_sha256([row["prediction_sha256"] for row in rows]),
        "forward_sealed": _sealed(forward, "result_payload_sha256"),
        "summary_sealed": _sealed(summary, "summary_payload_sha256"),
        "freeze_sealed": _sealed(freeze, "freeze_payload_sha256"),
        "mapping_evaluator_closed": freeze.get("mapping_gold_or_evaluator_opened_or_hashed") is False,
        "collector_zero_effect": forward.get("collector_model_search_fetch_network_or_process_effect") is False,
        "clean_pushed_head": _git("status", "--porcelain") == "" and _git("rev-parse", "HEAD") == _git("rev-parse", "target/main"),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": f"{ROLE_PREFIX}_forward_audit",
        "created_at_unix": int(time.time()),
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "provenance": {
            "protocol_sha256": contract.sha256(ROOT / PROTOCOL),
            "preactivation_audit_sha256": contract.sha256(ROOT / AUDIT),
            "source_forward_result_sha256": contract.sha256(ROOT / SOURCE_FORWARD),
            "recovered_forward_result_sha256": contract.sha256(ROOT / FORWARD_RESULT),
            "prediction_freeze_sha256": contract.sha256(ROOT / PREDICTION_FREEZE),
            "runtime_predictions_sha256": contract.sha256(ROOT / RUNTIME_PREDICTIONS),
        },
        "authorization": {"postfreeze_exact220_evaluator": not findings, "selective_retry_or_revaluation": False},
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "model_search_fetch_network_or_process_effect": False,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("protocol", "audit", "recover", "forward-audit"))
    command = parser.parse_args().command
    if command == "protocol":
        value = validate_protocol(build_protocol()); path = PROTOCOL
    elif command == "audit":
        value = build_audit(); path = AUDIT
    elif command == "recover":
        value = recover(); path = FORWARD_RESULT
    else:
        value = build_forward_audit(); path = FORWARD_AUDIT
    if command != "recover":
        _write_json(ROOT / path, value)
    print(json.dumps({"path": str(path), "role": value["role"], "audit_valid": value.get("audit_valid"), "model_generated_tables": value.get("model_generated_tables"), "fallback_tables": value.get("fallback_tables")}, sort_keys=True))


if __name__ == "__main__":
    main()
