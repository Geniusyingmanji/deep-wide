#!/usr/bin/env python3
"""Freeze the post-V2.42.16 neutral GPT-5.6 capacity successor."""

from __future__ import annotations

import argparse
import ast
import json
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24194_capacity_ladder import (  # noqa: E402
    ProbeSettings,
    payload_sha256,
    settings_from_dict,
)
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.preregister_v24210_search_component import (  # noqa: E402
    _start_ticks,
    ordinary,
    publish_new,
    read_object,
    sha256,
)


ROLE = "v24217_capacity_successor_preregistration"
PROTOCOL_ID = "v24217_post_v24216_neutral_capacity_successor_v1"
OUTPUT = Path("results/v24217_capacity_successor_preregistration_v1_20260731.json")
STATE = Path("outputs/v24217_capacity_successor_watcher_state_v1_20260731.json")
ACTIVATION = Path("results/v24217_capacity_successor_activation_v1_20260731.json")
WAIT_AUDIT = Path("results/v24217_capacity_successor_wait_audit_v1_20260731.json")
EXECUTION_START = Path("results/v24217_capacity_successor_execution_start_v1_20260731.json")
REPORT = Path("results/v24217_capacity_successor_report_v1_20260731.json")
FREEZE = Path("results/v24217_next_fresh_all220_capacity_freeze_v1_20260731.json")

PARENT_PROTOCOL = Path("results/v24216_package_gate_preregistration_v1_20260731.json")
PARENT_PROTOCOL_SHA256 = "5ad2ba72fda4dc516f922ddc33066a72054c7b082abee50dc7ac0b201a42b714"
PARENT_ACTIVATION = Path("results/v24216_package_gate_activation_v1_20260731.json")
PARENT_ACTIVATION_SHA256 = "fe3f285142086be6e7e64db5872bbe21b35b103d95747a76f0844bf74c2e30e5"
PARENT_WAIT_AUDIT = Path("results/v24216_package_gate_wait_audit_v1_20260731.json")
PARENT_WAIT_AUDIT_SHA256 = "75f70b056e0e780901205e461267e5bd08089c1820d4546e2a8ac181cd491dcb"
PARENT_STATE = Path("outputs/v24216_package_gate_watcher_state_v1_20260731.json")

V24194_PROTOCOL = Path("results/v24194_capacity_ladder_preregistration_v1_20260731.json")
V24194_PROTOCOL_SHA256 = "5da63416e800a73afa49ae479351f83e30892947e987e5d390011b02face4681"
V24194_STATE = Path("outputs/v24194_capacity_ladder_watcher_state_v1_20260731.json")
V24194_MARKER = "scripts/watch_v24194_capacity_ladder.py"
V24194_EXECUTION_ACTIVATION = Path("results/v24194_capacity_ladder_execution_activation_v1_20260731.json")
V24194_REPORT = Path("results/v24194_capacity_ladder_report_v1_20260731.json")
V24194_FREEZE = Path("results/v24194_next_fresh_all220_capacity_freeze_v1_20260731.json")

V24196_PROTOCOL = Path("results/v24196_capacity_executor_preregistration_v1_20260731.json")
V24196_STATE = Path("outputs/v24196_capacity_executor_watcher_state_v1_20260731.json")
V24196_MARKER = "scripts/watch_v24196_capacity_executor.py"
V24196_REPORT = Path("results/v24196_capacity_ladder_report_v1_20260731.json")
V24196_FREEZE = Path("results/v24196_next_fresh_all220_capacity_freeze_v1_20260731.json")

WATCHER_MARKER = "scripts/watch_v24217_capacity_successor.py"
LEASE = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24217_post_package_gate_neutral_capacity_v1"
LEASE_PURPOSE = "neutral_capacity_after_v24216_go_for_next_fresh_all220"

MUST_REMAIN_ABSENT = (
    OUTPUT,
    STATE,
    ACTIVATION,
    WAIT_AUDIT,
    EXECUTION_START,
    REPORT,
    FREEZE,
)
CONTROL_FILES = (
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/v24194_capacity_ladder.py",
    "src/deepwide_agent/v24217_capacity_successor.py",
    "scripts/deepwide_api_lease.py",
    "scripts/audit_v24187_phase_liveness.py",
    "scripts/audit_v24195_lease_owner_compatibility.py",
    "scripts/preregister_v24217_capacity_successor.py",
    "scripts/watch_v24217_capacity_successor.py",
    "scripts/activate_v24217_capacity_successor.py",
    "scripts/audit_v24217_capacity_successor_wait.py",
    "tests/test_v24217_capacity_successor.py",
    "tests/test_preregister_v24217_capacity_successor.py",
    "tests/test_watch_v24217_capacity_successor.py",
    "tests/test_activate_v24217_capacity_successor.py",
    "tests/test_audit_v24217_capacity_successor_wait.py",
)
DECISION_FIELDS = (
    "protocol_id",
    "parent_contract",
    "neutral_capacity_contract",
    "legacy_watcher_contract",
    "crash_only_contract",
    "lease_contract",
    "execution",
    "source_policy",
    "authorization",
    "safe_wait_boundary",
    "control_surface",
)


