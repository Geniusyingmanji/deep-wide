#!/usr/bin/env python3
"""Benchmark-external integration gate for V2.43.08 runner receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    payload_sha256,
    validate_parent_receipt,
)
from deepwide_agent.v24309_runner_exit_integration import (  # noqa: E402
    MODEL_RECEIPT_NAME,
    RESULT_NAME,
    TRANSPORT_RECEIPT_NAME,
    run_child_with_terminal_receipt,
    run_observed_subprocess,
)
from scripts import v24308_neutral_child_exit_observability as v24308  # noqa: E402


PROTOCOL_ID = "v24309_benchmark_external_runner_exit_integration_v1"
PROTOCOL = Path("results/v24309_runner_exit_integration_preregistration_v1_20260803.json")
RESULT = Path("results/v24309_runner_exit_integration_probe_v1_20260803.json")
DECISION = Path("results/v24309_runner_exit_integration_decision_v1_20260803.json")
POSTAUDIT = Path("results/v24309_runner_exit_integration_postresult_audit_v1_20260803.json")
PARENT_DECISION = Path("results/v24308_child_exit_observability_decision_v2_20260803.json")
PARENT_AUDIT = Path("results/v24308_child_exit_observability_postresult_audit_v2_20260803.json")
FROZEN_V24306 = {
    "scripts/run_v24306_paired_dev64.py": "ced8a6f16cb984f3fb69798ceac7d41750004d2781842d928ecec85c516ab73d",
    "scripts/run_v24306_paired_dev64_task.py": "1e377bfe5d4ad10292bf72b9634cf27ea6a9d97fbec3a49c1b03a360f50b8e56",
    "results/v24306_paired_dev64_forward_contract_v1_20260803.json": "097a08877296642b9046bb88fa90e1b00917c82103329454bf238c90eaae5530",
}
MODES = (
    "success",
    "nonzero_with_receipt",
    "nonzero_without_receipt",
    "zero_missing_envelope",
    "invalid_envelope",
    "missing_model_receipt",
    "missing_transport_receipt",
    "timeout",
    "parent_launch_exception",
)
EXPECTED = {
    "success": "success",
    "nonzero_with_receipt": "child_nonzero_with_terminal_receipt",
    "nonzero_without_receipt": "child_nonzero_without_terminal_receipt",
    "zero_missing_envelope": "zero_exit_missing_result_envelope",
    "invalid_envelope": "result_envelope_invalid",
    "missing_model_receipt": "model_receipt_missing_or_invalid",
    "missing_transport_receipt": "transport_receipt_missing_or_invalid",
    "timeout": "hard_deadline_timeout",
    "parent_launch_exception": "parent_subprocess_exception",
}
SOURCE_FILES = (
    "src/deepwide_agent/v24309_runner_exit_integration.py",
    "scripts/v24309_neutral_runner_exit_integration.py",
    "tests/test_v24309_runner_exit_integration.py",
    "tests/test_v24309_neutral_runner_exit_integration.py",
)
PROTOCOL_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "parents",
        "frozen_v24306_sha256",
        "modes",
        "expected_taxonomy",
        "timeout_seconds",
        "synthetic_subprocess_only",
        "runtime_input_question_or_opaque_id",
        "network_model_search_fetch_or_evaluator_calls",
        "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read",
        "source_manifest",
        "source_manifest_sha256",
        "authorization",
        "protocol_payload_sha256",
    }
)
PROJECTION_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "observed_taxonomy",
        "expected_taxonomy",
        "exact_taxonomy_match",
        "parent_receipts",
        "parent_receipt_files_created",
        "effect_ledger",
        "runtime_input_question_or_opaque_id",
        "mapping_gold_category_question_type_split_evaluator_score_read",
        "frozen_v24306_bytes_unchanged",
        "authorization",
        "result_payload_sha256",
    }
)


class SyntheticChildError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.43.09 expected an ordinary file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.43.09 expected an object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _new_json(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _marker(path: Path, *, valid: bool = True) -> None:
    _new_json(path, {"valid": valid})


def validate_marker(value: Mapping[str, Any]) -> None:
    if dict(value) != {"valid": True}:
        raise ValueError("V2.43.09 invalid synthetic marker")


def _manifest(root: Path) -> dict[str, str]:
    return {relative: sha256(root / relative) for relative in SOURCE_FILES}


def build_protocol(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    v24308.validate_v1_invalidation(
        root, v24308._read(root / v24308.INVALIDATION)
    )
    v24308.validate_protocol(root, v24308._read(root / v24308.PROTOCOL))
    v24308.validate_projection(v24308._read(root / v24308.RESULT))
    decision = _read(root / PARENT_DECISION)
    audit = _read(root / PARENT_AUDIT)
    v24308.validate_decision(root, decision)
    v24308.validate_postaudit(root, audit)
    observed_v24306 = {relative: sha256(root / relative) for relative in FROZEN_V24306}
    if observed_v24306 != FROZEN_V24306:
        raise RuntimeError("V2.43.09 frozen V2.43.06 bytes drifted")
    manifest = _manifest(root)
    value = {
        "artifact_version": 1,
        "role": "v24309_runner_exit_integration_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            str(PARENT_DECISION): sha256(root / PARENT_DECISION),
            str(PARENT_AUDIT): sha256(root / PARENT_AUDIT),
        },
        "frozen_v24306_sha256": dict(FROZEN_V24306),
        "modes": list(MODES),
        "expected_taxonomy": dict(EXPECTED),
        "timeout_seconds": 0.15,
        "synthetic_subprocess_only": True,
        "runtime_input_question_or_opaque_id": False,
        "network_model_search_fetch_or_evaluator_calls": 0,
        "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "authorization": {
            "one_benchmark_external_integration_probe": True,
            "future_paired_dev64_design": False,
            "future_paired_dev64_launch": False,
            "exact220": False,
            "evaluator": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    validate_protocol(root, value)
    return value


def validate_protocol(root: Path, value: Mapping[str, Any]) -> None:
    manifest = value.get("source_manifest")
    created = value.get("created_at_unix")
    if (
        set(value) != PROTOCOL_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24309_runner_exit_integration_preregistration"
        or value.get("protocol_id") != PROTOCOL_ID
        or isinstance(created, bool)
        or not isinstance(created, int)
        or value.get("parents")
        != {
            str(PARENT_DECISION): sha256(root / PARENT_DECISION),
            str(PARENT_AUDIT): sha256(root / PARENT_AUDIT),
        }
        or value.get("frozen_v24306_sha256") != FROZEN_V24306
        or {relative: sha256(root / relative) for relative in FROZEN_V24306}
        != FROZEN_V24306
        or value.get("modes") != list(MODES)
        or value.get("expected_taxonomy") != EXPECTED
        or value.get("timeout_seconds") != 0.15
        or value.get("synthetic_subprocess_only") is not True
        or value.get("runtime_input_question_or_opaque_id") is not False
        or value.get("network_model_search_fetch_or_evaluator_calls") != 0
        or value.get(
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or not isinstance(manifest, Mapping)
        or dict(manifest) != _manifest(root)
        or value.get("source_manifest_sha256") != payload_sha256(manifest)
        or value.get("authorization")
        != {
            "one_benchmark_external_integration_probe": True,
            "future_paired_dev64_design": False,
            "future_paired_dev64_launch": False,
            "exact220": False,
            "evaluator": False,
        }
        or not _sealed(value, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.43.09 protocol drifted")


def child(mode: str, directory: Path) -> int:
    if mode not in MODES or mode == "parent_launch_exception":
        raise ValueError("V2.43.09 invalid child mode")
    if mode == "nonzero_without_receipt":
        return 7

    def action() -> None:
        if mode == "timeout":
            time.sleep(2)
            return
        if mode == "nonzero_with_receipt":
            raise SyntheticChildError()
        if mode != "zero_missing_envelope":
            _marker(
                directory / RESULT_NAME,
                valid=mode != "invalid_envelope",
            )
        if mode != "missing_model_receipt":
            _marker(directory / MODEL_RECEIPT_NAME)
        if mode != "missing_transport_receipt":
            _marker(directory / TRANSPORT_RECEIPT_NAME)

    run_child_with_terminal_receipt(
        output_root=ROOT / "outputs",
        directory=directory,
        action=action,
    )
    return 0


def _environment() -> dict[str, str]:
    return {
        "HOME": str(Path.home()),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }


def run_mode(root: Path, mode: str, directory: Path, timeout_seconds: float) -> dict[str, Any]:
    if mode == "parent_launch_exception":
        command = [str(root / "absent_v24309_child")]
    else:
        command = [
            str(root / ".venv-eval/bin/python"),
            "-I",
            "-B",
            str(root / "scripts/v24309_neutral_runner_exit_integration.py"),
            "child",
            "--mode",
            mode,
            "--directory",
            str(directory),
        ]
    outcome = run_observed_subprocess(
        cwd=root,
        output_root=root / "outputs",
        directory=directory,
        command=command,
        environment=_environment(),
        timeout_seconds=timeout_seconds,
        result_validator=validate_marker,
        model_receipt_validator=validate_marker,
        transport_receipt_validator=validate_marker,
    )
    validate_parent_receipt(outcome.receipt)
    return outcome.receipt


def project(receipts: Mapping[str, Mapping[str, Any]], *, now: int | None = None) -> dict[str, Any]:
    if set(receipts) != set(MODES):
        raise RuntimeError("V2.43.09 mode set drifted")
    for receipt in receipts.values():
        validate_parent_receipt(receipt)
    observed = {mode: receipts[mode]["failure_taxonomy"] for mode in MODES}
    value = {
        "artifact_version": 1,
        "role": "v24309_runner_exit_integration_probe",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "observed_taxonomy": observed,
        "expected_taxonomy": dict(EXPECTED),
        "exact_taxonomy_match": observed == EXPECTED,
        "parent_receipts": {mode: dict(receipts[mode]) for mode in MODES},
        "parent_receipt_files_created": len(MODES),
        "effect_ledger": {
            "network_calls": 0,
            "model_calls": 0,
            "search_calls": 0,
            "fetch_calls": 0,
            "evaluator_calls": 0,
        },
        "runtime_input_question_or_opaque_id": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "frozen_v24306_bytes_unchanged": True,
        "authorization": {
            "future_paired_dev64_design": observed == EXPECTED,
            "future_paired_dev64_launch": False,
            "exact220": False,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
    validate_projection(value)
    return value


def validate_projection(value: Mapping[str, Any]) -> None:
    receipts = value.get("parent_receipts")
    created = value.get("created_at_unix")
    if (
        set(value) != PROJECTION_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24309_runner_exit_integration_probe"
        or value.get("protocol_id") != PROTOCOL_ID
        or isinstance(created, bool)
        or not isinstance(created, int)
        or not isinstance(receipts, Mapping)
        or set(receipts) != set(MODES)
        or value.get("observed_taxonomy") != EXPECTED
        or value.get("expected_taxonomy") != EXPECTED
        or value.get("exact_taxonomy_match") is not True
        or value.get("parent_receipt_files_created") != len(MODES)
        or any(value.get("effect_ledger", {}).values())
        or value.get("runtime_input_question_or_opaque_id") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
        or value.get("frozen_v24306_bytes_unchanged") is not True
        or value.get("authorization")
        != {
            "future_paired_dev64_design": True,
            "future_paired_dev64_launch": False,
            "exact220": False,
        }
        or not _sealed(value, "result_payload_sha256")
    ):
        raise RuntimeError("V2.43.09 projection drifted")
    for receipt in receipts.values():
        validate_parent_receipt(receipt)


def run_probe(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    protocol = _read(root / PROTOCOL)
    validate_protocol(root, protocol)
    receipts: dict[str, dict[str, Any]] = {}
    with tempfile.TemporaryDirectory(dir=root / "outputs") as temporary:
        base = Path(temporary)
        for mode in MODES:
            directory = base / mode
            directory.mkdir(mode=0o700)
            receipts[mode] = run_mode(
                root, mode, directory, float(protocol["timeout_seconds"])
            )
    value = project(receipts)
    _new_json(root / RESULT, value)
    return value


def build_decision(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    result = _read(root / RESULT)
    validate_projection(result)
    passed = result["exact_taxonomy_match"] and not any(result["effect_ledger"].values())
    value = {
        "artifact_version": 1,
        "role": "v24309_runner_exit_integration_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "neutral_runner_integration_go" if passed else "neutral_runner_integration_no_go",
        "passed": passed,
        "failed_checks": [] if passed else ["taxonomy_or_effect_ledger"],
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "result_sha256": sha256(root / RESULT),
        },
        "authorization": {
            "future_paired_dev64_design": passed,
            "future_paired_dev64_launch": False,
            "exact220": False,
        },
    }
    value["decision_payload_sha256"] = payload_sha256(value)
    validate_decision(root, value)
    return value


def validate_decision(root: Path, value: Mapping[str, Any]) -> None:
    created = value.get("created_at_unix")
    expected_keys = {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "status",
        "passed",
        "failed_checks",
        "provenance",
        "authorization",
        "decision_payload_sha256",
    }
    if (
        set(value) != expected_keys
        or value.get("artifact_version") != 1
        or value.get("role") != "v24309_runner_exit_integration_decision"
        or value.get("protocol_id") != PROTOCOL_ID
        or isinstance(created, bool)
        or not isinstance(created, int)
        or value.get("status") != "neutral_runner_integration_go"
        or value.get("passed") is not True
        or value.get("failed_checks") != []
        or value.get("provenance")
        != {
            "protocol_sha256": sha256(root / PROTOCOL),
            "result_sha256": sha256(root / RESULT),
        }
        or value.get("authorization")
        != {
            "future_paired_dev64_design": True,
            "future_paired_dev64_launch": False,
            "exact220": False,
        }
        or not _sealed(value, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.43.09 decision drifted")


def build_postaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    result = _read(root / RESULT)
    decision = _read(root / DECISION)
    validate_projection(result)
    findings: list[str] = []
    try:
        validate_decision(root, decision)
    except (OSError, RuntimeError, TypeError, ValueError):
        findings.append("decision_or_frozen_parent_invalid")
    if (
        {relative: sha256(root / relative) for relative in FROZEN_V24306}
        != FROZEN_V24306
    ):
        findings.append("frozen_v24306_bytes_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24309_runner_exit_integration_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "findings": findings,
        "audit_valid": not findings,
        "effect_ledger": dict(result["effect_ledger"]),
        "synthetic_temporary_roots_removed": True,
        "frozen_v24306_sha256": dict(FROZEN_V24306),
        "question_opaque_id_prompt_response_prediction_url_page_credential_gold_or_category_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "authorization": {
            "future_paired_dev64_design": not findings,
            "future_paired_dev64_launch": False,
            "exact220": False,
        },
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "result_sha256": sha256(root / RESULT),
            "decision_sha256": sha256(root / DECISION),
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate_postaudit(root, value)
    return value


def validate_postaudit(root: Path, value: Mapping[str, Any]) -> None:
    created = value.get("created_at_unix")
    expected_keys = {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "findings",
        "audit_valid",
        "effect_ledger",
        "synthetic_temporary_roots_removed",
        "frozen_v24306_sha256",
        "question_opaque_id_prompt_response_prediction_url_page_credential_gold_or_category_persisted",
        "mapping_gold_category_question_type_split_evaluator_score_read",
        "authorization",
        "provenance",
        "audit_payload_sha256",
    }
    if (
        set(value) != expected_keys
        or value.get("artifact_version") != 1
        or value.get("role")
        != "v24309_runner_exit_integration_postresult_audit"
        or value.get("protocol_id") != PROTOCOL_ID
        or isinstance(created, bool)
        or not isinstance(created, int)
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or any(value.get("effect_ledger", {}).values())
        or value.get("synthetic_temporary_roots_removed") is not True
        or value.get("frozen_v24306_sha256") != FROZEN_V24306
        or value.get(
            "question_opaque_id_prompt_response_prediction_url_page_credential_gold_or_category_persisted"
        )
        is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
        or value.get("authorization")
        != {
            "future_paired_dev64_design": True,
            "future_paired_dev64_launch": False,
            "exact220": False,
        }
        or value.get("provenance")
        != {
            "protocol_sha256": sha256(root / PROTOCOL),
            "result_sha256": sha256(root / RESULT),
            "decision_sha256": sha256(root / DECISION),
        }
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.09 postresult audit drifted")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("preregister", "probe", "finalize", "postaudit", "child"))
    parser.add_argument("--mode", choices=MODES)
    parser.add_argument("--directory")
    args = parser.parse_args()
    if args.action == "child":
        if args.mode is None or args.directory is None:
            raise SystemExit("child mode and directory required")
        raise SystemExit(child(args.mode, Path(args.directory)))
    if args.action == "preregister":
        value, path = build_protocol(), PROTOCOL
    elif args.action == "probe":
        value = run_probe()
        print(json.dumps({"path": str(RESULT), "taxonomy": value["observed_taxonomy"]}, sort_keys=True))
        return
    elif args.action == "finalize":
        value, path = build_decision(), DECISION
    else:
        value, path = build_postaudit(), POSTAUDIT
    _new_json(ROOT / path, value)
    print(json.dumps({"path": str(path), "role": value["role"]}, sort_keys=True))


if __name__ == "__main__":
    main()
