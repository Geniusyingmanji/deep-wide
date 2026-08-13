"""Monotone same-forward Unknown-cell fill for a bounded third model slot.

The model proposes one complete table with the baseline schema and row order.
This pure kernel can only replace a baseline Unknown cell with a value that is
mechanically bound to the same row and column on at least one fetched page.
Any known-cell edit or row/schema/order change rejects the whole proposal.
Any mechanically visible conflicting value rejects that cell.  All failures
return the baseline byte-for-byte.

Entropy reduction is a content-free shadow measurement after admission.  It
does not route, admit, sign, or weight credit.  This module has no filesystem,
environment, process, network, model, evaluator, benchmark, or credential
capability.
"""

from __future__ import annotations

import copy
import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24859_full_evidence_coverage_revision as parent


POLICY_ID = "v25289_monotone_same_forward_unknown_fill_v1"
ROLE = "v25289_content_free_monotone_unknown_fill_receipt"
MINIMUM_SUPPORTING_PAGES = 1
MAXIMUM_CONFLICTING_BOUND_VALUES = 0
MAXIMUM_BOUND_VALUE_CHARS = 160


def _distribution(values: Sequence[int]) -> dict[str, int]:
    counts = Counter(int(value) for value in values)
    return {str(key): counts[key] for key in sorted(counts)}


def _bound_value_key(value: object) -> str:
    text = str(value or "").strip().strip("`*_\"'[](){}")
    text = re.sub(r"[\s\u00a0]+", " ", text)
    text = text.rstrip(".,;:!?，。；：！？").strip()
    return parent._identity_key(text)


def _table_bound_values(
    content: str, row_key: str, column: str
) -> set[str]:
    target_row = parent._identity_key(row_key)
    target_column = parent._identity_key(column)
    output: set[str] = set()
    if not target_row or not target_column:
        return output
    for group in parent._markdown_groups(content):
        if len(group) < 3:
            continue
        for header_index in range(len(group) - 2):
            header = group[header_index]
            separator = group[header_index + 1]
            if (
                len(separator) != len(header)
                or not parent._separator_row(separator)
            ):
                continue
            matching = [
                index
                for index, value in enumerate(header)
                if parent._identity_key(value) == target_column
            ]
            for row in group[header_index + 2 :]:
                if (
                    len(row) != len(header)
                    or parent._separator_row(row)
                    or not row
                    or parent._identity_key(row[0]) != target_row
                ):
                    continue
                for index in matching:
                    value = _bound_value_key(row[index])
                    if value and not parent._is_unknown(value):
                        output.add(value)
    return output


def _prose_bound_values(
    content: str, row_key: str, column: str
) -> set[str]:
    output: set[str] = set()
    column_pattern = parent._term_pattern(column)
    if column_pattern is None:
        return output
    for record in parent._logical_records(content):
        if not parent._term_matches(record, row_key):
            continue
        for match in column_pattern.finditer(record):
            suffix = record[match.end() : match.end() + MAXIMUM_BOUND_VALUE_CHARS]
            prefix = re.match(r"\s*(?::|=|\bis\b|\bwas\b)\s*", suffix)
            if prefix is None:
                continue
            tail = suffix[prefix.end() :]
            boundary = re.search(r";|\||<|\.\s+[^.]{1,64}?:", tail)
            raw = tail[: boundary.start()] if boundary is not None else tail
            raw = raw[:MAXIMUM_BOUND_VALUE_CHARS]
            value = _bound_value_key(raw)
            if value and not parent._is_unknown(value):
                output.add(value)
    return output


def _bound_values(
    page: parent.EvidencePage, row_key: str, column: str
) -> set[str]:
    if not page.fetch_integrity:
        return set()
    return _table_bound_values(
        page.content, row_key, column
    ) | _prose_bound_values(page.content, row_key, column)


def _support_and_conflict(
    pages: Sequence[parent.EvidencePage],
    *,
    row_key: str,
    column: str,
    value: str,
) -> tuple[int, int]:
    target = _bound_value_key(value)
    supporting_pages = 0
    conflicting_values: set[str] = set()
    for page in pages:
        if parent._supports_cell(page, row_key, column, value):
            supporting_pages += 1
        for observed in _bound_values(page, row_key, column):
            if observed != target:
                conflicting_values.add(observed)
    return supporting_pages, len(conflicting_values)


