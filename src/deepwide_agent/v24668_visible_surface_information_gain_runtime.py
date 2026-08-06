"""Visible-surface information gain for strict Unknown-cell acquisition.

V2.46.64 found 399 independent targeted discovery sources and 38 usable pages,
but none of three proposals had two independent pages with exact local support
for the same value.  This successor changes only acquisition priority:

* select the first visible row-major Unknown cell (one target, not two);
* concentrate the unchanged four targeted fetches on that one target;
* before fetching, prefer each source's title/URL representative that is most
  aligned with the visible row key, then prefer aligned sources globally;
* quantify the localization information as ``log(N / M)`` nats, where ``N`` is
  the eligible independent-source count and ``M`` is the nonempty subset whose
  public title or normalized URL path aligns with the visible row surface.

The signal is action-level epistemic credit only.  Query text cannot prove its
own alignment, fetched page text remains the only active evidence, the proposal
is unchanged, and the strict two-independent-source exact-local support gate is
unchanged.  Decision credit remains zero until a safe change and post-freeze
outer utility are both observed.
"""

from __future__ import annotations

import copy
import math
import types
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import v24325_shared_prefix_revision_runtime as base
from . import v24547_alias_surface_observability as surface
from . import v24637_objective_alignment_runtime as paired
from . import v24655_unknown_cell_targeted_runtime as parent
from . import v24661_support_closure_task_runtime as strict
from .v24257_score_first_runtime import ScoreFirstLimits


POLICY_ID = "v24668_visible_surface_information_gain_acquisition_v1"
ROLE = "v24668_visible_surface_information_gain_task_result"
RECEIPT_ROLE = "v24668_visible_surface_information_gain_content_free_receipt"
ARMS = parent.ARMS
TARGET_CELL_CAP = 1
TARGET_FETCH_CAP = parent.TARGET_FETCH_CAP
MODE_ORDER = {
    "normalized_full_surface": 0,
    "distinctive_core_surface": 1,
    "visible_row_initialism": 2,
}
SELECTION_COUNT_FIELDS = (
    "visible_surface_selection_invocation_count",
    "visible_surface_input_lead_count",
    "visible_surface_eligible_source_count",
    "visible_surface_aligned_source_count",
    "visible_surface_selected_lead_count",
    "visible_surface_selected_aligned_lead_count",
    "visible_surface_source_representative_replacement_count",
    "visible_surface_title_aligned_source_count",
    "visible_surface_url_only_aligned_source_count",
)
SELECTION_FLOAT_FIELDS = (
    "visible_surface_prior_source_entropy_nats",
    "visible_surface_aligned_subset_entropy_nats",
    "visible_surface_localization_information_gain_nats",
    "epistemic_action_credit_nats",
)
SELECTION_FIELDS = frozenset(
    {
        *SELECTION_COUNT_FIELDS,
        *SELECTION_FLOAT_FIELDS,
        "selected_unknown_target_cap",
        "concentrated_targeted_fetch_cap",
        "one_stable_row_major_unknown_target_only",
        "all_targeted_fetch_capacity_concentrated_on_one_target",
        "visible_title_and_normalized_url_path_used_for_fetch_priority",
        "query_text_used_to_establish_surface_alignment",
        "url_query_fragment_userinfo_or_port_used_for_surface_alignment",
        "fetched_page_text_remains_only_active_support",
        "strict_two_independent_local_exact_support_gate_unchanged",
        "information_gain_routes_fetch_priority",
        "information_gain_uses_only_visible_pre_fetch_surfaces",
        "positive_epistemic_action_credit_assigned",
        "positive_decision_credit_assigned",
        "postfreeze_outer_utility_observed",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read_by_information_gain",
        "new_model_search_fetch_or_evaluator_effect_by_information_gain",
    }
)


def _mode_rank(modes: Sequence[str]) -> int:
    return min((MODE_ORDER.get(str(mode), len(MODE_ORDER)) for mode in modes), default=9)


