#!/usr/bin/env python3
"""Wait safely, then execute the frozen V2.41.94 neutral capacity ladder."""

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
PROTOCOL = Path("results/v24196_capacity_executor_preregistration_v1_20260731.json")


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
        raise RuntimeError("V2.41.96 watcher requires python -I -B")
    arguments = list(sys.argv[1:])

    def option(name: str, default: str) -> str:
        if name not in arguments:
            return default
        if arguments.count(name) != 1:
            raise RuntimeError(f"V2.41.96 option is not unique: {name}")
        index = arguments.index(name)
        if index + 1 >= len(arguments):
            raise RuntimeError(f"V2.41.96 option lacks a value: {name}")
        return arguments[index + 1]

    root = Path(option("--root", str(ROOT))).resolve()
    raw = Path(option("--protocol", str(PROTOCOL)))
    protocol = raw if raw.is_absolute() else root / raw
    if (
        root != ROOT.resolve()
        or protocol.resolve(strict=False) != (root / PROTOCOL).resolve(strict=False)
        or protocol.is_symlink()
        or not protocol.is_file()
        or option("--poll-seconds", "60") != "60"
        or option("--proc-root", "/proc") != "/proc"
    ):
        raise RuntimeError("V2.41.96 watcher execution drifted")
    value = json.loads(protocol.read_text(encoding="utf-8"))
    control = value.get("control_surface") or {}
    manifest = control.get("manifest")
    if (
        value.get("protocol_id") != "v24196_v24194_capacity_executor_successor_v1"
        or not isinstance(manifest, dict)
        or control.get("file_count") != len(manifest)
        or control.get("manifest_sha256") != _payload_sha(manifest)
    ):
        raise RuntimeError("V2.41.96 watcher protocol is invalid")
    for relative, digest in manifest.items():
        target = root / relative
        if (
            target.is_symlink()
            or not target.is_file()
            or hashlib.sha256(target.read_bytes()).hexdigest() != digest
        ):
            raise RuntimeError("V2.41.96 control bytes drifted")


_bootstrap()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.clients import ResponsesClient  # noqa: E402
from deepwide_agent.v24194_capacity_ladder import (  # noqa: E402
    CAPACITY_REPORT_CORE_FIELDS,
    CAPACITY_REPORT_EXECUTION_FIELDS,
    ProbeSettings,
    build_capacity_freeze,
    payload_sha256,
    run_capacity_ladder,
    settings_from_dict,
    validate_capacity_report,
)
from scripts.activate_v24196_capacity_executor import (  # noqa: E402
    validate_activation,
)
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    build_report as build_parent_report,
    process_snapshot,
)
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    build_report as build_compatibility_report,
)
from scripts.deepwide_api_lease import (  # noqa: E402
    DeepWideApiLeaseBusy,
    acquire_deepwide_api_lease,
)
from scripts.preregister_v24195_lease_owner_compatibility import (  # noqa: E402
    EXPECTED_PARENT_FINDING,
)
from scripts.preregister_v24196_capacity_executor import (  # noqa: E402
    ACTIVATION,
    FREEZE,
    LEASE_OWNER,
    LEASE_PURPOSE,
    LEGACY_CAPACITY_WATCHER_MARKER,
    OUTPUT,
    REPORT,
    STATE,
    V24195_STATE,
    payload_sha,
    read_object,
    sha256,
    validate_protocol,
)
from scripts.watch_v24194_capacity_ladder import (  # noqa: E402
    _active_api_workers,
    _campaign_terminal,
    _release_pair,
)
from scripts.v24159_true_continuation_reachability import (  # noqa: E402
    process_report,
)


TERMINAL_STATUSES = frozenset(
    {
        "complete_capacity_recommendation_available",
        "terminal_capacity_no_go_serial_probe_failed",
        "critical_capacity_execution_failed",
    }
)


def _target(root: Path, raw: Path, expected: str, parent: str) -> Path:
    unresolved = raw if raw.is_absolute() else root / raw
    target = unresolved.resolve(strict=False)
    if (
        target != (root / expected).resolve(strict=False)
        or unresolved.is_symlink()
        or (root / parent).resolve() not in (target, *target.parents)
    ):
        raise RuntimeError("V2.41.96 output path is noncanonical")
    return target


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


