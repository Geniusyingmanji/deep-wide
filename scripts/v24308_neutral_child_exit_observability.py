#!/usr/bin/env python3
"""Benchmark-external subprocess fault injection for V2.43.08 receipts."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
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
    child_receipt,
    parent_receipt,
    payload_sha256,
    validate_child_receipt,
    validate_parent_receipt,
)


PROTOCOL_ID = "v24308_benchmark_external_child_exit_observability_v2"
PROTOCOL = Path(
    "results/v24308_child_exit_observability_preregistration_v2_20260803.json"
)
RESULT = Path(
    "results/v24308_child_exit_observability_probe_v2_20260803.json"
)
DECISION = Path(
    "results/v24308_child_exit_observability_decision_v2_20260803.json"
)
POSTAUDIT = Path(
    "results/v24308_child_exit_observability_postresult_audit_v2_20260803.json"
)
INVALIDATION = Path(
    "results/v24308_child_exit_observability_v1_invalidation_v1_20260803.json"
)
V1_ARTIFACTS = (
    Path("results/v24308_child_exit_observability_preregistration_v1_20260803.json"),
    Path("results/v24308_child_exit_observability_probe_v1_20260803.json"),
    Path("results/v24308_child_exit_observability_decision_v1_20260803.json"),
    Path("results/v24308_child_exit_observability_postresult_audit_v1_20260803.json"),
)
PARENT = Path("results/v24307_v24306_postterminal_diagnosis_v1_20260803.json")
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
    "src/deepwide_agent/v24308_child_exit_observability.py",
    "scripts/v24308_neutral_child_exit_observability.py",
    "tests/test_v24308_child_exit_observability.py",
    "tests/test_v24308_neutral_child_exit_observability.py",
)


def sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.43.08 expected ordinary file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.43.08 expected object: {path}")
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


def _manifest(root: Path) -> dict[str, str]:
    return {relative: sha256(root / relative) for relative in SOURCE_FILES}


def build_v1_invalidation(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    old_protocol = _read(root / V1_ARTIFACTS[0])
    old_manifest = old_protocol.get("source_manifest")
    if not isinstance(old_manifest, Mapping) or dict(old_manifest) == _manifest(root):
        raise RuntimeError("V2.43.08 V1 source has not drifted")
    artifacts = {str(path): sha256(root / path) for path in V1_ARTIFACTS}
    value = {
        "artifact_version": 1,
        "role": "v24308_child_exit_observability_v1_invalidation",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "invalid_do_not_use",
        "reason": "freeform_exception_type_could_encode_prohibited_identifier",
        "invalidated_artifacts": artifacts,
        "invalidated_claims": [
            "content_free_child_receipt",
            "neutral_observability_go",
            "future_runner_integration_design",
        ],
        "effect_ledger": {
            "network_calls": 0,
            "model_calls": 0,
            "search_calls": 0,
            "fetch_calls": 0,
            "evaluator_calls": 0,
        },
        "authorization": {
            "future_runner_integration_design": False,
            "future_runner_integration_launch": False,
            "benchmark_dev64": False,
            "exact220": False,
        },
    }
    value["invalidation_payload_sha256"] = payload_sha256(value)
    validate_v1_invalidation(root, value)
    return value


def validate_v1_invalidation(root: Path, value: Mapping[str, Any]) -> None:
    created = value.get("created_at_unix")
    expected_artifacts = {str(path): sha256(root / path) for path in V1_ARTIFACTS}
    if (
        value.get("artifact_version") != 1
        or value.get("role") != "v24308_child_exit_observability_v1_invalidation"
        or isinstance(created, bool)
        or not isinstance(created, int)
        or value.get("status") != "invalid_do_not_use"
        or value.get("reason")
        != "freeform_exception_type_could_encode_prohibited_identifier"
        or value.get("invalidated_artifacts") != expected_artifacts
        or value.get("invalidated_claims")
        != [
            "content_free_child_receipt",
            "neutral_observability_go",
            "future_runner_integration_design",
        ]
        or any(value.get("effect_ledger", {}).values())
        or value.get("authorization")
        != {
            "future_runner_integration_design": False,
            "future_runner_integration_launch": False,
            "benchmark_dev64": False,
            "exact220": False,
        }
        or not _sealed(value, "invalidation_payload_sha256")
    ):
        raise RuntimeError("V2.43.08 V1 invalidation drifted")


def build_protocol(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    invalidation = _read(root / INVALIDATION)
    validate_v1_invalidation(root, invalidation)
    parent = _read(root / PARENT)
    if (
        parent.get("role") != "v24307_v24306_postterminal_diagnosis"
        or parent.get("authorization", {}).get(
            "child_exit_observability_benchmark_external_test"
        )
        is not True
        or not _sealed(parent, "diagnosis_payload_sha256")
    ):
        raise RuntimeError("V2.43.08 parent diagnosis drifted")
    manifest = _manifest(root)
    value = {
        "artifact_version": 1,
        "role": "v24308_child_exit_observability_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"path": str(PARENT), "sha256": sha256(root / PARENT)},
        "predecessor_invalidation": {
            "path": str(INVALIDATION),
            "sha256": sha256(root / INVALIDATION),
        },
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
            "one_benchmark_external_probe": True,
            "benchmark_dev64": False,
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
    parent = value.get("parent")
    invalidation = value.get("predecessor_invalidation")
    created = value.get("created_at_unix")
    if (
        value.get("artifact_version") != 1
        or value.get("role") != "v24308_child_exit_observability_preregistration"
        or value.get("protocol_id") != PROTOCOL_ID
        or isinstance(created, bool)
        or not isinstance(created, int)
        or not isinstance(parent, Mapping)
        or dict(parent)
        != {"path": str(PARENT), "sha256": sha256(root / PARENT)}
        or not isinstance(invalidation, Mapping)
        or dict(invalidation)
        != {"path": str(INVALIDATION), "sha256": sha256(root / INVALIDATION)}
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
            "one_benchmark_external_probe": True,
            "benchmark_dev64": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(value, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.43.08 protocol drifted")


def _write_marker(path: Path, *, valid: bool = True) -> None:
    _new_json(path, {"valid": valid})


def _probe_directory(root: Path, directory: Path) -> Path:
    output = (root / "outputs").resolve()
    if directory.is_symlink() or not directory.is_dir():
        raise RuntimeError("V2.43.08 probe directory must be an ordinary directory")
    resolved = directory.resolve()
    if not resolved.is_relative_to(output):
        raise RuntimeError("V2.43.08 probe directory escaped outputs")
    return resolved


def child(mode: str, directory: Path) -> int:
    if mode not in MODES or mode == "parent_launch_exception":
        raise ValueError("V2.43.08 invalid child mode")
    directory = _probe_directory(ROOT, directory)
    terminal = directory / "child_terminal_receipt.json"
    result = directory / "result_envelope.json"
    model = directory / "model_receipt.json"
    transport = directory / "transport_receipt.json"
    if mode == "timeout":
        time.sleep(2.0)
        return 0
    if mode == "nonzero_with_receipt":
        _new_json(
            terminal,
            child_receipt(
                stage="child_exception",
                exception_type="SyntheticChildError",
                model_receipt_written=False,
                transport_receipt_written=False,
                result_envelope_written=False,
            ),
        )
        return 7
    if mode == "nonzero_without_receipt":
        return 7
    if mode != "zero_missing_envelope":
        _write_marker(result, valid=mode != "invalid_envelope")
    if mode != "missing_model_receipt":
        _write_marker(model)
    if mode != "missing_transport_receipt":
        _write_marker(transport)
    # The terminal receipt is deliberately written last: its booleans describe
    # completed filesystem effects instead of predicting future writes.
    _new_json(
        terminal,
        child_receipt(
            stage="runtime_returned",
            exception_type=None,
            model_receipt_written=model.is_file() and not model.is_symlink(),
            transport_receipt_written=transport.is_file()
            and not transport.is_symlink(),
            result_envelope_written=result.is_file() and not result.is_symlink(),
        ),
    )
    return 0


def _valid_marker(path: Path) -> bool:
    try:
        return _read(path).get("valid") is True
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError):
        return False


def run_mode(
    root: Path,
    mode: str,
    directory: Path,
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    root = root.resolve()
    directory = _probe_directory(root, directory)
    started = time.monotonic()
    return_code: int | None = None
    timed_out = False
    subprocess_exception = False
    if mode == "parent_launch_exception":
        command = [str(root / "definitely_absent_v24308_binary")]
    else:
        command = [
            str(root / ".venv-eval/bin/python"),
            "-I",
            "-B",
            str(root / "scripts/v24308_neutral_child_exit_observability.py"),
            "child",
            "--mode",
            mode,
            "--directory",
            str(directory),
        ]
    try:
        process = subprocess.Popen(
            command,
            cwd=root,
            env={
                "HOME": str(Path.home()),
                "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
                "PYTHONSAFEPATH": "1",
            },
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            return_code = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            return_code = process.wait(timeout=2)
    except OSError:
        subprocess_exception = True
    child_path = directory / "child_terminal_receipt.json"
    child_present = child_path.is_file() and not child_path.is_symlink()
    child_valid = False
    if child_present:
        try:
            validate_child_receipt(_read(child_path))
            child_valid = True
        except (OSError, RuntimeError, TypeError, ValueError):
            child_valid = False
    result_path = directory / "result_envelope.json"
    model_path = directory / "model_receipt.json"
    transport_path = directory / "transport_receipt.json"
    value = parent_receipt(
        return_code=return_code,
        timed_out=timed_out,
        elapsed_seconds=max(0.0, time.monotonic() - started),
        subprocess_exception=subprocess_exception,
        child_terminal_receipt_present=child_present,
        child_terminal_receipt_valid=child_valid,
        result_envelope_present=result_path.is_file() and not result_path.is_symlink(),
        result_envelope_valid=_valid_marker(result_path),
        model_receipt_present=model_path.is_file() and not model_path.is_symlink(),
        model_receipt_valid=_valid_marker(model_path),
        transport_receipt_present=transport_path.is_file()
        and not transport_path.is_symlink(),
        transport_receipt_valid=_valid_marker(transport_path),
    )
    validate_parent_receipt(value)
    return value


def project(receipts: Mapping[str, Mapping[str, Any]], *, now: int | None = None) -> dict[str, Any]:
    if set(receipts) != set(MODES):
        raise RuntimeError("V2.43.08 receipt mode set drifted")
    for value in receipts.values():
        validate_parent_receipt(value)
    observed = {mode: receipts[mode]["failure_taxonomy"] for mode in MODES}
    value = {
        "artifact_version": 1,
        "role": "v24308_child_exit_observability_probe",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "observed_taxonomy": observed,
        "expected_taxonomy": dict(EXPECTED),
        "exact_taxonomy_match": observed == EXPECTED,
        "receipts": {mode: dict(receipts[mode]) for mode in MODES},
        "effect_ledger": {
            "network_calls": 0,
            "model_calls": 0,
            "search_calls": 0,
            "fetch_calls": 0,
            "evaluator_calls": 0,
        },
        "runtime_input_question_or_opaque_id": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "authorization": {
            "future_runner_integration_design": observed == EXPECTED,
            "future_runner_integration_launch": False,
            "benchmark_dev64": False,
            "exact220": False,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
    validate_projection(value)
    return value


def validate_projection(value: Mapping[str, Any]) -> None:
    receipts = value.get("receipts")
    created = value.get("created_at_unix")
    if (
        value.get("artifact_version") != 1
        or value.get("role") != "v24308_child_exit_observability_probe"
        or value.get("protocol_id") != PROTOCOL_ID
        or isinstance(created, bool)
        or not isinstance(created, int)
        or not isinstance(receipts, Mapping)
        or set(receipts) != set(MODES)
        or value.get("observed_taxonomy") != EXPECTED
        or value.get("expected_taxonomy") != EXPECTED
        or value.get("exact_taxonomy_match") is not True
        or any(value.get("effect_ledger", {}).values())
        or value.get("runtime_input_question_or_opaque_id") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
        or value.get("authorization")
        != {
            "future_runner_integration_design": True,
            "future_runner_integration_launch": False,
            "benchmark_dev64": False,
            "exact220": False,
        }
        or not _sealed(value, "result_payload_sha256")
    ):
        raise RuntimeError("V2.43.08 projection drifted")
    for receipt_value in receipts.values():
        validate_parent_receipt(receipt_value)


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
                root,
                mode,
                directory,
                timeout_seconds=float(protocol["timeout_seconds"]),
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
        "role": "v24308_child_exit_observability_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "neutral_observability_go" if passed else "neutral_observability_no_go",
        "passed": passed,
        "failed_checks": [] if passed else ["exact_taxonomy_or_zero_effect"],
        "observed_taxonomy": result["observed_taxonomy"],
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "result_sha256": sha256(root / RESULT),
        },
        "authorization": {
            "future_runner_integration_design": passed,
            "future_runner_integration_launch": False,
            "benchmark_dev64": False,
            "exact220": False,
        },
    }
    value["decision_payload_sha256"] = payload_sha256(value)
    validate_decision(root, value)
    return value


def validate_decision(root: Path, value: Mapping[str, Any]) -> None:
    created = value.get("created_at_unix")
    if (
        value.get("artifact_version") != 1
        or value.get("role") != "v24308_child_exit_observability_decision"
        or value.get("protocol_id") != PROTOCOL_ID
        or isinstance(created, bool)
        or not isinstance(created, int)
        or value.get("status") != "neutral_observability_go"
        or value.get("passed") is not True
        or value.get("failed_checks") != []
        or value.get("observed_taxonomy") != EXPECTED
        or value.get("provenance")
        != {
            "protocol_sha256": sha256(root / PROTOCOL),
            "result_sha256": sha256(root / RESULT),
        }
        or value.get("authorization")
        != {
            "future_runner_integration_design": True,
            "future_runner_integration_launch": False,
            "benchmark_dev64": False,
            "exact220": False,
        }
        or not _sealed(value, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.43.08 decision drifted")


def build_postaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    result = _read(root / RESULT)
    decision = _read(root / DECISION)
    validate_projection(result)
    findings: list[str] = []
    try:
        validate_decision(root, decision)
    except (OSError, RuntimeError, TypeError, ValueError):
        findings.append("decision_invalid")
    value = {
        "artifact_version": 1,
        "role": "v24308_child_exit_observability_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "findings": findings,
        "audit_valid": not findings,
        "effect_ledger": dict(result["effect_ledger"]),
        "synthetic_temporary_roots_removed": True,
        "question_opaque_id_prompt_response_prediction_url_page_credential_gold_or_category_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "authorization": {
            "future_runner_integration_design": not findings,
            "future_runner_integration_launch": False,
            "benchmark_dev64": False,
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
    if (
        value.get("artifact_version") != 1
        or value.get("role")
        != "v24308_child_exit_observability_postresult_audit"
        or value.get("protocol_id") != PROTOCOL_ID
        or isinstance(created, bool)
        or not isinstance(created, int)
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or any(value.get("effect_ledger", {}).values())
        or value.get("synthetic_temporary_roots_removed") is not True
        or value.get(
            "question_opaque_id_prompt_response_prediction_url_page_credential_gold_or_category_persisted"
        )
        is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
        or value.get("authorization")
        != {
            "future_runner_integration_design": True,
            "future_runner_integration_launch": False,
            "benchmark_dev64": False,
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
        raise RuntimeError("V2.43.08 postresult audit drifted")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=("invalidate-v1", "preregister", "probe", "finalize", "postaudit", "child"),
    )
    parser.add_argument("--mode", choices=MODES)
    parser.add_argument("--directory")
    args = parser.parse_args()
    if args.action == "child":
        if args.mode is None or args.directory is None:
            raise SystemExit("child mode and directory are required")
        raise SystemExit(child(args.mode, Path(args.directory)))
    if args.action == "invalidate-v1":
        value, path = build_v1_invalidation(), INVALIDATION
    elif args.action == "preregister":
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
