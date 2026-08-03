#!/usr/bin/env python3
"""Create-exclusive activation for the audited V2.43.11 paired-dev64 gate."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24311_forward_contract import (  # noqa: E402
    ACTIVATION,
    EXECUTOR_CONCURRENCY_PER_ARM,
    EXECUTION_START,
    FORWARD_CONTRACT,
    FORWARD_RESULT,
    FULL_PROTOCOL,
    MODEL_SLOT_CAP,
    OUTPUT_ROOT,
    PREAUDIT,
    protected_watcher_snapshot,
    SELECTED_COUNT,
    TOTAL_EXECUTOR_CONCURRENCY,
    payload_sha256,
    read_object,
    sha256,
    validate_forward_contract,
)
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.preregister_v24311_paired_dev64 import (  # noqa: E402
    publish_new,
    validate_protocol,
)


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict:
    root = root.resolve()
    contract = validate_forward_contract(root)
    protocol = validate_protocol(root)
    audit = read_object(root / PREAUDIT)
    lease = lease_observation(root, Path("/proc"))
    unsigned = dict(audit)
    seal = unsigned.pop("audit_payload_sha256", None)
    if (
        audit.get("role") != "v24311_paired_dev64_preactivation_audit"
        or audit.get("audit_valid") is not True
        or audit.get("launch_authorized") is not True
        or audit.get("findings") != []
        or audit.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or audit.get("protocol_sha256") != sha256(root / FULL_PROTOCOL)
        or audit.get("protected_watchers") != protected_watcher_snapshot()
        or lease.get("active") is not False
        or any(
            (root / path).exists() or (root / path).is_symlink()
            for path in (ACTIVATION, EXECUTION_START, FORWARD_RESULT, OUTPUT_ROOT)
        )
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.43.11 preactivation audit is not launchable")
    value = {
        "artifact_version": 1,
        "role": "v24311_paired_dev64_activation",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "active",
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "dependency_manifest_sha256": contract["dependency_manifest_sha256"],
        "control_manifest_sha256": protocol["control_manifest_sha256"],
        "selected_per_arm": SELECTED_COUNT,
        "executor_concurrency_per_arm": EXECUTOR_CONCURRENCY_PER_ARM,
        "total_executor_concurrency": TOTAL_EXECUTOR_CONCURRENCY,
        "model_slot_cap": MODEL_SLOT_CAP,
        "protected_watchers": audit["protected_watchers"],
        "shared_api_lease_active_before_activation": lease.get("active") is True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "exact220_leaderboard_or_sota_authorized": False,
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    activation = build_activation()
    publish_new(ROOT / ACTIVATION, activation)
    print(json.dumps({"path": str(ACTIVATION), "status": activation["status"]}, sort_keys=True))