def _previous_quiet_streak(path: Path, protocol_sha: str) -> int:
    if not path.exists() and not path.is_symlink():
        return 0
    value = read_object(path)
    if (
        value.get("role") != "v24196_capacity_executor_watcher_state"
        or value.get("protocol", {}).get("sha256") != protocol_sha
    ):
        raise RuntimeError("V2.41.96 previous state binding is invalid")
    streak = value.get("consecutive_quiet_observations", 0)
    if isinstance(streak, bool) or not isinstance(streak, int) or streak < 0:
        raise RuntimeError("V2.41.96 previous quiet streak is invalid")
    return streak


def _activation_summary(
    root: Path, protocol_path: Path, proc_root: Path
) -> dict[str, Any] | None:
    path = root / ACTIVATION
    if not path.exists() and not path.is_symlink():
        return None
    verified = validate_activation(
        root,
        ACTIVATION,
        protocol_path=protocol_path,
        proc_root=proc_root,
    )
    value = verified["value"]
    return {
        "path": str(ACTIVATION),
        "sha256": verified["sha256"],
        "activation_payload_sha256": value["activation_payload_sha256"],
        "executor_pid": value["executor"]["pid"],
        "executor_start_ticks": value["executor"]["start_ticks"],
        "registered_shared_lease_owner": LEASE_OWNER,
        "registered_shared_lease_purpose": LEASE_PURPOSE,
    }


def _legacy_capacity_watcher(proc_root: Path) -> dict[str, Any]:
    return process_report(
        process_snapshot(proc_root), LEGACY_CAPACITY_WATCHER_MARKER
    )


