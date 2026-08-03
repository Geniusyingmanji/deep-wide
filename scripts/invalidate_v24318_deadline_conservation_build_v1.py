#!/usr/bin/env python3
"""Invalidate the V2.43.18 V1 audit after its source-hook false negative."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24315_forward_contract import payload_sha256  # noqa: E402


V1 = Path("results/v24318_deadline_conservation_build_audit_v1_20260803.json")
INVALIDATION = Path(
    "results/v24318_deadline_conservation_build_audit_v1_invalidation_20260803.json"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(*, now: int | None = None) -> dict[str, Any]:
    value = json.loads((ROOT / V1).read_text(encoding="utf-8"))
    if (
        value.get("role") != "v24318_deadline_conservation_build_audit"
        or value.get("audit_valid") is not False
        or value.get("findings") != ["conservation_or_budget_hook_absent"]
        or value.get("authorization", {}).get("future_runner_integration_design")
        is not False
    ):
        raise RuntimeError("V2.43.18 V1 audit is not the expected false negative")
    output = {
        "artifact_version": 1,
        "role": "v24318_deadline_conservation_build_audit_v1_invalidation",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "invalidated_artifact": {"path": str(V1), "sha256": sha256(ROOT / V1)},
        "cause": "source_hook_whitespace_match_false_negative",
        "v1_audit_valid_claim": False,
        "v1_future_runner_integration_authority": False,
        "v1_benchmark_launch_authority": False,
        "v1_evaluator_leaderboard_or_sota_authority": False,
        "implementation_or_test_result_invalidated": False,
        "network_model_search_fetch_or_evaluator_called": False,
    }
    output["invalidation_payload_sha256"] = payload_sha256(output)
    return output


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    value = build()
    publish_new(ROOT / INVALIDATION, value)
    print(json.dumps({"path": str(INVALIDATION), "invalidated": True}, sort_keys=True))
