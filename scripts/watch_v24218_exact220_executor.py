#!/usr/bin/env python3
"""Wait for V2.42.16/17 GO, then own exactly one fresh exact-220 run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Mapping


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = Path("results/v24218_exact220_executor_preregistration_v1_20260731.json")
STATE_PATH = Path("outputs/v24218_exact220_executor_watcher_state_v1_20260731.json")


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
        raise RuntimeError("V2.42.18 watcher requires python -I -B")
    arguments = list(sys.argv[1:])

    def option(name: str, default: str) -> str:
        if name not in arguments:
            return default
        if arguments.count(name) != 1:
            raise RuntimeError(f"V2.42.18 option is not unique: {name}")
        index = arguments.index(name)
        if index + 1 >= len(arguments):
            raise RuntimeError(f"V2.42.18 option lacks a value: {name}")
        return arguments[index + 1]

    root = Path(option("--root", str(ROOT))).resolve()
    protocol = Path(option("--protocol", str(PROTOCOL)))
    protocol = protocol if protocol.is_absolute() else root / protocol
    state = Path(option("--state", str(STATE_PATH)))
    state = state if state.is_absolute() else root / state
    if (
        root != ROOT.resolve()
        or protocol.resolve(strict=False) != (root / PROTOCOL).resolve(strict=False)
        or protocol.is_symlink()
        or not protocol.is_file()
        or state.resolve(strict=False) != (root / STATE_PATH).resolve(strict=False)
        or state.is_symlink()
        or option("--poll-seconds", "60") != "60"
        or option("--proc-root", "/proc") != "/proc"
        or "--once" in arguments
    ):
        raise RuntimeError("V2.42.18 watcher execution drifted")
    value = json.loads(protocol.read_text(encoding="utf-8"))
    control = value.get("control_surface") or {}
    manifest = control.get("manifest")
    if (
        value.get("protocol_id")
        != "v24218_post_capacity_single_owner_fresh_exact220_v1"
        or not isinstance(manifest, dict)
        or control.get("file_count") != len(manifest)
        or control.get("manifest_sha256") != _payload_sha(manifest)
    ):
        raise RuntimeError("V2.42.18 watcher protocol is invalid")
    for relative, digest in manifest.items():
        path = root / relative
        if (
            path.is_symlink()
            or not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != digest
        ):
            raise RuntimeError("V2.42.18 control bytes drifted")


_bootstrap()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24218_exact220_executor import (  # noqa: E402
    file_sha256,
    payload_sha256,
)
from scripts.activate_v24218_exact220_executor import (  # noqa: E402
    validate_activation,
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
)
from scripts.preregister_v24218_exact220_executor import (  # noqa: E402
    ACTIVATION,
    EXECUTION_START,
    LEASE_OWNER,
    LEASE_PURPOSE,
    OUTPUT,
    PARENT_CAPACITY_FREEZE,
    PARENT_CAPACITY_REPORT,
    PARENT_CAPACITY_STATE,
    PARENT_PACKAGE_STATE,
    STATE,
    validate_protocol,
)
from scripts.run_v24218_exact220_executor import (  # noqa: E402
    EVALUATOR_ROOT,
    FORWARD_BARRIER,
    MATERIALIZATION,
    PREPARE_ROOT,
    RESULT,
    SHARD_ROOTS,
    SUMMARY,
    run_exact220,
    validate_capacity_authority,
    validate_package_authority,
    validate_result,
)


ACTIVE_API_MARKERS = (
    "scripts/run_deepwide_agent.py",
    "scripts/run_official_eval_local.py",
    "scripts/preflight_deepwide.py",
    "scripts/run_v24123_branch.py",
    "scripts/run_v2412_post_gate1_interventions.py",
    "scripts/run_sealed_v2409_owic_capture.py",
    "scripts/run_sealed_v2411_post_p12_owic_capture.py",
    "scripts/watch_v24216_package_gate.py",
    "scripts/watch_v24217_capacity_successor.py",
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
    path = root / ACTIVATION
    if not path.exists() and not path.is_symlink():
        return None
    verified = validate_activation(root, ACTIVATION)
    value = verified["value"]
    if value.get("protocol", {}).get("sha256") != protocol_sha:
        raise RuntimeError("V2.42.18 activation protocol binding drifted")
    watcher = value["watcher"]
    return {
        "path": str(ACTIVATION),
        "sha256": verified["sha256"],
        "watcher_pid": watcher["pid"],
        "watcher_start_ticks": watcher["start_ticks"],
    }


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _package_parent(root: Path) -> tuple[dict[str, Any], str]:
    state = read_object(root / PARENT_PACKAGE_STATE)
    status = state.get("status")
    if (
        state.get("role") != "v24216_package_gate_watcher_state"
        or state.get("benchmark_forward_or_full220_launch_allowed") is not False
        or state.get(
            "mapping_gold_category_question_type_or_per_task_score_used_for_forward_routing"
        )
        is not False
        or not _sealed(state, "state_payload_sha256")
    ):
        raise RuntimeError("V2.42.18 package parent envelope drifted")
    if state.get("terminal") is not True:
        return state, "waiting"
    if status in {
        "complete_identity_handoff_no_package_gate_required",
        "complete_package_gate_go",
    } and state.get("capacity_measurement_allowed") is True:
        return state, "go"
    return state, "no_go"


def _capacity_parent(root: Path) -> tuple[dict[str, Any], str]:
    state = read_object(root / PARENT_CAPACITY_STATE)
    if (
        state.get("role") != "v24217_capacity_successor_watcher_state"
        or state.get("benchmark_forward_or_full220_launch_allowed") is not False
        or state.get(
            "benchmark_question_prediction_mapping_gold_category_evaluator_score_read"
        )
        is not False
        or not _sealed(state, "state_payload_sha256")
    ):
        raise RuntimeError("V2.42.18 capacity parent envelope drifted")
    if state.get("terminal") is not True:
        return state, "waiting"
    if (
        state.get("status") == "complete_capacity_recommendation_available"
        and state.get("capacity_report_created") is True
        and state.get("capacity_freeze_created") is True
        and (root / PARENT_CAPACITY_REPORT).is_file()
        and (root / PARENT_CAPACITY_FREEZE).is_file()
    ):
        return state, "go"
    return state, "no_go"


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
        raise RuntimeError("V2.42.18 lease identity drifted")
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
        raise RuntimeError("V2.42.18 compatibility has unrelated findings")
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
    if value.get("protocol", {}).get("sha256") != protocol_sha:
        raise RuntimeError("V2.42.18 previous state protocol drifted")
    raw = value.get("consecutive_quiet_observations", 0)
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        raise RuntimeError("V2.42.18 quiet streak is invalid")
    return raw


def _base(
    verified: dict[str, Any],
    *,
    created: int,
    activation: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "artifact_version": 1,
        "role": "v24218_exact220_executor_watcher_state",
        "created_at_unix": created,
        "protocol": {
            "path": str(OUTPUT),
            "sha256": verified["sha256"],
            "decision_contract_sha256": verified["value"]["decision_contract_sha256"],
            "control_manifest_sha256": verified["value"]["control_surface"]["manifest_sha256"],
        },
        "execution_activation": activation,
        "package_parent_safe_envelope_opened": False,
        "package_parent_go_validated": False,
        "capacity_parent_safe_envelope_opened": False,
        "capacity_parent_go_validated": False,
        "active_api_workers": None,
        "consecutive_quiet_observations": 0,
        "shared_api_lease_acquired": False,
        "lease_compatibility_valid": False,
        "execution_start_published": False,
        "candidate_package_opened": False,
        "capacity_report_or_freeze_opened": False,
        "materialization_created": False,
        "fresh_candidate_roots_created": False,
        "preflight_model_search_api_called": False,
        "benchmark_forward_called": False,
        "all_four_shards_exact_terminal": False,
        "mapping_or_evaluator_opened": False,
        "official_evaluator_called": False,
        "result_created": False,
        "runtime_forward_inputs_exactly_opaque_id_and_question": True,
        "benchmark_category_question_type_split_mapping_gold_answer_evaluator_score_used_for_forward_routing": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        "existing_benchmark_or_watcher_signaled_restarted_modified_or_terminated": False,
        "leaderboard_submission_or_sota_claim": False,
        "terminal": False,
    }


def _seal_state(path: Path, value: dict[str, Any]) -> None:
    value.pop("state_payload_sha256", None)
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
    *,
    verified: dict[str, Any],
    activation: dict[str, Any],
    package: Mapping[str, Any],
    capacity: Mapping[str, Any],
    lease: Mapping[str, Any],
    created: int,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24218_exact220_execution_start",
        "created_at_unix": created,
        "protocol": {"path": str(OUTPUT), "sha256": verified["sha256"]},
        "execution_activation": {
            "path": str(ACTIVATION),
            "sha256": activation["sha256"],
            "watcher_pid": activation["watcher_pid"],
            "watcher_start_ticks": activation["watcher_start_ticks"],
        },
        "package_state": package["package_state"],
        "package_publication": package["publication"],
        "package_gate_decision": package["gate_decision"],
        "package_mode": package["mode"],
        "package_source_manifest_sha256": package["source_manifest_sha256"],
        "capacity_state": capacity["state"],
        "capacity_report": capacity["report"],
        "capacity_freeze": capacity["freeze"],
        "schedule": capacity["schedule"],
        "shared_api_lease": dict(lease),
        "all_future_candidate_roots_and_artifacts_absent_before_start": True,
        "runtime_boundary": ["opaque_id", "question"],
        "mapping_evaluator_gold_category_question_type_score_unavailable_to_forward": True,
        "fresh_exact220_forward_authorized": True,
        "resume_or_selective_rerun_allowed": False,
        "failure_as_zero": True,
        "leaderboard_submission_or_sota_claim": False,
    }
    value["execution_start_payload_sha256"] = payload_sha256(value)
    return value


def _validate_execution_start(
    root: Path,
    *,
    verified: dict[str, Any],
    activation: dict[str, Any],
    package: Mapping[str, Any],
    capacity: Mapping[str, Any],
) -> dict[str, Any]:
    value = read_object(root / EXECUTION_START)
    lease = value.get("shared_api_lease")
    created = value.get("created_at_unix")
    if (
        not isinstance(lease, dict)
        or lease.get("owner") != LEASE_OWNER
        or lease.get("purpose") != LEASE_PURPOSE
        or lease.get("watcher_pid") != activation["watcher_pid"]
        or lease.get("watcher_start_ticks") != activation["watcher_start_ticks"]
        or lease.get("owner_purpose_pid_and_lock_holder_exact") is not True
        or lease.get("contents_emitted") is not False
        or isinstance(created, bool)
        or not isinstance(created, int)
    ):
        raise RuntimeError("V2.42.18 execution-start lease identity drifted")
    expected = _execution_start(
        verified=verified,
        activation=activation,
        package=package,
        capacity=capacity,
        lease=lease,
        created=created,
    )
    if value != expected:
        raise RuntimeError("V2.42.18 execution start differs from live binding")
    return value


def _future_run_absent(root: Path) -> bool:
    paths = (MATERIALIZATION, FORWARD_BARRIER, PREPARE_ROOT, EVALUATOR_ROOT, SUMMARY, RESULT)
    return all(not _present(root, path) for path in paths) and all(
        not path.exists() and not path.is_symlink() for path in SHARD_ROOTS.values()
    )


def run_cycle(
    root: Path = ROOT,
    *,
    protocol_path: Path = OUTPUT,
    state_path: Path = STATE,
    proc_root: Path = Path("/proc"),
    now: int | None = None,
    lease_factory: Callable[..., Any] = acquire_deepwide_api_lease,
    executor: Callable[..., dict[str, Any]] = run_exact220,
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve() or proc_root.resolve() != Path("/proc"):
        raise RuntimeError("V2.42.18 canonical execution boundary drifted")
    verified = validate_protocol(root, protocol_path)
    target = state_path if state_path.is_absolute() else root / state_path
    created = int(time.time()) if now is None else int(now)
    activation = _activation(root, verified["sha256"])
    value = _base(verified, created=created, activation=activation)
    start_present = _present(root, EXECUTION_START)
    result_present = _present(root, RESULT)
    if activation is None:
        if start_present or not _future_run_absent(root):
            raise RuntimeError("V2.42.18 execution side effect appeared before activation")
        _phase(target, value, status="waiting_for_execution_activation", reason="activation_absent")
        return value

    package_state, package_mode = _package_parent(root)
    value["package_parent_safe_envelope_opened"] = True
    value["package_parent"] = {
        "path": str(PARENT_PACKAGE_STATE),
        "status": package_state.get("status"),
        "terminal": package_state.get("terminal"),
        "contents_emitted": False,
    }
    if package_mode == "waiting":
        if start_present or not _future_run_absent(root):
            raise RuntimeError("V2.42.18 side effect appeared before package terminal")
        _phase(
            target,
            value,
            status="waiting_for_v24216_package_gate_terminal",
            reason="package_parent_preterminal",
        )
        return value
    if package_mode == "no_go":
        if start_present or not _future_run_absent(root):
            raise RuntimeError("V2.42.18 side effect appeared after package NO-GO")
        _phase(
            target,
            value,
            status="terminal_parent_package_no_go",
            reason="package_gate_did_not_authorize_capacity_or_exact220",
            terminal=True,
        )
        return value
    value["package_parent_go_validated"] = True

    capacity_state, capacity_mode = _capacity_parent(root)
    value["capacity_parent_safe_envelope_opened"] = True
    value["capacity_parent"] = {
        "path": str(PARENT_CAPACITY_STATE),
        "status": capacity_state.get("status"),
        "terminal": capacity_state.get("terminal"),
        "contents_emitted": False,
    }
    if capacity_mode == "waiting":
        if start_present or not _future_run_absent(root):
            raise RuntimeError("V2.42.18 side effect appeared before capacity terminal")
        _phase(
            target,
            value,
            status="waiting_for_v24217_capacity_freeze",
            reason="capacity_parent_preterminal",
        )
        return value
    if capacity_mode == "no_go":
        if start_present or not _future_run_absent(root):
            raise RuntimeError("V2.42.18 side effect appeared after capacity NO-GO")
        _phase(
            target,
            value,
            status="terminal_parent_capacity_no_go",
            reason="capacity_ladder_did_not_authorize_exact220",
            terminal=True,
        )
        return value
    value["capacity_parent_go_validated"] = True

    package = validate_package_authority(root)
    capacity = validate_capacity_authority(package, root)
    value["candidate_package_opened"] = True
    value["capacity_report_or_freeze_opened"] = True
    value["schedule"] = capacity["schedule"]
    if result_present:
        if not start_present:
            raise RuntimeError("V2.42.18 result exists without execution start")
        _validate_execution_start(
            root,
            verified=verified,
            activation=activation,
            package=package,
            capacity=capacity,
        )
        result = validate_result(package, capacity, root=root)
        _phase(
            target,
            value,
            status="complete_exact220_local_result_released_not_sota",
            reason="existing_result_live_replay_valid",
            terminal=True,
            execution_start_published=True,
            materialization_created=True,
            fresh_candidate_roots_created=True,
            preflight_model_search_api_called=True,
            benchmark_forward_called=True,
            all_four_shards_exact_terminal=True,
            mapping_or_evaluator_opened=True,
            official_evaluator_called=True,
            result_created=True,
            result={"path": str(RESULT), "sha256": file_sha256(root / RESULT)},
            selected=result["selected"],
            runtime_completed=result["runtime_completed"],
            runtime_failed=result["runtime_failed"],
        )
        return value
    if start_present:
        _validate_execution_start(
            root,
            verified=verified,
            activation=activation,
            package=package,
            capacity=capacity,
        )
        _phase(
            target,
            value,
            status="terminal_incomplete_exact220_attempt_no_retry",
            reason="execution_start_exists_without_sealed_result",
            terminal=True,
            execution_start_published=True,
            materialization_created=_present(root, MATERIALIZATION),
            fresh_candidate_roots_created=any(path.exists() for path in SHARD_ROOTS.values()),
            preflight_model_search_api_called=None,
            benchmark_forward_called=None,
            mapping_or_evaluator_opened=None,
            official_evaluator_called=None,
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
    required = int(verified["value"]["execution"]["quiet_observations_before_lease"])
    streak = previous + 1
    value["consecutive_quiet_observations"] = streak
    if streak < required:
        _phase(
            target,
            value,
            status="waiting_for_second_quiet_observation",
            reason="exact220_requires_consecutive_quiet_observations",
        )
        return value

    if not _future_run_absent(root):
        raise RuntimeError("V2.42.18 future run path appeared before execution start")
    try:
        with lease_factory(root, owner=LEASE_OWNER, purpose=LEASE_PURPOSE) as lease:
            value["shared_api_lease_acquired"] = True
            if _activation(root, verified["sha256"]) != activation:
                raise RuntimeError("V2.42.18 activation changed under lease")
            second_package_state, second_package_mode = _package_parent(root)
            second_capacity_state, second_capacity_mode = _capacity_parent(root)
            if (
                second_package_mode != "go"
                or second_capacity_mode != "go"
                or second_package_state != package_state
                or second_capacity_state != capacity_state
                or validate_package_authority(root) != package
                or validate_capacity_authority(package, root) != capacity
            ):
                raise RuntimeError("V2.42.18 parent authority changed under lease")
            second_workers = _active_api_workers(proc_root)
            if second_workers["present"]:
                raise RuntimeError("V2.42.18 API worker appeared under lease")
            if not _future_run_absent(root):
                raise RuntimeError("V2.42.18 future run path appeared under lease")
            compatibility = _lease_compatibility(
                root, activation=activation, lease=lease, proc_root=proc_root
            )
            value["lease_compatibility_valid"] = True
            value["lease_compatibility"] = compatibility
            start = _execution_start(
                verified=verified,
                activation=activation,
                package=package,
                capacity=capacity,
                lease=compatibility,
                created=created,
            )
            publish_new(root / EXECUTION_START, start)
            value["execution_start_published"] = True
            _validate_execution_start(
                root,
                verified=verified,
                activation=activation,
                package=package,
                capacity=capacity,
            )
            _phase(
                target,
                value,
                status="running_fresh_exact220",
                reason="both_parent_go_quiet_lease_and_start_valid",
                shared_api_lease_acquired=True,
                lease_compatibility_valid=True,
                execution_start_published=True,
            )

            def phase(name: str, updates: Mapping[str, Any]) -> None:
                translated = dict(updates)
                if name == "materialized_all_four_fresh_roots":
                    translated["fresh_candidate_roots_created"] = True
                if name == "running_preflight_wave":
                    translated["preflight_model_search_api_called"] = True
                if name == "running_forward_wave":
                    translated["benchmark_forward_called"] = True
                if name == "all_shards_terminal_mapping_gate_open":
                    translated["all_four_shards_exact_terminal"] = True
                if name == "released_evaluator_terminal":
                    translated.update(
                        all_four_shards_exact_terminal=True,
                        mapping_or_evaluator_opened=True,
                    )
                _phase(
                    target,
                    value,
                    status=name,
                    reason="authorized_single_owner_execution_progress",
                    shared_api_lease_acquired=True,
                    lease_compatibility_valid=True,
                    execution_start_published=True,
                    **translated,
                )

            result = executor(package, capacity, root=root, phase=phase)
            value.update(
                status="complete_exact220_local_result_released_not_sota",
                reason="fresh_exact220_and_released_evaluator_terminal",
                terminal=True,
                materialization_created=True,
                fresh_candidate_roots_created=True,
                preflight_model_search_api_called=True,
                benchmark_forward_called=True,
                all_four_shards_exact_terminal=True,
                mapping_or_evaluator_opened=True,
                official_evaluator_called=True,
                result_created=True,
                result={"path": str(RESULT), "sha256": file_sha256(root / RESULT)},
                selected=result["selected"],
                runtime_completed=result["runtime_completed"],
                runtime_failed=result["runtime_failed"],
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
        raise RuntimeError("V2.42.18 watcher parameters drifted")
    while True:
        try:
            value = run_cycle(
                Path(args.root),
                protocol_path=Path(args.protocol),
                state_path=Path(args.state),
                proc_root=Path(args.proc_root),
            )
        except Exception as exc:
            try:
                verified = validate_protocol(Path(args.root), Path(args.protocol))
                activation = _activation(Path(args.root), verified["sha256"])
                value = _base(verified, created=int(time.time()), activation=activation)
                run_root = Path(args.root)
                start_present = _present(run_root, EXECUTION_START)
                materialized = _present(run_root, MATERIALIZATION)
                roots_present = any(
                    path.exists() or path.is_symlink() for path in SHARD_ROOTS.values()
                )
                barrier_present = _present(run_root, FORWARD_BARRIER)
                prepare_present = _present(run_root, PREPARE_ROOT)
                evaluator_present = _present(run_root, EVALUATOR_ROOT)
                result_present = _present(run_root, RESULT)
                value.update(
                    status="terminal_fail_closed_no_retry",
                    reason=type(exc).__name__,
                    terminal=True,
                    execution_start_published=start_present,
                    materialization_created=materialized,
                    fresh_candidate_roots_created=roots_present,
                    preflight_model_search_api_called=(None if start_present else False),
                    benchmark_forward_called=(None if start_present else False),
                    all_four_shards_exact_terminal=barrier_present,
                    mapping_or_evaluator_opened=prepare_present or evaluator_present,
                    official_evaluator_called=(None if evaluator_present else False),
                    result_created=result_present,
                )
                _seal_state(Path(args.root) / Path(args.state), value)
            except Exception:
                raise exc
        print(
            json.dumps(
                {
                    "role": value["role"],
                    "created_at_unix": value["created_at_unix"],
                    "status": value["status"],
                    "reason": value["reason"],
                    "execution_start_published": value["execution_start_published"],
                    "benchmark_forward_called": value["benchmark_forward_called"],
                    "result_created": value["result_created"],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        if args.once or value["terminal"]:
            return
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
