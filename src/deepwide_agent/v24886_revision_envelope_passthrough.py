"""Truthful identity passthrough outside the V2.48.59 revision envelope.

V2.48.59 deliberately bounds active coverage revision to 512 rows.  A valid
parent table may be larger, however, and the old integration constructed an
identity coverage receipt unconditionally before checking eligibility.  That
turned an optional revision limit into a fatal parent-result limit.

This pure append-only successor keeps V2.48.59 byte semantics for eligible
tables.  For a structurally valid parent with more than 512 rows it permits
only an exact identity receipt: no proposal, no evidence, no support checks,
no row deletion, and no entropy/IG admission.  It never truncates the parent.
"""

from __future__ import annotations

import copy
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24859_full_evidence_coverage_revision as frozen


POLICY_ID = "v24886_revision_envelope_identity_passthrough_v1"
ROLE = "v24886_revision_envelope_identity_passthrough_receipt"
MAXIMUM_ACTIVE_REVISION_ROWS = frozen.MAXIMUM_ROWS
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "baseline_row_count",
        "proposed_row_count",
        "final_row_count",
        "table_column_count",
        "proposed_existing_cell_changes",
        "admitted_existing_unknown_fills",
        "admitted_existing_overrides",
        "proposed_new_rows",
        "admitted_new_rows",
        "rejected_partial_new_rows",
        "support_checks",
        "admitted_support_checks",
        "support_source_count_distribution",
        "admitted_support_source_count_distribution",
        "admitted_unknown_fill_support_source_count_distribution",
        "admitted_override_support_source_count_distribution",
        "admitted_new_row_support_source_count_distribution",
        "minimum_unknown_sources",
        "minimum_override_sources",
        "minimum_new_row_sources",
        "baseline_rows_deleted",
        "unsupported_changes_reverted_to_baseline",
        "candidate_identity_handoff",
        "shadow_information_gain_nats",
        "entropy_or_information_gain_used_for_admission",
        "source_thresholds_only_used_for_admission",
        "model_declared_evidence_membership_trusted",
        "question_query_url_host_page_candidate_value_evidence_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_payload_sha256",
    }
)


def _matrix_unbounded(table: str) -> tuple[list[str], list[list[str]]]:
    groups = frozen._markdown_groups(table)
    if len(groups) != 1:
        raise ValueError("V2.48.86 canonical table grouping drifted")
    rows = groups[0]
    if len(rows) < 3:
        raise ValueError("V2.48.86 canonical table has no data row")
    columns = rows[0]
    if not 1 <= len(columns) <= frozen.MAXIMUM_COLUMNS:
        raise ValueError("V2.48.86 canonical table width drifted")
    if any(len(row) != len(columns) for row in rows):
        raise ValueError("V2.48.86 canonical table row width drifted")
    if any(
        re.fullmatch(r":?-{3,}:?", value.replace(" ", "")) is None
        for value in rows[1]
    ):
        raise ValueError("V2.48.86 canonical table separator drifted")
    return list(columns), [list(row) for row in rows[2:]]


def revision_envelope_eligible(table: str) -> bool:
    _columns, rows = _matrix_unbounded(table)
    return len(rows) <= MAXIMUM_ACTIVE_REVISION_ROWS


