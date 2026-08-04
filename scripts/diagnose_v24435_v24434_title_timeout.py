#!/usr/bin/env python3
"""Content-free diagnosis of the V2.44.34 external-gate NO-GO.

The one authorized V2.44.34 run deleted every task-private directory before
publishing its result.  This diagnosis therefore consumes only sealed public
counts.  It keeps two failure axes separate:

* four children reached the parent hard timeout even though global model-slot
  contention was small and produced no slot timeout;
* among successful tasks, page-title alignment was common, but the strict
  label/value projector emitted no title observation or decision credit.

The exact blocking effect and the exact private page syntax are intentionally
unidentifiable after cleanup.  The report authorizes only append-only designs
for bounded per-effect timeouts and a counts-only narrative-label taxonomy.
It cannot authorize another external run, dev64, exact220, evaluation, or a
quality/SOTA claim.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from collections.abc import Mapping
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
from scripts import v24434_title_anchor_external_gate as parent  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


DATE = "20260804"
REPORT = Path(f"results/v24435_v24434_title_timeout_diagnosis_v1_{DATE}.json")
RESULT = parent.RESULT
DECISION = parent.DECISION
POSTAUDIT = parent.POSTAUDIT
TITLE_PROJECTION = Path(
    "src/deepwide_agent/v24428_unique_title_anchor_projection.py"
)
DEADLINE_SEARCH = Path("src/deepwide_agent/v24316_deadline_search.py")
GATE = Path("scripts/v24434_title_anchor_external_gate.py")
SOURCES = (
    TITLE_PROJECTION,
    DEADLINE_SEARCH,
    GATE,
    Path("scripts/diagnose_v24435_v24434_title_timeout.py"),
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
        raise RuntimeError("V2.44.35 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _validate_parent() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    result = parent.validate_public_result(_read(RESULT))
    decision = _read(DECISION)
    postaudit = _read(POSTAUDIT)
    parent.validate_decision(ROOT, value=decision)
    parent.validate_postaudit(ROOT, value=postaudit)
    mechanism = result["mechanism_aggregate"]
    observation = result["observation_aggregate"]
    if (
        result.get("selected") != 16
        or result.get("diagnostic_complete") is not False
        or result.get("mechanism_passed") is not False
        or result.get("passed") is not False
        or result.get("official_evaluator_called") is not False
        or result.get("resume_retry_skip_or_revaluation") is not False
        or result.get("temporary_execution_directory_remaining") is not False
        or observation.get("success_tasks") != 12
        or observation.get("failure_tasks") != 4
        or observation.get("parent_taxonomy_counts")
        != {"hard_deadline_timeout": 4, "success": 12}
        or observation.get("deadline_evidence_counts")
        != {"observed_not_exhausted": 12, "parent_hard_timeout": 4}
        or observation.get("fully_observed_effect_tasks") != 12
        or observation.get("unobserved_effect_tasks") != 4
        or mechanism.get("batch_wall_seconds") != 435.322321
        or mechanism.get("slot_total_wait_seconds") != 25.887149
        or mechanism.get("slot_max_wait_seconds") != 8.989329
        or mechanism.get("slot_timeouts") != 0
        or mechanism.get("provider_deadline_failures") != 0
        or mechanism.get("hosted_search_deadline_failures") != 0
        or mechanism.get("hard_fetch_deadline_failures") != 0
        or mechanism.get("fetch_helper_failures") != 0
        or mechanism.get("deadline_exhausted_tasks") != 4
        or mechanism.get("active_pages") != 20
        or mechanism.get("title_unique_anchor_pages") != 17
        or mechanism.get("title_ambiguous_or_absent_anchor_pages") != 3
        or mechanism.get("title_projections") != 0
        or mechanism.get("title_novel_observations") != 0
        or mechanism.get("title_positive_epistemic_tasks") != 2
        or mechanism.get("title_safe_change_tasks") != 0
        or mechanism.get("title_decision_credit_tasks") != 0
        or mechanism.get("title_positive_information_gain_total_nats")
        != 0.44197027824
        or mechanism.get("title_epistemic_credit_total_nats") != 0.44197027824
        or mechanism.get("title_decision_credit_total_nats") != 0
        or decision.get("status")
        != "fresh_title_anchor_external_diagnostic_incomplete"
        or decision.get("diagnostic_route") != "runtime_or_observability_repair"
        or any(decision.get("authorization", {}).values())
        or postaudit.get("audit_valid") is not True
        or postaudit.get("findings") != []
        or postaudit.get("shared_api_lease_active") is not False
        or not _sealed(result, "result_payload_sha256")
        or not _sealed(decision, "decision_payload_sha256")
        or not _sealed(postaudit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.44.35 parent result or closure drifted")
    return result, decision, postaudit


def build_report(*, now: int | None = None) -> dict[str, Any]:
    result, decision, postaudit = _validate_parent()
    mechanism = result["mechanism_aggregate"]
    observation = result["observation_aggregate"]
    title_source = base._ordinary(TITLE_PROJECTION).read_text(encoding="utf-8")
    deadline_source = base._ordinary(DEADLINE_SEARCH).read_text(encoding="utf-8")
    gate_source = base._ordinary(GATE).read_text(encoding="utf-8")
    source_invariants = {
        "strict_title_parser_accepts_only_key_value_lines": all(
            token in title_source
            for token in (
                "bound = base._label_value(line, labels)",
                "single_distinct_labelled_year_required",
            )
        ),
        "hosted_search_timeout_is_minimum_of_static_and_remaining": (
            "timeout=min(self.static_search_timeout_seconds, remaining)"
            in deadline_source
        ),
        "v24434_static_search_timeout_equals_task_wall": (
            "timeout=TASK_WALL_SECONDS" in gate_source
        ),
        "v24434_parent_timeout_exceeds_task_wall": (
            parent.PARENT_TIMEOUT_SECONDS > parent.TASK_WALL_SECONDS
        ),
    }
    manifest = {str(path): sha256(base._ordinary(path)) for path in SOURCES}
    head = base._git("rev-parse", "HEAD")
    remote = base._git("rev-parse", "target/main")
    clean = base._git("status", "--porcelain") == ""
    tracked = all(base._tracked(path) for path in SOURCES)
    watchers = protected_watcher_snapshot()
    lease = lease_observation(ROOT, Path("/proc"))
    secret_hits = [
        str(path)
        for path in SOURCES
        if SECRET.search(base._ordinary(path).read_text(encoding="utf-8"))
    ]
    findings: list[str] = []
    if not all(source_invariants.values()):
        findings.append("title_or_deadline_source_invariant_drifted")
    if not tracked:
        findings.append("v24435_diagnosis_source_not_tracked")
    if head != remote:
        findings.append("v24435_diagnosis_source_commit_not_pushed")
    if not clean:
        findings.append("v24435_diagnosis_worktree_not_clean")
    if watchers != EXPECTED_WATCHERS:
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if secret_hits:
        findings.append("credential_literal_in_v24435_surface")

    value = {
        "artifact_version": 1,
        "role": "v24435_v24434_title_timeout_diagnosis",
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
        "public_observation": {
            "selected": 16,
            "success_tasks": int(observation["success_tasks"]),
            "parent_hard_timeout_tasks": 4,
            "fully_observed_effect_tasks": int(
                observation["fully_observed_effect_tasks"]
            ),
            "unobserved_effect_tasks": int(observation["unobserved_effect_tasks"]),
            "batch_wall_seconds": float(mechanism["batch_wall_seconds"]),
            "slot_total_wait_seconds": float(mechanism["slot_total_wait_seconds"]),
            "slot_max_wait_seconds": float(mechanism["slot_max_wait_seconds"]),
            "slot_timeouts": int(mechanism["slot_timeouts"]),
            "active_pages": int(mechanism["active_pages"]),
            "title_unique_anchor_pages": int(
                mechanism["title_unique_anchor_pages"]
            ),
            "title_ambiguous_or_absent_anchor_pages": int(
                mechanism["title_ambiguous_or_absent_anchor_pages"]
            ),
            "title_projections": int(mechanism["title_projections"]),
            "title_novel_observations": int(
                mechanism["title_novel_observations"]
            ),
            "title_positive_epistemic_tasks": int(
                mechanism["title_positive_epistemic_tasks"]
            ),
            "title_safe_change_tasks": int(mechanism["title_safe_change_tasks"]),
            "title_positive_information_gain_total_nats": float(
                mechanism["title_positive_information_gain_total_nats"]
            ),
            "title_decision_credit_total_nats": float(
                mechanism["title_decision_credit_total_nats"]
            ),
        },
        "diagnosis": {
            "global_model_slot_timeout_observed": False,
            "parent_hard_timeout_observed": True,
            "exact_blocking_child_effect_identifiable": False,
            "per_effect_timeout_equals_full_task_budget": True,
            "bounded_per_effect_timeout_is_required_next_evidence": True,
            "title_alignment_succeeded_on_most_observed_active_pages": True,
            "title_alignment_fraction": 17 / 20,
            "strict_title_label_projection_conversion_observed": False,
            "narrative_label_present_vs_parser_false_negative_identifiable": False,
            "narrative_label_present_vs_parser_false_negative": "unidentifiable",
            "counts_only_narrative_rejection_taxonomy_is_required_next_evidence": True,
            "information_gain_without_decision_credit_observed": True,
            "entropy_quality_improvement_proven": False,
            "benchmark_quality_measured": False,
        },
        "source_invariants": source_invariants,
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
            "v24434_private_task_directories_reopened": False,
            "v24434_rerun_resume_retry_or_selective_revaluation": False,
            "network_model_search_fetch_or_evaluator_called_by_diagnosis": False,
        },
        "credential_literal_hits": secret_hits,
        "findings": findings,
        "diagnosis_valid": not findings,
        "authorization": {
            "bounded_per_effect_timeout_design": not findings,
            "counts_only_narrative_label_taxonomy_design": not findings,
            "external_probe_launch": False,
            "paired_dev64": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return value


def validate_report(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    expected = {
        "artifact_version",
        "role",
        "created_at_unix",
        "parent",
        "public_observation",
        "diagnosis",
        "source_invariants",
        "source_manifest",
        "source_manifest_sha256",
        "git",
        "closure",
        "credential_literal_hits",
        "findings",
        "diagnosis_valid",
        "authorization",
        "diagnosis_payload_sha256",
    }
    diagnosis = value.get("diagnosis")
    authorization = value.get("authorization")
    if (
        set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != "v24435_v24434_title_timeout_diagnosis"
        or isinstance(value.get("created_at_unix"), bool)
        or not isinstance(value.get("created_at_unix"), int)
        or value["created_at_unix"] < 0
        or not isinstance(diagnosis, Mapping)
        or diagnosis.get("exact_blocking_child_effect_identifiable") is not False
        or diagnosis.get(
            "narrative_label_present_vs_parser_false_negative_identifiable"
        )
        is not False
        or diagnosis.get("entropy_quality_improvement_proven") is not False
        or diagnosis.get("benchmark_quality_measured") is not False
        or not isinstance(authorization, Mapping)
        or set(authorization)
        != {
            "bounded_per_effect_timeout_design",
            "counts_only_narrative_label_taxonomy_design",
            "external_probe_launch",
            "paired_dev64",
            "exact220",
            "evaluator",
            "leaderboard_or_sota",
        }
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
        or value.get("source_manifest_sha256")
        != payload_sha256(value.get("source_manifest"))
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.44.35 diagnosis drifted")
    return dict(value)


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    report = build_report()
    validate_report(report)
    publish_new(ROOT / REPORT, report)
    print(json.dumps({"path": str(REPORT), "diagnosis_valid": report["diagnosis_valid"]}))
