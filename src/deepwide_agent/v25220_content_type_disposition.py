"""Pure content-free MIME disposition observer for frozen snapshot transport.

The observer mirrors V2.52.17's media-type normalization and acceptance
decision without importing its network-capable module.  It persists only a
finite disposition.  The reserved known-safe-alternate vocabulary is empty in
this version, so observing a rejected value cannot relax transport behavior.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from typing import Any


POLICY_ID = "v25220_content_free_content_type_disposition_v1"
ROLE = "v25220_content_free_content_type_disposition_observation"
STRATA = (
    "single_authority_exact_record",
    "single_authority_multivalue_record",
    "same_identity_multipage_record",
    "sparse_ambiguous_open_web_record",
)
ACCEPTED_CONTENT_TYPES = {
    STRATA[0]: ("application/json",),
    STRATA[1]: ("text/plain",),
    STRATA[2]: ("application/json",),
    STRATA[3]: (
        "text/html",
        "application/vnd.pypi.simple.v1+html",
    ),
}
KNOWN_SAFE_ALTERNATES = {stratum: () for stratum in STRATA}
DISPOSITIONS = (
    "missing",
    "accepted",
    "known_safe_alternate",
    "unknown_disallowed",
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _normalize_media_type(raw_header: str) -> str:
    if not isinstance(raw_header, str):
        raise TypeError("V2.52.20 content type must be a string")
    return raw_header.split(";", 1)[0].strip().casefold()


def _classify(
    normalized_media_type: str,
    *,
    accepted: tuple[str, ...],
    known_safe_alternates: tuple[str, ...],
) -> str:
    if (
        not isinstance(normalized_media_type, str)
        or not isinstance(accepted, tuple)
        or not isinstance(known_safe_alternates, tuple)
        or set(accepted).intersection(known_safe_alternates)
    ):
        raise ValueError("V2.52.20 classifier contract drifted")
    if not normalized_media_type:
        return "missing"
    if normalized_media_type in accepted:
        return "accepted"
    if normalized_media_type in known_safe_alternates:
        return "known_safe_alternate"
    return "unknown_disallowed"


def observe_content_type(
    stratum: str,
    *,
    header_present: bool,
    raw_header: str | None,
) -> dict[str, Any]:
    if stratum not in STRATA or not isinstance(header_present, bool):
        raise ValueError("V2.52.20 observation input drifted")
    if header_present:
        if not isinstance(raw_header, str):
            raise ValueError("V2.52.20 present header shape drifted")
        normalized = _normalize_media_type(raw_header)
    else:
        if raw_header is not None:
            raise ValueError("V2.52.20 absent header carried a value")
        normalized = ""
    disposition = _classify(
        normalized,
        accepted=ACCEPTED_CONTENT_TYPES[stratum],
        known_safe_alternates=KNOWN_SAFE_ALTERNATES[stratum],
    )
    parent_accepts = disposition == "accepted"
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "stratum": stratum,
        "header_present": header_present,
        "disposition": disposition,
        "frozen_parent_transport_accepts": parent_accepts,
        "observer_successor_transport_accepts": parent_accepts,
        "known_safe_alternate_allowlist_count": len(
            KNOWN_SAFE_ALTERNATES[stratum]
        ),
        "known_safe_alternate_runtime_injection_allowed": False,
        "observer_changes_transport_acceptance": False,
        "header_original_normalized_value_or_hash_persisted": False,
        "contains_url_body_identity_record_value_question_prediction_evidence_exception_message_traceback_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_effect": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "transport_relaxation_population_freeze_external_forward_or_runtime_compatibility_authorized": False,
    }
    value["observation_payload_sha256"] = payload_sha256(value)
    return validate_observation(value)


def validate_observation(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("observation_payload_sha256", None)
    false_flags = (
        "known_safe_alternate_runtime_injection_allowed",
        "observer_changes_transport_acceptance",
        "header_original_normalized_value_or_hash_persisted",
        "contains_url_body_identity_record_value_question_prediction_evidence_exception_message_traceback_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "network_model_search_fetch_evaluator_benchmark_or_api_effect",
        "entropy_or_information_gain_assigns_signed_credit",
        "transport_relaxation_population_freeze_external_forward_or_runtime_compatibility_authorized",
    )
    disposition = copied.get("disposition")
    parent_accepts = copied.get("frozen_parent_transport_accepts")
    successor_accepts = copied.get("observer_successor_transport_accepts")
    expected_fields = {
        "artifact_version",
        "role",
        "policy_id",
        "stratum",
        "header_present",
        "disposition",
        "frozen_parent_transport_accepts",
        "observer_successor_transport_accepts",
        "known_safe_alternate_allowlist_count",
        *false_flags,
        "observation_payload_sha256",
    }
    if (
        set(copied) != expected_fields
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("stratum") not in STRATA
        or not isinstance(copied.get("header_present"), bool)
        or disposition not in DISPOSITIONS
        or disposition == "known_safe_alternate"
        or not isinstance(parent_accepts, bool)
        or not isinstance(successor_accepts, bool)
        or parent_accepts is not (disposition == "accepted")
        or successor_accepts is not parent_accepts
        or copied.get("known_safe_alternate_allowlist_count") != 0
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.20 content-type observation drifted")
    return copied


__all__ = [
    "ACCEPTED_CONTENT_TYPES",
    "DISPOSITIONS",
    "KNOWN_SAFE_ALTERNATES",
    "POLICY_ID",
    "ROLE",
    "STRATA",
    "observe_content_type",
    "validate_observation",
]
