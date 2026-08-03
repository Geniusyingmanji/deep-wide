"""Independent-host utility alignment for entropy-gated evidence credit.

Sources are partitioned before candidate discovery using only a frozen seed and
registrable host identity.  Baseline and candidate may see proposal sources;
verifier sources remain hidden from both.  A proposal receives utility-aligned
entropy credit only when a relation-bound projection on an independent hidden
source supports the new value, does not support the old value, and contains no
competing projected value for the same target.

This module is pure and benchmark-external.  It performs no file, environment,
network, model, search, fetch, process, evaluator, or scoring access.
"""

from __future__ import annotations

import copy
import hashlib
import json
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


POLICY_ID = "v24350_preproposal_source_split_independent_entropy_utility_v1"
ROLE = "v24350_independent_entropy_utility_catalog"
RECEIPT_ROLE = "v24350_independent_entropy_utility_resolution_receipt"
CATALOG_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "partition_seed_sha256",
        "targets",
        "original_pages",
        "proposal_pages",
        "verifier_pages",
        "proposal_source_key_sha256s",
        "verifier_source_key_sha256s",
        "proposal_semantic_catalog",
        "verifier_semantic_catalog",
        "utility_sets",
        "proposal_support_set_count",
        "utility_aligned_support_set_count",
        "quarantine_reasons",
        "source_partition_precedes_candidate_discovery",
        "proposal_and_verifier_sources_disjoint",
        "verifier_pages_hidden_from_baseline_and_candidate",
        "candidate_value_or_entropy_used_for_source_partition",
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
        "admit_independent_utility_support",
        "quarantine_unknown_utility_set",
        "quarantine_target_binding",
        "quarantine_value_binding",
        "quarantine_proposal_evidence_binding",
    }
)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _digest(value: object, *, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"V2.43.50 {label} is not a SHA-256 digest")
    return value


def _target(raw: CellTarget | Mapping[str, Any]) -> CellTarget:
    if isinstance(raw, CellTarget):
        value = raw
    elif isinstance(raw, Mapping) and set(raw) == {"row_key", "column", "old_value"}:
        value = CellTarget(
            str(raw["row_key"]),
            str(raw["column"]),
            None if raw["old_value"] is None else str(raw["old_value"]),
        )
    else:
        raise ValueError("V2.43.50 target schema drifted")
    value.validate()
    return value


