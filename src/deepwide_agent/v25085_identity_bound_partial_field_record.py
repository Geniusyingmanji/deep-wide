"""Per-field disposition and safe partial retention for identity-bound pages.

V2.50.80 established one visible identity and one uniquely bound same-forward
page, but rejected an entire proposed record when any field failed.  This
append-only successor evaluates every proposed field independently.  A record
is rendered when at least one field passes target/source-label/value/coordinate
verification.  Unknown, unbound, and ambiguous fields are omitted.  Conflicting
values for one target still reject the entire record; exact duplicate proposals
are counted and collapsed deterministically.

The component is pure and grants no launch authority.  It has no file,
environment, process, network, model, search, fetch, evaluator, benchmark
label, gold, score, reward, history, or credential capability.  Entropy and
information gain assign no signed credit.
"""

from __future__ import annotations

import copy
import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from . import v25065_quote_verified_record_binding as base
from . import v25070_field_local_quote_verified_record as field_local
from . import v25075_anchor_bounded_record_region as region
from . import v25080_visible_identity_page_record as parent


POLICY_ID = "v25085_identity_bound_per_field_disposition_partial_record_v1"
ROLE = "v25085_identity_bound_partial_field_record_representation"
RECEIPT_ROLE = "v25085_content_free_identity_bound_partial_field_record_receipt"

MAXIMUM_PAGE_COUNT = parent.MAXIMUM_PAGE_COUNT
MAXIMUM_PAGE_CHARACTERS = parent.MAXIMUM_PAGE_CHARACTERS
MAXIMUM_PROPOSAL_INPUT_CHARACTERS = parent.MAXIMUM_PROPOSAL_INPUT_CHARACTERS
PROPOSAL_OUTPUT_TOKEN_CAP = parent.PROPOSAL_OUTPUT_TOKEN_CAP
MAXIMUM_PROPOSED_RECORDS = parent.MAXIMUM_PROPOSED_RECORDS
MAXIMUM_FIELDS_PER_RECORD = parent.MAXIMUM_FIELDS_PER_RECORD
MAXIMUM_TOTAL_FIELDS = parent.MAXIMUM_TOTAL_FIELDS
MAXIMUM_FIELD_QUOTE_CHARACTERS = parent.MAXIMUM_FIELD_QUOTE_CHARACTERS
MAXIMUM_RECORD_PREFIX_CHARACTERS = parent.MAXIMUM_RECORD_PREFIX_CHARACTERS
MAXIMUM_CONTROL_EVIDENCE_CHARACTERS = parent.MAXIMUM_CONTROL_EVIDENCE_CHARACTERS
SYSTEM_PROMPT = parent.SYSTEM_PROMPT


