"""Budget-neutral title-query alignment with the frozen alias validator.

V2.45.87 preserved many same-source candidates but observed only three
title-surface hits, all from already excluded sources.  The inherited query
builder always combined the full visible name with one preferred alias; when
that alias was an initialism or hybrid, both constraints could make the query
more restrictive than any single title surface accepted by the unchanged
V2.45.23 validator.

This execution-scoped policy keeps exactly two logical queries.  Query one is
seeded by the validator's normalized full visible surface.  Query two is
seeded by its distinctive core, otherwise its initialism, otherwise the same
full surface with a distinct historical suffix.  The policy changes no search
batch, fetch, page, source, model, evidence, posterior, margin, leave-one-out,
safe-change, decision-credit, or evaluator rule.  A query surface remains a
retrieval hint and receives no evidence or credit.
"""

from __future__ import annotations

import copy
import threading
from collections.abc import Mapping
from contextlib import AbstractContextManager
from typing import Any

from . import v24523_conservative_alias_title_projection as validator
from . import v24529_alias_seeded_target_acquisition as acquisition


POLICY_ID = "v24589_budget_neutral_validator_aligned_title_query_v1"
EXPECTED_BINDING_COUNT = 1
ORIGINAL_ALIAS_SEEDED_QUERY_VECTOR = acquisition.alias_seeded_query_vector
_BINDING_GUARD = threading.Lock()

COUNT_FIELDS = (
    "query_vector_calls",
    "targeted_query_vector_calls",
    "discovery_query_vector_calls",
    "logical_query_count",
    "full_surface_first_query_calls",
    "distinctive_core_second_query_calls",
    "initialism_second_query_calls",
    "full_surface_fallback_second_query_calls",
)
RECEIPT_KEYS = frozenset(
    {
        "policy_id",
        "predecessor_policy_id",
        "binding_count",
        *COUNT_FIELDS,
        "exactly_two_logical_queries_per_call",
        "first_query_seed_is_frozen_validator_full_surface",
        "second_query_seed_is_frozen_validator_core_else_initialism_else_full",
        "query_seed_surfaces_are_derived_only_from_visible_row_text",
        "column_and_visible_alternative_remain_query_only_inputs",
        "logical_query_search_batch_fetch_page_source_and_model_budgets_unchanged",
        "title_alias_validator_and_evidence_projection_unchanged",
        "query_hint_receives_evidence_source_entropy_epistemic_or_decision_credit",
        "source_posterior_margin_leave_one_out_safe_change_and_decision_credit_rules_unchanged",
        "cache_or_cross_task_state_used",
        "bindings_restored",
        "task_question_opaque_id_query_url_title_page_prediction_value_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy",
        "benchmark_launch_or_evaluator_authorized",
    }
)


