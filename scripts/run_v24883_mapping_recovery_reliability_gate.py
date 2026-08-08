#!/usr/bin/env python3
"""Run the frozen neutral 20-way V2.48.83 reliability gate."""

from __future__ import annotations

import concurrent.futures
import json
import os
import socket
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24883_mapping_recovery_reliability_contract as contract  # noqa: E402
from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    validate_parent_receipt,
)
from deepwide_agent.v24879_mapping_recovery_effect_bundle import (  # noqa: E402
    BUNDLE_NAME,
    EFFECT_NAME,
    validate_bundle,
    validate_effect_receipt,
)
from deepwide_agent.v24881_mapping_recovery_subprocess_gate import (  # noqa: E402
    run_observed_bundle_subprocess,
    validate_parent_bundle_receipt,
)
from deepwide_agent.v24882_mapping_recovery_stage_runtime import (  # noqa: E402
    STAGE_NAME,
    validate_stage_receipt,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


def _read(path: Path) -> dict:
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.48.83 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.83 expected object")
    return value


def _sealed(value: dict, field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _environment() -> dict[str, str]:
    return {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "TERM": "xterm-256color",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }


def _new_json(path: Path, value: dict) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _command(directory: Path) -> list[str]:
    return [
        str(ROOT / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(ROOT / contract.CHILD_MARKER),
        "--task",
        str(directory / "visible_task.json"),
    ]


def _run_one(position: int, task: dict[str, str]) -> dict[str, Any]:
    directory = ROOT / contract.TASK_ROOT / f"task_{position:04d}"
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    _new_json(directory / "visible_task.json", task)
    observed, gate = run_observed_bundle_subprocess(
        cwd=ROOT,
        output_root=ROOT / contract.OUTPUT_ROOT,
        directory=directory,
        command=_command(directory),
        environment=_environment(),
        timeout_seconds=contract.TASK_WALL_SECONDS + contract.PARENT_GRACE_SECONDS,
        expected_model_slot_cap=contract.MODEL_SLOT_CAP,
    )
    validate_parent_receipt(observed.receipt)
    validate_parent_bundle_receipt(gate)
    bundle_valid = False
    try:
        validate_bundle(
            output_root=ROOT / contract.OUTPUT_ROOT,
            directory=directory,
            expected_model_slot_cap=contract.MODEL_SLOT_CAP,
        )
        bundle_valid = True
    except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        bundle_valid = False
    stage = "stage_absent"
    try:
        stage = str(
            validate_stage_receipt(_read(directory / STAGE_NAME))["stage"]
        )
    except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        pass
    return {
        "position": position,
        "base_failure_taxonomy": observed.receipt["failure_taxonomy"],
        "disposition": gate["disposition"],
        "timed_out": bool(observed.timed_out),
        "subprocess_exception": bool(observed.subprocess_exception),
        "bundle_valid": bundle_valid,
        "stage": stage,
        "elapsed_seconds": float(observed.receipt["elapsed_seconds"]),
    }


def _validate_authorization() -> tuple[dict, dict, dict]:
    protocol = _read(ROOT / contract.PROTOCOL)
    audit = _read(ROOT / contract.PREAUDIT)
    start = _read(ROOT / contract.EXECUTION_START)
    manifest = contract.source_manifest(ROOT)
    if (
        protocol.get("role")
        != "v24883_mapping_recovery_reliability_preregistration"
        or protocol.get("protocol_id") != contract.PROTOCOL_ID
        or protocol.get("source_manifest") != manifest
        or protocol.get("source_manifest_sha256")
        != contract.payload_sha256(manifest)
        or protocol.get("task_vector_sha256")
        != contract.payload_sha256(contract.task_vector())
        or protocol.get("authorization", {}).get("preactivation_audit") is not True
        or not _sealed(protocol, "protocol_payload_sha256")
        or audit.get("role")
        != "v24883_mapping_recovery_reliability_preactivation_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get("execution_start") is not True
        or not _sealed(audit, "audit_payload_sha256")
        or start.get("role")
        != "v24883_mapping_recovery_reliability_execution_start"
        or start.get("status") != "authorized_not_started"
        or start.get("authorization", {}).get("single_fresh_neutral_gate")
        is not True
        or not _sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.48.83 execution authorization drifted")
    return protocol, audit, start


def main() -> None:
    protocol, _audit, start = _validate_authorization()
    if (
        contract.git(ROOT, "status", "--porcelain")
        or contract.git(ROOT, "rev-parse", "HEAD")
        != contract.git(ROOT, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.48.83 launch requires clean pushed HEAD")
    if (ROOT / contract.RESULT).exists() or (ROOT / contract.OUTPUT_ROOT).exists():
        raise RuntimeError("V2.48.83 execution surface is not pristine")
    with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
        pass
    if contract.protected_watcher_snapshot() != protocol["protected_watchers"]:
        raise RuntimeError("V2.48.83 protected watcher drifted")
    with acquire_deepwide_api_lease(
        ROOT,
        owner=contract.LEASE_OWNER,
        purpose=contract.LEASE_PURPOSE,
        path=ROOT / contract.LEASE_PATH,
    ):
        (ROOT / contract.OUTPUT_ROOT).mkdir(mode=0o700)
        (ROOT / contract.MODEL_SLOT_DIRECTORY).mkdir(mode=0o700)
        for index in range(1, contract.MODEL_SLOT_CAP + 1):
            _new_json(
                ROOT / contract.MODEL_SLOT_DIRECTORY / f"slot_{index:02d}.lock",
                {"artifact_version": 1, "role": "v24883_model_slot", "slot": index},
            )
        (ROOT / contract.TASK_ROOT).mkdir(mode=0o700)
        started = time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=contract.EXECUTOR_CONCURRENCY,
            thread_name_prefix="v24883-neutral",
        ) as pool:
            futures = {
                pool.submit(_run_one, position, task): position
                for position, task in enumerate(contract.task_vector(), start=1)
            }
            rows = [future.result() for future in concurrent.futures.as_completed(futures)]
        wall = max(0.0, time.monotonic() - started)
    rows.sort(key=lambda item: int(item["position"]))
    disposition = Counter(str(row["disposition"]) for row in rows)
    taxonomy = Counter(str(row["base_failure_taxonomy"]) for row in rows)
    stages = Counter(str(row["stage"]) for row in rows)
    valid = sum(bool(row["bundle_valid"]) for row in rows)
    timeouts = sum(bool(row["timed_out"]) for row in rows)
    subprocess_failures = sum(bool(row["subprocess_exception"]) for row in rows)
    pass_gate = bool(
        len(rows) == contract.TASK_COUNT
        and valid >= contract.MINIMUM_VALID_BUNDLES
        and timeouts <= contract.MAXIMUM_HARD_TIMEOUTS
        and subprocess_failures == 0
        and disposition.get("success", 0) == valid
        and stages.get("bundle_committed", 0) == valid
    )
    value = {
        "artifact_version": 1,
        "role": "v24883_mapping_recovery_reliability_result",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "status": "go" if pass_gate else "no_go",
        "task_count": contract.TASK_COUNT,
        "valid_bundles": valid,
        "invalid_bundles": contract.TASK_COUNT - valid,
        "minimum_valid_bundles": contract.MINIMUM_VALID_BUNDLES,
        "valid_bundle_rate": valid / contract.TASK_COUNT,
        "hard_timeouts": timeouts,
        "subprocess_exceptions": subprocess_failures,
        "disposition_counts": dict(sorted(disposition.items())),
        "base_failure_taxonomy_counts": dict(sorted(taxonomy.items())),
        "terminal_stage_counts": dict(sorted(stages.items())),
        "wall_seconds": round(wall, 6),
        "maximum_task_elapsed_seconds": max(
            float(row["elapsed_seconds"]) for row in rows
        ),
        "gate_passed": pass_gate,
        "execution_start_payload_sha256": start[
            "execution_start_payload_sha256"
        ],
        "private_task_query_url_page_prediction_answer_or_credential_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "benchmark_task_or_evaluator_used": False,
        "retry_resume_skip_or_selective_rerun": False,
        "authorization": {
            "next_exact220_protocol_design": pass_gate,
            "exact220_launch": False,
            "evaluator": False,
        },
    }
    value["result_payload_sha256"] = contract.payload_sha256(value)
    _new_json(ROOT / contract.RESULT, value)
    print(json.dumps(value, sort_keys=True))


if __name__ == "__main__":
    main()
