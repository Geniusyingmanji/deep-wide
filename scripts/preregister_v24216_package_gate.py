#!/usr/bin/env python3
"""Freeze the V2.42.16 paired cold-start same-dev64 package gate."""

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

from deepwide_agent.v24200_successor import PACKAGE_GATE_CONTRACT  # noqa: E402
from deepwide_agent.v24216_package_gate import payload_sha256  # noqa: E402
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.preregister_v24210_search_component import (  # noqa: E402
    _start_ticks,
    ordinary,
    publish_new,
    read_object,
    sha256,
)
from scripts.preregister_v24212_entropy_component import (  # noqa: E402
    MUST_REMAIN_ABSENT,
)
from scripts.preregister_v24215_joint_package_recovery import (  # noqa: E402
    ACTIVATION as PARENT_ACTIVATION,
    OUTPUT as PARENT_PROTOCOL,
    PUBLICATION as PARENT_PUBLICATION,
    STATE as PARENT_STATE,
    WAIT_AUDIT as PARENT_WAIT_AUDIT,
    WATCHER_MARKER as PARENT_WATCHER_MARKER,
)
from scripts.run_v24216_package_gate import (  # noqa: E402
    ARM_ROOTS,
    BASELINE_RESULT,
    CANDIDATE_RESULT,
    FORWARD_BARRIER,
    GATE_DECISION,
    PAIR_PREPARE,
    execution_template,
)


ROLE = "v24216_package_gate_preregistration"
PROTOCOL_ID = "v24216_joint_package_paired_cold_same_dev64_gate_v1"
OUTPUT = Path("results/v24216_package_gate_preregistration_v1_20260731.json")
STATE = Path("outputs/v24216_package_gate_watcher_state_v1_20260731.json")
ACTIVATION = Path("results/v24216_package_gate_activation_v1_20260731.json")
WAIT_AUDIT = Path("results/v24216_package_gate_wait_audit_v1_20260731.json")
WATCHER_MARKER = "scripts/watch_v24216_package_gate.py"
LEASE_OWNER = "v24216_joint_package_same_dev64_gate_v1"
LEASE_PURPOSE = "paired_cold_dev64_joint_package_vs_selected_baseline"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")

PARENT_PROTOCOL_SHA256 = "345015c5672ff37baa74a633f302aeba92f77d48dd392c3a5fcf38f872db2a34"
PARENT_ACTIVATION_SHA256 = "6c2588e0bbd2dd50ac31bc8e47d5345fc03b4c814edcc6c0262f418f9470b733"
PARENT_WAIT_AUDIT_SHA256 = "5555a5df70bf82e89ad1666ccb63c6007858ac9b55182ee07e5f02c5be275e4a"

R1_STATE = Path("outputs/v24118_r1_finalization_watchdog_state_v1_20260728.json")
V24194_STATE = Path("outputs/v24194_capacity_ladder_watcher_state_v1_20260731.json")
V24194_EXECUTION_ACTIVATION = Path(
    "results/v24194_capacity_ladder_execution_activation_v1_20260731.json"
)
V24194_REPORT = Path("results/v24194_capacity_ladder_report_v1_20260731.json")
V24194_FREEZE = Path("results/v24194_next_fresh_all220_capacity_freeze_v1_20260731.json")
V24196_STATE = Path("outputs/v24196_capacity_executor_watcher_state_v1_20260731.json")
V24196_REPORT = Path("results/v24196_capacity_ladder_report_v1_20260731.json")
V24196_FREEZE = Path("results/v24196_next_fresh_all220_capacity_freeze_v1_20260731.json")
V24194_MARKER = "scripts/watch_v24194_capacity_ladder.py"
V24196_MARKER = "scripts/watch_v24196_capacity_executor.py"

