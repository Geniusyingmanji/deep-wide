"""Runner-shaped facade with explicit, fail-closed page-evidence admission.

V2.42.50 exposes typed model, search-lead, and fetched-page operations, while
the legacy DeepWide runtime expects ``complete_json``, ``search_many``, and an
optional ``fetch_urls`` method.  A mechanical method-name adapter would be
unsafe: legacy ``add_search_batches`` treats any non-empty ``raw_content`` as a
page, even though V2.42.46 deliberately grants neither search leads nor page
text active-evidence eligibility.

This isolated candidate closes that local handoff.  Search-provider prose is
never returned.  A projected lead is first fetched through the same exact
V2.42.50 ledger; only an exact, content-type-allowed page projection whose
canonical URL equals the lead can receive a content-free admission receipt and
be represented as legacy ``raw_content``.  The output retains an admission
reference in ``source_type`` so the old ingestion path does not silently erase
the boundary.  Direct fetch requests must match an in-memory lead previously
observed by this bridge and are rejected before a new durable claim otherwise.

Admission means only that bounded bytes from the pinned fetch may be supplied
to the agent as *untrusted data*.  It does not grant instruction authority or
prove truth, relevance, source independence, prompt-injection safety, or
cryptographic URL/content-type-to-response binding.  The equality checks use
exact immutable values in one process and are intentionally not persisted as
URL or text hashes.  The module is not imported by active clients, runtime,
runner, launcher, benchmark, or evaluator code and authorizes no traffic.
"""

from __future__ import annotations

import copy
import dataclasses
import threading
from typing import Any, Iterable, Mapping

from deepwide_agent.v24232_webswarm_total_budget import object_sha256
from deepwide_agent.v24246_search_page_projection import (
    PageTextProjection,
    SearchLeadProjection,
    validate_search_page_projection_receipt,
)
from deepwide_agent.v24248_candidate_client_facade import (
    validate_candidate_client_facade_contract,
    validate_candidate_client_facade_receipt,
)
from deepwide_agent.v24249_durable_action_registry import (
    validate_registered_facade_receipt,
)
from deepwide_agent.v24250_durable_action_outcome_ledger import (
    DurableActionOutcomeLedger,
    DurableOutcomeBoundFacadeResult,
    validate_durable_action_success_outcome,
)


POLICY_ID = "v24251_runner_compatible_evidence_bridge_v1"
ADMISSION_ROLE = "v24251_page_evidence_ingress_admission"

PRODUCTION_PACKAGE_AUTHORIZED = False
ACTIVE_FORWARD_INTEGRATION_AUTHORIZED = False
ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED = False
EXTERNAL_SIDE_EFFECT_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
DEV64_OR_EXACT220_LAUNCH_AUTHORIZED = False
SHARED_API_LEASE_ACQUIRE_AUTHORIZED = False
LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED = False

RUNNER_MODEL_COMPLETE_JSON_SURFACE_IMPLEMENTED = True
RUNNER_SEARCH_MANY_SURFACE_IMPLEMENTED = True
RUNNER_FETCH_URLS_SURFACE_IMPLEMENTED = True
SEARCH_LEAD_TO_PINNED_FETCH_IMPLEMENTED = True
EXPLICIT_PAGE_EVIDENCE_INGRESS_ADMISSION_IMPLEMENTED = True
SEARCH_LEADS_RETURNED_AS_ACTIVE_EVIDENCE = False
SEARCH_PROVIDER_PROSE_RETURNED = False
ADMITTED_PAGE_TEXT_RETURNED_AS_ACTIVE_EVIDENCE = True
ADMITTED_PAGE_TEXT_IS_UNTRUSTED_DATA = True
ADMITTED_PAGE_TEXT_INSTRUCTION_AUTHORITY = False
FETCH_BODY_HASH_AND_LENGTH_REVALIDATED = True
EPHEMERAL_LEAD_PAGE_URL_EQUALITY_ENFORCED = True
RUNNER_RESULT_CONTENT_HASH_BINDING_IMPLEMENTED = True
URL_OR_PAGE_TEXT_HASHED_IN_ADMISSION = True
RAW_URL_OR_PAGE_TEXT_PERSISTED_BY_BRIDGE = False
URL_CONTENT_TYPE_TO_RESPONSE_CRYPTOGRAPHIC_BINDING_PROVEN = False
PROMPT_INJECTION_SAFETY_INDEPENDENTLY_VERIFIED = False
SOURCE_TRUTH_RELEVANCE_OR_INDEPENDENCE_VERIFIED = False
GLOBAL_LEGACY_INGESTION_ENFORCEMENT_IMPLEMENTED = False
PARALLEL_PROVIDER_EXECUTION_IMPLEMENTED = False
FAILURE_USAGE_ACCOUNTING_EXACT = False

