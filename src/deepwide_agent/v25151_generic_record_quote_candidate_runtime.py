"""Generic exact-quote record grammars for deterministic candidate selection.

This append-only successor keeps the V2.51.47 retrieval trace, production
prediction, verified-gain gate, budgets, selector, and reverified projection.
It adds four content-generic candidate grammars over the same verified delta
pages: flat JSON objects, same-line labelled records, contiguous multi-line
labelled records, and an exact production-row heading followed by labelled
fields.  Labels must match visible output columns and the row identity must be
unique in the completed production table.  Every resulting edit still passes
the V2.51.43 exact-quote same-page row/field/value verifier before selection
and again after selection.

No benchmark label, mapping, gold, evaluator, score, reward, history,
credential, filesystem, process, environment, or additional network surface
is introduced. Entropy/information gain assigns no signed credit and this
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

from . import v25147_deterministic_quote_candidate_runtime as parent
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25151_generic_record_quote_candidate_runtime_v1"
ROLE = "v25151_generic_record_quote_candidate_runtime_result"
RECEIPT_ROLE = "v25151_content_free_generic_record_quote_candidate_receipt"
ARMS = parent.ARMS
CONTROL_ARM, CANDIDATE_ARM = ARMS
PHASES = parent.PHASES
FIRST_PHASE, SECOND_PHASE = PHASES
MAXIMUM_CANDIDATES = parent.MAXIMUM_CANDIDATES
MAXIMUM_QUOTE_CHARACTERS = parent.MAXIMUM_QUOTE_CHARACTERS
MAXIMUM_CELL_CHARACTERS = parent.MAXIMUM_CELL_CHARACTERS


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name and len(name) <= 128 else "Exception"


def _surface(value: object) -> str:
    return " ".join(
        unicodedata.normalize("NFKC", str(value or "")).split()
    ).casefold()


def _column_index(header: Sequence[str], raw: object) -> int | None:
    key = _surface(raw)
    matches = [index for index, value in enumerate(header) if _surface(value) == key]
    return matches[0] if key and len(matches) == 1 else None


def _proposals(
    *,
    page_ordinal: int,
    exact_quote: str,
    pairs: Sequence[tuple[int, object]],
    header: Sequence[str],
    rows: Sequence[Sequence[str]],
    source_kind: str,
) -> list[dict[str, Any]]:
    if not 1 <= len(exact_quote) <= MAXIMUM_QUOTE_CHARACTERS:
        return []
    identities = [value for index, value in pairs if index == 0]
    targets = [(index, value) for index, value in pairs if index > 0]
    if len(identities) != 1 or not targets:
        return []
    row_index = parent._row_index(rows, identities[0])
    if row_index is None:
        return []
    output: list[dict[str, Any]] = []
    for field_index, raw_value in targets:
        candidate = parent._proposal(
            page_ordinal=page_ordinal,
            quote=exact_quote,
            row_index=row_index,
            field_index=field_index,
            new_value=raw_value,
            header=header,
            rows=rows,
            source_kind=source_kind,
        )
        if candidate is not None:
            output.append(candidate)
    return output


def _flat_json_object_observations(
    content: str,
    *,
    page_ordinal: int,
    header: Sequence[str],
    rows: Sequence[Sequence[str]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for _start, _end, line in parent._line_spans(content):
        stripped = line.strip()
        if not (stripped.startswith("{") and stripped.endswith("}")):
            continue
        try:
            payload = parent.quote_parent._strict_json_object(stripped)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        pairs: list[tuple[int, object]] = []
        seen: set[int] = set()
        invalid = False
        for raw_label, raw_value in payload.items():
            index = _column_index(header, raw_label)
            if index is None:
                continue
            if index in seen or isinstance(raw_value, (Mapping, list)):
                invalid = True
                break
            seen.add(index)
            pairs.append((index, raw_value))
        if invalid:
            continue
        output.extend(
            _proposals(
                page_ordinal=page_ordinal,
                exact_quote=stripped,
                pairs=pairs,
                header=header,
                rows=rows,
                source_kind="flat_json_object_record",
            )
        )
    return output


def _label_pattern(header: Sequence[str]) -> re.Pattern[str]:
    labels = sorted((re.escape(value) for value in header), key=len, reverse=True)
    return re.compile(r"(^|[\s,;|•])(" + "|".join(labels) + r")\s*[:=]\s*")


def _inline_pairs(line: str, header: Sequence[str]) -> list[tuple[int, str]]:
    text = str(line).strip()
    pattern = _label_pattern(header)
    matches = list(pattern.finditer(text))
    if len(matches) < 2 or text[: matches[0].start()].strip(" \t-*•,;|"):
        return []
    output: list[tuple[int, str]] = []
    for position, match in enumerate(matches):
        index = _column_index(header, match.group(2))
        end = matches[position + 1].start() if position + 1 < len(matches) else len(text)
        raw = text[match.end() : end].strip(" \t,;|•")
        value = parent._safe_cell(raw)
        if index is None or value is None:
            return []
        output.append((index, value))
    return output


def _single_label_pair(line: str, header: Sequence[str]) -> tuple[int, str] | None:
    text = str(line).strip()
    labels = sorted((re.escape(value) for value in header), key=len, reverse=True)
    match = re.fullmatch(
        r"(?:[-*•]\s*)?(" + "|".join(labels) + r")\s*[:=]\s*(.+?)\s*",
        text,
    )
    if match is None:
        return None
    index = _column_index(header, match.group(1))
    value = parent._safe_cell(match.group(2))
    return (index, value) if index is not None and value is not None else None


def _inline_labelled_record_observations(
    content: str,
    *,
    page_ordinal: int,
    header: Sequence[str],
    rows: Sequence[Sequence[str]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for _start, _end, line in parent._line_spans(content):
        pairs = _inline_pairs(line, header)
        if pairs:
            output.extend(
                _proposals(
                    page_ordinal=page_ordinal,
                    exact_quote=line.strip(),
                    pairs=pairs,
                    header=header,
                    rows=rows,
                    source_kind="inline_exact_labelled_record",
                )
            )
    return output


def _heading_identity(line: str, rows: Sequence[Sequence[str]]) -> object | None:
    text = str(line).strip()
    text = re.sub(r"^#{1,6}\s+", "", text)
    text = re.sub(r"^\*\*(.*?)\*\*$", r"\1", text)
    text = text.strip(" \t:：")
    index = parent._row_index(rows, text)
    return rows[index][0] if index is not None else None


def _block_labelled_record_observations(
    content: str,
    *,
    page_ordinal: int,
    header: Sequence[str],
    rows: Sequence[Sequence[str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    multiline: list[dict[str, Any]] = []
    heading: list[dict[str, Any]] = []
    lines = parent._line_spans(content)
    index = 0
    while index < len(lines):
        start, _end, line = lines[index]
        first = _single_label_pair(line, header)
        if first is not None:
            pairs = [first]
            last_end = lines[index][1]
            cursor = index + 1
            while cursor < len(lines):
                pair = _single_label_pair(lines[cursor][2], header)
                if pair is None:
                    break
                pairs.append(pair)
                last_end = lines[cursor][1]
                cursor += 1
            if len(pairs) >= 2:
                multiline.extend(
                    _proposals(
                        page_ordinal=page_ordinal,
                        exact_quote=content[start:last_end],
                        pairs=pairs,
                        header=header,
                        rows=rows,
                        source_kind="contiguous_exact_labelled_record",
                    )
                )
            index = max(index + 1, cursor)
            continue
        identity = _heading_identity(line, rows)
        if identity is not None:
            pairs: list[tuple[int, object]] = [(0, identity)]
            last_end = lines[index][1]
            cursor = index + 1
            while cursor < len(lines):
                pair = _single_label_pair(lines[cursor][2], header)
                if pair is None or pair[0] == 0:
                    break
                pairs.append(pair)
                last_end = lines[cursor][1]
                cursor += 1
            if len(pairs) >= 2:
                heading.extend(
                    _proposals(
                        page_ordinal=page_ordinal,
                        exact_quote=content[start:last_end],
                        pairs=pairs,
                        header=header,
                        rows=rows,
                        source_kind="row_heading_exact_labelled_record",
                    )
                )
            index = max(index + 1, cursor)
            continue
        index += 1
    return multiline, heading


def extract_quote_candidates(
    production: str,
    *,
    columns: Sequence[str],
    pages: Sequence[Mapping[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Extract generic records, then conflict-filter and reverify every edit."""

    header, rows = parent.targeted_parent._table_matrix(production, columns)
    normalized_pages = [
        {
            "title": str(page.get("title") or ""),
            "content": str(page.get("content") or ""),
        }
        for page in pages
    ]
    observed: list[dict[str, Any]] = []
    counts = {
        "bound_json_record_observation_count": 0,
        "pipe_table_observation_count": 0,
        "flat_json_object_observation_count": 0,
        "inline_labelled_record_observation_count": 0,
        "multiline_labelled_record_observation_count": 0,
        "heading_labelled_record_observation_count": 0,
    }
    for ordinal, page in enumerate(normalized_pages, 1):
        values = {
            "bound_json_record_observation_count": parent._json_record_observations(
                page["content"], page_ordinal=ordinal, header=header, rows=rows
            ),
            "pipe_table_observation_count": parent._pipe_table_observations(
                page["content"], page_ordinal=ordinal, header=header, rows=rows
            ),
            "flat_json_object_observation_count": _flat_json_object_observations(
                page["content"], page_ordinal=ordinal, header=header, rows=rows
            ),
            "inline_labelled_record_observation_count": _inline_labelled_record_observations(
                page["content"], page_ordinal=ordinal, header=header, rows=rows
            ),
        }
        multiline, heading = _block_labelled_record_observations(
            page["content"], page_ordinal=ordinal, header=header, rows=rows
        )
        values["multiline_labelled_record_observation_count"] = multiline
        values["heading_labelled_record_observation_count"] = heading
        for name, candidates in values.items():
            counts[name] += len(candidates)
            observed.extend(candidates)

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
        edit = parent.quote_parent._edit_schema(raw_edit)
        if edit is None:
            continue
        projected, diagnostics = parent.quote_parent.apply_quote_attested_edits(
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
        "raw_candidate_observation_count": len(observed),
        "verifier_admissible_candidate_count": len(admissible),
        "conflicting_candidate_count": conflict_count,
        "duplicate_candidate_count": duplicate_count,
        "truncated_candidate_count": truncated,
        "available_candidate_count": len(output),
    }
    if diagnostics["raw_candidate_observation_count"] != sum(counts.values()):
        raise ValueError("V2.51.51 grammar accounting drifted")
    if diagnostics["verifier_admissible_candidate_count"] != (
        diagnostics["conflicting_candidate_count"]
        + diagnostics["duplicate_candidate_count"]
        + diagnostics["truncated_candidate_count"]
        + diagnostics["available_candidate_count"]
    ):
        raise ValueError("V2.51.51 candidate accounting drifted")
    return output, diagnostics


