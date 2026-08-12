#!/usr/bin/env python3
"""Build, authorize, and audit the V2.52.06 quality gate."""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25110_exact_visible_schema as parser_impl  # noqa: E402
from deepwide_agent import (  # noqa: E402
    v25196_vertical_receipt_invariant_observer as invariant_observer,
)
from deepwide_agent import (  # noqa: E402
    v25200_post_effect_tolerant_vertical_receipt as compatibility,
)
from deepwide_agent import (  # noqa: E402
    v25206_cran_dcf_quality_contract as contract,
)
from deepwide_agent import v25204_cran_dcf_parser as dcf_parser  # noqa: E402
from scripts import control_v25199_invariant_observable_quality as parent_control  # noqa: E402
from scripts import run_v25206_cran_dcf_quality as runner  # noqa: E402


TEST_SUITES = (
    ("test_v25206_cran_dcf_quality.py", 7),
    ("test_v25204_cran_dcf_parser.py", 6),
    ("test_diagnose_v25205_v25203_evaluator_invalid.py", 2),
    ("test_audit_v25206_cran_dcf_quality_population_selection.py", 3),
    ("test_v25200_post_effect_tolerant_vertical_receipt.py", 21),
    *parent_control.TEST_SUITES,
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)


def _bind_parent() -> None:
    parent_control.contract = contract
    parent_control.runner = runner
    parent_control._bind_parent()


def _publish(relative: Path, value: Mapping[str, Any]) -> None:
    _bind_parent()
    parent_control._publish(relative, value)


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    _bind_parent()
    return parent_control._read(relative, tracked=tracked)


def _clean_pushed() -> tuple[str, str]:
    _bind_parent()
    return parent_control._clean_pushed()


def _lease_inactive() -> bool:
    _bind_parent()
    return parent_control._lease_inactive()


def _endpoint_reachable() -> bool:
    return parent_control._endpoint_reachable()


def _active_conflicts() -> list[int]:
    _bind_parent()
    return parent_control._active_conflicts()


def _test(pattern: str, expected: int) -> dict[str, Any]:
    _bind_parent()
    return parent_control._test(pattern, expected)


