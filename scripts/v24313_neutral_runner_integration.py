#!/usr/bin/env python3
"""Benchmark-external real-child gate for V2.43.13 runner integration."""

from __future__ import annotations

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

from deepwide_agent.v24257_score_first_runtime import validate_visible_task  # noqa: E402
from deepwide_agent.v24287_hard_deadline_fetch import (  # noqa: E402
    validate_transport_health,
)
from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    payload_sha256,
    validate_parent_receipt,
)
from deepwide_agent.v24309_runner_exit_integration import (  # noqa: E402
    run_observed_subprocess,
)
from deepwide_agent.v24313_runner_integration import (  # noqa: E402
    validate_deadline_model_receipt,
)


DATE = "20260803"
PROTOCOL_ID = "v24313_benchmark_external_runner_integration_v1"
PROTOCOL = Path(f"results/v24313_runner_integration_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v24313_runner_integration_probe_v1_{DATE}.json")
DECISION = Path(f"results/v24313_runner_integration_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24313_runner_integration_postresult_audit_v1_{DATE}.json")
PARENT_DECISION = Path(f"results/v24312_deadline_reliability_decision_v1_{DATE}.json")
PARENT_AUDIT = Path(
    f"results/v24312_deadline_reliability_postresult_audit_v1_{DATE}.json"
)
MODES = ("baseline", "candidate")
SOURCE_FILES = (
    "src/deepwide_agent/v24313_runner_integration.py",
    "scripts/v24313_neutral_runner_integration.py",
    "tests/test_v24313_runner_integration.py",
    "tests/test_v24313_neutral_runner_integration.py",
    "tests/fixtures/v24313_synthetic_child.py",
)
RESULT_NAME = "result_envelope.json"
MODEL_NAME = "model_receipt.json"
TRANSPORT_NAME = "transport_receipt.json"
TERMINAL_NAME = "child_terminal_receipt.json"
PARENT_NAME = "parent_exit_receipt.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.43.13 expected an ordinary file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.43.13 expected an object")
    return value


def _new(path: Path, value: Mapping[str, Any]) -> None:
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


