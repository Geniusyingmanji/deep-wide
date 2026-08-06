#!/usr/bin/env python3
"""Append-only observer repair for the V2.47.15 package build audit."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24714_sparse_full220_order_join as contract  # noqa: E402
from scripts import audit_v24715_order_join_package_build as base  # noqa: E402


FAILURE = Path("results/v24716_v24715_build_observer_failure_v1_20260806.json")
AUDIT = contract.PACKAGE_BUILD


def active_runner() -> bool:
    completed = subprocess.run(
        ["ps", "-eo", "cmd="], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=False,
    )
    return any(
        contract.RUNNER_MARKER in line for line in completed.stdout.splitlines()
        if "ps -eo" not in line
        and "audit_v24715_order_join_package_build.py" not in line
        and "audit_v24717_order_join_observer_repair.py" not in line
    )


def _failure_valid() -> bool:
    value = contract.read_object(ROOT / FAILURE)
    return bool(
        value.get("role") == "v24716_v24715_build_observer_failure"
        and value.get("status")
        == "zero_effect_build_observer_failure_append_only_repair_required"
        and value.get("authorization", {}).get("append_only_observer_repair_build")
        is True
        and value.get("authorization", {}).get("activation_or_forward_launch")
        is False
        and value.get("root_cause", {}).get("active_runner_observer_returned_null")
        is True
        and value.get("repair_contract", {}).get(
            "protocol_mechanism_budget_join_and_stage_contract_unchanged"
        )
        is True
    )


def build_audit() -> dict[str, Any]:
    if not _failure_valid():
        raise RuntimeError("V2.47.17 observer-failure parent drifted")
    with patch.object(base, "_active", side_effect=active_runner):
        value = base.build_audit()
    value.pop("audit_payload_sha256", None)
    value["observer_repair"] = {
        "failure_path": str(FAILURE),
        "failure_sha256": contract.sha256(ROOT / FAILURE),
        "repair_source": "scripts/audit_v24717_order_join_observer_repair.py",
        "repair_source_sha256": contract.sha256(
            ROOT / "scripts/audit_v24717_order_join_observer_repair.py"
        ),
        "only_semantic_change": "active_runner_observer_returns_boolean",
        "base_builder_source_immutable": True,
        "active_runner_observation_type": type(
            value.get("runtime_state", {}).get("forward_runner_active")
        ).__name__,
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    validate_audit(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    repair = value.get("observer_repair", {})
    runtime = value.get("runtime_state", {})
    if (
        value.get("role") != "v24715_order_join_package_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or runtime.get("forward_runner_active") is not False
        or repair.get("failure_sha256") != contract.sha256(ROOT / FAILURE)
        or repair.get("only_semantic_change")
        != "active_runner_observer_returns_boolean"
        or repair.get("active_runner_observation_type") != "bool"
        or repair.get("base_builder_source_immutable") is not True
        or value.get("authorization")
        != {
            "protocol_publication": True,
            "activation_or_forward_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not contract.sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.17 repaired audit drifted")
    return dict(value)


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    value = build_audit()
    publish(ROOT / AUDIT, value)
    print(json.dumps({"path": str(AUDIT), "audit_valid": value["audit_valid"],
                      "findings": value["findings"], "test_count": value["tests"]["observed"],
                      "forward_runner_active": value["runtime_state"]["forward_runner_active"]}, sort_keys=True))
