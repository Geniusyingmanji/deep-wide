#!/usr/bin/env python3
"""Project content-free V2.42.61 serial metrics after all predictions froze."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24259_deterministic_table_normalizer import (  # noqa: E402
    validate_v24259_result,
)
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    read_object,
    sha256,
)


ROLE = "v24262_score_first_serial_baseline_projection"
OUTPUT = Path("results/v24262_score_first_serial_baseline_projection_v1_20260802.json")
PARENT_PROTOCOL = Path("results/v24261_direct_executor_smoke_preregistration_v1_20260802.json")
PARENT_RESULT = Path("results/v24261_direct_executor_smoke_result_v1_20260802.json")
PARENT_AUDIT = Path("results/v24261_direct_executor_smoke_postresult_audit_v1_20260802.json")
PARENT_TASK_ROOT = Path("outputs/v24261_direct_executor_smoke16_v1_20260802/tasks")
TASK_COUNT = 12


def _seal_valid(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def build_projection(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = read_object(root / PARENT_PROTOCOL)
    aggregate = read_object(root / PARENT_RESULT)
    audit = read_object(root / PARENT_AUDIT)
    if (
        protocol.get("protocol_id") != "v24261_direct_executor_smoke16_v1"
        or not _seal_valid(protocol, "decision_contract_sha256")
        or aggregate.get("engineering_gate") != "go"
        or aggregate.get("terminal") != 16
        or not _seal_valid(aggregate, "result_payload_sha256")
        or audit.get("audit_valid") is not True
        or not _seal_valid(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.42.62 serial projection parent drifted")
    ids_path = root / protocol["task_contract"]["id_source"]["path"]
    if ids_path.is_symlink() or not ids_path.is_file() or sha256(ids_path) != protocol["task_contract"]["id_source"]["sha256"]:
        raise RuntimeError("V2.42.62 serial projection ID source drifted")
    selected = [line for line in ids_path.read_text(encoding="utf-8").splitlines() if line][:TASK_COUNT]
    if len(selected) != TASK_COUNT or len(set(selected)) != TASK_COUNT:
        raise RuntimeError("V2.42.62 serial projection task prefix drifted")
    rows: list[dict[str, Any]] = []
    for position, opaque_id in enumerate(selected, start=1):
        result_path = root / PARENT_TASK_ROOT / f"task_{position:04d}" / "result.json"
        result = read_object(result_path)
        validate_v24259_result(result)
        if result.get("opaque_id") != opaque_id:
            raise RuntimeError("V2.42.62 serial projection task order drifted")
        rows.append(
            {
                "task_position": position,
                "completion_kind": str(result["completion_kind"]),
                "elapsed_seconds": float(result["budget"]["elapsed_seconds"]),
                "system_total_tokens": int(result["cost"]["system_total_tokens"]),
                "fetch_calls": int(result["cost"]["search"]["fetch_calls"]),
                "model_requests": int(result["cost"]["model"]["requests"]),
                "model_attempts": int(result["cost"]["model"]["attempts"]),
                "logical_search_calls": int(result["cost"]["search"]["calls"]),
                "logical_search_failures": int(result["cost"]["search"]["failures"]),
                "fetch_failures": int(result["cost"]["search"]["fetch_failures"]),
            }
        )
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "protocol": {"path": str(PARENT_PROTOCOL), "sha256": sha256(root / PARENT_PROTOCOL)},
            "result": {"path": str(PARENT_RESULT), "sha256": sha256(root / PARENT_RESULT)},
            "postresult_audit": {"path": str(PARENT_AUDIT), "sha256": sha256(root / PARENT_AUDIT)},
        },
        "selected_count": TASK_COUNT,
        "selected_opaque_ids_sha256": payload_sha256(selected),
        "selected_opaque_ids_persisted_or_emitted": False,
        "rows": rows,
        "rows_sha256": payload_sha256(rows),
        "source_policy": {
            "completed_parent_task_result_files_opened_post_terminal": True,
            "prediction_or_question_content_used_for_projection": False,
            "prediction_question_query_url_page_answer_or_opaque_id_persisted_hashed_or_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
            "network_model_search_fetch_or_evaluator_api_called": False,
        },
    }
    value["projection_payload_sha256"] = payload_sha256(value)
    return value


def validate_projection(root: Path = ROOT, path: Path = OUTPUT) -> dict[str, Any]:
    value = read_object(root / path)
    if (
        value.get("role") != ROLE
        or value.get("selected_count") != TASK_COUNT
        or value.get("source_policy", {}).get("prediction_or_question_content_used_for_projection") is not False
        or value.get("source_policy", {}).get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
        or not _seal_valid(value, "projection_payload_sha256")
    ):
        raise RuntimeError("V2.42.62 serial projection identity drifted")
    rows = value.get("rows")
    if not isinstance(rows, list) or len(rows) != TASK_COUNT or payload_sha256(rows) != value.get("rows_sha256"):
        raise RuntimeError("V2.42.62 serial projection rows drifted")
    expected_keys = {
        "task_position",
        "completion_kind",
        "elapsed_seconds",
        "system_total_tokens",
        "fetch_calls",
        "model_requests",
        "model_attempts",
        "logical_search_calls",
        "logical_search_failures",
        "fetch_failures",
    }
    if any(not isinstance(row, dict) or set(row) != expected_keys for row in rows):
        raise RuntimeError("V2.42.62 serial projection row schema drifted")
    for parent in value["parents"].values():
        if sha256(root / parent["path"]) != parent["sha256"]:
            raise RuntimeError("V2.42.62 serial projection parent bytes drifted")
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    publish_new(ROOT / OUTPUT, build_projection())
    print(json.dumps({"path": str(OUTPUT), "sha256": sha256(ROOT / OUTPUT)}))
