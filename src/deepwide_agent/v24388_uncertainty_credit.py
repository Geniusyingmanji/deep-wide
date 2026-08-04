"""Baseline-first uncertainty targeting and entropy credit assignment.

This pure component removes the candidate-activation dependency diagnosed in
V2.43.87.  Every visible baseline cell enters a private uncertainty catalog,
even when no alternative candidate already exists.  Up to two cells are
selected from label-blind posterior entropy, source disagreement, and evidence
sparsity.  Their active queries use only the frozen row and column.

After source-disjoint active evidence arrives, the component recomputes a
multi-hypothesis posterior and separates two credits:

* epistemic credit: positive entropy reduction, including confirmation of the
  baseline; and
* decision credit: the epistemic credit only when an independently supported
  alternative safely changes the final table.

Per-source credit is allocated from normalized leave-one-out marginal
information gain.  The fixed reliability model is deliberately shadow-only:
it does not authorize training, policy updates, benchmark routing, or claims
of calibrated probability.
"""

from __future__ import annotations

import copy
import hashlib
import math
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24325_shared_prefix_revision_runtime as table
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24333_programmatic_support_catalog import _normalize, _source_key


POLICY_ID = "v24388_baseline_first_uncertainty_entropy_credit_v1"
CATALOG_ROLE = "v24388_uncertainty_target_catalog"
RESULT_ROLE = "v24388_uncertainty_evidence_result"
RECEIPT_ROLE = "v24388_uncertainty_entropy_credit_receipt"
MAXIMUM_SELECTED_TARGETS = 2
FIXED_SOURCE_RELIABILITY = 0.75
KNOWN_ALTERNATIVE_MINIMUM_SOURCES = 3
UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES = 2
MINIMUM_ALTERNATIVE_POSTERIOR = 0.80
CURRENT = "__current__"
OTHER = "__other__"
OBSERVATION_KEYS = frozenset(
    {"row_key", "column", "value", "source_host", "fetch_integrity"}
)
TARGET_KEYS = frozenset(
    {
        "target_binding_sha256",
        "row_index",
        "column_index",
        "row_key",
        "column",
        "old_value",
        "baseline_unknown",
        "proposal_votes",
        "proposal_ambiguous_source_count",
        "hypotheses",
        "prior_probabilities",
        "proposal_posterior_probabilities",
        "prior_entropy_nats",
        "proposal_entropy_nats",
        "proposal_information_gain_nats",
        "proposal_bayesian_surprise_nats",
        "proposal_independent_source_count",
        "proposal_disagreement_rate",
        "selection_score",
        "selected",
    }
)
CATALOG_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "baseline_prediction",
        "proposal_observations",
        "targets",
        "selected_target_binding_sha256s",
        "active_queries",
        "maximum_selected_targets",
        "fixed_source_reliability",
        "target_selection_requires_preexisting_candidate_change",
        "active_queries_use_only_frozen_row_and_column",
        "benchmark_label_mapping_gold_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "catalog_payload_sha256",
    }
)
CREDIT_RECORD_KEYS = frozenset(
    {
        "target_binding_sha256",
        "source_key_sha256",
        "marginal_information_gain_nats",
        "epistemic_credit_nats",
        "decision_credit_nats",
    }
)
RESOLUTION_KEYS = frozenset(
    {
        "target_binding_sha256",
        "status",
        "final_value",
        "final_value_changed",
        "active_observation_count",
        "active_independent_source_count",
        "active_ambiguous_source_count",
        "combined_independent_source_count",
        "selected_alternative_support_count",
        "selected_alternative_active_support_count",
        "selected_alternative_posterior_probability",
        "selected_alternative_support_margin",
        "pre_active_entropy_nats",
        "combined_entropy_nats",
        "signed_entropy_reduction_nats",
        "positive_information_gain_nats",
        "bayesian_surprise_nats",
        "epistemic_credit_nats",
        "decision_credit_nats",
        "source_credit_records",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "selected_target_count",
        "active_observation_count",
        "active_independent_source_count",
        "active_ambiguous_source_count",
        "safe_change_count",
        "baseline_confirmed_count",
        "unresolved_count",
        "positive_epistemic_target_count",
        "source_credit_record_count",
        "pre_active_entropy_total_nats",
        "combined_entropy_total_nats",
        "signed_entropy_reduction_total_nats",
        "positive_information_gain_total_nats",
        "bayesian_surprise_total_nats",
        "epistemic_credit_total_nats",
        "decision_credit_total_nats",
        "active_sources_disjoint_from_proposal_sources",
        "epistemic_credit_may_be_positive_without_output_change",
        "decision_credit_requires_safe_output_change",
        "source_credit_uses_normalized_leave_one_out_information_gain",
        "fixed_reliability_is_uncalibrated_shadow_only",
        "training_policy_or_runtime_routing_update_authorized",
        "question_query_url_page_prediction_candidate_value_or_source_emitted",
        "benchmark_label_mapping_gold_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "receipt_sha256",
    }
)
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "catalog",
        "active_observations",
        "resolutions",
        "final_prediction",
        "receipt",
        "result_sha256",
    }
)
STATUSES = frozenset(
    {
        "safe_change",
        "baseline_confirmed",
        "unresolved",
    }
)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalized_value(value: object) -> str:
    return _normalize(value)


