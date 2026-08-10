#!/usr/bin/env python3
"""Development-only source-only hosted-search width staircase.

The same four already-consumed V2.42.81 neutral public-documentation queries
are issued at widths 1, 2, and 4.  This measures whether provider input-token
cost contains a batch-amortizable component.  No page fetch, generation model,
benchmark surface, evaluator, raw query, URL, provider payload, or credential
is persisted.  The consumed queries are permanently excluded from any future
confirmation population.
"""

from __future__ import annotations

import json
import math
import os
import re
import socket
import sys
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24269_task_union_discovery import (  # noqa: E402
    TaskUnionDiscoverySearchClient,
)
from scripts import probe_v25036_source_only_development as base  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


OUTPUT = ROOT / "results/v25037_source_only_width_development_probe_v1_20260810.json"
LEASE = ROOT / "outputs/deepwide_benchmark_api.lease.lock"
PAIR_INDICES = (2, 3)
PAIR_NUMBERS = (3, 4)
WIDTHS = (1, 2, 4)
ARMS = tuple(f"width_{width}" for width in WIDTHS)
EXPECTED_CALLS = {"width_1": 4, "width_2": 2, "width_4": 1}
RUNTIME_FILES = (
    "scripts/probe_v25037_source_only_width_development.py",
    "scripts/probe_v25036_source_only_development.py",
    "src/deepwide_agent/v25036_source_only_hosted_search.py",
)
SOURCE_POLICY = {
    "query_url_page_provider_payload_or_credential_persisted": False,
    "benchmark_manifest_question_mapping_gold_category_evaluator_score_or_reward_read": False,
    "standalone_generation_model_fetch_or_evaluator_called": False,
    "hosted_search_called": True,
    "entropy_or_information_gain_assigns_signed_credit": False,
}


def _query_vector() -> tuple[str, ...]:
    values = tuple(
        query
        for index in PAIR_INDICES
        for query in base.source.NEUTRAL_QUERY_PAIRS[index]
    )
    if len(values) != 4 or len({" ".join(value.split()).casefold() for value in values}) != 4:
        raise RuntimeError("V2.50.37 neutral query vector drifted")
    return values


def chunks_for_width(width: int) -> list[tuple[str, ...]]:
    if width not in WIDTHS:
        raise ValueError("V2.50.37 unsupported width")
    values = _query_vector()
    chunks = [tuple(values[index : index + width]) for index in range(0, 4, width)]
    if len(chunks) != 4 // width or tuple(item for chunk in chunks for item in chunk) != values:
        raise RuntimeError("V2.50.37 chunk schedule drifted")
    return chunks


def _parent_binding() -> dict[str, Any]:
    if (
        base.sha256(base._ordinary(base.PARENT_PROTOCOL))
        != base.EXPECTED_PARENT_PROTOCOL_SHA256
        or base.sha256(base._ordinary(base.PARENT_RESULT))
        != base.EXPECTED_PARENT_RESULT_SHA256
        or base.payload_sha256(base.source.NEUTRAL_QUERY_PAIRS)
        != base.EXPECTED_QUERY_SET_SHA256
    ):
        raise RuntimeError("V2.50.37 neutral parent bytes drifted")
    protocol = base._read_object(base.PARENT_PROTOCOL)
    result = base._read_object(base.PARENT_RESULT)
    protocol_unsigned = dict(protocol)
    protocol_seal = protocol_unsigned.pop("protocol_payload_sha256", None)
    result_unsigned = dict(result)
    result_seal = result_unsigned.pop("result_payload_sha256", None)
    arms = result.get("arms")
    consumed = [
        row
        for row in arms
        if isinstance(row, Mapping) and row.get("pair") in set(PAIR_NUMBERS)
    ] if isinstance(arms, list) else []
    expected = sorted(
        (pair, arm)
        for pair in PAIR_NUMBERS
        for arm in ("recursive", "single_shot")
    )
    if (
        protocol.get("role") != "v24281_neutral_single_shot_pair_preregistration"
        or protocol.get("pair_contract", {}).get("query_set_sha256")
        != base.EXPECTED_QUERY_SET_SHA256
        or protocol_seal != base.payload_sha256(protocol_unsigned)
        or result.get("role") != "v24281_neutral_single_shot_pair_result"
        or result.get("protocol_sha256") != base.EXPECTED_PARENT_PROTOCOL_SHA256
        or result_seal != base.payload_sha256(result_unsigned)
        or sorted((row.get("pair"), row.get("arm")) for row in consumed) != expected
        or any(row.get("terminal") is not True for row in consumed)
        or any(row.get("failure_type") is not None for row in consumed)
        or result.get("source_policy", {}).get(
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_read"
        )
        is not False
    ):
        raise RuntimeError("V2.50.37 neutral parent contract drifted")
    return {
        "protocol_path": str(base.PARENT_PROTOCOL.relative_to(ROOT)),
        "protocol_sha256": base.EXPECTED_PARENT_PROTOCOL_SHA256,
        "result_path": str(base.PARENT_RESULT.relative_to(ROOT)),
        "result_sha256": base.EXPECTED_PARENT_RESULT_SHA256,
        "query_set_sha256": base.EXPECTED_QUERY_SET_SHA256,
        "consumed_pair_numbers": list(PAIR_NUMBERS),
        "consumed_terminal_arm_rows": len(consumed),
        "consumed_queries_permanently_excluded_from_confirmation": True,
    }


