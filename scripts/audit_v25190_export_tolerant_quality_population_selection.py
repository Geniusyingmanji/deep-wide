#!/usr/bin/env python3
"""Aggregate-only selection audit for the V2.51.90 fresh quality cohort."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import audit_v25141_population_selection as base  # noqa: E402


ROLE = "v25190_export_tolerant_quality_population_selection_aggregate_audit"
payload_sha256 = base.payload_sha256


def build_audit(
    identities: Sequence[str], *, parent_commit: str, now: int | None = None
) -> dict[str, Any]:
    value = base.build_audit(
        identities, parent_commit=parent_commit, now=now
    )
    value["role"] = ROLE
    value.update(
        {
            "repository_history_used_for_disjointness_only": True,
            "manual_preselection_read_current_public_cran_packages_index": True,
            "preselection_enriched_for_license_literal_pipe": True,
            "preselection_is_unconditional_natural_population": False,
            "direct_preselection_transport_receipt_persisted": False,
            "preselection_endpoint_or_field_value_persisted": False,
            "preselection_model_hosted_search_or_evaluator_called": False,
            "v25187_population_reuse": False,
            "prior_external_population_reuse": False,
            "population_frozen_for_single_future_export_tolerant_same_response_quality_gate": True,
            "identity_is_future_visible_task_input_not_hidden_mapping": True,
            "external_forward_evaluator_deepwidebench_or_sota_authorized": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
        }
    )
    value.pop("audit_payload_sha256")
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    true_flags = (
        "repository_history_used_for_disjointness_only",
        "manual_preselection_read_current_public_cran_packages_index",
        "preselection_enriched_for_license_literal_pipe",
        "population_frozen_for_single_future_export_tolerant_same_response_quality_gate",
        "identity_is_future_visible_task_input_not_hidden_mapping",
    )
    false_flags = (
        "identity_plaintext_or_item_hash_persisted",
        "clue_to_identity_mapping_persisted",
        "network_endpoint_page_value_model_or_evaluator_access",
        "preselection_is_unconditional_natural_population",
        "direct_preselection_transport_receipt_persisted",
        "preselection_endpoint_or_field_value_persisted",
        "preselection_model_hosted_search_or_evaluator_called",
        "v25187_population_reuse",
        "prior_external_population_reuse",
        "external_forward_evaluator_deepwidebench_or_sota_authorized",
        "entropy_or_information_gain_assigns_signed_credit",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
    )
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("identity_count") != 20
        or copied.get("unique_identity_count") != 20
        or copied.get("identity_history_introduction_hit_total") != 0
        or copied.get("identity_history_zero_hit_count") != 20
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.51.90 population selection audit drifted")
    return copied


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--identity", action="append", required=True)
    args = parser.parse_args()
    value = build_audit(args.identity, parent_commit=args.parent)
    base.publish_exclusive(ROOT / args.output, value)
    print(
        json.dumps(
            {
                "path": str(args.output),
                "identity_count": value["identity_count"],
                "history_hits": value["identity_history_introduction_hit_total"],
                "mechanism_enriched": value[
                    "preselection_enriched_for_license_literal_pipe"
                ],
                "audit_valid": value["audit_valid"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