class GenericRecordQuoteCandidateProvider(parent.DeterministicQuoteCandidateProvider):
    """Use generic exact record grammars before bounded ID selection."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.bound_json_record_observation_count = 0
        self.pipe_table_observation_count = 0
        self.flat_json_object_observation_count = 0
        self.inline_labelled_record_observation_count = 0
        self.multiline_labelled_record_observation_count = 0
        self.heading_labelled_record_observation_count = 0

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        if not (
            system == parent.score.SYNTHESIS_SYSTEM
            and self.synthesis_provider_entry_count == 1
        ):
            return super().complete(
                system, user, max_output_tokens=max_output_tokens, json_mode=json_mode
            )
        self.synthesis_provider_entry_count = 2
        self.targeted_revision_entry_count = 1
        self.original_candidate_prompt_character_count = len(system) + len(user)
        try:
            columns = parent.sparse_parent._prompt_columns(user, self._columns())
            verified = self._verified_delta_pages(self._production_user, user, columns)
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
            self.targeted_prompt_character_count = len(parent.SELECTOR_SYSTEM) + len(
                selector_user
            )
            self.candidate_prompt_character_count = self.targeted_prompt_character_count
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
                    parent.SELECTOR_SYSTEM,
                    selector_user,
                    max_output_tokens=max_output_tokens,
                    json_mode=True,
                )
            except BaseException as exc:
                self.provider_failure_type = _safe_failure(exc)
                raise
            selected_ids = parent._selection(parent.score._model_text(response), supplied)
            self.selection_response_strict_json = True
            self.selected_candidate_count = len(selected_ids)
            by_id = {str(candidate["candidate_id"]): candidate for candidate in supplied}
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
            projected, applied = parent.quote_parent.apply_quote_attested_edits(
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
            return parent.table_normalizer._replace_text(response, projected)
        except BaseException as exc:
            if self.provider_failure_type is None:
                self.projection_failure_type = _safe_failure(exc)
            raise


_GRAMMAR_COUNTS = (
    "bound_json_record_observation_count",
    "pipe_table_observation_count",
    "flat_json_object_observation_count",
    "inline_labelled_record_observation_count",
    "multiline_labelled_record_observation_count",
    "heading_labelled_record_observation_count",
)


def _receipt(
    provider: GenericRecordQuoteCandidateProvider,
    parent_result: Mapping[str, Any],
) -> dict[str, Any]:
    sparse_receipt = parent_result["content_free_receipt"]
    changed = parent_result["prediction"] != parent_result["production_prediction"]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_role": parent.sparse_parent.ROLE,
        "parent_policy_id": parent.sparse_parent.POLICY_ID,
        "parent_result_payload_sha256": str(parent_result["result_payload_sha256"]),
        "candidate_revision_entry_count": provider.targeted_revision_entry_count,
        "underlying_provider_forward_count": provider.revision_underlying_provider_forward_count,
        "verified_incremental_page_count": provider.verified_incremental_page_count,
        "candidate_source_page_count": provider.candidate_source_page_count,
        "candidate_quote_character_count": provider.candidate_quote_character_count,
        "original_candidate_prompt_character_count": provider.original_candidate_prompt_character_count,
        "candidate_prompt_character_count": provider.candidate_prompt_character_count,
        **{name: int(getattr(provider, name)) for name in _GRAMMAR_COUNTS},
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
        "generic_grammars_require_unique_normalized_visible_column_labels_and_unique_production_row_identity": True,
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
        "generic_grammars_require_unique_normalized_visible_column_labels_and_unique_production_row_identity",
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
        or copied.get("parent_role") != parent.sparse_parent.ROLE
        or copied.get("parent_policy_id") != parent.sparse_parent.POLICY_ID
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
        raise ValueError("V2.51.51 generic record candidate receipt drifted")
    return copied


def run_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    limits: parent.score.ScoreFirstLimits,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    visible = parent.sparse_parent._validate_boundary(
        task, model=model, searches=searches, limits=limits
    )
    provider = GenericRecordQuoteCandidateProvider(
        model,
        question=visible["question"],
        first_wave_search=searches[FIRST_PHASE],
        limits=limits,
    )
    parent_result = parent.sparse_parent.validate_result(
        parent.sparse_parent.run_task(
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
        "production_prediction_sha256": parent_result["production_prediction_sha256"],
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
        raise ValueError("V2.51.51 result envelope drifted")
    sparse = parent.sparse_parent.validate_result(parent_raw)
    if (
        copied["opaque_id"] != sparse["opaque_id"]
        or copied["production_prediction"] != sparse["production_prediction"]
        or copied["production_prediction_sha256"]
        != sparse["production_prediction_sha256"]
        or copied["prediction"] != sparse["prediction"]
        or copied["prediction_sha256"] != sparse["prediction_sha256"]
        or copied["prediction_kind"] != sparse["prediction_kind"]
        or copied["cost"] != sparse["cost"]
        or copied["parent_result_payload_sha256"] != sparse["result_payload_sha256"]
        or receipt["parent_result_payload_sha256"] != sparse["result_payload_sha256"]
        or receipt["parent_revision_eligible"]
        is not sparse["content_free_receipt"]["revision_eligible"]
        or receipt["parent_revision_failure_present"]
        is not sparse["content_free_receipt"]["revision_failure_present"]
        or receipt["final_prediction_changed_from_production"]
        is not (sparse["prediction"] != sparse["production_prediction"])
    ):
        raise ValueError("V2.51.51 parent binding drifted")
    return copied


run_generic_record_quote_candidate_task = run_task


__all__ = [
    "ARMS",
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "FIRST_PHASE",
    "GenericRecordQuoteCandidateProvider",
    "PHASES",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "SECOND_PHASE",
    "extract_quote_candidates",
    "run_generic_record_quote_candidate_task",
    "run_task",
    "validate_receipt",
    "validate_result",
]
