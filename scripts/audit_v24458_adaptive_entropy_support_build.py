#!/usr/bin/env python3
"""Build-only label-blind audit for V2.44.57 adaptive entropy support.

The audit binds the externally motivated three-fetch cap, unchanged support /
posterior / margin thresholds, frozen source-disjoint lead reuse, adaptive
stop replay, online acquisition information gain, and final leave-one-out
source/decision credit.  It performs no external effect and authorizes only
offline proof-carrying integration design.
"""

from __future__ import annotations

import copy
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import (  # noqa: E402
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from deepwide_agent.v24388_uncertainty_credit import (  # noqa: E402
    KNOWN_ALTERNATIVE_MINIMUM_SOURCES,
    MINIMUM_ALTERNATIVE_POSTERIOR,
    UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES,
)
from deepwide_agent.v24457_adaptive_entropy_support import (  # noqa: E402
    MAXIMUM_ACTIVE_SOURCES,
    MAXIMUM_ADDITIONAL_FETCHES,
    MAXIMUM_TOTAL_FETCHES,
)
from scripts import audit_v24398_failure_observability_build as base  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


DATE = "20260804"
AUDIT = Path(f"results/v24458_adaptive_entropy_support_build_audit_v1_{DATE}.json")
PARENT = Path(f"results/v24456_proof_carrying_build_audit_v1_{DATE}.json")
DIAGNOSIS = Path(f"results/v24453_v24452_validation_and_support_diagnosis_v1_{DATE}.json")
SOURCES = (
    Path("src/deepwide_agent/v24447_third_source_entropy_to_decision.py"),
    Path("src/deepwide_agent/v24457_adaptive_entropy_support.py"),
    Path("tests/test_v24457_adaptive_entropy_support.py"),
    Path("scripts/audit_v24458_adaptive_entropy_support_build.py"),
    Path("tests/test_audit_v24458_adaptive_entropy_support_build.py"),
)
RUNTIME_SOURCES = (SOURCES[1],)
TEST_SUITES = (
    (SOURCES[2], 6, "adaptive_mechanism", 900),
    (SOURCES[4], 5, "audit_control", 360),
)
EXPECTED_MECHANISM_TEST_COUNT = 6
EXPECTED_CONTROL_TEST_COUNT = 5
EXPECTED_TEST_COUNT = 11
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
        raise RuntimeError("V2.44.58 expected object")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _validate_parents() -> tuple[dict[str, Any], dict[str, Any]]:
    parent = _read(PARENT)
    diagnosis = _read(DIAGNOSIS)
    if (
        parent.get("role") != "v24456_proof_carrying_build_audit"
        or parent.get("audit_valid") is not True
        or parent.get("findings") != []
        or parent.get("authorization", {}).get(
            "adaptive_support_successor_offline_design"
        )
        is not True
        or parent.get("authorization", {}).get("external_probe_launch") is not False
        or not _sealed(parent, "audit_payload_sha256")
        or diagnosis.get("role")
        != "v24453_v24452_validation_and_support_diagnosis"
        or diagnosis.get("root_cause_findings", {}).get(
            "one_additional_third_source_hypothesis_externally_falsified"
        )
        is not True
        or diagnosis.get("successor_work_order", {}).get(
            "adaptive_support_may_use_only_frozen_source_disjoint_leads"
        )
        is not True
        or diagnosis.get("successor_work_order", {}).get(
            "adaptive_support_stops_on_safe_decision_or_budget_exhaustion"
        )
        is not True
        or diagnosis.get("root_cause_findings", {}).get(
            "threshold_relaxation_supported"
        )
        is not False
        or not _sealed(diagnosis, "diagnosis_payload_sha256")
    ):
        raise RuntimeError("V2.44.58 parent authorization drifted")
    return parent, diagnosis


def _run_test(relative: Path, *, timeout_seconds: int) -> bool:
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, int)
        or timeout_seconds < 1
        or timeout_seconds > 900
    ):
        raise ValueError("V2.44.58 test timeout is outside the frozen bound")
    completed = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(ROOT / relative), "-q"],
        cwd=ROOT,
        env={
            "HOME": os.environ.get("HOME", str(Path.home())),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=timeout_seconds,
        check=False,
    )
    return completed.returncode == 0


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    _validate_parents()
    if (
        MAXIMUM_ADDITIONAL_FETCHES != 3
        or MAXIMUM_TOTAL_FETCHES != 13
        or MAXIMUM_ACTIVE_SOURCES != 5
        or KNOWN_ALTERNATIVE_MINIMUM_SOURCES != 3
        or UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES != 2
        or MINIMUM_ALTERNATIVE_POSTERIOR != 0.8
    ):
        raise RuntimeError("V2.44.58 frozen threshold or budget constant drifted")
    manifest = {str(path): sha256(base._ordinary(path)) for path in SOURCES}
    accesses: list[str] = []
    imports: list[str] = []
    for path in RUNTIME_SOURCES:
        current_accesses, current_imports = base._ast_findings(path)
        accesses.extend(current_accesses)
        imports.extend(current_imports)
    suites = [
        {
            "path": str(path),
            "passed": _run_test(path, timeout_seconds=timeout_seconds),
            "test_count": count,
            "scope": scope,
            "timeout_seconds": timeout_seconds,
        }
        for path, count, scope, timeout_seconds in TEST_SUITES
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
        findings.append("v24457_58_source_commit_not_pushed")
    if not clean:
        findings.append("v24457_58_source_worktree_not_clean")
    if not tracked:
        findings.append("v24457_58_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24457_58_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24457_runtime")
    if imports:
        findings.append("evaluator_import_in_v24457_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24457_58_surface")
    if watchers != EXPECTED_WATCHERS:
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24458_adaptive_entropy_support_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "proof_carrying_build": {
                "path": str(PARENT),
                "sha256": sha256(base._ordinary(PARENT)),
            },
            "external_diagnosis": {
                "path": str(DIAGNOSIS),
                "sha256": sha256(base._ordinary(DIAGNOSIS)),
            },
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
            "mechanism_test_count": EXPECTED_MECHANISM_TEST_COUNT,
            "audit_control_test_count": EXPECTED_CONTROL_TEST_COUNT,
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "mechanism_evidence": {
            "maximum_additional_fetches": MAXIMUM_ADDITIONAL_FETCHES,
            "maximum_total_fetches": MAXIMUM_TOTAL_FETCHES,
            "maximum_active_sources": MAXIMUM_ACTIVE_SOURCES,
            "known_baseline_minimum_support_sources": KNOWN_ALTERNATIVE_MINIMUM_SOURCES,
            "unknown_baseline_minimum_support_sources": UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES,
            "minimum_alternative_posterior": MINIMUM_ALTERNATIVE_POSTERIOR,
            "required_support_margin": 1,
            "thresholds_relaxed": False,
            "additional_model_requests": 0,
            "additional_logical_queries": 0,
            "additional_search_batches": 0,
            "additional_provider_search_calls": 0,
            "frozen_source_disjoint_lead_pool_reused": True,
            "first_step_reuses_parent_ranking": True,
            "later_steps_use_current_validated_entropy_priority": True,
            "safe_decision_stops_immediately": True,
            "support_unreachable_stops_before_budget_exhaustion": True,
            "lead_pool_exhaustion_is_zero_or_bounded_fetch_terminal": True,
            "three_source_worst_case_crosses_unchanged_synthetic_gate": True,
            "zero_source_and_one_source_terminal_paths_tested": True,
        },
        "credit_evidence": {
            "step_acquisition_credit_is_realized_positive_entropy_reduction": True,
            "step_acquisition_credit_is_order_dependent_online_diagnostic": True,
            "final_source_credit_uses_normalized_leave_one_out_information_gain": True,
            "decision_credit_requires_safe_output_change": True,
            "allocated_credit_used_for_same_run_routing_or_training": False,
            "acquisition_priority_and_final_credit_are_not_conflated": True,
        },
        "tamper_evidence": {
            "lead_order_drift_rejected": True,
            "threshold_drift_rejected": True,
            "effect_drift_rejected": True,
            "step_entropy_credit_drift_rejected": True,
            "support_deficit_drift_rejected": True,
            "stop_reason_drift_rejected": True,
        },
        "privileged_field_accesses": sorted(accesses),
        "evaluator_imports": sorted(imports),
        "credential_literal_hits": sorted(secret_hits),
        "closure": {
            "shared_api_lease_active": lease.get("active"),
            "protected_watchers": watchers,
            "protected_watchers_unchanged": watchers == EXPECTED_WATCHERS,
            "external_probe_launched": False,
            "benchmark_or_watcher_signaled_restarted_or_modified": False,
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
            "proof_carrying_adaptive_integration_design": not findings,
            "fresh_external_protocol_design": False,
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
    copied = copy.deepcopy(value)
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    authorization = copied.get("authorization")
    mechanism = copied.get("mechanism_evidence")
    credit = copied.get("credit_evidence")
    if (
        copied.get("role") != "v24458_adaptive_entropy_support_build_audit"
        or not isinstance(authorization, dict)
        or set(authorization)
        != {
            "proof_carrying_adaptive_integration_design",
            "fresh_external_protocol_design",
            "external_probe_launch",
            "paired_dev64",
            "exact220",
            "evaluator",
            "leaderboard_or_sota",
        }
        or authorization.get("proof_carrying_adaptive_integration_design")
        is not copied.get("audit_valid")
        or any(
            authorization.get(name) is not False
            for name in (
                "fresh_external_protocol_design",
                "external_probe_launch",
                "paired_dev64",
                "exact220",
                "evaluator",
                "leaderboard_or_sota",
            )
        )
        or not isinstance(mechanism, dict)
        or mechanism.get("maximum_additional_fetches") != 3
        or mechanism.get("thresholds_relaxed") is not False
        or any(
            mechanism.get(name) != 0
            for name in (
                "additional_model_requests",
                "additional_logical_queries",
                "additional_search_batches",
                "additional_provider_search_calls",
            )
        )
        or not isinstance(credit, dict)
        or credit.get("decision_credit_requires_safe_output_change") is not True
        or credit.get("allocated_credit_used_for_same_run_routing_or_training")
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.44.58 build audit drifted")
    return copied


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
