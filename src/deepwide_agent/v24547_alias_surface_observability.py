"""Label-blind title/URL alias observability for targeted acquisition.

V2.45.45 observed no hit with the frozen title-only matcher.  This append-only
successor classifies visible title and normalized URL surfaces by full, core,
and initialism alias mode.  URL matching uses only hostname and decoded path;
query, fragment, userinfo, and port are excluded so an alias injected into a
search query cannot prove its own retrieval success.

Surface matches remain acquisition/ranking hints.  They receive no evidence,
source, entropy, or decision credit, and the frozen source/posterior/margin,
leave-one-out, safe-change, and decision-credit rules remain unchanged.
"""

from __future__ import annotations

import copy
import threading
from collections.abc import Mapping, Sequence
from contextlib import AbstractContextManager
from typing import Any
from urllib.parse import unquote, urlsplit

from . import v24490_entropy_targeted_support_search as targeted
from . import v24515_neutral_cell_discovery_planner as neutral
from . import v24523_conservative_alias_title_projection as alias
from . import v24529_alias_seeded_target_acquisition as predecessor
from .v24355_explicit_partition_runtime import _source_from_lead
from .v24371_batch_stratified_verifier_runtime import _coverage
from .v24378_adaptive_heldout_verifier_runtime import _lead_projection, _target_score


POLICY_ID = "v24547_visible_title_normalized_url_alias_observability_v1"
EXPECTED_BINDING_COUNT = 3
ORIGINAL_TARGETED_QUERY_VECTOR = targeted._query_vector
ORIGINAL_DISCOVERY_QUERY_VECTOR = neutral._discovery_query_vector
ORIGINAL_SELECT_TARGETED_LEADS = targeted._select_targeted_leads
MODE_NAMES = {
    alias.ALIAS_MODES[0]: "full_surface",
    alias.ALIAS_MODES[1]: "core_surface",
    alias.ALIAS_MODES[2]: "initialism",
}
SURFACES = ("title", "url")
MAXIMUM_URL_ALIAS_MATCH_START = 8


def _mode_field(surface: str, mode: str, *, selected: bool = False) -> str:
    prefix = "selected_" if selected else ""
    return f"{prefix}{surface}_{MODE_NAMES[mode]}_hit_lead_count"


