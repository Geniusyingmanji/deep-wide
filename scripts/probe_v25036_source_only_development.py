#!/usr/bin/env python3
"""Minimal development probe for source-only hosted-search feasibility.

Two already-consumed neutral query pairs from V2.42.81 are used only to test
the provider/transport direction before designing a fresh formal gate.  The
result stores aggregate counters and per-pair numeric rows, never query text,
URLs, pages, provider payloads, or credentials.  These query pairs are
permanently excluded from any future confirmation population.
"""

from __future__ import annotations

import json
import math
import os
import re
import socket
import subprocess
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
from deepwide_agent.native_search import _web_search_actions  # noqa: E402
from deepwide_agent.v24985_robust_late_page_fetch import (  # noqa: E402
    RobustLatePageBoundSearchClient,
)
from deepwide_agent.v25036_source_only_hosted_search import (  # noqa: E402
    SourceOnlyRobustLatePageBoundSearchClient,
)
from scripts import preregister_v24281_single_shot_pair as source  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402


OUTPUT = ROOT / "results/v25036_source_only_development_probe_v1_20260810.json"
LEASE = ROOT / "outputs/deepwide_benchmark_api.lease.lock"
PARENT_PROTOCOL = ROOT / "results/v24281_single_shot_pair_preregistration_v1_20260803.json"
PARENT_RESULT = ROOT / "results/v24281_single_shot_pair_result_v1_20260803.json"
EXPECTED_PARENT_PROTOCOL_SHA256 = (
    "1ca846151ab5a2ba5b771344497dab91c7488c78a42557914e5614aa78a6d356"
)
EXPECTED_PARENT_RESULT_SHA256 = (
    "835b3dfa0025e70486763576016d5cfa8fbf7a97980b9f833dc542d38add8db0"
)
EXPECTED_QUERY_SET_SHA256 = (
    "bc8a702ca8bf35d0f573c63ebf8c63b73b89e6ac9f895f06870aa50ae96cfa07"
)
ARMS = ("production_summary", "source_only")
PAIR_INDICES = (0, 1)
ENDPOINT = "http://127.0.0.1:9878/responses"
MODEL = "gpt-5.6-sol"
EXPECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
    (2808901, 746680268, "scripts/watch_v24215_joint_package_recovery.py"),
    (2889939, 746969965, "scripts/watch_v24216_package_gate.py"),
)
RUNTIME_FILES = (
    "scripts/probe_v25036_source_only_development.py",
    "src/deepwide_agent/v25036_source_only_hosted_search.py",
)
CONFLICT = re.compile(
    r"scripts/(?:run|probe|evaluate|finalize|recover)_v\d+[^ ]*\.py"
    r"|scripts/run_official_eval_local\.py"
)
COUNTERS = (
    "calls",
    "failures",
    "tool_calls",
    "fetch_calls",
    "fetch_failures",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "hosted_search_attempts",
    "hard_total_wall_timeouts",
    "observed_action_query_count",
    "observed_exact_action_query_count",
    "fully_observed_request_query_vectors",
)

SOURCE_POLICY = {
    "query_url_page_provider_payload_or_credential_persisted": False,
    "benchmark_manifest_question_mapping_gold_category_evaluator_score_or_reward_read": False,
    "standalone_generation_model_fetch_or_evaluator_called": False,
    "hosted_search_called": True,
    "entropy_or_information_gain_assigns_signed_credit": False,
}


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _ordinary(path: Path) -> Path:
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
        or path.stat().st_size > 5_000_000
    ):
        raise RuntimeError("V2.50.36 expected a small ordinary repository file")
    return path


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.36 expected a JSON object")
    return value


def _clean_pushed() -> tuple[str, dict[str, str]]:
    status = _git("status", "--porcelain", "--untracked-files=all")
    head = _git("rev-parse", "HEAD")
    target = _git("rev-parse", "target/main")
    if status or head != target or not re.fullmatch(r"[0-9a-f]{40}", head):
        raise RuntimeError("V2.50.36 requires clean pushed HEAD")
    manifest: dict[str, str] = {}
    for relative in RUNTIME_FILES:
        if _git("ls-files", "--error-unmatch", relative) != relative:
            raise RuntimeError("V2.50.36 runtime file is not tracked")
        manifest[relative] = sha256(_ordinary(ROOT / relative))
    return head, manifest


