"""Pure contract for the V2.42.07 selected branch-scope publisher.

The publisher owns only ``markdown_branch_scope_open_fallback``.  P12 binds
the already frozen schema70 bytes.  The schema76/schema77 baselines already
contain the same conservative scope hook exactly once, so their selected
Markdown successors use a zero-byte namespace alias instead of replaying the
historical patch.  Search, entropy, joint packaging, evaluation, and benchmark
execution remain outside this contract.
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


DISPOSITIONS = (
    "selected_work_order_has_no_branch_scope_component",
    "p12_historical_markdown_scope_postdecision_binding",
    "schema76_existing_mainline_scope_namespace_alias",
    "schema77_existing_mainline_scope_namespace_alias",
)


def build_scope_publication_order(work_order: Mapping[str, Any]) -> dict[str, Any]:
    """Classify one exact work order without opening a parent publication."""

    selected = validate_work_order(work_order)
    components = list(selected["eligible_components"])
    baseline = str(selected["baseline_name"])
    scope_selected = SCOPE in components
    if scope_selected and MARKDOWN not in components:
        raise RuntimeError("V2.42.07 branch scope lacks its Markdown parent")

    if not scope_selected:
        disposition = "selected_work_order_has_no_branch_scope_component"
        publication_mode = "no_op_component_absent"
        target_schema = None
    elif baseline == "p12":
        disposition = "p12_historical_markdown_scope_postdecision_binding"
        publication_mode = "bind_historical_schema70_bytes"
        target_schema = 70
    elif baseline == "schema76":
        disposition = "schema76_existing_mainline_scope_namespace_alias"
        publication_mode = "bind_zero_byte_mainline_scope_namespace_alias"
        target_schema = 78
    elif baseline == "schema77":
        disposition = "schema77_existing_mainline_scope_namespace_alias"
        publication_mode = "bind_zero_byte_mainline_scope_namespace_alias"
        target_schema = 79
    else:  # pragma: no cover - frozen work-order manifest has three baselines.
        raise RuntimeError("V2.42.07 baseline is unsupported")
    if disposition not in DISPOSITIONS:
        raise RuntimeError("V2.42.07 disposition is unregistered")

    value: dict[str, Any] = {
        "decision_sha256": selected["decision_sha256"],
        "baseline_name": baseline,
        "baseline_publication": dict(selected["baseline_publication"]),
        "eligible_components": components,
        "branch_scope_component_selected": scope_selected,
        "markdown_parent_component_required": scope_selected,
        "disposition": disposition,
        "publication_mode": publication_mode,
        "target_state_schema_version": target_schema,
        "unowned_components_preserved_as_blockers": [
            name for name in components if name not in {MARKDOWN, SCOPE}
        ],
        "historical_scope_patch_reapplied": False,
        "candidate_bytes_modified_or_materialized": False,
        "search_yield_published_or_implemented": False,
        "entropy_controller_published_or_implemented": False,
        "joint_package_built_or_materialized": False,
        "package_gate_evaluated_or_launched": False,
        "shared_api_lease_acquired": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    if SEARCH in components and value["search_yield_published_or_implemented"]:
        raise RuntimeError("V2.42.07 search boundary drifted")
    if ENTROPY in components and value["entropy_controller_published_or_implemented"]:
        raise RuntimeError("V2.42.07 entropy boundary drifted")
    value["publication_order_payload_sha256"] = payload_sha256(value)
    return value


def build_scope_publication_manifest() -> dict[str, Any]:
    """Predeclare the scope disposition for all 36 frozen work orders."""

    from deepwide_agent.v24204_postdecision_work_order import (
        build_work_order_manifest,
    )

    work_orders = build_work_order_manifest()["rows"]
    rows = {
        digest: build_scope_publication_order(work_orders[digest])
        for digest in sorted(work_orders)
    }
    counts = Counter(row["disposition"] for row in rows.values())
    expected = {
        "selected_work_order_has_no_branch_scope_component": 24,
        "p12_historical_markdown_scope_postdecision_binding": 4,
        "schema76_existing_mainline_scope_namespace_alias": 4,
        "schema77_existing_mainline_scope_namespace_alias": 4,
    }
    if dict(sorted(counts.items())) != dict(sorted(expected.items())):
        raise RuntimeError("V2.42.07 publication coverage drifted")
    return {
        "rows": rows,
        "summary": {
            "decision_count": len(rows),
            "disposition_counts": dict(sorted(counts.items())),
            "scope_selected_count": 12,
            "no_scope_noop_count": 24,
            "p12_historical_binding_count": 4,
            "mainline_zero_byte_alias_count": 8,
            "historical_patch_reapplication_count": 0,
            "candidate_bytes_modified_count": 0,
            "joint_package_materialized_count": 0,
            "benchmark_launch_authorized_count": 0,
        },
        "manifest_payload_sha256": payload_sha256(rows),
    }


__all__ = [
    "DISPOSITIONS",
    "build_scope_publication_manifest",
    "build_scope_publication_order",
]
