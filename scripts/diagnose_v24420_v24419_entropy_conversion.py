#!/usr/bin/env python3
"""Content-free diagnosis of the V2.44.19 mechanism NO-GO.

The fresh gate deleted its private task directories before publishing a public
result.  This report therefore reasons only from sealed aggregate counters and
source-level invariants.  It separates three claims that must not be conflated:

* runtime/effect equivalence succeeded;
* information gain and epistemic credit were observed;
* no evidence-triggered output change or decision credit was observed.

Zero structured projections alone cannot distinguish absent eligible page
patterns from projector false negatives.  The report explicitly marks that
question unidentifiable and authorizes only a content-free rejection-taxonomy
successor, not another external run, dev64, exact220, or evaluator access.
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
REPORT = Path(f"results/v24420_v24419_entropy_conversion_diagnosis_v1_{DATE}.json")
RESULT = Path(f"results/v24419_effect_equivalent_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24419_effect_equivalent_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v24419_effect_equivalent_external_postresult_audit_v1_{DATE}.json"
)
PROJECTION = Path("src/deepwide_agent/v24405_structured_label_projection.py")
RECOVERY = Path("src/deepwide_agent/v24407_structured_uncertainty_recovery.py")
ENTROPY = Path("src/deepwide_agent/v24388_uncertainty_credit.py")
SOURCES = (
    PROJECTION,
    RECOVERY,
    ENTROPY,
    Path("scripts/diagnose_v24420_v24419_entropy_conversion.py"),
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
        raise RuntimeError("V2.44.20 expected object")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def build_report(*, now: int | None = None) -> dict[str, Any]:
    result = _read(RESULT)
    decision = _read(DECISION)
    postaudit = _read(POSTAUDIT)
    mechanism = result.get("mechanism_aggregate", {})
    observation = result.get("observation_aggregate", {})
    if (
        result.get("role") != "v24419_effect_equivalent_external_result"
        or result.get("selected") != 16
        or result.get("passed") is not False
        or mechanism.get("terminal_success_tasks") != 16
        or mechanism.get("effect_equivalent_tasks") != 16
        or mechanism.get("all_effect_equivalence_attested") is not True
        or mechanism.get("slot_timeouts") != 0
        or mechanism.get("provider_deadline_failures") != 0
        or mechanism.get("hosted_search_deadline_failures") != 0
        or mechanism.get("hard_fetch_deadline_failures") != 0
        or mechanism.get("fetch_helper_failures") != 0
        or mechanism.get("deadline_exhausted_tasks") != 0
        or mechanism.get("active_pages") != 26
        or mechanism.get("legacy_active_observations") != 10
        or mechanism.get("structured_projections") != 0
        or mechanism.get("novel_structured_observations") != 0
        or mechanism.get("positive_epistemic_tasks") != 7
        or mechanism.get("baseline_confirmation_tasks") != 7
        or mechanism.get("safe_change_tasks") != 0
        or mechanism.get("safe_change_count") != 0
        or mechanism.get("positive_information_gain_total_nats")
        != 1.567978432896
        or mechanism.get("epistemic_credit_total_nats") != 1.567978432896
        or mechanism.get("decision_credit_total_nats") != 0
        or observation.get("success_tasks") != 16
        or observation.get("failure_tasks") != 0
        or result.get("temporary_execution_directory_remaining") is not False
        or result.get("official_evaluator_called") is not False
        or not _sealed(result, "result_payload_sha256")
        or decision.get("status") != "fresh_effect_equivalent_external_no_go"
        or decision.get("failed_checks")
        != ["novel_structured_observation_tasks", "safe_change_tasks"]
        or decision.get("authorization", {}).get("fresh_paired_dev64_design")
        is not False
        or not _sealed(decision, "decision_payload_sha256")
        or postaudit.get("audit_valid") is not True
        or postaudit.get("findings") != []
        or postaudit.get("shared_api_lease_active") is not False
        or not _sealed(postaudit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.44.20 parent result or closure drifted")

    projection_source = base._ordinary(PROJECTION).read_text(encoding="utf-8")
    recovery_source = base._ordinary(RECOVERY).read_text(encoding="utf-8")
    entropy_source = base._ordinary(ENTROPY).read_text(encoding="utf-8")
    source_invariants = {
        "projection_requires_exact_entity_and_column_derived_label": all(
            token in projection_source
            for token in (
                '"exact_visible_entity_binding_required": True',
                '"exact_column_derived_label_required": True',
            )
        ),
        "recovery_reuses_parent_effects_without_reexecution": (
            '"parent_target_query_source_and_effects_reused_without_reexecution": True'
            in recovery_source
        ),
        "decision_credit_requires_safe_output_change": (
            "decision_credit_requires_safe_output_change" in entropy_source
            and "safe_change" in entropy_source
        ),
    }
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
    if not all(source_invariants.values()):
        findings.append("entropy_or_projection_source_invariant_drifted")
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
        findings.append("credential_literal_in_v24420_surface")

    value = {
        "artifact_version": 1,
        "role": "v24420_v24419_entropy_conversion_diagnosis",
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
            "terminal_success_tasks": 16,
            "effect_equivalent_tasks": 16,
            "active_pages": 26,
            "legacy_active_observations": 10,
            "structured_projections": 0,
            "positive_epistemic_tasks": 7,
            "baseline_confirmation_tasks": 7,
            "safe_change_tasks": 0,
            "positive_information_gain_total_nats": 1.567978432896,
            "epistemic_credit_total_nats": 1.567978432896,
            "decision_credit_total_nats": 0,
            "runtime_deadline_or_transport_failures": 0,
        },
        "diagnosis": {
            "runtime_and_effect_equivalence_failure_excluded": True,
            "nonzero_external_information_gain_observed": True,
            "epistemic_credit_equals_positive_information_gain": True,
            "all_positive_epistemic_tasks_confirmed_baseline": True,
            "information_gain_to_safe_change_conversion_observed": False,
            "structured_projection_increment_observed": False,
            "zero_structured_projection_cause_identifiable_from_public_artifacts": False,
            "eligible_structured_pattern_absent_vs_parser_false_negative": "unidentifiable",
            "entropy_credit_is_useless": False,
            "entropy_quality_improvement_proven": False,
            "benchmark_quality_measured": False,
            "next_required_evidence": "content_free_structured_rejection_taxonomy",
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
            "v24419_private_task_directories_reopened": False,
            "v24419_rerun_resume_retry_or_selective_revaluation": False,
            "network_model_search_fetch_or_evaluator_called_by_diagnosis": False,
        },
        "credential_literal_hits": secret_hits,
        "findings": findings,
        "diagnosis_valid": not findings,
        "authorization": {
            "content_free_projection_rejection_taxonomy_design": not findings,
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
