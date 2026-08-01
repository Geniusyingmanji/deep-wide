"""Typed assembly for the isolated durable provider-effect candidates.

V2.42.35--46 provide accounting, durable effect ordering, checkpoint
deadlines, five single-attempt adapters, and strict post-settlement parsers as
separate candidates.  This module composes those pieces without exposing a
caller-supplied callback interface.  It accepts only exact known adapter and
request types, executes every effect through one V2.42.43 scheduler, and then
routes the settled result to V2.42.44 model JSON parsing or V2.42.46
search/page projection.

The assembly is still isolated and is not imported by active clients, runtime,
runner, launcher, benchmark, or evaluator code.  It neither constructs
credentials nor reads environment configuration.  Its receipt embeds only the
content-free postprocessor graph; parsed JSON, leads, URLs, page text, prompts,
queries, credentials, and provider values remain ephemeral.  Exact Python type
checks constrain this implementation boundary but do not provide independent
attestation of adapter code identity or exclude unkeyed receipt resealing.
"""

from __future__ import annotations

import copy
import dataclasses
from typing import Any, Mapping

from deepwide_agent.v24232_webswarm_total_budget import object_sha256
from deepwide_agent.v24234_provider_cost_meter import validate_provider_meter_contract
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
    RetryDeadlineEffectScheduler,
    RetryDeadlineExecutionResult,
    validate_retry_deadline_contract,
)
from deepwide_agent.v24244_strict_json_parser_boundary import (
    StrictJsonParseResult,
    parse_settled_model_json,
    validate_strict_json_parser_contract,
    validate_strict_json_parser_receipt,
)
from deepwide_agent.v24245_pinned_native_http_fetch import (
    NativeHttpFetchRequest,
    PinnedNativeHttpFetchAdapter,
)
from deepwide_agent.v24246_search_page_projection import (
    SearchPageProjectionResult,
    project_settled_fetched_page,
    project_settled_search_leads,
    validate_search_page_projection_contract,
    validate_search_page_projection_receipt,
)


POLICY_ID = "v24247_candidate_runtime_assembly_v1"
CONTRACT_ROLE = "v24247_candidate_runtime_assembly_contract"
RECEIPT_ROLE = "v24247_candidate_runtime_assembly_receipt"

PRODUCTION_PACKAGE_AUTHORIZED = False
ACTIVE_FORWARD_INTEGRATION_AUTHORIZED = False
ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED = False
EXTERNAL_SIDE_EFFECT_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
DEV64_OR_EXACT220_LAUNCH_AUTHORIZED = False
SHARED_API_LEASE_ACQUIRE_AUTHORIZED = False
LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED = False

KNOWN_ADAPTER_EXACT_TYPE_ENFORCEMENT_IMPLEMENTED = True
KNOWN_REQUEST_EXACT_TYPE_ENFORCEMENT_IMPLEMENTED = True
CALLER_SUPPLIED_CALLBACK_INTERFACE_IMPLEMENTED = False
ALL_EFFECTS_ROUTED_THROUGH_DURABLE_DEADLINE_SCHEDULER = True
POST_SETTLEMENT_TYPED_PROCESSING_IMPLEMENTED = True
ADAPTER_CODE_IDENTITY_INDEPENDENTLY_ATTESTED = False
SCHEMA_RESEALING_WITHOUT_SECRET_CRYPTOGRAPHICALLY_EXCLUDED = False

