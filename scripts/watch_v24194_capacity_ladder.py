#!/usr/bin/env python3
"""Wait for campaign completion, then run the neutral capacity ladder once."""

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
PROTOCOL = Path("results/v24194_capacity_ladder_preregistration_v1_20260731.json")


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
        raise RuntimeError("V2.41.94 watcher requires python -I -B")
    arguments = list(sys.argv[1:])

    def option(name: str, default: str) -> str:
        if name not in arguments:
            return default
        if arguments.count(name) != 1:
            raise RuntimeError(f"V2.41.94 option is not unique: {name}")
        index = arguments.index(name)
        if index + 1 >= len(arguments):
            raise RuntimeError(f"V2.41.94 option lacks a value: {name}")
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
        raise RuntimeError("V2.41.94 watcher path or execution drifted")
    value = json.loads(protocol.read_text(encoding="utf-8"))
    control = value.get("control_surface") or {}
    manifest = control.get("manifest")
    if (
        value.get("protocol_id") != "v24194_neutral_gpt56_capacity_ladder_v1"
        or not isinstance(manifest, dict)
        or control.get("file_count") != len(manifest)
        or control.get("manifest_sha256") != _payload_sha(manifest)
    ):
        raise RuntimeError("V2.41.94 watcher protocol is invalid")
    for relative, digest in manifest.items():
        target = root / relative
        if (
            target.is_symlink()
            or not target.is_file()
            or hashlib.sha256(target.read_bytes()).hexdigest() != digest
        ):
            raise RuntimeError("V2.41.94 control bytes drifted")


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
from scripts.deepwide_api_lease import (  # noqa: E402
    DeepWideApiLeaseBusy,
    acquire_deepwide_api_lease,
)
from scripts.preregister_v24194_capacity_ladder import (  # noqa: E402
    EXECUTION_ACTIVATION,
    FREEZE,
    LEASE_OWNER,
    OUTPUT,
    PHASE_STATE,
    REPORT,
    R1_STATE,
    STATE,
    WAIT_ACTIVATION,
    sha256,
    validate_protocol,
)
from scripts.v24159_true_continuation_reachability import (  # noqa: E402
    actual_python_script,
    process_snapshot,
    publish_new,
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
        or not target.is_relative_to((root / parent).resolve())
    ):
        raise RuntimeError("V2.41.94 output path is noncanonical")
    return target


def _read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.41.94 source is noncanonical: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.41.94 source is not an object: {path}")
    return value


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


def _release_pair(root: Path) -> dict[str, Any] | None:
    r1 = _read_object(root / R1_STATE)
    aggregate = r1.get("aggregate") or {}
    release = r1.get("released_artifacts") or {}
    if r1.get("status") == "waiting_for_r1_exact_terminal_220":
        if (
            aggregate.get("selected") != 220
            or aggregate.get("exact_terminal_220") is not False
            or release.get("complete_pair") is not False
            or r1.get("mapping_or_gold_read") is not False
            or r1.get("evaluator_or_score_read") is not False
        ):
            raise RuntimeError("V2.41.94 R1 waiting state is inconsistent")
        return None
    if (
        r1.get("status")
        not in {"complete_existing_release_pair", "complete_recovered_release_pair"}
        or aggregate.get("selected") != 220
        or aggregate.get("terminal") != 220
        or aggregate.get("exact_terminal_220") is not True
        or release.get("complete_pair") is not True
        or release.get("partial_pair") is not False
        or release.get("noncanonical") is not False
    ):
        raise RuntimeError("V2.41.94 R1 release state is invalid")
    result_path = root / str(release.get("result_path"))
    seal_path = root / str(release.get("seal_path"))
    seal = _read_object(seal_path)
    if (
        seal.get("role") != "full220_rollout1_finalization_seal"
        or seal.get("exact_terminal_partition", {}).get("exact_terminal_220")
        is not True
        or seal.get("exact_terminal_partition", {}).get("selected") != 220
        or seal.get("exact_terminal_partition", {}).get("terminal") != 220
        or seal.get("released_result", {}).get("path")
        != str(release.get("result_path"))
        or seal.get("released_result", {}).get("sha256") != sha256(result_path)
        or seal.get("claims", {}).get("leaderboard_or_sota") is not False
    ):
        raise RuntimeError("V2.41.94 released pair failed live validation")
    return {
        "r1_state_path": str(R1_STATE),
        "r1_state_sha256": sha256(root / R1_STATE),
        "result_path": str(release["result_path"]),
        "result_sha256": sha256(result_path),
        "seal_path": str(release["seal_path"]),
        "seal_sha256": sha256(seal_path),
        "result_contents_parsed": False,
        "result_bytes_hashed_for_seal_only": True,
        "finalization_seal_metadata_read": True,
        "score_or_metric_values_emitted": False,
    }


