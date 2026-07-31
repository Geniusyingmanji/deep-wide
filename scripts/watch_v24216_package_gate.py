#!/usr/bin/env python3
"""Wait safely, then execute the V2.42.16 paired package gate."""

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
PROTOCOL = Path("results/v24216_package_gate_preregistration_v1_20260731.json")
STATE = Path("outputs/v24216_package_gate_watcher_state_v1_20260731.json")


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
        raise RuntimeError("V2.42.16 watcher requires python -I -B")
    arguments = list(sys.argv[1:])

    def option(name: str, default: str) -> str:
        if name not in arguments:
            return default
        if arguments.count(name) != 1:
            raise RuntimeError(f"V2.42.16 option is not unique: {name}")
        index = arguments.index(name)
        if index + 1 >= len(arguments):
            raise RuntimeError(f"V2.42.16 option lacks a value: {name}")
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
        raise RuntimeError("V2.42.16 watcher execution drifted")
    value = json.loads(protocol.read_text(encoding="utf-8"))
    control = value.get("control_surface") or {}
    manifest = control.get("manifest")
    if (
        value.get("protocol_id")
        != "v24216_joint_package_paired_cold_same_dev64_gate_v1"
        or not isinstance(manifest, dict)
        or control.get("file_count") != len(manifest)
        or control.get("manifest_sha256") != _payload_sha(manifest)
    ):
        raise RuntimeError("V2.42.16 watcher protocol is invalid")
    for relative, digest in manifest.items():
        target = root / relative
        if (
            target.is_symlink()
            or not target.is_file()
            or hashlib.sha256(target.read_bytes()).hexdigest() != digest
        ):
            raise RuntimeError("V2.42.16 control bytes drifted")


