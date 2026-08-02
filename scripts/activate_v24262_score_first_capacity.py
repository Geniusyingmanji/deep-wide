#!/usr/bin/env python3
"""Activate the frozen V2.42.62 full-pipeline capacity ladder."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.audit_v24187_phase_liveness import process_snapshot  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.preregister_v24259_deterministic_normalizer_smoke import _matching  # noqa: E402
from scripts.preregister_v24262_score_first_capacity import (  # noqa: E402
    ACTIVATION,
    OUTPUT,
    PREAUDIT,
    RUNNER_MARKER,
    WATCHER_MARKER,
    publish_new,
    validate_protocol,
)
from scripts.run_v24257_score_first_smoke import payload_sha256, read_object, sha256  # noqa: E402


ROLE = "v24262_score_first_capacity_activation"


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict:
    root = root.resolve()
    protocol = validate_protocol(root, OUTPUT)
    preaudit = read_object(root / PREAUDIT)
    unsigned = dict(preaudit)
    seal = unsigned.pop("audit_payload_sha256", None)
    if (
        preaudit.get("role") != "v24262_score_first_capacity_preactivation_audit"
        or preaudit.get("audit_valid") is not True
        or preaudit.get("launch_authorized") is not True
        or preaudit.get("protocol_sha256") != sha256(root / OUTPUT)
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.62 preactivation audit drifted")
    lease = lease_observation(root, Path("/proc"))
    rows = process_snapshot()
    if (
        (root / ACTIVATION).exists()
        or (root / ACTIVATION).is_symlink()
        or lease.get("active") is not False
        or _matching(rows, RUNNER_MARKER)
        or _matching(rows, WATCHER_MARKER)
    ):
        raise RuntimeError("V2.42.62 activation boundary is not clean")
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "active",
        "protocol_sha256": sha256(root / OUTPUT),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "decision_contract_sha256": protocol["decision_contract_sha256"],
        "control_manifest_sha256": protocol["control_surface"]["manifest_sha256"],
        "forward_manifest_sha256": protocol["forward_surface"]["manifest_sha256"],
        "selected_opaque_ids_sha256": protocol["task_contract"]["selected_opaque_ids_sha256"],
        "shared_api_lease_active_before_activation": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "official_evaluator_dev64_full220_or_leaderboard_authorized": False,
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    publish_new(ROOT / ACTIVATION, build_activation())
    print(json.dumps({"path": str(ACTIVATION), "sha256": sha256(ROOT / ACTIVATION)}))