def _tests() -> dict[str, Any]:
    suites = [_test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS
        and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _semantic_audit() -> dict[str, Any]:
    _bind_parent()
    return parent_control._semantic_audit()


def _future_pristine(paths: tuple[Path, ...]) -> bool:
    return parent_control._future_pristine(paths)


def _recursive_keys(value: object) -> set[str]:
    return parent_control._recursive_keys(value)


def _selection_valid(*, tracked: bool) -> bool:
    value = contract.validate_selection(ROOT, tracked=tracked)
    return bool(
        value["audit_valid"] is True
        and value["findings"] == []
        and value["identity_history_zero_hit_count"] == contract.TASK_COUNT
        and value["ordered_identity_vector_sha256"]
        == contract.IDENTITY_SELECTION_SHA256
        and value[
            "preselection_requires_license_literal_pipe_and_nonempty_needs_compilation"
        ]
        is True
        and value["preselection_is_unconditional_natural_population"] is False
        and value["v25195_population_reuse"] is False
        and value["v25199_population_reuse"] is False
        and value["v25203_population_reuse"] is False
        and value["prior_external_population_reuse"] is False
    )


def _diagnosis_valid(*, tracked: bool) -> bool:
    value = contract._validate_diagnosis(ROOT, tracked=tracked)
    return bool(
        value["audit_valid"] is True
        and value["findings"] == []
        and value["diagnosis"][
            "v25203_quality_outcome_is_evaluator_invalid_not_model_no_go"
        ]
        is True
        and value["diagnosis"]["actual_failed_stage_is_unidentified_due_to_catch_all"]
        is True
        and value["diagnosis"][
            "old_parser_bug_is_plausible_but_not_proven_unique_cause_of_network_run"
        ]
        is True
        and value["authorization"]["fresh_disjoint_quality_successor_design"]
        is True
        and value["authorization"][
            "same_population_refetch_revalue_retry_resume_or_replacement"
        ]
        is False
    )


def _expected_manifest() -> set[str]:
    return {
        *(str(path) for path in contract.forward_dependency_closure(ROOT)),
        str(contract.CONTROL),
        str(contract.TEST),
        str(contract.COMPATIBILITY_TEST),
        str(contract.DCF_PARSER),
        str(contract.DCF_PARSER_TEST),
        str(contract.SELECTION_SOURCE),
        str(contract.SELECTION_TEST),
        str(contract.SELECTION_AUDIT),
        str(contract.DIAGNOSIS),
        str(contract.DIAGNOSIS_SOURCE),
        str(contract.DIAGNOSIS_TEST),
    }


def build_audit(
    *, now: int | None = None, require_clean: bool = True
) -> dict[str, Any]:
    head, target = (
        _clean_pushed() if require_clean else ("build-only", "build-only")
    )
    manifest = contract.dependency_manifest(ROOT, tracked=require_clean)
    tests = _tests()
    semantic = _semantic_audit()
    future = (
        contract.BUILD_AUDIT,
        contract.PROTOCOL,
        contract.PREAUDIT,
        contract.EXECUTION_START,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.EVALUATOR,
        contract.EVALUATOR_TEST,
        contract.EVALUATOR_PROTOCOL,
        contract.RESULT,
        contract.POSTAUDIT,
        contract.OUTPUT_ROOT,
    )
    tasks = contract.task_vector()
    policy = contract.source_policy()
    gate = contract.mechanism_gate()
    quality = contract.quality_gate()
    checks = {
        "fresh_dcf_quality_population_bound": _selection_valid(
            tracked=require_clean
        ),
        "frozen_evaluator_invalid_diagnosis_bound": _diagnosis_valid(
            tracked=require_clean
        ),
        "focused_and_complete_parent_tests_exact": tests["passed"],
        "source_manifest_complete": set(manifest) == _expected_manifest(),
        "privileged_runtime_field_access_zero": not semantic[
            "privileged_runtime_field_accesses"
        ],
        "evaluator_capability_absent": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "future_forward_evaluator_and_quality_surfaces_absent": _future_pristine(
            future
        ),
        "protected_watchers_exact": contract.watcher_snapshot()
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in contract.EXPECTED_WATCHERS
        ],
        "shared_api_lease_inactive": _lease_inactive(),
        "natural_visible_tasks_exact_four_columns": len(tasks) == 20
        and all(
            parser_impl.extract_exact_visible_columns(task["question"])
            == list(contract.COLUMNS)
            and r"\|" not in task["question"]
            and "https://" not in task["question"]
            for task in tasks
        ),
        "fixed_concurrency_and_caps": contract.EXECUTOR_CONCURRENCY == 20
        and contract.MODEL_SLOT_CAP == 8
        and contract.LIMITS == parent_control.parent_control.contract.LIMITS,
        "fixed_terminal_effect_denominator": gate[
            "exact_physical_queries_total"
        ]
        == 80
        and gate["maximum_physical_fetches_total"] == 280,
        "exact_compatibility_is_behavior_preserving_and_isolated": policy[
            "exact_post_effect_compatibility_only_after_frozen_v25158_rejection"
        ]
        is True
        and policy[
            "compatibility_surrogate_changes_only_parent_post_effect_flag"
        ]
        is True
        and policy[
            "compatibility_surrogate_must_pass_exact_frozen_validator"
        ]
        is True
        and policy["compatibility_returns_original_receipt_byte_identical"]
        is True
        and policy[
            "compatibility_changes_candidate_prediction_routing_effect_budget_or_credit"
        ]
        is False
        and compatibility._FROZEN_VALIDATE.__module__
        == "deepwide_agent.v25158_vertical_key_value_candidate_runtime",
        "residual_invariant_codes_finite_and_observed": bool(
            invariant_observer.VIOLATION_CODES
        )
        and policy[
            "residual_frozen_v25158_failure_keeps_finite_invariant_observation"
        ]
        is True,
        "dcf_parser_finite_total_and_evaluator_only": bool(
            dcf_parser.FAILURE_STAGES
        )
        and policy["dcf_failure_stage_is_finite_and_content_free"] is True
        and policy["dcf_parser_is_postfreeze_evaluator_only_not_forward_runtime"]
        is True
        and contract.DCF_PARSER not in contract.forward_dependency_closure(ROOT),
        "old_population_reuse_and_revaluation_forbidden": policy[
            "v25203_population_reuse"
        ]
        is False
        and policy["v25203_quality_result_reused_or_revalued"] is False
        and policy[
            "same_population_refetch_revalue_retry_resume_or_replacement"
        ]
        is False,
        "same_response_mechanism_gate_frozen": gate[
            "minimum_same_raw_counterfactual_active_tasks"
        ]
        == 10
        and gate["minimum_prediction_changed_tasks"] == 10,
        "strict_quality_gate_frozen": quality[
            "minimum_candidate_exact_gain"
        ]
        == 10
        and quality["minimum_candidate_exact_successes"] == 10,
        "entropy_information_gain_signed_credit_disabled": policy[
            "entropy_or_information_gain_assigns_signed_credit"
        ]
        is False,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v25206_cran_dcf_quality_build_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target},
        "source_manifest": manifest,
        "source_manifest_sha256": contract.payload_sha256(manifest),
        "tests": tests,
        "semantic_audit": semantic,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "source_policy": policy,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "authorization": {
            "protocol_generation_after_build_commit_push": not findings,
            "external_forward": False,
            "external_evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_build(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role")
        != "v25206_cran_dcf_quality_build_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or not copied.get("checks")
        or not all(copied["checks"].values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("semantic_audit", {}).get(
            "privileged_runtime_field_accesses"
        )
        != []
        or copied.get("semantic_audit", {}).get("evaluator_capabilities") != []
        or copied.get("semantic_audit", {}).get("credential_literal_hits") != []
        or copied.get(
            "network_model_search_fetch_evaluator_benchmark_or_api_called"
        )
        is not False
        or copied.get("authorization")
        != {
            "protocol_generation_after_build_commit_push": True,
            "external_forward": False,
            "external_evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
        }
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.52.06 build audit drifted")
    return copied


def build_protocol(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    validate_build(_read(contract.BUILD_AUDIT))
    return contract.build_protocol(
        ROOT,
        now=int(time.time()) if now is None else int(now),
        tracked=True,
        require_pristine=True,
        build_audit_sha256=contract.sha256(ROOT / contract.BUILD_AUDIT),
    )


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    head, target = _clean_pushed()
    build = validate_build(_read(contract.BUILD_AUDIT))
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    tests = _tests()
    semantic = _semantic_audit()
    future = (
        contract.PREAUDIT,
        contract.EXECUTION_START,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.EVALUATOR,
        contract.EVALUATOR_TEST,
        contract.EVALUATOR_PROTOCOL,
        contract.RESULT,
        contract.POSTAUDIT,
        contract.OUTPUT_ROOT,
    )
    checks = {
        "build_and_protocol_valid": build["audit_valid"] is True,
        "protocol_source_manifest_live": protocol["source_manifest"]
        == contract.dependency_manifest(ROOT, tracked=True),
        "focused_and_complete_parent_tests_exact": tests["passed"],
        "privileged_runtime_field_access_zero": not semantic[
            "privileged_runtime_field_accesses"
        ],
        "evaluator_capability_absent": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "selection_still_valid": _selection_valid(tracked=True),
        "diagnosis_still_valid": _diagnosis_valid(tracked=True),
        "future_surfaces_pristine": _future_pristine(future),
        "local_gpt56_endpoint_reachable": _endpoint_reachable(),
        "shared_api_lease_inactive": _lease_inactive(),
        "no_active_conflicting_forward_or_evaluator": not _active_conflicts(),
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == protocol["protected_watchers"],
        "evaluator_implementation_absent_before_prediction_freeze": not (
            ROOT / contract.EVALUATOR
        ).exists()
        and not (ROOT / contract.EVALUATOR_TEST).exists(),
        "natural_task_vector_stable": contract.payload_sha256(
            contract.task_vector()
        )
        == protocol["population"]["task_vector_sha256"],
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v25206_cran_dcf_quality_preactivation_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target},
        "build_audit_sha256": contract.sha256(ROOT / contract.BUILD_AUDIT),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "tests": tests,
        "semantic_audit": semantic,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "protected_watchers": contract.watcher_snapshot(),
        "source_policy": contract.source_policy(),
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "authorization": {
            "one_external_forward_after_separate_clean_pushed_start": not findings,
            "external_evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_rerun": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role")
        != "v25206_cran_dcf_quality_preactivation_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or not copied.get("checks")
        or not all(copied["checks"].values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get(
            "network_model_search_fetch_evaluator_benchmark_or_api_called"
        )
        is not False
        or copied.get("authorization")
        != {
            "one_external_forward_after_separate_clean_pushed_start": True,
            "external_evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_rerun": False,
        }
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.52.06 preactivation audit drifted")
    return copied


def build_start(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    preaudit = validate_preaudit(_read(contract.PREAUDIT))
    future = (
        contract.EXECUTION_START,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.EVALUATOR,
        contract.EVALUATOR_TEST,
        contract.EVALUATOR_PROTOCOL,
        contract.RESULT,
        contract.POSTAUDIT,
        contract.OUTPUT_ROOT,
    )
    if (
        not _future_pristine(future)
        or not _endpoint_reachable()
        or not _lease_inactive()
        or _active_conflicts()
        or contract.watcher_snapshot() != protocol["protected_watchers"]
        or preaudit["audit_valid"] is not True
    ):
        raise RuntimeError("V2.52.06 execution start prerequisites failed")
    value = {
        "artifact_version": 1,
        "role": "v25206_cran_dcf_quality_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "task_vector_sha256": protocol["population"]["task_vector_sha256"],
        "protected_watchers": contract.watcher_snapshot(),
        "authorization": {
            "one_external_forward": True,
            "external_evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_rerun": False,
        },
    }
    return contract.seal(value, "execution_start_payload_sha256")


def build_forward_audit(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    forward = runner.validate_forward_result(_read(contract.FORWARD_RESULT))
    rows = [
        runner.validate_task_row(row)
        for row in runner._read_jsonl(contract.TASK_ROWS, tracked=True)
    ]
    sidecar = runner.validate_compatibility_aggregate(
        _read(contract.COMPATIBILITY_AGGREGATE)
    )
    aggregate = runner.aggregate_rows(
        rows,
        wall_seconds=float(forward["aggregate"]["batch_wall_seconds"]),
        compatibility_aggregate=sidecar,
    )
    decision = runner.mechanism_decision(aggregate)
    freeze = _read(contract.PREDICTION_FREEZE)
    forbidden = {
        "question",
        "query",
        "url",
        "host",
        "title",
        "page",
        "target",
        "authority",
        "column",
        "category",
        "question_type",
        "gold",
        "score",
        "reward",
        "message",
        "traceback",
        "frame",
        "exception_repr",
    }
    sidecar_sha = contract.sha256(ROOT / contract.COMPATIBILITY_AGGREGATE)
    checks = {
        "protocol_forward_rows_and_compatibility_validate": True,
        "exact_task_denominator": len(rows) == contract.TASK_COUNT
        and [row["opaque_id"] for row in rows]
        == [task["opaque_id"] for task in contract.task_vector()],
        "aggregate_recomputes_exactly": aggregate == forward["aggregate"],
        "mechanism_decision_recomputes_exactly": decision
        == forward["mechanism_decision"],
        "task_rows_contain_no_forbidden_content_keys": not _recursive_keys(
            rows
        ).intersection(forbidden),
        "compatibility_aggregate_contains_no_forbidden_content_keys": not _recursive_keys(
            sidecar
        ).intersection(forbidden),
        "compatibility_aggregate_hash_bound": forward[
            "compatibility_aggregate_sha256"
        ]
        == sidecar_sha
        and freeze.get("compatibility_aggregate_sha256") == sidecar_sha,
        "residual_invariant_failures_bind_outer_failures": sidecar[
            "residual_v25158_receipt_failure_tasks"
        ]
        == aggregate["outer_failure_code_counts"].get(
            "v25158_receipt_validation", 0
        ),
        "residual_invariant_observability_complete": sidecar[
            "residual_v25158_invariant_observer_missing_tasks"
        ]
        == 0,
        "compatibility_application_cannot_mask_outer_failure": sidecar[
            "compatibility_applied_outer_failure_tasks"
        ]
        == 0,
        "actual_effect_counts_complete": all(
            runner.accounting._validate_actual_effect_snapshot(
                row["actual_effect_snapshot"]
            )
            == row["actual_effect_snapshot"]
            for row in rows
        ),
        "task_rows_hash_bound": forward["task_rows_sha256"]
        == contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_valid": contract.sealed(
            freeze, "freeze_payload_sha256"
        ),
        "prediction_freeze_hash_bound": forward["prediction_freeze_sha256"]
        == contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "prediction_freeze_binds_task_rows": freeze.get("task_rows_sha256")
        == contract.sha256(ROOT / contract.TASK_ROWS),
        "gold_and_evaluator_surfaces_absent": _future_pristine(
            (
                contract.POSTFREEZE_GOLD,
                contract.EVALUATOR,
                contract.EVALUATOR_TEST,
                contract.EVALUATOR_PROTOCOL,
                contract.RESULT,
                contract.POSTAUDIT,
            )
        ),
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == protocol["protected_watchers"],
        "shared_api_lease_released": _lease_inactive(),
        "forward_process_absent": not _active_conflicts(),
        "no_deepwidebench_or_sota_authority": forward["authorization"][
            "deepwidebench_dev64_exact220_or_sota"
        ]
        is False,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v25206_cran_dcf_quality_forward_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "execution_start_sha256": contract.sha256(
            ROOT / contract.EXECUTION_START
        ),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_sha256": contract.sha256(
            ROOT / contract.PREDICTION_FREEZE
        ),
        "compatibility_aggregate_sha256": sidecar_sha,
        "aggregate": aggregate,
        "mechanism_decision": decision,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "postfreeze_evaluator_implementation_and_protocol": not findings
            and decision["same_response_mechanism_gate_passed"],
            "external_evaluator_now": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_revaluation": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("build-audit", "protocol", "preaudit", "start", "forward-audit"),
    )
    args = parser.parse_args()
    if args.command == "build-audit":
        value, path = build_audit(), contract.BUILD_AUDIT
    elif args.command == "protocol":
        value, path = build_protocol(), contract.PROTOCOL
    elif args.command == "preaudit":
        value, path = build_preaudit(), contract.PREAUDIT
    elif args.command == "start":
        value, path = build_start(), contract.EXECUTION_START
    else:
        value, path = build_forward_audit(), contract.FORWARD_AUDIT
    if value.get("findings"):
        raise RuntimeError(value["findings"])
    _publish(path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "role": value["role"],
                "audit_valid": value.get("audit_valid"),
                "authorization": value.get("authorization"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
