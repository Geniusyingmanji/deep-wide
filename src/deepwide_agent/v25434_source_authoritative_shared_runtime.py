"""One-parent production integration for source-authoritative candidates.

The V2.54.32 primitive can extract source/identity/field/value coordinates,
but its pages must come from the production forward rather than a separate
fetch.  This build-only runtime executes V2.54.01 exactly once.  A task-local
subclass mirrors the pages already embedded in the paid third synthesis
prompt without changing that prompt or provider request.  It retains a page
only when one visible row identity binds to both its URL path and title/leading
surface, and a distinctive token from one visible authority phrase binds to
the same URL.

After the parent table is complete, V2.54.32 builds candidates from those
same-forward pages.  A deterministic policy selects every unique candidate
ID; no model can author an identity, field, or value and no fourth model call
is introduced.  Conflicts, multiple coordinates, Unknown values, missing
rows, list collapse, capture failure, or no candidate preserve the shared
base byte-for-byte.  The parent changed-safe arm remains private diagnostic
state and is not composed with this treatment.

Runtime inputs remain visible ``opaque_id``/``question`` plus injected capped
clients.  This module has no filesystem, environment, process, network,
credential, evaluator, benchmark-label, mapping, gold, score, reward, or
historical-result capability.  Entropy/information gain assigns no signed
credit.  This build grants no external or benchmark launch.
"""

from __future__ import annotations

import copy
import hashlib
import json
import types
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import v24257_score_first_runtime as score
from . import v25004_identity_bound_detail_fields as authority
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25370_shared_synthesis_changed_safe_runtime as shared_parent
from . import v25389_hybrid_record_fallback_runtime as hybrid_parent
from . import v25395_visible_membership_synthesis_runtime as membership_parent
from . import v25401_grounded_record_membership_runtime as parent
from . import v25432_source_authoritative_field_candidate as candidates
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter


POLICY_ID = "v25434_source_authoritative_shared_runtime_v1"
ROLE = "v25434_source_authoritative_shared_runtime_result"
RECEIPT_ROLE = "v25434_content_free_source_authoritative_shared_receipt"
STAGE_RECEIPT_ROLE = "v25434_content_free_source_authoritative_shared_stage_receipt"
ARMS = ("shared_base_table", "source_authoritative_candidate")
BASE_ARM, CANDIDATE_ARM = ARMS
PHASES = parent.PHASES
ProductionOnlyStageError = parent.ProductionOnlyStageError
CONTENT_FREE_FLAG = (
    "contains_question_query_url_title_page_quote_identity_field_value_"
    "prediction_answer_hash_opaque_id_or_credential"
)

_INTEGER_FIELDS = (
    "input_synthesis_page_count",
    "visible_member_count",
    "visible_authority_token_count",
    "url_identity_bound_page_count",
    "identity_surface_bound_page_count",
    "authority_url_bound_page_count",
    "joint_identity_authority_bound_page_count",
    "ambiguous_identity_page_count",
    "accepted_authority_page_count",
    "available_candidate_count",
    "selected_candidate_count",
    "applied_coordinate_count",
    "positive_signed_credit_count",
    "additional_model_requests",
    "additional_logical_queries",
    "additional_search_calls",
    "additional_fetch_calls",
    "additional_provider_tokens",
)
_DYNAMIC_FLAGS = (
    "synthesis_capture_attempted",
    "synthesis_capture_valid",
    "source_authoritative_application_valid",
    "candidate_prediction_changed",
    "candidate_identity_handoff",
)
_TRUE_FLAGS = (
    "one_v25401_parent_forward_only",
    "third_synthesis_prompt_mirrored_without_mutation",
    "accepted_page_requires_visible_identity_url_and_surface_binding",
    "accepted_page_requires_visible_authority_url_binding",
    "candidate_registry_runs_only_after_shared_base_completion",
    "deterministic_policy_selects_only_registry_candidate_ids",
    "candidate_value_is_source_extracted_before_selection",
    "parent_changed_safe_arm_not_composed_with_candidate",
    "zero_candidate_or_capture_failure_preserves_base_byte_exact",
    "query4_fetch14_model3_token_context_and_wall_caps_unchanged",
)
_FALSE_FLAGS = (
    "additional_selector_model_call",
    CONTENT_FREE_FLAG,
    candidates.PRIVILEGED_READ_FLAG,
    "entropy_or_information_gain_assigns_signed_credit",
    "file_environment_process_network_model_search_fetch_or_evaluator_accessed_by_wrapper",
    "benchmark_launch_or_evaluator_authorized",
)


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__ or "Exception"
    return name[:128]