def _target_identity(row_key: object, column: object) -> tuple[str, str]:
    return (
        table._support_normalize(row_key),
        table._normalize_column(column),
    )


def _target_binding(row_key: str, column: str, old_value: str) -> str:
    return payload_sha256(
        {
            "row_key": table._support_normalize(row_key),
            "column": table._normalize_column(column),
            "old_value": table._support_normalize(old_value),
        }
    )


def _observation(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or set(raw) != OBSERVATION_KEYS:
        raise ValueError("V2.43.88 observation schema drifted")
    if raw["fetch_integrity"] is not True:
        raise ValueError("V2.43.88 observation lacks fetch integrity")
    row = " ".join(str(raw["row_key"]).split()).strip()
    column = " ".join(str(raw["column"]).split()).strip()
    value = " ".join(str(raw["value"]).split()).strip()
    source = _source_key(str(raw["source_host"]))
    if not row or not column or not value or table._is_unknown(value):
        raise ValueError("V2.43.88 observation content is incomplete")
    return {
        "row_key": row,
        "column": column,
        "value": value,
        "source_host": source,
        "fetch_integrity": True,
    }


def _canonical_observations(
    observations: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if isinstance(observations, (str, bytes)):
        raise ValueError("V2.43.88 observation vector is not a sequence")
    values = [_observation(item) for item in observations]
    values.sort(
        key=lambda item: (
            _target_identity(item["row_key"], item["column"]),
            item["source_host"],
            _normalized_value(item["value"]),
            item["value"],
        )
    )
    return values


def _baseline_targets(baseline: str) -> list[dict[str, Any]]:
    columns, rows = table._table_matrix(baseline)
    rendered = table._render_table(columns, rows)
    canonical, errors = table.extract_valid_markdown_table(rendered, columns)
    if canonical != baseline or errors:
        raise ValueError("V2.43.88 baseline is not canonical")
    seen: set[str] = set()
    targets: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows):
        row_identity = table._support_normalize(row[0])
        if not row_identity or row_identity in seen:
            raise ValueError("V2.43.88 baseline row identity drifted")
        seen.add(row_identity)
        for column_index in range(1, len(columns)):
            targets.append(
                {
                    "target_binding_sha256": _target_binding(
                        row[0], columns[column_index], row[column_index]
                    ),
                    "row_index": row_index,
                    "column_index": column_index,
                    "row_key": row[0],
                    "column": columns[column_index],
                    "old_value": row[column_index],
                    "baseline_unknown": table._is_unknown(row[column_index]),
                }
            )
    targets.sort(key=lambda item: item["target_binding_sha256"])
    return targets


def _bound_votes(
    target: Mapping[str, Any], observations: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, str]], int]:
    identity = _target_identity(target["row_key"], target["column"])
    by_source: dict[str, dict[str, str]] = {}
    ambiguous: set[str] = set()
    for observation in observations:
        if _target_identity(observation["row_key"], observation["column"]) != identity:
            continue
        source = str(observation["source_host"])
        normalized = _normalized_value(observation["value"])
        current = by_source.get(source)
        if current is not None and current["normalized_value"] != normalized:
            ambiguous.add(source)
            continue
        by_source[source] = {
            "source_key": source,
            "value": str(observation["value"]),
            "normalized_value": normalized,
        }
    for source in ambiguous:
        by_source.pop(source, None)
    baseline = _normalized_value(target["old_value"])
    output = []
    for source, vote in sorted(by_source.items()):
        hypothesis = (
            CURRENT
            if not target["baseline_unknown"]
            and vote["normalized_value"] == baseline
            else vote["normalized_value"]
        )
        output.append({**vote, "hypothesis": hypothesis})
    return output, len(ambiguous)


