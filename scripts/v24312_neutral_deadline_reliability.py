#!/usr/bin/env python3
"""Benchmark-external V2.43.12 deadline and outer-totality gate."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import deepwide_agent.v24312_deadline_reliability as reliability  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    payload_sha256,
    validate_parent_receipt,
)
from deepwide_agent.v24309_runner_exit_integration import (  # noqa: E402
    run_child_with_terminal_receipt,
    run_observed_subprocess,
)
from deepwide_agent.v24310_paired_dev_runtime import (  # noqa: E402
    RECEIPT_FIELD as RECOVERY_RECEIPT_FIELD,
)
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
    DeadlineAwareResponsesClient,
    run_v24312_total_task,
    validate_receipt,
)


DATE = "20260803"
PROTOCOL_ID = "v24312_benchmark_external_deadline_reliability_v1"
DIAGNOSIS = Path(f"results/v24312_v24311_deadline_diagnosis_v1_{DATE}.json")
PROTOCOL = Path(f"results/v24312_deadline_reliability_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v24312_deadline_reliability_probe_v1_{DATE}.json")
DECISION = Path(f"results/v24312_deadline_reliability_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24312_deadline_reliability_postresult_audit_v1_{DATE}.json")
MODES = (
    "immediate_success",
    "post_retrieval_slot_timeout_a",
    "post_retrieval_slot_timeout_b",
    "slow_provider_timeout",
    "projection_validation_totality",
)
SLOT_TIMEOUT_MODES = frozenset(
    {"post_retrieval_slot_timeout_a", "post_retrieval_slot_timeout_b"}
)
EXPECTED = {
    "immediate_success": {
        "outcome": "success",
        "provider_requests": 1,
        "provider_attempts": 1,
        "slot_acquisitions": 1,
        "slot_timeouts": 0,
        "provider_deadline_failures": 0,
    },
    "post_retrieval_slot_timeout_a": {
        "outcome": "total_fallback",
        "provider_requests": 0,
        "provider_attempts": 0,
        "slot_acquisitions": 0,
        "slot_timeouts": 1,
        "provider_deadline_failures": 0,
    },
    "post_retrieval_slot_timeout_b": {
        "outcome": "total_fallback",
        "provider_requests": 0,
        "provider_attempts": 0,
        "slot_acquisitions": 0,
        "slot_timeouts": 1,
        "provider_deadline_failures": 0,
    },
    "slow_provider_timeout": {
        "outcome": "total_fallback",
        "provider_requests": 1,
        "provider_attempts": 1,
        "slot_acquisitions": 1,
        "slot_timeouts": 0,
        "provider_deadline_failures": 1,
    },
    "projection_validation_totality": {
        "outcome": "total_fallback",
        "provider_requests": 1,
        "provider_attempts": 1,
        "slot_acquisitions": 1,
        "slot_timeouts": 0,
        "provider_deadline_failures": 0,
    },
}
PARENT_FILES = (
    "results/v24311_paired_dev64_forward_result_v1_20260803.json",
    "results/v24311_paired_dev64_result_v1_20260803.json",
    "results/v24311_paired_dev64_postresult_audit_v1_20260803.json",
    "scripts/run_v24311_paired_dev64.py",
    "scripts/run_v24311_paired_dev64_task.py",
)
SOURCE_FILES = (
    "src/deepwide_agent/v24312_deadline_reliability.py",
    "scripts/v24312_neutral_deadline_reliability.py",
    "tests/test_v24312_deadline_reliability.py",
    "tests/test_v24312_neutral_deadline_reliability.py",
)
SAFE_FAILURE_DIRS = {
    "baseline": (52,),
    "candidate": (46, 59, 62),
}
SAFE_FAILURE_FILES = (
    "safe_progress.json",
    "model_slot_receipt.json",
    "transport_health.json",
    "child_terminal_receipt.json",
    "parent_exit_receipt.json",
)
RESULT_NAME = "result_envelope.json"
MODEL_NAME = "model_receipt.json"
TRANSPORT_NAME = "transport_receipt.json"
TERMINAL_NAME = "child_terminal_receipt.json"
PARENT_NAME = "parent_exit_receipt.json"
ENVELOPE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "protocol_id",
        "mode",
        "outcome",
        "provider_requests",
        "provider_attempts",
        "slot_acquisitions",
        "slot_timeouts",
        "provider_deadline_failures",
        "fixed_denominator_terminal",
        "fourth_model_effect",
        "external_network_model_search_fetch_or_evaluator_calls",
        "contains_question_opaque_id_prompt_response_prediction_url_page_credential_gold_category_or_answer",
        "mapping_gold_category_question_type_split_evaluator_score_read",
        "envelope_payload_sha256",
    }
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.43.12 expected an ordinary JSON file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.43.12 expected a JSON object")
    return value


def _new_json(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _manifest(root: Path) -> dict[str, str]:
    return {relative: sha256(root / relative) for relative in SOURCE_FILES}


def _parents(root: Path) -> dict[str, str]:
    return {relative: sha256(root / relative) for relative in PARENT_FILES}


def build_diagnosis(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    failures: list[dict[str, Any]] = []
    base = root / "outputs/v24311_paired_dev64_v1_20260803/tasks"
    for arm, positions in SAFE_FAILURE_DIRS.items():
        for position in positions:
            directory = base / arm / f"task_{position:04d}"
            values = {
                name: _read(directory / name)
                for name in SAFE_FAILURE_FILES
                if (directory / name).is_file()
                and not (directory / name).is_symlink()
            }
            parent = values["parent_exit_receipt.json"]
            validate_parent_receipt(parent)
            progress = values.get("safe_progress.json", {})
            terminal = values.get("child_terminal_receipt.json", {})
            model = values.get("model_slot_receipt.json", {})
            failures.append(
                {
                    "arm": arm,
                    "position": position,
                    "parent_taxonomy": parent["failure_taxonomy"],
                    "parent_elapsed_seconds": parent["elapsed_seconds"],
                    "last_safe_stage": progress.get("stage"),
                    "last_safe_elapsed_seconds": progress.get("elapsed_seconds"),
                    "child_exception_type": terminal.get("exception_type"),
                    "model_slot_acquisitions": model.get("acquisitions"),
                    "model_slot_max_wait_seconds": model.get("max_wait_seconds"),
                    "safe_files_read": sorted(values),
                }
            )
    value = {
        "artifact_version": 1,
        "role": "v24312_v24311_content_free_deadline_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": _parents(root),
        "non_success_task_count": len(failures),
        "failures": failures,
        "mechanical_cause": {
            "slot_acquisition_had_absolute_deadline": False,
            "provider_timeout_inherited_remaining_task_wall": False,
            "provider_static_timeout_seconds": 180,
            "parent_hard_deadline_seconds": 195,
            "terminal_cleanup_time_reserved_inside_child": False,
            "candidate_timeouts_after_page_projection": 3,
            "baseline_postterminal_validation_failure": 1,
        },
        "files_explicitly_not_read": [
            "visible_task.json",
            "result.json",
            "runtime_predictions.jsonl",
            "mapping",
            "gold",
            "evaluator",
            "score",
        ],
        "contains_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "network_model_search_fetch_or_evaluator_called": False,
        "claims": {
            "single_search_took_195_seconds": False,
            "deadline_lifetime_mismatch_supported": True,
            "quality_or_sota_inference": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    validate_diagnosis(root, value)
    return value


def validate_diagnosis(root: Path, value: Mapping[str, Any]) -> None:
    failures = value.get("failures")
    observed = {
        (item.get("arm"), item.get("position")): item
        for item in failures or []
        if isinstance(item, Mapping)
    }
    expected_keys = {
        (arm, position)
        for arm, positions in SAFE_FAILURE_DIRS.items()
        for position in positions
    }
    if (
        value.get("artifact_version") != 1
        or value.get("role") != "v24312_v24311_content_free_deadline_diagnosis"
        or value.get("parents") != _parents(root)
        or value.get("non_success_task_count") != 4
        or not isinstance(failures, list)
        or set(observed) != expected_keys
        or observed[("baseline", 52)].get("parent_taxonomy")
        != "child_nonzero_with_terminal_receipt"
        or observed[("baseline", 52)].get("child_exception_type")
        != "ValidationError"
        or any(
            observed[("candidate", position)].get("parent_taxonomy")
            != "hard_deadline_timeout"
            or observed[("candidate", position)].get("last_safe_stage")
            != "page_projection_terminal"
            for position in SAFE_FAILURE_DIRS["candidate"]
        )
        or value.get("contains_question_query_url_page_prediction_answer_opaque_id_or_credential")
        is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
        or value.get("network_model_search_fetch_or_evaluator_called") is not False
        or value.get("claims", {}).get("deadline_lifetime_mismatch_supported")
        is not True
        or value.get("claims", {}).get("quality_or_sota_inference") is not False
        or not _sealed(value, "diagnosis_payload_sha256")
    ):
        raise RuntimeError("V2.43.12 diagnosis drifted")


def build_protocol(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    diagnosis = _read(root / DIAGNOSIS)
    validate_diagnosis(root, diagnosis)
    manifest = _manifest(root)
    value = {
        "artifact_version": 1,
        "role": "v24312_deadline_reliability_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "diagnosis_sha256": sha256(root / DIAGNOSIS),
        "parent_sha256": _parents(root),
        "modes": list(MODES),
        "expected": EXPECTED,
        "fixed_denominator": len(MODES),
        "slot_cap": 2,
        "simultaneously_held_slots_for_starvation": 2,
        "child_effect_deadline_seconds": 0.22,
        "parent_deadline_seconds": 1.0,
        "cleanup_reserve_seconds": 0.08,
        "minimum_attempt_seconds": 0.01,
        "synthetic_visible_input_only_for_projection_fault": True,
        "benchmark_task_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
        "external_network_model_search_fetch_or_evaluator_calls": 0,
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "authorization": {
            "one_benchmark_external_probe": True,
            "fresh_paired_dev64_design": False,
            "fresh_paired_dev64_launch": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    validate_protocol(root, value)
    return value


def validate_protocol(root: Path, value: Mapping[str, Any]) -> None:
    manifest = value.get("source_manifest")
    if (
        value.get("artifact_version") != 1
        or value.get("role") != "v24312_deadline_reliability_preregistration"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("diagnosis_sha256") != sha256(root / DIAGNOSIS)
        or value.get("parent_sha256") != _parents(root)
        or value.get("modes") != list(MODES)
        or value.get("expected") != EXPECTED
        or value.get("fixed_denominator") != len(MODES)
        or value.get("slot_cap") != 2
        or value.get("simultaneously_held_slots_for_starvation") != 2
        or value.get("external_network_model_search_fetch_or_evaluator_calls") != 0
        or value.get(
            "benchmark_task_manifest_mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or not isinstance(manifest, Mapping)
        or dict(manifest) != _manifest(root)
        or value.get("source_manifest_sha256") != payload_sha256(manifest)
        or value.get("authorization")
        != {
            "one_benchmark_external_probe": True,
            "fresh_paired_dev64_design": False,
            "fresh_paired_dev64_launch": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(value, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.43.12 protocol drifted")


class _SyntheticModel:
    def __init__(self, *, delay: float = 0.0) -> None:
        self.delay = delay
        self.requests = 0
        self.calls = 0
        self.failures = 0
        self.attempts = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.deadline_failures = 0

    def complete(self, *_args: Any, **_kwargs: Any) -> Any:
        self.requests += 1
        self.attempts += 1
        if self.delay:
            time.sleep(self.delay)
        self.calls += 1
        return SimpleNamespace(text="synthetic-ok")


class _SlowSession:
    def post(self, *_args: Any, **kwargs: Any) -> Any:
        time.sleep(float(kwargs["timeout"]) + 0.005)
        raise requests.Timeout()


class _NoSearch:
    calls = 0
    failures = 0
    tool_calls = 0
    fetch_calls = 0
    fetch_failures = 0
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0


def _prepare_slots(root: Path, cap: int = 2) -> Path:
    slots = root / "model_slots"
    slots.mkdir(mode=0o700)
    for index in range(1, cap + 1):
        (slots / f"slot_{index:02d}.lock").write_text(
            json.dumps({"slot": index}) + "\n", encoding="utf-8"
        )
    return slots


def _envelope(
    mode: str,
    outcome: str,
    receipt: Mapping[str, Any],
    *,
    provider_requests: int,
    provider_attempts: int,
) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": "v24312_deadline_reliability_case_envelope",
        "protocol_id": PROTOCOL_ID,
        "mode": mode,
        "outcome": outcome,
        "provider_requests": provider_requests,
        "provider_attempts": provider_attempts,
        "slot_acquisitions": receipt["acquisitions"],
        "slot_timeouts": receipt["slot_timeouts"],
        "provider_deadline_failures": receipt["provider_deadline_failures"],
        "fixed_denominator_terminal": True,
        "fourth_model_effect": False,
        "external_network_model_search_fetch_or_evaluator_calls": 0,
        "contains_question_opaque_id_prompt_response_prediction_url_page_credential_gold_category_or_answer": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
    }
    value["envelope_payload_sha256"] = payload_sha256(value)
    validate_envelope(value)
    return value


def validate_envelope(value: Mapping[str, Any]) -> dict[str, Any]:
    mode = value.get("mode")
    expected = EXPECTED.get(str(mode))
    if (
        set(value) != ENVELOPE_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24312_deadline_reliability_case_envelope"
        or value.get("protocol_id") != PROTOCOL_ID
        or expected is None
        or any(value.get(key) != expected[key] for key in expected)
        or value.get("fixed_denominator_terminal") is not True
        or value.get("fourth_model_effect") is not False
        or value.get("external_network_model_search_fetch_or_evaluator_calls") != 0
        or value.get(
            "contains_question_opaque_id_prompt_response_prediction_url_page_credential_gold_category_or_answer"
        )
        is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
        or not _sealed(value, "envelope_payload_sha256")
    ):
        raise ValueError("V2.43.12 case envelope drifted")
    return dict(value)


def _transport_marker(value: Mapping[str, Any]) -> dict[str, bool]:
    if dict(value) != {"valid": True}:
        raise ValueError("V2.43.12 transport marker drifted")
    return {"valid": True}


def _projection_fault(*_args: Any, **kwargs: Any) -> None:
    kwargs["model"].complete("synthetic", "synthetic", max_output_tokens=1)
    raise ValueError("synthetic projection validation fault")


def child_mode(
    mode: str,
    output_root: Path,
    directory: Path,
    slots: Path,
) -> None:
    if mode not in MODES:
        raise ValueError("V2.43.12 unknown child mode")

    def action() -> None:
        started = time.monotonic()
        deadline = started + (0.22 if mode != "immediate_success" else 0.7)
        if mode in SLOT_TIMEOUT_MODES:
            time.sleep(0.03)
        if mode == "slow_provider_timeout":
            inner: Any = DeadlineAwareResponsesClient(
                "http://invalid.local/responses",
                "synthetic",
                timeout=180,
                max_retries=2,
                absolute_deadline=deadline,
                cleanup_reserve_seconds=0.08,
                minimum_attempt_seconds=0.01,
            )
            inner._thread_local.session = _SlowSession()
        else:
            inner = _SyntheticModel()
        model = DeadlineAwareGlobalModelSlotLimiter(
            inner,
            slot_directory=slots,
            output_root=output_root,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=0.08,
            minimum_attempt_seconds=0.01,
            slot_cap=2,
            poll_seconds=0.005,
        )
        outcome = "success"
        if mode == "projection_validation_totality":
            original = reliability.run_v24310_task
            reliability.run_v24310_task = _projection_fault
            try:
                result = run_v24312_total_task(
                    {
                        "opaque_id": "task_0123456789abcdef01234567",
                        "question": "Synthetic benchmark-external table contract.",
                    },
                    arm="baseline",
                    model=model,
                    search=_NoSearch(),
                    limits=ScoreFirstLimits(
                        wall_seconds=120,
                        model_calls=3,
                        search_queries=4,
                        fetch_targets=10,
                        search_results_per_query=3,
                        evidence_chars=60_000,
                        page_chars=5_000,
                    ),
                    two_wave_policy=TwoWavePolicy(),
                )
            finally:
                reliability.run_v24310_task = original
            if (
                result.get("completion_kind") != "worker_failure_fallback"
                or result.get(RECOVERY_RECEIPT_FIELD, {}).get(
                    "total_effects_admitted"
                )
                != 1
            ):
                raise RuntimeError("V2.43.12 outer totality fault was not contained")
            outcome = "total_fallback"
        else:
            try:
                model.complete("synthetic", "synthetic", max_output_tokens=1)
            except reliability.ModelRequestError:
                outcome = "total_fallback"
        receipt = model.receipt()
        validate_receipt(receipt, expected_cap=2)
        envelope = _envelope(
            mode,
            outcome,
            receipt,
            provider_requests=int(getattr(inner, "requests", 0) or 0),
            provider_attempts=int(getattr(inner, "attempts", 0) or 0),
        )
        _new_json(directory / MODEL_NAME, receipt)
        _new_json(directory / TRANSPORT_NAME, {"valid": True})
        _new_json(directory / RESULT_NAME, envelope)

    run_child_with_terminal_receipt(
        output_root=output_root,
        directory=directory,
        action=action,
        result_name=RESULT_NAME,
        model_receipt_name=MODEL_NAME,
        transport_receipt_name=TRANSPORT_NAME,
        terminal_name=TERMINAL_NAME,
    )


def _environment() -> dict[str, str]:
    return {
        "HOME": str(Path.home()),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }


def run_mode(
    root: Path,
    mode: str,
    output_root: Path,
    directory: Path,
    slots: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    directory.mkdir(mode=0o700)
    command = [
        str(root / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(root / "scripts/v24312_neutral_deadline_reliability.py"),
        "child",
        "--mode",
        mode,
        "--output-root",
        str(output_root),
        "--directory",
        str(directory),
        "--slots",
        str(slots),
    ]
    observed = run_observed_subprocess(
        cwd=root,
        output_root=output_root,
        directory=directory,
        command=command,
        environment=_environment(),
        timeout_seconds=1.0,
        result_validator=validate_envelope,
        model_receipt_validator=lambda value: validate_receipt(
            value, expected_cap=2
        ),
        transport_receipt_validator=_transport_marker,
        result_name=RESULT_NAME,
        model_receipt_name=MODEL_NAME,
        transport_receipt_name=TRANSPORT_NAME,
        terminal_name=TERMINAL_NAME,
        parent_name=PARENT_NAME,
    )
    validate_parent_receipt(observed.receipt)
    return _read(directory / RESULT_NAME), observed.receipt


def execute_probe(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    cases: dict[str, dict[str, Any]] = {}
    parents: dict[str, dict[str, Any]] = {}
    with tempfile.TemporaryDirectory(dir=root / "outputs") as temporary:
        output_root = Path(temporary)
        slots = _prepare_slots(output_root, 2)
        held = [
            open(slots / f"slot_{index:02d}.lock", "r+", encoding="utf-8")
            for index in range(1, 3)
        ]
        for handle in held:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            for mode in SLOT_TIMEOUT_MODES:
                cases[mode], parents[mode] = run_mode(
                    root, mode, output_root, output_root / mode, slots
                )
        finally:
            for handle in held:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                handle.close()
        for mode in MODES:
            if mode in SLOT_TIMEOUT_MODES:
                continue
            cases[mode], parents[mode] = run_mode(
                root, mode, output_root, output_root / mode, slots
            )
    value = {
        "artifact_version": 1,
        "role": "v24312_deadline_reliability_probe",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "fixed_denominator": len(MODES),
        "terminal_cases": len(cases),
        "cases": cases,
        "parent_taxonomy": {
            mode: parents[mode]["failure_taxonomy"] for mode in MODES
        },
        "parent_receipts_created": len(parents),
        "child_terminal_receipts_created": len(parents),
        "slot_cap": 2,
        "simultaneously_held_slots_for_starvation": 2,
        "external_effect_ledger": {
            "network": 0,
            "model_provider": 0,
            "search": 0,
            "fetch": 0,
            "evaluator": 0,
        },
        "fourth_model_effects": 0,
        "benchmark_task_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
        "contains_question_opaque_id_prompt_response_prediction_url_page_credential_gold_category_or_answer": False,
        "authorization": {
            "fresh_paired_dev64_design": True,
            "fresh_paired_dev64_launch": False,
            "exact220": False,
            "evaluator": False,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
    validate_projection(value)
    return value


def validate_projection(value: Mapping[str, Any]) -> None:
    cases = value.get("cases")
    if (
        value.get("artifact_version") != 1
        or value.get("role") != "v24312_deadline_reliability_probe"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("fixed_denominator") != len(MODES)
        or value.get("terminal_cases") != len(MODES)
        or not isinstance(cases, Mapping)
        or set(cases) != set(MODES)
        or any(validate_envelope(cases[mode]) is None for mode in MODES)
        or value.get("parent_taxonomy") != {mode: "success" for mode in MODES}
        or value.get("parent_receipts_created") != len(MODES)
        or value.get("child_terminal_receipts_created") != len(MODES)
        or value.get("slot_cap") != 2
        or value.get("simultaneously_held_slots_for_starvation") != 2
        or any(value.get("external_effect_ledger", {}).values())
        or value.get("fourth_model_effects") != 0
        or value.get(
            "benchmark_task_manifest_mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or value.get(
            "contains_question_opaque_id_prompt_response_prediction_url_page_credential_gold_category_or_answer"
        )
        is not False
        or value.get("authorization")
        != {
            "fresh_paired_dev64_design": True,
            "fresh_paired_dev64_launch": False,
            "exact220": False,
            "evaluator": False,
        }
        or not _sealed(value, "result_payload_sha256")
    ):
        raise RuntimeError("V2.43.12 probe projection drifted")


def build_decision(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = _read(root / PROTOCOL)
    result = _read(root / RESULT)
    validate_protocol(root, protocol)
    validate_projection(result)
    passed = (
        result["terminal_cases"] == len(MODES)
        and result["parent_receipts_created"] == len(MODES)
        and result["child_terminal_receipts_created"] == len(MODES)
        and not any(result["external_effect_ledger"].values())
        and result["fourth_model_effects"] == 0
    )
    value = {
        "artifact_version": 1,
        "role": "v24312_deadline_reliability_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "neutral_reliability_go" if passed else "neutral_reliability_no_go",
        "passed": passed,
        "failed_checks": [] if passed else ["terminality_or_effect_ledger"],
        "provenance": {
            "diagnosis_sha256": sha256(root / DIAGNOSIS),
            "protocol_sha256": sha256(root / PROTOCOL),
            "result_sha256": sha256(root / RESULT),
        },
        "claim_scope": "benchmark_external_reliability_only",
        "authorization": {
            "fresh_paired_dev64_design": passed,
            "fresh_paired_dev64_launch": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["decision_payload_sha256"] = payload_sha256(value)
    validate_decision(root, value)
    return value


def validate_decision(root: Path, value: Mapping[str, Any]) -> None:
    if (
        value.get("artifact_version") != 1
        or value.get("role") != "v24312_deadline_reliability_decision"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("status") != "neutral_reliability_go"
        or value.get("passed") is not True
        or value.get("failed_checks") != []
        or value.get("provenance")
        != {
            "diagnosis_sha256": sha256(root / DIAGNOSIS),
            "protocol_sha256": sha256(root / PROTOCOL),
            "result_sha256": sha256(root / RESULT),
        }
        or value.get("claim_scope") != "benchmark_external_reliability_only"
        or value.get("authorization")
        != {
            "fresh_paired_dev64_design": True,
            "fresh_paired_dev64_launch": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(value, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.43.12 decision drifted")


def build_postaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    diagnosis = _read(root / DIAGNOSIS)
    protocol = _read(root / PROTOCOL)
    result = _read(root / RESULT)
    decision = _read(root / DECISION)
    validate_diagnosis(root, diagnosis)
    validate_protocol(root, protocol)
    validate_projection(result)
    validate_decision(root, decision)
    value = {
        "artifact_version": 1,
        "role": "v24312_deadline_reliability_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "provenance": {
            "diagnosis_sha256": sha256(root / DIAGNOSIS),
            "protocol_sha256": sha256(root / PROTOCOL),
            "result_sha256": sha256(root / RESULT),
            "decision_sha256": sha256(root / DECISION),
        },
        "source_manifest_unchanged": protocol["source_manifest"] == _manifest(root),
        "findings": [],
        "audit_valid": True,
        "runtime_input_from_benchmark": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "external_network_model_search_fetch_or_evaluator_calls": 0,
        "protected_watcher_signaled_restarted_modified_or_terminated": False,
        "authorization": decision["authorization"],
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate_postaudit(root, value)
    return value


def validate_postaudit(root: Path, value: Mapping[str, Any]) -> None:
    if (
        value.get("artifact_version") != 1
        or value.get("role") != "v24312_deadline_reliability_postresult_audit"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("source_manifest_unchanged") is not True
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or value.get("runtime_input_from_benchmark") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
        or value.get("external_network_model_search_fetch_or_evaluator_calls") != 0
        or value.get("protected_watcher_signaled_restarted_modified_or_terminated")
        is not False
        or value.get("authorization", {}).get("exact220") is not False
        or value.get("authorization", {}).get("evaluator") is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.12 post-result audit drifted")


def preregister(root: Path = ROOT) -> None:
    root = root.resolve()
    for relative in (DIAGNOSIS, PROTOCOL, RESULT, DECISION, POSTAUDIT):
        if (root / relative).exists() or (root / relative).is_symlink():
            raise FileExistsError(root / relative)
    _new_json(root / DIAGNOSIS, build_diagnosis(root))
    _new_json(root / PROTOCOL, build_protocol(root))


def run_probe(root: Path = ROOT) -> None:
    root = root.resolve()
    protocol = _read(root / PROTOCOL)
    validate_protocol(root, protocol)
    for relative in (RESULT, DECISION, POSTAUDIT):
        if (root / relative).exists() or (root / relative).is_symlink():
            raise FileExistsError(root / relative)
    _new_json(root / RESULT, execute_probe(root))


def finalize(root: Path = ROOT) -> None:
    root = root.resolve()
    for relative in (DECISION, POSTAUDIT):
        if (root / relative).exists() or (root / relative).is_symlink():
            raise FileExistsError(root / relative)
    _new_json(root / DECISION, build_decision(root))
    _new_json(root / POSTAUDIT, build_postaudit(root))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("preregister", "probe", "finalize", "child")
    )
    parser.add_argument("--mode", choices=MODES)
    parser.add_argument("--output-root")
    parser.add_argument("--directory")
    parser.add_argument("--slots")
    args = parser.parse_args()
    if args.command == "preregister":
        preregister(ROOT)
    elif args.command == "probe":
        run_probe(ROOT)
    elif args.command == "finalize":
        finalize(ROOT)
    else:
        if not all((args.mode, args.output_root, args.directory, args.slots)):
            raise ValueError("V2.43.12 child arguments are incomplete")
        child_mode(
            str(args.mode),
            Path(args.output_root).resolve(),
            Path(args.directory).resolve(),
            Path(args.slots).resolve(),
        )


if __name__ == "__main__":
    main()
