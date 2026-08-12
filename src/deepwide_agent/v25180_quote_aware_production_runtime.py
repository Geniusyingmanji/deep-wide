r"""Build-only quote-aware production runtime over frozen V2.51.65.

The first production response is observed content-free.  Only when the frozen
production parser rejects it may V2.51.77 replace an unambiguous ``\|`` table
with a reversible pipe-free internal table.  All frozen candidate logic then
runs on that internal table.  After the complete V2.51.65 parent result is
validated, this outer envelope exports CSV-quoted public predictions.

The parent result, effects, costs, failure state, and internal predictions are
retained byte-for-byte inside the sealed envelope.  No external launch or
evaluator is authorized by this module.
"""

from __future__ import annotations

import copy
import hashlib
import re
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import v24257_score_first_runtime as score
from . import v24259_deterministic_table_normalizer as table_normalizer
from . import v25165_observed_vertical_key_value_runtime as parent
from . import v25170_production_normalizer_disposition_observer as observer
from . import v25177_quote_aware_pipe_normalizer as repair
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25180_quote_aware_production_runtime_v1"
ROLE = "v25180_quote_aware_production_runtime_result"
RECEIPT_ROLE = "v25180_content_free_quote_aware_production_receipt"
ARMS = parent.ARMS
CONTROL_ARM, CANDIDATE_ARM = ARMS
PHASES = parent.PHASES
FIRST_PHASE, SECOND_PHASE = PHASES


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name and len(name) <= 128 else "Exception"


