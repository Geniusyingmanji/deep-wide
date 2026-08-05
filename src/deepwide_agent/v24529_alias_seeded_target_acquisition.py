"""Execution-scoped alias-seeded targeted acquisition.

V2.45.28 completed 8/8 workers and 99 fetches but produced zero alias-title
anchors.  This policy changes neither the number of logical queries, search
batches, nor fetches.  It derives a retrieval-only alias from the visible row
name, uses it in the existing two targeted queries, and prioritizes leads whose
visible title contains that alias before the frozen target/coverage ranking.

An alias match here is only an acquisition hint.  It receives no vote, source
credit, entropy credit, or decision credit.  The full V2.45.23 projector still
requires unique cross-row identity, explicit relation/label, one year, source
independence, posterior support, margin, leave-one-out information gain, and a
safe output change.
"""

from __future__ import annotations

import copy
import threading
from collections.abc import Mapping, Sequence
from contextlib import AbstractContextManager
from typing import Any

from . import v24490_entropy_targeted_support_search as targeted
from . import v24515_neutral_cell_discovery_planner as neutral
from . import v24523_conservative_alias_title_projection as alias
from .v24355_explicit_partition_runtime import _source_from_lead
from .v24371_batch_stratified_verifier_runtime import _coverage
from .v24378_adaptive_heldout_verifier_runtime import _lead_projection, _target_score


POLICY_ID = "v24529_visible_row_alias_seeded_target_acquisition_v1"
EXPECTED_BINDING_COUNT = 3
ORIGINAL_TARGETED_QUERY_VECTOR = targeted._query_vector
ORIGINAL_DISCOVERY_QUERY_VECTOR = neutral._discovery_query_vector
ORIGINAL_SELECT_TARGETED_LEADS = targeted._select_targeted_leads
RECEIPT_KEYS = frozenset(
    {
        "policy_id",
        "binding_count",
        "targeted_query_vector_calls",
        "discovery_query_vector_calls",
        "lead_selection_calls",
        "alias_seeded_query_vector_calls",
        "row_without_safe_alias_query_vector_calls",
        "visible_lead_count",
        "alias_title_hit_lead_count",
        "selected_lead_count",
        "selected_alias_title_hit_lead_count",
        "logical_queries_per_plan_unchanged",
        "search_batches_per_plan_unchanged",
        "maximum_fetches_per_plan_unchanged",
        "alias_derived_only_from_visible_row_text",
        "lead_priority_uses_visible_title_only",
        "alias_hint_receives_vote_or_source_entropy_or_decision_credit",
        "final_cross_row_identity_relation_year_source_posterior_margin_leave_one_out_and_safe_change_rules_unchanged",
        "cache_or_cross_task_state_used",
        "bindings_restored",
        "task_question_opaque_id_query_url_page_prediction_value_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy",
        "benchmark_launch_or_evaluator_authorized",
    }
)


