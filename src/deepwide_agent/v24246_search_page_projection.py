"""Strict post-settlement projections for search leads and fetched pages.

Search-provider answer text, summaries, action queries, scores, citations, and
result metadata are not page evidence.  This isolated candidate accepts only a
validated V2.42.43 success result after durable settlement, projects canonical
public fetch URLs from typed search values into untrusted leads, and discards
all provider prose.  A separate path accepts the V2.42.45 native-fetch value,
verifies its bytes against the settled attempt hash and length, decodes a
bounded text representation, and marks every character as untrusted data with
no instruction authority.

The module performs no model, search, fetch, repair, file, environment, or
network operation.  Search typed values remain only type/accounting bound to
their parent attempt because the earlier adapters do not bind each ephemeral
field to the response bytes.  The fetched-page path can bind the retained body
bytes to its parent hash, but neither path proves truth, relevance, source
independence, prompt-injection safety, or active-evidence eligibility.  This
module is not imported by active clients, runtime, runner, launcher, benchmark,
or evaluator code.
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import html
import ipaddress
import re
import unicodedata
from html.parser import HTMLParser
from typing import Any, Mapping, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from deepwide_agent.v24232_webswarm_total_budget import object_sha256
from deepwide_agent.v24237_tavily_search_single_attempt import (
    TavilySearchAttemptValue,
)
from deepwide_agent.v24239_azure_hosted_search_single_attempt import (
    AzureHostedSearchAttemptValue,
)
from deepwide_agent.v24240_anthropic_server_search_single_attempt import (
    AnthropicServerSearchAttemptValue,
)
from deepwide_agent.v24243_retry_deadline_scheduler import (
    RetryDeadlineExecutionResult,
    validate_retry_deadline_execution_receipt,
)
from deepwide_agent.v24245_pinned_native_http_fetch import (
    NativeHttpFetchAttemptValue,
)


POLICY_ID = "v24246_search_page_projection_v1"
CONTRACT_ROLE = "v24246_search_page_projection_contract"
RECEIPT_ROLE = "v24246_search_page_projection_receipt"

PRODUCTION_PACKAGE_AUTHORIZED = False
ACTIVE_FORWARD_INTEGRATION_AUTHORIZED = False
ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED = False
EXTERNAL_SIDE_EFFECT_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
DEV64_OR_EXACT220_LAUNCH_AUTHORIZED = False
SHARED_API_LEASE_ACQUIRE_AUTHORIZED = False
LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED = False

POST_DURABLE_SETTLEMENT_PROJECTION_IMPLEMENTED = True
SEARCH_PROVIDER_ANSWER_SNIPPET_QUERY_SCORE_AND_METADATA_DISCARDED = True
SEARCH_LEADS_ARE_PAGE_EVIDENCE = False
FETCH_BODY_HASH_AND_LENGTH_BINDING_IMPLEMENTED = True
UNTRUSTED_PAGE_TEXT_INSTRUCTION_AUTHORITY = False
ACTIVE_EVIDENCE_ELIGIBILITY_GRANTED = False
INTERNAL_REPAIR_OR_PROVIDER_EFFECT_IMPLEMENTED = False
SEARCH_TYPED_VALUE_TO_PARENT_RESPONSE_BINDING_INDEPENDENTLY_VERIFIED = False
FETCH_BODY_BYTES_TO_PARENT_RESPONSE_BINDING_INDEPENDENTLY_VERIFIED = True
FETCH_URL_CONTENT_TYPE_TO_PARENT_RESPONSE_BINDING_INDEPENDENTLY_VERIFIED = False
PROMPT_INJECTION_SAFETY_INDEPENDENTLY_VERIFIED = False
SOURCE_TRUTH_RELEVANCE_OR_INDEPENDENCE_VERIFIED = False

MAX_LEADS = 4096
MAX_PAGE_BYTES = 32_000_000
MAX_PAGE_TEXT_CHARACTERS = 4_000_000
MAX_TITLE_CHARACTERS = 4096
MAX_URL_CHARACTERS = 8192
MAX_HTML_TAGS = 1_000_000
TRACKING_QUERY_KEYS = frozenset(
    {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "ref_src"}
)
SENSITIVE_QUERY_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "apikey",
        "auth",
        "authorization",
        "credential",
        "key",
        "password",
        "secret",
        "sig",
        "signature",
        "token",
        "x-amz-credential",
        "x-amz-security-token",
        "x-amz-signature",
    }
)
SENSITIVE_COMPACT_QUERY_KEYS = frozenset(
    re.sub(r"[^a-z0-9]+", "", key) for key in SENSITIVE_QUERY_KEYS
)
CONTRACT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "candidate_runtime",
        "maximum_leads",
        "maximum_page_bytes",
        "maximum_page_text_characters",
        "maximum_title_characters",
        "maximum_url_characters",
        "maximum_html_tags",
        "accepted_search_provider_kinds",
        "accepted_fetch_provider_kind",
        "search_provider_content_policy",
        "search_lead_evidence_policy",
        "page_text_trust_policy",
        "active_evidence_eligibility_policy",
        "internal_repair_or_provider_effect_authorized",
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
        "projection_kind",
        "projection_contract",
        "projection_contract_sha256",
        "scheduler_execution_receipt",
        "scheduler_execution_receipt_sha256",
        "parent_durable_execution_receipt_sha256",
        "meter_contract_sha256",
        "provider_kind",
        "provider_response_ref_sha256",
        "parent_response_body_bytes",
        "source_item_count",
        "projected_item_count",
        "deduplicated_item_count",
        "dropped_item_count",
        "retained_body_bytes",
        "projected_text_characters",
        "projection_structure_sha256",
        "search_provider_answer_snippet_query_score_and_metadata_discarded",
        "search_leads_are_page_evidence",
        "fetch_body_hash_and_length_matches_parent_attempt",
        "search_typed_value_to_parent_response_binding_independently_verified",
        "fetch_body_bytes_to_parent_response_binding_independently_verified",
        "fetch_url_content_type_to_parent_response_binding_independently_verified",
        "page_text_is_untrusted_data",
        "page_text_instruction_authority",
        "active_evidence_eligibility_granted",
        "prompt_injection_safety_independently_verified",
        "source_truth_relevance_or_independence_verified",
        "internal_repair_or_provider_effect_called",
        "provider_answer_summary_snippet_raw_content_query_score_cited_text_or_action_metadata_returned",
        "raw_page_bytes_persisted_or_emitted_by_projector",
        "projected_text_or_url_persisted_hashed_or_emitted_in_receipt",
        "schema_resealing_without_secret_cryptographically_excluded",
        "credential_environment_or_keyring_read",
        "benchmark_or_evaluator_metadata_used_for_routing",
        "benchmark_or_evaluator_metadata_absence_in_projected_content_independently_verified",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "projection_receipt_sha256",
    }
)
SEARCH_PROVIDERS = frozenset(
    {
        "tavily_search_api",
        "azure_responses_web_search",
        "anthropic_server_web_search",
    }
)


class SearchPageProjectionError(ValueError):
    """Sanitized rejection that never embeds provider or page content."""


@dataclasses.dataclass(frozen=True)
class SearchLeadProjection:
    canonical_url: str
    fetch_url: str
    title: str
    source_kind: str


@dataclasses.dataclass(frozen=True)
class PageTextProjection:
    canonical_url: str
    content_type: str
    text: str
    source_kind: str
    truncated: bool
    untrusted_data: bool = True
    instruction_authority: bool = False
    active_evidence_eligible: bool = False


@dataclasses.dataclass(frozen=True)
class SearchPageProjectionResult:
    receipt: Mapping[str, Any]
    value: tuple[SearchLeadProjection, ...] | PageTextProjection


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
        raise ValueError(f"V2.42.46 {label} schema is not exact")
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
    maximum: int = 1_000_000_000,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise ValueError(f"V2.42.46 {label} is outside the frozen range")
    return value


def build_search_page_projection_contract(
    *,
    maximum_leads: int,
    maximum_page_bytes: int,
    maximum_page_text_characters: int,
    maximum_title_characters: int,
    maximum_url_characters: int,
    maximum_html_tags: int,
) -> dict[str, Any]:
    leads = _integer(
        maximum_leads,
        label="maximum leads",
        minimum=1,
        maximum=MAX_LEADS,
    )
    page_bytes = _integer(
        maximum_page_bytes,
        label="maximum page bytes",
        minimum=1,
        maximum=MAX_PAGE_BYTES,
    )
    text_chars = _integer(
        maximum_page_text_characters,
        label="maximum page text characters",
        minimum=1,
        maximum=MAX_PAGE_TEXT_CHARACTERS,
    )
    title_chars = _integer(
        maximum_title_characters,
        label="maximum title characters",
        minimum=1,
        maximum=MAX_TITLE_CHARACTERS,
    )
    url_chars = _integer(
        maximum_url_characters,
        label="maximum URL characters",
        minimum=1,
        maximum=MAX_URL_CHARACTERS,
    )
    html_tags = _integer(
        maximum_html_tags,
        label="maximum HTML tags",
        minimum=1,
        maximum=MAX_HTML_TAGS,
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": CONTRACT_ROLE,
        "policy_id": POLICY_ID,
        "candidate_runtime": True,
        "maximum_leads": leads,
        "maximum_page_bytes": page_bytes,
        "maximum_page_text_characters": text_chars,
        "maximum_title_characters": title_chars,
        "maximum_url_characters": url_chars,
        "maximum_html_tags": html_tags,
        "accepted_search_provider_kinds": sorted(SEARCH_PROVIDERS),
        "accepted_fetch_provider_kind": "native_http_fetch",
        "search_provider_content_policy": "retain_only_canonical_url_fetch_url_and_bounded_title_discard_answer_summary_snippet_raw_content_queries_scores_cited_text_response_ids_page_age_and_action_metadata",
        "search_lead_evidence_policy": "untrusted_discovery_lead_only_not_page_evidence",
        "page_text_trust_policy": "untrusted_data_zero_instruction_authority",
        "active_evidence_eligibility_policy": "never_granted_by_projection",
        "internal_repair_or_provider_effect_authorized": False,
        "active_forward_integration_authorized": False,
        "benchmark_forward_or_evaluator_authorized": False,
    }
    value["contract_sha256"] = object_sha256(value)
    return value


def validate_search_page_projection_contract(value: Mapping[str, Any]) -> None:
    contract = _exact(value, keys=CONTRACT_KEYS, label="projection contract")
    try:
        expected = build_search_page_projection_contract(
            maximum_leads=contract.get("maximum_leads"),
            maximum_page_bytes=contract.get("maximum_page_bytes"),
            maximum_page_text_characters=contract.get(
                "maximum_page_text_characters"
            ),
            maximum_title_characters=contract.get("maximum_title_characters"),
            maximum_url_characters=contract.get("maximum_url_characters"),
            maximum_html_tags=contract.get("maximum_html_tags"),
        )
    except (TypeError, ValueError):
        raise ValueError("V2.42.46 projection contract drifted") from None
    if dict(contract) != expected or not _sealed(contract, key="contract_sha256"):
        raise ValueError("V2.42.46 projection contract drifted")


def _validated_scheduler_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("V2.42.46 scheduler receipt is not an object")
    scheduler = _clone(dict(value))
    validate_retry_deadline_execution_receipt(scheduler)
    return scheduler


def _settled_parent(
    result: RetryDeadlineExecutionResult,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not isinstance(result, RetryDeadlineExecutionResult):
        raise SearchPageProjectionError("scheduler result type is invalid")
    try:
        scheduler = _validated_scheduler_receipt(result.receipt)
    except (TypeError, ValueError):
        raise SearchPageProjectionError("scheduler receipt is invalid") from None
    parent = scheduler["parent_execution_receipt"]
    if (
        parent.get("logical_status") != "completed"
        or parent.get("settlement_commit") is None
        or parent.get("settlement_event") is None
        or parent.get("state_after_settlement_sha256")
        != parent["settlement_commit"].get("resulting_state_sha256")
        or parent.get("attempt_count") < 1
    ):
        raise SearchPageProjectionError("parent settlement is invalid")
    return scheduler, parent, parent["measurement"]["attempts"][-1]


def _safe_url(value: object, *, maximum: int) -> tuple[str, str] | None:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > maximum
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        return None
    try:
        parsed = urlsplit(value)
        explicit_port = parsed.port
    except ValueError:
        return None
    scheme = parsed.scheme.casefold()
    if (
        scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or explicit_port is not None
    ):
        return None
    try:
        hostname = parsed.hostname.rstrip(".").encode("idna").decode("ascii").casefold()
    except UnicodeError:
        return None
    if not hostname or hostname == "localhost" or hostname.endswith(".localhost"):
        return None
    try:
        literal = ipaddress.ip_address(hostname.split("%", 1)[0])
    except ValueError:
        literal = None
    if literal is not None:
        if isinstance(literal, ipaddress.IPv6Address) and literal.ipv4_mapped:
            literal = literal.ipv4_mapped
        if not literal.is_global:
            return None
    try:
        pairs = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=False)
    except ValueError:
        return None
    normalized_keys = [
        unicodedata.normalize("NFKC", key).casefold() for key, _item in pairs
    ]
    compact_keys = {
        re.sub(r"[^a-z0-9]+", "", key) for key in normalized_keys
    }
    if compact_keys & SENSITIVE_COMPACT_QUERY_KEYS:
        return None
    canonical_pairs = [
        (key, item)
        for key, item in pairs
        if not re.sub(
            r"[^a-z0-9]+",
            "",
            unicodedata.normalize("NFKC", key).casefold(),
        ).startswith("utm")
        and unicodedata.normalize("NFKC", key).casefold()
        not in TRACKING_QUERY_KEYS
    ]
    host = f"[{hostname}]" if ":" in hostname else hostname
    path = parsed.path.rstrip("/") or "/"
    canonical = urlunsplit(
        (scheme, host, path, urlencode(canonical_pairs, doseq=True), "")
    )
    fetch_url = urlunsplit(
        (scheme, host, parsed.path or "/", parsed.query, "")
    )
    if len(canonical) > maximum or len(fetch_url) > maximum:
        return None
    return canonical, fetch_url


def _safe_title(value: object, *, maximum: int) -> str:
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFKC", value)
    normalized = "".join(
        character
        for character in normalized
        if not unicodedata.category(character).startswith("C")
    )
    normalized = " ".join(normalized.split())
    return normalized[:maximum]


def _lead_candidates(value: Any) -> tuple[str, Sequence[tuple[Any, Any]]]:
    try:
        if isinstance(value, TavilySearchAttemptValue):
            if not isinstance(value.results, tuple):
                raise TypeError
            return "tavily_result", tuple(
                (item.url, item.title) for item in value.results
            )
        if isinstance(value, AzureHostedSearchAttemptValue):
            if not isinstance(value.actions, tuple) or not isinstance(
                value.citations, tuple
            ):
                raise TypeError
            sources = [
                (source.fetch_url, source.title)
                for action in value.actions
                for source in action.sources
            ]
            sources.extend(
                (citation.fetch_url, citation.title)
                for citation in value.citations
            )
            return "azure_hosted_source", tuple(sources)
        if isinstance(value, AnthropicServerSearchAttemptValue):
            if not isinstance(value.results, tuple) or not isinstance(
                value.citations, tuple
            ):
                raise TypeError
            sources = [(item.fetch_url, item.title) for item in value.results]
            sources.extend(
                (citation.fetch_url, citation.title)
                for citation in value.citations
            )
            return "anthropic_server_source", tuple(sources)
    except (AttributeError, TypeError):
        raise SearchPageProjectionError(
            "ephemeral search value structure is invalid"
        ) from None
    raise SearchPageProjectionError("ephemeral search value type is invalid")


def _search_value_accounting_matches(
    value: Any, *, provider_kind: str, last_attempt: Mapping[str, Any]
) -> bool:
    if provider_kind == "tavily_search_api":
        return isinstance(value, TavilySearchAttemptValue)
    if provider_kind == "azure_responses_web_search":
        return (
            isinstance(value, AzureHostedSearchAttemptValue)
            and value.usage.get("input_tokens") == last_attempt.get("input_tokens")
            and value.usage.get("output_tokens") == last_attempt.get("output_tokens")
            and len(value.actions) == last_attempt.get("provider_tool_calls")
            and value.output_truncated is False
        )
    if provider_kind == "anthropic_server_web_search":
        return (
            isinstance(value, AnthropicServerSearchAttemptValue)
            and value.usage.get("metered_input_tokens") == last_attempt.get("input_tokens")
            and value.usage.get("output_tokens") == last_attempt.get("output_tokens")
            and len(value.actions) == last_attempt.get("provider_tool_calls")
            and value.output_truncated is False
        )
    return False


class _BoundedHtmlTextParser(HTMLParser):
    def __init__(self, *, maximum_characters: int, maximum_tags: int) -> None:
        super().__init__(convert_charrefs=True)
        self.maximum_characters = maximum_characters
        self.maximum_tags = maximum_tags
        self.tag_count = 0
        self.parts: list[str] = []
        self.characters = 0
        self.suppressed_depth = 0
        self.truncated = False

    def _tag(self) -> None:
        self.tag_count += 1
        if self.tag_count > self.maximum_tags:
            raise SearchPageProjectionError("HTML tag budget exceeded")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        self._tag()
        if tag.casefold() in {"script", "style", "template", "noscript"}:
            self.suppressed_depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del tag, attrs
        self._tag()

    def handle_endtag(self, tag: str) -> None:
        self._tag()
        if tag.casefold() in {"script", "style", "template", "noscript"}:
            self.suppressed_depth = max(0, self.suppressed_depth - 1)

    def handle_data(self, data: str) -> None:
        if self.suppressed_depth or not data or self.truncated:
            return
        remaining = self.maximum_characters - self.characters
        if remaining <= 0:
            self.truncated = True
            return
        item = data[:remaining]
        self.parts.append(item)
        self.characters += len(item)
        if len(item) != len(data):
            self.truncated = True


def _decode_page(
    body: bytes,
    *,
    content_type: str,
    maximum_characters: int,
    maximum_tags: int,
) -> tuple[str, bool]:
    try:
        decoded = body.decode("utf-8", errors="replace")
    except Exception:
        raise SearchPageProjectionError("page decoding failed") from None
    media = content_type.split(";", 1)[0].strip().casefold()
    if media in {"text/html", "application/xhtml+xml"}:
        parser = _BoundedHtmlTextParser(
            maximum_characters=maximum_characters,
            maximum_tags=maximum_tags,
        )
        try:
            parser.feed(decoded)
            parser.close()
        except SearchPageProjectionError:
            raise
        except Exception:
            raise SearchPageProjectionError("HTML text projection failed") from None
        raw = " ".join(parser.parts)
        truncated = parser.truncated
    elif (
        media.startswith("text/")
        or media in {"application/json", "application/xml", "application/xhtml+xml"}
        or not media
    ):
        raw = decoded[:maximum_characters]
        truncated = len(decoded) > maximum_characters
    else:
        raise SearchPageProjectionError("unsupported page content type rejected")
    projected = " ".join(html.unescape(raw).split())
    if len(projected) > maximum_characters:
        projected = projected[:maximum_characters]
        truncated = True
    if not projected:
        raise SearchPageProjectionError("empty page text projection rejected")
    return projected, truncated


def _projection_structure_sha256(
    *,
    projection_kind: str,
    source_item_count: int,
    projected_item_count: int,
    deduplicated_item_count: int,
    dropped_item_count: int,
    retained_body_bytes: int,
    projected_text_characters: int,
) -> str:
    return object_sha256(
        {
            "policy_id": POLICY_ID,
            "projection_kind": projection_kind,
            "source_item_count": source_item_count,
            "projected_item_count": projected_item_count,
            "deduplicated_item_count": deduplicated_item_count,
            "dropped_item_count": dropped_item_count,
            "retained_body_bytes": retained_body_bytes,
            "projected_text_characters": projected_text_characters,
            "structure_summary_excludes_text_titles_urls_and_scalar_content": True,
        }
    )


def _receipt(
    *,
    contract: Mapping[str, Any],
    scheduler: Mapping[str, Any],
    parent: Mapping[str, Any],
    last_attempt: Mapping[str, Any],
    projection_kind: str,
    source_item_count: int,
    projected_item_count: int,
    deduplicated_item_count: int,
    dropped_item_count: int,
    retained_body_bytes: int,
    projected_text_characters: int,
    fetch_bound: bool,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "candidate_runtime": True,
        "projection_kind": projection_kind,
        "projection_contract": _clone(dict(contract)),
        "projection_contract_sha256": contract["contract_sha256"],
        "scheduler_execution_receipt": _clone(dict(scheduler)),
        "scheduler_execution_receipt_sha256": scheduler["execution_receipt_sha256"],
        "parent_durable_execution_receipt_sha256": parent["execution_receipt_sha256"],
        "meter_contract_sha256": parent["meter_contract_sha256"],
        "provider_kind": parent["meter_contract"]["provider_kind"],
        "provider_response_ref_sha256": last_attempt["provider_response_ref_sha256"],
        "parent_response_body_bytes": last_attempt["response_body_bytes"],
        "source_item_count": source_item_count,
        "projected_item_count": projected_item_count,
        "deduplicated_item_count": deduplicated_item_count,
        "dropped_item_count": dropped_item_count,
        "retained_body_bytes": retained_body_bytes,
        "projected_text_characters": projected_text_characters,
        "projection_structure_sha256": _projection_structure_sha256(
            projection_kind=projection_kind,
            source_item_count=source_item_count,
            projected_item_count=projected_item_count,
            deduplicated_item_count=deduplicated_item_count,
            dropped_item_count=dropped_item_count,
            retained_body_bytes=retained_body_bytes,
            projected_text_characters=projected_text_characters,
        ),
        "search_provider_answer_snippet_query_score_and_metadata_discarded": True,
        "search_leads_are_page_evidence": False,
        "fetch_body_hash_and_length_matches_parent_attempt": fetch_bound,
        "search_typed_value_to_parent_response_binding_independently_verified": False,
        "fetch_body_bytes_to_parent_response_binding_independently_verified": fetch_bound,
        "fetch_url_content_type_to_parent_response_binding_independently_verified": False,
        "page_text_is_untrusted_data": projection_kind == "untrusted_page_text",
        "page_text_instruction_authority": False,
        "active_evidence_eligibility_granted": False,
        "prompt_injection_safety_independently_verified": False,
        "source_truth_relevance_or_independence_verified": False,
        "internal_repair_or_provider_effect_called": False,
        "provider_answer_summary_snippet_raw_content_query_score_cited_text_or_action_metadata_returned": False,
        "raw_page_bytes_persisted_or_emitted_by_projector": False,
        "projected_text_or_url_persisted_hashed_or_emitted_in_receipt": False,
        "schema_resealing_without_secret_cryptographically_excluded": False,
        "credential_environment_or_keyring_read": False,
        "benchmark_or_evaluator_metadata_used_for_routing": False,
        "benchmark_or_evaluator_metadata_absence_in_projected_content_independently_verified": False,
        "active_forward_integration_authorized": False,
        "benchmark_forward_or_evaluator_authorized": False,
    }
    value["projection_receipt_sha256"] = object_sha256(value)
    validate_search_page_projection_receipt(value)
    return value


def validate_search_page_projection_receipt(value: Mapping[str, Any]) -> None:
    receipt = _exact(value, keys=RECEIPT_KEYS, label="projection receipt")
    contract = dict(receipt["projection_contract"])
    validate_search_page_projection_contract(contract)
    scheduler = _validated_scheduler_receipt(receipt["scheduler_execution_receipt"])
    parent = scheduler["parent_execution_receipt"]
    last_attempt = parent["measurement"]["attempts"][-1]
    for field in (
        "projection_contract_sha256",
        "scheduler_execution_receipt_sha256",
        "parent_durable_execution_receipt_sha256",
        "meter_contract_sha256",
        "provider_response_ref_sha256",
        "projection_structure_sha256",
    ):
        if not _is_sha256(receipt.get(field)):
            raise ValueError(f"V2.42.46 {field} is not SHA-256 bound")
    integer_limits = {
        "parent_response_body_bytes": MAX_PAGE_BYTES * 4,
        "source_item_count": MAX_LEADS * 16,
        "projected_item_count": int(contract["maximum_leads"]),
        "deduplicated_item_count": MAX_LEADS * 16,
        "dropped_item_count": MAX_LEADS * 16,
        "retained_body_bytes": int(contract["maximum_page_bytes"]),
        "projected_text_characters": int(contract["maximum_page_text_characters"]),
    }
    for field, maximum in integer_limits.items():
        _integer(receipt.get(field), label=field, maximum=maximum)
    kind = receipt.get("projection_kind")
    provider = receipt.get("provider_kind")
    fetch_kind = kind == "untrusted_page_text"
    search_kind = kind == "untrusted_search_leads"
    expected_structure = _projection_structure_sha256(
        projection_kind=str(kind),
        source_item_count=int(receipt["source_item_count"]),
        projected_item_count=int(receipt["projected_item_count"]),
        deduplicated_item_count=int(receipt["deduplicated_item_count"]),
        dropped_item_count=int(receipt["dropped_item_count"]),
        retained_body_bytes=int(receipt["retained_body_bytes"]),
        projected_text_characters=int(receipt["projected_text_characters"]),
    )
    if (
        receipt.get("artifact_version") != 1
        or receipt.get("role") != RECEIPT_ROLE
        or receipt.get("policy_id") != POLICY_ID
        or receipt.get("candidate_runtime") is not True
        or receipt.get("projection_contract_sha256") != contract["contract_sha256"]
        or receipt.get("scheduler_execution_receipt_sha256")
        != scheduler["execution_receipt_sha256"]
        or receipt.get("parent_durable_execution_receipt_sha256")
        != parent["execution_receipt_sha256"]
        or receipt.get("meter_contract_sha256") != parent["meter_contract_sha256"]
        or provider != parent["meter_contract"]["provider_kind"]
        or receipt.get("provider_response_ref_sha256")
        != last_attempt["provider_response_ref_sha256"]
        or receipt.get("parent_response_body_bytes")
        != last_attempt["response_body_bytes"]
        or parent.get("logical_status") != "completed"
        or parent.get("settlement_commit") is None
        or parent.get("settlement_event") is None
        or last_attempt.get("outcome") != "success"
        or last_attempt.get("http_status") is None
        or not _is_sha256(last_attempt.get("provider_response_ref_sha256"))
        or last_attempt.get("response_body_bytes") is None
        or not ((search_kind and provider in SEARCH_PROVIDERS) or (fetch_kind and provider == "native_http_fetch"))
        or receipt["source_item_count"]
        != receipt["projected_item_count"]
        + receipt["deduplicated_item_count"]
        + receipt["dropped_item_count"]
        or search_kind
        and (
            receipt["projected_item_count"] < 1
            or receipt["retained_body_bytes"] != 0
            or receipt["projected_text_characters"] != 0
            or receipt["fetch_body_hash_and_length_matches_parent_attempt"] is not False
            or receipt["fetch_body_bytes_to_parent_response_binding_independently_verified"] is not False
            or receipt["page_text_is_untrusted_data"] is not False
        )
        or fetch_kind
        and (
            receipt["source_item_count"] != 1
            or receipt["projected_item_count"] != 1
            or receipt["deduplicated_item_count"] != 0
            or receipt["dropped_item_count"] != 0
            or receipt["retained_body_bytes"] != receipt["parent_response_body_bytes"]
            or receipt["projected_text_characters"] < 1
            or receipt["fetch_body_hash_and_length_matches_parent_attempt"] is not True
            or receipt["fetch_body_bytes_to_parent_response_binding_independently_verified"] is not True
            or receipt["page_text_is_untrusted_data"] is not True
        )
        or receipt.get("projection_structure_sha256") != expected_structure
        or receipt.get("search_provider_answer_snippet_query_score_and_metadata_discarded") is not True
        or receipt.get("search_leads_are_page_evidence") is not False
        or receipt.get("search_typed_value_to_parent_response_binding_independently_verified") is not False
        or receipt.get("fetch_url_content_type_to_parent_response_binding_independently_verified") is not False
        or receipt.get("page_text_instruction_authority") is not False
        or receipt.get("active_evidence_eligibility_granted") is not False
        or receipt.get("prompt_injection_safety_independently_verified") is not False
        or receipt.get("source_truth_relevance_or_independence_verified") is not False
        or receipt.get("internal_repair_or_provider_effect_called") is not False
        or receipt.get("provider_answer_summary_snippet_raw_content_query_score_cited_text_or_action_metadata_returned") is not False
        or receipt.get("raw_page_bytes_persisted_or_emitted_by_projector") is not False
        or receipt.get("projected_text_or_url_persisted_hashed_or_emitted_in_receipt") is not False
        or receipt.get("schema_resealing_without_secret_cryptographically_excluded") is not False
        or receipt.get("credential_environment_or_keyring_read") is not False
        or receipt.get("benchmark_or_evaluator_metadata_used_for_routing") is not False
        or receipt.get("benchmark_or_evaluator_metadata_absence_in_projected_content_independently_verified") is not False
        or receipt.get("active_forward_integration_authorized") is not False
        or receipt.get("benchmark_forward_or_evaluator_authorized") is not False
        or not _sealed(receipt, key="projection_receipt_sha256")
    ):
        raise ValueError("V2.42.46 projection receipt drifted")


def project_settled_search_leads(
    result: RetryDeadlineExecutionResult,
    *,
    projection_contract: Mapping[str, Any],
) -> SearchPageProjectionResult:
    contract = _clone(dict(projection_contract))
    validate_search_page_projection_contract(contract)
    scheduler, parent, last_attempt = _settled_parent(result)
    provider = parent["meter_contract"]["provider_kind"]
    if (
        provider not in SEARCH_PROVIDERS
        or parent["meter_contract"]["effect_kind"]
        not in {"search_request", "hosted_web_search"}
        or not _search_value_accounting_matches(
            result.value,
            provider_kind=provider,
            last_attempt=last_attempt,
        )
    ):
        raise SearchPageProjectionError("parent search settlement is invalid")
    source_kind, candidates = _lead_candidates(result.value)
    source_count = len(candidates)
    if source_count > MAX_LEADS * 16:
        raise SearchPageProjectionError("search lead source budget exceeded")
    projected: list[SearchLeadProjection] = []
    seen: set[str] = set()
    dropped = 0
    deduplicated = 0
    for raw_url, raw_title in candidates:
        normalized = _safe_url(raw_url, maximum=int(contract["maximum_url_characters"]))
        if normalized is None:
            dropped += 1
            continue
        canonical_url, fetch_url = normalized
        if canonical_url in seen:
            deduplicated += 1
            continue
        if len(projected) >= int(contract["maximum_leads"]):
            dropped += 1
            continue
        seen.add(canonical_url)
        projected.append(
            SearchLeadProjection(
                canonical_url=canonical_url,
                fetch_url=fetch_url,
                title=_safe_title(
                    raw_title,
                    maximum=int(contract["maximum_title_characters"]),
                ),
                source_kind=source_kind,
            )
        )
    if not projected:
        raise SearchPageProjectionError("no safe search lead remained")
    receipt = _receipt(
        contract=contract,
        scheduler=scheduler,
        parent=parent,
        last_attempt=last_attempt,
        projection_kind="untrusted_search_leads",
        source_item_count=source_count,
        projected_item_count=len(projected),
        deduplicated_item_count=deduplicated,
        dropped_item_count=dropped,
        retained_body_bytes=0,
        projected_text_characters=0,
        fetch_bound=False,
    )
    return SearchPageProjectionResult(receipt=receipt, value=tuple(projected))


def project_settled_fetched_page(
    result: RetryDeadlineExecutionResult,
    *,
    projection_contract: Mapping[str, Any],
) -> SearchPageProjectionResult:
    contract = _clone(dict(projection_contract))
    validate_search_page_projection_contract(contract)
    scheduler, parent, last_attempt = _settled_parent(result)
    fetch = result.value
    if (
        parent["meter_contract"]["provider_kind"] != "native_http_fetch"
        or parent["meter_contract"]["effect_kind"] != "fetch_request"
        or not isinstance(fetch, NativeHttpFetchAttemptValue)
        or not isinstance(fetch.body, bytes)
        or not fetch.body
        or len(fetch.body) > int(contract["maximum_page_bytes"])
        or len(fetch.body) != last_attempt.get("response_body_bytes")
        or hashlib.sha256(fetch.body).hexdigest()
        != last_attempt.get("provider_response_ref_sha256")
        or not isinstance(fetch.url, str)
        or not isinstance(fetch.content_type, str)
        or not isinstance(fetch.truncated, bool)
    ):
        raise SearchPageProjectionError("parent fetch settlement is invalid")
    normalized = _safe_url(
        fetch.url,
        maximum=int(contract["maximum_url_characters"]),
    )
    if normalized is None:
        raise SearchPageProjectionError("fetched page URL is invalid")
    text, text_truncated = _decode_page(
        fetch.body,
        content_type=fetch.content_type,
        maximum_characters=int(contract["maximum_page_text_characters"]),
        maximum_tags=int(contract["maximum_html_tags"]),
    )
    page = PageTextProjection(
        canonical_url=normalized[0],
        content_type=fetch.content_type[:1024],
        text=text,
        source_kind="native_fetched_page",
        truncated=fetch.truncated or text_truncated,
    )
    receipt = _receipt(
        contract=contract,
        scheduler=scheduler,
        parent=parent,
        last_attempt=last_attempt,
        projection_kind="untrusted_page_text",
        source_item_count=1,
        projected_item_count=1,
        deduplicated_item_count=0,
        dropped_item_count=0,
        retained_body_bytes=len(fetch.body),
        projected_text_characters=len(text),
        fetch_bound=True,
    )
    return SearchPageProjectionResult(receipt=receipt, value=page)
