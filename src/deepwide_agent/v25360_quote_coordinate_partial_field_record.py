"""Per-field disposition within one verified page/quote/row coordinate.

V2.53.59 showed that eleven proposals passed page reference, unique verbatim
quote, and row-identity binding but were rejected atomically because at least
one of four fields failed.  This append-only pure successor preserves those
record-coordinate checks and evaluates fields independently.  A record is
rendered when at least one field has an exact requested column, a uniquely
bound verbatim source label, and a non-unknown verbatim value in the same
quote.  Invalid fields are omitted.  Conflicting values for the same target
at the same coordinate reject the whole coordinate; exact duplicates collapse.

The component has no file, environment, process, network, model, search,
fetch, evaluator, benchmark-label, mapping, gold, score, reward, credential,
or historical-result capability.  Entropy/information gain assigns no signed
credit and no budget is expanded.
"""

from __future__ import annotations

import copy
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from . import v25065_quote_verified_record_binding as parent


POLICY_ID = "v25360_quote_coordinate_partial_field_record_v1"
ROLE = "v25360_quote_coordinate_partial_field_record_representation"
RECEIPT_ROLE = "v25360_content_free_quote_coordinate_partial_field_receipt"

MAXIMUM_PAGE_COUNT = parent.MAXIMUM_PAGE_COUNT
MAXIMUM_PAGE_CHARACTERS = parent.MAXIMUM_PAGE_CHARACTERS
MAXIMUM_PROPOSAL_INPUT_CHARACTERS = parent.MAXIMUM_PROPOSAL_INPUT_CHARACTERS
PROPOSAL_OUTPUT_TOKEN_CAP = parent.PROPOSAL_OUTPUT_TOKEN_CAP
MAXIMUM_PROPOSED_RECORDS = parent.MAXIMUM_PROPOSED_RECORDS
MAXIMUM_FIELDS_PER_RECORD = parent.MAXIMUM_FIELDS_PER_RECORD
MAXIMUM_TOTAL_FIELDS = parent.MAXIMUM_TOTAL_FIELDS
MAXIMUM_RECORD_PREFIX_CHARACTERS = parent.MAXIMUM_RECORD_PREFIX_CHARACTERS
MAXIMUM_CONTROL_EVIDENCE_CHARACTERS = parent.MAXIMUM_CONTROL_EVIDENCE_CHARACTERS
SYSTEM_PROMPT = parent.SYSTEM_PROMPT
payload_sha256 = parent.payload_sha256