class QuoteAwareProductionProvider(
    parent.ObservedVerticalKeyValueCandidateProvider
):
    """Repair only the first raw production response before parent parsing."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.raw_normalizer_observer_entry_count = 0
        self.raw_normalizer_observation: dict[str, Any] | None = None
        self.raw_normalizer_observer_failure_type: str | None = None
        self.quote_aware_repair_attempt_count = 0
        self.quote_aware_repair_applied_count = 0
        self.quote_aware_repair_failure_type: str | None = None
        self.quote_aware_repair_receipt: dict[str, Any] | None = None
        self.quote_aware_public_production: str | None = None

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        first_production = bool(
            system == parent.parent.score.SYNTHESIS_SYSTEM
            and self.synthesis_provider_entry_count == 0
        )
        response = super().complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )
        if not first_production:
            return response
        self.raw_normalizer_observer_entry_count = 1
        try:
            truncated = getattr(response, "output_truncated", False)
            if not isinstance(truncated, bool):
                raise TypeError("V2.51.80 provider truncation flag drifted")
            columns = parent.parent.sparse_parent._prompt_columns(
                user, self._columns()
            )
            raw_text = score._model_text(response)
            self.raw_normalizer_observation = (
                observer.observe_production_normalization(
                    raw_text,
                    columns=columns,
                    provider_output_truncated=truncated,
                )
            )
        except BaseException as exc:
            self.raw_normalizer_observer_failure_type = _safe_failure(exc)
            return response
        if self.raw_normalizer_observation[
            "frozen_synthesis_contract_accepted"
        ]:
            return response
        self.quote_aware_repair_attempt_count = 1
        try:
            repaired = repair.normalize_quote_aware_table(raw_text, columns)
        except BaseException as exc:
            self.quote_aware_repair_failure_type = _safe_failure(exc)
            return response
        if repaired is None:
            return response
        internal, public, receipt = repaired
        try:
            checked_receipt = repair.validate_receipt(receipt)
            header, rows = _internal_matrix(internal, columns)
            coordinates, occurrences = _entity_coordinates(rows)
            if (
                len(coordinates)
                != checked_receipt["internal_entity_cell_count"]
                or occurrences
                != checked_receipt["escaped_pipe_occurrence_count"]
                or public != _render_public(header, _decode_rows(rows))
            ):
                raise ValueError("V2.51.80 repair-public binding drifted")
            _validate_public_loader_values(public, header, _decode_rows(rows))
        except BaseException as exc:
            self.quote_aware_repair_failure_type = _safe_failure(exc)
            return response
        self.quote_aware_repair_receipt = checked_receipt
        self.quote_aware_public_production = public
        self.quote_aware_repair_applied_count = 1
        # The frozen candidate providers refer to this state after production.
        self.production_prediction = internal
        return table_normalizer._replace_text(response, internal)


def _internal_matrix(
    prediction: str, columns: Sequence[str]
) -> tuple[list[str], list[list[str]]]:
    checked, _errors = score.extract_valid_markdown_table(prediction, columns)
    if checked != prediction:
        raise ValueError("V2.51.80 internal prediction is not canonical")
    lines = [
        line.strip()
        for line in prediction.replace("\r\n", "\n").splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    if len(lines) < 3:
        raise ValueError("V2.51.80 internal table is missing")
    header = score._split_table_row(lines[0])
    separator = score._split_table_row(lines[1])
    rows = [score._split_table_row(line) for line in lines[2:]]
    if (
        [score._normalize_column(value) for value in header]
        != [score._normalize_column(value) for value in columns]
        or len(separator) != len(header)
        or any(len(row) != len(header) or not all(row) for row in rows)
    ):
        raise ValueError("V2.51.80 internal table shape drifted")
    return header, rows


def _canonical_internal_columns(prediction: str) -> tuple[str, ...]:
    """Derive columns directly from one canonical internal table header."""

    if not isinstance(prediction, str):
        raise TypeError("V2.51.80 internal prediction must be a string")
    if not prediction.startswith("```markdown\n") or not prediction.endswith(
        "\n```"
    ):
        raise ValueError("V2.51.80 internal prediction fence drifted")
    body = prediction[len("```markdown\n") : -len("\n```")]
    lines = body.splitlines()
    if len(lines) < 3:
        raise ValueError("V2.51.80 internal prediction is incomplete")
    header = score._split_table_row(lines[0])
    columns = tuple(str(value).strip() for value in header)
    normalized = [score._normalize_column(value) for value in columns]
    checked, _errors = score.extract_valid_markdown_table(prediction, columns)
    if (
        not columns
        or len(columns) > 20
        or not all(columns)
        or not all(normalized)
        or len(set(normalized)) != len(columns)
        or checked != prediction
    ):
        raise ValueError("V2.51.80 canonical internal header drifted")
    return columns


def _entity_coordinates(
    rows: Sequence[Sequence[str]],
) -> tuple[set[tuple[int, int]], int]:
    coordinates: set[tuple[int, int]] = set()
    occurrences = 0
    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(row):
            count = str(value).count(repair.INTERNAL_PIPE_ENTITY)
            if count:
                coordinates.add((row_index, column_index))
                occurrences += count
    return coordinates, occurrences


def _csv_quote(value: str) -> str:
    return (
        '"' + value.replace('"', '""') + '"'
        if "|" in value or '"' in value
        else value
    )


def _render_public(
    header: Sequence[str], rows: Sequence[Sequence[str]]
) -> str:
    return (
        "```markdown\n| "
        + " | ".join(header)
        + " |\n| "
        + " | ".join("---" for _ in header)
        + " |\n"
        + "\n".join(
            "| " + " | ".join(_csv_quote(value) for value in row) + " |"
            for row in rows
        )
        + "\n```"
    )


def _decode_rows(rows: Sequence[Sequence[str]]) -> list[list[str]]:
    return [
        [str(value).replace(repair.INTERNAL_PIPE_ENTITY, "|") for value in row]
        for row in rows
    ]


def _loader_canonical_cell(value: str) -> str:
    """Model the released loader's only semantic loss around literal pipes."""

    return re.sub(r"\s*\|\s*", "|", str(value).strip())