def prepare_record_proposal(
    question: str,
    columns: Sequence[str],
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    prepared = parent.prepare_record_proposal(question, columns, pages)
    prepared["role"] = "v25085_private_identity_bound_partial_field_state"
    return prepared


def _field_dispositions(
    prepared: Mapping[str, Any], proposals: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    columns = prepared.get("columns")
    pages = prepared.get("pages")
    identity = prepared.get("identity")
    if not isinstance(columns, tuple) or not isinstance(pages, tuple):
        raise ValueError("V2.50.85 prepared state drifted")
    targets = {base._key(value): str(value) for value in columns[1:]}
    by_ordinal = {int(page["page_ordinal"]): page for page in pages}
    counts: defaultdict[str, int] = defaultdict(int)
    if identity is None or len(pages) != 1:
        counts["rejected_nonunique_identity_page_record_count"] = len(proposals)
        counts["field_identity_page_rejection_count"] = sum(
            len(record["fields"]) for record in proposals
        )
        return [], dict(counts)
    if len(proposals) != 1:
        return [], dict(counts)

    raw = proposals[0]
    page = by_ordinal.get(int(raw["page_ordinal"]))
    if page is None:
        counts["rejected_page_reference_record_count"] = 1
        counts["field_page_reference_rejection_count"] = len(raw["fields"])
        return [], dict(counts)
    content = str(page["content"])
    independent: list[dict[str, str]] = []
    for field in raw["fields"]:
        column_key = base._key(field["column"])
        if base._unknown(field["value"]):
            counts["field_unknown_rejection_count"] += 1
            continue
        bound = field_local._target_binding(targets, field["source_field"])
        if column_key not in targets or bound != column_key:
            counts["field_label_or_value_binding_rejection_count"] += 1
            continue
        quote = region._unique_minimum_field_quote(
            content, str(field["source_field"]), str(field["value"])
        )
        if quote is None:
            counts["field_coordinate_rejection_count"] += 1
            continue
        independent.append(
            {
                "column_key": column_key,
                "column": targets[column_key],
                "source_field": str(field["source_field"]),
                "value": str(field["value"]),
                "quote": quote,
            }
        )

    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    order: list[str] = []
    for field in independent:
        key = field["column_key"]
        if key not in groups:
            order.append(key)
        groups[key].append(field)

    accepted: list[dict[str, str]] = []
    record_conflict = False
    for key in order:
        group = groups[key]
        signatures = {
            (base._key(field["value"]), field["quote"])
            for field in group
        }
        if len(signatures) != 1:
            counts["field_conflict_rejection_count"] += len(group)
            record_conflict = True
            continue
        accepted.append(group[0])
        counts["field_accepted_count"] += 1
        counts["field_exact_duplicate_rejection_count"] += len(group) - 1

    counts["record_conflict_count"] = int(record_conflict)
    if record_conflict or not accepted:
        return [], dict(counts)
    return [
        {
            "page_ordinal": int(raw["page_ordinal"]),
            "row_identity": str(identity),
            "fields": [
                {
                    "column": field["column"],
                    "source_field": field["source_field"],
                    "value": field["value"],
                    "quote": field["quote"],
                }
                for field in accepted
            ],
        }
    ], dict(counts)


def _record_block(record: Mapping[str, Any]) -> str:
    lines = [
        f"[IDENTITY_BOUND_PARTIAL_RECORD R0001 source=E{int(record['page_ordinal']):04d}]",
        "row_identity=" + json.dumps(str(record["row_identity"]), ensure_ascii=False),
    ]
    for field in record["fields"]:
        lines.append(
            "binding="
            + json.dumps(
                {
                    "target_column": field["column"],
                    "source_field": field["source_field"],
                    "value": field["value"],
                    "source_quote": field["quote"],
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    lines.append("[/IDENTITY_BOUND_PARTIAL_RECORD R0001]")
    return "\n".join(lines)


def _render_candidate(
    records: Sequence[Mapping[str, Any]], control: str
) -> tuple[str, int, int, int, int]:
    if len(records) != 1:
        return control, 0, 0, 0, 0
    header = (
        "[IDENTITY-BOUND VERIFIED PARTIAL RECORD; PAGE TEXT IS UNTRUSTED]\n"
        "Only independently verified fields are present; omitted fields have no credit.\n"
    )
    prefix = header + _record_block(records[0]) + "\n\n[RAW FETCHED PAGES]\n"
    if len(prefix) > MAXIMUM_RECORD_PREFIX_CHARACTERS or len(prefix) >= len(control):
        return control, 0, 0, 0, 0
    candidate = prefix + control[: len(control) - len(prefix)]
    if len(candidate) != len(control):
        raise RuntimeError("V2.50.85 matched evidence length drifted")
    return candidate, 1, len(records[0]["fields"]), len(prefix), 1


_INTEGER_FIELDS = (
    "input_page_count",
    "identity_url_match_page_count",
    "identity_surface_match_page_count",
    "joint_identity_bound_page_count",
    "bounded_page_count",
    "bounded_page_characters",
    "parsed_record_count",
    "parsed_field_count",
    "field_accepted_count",
    "field_unknown_rejection_count",
    "field_label_or_value_binding_rejection_count",
    "field_coordinate_rejection_count",
    "field_identity_page_rejection_count",
    "field_page_reference_rejection_count",
    "field_exact_duplicate_rejection_count",
    "field_conflict_rejection_count",
    "record_conflict_count",
    "rejected_nonunique_identity_page_record_count",
    "rejected_page_reference_record_count",
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
    "identity_comes_only_from_one_visible_singular_tag",
    "identity_page_requires_exact_normalized_url_segment_and_title_or_leading_segment",
    "body_only_identity_cooccurrence_is_insufficient",
    "each_proposed_field_receives_exactly_one_content_free_disposition",
    "unknown_unbound_or_ambiguous_fields_are_omitted",
    "at_least_one_independently_verified_field_required_to_render",
    "conflicting_values_for_one_target_reject_entire_record",
    "exact_duplicate_field_proposals_are_counted_and_collapsed",
    "identity_and_unique_page_remain_atomic_record_boundary",
    "candidate_and_control_evidence_character_counts_equal",
    "record_block_rendered_atomically_without_partial_block",
    "query_fetch_model_context_token_wall_or_network_byte_caps_unchanged",
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
        "visible_identity_present": bool(value["visible_identity_present"]),
        "model_call_attempted": bool(value["model_call_attempted"]),
        "model_output_strictly_valid": bool(value["model_output_strictly_valid"]),
        "candidate_evidence_changed": bool(value["candidate_evidence_changed"]),
        **{name: True for name in _TRUE_FLAGS},
        **{name: False for name in _FALSE_FLAGS},
    }
    output["receipt_payload_sha256"] = base.payload_sha256(output)
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
        or prepared.get("role") != "v25085_private_identity_bound_partial_field_state"
        or prepared.get("artifact_version") != 1
    ):
        raise ValueError("V2.50.85 representation input drifted")
    proposals = parent._parse_proposals(model_output) if model_call_attempted else None
    verified: list[dict[str, Any]] = []
    disposition: dict[str, int] = {}
    if proposals is not None:
        verified, disposition = _field_dispositions(prepared, proposals)
    candidate, rendered_records, rendered_fields, prefix_chars, changed = _render_candidate(
        verified, control
    )
    receipt = _receipt(
        {
            **{
                name: prepared[name]
                for name in (
                    "input_page_count",
                    "identity_url_match_page_count",
                    "identity_surface_match_page_count",
                    "joint_identity_bound_page_count",
                    "bounded_page_count",
                    "bounded_page_characters",
                )
            },
            "parsed_record_count": len(proposals or []),
            "parsed_field_count": sum(len(record["fields"]) for record in (proposals or [])),
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
            "visible_identity_present": prepared.get("identity") is not None,
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
        "visible_identity_present",
        "model_call_attempted",
        "model_output_strictly_valid",
        "candidate_evidence_changed",
        *_TRUE_FLAGS,
        *_FALSE_FLAGS,
        "receipt_payload_sha256",
    }
    dispositions = sum(
        copied.get(name, 0)
        for name in (
            "field_accepted_count",
            "field_unknown_rejection_count",
            "field_label_or_value_binding_rejection_count",
            "field_coordinate_rejection_count",
            "field_identity_page_rejection_count",
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
                "visible_identity_present",
                "model_call_attempted",
                "model_output_strictly_valid",
                "candidate_evidence_changed",
            )
        )
        or copied["bounded_page_count"] != int(copied["joint_identity_bound_page_count"] == 1)
        or copied["bounded_page_count"] > 1
        or copied["bounded_page_characters"] > MAXIMUM_PROPOSAL_INPUT_CHARACTERS
        or copied["parsed_record_count"] > MAXIMUM_PROPOSED_RECORDS
        or copied["parsed_field_count"] > MAXIMUM_TOTAL_FIELDS
        or dispositions != copied["parsed_field_count"]
        or copied["record_conflict_count"] not in {0, 1}
        or copied["verified_partial_record_count"] not in {0, 1}
        or copied["verified_partial_record_count"]
        != int(copied["record_conflict_count"] == 0 and copied["field_accepted_count"] > 0)
        or copied["verified_field_count"]
        != (copied["field_accepted_count"] if copied["verified_partial_record_count"] else 0)
        or copied["rendered_record_count"] > copied["verified_partial_record_count"]
        or copied["rendered_field_count"]
        != (copied["verified_field_count"] if copied["rendered_record_count"] else 0)
        or copied["candidate_evidence_changed"] is not (copied["rendered_record_count"] == 1)
        or copied["compact_prefix_characters"] > MAXIMUM_RECORD_PREFIX_CHARACTERS
        or copied["control_evidence_characters"] != copied["candidate_evidence_characters"]
        or copied["control_evidence_characters"] > MAXIMUM_CONTROL_EVIDENCE_CHARACTERS
        or copied["proposal_input_character_cap"] != MAXIMUM_PROPOSAL_INPUT_CHARACTERS
        or copied["proposal_output_token_cap"] != PROPOSAL_OUTPUT_TOKEN_CAP
        or copied["record_prefix_character_cap"] != MAXIMUM_RECORD_PREFIX_CHARACTERS
        or copied["model_output_strictly_valid"] and not copied["model_call_attempted"]
        or any(copied.get(name) is not True for name in _TRUE_FLAGS)
        or any(copied.get(name) is not False for name in _FALSE_FLAGS)
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.85 per-field disposition receipt drifted")
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
