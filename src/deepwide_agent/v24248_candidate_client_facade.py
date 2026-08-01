"""Content-free action-ref facade for the V2.42.47 candidate assembly.

The V2.42.47 assembly deliberately requires a caller to construct provider
meter and deadline contracts for every typed effect.  This module freezes
those contracts once, binds exact known adapters, and derives each durable
invocation only from a caller-supplied content-free action reference.  The
facade creates no new hash of a prompt, query, URL, provider value, or projected
value.  It does embed the validated parent assembly graph, including the
parent's provider-response reference, so that durable settlement remains
standalone-verifiable.

This remains an isolated candidate.  Search results are discovery leads and
fetched text remains untrusted with zero instruction or active-evidence
authority.  The module does not implement the legacy ``complete_json`` or
``search_many`` client surfaces and is not imported by active clients,
runtime, runner, launcher, benchmark, or evaluator code.  Caller action-ref
semantics, adapter code identity, provider authenticity, and secret-free
schema resealing are not independently attested.
"""

from __future__ import annotations

import copy
import dataclasses
from typing import Any, Mapping

from deepwide_agent.v24232_webswarm_total_budget import (
    build_cost_vector,
    object_sha256,
)
from deepwide_agent.v24234_provider_cost_meter import (
    build_provider_meter_contract,
)
from deepwide_agent.v24236_azure_responses_single_attempt import (
    AzureResponsesRequest,
    AzureResponsesSingleAttemptAdapter,
)
from deepwide_agent.v24237_tavily_search_single_attempt import (
    TavilySearchRequest,
    TavilySearchSingleAttemptAdapter,
)
from deepwide_agent.v24239_azure_hosted_search_single_attempt import (
    AzureHostedSearchRequest,
    AzureHostedSearchSingleAttemptAdapter,
)
from deepwide_agent.v24240_anthropic_server_search_single_attempt import (
    AnthropicServerSearchRequest,
    AnthropicServerSearchSingleAttemptAdapter,
)
from deepwide_agent.v24243_retry_deadline_scheduler import (
    build_retry_deadline_contract,
)
from deepwide_agent.v24244_strict_json_parser_boundary import (
    validate_strict_json_parser_receipt,
)
from deepwide_agent.v24245_pinned_native_http_fetch import (
    NativeHttpFetchRequest,
    PinnedNativeHttpFetchAdapter,
)
from deepwide_agent.v24246_search_page_projection import (
    PageTextProjection,
    SearchLeadProjection,
    validate_search_page_projection_receipt,
)
from deepwide_agent.v24247_candidate_runtime_assembly import (
    CandidateRuntimeAssembly,
    CandidateRuntimeAssemblyResult,
    validate_candidate_runtime_assembly_contract,
    validate_candidate_runtime_assembly_receipt,
)


POLICY_ID = "v24248_candidate_client_facade_v1"
CONTRACT_ROLE = "v24248_candidate_client_facade_contract"
RECEIPT_ROLE = "v24248_candidate_client_facade_receipt"

PRODUCTION_PACKAGE_AUTHORIZED = False
ACTIVE_FORWARD_INTEGRATION_AUTHORIZED = False
ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED = False
EXTERNAL_SIDE_EFFECT_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
DEV64_OR_EXACT220_LAUNCH_AUTHORIZED = False
SHARED_API_LEASE_ACQUIRE_AUTHORIZED = False
LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED = False

CONTENT_FREE_ACTION_REF_DERIVATION_IMPLEMENTED = True
FROZEN_PROVIDER_METER_AND_DEADLINE_CONTRACTS_IMPLEMENTED = True
EXACT_ADAPTER_AND_ASSEMBLY_TYPE_ENFORCEMENT_IMPLEMENTED = True
LEGACY_RUNTIME_CLIENT_SURFACE_IMPLEMENTED = False
SEARCH_LEADS_OR_PAGE_TEXT_ACTIVE_EVIDENCE_ELIGIBILITY_GRANTED = False
CALLER_ACTION_REF_SEMANTIC_INDEPENDENCE_VERIFIED = False
ADAPTER_CODE_IDENTITY_INDEPENDENTLY_ATTESTED = False
SCHEMA_RESEALING_WITHOUT_SECRET_CRYPTOGRAPHICALLY_EXCLUDED = False

SEARCH_PROVIDER_ADAPTERS = {
    "tavily_search_api": TavilySearchSingleAttemptAdapter,
    "azure_responses_web_search": AzureHostedSearchSingleAttemptAdapter,
    "anthropic_server_web_search": AnthropicServerSearchSingleAttemptAdapter,
}
OPERATION_KINDS = frozenset({"model_json", "search_leads", "fetched_page"})

CONTRACT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "candidate_runtime",
        "assembly_contract",
        "assembly_contract_sha256",
        "search_provider_kind",
        "model_maximum_prompt_utf8_bytes",
        "model_maximum_output_tokens",
        "model_reasoning_effort",
        "model_service_tier",
        "model_timeout_seconds",
        "model_max_attempts",
        "model_reserved_input_tokens_per_attempt",
        "search_maximum_query_utf8_bytes",
        "search_maximum_output_tokens",
        "search_maximum_provider_tool_calls_per_attempt",
        "search_maximum_results",
        "search_context_size",
        "search_reasoning_effort",
        "search_service_tier",
        "search_timeout_seconds",
        "search_max_attempts",
        "search_reserved_input_tokens_per_attempt",
        "fetch_maximum_response_bytes",
        "fetch_timeout_seconds",
        "fetch_max_attempts",
        "initial_backoff_milliseconds",
        "backoff_multiplier",
        "maximum_backoff_milliseconds",
        "deadline_margin_milliseconds",
        "model_meter_contract",
        "model_scheduler_contract",
        "search_meter_contract",
        "search_scheduler_contract",
        "fetch_meter_contract",
        "fetch_scheduler_contract",
        "caller_content_free_action_ref_required",
        "facade_invocation_derivation_uses_ephemeral_content",
        "legacy_runtime_client_surface_implemented",
        "search_leads_or_page_text_active_evidence_eligibility_granted",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "contract_sha256",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "candidate_runtime",
        "operation_kind",
        "provider_kind",
        "value_kind",
        "assembly_value_item_count",
        "requested_value_item_limit",
        "returned_value_item_count",
        "facade_value_truncation_applied",
        "action_ref",
        "action_ref_sha256",
        "invocation_ref_sha256",
        "facade_contract",
        "facade_contract_sha256",
        "assembly_receipt",
        "assembly_receipt_sha256",
        "meter_contract_sha256",
        "scheduler_contract_sha256",
        "attempt_count",
        "settlement_cost",
        "caller_content_free_action_ref_required",
        "caller_action_ref_semantic_independence_verified",
        "facade_invocation_derivation_used_ephemeral_content",
        "exact_adapter_and_assembly_type_enforced",
        "frozen_provider_meter_and_deadline_contracts_used",
        "legacy_runtime_client_surface_implemented",
        "search_leads_or_page_text_active_evidence_eligibility_granted",
        "raw_prompt_query_url_provider_value_or_projected_output_entered_receipt",
        "facade_created_new_ephemeral_content_hash",
        "parent_provider_response_reference_retained",
        "credential_environment_or_keyring_read",
        "benchmark_or_evaluator_metadata_used_for_routing",
        "adapter_code_identity_independently_attested",
        "schema_resealing_without_secret_cryptographically_excluded",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "facade_receipt_sha256",
    }
)


