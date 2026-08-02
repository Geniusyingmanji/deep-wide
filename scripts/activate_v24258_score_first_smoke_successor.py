#!/usr/bin/env python3
"""Create-exclusive activation for the V2.42.58 zero-effect successor."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.preregister_v24258_score_first_smoke_successor import (  # noqa: E402
    ACTIVATION,
    EXECUTION_START,
    OUTPUT,
    OUTPUT_ROOT,
    RESULT,
    ROLE as PROTOCOL_ROLE,
    _publish,
    _start_ticks,
    validate_protocol,
)
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402


ROLE = "v24258_score_first_smoke_successor_activation"


def _watchers(rows: list[dict[str, Any]], marker: str) -> list[int]:
    values: list[int] = []
    for row in rows:
        script = actual_python_script([str(item) for item in row.get("argv") or []])
        if script and (script == marker or script.endswith("/" + marker)):
            values.append(int(row["pid"]))
    return sorted(values)


def build_activation(
    root: Path = ROOT,
    *,
    now: int | None = None,
    proc_root: Path = Path("/proc"),
    processes: list[dict[str, Any]] | None = None,
    observed_lease: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root, OUTPUT)
    rows = process_snapshot(proc_root) if processes is None else processes
    lease = (
        lease_observation(root, proc_root)
        if observed_lease is None
        else dict(observed_lease)
    )
    expected = protocol["execution"]["existing_watcher"]
    pids = _watchers(rows, expected["marker"])
    if (
        protocol.get("role") != PROTOCOL_ROLE
        or pids != [expected["pid"]]
        or _start_ticks(proc_root, expected["pid"]) != expected["start_ticks"]
        or lease.get("active") is not False
        or any(
            (root / path).exists() or (root / path).is_symlink()
            for path in (ACTIVATION, EXECUTION_START, OUTPUT_ROOT, RESULT)
        )
    ):
        raise RuntimeError("V2.42.58 activation boundary drifted")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "active",
        "protocol": {"path": str(OUTPUT), "sha256": sha256(root / OUTPUT)},
        "decision_contract_sha256": protocol["decision_contract_sha256"],
        "control_manifest_sha256": protocol["control_surface"]["manifest_sha256"],
        "existing_watcher": expected,
        "shared_api_lease_active_before_activation": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "benchmark_question_prediction_mapping_gold_category_evaluator_score_read": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "one_corrected_smoke16_successor_launch": True,
        "new_or_restarted_watcher_process_signal_parent_retry_resume_or_selective_rerun": False,
        "official_evaluator_dev64_full220_or_leaderboard": False,
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    return value


def validate_activation(root: Path, path: Path = ACTIVATION) -> dict[str, Any]:
    value = json.loads((root / path).read_text(encoding="utf-8"))
    unsigned = dict(value)
    seal = unsigned.pop("activation_payload_sha256", None)
    if (
        value.get("role") != ROLE
        or value.get("status") != "active"
        or value.get("protocol", {}).get("sha256") != sha256(root / OUTPUT)
        or value.get("official_evaluator_dev64_full220_or_leaderboard") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.58 activation drifted")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    _publish(ROOT / ACTIVATION, build_activation())
    print(json.dumps({"path": str(ACTIVATION), "sha256": sha256(ROOT / ACTIVATION)}))


if __name__ == "__main__":
    main()
