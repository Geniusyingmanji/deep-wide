"""Pure post-decision work orders for the frozen V2.42.00 successor.

The module maps every predeclared content-free successor decision to either a
byte-exact baseline identity handoff or a blocked integration work order.  It
does not read files, status, benchmark content, predictions, evaluator data,
credentials, or services.  A work order is not an implementation publication,
package gate, all-220 freeze, or benchmark authorization.
"""

from __future__ import annotations

from typing import Any, Mapping

from deepwide_agent.v24200_successor import (
    BASELINES,
    PACKAGE_GATE_CONTRACT,
    build_decision_manifest,
    payload_sha256,
)
from deepwide_agent.v24203_materialization_audit import (
    COMPONENT_ORDER,
    build_materialization_manifest,
    reject_forbidden_metadata,
)


COMPONENT_WORK = {
    "search_yield_shared_query": {
        "authority_now": "future_go_permits_design_build_only_integration",
        "selected_baseline_bound_publication_available": False,
        "implementation_publication_required": True,
        "implementation_publisher_authorized_by_this_work_order": False,
    },
    "markdown_rank_slot": {
        "authority_now": "historical_schema69_build_only_publication",
        "selected_baseline_bound_publication_available": False,
        "selected_baseline_rebase_publication_required": True,
        "implementation_publisher_authorized_by_this_work_order": False,
    },
    "markdown_branch_scope_open_fallback": {
        "authority_now": "historical_schema70_build_only_publication",
        "selected_baseline_bound_publication_available": False,
        "namespaced_scope_rebase_publication_required": True,
        "implementation_publisher_authorized_by_this_work_order": False,
    },
    "entropy_credit_controller": {
        "authority_now": "controller_design_only_after_future_go",
        "controller_implementation_authority_available": False,
        "selected_baseline_bound_publication_available": False,
        "separate_implementation_authority_required": True,
        "implementation_publisher_authorized_by_this_work_order": False,
    },
}


def _expected_decision(decision_sha256: str, row: Mapping[str, Any]) -> dict[str, Any]:
    baseline_name = str(row["baseline_name"])
    components = list(row["eligible_components"])
    integrated = bool(components)
    value: dict[str, Any] = {
        "baseline_name": baseline_name,
        "baseline_publication": BASELINES[baseline_name],
        "mainline_scope": row["mainline_scope"],
        "markdown_branch_scope": row["markdown_branch_scope"],
        "eligible_components": components,
        "component_go_authority": "deterministic_build_and_package_gate_only",
        "integrated_package_namespace": "results/v24200_integrated_packages",
        "integrated_package_required": integrated,
        "package_gate_contract": PACKAGE_GATE_CONTRACT,
        "package_gate_required_before_all220_freeze": integrated,
        "empty_component_set_uses_selected_baseline_identity_handoff": not integrated,
        "identity_handoff_still_requires_separate_all220_freeze_and_executor": True,
        "all220_freeze_or_launch_allowed": False,
        "v24199_diagnostic_only_not_execution_authority": True,
        "mapping_gold_category_question_type_evaluator_score_read": False,
    }
    if payload_sha256(value) != decision_sha256:
        raise RuntimeError("V2.42.04 registered decision digest is inconsistent")
    value["decision_payload_sha256"] = decision_sha256
    return value


