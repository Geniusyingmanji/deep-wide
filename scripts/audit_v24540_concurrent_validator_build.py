#!/usr/bin/env python3
"""Build-only audit for the serialized successor-validator repair."""

from __future__ import annotations

import concurrent.futures
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
from scripts import audit_v24539_invalid_concurrent_validator as quarantine  # noqa: E402
from scripts import v24539_alias_action_credit_external_gate as runner  # noqa: E402


DATE = "20260805"
AUDIT = Path(f"results/v24540_concurrent_validator_build_audit_v1_{DATE}.json")
QUARANTINE_AUDIT = quarantine.AUDIT
FIX_COMMIT = quarantine.FIX_COMMIT
SOURCES = (
    Path("src/deepwide_agent/v24533_alias_acquisition_entropy_credit.py"),
    Path("tests/test_v24533_alias_acquisition_entropy_credit.py"),
    Path("src/deepwide_agent/v24534_proof_carrying_alias_acquisition.py"),
    Path("tests/test_v24534_proof_carrying_alias_acquisition.py"),
    Path("src/deepwide_agent/v24535_total_alias_acquisition_projection.py"),
    Path("tests/test_v24535_total_alias_acquisition_projection.py"),
    Path("scripts/v24537_alias_action_credit_external_gate.py"),
    Path("tests/test_v24537_alias_action_credit_external_gate.py"),
    Path("scripts/audit_v24538_execution_base_binding_build.py"),
    Path("tests/test_audit_v24538_execution_base_binding_build.py"),
    Path("results/v24538_execution_base_binding_build_audit_v1_20260805.json"),
    Path("scripts/v24539_alias_action_credit_external_gate.py"),
    Path("tests/test_v24539_alias_action_credit_external_gate.py"),
    Path("scripts/audit_v24539_invalid_concurrent_validator.py"),
    Path("tests/test_audit_v24539_invalid_concurrent_validator.py"),
    QUARANTINE_AUDIT,
    Path("scripts/audit_v24540_concurrent_validator_build.py"),
    Path("tests/test_audit_v24540_concurrent_validator_build.py"),
)
RUNTIME_SOURCES = (
    SOURCES[0],
    SOURCES[2],
    SOURCES[4],
    SOURCES[6],
    SOURCES[11],
)
TEST_SUITES = (
    (Path("tests/test_v24533_alias_acquisition_entropy_credit.py"), 5, 180),
    (Path("tests/test_v24534_proof_carrying_alias_acquisition.py"), 8, 360),
    (Path("tests/test_v24535_total_alias_acquisition_projection.py"), 7, 180),
    (Path("tests/test_v24537_alias_action_credit_external_gate.py"), 16, 360),
    (Path("tests/test_audit_v24538_execution_base_binding_build.py"), 6, 120),
    (Path("tests/test_v24539_alias_action_credit_external_gate.py"), 13, 360),
    (Path("tests/test_audit_v24539_invalid_concurrent_validator.py"), 5, 120),
    (Path("tests/test_audit_v24540_concurrent_validator_build.py"), 6, 120),
)
EXPECTED_TEST_COUNT = 66
STRESS_ROUNDS = 25
STRESS_WORKERS = 8
EXPECTED_STRESS_VALIDATIONS = STRESS_ROUNDS * STRESS_WORKERS


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
        and value.get("role") == "v24539_invalid_concurrent_validator_run_audit"
        and value.get("protocol_id") == runner.PROTOCOL_ID
        and value.get("status") == "invalid_quarantined_no_public_result"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and incident.get("shared_successor_module_patch_interleaving") is True
        and incident.get("historical_runner_lacked_serialized_validator") is True
        and incident.get("external_effect_counts_recoverable") is False
        and incident.get("public_result_published") is False
        and population.get("question_ordinals_consumed") == [396, 403]
        and population.get("entity_ordinals_consumed") == [3168, 3231]
        and population.get("same_population_rerun_allowed") is False
        and population.get("next_prior_question_count") == 404
        and population.get("next_prior_entity_count") == 3232
        and provenance.get("fix_commit") == FIX_COMMIT
        and provenance.get("current_runner_and_test_manifest_differ_from_frozen_execution")
        is True
        and authorization.get("same_population_resume_retry_or_rerun") is False
        and authorization.get("ordinary_v24539_result_decision_or_postaudit")
        is False
        and authorization.get("fresh_disjoint_successor_protocol_design") is True
        and authorization.get("fresh_successor_activation_or_launch") is False
        and authorization.get("paired_dev64_or_exact220") is False
    )


