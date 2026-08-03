#!/usr/bin/env python3
"""Preregister, run, and decide one neutral V2.42.94 staged-reserve probe."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.native_search import AzureNativeSearchClient  # noqa: E402
from deepwide_agent.v24294_staged_reserve import (  # noqa: E402
    StagedReservePolicy,
    payload_sha256,
    run_staged_reserve,
    validate_receipt,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


PROTOCOL_ID = "v24295_neutral_real_provider_staged_reserve_6_2_2_v1"
PROTOCOL = Path("results/v24295_neutral_staged_reserve_preregistration_v1_20260803.json")
RESULT = Path("results/v24295_neutral_staged_reserve_probe_v1_20260803.json")
DECISION = Path("results/v24295_neutral_staged_reserve_decision_v1_20260803.json")
PARENT = Path("results/v24293_v24291_dev64_postterminal_diagnosis_v1_20260803.json")
SOURCE_FILES = (
    "src/deepwide_agent/v24294_staged_reserve.py",
    "scripts/v24295_neutral_staged_reserve.py",
    "tests/test_v24294_staged_reserve.py",
    "tests/test_v24295_neutral_staged_reserve.py",
)
NEUTRAL_QUERIES = (
    "site:docs.python.org/3.13 whatsnew Python 3.13 free threaded CPython official documentation",
    "site:docs.python.org/3.13 whatsnew Python 3.13 JIT official documentation",
    "site:docs.python.org/3.13 library sys monitoring official documentation",
    "site:docs.python.org/3.13 library asyncio Python 3.13 changes official documentation",
)
SEARCH_COUNTERS = (
    "calls", "failures", "tool_calls", "fetch_calls", "fetch_failures",
    "input_tokens", "output_tokens", "total_tokens",
)
SECRET = re.compile(r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}")
GATES = {
    "maximum_wall_seconds": 180.0,
    "required_controller_decision": "expand",
    "required_reserved_reason": "low_coverage_diversity_tail",
    "required_low_coverage_before_reserved": True,
    "required_fetches_before_reserved": 8,
    "required_reserved_fetches": 2,
    "required_selected_tail_count": 2,
    "minimum_reserved_usable_pages": 1,
    "minimum_reserved_novel_pages": 1,
    "usable_pages_after_must_exceed_before": True,
    "content_chars_after_must_exceed_before": True,
    "maximum_total_queries": 4,
    "maximum_total_fetches": 10,
    "maximum_added_hosted_search_requests": 0,
    "provider_search_calls_unchanged_during_reserved": True,
    "required_real_fetch_requests_masked": 8,
    "required_real_reserved_fetch_requests_unmasked": 2,
}


def sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    path = root / raw
    if (
        raw.is_absolute()
        or ".." in raw.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.42.95 expected ordinary file: {relative}")
    return path


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.42.95 expected object: {relative}")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _manifest(root: Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCE_FILES:
        path = _ordinary(root, relative)
        source = path.read_text(encoding="utf-8")
        if SECRET.search(source):
            raise RuntimeError(f"V2.42.95 credential literal in {relative}")
        output[relative] = sha256(path)
    return output


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


class FirstEightFetchOutcomeMask:
    """Execute real fetches, but hide exactly the first eight results in memory."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.fetch_invocations = 0
        self.real_fetch_requests_masked = 0
        self.real_fetch_batches_masked = 0
        self.real_reserved_fetch_requests_unmasked = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def search_many(self, queries: Sequence[str], **kwargs: Any) -> Any:
        return self.inner.search_many(queries, **kwargs)

    def fetch_urls(self, requests_: Sequence[dict[str, str]]) -> Any:
        values = list(requests_)
        response = self.inner.fetch_urls(values)
        self.fetch_invocations += 1
        if self.real_fetch_requests_masked < 8:
            if self.real_fetch_requests_masked + len(values) > 8:
                raise RuntimeError("V2.42.95 mask boundary split one fetch invocation")
            self.real_fetch_requests_masked += len(values)
            self.real_fetch_batches_masked += len(response) if isinstance(response, list) else 0
            return []
        self.real_reserved_fetch_requests_unmasked += len(values)
        return response


