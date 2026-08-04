#!/usr/bin/env python3
"""Content-free diagnosis of the V2.44.88 support-conversion gate.

The frozen external result proves that execution-scoped validation memoization
removed the previously observed completion bottleneck: all eight workers and
all eight complete validations returned inside 109 seconds.  The same result
also shows a distinct mechanism failure.  Positive information gain was
observed, but no target crossed the unchanged source-count, posterior, and
support-margin gate, so decision credit correctly remained zero.

This report uses only sealed content-free aggregates.  It authorizes offline
design of one bounded entropy-conditioned targeted-support batch.  It does not
authorize another external population, dev64, exact-220, evaluator access,
threshold relaxation, training, or a leaderboard claim.
"""

from __future__ import annotations

import copy
import json
import os
import re
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import (  # noqa: E402
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from scripts import audit_v24398_failure_observability_build as base  # noqa: E402
from scripts import v24484_separated_budget_external_gate as previous_gate  # noqa: E402
from scripts import v24488_memoized_external_gate as gate  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


DATE = "20260804"
REPORT = Path(f"results/v24489_v24488_support_conversion_diagnosis_v1_{DATE}.json")
RESULT = gate.RESULT
DECISION = gate.DECISION
POSTAUDIT = gate.POSTAUDIT
PREVIOUS_RESULT = previous_gate.RESULT
DIAGNOSIS_SOURCE = Path(
    "scripts/diagnose_v24489_v24488_support_conversion.py"
)
TEST_SOURCE = Path(
    "tests/test_diagnose_v24489_v24488_support_conversion.py"
)
RUNTIME_SOURCES = (
    Path("src/deepwide_agent/v24457_adaptive_entropy_support.py"),
    Path("src/deepwide_agent/v24485_execution_scoped_validation_memo.py"),
    Path("src/deepwide_agent/v24486_memoized_worker_integration.py"),
    Path(gate.RUNNER_MARKER),
)
SOURCES = (*RUNTIME_SOURCES, DIAGNOSIS_SOURCE, TEST_SOURCE)
EXPECTED_WATCHERS = base.EXPECTED_WATCHERS
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(base._ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.44.89 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _validate_parents() -> tuple[dict[str, Any], dict[str, Any]]:
    result = gate.validate_public_result(_read(RESULT))
    decision = gate.validate_decision(ROOT, value=_read(DECISION))
    audit = gate.validate_postaudit(ROOT, value=_read(POSTAUDIT))
    previous = previous_gate.validate_public_result(_read(PREVIOUS_RESULT))
    mechanism = result.get("mechanism_aggregate") or {}
    observation = result.get("observation_aggregate") or {}
    timing = result.get("stage_timing_aggregate") or {}
    supervision = result.get("supervision_aggregate") or {}
    previous_supervision = previous.get("supervision_aggregate") or {}
    if (
        result.get("selected") != 8
        or result.get("batch_wall_seconds") != 108.366926
        or result.get("passed") is not False
        or result.get("mechanism_passed") is not False
        or result.get("reliability_passed") is not True
        or result.get("parent_validation_passed") is not True
        or result.get("latency_passed") is not True
        or result.get("diagnostic_complete") is not True
        or mechanism.get("passed_tasks") != 8
        or mechanism.get("failed_tasks") != 0
        or mechanism.get("stop_reason_counts")
        != {
            "budget_exhausted": 1,
            "pool_exhausted": 0,
            "safe_decision": 0,
            "support_unreachable": 7,
        }
        or mechanism.get("total_adaptive_safe_change_count") != 0
        or mechanism.get("total_adaptive_candidate_changed_cell_count") != 1
        or mechanism.get("total_adaptive_additional_fetch_calls") != 12
        or mechanism.get("total_adaptive_additional_fetch_effects") != 12
        or mechanism.get("total_adaptive_acquisition_credit_total_nats")
        != 0.441970278242
        or mechanism.get("total_adaptive_final_positive_information_gain_total_nats")
        != 1.807141910325
        or mechanism.get("total_adaptive_final_epistemic_credit_total_nats")
        != 1.807141910325
        or mechanism.get("total_adaptive_final_decision_credit_total_nats") != 0.0
        or observation.get("success_tasks") != 8
        or observation.get("failure_tasks") != 0
        or observation.get("fully_observed_effect_tasks") != 8
        or observation.get("unobserved_effect_tasks") != 0
        or supervision.get("worker_success_tasks") != 8
        or supervision.get("worker_hard_timeout_tasks") != 0
        or supervision.get("worker_nonzero_tasks") != 0
        or supervision.get("complete_validation_entered_tasks") != 8
        or supervision.get("complete_validation_returned_tasks") != 8
        or timing.get("parent_certificate_validation_wall_p95_seconds") != 0.070087
        or decision.get("status") != "fresh_memoized_external_no_go"
        or decision.get("diagnostic_route") != "adaptive_support_coverage_successor"
        or decision.get("authorization", {}).get("diagnostic_successor_design")
        is not True
        or decision.get("authorization", {}).get("fresh_paired_dev64_design")
        is not False
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("shared_api_lease_active") is not False
        or previous.get("selected") != 8
        or previous.get("batch_wall_seconds") != 220.338439
        or previous_supervision.get("worker_success_tasks") != 0
        or previous_supervision.get("worker_hard_timeout_tasks") != 8
        or previous_supervision.get("complete_validation_entered_tasks") != 3
        or previous_supervision.get("complete_validation_returned_tasks") != 0
        or not _sealed(result, "result_payload_sha256")
        or not _sealed(decision, "decision_payload_sha256")
        or not _sealed(audit, "audit_payload_sha256")
        or not _sealed(previous, "result_payload_sha256")
    ):
        raise RuntimeError("V2.44.89 frozen parent closure drifted")
    return result, previous


def _external_evidence(result: Mapping[str, Any]) -> dict[str, Any]:
    mechanism = result["mechanism_aggregate"]
    observation = result["observation_aggregate"]
    timing = result["stage_timing_aggregate"]
    supervision = result["supervision_aggregate"]
    return {
        "selected": 8,
        "batch_wall_seconds": result["batch_wall_seconds"],
        "worker_success_tasks": supervision["worker_success_tasks"],
        "worker_hard_timeout_tasks": supervision["worker_hard_timeout_tasks"],
        "complete_validation_entered_tasks": supervision[
            "complete_validation_entered_tasks"
        ],
        "complete_validation_returned_tasks": supervision[
            "complete_validation_returned_tasks"
        ],
        "parent_certificate_validation_wall_p95_seconds": timing[
            "parent_certificate_validation_wall_p95_seconds"
        ],
        "fully_observed_effect_tasks": observation["fully_observed_effect_tasks"],
        "unobserved_effect_tasks": observation["unobserved_effect_tasks"],
        "adaptive_additional_fetch_calls": mechanism[
            "total_adaptive_additional_fetch_calls"
        ],
        "adaptive_additional_fetch_effects": mechanism[
            "total_adaptive_additional_fetch_effects"
        ],
        "support_unreachable_tasks": mechanism["stop_reason_counts"][
            "support_unreachable"
        ],
        "budget_exhausted_tasks": mechanism["stop_reason_counts"][
            "budget_exhausted"
        ],
        "safe_decision_tasks": mechanism["stop_reason_counts"]["safe_decision"],
        "candidate_changed_cell_count": mechanism[
            "total_adaptive_candidate_changed_cell_count"
        ],
        "safe_change_count": mechanism["total_adaptive_safe_change_count"],
        "acquisition_credit_total_nats": mechanism[
            "total_adaptive_acquisition_credit_total_nats"
        ],
        "positive_information_gain_total_nats": mechanism[
            "total_adaptive_final_positive_information_gain_total_nats"
        ],
        "epistemic_credit_total_nats": mechanism[
            "total_adaptive_final_epistemic_credit_total_nats"
        ],
        "decision_credit_total_nats": mechanism[
            "total_adaptive_final_decision_credit_total_nats"
        ],
        "all_threshold_partitions_exact": mechanism[
            "all_threshold_partitions_exact"
        ],
        "all_effects_conserved": mechanism["all_effects_conserved"],
        "all_single_validation_attested": mechanism[
            "all_single_validation_attested"
        ],
    }


def _root_cause_findings() -> dict[str, bool]:
    return {
        "execution_scoped_validation_completion_gate_passed": True,
        "reliability_latency_and_parent_validation_gates_passed": True,
        "previous_all_worker_timeout_failure_not_observed": True,
        "positive_information_gain_without_safe_decision_observed": True,
        "positive_epistemic_credit_is_not_decision_credit": True,
        "frozen_lead_only_support_was_sufficient_on_this_population": False,
        "seven_of_eight_tasks_stopped_when_remaining_frozen_support_was_unreachable": True,
        "more_worker_or_parent_wall_time_is_primary_successor": False,
        "support_posterior_or_margin_threshold_relaxation_supported": False,
        "entropy_conditioned_targeted_search_causal_benefit_proven": False,
    }


def _successor_work_order() -> dict[str, Any]:
    return {
        "never_rerun_v24488_population": True,
        "preserve_runtime_boundary_exactly_opaque_id_and_question": True,
        "preserve_known_unknown_support_posterior_and_margin_thresholds": True,
        "preserve_decision_credit_requires_safe_output_change": True,
        "target_selection_uses_only_current_validated_entropy_and_support_deficit": True,
        "target_query_uses_only_frozen_visible_row_column_and_leading_alternative": True,
        "maximum_targeted_cells": 1,
        "maximum_additional_logical_queries": 2,
        "maximum_additional_search_batches": 1,
        "maximum_additional_provider_search_calls": 1,
        "maximum_additional_source_disjoint_fetches": 3,
        "additional_model_requests": 0,
        "new_sources_disjoint_from_all_proposal_active_and_adaptive_sources": True,
        "targeted_pages_never_enter_model_prompt": True,
        "posterior_source_credit_and_decision_credit_replayed_unchanged": True,
        "synthetic_safe_unreachable_empty_and_tamper_paths_required": True,
        "proof_carrying_worker_integration_required_before_external_effect": True,
        "fresh_external_population_required_after_offline_build_go": True,
        "paired_dev64_only_after_external_mechanism_go": True,
        "exact220_only_after_fresh_paired_dev64_go": True,
    }


def _authorization(valid: bool) -> dict[str, bool]:
    return {
        "entropy_conditioned_targeted_support_offline_design": valid,
        "synthetic_mechanism_and_tamper_tests": valid,
        "proof_carrying_worker_integration_design": False,
        "fresh_external_protocol_design": False,
        "external_probe_launch": False,
        "paired_dev64": False,
        "exact220": False,
        "evaluator": False,
        "leaderboard_or_sota": False,
    }


def build_report(*, now: int | None = None) -> dict[str, Any]:
    result, previous = _validate_parents()
    manifest = {str(path): sha256(base._ordinary(path)) for path in SOURCES}
    accesses: list[str] = []
    imports: list[str] = []
    for path in RUNTIME_SOURCES:
        current_accesses, current_imports = base._ast_findings(path)
        accesses.extend(current_accesses)
        imports.extend(current_imports)
    secret_hits = [
        str(path)
        for path in SOURCES
        if SECRET.search(base._ordinary(path).read_text(encoding="utf-8"))
    ]
    head = base._git("rev-parse", "HEAD")
    remote = base._git("rev-parse", "target/main")
    clean = base._git("status", "--porcelain") == ""
    tracked = all(base._tracked(path) for path in SOURCES)
    watchers = protected_watcher_snapshot()
    lease = lease_observation(ROOT, Path("/proc"))
    findings: list[str] = []
    if head != remote:
        findings.append("v24489_source_commit_not_pushed")
    if not clean:
        findings.append("v24489_source_worktree_not_clean")
    if not tracked:
        findings.append("v24489_source_not_tracked")
    if accesses:
        findings.append("privileged_field_access_in_bound_runtime")
    if imports:
        findings.append("evaluator_import_in_bound_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24489_surface")
    if watchers != EXPECTED_WATCHERS:
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    valid = not findings
    value = {
        "artifact_version": 1,
        "role": "v24489_v24488_support_conversion_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "result": {"path": str(RESULT), "sha256": sha256(base._ordinary(RESULT))},
            "decision": {
                "path": str(DECISION),
                "sha256": sha256(base._ordinary(DECISION)),
            },
            "postaudit": {
                "path": str(POSTAUDIT),
                "sha256": sha256(base._ordinary(POSTAUDIT)),
            },
            "previous_timeout_result": {
                "path": str(PREVIOUS_RESULT),
                "sha256": sha256(base._ordinary(PREVIOUS_RESULT)),
            },
        },
        "external_gate_evidence": _external_evidence(result),
        "cross_population_timing_context": {
            "v24484_batch_wall_seconds": previous["batch_wall_seconds"],
            "v24484_worker_success_tasks": previous["supervision_aggregate"][
                "worker_success_tasks"
            ],
            "v24484_worker_hard_timeout_tasks": previous["supervision_aggregate"][
                "worker_hard_timeout_tasks"
            ],
            "v24488_batch_wall_seconds": result["batch_wall_seconds"],
            "v24488_worker_success_tasks": result["supervision_aggregate"][
                "worker_success_tasks"
            ],
            "populations_are_different_so_timing_delta_is_not_a_paired_quality_effect": True,
        },
        "root_cause_findings": _root_cause_findings(),
        "successor_work_order": _successor_work_order(),
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "privileged_field_accesses": sorted(accesses),
        "evaluator_imports": sorted(imports),
        "credential_literal_hits": sorted(secret_hits),
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "worktree_clean": clean,
            "all_sources_tracked": tracked,
        },
        "closure": {
            "shared_api_lease_active": lease.get("active"),
            "protected_watchers": watchers,
            "protected_watchers_unchanged": watchers == EXPECTED_WATCHERS,
            "network_model_search_fetch_or_evaluator_called_by_diagnosis": False,
            "active_run_killed_or_quarantined": False,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "task_question_query_url_page_prediction_candidate_value_or_content_hash_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "same_run_evaluator_feedback_used": False,
        },
        "findings": findings,
        "diagnosis_valid": valid,
        "authorization": _authorization(valid),
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return value


def validate_report(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    evidence = copied.get("external_gate_evidence")
    context = copied.get("cross_population_timing_context")
    closure = copied.get("closure")
    valid = copied.get("findings") == []
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != "v24489_v24488_support_conversion_diagnosis"
        or not isinstance(evidence, Mapping)
        or evidence.get("selected") != 8
        or evidence.get("batch_wall_seconds") != 108.366926
        or evidence.get("worker_success_tasks") != 8
        or evidence.get("worker_hard_timeout_tasks") != 0
        or evidence.get("complete_validation_entered_tasks") != 8
        or evidence.get("complete_validation_returned_tasks") != 8
        or evidence.get("parent_certificate_validation_wall_p95_seconds") != 0.070087
        or evidence.get("adaptive_additional_fetch_calls") != 12
        or evidence.get("support_unreachable_tasks") != 7
        or evidence.get("budget_exhausted_tasks") != 1
        or evidence.get("safe_decision_tasks") != 0
        or evidence.get("safe_change_count") != 0
        or evidence.get("positive_information_gain_total_nats") != 1.807141910325
        or evidence.get("decision_credit_total_nats") != 0.0
        or not isinstance(context, Mapping)
        or context.get(
            "populations_are_different_so_timing_delta_is_not_a_paired_quality_effect"
        )
        is not True
        or copied.get("root_cause_findings") != _root_cause_findings()
        or copied.get("successor_work_order") != _successor_work_order()
        or copied.get("source_manifest_sha256")
        != payload_sha256(copied.get("source_manifest"))
        or copied.get("privileged_field_accesses") != []
        or copied.get("evaluator_imports") != []
        or copied.get("credential_literal_hits") != []
        or not isinstance(closure, Mapping)
        or closure.get("shared_api_lease_active") is not False
        or closure.get("protected_watchers_unchanged") is not True
        or closure.get("network_model_search_fetch_or_evaluator_called_by_diagnosis")
        is not False
        or copied.get("diagnosis_valid") is not valid
        or copied.get("authorization") != _authorization(valid)
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.44.89 diagnosis drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    report = build_report()
    validate_report(report)
    if not report["diagnosis_valid"]:
        raise RuntimeError("V2.44.89 diagnosis audit failed")
    publish_new(ROOT / REPORT, report)
    print(json.dumps({"path": str(REPORT), "diagnosis_valid": True}))
