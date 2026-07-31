"""Pure classification for selected-baseline search rebase feasibility.

The contract classifies all frozen V2.42.00 work orders without reading a live
gate, task state, predictions, evaluator data, credentials, or services.  It
does not publish search bytes, build a joint package, or authorize a benchmark.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from deepwide_agent.v24204_postdecision_work_order import build_work_order_manifest
from deepwide_agent.v24206_markdown_publisher import MARKDOWN, SEARCH
from deepwide_agent.v24203_materialization_audit import reject_forbidden_metadata


DISPOSITIONS = (
    "selected_work_order_has_no_search_component",
    "p12_search_rebase_feasibility_audit_required",
    "schema76_search_rebase_feasibility_audit_required",
    "schema77_search_rebase_feasibility_audit_required",
)


def classify_search_rebase_order(work_order: Mapping[str, Any]) -> dict[str, Any]:
    """Classify one exact registered work order or fail closed."""

    if not isinstance(work_order, Mapping):
        raise RuntimeError("V2.42.08 work order is not an object")
    reject_forbidden_metadata(work_order)
    digest = work_order.get("decision_sha256")
    manifest = build_work_order_manifest()["rows"]
    if not isinstance(digest, str) or digest not in manifest:
        raise RuntimeError("V2.42.08 work order is not registered")
    expected = manifest[digest]
    if dict(work_order) != expected:
        raise RuntimeError("V2.42.08 work-order bytes drifted")

    components = list(expected["eligible_components"])
    baseline = str(expected["baseline_name"])
    selected = SEARCH in components
    if not selected:
        disposition = "selected_work_order_has_no_search_component"
        parent_variant = "selected_baseline_or_markdown_publication"
    else:
        disposition = f"{baseline}_search_rebase_feasibility_audit_required"
        parent_variant = (
            "selected_markdown_candidate"
            if MARKDOWN in components
            else "selected_baseline"
        )
    if disposition not in DISPOSITIONS:
        raise RuntimeError("V2.42.08 disposition is unregistered")

    return {
        "decision_sha256": digest,
        "baseline_name": baseline,
        "eligible_components": components,
        "search_component_selected": selected,
        "parent_candidate_variant": parent_variant,
        "disposition": disposition,
        "historical_v24179_pure_scheduler_available": True,
        "historical_v24180_quality_gate_terminal_required_for_publication": selected,
        "selected_parent_bytes_must_remain_unmodified_by_this_audit": True,
        "search_candidate_bytes_built_or_materialized": False,
        "search_component_publication_available": False,
        "joint_package_built_or_materialized": False,
        "package_gate_evaluated_or_launched": False,
        "benchmark_forward_or_full220_launch_allowed": False,
    }


def build_search_rebase_manifest() -> dict[str, Any]:
    """Predeclare every search disposition before any terminal outcome."""

    work_orders = build_work_order_manifest()["rows"]
    rows = {
        digest: classify_search_rebase_order(work_orders[digest])
        for digest in sorted(work_orders)
    }
    counts = Counter(row["disposition"] for row in rows.values())
    expected = {
        "selected_work_order_has_no_search_component": 18,
        "p12_search_rebase_feasibility_audit_required": 6,
        "schema76_search_rebase_feasibility_audit_required": 6,
        "schema77_search_rebase_feasibility_audit_required": 6,
    }
    if dict(sorted(counts.items())) != dict(sorted(expected.items())):
        raise RuntimeError("V2.42.08 decision coverage drifted")
    return {
        "rows": rows,
        "summary": {
            "decision_count": len(rows),
            "disposition_counts": dict(sorted(counts.items())),
            "search_selected_count": 18,
            "search_absent_noop_count": 18,
            "baseline_only_parent_count": 6,
            "markdown_parent_count": 12,
            "search_candidate_materialized_count": 0,
            "benchmark_launch_authorized_count": 0,
        },
    }


__all__ = [
    "DISPOSITIONS",
    "build_search_rebase_manifest",
    "classify_search_rebase_order",
]
