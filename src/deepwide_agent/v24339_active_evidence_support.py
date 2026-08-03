"""Active-evidence support catalogs for entropy credit assignment.

V2.43.38 showed that three reserve pages usually cover different target rows,
so a strict two-host cell gate cannot activate even when the already-fetched
seven core pages contain corroboration.  This pure successor remaps the exact
shared 7+3 evidence vector into one active catalog.  Baseline and candidate
therefore use identical fetched pages; the candidate differs only by the
programmatic support structure and deterministic entropy gate.  This is an
algorithmic credit-assignment ablation, not a pure reserve-effect ablation.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24333_programmatic_support_catalog import (
    CellTarget,
    SupportPage,
    build_support_catalog,
    resolve_support_selection,
    validate_catalog_identity,
    validate_resolution_receipt,
    validate_support_catalog,
)


POLICY_ID = "v24339_shared_active_evidence_entropy_credit_v1"
ROLE = "v24339_active_evidence_support_catalog"
RECEIPT_ROLE = "v24339_active_evidence_resolution_receipt"
CATALOG_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "base_catalog",
        "active_pages",
        "active_scope_by_evidence_id",
        "core_page_count",
        "reserve_page_count",
        "active_page_count",
        "eligible_support_scope_counts",
        "baseline_and_candidate_share_exact_active_pages",
        "candidate_only_adds_programmatic_support_structure",
        "pure_reserve_effect_ablation",
        "catalog_payload_sha256",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "active_catalog_payload_sha256",
        "base_resolution_receipt",
        "support_scope",
        "core_evidence_count",
        "reserve_evidence_count",
        "admitted",
        "conditional_entropy_reduction_nats",
        "question_query_url_host_page_candidate_value_evidence_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)


def _page(raw: Mapping[str, Any], evidence_id: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ValueError("V2.43.39 active page is not a mapping")
    return {
        "evidence_id": evidence_id,
        "host": str(raw.get("host", "")),
        "content": str(raw.get("content", "")),
        "fetch_integrity": bool(raw.get("fetch_integrity", True)),
    }


def build_active_catalog(
    targets: Sequence[CellTarget | Mapping[str, Any]],
    core_pages: Sequence[Mapping[str, Any]],
    reserve_pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if isinstance(core_pages, (str, bytes)) or isinstance(reserve_pages, (str, bytes)):
        raise ValueError("V2.43.39 active page vector drifted")
    active_pages: list[dict[str, Any]] = []
    scopes: dict[str, str] = {}
    for scope, pages in (("core", core_pages), ("reserve", reserve_pages)):
        for raw in pages:
            evidence_id = f"R{len(active_pages) + 1:04d}"
            active_pages.append(_page(raw, evidence_id))
            scopes[evidence_id] = scope
    base_catalog = build_support_catalog(targets, active_pages)
    scope_counts: Counter[str] = Counter()
    for item in base_catalog["support_sets"]:
        present = {scopes[evidence_id] for evidence_id in item["evidence_ids"]}
        scope_counts[
            "mixed" if len(present) > 1 else next(iter(present), "none")
        ] += 1
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "base_catalog": copy.deepcopy(base_catalog),
        "active_pages": copy.deepcopy(active_pages),
        "active_scope_by_evidence_id": dict(scopes),
        "core_page_count": len(core_pages),
        "reserve_page_count": len(reserve_pages),
        "active_page_count": len(active_pages),
        "eligible_support_scope_counts": dict(sorted(scope_counts.items())),
        "baseline_and_candidate_share_exact_active_pages": True,
        "candidate_only_adds_programmatic_support_structure": True,
        "pure_reserve_effect_ablation": False,
    }
    value["catalog_payload_sha256"] = payload_sha256(value)
    validate_active_catalog(value, targets=targets)
    return value


def validate_active_catalog(
    value: Mapping[str, Any],
    *,
    targets: Sequence[CellTarget | Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("catalog_payload_sha256", None)
    base_catalog = value.get("base_catalog")
    pages = value.get("active_pages")
    scopes = value.get("active_scope_by_evidence_id")
    scope_counts = value.get("eligible_support_scope_counts")
    if (
        set(value) != CATALOG_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(base_catalog, Mapping)
        or not isinstance(pages, list)
        or not isinstance(scopes, Mapping)
        or not isinstance(scope_counts, Mapping)
        or value.get("active_page_count") != len(pages)
        or value.get("core_page_count", -1) + value.get("reserve_page_count", -1)
        != len(pages)
        or set(scopes) != {page.get("evidence_id") for page in pages}
        or any(scope not in {"core", "reserve"} for scope in scopes.values())
        or sum(scope == "core" for scope in scopes.values())
        != value.get("core_page_count")
        or sum(scope == "reserve" for scope in scopes.values())
        != value.get("reserve_page_count")
        or value.get("baseline_and_candidate_share_exact_active_pages") is not True
        or value.get("candidate_only_adds_programmatic_support_structure") is not True
        or value.get("pure_reserve_effect_ablation") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.39 active catalog identity drifted")
    validate_catalog_identity(base_catalog)
    if targets is not None:
        validate_support_catalog(base_catalog, targets, pages)
    expected_scopes: Counter[str] = Counter()
    for item in base_catalog["support_sets"]:
        present = {str(scopes[evidence_id]) for evidence_id in item["evidence_ids"]}
        expected_scopes["mixed" if len(present) > 1 else next(iter(present), "none")] += 1
    if dict(sorted(expected_scopes.items())) != dict(scope_counts):
        raise ValueError("V2.43.39 support scope accounting drifted")
    return dict(value)


def resolve_active_selection(
    catalog: Mapping[str, Any],
    *,
    row_key: str,
    column: str,
    new_value: str,
    support_set_id: str,
    declared_evidence_ids: Sequence[str],
) -> dict[str, Any]:
    validate_active_catalog(catalog)
    base_receipt = resolve_support_selection(
        catalog["base_catalog"],
        row_key=row_key,
        column=column,
        new_value=new_value,
        support_set_id=support_set_id,
        declared_evidence_ids=declared_evidence_ids,
    )
    scopes = catalog["active_scope_by_evidence_id"]
    support = next(
        (
            item
            for item in catalog["base_catalog"]["support_sets"]
            if item["support_set_id"] == support_set_id
        ),
        None,
    )
    evidence_ids = support["evidence_ids"] if support is not None else []
    core = sum(scopes.get(evidence_id) == "core" for evidence_id in evidence_ids)
    reserve = sum(scopes.get(evidence_id) == "reserve" for evidence_id in evidence_ids)
    support_scope = (
        "mixed" if core and reserve else "core" if core else "reserve" if reserve else "none"
    )
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "active_catalog_payload_sha256": catalog["catalog_payload_sha256"],
        "base_resolution_receipt": copy.deepcopy(base_receipt),
        "support_scope": support_scope,
        "core_evidence_count": core,
        "reserve_evidence_count": reserve,
        "admitted": base_receipt["admitted"],
        "conditional_entropy_reduction_nats": base_receipt[
            "conditional_entropy_reduction_nats"
        ],
        "question_query_url_host_page_candidate_value_evidence_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    validate_active_resolution(value)
    return value


def validate_active_resolution(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    base_receipt = value.get("base_resolution_receipt")
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != RECEIPT_ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(base_receipt, Mapping)
        or value.get("support_scope") not in {"none", "core", "reserve", "mixed"}
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in ("core_evidence_count", "reserve_evidence_count")
        )
        or value.get("admitted") is not base_receipt.get("admitted")
        or value.get("conditional_entropy_reduction_nats")
        != base_receipt.get("conditional_entropy_reduction_nats")
        or value.get("question_query_url_host_page_candidate_value_evidence_id_or_credential_emitted") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("file_environment_network_model_search_fetch_or_process_accessed") is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.39 active resolution drifted")
    validate_resolution_receipt(base_receipt)
    return dict(value)


__all__ = [
    "POLICY_ID",
    "ROLE",
    "build_active_catalog",
    "resolve_active_selection",
    "validate_active_catalog",
    "validate_active_resolution",
]
