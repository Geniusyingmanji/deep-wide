#!/usr/bin/env python3
"""One-shot label-blind V2.47.11 sparse full-220 forward."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24709_sparse_worldbank_adapter import (  # noqa: E402
    MAX_ARCHIVE_BYTES,
    TARGETS,
    run_sparse_adapter,
    validate_result as validate_adapter_result,
)
from deepwide_agent.v24711_sparse_full220_contract import (  # noqa: E402
    ACTIVATION,
    DOWNLOAD_CAP,
    DOWNLOAD_RECEIPT,
    DOWNLOAD_TIMEOUT_SECONDS,
    DOWNLOAD_WORKERS,
    EXECUTION_START,
    EXPECTED_APPLIED_TASKS,
    EXPECTED_ROUTE_ELIGIBLE,
    EXPECTED_TARGET_VALUES,
    EXPECTED_UNCHANGED_TASKS,
    FORWARD_AUDIT,
    FORWARD_RESULT,
    LEASE_OWNER,
    LEASE_PATH,
    LEASE_PURPOSE,
    OUTPUT_ROOT,
    PREAUDIT,
    PREAUDIT_AUTHORIZATION,
    PREDICTION_FREEZE,
    PROTOCOL,
    PROTOCOL_ID,
    RUN_SUMMARY,
    RUNTIME_PREDICTIONS,
    SELECTED_COUNT,
    START_AUTHORIZATION,
    ACTIVATION_AUTHORIZATION,
    payload_sha256,
    protected_watcher_snapshot,
    read_object,
    sealed,
    sha256,
    validate_control_rows,
    validate_protocol,
    validate_stage,
    validate_visible_rows,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


COST_FIELDS = (
    "model_calls",
    "model_successful_calls",
    "model_failed_calls",
    "model_attempts",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "search_calls",
    "search_failures",
    "search_tool_calls",
    "search_fetch_calls",
    "search_fetch_failures",
    "search_input_tokens",
    "search_output_tokens",
    "search_total_tokens",
    "system_total_tokens",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    ).stdout.strip()


def _tracked(path: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0


def _new_json(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _new_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _download_one(url: str) -> tuple[str, bytes | None, dict[str, Any]]:
    started = time.monotonic()
    expected = {spec.url: spec.indicator for spec in TARGETS}
    if url not in expected:
        raise ValueError("V2.47.11 download URL is outside the frozen vector")
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "api.worldbank.org"
        or parsed.path != f"/v2/en/indicator/{expected[url]}"
        or parsed.query != "downloadformat=csv"
        or parsed.fragment
    ):
        raise ValueError("V2.47.11 World Bank URL drifted")
    raw: bytes | None = None
    status: int | None = None
    failure: str | None = None
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "deepwide-v24711-label-blind-forward/1"}
        )
        with urllib.request.urlopen(
            request, timeout=DOWNLOAD_TIMEOUT_SECONDS
        ) as response:
            final = urllib.parse.urlsplit(response.geturl())
            status = int(response.status)
            if (
                status != 200
                or final.scheme != "https"
                or final.hostname != "api.worldbank.org"
                or final.path != parsed.path
                or final.query != parsed.query
            ):
                raise RuntimeError("WorldBankEndpointDrift")
            raw = response.read(MAX_ARCHIVE_BYTES + 1)
            if not 0 < len(raw) <= MAX_ARCHIVE_BYTES:
                raise RuntimeError("WorldBankArchiveSizeDrift")
    except Exception as exc:
        raw = None
        failure = type(exc).__name__
    receipt = {
        "indicator": expected[url],
        "url": url,
        "attempts": 1,
        "success": raw is not None,
        "http_status": status,
        "bytes": len(raw) if raw is not None else 0,
        "sha256": hashlib.sha256(raw).hexdigest() if raw is not None else None,
        "coarse_failure_type": failure,
        "elapsed_seconds": round(max(0.0, time.monotonic() - started), 6),
        "response_value_or_credential_persisted": False,
    }
    return url, raw, receipt


def download_bulk_bundle(
    urls: Sequence[str],
) -> tuple[dict[str, bytes], dict[str, Any]]:
    expected = tuple(spec.url for spec in TARGETS)
    if tuple(urls) != expected or len(urls) != DOWNLOAD_CAP:
        raise ValueError("V2.47.11 bulk URL vector drifted")
    started = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=DOWNLOAD_WORKERS
    ) as executor:
        outcomes = list(executor.map(_download_one, urls))
    bundle = {url: raw for url, raw, _receipt in outcomes if raw is not None}
    receipts = [receipt for _url, _raw, receipt in outcomes]
    value = {
        "artifact_version": 1,
        "role": "v24711_worldbank_bulk_download_receipt",
        "requested": len(urls),
        "successful": len(bundle),
        "failed": len(urls) - len(bundle),
        "workers": DOWNLOAD_WORKERS,
        "timeout_seconds_each": DOWNLOAD_TIMEOUT_SECONDS,
        "per_country_requests": 0,
        "model_calls": 0,
        "search_calls": 0,
        "downloads": receipts,
        "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "archive_content_or_credential_persisted": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return bundle, value


def validate_download_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    downloads = value.get("downloads")
    unsigned = dict(value)
    seal = unsigned.pop("receipt_payload_sha256", None)
    if (
        value.get("role") != "v24711_worldbank_bulk_download_receipt"
        or value.get("requested") != DOWNLOAD_CAP
        or value.get("successful", 0) + value.get("failed", 0) != DOWNLOAD_CAP
        or value.get("workers") != DOWNLOAD_WORKERS
        or value.get("timeout_seconds_each") != DOWNLOAD_TIMEOUT_SECONDS
        or value.get("per_country_requests") != 0
        or value.get("model_calls") != 0
        or value.get("search_calls") != 0
        or not isinstance(downloads, list)
        or len(downloads) != DOWNLOAD_CAP
        or [item.get("url") for item in downloads]
        != [spec.url for spec in TARGETS]
        or any(item.get("attempts") != 1 for item in downloads)
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get("archive_content_or_credential_persisted") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.11 download receipt drifted")
    return dict(value)


def _zero_cost() -> dict[str, int]:
    return {name: 0 for name in COST_FIELDS}


def build_candidate_rows(
    visible_rows: Sequence[Mapping[str, str]],
    control_rows: Sequence[Mapping[str, Any]],
    bundle: Mapping[str, bytes],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if (
        len(visible_rows) != SELECTED_COUNT
        or len(control_rows) != SELECTED_COUNT
        or [row.get("opaque_id") for row in visible_rows]
        != [row.get("opaque_id") for row in control_rows]
    ):
        raise ValueError("V2.47.11 full220 vectors drifted")
    callback_count = 0

    def fetch(requested: tuple[str, ...]) -> Mapping[str, bytes]:
        nonlocal callback_count
        if requested != tuple(spec.url for spec in TARGETS):
            raise ValueError("V2.47.11 adapter URL vector drifted")
        callback_count += 1
        return bundle

    output: list[dict[str, Any]] = []
    failure_reasons: Counter[str] = Counter()
    route = applied = unchanged = target_values = changed_cells = 0
    for visible, control in zip(visible_rows, control_rows, strict=True):
        result = validate_adapter_result(
            run_sparse_adapter(
                {"opaque_id": visible["opaque_id"], "question": visible["question"]},
                str(control["prediction"]),
                fetch,
            )
        )
        identity = result["prediction_sha256"] == control["prediction_sha256"]
        route += int(result["route_eligible"])
        applied += int(result["applied"])
        unchanged += int(identity)
        target_values += int(result["target_value_count"])
        changed_cells += int(result["changed_cell_count"])
        if result["failure_reason"] is not None:
            failure_reasons[str(result["failure_reason"])] += 1
        row = {
            "opaque_id": visible["opaque_id"],
            "status": "completed",
            "prediction": result["prediction"],
            "prediction_sha256": result["prediction_sha256"],
            "control_prediction_sha256": control["prediction_sha256"],
            "completion_kind": (
                "v24709_sparse_worldbank_applied"
                if result["applied"]
                else "v24267_frozen_control_reuse"
            ),
            "error": None,
            "evidence_count": int(result["target_value_count"]),
            "cost": _zero_cost(),
            "elapsed_seconds": 0.0,
            "process_model_cost": {"trace_complete": True},
            "candidate_prediction_identity": identity,
            "route_eligible": result["route_eligible"],
            "adapter_applied": result["applied"],
            "adapter_failure_reason": result["failure_reason"],
            "identity_binding_count": result["identity_binding_count"],
            "target_value_count": result["target_value_count"],
            "changed_cell_count": result["changed_cell_count"],
            "entropy_credit_assigned": False,
            "label_blind": True,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        }
        validate_runtime_row(row)
        output.append(row)
    summary = {
        "artifact_version": 1,
        "role": "v24711_sparse_full220_run_summary",
        "selected": len(output),
        "completed": len(output),
        "failed": 0,
        "route_eligible_tasks": route,
        "applied_tasks": applied,
        "unchanged_prediction_hash_tasks": unchanged,
        "changed_prediction_hash_tasks": len(output) - unchanged,
        "official_target_value_count": target_values,
        "changed_numeric_cell_count": changed_cells,
        "adapter_bulk_callback_invocations": callback_count,
        "failure_reason_counts": dict(sorted(failure_reasons.items())),
        "model_calls": 0,
        "search_calls": 0,
        "per_country_requests": 0,
        "runtime_input_keys": ["opaque_id", "question"],
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "official_evaluator_called": False,
        "resume_retry_skip_or_selective_rerun": False,
    }
    summary["summary_payload_sha256"] = payload_sha256(summary)
    validate_run_summary(summary)
    return output, summary


def validate_runtime_row(value: Mapping[str, Any]) -> dict[str, Any]:
    prediction = value.get("prediction")
    identity = value.get("candidate_prediction_identity")
    applied = value.get("adapter_applied")
    if (
        value.get("status") != "completed"
        or not isinstance(value.get("opaque_id"), str)
        or not isinstance(prediction, str)
        or hashlib.sha256(prediction.encode("utf-8")).hexdigest()
        != value.get("prediction_sha256")
        or not isinstance(value.get("control_prediction_sha256"), str)
        or len(value["control_prediction_sha256"]) != 64
        or not isinstance(identity, bool)
        or not isinstance(applied, bool)
        or identity is not (
            value.get("prediction_sha256") == value.get("control_prediction_sha256")
        )
        or applied is identity
        or value.get("completion_kind")
        not in {
            "v24709_sparse_worldbank_applied",
            "v24267_frozen_control_reuse",
        }
        or value.get("error") is not None
        or value.get("cost") != _zero_cost()
        or value.get("process_model_cost") != {"trace_complete": True}
        or value.get("entropy_credit_assigned") is not False
        or value.get("label_blind") is not True
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
    ):
        raise ValueError("V2.47.11 runtime row drifted")
    return dict(value)


def validate_run_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("summary_payload_sha256", None)
    if (
        value.get("role") != "v24711_sparse_full220_run_summary"
        or value.get("selected") != SELECTED_COUNT
        or value.get("completed") != SELECTED_COUNT
        or value.get("failed") != 0
        or value.get("route_eligible_tasks") not in {0, 1}
        or value.get("applied_tasks") not in {0, 1}
        or value.get("unchanged_prediction_hash_tasks", 0)
        + value.get("changed_prediction_hash_tasks", 0)
        != SELECTED_COUNT
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
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.11 run summary drifted")
    return dict(value)


def _validate_launch_chain() -> dict[str, Any]:
    protocol = validate_protocol(ROOT)
    preaudit = validate_stage(
        ROOT,
        PREAUDIT,
        role="v24711_sparse_full220_preactivation_audit",
        seal_field="audit_payload_sha256",
        authorization=PREAUDIT_AUTHORIZATION,
    )
    activation = validate_stage(
        ROOT,
        ACTIVATION,
        role="v24711_sparse_full220_activation",
        seal_field="activation_payload_sha256",
        authorization=ACTIVATION_AUTHORIZATION,
    )
    start = validate_stage(
        ROOT,
        EXECUTION_START,
        role="v24711_sparse_full220_execution_start",
        seal_field="execution_start_payload_sha256",
        authorization=START_AUTHORIZATION,
    )
    if (
        preaudit.get("audit_valid") is not True
        or preaudit.get("findings") != []
        or activation.get("preaudit_sha256") != sha256(ROOT / PREAUDIT)
        or start.get("activation_sha256") != sha256(ROOT / ACTIVATION)
        or any(not _tracked(path) for path in (PROTOCOL, PREAUDIT, ACTIVATION, EXECUTION_START))
        or _git("status", "--porcelain")
        or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")
        or protected_watcher_snapshot() != protocol["execution"]["protected_watchers"]
    ):
        raise RuntimeError("V2.47.11 launch chain drifted")
    return protocol


def main() -> None:
    protocol = _validate_launch_chain()
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (OUTPUT_ROOT, FORWARD_RESULT, FORWARD_AUDIT)
    ):
        raise RuntimeError("V2.47.11 forward surface is not pristine")
    visible = validate_visible_rows(ROOT)
    control = validate_control_rows(ROOT)
    if [row["opaque_id"] for row in visible] != [row["opaque_id"] for row in control]:
        raise RuntimeError("V2.47.11 full220 order drifted")
    urls = protocol["execution"]["download_urls"]
    with acquire_deepwide_api_lease(
        ROOT,
        owner=LEASE_OWNER,
        purpose=LEASE_PURPOSE,
        path=ROOT / LEASE_PATH,
    ):
        started = time.monotonic()
        bundle, download = download_bulk_bundle(urls)
        rows, summary = build_candidate_rows(visible, control, bundle)
        wall = max(0.0, time.monotonic() - started)
        summary = dict(summary)
        summary.pop("summary_payload_sha256")
        summary["forward_wall_seconds"] = round(wall, 6)
        summary["summary_payload_sha256"] = payload_sha256(summary)
        validate_run_summary(summary)
        (ROOT / OUTPUT_ROOT).mkdir(parents=True, mode=0o700)
        _new_jsonl(ROOT / RUNTIME_PREDICTIONS, rows)
        _new_json(ROOT / RUN_SUMMARY, summary)
        validate_download_receipt(download)
        _new_json(ROOT / DOWNLOAD_RECEIPT, download)
        freeze = {
            "artifact_version": 1,
            "role": "v24711_sparse_full220_prediction_freeze",
            "protocol_id": PROTOCOL_ID,
            "terminal": SELECTED_COUNT,
            "route_eligible_tasks": summary["route_eligible_tasks"],
            "applied_tasks": summary["applied_tasks"],
            "unchanged_prediction_hash_tasks": summary[
                "unchanged_prediction_hash_tasks"
            ],
            "changed_prediction_hash_tasks": summary[
                "changed_prediction_hash_tasks"
            ],
            "runtime_predictions_sha256": sha256(ROOT / RUNTIME_PREDICTIONS),
            "run_summary_sha256": sha256(ROOT / RUN_SUMMARY),
            "download_receipt_sha256": sha256(ROOT / DOWNLOAD_RECEIPT),
            "all_220_predictions_terminal_before_mapping_gold_evaluator_or_score_open": True,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_opened_or_hashed": False,
            "official_evaluator_called": False,
        }
        freeze["freeze_payload_sha256"] = payload_sha256(freeze)
        _new_json(ROOT / PREDICTION_FREEZE, freeze)
        forward = {
            "artifact_version": 1,
            "role": "v24711_sparse_full220_forward_result",
            "protocol_id": PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "status": (
                "forward_mechanism_gate_candidate"
                if summary["applied_tasks"] == EXPECTED_APPLIED_TASKS
                else "forward_mechanism_no_go"
            ),
            "terminal_predictions": SELECTED_COUNT,
            "route_eligible_tasks": summary["route_eligible_tasks"],
            "applied_tasks": summary["applied_tasks"],
            "unchanged_prediction_hash_tasks": summary[
                "unchanged_prediction_hash_tasks"
            ],
            "changed_prediction_hash_tasks": summary[
                "changed_prediction_hash_tasks"
            ],
            "official_target_value_count": summary["official_target_value_count"],
            "changed_numeric_cell_count": summary["changed_numeric_cell_count"],
            "prediction_freeze_sha256": sha256(ROOT / PREDICTION_FREEZE),
            "run_summary_sha256": sha256(ROOT / RUN_SUMMARY),
            "download_receipt_sha256": sha256(ROOT / DOWNLOAD_RECEIPT),
            "all_220_predictions_terminal_before_mapping_gold_evaluator_or_score_open": True,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "official_evaluator_called": False,
            "resume_retry_skip_or_selective_rerun": False,
            "exploratory_due_to_v24707_incident": True,
            "leaderboard_or_sota_claim": False,
        }
        forward["result_payload_sha256"] = payload_sha256(forward)
        _new_json(ROOT / FORWARD_RESULT, forward)
    if protected_watcher_snapshot() != protocol["execution"]["protected_watchers"]:
        raise RuntimeError("V2.47.11 protected watcher drifted after forward")
    print(
        json.dumps(
            {
                "forward_result": str(FORWARD_RESULT),
                "terminal": SELECTED_COUNT,
                "route_eligible": summary["route_eligible_tasks"],
                "applied": summary["applied_tasks"],
                "unchanged": summary["unchanged_prediction_hash_tasks"],
                "target_values": summary["official_target_value_count"],
                "wall_seconds": summary["forward_wall_seconds"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