def _page(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ValueError("V2.43.50 page is not a mapping")
    value = {
        "host": str(raw.get("host", "")),
        "content": str(raw.get("content", "")),
        "fetch_integrity": bool(raw.get("fetch_integrity", True)),
    }
    if not value["host"] or not value["content"].strip():
        raise ValueError("V2.43.50 page is incomplete")
    _source_key(value["host"])
    return value


def _source_digest(host: str) -> str:
    return _sha256_text(_source_key(host))


def _partition(
    pages: Sequence[Mapping[str, Any]],
    *,
    seed: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str], list[str]]:
    _digest(seed, label="partition seed")
    values = [_page(page) for page in pages]
    sources = sorted({_source_key(page["host"]) for page in values})
    if len(sources) < 3:
        return values, [], sorted(_sha256_text(source) for source in sources), []
    verifier_count = max(1, len(sources) // 4)
    ranked = sorted(
        sources,
        key=lambda source: (
            _sha256_text(seed + "|" + source),
            source,
        ),
    )
    verifier_sources = set(ranked[:verifier_count])
    proposal = [page for page in values if _source_key(page["host"]) not in verifier_sources]
    verifier = [page for page in values if _source_key(page["host"]) in verifier_sources]
    proposal_hashes = sorted({_source_digest(page["host"]) for page in proposal})
    verifier_hashes = sorted({_source_digest(page["host"]) for page in verifier})
    if set(proposal_hashes) & set(verifier_hashes):
        raise ValueError("V2.43.50 source partition overlaps")
    return proposal, verifier, proposal_hashes, verifier_hashes


def _target_values(targets: Sequence[CellTarget]) -> list[dict[str, Any]]:
    return [
        {
            "row_key": target.row_key,
            "column": target.column,
            "old_value": target.old_value,
        }
        for target in targets
    ]


def _projection_hash(value: object) -> str:
    return _sha256_text(projection_normalize(value))


def _source_by_projection_page(
    verifier_pages: Sequence[Mapping[str, Any]],
) -> dict[int, str]:
    return {
        ordinal: _source_digest(page["host"])
        for ordinal, page in enumerate(verifier_pages, start=1)
    }


def _compute(
    targets: Sequence[CellTarget | Mapping[str, Any]],
    pages: Sequence[Mapping[str, Any]],
    *,
    partition_seed_sha256: str,
) -> dict[str, Any]:
    cells = [_target(target) for target in targets]
    evidence = [_page(page) for page in pages]
    if len({target.binding_sha256 for target in cells}) != len(cells):
        raise ValueError("V2.43.50 duplicate target binding")
    proposal_pages, verifier_pages, proposal_sources, verifier_sources = _partition(
        evidence,
        seed=partition_seed_sha256,
    )
    proposal_catalog = build_semantic_active_catalog(cells, proposal_pages, [])
    verifier_catalog = build_semantic_active_catalog(cells, verifier_pages, [])
    validate_semantic_active_catalog(proposal_catalog)
    validate_semantic_active_catalog(verifier_catalog)

    target_by_binding = {target.binding_sha256: target for target in cells}
    verifier_page_sources = _source_by_projection_page(verifier_pages)
    projections_by_target: dict[str, list[dict[str, Any]]] = {}
    for projection in verifier_catalog["projections"]:
        projections_by_target.setdefault(
            str(projection["target_binding_sha256"]), []
        ).append(dict(projection))

    utility_sets: list[dict[str, Any]] = []
    quarantine: Counter[str] = Counter()
    support_sets = proposal_catalog["active_catalog"]["base_catalog"]["support_sets"]
    for support in support_sets:
        target = target_by_binding.get(str(support["target_binding_sha256"]))
        if target is None:
            raise ValueError("V2.43.50 proposal target binding drifted")
        candidate_hash = _projection_hash(support["candidate_value"])
        baseline_hash = (
            None if target.baseline_unknown else _projection_hash(target.old_value)
        )
        target_projections = projections_by_target.get(target.binding_sha256, [])
        candidate_projection_receipts = [
            projection
            for projection in target_projections
            if projection["normalized_value_sha256"] == candidate_hash
        ]
        baseline_projection_receipts = [
            projection
            for projection in target_projections
            if baseline_hash is not None
            and projection["normalized_value_sha256"] == baseline_hash
        ]
        conflicting_projection_receipts = [
            projection
            for projection in target_projections
            if projection["normalized_value_sha256"] != candidate_hash
        ]
        candidate_sources = {
            verifier_page_sources[int(projection["page_ordinal"])]
            for projection in candidate_projection_receipts
        }
        baseline_sources = {
            verifier_page_sources[int(projection["page_ordinal"])]
            for projection in baseline_projection_receipts
        }
        conflicting_sources = {
            verifier_page_sources[int(projection["page_ordinal"])]
            for projection in conflicting_projection_receipts
        }
        proposal_set_sources = sorted(
            str(binding["source_key_sha256"])
            for binding in support["evidence_source_bindings"]
        )
        sources_disjoint = not set(proposal_set_sources) & set(verifier_sources)
        baseline_outcome = bool(baseline_sources)
        candidate_outcome = bool(candidate_sources) and not conflicting_sources
        delta = int(candidate_outcome) - int(baseline_outcome)
        entropy = float(
            support["admission_receipt"]["conditional_entropy_reduction_nats"]
        )
        if not sources_disjoint:
            quarantine["quarantine_source_overlap"] += 1
            continue
        if not candidate_sources:
            quarantine["quarantine_no_independent_candidate_support"] += 1
            continue
        if baseline_sources:
            quarantine["quarantine_verifier_also_supports_baseline"] += 1
            continue
        if conflicting_sources:
            quarantine["quarantine_independent_conflict"] += 1
            continue
        if delta != 1 or entropy <= 0:
            quarantine["quarantine_nonpositive_verifier_sensitivity"] += 1
            continue
        verifier_receipt_hashes = sorted(
            payload_sha256(projection) for projection in candidate_projection_receipts
        )
        identity = {
            "partition_seed_sha256": partition_seed_sha256,
            "target_binding_sha256": target.binding_sha256,
            "candidate_value_sha256": _sha256_text(
                catalog_normalize(support["candidate_value"])
            ),
            "proposal_support_set_id": support["support_set_id"],
            "verifier_projection_receipt_sha256s": verifier_receipt_hashes,
        }
        utility_set_id = payload_sha256(identity)
        utility_sets.append(
            {
                "utility_set_id": utility_set_id,
                "target_binding_sha256": target.binding_sha256,
                "row_key": target.row_key,
                "column": target.column,
                "old_value": target.old_value,
                "candidate_value": support["candidate_value"],
                "candidate_value_sha256": identity["candidate_value_sha256"],
                "proposal_support_set_id": support["support_set_id"],
                "proposal_evidence_ids": list(support["evidence_ids"]),
                "proposal_source_key_sha256s": proposal_set_sources,
                "proposal_conditional_entropy_reduction_nats": round(entropy, 12),
                "verifier_projection_receipt_sha256s": verifier_receipt_hashes,
                "verifier_candidate_source_count": len(candidate_sources),
                "verifier_baseline_source_count": len(baseline_sources),
                "verifier_conflicting_source_count": len(conflicting_sources),
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
        "partition_seed_sha256": partition_seed_sha256,
        "targets": _target_values(cells),
        "original_pages": copy.deepcopy(evidence),
        "proposal_pages": copy.deepcopy(proposal_pages),
        "verifier_pages": copy.deepcopy(verifier_pages),
        "proposal_source_key_sha256s": proposal_sources,
        "verifier_source_key_sha256s": verifier_sources,
        "proposal_semantic_catalog": proposal_catalog,
        "verifier_semantic_catalog": verifier_catalog,
        "utility_sets": utility_sets,
        "proposal_support_set_count": len(support_sets),
        "utility_aligned_support_set_count": len(utility_sets),
        "quarantine_reasons": dict(sorted(quarantine.items())),
        "source_partition_precedes_candidate_discovery": True,
        "proposal_and_verifier_sources_disjoint": not set(proposal_sources)
        & set(verifier_sources),
        "verifier_pages_hidden_from_baseline_and_candidate": True,
        "candidate_value_or_entropy_used_for_source_partition": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["catalog_payload_sha256"] = payload_sha256(value)
    return value


def build_independent_utility_catalog(
    targets: Sequence[CellTarget | Mapping[str, Any]],
    pages: Sequence[Mapping[str, Any]],
    *,
    partition_seed_sha256: str,
) -> dict[str, Any]:
    value = _compute(
        targets,
        pages,
        partition_seed_sha256=partition_seed_sha256,
    )
    validate_independent_utility_catalog(value)
    return value


def validate_independent_utility_catalog(value: Mapping[str, Any]) -> dict[str, Any]:
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
        or value.get("source_partition_precedes_candidate_discovery") is not True
        or value.get("proposal_and_verifier_sources_disjoint") is not True
        or value.get("verifier_pages_hidden_from_baseline_and_candidate") is not True
        or value.get("candidate_value_or_entropy_used_for_source_partition") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("file_environment_network_model_search_fetch_process_or_evaluator_accessed") is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.50 utility catalog identity drifted")
    proposal_sources = value.get("proposal_source_key_sha256s")
    verifier_sources = value.get("verifier_source_key_sha256s")
    if (
        not isinstance(proposal_sources, list)
        or not isinstance(verifier_sources, list)
        or any(re.fullmatch(r"[0-9a-f]{64}", str(item)) is None for item in [*proposal_sources, *verifier_sources])
        or set(proposal_sources) & set(verifier_sources)
    ):
        raise ValueError("V2.43.50 utility source partition drifted")
    validate_semantic_active_catalog(value["proposal_semantic_catalog"])
    validate_semantic_active_catalog(value["verifier_semantic_catalog"])
    seen: set[str] = set()
    for item in utility_sets:
        if not isinstance(item, Mapping) or set(item) != UTILITY_SET_KEYS:
            raise ValueError("V2.43.50 utility set schema drifted")
        entropy = item.get("proposal_conditional_entropy_reduction_nats")
        credit = item.get("utility_aligned_entropy_credit_nats")
        if (
            re.fullmatch(r"[0-9a-f]{64}", str(item.get("utility_set_id"))) is None
            or item["utility_set_id"] in seen
            or re.fullmatch(r"[0-9a-f]{64}", str(item.get("target_binding_sha256"))) is None
            or re.fullmatch(r"[0-9a-f]{64}", str(item.get("candidate_value_sha256"))) is None
            or re.fullmatch(r"[0-9a-f]{64}", str(item.get("proposal_support_set_id"))) is None
            or not isinstance(item.get("proposal_evidence_ids"), list)
            or not isinstance(item.get("proposal_source_key_sha256s"), list)
            or set(item["proposal_source_key_sha256s"]) & set(verifier_sources)
            or not isinstance(item.get("verifier_projection_receipt_sha256s"), list)
            or any(re.fullmatch(r"[0-9a-f]{64}", str(entry)) is None for entry in item["verifier_projection_receipt_sha256s"])
            or any(
                isinstance(item.get(name), bool)
                or not isinstance(item.get(name), int)
                or item[name] < 0
                for name in (
                    "verifier_candidate_source_count",
                    "verifier_baseline_source_count",
                    "verifier_conflicting_source_count",
                )
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
            raise ValueError("V2.43.50 utility set identity drifted")
        expected_id = payload_sha256(
            {
                "partition_seed_sha256": value["partition_seed_sha256"],
                "target_binding_sha256": item["target_binding_sha256"],
                "candidate_value_sha256": item["candidate_value_sha256"],
                "proposal_support_set_id": item["proposal_support_set_id"],
                "verifier_projection_receipt_sha256s": item[
                    "verifier_projection_receipt_sha256s"
                ],
            }
        )
        if item["utility_set_id"] != expected_id:
            raise ValueError("V2.43.50 utility set seal drifted")
        seen.add(item["utility_set_id"])
    expected = _compute(
        value["targets"],
        value["original_pages"],
        partition_seed_sha256=value["partition_seed_sha256"],
    )
    if dict(value) != expected:
        raise ValueError("V2.43.50 utility catalog replay drifted")
    return dict(value)


def render_proposal_catalog(value: Mapping[str, Any]) -> str:
    catalog = validate_independent_utility_catalog(value)
    lines = [
        json.dumps(
            {
                "utility_set_id": item["utility_set_id"],
                "row_key": item["row_key"],
                "column": item["column"],
                "candidate_value": item["candidate_value"],
                "proposal_evidence_ids": item["proposal_evidence_ids"],
                "proposal_conditional_entropy_reduction_nats": item[
                    "proposal_conditional_entropy_reduction_nats"
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        for item in catalog["utility_sets"]
    ]
    return "\n".join(lines) or "No independently verifiable proposal set."


def resolve_independent_utility_selection(
    catalog: Mapping[str, Any],
    *,
    row_key: str,
    column: str,
    new_value: str,
    utility_set_id: str,
    declared_proposal_evidence_ids: Sequence[str],
) -> dict[str, Any]:
    value = validate_independent_utility_catalog(catalog)
    by_id = {item["utility_set_id"]: item for item in value["utility_sets"]}
    item = by_id.get(utility_set_id)
    target_match = value_match = evidence_match = False
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
        evidence_match = (
            not isinstance(declared_proposal_evidence_ids, (str, bytes))
            and list(declared_proposal_evidence_ids) == item["proposal_evidence_ids"]
        )
        disjoint = not set(item["proposal_source_key_sha256s"]) & set(
            value["verifier_source_key_sha256s"]
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
        elif not evidence_match:
            disposition = "quarantine_proposal_evidence_binding"
        else:
            disposition = "admit_independent_utility_support"
            credit = float(item["utility_aligned_entropy_credit_nats"])
    admitted = disposition == "admit_independent_utility_support"
    receipt = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "catalog_payload_sha256": value["catalog_payload_sha256"],
        "utility_set_id_sha256": _sha256_text(str(utility_set_id)),
        "selection_binding_sha256": payload_sha256(
            {
                "row_key": catalog_normalize(row_key),
                "column": catalog_normalize(column),
                "new_value": catalog_normalize(new_value),
                "utility_set_id": str(utility_set_id),
                "declared_proposal_evidence_ids": (
                    list(declared_proposal_evidence_ids)
                    if not isinstance(declared_proposal_evidence_ids, (str, bytes))
                    else None
                ),
            }
        ),
        "target_binding_matches": target_match,
        "value_binding_matches": value_match,
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
    validate_independent_utility_receipt(receipt)
    return receipt


def validate_independent_utility_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
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
        or re.fullmatch(r"[0-9a-f]{64}", str(value.get("catalog_payload_sha256")))
        is None
        or re.fullmatch(r"[0-9a-f]{64}", str(value.get("utility_set_id_sha256")))
        is None
        or re.fullmatch(r"[0-9a-f]{64}", str(value.get("selection_binding_sha256")))
        is None
        or disposition not in DISPOSITIONS
        or admitted is not (disposition == "admit_independent_utility_support")
        or any(
            not isinstance(value.get(name), bool)
            for name in (
                "target_binding_matches",
                "value_binding_matches",
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
        or isinstance(entropy, bool)
        or not isinstance(entropy, (int, float))
        or not math.isfinite(float(entropy))
        or float(entropy) < 0
        or isinstance(credit, bool)
        or not isinstance(credit, (int, float))
        or not math.isfinite(float(credit))
        or float(credit) < 0
        or isinstance(value.get("verifier_outcome_delta"), bool)
        or not isinstance(value.get("verifier_outcome_delta"), int)
        or value["verifier_outcome_delta"] not in {-1, 0, 1}
        or (admitted and float(credit) <= 0)
        or (not admitted and float(credit) != 0)
        or value.get("raw_page_novelty_or_character_count_used_as_task_value") is not False
        or value.get("question_query_url_host_page_candidate_value_evidence_id_or_credential_emitted") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("file_environment_network_model_search_fetch_process_or_evaluator_accessed") is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.50 utility receipt drifted")
    if admitted and (
        value.get("target_binding_matches") is not True
        or value.get("value_binding_matches") is not True
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
        raise ValueError("V2.43.50 admitted utility invariants drifted")
    return dict(value)


__all__ = [
    "POLICY_ID",
    "ROLE",
    "build_independent_utility_catalog",
    "render_proposal_catalog",
    "resolve_independent_utility_selection",
    "validate_independent_utility_catalog",
    "validate_independent_utility_receipt",
]
