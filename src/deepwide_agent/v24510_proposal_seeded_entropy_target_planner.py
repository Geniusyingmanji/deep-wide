"""Proposal-seeded, label-blind entropy target planning.

V2.45.06 completed network effects for five tasks but produced no target plan.
The frozen V2.44.90 planner requires the leading alternative to have at least
one active-support vote before it may issue an alternative-specific query.
That creates a dead zone when the proposal stage already exposes a concrete
alternative but the source-disjoint active stage has not recovered it.

This append-only planner allows a validated proposal alternative to seed the
query for one unresolved cell.  Proposal evidence is *not* promoted to active
evidence or source credit: the unchanged downstream resolution still requires
at least one source-disjoint active vote, the same total source threshold,
posterior threshold, support margin, and safe output change before decision
credit can be positive.  A target is eligible only when the bounded targeted
fetch budget can reach both the source-count and active-support requirements.

The planner is installed only inside one worker execution and restores all
three V2.44.90 planner bindings on every exit path.  It performs no file,
environment, network, model, search, fetch, process, benchmark, evaluator,
reward, score, or credential access.
"""

from __future__ import annotations

import copy
import math
import threading
from collections import Counter
from collections.abc import Mapping
from contextlib import AbstractContextManager
from typing import Any, Callable

from . import v24388_uncertainty_credit as credit
from . import v24490_entropy_targeted_support_search as targeted
from .v24323_shared_prefix_cell_entropy import payload_sha256


POLICY_ID = "v24510_proposal_seeded_label_blind_entropy_target_planner_v1"
PLAN_ROLE = "v24510_proposal_seeded_entropy_target_plan"
EXPECTED_BINDING_COUNT = 3
SEED_MODES = frozenset({"active_supported", "proposal_seeded"})
ORIGINAL_BUILD_TARGET_PLAN = targeted.build_target_plan
ORIGINAL_BUILD_TARGET_PLAN_WITHOUT_VALIDATION = (
    targeted.build_target_plan_without_validation
)
ORIGINAL_VALIDATE_TARGET_PLAN = targeted.validate_target_plan
PLAN_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "target_binding_sha256",
        "row_key",
        "column",
        "leading_alternative",
        "leading_alternative_hypothesis",
        "seed_mode",
        "combined_entropy_nats",
        "current_alternative_support_count",
        "current_alternative_proposal_support_count",
        "current_alternative_active_support_count",
        "current_alternative_posterior_probability",
        "current_alternative_support_margin",
        "required_support_count",
        "support_count_deficit",
        "active_support_deficit",
        "support_margin_deficit",
        "minimum_new_active_support_count",
        "projected_alternative_posterior_probability_after_planned_support",
        "support_deficit",
        "maximum_targeted_fetches",
        "query_vector",
        "selection_uses_only_validated_posterior_entropy_and_support_deficit",
        "queries_use_only_frozen_row_column_and_leading_alternative",
        "proposal_seed_used_for_query_only",
        "proposal_votes_receive_no_active_source_credit",
        "final_safe_change_thresholds_unchanged",
        "benchmark_label_mapping_gold_evaluator_score_or_reward_read",
        "plan_payload_sha256",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "policy_id",
        "binding_count",
        "build_calls",
        "replay_calls",
        "validation_calls",
        "active_supported_plan_builds",
        "proposal_seeded_plan_builds",
        "no_plan_builds",
        "proposal_seed_is_query_only",
        "final_source_posterior_margin_and_credit_thresholds_unchanged",
        "cache_or_cross_task_state_used",
        "bindings_restored",
        "task_question_opaque_id_query_url_page_prediction_or_value_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
    }
)