def _validate_public_loader_values(
    public: str,
    header: Sequence[str],
    rows: Sequence[Sequence[str]],
) -> list[list[str]]:
    """Require exact loader values after pipe-adjacent whitespace folding."""

    parsed = repair._public_loader_like_values(public)
    expected = [
        [_loader_canonical_cell(value) for value in header],
        *(
            [_loader_canonical_cell(value) for value in row]
            for row in rows
        ),
    ]
    if parsed != expected:
        raise ValueError("V2.51.80 public loader value drifted")
    return parsed


def _safe_public_production(
    production: str,
    *,
    expected_entity_cells: int,
    expected_entity_occurrences: int,
) -> str:
    """Reconstruct and validate the repair-bound public production table."""

    columns = _canonical_internal_columns(production)
    header, rows = _internal_matrix(production, columns)
    coordinates, occurrences = _entity_coordinates(rows)
    if (
        len(coordinates) != expected_entity_cells
        or occurrences != expected_entity_occurrences
        or not coordinates
    ):
        raise ValueError("V2.51.80 safe production entity binding drifted")
    decoded = _decode_rows(rows)
    public = _render_public(header, decoded)
    _validate_public_loader_values(public, header, decoded)
    return public


def _publication_failure_diagnostics(
    repair_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Content-free diagnostics for both-arm production fallback."""

    cells = int(repair_receipt["internal_entity_cell_count"])
    occurrences = int(repair_receipt["escaped_pipe_occurrence_count"])
    quoted = int(repair_receipt["csv_quoted_cell_count"])
    adjacent = int(repair_receipt["adjacent_pipe_whitespace_count"])
    return {
        "production_entity_cell_count": cells,
        "production_entity_occurrence_count": occurrences,
        "internal_final_entity_cell_count": 0,
        "internal_final_entity_occurrence_count": 0,
        "published_final_entity_cell_count": cells,
        "published_final_entity_occurrence_count": occurrences,
        "final_entity_coordinates_subset": False,
        "row_identity_order_shape_invariant": False,
        "candidate_publication_fallback": True,
        "production_csv_quoted_cell_count": quoted,
        "final_csv_quoted_cell_count": quoted,
        "production_adjacent_pipe_whitespace_count": adjacent,
        "final_adjacent_pipe_whitespace_count": adjacent,
    }


def export_public_predictions(
    production: str,
    final: str,
    *,
    columns: Sequence[str],
    expected_production_entity_cells: int,
    expected_production_entity_occurrences: int,
) -> tuple[str, str, dict[str, Any]]:
    """Export quoted tables and fail candidate publication closed on drift."""

    production_header, production_rows = _internal_matrix(production, columns)
    final_header, final_rows = _internal_matrix(final, columns)
    production_coordinates, production_occurrences = _entity_coordinates(
        production_rows
    )
    final_coordinates, final_occurrences = _entity_coordinates(final_rows)
    if (
        len(production_coordinates) != expected_production_entity_cells
        or production_occurrences != expected_production_entity_occurrences
        or not production_coordinates
    ):
        raise ValueError("V2.51.80 production entity binding drifted")
    invariant = bool(
        final_header == production_header
        and len(final_rows) == len(production_rows)
        and [row[0] for row in final_rows] == [row[0] for row in production_rows]
    )
    subset = final_coordinates.issubset(production_coordinates)
    occurrence_bounded = final_occurrences <= production_occurrences
    publication_fallback = not (invariant and subset and occurrence_bounded)
    published_final_rows = production_rows if publication_fallback else final_rows
    published_coordinates, published_occurrences = _entity_coordinates(
        published_final_rows
    )
    public_production = _render_public(
        production_header, _decode_rows(production_rows)
    )
    public_final = _render_public(
        production_header, _decode_rows(published_final_rows)
    )
    for public, expected_values in (
        (public_production, _decode_rows(production_rows)),
        (public_final, _decode_rows(published_final_rows)),
    ):
        _validate_public_loader_values(
            public, production_header, expected_values
        )
    diagnostics = {
        "production_entity_cell_count": len(production_coordinates),
        "production_entity_occurrence_count": production_occurrences,
        "internal_final_entity_cell_count": len(final_coordinates),
        "internal_final_entity_occurrence_count": final_occurrences,
        "published_final_entity_cell_count": len(published_coordinates),
        "published_final_entity_occurrence_count": published_occurrences,
        "final_entity_coordinates_subset": subset,
        "row_identity_order_shape_invariant": invariant,
        "candidate_publication_fallback": publication_fallback,
        "production_csv_quoted_cell_count": sum(
            "|" in value or '"' in value
            for row in _decode_rows(production_rows)
            for value in row
        ),
        "final_csv_quoted_cell_count": sum(
            "|" in value or '"' in value
            for row in _decode_rows(published_final_rows)
            for value in row
        ),
        "production_adjacent_pipe_whitespace_count": sum(
            len(re.findall(r"\s+\||\|\s+", value))
            for row in _decode_rows(production_rows)
            for value in row
        ),
        "final_adjacent_pipe_whitespace_count": sum(
            len(re.findall(r"\s+\||\|\s+", value))
            for row in _decode_rows(published_final_rows)
            for value in row
        ),
    }
    return public_production, public_final, diagnostics


def _internal_parent_result(
    provider: QuoteAwareProductionProvider,
    sparse_result: Mapping[str, Any],
) -> dict[str, Any]:
    vertical_result = parent._frozen_parent_result(provider, sparse_result)
    receipt = parent._receipt(provider, vertical_result)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": parent.ROLE,
        "policy_id": parent.POLICY_ID,
        "opaque_id": vertical_result["opaque_id"],
        "status": "terminal",
        "production_prediction": vertical_result["production_prediction"],
        "production_prediction_sha256": vertical_result[
            "production_prediction_sha256"
        ],
        "prediction": vertical_result["prediction"],
        "prediction_sha256": vertical_result["prediction_sha256"],
        "prediction_kind": vertical_result["prediction_kind"],
        "cost": copy.deepcopy(vertical_result["cost"]),
        "parent_result": copy.deepcopy(vertical_result),
        "parent_result_payload_sha256": vertical_result["result_payload_sha256"],
        "content_free_receipt": receipt,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return parent.validate_result(value)


def _receipt(
    provider: QuoteAwareProductionProvider,
    parent_result: Mapping[str, Any],
    diagnostics: Mapping[str, Any] | None,
    *,
    public_export_attempt_count: int,
    public_export_completed_count: int,
    public_export_failure_type: str | None,
    public_export_fallback_to_completed_production: bool,
) -> dict[str, Any]:
    observation = (
        observer.validate_observation(provider.raw_normalizer_observation)
        if provider.raw_normalizer_observation is not None
        else None
    )
    repair_receipt = (
        repair.validate_receipt(provider.quote_aware_repair_receipt)
        if provider.quote_aware_repair_receipt is not None
        else None
    )
    sparse_receipt = parent_result["parent_result"]["parent_result"][
        "content_free_receipt"
    ]
    values = dict(diagnostics or {})
    count_names = (
        "production_entity_cell_count",
        "production_entity_occurrence_count",
        "internal_final_entity_cell_count",
        "internal_final_entity_occurrence_count",
        "published_final_entity_cell_count",
        "published_final_entity_occurrence_count",
        "production_csv_quoted_cell_count",
        "final_csv_quoted_cell_count",
        "production_adjacent_pipe_whitespace_count",
        "final_adjacent_pipe_whitespace_count",
    )
    bool_names = (
        "final_entity_coordinates_subset",
        "row_identity_order_shape_invariant",
        "candidate_publication_fallback",
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_role": parent.ROLE,
        "parent_policy_id": parent.POLICY_ID,
        "parent_result_payload_sha256": str(parent_result["result_payload_sha256"]),
        "raw_normalizer_observer_entry_count": int(
            provider.raw_normalizer_observer_entry_count
        ),
        "raw_normalizer_observer_completed_count": int(observation is not None),
        "raw_normalizer_observer_failure_present": bool(
            provider.raw_normalizer_observer_failure_type is not None
        ),
        "raw_normalizer_observer_failure_type": (
            provider.raw_normalizer_observer_failure_type
        ),
        "raw_normalizer_observation": copy.deepcopy(observation),
        "quote_aware_repair_attempt_count": int(
            provider.quote_aware_repair_attempt_count
        ),
        "quote_aware_repair_applied_count": int(
            provider.quote_aware_repair_applied_count
        ),
        "quote_aware_repair_failure_present": bool(
            provider.quote_aware_repair_failure_type is not None
        ),
        "quote_aware_repair_failure_type": provider.quote_aware_repair_failure_type,
        "quote_aware_repair_receipt": copy.deepcopy(repair_receipt),
        "public_export_attempt_count": int(public_export_attempt_count),
        "public_export_completed_count": int(public_export_completed_count),
        "public_export_failure_present": bool(public_export_failure_type),
        "public_export_failure_type": public_export_failure_type,
        "public_export_fallback_to_completed_production": bool(
            public_export_fallback_to_completed_production
        ),
        "parent_production_provider_output_valid": bool(
            sparse_receipt["production_provider_output_valid"]
        ),
        "parent_production_fallback_used": bool(
            sparse_receipt["production_fallback_used"]
        ),
        **{name: int(values.get(name, 0)) for name in count_names},
        **{name: bool(values.get(name, False)) for name in bool_names},
        "raw_observation_precedes_repair_and_sparse_parent_normalization": True,
        "repair_only_after_frozen_raw_contract_rejection": True,
        "internal_parent_result_cost_effect_failure_and_candidate_receipts_bound": True,
        "public_export_only_after_internal_parent_terminal_validation": True,
        "candidate_publication_fails_closed_on_entity_or_shape_drift": True,
        "public_export_failure_preserves_completed_production": True,
        "query_fetch_model_context_token_wall_network_and_concurrency_caps_unchanged": True,
        "contains_raw_response_cell_column_question_identity_url_page_key_value_prediction_or_semantic_hash": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value, parent_result=parent_result)


def validate_receipt(
    value: Mapping[str, Any],
    *,
    parent_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    observation = copied.get("raw_normalizer_observation")
    repair_receipt = copied.get("quote_aware_repair_receipt")
    count_names = (
        "raw_normalizer_observer_entry_count",
        "raw_normalizer_observer_completed_count",
        "quote_aware_repair_attempt_count",
        "quote_aware_repair_applied_count",
        "public_export_attempt_count",
        "public_export_completed_count",
        "production_entity_cell_count",
        "production_entity_occurrence_count",
        "internal_final_entity_cell_count",
        "internal_final_entity_occurrence_count",
        "published_final_entity_cell_count",
        "published_final_entity_occurrence_count",
        "production_csv_quoted_cell_count",
        "final_csv_quoted_cell_count",
        "production_adjacent_pipe_whitespace_count",
        "final_adjacent_pipe_whitespace_count",
    )
    dynamic_bools = (
        "raw_normalizer_observer_failure_present",
        "quote_aware_repair_failure_present",
        "public_export_failure_present",
        "public_export_fallback_to_completed_production",
        "parent_production_provider_output_valid",
        "parent_production_fallback_used",
        "final_entity_coordinates_subset",
        "row_identity_order_shape_invariant",
        "candidate_publication_fallback",
    )
    true_flags = (
        "raw_observation_precedes_repair_and_sparse_parent_normalization",
        "repair_only_after_frozen_raw_contract_rejection",
        "internal_parent_result_cost_effect_failure_and_candidate_receipts_bound",
        "public_export_only_after_internal_parent_terminal_validation",
        "candidate_publication_fails_closed_on_entity_or_shape_drift",
        "public_export_failure_preserves_completed_production",
        "query_fetch_model_context_token_wall_network_and_concurrency_caps_unchanged",
    )
    false_flags = (
        "contains_raw_response_cell_column_question_identity_url_page_key_value_prediction_or_semantic_hash",
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
        *count_names,
        *dynamic_bools,
        "raw_normalizer_observer_failure_type",
        "raw_normalizer_observation",
        "quote_aware_repair_failure_type",
        "quote_aware_repair_receipt",
        "public_export_failure_type",
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    entered = copied.get("raw_normalizer_observer_entry_count") == 1
    completed = copied.get("raw_normalizer_observer_completed_count") == 1
    observer_failed = copied.get("raw_normalizer_observer_failure_present") is True
    attempted = copied.get("quote_aware_repair_attempt_count") == 1
    applied = copied.get("quote_aware_repair_applied_count") == 1
    repair_failed = copied.get("quote_aware_repair_failure_present") is True
    export_attempted = copied.get("public_export_attempt_count") == 1
    export_completed = copied.get("public_export_completed_count") == 1
    export_failed = copied.get("public_export_failure_present") is True
    export_fallback = copied.get(
        "public_export_fallback_to_completed_production"
    ) is True
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_role") != parent.ROLE
        or copied.get("parent_policy_id") != parent.POLICY_ID
        or not isinstance(copied.get("parent_result_payload_sha256"), str)
        or len(copied["parent_result_payload_sha256"]) != 64
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in count_names
        )
        or any(not isinstance(copied.get(name), bool) for name in dynamic_bools)
        or copied["raw_normalizer_observer_entry_count"] != 1
        or completed is observer_failed
        or observer_failed
        and (
            not isinstance(copied.get("raw_normalizer_observer_failure_type"), str)
            or not copied["raw_normalizer_observer_failure_type"]
        )
        or not observer_failed
        and copied.get("raw_normalizer_observer_failure_type") is not None
        or completed
        and (
            not isinstance(observation, Mapping)
            or observer.validate_observation(observation) != dict(observation)
        )
        or not completed and observation is not None
        or attempted
        is not bool(
            completed
            and not observation["frozen_synthesis_contract_accepted"]
        )
        or applied and not attempted
        or repair_failed and not attempted
        or applied and repair_failed
        or copied["public_export_attempt_count"] not in {0, 1}
        or copied["public_export_completed_count"] not in {0, 1}
        or export_attempted is not applied
        or export_completed and not export_attempted
        or export_failed is not bool(export_attempted and not export_completed)
        or export_fallback is not export_failed
        or export_failed
        and (
            not isinstance(copied.get("public_export_failure_type"), str)
            or not copied["public_export_failure_type"]
        )
        or not export_failed
        and copied.get("public_export_failure_type") is not None
        or repair_failed
        and (
            not isinstance(copied.get("quote_aware_repair_failure_type"), str)
            or not copied["quote_aware_repair_failure_type"]
        )
        or not repair_failed
        and copied.get("quote_aware_repair_failure_type") is not None
        or applied
        and (
            not isinstance(repair_receipt, Mapping)
            or repair.validate_receipt(repair_receipt) != dict(repair_receipt)
            or copied["production_entity_cell_count"]
            != repair_receipt["internal_entity_cell_count"]
            or copied["production_entity_occurrence_count"]
            != repair_receipt["escaped_pipe_occurrence_count"]
            or not copied["parent_production_provider_output_valid"]
            or copied["parent_production_fallback_used"]
        )
        or not applied
        and (
            repair_receipt is not None
            or any(
                copied[name]
                for name in count_names
                if name
                not in {
                    "raw_normalizer_observer_entry_count",
                    "raw_normalizer_observer_completed_count",
                    "quote_aware_repair_attempt_count",
                    "quote_aware_repair_applied_count",
                    "public_export_attempt_count",
                    "public_export_completed_count",
                }
            )
            or copied["final_entity_coordinates_subset"]
            or copied["row_identity_order_shape_invariant"]
            or copied["candidate_publication_fallback"]
            or copied["public_export_fallback_to_completed_production"]
        )
        or export_failed and not copied["candidate_publication_fallback"]
        or copied["parent_production_fallback_used"]
        is copied["parent_production_provider_output_valid"]
        or copied["published_final_entity_cell_count"]
        > copied["production_entity_cell_count"]
        or copied["published_final_entity_occurrence_count"]
        > copied["production_entity_occurrence_count"]
        or copied["final_csv_quoted_cell_count"]
        < copied["published_final_entity_cell_count"]
        or copied["production_csv_quoted_cell_count"]
        < copied["production_entity_cell_count"]
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.80 quote-aware receipt drifted")
    if parent_result is not None:
        checked_parent = parent.validate_result(parent_result)
        sparse_receipt = checked_parent["parent_result"]["parent_result"][
            "content_free_receipt"
        ]
        if (
            copied["parent_result_payload_sha256"]
            != checked_parent["result_payload_sha256"]
            or copied["parent_production_provider_output_valid"]
            is not sparse_receipt["production_provider_output_valid"]
            or copied["parent_production_fallback_used"]
            is not sparse_receipt["production_fallback_used"]
        ):
            raise ValueError("V2.51.80 receipt-parent binding drifted")
    return copied


def run_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    limits: score.ScoreFirstLimits,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    visible = parent.parent.sparse_parent._validate_boundary(
        task, model=model, searches=searches, limits=limits
    )
    provider = QuoteAwareProductionProvider(
        model,
        question=visible["question"],
        first_wave_search=searches[FIRST_PHASE],
        limits=limits,
    )
    sparse_result = parent.parent.sparse_parent.validate_result(
        parent.parent.sparse_parent.run_task(
            visible,
            model=provider,
            searches=searches,
            limits=limits,
            monotonic=monotonic,
        )
    )
    internal_parent = _internal_parent_result(provider, sparse_result)
    production = internal_parent["production_prediction"]
    final = internal_parent["prediction"]
    diagnostics: dict[str, Any] | None = None
    public_export_attempt_count = 0
    public_export_completed_count = 0
    public_export_failure_type: str | None = None
    public_export_fallback_to_completed_production = False
    if provider.quote_aware_repair_applied_count:
        repair_receipt = repair.validate_receipt(
            provider.quote_aware_repair_receipt or {}
        )
        safe_public = provider.quote_aware_public_production
        if not isinstance(safe_public, str) or not safe_public:
            raise RuntimeError("V2.51.80 repair lost safe public production")
        production = final = safe_public
        public_export_attempt_count = 1
        try:
            canonical_safe = _safe_public_production(
                internal_parent["production_prediction"],
                expected_entity_cells=repair_receipt[
                    "internal_entity_cell_count"
                ],
                expected_entity_occurrences=repair_receipt[
                    "escaped_pipe_occurrence_count"
                ],
            )
            if safe_public != canonical_safe:
                raise ValueError("V2.51.80 safe public production drifted")
            production, final, diagnostics = export_public_predictions(
                internal_parent["production_prediction"],
                internal_parent["prediction"],
                columns=_canonical_internal_columns(
                    internal_parent["production_prediction"]
                ),
                expected_production_entity_cells=repair_receipt[
                    "internal_entity_cell_count"
                ],
                expected_production_entity_occurrences=repair_receipt[
                    "escaped_pipe_occurrence_count"
                ],
            )
            public_export_completed_count = 1
        except BaseException as exc:
            public_export_failure_type = _safe_failure(exc)
            public_export_fallback_to_completed_production = True
            diagnostics = _publication_failure_diagnostics(repair_receipt)
            production = final = safe_public
    receipt = _receipt(
        provider,
        internal_parent,
        diagnostics,
        public_export_attempt_count=public_export_attempt_count,
        public_export_completed_count=public_export_completed_count,
        public_export_failure_type=public_export_failure_type,
        public_export_fallback_to_completed_production=(
            public_export_fallback_to_completed_production
        ),
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": internal_parent["opaque_id"],
        "status": "terminal",
        "production_prediction": production,
        "production_prediction_sha256": hashlib.sha256(production.encode()).hexdigest(),
        "prediction": final,
        "prediction_sha256": hashlib.sha256(final.encode()).hexdigest(),
        "prediction_kind": internal_parent["prediction_kind"],
        "cost": copy.deepcopy(internal_parent["cost"]),
        "parent_result": copy.deepcopy(internal_parent),
        "parent_result_payload_sha256": internal_parent["result_payload_sha256"],
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
    receipt_raw = copied.get("content_free_receipt")
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
    production = copied.get("production_prediction")
    final = copied.get("prediction")
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("status") != "terminal"
        or not isinstance(production, str)
        or not production
        or not isinstance(final, str)
        or not final
        or copied.get("production_prediction_sha256")
        != hashlib.sha256(production.encode()).hexdigest()
        or copied.get("prediction_sha256")
        != hashlib.sha256(final.encode()).hexdigest()
        or not isinstance(parent_raw, Mapping)
        or not isinstance(receipt_raw, Mapping)
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
        raise ValueError("V2.51.80 result envelope drifted")
    checked_parent = parent.validate_result(parent_raw)
    receipt = validate_receipt(receipt_raw, parent_result=checked_parent)
    if receipt["quote_aware_repair_applied_count"]:
        repair_receipt = repair.validate_receipt(receipt["quote_aware_repair_receipt"])
        columns = _canonical_internal_columns(
            checked_parent["production_prediction"]
        )
        safe_production = _safe_public_production(
            checked_parent["production_prediction"],
            expected_entity_cells=repair_receipt["internal_entity_cell_count"],
            expected_entity_occurrences=repair_receipt[
                "escaped_pipe_occurrence_count"
            ],
        )
        if receipt["public_export_failure_present"]:
            expected_production = expected_final = safe_production
            diagnostics = _publication_failure_diagnostics(repair_receipt)
        else:
            expected_production, expected_final, diagnostics = (
                export_public_predictions(
                    checked_parent["production_prediction"],
                    checked_parent["prediction"],
                    columns=columns,
                    expected_production_entity_cells=repair_receipt[
                        "internal_entity_cell_count"
                    ],
                    expected_production_entity_occurrences=repair_receipt[
                        "escaped_pipe_occurrence_count"
                    ],
                )
            )
        if (
            production != expected_production
            or final != expected_final
            or any(receipt[name] != value for name, value in diagnostics.items())
        ):
            raise ValueError("V2.51.80 public export binding drifted")
    elif (
        production != checked_parent["production_prediction"]
        or final != checked_parent["prediction"]
    ):
        raise ValueError("V2.51.80 inactive repair changed prediction")
    if (
        copied["opaque_id"] != checked_parent["opaque_id"]
        or copied["prediction_kind"] != checked_parent["prediction_kind"]
        or copied["cost"] != checked_parent["cost"]
        or copied["parent_result_payload_sha256"]
        != checked_parent["result_payload_sha256"]
        or receipt["parent_result_payload_sha256"]
        != checked_parent["result_payload_sha256"]
    ):
        raise ValueError("V2.51.80 parent binding drifted")
    return copied


run_quote_aware_production_task = run_task


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
    "QuoteAwareProductionProvider",
    "export_public_predictions",
    "run_quote_aware_production_task",
    "run_task",
    "validate_receipt",
    "validate_result",
]