def _hypotheses(
    target: Mapping[str, Any],
    *vote_vectors: Sequence[Mapping[str, str]],
) -> list[str]:
    alternatives = sorted(
        {
            str(vote["hypothesis"])
            for votes in vote_vectors
            for vote in votes
            if vote["hypothesis"] not in {CURRENT, OTHER}
        }
    )
    return [CURRENT, *alternatives, OTHER]


def _prior(target: Mapping[str, Any], hypotheses: Sequence[str]) -> list[float]:
    alternatives = len(hypotheses) - 2
    if target["baseline_unknown"]:
        if alternatives:
            current, other, alternative_mass = 0.25, 0.15, 0.60
        else:
            current, other, alternative_mass = 0.50, 0.50, 0.0
    elif alternatives:
        current, other, alternative_mass = 0.65, 0.10, 0.25
    else:
        current, other, alternative_mass = 0.65, 0.35, 0.0
    values = [current]
    if alternatives:
        values.extend([alternative_mass / alternatives] * alternatives)
    values.append(other)
    if not math.isclose(sum(values), 1.0, abs_tol=1e-12):
        raise ValueError("V2.43.88 prior mass drifted")
    return values


def _posterior(
    prior: Sequence[float],
    hypotheses: Sequence[str],
    votes: Sequence[Mapping[str, str]],
) -> list[float]:
    if len(prior) != len(hypotheses) or len(hypotheses) < 2:
        raise ValueError("V2.43.88 posterior hypothesis drifted")
    index = {value: ordinal for ordinal, value in enumerate(hypotheses)}
    logs = [math.log(max(float(value), 1e-300)) for value in prior]
    other_likelihood = (1.0 - FIXED_SOURCE_RELIABILITY) / (
        len(hypotheses) - 1
    )
    for vote in votes:
        chosen = index.get(str(vote["hypothesis"]), index[OTHER])
        for ordinal in range(len(logs)):
            likelihood = (
                FIXED_SOURCE_RELIABILITY
                if ordinal == chosen
                else other_likelihood
            )
            logs[ordinal] += math.log(max(likelihood, 1e-300))
    maximum = max(logs)
    weights = [math.exp(value - maximum) for value in logs]
    total = sum(weights)
    return [value / total for value in weights]


def _entropy(probabilities: Sequence[float]) -> float:
    return -sum(
        float(value) * math.log(float(value))
        for value in probabilities
        if float(value) > 0
    )


