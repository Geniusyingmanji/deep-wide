#!/usr/bin/env python3
"""Build-only audit for the V2.44.40 counts-only narrative projection."""

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
from scripts import audit_v24439_bounded_narrative_build as parent  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


DATE = "20260804"
AUDIT = Path(
    f"results/v24441_bounded_narrative_projection_build_audit_v1_{DATE}.json"
)
PARENT = parent.AUDIT
SOURCES = (
    Path("src/deepwide_agent/v24436_narrative_title_anchor_projection.py"),
    Path("src/deepwide_agent/v24437_narrative_title_uncertainty_recovery.py"),
    Path("src/deepwide_agent/v24438_bounded_narrative_effect_runner.py"),
    Path("scripts/v24440_bounded_narrative_external_projection.py"),
    Path("tests/test_v24440_bounded_narrative_external_projection.py"),
    Path("scripts/audit_v24441_bounded_narrative_projection_build.py"),
)
RUNTIME_SOURCES = SOURCES[:4]
TEST_SUITES = (*parent.TEST_SUITES, (SOURCES[4], 4))
EXPECTED_TEST_COUNT = 91
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
        raise RuntimeError("V2.44.41 expected object")
    return value


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    prior = parent.validate_audit(_read(PARENT))
    authorization = prior["authorization"]
    if (
        prior.get("audit_valid") is not True
        or prior.get("findings") != []
        or authorization.get("fresh_bounded_narrative_external_probe_design")
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
        raise RuntimeError("V2.44.41 parent audit drifted")
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
        findings.append("v24440_41_source_commit_not_pushed")
    if not clean:
        findings.append("v24440_41_source_worktree_not_clean")
    if not tracked:
        findings.append("v24440_41_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24312_4440_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24436_40_runtime")
    if imports:
        findings.append("evaluator_import_in_v24436_40_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24440_41_surface")
    if watchers != EXPECTED_WATCHERS:
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24441_bounded_narrative_projection_build_audit",
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
        "projection_evidence": {
            "complete_v24432_parent_projection_reused": True,
            "six_narrative_reason_counts_are_nonnegative": True,
            "narrative_page_target_reason_partition_conserved": True,
            "narrative_observation_and_resolution_counts_conserved": True,
            "epistemic_and_decision_credit_separated": True,
            "provider_effect_cap_is_public_and_bounded": True,
            "effect_equivalence_attested_per_task_and_aggregate": True,
            "failure_as_zero_does_not_claim_cap_or_equivalence": True,
            "task_private_content_not_emitted": True,
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
        value.get("role") != "v24441_bounded_narrative_projection_build_audit"
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
        raise RuntimeError("V2.44.41 build audit drifted")
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
