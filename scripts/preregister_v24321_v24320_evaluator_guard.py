#!/usr/bin/env python3
"""Freeze the append-only V2.43.21 guard before V2.43.20 evaluation."""

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

from deepwide_agent.v24320_forward_contract import (
    ACTIVATION,
    EXECUTION_START,
    FORWARD_CONTRACT,
    FULL_PROTOCOL,
    payload_sha256,
    sha256,
)
from deepwide_agent.v24321_v24320_evaluator_guard import (
    DECISION,
    POLICY_ID,
    PREREGISTRATION,
    SOURCE_FILES,
)


def build(root: Path = ROOT, *, now: int | None = None) -> dict:
    root = root.resolve()
    if (root / DECISION).exists() or (root / DECISION).is_symlink():
        raise RuntimeError("V2.43.21 decision surface is not pristine")
    manifest = {name: sha256(root / name) for name in SOURCE_FILES}
    value = {
        "artifact_version": 1,
        "role": "v24321_v24320_evaluator_guard_preregistration",
        "policy_id": POLICY_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_provenance": {
            "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
            "protocol_sha256": sha256(root / FULL_PROTOCOL),
            "activation_sha256": sha256(root / ACTIVATION),
            "execution_start_sha256": sha256(root / EXECUTION_START),
        },
        "required_checks": [
            "both arms exact64 and frozen",
            "64 valid parent, child, model, and transport receipts per arm",
            "64 accepted parent successes and zero non-success per arm",
            "zero incomplete effect counts and exact conservation per arm",
            "runner and children absent; shared lease inactive",
            "protected watcher identities unchanged",
            "evaluator surface absent before positive decision",
        ],
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "runtime_boundary_unchanged": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "authorization": {
            "publish_guard_after_forward_freeze": True,
            "evaluator_before_positive_guard": False,
            "exact220_leaderboard_or_sota": False,
        },
    }
    value["preregistration_payload_sha256"] = payload_sha256(value)
    return value


def publish(path: Path, value: dict) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    publish(ROOT / PREREGISTRATION, build())
    print(json.dumps({"path": str(PREREGISTRATION)}, sort_keys=True))