def _present(root: Path, path: Path) -> bool:
    target = root / path
    return target.exists() or target.is_symlink()


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _receipt(root: Path, path: Path, digest: str, role: str) -> dict[str, str]:
    value = read_object(ordinary(root, path, digest))
    if value.get("role") != role:
        raise RuntimeError("V2.42.17 parent receipt role drifted")
    return {"path": str(path), "sha256": digest}


def _parent_wait(root: Path) -> dict[str, Any]:
    state = read_object(ordinary(root, PARENT_STATE))
    if (
        state.get("role") != "v24216_package_gate_watcher_state"
        or state.get("protocol", {}).get("sha256") != PARENT_PROTOCOL_SHA256
        or state.get("execution_activation", {}).get("sha256")
        != PARENT_ACTIVATION_SHA256
        or state.get("terminal") is not False
        or state.get("capacity_measurement_allowed") is not False
        or state.get("all220_freeze_design_allowed") is not False
        or state.get("benchmark_forward_or_full220_launch_allowed") is not False
        or state.get(
            "mapping_gold_category_question_type_or_per_task_score_used_for_forward_routing"
        )
        is not False
        or state.get("process_signal_restart_resume_rerun_skip_or_selective_retry")
        is not False
        or not _sealed(state, "state_payload_sha256")
    ):
        raise RuntimeError("V2.42.17 parent wait envelope drifted")
    return {
        "path": str(PARENT_STATE),
        "status": state.get("status"),
        "terminal": False,
        "capacity_measurement_allowed": False,
        "contents_emitted": False,
    }


def _process(marker: str, *, proc_root: Path) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for row in process_snapshot(proc_root):
        argv = [str(value) for value in row.get("argv") or []]
        script = actual_python_script(argv)
        if script is not None and (script == marker or script.endswith("/" + marker)):
            matches.append({"pid": int(row["pid"]), "argv": argv})
    if len(matches) != 1 or not all(flag in matches[0]["argv"] for flag in ("-I", "-B")):
        raise RuntimeError(f"V2.42.17 protected process drifted: {marker}")
    pid = matches[0]["pid"]
    return {
        "marker": marker,
        "pid": pid,
        "start_ticks": _start_ticks(proc_root, pid),
        "python_isolated_no_bytecode_required": True,
        "command_line_emitted": False,
    }


def _legacy_boundary(root: Path, *, proc_root: Path) -> dict[str, Any]:
    v94 = read_object(ordinary(root, V24194_STATE))
    v96 = read_object(ordinary(root, V24196_STATE))
    forbidden = (
        V24194_EXECUTION_ACTIVATION,
        V24194_REPORT,
        V24194_FREEZE,
        V24196_REPORT,
        V24196_FREEZE,
    )
    if (
        v94.get("role") != "v24194_capacity_ladder_watcher_state"
        or v94.get("terminal") is not False
        or v94.get("shared_api_lease_acquired") is not False
        or v94.get("neutral_capacity_model_api_called") is not False
        or v96.get("role") != "v24196_capacity_executor_watcher_state"
        or v96.get("terminal") is not False
        or v96.get("shared_api_lease_acquired") is not False
        or v96.get("neutral_capacity_model_api_called") is not False
        or any(_present(root, path) for path in forbidden)
    ):
        raise RuntimeError("V2.42.17 legacy capacity boundary drifted")
    return {
        "v24194": _process(V24194_MARKER, proc_root=proc_root),
        "v24196": _process(V24196_MARKER, proc_root=proc_root),
        "v24194_status": v94.get("status"),
        "v24196_status": v96.get("status"),
        "execution_activation_reports_and_freezes_absent": True,
        "legacy_watchers_preserved_without_signal_or_restart": True,
        "contents_emitted": False,
    }


def _capacity_contract(root: Path) -> dict[str, Any]:
    protocol = read_object(ordinary(root, V24194_PROTOCOL, V24194_PROTOCOL_SHA256))
    capacity = protocol.get("capacity_contract")
    if not isinstance(capacity, dict):
        raise RuntimeError("V2.42.17 source capacity contract is absent")
    settings = settings_from_dict(capacity.get("settings") or {})
    if (
        capacity.get("settings_sha256") != payload_sha256(settings.as_dict())
        or capacity.get("endpoint") != "http://127.0.0.1:9878/responses"
        or capacity.get("model") != "gpt-5.6-sol"
        or capacity.get("reasoning_effort") != "high"
        or capacity.get("service_tier") != "priority"
        or capacity.get("request_timeout_seconds") != 180
        or capacity.get("client_max_retries") != 1
    ):
        raise RuntimeError("V2.42.17 source capacity contract drifted")
    return capacity


