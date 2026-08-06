#!/usr/bin/env python3
"""Clean-build audit for V2.46.68 visible-surface information gain.

The audit reads only the frozen V2.46.67 aggregate diagnosis, repository
sources, git/process/lease state, and non-evaluator tests.  It does not reopen
task traces or read mapping, gold, provenance, category, split, score, or
evaluator surfaces, and performs no model, search, fetch, benchmark, or
evaluator effect.
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from deepwide_agent import v24668_visible_surface_information_gain_runtime as runtime  # noqa: E402
from scripts import audit_v24495_targeted_conversion_projection_build as common  # noqa: E402
from scripts import diagnose_v24667_v24664_strict_closure_no_go as diagnosis  # noqa: E402


DATE = "20260806"
PARENT = diagnosis.OUTPUT
AUDIT = Path(f"results/v24669_information_gain_acquisition_build_audit_v1_{DATE}.json")
RUNTIME_SOURCES = (
    Path("src/deepwide_agent/v24668_visible_surface_information_gain_runtime.py"),
)
SOURCES = (
    PARENT,
    Path("src/deepwide_agent/v24547_alias_surface_observability.py"),
    Path("src/deepwide_agent/v24655_unknown_cell_targeted_runtime.py"),
    Path("src/deepwide_agent/v24659_support_closure_runtime.py"),
    Path("src/deepwide_agent/v24661_support_closure_task_runtime.py"),
    *RUNTIME_SOURCES,
    Path("tests/test_v24668_visible_surface_information_gain_runtime.py"),
    Path("scripts/audit_v24669_information_gain_acquisition_build.py"),
    Path("tests/test_audit_v24669_information_gain_acquisition_build.py"),
)
TEST_SUITES = (
    (Path("tests/test_v24655_unknown_cell_targeted_runtime.py"), 8, 180),
    (Path("tests/test_v24659_support_closure_runtime.py"), 7, 180),
    (Path("tests/test_v24661_support_closure_task_runtime.py"), 7, 180),
    (Path("tests/test_v24668_visible_surface_information_gain_runtime.py"), 8, 180),
    (Path("tests/test_audit_v24669_information_gain_acquisition_build.py"), 5, 120),
)
EXPECTED_TEST_COUNT = 35


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    try:
        value = json.loads(common._ordinary(PARENT).read_text(encoding="utf-8"))
        diagnosis.validate_diagnosis(value)
    except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        return False
    return (
        value.get("status")
        == "citation_omission_hypothesis_falsified_on_frozen_population"
        and value.get("aggregate", {}).get(
            "targeted_discovered_independent_source_count"
        )
        == 399
        and value.get("aggregate", {}).get("targeted_usable_page_count") == 38
        and value.get("aggregate", {}).get(
            "support_closure_added_evidence_id_count"
        )
        == 0
        and value.get("support_failure_taxonomy", {}).get(
            "proposal_with_two_or_more_local_exact_support_sources_count"
        )
        == 0
        and value.get("diagnosis", {}).get(
            "current_bottleneck_is_failure_to_acquire_same_value_two_source_exact_support"
        )
        is True
        and value.get("authorization")
        == {
            "visible_lead_alignment_successor_implementation": True,
            "fresh_external_protocol_design": False,
            "fresh_external_activation_or_launch": False,
            "evaluator": False,
            "dev64": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        }
        and _sealed(value, "diagnosis_payload_sha256")
    )


def _run_test(path: Path, timeout: int) -> tuple[bool, int]:
    completed = subprocess.run(
        [
            str(ROOT / ".venv-eval/bin/python"),
            "-I",
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            path.name,
        ],
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
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
        check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    return completed.returncode == 0, int(match.group(1)) if match else 0


def _implementation_valid() -> bool:
    batches = [
        {
            "query": '"Alpha Phone" "Release Date"',
            "results": [
                {
                    "title": "Generic database",
                    "url": "https://generic.example/record",
                },
                {
                    "title": "Alpha Phone official release",
                    "url": "https://aligned.example/record",
                },
                {
                    "title": "Release archive",
                    "url": "https://archive.example/alpha-phone/history",
                },
                {
                    "title": "Other record",
                    "url": "https://other.example/record",
                },
            ],
        }
    ]
    selected, eligible, observed = (
        runtime.select_visible_surface_information_gain_leads(
            batches,
            row_key="Alpha Phone",
            excluded_sources=set(),
            excluded_urls=set(),
            limit=2,
        )
    )
    return (
        runtime.TARGET_CELL_CAP == 1
        and runtime.TARGET_FETCH_CAP == 4
        and runtime.strict.MINIMUM_INDEPENDENT_SUPPORT_SOURCES == 2
        and len(eligible) == 4
        and len(selected) == 2
        and "Alpha Phone" in selected[0]["title"]
        and "alpha-phone" in selected[1]["url"]
        and observed["visible_surface_aligned_source_count"] == 2
        and observed["visible_surface_selected_aligned_lead_count"] == 2
        and math.isclose(
            float(observed["visible_surface_localization_information_gain_nats"]),
            math.log(2),
            abs_tol=1e-12,
        )
        and math.isclose(
            float(observed["epistemic_action_credit_nats"]),
            math.log(2),
            abs_tol=1e-12,
        )
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    manifest = {str(path): common._sha256(path) for path in SOURCES}
    accesses: list[str] = []
    imports: list[str] = []
    for path in RUNTIME_SOURCES:
        current_accesses, current_imports = common.ast_findings(path)
        accesses.extend(current_accesses)
        imports.extend(current_imports)
    secret_hits = [
        str(path)
        for path in SOURCES
        if common.SECRET.search(common._ordinary(path).read_text(encoding="utf-8"))
    ]
    suites = []
    for path, expected, timeout in TEST_SUITES:
        passed, observed = _run_test(path, timeout)
        suites.append(
            {
                "path": str(path),
                "expected_test_count": expected,
                "observed_test_count": observed,
                "passed": passed and observed == expected,
            }
        )
    test_count = sum(item["observed_test_count"] for item in suites)
    head = common._git("rev-parse", "HEAD")
    remote = common._git("rev-parse", "target/main")
    clean = common._git("status", "--porcelain") == ""
    tracked = all(common._tracked(path) for path in SOURCES)
    watchers = [
        {
            "pid": pid,
            "start_ticks": ticks,
            "marker": marker,
            "identity_valid": common._watcher(pid, ticks, marker),
        }
        for pid, ticks, marker in common.EXPECTED_WATCHERS
    ]
    parent_valid = _parent_valid()
    implementation_valid = _implementation_valid()
    lease_inactive = common._lease_inactive()
    findings: list[str] = []
    if head != remote:
        findings.append("v24669_source_commit_not_pushed")
    if not clean:
        findings.append("v24669_source_worktree_not_clean")
    if not tracked:
        findings.append("v24669_source_not_tracked")
    if not parent_valid:
        findings.append("v24667_no_go_diagnosis_drifted")
    if not implementation_valid:
        findings.append("v24668_information_gain_contract_drifted")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24655_59_61_68_69_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_runtime_field_access")
    if imports:
        findings.append("evaluator_import_in_runtime")
    if secret_hits:
        findings.append("credential_literal_in_build_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")

    value = {
        "artifact_version": 1,
        "role": "v24669_information_gain_acquisition_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {
            "v24667_diagnosis_path": str(PARENT),
            "v24667_diagnosis_sha256": common._sha256(PARENT),
            "valid": parent_valid,
            "task_trace_reopened_by_audit": False,
        },
        "mechanism": {
            "runtime_policy": runtime.POLICY_ID,
            "selected_unknown_target_cap": 1,
            "targeted_fetch_cap_concentrated_on_one_target": 4,
            "total_model_query_fetch_caps": [3, 4, 10],
            "visible_title_and_normalized_url_path_priority": True,
            "query_text_cannot_self_prove_alignment": True,
            "localization_information_gain_family": "uniform_source_subset_log_ratio_nats",
            "information_gain_routes_only_prefetch_acquisition": True,
            "fetched_page_text_remains_only_active_evidence": True,
            "minimum_independent_local_exact_support_sources": 2,
            "proposal_value_changed": False,
            "support_threshold_relaxed": False,
            "positive_epistemic_action_credit_can_be_assigned": True,
            "positive_decision_credit_before_safe_change_and_outer_utility": False,
            "implementation_valid": implementation_valid,
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
            "test_count": test_count,
            "passed": all(item["passed"] for item in suites)
            and test_count == EXPECTED_TEST_COUNT,
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
        },
        "label_blind_audit": {
            "runtime_input_contract": ["opaque_id", "question"],
            "privileged_runtime_field_accesses": sorted(accesses),
            "evaluator_imports": sorted(imports),
            "credential_literal_hits": sorted(secret_hits),
            "passed": not accesses and not imports and not secret_hits,
        },
        "runtime_state": {
            "protected_watchers": watchers,
            "protected_watchers_unchanged": all(
                item["identity_valid"] for item in watchers
            ),
            "shared_api_lease_inactive": lease_inactive,
            "external_population_launched_by_audit": False,
            "benchmark_launched_by_audit": False,
            "evaluator_called_by_audit": False,
        },
        "source_policy": {
            "mapping_gold_provenance_category_split_score_or_evaluator_read": False,
            "task_question_query_url_page_prediction_or_provider_payload_opened_by_audit": False,
            "remote_network_model_search_fetch_process_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_nonoverlapping_external_protocol_design": not findings,
            "fresh_external_activation_or_launch": False,
            "evaluator": False,
            "dev64_design_or_launch": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24669_information_gain_acquisition_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("parent", {}).get("valid") is not True
        or copied.get("mechanism", {}).get("implementation_valid") is not True
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("tests", {}).get("test_count") != EXPECTED_TEST_COUNT
        or copied.get("label_blind_audit", {}).get("passed") is not True
        or copied.get("runtime_state", {}).get("shared_api_lease_inactive") is not True
        or copied.get("authorization")
        != {
            "fresh_nonoverlapping_external_protocol_design": True,
            "fresh_external_activation_or_launch": False,
            "evaluator": False,
            "dev64_design_or_launch": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.69 build audit drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    value = build_audit()
    validate_audit(value)
    publish_new(ROOT / AUDIT, value)
    print(
        json.dumps(
            {
                "path": str(AUDIT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "test_count": value["tests"]["test_count"],
            },
            sort_keys=True,
        )
    )
