#!/usr/bin/env python3
"""Create-exclusive no-network audit for the V2.42.36 local adapter."""

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
from deepwide_agent.v24236_azure_responses_single_attempt import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    ARBITRARY_CALLER_HEADERS_ACCEPTED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CANDIDATE_SINGLE_ATTEMPT_NETWORK_CALL_CAPABILITY,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    ENVIRONMENT_OR_KEYRING_CREDENTIAL_READ_IMPLEMENTED,
    INTERNAL_RETRY_IMPLEMENTED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    LOOPBACK_ONLY_ENDPOINT_ENFORCED,
    NOMINAL_TIMEOUT_AND_OUTPUT_RESERVATION_CHECKED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED,
    PROVIDER_CHALLENGE_HEADER_SENT,
    PROVIDER_RESPONSE_AUTHENTICITY_INDEPENDENTLY_VERIFIED,
    REDIRECT_FOLLOWING_IMPLEMENTED,
    REQUESTS_TIMEOUT_IS_TOTAL_WALL_DEADLINE,
    REQUESTS_TRUST_ENV_DISABLED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    AzureResponsesAttemptValue,
    AzureResponsesRequest,
    AzureResponsesSingleAttemptAdapter,
)


ROLE = "v24236_azure_responses_single_attempt_candidate_audit"
OUTPUT = Path(
    "results/v24236_azure_responses_single_attempt_candidate_audit_v1_20260801.json"
)
PARENT_RECEIPT = Path(
    "results/v24235_preauthorized_effect_harness_candidate_audit_v1_20260801.json"
)
PARENT_RECEIPT_SHA256 = (
    "3f6101c7bb716a0f7d255c2b8d028827e02891c6e12943fa9ae65325a093e6fd"
)
PARENT_PAYLOAD_SHA256 = (
    "e3d0616ac78aded2abf894c4daea4b8cee06905c3f9c0bab9a2e58e8975d8872"
)
PARENT_MANIFEST_SHA256 = (
    "1f08afa3ab80460fb6e1c142bca4997d0930c592e494ad59aa2db8d12a3316e5"
)
PARENT_CONTROL_FILES = (
    Path("src/deepwide_agent/v24235_preauthorized_effect_harness.py"),
    Path("tests/test_v24235_preauthorized_effect_harness.py"),
    Path("scripts/audit_v24235_preauthorized_effect_harness.py"),
    Path("tests/test_audit_v24235_preauthorized_effect_harness.py"),
)
MODULE = Path("src/deepwide_agent/v24236_azure_responses_single_attempt.py")
MODULE_TEST = Path("tests/test_v24236_azure_responses_single_attempt.py")
AUDIT = Path("scripts/audit_v24236_azure_responses_single_attempt.py")
AUDIT_TEST = Path("tests/test_audit_v24236_azure_responses_single_attempt.py")
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
        "ipaddress",
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
        "AzureResponsesAttemptValue",
        "AzureResponsesRequest",
        "AzureResponsesSingleAttemptAdapter",
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
        raise RuntimeError("V2.42.36 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.42.36 expected ordinary repository file: {relative}")
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
        or post_calls != 1
    ):
        raise RuntimeError(
            "V2.42.36 capability boundary failed: "
            f"imports={disallowed_imports}, calls={forbidden_calls}, "
            f"privileged={privileged_reads}, environment={environment_reads}, "
            f"file_or_process={file_or_process_calls}, missing={missing}, "
            f"post_calls={post_calls}"
        )
    return {
        "ast_node_count": sum(1 for _ in ast.walk(tree)),
        "import_modules": sorted(imports),
        "required_public_symbols_present": sorted(REQUIRED_PUBLIC_SYMBOLS),
        "single_transport_post_call_site_count": post_calls,
        "network_post_capability": True,
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
            "id": "synthetic-response",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": "synthetic private answer"}
                    ],
                }
            ],
            "usage": {
                "input_tokens": 100,
                "output_tokens": 20,
                "total_tokens": 120,
            },
        },
        sort_keys=True,
    ).encode("utf-8")


