#!/usr/bin/env python3
"""Create-exclusive no-network audit for V2.42.40 Anthropic search."""

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
from deepwide_agent.v24240_anthropic_server_search_single_attempt import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    ARBITRARY_CALLER_HEADERS_ACCEPTED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CACHE_TOKENS_INCLUDED_IN_METERED_INPUT,
    CALLER_SUPPLIED_CREDENTIAL_REQUIRED,
    CANDIDATE_SINGLE_ATTEMPT_NETWORK_CALL_CAPABILITY,
    CREDENTIAL_DURABLY_PERSISTED_HASHED_OR_EMITTED,
    CREDENTIAL_EXCLUDED_FROM_REQUEST_BODY,
    CREDENTIAL_RETAINED_IN_ADAPTER_MEMORY,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    DIRECT_CREDENTIAL_ECHO_REJECTED_BEFORE_RESPONSE_HASH,
    ENVIRONMENT_OR_KEYRING_CREDENTIAL_READ_IMPLEMENTED,
    EXACT_HTTPS_ENDPOINT_ENFORCED,
    INPUT_TOKEN_RESERVATION_COVERAGE_PRE_EFFECT_PROVEN,
    INTERNAL_RETRY_IMPLEMENTED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    NOMINAL_TIMEOUT_OUTPUT_AND_TOOL_RESERVATION_CHECKED,
    OBSERVED_PROVIDER_TOOL_ACTIONS_METERED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    PROVIDER_ACTION_COUNTER_CROSS_CHECKED,
    PROVIDER_ACTION_COUNTER_MISMATCH_FAILS_CLOSED,
    PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED,
    PROVIDER_CHALLENGE_HEADER_SENT,
    PROVIDER_DECLARED_MAX_USES_SENT,
    PROVIDER_DECLARED_MAX_USES_VIOLATION_REJECTED_POST_EFFECT,
    PROVIDER_RESPONSE_AUTHENTICITY_INDEPENDENTLY_VERIFIED,
    PROVIDER_TOOL_ACTION_HARD_LIMIT_ENFORCED_PRE_EFFECT,
    PROVIDER_TOOL_ACTION_IS_PAGE_EVIDENCE,
    REDIRECT_FOLLOWING_IMPLEMENTED,
    REQUESTS_TIMEOUT_IS_TOTAL_WALL_DEADLINE,
    REQUESTS_TRUST_ENV_DISABLED,
    RESPONSE_BODY_STREAM_CAP_IMPLEMENTED,
    RESPONSE_CLOSE_ATTEMPTED,
    RESPONSE_CLOSE_SUCCESS_INDEPENDENTLY_VERIFIED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    TLS_VERIFICATION_DISABLED,
    AnthropicServerSearchAttemptValue,
    AnthropicServerSearchRequest,
    AnthropicServerSearchSingleAttemptAdapter,
)


