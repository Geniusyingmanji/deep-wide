"""Outcome-independent parent map for the V2.42.11 entropy component.

Every V2.42.00 decision that selects ``entropy_credit_controller`` has one
semantic parent.  The parent is derived from the already frozen Markdown,
scope, and search publication manifests.  This module does not inspect live
quality outcomes, files, benchmark content, predictions, or evaluator data.

The map is deliberately explicit about search exclusion: a decision without
the selected search component can never inherit search bytes.  A decision with
search selected must bind the V2.42.10 publication and cannot fall back to its
pre-search parent.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from deepwide_agent.v24200_successor import payload_sha256
from deepwide_agent.v24204_postdecision_work_order import build_work_order_manifest
from deepwide_agent.v24206_markdown_publisher import (
    ENTROPY,
    MARKDOWN,
    SCOPE,
    SEARCH,
    build_markdown_publication_manifest,
    validate_work_order,
)
from deepwide_agent.v24207_scope_alias_publisher import (
    build_scope_publication_manifest,
)
from deepwide_agent.v24210_search_publisher import (
    build_search_publication_manifest,
)


MODEL_PATH = "results/v24123_entropy_action_response_model_v1_20260728.json"
GATE2A_STATE_PATH = (
    "outputs/v24193_replicate_aware_gate2a_consumer_state_v1_20260731.json"
)
GATE2A_REPORT_PATH = (
    "results/v24193_replicate_aware_true_continuation_gate2a_report_v1_20260731.json"
)
KERNEL_PATH = "src/deepwide_agent/v24211_entropy_controller.py"

PUBLICATION_PATHS = {
    "baseline": None,
    "markdown": "results/v24206_selected_markdown_component_publication_v1_20260731.json",
    "scope": "results/v24207_selected_scope_alias_component_publication_v1_20260731.json",
    "search": "results/v24210_selected_search_component_publication_v1_20260731.json",
}

# Identical parent byte graphs intentionally share one target schema.  The
# source graphs are the seven non-search parents (68/69/70/76/77/78/79) and
# the seven V2.42.10 search outputs (80--86).
TARGET_SCHEMA_BY_PARENT_SCHEMA = {
    source: target
    for source, target in zip(
        (68, 69, 70, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86),
        range(87, 101),
        strict=True,
    )
}


def _parent_without_search(
    work_order: Mapping[str, Any],
    markdown: Mapping[str, Any],
    scope: Mapping[str, Any],
) -> dict[str, Any]:
    components = list(work_order["eligible_components"])
    if SEARCH in components:
        raise RuntimeError("V2.42.11 non-search parent received search")
    if SCOPE in components:
        if MARKDOWN not in components:
            raise RuntimeError("V2.42.11 scope parent lacks Markdown")
        owner = "scope"
        source_schema = scope["target_state_schema_version"]
        variant = "selected_scope_candidate"
    elif MARKDOWN in components:
        owner = "markdown"
        source_schema = markdown["target_state_schema_version"]
        variant = "selected_markdown_candidate"
    else:
        owner = "baseline"
        source_schema = work_order["baseline_publication"]["state_schema_version"]
        variant = "selected_baseline"
    if not isinstance(source_schema, int):
        raise RuntimeError("V2.42.11 non-search parent schema is absent")
    return {
        "parent_owner": owner,
        "semantic_parent_variant": variant,
        "source_state_schema_version": source_schema,
        "required_parent_publication_path": PUBLICATION_PATHS[owner],
        "search_bytes_required": False,
        "search_bytes_forbidden": True,
        "silent_presearch_fallback_allowed": False,
    }


def build_entropy_integration_order(work_order: Mapping[str, Any]) -> dict[str, Any]:
    """Derive the exact parent/model/gate bindings for one entropy decision."""

    selected = validate_work_order(work_order)
    components = list(selected["eligible_components"])
    if ENTROPY not in components:
        raise RuntimeError("V2.42.11 work order does not select entropy")
    decision = str(selected["decision_sha256"])
    markdown = build_markdown_publication_manifest()["rows"][decision]
    scope = build_scope_publication_manifest()["rows"][decision]
    search = build_search_publication_manifest()["rows"][decision]
    if (
        markdown["eligible_components"] != components
        or scope["eligible_components"] != components
        or search["eligible_components"] != components
    ):
        raise RuntimeError("V2.42.11 component manifest binding drifted")

    if SEARCH in components:
        if search.get("search_component_selected") is not True:
            raise RuntimeError("V2.42.11 selected search parent is inconsistent")
        source_schema = search.get("target_state_schema_version")
        parent = {
            "parent_owner": "search",
            "semantic_parent_variant": search["semantic_parent_variant"],
            "source_state_schema_version": source_schema,
            "required_parent_publication_path": PUBLICATION_PATHS["search"],
            "search_bytes_required": True,
            "search_bytes_forbidden": False,
            "silent_presearch_fallback_allowed": False,
        }
    else:
        if search.get("search_component_selected") is not False:
            raise RuntimeError("V2.42.11 absent search component is inconsistent")
        parent = _parent_without_search(selected, markdown, scope)
        source_schema = parent["source_state_schema_version"]

    if source_schema not in TARGET_SCHEMA_BY_PARENT_SCHEMA:
        raise RuntimeError("V2.42.11 parent byte graph is unregistered")
    value: dict[str, Any] = {
        "decision_sha256": decision,
        "baseline_name": selected["baseline_name"],
        "baseline_publication": dict(selected["baseline_publication"]),
        "eligible_components": components,
        **parent,
        "parent_graph_id": f"schema{source_schema}",
        "target_state_schema_version": TARGET_SCHEMA_BY_PARENT_SCHEMA[source_schema],
        "controller_kernel_path": KERNEL_PATH,
        "required_action_model_path": MODEL_PATH,
        "required_gate2a_state_path": GATE2A_STATE_PATH,
        "required_gate2a_report_path": GATE2A_REPORT_PATH,
        "required_gate2a_status": "replicate_aware_gate2a_pass",
        "required_gate2a_controller_design_allowed": True,
        "model_sha256_must_bind_publication": True,
        "job_manifest_sha256_must_bind_model_and_publication": True,
        "real_state_transition_adapters_required": True,
        "projection_only_action_arm_allowed": False,
        "controller_candidate_bytes_built_or_materialized": False,
        "package_gate_evaluated_or_launched": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    value["integration_order_payload_sha256"] = payload_sha256(value)
    return value


def build_entropy_feasibility_manifest() -> dict[str, Any]:
    """Predeclare all 18 entropy-containing decision mappings."""

    work_orders = build_work_order_manifest()["rows"]
    entropy_orders = {
        decision: build_entropy_integration_order(work_orders[decision])
        for decision in sorted(work_orders)
        if ENTROPY in work_orders[decision]["eligible_components"]
    }
    if len(entropy_orders) != 18:
        raise RuntimeError("V2.42.11 expected 18 entropy decisions")

    parent_counts = Counter(row["parent_owner"] for row in entropy_orders.values())
    graph_counts = Counter(row["parent_graph_id"] for row in entropy_orders.values())
    baseline_counts = Counter(row["baseline_name"] for row in entropy_orders.values())
    search_required = sum(row["search_bytes_required"] for row in entropy_orders.values())
    search_forbidden = sum(row["search_bytes_forbidden"] for row in entropy_orders.values())
    if (
        dict(sorted(baseline_counts.items()))
        != {"p12": 6, "schema76": 6, "schema77": 6}
        or dict(sorted(parent_counts.items()))
        != {"baseline": 3, "markdown": 3, "scope": 3, "search": 9}
        or len(graph_counts) != 14
        or search_required != 9
        or search_forbidden != 9
        or set(graph_counts)
        != {f"schema{source}" for source in TARGET_SCHEMA_BY_PARENT_SCHEMA}
    ):
        raise RuntimeError("V2.42.11 parent coverage drifted")
    return {
        "rows": entropy_orders,
        "summary": {
            "decision_count": len(entropy_orders),
            "baseline_counts": dict(sorted(baseline_counts.items())),
            "parent_owner_counts": dict(sorted(parent_counts.items())),
            "unique_parent_byte_graph_count": len(graph_counts),
            "parent_graph_counts": dict(sorted(graph_counts.items())),
            "search_bytes_required_count": search_required,
            "search_bytes_forbidden_count": search_forbidden,
            "target_state_schema_versions": sorted(
                {row["target_state_schema_version"] for row in entropy_orders.values()}
            ),
            "controller_candidate_materialized_count": 0,
            "benchmark_launch_authorized_count": 0,
        },
        "manifest_payload_sha256": payload_sha256(entropy_orders),
    }


__all__ = [
    "GATE2A_REPORT_PATH",
    "GATE2A_STATE_PATH",
    "KERNEL_PATH",
    "MODEL_PATH",
    "PUBLICATION_PATHS",
    "TARGET_SCHEMA_BY_PARENT_SCHEMA",
    "build_entropy_feasibility_manifest",
    "build_entropy_integration_order",
]