def _lease_boundary(root: Path, *, proc_root: Path) -> dict[str, Any]:
    observed = lease_observation(root, proc_root)
    if (
        observed.get("active") is not False
        or observed.get("ordinary") is not True
        or observed.get("record_valid") is not True
        or observed.get("lock_holder_pids") != []
    ):
        raise RuntimeError("V2.42.17 shared lease is not safely inactive")
    return {
        "present": observed.get("present"),
        "active": False,
        "ordinary": True,
        "record_valid": True,
        "lock_holder_count": 0,
        "owner_purpose_pid_or_contents_emitted": False,
    }


def _static_control_audit(root: Path) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for relative in CONTROL_FILES:
        source = ordinary(root, relative).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=relative)
        direct_network: list[str] = []
        process_calls: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                direct_network.extend(
                    alias.name
                    for alias in node.names
                    if alias.name in {"requests", "httpx", "urllib", "socket"}
                )
            elif isinstance(node, ast.ImportFrom) and node.module in {
                "requests",
                "httpx",
                "urllib",
                "socket",
            }:
                direct_network.append(str(node.module))
            elif (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "subprocess"
            ):
                process_calls.append(node.attr)
        if process_calls:
            raise RuntimeError("V2.42.17 direct subprocess capability appeared")
        allowed_network = {
            "src/deepwide_agent/clients.py": {"requests"},
            "scripts/deepwide_api_lease.py": {"socket"},
        }.get(relative, set())
        observed_network = set(direct_network)
        if not observed_network.issubset(allowed_network):
            raise RuntimeError("V2.42.17 network capability escaped client adapter")
        rows[relative] = {
            "sha256": sha256(root / relative),
            "direct_network_imports": sorted(observed_network),
            "network_authorized_only_in_client_or_lease_metadata_adapter": bool(
                observed_network
            ),
            "process_execution_references": [],
        }
    return rows