def _clean_pushed() -> tuple[str, dict[str, str]]:
    status = base._git("status", "--porcelain", "--untracked-files=all")
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    if status or head != target or not re.fullmatch(r"[0-9a-f]{40}", head):
        raise RuntimeError("V2.50.37 requires clean pushed HEAD")
    manifest: dict[str, str] = {}
    for relative in RUNTIME_FILES:
        if base._git("ls-files", "--error-unmatch", relative) != relative:
            raise RuntimeError("V2.50.37 runtime file is not tracked")
        manifest[relative] = base.sha256(base._ordinary(ROOT / relative))
    return head, manifest


def _effect_preflight(
    *, expected_head: str, expected_manifest: Mapping[str, str]
) -> dict[str, Any]:
    head, manifest = _clean_pushed()
    if head != expected_head or manifest != dict(expected_manifest):
        raise RuntimeError("V2.50.37 clean-pushed runtime drifted")
    conflicts = base._active_conflicts()
    if conflicts:
        raise RuntimeError("V2.50.37 conflicting experiment is active")
    watchers = base._watcher_snapshot()
    with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
        pass
    return {
        "git_head": head,
        "target_main": head,
        "runtime_manifest": manifest,
        "protected_watchers_before": watchers,
        "active_conflict_pids": conflicts,
        "loopback_gpt56_port_ready": True,
        "shared_api_lease_acquired": True,
        "shared_api_lease_owner": "v25037_source_only_width_development_v1",
    }


def _client(*, deadline: float) -> Any:
    return base._ObservedSourceOnlySearchClient(
        base.ENDPOINT,
        base.MODEL,
        visible_question="Neutral public-documentation width development probe.",
        reasoning_effort="low",
        service_tier="priority",
        timeout=65,
        max_retries=1,
        absolute_deadline=deadline,
        cleanup_reserve_seconds=5.0,
        minimum_attempt_seconds=0.05,
        max_workers=1,
        batch_size=8,
        search_context_size="medium",
        max_output_tokens=7_000,
        fetch_pages=False,
        fetch_workers=8,
        fetch_timeout=20,
        max_page_chars=5_000,
        hard_fetch_deadline_seconds=25,
        stage_callback=lambda _event: None,
    )


def _run_arm(width: int) -> dict[str, Any]:
    arm = f"width_{width}"
    if arm not in ARMS:
        raise ValueError("V2.50.37 arm drifted")
    started = time.monotonic()
    inner = _client(deadline=started + 300.0)
    union = TaskUnionDiscoverySearchClient(inner)
    failure_type: str | None = None
    distinct_urls: set[str] = set()
    try:
        for chunk in chunks_for_width(width):
            batches = union.search_many(
                chunk,
                max_results=3,
                search_depth="advanced",
                include_raw_content=False,
            )
            for batch in batches:
                if not isinstance(batch, Mapping):
                    continue
                for result in batch.get("results") or []:
                    if isinstance(result, Mapping):
                        url = str(result.get("url") or "").strip()
                        if url:
                            distinct_urls.add(url)
    except Exception as exc:
        failure_type = type(exc).__name__
    receipt = union.receipt()
    counters = {
        name: int(getattr(inner, name, 0) or 0) for name in base.COUNTERS
    }
    value = {
        "arm": arm,
        "width": width,
        "chunk_count": len(chunks_for_width(width)),
        "terminal": True,
        "failure_type": failure_type,
        "wall_seconds": round(time.monotonic() - started, 6),
        "provider_counters": counters,
        "logical_query_count": int(receipt["logical_query_count"]),
        "raw_query_local_result_count": int(receipt["raw_query_local_result_count"]),
        "raw_action_source_count": int(receipt["raw_action_source_count"]),
        "raw_query_local_mapping_failure_count": int(
            receipt["raw_query_local_mapping_failure_count"]
        ),
        "raw_unrecoverable_failure_count": int(
            receipt["raw_unrecoverable_failure_count"]
        ),
        "union_source_count": int(receipt["union_source_count"]),
        "distinct_union_source_count": len(distinct_urls),
        "recursive_split_requests": int(inner.recursive_split_requests),
        "query_url_page_payload_or_credential_persisted": False,
        "benchmark_manifest_question_mapping_gold_category_evaluator_score_or_reward_read": False,
    }
    return validate_row(value)


