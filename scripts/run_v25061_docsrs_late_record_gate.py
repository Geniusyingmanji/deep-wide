#!/usr/bin/env python3
"""Fixed-denominator, zero-model V2.50.61 external mechanism forward."""

from __future__ import annotations

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

from deepwide_agent import (  # noqa: E402
    v25061_pure_version_qualified_late_record as representation,
)
from deepwide_agent import v25061_docsrs_late_record_gate_contract as contract  # noqa: E402
from deepwide_agent.v25061_html_surface import (  # noqa: E402
    decode_web_text,
    html_to_title_text,
)


ROW_KEYS = {
    "artifact_version",
    "role",
    "protocol_id",
    "task_position",
    "terminal",
    "fetch_attempts",
    "fetch_success",
    "http_status",
    "decoded_page_characters",
    "input_characters_beyond_parent_prefix",
    "qualified_identity_binding_count",
    "complete_record_count",
    "late_target_field_count",
    "admissible_record_count",
    "mechanism_engaged",
    "candidate_evidence_changed",
    "projection_failure_count",
    "positive_signed_credit_count",
    "failure_as_zero",
    "failure_stage",
    "mapping_gold_category_question_type_split_evaluator_score_reward_read",
    "model_search_or_evaluator_called",
    "contains_opaque_id_crate_endpoint_question_page_title_field_value_prediction_or_page_hash",
    "result_payload_sha256",
}
FAILURE_STAGES = {
    "none",
    "transport",
    "http_status",
    "endpoint_identity",
    "content_type",
    "response_byte_cap",
    "empty_decoded_page",
    "representation",
}


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.61 expected JSON object")
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
            handle.write(
                json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n"
            )
        handle.flush()
        os.fsync(handle.fileno())


def _clean_pushed() -> None:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(
        ROOT, "rev-parse", "HEAD"
    ) != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.50.61 forward requires clean pushed HEAD")


