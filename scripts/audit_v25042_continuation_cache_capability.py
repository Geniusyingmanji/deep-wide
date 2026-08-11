#!/usr/bin/env python3
"""Zero-model audit of Responses continuation and prompt-cache capability."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
DATE = "20260811"
OUTPUT = Path(f"results/v25042_continuation_cache_capability_audit_v1_{DATE}.json")
HISTORICAL = Path("results/v24279_synthesis_factorial_result_v1_20260803.json")
ACTIVE_SOURCES = (
    Path("src/deepwide_agent/native_search.py"),
    Path("src/deepwide_agent/v25036_source_only_hosted_search.py"),
    Path("src/deepwide_agent/v25041_adaptive_single_request.py"),
)
HISTORICAL_PARSER = Path("scripts/probe_v24279_synthesis_factorial.py")
TEST = Path("tests/test_audit_v25042_continuation_cache_capability.py")
EXPECTED_HISTORICAL_SHA256 = "fc3fec71bb33b932f6191609d0a1ce34c7281cacd920696e2617120180ab0781"
OFFICIAL_SOURCES = {
    "conversation_state": "https://developers.openai.com/api/docs/guides/conversation-state#passing-context-from-the-previous-response",
    "prompt_caching": "https://developers.openai.com/api/docs/guides/prompt-caching",
}
REQUEST_FIELDS = (
    "previous_response_id",
    "prompt_cache_key",
    "prompt_cache_options",
    "prompt_cache_breakpoint",
)
USAGE_FIELDS = ("cached_tokens", "cache_write_tokens", "input_tokens_details")


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


def seal(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    copied.pop(field, None)
    copied[field] = payload_sha256(copied)
    return copied


def sealed(value: Mapping[str, Any], field: str) -> bool:
    copied = copy.deepcopy(dict(value))
    observed = copied.pop(field, None)
    return isinstance(observed, str) and observed == payload_sha256(copied)


def ordinary(relative: Path, *, tracked: bool) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.50.42 expected ordinary repository file: {relative}")
    if tracked and subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode != 0:
        raise RuntimeError(f"V2.50.42 expected tracked file: {relative}")
    return path


def clean_pushed() -> str:
    def git(*args: str) -> str:
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

    head = git("rev-parse", "HEAD")
    if git("status", "--porcelain", "--untracked-files=all") or head != git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.50.42 requires clean pushed HEAD")
    return head


def _literal_occurrences(relative: Path, values: tuple[str, ...]) -> dict[str, int]:
    path = ordinary(relative, tracked=True)
    source = path.read_text(encoding="utf-8")
    ast.parse(source, filename=str(path))
    return {value: source.count(value) for value in values}


def local_source_evidence() -> dict[str, Any]:
    request_occurrences = {
        str(relative): _literal_occurrences(relative, REQUEST_FIELDS)
        for relative in ACTIVE_SOURCES
    }
    usage_occurrences = {
        str(relative): _literal_occurrences(relative, USAGE_FIELDS)
        for relative in ACTIVE_SOURCES
    }
    historical_usage = _literal_occurrences(HISTORICAL_PARSER, USAGE_FIELDS)
    return {
        "active_source_sha256": {
            str(relative): sha256(ordinary(relative, tracked=True))
            for relative in ACTIVE_SOURCES
        },
        "active_request_field_occurrences": request_occurrences,
        "active_usage_field_occurrences": usage_occurrences,
        "historical_usage_parser_sha256": sha256(
            ordinary(HISTORICAL_PARSER, tracked=True)
        ),
        "historical_usage_field_occurrences": historical_usage,
        "active_request_fields_all_absent": all(
            count == 0
            for values in request_occurrences.values()
            for count in values.values()
        ),
        "active_cache_usage_fields_all_absent": all(
            count == 0
            for values in usage_occurrences.values()
            for count in values.values()
        ),
        "historical_parser_reads_cached_tokens": historical_usage[
            "cached_tokens"
        ]
        > 0,
        "historical_parser_reads_cache_write_tokens": historical_usage[
            "cache_write_tokens"
        ]
        > 0,
    }


def historical_evidence() -> dict[str, Any]:
    path = ordinary(HISTORICAL, tracked=True)
    if sha256(path) != EXPECTED_HISTORICAL_SHA256:
        raise RuntimeError("V2.50.42 historical cache evidence drifted")
    value = json.loads(path.read_text(encoding="utf-8"))
    outcomes = value.get("outcomes") if isinstance(value, Mapping) else None
    if (
        not isinstance(outcomes, list)
        or len(outcomes) != 32
        or any(not isinstance(row, Mapping) for row in outcomes)
    ):
        raise RuntimeError("V2.50.42 historical outcome denominator drifted")
    inputs = [int(row.get("input_tokens", 0) or 0) for row in outcomes]
    cached = [int(row.get("cached_input_tokens", 0) or 0) for row in outcomes]
    return {
        "path": str(HISTORICAL),
        "sha256": EXPECTED_HISTORICAL_SHA256,
        "outcomes": len(outcomes),
        "input_tokens": sum(inputs),
        "minimum_input_tokens_per_request": min(inputs),
        "maximum_input_tokens_per_request": max(inputs),
        "cached_input_tokens": sum(cached),
        "all_requests_below_official_1024_token_cache_minimum": max(inputs) < 1024,
        "does_not_test_cache_eligible_prefix": max(inputs) < 1024,
    }


def schema_probe(session: Any = requests) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for method, url in (
        ("GET", "http://127.0.0.1:9878/openapi.json"),
        ("OPTIONS", "http://127.0.0.1:9878/responses"),
    ):
        status = 0
        error: str | None = None
        try:
            response = session.request(method, url, timeout=5, allow_redirects=False)
            status = int(response.status_code)
        except requests.RequestException as exc:
            error = type(exc).__name__
        rows.append({"method": method, "path": url.split("9878", 1)[1], "http_status": status, "error": error})
    return {
        "requests": rows,
        "request_count": len(rows),
        "model_search_fetch_or_evaluator_calls": 0,
        "discoverable_schema_found": any(row["http_status"] == 200 for row in rows),
        "response_bodies_persisted_or_hashed": False,
    }


def official_evidence() -> dict[str, Any]:
    return {
        "sources": OFFICIAL_SOURCES,
        "retrieved_at_utc": "2026-08-11",
        "claims": {
            "previous_response_id_carries_context": True,
            "previous_response_id_all_prior_input_tokens_billed": True,
            "gpt56_cache_exact_prefix_at_breakpoint": True,
            "gpt56_minimum_cacheable_prefix_tokens": 1024,
            "gpt56_cache_write_uncached_input_rate_multiplier": 1.25,
            "cache_usage_read_field": "usage.input_tokens_details.cached_tokens",
            "cache_usage_write_field": "usage.input_tokens_details.cache_write_tokens",
            "prompt_cache_key_improves_matching_but_does_not_guarantee_hit": True,
        },
    }


def decision(
    official: Mapping[str, Any],
    local: Mapping[str, Any],
    historical: Mapping[str, Any],
    schema: Mapping[str, Any],
) -> dict[str, Any]:
    claims = official.get("claims") or {}
    checks = {
        "official_previous_response_history_is_billed": claims.get(
            "previous_response_id_all_prior_input_tokens_billed"
        )
        is True,
        "official_cache_requires_eligible_exact_prefix": claims.get(
            "gpt56_minimum_cacheable_prefix_tokens"
        )
        == 1024
        and claims.get("gpt56_cache_exact_prefix_at_breakpoint") is True,
        "official_cache_cost_requires_reads_and_writes": claims.get(
            "gpt56_cache_write_uncached_input_rate_multiplier"
        )
        == 1.25,
        "active_client_has_no_cache_or_continuation_request_fields": local.get(
            "active_request_fields_all_absent"
        )
        is True,
        "active_client_has_no_cache_read_write_accounting": local.get(
            "active_cache_usage_fields_all_absent"
        )
        is True,
        "historical_cache_observation_is_ineligible_negative_control": historical.get(
            "does_not_test_cache_eligible_prefix"
        )
        is True
        and historical.get("cached_input_tokens") == 0,
        "local_proxy_schema_not_discoverable_at_standard_routes": schema.get(
            "discoverable_schema_found"
        )
        is False,
    }
    return {
        "checks": checks,
        "failed_checks": sorted(name for name, ok in checks.items() if not ok),
        "previous_response_id_input_token_savings_hypothesis": "no_go",
        "prompt_cache_support_on_local_proxy_established": False,
        "prompt_cache_net_cost_savings_established": False,
        "prompt_cache_effect_probe_authorized": False,
        "search_cost_continuation_or_cache_mainline_authorized": False,
        "reason": (
            "previous_response_id preserves context but does not remove billed history; "
            "prompt caching remains unestablished locally and current clients neither "
            "request it nor account for cache writes"
        ),
        "quality_mainline_should_resume": all(checks.values()),
    }


def build(*, now: int | None = None, require_clean: bool = True, session: Any = requests) -> dict[str, Any]:
    head = clean_pushed() if require_clean else "0" * 40
    official = official_evidence()
    local = local_source_evidence()
    historical = historical_evidence()
    schema = schema_probe(session)
    result_decision = decision(official, local, historical, schema)
    value = {
        "artifact_version": 1,
        "role": "v25042_continuation_cache_capability_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "official_documentation": official,
        "local_source_evidence": local,
        "historical_usage_evidence": historical,
        "local_proxy_schema_probe": schema,
        "decision": result_decision,
        "source_policy": {
            "model_search_fetch_evaluator_or_benchmark_calls": 0,
            "local_schema_discovery_http_requests": schema["request_count"],
            "benchmark_manifest_question_mapping_gold_category_question_type_split_score_or_reward_read": False,
            "credential_read_print_persist_hash_or_emit": False,
            "query_url_page_prediction_or_provider_payload_persisted": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
        },
        "authorization": {
            "previous_response_id_cost_gate": False,
            "prompt_cache_effect_probe": False,
            "search_cost_continuation_or_cache_mainline": False,
            "resume_shared_page_quality_mainline": result_decision[
                "quality_mainline_should_resume"
            ],
            "dev64_exact220_evaluator_leaderboard_or_sota": False,
        },
    }
    return seal(value, "audit_payload_sha256")


def validate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    official = copied.get("official_documentation") or {}
    local = copied.get("local_source_evidence") or {}
    historical = copied.get("historical_usage_evidence") or {}
    schema = copied.get("local_proxy_schema_probe") or {}
    recomputed = decision(official, local, historical, schema)
    if (
        copied.get("role") != "v25042_continuation_cache_capability_audit"
        or copied.get("decision") != recomputed
        or copied.get("source_policy", {}).get(
            "model_search_fetch_evaluator_or_benchmark_calls"
        )
        != 0
        or copied.get("authorization", {}).get("prompt_cache_effect_probe") is not False
        or copied.get("authorization", {}).get(
            "dev64_exact220_evaluator_leaderboard_or_sota"
        )
        is not False
        or not sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.42 audit drifted")
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
    argparse.ArgumentParser().parse_args()
    value = validate(build())
    publish(value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "decision": value["decision"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
