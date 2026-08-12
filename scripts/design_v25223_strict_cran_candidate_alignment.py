#!/usr/bin/env python3
"""Freeze the V2.52.23 strict-CRAN candidate alignment decision.

This design performs only local, synthetic, pure-function checks.  It records
that the frozen V2.52.15 CRAN candidate parser is intentionally broader than
the V2.52.22 strict body attestor, so composing them is not yet authorized.
"""

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

from deepwide_agent import v25215_offline_candidate_discovery as legacy  # noqa: E402
from deepwide_agent import v25222_strict_cran_dcf_attestation as strict  # noqa: E402
from scripts import audit_v25210_receipt_disposition_observer_build as base  # noqa: E402
from scripts import audit_v25215_offline_candidate_discovery_build as legacy_audit  # noqa: E402
from scripts import audit_v25222_strict_cran_dcf_attestation_build as strict_audit  # noqa: E402
from scripts import design_v25221_cran_repository_format_evidence as evidence  # noqa: E402


DATE = "20260812"
OUTPUT = Path(f"results/v25223_strict_cran_candidate_alignment_design_v1_{DATE}.json")
SOURCE = Path("scripts/design_v25223_strict_cran_candidate_alignment.py")
TEST = Path("tests/test_design_v25223_strict_cran_candidate_alignment.py")
LEGACY_SOURCE = Path("src/deepwide_agent/v25215_offline_candidate_discovery.py")
LEGACY_AUDIT = legacy_audit.OUTPUT
EVIDENCE = evidence.OUTPUT
STRICT_SOURCE = Path("src/deepwide_agent/v25222_strict_cran_dcf_attestation.py")
STRICT_AUDIT = strict_audit.OUTPUT
ATTEMPT_CLAIM = Path(
    "results/v25219_snapshot_population_attempt_claim_v1_20260812.json"
)
NO_GO_RESULT = Path("results/v25219_snapshot_population_freeze_v1_20260812.json")
FIXED_HASHES = {
    LEGACY_SOURCE: "24a28f4fb85ca6a9bc7df5164813ab4ac823b3e31518ceb3e92818bc11682fab",
    LEGACY_AUDIT: "0793a619b853e2a69096bd199aa1c558da7299f704b8a201236fe3332ad171a5",
    EVIDENCE: "d3e106735d70f9c827a9727f37eb9ad5162c33d31da98d54fcb84d0990fa59b9",
    STRICT_SOURCE: "12665386ed26af983de2ccc2e0a209726dc95937609d53241c8590c1167af0a1",
    STRICT_AUDIT: "876e5f10cc0f86ba96549c1111d018df6d23625a628577d5667839b8a1bdcc5c",
    ATTEMPT_CLAIM: "815aa9bd1c29e6e128cde1e0cbdacf284cb6e7b6313213ae6cd753a35a1869fd",
    NO_GO_RESULT: "d98abd021142f0f94b0afcf7f06ce4834c6337f04dbb51cccbd60fa5128617e1",
}
MISMATCH_CASES = (
    (
        "missing_version_predicate",
        b"Package: HasSystem\nLicense: BSD\nSystemRequirements: libx\n",
        "minimum_candidate_coverage",
    ),
    (
        "colon_without_required_space",
        b"Package:X\nVersion:1\nLicense:MIT\nSuggests:a\n",
        "dcf_syntax",
    ),
    (
        "bare_carriage_return_newlines",
        b"Package: X\rVersion: 1\rLicense: MIT\rSuggests: a\r",
        "newline",
    ),
)
payload_sha256 = base.payload_sha256


def _hash_barrier() -> bool:
    return all(base.base.sha256(path) == digest for path, digest in FIXED_HASHES.items())


