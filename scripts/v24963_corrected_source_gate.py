#!/usr/bin/env python3
"""Fresh corrected capability gate for cumulative source-fair discovery.

V2.49.62 passed every reliability, exposure, relative source-gain, and usable
page guard but failed a minimum *control* source-count floor.  That floor is
anti-monotone in the treatment need: a weaker stable prefix makes a diversity
treatment more useful.  This fresh successor removes no treatment guard.  It
replaces the control floor with an absolute candidate capability floor while
retaining the relative gain, task engagement, matched-cost, page-yield, and
transport gates.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import FunctionType
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24962_cumulative_source_fair_live_gate as parent  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260809"
PROTOCOL_ID = "v24963_corrected_cumulative_source_fair_capability_gate_v1"
PROTOCOL = Path(f"results/v24963_corrected_source_gate_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v24963_corrected_source_gate_result_v1_{DATE}.json")
AUDIT = Path(f"results/v24963_corrected_source_gate_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24963_corrected_source_gate_v1_{DATE}")
PARENT_RESULT = Path("results/v24962_cumulative_source_fair_live_result_v1_20260809.json")
LEASE_PATH = parent.LEASE_PATH

TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
PRODUCTS = (
    ("JupyterLab", "4.2"),
    ("scikit-learn", "1.5"),
    ("SciPy", "1.14"),
    ("Matplotlib", "3.9"),
    ("Polars", "1.5"),
    ("DuckDB", "1.1"),
    ("ClickHouse", "24.8"),
    ("CockroachDB", "24.2"),
    ("TimescaleDB", "2.16"),
    ("Apache Airflow", "2.10"),
    ("Dagster", "1.8"),
    ("Prefect", "3.0"),
    ("Ray", "2.35"),
    ("Dask", "2024.8"),
    ("MLflow", "2.16"),
    ("ONNX Runtime", "1.19"),
    ("XGBoost", "2.1"),
    ("LightGBM", "4.5"),
    ("Transformers", "4.44"),
    ("JAX", "0.4.31"),
)
QUERY_PATTERNS = parent.QUERY_PATTERNS
SOURCES = (
    Path("scripts/v24963_corrected_source_gate.py"),
    Path("tests/test_v24963_corrected_source_gate.py"),
    Path("scripts/v24962_cumulative_source_fair_live_gate.py"),
    Path("src/deepwide_agent/v24961_cumulative_source_fair.py"),
    Path("src/deepwide_agent/v24959_source_fair_discovery.py"),
    Path("src/deepwide_agent/v24957_action_fair_discovery.py"),
    Path("src/deepwide_agent/v24280_task_union_single_shot.py"),
    Path("src/deepwide_agent/native_search.py"),
    Path("src/deepwide_agent/v24316_deadline_search.py"),
    Path("src/deepwide_agent/v24287_hard_deadline_fetch.py"),
    Path("scripts/deepwide_api_lease.py"),
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(("gh" + "p_", "github" + "_pat_", "tvly" + "-dev-", "s" + "k-"))
    + r")[A-Za-z0-9_-]{16,}"
)


payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
publish_new = parent.publish_new
expected_watchers = parent.expected_watchers
_watchers = parent._watchers
_lease_inactive = parent._lease_inactive
_aggregate = parent._aggregate


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def _clean_pushed() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.49.63 requires a clean pushed HEAD")


def _manifest(*, tracked: bool) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCES:
        path = ROOT / relative
        tracked_ok = not tracked or subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)],
            cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=20, check=False,
        ).returncode == 0
        if (
            relative.is_absolute() or ".." in relative.parts or path.is_symlink()
            or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve())
            or not tracked_ok
        ):
            raise RuntimeError(f"V2.49.63 source identity drifted: {relative}")
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError(f"V2.49.63 credential literal in {relative}")
        output[str(relative)] = sha256(path)
    return output


def _read(relative: Path) -> dict[str, Any]:
    path = ROOT / relative
    if (
        relative.is_absolute() or ".." in relative.parts or path.is_symlink()
        or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.49.63 expected ordinary repository object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.63 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parent_result() -> dict[str, Any]:
    value = parent.validate_result(_read(PARENT_RESULT))
    if (
        value.get("passed") is not False
        or value.get("decision", {}).get("failed_checks")
        != ["control_source_coverage_present"]
        or value.get("aggregate", {}).get("candidate_registrable_sources") != 95
        or value.get("aggregate", {}).get("control_registrable_sources") != 35
    ):
        raise RuntimeError("V2.49.63 parent gate evidence drifted")
    return value


def query_vector() -> tuple[tuple[str, ...], ...]:
    if len(PRODUCTS) != TASK_COUNT:
        raise RuntimeError("V2.49.63 neutral product vector drifted")
    return tuple(
        tuple(pattern.format(product=product, version=version) for pattern in QUERY_PATTERNS)
        for product, version in PRODUCTS
    )


def source_policy() -> dict[str, bool]:
    return {
        **parent.source_policy(),
        "fresh_population_disjoint_from_v24958_v24960_v24962": True,
        "absolute_control_source_floor_used_for_promotion": False,
        "absolute_candidate_source_capability_required": True,
        "parent_result_reclassified_as_go": False,
    }


def gates() -> dict[str, Any]:
    value = dict(parent.gates())
    value.pop("minimum_control_registrable_sources")
    value["minimum_candidate_registrable_sources"] = 80
    return value


def isolated_probe() -> Any:
    """Clone the frozen parent probe with only the fresh query-vector binding."""

    function = parent._probe
    if function.__closure__ is not None:
        raise RuntimeError("V2.49.63 parent probe unexpectedly closes over state")
    namespace = dict(function.__globals__)
    namespace["query_vector"] = query_vector
    clone = FunctionType(
        function.__code__, namespace, "v24963_isolated_probe", function.__defaults__, None
    )
    clone.__kwdefaults__ = function.__kwdefaults__
    return clone


def build_protocol(
    *, now: int | None = None, require_clean: bool = True,
    require_pristine: bool = True, require_watchers: bool = True,
) -> dict[str, Any]:
    if require_clean:
        _clean_pushed()
    if require_pristine and any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (PROTOCOL, RESULT, AUDIT, OUTPUT_ROOT)
    ):
        raise RuntimeError("V2.49.63 future surface is not pristine")
    parent_result = _parent_result()
    manifest = _manifest(tracked=require_clean)
    watchers = _watchers() if require_watchers else expected_watchers()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24963_corrected_source_gate_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD") if require_clean else "build-only",
        "parent_observation": {
            "path": str(PARENT_RESULT),
            "sha256": sha256(ROOT / PARENT_RESULT),
            "passed": parent_result["passed"],
            "failed_checks": parent_result["decision"]["failed_checks"],
            "parent_remains_no_go": True,
        },
        "gate_correction": {
            "removed": "minimum_control_registrable_sources",
            "replacement": "minimum_candidate_registrable_sources",
            "replacement_value": 80,
            "relative_source_ratio_gate_retained": 1.25,
            "source_gain_task_and_total_gates_retained": True,
            "usable_page_and_char_gates_retained": True,
            "reliability_and_matched_cost_gates_retained": True,
            "correction_frozen_before_fresh_population": True,
        },
        "provider": {
            "endpoint": parent.ENDPOINT, "model": parent.MODEL, "keyless": True,
            "reasoning_effort": "low", "service_tier": "priority",
            "search_context_size": "medium", "max_retries": 1,
        },
        "schedule": {
            "task_count": TASK_COUNT,
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "logical_queries_per_task": 4,
            "queries_per_wave": 2,
            "wave_fetch_caps": [6, 4],
            "fetch_cap_per_arm": 10,
            "maximum_planned_shared_union_urls_per_task": 20,
            "task_deadline_seconds": 150.0,
            "query_vector_sha256": payload_sha256(query_vector()),
            "isolated_parent_probe_with_only_fresh_query_binding": True,
            "one_provider_attempt_per_wave": True,
            "shared_response_replay": True,
            "task_local_shared_fetch_union": True,
            "cumulative_two_wave_source_guard": True,
        },
        "arms": {
            parent.CONTROL: "query_local_prefix_then_stable_first_seen_action_sources",
            parent.CANDIDATE: "cumulative_first_representative_per_registrable_source_then_deferred_duplicates",
        },
        "gates": gates(),
        "protected_watchers": watchers,
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": source_policy(),
        "authorization": {
            "one_fresh_corrected_neutral_capability_gate": True,
            "benchmark_external_quality_gate_design": False,
            "benchmark_external_or_exact220_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(value, require_tracked=require_clean)


def validate_protocol(
    value: Mapping[str, Any], *, require_tracked: bool = True
) -> dict[str, Any]:
    copied = dict(value)
    manifest = _manifest(tracked=True) if require_tracked else copied.get("source_manifest")
    correction = copied.get("gate_correction") or {}
    if (
        copied.get("role") != "v24963_corrected_source_gate_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("parent_observation", {}).get("parent_remains_no_go") is not True
        or correction.get("removed") != "minimum_control_registrable_sources"
        or correction.get("replacement") != "minimum_candidate_registrable_sources"
        or correction.get("replacement_value") != 80
        or copied.get("schedule", {}).get("query_vector_sha256") != payload_sha256(query_vector())
        or copied.get("schedule", {}).get("isolated_parent_probe_with_only_fresh_query_binding") is not True
        or copied.get("gates") != gates()
        or copied.get("protected_watchers") != expected_watchers()
        or copied.get("source_manifest") != manifest
        or copied.get("source_manifest_sha256") != payload_sha256(manifest)
        or copied.get("source_policy") != source_policy()
        or copied.get("authorization", {}).get("benchmark_external_or_exact220_launch") is not False
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.49.63 protocol drifted")
    return copied


def _ratio(numerator: Any, denominator: Any) -> float:
    left = float(numerator)
    right = float(denominator)
    return left / right if right > 0 else float("inf")


def decision(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    gate = gates()
    checks = {
        "all_tasks_terminal": aggregate.get("terminal_task_count") == gate["terminal_task_count"],
        "all_tasks_completed": aggregate.get("completed_task_count") == gate["completed_task_count"],
        "all_logical_query_rows_committed": aggregate.get("logical_query_rows") == gate["logical_query_rows"],
        "exact_search_attempts": aggregate.get("search_provider_attempts") == gate["search_provider_attempts"],
        "exact_search_responses": aggregate.get("search_provider_response_calls") == gate["search_provider_response_calls"],
        "all_search_responses_2xx": aggregate.get("search_http_2xx") == gate["search_http_2xx"],
        "no_transport_failures": aggregate.get("transport_failures", 1) <= gate["maximum_transport_failures"],
        "no_search_deadline_failures": aggregate.get("hosted_search_deadline_failures", 1) <= gate["maximum_hosted_search_deadline_failures"],
        "enough_action_groups": aggregate.get("raw_action_group_count", 0) >= gate["minimum_raw_action_group_count"],
        "enough_action_sources": aggregate.get("raw_action_source_count", 0) >= gate["minimum_raw_action_source_count"],
        "matched_selection_cost": aggregate.get("matched_selection_task_count", 0) >= gate["minimum_matched_selection_task_count"],
        "control_minimum_selection": aggregate.get("minimum_control_selected_leads", 0) >= gate["minimum_selected_leads_per_task_per_arm"],
        "candidate_minimum_selection": aggregate.get("minimum_candidate_selected_leads", 0) >= gate["minimum_selected_leads_per_task_per_arm"],
        "control_total_selection": aggregate.get("control_selected_leads", 0) >= gate["minimum_total_selected_leads_per_arm"],
        "candidate_total_selection": aggregate.get("candidate_selected_leads", 0) >= gate["minimum_total_selected_leads_per_arm"],
        "mechanism_changes_enough_tasks": aggregate.get("selection_changed_task_count", 0) >= gate["minimum_selection_changed_task_count"],
        "source_gain_reaches_enough_tasks": aggregate.get("source_coverage_gain_task_count", 0) >= gate["minimum_source_coverage_gain_task_count"],
        "source_gain_is_material": aggregate.get("registrable_source_coverage_gain", 0) >= gate["minimum_total_registrable_source_coverage_gain"],
        "candidate_absolute_source_capability": aggregate.get("candidate_registrable_sources", 0) >= gate["minimum_candidate_registrable_sources"],
        "candidate_source_coverage_improves": _ratio(
            aggregate.get("candidate_registrable_sources", 0), aggregate.get("control_registrable_sources", 0)
        ) >= gate["minimum_candidate_over_control_registrable_source_ratio"],
        "control_has_usable_pages": aggregate.get("control_usable_pages", 0) >= gate["minimum_control_usable_pages"],
        "candidate_usable_pages_bounded": _ratio(
            aggregate.get("candidate_usable_pages", 0), aggregate.get("control_usable_pages", 0)
        ) >= gate["minimum_candidate_over_control_usable_page_ratio"],
        "candidate_usable_chars_bounded": _ratio(
            aggregate.get("candidate_usable_chars", 0), aggregate.get("control_usable_chars", 0)
        ) >= gate["minimum_candidate_over_control_usable_char_ratio"],
        "planned_union_equals_actual_helpers": aggregate.get("planned_shared_url_union_count") == aggregate.get("actual_hard_fetch_helper_calls"),
        "no_fetch_deadlines": aggregate.get("hard_fetch_deadline_failures", 999) <= gate["maximum_hard_fetch_deadline_failures"],
        "no_fetch_helper_failures": aggregate.get("fetch_helper_failures", 999) <= gate["maximum_fetch_helper_failures"],
        "no_fetch_deadline_rejections": aggregate.get("fetch_deadline_rejections", 999) <= gate["maximum_fetch_deadline_rejections"],
        "task_p95_within_cap": float(aggregate.get("task_wall_p95_seconds", 1e9)) <= gate["maximum_task_p95_wall_seconds"],
        "batch_wall_within_cap": float(aggregate.get("batch_wall_seconds", 1e9)) <= gate["maximum_batch_wall_seconds"],
    }
    passed = all(checks.values())
    return {
        "checks": checks,
        "failed_checks": sorted(name for name, ok in checks.items() if not ok),
        "corrected_source_capability_gate_go": passed,
        "benchmark_external_quality_gate_design_authorized": passed,
        "public_exact220_authorized": False,
    }


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    protocol = validate_protocol(_read(PROTOCOL))
    computed = decision(copied.get("aggregate") or {})
    passed = computed["corrected_source_capability_gate_go"] is True
    if (
        copied.get("role") != "v24963_corrected_source_gate_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or copied.get("protected_watchers_before") != protocol["protected_watchers"]
        or copied.get("protected_watchers_after") != protocol["protected_watchers"]
        or copied.get("decision") != computed or copied.get("passed") is not passed
        or copied.get("source_policy") != source_policy()
        or copied.get("authorization") != {
            "benchmark_external_quality_gate_design": passed,
            "benchmark_external_or_exact220_launch": False,
            "evaluator": False, "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.49.63 result drifted")
    return copied


def run() -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(PROTOCOL))
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (RESULT, AUDIT, OUTPUT_ROOT)):
        raise RuntimeError("V2.49.63 result surface is not pristine")
    watchers_before = _watchers()
    with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
        pass
    probe = isolated_probe()
    if probe.__globals__.get("query_vector") is not query_vector or parent.query_vector is query_vector:
        raise RuntimeError("V2.49.63 isolated probe binding drifted")
    started = time.monotonic()
    with acquire_deepwide_api_lease(
        ROOT, owner="v24963_corrected_source_gate",
        purpose="fresh_corrected_cumulative_source_capability_gate",
        path=ROOT / LEASE_PATH,
    ):
        with ThreadPoolExecutor(max_workers=EXECUTOR_CONCURRENCY) as pool:
            rows = list(pool.map(probe, range(TASK_COUNT)))
    aggregate = _aggregate(rows, time.monotonic() - started)
    watchers_after = _watchers()
    computed = decision(aggregate)
    passed = computed["corrected_source_capability_gate_go"] is True
    value: dict[str, Any] = {
        "artifact_version": 1, "role": "v24963_corrected_source_gate_result",
        "protocol_id": PROTOCOL_ID, "created_at_unix": int(time.time()),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "protected_watchers_before": watchers_before,
        "protected_watchers_after": watchers_after,
        "aggregate": aggregate, "decision": computed, "passed": passed,
        "source_policy": protocol["source_policy"],
        "authorization": {
            "benchmark_external_quality_gate_design": passed,
            "benchmark_external_or_exact220_launch": False,
            "evaluator": False, "leaderboard_or_sota": False,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
    publish_new(ROOT / OUTPUT_ROOT / "aggregate.json", value)
    publish_new(ROOT / RESULT, value)
    return validate_result(value)


def audit() -> dict[str, Any]:
    _clean_pushed()
    if (ROOT / AUDIT).exists() or (ROOT / AUDIT).is_symlink():
        raise RuntimeError("V2.49.63 audit surface is not pristine")
    protocol = validate_protocol(_read(PROTOCOL))
    result = validate_result(_read(RESULT))
    output = _read(OUTPUT_ROOT / "aggregate.json")
    watchers = _watchers()
    checks = {
        "protocol_and_result_validate": True,
        "output_copy_matches_result": output == result,
        "aggregate_contains_no_per_task_rows_or_content": result["aggregate"][
            "contains_query_url_host_title_page_answer_provider_payload_selection_or_per_task_row"
        ] is False,
        "fixed_task_count": result["aggregate"]["terminal_task_count"] == TASK_COUNT,
        "protected_watchers_unchanged": watchers == protocol["protected_watchers"] == result["protected_watchers_before"] == result["protected_watchers_after"],
        "shared_api_lease_released": _lease_inactive(),
        "decision_recomputes_exactly": result["decision"] == decision(result["aggregate"]),
        "parent_result_remains_no_go": protocol["parent_observation"]["parent_remains_no_go"] is True,
        "no_benchmark_or_evaluator_authority": result["authorization"]["benchmark_external_or_exact220_launch"] is False and result["authorization"]["evaluator"] is False,
    }
    findings = sorted(name for name, ok in checks.items() if not ok)
    audit_valid = not findings
    gate_go = audit_valid and result["passed"] is True
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24963_corrected_source_gate_postresult_audit",
        "protocol_id": PROTOCOL_ID, "created_at_unix": int(time.time()),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "result_sha256": sha256(ROOT / RESULT),
        "output_sha256": sha256(ROOT / OUTPUT_ROOT / "aggregate.json"),
        "checks": checks, "findings": findings, "audit_valid": audit_valid,
        "corrected_source_capability_gate_go": gate_go,
        "source_policy": source_policy(),
        "authorization": {
            "benchmark_external_quality_gate_design": gate_go,
            "benchmark_external_or_exact220_launch": False,
            "evaluator": False, "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    publish_new(ROOT / AUDIT, value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("protocol", "run", "audit"))
    args = parser.parse_args()
    if args.command == "protocol":
        value = build_protocol()
        publish_new(ROOT / PROTOCOL, value)
        output = {"path": str(PROTOCOL), "role": value["role"]}
    elif args.command == "run":
        value = run()
        output = {"path": str(RESULT), "passed": value["passed"]}
    else:
        value = audit()
        output = {
            "path": str(AUDIT), "audit_valid": value["audit_valid"],
            "corrected_source_capability_gate_go": value[
                "corrected_source_capability_gate_go"
            ],
        }
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