def prepare_record_proposal(
    question: str,
    columns: Sequence[str],
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    prepared = parent.prepare_record_proposal(question, columns, pages)
    prepared["role"] = "v25360_private_quote_coordinate_partial_field_state"
    return prepared


def _field_dispositions(
    prepared: Mapping[str, Any], proposals: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    columns = prepared.get("columns")
    pages = prepared.get("pages")
    if not isinstance(columns, tuple) or not isinstance(pages, tuple):
        raise ValueError("V2.53.60 prepared state drifted")
    targets = {parent._key(value): str(value) for value in columns[1:]}
    by_ordinal = {int(page["page_ordinal"]): page for page in pages}
    counts: defaultdict[str, int] = defaultdict(int)
    candidates: list[dict[str, Any]] = []
    for position, raw in enumerate(proposals):
        page = by_ordinal.get(int(raw["page_ordinal"]))
        fields = list(raw["fields"])
        if page is None:
            counts["rejected_page_reference_record_count"] += 1
            counts["field_page_reference_rejection_count"] += len(fields)
            continue
        content = str(page["content"])
        quote = str(raw["quote"])
        identity = str(raw["row_identity"])
        if content.count(quote) != 1:
            counts["rejected_nonunique_or_nonverbatim_quote_record_count"] += 1
            counts["field_quote_coordinate_rejection_count"] += len(fields)
            continue
        if not parent._contains_phrase(quote, identity) or parent._unknown(identity):
            counts["rejected_row_identity_record_count"] += 1
            counts["field_row_identity_rejection_count"] += len(fields)
            continue
        accepted: list[dict[str, str]] = []
        for field in fields:
            column_key = parent._key(field["column"])
            source = str(field["source_field"])
            value = str(field["value"])
            matching = [
                key
                for key, target in targets.items()
                if parent._label_bound(target, source)
            ]
            if parent._unknown(value):
                counts["field_unknown_rejection_count"] += 1
                continue
            if (
                column_key not in targets
                or matching != [column_key]
                or not parent._contains_phrase(quote, source)
                or not parent._contains_phrase(quote, value)
            ):
                counts["field_label_or_value_binding_rejection_count"] += 1
                continue
            accepted.append(
                {
                    "column_key": column_key,
                    "column": targets[column_key],
                    "source_field": source,
                    "value": value,
                }
            )
        candidates.append(
            {
                "position": position,
                "page_ordinal": int(raw["page_ordinal"]),
                "quote": quote,
                "row_identity": identity,
                "fields": accepted,
            }
        )

    groups: dict[tuple[int, str, str], list[dict[str, Any]]] = defaultdict(list)
    order: list[tuple[int, str, str]] = []
    for item in candidates:
        key = (
            int(item["page_ordinal"]),
            parent._key(item["quote"]),
            parent._key(item["row_identity"]),
        )
        if key not in groups:
            order.append(key)
        groups[key].append(item)

    verified: list[dict[str, Any]] = []
    for key in order:
        group = groups[key]
        values: dict[str, set[str]] = defaultdict(set)
        representative: dict[str, dict[str, str]] = {}
        exact_duplicates = 0
        for item in group:
            for field in item["fields"]:
                column_key = field["column_key"]
                signature = parent._key(field["value"])
                if signature in values[column_key]:
                    exact_duplicates += 1
                values[column_key].add(signature)
                representative.setdefault(column_key, field)
        if any(len(signatures) > 1 for signatures in values.values()):
            counts["record_conflict_count"] += 1
            counts["field_conflict_rejection_count"] += sum(
                len(item["fields"]) for item in group
            )
            continue
        counts["field_exact_duplicate_rejection_count"] += exact_duplicates
        if not representative:
            counts["record_zero_accepted_field_count"] += 1
            continue
        first = min(group, key=lambda item: int(item["position"]))
        fields = [representative[name] for name in sorted(representative)]
        counts["field_accepted_count"] += len(fields)
        verified.append(
            {
                "page_ordinal": first["page_ordinal"],
                "quote": first["quote"],
                "row_identity": first["row_identity"],
                "fields": [
                    {
                        "column": field["column"],
                        "source_field": field["source_field"],
                        "value": field["value"],
                    }
                    for field in fields
                ],
            }
        )
    return verified, dict(counts)


_INTEGER_FIELDS = (
    "input_page_count",
    "bounded_page_count",
    "bounded_page_characters",
    "parsed_record_count",
    "parsed_field_count",
    "field_accepted_count",
    "field_unknown_rejection_count",
    "field_label_or_value_binding_rejection_count",
    "field_quote_coordinate_rejection_count",
    "field_row_identity_rejection_count",
    "field_page_reference_rejection_count",
    "field_exact_duplicate_rejection_count",
    "field_conflict_rejection_count",
    "record_conflict_count",
    "record_zero_accepted_field_count",
    "rejected_page_reference_record_count",
    "rejected_nonunique_or_nonverbatim_quote_record_count",
    "rejected_row_identity_record_count",
    "verified_partial_record_count",
    "verified_field_count",
    "rendered_record_count",
    "rendered_field_count",
    "compact_prefix_characters",
    "control_evidence_characters",
    "candidate_evidence_characters",
    "proposal_input_character_cap",
    "proposal_output_token_cap",
    "record_prefix_character_cap",
)
_TRUE_FLAGS = (
    "same_forward_fetched_pages_only",
    "one_canonical_contiguous_quote_from_exactly_one_page_required",
    "row_identity_source_field_and_value_remain_bound_to_same_quote_coordinate",
    "each_proposed_field_receives_exactly_one_content_free_disposition",
    "unknown_unbound_or_ambiguous_fields_are_omitted",
    "at_least_one_independently_verified_field_required_to_render",
    "conflicting_values_for_one_target_at_same_coordinate_reject_entire_record",
    "exact_duplicate_fields_collapsed_deterministically",
    "repeated_row_identity_at_distinct_quote_coordinates_preserved",
    "candidate_and_control_evidence_character_counts_equal",
    "record_blocks_rendered_atomically_without_partial_block",
    "query_fetch_model_context_token_wall_and_network_byte_caps_unchanged",
    "page_text_treated_as_untrusted_data",
)
_FALSE_FLAGS = (
    "rejected_or_unknown_field_assigns_positive_credit",
    "model_proposal_or_entropy_drop_assigns_signed_credit",
    "entropy_or_information_gain_assigns_signed_credit",
    "contains_question_query_url_title_page_quote_identity_field_value_prediction_answer_hash_opaque_id_or_credential",
    "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
    "file_environment_process_network_model_search_fetch_or_evaluator_accessed",
    "benchmark_launch_or_evaluator_authorized",
)


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(value.get(name, 0)) for name in _INTEGER_FIELDS},
        "model_call_attempted": bool(value["model_call_attempted"]),
        "model_output_strictly_valid": bool(value["model_output_strictly_valid"]),
        "candidate_evidence_changed": bool(value["candidate_evidence_changed"]),
        **{name: True for name in _TRUE_FLAGS},
        **{name: False for name in _FALSE_FLAGS},
    }
    output["receipt_payload_sha256"] = payload_sha256(output)
    return validate_receipt(output)