def _lead_rank(lead: Mapping[str, Any], row_key: str) -> tuple[Any, ...]:
    match = surface.classify_alias_surface(lead, row_key)
    source = parent._source_from_url(lead.get("url")) or "~"
    return (
        not bool(match["surface_hit"]),
        not bool(match["title_modes"]),
        _mode_rank(tuple(match["title_modes"])),
        _mode_rank(tuple(match["url_modes"])),
        source,
        str(lead.get("url", "")),
        str(lead.get("title", "")),
    )


def select_visible_surface_information_gain_leads(
    batches: object,
    *,
    row_key: str,
    excluded_sources: set[str],
    excluded_urls: set[str],
    limit: int,
) -> tuple[list[dict[str, str]], set[str], dict[str, int | float]]:
    """Select source-diverse leads using only visible pre-fetch surfaces."""

    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
        raise ValueError("V2.46.68 lead limit drifted")
    if not str(row_key).strip():
        raise ValueError("V2.46.68 row key absent")
    if not isinstance(batches, Sequence) or isinstance(batches, (str, bytes)):
        raw: list[dict[str, str]] = []
    else:
        raw = base._lead_requests(
            [batch for batch in batches if isinstance(batch, Mapping)], 128
        )

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    first_by_source: dict[str, dict[str, str]] = {}
    input_count = 0
    for lead in raw:
        input_count += 1
        url = str(lead.get("url", ""))
        canonical = parent.canonicalize_url(url)
        source = parent._source_from_url(canonical)
        if (
            not canonical
            or source is None
            or source in excluded_sources
            or canonical in excluded_urls
        ):
            continue
        item = {**lead, "url": canonical}
        grouped[source].append(item)
        first_by_source.setdefault(source, item)

    representatives: dict[str, dict[str, str]] = {}
    replacements = 0
    for source, values in grouped.items():
        chosen = min(values, key=lambda value: _lead_rank(value, row_key))
        representatives[source] = chosen
        replacements += int(chosen != first_by_source[source])

    ranked = sorted(
        representatives.values(), key=lambda value: _lead_rank(value, row_key)
    )
    selected = [copy.deepcopy(item) for item in ranked[:limit]]
    matches = {
        source: surface.classify_alias_surface(lead, row_key)
        for source, lead in representatives.items()
    }
    aligned_sources = {
        source for source, match in matches.items() if bool(match["surface_hit"])
    }
    selected_matches = [surface.classify_alias_surface(item, row_key) for item in selected]
    eligible_count = len(representatives)
    aligned_count = len(aligned_sources)
    prior_entropy = math.log(eligible_count) if eligible_count else 0.0
    aligned_entropy = math.log(aligned_count) if aligned_count else prior_entropy
    localization_gain = max(0.0, prior_entropy - aligned_entropy)
    selected_aligned = sum(bool(match["surface_hit"]) for match in selected_matches)
    action_credit = localization_gain if selected_aligned else 0.0
    diagnostic: dict[str, int | float] = {
        "visible_surface_input_lead_count": input_count,
        "visible_surface_eligible_source_count": eligible_count,
        "visible_surface_aligned_source_count": aligned_count,
        "visible_surface_selected_lead_count": len(selected),
        "visible_surface_selected_aligned_lead_count": selected_aligned,
        "visible_surface_source_representative_replacement_count": replacements,
        "visible_surface_title_aligned_source_count": sum(
            bool(match["title_modes"]) for match in matches.values()
        ),
        "visible_surface_url_only_aligned_source_count": sum(
            bool(match["url_modes"]) and not bool(match["title_modes"])
            for match in matches.values()
        ),
        "visible_surface_prior_source_entropy_nats": round(prior_entropy, 12),
        "visible_surface_aligned_subset_entropy_nats": round(
            aligned_entropy, 12
        ),
        "visible_surface_localization_information_gain_nats": round(
            localization_gain, 12
        ),
        "epistemic_action_credit_nats": round(action_credit, 12),
    }
    return selected, set(representatives), diagnostic


