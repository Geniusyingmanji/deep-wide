#!/usr/bin/env python3
"""Append-only revocation for the never-activated V2.43.94 protocol."""

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

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402


DATE = "20260804"
PROTOCOL_ID = "v24394_fresh_uncertainty_active_evidence_external_gate_v1"
PROTOCOL = Path(
    f"results/v24394_uncertainty_external_preregistration_v1_{DATE}.json"
)
REVOCATION = Path(
    f"results/v24394_uncertainty_external_revocation_v1_{DATE}.json"
)
FUTURE_SURFACES = (
    Path(f"results/v24394_uncertainty_external_preactivation_audit_v1_{DATE}.json"),
    Path(f"results/v24394_uncertainty_external_activation_v1_{DATE}.json"),
    Path(f"results/v24394_uncertainty_external_execution_start_v1_{DATE}.json"),
    Path(f"results/v24394_uncertainty_external_result_v1_{DATE}.json"),
    Path(f"results/v24394_uncertainty_external_decision_v1_{DATE}.json"),
    Path(f"results/v24394_uncertainty_external_postresult_audit_v1_{DATE}.json"),
)
OUTPUT_ROOT = Path(f"outputs/v24394_uncertainty_external_v1_{DATE}")
LEASE = Path("outputs/deepwide_benchmark_api.lease.lock")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected object: {path}")
    return value


def build(*, now: int | None = None) -> dict[str, Any]:
    protocol = _read(ROOT / PROTOCOL)
    if (
        protocol.get("role") != "v24394_uncertainty_external_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or protocol.get("authorization", {}).get("external_probe_launch") is not False
    ):
        raise RuntimeError("unexpected V2.43.94 protocol")
    present = [str(path) for path in FUTURE_SURFACES if (ROOT / path).exists()]
    if present:
        raise RuntimeError("V2.43.94 had already advanced: " + ",".join(present))
    if (ROOT / OUTPUT_ROOT).exists():
        raise RuntimeError("V2.43.94 execution output unexpectedly exists")
    lease = _read(ROOT / LEASE)
    if lease.get("active") is not False or lease.get("owner") == PROTOCOL_ID:
        raise RuntimeError("V2.43.94 lease state is not an inactive foreign lease")
    value = {
        "artifact_version": 1,
        "role": "v24394_uncertainty_external_revocation",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "revoked_protocol": {
            "path": str(PROTOCOL),
            "sha256": sha256(ROOT / PROTOCOL),
        },
        "cause": "isolated_focused_test_repository_root_missing_from_sys_path",
        "failure": {
            "test": "tests/test_v24393_uncertainty_external_projection.py",
            "isolated_interpreter": True,
            "return_code": 1,
            "exception_type": "ModuleNotFoundError",
            "missing_module": "scripts",
        },
        "preactivation_audit_published": False,
        "activation_published": False,
        "execution_start_published": False,
        "result_or_decision_published": False,
        "execution_output_created": False,
        "shared_api_lease_acquired": False,
        "network_model_search_fetch_or_evaluator_called": False,
        "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "protected_benchmark_or_watcher_signaled_restarted_modified_or_terminated": False,
        "authorization": {
            "v24394_external_probe_launch": False,
            "v24394_resume_retry_or_rerun": False,
            "benchmark_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
            "append_only_successor_design": True,
        },
    }
    value["revocation_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    artifact = build()
    publish_new(ROOT / REVOCATION, artifact)
    print(json.dumps({"path": str(REVOCATION), "revoked": True}, sort_keys=True))