CONTROL_FILES = (
    "src/deepwide_agent/v24216_package_gate.py",
    "scripts/run_v24216_package_gate.py",
    "scripts/preregister_v24216_package_gate.py",
    "scripts/watch_v24216_package_gate.py",
    "scripts/activate_v24216_package_gate.py",
    "scripts/audit_v24216_package_gate_wait.py",
    "tests/test_v24216_package_gate.py",
    "tests/test_run_v24216_package_gate.py",
    "tests/test_preregister_v24216_package_gate.py",
    "tests/test_watch_v24216_package_gate.py",
    "tests/test_activate_v24216_package_gate.py",
    "tests/test_audit_v24216_package_gate_wait.py",
)
DECISION_FIELDS = (
    "protocol_id",
    "parent_contract",
    "paired_dev64_contract",
    "capacity_priority_contract",
    "lease_compatibility_contract",
    "execution",
    "source_policy",
    "authorization",
    "safe_wait_boundary",
    "control_surface",
)


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _present(root: Path, path: Path) -> bool:
    target = root / path
    return target.exists() or target.is_symlink()


def _parent_receipts(root: Path) -> dict[str, Any]:
    rows = (
        (PARENT_PROTOCOL, PARENT_PROTOCOL_SHA256, "v24215_selected_joint_package_recovery_preregistration"),
        (PARENT_ACTIVATION, PARENT_ACTIVATION_SHA256, "v24215_selected_joint_package_recovery_activation"),
        (PARENT_WAIT_AUDIT, PARENT_WAIT_AUDIT_SHA256, "v24215_selected_joint_package_recovery_wait_audit"),
    )
    output: dict[str, Any] = {}
    for path, digest, role in rows:
        value = read_object(ordinary(root, path, digest))
        if value.get("role") != role:
            raise RuntimeError("V2.42.16 parent receipt role drifted")
        output[str(path)] = {"sha256": digest}
    return output


def _parent_preterminal(root: Path) -> dict[str, Any]:
    state = read_object(ordinary(root, PARENT_STATE))
    false_fields = (
        "selected_work_order_opened",
        "markdown_publication_opened",
        "scope_publication_opened",
        "search_publication_opened",
        "entropy_publication_opened",
        "joint_package_publication_created",
        "joint_package_materialized",
        "package_gate_evaluated_or_launched",
        "dev64_launch_allowed",
        "shared_api_lease_acquired",
        "network_model_search_fetch_evaluator_or_api_called",
        "mapping_gold_category_question_type_evaluator_score_or_reward_read",
        "benchmark_forward_or_full220_launch_allowed",
        "leaderboard_submission_or_sota_claim",
        "terminal",
    )
    if (
        state.get("role") != "v24215_selected_joint_package_recovery_state"
        or state.get("protocol", {}).get("sha256") != PARENT_PROTOCOL_SHA256
        or state.get("execution_activation", {}).get("sha256")
        != PARENT_ACTIVATION_SHA256
        or state.get("status")
        != "waiting_for_v24213_entropy_recovery_terminal"
        or any(state.get(field) is not False for field in false_fields)
        or not _sealed(state, "state_payload_sha256")
    ):
        raise RuntimeError("V2.42.16 parent preterminal state drifted")
    return {
        "path": str(PARENT_STATE),
        "status": state["status"],
        "terminal": False,
        "publication_absent": not _present(root, PARENT_PUBLICATION),
        "selected_content_opened": False,
        "contents_emitted": False,
    }


def _process(
    marker: str, *, proc_root: Path = Path("/proc"), isolated: bool = True
) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for row in process_snapshot(proc_root):
        argv = [str(value) for value in row.get("argv") or []]
        script = actual_python_script(argv)
        if script is not None and (script == marker or script.endswith("/" + marker)):
            matches.append({"pid": int(row["pid"]), "argv": argv})
    if len(matches) != 1 or isolated and not all(
        flag in matches[0]["argv"] for flag in ("-I", "-B")
    ):
        raise RuntimeError(f"V2.42.16 protected process drifted: {marker}")
    pid = matches[0]["pid"]
    return {
        "marker": marker,
        "pid": pid,
        "start_ticks": _start_ticks(proc_root, pid),
        "python_isolated_no_bytecode_required": isolated,
        "command_line_emitted": False,
    }