def _isolated_parent_run(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits,
    monotonic: Callable[[], float],
    gate: Callable[..., tuple[str, list[dict[str, Any]], dict[str, int]]],
    selections: list[dict[str, int | float]],
) -> dict[str, Any]:
    state: dict[str, str] = {}

    def one_target(baseline: str, *, limit: int = TARGET_CELL_CAP) -> list[dict[str, Any]]:
        if limit != TARGET_CELL_CAP:
            raise ValueError("V2.46.68 target cap drifted")
        targets = parent.unknown_cell_targets(baseline, limit=TARGET_CELL_CAP)
        state.clear()
        if targets:
            state["row_key"] = str(targets[0]["row_key"])
        return targets

    def aligned_selection(
        batches: object,
        *,
        excluded_sources: set[str],
        excluded_urls: set[str],
        limit: int,
    ) -> tuple[list[dict[str, str]], set[str]]:
        row_key = state.get("row_key", "")
        selected, eligible, diagnostic = select_visible_surface_information_gain_leads(
            batches,
            row_key=row_key,
            excluded_sources=excluded_sources,
            excluded_urls=excluded_urls,
            limit=limit,
        )
        selections.append(diagnostic)
        return selected, eligible

    namespace = dict(vars(parent))
    namespace["_gate_unknown_candidate"] = gate
    namespace["unknown_cell_targets"] = one_target
    namespace["_selected_leads"] = aligned_selection
    namespace["TARGET_CELL_CAP"] = TARGET_CELL_CAP
    isolated = types.FunctionType(
        parent.run_v24655_task.__code__,
        namespace,
        name="run_v24668_isolated_parent_task",
        argdefs=parent.run_v24655_task.__defaults__,
        closure=parent.run_v24655_task.__closure__,
    )
    isolated.__kwdefaults__ = dict(parent.run_v24655_task.__kwdefaults__ or {})
    return isolated(
        task, model=model, search=search, limits=limits, monotonic=monotonic
    )