MAX_QUERIES_PER_CALL = 256
ALLOWED_SEARCH_DEPTH = "advanced"
ALLOWED_EXPLICIT_MEDIA_TYPES = frozenset(
    {
        "application/json",
        "application/xhtml+xml",
        "application/xml",
        "text/html",
        "text/plain",
    }
)
ADMISSION_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "search_outcome_sha256",
        "fetch_outcome_sha256",
        "search_action_ordinal",
        "fetch_action_ordinal",
        "search_projection_receipt_sha256",
        "fetch_projection_receipt_sha256",
        "runner_result_binding_sha256",
        "same_exact_durable_ledger_instance",
        "search_lead_exact_type",
        "fetched_page_exact_type",
        "fetch_request_used_projected_lead_fetch_url",
        "ephemeral_canonical_lead_page_url_equal",
        "explicit_supported_content_type",
        "fetch_body_hash_and_length_matches_parent_attempt",
        "search_provider_prose_discarded",
        "search_lead_not_admitted_as_page_evidence",
        "page_projection_was_untrusted_data",
        "page_projection_instruction_authority",
        "page_projection_active_evidence_eligibility_granted",
        "bridge_active_evidence_eligibility_granted",
        "bridge_output_remains_untrusted_data",
        "bridge_output_instruction_authority",
        "page_was_truncated",
        "url_or_page_text_hashed_in_admission",
        "raw_url_or_page_text_persisted_by_bridge",
        "url_content_type_to_response_cryptographic_binding_proven",
        "schema_resealing_without_secret_cryptographically_excluded",
        "admission_replay_without_ephemeral_values_implemented",
        "prompt_injection_safety_independently_verified",
        "source_truth_relevance_or_independence_verified",
        "global_legacy_ingestion_enforcement_implemented",
        "benchmark_or_evaluator_metadata_used_for_routing",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "admission_sha256",
    }
)


class RunnerEvidenceBridgeError(RuntimeError):
    """Sanitized bridge error without prompt, query, URL, or page content."""


class EvidenceIngressRejected(RunnerEvidenceBridgeError):
    """A lead or page failed admission before legacy evidence ingestion."""


@dataclasses.dataclass(frozen=True)
class _LeadContext:
    lead: SearchLeadProjection
    search_result: DurableOutcomeBoundFacadeResult


