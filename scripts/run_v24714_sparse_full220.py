#!/usr/bin/env python3
"""One-shot V2.47.14 opaque-ID-joined sparse full-220 forward."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24714_sparse_full220_order_join as contract  # noqa: E402
from deepwide_agent.v24709_sparse_worldbank_adapter import TARGETS  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.run_v24711_sparse_full220 import (  # noqa: E402
    build_candidate_rows,
    download_bulk_bundle,
)


def validate_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("summary_payload_sha256", None)
    if (
        value.get("role") != "v24714_sparse_full220_run_summary"
        or value.get("protocol_id") != contract.PROTOCOL_ID
        or value.get("selected") != contract.SELECTED_COUNT
        or value.get("completed") != contract.SELECTED_COUNT
        or value.get("failed") != 0
        or value.get("route_eligible_tasks") not in {0, 1}
        or value.get("applied_tasks") not in {0, 1}
        or value.get("unchanged_prediction_hash_tasks", 0)
        + value.get("changed_prediction_hash_tasks", 0)
        != contract.SELECTED_COUNT
        or value.get("adapter_bulk_callback_invocations") not in {0, 1}
        or value.get("model_calls") != 0
        or value.get("search_calls") != 0
        or value.get("per_country_requests") != 0
        or value.get("runtime_input_keys") != ["opaque_id", "question"]
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get("official_evaluator_called") is not False
        or value.get("resume_retry_skip_or_selective_rerun") is not False
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.14 run summary drifted")
    return dict(value)


def validate_download(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_payload_sha256", None)
    downloads = value.get("downloads")
    if (
        value.get("role") != "v24714_worldbank_bulk_download_receipt"
        or value.get("protocol_id") != contract.PROTOCOL_ID
        or value.get("requested") != contract.DOWNLOAD_CAP
        or value.get("successful", 0) + value.get("failed", 0)
        != contract.DOWNLOAD_CAP
        or value.get("workers") != contract.DOWNLOAD_WORKERS
        or value.get("timeout_seconds_each") != contract.DOWNLOAD_TIMEOUT_SECONDS
        or value.get("per_country_requests") != 0
        or value.get("model_calls") != 0
        or value.get("search_calls") != 0
        or not isinstance(downloads, list)
        or len(downloads) != contract.DOWNLOAD_CAP
        or [item.get("url") for item in downloads]
        != [spec.url for spec in TARGETS]
        or any(item.get("attempts") != 1 for item in downloads)
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get("archive_content_or_credential_persisted") is not False
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.14 download receipt drifted")
    return dict(value)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20,
    ).stdout.strip()


def _tracked(path: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)], cwd=ROOT,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, timeout=20, check=False,
    ).returncode == 0


def _new_json(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _new_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _validate_launch_chain() -> dict[str, Any]:
    protocol = contract.validate_protocol(ROOT)
    preaudit = contract.validate_stage(
        ROOT, contract.PREAUDIT,
        role="v24714_sparse_full220_preactivation_audit",
        seal_field="audit_payload_sha256",
        authorization=contract.PREAUDIT_AUTHORIZATION,
    )
    activation = contract.validate_stage(
        ROOT, contract.ACTIVATION,
        role="v24714_sparse_full220_activation",
        seal_field="activation_payload_sha256",
        authorization=contract.ACTIVATION_AUTHORIZATION,
    )
    start = contract.validate_stage(
        ROOT, contract.EXECUTION_START,
        role="v24714_sparse_full220_execution_start",
        seal_field="execution_start_payload_sha256",
        authorization=contract.START_AUTHORIZATION,
    )
    if (
        preaudit.get("audit_valid") is not True
        or preaudit.get("findings") != []
        or activation.get("preaudit_sha256") != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("activation_sha256") != contract.sha256(ROOT / contract.ACTIVATION)
        or any(not _tracked(path) for path in (contract.PROTOCOL, contract.PREAUDIT, contract.ACTIVATION, contract.EXECUTION_START))
        or _git("status", "--porcelain")
        or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")
        or contract.protected_watcher_snapshot() != protocol["execution"]["protected_watchers"]
    ):
        raise RuntimeError("V2.47.14 launch chain drifted")
    return protocol


def main() -> None:
    protocol = _validate_launch_chain()
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (contract.OUTPUT_ROOT, contract.FORWARD_RESULT, contract.FORWARD_AUDIT)
    ):
        raise RuntimeError("V2.47.14 forward surface is not pristine")
    visible = contract.ordered_visible_rows(ROOT)
    control = contract.validate_control_rows(ROOT)
    if [row["opaque_id"] for row in visible] != [row["opaque_id"] for row in control]:
        raise RuntimeError("V2.47.14 ordered join drifted")
    with acquire_deepwide_api_lease(
        ROOT,
        owner=contract.LEASE_OWNER,
        purpose=contract.LEASE_PURPOSE,
        path=ROOT / contract.LEASE_PATH,
    ):
        started = time.monotonic()
        bundle, download = download_bulk_bundle(protocol["execution"]["download_urls"])
        rows, summary = build_candidate_rows(visible, control, bundle)
        summary = dict(summary)
        summary.pop("summary_payload_sha256")
        summary["role"] = "v24714_sparse_full220_run_summary"
        summary["protocol_id"] = contract.PROTOCOL_ID
        summary["forward_wall_seconds"] = round(max(0.0, time.monotonic() - started), 6)
        summary["summary_payload_sha256"] = contract.payload_sha256(summary)
        validate_summary(summary)
        download = dict(download)
        download.pop("receipt_payload_sha256")
        download["role"] = "v24714_worldbank_bulk_download_receipt"
        download["protocol_id"] = contract.PROTOCOL_ID
        download["receipt_payload_sha256"] = contract.payload_sha256(download)
        validate_download(download)
        (ROOT / contract.OUTPUT_ROOT).mkdir(parents=True, mode=0o700)
        _new_jsonl(ROOT / contract.RUNTIME_PREDICTIONS, rows)
        _new_json(ROOT / contract.RUN_SUMMARY, summary)
        _new_json(ROOT / contract.DOWNLOAD_RECEIPT, download)
        freeze = {
            "artifact_version": 1,
            "role": "v24714_sparse_full220_prediction_freeze",
            "protocol_id": contract.PROTOCOL_ID,
            "terminal": contract.SELECTED_COUNT,
            "route_eligible_tasks": summary["route_eligible_tasks"],
            "applied_tasks": summary["applied_tasks"],
            "unchanged_prediction_hash_tasks": summary["unchanged_prediction_hash_tasks"],
            "changed_prediction_hash_tasks": summary["changed_prediction_hash_tasks"],
            "runtime_predictions_sha256": contract.sha256(ROOT / contract.RUNTIME_PREDICTIONS),
            "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
            "download_receipt_sha256": contract.sha256(ROOT / contract.DOWNLOAD_RECEIPT),
            "all_220_predictions_terminal_before_mapping_gold_evaluator_or_score_open": True,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_opened_or_hashed": False,
            "official_evaluator_called": False,
        }
        freeze["freeze_payload_sha256"] = contract.payload_sha256(freeze)
        _new_json(ROOT / contract.PREDICTION_FREEZE, freeze)
        forward = {
            "artifact_version": 1,
            "role": "v24714_sparse_full220_forward_result",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "status": "forward_mechanism_gate_candidate" if summary["applied_tasks"] == 1 else "forward_mechanism_no_go",
            "terminal_predictions": contract.SELECTED_COUNT,
            "route_eligible_tasks": summary["route_eligible_tasks"],
            "applied_tasks": summary["applied_tasks"],
            "unchanged_prediction_hash_tasks": summary["unchanged_prediction_hash_tasks"],
            "changed_prediction_hash_tasks": summary["changed_prediction_hash_tasks"],
            "official_target_value_count": summary["official_target_value_count"],
            "changed_numeric_cell_count": summary["changed_numeric_cell_count"],
            "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
            "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
            "download_receipt_sha256": contract.sha256(ROOT / contract.DOWNLOAD_RECEIPT),
            "all_220_predictions_terminal_before_mapping_gold_evaluator_or_score_open": True,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "official_evaluator_called": False,
            "resume_retry_skip_or_selective_rerun": False,
            "exploratory_due_to_v24707_incident": True,
            "leaderboard_or_sota_claim": False,
        }
        forward["result_payload_sha256"] = contract.payload_sha256(forward)
        _new_json(ROOT / contract.FORWARD_RESULT, forward)
    if contract.protected_watcher_snapshot() != protocol["execution"]["protected_watchers"]:
        raise RuntimeError("V2.47.14 protected watcher drifted after forward")
    print(json.dumps({"forward_result": str(contract.FORWARD_RESULT), "terminal": contract.SELECTED_COUNT, "route_eligible": summary["route_eligible_tasks"], "applied": summary["applied_tasks"], "unchanged": summary["unchanged_prediction_hash_tasks"], "target_values": summary["official_target_value_count"], "wall_seconds": summary["forward_wall_seconds"]}, sort_keys=True))


if __name__ == "__main__":
    main()
