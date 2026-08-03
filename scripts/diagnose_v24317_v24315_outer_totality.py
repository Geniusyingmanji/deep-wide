#!/usr/bin/env python3
"""Publish a content-free diagnosis of V2.43.15 outer-totality fallbacks.

The exact-220 predictions were already frozen and the evaluator remained
closed.  This post-terminal diagnostic reads only aggregate counters, fixed
failure stages, and sealed receipts.  It never emits task identifiers,
questions, prompts, responses, predictions, queries, URLs, pages, labels, or
evaluator-side data.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24287_hard_deadline_fetch import (  # noqa: E402
    validate_transport_health,
)
from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    validate_child_receipt,
    validate_parent_receipt,
)
from deepwide_agent.v24313_runner_integration import (  # noqa: E402
    validate_deadline_model_receipt,
)
from deepwide_agent.v24315_forward_contract import (  # noqa: E402
    MODEL_SLOT_CAP,
    OUTPUT_ROOT,
    SELECTED_COUNT,
    payload_sha256,
)
from scripts.publish_v24315_exact220_forward_nogo import (  # noqa: E402
    RESULT as PARENT_RESULT,
    validate_result as validate_parent_result,
)


RESULT = Path("results/v24317_v24315_outer_totality_diagnosis_v1_20260803.json")
EXPECTED_POSITIONS = (
    19,
    20,
    28,
    48,
    67,
    71,
    85,
    91,
    99,
    109,
    118,
    123,
    132,
    155,
    164,
    165,
    167,
    168,
)
BOUND_SOURCES = (
    Path("src/deepwide_agent/v24257_score_first_runtime.py"),
    Path("src/deepwide_agent/v24296_staged_reserve_task_runtime.py"),
    Path("src/deepwide_agent/v24299_synthesis_recovery.py"),
    Path("src/deepwide_agent/v24310_paired_dev_runtime.py"),
    Path("src/deepwide_agent/v24312_deadline_reliability.py"),
    Path("src/deepwide_agent/v24316_deadline_search.py"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ordinary(path: Path) -> Path:
    target = path.resolve(strict=False)
    if path.is_symlink() or not path.is_file() or not target.is_relative_to(ROOT):
        raise RuntimeError("V2.43.17 expected an ordinary repository file")
    return path


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.43.17 expected a JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _task_directory(root: Path, position: int) -> Path:
    directory = root / OUTPUT_ROOT / "tasks" / f"task_{position:04d}"
    target = directory.resolve(strict=False)
    output = (root / OUTPUT_ROOT).resolve()
    if directory.is_symlink() or not directory.is_dir() or not target.is_relative_to(output):
        raise RuntimeError("V2.43.17 task directory is invalid")
    return directory


def _outer_failure(result: Mapping[str, Any]) -> bool:
    failures = result.get("failures")
    return isinstance(failures, list) and any(
        isinstance(item, Mapping)
        and item.get("stage") == "v24312_outer_totality"
        and item.get("type") == "ValidationError"
        for item in failures
    )


def _row(root: Path, position: int) -> dict[str, Any]:
    directory = _task_directory(root, position)
    envelope = _read(directory / "result.json")
    result = envelope.get("result")
    if not isinstance(result, Mapping) or not _outer_failure(result):
        raise RuntimeError("V2.43.17 expected one outer-totality fallback")
    progress = _read(directory / "safe_progress.json")
    model = validate_deadline_model_receipt(
        _read(directory / "model_slot_receipt.json"), expected_cap=MODEL_SLOT_CAP
    )
    transport = validate_transport_health(_read(directory / "transport_health.json"))
    validate_child_receipt(_read(directory / "child_terminal_receipt.json"))
    parent = validate_parent_receipt(_read(directory / "parent_exit_receipt.json"))
    if parent["failure_taxonomy"] != "success":
        raise RuntimeError("V2.43.17 outer fallback lacked a successful parent envelope")
    model_cost = result.get("cost", {}).get("model", {})
    progress_model = progress.get("model_cost", {})
    search_cost = progress.get("search_cost", {})
    stage = str(progress.get("stage"))
    slot_timeouts = int(model["slot_timeouts"])
    provider_requests = int(model_cost.get("requests", -1))
    acquisitions = int(model["acquisitions"])
    if acquisitions != provider_requests:
        raise RuntimeError("V2.43.17 provider request/slot accounting drifted")
    cause = (
        "logical_model_admission_rejected_before_provider"
        if slot_timeouts > 0
        else "deadline_deferred_cached_pages"
    )
    return {
        "position": position,
        "last_safe_stage": stage,
        "last_safe_elapsed_seconds": float(progress.get("elapsed_seconds", 0.0)),
        "progress_model_requests": int(progress_model.get("requests", 0)),
        "terminal_model_requests": provider_requests,
        "terminal_model_attempts": int(model_cost.get("attempts", -1)),
        "model_slot_acquisitions": acquisitions,
        "model_slot_timeouts": slot_timeouts,
        "model_provider_deadline_failures": int(model["provider_deadline_failures"]),
        "deadline_exhausted_at_receipt": bool(model["deadline_exhausted"]),
        "admitted_model_calls_at_last_safe_progress": int(
            progress.get("admitted_model_calls", 0)
        ),
        "admitted_fetch_targets_at_last_safe_progress": int(
            progress.get("admitted_fetch_targets", 0)
        ),
        "search_fetch_calls_at_last_safe_progress": int(
            search_cost.get("fetch_calls", 0)
        ),
        "search_fetch_failures_at_last_safe_progress": int(
            search_cost.get("fetch_failures", 0)
        ),
        "hard_fetch_deadline_failures": int(
            transport["hard_fetch_deadline_failures"]
        ),
        "mechanical_cause": cause,
    }


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    parent = _read(root / PARENT_RESULT)
    validate_parent_result(root, parent)
    observed: list[int] = []
    for position in range(1, SELECTED_COUNT + 1):
        path = _task_directory(root, position) / "result.json"
        if not path.is_file() or path.is_symlink():
            continue
        envelope = _read(path)
        result = envelope.get("result")
        if isinstance(result, Mapping) and _outer_failure(result):
            observed.append(position)
    if tuple(observed) != EXPECTED_POSITIONS:
        raise RuntimeError("V2.43.17 outer-totality position set drifted")
    rows = [_row(root, position) for position in observed]
    causes = Counter(str(row["mechanical_cause"]) for row in rows)
    stages = Counter(str(row["last_safe_stage"]) for row in rows)
    source_manifest = {
        str(relative): sha256(_ordinary(root / relative)) for relative in BOUND_SOURCES
    }
    findings: list[str] = []
    slot_rows = [row for row in rows if row["model_slot_timeouts"] > 0]
    cache_rows = [row for row in rows if row["model_slot_timeouts"] == 0]
    if len(slot_rows) != 17:
        findings.append("pre_provider_rejection_count_mismatch")
    if any(
        row["model_slot_acquisitions"] != row["terminal_model_requests"]
        or row["deadline_exhausted_at_receipt"] is not True
        for row in slot_rows
    ):
        findings.append("pre_provider_rejection_receipt_invariant_failed")
    if (
        len(cache_rows) != 1
        or cache_rows[0]["position"] != 118
        or cache_rows[0]["last_safe_stage"] != "terminal"
        or cache_rows[0]["last_safe_elapsed_seconds"] <= 180
        or cache_rows[0]["admitted_fetch_targets_at_last_safe_progress"] != 0
        or cache_rows[0]["search_fetch_calls_at_last_safe_progress"]
        <= cache_rows[0]["search_fetch_failures_at_last_safe_progress"]
    ):
        findings.append("deadline_deferred_cache_signature_failed")
    value = {
        "artifact_version": 1,
        "role": "v24317_v24315_outer_totality_content_free_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_nogo": {
            "path": str(PARENT_RESULT),
            "sha256": sha256(root / PARENT_RESULT),
        },
        "source_manifest": source_manifest,
        "source_manifest_sha256": payload_sha256(source_manifest),
        "selected": SELECTED_COUNT,
        "outer_totality_fallbacks": len(rows),
        "positions": observed,
        "rows": rows,
        "stage_counts": {name: int(stages[name]) for name in sorted(stages)},
        "mechanical_cause_counts": {
            name: int(causes[name]) for name in sorted(causes)
        },
        "mechanical_conclusion": {
            "logical_model_admission_must_equal_provider_request_plus_pre_provider_rejection": True,
            "cached_usable_pages_must_equal_served_plus_deadline_deferred_pages": True,
            "existing_strict_equalities_reject_valid_deadline_stops": True,
            "quality_effect_or_sota_inferred": False,
        },
        "source_policy": {
            "all_220_predictions_frozen_before_diagnosis": True,
            "same_run_mapping_gold_category_question_type_split_evaluator_score_read": False,
            "question_opaque_id_prompt_response_prediction_query_url_page_or_credential_emitted": False,
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "findings": findings,
        "diagnosis_valid": not findings,
        "authorization": {
            "append_only_accounting_fix_design": not findings,
            "benchmark_launch": False,
            "same_run_evaluator": False,
            "same_run_retry_resume_or_selective_rerun": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    validate_report(root, value)
    return value


def validate_report(root: Path, value: Mapping[str, Any]) -> None:
    rows = value.get("rows")
    causes = value.get("mechanical_cause_counts")
    if (
        value.get("artifact_version") != 1
        or value.get("role")
        != "v24317_v24315_outer_totality_content_free_diagnosis"
        or value.get("parent_nogo")
        != {"path": str(PARENT_RESULT), "sha256": sha256(root / PARENT_RESULT)}
        or value.get("selected") != SELECTED_COUNT
        or value.get("outer_totality_fallbacks") != len(EXPECTED_POSITIONS)
        or value.get("positions") != list(EXPECTED_POSITIONS)
        or not isinstance(rows, list)
        or [row.get("position") for row in rows if isinstance(row, Mapping)]
        != list(EXPECTED_POSITIONS)
        or causes
        != {
            "deadline_deferred_cached_pages": 1,
            "logical_model_admission_rejected_before_provider": 17,
        }
        or value.get("stage_counts")
        != {"page_projection_terminal": 16, "synthesis_terminal": 1, "terminal": 1}
        or value.get("source_policy", {}).get(
            "same_run_mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or value.get("source_policy", {}).get(
            "question_opaque_id_prompt_response_prediction_query_url_page_or_credential_emitted"
        )
        is not False
        or value.get("source_policy", {}).get(
            "network_model_search_fetch_or_evaluator_called"
        )
        is not False
        or value.get("diagnosis_valid") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get("benchmark_launch") is not False
        or not _sealed(value, "diagnosis_payload_sha256")
    ):
        raise RuntimeError("V2.43.17 diagnosis drifted")


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    report = build_report()
    publish_new(ROOT / RESULT, report)
    print(json.dumps({"path": str(RESULT), "diagnosis_valid": True}, sort_keys=True))
