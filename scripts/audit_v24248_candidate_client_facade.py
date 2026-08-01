#!/usr/bin/env python3
"""Create-exclusive no-network audit for V2.42.48 candidate client facade."""

from __future__ import annotations

import argparse
import ast
import hashlib
import inspect
import json
import os
import re
import sys
import tempfile
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
    build_shared_total_budget_contract,
    initialize_arm_budget_ledger,
)
from deepwide_agent.v24233_webswarm_effect_preauthorization import (  # noqa: E402
    initialize_effect_preauthorization_state,
)
from deepwide_agent.v24236_azure_responses_single_attempt import (  # noqa: E402
    AzureResponsesSingleAttemptAdapter,
)
from deepwide_agent.v24237_tavily_search_single_attempt import (  # noqa: E402
    TavilySearchSingleAttemptAdapter,
)
from deepwide_agent.v24242_durable_effect_coordinator import (  # noqa: E402
    DurableEffectReplayRejected,
    DurablePreauthorizedEffectCoordinator,
)
from deepwide_agent.v24243_retry_deadline_scheduler import (  # noqa: E402
    RetryDeadlineEffectScheduler,
)
from deepwide_agent.v24244_strict_json_parser_boundary import (  # noqa: E402
    build_strict_json_parser_contract,
)
from deepwide_agent.v24245_pinned_native_http_fetch import (  # noqa: E402
    PinnedNativeHttpFetchAdapter,
)
from deepwide_agent.v24246_search_page_projection import (  # noqa: E402
    build_search_page_projection_contract,
)
from deepwide_agent.v24247_candidate_runtime_assembly import (  # noqa: E402
    CandidateRuntimeAssembly,
    build_candidate_runtime_assembly_contract,
)
from deepwide_agent.v24248_candidate_client_facade import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    ADAPTER_CODE_IDENTITY_INDEPENDENTLY_ATTESTED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CALLER_ACTION_REF_SEMANTIC_INDEPENDENCE_VERIFIED,
    CONTENT_FREE_ACTION_REF_DERIVATION_IMPLEMENTED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    EXACT_ADAPTER_AND_ASSEMBLY_TYPE_ENFORCEMENT_IMPLEMENTED,
    EXTERNAL_SIDE_EFFECT_AUTHORIZED,
    FROZEN_PROVIDER_METER_AND_DEADLINE_CONTRACTS_IMPLEMENTED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    LEGACY_RUNTIME_CLIENT_SURFACE_IMPLEMENTED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    SCHEMA_RESEALING_WITHOUT_SECRET_CRYPTOGRAPHICALLY_EXCLUDED,
    SEARCH_LEADS_OR_PAGE_TEXT_ACTIVE_EVIDENCE_ELIGIBILITY_GRANTED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    CandidateClientFacade,
    build_candidate_client_facade_contract,
    derive_candidate_facade_action_ref,
    validate_candidate_client_facade_receipt,
)


