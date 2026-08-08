#!/usr/bin/env python3
"""Aggregate-only diagnosis of the V2.49.18 post-retrieval failures.

This script reads the already frozen forward artifacts after evaluation.  It
emits counts only: no task identifier, question, query, URL, page, prediction,
answer, or evaluator row is copied to the report.  The synthetic reproduction
uses benchmark-external placeholder pages and performs no network/model I/O.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24916_prefix_total_long_page_packer as packer  # noqa: E402
from deepwide_agent.v24916_prefix_total_runtime_binding import (  # noqa: E402
    project_evidence,
)
from scripts.audit_v24635_exact220 import (  # noqa: E402
    _accesses,
    _evaluator_capabilities,
)


DATE = "20260808"
ROLE = "v24919_v24918_aggregate_total_projection_failure_diagnosis"
OUTPUT = Path(
    f"results/v24919_v24918_total_projection_failure_diagnosis_v1_{DATE}.json"
)
RESULT = Path(f"results/v24918_prefix_total_exact220_result_v2_{DATE}.json")
POSTAUDIT = Path(
    f"results/v24918_prefix_total_exact220_postresult_audit_v2_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v24918_prefix_total_exact220_v2_{DATE}")
TASK_ROOT = OUTPUT_ROOT / "tasks"
SELECTED = 220
TOTAL_OVERFLOW = "V2.49.11 rendered projection exceeded total cap"
SOURCE_FILES = (
    Path("src/deepwide_agent/v24911_long_page_evidence_packer.py"),
    Path("src/deepwide_agent/v24916_prefix_total_long_page_packer.py"),
    Path("src/deepwide_agent/v24916_prefix_total_runtime_binding.py"),
    Path("scripts/diagnose_v24919_v24918_total_projection_failure.py"),
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.49.19 expected ordinary file: {relative}")
    return path


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.19 expected JSON object")
    return value


def _sha(relative: Path) -> str:
    return hashlib.sha256(_ordinary(relative).read_bytes()).hexdigest()


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == packer.long_parent.payload_sha256(unsigned)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _task_directories() -> list[Path]:
    root = ROOT / TASK_ROOT
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("V2.49.19 frozen task root is absent")
    values = [root / f"task_{position:04d}" for position in range(1, SELECTED + 1)]
    if any(path.is_symlink() or not path.is_dir() for path in values):
        raise RuntimeError("V2.49.19 frozen task partition is incomplete")
    return values


def _progress(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24257_score_first_safe_progress"
        or copied.get("stage") not in {
            "retrieval_terminal",
            "page_projection_terminal",
            "synthesis_terminal",
            "repair_or_fallback_ready",
            "terminal",
        }
        or copied.get("contains_question_query_url_page_prediction_or_answer") is not False
        or copied.get("mapping_gold_evaluator_or_score_read") is not False
    ):
        raise RuntimeError("V2.49.19 unsafe or invalid progress receipt")
    for name in (
        "admitted_model_calls",
        "admitted_search_queries",
        "admitted_fetch_targets",
        "search_batch_count",
        "projected_chars",
    ):
        amount = copied.get(name)
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise RuntimeError("V2.49.19 invalid progress count")
    elapsed = copied.get("elapsed_seconds")
    if (
        isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not math.isfinite(float(elapsed))
        or float(elapsed) < 0
    ):
        raise RuntimeError("V2.49.19 invalid progress elapsed time")
    return copied


def _distribution(values: Sequence[int]) -> dict[str, int]:
    return {str(key): amount for key, amount in sorted(Counter(values).items())}


def _synthetic_pages(count: int, *, long_url: bool) -> list[dict[str, str]]:
    content = (("Entity Value " + "x" * 40) + "\n\n") * 200
    pages: list[dict[str, str]] = []
    for index in range(count):
        prefix = f"https://source-{index}.example/"
        url = prefix + ("u" * (8_192 - len(prefix)) if long_url else "data")
        pages.append({"title": "T" * 500, "url": url, "content": content})
    return pages


def _synthetic_reproduction() -> dict[str, Any]:
    question = "Return one table. Columns: Entity, Value"
    cases = 0
    total_overflows = 0
    first_error = ""
    runtime_binding_overflow = False
    for page_count in (6, 8, 9, 10):
        for long_url in (False, True):
            cases += 1
            pages = _synthetic_pages(page_count, long_url=long_url)
            try:
                packer.build_prefix_total_packing(question, pages)
            except RuntimeError as error:
                total_overflows += int(str(error) == TOTAL_OVERFLOW)
                first_error = first_error or str(error)
    pages = _synthetic_pages(10, long_url=True)
    batches = [
        {
            "results": [
                {
                    "title": page["title"],
                    "url": page["url"],
                    "raw_content": page["content"],
                }
            ]
        }
        for page in pages
    ]
    try:
        project_evidence(
            question,
            [],
            batches,
            SimpleNamespace(page_chars=12_000, evidence_chars=60_000),
        )
    except RuntimeError as error:
        runtime_binding_overflow = str(error) == TOTAL_OVERFLOW
    short = packer.build_prefix_total_packing(
        question,
        [
            {
                "title": "Official",
                "url": "https://short.example/data",
                "content": "Entity Value: 1",
            }
        ],
    )
    duplicate = packer.build_prefix_total_packing(
        question,
        [
            {
                "title": "First",
                "url": "https://duplicate.example/data",
                "content": "Entity Value: 1",
            },
            {
                "title": "Second",
                "url": "https://duplicate.example/data",
                "content": "Entity Value: 2",
            },
        ],
    )
    return {
        "production_shaped_cases": cases,
        "exact_total_render_overflow_cases": total_overflows,
        "total_render_overflow_reproduced": total_overflows > 0,
        "first_error_class": "RuntimeError" if first_error else "",
        "first_error_matches_exact_total_cap": first_error == TOTAL_OVERFLOW,
        "runtime_binding_exact_total_cap_reproduced": runtime_binding_overflow,
        "short_page_control_succeeds": bool(short["projection"]),
        "duplicate_url_control_deduplicates": (
            duplicate["content_free_receipt"]["input_page_count"] == 1
        ),
        "network_model_search_fetch_or_evaluator_called": False,
        "question_url_page_or_projection_persisted": False,
    }


def summarize() -> dict[str, Any]:
    completion: Counter[str] = Counter()
    progress_stage: Counter[str] = Counter()
    failure_type: Counter[str] = Counter()
    failed_fetch_calls: list[int] = []
    generated_fetch_calls: list[int] = []
    failed_hosted_attempts = 0
    failed_hard_fetch_calls = 0
    failed_hard_fetch_deadlines = 0
    failed_fetch_helper_failures = 0
    failed_model_calls: list[int] = []
    failed_search_queries: list[int] = []
    failed_projection_input_pages: list[int] = []
    generated_projection_input_pages: list[int] = []
    failed_elapsed: list[float] = []
    generated_elapsed: list[float] = []

    for directory in _task_directories():
        envelope = _read(directory.relative_to(ROOT) / "result.json")
        result = envelope.get("result")
        if not isinstance(result, Mapping):
            raise RuntimeError("V2.49.19 task result envelope drifted")
        progress = _progress(
            _read(directory.relative_to(ROOT) / "safe_progress.json")
        )
        projection = packer.validate_receipt(
            _read(directory.relative_to(ROOT) / "projection_receipt.json")
        )
        transport = envelope.get("transport_health")
        if not isinstance(transport, Mapping):
            raise RuntimeError("V2.49.19 transport receipt is absent")
        kind = str(result.get("completion_kind", ""))
        completion[kind] += 1
        progress_stage[str(progress["stage"])] += 1
        is_failed = kind == "worker_failure_fallback"
        failures = result.get("failures")
        if is_failed:
            if not isinstance(failures, list) or len(failures) != 1:
                raise RuntimeError("V2.49.19 fallback failure vector drifted")
            failure_type[str(failures[0].get("type", ""))] += 1
        search_cost = result.get("cost", {}).get("search", {})
        fetch_calls = int(search_cost.get("fetch_calls", 0))
        elapsed = float(result.get("budget", {}).get("elapsed_seconds", 0.0))
        if is_failed:
            failed_fetch_calls.append(fetch_calls)
            failed_hosted_attempts += int(transport.get("hosted_search_attempts", 0))
            failed_hard_fetch_calls += int(transport.get("hard_fetch_helper_calls", 0))
            failed_hard_fetch_deadlines += int(
                transport.get("hard_fetch_deadline_failures", 0)
            )
            failed_fetch_helper_failures += int(
                transport.get("fetch_helper_failures", 0)
            )
            failed_model_calls.append(
                int(result.get("budget", {}).get("admitted_model_calls", 0))
            )
            failed_search_queries.append(
                int(result.get("budget", {}).get("admitted_search_queries", 0))
            )
            failed_projection_input_pages.append(int(projection["input_page_count"]))
            failed_elapsed.append(elapsed)
        else:
            generated_fetch_calls.append(fetch_calls)
            generated_projection_input_pages.append(int(projection["input_page_count"]))
            generated_elapsed.append(elapsed)

    failed = completion["worker_failure_fallback"]
    return {
        "selected": sum(completion.values()),
        "completion_kind_counts": dict(sorted(completion.items())),
        "last_safe_progress_stage_counts": dict(sorted(progress_stage.items())),
        "fallback_failure_type_counts": dict(sorted(failure_type.items())),
        "fallback_admitted_model_call_distribution": _distribution(failed_model_calls),
        "fallback_admitted_search_query_distribution": _distribution(
            failed_search_queries
        ),
        "fallback_actual_fetch_call_distribution": _distribution(failed_fetch_calls),
        "generated_actual_fetch_call_distribution": _distribution(
            generated_fetch_calls
        ),
        "fallback_projection_input_page_distribution": _distribution(
            failed_projection_input_pages
        ),
        "generated_projection_input_page_distribution": _distribution(
            generated_projection_input_pages
        ),
        "fallback_transport_totals": {
            "hosted_search_attempts": failed_hosted_attempts,
            "hard_fetch_helper_calls": failed_hard_fetch_calls,
            "hard_fetch_deadline_failures": failed_hard_fetch_deadlines,
            "fetch_helper_failures": failed_fetch_helper_failures,
        },
        "fallback_elapsed_seconds": {
            "minimum": round(min(failed_elapsed), 6),
            "maximum": round(max(failed_elapsed), 6),
            "mean": round(sum(failed_elapsed) / failed, 6),
        },
        "generated_elapsed_seconds": {
            "minimum": round(min(generated_elapsed), 6),
            "maximum": round(max(generated_elapsed), 6),
            "mean": round(sum(generated_elapsed) / len(generated_elapsed), 6),
        },
    }


def _source_audit() -> dict[str, Any]:
    privileged: list[str] = []
    evaluator: list[str] = []
    secrets: list[str] = []
    for relative in SOURCE_FILES:
        path = _ordinary(relative)
        privileged.extend(_accesses(path, ROOT))
        evaluator.extend(_evaluator_capabilities(path, ROOT))
        if SECRET.search(path.read_text(encoding="utf-8")):
            secrets.append(str(relative))
    return {
        "runtime_privileged_access_hits": sorted(privileged),
        "evaluator_capability_hits": sorted(evaluator),
        "credential_literal_files": sorted(secrets),
    }


def build(*, now: int | None = None) -> dict[str, Any]:
    parent_result = _read(RESULT)
    parent_audit = _read(POSTAUDIT)
    aggregate = summarize()
    synthetic = _synthetic_reproduction()
    source_audit = _source_audit()
    parent_valid = (
        parent_result.get("status") == "exact220_single_rollout_complete"
        and parent_result.get("selected") == SELECTED
        and parent_result.get("claims", {}).get("public_exact220_single_rollout") is True
        and parent_result.get("authorization", {}).get(
            "selective_retry_or_revaluation"
        )
        is False
        and _sealed(parent_result, "result_payload_sha256")
        and parent_audit.get("audit_valid") is True
        and parent_audit.get("findings") == []
        and _sealed(parent_audit, "audit_payload_sha256")
    )
    checks = {
        "parent_result_and_postresult_audit_valid": parent_valid,
        "terminal_vector_exact220": aggregate["selected"] == SELECTED,
        "failure_partition_exact72_148": aggregate["completion_kind_counts"]
        == {
            "normalized_primary": 4,
            "primary": 144,
            "worker_failure_fallback": 72,
        },
        "all_fallbacks_last_safe_after_retrieval_before_projection": aggregate[
            "last_safe_progress_stage_counts"
        ]
        == {"retrieval_terminal": 72, "terminal": 148},
        "all_fallbacks_coarse_validation_error": aggregate[
            "fallback_failure_type_counts"
        ]
        == {"ValidationError": 72},
        "all_fallbacks_plan_only_model_and_four_queries": (
            aggregate["fallback_admitted_model_call_distribution"] == {"1": 72}
            and aggregate["fallback_admitted_search_query_distribution"]
            == {"4": 72}
        ),
        "all_fallback_projection_receipts_are_empty_terminal_receipts": aggregate[
            "fallback_projection_input_page_distribution"
        ]
        == {"0": 72},
        "fallbacks_executed_real_fetch_effects": aggregate[
            "fallback_transport_totals"
        ]["hard_fetch_helper_calls"]
        > 0,
        "fallback_provider_and_fetch_deadline_not_systemic": (
            aggregate["fallback_transport_totals"]["fetch_helper_failures"] == 0
            and aggregate["fallback_transport_totals"][
                "hard_fetch_deadline_failures"
            ]
            < 5
        ),
        "production_shaped_exact_total_cap_reproduced": (
            synthetic["total_render_overflow_reproduced"]
            and synthetic["first_error_matches_exact_total_cap"]
            and synthetic["runtime_binding_exact_total_cap_reproduced"]
        ),
        "synthetic_controls_valid": (
            synthetic["short_page_control_succeeds"]
            and synthetic["duplicate_url_control_deduplicates"]
        ),
        "source_privileged_access_zero": not source_audit[
            "runtime_privileged_access_hits"
        ],
        "source_evaluator_capability_zero": not source_audit[
            "evaluator_capability_hits"
        ],
        "source_secret_literal_zero": not source_audit[
            "credential_literal_files"
        ],
    }
    manifest = {
        str(path): _sha(path) for path in (*SOURCE_FILES, RESULT, POSTAUDIT)
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "parent": {
            "result": {"path": str(RESULT), "sha256": _sha(RESULT)},
            "postresult_audit": {
                "path": str(POSTAUDIT),
                "sha256": _sha(POSTAUDIT),
            },
        },
        "aggregate": aggregate,
        "synthetic_reproduction": synthetic,
        "mechanical_conclusion": {
            "failure_window": "after_retrieval_terminal_before_page_projection_terminal",
            "exact_reproduced_sufficient_cause": (
                "rendered_headers_plus_bounded_page_content_exceed_the_60000_"
                "total_projection_cap"
            ),
            "legacy_per_page_overflow_is_totalized": True,
            "remaining_unhandled_overflow": TOTAL_OVERFLOW,
            "empty_projection_receipt_is_postfailure_terminal_backfill_not_zero_retrieval": True,
            "endpoint_transport_model_slot_or_evaluator_failure": False,
            "all_72_failures_uniquely_attributed_from_frozen_artifacts": False,
            "reason_unique_attribution_is_unavailable": (
                "frozen_failure_artifacts_retain_only_coarse_exception_class_and_"
                "last_safe_stage"
            ),
            "next_safe_step": (
                "append_only_projection_totality_repair_plus_benchmark_external_"
                "production_shaped_regression"
            ),
        },
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "diagnosis_valid": all(checks.values()),
        "source_audit": source_audit,
        "source_manifest": manifest,
        "source_manifest_sha256": packer.long_parent.payload_sha256(manifest),
        "source_policy": {
            "aggregate_only_no_task_id_question_query_url_page_prediction_or_answer_emitted": True,
            "runtime_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "network_model_search_fetch_or_evaluator_called_by_diagnosis": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "same_population_retry_resume_skip_selective_rerun_or_revaluation": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
        },
        "authorization": {
            "append_only_projection_totality_repair_build": all(checks.values()),
            "benchmark_external_regression": all(checks.values()),
            "public_dev64_or_exact220": False,
            "evaluator_or_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["diagnosis_payload_sha256"] = packer.long_parent.payload_sha256(value)
    return value


def validate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    if (
        copied.get("role") != ROLE
        or copied.get("diagnosis_valid") is not True
        or copied.get("findings") != []
        or seal != packer.long_parent.payload_sha256(unsigned)
        or copied.get("source_manifest_sha256")
        != packer.long_parent.payload_sha256(copied.get("source_manifest"))
        or copied.get("mechanical_conclusion", {}).get(
            "all_72_failures_uniquely_attributed_from_frozen_artifacts"
        )
        is not False
        or copied.get("source_policy", {}).get(
            "entropy_or_information_gain_assigns_signed_credit"
        )
        is not False
    ):
        raise RuntimeError("V2.49.19 diagnosis drifted")
    return copied


def publish(value: Mapping[str, Any]) -> None:
    path = ROOT / OUTPUT
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = validate(build())
    publish(value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "diagnosis_valid": value["diagnosis_valid"],
                "findings": value["findings"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
