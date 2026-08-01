#!/usr/bin/env python3
"""Create-exclusive no-network audit for V2.42.45 pinned native fetch."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepwide_agent.v24231_webswarm_guidance_baseline import (  # noqa: E402
    build_guidance_arm,
    build_guidance_policy,
    build_scout_process_trace,
    build_sibling_process_experience,
    build_web_probe_receipt,
)
from deepwide_agent.v24232_webswarm_total_budget import (  # noqa: E402
    build_cost_vector,
    build_shared_total_budget_contract,
    initialize_arm_budget_ledger,
)
from deepwide_agent.v24233_webswarm_effect_preauthorization import (  # noqa: E402
    initialize_effect_preauthorization_state,
    validate_effect_preauthorization_state,
)
from deepwide_agent.v24234_provider_cost_meter import (  # noqa: E402
    build_provider_meter_contract,
)
from deepwide_agent.v24235_preauthorized_effect_harness import (  # noqa: E402
    PreauthorizedEffectHarness,
)
from deepwide_agent.v24238_native_http_fetch_single_attempt import (  # noqa: E402
    NativeHttpFetchAttemptValue,
    NativeHttpFetchRequest,
)
from deepwide_agent.v24245_pinned_native_http_fetch import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    ALL_RESOLVED_ADDRESSES_MUST_BE_PUBLIC,
    ARBITRARY_CALLER_HEADERS_ACCEPTED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CALLER_PUBLIC_NONSECRET_URL_REQUIRED,
    CANDIDATE_SINGLE_ATTEMPT_NETWORK_CALL_CAPABILITY,
    DETERMINISTIC_ATTEMPT_INDEX_ADDRESS_SELECTION_IMPLEMENTED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    DNS_PREFLIGHT_RESULT_PINNED_TO_TRANSPORT,
    ENVIRONMENT_OR_KEYRING_CREDENTIAL_READ_IMPLEMENTED,
    FRESH_POOL_PER_CALLBACK_IMPLEMENTED,
    FULL_PROVIDER_RESPONSE_HASHED_WHEN_TRUNCATED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    NOMINAL_TIMEOUT_RESERVATION_CHECKED,
    ONE_URLOPEN_PER_CALLBACK_IMPLEMENTED,
    ORIGINAL_HOST_HEADER_IMPLEMENTED,
    POOL_CLOSE_ATTEMPTED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED,
    PROVIDER_CHALLENGE_HEADER_SENT,
    PROVIDER_RESPONSE_AUTHENTICITY_INDEPENDENTLY_VERIFIED,
    PUBLIC_ADDRESS_DNS_PREFLIGHT_IMPLEMENTED,
    REDIRECT_FOLLOWING_IMPLEMENTED,
    REQUESTS_OR_ENVIRONMENT_PROXY_USED,
    REQUEST_URL_DIRECTLY_PERSISTED_OR_EMITTED,
    RESPONSE_AND_POOL_CLOSE_SUCCESS_INDEPENDENTLY_VERIFIED,
    RESPONSE_CLOSE_ATTEMPTED,
    RESPONSE_RELEASE_ATTEMPTED,
    RETAINED_RESPONSE_BYTE_CAP_IMPLEMENTED,
    SENSITIVE_QUERY_KEY_REJECTION_IMPLEMENTED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    SINGLE_SOCKET_CONNECTION_ATTEMPT_INDEPENDENTLY_ATTESTED,
    SYSTEM_RESOLVER_USED_BY_DEFAULT,
    TLS_ORIGINAL_HOSTNAME_CERTIFICATE_ASSERTION_IMPLEMENTED,
    TLS_ORIGINAL_HOSTNAME_SNI_IMPLEMENTED,
    TOTAL_TRANSPORT_RESPONSE_BYTES_HARD_CAPPED,
    URL_SECRET_ABSENCE_INDEPENDENTLY_VERIFIED,
    URLLIB3_INTERNAL_RETRY_DISABLED,
    URLLIB3_TIMEOUT_IS_TOTAL_WALL_DEADLINE,
    PinnedNativeHttpFetchAdapter,
)


ROLE = "v24245_pinned_native_http_fetch_candidate_audit"
OUTPUT = Path("results/v24245_pinned_native_http_fetch_candidate_audit_v1_20260801.json")

SEQUENTIAL_PARENT_RECEIPT = Path(
    "results/v24244_strict_json_parser_boundary_candidate_audit_v1_20260801.json"
)
SEQUENTIAL_PARENT_RECEIPT_SHA256 = (
    "c33f9f464c9e87d68112068a593c077e0841b2836c1487c43831a240f5bebba1"
)
SEQUENTIAL_PARENT_PAYLOAD_SHA256 = (
    "60424e494f502a29856b99e87496e47bd5adbaab82307e824fa485f9fc97373c"
)
SEQUENTIAL_PARENT_MANIFEST_SHA256 = (
    "ead4137f4a3069b8dd6efdef71fb133645ea6efdfe6b0d55e54fec2aed8fd322"
)
SEQUENTIAL_PARENT_CONTROL_FILES = (
    Path("src/deepwide_agent/v24244_strict_json_parser_boundary.py"),
    Path("tests/test_v24244_strict_json_parser_boundary.py"),
    Path("scripts/audit_v24244_strict_json_parser_boundary.py"),
    Path("tests/test_audit_v24244_strict_json_parser_boundary.py"),
)

DEPENDENCY_RECEIPT = Path(
    "results/v24238_native_http_fetch_single_attempt_candidate_audit_v1_20260801.json"
)
DEPENDENCY_RECEIPT_SHA256 = (
    "93b9752d4a0161944a6a6080c514ea684501b396f35c72e4f3a4e76c7c916b36"
)
DEPENDENCY_PAYLOAD_SHA256 = (
    "89e249bec8c76a66883dadb0931aa1f969808629ebb8b82a120d7596ed5fafde"
)
DEPENDENCY_MANIFEST_SHA256 = (
    "d343b2f5bbd67c52afb107829af852ae504566fb4271d64ca7296450fc3a0eb7"
)
DEPENDENCY_CONTROL_FILES = (
    Path("src/deepwide_agent/v24238_native_http_fetch_single_attempt.py"),
    Path("tests/test_v24238_native_http_fetch_single_attempt.py"),
    Path("scripts/audit_v24238_native_http_fetch_single_attempt.py"),
    Path("tests/test_audit_v24238_native_http_fetch_single_attempt.py"),
)

MODULE = Path("src/deepwide_agent/v24245_pinned_native_http_fetch.py")
MODULE_TEST = Path("tests/test_v24245_pinned_native_http_fetch.py")
AUDIT = Path("scripts/audit_v24245_pinned_native_http_fetch.py")
AUDIT_TEST = Path("tests/test_audit_v24245_pinned_native_http_fetch.py")
CONTROL_FILES = (MODULE, MODULE_TEST, AUDIT, AUDIT_TEST)
ACTIVE_FORWARD_GUARDS = (
    Path("src/deepwide_agent/__init__.py"),
    Path("src/deepwide_agent/clients.py"),
    Path("src/deepwide_agent/native_search.py"),
    Path("src/deepwide_agent/anthropic_search.py"),
    Path("src/deepwide_agent/runtime.py"),
    Path("src/deepwide_agent/v24211_entropy_runtime.py"),
    Path("scripts/run_deepwide_agent.py"),
    Path("scripts/launch_frozen_deepwide.py"),
)

ALLOWED_IMPORT_MODULES = frozenset(
    {
        "__future__",
        "hashlib",
        "ipaddress",
        "ssl",
        "typing",
        "urllib.parse",
        "urllib3",
        "deepwide_agent.v24235_preauthorized_effect_harness",
        "deepwide_agent.v24238_native_http_fetch_single_attempt",
    }
)
REQUIRED_PUBLIC_SYMBOLS = frozenset(
    {
        "PinnedNativeHttpFetchError",
        "PinnedNativeHttpFetchAdapter",
        "_canonical_public_addresses",
        "_select_pinned_address",
        "_default_pool_factory",
        "_bounded_pool_stream",
        "bind",
        "single_attempt",
    }
)
FORBIDDEN_CALL_NAMES = frozenset(
    {"__import__", "compile", "eval", "exec", "getattr", "open", "setattr"}
)
FORBIDDEN_METADATA_ACCESS_KEYS = frozenset(
    {
        "answer_key",
        "benchmark_category",
        "benchmark_label",
        "benchmark_subset",
        "category",
        "correctness",
        "evaluator_payload",
        "evaluator_score",
        "gold",
        "ground_truth",
        "mapping",
        "prediction",
        "question_type",
        "results.csv",
        "reward",
        "score",
        "split",
        "task_category",
        "task_id",
    }
)
SECRET_LITERAL = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-(?:dev-)?|sk-)[A-Za-z0-9_-]{16,}"
)
OPAQUE_ID = re.compile(r"task_[0-9a-f]{24}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def ordinary(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.42.45 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.42.45 expected ordinary repository file: {relative}")
    return path


def _literal_key(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.casefold()
    return None


def audit_python_source(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    imports: set[str] = set()
    symbols: set[str] = set()
    forbidden_calls: list[str] = []
    privileged_reads: list[str] = []
    environment_reads = 0
    file_or_process_calls = 0
    pool_urlopen_calls = 0
    resolver_calls = 0
    redirect_true_calls = 0
    retries_enabled_calls = 0
    pool_constructors = 0
    original_host_literals = 0
    server_hostname_keywords = 0
    assert_hostname_keywords = 0
    cert_required_keywords = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.add(node.name)
        elif isinstance(node, ast.Dict):
            for key, item in zip(node.keys, node.values):
                if (
                    _literal_key(key) == "host"
                    and isinstance(item, ast.Call)
                    and isinstance(item.func, ast.Name)
                    and item.func.id == "_host_header"
                ):
                    original_host_literals += 1
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALL_NAMES:
                forbidden_calls.append(node.func.id)
            if isinstance(node.func, ast.Name) and node.func.id == "_validate_public_resolution":
                resolver_calls += 1
            if isinstance(node.func, ast.Name) and node.func.id == "urlopen":
                pool_urlopen_calls += 1
            for keyword in node.keywords:
                if keyword.arg == "redirect" and not (
                    isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is False
                ):
                    redirect_true_calls += 1
                if keyword.arg == "retries" and not (
                    isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is False
                ):
                    retries_enabled_calls += 1
            if isinstance(node.func, ast.Attribute):
                attribute = node.func.attr
                if attribute == "get" and node.args:
                    key = _literal_key(node.args[0])
                    if key in FORBIDDEN_METADATA_ACCESS_KEYS:
                        privileged_reads.append(str(key))
                if attribute in {
                    "getenv",
                    "get_keyring",
                    "read_bytes",
                    "read_text",
                    "write_bytes",
                    "write_text",
                    "popen",
                    "run",
                    "system",
                }:
                    if attribute in {"getenv", "get_keyring"}:
                        environment_reads += 1
                    else:
                        file_or_process_calls += 1
                if attribute == "urlopen":
                    pool_urlopen_calls += 1
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "urllib3"
                    and attribute in {"HTTPConnectionPool", "HTTPSConnectionPool"}
                ):
                    pool_constructors += 1
                for keyword in node.keywords:
                    if keyword.arg == "server_hostname":
                        server_hostname_keywords += 1
                    if keyword.arg == "assert_hostname":
                        assert_hostname_keywords += 1
                    if keyword.arg == "cert_reqs":
                        cert_required_keywords += 1
        elif isinstance(node, ast.Subscript):
            key = _literal_key(node.slice)
            if key in FORBIDDEN_METADATA_ACCESS_KEYS:
                privileged_reads.append(str(key))
    disallowed_imports = sorted(imports - ALLOWED_IMPORT_MODULES)
    missing = sorted(REQUIRED_PUBLIC_SYMBOLS - symbols)
    if (
        disallowed_imports
        or forbidden_calls
        or privileged_reads
        or environment_reads
        or file_or_process_calls
        or missing
        or pool_urlopen_calls != 1
        or resolver_calls != 1
        or redirect_true_calls
        or retries_enabled_calls
        or pool_constructors != 2
        or original_host_literals != 1
        or server_hostname_keywords != 1
        or assert_hostname_keywords != 1
        or cert_required_keywords != 1
    ):
        raise RuntimeError(
            "V2.42.45 capability boundary failed: "
            f"imports={disallowed_imports}, calls={forbidden_calls}, "
            f"privileged={privileged_reads}, environment={environment_reads}, "
            f"file_or_process={file_or_process_calls}, missing={missing}, "
            f"urlopen={pool_urlopen_calls}, resolver={resolver_calls}, "
            f"redirect={redirect_true_calls}, retries={retries_enabled_calls}, "
            f"pools={pool_constructors}, host={original_host_literals}, "
            f"sni={server_hostname_keywords}, assert={assert_hostname_keywords}, "
            f"cert={cert_required_keywords}"
        )
    return {
        "ast_node_count": sum(1 for _ in ast.walk(tree)),
        "import_modules": sorted(imports),
        "required_public_symbols_present": sorted(REQUIRED_PUBLIC_SYMBOLS),
        "single_pool_urlopen_call_site_count": pool_urlopen_calls,
        "public_resolution_validation_call_site_count": resolver_calls,
        "urllib3_pool_constructor_count": pool_constructors,
        "original_host_header_literal_count": original_host_literals,
        "tls_server_hostname_keyword_count": server_hostname_keywords,
        "tls_assert_hostname_keyword_count": assert_hostname_keywords,
        "tls_cert_required_keyword_count": cert_required_keywords,
        "redirect_or_retry_enable_call_count": 0,
        "file_environment_keyring_process_subprocess_or_dynamic_code_capability": False,
        "privileged_metadata_read_count": 0,
    }


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _signal(kind: str, tactic: str, label: str) -> dict[str, str]:
    return {"kind": kind, "tactic": tactic, "value_sha256": _digest(label)}


def _parent() -> tuple[dict[str, Any], dict[str, Any]]:
    budget = build_shared_total_budget_contract(
        model_calls=100,
        model_attempts=120,
        search_calls=100,
        fetch_calls=200,
        other_tool_calls=100,
        orchestrator_calls=100,
        input_tokens=100_000,
        output_tokens=20_000,
        wall_milliseconds=1_000_000,
    )
    policy = build_guidance_policy(
        selection_protocol_sha256=_digest("selection"),
        model_contract_sha256=_digest("model"),
        search_fetch_contract_sha256=_digest("search-fetch"),
        total_budget_contract_sha256=budget["contract_sha256"],
        root_scope_projection_protocol_sha256=_digest("root-projection"),
        process_signal_vocabulary_sha256=_digest("process-vocabulary"),
    )
    probe = build_web_probe_receipt(
        policy=policy,
        root_scope_projection_sha256=_digest("root"),
        parent_node_ref_sha256=_digest("parent"),
        probe_run_ref_sha256=_digest("probe"),
        topology="distributed",
        probe_search_calls=3,
        probe_fetch_calls=2,
        probe_model_calls=1,
        probe_input_tokens=100,
        probe_output_tokens=20,
        probe_wall_seconds=4.0004,
    )
    scouts = [
        build_scout_process_trace(
            policy=policy,
            root_scope_projection_sha256=_digest("root"),
            parent_node_ref_sha256=_digest("parent"),
            homogeneous_group_ref_sha256=_digest("group"),
            scout_slot=slot,
            sibling_node_ref_sha256=_digest(f"sibling-{slot}"),
            sibling_mode_sha256=_digest("mode"),
            process_signals=[
                _signal(
                    "effective_query_pattern",
                    "combine_visible_entity_and_attribute_terms",
                    f"query-{slot}",
                )
            ],
            model_calls=1,
            search_calls=1,
            fetch_calls=1,
            input_tokens=10,
            output_tokens=5,
            wall_seconds=1.0,
            scout_terminal_status="completed",
        )
        for slot in (1, 2)
    ]
    experience = build_sibling_process_experience(
        policy=policy,
        scouts=scouts,
        experience_extractor_ref_sha256=_digest("extractor"),
        process_signals=[
            _signal("workflow_hint", "verify_with_independent_source", "workflow")
        ],
        extractor_model_calls=1,
        extractor_input_tokens=300,
        extractor_output_tokens=30,
        extractor_wall_seconds=2.0002,
    )
    arm = build_guidance_arm(
        policy=policy,
        arm_name="full",
        arm_ref_sha256=_digest("arm-full"),
        root_scope_projection_sha256=_digest("root"),
        parent_node_ref_sha256=_digest("parent"),
        homogeneous_group_ref_sha256=_digest("group"),
        sibling_count=8,
        scouts=scouts,
        probe=probe,
        experience=experience,
    )
    ledger = initialize_arm_budget_ledger(
        contract=budget,
        guidance_policy=policy,
        arm=arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
        charge_ref_sha256=_digest("overhead"),
        method_overhead_model_attempts=arm["probe_extractor_cost"]["model_calls"],
        method_overhead_other_tool_calls=0,
        method_overhead_orchestrator_calls=1,
    )
    state_shared = {
        "contract": budget,
        "guidance_policy": policy,
        "guidance_arm": arm,
        "scouts": scouts,
        "probe": probe,
        "experience": experience,
    }
    state = initialize_effect_preauthorization_state(
        initial_budget_ledger=ledger,
        **state_shared,
    )
    harness_shared = {
        "guidance_contract": budget,
        "guidance_policy": policy,
        "guidance_arm": arm,
        "scouts": scouts,
        "probe": probe,
        "experience": experience,
    }
    return state, {"state_shared": state_shared, "harness_shared": harness_shared}


class _Response:
    def __init__(self, status: int, chunks: list[bytes]) -> None:
        self.status = status
        self.chunks = list(chunks)
        self.headers = {"Content-Type": "text/plain"}
        self.closed = False
        self.released = False

    def stream(self, *, amt: int, decode_content: bool):
        if amt != 1025 or decode_content is not True:
            raise RuntimeError("synthetic stream contract drifted")
        yield from self.chunks

    def close(self) -> None:
        self.closed = True

    def release_conn(self) -> None:
        self.released = True


class _Pool:
    def __init__(self, response: _Response) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []
        self.closed = False

    def urlopen(self, method: str, target: str, **kwargs: Any) -> _Response:
        self.calls.append({"method": method, "target": target, **kwargs})
        return self.response

    def close(self) -> None:
        self.closed = True


class _Factory:
    def __init__(self, responses: list[_Response]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []
        self.pools: list[_Pool] = []

    def __call__(self, **kwargs: Any) -> _Pool:
        self.calls.append(dict(kwargs))
        if not self.responses:
            raise RuntimeError("unexpected extra synthetic pool")
        pool = _Pool(self.responses.pop(0))
        self.pools.append(pool)
        return pool


class _Resolve:
    def __init__(self, actions: list[tuple[str, ...]]) -> None:
        self.actions = list(actions)
        self.calls: list[tuple[str, int]] = []

    def __call__(self, hostname: str, port: int) -> tuple[str, ...]:
        self.calls.append((hostname, port))
        if not self.actions:
            raise RuntimeError("unexpected extra synthetic DNS resolution")
        return self.actions.pop(0)


def replay_fake_pinned_transport() -> dict[str, Any]:
    state, parent = _parent()
    harness = PreauthorizedEffectHarness(state, **parent["harness_shared"])
    meter = build_provider_meter_contract(
        provider_kind="native_http_fetch",
        charge_kind="fanout_execution",
        max_attempts=2,
        reserved_cost=build_cost_vector(
            model_calls=0,
            model_attempts=0,
            search_calls=0,
            fetch_calls=2,
            other_tool_calls=0,
            orchestrator_calls=0,
            input_tokens=0,
            output_tokens=0,
            wall_milliseconds=90_000,
        ),
    )
    first = _Response(500, [b"synthetic private server error"])
    second = _Response(200, [b"synthetic private fetched page"])
    resolver = _Resolve(
        [
            ("2606:2800:220:1:248:1893:25c8:1946", "93.184.216.35", "93.184.216.34"),
            ("93.184.216.34", "93.184.216.35", "2606:2800:220:1:248:1893:25c8:1946"),
        ]
    )
    factory = _Factory([first, second])
    adapter = PinnedNativeHttpFetchAdapter(
        timeout_seconds=45,
        max_response_bytes=1024,
        resolve=resolver,
        pool_factory=factory,
    )
    result = harness.run_effect(
        meter_contract=meter,
        invocation_ref_sha256=_digest("invocation"),
        permit_ref_sha256=_digest("permit"),
        charge_ref_sha256=_digest("charge"),
        callback=adapter.bind(
            NativeHttpFetchRequest(
                "https://example.test/public?q=visible#fragment"
            ),
            meter_contract=meter,
        ),
    )
    final = harness.snapshot_state()
    validate_effect_preauthorization_state(final, **parent["state_shared"])
    if (
        result.receipt["attempt_count"] != 2
        or len(resolver.calls) != 2
        or len(factory.calls) != 2
        or any(len(pool.calls) != 1 for pool in factory.pools)
    ):
        raise RuntimeError("V2.42.45 one-callback-one-pinned-pool replay drifted")
    if not isinstance(result.value, NativeHttpFetchAttemptValue):
        raise RuntimeError("V2.42.45 success value type drifted")
    encoded_receipt = json.dumps(result.receipt, ensure_ascii=False)
    private_literals = (
        "example.test",
        "synthetic private server error",
        "synthetic private fetched page",
    )
    if any(item in encoded_receipt for item in private_literals):
        raise RuntimeError("V2.42.45 private value leaked into receipt")
    pool_calls = [pool.calls[0] for pool in factory.pools]
    return {
        "fake_resolver_pool_and_response_only": True,
        "network_socket_or_real_fetch_called": False,
        "callback_attempt_count": result.receipt["attempt_count"],
        "resolver_call_count": len(resolver.calls),
        "fresh_pool_count": len(factory.pools),
        "pool_urlopen_count": sum(len(pool.calls) for pool in factory.pools),
        "one_callback_invocation_equals_one_fresh_pool_and_one_urlopen": True,
        "pinned_address_sequence": [
            call["pinned_address"] for call in factory.calls
        ],
        "attempt_index_address_rotation_is_canonical_and_deterministic": [
            call["pinned_address"] for call in factory.calls
        ]
        == ["93.184.216.34", "93.184.216.35"],
        "original_host_header_preserved": all(
            call["headers"]["Host"] == "example.test" for call in pool_calls
        ),
        "origin_form_target_preserved": all(
            call["target"] == "/public?q=visible" for call in pool_calls
        ),
        "redirect_following_and_internal_retries_disabled": all(
            call["redirect"] is False and call["retries"] is False
            for call in pool_calls
        ),
        "streaming_without_preload_enabled": all(
            call["preload_content"] is False
            and call["release_conn"] is False
            for call in pool_calls
        ),
        "responses_close_and_release_attempted": first.closed
        and first.released
        and second.closed
        and second.released,
        "fresh_pools_closed": all(pool.closed for pool in factory.pools),
        "raw_url_or_response_not_in_receipt": True,
        "settled_permit_count": final["settled_permit_count"],
        "pending_permit_count": len(final["pending_permit_refs"]),
        "benchmark_question_prediction_mapping_gold_evaluator_or_score_read": False,
    }


def _validate_receipt_and_manifest(
    *,
    root: Path,
    receipt: Path,
    expected_file_sha256: str,
    expected_payload_sha256: str,
    expected_manifest_sha256: str,
    control_files: tuple[Path, ...],
    role: str,
    manifest_label: str,
) -> tuple[dict[str, Any], dict[str, str]]:
    receipt_path = ordinary(root, receipt)
    if sha256(receipt_path) != expected_file_sha256:
        raise RuntimeError(f"V2.42.45 {manifest_label} receipt bytes drifted")
    value = json.loads(receipt_path.read_text(encoding="utf-8"))
    unsigned = dict(value)
    payload = unsigned.pop("audit_payload_sha256", None)
    if (
        value.get("role") != role
        or value.get("audit_valid") is not True
        or payload != expected_payload_sha256
        or payload_sha256(unsigned) != expected_payload_sha256
        or value.get("control_surface", {}).get("manifest_sha256")
        != expected_manifest_sha256
    ):
        raise RuntimeError(f"V2.42.45 {manifest_label} receipt semantics drifted")
    paths = {str(path): ordinary(root, path) for path in control_files}
    manifest = {name: sha256(path) for name, path in paths.items()}
    if manifest != value["control_surface"]["manifest"]:
        raise RuntimeError(f"V2.42.45 {manifest_label} control files drifted")
    if payload_sha256(manifest) != expected_manifest_sha256:
        raise RuntimeError(f"V2.42.45 {manifest_label} manifest seal drifted")
    return value, manifest


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.45 audit may only use canonical workspace")
    paths = {str(path): ordinary(root, path) for path in CONTROL_FILES}
    _, sequential_manifest = _validate_receipt_and_manifest(
        root=root,
        receipt=SEQUENTIAL_PARENT_RECEIPT,
        expected_file_sha256=SEQUENTIAL_PARENT_RECEIPT_SHA256,
        expected_payload_sha256=SEQUENTIAL_PARENT_PAYLOAD_SHA256,
        expected_manifest_sha256=SEQUENTIAL_PARENT_MANIFEST_SHA256,
        control_files=SEQUENTIAL_PARENT_CONTROL_FILES,
        role="v24244_strict_json_parser_boundary_candidate_audit",
        manifest_label="sequential parent",
    )
    dependency_value, dependency_manifest = _validate_receipt_and_manifest(
        root=root,
        receipt=DEPENDENCY_RECEIPT,
        expected_file_sha256=DEPENDENCY_RECEIPT_SHA256,
        expected_payload_sha256=DEPENDENCY_PAYLOAD_SHA256,
        expected_manifest_sha256=DEPENDENCY_MANIFEST_SHA256,
        control_files=DEPENDENCY_CONTROL_FILES,
        role="v24238_native_http_fetch_single_attempt_candidate_audit",
        manifest_label="native-fetch dependency",
    )
    if (
        dependency_value.get("candidate_runtime_adapter") is not True
        or dependency_value.get("scientific_scope", {}).get(
            "dns_preflight_result_pinned_to_transport"
        )
        is not False
    ):
        raise RuntimeError("V2.42.45 dependency boundary semantics drifted")

    sources = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    literal_hits = {
        name: bool(SECRET_LITERAL.search(source) or OPAQUE_ID.search(source))
        for name, source in sources.items()
    }
    if any(literal_hits.values()):
        raise RuntimeError("V2.42.45 control source contains forbidden content")
    static = audit_python_source(sources[str(MODULE)])
    guards = {str(path): ordinary(root, path) for path in ACTIVE_FORWARD_GUARDS}
    module_name = "v24245_pinned_native_http_fetch"
    guard_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in guards.items()
    }
    if any(guard_hits.values()):
        raise RuntimeError("V2.42.45 appears in an active forward guard")
    control_manifest = {name: sha256(path) for name, path in paths.items()}
    guard_manifest = {name: sha256(path) for name, path in guards.items()}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time())
        if created_at_unix is None
        else int(created_at_unix),
        "label_blind_runtime": True,
        "candidate_runtime_adapter": True,
        "sequential_parent_receipt": {
            "path": str(SEQUENTIAL_PARENT_RECEIPT),
            "file_sha256": SEQUENTIAL_PARENT_RECEIPT_SHA256,
            "payload_sha256": SEQUENTIAL_PARENT_PAYLOAD_SHA256,
            "v24244_control_manifest_sha256": SEQUENTIAL_PARENT_MANIFEST_SHA256,
            "v24244_control_files_rehashed": len(sequential_manifest),
            "v24244_candidate_parent_validated": True,
        },
        "native_fetch_dependency_receipt": {
            "path": str(DEPENDENCY_RECEIPT),
            "file_sha256": DEPENDENCY_RECEIPT_SHA256,
            "payload_sha256": DEPENDENCY_PAYLOAD_SHA256,
            "v24238_control_manifest_sha256": DEPENDENCY_MANIFEST_SHA256,
            "v24238_control_files_rehashed": len(dependency_manifest),
            "v24238_candidate_dependency_validated": True,
            "v24238_unpinned_gap_confirmed": True,
        },
        "control_surface": {
            "file_count": len(control_manifest),
            "manifest": control_manifest,
            "manifest_sha256": payload_sha256(control_manifest),
        },
        "active_forward_guard": {
            "file_count": len(guard_manifest),
            "manifest": guard_manifest,
            "manifest_sha256": payload_sha256(guard_manifest),
            "module_name_hit_count_by_file": guard_hits,
            "module_absent_from_guarded_clients_and_forward_entrypoints": True,
        },
        "static_capability_audit": static,
        "control_source_forbidden_literal_scan": {
            "file_count": len(literal_hits),
            "hit_count": 0,
            "credential_or_concrete_opaque_id_literal_present": False,
        },
        "fake_pinned_transport_replay": replay_fake_pinned_transport(),
        "scientific_scope": {
            "public_address_dns_preflight_implemented": PUBLIC_ADDRESS_DNS_PREFLIGHT_IMPLEMENTED,
            "all_resolved_addresses_must_be_public": ALL_RESOLVED_ADDRESSES_MUST_BE_PUBLIC,
            "dns_preflight_result_pinned_to_transport": DNS_PREFLIGHT_RESULT_PINNED_TO_TRANSPORT,
            "deterministic_attempt_index_address_selection_implemented": DETERMINISTIC_ATTEMPT_INDEX_ADDRESS_SELECTION_IMPLEMENTED,
            "original_host_header_implemented": ORIGINAL_HOST_HEADER_IMPLEMENTED,
            "tls_original_hostname_sni_implemented": TLS_ORIGINAL_HOSTNAME_SNI_IMPLEMENTED,
            "tls_original_hostname_certificate_assertion_implemented": TLS_ORIGINAL_HOSTNAME_CERTIFICATE_ASSERTION_IMPLEMENTED,
            "urllib3_internal_retry_disabled": URLLIB3_INTERNAL_RETRY_DISABLED,
            "redirect_following_implemented": REDIRECT_FOLLOWING_IMPLEMENTED,
            "fresh_pool_per_callback_implemented": FRESH_POOL_PER_CALLBACK_IMPLEMENTED,
            "one_urlopen_per_callback_implemented": ONE_URLOPEN_PER_CALLBACK_IMPLEMENTED,
            "system_resolver_used_by_default": SYSTEM_RESOLVER_USED_BY_DEFAULT,
            "retained_response_byte_cap_implemented": RETAINED_RESPONSE_BYTE_CAP_IMPLEMENTED,
            "total_transport_response_bytes_hard_capped": TOTAL_TRANSPORT_RESPONSE_BYTES_HARD_CAPPED,
            "full_provider_response_hashed_when_truncated": FULL_PROVIDER_RESPONSE_HASHED_WHEN_TRUNCATED,
            "response_close_attempted": RESPONSE_CLOSE_ATTEMPTED,
            "response_release_attempted": RESPONSE_RELEASE_ATTEMPTED,
            "pool_close_attempted": POOL_CLOSE_ATTEMPTED,
            "response_and_pool_close_success_independently_verified": RESPONSE_AND_POOL_CLOSE_SUCCESS_INDEPENDENTLY_VERIFIED,
            "single_socket_connection_attempt_independently_attested": SINGLE_SOCKET_CONNECTION_ATTEMPT_INDEPENDENTLY_ATTESTED,
            "provider_response_authenticity_independently_verified": PROVIDER_RESPONSE_AUTHENTICITY_INDEPENDENTLY_VERIFIED,
            "requests_or_environment_proxy_used": REQUESTS_OR_ENVIRONMENT_PROXY_USED,
            "arbitrary_caller_headers_accepted": ARBITRARY_CALLER_HEADERS_ACCEPTED,
            "environment_or_keyring_credential_read_implemented": ENVIRONMENT_OR_KEYRING_CREDENTIAL_READ_IMPLEMENTED,
            "request_url_directly_persisted_or_emitted": REQUEST_URL_DIRECTLY_PERSISTED_OR_EMITTED,
            "caller_public_nonsecret_url_required": CALLER_PUBLIC_NONSECRET_URL_REQUIRED,
            "url_secret_absence_independently_verified": URL_SECRET_ABSENCE_INDEPENDENTLY_VERIFIED,
            "sensitive_query_key_rejection_implemented": SENSITIVE_QUERY_KEY_REJECTION_IMPLEMENTED,
            "challenge_and_attempt_reference_headers_sent": PROVIDER_CHALLENGE_HEADER_SENT,
            "provider_challenge_consumption_independently_verified": PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED,
            "nominal_timeout_reservation_checked": NOMINAL_TIMEOUT_RESERVATION_CHECKED,
            "urllib3_timeout_is_total_wall_deadline": URLLIB3_TIMEOUT_IS_TOTAL_WALL_DEADLINE,
            "dns_rebinding_between_validated_resolution_and_socket_target_excluded_by_construction": True,
            "upstream_dns_or_bgp_routing_compromise_excluded": False,
            "real_provider_traffic_observed": False,
            "active_client_or_runner_integrated": False,
            "dev64_gate_evaluated": False,
            "fresh_exact220_evaluated": False,
            "quality_cost_or_benchmark_effect_observed": False,
        },
        "source_policy": {
            "repository_control_code_parent_and_dependency_receipts_fake_resolver_pool_and_response_only": True,
            "runtime_task_question_query_raw_evidence_url_prediction_or_answer_read": False,
            "benchmark_subset_category_question_type_label_split_or_mapping_read": False,
            "gold_evaluator_payload_score_reward_or_results_read": False,
            "credential_environment_keyring_or_secret_value_read": False,
            "audit_network_socket_model_search_fetch_subprocess_or_api_called": False,
        },
        "authorization": {
            "candidate_single_attempt_network_call_capability": CANDIDATE_SINGLE_ATTEMPT_NETWORK_CALL_CAPABILITY,
            "active_provider_traffic_authorized": ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
            "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
            "active_forward_integration_authorized": ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
            "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
            "dev64_or_exact220_launch_authorized": DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
            "shared_api_lease_acquire_authorized": SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
            "process_signal_restart_resume_rerun_or_selective_retry": False,
            "leaderboard_submission_or_sota_claim": LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
        },
        "claims": {
            "candidate_dns_to_transport_pinned_native_fetch_available": True,
            "production_runtime_wrapper_available": False,
            "single_socket_connection_attempt_attested": False,
            "real_provider_execution_evidence_available": False,
            "benchmark_score_available": False,
            "benchmark_improvement_observed": False,
            "leaderboard_submission_performed": False,
            "sota": False,
        },
        "audit_valid": True,
    }
    encoded = json.dumps(value, ensure_ascii=False)
    if SECRET_LITERAL.search(encoded) or OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.45 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.45 audit output path is noncanonical")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        parent_descriptor = os.open(
            target.parent,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )
        try:
            os.fsync(parent_descriptor)
        finally:
            os.close(parent_descriptor)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    target = target if target.is_absolute() else ROOT / target
    value = build_audit()
    publish_new(target, value)
    print(
        json.dumps(
            {
                "path": str(target),
                "sha256": sha256(target),
                "audit_valid": value["audit_valid"],
                "candidate_runtime_adapter": value["candidate_runtime_adapter"],
            }
        )
    )


if __name__ == "__main__":
    main()