def _count(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.45.89 {label} is invalid")
    return value


def _visible(value: object, label: str, *, optional: bool = False) -> str:
    normalized = " ".join(str(value).split()).strip()
    if not normalized and not optional:
        raise ValueError(f"V2.45.89 visible {label} is absent")
    return normalized


def _surface_vector(row: str) -> tuple[str, str, str]:
    tokens = validator._canonical_tokens(row)
    candidates = validator._candidate_aliases(tokens)
    full = next(
        (surface for mode, surface in candidates if mode == validator.ALIAS_MODES[0]),
        None,
    )
    if full is None:
        raise ValueError("V2.45.89 validator full surface is absent")
    core = next(
        (surface for mode, surface in candidates if mode == validator.ALIAS_MODES[1]),
        None,
    )
    initialism = next(
        (surface for mode, surface in candidates if mode == validator.ALIAS_MODES[2]),
        None,
    )
    if core is not None and core != full:
        second, mode = core, "distinctive_core"
    elif initialism is not None and initialism != full:
        second, mode = initialism, "initialism"
    else:
        second, mode = full, "full_fallback"
    return " ".join(full), " ".join(second), mode


def validator_aligned_query_vector(
    row: str, column: str, alternative: str = ""
) -> list[str]:
    row = _visible(row, "row")
    column = _visible(column, "column")
    alternative = _visible(alternative, "alternative", optional=True)
    full, second, _mode = _surface_vector(row)
    visible = row + column + alternative
    if any("\u4e00" <= character <= "\u9fff" for character in visible):
        suffixes = ("官方 校史 成立", "历史 档案 创立")
    else:
        suffixes = (
            "official institutional history founded established",
            "historical archive founding established",
        )
    alternative_part = f' "{alternative}"' if alternative else ""
    queries = [
        f'"{full}" "{column}"{alternative_part} {suffixes[0]}'[:1_200],
        f'"{second}" "{column}"{alternative_part} {suffixes[1]}'[:1_200],
    ]
    if (
        any(not item for item in queries)
        or len(queries) != 2
        or len({item.casefold() for item in queries}) != 2
    ):
        raise ValueError("V2.45.89 validator-aligned query vector drifted")
    return queries


class ValidatorAlignedTitleQuery(
    AbstractContextManager["ValidatorAlignedTitleQuery"]
):
    """Install the two-query policy for exactly one worker call."""

    def __init__(self) -> None:
        self._active = False
        self._acquired = False
        self._installed: Any = None
        self._lock = threading.RLock()
        self._stats = {name: 0 for name in COUNT_FIELDS}

    def _query(
        self, row: str, column: str, alternative: str = ""
    ) -> list[str]:
        _full, _second, mode = _surface_vector(_visible(row, "row"))
        queries = validator_aligned_query_vector(row, column, alternative)
        with self._lock:
            self._stats["query_vector_calls"] += 1
            self._stats[
                "targeted_query_vector_calls"
                if _visible(alternative, "alternative", optional=True)
                else "discovery_query_vector_calls"
            ] += 1
            self._stats["logical_query_count"] += len(queries)
            self._stats["full_surface_first_query_calls"] += 1
            self._stats[f"{mode}_second_query_calls"] += 1
        return queries

    def __enter__(self) -> "ValidatorAlignedTitleQuery":
        if self._active or not _BINDING_GUARD.acquire(blocking=False):
            raise RuntimeError("V2.45.89 title-query context is already active")
        self._acquired = True
        if (
            acquisition.alias_seeded_query_vector
            is not ORIGINAL_ALIAS_SEEDED_QUERY_VECTOR
        ):
            _BINDING_GUARD.release()
            self._acquired = False
            raise RuntimeError("V2.45.89 frozen query binding drifted")
        self._installed = self._query
        acquisition.alias_seeded_query_vector = self._installed
        self._active = True
        return self

    def __exit__(self, *_: object) -> None:
        drifted = False
        try:
            if self._active:
                drifted = acquisition.alias_seeded_query_vector is not self._installed
                acquisition.alias_seeded_query_vector = (
                    ORIGINAL_ALIAS_SEEDED_QUERY_VECTOR
                )
                self._active = False
                self._installed = None
        finally:
            if self._acquired:
                self._acquired = False
                _BINDING_GUARD.release()
        if drifted:
            raise RuntimeError("V2.45.89 installed query binding drifted")

    def content_free_receipt(self) -> dict[str, Any]:
        return {
            "policy_id": POLICY_ID,
            "predecessor_policy_id": acquisition.POLICY_ID,
            "binding_count": EXPECTED_BINDING_COUNT,
            **dict(self._stats),
            "exactly_two_logical_queries_per_call": True,
            "first_query_seed_is_frozen_validator_full_surface": True,
            "second_query_seed_is_frozen_validator_core_else_initialism_else_full": True,
            "query_seed_surfaces_are_derived_only_from_visible_row_text": True,
            "column_and_visible_alternative_remain_query_only_inputs": True,
            "logical_query_search_batch_fetch_page_source_and_model_budgets_unchanged": True,
            "title_alias_validator_and_evidence_projection_unchanged": True,
            "query_hint_receives_evidence_source_entropy_epistemic_or_decision_credit": False,
            "source_posterior_margin_leave_one_out_safe_change_and_decision_credit_rules_unchanged": True,
            "cache_or_cross_task_state_used": False,
            "bindings_restored": not self._active and not self._acquired,
            "task_question_opaque_id_query_url_title_page_prediction_value_or_credential_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    true_fields = (
        "exactly_two_logical_queries_per_call",
        "first_query_seed_is_frozen_validator_full_surface",
        "second_query_seed_is_frozen_validator_core_else_initialism_else_full",
        "query_seed_surfaces_are_derived_only_from_visible_row_text",
        "column_and_visible_alternative_remain_query_only_inputs",
        "logical_query_search_batch_fetch_page_source_and_model_budgets_unchanged",
        "title_alias_validator_and_evidence_projection_unchanged",
        "source_posterior_margin_leave_one_out_safe_change_and_decision_credit_rules_unchanged",
        "bindings_restored",
    )
    false_fields = (
        "query_hint_receives_evidence_source_entropy_epistemic_or_decision_credit",
        "cache_or_cross_task_state_used",
        "task_question_opaque_id_query_url_title_page_prediction_value_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy",
        "benchmark_launch_or_evaluator_authorized",
    )
    calls = copied.get("query_vector_calls", -1)
    modes = (
        copied.get("distinctive_core_second_query_calls", -1)
        + copied.get("initialism_second_query_calls", -1)
        + copied.get("full_surface_fallback_second_query_calls", -1)
    )
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("policy_id") != POLICY_ID
        or copied.get("predecessor_policy_id") != acquisition.POLICY_ID
        or copied.get("binding_count") != EXPECTED_BINDING_COUNT
        or any(_count(copied.get(name), name) < 0 for name in COUNT_FIELDS)
        or calls
        != copied["targeted_query_vector_calls"]
        + copied["discovery_query_vector_calls"]
        or copied["logical_query_count"] != 2 * calls
        or copied["full_surface_first_query_calls"] != calls
        or modes != calls
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
    ):
        raise ValueError("V2.45.89 title-query receipt drifted")
    return copied


__all__ = [
    "COUNT_FIELDS",
    "POLICY_ID",
    "ValidatorAlignedTitleQuery",
    "validate_receipt",
    "validator_aligned_query_vector",
]