def _shadow_information_gain(supporting_pages: int) -> float:
    if supporting_pages <= 0:
        return 0.0
    prior = 0.5
    likelihood_ratio = 4.0 ** min(int(supporting_pages), 8)
    posterior = likelihood_ratio / (1.0 + likelihood_ratio)

    def entropy(probability: float) -> float:
        if probability <= 0.0 or probability >= 1.0:
            return 0.0
        return -probability * math.log(probability) - (
            1.0 - probability
        ) * math.log(1.0 - probability)

    return round(max(0.0, entropy(prior) - entropy(posterior)), 12)


def _receipt(
    *,
    baseline_rows: int,
    columns: int,
    same_forward_pages: int,
    baseline_unknown_cells: int,
    proposal_parse_valid: bool,
    proposal_structure_exact: bool,
    forbidden_known_changes: int,
    proposed_fills: int,
    admitted_fills: int,
    unsupported_fills: int,
    conflicting_fills: int,
    whole_proposal_rejected_fills: int,
    support_counts: Sequence[int],
    conflict_counts: Sequence[int],
    admitted_support_counts: Sequence[int],
    shadow_information_gain_nats: float,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "baseline_row_count": int(baseline_rows),
        "final_row_count": int(baseline_rows),
        "table_column_count": int(columns),
        "same_forward_page_count": int(same_forward_pages),
        "baseline_unknown_cell_count": int(baseline_unknown_cells),
        "proposal_parse_valid": bool(proposal_parse_valid),
        "proposal_structure_exact": bool(proposal_structure_exact),
        "forbidden_known_cell_change_count": int(forbidden_known_changes),
        "proposed_unknown_fill_count": int(proposed_fills),
        "admitted_unknown_fill_count": int(admitted_fills),
        "rejected_unsupported_fill_count": int(unsupported_fills),
        "rejected_conflicting_fill_count": int(conflicting_fills),
        "rejected_by_whole_proposal_count": int(
            whole_proposal_rejected_fills
        ),
        "support_check_count": len(support_counts),
        "supporting_page_count_distribution": _distribution(support_counts),
        "conflicting_bound_value_count_distribution": _distribution(
            conflict_counts
        ),
        "admitted_supporting_page_count_distribution": _distribution(
            admitted_support_counts
        ),
        "minimum_supporting_pages": MINIMUM_SUPPORTING_PAGES,
        "maximum_conflicting_bound_values": MAXIMUM_CONFLICTING_BOUND_VALUES,
        "prediction_changed": admitted_fills > 0,
        "candidate_identity_handoff": admitted_fills == 0,
        "baseline_known_cells_preserved": True,
        "baseline_row_keys_order_count_and_schema_preserved": True,
        "whole_proposal_rejected_on_known_cell_or_structure_change": True,
        "same_forward_row_column_value_binding_only": True,
        "model_declared_citation_or_evidence_membership_trusted": False,
        "shadow_information_gain_nats": round(
            float(shadow_information_gain_nats), 12
        ),
        "entropy_or_information_gain_used_for_admission_or_credit_sign": False,
        "question_query_url_host_page_candidate_value_evidence_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_external_forward_authorized": False,
    }
    value["receipt_payload_sha256"] = parent.payload_sha256(value)
    return validate_receipt(value)


def _identity_result(
    *,
    baseline: str,
    baseline_rows: int,
    columns: int,
    same_forward_pages: int,
    baseline_unknown_cells: int,
    proposal_parse_valid: bool,
    proposal_structure_exact: bool,
    forbidden_known_changes: int = 0,
    proposed_fills: int = 0,
    whole_proposal_rejected_fills: int = 0,
) -> dict[str, Any]:
    return {
        "candidate_table": baseline,
        "receipt": _receipt(
            baseline_rows=baseline_rows,
            columns=columns,
            same_forward_pages=same_forward_pages,
            baseline_unknown_cells=baseline_unknown_cells,
            proposal_parse_valid=proposal_parse_valid,
            proposal_structure_exact=proposal_structure_exact,
            forbidden_known_changes=forbidden_known_changes,
            proposed_fills=proposed_fills,
            admitted_fills=0,
            unsupported_fills=0,
            conflicting_fills=0,
            whole_proposal_rejected_fills=whole_proposal_rejected_fills,
            support_counts=(),
            conflict_counts=(),
            admitted_support_counts=(),
            shadow_information_gain_nats=0.0,
        ),
    }


