"""Pure selected-parent contract for the V2.42.10 search publisher.

The contract owns only ``search_yield_shared_query``.  It resolves the real
semantic parent selected by Markdown and branch-scope components before a
future immutable V2.41.80 outcome is consulted.  In particular, P12 scope
uses historical schema70 bytes; the schema76/schema77 scope publications are
zero-byte aliases of their Markdown parents.

This module never reads a live gate, task state, prediction, evaluator
artifact, credential, or service and grants no benchmark authority.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from deepwide_agent.v24200_successor import payload_sha256
from deepwide_agent.v24206_markdown_publisher import (
    ENTROPY,
    MARKDOWN,
    SCOPE,
    SEARCH,
    validate_work_order,
)


PARENT_VARIANTS = (
    "selected_baseline",
    "selected_markdown_candidate",
    "selected_scope_candidate",
)

# Seven unique byte graphs cover the nine semantic parent branches.  Mainline
# scope is a zero-byte alias, so it intentionally shares the Markdown target.
TARGET_SCHEMAS = {
    ("p12", "selected_baseline"): 80,
    ("p12", "selected_markdown_candidate"): 81,
    ("p12", "selected_scope_candidate"): 86,
    ("schema76", "selected_baseline"): 82,
    ("schema76", "selected_markdown_candidate"): 83,
    ("schema76", "selected_scope_candidate"): 83,
    ("schema77", "selected_baseline"): 84,
    ("schema77", "selected_markdown_candidate"): 85,
    ("schema77", "selected_scope_candidate"): 85,
}


def _parent_variant(components: list[str]) -> str:
    if SCOPE in components:
        if MARKDOWN not in components:
            raise RuntimeError("V2.42.10 scope appeared without Markdown parent")
        return "selected_scope_candidate"
    if MARKDOWN in components:
        return "selected_markdown_candidate"
    return "selected_baseline"


def build_search_publication_order(work_order: Mapping[str, Any]) -> dict[str, Any]:
    """Classify one exact registered work order without reading an outcome."""

    selected = validate_work_order(work_order)
    components = list(selected["eligible_components"])
    baseline = str(selected["baseline_name"])
    search_selected = SEARCH in components
    semantic_parent = _parent_variant(components)
    if baseline not in {"p12", "schema76", "schema77"}:
        raise RuntimeError("V2.42.10 baseline is unsupported")

    if search_selected:
        target_schema = TARGET_SCHEMAS[(baseline, semantic_parent)]
        if baseline == "p12":
            byte_parent = semantic_parent
        elif semantic_parent == "selected_scope_candidate":
            byte_parent = "selected_markdown_candidate"
        else:
            byte_parent = semantic_parent
        disposition = f"{baseline}_{semantic_parent}_search_publication_pending_quality"
        publication_mode = "materialize_after_immutable_search_yield_go"
    else:
        target_schema = None
        byte_parent = None
        disposition = "selected_work_order_has_no_search_component"
        publication_mode = "content_free_no_op_component_absent"

    value: dict[str, Any] = {
        "decision_sha256": selected["decision_sha256"],
        "baseline_name": baseline,
        "baseline_publication": dict(selected["baseline_publication"]),
        "eligible_components": components,
        "search_component_selected": search_selected,
        "semantic_parent_variant": semantic_parent,
        "byte_parent_variant": byte_parent,
        "disposition": disposition,
        "publication_mode": publication_mode,
        "target_state_schema_version": target_schema,
        "p12_scope_uses_historical_schema70_parent": bool(
            search_selected
            and baseline == "p12"
            and semantic_parent == "selected_scope_candidate"
        ),
        "mainline_scope_is_zero_byte_markdown_alias": bool(
            search_selected
            and baseline in {"schema76", "schema77"}
            and semantic_parent == "selected_scope_candidate"
        ),
        "immutable_v24180_terminal_outcome_required": search_selected,
        "immutable_v24180_go_required_for_materialization": search_selected,
        "no_go_or_incomplete_attempt_retires_component_without_rerun": search_selected,
        "unowned_components_preserved_as_blockers": [
            name for name in components if name == ENTROPY
        ],
        "search_candidate_bytes_built_or_materialized": False,
        "entropy_controller_published_or_implemented": False,
        "joint_package_built_or_materialized": False,
        "package_gate_evaluated_or_launched": False,
        "shared_api_lease_acquired": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    value["publication_order_payload_sha256"] = payload_sha256(value)
    return value


def build_search_publication_manifest() -> dict[str, Any]:
    """Predeclare all outcome-independent search dispositions."""

    from deepwide_agent.v24204_postdecision_work_order import (
        build_work_order_manifest,
    )

    work_orders = build_work_order_manifest()["rows"]
    rows = {
        digest: build_search_publication_order(work_orders[digest])
        for digest in sorted(work_orders)
    }
    selected = [row for row in rows.values() if row["search_component_selected"]]
    semantic_counts = Counter(
        f"{row['baseline_name']}:{row['semantic_parent_variant']}" for row in selected
    )
    expected_semantic = {
        f"{baseline}:{variant}": 2
        for baseline in ("p12", "schema76", "schema77")
        for variant in PARENT_VARIANTS
    }
    if dict(sorted(semantic_counts.items())) != dict(sorted(expected_semantic.items())):
        raise RuntimeError("V2.42.10 semantic parent coverage drifted")
    target_counts = Counter(row["target_state_schema_version"] for row in selected)
    if dict(sorted(target_counts.items())) != {
        80: 2,
        81: 2,
        82: 2,
        83: 4,
        84: 2,
        85: 4,
        86: 2,
    }:
        raise RuntimeError("V2.42.10 unique byte-graph coverage drifted")
    return {
        "rows": rows,
        "summary": {
            "decision_count": len(rows),
            "search_selected_count": len(selected),
            "search_absent_noop_count": len(rows) - len(selected),
            "semantic_parent_branch_count": len(semantic_counts),
            "unique_parent_byte_graph_count": len(target_counts),
            "semantic_parent_counts": dict(sorted(semantic_counts.items())),
            "target_schema_counts": {
                str(key): target_counts[key] for key in sorted(target_counts)
            },
            "p12_schema70_search_target_schema": 86,
            "search_candidate_materialized_count": 0,
            "benchmark_launch_authorized_count": 0,
        },
        "manifest_payload_sha256": payload_sha256(rows),
    }


__all__ = [
    "PARENT_VARIANTS",
    "TARGET_SCHEMAS",
    "build_search_publication_manifest",
    "build_search_publication_order",
]
