"""Content-free subprocess parent gate for V2.48.75 child bundles."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .v24263_global_model_limiter import payload_sha256
from .v24308_child_exit_observability import TAXONOMY, validate_parent_receipt
from .v24309_runner_exit_integration import (
    ObservedChildOutcome,
    run_observed_subprocess,
)
from .v24312_deadline_reliability import validate_receipt as validate_slot
from .v24316_deadline_search import validate_transport_health
from .v24874_keyless_coverage_bundle import (
    BUNDLE_NAME,
    DATA_NAMES,
    FINAL_MODEL_NAME,
    RESULT_NAME,
    TRANSPORT_NAME,
    validate_bundle,
)
from .v24875_keyless_coverage_child_runtime import TERMINAL_NAME


POLICY_ID = "v24876_keyless_coverage_subprocess_bundle_gate_v1"
PARENT_ROLE = "v24876_keyless_coverage_parent_bundle_receipt"
BASE_PARENT_NAME = "base_parent_exit_receipt.json"
PARENT_NAME = "keyless_coverage_parent_bundle_receipt.json"
DISPOSITIONS = frozenset(
    {
        "success",
        "hard_deadline_timeout",
        "parent_subprocess_exception",
        "child_nonzero",
        "bundle_missing_or_invalid",
    }
)


def _ordinary_directory(directory: Path, output_root: Path) -> Path:
    root = output_root.resolve()
    target = directory.resolve()
    if (
        output_root.is_symlink()
        or not output_root.is_dir()
        or directory.is_symlink()
        or not directory.is_dir()
        or not target.is_relative_to(root)
    ):
        raise ValueError("V2.48.76 task directory escaped output root")
    return target


def _ordinary_file(path: Path, directory: Path) -> Path:
    target = path.resolve(strict=False)
    if (
        path.parent != directory
        or path.is_symlink()
        or not path.is_file()
        or not target.is_relative_to(directory)
    ):
        raise ValueError("V2.48.76 expected an ordinary parent artifact")
    return target


def _read(path: Path, directory: Path) -> dict[str, Any]:
    value = json.loads(_ordinary_file(path, directory).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("V2.48.76 expected an object artifact")
    return value


def _sha256(path: Path, directory: Path) -> str:
    return hashlib.sha256(_ordinary_file(path, directory).read_bytes()).hexdigest()


def _atomic_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _disposition(base_taxonomy: str, bundle_valid: bool) -> str:
    if base_taxonomy == "success" and bundle_valid:
        return "success"
    if base_taxonomy == "hard_deadline_timeout":
        return "hard_deadline_timeout"
    if base_taxonomy == "parent_subprocess_exception":
        return "parent_subprocess_exception"
    if base_taxonomy.startswith("child_nonzero"):
        return "child_nonzero"
    return "bundle_missing_or_invalid"


def build_parent_receipt(
    *, base_parent_receipt: Mapping[str, Any], base_parent_sha256: str,
    bundle_commit_marker_present: bool, bundle_valid: bool,
    data_artifact_count_present: int,
) -> dict[str, Any]:
    base = validate_parent_receipt(base_parent_receipt)
    taxonomy = str(base["failure_taxonomy"])
    value = {
        "artifact_version": 1,
        "role": PARENT_ROLE,
        "policy_id": POLICY_ID,
        "base_parent_exit_receipt_sha256": str(base_parent_sha256),
        "base_failure_taxonomy": taxonomy,
        "return_code": base["return_code"],
        "timed_out": bool(base["timed_out"]),
        "subprocess_exception": bool(base["subprocess_exception"]),
        "child_terminal_receipt_present": bool(base["child_terminal_receipt_present"]),
        "child_terminal_receipt_valid": bool(base["child_terminal_receipt_valid"]),
        "bundle_commit_marker_present": bool(bundle_commit_marker_present),
        "bundle_valid": bool(bundle_valid),
        "expected_data_artifact_count": len(DATA_NAMES),
        "data_artifact_count_present": int(data_artifact_count_present),
        "disposition": _disposition(taxonomy, bundle_valid),
        "result_envelope_cannot_substitute_for_bundle_commit_marker": True,
        "contains_question_opaque_id_prompt_response_prediction_url_page_candidate_value_credential_or_answer": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "network_model_search_fetch_or_evaluator_effect_by_parent_receipt_builder": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_parent_bundle_receipt(value)


def validate_parent_bundle_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    expected = {
        "artifact_version", "role", "policy_id", "base_parent_exit_receipt_sha256",
        "base_failure_taxonomy", "return_code", "timed_out", "subprocess_exception",
        "child_terminal_receipt_present", "child_terminal_receipt_valid",
        "bundle_commit_marker_present", "bundle_valid", "expected_data_artifact_count",
        "data_artifact_count_present", "disposition",
        "result_envelope_cannot_substitute_for_bundle_commit_marker",
        "contains_question_opaque_id_prompt_response_prediction_url_page_candidate_value_credential_or_answer",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "network_model_search_fetch_or_evaluator_effect_by_parent_receipt_builder",
        "benchmark_launch_or_evaluator_authorized", "receipt_payload_sha256",
    }
    code = copied.get("return_code")
    count = copied.get("data_artifact_count_present")
    bools = (
        "timed_out", "subprocess_exception", "child_terminal_receipt_present",
        "child_terminal_receipt_valid", "bundle_commit_marker_present", "bundle_valid",
    )
    if (
        set(copied) != expected or copied.get("artifact_version") != 1
        or copied.get("role") != PARENT_ROLE or copied.get("policy_id") != POLICY_ID
        or not isinstance(copied.get("base_parent_exit_receipt_sha256"), str)
        or len(copied["base_parent_exit_receipt_sha256"]) != 64
        or copied.get("base_failure_taxonomy") not in TAXONOMY
        or code is not None and (isinstance(code, bool) or not isinstance(code, int))
        or any(not isinstance(copied.get(name), bool) for name in bools)
        or isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= len(DATA_NAMES)
        or copied.get("expected_data_artifact_count") != len(DATA_NAMES)
        or copied.get("disposition") not in DISPOSITIONS
        or copied.get("result_envelope_cannot_substitute_for_bundle_commit_marker") is not True
        or copied.get("contains_question_opaque_id_prompt_response_prediction_url_page_candidate_value_credential_or_answer") is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or copied.get("network_model_search_fetch_or_evaluator_effect_by_parent_receipt_builder") is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
        or copied["child_terminal_receipt_valid"] and not copied["child_terminal_receipt_present"]
        or copied["bundle_valid"] and (
            not copied["bundle_commit_marker_present"]
            or copied["data_artifact_count_present"] != len(DATA_NAMES)
        )
        or copied["disposition"] != _disposition(str(copied["base_failure_taxonomy"]), copied["bundle_valid"])
        or copied["disposition"] == "success" and (
            code != 0 or copied["timed_out"] or copied["subprocess_exception"]
            or not copied["child_terminal_receipt_valid"]
        )
    ):
        raise ValueError("V2.48.76 parent bundle receipt drifted")
    return copied


def run_observed_bundle_subprocess(
    *, cwd: Path, output_root: Path, directory: Path, command: Sequence[str],
    environment: Mapping[str, str], timeout_seconds: float,
    expected_model_slot_cap: int, popen: Any = subprocess.Popen,
) -> tuple[ObservedChildOutcome, dict[str, Any]]:
    task_directory = _ordinary_directory(directory, output_root)
    for name in (BASE_PARENT_NAME, PARENT_NAME):
        if (task_directory / name).exists() or (task_directory / name).is_symlink():
            raise FileExistsError("V2.48.76 parent surface is not pristine")

    def bundle_validator(_value: Mapping[str, Any]) -> object:
        return validate_bundle(
            output_root=output_root, directory=task_directory,
            expected_model_slot_cap=expected_model_slot_cap,
        )

    observed = run_observed_subprocess(
        cwd=cwd, output_root=output_root, directory=task_directory,
        command=command, environment=environment, timeout_seconds=timeout_seconds,
        result_validator=bundle_validator,
        model_receipt_validator=lambda value: validate_slot(value, expected_cap=expected_model_slot_cap),
        transport_receipt_validator=validate_transport_health,
        result_name=RESULT_NAME, model_receipt_name=FINAL_MODEL_NAME,
        transport_receipt_name=TRANSPORT_NAME, terminal_name=TERMINAL_NAME,
        parent_name=BASE_PARENT_NAME, popen=popen,
    )
    base_path = task_directory / BASE_PARENT_NAME
    base = _read(base_path, task_directory)
    validate_parent_receipt(base)
    marker = task_directory / BUNDLE_NAME
    marker_present = marker.is_file() and not marker.is_symlink()
    count = sum((task_directory / name).is_file() and not (task_directory / name).is_symlink() for name in DATA_NAMES)
    bundle_valid = False
    try:
        validate_bundle(output_root=output_root, directory=task_directory, expected_model_slot_cap=expected_model_slot_cap)
        bundle_valid = True
    except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        bundle_valid = False
    receipt = build_parent_receipt(
        base_parent_receipt=base, base_parent_sha256=_sha256(base_path, task_directory),
        bundle_commit_marker_present=marker_present, bundle_valid=bundle_valid,
        data_artifact_count_present=count,
    )
    _atomic_new(task_directory / PARENT_NAME, receipt)
    return observed, receipt


__all__ = [
    "BASE_PARENT_NAME", "DISPOSITIONS", "PARENT_NAME", "PARENT_ROLE", "POLICY_ID",
    "build_parent_receipt", "run_observed_bundle_subprocess", "validate_parent_bundle_receipt",
]