def _count(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.45.10 {label} is invalid")
    return value


def _finite(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise ValueError(f"V2.45.10 {label} is invalid")
    return float(value)


def _candidate(
    validated: Mapping[str, Any],
    target: Mapping[str, Any],
    resolution: Mapping[str, Any],
) -> dict[str, Any] | None:
    if resolution["status"] == "safe_change":
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
    proposal_votes = list(target["proposal_votes"])
    combined_votes = [*proposal_votes, *active_votes]
    counts = Counter(str(item["hypothesis"]) for item in combined_votes)
    proposal_counts = Counter(
        str(item["hypothesis"]) for item in proposal_votes
    )
    active_counts = Counter(str(item["hypothesis"]) for item in active_votes)
    alternatives = [
        item for item in hypotheses if item not in {credit.CURRENT, credit.OTHER}
    ]
    alternative = max(
        alternatives,
        key=lambda item: (
            counts[item],
            combined[hypotheses.index(item)],
            item,
        ),
        default=None,
    )
    if alternative is None or counts[alternative] <= 0:
        return None
    proposal_support = proposal_counts[alternative]
    active_support = active_counts[alternative]
    if proposal_support <= 0 and active_support <= 0:
        return None
    if active_support == 0:
        leading_key = (
            counts[alternative],
            combined[hypotheses.index(alternative)],
        )
        if any(
            (
                counts[item],
                combined[hypotheses.index(item)],
            )
            == leading_key
            for item in alternatives
            if item != alternative
        ):
            return None
    displays = sorted(
        {
            str(item["value"])
            for item in combined_votes
            if item["hypothesis"] == alternative
        },
        key=lambda item: (credit._normalized_value(item), len(item), item),
    )
    if not displays:
        return None
    support = counts[alternative]
    probability = combined[hypotheses.index(alternative)]
    competitor = max(
        [
            counts[credit.CURRENT],
            *(counts[item] for item in alternatives if item != alternative),
        ],
        default=0,
    )
    margin = support - competitor
    required = (
        credit.UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES
        if target["baseline_unknown"]
        else credit.KNOWN_ALTERNATIVE_MINIMUM_SOURCES
    )
    support_count_deficit = max(0, required - support)
    active_support_deficit = max(0, 1 - active_support)
    support_margin_deficit = max(0, competitor + 1 - support)
    additional_needed: int | None = None
    projected_probability = probability
    for added in range(1, targeted.MAXIMUM_TARGETED_SOURCES + 1):
        projected = credit._posterior_from_base(
            combined,
            hypotheses,
            [{"hypothesis": alternative}] * added,
        )
        projected_probability = projected[hypotheses.index(alternative)]
        if (
            support + added >= required
            and active_support + added >= 1
            and support + added - competitor >= 1
            and projected_probability >= credit.MINIMUM_ALTERNATIVE_POSTERIOR
        ):
            additional_needed = added
            break
    if (
        additional_needed is None
        or support
        != int(resolution["selected_alternative_support_count"])
        or active_support
        != int(resolution["selected_alternative_active_support_count"])
        or not math.isclose(
            probability,
            float(resolution["selected_alternative_posterior_probability"]),
            abs_tol=2e-12,
        )
        or margin != int(resolution["selected_alternative_support_margin"])
    ):
        return None
    return {
        "binding": str(resolution["target_binding_sha256"]),
        "target": target,
        "resolution": resolution,
        "alternative_hypothesis": alternative,
        "alternative_display": displays[0],
        "seed_mode": (
            "active_supported" if active_support > 0 else "proposal_seeded"
        ),
        "support": support,
        "proposal_support": proposal_support,
        "active_support": active_support,
        "probability": probability,
        "margin": margin,
        "required": required,
        "support_count_deficit": support_count_deficit,
        "active_support_deficit": active_support_deficit,
        "support_margin_deficit": support_margin_deficit,
        "projected_probability": projected_probability,
        "additional_needed": additional_needed,
    }


def _build_plan(active_result: Mapping[str, Any]) -> dict[str, Any] | None:
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
            raise ValueError("V2.45.10 target binding is absent")
        candidate = _candidate(validated, target, resolution)
        if candidate is not None:
            candidates.append(candidate)
    if not candidates:
        return None
    chosen = min(
        candidates,
        key=lambda item: (
            -float(item["resolution"]["combined_entropy_nats"]),
            int(item["additional_needed"]),
            -float(item["probability"]),
            -int(item["support"]),
            str(item["binding"]),
        ),
    )
    target = chosen["target"]
    row = " ".join(str(target["row_key"]).split()).strip()
    column = " ".join(str(target["column"]).split()).strip()
    alternative = " ".join(
        str(chosen["alternative_display"]).split()
    ).strip()
    value = {
        "artifact_version": 1,
        "role": PLAN_ROLE,
        "policy_id": POLICY_ID,
        "target_binding_sha256": str(chosen["binding"]),
        "row_key": row,
        "column": column,
        "leading_alternative": alternative,
        "leading_alternative_hypothesis": str(
            chosen["alternative_hypothesis"]
        ),
        "seed_mode": str(chosen["seed_mode"]),
        "combined_entropy_nats": float(
            chosen["resolution"]["combined_entropy_nats"]
        ),
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
        "support_deficit": int(chosen["additional_needed"]),
        "maximum_targeted_fetches": int(chosen["additional_needed"]),
        "query_vector": targeted._query_vector(row, column, alternative),
        "selection_uses_only_validated_posterior_entropy_and_support_deficit": True,
        "queries_use_only_frozen_row_column_and_leading_alternative": True,
        "proposal_seed_used_for_query_only": True,
        "proposal_votes_receive_no_active_source_credit": True,
        "final_safe_change_thresholds_unchanged": True,
        "benchmark_label_mapping_gold_evaluator_score_or_reward_read": False,
    }
    value["plan_payload_sha256"] = payload_sha256(value)
    return value


def _validate_plan(
    value: Mapping[str, Any], *, active_result: Mapping[str, Any]
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("plan_payload_sha256", None)
    if (
        set(copied) != PLAN_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != PLAN_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("seed_mode") not in SEED_MODES
        or not isinstance(copied.get("row_key"), str)
        or not copied.get("row_key")
        or not isinstance(copied.get("column"), str)
        or not copied.get("column")
        or not isinstance(copied.get("leading_alternative"), str)
        or not copied.get("leading_alternative")
        or _finite(copied.get("combined_entropy_nats"), "combined entropy") < 0
        or any(
            _count(copied.get(name), name) < 0
            for name in (
                "current_alternative_support_count",
                "current_alternative_proposal_support_count",
                "current_alternative_active_support_count",
                "required_support_count",
                "support_count_deficit",
                "active_support_deficit",
                "support_margin_deficit",
                "minimum_new_active_support_count",
                "support_deficit",
                "maximum_targeted_fetches",
            )
        )
        or _finite(
            copied.get("current_alternative_posterior_probability"),
            "alternative posterior",
        )
        > 1
        or _finite(
            copied.get(
                "projected_alternative_posterior_probability_after_planned_support"
            ),
            "projected alternative posterior",
        )
        > 1
        or copied.get("current_alternative_proposal_support_count")
        + copied.get("current_alternative_active_support_count")
        != copied.get("current_alternative_support_count")
        or copied.get("support_count_deficit")
        != max(
            0,
            copied.get("required_support_count")
            - copied.get("current_alternative_support_count"),
        )
        or copied.get("active_support_deficit")
        != max(
            0,
            copied.get("minimum_new_active_support_count")
            - copied.get("current_alternative_active_support_count"),
        )
        or copied.get("support_margin_deficit")
        != max(
            0,
            1 - copied.get("current_alternative_support_margin"),
        )
        or copied.get("minimum_new_active_support_count") != 1
        or copied.get("support_deficit")
        < max(
            copied.get("support_count_deficit"),
            copied.get("active_support_deficit"),
            copied.get("support_margin_deficit"),
        )
        or not 1
        <= copied.get("support_deficit")
        <= targeted.MAXIMUM_TARGETED_SOURCES
        or copied.get("maximum_targeted_fetches")
        != copied.get("support_deficit")
        or copied.get("seed_mode") == "proposal_seeded"
        and (
            copied.get("current_alternative_proposal_support_count") < 1
            or copied.get("current_alternative_active_support_count") != 0
        )
        or copied.get("seed_mode") == "active_supported"
        and copied.get("current_alternative_active_support_count") < 1
        or not isinstance(copied.get("query_vector"), list)
        or len(copied["query_vector"])
        != targeted.MAXIMUM_TARGETED_LOGICAL_QUERIES
        or copied["query_vector"]
        != targeted._query_vector(
            copied["row_key"],
            copied["column"],
            copied["leading_alternative"],
        )
        or any(
            copied.get(name) is not True
            for name in (
                "selection_uses_only_validated_posterior_entropy_and_support_deficit",
                "queries_use_only_frozen_row_column_and_leading_alternative",
                "proposal_seed_used_for_query_only",
                "proposal_votes_receive_no_active_source_credit",
                "final_safe_change_thresholds_unchanged",
            )
        )
        or copied.get(
            "benchmark_label_mapping_gold_evaluator_score_or_reward_read"
        )
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.45.10 target plan drifted")
    expected = _build_plan(active_result)
    if expected is None or copied != expected:
        raise ValueError("V2.45.10 target plan replay drifted")
    return copied


def build_target_plan(
    active_result: Mapping[str, Any],
) -> dict[str, Any] | None:
    value = _build_plan(active_result)
    return (
        None
        if value is None
        else _validate_plan(value, active_result=active_result)
    )


def build_target_plan_without_validation(
    active_result: Mapping[str, Any],
) -> dict[str, Any] | None:
    return _build_plan(active_result)


def validate_target_plan(
    value: Mapping[str, Any], *, active_result: Mapping[str, Any]
) -> dict[str, Any]:
    return _validate_plan(value, active_result=active_result)


class ProposalSeededTargetPlanner(
    AbstractContextManager["ProposalSeededTargetPlanner"]
):
    """Install the successor planner for exactly one worker execution."""

    def __init__(self) -> None:
        self._active = False
        self._lock = threading.RLock()
        self._restorations: list[tuple[Any, str, Any]] = []
        self._stats = {
            "build_calls": 0,
            "replay_calls": 0,
            "validation_calls": 0,
            "active_supported_plan_builds": 0,
            "proposal_seeded_plan_builds": 0,
            "no_plan_builds": 0,
        }

    def _build(self, active_result: Mapping[str, Any]) -> dict[str, Any] | None:
        with self._lock:
            self._stats["build_calls"] += 1
            value = _build_plan(active_result)
            if value is None:
                self._stats["no_plan_builds"] += 1
                return None
            key = f"{value['seed_mode']}_plan_builds"
            self._stats[key] += 1
            return self._validate(value, active_result=active_result)

    def _replay(
        self, active_result: Mapping[str, Any]
    ) -> dict[str, Any] | None:
        with self._lock:
            self._stats["replay_calls"] += 1
            return _build_plan(active_result)

    def _validate(
        self, value: Mapping[str, Any], *, active_result: Mapping[str, Any]
    ) -> dict[str, Any]:
        with self._lock:
            self._stats["validation_calls"] += 1
            return _validate_plan(value, active_result=active_result)

    def __enter__(self) -> "ProposalSeededTargetPlanner":
        if self._active:
            raise RuntimeError("V2.45.10 planner context is already active")
        bindings: tuple[tuple[str, Callable[..., Any], Callable[..., Any]], ...] = (
            (
                "build_target_plan",
                ORIGINAL_BUILD_TARGET_PLAN,
                self._build,
            ),
            (
                "build_target_plan_without_validation",
                ORIGINAL_BUILD_TARGET_PLAN_WITHOUT_VALIDATION,
                self._replay,
            ),
            (
                "validate_target_plan",
                ORIGINAL_VALIDATE_TARGET_PLAN,
                self._validate,
            ),
        )
        if len(bindings) != EXPECTED_BINDING_COUNT:
            raise RuntimeError("V2.45.10 planner binding surface drifted")
        if any(
            getattr(targeted, name) is not expected
            for name, expected, _replacement in bindings
        ):
            raise RuntimeError("V2.45.10 frozen planner binding drifted")
        try:
            for name, expected, replacement in bindings:
                self._restorations.append((targeted, name, expected))
                setattr(targeted, name, replacement)
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
            "proposal_seed_is_query_only": True,
            "final_source_posterior_margin_and_credit_thresholds_unchanged": True,
            "cache_or_cross_task_state_used": False,
            "bindings_restored": not self._active and not self._restorations,
            "task_question_opaque_id_query_url_page_prediction_or_value_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    count_fields = (
        "build_calls",
        "replay_calls",
        "validation_calls",
        "active_supported_plan_builds",
        "proposal_seeded_plan_builds",
        "no_plan_builds",
    )
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("policy_id") != POLICY_ID
        or copied.get("binding_count") != EXPECTED_BINDING_COUNT
        or any(_count(copied.get(name), name) < 0 for name in count_fields)
        or copied.get("build_calls")
        != copied.get("active_supported_plan_builds")
        + copied.get("proposal_seeded_plan_builds")
        + copied.get("no_plan_builds")
        or any(
            copied.get(name) is not True
            for name in (
                "proposal_seed_is_query_only",
                "final_source_posterior_margin_and_credit_thresholds_unchanged",
                "bindings_restored",
            )
        )
        or any(
            copied.get(name) is not False
            for name in (
                "cache_or_cross_task_state_used",
                "task_question_opaque_id_query_url_page_prediction_or_value_emitted",
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
                "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
    ):
        raise ValueError("V2.45.10 planner receipt drifted")
    return copied


__all__ = [
    "PLAN_KEYS",
    "PLAN_ROLE",
    "POLICY_ID",
    "ProposalSeededTargetPlanner",
    "build_target_plan",
    "build_target_plan_without_validation",
    "validate_receipt",
    "validate_target_plan",
]
