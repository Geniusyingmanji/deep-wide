"""Pure classification for post-decision Markdown rebase feasibility.

This module classifies the 36 frozen V2.42.00 decisions from content-free
component names and audited hook facts.  It does not read files, build or
materialize candidates, call services, evaluate a package, or authorize a
benchmark.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from deepwide_agent.v24200_successor import BASELINES, build_decision_manifest
from deepwide_agent.v24203_materialization_audit import reject_forbidden_metadata


MARKDOWN = "markdown_rank_slot"
MARKDOWN_SCOPE = "markdown_branch_scope_open_fallback"
SEARCH = "search_yield_shared_query"
ENTROPY = "entropy_credit_controller"

DISPOSITIONS = (
    "byte_exact_baseline_identity_handoff_ready",
    "p12_historical_byte_exact_postdecision_binding_required",
    "mainline_markdown_rebase_hook_compatible_publication_required",
    "mainline_markdown_rebase_plus_scope_namespace_alias_required",
    "blocked_by_search_or_entropy_implementation_authority",
)


def classify_markdown_rebase_decision(
    decision_sha256: str,
    decision: Mapping[str, Any],
) -> dict[str, Any]:
    """Classify one registered decision using only component names."""

    reject_forbidden_metadata(decision)
    manifest = build_decision_manifest()
    if decision_sha256 not in manifest or dict(decision) != manifest[decision_sha256]:
        raise RuntimeError("V2.42.05 decision is not the frozen manifest row")
    baseline = str(decision["baseline_name"])
    components = list(decision["eligible_components"])
    if not components:
        disposition = "byte_exact_baseline_identity_handoff_ready"
        feasibility = "ready_identity_only"
        future_artifacts: list[str] = []
    elif SEARCH in components or ENTROPY in components:
        disposition = "blocked_by_search_or_entropy_implementation_authority"
        feasibility = "blocked_before_markdown_package_publication"
        future_artifacts = []
        if SEARCH in components:
            future_artifacts.append(
                "search_yield_selected_baseline_implementation_publication"
            )
        if ENTROPY in components:
            future_artifacts.extend(
                [
                    "entropy_controller_separate_implementation_authorization",
                    "entropy_controller_selected_baseline_publication",
                ]
            )
    elif baseline == "p12":
        disposition = "p12_historical_byte_exact_postdecision_binding_required"
        feasibility = "historical_bytes_available_not_selected_package_publication"
        future_artifacts = [
            (
                "schema70_postdecision_selected_package_binding"
                if MARKDOWN_SCOPE in components
                else "schema69_postdecision_selected_package_binding"
            )
        ]
    elif MARKDOWN_SCOPE in components:
        disposition = "mainline_markdown_rebase_plus_scope_namespace_alias_required"
        feasibility = "production_hooks_compatible_namespace_semantics_unpublished"
        future_artifacts = [
            "selected_baseline_markdown_rebase_publication",
            "mainline_scope_to_markdown_branch_scope_namespace_alias_attestation",
            "joint_conflict_and_behavior_regression_receipt",
        ]
    else:
        disposition = "mainline_markdown_rebase_hook_compatible_publication_required"
        feasibility = "production_hooks_compatible_tests_and_publication_absent"
        future_artifacts = [
            "selected_baseline_markdown_rebase_publication",
            "joint_conflict_and_behavior_regression_receipt",
        ]
    if disposition not in DISPOSITIONS:
        raise RuntimeError("V2.42.05 disposition is unregistered")
    return {
        "decision_sha256": decision_sha256,
        "baseline_name": baseline,
        "baseline_publication": dict(BASELINES[baseline]),
        "eligible_components": components,
        "disposition": disposition,
        "feasibility": feasibility,
        "future_artifacts_required": future_artifacts,
        "candidate_bytes_built_or_materialized": False,
        "selected_package_publication_available": False,
        "component_implementation_authority_granted": False,
        "package_gate_evaluated_or_launched": False,
        "benchmark_forward_or_full220_launch_allowed": False,
    }


def build_markdown_rebase_manifest() -> dict[str, Any]:
    """Classify all frozen decisions before any terminal outcome."""

    decisions = build_decision_manifest()
    rows = {
        digest: classify_markdown_rebase_decision(digest, decisions[digest])
        for digest in sorted(decisions)
    }
    counts = Counter(row["disposition"] for row in rows.values())
    expected = {
        "byte_exact_baseline_identity_handoff_ready": 3,
        "p12_historical_byte_exact_postdecision_binding_required": 2,
        "mainline_markdown_rebase_hook_compatible_publication_required": 2,
        "mainline_markdown_rebase_plus_scope_namespace_alias_required": 2,
        "blocked_by_search_or_entropy_implementation_authority": 27,
    }
    if dict(sorted(counts.items())) != dict(sorted(expected.items())):
        raise RuntimeError("V2.42.05 decision coverage is inconsistent")
    return {
        "rows": rows,
        "summary": {
            "decision_count": len(rows),
            "disposition_counts": dict(sorted(counts.items())),
            "identity_ready_count": 3,
            "historical_p12_binding_required_count": 2,
            "mainline_markdown_hook_compatible_count": 4,
            "scope_namespace_alias_required_count": 2,
            "search_or_entropy_authority_blocked_count": 27,
            "selected_package_publication_count": 0,
            "benchmark_launch_authorized_count": 0,
        },
    }


__all__ = [
    "DISPOSITIONS",
    "build_markdown_rebase_manifest",
    "classify_markdown_rebase_decision",
]
