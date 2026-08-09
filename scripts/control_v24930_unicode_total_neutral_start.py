#!/usr/bin/env python3
"""Append-only execution-start correction for the frozen V2.49.29 gate.

The frozen V2.49.29 controller stored ``conflicting_process_pids`` as a list
inside a generic boolean checks map.  The valid empty list was therefore
treated as a failed check.  No execution-start artifact or external effect was
created.  This successor binds the frozen protocol and preactivation audit and
uses an explicit ``conflicting_process_pids_empty`` boolean.
"""

from __future__ import annotations

import json
import os
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


ROLE = "v24930_corrected_unicode_total_neutral_execution_start"


def build_start(*, now: int | None = None) -> dict[str, Any]:
    protocol = parent.validate_protocol(parent._read(ROOT / contract.PROTOCOL))
    parent.validate_audit(parent._read(ROOT / contract.PREAUDIT))
    parent._clean_pushed()
    conflicts = parent._active_conflicts()
    checks = {
        "gpt56_endpoint_reachable_without_provider_request": parent._endpoint(),
        "shared_api_lease_inactive": parent._lease_inactive(),
        "conflicting_process_pids_empty": conflicts == [],
        "protected_watchers_unchanged": contract.protected_watcher_snapshot()
        == protocol["protected_watchers"],
        "future_surface_pristine": all(
            not (ROOT / path).exists() and not (ROOT / path).is_symlink()
            for path in (
                contract.EXECUTION_START,
                contract.RESULT,
                contract.POSTAUDIT,
                contract.OUTPUT_ROOT,
            )
        ),
        "frozen_parent_empty_conflict_bug_reproduced": conflicts == []
        and parent.build_start().get("findings") == ["conflicting_process_pids"],
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "authorized_not_started" if not findings else "not_authorized",
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "superseded_controller": str(contract.CONTROL),
        "superseded_controller_sha256": contract.sha256(ROOT / contract.CONTROL),
        "correction": {
            "field": "conflicting_process_pids",
            "frozen_parent_value": conflicts,
            "frozen_parent_interpretation": "generic_truthiness_false",
            "corrected_predicate": "conflicting_process_pids == []",
            "algorithm_model_search_fetch_prompt_budget_or_task_vector_changed": False,
            "external_effect_before_corrected_start": False,
        },
        "selected": contract.TASK_COUNT,
        "executor_concurrency": contract.EXECUTOR_CONCURRENCY,
        "model_slot_cap": contract.MODEL_SLOT_CAP,
        "runtime_input_keys": ["opaque_id", "question"],
        "checks": checks,
        "findings": findings,
        "first_network_model_search_or_fetch_effect_started": False,
        "authorization": {
            "single_fresh_neutral_gate": not findings,
            "retry_resume_or_selective_rerun": False,
            "public_exact220": False,
            "evaluator": False,
        },
    }
    value["execution_start_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_start(value: dict[str, Any]) -> dict[str, Any]:
    if (
        value.get("role") != ROLE
        or value.get("protocol_id") != contract.PROTOCOL_ID
        or value.get("status") != "authorized_not_started"
        or value.get("findings") != []
        or not all((value.get("checks") or {}).values())
        or value.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or value.get("preactivation_audit_sha256")
        != contract.sha256(ROOT / contract.PREAUDIT)
        or value.get("correction", {}).get(
            "algorithm_model_search_fetch_prompt_budget_or_task_vector_changed"
        )
        is not False
        or value.get("correction", {}).get("external_effect_before_corrected_start")
        is not False
        or value.get("authorization")
        != {
            "single_fresh_neutral_gate": True,
            "retry_resume_or_selective_rerun": False,
            "public_exact220": False,
            "evaluator": False,
        }
        or not parent._sealed(value, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.49.30 corrected execution start drifted")
    return value


def main() -> None:
    value = validate_start(build_start())
    path = ROOT / contract.EXECUTION_START
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
                "path": str(contract.EXECUTION_START),
                "role": value["role"],
                "findings": value["findings"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
