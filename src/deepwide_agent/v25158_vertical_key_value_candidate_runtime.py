"""Vertical key-value record binder for deterministic quote candidates.

This append-only successor addresses the representation mismatch localized by
V2.51.57: many already-fetched detail pages retain one record as a vertical
two-column ``field | value`` table, while the production row identity appears
on another row of that same table.  The inherited V2.51.51 grammars, retrieval
trace, verified-gain gate, budgets, selector, and production prediction remain
unchanged.

A vertical block is admissible only when every visible key maps injectively to
the visible output schema, the block contains exactly one primary-key row, and
that value uniquely matches one existing production row.  Every non-key edit
uses the exact contiguous identity-row-to-field-row span from the same page;
the span must be unique and at most 1,200 characters.  Duplicate keys, multiple
identity-bound blocks on one page, unknown values, conflicts, cross-page joins,
or any attempt to change shape or the key column fail closed.  Each candidate
still passes the V2.51.43 verifier before selection and again after selection.

No benchmark label, mapping, gold, evaluator, score, reward, history,
credential, filesystem, process, environment, or additional network surface
is introduced.  Entropy/information gain assigns no signed credit, and this
build-only module authorizes no benchmark or evaluator launch.
"""

from __future__ import annotations

import copy
import json
import re
import time
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import v25151_generic_record_quote_candidate_runtime as parent
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


deterministic_parent = parent.parent
quote_parent = deterministic_parent.quote_parent
score = deterministic_parent.score
sparse_parent = deterministic_parent.sparse_parent
table_normalizer = deterministic_parent.table_normalizer

POLICY_ID = "v25158_vertical_key_value_candidate_runtime_v1"
ROLE = "v25158_vertical_key_value_candidate_runtime_result"
RECEIPT_ROLE = "v25158_content_free_vertical_key_value_candidate_receipt"
ARMS = parent.ARMS
CONTROL_ARM, CANDIDATE_ARM = ARMS
PHASES = parent.PHASES
FIRST_PHASE, SECOND_PHASE = PHASES
MAXIMUM_CANDIDATES = parent.MAXIMUM_CANDIDATES
MAXIMUM_QUOTE_CHARACTERS = parent.MAXIMUM_QUOTE_CHARACTERS


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name and len(name) <= 128 else "Exception"


def _surface(value: object) -> str:
    return " ".join(
        unicodedata.normalize("NFKC", str(value or "")).split()
    ).casefold()


def _vertical_key(value: object) -> str:
    text = " ".join(unicodedata.normalize("NFKC", str(value or "")).split())
    return re.sub(r"[\s:=]+$", "", text).strip()


def _vertical_pipe_blocks(
    content: str,
) -> list[list[tuple[int, int, str, str]]]:
    """Return maximal two-column row blocks; blank lines do not split a block."""

    blocks: list[list[tuple[int, int, str, str]]] = []
    current: list[tuple[int, int, str, str]] = []
    for start, end, line in deterministic_parent._line_spans(content):
        if not line.strip():
            continue
        cells = deterministic_parent._pipe_cells(line)
        if (
            cells is not None
            and len(cells) == 2
            and not deterministic_parent._separator(cells)
        ):
            current.append((start, end, cells[0], cells[1]))
            continue
        if current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def _vertical_block_candidates(
    content: str,
    block: Sequence[tuple[int, int, str, str]],
    *,
    page_ordinal: int,
    header: Sequence[str],
    rows: Sequence[Sequence[str]],
) -> tuple[bool, list[dict[str, Any]]]:
    """Bind one block to one production row and return bounded field edits."""

    seen_keys: set[str] = set()
    visible: list[tuple[int, int, int, str]] = []
    for start, end, raw_key, raw_value in block:
        key = _vertical_key(raw_key)
        canonical_key = _surface(key)
        if not key or not canonical_key or canonical_key in seen_keys:
            return False, []
        seen_keys.add(canonical_key)
        field_index = parent._column_index(header, key)
        if field_index is None:
            continue
        value = deterministic_parent._safe_cell(raw_value)
        if value is None:
            return False, []
        visible.append((start, end, field_index, value))

    identity_rows = [entry for entry in visible if entry[2] == 0]
    if len(identity_rows) != 1:
        return False, []
    identity_start, identity_end, _identity_field, raw_identity = identity_rows[0]
    row_index = deterministic_parent._row_index(rows, raw_identity)
    if row_index is None:
        return False, []

    output: list[dict[str, Any]] = []
    for field_start, field_end, field_index, raw_value in visible:
        if field_index == 0:
            continue
        quote_start = min(identity_start, field_start)
        quote_end = max(identity_end, field_end)
        exact_quote = content[quote_start:quote_end]
        if (
            not 1 <= len(exact_quote) <= MAXIMUM_QUOTE_CHARACTERS
            or not quote_parent._occurs_exactly_once(content, exact_quote)
        ):
            continue
        candidate = deterministic_parent._proposal(
            page_ordinal=page_ordinal,
            quote=exact_quote,
            row_index=row_index,
            field_index=field_index,
            new_value=raw_value,
            header=header,
            rows=rows,
            source_kind="vertical_key_value_identity_field_span",
        )
        if candidate is not None:
            output.append(candidate)
    return True, output


