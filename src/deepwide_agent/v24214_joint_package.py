"""Outcome-independent deepest-owner contract for the V2.42 joint package.

The component publishers are cumulative candidates, not independent overlay
directories.  This module maps every frozen V2.42.04 work order to one exact
parent chain and one deepest byte graph.  It reads no files or live outcomes,
does not materialize a package, and grants no evaluation or benchmark
authority.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from deepwide_agent.v24200_successor import payload_sha256
from deepwide_agent.v24204_postdecision_work_order import (
    build_work_order_manifest,
)
from deepwide_agent.v24206_markdown_publisher import (
    ENTROPY,
    MARKDOWN,
    SCOPE,
    SEARCH,
    build_markdown_publication_order,
    validate_work_order,
)
from deepwide_agent.v24207_scope_alias_publisher import (
    build_scope_publication_order,
)
from deepwide_agent.v24210_search_publisher import (
    build_search_publication_order,
)
from deepwide_agent.v24211_entropy_feasibility import (
    build_entropy_integration_order,
)


PUBLICATION_PATHS = {
    "markdown": (
        "results/v24206_selected_markdown_component_publication_v1_20260731.json"
    ),
    "scope": (
        "results/v24207_selected_scope_alias_component_publication_v1_20260731.json"
    ),
    "search": (
        "results/v24210_selected_search_component_publication_v1_20260731.json"
    ),
    "entropy": (
        "results/v24213_selected_entropy_component_recovery_publication_v1_20260731.json"
    ),
}

STAGE_COMPONENTS = {
    "markdown": MARKDOWN,
    "scope": SCOPE,
    "search": SEARCH,
    "entropy": ENTROPY,
}


def _stage(
    *,
    name: str,
    component: str | None,
    semantic_owner: str,
    byte_owner: str,
    publication_path: str,
    source_schema: int | None,
    target_schema: int,
    zero_byte_alias: bool,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "stage": name,
        "component": component,
        "semantic_owner": semantic_owner,
        "byte_owner": byte_owner,
        "publication_path": publication_path,
        "source_state_schema_version": source_schema,
        "target_state_schema_version": target_schema,
        "zero_byte_alias": zero_byte_alias,
        "candidate_directory_overlay_required": False,
    }
    value["stage_payload_sha256"] = payload_sha256(value)
    return value


def build_joint_package_order(work_order: Mapping[str, Any]) -> dict[str, Any]:
    """Derive the only admissible deepest candidate for one work order."""

    selected = validate_work_order(work_order)
    decision = str(selected["decision_sha256"])
    components = list(selected["eligible_components"])
    baseline = str(selected["baseline_name"])
    baseline_publication = dict(selected["baseline_publication"])
    baseline_schema = int(baseline_publication["state_schema_version"])

    markdown = build_markdown_publication_order(selected)
    scope = build_scope_publication_order(selected)
    search = build_search_publication_order(selected)
    for component_order in (markdown, scope, search):
        if (
            component_order["decision_sha256"] != decision
            or component_order["eligible_components"] != components
        ):
            raise RuntimeError("V2.42.14 component order binding drifted")

    chain = [
        _stage(
            name="baseline",
            component=None,
            semantic_owner="baseline",
            byte_owner="baseline",
            publication_path=str(baseline_publication["path"]),
            source_schema=None,
            target_schema=baseline_schema,
            zero_byte_alias=False,
        )
    ]
    current_schema = baseline_schema

    if MARKDOWN in components:
        target = markdown.get("target_state_schema_version")
        if not isinstance(target, int):
            raise RuntimeError("V2.42.14 Markdown target schema is absent")
        chain.append(
            _stage(
                name="markdown",
                component=MARKDOWN,
                semantic_owner="markdown",
                byte_owner="markdown",
                publication_path=PUBLICATION_PATHS["markdown"],
                source_schema=current_schema,
                target_schema=target,
                zero_byte_alias=False,
            )
        )
        current_schema = target

    if SCOPE in components:
        target = scope.get("target_state_schema_version")
        if not isinstance(target, int):
            raise RuntimeError("V2.42.14 scope target schema is absent")
        zero_alias = bool(
            scope.get("publication_mode")
            == "bind_zero_byte_mainline_scope_namespace_alias"
        )
        if zero_alias and target != current_schema:
            raise RuntimeError("V2.42.14 scope alias changed byte identity")
        chain.append(
            _stage(
                name="scope",
                component=SCOPE,
                semantic_owner="scope",
                byte_owner="markdown" if zero_alias else "scope",
                publication_path=PUBLICATION_PATHS["scope"],
                source_schema=current_schema,
                target_schema=target,
                zero_byte_alias=zero_alias,
            )
        )
        current_schema = target

    if SEARCH in components:
        target = search.get("target_state_schema_version")
        if not isinstance(target, int):
            raise RuntimeError("V2.42.14 search target schema is absent")
        chain.append(
            _stage(
                name="search",
                component=SEARCH,
                semantic_owner="search",
                byte_owner="search",
                publication_path=PUBLICATION_PATHS["search"],
                source_schema=current_schema,
                target_schema=target,
                zero_byte_alias=False,
            )
        )
        current_schema = target

    entropy: dict[str, Any] | None = None
    if ENTROPY in components:
        entropy = build_entropy_integration_order(selected)
        source = entropy.get("source_state_schema_version")
        target = entropy.get("target_state_schema_version")
        if source != current_schema or not isinstance(target, int):
            raise RuntimeError("V2.42.14 entropy parent chain drifted")
        chain.append(
            _stage(
                name="entropy",
                component=ENTROPY,
                semantic_owner="entropy",
                byte_owner="entropy",
                publication_path=PUBLICATION_PATHS["entropy"],
                source_schema=current_schema,
                target_schema=target,
                zero_byte_alias=False,
            )
        )
        current_schema = target

    parent_chain_components = [
        str(row["component"])
        for row in chain
        if row["component"] is not None
    ]
    covered_in_frozen_order = [
        component for component in components if component in parent_chain_components
    ]
    if (
        covered_in_frozen_order != components
        or len(parent_chain_components) != len(components)
        or len(set(parent_chain_components)) != len(parent_chain_components)
    ):
        raise RuntimeError("V2.42.14 parent chain dropped or reordered a component")
    deepest = chain[-1]
    identity = not components
    value: dict[str, Any] = {
        "decision_sha256": decision,
        "baseline_name": baseline,
        "baseline_publication": baseline_publication,
        "eligible_components": components,
        "parent_chain": chain,
        "parent_chain_payload_sha256": payload_sha256(chain),
        "parent_dependency_order_components": parent_chain_components,
        "selected_components_covered_in_frozen_order": covered_in_frozen_order,
        "all_selected_components_covered_exactly_once": True,
        "deepest_semantic_owner": deepest["semantic_owner"],
        "deepest_byte_owner": deepest["byte_owner"],
        "deepest_publication_path": deepest["publication_path"],
        "final_state_schema_version": current_schema,
        "identity_handoff_only": identity,
        "joint_revalidation_required": not identity,
        "full_parent_and_component_regression_required": not identity,
        "strict_component_activation_required_when_nonempty": not identity,
        "silent_component_drop_or_baseline_fallback_allowed": False,
        "candidate_directory_overlay_allowed": False,
        "joint_package_built_or_materialized": False,
        "package_gate_evaluated_or_launched": False,
        "shared_api_lease_acquired": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    value["joint_order_payload_sha256"] = payload_sha256(value)
    return value


def validate_joint_package_order(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate an order by recomputing its registered work-order row."""

    if not isinstance(value, Mapping):
        raise RuntimeError("V2.42.14 joint order is not an object")
    digest = value.get("decision_sha256")
    rows = build_work_order_manifest()["rows"]
    if not isinstance(digest, str) or digest not in rows:
        raise RuntimeError("V2.42.14 joint order decision is unregistered")
    expected = build_joint_package_order(rows[digest])
    if dict(value) != expected:
        raise RuntimeError("V2.42.14 joint order bytes drifted")
    return expected


