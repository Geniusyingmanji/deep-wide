"""Pure materialization audit for the frozen V2.42.00 successor manifest.

The V2.42.00 decision identifies a hierarchical baseline and quality-eligible
components.  Eligibility is not the same as executable bytes.  This module
classifies every predeclared decision without reading a live status envelope,
benchmark input, prediction, evaluator artifact, or score.

Only an empty-component decision has a byte-exact identity handoff available.
Every non-empty decision must wait for the missing, selected-baseline-bound
integration publication and its conflict/regression receipt.  In particular,
the entropy chain authorizes controller design only, not implementation.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Mapping


BASELINES = ("p12", "schema76", "schema77")
COMPONENT_ORDER = (
    "search_yield_shared_query",
    "markdown_rank_slot",
    "markdown_branch_scope_open_fallback",
    "entropy_credit_controller",
)

FORBIDDEN_KEYS = frozenset(
    {
        "answer",
        "answer_key",
        "answers",
        "category",
        "evidence",
        "evaluator",
        "gold",
        "ground_truth",
        "mapping",
        "prediction",
        "predictions",
        "question",
        "questions",
        "question_type",
        "reward",
        "score",
        "scores",
        "split",
        "task_category",
        "task_id",
        "url",
        "urls",
    }
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def reject_forbidden_metadata(value: object) -> None:
    """Reject evaluator-only or sample-level keys recursively."""

    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).casefold() in FORBIDDEN_KEYS:
                raise RuntimeError("V2.42.03 privileged metadata appeared")
            reject_forbidden_metadata(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            reject_forbidden_metadata(item)


def _component_blockers(baseline: str, component: str) -> tuple[str, ...]:
    if component == "search_yield_shared_query":
        return (
            "search_yield_selected_baseline_implementation_publication_absent",
        )
    if component == "markdown_rank_slot":
        return (
            "markdown_postdecision_package_publication_absent"
            if baseline == "p12"
            else "markdown_selected_baseline_rebase_publication_absent",
        )
    if component == "markdown_branch_scope_open_fallback":
        return (
            "markdown_scope_postdecision_package_publication_absent"
            if baseline == "p12"
            else "markdown_branch_scope_namespace_rebase_publication_absent",
        )
    if component == "entropy_credit_controller":
        return (
            "entropy_controller_implementation_authority_absent",
            "entropy_controller_selected_baseline_publication_absent",
        )
    raise RuntimeError("V2.42.03 component is unregistered")


def classify_decision(
    decision_sha256: str,
    decision: Mapping[str, Any],
) -> dict[str, Any]:
    """Classify one content-free V2.42.00 decision manifest row."""

    reject_forbidden_metadata(decision)
    if (
        not isinstance(decision_sha256, str)
        or len(decision_sha256) != 64
        or any(character not in "0123456789abcdef" for character in decision_sha256)
    ):
        raise RuntimeError("V2.42.03 decision key is not a SHA-256 digest")
    expected_fields = {
        "baseline_name",
        "mainline_scope",
        "markdown_branch_scope",
        "eligible_components",
    }
    if set(decision) != expected_fields:
        raise RuntimeError("V2.42.03 decision row schema drifted")
    baseline = decision.get("baseline_name")
    components = decision.get("eligible_components")
    if baseline not in BASELINES or not isinstance(components, list):
        raise RuntimeError("V2.42.03 decision baseline/components are invalid")
    if components != [name for name in COMPONENT_ORDER if name in components]:
        raise RuntimeError("V2.42.03 component order or uniqueness drifted")
    if any(name not in COMPONENT_ORDER for name in components):
        raise RuntimeError("V2.42.03 decision contains an unknown component")
    markdown_scope = "markdown_branch_scope_open_fallback" in components
    if markdown_scope and "markdown_rank_slot" not in components:
        raise RuntimeError("V2.42.03 branch scope lacks Markdown")
    if decision.get("markdown_branch_scope") is not markdown_scope:
        raise RuntimeError("V2.42.03 branch-scope flag drifted")
    if decision.get("mainline_scope") is not (baseline in {"schema76", "schema77"}):
        raise RuntimeError("V2.42.03 mainline-scope flag drifted")

    if not components:
        blockers: list[str] = []
        materialization_class = "byte_exact_baseline_identity_handoff"
        frozen_package_bytes_available = True
    else:
        blockers = []
        for component in components:
            blockers.extend(_component_blockers(str(baseline), component))
        blockers.append("postdecision_joint_conflict_audit_and_regression_absent")
        materialization_class = "nonempty_package_not_materializable_from_frozen_bytes"
        frozen_package_bytes_available = False

    value: dict[str, Any] = {
        "decision_sha256": decision_sha256,
        "baseline_name": baseline,
        "eligible_components": list(components),
        "materialization_class": materialization_class,
        "baseline_bytes_byte_exact_available": True,
        "frozen_package_bytes_available": frozen_package_bytes_available,
        "identity_handoff_only": not components,
        "package_gate_required": bool(components),
        "blockers": blockers,
        "silent_component_drop_or_fallback_allowed": False,
        "benchmark_forward_or_full220_launch_allowed": False,
    }
    value["classification_payload_sha256"] = payload_sha256(value)
    return value


def build_materialization_manifest(
    decision_manifest: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Classify all 36 outcome-independent successor decisions."""

    reject_forbidden_metadata(decision_manifest)
    if len(decision_manifest) != 36:
        raise RuntimeError("V2.42.03 expected exactly 36 successor decisions")
    rows = {
        key: classify_decision(key, decision_manifest[key])
        for key in sorted(decision_manifest)
    }
    if set(rows) != set(decision_manifest):
        raise RuntimeError("V2.42.03 decision manifest coverage drifted")

    class_counts = Counter(row["materialization_class"] for row in rows.values())
    baseline_counts = Counter(row["baseline_name"] for row in rows.values())
    component_counts = Counter(
        component
        for row in rows.values()
        for component in row["eligible_components"]
    )
    blocker_counts = Counter(
        blocker for row in rows.values() for blocker in row["blockers"]
    )
    summary = {
        "decision_count": len(rows),
        "baseline_counts": dict(sorted(baseline_counts.items())),
        "materialization_class_counts": dict(sorted(class_counts.items())),
        "component_selection_counts": dict(sorted(component_counts.items())),
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "identity_handoff_decision_count": sum(
            row["identity_handoff_only"] for row in rows.values()
        ),
        "blocked_nonempty_package_decision_count": sum(
            not row["frozen_package_bytes_available"] for row in rows.values()
        ),
        "all_decisions_classified": True,
        "any_nonempty_package_materializable_now": any(
            row["eligible_components"] and row["frozen_package_bytes_available"]
            for row in rows.values()
        ),
    }
    if (
        summary["baseline_counts"] != {name: 12 for name in BASELINES}
        or summary["identity_handoff_decision_count"] != 3
        or summary["blocked_nonempty_package_decision_count"] != 33
        or summary["any_nonempty_package_materializable_now"] is not False
    ):
        raise RuntimeError("V2.42.03 materialization summary is inconsistent")
    return {
        "rows": rows,
        "summary": summary,
        "manifest_payload_sha256": payload_sha256(rows),
    }


__all__ = [
    "BASELINES",
    "COMPONENT_ORDER",
    "build_materialization_manifest",
    "classify_decision",
    "payload_sha256",
    "reject_forbidden_metadata",
]