CONTRACT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "candidate_runtime",
        "model_parser_contract",
        "model_parser_contract_sha256",
        "search_page_projection_contract",
        "search_page_projection_contract_sha256",
        "operation_adapter_request_provider_map",
        "known_adapter_exact_type_required",
        "known_request_exact_type_required",
        "caller_supplied_callback_authorized",
        "all_effects_routed_through_durable_deadline_scheduler",
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
        "adapter_kind",
        "request_kind",
        "provider_kind",
        "assembly_contract",
        "assembly_contract_sha256",
        "invocation_ref_sha256",
        "meter_contract_sha256",
        "scheduler_contract_sha256",
        "scheduler_execution_receipt_sha256",
        "parent_durable_execution_receipt_sha256",
        "postprocessor_kind",
        "postprocessor_receipt",
        "postprocessor_receipt_sha256",
        "known_adapter_exact_type_enforced",
        "known_request_exact_type_enforced",
        "caller_supplied_callback_accepted",
        "all_effects_routed_through_durable_deadline_scheduler",
        "post_settlement_typed_processing",
        "raw_provider_value_or_projected_output_entered_receipt",
        "prompt_query_search_lead_url_page_text_or_parsed_json_present_in_receipt",
        "credential_environment_or_keyring_read",
        "benchmark_or_evaluator_metadata_used_for_routing",
        "adapter_code_identity_independently_attested",
        "schema_resealing_without_secret_cryptographically_excluded",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "assembly_receipt_sha256",
    }
)
OPERATION_MAP = (
    {
        "operation_kind": "model_json",
        "adapter_kind": "AzureResponsesSingleAttemptAdapter",
        "request_kind": "AzureResponsesRequest",
        "provider_kind": "azure_responses_model",
        "effect_kind": "model_request",
        "postprocessor_kind": "strict_model_json",
    },
    {
        "operation_kind": "search_leads",
        "adapter_kind": "TavilySearchSingleAttemptAdapter",
        "request_kind": "TavilySearchRequest",
        "provider_kind": "tavily_search_api",
        "effect_kind": "search_request",
        "postprocessor_kind": "untrusted_search_leads",
    },
    {
        "operation_kind": "search_leads",
        "adapter_kind": "AzureHostedSearchSingleAttemptAdapter",
        "request_kind": "AzureHostedSearchRequest",
        "provider_kind": "azure_responses_web_search",
        "effect_kind": "hosted_web_search",
        "postprocessor_kind": "untrusted_search_leads",
    },
    {
        "operation_kind": "search_leads",
        "adapter_kind": "AnthropicServerSearchSingleAttemptAdapter",
        "request_kind": "AnthropicServerSearchRequest",
        "provider_kind": "anthropic_server_web_search",
        "effect_kind": "hosted_web_search",
        "postprocessor_kind": "untrusted_search_leads",
    },
    {
        "operation_kind": "fetched_page",
        "adapter_kind": "PinnedNativeHttpFetchAdapter",
        "request_kind": "NativeHttpFetchRequest",
        "provider_kind": "native_http_fetch",
        "effect_kind": "fetch_request",
        "postprocessor_kind": "untrusted_page_text",
    },
)


class CandidateRuntimeAssemblyError(ValueError):
    """Sanitized assembly rejection without ephemeral content."""


@dataclasses.dataclass(frozen=True)
class CandidateRuntimeAssemblyResult:
    receipt: Mapping[str, Any]
    value: Any


def _clone(value: Any) -> Any:
    return copy.deepcopy(value)


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _exact(
    value: Mapping[str, Any], *, keys: frozenset[str], label: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"V2.42.47 {label} schema is not exact")
    return value


def _sealed(value: Mapping[str, Any], *, key: str) -> bool:
    seal = value.get(key)
    if not _is_sha256(seal):
        return False
    unsigned = dict(value)
    unsigned.pop(key)
    return seal == object_sha256(unsigned)


def build_candidate_runtime_assembly_contract(
    *,
    model_parser_contract: Mapping[str, Any],
    search_page_projection_contract: Mapping[str, Any],
) -> dict[str, Any]:
    parser = _clone(dict(model_parser_contract))
    projection = _clone(dict(search_page_projection_contract))
    validate_strict_json_parser_contract(parser)
    validate_search_page_projection_contract(projection)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": CONTRACT_ROLE,
        "policy_id": POLICY_ID,
        "candidate_runtime": True,
        "model_parser_contract": parser,
        "model_parser_contract_sha256": parser["contract_sha256"],
        "search_page_projection_contract": projection,
        "search_page_projection_contract_sha256": projection[
            "contract_sha256"
        ],
        "operation_adapter_request_provider_map": _clone(list(OPERATION_MAP)),
        "known_adapter_exact_type_required": True,
        "known_request_exact_type_required": True,
        "caller_supplied_callback_authorized": False,
        "all_effects_routed_through_durable_deadline_scheduler": True,
        "active_forward_integration_authorized": False,
        "benchmark_forward_or_evaluator_authorized": False,
    }
    value["contract_sha256"] = object_sha256(value)
    return value


def validate_candidate_runtime_assembly_contract(value: Mapping[str, Any]) -> None:
    contract = _exact(value, keys=CONTRACT_KEYS, label="assembly contract")
    try:
        expected = build_candidate_runtime_assembly_contract(
            model_parser_contract=contract["model_parser_contract"],
            search_page_projection_contract=contract[
                "search_page_projection_contract"
            ],
        )
    except (KeyError, TypeError, ValueError):
        raise ValueError("V2.42.47 assembly contract drifted") from None
    if dict(contract) != expected or not _sealed(contract, key="contract_sha256"):
        raise ValueError("V2.42.47 assembly contract drifted")