def _url_bindings(
    url: str,
    *,
    identity: str,
    authority_tokens: Sequence[str],
) -> tuple[bool, bool]:
    """Bind an identity to path tokens, allowing one exact joined token.

    Public record URLs commonly serialize ``RFC 9160`` as ``rfc9160``.  The
    joined form is accepted only as one complete path token; substrings and
    host/TLD matches remain forbidden.
    """

    canonical = authority.canonicalize_url(str(url or ""))
    if not canonical:
        return False, False
    try:
        parsed = authority.urlsplit(canonical)
    except ValueError:
        return False, False
    path_tokens = frozenset(authority._tokens(authority.unquote(parsed.path or "")))
    url_tokens = frozenset(
        authority._tokens(
            f"{authority.unquote(parsed.hostname or '')} "
            f"{authority.unquote(parsed.path or '')}"
        )
    )
    identity_tokens = tuple(authority._tokens(identity))
    joined = "".join(identity_tokens)
    identity_bound = bool(
        identity_tokens
        and (
            set(identity_tokens).issubset(path_tokens)
            or (len(identity_tokens) >= 2 and joined in path_tokens)
        )
    )
    authority_bound = any(token in url_tokens for token in authority_tokens)
    return identity_bound, authority_bound


def _authority_bound_pages(
    question: str,
    identities: Sequence[str],
    pages: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """Select same-forward pages by visible identity and authority only."""

    if isinstance(identities, (str, bytes)) or not isinstance(
        identities, Sequence
    ):
        raise ValueError("V2.54.34 visible identity vector drifted")
    if isinstance(pages, (str, bytes)) or not isinstance(pages, Sequence):
        raise ValueError("V2.54.34 synthesis page vector drifted")
    checked_identities = tuple(str(value) for value in identities)
    authority_tokens = authority._authority_tokens(str(question))
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    url_identity_pages = surface_pages = authority_pages = joint_pages = ambiguous = 0
    for raw in pages:
        if not isinstance(raw, Mapping):
            continue
        page = {
            "url": str(raw.get("url") or ""),
            "title": str(raw.get("title") or ""),
            "content": str(raw.get("content") or raw.get("raw_content") or ""),
        }
        if not page["url"] or not page["content"] or page["url"] in seen:
            continue
        identity_url_matches: list[str] = []
        identity_surface_matches: list[str] = []
        joint_matches: list[str] = []
        authority_bound = False
        for identity in checked_identities:
            path_bound, current_authority_bound = _url_bindings(
                page["url"],
                identity=identity,
                authority_tokens=authority_tokens,
            )
            surface_bound = authority._page_identity_bound(page, identity)
            authority_bound = authority_bound or current_authority_bound
            if path_bound:
                identity_url_matches.append(identity)
            if surface_bound:
                identity_surface_matches.append(identity)
            if path_bound and surface_bound:
                joint_matches.append(identity)
        url_identity_pages += int(bool(identity_url_matches))
        surface_pages += int(bool(identity_surface_matches))
        authority_pages += int(authority_bound)
        joint = bool(authority_bound and len(joint_matches) == 1)
        joint_pages += int(joint)
        ambiguous += int(len(joint_matches) > 1)
        if joint:
            seen.add(page["url"])
            output.append(page)
    return output, {
        "input_synthesis_page_count": len(pages),
        "visible_member_count": len(checked_identities),
        "visible_authority_token_count": len(authority_tokens),
        "url_identity_bound_page_count": url_identity_pages,
        "identity_surface_bound_page_count": surface_pages,
        "authority_url_bound_page_count": authority_pages,
        "joint_identity_authority_bound_page_count": joint_pages,
        "ambiguous_identity_page_count": ambiguous,
        "accepted_authority_page_count": len(output),
    }


class _SourceAuthoritativeCaptureHybrid(
    parent._GroundedRecordMembershipHybridInner
):
    """Mirror the frozen third-call page vector without changing its bytes."""

    def __init__(
        self,
        bounded: DeadlineAwareGlobalModelSlotLimiter,
        *,
        question: str,
    ) -> None:
        super().__init__(bounded, question=question)
        self.source_columns: tuple[str, ...] = ()
        self.source_pages: list[dict[str, str]] = []
        self.source_page_counts = {
            "input_synthesis_page_count": 0,
            "visible_member_count": len(self.visible_members),
            "visible_authority_token_count": 0,
            "url_identity_bound_page_count": 0,
            "identity_surface_bound_page_count": 0,
            "authority_url_bound_page_count": 0,
            "joint_identity_authority_bound_page_count": 0,
            "ambiguous_identity_page_count": 0,
            "accepted_authority_page_count": 0,
        }
        self.source_capture_attempted = False
        self.source_capture_valid = False
        self.source_capture_failure_type: str | None = None

    def _synthesis(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
    ) -> Any:
        self.source_capture_attempted = True
        try:
            self.source_columns = tuple(
                hybrid_parent.joint_parent.sparse._prompt_columns(
                    str(user), ("Result", "Value")
                )
            )
            prompt_pages = hybrid_parent.joint_parent.sparse._prompt_pages(
                str(user)
            )
            self.source_pages, self.source_page_counts = _authority_bound_pages(
                self._question,
                self.visible_members,
                prompt_pages,
            )
            self.source_capture_valid = bool(len(self.source_columns) >= 2)
            if not self.source_capture_valid:
                self.source_capture_failure_type = "InsufficientVisibleColumns"
        except BaseException as exc:
            self.source_columns = ()
            self.source_pages = []
            self.source_capture_valid = False
            self.source_capture_failure_type = _safe_failure(exc)
        return super()._synthesis(
            system,
            user,
            max_output_tokens=max_output_tokens,
        )


def _parent_runner(
    created: list[_SourceAuthoritativeCaptureHybrid],
) -> Callable[..., tuple[dict[str, Any], dict[str, Any]]]:
    def factory(
        bounded: DeadlineAwareGlobalModelSlotLimiter,
        *,
        question: str,
    ) -> _SourceAuthoritativeCaptureHybrid:
        hybrid = _SourceAuthoritativeCaptureHybrid(bounded, question=question)
        created.append(hybrid)
        return hybrid

    namespace = dict(parent.run_task.__globals__)
    namespace["_GroundedRecordMembershipHybridInner"] = factory
    cloned = types.FunctionType(
        parent.run_task.__code__,
        namespace,
        name="v25434_task_local_v25401_parent",
        argdefs=parent.run_task.__defaults__,
        closure=parent.run_task.__closure__,
    )
    cloned.__kwdefaults__ = dict(parent.run_task.__kwdefaults__ or {})
    cloned.__annotations__ = dict(parent.run_task.__annotations__)
    return cloned


def _shared_base(parent_result: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    checked = parent.validate_result(parent_result)
    membership = membership_parent.validate_result(checked["private_parent_result"])
    hybrid = hybrid_parent.validate_result(membership["private_parent_result"])
    shared = shared_parent.validate_result(hybrid["private_parent_result"])
    base = str(shared["predictions"][shared_parent.CONTROL_ARM])
    if not base:
        raise ValueError("V2.54.34 shared base is absent")
    return base, shared


def _application(
    base: str,
    hybrid: _SourceAuthoritativeCaptureHybrid,
) -> tuple[dict[str, Any] | None, str, str | None]:
    if not hybrid.source_capture_valid:
        failure = hybrid.source_capture_failure_type
        if failure is None:
            failure = "SynthesisCaptureNotAttempted"
        return None, base, failure
    try:
        registry = candidates.build_candidate_registry(
            base,
            columns=hybrid.source_columns,
            pages=hybrid.source_pages,
        )
        selected = [item["candidate_id"] for item in registry["candidates"]]
        selector_output = json.dumps(
            {"candidate_ids": selected}, separators=(",", ":")
        )
        application = candidates.apply_candidate_selection(
            base,
            columns=hybrid.source_columns,
            pages=hybrid.source_pages,
            selector_output=selector_output,
        )
        return application, str(application["candidate_prediction"]), None
    except BaseException as exc:
        return None, base, _safe_failure(exc)


def _receipt(
    *,
    parent_result: Mapping[str, Any],
    hybrid: _SourceAuthoritativeCaptureHybrid,
    application: Mapping[str, Any] | None,
    application_failure_type: str | None,
    base: str,
    candidate: str,
) -> dict[str, Any]:
    checked = parent.validate_result(parent_result)
    counts = dict(hybrid.source_page_counts)
    if application is None:
        available = selected = applied = 0
        application_valid = False
        application_hash = None
    else:
        observed = candidates.validate_application(application)
        app_receipt = candidates.validate_application_receipt(
            observed["content_free_receipt"]
        )
        available = int(app_receipt["available_candidate_count"])
        selected = int(app_receipt["selected_candidate_count"])
        applied = int(app_receipt["applied_coordinate_count"])
        application_valid = True
        application_hash = str(observed["artifact_payload_sha256"])
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(counts.get(name, 0)) for name in _INTEGER_FIELDS[:9]},
        "available_candidate_count": available,
        "selected_candidate_count": selected,
        "applied_coordinate_count": applied,
        "positive_signed_credit_count": 0,
        "additional_model_requests": 0,
        "additional_logical_queries": 0,
        "additional_search_calls": 0,
        "additional_fetch_calls": 0,
        "additional_provider_tokens": 0,
        "synthesis_capture_attempted": hybrid.source_capture_attempted,
        "synthesis_capture_valid": hybrid.source_capture_valid,
        "source_authoritative_application_valid": application_valid,
        "candidate_prediction_changed": base != candidate,
        "candidate_identity_handoff": base == candidate,
        "capture_failure_type": (
            hybrid.source_capture_failure_type
            if hybrid.source_capture_valid or hybrid.source_capture_failure_type
            else "SynthesisCaptureNotAttempted"
        ),
        "application_failure_type": application_failure_type,
        "parent_result_payload_sha256": checked["result_payload_sha256"],
        "application_payload_sha256": application_hash,
        **{name: True for name in _TRUE_FLAGS},
        **{name: False for name in _FALSE_FLAGS},
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def _receipt_matches_application(
    receipt: Mapping[str, Any],
    application: Mapping[str, Any] | None,
) -> bool:
    if application is None:
        return bool(
            receipt.get("source_authoritative_application_valid") is False
            and receipt.get("application_payload_sha256") is None
            and receipt.get("available_candidate_count") == 0
            and receipt.get("selected_candidate_count") == 0
            and receipt.get("applied_coordinate_count") == 0
        )
    try:
        checked = candidates.validate_application(application)
        observed = candidates.validate_application_receipt(
            checked["content_free_receipt"]
        )
    except (TypeError, ValueError):
        return False
    return bool(
        receipt.get("source_authoritative_application_valid") is True
        and receipt.get("application_payload_sha256")
        == checked["artifact_payload_sha256"]
        and receipt.get("available_candidate_count")
        == observed["available_candidate_count"]
        and receipt.get("selected_candidate_count")
        == observed["selected_candidate_count"]
        and receipt.get("applied_coordinate_count")
        == observed["applied_coordinate_count"]
        and receipt.get("candidate_prediction_changed")
        is observed["candidate_prediction_changed"]
    )


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *_INTEGER_FIELDS,
        *_DYNAMIC_FLAGS,
        "capture_failure_type",
        "application_failure_type",
        "parent_result_payload_sha256",
        "application_payload_sha256",
        *_TRUE_FLAGS,
        *_FALSE_FLAGS,
        "receipt_payload_sha256",
    }
    failure_fields = ("capture_failure_type", "application_failure_type")
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in _INTEGER_FIELDS
        )
        or any(not isinstance(copied.get(name), bool) for name in _DYNAMIC_FLAGS)
        or copied["accepted_authority_page_count"]
        > copied["joint_identity_authority_bound_page_count"]
        or copied["joint_identity_authority_bound_page_count"]
        > copied["input_synthesis_page_count"]
        or copied["selected_candidate_count"]
        > copied["available_candidate_count"]
        or copied["applied_coordinate_count"]
        != copied["selected_candidate_count"]
        or copied["positive_signed_credit_count"] != 0
        or any(copied[name] != 0 for name in _INTEGER_FIELDS[-5:])
        or copied["candidate_prediction_changed"]
        is not (copied["applied_coordinate_count"] > 0)
        or copied["candidate_identity_handoff"]
        is not (not copied["candidate_prediction_changed"])
        or copied["synthesis_capture_valid"]
        and not copied["synthesis_capture_attempted"]
        or copied["source_authoritative_application_valid"]
        and not copied["synthesis_capture_valid"]
        or copied["source_authoritative_application_valid"]
        is not (copied.get("application_payload_sha256") is not None)
        or copied["source_authoritative_application_valid"]
        and copied.get("application_failure_type") is not None
        or not copied["synthesis_capture_valid"]
        and copied.get("capture_failure_type") is None
        or any(
            item is not None
            and (not isinstance(item, str) or not item or len(item) > 128)
            for item in (copied.get(name) for name in failure_fields)
        )
        or not isinstance(copied.get("parent_result_payload_sha256"), str)
        or len(copied["parent_result_payload_sha256"]) != 64
        or copied.get("application_payload_sha256") is not None
        and (
            not isinstance(copied["application_payload_sha256"], str)
            or len(copied["application_payload_sha256"]) != 64
        )
        or any(copied.get(name) is not True for name in _TRUE_FLAGS)
        or any(copied.get(name) is not False for name in _FALSE_FLAGS)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.34 source-authoritative receipt drifted")
    return copied


