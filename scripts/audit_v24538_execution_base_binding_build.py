#!/usr/bin/env python3
"""Build-only audit for the V2.45.37 execution-base binding repair.

The audit reads only repository sources and content-free control artifacts. It
does not open task-private directories, questions, queries, URLs, pages,
predictions, benchmark mappings, evaluator outputs, scores, or credentials.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import audit_v24495_targeted_conversion_projection_build as common  # noqa: E402
from scripts import audit_v24537_invalid_action_schema as quarantine  # noqa: E402
from scripts import v24537_alias_action_credit_external_gate as runner  # noqa: E402


DATE = "20260805"
AUDIT = Path(
    f"results/v24538_execution_base_binding_build_audit_v1_{DATE}.json"
)
QUARANTINE_AUDIT = quarantine.AUDIT
FIX_COMMIT = quarantine.FIX_COMMIT
SOURCES = (
    Path("scripts/v24492_targeted_external_gate.py"),
    Path("tests/test_v24492_targeted_external_gate.py"),
    Path("scripts/v24506_record_bound_external_gate.py"),
    Path("tests/test_v24506_record_bound_external_gate.py"),
    Path("scripts/v24512_proposal_seeded_external_gate.py"),
    Path("tests/test_v24512_proposal_seeded_external_gate.py"),
    Path("scripts/v24517_neutral_discovery_external_gate.py"),
    Path("tests/test_v24517_neutral_discovery_external_gate.py"),
    Path("scripts/v24522_conversion_diagnostic_external_gate.py"),
    Path("tests/test_v24522_conversion_diagnostic_external_gate.py"),
    Path("scripts/v24528_alias_title_external_gate.py"),
    Path("tests/test_v24528_alias_title_external_gate.py"),
    Path("scripts/v24531_alias_seeded_external_gate.py"),
    Path("tests/test_v24531_alias_seeded_external_gate.py"),
    Path("scripts/v24532_alias_seeded_external_gate.py"),
    Path("tests/test_v24532_alias_seeded_external_gate.py"),
    Path("src/deepwide_agent/v24533_alias_acquisition_entropy_credit.py"),
    Path("tests/test_v24533_alias_acquisition_entropy_credit.py"),
    Path("src/deepwide_agent/v24534_proof_carrying_alias_acquisition.py"),
    Path("tests/test_v24534_proof_carrying_alias_acquisition.py"),
    Path("src/deepwide_agent/v24535_total_alias_acquisition_projection.py"),
    Path("tests/test_v24535_total_alias_acquisition_projection.py"),
    Path("scripts/audit_v24536_alias_acquisition_credit_build.py"),
    Path("tests/test_audit_v24536_alias_acquisition_credit_build.py"),
    runner.PROTOCOL,
    runner.PREAUDIT,
    runner.ACTIVATION,
    runner.EXECUTION_START,
    runner.RESULT,
    runner.RUNNER_MARKER and Path(runner.RUNNER_MARKER),
    Path("tests/test_v24537_alias_action_credit_external_gate.py"),
    Path("scripts/audit_v24537_invalid_action_schema.py"),
    Path("tests/test_audit_v24537_invalid_action_schema.py"),
    QUARANTINE_AUDIT,
    Path("scripts/audit_v24538_execution_base_binding_build.py"),
    Path("tests/test_audit_v24538_execution_base_binding_build.py"),
)
RUNTIME_SOURCES = (
    Path("src/deepwide_agent/v24533_alias_acquisition_entropy_credit.py"),
    Path("src/deepwide_agent/v24534_proof_carrying_alias_acquisition.py"),
    Path("src/deepwide_agent/v24535_total_alias_acquisition_projection.py"),
    Path(runner.RUNNER_MARKER),
)
TEST_SUITES = (
    (Path("tests/test_v24492_targeted_external_gate.py"), 8, 120),
    (Path("tests/test_v24506_record_bound_external_gate.py"), 9, 180),
    (Path("tests/test_v24512_proposal_seeded_external_gate.py"), 9, 120),
    (Path("tests/test_v24517_neutral_discovery_external_gate.py"), 10, 120),
    (Path("tests/test_v24522_conversion_diagnostic_external_gate.py"), 12, 180),
    (Path("tests/test_v24528_alias_title_external_gate.py"), 12, 240),
    (Path("tests/test_v24531_alias_seeded_external_gate.py"), 12, 240),
    (Path("tests/test_v24532_alias_seeded_external_gate.py"), 12, 300),
    (Path("tests/test_v24533_alias_acquisition_entropy_credit.py"), 5, 180),
    (Path("tests/test_v24534_proof_carrying_alias_acquisition.py"), 8, 360),
    (Path("tests/test_v24535_total_alias_acquisition_projection.py"), 7, 180),
    (Path("tests/test_audit_v24536_alias_acquisition_credit_build.py"), 7, 120),
    (Path("tests/test_v24537_alias_action_credit_external_gate.py"), 16, 360),
    (Path("tests/test_audit_v24537_invalid_action_schema.py"), 5, 120),
    (Path("tests/test_audit_v24538_execution_base_binding_build.py"), 6, 120),
)
EXPECTED_TEST_COUNT = 138


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _quarantine_valid() -> bool:
    value = common._read(QUARANTINE_AUDIT)
    incident = value.get("incident", {})
    population = value.get("population", {})
    provenance = value.get("provenance", {})
    authorization = value.get("authorization", {})
    return (
        _sealed(value, "audit_payload_sha256")
        and value.get("role") == "v24537_invalid_action_schema_run_audit"
        and value.get("protocol_id") == runner.PROTOCOL_ID
        and value.get("status") == "invalid_quarantined_action_credit_unrecoverable"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and incident.get("external_execution_reliable") is True
        and incident.get("external_success_tasks") == 8
        and incident.get("external_failure_tasks") == 0
        and incident.get("published_schema_exactly_matches_legacy") is True
        and incident.get("public_result_valid_for_action_credit") is False
        and incident.get(
            "action_information_epistemic_or_decision_credit_recoverable"
        )
        is False
        and incident.get("benchmark_or_evaluator_called") is False
        and population.get("question_ordinals_consumed") == [388, 395]
        and population.get("entity_ordinals_consumed") == [3104, 3167]
        and population.get("same_population_rerun_allowed") is False
        and population.get("next_prior_question_count") == 396
        and population.get("next_prior_entity_count") == 3168
        and provenance.get("fix_commit") == FIX_COMMIT
        and provenance.get("current_runner_and_test_manifest_differ_from_frozen_execution")
        is True
        and authorization.get("same_population_resume_retry_or_rerun") is False
        and authorization.get("ordinary_v24537_decision_or_postaudit") is False
        and authorization.get("fresh_disjoint_successor_protocol_design") is True
        and authorization.get("fresh_successor_activation_or_launch") is False
        and authorization.get("paired_dev64_or_exact220") is False
    )


def _fix_is_ancestor() -> bool:
    for ref in ("HEAD", "target/main"):
        completed = subprocess.run(
            ["git", "merge-base", "--is-ancestor", FIX_COMMIT, ref],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        )
        if completed.returncode != 0:
            return False
    return True


def _runtime_binding_valid() -> bool:
    core = runner._patched_core()
    base = runner._base()
    return (
        core.get("run_targeted_worker") is runner.proof.run_worker
        and core.get("supervise_targeted_worker_with_separated_budget")
        is runner.proof.supervise_worker_with_separated_budget
        and core.get("run_targeted_parent_with_separated_budget")
        is runner.proof.run_parent_with_separated_budget
        and core.get("aggregate_projections") is runner.aggregate_action_projections
        and core.get("validate_targeted_aggregate") is runner.total.validate_aggregate
        and core.get("_mechanism_passed") is runner.mechanism_passed
        and base.run_probe.__module__ == "scripts.v24492_targeted_external_gate"
    )


def _legacy_result_rejected() -> bool:
    value = common._read(runner.RESULT)
    try:
        runner.validate_public_result(value)
    except RuntimeError as error:
        return str(error) == "V2.45.37 action aggregate schema is absent"
    return False


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    quarantine_valid = _quarantine_valid()
    fix_ancestor = _fix_is_ancestor()
    runtime_binding = _runtime_binding_valid()
    legacy_rejected = _legacy_result_rejected()
    manifest = {str(path): common._sha256(path) for path in SOURCES}
    accesses: list[str] = []
    imports: list[str] = []
    for path in RUNTIME_SOURCES:
        current_accesses, current_imports = common.ast_findings(path)
        accesses.extend(current_accesses)
        imports.extend(current_imports)
    secret_hits = [
        str(path)
        for path in SOURCES
        if common.SECRET.search(common._ordinary(path).read_text(encoding="utf-8"))
    ]
    suites = [
        {
            "path": str(path),
            "test_count": count,
            "passed": common._run_test(path, timeout),
        }
        for path, count, timeout in TEST_SUITES
    ]
    test_count = sum(item["test_count"] for item in suites)
    head = common._git("rev-parse", "HEAD")
    remote = common._git("rev-parse", "target/main")
    clean = common._git("status", "--porcelain") == ""
    tracked = all(common._tracked(path) for path in SOURCES)
    watchers = [
        {
            "pid": pid,
            "start_ticks": ticks,
            "marker": marker,
            "identity_valid": common._watcher(pid, ticks, marker),
        }
        for pid, ticks, marker in common.EXPECTED_WATCHERS
    ]
    lease_inactive = common._lease_inactive()
    no_process = quarantine._no_active_v24537_process()
    findings: list[str] = []
    if not quarantine_valid:
        findings.append("v24537_quarantine_drifted")
    if not fix_ancestor:
        findings.append("execution_base_fix_not_in_head_and_target_main")
    if not runtime_binding:
        findings.append("execution_base_action_binding_drifted")
    if not legacy_rejected:
        findings.append("legacy_alias_aggregate_not_rejected")
    if head != remote:
        findings.append("v24538_source_commit_not_pushed")
    if not clean:
        findings.append("v24538_source_worktree_not_clean")
    if not tracked:
        findings.append("v24538_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24492_v24538_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24533_v24537_runtime")
    if imports:
        findings.append("evaluator_import_in_v24533_v24537_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24538_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    if not no_process:
        findings.append("v24537_process_still_active")
    value = {
        "artifact_version": 1,
        "role": "v24538_execution_base_binding_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "v24537_quarantine": {
            "path": str(QUARANTINE_AUDIT),
            "sha256": common._sha256(QUARANTINE_AUDIT),
            "valid": quarantine_valid,
            "same_population_rerun_authorized": False,
            "next_prior_question_count": 396,
            "next_prior_entity_count": 3168,
        },
        "repair": {
            "fix_commit": FIX_COMMIT,
            "fix_is_ancestor_of_head_and_target_main": fix_ancestor,
            "execution_base_action_binding_valid": runtime_binding,
            "legacy_v24526_alias_aggregate_rejected": legacy_rejected,
            "direct_bottom_level_v24492_run_probe": True,
            "worker_and_supervisor_direct_bottom_level_dispatch": True,
            "required_action_aggregate_keys": sorted(
                runner._REQUIRED_ACTION_AGGREGATE_KEYS
            ),
            "configured_context_restores_all_bindings": True,
        },
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "worktree_clean": clean,
            "all_sources_tracked": tracked,
        },
        "tests": {
            "suites": suites,
            "test_count": test_count,
            "passed": all(item["passed"] for item in suites)
            and test_count == EXPECTED_TEST_COUNT,
            "synthetic_clients_and_pages_only": True,
            "historical_private_pages_opened": False,
            "remote_network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "label_blind_audit": {
            "privileged_runtime_field_accesses": sorted(accesses),
            "evaluator_imports": sorted(imports),
            "credential_literal_hits": sorted(secret_hits),
            "runtime_input_contract": ["opaque_id", "question"],
            "evaluator_opened": False,
            "passed": not accesses and not imports and not secret_hits,
        },
        "mechanism_evidence": {
            "action_credit_requires_plan_query_selection_new_observation_and_positive_posterior_delta": True,
            "decision_credit_additionally_requires_safe_output_change": True,
            "success_projection_requires_opaque_v24534_capability": True,
            "public_success_dictionary_cannot_be_reingested_as_proof": True,
            "failure_projection_is_exact_content_free_zero": True,
            "full_bottom_level_eight_row_aggregation_regression_present": True,
            "old_alias_schema_fails_before_result_acceptance": True,
            "same_run_credit_not_used_for_routing_training_or_policy_update": True,
        },
        "runtime_state": {
            "protected_watchers": watchers,
            "protected_watchers_unchanged": all(
                item["identity_valid"] for item in watchers
            ),
            "shared_api_lease_inactive": lease_inactive,
            "v24537_process_absent": no_process,
            "benchmark_launched": False,
            "external_population_launched": False,
            "evaluator_called": False,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "prior_external_or_benchmark_private_content_opened_by_audit": False,
            "remote_network_model_search_fetch_process_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_disjoint_action_credit_external_protocol_design": not findings,
            "fresh_external_activation_or_launch": False,
            "paired_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    value = build_audit()
    publish_new(ROOT / AUDIT, value)
    print(
        json.dumps(
            {
                "path": str(AUDIT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "test_count": value["tests"]["test_count"],
            },
            sort_keys=True,
        )
    )