def _validate_report(
    report: dict[str, Any],
    *,
    protocol_sha: str,
    expected_settings: ProbeSettings,
) -> None:
    unsigned = dict(report)
    seal = unsigned.pop("report_payload_sha256", None)
    if (
        set(report) != CAPACITY_REPORT_CORE_FIELDS | CAPACITY_REPORT_EXECUTION_FIELDS
        or report.get("protocol")
        != {"path": str(OUTPUT), "sha256": protocol_sha}
        or report.get("role")
        != "v24194_neutral_gpt56_capacity_ladder_measurement"
        or not isinstance(report.get("r1_release"), dict)
        or not isinstance(report.get("quality_campaign_terminal"), dict)
        or not isinstance(report.get("execution_activation"), dict)
        or report.get("shared_api_lease_owner") != LEASE_OWNER
        or report.get("shared_api_lease_acquired") is not True
        or isinstance(report.get("created_at_unix"), bool)
        or not isinstance(report.get("created_at_unix"), int)
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.41.96 capacity report is invalid")
    validate_capacity_report(report, expected_settings=expected_settings)


def _validate_freeze(
    freeze: dict[str, Any],
    *,
    report: dict[str, Any],
    report_sha: str,
    protocol_sha: str,
) -> None:
    expected = build_capacity_freeze(
        report,
        report_path=str(REPORT),
        report_sha256=report_sha,
        protocol_path=str(OUTPUT),
        protocol_sha256=protocol_sha,
    )
    expected["freeze_payload_sha256"] = payload_sha256(expected)
    if freeze != expected:
        raise RuntimeError("V2.41.96 capacity freeze is invalid")


def _compatibility_valid(
    value: dict[str, Any], *, executor_pid: int
) -> bool:
    compatibility = value.get("compatibility") or {}
    parent = value.get("parent_v24187") or {}
    return bool(
        value.get("role") == "v24195_lease_owner_compatibility_audit"
        and value.get("overall_status")
        in {"healthy", "degraded_forward_healthy_manual_review_only"}
        and value.get("critical_findings") == []
        and compatibility.get("mode") == "registered_successor_active"
        and compatibility.get("successor_identity_valid") is True
        and compatibility.get("successor_identity_findings") == []
        and compatibility.get("successor_executor_pid") == executor_pid
        and compatibility.get("suppressed_expected_parent_findings")
        == [EXPECTED_PARENT_FINDING]
        and compatibility.get("unrelated_parent_critical_findings_preserved")
        is True
        and parent.get("critical_findings") == [EXPECTED_PARENT_FINDING]
        and value.get("authorization", {}).get("shared_api_lease_acquire") is False
        and value.get("authorization", {}).get("benchmark_forward_or_full220_launch")
        is False
    )


def _live_post_lease_compatibility(
    root: Path,
    *,
    proc_root: Path,
    executor_pid: int,
) -> dict[str, Any]:
    rows = process_snapshot(proc_root)
    parent = build_parent_report(root, proc_root=proc_root, processes=rows)
    current = parent.get("current_phase") or {}
    if (
        parent.get("critical_findings") != [EXPECTED_PARENT_FINDING]
        or current.get("phase") != "post_gate1_and_leaderboard_handoff"
        or current.get("terminal") is not True
        or current.get("valid") is not True
    ):
        raise RuntimeError("V2.41.96 live parent liveness is outside the lease envelope")
    compatibility = build_compatibility_report(
        root,
        proc_root=proc_root,
        processes=rows,
    )
    if not _compatibility_valid(compatibility, executor_pid=executor_pid):
        raise RuntimeError("V2.41.96 live compatibility audit did not authorize identity")
    return {
        "parent_audit_payload_sha256": parent["audit_payload_sha256"],
        "compatibility_audit_payload_sha256": compatibility[
            "audit_payload_sha256"
        ],
        "phase": current["phase"],
        "terminal": True,
        "valid": True,
        "parent_expected_owner_finding_only": True,
        "compatibility_valid": True,
    }


def _wait_for_compatibility_watcher(
    root: Path,
    *,
    acquired_at_unix: int,
    executor_pid: int,
    timeout_seconds: int,
    sleeper: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    deadline = monotonic() + timeout_seconds
    while True:
        path = root / V24195_STATE
        if path.is_file() and not path.is_symlink():
            value = read_object(path)
            unsigned = dict(value)
            seal = unsigned.pop("audit_payload_sha256", None)
            if (
                int(value.get("created_at_unix", -1)) >= acquired_at_unix
                and seal == payload_sha(unsigned)
                and _compatibility_valid(value, executor_pid=executor_pid)
            ):
                return {
                    "path": str(V24195_STATE),
                    "sha256": sha256(path),
                    "audit_payload_sha256": seal,
                    "created_at_unix": value["created_at_unix"],
                    "successor_executor_pid": executor_pid,
                    "registered_successor_active": True,
                    "contents_emitted": False,
                }
        if monotonic() >= deadline:
            raise RuntimeError("V2.41.96 timed out waiting for V2.41.95 observation")
        sleeper(1.0)


def _base_state(
    verified: dict[str, Any],
    *,
    created: int,
    release: dict[str, Any] | None,
    campaign: dict[str, Any] | None,
    workers: dict[str, Any],
    legacy_watcher: dict[str, Any],
    activation: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "artifact_version": 1,
        "role": "v24196_capacity_executor_watcher_state",
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
        "r1_release": release,
        "quality_campaign_terminal": campaign,
        "active_api_workers": workers,
        "protected_legacy_capacity_watcher": legacy_watcher,
        "execution_activation": activation,
        "consecutive_quiet_observations": 0,
        "shared_api_lease_acquired": False,
        "v24195_live_compatibility_valid": False,
        "v24195_watcher_observation_valid": False,
        "neutral_capacity_model_api_called": False,
        "benchmark_question_prediction_mapping_gold_category_evaluator_score_read": False,
        "runtime_task_state_answer_evidence_or_url_opened": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "search_fetch_or_evaluator_api_called": False,
        "response_text_or_response_id_persisted": False,
        "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        "current_r1_or_quality_chain_forward_config_changed": False,
        "full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
        "terminal": False,
    }


def run_cycle(
    root: Path,
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
    if root != ROOT.resolve():
        raise RuntimeError("V2.41.96 may only run in the canonical workspace")
    verified = validate_protocol(root, protocol_path)
    protocol = verified["value"]
    execution = protocol["execution"]
    settings = settings_from_dict(protocol["capacity_contract"]["settings"])
    if proc_root.resolve() != Path(execution["proc_root"]).resolve():
        raise RuntimeError("V2.41.96 proc root differs from protocol")
    state_target = _target(root, state_path, execution["state_path"], "outputs")
    report_target = _target(
        root, Path(execution["report_path"]), execution["report_path"], "results"
    )
    freeze_target = _target(
        root, Path(execution["freeze_path"]), execution["freeze_path"], "results"
    )
    created = int(time.time()) if now is None else int(now)
    release = _release_pair(root)
    campaign = _campaign_terminal(root)
    workers = _active_api_workers(
        proc_root, list(execution["active_api_worker_markers"])
    )
    legacy_watcher = _legacy_capacity_watcher(proc_root)
    activation = _activation_summary(root, protocol_path, proc_root)
    value = _base_state(
        verified,
        created=created,
        release=release,
        campaign=campaign,
        workers=workers,
        legacy_watcher=legacy_watcher,
        activation=activation,
    )
    previous_streak = _previous_quiet_streak(state_target, verified["sha256"])
    report_present = report_target.exists() or report_target.is_symlink()
    freeze_present = freeze_target.exists() or freeze_target.is_symlink()
    if freeze_present and not report_present:
        raise RuntimeError("V2.41.96 freeze exists without its source report")
    if report_present:
        report = read_object(report_target)
        _validate_report(
            report,
            protocol_sha=verified["sha256"],
            expected_settings=settings,
        )
        recovered = False
        if not freeze_present:
            freeze = build_capacity_freeze(
                report,
                report_path=str(REPORT),
                report_sha256=sha256(report_target),
                protocol_path=str(OUTPUT),
                protocol_sha256=verified["sha256"],
            )
            freeze["freeze_payload_sha256"] = payload_sha256(freeze)
            from scripts.preregister_v24196_capacity_executor import publish_new

            publish_new(freeze_target, freeze)
            recovered = True
        else:
            freeze = read_object(freeze_target)
        _validate_freeze(
            freeze,
            report=report,
            report_sha=sha256(report_target),
            protocol_sha=verified["sha256"],
        )
        value.update(
            status=(
                "complete_capacity_recommendation_available"
                if report.get("selected_model_request_concurrency", 0) > 0
                else "terminal_capacity_no_go_serial_probe_failed"
            ),
            reason=(
                "recovered_freeze_from_sealed_successor_report_without_reprobe"
                if recovered
                else "existing_successor_capacity_output_pair_live_valid"
            ),
            terminal=True,
            capacity_report={"path": str(REPORT), "sha256": sha256(report_target)},
            capacity_freeze={"path": str(FREEZE), "sha256": sha256(freeze_target)},
        )
    elif release is None:
        value.update(status="waiting_for_r1_release", reason="r1_not_exact220_released")
    elif campaign is None:
        value.update(
            status="waiting_for_quality_campaign_terminal",
            reason="capacity_probe_yields_to_all_preregistered_quality_work",
        )
    elif activation is None:
        value.update(
            status="waiting_for_execution_activation",
            reason="identity_bound_successor_activation_absent",
        )
    elif workers["present"]:
        value.update(
            status="waiting_for_api_workers_to_exit",
            reason="active_api_worker_family_present",
        )
    elif legacy_watcher["present"]:
        value.update(
            status="waiting_for_legacy_v24194_watcher_safe_handoff",
            reason="preserve_healthy_legacy_capacity_watcher_before_new_owner_lease",
        )
    else:
        required = int(
            protocol["release_and_compatibility_gate"][
                "quiet_observations_before_lease"
            ]
        )
        streak = previous_streak + 1
        value["consecutive_quiet_observations"] = streak
        if streak < required:
            value.update(
                status="waiting_for_second_quiet_observation",
                reason="capacity_probe_requires_consecutive_quiet_observations",
            )
        else:
            try:
                with lease_factory(
                    root,
                    owner=execution["shared_lease_owner"],
                    purpose=execution["shared_lease_purpose"],
                ) as lease:
                    value["shared_api_lease_acquired"] = True
                    post_activation = _activation_summary(
                        root, protocol_path, proc_root
                    )
                    post_release = _release_pair(root)
                    post_workers = _active_api_workers(
                        proc_root, list(execution["active_api_worker_markers"])
                    )
                    post_legacy = _legacy_capacity_watcher(proc_root)
                    if (
                        post_activation != activation
                        or post_release != release
                        or post_workers["present"]
                        or post_legacy["present"]
                        or lease.get("owner") != LEASE_OWNER
                        or lease.get("purpose") != LEASE_PURPOSE
                        or lease.get("pid") != os.getpid()
                    ):
                        value.update(
                            status="waiting_after_post_lease_recheck",
                            reason="release_worker_activation_or_lease_boundary_changed",
                            consecutive_quiet_observations=0,
                        )
                    else:
                        live = _live_post_lease_compatibility(
                            root,
                            proc_root=proc_root,
                            executor_pid=os.getpid(),
                        )
                        observed = _wait_for_compatibility_watcher(
                            root,
                            acquired_at_unix=int(lease["acquired_at_unix"]),
                            executor_pid=os.getpid(),
                            timeout_seconds=int(
                                protocol["release_and_compatibility_gate"][
                                    "post_lease_compatibility_timeout_seconds"
                                ]
                            ),
                        )
                        final_live = _live_post_lease_compatibility(
                            root,
                            proc_root=proc_root,
                            executor_pid=os.getpid(),
                        )
                        final_release = _release_pair(root)
                        final_workers = _active_api_workers(
                            proc_root, list(execution["active_api_worker_markers"])
                        )
                        final_legacy = _legacy_capacity_watcher(proc_root)
                        if (
                            final_release != release
                            or final_workers["present"]
                            or final_legacy["present"]
                        ):
                            value.update(
                                status="waiting_after_final_compatibility_recheck",
                                reason="release_or_worker_boundary_changed_before_probe",
                                consecutive_quiet_observations=0,
                            )
                        else:
                            value["v24195_live_compatibility_valid"] = True
                            value["v24195_watcher_observation_valid"] = True
                            capacity = protocol["capacity_contract"]
                            client = client_factory(
                                str(capacity["endpoint"]),
                                str(capacity["model"]),
                                reasoning_effort=str(capacity["reasoning_effort"]),
                                service_tier=str(capacity["service_tier"]),
                                timeout=int(capacity["request_timeout_seconds"]),
                                max_retries=int(capacity["client_max_retries"]),
                            )
                            report = ladder_runner(client, settings=settings)
                            report.update(
                                protocol={
                                    "path": str(OUTPUT),
                                    "sha256": verified["sha256"],
                                },
                                r1_release=release,
                                quality_campaign_terminal={
                                    **campaign,
                                    "post_lease_live": live,
                                    "v24195_watcher_observation": observed,
                                    "final_post_lease_live": final_live,
                                },
                                execution_activation=activation,
                                shared_api_lease_owner=LEASE_OWNER,
                                shared_api_lease_acquired=True,
                                created_at_unix=created,
                            )
                            report["report_payload_sha256"] = payload_sha256(report)
                            from scripts.preregister_v24196_capacity_executor import publish_new

                            publish_new(report_target, report)
                            freeze = build_capacity_freeze(
                                report,
                                report_path=str(REPORT),
                                report_sha256=sha256(report_target),
                                protocol_path=str(OUTPUT),
                                protocol_sha256=verified["sha256"],
                            )
                            freeze["freeze_payload_sha256"] = payload_sha256(freeze)
                            publish_new(freeze_target, freeze)
                            _validate_report(
                                report,
                                protocol_sha=verified["sha256"],
                                expected_settings=settings,
                            )
                            _validate_freeze(
                                freeze,
                                report=report,
                                report_sha=sha256(report_target),
                                protocol_sha=verified["sha256"],
                            )
                            selected = report[
                                "selected_model_request_concurrency"
                            ]
                            value.update(
                                status=(
                                    "complete_capacity_recommendation_available"
                                    if selected > 0
                                    else "terminal_capacity_no_go_serial_probe_failed"
                                ),
                                reason="neutral_capacity_ladder_completed_under_compatible_shared_lease",
                                terminal=True,
                                neutral_capacity_model_api_called=True,
                                capacity_report={
                                    "path": str(REPORT),
                                    "sha256": sha256(report_target),
                                },
                                capacity_freeze={
                                    "path": str(FREEZE),
                                    "sha256": sha256(freeze_target),
                                },
                                selected_model_request_concurrency=selected,
                                selected_parallel_full220_shards=report[
                                    "selected_parallel_full220_shards"
                                ],
                            )
            except DeepWideApiLeaseBusy:
                value.update(
                    status="waiting_for_shared_api_lease",
                    reason="shared_api_lease_busy",
                    shared_api_lease_acquired=False,
                )
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as exc:
                value.update(
                    status="critical_capacity_execution_failed",
                    reason=type(exc).__name__,
                    terminal=True,
                    neutral_capacity_model_api_called=None,
                    shared_api_lease_acquired=None,
                    consecutive_quiet_observations=0,
                )
    value["state_payload_sha256"] = payload_sha256(value)
    _atomic_json(state_target, value)
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
        raise RuntimeError("V2.41.96 execution parameters drifted")
    while True:
        value = run_cycle(
            Path(args.root),
            protocol_path=Path(args.protocol),
            state_path=Path(args.state),
            proc_root=Path(args.proc_root),
        )
        print(
            json.dumps(
                {
                    "role": value["role"],
                    "created_at_unix": value["created_at_unix"],
                    "status": value["status"],
                    "reason": value["reason"],
                    "shared_api_lease_acquired": value[
                        "shared_api_lease_acquired"
                    ],
                    "neutral_capacity_model_api_called": value[
                        "neutral_capacity_model_api_called"
                    ],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        if args.once or value["status"] in TERMINAL_STATUSES:
            return
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
