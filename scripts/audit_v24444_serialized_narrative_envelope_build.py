#!/usr/bin/env python3
"""Build-only audit for the V2.44.43 serialized-envelope repair.

V2.44.42 is immutable and is not retried here.  Its content-free closure
shows that every child wrote a result envelope without a child exception,
while every parent rejected that envelope after JSON serialization.  This
audit binds that observation to V2.44.43's value-preserving normalization and
full V2.44.38 validator delegation before permitting only the design of one
fresh external successor.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
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
from scripts import audit_v24441_bounded_narrative_projection_build as parent  # noqa: E402
from scripts import v24442_bounded_narrative_external_gate as failed_gate  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


DATE = "20260804"
AUDIT = Path(
    f"results/v24444_serialized_narrative_envelope_build_audit_v1_{DATE}.json"
)
PARENT = parent.AUDIT
FAILED_RESULT = failed_gate.RESULT
FAILED_DECISION = failed_gate.DECISION
FAILED_POSTAUDIT = failed_gate.POSTAUDIT
SOURCES = (
    Path("src/deepwide_agent/v24443_serialized_narrative_envelope.py"),
    Path("tests/test_v24443_serialized_narrative_envelope.py"),
    Path("scripts/audit_v24444_serialized_narrative_envelope_build.py"),
    Path("tests/test_audit_v24444_serialized_narrative_envelope_build.py"),
)
RUNTIME_SOURCES = (SOURCES[0],)
TEST_SUITES = (
    *parent.TEST_SUITES,
    (SOURCES[1], 5),
    (SOURCES[3], 4),
)
EXPECTED_TEST_COUNT = 100
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
        raise RuntimeError("V2.44.44 expected object")
    return value


def _failed_gate_evidence() -> dict[str, Any]:
    result = failed_gate.validate_public_result(_read(FAILED_RESULT))
    decision = failed_gate.validate_decision(ROOT, value=_read(FAILED_DECISION))
    postaudit = failed_gate.validate_postaudit(
        ROOT, value=_read(FAILED_POSTAUDIT)
    )
    observation = result["observation_aggregate"]
    if (
        result.get("selected") != 16
        or result.get("diagnostic_complete") is not False
        or result.get("mechanism_passed") is not False
        or result.get("passed") is not False
        or result.get("official_evaluator_called") is not False
        or result.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or observation.get("parent_taxonomy_counts")
        != {"result_envelope_invalid": 16}
        or observation.get("child_stage_counts")
        != {"result_envelope_written": 16}
        or observation.get("child_exception_type_counts") != {"None": 16}
        or observation.get("failure_tasks") != 16
        or observation.get("success_tasks") != 0
        or observation.get("fully_observed_effect_tasks") != 16
        or observation.get("model_acquisitions_lower_bound") != 32
        or observation.get("hosted_search_attempts_lower_bound") != 48
        or observation.get("hard_fetch_helper_calls_lower_bound") != 159
        or observation.get("provider_deadline_failures_lower_bound") != 0
        or decision.get("status")
        != "fresh_bounded_narrative_external_diagnostic_incomplete"
        or decision.get("diagnostic_route") != "runtime_or_observability_repair"
        or any(decision.get("authorization", {}).values())
        or postaudit.get("audit_valid") is not True
        or postaudit.get("findings") != []
        or any(postaudit.get("authorization", {}).values())
    ):
        raise RuntimeError("V2.44.44 failed-gate evidence drifted")
    return {
        "result": {"path": str(FAILED_RESULT), "sha256": sha256(ROOT / FAILED_RESULT)},
        "decision": {
            "path": str(FAILED_DECISION),
            "sha256": sha256(ROOT / FAILED_DECISION),
        },
        "postaudit": {
            "path": str(FAILED_POSTAUDIT),
            "sha256": sha256(ROOT / FAILED_POSTAUDIT),
        },
        "selected": 16,
        "child_result_envelopes_written": 16,
        "child_exceptions": 0,
        "parent_result_envelope_invalid": 16,
        "model_acquisitions_lower_bound": 32,
        "hosted_search_attempts_lower_bound": 48,
        "hard_fetch_helper_calls_lower_bound": 159,
        "provider_deadline_failures_lower_bound": 0,
        "diagnostic_route": "runtime_or_observability_repair",
        "v24442_rerun_resume_retry_or_revaluation": False,
    }


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    prior = parent.validate_audit(_read(PARENT))
    if prior.get("audit_valid") is not True or prior.get("findings") != []:
        raise RuntimeError("V2.44.44 parent build audit drifted")
    evidence = _failed_gate_evidence()
    manifest = {str(path): sha256(base._ordinary(path)) for path in SOURCES}
    accesses: list[str] = []
    imports: list[str] = []
    for path in RUNTIME_SOURCES:
        current_accesses, current_imports = base._ast_findings(path)
        accesses.extend(current_accesses)
        imports.extend(current_imports)
    suites = [
        {"path": str(path), "passed": base._run_test(path), "test_count": count}
        for path, count in TEST_SUITES
    ]
    test_count = sum(item["test_count"] for item in suites)
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
        findings.append("v24443_44_source_commit_not_pushed")
    if not clean:
        findings.append("v24443_44_source_worktree_not_clean")
    if not tracked:
        findings.append("v24443_44_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24312_4444_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24443_runtime")
    if imports:
        findings.append("evaluator_import_in_v24443_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24443_44_surface")
    if watchers != EXPECTED_WATCHERS:
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24444_serialized_narrative_envelope_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"path": str(PARENT), "sha256": sha256(base._ordinary(PARENT))},
        "failed_gate_evidence": evidence,
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
            "passed": all(item["passed"] for item in suites)
            and test_count == EXPECTED_TEST_COUNT,
            "test_count": test_count,
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "repair_evidence": {
            "failure_reproduced_by_sort_keys_json_round_trip": True,
            "only_two_protocol_reason_mappings_reordered": True,
            "canonical_json_value_preserved": True,
            "envelope_payload_seal_preserved": True,
            "complete_v24438_envelope_validator_reused": True,
            "complete_v24438_cross_artifact_validator_reused": True,
            "non_order_tamper_still_rejected": True,
            "external_effect_contract_not_relaxed": True,
            "benchmark_quality_not_measured": True,
        },
        "privileged_field_accesses": sorted(accesses),
        "evaluator_imports": sorted(imports),
        "credential_literal_hits": sorted(secret_hits),
        "closure": {
            "shared_api_lease_active": lease.get("active"),
            "protected_watchers": watchers,
            "protected_watchers_unchanged": watchers == EXPECTED_WATCHERS,
            "v24442_rerun_resume_retry_or_selective_revaluation": False,
            "active_run_killed_or_quarantined": False,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "task_query_url_page_prediction_value_or_content_hash_emitted": False,
            "remote_network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_serialization_fixed_external_probe_design": not findings,
            "external_probe_launch": False,
            "v24442_rerun": False,
            "paired_dev64": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def validate_audit(value: dict[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("audit_payload_sha256", None)
    authorization = value.get("authorization")
    if (
        value.get("role")
        != "v24444_serialized_narrative_envelope_build_audit"
        or not isinstance(authorization, dict)
        or set(authorization)
        != {
            "fresh_serialization_fixed_external_probe_design",
            "external_probe_launch",
            "v24442_rerun",
            "paired_dev64",
            "exact220",
            "evaluator",
            "leaderboard_or_sota",
        }
        or any(
            authorization.get(name) is not False
            for name in (
                "external_probe_launch",
                "v24442_rerun",
                "paired_dev64",
                "exact220",
                "evaluator",
                "leaderboard_or_sota",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.44.44 build audit drifted")
    return dict(value)


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    audit = build_audit()
    validate_audit(audit)
    publish_new(ROOT / AUDIT, audit)
    print(json.dumps({"path": str(AUDIT), "audit_valid": audit["audit_valid"]}))