def _fixed(root: Path) -> dict[str, Any]:
    capacity = _capacity_contract(root)
    return {
        "parent_contract": {
            "protocol": _receipt(
                root,
                PARENT_PROTOCOL,
                PARENT_PROTOCOL_SHA256,
                "v24216_package_gate_preregistration",
            ),
            "activation": _receipt(
                root,
                PARENT_ACTIVATION,
                PARENT_ACTIVATION_SHA256,
                "v24216_package_gate_activation",
            ),
            "wait_audit": _receipt(
                root,
                PARENT_WAIT_AUDIT,
                PARENT_WAIT_AUDIT_SHA256,
                "v24216_package_gate_wait_audit",
            ),
            "state_path": str(PARENT_STATE),
            "accepted_go_statuses": [
                "complete_identity_handoff_no_package_gate_required",
                "complete_package_gate_go",
            ],
            "terminal_no_go_or_failure_stops_without_capacity_api": True,
        },
        "neutral_capacity_contract": {
            "source_protocol": {
                "path": str(V24194_PROTOCOL),
                "sha256": V24194_PROTOCOL_SHA256,
            },
            "capacity_contract": capacity,
            "capacity_contract_sha256": payload_sha256(capacity),
            "reuse_exact_v24194_probe_core_without_semantic_change": True,
            "levels": [1, 2, 4, 8, 12],
            "waves_per_level": 3,
            "highest_consecutive_safe_level_selected": True,
            "fixed_selected_concurrency_for_entire_future_all220": True,
            "full220_launch_allowed": False,
        },
        "legacy_watcher_contract": {
            "v24194_protocol": {
                "path": str(V24194_PROTOCOL),
                "sha256": V24194_PROTOCOL_SHA256,
            },
            "v24196_protocol_path": str(V24196_PROTOCOL),
            "both_healthy_watchers_remain_running_and_unmodified": True,
            "v24194_execution_activation_must_remain_absent": True,
            "legacy_report_and_freeze_outputs_must_remain_absent": True,
            "legacy_watchers_need_not_terminate_for_successor_execution": True,
        },
        "crash_only_contract": {
            "execution_start_published_before_client_construction_or_api_call": True,
            "start_without_report_is_terminal_incomplete_no_retry": True,
            "sealed_report_without_freeze_recovers_freeze_without_reprobe": True,
            "report_or_freeze_overwrite_allowed": False,
            "capacity_threshold_or_level_change_after_start_allowed": False,
        },
        "lease_contract": {
            "path": str(LEASE),
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
            "live_owner_purpose_pid_lock_holder_activation_and_start_ticks_required": True,
            "suppress_only_expected_unknown-owner_liveness_findings": True,
            "preserve_and_fail_on_every_unrelated_parent_finding": True,
        },
        "execution": {
            "watcher_marker": WATCHER_MARKER,
            "python_flags": ["-I", "-B"],
            "poll_seconds": 60,
            "proc_root": "/proc",
            "state_path": str(STATE),
            "activation_path": str(ACTIVATION),
            "wait_audit_path": str(WAIT_AUDIT),
            "execution_start_path": str(EXECUTION_START),
            "report_path": str(REPORT),
            "freeze_path": str(FREEZE),
            "quiet_observations_before_lease": 2,
        },
        "source_policy": {
            "before_activation_parent_state_opened": False,
            "parent_safe_state_envelope_only_before_terminal": True,
            "neutral_payload_has_no_benchmark_content": True,
            "benchmark_question_prediction_mapping_gold_category_evaluator_score_read": False,
            "search_fetch_or_evaluator_api_called": False,
            "credential_value_persisted_hashed_or_emitted": False,
            "response_text_or_response_id_persisted": False,
        },
        "authorization": {
            "watcher_active_after_activation": True,
            "neutral_model_capacity_api_after_parent_go_and_lease": True,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
            "legacy_watcher_modification_or_termination": False,
            "benchmark_forward_or_evaluator_call": False,
            "full220_launch": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }


def build_protocol(
    root: Path = ROOT,
    *,
    created_at_unix: int | None = None,
    require_pristine: bool = True,
    proc_root: Path = Path("/proc"),
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.17 may only freeze the canonical workspace")
    future_absent = all(not _present(root, path) for path in MUST_REMAIN_ABSENT)
    if require_pristine and not future_absent:
        raise RuntimeError("V2.42.17 create-exclusive boundary is not pristine")
    fixed = _fixed(root)
    control = {relative: sha256(ordinary(root, relative)) for relative in CONTROL_FILES}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "label_blind": True,
        **fixed,
        "safe_wait_boundary": {
            "future_protocol_state_activation_start_report_and_freeze_absent": future_absent,
            "parent": _parent_wait(root),
            "legacy_capacity": _legacy_boundary(root, proc_root=proc_root),
            "shared_api_lease": _lease_boundary(root, proc_root=proc_root),
        },
        "control_surface": {
            "file_count": len(control),
            "manifest": control,
            "manifest_sha256": payload_sha256(control),
            "must_remain_absent": [str(path) for path in MUST_REMAIN_ABSENT],
            "static_capability_audit": _static_control_audit(root),
        },
    }
    value["decision_contract_sha256"] = payload_sha256(
        {key: value[key] for key in DECISION_FIELDS}
    )
    return value


def validate_protocol(root: Path, path: Path = OUTPUT) -> dict[str, Any]:
    root = root.resolve()
    target = path if path.is_absolute() else root / path
    value = read_object(target)
    manifest = value.get("control_surface", {}).get("manifest")
    fixed = _fixed(root)
    if (
        target.resolve(strict=False) != (root / OUTPUT).resolve(strict=False)
        or target.is_symlink()
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("label_blind") is not True
        or any(value.get(key) != expected for key, expected in fixed.items())
        or value.get("safe_wait_boundary", {}).get(
            "future_protocol_state_activation_start_report_and_freeze_absent"
        )
        is not True
        or value.get("safe_wait_boundary", {}).get("parent", {}).get("terminal")
        is not False
        or value.get("safe_wait_boundary", {})
        .get("shared_api_lease", {})
        .get("active")
        is not False
        or not isinstance(manifest, dict)
        or set(manifest) != set(CONTROL_FILES)
        or value.get("control_surface", {}).get("file_count") != len(CONTROL_FILES)
        or value.get("control_surface", {}).get("manifest_sha256")
        != payload_sha256(manifest)
        or value.get("control_surface", {}).get("must_remain_absent")
        != [str(item) for item in MUST_REMAIN_ABSENT]
        or value.get("decision_contract_sha256")
        != payload_sha256({key: value[key] for key in DECISION_FIELDS})
    ):
        raise RuntimeError("V2.42.17 protocol contract drifted")
    for relative, digest in manifest.items():
        ordinary(root, relative, str(digest))
    if value["control_surface"]["static_capability_audit"] != _static_control_audit(root):
        raise RuntimeError("V2.42.17 static capability receipt drifted")
    return {"path": target, "sha256": sha256(target), "value": value}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / OUTPUT).resolve(strict=False):
        raise RuntimeError("V2.42.17 protocol output path drifted")
    value = build_protocol()
    publish_new(target, value)
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
