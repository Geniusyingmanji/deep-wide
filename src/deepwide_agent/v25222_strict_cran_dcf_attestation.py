"""Pure strict DCF body attestation for a caller-supplied CRAN snapshot.

The module has no filesystem, process, environment, network, model, search,
evaluator, or credential capability.  It never changes transport acceptance.
It verifies caller-provided byte-length/SHA binding before parsing and emits
only whole-body metadata plus aggregate record counts.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any


POLICY_ID = "v25222_strict_cran_packages_dcf_body_attestation_v1"
ROLE = "v25222_content_free_strict_cran_dcf_body_attestation"
STRATUM = "single_authority_multivalue_record"
MAXIMUM_BODY_BYTES = 32 * 1024 * 1024
MINIMUM_DISTINCT_CANDIDATES = 64
FAILURE_STAGES = (
    "body_type_or_size",
    "body_length_binding",
    "body_sha256_binding",
    "utf8_decode",
    "control_character",
    "newline",
    "dcf_syntax",
    "duplicate_field",
    "minimum_candidate_coverage",
)
_FIELD = re.compile(r"[A-Za-z][A-Za-z0-9._-]*")
_PACKAGE = re.compile(r"[A-Za-z][A-Za-z0-9.]{0,99}")


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _expected_binding(expected_body_bytes: int, expected_body_sha256: str) -> None:
    if (
        isinstance(expected_body_bytes, bool)
        or not isinstance(expected_body_bytes, int)
        or not 1 <= expected_body_bytes <= MAXIMUM_BODY_BYTES
        or not isinstance(expected_body_sha256, str)
        or len(expected_body_sha256) != 64
        or any(character not in "0123456789abcdef" for character in expected_body_sha256)
    ):
        raise ValueError("V2.52.22 expected body binding drifted")


def _decode(value: bytes) -> str:
    try:
        text = value.decode("utf-8")
    except UnicodeDecodeError:
        raise RuntimeError("utf8_decode") from None
    if any(
        ord(character) < 32 and character not in {"\t", "\n", "\r"}
        or ord(character) == 127
        for character in text
    ):
        raise RuntimeError("control_character")
    if "\r" in text.replace("\r\n", ""):
        raise RuntimeError("newline")
    return text.replace("\r\n", "\n")


def _parse_records(value: bytes) -> list[dict[str, str]]:
    text = _decode(value)
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    last_key: str | None = None
    for raw in text.split("\n"):
        if raw == "":
            if current:
                records.append(current)
                current = {}
                last_key = None
            continue
        if raw[:1] in {" ", "\t"}:
            if last_key is None:
                raise RuntimeError("dcf_syntax")
            continuation = raw.lstrip(" \t")
            if not continuation:
                raise RuntimeError("dcf_syntax")
            current[last_key] = current[last_key] + "\n" + continuation
            continue
        if ": " not in raw:
            raise RuntimeError("dcf_syntax")
        key, field_value = raw.split(": ", 1)
        if _FIELD.fullmatch(key) is None:
            raise RuntimeError("dcf_syntax")
        if key in current:
            raise RuntimeError("duplicate_field")
        current[key] = field_value
        last_key = key
    if current:
        records.append(current)
    if not records:
        raise RuntimeError("dcf_syntax")
    return records


def _candidate_counts(records: list[dict[str, str]]) -> tuple[int, int]:
    valid = 0
    identities: set[str] = set()
    for record in records:
        package = record.get("Package")
        version = record.get("Version")
        license_value = record.get("License")
        multivalue = record.get("SystemRequirements") or record.get("Suggests")
        if (
            isinstance(package, str)
            and package == package.strip()
            and _PACKAGE.fullmatch(package) is not None
            and isinstance(version, str)
            and bool(version.strip())
            and isinstance(license_value, str)
            and bool(license_value.strip())
            and isinstance(multivalue, str)
            and bool(multivalue.strip())
        ):
            valid += 1
            identities.add(package.casefold())
    return valid, len(identities)


def _observation(
    *,
    expected_body_bytes: int,
    expected_body_sha256: str,
    body_byte_count: int,
    body_sha256: str,
    failure_stage: str | None,
    parse_completed: bool,
    parsed_record_count: int,
    predicate_valid_record_count: int,
    distinct_candidate_count: int,
) -> dict[str, Any]:
    passed = failure_stage is None
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "stratum": STRATUM,
        "maximum_body_bytes": MAXIMUM_BODY_BYTES,
        "expected_body_byte_count": expected_body_bytes,
        "expected_body_sha256": expected_body_sha256,
        "body_byte_count": body_byte_count,
        "body_sha256": body_sha256,
        "body_byte_count_matches_expected": body_byte_count == expected_body_bytes,
        "body_sha256_matches_expected": body_sha256 == expected_body_sha256,
        "parse_completed": parse_completed,
        "failure_stage": failure_stage,
        "parsed_record_count": parsed_record_count,
        "predicate_valid_record_count": predicate_valid_record_count,
        "distinct_candidate_count": distinct_candidate_count,
        "minimum_distinct_candidate_count": MINIMUM_DISTINCT_CANDIDATES,
        "minimum_distinct_candidate_count_met": (
            distinct_candidate_count >= MINIMUM_DISTINCT_CANDIDATES
        ),
        "attestation_passed": passed,
        "known_safe_alternate_mime_allowlist_changed": False,
        "content_type_or_transport_acceptance_modified": False,
        "attestation_alone_authorizes_transport_acceptance": False,
        "identity_record_field_value_body_question_prediction_evidence_or_credential_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_filesystem_process_or_environment_effect": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "population_freeze_external_forward_runtime_compatibility_or_benchmark_authorized": False,
    }
    value["observation_payload_sha256"] = payload_sha256(value)
    return validate_observation(value)


def attest_cran_packages_body(
    value: object,
    *,
    expected_body_bytes: int,
    expected_body_sha256: str,
) -> dict[str, Any]:
    _expected_binding(expected_body_bytes, expected_body_sha256)
    body = value if isinstance(value, bytes) else b""
    byte_count = len(body)
    digest = hashlib.sha256(body).hexdigest()
    if not isinstance(value, bytes) or not 1 <= byte_count <= MAXIMUM_BODY_BYTES:
        return _observation(
            expected_body_bytes=expected_body_bytes,
            expected_body_sha256=expected_body_sha256,
            body_byte_count=byte_count,
            body_sha256=digest,
            failure_stage="body_type_or_size",
            parse_completed=False,
            parsed_record_count=0,
            predicate_valid_record_count=0,
            distinct_candidate_count=0,
        )
    if byte_count != expected_body_bytes:
        return _observation(
            expected_body_bytes=expected_body_bytes,
            expected_body_sha256=expected_body_sha256,
            body_byte_count=byte_count,
            body_sha256=digest,
            failure_stage="body_length_binding",
            parse_completed=False,
            parsed_record_count=0,
            predicate_valid_record_count=0,
            distinct_candidate_count=0,
        )
    if digest != expected_body_sha256:
        return _observation(
            expected_body_bytes=expected_body_bytes,
            expected_body_sha256=expected_body_sha256,
            body_byte_count=byte_count,
            body_sha256=digest,
            failure_stage="body_sha256_binding",
            parse_completed=False,
            parsed_record_count=0,
            predicate_valid_record_count=0,
            distinct_candidate_count=0,
        )
    try:
        records = _parse_records(body)
        valid_count, distinct_count = _candidate_counts(records)
    except RuntimeError as exc:
        stage = str(exc)
        if stage not in FAILURE_STAGES:
            stage = "dcf_syntax"
        return _observation(
            expected_body_bytes=expected_body_bytes,
            expected_body_sha256=expected_body_sha256,
            body_byte_count=byte_count,
            body_sha256=digest,
            failure_stage=stage,
            parse_completed=False,
            parsed_record_count=0,
            predicate_valid_record_count=0,
            distinct_candidate_count=0,
        )
    stage = (
        None
        if distinct_count >= MINIMUM_DISTINCT_CANDIDATES
        else "minimum_candidate_coverage"
    )
    return _observation(
        expected_body_bytes=expected_body_bytes,
        expected_body_sha256=expected_body_sha256,
        body_byte_count=byte_count,
        body_sha256=digest,
        failure_stage=stage,
        parse_completed=True,
        parsed_record_count=len(records),
        predicate_valid_record_count=valid_count,
        distinct_candidate_count=distinct_count,
    )


def validate_observation(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("observation_payload_sha256", None)
    stage = copied.get("failure_stage")
    parse_completed = copied.get("parse_completed")
    passed = copied.get("attestation_passed")
    counts = (
        "expected_body_byte_count",
        "body_byte_count",
        "parsed_record_count",
        "predicate_valid_record_count",
        "distinct_candidate_count",
        "minimum_distinct_candidate_count",
    )
    false_flags = (
        "known_safe_alternate_mime_allowlist_changed",
        "content_type_or_transport_acceptance_modified",
        "attestation_alone_authorizes_transport_acceptance",
        "identity_record_field_value_body_question_prediction_evidence_or_credential_persisted",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "network_model_search_fetch_evaluator_filesystem_process_or_environment_effect",
        "entropy_or_information_gain_assigns_signed_credit",
        "population_freeze_external_forward_runtime_compatibility_or_benchmark_authorized",
    )
    expected_fields = {
        "artifact_version",
        "role",
        "policy_id",
        "stratum",
        "maximum_body_bytes",
        *counts,
        "expected_body_sha256",
        "body_sha256",
        "body_byte_count_matches_expected",
        "body_sha256_matches_expected",
        "parse_completed",
        "failure_stage",
        "minimum_distinct_candidate_count_met",
        "attestation_passed",
        *false_flags,
        "observation_payload_sha256",
    }
    expected_digest = copied.get("expected_body_sha256")
    body_digest = copied.get("body_sha256")
    if (
        set(copied) != expected_fields
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("stratum") != STRATUM
        or copied.get("maximum_body_bytes") != MAXIMUM_BODY_BYTES
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or not 1 <= copied.get("expected_body_byte_count") <= MAXIMUM_BODY_BYTES
        or copied.get("minimum_distinct_candidate_count")
        != MINIMUM_DISTINCT_CANDIDATES
        or not isinstance(expected_digest, str)
        or len(expected_digest) != 64
        or not isinstance(body_digest, str)
        or len(body_digest) != 64
        or any(
            character not in "0123456789abcdef"
            for character in expected_digest + body_digest
        )
        or copied.get("body_byte_count_matches_expected")
        is not (copied["body_byte_count"] == copied["expected_body_byte_count"])
        or copied.get("body_sha256_matches_expected")
        is not (body_digest == expected_digest)
        or not isinstance(parse_completed, bool)
        or stage not in {None, *FAILURE_STAGES}
        or not isinstance(passed, bool)
        or passed is not (stage is None)
        or copied.get("predicate_valid_record_count")
        < copied.get("distinct_candidate_count")
        or copied.get("parsed_record_count")
        < copied.get("predicate_valid_record_count")
        or copied.get("minimum_distinct_candidate_count_met")
        is not (
            copied["distinct_candidate_count"] >= MINIMUM_DISTINCT_CANDIDATES
        )
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.22 CRAN DCF attestation observation drifted")
    binding_passed = bool(
        copied["body_byte_count_matches_expected"]
        and copied["body_sha256_matches_expected"]
    )
    parse_failure_stages = {
        "utf8_decode",
        "control_character",
        "newline",
        "dcf_syntax",
        "duplicate_field",
    }
    if (
        stage is None
        and (
            not binding_passed
            or parse_completed is not True
            or copied["minimum_distinct_candidate_count_met"] is not True
        )
        or stage == "minimum_candidate_coverage"
        and (
            not binding_passed
            or parse_completed is not True
            or copied["minimum_distinct_candidate_count_met"] is not False
        )
        or stage in parse_failure_stages
        and (
            not binding_passed
            or parse_completed is not False
            or any(
                copied[name]
                for name in (
                    "parsed_record_count",
                    "predicate_valid_record_count",
                    "distinct_candidate_count",
                )
            )
        )
        or stage == "body_length_binding"
        and (
            copied["body_byte_count_matches_expected"] is not False
            or parse_completed is not False
        )
        or stage == "body_sha256_binding"
        and (
            copied["body_byte_count_matches_expected"] is not True
            or copied["body_sha256_matches_expected"] is not False
            or parse_completed is not False
        )
        or stage == "body_type_or_size" and parse_completed is not False
        or stage == "body_type_or_size"
        and not (
            copied["body_byte_count"] == 0
            or copied["body_byte_count"] > MAXIMUM_BODY_BYTES
        )
        or stage != "body_type_or_size"
        and not 1 <= copied["body_byte_count"] <= MAXIMUM_BODY_BYTES
    ):
        raise ValueError("V2.52.22 CRAN DCF attestation state drifted")
    return copied


__all__ = [
    "FAILURE_STAGES",
    "MAXIMUM_BODY_BYTES",
    "MINIMUM_DISTINCT_CANDIDATES",
    "POLICY_ID",
    "ROLE",
    "STRATUM",
    "attest_cran_packages_body",
    "validate_observation",
]
