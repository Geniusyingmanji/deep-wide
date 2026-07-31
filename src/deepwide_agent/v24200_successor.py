"""Label-blind successor selection for the post-V2.41.99 quality chain.

V2.41.99 represented every downstream GO as an independent feature bit.  That
is not a valid inheritance rule: schema 76 is itself a P12-paired candidate,
schema 77 is only paired against schema 76, and the scope mechanism already in
schema 76 is different from the optional Markdown-branch scope mechanism.

This module contains the outcome-independent V2.42.00 decision rule.  It only
classifies registered status envelopes.  It does not build code, read metrics,
acquire a lease, call a service, evaluate a package, freeze an all-220 run, or
launch a benchmark.
"""

from __future__ import annotations

import hashlib
import json
from itertools import product
from typing import Any, Mapping


P12_PUBLICATION = {
    "path": "results/v2410_rank_slot_candidate_publication_v4_20260727.json",
    "sha256": "e7dee0a2f8b8b2ed55e318aeed1c383bcc7fdfbae226dd8732c1d2eb5a2c1675",
    "pipeline_branch": "p12",
    "state_schema_version": 68,
    "mainline_scope": False,
}
SCHEMA76_PUBLICATION = {
    "path": "results/v24154_scope_combined_execution_candidate_publication_v1_20260729.json",
    "sha256": "0cd2c47af0f4dfbb3cc0f2b3fdc80182a48037e5936bd0a41082a8f63c2f29f1",
    "pipeline_branch": "schema76",
    "state_schema_version": 76,
    "mainline_scope": True,
}
SCHEMA77_PUBLICATION = {
    "path": "results/v24175_predicate_completion_execution_candidate_publication_v1_20260730.json",
    "sha256": "139780e26566ac8d0fbd3328dafad05652552048e99330d39bb00bf8f7d77e5e",
    "pipeline_branch": "schema77",
    "state_schema_version": 77,
    "mainline_scope": True,
}
BASELINES = {
    "p12": P12_PUBLICATION,
    "schema76": SCHEMA76_PUBLICATION,
    "schema77": SCHEMA77_PUBLICATION,
}

SOURCE_ORDER = (
    "schema76",
    "schema77",
    "search_yield",
    "markdown",
    "markdown_branch_scope",
    "entropy_credit",
)
COMPONENT_ORDER = (
    "search_yield_shared_query",
    "markdown_rank_slot",
    "markdown_branch_scope_open_fallback",
    "entropy_credit_controller",
)