def _validate_start(protocol: Mapping[str, Any]) -> dict[str, Any]:
    value = _read(contract.EXECUTION_START)
    expected_keys = {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "git_head",
        "protocol_sha256",
        "preactivation_audit_sha256",
        "task_vector_sha256",
        "endpoint_vector_sha256",
        "protected_watchers",
        "authorization",
        "execution_start_payload_sha256",
    }
    expected_authorization = {
        "one_fixed_denominator_external_mechanism_forward": True,
        "model_search_or_evaluator": False,
        "deepwidebench_dev64_exact220_or_sota": False,
        "retry_resume_population_replacement_or_selective_revaluation": False,
    }
    if (
        set(value) != expected_keys
        or value.get("artifact_version") != 1
        or value.get("role") != "v25061_docsrs_late_record_execution_start"
        or value.get("protocol_id") != contract.PROTOCOL_ID
        or value.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or value.get("preactivation_audit_sha256")
        != contract.sha256(ROOT / contract.PREAUDIT)
        or value.get("task_vector_sha256")
        != protocol["population"]["task_vector_sha256"]
        or value.get("endpoint_vector_sha256")
        != protocol["population"]["endpoint_vector_sha256"]
        or value.get("protected_watchers") != contract.watcher_snapshot()
        or value.get("authorization") != expected_authorization
        or not contract.sealed(value, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.50.61 execution start drifted")
    return value


def _failure_row(
    position: int, *, status: int, stage: str, projection_failure: int = 0
) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": "v25061_docsrs_late_record_task_receipt",
        "protocol_id": contract.PROTOCOL_ID,
        "task_position": int(position),
        "terminal": True,
        "fetch_attempts": 1,
        "fetch_success": False,
        "http_status": int(status),
        "decoded_page_characters": 0,
        "input_characters_beyond_parent_prefix": 0,
        "qualified_identity_binding_count": 0,
        "complete_record_count": 0,
        "late_target_field_count": 0,
        "admissible_record_count": 0,
        "mechanism_engaged": False,
        "candidate_evidence_changed": False,
        "projection_failure_count": int(projection_failure),
        "positive_signed_credit_count": 0,
        "failure_as_zero": True,
        "failure_stage": stage,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "model_search_or_evaluator_called": False,
        "contains_opaque_id_crate_endpoint_question_page_title_field_value_prediction_or_page_hash": False,
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
                "User-Agent": "DeepWideResearch/1.0 (+v25061-zero-model-mechanism-gate)"
            },
            timeout=(
                contract.FETCH_CONNECT_TIMEOUT_SECONDS,
                contract.FETCH_READ_TIMEOUT_SECONDS,
            ),
            allow_redirects=False,
            stream=True,
        ) as response:
            status = int(response.status_code)
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
        rendered = representation.build_representation(
            task["question"], {"url": endpoint, "title": title, "text": text}
        )
        receipt = representation.validate_receipt(
            rendered["version_qualified_late_record_receipt"]
        )
        value = {
            "artifact_version": 1,
            "role": "v25061_docsrs_late_record_task_receipt",
            "protocol_id": contract.PROTOCOL_ID,
            "task_position": int(position),
            "terminal": True,
            "fetch_attempts": 1,
            "fetch_success": True,
            "http_status": status,
            "decoded_page_characters": len(text),
            "input_characters_beyond_parent_prefix": receipt[
                "input_characters_beyond_parent_prefix"
            ],
            "qualified_identity_binding_count": receipt[
                "version_qualified_consensus_binding_count"
            ],
            "complete_record_count": receipt["discovered_record_count"],
            "late_target_field_count": receipt["late_target_field_count"],
            "admissible_record_count": receipt["admissible_record_count"],
            "mechanism_engaged": receipt["mechanism_engaged"],
            "candidate_evidence_changed": receipt["candidate_evidence_changed"],
            "projection_failure_count": receipt["projection_failure_count"],
            "positive_signed_credit_count": receipt[
                "positive_signed_credit_count"
            ],
            "failure_as_zero": False,
            "failure_stage": "none",
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "model_search_or_evaluator_called": False,
            "contains_opaque_id_crate_endpoint_question_page_title_field_value_prediction_or_page_hash": False,
        }
        return validate_task_row(contract.seal(value, "result_payload_sha256"))
    except (requests.RequestException, OSError):
        return _failure_row(position, status=status, stage="transport")
    except (TypeError, ValueError, RuntimeError, KeyError, IndexError):
        return _failure_row(
            position,
            status=status,
            stage="representation",
            projection_failure=1,
        )


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    success = copied.get("fetch_success") is True
    engaged = copied.get("mechanism_engaged") is True
    if (
        set(copied) != ROW_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25061_docsrs_late_record_task_receipt"
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
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in (
                "decoded_page_characters",
                "input_characters_beyond_parent_prefix",
                "qualified_identity_binding_count",
                "complete_record_count",
                "late_target_field_count",
                "admissible_record_count",
                "projection_failure_count",
                "positive_signed_credit_count",
            )
        )
        or copied["qualified_identity_binding_count"] > 1
        or copied["complete_record_count"] > 1
        or copied["admissible_record_count"] > copied["complete_record_count"]
        or copied["positive_signed_credit_count"] != 0
        or copied.get("failure_stage") not in FAILURE_STAGES
        or copied.get("failure_as_zero") is not (not success)
        or success
        and (
            copied["http_status"] != 200
            or copied["decoded_page_characters"] <= 0
            or copied["failure_stage"] != "none"
        )
        or not success
        and any(
            copied[name] != 0
            for name in (
                "decoded_page_characters",
                "input_characters_beyond_parent_prefix",
                "qualified_identity_binding_count",
                "complete_record_count",
                "late_target_field_count",
                "admissible_record_count",
                "positive_signed_credit_count",
            )
        )
        or not success
        and copied["projection_failure_count"]
        != int(copied["failure_stage"] == "representation")
        or engaged
        is not (
            success
            and copied["admissible_record_count"] == 1
            and copied["late_target_field_count"] >= 1
            and copied.get("candidate_evidence_changed") is True
            and copied["projection_failure_count"] == 0
        )
        or copied.get("candidate_evidence_changed") is not engaged
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read"
        )
        is not False
        or copied.get("model_search_or_evaluator_called") is not False
        or copied.get(
            "contains_opaque_id_crate_endpoint_question_page_title_field_value_prediction_or_page_hash"
        )
        is not False
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.50.61 content-free task receipt drifted")
    return copied


def aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    checked = [validate_task_row(row) for row in rows]
    if (
        len(checked) != contract.TASK_COUNT
        or [row["task_position"] for row in checked]
        != list(range(contract.TASK_COUNT))
    ):
        raise RuntimeError("V2.50.61 fixed task vector drifted")
    failures = Counter(row["failure_stage"] for row in checked)
    return {
        "task_count": len(checked),
        "terminal_tasks": sum(row["terminal"] is True for row in checked),
        "fetch_attempts": sum(row["fetch_attempts"] for row in checked),
        "fetch_successes": sum(row["fetch_success"] is True for row in checked),
        "failure_as_zero_tasks": sum(
            row["failure_as_zero"] is True for row in checked
        ),
        "decoded_pages_over_5k": sum(
            row["decoded_page_characters"] > representation.PAGE_CHARACTER_CAP
            for row in checked
        ),
        "qualified_identity_pages": sum(
            row["qualified_identity_binding_count"] == 1 for row in checked
        ),
        "complete_record_pages": sum(
            row["complete_record_count"] == 1 for row in checked
        ),
        "late_target_pages": sum(
            row["late_target_field_count"] >= 1 for row in checked
        ),
        "mechanism_exposed_pages": sum(
            row["mechanism_engaged"] is True for row in checked
        ),
        "candidate_evidence_changed_pages": sum(
            row["candidate_evidence_changed"] is True for row in checked
        ),
        "projection_failure_count": sum(
            row["projection_failure_count"] for row in checked
        ),
        "positive_signed_credit_count": sum(
            row["positive_signed_credit_count"] for row in checked
        ),
        "failure_stage_counts": dict(sorted(failures.items())),
    }


