"""Decision-reachability-first planning under the frozen safety thresholds.

V2.45.54 produced a same-task alias hit, new observation, positive information
gain, and positive epistemic action credit, but no changed cell or decision
credit.  The active V2.45.10 planner already proves that a concrete alternative
can cross every frozen safe-change rule within the three-fetch cap.  Its final
choice, however, ranks reachable targets by entropy before the number of new
independent observations required to make a safe decision.

This append-only policy changes only that ordering.  It first minimizes the
number of matching, source-independent observations needed to cross the
unchanged source-count, active-support, posterior, and margin gates.  Ties are
broken by optimistic information reduction per required observation and then
current entropy.  The optimistic projection is a reachability certificate, not
a claim that search will return matching evidence and not a causal or expected
utility estimate.

The emitted target plan remains byte-schema compatible with V2.45.10 so the
frozen V2.45.15 discovery fallback and V2.44.90 executor can validate it.  A
separate content-free receipt identifies this policy.  No benchmark label,
mapping, gold answer, evaluator, reward, score, credential, file, environment,
network, model, search, fetch, or process input is available to this module.
"""

from __future__ import annotations

import copy
import math
import threading
from collections.abc import Mapping
from contextlib import AbstractContextManager
from typing import Any

from . import v24388_uncertainty_credit as credit
from . import v24490_entropy_targeted_support_search as targeted
from . import v24510_proposal_seeded_entropy_target_planner as previous
from .v24323_shared_prefix_cell_entropy import payload_sha256


POLICY_ID = "v24555_decision_reachability_first_target_planner_v1"
EXPECTED_BINDING_COUNT = 1
ORIGINAL_BUILD_PLAN = previous._build_plan
_BINDING_GUARD = threading.Lock()

RECEIPT_KEYS = frozenset(
    {
        "policy_id",
        "binding_count",
        "selection_calls",
        "no_reachable_plan_calls",
        "one_observation_plan_calls",
        "two_observation_plan_calls",
        "three_observation_plan_calls",
        "legacy_entropy_choice_changed_calls",
        "reachable_candidate_count_total",
        "minimum_independent_observations_is_primary_priority",
        "optimistic_information_gain_per_observation_is_secondary_priority",
        "current_entropy_is_tertiary_priority",
        "projection_is_reachability_not_expected_utility_or_causality",
        "legacy_plan_schema_preserved",
        "neutral_discovery_fallback_preserved",
        "source_count_active_support_posterior_margin_leave_one_out_safe_change_and_decision_credit_rules_unchanged",
        "cache_or_cross_task_state_used",
        "bindings_restored",
        "task_question_opaque_id_query_url_page_source_value_prediction_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
    }
)