SOURCE_SPECS: dict[str, dict[str, Any]] = {
    "schema76": {
        "role": "v24154_scope_combined_fasttrack_watcher_state",
        "protocol_kind": "protocol_sha256",
        "protocol_sha256": "8e1a15ce3e5342538e57d136c170031e2d0d34e268d5761b9de8d55c91b12f80",
        "go": ("complete_exact220_released",),
        "no_go": ("complete_paired_dev_no_go",),
        "false_fields": (
            "forward_resume_used",
            "selective_rerun_used",
            "leaderboard_or_sota_claim",
        ),
    },
    "schema77": {
        "role": "v24176_predicate_completion_paired_dev_watcher_state",
        "protocol_kind": "protocol_sha256",
        "protocol_sha256": "8c1c3c4d9f7ed8604258fa301ea931a6425cf6c189c5e1c30c0ee387eddd1f1e",
        "go": ("complete_paired_dev_go",),
        "no_go": ("complete_paired_dev_no_go",),
        "false_fields": (
            "forward_resume_used",
            "selective_rerun_used",
            "test156_or_full220_launch_allowed",
            "test156_or_full220_api_called",
            "leaderboard_submission_or_sota_claim",
        ),
    },
    "search_yield": {
        "role": "v24180_predicate_search_yield_watcher_state",
        "protocol_kind": "protocol_sha256",
        "protocol_sha256": "1274fe4a9b7801d96dd5265443cb3f6b837edd469be3fe85bef1c3d71ebdf5e4",
        "go": ("complete_search_yield_go",),
        "no_go": (
            "complete_search_yield_no_go",
            "terminal_incomplete_attempt_no_rerun",
        ),
        "false_fields": (
            "benchmark_forward_called",
            "resume_or_selective_rerun_used",
            "leaderboard_submission_or_sota_claim",
        ),
    },
    "markdown": {
        "role": "v24103_markdown_paired_dev_watcher_state",
        "protocol_kind": "protocol_sha256",
        "protocol_sha256": "47be69831bc7b20a8ad6827bab67a14d599542fb57baf97b3e8a042862c4a9f0",
        "go": ("complete_paired_dev_go",),
        "no_go": ("complete_paired_dev_no_go",),
        "false_fields": (
            "test156_or_full220_launch_allowed",
            "test156_or_full220_api_called",
            "leaderboard_submission_or_sota_claim",
        ),
    },
    "markdown_branch_scope": {
        "role": "v24105_scope_open_paired_dev_watcher_state",
        "protocol_kind": "protocol_sha256",
        "protocol_sha256": "a435bf2fb3ea08fa16feece631b35b51139c0134a965605987bc4e854ea3d6e9",
        "go": ("complete_paired_dev_go",),
        "no_go": (
            "complete_paired_dev_no_go",
            "complete_parent_v24103_no_go_no_p12_3_api",
        ),
        "false_fields": (
            "test156_or_full220_launch_allowed",
            "test156_or_full220_api_called",
            "leaderboard_submission_or_sota_claim",
        ),
    },
    "entropy_credit": {
        "role": "v24193_replicate_aware_gate2a_consumer_state",
        "protocol_kind": "protocol_object",
        "protocol_path": "results/v24193_replicate_aware_gate2a_consumer_preregistration_v1_20260731.json",
        "protocol_sha256": "9b2fcf677bbb4f7cdb361d689f2634b23326d1cb640416eee920fb2b131b6031",
        "go": ("replicate_aware_gate2a_pass",),
        "no_go": (
            "replicate_aware_gate2a_fail",
            "replicate_aware_gate2a_not_evaluable",
        ),
        "false_fields": (
            "controller_implementation_or_pilot_launch_allowed",
            "training_credit_allowed",
            "full220_controller_launch_allowed",
        ),
    },
}

ENTROPY_ROOT_SPEC = {
    "role": "v24190_tie_aware_gate2a_consumer_state",
    "protocol_path": "results/v24190_tie_aware_gate2a_consumer_preregistration_v1_20260730.json",
    "protocol_sha256": "e978988b6a7617bba702ced578cf1eb47fc0392a32fc7298ae136add922927ac",
    "terminal_no_report_sources": (
        "gate1_no_go_true_continuation_not_launched",
        "capture_attempt_failed_no_api_reissue",
        "fit_calibration_model_support_no_go",
    ),
}

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
        "score",
        "scores",
        "split",
        "task_category",
        "url",
        "urls",
    }
)