ROLE = "v24240_anthropic_server_search_single_attempt_candidate_audit"
OUTPUT = Path(
    "results/v24240_anthropic_server_search_single_attempt_candidate_audit_v1_20260801.json"
)
PARENT_RECEIPT = Path(
    "results/v24239_azure_hosted_search_single_attempt_candidate_audit_v1_20260801.json"
)
PARENT_RECEIPT_SHA256 = (
    "8d1022e6f2570668f6ad46d5c87e21bc2e0524319a910613adff063c51587de7"
)
PARENT_PAYLOAD_SHA256 = (
    "22483f5e0f847eee50b8fa2093ec5cba46eb5b9a84af0b85bbaa55358b5681b8"
)
PARENT_MANIFEST_SHA256 = (
    "ca3badf75a01e47dc6d598fd592389f06ca27eaaac9e6a47d9002b546cc4f4b5"
)
PARENT_CONTROL_FILES = (
    Path("src/deepwide_agent/v24239_azure_hosted_search_single_attempt.py"),
    Path("tests/test_v24239_azure_hosted_search_single_attempt.py"),
    Path("scripts/audit_v24239_azure_hosted_search_single_attempt.py"),
    Path("tests/test_audit_v24239_azure_hosted_search_single_attempt.py"),
)
MODULE = Path("src/deepwide_agent/v24240_anthropic_server_search_single_attempt.py")
MODULE_TEST = Path("tests/test_v24240_anthropic_server_search_single_attempt.py")
AUDIT = Path("scripts/audit_v24240_anthropic_server_search_single_attempt.py")
AUDIT_TEST = Path("tests/test_audit_v24240_anthropic_server_search_single_attempt.py")
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
        "dataclasses",
        "hashlib",
        "json",
        "typing",
        "urllib.parse",
        "requests",
        "deepwide_agent.v24232_webswarm_total_budget",
        "deepwide_agent.v24234_provider_cost_meter",
        "deepwide_agent.v24235_preauthorized_effect_harness",
    }
)
REQUIRED_PUBLIC_SYMBOLS = frozenset(
    {
        "AnthropicServerSearchActionValue",
        "AnthropicServerSearchAttemptValue",
        "AnthropicServerSearchCitationValue",
        "AnthropicServerSearchRequest",
        "AnthropicServerSearchResultValue",
        "AnthropicServerSearchSingleAttemptAdapter",
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
        raise RuntimeError("V2.42.40 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.42.40 expected ordinary repository file: {relative}")
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
    post_calls = 0
    environment_reads = 0
    file_or_process_calls = 0
    redirect_follow_calls = 0
    tls_disable_calls = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.add(node.name)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALL_NAMES:
                forbidden_calls.append(node.func.id)
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == "get" and node.args:
                    key = _literal_key(node.args[0])
                    if key in FORBIDDEN_METADATA_ACCESS_KEYS:
                        privileged_reads.append(str(key))
                if node.func.attr in {
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
                    if node.func.attr in {"getenv", "get_keyring"}:
                        environment_reads += 1
                    else:
                        file_or_process_calls += 1
                if node.func.attr == "_post":
                    post_calls += 1
                    for keyword in node.keywords:
                        if (
                            keyword.arg == "allow_redirects"
                            and isinstance(keyword.value, ast.Constant)
                            and keyword.value.value is True
                        ):
                            redirect_follow_calls += 1
                        if (
                            keyword.arg == "verify"
                            and isinstance(keyword.value, ast.Constant)
                            and keyword.value.value is False
                        ):
                            tls_disable_calls += 1
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
        or redirect_follow_calls
        or tls_disable_calls
        or missing
        or post_calls != 1
    ):
        raise RuntimeError(
            "V2.42.40 capability boundary failed: "
            f"imports={disallowed_imports}, calls={forbidden_calls}, "
            f"privileged={privileged_reads}, environment={environment_reads}, "
            f"file_or_process={file_or_process_calls}, "
            f"redirect_follow={redirect_follow_calls}, tls_disable={tls_disable_calls}, "
            f"missing={missing}, post_calls={post_calls}"
        )
    return {
        "ast_node_count": sum(1 for _ in ast.walk(tree)),
        "import_modules": sorted(imports),
        "required_public_symbols_present": sorted(REQUIRED_PUBLIC_SYMBOLS),
        "single_transport_post_call_site_count": post_calls,
        "network_post_capability": True,
        "redirect_following_call_count": 0,
        "tls_verification_disable_call_count": 0,
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
    def __init__(self, status: int, content: bytes) -> None:
        self.status_code = status
        self.content = content
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _Post:
    def __init__(self, actions: list[Any]) -> None:
        self.actions = list(actions)
        self.calls: list[dict[str, Any]] = []

    def __call__(self, endpoint: str, **kwargs: Any) -> Any:
        self.calls.append({"endpoint": endpoint, **kwargs})
        if not self.actions:
            raise RuntimeError("unexpected extra synthetic POST")
        action = self.actions.pop(0)
        if isinstance(action, BaseException):
            raise action
        return action


def _success_payload() -> bytes:
    return json.dumps(
        {
            "id": "synthetic-anthropic-message",
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 20,
                "cache_creation_input_tokens": 10,
                "cache_read_input_tokens": 5,
                "server_tool_use": {"web_search_requests": 1},
            },
            "content": [
                {
                    "type": "server_tool_use",
                    "id": "synthetic-call-1",
                    "name": "web_search",
                    "input": {"query": "synthetic private provider query"},
                },
                {
                    "type": "web_search_tool_result",
                    "tool_use_id": "synthetic-call-1",
                    "content": [
                        {
                            "type": "web_search_result",
                            "url": "https://example.test/source#fragment",
                            "title": "synthetic private title",
                            "page_age": "2026-08-01",
                            "encrypted_content": "must-not-be-retained",
                        }
                    ],
                },
                {
                    "type": "text",
                    "text": "synthetic private answer",
                    "citations": [
                        {
                            "type": "web_search_result_location",
                            "url": "https://example.test/source#fragment",
                            "title": "synthetic private citation",
                            "cited_text": "synthetic private cited lead",
                            "encrypted_index": "must-not-be-retained",
                        }
                    ],
                },
            ],
        },
        sort_keys=True,
    ).encode("utf-8")


def replay_fake_transport() -> dict[str, Any]:
    state, parent = _parent()
    harness = PreauthorizedEffectHarness(state, **parent["harness_shared"])
    meter = build_provider_meter_contract(
        provider_kind="anthropic_server_web_search",
        charge_kind="fanout_execution",
        max_attempts=2,
        reserved_cost=build_cost_vector(
            model_calls=0,
            model_attempts=0,
            search_calls=2,
            fetch_calls=0,
            other_tool_calls=4,
            orchestrator_calls=0,
            input_tokens=1000,
            output_tokens=400,
            wall_milliseconds=600_000,
        ),
    )
    first = _Response(429, b'{"error":"synthetic rate limit"}')
    second = _Response(200, _success_payload())
    post = _Post([first, second])
    credential = "synthetic-audit-credential-value"
    adapter = AnthropicServerSearchSingleAttemptAdapter(
        endpoint="https://api.anthropic.com/v1/messages",
        model="claude-haiku-4-5-20251001",
        anthropic_version="2023-06-01",
        credential=credential,
        timeout_seconds=300,
        post=post,
    )
    request = AnthropicServerSearchRequest(
        query="synthetic visible query",
        max_output_tokens=200,
        max_uses=2,
    )
    result = harness.run_effect(
        meter_contract=meter,
        invocation_ref_sha256=_digest("invocation"),
        permit_ref_sha256=_digest("permit"),
        charge_ref_sha256=_digest("charge"),
        callback=adapter.bind(request, meter_contract=meter),
    )
    final = harness.snapshot_state()
    validate_effect_preauthorization_state(final, **parent["state_shared"])
    if len(post.calls) != 2 or result.receipt["attempt_count"] != 2:
        raise RuntimeError("V2.42.40 one-callback-one-POST replay drifted")
    if not isinstance(result.value, AnthropicServerSearchAttemptValue):
        raise RuntimeError("V2.42.40 success value type drifted")
    encoded_receipt = json.dumps(result.receipt, ensure_ascii=False)
    for private in (
        credential,
        request.query,
        result.value.text,
        result.value.actions[0].query,
        result.value.results[0].url,
    ):
        if private in encoded_receipt:
            raise RuntimeError("V2.42.40 private value leaked into receipt")
    attempts = result.receipt["measurement"]["attempts"]
    return {
        "fake_transport_only": True,
        "network_socket_or_real_provider_called": False,
        "callback_attempt_count": result.receipt["attempt_count"],
        "transport_post_count": len(post.calls),
        "one_callback_invocation_equals_one_transport_post": True,
        "first_status_retryable_429": attempts[0]["outcome"] == "retryable_http",
        "second_status_success_200": attempts[1]["outcome"] == "success",
        "retry_usage_unavailable_and_reserved": (
            attempts[0]["token_usage_state"] == "unavailable"
            and attempts[0]["provider_tool_usage_state"] == "unavailable"
        ),
        "success_token_usage_observed_with_cache": (
            attempts[1]["token_usage_state"] == "observed"
            and attempts[1]["input_tokens"] == 115
            and result.value.usage["cache_creation_input_tokens"] == 10
            and result.value.usage["cache_read_input_tokens"] == 5
        ),
        "success_provider_tool_usage_observed_and_cross_checked": (
            attempts[1]["provider_tool_usage_state"] == "observed"
            and attempts[1]["provider_tool_calls"] == 1
            and result.value.usage["web_search_requests"] == len(result.value.actions)
        ),
        "same_execution_challenge_across_retries": (
            post.calls[0]["headers"]["X-DeepWide-Execution-Challenge"]
            == post.calls[1]["headers"]["X-DeepWide-Execution-Challenge"]
        ),
        "distinct_attempt_reference_across_retries": (
            post.calls[0]["headers"]["X-DeepWide-Attempt-Ref"]
            != post.calls[1]["headers"]["X-DeepWide-Attempt-Ref"]
        ),
        "credential_header_only_and_same_across_retries": (
            post.calls[0]["headers"]["x-api-key"] == credential
            and post.calls[1]["headers"]["x-api-key"] == credential
            and credential.encode("ascii") not in post.calls[0]["data"]
            and credential.encode("ascii") not in post.calls[1]["data"]
        ),
        "redirect_following_disabled_and_tls_enabled": all(
            call["allow_redirects"] is False and call["verify"] is True
            for call in post.calls
        ),
        "raw_query_answer_credential_urls_not_in_receipt": True,
        "responses_closed": first.closed and second.closed,
        "settled_permit_count": final["settled_permit_count"],
        "pending_permit_count": len(final["pending_permit_refs"]),
        "benchmark_question_prediction_mapping_gold_evaluator_or_score_read": False,
    }


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.40 audit may only use canonical workspace")
    paths = {str(path): ordinary(root, path) for path in CONTROL_FILES}
    parent_path = ordinary(root, PARENT_RECEIPT)
    if sha256(parent_path) != PARENT_RECEIPT_SHA256:
        raise RuntimeError("V2.42.40 parent receipt bytes drifted")
    parent_value = json.loads(parent_path.read_text(encoding="utf-8"))
    parent_unsigned = dict(parent_value)
    parent_payload = parent_unsigned.pop("audit_payload_sha256", None)
    if (
        parent_value.get("role")
        != "v24239_azure_hosted_search_single_attempt_candidate_audit"
        or parent_value.get("audit_valid") is not True
        or parent_value.get("candidate_runtime_adapter") is not True
        or parent_payload != PARENT_PAYLOAD_SHA256
        or payload_sha256(parent_unsigned) != PARENT_PAYLOAD_SHA256
        or parent_value.get("control_surface", {}).get("manifest_sha256")
        != PARENT_MANIFEST_SHA256
    ):
        raise RuntimeError("V2.42.40 parent receipt semantics drifted")
    parent_paths = {
        str(path): ordinary(root, path) for path in PARENT_CONTROL_FILES
    }
    parent_manifest = {name: sha256(path) for name, path in parent_paths.items()}
    if parent_manifest != parent_value["control_surface"]["manifest"]:
        raise RuntimeError("V2.42.40 parent control files drifted")
    if payload_sha256(parent_manifest) != PARENT_MANIFEST_SHA256:
        raise RuntimeError("V2.42.40 parent manifest seal drifted")

    sources = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    literal_hits = {
        name: bool(SECRET_LITERAL.search(source) or OPAQUE_ID.search(source))
        for name, source in sources.items()
    }
    if any(literal_hits.values()):
        raise RuntimeError("V2.42.40 control source contains forbidden content")
    static = audit_python_source(sources[str(MODULE)])
    guards = {str(path): ordinary(root, path) for path in ACTIVE_FORWARD_GUARDS}
    module_name = "v24240_anthropic_server_search_single_attempt"
    guard_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in guards.items()
    }
    if any(guard_hits.values()):
        raise RuntimeError("V2.42.40 appears in an active forward guard")
    control_manifest = {name: sha256(path) for name, path in paths.items()}
    guard_manifest = {name: sha256(path) for name, path in guards.items()}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "label_blind_runtime": True,
        "build_only": False,
        "candidate_runtime_adapter": True,
        "parent_receipt": {
            "path": str(PARENT_RECEIPT),
            "file_sha256": PARENT_RECEIPT_SHA256,
            "payload_sha256": PARENT_PAYLOAD_SHA256,
            "v24239_control_manifest_sha256": PARENT_MANIFEST_SHA256,
            "v24239_control_files_rehashed": len(parent_manifest),
            "v24239_candidate_parent_validated": True,
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
        "fake_transport_replay": replay_fake_transport(),
        "scientific_scope": {
            "one_callback_invocation_one_transport_post_by_implementation": True,
            "exact_https_endpoint_enforced": EXACT_HTTPS_ENDPOINT_ENFORCED,
            "internal_retry_implemented": INTERNAL_RETRY_IMPLEMENTED,
            "redirect_following_implemented": REDIRECT_FOLLOWING_IMPLEMENTED,
            "requests_trust_env_disabled": REQUESTS_TRUST_ENV_DISABLED,
            "tls_verification_disabled": TLS_VERIFICATION_DISABLED,
            "arbitrary_caller_headers_accepted": ARBITRARY_CALLER_HEADERS_ACCEPTED,
            "environment_or_keyring_credential_read_implemented": ENVIRONMENT_OR_KEYRING_CREDENTIAL_READ_IMPLEMENTED,
            "caller_supplied_credential_required": CALLER_SUPPLIED_CREDENTIAL_REQUIRED,
            "credential_retained_in_adapter_memory": CREDENTIAL_RETAINED_IN_ADAPTER_MEMORY,
            "credential_durably_persisted_hashed_or_emitted": CREDENTIAL_DURABLY_PERSISTED_HASHED_OR_EMITTED,
            "credential_excluded_from_request_body": CREDENTIAL_EXCLUDED_FROM_REQUEST_BODY,
            "direct_credential_echo_rejected_before_response_hash": DIRECT_CREDENTIAL_ECHO_REJECTED_BEFORE_RESPONSE_HASH,
            "challenge_and_attempt_reference_headers_sent": PROVIDER_CHALLENGE_HEADER_SENT,
            "provider_challenge_consumption_independently_verified": PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED,
            "provider_response_authenticity_independently_verified": PROVIDER_RESPONSE_AUTHENTICITY_INDEPENDENTLY_VERIFIED,
            "provider_declared_max_uses_sent": PROVIDER_DECLARED_MAX_USES_SENT,
            "provider_declared_max_uses_violation_rejected_post_effect": PROVIDER_DECLARED_MAX_USES_VIOLATION_REJECTED_POST_EFFECT,
            "observed_provider_tool_actions_metered": OBSERVED_PROVIDER_TOOL_ACTIONS_METERED,
            "provider_action_counter_cross_checked": PROVIDER_ACTION_COUNTER_CROSS_CHECKED,
            "provider_action_counter_mismatch_fails_closed": PROVIDER_ACTION_COUNTER_MISMATCH_FAILS_CLOSED,
            "provider_tool_action_hard_limit_enforced_pre_effect": PROVIDER_TOOL_ACTION_HARD_LIMIT_ENFORCED_PRE_EFFECT,
            "provider_tool_action_is_page_evidence": PROVIDER_TOOL_ACTION_IS_PAGE_EVIDENCE,
            "cache_tokens_included_in_metered_input": CACHE_TOKENS_INCLUDED_IN_METERED_INPUT,
            "input_token_reservation_coverage_pre_effect_proven": INPUT_TOKEN_RESERVATION_COVERAGE_PRE_EFFECT_PROVEN,
            "response_body_stream_cap_implemented": RESPONSE_BODY_STREAM_CAP_IMPLEMENTED,
            "response_close_attempted": RESPONSE_CLOSE_ATTEMPTED,
            "response_close_success_independently_verified": RESPONSE_CLOSE_SUCCESS_INDEPENDENTLY_VERIFIED,
            "nominal_timeout_output_and_tool_reservation_checked": NOMINAL_TIMEOUT_OUTPUT_AND_TOOL_RESERVATION_CHECKED,
            "requests_timeout_is_total_wall_deadline": REQUESTS_TIMEOUT_IS_TOTAL_WALL_DEADLINE,
            "real_provider_traffic_observed": False,
            "active_client_or_runner_integrated": False,
            "dev64_gate_evaluated": False,
            "fresh_exact220_evaluated": False,
            "quality_cost_or_benchmark_effect_observed": False,
        },
        "source_policy": {
            "repository_control_code_parent_receipt_and_fake_transport_only": True,
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
            "candidate_anthropic_server_search_single_attempt_adapter_available": True,
            "production_runtime_wrapper_available": False,
            "provider_action_budget_enforced_pre_effect": False,
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
        raise RuntimeError("V2.42.40 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.40 audit output path is noncanonical")
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