def validate_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    counters = copied.get("provider_counters")
    numeric = (
        "logical_query_count",
        "raw_query_local_result_count",
        "raw_action_source_count",
        "raw_query_local_mapping_failure_count",
        "raw_unrecoverable_failure_count",
        "union_source_count",
        "distinct_union_source_count",
        "recursive_split_requests",
    )
    width = copied.get("width")
    if (
        set(copied)
        != {
            "arm", "width", "chunk_count", "terminal", "failure_type",
            "wall_seconds", "provider_counters", *numeric,
            "query_url_page_payload_or_credential_persisted",
            "benchmark_manifest_question_mapping_gold_category_evaluator_score_or_reward_read",
        }
        or copied.get("arm") not in ARMS
        or width not in WIDTHS
        or copied.get("arm") != f"width_{width}"
        or copied.get("chunk_count") != 4 // int(width)
        or copied.get("terminal") is not True
        or copied.get("failure_type") is not None
        and not isinstance(copied.get("failure_type"), str)
        or isinstance(copied.get("wall_seconds"), bool)
        or not isinstance(copied.get("wall_seconds"), (int, float))
        or not math.isfinite(float(copied["wall_seconds"]))
        or copied["wall_seconds"] < 0
        or not isinstance(counters, Mapping)
        or set(counters) != set(base.COUNTERS)
        or any(
            isinstance(counters.get(name), bool)
            or not isinstance(counters.get(name), int)
            or counters[name] < 0
            for name in base.COUNTERS
        )
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in numeric
        )
        or copied["distinct_union_source_count"] > copied["union_source_count"]
        or copied.get("query_url_page_payload_or_credential_persisted") is not False
        or copied.get(
            "benchmark_manifest_question_mapping_gold_category_evaluator_score_or_reward_read"
        )
        is not False
    ):
        raise ValueError("V2.50.37 development row drifted")
    return copied


def _ratio(candidate: int | float, control: int | float) -> float | None:
    return round(float(candidate) / float(control), 12) if control else None


def _at_most(value: float | None, threshold: float) -> bool:
    return value is not None and value <= threshold


def _at_least(value: float | None, threshold: float) -> bool:
    return value is not None and value >= threshold