def _parent_binding() -> dict[str, Any]:
    if (
        sha256(_ordinary(PARENT_PROTOCOL)) != EXPECTED_PARENT_PROTOCOL_SHA256
        or sha256(_ordinary(PARENT_RESULT)) != EXPECTED_PARENT_RESULT_SHA256
        or payload_sha256(source.NEUTRAL_QUERY_PAIRS) != EXPECTED_QUERY_SET_SHA256
    ):
        raise RuntimeError("V2.50.36 neutral parent bytes drifted")
    protocol = _read_object(PARENT_PROTOCOL)
    result = _read_object(PARENT_RESULT)
    protocol_unsigned = dict(protocol)
    protocol_seal = protocol_unsigned.pop("protocol_payload_sha256", None)
    result_unsigned = dict(result)
    result_seal = result_unsigned.pop("result_payload_sha256", None)
    arms = result.get("arms")
    consumed = [
        row
        for row in arms if isinstance(row, Mapping) and row.get("pair") in {1, 2}
    ] if isinstance(arms, list) else []
    expected = sorted(
        (pair, arm) for pair in (1, 2) for arm in ("recursive", "single_shot")
    )
    if (
        protocol.get("role") != "v24281_neutral_single_shot_pair_preregistration"
        or protocol.get("pair_contract", {}).get("query_set_sha256")
        != EXPECTED_QUERY_SET_SHA256
        or protocol_seal != payload_sha256(protocol_unsigned)
        or result.get("role") != "v24281_neutral_single_shot_pair_result"
        or result.get("protocol_sha256") != EXPECTED_PARENT_PROTOCOL_SHA256
        or result_seal != payload_sha256(result_unsigned)
        or sorted((row.get("pair"), row.get("arm")) for row in consumed) != expected
        or any(row.get("terminal") is not True for row in consumed)
        or any(row.get("failure_type") is not None for row in consumed)
        or result.get("source_policy", {}).get(
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_read"
        )
        is not False
    ):
        raise RuntimeError("V2.50.36 neutral parent contract drifted")
    return {
        "protocol_path": str(PARENT_PROTOCOL.relative_to(ROOT)),
        "protocol_sha256": EXPECTED_PARENT_PROTOCOL_SHA256,
        "result_path": str(PARENT_RESULT.relative_to(ROOT)),
        "result_sha256": EXPECTED_PARENT_RESULT_SHA256,
        "query_set_sha256": EXPECTED_QUERY_SET_SHA256,
        "consumed_pair_count": len(PAIR_INDICES),
        "consumed_terminal_arm_rows": len(consumed),
        "consumed_pairs_permanently_excluded_from_confirmation": True,
    }


def _watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pid, expected_ticks, marker in EXPECTED_WATCHERS:
        stat = proc_root / str(pid) / "stat"
        cmdline = proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.50.36 protected watcher is absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(
            "utf-8", errors="replace"
        )
        if (
            len(suffix) <= 19
            or int(suffix[19]) != expected_ticks
            or marker not in command
        ):
            raise RuntimeError("V2.50.36 protected watcher identity drifted")
        rows.append({"pid": pid, "start_ticks": expected_ticks, "marker": marker})
    return rows


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
    conflicts: list[int] = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if (
            len(parts) == 3
            and parts[0].isdigit()
            and int(parts[0]) != os.getpid()
            and "python" in parts[1].casefold()
            and CONFLICT.search(parts[2])
        ):
            conflicts.append(int(parts[0]))
    return sorted(set(conflicts))


def _effect_preflight(
    *, expected_head: str, expected_manifest: Mapping[str, str]
) -> dict[str, Any]:
    head, manifest = _clean_pushed()
    if head != expected_head or manifest != dict(expected_manifest):
        raise RuntimeError("V2.50.36 clean-pushed runtime drifted")
    conflicts = _active_conflicts()
    if conflicts:
        raise RuntimeError("V2.50.36 conflicting experiment is active")
    watchers = _watcher_snapshot()
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
        "shared_api_lease_owner": "v25036_source_only_development_probe_v1",
    }


def _normalized_query(value: object) -> str:
    return " ".join(str(value).split()).strip()