ROLE = "v24248_candidate_client_facade_candidate_audit"
OUTPUT = Path("results/v24248_candidate_client_facade_candidate_audit_v1_20260801.json")
PARENT_RECEIPT = Path(
    "results/v24247_candidate_runtime_assembly_candidate_audit_v1_20260801.json"
)
PARENT_RECEIPT_SHA256 = (
    "8c627b811be2d1b769dfe93d27891d90555b25c8a7c6077d372842aa4118146b"
)
PARENT_PAYLOAD_SHA256 = (
    "c27ee157cab65f2e5d5ca426b6d3ce21d66e646eadd9bd83890423e7da8dc70c"
)
PARENT_MANIFEST_SHA256 = (
    "e2d7dfe1c50e36685d4dcd4d5b1bf2f6420b84bafec0e5be45852d8da4bc9c19"
)
PARENT_CONTROL_FILES = (
    Path("src/deepwide_agent/v24247_candidate_runtime_assembly.py"),
    Path("tests/test_v24247_candidate_runtime_assembly.py"),
    Path("scripts/audit_v24247_candidate_runtime_assembly.py"),
    Path("tests/test_audit_v24247_candidate_runtime_assembly.py"),
)
MODULE = Path("src/deepwide_agent/v24248_candidate_client_facade.py")
MODULE_TEST = Path("tests/test_v24248_candidate_client_facade.py")
AUDIT = Path("scripts/audit_v24248_candidate_client_facade.py")
AUDIT_TEST = Path("tests/test_audit_v24248_candidate_client_facade.py")
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
        "copy",
        "dataclasses",
        "typing",
        "deepwide_agent.v24232_webswarm_total_budget",
        "deepwide_agent.v24234_provider_cost_meter",
        "deepwide_agent.v24236_azure_responses_single_attempt",
        "deepwide_agent.v24237_tavily_search_single_attempt",
        "deepwide_agent.v24239_azure_hosted_search_single_attempt",
        "deepwide_agent.v24240_anthropic_server_search_single_attempt",
        "deepwide_agent.v24243_retry_deadline_scheduler",
        "deepwide_agent.v24244_strict_json_parser_boundary",
        "deepwide_agent.v24245_pinned_native_http_fetch",
        "deepwide_agent.v24246_search_page_projection",
        "deepwide_agent.v24247_candidate_runtime_assembly",
    }
)
REQUIRED_PUBLIC_SYMBOLS = frozenset(
    {
        "CandidateClientFacadeError",
        "CandidateClientFacadeResult",
        "CandidateFacadeActionRef",
        "build_candidate_client_facade_contract",
        "validate_candidate_client_facade_contract",
        "derive_candidate_facade_action_ref",
        "validate_candidate_client_facade_receipt",
        "CandidateClientFacade",
        "run_model_json",
        "run_search_leads",
        "run_fetched_page",
    }
)
FORBIDDEN_CALL_NAMES = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "open",
        "input",
        "breakpoint",
        "__import__",
        "getattr",
        "setattr",
    }
)
FORBIDDEN_ATTRIBUTES = frozenset(
    {
        "getenv",
        "environ",
        "popen",
        "system",
        "execv",
        "execve",
        "fork",
        "kill",
        "connect",
        "request",
        "urlopen",
        "post",
        "put",
        "delete",
        "read_bytes",
        "read_text",
        "write_bytes",
        "write_text",
    }
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
INVOCATION_FORBIDDEN_NAMES = frozenset(
    {
        "system",
        "user",
        "prompt",
        "query",
        "url",
        "credential",
        "provider_value",
        "projected_value",
        "question",
        "prediction",
        "answer",
        "score",
        "gold",
        "mapping",
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
        raise RuntimeError("V2.42.48 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.42.48 expected ordinary repository file: {relative}")
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
    expansive_calls: list[str] = []
    privileged_reads: list[str] = []
    public_callback_parameters: list[str] = []
    assembly_dispatch = {
        "run_model_json": 0,
        "run_search_leads": 0,
        "run_fetched_page": 0,
    }
    derivation_functions: dict[str, ast.FunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.add(node.name)
            if isinstance(node, ast.FunctionDef) and node.name in {
                "derive_candidate_facade_action_ref",
                "_invocation_ref",
            }:
                derivation_functions[node.name] = node
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in {
                "run_model_json",
                "run_search_leads",
                "run_fetched_page",
            }:
                names = [argument.arg for argument in node.args.args + node.args.kwonlyargs]
                public_callback_parameters.extend(
                    name for name in names if name in {"callback", "fault_hook"}
                )
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_CALL_NAMES:
                    forbidden_calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                attribute = node.func.attr
                if attribute in FORBIDDEN_ATTRIBUTES:
                    expansive_calls.append(attribute)
                if attribute == "get" and node.args:
                    key = _literal_key(node.args[0])
                    if key in FORBIDDEN_METADATA_ACCESS_KEYS:
                        privileged_reads.append(str(key))
                if attribute in assembly_dispatch:
                    assembly_dispatch[attribute] += 1
        elif isinstance(node, ast.Subscript):
            key = _literal_key(node.slice)
            if key in FORBIDDEN_METADATA_ACCESS_KEYS:
                privileged_reads.append(str(key))
    derivation_names = {
        node.id
        for function in derivation_functions.values()
        for node in ast.walk(function)
        if isinstance(node, ast.Name)
    }
    invocation_forbidden = sorted(
        derivation_names & INVOCATION_FORBIDDEN_NAMES
    )
    disallowed_imports = sorted(imports - ALLOWED_IMPORT_MODULES)
    missing = sorted(REQUIRED_PUBLIC_SYMBOLS - symbols)
    if (
        disallowed_imports
        or forbidden_calls
        or expansive_calls
        or privileged_reads
        or missing
        or public_callback_parameters
        or set(derivation_functions)
        != {"derive_candidate_facade_action_ref", "_invocation_ref"}
        or invocation_forbidden
        or assembly_dispatch
        != {"run_model_json": 1, "run_search_leads": 1, "run_fetched_page": 1}
    ):
        raise RuntimeError(
            "V2.42.48 capability boundary failed: "
            f"imports={disallowed_imports}, calls={forbidden_calls}, "
            f"expansive={expansive_calls}, privileged={privileged_reads}, "
            f"missing={missing}, callback_params={public_callback_parameters}, "
            f"invocation_forbidden={invocation_forbidden}, "
            f"assembly_dispatch={assembly_dispatch}"
        )
    return {
        "ast_node_count": sum(1 for _ in ast.walk(tree)),
        "import_modules": sorted(imports),
        "required_public_symbols_present": sorted(REQUIRED_PUBLIC_SYMBOLS),
        "candidate_assembly_dispatch_call_site_count_by_method": assembly_dispatch,
        "invocation_derivation_forbidden_ephemeral_name_count": 0,
        "public_callback_or_fault_hook_parameter_count": 0,
        "privileged_metadata_read_count": 0,
        "direct_network_environment_file_process_subprocess_or_dynamic_code_call_site_count": 0,
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
    shared = {
        "guidance_contract": budget,
        "guidance_policy": policy,
        "guidance_arm": arm,
        "scouts": scouts,
        "probe": probe,
        "experience": experience,
    }
    initial = initialize_effect_preauthorization_state(
        initial_budget_ledger=ledger,
        contract=budget,
        guidance_policy=policy,
        guidance_arm=arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
    )
    return initial, shared


class _Clock:
    def __init__(self) -> None:
        self.now_ns = 10_000_000_000

    def monotonic_ns(self) -> int:
        return self.now_ns

    def sleep(self, seconds: float) -> None:
        self.now_ns += int(round(seconds * 1_000_000_000))


class _Response:
    def __init__(self, content: bytes) -> None:
        self.status_code = 200
        self.content = content


class _Post:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.calls = 0

    def __call__(self, _url: str, **_kwargs: Any) -> _Response:
        self.calls += 1
        return _Response(self.content)


class _FetchResponse:
    def __init__(self, content: bytes) -> None:
        self.status = 200
        self.content = content
        self.headers = {"Content-Type": "text/html; charset=utf-8"}

    def stream(self, **_kwargs: Any):
        yield self.content

    def close(self) -> None:
        pass

    def release_conn(self) -> None:
        pass


class _Pool:
    def __init__(self, response: _FetchResponse) -> None:
        self.response = response
        self.calls = 0

    def urlopen(self, *_args: Any, **_kwargs: Any) -> _FetchResponse:
        self.calls += 1
        return self.response

    def close(self) -> None:
        pass


class _PoolFactory:
    def __init__(self, response: _FetchResponse) -> None:
        self.pool = _Pool(response)
        self.calls = 0

    def __call__(self, **_kwargs: Any) -> _Pool:
        self.calls += 1
        return self.pool


def replay_fake_facade() -> dict[str, Any]:
    initial, shared = _parent()
    private_model = "synthetic private model value"
    private_answer = "synthetic private search answer"
    private_snippet = "synthetic private search snippet"
    private_page = "synthetic private visible page"
    private_query = "synthetic private visible query"
    private_url = "https://example.test/page"
    model_bytes = json.dumps(
        {
            "id": "synthetic-response",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps(
                                {"ready": True, "value": private_model}
                            ),
                        }
                    ],
                }
            ],
            "usage": {"input_tokens": 20, "output_tokens": 5, "total_tokens": 25},
        },
        sort_keys=True,
    ).encode()
    search_bytes = json.dumps(
        {
            "answer": private_answer,
            "results": [
                {
                    "title": "synthetic title",
                    "url": private_url,
                    "content": private_snippet,
                    "raw_content": private_snippet,
                    "score": 0.9,
                }
            ],
        },
        sort_keys=True,
    ).encode()
    page_bytes = (
        f"<html><body>{private_page}<script>private script</script></body></html>"
    ).encode()
    with tempfile.TemporaryDirectory(dir=ROOT) as directory:
        coordinator = DurablePreauthorizedEffectCoordinator.initialize(
            root=Path(directory).resolve(),
            journal_namespace_sha256=_digest("v24248-audit-journal"),
            initial_state=initial,
            **shared,
        )
        clock = _Clock()
        scheduler = RetryDeadlineEffectScheduler(
            coordinator=coordinator,
            monotonic_ns=clock.monotonic_ns,
            sleeper=clock.sleep,
        )
        assembly_contract = build_candidate_runtime_assembly_contract(
            model_parser_contract=build_strict_json_parser_contract(
                maximum_text_characters=2000,
                maximum_utf8_bytes=4000,
                maximum_depth=8,
                maximum_nodes=100,
                maximum_object_members=20,
                maximum_array_items=20,
                maximum_string_characters=500,
            ),
            search_page_projection_contract=build_search_page_projection_contract(
                maximum_leads=8,
                maximum_page_bytes=4096,
                maximum_page_text_characters=500,
                maximum_title_characters=100,
                maximum_url_characters=1024,
                maximum_html_tags=100,
            ),
        )
        assembly = CandidateRuntimeAssembly(
            scheduler=scheduler,
            assembly_contract=assembly_contract,
        )
        facade_contract = build_candidate_client_facade_contract(
            assembly_contract=assembly_contract,
            search_provider_kind="tavily_search_api",
            model_maximum_prompt_utf8_bytes=4000,
            model_maximum_output_tokens=200,
            model_reasoning_effort="high",
            model_service_tier="priority",
            model_timeout_seconds=1,
            model_max_attempts=1,
            model_reserved_input_tokens_per_attempt=8096,
            search_maximum_query_utf8_bytes=2000,
            search_maximum_output_tokens=0,
            search_maximum_provider_tool_calls_per_attempt=0,
            search_maximum_results=2,
            search_context_size="",
            search_reasoning_effort="",
            search_service_tier="",
            search_timeout_seconds=1,
            search_max_attempts=1,
            search_reserved_input_tokens_per_attempt=0,
            fetch_maximum_response_bytes=4096,
            fetch_timeout_seconds=1,
            fetch_max_attempts=1,
            initial_backoff_milliseconds=10,
            backoff_multiplier=2,
            maximum_backoff_milliseconds=100,
            deadline_margin_milliseconds=100,
        )
        model_post = _Post(model_bytes)
        search_post = _Post(search_bytes)
        fetch_response = _FetchResponse(page_bytes)
        pool_factory = _PoolFactory(fetch_response)
        facade = CandidateClientFacade(
            assembly=assembly,
            facade_contract=facade_contract,
            model_adapter=AzureResponsesSingleAttemptAdapter(
                endpoint="http://127.0.0.1:9878/responses",
                model="gpt-5.6-sol",
                timeout_seconds=1,
                post=model_post,
            ),
            search_adapter=TavilySearchSingleAttemptAdapter(
                endpoint="https://api.tavily.com/search",
                credentials=("synthetic-credential",),
                timeout_seconds=1,
                post=search_post,
            ),
            fetch_adapter=PinnedNativeHttpFetchAdapter(
                timeout_seconds=1,
                max_response_bytes=4096,
                resolve=lambda _host, _port: ("93.184.216.34",),
                pool_factory=pool_factory,
            ),
        )
        model_action = derive_candidate_facade_action_ref(
            task_scope_ref_sha256=_digest("opaque-scope"),
            stage_ref_sha256=_digest("model-stage"),
            operation_kind="model_json",
            action_ordinal=1,
        )
        model = facade.run_model_json(
            action_ref=model_action,
            system="synthetic private system",
            user="synthetic private user",
            max_output_tokens=200,
        )
        search = facade.run_search_leads(
            action_ref=derive_candidate_facade_action_ref(
                task_scope_ref_sha256=_digest("opaque-scope"),
                stage_ref_sha256=_digest("search-stage"),
                operation_kind="search_leads",
                action_ordinal=1,
            ),
            query=private_query,
            max_results=1,
        )
        page = facade.run_fetched_page(
            action_ref=derive_candidate_facade_action_ref(
                task_scope_ref_sha256=_digest("opaque-scope"),
                stage_ref_sha256=_digest("fetch-stage"),
                operation_kind="fetched_page",
                action_ordinal=1,
            ),
            url=private_url,
        )
        for result in (model, search, page):
            validate_candidate_client_facade_receipt(result.receipt)
        encoded_receipts = json.dumps(
            [model.receipt, search.receipt, page.receipt], ensure_ascii=False
        )
        private_values = (
            private_model,
            private_answer,
            private_snippet,
            private_page,
            private_query,
            private_url,
            "synthetic private system",
            "synthetic private user",
        )
        if any(value in encoded_receipts for value in private_values):
            raise RuntimeError("V2.42.48 ephemeral content entered receipt")
        replay_rejected = False
        try:
            facade.run_model_json(
                action_ref=model_action,
                system="different synthetic private system",
                user="different synthetic private user",
                max_output_tokens=200,
            )
        except DurableEffectReplayRejected:
            replay_rejected = True
        method_parameters = {
            name: sorted(inspect.signature(getattr(CandidateClientFacade, name)).parameters)
            for name in ("run_model_json", "run_search_leads", "run_fetched_page")
        }
        return {
            "local_tempdir_virtual_time_and_injected_fake_transports_only": True,
            "network_socket_or_real_model_search_fetch_api_called": False,
            "durable_settled_effect_count": coordinator.journal.load()["settled_permit_count"],
            "model_post_count": model_post.calls,
            "search_post_count": search_post.calls,
            "fetch_pool_count": pool_factory.calls,
            "fetch_urlopen_count": pool_factory.pool.calls,
            "model_json_ephemeral_value_returned": model.value["value"] == private_model,
            "search_untrusted_lead_ephemeral_value_returned": len(search.value) == 1,
            "page_untrusted_text_ephemeral_value_returned": page.value.text == private_page,
            "search_or_page_active_evidence_eligibility_granted": False,
            "private_prompt_query_answer_snippet_url_page_or_json_in_receipts": False,
            "same_action_ref_different_prompt_replay_rejected_before_second_post": replay_rejected,
            "model_post_count_after_replay_rejection": model_post.calls,
            "public_callback_or_fault_hook_parameter_present": any(
                "callback" in parameters or "fault_hook" in parameters
                for parameters in method_parameters.values()
            ),
            "legacy_complete_json_search_many_or_fetch_urls_surface_present": any(
                hasattr(CandidateClientFacade, name)
                for name in ("complete_json", "search_many", "fetch_urls")
            ),
            "benchmark_question_prediction_mapping_gold_evaluator_or_score_used_for_routing": False,
        }


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.48 audit may only use canonical workspace")
    paths = {str(path): ordinary(root, path) for path in CONTROL_FILES}
    parent_path = ordinary(root, PARENT_RECEIPT)
    if sha256(parent_path) != PARENT_RECEIPT_SHA256:
        raise RuntimeError("V2.42.48 parent receipt bytes drifted")
    parent_value = json.loads(parent_path.read_text(encoding="utf-8"))
    parent_unsigned = dict(parent_value)
    parent_payload = parent_unsigned.pop("audit_payload_sha256", None)
    if (
        parent_value.get("role")
        != "v24247_candidate_runtime_assembly_candidate_audit"
        or parent_value.get("audit_valid") is not True
        or parent_payload != PARENT_PAYLOAD_SHA256
        or payload_sha256(parent_unsigned) != PARENT_PAYLOAD_SHA256
        or parent_value.get("control_surface", {}).get("manifest_sha256")
        != PARENT_MANIFEST_SHA256
    ):
        raise RuntimeError("V2.42.48 parent receipt semantics drifted")
    parent_paths = {
        str(path): ordinary(root, path) for path in PARENT_CONTROL_FILES
    }
    parent_manifest = {name: sha256(path) for name, path in parent_paths.items()}
    if parent_manifest != parent_value["control_surface"]["manifest"]:
        raise RuntimeError("V2.42.48 parent control files drifted")
    if payload_sha256(parent_manifest) != PARENT_MANIFEST_SHA256:
        raise RuntimeError("V2.42.48 parent manifest seal drifted")
    sources = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    literal_hits = {
        name: bool(SECRET_LITERAL.search(source) or OPAQUE_ID.search(source))
        for name, source in sources.items()
    }
    if any(literal_hits.values()):
        raise RuntimeError("V2.42.48 control source contains forbidden content")
    static = audit_python_source(sources[str(MODULE)])
    guards = {str(path): ordinary(root, path) for path in ACTIVE_FORWARD_GUARDS}
    module_name = "v24248_candidate_client_facade"
    guard_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in guards.items()
    }
    if any(guard_hits.values()):
        raise RuntimeError("V2.42.48 appears in an active forward guard")
    control_manifest = {name: sha256(path) for name, path in paths.items()}
    guard_manifest = {name: sha256(path) for name, path in guards.items()}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "label_blind_runtime": True,
        "candidate_client_facade": True,
        "parent_receipt": {
            "path": str(PARENT_RECEIPT),
            "file_sha256": PARENT_RECEIPT_SHA256,
            "payload_sha256": PARENT_PAYLOAD_SHA256,
            "v24247_control_manifest_sha256": PARENT_MANIFEST_SHA256,
            "v24247_control_files_rehashed": len(parent_manifest),
            "v24247_candidate_parent_validated": True,
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
        "fake_facade_replay": replay_fake_facade(),
        "scientific_scope": {
            "content_free_action_ref_derivation_implemented": CONTENT_FREE_ACTION_REF_DERIVATION_IMPLEMENTED,
            "frozen_provider_meter_and_deadline_contracts_implemented": FROZEN_PROVIDER_METER_AND_DEADLINE_CONTRACTS_IMPLEMENTED,
            "exact_adapter_and_assembly_type_enforcement_implemented": EXACT_ADAPTER_AND_ASSEMBLY_TYPE_ENFORCEMENT_IMPLEMENTED,
            "legacy_runtime_client_surface_implemented": LEGACY_RUNTIME_CLIENT_SURFACE_IMPLEMENTED,
            "search_leads_or_page_text_active_evidence_eligibility_granted": SEARCH_LEADS_OR_PAGE_TEXT_ACTIVE_EVIDENCE_ELIGIBILITY_GRANTED,
            "caller_action_ref_semantic_independence_verified": CALLER_ACTION_REF_SEMANTIC_INDEPENDENCE_VERIFIED,
            "adapter_code_identity_independently_attested": ADAPTER_CODE_IDENTITY_INDEPENDENTLY_ATTESTED,
            "schema_resealing_without_secret_cryptographically_excluded": SCHEMA_RESEALING_WITHOUT_SECRET_CRYPTOGRAPHICALLY_EXCLUDED,
            "real_provider_traffic_observed": False,
            "active_client_or_runner_integrated": False,
            "dev64_gate_evaluated": False,
            "fresh_exact220_evaluated": False,
            "quality_cost_or_benchmark_effect_observed": False,
        },
        "source_policy": {
            "repository_control_code_parent_receipt_synthetic_requests_values_fake_transports_and_local_tempdir_only": True,
            "runtime_task_question_prediction_or_answer_read": False,
            "benchmark_subset_category_question_type_label_split_or_mapping_used_for_routing": False,
            "gold_evaluator_payload_score_reward_or_results_read": False,
            "credential_environment_keyring_or_secret_value_read": False,
            "audit_network_socket_real_model_search_fetch_subprocess_or_api_called": False,
        },
        "authorization": {
            "isolated_content_free_action_ref_facade_capability": True,
            "active_provider_traffic_authorized": ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
            "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
            "active_forward_integration_authorized": ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
            "external_side_effect_authorized": EXTERNAL_SIDE_EFFECT_AUTHORIZED,
            "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
            "dev64_or_exact220_launch_authorized": DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
            "shared_api_lease_acquire_authorized": SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
            "process_signal_restart_resume_rerun_or_selective_retry": False,
            "leaderboard_submission_or_sota_claim": LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
        },
        "claims": {
            "candidate_content_free_action_ref_facade_available": True,
            "legacy_runtime_drop_in_client_available": False,
            "active_runtime_wrapper_available": False,
            "active_evidence_admission_available": False,
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
        raise RuntimeError("V2.42.48 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.48 audit output path is noncanonical")
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
                "candidate_client_facade": value["candidate_client_facade"],
            }
        )
    )


if __name__ == "__main__":
    main()