def _kl(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("V2.43.88 KL vector drifted")
    return sum(
        float(p) * math.log(float(p) / max(float(q), 1e-300))
        for p, q in zip(left, right, strict=True)
        if float(p) > 0
    )


def _disagreement(votes: Sequence[Mapping[str, str]]) -> float:
    if not votes:
        return 0.0
    counts = Counter(str(item["hypothesis"]) for item in votes)
    return 1.0 - max(counts.values()) / len(votes)


def _active_query(target: Mapping[str, Any]) -> str:
    row = " ".join(str(target["row_key"]).split()).strip()
    column = " ".join(str(target["column"]).split()).strip()
    visible = row + column
    suffix = (
        "权威 独立 来源"
        if any("\u4e00" <= character <= "\u9fff" for character in visible)
        else "official history independent source"
    )
    return f'"{row}" "{column}" {suffix}'[:1_200]


def _compute_catalog(
    baseline_prediction: str,
    proposal_observations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    observations = _canonical_observations(proposal_observations)
    targets = _baseline_targets(baseline_prediction)
    valid_identities = {
        _target_identity(target["row_key"], target["column"]) for target in targets
    }
    if any(
        _target_identity(item["row_key"], item["column"]) not in valid_identities
        for item in observations
    ):
        raise ValueError("V2.43.88 proposal observation target is not visible")
    projected: list[dict[str, Any]] = []
    for target in targets:
        votes, ambiguous = _bound_votes(target, observations)
        hypotheses = _hypotheses(target, votes)
        prior = _prior(target, hypotheses)
        posterior = _posterior(prior, hypotheses, votes)
        prior_entropy = _entropy(prior)
        proposal_entropy = _entropy(posterior)
        normalized_entropy = proposal_entropy / math.log(len(hypotheses))
        disagreement = _disagreement(votes)
        sparsity = 1.0 / (1.0 + len(votes))
        score = (
            normalized_entropy
            + 0.25 * disagreement
            + 0.10 * sparsity
            + (0.05 if target["baseline_unknown"] else 0.0)
        )
        projected.append(
            {
                **target,
                "proposal_votes": votes,
                "proposal_ambiguous_source_count": ambiguous,
                "hypotheses": hypotheses,
                "prior_probabilities": [round(value, 15) for value in prior],
                "proposal_posterior_probabilities": [
                    round(value, 15) for value in posterior
                ],
                "prior_entropy_nats": round(prior_entropy, 12),
                "proposal_entropy_nats": round(proposal_entropy, 12),
                "proposal_information_gain_nats": round(
                    max(0.0, prior_entropy - proposal_entropy), 12
                ),
                "proposal_bayesian_surprise_nats": round(
                    _kl(posterior, prior), 12
                ),
                "proposal_independent_source_count": len(votes),
                "proposal_disagreement_rate": round(disagreement, 12),
                "selection_score": round(score, 12),
                "selected": False,
            }
        )
    ranked = sorted(
        projected,
        key=lambda item: (
            -float(item["selection_score"]),
            -float(item["proposal_entropy_nats"]),
            int(item["proposal_independent_source_count"]),
            str(item["target_binding_sha256"]),
        ),
    )[:MAXIMUM_SELECTED_TARGETS]
    selected_ids = [str(item["target_binding_sha256"]) for item in ranked]
    selected_set = set(selected_ids)
    for item in projected:
        item["selected"] = item["target_binding_sha256"] in selected_set
    projected.sort(key=lambda item: item["target_binding_sha256"])
    queries = [
        _active_query(next(item for item in projected if item["target_binding_sha256"] == binding))
        for binding in selected_ids
    ]
    if len(set(query.casefold() for query in queries)) != len(queries):
        raise ValueError("V2.43.88 active query vector is not unique")
    value = {
        "artifact_version": 1,
        "role": CATALOG_ROLE,
        "policy_id": POLICY_ID,
        "baseline_prediction": baseline_prediction,
        "proposal_observations": observations,
        "targets": projected,
        "selected_target_binding_sha256s": selected_ids,
        "active_queries": queries,
        "maximum_selected_targets": MAXIMUM_SELECTED_TARGETS,
        "fixed_source_reliability": FIXED_SOURCE_RELIABILITY,
        "target_selection_requires_preexisting_candidate_change": False,
        "active_queries_use_only_frozen_row_and_column": True,
        "benchmark_label_mapping_gold_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
    }
    value["catalog_payload_sha256"] = payload_sha256(value)
    return value


def build_uncertainty_catalog(
    baseline_prediction: str,
    proposal_observations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    value = _compute_catalog(baseline_prediction, proposal_observations)
    validate_uncertainty_catalog(value)
    return value


def validate_uncertainty_catalog(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("catalog_payload_sha256", None)
    targets = value.get("targets")
    selected = value.get("selected_target_binding_sha256s")
    queries = value.get("active_queries")
    if (
        set(value) != CATALOG_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != CATALOG_ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(value.get("baseline_prediction"), str)
        or not isinstance(value.get("proposal_observations"), list)
        or not isinstance(targets, list)
        or any(not isinstance(item, Mapping) or set(item) != TARGET_KEYS for item in targets)
        or not isinstance(selected, list)
        or len(selected) > MAXIMUM_SELECTED_TARGETS
        or len(selected) != len(set(selected))
        or any(re.fullmatch(r"[0-9a-f]{64}", str(item)) is None for item in selected)
        or not isinstance(queries, list)
        or len(queries) != len(selected)
        or any(not isinstance(item, str) or not item for item in queries)
        or value.get("maximum_selected_targets") != MAXIMUM_SELECTED_TARGETS
        or value.get("fixed_source_reliability") != FIXED_SOURCE_RELIABILITY
        or value.get("target_selection_requires_preexisting_candidate_change")
        is not False
        or value.get("active_queries_use_only_frozen_row_and_column") is not True
        or value.get("benchmark_label_mapping_gold_evaluator_score_or_reward_read")
        is not False
        or value.get(
            "file_environment_network_model_search_fetch_process_or_evaluator_accessed"
        )
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.88 uncertainty catalog identity drifted")
    expected = _compute_catalog(
        str(value["baseline_prediction"]), value["proposal_observations"]
    )
    if dict(value) != expected:
        raise ValueError("V2.43.88 uncertainty catalog replay drifted")
    return copy.deepcopy(dict(value))


def _source_credit_records(
    target: Mapping[str, Any],
    hypotheses: Sequence[str],
    prior: Sequence[float],
    proposal_votes: Sequence[Mapping[str, str]],
    active_votes: Sequence[Mapping[str, str]],
    *,
    epistemic_credit: float,
    decision_credit: float,
) -> list[dict[str, Any]]:
    combined = _posterior(prior, hypotheses, [*proposal_votes, *active_votes])
    combined_entropy = _entropy(combined)
    marginals: list[tuple[Mapping[str, str], float]] = []
    for ordinal, vote in enumerate(active_votes):
        without = [
            item for index, item in enumerate(active_votes) if index != ordinal
        ]
        without_entropy = _entropy(
            _posterior(prior, hypotheses, [*proposal_votes, *without])
        )
        marginals.append((vote, max(0.0, without_entropy - combined_entropy)))
    total = sum(value for _, value in marginals)

    def allocate(total_credit: float) -> list[float]:
        """Allocate a 12-decimal credit total without rounding drift."""

        scale = 10**12
        total_units = int(round(max(0.0, total_credit) * scale))
        if total_units == 0 or total <= 0:
            return [0.0] * len(marginals)
        exact_units = [
            total_units * marginal / total for _, marginal in marginals
        ]
        units = [int(math.floor(value)) for value in exact_units]
        remainder = total_units - sum(units)
        order = sorted(
            range(len(marginals)),
            key=lambda ordinal: (
                -(exact_units[ordinal] - units[ordinal]),
                _sha256_text(str(marginals[ordinal][0]["source_key"])),
            ),
        )
        for ordinal in order[:remainder]:
            units[ordinal] += 1
        if sum(units) != total_units:
            raise ValueError("V2.43.88 source credit allocation did not conserve")
        return [value / scale for value in units]

    epistemic_allocations = allocate(epistemic_credit)
    decision_allocations = allocate(decision_credit)
    output: list[dict[str, Any]] = []
    for ordinal, (vote, marginal) in enumerate(marginals):
        output.append(
            {
                "target_binding_sha256": str(target["target_binding_sha256"]),
                "source_key_sha256": _sha256_text(str(vote["source_key"])),
                "marginal_information_gain_nats": round(marginal, 12),
                "epistemic_credit_nats": epistemic_allocations[ordinal],
                "decision_credit_nats": decision_allocations[ordinal],
            }
        )
    output.sort(
        key=lambda item: (
            item["target_binding_sha256"], item["source_key_sha256"]
        )
    )
    return output


def _resolution(
    target: Mapping[str, Any],
    active_votes: Sequence[Mapping[str, str]],
    active_ambiguous: int,
) -> dict[str, Any]:
    proposal_votes = list(target["proposal_votes"])
    hypotheses = _hypotheses(target, proposal_votes, active_votes)
    prior = _prior(target, hypotheses)
    proposal_posterior = _posterior(prior, hypotheses, proposal_votes)
    combined_votes = [*proposal_votes, *active_votes]
    combined = _posterior(prior, hypotheses, combined_votes)
    pre_entropy = _entropy(proposal_posterior)
    combined_entropy = _entropy(combined)
    signed_gain = pre_entropy - combined_entropy
    positive_gain = max(0.0, signed_gain)
    surprise = _kl(combined, proposal_posterior)
    counts = Counter(str(item["hypothesis"]) for item in combined_votes)
    active_counts = Counter(str(item["hypothesis"]) for item in active_votes)
    candidates = [item for item in hypotheses if item not in {CURRENT, OTHER}]
    alternative = max(
        candidates,
        key=lambda item: (
            counts[item],
            combined[hypotheses.index(item)],
            item,
        ),
        default=None,
    )
    support = counts[alternative] if alternative is not None else 0
    active_support = active_counts[alternative] if alternative is not None else 0
    probability = (
        combined[hypotheses.index(alternative)] if alternative is not None else 0.0
    )
    competitor = max(
        [counts[CURRENT], *(counts[item] for item in candidates if item != alternative)],
        default=0,
    )
    margin = support - competitor
    required = (
        UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES
        if target["baseline_unknown"]
        else KNOWN_ALTERNATIVE_MINIMUM_SOURCES
    )
    safe_change = (
        alternative is not None
        and support >= required
        and active_support >= 1
        and probability >= MINIMUM_ALTERNATIVE_POSTERIOR
        and margin >= 1
    )
    active_current = active_counts[CURRENT]
    combined_map = hypotheses[max(range(len(combined)), key=combined.__getitem__)]
    baseline_confirmed = (
        not safe_change
        and combined_map == CURRENT
        and active_current > 0
        and positive_gain > 0
    )
    status = (
        "safe_change"
        if safe_change
        else "baseline_confirmed"
        if baseline_confirmed
        else "unresolved"
    )
    final_value = str(target["old_value"])
    if safe_change and alternative is not None:
        displays = sorted(
            {
                str(item["value"])
                for item in combined_votes
                if item["hypothesis"] == alternative
            },
            key=lambda item: (_normalized_value(item), len(item), item),
        )
        final_value = displays[0]
    raw_marginals = []
    combined_entropy_value = _entropy(
        _posterior(prior, hypotheses, combined_votes)
    )
    for ordinal in range(len(active_votes)):
        without = [
            item for index, item in enumerate(active_votes) if index != ordinal
        ]
        raw_marginals.append(
            max(
                0.0,
                _entropy(_posterior(prior, hypotheses, [*proposal_votes, *without]))
                - combined_entropy_value,
            )
        )
    epistemic = positive_gain if active_votes and sum(raw_marginals) > 0 else 0.0
    decision = epistemic if safe_change else 0.0
    records = _source_credit_records(
        target,
        hypotheses,
        prior,
        proposal_votes,
        active_votes,
        epistemic_credit=epistemic,
        decision_credit=decision,
    )
    value = {
        "target_binding_sha256": str(target["target_binding_sha256"]),
        "status": status,
        "final_value": final_value,
        "final_value_changed": safe_change,
        "active_observation_count": len(active_votes),
        "active_independent_source_count": len(active_votes),
        "active_ambiguous_source_count": active_ambiguous,
        "combined_independent_source_count": len(combined_votes),
        "selected_alternative_support_count": support,
        "selected_alternative_active_support_count": active_support,
        "selected_alternative_posterior_probability": round(probability, 12),
        "selected_alternative_support_margin": margin,
        "pre_active_entropy_nats": round(pre_entropy, 12),
        "combined_entropy_nats": round(combined_entropy, 12),
        "signed_entropy_reduction_nats": round(signed_gain, 12),
        "positive_information_gain_nats": round(positive_gain, 12),
        "bayesian_surprise_nats": round(surprise, 12),
        "epistemic_credit_nats": round(epistemic, 12),
        "decision_credit_nats": round(decision, 12),
        "source_credit_records": records,
    }
    return value


def _compute_update(
    catalog: Mapping[str, Any],
    active_observations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    validated = validate_uncertainty_catalog(catalog)
    active = _canonical_observations(active_observations)
    selected_ids = set(validated["selected_target_binding_sha256s"])
    targets = {
        str(item["target_binding_sha256"]): item
        for item in validated["targets"]
        if item["target_binding_sha256"] in selected_ids
    }
    identities = {
        _target_identity(item["row_key"], item["column"]): binding
        for binding, item in targets.items()
    }
    if any(
        _target_identity(item["row_key"], item["column"]) not in identities
        for item in active
    ):
        raise ValueError("V2.43.88 active observation target was not selected")
    proposal_sources = {
        str(vote["source_key"])
        for target in validated["targets"]
        for vote in target["proposal_votes"]
    }
    active_sources = {str(item["source_host"]) for item in active}
    if proposal_sources & active_sources:
        raise ValueError("V2.43.88 active source overlaps proposal source")
    resolutions: list[dict[str, Any]] = []
    for binding in validated["selected_target_binding_sha256s"]:
        target = targets[str(binding)]
        votes, ambiguous = _bound_votes(target, active)
        resolution = _resolution(target, votes, ambiguous)
        resolutions.append(resolution)
    columns, rows = table._table_matrix(str(validated["baseline_prediction"]))
    output_rows = [list(row) for row in rows]
    for resolution in resolutions:
        target = targets[str(resolution["target_binding_sha256"])]
        if resolution["final_value_changed"]:
            output_rows[int(target["row_index"])][int(target["column_index"])] = str(
                resolution["final_value"]
            )
    final_prediction = table._render_table(columns, output_rows)
    canonical, errors = table.extract_valid_markdown_table(final_prediction, columns)
    if canonical != final_prediction or errors:
        raise ValueError("V2.43.88 final table is not canonical")
    status_counts = Counter(str(item["status"]) for item in resolutions)
    credit_records = [
        record
        for resolution in resolutions
        for record in resolution["source_credit_records"]
    ]
    receipt = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "selected_target_count": len(resolutions),
        "active_observation_count": sum(
            int(item["active_observation_count"]) for item in resolutions
        ),
        "active_independent_source_count": len(active_sources),
        "active_ambiguous_source_count": sum(
            int(item["active_ambiguous_source_count"]) for item in resolutions
        ),
        "safe_change_count": status_counts["safe_change"],
        "baseline_confirmed_count": status_counts["baseline_confirmed"],
        "unresolved_count": status_counts["unresolved"],
        "positive_epistemic_target_count": sum(
            float(item["epistemic_credit_nats"]) > 0 for item in resolutions
        ),
        "source_credit_record_count": len(credit_records),
        "pre_active_entropy_total_nats": round(
            sum(float(item["pre_active_entropy_nats"]) for item in resolutions), 12
        ),
        "combined_entropy_total_nats": round(
            sum(float(item["combined_entropy_nats"]) for item in resolutions), 12
        ),
        "signed_entropy_reduction_total_nats": round(
            sum(
                float(item["signed_entropy_reduction_nats"])
                for item in resolutions
            ),
            12,
        ),
        "positive_information_gain_total_nats": round(
            sum(
                float(item["positive_information_gain_nats"])
                for item in resolutions
            ),
            12,
        ),
        "bayesian_surprise_total_nats": round(
            sum(float(item["bayesian_surprise_nats"]) for item in resolutions), 12
        ),
        "epistemic_credit_total_nats": round(
            sum(float(item["epistemic_credit_nats"]) for item in resolutions), 12
        ),
        "decision_credit_total_nats": round(
            sum(float(item["decision_credit_nats"]) for item in resolutions), 12
        ),
        "active_sources_disjoint_from_proposal_sources": True,
        "epistemic_credit_may_be_positive_without_output_change": True,
        "decision_credit_requires_safe_output_change": True,
        "source_credit_uses_normalized_leave_one_out_information_gain": True,
        "fixed_reliability_is_uncalibrated_shadow_only": True,
        "training_policy_or_runtime_routing_update_authorized": False,
        "question_query_url_page_prediction_candidate_value_or_source_emitted": False,
        "benchmark_label_mapping_gold_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
    }
    receipt["receipt_sha256"] = payload_sha256(receipt)
    value = {
        "artifact_version": 1,
        "role": RESULT_ROLE,
        "policy_id": POLICY_ID,
        "catalog": copy.deepcopy(validated),
        "active_observations": active,
        "resolutions": resolutions,
        "final_prediction": final_prediction,
        "receipt": receipt,
    }
    value["result_sha256"] = payload_sha256(value)
    return value


def apply_active_evidence(
    catalog: Mapping[str, Any],
    active_observations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    value = _compute_update(catalog, active_observations)
    validate_active_evidence_result(value)
    return value


def _finite(value: object, *, nonnegative: bool = True) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and (float(value) >= 0 if nonnegative else True)
    )


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    count_fields = (
        "selected_target_count",
        "active_observation_count",
        "active_independent_source_count",
        "active_ambiguous_source_count",
        "safe_change_count",
        "baseline_confirmed_count",
        "unresolved_count",
        "positive_epistemic_target_count",
        "source_credit_record_count",
    )
    nonnegative_fields = (
        "pre_active_entropy_total_nats",
        "combined_entropy_total_nats",
        "positive_information_gain_total_nats",
        "bayesian_surprise_total_nats",
        "epistemic_credit_total_nats",
        "decision_credit_total_nats",
    )
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != RECEIPT_ROLE
        or value.get("policy_id") != POLICY_ID
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in count_fields
        )
        or any(not _finite(value.get(name)) for name in nonnegative_fields)
        or not _finite(
            value.get("signed_entropy_reduction_total_nats"), nonnegative=False
        )
        or value["safe_change_count"]
        + value["baseline_confirmed_count"]
        + value["unresolved_count"]
        != value["selected_target_count"]
        or value["decision_credit_total_nats"]
        > value["epistemic_credit_total_nats"] + 1e-12
        or value.get("active_sources_disjoint_from_proposal_sources") is not True
        or value.get("epistemic_credit_may_be_positive_without_output_change")
        is not True
        or value.get("decision_credit_requires_safe_output_change") is not True
        or value.get(
            "source_credit_uses_normalized_leave_one_out_information_gain"
        )
        is not True
        or value.get("fixed_reliability_is_uncalibrated_shadow_only") is not True
        or value.get("training_policy_or_runtime_routing_update_authorized")
        is not False
        or value.get(
            "question_query_url_page_prediction_candidate_value_or_source_emitted"
        )
        is not False
        or value.get("benchmark_label_mapping_gold_evaluator_score_or_reward_read")
        is not False
        or value.get(
            "file_environment_network_model_search_fetch_process_or_evaluator_accessed"
        )
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.88 credit receipt drifted")
    return copy.deepcopy(dict(value))


def validate_active_evidence_result(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("result_sha256", None)
    catalog = value.get("catalog")
    observations = value.get("active_observations")
    resolutions = value.get("resolutions")
    receipt = value.get("receipt")
    if (
        set(value) != RESULT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != RESULT_ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(catalog, Mapping)
        or not isinstance(observations, list)
        or not isinstance(resolutions, list)
        or any(
            not isinstance(item, Mapping)
            or set(item) != RESOLUTION_KEYS
            or item.get("status") not in STATUSES
            or not isinstance(item.get("source_credit_records"), list)
            or any(
                not isinstance(record, Mapping)
                or set(record) != CREDIT_RECORD_KEYS
                for record in item["source_credit_records"]
            )
            for item in resolutions
        )
        or not isinstance(value.get("final_prediction"), str)
        or not isinstance(receipt, Mapping)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.88 active evidence result identity drifted")
    validate_uncertainty_catalog(catalog)
    validate_receipt(receipt)
    expected = _compute_update(catalog, observations)
    if dict(value) != expected:
        raise ValueError("V2.43.88 active evidence replay drifted")
    allocated_epistemic = round(
        sum(
            float(record["epistemic_credit_nats"])
            for resolution in resolutions
            for record in resolution["source_credit_records"]
        ),
        12,
    )
    allocated_decision = round(
        sum(
            float(record["decision_credit_nats"])
            for resolution in resolutions
            for record in resolution["source_credit_records"]
        ),
        12,
    )
    if (
        abs(allocated_epistemic - float(receipt["epistemic_credit_total_nats"]))
        > 2e-12
        or abs(allocated_decision - float(receipt["decision_credit_total_nats"]))
        > 2e-12
    ):
        raise ValueError("V2.43.88 source credit allocation drifted")
    return copy.deepcopy(dict(value))


__all__ = [
    "POLICY_ID",
    "apply_active_evidence",
    "build_uncertainty_catalog",
    "validate_active_evidence_result",
    "validate_receipt",
    "validate_uncertainty_catalog",
]
