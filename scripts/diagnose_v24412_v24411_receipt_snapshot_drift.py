#!/usr/bin/env python3
"""Content-free diagnosis of the V2.44.11 uniform runtime failure.

The V2.44.11 private task directories were deleted by protocol and are never
reopened.  This report combines only the sealed public exit/effect aggregate
with code-level invariants and synthetic fault reproduction.  It identifies a
single V2.44.09 RuntimeError branch: the runner compares whole model and
transport receipts before and after pure recovery, even though those receipts
contain observation-time state (remaining deadline / deadline exhausted).
With a real advancing monotonic clock, the snapshots differ while all external
effect counters remain unchanged.

This diagnosis performs no network, model, search, fetch, benchmark, evaluator,
reward, or score access and authorizes no rerun of V2.44.11.
"""

from __future__ import annotations

import ast
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
REPORT = Path(f"results/v24412_v24411_receipt_snapshot_diagnosis_v1_{DATE}.json")
RESULT = Path(f"results/v24411_structured_uncertainty_external_result_v1_{DATE}.json")
DECISION = Path(
    f"results/v24411_structured_uncertainty_external_decision_v1_{DATE}.json"
)
POSTAUDIT = Path(
    f"results/v24411_structured_uncertainty_external_postresult_audit_v1_{DATE}.json"
)
RUNNER = Path("src/deepwide_agent/v24409_structured_uncertainty_runner.py")
MODEL = Path("src/deepwide_agent/v24312_deadline_reliability.py")
SEARCH = Path("src/deepwide_agent/v24316_deadline_search.py")
SOURCES = (
    RUNNER,
    MODEL,
    SEARCH,
    Path("scripts/diagnose_v24412_v24411_receipt_snapshot_drift.py"),
    Path("tests/test_v24412_receipt_snapshot_diagnosis.py"),
)
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
        raise RuntimeError("V2.44.12 expected object")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _runner_runtime_branches() -> list[dict[str, Any]]:
    tree = ast.parse(base._ordinary(RUNNER).read_text(encoding="utf-8"))
    output: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
            continue
        function = node.exc.func
        name = function.id if isinstance(function, ast.Name) else ""
        if name != "RuntimeError":
            continue
        message = ""
        if node.exc.args and isinstance(node.exc.args[0], ast.Constant):
            message = str(node.exc.args[0].value)
        output.append({"line": node.lineno, "message": message})
    return sorted(output, key=lambda item: item["line"])


def _receipt_fields() -> dict[str, list[str]]:
    return {
        "model_effect_identity": [
            "acquisitions",
            "slot_timeouts",
            "provider_deadline_failures",
            "total_wait_seconds",
            "max_wait_seconds",
            "slot_acquisition_counts",
        ],
        "model_observation_time_state": [
            "remaining_seconds_at_receipt",
            "deadline_exhausted",
        ],
        "transport_effect_identity": [
            "hosted_search_attempts",
            "hosted_search_deadline_failures",
            "hard_fetch_helper_calls",
            "hard_fetch_deadline_failures",
            "fetch_deadline_rejections",
            "fetch_helper_failures",
        ],
        "transport_observation_time_state": ["deadline_exhausted"],
        "search_shape_identity": [
            "multi_query_chunks",
            "incomplete_mapping_chunks",
            "recursive_split_requests",
        ],
    }


