#!/usr/bin/env python3
"""Append-only invalidation for the failed V2.43.16 V1 build audit."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24315_forward_contract import payload_sha256  # noqa: E402


PARENT = Path("results/v24316_deadline_search_build_audit_v1_20260803.json")
INVALIDATION = Path(
    "results/v24316_deadline_search_build_audit_v1_invalidation_20260803.json"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_parent() -> dict[str, Any]:
    path = ROOT / PARENT
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
        raise RuntimeError("V2.43.16 V1 audit is not an ordinary repository file")
    value = json.loads(path.read_text(encoding="utf-8"))
    unsigned = dict(value)
    seal = unsigned.pop("audit_payload_sha256", None)
    if (
        not isinstance(value, dict)
        or value.get("role") != "v24316_deadline_search_build_audit"
        or value.get("audit_valid") is not False
        or value.get("findings") != ["focused_tests_failed"]
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.43.16 V1 audit identity drifted")
    return value


def build_invalidation(*, now: int | None = None) -> dict[str, Any]:
    read_parent()
    value = {
        "artifact_version": 1,
        "role": "v24316_deadline_search_build_audit_v1_invalidation",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "invalidated_artifact": {
            "path": str(PARENT),
            "sha256": sha256(ROOT / PARENT),
        },
        "reason": "isolated_python_module_discovery_failed_before_tests_ran",
        "production_source_or_runtime_failure": False,
        "v1_audit_valid_claim": False,
        "v1_future_integration_authority": False,
        "v1_benchmark_launch_authority": False,
        "v1_evaluator_authority": False,
        "v1_leaderboard_or_sota_authority": False,
        "active_v24315_run_signaled_restarted_resumed_rerun_or_modified": False,
    }
    value["invalidation_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    value = build_invalidation()
    publish_new(ROOT / INVALIDATION, value)
    print(json.dumps({"path": str(INVALIDATION)}, sort_keys=True))
