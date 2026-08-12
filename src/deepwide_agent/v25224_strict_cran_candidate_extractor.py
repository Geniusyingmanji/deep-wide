"""Pure strict CRAN candidate extraction after V2.52.22 attestation.

The caller supplies one in-memory body plus its pre-frozen byte-length and
SHA-256 binding.  The frozen V2.52.22 attestor decides body admission.  This
module then reuses that exact parser and invokes the exact frozen candidate
predicate once per parsed record, returning identities only in memory.

No filesystem, process, environment, network, model, search, evaluator, or
credential capability exists here.  This module does not alter MIME or
transport acceptance and does not authorize a snapshot request or population.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from typing import Any

from . import v25222_strict_cran_dcf_attestation as parent


POLICY_ID = "v25224_strict_cran_candidate_extractor_v1"
ROLE = "v25224_content_free_strict_cran_candidate_extraction_observation"
STRATUM = parent.STRATUM
FAILURE_STAGES = (*parent.FAILURE_STAGES, "candidate_count_parity")


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _observation(
    *,
    attestation: Mapping[str, Any],
    failure_stage: str | None,
    extracted_candidate_count: int,
    candidate_count_parity: bool,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "stratum": STRATUM,
        "parent_policy_id": parent.POLICY_ID,
        "parent_attestation_payload_sha256": attestation[
            "observation_payload_sha256"
        ],
        "expected_body_byte_count": attestation["expected_body_byte_count"],
        "expected_body_sha256": attestation["expected_body_sha256"],
        "body_byte_count": attestation["body_byte_count"],
        "body_sha256": attestation["body_sha256"],
        "parent_attestation_passed": attestation["attestation_passed"],
        "parent_failure_stage": attestation["failure_stage"],
        "parsed_record_count": attestation["parsed_record_count"],
        "predicate_valid_record_count": attestation[
            "predicate_valid_record_count"
        ],
        "parent_distinct_candidate_count": attestation[
            "distinct_candidate_count"
        ],
        "extracted_candidate_count": extracted_candidate_count,
        "candidate_count_parity": candidate_count_parity,
        "failure_stage": failure_stage,
        "extraction_completed": failure_stage is None,
        "identity_record_field_value_body_question_prediction_evidence_or_credential_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_filesystem_process_or_environment_effect": False,
        "content_type_or_transport_acceptance_modified": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "population_freeze_external_forward_runtime_compatibility_or_benchmark_authorized": False,
    }
    value["observation_payload_sha256"] = payload_sha256(value)
    return validate_observation(value)


def extract_strict_cran_candidates(
    value: object,
    *,
    expected_body_bytes: int,
    expected_body_sha256: str,
) -> tuple[list[str], dict[str, Any]]:
    """Return strict Package identities in memory and a content-free receipt."""

    attestation = parent.attest_cran_packages_body(
        value,
        expected_body_bytes=expected_body_bytes,
        expected_body_sha256=expected_body_sha256,
    )
    parent.validate_observation(attestation)
    if attestation["attestation_passed"] is not True:
        return [], _observation(
            attestation=attestation,
            failure_stage=attestation["failure_stage"],
            extracted_candidate_count=0,
            candidate_count_parity=(
                attestation["predicate_valid_record_count"] == 0
                and attestation["distinct_candidate_count"] == 0
            ),
        )

    if not isinstance(value, bytes):
        raise RuntimeError("V2.52.24 passed parent attestation without bytes")
    records = parent._parse_records(value)
    candidates: list[str] = []
    valid_records = 0
    for record in records:
        valid_count, distinct_count = parent._candidate_counts([record])
        if (valid_count, distinct_count) == (1, 1):
            package = record.get("Package")
            if not isinstance(package, str):
                raise RuntimeError("V2.52.24 parent predicate admitted no identity")
            valid_records += 1
            candidates.append(package.casefold())
        elif (valid_count, distinct_count) != (0, 0):
            raise RuntimeError("V2.52.24 parent single-record predicate drifted")

    distinct_candidates = list(dict.fromkeys(candidates))
    parity = bool(
        len(records) == attestation["parsed_record_count"]
        and valid_records == attestation["predicate_valid_record_count"]
        and len(distinct_candidates) == attestation["distinct_candidate_count"]
    )
    if not parity:
        return [], _observation(
            attestation=attestation,
            failure_stage="candidate_count_parity",
            extracted_candidate_count=0,
            candidate_count_parity=False,
        )
    return distinct_candidates, _observation(
        attestation=attestation,
        failure_stage=None,
        extracted_candidate_count=len(distinct_candidates),
        candidate_count_parity=True,
    )


def _reconstruct_parent_attestation(value: Mapping[str, Any]) -> dict[str, Any]:
    parent_stage = value.get("parent_failure_stage")
    parse_completed = parent_stage in {None, "minimum_candidate_coverage"}
    distinct_count = value.get("parent_distinct_candidate_count")
    expected_count = value.get("expected_body_byte_count")
    body_count = value.get("body_byte_count")
    expected_digest = value.get("expected_body_sha256")
    body_digest = value.get("body_sha256")
    reconstructed: dict[str, Any] = {
        "artifact_version": 1,
        "role": parent.ROLE,
        "policy_id": parent.POLICY_ID,
        "stratum": parent.STRATUM,
        "maximum_body_bytes": parent.MAXIMUM_BODY_BYTES,
        "expected_body_byte_count": expected_count,
        "expected_body_sha256": expected_digest,
        "body_byte_count": body_count,
        "body_sha256": body_digest,
        "body_byte_count_matches_expected": body_count == expected_count,
        "body_sha256_matches_expected": body_digest == expected_digest,
        "parse_completed": parse_completed,
        "failure_stage": parent_stage,
        "parsed_record_count": value.get("parsed_record_count"),
        "predicate_valid_record_count": value.get("predicate_valid_record_count"),
        "distinct_candidate_count": distinct_count,
        "minimum_distinct_candidate_count": parent.MINIMUM_DISTINCT_CANDIDATES,
        "minimum_distinct_candidate_count_met": (
            isinstance(distinct_count, int)
            and not isinstance(distinct_count, bool)
            and distinct_count >= parent.MINIMUM_DISTINCT_CANDIDATES
        ),
        "attestation_passed": value.get("parent_attestation_passed"),
        "known_safe_alternate_mime_allowlist_changed": False,
        "content_type_or_transport_acceptance_modified": False,
        "attestation_alone_authorizes_transport_acceptance": False,
        "identity_record_field_value_body_question_prediction_evidence_or_credential_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_filesystem_process_or_environment_effect": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "population_freeze_external_forward_runtime_compatibility_or_benchmark_authorized": False,
        "observation_payload_sha256": value.get(
            "parent_attestation_payload_sha256"
        ),
    }
    return parent.validate_observation(reconstructed)


def validate_observation(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("observation_payload_sha256", None)
    expected_fields = {
        "artifact_version",
        "role",
        "policy_id",
        "stratum",
        "parent_policy_id",
        "parent_attestation_payload_sha256",
        "expected_body_byte_count",
        "expected_body_sha256",
        "body_byte_count",
        "body_sha256",
        "parent_attestation_passed",
        "parent_failure_stage",
        "parsed_record_count",
        "predicate_valid_record_count",
        "parent_distinct_candidate_count",
        "extracted_candidate_count",
        "candidate_count_parity",
        "failure_stage",
        "extraction_completed",
        "identity_record_field_value_body_question_prediction_evidence_or_credential_persisted",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "network_model_search_fetch_evaluator_filesystem_process_or_environment_effect",
        "content_type_or_transport_acceptance_modified",
        "entropy_or_information_gain_assigns_signed_credit",
        "population_freeze_external_forward_runtime_compatibility_or_benchmark_authorized",
        "observation_payload_sha256",
    }
    false_flags = (
        "identity_record_field_value_body_question_prediction_evidence_or_credential_persisted",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "network_model_search_fetch_evaluator_filesystem_process_or_environment_effect",
        "content_type_or_transport_acceptance_modified",
        "entropy_or_information_gain_assigns_signed_credit",
        "population_freeze_external_forward_runtime_compatibility_or_benchmark_authorized",
    )
    count_fields = (
        "expected_body_byte_count",
        "body_byte_count",
        "parsed_record_count",
        "predicate_valid_record_count",
        "parent_distinct_candidate_count",
        "extracted_candidate_count",
    )
    parent_passed = copied.get("parent_attestation_passed")
    parent_stage = copied.get("parent_failure_stage")
    stage = copied.get("failure_stage")
    parity = copied.get("candidate_count_parity")
    completed = copied.get("extraction_completed")
    digests = (
        copied.get("parent_attestation_payload_sha256"),
        copied.get("expected_body_sha256"),
        copied.get("body_sha256"),
    )
    try:
        _reconstruct_parent_attestation(copied)
    except (TypeError, ValueError):
        raise ValueError(
            "V2.52.24 strict CRAN parent attestation binding drifted"
        ) from None
    if (
        set(copied) != expected_fields
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("stratum") != STRATUM
        or copied.get("parent_policy_id") != parent.POLICY_ID
        or any(
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            for digest in digests
        )
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in count_fields
        )
        or not 1
        <= copied.get("expected_body_byte_count")
        <= parent.MAXIMUM_BODY_BYTES
        or not isinstance(parent_passed, bool)
        or parent_stage not in {None, *parent.FAILURE_STAGES}
        or parent_passed is not (parent_stage is None)
        or stage not in {None, *FAILURE_STAGES}
        or not isinstance(parity, bool)
        or not isinstance(completed, bool)
        or completed is not (stage is None)
        or copied["predicate_valid_record_count"]
        < copied["parent_distinct_candidate_count"]
        or copied["parsed_record_count"]
        < copied["predicate_valid_record_count"]
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.24 strict CRAN extraction observation drifted")
    if (
        stage is None
        and (
            parent_passed is not True
            or parent_stage is not None
            or parity is not True
            or copied["extracted_candidate_count"]
            != copied["parent_distinct_candidate_count"]
            or copied["extracted_candidate_count"]
            < parent.MINIMUM_DISTINCT_CANDIDATES
        )
        or stage in parent.FAILURE_STAGES
        and (
            parent_passed is not False
            or parent_stage != stage
            or copied["extracted_candidate_count"] != 0
        )
        or stage == "candidate_count_parity"
        and (
            parent_passed is not True
            or parent_stage is not None
            or parity is not False
            or copied["extracted_candidate_count"] != 0
        )
    ):
        raise ValueError("V2.52.24 strict CRAN extraction state drifted")
    return copied


__all__ = [
    "FAILURE_STAGES",
    "POLICY_ID",
    "ROLE",
    "STRATUM",
    "extract_strict_cran_candidates",
    "validate_observation",
]
