"""Label-blind neutral cell discovery for the no-alternative dead zone.

V2.45.10 can target a concrete proposal or active alternative, but it must
return no plan when an unresolved high-entropy cell has no concrete value at
all.  In that state there is nothing safe to place in an alternative-specific
query.  This execution-scoped successor keeps V2.45.10 unchanged whenever it
can build a plan, and otherwise may select one unresolved cell using only its
validated entropy state and issue two row/column-only discovery queries.

The discovery plan carries no candidate value and contributes no vote or
source credit.  At most three source-disjoint pages are still selected and
projected by the frozen V2.44.90 programmatic relation extractor.  The same
source-count, active-support, posterior, support-margin, safe-change, and
decision-credit rules remain downstream.  A cell is eligible only if a
hypothetical novel value could cross every unchanged rule within that frozen
three-source budget.

The planner performs no file, environment, network, model, search, fetch,
process, benchmark, evaluator, reward, score, or credential access.
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
from . import v24510_proposal_seeded_entropy_target_planner as previous
from .v24323_shared_prefix_cell_entropy import payload_sha256


POLICY_ID = "v24515_label_blind_neutral_cell_discovery_planner_v1"
PLAN_ROLE = "v24515_neutral_cell_discovery_plan"
EXPECTED_BINDING_COUNT = 3
SEED_MODES = frozenset(
    {"active_supported", "proposal_seeded", "cell_discovery"}
)
DISCOVERY_HYPOTHESIS = "__v24515_novel_discovery_hypothesis__"
ORIGINAL_BUILD_TARGET_PLAN = targeted.build_target_plan
ORIGINAL_BUILD_TARGET_PLAN_WITHOUT_VALIDATION = (
    targeted.build_target_plan_without_validation
)
ORIGINAL_VALIDATE_TARGET_PLAN = targeted.validate_target_plan
PLAN_KEYS = previous.PLAN_KEYS
RECEIPT_KEYS = frozenset(
    {
        "policy_id",
        "binding_count",
        "build_calls",
        "replay_calls",
        "validation_calls",
        "active_supported_plan_builds",
        "proposal_seeded_plan_builds",
        "cell_discovery_plan_builds",
        "no_plan_builds",
        "proposal_seed_is_query_only",
        "cell_discovery_seed_value_present",
        "cell_discovery_queries_use_only_frozen_row_and_column",
        "cell_discovery_receives_vote_or_source_credit",
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
        raise ValueError(f"V2.45.15 {label} is invalid")
    return value


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"V2.45.15 {label} is invalid")
    return value


def _finite(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise ValueError(f"V2.45.15 {label} is invalid")
    return float(value)


def _discovery_query_vector(row: str, column: str) -> list[str]:
    visible = row + column
    suffixes = (
        ("官方 记录 独立 来源", "历史 档案 独立 来源")
        if any("\u4e00" <= character <= "\u9fff" for character in visible)
        else (
            "official record independent source",
            "historical archive independent source",
        )
    )
    queries = [f'"{row}" "{column}" {suffix}'[:1_200] for suffix in suffixes]
    if (
        any(not query for query in queries)
        or len(queries) != targeted.MAXIMUM_TARGETED_LOGICAL_QUERIES
        or len(set(item.casefold() for item in queries)) != len(queries)
    ):
        raise ValueError("V2.45.15 discovery query vector drifted")
    return queries


def _transformed_previous_plan(
    active_result: Mapping[str, Any],
) -> dict[str, Any] | None:
    old = previous._build_plan(active_result)
    if old is None:
        return None
    previous._validate_plan(old, active_result=active_result)
    value = copy.deepcopy(old)
    value["role"] = PLAN_ROLE
    value["policy_id"] = POLICY_ID
    value["plan_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "plan_payload_sha256"}
    )
    return value


def _previous_form(value: Mapping[str, Any]) -> dict[str, Any]:
    restored = copy.deepcopy(dict(value))
    restored["role"] = previous.PLAN_ROLE
    restored["policy_id"] = previous.POLICY_ID
    restored["plan_payload_sha256"] = payload_sha256(
        {
            key: item
            for key, item in restored.items()
            if key != "plan_payload_sha256"
        }
    )
    return restored


def _discovery_reachability(
    target: Mapping[str, Any],
    active_votes: list[dict[str, str]],
) -> tuple[int, float] | None:
    proposal_votes = list(target["proposal_votes"])
    required = (
        credit.UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES
        if target["baseline_unknown"]
        else credit.KNOWN_ALTERNATIVE_MINIMUM_SOURCES
    )
    for added in range(1, targeted.MAXIMUM_TARGETED_SOURCES + 1):
        hypothetical = [
            *active_votes,
            *(
                {"hypothesis": DISCOVERY_HYPOTHESIS}
                for _ in range(added)
            ),
        ]
        hypotheses, _prior, proposal_posterior = credit._expanded_frozen_belief(
            target, hypothetical
        )
        if DISCOVERY_HYPOTHESIS not in hypotheses:
            raise ValueError("V2.45.15 discovery hypothesis was not materialized")
        combined = credit._posterior_from_base(
            proposal_posterior, hypotheses, hypothetical
        )
        combined_votes = [*proposal_votes, *hypothetical]
        counts = Counter(str(item["hypothesis"]) for item in combined_votes)
        support = counts[DISCOVERY_HYPOTHESIS]
        competitor = max(
            [
                counts[credit.CURRENT],
                *(
                    counts[item]
                    for item in hypotheses
                    if item
                    not in {
                        credit.CURRENT,
                        credit.OTHER,
                        DISCOVERY_HYPOTHESIS,
                    }
                ),
            ],
            default=0,
        )
        probability = combined[hypotheses.index(DISCOVERY_HYPOTHESIS)]
        if (
            support >= required
            and added >= 1
            and support - competitor >= 1
            and probability >= credit.MINIMUM_ALTERNATIVE_POSTERIOR
        ):
            return added, probability
    return None


def _discovery_candidate(
    validated: Mapping[str, Any],
    target: Mapping[str, Any],
    resolution: Mapping[str, Any],
) -> dict[str, Any] | None:
    if resolution["status"] == "safe_change":
        return None
    proposal_votes = list(target["proposal_votes"])
    active_votes, _ambiguous = credit._bound_votes(
        target, validated["active_observations"]
    )
    hypotheses, _prior, _posterior = credit._expanded_frozen_belief(
        target, active_votes
    )
    concrete = [
        item for item in hypotheses if item not in {credit.CURRENT, credit.OTHER}
    ]
    if concrete:
        return None
    if any(
        str(item["hypothesis"]) not in {credit.CURRENT, credit.OTHER}
        for item in [*proposal_votes, *active_votes]
    ):
        raise ValueError("V2.45.15 concrete vote/hypothesis drifted")
    if (
        int(resolution["selected_alternative_support_count"]) != 0
        or int(resolution["selected_alternative_active_support_count"]) != 0
        or not math.isclose(
            float(resolution["selected_alternative_posterior_probability"]),
            0.0,
            abs_tol=1e-12,
        )
    ):
        return None
    reachable = _discovery_reachability(target, active_votes)
    if reachable is None:
        return None
    additional_needed, projected_probability = reachable
    required = (
        credit.UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES
        if target["baseline_unknown"]
        else credit.KNOWN_ALTERNATIVE_MINIMUM_SOURCES
    )
    margin = int(resolution["selected_alternative_support_margin"])
    return {
        "binding": str(resolution["target_binding_sha256"]),
        "target": target,
        "resolution": resolution,
        "required": required,
        "support_margin": margin,
        "support_margin_deficit": max(0, 1 - margin),
        "additional_needed": additional_needed,
        "projected_probability": projected_probability,
    }


def _build_discovery_plan(
    active_result: Mapping[str, Any],
) -> dict[str, Any] | None:
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
            raise ValueError("V2.45.15 target binding is absent")
        candidate = _discovery_candidate(validated, target, resolution)
        if candidate is not None:
            candidates.append(candidate)
    if not candidates:
        return None
    chosen = min(
        candidates,
        key=lambda item: (
            -float(item["resolution"]["combined_entropy_nats"]),
            int(item["additional_needed"]),
            str(item["binding"]),
        ),
    )
    target = chosen["target"]
    row = " ".join(str(target["row_key"]).split()).strip()
    column = " ".join(str(target["column"]).split()).strip()
    value = {
        "artifact_version": 1,
        "role": PLAN_ROLE,
        "policy_id": POLICY_ID,
        "target_binding_sha256": str(chosen["binding"]),
        "row_key": row,
        "column": column,
        "leading_alternative": "",
        "leading_alternative_hypothesis": "",
        "seed_mode": "cell_discovery",
        "combined_entropy_nats": float(
            chosen["resolution"]["combined_entropy_nats"]
        ),
        "current_alternative_support_count": 0,
        "current_alternative_proposal_support_count": 0,
        "current_alternative_active_support_count": 0,
        "current_alternative_posterior_probability": 0.0,
        "current_alternative_support_margin": int(chosen["support_margin"]),
        "required_support_count": int(chosen["required"]),
        "support_count_deficit": int(chosen["required"]),
        "active_support_deficit": 1,
        "support_margin_deficit": int(chosen["support_margin_deficit"]),
        "minimum_new_active_support_count": 1,
        "projected_alternative_posterior_probability_after_planned_support": round(
            float(chosen["projected_probability"]), 12
        ),
        "support_deficit": int(chosen["additional_needed"]),
        "maximum_targeted_fetches": int(chosen["additional_needed"]),
        "query_vector": _discovery_query_vector(row, column),
        "selection_uses_only_validated_posterior_entropy_and_support_deficit": True,
        "queries_use_only_frozen_row_column_and_leading_alternative": True,
        "proposal_seed_used_for_query_only": False,
        "proposal_votes_receive_no_active_source_credit": True,
        "final_safe_change_thresholds_unchanged": True,
        "benchmark_label_mapping_gold_evaluator_score_or_reward_read": False,
    }
    value["plan_payload_sha256"] = payload_sha256(value)
    return value


def _build_plan(active_result: Mapping[str, Any]) -> dict[str, Any] | None:
    existing = _transformed_previous_plan(active_result)
    return existing if existing is not None else _build_discovery_plan(active_result)


def _validate_discovery_plan(
    copied: Mapping[str, Any], *, active_result: Mapping[str, Any]
) -> None:
    if (
        copied.get("leading_alternative") != ""
        or copied.get("leading_alternative_hypothesis") != ""
        or copied.get("current_alternative_support_count") != 0
        or copied.get("current_alternative_proposal_support_count") != 0
        or copied.get("current_alternative_active_support_count") != 0
        or float(copied.get("current_alternative_posterior_probability", -1))
        != 0.0
        or copied.get("proposal_seed_used_for_query_only") is not False
        or copied.get("query_vector")
        != _discovery_query_vector(
            str(copied.get("row_key")), str(copied.get("column"))
        )
    ):
        raise ValueError("V2.45.15 discovery plan carries a seed value")
    expected = _build_discovery_plan(active_result)
    if expected is None or dict(copied) != expected:
        raise ValueError("V2.45.15 discovery plan replay drifted")


def _validate_plan(
    value: Mapping[str, Any], *, active_result: Mapping[str, Any]
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("plan_payload_sha256", None)
    margin = copied.get("current_alternative_support_margin")
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
        or not isinstance(copied.get("leading_alternative_hypothesis"), str)
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
        or _integer(margin, "support margin") != margin
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
        != max(0, 1 - copied.get("current_alternative_support_margin"))
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
        or not isinstance(copied.get("query_vector"), list)
        or len(copied["query_vector"])
        != targeted.MAXIMUM_TARGETED_LOGICAL_QUERIES
        or any(
            copied.get(name) is not True
            for name in (
                "selection_uses_only_validated_posterior_entropy_and_support_deficit",
                "queries_use_only_frozen_row_column_and_leading_alternative",
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
        raise ValueError("V2.45.15 target plan drifted")
    if copied["seed_mode"] == "cell_discovery":
        _validate_discovery_plan(copied, active_result=active_result)
    else:
        expected = _transformed_previous_plan(active_result)
        if expected is None or copied != expected:
            raise ValueError("V2.45.15 inherited plan replay drifted")
        previous._validate_plan(
            _previous_form(copied), active_result=active_result
        )
    return copied


def build_target_plan(
    active_result: Mapping[str, Any],
) -> dict[str, Any] | None:
    value = _build_plan(active_result)
    return None if value is None else _validate_plan(value, active_result=active_result)


def build_target_plan_without_validation(
    active_result: Mapping[str, Any],
) -> dict[str, Any] | None:
    return _build_plan(active_result)


def validate_target_plan(
    value: Mapping[str, Any], *, active_result: Mapping[str, Any]
) -> dict[str, Any]:
    return _validate_plan(value, active_result=active_result)


class NeutralCellDiscoveryPlanner(
    AbstractContextManager["NeutralCellDiscoveryPlanner"]
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
            "cell_discovery_plan_builds": 0,
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

    def __enter__(self) -> "NeutralCellDiscoveryPlanner":
        if self._active:
            raise RuntimeError("V2.45.15 planner context is already active")
        bindings: tuple[tuple[str, Callable[..., Any], Callable[..., Any]], ...] = (
            ("build_target_plan", ORIGINAL_BUILD_TARGET_PLAN, self._build),
            (
                "build_target_plan_without_validation",
                ORIGINAL_BUILD_TARGET_PLAN_WITHOUT_VALIDATION,
                self._replay,
            ),
            ("validate_target_plan", ORIGINAL_VALIDATE_TARGET_PLAN, self._validate),
        )
        if len(bindings) != EXPECTED_BINDING_COUNT:
            raise RuntimeError("V2.45.15 planner binding surface drifted")
        if any(
            getattr(targeted, name) is not expected
            for name, expected, _replacement in bindings
        ):
            raise RuntimeError("V2.45.15 frozen planner binding drifted")
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
            "cell_discovery_seed_value_present": False,
            "cell_discovery_queries_use_only_frozen_row_and_column": True,
            "cell_discovery_receives_vote_or_source_credit": False,
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
        "cell_discovery_plan_builds",
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
        + copied.get("cell_discovery_plan_builds")
        + copied.get("no_plan_builds")
        or any(
            copied.get(name) is not True
            for name in (
                "proposal_seed_is_query_only",
                "cell_discovery_queries_use_only_frozen_row_and_column",
                "final_source_posterior_margin_and_credit_thresholds_unchanged",
                "bindings_restored",
            )
        )
        or any(
            copied.get(name) is not False
            for name in (
                "cell_discovery_seed_value_present",
                "cell_discovery_receives_vote_or_source_credit",
                "cache_or_cross_task_state_used",
                "task_question_opaque_id_query_url_page_prediction_or_value_emitted",
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
                "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
    ):
        raise ValueError("V2.45.15 planner receipt drifted")
    return copied


__all__ = [
    "PLAN_KEYS",
    "PLAN_ROLE",
    "POLICY_ID",
    "NeutralCellDiscoveryPlanner",
    "build_target_plan",
    "build_target_plan_without_validation",
    "validate_receipt",
    "validate_target_plan",
]
