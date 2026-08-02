#!/usr/bin/env python3
"""Read-only liveness watcher for the V2.42.59 smoke16."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    build_report as build_legacy_report,
    lease_observation,
)
from scripts.audit_v24187_phase_liveness import process_snapshot  # noqa: E402
from scripts.audit_v24259_deterministic_normalizer_smoke import (  # noqa: E402
    EXPECTED_LEGACY_ACTIVE_FINDING,
    lease_overlay,
)
from scripts.preregister_v24259_deterministic_normalizer_smoke import (  # noqa: E402
    ACTIVATION,
    OUTPUT,
    RESULT,
    STATE,
    _read_object,
    _sealed,
    validate_protocol,
)
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402


ROLE = "v24259_deterministic_normalizer_smoke_watcher_state"


def build_state(
    root: Path = ROOT,
    *,
    now: int | None = None,
    proc_root: Path = Path("/proc"),
) -> dict:
    root = root.resolve()
    protocol = validate_protocol(root, OUTPUT)
    activation = _read_object(root / ACTIVATION)
    if (
        activation.get("role") != "v24259_deterministic_normalizer_smoke_activation"
        or activation.get("status") != "active"
        or activation.get("protocol_sha256") != sha256(root / OUTPUT)
        or not _sealed(activation, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.42.59 watcher activation drifted")
    processes = process_snapshot(proc_root)
    lease = lease_observation(root, proc_root)
    overlay = lease_overlay(
        root,
        protocol,
        proc_root=proc_root,
        processes=processes,
        observed_lease=lease,
    )
    legacy = build_legacy_report(
        root,
        now=int(time.time()) if now is None else int(now),
        proc_root=proc_root,
        processes=processes,
        observed_lease=lease,
    )
    critical = list(legacy.get("critical_findings") or [])
    effective = list(critical)
    suppressed: list[str] = []
    if overlay["legacy_finding_suppression_allowed"]:
        if EXPECTED_LEGACY_ACTIVE_FINDING not in effective:
            effective.append("v24259:expected_legacy_unknown_owner_finding_absent")
        else:
            effective.remove(EXPECTED_LEGACY_ACTIVE_FINDING)
            suppressed = [EXPECTED_LEGACY_ACTIVE_FINDING]
    result_present = (root / RESULT).is_file() and not (root / RESULT).is_symlink()
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "protocol_sha256": sha256(root / OUTPUT),
        "activation_sha256": sha256(root / ACTIVATION),
        "status": (
            "complete_smoke_result_available"
            if result_present
            else "running_smoke_under_registered_lease"
            if overlay["identity_valid"]
            else "waiting_for_smoke_launch"
            if lease.get("active") is False
            else "critical_lease_identity"
        ),
        "terminal": result_present,
        "lease_compatibility_overlay": overlay,
        "legacy_liveness": {
            "overall_status": legacy.get("overall_status"),
            "critical_findings": critical,
            "suppressed_exact_findings": suppressed,
            "effective_critical_findings": sorted(set(effective)),
            "all_unrelated_findings_preserved": all(
                item in effective
                for item in critical
                if item != EXPECTED_LEGACY_ACTIVE_FINDING
            ),
            "contents_emitted": False,
        },
        "result_present": result_present,
        "mapping_gold_category_question_type_evaluator_score_read": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "network_model_search_fetch_evaluator_or_api_called_by_watcher": False,
        "process_signal_restart_resume_skip_or_selective_retry": False,
        "dev64_full220_leaderboard_or_sota_authorized": False,
    }
    value["state_payload_sha256"] = payload_sha256(value)
    return value


def publish_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--protocol", default=str(OUTPUT))
    parser.add_argument("--state", default=str(STATE))
    parser.add_argument("--poll-seconds", type=int, default=10)
    args = parser.parse_args()
    if Path(args.root).resolve() != ROOT or Path(args.protocol) != OUTPUT or Path(args.state) != STATE:
        raise RuntimeError("V2.42.59 watcher controls drifted")
    while True:
        value = build_state()
        publish_atomic(ROOT / STATE, value)
        print(json.dumps({"status": value["status"], "terminal": value["terminal"]}), flush=True)
        if value["terminal"]:
            return
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
