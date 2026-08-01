"""Strict post-settlement JSON-object parsing for V2.42.43 model effects.

The local GPT-5.6 adapter deliberately returns ephemeral text.  This candidate
accepts that text only through a validated V2.42.43 success result whose
V2.42.42 parent has already durably settled.  It parses either one exact JSON
object or one whole-response JSON fence, rejects duplicate keys and non-finite
numbers, enforces structural budgets, and blocks evaluator-like metadata at
every nesting level before returning an ephemeral object.

Parsing is pure and performs no repair request.  A repair, if ever authorized,
must be a new independently preauthorized provider effect with a distinct
invocation identity and cost reservation.  This module does not parse search
leads or fetched pages and is not imported by active clients, runtime, runner,
launcher, benchmark, or evaluator code.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import math
import re
import unicodedata
from typing import Any, Mapping, Sequence

from deepwide_agent.v24232_webswarm_total_budget import object_sha256
from deepwide_agent.v24236_azure_responses_single_attempt import (
    AzureResponsesAttemptValue,
)
from deepwide_agent.v24243_retry_deadline_scheduler import (
    RetryDeadlineExecutionResult,
    validate_retry_deadline_execution_receipt,
)


POLICY_ID = "v24244_strict_json_parser_boundary_v1"
CONTRACT_ROLE = "v24244_strict_json_parser_contract"
RECEIPT_ROLE = "v24244_strict_json_parser_receipt"

PRODUCTION_PACKAGE_AUTHORIZED = False
ACTIVE_FORWARD_INTEGRATION_AUTHORIZED = False
ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED = False
EXTERNAL_SIDE_EFFECT_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
DEV64_OR_EXACT220_LAUNCH_AUTHORIZED = False
SHARED_API_LEASE_ACQUIRE_AUTHORIZED = False
LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED = False

POST_DURABLE_SETTLEMENT_PARSE_BOUNDARY_IMPLEMENTED = True
EXACT_OBJECT_OR_WHOLE_FENCE_ONLY_IMPLEMENTED = True
DUPLICATE_KEY_REJECTION_IMPLEMENTED = True
NONFINITE_NUMBER_REJECTION_IMPLEMENTED = True
STRUCTURAL_BUDGET_IMPLEMENTED = True
NESTED_PRIVILEGED_METADATA_REJECTION_IMPLEMENTED = True
INTERNAL_REPAIR_PROVIDER_EFFECT_IMPLEMENTED = False
SEARCH_OR_PAGE_PARSER_INTEGRATION_IMPLEMENTED = False
EPHEMERAL_TEXT_TO_PARENT_RESPONSE_BINDING_INDEPENDENTLY_VERIFIED = False

MAX_TEXT_CHARACTERS = 1_000_000
MAX_UTF8_BYTES = 4_000_000
MAX_DEPTH = 128
MAX_NODES = 100_000
MAX_CONTAINER_ITEMS = 100_000
MAX_STRING_CHARACTERS = 1_000_000
CONTRACT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "candidate_runtime",
        "maximum_text_characters",
        "maximum_utf8_bytes",
        "maximum_depth",
        "maximum_nodes",
        "maximum_object_members",
        "maximum_array_items",
        "maximum_string_characters",
        "top_level_type",
        "accepted_envelopes",
        "duplicate_key_policy",
        "nonfinite_number_policy",
        "privileged_metadata_policy",
        "internal_repair_provider_effect_authorized",
        "raw_text_persistence_authorized",
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
        "parser_contract",
        "parser_contract_sha256",
        "scheduler_execution_receipt",
        "scheduler_execution_receipt_sha256",
        "parent_durable_execution_receipt_sha256",
        "meter_contract_sha256",
        "provider_response_ref_sha256",
        "input_text_characters",
        "input_utf8_bytes",
        "envelope_kind",
        "top_level_member_count",
        "node_count",
        "maximum_observed_depth",
        "string_character_count",
        "parsed_structure_sha256",
        "model_value_usage_matches_parent_attempt",
        "ephemeral_text_to_parent_response_binding_independently_verified",
        "post_durable_settlement_parse_boundary",
        "duplicate_keys_rejected",
        "nonfinite_numbers_rejected",
        "structural_budget_enforced",
        "nested_privileged_metadata_rejected",
        "internal_repair_provider_effect_called",
        "search_or_page_content_parsed",
        "raw_text_directly_persisted_or_emitted",
        "parser_created_raw_text_hash",
        "parsed_raw_strings_persisted_hashed_or_emitted",
        "schema_resealing_without_secret_cryptographically_excluded",
        "credential_or_url_present",
        "benchmark_or_evaluator_metadata_present",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "parser_receipt_sha256",
    }
)

PRIVILEGED_KEYS = frozenset(
    {
        "answer_key",
        "benchmark_category",
        "benchmark_label",
        "benchmark_subset",
        "category",
        "correct_answer",
        "correctness",
        "evaluator",
        "evaluator_payload",
        "evaluator_score",
        "gold",
        "gold_answer",
        "ground_truth",
        "label",
        "mapping",
        "official_score",
        "prediction",
        "question_type",
        "results.csv",
        "reward",
        "score",
        "split",
        "subset",
        "task_category",
        "task_id",
    }
)
PRIVILEGED_COMPACT_KEYS = frozenset(
    key.replace("_", "") for key in PRIVILEGED_KEYS
)
WHOLE_FENCE = re.compile(
    r"\A```(?:json)?[ \t]*\r?\n(?P<body>[\s\S]*?)\r?\n```[ \t]*\Z",
    re.IGNORECASE,
)


class StrictJsonParserBoundaryError(ValueError):
    """Sanitized parse rejection that never embeds provider text."""


@dataclasses.dataclass(frozen=True)
class StrictJsonParseResult:
    """Content-free parser receipt plus the ephemeral parsed object."""

    receipt: Mapping[str, Any]
    value: Mapping[str, Any]


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
        raise ValueError(f"V2.42.44 {label} schema is not exact")
    return value


def _sealed(value: Mapping[str, Any], *, key: str) -> bool:
    seal = value.get(key)
    if not _is_sha256(seal):
        return False
    unsigned = dict(value)
    unsigned.pop(key)
    return seal == object_sha256(unsigned)


def _integer(
    value: object,
    *,
    label: str,
    minimum: int = 0,
    maximum: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise ValueError(f"V2.42.44 {label} is outside the frozen range")
    return value


def build_strict_json_parser_contract(
    *,
    maximum_text_characters: int,
    maximum_utf8_bytes: int,
    maximum_depth: int,
    maximum_nodes: int,
    maximum_object_members: int,
    maximum_array_items: int,
    maximum_string_characters: int,
) -> dict[str, Any]:
    text_chars = _integer(
        maximum_text_characters,
        label="maximum text characters",
        minimum=2,
        maximum=MAX_TEXT_CHARACTERS,
    )
    utf8_bytes = _integer(
        maximum_utf8_bytes,
        label="maximum UTF-8 bytes",
        minimum=2,
        maximum=MAX_UTF8_BYTES,
    )
    depth = _integer(
        maximum_depth,
        label="maximum depth",
        minimum=1,
        maximum=MAX_DEPTH,
    )
    nodes = _integer(
        maximum_nodes,
        label="maximum nodes",
        minimum=1,
        maximum=MAX_NODES,
    )
    members = _integer(
        maximum_object_members,
        label="maximum object members",
        minimum=1,
        maximum=MAX_CONTAINER_ITEMS,
    )
    items = _integer(
        maximum_array_items,
        label="maximum array items",
        minimum=1,
        maximum=MAX_CONTAINER_ITEMS,
    )
    string_chars = _integer(
        maximum_string_characters,
        label="maximum string characters",
        minimum=1,
        maximum=MAX_STRING_CHARACTERS,
    )
    if string_chars > text_chars or max(members, items, depth) > nodes:
        raise ValueError("V2.42.44 structural limits are internally inconsistent")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": CONTRACT_ROLE,
        "policy_id": POLICY_ID,
        "candidate_runtime": True,
        "maximum_text_characters": text_chars,
        "maximum_utf8_bytes": utf8_bytes,
        "maximum_depth": depth,
        "maximum_nodes": nodes,
        "maximum_object_members": members,
        "maximum_array_items": items,
        "maximum_string_characters": string_chars,
        "top_level_type": "json_object",
        "accepted_envelopes": ["exact_json_object", "whole_response_json_fence"],
        "duplicate_key_policy": "reject_exact_or_normalized_collision_at_every_object_depth",
        "nonfinite_number_policy": "reject_nan_infinity_and_overflow",
        "privileged_metadata_policy": "reject_normalized_key_at_every_object_depth",
        "internal_repair_provider_effect_authorized": False,
        "raw_text_persistence_authorized": False,
        "active_forward_integration_authorized": False,
        "benchmark_forward_or_evaluator_authorized": False,
    }
    value["contract_sha256"] = object_sha256(value)
    return value


def validate_strict_json_parser_contract(value: Mapping[str, Any]) -> None:
    contract = _exact(value, keys=CONTRACT_KEYS, label="parser contract")
    expected = build_strict_json_parser_contract(
        maximum_text_characters=contract.get("maximum_text_characters"),
        maximum_utf8_bytes=contract.get("maximum_utf8_bytes"),
        maximum_depth=contract.get("maximum_depth"),
        maximum_nodes=contract.get("maximum_nodes"),
        maximum_object_members=contract.get("maximum_object_members"),
        maximum_array_items=contract.get("maximum_array_items"),
        maximum_string_characters=contract.get("maximum_string_characters"),
    )
    if dict(contract) != expected or not _sealed(contract, key="contract_sha256"):
        raise ValueError("V2.42.44 parser contract drifted")


def _normalized_key(value: str) -> str:
    canonical = unicodedata.normalize("NFKC", value)
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", canonical)
    return "_".join(
        part for part in re.split(r"[^a-z0-9]+", separated.casefold()) if part
    )


def _is_privileged_key(value: str) -> bool:
    normalized = _normalized_key(value)
    return (
        normalized in PRIVILEGED_KEYS
        or normalized.replace("_", "") in PRIVILEGED_COMPACT_KEYS
    )


def _pairs_hook(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    normalized_keys: set[str] = set()
    for key, item in pairs:
        normalized = _normalized_key(key)
        if key in value or normalized in normalized_keys:
            raise StrictJsonParserBoundaryError("duplicate JSON object key rejected")
        value[key] = item
        normalized_keys.add(normalized)
    return value


def _parse_constant(_value: str) -> None:
    raise StrictJsonParserBoundaryError("non-finite JSON number rejected")


def _parse_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise StrictJsonParserBoundaryError("non-finite JSON number rejected")
    return parsed


def _envelope(text: str) -> tuple[str, str]:
    stripped = text.strip()
    fence = WHOLE_FENCE.fullmatch(stripped)
    if fence is not None:
        body = fence.group("body").strip()
        if not body:
            raise StrictJsonParserBoundaryError("empty JSON fence rejected")
        return "whole_response_json_fence", body
    if "```" in stripped:
        raise StrictJsonParserBoundaryError("partial or non-JSON fence rejected")
    return "exact_json_object", stripped


def _parse_object(text: str) -> Mapping[str, Any]:
    try:
        value = json.loads(
            text,
            object_pairs_hook=_pairs_hook,
            parse_constant=_parse_constant,
            parse_float=_parse_float,
        )
    except StrictJsonParserBoundaryError:
        raise
    except (
        json.JSONDecodeError,
        UnicodeError,
        ValueError,
        OverflowError,
        RecursionError,
    ):
        raise StrictJsonParserBoundaryError("invalid JSON object rejected") from None
    if not isinstance(value, Mapping):
        raise StrictJsonParserBoundaryError("top-level JSON value is not an object")
    return value


def _inspect(
    value: Mapping[str, Any], *, contract: Mapping[str, Any]
) -> dict[str, int]:
    maximum_depth = int(contract["maximum_depth"])
    maximum_nodes = int(contract["maximum_nodes"])
    maximum_members = int(contract["maximum_object_members"])
    maximum_items = int(contract["maximum_array_items"])
    maximum_string = int(contract["maximum_string_characters"])
    node_count = 0
    observed_depth = 0
    string_characters = 0
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        node_count += 1
        observed_depth = max(observed_depth, depth)
        if node_count > maximum_nodes:
            raise StrictJsonParserBoundaryError("JSON node budget exceeded")
        if depth > maximum_depth:
            raise StrictJsonParserBoundaryError("JSON depth budget exceeded")
        if isinstance(current, Mapping):
            if len(current) > maximum_members:
                raise StrictJsonParserBoundaryError("JSON object member budget exceeded")
            for key, item in current.items():
                if not isinstance(key, str):
                    raise StrictJsonParserBoundaryError("JSON object key is invalid")
                if len(key) > maximum_string:
                    raise StrictJsonParserBoundaryError("JSON key string budget exceeded")
                string_characters += len(key)
                if _is_privileged_key(key):
                    raise StrictJsonParserBoundaryError(
                        "privileged JSON metadata key rejected"
                    )
                stack.append((item, depth + 1))
        elif isinstance(current, list):
            if len(current) > maximum_items:
                raise StrictJsonParserBoundaryError("JSON array item budget exceeded")
            for item in reversed(current):
                stack.append((item, depth + 1))
        elif isinstance(current, str):
            if len(current) > maximum_string:
                raise StrictJsonParserBoundaryError("JSON value string budget exceeded")
            string_characters += len(current)
        elif current is None or isinstance(current, (bool, int)):
            pass
        elif isinstance(current, float):
            if not math.isfinite(current):
                raise StrictJsonParserBoundaryError("non-finite JSON number rejected")
        else:
            raise StrictJsonParserBoundaryError("unsupported JSON value rejected")
        if string_characters > int(contract["maximum_text_characters"]):
            raise StrictJsonParserBoundaryError("JSON aggregate string budget exceeded")
    return {
        "node_count": node_count,
        "maximum_observed_depth": observed_depth,
        "string_character_count": string_characters,
    }


def _structure_sha256(
    *, top_level_member_count: int, metrics: Mapping[str, int]
) -> str:
    return object_sha256(
        {
            "policy_id": POLICY_ID,
            "top_level_member_count": top_level_member_count,
            "node_count": metrics["node_count"],
            "maximum_observed_depth": metrics["maximum_observed_depth"],
            "string_character_count": metrics["string_character_count"],
            "structure_summary_excludes_keys_and_scalar_values": True,
        }
    )


def _validated_scheduler_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("V2.42.44 scheduler receipt is not an object")
    scheduler = _clone(dict(value))
    validate_retry_deadline_execution_receipt(scheduler)
    return scheduler


def validate_strict_json_parser_receipt(value: Mapping[str, Any]) -> None:
    receipt = _exact(value, keys=RECEIPT_KEYS, label="parser receipt")
    contract = dict(receipt["parser_contract"])
    validate_strict_json_parser_contract(contract)
    scheduler = _validated_scheduler_receipt(
        receipt["scheduler_execution_receipt"]
    )
    parent = scheduler["parent_execution_receipt"]
    last_attempt = parent["measurement"]["attempts"][-1]
    for field in (
        "scheduler_execution_receipt_sha256",
        "parent_durable_execution_receipt_sha256",
        "meter_contract_sha256",
        "provider_response_ref_sha256",
        "parsed_structure_sha256",
    ):
        if not _is_sha256(receipt.get(field)):
            raise ValueError(f"V2.42.44 {field} is not SHA-256 bound")
    integers = {
        "input_text_characters": (2, int(contract["maximum_text_characters"])),
        "input_utf8_bytes": (2, int(contract["maximum_utf8_bytes"])),
        "top_level_member_count": (0, int(contract["maximum_object_members"])),
        "node_count": (1, int(contract["maximum_nodes"])),
        "maximum_observed_depth": (1, int(contract["maximum_depth"])),
        "string_character_count": (0, int(contract["maximum_text_characters"])),
    }
    for field, (minimum, maximum) in integers.items():
        _integer(
            receipt.get(field),
            label=field,
            minimum=minimum,
            maximum=maximum,
        )
    expected_structure = _structure_sha256(
        top_level_member_count=int(receipt["top_level_member_count"]),
        metrics={
            "node_count": int(receipt["node_count"]),
            "maximum_observed_depth": int(receipt["maximum_observed_depth"]),
            "string_character_count": int(receipt["string_character_count"]),
        },
    )
    if (
        receipt.get("artifact_version") != 1
        or receipt.get("role") != RECEIPT_ROLE
        or receipt.get("policy_id") != POLICY_ID
        or receipt.get("candidate_runtime") is not True
        or receipt.get("parser_contract_sha256")
        != contract.get("contract_sha256")
        or receipt.get("scheduler_execution_receipt_sha256")
        != scheduler.get("execution_receipt_sha256")
        or receipt.get("parent_durable_execution_receipt_sha256")
        != parent.get("execution_receipt_sha256")
        or receipt.get("meter_contract_sha256")
        != parent.get("meter_contract_sha256")
        or receipt.get("provider_response_ref_sha256")
        != last_attempt.get("provider_response_ref_sha256")
        or parent.get("logical_status") != "completed"
        or parent.get("settlement_commit") is None
        or parent.get("settlement_event") is None
        or parent.get("state_after_settlement_sha256")
        != parent["settlement_commit"].get("resulting_state_sha256")
        or parent.get("meter_contract", {}).get("provider_kind")
        != "azure_responses_model"
        or parent.get("meter_contract", {}).get("effect_kind") != "model_request"
        or receipt.get("envelope_kind") not in contract["accepted_envelopes"]
        or receipt.get("parsed_structure_sha256") != expected_structure
        or receipt.get("model_value_usage_matches_parent_attempt") is not True
        or receipt.get(
            "ephemeral_text_to_parent_response_binding_independently_verified"
        )
        is not False
        or receipt["node_count"] < receipt["top_level_member_count"] + 1
        or receipt["maximum_observed_depth"] > receipt["node_count"]
        or receipt["input_utf8_bytes"] < receipt["input_text_characters"]
        or receipt["input_utf8_bytes"] > receipt["input_text_characters"] * 4
        or receipt.get("post_durable_settlement_parse_boundary") is not True
        or receipt.get("duplicate_keys_rejected") is not True
        or receipt.get("nonfinite_numbers_rejected") is not True
        or receipt.get("structural_budget_enforced") is not True
        or receipt.get("nested_privileged_metadata_rejected") is not True
        or receipt.get("internal_repair_provider_effect_called") is not False
        or receipt.get("search_or_page_content_parsed") is not False
        or receipt.get("raw_text_directly_persisted_or_emitted") is not False
        or receipt.get("parser_created_raw_text_hash") is not False
        or receipt.get("parsed_raw_strings_persisted_hashed_or_emitted") is not False
        or receipt.get(
            "schema_resealing_without_secret_cryptographically_excluded"
        )
        is not False
        or receipt.get("credential_or_url_present") is not False
        or receipt.get("benchmark_or_evaluator_metadata_present") is not False
        or receipt.get("active_forward_integration_authorized") is not False
        or receipt.get("benchmark_forward_or_evaluator_authorized") is not False
        or not _sealed(receipt, key="parser_receipt_sha256")
    ):
        raise ValueError("V2.42.44 parser receipt drifted")


def parse_settled_model_json(
    result: RetryDeadlineExecutionResult,
    *,
    parser_contract: Mapping[str, Any],
) -> StrictJsonParseResult:
    """Parse one settled GPT-5.6 value without calling a repair provider."""

    contract = _clone(dict(parser_contract))
    validate_strict_json_parser_contract(contract)
    if not isinstance(result, RetryDeadlineExecutionResult):
        raise StrictJsonParserBoundaryError("scheduler result type is invalid")
    try:
        scheduler_receipt = _validated_scheduler_receipt(result.receipt)
    except (TypeError, ValueError):
        raise StrictJsonParserBoundaryError("scheduler receipt is invalid") from None
    parent = scheduler_receipt["parent_execution_receipt"]
    if (
        parent.get("logical_status") != "completed"
        or parent.get("settlement_commit") is None
        or parent.get("settlement_event") is None
        or parent.get("state_after_settlement_sha256")
        != parent["settlement_commit"].get("resulting_state_sha256")
        or parent.get("meter_contract", {}).get("provider_kind")
        != "azure_responses_model"
        or parent.get("meter_contract", {}).get("effect_kind") != "model_request"
        or parent.get("attempt_count") < 1
    ):
        raise StrictJsonParserBoundaryError("parent model settlement is invalid")
    model_value = result.value
    if not isinstance(model_value, AzureResponsesAttemptValue):
        raise StrictJsonParserBoundaryError("ephemeral model value type is invalid")
    if model_value.output_truncated:
        raise StrictJsonParserBoundaryError("truncated model output rejected")
    if not isinstance(model_value.text, str):
        raise StrictJsonParserBoundaryError("model text type is invalid")
    last_attempt = parent["measurement"]["attempts"][-1]
    if (
        not isinstance(model_value.usage, Mapping)
        or model_value.usage.get("input_tokens") != last_attempt.get("input_tokens")
        or model_value.usage.get("output_tokens")
        != last_attempt.get("output_tokens")
        or not isinstance(model_value.output_truncated, bool)
        or (
            model_value.response_id is not None
            and not isinstance(model_value.response_id, str)
        )
    ):
        raise StrictJsonParserBoundaryError(
            "ephemeral model value accounting binding is invalid"
        )
    text = model_value.text
    input_characters = len(text)
    if input_characters > int(contract["maximum_text_characters"]):
        raise StrictJsonParserBoundaryError("model text character budget exceeded")
    try:
        input_bytes = len(text.encode("utf-8"))
    except UnicodeEncodeError:
        raise StrictJsonParserBoundaryError("model text UTF-8 encoding rejected") from None
    if input_bytes > int(contract["maximum_utf8_bytes"]):
        raise StrictJsonParserBoundaryError("model text byte budget exceeded")
    envelope_kind, candidate = _envelope(text)
    parsed = _parse_object(candidate)
    metrics = _inspect(parsed, contract=contract)
    structure_sha = _structure_sha256(
        top_level_member_count=len(parsed),
        metrics=metrics,
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "candidate_runtime": True,
        "parser_contract": contract,
        "parser_contract_sha256": contract["contract_sha256"],
        "scheduler_execution_receipt": scheduler_receipt,
        "scheduler_execution_receipt_sha256": scheduler_receipt[
            "execution_receipt_sha256"
        ],
        "parent_durable_execution_receipt_sha256": parent[
            "execution_receipt_sha256"
        ],
        "meter_contract_sha256": parent["meter_contract_sha256"],
        "provider_response_ref_sha256": last_attempt[
            "provider_response_ref_sha256"
        ],
        "input_text_characters": input_characters,
        "input_utf8_bytes": input_bytes,
        "envelope_kind": envelope_kind,
        "top_level_member_count": len(parsed),
        "node_count": metrics["node_count"],
        "maximum_observed_depth": metrics["maximum_observed_depth"],
        "string_character_count": metrics["string_character_count"],
        "parsed_structure_sha256": structure_sha,
        "model_value_usage_matches_parent_attempt": True,
        "ephemeral_text_to_parent_response_binding_independently_verified": False,
        "post_durable_settlement_parse_boundary": True,
        "duplicate_keys_rejected": True,
        "nonfinite_numbers_rejected": True,
        "structural_budget_enforced": True,
        "nested_privileged_metadata_rejected": True,
        "internal_repair_provider_effect_called": False,
        "search_or_page_content_parsed": False,
        "raw_text_directly_persisted_or_emitted": False,
        "parser_created_raw_text_hash": False,
        "parsed_raw_strings_persisted_hashed_or_emitted": False,
        "schema_resealing_without_secret_cryptographically_excluded": False,
        "credential_or_url_present": False,
        "benchmark_or_evaluator_metadata_present": False,
        "active_forward_integration_authorized": False,
        "benchmark_forward_or_evaluator_authorized": False,
    }
    value["parser_receipt_sha256"] = object_sha256(value)
    validate_strict_json_parser_receipt(value)
    return StrictJsonParseResult(receipt=value, value=_clone(dict(parsed)))
