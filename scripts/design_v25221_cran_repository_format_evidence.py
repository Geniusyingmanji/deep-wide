#!/usr/bin/env python3
"""Freeze official pre-effect evidence for a CRAN DCF body-attestation design."""

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
from scripts import audit_v25220_content_type_disposition_build as parent  # noqa: E402


DATE = "20260812"
OUTPUT = Path(f"results/v25221_cran_repository_format_evidence_v1_{DATE}.json")
SOURCE = Path("scripts/design_v25221_cran_repository_format_evidence.py")
TEST = Path("tests/test_design_v25221_cran_repository_format_evidence.py")
PARENT_AUDIT = parent.OUTPUT
EXPECTED_PARENT_AUDIT_SHA256 = (
    "4ce79154f88d835faf6f80287ce0c2b66d249287d7d5ee1dcd1bed3d39ddcb5a"
)
OFFICIAL_DOCUMENTS = {
    "r_admin": {
        "url": "https://cran.r-project.org/doc/manuals/r-release/R-admin.html",
        "whole_document_sha256": "c2ddc83fdfa0ad98d8a455a85dff38134e2d2a2bffe778e6d062b5d585533686",
        "repository_section_line_interval": [2904, 2967],
        "repository_section_sha256": "70a983cffc12bf920a395cde4d2cf4ecc1028621a55e1c563d8c1cb0870ca387",
    },
    "r_exts": {
        "url": "https://cran.r-project.org/doc/manuals/r-release/R-exts.html",
        "whole_document_sha256": "4f83a630fa0a68df34ab111847819bb9b3014922b09bf484db2d037d22295a59",
        "dcf_section_line_interval": [881, 900],
        "dcf_section_sha256": "3952f2fd4390da1868da5ec95c8ca71ff923eca23d4d1c1edd614f6e70608d64",
    },
}
payload_sha256 = base.payload_sha256


def _parent_barrier() -> bool:
    raw = json.loads(base.base._ordinary(PARENT_AUDIT).read_text(encoding="utf-8"))
    value = parent.validate_audit(raw)
    authorization = value["authorization"]
    return bool(
        base.base.sha256(PARENT_AUDIT) == EXPECTED_PARENT_AUDIT_SHA256
        and value["audit_valid"] is True
        and value["findings"] == []
        and value["known_safe_alternate_allowlist_count"] == 0
        and authorization["content_type_disposition_observer_build_only"] is True
        and authorization["fresh_transport_observability_protocol_design"] is False
        and authorization["known_safe_alternate_allowlist_change"] is False
        and authorization["public_snapshot_network_access_or_execution_start"] is False
    )


