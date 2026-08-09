#!/usr/bin/env python3
"""Bind the frozen V2.49.29 gate to the corrected V2.49.30 launcher."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24929_unicode_total_neutral_contract as contract  # noqa: E402
from scripts import control_v24929_unicode_total_neutral_gate as parent  # noqa: E402
from scripts import control_v24930_unicode_total_neutral_start as corrected  # noqa: E402


DATE = "20260809"
ACTIVATION = Path(f"results/v24931_unicode_total_neutral_activation_v1_{DATE}.json")
LAUNCHER = Path("scripts/run_v24931_unicode_total_neutral_gate.py")
SOURCE = Path("scripts/control_v24931_unicode_total_neutral_activation.py")
TEST = Path("tests/test_v24931_unicode_total_neutral_activation.py")


def _read(path: Path) -> dict[str, Any]:
    return parent._read(path)


def _tracked(path: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0


def build_activation(*, now: int | None = None) -> dict[str, Any]:
    protocol = parent.validate_protocol(_read(ROOT / contract.PROTOCOL))
    audit = parent.validate_audit(_read(ROOT / contract.PREAUDIT))
    start = corrected.validate_start(_read(ROOT / contract.EXECUTION_START))
    parent._clean_pushed()
    checks = {
        "protocol_and_audit_valid": protocol.get("protocol_id")
        == contract.PROTOCOL_ID
        and audit.get("audit_valid") is True,
        "corrected_start_valid": start.get("status") == "authorized_not_started",
        "launcher_control_and_test_tracked": all(
            _tracked(path) for path in (LAUNCHER, SOURCE, TEST)
        ),
        "launcher_surface_pristine": not (ROOT / ACTIVATION).exists()
        and not (ROOT / ACTIVATION).is_symlink()
        and not (ROOT / contract.RESULT).exists()
        and not (ROOT / contract.OUTPUT_ROOT).exists(),
        "shared_api_lease_inactive": parent._lease_inactive(),
        "conflicting_process_pids_empty": parent._active_conflicts() == [],
        "protected_watchers_unchanged": contract.protected_watcher_snapshot()
        == protocol["protected_watchers"],
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    controls = {
        str(path): contract.sha256(ROOT / path) for path in (LAUNCHER, SOURCE, TEST)
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24931_unicode_total_neutral_activation",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "active_not_started" if not findings else "rejected",
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "corrected_execution_start_sha256": contract.sha256(
            ROOT / contract.EXECUTION_START
        ),
        "corrected_execution_start_payload_sha256": start[
            "execution_start_payload_sha256"
        ],
        "control_manifest": controls,
        "control_manifest_sha256": contract.payload_sha256(controls),
        "checks": checks,
        "findings": findings,
        "first_network_model_search_or_fetch_effect_started": False,
        "binding": {
            "authorization_role_adapter_only": True,
            "algorithm_task_vector_prompt_model_search_fetch_or_budget_changed": False,
            "runtime_input_keys": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        },
        "authorization": {
            "single_fresh_neutral_gate": not findings,
            "retry_resume_or_selective_rerun": False,
            "public_exact220": False,
            "evaluator": False,
        },
    }
    value["activation_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_activation(value: dict[str, Any]) -> dict[str, Any]:
    controls = value.get("control_manifest")
    if (
        value.get("role") != "v24931_unicode_total_neutral_activation"
        or value.get("protocol_id") != contract.PROTOCOL_ID
        or value.get("status") != "active_not_started"
        or value.get("findings") != []
        or not all((value.get("checks") or {}).values())
        or value.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or value.get("preactivation_audit_sha256")
        != contract.sha256(ROOT / contract.PREAUDIT)
        or value.get("corrected_execution_start_sha256")
        != contract.sha256(ROOT / contract.EXECUTION_START)
        or not isinstance(controls, dict)
        or value.get("control_manifest_sha256")
        != contract.payload_sha256(controls)
        or any(contract.sha256(ROOT / path) != digest for path, digest in controls.items())
        or value.get("binding", {}).get("authorization_role_adapter_only") is not True
        or value.get("binding", {}).get(
            "algorithm_task_vector_prompt_model_search_fetch_or_budget_changed"
        )
        is not False
        or value.get("authorization")
        != {
            "single_fresh_neutral_gate": True,
            "retry_resume_or_selective_rerun": False,
            "public_exact220": False,
            "evaluator": False,
        }
        or not parent._sealed(value, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.49.31 activation drifted")
    return value


def main() -> None:
    value = validate_activation(build_activation())
    path = ROOT / ACTIVATION
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    print(
        json.dumps(
            {
                "path": str(ACTIVATION),
                "role": value["role"],
                "status": value["status"],
                "findings": value["findings"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
