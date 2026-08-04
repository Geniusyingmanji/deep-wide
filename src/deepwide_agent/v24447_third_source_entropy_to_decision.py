"""Bounded third-source recovery for entropy-to-decision conversion.

V2.44.45 proved that narrative evidence can earn positive epistemic credit,
but no target crossed the unchanged safe-change gate.  For a known baseline
that gate requires three independent supporting sources, while the frozen
active selection admits at most two.  This append-only successor reuses the
already-frozen active-search response, selects the next ranked source that is
disjoint from proposal and active sources, and performs at most one additional
public-page fetch.  It issues no additional model call, logical query, hosted
search batch, or hosted-search provider call.

The original support, posterior, and margin thresholds are unchanged.  A
content-free mutually exclusive partition records why each selected target
did or did not cross the gate.  The private result retains the third lead and
page only so replay validation can prove selection and effect accounting; no
private content is authorized for a public aggregate.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from . import v24390_uncertainty_active_evidence_runtime as runtime
from . import v24437_narrative_title_uncertainty_recovery as parent_recovery
from .v24280_task_union_single_shot import validate_receipt as validate_search_receipt
from .v24312_deadline_reliability import (
    validate_receipt as validate_model_receipt,
)
from .v24316_deadline_search import validate_transport_health
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24325_shared_prefix_revision_runtime import _page_vector
from .v24333_programmatic_support_catalog import _source_key
from .v24355_explicit_partition_runtime import _source_from_lead
from .v24371_batch_stratified_verifier_runtime import _coverage
from .v24378_adaptive_heldout_verifier_runtime import (
    _lead_projection,
    _target_score,
)
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
from .v24438_bounded_narrative_effect_runner import (
    IntegratedBoundedNarrativeOutcome,
    build_envelope as build_parent_envelope,
    run_v24438_task,
    validate_envelope as validate_parent_envelope,
)


POLICY_ID = "v24447_bounded_third_source_entropy_to_decision_v1"
RESULT_ROLE = "v24447_third_source_entropy_to_decision_result"
RECEIPT_ROLE = "v24447_third_source_entropy_to_decision_receipt"
ENVELOPE_ROLE = "v24447_third_source_entropy_to_decision_envelope"
EFFECT_ROLE = "v24447_single_fetch_effect_delta"
MAXIMUM_ACTIVE_SOURCES = 3
MAXIMUM_ADDITIONAL_FETCHES = 1
MAXIMUM_TOTAL_FETCHES = 11
PAGE_PREFIX = "T"
THRESHOLD_PARTITION_FIELDS = (
    "insufficient_support_count",
    "no_active_support_count",
    "posterior_below_threshold_count",
    "support_margin_below_threshold_count",
    "safe_change_count",
)
PRIVATE_KEYS = frozenset(
    {"selected_third_lead", "third_fetch_batches", "third_pages"}
)
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_result",
        "candidate_prediction",
        "extended_narrative_title_projection",
        "extended_active_evidence_result",
        "third_source_private_state",
        "third_source_recovery_receipt",
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
        "third_source_candidate_count",
        "third_source_fetch_attempt_count",
        "third_source_usable_page_count",
        "parent_active_page_count",
        "extended_active_page_count",
        "extended_narrative_projection_count",
        "extended_novel_observation_count",
        "safe_change_count",
        "baseline_confirmed_count",
        "unresolved_count",
        "positive_epistemic_target_count",
        "source_credit_record_count",
        "parent_candidate_changed_cell_count",
        "candidate_changed_cell_count",
        "pre_active_entropy_total_nats",
        "combined_entropy_total_nats",
        "positive_information_gain_total_nats",
        "epistemic_credit_total_nats",
        "decision_credit_total_nats",
        "parent_epistemic_credit_total_nats",
        "parent_decision_credit_total_nats",
        "threshold_failure_partition",
        "known_baseline_minimum_support_sources",
        "unknown_baseline_minimum_support_sources",
        "minimum_alternative_posterior",
        "required_support_margin",
        "active_source_cap",
        "parent_total_fetch_cap",
        "additional_model_requests",
        "additional_logical_queries",
        "additional_search_batches",
        "additional_provider_search_calls",
        "additional_fetch_calls",
        "total_fetch_cap",
        "frozen_active_lead_ranking_reused",
        "proposal_and_existing_active_sources_excluded",
        "parent_narrative_projection_replayed_exactly",
        "safe_change_thresholds_preserved",
        "posterior_and_credit_recomputed_without_model_or_search",
        "third_source_alone_assumed_sufficient",
        "task_private_lead_page_observation_value_prediction_or_source_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)
EFFECT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "third_source_fetch_attempted",
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
        "only_one_public_page_fetch_effect_allowed",
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
        "third_source_result",
        "model_slot_receipt_before_third_source",
        "transport_health_before_third_source",
        "search_single_shot_receipt_before_third_source",
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
class IntegratedThirdSourceOutcome:
    parent: IntegratedBoundedNarrativeOutcome
    third_source_result: dict[str, Any]
    model_slot_receipt_before_third_source: dict[str, Any]
    transport_health_before_third_source: dict[str, Any]
    search_single_shot_receipt_before_third_source: dict[str, Any]
    model_slot_receipt: dict[str, Any]
    transport_health: dict[str, Any]
    search_single_shot_receipt: dict[str, Any]
    effect_delta_receipt: dict[str, Any]


def _nonnegative_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.44.47 {label} is not a nonnegative integer")
    return value


def _finite(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise ValueError(f"V2.44.47 {label} is not a nonnegative finite number")
    return float(value)


def _counter_delta(before: Mapping[str, Any], after: Mapping[str, Any], name: str) -> int:
    left = _nonnegative_integer(before.get(name), f"before {name}")
    right = _nonnegative_integer(after.get(name), f"after {name}")
    if right < left:
        raise ValueError(f"V2.44.47 {name} counter decreased")
    return right - left


def _selected_identities(catalog: Mapping[str, Any]) -> set[tuple[str, str]]:
    return {
        runtime._target_identity(item["row_key"], item["column"])
        for item in runtime._selected_targets(catalog)
    }


def _legacy(parent_result: Mapping[str, Any]) -> Mapping[str, Any]:
    validated = parent_recovery.validate_result(parent_result)
    return validated["parent_result"]["parent_result"]["parent_result"]


def _ranked_active_leads(parent_result: Mapping[str, Any]) -> list[dict[str, str]]:
    legacy = _legacy(parent_result)
    private = legacy["private_replay_state"]
    catalog = validate_uncertainty_catalog(private["uncertainty_catalog"])
    targets = runtime._selected_targets(catalog)
    queries = list(catalog["active_queries"])
    proposal_sources = {
        _source_from_lead(lead)
        for batch in private["proposal_selection_state"]["proposal_batch_leads"]
        for lead in batch
    }
    available: dict[str, dict[str, str]] = {}
    for raw in private["active_union_leads"]:
        lead = _lead_projection(raw)
        source = _source_from_lead(lead)
        if source in proposal_sources or source in available:
            continue
        available[source] = lead
    if len(targets) != len(queries):
        raise ValueError("V2.44.47 frozen target/query vector drifted")
    ranked = sorted(
        available.values(),
        key=lambda lead: (
            tuple(-number for number in _target_score(lead, targets)),
            tuple(-number for number in _coverage(lead, queries)[1]),
            _source_from_lead(lead),
        ),
    )
    selected = [_lead_projection(item) for item in private["selected_active_leads"]]
    if selected != ranked[: len(selected)] or len(selected) > 2:
        raise ValueError("V2.44.47 frozen active source ranking drifted")
    return [copy.deepcopy(item) for item in ranked]


def select_third_source(parent_result: Mapping[str, Any]) -> dict[str, str] | None:
    legacy = _legacy(parent_result)
    selected = [
        _lead_projection(item)
        for item in legacy["private_replay_state"]["selected_active_leads"]
    ]
    selected_sources = {_source_from_lead(item) for item in selected}
    for lead in _ranked_active_leads(parent_result):
        if _source_from_lead(lead) not in selected_sources:
            return copy.deepcopy(lead)
    return None


def _canonical_private_state(
    parent_result: Mapping[str, Any], value: Mapping[str, Any]
) -> dict[str, Any]:
    if set(value) != PRIVATE_KEYS:
        raise ValueError("V2.44.47 private state keys drifted")
    expected_lead = select_third_source(parent_result)
    lead = value.get("selected_third_lead")
    if lead is not None:
        if not isinstance(lead, Mapping):
            raise ValueError("V2.44.47 third lead is not an object")
        lead = _lead_projection(lead)
    if lead != expected_lead:
        raise ValueError("V2.44.47 third lead selection drifted")
    batches = value.get("third_fetch_batches")
    pages = value.get("third_pages")
    if not isinstance(batches, list) or not isinstance(pages, list):
        raise ValueError("V2.44.47 third fetch/page vector drifted")
    if lead is None and (batches or pages):
        raise ValueError("V2.44.47 absent third lead produced artifacts")
    rebuilt = _page_vector(batches, prefix=PAGE_PREFIX, page_chars=5_000)
    if len(rebuilt) > 1:
        raise ValueError("V2.44.47 third fetch produced multiple pages")
    if lead is not None and rebuilt:
        source = _source_from_lead(lead)
        if any(_source_key(str(page["host"])) != source for page in rebuilt):
            rebuilt = []
    if pages != rebuilt:
        raise ValueError("V2.44.47 third page replay drifted")
    return {
        "selected_third_lead": copy.deepcopy(lead),
        "third_fetch_batches": copy.deepcopy(batches),
        "third_pages": copy.deepcopy(rebuilt),
    }


def threshold_failure_partition(
    active_result: Mapping[str, Any],
) -> dict[str, int]:
    validated = validate_active_evidence_result(active_result)
    targets = {
        str(item["target_binding_sha256"]): item
        for item in validated["catalog"]["targets"]
    }
    counts = {name: 0 for name in THRESHOLD_PARTITION_FIELDS}
    for resolution in validated["resolutions"]:
        target = targets.get(str(resolution["target_binding_sha256"]))
        if target is None:
            raise ValueError("V2.44.47 threshold target is absent")
        required = (
            UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES
            if target["baseline_unknown"]
            else KNOWN_ALTERNATIVE_MINIMUM_SOURCES
        )
        if resolution["status"] == "safe_change":
            field = "safe_change_count"
        elif int(resolution["selected_alternative_support_count"]) < required:
            field = "insufficient_support_count"
        elif int(resolution["selected_alternative_active_support_count"]) < 1:
            field = "no_active_support_count"
        elif (
            float(resolution["selected_alternative_posterior_probability"])
            < MINIMUM_ALTERNATIVE_POSTERIOR
        ):
            field = "posterior_below_threshold_count"
        elif int(resolution["selected_alternative_support_margin"]) < 1:
            field = "support_margin_below_threshold_count"
        else:
            raise ValueError("V2.44.47 non-safe resolution passed every threshold")
        counts[field] += 1
    if sum(counts.values()) != int(validated["receipt"]["selected_target_count"]):
        raise ValueError("V2.44.47 threshold partition does not conserve targets")
    return counts


def _compute_result(
    parent_result: Mapping[str, Any], private_state: Mapping[str, Any]
) -> dict[str, Any]:
    validated_parent = parent_recovery.validate_result(parent_result)
    private = _canonical_private_state(validated_parent, private_state)
    anchored = validated_parent["parent_result"]
    structured = anchored["parent_result"]
    legacy = structured["parent_result"]
    baseline = str(legacy["baseline_prediction"])
    legacy_private = legacy["private_replay_state"]
    catalog = validate_uncertainty_catalog(legacy_private["uncertainty_catalog"])
    original_pages = list(legacy_private["active_pages"])
    original_projection = build_narrative_title_anchor_projection(
        baseline,
        original_pages,
        selected_identities=_selected_identities(catalog),
    )
    if original_projection != validated_parent["narrative_title_projection"]:
        raise ValueError("V2.44.47 parent narrative projection drifted")
    extended_pages = [*original_pages, *private["third_pages"]]
    projection = build_narrative_title_anchor_projection(
        baseline,
        extended_pages,
        selected_identities=_selected_identities(catalog),
    )
    validate_narrative_title_anchor_projection(projection)
    active = apply_active_evidence(catalog, projection["observations"])
    validate_active_evidence_result(active)
    candidate, _ = runtime._merge_parent_candidate(legacy["parent_result"], active)
    entropy = active["receipt"]
    parent_entropy = validated_parent["narrative_recovery_receipt"]
    parent_changes = runtime._changed_cells(
        baseline, validated_parent["candidate_prediction"]
    )
    changes = runtime._changed_cells(baseline, candidate)
    parent_observation_keys = {
        runtime._target_identity(item["row_key"], item["column"])
        + (str(item["source_host"]), str(item["value"]))
        for item in original_projection["observations"]
    }
    extended_novel = sum(
        runtime._target_identity(item["row_key"], item["column"])
        + (str(item["source_host"]), str(item["value"]))
        not in parent_observation_keys
        for item in projection["observations"]
    )
    partition = threshold_failure_partition(active)
    attempted = private["selected_third_lead"] is not None
    receipt = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": parent_recovery.POLICY_ID,
        "selected_target_count": int(entropy["selected_target_count"]),
        "frozen_active_lead_count": len(legacy_private["active_union_leads"]),
        "parent_selected_active_source_count": len(
            legacy_private["selected_active_leads"]
        ),
        "third_source_candidate_count": int(attempted),
        "third_source_fetch_attempt_count": int(attempted),
        "third_source_usable_page_count": len(private["third_pages"]),
        "parent_active_page_count": len(original_pages),
        "extended_active_page_count": len(extended_pages),
        "extended_narrative_projection_count": int(
            projection["narrative_projection_count"]
        ),
        "extended_novel_observation_count": int(extended_novel),
        "safe_change_count": int(entropy["safe_change_count"]),
        "baseline_confirmed_count": int(entropy["baseline_confirmed_count"]),
        "unresolved_count": int(entropy["unresolved_count"]),
        "positive_epistemic_target_count": int(
            entropy["positive_epistemic_target_count"]
        ),
        "source_credit_record_count": int(entropy["source_credit_record_count"]),
        "parent_candidate_changed_cell_count": len(parent_changes),
        "candidate_changed_cell_count": len(changes),
        "pre_active_entropy_total_nats": float(
            entropy["pre_active_entropy_total_nats"]
        ),
        "combined_entropy_total_nats": float(
            entropy["combined_entropy_total_nats"]
        ),
        "positive_information_gain_total_nats": float(
            entropy["positive_information_gain_total_nats"]
        ),
        "epistemic_credit_total_nats": float(
            entropy["epistemic_credit_total_nats"]
        ),
        "decision_credit_total_nats": float(entropy["decision_credit_total_nats"]),
        "parent_epistemic_credit_total_nats": float(
            parent_entropy["narrative_recovered_epistemic_credit_total_nats"]
        ),
        "parent_decision_credit_total_nats": float(
            parent_entropy["narrative_recovered_decision_credit_total_nats"]
        ),
        "threshold_failure_partition": partition,
        "known_baseline_minimum_support_sources": KNOWN_ALTERNATIVE_MINIMUM_SOURCES,
        "unknown_baseline_minimum_support_sources": UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES,
        "minimum_alternative_posterior": MINIMUM_ALTERNATIVE_POSTERIOR,
        "required_support_margin": 1,
        "active_source_cap": MAXIMUM_ACTIVE_SOURCES,
        "parent_total_fetch_cap": 10,
        "additional_model_requests": 0,
        "additional_logical_queries": 0,
        "additional_search_batches": 0,
        "additional_provider_search_calls": 0,
        "additional_fetch_calls": int(attempted),
        "total_fetch_cap": MAXIMUM_TOTAL_FETCHES,
        "frozen_active_lead_ranking_reused": True,
        "proposal_and_existing_active_sources_excluded": True,
        "parent_narrative_projection_replayed_exactly": True,
        "safe_change_thresholds_preserved": True,
        "posterior_and_credit_recomputed_without_model_or_search": True,
        "third_source_alone_assumed_sufficient": False,
        "task_private_lead_page_observation_value_prediction_or_source_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_sha256"] = payload_sha256(receipt)
    value = {
        "artifact_version": 1,
        "role": RESULT_ROLE,
        "policy_id": POLICY_ID,
        "parent_result": copy.deepcopy(validated_parent),
        "candidate_prediction": candidate,
        "extended_narrative_title_projection": projection,
        "extended_active_evidence_result": active,
        "third_source_private_state": private,
        "third_source_recovery_receipt": receipt,
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
        "third_source_candidate_count",
        "third_source_fetch_attempt_count",
        "third_source_usable_page_count",
        "parent_active_page_count",
        "extended_active_page_count",
        "extended_narrative_projection_count",
        "extended_novel_observation_count",
        "safe_change_count",
        "baseline_confirmed_count",
        "unresolved_count",
        "positive_epistemic_target_count",
        "source_credit_record_count",
        "parent_candidate_changed_cell_count",
        "candidate_changed_cell_count",
        "known_baseline_minimum_support_sources",
        "unknown_baseline_minimum_support_sources",
        "required_support_margin",
        "active_source_cap",
        "parent_total_fetch_cap",
        "additional_model_requests",
        "additional_logical_queries",
        "additional_search_batches",
        "additional_provider_search_calls",
        "additional_fetch_calls",
        "total_fetch_cap",
    )
    numeric_fields = (
        "pre_active_entropy_total_nats",
        "combined_entropy_total_nats",
        "positive_information_gain_total_nats",
        "epistemic_credit_total_nats",
        "decision_credit_total_nats",
        "parent_epistemic_credit_total_nats",
        "parent_decision_credit_total_nats",
        "minimum_alternative_posterior",
    )
    true_fields = (
        "frozen_active_lead_ranking_reused",
        "proposal_and_existing_active_sources_excluded",
        "parent_narrative_projection_replayed_exactly",
        "safe_change_thresholds_preserved",
        "posterior_and_credit_recomputed_without_model_or_search",
    )
    false_fields = (
        "third_source_alone_assumed_sufficient",
        "task_private_lead_page_observation_value_prediction_or_source_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_policy_id") != parent_recovery.POLICY_ID
        or any(_nonnegative_integer(copied.get(name), name) < 0 for name in count_fields)
        or any(_finite(copied.get(name), name) < 0 for name in numeric_fields)
        or not isinstance(partition, Mapping)
        or tuple(partition) != THRESHOLD_PARTITION_FIELDS
        or any(
            _nonnegative_integer(partition.get(name), name) < 0
            for name in THRESHOLD_PARTITION_FIELDS
        )
        or sum(int(partition[name]) for name in THRESHOLD_PARTITION_FIELDS)
        != copied.get("selected_target_count")
        or copied.get("third_source_candidate_count") not in {0, 1}
        or copied.get("third_source_fetch_attempt_count")
        != copied.get("third_source_candidate_count")
        or copied.get("third_source_usable_page_count")
        > copied.get("third_source_fetch_attempt_count")
        or copied.get("extended_active_page_count")
        != copied.get("parent_active_page_count")
        + copied.get("third_source_usable_page_count")
        or copied.get("safe_change_count")
        + copied.get("baseline_confirmed_count")
        + copied.get("unresolved_count")
        != copied.get("selected_target_count")
        or copied.get("safe_change_count") != partition.get("safe_change_count")
        or copied.get("known_baseline_minimum_support_sources")
        != KNOWN_ALTERNATIVE_MINIMUM_SOURCES
        or copied.get("unknown_baseline_minimum_support_sources")
        != UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES
        or copied.get("minimum_alternative_posterior")
        != MINIMUM_ALTERNATIVE_POSTERIOR
        or copied.get("active_source_cap") != MAXIMUM_ACTIVE_SOURCES
        or copied.get("additional_fetch_calls")
        != copied.get("third_source_fetch_attempt_count")
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
        or copied.get("decision_credit_total_nats", 0)
        > copied.get("epistemic_credit_total_nats", 0) + 1e-12
        or (
            copied.get("decision_credit_total_nats", 0) > 0
            and copied.get("safe_change_count") == 0
        )
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.47 recovery receipt drifted")
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
        or not isinstance(copied.get("extended_narrative_title_projection"), Mapping)
        or not isinstance(copied.get("extended_active_evidence_result"), Mapping)
        or not isinstance(copied.get("third_source_private_state"), Mapping)
        or not isinstance(copied.get("third_source_recovery_receipt"), Mapping)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.47 result identity drifted")
    parent_recovery.validate_result(copied["parent_result"])
    validate_narrative_title_anchor_projection(
        copied["extended_narrative_title_projection"]
    )
    validate_active_evidence_result(copied["extended_active_evidence_result"])
    validate_recovery_receipt(copied["third_source_recovery_receipt"])
    expected = _compute_result(
        copied["parent_result"], copied["third_source_private_state"]
    )
    if copied != expected:
        raise ValueError("V2.44.47 result replay drifted")
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
    third_source_fetch_attempted: bool,
) -> dict[str, Any]:
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
    remaining = (
        0.0
        <= float(after_model["remaining_seconds_at_receipt"])
        <= float(before_model["remaining_seconds_at_receipt"]) + 1e-6
    )
    model_deadline = not (
        before_model["deadline_exhausted"] is True
        and after_model["deadline_exhausted"] is False
    )
    transport_deadline = not (
        before_transport["deadline_exhausted"] is True
        and after_transport["deadline_exhausted"] is False
    )
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
        "third_source_fetch_attempted": bool(third_source_fetch_attempted),
        "additional_model_acquisitions": int(after_model["acquisitions"])
        - int(before_model["acquisitions"]),
        # The model receipt effect surface is unchanged in full.  Provider
        # attempts cannot occur without a slot acquisition, so zero delta in
        # that surface also proves zero additional attempts.
        "additional_model_attempts": 0,
        "additional_hosted_search_attempts": deltas["hosted_search_attempts"],
        "additional_hosted_search_deadline_failures": deltas[
            "hosted_search_deadline_failures"
        ],
        "additional_hard_fetch_helper_calls": deltas["hard_fetch_helper_calls"],
        "additional_fetch_deadline_rejections": deltas[
            "fetch_deadline_rejections"
        ],
        "additional_hard_fetch_deadline_failures": deltas[
            "hard_fetch_deadline_failures"
        ],
        "additional_fetch_helper_failures": deltas["fetch_helper_failures"],
        "additional_fetch_effects": fetch_effects,
        "model_effect_and_static_fields_equal": model_equal,
        "model_remaining_seconds_nonincreasing": remaining,
        "model_deadline_state_monotonic": model_deadline,
        "search_shape_fields_equal": before_search == after_search,
        "transport_deadline_state_monotonic": transport_deadline,
        "only_one_public_page_fetch_effect_allowed": True,
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
    true_fields = (
        "model_effect_and_static_fields_equal",
        "model_remaining_seconds_nonincreasing",
        "model_deadline_state_monotonic",
        "search_shape_fields_equal",
        "transport_deadline_state_monotonic",
        "only_one_public_page_fetch_effect_allowed",
    )
    false_fields = (
        "question_prompt_response_query_url_page_prediction_candidate_value_or_source_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(copied) != EFFECT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != EFFECT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(copied.get("third_source_fetch_attempted"), bool)
        or any(_nonnegative_integer(copied.get(name), name) < 0 for name in counts)
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
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
        != copied.get("additional_hard_fetch_helper_calls")
        + copied.get("additional_fetch_deadline_rejections")
        or copied.get("additional_fetch_effects")
        != int(copied.get("third_source_fetch_attempted"))
        or copied.get("additional_hard_fetch_deadline_failures")
        + copied.get("additional_fetch_helper_failures")
        > copied.get("additional_hard_fetch_helper_calls")
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.47 effect delta receipt drifted")
    return copy.deepcopy(copied)


def run_v24447_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    partition_seed_sha256: str,
    limits: Any,
    monotonic: Callable[[], float],
) -> IntegratedThirdSourceOutcome:
    parent = run_v24438_task(
        task,
        model=model,
        search=search,
        partition_seed_sha256=partition_seed_sha256,
        limits=limits,
        monotonic=monotonic,
    )
    before_model = copy.deepcopy(parent.model_slot_receipt)
    before_transport = copy.deepcopy(parent.transport_health)
    before_search = copy.deepcopy(parent.search_single_shot_receipt)
    lead = select_third_source(parent.narrative_title_result)
    batches = search.fetch_urls([lead]) if lead is not None else []
    pages = _page_vector(batches, prefix=PAGE_PREFIX, page_chars=int(limits.page_chars))
    if len(pages) > 1:
        raise ValueError("V2.44.47 third fetch returned multiple usable pages")
    if lead is not None and pages:
        source = _source_from_lead(lead)
        if any(_source_key(str(page["host"])) != source for page in pages):
            pages = []
    private = {
        "selected_third_lead": copy.deepcopy(lead),
        "third_fetch_batches": copy.deepcopy(list(batches)),
        "third_pages": copy.deepcopy(pages),
    }
    result = _compute_result(parent.narrative_title_result, private)
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
        third_source_fetch_attempted=lead is not None,
    )
    outcome = IntegratedThirdSourceOutcome(
        parent=parent,
        third_source_result=result,
        model_slot_receipt_before_third_source=before_model,
        transport_health_before_third_source=before_transport,
        search_single_shot_receipt_before_third_source=before_search,
        model_slot_receipt=after_model,
        transport_health=after_transport,
        search_single_shot_receipt=after_search,
        effect_delta_receipt=effect,
    )
    validate_cross_artifacts(
        build_parent_envelope(parent),
        result,
        model_slot_receipt_before_third_source=before_model,
        transport_health_before_third_source=before_transport,
        search_single_shot_receipt_before_third_source=before_search,
        model_slot_receipt=after_model,
        transport_health=after_transport,
        search_single_shot_receipt=after_search,
        effect_delta_receipt=effect,
        expected_model_cap=int(after_model["slot_cap"]),
    )
    return outcome


def validate_cross_artifacts(
    parent_envelope: Mapping[str, Any],
    third_source_result: Mapping[str, Any],
    *,
    model_slot_receipt_before_third_source: Mapping[str, Any],
    transport_health_before_third_source: Mapping[str, Any],
    search_single_shot_receipt_before_third_source: Mapping[str, Any],
    model_slot_receipt: Mapping[str, Any],
    transport_health: Mapping[str, Any],
    search_single_shot_receipt: Mapping[str, Any],
    effect_delta_receipt: Mapping[str, Any],
    expected_model_cap: int,
) -> None:
    parent = validate_parent_envelope(parent_envelope)
    result = validate_result(third_source_result)
    effect = validate_effect_delta_receipt(effect_delta_receipt)
    if result["parent_result"] != parent["narrative_title_result"]:
        raise ValueError("V2.44.47 parent result drifted from parent envelope")
    expected = build_effect_delta_receipt(
        model_before=model_slot_receipt_before_third_source,
        model_after=model_slot_receipt,
        transport_before=transport_health_before_third_source,
        transport_after=transport_health,
        search_before=search_single_shot_receipt_before_third_source,
        search_after=search_single_shot_receipt,
        expected_model_cap=expected_model_cap,
        third_source_fetch_attempted=bool(
            result["third_source_recovery_receipt"]["third_source_fetch_attempt_count"]
        ),
    )
    if expected != effect:
        raise ValueError("V2.44.47 effect delta replay drifted")


def build_envelope(outcome: IntegratedThirdSourceOutcome) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": ENVELOPE_ROLE,
        "policy_id": POLICY_ID,
        "parent_envelope": build_parent_envelope(outcome.parent),
        "third_source_result": copy.deepcopy(outcome.third_source_result),
        "model_slot_receipt_before_third_source": copy.deepcopy(
            outcome.model_slot_receipt_before_third_source
        ),
        "transport_health_before_third_source": copy.deepcopy(
            outcome.transport_health_before_third_source
        ),
        "search_single_shot_receipt_before_third_source": copy.deepcopy(
            outcome.search_single_shot_receipt_before_third_source
        ),
        "model_slot_receipt": copy.deepcopy(outcome.model_slot_receipt),
        "transport_health": copy.deepcopy(outcome.transport_health),
        "search_single_shot_receipt": copy.deepcopy(
            outcome.search_single_shot_receipt
        ),
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


def run_and_persist_v24447_task(
    task: Mapping[str, Any],
    *,
    model_factory: Callable[[], Any],
    search_factory: Callable[[], Any],
    partition_seed_sha256: str,
    limits: Any,
    monotonic: Callable[[], float],
    expected_model_cap: int,
    writer: Callable[[str, Mapping[str, Any]], None],
) -> IntegratedThirdSourceOutcome:
    """Run V2.44.47 and persist terminal artifacts with failure observability."""

    model: Any = None
    search: Any = None
    stage = "model_construction"
    try:
        model = model_factory()
        stage = "search_construction"
        search = search_factory()
        stage = "runtime"
        outcome = run_v24447_task(
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
            model_receipt=(outcome.model_slot_receipt if model_written else None),
            transport_health=(outcome.transport_health if transport_written else None),
            search_receipt=(
                outcome.search_single_shot_receipt if search_written else None
            ),
            expected_model_cap=expected_model_cap,
        )
        writer(FAILURE_NAME, snapshot)
        raise
    return outcome


def validate_envelope(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("envelope_payload_sha256", None)
    mapping_fields = (
        "parent_envelope",
        "third_source_result",
        "model_slot_receipt_before_third_source",
        "transport_health_before_third_source",
        "search_single_shot_receipt_before_third_source",
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
        or any(not isinstance(copied.get(name), Mapping) for name in mapping_fields)
        or copied.get("private_task_content_present") is not True
        or copied.get("private_task_content_emitted_to_public_aggregate") is not False
        or copied.get("credential_or_privileged_evaluator_content_present") is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.47 envelope identity drifted")
    after_model = copied["model_slot_receipt"]
    validate_cross_artifacts(
        copied["parent_envelope"],
        copied["third_source_result"],
        model_slot_receipt_before_third_source=copied[
            "model_slot_receipt_before_third_source"
        ],
        transport_health_before_third_source=copied[
            "transport_health_before_third_source"
        ],
        search_single_shot_receipt_before_third_source=copied[
            "search_single_shot_receipt_before_third_source"
        ],
        model_slot_receipt=after_model,
        transport_health=copied["transport_health"],
        search_single_shot_receipt=copied["search_single_shot_receipt"],
        effect_delta_receipt=copied["effect_delta_receipt"],
        expected_model_cap=int(after_model.get("slot_cap", -1)),
    )
    return copy.deepcopy(copied)


__all__ = [
    "EFFECT_ROLE",
    "ENVELOPE_ROLE",
    "IntegratedThirdSourceOutcome",
    "MAXIMUM_ACTIVE_SOURCES",
    "MAXIMUM_ADDITIONAL_FETCHES",
    "MAXIMUM_TOTAL_FETCHES",
    "FAILURE_NAME",
    "MODEL_NAME",
    "POLICY_ID",
    "RESULT_ROLE",
    "RESULT_NAME",
    "SEARCH_NAME",
    "THRESHOLD_PARTITION_FIELDS",
    "build_effect_delta_receipt",
    "build_envelope",
    "run_and_persist_v24447_task",
    "run_v24447_task",
    "select_third_source",
    "threshold_failure_partition",
    "validate_effect_delta_receipt",
    "validate_envelope",
    "validate_recovery_receipt",
    "validate_result",
    "TRANSPORT_NAME",
]
