#!/usr/bin/env python3
"""Activate V2.43.15 after its read-only label-blind preflight passes."""

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

from deepwide_agent.v24315_forward_contract import (  # noqa: E402
    ACTIVATION,
    CHILD_MARKER,
    EXECUTOR_CONCURRENCY,
    FORWARD_CONTRACT,
    MODEL_SLOT_CAP,
    PREAUDIT,
    RUNNER_MARKER,
    SELECTED_COUNT,
    payload_sha256,
    protected_watcher_snapshot,
    read_object,
    sha256,
    validate_forward_contract,
)
from scripts.audit_v24187_phase_liveness import process_snapshot  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.preregister_v24259_deterministic_normalizer_smoke import _matching  # noqa: E402
from scripts.preregister_v24315_exact220 import PROTOCOL, publish_new, validate_protocol  # noqa: E402


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict:
    root = root.resolve()
    contract = validate_forward_contract(root)
    protocol = validate_protocol(root, PROTOCOL)
    audit = read_object(root / PREAUDIT)
    unsigned = dict(audit)
    seal = unsigned.pop("audit_payload_sha256", None)
    rows = process_snapshot()
    lease = lease_observation(root, Path("/proc"))
    watchers = protected_watcher_snapshot()
    if (
        audit.get("role") != "v24315_exact220_preactivation_audit"
        or audit.get("audit_valid") is not True
        or audit.get("launch_authorized") is not True
        or seal != payload_sha256(unsigned)
        or (root / ACTIVATION).exists()
        or (root / ACTIVATION).is_symlink()
        or lease.get("active") is not False
        or _matching(rows, RUNNER_MARKER)
        or _matching(rows, CHILD_MARKER)
        or audit.get("protected_watchers") != watchers
        or watchers != contract["execution"]["protected_watchers"]
    ):
        raise RuntimeError("V2.43.15 activation boundary is not clean")
    value = {
        "artifact_version": 1,
        "role": "v24315_exact220_activation",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "active",
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "protocol_sha256": sha256(root / PROTOCOL),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "dependency_manifest_sha256": contract["dependency_manifest_sha256"],
        "control_manifest_sha256": protocol["control_manifest_sha256"],
        "selected": SELECTED_COUNT,
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "model_slot_cap": MODEL_SLOT_CAP,
        "protected_watchers": watchers,
        "shared_api_lease_active_before_activation": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "additional_rollout_avg4_leaderboard_or_sota_authorized": False,
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    publish_new(ROOT / ACTIVATION, build_activation())
    print(json.dumps({"path": str(ACTIVATION), "sha256": sha256(ROOT / ACTIVATION)}, sort_keys=True))