def build_report(*, now: int | None = None) -> dict[str, Any]:
    result = _read(RESULT)
    decision = _read(DECISION)
    postaudit = _read(POSTAUDIT)
    observation = result.get("observation_aggregate", {})
    mechanism = result.get("mechanism_aggregate", {})
    if (
        result.get("role") != "v24411_structured_uncertainty_external_result"
        or result.get("selected") != 16
        or result.get("passed") is not False
        or mechanism.get("terminal_success_tasks") != 0
        or observation.get("parent_taxonomy_counts")
        != {"child_nonzero_with_terminal_receipt": 16}
        or observation.get("failure_stage_counts") != {"runtime": 16}
        or observation.get("failure_exception_type_counts") != {"RuntimeError": 16}
        or observation.get("effect_scope_counts")
        != {"failure_partial_receipts": 16}
        or observation.get("fully_observed_effect_tasks") != 16
        or observation.get("unobserved_effect_tasks") != 0
        or observation.get("slot_timeouts_lower_bound") != 0
        or observation.get("provider_deadline_failures_lower_bound") != 0
        or observation.get("hosted_search_deadline_failures_lower_bound") != 0
        or observation.get("hard_fetch_deadline_failures_lower_bound") != 0
        or observation.get("fetch_helper_failures_lower_bound") != 0
        or not _sealed(result, "result_payload_sha256")
        or decision.get("status") != "fresh_structured_uncertainty_external_no_go"
        or decision.get("authorization", {}).get("fresh_paired_dev64_design")
        is not False
        or not _sealed(decision, "decision_payload_sha256")
        or postaudit.get("audit_valid") is not True
        or postaudit.get("findings") != []
        or postaudit.get("shared_api_lease_active") is not False
        or not _sealed(postaudit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.44.12 parent result or closure drifted")

    runner = base._ordinary(RUNNER).read_text(encoding="utf-8")
    model = base._ordinary(MODEL).read_text(encoding="utf-8")
    search = base._ordinary(SEARCH).read_text(encoding="utf-8")
    branches = _runner_runtime_branches()
    whole_receipt_comparison = all(
        token in runner
        for token in (
            "model_after != model_before",
            "transport_after != transport_before",
            "search_after != search_before",
            "recovery caused an external effect",
        )
    )
    time_variant_fields_present = (
        '"remaining_seconds_at_receipt": round(remaining, 6)' in model
        and '"deadline_exhausted": self.remaining_effect_seconds()' in model
        and '"deadline_exhausted": self.remaining_effect_seconds()' in search
    )
    manifest = {str(path): sha256(base._ordinary(path)) for path in SOURCES}
    tracked = all(base._tracked(path) for path in SOURCES)
    head = base._git("rev-parse", "HEAD")
    remote = base._git("rev-parse", "target/main")
    clean = base._git("status", "--porcelain") == ""
    watchers = protected_watcher_snapshot()
    lease = lease_observation(ROOT, Path("/proc"))
    secret_hits = [
        str(path)
        for path in SOURCES
        if SECRET.search(base._ordinary(path).read_text(encoding="utf-8"))
    ]
    findings: list[str] = []
    if branches != [
        {"line": next(item["line"] for item in branches if item["message"] == "V2.44.09 recovery caused an external effect"), "message": "V2.44.09 recovery caused an external effect"}
    ]:
        findings.append("v24409_runtime_branch_set_drifted")
    if not whole_receipt_comparison or not time_variant_fields_present:
        findings.append("receipt_snapshot_drift_not_code_identified")
    if not tracked:
        findings.append("diagnosis_source_not_tracked")
    if head != remote:
        findings.append("diagnosis_source_commit_not_pushed")
    if not clean:
        findings.append("diagnosis_source_worktree_not_clean")
    if watchers != EXPECTED_WATCHERS:
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if secret_hits:
        findings.append("credential_literal_in_v24412_surface")

    value = {
        "artifact_version": 1,
        "role": "v24412_v24411_receipt_snapshot_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {
            "result": {"path": str(RESULT), "sha256": sha256(base._ordinary(RESULT))},
            "decision": {
                "path": str(DECISION),
                "sha256": sha256(base._ordinary(DECISION)),
            },
            "postresult_audit": {
                "path": str(POSTAUDIT),
                "sha256": sha256(base._ordinary(POSTAUDIT)),
            },
        },
        "public_failure_observation": {
            "selected": 16,
            "parent_taxonomy_counts": observation["parent_taxonomy_counts"],
            "failure_stage_counts": observation["failure_stage_counts"],
            "failure_exception_type_counts": observation[
                "failure_exception_type_counts"
            ],
            "effect_scope_counts": observation["effect_scope_counts"],
            "fully_observed_effect_tasks": observation[
                "fully_observed_effect_tasks"
            ],
            "model_acquisitions_lower_bound": observation[
                "model_acquisitions_lower_bound"
            ],
            "hosted_search_attempts_lower_bound": observation[
                "hosted_search_attempts_lower_bound"
            ],
            "hard_fetch_helper_calls_lower_bound": observation[
                "hard_fetch_helper_calls_lower_bound"
            ],
            "all_observed_deadline_or_transport_failure_counts_zero": True,
        },
        "code_diagnosis": {
            "runtime_error_branches": branches,
            "whole_receipt_snapshot_equality_required_after_pure_recovery": whole_receipt_comparison,
            "receipt_contains_observation_time_state": time_variant_fields_present,
            "receipt_field_classes": _receipt_fields(),
            "effect_counter_change_is_required_for_external_effect": True,
            "observation_time_state_change_alone_is_not_an_external_effect": True,
            "advancing_clock_reproduction_required_by_test": True,
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
        "closure": {
            "shared_api_lease_active": lease.get("active"),
            "protected_watchers": watchers,
            "protected_watchers_unchanged": watchers == EXPECTED_WATCHERS,
            "v24411_private_task_directories_reopened": False,
            "v24411_rerun_resume_retry_or_selective_revaluation": False,
            "network_model_search_fetch_or_evaluator_called_by_diagnosis": False,
        },
        "credential_literal_hits": secret_hits,
        "findings": findings,
        "diagnosis_valid": not findings,
        "diagnosis": (
            "whole_receipt_snapshot_equality_confuses_observation_time_drift_with_external_effect"
            if not findings
            else "inconclusive"
        ),
        "authorization": {
            "effect_equivalence_successor_design": not findings,
            "external_probe_launch": False,
            "paired_dev64": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
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
    report = build_report()
    publish_new(ROOT / REPORT, report)
    print(json.dumps({"path": str(REPORT), "diagnosis_valid": report["diagnosis_valid"]}))