def build_representation(
    prepared: Mapping[str, Any],
    model_output: object,
    *,
    control_evidence: str,
    model_call_attempted: bool,
) -> dict[str, Any]:
    control = str(control_evidence)
    if (
        not control
        or "\x00" in control
        or len(control) > MAXIMUM_CONTROL_EVIDENCE_CHARACTERS
        or prepared.get("role")
        != "v25360_private_quote_coordinate_partial_field_state"
        or prepared.get("artifact_version") != 1
    ):
        raise ValueError("V2.53.60 representation input drifted")
    proposals = parent._parse_proposals(model_output) if model_call_attempted else None
    verified: list[dict[str, Any]] = []
    disposition: dict[str, int] = {}
    if proposals is not None:
        verified, disposition = _field_dispositions(prepared, proposals)
    candidate, rendered_records, rendered_fields, prefix_chars, changed = (
        parent._render_candidate(verified, control)
    )
    receipt = _receipt(
        {
            "input_page_count": prepared["input_page_count"],
            "bounded_page_count": prepared["bounded_page_count"],
            "bounded_page_characters": prepared["bounded_page_characters"],
            "parsed_record_count": len(proposals or []),
            "parsed_field_count": sum(
                len(record["fields"]) for record in (proposals or [])
            ),
            **disposition,
            "verified_partial_record_count": len(verified),
            "verified_field_count": sum(len(record["fields"]) for record in verified),
            "rendered_record_count": rendered_records,
            "rendered_field_count": rendered_fields,
            "compact_prefix_characters": prefix_chars,
            "control_evidence_characters": len(control),
            "candidate_evidence_characters": len(candidate),
            "proposal_input_character_cap": MAXIMUM_PROPOSAL_INPUT_CHARACTERS,
            "proposal_output_token_cap": PROPOSAL_OUTPUT_TOKEN_CAP,
            "record_prefix_character_cap": MAXIMUM_RECORD_PREFIX_CHARACTERS,
            "model_call_attempted": model_call_attempted,
            "model_output_strictly_valid": proposals is not None,
            "candidate_evidence_changed": bool(changed),
        }
    )
    return {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "candidate_evidence": candidate,
        "content_free_receipt": receipt,
    }


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *_INTEGER_FIELDS,
        "model_call_attempted",
        "model_output_strictly_valid",
        "candidate_evidence_changed",
        *_TRUE_FLAGS,
        *_FALSE_FLAGS,
        "receipt_payload_sha256",
    }
    disposition_total = sum(
        copied.get(name, 0)
        for name in (
            "field_accepted_count",
            "field_unknown_rejection_count",
            "field_label_or_value_binding_rejection_count",
            "field_quote_coordinate_rejection_count",
            "field_row_identity_rejection_count",
            "field_page_reference_rejection_count",
            "field_exact_duplicate_rejection_count",
            "field_conflict_rejection_count",
        )
    )
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
        or any(
            not isinstance(copied.get(name), bool)
            for name in (
                "model_call_attempted",
                "model_output_strictly_valid",
                "candidate_evidence_changed",
            )
        )
        or copied["bounded_page_count"]
        > min(copied["input_page_count"], MAXIMUM_PAGE_COUNT)
        or copied["bounded_page_characters"] > MAXIMUM_PROPOSAL_INPUT_CHARACTERS
        or copied["parsed_record_count"] > MAXIMUM_PROPOSED_RECORDS
        or copied["parsed_field_count"] > MAXIMUM_TOTAL_FIELDS
        or disposition_total != copied["parsed_field_count"]
        or copied["record_conflict_count"] > copied["parsed_record_count"]
        or copied["record_zero_accepted_field_count"] > copied["parsed_record_count"]
        or copied["verified_partial_record_count"] > copied["parsed_record_count"]
        or copied["verified_field_count"] != copied["field_accepted_count"]
        or copied["rendered_record_count"] > copied["verified_partial_record_count"]
        or copied["rendered_field_count"] > copied["verified_field_count"]
        or copied["candidate_evidence_changed"]
        is not (copied["rendered_record_count"] > 0)
        or copied["compact_prefix_characters"] > MAXIMUM_RECORD_PREFIX_CHARACTERS
        or copied["control_evidence_characters"]
        != copied["candidate_evidence_characters"]
        or copied["control_evidence_characters"]
        > MAXIMUM_CONTROL_EVIDENCE_CHARACTERS
        or copied["proposal_input_character_cap"]
        != MAXIMUM_PROPOSAL_INPUT_CHARACTERS
        or copied["proposal_output_token_cap"] != PROPOSAL_OUTPUT_TOKEN_CAP
        or copied["record_prefix_character_cap"]
        != MAXIMUM_RECORD_PREFIX_CHARACTERS
        or copied["model_output_strictly_valid"]
        and not copied["model_call_attempted"]
        or any(copied.get(name) is not True for name in _TRUE_FLAGS)
        or any(copied.get(name) is not False for name in _FALSE_FLAGS)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.60 partial-field receipt drifted")
    return copied


__all__ = [
    "MAXIMUM_CONTROL_EVIDENCE_CHARACTERS",
    "MAXIMUM_PROPOSAL_INPUT_CHARACTERS",
    "POLICY_ID",
    "PROPOSAL_OUTPUT_TOKEN_CAP",
    "RECEIPT_ROLE",
    "ROLE",
    "SYSTEM_PROMPT",
    "build_representation",
    "prepare_record_proposal",
    "validate_receipt",
]
