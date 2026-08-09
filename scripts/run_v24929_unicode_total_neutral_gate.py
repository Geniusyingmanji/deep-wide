#!/usr/bin/env python3
"""Run the one-shot aggregate-only V2.49.29 neutral production gate."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24929_unicode_total_neutral_contract as contract  # noqa: E402
from deepwide_agent import v24928_unicode_total_visible_row_compactor as projector  # noqa: E402
from scripts import run_v24635_exact220 as algorithm  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


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


def _new_json(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def configure_algorithm() -> None:
    bindings = {
        "PROTOCOL_ID": contract.PROTOCOL_ID,
        "CHILD_MARKER": contract.CHILD_MARKER,
        "OUTPUT_ROOT": contract.OUTPUT_ROOT,
        "MODEL_SLOT_DIRECTORY": contract.MODEL_SLOT_DIRECTORY,
        "TASK_ROOT": contract.TASK_ROOT,
        "SAFE_PROGRESS": contract.SAFE_PROGRESS,
        "SELECTED_COUNT": contract.SELECTED_COUNT,
        "EXECUTOR_CONCURRENCY": contract.EXECUTOR_CONCURRENCY,
        "MODEL_SLOT_CAP": contract.MODEL_SLOT_CAP,
        "LIMITS": contract.LIMITS,
        "PARENT_DEADLINE_GRACE_SECONDS": contract.PARENT_DEADLINE_GRACE_SECONDS,
    }
    for name, value in bindings.items():
        setattr(algorithm, name, value)


def _validate_authorization() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = _read(ROOT / contract.PROTOCOL)
    audit = _read(ROOT / contract.PREAUDIT)
    start = _read(ROOT / contract.EXECUTION_START)
    manifest = contract.source_manifest(ROOT)
    if (
        protocol.get("role") != "v24929_unicode_total_neutral_preregistration"
        or protocol.get("protocol_id") != contract.PROTOCOL_ID
        or protocol.get("source_manifest") != manifest
        or protocol.get("task_vector_sha256")
        != contract.payload_sha256(contract.task_vector())
        or not _sealed(protocol, "protocol_payload_sha256")
        or audit.get("role")
        != "v24929_unicode_total_neutral_preactivation_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or not _sealed(audit, "audit_payload_sha256")
        or start.get("role") != "v24929_unicode_total_neutral_execution_start"
        or start.get("status") != "authorized_not_started"
        or start.get("authorization", {}).get("single_fresh_neutral_gate") is not True
        or not _sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.49.29 execution authorization drifted")
    return protocol, start


def _active_conflicts() -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    markers = (
        contract.RUNNER_MARKER,
        contract.CHILD_MARKER,
        "scripts/run_official_eval_local.py",
    )
    rows = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if (
            len(parts) >= 3
            and int(parts[0]) != os.getpid()
            and "python" in parts[1].casefold()
            and any(marker in parts[2] for marker in markers)
        ):
            rows.append(int(parts[0]))
    return sorted(rows)


def _projection_receipt(directory: Path) -> dict[str, Any]:
    value = _read(directory / contract.PROJECTION_RECEIPT_NAME)
    unsigned = dict(value)
    seal = unsigned.pop("receipt_payload_sha256", None)
    if (
        value.get("role")
        != "v24929_content_free_unicode_total_projection_receipt"
        or seal != contract.payload_sha256(unsigned)
        or projector.target_value.validate_receipt(value.get("projection_receipt", {}))
        != value.get("projection_receipt")
        or projector.validate_receipt(value.get("compaction_receipt", {}))
        != value.get("compaction_receipt")
        or value.get(
            "contains_question_query_url_host_page_projection_prediction_or_hash"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read"
        )
        is not False
        or value.get("entropy_or_information_gain_assigns_credit") is not False
    ):
        raise ValueError("V2.49.29 projection receipt drifted")
    return value


def _aggregate(outcomes: list[Any], wall: float) -> dict[str, Any]:
    completion = Counter(str(item.result.get("completion_kind")) for item in outcomes)
    parent = Counter(
        str((item.parent_exit or {}).get("failure_taxonomy", "parent_unobserved"))
        for item in outcomes
    )
    model_generated = sum(
        item.result.get("completion_kind") in algorithm.MODEL_GENERATED
        for item in outcomes
    )
    accepted = sum(bool(item.accepted_parent_success) for item in outcomes)
    hard_timeouts = parent.get("hard_deadline_timeout", 0)
    hosted_deadlines = sum(
        int(item.transport.get("hosted_search_deadline_failures", 0))
        for item in outcomes
    )
    model_slot_timeouts = sum(int(item.model_slot_timeouts) for item in outcomes)
    projection_valid = expansion_tasks = expansion_characters = 0
    raw_chars = normalized_chars = output_chars = 0
    for position in range(1, contract.TASK_COUNT + 1):
        directory = ROOT / contract.TASK_ROOT / f"task_{position:04d}"
        try:
            receipt = _projection_receipt(directory)
        except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            continue
        projection_valid += 1
        compact = receipt["compaction_receipt"]
        expansion = int(compact["nfkc_expansion_characters"])
        expansion_tasks += int(expansion > 0)
        expansion_characters += expansion
        raw_chars += int(compact["raw_input_content_characters"])
        normalized_chars += int(compact["normalized_input_content_characters"])
        output_chars += int(compact["output_content_characters"])
    valid_retrieval = logical_queries = fetches = usable_pages = 0
    for item in outcomes:
        retrieval = item.result.get("two_wave_retrieval") or {}
        receipt = retrieval.get("receipt") or {}
        total = receipt.get("total") or {}
        if retrieval.get("status") != "completed" or not total:
            continue
        try:
            logical_queries += int(total["queries_executed"])
            fetches += int(total["fetches_attempted"])
            usable_pages += int(total["usable_pages"])
        except (KeyError, TypeError, ValueError):
            continue
        valid_retrieval += 1
    gate = bool(
        len(outcomes) == contract.TASK_COUNT
        and accepted >= contract.MINIMUM_ACCEPTED_PARENT_SUCCESSES
        and model_generated >= contract.MINIMUM_MODEL_GENERATED_TABLES
        and completion.get("worker_failure_fallback", 0) == 0
        and projection_valid >= contract.MINIMUM_VALID_PROJECTION_RECEIPTS
        and valid_retrieval >= contract.MINIMUM_VALID_RETRIEVAL_RECEIPTS
        and logical_queries >= contract.MINIMUM_LOGICAL_QUERIES
        and fetches <= contract.TASK_COUNT * contract.LIMITS["fetch_targets"]
        and usable_pages >= contract.MINIMUM_USABLE_PAGES
        and expansion_tasks >= contract.MINIMUM_REAL_NFKC_EXPANSION_TASKS
        and expansion_characters >= contract.MINIMUM_REAL_NFKC_EXPANSION_CHARACTERS
        and hard_timeouts <= contract.MAXIMUM_HARD_TIMEOUTS
        and hosted_deadlines <= contract.MAXIMUM_HOSTED_SEARCH_DEADLINE_FAILURES
        and model_slot_timeouts <= contract.MAXIMUM_MODEL_SLOT_TIMEOUTS
        and wall <= contract.MAXIMUM_FORWARD_WALL_SECONDS
    )
    return {
        "task_count": len(outcomes),
        "accepted_parent_successes": accepted,
        "model_generated_tables": model_generated,
        "fallback_tables": len(outcomes) - model_generated,
        "completion_kind_counts": dict(sorted(completion.items())),
        "parent_exit_taxonomy": dict(sorted(parent.items())),
        "valid_projection_receipts": projection_valid,
        "valid_retrieval_receipts": valid_retrieval,
        "real_nfkc_expansion_tasks": expansion_tasks,
        "real_nfkc_expansion_characters": expansion_characters,
        "raw_input_content_characters": raw_chars,
        "normalized_input_content_characters": normalized_chars,
        "compacted_output_content_characters": output_chars,
        "logical_queries_executed": logical_queries,
        "fetches_attempted": fetches,
        "usable_pages": usable_pages,
        "hard_timeouts": hard_timeouts,
        "hosted_search_deadline_failures": hosted_deadlines,
        "model_slot_timeouts": model_slot_timeouts,
        "forward_wall_seconds": round(max(0.0, wall), 6),
        "gate_passed": gate,
    }


def main() -> None:
    configure_algorithm()
    protocol, start = _validate_authorization()
    if (
        contract.git(ROOT, "status", "--porcelain")
        or contract.git(ROOT, "rev-parse", "HEAD")
        != contract.git(ROOT, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.49.29 launch requires clean pushed HEAD")
    conflicts = _active_conflicts()
    if conflicts:
        raise RuntimeError(f"V2.49.29 conflicting benchmark or evaluator active: {conflicts}")
    if (ROOT / contract.RESULT).exists() or (ROOT / contract.OUTPUT_ROOT).exists():
        raise RuntimeError("V2.49.29 execution surface is not pristine")
    with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
        pass
    if contract.protected_watcher_snapshot() != protocol["protected_watchers"]:
        raise RuntimeError("V2.49.29 protected watcher drifted")
    with acquire_deepwide_api_lease(
        ROOT,
        owner=contract.LEASE_OWNER,
        purpose=contract.LEASE_PURPOSE,
        path=ROOT / contract.LEASE_PATH,
    ):
        (ROOT / contract.OUTPUT_ROOT).mkdir(mode=0o700)
        algorithm._prepare_slots(ROOT)
        (ROOT / contract.TASK_ROOT).mkdir(mode=0o700)
        started = time.monotonic()
        outcomes = algorithm.execute_forward(ROOT, protocol, contract.task_vector())
        wall = max(0.0, time.monotonic() - started)
    aggregate = _aggregate(outcomes, wall)
    value = {
        "artifact_version": 1,
        "role": "v24929_unicode_total_neutral_result",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "status": "go" if aggregate["gate_passed"] else "no_go",
        "aggregate": aggregate,
        "execution_start_payload_sha256": start["execution_start_payload_sha256"],
        "runtime_input_keys": ["opaque_id", "question"],
        "private_task_question_query_url_page_prediction_answer_or_credential_persisted_in_result": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "benchmark_task_or_evaluator_used": False,
        "entropy_or_information_gain_used_for_admission_or_credit": False,
        "retry_resume_skip_or_selective_rerun": False,
        "authorization": {
            "next_benchmark_external_quality_gate_design": aggregate["gate_passed"],
            "public_exact220_launch": False,
            "evaluator": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["result_payload_sha256"] = contract.payload_sha256(value)
    _new_json(ROOT / contract.RESULT, value)
    print(json.dumps(value, sort_keys=True))


if __name__ == "__main__":
    main()
