"""Versioned path-binding recovery for the V2.42.14 joint package.

V2.42.14 froze a nonexistent entropy recovery-publication path while the
actual V2.42.13 publisher uses ``selected_entropy_component_publication``.
This module changes only that path and the hashes transitively derived from
it.  All owner, parent, schema, component, regression, and authorization
fields remain byte-identical.
"""

from __future__ import annotations

import copy
from typing import Any, Mapping

from deepwide_agent.v24200_successor import payload_sha256
from deepwide_agent.v24204_postdecision_work_order import (
    build_work_order_manifest,
)
from deepwide_agent.v24206_markdown_publisher import ENTROPY
from deepwide_agent.v24214_joint_package import (
    PUBLICATION_PATHS as V24214_PUBLICATION_PATHS,
    build_joint_package_manifest,
    build_joint_package_order,
    validate_joint_package_order,
)


FAILED_AUDIT_PATH = (
    "results/v24214_selected_joint_package_failed_activation_audit_v1_20260731.json"
)
FAILED_AUDIT_SHA256 = (
    "f216e96eaeba94bd04d4ca082903e5825e0c0624608846c199f9888679c8974e"
)
FROZEN_WRONG_ENTROPY_PATH = V24214_PUBLICATION_PATHS["entropy"]
ACTUAL_ENTROPY_PATH = (
    "results/v24213_selected_entropy_component_publication_v1_20260731.json"
)


def build_recovery_order(work_order: Mapping[str, Any]) -> dict[str, Any]:
    """Apply the single registered path correction to one frozen order."""

    base = validate_joint_package_order(build_joint_package_order(work_order))
    value = copy.deepcopy(base)
    components = list(value["eligible_components"])
    chain = value["parent_chain"]
    entropy_rows = [row for row in chain if row.get("component") == ENTROPY]
    if ENTROPY in components:
        if (
            len(entropy_rows) != 1
            or entropy_rows[0].get("stage") != "entropy"
            or entropy_rows[0].get("publication_path")
            != FROZEN_WRONG_ENTROPY_PATH
            or value.get("deepest_semantic_owner") != "entropy"
            or value.get("deepest_byte_owner") != "entropy"
            or value.get("deepest_publication_path")
            != FROZEN_WRONG_ENTROPY_PATH
        ):
            raise RuntimeError("V2.42.15 frozen entropy path boundary drifted")
        stage = entropy_rows[0]
        stage.pop("stage_payload_sha256")
        stage["publication_path"] = ACTUAL_ENTROPY_PATH
        stage["stage_payload_sha256"] = payload_sha256(stage)
        value["parent_chain_payload_sha256"] = payload_sha256(chain)
        value["deepest_publication_path"] = ACTUAL_ENTROPY_PATH
        value.pop("joint_order_payload_sha256")
        value["joint_order_payload_sha256"] = payload_sha256(value)
    elif entropy_rows:
        raise RuntimeError("V2.42.15 entropy stage appeared on an absent branch")
    return value


def validate_recovery_order(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one recovery order from its registered V2.42.04 decision."""

    if not isinstance(value, Mapping):
        raise RuntimeError("V2.42.15 recovery order is not an object")
    digest = value.get("decision_sha256")
    rows = build_work_order_manifest()["rows"]
    if not isinstance(digest, str) or digest not in rows:
        raise RuntimeError("V2.42.15 recovery decision is unregistered")
    expected = build_recovery_order(rows[digest])
    if dict(value) != expected:
        raise RuntimeError("V2.42.15 recovery order bytes drifted")
    return expected


def build_recovery_manifest() -> dict[str, Any]:
    """Freeze the corrected path over all 36 possible decisions."""

    work_orders = build_work_order_manifest()["rows"]
    base = build_joint_package_manifest()
    rows = {
        decision: build_recovery_order(work_orders[decision])
        for decision in sorted(work_orders)
    }
    changed = [
        decision
        for decision in rows
        if rows[decision] != base["rows"][decision]
    ]
    unchanged = [decision for decision in rows if decision not in changed]
    if (
        len(rows) != 36
        or len(changed) != 18
        or len(unchanged) != 18
        or any(ENTROPY not in rows[decision]["eligible_components"] for decision in changed)
        or any(ENTROPY in rows[decision]["eligible_components"] for decision in unchanged)
    ):
        raise RuntimeError("V2.42.15 recovery coverage drifted")
    invariant_fields = (
        "decision_sha256",
        "baseline_name",
        "baseline_publication",
        "eligible_components",
        "parent_dependency_order_components",
        "selected_components_covered_in_frozen_order",
        "all_selected_components_covered_exactly_once",
        "deepest_semantic_owner",
        "deepest_byte_owner",
        "final_state_schema_version",
        "identity_handoff_only",
        "joint_revalidation_required",
        "full_parent_and_component_regression_required",
        "strict_component_activation_required_when_nonempty",
        "silent_component_drop_or_baseline_fallback_allowed",
        "candidate_directory_overlay_allowed",
        "joint_package_built_or_materialized",
        "package_gate_evaluated_or_launched",
        "shared_api_lease_acquired",
        "network_model_search_fetch_evaluator_or_api_called",
        "mapping_gold_category_question_type_evaluator_score_or_reward_read",
        "benchmark_forward_or_full220_launch_allowed",
        "leaderboard_submission_or_sota_claim",
    )
    for decision in rows:
        if any(
            rows[decision][field] != base["rows"][decision][field]
            for field in invariant_fields
        ):
            raise RuntimeError("V2.42.15 non-path invariant changed")
    summary = copy.deepcopy(base["summary"])
    summary.update(
        recovery_decision_count=36,
        entropy_path_corrected_count=len(changed),
        byte_identical_nonentropy_order_count=len(unchanged),
        other_field_change_authorized_count=0,
    )
    return {
        "rows": rows,
        "summary": summary,
        "recovery_parent": {
            "path": FAILED_AUDIT_PATH,
            "sha256": FAILED_AUDIT_SHA256,
        },
        "only_recovery_delta": {
            "source_binding_fields": [
                "parent_chain[entropy].publication_path",
                "deepest_publication_path",
            ],
            "from": FROZEN_WRONG_ENTROPY_PATH,
            "to": ACTUAL_ENTROPY_PATH,
            "transitive_hash_fields_resealed": [
                "parent_chain[entropy].stage_payload_sha256",
                "parent_chain_payload_sha256",
                "joint_order_payload_sha256",
            ],
        },
        "manifest_payload_sha256": payload_sha256(rows),
    }


__all__ = [
    "ACTUAL_ENTROPY_PATH",
    "FAILED_AUDIT_PATH",
    "FAILED_AUDIT_SHA256",
    "FROZEN_WRONG_ENTROPY_PATH",
    "build_recovery_manifest",
    "build_recovery_order",
    "validate_recovery_order",
]