def _validate_parent(root: Path) -> None:
    decision = _read(root / PARENT_DECISION)
    audit = _read(root / PARENT_AUDIT)
    if (
        decision.get("status") != "neutral_reliability_go"
        or decision.get("passed") is not True
        or decision.get("authorization", {}).get("fresh_paired_dev64_design")
        is not True
        or decision.get("authorization", {}).get("fresh_paired_dev64_launch")
        is not False
        or not _sealed(decision, "decision_payload_sha256")
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.13 V2.43.12 parent drifted")


def build_protocol(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    _validate_parent(root)
    manifest = _manifest(root)
    value = {
        "artifact_version": 1,
        "role": "v24313_runner_integration_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            str(PARENT_DECISION): sha256(root / PARENT_DECISION),
            str(PARENT_AUDIT): sha256(root / PARENT_AUDIT),
        },
        "arms": list(MODES),
        "real_subprocess_children": len(MODES),
        "runtime_boundary": ["opaque_id", "question"],
        "synthetic_visible_tasks_only": True,
        "model_slot_cap": 2,
        "deadline_aware_slot_and_provider": True,
        "outer_totality": True,
        "external_network_model_search_fetch_or_evaluator_calls": 0,
        "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "authorization": {
            "one_benchmark_external_runner_probe": True,
            "fresh_paired_dev64_design": False,
            "fresh_paired_dev64_launch": False,
            "exact220": False,
            "evaluator": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    validate_protocol(root, value)
    return value


def validate_protocol(root: Path, value: Mapping[str, Any]) -> None:
    manifest = value.get("source_manifest")
    if (
        value.get("artifact_version") != 1
        or value.get("role") != "v24313_runner_integration_preregistration"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("parents")
        != {
            str(PARENT_DECISION): sha256(root / PARENT_DECISION),
            str(PARENT_AUDIT): sha256(root / PARENT_AUDIT),
        }
        or value.get("arms") != list(MODES)
        or value.get("real_subprocess_children") != len(MODES)
        or value.get("runtime_boundary") != ["opaque_id", "question"]
        or value.get("synthetic_visible_tasks_only") is not True
        or value.get("model_slot_cap") != 2
        or value.get("deadline_aware_slot_and_provider") is not True
        or value.get("outer_totality") is not True
        or value.get("external_network_model_search_fetch_or_evaluator_calls") != 0
        or value.get(
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or not isinstance(manifest, Mapping)
        or dict(manifest) != _manifest(root)
        or value.get("source_manifest_sha256") != payload_sha256(manifest)
        or value.get("authorization", {}).get("fresh_paired_dev64_launch")
        is not False
        or value.get("authorization", {}).get("exact220") is not False
        or not _sealed(value, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.43.13 protocol drifted")


def validate_envelope(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "artifact_version",
        "role",
        "arm",
        "completion_kind",
        "model_effects",
        "fourth_model_effect",
        "slot_acquisitions",
        "slot_timeouts",
        "provider_deadline_failures",
        "contains_question_opaque_id_prompt_response_prediction_url_page_credential_gold_category_or_answer",
        "mapping_gold_category_question_type_split_evaluator_score_read",
    }
    if (
        set(value) != expected
        or value.get("role") != "v24313_synthetic_task_envelope"
        or value.get("arm") not in MODES
        or value.get("completion_kind")
        not in {"primary", "best_effort_fallback", "worker_failure_fallback"}
        or value.get("model_effects") != 3
        or value.get("fourth_model_effect") is not False
        or value.get("slot_acquisitions") != 3
        or value.get("slot_timeouts") != 0
        or value.get("provider_deadline_failures") != 0
        or value.get(
            "contains_question_opaque_id_prompt_response_prediction_url_page_credential_gold_category_or_answer"
        )
        is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
    ):
        raise ValueError("V2.43.13 envelope drifted")
    return dict(value)


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


def _slots(output: Path) -> Path:
    value = output / "model_slots"
    value.mkdir(mode=0o700)
    for index in range(1, 3):
        (value / f"slot_{index:02d}.lock").write_text(
            json.dumps({"slot": index}) + "\n", encoding="utf-8"
        )
    return value


def run_case(
    root: Path, arm: str, output: Path, directory: Path, slots: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    directory.mkdir(mode=0o700)
    task = {
        "opaque_id": "task_0123456789abcdef01234567"
        if arm == "baseline"
        else "task_123456789abcdef012345678",
        "question": "Return one table. The column names are: Name and Date.",
    }
    validate_visible_task(task)
    task_path = directory / "visible_task.json"
    _new(task_path, task)
    command = [
        str(root / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(root / "tests/fixtures/v24313_synthetic_child.py"),
        "--arm",
        arm,
        "--task",
        str(task_path),
        "--result",
        str(directory / RESULT_NAME),
        "--model-receipt",
        str(directory / MODEL_NAME),
        "--transport",
        str(directory / TRANSPORT_NAME),
        "--terminal",
        str(directory / TERMINAL_NAME),
        "--slots",
        str(slots),
        "--output-root",
        str(output),
    ]
    observed = run_observed_subprocess(
        cwd=root,
        output_root=output,
        directory=directory,
        command=command,
        environment=_environment(),
        timeout_seconds=3.0,
        result_validator=validate_envelope,
        model_receipt_validator=lambda value: validate_deadline_model_receipt(
            value, expected_cap=2, expected_acquisitions=3
        ),
        transport_receipt_validator=validate_transport_health,
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
        output = Path(temporary)
        slots = _slots(output)
        for arm in MODES:
            cases[arm], parents[arm] = run_case(
                root, arm, output, output / arm, slots
            )
    value = {
        "artifact_version": 1,
        "role": "v24313_runner_integration_probe",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "cases": cases,
        "parent_taxonomy": {
            arm: parents[arm]["failure_taxonomy"] for arm in MODES
        },
        "parent_receipts_created": len(parents),
        "child_terminal_receipts_created": len(parents),
        "external_effect_ledger": {
            "network": 0,
            "model_provider": 0,
            "search": 0,
            "fetch": 0,
            "evaluator": 0,
        },
        "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
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
        value.get("role") != "v24313_runner_integration_probe"
        or value.get("protocol_id") != PROTOCOL_ID
        or not isinstance(cases, Mapping)
        or set(cases) != set(MODES)
        or any(validate_envelope(cases[arm]) is None for arm in MODES)
        or value.get("parent_taxonomy") != {arm: "success" for arm in MODES}
        or value.get("parent_receipts_created") != len(MODES)
        or value.get("child_terminal_receipts_created") != len(MODES)
        or any(value.get("external_effect_ledger", {}).values())
        or value.get(
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or value.get("authorization", {}).get("fresh_paired_dev64_design")
        is not True
        or value.get("authorization", {}).get("fresh_paired_dev64_launch")
        is not False
        or not _sealed(value, "result_payload_sha256")
    ):
        raise RuntimeError("V2.43.13 probe drifted")


def build_decision(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    result = _read(root / RESULT)
    validate_projection(result)
    value = {
        "artifact_version": 1,
        "role": "v24313_runner_integration_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "neutral_runner_integration_go",
        "passed": True,
        "failed_checks": [],
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "result_sha256": sha256(root / RESULT),
        },
        "authorization": result["authorization"],
    }
    value["decision_payload_sha256"] = payload_sha256(value)
    return value


def build_postaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    decision = _read(root / DECISION)
    if (
        decision.get("passed") is not True
        or decision.get("status") != "neutral_runner_integration_go"
        or not _sealed(decision, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.43.13 decision drifted")
    protocol = _read(root / PROTOCOL)
    validate_protocol(root, protocol)
    value = {
        "artifact_version": 1,
        "role": "v24313_runner_integration_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "result_sha256": sha256(root / RESULT),
            "decision_sha256": sha256(root / DECISION),
        },
        "source_manifest_unchanged": protocol["source_manifest"] == _manifest(root),
        "findings": [],
        "audit_valid": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "external_network_model_search_fetch_or_evaluator_calls": 0,
        "authorization": decision["authorization"],
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def preregister(root: Path = ROOT) -> None:
    root = root.resolve()
    for relative in (PROTOCOL, RESULT, DECISION, POSTAUDIT):
        if (root / relative).exists() or (root / relative).is_symlink():
            raise FileExistsError(root / relative)
    _new(root / PROTOCOL, build_protocol(root))


def probe(root: Path = ROOT) -> None:
    root = root.resolve()
    protocol = _read(root / PROTOCOL)
    validate_protocol(root, protocol)
    _new(root / RESULT, execute_probe(root))


def finalize(root: Path = ROOT) -> None:
    root = root.resolve()
    _new(root / DECISION, build_decision(root))
    _new(root / POSTAUDIT, build_postaudit(root))


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "preregister":
        preregister(ROOT)
    elif command == "probe":
        probe(ROOT)
    elif command == "finalize":
        finalize(ROOT)
    else:
        raise SystemExit("usage: v24313_neutral_runner_integration.py preregister|probe|finalize")