_bootstrap()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24216_package_gate import payload_sha256  # noqa: E402
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
from scripts.preregister_v24210_search_component import read_object, sha256  # noqa: E402
from scripts.preregister_v24216_package_gate import (  # noqa: E402
    ACTIVATION,
    BASELINE_RESULT,
    CANDIDATE_RESULT,
    FORWARD_BARRIER,
    GATE_DECISION,
    LEASE_OWNER,
    LEASE_PURPOSE,
    OUTPUT,
    PAIR_PREPARE,
    PARENT_PROTOCOL_SHA256,
    PARENT_PUBLICATION,
    PARENT_STATE,
    R1_STATE,
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
from scripts.run_v24216_package_gate import (  # noqa: E402
    ARM_ROOTS,
    _evaluate_arm,
    _existing_arm_evaluator,
    prepare_pair,
    publish_forward_barrier,
    publish_gate_from_results,
    run_forward_arm,
    terminal_arm,
    validate_forward_barrier,
    validate_gate_decision,
    validate_pair_prepare,
    validate_parent_publication,
)


PARENT_PRETERMINAL = {"waiting_for_v24213_entropy_recovery_terminal"}
PARENT_TERMINAL = {
    "complete_selected_baseline_identity_handoff_recovered",
    "complete_joint_package_recovery_revalidated",
}
TERMINAL_STATUSES = {
    "complete_identity_handoff_no_package_gate_required",
    "complete_package_gate_go",
    "complete_package_gate_no_go",
    "critical_package_gate_execution_failed_no_retry",
}


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


def _present(root: Path, path: Path) -> bool:
    target = root / path
    return target.exists() or target.is_symlink()


def _activation(root: Path, protocol_sha: str) -> dict[str, Any] | None:
    if not _present(root, ACTIVATION):
        return None
    from scripts.activate_v24216_package_gate import validate_activation

    verified = validate_activation(root, ACTIVATION, protocol_path=OUTPUT)
    if verified["value"]["protocol"]["sha256"] != protocol_sha:
        raise RuntimeError("V2.42.16 activation binding drifted")
    return {
        "path": str(ACTIVATION),
        "sha256": verified["sha256"],
        "watcher_pid": verified["value"]["watcher"]["pid"],
        "watcher_start_ticks": verified["value"]["watcher"]["start_ticks"],
    }


def _parent_state(root: Path) -> tuple[dict[str, Any], bool]:
    state = read_object(root / PARENT_STATE)
    unsigned = dict(state)
    seal = unsigned.pop("state_payload_sha256", None)
    false_fields = (
        "package_gate_evaluated_or_launched",
        "dev64_launch_allowed",
        "shared_api_lease_acquired",
        "network_model_search_fetch_evaluator_or_api_called",
        "mapping_gold_category_question_type_evaluator_score_or_reward_read",
        "process_signal_restart_resume_rerun_skip_or_selective_retry",
        "benchmark_forward_or_full220_launch_allowed",
        "leaderboard_submission_or_sota_claim",
    )
    terminal = state.get("terminal")
    status = state.get("status")
    if (
        state.get("role") != "v24215_selected_joint_package_recovery_state"
        or state.get("protocol", {}).get("sha256") != PARENT_PROTOCOL_SHA256
        or terminal not in {True, False}
        or any(state.get(field) is not False for field in false_fields)
        or seal != payload_sha256(unsigned)
        or terminal is False
        and (
            status not in PARENT_PRETERMINAL
            or state.get("selected_work_order_opened") is not False
            or state.get("joint_package_publication_created") is not False
        )
        or terminal is True
        and (
            status not in PARENT_TERMINAL
            or state.get("joint_package_publication_created") is not True
        )
    ):
        raise RuntimeError("V2.42.16 parent safe envelope drifted")
    return state, bool(terminal)


def _r1_release_envelope(root: Path) -> dict[str, Any] | None:
    state = read_object(root / R1_STATE)
    aggregate = state.get("aggregate") or {}
    if state.get("role") != "v24118_r1_finalization_watchdog_state":
        raise RuntimeError("V2.42.16 R1 release envelope role drifted")
    if state.get("status") == "waiting_for_r1_exact_terminal_220":
        if (
            aggregate.get("selected") != 220
            or aggregate.get("exact_terminal_220") is not False
            or state.get("mapping_or_gold_read") is not False
            or state.get("evaluator_or_score_read") is not False
        ):
            raise RuntimeError("V2.42.16 R1 wait envelope drifted")
        return None
    if state.get("status") not in {
        "complete_existing_release_pair",
        "complete_recovered_release_pair",
    }:
        raise RuntimeError("V2.42.16 R1 terminal status is unregistered")
    released = state.get("released_artifacts") or {}
    if (
        released.get("complete_pair") is not True
        or released.get("partial_pair") is not False
        or released.get("noncanonical") is not False
        or state.get("mapping_or_gold_read") is not True
        or state.get("evaluator_or_score_read") is not True
        or state.get("leaderboard_submission_performed") is not False
        or state.get("sota_claim") is not False
    ):
        raise RuntimeError("V2.42.16 R1 release envelope drifted")
    return {
        "path": str(R1_STATE),
        "status": state["status"],
        "result_kind": released.get("result_kind"),
        "seal_kind": released.get("seal_kind"),
        "contents_emitted": False,
    }


def _process_present(marker: str, *, proc_root: Path) -> bool:
    matches = []
    for row in process_snapshot(proc_root):
        argv = [str(value) for value in row.get("argv") or []]
        from scripts.audit_v24187_phase_liveness import actual_python_script

        script = actual_python_script(argv)
        if script is not None and (script == marker or script.endswith("/" + marker)):
            matches.append(row)
    return len(matches) == 1


def _capacity_priority(root: Path, *, proc_root: Path) -> dict[str, Any]:
    if not _process_present(V24194_MARKER, proc_root=proc_root) or not _process_present(
        V24196_MARKER, proc_root=proc_root
    ):
        raise RuntimeError("V2.42.16 protected capacity watcher disappeared")
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
        or v96.get("protected_legacy_capacity_watcher", {}).get("present") is not True
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
        raise RuntimeError("V2.42.16 package-gate-before-capacity order drifted")
    return {
        "v24194_status": v94.get("status"),
        "v24196_status": v96.get("status"),
        "capacity_execution_activation_report_and_freezes_absent": True,
        "protected_watchers_present": True,
        "contents_emitted": False,
    }


def _lease_compatibility(
    root: Path,
    *,
    activation: dict[str, Any],
    lease: dict[str, Any],
    proc_root: Path,
) -> dict[str, Any]:
    processes = process_snapshot(proc_root)
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
        raise RuntimeError("V2.42.16 live lease identity drifted")
    parent = build_v24187_report(root, proc_root=proc_root, processes=processes)
    compatibility = build_v24195_report(
        root,
        proc_root=proc_root,
        processes=processes,
        observed_lease=observed,
    )
    parent_expected = ["shared_api_lease_identity"]
    compatibility_expected = sorted(
        ["shared_api_lease_identity", "v24195:unknown_lease_owner"]
    )
    if (
        parent.get("critical_findings") != parent_expected
        or compatibility.get("critical_findings") != compatibility_expected
        or compatibility.get("compatibility", {}).get("mode")
        != "unknown_lease_owner_active"
        or compatibility.get("compatibility", {}).get(
            "unrelated_parent_critical_findings_preserved"
        )
        is not True
    ):
        raise RuntimeError("V2.42.16 compatibility has unrelated findings")
    return {
        "lease_owner_purpose_pid_and_kernel_holder_exact": True,
        "v24187_suppressed_expected_findings": parent_expected,
        "v24195_suppressed_expected_findings": compatibility_expected,
        "unrelated_findings": [],
        "parent_audit_payload_sha256": parent["audit_payload_sha256"],
        "compatibility_audit_payload_sha256": compatibility[
            "audit_payload_sha256"
        ],
        "contents_emitted": False,
    }


def _execution_outputs_absent(root: Path) -> bool:
    return all(
        not _present(root, path)
        for path in (
            PAIR_PREPARE,
            FORWARD_BARRIER,
            BASELINE_RESULT,
            CANDIDATE_RESULT,
            GATE_DECISION,
        )
    ) and all(not path.exists() and not path.is_symlink() for path in ARM_ROOTS.values())


def _base(
    verified: dict[str, Any],
    *,
    created: int,
    activation: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "artifact_version": 1,
        "role": "v24216_package_gate_watcher_state",
        "created_at_unix": created,
        "protocol": {
            "path": str(OUTPUT),
            "sha256": verified["sha256"],
            "decision_contract_sha256": verified["value"][
                "decision_contract_sha256"
            ],
            "control_manifest_sha256": verified["value"]["control_surface"][
                "manifest_sha256"
            ],
        },
        "execution_activation": activation,
        "parent_safe_state_envelope_opened": False,
        "parent_publication_opened": False,
        "r1_release_envelope_opened": False,
        "capacity_priority_rechecked": False,
        "paired_roots_materialized": False,
        "historical_baseline_result_reused": False,
        "baseline_forward_called": False,
        "candidate_forward_called": False,
        "both_forward_arms_exact_terminal_before_mapping": False,
        "mapping_or_evaluator_opened": False,
        "baseline_evaluator_called": False,
        "candidate_evaluator_called": False,
        "package_gate_evaluated": False,
        "package_gate_passed": False,
        "capacity_measurement_allowed": False,
        "all220_freeze_design_allowed": False,
        "shared_api_lease_acquired": False,
        "lease_compatibility_valid": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "runtime_forward_inputs_exactly_opaque_id_and_question": True,
        "mapping_gold_category_question_type_or_per_task_score_used_for_forward_routing": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
        "terminal": False,
    }


def _seal_and_write(path: Path, value: dict[str, Any]) -> None:
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
    _seal_and_write(path, value)


def _arm_result_present(root: Path, arm: str) -> bool:
    return _present(root, BASELINE_RESULT if arm == "baseline" else CANDIDATE_RESULT)


def run_cycle(
    root: Path = ROOT,
    *,
    protocol_path: Path = OUTPUT,
    state_path: Path = STATE,
    proc_root: Path = Path("/proc"),
    now: int | None = None,
    lease_factory: Callable[..., Any] = acquire_deepwide_api_lease,
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve() or proc_root.resolve() != Path("/proc"):
        raise RuntimeError("V2.42.16 canonical execution boundary drifted")
    verified = validate_protocol(root, protocol_path)
    target = state_path if state_path.is_absolute() else root / state_path
    created = int(time.time()) if now is None else int(now)
    activation = _activation(root, verified["sha256"])
    value = _base(verified, created=created, activation=activation)
    if activation is None:
        if not _execution_outputs_absent(root):
            raise RuntimeError("V2.42.16 execution output appeared before activation")
        _phase(
            target,
            value,
            status="waiting_for_execution_activation",
            reason="activation_absent",
        )
        return value

    parent, terminal = _parent_state(root)
    value["parent_safe_state_envelope_opened"] = True
    value["parent_state"] = {
        "path": str(PARENT_STATE),
        "status": parent["status"],
        "terminal": terminal,
        "contents_emitted": False,
    }
    if not terminal:
        if not _execution_outputs_absent(root):
            raise RuntimeError("V2.42.16 execution output appeared before parent terminal")
        _phase(
            target,
            value,
            status="waiting_for_v24215_joint_package_terminal",
            reason="parent_preterminal",
        )
        return value

    publication = validate_parent_publication(root)
    value["parent_publication_opened"] = True
    order = publication["joint_package_order"]
    release = _r1_release_envelope(root)
    value["r1_release_envelope_opened"] = True
    if release is None:
        if not _execution_outputs_absent(root):
            raise RuntimeError("V2.42.16 execution output appeared before R1 release")
        _phase(
            target,
            value,
            status="waiting_for_r1_exact220_release",
            reason="r1_release_pair_absent",
        )
        return value
    value["r1_release"] = release
    priority = _capacity_priority(root, proc_root=proc_root)
    value["capacity_priority_rechecked"] = True
    value["capacity_priority"] = priority

    if bool(publication["identity_handoff_only"]):
        if not _execution_outputs_absent(root):
            raise RuntimeError("V2.42.16 identity handoff has unexpected gate output")
        _phase(
            target,
            value,
            status="complete_identity_handoff_no_package_gate_required",
            reason="empty_component_set_uses_selected_baseline_identity_after_release_and_priority_recheck",
            terminal=True,
            capacity_measurement_allowed=True,
            all220_freeze_design_allowed=True,
            identity_handoff_only=True,
            selected_baseline=order["baseline_name"],
        )
        return value

    if not _present(root, PAIR_PREPARE):
        if any(path.exists() or path.is_symlink() for path in ARM_ROOTS.values()):
            raise RuntimeError("V2.42.16 unsealed arm root appeared")
        prepare_pair(publication, root=root)
    prepare = validate_pair_prepare(root)
    value["paired_roots_materialized"] = True
    value["pair_prepare"] = {
        "path": str(PAIR_PREPARE),
        "sha256": sha256(root / PAIR_PREPARE),
        "contents_emitted": False,
    }

    if _present(root, GATE_DECISION):
        gate = validate_gate_decision(root)
        passed = bool(gate["passed"])
        _phase(
            target,
            value,
            status="complete_package_gate_go" if passed else "complete_package_gate_no_go",
            reason="existing_gate_live_replay_valid",
            terminal=True,
            package_gate_evaluated=True,
            package_gate_passed=passed,
            capacity_measurement_allowed=passed,
            all220_freeze_design_allowed=passed,
            baseline_forward_called=True,
            candidate_forward_called=True,
            baseline_evaluator_called=True,
            candidate_evaluator_called=True,
            network_model_search_fetch_evaluator_or_api_called=True,
            mapping_or_evaluator_opened=True,
            both_forward_arms_exact_terminal_before_mapping=True,
            gate_decision={
                "path": str(GATE_DECISION),
                "sha256": sha256(root / GATE_DECISION),
                "contents_emitted": False,
            },
        )
        return value

    try:
        with lease_factory(
            root,
            owner=LEASE_OWNER,
            purpose=LEASE_PURPOSE,
        ) as lease:
            value["shared_api_lease_acquired"] = True
            live_activation = _activation(root, verified["sha256"])
            if live_activation != activation:
                raise RuntimeError("V2.42.16 activation changed under lease")
            if validate_parent_publication(root) != publication:
                raise RuntimeError("V2.42.16 parent publication changed under lease")
            if _r1_release_envelope(root) != release:
                raise RuntimeError("V2.42.16 R1 release changed under lease")
            if _capacity_priority(root, proc_root=proc_root) != priority:
                raise RuntimeError("V2.42.16 capacity priority changed under lease")
            compatibility = _lease_compatibility(
                root,
                activation=activation,
                lease=lease,
                proc_root=proc_root,
            )
            value["lease_compatibility_valid"] = True
            value["lease_compatibility"] = compatibility

            baseline_terminal = terminal_arm("baseline")
            if baseline_terminal is None:
                _phase(
                    target,
                    value,
                    status="running_baseline_exact_dev64",
                    reason="fixed_first_arm",
                    shared_api_lease_acquired=True,
                    lease_compatibility_valid=True,
                    baseline_forward_called=True,
                    network_model_search_fetch_evaluator_or_api_called=True,
                )
                baseline_terminal = run_forward_arm("baseline")
            value["baseline_forward_called"] = True
            value["network_model_search_fetch_evaluator_or_api_called"] = True

            candidate_terminal = terminal_arm("candidate")
            if candidate_terminal is None:
                _phase(
                    target,
                    value,
                    status="running_candidate_exact_dev64",
                    reason="fixed_second_arm_independent_of_baseline_outcome",
                    shared_api_lease_acquired=True,
                    lease_compatibility_valid=True,
                    baseline_forward_called=True,
                    candidate_forward_called=True,
                    network_model_search_fetch_evaluator_or_api_called=True,
                )
                candidate_terminal = run_forward_arm("candidate")
            value["candidate_forward_called"] = True
            if not _present(root, FORWARD_BARRIER):
                publish_forward_barrier(root)
            barrier = validate_forward_barrier(root)
            value["both_forward_arms_exact_terminal_before_mapping"] = True
            value["forward_barrier"] = {
                "path": str(FORWARD_BARRIER),
                "sha256": sha256(root / FORWARD_BARRIER),
                "contents_emitted": False,
            }

            if not _arm_result_present(root, "baseline"):
                _phase(
                    target,
                    value,
                    status="evaluating_baseline_after_both_forward_terminal",
                    reason="mapping_barrier_open",
                    shared_api_lease_acquired=True,
                    lease_compatibility_valid=True,
                    baseline_forward_called=True,
                    candidate_forward_called=True,
                    both_forward_arms_exact_terminal_before_mapping=True,
                    mapping_or_evaluator_opened=True,
                    baseline_evaluator_called=True,
                    network_model_search_fetch_evaluator_or_api_called=True,
                )
                _evaluate_arm("baseline", root=root)
            else:
                _existing_arm_evaluator("baseline", root=root)
            value["mapping_or_evaluator_opened"] = True
            value["baseline_evaluator_called"] = True

            if not _arm_result_present(root, "candidate"):
                _phase(
                    target,
                    value,
                    status="evaluating_candidate_after_both_forward_terminal",
                    reason="fixed_second_evaluator",
                    shared_api_lease_acquired=True,
                    lease_compatibility_valid=True,
                    baseline_forward_called=True,
                    candidate_forward_called=True,
                    both_forward_arms_exact_terminal_before_mapping=True,
                    mapping_or_evaluator_opened=True,
                    baseline_evaluator_called=True,
                    candidate_evaluator_called=True,
                    network_model_search_fetch_evaluator_or_api_called=True,
                )
                _evaluate_arm("candidate", root=root)
            else:
                _existing_arm_evaluator("candidate", root=root)
            value["candidate_evaluator_called"] = True
            if not _present(root, GATE_DECISION):
                publish_gate_from_results(publication, root=root)
            gate = validate_gate_decision(root)
            passed = bool(gate["passed"])
            value.update(
                status="complete_package_gate_go" if passed else "complete_package_gate_no_go",
                reason="paired_cold_same_dev64_gate_terminal",
                terminal=True,
                package_gate_evaluated=True,
                package_gate_passed=passed,
                capacity_measurement_allowed=passed,
                all220_freeze_design_allowed=passed,
                gate_decision={
                    "path": str(GATE_DECISION),
                    "sha256": sha256(root / GATE_DECISION),
                    "contents_emitted": False,
                },
            )
    except DeepWideApiLeaseBusy as exc:
        value.update(
            status="waiting_for_shared_api_lease",
            reason=type(exc).__name__,
            shared_api_lease_acquired=False,
        )
    _seal_and_write(target, value)
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
        raise RuntimeError("V2.42.16 watcher parameters drifted")
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
                value = _base(
                    verified,
                    created=int(time.time()),
                    activation=activation,
                )
                value.update(
                    status="critical_package_gate_execution_failed_no_retry",
                    reason=type(exc).__name__,
                    terminal=True,
                    failure_message_or_benchmark_content_emitted=False,
                )
                target = Path(args.state)
                if not target.is_absolute():
                    target = Path(args.root) / target
                _seal_and_write(target, value)
            except Exception:
                raise exc
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