def _parent_barrier() -> bool:
    if not _hash_barrier():
        return False
    legacy_value = legacy_audit.validate_audit(
        json.loads(base.base._ordinary(LEGACY_AUDIT).read_text(encoding="utf-8"))
    )
    evidence_value = evidence.validate_design(
        json.loads(base.base._ordinary(EVIDENCE).read_text(encoding="utf-8"))
    )
    strict_value = strict_audit.validate_audit(
        json.loads(base.base._ordinary(STRICT_AUDIT).read_text(encoding="utf-8"))
    )
    claim = json.loads(base.base._ordinary(ATTEMPT_CLAIM).read_text(encoding="utf-8"))
    no_go = json.loads(base.base._ordinary(NO_GO_RESULT).read_text(encoding="utf-8"))
    return bool(
        legacy_value["audit_valid"] is True
        and legacy_value["findings"] == []
        and legacy_value["authorization"]["offline_candidate_discovery_build_only"]
        is True
        and evidence_value["evidence_limits"][
            "official_documentation_establishes_repository_body_format"
        ]
        is True
        and evidence_value["evidence_limits"][
            "official_documentation_establishes_specific_alternate_http_mime"
        ]
        is False
        and strict_value["audit_valid"] is True
        and strict_value["findings"] == []
        and strict_value["authorization"][
            "strict_cran_dcf_body_attestation_build_only"
        ]
        is True
        and claim.get("claim_is_permanent_even_if_process_crashes_or_result_write_fails")
        is True
        and claim.get(
            "retry_refetch_backfill_replacement_or_second_batch_authorized"
        )
        is False
        and no_go.get("status") == "no_go"
        and no_go.get("failure_stage") == "snapshot_transport"
    )


def _alignment_observation() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for name, body, expected_stage in MISMATCH_CASES:
        candidates, legacy_receipt = legacy.discover_candidates(
            body, stratum="single_authority_multivalue_record"
        )
        strict_receipt = strict.attest_cran_packages_body(
            body,
            expected_body_bytes=len(body),
            expected_body_sha256=hashlib.sha256(body).hexdigest(),
        )
        rows.append(
            {
                "case": name,
                "legacy_parse_completed": legacy_receipt["parse_completed"],
                "legacy_candidate_count": len(candidates),
                "strict_attestation_passed": strict_receipt["attestation_passed"],
                "strict_failure_stage": strict_receipt["failure_stage"],
                "expected_strict_failure_stage": expected_stage,
            }
        )
    return {
        "synthetic_case_count": len(rows),
        "legacy_accept_count": sum(
            row["legacy_parse_completed"] and row["legacy_candidate_count"] == 1
            for row in rows
        ),
        "strict_reject_count": sum(
            not row["strict_attestation_passed"]
            and row["strict_failure_stage"] == row["expected_strict_failure_stage"]
            for row in rows
        ),
        "cases": rows,
        "synthetic_body_identity_record_field_or_value_persisted": False,
    }


