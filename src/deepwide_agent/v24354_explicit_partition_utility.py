"""Explicit prepartition utility alignment for entropy credit assignment.

V2.43.53 showed that repartitioning only the successfully fetched pages can
invalidate an otherwise correct preproposal host split.  This successor never
repartitions.  It reuses the exact parent proposal semantic catalog (including
its support-set IDs and evidence IDs), accepts successful proposal/verifier
pages as subsets of the already frozen host partitions, and derives credit only
from relation-bound projections on hidden verifier pages.

The component is pure and benchmark-external.  It performs no file,
environment, network, model, search, fetch, process, evaluator, or score access.
"""

from __future__ import annotations

import copy
import hashlib
import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24333_programmatic_support_catalog import (
    CellTarget,
    _normalize as catalog_normalize,
    _source_key,
)
from .v24341_semantic_evidence_projection import (
    _normalize as projection_normalize,
    build_semantic_active_catalog,
    validate_semantic_active_catalog,
)


POLICY_ID = "v24354_explicit_prepartition_entropy_utility_v1"
ROLE = "v24354_explicit_partition_utility_catalog"
RECEIPT_ROLE = "v24354_explicit_partition_utility_resolution_receipt"
CATALOG_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "partition_seed_sha256",
        "targets",
        "proposal_semantic_catalog",
        "verifier_pages",
        "verifier_semantic_catalog",
        "expected_proposal_source_key_sha256s",
        "expected_verifier_source_key_sha256s",
        "observed_proposal_source_key_sha256s",
        "observed_verifier_source_key_sha256s",
        "utility_sets",
        "proposal_support_set_count",
        "utility_aligned_support_set_count",
        "quarantine_reasons",
        "explicit_preproposal_partition_reused",
        "successful_pages_may_be_strict_subset_of_partition",
        "observed_pages_respect_frozen_partition",
        "proposal_and_verifier_sources_disjoint",
        "parent_proposal_support_ids_reused_without_rebuild",
        "verifier_pages_hidden_from_parent_model",
        "candidate_value_entropy_or_page_content_used_for_partition",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "catalog_payload_sha256",
    }
)
UTILITY_SET_KEYS = frozenset(
    {
        "utility_set_id",
        "target_binding_sha256",
        "row_key",
        "column",
        "old_value",
        "candidate_value",
        "candidate_value_sha256",
        "proposal_semantic_catalog_payload_sha256",
        "proposal_support_set_id",
        "proposal_evidence_ids",
        "proposal_source_key_sha256s",
        "proposal_conditional_entropy_reduction_nats",
        "verifier_projection_receipt_sha256s",
        "verifier_candidate_source_count",
        "verifier_baseline_source_count",
        "verifier_conflicting_source_count",
        "verifier_outcome_baseline",
        "verifier_outcome_candidate",
        "verifier_outcome_delta",
        "utility_aligned_entropy_credit_nats",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "catalog_payload_sha256",
        "utility_set_id_sha256",
        "selection_binding_sha256",
        "target_binding_matches",
        "value_binding_matches",
        "proposal_support_set_binding_matches",
        "proposal_evidence_binding_matches",
        "proposal_and_verifier_sources_disjoint",
        "verifier_candidate_source_count",
        "verifier_baseline_source_count",
        "verifier_conflicting_source_count",
        "verifier_outcome_baseline",
        "verifier_outcome_candidate",
        "verifier_outcome_delta",
        "proposal_conditional_entropy_reduction_nats",
        "utility_aligned_entropy_credit_nats",
        "admitted",
        "disposition",
        "raw_page_novelty_or_character_count_used_as_task_value",
        "question_query_url_host_page_candidate_value_evidence_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)
DISPOSITIONS = frozenset(
    {
        "admit_explicit_partition_utility_support",
        "quarantine_unknown_utility_set",
        "quarantine_target_binding",
        "quarantine_value_binding",
        "quarantine_proposal_support_binding",
        "quarantine_proposal_evidence_binding",
    }
)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _digest(value: object, *, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"V2.43.54 {label} is not a SHA-256 digest")
    return value


def _digest_vector(value: object, *, label: str) -> list[str]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes))
        or any(
            not isinstance(item, str)
            or re.fullmatch(r"[0-9a-f]{64}", item) is None
            for item in value
        )
    ):
        raise ValueError(f"V2.43.54 {label} digest vector drifted")
    output = list(value)
    if output != sorted(set(output)):
        raise ValueError(f"V2.43.54 {label} digest vector is not canonical")
    return output