def _wrap_result(
    parent_result: Mapping[str, Any],
    hybrid: _SourceAuthoritativeCaptureHybrid,
) -> dict[str, Any]:
    checked = parent.validate_result(parent_result)
    base, _shared = _shared_base(checked)
    application, candidate, failure = _application(base, hybrid)
    receipt = _receipt(
        parent_result=checked,
        hybrid=hybrid,
        application=application,
        application_failure_type=failure,
        base=base,
        candidate=candidate,
    )
    predictions = {BASE_ARM: base, CANDIDATE_ARM: candidate}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": checked["opaque_id"],
        "status": "terminal",
        "prediction": candidate,
        "prediction_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        "prediction_kind": checked["prediction_kind"],
        "predictions": predictions,
        "prediction_sha256_by_arm": {
            arm: hashlib.sha256(prediction.encode()).hexdigest()
            for arm, prediction in predictions.items()
        },
        "prediction_changed": base != candidate,
        "source_authoritative_receipt": copy.deepcopy(receipt),
        "private_source_authoritative_application": copy.deepcopy(application),
        "private_source_columns": list(hybrid.source_columns),
        "private_same_forward_authority_pages": copy.deepcopy(
            hybrid.source_pages
        ),
        "private_parent_result": copy.deepcopy(checked),
        "private_parent_result_payload_sha256": checked["result_payload_sha256"],
        "cost": copy.deepcopy(checked["cost"]),
        "scored_prediction_is_source_authoritative_candidate": True,
        "shared_base_is_parent_control_not_parent_changed_safe_candidate": True,
        candidates.PRIVILEGED_READ_FLAG: False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return value


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    raw = copied.get("private_parent_result")
    application = copied.get("private_source_authoritative_application")
    source_columns = copied.get("private_source_columns")
    source_pages = copied.get("private_same_forward_authority_pages")
    receipt = copied.get("source_authoritative_receipt")
    predictions = copied.get("predictions")
    hashes = copied.get("prediction_sha256_by_arm")
    if not isinstance(raw, Mapping):
        raise ValueError("V2.54.34 private parent result is absent")
    parent_result = parent.validate_result(raw)
    base, _shared = _shared_base(parent_result)
    application_checked: dict[str, Any] | None = None
    if application is not None:
        if not isinstance(application, Mapping):
            raise ValueError("V2.54.34 private application drifted")
        application_checked = candidates.validate_application(application)
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "opaque_id",
        "status",
        "prediction",
        "prediction_sha256",
        "prediction_kind",
        "predictions",
        "prediction_sha256_by_arm",
        "prediction_changed",
        "source_authoritative_receipt",
        "private_source_authoritative_application",
        "private_source_columns",
        "private_same_forward_authority_pages",
        "private_parent_result",
        "private_parent_result_payload_sha256",
        "cost",
        "scored_prediction_is_source_authoritative_candidate",
        "shared_base_is_parent_control_not_parent_changed_safe_candidate",
        candidates.PRIVILEGED_READ_FLAG,
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
        "result_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("status") != "terminal"
        or copied.get("opaque_id") != parent_result["opaque_id"]
        or copied.get("prediction_kind") != parent_result["prediction_kind"]
        or not isinstance(source_columns, list)
        or any(not isinstance(item, str) for item in source_columns)
        or not isinstance(source_pages, list)
        or any(
            not isinstance(page, Mapping)
            or set(page) != candidates.PAGE_KEYS
            for page in source_pages
        )
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt["parent_result_payload_sha256"]
        != parent_result["result_payload_sha256"]
        or receipt["accepted_authority_page_count"] != len(source_pages)
        or not _receipt_matches_application(receipt, application_checked)
        or copied.get("private_parent_result_payload_sha256")
        != parent_result["result_payload_sha256"]
        or copied.get("cost") != parent_result["cost"]
        or set(predictions or {}) != set(ARMS)
        or predictions[BASE_ARM] != base
        or set(hashes or {}) != set(ARMS)
        or any(
            hashes[arm] != hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        )
        or copied.get("prediction") != predictions[CANDIDATE_ARM]
        or copied.get("prediction_sha256") != hashes[CANDIDATE_ARM]
        or copied.get("prediction_changed")
        is not (predictions[BASE_ARM] != predictions[CANDIDATE_ARM])
        or receipt["candidate_prediction_changed"]
        is not copied["prediction_changed"]
        or (
            application_checked is None
            and predictions[CANDIDATE_ARM] != predictions[BASE_ARM]
        )
        or (
            application_checked is not None
            and (
                application_checked["control_prediction"] != base
                or application_checked["candidate_prediction"]
                != predictions[CANDIDATE_ARM]
                or receipt["application_payload_sha256"]
                != application_checked["artifact_payload_sha256"]
                or candidates.validate_application(
                    application_checked,
                    base_prediction=base,
                    columns=source_columns,
                    pages=source_pages,
                    selector_output=json.dumps(
                        {
                            "candidate_ids": application_checked[
                                "selected_candidate_ids"
                            ]
                        },
                        separators=(",", ":"),
                    ),
                )
                != application_checked
            )
        )
        or copied.get("scored_prediction_is_source_authoritative_candidate")
        is not True
        or copied.get(
            "shared_base_is_parent_control_not_parent_changed_safe_candidate"
        )
        is not True
        or any(
            copied.get(name) is not False
            for name in (
                candidates.PRIVILEGED_READ_FLAG,
                "entropy_or_information_gain_assigns_signed_credit",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.34 source-authoritative result drifted")
    return copied


def _stage_receipt(
    result: Mapping[str, Any],
    parent_stage: Mapping[str, Any],
) -> dict[str, Any]:
    checked = validate_result(result)
    stage = parent.validate_stage_receipt(parent_stage)
    receipt = validate_receipt(checked["source_authoritative_receipt"])
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "failure_present": False,
        "failure_stage": None,
        "failure_type": None,
        "source_authoritative_receipt": copy.deepcopy(receipt),
        "parent_stage_receipt": copy.deepcopy(stage),
        "parent_runtime_result_payload_sha256": checked[
            "private_parent_result_payload_sha256"
        ],
        "runtime_result_payload_sha256": checked["result_payload_sha256"],
        "outer_physical_budget_receipt": copy.deepcopy(
            stage["outer_physical_budget_receipt"]
        ),
        "one_parent_forward_and_pure_local_candidate_application": True,
        "query_fetch_model_token_context_and_wall_caps_unchanged": True,
        "contains_question_query_url_page_quote_prediction_answer_opaque_id_or_credential": False,
        candidates.PRIVILEGED_READ_FLAG: False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_stage_receipt(value)


def validate_stage_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    receipt = copied.get("source_authoritative_receipt")
    stage = copied.get("parent_stage_receipt")
    budget = copied.get("outer_physical_budget_receipt")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "failure_present",
        "failure_stage",
        "failure_type",
        "source_authoritative_receipt",
        "parent_stage_receipt",
        "parent_runtime_result_payload_sha256",
        "runtime_result_payload_sha256",
        "outer_physical_budget_receipt",
        "one_parent_forward_and_pure_local_candidate_application",
        "query_fetch_model_token_context_and_wall_caps_unchanged",
        "contains_question_query_url_page_quote_prediction_answer_opaque_id_or_credential",
        candidates.PRIVILEGED_READ_FLAG,
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != STAGE_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("failure_present") is not False
        or copied.get("failure_stage") is not None
        or copied.get("failure_type") is not None
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or not isinstance(stage, Mapping)
        or parent.validate_stage_receipt(stage) != dict(stage)
        or not isinstance(budget, Mapping)
        or cap.validate_budget_receipt(budget) != dict(budget)
        or stage["outer_physical_budget_receipt"] != budget
        or copied.get("parent_runtime_result_payload_sha256")
        != receipt["parent_result_payload_sha256"]
        or not isinstance(copied.get("runtime_result_payload_sha256"), str)
        or len(copied["runtime_result_payload_sha256"]) != 64
        or copied.get("one_parent_forward_and_pure_local_candidate_application")
        is not True
        or copied.get("query_fetch_model_token_context_and_wall_caps_unchanged")
        is not True
        or any(
            copied.get(name) is not False
            for name in (
                "contains_question_query_url_page_quote_prediction_answer_opaque_id_or_credential",
                candidates.PRIVILEGED_READ_FLAG,
                "entropy_or_information_gain_assigns_signed_credit",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.34 source-authoritative stage receipt drifted")
    return copied


def run_task(
    task: Mapping[str, Any],
    *,
    model: cap.HardCappedModelLimiter,
    searches: Mapping[str, cap.HardCappedSearchClient],
    limits: score.ScoreFirstLimits,
    budget: cap.PhysicalEffectBudget,
    monotonic: Callable[[], float],
) -> tuple[dict[str, Any], dict[str, Any]]:
    visible = score.validate_visible_task(task)
    created: list[_SourceAuthoritativeCaptureHybrid] = []
    parent_result, parent_stage = _parent_runner(created)(
        visible,
        model=model,
        searches=searches,
        limits=limits,
        budget=budget,
        monotonic=monotonic,
    )
    if len(created) != 1:
        raise RuntimeError("V2.54.34 task-local parent count drifted")
    result = validate_result(_wrap_result(parent_result, created[0]))
    return result, _stage_receipt(result, parent_stage)


__all__ = [
    "ARMS",
    "BASE_ARM",
    "CANDIDATE_ARM",
    "PHASES",
    "POLICY_ID",
    "ProductionOnlyStageError",
    "RECEIPT_ROLE",
    "ROLE",
    "STAGE_RECEIPT_ROLE",
    "run_task",
    "validate_receipt",
    "validate_result",
    "validate_stage_receipt",
]