def _counters(client: Any) -> dict[str, int]:
    return {name: max(0, int(getattr(client, name, 0) or 0)) for name in SEARCH_COUNTERS}


def _finite(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"V2.42.95 {label} is not numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise RuntimeError(f"V2.42.95 {label} is invalid")
    return number


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    if require_pristine:
        present = [str(path) for path in (RESULT, DECISION) if (root / path).exists() or (root / path).is_symlink()]
        if present:
            raise RuntimeError(f"V2.42.95 future surface is not pristine: {present}")
    parent = _read(root, PARENT)
    if (
        parent.get("role") != "v24293_v24291_dev64_postterminal_diagnosis"
        or parent.get("conclusions", {}).get("reserved_tail_capacity_required_before_any_new_benchmark") is not True
        or parent.get("conclusions", {}).get("exact220_authorized") is not False
        or parent.get("next_experiment", {}).get("stage") != "neutral_and_synthetic_only"
        or parent.get("next_experiment", {}).get("maximum_total_fetches") != 10
        or not _sealed(parent, "diagnosis_payload_sha256")
    ):
        raise RuntimeError("V2.42.95 diagnosis parent drifted")
    manifest = _manifest(root)
    value = {
        "artifact_version": 1,
        "role": "v24295_neutral_staged_reserve_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": "one_fault_injected_neutral_real_provider_staged_reserve_probe",
        "parent": {"path": str(PARENT), "sha256": sha256(root / PARENT)},
        "task_contract": {
            "synthetic_public_documentation_queries": True,
            "query_count": 4,
            "required_column_proxy": 14,
            "query_value_or_hash_persisted_in_result": False,
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_opened": False,
        },
        "provider": {
            "proxy_url": "http://127.0.0.1:9878/responses",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "low",
            "service_tier": "priority",
            "timeout_seconds": 180,
            "max_retries": 2,
            "search_context_size": "medium",
            "search_batch_size": 8,
            "fetch_workers": 8,
            "fetch_timeout_seconds": 20,
        },
        "fault_injection": {
            "kind": "first_eight_real_fetch_outcomes_masked_in_memory",
            "all_provider_search_calls_unmodified": True,
            "all_ten_real_fetch_requests_executed": True,
            "first_eight_fetch_results_hidden_only_from_controller": True,
            "final_two_reserved_fetch_results_unmodified": True,
            "claim_scope": "mechanism_robustness_not_natural_frequency_or_benchmark_quality",
        },
        "retrieval_contract": {
            "schedule": "6_first_plus_2_observation_plus_2_reserved",
            "maximum_queries": 4,
            "maximum_fetches": 10,
            "reserved_fetches": 2,
            "additional_hosted_search_request_for_reserved": False,
            "same_response_deterministic_candidates_only": True,
        },
        "gates": dict(GATES),
        "lease": {
            "path": "outputs/deepwide_benchmark_api.lease.lock",
            "owner": "v24295_neutral_staged_reserve_probe_v1",
            "purpose": "neutral_real_provider_staged_reserve_6_2_2",
            "nonblocking_single_owner": True,
        },
        "surface_manifest": manifest,
        "surface_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_read": False,
            "query_url_host_page_prediction_answer_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
        },
        "authorization": {
            "one_neutral_probe": True,
            "benchmark_dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
            "training_credit_assignment": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    validate_protocol(root, value=value)
    return value


def validate_protocol(root: Path = ROOT, *, value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = dict(value) if value is not None else _read(root, PROTOCOL)
    task = protocol.get("task_contract")
    injection = protocol.get("fault_injection")
    retrieval = protocol.get("retrieval_contract")
    manifest = protocol.get("surface_manifest")
    source = protocol.get("source_policy")
    auth = protocol.get("authorization")
    if (
        protocol.get("role") != "v24295_neutral_staged_reserve_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or protocol.get("scope") != "one_fault_injected_neutral_real_provider_staged_reserve_probe"
        or protocol.get("gates") != GATES
        or not _sealed(protocol, "protocol_payload_sha256")
        or not isinstance(task, Mapping)
        or task.get("query_count") != 4
        or task.get("required_column_proxy") != 14
        or task.get("benchmark_manifest_mapping_gold_prediction_or_evaluator_opened") is not False
        or task.get("query_value_or_hash_persisted_in_result") is not False
        or not isinstance(injection, Mapping)
        or injection.get("claim_scope") != "mechanism_robustness_not_natural_frequency_or_benchmark_quality"
        or not isinstance(retrieval, Mapping)
        or retrieval.get("schedule") != "6_first_plus_2_observation_plus_2_reserved"
        or retrieval.get("maximum_queries") != 4
        or retrieval.get("maximum_fetches") != 10
        or retrieval.get("additional_hosted_search_request_for_reserved") is not False
        or not isinstance(manifest, Mapping)
        or set(manifest) != set(SOURCE_FILES)
        or protocol.get("surface_manifest_sha256") != payload_sha256(manifest)
        or any(sha256(_ordinary(root, relative)) != digest for relative, digest in manifest.items())
        or not isinstance(source, Mapping)
        or any(source.values())
        or not isinstance(auth, Mapping)
        or auth.get("one_neutral_probe") is not True
        or any(value_ for key, value_ in auth.items() if key != "one_neutral_probe")
    ):
        raise RuntimeError("V2.42.95 protocol drifted")
    parent = _read(root, PARENT)
    if protocol.get("parent") != {"path": str(PARENT), "sha256": sha256(root / PARENT)} or not _sealed(parent, "diagnosis_payload_sha256"):
        raise RuntimeError("V2.42.95 parent binding drifted")
    return protocol


def project(
    retrieval: Mapping[str, Any],
    *,
    search_counters: Mapping[str, int],
    injection: FirstEightFetchOutcomeMask,
    wall_seconds: float,
    now: int | None = None,
) -> dict[str, Any]:
    receipt = retrieval["receipt"]
    validate_receipt(receipt)
    before = receipt["total_before_reserved"]
    stage = receipt["reserved_stage"]
    total = receipt["total"]
    value = {
        "artifact_version": 1,
        "role": "v24295_neutral_staged_reserve_probe",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": "fault_injected_neutral_real_provider_staged_reserve_only",
        "provider": "azure-native-keyless-gpt-5.6-sol",
        "wall_seconds": round(max(0.0, float(wall_seconds)), 6),
        "search_counters": dict(search_counters),
        "fault_injection": {
            "kind": "first_eight_real_fetch_outcomes_masked_in_memory",
            "fetch_invocations": injection.fetch_invocations,
            "real_fetch_requests_masked": injection.real_fetch_requests_masked,
            "real_fetch_batches_masked": injection.real_fetch_batches_masked,
            "real_reserved_fetch_requests_unmasked": injection.real_reserved_fetch_requests_unmasked,
            "query_url_host_page_or_provider_payload_persisted": False,
        },
        "controller": {
            "decision": receipt["controller"]["decision"],
            "reason": receipt["controller"]["reason"],
            "provider_search_calls_before_reserved": receipt["provider_search_calls_before_reserved"],
            "provider_search_calls_after_reserved": receipt["provider_search_calls_after_reserved"],
            "hosted_search_requests_added_by_reserved": receipt["hosted_search_requests_added_by_reserved"],
        },
        "coverage": {
            "queries_executed": total["queries_executed"],
            "fetches_before_reserved": before["fetches_attempted"],
            "usable_pages_before_reserved": before["usable_pages"],
            "unique_hosts_before_reserved": before["unique_hosts"],
            "content_chars_before_reserved": before["content_chars"],
            "reserved_executed": stage["executed"],
            "reserved_reason": stage["reason"],
            "low_coverage_before_reserved": stage["low_coverage_before"],
            "ranked_candidate_count": stage["ranked_candidate_count"],
            "tail_candidate_count": stage["tail_candidate_count"],
            "selected_ranked_count": stage["selected_ranked_count"],
            "selected_tail_count": stage["selected_tail_count"],
            "reserved_fetches": stage["fetches_attempted"],
            "reserved_usable_pages": stage["usable_pages"],
            "reserved_novel_pages": stage["novel_pages"],
            "fetches_after_reserved": total["fetches_attempted"],
            "usable_pages_after_reserved": total["usable_pages"],
            "unique_hosts_after_reserved": total["unique_hosts"],
            "content_chars_after_reserved": total["content_chars"],
        },
        "runtime_health": {
            "provider_fetch_calls_match_receipt": search_counters["fetch_calls"] == total["fetches_attempted"],
            "controller_search_invocations_unchanged_during_reserved": receipt["controller_search_invocations_before_reserved"] == receipt["controller_search_invocations_after_reserved"],
            "provider_search_calls_unchanged_during_reserved": receipt["provider_search_calls_before_reserved"] == receipt["provider_search_calls_after_reserved"],
        },
        "source_policy": {
            "synthetic_public_documentation_queries_used_but_not_persisted_or_hashed": True,
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_read": False,
            "query_url_host_page_prediction_answer_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
            "shared_api_lease_acquired": True,
        },
        "authorization": {
            "benchmark_dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
            "training_credit_assignment": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
    validate_projection(value)
    return value


def validate_projection(value: Mapping[str, Any]) -> None:
    search = value.get("search_counters")
    injection = value.get("fault_injection")
    controller = value.get("controller")
    coverage = value.get("coverage")
    health = value.get("runtime_health")
    source = value.get("source_policy")
    auth = value.get("authorization")
    if (
        value.get("role") != "v24295_neutral_staged_reserve_probe"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("scope") != "fault_injected_neutral_real_provider_staged_reserve_only"
        or value.get("provider") != "azure-native-keyless-gpt-5.6-sol"
        or not _sealed(value, "result_payload_sha256")
        or not isinstance(search, Mapping)
        or set(search) != set(SEARCH_COUNTERS)
        or any(isinstance(number, bool) or not isinstance(number, int) or number < 0 for number in search.values())
        or not isinstance(injection, Mapping)
        or set(injection) != {
            "kind", "fetch_invocations", "real_fetch_requests_masked", "real_fetch_batches_masked",
            "real_reserved_fetch_requests_unmasked", "query_url_host_page_or_provider_payload_persisted",
        }
        or injection.get("kind") != "first_eight_real_fetch_outcomes_masked_in_memory"
        or injection.get("query_url_host_page_or_provider_payload_persisted") is not False
        or any(
            isinstance(injection.get(name), bool)
            or not isinstance(injection.get(name), int)
            or injection[name] < 0
            for name in (
                "fetch_invocations",
                "real_fetch_requests_masked",
                "real_fetch_batches_masked",
                "real_reserved_fetch_requests_unmasked",
            )
        )
        or not isinstance(controller, Mapping)
        or not isinstance(coverage, Mapping)
        or not isinstance(health, Mapping)
        or not isinstance(source, Mapping)
        or source.get("synthetic_public_documentation_queries_used_but_not_persisted_or_hashed") is not True
        or source.get("shared_api_lease_acquired") is not True
        or any(value_ for key, value_ in source.items() if key not in {"synthetic_public_documentation_queries_used_but_not_persisted_or_hashed", "shared_api_lease_acquired"})
        or not isinstance(auth, Mapping)
        or any(auth.values())
    ):
        raise RuntimeError("V2.42.95 neutral projection drifted")
    _finite(value.get("wall_seconds"), label="wall seconds")
    if (
        controller.get("provider_search_calls_before_reserved") != controller.get("provider_search_calls_after_reserved")
        or controller.get("hosted_search_requests_added_by_reserved") != 0
        or coverage.get("queries_executed", 5) > 4
        or coverage.get("fetches_after_reserved", 11) > 10
        or coverage.get("usable_pages_after_reserved", -1) < coverage.get("usable_pages_before_reserved", 0)
        or coverage.get("content_chars_after_reserved", -1) < coverage.get("content_chars_before_reserved", 0)
        or health.get("provider_fetch_calls_match_receipt") is not True
        or health.get("controller_search_invocations_unchanged_during_reserved") is not True
        or health.get("provider_search_calls_unchanged_during_reserved") is not True
        or search["fetch_calls"] != coverage["fetches_after_reserved"]
    ):
        raise RuntimeError("V2.42.95 neutral effect accounting drifted")


def run_probe(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    if (root / RESULT).exists() or (root / RESULT).is_symlink():
        raise FileExistsError(root / RESULT)
    provider = protocol["provider"]
    raw = AzureNativeSearchClient(
        provider["proxy_url"],
        provider["model"],
        reasoning_effort=provider["reasoning_effort"],
        service_tier=provider["service_tier"],
        timeout=provider["timeout_seconds"],
        max_retries=provider["max_retries"],
        max_workers=1,
        batch_size=provider["search_batch_size"],
        search_context_size=provider["search_context_size"],
        max_output_tokens=7_000,
        fetch_pages=False,
        fetch_workers=provider["fetch_workers"],
        fetch_timeout=provider["fetch_timeout_seconds"],
        max_page_chars=5_000,
    )
    search = FirstEightFetchOutcomeMask(raw)
    started = time.monotonic()
    lease = protocol["lease"]
    with acquire_deepwide_api_lease(root, owner=lease["owner"], purpose=lease["purpose"], path=root / lease["path"]):
        retrieval = run_staged_reserve(
            NEUTRAL_QUERIES,
            search=search,
            required_column_count=14,
            reserve_policy=StagedReservePolicy(),
        )
    value = project(
        retrieval,
        search_counters=_counters(search),
        injection=search,
        wall_seconds=max(0.0, time.monotonic() - started),
    )
    publish(root / RESULT, value)
    return value


def _checks(result: Mapping[str, Any], gates: Mapping[str, Any]) -> dict[str, bool]:
    injection = result["fault_injection"]
    controller = result["controller"]
    coverage = result["coverage"]
    health = result["runtime_health"]
    return {
        "wall_seconds": float(result["wall_seconds"]) <= float(gates["maximum_wall_seconds"]),
        "controller_decision": controller["decision"] == gates["required_controller_decision"],
        "reserved_reason": coverage["reserved_reason"] == gates["required_reserved_reason"],
        "low_coverage_before_reserved": coverage["low_coverage_before_reserved"] is gates["required_low_coverage_before_reserved"],
        "fetches_before_reserved": coverage["fetches_before_reserved"] == gates["required_fetches_before_reserved"],
        "reserved_fetches": coverage["reserved_fetches"] == gates["required_reserved_fetches"],
        "selected_tail_count": coverage["selected_tail_count"] == gates["required_selected_tail_count"],
        "reserved_usable_pages": coverage["reserved_usable_pages"] >= gates["minimum_reserved_usable_pages"],
        "reserved_novel_pages": coverage["reserved_novel_pages"] >= gates["minimum_reserved_novel_pages"],
        "usable_pages_strictly_increased": coverage["usable_pages_after_reserved"] > coverage["usable_pages_before_reserved"],
        "content_chars_strictly_increased": coverage["content_chars_after_reserved"] > coverage["content_chars_before_reserved"],
        "total_queries": coverage["queries_executed"] <= gates["maximum_total_queries"],
        "total_fetches": coverage["fetches_after_reserved"] <= gates["maximum_total_fetches"],
        "no_added_hosted_search_request": controller["hosted_search_requests_added_by_reserved"] <= gates["maximum_added_hosted_search_requests"],
        "provider_search_calls_unchanged": health["provider_search_calls_unchanged_during_reserved"] is gates["provider_search_calls_unchanged_during_reserved"],
        "provider_fetch_calls_match_receipt": health["provider_fetch_calls_match_receipt"] is True,
        "real_fetch_requests_masked": injection["real_fetch_requests_masked"] == gates["required_real_fetch_requests_masked"],
        "real_reserved_fetch_requests_unmasked": injection["real_reserved_fetch_requests_unmasked"] == gates["required_real_reserved_fetch_requests_unmasked"],
    }


def build_decision(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    result = _read(root, RESULT)
    validate_projection(result)
    checks = _checks(result, protocol["gates"])
    failed = sorted(name for name, passed in checks.items() if not passed)
    passed = not failed
    value = {
        "artifact_version": 1,
        "role": "v24295_neutral_staged_reserve_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "neutral_mechanism_go" if passed else "neutral_mechanism_no_go",
        "passed": passed,
        "checks": checks,
        "failed_checks": failed,
        "observed": {
            "wall_seconds": result["wall_seconds"],
            "controller_decision": result["controller"]["decision"],
            "reserved_reason": result["coverage"]["reserved_reason"],
            "fetches_before_reserved": result["coverage"]["fetches_before_reserved"],
            "reserved_fetches": result["coverage"]["reserved_fetches"],
            "reserved_usable_pages": result["coverage"]["reserved_usable_pages"],
            "fetches_after_reserved": result["coverage"]["fetches_after_reserved"],
            "usable_pages_before_reserved": result["coverage"]["usable_pages_before_reserved"],
            "usable_pages_after_reserved": result["coverage"]["usable_pages_after_reserved"],
            "content_chars_before_reserved": result["coverage"]["content_chars_before_reserved"],
            "content_chars_after_reserved": result["coverage"]["content_chars_after_reserved"],
            "hosted_search_requests_added_by_reserved": result["controller"]["hosted_search_requests_added_by_reserved"],
        },
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "result_sha256": sha256(root / RESULT),
            "surface_manifest_sha256": protocol["surface_manifest_sha256"],
        },
        "claim_scope": {
            "fault_injected_mechanism_robustness": True,
            "natural_trigger_frequency_measured": False,
            "benchmark_quality_measured": False,
            "causal_quality_improvement_proven": False,
            "sota_supported": False,
        },
        "authorization": {
            "successor_dev64_design": passed,
            "successor_dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
            "training_credit_assignment": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["decision_payload_sha256"] = payload_sha256(value)
    validate_decision(value)
    return value


def validate_decision(value: Mapping[str, Any]) -> None:
    checks = value.get("checks")
    failed = value.get("failed_checks")
    claim = value.get("claim_scope")
    auth = value.get("authorization")
    if (
        value.get("role") != "v24295_neutral_staged_reserve_decision"
        or value.get("protocol_id") != PROTOCOL_ID
        or not _sealed(value, "decision_payload_sha256")
        or not isinstance(checks, Mapping)
        or not isinstance(failed, list)
        or value.get("passed") is not all(checks.values())
        or failed != sorted(name for name, passed in checks.items() if not passed)
        or value.get("status") != ("neutral_mechanism_go" if value["passed"] else "neutral_mechanism_no_go")
        or not isinstance(claim, Mapping)
        or claim.get("fault_injected_mechanism_robustness") is not True
        or any(value_ for key, value_ in claim.items() if key != "fault_injected_mechanism_robustness")
        or not isinstance(auth, Mapping)
        or auth.get("successor_dev64_design") is not value["passed"]
        or any(value_ for key, value_ in auth.items() if key != "successor_dev64_design")
    ):
        raise RuntimeError("V2.42.95 decision drifted")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("preregister", "probe", "finalize"))
    args = parser.parse_args()
    if args.action == "preregister":
        value = build_protocol()
        path = PROTOCOL
    elif args.action == "probe":
        value = run_probe()
        print(json.dumps({"path": str(RESULT), "wall_seconds": value["wall_seconds"]}, sort_keys=True))
        return
    else:
        value = build_decision()
        path = DECISION
    publish(ROOT / path, value)
    print(json.dumps({"path": str(path), "role": value["role"]}, sort_keys=True))


if __name__ == "__main__":
    main()
