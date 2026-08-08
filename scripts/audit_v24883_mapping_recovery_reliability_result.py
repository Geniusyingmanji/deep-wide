#!/usr/bin/env python3
"""Read-only post-result audit for the neutral V2.48.83 gate."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24883_mapping_recovery_reliability_contract as contract  # noqa: E402
from deepwide_agent.v24879_mapping_recovery_effect_bundle import (  # noqa: E402
    validate_bundle,
)
from deepwide_agent.v24882_mapping_recovery_stage_runtime import (  # noqa: E402
    STAGE_NAME,
    validate_stage_receipt,
)


AUDIT = Path(
    "results/v24883_mapping_recovery_reliability_postresult_audit_v1_20260808.json"
)


def _read(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.48.83 audit expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.83 audit expected object")
    return value


def _sealed(value: dict, field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def build() -> dict:
    if (ROOT / AUDIT).exists() or (ROOT / AUDIT).is_symlink():
        raise FileExistsError(AUDIT)
    protocol = _read(ROOT / contract.PROTOCOL)
    result = _read(ROOT / contract.RESULT)
    valid = 0
    stages = 0
    for position in range(1, contract.TASK_COUNT + 1):
        directory = ROOT / contract.TASK_ROOT / f"task_{position:04d}"
        validate_bundle(
            output_root=ROOT / contract.OUTPUT_ROOT,
            directory=directory,
            expected_model_slot_cap=contract.MODEL_SLOT_CAP,
        )
        stage = validate_stage_receipt(_read(directory / STAGE_NAME))
        valid += 1
        stages += int(stage["stage"] == "bundle_committed")
    checks = {
        "protocol_sealed": _sealed(protocol, "protocol_payload_sha256"),
        "result_sealed": _sealed(result, "result_payload_sha256"),
        "gate_passed": result.get("gate_passed") is True,
        "valid_bundles_exact20": valid == 20 == result.get("valid_bundles"),
        "bundle_committed_stage_exact20": stages == 20,
        "hard_timeouts_zero": result.get("hard_timeouts") == 0,
        "subprocess_exceptions_zero": result.get("subprocess_exceptions") == 0,
        "benchmark_or_evaluator_unused": result.get("benchmark_task_or_evaluator_used")
        is False,
        "protected_watchers_unchanged": contract.protected_watcher_snapshot()
        == protocol["protected_watchers"],
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v24883_mapping_recovery_reliability_postresult_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "result_sha256": contract.sha256(ROOT / contract.RESULT),
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "next_exact220_protocol_design": not findings,
            "exact220_launch": False,
            "evaluator": False,
        },
        "private_task_query_url_page_prediction_answer_or_credential_read_or_persisted_by_audit": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "network_model_search_fetch_or_evaluator_called_by_audit": False,
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def main() -> None:
    value = build()
    path = ROOT / AUDIT
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    print(json.dumps({"path": str(AUDIT), "audit_valid": value["audit_valid"], "findings": value["findings"]}, sort_keys=True))


if __name__ == "__main__":
    main()