def _count(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.45.29 {label} is invalid")
    return value


def _row_aliases(row: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    tokens = alias._canonical_tokens(row)
    candidates = tuple(
        (mode, tuple(surface))
        for mode, surface in alias._candidate_aliases(tokens)
        if mode != alias.ALIAS_MODES[0]
    )
    # Prefer a compact initialism; a two-token hybrid is the fallback for
    # member/campus names such as SUNY Geneseo.
    return tuple(
        sorted(
            candidates,
            key=lambda item: (
                0 if item[0] == alias.ALIAS_MODES[2] and len(item[1]) == 1 else 1,
                0 if item[0] == alias.ALIAS_MODES[2] else 1,
                len(item[1]),
                -sum(len(token) for token in item[1]),
                item[1],
            ),
        )
    )


def primary_alias_surface(row: str) -> str | None:
    aliases = _row_aliases(" ".join(str(row).split()).strip())
    if not aliases:
        return None
    return " ".join(aliases[0][1])


def alias_seeded_query_vector(
    row: str, column: str, alternative: str = ""
) -> list[str]:
    row = " ".join(str(row).split()).strip()
    column = " ".join(str(column).split()).strip()
    alternative = " ".join(str(alternative).split()).strip()
    if not row or not column:
        raise ValueError("V2.45.29 visible row or column is absent")
    surface = primary_alias_surface(row)
    if surface is None:
        if alternative:
            return ORIGINAL_TARGETED_QUERY_VECTOR(row, column, alternative)
        return ORIGINAL_DISCOVERY_QUERY_VECTOR(row, column)
    visible = row + column + alternative
    if any("\u4e00" <= character <= "\u9fff" for character in visible):
        suffixes = ("官方 校史 成立", "历史 档案 创立")
    else:
        suffixes = ("official history founded established", "historical archive founding")
    alternative_part = f' "{alternative}"' if alternative else ""
    queries = [
        f'"{surface}" "{column}"{alternative_part} {suffixes[0]}'[:1_200],
        f'"{row}" "{surface}" "{column}"{alternative_part} {suffixes[1]}'[:1_200],
    ]
    if any(not item for item in queries) or len({item.casefold() for item in queries}) != 2:
        raise ValueError("V2.45.29 alias query vector drifted")
    return queries


def _title_has_alias(title_text: str, row: str) -> bool:
    row_tokens = alias._canonical_tokens(row)
    title_tokens = alias._canonical_tokens(title_text)
    if not row_tokens or not title_tokens:
        return False
    for mode, surface in _row_aliases(row):
        start = alias.title._subsequence_start(title_tokens, surface)
        if (
            start is not None
            and start <= alias.MAXIMUM_ALIAS_MATCH_START
            and alias._type_compatible(
                row_tokens,
                title_tokens,
                mode=mode,
                alias_tokens=surface,
                start=start,
            )
        ):
            return True
    return False


def _select_alias_seeded_leads(
    leads: Sequence[Mapping[str, Any]],
    plan: Mapping[str, Any],
    *,
    excluded_sources: set[str],
) -> list[dict[str, str]]:
    available: dict[str, dict[str, str]] = {}
    for raw in leads:
        lead = _lead_projection(raw)
        source = _source_from_lead(lead)
        if source in excluded_sources or source in available:
            continue
        available[source] = lead
    row = str(plan["row_key"])
    target = {
        "row_key": row,
        "column": str(plan["column"]),
        "new_value": str(plan["leading_alternative"]),
    }
    ranked = sorted(
        available.values(),
        key=lambda lead: (
            not _title_has_alias(str(lead.get("title", "")), row),
            tuple(-number for number in _target_score(lead, [target])),
            tuple(-number for number in _coverage(lead, plan["query_vector"])[1]),
            _source_from_lead(lead),
        ),
    )
    return [
        copy.deepcopy(item)
        for item in ranked[: int(plan["maximum_targeted_fetches"])]
    ]


class AliasSeededTargetAcquisition(
    AbstractContextManager["AliasSeededTargetAcquisition"]
):
    """Patch exactly the query and lead-ranking surfaces for one execution."""

    def __init__(self) -> None:
        self._active = False
        self._lock = threading.RLock()
        self._restorations: list[tuple[Any, str, Any]] = []
        self._stats = {
            "targeted_query_vector_calls": 0,
            "discovery_query_vector_calls": 0,
            "lead_selection_calls": 0,
            "alias_seeded_query_vector_calls": 0,
            "row_without_safe_alias_query_vector_calls": 0,
            "visible_lead_count": 0,
            "alias_title_hit_lead_count": 0,
            "selected_lead_count": 0,
            "selected_alias_title_hit_lead_count": 0,
        }

    def _query(self, row: str, column: str, alternative: str) -> list[str]:
        with self._lock:
            self._stats["targeted_query_vector_calls"] += 1
            if primary_alias_surface(row) is None:
                self._stats["row_without_safe_alias_query_vector_calls"] += 1
            else:
                self._stats["alias_seeded_query_vector_calls"] += 1
            return alias_seeded_query_vector(row, column, alternative)

    def _discovery_query(self, row: str, column: str) -> list[str]:
        with self._lock:
            self._stats["discovery_query_vector_calls"] += 1
            if primary_alias_surface(row) is None:
                self._stats["row_without_safe_alias_query_vector_calls"] += 1
            else:
                self._stats["alias_seeded_query_vector_calls"] += 1
            return alias_seeded_query_vector(row, column)

    def _select(
        self,
        leads: Sequence[Mapping[str, Any]],
        plan: Mapping[str, Any],
        *,
        excluded_sources: set[str],
    ) -> list[dict[str, str]]:
        with self._lock:
            projected = [_lead_projection(item) for item in leads]
            row = str(plan["row_key"])
            selected = _select_alias_seeded_leads(
                projected, plan, excluded_sources=excluded_sources
            )
            self._stats["lead_selection_calls"] += 1
            self._stats["visible_lead_count"] += len(projected)
            self._stats["alias_title_hit_lead_count"] += sum(
                _title_has_alias(item["title"], row) for item in projected
            )
            self._stats["selected_lead_count"] += len(selected)
            self._stats["selected_alias_title_hit_lead_count"] += sum(
                _title_has_alias(item["title"], row) for item in selected
            )
            return selected

    def __enter__(self) -> "AliasSeededTargetAcquisition":
        if self._active:
            raise RuntimeError("V2.45.29 context is already active")
        bindings = (
            (targeted, "_query_vector", ORIGINAL_TARGETED_QUERY_VECTOR, self._query),
            (
                neutral,
                "_discovery_query_vector",
                ORIGINAL_DISCOVERY_QUERY_VECTOR,
                self._discovery_query,
            ),
            (
                targeted,
                "_select_targeted_leads",
                ORIGINAL_SELECT_TARGETED_LEADS,
                self._select,
            ),
        )
        if len(bindings) != EXPECTED_BINDING_COUNT or any(
            getattr(owner, name) is not expected
            for owner, name, expected, _replacement in bindings
        ):
            raise RuntimeError("V2.45.29 frozen acquisition binding drifted")
        try:
            for owner, name, expected, replacement in bindings:
                self._restorations.append((owner, name, expected))
                setattr(owner, name, replacement)
        except BaseException:
            self._restore()
            raise
        self._active = True
        return self

    def _restore(self) -> None:
        for owner, name, original in reversed(self._restorations):
            setattr(owner, name, original)
        self._restorations.clear()
        self._active = False

    def __exit__(self, *_: object) -> None:
        self._restore()

    def content_free_receipt(self) -> dict[str, Any]:
        return {
            "policy_id": POLICY_ID,
            "binding_count": EXPECTED_BINDING_COUNT,
            **dict(self._stats),
            "logical_queries_per_plan_unchanged": True,
            "search_batches_per_plan_unchanged": True,
            "maximum_fetches_per_plan_unchanged": True,
            "alias_derived_only_from_visible_row_text": True,
            "lead_priority_uses_visible_title_only": True,
            "alias_hint_receives_vote_or_source_entropy_or_decision_credit": False,
            "final_cross_row_identity_relation_year_source_posterior_margin_leave_one_out_and_safe_change_rules_unchanged": True,
            "cache_or_cross_task_state_used": False,
            "bindings_restored": not self._active and not self._restorations,
            "task_question_opaque_id_query_url_page_prediction_value_or_credential_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    counts = (
        "targeted_query_vector_calls",
        "discovery_query_vector_calls",
        "lead_selection_calls",
        "alias_seeded_query_vector_calls",
        "row_without_safe_alias_query_vector_calls",
        "visible_lead_count",
        "alias_title_hit_lead_count",
        "selected_lead_count",
        "selected_alias_title_hit_lead_count",
    )
    true_fields = (
        "logical_queries_per_plan_unchanged",
        "search_batches_per_plan_unchanged",
        "maximum_fetches_per_plan_unchanged",
        "alias_derived_only_from_visible_row_text",
        "lead_priority_uses_visible_title_only",
        "final_cross_row_identity_relation_year_source_posterior_margin_leave_one_out_and_safe_change_rules_unchanged",
        "bindings_restored",
    )
    false_fields = (
        "alias_hint_receives_vote_or_source_entropy_or_decision_credit",
        "cache_or_cross_task_state_used",
        "task_question_opaque_id_query_url_page_prediction_value_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("policy_id") != POLICY_ID
        or copied.get("binding_count") != EXPECTED_BINDING_COUNT
        or any(_count(copied.get(name), name) < 0 for name in counts)
        or copied["alias_seeded_query_vector_calls"]
        + copied["row_without_safe_alias_query_vector_calls"]
        != copied["targeted_query_vector_calls"]
        + copied["discovery_query_vector_calls"]
        or copied["alias_title_hit_lead_count"] > copied["visible_lead_count"]
        or copied["selected_lead_count"] > copied["visible_lead_count"]
        or copied["selected_alias_title_hit_lead_count"]
        > copied["selected_lead_count"]
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
    ):
        raise ValueError("V2.45.29 acquisition receipt drifted")
    return copied


__all__ = [
    "AliasSeededTargetAcquisition",
    "POLICY_ID",
    "alias_seeded_query_vector",
    "primary_alias_surface",
    "validate_receipt",
]