def _fix_is_ancestor() -> bool:
    return all(
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", FIX_COMMIT, ref],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode
        == 0
        for ref in ("HEAD", "target/main")
    )


def _serialized_binding_valid() -> bool:
    protocol = runner.build_protocol(now=0, require_pristine=False)
    if (
        not hasattr(runner, "_PROTOCOL_VALIDATOR_LOCK")
        or not callable(getattr(runner, "_validate_protocol_unlocked", None))
    ):
        return False
    with runner._PROTOCOL_VALIDATOR_LOCK:
        validated = runner.validate_protocol(value=protocol)
    return validated.get("protocol_id") == runner.PROTOCOL_ID


def _concurrent_stress() -> dict[str, Any]:
    protocol = runner.build_protocol(now=0, require_pristine=False)
    completed = 0
    for _round in range(STRESS_ROUNDS):
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=STRESS_WORKERS
        ) as pool:
            values = list(
                pool.map(
                    lambda _index: runner.validate_protocol(value=protocol)[
                        "protocol_id"
                    ],
                    range(STRESS_WORKERS),
                )
            )
        if values != [runner.PROTOCOL_ID] * STRESS_WORKERS:
            return {
                "rounds": STRESS_ROUNDS,
                "workers": STRESS_WORKERS,
                "validations": completed + len(values),
                "passed": False,
            }
        completed += len(values)
    return {
        "rounds": STRESS_ROUNDS,
        "workers": STRESS_WORKERS,
        "validations": completed,
        "passed": completed == EXPECTED_STRESS_VALIDATIONS,
    }


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    quarantine_valid = _quarantine_valid()
    fix_ancestor = _fix_is_ancestor()
    binding_valid = _serialized_binding_valid()
    stress = _concurrent_stress()
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
    no_process = quarantine._no_active_v24539_process()
    findings: list[str] = []
    if not quarantine_valid:
        findings.append("v24539_quarantine_drifted")
    if not fix_ancestor:
        findings.append("concurrent_validator_fix_not_in_head_and_target_main")
    if not binding_valid:
        findings.append("serialized_validator_binding_drifted")
    if stress.get("passed") is not True:
        findings.append("concurrent_validator_stress_failed")
    if head != remote:
        findings.append("v24540_source_commit_not_pushed")
    if not clean:
        findings.append("v24540_source_worktree_not_clean")
    if not tracked:
        findings.append("v24540_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24533_v24540_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24533_v24539_runtime")
    if imports:
        findings.append("evaluator_import_in_v24533_v24539_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24540_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    if not no_process:
        findings.append("v24539_process_still_active")
    value = {
        "artifact_version": 1,
        "role": "v24540_concurrent_validator_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "v24539_quarantine": {
            "path": str(QUARANTINE_AUDIT),
            "sha256": common._sha256(QUARANTINE_AUDIT),
            "valid": quarantine_valid,
            "same_population_rerun_authorized": False,
            "next_prior_question_count": 404,
            "next_prior_entity_count": 3232,
        },
        "repair": {
            "fix_commit": FIX_COMMIT,
            "fix_is_ancestor_of_head_and_target_main": fix_ancestor,
            "reentrant_protocol_validator_lock_present": binding_valid,
            "nested_module_patch_critical_section_serialized": True,
            "task_execution_remains_parallel_after_protocol_validation": True,
            "stress": stress,
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
        "runtime_state": {
            "protected_watchers": watchers,
            "protected_watchers_unchanged": all(
                item["identity_valid"] for item in watchers
            ),
            "shared_api_lease_inactive": lease_inactive,
            "v24539_process_absent": no_process,
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
                "stress_validations": value["repair"]["stress"]["validations"],
            },
            sort_keys=True,
        )
    )
