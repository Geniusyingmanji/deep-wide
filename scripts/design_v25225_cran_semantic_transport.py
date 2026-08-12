#!/usr/bin/env python3
"""Freeze the V2.52.25 CRAN semantic-transport implementation contract."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25210_receipt_disposition_observer_build as base  # noqa: E402
from scripts import audit_v25217_single_snapshot_transport_build as transport_audit  # noqa: E402
from scripts import audit_v25218_snapshot_hard_deadline_controller_build as deadline_audit  # noqa: E402
from scripts import audit_v25220_content_type_disposition_build as disposition_audit  # noqa: E402
from scripts import audit_v25224_strict_cran_candidate_extractor_build as extractor_audit  # noqa: E402
from scripts import design_v25221_cran_repository_format_evidence as evidence  # noqa: E402
from scripts import design_v25223_strict_cran_candidate_alignment as alignment  # noqa: E402


DATE = "20260812"
OUTPUT = Path(f"results/v25225_cran_semantic_transport_design_v1_{DATE}.json")
SOURCE = Path("scripts/design_v25225_cran_semantic_transport.py")
TEST = Path("tests/test_design_v25225_cran_semantic_transport.py")
TRANSPORT_AUDIT = transport_audit.OUTPUT
DEADLINE_AUDIT = deadline_audit.OUTPUT
DISPOSITION_AUDIT = disposition_audit.OUTPUT
EVIDENCE = evidence.OUTPUT
ALIGNMENT = alignment.OUTPUT
EXTRACTOR_AUDIT = extractor_audit.OUTPUT
ATTEMPT_CLAIM = Path(
    "results/v25219_snapshot_population_attempt_claim_v1_20260812.json"
)
NO_GO_RESULT = Path("results/v25219_snapshot_population_freeze_v1_20260812.json")
FIXED_HASHES = {
    TRANSPORT_AUDIT: "d13c9334b91937738c70da344328e6714ad9ea20a6771daa6105e584945afe53",
    DEADLINE_AUDIT: "988185da358ad0a9b13e846c1abc735152a4a4cf60a103bc74ee6b7c4ba86edc",
    DISPOSITION_AUDIT: "4ce79154f88d835faf6f80287ce0c2b66d249287d7d5ee1dcd1bed3d39ddcb5a",
    EVIDENCE: "d3e106735d70f9c827a9727f37eb9ad5162c33d31da98d54fcb84d0990fa59b9",
    ALIGNMENT: "212d0c96ad3fbf2479e2275e90df29f47bfaf04e0554435bec0d3bedd4fd27ac",
    EXTRACTOR_AUDIT: "a0dad97a06d412fb1f6741e24a09db2f9c608902e4b06dd536ac6e805975072c",
    ATTEMPT_CLAIM: "815aa9bd1c29e6e128cde1e0cbdacf284cb6e7b6313213ae6cd753a35a1869fd",
    NO_GO_RESULT: "d98abd021142f0f94b0afcf7f06ce4834c6337f04dbb51cccbd60fa5128617e1",
}
ENDPOINT = "https://cran.r-project.org/src/contrib/PACKAGES"
ENDPOINT_SHA256 = hashlib.sha256(ENDPOINT.encode("utf-8")).hexdigest()
payload_sha256 = base.payload_sha256


def _hash_barrier() -> bool:
    return all(base.base.sha256(path) == digest for path, digest in FIXED_HASHES.items())


def _parent_barrier() -> bool:
    if not _hash_barrier():
        return False
    transport = transport_audit.validate_audit(
        json.loads(base.base._ordinary(TRANSPORT_AUDIT).read_text(encoding="utf-8"))
    )
    deadline = deadline_audit.validate_audit(
        json.loads(base.base._ordinary(DEADLINE_AUDIT).read_text(encoding="utf-8"))
    )
    disposition = disposition_audit.validate_audit(
        json.loads(base.base._ordinary(DISPOSITION_AUDIT).read_text(encoding="utf-8"))
    )
    official = evidence.validate_design(
        json.loads(base.base._ordinary(EVIDENCE).read_text(encoding="utf-8"))
    )
    aligned = alignment.validate_design(
        json.loads(base.base._ordinary(ALIGNMENT).read_text(encoding="utf-8"))
    )
    extractor = extractor_audit.validate_audit(
        json.loads(base.base._ordinary(EXTRACTOR_AUDIT).read_text(encoding="utf-8"))
    )
    claim = json.loads(base.base._ordinary(ATTEMPT_CLAIM).read_text(encoding="utf-8"))
    no_go = json.loads(base.base._ordinary(NO_GO_RESULT).read_text(encoding="utf-8"))
    return bool(
        transport["audit_valid"] is True
        and transport["findings"] == []
        and deadline["audit_valid"] is True
        and deadline["findings"] == []
        and disposition["audit_valid"] is True
        and disposition["known_safe_alternate_allowlist_count"] == 0
        and official["evidence_limits"][
            "official_documentation_establishes_repository_body_format"
        ]
        is True
        and official["evidence_limits"][
            "official_documentation_establishes_specific_alternate_http_mime"
        ]
        is False
        and aligned["alignment_decision"][
            "compose_existing_parser_after_strict_attestation"
        ]
        == "no_go"
        and extractor["audit_valid"] is True
        and extractor["findings"] == []
        and extractor["authorization"]["strict_cran_candidate_extractor_build_only"]
        is True
        and claim.get(
            "retry_refetch_backfill_replacement_or_second_batch_authorized"
        )
        is False
        and no_go.get("status") == "no_go"
        and no_go.get("failure_stage") == "snapshot_transport"
    )


def build_design(*, now: int | None = None) -> dict[str, Any]:
    if not _parent_barrier():
        raise RuntimeError("V2.52.25 parent barrier failed")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25225_cran_semantic_transport_design",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "fixed_artifact_hashes": {
            str(path): base.base.sha256(path) for path in FIXED_HASHES
        },
        "fixed_endpoint": {
            "url": ENDPOINT,
            "url_sha256": ENDPOINT_SHA256,
            "scheme": "https",
            "hostname": "cran.r-project.org",
            "path": "/src/contrib/PACKAGES",
            "maximum_response_bytes": 32 * 1024 * 1024,
        },
        "policy_change": {
            "new_version_and_namespace_required": True,
            "old_v25217_text_plain_only_acceptance_modified": False,
            "new_policy_acceptance_differs_from_v25217_for_missing_or_unknown_mime": True,
            "known_safe_alternate_mime_allowlist_remains_empty": True,
            "missing_or_unknown_mime_is_not_relabelled_as_text_plain": True,
            "mime_alone_never_establishes_success": True,
            "strict_body_semantics_can_establish_success_only_after_transport_safety": True,
        },
        "transport_safety_contract": {
            "literal_endpoint_only_no_runtime_url_input": True,
            "single_request_method": "GET",
            "maximum_provider_attempts": 1,
            "redirect_count": 0,
            "retry_count": 0,
            "conditional_refetch_count": 0,
            "trust_environment_disabled": True,
            "authorization_cookie_query_secret_or_credential": False,
            "tls_verification_and_hostname_verification_required": True,
            "public_address_dns_preflight_required": True,
            "dns_preflight_result_pinned_to_transport": False,
            "untrusted_runtime_endpoint_or_hostname_forbidden": True,
            "http_status_must_equal_200": True,
            "nonempty_streamed_body_with_byte_cap_required": True,
            "body_length_and_sha256_binding_required": True,
            "independent_fork_hard_deadline_controller_required": True,
            "raw_body_in_memory_only": True,
            "failure_discards_body_and_candidates": True,
        },
        "semantic_gate_contract": {
            "content_type_disposition_observed_before_body_gate": True,
            "disposition_vocabulary": [
                "missing",
                "accepted",
                "known_safe_alternate",
                "unknown_disallowed",
            ],
            "known_safe_alternate_disposition_reachable": False,
            "raw_or_normalized_header_value_or_hash_persisted": False,
            "v25224_strict_extractor_required": True,
            "strict_extraction_must_complete": True,
            "candidate_count_parity_required": True,
            "minimum_distinct_candidate_count": 64,
            "transport_and_semantic_receipts_must_bind_same_body_length_and_sha256": True,
            "candidate_identity_returned_in_memory_only": True,
            "mime_magic_bytes_or_http_200_alone_never_authorizes_success": True,
        },
        "failure_policy": {
            "dns_timeout_transport_redirect_non200_empty_oversize_stream_or_deadline": "failure_discard_all",
            "strict_utf8_control_newline_dcf_duplicate_predicate_or_count_parity": "failure_discard_all",
            "receipt_body_length_or_sha_mismatch": "failure_discard_all",
            "observer_or_validator_exception": "failure_discard_all",
            "retry_refetch_backfill_replacement_or_second_batch": "forbidden",
            "v25219_namespace_population_claim_or_result_reuse": "forbidden",
        },
        "residual_risks": {
            "dns_preflight_not_connection_pinned": True,
            "fixed_hostname_tls_verification_remains_security_boundary": True,
            "official_body_format_does_not_define_http_mime": True,
            "semantic_success_does_not_prove_candidate_freshness_or_benchmark_value": True,
            "future_effect_requires_independent_protocol_preactivation_and_execution_start": True,
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "cran_semantic_transport_implementation_build_only": True,
            "fresh_semantic_transport_protocol_design": False,
            "public_snapshot_network_access_or_execution_start": False,
            "v25219_retry_refetch_backfill_replacement_or_second_batch": False,
            "real_identity_selection_or_population_freeze": False,
            "probe_runtime_integration_external_forward_or_activation": False,
            "runtime_compatibility_validator_relaxation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    value["design_payload_sha256"] = payload_sha256(value)
    return validate_design(value)


def validate_design(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("design_payload_sha256", None)
    expected_top = {
        "artifact_version",
        "role",
        "created_at_unix",
        "fixed_artifact_hashes",
        "fixed_endpoint",
        "policy_change",
        "transport_safety_contract",
        "semantic_gate_contract",
        "failure_policy",
        "residual_risks",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "network_model_search_fetch_evaluator_benchmark_or_api_called",
        "entropy_or_information_gain_assigns_signed_credit",
        "authorization",
        "design_payload_sha256",
    }
    expected_endpoint = {
        "url": ENDPOINT,
        "url_sha256": ENDPOINT_SHA256,
        "scheme": "https",
        "hostname": "cran.r-project.org",
        "path": "/src/contrib/PACKAGES",
        "maximum_response_bytes": 32 * 1024 * 1024,
    }
    expected_policy = {
        "new_version_and_namespace_required": True,
        "old_v25217_text_plain_only_acceptance_modified": False,
        "new_policy_acceptance_differs_from_v25217_for_missing_or_unknown_mime": True,
        "known_safe_alternate_mime_allowlist_remains_empty": True,
        "missing_or_unknown_mime_is_not_relabelled_as_text_plain": True,
        "mime_alone_never_establishes_success": True,
        "strict_body_semantics_can_establish_success_only_after_transport_safety": True,
    }
    expected_transport = {
        "literal_endpoint_only_no_runtime_url_input": True,
        "single_request_method": "GET",
        "maximum_provider_attempts": 1,
        "redirect_count": 0,
        "retry_count": 0,
        "conditional_refetch_count": 0,
        "trust_environment_disabled": True,
        "authorization_cookie_query_secret_or_credential": False,
        "tls_verification_and_hostname_verification_required": True,
        "public_address_dns_preflight_required": True,
        "dns_preflight_result_pinned_to_transport": False,
        "untrusted_runtime_endpoint_or_hostname_forbidden": True,
        "http_status_must_equal_200": True,
        "nonempty_streamed_body_with_byte_cap_required": True,
        "body_length_and_sha256_binding_required": True,
        "independent_fork_hard_deadline_controller_required": True,
        "raw_body_in_memory_only": True,
        "failure_discards_body_and_candidates": True,
    }
    expected_semantic = {
        "content_type_disposition_observed_before_body_gate": True,
        "disposition_vocabulary": [
            "missing",
            "accepted",
            "known_safe_alternate",
            "unknown_disallowed",
        ],
        "known_safe_alternate_disposition_reachable": False,
        "raw_or_normalized_header_value_or_hash_persisted": False,
        "v25224_strict_extractor_required": True,
        "strict_extraction_must_complete": True,
        "candidate_count_parity_required": True,
        "minimum_distinct_candidate_count": 64,
        "transport_and_semantic_receipts_must_bind_same_body_length_and_sha256": True,
        "candidate_identity_returned_in_memory_only": True,
        "mime_magic_bytes_or_http_200_alone_never_authorizes_success": True,
    }
    expected_failure = {
        "dns_timeout_transport_redirect_non200_empty_oversize_stream_or_deadline": "failure_discard_all",
        "strict_utf8_control_newline_dcf_duplicate_predicate_or_count_parity": "failure_discard_all",
        "receipt_body_length_or_sha_mismatch": "failure_discard_all",
        "observer_or_validator_exception": "failure_discard_all",
        "retry_refetch_backfill_replacement_or_second_batch": "forbidden",
        "v25219_namespace_population_claim_or_result_reuse": "forbidden",
    }
    expected_risks = {
        "dns_preflight_not_connection_pinned": True,
        "fixed_hostname_tls_verification_remains_security_boundary": True,
        "official_body_format_does_not_define_http_mime": True,
        "semantic_success_does_not_prove_candidate_freshness_or_benchmark_value": True,
        "future_effect_requires_independent_protocol_preactivation_and_execution_start": True,
    }
    expected_authorization = {
        "cran_semantic_transport_implementation_build_only": True,
        "fresh_semantic_transport_protocol_design": False,
        "public_snapshot_network_access_or_execution_start": False,
        "v25219_retry_refetch_backfill_replacement_or_second_batch": False,
        "real_identity_selection_or_population_freeze": False,
        "probe_runtime_integration_external_forward_or_activation": False,
        "runtime_compatibility_validator_relaxation_or_prediction_change": False,
        "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
    }
    if (
        set(copied) != expected_top
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25225_cran_semantic_transport_design"
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied.get("created_at_unix") < 0
        or copied.get("fixed_artifact_hashes")
        != {str(path): digest for path, digest in FIXED_HASHES.items()}
        or copied.get("fixed_endpoint") != expected_endpoint
        or copied.get("policy_change") != expected_policy
        or copied.get("transport_safety_contract") != expected_transport
        or copied.get("semantic_gate_contract") != expected_semantic
        or copied.get("failure_policy") != expected_failure
        or copied.get("residual_risks") != expected_risks
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or copied.get("authorization") != expected_authorization
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.25 CRAN semantic transport design drifted")
    return copied


def main() -> None:
    value = build_design()
    base.base.publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "implementation_build_only": value["authorization"][
                    "cran_semantic_transport_implementation_build_only"
                ],
                "network_authorized": value["authorization"][
                    "public_snapshot_network_access_or_execution_start"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