def _r1_boundary(root: Path) -> dict[str, Any]:
    state = read_object(ordinary(root, R1_STATE))
    aggregate = state.get("aggregate") or {}
    if (
        state.get("role") != "v24118_r1_finalization_watchdog_state"
        or state.get("status") != "waiting_for_r1_exact_terminal_220"
        or aggregate.get("selected") != 220
        or aggregate.get("exact_terminal_220") is not False
        or aggregate.get("terminal")
        != int(aggregate.get("completed", -1)) + int(aggregate.get("failed", -1))
        or state.get("mapping_or_gold_read") is not False
        or state.get("evaluator_or_score_read") is not False
    ):
        raise RuntimeError("V2.42.16 R1 safe boundary drifted")
    return {
        "path": str(R1_STATE),
        "selected": 220,
        "terminal": aggregate["terminal"],
        "completed": aggregate["completed"],
        "failed": aggregate["failed"],
        "remaining": aggregate["remaining"],
        "mapping_or_evaluator_read": False,
        "contents_emitted": False,
    }


def _capacity_boundary(root: Path, *, proc_root: Path) -> dict[str, Any]:
    v94 = read_object(ordinary(root, V24194_STATE))
    v96 = read_object(ordinary(root, V24196_STATE))
    outputs = (
        V24194_EXECUTION_ACTIVATION,
        V24194_REPORT,
        V24194_FREEZE,
        V24196_REPORT,
        V24196_FREEZE,
    )
    if (
        v94.get("role") != "v24194_capacity_ladder_watcher_state"
        or v94.get("status") != "waiting_for_r1_release"
        or v94.get("shared_api_lease_acquired") is not False
        or v94.get("neutral_capacity_model_api_called") is not False
        or v96.get("role") != "v24196_capacity_executor_watcher_state"
        or v96.get("status") != "waiting_for_r1_release"
        or v96.get("shared_api_lease_acquired") is not False
        or v96.get("neutral_capacity_model_api_called") is not False
        or v96.get("protected_legacy_capacity_watcher", {}).get("present") is not True
        or any(_present(root, path) for path in outputs)
    ):
        raise RuntimeError("V2.42.16 capacity priority boundary drifted")
    return {
        "v24194_status": v94["status"],
        "v24194_execution_activation_absent": True,
        "v24194_report_and_freeze_absent": True,
        "v24196_status": v96["status"],
        "v24196_report_and_freeze_absent": True,
        "v24196_blocked_by_healthy_legacy_watcher": True,
        "v24194_watcher": _process(V24194_MARKER, proc_root=proc_root),
        "v24196_watcher": _process(V24196_MARKER, proc_root=proc_root),
    }


def _future_absent(root: Path) -> bool:
    files = (
        OUTPUT,
        STATE,
        ACTIVATION,
        WAIT_AUDIT,
        PAIR_PREPARE,
        FORWARD_BARRIER,
        BASELINE_RESULT,
        CANDIDATE_RESULT,
        GATE_DECISION,
    )
    return all(not _present(root, path) for path in files) and all(
        not path.exists() and not path.is_symlink() for path in ARM_ROOTS.values()
    )


def _static_control_audit(root: Path) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for relative in CONTROL_FILES:
        source = ordinary(root, relative).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=relative)
        process_references: list[str] = []
        network_imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                network_imports.extend(
                    alias.name for alias in node.names if alias.name in {"requests", "httpx", "socket"}
                )
            elif isinstance(node, ast.ImportFrom) and node.module in {"requests", "httpx", "socket"}:
                network_imports.append(str(node.module))
            elif (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "subprocess"
                and node.attr == "run"
            ):
                process_references.append("subprocess.run")
        process_references = sorted(set(process_references))
        if network_imports or process_references not in ([], ["subprocess.run"]):
            raise RuntimeError("V2.42.16 unexpected direct capability appeared")
        if process_references and relative != "scripts/run_v24216_package_gate.py":
            raise RuntimeError("V2.42.16 subprocess capability escaped runner")
        if (
            relative == "scripts/run_v24216_package_gate.py"
            and process_references != ["subprocess.run"]
        ):
            raise RuntimeError("V2.42.16 runner process capability is absent")
        rows[relative] = {
            "sha256": sha256(root / relative),
            "direct_network_imports": [],
            "process_references": process_references,
            "process_execution_authorized_only_after_terminal_activation_and_lease": bool(process_references),
        }
    return rows


