#!/usr/bin/env python3
"""Build-only label-blind audit for V2.44.36--38 successors."""

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
from scripts import diagnose_v24435_v24434_title_timeout as diagnosis  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


DATE = "20260804"
AUDIT = Path(f"results/v24439_bounded_narrative_build_audit_v1_{DATE}.json")
PARENT = diagnosis.REPORT
SOURCES = (
    Path("src/deepwide_agent/v24436_narrative_title_anchor_projection.py"),
    Path("src/deepwide_agent/v24437_narrative_title_uncertainty_recovery.py"),
    Path("src/deepwide_agent/v24438_bounded_narrative_effect_runner.py"),
    Path("tests/test_v24436_narrative_title_anchor_projection.py"),
    Path("tests/test_v24437_narrative_title_uncertainty_recovery.py"),
    Path("tests/test_v24438_bounded_narrative_effect_runner.py"),
    Path("scripts/audit_v24439_bounded_narrative_build.py"),
)
RUNTIME_SOURCES = SOURCES[:3]
TEST_SUITES = (
    (Path("tests/test_v24312_deadline_reliability.py"), 7),
    (Path("tests/test_v24316_deadline_search.py"), 7),
    (Path("tests/test_v24388_uncertainty_credit.py"), 10),
    (Path("tests/test_v24391_uncertainty_active_evidence_runner.py"), 4),
    (Path("tests/test_v24399_failure_observable_runner.py"), 7),
    (Path("tests/test_v24413_effect_equivalence.py"), 7),
    (Path("tests/test_v24428_unique_title_anchor_projection.py"), 10),
    (Path("tests/test_v24429_title_anchor_uncertainty_recovery.py"), 7),
    (Path("tests/test_v24430_title_anchor_effect_runner.py"), 5),
    (Path("tests/test_v24436_narrative_title_anchor_projection.py"), 9),
    (Path("tests/test_v24437_narrative_title_uncertainty_recovery.py"), 7),
    (Path("tests/test_v24438_bounded_narrative_effect_runner.py"), 7),
)
EXPECTED_TEST_COUNT = 87
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
        raise RuntimeError("V2.44.39 expected object")
    return value


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    parent = diagnosis.validate_report(_read(PARENT))
    authorization = parent["authorization"]
    if (
        parent.get("diagnosis_valid") is not True
        or parent.get("findings") != []
        or authorization.get("bounded_per_effect_timeout_design") is not True
        or authorization.get("counts_only_narrative_label_taxonomy_design")
        is not True
        or any(
            authorization.get(name) is not False
            for name in (
                "external_probe_launch",
                "paired_dev64",
                "exact220",
                "evaluator",
                "leaderboard_or_sota",
            )
        )
    ):
        raise RuntimeError("V2.44.39 parent diagnosis drifted")
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
        findings.append("v24436_39_source_commit_not_pushed")
    if not clean:
        findings.append("v24436_39_source_worktree_not_clean")
    if not tracked:
        findings.append("v24436_39_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24312_4438_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24436_38_runtime")
    if imports:
        findings.append("evaluator_import_in_v24436_38_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24436_39_surface")
    if watchers != EXPECTED_WATCHERS:
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24439_bounded_narrative_build_audit",
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
            "v24428_parent_key_value_projection_preserved": True,
            "unique_complete_title_anchor_still_required": True,
            "narrative_relation_and_year_share_bounded_line": True,
            "other_visible_row_stops_title_scope": True,
            "arbitrary_nearby_year_rejected": True,
            "multiple_distinct_narrative_years_rejected": True,
            "page_target_rejection_partition_is_exact": True,
            "posterior_and_credit_recomputed_without_external_effect": True,
            "decision_credit_requires_safe_output_change": True,
            "model_and_search_provider_effect_cap_seconds": 70.0,
            "effect_cap_drift_rejected_before_external_effect": True,
            "narrative_recovery_effect_equivalence_attested": True,
            "failure_path_preserves_content_free_partial_receipts": True,
            "real_external_narrative_activation_not_yet_measured": True,
            "benchmark_quality_not_measured": True,
        },
        "privileged_field_accesses": sorted(accesses),
        "evaluator_imports": sorted(imports),
        "credential_literal_hits": sorted(secret_hits),
        "closure": {
            "shared_api_lease_active": lease.get("active"),
            "protected_watchers": watchers,
            "protected_watchers_unchanged": watchers == EXPECTED_WATCHERS,
            "v24434_rerun_resume_retry_or_selective_revaluation": False,
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
            "fresh_bounded_narrative_external_probe_design": not findings,
            "external_probe_launch": False,
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
        value.get("role") != "v24439_bounded_narrative_build_audit"
        or not isinstance(authorization, dict)
        or set(authorization)
        != {
            "fresh_bounded_narrative_external_probe_design",
            "external_probe_launch",
            "paired_dev64",
            "exact220",
            "evaluator",
            "leaderboard_or_sota",
        }
        or authorization.get("external_probe_launch") is not False
        or authorization.get("paired_dev64") is not False
        or authorization.get("exact220") is not False
        or authorization.get("evaluator") is not False
        or authorization.get("leaderboard_or_sota") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.44.39 build audit drifted")
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