def build_joint_package_manifest() -> dict[str, Any]:
    """Freeze deepest-owner and parent-chain rows for all 36 decisions."""

    work_orders = build_work_order_manifest()["rows"]
    rows = {
        decision: build_joint_package_order(work_orders[decision])
        for decision in sorted(work_orders)
    }
    semantic_counts = Counter(
        row["deepest_semantic_owner"] for row in rows.values()
    )
    byte_counts = Counter(row["deepest_byte_owner"] for row in rows.values())
    expected_semantic = {
        "baseline": 3,
        "entropy": 18,
        "markdown": 3,
        "scope": 3,
        "search": 9,
    }
    expected_byte = {
        "baseline": 3,
        "entropy": 18,
        "markdown": 5,
        "scope": 1,
        "search": 9,
    }
    identity = sum(row["identity_handoff_only"] for row in rows.values())
    if (
        len(rows) != 36
        or dict(sorted(semantic_counts.items())) != expected_semantic
        or dict(sorted(byte_counts.items())) != expected_byte
        or identity != 3
    ):
        raise RuntimeError("V2.42.14 joint manifest coverage drifted")
    return {
        "rows": rows,
        "summary": {
            "decision_count": len(rows),
            "identity_handoff_count": identity,
            "joint_revalidation_required_count": len(rows) - identity,
            "deepest_semantic_owner_counts": dict(
                sorted(semantic_counts.items())
            ),
            "deepest_byte_owner_counts": dict(sorted(byte_counts.items())),
            "candidate_directory_overlay_count": 0,
            "joint_package_materialized_count": 0,
            "package_gate_evaluated_count": 0,
            "benchmark_launch_authorized_count": 0,
        },
        "manifest_payload_sha256": payload_sha256(rows),
    }


__all__ = [
    "PUBLICATION_PATHS",
    "STAGE_COMPONENTS",
    "build_joint_package_manifest",
    "build_joint_package_order",
    "validate_joint_package_order",
]