def _mapping(
    *, operation_kind: str, adapter_kind: str
) -> Mapping[str, str]:
    matches = [
        row
        for row in OPERATION_MAP
        if row["operation_kind"] == operation_kind
        and row["adapter_kind"] == adapter_kind
    ]
    if len(matches) != 1:
        raise CandidateRuntimeAssemblyError("adapter is outside the operation map")
    return matches[0]


def _postprocessor_graph(
    *, operation_kind: str, receipt: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    post = _clone(dict(receipt))
    if operation_kind == "model_json":
        validate_strict_json_parser_receipt(post)
        scheduler = post["scheduler_execution_receipt"]
        post_sha = post["parser_receipt_sha256"]
        post_kind = "strict_model_json"
    else:
        validate_search_page_projection_receipt(post)
        scheduler = post["scheduler_execution_receipt"]
        post_sha = post["projection_receipt_sha256"]
        post_kind = post["projection_kind"]
    return post, scheduler, post_sha, post_kind


def _assembly_receipt(
    *,
    contract: Mapping[str, Any],
    operation_kind: str,
    adapter_kind: str,
    request_kind: str,
    meter_contract: Mapping[str, Any],
    scheduler_contract: Mapping[str, Any],
    invocation_ref_sha256: str,
    postprocessor_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    mapping = _mapping(
        operation_kind=operation_kind,
        adapter_kind=adapter_kind,
    )
    post, scheduler, post_sha, post_kind = _postprocessor_graph(
        operation_kind=operation_kind,
        receipt=postprocessor_receipt,
    )
    parent = scheduler["parent_execution_receipt"]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "candidate_runtime": True,
        "operation_kind": operation_kind,
        "adapter_kind": adapter_kind,
        "request_kind": request_kind,
        "provider_kind": mapping["provider_kind"],
        "assembly_contract": _clone(dict(contract)),
        "assembly_contract_sha256": contract["contract_sha256"],
        "invocation_ref_sha256": invocation_ref_sha256,
        "meter_contract_sha256": meter_contract["contract_sha256"],
        "scheduler_contract_sha256": scheduler_contract["contract_sha256"],
        "scheduler_execution_receipt_sha256": scheduler[
            "execution_receipt_sha256"
        ],
        "parent_durable_execution_receipt_sha256": parent[
            "execution_receipt_sha256"
        ],
        "postprocessor_kind": post_kind,
        "postprocessor_receipt": post,
        "postprocessor_receipt_sha256": post_sha,
        "known_adapter_exact_type_enforced": True,
        "known_request_exact_type_enforced": True,
        "caller_supplied_callback_accepted": False,
        "all_effects_routed_through_durable_deadline_scheduler": True,
        "post_settlement_typed_processing": True,
        "raw_provider_value_or_projected_output_entered_receipt": False,
        "prompt_query_search_lead_url_page_text_or_parsed_json_present_in_receipt": False,
        "credential_environment_or_keyring_read": False,
        "benchmark_or_evaluator_metadata_used_for_routing": False,
        "adapter_code_identity_independently_attested": False,
        "schema_resealing_without_secret_cryptographically_excluded": False,
        "active_forward_integration_authorized": False,
        "benchmark_forward_or_evaluator_authorized": False,
    }
    value["assembly_receipt_sha256"] = object_sha256(value)
    validate_candidate_runtime_assembly_receipt(value)
    return value


def validate_candidate_runtime_assembly_receipt(value: Mapping[str, Any]) -> None:
    receipt = _exact(value, keys=RECEIPT_KEYS, label="assembly receipt")
    contract = dict(receipt["assembly_contract"])
    validate_candidate_runtime_assembly_contract(contract)
    operation = receipt.get("operation_kind")
    adapter = receipt.get("adapter_kind")
    request = receipt.get("request_kind")
    mapping = _mapping(operation_kind=str(operation), adapter_kind=str(adapter))
    post, scheduler, post_sha, post_kind = _postprocessor_graph(
        operation_kind=str(operation),
        receipt=receipt["postprocessor_receipt"],
    )
    parent = scheduler["parent_execution_receipt"]
    meter = parent["meter_contract"]
    scheduler_contract = scheduler["scheduler_contract"]
    if (
        receipt.get("artifact_version") != 1
        or receipt.get("role") != RECEIPT_ROLE
        or receipt.get("policy_id") != POLICY_ID
        or receipt.get("candidate_runtime") is not True
        or request != mapping["request_kind"]
        or receipt.get("provider_kind") != mapping["provider_kind"]
        or meter.get("provider_kind") != mapping["provider_kind"]
        or meter.get("effect_kind") != mapping["effect_kind"]
        or post_kind != mapping["postprocessor_kind"]
        or receipt.get("assembly_contract_sha256") != contract["contract_sha256"]
        or receipt.get("invocation_ref_sha256")
        != scheduler.get("invocation_ref_sha256")
        or receipt.get("meter_contract_sha256") != meter["contract_sha256"]
        or receipt.get("scheduler_contract_sha256")
        != scheduler_contract["contract_sha256"]
        or receipt.get("scheduler_execution_receipt_sha256")
        != scheduler["execution_receipt_sha256"]
        or receipt.get("parent_durable_execution_receipt_sha256")
        != parent["execution_receipt_sha256"]
        or receipt.get("postprocessor_receipt_sha256") != post_sha
        or post != receipt["postprocessor_receipt"]
        or operation == "model_json"
        and post["parser_contract_sha256"]
        != contract["model_parser_contract_sha256"]
        or operation in {"search_leads", "fetched_page"}
        and post["projection_contract_sha256"]
        != contract["search_page_projection_contract_sha256"]
        or receipt.get("known_adapter_exact_type_enforced") is not True
        or receipt.get("known_request_exact_type_enforced") is not True
        or receipt.get("caller_supplied_callback_accepted") is not False
        or receipt.get("all_effects_routed_through_durable_deadline_scheduler")
        is not True
        or receipt.get("post_settlement_typed_processing") is not True
        or receipt.get("raw_provider_value_or_projected_output_entered_receipt")
        is not False
        or receipt.get(
            "prompt_query_search_lead_url_page_text_or_parsed_json_present_in_receipt"
        )
        is not False
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
        or not _sealed(receipt, key="assembly_receipt_sha256")
    ):
        raise ValueError("V2.42.47 assembly receipt drifted")


class CandidateRuntimeAssembly:
    """Execute only known typed adapters through one durable scheduler."""

    def __init__(
        self,
        *,
        scheduler: RetryDeadlineEffectScheduler,
        assembly_contract: Mapping[str, Any],
    ) -> None:
        if type(scheduler) is not RetryDeadlineEffectScheduler:
            raise ValueError("V2.42.47 scheduler exact type is invalid")
        contract = _clone(dict(assembly_contract))
        validate_candidate_runtime_assembly_contract(contract)
        self._scheduler = scheduler
        self._contract = contract

    def _execute(
        self,
        *,
        operation_kind: str,
        adapter: Any,
        request: Any,
        meter_contract: Mapping[str, Any],
        scheduler_contract: Mapping[str, Any],
        invocation_ref_sha256: str,
    ) -> RetryDeadlineExecutionResult:
        exact_pairs = {
            ("model_json", AzureResponsesSingleAttemptAdapter): AzureResponsesRequest,
            ("search_leads", TavilySearchSingleAttemptAdapter): TavilySearchRequest,
            (
                "search_leads",
                AzureHostedSearchSingleAttemptAdapter,
            ): AzureHostedSearchRequest,
            (
                "search_leads",
                AnthropicServerSearchSingleAttemptAdapter,
            ): AnthropicServerSearchRequest,
            ("fetched_page", PinnedNativeHttpFetchAdapter): NativeHttpFetchRequest,
        }
        expected_request_type = exact_pairs.get((operation_kind, type(adapter)))
        if expected_request_type is None or type(request) is not expected_request_type:
            raise CandidateRuntimeAssemblyError(
                "adapter or request is outside the exact operation map"
            )
        meter = _clone(dict(meter_contract))
        schedule = _clone(dict(scheduler_contract))
        validate_provider_meter_contract(meter)
        validate_retry_deadline_contract(schedule, meter_contract=meter)
        mapping = _mapping(
            operation_kind=operation_kind,
            adapter_kind=type(adapter).__name__,
        )
        if type(request).__name__ != mapping["request_kind"]:
            raise CandidateRuntimeAssemblyError("request is outside the operation map")
        callback = type(adapter).bind(adapter, request, meter_contract=meter)
        return self._scheduler.run_effect(
            meter_contract=meter,
            scheduler_contract=schedule,
            invocation_ref_sha256=invocation_ref_sha256,
            callback=callback,
        )

    def run_model_json(
        self,
        *,
        adapter: AzureResponsesSingleAttemptAdapter,
        request: AzureResponsesRequest,
        meter_contract: Mapping[str, Any],
        scheduler_contract: Mapping[str, Any],
        invocation_ref_sha256: str,
    ) -> CandidateRuntimeAssemblyResult:
        if type(adapter) is not AzureResponsesSingleAttemptAdapter or type(
            request
        ) is not AzureResponsesRequest:
            raise CandidateRuntimeAssemblyError("model adapter or request type is invalid")
        scheduled = self._execute(
            operation_kind="model_json",
            adapter=adapter,
            request=request,
            meter_contract=meter_contract,
            scheduler_contract=scheduler_contract,
            invocation_ref_sha256=invocation_ref_sha256,
        )
        parsed: StrictJsonParseResult = parse_settled_model_json(
            scheduled,
            parser_contract=self._contract["model_parser_contract"],
        )
        receipt = _assembly_receipt(
            contract=self._contract,
            operation_kind="model_json",
            adapter_kind=type(adapter).__name__,
            request_kind=type(request).__name__,
            meter_contract=scheduled.receipt["parent_execution_receipt"][
                "meter_contract"
            ],
            scheduler_contract=scheduled.receipt["scheduler_contract"],
            invocation_ref_sha256=invocation_ref_sha256,
            postprocessor_receipt=parsed.receipt,
        )
        return CandidateRuntimeAssemblyResult(receipt=receipt, value=parsed.value)

    def run_search_leads(
        self,
        *,
        adapter: TavilySearchSingleAttemptAdapter
        | AzureHostedSearchSingleAttemptAdapter
        | AnthropicServerSearchSingleAttemptAdapter,
        request: TavilySearchRequest
        | AzureHostedSearchRequest
        | AnthropicServerSearchRequest,
        meter_contract: Mapping[str, Any],
        scheduler_contract: Mapping[str, Any],
        invocation_ref_sha256: str,
    ) -> CandidateRuntimeAssemblyResult:
        exact_pairs = {
            TavilySearchSingleAttemptAdapter: TavilySearchRequest,
            AzureHostedSearchSingleAttemptAdapter: AzureHostedSearchRequest,
            AnthropicServerSearchSingleAttemptAdapter: AnthropicServerSearchRequest,
        }
        expected_request = exact_pairs.get(type(adapter))
        if expected_request is None or type(request) is not expected_request:
            raise CandidateRuntimeAssemblyError("search adapter or request type is invalid")
        scheduled = self._execute(
            operation_kind="search_leads",
            adapter=adapter,
            request=request,
            meter_contract=meter_contract,
            scheduler_contract=scheduler_contract,
            invocation_ref_sha256=invocation_ref_sha256,
        )
        projected: SearchPageProjectionResult = project_settled_search_leads(
            scheduled,
            projection_contract=self._contract["search_page_projection_contract"],
        )
        receipt = _assembly_receipt(
            contract=self._contract,
            operation_kind="search_leads",
            adapter_kind=type(adapter).__name__,
            request_kind=type(request).__name__,
            meter_contract=scheduled.receipt["parent_execution_receipt"][
                "meter_contract"
            ],
            scheduler_contract=scheduled.receipt["scheduler_contract"],
            invocation_ref_sha256=invocation_ref_sha256,
            postprocessor_receipt=projected.receipt,
        )
        return CandidateRuntimeAssemblyResult(
            receipt=receipt,
            value=projected.value,
        )

    def run_fetched_page(
        self,
        *,
        adapter: PinnedNativeHttpFetchAdapter,
        request: NativeHttpFetchRequest,
        meter_contract: Mapping[str, Any],
        scheduler_contract: Mapping[str, Any],
        invocation_ref_sha256: str,
    ) -> CandidateRuntimeAssemblyResult:
        if type(adapter) is not PinnedNativeHttpFetchAdapter or type(
            request
        ) is not NativeHttpFetchRequest:
            raise CandidateRuntimeAssemblyError("fetch adapter or request type is invalid")
        scheduled = self._execute(
            operation_kind="fetched_page",
            adapter=adapter,
            request=request,
            meter_contract=meter_contract,
            scheduler_contract=scheduler_contract,
            invocation_ref_sha256=invocation_ref_sha256,
        )
        projected: SearchPageProjectionResult = project_settled_fetched_page(
            scheduled,
            projection_contract=self._contract["search_page_projection_contract"],
        )
        receipt = _assembly_receipt(
            contract=self._contract,
            operation_kind="fetched_page",
            adapter_kind=type(adapter).__name__,
            request_kind=type(request).__name__,
            meter_contract=scheduled.receipt["parent_execution_receipt"][
                "meter_contract"
            ],
            scheduler_contract=scheduled.receipt["scheduler_contract"],
            invocation_ref_sha256=invocation_ref_sha256,
            postprocessor_receipt=projected.receipt,
        )
        return CandidateRuntimeAssemblyResult(
            receipt=receipt,
            value=projected.value,
        )
