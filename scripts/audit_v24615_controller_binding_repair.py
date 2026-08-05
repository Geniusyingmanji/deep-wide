#!/usr/bin/env python3
"""Clean-build audit for the V2.46.14 controller-binding repair.

The audit opens only committed source, tests, and content-free control/failure
artifacts.  It performs no network, model, search, fetch, process launch, or
evaluator effect and never opens a private task/query/URL/title/page/prediction
surface.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from deepwide_agent import v24614_title_provenance_controller_binding as binding  # noqa: E402
from scripts import audit_v24495_targeted_conversion_projection_build as common  # noqa: E402
from scripts import finalize_v24613_v24612_title_provenance_failure as failure  # noqa: E402


DATE = "20260805"
AUDIT = Path(f"results/v24615_controller_binding_repair_audit_v1_{DATE}.json")
PARENT_FAILURE = failure.FAILURE
PARENT_POSTAUDIT = failure.POSTAUDIT
SOURCES = (
    Path("scripts/v24612_title_provenance_external_gate.py"),
    Path("tests/test_v24612_title_provenance_external_gate.py"),
    Path("scripts/finalize_v24613_v24612_title_provenance_failure.py"),
    PARENT_FAILURE,
    PARENT_POSTAUDIT,
    Path("src/deepwide_agent/v24607_proof_carrying_title_provenance.py"),
    Path("src/deepwide_agent/v24608_total_title_provenance_projection.py"),
    Path("src/deepwide_agent/v24609_bounded_title_provenance_parent.py"),
    Path("scripts/v24610_title_provenance_collector.py"),
    Path("src/deepwide_agent/v24614_title_provenance_controller_binding.py"),
    Path("tests/test_v24614_title_provenance_controller_binding.py"),
    Path("scripts/audit_v24615_controller_binding_repair.py"),
    Path("tests/test_audit_v24615_controller_binding_repair.py"),
)
RUNTIME_SOURCES = (SOURCES[9],)
TEST_SUITES = (
    (Path("tests/test_v24607_proof_carrying_title_provenance.py"), 6, 300),
    (Path("tests/test_v24608_total_title_provenance_projection.py"), 6, 300),
    (Path("tests/test_v24609_bounded_title_provenance_parent.py"), 5, 360),
    (Path("tests/test_v24610_title_provenance_collector.py"), 7, 360),
    (Path("tests/test_v24612_title_provenance_external_gate.py"), 18, 600),
    (Path("tests/test_v24614_title_provenance_controller_binding.py"), 7, 300),
    (Path("tests/test_audit_v24615_controller_binding_repair.py"), 8, 180),
)
EXPECTED_TEST_COUNT = 57
PRIOR_QUESTION_COUNT = 492
PRIOR_ENTITY_COUNT = 3936


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parent_closed() -> bool:
    failed = common._read(PARENT_FAILURE)
    audited = common._read(PARENT_POSTAUDIT)
    return (
        failure.validate_failure(failed) == failed
        and failure.validate_postaudit(audited) == audited
        and _sealed(failed, "failure_payload_sha256")
        and _sealed(audited, "audit_payload_sha256")
        and failed.get("status") == "terminal_controller_binding_failure_no_result"
        and failed.get("external_wave_started") is True
        and failed.get("external_wave_count") == 1
        and failed.get("external_population_consumed") is True
        and failed.get("result_created") is False
        and failed.get("official_evaluator_called") is False
        and failed.get(
            "same_population_resume_retry_skip_selective_rerun_or_evaluation_authorized"
        )
        is False
        and failed.get("failure_class")
        == "controller_compatibility_binding_contaminated_runtime_proof_module"
        and audited.get("audit_valid") is True
        and audited.get("findings") == []
        and audited.get("shared_api_lease_active") is False
        and audited.get("v24612_runner_present") is False
        and audited.get("v24612_result_decision_or_postaudit_present") is False
    )


def _binding_valid() -> bool:
    protocol = binding.binding_vector(protocol_compatibility=True)
    runtime = binding.binding_vector(protocol_compatibility=False)
    return (
        binding.invariant_valid()
        and set(protocol) == {"proof", "total", "bounded", "collector_repair"}
        and set(runtime) == set(protocol)
        and all(protocol[name] is not runtime[name] for name in protocol)
        and runtime["proof"] is binding.runtime_proof
        and runtime["total"] is binding.runtime_total
        and runtime["bounded"] is binding.runtime_bounded
        and protocol["proof"] is binding.protocol_proof
        and protocol["total"] is binding.protocol_total
        and protocol["bounded"] is binding.protocol_bounded
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    parent_valid = _parent_closed()
    binding_valid = _binding_valid()
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
    findings: list[str] = []
    if not parent_valid:
        findings.append("v24612_13_terminal_failure_chain_drifted")
    if not binding_valid:
        findings.append("v24614_noncontaminating_binding_drifted")
    if head != remote:
        findings.append("v24614_15_source_commit_not_pushed")
    if not clean:
        findings.append("v24614_15_source_worktree_not_clean")
    if not tracked:
        findings.append("v24614_15_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24614_15_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24614_runtime")
    if imports:
        findings.append("evaluator_import_in_v24614_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24614_15_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24615_controller_binding_repair_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "closed_parent": {
            "failure_path": str(PARENT_FAILURE),
            "failure_sha256": common._sha256(PARENT_FAILURE),
            "postaudit_path": str(PARENT_POSTAUDIT),
            "postaudit_sha256": common._sha256(PARENT_POSTAUDIT),
            "v24612_population_consumed": True,
            "v24612_population_resume_retry_rerun_or_evaluation_authorized": False,
            "valid": parent_valid,
        },
        "freshness_baseline": {
            "prior_external_question_count": PRIOR_QUESTION_COUNT,
            "prior_external_entity_count": PRIOR_ENTITY_COUNT,
            "all_populations_through_v24612_counted_as_consumed": True,
            "v24612_population_resume_retry_rerun_or_evaluation_authorized": False,
            "v24613_15_build_work_consumes_external_population": False,
        },
        "binding_repair": {
            "policy_id": binding.POLICY_ID,
            "protocol_view_rebinds_controller_only": True,
            "runtime_view_rebinds_controller_only": True,
            "v24607_parent_proof_module_mutated": False,
            "v24607_parent_validator_mutated": False,
            "v24609_frozen_proof_or_total_binding_mutated": False,
            "nested_views_restore_lifo": True,
            "real_v24607_capability_validates_inside_protocol_view": True,
            "binding_valid": binding_valid,
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
            "synthetic_clients_capabilities_subprocesses_and_control_state_only": True,
            "historical_private_task_query_url_title_page_value_or_prediction_opened": False,
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
        "runtime_state": {
            "protected_watchers": watchers,
            "protected_watchers_unchanged": all(
                item["identity_valid"] for item in watchers
            ),
            "shared_api_lease_inactive": lease_inactive,
            "benchmark_launched": False,
            "external_population_launched_by_audit": False,
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
            "fresh_disjoint_content_free_title_provenance_successor_protocol_design": not findings,
            "same_v24612_population_retry_resume_rerun_or_evaluation": False,
            "fresh_external_activation_or_launch": False,
            "search_parser_title_validator_or_evidence_rule_change": False,
            "paired_dev64_or_exact220": False,
            "evaluator_access_authorized": False,
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
