#!/usr/bin/env python3
"""Create-exclusive activation for the V2.42.57 smoke16 protocol."""

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
    lease_observation,
)
from scripts.preregister_v24257_score_first_smoke import (  # noqa: E402
    ACTIVATION,
    FUTURE_PATHS,
    OUTPUT,
    ROLE as PROTOCOL_ROLE,
    validate_protocol,
)
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402


ROLE = "v24257_score_first_smoke_activation"


def build_activation(root: Path = ROOT, *, created_at_unix: int | None = None) -> dict:
    root = root.resolve()
    protocol = validate_protocol(root, OUTPUT)
    if protocol.get("role") != PROTOCOL_ROLE:
        raise RuntimeError("V2.42.57 protocol role drifted")
    present = [
        str(path)
        for path in FUTURE_PATHS
        if path != ACTIVATION and ((root / path).exists() or (root / path).is_symlink())
    ]
    if present or (root / ACTIVATION).exists() or (root / ACTIVATION).is_symlink():
        raise RuntimeError("V2.42.57 activation boundary is not pristine")
    lease = lease_observation(root, Path("/proc"))
    if lease.get("active") is not False or lease.get("ordinary") is not True:
        raise RuntimeError("V2.42.57 cannot activate while the shared lease is active")
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "status": "active",
        "protocol_path": str(OUTPUT),
        "protocol_sha256": sha256(root / OUTPUT),
        "decision_contract_sha256": protocol["decision_contract_sha256"],
        "control_manifest_sha256": protocol["control_surface"]["manifest_sha256"],
        "selected_opaque_ids_sha256": protocol["task_contract"][
            "selected_opaque_ids_sha256"
        ],
        "shared_api_lease_active_before_activation": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "benchmark_question_prediction_mapping_gold_score_read": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "existing_benchmark_or_watcher_signaled_restarted_modified_or_terminated": False,
        "official_evaluator_dev64_full220_or_leaderboard_authorized": False,
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / ACTIVATION).resolve(strict=False)
    if target != expected or not target.is_relative_to((ROOT / "results").resolve()):
        raise RuntimeError("V2.42.57 activation output is noncanonical")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        parent = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ACTIVATION))
    args = parser.parse_args()
    output = Path(args.output)
    output = output if output.is_absolute() else ROOT / output
    value = build_activation()
    publish_new(output, value)
    print(json.dumps({"path": str(output), "sha256": sha256(output)}))


if __name__ == "__main__":
    main()

