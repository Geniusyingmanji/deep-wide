#!/usr/bin/env python3
"""Quarantine the V2.45.31 callback-recursion execution.

The external children may have completed, but the parent process raised
``RecursionError`` while applying the content-free mechanism gate and before
publishing a result.  No score can be reconstructed or trusted.  The entire
372--379 question / 2,976--3,039 entity population is consumed and may never
be rerun; only a fresh disjoint successor may be designed.
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
from scripts import audit_v24495_targeted_conversion_projection_build as common  # noqa: E402


DATE = "20260805"
PROTOCOL_ID = "v24531_fresh_alias_seeded_entropy_credit_external_gate_v1"
PROTOCOL = Path(f"results/v24531_alias_seeded_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(
    f"results/v24531_alias_seeded_external_preactivation_audit_v1_{DATE}.json"
)
ACTIVATION = Path(f"results/v24531_alias_seeded_external_activation_v1_{DATE}.json")
EXECUTION_START = Path(
    f"results/v24531_alias_seeded_external_execution_start_v1_{DATE}.json"
)
RESULT = Path(f"results/v24531_alias_seeded_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24531_alias_seeded_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v24531_alias_seeded_external_postresult_audit_v1_{DATE}.json"
)
QUARANTINE = Path(
    "results/DO_NOT_USE_invalid_v24531_alias_seeded_callback_recursion_20260805"
)
AUDIT = QUARANTINE / "invalid_run_audit.json"
EXECUTION_START_COMMIT = "8a9b192cc375b84b9e42acecc652cfbc693de6e3"
ACTIVATION_COMMIT = "50fac0b6766c147318561da4a47627d77caec887"
FIX_COMMIT = "b0dfee4"
RUNNER = Path("scripts/v24531_alias_seeded_external_gate.py")
TEST = Path("tests/test_v24531_alias_seeded_external_gate.py")
SOURCES = (
    PROTOCOL,
    PREAUDIT,
    ACTIVATION,
    EXECUTION_START,
    RUNNER,
    TEST,
    Path("scripts/audit_v24531_invalid_callback_recursion.py"),
    Path("tests/test_audit_v24531_invalid_callback_recursion.py"),
)


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _frozen_start_valid() -> bool:
    protocol = common._read(PROTOCOL)
    preaudit = common._read(PREAUDIT)
    activation = common._read(ACTIVATION)
    start = common._read(EXECUTION_START)
    return (
        all(
            value.get("protocol_id") == PROTOCOL_ID
            for value in (protocol, preaudit, activation, start)
        )
        and _sealed(protocol, "protocol_payload_sha256")
        and _sealed(preaudit, "audit_payload_sha256")
        and _sealed(activation, "activation_payload_sha256")
        and _sealed(start, "execution_start_payload_sha256")
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
    )


def _future_absent() -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in (RESULT, DECISION, POSTAUDIT)
    )


def _source_drift_blocks_replay() -> bool:
    protocol = common._read(PROTOCOL)
    manifest = protocol.get("surface_manifest", {})
    return (
        isinstance(manifest, dict)
        and manifest.get(str(RUNNER)) != common._sha256(RUNNER)
        and manifest.get(str(TEST)) != common._sha256(TEST)
    )


def _no_active_v24531_process() -> bool:
    marker = b"scripts/v24531_alias_seeded_external_gate.py"
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


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    frozen_start_valid = _frozen_start_valid()
    future_absent = _future_absent()
    source_drift = _source_drift_blocks_replay()
    no_process = _no_active_v24531_process()
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
    findings: list[str] = []
    if not frozen_start_valid:
        findings.append("v24531_frozen_execution_start_drifted")
    if not future_absent:
        findings.append("v24531_untrusted_future_surface_present")
    if not source_drift:
        findings.append("v24531_same_population_replay_not_cryptographically_blocked")
    if not no_process:
        findings.append("v24531_process_still_active")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if head != remote:
        findings.append("incident_source_commit_not_pushed")
    if not clean:
        findings.append("incident_source_worktree_not_clean")
    if not tracked:
        findings.append("incident_source_not_tracked")
    if accesses:
        findings.append("privileged_field_access_in_fixed_runtime")
    if imports:
        findings.append("evaluator_import_in_fixed_runtime")
    if secret_hits:
        findings.append("credential_literal_in_incident_surface")
    value = {
        "artifact_version": 1,
        "role": "v24531_invalid_callback_recursion_run_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "invalid_quarantined_no_public_result",
        "incident": {
            "terminal_exception_type": "RecursionError",
            "failure_stage": "content_free_mechanism_gate_after_child_aggregation",
            "external_effects_may_have_occurred": True,
            "external_effect_counts_recoverable": False,
            "public_result_published": False,
            "decision_published": False,
            "postaudit_published": False,
            "benchmark_or_evaluator_called": False,
            "score_available": False,
            "quality_or_sota_claim_allowed": False,
        },
        "population": {
            "question_ordinals_consumed": [372, 379],
            "entity_ordinals_consumed": [2976, 3039],
            "question_count": 8,
            "entity_count": 64,
            "same_population_rerun_allowed": False,
            "next_prior_question_count": 380,
            "next_prior_entity_count": 3040,
        },
        "provenance": {
            "execution_start_commit": EXECUTION_START_COMMIT,
            "activation_commit_bound_by_execution_start": ACTIVATION_COMMIT,
            "fix_commit_prefix": FIX_COMMIT,
            "protocol_sha256": common._sha256(PROTOCOL),
            "preaudit_sha256": common._sha256(PREAUDIT),
            "activation_sha256": common._sha256(ACTIVATION),
            "execution_start_sha256": common._sha256(EXECUTION_START),
            "frozen_execution_start_valid": frozen_start_valid,
            "current_source_manifest_differs_from_frozen_execution": source_drift,
        },
        "runtime_state": {
            "result_decision_and_postaudit_absent": future_absent,
            "v24531_process_absent": no_process,
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
            "fresh_disjoint_successor_protocol_design": not findings,
            "fresh_successor_launch": False,
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