def mechanism_decision(value: Mapping[str, Any]) -> dict[str, Any]:
    checks = {
        "fixed_terminal_denominator": value.get("task_count") == contract.TASK_COUNT
        and value.get("terminal_tasks") == contract.TASK_COUNT,
        "one_fetch_attempt_per_task": value.get("fetch_attempts")
        == contract.TASK_COUNT,
        "minimum_fetch_successes": value.get("fetch_successes", 0)
        >= contract.MINIMUM_FETCH_SUCCESSES,
        "minimum_natural_exposures": value.get("mechanism_exposed_pages", 0)
        >= contract.MINIMUM_NATURAL_EXPOSURES,
        "every_exposure_changes_evidence": value.get("mechanism_exposed_pages")
        == value.get("candidate_evidence_changed_pages"),
        "every_exposure_has_late_target": value.get("mechanism_exposed_pages", 0)
        <= value.get("late_target_pages", 0),
        "zero_projection_failure": value.get("projection_failure_count") == 0,
        "zero_positive_signed_credit": value.get("positive_signed_credit_count")
        == 0,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "checks": checks,
        "failed_checks": failed,
        "mechanism_gate_passed": not failed,
        "fresh_disjoint_quality_gate_design_authorized": not failed,
        "model_or_evaluator_on_this_population_authorized": False,
        "deepwidebench_dev64_exact220_or_sota": False,
    }


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    expected = {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "wall_seconds",
        "task_rows_sha256",
        "aggregate",
        "mechanism_decision",
        "mapping_gold_category_question_type_split_evaluator_score_reward_read",
        "model_search_or_evaluator_called",
        "retry_resume_population_replacement_or_selective_rerun",
        "authorization",
        "result_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25061_docsrs_late_record_forward_result"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or not isinstance(copied.get("wall_seconds"), (int, float))
        or copied["wall_seconds"] < 0
        or mechanism_decision(copied.get("aggregate") or {})
        != copied.get("mechanism_decision")
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read"
        )
        is not False
        or copied.get("model_search_or_evaluator_called") is not False
        or copied.get("retry_resume_population_replacement_or_selective_rerun")
        is not False
        or copied.get("authorization")
        != {
            "forward_audit_after_clean_pushed_result": True,
            "model_or_evaluator_on_this_population": False,
            "deepwidebench_dev64_exact220_or_sota": False,
        }
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.50.61 forward result drifted")
    return copied


def run_forward() -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    start = _validate_start(protocol)
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (contract.FORWARD_RESULT, contract.FORWARD_AUDIT, contract.OUTPUT_ROOT)
    ):
        raise RuntimeError("V2.50.61 forward surface is not pristine")
    if contract.watcher_snapshot() != protocol["protected_watchers"]:
        raise RuntimeError("V2.50.61 protected watcher drifted before forward")
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=contract.FETCH_WORKERS) as executor:
        rows = list(executor.map(_fetch_one, range(contract.TASK_COUNT)))
    rows = [validate_task_row(row) for row in rows]
    summary = aggregate(rows)
    decision = mechanism_decision(summary)
    _publish_jsonl(ROOT / contract.TASK_ROWS, rows)
    value = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25061_docsrs_late_record_forward_result",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "wall_seconds": round(time.monotonic() - started, 6),
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "aggregate": summary,
            "mechanism_decision": decision,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "model_search_or_evaluator_called": False,
            "retry_resume_population_replacement_or_selective_rerun": False,
            "authorization": {
                "forward_audit_after_clean_pushed_result": True,
                "model_or_evaluator_on_this_population": False,
                "deepwidebench_dev64_exact220_or_sota": False,
            },
        },
        "result_payload_sha256",
    )
    if contract.watcher_snapshot() != protocol["protected_watchers"]:
        raise RuntimeError("V2.50.61 protected watcher drifted after forward")
    _publish(ROOT / contract.FORWARD_RESULT, validate_forward_result(value))
    return value


def main() -> None:
    value = run_forward()
    print(
        json.dumps(
            {
                "tasks": value["aggregate"]["task_count"],
                "fetch_successes": value["aggregate"]["fetch_successes"],
                "mechanism_exposed_pages": value["aggregate"][
                    "mechanism_exposed_pages"
                ],
                "mechanism_gate_passed": value["mechanism_decision"][
                    "mechanism_gate_passed"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
