"""Build-only typed cost meter for V2.42.33 effect settlements.

The current clients expose different accounting surfaces.  Responses and
Anthropic hosted-search success payloads can report token usage, Tavily and
direct HTTP fetches have no interface-level token meter, and retry failures may
return no usage at all.  This module preserves those distinctions instead of
turning missing usage into zero.

A meter contract is frozen before V2.42.33 issues a permit.  Sanitized attempt
receipts then produce either a complete cost vector or an incomplete lower
bound.  Missing applicable dimensions use the already charged reservation as
a conservative settlement fallback rather than becoming zero or creating a
refund.  The module is pure and build-only: it cannot call a provider, attest a
response, measure a clock, serialize concurrent writers, or authorize an
external effect, benchmark, evaluator, lease, or launch.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from deepwide_agent.v24232_webswarm_total_budget import (
    COST_DIMENSIONS,
    build_cost_vector,
    object_sha256,
)
from deepwide_agent.v24233_webswarm_effect_preauthorization import (
    PERMIT_KEYS,
    PERMIT_ROLE,
    issue_effect_permit,
    settle_effect_permit,
    validate_effect_preauthorization_state,
)


POLICY_ID = "v24234_provider_cost_meter_v1"
CONTRACT_ROLE = "v24234_provider_cost_meter_contract"
ATTEMPT_ROLE = "v24234_provider_cost_attempt"
MEASUREMENT_ROLE = "v24234_provider_cost_measurement"

MAX_ATTEMPTS = 64
MAX_COST = 1_000_000_000_000_000
COST_KEYS = frozenset(COST_DIMENSIONS)

PRODUCTION_PACKAGE_AUTHORIZED = False
ACTIVE_FORWARD_INTEGRATION_AUTHORIZED = False
EXTERNAL_SIDE_EFFECT_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
DEV64_OR_EXACT220_LAUNCH_AUTHORIZED = False
SHARED_API_LEASE_ACQUIRE_AUTHORIZED = False
LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED = False

USAGE_OBSERVED = "observed"
USAGE_UNAVAILABLE = "unavailable"
USAGE_NOT_APPLICABLE = "not_applicable"
USAGE_STATES = frozenset(
    {USAGE_OBSERVED, USAGE_UNAVAILABLE, USAGE_NOT_APPLICABLE}
)
OUTCOMES = frozenset(
    {
        "success",
        "retryable_http",
        "key_local_http",
        "terminal_http",
        "transport_error",
        "invalid_json",
        "empty_output",
        "local_success",
        "local_error",
    }
)

PROVIDER_SPECS: dict[str, dict[str, Any]] = {
    "azure_responses_model": {
        "effect_kind": "model_request",
        "token_usage_policy": "required",
        "provider_tool_usage_policy": "not_applicable",
        "count_mapping": "one_logical_model_call_and_all_http_attempts",
        "allowed_charge_kinds": frozenset(
            {"scout_execution", "fanout_execution", "renderer"}
        ),
    },
    "azure_responses_web_search": {
        "effect_kind": "hosted_web_search",
        "token_usage_policy": "required",
        "provider_tool_usage_policy": "required",
        "count_mapping": "all_http_attempts_plus_provider_web_search_actions",
        "allowed_charge_kinds": frozenset(
            {"scout_execution", "fanout_execution"}
        ),
    },
    "anthropic_server_web_search": {
        "effect_kind": "hosted_web_search",
        "token_usage_policy": "required",
        "provider_tool_usage_policy": "required",
        "count_mapping": "all_http_attempts_plus_provider_web_search_actions",
        "allowed_charge_kinds": frozenset(
            {"scout_execution", "fanout_execution"}
        ),
    },
    "tavily_search_api": {
        "effect_kind": "search_request",
        "token_usage_policy": "not_applicable",
        "provider_tool_usage_policy": "not_applicable",
        "count_mapping": "all_http_attempts_as_search_calls",
        "allowed_charge_kinds": frozenset(
            {"scout_execution", "fanout_execution"}
        ),
    },
    "native_http_fetch": {
        "effect_kind": "fetch_request",
        "token_usage_policy": "not_applicable",
        "provider_tool_usage_policy": "not_applicable",
        "count_mapping": "all_http_attempts_as_fetch_calls",
        "allowed_charge_kinds": frozenset(
            {"scout_execution", "fanout_execution"}
        ),
    },
    "local_orchestrator": {
        "effect_kind": "orchestrator_step",
        "token_usage_policy": "not_applicable",
        "provider_tool_usage_policy": "not_applicable",
        "count_mapping": "one_local_orchestrator_call",
        "allowed_charge_kinds": frozenset({"orchestrator"}),
    },
    "local_other_tool": {
        "effect_kind": "other_tool_step",
        "token_usage_policy": "not_applicable",
        "provider_tool_usage_policy": "not_applicable",
        "count_mapping": "one_local_other_tool_call",
        "allowed_charge_kinds": frozenset({"other_tool", "renderer"}),
    },
}

CONTRACT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "build_only",
        "provider_kind",
        "effect_kind",
        "charge_kind",
        "max_attempts",
        "reserved_cost",
        "token_usage_policy",
        "provider_tool_usage_policy",
        "count_mapping",
        "wall_measurement_policy",
        "missing_applicable_usage_is_zero",
        "raw_request_or_response_content_allowed",
        "provider_response_authenticity_independently_verified",
        "local_counter_and_clock_independently_attested",
        "runtime_provider_wrapper_integrated",
        "external_side_effect_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "contract_sha256",
    }
)
ATTEMPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "build_only",
        "meter_contract_sha256",
        "provider_kind",
        "effect_kind",
        "attempt_index",
        "attempt_ref_sha256",
        "local_counter_ref_sha256",
        "outcome",
        "http_status",
        "provider_response_ref_sha256",
        "token_usage_state",
        "input_tokens",
        "output_tokens",
        "provider_tool_usage_state",
        "provider_tool_calls",
        "wall_milliseconds",
        "request_body_bytes",
        "response_body_bytes",
        "raw_request_or_response_content_present",
        "credential_or_url_present",
        "provider_response_authenticity_independently_verified",
        "local_counter_and_clock_independently_attested",
        "attempt_sha256",
    }
)
MEASUREMENT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "build_only",
        "measurement_ref_sha256",
        "meter_contract_sha256",
        "provider_kind",
        "effect_kind",
        "permit_ref_sha256",
        "permit_sha256",
        "attempts",
        "attempt_count",
        "logical_status",
        "effect_receipt_sha256",
        "observed_cost_lower_bound",
        "settlement_cost",
        "unavailable_dimensions",
        "reservation_fallback_dimensions",
        "settlement_cost_basis",
        "all_applicable_usage_observed",
        "reservation_fallback_applied",
        "observed_lower_bound_within_reservation",
        "settlement_cost_within_reservation",
        "settlement_eligible",
        "missing_applicable_usage_treated_as_zero",
        "raw_request_or_response_content_present",
        "credential_or_url_present",
        "provider_response_authenticity_independently_verified",
        "local_counter_and_clock_independently_attested",
        "runtime_provider_wrapper_integrated",
        "external_side_effect_authorized",
        "measurement_sha256",
    }
)


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
        raise ValueError(f"V2.42.34 {label} schema is not exact")
    return value


def _integer(
    value: object,
    *,
    label: str,
    minimum: int = 0,
    maximum: int = MAX_COST,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise ValueError(f"V2.42.34 {label} is outside the frozen range")
    return value


def _optional_integer(value: object, *, label: str) -> int | None:
    if value is None:
        return None
    return _integer(value, label=label)


def _optional_sha256(value: object, *, label: str) -> str | None:
    if value is None:
        return None
    if not _is_sha256(value):
        raise ValueError(f"V2.42.34 {label} is not SHA-256 bound")
    return str(value)


def _sealed(value: Mapping[str, Any], *, seal_key: str) -> bool:
    if not _is_sha256(value.get(seal_key)):
        return False
    unsigned = dict(value)
    seal = unsigned.pop(seal_key)
    return seal == object_sha256(unsigned)


def _cost(value: Mapping[str, Any], *, positive: bool) -> dict[str, int]:
    source = _exact(value, keys=COST_KEYS, label="cost")
    cost = build_cost_vector(
        **{dimension: source.get(dimension) for dimension in COST_DIMENSIONS}
    )
    if positive and not any(cost.values()):
        raise ValueError("V2.42.34 reserved cost must be positive")
    return cost


def _zero_cost() -> dict[str, int]:
    return {dimension: 0 for dimension in COST_DIMENSIONS}


def _provider_spec(provider_kind: str) -> dict[str, Any]:
    if provider_kind not in PROVIDER_SPECS:
        raise ValueError("V2.42.34 provider kind is invalid")
    return PROVIDER_SPECS[provider_kind]


def _expected_reserved_counts(
    *, provider_kind: str, max_attempts: int
) -> dict[str, int | None]:
    expected: dict[str, int | None] = {
        "model_calls": 0,
        "model_attempts": 0,
        "search_calls": 0,
        "fetch_calls": 0,
        "other_tool_calls": 0,
        "orchestrator_calls": 0,
    }
    if provider_kind == "azure_responses_model":
        expected["model_calls"] = 1
        expected["model_attempts"] = max_attempts
    elif provider_kind in {
        "azure_responses_web_search",
        "anthropic_server_web_search",
    }:
        expected["search_calls"] = max_attempts
        expected["other_tool_calls"] = None
    elif provider_kind == "tavily_search_api":
        expected["search_calls"] = max_attempts
    elif provider_kind == "native_http_fetch":
        expected["fetch_calls"] = max_attempts
    elif provider_kind == "local_orchestrator":
        expected["orchestrator_calls"] = 1
    elif provider_kind == "local_other_tool":
        expected["other_tool_calls"] = 1
    return expected


def build_provider_meter_contract(
    *,
    provider_kind: str,
    charge_kind: str,
    max_attempts: int,
    reserved_cost: Mapping[str, Any],
) -> dict[str, Any]:
    spec = _provider_spec(provider_kind)
    attempts = _integer(
        max_attempts,
        label="max attempts",
        minimum=1,
        maximum=MAX_ATTEMPTS,
    )
    if provider_kind in {"local_orchestrator", "local_other_tool"} and attempts != 1:
        raise ValueError("V2.42.34 local effects require one attempt")
    if charge_kind not in spec["allowed_charge_kinds"]:
        raise ValueError("V2.42.34 charge kind is incompatible with provider")
    reserved = _cost(reserved_cost, positive=True)
    expected_counts = _expected_reserved_counts(
        provider_kind=provider_kind,
        max_attempts=attempts,
    )
    for dimension, expected in expected_counts.items():
        if expected is None:
            if reserved[dimension] < 1:
                raise ValueError(
                    "V2.42.34 hosted search must reserve provider tool calls"
                )
        elif reserved[dimension] != expected:
            raise ValueError(
                f"V2.42.34 reserved {dimension} differs from count mapping"
            )
    if spec["token_usage_policy"] == "required":
        if reserved["input_tokens"] < 1 or reserved["output_tokens"] < 1:
            raise ValueError("V2.42.34 token-metered effect needs token reservation")
    elif reserved["input_tokens"] != 0 or reserved["output_tokens"] != 0:
        raise ValueError("V2.42.34 token-inapplicable effect reserved tokens")
    if reserved["wall_milliseconds"] < 1:
        raise ValueError("V2.42.34 effect needs positive wall reservation")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": CONTRACT_ROLE,
        "policy_id": POLICY_ID,
        "build_only": True,
        "provider_kind": provider_kind,
        "effect_kind": spec["effect_kind"],
        "charge_kind": charge_kind,
        "max_attempts": attempts,
        "reserved_cost": reserved,
        "token_usage_policy": spec["token_usage_policy"],
        "provider_tool_usage_policy": spec["provider_tool_usage_policy"],
        "count_mapping": spec["count_mapping"],
        "wall_measurement_policy": "sum_attempt_intervals_including_retry_backoff",
        "missing_applicable_usage_is_zero": False,
        "raw_request_or_response_content_allowed": False,
        "provider_response_authenticity_independently_verified": False,
        "local_counter_and_clock_independently_attested": False,
        "runtime_provider_wrapper_integrated": False,
        "external_side_effect_authorized": EXTERNAL_SIDE_EFFECT_AUTHORIZED,
        "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    }
    value["contract_sha256"] = object_sha256(value)
    return value


def validate_provider_meter_contract(value: Mapping[str, Any]) -> None:
    contract = _exact(value, keys=CONTRACT_KEYS, label="meter contract")
    expected = build_provider_meter_contract(
        provider_kind=str(contract.get("provider_kind")),
        charge_kind=str(contract.get("charge_kind")),
        max_attempts=contract.get("max_attempts"),
        reserved_cost=contract.get("reserved_cost"),
    )
    if dict(contract) != expected or not _sealed(
        contract, seal_key="contract_sha256"
    ):
        raise ValueError("V2.42.34 meter contract drifted")


def _validate_outcome(
    *, provider_kind: str, outcome: str, status: int | None
) -> None:
    local = provider_kind in {"local_orchestrator", "local_other_tool"}
    if local:
        if outcome not in {"local_success", "local_error"} or status is not None:
            raise ValueError("V2.42.34 local outcome or HTTP status is invalid")
        return
    if outcome in {"local_success", "local_error"}:
        raise ValueError("V2.42.34 network provider has local outcome")
    if outcome == "transport_error":
        if status is not None:
            raise ValueError("V2.42.34 transport error has HTTP status")
        return
    if status is None or isinstance(status, bool) or not isinstance(status, int):
        raise ValueError("V2.42.34 HTTP outcome lacks status")
    if status < 100 or status > 599:
        raise ValueError("V2.42.34 HTTP status is invalid")
    if outcome in {"success", "invalid_json", "empty_output"}:
        valid = 200 <= status < 300
    elif outcome == "retryable_http":
        valid = status in {408, 409, 429} or status >= 500
    elif outcome == "key_local_http":
        valid = (
            provider_kind == "tavily_search_api"
            and status in {401, 403, 432}
        )
    else:
        valid = (
            400 <= status < 500
            and status not in {408, 409, 429}
            and not (
                provider_kind == "tavily_search_api"
                and status in {401, 403, 432}
            )
        )
    if not valid:
        raise ValueError("V2.42.34 outcome and HTTP status disagree")


def _normalize_usage(
    *,
    state: str,
    first: object,
    second: object,
    policy: str,
    label: str,
) -> tuple[int | None, int | None]:
    if state not in USAGE_STATES:
        raise ValueError(f"V2.42.34 {label} usage state is invalid")
    if policy == "not_applicable":
        if state != USAGE_NOT_APPLICABLE or first is not None or second is not None:
            raise ValueError(f"V2.42.34 {label} usage must be not applicable")
        return None, None
    if state == USAGE_NOT_APPLICABLE:
        raise ValueError(f"V2.42.34 applicable {label} usage marked inapplicable")
    if state == USAGE_UNAVAILABLE:
        if first is not None or second is not None:
            raise ValueError(f"V2.42.34 unavailable {label} usage has values")
        return None, None
    return (
        _integer(first, label=f"{label} first value"),
        _integer(second, label=f"{label} second value"),
    )


def build_provider_attempt(
    *,
    contract: Mapping[str, Any],
    attempt_index: int,
    attempt_ref_sha256: str,
    local_counter_ref_sha256: str,
    outcome: str,
    http_status: int | None,
    provider_response_ref_sha256: str | None,
    token_usage_state: str,
    input_tokens: int | None,
    output_tokens: int | None,
    provider_tool_usage_state: str,
    provider_tool_calls: int | None,
    wall_milliseconds: int,
    request_body_bytes: int,
    response_body_bytes: int | None,
) -> dict[str, Any]:
    validate_provider_meter_contract(contract)
    index = _integer(
        attempt_index,
        label="attempt index",
        minimum=1,
        maximum=int(contract["max_attempts"]),
    )
    if not _is_sha256(attempt_ref_sha256) or not _is_sha256(
        local_counter_ref_sha256
    ):
        raise ValueError("V2.42.34 attempt provenance is not SHA-256 bound")
    if outcome not in OUTCOMES:
        raise ValueError("V2.42.34 attempt outcome is invalid")
    provider_kind = str(contract["provider_kind"])
    _validate_outcome(
        provider_kind=provider_kind,
        outcome=outcome,
        status=http_status,
    )
    response_ref = _optional_sha256(
        provider_response_ref_sha256,
        label="provider response reference",
    )
    local = provider_kind in {"local_orchestrator", "local_other_tool"}
    if outcome != "transport_error" and response_ref is None:
        raise ValueError("V2.42.34 observed response lacks reference")
    if outcome == "transport_error" and response_ref is not None:
        raise ValueError("V2.42.34 transport error has provider response")
    normalized_input, normalized_output = _normalize_usage(
        state=token_usage_state,
        first=input_tokens,
        second=output_tokens,
        policy=str(contract["token_usage_policy"]),
        label="token",
    )
    normalized_tool, _ = _normalize_usage(
        state=provider_tool_usage_state,
        first=provider_tool_calls,
        second=provider_tool_calls,
        policy=str(contract["provider_tool_usage_policy"]),
        label="provider tool",
    )
    success = outcome in {"success", "local_success"}
    if success:
        if contract["token_usage_policy"] == "required" and token_usage_state != USAGE_OBSERVED:
            raise ValueError("V2.42.34 success lacks provider token usage")
        if (
            contract["provider_tool_usage_policy"] == "required"
            and provider_tool_usage_state != USAGE_OBSERVED
        ):
            raise ValueError("V2.42.34 hosted-search success lacks tool usage")
        if normalized_tool is not None and normalized_tool < 1:
            raise ValueError("V2.42.34 hosted-search success has no tool call")
        if (
            contract["token_usage_policy"] == "required"
            and int(normalized_input or 0) + int(normalized_output or 0) < 1
        ):
            raise ValueError("V2.42.34 success reports zero provider tokens")
    wall = _integer(wall_milliseconds, label="wall milliseconds", minimum=1)
    request_bytes = _integer(request_body_bytes, label="request body bytes")
    response_bytes = _optional_integer(
        response_body_bytes,
        label="response body bytes",
    )
    if outcome == "transport_error":
        if response_bytes is not None:
            raise ValueError("V2.42.34 transport error has response bytes")
    elif local:
        if request_bytes != 0 or response_bytes is not None:
            raise ValueError("V2.42.34 local effect has HTTP byte accounting")
    else:
        if response_bytes is None:
            raise ValueError("V2.42.34 HTTP response lacks byte accounting")
        if provider_kind == "native_http_fetch":
            if request_bytes != 0:
                raise ValueError("V2.42.34 direct fetch has request body")
        elif request_bytes < 1:
            raise ValueError("V2.42.34 POST request body is empty")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ATTEMPT_ROLE,
        "policy_id": POLICY_ID,
        "build_only": True,
        "meter_contract_sha256": contract["contract_sha256"],
        "provider_kind": contract["provider_kind"],
        "effect_kind": contract["effect_kind"],
        "attempt_index": index,
        "attempt_ref_sha256": attempt_ref_sha256,
        "local_counter_ref_sha256": local_counter_ref_sha256,
        "outcome": outcome,
        "http_status": http_status,
        "provider_response_ref_sha256": response_ref,
        "token_usage_state": token_usage_state,
        "input_tokens": normalized_input,
        "output_tokens": normalized_output,
        "provider_tool_usage_state": provider_tool_usage_state,
        "provider_tool_calls": normalized_tool,
        "wall_milliseconds": wall,
        "request_body_bytes": request_bytes,
        "response_body_bytes": response_bytes,
        "raw_request_or_response_content_present": False,
        "credential_or_url_present": False,
        "provider_response_authenticity_independently_verified": False,
        "local_counter_and_clock_independently_attested": False,
    }
    value["attempt_sha256"] = object_sha256(value)
    return value


def validate_provider_attempt(
    value: Mapping[str, Any], *, contract: Mapping[str, Any]
) -> None:
    attempt = _exact(value, keys=ATTEMPT_KEYS, label="provider attempt")
    expected = build_provider_attempt(
        contract=contract,
        attempt_index=attempt.get("attempt_index"),
        attempt_ref_sha256=str(attempt.get("attempt_ref_sha256")),
        local_counter_ref_sha256=str(attempt.get("local_counter_ref_sha256")),
        outcome=str(attempt.get("outcome")),
        http_status=attempt.get("http_status"),
        provider_response_ref_sha256=attempt.get("provider_response_ref_sha256"),
        token_usage_state=str(attempt.get("token_usage_state")),
        input_tokens=attempt.get("input_tokens"),
        output_tokens=attempt.get("output_tokens"),
        provider_tool_usage_state=str(attempt.get("provider_tool_usage_state")),
        provider_tool_calls=attempt.get("provider_tool_calls"),
        wall_milliseconds=attempt.get("wall_milliseconds"),
        request_body_bytes=attempt.get("request_body_bytes"),
        response_body_bytes=attempt.get("response_body_bytes"),
    )
    if dict(attempt) != expected or not _sealed(
        attempt, seal_key="attempt_sha256"
    ):
        raise ValueError("V2.42.34 provider attempt drifted")


def _validate_permit(
    permit: Mapping[str, Any], *, contract: Mapping[str, Any]
) -> None:
    value = _exact(permit, keys=PERMIT_KEYS, label="V2.42.33 permit")
    if (
        value.get("role") != PERMIT_ROLE
        or value.get("build_only") is not True
        or not _sealed(value, seal_key="permit_sha256")
        or value.get("charge_kind") != contract["charge_kind"]
        or value.get("estimate_source_sha256") != contract["contract_sha256"]
        or value.get("reserved_cost") != contract["reserved_cost"]
        or value.get("external_side_effect_authorized") is not False
    ):
        raise ValueError("V2.42.34 permit and meter contract binding drifted")


def issue_metered_effect_permit(
    previous: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    guidance_contract: Mapping[str, Any],
    guidance_policy: Mapping[str, Any],
    guidance_arm: Mapping[str, Any],
    scouts: Sequence[Mapping[str, Any]],
    probe: Mapping[str, Any] | None,
    experience: Mapping[str, Any] | None,
    permit_ref_sha256: str,
    charge_ref_sha256: str,
) -> dict[str, Any]:
    validate_provider_meter_contract(contract)
    return issue_effect_permit(
        previous,
        contract=guidance_contract,
        guidance_policy=guidance_policy,
        guidance_arm=guidance_arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
        permit_ref_sha256=permit_ref_sha256,
        charge_kind=str(contract["charge_kind"]),
        charge_ref_sha256=charge_ref_sha256,
        estimate_source_sha256=str(contract["contract_sha256"]),
        reserved_cost=contract["reserved_cost"],
    )


def _mapped_lower_bound(
    *, contract: Mapping[str, Any], attempts: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, int], list[str]]:
    cost = _zero_cost()
    provider = str(contract["provider_kind"])
    if provider == "azure_responses_model":
        cost["model_calls"] = 1
        cost["model_attempts"] = len(attempts)
    elif provider in {
        "azure_responses_web_search",
        "anthropic_server_web_search",
        "tavily_search_api",
    }:
        cost["search_calls"] = len(attempts)
    elif provider == "native_http_fetch":
        cost["fetch_calls"] = len(attempts)
    elif provider == "local_orchestrator":
        cost["orchestrator_calls"] = 1
    elif provider == "local_other_tool":
        cost["other_tool_calls"] = 1
    unavailable: set[str] = set()
    for attempt in attempts:
        if attempt["token_usage_state"] == USAGE_OBSERVED:
            cost["input_tokens"] += int(attempt["input_tokens"])
            cost["output_tokens"] += int(attempt["output_tokens"])
        elif attempt["token_usage_state"] == USAGE_UNAVAILABLE:
            unavailable.update({"input_tokens", "output_tokens"})
        if attempt["provider_tool_usage_state"] == USAGE_OBSERVED:
            cost["other_tool_calls"] += int(attempt["provider_tool_calls"])
        elif attempt["provider_tool_usage_state"] == USAGE_UNAVAILABLE:
            unavailable.add("other_tool_calls")
        cost["wall_milliseconds"] += int(attempt["wall_milliseconds"])
        if any(value > MAX_COST for value in cost.values()):
            raise ValueError("V2.42.34 measured cost overflowed")
    ordered = [dimension for dimension in COST_DIMENSIONS if dimension in unavailable]
    return build_cost_vector(**cost), ordered


def build_provider_cost_measurement(
    *,
    contract: Mapping[str, Any],
    permit: Mapping[str, Any],
    measurement_ref_sha256: str,
    attempts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    validate_provider_meter_contract(contract)
    _validate_permit(permit, contract=contract)
    if not _is_sha256(measurement_ref_sha256):
        raise ValueError("V2.42.34 measurement reference is not SHA-256 bound")
    if isinstance(attempts, (str, bytes)) or not isinstance(attempts, Sequence):
        raise ValueError("V2.42.34 attempts must be a sequence")
    if not 1 <= len(attempts) <= int(contract["max_attempts"]):
        raise ValueError("V2.42.34 attempt count is invalid")
    normalized: list[dict[str, Any]] = []
    for expected_index, source in enumerate(attempts, start=1):
        attempt = dict(source)
        validate_provider_attempt(attempt, contract=contract)
        if attempt["attempt_index"] != expected_index:
            raise ValueError("V2.42.34 attempt sequence is not contiguous")
        normalized.append(attempt)
    attempt_refs = [item["attempt_ref_sha256"] for item in normalized]
    counter_refs = [item["local_counter_ref_sha256"] for item in normalized]
    response_refs = [
        item["provider_response_ref_sha256"]
        for item in normalized
        if item["provider_response_ref_sha256"] is not None
    ]
    if len(attempt_refs) != len(set(attempt_refs)):
        raise ValueError("V2.42.34 duplicate attempt reference rejected")
    if len(counter_refs) != len(set(counter_refs)):
        raise ValueError("V2.42.34 duplicate local counter reference rejected")
    if len(response_refs) != len(set(response_refs)):
        raise ValueError("V2.42.34 duplicate provider response reference rejected")
    success_indices = [
        index
        for index, item in enumerate(normalized)
        if item["outcome"] in {"success", "local_success"}
    ]
    if len(success_indices) > 1 or (
        success_indices and success_indices[0] != len(normalized) - 1
    ):
        raise ValueError("V2.42.34 success must be unique and final")
    for item in normalized[:-1]:
        if item["outcome"] in {"terminal_http", "local_error"}:
            raise ValueError("V2.42.34 terminal outcome must be final")
    logical_status = "completed" if success_indices else "failed"
    lower_bound, unavailable = _mapped_lower_bound(
        contract=contract,
        attempts=normalized,
    )
    reserved = contract["reserved_cost"]
    lower_within = all(
        lower_bound[dimension] <= reserved[dimension]
        for dimension in COST_DIMENSIONS
    )
    complete = not unavailable
    settlement_cost = dict(lower_bound)
    for dimension in unavailable:
        settlement_cost[dimension] = int(reserved[dimension])
    fallback_applied = bool(unavailable)
    settlement_within = all(
        settlement_cost[dimension] <= reserved[dimension]
        for dimension in COST_DIMENSIONS
    )
    settlement_eligible = bool(lower_within and settlement_within)
    effect_receipt_sha256 = object_sha256(
        {
            "meter_contract_sha256": contract["contract_sha256"],
            "permit_sha256": permit["permit_sha256"],
            "attempt_sha256s": [item["attempt_sha256"] for item in normalized],
        }
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": MEASUREMENT_ROLE,
        "policy_id": POLICY_ID,
        "build_only": True,
        "measurement_ref_sha256": measurement_ref_sha256,
        "meter_contract_sha256": contract["contract_sha256"],
        "provider_kind": contract["provider_kind"],
        "effect_kind": contract["effect_kind"],
        "permit_ref_sha256": permit["permit_ref_sha256"],
        "permit_sha256": permit["permit_sha256"],
        "attempts": normalized,
        "attempt_count": len(normalized),
        "logical_status": logical_status,
        "effect_receipt_sha256": effect_receipt_sha256,
        "observed_cost_lower_bound": lower_bound,
        "settlement_cost": settlement_cost,
        "unavailable_dimensions": unavailable,
        "reservation_fallback_dimensions": list(unavailable),
        "settlement_cost_basis": (
            "declared_reservation_fallback"
            if fallback_applied
            else "fully_observed_or_schema_mapped"
        ),
        "all_applicable_usage_observed": complete,
        "reservation_fallback_applied": fallback_applied,
        "observed_lower_bound_within_reservation": lower_within,
        "settlement_cost_within_reservation": settlement_within,
        "settlement_eligible": settlement_eligible,
        "missing_applicable_usage_treated_as_zero": False,
        "raw_request_or_response_content_present": False,
        "credential_or_url_present": False,
        "provider_response_authenticity_independently_verified": False,
        "local_counter_and_clock_independently_attested": False,
        "runtime_provider_wrapper_integrated": False,
        "external_side_effect_authorized": EXTERNAL_SIDE_EFFECT_AUTHORIZED,
    }
    value["measurement_sha256"] = object_sha256(value)
    return value


def validate_provider_cost_measurement(
    value: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    permit: Mapping[str, Any],
) -> None:
    measurement = _exact(value, keys=MEASUREMENT_KEYS, label="cost measurement")
    expected = build_provider_cost_measurement(
        contract=contract,
        permit=permit,
        measurement_ref_sha256=str(measurement.get("measurement_ref_sha256")),
        attempts=measurement.get("attempts"),
    )
    if dict(measurement) != expected or not _sealed(
        measurement, seal_key="measurement_sha256"
    ):
        raise ValueError("V2.42.34 cost measurement drifted")


def settle_metered_effect_permit(
    previous: Mapping[str, Any],
    *,
    meter_contract: Mapping[str, Any],
    measurement: Mapping[str, Any],
    guidance_contract: Mapping[str, Any],
    guidance_policy: Mapping[str, Any],
    guidance_arm: Mapping[str, Any],
    scouts: Sequence[Mapping[str, Any]],
    probe: Mapping[str, Any] | None,
    experience: Mapping[str, Any] | None,
) -> dict[str, Any]:
    validate_provider_meter_contract(meter_contract)
    validate_effect_preauthorization_state(
        previous,
        contract=guidance_contract,
        guidance_policy=guidance_policy,
        guidance_arm=guidance_arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
    )
    pending = {
        event["permit_ref_sha256"]: event
        for event in previous["events"]
        if event["role"] == PERMIT_ROLE
        and event["permit_ref_sha256"] in previous["pending_permit_refs"]
    }
    permit_ref = str(measurement.get("permit_ref_sha256"))
    if permit_ref not in pending:
        raise ValueError("V2.42.34 measurement permit is absent or settled")
    permit = pending[permit_ref]
    validate_provider_cost_measurement(
        measurement,
        contract=meter_contract,
        permit=permit,
    )
    if measurement["settlement_eligible"] is not True:
        raise ValueError("V2.42.34 over-reservation measurement")
    return settle_effect_permit(
        previous,
        contract=guidance_contract,
        guidance_policy=guidance_policy,
        guidance_arm=guidance_arm,
        scouts=scouts,
        probe=probe,
        experience=experience,
        permit_ref_sha256=permit_ref,
        effect_receipt_sha256=str(measurement["effect_receipt_sha256"]),
        actual_cost_source_sha256=str(measurement["measurement_sha256"]),
        actual_cost=measurement["settlement_cost"],
    )