def apply_monotone_unknown_fill(
    *,
    baseline: str,
    proposed: str,
    pages: Sequence[parent.EvidencePage | Mapping[str, Any]],
) -> dict[str, Any]:
    """Return a monotone fill candidate or the exact baseline on any rejection."""

    columns, baseline_rows = parent._matrix(baseline)
    baseline_unknown = sum(
        parent._is_unknown(row[index])
        for row in baseline_rows
        for index in range(1, len(columns))
    )
    canonical = parent._canonical_candidate(proposed, columns)
    evidence = parent.prepare_evidence_pages(pages)
    if canonical is None:
        return _identity_result(
            baseline=baseline,
            baseline_rows=len(baseline_rows),
            columns=len(columns),
            same_forward_pages=len(evidence),
            baseline_unknown_cells=baseline_unknown,
            proposal_parse_valid=False,
            proposal_structure_exact=False,
        )
    candidate_columns, candidate_rows = parent._matrix(canonical)
    baseline_keys = [parent._identity_key(row[0]) for row in baseline_rows]
    candidate_keys = [parent._identity_key(row[0]) for row in candidate_rows]
    structure_exact = bool(
        [parent._identity_key(value) for value in candidate_columns]
        == [parent._identity_key(value) for value in columns]
        and len(candidate_rows) == len(baseline_rows)
        and candidate_keys == baseline_keys
        and all(baseline_keys)
        and len(set(baseline_keys)) == len(baseline_keys)
    )
    if not structure_exact:
        return _identity_result(
            baseline=baseline,
            baseline_rows=len(baseline_rows),
            columns=len(columns),
            same_forward_pages=len(evidence),
            baseline_unknown_cells=baseline_unknown,
            proposal_parse_valid=True,
            proposal_structure_exact=False,
        )

    forbidden = 0
    proposed_fills = 0
    for old_row, new_row in zip(baseline_rows, candidate_rows, strict=True):
        if parent._identity_key(old_row[0]) != parent._identity_key(new_row[0]):
            forbidden += 1
        for index in range(1, len(columns)):
            old = old_row[index]
            new = new_row[index]
            if parent._identity_key(old) == parent._identity_key(new):
                continue
            if parent._is_unknown(old) and not parent._is_unknown(new):
                proposed_fills += 1
            elif parent._is_unknown(old) and parent._is_unknown(new):
                continue
            else:
                forbidden += 1
    if forbidden:
        return _identity_result(
            baseline=baseline,
            baseline_rows=len(baseline_rows),
            columns=len(columns),
            same_forward_pages=len(evidence),
            baseline_unknown_cells=baseline_unknown,
            proposal_parse_valid=True,
            proposal_structure_exact=True,
            forbidden_known_changes=forbidden,
            proposed_fills=proposed_fills,
            whole_proposal_rejected_fills=proposed_fills,
        )

    output = [list(row) for row in baseline_rows]
    support_counts: list[int] = []
    conflict_counts: list[int] = []
    admitted_support_counts: list[int] = []
    admitted = unsupported = conflicting = 0
    shadow_gain = 0.0
    for row_index, (old_row, new_row) in enumerate(
        zip(baseline_rows, candidate_rows, strict=True)
    ):
        for column_index in range(1, len(columns)):
            old = old_row[column_index]
            new = new_row[column_index]
            if (
                parent._identity_key(old) == parent._identity_key(new)
                or parent._is_unknown(new)
            ):
                continue
            support, conflict = _support_and_conflict(
                evidence,
                row_key=old_row[0],
                column=columns[column_index],
                value=new,
            )
            support_counts.append(support)
            conflict_counts.append(conflict)
            if conflict > MAXIMUM_CONFLICTING_BOUND_VALUES:
                conflicting += 1
                continue
            if support < MINIMUM_SUPPORTING_PAGES:
                unsupported += 1
                continue
            output[row_index][column_index] = new
            admitted += 1
            admitted_support_counts.append(support)
            shadow_gain += _shadow_information_gain(support)

    candidate = parent._render(columns, output)
    canonical_output, errors = parent._extract_valid_markdown_table(
        candidate, columns
    )
    if canonical_output != candidate or errors:
        raise RuntimeError("V2.52.89 monotone candidate is not canonical")
    receipt = _receipt(
        baseline_rows=len(baseline_rows),
        columns=len(columns),
        same_forward_pages=len(evidence),
        baseline_unknown_cells=baseline_unknown,
        proposal_parse_valid=True,
        proposal_structure_exact=True,
        forbidden_known_changes=0,
        proposed_fills=proposed_fills,
        admitted_fills=admitted,
        unsupported_fills=unsupported,
        conflicting_fills=conflicting,
        whole_proposal_rejected_fills=0,
        support_counts=support_counts,
        conflict_counts=conflict_counts,
        admitted_support_counts=admitted_support_counts,
        shadow_information_gain_nats=shadow_gain,
    )
    return {"candidate_table": candidate, "receipt": receipt}


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("receipt_payload_sha256", None)
    integer_fields = (
        "baseline_row_count",
        "final_row_count",
        "table_column_count",
        "same_forward_page_count",
        "baseline_unknown_cell_count",
        "forbidden_known_cell_change_count",
        "proposed_unknown_fill_count",
        "admitted_unknown_fill_count",
        "rejected_unsupported_fill_count",
        "rejected_conflicting_fill_count",
        "rejected_by_whole_proposal_count",
        "support_check_count",
        "minimum_supporting_pages",
        "maximum_conflicting_bound_values",
    )
    boolean_fields = (
        "proposal_parse_valid",
        "proposal_structure_exact",
        "prediction_changed",
        "candidate_identity_handoff",
        "baseline_known_cells_preserved",
        "baseline_row_keys_order_count_and_schema_preserved",
        "whole_proposal_rejected_on_known_cell_or_structure_change",
        "same_forward_row_column_value_binding_only",
        "model_declared_citation_or_evidence_membership_trusted",
        "entropy_or_information_gain_used_for_admission_or_credit_sign",
        "question_query_url_host_page_candidate_value_evidence_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_external_forward_authorized",
    )
    distribution_fields = (
        "supporting_page_count_distribution",
        "conflicting_bound_value_count_distribution",
        "admitted_supporting_page_count_distribution",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *integer_fields,
        *boolean_fields,
        *distribution_fields,
        "shadow_information_gain_nats",
        "receipt_payload_sha256",
    }
    distributions: dict[str, dict[int, int]] = {}
    valid_distributions = True
    for name in distribution_fields:
        raw = copied.get(name)
        parsed: dict[int, int] = {}
        if not isinstance(raw, Mapping):
            valid_distributions = False
            continue
        for key, count in raw.items():
            if not isinstance(key, str):
                valid_distributions = False
                break
            try:
                number = int(key)
            except (TypeError, ValueError):
                valid_distributions = False
                break
            if (
                isinstance(count, bool)
                or not isinstance(count, int)
                or count <= 0
                or str(number) != str(key)
                or number < 0
                or number in parsed
            ):
                valid_distributions = False
                break
            parsed[number] = count
        distributions[name] = parsed
    proposed = copied.get("proposed_unknown_fill_count", -1)
    admitted = copied.get("admitted_unknown_fill_count", -1)
    unsupported = copied.get("rejected_unsupported_fill_count", -1)
    conflicting = copied.get("rejected_conflicting_fill_count", -1)
    whole = copied.get("rejected_by_whole_proposal_count", -1)
    checked = copied.get("support_check_count", -1)
    support_total = sum(
        distributions.get("supporting_page_count_distribution", {}).values()
    )
    conflict_total = sum(
        distributions.get(
            "conflicting_bound_value_count_distribution", {}
        ).values()
    )
    admitted_total = sum(
        distributions.get(
            "admitted_supporting_page_count_distribution", {}
        ).values()
    )
    admitted_dist = distributions.get(
        "admitted_supporting_page_count_distribution", {}
    )
    conflict_dist = distributions.get(
        "conflicting_bound_value_count_distribution", {}
    )
    expected_shadow = round(
        sum(
            count * _shadow_information_gain(support)
            for support, count in admitted_dist.items()
        ),
        12,
    )
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integer_fields
        )
        or any(not isinstance(copied.get(name), bool) for name in boolean_fields)
        or not valid_distributions
        or copied.get("baseline_row_count") <= 0
        or copied.get("final_row_count") != copied.get("baseline_row_count")
        or copied.get("table_column_count") <= 1
        or copied.get("same_forward_page_count") > parent.MAXIMUM_PAGES
        or copied.get("baseline_unknown_cell_count")
        > copied.get("baseline_row_count")
        * (copied.get("table_column_count") - 1)
        or proposed > copied.get("baseline_unknown_cell_count")
        or copied.get("forbidden_known_cell_change_count")
        > copied.get("baseline_row_count")
        * (copied.get("table_column_count") - 1)
        - copied.get("baseline_unknown_cell_count")
        or copied.get("minimum_supporting_pages") != MINIMUM_SUPPORTING_PAGES
        or copied.get("maximum_conflicting_bound_values")
        != MAXIMUM_CONFLICTING_BOUND_VALUES
        or proposed < admitted + unsupported + conflicting + whole
        or copied.get("proposal_parse_valid") is False
        and any(
            (
                copied.get("proposal_structure_exact"),
                copied.get("forbidden_known_cell_change_count"),
                proposed,
                admitted,
                unsupported,
                conflicting,
                whole,
                checked,
            )
        )
        or copied.get("proposal_structure_exact") is False
        and any(
            (
                copied.get("forbidden_known_cell_change_count"),
                proposed,
                admitted,
                unsupported,
                conflicting,
                whole,
                checked,
            )
        )
        or copied.get("forbidden_known_cell_change_count", 0) > 0
        and (whole != proposed or any((admitted, unsupported, conflicting, checked)))
        or copied.get("forbidden_known_cell_change_count", 0) == 0
        and copied.get("proposal_structure_exact") is True
        and whole != 0
        or copied.get("proposal_structure_exact") is True
        and copied.get("forbidden_known_cell_change_count", 0) == 0
        and proposed != admitted + unsupported + conflicting
        or checked != admitted + unsupported + conflicting
        or support_total != checked
        or conflict_total != checked
        or admitted_total != admitted
        or any(
            support < MINIMUM_SUPPORTING_PAGES
            for support in admitted_dist
        )
        or any(
            support > copied.get("same_forward_page_count")
            for support in distributions.get(
                "supporting_page_count_distribution", {}
            )
        )
        or sum(
            count
            for conflict, count in conflict_dist.items()
            if conflict > MAXIMUM_CONFLICTING_BOUND_VALUES
        )
        != conflicting
        or copied.get("prediction_changed") is not (admitted > 0)
        or copied.get("candidate_identity_handoff") is not (admitted == 0)
        or any(
            copied.get(name) is not True
            for name in (
                "baseline_known_cells_preserved",
                "baseline_row_keys_order_count_and_schema_preserved",
                "whole_proposal_rejected_on_known_cell_or_structure_change",
                "same_forward_row_column_value_binding_only",
            )
        )
        or any(
            copied.get(name) is not False
            for name in (
                "model_declared_citation_or_evidence_membership_trusted",
                "entropy_or_information_gain_used_for_admission_or_credit_sign",
                "question_query_url_host_page_candidate_value_evidence_id_or_credential_emitted",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
                "benchmark_launch_or_external_forward_authorized",
            )
        )
        or isinstance(copied.get("shadow_information_gain_nats"), bool)
        or not isinstance(
            copied.get("shadow_information_gain_nats"), (int, float)
        )
        or not math.isfinite(float(copied["shadow_information_gain_nats"]))
        or float(copied["shadow_information_gain_nats"]) != expected_shadow
        or signature != parent.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.89 monotone Unknown-fill receipt drifted")
    return copied


__all__ = [
    "MAXIMUM_CONFLICTING_BOUND_VALUES",
    "MINIMUM_SUPPORTING_PAGES",
    "POLICY_ID",
    "ROLE",
    "apply_monotone_unknown_fill",
    "validate_receipt",
]