def _reseal(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    copied["role"] = ROLE
    copied["policy_id"] = POLICY_ID
    copied.pop("receipt_payload_sha256", None)
    copied["receipt_payload_sha256"] = frozen.payload_sha256(copied)
    return copied


def _identity_receipt(*, rows: int, columns: int) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "baseline_row_count": rows,
        "proposed_row_count": 0,
        "final_row_count": rows,
        "table_column_count": columns,
        "proposed_existing_cell_changes": 0,
        "admitted_existing_unknown_fills": 0,
        "admitted_existing_overrides": 0,
        "proposed_new_rows": 0,
        "admitted_new_rows": 0,
        "rejected_partial_new_rows": 0,
        "support_checks": 0,
        "admitted_support_checks": 0,
        "support_source_count_distribution": {},
        "admitted_support_source_count_distribution": {},
        "admitted_unknown_fill_support_source_count_distribution": {},
        "admitted_override_support_source_count_distribution": {},
        "admitted_new_row_support_source_count_distribution": {},
        "minimum_unknown_sources": frozen.MINIMUM_UNKNOWN_SOURCES,
        "minimum_override_sources": frozen.MINIMUM_OVERRIDE_SOURCES,
        "minimum_new_row_sources": frozen.MINIMUM_NEW_ROW_SOURCES,
        "baseline_rows_deleted": 0,
        "unsupported_changes_reverted_to_baseline": True,
        "candidate_identity_handoff": True,
        "shadow_information_gain_nats": 0.0,
        "entropy_or_information_gain_used_for_admission": False,
        "source_thresholds_only_used_for_admission": True,
        "model_declared_evidence_membership_trusted": False,
        "question_query_url_host_page_candidate_value_evidence_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = frozen.payload_sha256(value)
    return validate_receipt(value)


def apply_full_evidence_revision(
    *,
    baseline: str,
    proposed: str,
    pages: Sequence[frozen.EvidencePage | Mapping[str, Any]],
) -> dict[str, Any]:
    columns, rows = _matrix_unbounded(baseline)
    if len(rows) <= MAXIMUM_ACTIVE_REVISION_ROWS:
        value = frozen.apply_full_evidence_revision(
            baseline=baseline, proposed=proposed, pages=pages
        )
        return {
            "candidate_table": value["candidate_table"],
            "receipt": validate_receipt(_reseal(value["receipt"])),
        }
    if str(proposed).strip() or len(pages) != 0:
        raise ValueError("V2.48.86 over-envelope table is identity-only")
    return {
        "candidate_table": baseline,
        "receipt": _identity_receipt(rows=len(rows), columns=len(columns)),
    }


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or seal != frozen.payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.86 receipt identity drifted")
    rows = copied.get("baseline_row_count")
    if isinstance(rows, bool) or not isinstance(rows, int) or rows < 1:
        raise ValueError("V2.48.86 baseline row count drifted")
    if rows <= MAXIMUM_ACTIVE_REVISION_ROWS:
        projected = copy.deepcopy(copied)
        projected["role"] = frozen.ROLE
        projected["policy_id"] = frozen.POLICY_ID
        projected.pop("receipt_payload_sha256", None)
        projected["receipt_payload_sha256"] = frozen.payload_sha256(projected)
        frozen.validate_receipt(projected)
        return copied
    zero_fields = (
        "proposed_row_count",
        "proposed_existing_cell_changes",
        "admitted_existing_unknown_fills",
        "admitted_existing_overrides",
        "proposed_new_rows",
        "admitted_new_rows",
        "rejected_partial_new_rows",
        "support_checks",
        "admitted_support_checks",
        "baseline_rows_deleted",
    )
    distributions = (
        "support_source_count_distribution",
        "admitted_support_source_count_distribution",
        "admitted_unknown_fill_support_source_count_distribution",
        "admitted_override_support_source_count_distribution",
        "admitted_new_row_support_source_count_distribution",
    )
    integer_fields = (
        "artifact_version",
        "baseline_row_count",
        "proposed_row_count",
        "final_row_count",
        "table_column_count",
        "proposed_existing_cell_changes",
        "admitted_existing_unknown_fills",
        "admitted_existing_overrides",
        "proposed_new_rows",
        "admitted_new_rows",
        "rejected_partial_new_rows",
        "support_checks",
        "admitted_support_checks",
        "minimum_unknown_sources",
        "minimum_override_sources",
        "minimum_new_row_sources",
        "baseline_rows_deleted",
    )
    boolean_fields = (
        "unsupported_changes_reverted_to_baseline",
        "candidate_identity_handoff",
        "entropy_or_information_gain_used_for_admission",
        "source_thresholds_only_used_for_admission",
        "model_declared_evidence_membership_trusted",
        "question_query_url_host_page_candidate_value_evidence_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    gain = copied.get("shadow_information_gain_nats")
    if (
        any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integer_fields
        )
        or any(not isinstance(copied.get(name), bool) for name in boolean_fields)
        or isinstance(gain, bool)
        or not isinstance(gain, (int, float))
        or not math.isfinite(float(gain))
        or any(not isinstance(copied.get(name), Mapping) for name in distributions)
        or
        copied.get("final_row_count") != rows
        or not 1 <= copied.get("table_column_count", 0) <= frozen.MAXIMUM_COLUMNS
        or any(copied.get(name) != 0 for name in zero_fields)
        or any(copied.get(name) != {} for name in distributions)
        or copied.get("minimum_unknown_sources") != frozen.MINIMUM_UNKNOWN_SOURCES
        or copied.get("minimum_override_sources") != frozen.MINIMUM_OVERRIDE_SOURCES
        or copied.get("minimum_new_row_sources") != frozen.MINIMUM_NEW_ROW_SOURCES
        or copied.get("unsupported_changes_reverted_to_baseline") is not True
        or copied.get("candidate_identity_handoff") is not True
        or float(gain) != 0.0
        or copied.get("entropy_or_information_gain_used_for_admission") is not False
        or copied.get("source_thresholds_only_used_for_admission") is not True
        or copied.get("model_declared_evidence_membership_trusted") is not False
        or copied.get(
            "question_query_url_host_page_candidate_value_evidence_id_or_credential_emitted"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get("file_environment_network_model_search_fetch_or_process_accessed")
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
    ):
        raise ValueError("V2.48.86 identity passthrough drifted")
    return copied


__all__ = [
    "MAXIMUM_ACTIVE_REVISION_ROWS",
    "POLICY_ID",
    "ROLE",
    "apply_full_evidence_revision",
    "revision_envelope_eligible",
    "validate_receipt",
]
