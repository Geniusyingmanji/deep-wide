#!/usr/bin/env python3
"""Create-exclusive activation for the audited V2.42.91 dev64 gate."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24291_forward_contract import (  # noqa: E402
    ACTIVATION,
    EXECUTOR_CONCURRENCY,
    FORWARD_CONTRACT,
    MODEL_SLOT_CAP,
    PREAUDIT,
    SELECTED_COUNT,
    payload_sha256,
    read_object,
    sha256,
    validate_forward_contract,
)
from scripts.preregister_v24291_dev64 import FULL_PROTOCOL, publish_new, validate_protocol  # noqa: E402


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict:
    root = root.resolve()
    contract = validate_forward_contract(root)
    protocol = validate_protocol(root)
    audit = read_object(root / PREAUDIT)
    unsigned = dict(audit)
    seal = unsigned.pop("audit_payload_sha256", None)
    if (
        audit.get("role") != "v24291_dev64_preactivation_audit"
        or audit.get("audit_valid") is not True
        or audit.get("launch_authorized") is not True
        or audit.get("findings") != []
        or audit.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or audit.get("protocol_sha256") != sha256(root / FULL_PROTOCOL)
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.91 preactivation audit is not launchable")
    value = {
        "artifact_version": 1,
        "role": "v24291_dev64_activation",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "active",
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "dependency_manifest_sha256": contract["dependency_manifest_sha256"],
        "control_manifest_sha256": protocol["control_manifest_sha256"],
        "selected": SELECTED_COUNT,
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "model_slot_cap": MODEL_SLOT_CAP,
        "shared_api_lease_active_before_activation": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "exact220_leaderboard_or_sota_authorized": False,
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    value = build_activation()
    publish_new(ROOT / ACTIVATION, value)
    print(json.dumps({"path": str(ACTIVATION), "status": value["status"]}, sort_keys=True))