def build_design(*, now: int | None = None) -> dict[str, Any]:
    if not _parent_barrier():
        raise RuntimeError("V2.52.21 parent observer audit barrier failed")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25221_cran_repository_format_pre_effect_evidence",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_content_type_observer_audit": {
            "path": str(PARENT_AUDIT),
            "sha256": base.base.sha256(PARENT_AUDIT),
        },
        "official_documents": copy.deepcopy(OFFICIAL_DOCUMENTS),
        "official_evidence": {
            "cran_style_terminal_repository_directory_must_contain_PACKAGES": True,
            "PACKAGES_may_be_concatenated_DESCRIPTION_records_separated_by_blank_lines": True,
            "PACKAGES_rds_and_PACKAGES_gz_are_optional_preferred_alternatives": True,
            "DESCRIPTION_uses_Debian_Control_File_style_records": True,
            "DCF_fields_begin_with_ASCII_name_colon_and_space": True,
            "DCF_continuation_lines_begin_with_space_or_tab": True,
            "repository_format_section_explicit_http_content_type_or_mime_contract_count": 0,
        },
        "evidence_limits": {
            "official_documentation_establishes_repository_body_format": True,
            "official_documentation_establishes_specific_alternate_http_mime": False,
            "absence_of_mime_contract_does_not_prove_any_observed_mime_safe": True,
            "v25219_actual_rejected_header_value_was_not_persisted_or_recovered": True,
            "v25219_snapshot_endpoint_was_not_called_by_this_design": True,
            "whole_document_and_section_hashes_are_retrieval_specific_not_semantic_body_hashes": True,
            "raw_official_document_bodies_persisted_in_repository": False,
        },
        "successor_design_constraints": {
            "known_safe_alternate_mime_allowlist_remains_empty": True,
            "fixed_stratum_only": "single_authority_multivalue_record",
            "fixed_endpoint_path_only": "/src/contrib/PACKAGES",
            "candidate_may_require_strict_DCF_body_attestation": True,
            "candidate_may_not_accept_body_on_mime_or_magic_bytes_alone": True,
            "candidate_must_require_minimum_64_distinct_valid_records": True,
            "candidate_must_require_each_selected_record_has_Package_Version_License_and_SystemRequirements_or_Suggests": True,
            "duplicate_field_malformed_continuation_invalid_utf8_control_character_and_oversize_fail_closed": True,
            "unknown_or_disallowed_mime_remains_reported_not_silently_relabelled": True,
            "body_bytes_sha256_length_and_transport_receipt_binding_required": True,
            "redirect_retry_refetch_backfill_replacement_and_second_batch": 0,
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "official_documentation_https_network_called": True,
        "public_snapshot_endpoint_or_api_called": False,
        "model_hosted_search_tavily_evaluator_or_benchmark_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "strict_cran_dcf_body_attestation_implementation_build_only": True,
            "known_safe_alternate_mime_allowlist_change": False,
            "fresh_transport_observability_protocol_design": False,
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
    official = copied.get("official_evidence") or {}
    limits = copied.get("evidence_limits") or {}
    constraints = copied.get("successor_design_constraints") or {}
    authorization = copied.get("authorization") or {}
    parent_audit = copied.get("parent_content_type_observer_audit") or {}
    expected_fields = {
        "artifact_version",
        "role",
        "created_at_unix",
        "parent_content_type_observer_audit",
        "official_documents",
        "official_evidence",
        "evidence_limits",
        "successor_design_constraints",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "official_documentation_https_network_called",
        "public_snapshot_endpoint_or_api_called",
        "model_hosted_search_tavily_evaluator_or_benchmark_called",
        "entropy_or_information_gain_assigns_signed_credit",
        "authorization",
        "design_payload_sha256",
    }
    expected_limits = {
        "official_documentation_establishes_repository_body_format": True,
        "official_documentation_establishes_specific_alternate_http_mime": False,
        "absence_of_mime_contract_does_not_prove_any_observed_mime_safe": True,
        "v25219_actual_rejected_header_value_was_not_persisted_or_recovered": True,
        "v25219_snapshot_endpoint_was_not_called_by_this_design": True,
        "whole_document_and_section_hashes_are_retrieval_specific_not_semantic_body_hashes": True,
        "raw_official_document_bodies_persisted_in_repository": False,
    }
    expected_constraints = {
        "known_safe_alternate_mime_allowlist_remains_empty": True,
        "fixed_stratum_only": "single_authority_multivalue_record",
        "fixed_endpoint_path_only": "/src/contrib/PACKAGES",
        "candidate_may_require_strict_DCF_body_attestation": True,
        "candidate_may_not_accept_body_on_mime_or_magic_bytes_alone": True,
        "candidate_must_require_minimum_64_distinct_valid_records": True,
        "candidate_must_require_each_selected_record_has_Package_Version_License_and_SystemRequirements_or_Suggests": True,
        "duplicate_field_malformed_continuation_invalid_utf8_control_character_and_oversize_fail_closed": True,
        "unknown_or_disallowed_mime_remains_reported_not_silently_relabelled": True,
        "body_bytes_sha256_length_and_transport_receipt_binding_required": True,
        "redirect_retry_refetch_backfill_replacement_and_second_batch": 0,
    }
    if (
        set(copied) != expected_fields
        or copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25221_cran_repository_format_pre_effect_evidence"
        or not isinstance(copied.get("created_at_unix"), int)
        or isinstance(copied.get("created_at_unix"), bool)
        or parent_audit
        != {
            "path": str(PARENT_AUDIT),
            "sha256": EXPECTED_PARENT_AUDIT_SHA256,
        }
        or parent_audit.get("sha256")
        != EXPECTED_PARENT_AUDIT_SHA256
        or copied.get("official_documents") != OFFICIAL_DOCUMENTS
        or official
        != {
            "cran_style_terminal_repository_directory_must_contain_PACKAGES": True,
            "PACKAGES_may_be_concatenated_DESCRIPTION_records_separated_by_blank_lines": True,
            "PACKAGES_rds_and_PACKAGES_gz_are_optional_preferred_alternatives": True,
            "DESCRIPTION_uses_Debian_Control_File_style_records": True,
            "DCF_fields_begin_with_ASCII_name_colon_and_space": True,
            "DCF_continuation_lines_begin_with_space_or_tab": True,
            "repository_format_section_explicit_http_content_type_or_mime_contract_count": 0,
        }
        or limits != expected_limits
        or constraints != expected_constraints
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("official_documentation_https_network_called") is not True
        or copied.get("public_snapshot_endpoint_or_api_called")
        is not False
        or copied.get(
            "model_hosted_search_tavily_evaluator_or_benchmark_called"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization
        != {
            "strict_cran_dcf_body_attestation_implementation_build_only": True,
            "known_safe_alternate_mime_allowlist_change": False,
            "fresh_transport_observability_protocol_design": False,
            "public_snapshot_network_access_or_execution_start": False,
            "v25219_retry_refetch_backfill_replacement_or_second_batch": False,
            "real_identity_selection_or_population_freeze": False,
            "probe_runtime_integration_external_forward_or_activation": False,
            "runtime_compatibility_validator_relaxation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.21 CRAN repository evidence design drifted")
    return copied


def main() -> None:
    value = build_design()
    base.base.publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "implementation_build_only": value["authorization"][
                    "strict_cran_dcf_body_attestation_implementation_build_only"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
