#!/usr/bin/env python3
"""Clean-build audit for the V2.46.55 no-entropy strong baseline.

The audit reads only tracked repository source, the sealed aggregate-only
V2.46.54 post-result audit, Git state, two protected watcher identities, and
the shared lease.  It performs no network, model, search, fetch, benchmark, or
evaluator effect and opens no task, question, query, URL, page, prediction,
mapping, gold, score, or credential.
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from deepwide_agent import v24655_unknown_cell_targeted_runtime as runtime  # noqa: E402
from scripts import audit_v24495_targeted_conversion_projection_build as common  # noqa: E402


DATE = "20260806"
PARENT = Path(
    f"results/v24654_v24651_unknown_target_structured_postresult_audit_v1_{DATE}.json"
)
AUDIT = Path(f"results/v24656_unknown_cell_targeted_build_audit_v1_{DATE}.json")
SOURCES = (
    PARENT,
    Path("src/deepwide_agent/v24325_shared_prefix_revision_runtime.py"),
    Path("src/deepwide_agent/v24637_objective_alignment_runtime.py"),
    Path("src/deepwide_agent/v24644_primary_identity_pair_runtime.py"),
    Path("src/deepwide_agent/v24655_unknown_cell_targeted_runtime.py"),
    Path("tests/test_v24655_unknown_cell_targeted_runtime.py"),
    Path("scripts/audit_v24656_unknown_cell_targeted_build.py"),
    Path("tests/test_audit_v24656_unknown_cell_targeted_build.py"),
)
RUNTIME_SOURCES = SOURCES[1:5]
TEST_SUITES = (
    (Path("tests/test_v24323_shared_prefix_cell_entropy.py"), 8, 120),
    (Path("tests/test_v24325_shared_prefix_revision_runtime.py"), 13, 180),
    (Path("tests/test_v24286_visible_schema_runtime.py"), 6, 120),
    (Path("tests/test_v24648_unknown_target_structured_runtime.py"), 6, 120),
    (Path("tests/test_v24655_unknown_cell_targeted_runtime.py"), 8, 120),
    (Path("tests/test_audit_v24656_unknown_cell_targeted_build.py"), 6, 120),
)
EXPECTED_TEST_COUNT = 47
DECISION_FUNCTIONS = frozenset(
    {
        "unknown_cell_targets",
        "_deterministic_support_admission",
        "_gate_unknown_candidate",
    }
)
FORBIDDEN_DECISION_CALLS = frozenset(
    {
        "_cell_admission",
        "admit_reserve_evidence",
        "validate_admission_receipt",
        "entropy_nats",
        "kl_nats",
        "beta_expected_information_gain",
        "_shadow_entropy",
    }
)


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(common._ordinary(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.56 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = _read(PARENT)
    authorization = value.get("authorization", {})
    findings = value.get("findings")
    return (
        value.get("role")
        == "v24654_v24651_unknown_target_structured_postresult_audit"
        and _sealed(value, "audit_sha256")
        and value.get("audit_valid") is True
        and findings == []
        and authorization.get("fresh_dev64_design") is True
        and authorization.get("fresh_dev64_launch") is False
        and authorization.get("new_exact220") is False
        and authorization.get("leaderboard_or_sota") is False
        and value.get("gold_or_provenance_opened_or_hashed_by_postresult_audit")
        is False
        and value.get(
            "network_model_search_fetch_or_official_benchmark_evaluator_called_by_audit"
        )
        is False
        and re.fullmatch(r"[0-9a-f]{64}", str(value.get("result_sha256", "")))
        is not None
    )


def _decision_dependency_findings() -> list[str]:
    path = Path("src/deepwide_agent/v24655_unknown_cell_targeted_runtime.py")
    tree = ast.parse(common._ordinary(path).read_text(encoding="utf-8"))
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    findings: list[str] = []
    for name in sorted(DECISION_FUNCTIONS):
        function = functions.get(name)
        if function is None:
            findings.append(f"missing:{name}")
            continue
        for node in ast.walk(function):
            called: str | None = None
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    called = node.func.attr
            if called in FORBIDDEN_DECISION_CALLS:
                findings.append(f"{path}:{node.lineno}:{name}:{called}")
    gate = functions.get("_gate_unknown_candidate")
    gate_calls: set[str] = set()
    if gate is not None:
        gate_calls = {
            node.func.id
            for node in ast.walk(gate)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
    if "_deterministic_support_admission" not in gate_calls:
        findings.append("gate_missing_deterministic_support_admission")
    return sorted(findings)


def _implementation_valid() -> bool:
    baseline = """```markdown
| Product | Release Date | Maker |
| --- | --- | --- |
| Alpha Phone | Unknown | Acme |
| Beta Phone | 2020 | Unknown |
```"""
    proposed = baseline.replace(
        "| Alpha Phone | Unknown | Acme |",
        "| Alpha Phone | 2024-09-20 | Acme |",
    )
    targets = runtime.unknown_cell_targets(baseline)
    pages = [
        {
            "evidence_id": f"R{index:04d}",
            "host": f"source-{index}.example",
            "title": "",
            "url": f"https://source-{index}.example/record",
            "content": "Alpha Phone official record Release Date 2024-09-20",
        }
        for index in (1, 2)
    ]
    candidate, admissions, counts = runtime._gate_unknown_candidate(
        baseline=baseline,
        proposed=proposed,
        evidence_declarations=[
            {
                "row_key": "Alpha Phone",
                "column": "Release Date",
                "evidence_ids": ["R0001", "R0002"],
            }
        ],
        targeted_pages=pages,
        targets=targets,
    )
    support = admissions[0].get("support_receipt", {}) if admissions else {}
    return (
        runtime.ARMS == ("baseline", "unknown_cell_targeted")
        and runtime.GENERIC_QUERY_CAP == 2
        and runtime.GENERIC_FETCH_CAP == 6
        and runtime.TARGET_CELL_CAP == 2
        and runtime.TARGET_QUERY_CAP == 2
        and runtime.TARGET_FETCH_CAP == 4
        and runtime.MINIMUM_INDEPENDENT_SUPPORT_SOURCES == 2
        and [(item["row_ordinal"], item["column_index"]) for item in targets]
        == [(0, 1), (1, 2)]
        and counts.get("admitted_cell_change_count") == 1
        and len(admissions) == 1
        and admissions[0].get("admitted") is True
        and support.get("deterministic_support_gate_passed") is True
        and support.get("entropy_information_gain_evaluator_or_task_credit_used")
        is False
        and "| Alpha Phone | 2024-09-20 | Acme |" in candidate
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    manifest = {str(path): common._sha256(path) for path in SOURCES}
    accesses: list[str] = []
    imports: list[str] = []
    for path in RUNTIME_SOURCES:
        current_accesses, current_imports = common.ast_findings(path)
        accesses.extend(current_accesses)
        imports.extend(current_imports)
    decision_findings = _decision_dependency_findings()
    secret_hits = [
        str(path)
        for path in SOURCES
        if common.SECRET.search(common._ordinary(path).read_text(encoding="utf-8"))
    ]
    suites = [
        {
            "path": str(path),
            "test_count": count,
            "passed": common._run_test(path, timeout),
        }
        for path, count, timeout in TEST_SUITES
    ]
    test_count = sum(item["test_count"] for item in suites)
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
        findings.append("v24656_source_commit_not_pushed")
    if not clean:
        findings.append("v24656_source_worktree_not_clean")
    if not tracked:
        findings.append("v24656_source_not_tracked")
    if not parent_valid:
        findings.append("v24654_parent_postresult_audit_drifted")
    if not implementation_valid:
        findings.append("v24655_implementation_contract_drifted")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24323_25_v24286_v24648_55_56_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_runtime_field_access")
    if imports:
        findings.append("evaluator_import_in_runtime")
    if decision_findings:
        findings.append("entropy_or_nondeterministic_dependency_in_decision_path")
    if secret_hits:
        findings.append("credential_literal_in_build_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")

    value = {
        "artifact_version": 1,
        "role": "v24656_unknown_cell_targeted_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {
            "v24654_postresult_audit_path": str(PARENT),
            "v24654_postresult_audit_sha256": common._sha256(PARENT),
            "valid": parent_valid,
            "fresh_dev64_design_authorized": parent_valid,
            "fresh_dev64_launch_authorized": False,
        },
        "mechanism": {
            "runtime_policy": runtime.POLICY_ID,
            "generic_query_cap": runtime.GENERIC_QUERY_CAP,
            "generic_fetch_cap": runtime.GENERIC_FETCH_CAP,
            "unknown_target_cell_cap": runtime.TARGET_CELL_CAP,
            "targeted_query_cap": runtime.TARGET_QUERY_CAP,
            "targeted_fetch_cap": runtime.TARGET_FETCH_CAP,
            "total_model_query_fetch_caps": [3, 4, 10],
            "baseline_precedes_target_selection": True,
            "target_selection_is_stable_row_major": True,
            "target_query_uses_only_visible_row_and_column": True,
            "candidate_changes_only_selected_unknown_cells": True,
            "minimum_independent_registrable_local_exact_sources": 2,
            "final_redirect_sources_deduplicated_and_generic_disjoint": True,
            "entropy_is_shadow_only": True,
            "positive_task_credit_assigned": False,
            "decision_dependency_findings": decision_findings,
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
            "privileged_runtime_field_accesses": sorted(accesses),
            "evaluator_imports": sorted(imports),
            "credential_literal_hits": sorted(secret_hits),
            "runtime_input_contract": ["opaque_id", "question"],
            "passed": not accesses and not imports and not secret_hits,
        },
        "runtime_state": {
            "protected_watchers": watchers,
            "protected_watchers_unchanged": all(
                item["identity_valid"] for item in watchers
            ),
            "shared_api_lease_inactive": lease_inactive,
            "benchmark_launched": False,
            "external_population_launched_by_audit": False,
            "evaluator_called": False,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "task_question_query_url_page_prediction_or_provider_payload_opened_by_audit": False,
            "remote_network_model_search_fetch_process_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_paired_dev64_protocol_design": not findings,
            "fresh_paired_dev64_activation_or_launch": False,
            "new_exact220": False,
            "evaluator_access": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    value = build_audit()
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
