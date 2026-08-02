#!/usr/bin/env python3
"""Read-only preactivation audit for V2.42.61."""

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

from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.preregister_v24261_direct_executor_smoke import ACTIVATION, OUTPUT, RESULT, ROLE as PROTOCOL_ROLE, publish, validate_protocol  # noqa: E402
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402


OUTPUT_PATH = Path("results/v24261_direct_executor_smoke_preactivation_audit_v1_20260802.json")


def build_report(root: Path = ROOT):
    root = root.resolve()
    validate_protocol(root, OUTPUT)
    lease = lease_observation(root, Path("/proc"))
    value = {"artifact_version": 1, "role": "v24261_direct_executor_smoke_audit", "created_at_unix": int(time.time()), "label_blind": True, "protocol": {"path": str(OUTPUT), "sha256": sha256(root / OUTPUT), "role": PROTOCOL_ROLE}, "activation_present": (root / ACTIVATION).exists(), "result_present": (root / RESULT).exists(), "shared_api_lease_active": lease.get("active") is True, "runtime_monkeypatch_used": False, "run_one_task_failure_injection_popen_count": 1, "mapping_gold_category_question_type_evaluator_score_read": False, "credential_value_or_keyring_read": False, "network_model_search_fetch_or_evaluator_api_called_by_audit": False, "official_evaluator_dev64_full220_or_leaderboard_authorized": False, "audit_valid": True}
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    publish(ROOT / OUTPUT_PATH, build_report())
    print(json.dumps({"path": str(OUTPUT_PATH), "sha256": sha256(ROOT / OUTPUT_PATH)}))
