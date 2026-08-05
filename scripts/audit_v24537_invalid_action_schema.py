#!/usr/bin/env python3
"""Quarantine the V2.45.37 action-credit aggregate schema mismatch.

The one-wave external execution completed reliably, but the public mechanism
aggregate was exactly the older V2.45.26 alias schema.  It omitted every
V2.45.35 acquisition-action field, so action-level entropy/epistemic/decision
credit is not recoverable from the public result.  The 388--395 question and
3,104--3,167 entity population is consumed and may never be rerun.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from deepwide_agent import v24526_total_alias_title_projection as legacy  # noqa: E402
from deepwide_agent import v24535_total_alias_acquisition_projection as action  # noqa: E402
from scripts import audit_v24495_targeted_conversion_projection_build as common  # noqa: E402


DATE = "20260805"
PROTOCOL_ID = "v24537_fresh_alias_action_credit_external_gate_v1"
PROTOCOL = Path(f"results/v24537_alias_action_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(
    f"results/v24537_alias_action_external_preactivation_audit_v1_{DATE}.json"
)
ACTIVATION = Path(f"results/v24537_alias_action_external_activation_v1_{DATE}.json")
EXECUTION_START = Path(
    f"results/v24537_alias_action_external_execution_start_v1_{DATE}.json"
)
RESULT = Path(f"results/v24537_alias_action_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24537_alias_action_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24537_alias_action_external_postresult_audit_v1_{DATE}.json")
RUNNER = Path("scripts/v24537_alias_action_credit_external_gate.py")
RUNNER_TEST = Path("tests/test_v24537_alias_action_credit_external_gate.py")
QUARANTINE = Path(
    "results/DO_NOT_USE_invalid_v24537_alias_action_schema_mismatch_20260805"
)
AUDIT = QUARANTINE / "invalid_run_audit.json"
EXECUTION_START_COMMIT = "b73eae29169c825ad2601323845f9a92d3e43ba2"
ACTIVATION_COMMIT = "5ef327ba0efcbb990908f424ae3c4d3a50972190"
RESULT_COMMIT = "d628f932063a26252f5903368b991ce266927209"
FIX_COMMIT = "a0b649718439514cb2a53cb1fbe1c847b7ce8476"
REQUIRED_ACTION_KEYS = frozenset(
    {
        "acquisition_plan_tasks",
        "total_acquisition_action_count_fields",
        "total_acquisition_action_number_fields",
    }
)
SOURCES = (
    PROTOCOL,
    PREAUDIT,
    ACTIVATION,
    EXECUTION_START,
    RESULT,
    RUNNER,
    RUNNER_TEST,
    Path("scripts/audit_v24537_invalid_action_schema.py"),
    Path("tests/test_audit_v24537_invalid_action_schema.py"),
)


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _frozen_chain_valid() -> bool:
    protocol = common._read(PROTOCOL)
    preaudit = common._read(PREAUDIT)
    activation = common._read(ACTIVATION)
    start = common._read(EXECUTION_START)
    result = common._read(RESULT)
    provenance = result.get("provenance", {})
    return (
        all(
            value.get("protocol_id") == PROTOCOL_ID
            for value in (protocol, preaudit, activation, start, result)
        )
        and _sealed(protocol, "protocol_payload_sha256")
        and _sealed(preaudit, "audit_payload_sha256")
        and _sealed(activation, "activation_payload_sha256")
        and _sealed(start, "execution_start_payload_sha256")
        and _sealed(result, "result_payload_sha256")
        and preaudit.get("audit_valid") is True
        and preaudit.get("findings") == []
        and activation.get("launch_authorized") is True
        and start.get("execution_authorized") is True
        and start.get("activation_base_commit") == ACTIVATION_COMMIT
        and start.get("target_main_at_start") == ACTIVATION_COMMIT
        and start.get("runtime_input_exactly_opaque_id_and_question") is True
        and start.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is False
        and start.get("benchmark_or_evaluator_authorized") is False
        and provenance.get("protocol_sha256") == common._sha256(PROTOCOL)
        and provenance.get("preactivation_audit_sha256") == common._sha256(PREAUDIT)
        and provenance.get("activation_sha256") == common._sha256(ACTIVATION)
        and provenance.get("execution_start_sha256")
        == common._sha256(EXECUTION_START)
    )


def _schema_mismatch_proven() -> bool:
    result = common._read(RESULT)
    mechanism = result.get("mechanism_aggregate")
    if not isinstance(mechanism, Mapping):
        return False
    keys = frozenset(mechanism)
    return (
        keys == legacy.AGGREGATE_KEYS
        and keys != action.AGGREGATE_KEYS
        and REQUIRED_ACTION_KEYS.isdisjoint(keys)
        and action.AGGREGATE_KEYS - keys
        == action.AGGREGATE_KEYS - legacy.AGGREGATE_KEYS
    )


def _external_execution_reliable() -> bool:
    result = common._read(RESULT)
    observation = result.get("observation_aggregate", {})
    timing = result.get("stage_timing_aggregate", {})
    supervision = result.get("supervision_aggregate", {})
    return (
        result.get("selected") == 8
        and result.get("executor_count") == 8
        and result.get("model_slot_cap") == 2
        and result.get("one_wave") is True
        and result.get("batch_wall_seconds") == 150.403998
        and result.get("reliability_passed") is True
        and result.get("parent_validation_passed") is True
        and result.get("latency_passed") is True
        and observation.get("success_tasks") == 8
        and observation.get("failure_tasks") == 0
        and observation.get("slot_timeouts_lower_bound") == 0
        and observation.get("provider_deadline_failures_lower_bound") == 0
        and observation.get("hosted_search_deadline_failures_lower_bound") == 0
        and observation.get("hard_fetch_deadline_failures_lower_bound") == 0
        and observation.get("fetch_helper_failures_lower_bound") == 0
        and supervision.get("worker_success_tasks") == 8
        and supervision.get("worker_hard_timeout_tasks") == 0
        and supervision.get("worker_nonzero_tasks") == 0
        and supervision.get("complete_validation_returned_tasks") == 8
        and timing.get("parent_certificate_validation_wall_p95_seconds")
        == 0.764173
        and result.get("temporary_execution_directory_remaining") is False
        and result.get("resume_retry_skip_or_revaluation") is False
    )


def _source_drift_blocks_replay() -> bool:
    protocol = common._read(PROTOCOL)
    manifest = protocol.get("surface_manifest", {})
    return (
        isinstance(manifest, Mapping)
        and manifest.get(str(RUNNER)) != common._sha256(RUNNER)
        and manifest.get(str(RUNNER_TEST)) != common._sha256(RUNNER_TEST)
    )


def _no_active_v24537_process() -> bool:
    marker = b"scripts/v24537_alias_action_credit_external_gate.py"
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            command = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        if marker in command:
            return False
    return True


def _future_absent() -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in (DECISION, POSTAUDIT)
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    frozen_chain = _frozen_chain_valid()
    schema_mismatch = _schema_mismatch_proven()
    reliable = _external_execution_reliable()
    source_drift = _source_drift_blocks_replay()
    no_process = _no_active_v24537_process()
    future_absent = _future_absent()
    lease_inactive = common._lease_inactive()
    watchers = [
        {
            "pid": pid,
            "start_ticks": ticks,
            "marker": marker,
            "identity_valid": common._watcher(pid, ticks, marker),
        }
        for pid, ticks, marker in common.EXPECTED_WATCHERS
    ]
    head = common._git("rev-parse", "HEAD")
    remote = common._git("rev-parse", "target/main")
    clean = common._git("status", "--porcelain") == ""
    tracked = all(common._tracked(path) for path in SOURCES)
    accesses: list[str] = []
    imports: list[str] = []
    for path in (RUNNER,):
        current_accesses, current_imports = common.ast_findings(path)
        accesses.extend(current_accesses)
        imports.extend(current_imports)
    secret_hits = [
        str(path)
        for path in SOURCES
        if common.SECRET.search(common._ordinary(path).read_text(encoding="utf-8"))
    ]
    result = common._read(RESULT)
    findings: list[str] = []
    if not frozen_chain:
        findings.append("v24537_frozen_execution_chain_drifted")
    if not schema_mismatch:
        findings.append("v24537_action_schema_mismatch_not_proven")
    if not reliable:
        findings.append("v24537_external_reliability_evidence_drifted")
    if not source_drift:
        findings.append("v24537_same_population_replay_not_cryptographically_blocked")
    if not no_process:
        findings.append("v24537_process_still_active")
    if not future_absent:
        findings.append("v24537_decision_or_postaudit_present")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if head != remote:
        findings.append("quarantine_source_commit_not_pushed")
    if not clean:
        findings.append("quarantine_source_worktree_not_clean")
    if not tracked:
        findings.append("quarantine_source_not_tracked")
    if accesses:
        findings.append("privileged_field_access_in_fixed_runtime")
    if imports:
        findings.append("evaluator_import_in_fixed_runtime")
    if secret_hits:
        findings.append("credential_literal_in_quarantine_surface")
    if result.get(
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
    ) is not False or result.get("official_evaluator_called") is not False:
        findings.append("privileged_or_evaluator_effect_observed")
    value = {
        "artifact_version": 1,
        "role": "v24537_invalid_action_schema_run_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "invalid_quarantined_action_credit_unrecoverable",
        "incident": {
            "failure_stage": "content_free_mechanism_aggregate_after_successful_external_execution",
            "published_aggregate_schema": "v24526_total_alias_title_projection",
            "required_aggregate_schema": "v24535_total_alias_acquisition_projection",
            "published_schema_exactly_matches_legacy": schema_mismatch,
            "missing_required_action_key_count": len(
                action.AGGREGATE_KEYS - legacy.AGGREGATE_KEYS
            ),
            "required_action_keys_absent": sorted(REQUIRED_ACTION_KEYS),
            "external_execution_reliable": reliable,
            "external_success_tasks": 8,
            "external_failure_tasks": 0,
            "batch_wall_seconds": result.get("batch_wall_seconds"),
            "parent_validation_p95_seconds": result.get(
                "stage_timing_aggregate", {}
            ).get("parent_certificate_validation_wall_p95_seconds"),
            "public_result_published": True,
            "public_result_valid_for_reliability_only": True,
            "public_result_valid_for_action_credit": False,
            "action_information_epistemic_or_decision_credit_recoverable": False,
            "decision_published": False,
            "postaudit_published": False,
            "benchmark_or_evaluator_called": False,
            "score_available": False,
            "quality_or_sota_claim_allowed": False,
        },
        "population": {
            "question_ordinals_consumed": [388, 395],
            "entity_ordinals_consumed": [3104, 3167],
            "question_count": 8,
            "entity_count": 64,
            "same_population_rerun_allowed": False,
            "next_prior_question_count": 396,
            "next_prior_entity_count": 3168,
        },
        "provenance": {
            "execution_start_commit": EXECUTION_START_COMMIT,
            "activation_commit_bound_by_execution_start": ACTIVATION_COMMIT,
            "result_commit": RESULT_COMMIT,
            "fix_commit": FIX_COMMIT,
            "protocol_sha256": common._sha256(PROTOCOL),
            "preaudit_sha256": common._sha256(PREAUDIT),
            "activation_sha256": common._sha256(ACTIVATION),
            "execution_start_sha256": common._sha256(EXECUTION_START),
            "result_file_sha256": common._sha256(RESULT),
            "result_payload_sha256": result.get("result_payload_sha256"),
            "frozen_execution_chain_valid": frozen_chain,
            "current_runner_and_test_manifest_differ_from_frozen_execution": source_drift,
        },
        "runtime_state": {
            "decision_and_postaudit_absent": future_absent,
            "v24537_process_absent": no_process,
            "shared_api_lease_inactive": lease_inactive,
            "protected_watchers": watchers,
            "protected_watchers_unchanged": all(
                item["identity_valid"] for item in watchers
            ),
        },
        "label_blind_audit": {
            "runtime_input_contract": ["opaque_id", "question"],
            "privileged_runtime_field_accesses": sorted(accesses),
            "evaluator_imports": sorted(imports),
            "credential_literal_hits": sorted(secret_hits),
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "official_evaluator_called": False,
            "passed": not accesses and not imports and not secret_hits,
        },
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "worktree_clean": clean,
            "all_sources_tracked": tracked,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "same_population_resume_retry_or_rerun": False,
            "ordinary_v24537_decision_or_postaudit": False,
            "fresh_disjoint_successor_protocol_design": not findings,
            "fresh_successor_activation_or_launch": False,
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
    path.parent.mkdir(parents=False, exist_ok=False)
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
            },
            sort_keys=True,
        )
    )
