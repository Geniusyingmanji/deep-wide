#!/usr/bin/env python3
"""Fixed-denominator zero-model V2.51.57 structure-layer forward."""

from __future__ import annotations

import copy
import json
import os
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24984_robust_late_page_projection as projection  # noqa: E402
from deepwide_agent import v25155_projection_structure_observer as observer  # noqa: E402
from deepwide_agent import v25157_structure_layer_gate_contract as contract  # noqa: E402
from deepwide_agent.v25061_html_surface import (  # noqa: E402
    decode_web_text,
    html_to_title_text,
)


ROW_COUNT_KEYS = observer.AGGREGATE_COUNT_NAMES
ROW_KEYS = {
    "artifact_version",
    "role",
    "protocol_id",
    "task_position",
    "terminal",
    "fetch_attempts",
    "fetch_success",
    "http_status",
    "structure_counts",
    "failure_as_zero",
    "failure_stage",
    "mapping_gold_category_question_type_split_evaluator_score_reward_read",
    "model_hosted_search_or_evaluator_called",
    "contains_opaque_id_package_endpoint_question_page_title_label_value_text_prediction_or_content_hash",
    "entropy_or_information_gain_assigns_signed_credit",
    "result_payload_sha256",
}
FAILURE_STAGES = {
    "none",
    "transport",
    "http_status",
    "redirect",
    "endpoint_identity",
    "content_type",
    "response_byte_cap",
    "empty_decoded_page",
    "projection_or_observer",
}


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.51.57 expected JSON object")
    return value


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _publish_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True))
            handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _clean_pushed() -> None:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(
        ROOT, "rev-parse", "HEAD"
    ) != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.51.57 forward requires clean pushed HEAD")