def _campaign_terminal(root: Path) -> dict[str, Any] | None:
    phase_path = root / PHASE_STATE
    phase = _read_object(phase_path)
    current = phase.get("current_phase") or {}
    if (
        phase.get("role") != "v24187_phase_liveness_audit"
        or phase.get("critical_findings") != []
        or phase.get("overall_status")
        not in {"healthy", "degraded_forward_healthy_manual_review_only"}
        or current.get("valid") is not True
    ):
        raise RuntimeError("V2.41.94 authoritative campaign state is invalid")
    if current.get("phase") != "post_gate1_and_leaderboard_handoff":
        return None
    if current.get("terminal") is not True:
        return None
    return {
        "phase_state_path": str(PHASE_STATE),
        "phase_state_sha256": sha256(phase_path),
        "phase": current["phase"],
        "terminal": True,
        "valid": True,
        "critical_findings": [],
    }


def _active_api_workers(proc_root: Path, markers: list[str]) -> dict[str, Any]:
    rows = process_snapshot(proc_root)
    pids: list[int] = []
    observed_markers: set[str] = set()
    for row in rows:
        pid = int(row["pid"])
        if pid == os.getpid():
            continue
        script = actual_python_script([str(value) for value in row.get("argv") or []])
        if script is None:
            continue
        for marker in markers:
            if script == marker or script.endswith("/" + marker):
                pids.append(pid)
                observed_markers.add(marker)
                break
    return {
        "present": bool(pids),
        "match_count": len(set(pids)),
        "pids": sorted(set(pids)),
        "matched_markers": sorted(observed_markers),
        "command_lines_emitted": False,
    }


def _execution_activation(root: Path, verified: dict[str, Any]) -> dict[str, Any] | None:
    path = root / EXECUTION_ACTIVATION
    if not path.exists() and not path.is_symlink():
        return None
    value = _read_object(path)
    if (
        value.get("role") != "v24194_capacity_ladder_execution_activation"
        or value.get("activation_valid") is not True
        or value.get("protocol", {}).get("sha256") != verified["sha256"]
        or value.get("registered_shared_lease_owner") != LEASE_OWNER
        or value.get("quality_chain_priority_preserved") is not True
        or value.get("benchmark_question_prediction_mapping_gold_category_evaluator_score_read")
        is not False
        or value.get("credential_value_read_persisted_hashed_or_emitted") is not False
        or value.get("network_model_search_fetch_or_evaluator_api_called") is not False
    ):
        raise RuntimeError("V2.41.94 execution activation is invalid")
    unsigned = dict(value)
    seal = unsigned.pop("activation_payload_sha256", None)
    if seal != payload_sha256(unsigned):
        raise RuntimeError("V2.41.94 execution activation seal is invalid")
    return {
        "path": str(EXECUTION_ACTIVATION),
        "sha256": sha256(path),
        "activation_payload_sha256": seal,
        "registered_shared_lease_owner": LEASE_OWNER,
    }


def _previous_quiet_streak(path: Path, protocol_sha: str) -> int:
    if not path.exists() and not path.is_symlink():
        return 0
    value = _read_object(path)
    if (
        value.get("role") != "v24194_capacity_ladder_watcher_state"
        or value.get("protocol", {}).get("sha256") != protocol_sha
    ):
        raise RuntimeError("V2.41.94 previous state binding is invalid")
    streak = value.get("consecutive_quiet_observations", 0)
    if isinstance(streak, bool) or not isinstance(streak, int) or streak < 0:
        raise RuntimeError("V2.41.94 previous quiet streak is invalid")
    return streak