def _summarize(
    rows: Sequence[Mapping[str, Any]], *, batch_wall_seconds: float
) -> tuple[dict[str, Any], dict[str, bool]]:
    if (
        isinstance(batch_wall_seconds, bool)
        or not isinstance(batch_wall_seconds, (int, float))
        or not math.isfinite(float(batch_wall_seconds))
        or float(batch_wall_seconds) < 0
    ):
        raise ValueError("V2.50.37 invalid batch wall")
    checked = [validate_row(row) for row in rows]
    if sorted(row["arm"] for row in checked) != sorted(ARMS):
        raise ValueError("V2.50.37 arm coverage drifted")
    arms = {row["arm"]: row for row in checked}
    fields = (
        "calls", "input_tokens", "output_tokens", "total_tokens",
        "wall_seconds", "raw_action_source_count", "union_source_count",
        "distinct_union_source_count",
    )
    ratios = {
        "width_2_over_width_1": {
            name: _ratio(arms["width_2"].get(name, arms["width_2"]["provider_counters"].get(name)),
                         arms["width_1"].get(name, arms["width_1"]["provider_counters"].get(name)))
            for name in fields
        },
        "width_4_over_width_2": {
            name: _ratio(arms["width_4"].get(name, arms["width_4"]["provider_counters"].get(name)),
                         arms["width_2"].get(name, arms["width_2"]["provider_counters"].get(name)))
            for name in fields
        },
        "width_4_over_width_1": {
            name: _ratio(arms["width_4"].get(name, arms["width_4"]["provider_counters"].get(name)),
                         arms["width_1"].get(name, arms["width_1"]["provider_counters"].get(name)))
            for name in fields
        },
    }
    aggregate = {
        "arms": arms,
        "ratios": ratios,
        "batch_wall_seconds": round(float(batch_wall_seconds), 6),
    }
    checks = {
        "all_three_arms_terminal": len(checked) == 3
        and all(row["terminal"] for row in checked),
        "no_arm_exception": all(row["failure_type"] is None for row in checked),
        "exact_four_logical_queries_per_arm": all(
            row["logical_query_count"] == 4 for row in checked
        ),
        "exact_provider_calls": all(
            row["provider_counters"]["calls"] == EXPECTED_CALLS[row["arm"]]
            for row in checked
        ),
        "no_provider_retry": all(
            row["provider_counters"]["hosted_search_attempts"]
            == EXPECTED_CALLS[row["arm"]]
            for row in checked
        ),
        "one_or_more_search_actions_per_call": all(
            row["provider_counters"]["tool_calls"] >= EXPECTED_CALLS[row["arm"]]
            for row in checked
        ),
        "all_exact_action_queries_observed": all(
            row["provider_counters"]["observed_exact_action_query_count"] == 4
            and row["provider_counters"]["fully_observed_request_query_vectors"]
            == EXPECTED_CALLS[row["arm"]]
            for row in checked
        ),
        "zero_fetch": all(
            row["provider_counters"]["fetch_calls"] == 0
            and row["provider_counters"]["fetch_failures"] == 0
            for row in checked
        ),
        "no_hard_total_wall_timeout": all(
            row["provider_counters"]["hard_total_wall_timeouts"] == 0
            for row in checked
        ),
        "no_unrecoverable_failure": all(
            row["raw_unrecoverable_failure_count"] == 0 for row in checked
        ),
        "no_recursive_split": all(
            row["recursive_split_requests"] == 0 for row in checked
        ),
        "input_tokens_monotonic_with_width": arms["width_4"]["provider_counters"]["input_tokens"]
        <= arms["width_2"]["provider_counters"]["input_tokens"]
        <= arms["width_1"]["provider_counters"]["input_tokens"],
        "width_4_input_token_amortization": _at_most(
            ratios["width_4_over_width_1"]["input_tokens"], 0.90
        ),
        "width_4_total_token_amortization": _at_most(
            ratios["width_4_over_width_1"]["total_tokens"], 0.90
        ),
        "width_4_union_source_yield": _at_least(
            ratios["width_4_over_width_1"]["union_source_count"], 0.85
        ),
        "width_4_distinct_source_yield": _at_least(
            ratios["width_4_over_width_1"]["distinct_union_source_count"], 0.85
        ),
        "width_4_absolute_distinct_sources": arms["width_4"][
            "distinct_union_source_count"
        ]
        >= 8,
    }
    return aggregate, checks