def _validate_start(protocol: Mapping[str, Any]) -> dict[str, Any]:
    value = _read(contract.EXECUTION_START)
    if (
        value.get("role") != "v25157_structure_layer_gate_execution_start"
        or value.get("protocol_id") != contract.PROTOCOL_ID
        or value.get("protocol_sha256")
        != contract.sha256(ROOT / contract.PROTOCOL)
        or value.get("preactivation_audit_sha256")
        != contract.sha256(ROOT / contract.PREAUDIT)
        or value.get("task_vector_sha256")
        != protocol["population"]["task_vector_sha256"]
        or value.get("endpoint_vector_sha256")
        != protocol["population"]["endpoint_vector_sha256"]
        or value.get("protected_watchers") != contract.watcher_snapshot()
        or value.get("authorization")
        != {
            "one_fixed_denominator_external_structure_forward": True,
            "model_hosted_search_or_evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_population_replacement_or_selective_revaluation": False,
        }
        or not contract.sealed(value, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.51.57 execution start drifted")
    return value


def _zero_counts() -> dict[str, int]:
    return {name: 0 for name in ROW_COUNT_KEYS}


def _failure_row(position: int, *, status: int, stage: str) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25157_structure_layer_task_receipt",
        "protocol_id": contract.PROTOCOL_ID,
        "task_position": int(position),
        "terminal": True,
        "fetch_attempts": 1,
        "fetch_success": False,
        "http_status": int(status),
        "structure_counts": _zero_counts(),
        "failure_as_zero": True,
        "failure_stage": stage,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "model_hosted_search_or_evaluator_called": False,
        "contains_opaque_id_package_endpoint_question_page_title_label_value_text_prediction_or_content_hash": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
    }
    return validate_task_row(contract.seal(value, "result_payload_sha256"))


def _fetch_one(position: int) -> dict[str, Any]:
    task = contract.task_vector()[position]
    endpoint = contract.endpoint_vector()[position]
    status = 0
    try:
        with requests.get(
            endpoint,
            headers={
                "User-Agent": "DeepWideResearch/1.0 (+v25157-content-free-structure-gate)"
            },
            timeout=(
                contract.FETCH_CONNECT_TIMEOUT_SECONDS,
                contract.FETCH_READ_TIMEOUT_SECONDS,
            ),
            allow_redirects=False,
            stream=True,
        ) as response:
            status = int(response.status_code)
            if status in {301, 302, 303, 307, 308}:
                return _failure_row(position, status=status, stage="redirect")
            if status != 200:
                return _failure_row(position, status=status, stage="http_status")
            if str(response.url) != endpoint:
                return _failure_row(
                    position, status=status, stage="endpoint_identity"
                )
            content_type = (
                response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            )
            if content_type not in {"text/html", "application/xhtml+xml", ""}:
                return _failure_row(position, status=status, stage="content_type")
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_content(chunk_size=1 << 20):
                if not chunk:
                    continue
                size += len(chunk)
                if size > contract.MAX_RESPONSE_BYTES:
                    return _failure_row(
                        position, status=status, stage="response_byte_cap"
                    )
                chunks.append(bytes(chunk))
            encoding = response.encoding
        decoded = decode_web_text(b"".join(chunks), encoding)
        title, text = html_to_title_text(decoded)
        if not title or not text:
            return _failure_row(
                position, status=status, stage="empty_decoded_page"
            )
        projected = projection.build_projection(
            task["question"],
            {"url": endpoint, "title": title, "text": text},
        )
        observation = observer.observe_structure(
            decoded, text, str(projected["projection"])
        )
        aggregate = observer.aggregate_observations([observation])
        value: dict[str, Any] = {
            "artifact_version": 1,
            "role": "v25157_structure_layer_task_receipt",
            "protocol_id": contract.PROTOCOL_ID,
            "task_position": int(position),
            "terminal": True,
            "fetch_attempts": 1,
            "fetch_success": True,
            "http_status": status,
            "structure_counts": copy.deepcopy(aggregate["counts"]),
            "failure_as_zero": False,
            "failure_stage": "none",
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "model_hosted_search_or_evaluator_called": False,
            "contains_opaque_id_package_endpoint_question_page_title_label_value_text_prediction_or_content_hash": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
        }
        return validate_task_row(contract.seal(value, "result_payload_sha256"))
    except (requests.RequestException, OSError):
        return _failure_row(position, status=status, stage="transport")
    except (TypeError, ValueError, RuntimeError, KeyError, IndexError):
        return _failure_row(
            position, status=status, stage="projection_or_observer"
        )


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    success = copied.get("fetch_success") is True
    counts = copied.get("structure_counts")
    if (
        set(copied) != ROW_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25157_structure_layer_task_receipt"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or isinstance(copied.get("task_position"), bool)
        or not isinstance(copied.get("task_position"), int)
        or not 0 <= copied["task_position"] < contract.TASK_COUNT
        or copied.get("terminal") is not True
        or copied.get("fetch_attempts") != 1
        or not isinstance(copied.get("fetch_success"), bool)
        or isinstance(copied.get("http_status"), bool)
        or not isinstance(copied.get("http_status"), int)
        or not 0 <= copied["http_status"] <= 599
        or not isinstance(counts, Mapping)
        or set(counts) != set(ROW_COUNT_KEYS)
        or any(
            isinstance(count, bool) or not isinstance(count, int) or count < 0
            for count in counts.values()
        )
        or counts["observed_page_count"] != int(success)
        or any(
            counts[name] > counts["observed_page_count"]
            for name in (
                "raw_structured_page_count",
                "extracted_structured_page_count",
                "projected_structured_page_count",
                "raw_to_extracted_total_structure_loss_page_count",
                "extracted_to_projected_total_structure_loss_page_count",
                "raw_table_and_extracted_pipe_page_count",
                "extracted_pipe_retained_after_projection_page_count",
                "extracted_key_value_pipe_retained_after_projection_page_count",
            )
        )
        or copied.get("failure_stage") not in FAILURE_STAGES
        or copied.get("failure_as_zero") is not (not success)
        or success
        and (copied["http_status"] != 200 or copied["failure_stage"] != "none")
        or not success
        and any(counts.values())
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_read",
                "model_hosted_search_or_evaluator_called",
                "contains_opaque_id_package_endpoint_question_page_title_label_value_text_prediction_or_content_hash",
                "entropy_or_information_gain_assigns_signed_credit",
            )
        )
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.51.57 content-free task receipt drifted")
    return copied


def aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    checked = [validate_task_row(row) for row in rows]
    if (
        len(checked) != contract.TASK_COUNT
        or [row["task_position"] for row in checked]
        != list(range(contract.TASK_COUNT))
    ):
        raise RuntimeError("V2.51.57 fixed task vector drifted")
    failures = Counter(row["failure_stage"] for row in checked)
    structure_counts = {
        name: sum(row["structure_counts"][name] for row in checked)
        for name in ROW_COUNT_KEYS
    }
    return {
        "task_count": len(checked),
        "terminal_tasks": sum(row["terminal"] is True for row in checked),
        "fetch_attempts": sum(row["fetch_attempts"] for row in checked),
        "fetch_successes": sum(row["fetch_success"] is True for row in checked),
        "failure_as_zero_tasks": sum(
            row["failure_as_zero"] is True for row in checked
        ),
        "structure_counts": structure_counts,
        "positive_signed_credit_count": sum(
            row["entropy_or_information_gain_assigns_signed_credit"] is True
            for row in checked
        ),
        "failure_stage_counts": dict(sorted(failures.items())),
    }


def mechanism_decision(value: Mapping[str, Any]) -> dict[str, Any]:
    counts = value.get("structure_counts") or {}
    events = sum(
        int(counts.get(name, 0))
        for name in (
            "raw_structured_page_count",
            "extracted_structured_page_count",
            "projected_structured_page_count",
            "raw_to_extracted_total_structure_loss_page_count",
            "extracted_to_projected_total_structure_loss_page_count",
        )
    )
    checks = {
        "fixed_terminal_denominator": value.get("task_count")
        == contract.TASK_COUNT
        and value.get("terminal_tasks") == contract.TASK_COUNT,
        "one_fetch_attempt_per_task": value.get("fetch_attempts")
        == contract.TASK_COUNT,
        "minimum_fetch_successes": value.get("fetch_successes", 0)
        >= contract.MINIMUM_FETCH_SUCCESSES,
        "minimum_observed_structure_pages": counts.get(
            "observed_page_count", 0
        )
        >= contract.MINIMUM_FETCH_SUCCESSES,
        "minimum_any_layer_structure_or_loss_events": events >= 1,
        "zero_positive_signed_credit": value.get("positive_signed_credit_count")
        == 0,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "checks": checks,
        "failed_checks": failed,
        "structure_localization_gate_passed": not failed,
        "next_layer_repair_design_authorized": not failed,
        "model_or_evaluator_on_this_population_authorized": False,
        "deepwidebench_dev64_exact220_or_sota": False,
    }


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != "v25157_structure_layer_gate_forward_result"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("mechanism_decision")
        != mechanism_decision(copied.get("aggregate") or {})
        or copied.get("authorization")
        != {
            "forward_audit": True,
            "next_layer_repair_design": False,
            "model_or_evaluator_on_this_population": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_population_replacement_or_selective_rerun": False,
        }
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.51.57 forward result drifted")
    return copied


def run_forward() -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    _validate_start(protocol)
    if (ROOT / contract.OUTPUT_ROOT).exists():
        raise FileExistsError(contract.OUTPUT_ROOT)
    (ROOT / contract.OUTPUT_ROOT).mkdir(parents=True, mode=0o700)
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=contract.FETCH_WORKERS) as pool:
        rows = list(pool.map(_fetch_one, range(contract.TASK_COUNT)))
    rows = [validate_task_row(row) for row in rows]
    _publish_jsonl(ROOT / contract.TASK_ROWS, rows)
    summary = aggregate(rows)
    decision = mechanism_decision(summary)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25157_structure_layer_gate_forward_result",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "wall_seconds": round(time.monotonic() - started, 6),
        "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        "aggregate": summary,
        "mechanism_decision": decision,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "model_hosted_search_or_evaluator_called": False,
        "retry_resume_population_replacement_or_selective_rerun": False,
        "authorization": {
            "forward_audit": True,
            "next_layer_repair_design": False,
            "model_or_evaluator_on_this_population": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_population_replacement_or_selective_rerun": False,
        },
    }
    value = contract.seal(value, "result_payload_sha256")
    _publish(ROOT / contract.FORWARD_RESULT, validate_forward_result(value))
    return value


def main() -> None:
    value = run_forward()
    print(
        json.dumps(
            {
                "path": str(contract.FORWARD_RESULT),
                "aggregate": value["aggregate"],
                "mechanism_decision": value["mechanism_decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
