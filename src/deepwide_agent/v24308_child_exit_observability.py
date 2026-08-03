"""Content-free child/parent exit receipts for future DeepWide executors."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any


CHILD_ROLE = "v24308_content_free_child_terminal_receipt"
PARENT_ROLE = "v24308_content_free_parent_exit_receipt"
CHILD_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "stage",
        "exception_type",
        "model_receipt_written",
        "transport_receipt_written",
        "result_envelope_written",
        "contains_question_opaque_id_prompt_response_prediction_url_page_credential_gold_category_or_answer",
        "mapping_gold_category_question_type_split_evaluator_score_read",
        "network_model_search_fetch_or_evaluator_called_by_receipt_builder",
        "receipt_payload_sha256",
    }
)
PARENT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "return_code",
        "timed_out",
        "elapsed_seconds",
        "subprocess_exception",
        "child_terminal_receipt_present",
        "child_terminal_receipt_valid",
        "result_envelope_present",
        "result_envelope_valid",
        "model_receipt_present",
        "model_receipt_valid",
        "transport_receipt_present",
        "transport_receipt_valid",
        "failure_taxonomy",
        "contains_question_opaque_id_prompt_response_prediction_url_page_credential_gold_category_or_answer",
        "mapping_gold_category_question_type_split_evaluator_score_read",
        "network_model_search_fetch_or_evaluator_called_by_receipt_builder",
        "receipt_payload_sha256",
    }
)
CHILD_STAGES = frozenset(
    {
        "validated_visible_input",
        "model_client_constructed",
        "search_client_constructed",
        "runtime_entered",
        "runtime_returned",
        "model_receipt_written",
        "transport_receipt_written",
        "result_envelope_written",
        "child_exception",
    }
)
TAXONOMY = frozenset(
    {
        "success",
        "hard_deadline_timeout",
        "child_nonzero_with_terminal_receipt",
        "child_nonzero_without_terminal_receipt",
        "zero_exit_missing_result_envelope",
        "result_envelope_invalid",
        "model_receipt_missing_or_invalid",
        "transport_receipt_missing_or_invalid",
        "parent_subprocess_exception",
    }
)
COARSE_EXCEPTION_TYPES = frozenset(
    {
        "SyntheticChildError",
        "ModelRequestError",
        "TimeoutError",
        "ValidationError",
        "SerializationError",
        "SubprocessError",
        "RuntimeError",
        "OSError",
        "UnknownError",
    }
)
PROHIBITED = (
    "benchmark",
    "question",
    "question_type",
    "task_category",
    "opaque_id",
    "prompt",
    "response",
    "prediction",
    "url",
    "page",
    "credential",
    "mapping",
    "gold",
    "category",
    "answer",
    "split",
    "evaluator",
    "score",
)
def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def coarse_exception_type(error: BaseException) -> str:
    """Map an exception to a fixed content-free class without reading its message."""

    name = type(error).__name__
    if name in COARSE_EXCEPTION_TYPES:
        return name
    folded = name.casefold()
    if isinstance(error, TimeoutError) or "timeout" in folded:
        return "TimeoutError"
    if "model" in folded and "request" in folded:
        return "ModelRequestError"
    if "json" in folded or "serial" in folded or "decode" in folded:
        return "SerializationError"
    if "subprocess" in folded or "process" in folded:
        return "SubprocessError"
    if isinstance(error, OSError):
        return "OSError"
    if isinstance(error, (TypeError, ValueError)) or "valid" in folded:
        return "ValidationError"
    return "UnknownError"


def child_receipt(
    *,
    stage: str,
    exception_type: str | None,
    model_receipt_written: bool,
    transport_receipt_written: bool,
    result_envelope_written: bool,
) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": CHILD_ROLE,
        "stage": stage,
        "exception_type": exception_type,
        "model_receipt_written": model_receipt_written,
        "transport_receipt_written": transport_receipt_written,
        "result_envelope_written": result_envelope_written,
        "contains_question_opaque_id_prompt_response_prediction_url_page_credential_gold_category_or_answer": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "network_model_search_fetch_or_evaluator_called_by_receipt_builder": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    validate_child_receipt(value)
    return value


def validate_child_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    if (
        set(value) != CHILD_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != CHILD_ROLE
        or value.get("stage") not in CHILD_STAGES
        or value.get("exception_type") is not None
        and value.get("exception_type") not in COARSE_EXCEPTION_TYPES
        or any(
            not isinstance(value.get(name), bool)
            for name in (
                "model_receipt_written",
                "transport_receipt_written",
                "result_envelope_written",
            )
        )
        or value.get(
            "contains_question_opaque_id_prompt_response_prediction_url_page_credential_gold_category_or_answer"
        )
        is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
        or value.get("network_model_search_fetch_or_evaluator_called_by_receipt_builder")
        is not False
        or not _sealed(value, "receipt_payload_sha256")
    ):
        raise ValueError("V2.43.08 child receipt drifted")
    encoded = json.dumps(value, ensure_ascii=False).casefold()
    if any(f'"{name}"' in encoded for name in PROHIBITED):
        raise ValueError("V2.43.08 child receipt contains prohibited field")
    return dict(value)


def classify_parent_exit(
    *,
    return_code: int | None,
    timed_out: bool,
    subprocess_exception: bool,
    child_terminal_receipt_present: bool,
    child_terminal_receipt_valid: bool,
    result_envelope_present: bool,
    result_envelope_valid: bool,
    model_receipt_present: bool,
    model_receipt_valid: bool,
    transport_receipt_present: bool,
    transport_receipt_valid: bool,
) -> str:
    if subprocess_exception:
        return "parent_subprocess_exception"
    if timed_out:
        return "hard_deadline_timeout"
    if return_code is None or return_code != 0:
        return (
            "child_nonzero_with_terminal_receipt"
            if child_terminal_receipt_present and child_terminal_receipt_valid
            else "child_nonzero_without_terminal_receipt"
        )
    if not result_envelope_present:
        return "zero_exit_missing_result_envelope"
    if not result_envelope_valid:
        return "result_envelope_invalid"
    if not model_receipt_present or not model_receipt_valid:
        return "model_receipt_missing_or_invalid"
    if not transport_receipt_present or not transport_receipt_valid:
        return "transport_receipt_missing_or_invalid"
    return "success"


def parent_receipt(
    *,
    return_code: int | None,
    timed_out: bool,
    elapsed_seconds: float,
    subprocess_exception: bool,
    child_terminal_receipt_present: bool,
    child_terminal_receipt_valid: bool,
    result_envelope_present: bool,
    result_envelope_valid: bool,
    model_receipt_present: bool,
    model_receipt_valid: bool,
    transport_receipt_present: bool,
    transport_receipt_valid: bool,
) -> dict[str, Any]:
    taxonomy = classify_parent_exit(
        return_code=return_code,
        timed_out=timed_out,
        subprocess_exception=subprocess_exception,
        child_terminal_receipt_present=child_terminal_receipt_present,
        child_terminal_receipt_valid=child_terminal_receipt_valid,
        result_envelope_present=result_envelope_present,
        result_envelope_valid=result_envelope_valid,
        model_receipt_present=model_receipt_present,
        model_receipt_valid=model_receipt_valid,
        transport_receipt_present=transport_receipt_present,
        transport_receipt_valid=transport_receipt_valid,
    )
    value = {
        "artifact_version": 1,
        "role": PARENT_ROLE,
        "return_code": return_code,
        "timed_out": timed_out,
        "elapsed_seconds": round(float(elapsed_seconds), 6),
        "subprocess_exception": subprocess_exception,
        "child_terminal_receipt_present": child_terminal_receipt_present,
        "child_terminal_receipt_valid": child_terminal_receipt_valid,
        "result_envelope_present": result_envelope_present,
        "result_envelope_valid": result_envelope_valid,
        "model_receipt_present": model_receipt_present,
        "model_receipt_valid": model_receipt_valid,
        "transport_receipt_present": transport_receipt_present,
        "transport_receipt_valid": transport_receipt_valid,
        "failure_taxonomy": taxonomy,
        "contains_question_opaque_id_prompt_response_prediction_url_page_credential_gold_category_or_answer": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "network_model_search_fetch_or_evaluator_called_by_receipt_builder": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    validate_parent_receipt(value)
    return value


def validate_parent_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    elapsed = value.get("elapsed_seconds")
    return_code = value.get("return_code")
    bools = (
        "timed_out",
        "subprocess_exception",
        "child_terminal_receipt_present",
        "child_terminal_receipt_valid",
        "result_envelope_present",
        "result_envelope_valid",
        "model_receipt_present",
        "model_receipt_valid",
        "transport_receipt_present",
        "transport_receipt_valid",
    )
    presence_validity_pairs = (
        ("child_terminal_receipt_present", "child_terminal_receipt_valid"),
        ("result_envelope_present", "result_envelope_valid"),
        ("model_receipt_present", "model_receipt_valid"),
        ("transport_receipt_present", "transport_receipt_valid"),
    )
    if (
        set(value) != PARENT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != PARENT_ROLE
        or return_code is not None
        and (isinstance(return_code, bool) or not isinstance(return_code, int))
        or isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not math.isfinite(float(elapsed))
        or float(elapsed) < 0
        or any(not isinstance(value.get(name), bool) for name in bools)
        or any(
            value.get(valid) is True and value.get(present) is not True
            for present, valid in presence_validity_pairs
        )
        or value.get("subprocess_exception") is True
        and (
            return_code is not None
            or value.get("timed_out") is True
        )
        or value.get("subprocess_exception") is False
        and value.get("timed_out") is False
        and return_code is None
        or value.get("failure_taxonomy") not in TAXONOMY
        or value.get(
            "contains_question_opaque_id_prompt_response_prediction_url_page_credential_gold_category_or_answer"
        )
        is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
        or value.get("network_model_search_fetch_or_evaluator_called_by_receipt_builder")
        is not False
        or not _sealed(value, "receipt_payload_sha256")
    ):
        raise ValueError("V2.43.08 parent receipt drifted")
    expected = classify_parent_exit(
        return_code=return_code,
        timed_out=value["timed_out"],
        subprocess_exception=value["subprocess_exception"],
        child_terminal_receipt_present=value["child_terminal_receipt_present"],
        child_terminal_receipt_valid=value["child_terminal_receipt_valid"],
        result_envelope_present=value["result_envelope_present"],
        result_envelope_valid=value["result_envelope_valid"],
        model_receipt_present=value["model_receipt_present"],
        model_receipt_valid=value["model_receipt_valid"],
        transport_receipt_present=value["transport_receipt_present"],
        transport_receipt_valid=value["transport_receipt_valid"],
    )
    if value["failure_taxonomy"] != expected:
        raise ValueError("V2.43.08 parent receipt taxonomy drifted")
    encoded = json.dumps(value, ensure_ascii=False).casefold()
    if any(f'"{name}"' in encoded for name in PROHIBITED):
        raise ValueError("V2.43.08 parent receipt contains prohibited field")
    return dict(value)


__all__ = [
    "CHILD_KEYS",
    "CHILD_ROLE",
    "COARSE_EXCEPTION_TYPES",
    "PARENT_KEYS",
    "PARENT_ROLE",
    "TAXONOMY",
    "child_receipt",
    "classify_parent_exit",
    "coarse_exception_type",
    "parent_receipt",
    "payload_sha256",
    "validate_child_receipt",
    "validate_parent_receipt",
]