def _clone(value: Any) -> Any:
    return copy.deepcopy(value)


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _exact(value: Mapping[str, Any], *, keys: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise EvidenceIngressRejected(f"V2.42.51 {label} schema drifted")
    return dict(value)


def _parent_contract(ledger: DurableActionOutcomeLedger) -> dict[str, Any]:
    if type(ledger) is not DurableActionOutcomeLedger:
        raise ValueError("V2.42.51 ledger exact type is invalid")
    ledger._require_registry_binding()
    contract = _clone(dict(ledger._registry._facade._contract))
    validate_candidate_client_facade_contract(contract)
    return contract


def _postprocessor_receipt(facade_receipt: Mapping[str, Any]) -> dict[str, Any]:
    try:
        post = facade_receipt["assembly_receipt"]["postprocessor_receipt"]
    except (KeyError, TypeError):
        raise RunnerEvidenceBridgeError("V2.42.51 parent receipt graph is invalid") from None
    if not isinstance(post, Mapping):
        raise RunnerEvidenceBridgeError("V2.42.51 parent postprocessor receipt is invalid")
    return dict(post)


def _validated_result(
    ledger: DurableActionOutcomeLedger,
    result: DurableOutcomeBoundFacadeResult,
    *,
    operation_kind: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if type(result) is not DurableOutcomeBoundFacadeResult:
        raise RunnerEvidenceBridgeError("V2.42.51 parent result exact type drifted")
    try:
        validate_durable_action_success_outcome(result.receipt)
        ledger.validate_outcome_against_ledger(result.receipt)
        registered = result.receipt["registered_facade_receipt"]
        validate_registered_facade_receipt(registered)
        facade = registered["facade_receipt"]
        validate_candidate_client_facade_receipt(facade)
    except (KeyError, TypeError, ValueError, RuntimeError):
        raise RunnerEvidenceBridgeError("V2.42.51 parent outcome validation failed") from None
    if (
        result.receipt.get("operation_kind") != operation_kind
        or registered.get("operation_kind") != operation_kind
        or facade.get("operation_kind") != operation_kind
    ):
        raise RunnerEvidenceBridgeError("V2.42.51 parent operation drifted")
    return dict(result.receipt), dict(facade)


def _attempts(facade_receipt: Mapping[str, Any]) -> list[dict[str, Any]]:
    post = _postprocessor_receipt(facade_receipt)
    try:
        attempts = post["scheduler_execution_receipt"]["parent_execution_receipt"][
            "measurement"
        ]["attempts"]
    except (KeyError, TypeError):
        raise RunnerEvidenceBridgeError("V2.42.51 parent attempt graph is invalid") from None
    if not isinstance(attempts, list) or not attempts:
        raise RunnerEvidenceBridgeError("V2.42.51 parent attempt graph is empty")
    return [dict(item) for item in attempts if isinstance(item, Mapping)]


def _integer(value: object, *, label: str, minimum: int, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise ValueError(f"V2.42.51 {label} is outside the frozen range")
    return value


def _media_type(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip().casefold()


def _allowed_media_type(content_type: str) -> bool:
    media = _media_type(content_type)
    return bool(media) and (
        media.startswith("text/") or media in ALLOWED_EXPLICIT_MEDIA_TYPES
    )


def _runner_result_binding(
    *,
    title: str,
    url: str,
    content_type: str,
    raw_content: str,
    query: str,
) -> str:
    if not all(
        isinstance(value, str)
        for value in (title, url, content_type, raw_content, query)
    ):
        raise EvidenceIngressRejected("V2.42.51 runner result binding input drifted")
    return object_sha256(
        {
            "policy_id": POLICY_ID,
            "title": title,
            "url": url,
            "content_type": content_type,
            "raw_content": raw_content,
            "query": query,
            "content": "",
            "score": None,
            "fetch_status": "ok",
            "untrusted_data": True,
            "instruction_authority": False,
            "active_evidence_eligible": True,
        }
    )


def _build_admission(
    *,
    search_outcome: Mapping[str, Any],
    fetch_outcome: Mapping[str, Any],
    search_projection: Mapping[str, Any],
    fetch_projection: Mapping[str, Any],
    lead: SearchLeadProjection,
    page: PageTextProjection,
    query: str,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ADMISSION_ROLE,
        "policy_id": POLICY_ID,
        "search_outcome_sha256": search_outcome["outcome_sha256"],
        "fetch_outcome_sha256": fetch_outcome["outcome_sha256"],
        "search_action_ordinal": search_outcome["action_ordinal"],
        "fetch_action_ordinal": fetch_outcome["action_ordinal"],
        "search_projection_receipt_sha256": search_projection[
            "projection_receipt_sha256"
        ],
        "fetch_projection_receipt_sha256": fetch_projection[
            "projection_receipt_sha256"
        ],
        "runner_result_binding_sha256": _runner_result_binding(
            title=lead.title,
            url=page.canonical_url,
            content_type=page.content_type,
            raw_content=page.text,
            query=query,
        ),
        "same_exact_durable_ledger_instance": True,
        "search_lead_exact_type": True,
        "fetched_page_exact_type": True,
        "fetch_request_used_projected_lead_fetch_url": True,
        "ephemeral_canonical_lead_page_url_equal": True,
        "explicit_supported_content_type": True,
        "fetch_body_hash_and_length_matches_parent_attempt": True,
        "search_provider_prose_discarded": True,
        "search_lead_not_admitted_as_page_evidence": True,
        "page_projection_was_untrusted_data": True,
        "page_projection_instruction_authority": False,
        "page_projection_active_evidence_eligibility_granted": False,
        "bridge_active_evidence_eligibility_granted": True,
        "bridge_output_remains_untrusted_data": True,
        "bridge_output_instruction_authority": False,
        "page_was_truncated": False,
        "url_or_page_text_hashed_in_admission": True,
        "raw_url_or_page_text_persisted_by_bridge": False,
        "url_content_type_to_response_cryptographic_binding_proven": False,
        "schema_resealing_without_secret_cryptographically_excluded": False,
        "admission_replay_without_ephemeral_values_implemented": False,
        "prompt_injection_safety_independently_verified": False,
        "source_truth_relevance_or_independence_verified": False,
        "global_legacy_ingestion_enforcement_implemented": False,
        "benchmark_or_evaluator_metadata_used_for_routing": False,
        "active_forward_integration_authorized": False,
        "benchmark_forward_or_evaluator_authorized": False,
    }
    value["admission_sha256"] = object_sha256(value)
    validate_page_evidence_admission(value)
    return value


def validate_page_evidence_admission(value: Mapping[str, Any]) -> None:
    admission = _exact(value, keys=ADMISSION_KEYS, label="admission")
    unsigned = dict(admission)
    seal = unsigned.pop("admission_sha256", None)
    for field in (
        "search_outcome_sha256",
        "fetch_outcome_sha256",
        "search_projection_receipt_sha256",
        "fetch_projection_receipt_sha256",
        "runner_result_binding_sha256",
    ):
        if not _is_sha256(admission.get(field)):
            raise EvidenceIngressRejected("V2.42.51 admission reference is invalid")
    search_ordinal = admission.get("search_action_ordinal")
    fetch_ordinal = admission.get("fetch_action_ordinal")
    if (
        admission.get("artifact_version") != 1
        or admission.get("role") != ADMISSION_ROLE
        or admission.get("policy_id") != POLICY_ID
        or isinstance(search_ordinal, bool)
        or not isinstance(search_ordinal, int)
        or isinstance(fetch_ordinal, bool)
        or not isinstance(fetch_ordinal, int)
        or search_ordinal < 1
        or fetch_ordinal <= search_ordinal
        or admission.get("same_exact_durable_ledger_instance") is not True
        or admission.get("search_lead_exact_type") is not True
        or admission.get("fetched_page_exact_type") is not True
        or admission.get("fetch_request_used_projected_lead_fetch_url") is not True
        or admission.get("ephemeral_canonical_lead_page_url_equal") is not True
        or admission.get("explicit_supported_content_type") is not True
        or admission.get("fetch_body_hash_and_length_matches_parent_attempt") is not True
        or admission.get("search_provider_prose_discarded") is not True
        or admission.get("search_lead_not_admitted_as_page_evidence") is not True
        or admission.get("page_projection_was_untrusted_data") is not True
        or admission.get("page_projection_instruction_authority") is not False
        or admission.get("page_projection_active_evidence_eligibility_granted")
        is not False
        or admission.get("bridge_active_evidence_eligibility_granted") is not True
        or admission.get("bridge_output_remains_untrusted_data") is not True
        or admission.get("bridge_output_instruction_authority") is not False
        or admission.get("page_was_truncated") is not False
        or admission.get("url_or_page_text_hashed_in_admission") is not True
        or admission.get("raw_url_or_page_text_persisted_by_bridge") is not False
        or admission.get(
            "url_content_type_to_response_cryptographic_binding_proven"
        )
        is not False
        or admission.get(
            "schema_resealing_without_secret_cryptographically_excluded"
        )
        is not False
        or admission.get("admission_replay_without_ephemeral_values_implemented")
        is not False
        or admission.get("prompt_injection_safety_independently_verified") is not False
        or admission.get("source_truth_relevance_or_independence_verified") is not False
        or admission.get("global_legacy_ingestion_enforcement_implemented") is not False
        or admission.get("benchmark_or_evaluator_metadata_used_for_routing")
        is not False
        or admission.get("active_forward_integration_authorized") is not False
        or admission.get("benchmark_forward_or_evaluator_authorized") is not False
        or not _is_sha256(seal)
        or seal != object_sha256(unsigned)
    ):
        raise EvidenceIngressRejected("V2.42.51 admission drifted")


def validate_runner_search_batch(value: Mapping[str, Any]) -> dict[str, Any]:
    """Reject every legacy ``raw_content`` item without an explicit admission."""

    if not isinstance(value, Mapping) or set(value) != {
        "query",
        "answer",
        "results",
        "error",
        "provider",
    }:
        raise EvidenceIngressRejected("V2.42.51 runner search batch schema drifted")
    batch = dict(value)
    results = batch.get("results")
    if (
        not isinstance(batch.get("query"), str)
        or not batch["query"]
        or batch.get("answer") != ""
        or batch.get("provider") != "v24251-durable-pinned-page-admission"
        or not isinstance(results, list)
        or (results and batch.get("error") is not None)
        or (not results and not isinstance(batch.get("error"), str))
    ):
        raise EvidenceIngressRejected("V2.42.51 runner search batch policy drifted")
    expected_result_keys = {
        "title",
        "url",
        "content_type",
        "content",
        "raw_content",
        "score",
        "source_type",
        "fetch_status",
        "query",
        "untrusted_data",
        "instruction_authority",
        "active_evidence_eligible",
        "evidence_ingress_admission",
    }
    for result in results:
        if not isinstance(result, Mapping) or set(result) != expected_result_keys:
            raise EvidenceIngressRejected("V2.42.51 runner result schema drifted")
        admission = result.get("evidence_ingress_admission")
        validate_page_evidence_admission(admission)
        if (
            not isinstance(result.get("title"), str)
            or not isinstance(result.get("url"), str)
            or not result["url"]
            or not isinstance(result.get("content_type"), str)
            or not result["content_type"]
            or result.get("content") != ""
            or not isinstance(result.get("raw_content"), str)
            or not result["raw_content"]
            or result.get("score") is not None
            or result.get("source_type")
            != f"v24251_explicit_page_ingress:{admission['admission_sha256']}"
            or result.get("fetch_status") != "ok"
            or result.get("query") != batch["query"]
            or result.get("untrusted_data") is not True
            or result.get("instruction_authority") is not False
            or result.get("active_evidence_eligible") is not True
            or admission.get("runner_result_binding_sha256")
            != _runner_result_binding(
                title=result["title"],
                url=result["url"],
                content_type=result["content_type"],
                raw_content=result["raw_content"],
                query=result["query"],
            )
        ):
            raise EvidenceIngressRejected("V2.42.51 runner result policy drifted")
    return _clone(batch)


class RunnerCompatibleModelClient:
    """Expose V2.42.50 model JSON through the legacy runner call shape."""

    def __init__(self, *, ledger: DurableActionOutcomeLedger) -> None:
        self._ledger = ledger
        self._contract = _parent_contract(ledger)
        self.requests = 0
        self.calls = 0
        self.failures = 0
        self.attempts = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self._lock = threading.Lock()

    def _require_binding(self) -> None:
        if _parent_contract(self._ledger) != self._contract:
            raise RunnerEvidenceBridgeError("V2.42.51 model parent contract drifted")

    def complete_json(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        repair_tokens: int = 4096,
        max_parse_attempts: int = 3,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        del repair_tokens, max_parse_attempts
        self._require_binding()
        output_limit = _integer(
            max_output_tokens,
            label="model output token limit",
            minimum=1,
            maximum=int(self._contract["model_maximum_output_tokens"]),
        )
        if not isinstance(system, str) or not isinstance(user, str) or not system or not user:
            raise ValueError("V2.42.51 model prompts are invalid")
        input_chars = len(system) + len(user)
        input_bytes = len(system.encode("utf-8")) + len(user.encode("utf-8"))
        with self._lock:
            self.requests += 1
            request_index = self.requests
        try:
            result = type(self._ledger).run_model_json(
                self._ledger,
                system=system,
                user=user,
                max_output_tokens=output_limit,
            )
            _outcome, facade = _validated_result(
                self._ledger, result, operation_kind="model_json"
            )
            if type(result.value) is not dict:
                raise RunnerEvidenceBridgeError("V2.42.51 model value exact type drifted")
            attempts = _attempts(facade)
            settlement = dict(facade["settlement_cost"])
            input_tokens = int(settlement["input_tokens"])
            output_tokens = int(settlement["output_tokens"])
            request_body_bytes = int(attempts[-1]["request_body_bytes"])
            attempt_count = int(facade["attempt_count"])
        except BaseException as error:
            reserved = self._contract["model_meter_contract"]["reserved_cost"]
            reserved_attempts = int(self._contract["model_max_attempts"])
            with self._lock:
                self.failures += 1
                self.attempts += reserved_attempts
                self.input_tokens += int(reserved["input_tokens"])
                self.output_tokens += int(reserved["output_tokens"])
                self.total_tokens += int(reserved["input_tokens"]) + int(
                    reserved["output_tokens"]
                )
            trace = {
                "purpose": "request_failure",
                "response_id": None,
                "usage": {
                    "input_tokens": int(reserved["input_tokens"]),
                    "output_tokens": int(reserved["output_tokens"]),
                    "total_tokens": int(reserved["input_tokens"])
                    + int(reserved["output_tokens"]),
                },
                "attempts": reserved_attempts,
                "request_index": request_index,
                "success": False,
                "error_type": type(error).__name__,
                "last_status": None,
                "input_chars": input_chars,
                "input_utf8_bytes": input_bytes,
                "request_body_bytes": 0,
                "max_output_tokens": output_limit,
                "accounting_basis": "conservative_frozen_reservation",
            }
            setattr(error, "model_traces", [trace])
            raise
        total_tokens = input_tokens + output_tokens
        with self._lock:
            self.calls += 1
            self.attempts += attempt_count
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            self.total_tokens += total_tokens
        trace = {
            "purpose": "initial",
            "response_id": None,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            },
            "attempts": attempt_count,
            "request_index": request_index,
            "success": True,
            "input_chars": input_chars,
            "input_utf8_bytes": input_bytes,
            "request_body_bytes": request_body_bytes,
            "max_output_tokens": output_limit,
            "output_truncated": output_tokens >= output_limit,
            "content_free_outcome_sha256": result.receipt["outcome_sha256"],
            "accounting_basis": "durable_parent_settlement",
        }
        return _clone(result.value), [trace]


class RunnerCompatibleSearchClient:
    """Fetch projected leads before emitting any legacy page content."""

    def __init__(self, *, ledger: DurableActionOutcomeLedger) -> None:
        self._ledger = ledger
        self._contract = _parent_contract(ledger)
        self.calls = 0
        self.failures = 0
        self.tool_calls = 0
        self.fetch_calls = 0
        self.fetch_failures = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.ingress_rejections = 0
        self._lead_cache: dict[str, _LeadContext] = {}
        self._lock = threading.Lock()

    def _require_binding(self) -> None:
        if _parent_contract(self._ledger) != self._contract:
            raise RunnerEvidenceBridgeError("V2.42.51 search parent contract drifted")

    def _account_success(self, facade: Mapping[str, Any]) -> None:
        settlement = dict(facade["settlement_cost"])
        attempts = _attempts(facade)
        with self._lock:
            self.calls += int(settlement["search_calls"])
            self.fetch_calls += int(settlement["fetch_calls"])
            self.tool_calls += sum(
                int(item.get("provider_tool_calls") or 0) for item in attempts
            )
            self.input_tokens += int(settlement["input_tokens"])
            self.output_tokens += int(settlement["output_tokens"])
            self.total_tokens += int(settlement["input_tokens"]) + int(
                settlement["output_tokens"]
            )

    def _account_failure(self, operation_kind: str) -> None:
        meter = self._contract[
            "search_meter_contract"
            if operation_kind == "search_leads"
            else "fetch_meter_contract"
        ]
        reserved = meter["reserved_cost"]
        with self._lock:
            self.failures += operation_kind == "search_leads"
            self.fetch_failures += operation_kind == "fetched_page"
            self.calls += int(reserved["search_calls"])
            self.fetch_calls += int(reserved["fetch_calls"])
            self.input_tokens += int(reserved["input_tokens"])
            self.output_tokens += int(reserved["output_tokens"])
            self.total_tokens += int(reserved["input_tokens"]) + int(
                reserved["output_tokens"]
            )

    def _search_contexts(self, query: str, max_results: int) -> list[_LeadContext]:
        accounted = False
        try:
            result = type(self._ledger).run_search_leads(
                self._ledger,
                query=query,
                max_results=max_results,
            )
            search_outcome, facade = _validated_result(
                self._ledger, result, operation_kind="search_leads"
            )
            del search_outcome
            self._account_success(facade)
            accounted = True
            search_projection = _postprocessor_receipt(facade)
            validate_search_page_projection_receipt(search_projection)
            if (
                search_projection["projection_kind"] != "untrusted_search_leads"
                or search_projection["search_leads_are_page_evidence"] is not False
                or search_projection["active_evidence_eligibility_granted"] is not False
                or type(result.value) is not tuple
                or len(result.value) != facade["returned_value_item_count"]
            ):
                raise RunnerEvidenceBridgeError(
                    "V2.42.51 search projection policy drifted"
                )
        except BaseException:
            if not accounted:
                self._account_failure("search_leads")
            raise
        contexts: list[_LeadContext] = []
        for lead in result.value:
            if type(lead) is not SearchLeadProjection:
                raise RunnerEvidenceBridgeError("V2.42.51 search lead exact type drifted")
            context = _LeadContext(lead=lead, search_result=result)
            contexts.append(context)
            with self._lock:
                self._lead_cache.setdefault(lead.fetch_url, context)
                self._lead_cache.setdefault(lead.canonical_url, context)
        return contexts

    def _admitted_result(
        self,
        context: _LeadContext,
        *,
        query: str,
    ) -> dict[str, Any]:
        self._require_binding()
        lead = context.lead
        if (
            type(lead) is not SearchLeadProjection
            or type(context.search_result) is not DurableOutcomeBoundFacadeResult
            or type(context.search_result.value) is not tuple
            or not any(item is lead for item in context.search_result.value)
        ):
            with self._lock:
                self.ingress_rejections += 1
            raise EvidenceIngressRejected("V2.42.51 cached lead exact type drifted")
        search_outcome, search_facade = _validated_result(
            self._ledger, context.search_result, operation_kind="search_leads"
        )
        search_projection = _postprocessor_receipt(search_facade)
        validate_search_page_projection_receipt(search_projection)
        accounted = False
        try:
            result = type(self._ledger).run_fetched_page(
                self._ledger,
                url=lead.fetch_url,
            )
            fetch_outcome, fetch_facade = _validated_result(
                self._ledger, result, operation_kind="fetched_page"
            )
            self._account_success(fetch_facade)
            accounted = True
            fetch_projection = _postprocessor_receipt(fetch_facade)
            validate_search_page_projection_receipt(fetch_projection)
        except BaseException:
            if not accounted:
                self._account_failure("fetched_page")
            raise
        page = result.value
        if (
            type(page) is not PageTextProjection
            or page.canonical_url != lead.canonical_url
            or not _allowed_media_type(page.content_type)
            or not page.text
            or page.truncated
            or page.untrusted_data is not True
            or page.instruction_authority is not False
            or page.active_evidence_eligible is not False
            or fetch_projection["projection_kind"] != "untrusted_page_text"
            or fetch_projection["fetch_body_hash_and_length_matches_parent_attempt"]
            is not True
            or fetch_projection[
                "fetch_body_bytes_to_parent_response_binding_independently_verified"
            ]
            is not True
            or fetch_projection["page_text_is_untrusted_data"] is not True
            or fetch_projection["page_text_instruction_authority"] is not False
            or fetch_projection["active_evidence_eligibility_granted"] is not False
            or search_projection["search_leads_are_page_evidence"] is not False
            or search_projection["active_evidence_eligibility_granted"] is not False
        ):
            with self._lock:
                self.ingress_rejections += 1
            raise EvidenceIngressRejected("V2.42.51 fetched page admission rejected")
        admission = _build_admission(
            search_outcome=search_outcome,
            fetch_outcome=fetch_outcome,
            search_projection=search_projection,
            fetch_projection=fetch_projection,
            lead=lead,
            page=page,
            query=query,
        )
        source_type = f"v24251_explicit_page_ingress:{admission['admission_sha256']}"
        return {
            "title": lead.title,
            "url": page.canonical_url,
            "content_type": page.content_type,
            "content": "",
            "raw_content": page.text,
            "score": None,
            "source_type": source_type,
            "fetch_status": "ok",
            "query": query,
            "untrusted_data": True,
            "instruction_authority": False,
            "active_evidence_eligible": True,
            "evidence_ingress_admission": admission,
        }

    def _batch(self, query: str, contexts: Iterable[_LeadContext]) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        rejected = 0
        for context in contexts:
            try:
                results.append(self._admitted_result(context, query=query))
            except EvidenceIngressRejected:
                rejected += 1
        batch = {
            "query": query,
            "answer": "",
            "results": results,
            "error": (
                None
                if results
                else "all fetched pages rejected by explicit evidence-ingress policy"
                if rejected
                else "no admitted fetched page"
            ),
            "provider": "v24251-durable-pinned-page-admission",
        }
        return validate_runner_search_batch(batch)

    def search_many(
        self,
        queries: Iterable[str],
        *,
        max_results: int,
        search_depth: str = ALLOWED_SEARCH_DEPTH,
        include_raw_content: bool = True,
    ) -> list[dict[str, Any]]:
        self._require_binding()
        limit = _integer(
            max_results,
            label="search result limit",
            minimum=1,
            maximum=int(self._contract["search_maximum_results"]),
        )
        if search_depth != ALLOWED_SEARCH_DEPTH:
            raise ValueError("V2.42.51 search depth drifted")
        if include_raw_content is not True:
            raise ValueError("V2.42.51 raw page admission must be explicit")
        if isinstance(queries, (str, bytes)):
            raise ValueError("V2.42.51 search query collection is invalid")
        unique: list[str] = []
        seen: set[str] = set()
        for supplied in queries:
            if not isinstance(supplied, str):
                raise ValueError("V2.42.51 search query is invalid")
            query = " ".join(supplied.split()).strip()
            key = query.casefold()
            if query and key not in seen:
                unique.append(query)
                seen.add(key)
            if len(unique) > MAX_QUERIES_PER_CALL:
                raise ValueError("V2.42.51 search query count exceeds the frozen cap")
        return [
            self._batch(query, self._search_contexts(query, limit)) for query in unique
        ]

    def search(
        self,
        query: str,
        *,
        max_results: int,
        search_depth: str = ALLOWED_SEARCH_DEPTH,
        include_raw_content: bool = True,
    ) -> dict[str, Any]:
        batches = self.search_many(
            [query],
            max_results=max_results,
            search_depth=search_depth,
            include_raw_content=include_raw_content,
        )
        if not batches:
            raise ValueError("V2.42.51 search query is empty")
        return batches[0]

    def fetch_urls(self, requests_: Iterable[dict[str, str]]) -> list[dict[str, Any]]:
        self._require_binding()
        if isinstance(requests_, (str, bytes, Mapping)):
            raise ValueError("V2.42.51 fetch request collection is invalid")
        batches: list[dict[str, Any]] = []
        count = 0
        for request in requests_:
            count += 1
            if count > MAX_QUERIES_PER_CALL or not isinstance(request, Mapping):
                raise ValueError("V2.42.51 fetch request collection is invalid")
            supplied = request.get("url")
            if not isinstance(supplied, str) or not supplied:
                raise ValueError("V2.42.51 fetch request URL is invalid")
            with self._lock:
                context = self._lead_cache.get(supplied)
            if context is None:
                raise EvidenceIngressRejected(
                    "V2.42.51 direct fetch lacks a prior projected search lead"
                )
            query_value = request.get("query")
            query = (
                " ".join(query_value.split()).strip()
                if isinstance(query_value, str) and query_value.strip()
                else "admitted direct page fetch"
            )
            batches.append(self._batch(query, [context]))
        return batches