class _ActionQueryObservationMixin:
    """Count exact action-query coverage without retaining query values."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.observed_action_query_count = 0
        self.observed_exact_action_query_count = 0
        self.fully_observed_request_query_vectors = 0

    def _request(self, queries: list[str]) -> dict[str, Any]:
        payload = super()._request(queries)
        observed: set[str] = set()
        for action in _web_search_actions(payload):
            query = _normalized_query(action.get("query"))
            if query:
                observed.add(query)
            observed.update(
                normalized
                for value in action.get("queries") or []
                if (normalized := _normalized_query(value))
            )
        expected = {_normalized_query(value) for value in queries}
        exact = expected & observed
        self._increment("observed_action_query_count", len(observed))
        self._increment("observed_exact_action_query_count", len(exact))
        self._increment(
            "fully_observed_request_query_vectors", int(exact == expected)
        )
        return payload


class _ObservedProductionSearchClient(
    _ActionQueryObservationMixin, RobustLatePageBoundSearchClient
):
    pass


class _ObservedSourceOnlySearchClient(
    _ActionQueryObservationMixin, SourceOnlyRobustLatePageBoundSearchClient
):
    pass


def _client(arm: str, *, deadline: float) -> Any:
    cls = (
        _ObservedProductionSearchClient
        if arm == "production_summary"
        else _ObservedSourceOnlySearchClient
    )
    if arm not in ARMS:
        raise ValueError("V2.50.36 development arm drifted")
    return cls(
        ENDPOINT,
        MODEL,
        visible_question="Neutral public-documentation transport development probe.",
        reasoning_effort="low",
        service_tier="priority",
        timeout=65,
        max_retries=2,
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


def _run(pair: int, arm: str) -> dict[str, Any]:
    if pair not in PAIR_INDICES or arm not in ARMS:
        raise ValueError("V2.50.36 development schedule drifted")
    queries = source.NEUTRAL_QUERY_PAIRS[pair]
    started = time.monotonic()
    inner = _client(arm, deadline=started + 120.0)
    union = TaskUnionDiscoverySearchClient(inner)
    failure_type: str | None = None
    try:
        union.search_many(
            queries,
            max_results=3,
            search_depth="advanced",
            include_raw_content=False,
        )
    except Exception as exc:
        failure_type = type(exc).__name__
    receipt = union.receipt()
    counters = {
        name: int(getattr(inner, name, 0) or 0) for name in COUNTERS
    }
    value = {
        "pair": pair + 1,
        "arm": arm,
        "terminal": True,
        "failure_type": failure_type,
        "wall_seconds": round(time.monotonic() - started, 6),
        "provider_counters": counters,
        "logical_query_count": int(receipt["logical_query_count"]),
        "raw_query_local_result_count": int(
            receipt["raw_query_local_result_count"]
        ),
        "raw_action_source_count": int(receipt["raw_action_source_count"]),
        "raw_query_local_mapping_failure_count": int(
            receipt["raw_query_local_mapping_failure_count"]
        ),
        "raw_unrecoverable_failure_count": int(
            receipt["raw_unrecoverable_failure_count"]
        ),
        "union_source_count": int(receipt["union_source_count"]),
        "recursive_split_requests": int(inner.recursive_split_requests),
        "query_url_page_payload_or_credential_persisted": False,
        "benchmark_manifest_question_mapping_gold_category_evaluator_score_or_reward_read": False,
    }
    validate_row(value)
    return value


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
        "recursive_split_requests",
    )
    if (
        set(copied)
        != {
            "pair",
            "arm",
            "terminal",
            "failure_type",
            "wall_seconds",
            "provider_counters",
            *numeric,
            "query_url_page_payload_or_credential_persisted",
            "benchmark_manifest_question_mapping_gold_category_evaluator_score_or_reward_read",
        }
        or copied.get("pair") not in {1, 2}
        or copied.get("arm") not in ARMS
        or copied.get("terminal") is not True
        or copied.get("failure_type") is not None
        and not isinstance(copied.get("failure_type"), str)
        or isinstance(copied.get("wall_seconds"), bool)
        or not isinstance(copied.get("wall_seconds"), (int, float))
        or not math.isfinite(float(copied["wall_seconds"]))
        or copied["wall_seconds"] < 0
        or not isinstance(counters, Mapping)
        or set(counters) != set(COUNTERS)
        or any(
            isinstance(counters.get(name), bool)
            or not isinstance(counters.get(name), int)
            or counters[name] < 0
            for name in COUNTERS
        )
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in numeric
        )
        or copied.get("query_url_page_payload_or_credential_persisted") is not False
        or copied.get(
            "benchmark_manifest_question_mapping_gold_category_evaluator_score_or_reward_read"
        )
        is not False
    ):
        raise ValueError("V2.50.36 development row drifted")
    return copied


def _aggregate(rows: Sequence[Mapping[str, Any]], arm: str) -> dict[str, Any]:
    selected = [validate_row(row) for row in rows if row["arm"] == arm]
    if len(selected) != len(PAIR_INDICES):
        raise ValueError("V2.50.36 development arm denominator drifted")
    return {
        "selected": len(selected),
        "terminal": sum(row["terminal"] is True for row in selected),
        "arm_exceptions": sum(row["failure_type"] is not None for row in selected),
        "wall_seconds": round(sum(float(row["wall_seconds"]) for row in selected), 6),
        **{
            name: sum(int(row["provider_counters"][name]) for row in selected)
            for name in COUNTERS
        },
        "logical_query_count": sum(row["logical_query_count"] for row in selected),
        "query_local_results": sum(
            row["raw_query_local_result_count"] for row in selected
        ),
        "action_sources": sum(row["raw_action_source_count"] for row in selected),
        "mapping_failures": sum(
            row["raw_query_local_mapping_failure_count"] for row in selected
        ),
        "unrecoverable_failures": sum(
            row["raw_unrecoverable_failure_count"] for row in selected
        ),
        "union_sources": sum(row["union_source_count"] for row in selected),
        "recursive_split_requests": sum(
            row["recursive_split_requests"] for row in selected
        ),
    }


def _ratio(candidate: int | float, control: int | float) -> float | None:
    return round(float(candidate) / float(control), 12) if control else None


def _at_most(value: float | None, threshold: float) -> bool:
    return value is not None and value <= threshold


def _at_least(value: float | None, threshold: float) -> bool:
    return value is not None and value >= threshold


def build_result(
    rows: Sequence[Mapping[str, Any]],
    *,
    wall: float,
    parent_binding: Mapping[str, Any],
    execution: Mapping[str, Any],
) -> dict[str, Any]:
    checked = [validate_row(row) for row in rows]
    expected = sorted(
        (pair + 1, arm) for pair in PAIR_INDICES for arm in ARMS
    )
    if sorted((row["pair"], row["arm"]) for row in checked) != expected:
        raise ValueError("V2.50.36 development coverage drifted")
    control = _aggregate(checked, "production_summary")
    candidate = _aggregate(checked, "source_only")
    ratios = {
        name: _ratio(candidate[name], control[name])
        for name in (
            "calls",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "wall_seconds",
            "action_sources",
            "union_sources",
        )
    }
    checks = {
        "all_four_rows_terminal": len(checked) == 4
        and all(row["terminal"] for row in checked),
        "no_arm_exception": all(row["failure_type"] is None for row in checked),
        "exact_logical_queries": control["logical_query_count"]
        == candidate["logical_query_count"]
        == 4,
        "one_provider_call_per_pair_arm": control["calls"]
        == candidate["calls"]
        == 2,
        "one_provider_attempt_per_pair_arm": control["hosted_search_attempts"]
        == candidate["hosted_search_attempts"]
        == 2,
        "one_or_more_search_actions_per_call": control["tool_calls"] >= 2
        and candidate["tool_calls"] >= 2,
        "all_exact_action_queries_observed": control[
            "observed_exact_action_query_count"
        ]
        == candidate["observed_exact_action_query_count"]
        == 4
        and control["fully_observed_request_query_vectors"]
        == candidate["fully_observed_request_query_vectors"]
        == 2,
        "no_unrecoverable_failure": control["unrecoverable_failures"]
        == candidate["unrecoverable_failures"]
        == 0,
        "no_recursive_split": control["recursive_split_requests"]
        == candidate["recursive_split_requests"]
        == 0,
        "candidate_input_token_direction": _at_most(
            ratios["input_tokens"], 0.90
        ),
        "candidate_total_token_direction": _at_most(
            ratios["total_tokens"], 0.90
        ),
        "candidate_action_source_yield": _at_least(
            ratios["action_sources"], 0.75
        ),
        "candidate_union_source_yield": _at_least(
            ratios["union_sources"], 0.75
        ),
        "candidate_absolute_union_sources": candidate["union_sources"] >= 6,
    }
    passed = all(checks.values())
    parent = dict(parent_binding)
    runtime = dict(execution)
    value = {
        "artifact_version": 1,
        "role": "v25036_source_only_hosted_search_development_probe",
        "created_at_unix": int(time.time()),
        "scope": "development_feasibility_only_old_neutral_queries",
        "parent_query_evidence": parent,
        "execution": runtime,
        "schedule": [
            {"pair": pair + 1, "arms": list(ARMS if pair % 2 == 0 else ARMS[::-1])}
            for pair in PAIR_INDICES
        ],
        "rows": checked,
        "aggregate": {
            "production_summary": control,
            "source_only": candidate,
            "source_only_over_production_summary": ratios,
            "batch_wall_seconds": round(float(wall), 6),
        },
        "checks": checks,
        "passed": passed,
        "findings": sorted(name for name, ok in checks.items() if not ok),
        "source_policy": dict(SOURCE_POLICY),
        "authorization": {
            "fresh_source_only_confirmation_gate_design": passed,
            "confirmation_or_benchmark_launch": False,
            "dev64_or_exact220": False,
            "evaluator_or_leaderboard_sota": False,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
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
    checks = copied.get("checks")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25036_source_only_hosted_search_development_probe"
        or copied.get("scope") != "development_feasibility_only_old_neutral_queries"
        or not isinstance(rows, list)
        or len(rows) != 4
        or any(validate_row(row) != row for row in rows)
        or not isinstance(parent, Mapping)
        or parent.get("protocol_sha256") != EXPECTED_PARENT_PROTOCOL_SHA256
        or parent.get("protocol_path")
        != str(PARENT_PROTOCOL.relative_to(ROOT))
        or parent.get("result_path") != str(PARENT_RESULT.relative_to(ROOT))
        or parent.get("result_sha256") != EXPECTED_PARENT_RESULT_SHA256
        or parent.get("query_set_sha256") != EXPECTED_QUERY_SET_SHA256
        or parent.get("consumed_pair_count") != len(PAIR_INDICES)
        or parent.get("consumed_terminal_arm_rows") != 4
        or parent.get("consumed_pairs_permanently_excluded_from_confirmation")
        is not True
        or not isinstance(execution, Mapping)
        or not re.fullmatch(r"[0-9a-f]{40}", str(execution.get("git_head", "")))
        or execution.get("target_main") != execution.get("git_head")
        or not isinstance(manifest, Mapping)
        or set(manifest) != set(RUNTIME_FILES)
        or any(not re.fullmatch(r"[0-9a-f]{64}", str(value)) for value in manifest.values())
        or before != after
        or before
        != [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in EXPECTED_WATCHERS
        ]
        or execution.get("active_conflict_pids") != []
        or execution.get("loopback_gpt56_port_ready") is not True
        or execution.get("shared_api_lease_acquired") is not True
        or execution.get("shared_api_lease_owner")
        != "v25036_source_only_development_probe_v1"
        or copied.get("source_policy") != SOURCE_POLICY
        or not isinstance(checks, Mapping)
        or set(checks)
        != {
            "all_four_rows_terminal",
            "no_arm_exception",
            "exact_logical_queries",
            "one_provider_call_per_pair_arm",
            "one_provider_attempt_per_pair_arm",
            "one_or_more_search_actions_per_call",
            "all_exact_action_queries_observed",
            "no_unrecoverable_failure",
            "no_recursive_split",
            "candidate_input_token_direction",
            "candidate_total_token_direction",
            "candidate_action_source_yield",
            "candidate_union_source_yield",
            "candidate_absolute_union_sources",
        }
        or any(not isinstance(item, bool) for item in checks.values())
        or copied.get("passed") is not all(checks.values() if isinstance(checks, Mapping) else [])
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.36 development result drifted")
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
    schedule = [
        (pair, arm) for pair in PAIR_INDICES for arm in (ARMS if pair % 2 == 0 else ARMS[::-1])
    ]
    started = time.monotonic()
    with acquire_deepwide_api_lease(
        ROOT,
        owner="v25036_source_only_development_probe_v1",
        purpose="source_only_hosted_search_directional_feasibility",
        path=LEASE,
    ):
        execution = _effect_preflight(
            expected_head=head, expected_manifest=manifest
        )
        with ThreadPoolExecutor(max_workers=4) as pool:
            rows = list(pool.map(lambda item: _run(*item), schedule))
    execution["protected_watchers_after"] = _watcher_snapshot()
    if execution["protected_watchers_after"] != execution["protected_watchers_before"]:
        raise RuntimeError("V2.50.36 protected watcher changed during probe")
    result = build_result(
        rows,
        wall=time.monotonic() - started,
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