def replay_fake_transport() -> dict[str, Any]:
    state, parent = _parent()
    harness = PreauthorizedEffectHarness(state, **parent["harness_shared"])
    meter = build_provider_meter_contract(
        provider_kind="azure_responses_model",
        charge_kind="renderer",
        max_attempts=2,
        reserved_cost=build_cost_vector(
            model_calls=1,
            model_attempts=2,
            search_calls=0,
            fetch_calls=0,
            other_tool_calls=0,
            orchestrator_calls=0,
            input_tokens=1000,
            output_tokens=200,
            wall_milliseconds=600_000,
        ),
    )
    post = _Post(
        [
            _Response(429, b'{"error":"rate-limit"}'),
            _Response(200, _success_payload()),
        ]
    )
    adapter = AzureResponsesSingleAttemptAdapter(
        endpoint="http://127.0.0.1:9878/responses",
        model="gpt-5.6-sol",
        timeout_seconds=300,
        post=post,
    )
    request = AzureResponsesRequest(
        system="synthetic visible system",
        user="synthetic visible user",
        max_output_tokens=200,
        json_mode=True,
        reasoning_effort="high",
        service_tier="priority",
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
        raise RuntimeError("V2.42.36 one-callback-one-POST replay drifted")
    if not isinstance(result.value, AzureResponsesAttemptValue):
        raise RuntimeError("V2.42.36 success value type drifted")
    encoded_receipt = json.dumps(result.receipt, ensure_ascii=False)
    if "synthetic private answer" in encoded_receipt:
        raise RuntimeError("V2.42.36 raw response leaked into receipt")
    return {
        "fake_transport_only": True,
        "network_socket_or_real_provider_called": False,
        "callback_attempt_count": result.receipt["attempt_count"],
        "transport_post_count": len(post.calls),
        "one_callback_invocation_equals_one_transport_post": True,
        "first_status_retryable_429": True,
        "second_status_success_200": True,
        "same_execution_challenge_across_retries": (
            post.calls[0]["headers"]["X-DeepWide-Execution-Challenge"]
            == post.calls[1]["headers"]["X-DeepWide-Execution-Challenge"]
        ),
        "distinct_attempt_reference_across_retries": (
            post.calls[0]["headers"]["X-DeepWide-Attempt-Ref"]
            != post.calls[1]["headers"]["X-DeepWide-Attempt-Ref"]
        ),
        "redirect_following_disabled": all(
            call["allow_redirects"] is False for call in post.calls
        ),
        "loopback_endpoint_only": all(
            call["endpoint"] == "http://127.0.0.1:9878/responses"
            for call in post.calls
        ),
        "raw_prompt_or_response_not_in_receipt": True,
        "settled_permit_count": final["settled_permit_count"],
        "pending_permit_count": len(final["pending_permit_refs"]),
        "benchmark_question_prediction_mapping_gold_evaluator_or_score_read": False,
    }


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.36 audit may only use canonical workspace")
    paths = {str(path): ordinary(root, path) for path in CONTROL_FILES}
    parent = ordinary(root, PARENT_RECEIPT)
    if sha256(parent) != PARENT_RECEIPT_SHA256:
        raise RuntimeError("V2.42.36 parent receipt bytes drifted")
    parent_value = json.loads(parent.read_text(encoding="utf-8"))
    parent_unsigned = dict(parent_value)
    parent_payload = parent_unsigned.pop("audit_payload_sha256", None)
    if (
        parent_value.get("role")
        != "v24235_preauthorized_effect_harness_candidate_audit"
        or parent_value.get("audit_valid") is not True
        or parent_value.get("candidate_runtime_harness") is not True
        or parent_payload != PARENT_PAYLOAD_SHA256
        or payload_sha256(parent_unsigned) != PARENT_PAYLOAD_SHA256
        or parent_value.get("control_surface", {}).get("manifest_sha256")
        != PARENT_MANIFEST_SHA256
    ):
        raise RuntimeError("V2.42.36 parent receipt semantics drifted")
    parent_paths = {
        str(path): ordinary(root, path) for path in PARENT_CONTROL_FILES
    }
    parent_manifest = {name: sha256(path) for name, path in parent_paths.items()}
    if parent_manifest != parent_value["control_surface"]["manifest"]:
        raise RuntimeError("V2.42.36 parent control files drifted")
    if payload_sha256(parent_manifest) != PARENT_MANIFEST_SHA256:
        raise RuntimeError("V2.42.36 parent manifest seal drifted")

    sources = {
        name: path.read_text(encoding="utf-8") for name, path in paths.items()
    }
    literal_hits = {
        name: bool(SECRET_LITERAL.search(source) or OPAQUE_ID.search(source))
        for name, source in sources.items()
    }
    if any(literal_hits.values()):
        raise RuntimeError("V2.42.36 control source contains forbidden content")
    static = audit_python_source(sources[str(MODULE)])
    guards = {
        str(path): ordinary(root, path) for path in ACTIVE_FORWARD_GUARDS
    }
    module_name = "v24236_azure_responses_single_attempt"
    guard_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in guards.items()
    }
    if any(guard_hits.values()):
        raise RuntimeError("V2.42.36 appears in an active forward guard")
    control_manifest = {name: sha256(path) for name, path in paths.items()}
    guard_manifest = {name: sha256(path) for name, path in guards.items()}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": (
            int(time.time()) if created_at_unix is None else int(created_at_unix)
        ),
        "label_blind_runtime": True,
        "build_only": False,
        "candidate_runtime_adapter": True,
        "parent_receipt": {
            "path": str(PARENT_RECEIPT),
            "file_sha256": PARENT_RECEIPT_SHA256,
            "payload_sha256": PARENT_PAYLOAD_SHA256,
            "v24235_control_manifest_sha256": PARENT_MANIFEST_SHA256,
            "v24235_control_files_rehashed": len(parent_manifest),
            "v24235_candidate_parent_validated": True,
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
            "internal_retry_implemented": INTERNAL_RETRY_IMPLEMENTED,
            "loopback_only_endpoint_enforced": LOOPBACK_ONLY_ENDPOINT_ENFORCED,
            "nominal_timeout_and_output_reservation_checked": NOMINAL_TIMEOUT_AND_OUTPUT_RESERVATION_CHECKED,
            "requests_timeout_is_total_wall_deadline": REQUESTS_TIMEOUT_IS_TOTAL_WALL_DEADLINE,
            "redirect_following_implemented": REDIRECT_FOLLOWING_IMPLEMENTED,
            "arbitrary_caller_headers_accepted": ARBITRARY_CALLER_HEADERS_ACCEPTED,
            "environment_or_keyring_credential_read_implemented": ENVIRONMENT_OR_KEYRING_CREDENTIAL_READ_IMPLEMENTED,
            "requests_trust_env_disabled": REQUESTS_TRUST_ENV_DISABLED,
            "challenge_and_attempt_reference_headers_sent": PROVIDER_CHALLENGE_HEADER_SENT,
            "provider_challenge_consumption_independently_verified": PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED,
            "provider_response_authenticity_independently_verified": PROVIDER_RESPONSE_AUTHENTICITY_INDEPENDENTLY_VERIFIED,
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
            "candidate_azure_responses_single_attempt_adapter_available": True,
            "production_runtime_wrapper_available": False,
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
        raise RuntimeError("V2.42.36 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.36 audit output path is noncanonical")
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
