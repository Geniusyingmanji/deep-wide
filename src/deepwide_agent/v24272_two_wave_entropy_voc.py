"""Pure label-blind entropy/VOC kernel for two-wave retrieval.

This build-only successor does not perform model, search, fetch, file, process,
or evaluator I/O.  It receives aggregate observations from the first retrieval
wave and decides whether a bounded delta-only second wave has positive proxy
value after latency cost.

The entropy term is deliberately narrow and auditable: a Beta--Bernoulli
posterior models the rate at which a fetched page supplies *novel usable
evidence*.  ``expected_information_gain_nats`` is the exact expected decrease
in posterior differential entropy after the preregistered number of additional
fetches.  It is transport/evidence uncertainty, not answer correctness entropy,
not benchmark reward, and not causal credit.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any


POLICY_ID = "v24272_label_blind_two_wave_entropy_voc_build_only_v1"
RECEIPT_ROLE = "v24272_two_wave_entropy_voc_decision_receipt"
DECISIONS = frozenset({"expand", "stop"})
REASONS = frozenset(
    {
        "first_wave_sufficient",
        "positive_entropy_voc",
        "nonpositive_entropy_voc",
        "latency_ceiling",
        "no_delta_budget",
    }
)
RISK_LAYERS = ("anchor", "coverage", "row_eligibility", "cell_value")
RISK_WEIGHTS = {
    "anchor": 0.20,
    "coverage": 0.35,
    "row_eligibility": 0.20,
    "cell_value": 0.25,
}
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "label_blind",
        "policy",
        "first_wave",
        "delta_budget",
        "novelty_posterior",
        "four_layer_risk_before",
        "four_layer_expected_risk_after",
        "terminal_risk_proxy_before",
        "terminal_risk_proxy_after",
        "expected_terminal_risk_reduction",
        "expected_information_gain_nats",
        "predicted_delta_seconds",
        "latency_cost",
        "entropy_value",
        "net_value",
        "decision",
        "reason",
        "calibration_status",
        "claim_scope",
        "question_text_or_content_read_by_kernel",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "receipt_sha256",
    }
)


def object_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _finite(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"V2.42.72 {label} is not numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"V2.42.72 {label} is not finite")
    return number


def _nonnegative(value: object, *, label: str) -> float:
    number = _finite(value, label=label)
    if number < 0:
        raise ValueError(f"V2.42.72 {label} is negative")
    return number


def _integer(value: object, *, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"V2.42.72 {label} is outside its range")
    return value


def _unit(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def _quantize(value: float) -> float:
    number = round(float(value), 12)
    return 0.0 if number == 0.0 else number


@dataclasses.dataclass(frozen=True)
class TwoWavePolicy:
    """Frozen build-only policy; values are not benchmark-calibrated."""

    wave1_queries: int = 2
    wave1_fetches: int = 6
    wave2_queries: int = 2
    wave2_fetches: int = 4
    minimum_usable_pages: int = 3
    minimum_novel_pages: int = 3
    minimum_unique_hosts: int = 2
    content_chars_per_column: int = 1_200
    maximum_wave1_seconds: float = 30.0
    latency_loss_per_second: float = 0.005
    information_gain_weight: float = 0.25
    minimum_net_value: float = 0.0
    beta_prior_alpha: float = 1.0
    beta_prior_beta: float = 1.0

    def validate(self) -> None:
        for name in (
            "wave1_queries",
            "wave1_fetches",
            "minimum_usable_pages",
            "minimum_novel_pages",
            "minimum_unique_hosts",
            "content_chars_per_column",
        ):
            _integer(getattr(self, name), label=name, minimum=1)
        for name in ("wave2_queries", "wave2_fetches"):
            _integer(getattr(self, name), label=name, minimum=0)
        if self.minimum_usable_pages > self.wave1_fetches:
            raise ValueError("V2.42.72 usable-page sufficiency exceeds wave one")
        if self.minimum_novel_pages > self.minimum_usable_pages:
            raise ValueError("V2.42.72 novel-page sufficiency exceeds usable pages")
        _nonnegative(self.maximum_wave1_seconds, label="maximum_wave1_seconds")
        if self.maximum_wave1_seconds <= 0:
            raise ValueError("V2.42.72 wave-one latency ceiling is not positive")
        _nonnegative(self.latency_loss_per_second, label="latency_loss_per_second")
        _nonnegative(self.information_gain_weight, label="information_gain_weight")
        _finite(self.minimum_net_value, label="minimum_net_value")
        if self.beta_prior_alpha <= 0 or self.beta_prior_beta <= 0:
            raise ValueError("V2.42.72 Beta prior must be positive")


@dataclasses.dataclass(frozen=True)
class FirstWaveObservation:
    """Content-free aggregate supplied after the first retrieval wave."""

    queries_executed: int
    sources_discovered: int
    fetches_attempted: int
    usable_pages: int
    novel_pages: int
    unique_hosts: int
    content_chars: int
    required_column_count: int
    explicit_row_target: int
    search_seconds: float
    fetch_seconds: float
    unrecoverable_search_failures: int = 0

    def validate(self, policy: TwoWavePolicy) -> None:
        policy.validate()
        for name in (
            "queries_executed",
            "sources_discovered",
            "fetches_attempted",
            "usable_pages",
            "novel_pages",
            "unique_hosts",
            "content_chars",
            "explicit_row_target",
            "unrecoverable_search_failures",
        ):
            _integer(getattr(self, name), label=name)
        _integer(self.required_column_count, label="required_column_count", minimum=1)
        _nonnegative(self.search_seconds, label="search_seconds")
        _nonnegative(self.fetch_seconds, label="fetch_seconds")
        if self.queries_executed > policy.wave1_queries:
            raise ValueError("V2.42.72 first-wave query budget exceeded")
        if self.fetches_attempted > policy.wave1_fetches:
            raise ValueError("V2.42.72 first-wave fetch budget exceeded")
        if self.usable_pages > self.fetches_attempted:
            raise ValueError("V2.42.72 usable pages exceed attempted fetches")
        if self.novel_pages > self.usable_pages:
            raise ValueError("V2.42.72 novel pages exceed usable pages")
        if self.unique_hosts > self.usable_pages:
            raise ValueError("V2.42.72 unique hosts exceed usable pages")
        if self.unrecoverable_search_failures > self.queries_executed:
            raise ValueError("V2.42.72 search failures exceed executed queries")


def _digamma(value: float) -> float:
    """Stable digamma approximation for strictly positive arguments."""

    x = float(value)
    if not math.isfinite(x) or x <= 0:
        raise ValueError("V2.42.72 digamma argument must be positive")
    result = 0.0
    while x < 8.0:
        result -= 1.0 / x
        x += 1.0
    inverse = 1.0 / x
    square = inverse * inverse
    result += (
        math.log(x)
        - 0.5 * inverse
        - square
        * (
            1.0 / 12.0
            - square
            * (1.0 / 120.0 - square * (1.0 / 252.0 - square * 1.0 / 240.0))
        )
    )
    return result


def beta_entropy(alpha: float, beta: float) -> float:
    """Differential entropy of Beta(alpha, beta), in nats."""

    a = _finite(alpha, label="beta alpha")
    b = _finite(beta, label="beta beta")
    if a <= 0 or b <= 0:
        raise ValueError("V2.42.72 Beta parameters must be positive")
    return (
        math.lgamma(a)
        + math.lgamma(b)
        - math.lgamma(a + b)
        - (a - 1.0) * _digamma(a)
        - (b - 1.0) * _digamma(b)
        + (a + b - 2.0) * _digamma(a + b)
    )


def beta_expected_information_gain(
    alpha: float, beta: float, samples: int
) -> float:
    """Exact expected posterior-entropy reduction under Beta--Binomial sampling."""

    a = _finite(alpha, label="information alpha")
    b = _finite(beta, label="information beta")
    n = _integer(samples, label="information samples")
    if a <= 0 or b <= 0:
        raise ValueError("V2.42.72 information posterior is invalid")
    if n == 0:
        return 0.0
    prior_entropy = beta_entropy(a, b)
    log_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    expected = 0.0
    probability_sum = 0.0
    for successes in range(n + 1):
        failures = n - successes
        log_probability = (
            math.lgamma(n + 1)
            - math.lgamma(successes + 1)
            - math.lgamma(failures + 1)
            + math.lgamma(a + successes)
            + math.lgamma(b + failures)
            - math.lgamma(a + b + n)
            - log_beta
        )
        probability = math.exp(log_probability)
        probability_sum += probability
        expected += probability * beta_entropy(a + successes, b + failures)
    if not math.isclose(probability_sum, 1.0, rel_tol=1e-10, abs_tol=1e-10):
        raise RuntimeError("V2.42.72 Beta--Binomial probabilities drifted")
    return max(0.0, prior_entropy - expected)


def _coverage_target(observation: FirstWaveObservation, policy: TwoWavePolicy) -> int:
    visible_units = max(observation.required_column_count, observation.explicit_row_target)
    complexity_target = 2 + int(math.ceil(math.log2(1 + visible_units)))
    return min(policy.wave1_fetches + policy.wave2_fetches, max(policy.minimum_novel_pages, complexity_target))


def _four_layer_risk(
    observation: FirstWaveObservation,
    policy: TwoWavePolicy,
    *,
    extra_sources: float = 0.0,
    extra_usable: float = 0.0,
    extra_novel: float = 0.0,
    extra_hosts: float = 0.0,
    extra_chars: float = 0.0,
) -> dict[str, float]:
    hosts = observation.unique_hosts + max(0.0, extra_hosts)
    sources = observation.sources_discovered + max(0.0, extra_sources)
    usable = observation.usable_pages + max(0.0, extra_usable)
    novel = observation.novel_pages + max(0.0, extra_novel)
    characters = observation.content_chars + max(0.0, extra_chars)
    coverage_target = _coverage_target(observation, policy)
    row_target = observation.explicit_row_target or max(
        policy.minimum_usable_pages, observation.required_column_count
    )
    content_target = policy.content_chars_per_column * observation.required_column_count
    return {
        "anchor": _quantize(1.0 - _unit(hosts / policy.minimum_unique_hosts)),
        "coverage": _quantize(1.0 - _unit(novel / coverage_target)),
        "row_eligibility": _quantize(1.0 - _unit(sources / max(1, row_target))),
        "cell_value": _quantize(1.0 - _unit(characters / max(1, content_target))),
    }


def _terminal_risk(risk: Mapping[str, float]) -> float:
    return _quantize(sum(RISK_WEIGHTS[layer] * float(risk[layer]) for layer in RISK_LAYERS))


def _predicted_seconds(
    observation: FirstWaveObservation, policy: TwoWavePolicy
) -> float:
    if policy.wave2_queries == 0 and policy.wave2_fetches == 0:
        return 0.0
    search_scale = policy.wave2_queries / max(1, observation.queries_executed)
    fetch_scale = policy.wave2_fetches / max(1, observation.fetches_attempted)
    predicted = observation.search_seconds * search_scale + observation.fetch_seconds * fetch_scale
    return _quantize(max(0.001, predicted))


def _decide_two_wave(
    observation: FirstWaveObservation,
    *,
    policy: TwoWavePolicy | None = None,
) -> dict[str, Any]:
    """Return one sealed content-free expand/stop decision."""

    chosen = policy or TwoWavePolicy()
    observation.validate(chosen)
    alpha = chosen.beta_prior_alpha + observation.novel_pages
    beta = chosen.beta_prior_beta + observation.fetches_attempted - observation.novel_pages
    novelty_rate = alpha / (alpha + beta)
    usable_rate = (
        chosen.beta_prior_alpha + observation.usable_pages
    ) / (
        chosen.beta_prior_alpha
        + chosen.beta_prior_beta
        + observation.fetches_attempted
    )
    source_rate = observation.sources_discovered / max(1, observation.queries_executed)
    chars_per_usable = observation.content_chars / max(1, observation.usable_pages)
    expected_novel = chosen.wave2_fetches * novelty_rate
    expected_usable = chosen.wave2_fetches * usable_rate
    expected_sources = chosen.wave2_queries * source_rate
    expected_hosts = min(expected_novel, chosen.wave2_fetches)
    expected_chars = expected_usable * chars_per_usable

    risk_before = _four_layer_risk(observation, chosen)
    risk_after = _four_layer_risk(
        observation,
        chosen,
        extra_sources=expected_sources,
        extra_usable=expected_usable,
        extra_novel=expected_novel,
        extra_hosts=expected_hosts,
        extra_chars=expected_chars,
    )
    terminal_before = _terminal_risk(risk_before)
    terminal_after = _terminal_risk(risk_after)
    risk_reduction = _quantize(max(0.0, terminal_before - terminal_after))
    information_gain = _quantize(
        beta_expected_information_gain(alpha, beta, chosen.wave2_fetches)
    )
    predicted_seconds = _predicted_seconds(observation, chosen)
    latency_cost = _quantize(chosen.latency_loss_per_second * predicted_seconds)
    entropy_value = _quantize(chosen.information_gain_weight * information_gain)
    net_value = _quantize(risk_reduction + entropy_value - latency_cost)
    elapsed = observation.search_seconds + observation.fetch_seconds

    sufficient = (
        observation.usable_pages >= chosen.minimum_usable_pages
        and observation.novel_pages >= chosen.minimum_novel_pages
        and observation.unique_hosts >= chosen.minimum_unique_hosts
        and risk_before["cell_value"] <= 0.0
    )
    if chosen.wave2_queries == 0 and chosen.wave2_fetches == 0:
        decision, reason = "stop", "no_delta_budget"
    elif sufficient:
        decision, reason = "stop", "first_wave_sufficient"
    elif elapsed >= chosen.maximum_wave1_seconds:
        decision, reason = "stop", "latency_ceiling"
    elif net_value > chosen.minimum_net_value:
        decision, reason = "expand", "positive_entropy_voc"
    else:
        decision, reason = "stop", "nonpositive_entropy_voc"

    first_wave = dataclasses.asdict(observation)
    delta_budget = {
        "queries": chosen.wave2_queries if decision == "expand" else 0,
        "fetches": chosen.wave2_fetches if decision == "expand" else 0,
        "delta_only": True,
    }
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "label_blind": True,
        "policy": dataclasses.asdict(chosen),
        "first_wave": first_wave,
        "delta_budget": delta_budget,
        "novelty_posterior": {
            "family": "Beta-Bernoulli",
            "event": "fetched_page_supplies_novel_usable_evidence",
            "alpha": _quantize(alpha),
            "beta": _quantize(beta),
            "posterior_mean": _quantize(novelty_rate),
            "usable_posterior_mean": _quantize(usable_rate),
        },
        "four_layer_risk_before": risk_before,
        "four_layer_expected_risk_after": risk_after,
        "terminal_risk_proxy_before": terminal_before,
        "terminal_risk_proxy_after": terminal_after,
        "expected_terminal_risk_reduction": risk_reduction,
        "expected_information_gain_nats": information_gain,
        "predicted_delta_seconds": predicted_seconds,
        "latency_cost": latency_cost,
        "entropy_value": entropy_value,
        "net_value": net_value,
        "decision": decision,
        "reason": reason,
        "calibration_status": "heuristic_build_only_not_benchmark_calibrated",
        "claim_scope": "transport_evidence_uncertainty_not_answer_entropy_reward_or_causal_credit",
        "question_text_or_content_read_by_kernel": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
    }
    value["receipt_sha256"] = object_sha256(value)
    return value


def decide_two_wave(
    observation: FirstWaveObservation,
    *,
    policy: TwoWavePolicy | None = None,
) -> dict[str, Any]:
    """Return and replay-validate one sealed content-free decision."""

    value = _decide_two_wave(observation, policy=policy)
    validate_receipt(value)
    return value


def validate_receipt(value: Mapping[str, Any]) -> None:
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != RECEIPT_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("label_blind") is not True
        or value.get("decision") not in DECISIONS
        or value.get("reason") not in REASONS
        or value.get("calibration_status")
        != "heuristic_build_only_not_benchmark_calibrated"
        or value.get("claim_scope")
        != "transport_evidence_uncertainty_not_answer_entropy_reward_or_causal_credit"
        or value.get("question_text_or_content_read_by_kernel") is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get("file_environment_network_model_search_fetch_or_process_accessed")
        is not False
    ):
        raise ValueError("V2.42.72 decision receipt identity drifted")
    raw_policy = value.get("policy")
    first = value.get("first_wave")
    delta = value.get("delta_budget")
    posterior = value.get("novelty_posterior")
    before = value.get("four_layer_risk_before")
    after = value.get("four_layer_expected_risk_after")
    if (
        not isinstance(raw_policy, Mapping)
        or set(raw_policy) != {field.name for field in dataclasses.fields(TwoWavePolicy)}
        or not isinstance(first, Mapping)
        or set(first) != {field.name for field in dataclasses.fields(FirstWaveObservation)}
        or not isinstance(delta, Mapping)
        or set(delta) != {"queries", "fetches", "delta_only"}
        or delta.get("delta_only") is not True
        or not isinstance(posterior, Mapping)
        or set(posterior)
        != {"family", "event", "alpha", "beta", "posterior_mean", "usable_posterior_mean"}
        or posterior.get("family") != "Beta-Bernoulli"
        or posterior.get("event")
        != "fetched_page_supplies_novel_usable_evidence"
        or not isinstance(before, Mapping)
        or set(before) != set(RISK_LAYERS)
        or not isinstance(after, Mapping)
        or set(after) != set(RISK_LAYERS)
    ):
        raise ValueError("V2.42.72 decision receipt schema drifted")
    for name in ("queries", "fetches"):
        _integer(delta.get(name), label=f"delta {name}")
    if value["decision"] == "stop" and (delta["queries"] or delta["fetches"]):
        raise ValueError("V2.42.72 stop decision retained a delta budget")
    if value["decision"] == "expand" and not (delta["queries"] or delta["fetches"]):
        raise ValueError("V2.42.72 expand decision lacks a delta budget")
    for mapping in (before, after):
        for layer in RISK_LAYERS:
            number = _finite(mapping[layer], label=f"{layer} risk")
            if not 0 <= number <= 1:
                raise ValueError("V2.42.72 risk proxy is outside [0,1]")
    for name in (
        "terminal_risk_proxy_before",
        "terminal_risk_proxy_after",
        "expected_terminal_risk_reduction",
        "expected_information_gain_nats",
        "predicted_delta_seconds",
        "latency_cost",
        "entropy_value",
    ):
        _nonnegative(value.get(name), label=name)
    _finite(value.get("net_value"), label="net_value")
    if value["terminal_risk_proxy_after"] > value["terminal_risk_proxy_before"]:
        raise ValueError("V2.42.72 expected risk increased after expansion")
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    if not isinstance(seal, str) or seal != object_sha256(unsigned):
        raise ValueError("V2.42.72 decision receipt seal drifted")
    try:
        policy = TwoWavePolicy(**dict(raw_policy))
        observation = FirstWaveObservation(**dict(first))
        expected = _decide_two_wave(observation, policy=policy)
    except (TypeError, ValueError) as exc:
        raise ValueError("V2.42.72 decision receipt replay inputs drifted") from exc
    if dict(value) != expected:
        raise ValueError("V2.42.72 decision receipt replay drifted")


__all__ = [
    "FirstWaveObservation",
    "POLICY_ID",
    "TwoWavePolicy",
    "beta_entropy",
    "beta_expected_information_gain",
    "decide_two_wave",
    "validate_receipt",
]