def run_v24668_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits,
    monotonic: Callable[[], float],
) -> dict[str, Any]:
    """Run the one-target acquisition policy with strict support closure."""

    interventions: list[dict[str, int]] = []
    selections: list[dict[str, int | float]] = []

    def gate(**kwargs: Any) -> tuple[str, list[dict[str, Any]], dict[str, int]]:
        _parent_candidate, _parent_admissions, parent_counts = (
            parent._gate_unknown_candidate(**kwargs)
        )
        candidate, admissions, closure_counts = (
            strict.gate_unknown_candidate_with_strict_support_closure(**kwargs)
        )
        parent_admitted = int(parent_counts["admitted_cell_change_count"])
        closure_admitted = int(closure_counts["admitted_cell_change_count"])
        if closure_admitted < parent_admitted:
            raise RuntimeError("V2.46.68 strict closure is not monotone")
        interventions.append(
            {
                "added": int(
                    closure_counts["support_closure_added_evidence_id_count"]
                ),
                "eligible": int(
                    closure_counts["support_closure_eligible_change_count"]
                ),
                "parent_admitted": parent_admitted,
                "closure_admitted": closure_admitted,
            }
        )
        return candidate, admissions, closure_counts

    parent_result = parent.validate_result(
        _isolated_parent_run(
            task,
            model=model,
            search=search,
            limits=limits,
            monotonic=monotonic,
            gate=gate,
            selections=selections,
        )
    )
    copied = copy.deepcopy(parent_result)
    copied["role"] = ROLE
    copied["policy_id"] = POLICY_ID
    receipt = copied["receipt"]
    receipt.pop("receipt_sha256", None)
    receipt["role"] = RECEIPT_ROLE
    receipt["policy_id"] = POLICY_ID
    parent_admitted = sum(item["parent_admitted"] for item in interventions)
    closure_admitted = sum(item["closure_admitted"] for item in interventions)
    receipt.update(
        {
            "support_closure_invocation_count": len(interventions),
            "support_closure_added_evidence_id_count": sum(
                item["added"] for item in interventions
            ),
            "support_closure_eligible_change_count": sum(
                item["eligible"] for item in interventions
            ),
            "counterfactual_parent_admitted_cell_change_count": parent_admitted,
            "strict_closure_admitted_cell_change_count": closure_admitted,
            "incremental_strict_closure_admitted_cell_change_count": (
                closure_admitted - parent_admitted
            ),
            "minimum_independent_support_sources": 2,
            "unresolved_declared_evidence_ids_preserved": True,
            "non_supporting_declared_evidence_ids_preserved": True,
            "uses_only_already_fetched_targeted_pages": True,
            "proposal_value_changed_by_closure": False,
            "support_threshold_relaxed": False,
            "new_model_search_fetch_or_evaluator_effect": False,
            "entropy_or_task_credit_used_by_closure": False,
            "v24659_design_only_precursor_superseded": True,
        }
    )
    for name in SELECTION_COUNT_FIELDS[1:]:
        receipt[name] = sum(int(item[name]) for item in selections)
    for name in SELECTION_FLOAT_FIELDS:
        receipt[name] = round(sum(float(item[name]) for item in selections), 12)
    receipt.update(
        {
            "visible_surface_selection_invocation_count": len(selections),
            "selected_unknown_target_cap": TARGET_CELL_CAP,
            "concentrated_targeted_fetch_cap": TARGET_FETCH_CAP,
            "one_stable_row_major_unknown_target_only": True,
            "all_targeted_fetch_capacity_concentrated_on_one_target": True,
            "visible_title_and_normalized_url_path_used_for_fetch_priority": True,
            "query_text_used_to_establish_surface_alignment": False,
            "url_query_fragment_userinfo_or_port_used_for_surface_alignment": False,
            "fetched_page_text_remains_only_active_support": True,
            "strict_two_independent_local_exact_support_gate_unchanged": True,
            "information_gain_routes_fetch_priority": True,
            "information_gain_uses_only_visible_pre_fetch_surfaces": True,
            "positive_epistemic_action_credit_assigned": receipt[
                "epistemic_action_credit_nats"
            ]
            > 0,
            "positive_decision_credit_assigned": False,
            "postfreeze_outer_utility_observed": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read_by_information_gain": False,
            "new_model_search_fetch_or_evaluator_effect_by_information_gain": False,
        }
    )
    receipt["receipt_sha256"] = paired.payload_sha256(receipt)
    copied.pop("result_sha256", None)
    copied["result_sha256"] = paired.payload_sha256(copied)
    return validate_result(copied)