def _page(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ValueError("V2.43.54 page is not a mapping")
    value = {
        "host": str(raw.get("host", "")),
        "content": str(raw.get("content", "")),
        "fetch_integrity": bool(raw.get("fetch_integrity", True)),
    }
    if not value["host"] or not value["content"].strip():
        raise ValueError("V2.43.54 page is incomplete")
    _source_key(value["host"])
    return value


def _source_digest(host: str) -> str:
    return _sha256_text(_source_key(host))


def _target(raw: Mapping[str, Any]) -> CellTarget:
    if not isinstance(raw, Mapping) or set(raw) != {"row_key", "column", "old_value"}:
        raise ValueError("V2.43.54 target schema drifted")
    value = CellTarget(
        str(raw["row_key"]),
        str(raw["column"]),
        None if raw["old_value"] is None else str(raw["old_value"]),
    )
    value.validate()
    return value


def _projection_hash(value: object) -> str:
    return _sha256_text(projection_normalize(value))


def _compute(
    proposal_semantic_catalog: Mapping[str, Any],
    verifier_pages: Sequence[Mapping[str, Any]],
    *,
    partition_seed_sha256: str,
    expected_proposal_source_key_sha256s: Sequence[str],
    expected_verifier_source_key_sha256s: Sequence[str],
) -> dict[str, Any]:
    seed = _digest(partition_seed_sha256, label="partition seed")
    proposal = validate_semantic_active_catalog(proposal_semantic_catalog)
    expected_proposal = _digest_vector(
        expected_proposal_source_key_sha256s,
        label="expected proposal source",
    )
    expected_verifier = _digest_vector(
        expected_verifier_source_key_sha256s,
        label="expected verifier source",
    )
    if set(expected_proposal) & set(expected_verifier):
        raise ValueError("V2.43.54 frozen source partitions overlap")

    targets = [_target(value) for value in proposal["targets"]]
    if len({target.binding_sha256 for target in targets}) != len(targets):
        raise ValueError("V2.43.54 duplicate target binding")
    proposal_pages = [
        _page(page)
        for page in [
            *proposal["original_core_pages"],
            *proposal["original_reserve_pages"],
        ]
    ]
    hidden_pages = [_page(page) for page in verifier_pages]
    observed_proposal = sorted({_source_digest(page["host"]) for page in proposal_pages})
    observed_verifier = sorted({_source_digest(page["host"]) for page in hidden_pages})
    partition_respected = (
        set(observed_proposal).issubset(expected_proposal)
        and set(observed_verifier).issubset(expected_verifier)
        and not set(observed_proposal) & set(observed_verifier)
    )
    if not partition_respected:
        raise ValueError("V2.43.54 successful page escaped its frozen partition")

    verifier_catalog = build_semantic_active_catalog(targets, hidden_pages, [])
    validate_semantic_active_catalog(verifier_catalog)
    target_by_binding = {target.binding_sha256: target for target in targets}
    verifier_source_by_ordinal = {
        ordinal: _source_digest(page["host"])
        for ordinal, page in enumerate(hidden_pages, start=1)
    }
    projections_by_target: dict[str, list[dict[str, Any]]] = {}
    for projection in verifier_catalog["projections"]:
        projections_by_target.setdefault(
            str(projection["target_binding_sha256"]), []
        ).append(dict(projection))

    base_catalog = proposal["active_catalog"]["base_catalog"]
    support_sets = list(base_catalog["support_sets"])
    utility_sets: list[dict[str, Any]] = []
    quarantine: Counter[str] = Counter()
    for support in support_sets:
        target = target_by_binding.get(str(support["target_binding_sha256"]))
        if target is None:
            raise ValueError("V2.43.54 proposal target binding drifted")
        proposal_sources = sorted(
            str(binding["source_key_sha256"])
            for binding in support["evidence_source_bindings"]
        )
        if not set(proposal_sources).issubset(observed_proposal):
            raise ValueError("V2.43.54 parent support source escaped proposal pages")
        candidate_hash = _projection_hash(support["candidate_value"])
        baseline_hash = (
            None if target.baseline_unknown else _projection_hash(target.old_value)
        )
        target_projections = projections_by_target.get(target.binding_sha256, [])
        candidate_receipts = [
            item
            for item in target_projections
            if item["normalized_value_sha256"] == candidate_hash
        ]
        baseline_receipts = [
            item
            for item in target_projections
            if baseline_hash is not None
            and item["normalized_value_sha256"] == baseline_hash
        ]
        conflict_receipts = [
            item
            for item in target_projections
            if item["normalized_value_sha256"] != candidate_hash
        ]
        candidate_sources = {
            verifier_source_by_ordinal[int(item["page_ordinal"])]
            for item in candidate_receipts
        }
        baseline_sources = {
            verifier_source_by_ordinal[int(item["page_ordinal"])]
            for item in baseline_receipts
        }
        conflict_sources = {
            verifier_source_by_ordinal[int(item["page_ordinal"])]
            for item in conflict_receipts
        }
        disjoint = not set(proposal_sources) & set(observed_verifier)
        baseline_outcome = bool(baseline_sources)
        candidate_outcome = bool(candidate_sources) and not conflict_sources
        delta = int(candidate_outcome) - int(baseline_outcome)
        entropy = float(
            support["admission_receipt"]["conditional_entropy_reduction_nats"]
        )
        if not disjoint:
            quarantine["quarantine_source_overlap"] += 1
            continue
        if not candidate_sources:
            quarantine["quarantine_no_independent_candidate_support"] += 1
            continue
        if baseline_sources:
            quarantine["quarantine_verifier_also_supports_baseline"] += 1
            continue
        if conflict_sources:
            quarantine["quarantine_independent_conflict"] += 1
            continue
        if delta != 1 or entropy <= 0:
            quarantine["quarantine_nonpositive_verifier_sensitivity"] += 1
            continue
        verifier_hashes = sorted(payload_sha256(item) for item in candidate_receipts)
        identity = {
            "partition_seed_sha256": seed,
            "proposal_semantic_catalog_payload_sha256": proposal[
                "catalog_payload_sha256"
            ],
            "target_binding_sha256": target.binding_sha256,
            "candidate_value_sha256": _sha256_text(
                catalog_normalize(support["candidate_value"])
            ),
            "proposal_support_set_id": support["support_set_id"],
            "verifier_projection_receipt_sha256s": verifier_hashes,
        }
        utility_sets.append(
            {
                "utility_set_id": payload_sha256(identity),
                "target_binding_sha256": target.binding_sha256,
                "row_key": target.row_key,
                "column": target.column,
                "old_value": target.old_value,
                "candidate_value": support["candidate_value"],
                "candidate_value_sha256": identity["candidate_value_sha256"],
                "proposal_semantic_catalog_payload_sha256": proposal[
                    "catalog_payload_sha256"
                ],
                "proposal_support_set_id": support["support_set_id"],
                "proposal_evidence_ids": list(support["evidence_ids"]),
                "proposal_source_key_sha256s": proposal_sources,
                "proposal_conditional_entropy_reduction_nats": round(entropy, 12),
                "verifier_projection_receipt_sha256s": verifier_hashes,
                "verifier_candidate_source_count": len(candidate_sources),
                "verifier_baseline_source_count": len(baseline_sources),
                "verifier_conflicting_source_count": len(conflict_sources),
                "verifier_outcome_baseline": baseline_outcome,
                "verifier_outcome_candidate": candidate_outcome,
                "verifier_outcome_delta": delta,
                "utility_aligned_entropy_credit_nats": round(entropy * delta, 12),
            }
        )
    utility_sets.sort(key=lambda item: item["utility_set_id"])
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "partition_seed_sha256": seed,
        "targets": copy.deepcopy(proposal["targets"]),
        "proposal_semantic_catalog": copy.deepcopy(dict(proposal)),
        "verifier_pages": copy.deepcopy(hidden_pages),
        "verifier_semantic_catalog": verifier_catalog,
        "expected_proposal_source_key_sha256s": expected_proposal,
        "expected_verifier_source_key_sha256s": expected_verifier,
        "observed_proposal_source_key_sha256s": observed_proposal,
        "observed_verifier_source_key_sha256s": observed_verifier,
        "utility_sets": utility_sets,
        "proposal_support_set_count": len(support_sets),
        "utility_aligned_support_set_count": len(utility_sets),
        "quarantine_reasons": dict(sorted(quarantine.items())),
        "explicit_preproposal_partition_reused": True,
        "successful_pages_may_be_strict_subset_of_partition": True,
        "observed_pages_respect_frozen_partition": partition_respected,
        "proposal_and_verifier_sources_disjoint": not set(observed_proposal)
        & set(observed_verifier),
        "parent_proposal_support_ids_reused_without_rebuild": True,
        "verifier_pages_hidden_from_parent_model": True,
        "candidate_value_entropy_or_page_content_used_for_partition": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["catalog_payload_sha256"] = payload_sha256(value)
    return value


def build_explicit_partition_utility_catalog(
    proposal_semantic_catalog: Mapping[str, Any],
    verifier_pages: Sequence[Mapping[str, Any]],
    *,
    partition_seed_sha256: str,
    expected_proposal_source_key_sha256s: Sequence[str],
    expected_verifier_source_key_sha256s: Sequence[str],
) -> dict[str, Any]:
    value = _compute(
        proposal_semantic_catalog,
        verifier_pages,
        partition_seed_sha256=partition_seed_sha256,
        expected_proposal_source_key_sha256s=expected_proposal_source_key_sha256s,
        expected_verifier_source_key_sha256s=expected_verifier_source_key_sha256s,
    )
    validate_explicit_partition_utility_catalog(value)
    return value


def validate_explicit_partition_utility_catalog(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("catalog_payload_sha256", None)
    utility_sets = value.get("utility_sets")
    quarantine = value.get("quarantine_reasons")
    if (
        set(value) != CATALOG_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("policy_id") != POLICY_ID
        or re.fullmatch(r"[0-9a-f]{64}", str(value.get("partition_seed_sha256")))
        is None
        or not isinstance(utility_sets, list)
        or value.get("utility_aligned_support_set_count") != len(utility_sets)
        or not isinstance(quarantine, Mapping)
        or any(
            isinstance(number, bool) or not isinstance(number, int) or number < 0
            for number in quarantine.values()
        )
        or value.get("explicit_preproposal_partition_reused") is not True
        or value.get("successful_pages_may_be_strict_subset_of_partition") is not True
        or value.get("observed_pages_respect_frozen_partition") is not True
        or value.get("proposal_and_verifier_sources_disjoint") is not True
        or value.get("parent_proposal_support_ids_reused_without_rebuild") is not True
        or value.get("verifier_pages_hidden_from_parent_model") is not True
        or value.get("candidate_value_entropy_or_page_content_used_for_partition") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("file_environment_network_model_search_fetch_process_or_evaluator_accessed") is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.54 utility catalog identity drifted")
    validate_semantic_active_catalog(value["proposal_semantic_catalog"])
    validate_semantic_active_catalog(value["verifier_semantic_catalog"])
    for name in (
        "expected_proposal_source_key_sha256s",
        "expected_verifier_source_key_sha256s",
        "observed_proposal_source_key_sha256s",
        "observed_verifier_source_key_sha256s",
    ):
        _digest_vector(value[name], label=name)
    seen: set[str] = set()
    for item in utility_sets:
        if not isinstance(item, Mapping) or set(item) != UTILITY_SET_KEYS:
            raise ValueError("V2.43.54 utility set schema drifted")
        entropy = item.get("proposal_conditional_entropy_reduction_nats")
        credit = item.get("utility_aligned_entropy_credit_nats")
        expected_id = payload_sha256(
            {
                "partition_seed_sha256": value["partition_seed_sha256"],
                "proposal_semantic_catalog_payload_sha256": item[
                    "proposal_semantic_catalog_payload_sha256"
                ],
                "target_binding_sha256": item["target_binding_sha256"],
                "candidate_value_sha256": item["candidate_value_sha256"],
                "proposal_support_set_id": item["proposal_support_set_id"],
                "verifier_projection_receipt_sha256s": item[
                    "verifier_projection_receipt_sha256s"
                ],
            }
        )
        if (
            re.fullmatch(r"[0-9a-f]{64}", str(item.get("utility_set_id"))) is None
            or item["utility_set_id"] in seen
            or item["utility_set_id"] != expected_id
            or item.get("proposal_semantic_catalog_payload_sha256")
            != value["proposal_semantic_catalog"]["catalog_payload_sha256"]
            or any(
                re.fullmatch(r"[0-9a-f]{64}", str(item.get(name))) is None
                for name in (
                    "target_binding_sha256",
                    "candidate_value_sha256",
                    "proposal_support_set_id",
                )
            )
            or not isinstance(item.get("proposal_evidence_ids"), list)
            or not isinstance(item.get("proposal_source_key_sha256s"), list)
            or set(item["proposal_source_key_sha256s"])
            & set(value["observed_verifier_source_key_sha256s"])
            or not isinstance(item.get("verifier_projection_receipt_sha256s"), list)
            or any(
                re.fullmatch(r"[0-9a-f]{64}", str(entry)) is None
                for entry in item["verifier_projection_receipt_sha256s"]
            )
            or item.get("verifier_candidate_source_count", 0) < 1
            or item.get("verifier_baseline_source_count") != 0
            or item.get("verifier_conflicting_source_count") != 0
            or item.get("verifier_outcome_baseline") is not False
            or item.get("verifier_outcome_candidate") is not True
            or item.get("verifier_outcome_delta") != 1
            or isinstance(entropy, bool)
            or not isinstance(entropy, (int, float))
            or not math.isfinite(float(entropy))
            or float(entropy) <= 0
            or not math.isclose(float(credit), float(entropy), abs_tol=1e-12)
        ):
            raise ValueError("V2.43.54 utility set identity drifted")
        seen.add(item["utility_set_id"])
    expected = _compute(
        value["proposal_semantic_catalog"],
        value["verifier_pages"],
        partition_seed_sha256=value["partition_seed_sha256"],
        expected_proposal_source_key_sha256s=value[
            "expected_proposal_source_key_sha256s"
        ],
        expected_verifier_source_key_sha256s=value[
            "expected_verifier_source_key_sha256s"
        ],
    )
    if dict(value) != expected:
        raise ValueError("V2.43.54 utility catalog replay drifted")
    return dict(value)


def resolve_explicit_partition_utility_selection(
    catalog: Mapping[str, Any],
    *,
    row_key: str,
    column: str,
    new_value: str,
    proposal_support_set_id: str,
    declared_proposal_evidence_ids: Sequence[str],
) -> dict[str, Any]:
    value = validate_explicit_partition_utility_catalog(catalog)
    matching = [
        item
        for item in value["utility_sets"]
        if item["proposal_support_set_id"] == proposal_support_set_id
    ]
    item = matching[0] if len(matching) == 1 else None
    target_match = value_match = support_match = evidence_match = False
    verifier_candidate = verifier_baseline = verifier_conflict = 0
    outcome_before = outcome_after = False
    delta = 0
    entropy = credit = 0.0
    disjoint = True
    if item is None:
        disposition = "quarantine_unknown_utility_set"
    else:
        target_match = (
            catalog_normalize(row_key) == catalog_normalize(item["row_key"])
            and catalog_normalize(column) == catalog_normalize(item["column"])
        )
        value_match = catalog_normalize(new_value) == catalog_normalize(
            item["candidate_value"]
        )
        support_match = proposal_support_set_id == item["proposal_support_set_id"]
        evidence_match = (
            not isinstance(declared_proposal_evidence_ids, (str, bytes))
            and list(declared_proposal_evidence_ids) == item["proposal_evidence_ids"]
        )
        disjoint = not set(item["proposal_source_key_sha256s"]) & set(
            value["observed_verifier_source_key_sha256s"]
        )
        verifier_candidate = int(item["verifier_candidate_source_count"])
        verifier_baseline = int(item["verifier_baseline_source_count"])
        verifier_conflict = int(item["verifier_conflicting_source_count"])
        outcome_before = bool(item["verifier_outcome_baseline"])
        outcome_after = bool(item["verifier_outcome_candidate"])
        delta = int(item["verifier_outcome_delta"])
        entropy = float(item["proposal_conditional_entropy_reduction_nats"])
        if not target_match:
            disposition = "quarantine_target_binding"
        elif not value_match:
            disposition = "quarantine_value_binding"
        elif not support_match:
            disposition = "quarantine_proposal_support_binding"
        elif not evidence_match:
            disposition = "quarantine_proposal_evidence_binding"
        else:
            disposition = "admit_explicit_partition_utility_support"
            credit = float(item["utility_aligned_entropy_credit_nats"])
    admitted = disposition == "admit_explicit_partition_utility_support"
    receipt = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "catalog_payload_sha256": value["catalog_payload_sha256"],
        "utility_set_id_sha256": _sha256_text(
            str(item["utility_set_id"] if item is not None else "")
        ),
        "selection_binding_sha256": payload_sha256(
            {
                "row_key": catalog_normalize(row_key),
                "column": catalog_normalize(column),
                "new_value": catalog_normalize(new_value),
                "proposal_support_set_id": str(proposal_support_set_id),
                "declared_proposal_evidence_ids": (
                    list(declared_proposal_evidence_ids)
                    if not isinstance(declared_proposal_evidence_ids, (str, bytes))
                    else None
                ),
            }
        ),
        "target_binding_matches": target_match,
        "value_binding_matches": value_match,
        "proposal_support_set_binding_matches": support_match,
        "proposal_evidence_binding_matches": evidence_match,
        "proposal_and_verifier_sources_disjoint": disjoint,
        "verifier_candidate_source_count": verifier_candidate,
        "verifier_baseline_source_count": verifier_baseline,
        "verifier_conflicting_source_count": verifier_conflict,
        "verifier_outcome_baseline": outcome_before,
        "verifier_outcome_candidate": outcome_after,
        "verifier_outcome_delta": delta,
        "proposal_conditional_entropy_reduction_nats": round(entropy, 12),
        "utility_aligned_entropy_credit_nats": round(credit, 12),
        "admitted": admitted,
        "disposition": disposition,
        "raw_page_novelty_or_character_count_used_as_task_value": False,
        "question_query_url_host_page_candidate_value_evidence_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_sha256"] = payload_sha256(receipt)
    validate_explicit_partition_utility_receipt(receipt)
    return receipt


def validate_explicit_partition_utility_receipt(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    admitted = value.get("admitted")
    disposition = value.get("disposition")
    entropy = value.get("proposal_conditional_entropy_reduction_nats")
    credit = value.get("utility_aligned_entropy_credit_nats")
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != RECEIPT_ROLE
        or value.get("policy_id") != POLICY_ID
        or any(
            re.fullmatch(r"[0-9a-f]{64}", str(value.get(name))) is None
            for name in (
                "catalog_payload_sha256",
                "utility_set_id_sha256",
                "selection_binding_sha256",
            )
        )
        or disposition not in DISPOSITIONS
        or admitted
        is not (disposition == "admit_explicit_partition_utility_support")
        or any(
            not isinstance(value.get(name), bool)
            for name in (
                "target_binding_matches",
                "value_binding_matches",
                "proposal_support_set_binding_matches",
                "proposal_evidence_binding_matches",
                "proposal_and_verifier_sources_disjoint",
                "verifier_outcome_baseline",
                "verifier_outcome_candidate",
                "admitted",
            )
        )
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in (
                "verifier_candidate_source_count",
                "verifier_baseline_source_count",
                "verifier_conflicting_source_count",
            )
        )
        or value.get("verifier_outcome_delta") not in {-1, 0, 1}
        or isinstance(entropy, bool)
        or not isinstance(entropy, (int, float))
        or not math.isfinite(float(entropy))
        or float(entropy) < 0
        or isinstance(credit, bool)
        or not isinstance(credit, (int, float))
        or not math.isfinite(float(credit))
        or float(credit) < 0
        or (admitted and float(credit) <= 0)
        or (not admitted and float(credit) != 0)
        or value.get("raw_page_novelty_or_character_count_used_as_task_value") is not False
        or value.get("question_query_url_host_page_candidate_value_evidence_id_or_credential_emitted") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("file_environment_network_model_search_fetch_process_or_evaluator_accessed") is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.54 utility receipt drifted")
    if admitted and (
        value.get("target_binding_matches") is not True
        or value.get("value_binding_matches") is not True
        or value.get("proposal_support_set_binding_matches") is not True
        or value.get("proposal_evidence_binding_matches") is not True
        or value.get("proposal_and_verifier_sources_disjoint") is not True
        or value.get("verifier_candidate_source_count", 0) < 1
        or value.get("verifier_baseline_source_count") != 0
        or value.get("verifier_conflicting_source_count") != 0
        or value.get("verifier_outcome_baseline") is not False
        or value.get("verifier_outcome_candidate") is not True
        or value.get("verifier_outcome_delta") != 1
        or not math.isclose(float(credit), float(entropy), abs_tol=1e-12)
    ):
        raise ValueError("V2.43.54 admitted utility invariants drifted")
    return dict(value)


__all__ = [
    "POLICY_ID",
    "ROLE",
    "build_explicit_partition_utility_catalog",
    "resolve_explicit_partition_utility_selection",
    "validate_explicit_partition_utility_catalog",
    "validate_explicit_partition_utility_receipt",
]
