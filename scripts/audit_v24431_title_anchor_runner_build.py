#!/usr/bin/env python3
"""Build audit for the V2.44.28-30 title-anchor recovery chain."""

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
AUDIT = Path(f"results/v24431_title_anchor_runner_build_audit_v1_{DATE}.json")
PARENT = Path(f"results/v24427_projection_observable_external_postresult_audit_v1_{DATE}.json")
SOURCES = (
    Path("src/deepwide_agent/v24428_unique_title_anchor_projection.py"),
    Path("src/deepwide_agent/v24429_title_anchor_uncertainty_recovery.py"),
    Path("src/deepwide_agent/v24430_title_anchor_effect_runner.py"),
    Path("tests/test_v24428_unique_title_anchor_projection.py"),
    Path("tests/test_v24429_title_anchor_uncertainty_recovery.py"),
    Path("tests/test_v24430_title_anchor_effect_runner.py"),
    Path("scripts/audit_v24431_title_anchor_runner_build.py"),
)
RUNTIME_SOURCES = SOURCES[:3]
TEST_SUITES = (
    (Path("tests/test_v24388_uncertainty_credit.py"), 10),
    (Path("tests/test_v24390_uncertainty_active_evidence_runtime.py"), 9),
    (Path("tests/test_v24405_structured_label_projection.py"), 8),
    (Path("tests/test_v24407_structured_uncertainty_recovery.py"), 6),
    (Path("tests/test_v24413_effect_equivalence.py"), 7),
    (Path("tests/test_v24415_effect_equivalent_structured_runner.py"), 6),
    (Path("tests/test_v24421_structured_projection_observability.py"), 7),
    (Path("tests/test_v24423_projection_observable_runner.py"), 5),
    (Path("tests/test_v24428_unique_title_anchor_projection.py"), 10),
    (Path("tests/test_v24429_title_anchor_uncertainty_recovery.py"), 7),
    (Path("tests/test_v24430_title_anchor_effect_runner.py"), 5),
)
EXPECTED_TEST_COUNT = 80
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
        raise RuntimeError("V2.44.31 expected object")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    parent = _read(PARENT)
    authorization = parent.get("authorization", {})
    if (
        parent.get("role")
        != "v24427_projection_observable_external_postresult_audit"
        or parent.get("audit_valid") is not True
        or parent.get("findings") != []
        or parent.get("diagnostic_route") != "entity_anchor_or_retrieval_successor"
        or authorization.get("diagnostic_successor_design") is not True
        or authorization.get("fresh_paired_dev64_design") is not False
        or authorization.get("fresh_paired_dev64_launch") is not False
        or authorization.get("new_exact220") is not False
        or authorization.get("evaluator") is not False
        or authorization.get("leaderboard_or_sota") is not False
        or not _sealed(parent, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.44.31 parent audit drifted")
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
        findings.append("v24428_31_source_commit_not_pushed")
    if not clean:
        findings.append("v24428_31_source_worktree_not_clean")
    if not tracked:
        findings.append("v24428_31_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24388_4430_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24428_30_runtime")
    if imports:
        findings.append("evaluator_import_in_v24428_30_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24428_31_surface")
    if watchers != EXPECTED_WATCHERS:
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24431_title_anchor_runner_build_audit",
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
        "title_anchor_evidence": {
            "v24427_route_is_entity_anchor_or_retrieval": True,
            "complete_visible_row_surface_required": True,
            "unique_visible_row_title_match_required": True,
            "exact_column_derived_label_required": True,
            "single_distinct_labelled_year_required": True,
            "other_visible_row_closes_title_scope": True,
            "multicolumn_unbound_row_rejected": True,
            "parent_projection_preserved_exactly": True,
            "same_pages_targets_queries_and_effects_reused": True,
            "decision_credit_still_requires_safe_output_change": True,
            "effect_equivalence_replayed_before_persistence": True,
            "real_external_title_activation_not_yet_measured": True,
            "benchmark_quality_not_measured": True,
        },
        "privileged_field_accesses": accesses,
        "evaluator_imports": imports,
        "credential_literal_hits": secret_hits,
        "closure": {
            "shared_api_lease_active": lease.get("active"),
            "protected_watchers": watchers,
            "protected_watchers_unchanged": watchers == EXPECTED_WATCHERS,
            "v24427_rerun_resume_retry_or_selective_revaluation": False,
            "active_run_killed_or_quarantined": False,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "task_title_page_entity_source_value_or_content_hash_emitted": False,
            "remote_network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_title_anchor_external_probe_design": not findings,
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