def validate_terminal_decision(decision: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one V2.42.00 terminal decision without retaining guard fields."""

    if not isinstance(decision, Mapping):
        raise RuntimeError("V2.42.04 decision is not an object")
    privileged_guard = decision.get(
        "mapping_gold_category_question_type_evaluator_score_read"
    )
    if privileged_guard is not False:
        raise RuntimeError("V2.42.04 privileged-read guard drifted")
    projected = {
        key: item
        for key, item in decision.items()
        if key != "mapping_gold_category_question_type_evaluator_score_read"
    }
    reject_forbidden_metadata(projected)
    digest = projected.get("decision_payload_sha256")
    manifest = build_decision_manifest()
    if not isinstance(digest, str) or digest not in manifest:
        raise RuntimeError("V2.42.04 decision is not in the frozen manifest")
    expected = _expected_decision(digest, manifest[digest])
    if dict(decision) != expected:
        raise RuntimeError("V2.42.04 terminal decision bytes drifted")
    return {
        "decision_sha256": digest,
        "baseline_name": expected["baseline_name"],
        "baseline_publication": dict(expected["baseline_publication"]),
        "mainline_scope": expected["mainline_scope"],
        "markdown_branch_scope": expected["markdown_branch_scope"],
        "eligible_components": list(expected["eligible_components"]),
    }


def build_work_order(
    decision_sha256: str,
    decision_row: Mapping[str, Any],
    materialization_row: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one non-executing work order from registered content-free rows."""

    reject_forbidden_metadata(decision_row)
    reject_forbidden_metadata(materialization_row)
    if materialization_row.get("decision_sha256") != decision_sha256:
        raise RuntimeError("V2.42.04 materialization decision binding drifted")
    if materialization_row.get("baseline_name") != decision_row.get("baseline_name"):
        raise RuntimeError("V2.42.04 materialization baseline binding drifted")
    components = list(decision_row.get("eligible_components") or [])
    if components != [name for name in COMPONENT_ORDER if name in components]:
        raise RuntimeError("V2.42.04 component order drifted")
    if materialization_row.get("eligible_components") != components:
        raise RuntimeError("V2.42.04 component binding drifted")

    identity = not components
    value: dict[str, Any] = {
        "decision_sha256": decision_sha256,
        "baseline_name": decision_row["baseline_name"],
        "baseline_publication": dict(BASELINES[str(decision_row["baseline_name"])]),
        "eligible_components": components,
        "disposition": (
            "byte_exact_baseline_identity_handoff_ready"
            if identity
            else "blocked_pending_selected_baseline_publications_and_joint_audit"
        ),
        "identity_handoff_only": identity,
        "baseline_bytes_byte_exact_available": True,
        "integrated_package_bytes_available": identity,
        "component_work": {
            name: dict(COMPONENT_WORK[name]) for name in components
        },
        "blockers": list(materialization_row.get("blockers") or []),
        "joint_conflict_audit_and_regression_required": bool(components),
        "package_gate_required": bool(components),
        "package_gate_contract": PACKAGE_GATE_CONTRACT,
        "silent_component_drop_or_baseline_fallback_allowed": False,
        "candidate_code_built_merged_or_materialized": False,
        "package_gate_evaluated_or_launched": False,
        "shared_api_lease_acquired": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    if identity and value["blockers"]:
        raise RuntimeError("V2.42.04 identity handoff unexpectedly has blockers")
    if not identity and (
        not value["blockers"]
        or "postdecision_joint_conflict_audit_and_regression_absent"
        not in value["blockers"]
    ):
        raise RuntimeError("V2.42.04 nonempty work order lacks joint blocker")
    value["work_order_payload_sha256"] = payload_sha256(value)
    return value


def build_work_order_manifest() -> dict[str, Any]:
    """Predeclare all 36 work orders before any terminal quality outcome."""

    decisions = build_decision_manifest()
    materialization = build_materialization_manifest(decisions)
    rows = {
        digest: build_work_order(
            digest,
            decisions[digest],
            materialization["rows"][digest],
        )
        for digest in sorted(decisions)
    }
    identity_count = sum(row["identity_handoff_only"] for row in rows.values())
    blocked_count = sum(not row["integrated_package_bytes_available"] for row in rows.values())
    if len(rows) != 36 or identity_count != 3 or blocked_count != 33:
        raise RuntimeError("V2.42.04 work-order coverage is inconsistent")
    return {
        "rows": rows,
        "summary": {
            "decision_count": len(rows),
            "identity_handoff_ready_count": identity_count,
            "blocked_nonempty_work_order_count": blocked_count,
            "candidate_package_materialized_count": 0,
            "benchmark_launch_authorized_count": 0,
        },
        "manifest_payload_sha256": payload_sha256(rows),
    }


def select_work_order(decision: Mapping[str, Any]) -> dict[str, Any]:
    """Select the predeclared work order for one validated terminal decision."""

    safe = validate_terminal_decision(decision)
    manifest = build_work_order_manifest()
    selected = dict(manifest["rows"][safe["decision_sha256"]])
    if (
        selected["baseline_name"] != safe["baseline_name"]
        or selected["eligible_components"] != safe["eligible_components"]
        or selected["baseline_publication"] != safe["baseline_publication"]
    ):
        raise RuntimeError("V2.42.04 selected work-order binding drifted")
    return selected


__all__ = [
    "COMPONENT_WORK",
    "build_work_order",
    "build_work_order_manifest",
    "select_work_order",
    "validate_terminal_decision",
]