def _validate_report(
    report: dict[str, Any],
    *,
    protocol_sha: str,
    expected_settings: ProbeSettings,
) -> None:
    unsigned = dict(report)
    seal = unsigned.pop("report_payload_sha256", None)
    if (
        set(report)
        != CAPACITY_REPORT_CORE_FIELDS | CAPACITY_REPORT_EXECUTION_FIELDS
        or report.get("protocol")
        != {"path": str(OUTPUT), "sha256": protocol_sha}
        or isinstance(report.get("created_at_unix"), bool)
        or not isinstance(report.get("created_at_unix"), int)
        or report.get("r1_release") is None
        or report.get("quality_campaign_terminal") is None
        or report.get("execution_activation") is None
        or not isinstance(report.get("r1_release"), dict)
        or not isinstance(report.get("quality_campaign_terminal"), dict)
        or not isinstance(report.get("execution_activation"), dict)
        or report.get("role")
        != "v24194_neutral_gpt56_capacity_ladder_measurement"
        or seal != payload_sha256(unsigned)
        or report.get("protocol", {}).get("sha256") != protocol_sha
        or report.get("shared_api_lease_owner") != LEASE_OWNER
        or report.get("shared_api_lease_acquired") is not True
    ):
        raise RuntimeError("V2.41.94 capacity report is invalid")
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
        raise RuntimeError("V2.41.94 capacity freeze is invalid")