def _vertical_key_value_observations(
    content: str,
    *,
    page_ordinal: int,
    header: Sequence[str],
    rows: Sequence[Sequence[str]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    blocks = _vertical_pipe_blocks(content)
    identity_bound = 0
    bundles: list[list[dict[str, Any]]] = []
    for block in blocks:
        bound, candidates = _vertical_block_candidates(
            content,
            block,
            page_ordinal=page_ordinal,
            header=header,
            rows=rows,
        )
        if bound:
            identity_bound += 1
            bundles.append(candidates)
    ambiguous = int(identity_bound > 1)
    output = bundles[0] if identity_bound == 1 else []
    return output, {
        "vertical_pipe_block_count": len(blocks),
        "vertical_identity_bound_block_count": identity_bound,
        "vertical_ambiguous_page_count": ambiguous,
    }


_GRAMMAR_COUNTS = (
    *parent._GRAMMAR_COUNTS,
    "vertical_key_value_record_observation_count",
)
_VERTICAL_STRUCTURE_COUNTS = (
    "vertical_pipe_block_count",
    "vertical_identity_bound_block_count",
    "vertical_ambiguous_page_count",
)


def extract_quote_candidates(
    production: str,
    *,
    columns: Sequence[str],
    pages: Sequence[Mapping[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Extract seven grammars, conflict-filter, and V2.51.43-preverify edits."""

    header, rows = deterministic_parent.targeted_parent._table_matrix(
        production, columns
    )
    header_keys = [_surface(value) for value in header]
    if any(not value for value in header_keys) or len(set(header_keys)) != len(
        header_keys
    ):
        raise ValueError("V2.51.58 visible schema is not uniquely keyed")
    normalized_pages = [
        {
            "title": str(page.get("title") or ""),
            "content": str(page.get("content") or ""),
        }
        for page in pages
    ]
    observed: list[dict[str, Any]] = []
    counts = {name: 0 for name in _GRAMMAR_COUNTS}
    structure = {name: 0 for name in _VERTICAL_STRUCTURE_COUNTS}
    for ordinal, page in enumerate(normalized_pages, 1):
        values = {
            "bound_json_record_observation_count": deterministic_parent._json_record_observations(
                page["content"], page_ordinal=ordinal, header=header, rows=rows
            ),
            "pipe_table_observation_count": deterministic_parent._pipe_table_observations(
                page["content"], page_ordinal=ordinal, header=header, rows=rows
            ),
            "flat_json_object_observation_count": parent._flat_json_object_observations(
                page["content"], page_ordinal=ordinal, header=header, rows=rows
            ),
            "inline_labelled_record_observation_count": parent._inline_labelled_record_observations(
                page["content"], page_ordinal=ordinal, header=header, rows=rows
            ),
        }
        multiline, heading = parent._block_labelled_record_observations(
            page["content"], page_ordinal=ordinal, header=header, rows=rows
        )
        values["multiline_labelled_record_observation_count"] = multiline
        values["heading_labelled_record_observation_count"] = heading
        vertical, vertical_structure = _vertical_key_value_observations(
            page["content"], page_ordinal=ordinal, header=header, rows=rows
        )
        values["vertical_key_value_record_observation_count"] = vertical
        for name, candidates in values.items():
            counts[name] += len(candidates)
            observed.extend(candidates)
        for name, value in vertical_structure.items():
            structure[name] += value

    admissible: list[dict[str, Any]] = []
    for candidate in observed:
        raw_edit = {
            key: candidate[key]
            for key in (
                "page_ordinal",
                "exact_quote",
                "row_identity",
                "field",
                "old_value",
                "new_value",
            )
        }
        edit = quote_parent._edit_schema(raw_edit)
        if edit is None:
            continue
        projected, diagnostics = quote_parent.apply_quote_attested_edits(
            production,
            {"edits": [edit]},
            columns=columns,
            pages=normalized_pages,
        )
        if diagnostics["applied_edit_count"] == 1 and projected != production:
            admissible.append(copy.deepcopy(candidate))

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for candidate in admissible:
        grouped.setdefault(
            (candidate["row_identity"], candidate["field"]), []
        ).append(candidate)
    retained: list[dict[str, Any]] = []
    conflict_count = duplicate_count = 0
    for candidates in grouped.values():
        values = {_surface(candidate["new_value"]) for candidate in candidates}
        if len(values) != 1:
            conflict_count += len(candidates)
            continue
        ordered = sorted(
            candidates,
            key=lambda item: (
                int(item["page_ordinal"]),
                str(item["exact_quote"]),
                str(item["new_value"]),
            ),
        )
        retained.append(ordered[0])
        duplicate_count += len(ordered) - 1
    retained.sort(
        key=lambda item: (
            int(item["page_ordinal"]),
            str(item["row_identity"]),
            str(item["field"]),
            str(item["new_value"]),
        )
    )
    truncated = max(0, len(retained) - MAXIMUM_CANDIDATES)
    retained = retained[:MAXIMUM_CANDIDATES]
    output = [
        {"candidate_id": f"C{index:03d}", **copy.deepcopy(candidate)}
        for index, candidate in enumerate(retained, 1)
    ]
    diagnostics = {
        **counts,
        **structure,
        "raw_candidate_observation_count": len(observed),
        "verifier_admissible_candidate_count": len(admissible),
        "conflicting_candidate_count": conflict_count,
        "duplicate_candidate_count": duplicate_count,
        "truncated_candidate_count": truncated,
        "available_candidate_count": len(output),
    }
    if diagnostics["raw_candidate_observation_count"] != sum(
        counts.values()
    ):
        raise ValueError("V2.51.58 grammar accounting drifted")
    if diagnostics["vertical_identity_bound_block_count"] > diagnostics[
        "vertical_pipe_block_count"
    ]:
        raise ValueError("V2.51.58 vertical block accounting drifted")
    if diagnostics["verifier_admissible_candidate_count"] != (
        diagnostics["conflicting_candidate_count"]
        + diagnostics["duplicate_candidate_count"]
        + diagnostics["truncated_candidate_count"]
        + diagnostics["available_candidate_count"]
    ):
        raise ValueError("V2.51.58 candidate accounting drifted")
    return output, diagnostics


class VerticalKeyValueCandidateProvider(parent.GenericRecordQuoteCandidateProvider):
    """Add vertical record binding before the inherited bounded selector."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.vertical_key_value_record_observation_count = 0
        self.vertical_pipe_block_count = 0
        self.vertical_identity_bound_block_count = 0
        self.vertical_ambiguous_page_count = 0

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        if not (
            system == score.SYNTHESIS_SYSTEM
            and self.synthesis_provider_entry_count == 1
        ):
            return super().complete(
                system, user, max_output_tokens=max_output_tokens, json_mode=json_mode
            )
        self.synthesis_provider_entry_count = 2
        self.targeted_revision_entry_count = 1
        self.original_candidate_prompt_character_count = len(system) + len(user)
        try:
            columns = sparse_parent._prompt_columns(user, self._columns())
            verified = self._verified_delta_pages(
                self._production_user, user, columns
            )
            self.verified_incremental_page_count = len(verified)
            candidates, diagnostics = extract_quote_candidates(
                self.production_prediction or "", columns=columns, pages=verified
            )
            for name, value in diagnostics.items():
                setattr(self, name, value)
            selector_user, supplied = self._candidate_prompt(
                inherited_system=system,
                inherited_user=user,
                columns=columns,
                candidates=candidates,
            )
            self.supplied_candidate_count = len(supplied)
            self.supplied_incremental_page_count = len(
                {int(candidate["page_ordinal"]) for candidate in supplied}
            )
            self.candidate_source_page_count = self.supplied_incremental_page_count
            self.candidate_quote_character_count = sum(
                len(str(candidate["exact_quote"])) for candidate in supplied
            )
            self.supplied_incremental_evidence_character_count = (
                self.candidate_quote_character_count
            )
            self.targeted_prompt_character_count = len(
                deterministic_parent.SELECTOR_SYSTEM
            ) + len(selector_user)
            self.candidate_prompt_character_count = (
                self.targeted_prompt_character_count
            )
            self.context_cap_preserved = (
                self.targeted_prompt_character_count
                <= self.original_candidate_prompt_character_count
            )
            self.targeted_prompt_built = True
            self.selector_prompt_built = True
            self.production_table_conditioned = bool(
                self.production_prediction
                and self.production_prediction in selector_user
            )
            self.revision_underlying_provider_forward_count = 1
            try:
                response = self._bounded.complete(
                    deterministic_parent.SELECTOR_SYSTEM,
                    selector_user,
                    max_output_tokens=max_output_tokens,
                    json_mode=True,
                )
            except BaseException as exc:
                self.provider_failure_type = _safe_failure(exc)
                raise
            selected_ids = deterministic_parent._selection(
                score._model_text(response), supplied
            )
            self.selection_response_strict_json = True
            self.selected_candidate_count = len(selected_ids)
            by_id = {
                str(candidate["candidate_id"]): candidate for candidate in supplied
            }
            edits = [
                {
                    key: by_id[candidate_id][key]
                    for key in (
                        "page_ordinal",
                        "exact_quote",
                        "row_identity",
                        "field",
                        "old_value",
                        "new_value",
                    )
                }
                for candidate_id in selected_ids
            ]
            self.projection_attempted = True
            projected, applied = quote_parent.apply_quote_attested_edits(
                self.production_prediction or "",
                {"edits": edits},
                columns=columns,
                pages=verified,
            )
            self.model_edit_count = applied["model_edit_count"]
            self.parsed_edit_count = applied["parsed_edit_count"]
            self.quote_attested_edit_count = applied["quote_attested_edit_count"]
            self.applied_edit_count = applied["applied_edit_count"]
            self.rejected_edit_count = applied["rejected_edit_count"]
            self.rejected_selected_edit_count = self.rejected_edit_count
            self.rejection_counts = applied["rejection_counts"]
            self.proposed_changed_cell_count = self.selected_candidate_count
            self.applied_changed_cell_count = self.applied_edit_count
            self.rejected_changed_cell_count = self.rejected_edit_count
            self.conflicting_changed_cell_count = self.rejection_counts[
                "duplicate_or_conflicting_cell"
            ]
            self.projection_valid = True
            self.edit_projection_valid = True
            self.candidate_projection_valid = True
            return table_normalizer._replace_text(response, projected)
        except BaseException as exc:
            if self.provider_failure_type is None:
                self.projection_failure_type = _safe_failure(exc)
            raise


def _receipt(
    provider: VerticalKeyValueCandidateProvider,
    parent_result: Mapping[str, Any],
) -> dict[str, Any]:
    sparse_receipt = parent_result["content_free_receipt"]
    changed = parent_result["prediction"] != parent_result["production_prediction"]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_role": sparse_parent.ROLE,
        "parent_policy_id": sparse_parent.POLICY_ID,
        "parent_result_payload_sha256": str(parent_result["result_payload_sha256"]),
        "candidate_revision_entry_count": provider.targeted_revision_entry_count,
        "underlying_provider_forward_count": provider.revision_underlying_provider_forward_count,
        "verified_incremental_page_count": provider.verified_incremental_page_count,
        "candidate_source_page_count": provider.candidate_source_page_count,
        "candidate_quote_character_count": provider.candidate_quote_character_count,
        "original_candidate_prompt_character_count": provider.original_candidate_prompt_character_count,
        "candidate_prompt_character_count": provider.candidate_prompt_character_count,
        **{name: int(getattr(provider, name)) for name in _GRAMMAR_COUNTS},
        **{
            name: int(getattr(provider, name))
            for name in _VERTICAL_STRUCTURE_COUNTS
        },
        "raw_candidate_observation_count": provider.raw_candidate_observation_count,
        "verifier_admissible_candidate_count": provider.verifier_admissible_candidate_count,
        "conflicting_candidate_count": provider.conflicting_candidate_count,
        "duplicate_candidate_count": provider.duplicate_candidate_count,
        "truncated_candidate_count": provider.truncated_candidate_count,
        "available_candidate_count": provider.available_candidate_count,
        "supplied_candidate_count": provider.supplied_candidate_count,
        "selected_candidate_count": provider.selected_candidate_count,
        "applied_edit_count": provider.applied_edit_count,
        "rejected_selected_edit_count": provider.rejected_selected_edit_count,
        "selector_prompt_built": provider.selector_prompt_built,
        "production_table_conditioned": provider.production_table_conditioned,
        "only_verified_incremental_evidence_supplied": provider.only_verified_incremental_evidence_supplied,
        "context_cap_preserved": provider.context_cap_preserved,
        "selection_response_strict_json": provider.selection_response_strict_json,
        "candidate_projection_valid": provider.candidate_projection_valid,
        "projection_failure_present": provider.projection_failure_type is not None,
        "provider_failure_present": provider.provider_failure_type is not None,
        "parent_post_effect_failure_present": bool(
            sparse_receipt["post_effect_failure_present"]
        ),
        "final_prediction_changed_from_production": changed,
        "production_prediction_preserved_on_failure": bool(
            not (
                provider.projection_failure_type is not None
                or provider.provider_failure_type is not None
                or sparse_receipt["post_effect_failure_present"]
            )
            or not changed
        ),
        "parent_revision_eligible": bool(sparse_receipt["revision_eligible"]),
        "parent_revision_failure_present": bool(
            sparse_receipt["revision_failure_present"]
        ),
        "vertical_blocks_require_one_unique_production_identity_and_unique_visible_keys": True,
        "vertical_quotes_are_same_page_unique_bounded_identity_to_field_spans": True,
        "duplicate_keys_multiple_identity_blocks_unknowns_and_cross_page_joins_fail_closed": True,
        "every_candidate_is_preverified_and_selected_edits_are_reverified": True,
        "model_can_only_select_candidate_ids_or_abstain": True,
        "conflicting_coordinates_are_omitted_before_selection": True,
        "row_identity_order_shape_key_and_unselected_cells_preserved": True,
        "query_fetch_model_context_token_wall_and_network_caps_unchanged": True,
        "contains_question_column_query_url_title_page_quote_row_field_value_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    counts = (
        "candidate_revision_entry_count",
        "underlying_provider_forward_count",
        "verified_incremental_page_count",
        "candidate_source_page_count",
        "candidate_quote_character_count",
        "original_candidate_prompt_character_count",
        "candidate_prompt_character_count",
        *_GRAMMAR_COUNTS,
        *_VERTICAL_STRUCTURE_COUNTS,
        "raw_candidate_observation_count",
        "verifier_admissible_candidate_count",
        "conflicting_candidate_count",
        "duplicate_candidate_count",
        "truncated_candidate_count",
        "available_candidate_count",
        "supplied_candidate_count",
        "selected_candidate_count",
        "applied_edit_count",
        "rejected_selected_edit_count",
    )
    dynamics = (
        "selector_prompt_built",
        "production_table_conditioned",
        "only_verified_incremental_evidence_supplied",
        "context_cap_preserved",
        "selection_response_strict_json",
        "candidate_projection_valid",
        "projection_failure_present",
        "provider_failure_present",
        "parent_post_effect_failure_present",
        "final_prediction_changed_from_production",
        "production_prediction_preserved_on_failure",
        "parent_revision_eligible",
        "parent_revision_failure_present",
    )
    true_flags = (
        "vertical_blocks_require_one_unique_production_identity_and_unique_visible_keys",
        "vertical_quotes_are_same_page_unique_bounded_identity_to_field_spans",
        "duplicate_keys_multiple_identity_blocks_unknowns_and_cross_page_joins_fail_closed",
        "every_candidate_is_preverified_and_selected_edits_are_reverified",
        "model_can_only_select_candidate_ids_or_abstain",
        "conflicting_coordinates_are_omitted_before_selection",
        "row_identity_order_shape_key_and_unselected_cells_preserved",
        "query_fetch_model_context_token_wall_and_network_caps_unchanged",
    )
    false_flags = (
        "contains_question_column_query_url_title_page_quote_row_field_value_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "parent_role",
        "parent_policy_id",
        "parent_result_payload_sha256",
        *counts,
        *dynamics,
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    entered = copied.get("candidate_revision_entry_count") == 1
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_role") != sparse_parent.ROLE
        or copied.get("parent_policy_id") != sparse_parent.POLICY_ID
        or not isinstance(copied.get("parent_result_payload_sha256"), str)
        or len(copied["parent_result_payload_sha256"]) != 64
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or copied["candidate_revision_entry_count"] not in {0, 1}
        or copied["underlying_provider_forward_count"] not in {0, 1}
        or copied["underlying_provider_forward_count"]
        > copied["candidate_revision_entry_count"]
        or copied["candidate_source_page_count"]
        > copied["verified_incremental_page_count"]
        or copied["vertical_identity_bound_block_count"]
        > copied["vertical_pipe_block_count"]
        or copied["vertical_ambiguous_page_count"]
        > copied["verified_incremental_page_count"]
        or copied["raw_candidate_observation_count"]
        != sum(copied[name] for name in _GRAMMAR_COUNTS)
        or copied["verifier_admissible_candidate_count"]
        != copied["conflicting_candidate_count"]
        + copied["duplicate_candidate_count"]
        + copied["truncated_candidate_count"]
        + copied["available_candidate_count"]
        or copied["available_candidate_count"] > MAXIMUM_CANDIDATES
        or copied["supplied_candidate_count"] > copied["available_candidate_count"]
        or copied["selected_candidate_count"] > copied["supplied_candidate_count"]
        or copied["applied_edit_count"] + copied["rejected_selected_edit_count"]
        != copied["selected_candidate_count"]
        or any(not isinstance(copied.get(name), bool) for name in dynamics)
        or copied["parent_revision_eligible"] is not entered
        or copied["only_verified_incremental_evidence_supplied"] is not True
        or copied["context_cap_preserved"] is not True
        or not entered
        and any(copied[name] for name in counts if name != "candidate_revision_entry_count")
        or not entered
        and any(
            copied[name]
            for name in (
                "selector_prompt_built",
                "production_table_conditioned",
                "selection_response_strict_json",
                "candidate_projection_valid",
                "projection_failure_present",
                "provider_failure_present",
                "parent_post_effect_failure_present",
                "final_prediction_changed_from_production",
                "parent_revision_failure_present",
            )
        )
        or copied["selector_prompt_built"]
        and (
            not copied["production_table_conditioned"]
            or copied["candidate_prompt_character_count"]
            > copied["original_candidate_prompt_character_count"]
        )
        or copied["candidate_projection_valid"]
        and (
            not copied["selection_response_strict_json"]
            or copied["underlying_provider_forward_count"] != 1
        )
        or copied["final_prediction_changed_from_production"]
        is not bool(
            copied["applied_edit_count"] > 0
            and not copied["parent_post_effect_failure_present"]
        )
        or (copied["projection_failure_present"] or copied["provider_failure_present"])
        and not copied["parent_revision_failure_present"]
        or (
            copied["projection_failure_present"]
            or copied["provider_failure_present"]
            or copied["parent_post_effect_failure_present"]
        )
        and not copied["production_prediction_preserved_on_failure"]
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.58 vertical key-value candidate receipt drifted")
    return copied


def run_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    limits: score.ScoreFirstLimits,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    visible = sparse_parent._validate_boundary(
        task, model=model, searches=searches, limits=limits
    )
    provider = VerticalKeyValueCandidateProvider(
        model,
        question=visible["question"],
        first_wave_search=searches[FIRST_PHASE],
        limits=limits,
    )
    parent_result = sparse_parent.validate_result(
        sparse_parent.run_task(
            visible,
            model=provider,
            searches=searches,
            limits=limits,
            monotonic=monotonic,
        )
    )
    receipt = _receipt(provider, parent_result)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": parent_result["opaque_id"],
        "status": "terminal",
        "production_prediction": parent_result["production_prediction"],
        "production_prediction_sha256": parent_result[
            "production_prediction_sha256"
        ],
        "prediction": parent_result["prediction"],
        "prediction_sha256": parent_result["prediction_sha256"],
        "prediction_kind": parent_result["prediction_kind"],
        "cost": copy.deepcopy(parent_result["cost"]),
        "parent_result": copy.deepcopy(parent_result),
        "parent_result_payload_sha256": parent_result["result_payload_sha256"],
        "content_free_receipt": receipt,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    parent_raw = copied.get("parent_result")
    receipt = copied.get("content_free_receipt")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "opaque_id",
        "status",
        "production_prediction",
        "production_prediction_sha256",
        "prediction",
        "prediction_sha256",
        "prediction_kind",
        "cost",
        "parent_result",
        "parent_result_payload_sha256",
        "content_free_receipt",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
        "result_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("status") != "terminal"
        or not isinstance(parent_raw, Mapping)
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.58 result envelope drifted")
    sparse = sparse_parent.validate_result(parent_raw)
    if (
        copied["opaque_id"] != sparse["opaque_id"]
        or copied["production_prediction"] != sparse["production_prediction"]
        or copied["production_prediction_sha256"]
        != sparse["production_prediction_sha256"]
        or copied["prediction"] != sparse["prediction"]
        or copied["prediction_sha256"] != sparse["prediction_sha256"]
        or copied["prediction_kind"] != sparse["prediction_kind"]
        or copied["cost"] != sparse["cost"]
        or copied["parent_result_payload_sha256"]
        != sparse["result_payload_sha256"]
        or receipt["parent_result_payload_sha256"]
        != sparse["result_payload_sha256"]
        or receipt["parent_revision_eligible"]
        is not sparse["content_free_receipt"]["revision_eligible"]
        or receipt["parent_revision_failure_present"]
        is not sparse["content_free_receipt"]["revision_failure_present"]
        or receipt["final_prediction_changed_from_production"]
        is not (sparse["prediction"] != sparse["production_prediction"])
    ):
        raise ValueError("V2.51.58 parent binding drifted")
    return copied


run_vertical_key_value_candidate_task = run_task


__all__ = [
    "ARMS",
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "FIRST_PHASE",
    "PHASES",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "SECOND_PHASE",
    "VerticalKeyValueCandidateProvider",
    "extract_quote_candidates",
    "run_task",
    "run_vertical_key_value_candidate_task",
    "validate_receipt",
    "validate_result",
]
