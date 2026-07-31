"""Search-environment attestation for one future fresh all-220 run.

The environment around an agent is part of the experiment.  A provider model,
tool schema, result limit, page-fetch policy, or adapter implementation can
change measured quality without any controller improvement.  This module
builds a credential-free fingerprint over those variables and binds it to the
existing capacity-fixed, no-resume all-220 plan.

The module is deliberately label-blind and non-executing.  It reads only
frozen configuration metadata and adapter bytes.  It never opens a benchmark
manifest or selected-ID file, calls a provider, reads credentials, or grants
benchmark launch authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit


EXPECTED_SHARDS = ("test_s01", "test_s02", "test_s03", "devval")
EXPECTED_COUNTS = {
    "test_s01": 52,
    "test_s02": 52,
    "test_s03": 52,
    "devval": 64,
}
SHA256 = re.compile(r"[0-9a-f]{64}")
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/ -]{0,511}")
SAFE_ENDPOINT = re.compile(r"https?://[A-Za-z0-9.:-]+(?:/[A-Za-z0-9._~/-]*)?")
SECRET_LITERAL = re.compile(
    r"(?:ghp_|github_pat_|tvly" r"-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
OPAQUE_ID = re.compile(r"task_[0-9a-f]{24}")

FORBIDDEN_METADATA_KEYS = frozenset(
    {
        "answer",
        "answer_key",
        "answers",
        "api_key",
        "api_keys",
        "category",
        "credential",
        "credentials",
        "evidence",
        "evaluator",
        "gold",
        "ground_truth",
        "instance_id",
        "label",
        "labels",
        "mapping",
        "opaque_id",
        "prediction",
        "predictions",
        "question",
        "questions",
        "question_type",
        "result",
        "results",
        "reward",
        "score",
        "scores",
        "secret",
        "secrets",
        "split",
        "subset",
        "task_category",
        "task_id",
        "token",
        "url",
        "urls",
    }
)

ANTHROPIC_QUERY_POLICY = (
    "one Messages request per logical query; web_search is forced; "
    "no cross-query evidence mapping"
)
ANTHROPIC_CITATION_POLICY = (
    "server tool results and URL citations are query-local leads and cannot "
    "satisfy page-evidence gates"
)
ANTHROPIC_CREDENTIAL_POLICY = (
    "ANTHROPIC_API_KEY is environment-only and may only be sent to the fixed "
    "Anthropic Messages endpoint"
)
AZURE_CITATION_POLICY = (
    "query-local URL citation only; citation text is a lead and cannot satisfy "
    "page-evidence gates"
)
AZURE_PAGE_POLICY = (
    "public HTTP(S) only; redirect revalidation; HTML/PDF direct extraction"
)

PROVIDER_SPECS: dict[str, dict[str, Any]] = {
    "anthropic": {
        "search_keys": frozenset(
            {
                "provider",
                "model",
                "timeout_seconds",
                "max_retries",
                "results_per_query",
                "max_uses",
                "max_output_tokens",
                "fetch_pages",
                "fetch_workers",
                "fetch_timeout",
                "workers",
                "query_policy",
                "citation_policy",
                "credential_policy",
            }
        ),
        "adapter_paths": (
            "src/deepwide_agent/clients.py",
            "src/deepwide_agent/native_search.py",
            "src/deepwide_agent/anthropic_search.py",
        ),
        "provider_identity": "anthropic-server-web-search",
        "endpoint": "https://api.anthropic.com/v1/messages",
        "tool_schema": "web_search_20250305",
        "query_isolation": "one_logical_query_per_request",
        "observation_mapping": "query_local_server_results_and_url_citations",
        "page_evidence_rule": "independently_fetched_public_pages_only",
    },
    "azure-native": {
        "search_keys": frozenset(
            {
                "provider",
                "context_size",
                "results_per_query",
                "batch_size",
                "max_output_tokens",
                "fetch_pages",
                "fetch_workers",
                "fetch_timeout",
                "workers",
                "citation_policy",
                "page_policy",
            }
        ),
        "adapter_paths": (
            "src/deepwide_agent/clients.py",
            "src/deepwide_agent/native_search.py",
        ),
        "provider_identity": "azure-responses-web-search",
        "endpoint_from_model": True,
        "tool_schema": "responses_web_search",
        "query_isolation": "explicit_query_markers_with_query_local_citations",
        "observation_mapping": "query_marker_and_citation_span_mapping",
        "page_evidence_rule": "independently_fetched_public_pages_only",
    },
    "tavily": {
        "search_keys": frozenset(
            {
                "provider",
                "depth",
                "results_per_query",
                "include_raw_content",
                "workers",
            }
        ),
        "adapter_paths": ("src/deepwide_agent/clients.py",),
        "provider_identity": "tavily-search-api",
        "endpoint": "https://api.tavily.com/search",
        "tool_schema": "tavily_search_v1",
        "query_isolation": "one_logical_query_per_http_request",
        "observation_mapping": "provider_result_list_per_query",
        "page_evidence_rule": "provider_content_and_raw_content",
    },
}

ENVIRONMENT_BOUNDARY_PATHS = (
    "src/deepwide_agent/runtime.py",
    "scripts/run_deepwide_agent.py",
    "scripts/launch_frozen_deepwide.py",
)

CONTRACT_FIELDS = frozenset(
    {
        "artifact_version",
        "role",
        "label_blind",
        "provider",
        "corpus",
        "query_contract",
        "observation_contract",
        "search_config",
        "search_config_sha256",
        "environment_code_sha256",
        "environment_code_manifest_sha256",
        "credential_values_read_persisted_hashed_or_emitted",
        "benchmark_question_answer_evidence_prediction_result_or_url_read",
        "environment_fingerprint_sha256",
    }
)

ATTESTATION_FIELDS = frozenset(
    {
        "artifact_version",
        "role",
        "label_blind",
        "shard_order",
        "shards",
        "selected_total",
        "search_environment",
        "one_environment_across_all_shards",
        "provider_index_snapshot_pinned",
        "environment_revalidation_before_executor_activation_required",
        "credential_values_read_persisted_hashed_or_emitted",
        "benchmark_manifest_selected_ids_question_answer_evidence_prediction_result_or_url_read",
        "network_model_search_fetch_evaluator_or_api_called",
        "benchmark_forward_or_full220_launch_allowed",
        "leaderboard_submission_or_sota_claim",
        "attestation_payload_sha256",
    }
)

ATTESTED_SHARD_FIELDS = frozenset(
    {
        "freeze",
        "selected_count",
        "selected_ids_sha256",
        "pipeline_version",
        "state_schema_version",
        "environment_fingerprint_sha256",
    }
)

PLAN_FIELDS = frozenset(
    {
        "artifact_version",
        "role",
        "label_blind",
        "candidate_bundle",
        "capacity_freeze",
        "target_name",
        "pipeline_version",
        "state_schema_version",
        "candidate_method_contract_sha256",
        "opaque_partition_sha256",
        "shards",
        "schedule",
        "selected_total",
        "new_output_roots_required",
        "resume_or_selective_rerun_allowed",
        "forward_failure_scored_as_zero",
        "search_capacity_preflight_required",
        "full220_launch_allowed",
        "separate_identity_bound_executor_activation_required",
        "single_parent_shared_lease_owner_required",
        "leaderboard_submission_or_sota_claim",
        "plan_payload_sha256",
    }
)

PLAN_SHARD_FIELDS = frozenset(
    {"freeze", "selected_ids", "output_directory"}
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _without(value: dict[str, Any], key: str) -> dict[str, Any]:
    return {name: item for name, item in value.items() if name != key}


def _reject_forbidden_metadata(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).casefold() in FORBIDDEN_METADATA_KEYS:
                raise RuntimeError("V2.42.09 evaluator-only or credential key appeared")
            _reject_forbidden_metadata(item)
    elif isinstance(value, list):
        for item in value:
            _reject_forbidden_metadata(item)
    elif isinstance(value, str):
        if SECRET_LITERAL.search(value) or OPAQUE_ID.search(value):
            raise RuntimeError("V2.42.09 secret or opaque task ID appeared")


def _positive_int(value: object, label: str, *, maximum: int = 1_000_000) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
        or value > maximum
    ):
        raise RuntimeError(f"V2.42.09 {label} must be a bounded positive integer")
    return value


def _safe_string(value: object, label: str) -> str:
    if not isinstance(value, str) or SAFE_NAME.fullmatch(value) is None:
        raise RuntimeError(f"V2.42.09 {label} is invalid")
    return value


def _validated_native_endpoint(value: object) -> str:
    if not isinstance(value, str) or SAFE_ENDPOINT.fullmatch(value) is None:
        raise RuntimeError("V2.42.09 native search endpoint is invalid")
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as exc:
        raise RuntimeError("V2.42.09 native search endpoint port is invalid") from exc
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost"}
        or port is None
        or not 1 <= port <= 65535
        or parsed.path != "/responses"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError("V2.42.09 native search endpoint is not a local responses service")
    return value


def _bytes_snapshot(path: Path) -> tuple[bytes, str]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise RuntimeError("V2.42.09 snapshot source is not a regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    )
    payload = b"".join(chunks)
    if before_identity != after_identity or len(payload) != before.st_size:
        raise RuntimeError("V2.42.09 source changed during byte snapshot")
    return payload, hashlib.sha256(payload).hexdigest()


def _ordinary(root: Path, relative: object, *, prefix: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise RuntimeError("V2.42.09 path is noncanonical")
    raw = Path(relative)
    if not raw.parts or raw.parts[0] != prefix or ".." in raw.parts:
        raise RuntimeError("V2.42.09 path escapes its declared prefix")
    path = root / raw
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError("V2.42.09 expected an ordinary workspace file")
    return path


def _validated_reference(value: object, *, prefix: str, label: str) -> dict[str, str]:
    if (
        not isinstance(value, dict)
        or set(value) != {"path", "sha256"}
        or not isinstance(value.get("path"), str)
        or Path(value["path"]).is_absolute()
        or ".." in Path(value["path"]).parts
        or not Path(value["path"]).parts
        or Path(value["path"]).parts[0] != prefix
        or SHA256.fullmatch(str(value.get("sha256", ""))) is None
    ):
        raise RuntimeError(f"V2.42.09 {label} reference is invalid")
    return {"path": value["path"], "sha256": value["sha256"]}


def _object_snapshot(path: Path) -> tuple[dict[str, Any], str]:
    payload, digest = _bytes_snapshot(path)
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("V2.42.09 source is not UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError("V2.42.09 expected one JSON object")
    return value, digest


def _validated_search_config(search: object) -> tuple[str, dict[str, Any]]:
    if not isinstance(search, dict):
        raise RuntimeError("V2.42.09 search configuration is absent")
    _reject_forbidden_metadata(search)
    provider = search.get("provider")
    if not isinstance(provider, str) or provider not in PROVIDER_SPECS:
        raise RuntimeError("V2.42.09 search provider is unsupported")
    spec = PROVIDER_SPECS[provider]
    if set(search) != spec["search_keys"]:
        raise RuntimeError("V2.42.09 search configuration schema drifted")
    _positive_int(search["results_per_query"], "results_per_query", maximum=100)
    _positive_int(search["workers"], "search workers", maximum=64)

    if provider == "anthropic":
        _safe_string(search["model"], "Anthropic search model")
        for key in (
            "timeout_seconds",
            "max_retries",
            "max_uses",
            "max_output_tokens",
            "fetch_workers",
            "fetch_timeout",
        ):
            _positive_int(search[key], key)
        if search["fetch_pages"] is not True:
            raise RuntimeError("V2.42.09 Anthropic page fetch must remain enabled")
        if (
            search["query_policy"] != ANTHROPIC_QUERY_POLICY
            or search["citation_policy"] != ANTHROPIC_CITATION_POLICY
            or search["credential_policy"] != ANTHROPIC_CREDENTIAL_POLICY
        ):
            raise RuntimeError("V2.42.09 Anthropic declared policy drifted")
    elif provider == "azure-native":
        if search["context_size"] not in {"low", "medium", "high"}:
            raise RuntimeError("V2.42.09 native context size is invalid")
        for key in (
            "batch_size",
            "max_output_tokens",
            "fetch_workers",
            "fetch_timeout",
        ):
            _positive_int(search[key], key)
        if search["fetch_pages"] is not True:
            raise RuntimeError("V2.42.09 native page fetch must remain enabled")
        if (
            search["citation_policy"] != AZURE_CITATION_POLICY
            or search["page_policy"] != AZURE_PAGE_POLICY
        ):
            raise RuntimeError("V2.42.09 native declared policy drifted")
    else:
        if search["depth"] not in {"basic", "advanced"}:
            raise RuntimeError("V2.42.09 Tavily depth is invalid")
        if not isinstance(search["include_raw_content"], bool):
            raise RuntimeError("V2.42.09 Tavily raw-content policy is invalid")
    return provider, json.loads(json.dumps(search, sort_keys=True))


def build_search_environment_contract(freeze: Mapping[str, Any]) -> dict[str, Any]:
    """Build one deterministic, credential-free search environment contract."""

    provider, search = _validated_search_config(freeze.get("search"))
    spec = PROVIDER_SPECS[provider]
    code = freeze.get("code_sha256")
    if not isinstance(code, dict):
        raise RuntimeError("V2.42.09 code manifest is absent")
    environment_paths = tuple(
        sorted(set(spec["adapter_paths"]) | set(ENVIRONMENT_BOUNDARY_PATHS))
    )
    environment_code: dict[str, str] = {}
    for relative in environment_paths:
        digest = code.get(relative)
        if not isinstance(digest, str) or SHA256.fullmatch(digest) is None:
            raise RuntimeError("V2.42.09 environment code closure is incomplete")
        environment_code[relative] = digest

    if spec.get("endpoint_from_model"):
        model = freeze.get("model")
        endpoint = model.get("proxy_url") if isinstance(model, dict) else None
        endpoint = _validated_native_endpoint(endpoint)
    else:
        endpoint = spec["endpoint"]

    provider_value: dict[str, Any] = {
        "declared_name": provider,
        "runtime_identity": spec["provider_identity"],
        "endpoint": endpoint,
        "tool_schema": spec["tool_schema"],
    }
    if "model" in search:
        provider_value["search_model"] = search["model"]

    contract: dict[str, Any] = {
        "artifact_version": 1,
        "role": "deepwide_search_environment_contract",
        "label_blind": True,
        "provider": provider_value,
        "corpus": {
            "mode": "live_web",
            "snapshot_pinned": False,
            "index_version_pinned": False,
            "retrieval_cutoff_pinned": False,
            "reproducibility_class": "provider_managed_live_index_not_exactly_replayable",
        },
        "query_contract": {
            "isolation": spec["query_isolation"],
            "results_per_query": search["results_per_query"],
            "workers": search["workers"],
        },
        "observation_contract": {
            "observation_mapping": spec["observation_mapping"],
            "page_evidence_rule": spec["page_evidence_rule"],
            "fetch_pages": bool(search.get("fetch_pages", False)),
            "content_truncation_is_adapter_code_bound": True,
            "submission_rule": "one_terminal_task_prediction_or_conservative_zero",
        },
        "search_config": search,
        "search_config_sha256": payload_sha256(search),
        "environment_code_sha256": environment_code,
        "environment_code_manifest_sha256": payload_sha256(environment_code),
        "credential_values_read_persisted_hashed_or_emitted": False,
        "benchmark_question_answer_evidence_prediction_result_or_url_read": False,
    }
    _reject_forbidden_metadata(
        {
            key: item
            for key, item in contract.items()
            if key
            not in {
                "credential_values_read_persisted_hashed_or_emitted",
                "benchmark_question_answer_evidence_prediction_result_or_url_read",
            }
        }
    )
    contract["environment_fingerprint_sha256"] = payload_sha256(contract)
    validate_search_environment_contract(contract)
    return contract


def validate_search_environment_contract(contract: object) -> dict[str, Any]:
    if (
        not isinstance(contract, dict)
        or set(contract) != CONTRACT_FIELDS
        or contract.get("artifact_version") != 1
        or contract.get("role") != "deepwide_search_environment_contract"
        or contract.get("label_blind") is not True
        or contract.get("credential_values_read_persisted_hashed_or_emitted")
        is not False
        or contract.get(
            "benchmark_question_answer_evidence_prediction_result_or_url_read"
        )
        is not False
        or contract.get("environment_fingerprint_sha256")
        != payload_sha256(_without(contract, "environment_fingerprint_sha256"))
    ):
        raise RuntimeError("V2.42.09 search environment contract is invalid")
    provider = contract.get("provider")
    search = contract.get("search_config")
    if not isinstance(provider, dict) or not isinstance(search, dict):
        raise RuntimeError("V2.42.09 search environment payload is invalid")
    declared, normalized = _validated_search_config(search)
    spec = PROVIDER_SPECS[declared]
    endpoint = provider.get("endpoint")
    if spec.get("endpoint_from_model"):
        endpoint = _validated_native_endpoint(endpoint)
    elif endpoint != spec["endpoint"]:
        raise RuntimeError("V2.42.09 fixed provider endpoint drifted")
    expected_provider = {
        "declared_name": declared,
        "runtime_identity": spec["provider_identity"],
        "endpoint": endpoint,
        "tool_schema": spec["tool_schema"],
    }
    if "model" in normalized:
        expected_provider["search_model"] = normalized["model"]
    if provider != expected_provider:
        raise RuntimeError("V2.42.09 provider identity drifted")
    environment_code = contract.get("environment_code_sha256")
    expected_code_paths = set(spec["adapter_paths"]) | set(
        ENVIRONMENT_BOUNDARY_PATHS
    )
    expected_corpus = {
        "mode": "live_web",
        "snapshot_pinned": False,
        "index_version_pinned": False,
        "retrieval_cutoff_pinned": False,
        "reproducibility_class": "provider_managed_live_index_not_exactly_replayable",
    }
    expected_query = {
        "isolation": spec["query_isolation"],
        "results_per_query": normalized["results_per_query"],
        "workers": normalized["workers"],
    }
    expected_observation = {
        "observation_mapping": spec["observation_mapping"],
        "page_evidence_rule": spec["page_evidence_rule"],
        "fetch_pages": bool(normalized.get("fetch_pages", False)),
        "content_truncation_is_adapter_code_bound": True,
        "submission_rule": "one_terminal_task_prediction_or_conservative_zero",
    }
    if (
        not isinstance(environment_code, dict)
        or set(environment_code) != expected_code_paths
        or any(
            not isinstance(digest, str) or SHA256.fullmatch(digest) is None
            for digest in environment_code.values()
        )
        or contract.get("environment_code_manifest_sha256")
        != payload_sha256(environment_code)
        or contract.get("search_config_sha256") != payload_sha256(normalized)
        or contract.get("corpus") != expected_corpus
        or contract.get("query_contract") != expected_query
        or contract.get("observation_contract") != expected_observation
    ):
        raise RuntimeError("V2.42.09 environment fingerprint inputs drifted")
    return contract


def build_all220_environment_attestation(
    root: Path,
    shard_freezes: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    """Attest one environment across four config-only shard freezes."""

    root = root.resolve()
    if set(shard_freezes) != set(EXPECTED_SHARDS):
        raise RuntimeError("V2.42.09 expected the exact four all-220 shards")
    rows: dict[str, Any] = {}
    canonical: dict[str, Any] | None = None
    for tag in EXPECTED_SHARDS:
        reference = shard_freezes[tag]
        if not isinstance(reference, Mapping) or set(reference) != {"path", "sha256"}:
            raise RuntimeError("V2.42.09 freeze reference is invalid")
        relative = reference["path"]
        expected_digest = reference["sha256"]
        if not isinstance(expected_digest, str) or SHA256.fullmatch(expected_digest) is None:
            raise RuntimeError("V2.42.09 freeze digest is invalid")
        path = _ordinary(root, relative, prefix="configs")
        freeze, observed_digest = _object_snapshot(path)
        if observed_digest != expected_digest:
            raise RuntimeError("V2.42.09 freeze bytes drifted")
        _reject_forbidden_metadata(freeze)
        count = freeze.get("selected_count")
        if count != EXPECTED_COUNTS[tag]:
            raise RuntimeError("V2.42.09 shard count drifted")
        selected_ids_sha = freeze.get("selected_ids_sha256")
        if not isinstance(selected_ids_sha, str) or SHA256.fullmatch(selected_ids_sha) is None:
            raise RuntimeError("V2.42.09 opaque partition reference is invalid")
        contract = build_search_environment_contract(freeze)
        for code_relative, code_digest in contract["environment_code_sha256"].items():
            code_path = _ordinary(
                root,
                code_relative,
                prefix=Path(code_relative).parts[0],
            )
            if _bytes_snapshot(code_path)[1] != code_digest:
                raise RuntimeError("V2.42.09 environment source bytes drifted")
        if canonical is None:
            canonical = contract
        elif contract != canonical:
            raise RuntimeError("V2.42.09 shard search environments are not identical")
        pipeline = freeze.get("pipeline_version")
        schema = freeze.get("state_schema_version")
        if not isinstance(pipeline, str) or not pipeline:
            raise RuntimeError("V2.42.09 shard pipeline identity is invalid")
        if isinstance(schema, bool) or not isinstance(schema, int) or schema <= 0:
            raise RuntimeError("V2.42.09 shard schema identity is invalid")
        rows[tag] = {
            "freeze": {"path": relative, "sha256": observed_digest},
            "selected_count": count,
            "selected_ids_sha256": selected_ids_sha,
            "pipeline_version": pipeline,
            "state_schema_version": schema,
            "environment_fingerprint_sha256": contract[
                "environment_fingerprint_sha256"
            ],
        }
    assert canonical is not None
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24209_all220_search_environment_attestation",
        "label_blind": True,
        "shard_order": list(EXPECTED_SHARDS),
        "shards": rows,
        "selected_total": sum(EXPECTED_COUNTS.values()),
        "search_environment": canonical,
        "one_environment_across_all_shards": True,
        "provider_index_snapshot_pinned": False,
        "environment_revalidation_before_executor_activation_required": True,
        "credential_values_read_persisted_hashed_or_emitted": False,
        "benchmark_manifest_selected_ids_question_answer_evidence_prediction_result_or_url_read": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    value["attestation_payload_sha256"] = payload_sha256(value)
    return value


def _validate_attestation(value: object) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value) != ATTESTATION_FIELDS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24209_all220_search_environment_attestation"
        or value.get("label_blind") is not True
        or value.get("selected_total") != 220
        or value.get("shard_order") != list(EXPECTED_SHARDS)
        or value.get("one_environment_across_all_shards") is not True
        or value.get("provider_index_snapshot_pinned") is not False
        or value.get("environment_revalidation_before_executor_activation_required")
        is not True
        or value.get("credential_values_read_persisted_hashed_or_emitted")
        is not False
        or value.get(
            "benchmark_manifest_selected_ids_question_answer_evidence_prediction_result_or_url_read"
        )
        is not False
        or value.get("network_model_search_fetch_evaluator_or_api_called") is not False
        or value.get("benchmark_forward_or_full220_launch_allowed") is not False
        or value.get("leaderboard_submission_or_sota_claim") is not False
        or value.get("attestation_payload_sha256")
        != payload_sha256(_without(value, "attestation_payload_sha256"))
    ):
        raise RuntimeError("V2.42.09 all-220 environment attestation is invalid")
    validate_search_environment_contract(value.get("search_environment"))
    rows = value.get("shards")
    if not isinstance(rows, dict) or set(rows) != set(EXPECTED_SHARDS):
        raise RuntimeError("V2.42.09 attested shard map is invalid")
    fingerprint = value["search_environment"]["environment_fingerprint_sha256"]
    for tag in EXPECTED_SHARDS:
        row = rows[tag]
        if (
            not isinstance(row, dict)
            or set(row) != ATTESTED_SHARD_FIELDS
            or row.get("selected_count") != EXPECTED_COUNTS[tag]
            or row.get("environment_fingerprint_sha256") != fingerprint
            or not isinstance(row.get("pipeline_version"), str)
            or not row.get("pipeline_version")
            or isinstance(row.get("state_schema_version"), bool)
            or not isinstance(row.get("state_schema_version"), int)
            or row.get("state_schema_version", 0) <= 0
            or SHA256.fullmatch(str(row.get("selected_ids_sha256", ""))) is None
            or not isinstance(row.get("freeze"), dict)
            or set(row["freeze"]) != {"path", "sha256"}
        ):
            raise RuntimeError("V2.42.09 attested shard environment drifted")
        _validated_reference(
            row["freeze"], prefix="configs", label=f"{tag} freeze"
        )
    return value


def compile_environment_bound_prelaunch(
    plan: Mapping[str, Any],
    attestation: Mapping[str, Any],
    *,
    plan_path: str,
    plan_sha256: str,
    attestation_path: str,
    attestation_sha256: str,
) -> dict[str, Any]:
    """Bind environment identity to a fixed all-220 plan without launching it."""

    for label, path, digest in (
        ("plan", plan_path, plan_sha256),
        ("attestation", attestation_path, attestation_sha256),
    ):
        if (
            not isinstance(path, str)
            or Path(path).is_absolute()
            or ".." in Path(path).parts
            or not Path(path).parts
            or Path(path).parts[0] != "results"
            or SHA256.fullmatch(digest) is None
        ):
            raise RuntimeError(f"V2.42.09 {label} reference is invalid")
    if (
        set(plan) != PLAN_FIELDS
        or plan.get("artifact_version") != 1
        or plan.get("role")
        != "v24197_capacity_bound_fresh_all220_parallel_plan"
        or plan.get("label_blind") is not True
        or plan.get("plan_payload_sha256")
        != payload_sha256(_without(dict(plan), "plan_payload_sha256"))
        or plan.get("selected_total") != 220
        or plan.get("new_output_roots_required") is not True
        or plan.get("resume_or_selective_rerun_allowed") is not False
        or plan.get("forward_failure_scored_as_zero") is not True
        or plan.get("search_capacity_preflight_required") is not True
        or plan.get("full220_launch_allowed") is not False
        or plan.get("separate_identity_bound_executor_activation_required") is not True
        or plan.get("single_parent_shared_lease_owner_required") is not True
        or plan.get("leaderboard_submission_or_sota_claim") is not False
        or not isinstance(plan.get("target_name"), str)
        or SAFE_NAME.fullmatch(plan.get("target_name", "")) is None
        or SHA256.fullmatch(str(plan.get("candidate_method_contract_sha256", "")))
        is None
        or SHA256.fullmatch(str(plan.get("opaque_partition_sha256", ""))) is None
    ):
        raise RuntimeError("V2.42.09 parallel plan boundary is invalid")
    _validated_reference(
        plan.get("candidate_bundle"), prefix="results", label="candidate bundle"
    )
    _validated_reference(
        plan.get("capacity_freeze"), prefix="results", label="capacity freeze"
    )
    _reject_forbidden_metadata(dict(plan))
    attested = _validate_attestation(dict(attestation))
    plan_rows = plan.get("shards")
    attested_rows = attested["shards"]
    if not isinstance(plan_rows, dict) or set(plan_rows) != set(EXPECTED_SHARDS):
        raise RuntimeError("V2.42.09 parallel plan shard map is invalid")
    pipeline_versions = {
        attested_rows[tag]["pipeline_version"] for tag in EXPECTED_SHARDS
    }
    state_schemas = {
        attested_rows[tag]["state_schema_version"] for tag in EXPECTED_SHARDS
    }
    if (
        len(pipeline_versions) != 1
        or len(state_schemas) != 1
        or plan.get("pipeline_version") != next(iter(pipeline_versions))
        or plan.get("state_schema_version") != next(iter(state_schemas))
    ):
        raise RuntimeError("V2.42.09 plan and environment method identities differ")
    output_directories: set[str] = set()
    for tag in EXPECTED_SHARDS:
        row = plan_rows[tag]
        selected_ids = row.get("selected_ids") if isinstance(row, dict) else None
        output_directory = row.get("output_directory") if isinstance(row, dict) else None
        if (
            not isinstance(row, dict)
            or set(row) != PLAN_SHARD_FIELDS
            or row.get("freeze") != attested_rows[tag]["freeze"]
            or not isinstance(selected_ids, dict)
            or set(selected_ids) != {"path", "sha256", "count"}
            or selected_ids.get("sha256") != attested_rows[tag]["selected_ids_sha256"]
            or selected_ids.get("count") != EXPECTED_COUNTS[tag]
            or not isinstance(selected_ids.get("path"), str)
            or Path(selected_ids["path"]).is_absolute()
            or ".." in Path(selected_ids["path"]).parts
            or not Path(selected_ids["path"]).parts
            or Path(selected_ids["path"]).parts[0] != "configs"
            or not isinstance(output_directory, str)
            or Path(output_directory).is_absolute()
            or ".." in Path(output_directory).parts
            or not Path(output_directory).parts
            or Path(output_directory).parts[0] != "outputs"
            or output_directory in output_directories
        ):
            raise RuntimeError("V2.42.09 plan and environment freeze references differ")
        output_directories.add(output_directory)

    schedule = plan.get("schedule")
    if not isinstance(schedule, dict):
        raise RuntimeError("V2.42.09 fixed schedule is absent")
    width = _positive_int(schedule.get("parallel_shards"), "parallel shard width", maximum=4)
    workers = _positive_int(
        schedule.get("candidate_model_workers_per_shard"),
        "candidate workers",
        maximum=64,
    )
    if (
        schedule.get("row_model_workers_per_shard") != workers
        or schedule.get("fixed_for_entire_all220") is not True
        or schedule.get("worst_case_model_request_concurrency") != width * workers
    ):
        raise RuntimeError("V2.42.09 schedule is not fixed or capacity-bound")
    waves = schedule.get("waves")
    expected_waves = [
        list(EXPECTED_SHARDS[index : index + width])
        for index in range(0, len(EXPECTED_SHARDS), width)
    ]
    if (
        waves != expected_waves
        or _positive_int(
            schedule.get("model_request_concurrency_cap"),
            "model request concurrency cap",
            maximum=256,
        )
        < schedule.get("worst_case_model_request_concurrency")
    ):
        raise RuntimeError("V2.42.09 schedule waves do not cover exact all-220")

    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24209_environment_bound_all220_prelaunch",
        "label_blind": True,
        "parallel_plan": {"path": plan_path, "sha256": plan_sha256},
        "environment_attestation": {
            "path": attestation_path,
            "sha256": attestation_sha256,
        },
        "environment_fingerprint_sha256": attested["search_environment"][
            "environment_fingerprint_sha256"
        ],
        "schedule": json.loads(json.dumps(schedule, sort_keys=True)),
        "selected_total": 220,
        "new_output_roots_required": True,
        "resume_or_selective_rerun_allowed": False,
        "forward_failure_scored_as_zero": True,
        "fixed_concurrency_for_entire_all220": True,
        "provider_health_probe_required": True,
        "environment_revalidation_before_executor_activation_required": True,
        "provider_index_snapshot_pinned": False,
        "environment_shift_must_be_reported_separately_from_method_effect": True,
        "credential_values_read_persisted_hashed_or_emitted": False,
        "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "separate_identity_bound_executor_activation_required": True,
        "leaderboard_submission_or_sota_claim": False,
    }
    value["prelaunch_payload_sha256"] = payload_sha256(value)
    return value
