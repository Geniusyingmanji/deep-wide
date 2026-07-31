#!/usr/bin/env python3
"""Wait for V2.42.16 GO, then run one crash-only neutral capacity ladder."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = Path("results/v24217_capacity_successor_preregistration_v1_20260731.json")
STATE = Path("outputs/v24217_capacity_successor_watcher_state_v1_20260731.json")


def _payload_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _bootstrap() -> None:
    if __name__ != "__main__" or sys.argv[1:] in (["--help"], ["-h"]):
        return
    if not (
        sys.flags.isolated
        and sys.flags.safe_path
        and sys.flags.no_user_site
        and sys.flags.dont_write_bytecode
    ):
        raise RuntimeError("V2.42.17 watcher requires python -I -B")
    arguments = list(sys.argv[1:])

    def option(name: str, default: str) -> str:
        if name not in arguments:
            return default
        if arguments.count(name) != 1:
            raise RuntimeError(f"V2.42.17 option is not unique: {name}")
        index = arguments.index(name)
        if index + 1 >= len(arguments):
            raise RuntimeError(f"V2.42.17 option lacks a value: {name}")
        return arguments[index + 1]

    root = Path(option("--root", str(ROOT))).resolve()
    raw_protocol = Path(option("--protocol", str(PROTOCOL)))
    protocol = raw_protocol if raw_protocol.is_absolute() else root / raw_protocol
    raw_state = Path(option("--state", str(STATE)))
    state = raw_state if raw_state.is_absolute() else root / raw_state
    if (
        root != ROOT.resolve()
        or protocol.resolve(strict=False) != (root / PROTOCOL).resolve(strict=False)
        or protocol.is_symlink()
        or not protocol.is_file()
        or state.resolve(strict=False) != (root / STATE).resolve(strict=False)
        or state.is_symlink()
        or option("--poll-seconds", "60") != "60"
        or option("--proc-root", "/proc") != "/proc"
        or "--once" in arguments
    ):
        raise RuntimeError("V2.42.17 watcher execution drifted")
    value = json.loads(protocol.read_text(encoding="utf-8"))
    control = value.get("control_surface") or {}
    manifest = control.get("manifest")
    if (
        value.get("protocol_id")
        != "v24217_post_v24216_neutral_capacity_successor_v1"
        or not isinstance(manifest, dict)
        or control.get("file_count") != len(manifest)
        or control.get("manifest_sha256") != _payload_sha(manifest)
    ):
        raise RuntimeError("V2.42.17 watcher protocol is invalid")
    for relative, digest in manifest.items():
        target = root / relative
        if (
            target.is_symlink()
            or not target.is_file()
            or hashlib.sha256(target.read_bytes()).hexdigest() != digest
        ):
            raise RuntimeError("V2.42.17 control bytes drifted")


_bootstrap()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.clients import ResponsesClient  # noqa: E402
from deepwide_agent.v24194_capacity_ladder import (  # noqa: E402
    run_capacity_ladder,
    settings_from_dict,
)
from deepwide_agent.v24217_capacity_successor import (  # noqa: E402
    build_freeze,
    build_report,
    payload_sha256,
    validate_freeze,
    validate_report,
)
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    build_report as build_v24187_report,
    process_snapshot,
)
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    build_report as build_v24195_report,
    lease_observation,
)
from scripts.deepwide_api_lease import (  # noqa: E402
    DeepWideApiLeaseBusy,
    acquire_deepwide_api_lease,
)
from scripts.preregister_v24210_search_component import (  # noqa: E402
    publish_new,
    read_object,
    sha256,
)
from scripts.preregister_v24217_capacity_successor import (  # noqa: E402
    ACTIVATION,
    EXECUTION_START,
    FREEZE,
    LEASE_OWNER,
    LEASE_PURPOSE,
    OUTPUT,
    PARENT_ACTIVATION_SHA256,
    PARENT_PROTOCOL_SHA256,
    PARENT_STATE,
    REPORT,
    STATE,
    V24194_EXECUTION_ACTIVATION,
    V24194_FREEZE,
    V24194_MARKER,
    V24194_REPORT,
    V24194_STATE,
    V24196_FREEZE,
    V24196_MARKER,
    V24196_REPORT,
    V24196_STATE,
    validate_protocol,
)


PARENT_PRETERMINAL = {
    "waiting_for_execution_activation",
    "waiting_for_v24215_joint_package_terminal",
    "waiting_for_r1_exact220_release",
    "waiting_for_shared_api_lease",
    "running_baseline_exact_dev64",
    "running_candidate_exact_dev64",
    "evaluating_baseline_after_both_forward_terminal",
    "evaluating_candidate_after_both_forward_terminal",
}
PARENT_GO = {
    "complete_identity_handoff_no_package_gate_required",
    "complete_package_gate_go",
}
PARENT_NO_GO = {
    "complete_package_gate_no_go",
    "critical_package_gate_execution_failed_no_retry",
}
TERMINAL_STATUSES = {
    "complete_capacity_recommendation_available",
    "terminal_capacity_no_go_serial_probe_failed",
    "terminal_parent_package_gate_no_go",
    "terminal_parent_package_gate_failed",
    "terminal_incomplete_capacity_attempt_no_retry",
    "critical_capacity_successor_failed_no_retry",
}
ACTIVE_API_MARKERS = (
    "scripts/run_deepwide_agent.py",
    "scripts/run_official_eval_local.py",
    "scripts/preflight_deepwide.py",
    "scripts/run_v24123_branch.py",
    "scripts/run_v2412_post_gate1_interventions.py",
    "scripts/run_sealed_v2409_owic_capture.py",
    "scripts/run_sealed_v2411_post_p12_owic_capture.py",
    "scripts/watch_v24216_package_gate.py",
)


def _present(root: Path, path: Path) -> bool:
    target = root / path
    return target.exists() or target.is_symlink()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(raw)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _activation(root: Path, protocol_sha: str) -> dict[str, Any] | None:
    if not _present(root, ACTIVATION):
        return None
    from scripts.activate_v24217_capacity_successor import validate_activation

    verified = validate_activation(root, ACTIVATION, protocol_path=OUTPUT)
    if verified["value"].get("protocol", {}).get("sha256") != protocol_sha:
        raise RuntimeError("V2.42.17 activation protocol binding drifted")
    watcher = verified["value"]["watcher"]
    return {
        "path": str(ACTIVATION),
        "sha256": verified["sha256"],
        "watcher_pid": watcher["pid"],
        "watcher_start_ticks": watcher["start_ticks"],
    }


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parent(root: Path) -> tuple[dict[str, Any], str]:
    state = read_object(root / PARENT_STATE)
    status = state.get("status")
    terminal = state.get("terminal")
    if (
        state.get("role") != "v24216_package_gate_watcher_state"
        or state.get("protocol", {}).get("sha256") != PARENT_PROTOCOL_SHA256
        or state.get("execution_activation", {}).get("sha256")
        != PARENT_ACTIVATION_SHA256
        or not isinstance(status, str)
        or terminal not in {True, False}
        or state.get("benchmark_forward_or_full220_launch_allowed") is not False
        or state.get(
            "mapping_gold_category_question_type_or_per_task_score_used_for_forward_routing"
        )
        is not False
        or state.get("process_signal_restart_resume_rerun_skip_or_selective_retry")
        is not False
        or not _sealed(state, "state_payload_sha256")
    ):
        raise RuntimeError("V2.42.17 parent state drifted")
    if terminal is False:
        if (
            status not in PARENT_PRETERMINAL
            or state.get("capacity_measurement_allowed") is not False
            or state.get("all220_freeze_design_allowed") is not False
        ):
            raise RuntimeError("V2.42.17 parent preterminal state drifted")
        return state, "waiting"
    if status in PARENT_GO:
        if (
            state.get("capacity_measurement_allowed") is not True
            or state.get("all220_freeze_design_allowed") is not True
        ):
            raise RuntimeError("V2.42.17 parent GO lacks capacity authority")
        return state, "go"
    if status in PARENT_NO_GO:
        if (
            state.get("capacity_measurement_allowed") is not False
            or state.get("all220_freeze_design_allowed") is not False
        ):
            raise RuntimeError("V2.42.17 parent NO-GO has capacity authority")
        return state, "failed" if status.startswith("critical_") else "no_go"
    raise RuntimeError("V2.42.17 parent terminal status is unregistered")


def _process_identity(marker: str, proc_root: Path) -> dict[str, int]:
    from scripts.audit_v24187_phase_liveness import actual_python_script

    matches: list[dict[str, Any]] = []
    for row in process_snapshot(proc_root):
        argv = [str(item) for item in row.get("argv") or []]
        script = actual_python_script(argv)
        if script is not None and (script == marker or script.endswith("/" + marker)):
            matches.append({"pid": int(row["pid"]), "argv": argv})
    if len(matches) != 1 or not all(flag in matches[0]["argv"] for flag in ("-I", "-B")):
        raise RuntimeError(f"V2.42.17 protected watcher identity drifted: {marker}")
    pid = matches[0]["pid"]
    raw = (proc_root / str(pid) / "stat").read_text(encoding="utf-8")
    suffix = raw[raw.rfind(")") + 2 :].split()
    if len(suffix) <= 19:
        raise RuntimeError("V2.42.17 protected watcher stat is truncated")
    return {"pid": pid, "start_ticks": int(suffix[19])}


def _legacy_boundary(
    root: Path, protocol: dict[str, Any], proc_root: Path
) -> dict[str, Any]:
    frozen = protocol["safe_wait_boundary"]["legacy_capacity"]
    v94_identity = _process_identity(V24194_MARKER, proc_root)
    v96_identity = _process_identity(V24196_MARKER, proc_root)
    if (
        v94_identity.get("pid") != frozen["v24194"]["pid"]
        or v94_identity.get("start_ticks") != frozen["v24194"]["start_ticks"]
        or v96_identity.get("pid") != frozen["v24196"]["pid"]
        or v96_identity.get("start_ticks") != frozen["v24196"]["start_ticks"]
    ):
        raise RuntimeError("V2.42.17 protected watcher changed")
    v94 = read_object(root / V24194_STATE)
    v96 = read_object(root / V24196_STATE)
    if (
        v94.get("role") != "v24194_capacity_ladder_watcher_state"
        or v94.get("terminal") is not False
        or v94.get("shared_api_lease_acquired") is not False
        or v94.get("neutral_capacity_model_api_called") is not False
        or v96.get("role") != "v24196_capacity_executor_watcher_state"
        or v96.get("terminal") is not False
        or v96.get("shared_api_lease_acquired") is not False
        or v96.get("neutral_capacity_model_api_called") is not False
        or any(
            _present(root, path)
            for path in (
                V24194_EXECUTION_ACTIVATION,
                V24194_REPORT,
                V24194_FREEZE,
                V24196_REPORT,
                V24196_FREEZE,
            )
        )
    ):
        raise RuntimeError("V2.42.17 legacy capacity side effect appeared")
    return {
        "v24194_pid_start_ticks_exact": True,
        "v24196_pid_start_ticks_exact": True,
        "both_legacy_watchers_terminal_false": True,
        "both_legacy_watchers_shared_lease_and_api_false": True,
        "legacy_execution_activation_reports_and_freezes_absent": True,
        "contents_emitted": False,
    }


def _active_api_workers(proc_root: Path) -> dict[str, Any]:
    from scripts.audit_v24187_phase_liveness import actual_python_script

    pids: set[int] = set()
    matched: set[str] = set()
    for row in process_snapshot(proc_root):
        pid = int(row["pid"])
        if pid == os.getpid():
            continue
        argv = [str(item) for item in row.get("argv") or []]
        script = actual_python_script(argv)
        if script is None:
            continue
        for marker in ACTIVE_API_MARKERS:
            if script == marker or script.endswith("/" + marker):
                pids.add(pid)
                matched.add(marker)
                break
    return {
        "present": bool(pids),
        "match_count": len(pids),
        "pids": sorted(pids),
        "matched_markers": sorted(matched),
        "command_lines_emitted": False,
    }


def _lease_compatibility(
    root: Path,
    *,
    activation: dict[str, Any],
    lease: dict[str, Any],
    proc_root: Path,
) -> dict[str, Any]:
    observed = lease_observation(root, proc_root)
    pid = int(activation["watcher_pid"])
    if (
        lease.get("owner") != LEASE_OWNER
        or lease.get("purpose") != LEASE_PURPOSE
        or lease.get("pid") != pid
        or observed.get("active") is not True
        or observed.get("ordinary") is not True
        or observed.get("record_valid") is not True
        or observed.get("owner") != LEASE_OWNER
        or observed.get("purpose") != LEASE_PURPOSE
        or observed.get("pid") != pid
        or observed.get("lock_holder_pids") != [pid]
    ):
        raise RuntimeError("V2.42.17 lease identity drifted")
    processes = process_snapshot(proc_root)
    parent = build_v24187_report(root, proc_root=proc_root, processes=processes)
    compatibility = build_v24195_report(
        root,
        proc_root=proc_root,
        processes=processes,
        observed_lease=observed,
    )
    expected_parent = ["shared_api_lease_identity"]
    expected_compatibility = sorted(
        ["shared_api_lease_identity", "v24195:unknown_lease_owner"]
    )
    if (
        parent.get("critical_findings") != expected_parent
        or compatibility.get("critical_findings") != expected_compatibility
        or compatibility.get("compatibility", {}).get("mode")
        != "unknown_lease_owner_active"
        or compatibility.get("compatibility", {}).get(
            "unrelated_parent_critical_findings_preserved"
        )
        is not True
    ):
        raise RuntimeError("V2.42.17 compatibility has unrelated findings")
    return {
        "owner": LEASE_OWNER,
        "purpose": LEASE_PURPOSE,
        "watcher_pid": pid,
        "watcher_start_ticks": activation["watcher_start_ticks"],
        "owner_purpose_pid_and_lock_holder_exact": True,
        "parent_expected_findings": expected_parent,
        "compatibility_expected_findings": expected_compatibility,
        "unrelated_findings": [],
        "contents_emitted": False,
    }


def _previous_quiet_streak(path: Path, protocol_sha: str) -> int:
    if not path.exists() and not path.is_symlink():
        return 0
    value = read_object(path)
    if (
        value.get("role") != "v24217_capacity_successor_watcher_state"
        or value.get("protocol", {}).get("sha256") != protocol_sha
    ):
        raise RuntimeError("V2.42.17 previous state binding drifted")
    streak = value.get("consecutive_quiet_observations", 0)
    if isinstance(streak, bool) or not isinstance(streak, int) or streak < 0:
        raise RuntimeError("V2.42.17 quiet streak is invalid")
    return streak


def _base(
    verified: dict[str, Any],
    *,
    created: int,
    activation: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "artifact_version": 1,
        "role": "v24217_capacity_successor_watcher_state",
        "created_at_unix": created,
        "protocol": {
            "path": str(OUTPUT),
            "sha256": verified["sha256"],
            "decision_contract_sha256": verified["value"]["decision_contract_sha256"],
            "control_manifest_sha256": verified["value"]["control_surface"]["manifest_sha256"],
        },
        "execution_activation": activation,
        "parent_safe_state_envelope_opened": False,
        "parent_terminal_go_validated": False,
        "legacy_capacity_boundary_validated": False,
        "active_api_workers": None,
        "consecutive_quiet_observations": 0,
        "shared_api_lease_acquired": False,
        "lease_compatibility_valid": False,
        "execution_start_published": False,
        "neutral_capacity_model_api_called": False,
        "capacity_report_created": False,
        "capacity_freeze_created": False,
        "benchmark_question_prediction_mapping_gold_category_evaluator_score_read": False,
        "search_fetch_or_evaluator_api_called": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "response_text_or_response_id_persisted": False,
        "legacy_watcher_signaled_restarted_modified_or_terminated": False,
        "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
        "terminal": False,
    }


def _seal_state(path: Path, value: dict[str, Any]) -> None:
    value["state_payload_sha256"] = payload_sha256(value)
    _atomic_json(path, value)


def _phase(
    path: Path,
    value: dict[str, Any],
    *,
    status: str,
    reason: str,
    **updates: Any,
) -> None:
    value.update(status=status, reason=reason, **updates)
    _seal_state(path, value)


def _execution_start(
    root: Path,
    *,
    verified: dict[str, Any],
    activation: dict[str, Any],
    parent: dict[str, Any],
    legacy: dict[str, Any],
    lease: dict[str, Any],
    created: int,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24217_capacity_successor_execution_start",
        "created_at_unix": created,
        "protocol": {"path": str(OUTPUT), "sha256": verified["sha256"]},
        "execution_activation": {
            "path": str(ACTIVATION),
            "sha256": activation["sha256"],
            "watcher_pid": activation["watcher_pid"],
            "watcher_start_ticks": activation["watcher_start_ticks"],
        },
        "parent_package_gate": {
            "path": str(PARENT_STATE),
            "sha256": sha256(root / PARENT_STATE),
            "status": parent["status"],
            "capacity_measurement_allowed": True,
            "all220_freeze_design_allowed": True,
            "contents_emitted": False,
        },
        "legacy_capacity": legacy,
        "shared_api_lease": lease,
        "neutral_payload_only": True,
        "benchmark_question_prediction_mapping_gold_category_evaluator_score_read": False,
        "search_fetch_or_evaluator_api_called": False,
        "credential_value_persisted_hashed_or_emitted": False,
        "full220_launch_allowed": False,
        "retry_or_resume_allowed": False,
    }
    value["execution_start_payload_sha256"] = payload_sha256(value)
    return value


def _validate_execution_start(
    root: Path,
    *,
    verified: dict[str, Any],
    activation: dict[str, Any],
    parent: dict[str, Any],
    legacy: dict[str, Any],
) -> dict[str, Any]:
    value = read_object(root / EXECUTION_START)
    expected_parent = {
        "path": str(PARENT_STATE),
        "sha256": sha256(root / PARENT_STATE),
        "status": parent["status"],
        "capacity_measurement_allowed": True,
        "all220_freeze_design_allowed": True,
        "contents_emitted": False,
    }
    lease = value.get("shared_api_lease") or {}
    if (
        value.get("role") != "v24217_capacity_successor_execution_start"
        or value.get("protocol")
        != {"path": str(OUTPUT), "sha256": verified["sha256"]}
        or value.get("execution_activation", {}).get("sha256")
        != activation["sha256"]
        or value.get("execution_activation", {}).get("watcher_pid")
        != activation["watcher_pid"]
        or value.get("execution_activation", {}).get("watcher_start_ticks")
        != activation["watcher_start_ticks"]
        or value.get("parent_package_gate") != expected_parent
        or value.get("legacy_capacity") != legacy
        or lease.get("owner") != LEASE_OWNER
        or lease.get("purpose") != LEASE_PURPOSE
        or lease.get("watcher_pid") != activation["watcher_pid"]
        or lease.get("watcher_start_ticks") != activation["watcher_start_ticks"]
        or lease.get("owner_purpose_pid_and_lock_holder_exact") is not True
        or lease.get("unrelated_findings") != []
        or lease.get("contents_emitted") is not False
        or value.get("neutral_payload_only") is not True
        or value.get(
            "benchmark_question_prediction_mapping_gold_category_evaluator_score_read"
        )
        is not False
        or value.get("search_fetch_or_evaluator_api_called") is not False
        or value.get("full220_launch_allowed") is not False
        or value.get("retry_or_resume_allowed") is not False
        or not _sealed(value, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.42.17 execution-start receipt drifted")
    return value


def run_cycle(
    root: Path = ROOT,
    *,
    protocol_path: Path = OUTPUT,
    state_path: Path = STATE,
    proc_root: Path = Path("/proc"),
    now: int | None = None,
    lease_factory: Callable[..., Any] = acquire_deepwide_api_lease,
    client_factory: Callable[..., ResponsesClient] = ResponsesClient,
    ladder_runner: Callable[..., dict[str, Any]] = run_capacity_ladder,
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve() or proc_root.resolve() != Path("/proc"):
        raise RuntimeError("V2.42.17 canonical execution boundary drifted")
    verified = validate_protocol(root, protocol_path)
    protocol = verified["value"]
    execution = protocol["execution"]
    target = state_path if state_path.is_absolute() else root / state_path
    if target.resolve(strict=False) != (root / STATE).resolve(strict=False) and not target.is_relative_to(root / "outputs"):
        raise RuntimeError("V2.42.17 state path escaped outputs")
    created = int(time.time()) if now is None else int(now)
    activation = _activation(root, verified["sha256"])
    value = _base(verified, created=created, activation=activation)
    if activation is None:
        if any(_present(root, path) for path in (EXECUTION_START, REPORT, FREEZE)):
            raise RuntimeError("V2.42.17 execution artifact appeared before activation")
        _phase(
            target,
            value,
            status="waiting_for_execution_activation",
            reason="activation_absent",
        )
        return value

    parent, parent_mode = _parent(root)
    value["parent_safe_state_envelope_opened"] = True
    value["parent_state"] = {
        "path": str(PARENT_STATE),
        "status": parent["status"],
        "terminal": parent["terminal"],
        "contents_emitted": False,
    }
    if parent_mode == "waiting":
        if any(_present(root, path) for path in (EXECUTION_START, REPORT, FREEZE)):
            raise RuntimeError("V2.42.17 execution artifact appeared before parent GO")
        _phase(
            target,
            value,
            status="waiting_for_v24216_package_gate_terminal",
            reason="parent_preterminal",
        )
        return value
    if parent_mode in {"no_go", "failed"}:
        if any(_present(root, path) for path in (EXECUTION_START, REPORT, FREEZE)):
            raise RuntimeError("V2.42.17 capacity artifact exists after parent NO-GO")
        _phase(
            target,
            value,
            status=(
                "terminal_parent_package_gate_failed"
                if parent_mode == "failed"
                else "terminal_parent_package_gate_no_go"
            ),
            reason=parent["status"],
            terminal=True,
        )
        return value
    value["parent_terminal_go_validated"] = True

    legacy = _legacy_boundary(root, protocol, proc_root)
    value["legacy_capacity_boundary_validated"] = True
    value["legacy_capacity"] = legacy
    report_present = _present(root, REPORT)
    freeze_present = _present(root, FREEZE)
    start_present = _present(root, EXECUTION_START)
    settings = settings_from_dict(
        protocol["neutral_capacity_contract"]["capacity_contract"]["settings"]
    )
    if freeze_present and not report_present:
        raise RuntimeError("V2.42.17 freeze exists without report")
    if report_present:
        report = read_object(root / REPORT)
        validate_report(
            report,
            expected_settings=settings,
            protocol_path=str(OUTPUT),
            protocol_sha256=verified["sha256"],
        )
        if not start_present:
            raise RuntimeError("V2.42.17 report exists without execution start")
        start = _validate_execution_start(
            root,
            verified=verified,
            activation=activation,
            parent=parent,
            legacy=legacy,
        )
        expected_parent = start["parent_package_gate"]
        if (
            report.get("parent_package_gate") != expected_parent
            or report.get("execution_activation")
            != {"path": str(ACTIVATION), "sha256": activation["sha256"]}
            or report.get("shared_api_lease") != start["shared_api_lease"]
            or int(start.get("created_at_unix", -1))
            > int(report.get("created_at_unix", -1))
        ):
            raise RuntimeError("V2.42.17 report live binding drifted")
        if not freeze_present:
            freeze = build_freeze(
                report,
                expected_settings=settings,
                report_path=str(REPORT),
                report_sha256=sha256(root / REPORT),
                protocol_path=str(OUTPUT),
                protocol_sha256=verified["sha256"],
                created_at_unix=created,
            )
            publish_new(root / FREEZE, freeze)
            recovered = True
        else:
            freeze = read_object(root / FREEZE)
            recovered = False
        derived = validate_freeze(
            freeze,
            report=report,
            expected_settings=settings,
            report_path=str(REPORT),
            report_sha256=sha256(root / REPORT),
            protocol_path=str(OUTPUT),
            protocol_sha256=verified["sha256"],
        )
        selected = derived["selected"]
        _phase(
            target,
            value,
            status=(
                "complete_capacity_recommendation_available"
                if selected > 0
                else "terminal_capacity_no_go_serial_probe_failed"
            ),
            reason=(
                "recovered_freeze_from_sealed_report_without_reprobe"
                if recovered
                else "existing_report_and_freeze_live_valid"
            ),
            terminal=True,
            execution_start_published=True,
            neutral_capacity_model_api_called=True,
            capacity_report_created=True,
            capacity_freeze_created=True,
            capacity_report={"path": str(REPORT), "sha256": sha256(root / REPORT)},
            capacity_freeze={"path": str(FREEZE), "sha256": sha256(root / FREEZE)},
            selected_model_request_concurrency=selected,
            selected_parallel_full220_shards=derived["shards"],
            selected_per_shard_model_workers=derived["workers"],
        )
        return value
    if start_present:
        _validate_execution_start(
            root,
            verified=verified,
            activation=activation,
            parent=parent,
            legacy=legacy,
        )
        _phase(
            target,
            value,
            status="terminal_incomplete_capacity_attempt_no_retry",
            reason="execution_start_exists_without_sealed_report",
            terminal=True,
            execution_start_published=True,
            neutral_capacity_model_api_called=None,
        )
        return value

    workers = _active_api_workers(proc_root)
    value["active_api_workers"] = workers
    if workers["present"]:
        _phase(
            target,
            value,
            status="waiting_for_api_workers_to_exit",
            reason="active_api_worker_family_present",
        )
        return value
    previous = _previous_quiet_streak(target, verified["sha256"])
    required = int(execution["quiet_observations_before_lease"])
    streak = previous + 1
    value["consecutive_quiet_observations"] = streak
    if streak < required:
        _phase(
            target,
            value,
            status="waiting_for_second_quiet_observation",
            reason="capacity_probe_requires_consecutive_quiet_observations",
        )
        return value

    try:
        with lease_factory(root, owner=LEASE_OWNER, purpose=LEASE_PURPOSE) as lease:
            value["shared_api_lease_acquired"] = True
            if _activation(root, verified["sha256"]) != activation:
                raise RuntimeError("V2.42.17 activation changed under lease")
            second_parent, second_mode = _parent(root)
            if second_parent != parent or second_mode != "go":
                raise RuntimeError("V2.42.17 parent changed under lease")
            if _legacy_boundary(root, protocol, proc_root) != legacy:
                raise RuntimeError("V2.42.17 legacy boundary changed under lease")
            second_workers = _active_api_workers(proc_root)
            if second_workers["present"]:
                raise RuntimeError("V2.42.17 API worker appeared under lease")
            compatibility = _lease_compatibility(
                root,
                activation=activation,
                lease=lease,
                proc_root=proc_root,
            )
            value["lease_compatibility_valid"] = True
            value["lease_compatibility"] = compatibility
            parent_identity = {
                "path": str(PARENT_STATE),
                "sha256": sha256(root / PARENT_STATE),
                "status": parent["status"],
                "capacity_measurement_allowed": True,
                "all220_freeze_design_allowed": True,
                "contents_emitted": False,
            }
            start = _execution_start(
                root,
                verified=verified,
                activation=activation,
                parent=parent,
                legacy=legacy,
                lease=compatibility,
                created=created,
            )
            publish_new(root / EXECUTION_START, start)
            value["execution_start_published"] = True
            _phase(
                target,
                value,
                status="running_neutral_capacity_ladder",
                reason="parent_go_legacy_preserved_and_lease_valid",
                shared_api_lease_acquired=True,
                lease_compatibility_valid=True,
                execution_start_published=True,
                neutral_capacity_model_api_called=True,
            )
            capacity = protocol["neutral_capacity_contract"]["capacity_contract"]
            client = client_factory(
                str(capacity["endpoint"]),
                str(capacity["model"]),
                reasoning_effort=str(capacity["reasoning_effort"]),
                service_tier=str(capacity["service_tier"]),
                timeout=int(capacity["request_timeout_seconds"]),
                max_retries=int(capacity["client_max_retries"]),
            )
            measurement = ladder_runner(client, settings=settings)
            report = build_report(
                measurement,
                protocol={"path": str(OUTPUT), "sha256": verified["sha256"]},
                parent_package_gate=parent_identity,
                execution_activation={
                    "path": str(ACTIVATION),
                    "sha256": activation["sha256"],
                },
                shared_api_lease=compatibility,
                created_at_unix=created,
                expected_settings=settings,
            )
            publish_new(root / REPORT, report)
            freeze = build_freeze(
                report,
                expected_settings=settings,
                report_path=str(REPORT),
                report_sha256=sha256(root / REPORT),
                protocol_path=str(OUTPUT),
                protocol_sha256=verified["sha256"],
                created_at_unix=created,
            )
            publish_new(root / FREEZE, freeze)
            derived = validate_freeze(
                freeze,
                report=report,
                expected_settings=settings,
                report_path=str(REPORT),
                report_sha256=sha256(root / REPORT),
                protocol_path=str(OUTPUT),
                protocol_sha256=verified["sha256"],
            )
            selected = derived["selected"]
            value.update(
                status=(
                    "complete_capacity_recommendation_available"
                    if selected > 0
                    else "terminal_capacity_no_go_serial_probe_failed"
                ),
                reason="neutral_capacity_ladder_completed_after_package_gate_go",
                terminal=True,
                capacity_report_created=True,
                capacity_freeze_created=True,
                capacity_report={"path": str(REPORT), "sha256": sha256(root / REPORT)},
                capacity_freeze={"path": str(FREEZE), "sha256": sha256(root / FREEZE)},
                selected_model_request_concurrency=selected,
                selected_parallel_full220_shards=derived["shards"],
                selected_per_shard_model_workers=derived["workers"],
            )
    except DeepWideApiLeaseBusy:
        value.update(
            status="waiting_for_shared_api_lease",
            reason="shared_api_lease_busy",
            shared_api_lease_acquired=False,
            consecutive_quiet_observations=0,
        )
    _seal_state(target, value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--protocol", default=str(OUTPUT))
    parser.add_argument("--state", default=str(STATE))
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--proc-root", default="/proc")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.poll_seconds != 60 or args.proc_root != "/proc":
        raise RuntimeError("V2.42.17 watcher parameters drifted")
    while True:
        try:
            value = run_cycle(
                Path(args.root),
                protocol_path=Path(args.protocol),
                state_path=Path(args.state),
                proc_root=Path(args.proc_root),
            )
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:
            verified = validate_protocol(Path(args.root), Path(args.protocol))
            activation = _activation(Path(args.root), verified["sha256"])
            value = _base(
                verified,
                created=int(time.time()),
                activation=activation,
            )
            start_present = _present(Path(args.root), EXECUTION_START)
            value.update(
                status="critical_capacity_successor_failed_no_retry",
                reason=type(exc).__name__,
                terminal=True,
                execution_start_published=start_present,
                neutral_capacity_model_api_called=None if start_present else False,
                failure_message_or_benchmark_content_emitted=False,
            )
            target = Path(args.state)
            if not target.is_absolute():
                target = Path(args.root) / target
            _seal_state(target, value)
        print(
            json.dumps(
                {
                    key: value[key]
                    for key in ("role", "created_at_unix", "status", "reason", "terminal")
                }
            ),
            flush=True,
        )
        if args.once or value["terminal"]:
            return
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