def _base_state(
    verified: dict[str, Any],
    *,
    now: int,
    release: dict[str, Any] | None,
    campaign: dict[str, Any] | None,
    workers: dict[str, Any],
    activation: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "artifact_version": 1,
        "role": "v24194_capacity_ladder_watcher_state",
        "created_at_unix": now,
        "protocol": {
            "path": str(verified["path"].relative_to(ROOT)),
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
        "execution_activation": activation,
        "consecutive_quiet_observations": 0,
        "shared_api_lease_acquired": False,
        "neutral_capacity_model_api_called": False,
        "benchmark_question_prediction_mapping_gold_category_evaluator_score_read": False,
        "runtime_task_state_answer_evidence_or_url_opened": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "search_fetch_or_evaluator_api_called": False,
        "response_text_or_response_id_persisted": False,
        "current_r1_or_quality_chain_process_signal_restart_resume_rerun_skip": False,
        "current_r1_or_quality_chain_forward_config_concurrency_changed": False,
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
        raise RuntimeError("V2.41.94 may only run in the canonical workspace")
    verified = validate_protocol(root, protocol_path)
    protocol = verified["value"]
    execution = protocol["execution"]
    settings = settings_from_dict(protocol["capacity_contract"]["settings"])
    if proc_root.resolve() != Path(execution["proc_root"]).resolve():
        raise RuntimeError("V2.41.94 proc root differs from protocol")
    state_target = _target(root, state_path, execution["state_path"], "outputs")
    report_target = _target(root, Path(execution["report_path"]), execution["report_path"], "results")
    freeze_target = _target(root, Path(execution["freeze_path"]), execution["freeze_path"], "results")
    created = int(time.time()) if now is None else int(now)
    release = _release_pair(root)
    campaign = _campaign_terminal(root)
    workers = _active_api_workers(
        proc_root, list(execution["active_api_worker_markers"])
    )
    activation = _execution_activation(root, verified)
    value = _base_state(
        verified,
        now=created,
        release=release,
        campaign=campaign,
        workers=workers,
        activation=activation,
    )
    previous_streak = _previous_quiet_streak(state_target, verified["sha256"])
    report_present = report_target.exists() or report_target.is_symlink()
    freeze_present = freeze_target.exists() or freeze_target.is_symlink()
    if freeze_present and not report_present:
        raise RuntimeError("V2.41.94 freeze exists without its source report")
    if report_present:
        if report_target.is_symlink() or not report_target.is_file():
            raise RuntimeError("V2.41.94 report is noncanonical")
        report = _read_object(report_target)
        _validate_report(
            report,
            protocol_sha=verified["sha256"],
            expected_settings=settings,
        )
        if not freeze_present:
            freeze = build_capacity_freeze(
                report,
                report_path=str(REPORT),
                report_sha256=sha256(report_target),
                protocol_path=str(OUTPUT),
                protocol_sha256=verified["sha256"],
            )
            unsigned_freeze = dict(freeze)
            freeze["freeze_payload_sha256"] = payload_sha256(unsigned_freeze)
            publish_new(freeze_target, freeze)
            recovered_freeze_only = True
        else:
            if freeze_target.is_symlink() or not freeze_target.is_file():
                raise RuntimeError("V2.41.94 freeze is noncanonical")
            freeze = _read_object(freeze_target)
            recovered_freeze_only = False
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
                "recovered_freeze_from_sealed_capacity_report_without_reprobe"
                if recovered_freeze_only
                else "existing_capacity_output_pair_live_valid"
            ),
            terminal=True,
            capacity_report={"path": str(REPORT), "sha256": sha256(report_target)},
            capacity_freeze={"path": str(FREEZE), "sha256": sha256(freeze_target)},
        )
    elif release is None:
        value.update(
            status="waiting_for_r1_release",
            reason="r1_not_exact220_released",
        )
    elif campaign is None:
        value.update(
            status="waiting_for_quality_campaign_terminal",
            reason="capacity_probe_yields_to_all_preregistered_quality_work",
        )
    elif activation is None:
        value.update(
            status="waiting_for_execution_activation",
            reason="shared_lease_owner_not_yet_registered_by_activation",
        )
    elif workers["present"]:
        value.update(
            status="waiting_for_api_workers_to_exit",
            reason="active_api_worker_family_present",
        )
    else:
        required = int(
            protocol["release_and_priority_gate"]["quiet_observations_before_lease"]
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
                    second_release = _release_pair(root)
                    second_campaign = _campaign_terminal(root)
                    second_workers = _active_api_workers(
                        proc_root, list(execution["active_api_worker_markers"])
                    )
                    second_activation = _execution_activation(root, verified)
                    value["post_lease_recheck"] = {
                        "r1_release_unchanged": second_release == release,
                        "quality_campaign_terminal_unchanged": second_campaign == campaign,
                        "active_api_workers": second_workers,
                        "execution_activation_unchanged": second_activation == activation,
                        "lease_owner_matches": lease.get("owner")
                        == execution["shared_lease_owner"],
                        "lease_pid_matches": lease.get("pid") == os.getpid(),
                        "lease_purpose_or_hostname_emitted": False,
                    }
                    if (
                        second_release != release
                        or second_campaign != campaign
                        or second_workers["present"]
                        or second_activation != activation
                    ):
                        value.update(
                            status="waiting_after_post_lease_recheck",
                            reason="priority_or_release_boundary_changed_after_lease",
                            consecutive_quiet_observations=0,
                        )
                    else:
                        capacity = protocol["capacity_contract"]
                        client = client_factory(
                            str(capacity["endpoint"]),
                            str(capacity["model"]),
                            reasoning_effort=str(capacity["reasoning_effort"]),
                            service_tier=str(capacity["service_tier"]),
                            timeout=int(capacity["request_timeout_seconds"]),
                            max_retries=int(capacity["client_max_retries"]),
                        )
                        try:
                            report = ladder_runner(client, settings=settings)
                        except BaseException:
                            # Preserve KeyboardInterrupt/SystemExit semantics;
                            # a future watcher restart may retry only because no
                            # create-exclusive report/freeze was published.
                            raise
                        report.update(
                            protocol={"path": str(OUTPUT), "sha256": verified["sha256"]},
                            r1_release=release,
                            quality_campaign_terminal=campaign,
                            execution_activation=activation,
                            shared_api_lease_owner=execution["shared_lease_owner"],
                            shared_api_lease_acquired=True,
                            created_at_unix=created,
                        )
                        unsigned_report = dict(report)
                        report["report_payload_sha256"] = payload_sha256(unsigned_report)
                        publish_new(report_target, report)
                        freeze = build_capacity_freeze(
                            report,
                            report_path=str(REPORT),
                            report_sha256=sha256(report_target),
                            protocol_path=str(OUTPUT),
                            protocol_sha256=verified["sha256"],
                        )
                        unsigned_freeze = dict(freeze)
                        freeze["freeze_payload_sha256"] = payload_sha256(unsigned_freeze)
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
                        selected = report["selected_model_request_concurrency"]
                        value.update(
                            status=(
                                "complete_capacity_recommendation_available"
                                if selected > 0
                                else "terminal_capacity_no_go_serial_probe_failed"
                            ),
                            reason="neutral_capacity_ladder_completed_under_shared_lease",
                            terminal=True,
                            shared_api_lease_acquired=True,
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
        raise RuntimeError("V2.41.94 execution parameters drifted")
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