PACKAGE_GATE_CONTRACT = {
    "gate_id": "v24200_integrated_package_vs_selected_baseline_same_dev64_v1",
    "selection_frozen_before_package_build": True,
    "candidate_cold_start_required": True,
    "same_opaque_dev64_ids_required": True,
    "same_model_search_prompt_budget_threshold_required": True,
    "candidate_and_baseline_evaluator_contract_identical": True,
    "all_64_outcomes_required": True,
    "forward_failure_scored_as_zero": True,
    "resume_or_selective_rerun_allowed": False,
    "completion_non_decrease_required": True,
    "whole_table_non_decrease_required": True,
    "each_quality_component_min_delta": -0.005,
    "candidate_token_ratio_max": 1.05,
    "strict_component_activation_required_when_nonempty": True,
    "minimum_material_improvement_any": {
        "completion_count_delta": 1,
        "whole_table_count_delta": 1,
        "quality_composite_delta": 0.001,
    },
    "go_authorizes_only_new_all220_freeze": True,
    "benchmark_launch_allowed": False,
    "leaderboard_submission_or_sota_claim": False,
}


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def reject_forbidden_metadata(value: object) -> None:
    """Reject evaluator-only keys recursively before status classification."""

    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).casefold() in FORBIDDEN_KEYS:
                raise RuntimeError("V2.42.00 evaluator-only metadata appeared")
            reject_forbidden_metadata(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            reject_forbidden_metadata(item)


def _binding_is_valid(value: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    if spec["protocol_kind"] == "protocol_sha256":
        return value.get("protocol_sha256") == spec["protocol_sha256"]
    protocol = value.get("protocol")
    return (
        isinstance(protocol, Mapping)
        and protocol.get("path") == spec["protocol_path"]
        and protocol.get("sha256") == spec["protocol_sha256"]
    )


def classify_source(name: str, value: Mapping[str, Any]) -> str:
    """Classify one immutable status envelope as waiting, go, or no_go."""

    if name not in SOURCE_SPECS:
        raise RuntimeError("V2.42.00 source is not registered")
    reject_forbidden_metadata(value)
    spec = SOURCE_SPECS[name]
    if value.get("role") != spec["role"] or not _binding_is_valid(value, spec):
        raise RuntimeError(f"V2.42.00 {name} envelope binding drifted")
    for field in spec["false_fields"]:
        if value.get(field) is not False:
            raise RuntimeError(f"V2.42.00 {name} authorization drifted: {field}")
    status = value.get("status")
    if not isinstance(status, str) or not status:
        raise RuntimeError(f"V2.42.00 {name} status is absent")
    if status in spec["go"]:
        if name == "entropy_credit" and (
            value.get("terminal") is not True
            or value.get("replicate_aware_gate2a_evaluated") is not True
            or value.get("replicate_aware_gate2a_passed") is not True
            or value.get("controller_design_allowed") is not True
        ):
            raise RuntimeError("V2.42.00 entropy GO envelope is invalid")
        return "go"
    if status in spec["no_go"]:
        if name == "entropy_credit" and (
            value.get("terminal") is not True
            or value.get("replicate_aware_gate2a_evaluated") is not True
            or value.get("replicate_aware_gate2a_passed") is not False
        ):
            raise RuntimeError("V2.42.00 entropy NO-GO envelope is invalid")
        return "no_go"
    if status.startswith("complete") or status.startswith("terminal"):
        raise RuntimeError(f"V2.42.00 {name} terminal status is unregistered")
    return "waiting"


def classify_entropy_chain(
    final_value: Mapping[str, Any], root_value: Mapping[str, Any]
) -> str:
    """Close registered early-terminal entropy paths without reading a report."""

    reject_forbidden_metadata(root_value)
    protocol = root_value.get("protocol")
    if (
        root_value.get("role") != ENTROPY_ROOT_SPEC["role"]
        or not isinstance(protocol, Mapping)
        or protocol.get("path") != ENTROPY_ROOT_SPEC["protocol_path"]
        or protocol.get("sha256") != ENTROPY_ROOT_SPEC["protocol_sha256"]
    ):
        raise RuntimeError("V2.42.00 entropy-root binding drifted")
    if root_value.get("terminal") is not True:
        return classify_source("entropy_credit", final_value)
    if root_value.get("tie_aware_gate2a_evaluated") is True:
        return classify_source("entropy_credit", final_value)
    if (
        root_value.get("status") == "waiting_for_true_continuation_audit_terminal"
        and root_value.get("source_terminal") is True
        and root_value.get("source_status")
        in ENTROPY_ROOT_SPEC["terminal_no_report_sources"]
        and root_value.get("tie_aware_gate2a_passed") is False
        and root_value.get("controller_design_allowed") is False
    ):
        return "no_go"
    raise RuntimeError("V2.42.00 entropy-root terminal status is unregistered")


def select_hierarchical_baseline(statuses: Mapping[str, str]) -> str | None:
    """Select P12/schema76/schema77 using only their registered paired gates."""

    for name in ("schema76", "schema77"):
        if statuses.get(name) not in {"waiting", "go", "no_go"}:
            raise RuntimeError("V2.42.00 mainline status is invalid")
    if statuses["schema76"] == "waiting":
        return None
    if statuses["schema76"] == "no_go":
        # schema77 is only compared with schema76.  Even a local schema77 GO
        # cannot overrule schema76's loss to P12.
        return "p12"
    if statuses["schema77"] == "waiting":
        return None
    return "schema77" if statuses["schema77"] == "go" else "schema76"


def eligible_components(statuses: Mapping[str, str]) -> tuple[str, ...]:
    """Return build-only components; GO never means production authorization."""

    if statuses.get("markdown_branch_scope") == "go" and statuses.get("markdown") != "go":
        raise RuntimeError("V2.42.00 Markdown-branch scope lacks Markdown GO")
    enabled = (
        ("search_yield_shared_query", statuses.get("search_yield") == "go"),
        ("markdown_rank_slot", statuses.get("markdown") == "go"),
        (
            "markdown_branch_scope_open_fallback",
            statuses.get("markdown_branch_scope") == "go",
        ),
        ("entropy_credit_controller", statuses.get("entropy_credit") == "go"),
    )
    return tuple(name for name, use in enabled if use)


def decision_from_statuses(statuses: Mapping[str, str]) -> dict[str, Any] | None:
    """Build the unique successor decision after every quality gate is terminal."""

    if set(statuses) != set(SOURCE_ORDER):
        raise RuntimeError("V2.42.00 status source set drifted")
    if any(value == "waiting" for value in statuses.values()):
        return None
    if any(value not in {"go", "no_go"} for value in statuses.values()):
        raise RuntimeError("V2.42.00 status classification is invalid")
    baseline_name = select_hierarchical_baseline(statuses)
    if baseline_name is None:
        raise RuntimeError("V2.42.00 terminal vector lacks a baseline")
    components = eligible_components(statuses)
    baseline = BASELINES[baseline_name]
    decision: dict[str, Any] = {
        "baseline_name": baseline_name,
        "baseline_publication": baseline,
        "mainline_scope": baseline["mainline_scope"],
        "markdown_branch_scope": "markdown_branch_scope_open_fallback" in components,
        "eligible_components": list(components),
        "component_go_authority": "deterministic_build_and_package_gate_only",
        "integrated_package_namespace": "results/v24200_integrated_packages",
        "package_gate_contract": PACKAGE_GATE_CONTRACT,
        "package_gate_required_before_all220_freeze": True,
        "all220_freeze_or_launch_allowed": False,
        "v24199_diagnostic_only_not_execution_authority": True,
        "mapping_gold_category_question_type_evaluator_score_read": False,
    }
    decision["decision_payload_sha256"] = payload_sha256(decision)
    return decision


def derive_successor_decision(
    states: Mapping[str, Mapping[str, Any]],
    *,
    entropy_root: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, str]]:
    """Classify bound envelopes and return the terminal decision, if available."""

    if set(states) != set(SOURCE_ORDER):
        raise RuntimeError("V2.42.00 source envelope set drifted")
    statuses = {
        name: classify_source(name, states[name])
        for name in SOURCE_ORDER
        if name != "entropy_credit"
    }
    statuses["entropy_credit"] = classify_entropy_chain(
        states["entropy_credit"], entropy_root
    )
    # Check this relationship even while unrelated sources are still waiting.
    eligible_components(statuses)
    return decision_from_statuses(statuses), statuses


def build_decision_manifest() -> dict[str, Any]:
    """Enumerate the 36 possible packages implied by the frozen decision rule."""

    decisions: dict[str, dict[str, Any]] = {}
    for schema76, schema77, search, markdown_level, entropy in product(
        ("go", "no_go"),
        ("go", "no_go"),
        ("go", "no_go"),
        ("none", "markdown", "markdown_scope"),
        ("go", "no_go"),
    ):
        statuses = {
            "schema76": schema76,
            "schema77": schema77,
            "search_yield": search,
            "markdown": "go" if markdown_level != "none" else "no_go",
            "markdown_branch_scope": (
                "go" if markdown_level == "markdown_scope" else "no_go"
            ),
            "entropy_credit": entropy,
        }
        decision = decision_from_statuses(statuses)
        assert decision is not None
        key = decision["decision_payload_sha256"]
        decisions[key] = {
            "baseline_name": decision["baseline_name"],
            "mainline_scope": decision["mainline_scope"],
            "markdown_branch_scope": decision["markdown_branch_scope"],
            "eligible_components": decision["eligible_components"],
        }
    if len(decisions) != 36:
        raise AssertionError("V2.42.00 decision manifest is not the expected 36 packages")
    return dict(sorted(decisions.items()))

