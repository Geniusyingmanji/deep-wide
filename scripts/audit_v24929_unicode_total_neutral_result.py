#!/usr/bin/env python3
"""Post-result audit for the V2.49.29 neutral production gate."""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24929_unicode_total_neutral_contract as contract  # noqa: E402


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
        raise RuntimeError("V2.49.29 expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.29 expected object")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _lease_inactive() -> bool:
    path = ROOT / contract.LEASE_PATH
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def _active() -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,cmd="],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    markers = (contract.RUNNER_MARKER, contract.CHILD_MARKER)
    return [
        int(line.strip().split(maxsplit=1)[0])
        for line in completed.stdout.splitlines()
        if any(marker in line for marker in markers)
        and "audit_v24929_unicode_total_neutral_result.py" not in line
    ]


def build() -> dict[str, Any]:
    protocol = _read(ROOT / contract.PROTOCOL)
    result = _read(ROOT / contract.RESULT)
    aggregate = result.get("aggregate") or {}
    checks = {
        "protocol_sealed": _sealed(protocol, "protocol_payload_sha256"),
        "result_sealed": _sealed(result, "result_payload_sha256"),
        "task_count_20": aggregate.get("task_count") == 20,
        "accepted_parent_successes_20": aggregate.get(
            "accepted_parent_successes"
        )
        == 20,
        "model_generated_tables_20": aggregate.get("model_generated_tables") == 20,
        "fallback_tables_zero": aggregate.get("fallback_tables") == 0,
        "valid_projection_receipts_20": aggregate.get(
            "valid_projection_receipts"
        )
        == 20,
        "valid_retrieval_receipts_20": aggregate.get("valid_retrieval_receipts")
        == 20,
        "real_nfkc_expansion_observed": int(
            aggregate.get("real_nfkc_expansion_tasks", 0)
        )
        >= contract.MINIMUM_REAL_NFKC_EXPANSION_TASKS
        and int(aggregate.get("real_nfkc_expansion_characters", 0))
        >= contract.MINIMUM_REAL_NFKC_EXPANSION_CHARACTERS,
        "hard_timeouts_zero": aggregate.get("hard_timeouts") == 0,
        "hosted_search_deadline_failures_zero": aggregate.get(
            "hosted_search_deadline_failures"
        )
        == 0,
        "model_slot_timeouts_zero": aggregate.get("model_slot_timeouts") == 0,
        "gate_status_consistent": result.get("status")
        == ("go" if aggregate.get("gate_passed") is True else "no_go"),
        "runner_and_children_absent": not _active(),
        "shared_api_lease_released": _lease_inactive(),
        "protected_watchers_unchanged": contract.protected_watcher_snapshot()
        == protocol["protected_watchers"],
        "no_retry_resume_or_selective_rerun": result.get(
            "retry_resume_skip_or_selective_rerun"
        )
        is False,
        "benchmark_or_evaluator_not_used": result.get("benchmark_task_or_evaluator_used")
        is False,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v24929_unicode_total_neutral_postresult_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "result_sha256": contract.sha256(ROOT / contract.RESULT),
        "aggregate": aggregate,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "source_policy": {
            "benchmark_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "private_task_query_url_page_prediction_or_answer_persisted_by_audit": False,
            "entropy_or_information_gain_used_for_admission_or_credit": False,
        },
        "authorization": {
            "next_benchmark_external_quality_gate_design": not findings
            and result.get("status") == "go",
            "public_exact220": False,
            "evaluator": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def main() -> None:
    value = build()
    path = ROOT / contract.POSTAUDIT
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    print(
        json.dumps(
            {
                "path": str(contract.POSTAUDIT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