class CandidateClientFacadeError(ValueError):
    """Sanitized facade rejection without ephemeral request content."""


@dataclasses.dataclass(frozen=True)
class CandidateClientFacadeResult:
    receipt: Mapping[str, Any]
    value: Any


@dataclasses.dataclass(frozen=True)
class CandidateFacadeActionRef:
    task_scope_ref_sha256: str
    stage_ref_sha256: str
    operation_kind: str
    action_ordinal: int
    action_ref_sha256: str


ACTION_REF_KEYS = frozenset(
    {
        "task_scope_ref_sha256",
        "stage_ref_sha256",
        "operation_kind",
        "action_ordinal",
        "action_ref_sha256",
    }
)


def _clone(value: Any) -> Any:
    return copy.deepcopy(value)


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _integer(
    value: object,
    *,
    label: str,
    minimum: int = 0,
    maximum: int = 1_000_000_000_000_000,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise ValueError(f"V2.42.48 {label} is outside the frozen range")
    return value


def _exact(
    value: Mapping[str, Any], *, keys: frozenset[str], label: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"V2.42.48 {label} schema is not exact")
    return value


def _sealed(value: Mapping[str, Any], *, key: str) -> bool:
    seal = value.get(key)
    if not _is_sha256(seal):
        return False
    unsigned = dict(value)
    unsigned.pop(key)
    return seal == object_sha256(unsigned)


def _backoffs(
    *, attempts: int, initial: int, multiplier: int, maximum: int
) -> tuple[int, ...]:
    current = initial
    values: list[int] = []
    for _ in range(attempts - 1):
        bounded = min(current, maximum)
        values.append(bounded)
        current = maximum if bounded >= maximum else min(maximum, bounded * multiplier)
    return tuple(values)


def _effect_contracts(
    *,
    provider_kind: str,
    charge_kind: str,
    max_attempts: int,
    timeout_seconds: int,
    reserved_input_tokens_per_attempt: int,
    reserved_output_tokens_per_attempt: int,
    reserved_provider_tool_calls_per_attempt: int,
    initial_backoff_milliseconds: int,
    backoff_multiplier: int,
    maximum_backoff_milliseconds: int,
    deadline_margin_milliseconds: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    attempts = _integer(max_attempts, label="maximum attempts", minimum=1, maximum=64)
    timeout = _integer(timeout_seconds, label="timeout seconds", minimum=1, maximum=3600)
    input_tokens = _integer(
        reserved_input_tokens_per_attempt,
        label="reserved input tokens per attempt",
    )
    output_tokens = _integer(
        reserved_output_tokens_per_attempt,
        label="reserved output tokens per attempt",
    )
    provider_tools = _integer(
        reserved_provider_tool_calls_per_attempt,
        label="reserved provider tool calls per attempt",
    )
    initial = _integer(
        initial_backoff_milliseconds,
        label="initial backoff milliseconds",
        minimum=1,
    )
    multiplier = _integer(
        backoff_multiplier,
        label="backoff multiplier",
        minimum=1,
        maximum=1024,
    )
    maximum = _integer(
        maximum_backoff_milliseconds,
        label="maximum backoff milliseconds",
        minimum=1,
    )
    margin = _integer(
        deadline_margin_milliseconds,
        label="deadline margin milliseconds",
        minimum=1,
    )
    if maximum < initial:
        raise ValueError("V2.42.48 maximum backoff is below initial backoff")
    backoff_total = sum(
        _backoffs(
            attempts=attempts,
            initial=initial,
            multiplier=multiplier,
            maximum=maximum,
        )
    )
    total_deadline = attempts * timeout * 1000 + backoff_total + margin
    wall_reservation = total_deadline + attempts - 1
    values = {
        "model_calls": 0,
        "model_attempts": 0,
        "search_calls": 0,
        "fetch_calls": 0,
        "other_tool_calls": 0,
        "orchestrator_calls": 0,
        "input_tokens": attempts * input_tokens,
        "output_tokens": attempts * output_tokens,
        "wall_milliseconds": wall_reservation,
    }
    if provider_kind == "azure_responses_model":
        values.update(model_calls=1, model_attempts=attempts)
    elif provider_kind in {
        "azure_responses_web_search",
        "anthropic_server_web_search",
    }:
        values.update(
            search_calls=attempts,
            other_tool_calls=attempts * provider_tools,
        )
    elif provider_kind == "tavily_search_api":
        values["search_calls"] = attempts
    elif provider_kind == "native_http_fetch":
        values["fetch_calls"] = attempts
    else:
        raise ValueError("V2.42.48 provider kind is invalid")
    meter = build_provider_meter_contract(
        provider_kind=provider_kind,
        charge_kind=charge_kind,
        max_attempts=attempts,
        reserved_cost=build_cost_vector(**values),
    )
    scheduler = build_retry_deadline_contract(
        meter_contract=meter,
        total_deadline_milliseconds=total_deadline,
        minimum_attempt_window_milliseconds=timeout * 1000,
        initial_backoff_milliseconds=initial,
        backoff_multiplier=multiplier,
        maximum_backoff_milliseconds=maximum,
    )
    return meter, scheduler


def build_candidate_client_facade_contract(
    *,
    assembly_contract: Mapping[str, Any],
    search_provider_kind: str,
    model_maximum_prompt_utf8_bytes: int,
    model_maximum_output_tokens: int,
    model_reasoning_effort: str,
    model_service_tier: str,
    model_timeout_seconds: int,
    model_max_attempts: int,
    model_reserved_input_tokens_per_attempt: int,
    search_maximum_query_utf8_bytes: int,
    search_maximum_output_tokens: int,
    search_maximum_provider_tool_calls_per_attempt: int,
    search_maximum_results: int,
    search_context_size: str,
    search_reasoning_effort: str,
    search_service_tier: str,
    search_timeout_seconds: int,
    search_max_attempts: int,
    search_reserved_input_tokens_per_attempt: int,
    fetch_maximum_response_bytes: int,
    fetch_timeout_seconds: int,
    fetch_max_attempts: int,
    initial_backoff_milliseconds: int,
    backoff_multiplier: int,
    maximum_backoff_milliseconds: int,
    deadline_margin_milliseconds: int,
) -> dict[str, Any]:
    assembly = _clone(dict(assembly_contract))
    validate_candidate_runtime_assembly_contract(assembly)
    provider = str(search_provider_kind)
    if provider not in SEARCH_PROVIDER_ADAPTERS:
        raise ValueError("V2.42.48 search provider is invalid")
    prompt_bytes = _integer(
        model_maximum_prompt_utf8_bytes,
        label="maximum prompt UTF-8 bytes",
        minimum=1,
    )
    model_output = _integer(
        model_maximum_output_tokens,
        label="maximum model output tokens",
        minimum=1,
    )
    model_input = _integer(
        model_reserved_input_tokens_per_attempt,
        label="model input reservation per attempt",
        minimum=1,
    )
    if model_input < prompt_bytes + 4096:
        raise ValueError("V2.42.48 model input reservation is not conservative")
    query_bytes = _integer(
        search_maximum_query_utf8_bytes,
        label="maximum query UTF-8 bytes",
        minimum=1,
        maximum=32_768,
    )
    search_output = _integer(
        search_maximum_output_tokens,
        label="maximum search output tokens",
    )
    search_tools = _integer(
        search_maximum_provider_tool_calls_per_attempt,
        label="maximum search provider tool calls per attempt",
    )
    search_results = _integer(
        search_maximum_results,
        label="maximum search results",
        minimum=1,
        maximum=20,
    )
    search_input = _integer(
        search_reserved_input_tokens_per_attempt,
        label="search input reservation per attempt",
    )
    fetch_bytes = _integer(
        fetch_maximum_response_bytes,
        label="maximum fetch response bytes",
        minimum=1,
        maximum=32_000_000,
    )
    if search_results > int(
        assembly["search_page_projection_contract"]["maximum_leads"]
    ):
        raise ValueError("V2.42.48 search results exceed projection capacity")
    if fetch_bytes > int(
        assembly["search_page_projection_contract"]["maximum_page_bytes"]
    ):
        raise ValueError("V2.42.48 fetch bytes exceed projection capacity")
    if model_reasoning_effort not in {"", "low", "medium", "high"}:
        raise ValueError("V2.42.48 model reasoning effort is invalid")
    if model_service_tier not in {"", "auto", "default", "flex", "priority"}:
        raise ValueError("V2.42.48 model service tier is invalid")
    if provider == "tavily_search_api":
        if any(
            (
                search_output,
                search_tools,
                search_input,
                bool(search_context_size),
                bool(search_reasoning_effort),
                bool(search_service_tier),
            )
        ):
            raise ValueError("V2.42.48 Tavily hosted-token settings must be empty")
    elif provider == "azure_responses_web_search":
        if (
            search_input < query_bytes + 4096
            or search_output < 1
            or search_tools < 1
            or search_context_size not in {"low", "medium", "high"}
            or search_reasoning_effort not in {"", "low", "medium", "high"}
            or search_service_tier
            not in {"", "auto", "default", "flex", "priority"}
        ):
            raise ValueError("V2.42.48 Azure hosted-search settings are invalid")
    else:
        if (
            search_input < query_bytes + 4096
            or search_output < 1
            or not 1 <= search_tools <= 64
            or search_context_size
            or search_reasoning_effort
            or search_service_tier
        ):
            raise ValueError("V2.42.48 Anthropic search settings are invalid")

    common = {
        "initial_backoff_milliseconds": initial_backoff_milliseconds,
        "backoff_multiplier": backoff_multiplier,
        "maximum_backoff_milliseconds": maximum_backoff_milliseconds,
        "deadline_margin_milliseconds": deadline_margin_milliseconds,
    }
    model_meter, model_scheduler = _effect_contracts(
        provider_kind="azure_responses_model",
        charge_kind="renderer",
        max_attempts=model_max_attempts,
        timeout_seconds=model_timeout_seconds,
        reserved_input_tokens_per_attempt=model_input,
        reserved_output_tokens_per_attempt=model_output,
        reserved_provider_tool_calls_per_attempt=0,
        **common,
    )
    search_meter, search_scheduler = _effect_contracts(
        provider_kind=provider,
        charge_kind="fanout_execution",
        max_attempts=search_max_attempts,
        timeout_seconds=search_timeout_seconds,
        reserved_input_tokens_per_attempt=search_input,
        reserved_output_tokens_per_attempt=search_output,
        reserved_provider_tool_calls_per_attempt=search_tools,
        **common,
    )
    fetch_meter, fetch_scheduler = _effect_contracts(
        provider_kind="native_http_fetch",
        charge_kind="fanout_execution",
        max_attempts=fetch_max_attempts,
        timeout_seconds=fetch_timeout_seconds,
        reserved_input_tokens_per_attempt=0,
        reserved_output_tokens_per_attempt=0,
        reserved_provider_tool_calls_per_attempt=0,
        **common,
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": CONTRACT_ROLE,
        "policy_id": POLICY_ID,
        "candidate_runtime": True,
        "assembly_contract": assembly,
        "assembly_contract_sha256": assembly["contract_sha256"],
        "search_provider_kind": provider,
        "model_maximum_prompt_utf8_bytes": prompt_bytes,
        "model_maximum_output_tokens": model_output,
        "model_reasoning_effort": model_reasoning_effort,
        "model_service_tier": model_service_tier,
        "model_timeout_seconds": _integer(
            model_timeout_seconds, label="model timeout seconds", minimum=1, maximum=3600
        ),
        "model_max_attempts": _integer(
            model_max_attempts, label="model maximum attempts", minimum=1, maximum=64
        ),
        "model_reserved_input_tokens_per_attempt": model_input,
        "search_maximum_query_utf8_bytes": query_bytes,
        "search_maximum_output_tokens": search_output,
        "search_maximum_provider_tool_calls_per_attempt": search_tools,
        "search_maximum_results": search_results,
        "search_context_size": search_context_size,
        "search_reasoning_effort": search_reasoning_effort,
        "search_service_tier": search_service_tier,
        "search_timeout_seconds": _integer(
            search_timeout_seconds, label="search timeout seconds", minimum=1, maximum=3600
        ),
        "search_max_attempts": _integer(
            search_max_attempts, label="search maximum attempts", minimum=1, maximum=64
        ),
        "search_reserved_input_tokens_per_attempt": search_input,
        "fetch_maximum_response_bytes": fetch_bytes,
        "fetch_timeout_seconds": _integer(
            fetch_timeout_seconds, label="fetch timeout seconds", minimum=1, maximum=3600
        ),
        "fetch_max_attempts": _integer(
            fetch_max_attempts, label="fetch maximum attempts", minimum=1, maximum=64
        ),
        "initial_backoff_milliseconds": _integer(
            initial_backoff_milliseconds,
            label="initial backoff milliseconds",
            minimum=1,
        ),
        "backoff_multiplier": _integer(
            backoff_multiplier,
            label="backoff multiplier",
            minimum=1,
            maximum=1024,
        ),
        "maximum_backoff_milliseconds": _integer(
            maximum_backoff_milliseconds,
            label="maximum backoff milliseconds",
            minimum=1,
        ),
        "deadline_margin_milliseconds": _integer(
            deadline_margin_milliseconds,
            label="deadline margin milliseconds",
            minimum=1,
        ),
        "model_meter_contract": model_meter,
        "model_scheduler_contract": model_scheduler,
        "search_meter_contract": search_meter,
        "search_scheduler_contract": search_scheduler,
        "fetch_meter_contract": fetch_meter,
        "fetch_scheduler_contract": fetch_scheduler,
        "caller_content_free_action_ref_required": True,
        "facade_invocation_derivation_uses_ephemeral_content": False,
        "legacy_runtime_client_surface_implemented": False,
        "search_leads_or_page_text_active_evidence_eligibility_granted": False,
        "active_forward_integration_authorized": False,
        "benchmark_forward_or_evaluator_authorized": False,
    }
    value["contract_sha256"] = object_sha256(value)
    return value


def validate_candidate_client_facade_contract(value: Mapping[str, Any]) -> None:
    contract = _exact(value, keys=CONTRACT_KEYS, label="facade contract")
    try:
        expected = build_candidate_client_facade_contract(
            assembly_contract=contract["assembly_contract"],
            **{
                key: contract[key]
                for key in (
                    "search_provider_kind",
                    "model_maximum_prompt_utf8_bytes",
                    "model_maximum_output_tokens",
                    "model_reasoning_effort",
                    "model_service_tier",
                    "model_timeout_seconds",
                    "model_max_attempts",
                    "model_reserved_input_tokens_per_attempt",
                    "search_maximum_query_utf8_bytes",
                    "search_maximum_output_tokens",
                    "search_maximum_provider_tool_calls_per_attempt",
                    "search_maximum_results",
                    "search_context_size",
                    "search_reasoning_effort",
                    "search_service_tier",
                    "search_timeout_seconds",
                    "search_max_attempts",
                    "search_reserved_input_tokens_per_attempt",
                    "fetch_maximum_response_bytes",
                    "fetch_timeout_seconds",
                    "fetch_max_attempts",
                    "initial_backoff_milliseconds",
                    "backoff_multiplier",
                    "maximum_backoff_milliseconds",
                    "deadline_margin_milliseconds",
                )
            },
        )
    except (KeyError, TypeError, ValueError):
        raise ValueError("V2.42.48 facade contract drifted") from None
    if dict(contract) != expected or not _sealed(contract, key="contract_sha256"):
        raise ValueError("V2.42.48 facade contract drifted")


def derive_candidate_facade_action_ref(
    *,
    task_scope_ref_sha256: str,
    stage_ref_sha256: str,
    operation_kind: str,
    action_ordinal: int,
) -> CandidateFacadeActionRef:
    if not _is_sha256(task_scope_ref_sha256) or not _is_sha256(stage_ref_sha256):
        raise ValueError("V2.42.48 action scope references are invalid")
    if operation_kind not in OPERATION_KINDS:
        raise ValueError("V2.42.48 action operation kind is invalid")
    ordinal = _integer(
        action_ordinal,
        label="action ordinal",
        minimum=1,
        maximum=1_000_000_000,
    )
    payload = {
        "policy_id": POLICY_ID,
        "task_scope_ref_sha256": task_scope_ref_sha256,
        "stage_ref_sha256": stage_ref_sha256,
        "operation_kind": operation_kind,
        "action_ordinal": ordinal,
        "ephemeral_content_used": False,
    }
    return CandidateFacadeActionRef(
        task_scope_ref_sha256=task_scope_ref_sha256,
        stage_ref_sha256=stage_ref_sha256,
        operation_kind=operation_kind,
        action_ordinal=ordinal,
        action_ref_sha256=object_sha256(payload),
    )


def _validated_action_ref(
    action_ref: CandidateFacadeActionRef, *, operation_kind: str
) -> str:
    if type(action_ref) is not CandidateFacadeActionRef:
        raise CandidateClientFacadeError("action reference exact type is invalid")
    try:
        expected = derive_candidate_facade_action_ref(
            task_scope_ref_sha256=action_ref.task_scope_ref_sha256,
            stage_ref_sha256=action_ref.stage_ref_sha256,
            operation_kind=action_ref.operation_kind,
            action_ordinal=action_ref.action_ordinal,
        )
    except ValueError:
        raise CandidateClientFacadeError("action reference drifted") from None
    if action_ref != expected or action_ref.operation_kind != operation_kind:
        raise CandidateClientFacadeError("action reference drifted")
    return action_ref.action_ref_sha256


def _action_ref_mapping(action_ref: CandidateFacadeActionRef) -> dict[str, Any]:
    _validated_action_ref(action_ref, operation_kind=action_ref.operation_kind)
    return {
        "task_scope_ref_sha256": action_ref.task_scope_ref_sha256,
        "stage_ref_sha256": action_ref.stage_ref_sha256,
        "operation_kind": action_ref.operation_kind,
        "action_ordinal": action_ref.action_ordinal,
        "action_ref_sha256": action_ref.action_ref_sha256,
    }


def _validate_action_ref_mapping(
    value: Mapping[str, Any], *, operation_kind: str
) -> CandidateFacadeActionRef:
    mapping = _exact(value, keys=ACTION_REF_KEYS, label="action reference")
    try:
        expected = derive_candidate_facade_action_ref(
            task_scope_ref_sha256=mapping["task_scope_ref_sha256"],
            stage_ref_sha256=mapping["stage_ref_sha256"],
            operation_kind=mapping["operation_kind"],
            action_ordinal=mapping["action_ordinal"],
        )
    except (KeyError, TypeError, ValueError):
        raise ValueError("V2.42.48 action reference drifted") from None
    if (
        mapping["operation_kind"] != operation_kind
        or mapping["action_ref_sha256"] != expected.action_ref_sha256
        or dict(mapping) != _action_ref_mapping(expected)
    ):
        raise ValueError("V2.42.48 action reference drifted")
    return expected


def _invocation_ref(
    *,
    contract: Mapping[str, Any],
    action_ref_sha256: str,
    operation_kind: str,
    provider_kind: str,
) -> str:
    if not _is_sha256(action_ref_sha256):
        raise CandidateClientFacadeError("action reference is not SHA-256")
    return object_sha256(
        {
            "policy_id": POLICY_ID,
            "facade_contract_sha256": contract["contract_sha256"],
            "action_ref_sha256": action_ref_sha256,
            "operation_kind": operation_kind,
            "provider_kind": provider_kind,
            "ephemeral_content_used": False,
        }
    )


def _expected_receipt_shape(
    assembly_receipt: Mapping[str, Any],
) -> tuple[str, str, int, Mapping[str, Any], int]:
    assembly = dict(assembly_receipt)
    validate_candidate_runtime_assembly_receipt(assembly)
    operation = str(assembly["operation_kind"])
    post = dict(assembly["postprocessor_receipt"])
    if operation == "model_json":
        validate_strict_json_parser_receipt(post)
        value_kind = "strict_json_object"
        count = int(post["top_level_member_count"])
    else:
        validate_search_page_projection_receipt(post)
        value_kind = (
            "untrusted_search_leads"
            if operation == "search_leads"
            else "untrusted_page_text"
        )
        count = int(post["projected_item_count"])
    scheduler = post["scheduler_execution_receipt"]
    parent = scheduler["parent_execution_receipt"]
    return (
        operation,
        value_kind,
        count,
        parent["settlement_cost"],
        int(scheduler["attempt_count"]),
    )


def _facade_receipt(
    *,
    contract: Mapping[str, Any],
    action_ref: CandidateFacadeActionRef,
    invocation_ref_sha256: str,
    assembly_receipt: Mapping[str, Any],
    requested_value_item_limit: int | None,
    returned_value_item_count: int,
) -> dict[str, Any]:
    assembly = _clone(dict(assembly_receipt))
    operation, value_kind, count, settlement, attempts = _expected_receipt_shape(
        assembly
    )
    returned = _integer(
        returned_value_item_count,
        label="returned value item count",
    )
    if requested_value_item_limit is None:
        limit = None
        if returned != count:
            raise ValueError("V2.42.48 unbounded facade value count drifted")
    else:
        limit = _integer(
            requested_value_item_limit,
            label="requested value item limit",
            minimum=1,
        )
        if returned != min(count, limit):
            raise ValueError("V2.42.48 bounded facade value count drifted")
    provider = str(assembly["provider_kind"])
    action = _action_ref_mapping(action_ref)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "candidate_runtime": True,
        "operation_kind": operation,
        "provider_kind": provider,
        "value_kind": value_kind,
        "assembly_value_item_count": count,
        "requested_value_item_limit": limit,
        "returned_value_item_count": returned,
        "facade_value_truncation_applied": returned < count,
        "action_ref": action,
        "action_ref_sha256": action_ref.action_ref_sha256,
        "invocation_ref_sha256": invocation_ref_sha256,
        "facade_contract": _clone(dict(contract)),
        "facade_contract_sha256": contract["contract_sha256"],
        "assembly_receipt": assembly,
        "assembly_receipt_sha256": assembly["assembly_receipt_sha256"],
        "meter_contract_sha256": assembly["meter_contract_sha256"],
        "scheduler_contract_sha256": assembly["scheduler_contract_sha256"],
        "attempt_count": attempts,
        "settlement_cost": _clone(settlement),
        "caller_content_free_action_ref_required": True,
        "caller_action_ref_semantic_independence_verified": False,
        "facade_invocation_derivation_used_ephemeral_content": False,
        "exact_adapter_and_assembly_type_enforced": True,
        "frozen_provider_meter_and_deadline_contracts_used": True,
        "legacy_runtime_client_surface_implemented": False,
        "search_leads_or_page_text_active_evidence_eligibility_granted": False,
        "raw_prompt_query_url_provider_value_or_projected_output_entered_receipt": False,
        "facade_created_new_ephemeral_content_hash": False,
        "parent_provider_response_reference_retained": True,
        "credential_environment_or_keyring_read": False,
        "benchmark_or_evaluator_metadata_used_for_routing": False,
        "adapter_code_identity_independently_attested": False,
        "schema_resealing_without_secret_cryptographically_excluded": False,
        "active_forward_integration_authorized": False,
        "benchmark_forward_or_evaluator_authorized": False,
    }
    value["facade_receipt_sha256"] = object_sha256(value)
    validate_candidate_client_facade_receipt(value)
    return value


def validate_candidate_client_facade_receipt(value: Mapping[str, Any]) -> None:
    receipt = _exact(value, keys=RECEIPT_KEYS, label="facade receipt")
    contract = dict(receipt["facade_contract"])
    assembly = dict(receipt["assembly_receipt"])
    validate_candidate_client_facade_contract(contract)
    operation, value_kind, count, settlement, attempts = _expected_receipt_shape(
        assembly
    )
    provider = str(assembly["provider_kind"])
    action = _validate_action_ref_mapping(
        receipt["action_ref"], operation_kind=operation
    )
    expected_provider = (
        "azure_responses_model"
        if operation == "model_json"
        else "native_http_fetch"
        if operation == "fetched_page"
        else str(contract["search_provider_kind"])
    )
    expected_invocation = _invocation_ref(
        contract=contract,
        action_ref_sha256=action.action_ref_sha256,
        operation_kind=operation,
        provider_kind=provider,
    )
    expected_meter = contract[
        "model_meter_contract"
        if operation == "model_json"
        else "fetch_meter_contract"
        if operation == "fetched_page"
        else "search_meter_contract"
    ]
    expected_scheduler = contract[
        "model_scheduler_contract"
        if operation == "model_json"
        else "fetch_scheduler_contract"
        if operation == "fetched_page"
        else "search_scheduler_contract"
    ]
    if (
        receipt.get("artifact_version") != 1
        or receipt.get("role") != RECEIPT_ROLE
        or receipt.get("policy_id") != POLICY_ID
        or receipt.get("candidate_runtime") is not True
        or receipt.get("operation_kind") != operation
        or receipt.get("provider_kind") != provider
        or provider != expected_provider
        or receipt.get("value_kind") != value_kind
        or isinstance(receipt.get("assembly_value_item_count"), bool)
        or not isinstance(receipt.get("assembly_value_item_count"), int)
        or receipt.get("assembly_value_item_count") != count
        or isinstance(receipt.get("returned_value_item_count"), bool)
        or not isinstance(receipt.get("returned_value_item_count"), int)
        or receipt["returned_value_item_count"] < 0
        or receipt.get("returned_value_item_count")
        != min(
            count,
            receipt.get("requested_value_item_limit")
            if isinstance(receipt.get("requested_value_item_limit"), int)
            and not isinstance(receipt.get("requested_value_item_limit"), bool)
            and receipt["requested_value_item_limit"] >= 1
            else count,
        )
        or operation == "search_leads"
        and (
            isinstance(receipt.get("requested_value_item_limit"), bool)
            or not isinstance(receipt.get("requested_value_item_limit"), int)
            or receipt["requested_value_item_limit"] < 1
            or receipt["requested_value_item_limit"]
            > contract["search_maximum_results"]
        )
        or operation != "search_leads"
        and receipt.get("requested_value_item_limit") is not None
        or receipt.get("facade_value_truncation_applied")
        is not (receipt.get("returned_value_item_count") < count)
        or receipt.get("action_ref_sha256") != action.action_ref_sha256
        or receipt.get("invocation_ref_sha256") != expected_invocation
        or assembly.get("invocation_ref_sha256") != expected_invocation
        or receipt.get("facade_contract_sha256") != contract["contract_sha256"]
        or receipt.get("assembly_receipt_sha256")
        != assembly["assembly_receipt_sha256"]
        or receipt.get("meter_contract_sha256")
        != expected_meter["contract_sha256"]
        or receipt.get("scheduler_contract_sha256")
        != expected_scheduler["contract_sha256"]
        or receipt.get("attempt_count") != attempts
        or receipt.get("settlement_cost") != settlement
        or receipt.get("caller_content_free_action_ref_required") is not True
        or receipt.get("caller_action_ref_semantic_independence_verified")
        is not False
        or receipt.get("facade_invocation_derivation_used_ephemeral_content")
        is not False
        or receipt.get("exact_adapter_and_assembly_type_enforced") is not True
        or receipt.get("frozen_provider_meter_and_deadline_contracts_used")
        is not True
        or receipt.get("legacy_runtime_client_surface_implemented") is not False
        or receipt.get(
            "search_leads_or_page_text_active_evidence_eligibility_granted"
        )
        is not False
        or receipt.get(
            "raw_prompt_query_url_provider_value_or_projected_output_entered_receipt"
        )
        is not False
        or receipt.get("facade_created_new_ephemeral_content_hash") is not False
        or receipt.get("parent_provider_response_reference_retained") is not True
        or receipt.get("credential_environment_or_keyring_read") is not False
        or receipt.get("benchmark_or_evaluator_metadata_used_for_routing")
        is not False
        or receipt.get("adapter_code_identity_independently_attested") is not False
        or receipt.get(
            "schema_resealing_without_secret_cryptographically_excluded"
        )
        is not False
        or receipt.get("active_forward_integration_authorized") is not False
        or receipt.get("benchmark_forward_or_evaluator_authorized") is not False
        or not _sealed(receipt, key="facade_receipt_sha256")
    ):
        raise ValueError("V2.42.48 facade receipt drifted")


def _utf8_size(value: str, *, label: str) -> int:
    if not isinstance(value, str) or not value:
        raise CandidateClientFacadeError(f"{label} is empty or invalid")
    try:
        return len(value.encode("utf-8"))
    except UnicodeEncodeError:
        raise CandidateClientFacadeError(f"{label} is not valid UTF-8 text") from None


def _search_adapter_state(adapter: Any) -> dict[str, Any]:
    if type(adapter) is TavilySearchSingleAttemptAdapter:
        return {
            "search_endpoint": adapter._endpoint,
            "search_timeout_seconds": adapter._timeout_seconds,
            "search_model": None,
            "search_anthropic_version": None,
        }
    if type(adapter) is AzureHostedSearchSingleAttemptAdapter:
        return {
            "search_endpoint": adapter._endpoint,
            "search_timeout_seconds": adapter._timeout_seconds,
            "search_model": adapter._model,
            "search_anthropic_version": None,
        }
    if type(adapter) is AnthropicServerSearchSingleAttemptAdapter:
        return {
            "search_endpoint": adapter._endpoint,
            "search_timeout_seconds": adapter._timeout_seconds,
            "search_model": adapter._model,
            "search_anthropic_version": adapter._anthropic_version,
        }
    raise CandidateClientFacadeError("search adapter exact type is invalid")


class CandidateClientFacade:
    """Freeze provider accounting while preserving typed quarantine values."""

    def __init__(
        self,
        *,
        assembly: CandidateRuntimeAssembly,
        facade_contract: Mapping[str, Any],
        model_adapter: AzureResponsesSingleAttemptAdapter,
        search_adapter: TavilySearchSingleAttemptAdapter
        | AzureHostedSearchSingleAttemptAdapter
        | AnthropicServerSearchSingleAttemptAdapter,
        fetch_adapter: PinnedNativeHttpFetchAdapter,
    ) -> None:
        if type(assembly) is not CandidateRuntimeAssembly:
            raise ValueError("V2.42.48 assembly exact type is invalid")
        contract = _clone(dict(facade_contract))
        validate_candidate_client_facade_contract(contract)
        expected_search = SEARCH_PROVIDER_ADAPTERS[contract["search_provider_kind"]]
        if (
            type(model_adapter) is not AzureResponsesSingleAttemptAdapter
            or type(search_adapter) is not expected_search
            or type(fetch_adapter) is not PinnedNativeHttpFetchAdapter
        ):
            raise ValueError("V2.42.48 adapter exact type is invalid")
        if assembly._contract != contract["assembly_contract"]:
            raise ValueError("V2.42.48 assembly contract binding drifted")
        if (
            model_adapter._timeout_seconds != contract["model_timeout_seconds"]
            or search_adapter._timeout_seconds != contract["search_timeout_seconds"]
            or fetch_adapter._timeout_seconds != contract["fetch_timeout_seconds"]
            or fetch_adapter._max_response_bytes
            != contract["fetch_maximum_response_bytes"]
        ):
            raise ValueError("V2.42.48 adapter limits drifted")
        self._assembly = assembly
        self._contract = contract
        self._model_adapter = model_adapter
        self._search_adapter = search_adapter
        self._fetch_adapter = fetch_adapter
        self._adapter_state = {
            "model_endpoint": model_adapter._endpoint,
            "model_name": model_adapter._model,
            "model_timeout_seconds": model_adapter._timeout_seconds,
            **_search_adapter_state(search_adapter),
            "fetch_timeout_seconds": fetch_adapter._timeout_seconds,
            "fetch_maximum_response_bytes": fetch_adapter._max_response_bytes,
        }
        self._identity = {
            "assembly": id(assembly),
            "scheduler": id(assembly._scheduler),
            "coordinator": id(assembly._scheduler._coordinator),
            "monotonic_ns": id(assembly._scheduler._monotonic_ns),
            "sleeper": id(assembly._scheduler._sleeper),
            "model_adapter": id(model_adapter),
            "model_post": id(model_adapter._post),
            "search_adapter": id(search_adapter),
            "search_post": id(search_adapter._post),
            "fetch_adapter": id(fetch_adapter),
            "fetch_resolve": id(fetch_adapter._resolve),
            "fetch_pool_factory": id(fetch_adapter._pool_factory),
        }
        if type(search_adapter) is TavilySearchSingleAttemptAdapter:
            self._identity["search_credentials"] = id(search_adapter._credentials)
        elif type(search_adapter) is AnthropicServerSearchSingleAttemptAdapter:
            self._identity["search_credential"] = id(search_adapter._credential)

    def _snapshot_contract(self) -> dict[str, Any]:
        contract = _clone(dict(self._contract))
        validate_candidate_client_facade_contract(contract)
        expected_search = SEARCH_PROVIDER_ADAPTERS[contract["search_provider_kind"]]
        current_identity = {
            "assembly": id(self._assembly),
            "scheduler": id(self._assembly._scheduler),
            "coordinator": id(self._assembly._scheduler._coordinator),
            "monotonic_ns": id(self._assembly._scheduler._monotonic_ns),
            "sleeper": id(self._assembly._scheduler._sleeper),
            "model_adapter": id(self._model_adapter),
            "model_post": id(self._model_adapter._post),
            "search_adapter": id(self._search_adapter),
            "search_post": id(self._search_adapter._post),
            "fetch_adapter": id(self._fetch_adapter),
            "fetch_resolve": id(self._fetch_adapter._resolve),
            "fetch_pool_factory": id(self._fetch_adapter._pool_factory),
        }
        if type(self._search_adapter) is TavilySearchSingleAttemptAdapter:
            current_identity["search_credentials"] = id(
                self._search_adapter._credentials
            )
        elif type(self._search_adapter) is AnthropicServerSearchSingleAttemptAdapter:
            current_identity["search_credential"] = id(
                self._search_adapter._credential
            )
        current_adapter_state = {
            "model_endpoint": self._model_adapter._endpoint,
            "model_name": self._model_adapter._model,
            "model_timeout_seconds": self._model_adapter._timeout_seconds,
            **_search_adapter_state(self._search_adapter),
            "fetch_timeout_seconds": self._fetch_adapter._timeout_seconds,
            "fetch_maximum_response_bytes": self._fetch_adapter._max_response_bytes,
        }
        if (
            type(self._assembly) is not CandidateRuntimeAssembly
            or self._assembly._contract != contract["assembly_contract"]
            or type(self._model_adapter) is not AzureResponsesSingleAttemptAdapter
            or type(self._search_adapter) is not expected_search
            or type(self._fetch_adapter) is not PinnedNativeHttpFetchAdapter
            or self._model_adapter._timeout_seconds
            != contract["model_timeout_seconds"]
            or self._search_adapter._timeout_seconds
            != contract["search_timeout_seconds"]
            or self._fetch_adapter._timeout_seconds
            != contract["fetch_timeout_seconds"]
            or self._fetch_adapter._max_response_bytes
            != contract["fetch_maximum_response_bytes"]
            or expected_search is TavilySearchSingleAttemptAdapter
            and len(self._search_adapter._credentials)
            < contract["search_max_attempts"]
            or current_identity != self._identity
            or current_adapter_state != self._adapter_state
        ):
            raise CandidateClientFacadeError(
                "facade assembly or adapter binding drifted"
            )
        return contract

    def run_model_json(
        self,
        *,
        action_ref: CandidateFacadeActionRef,
        system: str,
        user: str,
        max_output_tokens: int,
    ) -> CandidateClientFacadeResult:
        contract = self._snapshot_contract()
        action_ref_sha256 = _validated_action_ref(
            action_ref, operation_kind="model_json"
        )
        size = _utf8_size(system, label="model system prompt") + _utf8_size(
            user, label="model user prompt"
        )
        output = _integer(
            max_output_tokens,
            label="model requested output tokens",
            minimum=1,
        )
        if (
            size > contract["model_maximum_prompt_utf8_bytes"]
            or output > contract["model_maximum_output_tokens"]
        ):
            raise CandidateClientFacadeError("model request exceeds facade limits")
        provider = "azure_responses_model"
        invocation = _invocation_ref(
            contract=contract,
            action_ref_sha256=action_ref_sha256,
            operation_kind="model_json",
            provider_kind=provider,
        )
        result: CandidateRuntimeAssemblyResult = type(self._assembly).run_model_json(
            self._assembly,
            adapter=self._model_adapter,
            request=AzureResponsesRequest(
                system=system,
                user=user,
                max_output_tokens=output,
                json_mode=True,
                reasoning_effort=contract["model_reasoning_effort"],
                service_tier=contract["model_service_tier"],
            ),
            meter_contract=contract["model_meter_contract"],
            scheduler_contract=contract["model_scheduler_contract"],
            invocation_ref_sha256=invocation,
        )
        receipt = _facade_receipt(
            contract=contract,
            action_ref=action_ref,
            invocation_ref_sha256=invocation,
            assembly_receipt=result.receipt,
            requested_value_item_limit=None,
            returned_value_item_count=len(result.value),
        )
        return CandidateClientFacadeResult(receipt=receipt, value=result.value)

    def run_search_leads(
        self,
        *,
        action_ref: CandidateFacadeActionRef,
        query: str,
        max_results: int,
    ) -> CandidateClientFacadeResult:
        contract = self._snapshot_contract()
        action_ref_sha256 = _validated_action_ref(
            action_ref, operation_kind="search_leads"
        )
        query_size = _utf8_size(query, label="search query")
        results = _integer(
            max_results,
            label="requested search results",
            minimum=1,
        )
        if (
            query_size > contract["search_maximum_query_utf8_bytes"]
            or results > contract["search_maximum_results"]
        ):
            raise CandidateClientFacadeError("search request exceeds facade limits")
        provider = str(contract["search_provider_kind"])
        invocation = _invocation_ref(
            contract=contract,
            action_ref_sha256=action_ref_sha256,
            operation_kind="search_leads",
            provider_kind=provider,
        )
        if provider == "tavily_search_api":
            request: Any = TavilySearchRequest(
                query=query,
                max_results=results,
                search_depth="advanced",
                include_raw_content=False,
                include_answer=False,
            )
        elif provider == "azure_responses_web_search":
            request = AzureHostedSearchRequest(
                queries=(query,),
                max_output_tokens=contract["search_maximum_output_tokens"],
                search_context_size=contract["search_context_size"],
                reasoning_effort=contract["search_reasoning_effort"],
                service_tier=contract["search_service_tier"],
            )
        else:
            request = AnthropicServerSearchRequest(
                query=query,
                max_output_tokens=contract["search_maximum_output_tokens"],
                max_uses=contract[
                    "search_maximum_provider_tool_calls_per_attempt"
                ],
            )
        result: CandidateRuntimeAssemblyResult = type(
            self._assembly
        ).run_search_leads(
            self._assembly,
            adapter=self._search_adapter,
            request=request,
            meter_contract=contract["search_meter_contract"],
            scheduler_contract=contract["search_scheduler_contract"],
            invocation_ref_sha256=invocation,
        )
        if not isinstance(result.value, tuple) or any(
            type(item) is not SearchLeadProjection for item in result.value
        ):
            raise CandidateClientFacadeError("search projection type drifted")
        returned_value = result.value[:results]
        receipt = _facade_receipt(
            contract=contract,
            action_ref=action_ref,
            invocation_ref_sha256=invocation,
            assembly_receipt=result.receipt,
            requested_value_item_limit=results,
            returned_value_item_count=len(returned_value),
        )
        return CandidateClientFacadeResult(receipt=receipt, value=returned_value)

    def run_fetched_page(
        self,
        *,
        action_ref: CandidateFacadeActionRef,
        url: str,
    ) -> CandidateClientFacadeResult:
        contract = self._snapshot_contract()
        action_ref_sha256 = _validated_action_ref(
            action_ref, operation_kind="fetched_page"
        )
        _utf8_size(url, label="fetch URL")
        provider = "native_http_fetch"
        invocation = _invocation_ref(
            contract=contract,
            action_ref_sha256=action_ref_sha256,
            operation_kind="fetched_page",
            provider_kind=provider,
        )
        result: CandidateRuntimeAssemblyResult = type(
            self._assembly
        ).run_fetched_page(
            self._assembly,
            adapter=self._fetch_adapter,
            request=NativeHttpFetchRequest(url=url),
            meter_contract=contract["fetch_meter_contract"],
            scheduler_contract=contract["fetch_scheduler_contract"],
            invocation_ref_sha256=invocation,
        )
        if type(result.value) is not PageTextProjection:
            raise CandidateClientFacadeError("page projection type drifted")
        receipt = _facade_receipt(
            contract=contract,
            action_ref=action_ref,
            invocation_ref_sha256=invocation,
            assembly_receipt=result.receipt,
            requested_value_item_limit=None,
            returned_value_item_count=1,
        )
        return CandidateClientFacadeResult(receipt=receipt, value=result.value)
