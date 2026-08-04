"""Bounded adaptive support acquisition from frozen source-disjoint leads.

V2.44.52 externally falsified the assumption that one additional source is
generally sufficient to turn positive information gain into a safe decision:
all fourteen observed targets remained below the unchanged support threshold.
This append-only successor therefore starts with the unchanged V2.44.47 third
source and may fetch at most two more already-discovered, source-disjoint
leads (three additional fetches total relative to the V2.44.38 parent).

After each fetch, the frozen narrative projection and uncertainty update are
replayed.  A safe decision stops immediately.  Otherwise the runner stops
when the remaining fetch budget cannot satisfy even the minimum support-count
gate, when the frozen lead pool is exhausted, or when the three-fetch budget
is exhausted.  The known/unknown support, posterior, and margin thresholds are
unchanged.  No extra model request, logical query, search batch, or hosted
search provider call is allowed.

Information entropy has two deliberately separate roles.  Current unresolved
entropy plus visible title/query affinity prioritizes the next frozen lead.
Realized positive entropy reduction is recorded as order-dependent online
acquisition credit.  Final source credit remains the existing normalized
leave-one-out information gain, and decision credit remains zero unless the
unchanged safe-output gate is crossed.  Neither credit changes routing within
the already evaluated forward pass or authorizes training.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from . import v24390_uncertainty_active_evidence_runtime as runtime
from . import v24437_narrative_title_uncertainty_recovery as narrative_parent
from . import v24447_third_source_entropy_to_decision as parent
from .v24280_task_union_single_shot import validate_receipt as validate_search_receipt
from .v24312_deadline_reliability import validate_receipt as validate_model_receipt
from .v24316_deadline_search import validate_transport_health
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24325_shared_prefix_revision_runtime import _page_vector
from .v24333_programmatic_support_catalog import _source_key
from .v24355_explicit_partition_runtime import _source_from_lead
from .v24371_batch_stratified_verifier_runtime import _coverage
from .v24378_adaptive_heldout_verifier_runtime import _lead_projection, _target_score
from .v24388_uncertainty_credit import (
    KNOWN_ALTERNATIVE_MINIMUM_SOURCES,
    MINIMUM_ALTERNATIVE_POSTERIOR,
    UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES,
    apply_active_evidence,
    validate_active_evidence_result,
    validate_uncertainty_catalog,
)
from .v24397_failure_observability import build_failure_snapshot
from .v24399_failure_observable_runner import (
    FAILURE_NAME,
    MODEL_NAME,
    RESULT_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
    persist_failure_artifacts,
)
from .v24436_narrative_title_anchor_projection import (
    build_narrative_title_anchor_projection,
    validate_narrative_title_anchor_projection,
)


POLICY_ID = "v24457_bounded_adaptive_entropy_support_v1"
RESULT_ROLE = "v24457_adaptive_entropy_support_result"
RECEIPT_ROLE = "v24457_adaptive_entropy_support_receipt"
STEP_ROLE = "v24457_adaptive_entropy_support_step_receipt"
EFFECT_ROLE = "v24457_adaptive_fetch_effect_delta"
ENVELOPE_ROLE = "v24457_adaptive_entropy_support_envelope"
MAXIMUM_ADDITIONAL_FETCHES = 3
MAXIMUM_POST_THIRD_FETCHES = 2
MAXIMUM_ACTIVE_SOURCES = 5
PARENT_FETCH_CAP = 10
MAXIMUM_TOTAL_FETCHES = PARENT_FETCH_CAP + MAXIMUM_ADDITIONAL_FETCHES
PAGE_CHARACTER_CAP = 5_000
STOP_REASONS = frozenset(
    {
        "safe_decision",
        "support_unreachable",
        "lead_pool_exhausted",
        "budget_exhausted",
    }
)
PRIVATE_KEYS = frozenset(
    {
        "selected_adaptive_leads",
        "adaptive_fetch_batches",
        "adaptive_step_pages",
        "adaptive_step_receipts",
        "stop_reason",
    }
)
STEP_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "step_ordinal",
        "pre_combined_entropy_total_nats",
        "post_combined_entropy_total_nats",
        "signed_information_gain_nats",
        "positive_acquisition_credit_nats",
        "pre_safe_change_count",
        "post_safe_change_count",
        "pre_minimum_support_deficit",
        "post_minimum_support_deficit",
        "remaining_fetch_budget",
        "remaining_frozen_lead_count",
        "stop_reason_after_step",
        "first_step_reuses_frozen_parent_ranking",
        "later_step_uses_current_entropy_priority",
        "realized_information_gain_is_order_dependent_online_credit",
        "final_source_credit_uses_normalized_leave_one_out_information_gain",
        "decision_credit_requires_safe_output_change",
        "safe_change_thresholds_preserved",
        "question_query_url_page_prediction_candidate_value_source_or_content_hash_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_process_or_evaluator_accessed",
        "step_payload_sha256",
    }
)
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_result",
        "candidate_prediction",
        "adaptive_narrative_title_projection",
        "adaptive_active_evidence_result",
        "adaptive_private_state",
        "adaptive_support_receipt",
        "result_sha256",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_policy_id",
        "selected_target_count",
        "frozen_active_lead_count",
        "parent_selected_active_source_count",
        "adaptive_source_candidate_count",
        "adaptive_fetch_attempt_count",
        "adaptive_usable_page_count",
        "adaptive_positive_information_gain_step_count",
        "adaptive_safe_decision_step_count",
        "adaptive_acquisition_credit_total_nats",
        "adaptive_extended_novel_observation_count",
        "safe_change_count",
        "baseline_confirmed_count",
        "unresolved_count",
        "positive_epistemic_target_count",
        "source_credit_record_count",
        "candidate_changed_cell_count",
        "pre_active_entropy_total_nats",
        "final_combined_entropy_total_nats",
        "final_positive_information_gain_total_nats",
        "final_epistemic_credit_total_nats",
        "final_decision_credit_total_nats",
        "threshold_failure_partition",
        "known_baseline_minimum_support_sources",
        "unknown_baseline_minimum_support_sources",
        "minimum_alternative_posterior",
        "required_support_margin",
        "active_source_cap",
        "parent_total_fetch_cap",
        "maximum_additional_fetches",
        "additional_fetch_calls",
        "total_fetch_cap",
        "additional_model_requests",
        "additional_logical_queries",
        "additional_search_batches",
        "additional_provider_search_calls",
        "stop_reason",
        "frozen_source_disjoint_lead_pool_reused",
        "adaptive_stop_replayed_exactly",
        "safe_change_thresholds_preserved",
        "entropy_priority_uses_only_frozen_leads_and_current_validated_state",
        "realized_step_information_gain_is_order_dependent_online_credit",
        "final_source_credit_uses_normalized_leave_one_out_information_gain",
        "decision_credit_requires_safe_output_change",
        "allocated_credit_used_for_same_run_routing_or_training",
        "task_private_lead_page_observation_value_prediction_or_source_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)
EFFECT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "additional_fetch_attempt_count",
        "additional_model_acquisitions",
        "additional_model_attempts",
        "additional_hosted_search_attempts",
        "additional_hosted_search_deadline_failures",
        "additional_hard_fetch_helper_calls",
        "additional_fetch_deadline_rejections",
        "additional_hard_fetch_deadline_failures",
        "additional_fetch_helper_failures",
        "additional_fetch_effects",
        "model_effect_and_static_fields_equal",
        "model_remaining_seconds_nonincreasing",
        "model_deadline_state_monotonic",
        "search_shape_fields_equal",
        "transport_deadline_state_monotonic",
        "only_frozen_source_disjoint_page_fetch_effects_allowed",
        "question_prompt_response_query_url_page_prediction_candidate_value_or_source_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)
ENVELOPE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_envelope",
        "adaptive_result",
        "model_slot_receipt_before_adaptive_support",
        "transport_health_before_adaptive_support",
        "search_single_shot_receipt_before_adaptive_support",
        "model_slot_receipt",
        "transport_health",
        "search_single_shot_receipt",
        "effect_delta_receipt",
        "private_task_content_present",
        "private_task_content_emitted_to_public_aggregate",
        "credential_or_privileged_evaluator_content_present",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "envelope_payload_sha256",
    }
)


@dataclass(frozen=True)
class IntegratedAdaptiveEntropySupportOutcome:
    parent: parent.IntegratedThirdSourceOutcome
    adaptive_result: dict[str, Any]
    model_slot_receipt_before_adaptive_support: dict[str, Any]
    transport_health_before_adaptive_support: dict[str, Any]
    search_single_shot_receipt_before_adaptive_support: dict[str, Any]
    model_slot_receipt: dict[str, Any]
    transport_health: dict[str, Any]
    search_single_shot_receipt: dict[str, Any]
    effect_delta_receipt: dict[str, Any]


def _nonnegative_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.44.57 {label} is not a nonnegative integer")
    return value


def _finite(value: object, label: str, *, nonnegative: bool = True) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or nonnegative
        and float(value) < 0
    ):
        raise ValueError(f"V2.44.57 {label} is not finite")
    return float(value)


def _counter_delta(before: Mapping[str, Any], after: Mapping[str, Any], name: str) -> int:
    left = _nonnegative_integer(before.get(name), f"before {name}")
    right = _nonnegative_integer(after.get(name), f"after {name}")
    if right < left:
        raise ValueError(f"V2.44.57 {name} counter decreased")
    return right - left


def _original_parent_result(parent_result: Mapping[str, Any]) -> dict[str, Any]:
    validated = parent.validate_result(parent_result)
    return narrative_parent.validate_result(validated["parent_result"])


def _selected_identities(catalog: Mapping[str, Any]) -> set[tuple[str, str]]:
    return {
        runtime._target_identity(item["row_key"], item["column"])
        for item in runtime._selected_targets(catalog)
    }


def _snapshot(
    original_parent_result: Mapping[str, Any],
    adaptive_pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    validated_parent = narrative_parent.validate_result(original_parent_result)
    anchored = validated_parent["parent_result"]
    structured = anchored["parent_result"]
    legacy = structured["parent_result"]
    baseline = str(legacy["baseline_prediction"])
    private = legacy["private_replay_state"]
    catalog = validate_uncertainty_catalog(private["uncertainty_catalog"])
    original_pages = list(private["active_pages"])
    projection = build_narrative_title_anchor_projection(
        baseline,
        [*original_pages, *copy.deepcopy(list(adaptive_pages))],
        selected_identities=_selected_identities(catalog),
    )
    validate_narrative_title_anchor_projection(projection)
    active = apply_active_evidence(catalog, projection["observations"])
    validate_active_evidence_result(active)
    candidate, _ = runtime._merge_parent_candidate(legacy["parent_result"], active)
    partition = parent.threshold_failure_partition(active)
    return {
        "baseline_prediction": baseline,
        "candidate_prediction": candidate,
        "catalog": catalog,
        "original_pages": copy.deepcopy(original_pages),
        "projection": projection,
        "active": active,
        "threshold_failure_partition": partition,
    }


def _minimum_support_deficit(snapshot: Mapping[str, Any]) -> int:
    active = snapshot["active"]
    targets = {
        str(item["target_binding_sha256"]): item
        for item in active["catalog"]["targets"]
    }
    deficits: list[int] = []
    for resolution in active["resolutions"]:
        if resolution["status"] == "safe_change":
            return 0
        target = targets[str(resolution["target_binding_sha256"])]
        required = (
            UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES
            if target["baseline_unknown"]
            else KNOWN_ALTERNATIVE_MINIMUM_SOURCES
        )
        deficits.append(
            max(0, required - int(resolution["selected_alternative_support_count"]))
        )
    return min(deficits, default=MAXIMUM_ADDITIONAL_FETCHES + 1)


def _entropy_priority(
    lead: Mapping[str, Any], snapshot: Mapping[str, Any]
) -> tuple[int, ...]:
    active = snapshot["active"]
    catalog = active["catalog"]
    targets = {
        str(item["target_binding_sha256"]): item for item in catalog["targets"]
    }
    query_by_binding = dict(
        zip(
            catalog["selected_target_binding_sha256s"],
            catalog["active_queries"],
            strict=True,
        )
    )
    priorities: list[tuple[int, ...]] = []
    for resolution in active["resolutions"]:
        if resolution["status"] == "safe_change":
            continue
        binding = str(resolution["target_binding_sha256"])
        target = targets[binding]
        required = (
            UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES
            if target["baseline_unknown"]
            else KNOWN_ALTERNATIVE_MINIMUM_SOURCES
        )
        deficit = max(
            0, required - int(resolution["selected_alternative_support_count"])
        )
        affinity = _target_score(
            lead,
            [
                {
                    "row_key": target["row_key"],
                    "column": target["column"],
                    "new_value": "",
                }
            ],
        )
        coverage = _coverage(lead, [query_by_binding[binding]])[1]
        priorities.append(
            (
                int(round(float(resolution["combined_entropy_nats"]) * 10**12)),
                -deficit,
                *map(int, affinity),
                *map(int, coverage),
            )
        )
    return max(priorities, default=(0,) * 11)


def _remaining_ranked_leads(
    original_parent_result: Mapping[str, Any],
    selected: Sequence[Mapping[str, Any]],
    snapshot: Mapping[str, Any],
) -> list[dict[str, str]]:
    chosen = {_source_from_lead(item) for item in selected}
    remaining = [
        _lead_projection(item)
        for item in parent._ranked_active_leads(original_parent_result)
        if _source_from_lead(item) not in chosen
    ]
    return sorted(
        remaining,
        key=lambda lead: (
            tuple(-number for number in _entropy_priority(lead, snapshot)),
            _source_from_lead(lead),
        ),
    )


def _stop_reason(
    snapshot: Mapping[str, Any],
    *,
    attempted: int,
    remaining_lead_count: int,
) -> str | None:
    if int(snapshot["active"]["receipt"]["safe_change_count"]) > 0:
        return "safe_decision"
    if attempted >= MAXIMUM_ADDITIONAL_FETCHES:
        return "budget_exhausted"
    if remaining_lead_count <= 0:
        return "lead_pool_exhausted"
    remaining_budget = min(
        MAXIMUM_ADDITIONAL_FETCHES - attempted, remaining_lead_count
    )
    if _minimum_support_deficit(snapshot) > remaining_budget:
        return "support_unreachable"
    return None


def build_step_receipt(
    *,
    step_ordinal: int,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    remaining_fetch_budget: int,
    remaining_frozen_lead_count: int,
    stop_reason_after_step: str | None,
) -> dict[str, Any]:
    pre_entropy = float(before["active"]["receipt"]["combined_entropy_total_nats"])
    post_entropy = float(after["active"]["receipt"]["combined_entropy_total_nats"])
    signed = pre_entropy - post_entropy
    if (
        isinstance(step_ordinal, bool)
        or not isinstance(step_ordinal, int)
        or not 1 <= step_ordinal <= MAXIMUM_ADDITIONAL_FETCHES
        or isinstance(remaining_fetch_budget, bool)
        or not isinstance(remaining_fetch_budget, int)
        or not 0 <= remaining_fetch_budget <= MAXIMUM_ADDITIONAL_FETCHES - step_ordinal
        or isinstance(remaining_frozen_lead_count, bool)
        or not isinstance(remaining_frozen_lead_count, int)
        or remaining_frozen_lead_count < 0
        or stop_reason_after_step is not None
        and stop_reason_after_step not in STOP_REASONS
    ):
        raise ValueError("V2.44.57 step contract drifted")
    value = {
        "artifact_version": 1,
        "role": STEP_ROLE,
        "policy_id": POLICY_ID,
        "step_ordinal": step_ordinal,
        "pre_combined_entropy_total_nats": round(pre_entropy, 12),
        "post_combined_entropy_total_nats": round(post_entropy, 12),
        "signed_information_gain_nats": round(signed, 12),
        "positive_acquisition_credit_nats": round(max(0.0, signed), 12),
        "pre_safe_change_count": int(before["active"]["receipt"]["safe_change_count"]),
        "post_safe_change_count": int(after["active"]["receipt"]["safe_change_count"]),
        "pre_minimum_support_deficit": _minimum_support_deficit(before),
        "post_minimum_support_deficit": _minimum_support_deficit(after),
        "remaining_fetch_budget": remaining_fetch_budget,
        "remaining_frozen_lead_count": remaining_frozen_lead_count,
        "stop_reason_after_step": stop_reason_after_step,
        "first_step_reuses_frozen_parent_ranking": step_ordinal == 1,
        "later_step_uses_current_entropy_priority": step_ordinal > 1,
        "realized_information_gain_is_order_dependent_online_credit": True,
        "final_source_credit_uses_normalized_leave_one_out_information_gain": True,
        "decision_credit_requires_safe_output_change": True,
        "safe_change_thresholds_preserved": True,
        "question_query_url_page_prediction_candidate_value_source_or_content_hash_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_process_or_evaluator_accessed": False,
    }
    value["step_payload_sha256"] = payload_sha256(value)
    validate_step_receipt(value)
    return value


def validate_step_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("step_payload_sha256", None)
    step = copied.get("step_ordinal")
    numeric = (
        "pre_combined_entropy_total_nats",
        "post_combined_entropy_total_nats",
        "positive_acquisition_credit_nats",
    )
    counts = (
        "pre_safe_change_count",
        "post_safe_change_count",
        "pre_minimum_support_deficit",
        "post_minimum_support_deficit",
        "remaining_fetch_budget",
        "remaining_frozen_lead_count",
    )
    signed = copied.get("signed_information_gain_nats")
    if (
        set(copied) != STEP_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != STEP_ROLE
        or copied.get("policy_id") != POLICY_ID
        or isinstance(step, bool)
        or not isinstance(step, int)
        or not 1 <= step <= MAXIMUM_ADDITIONAL_FETCHES
        or any(_finite(copied.get(name), name) < 0 for name in numeric)
        or _finite(signed, "signed IG", nonnegative=False) != float(signed)
        or any(_nonnegative_integer(copied.get(name), name) < 0 for name in counts)
        or copied.get("remaining_fetch_budget") > MAXIMUM_ADDITIONAL_FETCHES - step
        or not math.isclose(
            float(copied["signed_information_gain_nats"]),
            float(copied["pre_combined_entropy_total_nats"])
            - float(copied["post_combined_entropy_total_nats"]),
            abs_tol=2e-12,
        )
        or not math.isclose(
            float(copied["positive_acquisition_credit_nats"]),
            max(0.0, float(copied["signed_information_gain_nats"])),
            abs_tol=2e-12,
        )
        or copied.get("stop_reason_after_step") is not None
        and copied.get("stop_reason_after_step") not in STOP_REASONS
        or copied.get("first_step_reuses_frozen_parent_ranking")
        is not (step == 1)
        or copied.get("later_step_uses_current_entropy_priority")
        is not (step > 1)
        or any(
            copied.get(name) is not True
            for name in (
                "realized_information_gain_is_order_dependent_online_credit",
                "final_source_credit_uses_normalized_leave_one_out_information_gain",
                "decision_credit_requires_safe_output_change",
                "safe_change_thresholds_preserved",
            )
        )
        or any(
            copied.get(name) is not False
            for name in (
                "question_query_url_page_prediction_candidate_value_source_or_content_hash_emitted",
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
                "file_environment_network_model_search_process_or_evaluator_accessed",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.57 step receipt drifted")
    return copy.deepcopy(copied)


def _rebuild_step_pages(
    batches: Sequence[Mapping[str, Any]],
    *,
    step_ordinal: int,
    lead: Mapping[str, Any],
) -> list[dict[str, Any]]:
    prefix = "T" if step_ordinal == 1 else f"U{step_ordinal}"
    pages = _page_vector(batches, prefix=prefix, page_chars=PAGE_CHARACTER_CAP)
    if len(pages) > 1:
        raise ValueError("V2.44.57 adaptive fetch returned multiple usable pages")
    source = _source_from_lead(lead)
    if pages and any(_source_key(str(page["host"])) != source for page in pages):
        pages = []
    return copy.deepcopy(pages)


def _canonical_private_state(
    parent_result: Mapping[str, Any], value: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    validated_parent = parent.validate_result(parent_result)
    if set(value) != PRIVATE_KEYS:
        raise ValueError("V2.44.57 private state keys drifted")
    leads = value.get("selected_adaptive_leads")
    batches = value.get("adaptive_fetch_batches")
    pages = value.get("adaptive_step_pages")
    steps = value.get("adaptive_step_receipts")
    stop = value.get("stop_reason")
    if (
        not isinstance(leads, list)
        or not isinstance(batches, list)
        or not isinstance(pages, list)
        or not isinstance(steps, list)
        or not (len(leads) == len(batches) == len(pages) == len(steps))
        or len(leads) > MAXIMUM_ADDITIONAL_FETCHES
        or stop not in STOP_REASONS
    ):
        raise ValueError("V2.44.57 adaptive private vector drifted")
    original = _original_parent_result(validated_parent)
    first_private = validated_parent["third_source_private_state"]
    expected_first = first_private["selected_third_lead"]
    if expected_first is None:
        final = _snapshot(original, [])
        expected_stop = _stop_reason(
            final, attempted=0, remaining_lead_count=0
        )
        if (
            leads
            or batches
            or pages
            or steps
            or stop != expected_stop
        ):
            raise ValueError("V2.44.57 absent inherited lead drifted")
        return {
            "selected_adaptive_leads": [],
            "adaptive_fetch_batches": [],
            "adaptive_step_pages": [],
            "adaptive_step_receipts": [],
            "stop_reason": stop,
        }, final
    if not leads:
        raise ValueError("V2.44.57 inherited third-source step is absent")
    canonical_leads: list[dict[str, str]] = []
    canonical_batches: list[list[dict[str, Any]]] = []
    canonical_pages: list[list[dict[str, Any]]] = []
    canonical_steps: list[dict[str, Any]] = []
    flattened_pages: list[dict[str, Any]] = []
    before = _snapshot(original, flattened_pages)
    for index, (raw_lead, raw_batches, raw_pages, raw_step) in enumerate(
        zip(leads, batches, pages, steps, strict=True), start=1
    ):
        if not isinstance(raw_lead, Mapping) or not isinstance(raw_batches, list) or not isinstance(raw_pages, list):
            raise ValueError("V2.44.57 adaptive step artifact schema drifted")
        lead = _lead_projection(raw_lead)
        if index == 1:
            expected = _lead_projection(expected_first)
            if raw_batches != first_private["third_fetch_batches"]:
                raise ValueError("V2.44.57 inherited third fetch drifted")
        else:
            remaining = _remaining_ranked_leads(original, canonical_leads, before)
            expected = remaining[0] if remaining else None
        if expected is None or lead != expected:
            raise ValueError("V2.44.57 adaptive entropy lead selection drifted")
        rebuilt = _rebuild_step_pages(raw_batches, step_ordinal=index, lead=lead)
        if index == 1 and rebuilt != first_private["third_pages"]:
            raise ValueError("V2.44.57 inherited third page drifted")
        if raw_pages != rebuilt:
            raise ValueError("V2.44.57 adaptive page replay drifted")
        canonical_leads.append(lead)
        canonical_batches.append(copy.deepcopy(raw_batches))
        canonical_pages.append(rebuilt)
        flattened_pages.extend(rebuilt)
        after = _snapshot(original, flattened_pages)
        remaining = _remaining_ranked_leads(original, canonical_leads, after)
        reason = _stop_reason(
            after, attempted=index, remaining_lead_count=len(remaining)
        )
        expected_step = build_step_receipt(
            step_ordinal=index,
            before=before,
            after=after,
            remaining_fetch_budget=MAXIMUM_ADDITIONAL_FETCHES - index,
            remaining_frozen_lead_count=len(remaining),
            stop_reason_after_step=reason,
        )
        if validate_step_receipt(raw_step) != expected_step:
            raise ValueError("V2.44.57 adaptive step receipt replay drifted")
        canonical_steps.append(expected_step)
        if reason is not None and index != len(leads):
            raise ValueError("V2.44.57 adaptive fetch continued after stop")
        if reason is None and index == len(leads):
            raise ValueError("V2.44.57 adaptive fetch stopped without reason")
        before = after
    if canonical_steps[-1]["stop_reason_after_step"] != stop:
        raise ValueError("V2.44.57 final stop reason drifted")
    return {
        "selected_adaptive_leads": canonical_leads,
        "adaptive_fetch_batches": canonical_batches,
        "adaptive_step_pages": canonical_pages,
        "adaptive_step_receipts": canonical_steps,
        "stop_reason": stop,
    }, before


def _compute_result(
    parent_result: Mapping[str, Any], private_state: Mapping[str, Any]
) -> dict[str, Any]:
    validated_parent = parent.validate_result(parent_result)
    private, snapshot = _canonical_private_state(validated_parent, private_state)
    active = snapshot["active"]
    entropy = active["receipt"]
    baseline = snapshot["baseline_prediction"]
    candidate = snapshot["candidate_prediction"]
    changes = runtime._changed_cells(baseline, candidate)
    parent_observations = {
        runtime._target_identity(item["row_key"], item["column"])
        + (str(item["source_host"]), str(item["value"]))
        for item in build_narrative_title_anchor_projection(
            baseline,
            snapshot["original_pages"],
            selected_identities=_selected_identities(snapshot["catalog"]),
        )["observations"]
    }
    novel = sum(
        runtime._target_identity(item["row_key"], item["column"])
        + (str(item["source_host"]), str(item["value"]))
        not in parent_observations
        for item in snapshot["projection"]["observations"]
    )
    steps = private["adaptive_step_receipts"]
    receipt = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "selected_target_count": int(entropy["selected_target_count"]),
        "frozen_active_lead_count": len(parent._ranked_active_leads(_original_parent_result(validated_parent))),
        "parent_selected_active_source_count": int(
            validated_parent["third_source_recovery_receipt"][
                "parent_selected_active_source_count"
            ]
        ),
        "adaptive_source_candidate_count": len(
            parent._ranked_active_leads(_original_parent_result(validated_parent))
        )
        - int(
            validated_parent["third_source_recovery_receipt"][
                "parent_selected_active_source_count"
            ]
        ),
        "adaptive_fetch_attempt_count": len(private["selected_adaptive_leads"]),
        "adaptive_usable_page_count": sum(len(item) for item in private["adaptive_step_pages"]),
        "adaptive_positive_information_gain_step_count": sum(
            float(item["positive_acquisition_credit_nats"]) > 0 for item in steps
        ),
        "adaptive_safe_decision_step_count": sum(
            int(item["post_safe_change_count"]) > int(item["pre_safe_change_count"])
            for item in steps
        ),
        "adaptive_acquisition_credit_total_nats": round(
            sum(float(item["positive_acquisition_credit_nats"]) for item in steps), 12
        ),
        "adaptive_extended_novel_observation_count": int(novel),
        "safe_change_count": int(entropy["safe_change_count"]),
        "baseline_confirmed_count": int(entropy["baseline_confirmed_count"]),
        "unresolved_count": int(entropy["unresolved_count"]),
        "positive_epistemic_target_count": int(entropy["positive_epistemic_target_count"]),
        "source_credit_record_count": int(entropy["source_credit_record_count"]),
        "candidate_changed_cell_count": len(changes),
        "pre_active_entropy_total_nats": float(entropy["pre_active_entropy_total_nats"]),
        "final_combined_entropy_total_nats": float(entropy["combined_entropy_total_nats"]),
        "final_positive_information_gain_total_nats": float(entropy["positive_information_gain_total_nats"]),
        "final_epistemic_credit_total_nats": float(entropy["epistemic_credit_total_nats"]),
        "final_decision_credit_total_nats": float(entropy["decision_credit_total_nats"]),
        "threshold_failure_partition": snapshot["threshold_failure_partition"],
        "known_baseline_minimum_support_sources": KNOWN_ALTERNATIVE_MINIMUM_SOURCES,
        "unknown_baseline_minimum_support_sources": UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES,
        "minimum_alternative_posterior": MINIMUM_ALTERNATIVE_POSTERIOR,
        "required_support_margin": 1,
        "active_source_cap": MAXIMUM_ACTIVE_SOURCES,
        "parent_total_fetch_cap": PARENT_FETCH_CAP,
        "maximum_additional_fetches": MAXIMUM_ADDITIONAL_FETCHES,
        "additional_fetch_calls": len(private["selected_adaptive_leads"]),
        "total_fetch_cap": MAXIMUM_TOTAL_FETCHES,
        "additional_model_requests": 0,
        "additional_logical_queries": 0,
        "additional_search_batches": 0,
        "additional_provider_search_calls": 0,
        "stop_reason": private["stop_reason"],
        "frozen_source_disjoint_lead_pool_reused": True,
        "adaptive_stop_replayed_exactly": True,
        "safe_change_thresholds_preserved": True,
        "entropy_priority_uses_only_frozen_leads_and_current_validated_state": True,
        "realized_step_information_gain_is_order_dependent_online_credit": True,
        "final_source_credit_uses_normalized_leave_one_out_information_gain": True,
        "decision_credit_requires_safe_output_change": True,
        "allocated_credit_used_for_same_run_routing_or_training": False,
        "task_private_lead_page_observation_value_prediction_or_source_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_sha256"] = payload_sha256(receipt)
    value = {
        "artifact_version": 1,
        "role": RESULT_ROLE,
        "policy_id": POLICY_ID,
        "parent_result": copy.deepcopy(validated_parent),
        "candidate_prediction": candidate,
        "adaptive_narrative_title_projection": snapshot["projection"],
        "adaptive_active_evidence_result": active,
        "adaptive_private_state": private,
        "adaptive_support_receipt": receipt,
    }
    value["result_sha256"] = payload_sha256(value)
    return value


def validate_recovery_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    partition = copied.get("threshold_failure_partition")
    count_fields = (
        "selected_target_count",
        "frozen_active_lead_count",
        "parent_selected_active_source_count",
        "adaptive_source_candidate_count",
        "adaptive_fetch_attempt_count",
        "adaptive_usable_page_count",
        "adaptive_positive_information_gain_step_count",
        "adaptive_safe_decision_step_count",
        "adaptive_extended_novel_observation_count",
        "safe_change_count",
        "baseline_confirmed_count",
        "unresolved_count",
        "positive_epistemic_target_count",
        "source_credit_record_count",
        "candidate_changed_cell_count",
        "known_baseline_minimum_support_sources",
        "unknown_baseline_minimum_support_sources",
        "required_support_margin",
        "active_source_cap",
        "parent_total_fetch_cap",
        "maximum_additional_fetches",
        "additional_fetch_calls",
        "total_fetch_cap",
        "additional_model_requests",
        "additional_logical_queries",
        "additional_search_batches",
        "additional_provider_search_calls",
    )
    numeric_fields = (
        "adaptive_acquisition_credit_total_nats",
        "pre_active_entropy_total_nats",
        "final_combined_entropy_total_nats",
        "final_positive_information_gain_total_nats",
        "final_epistemic_credit_total_nats",
        "final_decision_credit_total_nats",
        "minimum_alternative_posterior",
    )
    true_fields = (
        "frozen_source_disjoint_lead_pool_reused",
        "adaptive_stop_replayed_exactly",
        "safe_change_thresholds_preserved",
        "entropy_priority_uses_only_frozen_leads_and_current_validated_state",
        "realized_step_information_gain_is_order_dependent_online_credit",
        "final_source_credit_uses_normalized_leave_one_out_information_gain",
        "decision_credit_requires_safe_output_change",
    )
    false_fields = (
        "allocated_credit_used_for_same_run_routing_or_training",
        "task_private_lead_page_observation_value_prediction_or_source_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_policy_id") != parent.POLICY_ID
        or any(_nonnegative_integer(copied.get(name), name) < 0 for name in count_fields)
        or any(_finite(copied.get(name), name) < 0 for name in numeric_fields)
        or not isinstance(partition, Mapping)
        or tuple(partition) != parent.THRESHOLD_PARTITION_FIELDS
        or sum(int(partition[name]) for name in parent.THRESHOLD_PARTITION_FIELDS)
        != copied.get("selected_target_count")
        or copied.get("adaptive_fetch_attempt_count") > MAXIMUM_ADDITIONAL_FETCHES
        or copied.get("adaptive_usable_page_count") > copied.get("adaptive_fetch_attempt_count")
        or copied.get("adaptive_positive_information_gain_step_count") > copied.get("adaptive_fetch_attempt_count")
        or copied.get("adaptive_safe_decision_step_count") not in {0, 1}
        or copied.get("adaptive_safe_decision_step_count")
        > int(copied.get("safe_change_count", 0) > 0)
        or copied.get("safe_change_count") != partition.get("safe_change_count")
        or copied.get("safe_change_count")
        + copied.get("baseline_confirmed_count")
        + copied.get("unresolved_count")
        != copied.get("selected_target_count")
        or copied.get("known_baseline_minimum_support_sources")
        != KNOWN_ALTERNATIVE_MINIMUM_SOURCES
        or copied.get("unknown_baseline_minimum_support_sources")
        != UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES
        or copied.get("minimum_alternative_posterior") != MINIMUM_ALTERNATIVE_POSTERIOR
        or copied.get("required_support_margin") != 1
        or copied.get("active_source_cap") != MAXIMUM_ACTIVE_SOURCES
        or copied.get("parent_total_fetch_cap") != PARENT_FETCH_CAP
        or copied.get("maximum_additional_fetches") != MAXIMUM_ADDITIONAL_FETCHES
        or copied.get("additional_fetch_calls") != copied.get("adaptive_fetch_attempt_count")
        or copied.get("total_fetch_cap") != MAXIMUM_TOTAL_FETCHES
        or any(
            copied.get(name) != 0
            for name in (
                "additional_model_requests",
                "additional_logical_queries",
                "additional_search_batches",
                "additional_provider_search_calls",
            )
        )
        or copied.get("final_decision_credit_total_nats", 0)
        > copied.get("final_epistemic_credit_total_nats", 0) + 1e-12
        or copied.get("final_decision_credit_total_nats", 0) > 0
        and copied.get("safe_change_count") == 0
        or copied.get("stop_reason") not in STOP_REASONS
        or copied.get("stop_reason") == "safe_decision"
        and copied.get("safe_change_count") == 0
        or copied.get("stop_reason") != "safe_decision"
        and copied.get("safe_change_count") > 0
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.57 recovery receipt drifted")
    return copy.deepcopy(copied)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("result_sha256", None)
    if (
        set(copied) != RESULT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != RESULT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(copied.get("parent_result"), Mapping)
        or not isinstance(copied.get("candidate_prediction"), str)
        or not isinstance(copied.get("adaptive_narrative_title_projection"), Mapping)
        or not isinstance(copied.get("adaptive_active_evidence_result"), Mapping)
        or not isinstance(copied.get("adaptive_private_state"), Mapping)
        or not isinstance(copied.get("adaptive_support_receipt"), Mapping)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.57 result identity drifted")
    parent.validate_result(copied["parent_result"])
    validate_narrative_title_anchor_projection(copied["adaptive_narrative_title_projection"])
    validate_active_evidence_result(copied["adaptive_active_evidence_result"])
    validate_recovery_receipt(copied["adaptive_support_receipt"])
    expected = _compute_result(copied["parent_result"], copied["adaptive_private_state"])
    if copied != expected:
        raise ValueError("V2.44.57 result replay drifted")
    return copy.deepcopy(copied)


def build_effect_delta_receipt(
    *,
    model_before: Mapping[str, Any],
    model_after: Mapping[str, Any],
    transport_before: Mapping[str, Any],
    transport_after: Mapping[str, Any],
    search_before: Mapping[str, Any],
    search_after: Mapping[str, Any],
    expected_model_cap: int,
    additional_fetch_attempt_count: int,
) -> dict[str, Any]:
    if not 0 <= _nonnegative_integer(additional_fetch_attempt_count, "fetch attempts") <= MAXIMUM_ADDITIONAL_FETCHES:
        raise ValueError("V2.44.57 adaptive fetch cap exceeded")
    before_model = validate_model_receipt(dict(model_before), expected_cap=expected_model_cap)
    after_model = validate_model_receipt(dict(model_after), expected_cap=expected_model_cap)
    before_transport = validate_transport_health(transport_before)
    after_transport = validate_transport_health(transport_after)
    before_search = dict(search_before)
    after_search = dict(search_after)
    validate_search_receipt(before_search)
    validate_search_receipt(after_search)
    model_observation = {"remaining_seconds_at_receipt", "deadline_exhausted", "receipt_payload_sha256"}
    model_equal = {
        key: item for key, item in before_model.items() if key not in model_observation
    } == {
        key: item for key, item in after_model.items() if key not in model_observation
    }
    deltas = {
        name: _counter_delta(before_transport, after_transport, name)
        for name in (
            "hosted_search_attempts",
            "hosted_search_deadline_failures",
            "hard_fetch_helper_calls",
            "fetch_deadline_rejections",
            "hard_fetch_deadline_failures",
            "fetch_helper_failures",
        )
    }
    fetch_effects = deltas["hard_fetch_helper_calls"] + deltas["fetch_deadline_rejections"]
    value = {
        "artifact_version": 1,
        "role": EFFECT_ROLE,
        "policy_id": POLICY_ID,
        "additional_fetch_attempt_count": additional_fetch_attempt_count,
        "additional_model_acquisitions": int(after_model["acquisitions"]) - int(before_model["acquisitions"]),
        "additional_model_attempts": 0,
        "additional_hosted_search_attempts": deltas["hosted_search_attempts"],
        "additional_hosted_search_deadline_failures": deltas["hosted_search_deadline_failures"],
        "additional_hard_fetch_helper_calls": deltas["hard_fetch_helper_calls"],
        "additional_fetch_deadline_rejections": deltas["fetch_deadline_rejections"],
        "additional_hard_fetch_deadline_failures": deltas["hard_fetch_deadline_failures"],
        "additional_fetch_helper_failures": deltas["fetch_helper_failures"],
        "additional_fetch_effects": fetch_effects,
        "model_effect_and_static_fields_equal": model_equal,
        "model_remaining_seconds_nonincreasing": 0.0 <= float(after_model["remaining_seconds_at_receipt"]) <= float(before_model["remaining_seconds_at_receipt"]) + 1e-6,
        "model_deadline_state_monotonic": not (before_model["deadline_exhausted"] is True and after_model["deadline_exhausted"] is False),
        "search_shape_fields_equal": before_search == after_search,
        "transport_deadline_state_monotonic": not (before_transport["deadline_exhausted"] is True and after_transport["deadline_exhausted"] is False),
        "only_frozen_source_disjoint_page_fetch_effects_allowed": True,
        "question_prompt_response_query_url_page_prediction_candidate_value_or_source_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    validate_effect_delta_receipt(value)
    return value


def validate_effect_delta_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    counts = (
        "additional_fetch_attempt_count",
        "additional_model_acquisitions",
        "additional_model_attempts",
        "additional_hosted_search_attempts",
        "additional_hosted_search_deadline_failures",
        "additional_hard_fetch_helper_calls",
        "additional_fetch_deadline_rejections",
        "additional_hard_fetch_deadline_failures",
        "additional_fetch_helper_failures",
        "additional_fetch_effects",
    )
    if (
        set(copied) != EFFECT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != EFFECT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(_nonnegative_integer(copied.get(name), name) < 0 for name in counts)
        or copied.get("additional_fetch_attempt_count") > MAXIMUM_ADDITIONAL_FETCHES
        or any(
            copied.get(name) != 0
            for name in (
                "additional_model_acquisitions",
                "additional_model_attempts",
                "additional_hosted_search_attempts",
                "additional_hosted_search_deadline_failures",
            )
        )
        or copied.get("additional_fetch_effects")
        != copied.get("additional_hard_fetch_helper_calls") + copied.get("additional_fetch_deadline_rejections")
        or copied.get("additional_fetch_effects") != copied.get("additional_fetch_attempt_count")
        or copied.get("additional_hard_fetch_deadline_failures") + copied.get("additional_fetch_helper_failures")
        > copied.get("additional_hard_fetch_helper_calls")
        or any(
            copied.get(name) is not True
            for name in (
                "model_effect_and_static_fields_equal",
                "model_remaining_seconds_nonincreasing",
                "model_deadline_state_monotonic",
                "search_shape_fields_equal",
                "transport_deadline_state_monotonic",
                "only_frozen_source_disjoint_page_fetch_effects_allowed",
            )
        )
        or any(
            copied.get(name) is not False
            for name in (
                "question_prompt_response_query_url_page_prediction_candidate_value_or_source_emitted",
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.57 effect delta receipt drifted")
    return copy.deepcopy(copied)


def run_v24457_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    partition_seed_sha256: str,
    limits: Any,
    monotonic: Callable[[], float],
) -> IntegratedAdaptiveEntropySupportOutcome:
    first = parent.run_v24447_task(
        task,
        model=model,
        search=search,
        partition_seed_sha256=partition_seed_sha256,
        limits=limits,
        monotonic=monotonic,
    )
    before_model = copy.deepcopy(first.model_slot_receipt_before_third_source)
    before_transport = copy.deepcopy(first.transport_health_before_third_source)
    before_search = copy.deepcopy(first.search_single_shot_receipt_before_third_source)
    first_private = first.third_source_result["third_source_private_state"]
    leads: list[dict[str, str]] = []
    batches: list[list[dict[str, Any]]] = []
    pages: list[list[dict[str, Any]]] = []
    steps: list[dict[str, Any]] = []
    original = _original_parent_result(first.third_source_result)
    before = _snapshot(original, [])
    if first_private["selected_third_lead"] is None:
        stop = str(
            _stop_reason(before, attempted=0, remaining_lead_count=0)
        )
    else:
        lead = _lead_projection(first_private["selected_third_lead"])
        leads.append(lead)
        batches.append(copy.deepcopy(first_private["third_fetch_batches"]))
        pages.append(copy.deepcopy(first_private["third_pages"]))
        flattened = [page for vector in pages for page in vector]
        after = _snapshot(original, flattened)
        remaining = _remaining_ranked_leads(original, leads, after)
        reason = _stop_reason(after, attempted=1, remaining_lead_count=len(remaining))
        steps.append(
            build_step_receipt(
                step_ordinal=1,
                before=before,
                after=after,
                remaining_fetch_budget=MAXIMUM_ADDITIONAL_FETCHES - 1,
                remaining_frozen_lead_count=len(remaining),
                stop_reason_after_step=reason,
            )
        )
        before = after
        while reason is None:
            step = len(leads) + 1
            lead = remaining[0]
            fetched = list(search.fetch_urls([lead]))
            rebuilt = _rebuild_step_pages(fetched, step_ordinal=step, lead=lead)
            leads.append(copy.deepcopy(lead))
            batches.append(copy.deepcopy(fetched))
            pages.append(rebuilt)
            flattened = [page for vector in pages for page in vector]
            after = _snapshot(original, flattened)
            remaining = _remaining_ranked_leads(original, leads, after)
            reason = _stop_reason(
                after, attempted=step, remaining_lead_count=len(remaining)
            )
            steps.append(
                build_step_receipt(
                    step_ordinal=step,
                    before=before,
                    after=after,
                    remaining_fetch_budget=MAXIMUM_ADDITIONAL_FETCHES - step,
                    remaining_frozen_lead_count=len(remaining),
                    stop_reason_after_step=reason,
                )
            )
            before = after
        stop = str(reason)
    private = {
        "selected_adaptive_leads": leads,
        "adaptive_fetch_batches": batches,
        "adaptive_step_pages": pages,
        "adaptive_step_receipts": steps,
        "stop_reason": stop,
    }
    result = _compute_result(first.third_source_result, private)
    after_model = model.receipt()
    after_transport = search.transport_health()
    after_search = search.single_shot_receipt()
    effect = build_effect_delta_receipt(
        model_before=before_model,
        model_after=after_model,
        transport_before=before_transport,
        transport_after=after_transport,
        search_before=before_search,
        search_after=after_search,
        expected_model_cap=int(after_model["slot_cap"]),
        additional_fetch_attempt_count=len(leads),
    )
    outcome = IntegratedAdaptiveEntropySupportOutcome(
        parent=first,
        adaptive_result=result,
        model_slot_receipt_before_adaptive_support=before_model,
        transport_health_before_adaptive_support=before_transport,
        search_single_shot_receipt_before_adaptive_support=before_search,
        model_slot_receipt=after_model,
        transport_health=after_transport,
        search_single_shot_receipt=after_search,
        effect_delta_receipt=effect,
    )
    validate_cross_artifacts(
        parent.build_envelope(first),
        result,
        model_slot_receipt_before_adaptive_support=before_model,
        transport_health_before_adaptive_support=before_transport,
        search_single_shot_receipt_before_adaptive_support=before_search,
        model_slot_receipt=after_model,
        transport_health=after_transport,
        search_single_shot_receipt=after_search,
        effect_delta_receipt=effect,
        expected_model_cap=int(after_model["slot_cap"]),
    )
    return outcome


def validate_cross_artifacts(
    parent_envelope: Mapping[str, Any],
    adaptive_result: Mapping[str, Any],
    *,
    model_slot_receipt_before_adaptive_support: Mapping[str, Any],
    transport_health_before_adaptive_support: Mapping[str, Any],
    search_single_shot_receipt_before_adaptive_support: Mapping[str, Any],
    model_slot_receipt: Mapping[str, Any],
    transport_health: Mapping[str, Any],
    search_single_shot_receipt: Mapping[str, Any],
    effect_delta_receipt: Mapping[str, Any],
    expected_model_cap: int,
) -> None:
    validated_parent = parent.validate_envelope(parent_envelope)
    result = validate_result(adaptive_result)
    effect = validate_effect_delta_receipt(effect_delta_receipt)
    if result["parent_result"] != validated_parent["third_source_result"]:
        raise ValueError("V2.44.57 parent result drifted from parent envelope")
    expected = build_effect_delta_receipt(
        model_before=model_slot_receipt_before_adaptive_support,
        model_after=model_slot_receipt,
        transport_before=transport_health_before_adaptive_support,
        transport_after=transport_health,
        search_before=search_single_shot_receipt_before_adaptive_support,
        search_after=search_single_shot_receipt,
        expected_model_cap=expected_model_cap,
        additional_fetch_attempt_count=int(
            result["adaptive_support_receipt"]["adaptive_fetch_attempt_count"]
        ),
    )
    if expected != effect:
        raise ValueError("V2.44.57 adaptive effect replay drifted")


def build_envelope(outcome: IntegratedAdaptiveEntropySupportOutcome) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": ENVELOPE_ROLE,
        "policy_id": POLICY_ID,
        "parent_envelope": parent.build_envelope(outcome.parent),
        "adaptive_result": copy.deepcopy(outcome.adaptive_result),
        "model_slot_receipt_before_adaptive_support": copy.deepcopy(outcome.model_slot_receipt_before_adaptive_support),
        "transport_health_before_adaptive_support": copy.deepcopy(outcome.transport_health_before_adaptive_support),
        "search_single_shot_receipt_before_adaptive_support": copy.deepcopy(outcome.search_single_shot_receipt_before_adaptive_support),
        "model_slot_receipt": copy.deepcopy(outcome.model_slot_receipt),
        "transport_health": copy.deepcopy(outcome.transport_health),
        "search_single_shot_receipt": copy.deepcopy(outcome.search_single_shot_receipt),
        "effect_delta_receipt": copy.deepcopy(outcome.effect_delta_receipt),
        "private_task_content_present": True,
        "private_task_content_emitted_to_public_aggregate": False,
        "credential_or_privileged_evaluator_content_present": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["envelope_payload_sha256"] = payload_sha256(value)
    validate_envelope(value)
    return value


def validate_envelope(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("envelope_payload_sha256", None)
    mappings = (
        "parent_envelope",
        "adaptive_result",
        "model_slot_receipt_before_adaptive_support",
        "transport_health_before_adaptive_support",
        "search_single_shot_receipt_before_adaptive_support",
        "model_slot_receipt",
        "transport_health",
        "search_single_shot_receipt",
        "effect_delta_receipt",
    )
    if (
        set(copied) != ENVELOPE_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != ENVELOPE_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(not isinstance(copied.get(name), Mapping) for name in mappings)
        or copied.get("private_task_content_present") is not True
        or copied.get("private_task_content_emitted_to_public_aggregate") is not False
        or copied.get("credential_or_privileged_evaluator_content_present") is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.57 envelope identity drifted")
    after_model = copied["model_slot_receipt"]
    validate_cross_artifacts(
        copied["parent_envelope"],
        copied["adaptive_result"],
        model_slot_receipt_before_adaptive_support=copied["model_slot_receipt_before_adaptive_support"],
        transport_health_before_adaptive_support=copied["transport_health_before_adaptive_support"],
        search_single_shot_receipt_before_adaptive_support=copied["search_single_shot_receipt_before_adaptive_support"],
        model_slot_receipt=after_model,
        transport_health=copied["transport_health"],
        search_single_shot_receipt=copied["search_single_shot_receipt"],
        effect_delta_receipt=copied["effect_delta_receipt"],
        expected_model_cap=int(after_model.get("slot_cap", -1)),
    )
    return copy.deepcopy(copied)


def run_and_persist_v24457_task(
    task: Mapping[str, Any],
    *,
    model_factory: Callable[[], Any],
    search_factory: Callable[[], Any],
    partition_seed_sha256: str,
    limits: Any,
    monotonic: Callable[[], float],
    expected_model_cap: int,
    writer: Callable[[str, Mapping[str, Any]], None],
) -> IntegratedAdaptiveEntropySupportOutcome:
    model: Any = None
    search: Any = None
    stage = "model_construction"
    try:
        model = model_factory()
        stage = "search_construction"
        search = search_factory()
        stage = "runtime"
        outcome = run_v24457_task(
            task,
            model=model,
            search=search,
            partition_seed_sha256=partition_seed_sha256,
            limits=limits,
            monotonic=monotonic,
        )
    except BaseException as error:
        persist_failure_artifacts(
            error,
            failure_stage=stage,
            model=model,
            search=search,
            expected_model_cap=expected_model_cap,
            writer=writer,
        )
        raise
    envelope = build_envelope(outcome)
    model_written = False
    transport_written = False
    search_written = False
    try:
        writer(MODEL_NAME, outcome.model_slot_receipt)
        model_written = True
        writer(TRANSPORT_NAME, outcome.transport_health)
        transport_written = True
        writer(SEARCH_NAME, outcome.search_single_shot_receipt)
        search_written = True
        writer(RESULT_NAME, envelope)
    except BaseException as error:
        snapshot = build_failure_snapshot(
            error,
            failure_stage="artifact_serialization",
            model_receipt=outcome.model_slot_receipt if model_written else None,
            transport_health=outcome.transport_health if transport_written else None,
            search_receipt=outcome.search_single_shot_receipt if search_written else None,
            expected_model_cap=expected_model_cap,
        )
        writer(FAILURE_NAME, snapshot)
        raise
    return outcome


__all__ = [
    "EFFECT_ROLE",
    "ENVELOPE_ROLE",
    "IntegratedAdaptiveEntropySupportOutcome",
    "MAXIMUM_ACTIVE_SOURCES",
    "MAXIMUM_ADDITIONAL_FETCHES",
    "MAXIMUM_TOTAL_FETCHES",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "RESULT_ROLE",
    "STEP_ROLE",
    "STOP_REASONS",
    "build_effect_delta_receipt",
    "build_envelope",
    "build_step_receipt",
    "run_and_persist_v24457_task",
    "run_v24457_task",
    "validate_effect_delta_receipt",
    "validate_envelope",
    "validate_recovery_receipt",
    "validate_result",
    "validate_step_receipt",
]
