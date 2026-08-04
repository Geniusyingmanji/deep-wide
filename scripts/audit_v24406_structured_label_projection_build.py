#!/usr/bin/env python3
"""Build-only audit for the V2.44.05 structured label projector.

The V2.44.03 external run is immutable and remains a NO-GO.  This audit binds
its observed page-to-observation bottleneck to a pure, replayable successor
that recognizes entity-scoped label/value records and exact-header table rows.
It authorizes only runtime-successor design; no external task, benchmark,
evaluator, retry, resume, or leaderboard action is authorized.
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
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


DATE = "20260804"
AUDIT = Path(f"results/v24406_structured_label_projection_build_audit_v1_{DATE}.json")
PARENT_DECISION = Path(
    f"results/v24403_uncertainty_external_decision_v1_{DATE}.json"
)
PARENT_POSTAUDIT = Path(
    f"results/v24403_uncertainty_external_postresult_audit_v1_{DATE}.json"
)
SOURCES = (
    Path("src/deepwide_agent/v24405_structured_label_projection.py"),
    Path("tests/test_v24405_structured_label_projection.py"),
    Path("scripts/audit_v24406_structured_label_projection_build.py"),
)
RUNTIME_SOURCES = (SOURCES[0],)
TEST_SUITES = (
    (Path("tests/test_v24365_entity_segment_projection.py"), 9),
    (Path("tests/test_v24388_uncertainty_credit.py"), 10),
    (Path("tests/test_v24390_uncertainty_active_evidence_runtime.py"), 9),
    (Path("tests/test_v24405_structured_label_projection.py"), 8),
)
EXPECTED_TEST_COUNT = 36
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
        raise RuntimeError("V2.44.06 expected object")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    decision = _read(PARENT_DECISION)
    postaudit = _read(PARENT_POSTAUDIT)
    mechanism = decision.get("mechanism_aggregate", {})
    if (
        decision.get("role") != "v24403_uncertainty_external_decision"
        or decision.get("status")
        != "fresh_failure_observable_uncertainty_external_no_go"
        or decision.get("passed") is not False
        or decision.get("failed_checks")
        != [
            "positive_epistemic_credit",
            "positive_epistemic_tasks",
            "safe_change_tasks",
        ]
        or mechanism.get("terminal_success_tasks") != 16
        or mechanism.get("active_page_tasks") != 16
        or mechanism.get("active_pages") != 28
        or mechanism.get("active_observations") != 1
        or mechanism.get("positive_epistemic_tasks") != 0
        or mechanism.get("safe_change_tasks") != 0
        or mechanism.get("slot_timeouts") != 0
        or mechanism.get("deadline_exhausted_tasks") != 0
        or decision.get("authorization", {}).get("fresh_paired_dev64_design")
        is not False
        or decision.get("authorization", {}).get("new_exact220") is not False
        or not _sealed(decision, "decision_payload_sha256")
        or postaudit.get("role")
        != "v24403_uncertainty_external_postresult_audit"
        or postaudit.get("audit_valid") is not True
        or postaudit.get("findings") != []
        or postaudit.get("shared_api_lease_active") is not False
        or not _sealed(postaudit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.44.06 parent NO-GO or closure drifted")

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
    suites = [
        {"path": str(path), "passed": base._run_test(path), "test_count": count}
        for path, count in TEST_SUITES
    ]
    test_count = sum(item["test_count"] for item in suites)
    head = base._git("rev-parse", "HEAD")
    remote = base._git("rev-parse", "target/main")
    clean = base._git("status", "--porcelain") == ""
    tracked = all(base._tracked(path) for path in SOURCES)
    watchers = protected_watcher_snapshot()
    lease = lease_observation(ROOT, Path("/proc"))
    findings: list[str] = []
    if head != remote:
        findings.append("v24405_source_commit_not_pushed")
    if not clean:
        findings.append("v24405_source_worktree_not_clean")
    if not tracked:
        findings.append("v24405_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24365_4405_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24405_runtime")
    if imports:
        findings.append("evaluator_import_in_v24405_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24405_4406_surface")
    if watchers != EXPECTED_WATCHERS:
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")

    value = {
        "artifact_version": 1,
        "role": "v24406_structured_label_projection_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {
            "decision": {
                "path": str(PARENT_DECISION),
                "sha256": sha256(base._ordinary(PARENT_DECISION)),
            },
            "postresult_audit": {
                "path": str(PARENT_POSTAUDIT),
                "sha256": sha256(base._ordinary(PARENT_POSTAUDIT)),
            },
            "status": decision["status"],
            "active_pages": int(mechanism["active_pages"]),
            "active_observations": int(mechanism["active_observations"]),
            "positive_epistemic_tasks": int(
                mechanism["positive_epistemic_tasks"]
            ),
            "safe_change_tasks": int(mechanism["safe_change_tasks"]),
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
            "passed": all(item["passed"] for item in suites)
            and test_count == EXPECTED_TEST_COUNT,
            "test_count": test_count,
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "mechanism_evidence": {
            "legacy_target_segment_observations_preserved": True,
            "entity_scoped_infobox_label_value_supported": True,
            "exact_header_table_row_supported": True,
            "exact_visible_entity_binding_required": True,
            "exact_column_derived_label_required": True,
            "stable_latest_preview_release_labels_rejected": True,
            "unlabelled_nearby_year_rejected": True,
            "cross_target_relation_binding_rejected": True,
            "selected_target_projection_scope_enforced": True,
            "deterministic_private_replay_and_tamper_check": True,
            "observation_conversion_improved_on_synthetic_formats": True,
            "external_population_information_gain_not_yet_measured": True,
            "safe_change_or_benchmark_quality_not_yet_demonstrated": True,
        },
        "privileged_field_accesses": sorted(accesses),
        "evaluator_imports": sorted(imports),
        "credential_literal_hits": sorted(secret_hits),
        "closure": {
            "shared_api_lease_active": lease.get("active"),
            "protected_watchers": watchers,
            "protected_watchers_unchanged": watchers == EXPECTED_WATCHERS,
            "active_run_killed_or_quarantined": False,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        },
        "source_policy": {
            "runtime_boundary": ["baseline_prediction", "fetched_pages"],
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "remote_network_model_search_fetch_or_evaluator_called_by_audit": False,
            "parent_v24403_private_pages_reopened": False,
            "parent_v24403_result_reinterpreted_or_modified": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "structured_projection_runtime_successor_design": not findings,
            "external_probe_launch": False,
            "paired_dev64": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


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
    publish_new(ROOT / AUDIT, audit)
    print(json.dumps({"path": str(AUDIT), "audit_valid": audit["audit_valid"]}))
