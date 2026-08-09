#!/usr/bin/env python3
"""Fresh shared-response live gate for registrable-source-fair discovery."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.clients import SearchRequestError, canonicalize_url  # noqa: E402
from deepwide_agent.v24280_task_union_single_shot import (  # noqa: E402
    parse_task_union_single_shot,
)
from deepwide_agent.v24316_deadline_search import validate_transport_health  # noqa: E402
from deepwide_agent.v24743_generic_record_binding import _source_key  # noqa: E402
from deepwide_agent.v24959_source_fair_discovery import (  # noqa: E402
    compare_prefixes,
    order_source_fair_leads,
)
from scripts import v24958_action_fair_live_gate as base  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260809"
PROTOCOL_ID = "v24960_registrable_source_fair_shared_response_live_gate_v1"
PROTOCOL = Path(
    f"results/v24960_source_fair_live_preregistration_v1_{DATE}.json"
)
RESULT = Path(f"results/v24960_source_fair_live_result_v1_{DATE}.json")
AUDIT = Path(f"results/v24960_source_fair_live_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24960_source_fair_live_v1_{DATE}")
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")

ENDPOINT = base.ENDPOINT
MODEL = base.MODEL
CONTROL = "stable_first_seen"
CANDIDATE = "registrable_source_fair"
ARMS = (CONTROL, CANDIDATE)
TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
LOGICAL_QUERIES_PER_TASK = 4
QUERIES_PER_WAVE = 2
WAVE_FETCH_CAPS = (6, 4)
FETCH_CAP_PER_ARM = 10
RESULTS_PER_QUERY = 3
TASK_DEADLINE_SECONDS = 150.0
MAX_TASK_P95_SECONDS = 130.0
MAX_BATCH_SECONDS = 170.0
PRODUCTS = (
    ("Caddy", "2.8"),
    ("HAProxy", "3.0"),
    ("Envoy", "1.31"),
    ("Traefik", "3.1"),
    ("HashiCorp Consul", "1.19"),
    ("HashiCorp Vault", "1.17"),
    ("HashiCorp Nomad", "1.8"),
    ("OpenTofu", "1.8"),
    ("Bazel", "7.3"),
    ("Neovim", "0.10"),
    ("GNU Emacs", "29.4"),
    ("GDB", "15.1"),
    ("GCC", "14.2"),
    ("PHP", "8.3"),
    ("Ruby", "3.3"),
    ("Perl", "5.40"),
    (".NET", "8"),
    ("Spring Boot", "3.3"),
    ("Apache Tomcat", "10.1"),
    ("Eclipse Temurin", "21"),
)
QUERY_PATTERNS = (
    "{product} {version} official documentation release notes",
    "{product} {version} official documentation installation guide",
    "{product} {version} official documentation configuration reference",
    "{product} {version} official documentation security migration changes",
)
PROTECTED_WATCHERS = base.PROTECTED_WATCHERS
SOURCES = (
    Path("scripts/v24960_source_fair_live_gate.py"),
    Path("tests/test_v24960_source_fair_live_gate.py"),
    Path("src/deepwide_agent/v24959_source_fair_discovery.py"),
    Path("src/deepwide_agent/v24957_action_fair_discovery.py"),
    Path("src/deepwide_agent/v24743_generic_record_binding.py"),
    Path("scripts/v24958_action_fair_live_gate.py"),
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


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


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
        raise RuntimeError("V2.49.60 requires a clean pushed HEAD")


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
            raise RuntimeError(f"V2.49.60 source identity drifted: {relative}")
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError(f"V2.49.60 credential literal in {relative}")
        output[str(relative)] = sha256(path)
    return output


def _read(relative: Path) -> dict[str, Any]:
    path = ROOT / relative
    if (
        relative.is_absolute() or ".." in relative.parts or path.is_symlink()
        or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.49.60 expected ordinary repository object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.60 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def expected_watchers() -> list[dict[str, Any]]:
    return base.expected_watchers()


def _watchers() -> list[dict[str, Any]]:
    return base._watchers()


def _lease_inactive() -> bool:
    path = ROOT / LEASE_PATH
    if path.is_symlink():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return True


def query_vector() -> tuple[tuple[str, ...], ...]:
    if len(PRODUCTS) != TASK_COUNT:
        raise RuntimeError("V2.49.60 neutral product vector drifted")
    return tuple(
        tuple(pattern.format(product=product, version=version) for pattern in QUERY_PATTERNS)
        for product, version in PRODUCTS
    )


def source_policy() -> dict[str, bool]:
    return {
        "fresh_neutral_public_software_documentation_queries_only": True,
        "same_provider_payload_replayed_by_both_arms": True,
        "same_fetched_page_bytes_used_for_shared_urls": True,
        "provider_narrative_or_snippet_used_as_active_evidence": False,
        "query_url_host_title_page_answer_provider_payload_selection_or_per_task_row_persisted": False,
        "benchmark_manifest_question_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "credential_value_environment_or_keyring_read": False,
        "task_answer_synthesis_or_evaluator_effect": False,
        "entropy_or_information_gain_used_for_selection_or_credit": False,
    }


def gates() -> dict[str, Any]:
    return {
        "terminal_task_count": 20,
        "completed_task_count": 20,
        "search_provider_attempts": 40,
        "search_provider_response_calls": 40,
        "search_http_2xx": 40,
        "maximum_transport_failures": 0,
        "maximum_hosted_search_deadline_failures": 0,
        "minimum_raw_action_group_count": 40,
        "minimum_raw_action_source_count": 400,
        "minimum_matched_selection_task_count": 20,
        "minimum_selected_leads_per_task_per_arm": 2,
        "minimum_total_selected_leads_per_arm": 180,
        "minimum_selection_changed_task_count": 16,
        "minimum_source_coverage_gain_task_count": 12,
        "minimum_total_registrable_source_coverage_gain": 20,
        "minimum_control_registrable_sources": 60,
        "minimum_candidate_over_control_registrable_source_ratio": 1.10,
        "minimum_control_usable_pages": 120,
        "minimum_candidate_over_control_usable_page_ratio": 0.95,
        "minimum_candidate_over_control_usable_char_ratio": 0.85,
        "maximum_hard_fetch_deadline_failures": 4,
        "maximum_fetch_helper_failures": 4,
        "maximum_task_p95_wall_seconds": MAX_TASK_P95_SECONDS,
        "maximum_batch_wall_seconds": MAX_BATCH_SECONDS,
    }


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
        raise RuntimeError("V2.49.60 future surface is not pristine")
    manifest = _manifest(tracked=require_clean)
    watchers = _watchers() if require_watchers else expected_watchers()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24960_source_fair_live_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD") if require_clean else "build-only",
        "provider": {
            "endpoint": ENDPOINT, "model": MODEL, "keyless": True,
            "reasoning_effort": "low", "service_tier": "priority",
            "search_context_size": "medium", "max_retries": 1,
        },
        "schedule": {
            "task_count": TASK_COUNT,
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "logical_queries_per_task": LOGICAL_QUERIES_PER_TASK,
            "queries_per_wave": QUERIES_PER_WAVE,
            "wave_fetch_caps": list(WAVE_FETCH_CAPS),
            "fetch_cap_per_arm": FETCH_CAP_PER_ARM,
            "maximum_shared_physical_fetches_per_task": FETCH_CAP_PER_ARM * 2,
            "task_deadline_seconds": TASK_DEADLINE_SECONDS,
            "query_vector_sha256": payload_sha256(query_vector()),
            "one_provider_attempt_per_wave": True,
            "shared_response_replay": True,
            "task_local_shared_fetch_union": True,
        },
        "arms": {
            CONTROL: "query_local_prefix_then_stable_first_seen_action_sources",
            CANDIDATE: "first_representative_per_registrable_source_then_deferred_duplicates",
        },
        "gates": gates(),
        "protected_watchers": watchers,
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": source_policy(),
        "authorization": {
            "one_fresh_neutral_source_fair_live_gate": True,
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
    if (
        copied.get("role") != "v24960_source_fair_live_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("schedule", {}).get("task_count") != TASK_COUNT
        or copied.get("schedule", {}).get("wave_fetch_caps") != list(WAVE_FETCH_CAPS)
        or copied.get("schedule", {}).get("query_vector_sha256") != payload_sha256(query_vector())
        or copied.get("gates") != gates()
        or copied.get("protected_watchers") != expected_watchers()
        or copied.get("source_manifest") != manifest
        or copied.get("source_manifest_sha256") != payload_sha256(manifest)
        or copied.get("source_policy") != source_policy()
        or copied.get("authorization", {}).get("benchmark_external_or_exact220_launch") is not False
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.49.60 protocol drifted")
    return copied


def _client(deadline: float) -> Any:
    return base._client(deadline)


def _registrable_sources(leads: Sequence[Mapping[str, Any]]) -> set[str]:
    output: set[str] = set()
    for lead in leads:
        url = canonicalize_url(str(lead.get("fetch_url") or lead.get("url") or ""))
        host = (urlsplit(url).hostname or "").casefold() if url else ""
        try:
            output.add(_source_key(host))
        except ValueError:
            continue
    return output


def _probe(index: int) -> dict[str, int | float | bool]:
    deadline = time.monotonic() + TASK_DEADLINE_SECONDS
    client = _client(deadline)
    started = time.monotonic()
    selected: dict[str, list[dict[str, str]]] = {arm: [] for arm in ARMS}
    prior_urls: dict[str, set[str]] = {arm: set() for arm in ARMS}
    prior_candidate_sources: set[str] = set()
    raw_action_groups = raw_action_sources = 0
    completed = True
    query_rows = 0
    try:
        queries = query_vector()[index]
        for wave_index, cap in enumerate(WAVE_FETCH_CAPS):
            wave_queries = list(
                queries[wave_index * QUERIES_PER_WAVE : (wave_index + 1) * QUERIES_PER_WAVE]
            )
            payload = client._request(wave_queries)
            batches, _complete, _normalized, _attachments = parse_task_union_single_shot(
                client, wave_queries, payload, max_results=RESULTS_PER_QUERY
            )
            _ordered, observation, _private = order_source_fair_leads(
                batches, prior_sources=prior_candidate_sources
            )
            value = compare_prefixes(
                batches, cap=cap,
                prior_control_urls=prior_urls[CONTROL],
                prior_candidate_urls=prior_urls[CANDIDATE],
                prior_candidate_sources=prior_candidate_sources,
            )
            raw_action_groups += int(observation["raw_action_group_count"])
            raw_action_sources += int(observation["raw_action_source_count"])
            query_rows += len(wave_queries)
            for arm, key in ((CONTROL, "stable"), (CANDIDATE, "candidate")):
                leads = list(value[key])
                selected[arm].extend(leads)
                prior_urls[arm].update(
                    canonicalize_url(str(lead.get("url", ""))) for lead in leads
                )
            prior_candidate_sources.update(value["candidate_sources"])
    except (SearchRequestError, ValueError, RuntimeError, OSError):
        completed = False

    union: list[dict[str, str]] = []
    seen: set[str] = set()
    for arm in ARMS:
        for lead in selected[arm]:
            url = canonicalize_url(str(lead.get("url", "")))
            if not url or url in seen:
                continue
            seen.add(url)
            union.append({
                "url": str(lead.get("fetch_url") or lead.get("url") or ""),
                "query": "shared paired neutral fetch",
                "title": str(lead.get("title", "")),
                "member_label": "",
            })
    fetched_batches: Any = []
    if completed and union:
        try:
            fetched_batches = client.fetch_urls(union)
        except (ValueError, RuntimeError, OSError):
            completed = False
    fetched = base._fetch_map(fetched_batches)
    stats = {arm: base._arm_page_stats(selected[arm], fetched) for arm in ARMS}
    sources = {arm: _registrable_sources(selected[arm]) for arm in ARMS}
    if len(sources[CANDIDATE]) < len(sources[CONTROL]):
        completed = False
    control_urls = [canonicalize_url(str(item.get("url", ""))) for item in selected[CONTROL]]
    candidate_urls = [canonicalize_url(str(item.get("url", ""))) for item in selected[CANDIDATE]]
    health = validate_transport_health(client.transport_health())
    statuses = dict(client.status_counts)
    gain = max(0, len(sources[CANDIDATE]) - len(sources[CONTROL]))
    return {
        "terminal": True,
        "completed": completed,
        "logical_query_rows": query_rows,
        "search_provider_attempts": int(health["hosted_search_attempts"]),
        "search_provider_response_calls": int(client.calls),
        "search_http_2xx": sum(count for status, count in statuses.items() if 200 <= status < 300),
        "transport_failures": int(client.transport_failures),
        "hosted_search_deadline_failures": int(health["hosted_search_deadline_failures"]),
        "raw_action_group_count": raw_action_groups,
        "raw_action_source_count": raw_action_sources,
        "matched_selection": len(control_urls) == len(candidate_urls),
        "control_selected_leads": stats[CONTROL]["selected_leads"],
        "candidate_selected_leads": stats[CANDIDATE]["selected_leads"],
        "selection_changed": control_urls != candidate_urls,
        "control_registrable_sources": len(sources[CONTROL]),
        "candidate_registrable_sources": len(sources[CANDIDATE]),
        "registrable_source_coverage_gain": gain,
        "source_coverage_gain_task": gain > 0,
        "control_usable_pages": stats[CONTROL]["usable_pages"],
        "candidate_usable_pages": stats[CANDIDATE]["usable_pages"],
        "control_usable_chars": stats[CONTROL]["usable_chars"],
        "candidate_usable_chars": stats[CANDIDATE]["usable_chars"],
        "physical_union_fetches": len(union),
        "hard_fetch_helper_calls": int(health["hard_fetch_helper_calls"]),
        "hard_fetch_deadline_failures": int(health["hard_fetch_deadline_failures"]),
        "fetch_helper_failures": int(health["fetch_helper_failures"]),
        "fetch_deadline_rejections": int(health["fetch_deadline_rejections"]),
        "input_tokens": int(client.input_tokens),
        "output_tokens": int(client.output_tokens),
        "total_tokens": int(client.total_tokens),
        "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
    }


def _percentile(values: Sequence[float], probability: float) -> float:
    return base._percentile(list(values), probability)


def _aggregate(
    rows: Sequence[Mapping[str, int | float | bool]], batch_wall: float
) -> dict[str, Any]:
    counters: Counter[str] = Counter()
    walls: list[float] = []
    control_selected: list[int] = []
    candidate_selected: list[int] = []
    for row in rows:
        walls.append(float(row.get("wall_seconds", 0.0)))
        control_selected.append(int(row.get("control_selected_leads", 0)))
        candidate_selected.append(int(row.get("candidate_selected_leads", 0)))
        for name, amount in row.items():
            if name != "wall_seconds":
                counters[name] += int(amount)
    return {
        **{name: int(counters[name]) for name in sorted(counters)},
        "terminal_task_count": int(counters["terminal"]),
        "completed_task_count": int(counters["completed"]),
        "failed_task_count": len(rows) - int(counters["completed"]),
        "matched_selection_task_count": int(counters["matched_selection"]),
        "selection_changed_task_count": int(counters["selection_changed"]),
        "source_coverage_gain_task_count": int(counters["source_coverage_gain_task"]),
        "minimum_control_selected_leads": min(control_selected, default=0),
        "minimum_candidate_selected_leads": min(candidate_selected, default=0),
        "task_wall_p50_seconds": _percentile(walls, 0.50),
        "task_wall_p95_seconds": _percentile(walls, 0.95),
        "task_wall_max_seconds": round(max(walls, default=0.0), 6),
        "batch_wall_seconds": round(max(0.0, float(batch_wall)), 6),
        "contains_query_url_host_title_page_answer_provider_payload_selection_or_per_task_row": False,
    }


def _ratio(numerator: Any, denominator: Any) -> float:
    left = float(numerator)
    right = float(denominator)
    return left / right if right > 0 else float("inf")


def decision(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    gate = gates()
    checks = {
        "all_tasks_terminal": aggregate.get("terminal_task_count") == gate["terminal_task_count"],
        "all_tasks_completed": aggregate.get("completed_task_count") == gate["completed_task_count"],
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
        "control_source_coverage_present": aggregate.get("control_registrable_sources", 0) >= gate["minimum_control_registrable_sources"],
        "candidate_source_coverage_improves": _ratio(
            aggregate.get("candidate_registrable_sources", 0),
            aggregate.get("control_registrable_sources", 0),
        ) >= gate["minimum_candidate_over_control_registrable_source_ratio"],
        "control_has_usable_pages": aggregate.get("control_usable_pages", 0) >= gate["minimum_control_usable_pages"],
        "candidate_usable_pages_bounded": _ratio(
            aggregate.get("candidate_usable_pages", 0), aggregate.get("control_usable_pages", 0)
        ) >= gate["minimum_candidate_over_control_usable_page_ratio"],
        "candidate_usable_chars_bounded": _ratio(
            aggregate.get("candidate_usable_chars", 0), aggregate.get("control_usable_chars", 0)
        ) >= gate["minimum_candidate_over_control_usable_char_ratio"],
        "physical_fetches_conserved": aggregate.get("physical_union_fetches") == aggregate.get("hard_fetch_helper_calls"),
        "fetch_deadlines_bounded": aggregate.get("hard_fetch_deadline_failures", 999) <= gate["maximum_hard_fetch_deadline_failures"],
        "fetch_helper_failures_bounded": aggregate.get("fetch_helper_failures", 999) <= gate["maximum_fetch_helper_failures"],
        "task_p95_within_cap": float(aggregate.get("task_wall_p95_seconds", 1e9)) <= gate["maximum_task_p95_wall_seconds"],
        "batch_wall_within_cap": float(aggregate.get("batch_wall_seconds", 1e9)) <= gate["maximum_batch_wall_seconds"],
    }
    passed = all(checks.values())
    return {
        "checks": checks,
        "failed_checks": sorted(name for name, ok in checks.items() if not ok),
        "source_fair_live_gate_go": passed,
        "benchmark_external_quality_gate_design_authorized": passed,
        "public_exact220_authorized": False,
    }


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    protocol = validate_protocol(_read(PROTOCOL))
    computed = decision(copied.get("aggregate") or {})
    passed = computed["source_fair_live_gate_go"] is True
    if (
        copied.get("role") != "v24960_source_fair_live_result"
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
        raise RuntimeError("V2.49.60 result drifted")
    return copied


def run() -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(PROTOCOL))
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (RESULT, AUDIT, OUTPUT_ROOT)):
        raise RuntimeError("V2.49.60 result surface is not pristine")
    watchers_before = _watchers()
    with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
        pass
    started = time.monotonic()
    with acquire_deepwide_api_lease(
        ROOT, owner="v24960_source_fair_live_gate",
        purpose="fresh_neutral_shared_response_registrable_source_fair_exposure",
        path=ROOT / LEASE_PATH,
    ):
        with ThreadPoolExecutor(max_workers=EXECUTOR_CONCURRENCY) as pool:
            rows = list(pool.map(_probe, range(TASK_COUNT)))
    aggregate = _aggregate(rows, time.monotonic() - started)
    watchers_after = _watchers()
    computed = decision(aggregate)
    passed = computed["source_fair_live_gate_go"] is True
    value: dict[str, Any] = {
        "artifact_version": 1, "role": "v24960_source_fair_live_result",
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
        raise RuntimeError("V2.49.60 audit surface is not pristine")
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
        "no_benchmark_or_evaluator_authority": result["authorization"]["benchmark_external_or_exact220_launch"] is False and result["authorization"]["evaluator"] is False,
    }
    findings = sorted(name for name, ok in checks.items() if not ok)
    audit_valid = not findings
    gate_go = audit_valid and result["passed"] is True
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24960_source_fair_live_postresult_audit",
        "protocol_id": PROTOCOL_ID, "created_at_unix": int(time.time()),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "result_sha256": sha256(ROOT / RESULT),
        "output_sha256": sha256(ROOT / OUTPUT_ROOT / "aggregate.json"),
        "checks": checks, "findings": findings, "audit_valid": audit_valid,
        "source_fair_live_gate_go": gate_go,
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
        output = {"path": str(AUDIT), "audit_valid": value["audit_valid"], "source_fair_live_gate_go": value["source_fair_live_gate_go"]}
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