def _fixed() -> dict[str, Any]:
    template = execution_template(ROOT)
    return {
        "parent_contract": {
            "protocol": {"path": str(PARENT_PROTOCOL), "sha256": PARENT_PROTOCOL_SHA256},
            "activation": {"path": str(PARENT_ACTIVATION), "sha256": PARENT_ACTIVATION_SHA256},
            "wait_audit": {"path": str(PARENT_WAIT_AUDIT), "sha256": PARENT_WAIT_AUDIT_SHA256},
            "state_path": str(PARENT_STATE),
            "publication_path": str(PARENT_PUBLICATION),
            "safe_state_envelope_only_before_parent_terminal": True,
            "publication_open_only_after_parent_terminal": True,
        },
        "paired_dev64_contract": {
            "package_gate_contract": PACKAGE_GATE_CONTRACT,
            "historical_baseline_result_reuse_default": False,
            "paired_baseline_and_candidate_cold_start_required": True,
            "same_opaque_dev64_ids_required": True,
            "same_runtime_manifest_required": True,
            "same_model_search_runtime_budget_and_threshold_required": True,
            "execution_template": template,
            "execution_template_sha256": payload_sha256(template),
            "both_forward_arms_exact_terminal_before_mapping_required": True,
            "same_official_evaluator_contract_required": True,
            "failure_as_zero": True,
            "forward_or_evaluator_resume_allowed": False,
            "selective_rerun_allowed": False,
            "identity_handoff_skips_dev64_and_requires_separate_all220_freeze": True,
            "go_authorizes_capacity_and_separate_all220_freeze_only": True,
            "full220_launch_allowed": False,
        },
        "capacity_priority_contract": {
            "package_gate_precedes_neutral_capacity_measurement": True,
            "v24194_execution_activation_must_remain_absent_before_gate_terminal": True,
            "v24194_and_v24196_capacity_outputs_must_remain_absent_before_gate_terminal": True,
            "healthy_v24194_or_v24196_watcher_may_not_be_signaled_restarted_or_modified": True,
            "capacity_order_conflict_fails_closed": True,
        },
        "lease_compatibility_contract": {
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
            "path": str(LEASE_PATH),
            "old_liveness_expected_finding_during_exact_new_owner": "shared_api_lease_identity",
            "old_v24195_expected_mode_during_exact_new_owner": "unknown_lease_owner_active",
            "suppress_only_these_expected_findings_in_v24216_local_authority": True,
            "preserve_and_fail_on_every_unrelated_parent_finding": True,
            "live_owner_purpose_pid_lock_holder_protocol_activation_and_start_ticks_required": True,
        },
        "execution": {
            "watcher_marker": WATCHER_MARKER,
            "python_flags": ["-I", "-B"],
            "poll_seconds": 60,
            "proc_root": "/proc",
            "state_path": str(STATE),
            "activation_path": str(ACTIVATION),
            "wait_audit_path": str(WAIT_AUDIT),
            "pair_prepare_path": str(PAIR_PREPARE),
            "forward_barrier_path": str(FORWARD_BARRIER),
            "baseline_result_path": str(BASELINE_RESULT),
            "candidate_result_path": str(CANDIDATE_RESULT),
            "gate_decision_path": str(GATE_DECISION),
        },
        "source_policy": {
            "before_activation_parent_state_opened": False,
            "preterminal_parent_safe_state_envelope_only": True,
            "runtime_forward_inputs_exactly_opaque_id_and_question": True,
            "mapping_and_evaluator_open_only_after_both_forward_arms_terminal": True,
            "gate_receives_aggregate_metrics_and_content_free_identity_only": True,
            "category_question_type_split_ground_truth_answer_key_or_per_task_score_for_routing": False,
            "credential_value_persisted_hashed_or_emitted": False,
        },
        "authorization": {
            "watcher_active_after_activation": True,
            "local_pair_materialization_after_parent_terminal": True,
            "shared_api_lease_acquire_after_parent_terminal_and_priority_recheck": True,
            "paired_dev64_forward_and_evaluator_under_one_lease": True,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
            "capacity_measurement_before_package_gate_go": False,
            "benchmark_forward_or_full220_launch": False,
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
        raise RuntimeError("V2.42.16 may only freeze the canonical workspace")
    if any(_present(root, Path(name)) for name in MUST_REMAIN_ABSENT):
        raise RuntimeError("V2.42.16 unattested Python bootstrap path appeared")
    future_absent = _future_absent(root)
    if require_pristine and not future_absent:
        raise RuntimeError("V2.42.16 create-exclusive boundary is not pristine")
    parent = _parent_preterminal(root)
    if parent["publication_absent"] is not True:
        raise RuntimeError("V2.42.16 parent publication appeared before freeze")
    control = {relative: sha256(ordinary(root, relative)) for relative in CONTROL_FILES}
    fixed = _fixed()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "label_blind": True,
        **fixed,
        "safe_wait_boundary": {
            "future_protocol_state_activation_results_roots_absent": future_absent,
            "parent_receipts": _parent_receipts(root),
            "parent_preterminal": parent,
            "r1": _r1_boundary(root),
            "capacity": _capacity_boundary(root, proc_root=proc_root),
            "shared_api_lease_absent": not _present(root, LEASE_PATH),
            "parent_watcher": _process(PARENT_WATCHER_MARKER, proc_root=proc_root),
        },
        "control_surface": {
            "file_count": len(control),
            "manifest": control,
            "manifest_sha256": payload_sha256(control),
            "must_remain_absent": list(MUST_REMAIN_ABSENT),
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
    fixed = _fixed()
    if (
        target.resolve(strict=False) != (root / OUTPUT).resolve(strict=False)
        or target.is_symlink()
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("label_blind") is not True
        or any(value.get(key) != expected for key, expected in fixed.items())
        or value.get("safe_wait_boundary", {}).get(
            "future_protocol_state_activation_results_roots_absent"
        )
        is not True
        or value.get("safe_wait_boundary", {}).get("parent_preterminal", {}).get("terminal")
        is not False
        or value.get("safe_wait_boundary", {}).get("parent_preterminal", {}).get("publication_absent")
        is not True
        or value.get("safe_wait_boundary", {}).get("shared_api_lease_absent") is not True
        or not isinstance(manifest, dict)
        or set(manifest) != set(CONTROL_FILES)
        or value.get("control_surface", {}).get("file_count") != len(CONTROL_FILES)
        or value.get("control_surface", {}).get("manifest_sha256") != payload_sha256(manifest)
        or value.get("control_surface", {}).get("must_remain_absent") != list(MUST_REMAIN_ABSENT)
        or value.get("decision_contract_sha256")
        != payload_sha256({key: value[key] for key in DECISION_FIELDS})
    ):
        raise RuntimeError("V2.42.16 protocol contract drifted")
    _parent_receipts(root)
    for relative, digest in manifest.items():
        ordinary(root, relative, str(digest))
    if value["control_surface"]["static_capability_audit"] != _static_control_audit(root):
        raise RuntimeError("V2.42.16 static capability receipt drifted")
    return {"path": target, "sha256": sha256(target), "value": value}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / OUTPUT).resolve(strict=False):
        raise RuntimeError("V2.42.16 protocol output path drifted")
    value = build_protocol()
    publish_new(target, value)
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