def _count(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.45.55 {label} is invalid")
    return value


def _reachable_candidate(
    validated: Mapping[str, Any],
    target: Mapping[str, Any],
    resolution: Mapping[str, Any],
) -> dict[str, Any] | None:
    candidate = previous._candidate(validated, target, resolution)
    if candidate is None:
        return None
    active_votes, _ambiguous = credit._bound_votes(
        target, validated["active_observations"]
    )
    hypotheses, _prior, proposal_posterior = credit._expanded_frozen_belief(
        target, active_votes
    )
    combined = credit._posterior_from_base(
        proposal_posterior, hypotheses, active_votes
    )
    alternative = str(candidate["alternative_hypothesis"])
    if alternative not in hypotheses:
        raise ValueError("V2.45.55 reachable alternative is absent")
    required_observations = int(candidate["additional_needed"])
    projected = credit._posterior_from_base(
        combined,
        hypotheses,
        [{"hypothesis": alternative}] * required_observations,
    )
    projected_probability = projected[hypotheses.index(alternative)]
    current_entropy = credit._entropy(combined)
    projected_entropy = credit._entropy(projected)
    projected_information_gain = max(0.0, current_entropy - projected_entropy)
    projected_support = int(candidate["support"]) + required_observations
    projected_active_support = (
        int(candidate["active_support"]) + required_observations
    )
    projected_margin = int(candidate["margin"]) + required_observations
    if (
        not 1 <= required_observations <= targeted.MAXIMUM_TARGETED_SOURCES
        or projected_support < int(candidate["required"])
        or projected_active_support < 1
        or projected_probability < credit.MINIMUM_ALTERNATIVE_POSTERIOR
        or projected_margin < 1
        or projected_information_gain <= 0
        or not math.isclose(
            current_entropy,
            float(resolution["combined_entropy_nats"]),
            abs_tol=2e-12,
        )
        or not math.isclose(
            projected_probability,
            float(candidate["projected_probability"]),
            abs_tol=2e-12,
        )
    ):
        raise ValueError("V2.45.55 decision reachability proof drifted")
    return {
        **candidate,
        "required_observations": required_observations,
        "projected_probability": projected_probability,
        "current_entropy": current_entropy,
        "projected_entropy": projected_entropy,
        "projected_information_gain": projected_information_gain,
        "projected_information_gain_per_observation": (
            projected_information_gain / required_observations
        ),
    }


def _selection(
    active_result: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    validated = credit.validate_active_evidence_result(active_result)
    targets = {
        str(item["target_binding_sha256"]): item
        for item in validated["catalog"]["targets"]
    }
    candidates: list[dict[str, Any]] = []
    for resolution in validated["resolutions"]:
        binding = str(resolution["target_binding_sha256"])
        target = targets.get(binding)
        if target is None:
            raise ValueError("V2.45.55 target binding is absent")
        candidate = _reachable_candidate(validated, target, resolution)
        if candidate is not None:
            candidates.append(candidate)
    if not candidates:
        return None, {"candidate_count": 0, "required_observations": 0}
    chosen = min(
        candidates,
        key=lambda item: (
            int(item["required_observations"]),
            -float(item["projected_information_gain_per_observation"]),
            -float(item["current_entropy"]),
            -float(item["projected_probability"]),
            -int(item["support"]),
            str(item["binding"]),
        ),
    )
    target = chosen["target"]
    row = " ".join(str(target["row_key"]).split()).strip()
    column = " ".join(str(target["column"]).split()).strip()
    alternative = " ".join(str(chosen["alternative_display"]).split()).strip()
    value = {
        "artifact_version": 1,
        "role": previous.PLAN_ROLE,
        "policy_id": previous.POLICY_ID,
        "target_binding_sha256": str(chosen["binding"]),
        "row_key": row,
        "column": column,
        "leading_alternative": alternative,
        "leading_alternative_hypothesis": str(
            chosen["alternative_hypothesis"]
        ),
        "seed_mode": str(chosen["seed_mode"]),
        "combined_entropy_nats": float(chosen["current_entropy"]),
        "current_alternative_support_count": int(chosen["support"]),
        "current_alternative_proposal_support_count": int(
            chosen["proposal_support"]
        ),
        "current_alternative_active_support_count": int(
            chosen["active_support"]
        ),
        "current_alternative_posterior_probability": round(
            float(chosen["probability"]), 12
        ),
        "current_alternative_support_margin": int(chosen["margin"]),
        "required_support_count": int(chosen["required"]),
        "support_count_deficit": int(chosen["support_count_deficit"]),
        "active_support_deficit": int(chosen["active_support_deficit"]),
        "support_margin_deficit": int(chosen["support_margin_deficit"]),
        "minimum_new_active_support_count": 1,
        "projected_alternative_posterior_probability_after_planned_support": round(
            float(chosen["projected_probability"]), 12
        ),
        "support_deficit": int(chosen["required_observations"]),
        "maximum_targeted_fetches": int(chosen["required_observations"]),
        "query_vector": targeted._query_vector(row, column, alternative),
        "selection_uses_only_validated_posterior_entropy_and_support_deficit": True,
        "queries_use_only_frozen_row_column_and_leading_alternative": True,
        "proposal_seed_used_for_query_only": True,
        "proposal_votes_receive_no_active_source_credit": True,
        "final_safe_change_thresholds_unchanged": True,
        "benchmark_label_mapping_gold_evaluator_score_or_reward_read": False,
    }
    value["plan_payload_sha256"] = payload_sha256(value)
    return value, {
        "candidate_count": len(candidates),
        "required_observations": int(chosen["required_observations"]),
    }


def build_target_plan(
    active_result: Mapping[str, Any],
) -> dict[str, Any] | None:
    value, _diagnostic = _selection(active_result)
    if value is not None:
        validate_target_plan(value, active_result=active_result)
    return value


def validate_target_plan(
    value: Mapping[str, Any], *, active_result: Mapping[str, Any]
) -> dict[str, Any]:
    expected, _diagnostic = _selection(active_result)
    copied = copy.deepcopy(dict(value))
    if expected is None or copied != expected:
        raise ValueError("V2.45.55 target plan replay drifted")
    if not _BINDING_GUARD.acquire(blocking=False):
        raise RuntimeError("V2.45.55 planner binding is already active")
    installed = previous._build_plan
    try:
        if installed is not ORIGINAL_BUILD_PLAN:
            raise RuntimeError("V2.45.55 frozen planner binding drifted")
        previous._build_plan = lambda state: _selection(state)[0]
        previous._validate_plan(copied, active_result=active_result)
    finally:
        previous._build_plan = installed
        _BINDING_GUARD.release()
    return copied


class DecisionReachabilityPlanner(
    AbstractContextManager["DecisionReachabilityPlanner"]
):
    """Install reachability-first choice around one existing worker call."""

    def __init__(self) -> None:
        self._active = False
        self._acquired = False
        self._installed: Any = None
        self._stats = {
            "selection_calls": 0,
            "no_reachable_plan_calls": 0,
            "one_observation_plan_calls": 0,
            "two_observation_plan_calls": 0,
            "three_observation_plan_calls": 0,
            "legacy_entropy_choice_changed_calls": 0,
            "reachable_candidate_count_total": 0,
        }

    def _build(self, active_result: Mapping[str, Any]) -> dict[str, Any] | None:
        value, diagnostic = _selection(active_result)
        legacy = ORIGINAL_BUILD_PLAN(active_result)
        self._stats["selection_calls"] += 1
        self._stats["reachable_candidate_count_total"] += int(
            diagnostic["candidate_count"]
        )
        if value is None:
            self._stats["no_reachable_plan_calls"] += 1
            return None
        needed = int(diagnostic["required_observations"])
        self._stats[
            ("one", "two", "three")[needed - 1] + "_observation_plan_calls"
        ] += 1
        if legacy is not None and (
            legacy["target_binding_sha256"] != value["target_binding_sha256"]
        ):
            self._stats["legacy_entropy_choice_changed_calls"] += 1
        return value

    def __enter__(self) -> "DecisionReachabilityPlanner":
        if self._active or not _BINDING_GUARD.acquire(blocking=False):
            raise RuntimeError("V2.45.55 planner context is already active")
        self._acquired = True
        if previous._build_plan is not ORIGINAL_BUILD_PLAN:
            _BINDING_GUARD.release()
            self._acquired = False
            raise RuntimeError("V2.45.55 frozen planner binding drifted")
        self._installed = self._build
        previous._build_plan = self._installed
        self._active = True
        return self

    def __exit__(self, *_: object) -> None:
        drifted = False
        try:
            if self._active:
                drifted = previous._build_plan is not self._installed
                previous._build_plan = ORIGINAL_BUILD_PLAN
                self._active = False
                self._installed = None
        finally:
            if self._acquired:
                self._acquired = False
                _BINDING_GUARD.release()
        if drifted:
            raise RuntimeError("V2.45.55 installed planner binding drifted")

    def content_free_receipt(self) -> dict[str, Any]:
        return {
            "policy_id": POLICY_ID,
            "binding_count": EXPECTED_BINDING_COUNT,
            **dict(self._stats),
            "minimum_independent_observations_is_primary_priority": True,
            "optimistic_information_gain_per_observation_is_secondary_priority": True,
            "current_entropy_is_tertiary_priority": True,
            "projection_is_reachability_not_expected_utility_or_causality": True,
            "legacy_plan_schema_preserved": True,
            "neutral_discovery_fallback_preserved": True,
            "source_count_active_support_posterior_margin_leave_one_out_safe_change_and_decision_credit_rules_unchanged": True,
            "cache_or_cross_task_state_used": False,
            "bindings_restored": not self._active and not self._acquired,
            "task_question_opaque_id_query_url_page_source_value_prediction_or_credential_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    counts = (
        "selection_calls",
        "no_reachable_plan_calls",
        "one_observation_plan_calls",
        "two_observation_plan_calls",
        "three_observation_plan_calls",
        "legacy_entropy_choice_changed_calls",
        "reachable_candidate_count_total",
    )
    true_fields = (
        "minimum_independent_observations_is_primary_priority",
        "optimistic_information_gain_per_observation_is_secondary_priority",
        "current_entropy_is_tertiary_priority",
        "projection_is_reachability_not_expected_utility_or_causality",
        "legacy_plan_schema_preserved",
        "neutral_discovery_fallback_preserved",
        "source_count_active_support_posterior_margin_leave_one_out_safe_change_and_decision_credit_rules_unchanged",
        "bindings_restored",
    )
    false_fields = (
        "cache_or_cross_task_state_used",
        "task_question_opaque_id_query_url_page_source_value_prediction_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    planned = sum(
        int(copied.get(name, -1))
        for name in (
            "one_observation_plan_calls",
            "two_observation_plan_calls",
            "three_observation_plan_calls",
        )
    )
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("policy_id") != POLICY_ID
        or copied.get("binding_count") != EXPECTED_BINDING_COUNT
        or any(_count(copied.get(name), name) < 0 for name in counts)
        or copied["selection_calls"]
        != copied["no_reachable_plan_calls"] + planned
        or copied["legacy_entropy_choice_changed_calls"] > planned
        or copied["reachable_candidate_count_total"] < planned
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
    ):
        raise ValueError("V2.45.55 planner receipt drifted")
    return copied


__all__ = [
    "DecisionReachabilityPlanner",
    "POLICY_ID",
    "build_target_plan",
    "validate_receipt",
    "validate_target_plan",
]
