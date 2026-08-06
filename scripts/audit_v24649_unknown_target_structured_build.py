#!/usr/bin/env python3
"""Clean-build audit for the V2.46.48 unknown-target structured lookup.

The audit reads repository sources, the sealed aggregate-only V2.46.47
diagnosis, Git state, two protected watcher identities, and the shared lease.
It performs no network, model, search, fetch, benchmark, or evaluator effect
and opens no task, question, query, URL, page, prediction, gold, or credential.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from deepwide_agent import v24648_unknown_target_structured_runtime as runtime  # noqa: E402
from scripts import audit_v24495_targeted_conversion_projection_build as common  # noqa: E402


DATE = "20260806"
PARENT = Path(f"results/v24647_v24645_zero_intervention_diagnosis_v1_{DATE}.json")
AUDIT = Path(f"results/v24649_unknown_target_structured_build_audit_v2_{DATE}.json")
SUPERSEDED = Path(
    f"results/v24649_unknown_target_structured_build_audit_v1_{DATE}.json"
)
SOURCES = (
    PARENT,
    Path("src/deepwide_agent/v24644_primary_identity_pair_runtime.py"),
    Path("src/deepwide_agent/v24648_unknown_target_structured_runtime.py"),
    Path("tests/test_v24648_unknown_target_structured_runtime.py"),
    Path("scripts/audit_v24649_unknown_target_structured_build.py"),
    Path("tests/test_audit_v24649_unknown_target_structured_build.py"),
)
RUNTIME_SOURCES = (SOURCES[1], SOURCES[2])
TEST_SUITES = (
    (Path("tests/test_v24640_evidence_constrained_runtime.py"), 11, 180),
    (Path("tests/test_v24642_deterministic_pair_runtime.py"), 14, 180),
    (Path("tests/test_v24644_primary_identity_pair_runtime.py"), 14, 180),
    (Path("tests/test_v24648_unknown_target_structured_runtime.py"), 6, 120),
    (Path("tests/test_audit_v24649_unknown_target_structured_build.py"), 5, 120),
)
EXPECTED_TEST_COUNT = 50


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(common._ordinary(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.49 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = _read(PARENT)
    next_step = value.get("next_falsification", {})
    authorization = value.get("authorization", {})
    return (
        value.get("role")
        == "v24647_v24645_zero_intervention_postfreeze_diagnosis"
        and _sealed(value, "diagnosis_sha256")
        and value.get("diagnosis", {}).get(
            "current_bottleneck_is_unknown_target_structured_pair_acquisition"
        )
        is True
        and next_step.get("treatment")
        == "unknown_target_directed_structured_primary_identity_acquisition"
        and next_step.get("strong_baseline")
        == "deterministic_official_registry_name_lookup_when_available"
        and next_step.get("same_total_model_query_fetch_budget") is True
        and next_step.get("unconditional_page_volume_increase") is False
        and next_step.get("mechanism_gate")
        == "at_least_one_identity_bound_unknown_target_intervention"
        and authorization.get("fresh_external_successor_design") is True
        and authorization.get("fresh_external_successor_launch") is False
        and authorization.get("dev64") is False
        and authorization.get("exact220") is False
    )


def _implementation_valid() -> bool:
    requests = runtime.unknown_target_lookup_requests(
        """```markdown
| Organization | ROR ID | Country code |
| --- | --- | --- |
| Alpha Institute | Unknown | GB |
| Beta Institute | 01abc2d34 | US |
| Gamma Institute | Unknown | DE |
| Delta Institute | Unknown | FR |
```""",
        ("Alpha Institute", "Beta Institute", "Gamma Institute", "Delta Institute"),
    )
    return (
        runtime.GENERIC_FETCH_CAP == 6
        and runtime.TARGETED_LOOKUP_CAP == 4
        and runtime.ARMS == ("baseline", "unknown_target_structured")
        and len(requests) == 3
        and [item["member_label"] for item in requests]
        == ["Alpha Institute", "Gamma Institute", "Delta Institute"]
        and all(
            str(item["url"]).startswith(
                "https://api.ror.org/v2/organizations?query.advanced="
            )
            and "filter=status%3Aactive" in str(item["url"])
            for item in requests
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
        findings.append("v24649_source_commit_not_pushed")
    if not clean:
        findings.append("v24649_source_worktree_not_clean")
    if not tracked:
        findings.append("v24649_source_not_tracked")
    if not parent_valid:
        findings.append("v24647_parent_diagnosis_drifted")
    if not implementation_valid:
        findings.append("v24648_implementation_contract_drifted")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24640_42_44_48_49_regression_failed_or_count_drifted")
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
        "role": "v24649_unknown_target_structured_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "supersedes": {
            "path": str(SUPERSEDED),
            "sha256": common._sha256(SUPERSEDED),
            "reason": "candidate_consumes_only_new_unknown_target_lookup_projection",
            "v1_authorizes_successor_use": False,
        },
        "parent": {
            "v24647_diagnosis_sha256": common._sha256(PARENT),
            "valid": parent_valid,
            "v24645_zero_effective_intervention": True,
            "same_v24645_population_retry_resume_or_revaluation_authorized": False,
        },
        "mechanism": {
            "generic_fetch_cap": runtime.GENERIC_FETCH_CAP,
            "unknown_target_lookup_cap": runtime.TARGETED_LOOKUP_CAP,
            "total_fetch_cap": 10,
            "provider_model_effect_cap": 2,
            "hosted_search_query_cap": 4,
            "baseline_precedes_unknown_target_selection": True,
            "official_ror_v2_exact_name_and_active_filter": True,
            "full_response_required_before_uniqueness_claim": True,
            "unique_normalized_ror_display_required": True,
            "nonunknown_ror_and_all_country_cells_immutable": True,
            "quality_cost_pareto_not_equal_effect_causal_ablation": True,
            "entropy_routes_forward_or_assigns_positive_credit": False,
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
            "network_model_search_fetch_or_evaluator_called": False,
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
            "fresh_external_population_and_protocol_design": not findings,
            "fresh_external_activation_or_launch": False,
            "same_v24645_population_retry_resume_or_revaluation": False,
            "paired_dev64_or_exact220": False,
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