MODE_COUNT_FIELDS = tuple(
    _mode_field(surface, mode, selected=selected)
    for selected in (False, True)
    for surface in SURFACES
    for mode in alias.ALIAS_MODES
)
UNION_COUNT_FIELDS = (
    "title_alias_surface_hit_lead_count",
    "url_alias_surface_hit_lead_count",
    "alias_surface_hit_lead_count",
    "query_only_alias_surface_lead_count",
    "selected_title_alias_surface_hit_lead_count",
    "selected_url_alias_surface_hit_lead_count",
    "selected_alias_surface_hit_lead_count",
    "selected_query_only_alias_surface_lead_count",
)
ACTIVITY_COUNT_FIELDS = (
    "targeted_query_vector_calls",
    "discovery_query_vector_calls",
    "lead_selection_calls",
    "alias_seeded_query_vector_calls",
    "row_without_safe_alias_query_vector_calls",
    "visible_lead_count",
    "selected_lead_count",
)
COUNT_FIELDS = (*ACTIVITY_COUNT_FIELDS, *MODE_COUNT_FIELDS, *UNION_COUNT_FIELDS)
RECEIPT_KEYS = frozenset(
    {
        "policy_id",
        "predecessor_policy_id",
        "binding_count",
        *COUNT_FIELDS,
        "logical_queries_per_plan_unchanged",
        "search_batches_per_plan_unchanged",
        "maximum_fetches_per_plan_unchanged",
        "alias_derived_only_from_visible_row_text",
        "lead_priority_uses_visible_title_and_normalized_url_only",
        "normalized_url_surface_excludes_query_fragment_userinfo_and_port",
        "query_text_used_to_establish_alias_hit",
        "query_only_alias_surface_receives_ranking_priority",
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
        raise ValueError(f"V2.45.47 {label} is invalid")
    return value


def _candidate_aliases(row: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    tokens = alias._canonical_tokens(" ".join(str(row).split()).strip())
    return tuple(
        (mode, tuple(surface))
        for mode, surface in alias._candidate_aliases(tokens)
        if mode in MODE_NAMES
    )


def _matching_modes(
    tokens: Sequence[str], row: str, *, maximum_start: int
) -> frozenset[str]:
    row_tokens = alias._canonical_tokens(row)
    if not row_tokens or not tokens:
        return frozenset()
    output: set[str] = set()
    for mode, surface in _candidate_aliases(row):
        start = alias.title._subsequence_start(tokens, surface)
        if (
            start is not None
            and start <= maximum_start
            and alias._type_compatible(
                row_tokens,
                tokens,
                mode=mode,
                alias_tokens=surface,
                start=start,
            )
        ):
            output.add(mode)
    return frozenset(output)


def _normalized_url_surface_tokens(raw_url: str) -> tuple[str, ...]:
    """Tokenize only public hostname/path, excluding self-proving query data."""

    try:
        parsed = urlsplit(str(raw_url))
    except ValueError:
        return ()
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
        return ()
    hostname = parsed.hostname.rstrip(".").casefold()
    if not hostname:
        return ()
    try:
        path = unquote(parsed.path or "/", errors="strict")
    except (UnicodeDecodeError, ValueError):
        return ()
    return alias._canonical_tokens(f"{hostname} {path}")


def classify_alias_surface(lead: Mapping[str, Any], row: str) -> dict[str, Any]:
    """Return fixed-vocabulary mode booleans without returning matched content."""

    title_modes = _matching_modes(
        alias._canonical_tokens(str(lead.get("title", ""))),
        row,
        maximum_start=alias.MAXIMUM_ALIAS_MATCH_START,
    )
    url_modes = _matching_modes(
        _normalized_url_surface_tokens(str(lead.get("url", ""))),
        row,
        maximum_start=MAXIMUM_URL_ALIAS_MATCH_START,
    )
    query_modes = _matching_modes(
        alias._canonical_tokens(str(lead.get("query", ""))),
        row,
        maximum_start=1_200,
    )
    surface_hit = bool(title_modes or url_modes)
    return {
        "title_modes": title_modes,
        "url_modes": url_modes,
        "surface_hit": surface_hit,
        "query_only": bool(query_modes) and not surface_hit,
    }


def _select_surface_seeded_leads(
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

    def rank(lead: Mapping[str, Any]) -> tuple[Any, ...]:
        match = classify_alias_surface(lead, row)
        return (
            not match["surface_hit"],
            not bool(match["title_modes"]),
            tuple(-number for number in _target_score(lead, [target])),
            tuple(-number for number in _coverage(lead, plan["query_vector"])[1]),
            _source_from_lead(lead),
        )

    ranked = sorted(available.values(), key=rank)
    return [
        copy.deepcopy(item)
        for item in ranked[: int(plan["maximum_targeted_fetches"])]
    ]


class AliasSurfaceObservability(
    AbstractContextManager["AliasSurfaceObservability"]
):
    """Patch query/ranking surfaces for exactly one execution."""

    def __init__(self) -> None:
        self._active = False
        self._lock = threading.RLock()
        self._restorations: list[tuple[Any, str, Any]] = []
        self._stats = {name: 0 for name in COUNT_FIELDS}

    def _query(self, row: str, column: str, alternative: str) -> list[str]:
        with self._lock:
            self._stats["targeted_query_vector_calls"] += 1
            if predecessor.primary_alias_surface(row) is None:
                self._stats["row_without_safe_alias_query_vector_calls"] += 1
            else:
                self._stats["alias_seeded_query_vector_calls"] += 1
            return predecessor.alias_seeded_query_vector(row, column, alternative)

    def _discovery_query(self, row: str, column: str) -> list[str]:
        with self._lock:
            self._stats["discovery_query_vector_calls"] += 1
            if predecessor.primary_alias_surface(row) is None:
                self._stats["row_without_safe_alias_query_vector_calls"] += 1
            else:
                self._stats["alias_seeded_query_vector_calls"] += 1
            return predecessor.alias_seeded_query_vector(row, column)

    def _record(self, prefix: str, match: Mapping[str, Any]) -> None:
        selected = prefix == "selected_"
        for surface in SURFACES:
            modes = match[f"{surface}_modes"]
            for mode in modes:
                self._stats[_mode_field(surface, mode, selected=selected)] += 1
            if modes:
                self._stats[f"{prefix}{surface}_alias_surface_hit_lead_count"] += 1
        if match["surface_hit"]:
            self._stats[f"{prefix}alias_surface_hit_lead_count"] += 1
        if match["query_only"]:
            self._stats[f"{prefix}query_only_alias_surface_lead_count"] += 1

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
            selected = _select_surface_seeded_leads(
                projected, plan, excluded_sources=excluded_sources
            )
            self._stats["lead_selection_calls"] += 1
            self._stats["visible_lead_count"] += len(projected)
            self._stats["selected_lead_count"] += len(selected)
            for item in projected:
                self._record("", classify_alias_surface(item, row))
            for item in selected:
                self._record("selected_", classify_alias_surface(item, row))
            return selected

    def __enter__(self) -> "AliasSurfaceObservability":
        if self._active:
            raise RuntimeError("V2.45.47 context is already active")
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
            raise RuntimeError("V2.45.47 frozen acquisition binding drifted")
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
            "predecessor_policy_id": predecessor.POLICY_ID,
            "binding_count": EXPECTED_BINDING_COUNT,
            **dict(self._stats),
            "logical_queries_per_plan_unchanged": True,
            "search_batches_per_plan_unchanged": True,
            "maximum_fetches_per_plan_unchanged": True,
            "alias_derived_only_from_visible_row_text": True,
            "lead_priority_uses_visible_title_and_normalized_url_only": True,
            "normalized_url_surface_excludes_query_fragment_userinfo_and_port": True,
            "query_text_used_to_establish_alias_hit": False,
            "query_only_alias_surface_receives_ranking_priority": False,
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
    true_fields = (
        "logical_queries_per_plan_unchanged",
        "search_batches_per_plan_unchanged",
        "maximum_fetches_per_plan_unchanged",
        "alias_derived_only_from_visible_row_text",
        "lead_priority_uses_visible_title_and_normalized_url_only",
        "normalized_url_surface_excludes_query_fragment_userinfo_and_port",
        "final_cross_row_identity_relation_year_source_posterior_margin_leave_one_out_and_safe_change_rules_unchanged",
        "bindings_restored",
    )
    false_fields = (
        "query_text_used_to_establish_alias_hit",
        "query_only_alias_surface_receives_ranking_priority",
        "alias_hint_receives_vote_or_source_entropy_or_decision_credit",
        "cache_or_cross_task_state_used",
        "task_question_opaque_id_query_url_page_prediction_value_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed_by_policy",
        "benchmark_launch_or_evaluator_authorized",
    )
    visible = copied.get("visible_lead_count", -1)
    selected = copied.get("selected_lead_count", -1)
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("policy_id") != POLICY_ID
        or copied.get("predecessor_policy_id") != predecessor.POLICY_ID
        or copied.get("binding_count") != EXPECTED_BINDING_COUNT
        or any(_count(copied.get(name), name) < 0 for name in COUNT_FIELDS)
        or copied["alias_seeded_query_vector_calls"]
        + copied["row_without_safe_alias_query_vector_calls"]
        != copied["targeted_query_vector_calls"]
        + copied["discovery_query_vector_calls"]
        or selected > visible
        or any(
            copied[_mode_field(surface, mode)]
            > copied[f"{surface}_alias_surface_hit_lead_count"]
            for surface in SURFACES
            for mode in alias.ALIAS_MODES
        )
        or any(
            copied[_mode_field(surface, mode, selected=True)]
            > copied[f"selected_{surface}_alias_surface_hit_lead_count"]
            for surface in SURFACES
            for mode in alias.ALIAS_MODES
        )
        or any(
            copied[name] > visible
            for name in (
                *MODE_COUNT_FIELDS[: len(MODE_COUNT_FIELDS) // 2],
                *UNION_COUNT_FIELDS[: len(UNION_COUNT_FIELDS) // 2],
            )
        )
        or any(
            copied[name] > selected
            for name in (
                *MODE_COUNT_FIELDS[len(MODE_COUNT_FIELDS) // 2 :],
                *UNION_COUNT_FIELDS[len(UNION_COUNT_FIELDS) // 2 :],
            )
        )
        or copied["title_alias_surface_hit_lead_count"]
        > copied["alias_surface_hit_lead_count"]
        or copied["url_alias_surface_hit_lead_count"]
        > copied["alias_surface_hit_lead_count"]
        or copied["selected_title_alias_surface_hit_lead_count"]
        > copied["selected_alias_surface_hit_lead_count"]
        or copied["selected_url_alias_surface_hit_lead_count"]
        > copied["selected_alias_surface_hit_lead_count"]
        or copied["query_only_alias_surface_lead_count"]
        + copied["alias_surface_hit_lead_count"]
        > visible
        or copied["selected_query_only_alias_surface_lead_count"]
        + copied["selected_alias_surface_hit_lead_count"]
        > selected
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
    ):
        raise ValueError("V2.45.47 alias surface receipt drifted")
    return copied


__all__ = [
    "ACTIVITY_COUNT_FIELDS",
    "AliasSurfaceObservability",
    "COUNT_FIELDS",
    "MODE_COUNT_FIELDS",
    "POLICY_ID",
    "UNION_COUNT_FIELDS",
    "classify_alias_surface",
    "validate_receipt",
]
