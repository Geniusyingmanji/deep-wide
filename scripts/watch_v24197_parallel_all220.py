#!/usr/bin/env python3
"""Wait for V2.41.96 capacity and a future candidate bundle, then plan only."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = Path("results/v24197_parallel_all220_preregistration_v1_20260731.json")
STATE_PATH = Path("outputs/v24197_parallel_all220_watcher_state_v1_20260731.json")


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
        raise RuntimeError("V2.41.97 watcher requires python -I -B")
    arguments = list(sys.argv[1:])

    def option(name: str, default: str) -> str:
        if name not in arguments:
            return default
        if arguments.count(name) != 1:
            raise RuntimeError(f"V2.41.97 option is not unique: {name}")
        index = arguments.index(name)
        if index + 1 >= len(arguments):
            raise RuntimeError(f"V2.41.97 option lacks a value: {name}")
        return arguments[index + 1]

    root = Path(option("--root", str(ROOT))).resolve()
    raw_protocol = Path(option("--protocol", str(PROTOCOL)))
    protocol = raw_protocol if raw_protocol.is_absolute() else root / raw_protocol
    raw_state = Path(option("--state", str(STATE_PATH)))
    state = raw_state if raw_state.is_absolute() else root / raw_state

    if (
        root != ROOT.resolve()
        or protocol.resolve(strict=False) != (root / PROTOCOL).resolve(strict=False)
        or protocol.is_symlink()
        or not protocol.is_file()
        or state.resolve(strict=False) != (root / STATE_PATH).resolve(strict=False)
        or state.is_symlink()
        or option("--poll-seconds", "60") != "60"
        or "--once" in arguments
    ):
        raise RuntimeError("V2.41.97 watcher execution drifted")
    value = json.loads(protocol.read_text(encoding="utf-8"))
    control = value.get("control_surface") or {}
    manifest = control.get("manifest")
    if (
        value.get("protocol_id")
        != "v24197_capacity_bound_parallel_all220_planner_v1"
        or not isinstance(manifest, dict)
        or control.get("file_count") != len(manifest)
        or control.get("manifest_sha256") != _payload_sha(manifest)
    ):
        raise RuntimeError("V2.41.97 watcher protocol is invalid")
    for relative, digest in manifest.items():
        target = root / relative
        if (
            target.is_symlink()
            or not target.is_file()
            or hashlib.sha256(target.read_bytes()).hexdigest() != digest
        ):
            raise RuntimeError("V2.41.97 control bytes drifted")


_bootstrap()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24197_parallel_all220 import (  # noqa: E402
    _object_snapshot,
    compile_parallel_plan,
    file_sha256,
    load_capacity_pair,
    payload_sha256,
    validate_candidate_bundle,
)
from scripts.activate_v24197_parallel_all220 import (  # noqa: E402
    validate_activation,
)
from scripts.preregister_v24197_parallel_all220 import (  # noqa: E402
    ACTIVATION,
    BUNDLE,
    CAPACITY_FREEZE,
    CAPACITY_REPORT,
    OUTPUT,
    PLAN,
    STATE,
    read_object,
    validate_protocol,
)


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


def _publish_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _activation(root: Path, protocol_sha: str) -> dict[str, Any] | None:
    path = root / ACTIVATION
    if not path.exists() and not path.is_symlink():
        return None
    verified = validate_activation(root, ACTIVATION, protocol_path=OUTPUT)
    value = verified["value"]
    if value.get("protocol", {}).get("sha256") != protocol_sha:
        raise RuntimeError("V2.41.97 activation protocol binding drifted")
    return {
        "path": str(ACTIVATION),
        "sha256": verified["sha256"],
        "executor_pid": value["executor"]["pid"],
        "executor_start_ticks": value["executor"]["start_ticks"],
    }


def _base_state(
    verified: dict[str, Any],
    *,
    created: int,
    activation: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "artifact_version": 1,
        "role": "v24197_parallel_all220_watcher_state",
        "created_at_unix": created,
        "protocol": {
            "path": str(OUTPUT),
            "sha256": verified["sha256"],
            "decision_contract_sha256": verified["value"]["decision_contract_sha256"],
            "control_manifest_sha256": verified["value"]["control_surface"]["manifest_sha256"],
        },
        "execution_activation": activation,
        "capacity_pair_opened": False,
        "candidate_bundle_opened": False,
        "opaque_id_files_opened": False,
        "candidate_manifest_bytes_hashed": False,
        "parallel_plan_created": False,
        "shared_api_lease_acquired": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "benchmark_question_answer_evidence_prediction_or_url_values_parsed_or_emitted": False,
        "mapping_gold_category_question_type_evaluator_score_read": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        "current_r1_or_quality_chain_forward_config_changed": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
        "terminal": False,
    }


def _target(root: Path, raw: Path, expected: str) -> Path:
    unresolved = raw if raw.is_absolute() else root / raw
    target = unresolved.resolve(strict=False)
    if (
        target != (root / expected).resolve(strict=False)
        or unresolved.is_symlink()
        or not target.is_relative_to((root / "outputs").resolve())
    ):
        raise RuntimeError("V2.41.97 state path is noncanonical")
    return target


def _recompute_plan(
    root: Path,
    verified: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, int], dict[str, Any], dict[str, str]]:
    capacity, freeze, capacity_snapshots = load_capacity_pair(
        root,
        report_path=str(CAPACITY_REPORT),
        freeze_path=str(CAPACITY_FREEZE),
        protocol_sha256=verified["value"]["capacity_input"][
            "parent_protocol_sha256"
        ],
    )
    bundle_path = root / BUNDLE
    bundle, bundle_digest = _object_snapshot(bundle_path)
    candidate = validate_candidate_bundle(
        root,
        bundle,
        bundle_path=str(BUNDLE),
        bundle_sha256=bundle_digest,
        capacity_path=str(CAPACITY_FREEZE),
        capacity_sha256=capacity_snapshots["freeze_sha256"],
        capacity=capacity,
        capacity_freeze=freeze,
    )
    plan = compile_parallel_plan(
        candidate,
        capacity,
        capacity_freeze_path=str(CAPACITY_FREEZE),
        capacity_freeze_sha256=capacity_snapshots["freeze_sha256"],
    )
    return plan, capacity, freeze, capacity_snapshots


def run_cycle(
    root: Path,
    *,
    protocol_path: Path = OUTPUT,
    state_path: Path = STATE,
    now: int | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.41.97 may only run in the canonical workspace")
    verified = validate_protocol(root, protocol_path)
    state_target = _target(
        root,
        state_path,
        verified["value"]["execution"]["state_path"],
    )
    created = int(time.time()) if now is None else int(now)
    activation = _activation(root, verified["sha256"])
    value = _base_state(verified, created=created, activation=activation)
    capacity_report = root / CAPACITY_REPORT
    capacity_freeze = root / CAPACITY_FREEZE
    bundle_path = root / BUNDLE
    plan_path = root / PLAN
    if activation is None:
        if plan_path.exists() or plan_path.is_symlink():
            raise RuntimeError("V2.41.97 plan appeared before activation")
        value.update(
            status="waiting_for_execution_activation",
            reason="identity_bound_planner_activation_absent",
        )
    elif plan_path.exists() or plan_path.is_symlink():
        if not capacity_report.is_file() or not capacity_freeze.is_file() or not bundle_path.is_file():
            raise RuntimeError("V2.41.97 plan exists without all live inputs")
        expected, _capacity, _freeze, _snapshots = _recompute_plan(root, verified)
        plan = read_object(plan_path)
        if plan != expected:
            raise RuntimeError("V2.41.97 existing plan differs from live replay")
        value.update(
            status="complete_parallel_plan_frozen",
            reason="existing_capacity_bound_plan_live_valid",
            capacity_pair_opened=True,
            candidate_bundle_opened=True,
            opaque_id_files_opened=True,
            candidate_manifest_bytes_hashed=True,
            parallel_plan_created=True,
            terminal=True,
            plan={"path": str(PLAN), "sha256": file_sha256(plan_path)},
        )
    elif not capacity_report.exists() and not capacity_report.is_symlink():
        if capacity_freeze.exists() or capacity_freeze.is_symlink():
            raise RuntimeError("V2.41.97 capacity freeze exists without report")
        value.update(
            status="waiting_for_capacity_freeze",
            reason="v24196_capacity_pair_absent",
        )
    elif not capacity_freeze.exists() and not capacity_freeze.is_symlink():
        value.update(
            status="waiting_for_capacity_freeze",
            reason="v24196_capacity_report_present_freeze_absent",
        )
    else:
        capacity, freeze, capacity_snapshots = load_capacity_pair(
            root,
            report_path=str(CAPACITY_REPORT),
            freeze_path=str(CAPACITY_FREEZE),
            protocol_sha256=verified["value"]["capacity_input"]["parent_protocol_sha256"],
        )
        value["capacity_pair_opened"] = True
        if capacity["selected"] <= 0:
            value.update(
                status="terminal_capacity_no_go_no_plan",
                reason="v24196_serial_probe_failed",
                terminal=True,
            )
        elif not bundle_path.exists() and not bundle_path.is_symlink():
            value.update(
                status="waiting_for_candidate_execution_bundle",
                reason="quality_go_and_candidate_freezes_not_yet_published",
            )
        else:
            value["candidate_bundle_opened"] = True
            plan, replay_capacity, replay_freeze, replay_snapshots = _recompute_plan(
                root, verified
            )
            if (
                replay_capacity != capacity
                or replay_freeze != freeze
                or replay_snapshots != capacity_snapshots
            ):
                raise RuntimeError("V2.41.97 capacity pair changed during replay")
            value["opaque_id_files_opened"] = True
            value["candidate_manifest_bytes_hashed"] = True
            _publish_new(plan_path, plan)
            value.update(
                status="complete_parallel_plan_frozen",
                reason="capacity_and_candidate_bundle_live_validated",
                parallel_plan_created=True,
                terminal=True,
                plan={"path": str(PLAN), "sha256": file_sha256(plan_path)},
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
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.poll_seconds != 60:
        raise RuntimeError("V2.41.97 poll interval drifted")
    while True:
        value = run_cycle(
            Path(args.root),
            protocol_path=Path(args.protocol),
            state_path=Path(args.state),
        )
        print(
            json.dumps(
                {
                    "role": value["role"],
                    "created_at_unix": value["created_at_unix"],
                    "status": value["status"],
                    "reason": value["reason"],
                    "parallel_plan_created": value["parallel_plan_created"],
                    "benchmark_forward_or_full220_launch_allowed": value[
                        "benchmark_forward_or_full220_launch_allowed"
                    ],
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
