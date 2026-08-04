#!/usr/bin/env python3
"""Content-free performance diagnosis for the V2.44.78 bounded gate.

The frozen V2.44.78 public receipts show that every recorded model, hosted
search, and public-fetch effect start has a matching finish, while all eight
workers still reached the hard worker cutoff.  The last content-free stages
place six workers after the parent runtime, one inside complete validation,
and one immediately after a fetch effect.  This report combines those public
facts with a local *synthetic* cProfile of the already-frozen V2.44.76 full
chain test.

The profile contains no benchmark or external-task content.  It has profiling
overhead and is not an estimate of provider, search, fetch, benchmark, or
external latency.  It is used only to identify repeated local semantic replay,
deep-copy, and hashing work.  The report authorizes append-only local design;
it does not authorize another external population, a V2.44.78 rerun, dev64,
exact-220, evaluator access, or a leaderboard claim.
"""

from __future__ import annotations

import json
import math
import os
import pstats
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
from scripts import v24478_bounded_adaptive_external_gate as gate  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


DATE = "20260804"
REPORT = Path(
    f"results/v24479_v24478_post_effect_validation_diagnosis_v1_{DATE}.json"
)
RESULT = gate.RESULT
DECISION = gate.DECISION
POSTAUDIT = gate.POSTAUDIT
PROFILE = Path("outputs/v24478_local_full_chain_profile.prof")
UNPROFILED_BUILD_AUDIT = Path(
    "results/v24477_bounded_nominal_integration_build_audit_v1_20260804.json"
)
PROFILED_TEST_SOURCE = Path(
    "tests/test_v24476_bounded_nominal_search_integration.py"
)
DIAGNOSIS_SOURCE = Path(
    "scripts/diagnose_v24479_v24478_post_effect_validation.py"
)
TEST_SOURCE = Path(
    "tests/test_diagnose_v24479_v24478_post_effect_validation.py"
)
SOURCES = (
    PROFILED_TEST_SOURCE,
    Path("src/deepwide_agent/v24457_adaptive_entropy_support.py"),
    Path("src/deepwide_agent/v24470_bounded_adaptive_integration.py"),
    DIAGNOSIS_SOURCE,
    TEST_SOURCE,
)
EXPECTED_WATCHERS = base.EXPECTED_WATCHERS
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)
EXPECTED_PROFILE_SHA256 = (
    "4e0421fc0d034fbeee02ba7aa2b03e24ab957443387dc6f1284211f7ae310c6e"
)
EXPECTED_PROFILE_TOTAL_CALLS = 199_890_631
EXPECTED_PROFILE_PRIMITIVE_CALLS = 181_785_197
EXPECTED_VALIDATE_RESULT_CALLS = 11_303
EXPECTED_DEEPCOPY_CALLS = 16_788_412
EXPECTED_PAYLOAD_SHA256_CALLS = 574_063
REMOTE_EFFECT_DEADLINE_SECONDS = 150.0
FROZEN_WORKER_TIMEOUT_SECONDS = 175.0
FROZEN_LOCAL_RESERVE_SECONDS = 25.0
DESIGN_WORKER_TIMEOUT_SECONDS = 220.0
DESIGN_PARENT_TIMEOUT_SECONDS = 245.0
DESIGN_BATCH_CEILING_SECONDS = 255.0


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(base._ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.44.79 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _validate_parents() -> tuple[dict[str, Any], dict[str, Any]]:
    result = gate.validate_public_result(_read(RESULT))
    decision = gate.validate_decision(ROOT, value=_read(DECISION))
    audit = gate.validate_postaudit(ROOT, value=_read(POSTAUDIT))
    build = _read(UNPROFILED_BUILD_AUDIT)
    supervision = result.get("supervision_aggregate") or {}
    timing = result.get("stage_timing_aggregate") or {}
    suites = build.get("tests", {}).get("suites", [])
    local_suite = next(
        (
            item
            for item in suites
            if item.get("path") == str(PROFILED_TEST_SOURCE)
        ),
        None,
    )
    if (
        result.get("selected") != 8
        or result.get("batch_wall_seconds") != 175.400464
        or result.get("effect_deadline_seconds") != 150
        or result.get("worker_timeout_seconds") != 175
        or result.get("parent_timeout_seconds") != 200
        or result.get("passed") is not False
        or result.get("diagnostic_complete") is not False
        or supervision.get("worker_success_tasks") != 0
        or supervision.get("worker_hard_timeout_tasks") != 8
        or supervision.get("worker_nonzero_tasks") != 0
        or supervision.get("checkpoint_chain_valid_tasks") != 8
        or supervision.get("last_stage_counts")
        != {
            "adaptive_support_entered": 6,
            "complete_validation_entered": 1,
            "public_fetch_effect_finished": 1,
        }
        or supervision.get("model_effect_started_lower_bound") != 16
        or supervision.get("model_effect_finished_lower_bound") != 16
        or supervision.get("hosted_search_effect_started_lower_bound") != 24
        or supervision.get("hosted_search_effect_finished_lower_bound") != 24
        or supervision.get("public_fetch_effect_started_lower_bound") != 87
        or supervision.get("public_fetch_effect_finished_lower_bound") != 87
        or supervision.get("complete_validation_entered_tasks") != 1
        or supervision.get("complete_validation_returned_tasks") != 0
        or timing.get("parent_success_tasks") != 0
        or timing.get("parent_failure_tasks") != 8
        or decision.get("status") != "fresh_bounded_adaptive_external_no_go"
        or decision.get("diagnostic_route") != "bounded_worker_stage_successor"
        or decision.get("authorization", {}).get("diagnostic_successor_design")
        is not True
        or decision.get("authorization", {}).get("new_exact220") is not False
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("shared_api_lease_active") is not False
        or build.get("audit_valid") is not True
        or build.get("findings") != []
        or not isinstance(local_suite, Mapping)
        or local_suite.get("passed") is not True
        or local_suite.get("return_code") != 0
        or local_suite.get("test_count") != 2
        or local_suite.get("elapsed_seconds") != 26.628652
        or not _sealed(result, "result_payload_sha256")
        or not _sealed(decision, "decision_payload_sha256")
        or not _sealed(audit, "audit_payload_sha256")
        or not _sealed(build, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.44.79 parent closure drifted")
    return result, build


def _profile_path() -> Path:
    path = ROOT / PROFILE
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT)
    ):
        raise RuntimeError("V2.44.79 synthetic profile is absent")
    return path


def _profile_stat(
    stats: pstats.Stats, *, basename: str, function: str
) -> tuple[int, int, float, float]:
    matches = [
        value
        for (filename, _line, name), value in stats.stats.items()
        if Path(filename).name == basename and name == function
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"V2.44.79 expected one profile stat for {basename}:{function}"
        )
    primitive, total, inline, cumulative, _callers = matches[0]
    return int(primitive), int(total), float(inline), float(cumulative)


def _aggregate_function(
    stats: pstats.Stats, *, function: str
) -> dict[str, Any]:
    matches = [
        (filename, line, value)
        for (filename, line, name), value in stats.stats.items()
        if name == function
    ]
    return {
        "function_definition_count": len(matches),
        "primitive_calls": sum(int(value[0]) for _, _, value in matches),
        "total_calls": sum(int(value[1]) for _, _, value in matches),
        "inline_seconds_sum": round(
            sum(float(value[2]) for _, _, value in matches), 6
        ),
        "nested_cumulative_seconds_sum_nonadditive": round(
            sum(float(value[3]) for _, _, value in matches), 6
        ),
    }


def _synthetic_profile_evidence() -> dict[str, Any]:
    path = _profile_path()
    stats = pstats.Stats(str(path))
    test = _profile_stat(
        stats,
        basename=PROFILED_TEST_SOURCE.name,
        function="test_full_frozen_chain_succeeds_with_hard_request_and_certificate",
    )
    stage = _profile_stat(
        stats,
        basename="v24470_bounded_adaptive_integration.py",
        function="run_stage_hooked_single_validation",
    )
    runtime = _profile_stat(
        stats,
        basename="v24457_adaptive_entropy_support.py",
        function="run_v24457_task",
    )
    cross = _profile_stat(
        stats,
        basename="v24457_adaptive_entropy_support.py",
        function="validate_cross_artifacts",
    )
    adaptive_validate = _profile_stat(
        stats,
        basename="v24457_adaptive_entropy_support.py",
        function="validate_result",
    )
    deepcopy = _profile_stat(stats, basename="copy.py", function="deepcopy")
    digest = _profile_stat(
        stats,
        basename="v24323_shared_prefix_cell_entropy.py",
        function="payload_sha256",
    )
    validate_aggregate = _aggregate_function(stats, function="validate_result")
    compute_aggregate = _aggregate_function(stats, function="_compute_result")
    cross_aggregate = _aggregate_function(stats, function="validate_cross_artifacts")
    return {
        "scope": "one_local_synthetic_full_frozen_chain_unittest_under_cprofile",
        "path": str(PROFILE),
        "sha256": sha256(path),
        "total_profiled_seconds": round(float(stats.total_tt), 6),
        "total_calls": int(stats.total_calls),
        "primitive_calls": int(stats.prim_calls),
        "profiled_test_total_calls": test[1],
        "profiled_test_cumulative_seconds": round(test[3], 6),
        "stage_hooked_validation_total_calls": stage[1],
        "stage_hooked_validation_cumulative_seconds": round(stage[3], 6),
        "adaptive_runtime_total_calls": runtime[1],
        "adaptive_runtime_cumulative_seconds": round(runtime[3], 6),
        "adaptive_cross_validation_total_calls": cross[1],
        "adaptive_cross_validation_cumulative_seconds": round(cross[3], 6),
        "adaptive_result_validation_total_calls": adaptive_validate[1],
        "adaptive_result_validation_cumulative_seconds": round(
            adaptive_validate[3], 6
        ),
        "validate_result_aggregate": validate_aggregate,
        "compute_result_aggregate": compute_aggregate,
        "cross_artifact_validation_aggregate": cross_aggregate,
        "deepcopy_primitive_calls": deepcopy[0],
        "deepcopy_total_calls": deepcopy[1],
        "deepcopy_cumulative_seconds": round(deepcopy[3], 6),
        "payload_sha256_total_calls": digest[1],
        "payload_sha256_cumulative_seconds": round(digest[3], 6),
        "contains_profile_function_names_and_aggregate_counts_only": True,
        "task_question_opaque_id_query_url_page_prediction_or_value_emitted": False,
        "benchmark_or_external_task_content_used": False,
        "network_model_search_fetch_or_evaluator_called_by_diagnosis": False,
        "profile_has_instrumentation_overhead": True,
        "profile_is_not_external_latency_estimate": True,
    }


def _profile_valid(value: Mapping[str, Any]) -> bool:
    validate_aggregate = value.get("validate_result_aggregate")
    return (
        value.get("sha256") == EXPECTED_PROFILE_SHA256
        and value.get("total_calls") == EXPECTED_PROFILE_TOTAL_CALLS
        and value.get("primitive_calls") == EXPECTED_PROFILE_PRIMITIVE_CALLS
        and value.get("profiled_test_total_calls") == 1
        and value.get("stage_hooked_validation_total_calls") == 1
        and value.get("adaptive_runtime_total_calls") == 1
        and value.get("adaptive_cross_validation_total_calls") == 1
        and value.get("adaptive_result_validation_total_calls") == 1
        and isinstance(validate_aggregate, Mapping)
        and validate_aggregate.get("total_calls") == EXPECTED_VALIDATE_RESULT_CALLS
        and value.get("deepcopy_total_calls") == EXPECTED_DEEPCOPY_CALLS
        and value.get("payload_sha256_total_calls")
        == EXPECTED_PAYLOAD_SHA256_CALLS
        and value.get("profile_has_instrumentation_overhead") is True
        and value.get("profile_is_not_external_latency_estimate") is True
        and value.get("benchmark_or_external_task_content_used") is False
        and value.get("network_model_search_fetch_or_evaluator_called_by_diagnosis")
        is False
    )


def build_report(*, now: int | None = None) -> dict[str, Any]:
    result, build = _validate_parents()
    supervision = result["supervision_aggregate"]
    profile = _synthetic_profile_evidence()
    local_suite = next(
        item
        for item in build["tests"]["suites"]
        if item["path"] == str(PROFILED_TEST_SOURCE)
    )
    unprofiled_seconds = float(local_suite["elapsed_seconds"])
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
    if not _profile_valid(profile):
        findings.append("synthetic_profile_identity_or_counter_drifted")
    if head != remote:
        findings.append("v24479_source_commit_not_pushed")
    if not clean:
        findings.append("v24479_worktree_not_clean")
    if not tracked:
        findings.append("v24479_source_not_tracked")
    if watchers != EXPECTED_WATCHERS:
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if secret_hits:
        findings.append("credential_literal_in_v24479_surface")
    valid = not findings
    value = {
        "artifact_version": 1,
        "role": "v24479_v24478_post_effect_validation_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "result": {"path": str(RESULT), "sha256": sha256(base._ordinary(RESULT))},
            "decision": {
                "path": str(DECISION),
                "sha256": sha256(base._ordinary(DECISION)),
            },
            "postaudit": {
                "path": str(POSTAUDIT),
                "sha256": sha256(base._ordinary(POSTAUDIT)),
            },
            "unprofiled_build_audit": {
                "path": str(UNPROFILED_BUILD_AUDIT),
                "sha256": sha256(base._ordinary(UNPROFILED_BUILD_AUDIT)),
            },
        },
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "public_observation": {
            "selected": 8,
            "batch_wall_seconds": result["batch_wall_seconds"],
            "worker_success_tasks": supervision["worker_success_tasks"],
            "worker_hard_timeout_tasks": supervision["worker_hard_timeout_tasks"],
            "checkpoint_chain_valid_tasks": supervision[
                "checkpoint_chain_valid_tasks"
            ],
            "last_stage_counts": supervision["last_stage_counts"],
            "model_effect_started_lower_bound": supervision[
                "model_effect_started_lower_bound"
            ],
            "model_effect_finished_lower_bound": supervision[
                "model_effect_finished_lower_bound"
            ],
            "hosted_search_effect_started_lower_bound": supervision[
                "hosted_search_effect_started_lower_bound"
            ],
            "hosted_search_effect_finished_lower_bound": supervision[
                "hosted_search_effect_finished_lower_bound"
            ],
            "public_fetch_effect_started_lower_bound": supervision[
                "public_fetch_effect_started_lower_bound"
            ],
            "public_fetch_effect_finished_lower_bound": supervision[
                "public_fetch_effect_finished_lower_bound"
            ],
            "complete_validation_entered_tasks": supervision[
                "complete_validation_entered_tasks"
            ],
            "complete_validation_returned_tasks": supervision[
                "complete_validation_returned_tasks"
            ],
            "all_recorded_network_effect_starts_equal_finishes": (
                supervision["model_effect_started_lower_bound"]
                == supervision["model_effect_finished_lower_bound"]
                and supervision["hosted_search_effect_started_lower_bound"]
                == supervision["hosted_search_effect_finished_lower_bound"]
                and supervision["public_fetch_effect_started_lower_bound"]
                == supervision["public_fetch_effect_finished_lower_bound"]
            ),
        },
        "synthetic_profile": profile,
        "budget_evidence": {
            "remote_effect_deadline_seconds": REMOTE_EFFECT_DEADLINE_SECONDS,
            "frozen_worker_timeout_seconds": FROZEN_WORKER_TIMEOUT_SECONDS,
            "frozen_local_closure_reserve_seconds": FROZEN_LOCAL_RESERVE_SECONDS,
            "unprofiled_synthetic_full_chain_suite_seconds": unprofiled_seconds,
            "unprofiled_suite_exceeds_frozen_reserve_seconds": round(
                unprofiled_seconds - FROZEN_LOCAL_RESERVE_SECONDS, 6
            ),
            "profiled_to_unprofiled_suite_ratio_with_instrumentation_overhead": round(
                float(profile["total_profiled_seconds"]) / unprofiled_seconds, 6
            ),
            "design_worker_timeout_seconds": DESIGN_WORKER_TIMEOUT_SECONDS,
            "design_local_reserve_seconds": (
                DESIGN_WORKER_TIMEOUT_SECONDS - REMOTE_EFFECT_DEADLINE_SECONDS
            ),
            "design_parent_timeout_seconds": DESIGN_PARENT_TIMEOUT_SECONDS,
            "design_parent_reserve_seconds": (
                DESIGN_PARENT_TIMEOUT_SECONDS - DESIGN_WORKER_TIMEOUT_SECONDS
            ),
            "design_batch_ceiling_seconds": DESIGN_BATCH_CEILING_SECONDS,
            "design_values_are_local_successor_hypotheses_not_launch_authority": True,
        },
        "diagnosis": {
            "public_receipts_prove_balanced_recorded_network_effect_boundaries": True,
            "public_receipts_localize_all_terminal_failures_to_worker_hard_cutoff": True,
            "public_receipts_show_post_parent_or_validation_progress_for_seven_tasks": True,
            "synthetic_profile_proves_repeated_nested_semantic_validation_is_a_local_hot_path": True,
            "synthetic_profile_proves_large_deepcopy_and_hash_work": True,
            "frozen_25_second_post_effect_reserve_is_not_supported_by_local_full_chain_evidence": True,
            "private_v24478_traceback_or_per_task_timing_available": False,
            "local_replay_is_proven_as_unique_v24478_timeout_cause": False,
            "profile_is_external_latency_estimate": False,
            "same_v24478_population_rerun_allowed": False,
        },
        "source_policy": {
            "runtime_input_keys_exactly_opaque_id_and_question": True,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
            "profile_contains_synthetic_function_counts_only": True,
            "network_model_search_fetch_or_evaluator_called_by_diagnosis": False,
        },
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
            "active_run_killed_or_quarantined": False,
        },
        "credential_literal_hits": secret_hits,
        "findings": findings,
        "diagnosis_valid": valid,
        "authorization": {
            "append_only_local_validation_performance_design": valid,
            "separate_remote_effect_and_local_validation_budget_design": valid,
            "local_synthetic_equivalence_and_timing_tests": valid,
            "same_v24478_population_rerun": False,
            "external_probe_launch": False,
            "paired_dev64": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return value


def validate_report(value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(REPORT)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    valid = copied.get("findings") == []
    public = copied.get("public_observation")
    profile = copied.get("synthetic_profile")
    budget = copied.get("budget_evidence")
    diagnosis = copied.get("diagnosis")
    authorization = copied.get("authorization")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role")
        != "v24479_v24478_post_effect_validation_diagnosis"
        or copied.get("diagnosis_valid") is not valid
        or not isinstance(public, Mapping)
        or public.get("worker_hard_timeout_tasks") != 8
        or public.get("all_recorded_network_effect_starts_equal_finishes") is not True
        or public.get("complete_validation_returned_tasks") != 0
        or not isinstance(profile, Mapping)
        or not _profile_valid(profile)
        or not isinstance(budget, Mapping)
        or budget.get("frozen_local_closure_reserve_seconds") != 25.0
        or budget.get("unprofiled_synthetic_full_chain_suite_seconds")
        != 26.628652
        or budget.get("design_worker_timeout_seconds") != 220.0
        or budget.get("design_parent_timeout_seconds") != 245.0
        or budget.get("design_batch_ceiling_seconds") != 255.0
        or budget.get(
            "design_values_are_local_successor_hypotheses_not_launch_authority"
        )
        is not True
        or not isinstance(diagnosis, Mapping)
        or diagnosis.get(
            "public_receipts_prove_balanced_recorded_network_effect_boundaries"
        )
        is not True
        or diagnosis.get(
            "synthetic_profile_proves_repeated_nested_semantic_validation_is_a_local_hot_path"
        )
        is not True
        or diagnosis.get("private_v24478_traceback_or_per_task_timing_available")
        is not False
        or diagnosis.get("local_replay_is_proven_as_unique_v24478_timeout_cause")
        is not False
        or diagnosis.get("profile_is_external_latency_estimate") is not False
        or diagnosis.get("same_v24478_population_rerun_allowed") is not False
        or copied.get("source_manifest_sha256")
        != payload_sha256(copied.get("source_manifest"))
        or not isinstance(authorization, Mapping)
        or authorization.get("append_only_local_validation_performance_design")
        is not valid
        or authorization.get("separate_remote_effect_and_local_validation_budget_design")
        is not valid
        or authorization.get("local_synthetic_equivalence_and_timing_tests")
        is not valid
        or authorization.get("same_v24478_population_rerun") is not False
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
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.44.79 diagnosis drifted")
    return copied


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