def build_result(
    rows: Sequence[Mapping[str, Any]],
    *,
    batch_wall_seconds: float,
    parent_binding: Mapping[str, Any],
    execution: Mapping[str, Any],
) -> dict[str, Any]:
    aggregate, checks = _summarize(rows, batch_wall_seconds=batch_wall_seconds)
    passed = all(checks.values())
    value = {
        "artifact_version": 1,
        "role": "v25037_source_only_width_development_probe",
        "created_at_unix": int(time.time()),
        "scope": "development_feasibility_only_old_neutral_queries",
        "parent_query_evidence": dict(parent_binding),
        "execution": dict(execution),
        "schedule": {
            "arms_concurrent": True,
            "widths": list(WIDTHS),
            "logical_queries_per_arm": 4,
            "max_retries": 1,
        },
        "rows": [validate_row(row) for row in rows],
        "aggregate": aggregate,
        "checks": checks,
        "passed": passed,
        "findings": sorted(name for name, ok in checks.items() if not ok),
        "source_policy": dict(SOURCE_POLICY),
        "authorization": {
            "fresh_width_matched_gate_design": passed,
            "confirmation_or_benchmark_launch": False,
            "dev64_or_exact220": False,
            "evaluator_or_leaderboard_sota": False,
        },
    }
    value["result_payload_sha256"] = base.payload_sha256(value)
    return validate_result(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    rows = copied.get("rows")
    parent = copied.get("parent_query_evidence")
    execution = copied.get("execution")
    manifest = execution.get("runtime_manifest") if isinstance(execution, Mapping) else None
    before = execution.get("protected_watchers_before") if isinstance(execution, Mapping) else None
    after = execution.get("protected_watchers_after") if isinstance(execution, Mapping) else None
    batch_wall = (copied.get("aggregate") or {}).get("batch_wall_seconds")
    recomputed: tuple[dict[str, Any], dict[str, bool]] | None = None
    if isinstance(rows, list) and isinstance(batch_wall, (int, float)):
        recomputed = _summarize(rows, batch_wall_seconds=float(batch_wall))
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != "v25037_source_only_width_development_probe"
        or copied.get("scope") != "development_feasibility_only_old_neutral_queries"
        or not isinstance(rows, list)
        or len(rows) != 3
        or not isinstance(parent, Mapping)
        or parent.get("protocol_sha256") != base.EXPECTED_PARENT_PROTOCOL_SHA256
        or parent.get("protocol_path")
        != str(base.PARENT_PROTOCOL.relative_to(ROOT))
        or parent.get("result_sha256") != base.EXPECTED_PARENT_RESULT_SHA256
        or parent.get("result_path") != str(base.PARENT_RESULT.relative_to(ROOT))
        or parent.get("query_set_sha256") != base.EXPECTED_QUERY_SET_SHA256
        or parent.get("consumed_pair_numbers") != list(PAIR_NUMBERS)
        or parent.get("consumed_terminal_arm_rows") != 4
        or parent.get("consumed_queries_permanently_excluded_from_confirmation")
        is not True
        or not isinstance(execution, Mapping)
        or not re.fullmatch(r"[0-9a-f]{40}", str(execution.get("git_head", "")))
        or execution.get("target_main") != execution.get("git_head")
        or not isinstance(manifest, Mapping)
        or set(manifest) != set(RUNTIME_FILES)
        or any(
            not re.fullmatch(r"[0-9a-f]{64}", str(item))
            for item in manifest.values()
        )
        or before != after
        or before
        != [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in base.EXPECTED_WATCHERS
        ]
        or execution.get("active_conflict_pids") != []
        or execution.get("loopback_gpt56_port_ready") is not True
        or execution.get("shared_api_lease_acquired") is not True
        or execution.get("shared_api_lease_owner")
        != "v25037_source_only_width_development_v1"
        or copied.get("source_policy") != SOURCE_POLICY
        or copied.get("schedule")
        != {
            "arms_concurrent": True,
            "widths": list(WIDTHS),
            "logical_queries_per_arm": 4,
            "max_retries": 1,
        }
        or copied.get("authorization")
        != {
            "fresh_width_matched_gate_design": bool(
                recomputed is not None and all(recomputed[1].values())
            ),
            "confirmation_or_benchmark_launch": False,
            "dev64_or_exact220": False,
            "evaluator_or_leaderboard_sota": False,
        }
        or recomputed is None
        or copied.get("aggregate") != recomputed[0]
        or copied.get("checks") != recomputed[1]
        or copied.get("passed") is not all(recomputed[1].values())
        or copied.get("findings")
        != sorted(name for name, ok in recomputed[1].items() if not ok)
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.37 development result drifted")
    return copied


def _publish(value: Mapping[str, Any]) -> None:
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise FileExistsError(OUTPUT)
    descriptor = os.open(
        OUTPUT, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise FileExistsError(OUTPUT)
    head, manifest = _clean_pushed()
    parent = _parent_binding()
    started = time.monotonic()
    with acquire_deepwide_api_lease(
        ROOT,
        owner="v25037_source_only_width_development_v1",
        purpose="source_only_hosted_search_width_cost_feasibility",
        path=LEASE,
    ):
        execution = _effect_preflight(
            expected_head=head, expected_manifest=manifest
        )
        with ThreadPoolExecutor(max_workers=3) as pool:
            rows = list(pool.map(_run_arm, WIDTHS))
    execution["protected_watchers_after"] = base._watcher_snapshot()
    if execution["protected_watchers_after"] != execution["protected_watchers_before"]:
        raise RuntimeError("V2.50.37 protected watcher changed during probe")
    result = build_result(
        rows,
        batch_wall_seconds=time.monotonic() - started,
        parent_binding=parent,
        execution=execution,
    )
    _publish(result)
    print(
        json.dumps(
            {
                "path": str(OUTPUT.relative_to(ROOT)),
                "passed": result["passed"],
                "aggregate": result["aggregate"],
                "findings": result["findings"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