def build_design(*, now: int | None = None) -> dict[str, Any]:
    if not _parent_barrier():
        raise RuntimeError("V2.52.23 parent barrier failed")
    alignment = _alignment_observation()
    if (
        alignment["legacy_accept_count"] != len(MISMATCH_CASES)
        or alignment["strict_reject_count"] != len(MISMATCH_CASES)
    ):
        raise RuntimeError("V2.52.23 synthetic alignment evidence drifted")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25223_strict_cran_candidate_alignment_design",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "fixed_artifact_hashes": {
            str(path): base.base.sha256(path) for path in FIXED_HASHES
        },
        "synthetic_alignment_observation": alignment,
        "alignment_decision": {
            "v25215_candidate_parser_and_v25222_attestor_semantics_aligned": False,
            "legacy_parser_omits_required_Version_predicate": True,
            "legacy_parser_accepts_colon_without_required_space": True,
            "legacy_parser_normalizes_bare_carriage_return": True,
            "strict_attestor_requires_Version": True,
            "strict_attestor_requires_colon_space": True,
            "strict_attestor_rejects_bare_carriage_return": True,
            "compose_existing_parser_after_strict_attestation": "no_go",
            "strict_candidate_extractor_build_required": True,
        },
        "successor_constraints": {
            "append_only_new_module_without_modifying_v25215_or_v25222": True,
            "candidate_extraction_uses_same_frozen_record_parser_and_predicate_as_attestation": True,
            "parent_attestation_must_pass_before_any_candidate_is_returned": True,
            "predicate_valid_and_distinct_candidate_counts_must_match_parent": True,
            "candidate_identities_returned_in_memory_only": True,
            "receipt_contains_only_body_binding_aggregate_counts_and_finite_stage": True,
            "known_safe_alternate_mime_allowlist_remains_empty": True,
            "unknown_mime_not_relabelled_or_accepted_by_mime_alone": True,
            "v25219_population_claim_or_result_not_reused": True,
            "transport_runtime_integration_requires_later_independent_audit": True,
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "strict_cran_candidate_extractor_implementation_build_only": True,
            "transport_or_content_type_acceptance_change": False,
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
    alignment = copied.get("synthetic_alignment_observation")
    decision = copied.get("alignment_decision")
    constraints = copied.get("successor_constraints")
    authorization = copied.get("authorization")
    expected_top = {
        "artifact_version",
        "role",
        "created_at_unix",
        "fixed_artifact_hashes",
        "synthetic_alignment_observation",
        "alignment_decision",
        "successor_constraints",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "network_model_search_fetch_evaluator_benchmark_or_api_called",
        "entropy_or_information_gain_assigns_signed_credit",
        "authorization",
        "design_payload_sha256",
    }
    expected_cases = [
        {
            "case": name,
            "legacy_parse_completed": True,
            "legacy_candidate_count": 1,
            "strict_attestation_passed": False,
            "strict_failure_stage": stage,
            "expected_strict_failure_stage": stage,
        }
        for name, _body, stage in MISMATCH_CASES
    ]
    expected_alignment = {
        "synthetic_case_count": 3,
        "legacy_accept_count": 3,
        "strict_reject_count": 3,
        "cases": expected_cases,
        "synthetic_body_identity_record_field_or_value_persisted": False,
    }
    expected_decision = {
        "v25215_candidate_parser_and_v25222_attestor_semantics_aligned": False,
        "legacy_parser_omits_required_Version_predicate": True,
        "legacy_parser_accepts_colon_without_required_space": True,
        "legacy_parser_normalizes_bare_carriage_return": True,
        "strict_attestor_requires_Version": True,
        "strict_attestor_requires_colon_space": True,
        "strict_attestor_rejects_bare_carriage_return": True,
        "compose_existing_parser_after_strict_attestation": "no_go",
        "strict_candidate_extractor_build_required": True,
    }
    expected_constraints = {
        "append_only_new_module_without_modifying_v25215_or_v25222": True,
        "candidate_extraction_uses_same_frozen_record_parser_and_predicate_as_attestation": True,
        "parent_attestation_must_pass_before_any_candidate_is_returned": True,
        "predicate_valid_and_distinct_candidate_counts_must_match_parent": True,
        "candidate_identities_returned_in_memory_only": True,
        "receipt_contains_only_body_binding_aggregate_counts_and_finite_stage": True,
        "known_safe_alternate_mime_allowlist_remains_empty": True,
        "unknown_mime_not_relabelled_or_accepted_by_mime_alone": True,
        "v25219_population_claim_or_result_not_reused": True,
        "transport_runtime_integration_requires_later_independent_audit": True,
    }
    expected_authorization = {
        "strict_cran_candidate_extractor_implementation_build_only": True,
        "transport_or_content_type_acceptance_change": False,
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
        or copied.get("role") != "v25223_strict_cran_candidate_alignment_design"
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied.get("created_at_unix") < 0
        or copied.get("fixed_artifact_hashes")
        != {str(path): digest for path, digest in FIXED_HASHES.items()}
        or alignment != expected_alignment
        or decision != expected_decision
        or constraints != expected_constraints
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization != expected_authorization
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.23 strict CRAN alignment design drifted")
    return copied


def main() -> None:
    value = build_design()
    base.base.publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "compose_existing_parser": value["alignment_decision"][
                    "compose_existing_parser_after_strict_attestation"
                ],
                "extractor_build_only": value["authorization"][
                    "strict_cran_candidate_extractor_implementation_build_only"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
