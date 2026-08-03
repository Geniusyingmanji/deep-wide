"""Shared-prefix and cell-conditional entropy kernel for a future search ablation.

This module is deliberately benchmark-external and I/O-free.  It fixes two
problems exposed by V2.43.22:

* page novelty is not answer value; evidence is scored against an anonymous
  target-cell belief and must reduce its conditional entropy;
* independently sampled plans and first-wave retrieval confound a paired
  reserve ablation; both branches must bind to one exact shared prefix.

Reliability tempers likelihood ratios toward one before the Bayesian update.
Low-reliability, weakly corroborated, conflicting, or entropy-increasing
reserve evidence remains quarantined from the core synthesis context.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any


POLICY_ID = "v24323_shared_prefix_reliability_weighted_cell_entropy_v1"
ADMISSION_ROLE = "v24323_cell_conditional_entropy_admission_receipt"
PREFIX_ROLE = "v24323_shared_upstream_prefix_receipt"
PAIR_ROLE = "v24323_shared_prefix_pair_contract"
DISPOSITIONS = frozenset(
    {
        "admit_support",
        "admit_corroborated_override",
        "quarantine_fetch_integrity",
        "quarantine_low_reliability",
        "quarantine_insufficient_independence",
        "quarantine_insufficient_corroboration",
        "quarantine_conflict",
        "quarantine_nonpositive_conditional_gain",
    }
)
CONTEXT_ACTIONS = frozenset(
    {"core_only", "append_reserve_support", "replace_core_after_corroborated_override"}
)
ADMISSION_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "policy",
        "anonymous_belief",
        "anonymous_evidence",
        "reliability",
        "corroboration_factor",
        "conflict_rate",
        "tempered_posterior_probabilities",
        "prior_entropy_nats",
        "posterior_entropy_nats",
        "conditional_entropy_reduction_nats",
        "posterior_prior_kl_information_gain_nats",
        "reserve_map_index",
        "reserve_conflicts_with_core_map",
        "disposition",
        "context_action",
        "raw_page_novelty_or_character_count_used_as_task_value",
        "unreliable_likelihood_tempered_to_neutral",
        "reserve_context_isolated_until_admitted",
        "anonymous_hypothesis_values_or_evidence_content_emitted",
        "question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)
PREFIX_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "visible_plan_sha256",
        "planned_query_vector_sha256",
        "first_wave_search_receipt_sha256",
        "core_evidence_vector_sha256",
        "plan_model_effects",
        "first_wave_search_effects",
        "first_wave_fetch_effects",
        "core_usable_pages",
        "branch_point",
        "prefix_generated_once_then_referenced_by_both_arms",
        "question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)
PAIR_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "shared_prefix_receipt_sha256",
        "baseline_prefix_sha256",
        "candidate_prefix_sha256",
        "synthesis_prompt_template_sha256",
        "model_configuration_sha256",
        "candidate_admission_receipt_sha256",
        "candidate_context_action",
        "baseline_context_action",
        "shared_plan_query_first_wave_and_core_evidence_exact",
        "only_intended_branch_difference",
        "independent_synthesis_calls",
        "synthesis_randomness_shared",
        "strict_shared_upstream_prefix_ablation",
        "reserve_effect_fully_causally_identified",
        "question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _digest(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"V2.43.23 {label} is not a lowercase SHA-256 digest")
    return value


def _finite(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"V2.43.23 {label} is not numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"V2.43.23 {label} is not finite")
    return number


def _unit(value: object, *, label: str) -> float:
    number = _finite(value, label=label)
    if not 0 <= number <= 1:
        raise ValueError(f"V2.43.23 {label} is outside [0,1]")
    return number


def _count(value: object, *, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"V2.43.23 {label} is outside its range")
    return value


def _quantize(value: float) -> float:
    number = round(float(value), 12)
    return 0.0 if number == 0.0 else number


def _probabilities(values: Sequence[float], *, label: str) -> tuple[float, ...]:
    if isinstance(values, (str, bytes)) or len(values) < 2:
        raise ValueError(f"V2.43.23 {label} requires at least two hypotheses")
    numbers = tuple(_finite(value, label=label) for value in values)
    if any(number <= 0 for number in numbers) or not math.isclose(
        sum(numbers), 1.0, rel_tol=1e-9, abs_tol=1e-9
    ):
        raise ValueError(f"V2.43.23 {label} is not a strictly positive distribution")
    return numbers


def _likelihoods(values: Sequence[float], *, size: int) -> tuple[float, ...]:
    if isinstance(values, (str, bytes)) or len(values) != size:
        raise ValueError("V2.43.23 likelihood vector size drifted")
    numbers = tuple(_finite(value, label="likelihood ratio") for value in values)
    if any(number <= 0 for number in numbers):
        raise ValueError("V2.43.23 likelihood ratios must be positive")
    return numbers


def entropy_nats(values: Sequence[float]) -> float:
    probabilities = _probabilities(values, label="entropy distribution")
    return _quantize(-sum(value * math.log(value) for value in probabilities))


def kl_nats(posterior: Sequence[float], prior: Sequence[float]) -> float:
    after = _probabilities(posterior, label="posterior")
    before = _probabilities(prior, label="prior")
    if len(after) != len(before):
        raise ValueError("V2.43.23 KL vector size drifted")
    return _quantize(
        sum(after[index] * math.log(after[index] / before[index]) for index in range(len(after)))
    )


@dataclasses.dataclass(frozen=True)
class EntropyAdmissionPolicy:
    minimum_reliability: float = 0.65
    minimum_independent_sources: int = 2
    minimum_corroborating_sources: int = 2
    maximum_conflict_rate: float = 0.20
    minimum_entropy_reduction_nats: float = 0.02
    override_minimum_reliability: float = 0.85
    override_minimum_corroborating_sources: int = 3
    override_minimum_entropy_reduction_nats: float = 0.08

    def validate(self) -> None:
        _unit(self.minimum_reliability, label="minimum reliability")
        _count(self.minimum_independent_sources, label="minimum independent sources", minimum=1)
        _count(self.minimum_corroborating_sources, label="minimum corroborating sources", minimum=1)
        _unit(self.maximum_conflict_rate, label="maximum conflict rate")
        reduction = _finite(
            self.minimum_entropy_reduction_nats,
            label="minimum entropy reduction",
        )
        if reduction < 0:
            raise ValueError("V2.43.23 minimum entropy reduction is negative")
        override = _unit(
            self.override_minimum_reliability,
            label="override minimum reliability",
        )
        _count(
            self.override_minimum_corroborating_sources,
            label="override minimum corroborating sources",
            minimum=1,
        )
        override_gain = _finite(
            self.override_minimum_entropy_reduction_nats,
            label="override minimum entropy reduction",
        )
        if (
            override < self.minimum_reliability
            or self.override_minimum_corroborating_sources
            < self.minimum_corroborating_sources
            or override_gain < self.minimum_entropy_reduction_nats
        ):
            raise ValueError("V2.43.23 override gate is weaker than support gate")


@dataclasses.dataclass(frozen=True)
class AnonymousCellBelief:
    prior_probabilities: tuple[float, ...]
    core_map_index: int

    def validate(self) -> None:
        values = _probabilities(self.prior_probabilities, label="cell prior")
        if (
            isinstance(self.core_map_index, bool)
            or not isinstance(self.core_map_index, int)
            or not 0 <= self.core_map_index < len(values)
            or values[self.core_map_index] != max(values)
        ):
            raise ValueError("V2.43.23 core MAP index drifted")


@dataclasses.dataclass(frozen=True)
class ReserveEvidenceSignal:
    likelihood_ratios: tuple[float, ...]
    source_reliability: float
    source_independence: float
    fetch_integrity: bool
    independent_sources: int
    corroborating_sources: int
    conflicting_sources: int
    evidence_chars: int

    def validate(self, *, hypothesis_count: int) -> None:
        _likelihoods(self.likelihood_ratios, size=hypothesis_count)
        _unit(self.source_reliability, label="source reliability")
        _unit(self.source_independence, label="source independence")
        if not isinstance(self.fetch_integrity, bool):
            raise ValueError("V2.43.23 fetch integrity is not boolean")
        independent = _count(self.independent_sources, label="independent sources")
        corroborating = _count(self.corroborating_sources, label="corroborating sources")
        conflicting = _count(self.conflicting_sources, label="conflicting sources")
        _count(self.evidence_chars, label="evidence characters")
        if max(corroborating, conflicting) > independent:
            raise ValueError("V2.43.23 evidence source counts drifted")


def _reliability(
    signal: ReserveEvidenceSignal, policy: EntropyAdmissionPolicy
) -> tuple[float, float, float]:
    corroboration_factor = min(
        1.0,
        signal.corroborating_sources / policy.minimum_corroborating_sources,
    )
    denominator = signal.corroborating_sources + signal.conflicting_sources
    conflict_rate = signal.conflicting_sources / max(1, denominator)
    reliability = (
        math.sqrt(signal.source_reliability * signal.source_independence)
        * corroboration_factor
        * (1.0 - conflict_rate)
        * float(signal.fetch_integrity)
    )
    return (
        _quantize(reliability),
        _quantize(corroboration_factor),
        _quantize(conflict_rate),
    )


def _compute_admission(
    belief: AnonymousCellBelief,
    signal: ReserveEvidenceSignal,
    *,
    policy: EntropyAdmissionPolicy,
) -> dict[str, Any]:
    policy.validate()
    belief.validate()
    prior = _probabilities(belief.prior_probabilities, label="cell prior")
    signal.validate(hypothesis_count=len(prior))
    likelihood = _likelihoods(signal.likelihood_ratios, size=len(prior))
    reliability, corroboration_factor, conflict_rate = _reliability(signal, policy)
    # Power likelihood tempering is Bayesian evidence discounting.  At
    # reliability zero every likelihood becomes one and the posterior equals
    # the core prior; unreliable surprise cannot manufacture information gain.
    tempered = tuple(math.exp(reliability * math.log(value)) for value in likelihood)
    normalizer = sum(prior[index] * tempered[index] for index in range(len(prior)))
    posterior = tuple(
        prior[index] * tempered[index] / normalizer for index in range(len(prior))
    )
    prior_entropy = entropy_nats(prior)
    posterior_entropy = entropy_nats(posterior)
    entropy_reduction = _quantize(prior_entropy - posterior_entropy)
    information_gain = kl_nats(posterior, prior)
    reserve_map = max(range(len(posterior)), key=posterior.__getitem__)
    conflicts_with_core = reserve_map != belief.core_map_index

    if not signal.fetch_integrity:
        disposition = "quarantine_fetch_integrity"
    elif signal.independent_sources < policy.minimum_independent_sources:
        disposition = "quarantine_insufficient_independence"
    elif signal.corroborating_sources < policy.minimum_corroborating_sources:
        disposition = "quarantine_insufficient_corroboration"
    elif reliability < policy.minimum_reliability:
        disposition = "quarantine_low_reliability"
    elif entropy_reduction < policy.minimum_entropy_reduction_nats:
        disposition = "quarantine_nonpositive_conditional_gain"
    elif conflicts_with_core:
        if (
            conflict_rate <= policy.maximum_conflict_rate
            and reliability >= policy.override_minimum_reliability
            and signal.corroborating_sources
            >= policy.override_minimum_corroborating_sources
            and entropy_reduction
            >= policy.override_minimum_entropy_reduction_nats
        ):
            disposition = "admit_corroborated_override"
        else:
            disposition = "quarantine_conflict"
    elif conflict_rate > policy.maximum_conflict_rate:
        disposition = "quarantine_conflict"
    else:
        disposition = "admit_support"

    action = {
        "admit_support": "append_reserve_support",
        "admit_corroborated_override": "replace_core_after_corroborated_override",
    }.get(disposition, "core_only")
    value = {
        "artifact_version": 1,
        "role": ADMISSION_ROLE,
        "policy_id": POLICY_ID,
        "policy": dataclasses.asdict(policy),
        "anonymous_belief": {
            "hypothesis_count": len(prior),
            "prior_probabilities": [_quantize(item) for item in prior],
            "core_map_index": belief.core_map_index,
        },
        "anonymous_evidence": {
            "likelihood_ratios": [_quantize(item) for item in likelihood],
            "source_reliability": _quantize(signal.source_reliability),
            "source_independence": _quantize(signal.source_independence),
            "fetch_integrity": signal.fetch_integrity,
            "independent_sources": signal.independent_sources,
            "corroborating_sources": signal.corroborating_sources,
            "conflicting_sources": signal.conflicting_sources,
            "evidence_chars": signal.evidence_chars,
        },
        "reliability": reliability,
        "corroboration_factor": corroboration_factor,
        "conflict_rate": conflict_rate,
        "tempered_posterior_probabilities": [_quantize(item) for item in posterior],
        "prior_entropy_nats": prior_entropy,
        "posterior_entropy_nats": posterior_entropy,
        "conditional_entropy_reduction_nats": entropy_reduction,
        "posterior_prior_kl_information_gain_nats": information_gain,
        "reserve_map_index": reserve_map,
        "reserve_conflicts_with_core_map": conflicts_with_core,
        "disposition": disposition,
        "context_action": action,
        "raw_page_novelty_or_character_count_used_as_task_value": False,
        "unreliable_likelihood_tempered_to_neutral": True,
        "reserve_context_isolated_until_admitted": True,
        "anonymous_hypothesis_values_or_evidence_content_emitted": False,
        "question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    return value


def admit_reserve_evidence(
    belief: AnonymousCellBelief,
    signal: ReserveEvidenceSignal,
    *,
    policy: EntropyAdmissionPolicy | None = None,
) -> dict[str, Any]:
    value = _compute_admission(
        belief,
        signal,
        policy=policy or EntropyAdmissionPolicy(),
    )
    validate_admission_receipt(value)
    return value


def validate_admission_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    belief = value.get("anonymous_belief")
    evidence = value.get("anonymous_evidence")
    raw_policy = value.get("policy")
    if (
        set(value) != ADMISSION_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != ADMISSION_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("disposition") not in DISPOSITIONS
        or value.get("context_action") not in CONTEXT_ACTIONS
        or not isinstance(belief, Mapping)
        or not isinstance(evidence, Mapping)
        or not isinstance(raw_policy, Mapping)
        or value.get("raw_page_novelty_or_character_count_used_as_task_value")
        is not False
        or value.get("unreliable_likelihood_tempered_to_neutral") is not True
        or value.get("reserve_context_isolated_until_admitted") is not True
        or value.get("anonymous_hypothesis_values_or_evidence_content_emitted")
        is not False
        or value.get(
            "question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get("file_environment_network_model_search_fetch_or_process_accessed")
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.23 admission receipt identity drifted")
    try:
        policy = EntropyAdmissionPolicy(**dict(raw_policy))
        prior = tuple(float(item) for item in belief["prior_probabilities"])
        cell = AnonymousCellBelief(prior, int(belief["core_map_index"]))
        signal = ReserveEvidenceSignal(
            likelihood_ratios=tuple(float(item) for item in evidence["likelihood_ratios"]),
            source_reliability=float(evidence["source_reliability"]),
            source_independence=float(evidence["source_independence"]),
            fetch_integrity=evidence["fetch_integrity"],
            independent_sources=int(evidence["independent_sources"]),
            corroborating_sources=int(evidence["corroborating_sources"]),
            conflicting_sources=int(evidence["conflicting_sources"]),
            evidence_chars=int(evidence["evidence_chars"]),
        )
        expected = _compute_admission(cell, signal, policy=policy)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("V2.43.23 admission replay inputs drifted") from error
    if dict(value) != expected:
        raise ValueError("V2.43.23 admission receipt replay drifted")
    return dict(value)


def build_shared_prefix_receipt(
    *,
    visible_plan_sha256: str,
    planned_query_vector_sha256: str,
    first_wave_search_receipt_sha256: str,
    core_evidence_vector_sha256: str,
    plan_model_effects: int,
    first_wave_search_effects: int,
    first_wave_fetch_effects: int,
    core_usable_pages: int,
) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": PREFIX_ROLE,
        "policy_id": POLICY_ID,
        "visible_plan_sha256": _digest(visible_plan_sha256, label="plan digest"),
        "planned_query_vector_sha256": _digest(
            planned_query_vector_sha256, label="query digest"
        ),
        "first_wave_search_receipt_sha256": _digest(
            first_wave_search_receipt_sha256, label="search receipt digest"
        ),
        "core_evidence_vector_sha256": _digest(
            core_evidence_vector_sha256, label="core evidence digest"
        ),
        "plan_model_effects": _count(plan_model_effects, label="plan effects"),
        "first_wave_search_effects": _count(
            first_wave_search_effects, label="first-wave search effects"
        ),
        "first_wave_fetch_effects": _count(
            first_wave_fetch_effects, label="first-wave fetch effects"
        ),
        "core_usable_pages": _count(core_usable_pages, label="core usable pages"),
        "branch_point": "after_exact_core_evidence_freeze_before_reserve_and_synthesis",
        "prefix_generated_once_then_referenced_by_both_arms": True,
        "question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    validate_shared_prefix_receipt(value)
    return value


def validate_shared_prefix_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    if (
        set(value) != PREFIX_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != PREFIX_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("branch_point")
        != "after_exact_core_evidence_freeze_before_reserve_and_synthesis"
        or value.get("prefix_generated_once_then_referenced_by_both_arms") is not True
        or value.get(
            "question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.23 shared-prefix receipt drifted")
    for name in (
        "visible_plan_sha256",
        "planned_query_vector_sha256",
        "first_wave_search_receipt_sha256",
        "core_evidence_vector_sha256",
    ):
        _digest(value.get(name), label=name)
    for name in (
        "plan_model_effects",
        "first_wave_search_effects",
        "first_wave_fetch_effects",
        "core_usable_pages",
    ):
        _count(value.get(name), label=name)
    if (
        value["plan_model_effects"] != 1
        or value["first_wave_search_effects"] < 1
        or value["first_wave_fetch_effects"] < value["core_usable_pages"]
        or value["core_usable_pages"] <= 0
    ):
        raise ValueError("V2.43.23 shared-prefix effect identity drifted")
    return dict(value)


def build_pair_contract(
    *,
    shared_prefix: Mapping[str, Any],
    baseline_prefix_sha256: str,
    candidate_prefix_sha256: str,
    synthesis_prompt_template_sha256: str,
    model_configuration_sha256: str,
    candidate_admission: Mapping[str, Any],
) -> dict[str, Any]:
    prefix = validate_shared_prefix_receipt(shared_prefix)
    admission = validate_admission_receipt(candidate_admission)
    prefix_sha = str(prefix["receipt_sha256"])
    baseline = _digest(baseline_prefix_sha256, label="baseline prefix digest")
    candidate = _digest(candidate_prefix_sha256, label="candidate prefix digest")
    if baseline != prefix_sha or candidate != prefix_sha:
        raise ValueError("V2.43.23 branch prefix identity drifted")
    value = {
        "artifact_version": 1,
        "role": PAIR_ROLE,
        "policy_id": POLICY_ID,
        "shared_prefix_receipt_sha256": prefix_sha,
        "baseline_prefix_sha256": baseline,
        "candidate_prefix_sha256": candidate,
        "synthesis_prompt_template_sha256": _digest(
            synthesis_prompt_template_sha256, label="synthesis prompt digest"
        ),
        "model_configuration_sha256": _digest(
            model_configuration_sha256, label="model configuration digest"
        ),
        "candidate_admission_receipt_sha256": str(admission["receipt_sha256"]),
        "candidate_context_action": admission["context_action"],
        "baseline_context_action": "core_only",
        "shared_plan_query_first_wave_and_core_evidence_exact": True,
        "only_intended_branch_difference": "admitted_reserve_evidence_context",
        "independent_synthesis_calls": 2,
        "synthesis_randomness_shared": False,
        "strict_shared_upstream_prefix_ablation": True,
        "reserve_effect_fully_causally_identified": False,
        "question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    validate_pair_contract(value)
    return value


def validate_pair_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    if (
        set(value) != PAIR_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != PAIR_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("shared_prefix_receipt_sha256")
        != value.get("baseline_prefix_sha256")
        or value.get("shared_prefix_receipt_sha256")
        != value.get("candidate_prefix_sha256")
        or value.get("shared_plan_query_first_wave_and_core_evidence_exact") is not True
        or value.get("only_intended_branch_difference")
        != "admitted_reserve_evidence_context"
        or value.get("independent_synthesis_calls") != 2
        or value.get("synthesis_randomness_shared") is not False
        or value.get("strict_shared_upstream_prefix_ablation") is not True
        or value.get("reserve_effect_fully_causally_identified") is not False
        or value.get(
            "question_query_url_host_page_prediction_answer_opaque_id_or_credential_emitted"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.23 pair contract drifted")
    for name in (
        "shared_prefix_receipt_sha256",
        "baseline_prefix_sha256",
        "candidate_prefix_sha256",
        "synthesis_prompt_template_sha256",
        "model_configuration_sha256",
        "candidate_admission_receipt_sha256",
    ):
        _digest(value.get(name), label=name)
    if value.get("baseline_context_action") != "core_only" or value.get(
        "candidate_context_action"
    ) not in CONTEXT_ACTIONS:
        raise ValueError("V2.43.23 branch context action drifted")
    return dict(value)


__all__ = [
    "AnonymousCellBelief",
    "EntropyAdmissionPolicy",
    "ReserveEvidenceSignal",
    "admit_reserve_evidence",
    "build_pair_contract",
    "build_shared_prefix_receipt",
    "entropy_nats",
    "kl_nats",
    "payload_sha256",
    "validate_admission_receipt",
    "validate_pair_contract",
    "validate_shared_prefix_receipt",
]
