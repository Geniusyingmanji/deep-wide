"""Pure selection contract for the V2.42.06 Markdown component publisher.

The contract authorizes exactly one selected-baseline-bound Markdown component
publication after a byte-exact V2.42.04 work order is terminal.  It never
authorizes search-yield, branch-scope, entropy, a joint package, a package
gate, or a benchmark launch.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from deepwide_agent.v24200_successor import payload_sha256
from deepwide_agent.v24203_materialization_audit import reject_forbidden_metadata
from deepwide_agent.v24204_postdecision_work_order import build_work_order_manifest


MARKDOWN = "markdown_rank_slot"
SCOPE = "markdown_branch_scope_open_fallback"
SEARCH = "search_yield_shared_query"
ENTROPY = "entropy_credit_controller"

DISPOSITIONS = (
    "selected_work_order_has_no_markdown_component",
    "p12_historical_markdown_postdecision_binding",
    "schema76_selected_baseline_markdown_rebase_publication",
    "schema77_selected_baseline_markdown_rebase_publication",
)


def validate_work_order(work_order: Mapping[str, Any]) -> dict[str, Any]:
    """Return the exact registered work order or fail closed."""

    if not isinstance(work_order, Mapping):
        raise RuntimeError("V2.42.06 work order is not an object")
    reject_forbidden_metadata(work_order)
    digest = work_order.get("decision_sha256")
    manifest = build_work_order_manifest()["rows"]
    if not isinstance(digest, str) or digest not in manifest:
        raise RuntimeError("V2.42.06 work order is not registered")
    expected = manifest[digest]
    if dict(work_order) != expected:
        raise RuntimeError("V2.42.06 work-order bytes drifted")
    return dict(expected)


def build_markdown_publication_order(work_order: Mapping[str, Any]) -> dict[str, Any]:
    """Classify one frozen work order without building component bytes."""

    selected = validate_work_order(work_order)
    components = list(selected["eligible_components"])
    baseline = str(selected["baseline_name"])
    markdown_selected = MARKDOWN in components
    if not markdown_selected:
        disposition = "selected_work_order_has_no_markdown_component"
        publication_mode = "no_op_component_absent"
        target_schema = None
    elif baseline == "p12":
        disposition = "p12_historical_markdown_postdecision_binding"
        publication_mode = "bind_historical_schema69_bytes"
        target_schema = 69
    elif baseline == "schema76":
        disposition = "schema76_selected_baseline_markdown_rebase_publication"
        publication_mode = "materialize_selected_baseline_rebase"
        target_schema = 78
    elif baseline == "schema77":
        disposition = "schema77_selected_baseline_markdown_rebase_publication"
        publication_mode = "materialize_selected_baseline_rebase"
        target_schema = 79
    else:  # pragma: no cover - frozen manifest has exactly three baselines.
        raise RuntimeError("V2.42.06 baseline is unsupported")
    if disposition not in DISPOSITIONS:
        raise RuntimeError("V2.42.06 disposition is unregistered")
    if SCOPE in components and not markdown_selected:
        raise RuntimeError("V2.42.06 scope appeared without Markdown parent")

    unowned = [name for name in components if name != MARKDOWN]
    value: dict[str, Any] = {
        "decision_sha256": selected["decision_sha256"],
        "baseline_name": baseline,
        "baseline_publication": dict(selected["baseline_publication"]),
        "eligible_components": components,
        "markdown_component_selected": markdown_selected,
        "disposition": disposition,
        "publication_mode": publication_mode,
        "target_state_schema_version": target_schema,
        "unowned_components_preserved_as_blockers": unowned,
        "search_yield_published_or_implemented": False,
        "branch_scope_alias_or_publication_created": False,
        "entropy_controller_published_or_implemented": False,
        "joint_package_built_or_materialized": False,
        "package_gate_evaluated_or_launched": False,
        "shared_api_lease_acquired": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    if SEARCH in unowned and value["search_yield_published_or_implemented"]:
        raise RuntimeError("V2.42.06 search boundary drifted")
    if SCOPE in unowned and value["branch_scope_alias_or_publication_created"]:
        raise RuntimeError("V2.42.06 scope boundary drifted")
    if ENTROPY in unowned and value["entropy_controller_published_or_implemented"]:
        raise RuntimeError("V2.42.06 entropy boundary drifted")
    value["publication_order_payload_sha256"] = payload_sha256(value)
    return value


def build_markdown_publication_manifest() -> dict[str, Any]:
    """Predeclare the outcome-independent publisher order for all decisions."""

    work_orders = build_work_order_manifest()["rows"]
    rows = {
        digest: build_markdown_publication_order(work_orders[digest])
        for digest in sorted(work_orders)
    }
    counts = Counter(row["disposition"] for row in rows.values())
    expected = {
        "selected_work_order_has_no_markdown_component": 12,
        "p12_historical_markdown_postdecision_binding": 8,
        "schema76_selected_baseline_markdown_rebase_publication": 8,
        "schema77_selected_baseline_markdown_rebase_publication": 8,
    }
    if dict(sorted(counts.items())) != dict(sorted(expected.items())):
        raise RuntimeError("V2.42.06 publication coverage drifted")
    return {
        "rows": rows,
        "summary": {
            "decision_count": len(rows),
            "disposition_counts": dict(sorted(counts.items())),
            "markdown_selected_count": 24,
            "no_markdown_noop_count": 12,
            "p12_historical_binding_count": 8,
            "mainline_rebase_count": 16,
            "joint_package_materialized_count": 0,
            "benchmark_launch_authorized_count": 0,
        },
        "manifest_payload_sha256": payload_sha256(rows),
    }


__all__ = [
    "DISPOSITIONS",
    "ENTROPY",
    "MARKDOWN",
    "SCOPE",
    "SEARCH",
    "build_markdown_publication_manifest",
    "build_markdown_publication_order",
    "validate_work_order",
]
