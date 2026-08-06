#!/usr/bin/env python3
"""Create-exclusive activation for audited V2.46.30 exact-220."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24630_exact220_contract import (  # noqa: E402
    ACTIVATION, EXECUTION_START, EXECUTOR_CONCURRENCY, FORWARD_CONTRACT,
    FORWARD_RESULT, MODEL_SLOT_CAP, OUTPUT_ROOT, PREAUDIT, SELECTED_COUNT,
    payload_sha256, protected_watcher_snapshot, read_object, sha256,
    validate_forward_contract,
)
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.preregister_v24630_exact220 import publish_new  # noqa: E402


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict:
    root = root.resolve()
    contract = validate_forward_contract(root)
    audit = read_object(root / PREAUDIT)
    unsigned = dict(audit)
    seal = unsigned.pop("audit_payload_sha256", None)
    lease = lease_observation(root, Path("/proc"))
    if (
        audit.get("role") != "v24630_exact220_preactivation_audit"
        or audit.get("audit_valid") is not True
        or audit.get("launch_authorized") is not True
        or audit.get("findings") != []
        or audit.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or audit.get("protected_watchers") != protected_watcher_snapshot()
        or seal != payload_sha256(unsigned)
        or lease.get("active") is not False
        or any((root / path).exists() or (root / path).is_symlink() for path in (ACTIVATION, EXECUTION_START, FORWARD_RESULT, OUTPUT_ROOT))
    ):
        raise RuntimeError("V2.46.30 preactivation audit is not launchable")
    value = {
        "artifact_version": 1,
        "role": "v24630_exact220_activation",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "active",
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "dependency_manifest_sha256": contract["dependency_manifest_sha256"],
        "selected": SELECTED_COUNT,
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "model_slot_cap": MODEL_SLOT_CAP,
        "protected_watchers": audit["protected_watchers"],
        "shared_api_lease_active_before_activation": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "leaderboard_or_sota_authorized": False,
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    value = build_activation()
    publish_new(ROOT / ACTIVATION, value)
    print(json.dumps({"path": str(ACTIVATION), "status": value["status"]}, sort_keys=True))