def _strict_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    receipt = copied["receipt"]
    receipt.pop("receipt_sha256", None)
    for field in SELECTION_FIELDS:
        receipt.pop(field, None)
    receipt["role"] = strict.RECEIPT_ROLE
    receipt["policy_id"] = strict.POLICY_ID
    receipt["receipt_sha256"] = paired.payload_sha256(receipt)
    copied["role"] = strict.ROLE
    copied["policy_id"] = strict.POLICY_ID
    copied.pop("result_sha256", None)
    copied["result_sha256"] = paired.payload_sha256(copied)
    return strict.validate_result(copied)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    if any(
        isinstance(copied.get(name), bool)
        or not isinstance(copied.get(name), int)
        or copied.get(name, -1) < 0
        for name in SELECTION_COUNT_FIELDS
    ):
        raise ValueError("V2.46.68 selection count drifted")
    if any(
        isinstance(copied.get(name), bool)
        or not isinstance(copied.get(name), (int, float))
        or not math.isfinite(float(copied.get(name, -1)))
        or float(copied.get(name, -1)) < 0
        for name in SELECTION_FLOAT_FIELDS
    ):
        raise ValueError("V2.46.68 selection entropy drifted")
    eligible = copied["visible_surface_eligible_source_count"]
    aligned = copied["visible_surface_aligned_source_count"]
    selected = copied["visible_surface_selected_lead_count"]
    selected_aligned = copied["visible_surface_selected_aligned_lead_count"]
    expected_prior = math.log(eligible) if eligible else 0.0
    expected_aligned = math.log(aligned) if aligned else expected_prior
    expected_gain = max(0.0, expected_prior - expected_aligned)
    expected_credit = expected_gain if selected_aligned else 0.0
    true_fields = (
        "one_stable_row_major_unknown_target_only",
        "all_targeted_fetch_capacity_concentrated_on_one_target",
        "visible_title_and_normalized_url_path_used_for_fetch_priority",
        "fetched_page_text_remains_only_active_support",
        "strict_two_independent_local_exact_support_gate_unchanged",
        "information_gain_routes_fetch_priority",
        "information_gain_uses_only_visible_pre_fetch_surfaces",
    )
    false_fields = (
        "query_text_used_to_establish_surface_alignment",
        "url_query_fragment_userinfo_or_port_used_for_surface_alignment",
        "positive_decision_credit_assigned",
        "postfreeze_outer_utility_observed",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read_by_information_gain",
        "new_model_search_fetch_or_evaluator_effect_by_information_gain",
    )
    if (
        copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("selected_unknown_target_cap") != TARGET_CELL_CAP
        or copied.get("concentrated_targeted_fetch_cap") != TARGET_FETCH_CAP
        or copied["visible_surface_selection_invocation_count"] not in (0, 1)
        or aligned > eligible
        or selected > eligible
        or selected_aligned > selected
        or copied["visible_surface_title_aligned_source_count"] > aligned
        or copied["visible_surface_url_only_aligned_source_count"] > aligned
        or copied["visible_surface_source_representative_replacement_count"]
        > max(0, copied["visible_surface_input_lead_count"] - eligible)
        or copied.get("selected_unknown_target_count", -1) > TARGET_CELL_CAP
        or copied.get("targeted_logical_query_count", -1) > TARGET_CELL_CAP
        or copied.get("targeted_fetch_targets", -1) > TARGET_FETCH_CAP
        or selected
        != copied.get("targeted_selected_independent_source_count")
        or eligible
        != copied.get("targeted_discovered_independent_source_count")
        or not math.isclose(
            float(copied["visible_surface_prior_source_entropy_nats"]),
            expected_prior,
            abs_tol=1e-12,
        )
        or not math.isclose(
            float(copied["visible_surface_aligned_subset_entropy_nats"]),
            expected_aligned,
            abs_tol=1e-12,
        )
        or not math.isclose(
            float(copied["visible_surface_localization_information_gain_nats"]),
            expected_gain,
            abs_tol=1e-12,
        )
        or not math.isclose(
            float(copied["epistemic_action_credit_nats"]),
            expected_credit,
            abs_tol=1e-12,
        )
        or copied.get("positive_epistemic_action_credit_assigned")
        is not (expected_credit > 0)
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
        or seal != paired.payload_sha256(unsigned)
    ):
        raise ValueError("V2.46.68 information-gain receipt drifted")
    return copied


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_sha256", None)
    if (
        copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or seal != paired.payload_sha256(unsigned)
    ):
        raise ValueError("V2.46.68 result drifted")
    validate_receipt(copied.get("receipt", {}))
    _strict_projection(copied)
    return copied


__all__ = [
    "ARMS",
    "POLICY_ID",
    "ROLE",
    "run_v24668_task",
    "select_visible_surface_information_gain_leads",
    "validate_receipt",
    "validate_result",
]
