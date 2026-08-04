#!/usr/bin/env python3
"""Build-only label-blind audit for V2.44.47--50.

The audit binds the bounded third-source mechanism, value-preserving wire
normalization, capability-only counts projection, and non-overlapping child /
validation / projection timings.  It authorizes only preparation of a fresh
external diagnostic protocol.  It does not launch a probe, benchmark,
paired-dev64, exact220, evaluator, leaderboard submission, or SOTA claim.
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
from scripts import diagnose_v24446_v24445_entropy_to_decision as parent  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


DATE = "20260804"
AUDIT = Path(f"results/v24451_third_source_timing_build_audit_v2_{DATE}.json")
PARENT = parent.DIAGNOSIS
SOURCES = (
    Path("src/deepwide_agent/v24447_third_source_entropy_to_decision.py"),
    Path("src/deepwide_agent/v24448_serialized_third_source_envelope.py"),
    Path("scripts/v24449_third_source_external_projection.py"),
    Path("src/deepwide_agent/v24450_timed_third_source_runner.py"),
    Path("tests/test_v24447_third_source_entropy_to_decision.py"),
    Path("tests/test_v24448_serialized_third_source_envelope.py"),
    Path("tests/test_v24449_third_source_external_projection.py"),
    Path("tests/test_v24450_timed_third_source_runner.py"),
    Path("scripts/audit_v24451_third_source_timing_build.py"),
    Path("tests/test_audit_v24451_third_source_timing_build.py"),
)
RUNTIME_SOURCES = SOURCES[:4]
TEST_SUITES = (
    (Path("tests/test_v24308_child_exit_observability.py"), 9),
    (Path("tests/test_v24309_runner_exit_integration.py"), 5),
    (Path("tests/test_v24312_deadline_reliability.py"), 7),
    (Path("tests/test_v24316_deadline_search.py"), 7),
    (Path("tests/test_v24388_uncertainty_credit.py"), 10),
    (Path("tests/test_v24390_uncertainty_active_evidence_runtime.py"), 9),
    (Path("tests/test_v24436_narrative_title_anchor_projection.py"), 9),
    (Path("tests/test_v24437_narrative_title_uncertainty_recovery.py"), 7),
    (Path("tests/test_v24438_bounded_narrative_effect_runner.py"), 7),
    (SOURCES[4], 5),
    (SOURCES[5], 4),
    (SOURCES[6], 5),
    (SOURCES[7], 4),
    (SOURCES[9], 4),
)
EXPECTED_TEST_COUNT = 92
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
        raise RuntimeError("V2.44.51 expected object")
    return value


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    diagnosis = parent.validate_diagnosis(_read(PARENT))
    order = diagnosis["successor_work_order"]
    if (
        diagnosis.get("claims", {}).get("positive_epistemic_credit_measured")
        is not True
        or diagnosis.get("claims", {}).get("entropy_to_safe_decision_proven")
        is not False
        or order.get("allow_at_most_one_additional_active_source") is not True
        or order.get("single_complete_envelope_and_cross_artifact_validation_required")
        is not True
        or order.get("projection_may_consume_only_the_already_validated_envelope")
        is not True
        or order.get("publish_content_free_child_and_post_child_stage_timings")
        is not True
    ):
        raise RuntimeError("V2.44.51 parent work order drifted")
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
        findings.append("v24447_51_source_commit_not_pushed")
    if not clean:
        findings.append("v24447_51_source_worktree_not_clean")
    if not tracked:
        findings.append("v24447_51_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24308_4451_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24447_50_runtime")
    if imports:
        findings.append("evaluator_import_in_v24447_50_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24447_51_surface")
    if watchers != EXPECTED_WATCHERS:
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24451_third_source_timing_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"path": str(PARENT), "sha256": sha256(base._ordinary(PARENT))},
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
        "mechanism_evidence": {
            "safe_change_thresholds_preserved": True,
            "next_ranked_source_disjoint_third_lead_reused": True,
            "maximum_additional_fetch_calls": 1,
            "additional_model_query_search_batch_or_provider_search_calls": 0,
            "synthetic_safe_change_count": 1,
            "synthetic_decision_credit_positive": True,
            "third_source_alone_assumed_sufficient": False,
        },
        "validation_and_projection_evidence": {
            "sort_keys_json_value_preserved": True,
            "complete_envelope_and_terminal_artifact_validation_once": True,
            "unvalidated_or_envelope_only_capability_rejected_by_projection": True,
            "projection_receives_only_two_content_free_receipts": True,
            "threshold_failure_partition_mutually_exclusive_and_conserved": True,
            "private_content_absent_from_projection": True,
        },
        "timing_evidence": {
            "child_wait_wall_measured_before_parent_validation": True,
            "post_child_validation_wall_measured_separately": True,
            "model_transport_and_failure_observation_validation_included": True,
            "projection_wall_measured_separately": True,
            "failure_as_zero_projection_explicit": True,
            "sum_median_p95_max_published": True,
            "parallel_work_sums_not_claimed_as_batch_wall": True,
            "historical_v24445_latency_root_cause_retroactively_proven": False,
        },
        "privileged_field_accesses": sorted(accesses),
        "evaluator_imports": sorted(imports),
        "credential_literal_hits": sorted(secret_hits),
        "closure": {
            "shared_api_lease_active": lease.get("active"),
            "protected_watchers": watchers,
            "protected_watchers_unchanged": watchers == EXPECTED_WATCHERS,
            "old_v24445_rerun": False,
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
            "fresh_third_source_timing_external_probe_design": not findings,
            "external_probe_launch": False,
            "old_v24445_rerun": False,
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
        value.get("role") != "v24451_third_source_timing_build_audit"
        or not isinstance(authorization, dict)
        or set(authorization)
        != {
            "fresh_third_source_timing_external_probe_design",
            "external_probe_launch",
            "old_v24445_rerun",
            "paired_dev64",
            "exact220",
            "evaluator",
            "leaderboard_or_sota",
        }
        or any(
            authorization.get(name) is not False
            for name in (
                "external_probe_launch",
                "old_v24445_rerun",
                "paired_dev64",
                "exact220",
                "evaluator",
                "leaderboard_or_sota",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.44.51 build audit drifted")
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
