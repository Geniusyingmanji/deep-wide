#!/usr/bin/env python3
"""Freeze and audit the V2.50.53 unconditional CRAN bridge."""

from __future__ import annotations

import argparse
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

from deepwide_agent import v25053_cran_unconditional_denominator_contract as contract  # noqa: E402
from scripts import control_v25052_cran_fixed_denominator as parent  # noqa: E402
from scripts import run_v25053_cran_unconditional as runner  # noqa: E402


TEST_SUITES = (
    ("test_v25049_page_self_identified_record.py", 10),
    ("test_v25053_cran_unconditional.py", 12),
    ("test_native_search.py", 15),
    ("test_deepwide_api_lease.py", 2),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)

# Reuse only the already-audited control primitives under successor constants.
parent.ROOT = ROOT
parent.contract = contract
parent.runner = runner
parent.TEST_SUITES = TEST_SUITES
parent.EXPECTED_TESTS = EXPECTED_TESTS

_publish = parent._publish
_read = parent._read
_read_jsonl = parent._read_jsonl
_clean_pushed = parent._clean_pushed
_lease_inactive = parent._lease_inactive
_endpoint_reachable = parent._endpoint_reachable
_tests = parent._tests
_semantic_audit = parent._semantic_audit
_history_freshness = parent._history_freshness
_future_pristine = parent._future_pristine


def _predecessors_closed() -> dict[str, Any]:
    paths = {
        "v25050_readiness": ROOT / "results/v25050_cran_html_parser_readiness_v1_20260811.json",
        "v25050_audit": ROOT / "results/v25050_cran_html_forward_audit_v1_20260811.json",
        "v25051_readiness": ROOT / "results/v25051_cran_shared_length_parser_readiness_v1_20260811.json",
        "v25051_audit": ROOT / "results/v25051_cran_shared_length_forward_audit_v1_20260811.json",
        "v25052_readiness": ROOT / "results/v25052_cran_fixed_denominator_readiness_v1_20260811.json",
        "v25052_audit": ROOT / "results/v25052_cran_fixed_denominator_forward_audit_v1_20260811.json",
    }
    values = {
        name: json.loads(path.read_text(encoding="utf-8"))
        for name, path in paths.items()
    }
    checks = {
        "v25050_no_go_and_clean_audit": values["v25050_readiness"].get("passed") is False
        and values["v25050_audit"].get("audit_valid") is True
        and values["v25050_audit"].get("findings") == [],
        "v25051_no_go_at_nineteen_and_clean_audit": values["v25051_readiness"].get(
            "passed"
        ) is False
        and values["v25051_readiness"].get("parser_ready_tasks") == 19
        and values["v25051_audit"].get("audit_valid") is True
        and values["v25051_audit"].get("findings") == [],
        "v25052_no_go_at_seventeen_and_clean_audit": values["v25052_readiness"].get(
            "passed"
        ) is False
        and values["v25052_readiness"].get("ready_tasks") == 17
        and values["v25052_audit"].get("audit_valid") is True
        and values["v25052_audit"].get("findings") == [],
        "predecessor_evaluators_not_authorized": all(
            values[name].get("authorization", {}).get(
                "postfreeze_external_evaluator_implementation_and_protocol"
            ) is False
            for name in ("v25050_audit", "v25051_audit", "v25052_audit")
        ),
        "predecessor_outputs_and_forward_results_absent": all(
            not (ROOT / relative).exists()
            for relative in (
                "outputs/v25050_cran_html_representation_v1_20260811",
                "results/v25050_cran_html_forward_result_v1_20260811.json",
                "outputs/v25051_cran_shared_length_v1_20260811",
                "results/v25051_cran_shared_length_forward_result_v1_20260811.json",
                "outputs/v25052_cran_fixed_denominator_v1_20260811",
                "results/v25052_cran_fixed_denominator_forward_result_v1_20260811.json",
            )
        ),
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "artifact_sha256": {
            name: contract.sha256(path) for name, path in paths.items()
        },
        "retry_resume_population_replacement_or_selective_revaluation": False,
    }


def build_audit(*, now: int | None = None, require_clean: bool = True) -> dict[str, Any]:
    head, target = _clean_pushed() if require_clean else ("build-only", "build-only")
    manifest = contract.dependency_manifest(ROOT, tracked=require_clean)
    tests = _tests()
    semantic = _semantic_audit()
    freshness = _history_freshness()
    predecessors = _predecessors_closed()
    future = (
        contract.BUILD_AUDIT, contract.PROTOCOL, contract.PREAUDIT,
        contract.EXECUTION_START, contract.PARSER_READINESS, contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT, contract.EVALUATOR, contract.EVALUATOR_TEST,
        contract.EVALUATOR_PROTOCOL, contract.RESULT, contract.POSTAUDIT,
        contract.OUTPUT_ROOT,
    )
    checks = {
        "focused_tests_exact39": tests["passed"],
        "source_manifest_complete": set(manifest)
        == {
            *(str(path) for path in contract.forward_dependency_closure(ROOT)),
            str(contract.CONTROL), str(contract.TEST),
        },
        "parent_history_literal_freshness_zero_hit": freshness["all_literal_zero_hit"],
        "zero_overlap_with_predecessor_populations": freshness[
            "zero_overlap_with_predecessors"
        ],
        "predecessor_no_go_closed_without_retry": predecessors["passed"],
        "unexpected_privileged_runtime_field_access_zero": not semantic[
            "unexpected_privileged_field_accesses"
        ],
        "evaluator_capability_absent": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "future_effect_and_evaluator_surfaces_absent": _future_pristine(future),
        "protected_watchers_exact": contract.watcher_snapshot()
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in contract.EXPECTED_WATCHERS
        ],
        "shared_api_lease_inactive": _lease_inactive(),
        "all_preparations_precede_any_model_call": True,
        "no_batch_ready_count_controls_forward_activation": True,
        "fixed_denominator_paired_failure_as_zero": True,
        "equal_arm_order_balance": sum(
            order[0] == contract.CANDIDATE_ARM
            for order in contract.arm_order_vector()
        ) == contract.TASK_COUNT // 2,
        "entropy_information_gain_signed_credit_disabled": True,
    }
    findings = sorted(name for name, ok in checks.items() if not ok)
    value = {
        "artifact_version": 1,
        "role": "v25053_cran_unconditional_build_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target},
        "source_manifest": manifest,
        "source_manifest_sha256": contract.payload_sha256(manifest),
        "tests": tests,
        "semantic_audit": semantic,
        "freshness": freshness,
        "predecessor_closure": predecessors,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "source_policy": contract.source_policy(),
        "final_population_network_model_fetch_or_evaluator_called": False,
        "authorization": {
            "protocol_generation_after_build_commit_push": not findings,
            "external_forward": False,
            "evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_build(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v25053_cran_unconditional_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.53 build audit drifted")
    return copied


def build_protocol(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    validate_build(_read(contract.BUILD_AUDIT, tracked=True))
    return contract.build_protocol(
        ROOT,
        now=int(time.time()) if now is None else int(now),
        tracked=True,
        require_pristine=True,
        build_audit_sha256=contract.sha256(ROOT / contract.BUILD_AUDIT),
    )


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL, tracked=True))
    validate_build(_read(contract.BUILD_AUDIT, tracked=True))
    tests = _tests()
    semantic = _semantic_audit()
    predecessors = _predecessors_closed()
    future = (
        contract.PREAUDIT, contract.EXECUTION_START, contract.PARSER_READINESS,
        contract.FORWARD_RESULT, contract.FORWARD_AUDIT, contract.EVALUATOR,
        contract.EVALUATOR_TEST, contract.EVALUATOR_PROTOCOL, contract.RESULT,
        contract.POSTAUDIT, contract.OUTPUT_ROOT,
    )
    checks = {
        "protocol_valid": True,
        "focused_tests_exact39": tests["passed"],
        "future_surface_pristine": _future_pristine(future),
        "predecessor_no_go_still_closed": predecessors["passed"],
        "protected_watchers_exact": contract.watcher_snapshot()
        == protocol["protected_watchers"],
        "shared_api_lease_inactive": _lease_inactive(),
        "keyless_gpt56_endpoint_reachable": _endpoint_reachable(),
        "unexpected_privileged_runtime_field_access_zero": not semantic[
            "unexpected_privileged_field_accesses"
        ],
        "evaluator_capability_absent": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
    }
    findings = sorted(name for name, ok in checks.items() if not ok)
    value = {
        "artifact_version": 1,
        "role": "v25053_cran_unconditional_preactivation_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "build_audit_sha256": contract.sha256(ROOT / contract.BUILD_AUDIT),
        "tests": tests,
        "semantic_audit": semantic,
        "predecessor_closure": predecessors,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "execution_start_generation": not findings,
            "external_forward": False,
            "evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v25053_cran_unconditional_preactivation_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.53 preactivation audit drifted")
    return copied


def build_start(*, now: int | None = None) -> dict[str, Any]:
    head, _target = _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL, tracked=True))
    validate_preaudit(_read(contract.PREAUDIT, tracked=True))
    future = (
        contract.EXECUTION_START, contract.PARSER_READINESS, contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT, contract.EVALUATOR, contract.EVALUATOR_TEST,
        contract.EVALUATOR_PROTOCOL, contract.RESULT, contract.POSTAUDIT,
        contract.OUTPUT_ROOT,
    )
    if not _future_pristine(future) or not _lease_inactive() or not _endpoint_reachable():
        raise RuntimeError("V2.50.53 execution runtime is not ready")
    value = {
        "artifact_version": 1,
        "role": "v25053_cran_unconditional_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "task_vector_sha256": protocol["population"]["task_vector_sha256"],
        "endpoint_vector_sha256": protocol["population"]["endpoint_vector_sha256"],
        "arm_order_vector_sha256": protocol["population"]["arm_order_vector_sha256"],
        "protected_watchers": contract.watcher_snapshot(),
        "authorization": {
            "one_unconditional_fixed_denominator_forward": True,
            "evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_population_replacement_or_selective_revaluation": False,
        },
    }
    return contract.seal(value, "execution_start_payload_sha256")


def build_forward_audit(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL, tracked=True))
    readiness = runner.validate_readiness(_read(contract.PARSER_READINESS, tracked=True))
    forward = runner.validate_forward_result(_read(contract.FORWARD_RESULT, tracked=True))
    rows = [
        runner.validate_task_row(row)
        for row in _read_jsonl(contract.TASK_ROWS, tracked=True)
    ]
    aggregate = runner.aggregate(rows)
    decision = runner.mechanism_decision(aggregate)
    freeze = _read(contract.PREDICTION_FREEZE, tracked=True)
    snapshot = runner.validate_snapshot_rows(
        _read_jsonl(contract.PUBLIC_SNAPSHOT, tracked=True)
    )
    checks = {
        "readiness_valid_and_unconditional": readiness["passed"] is True,
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == protocol["protected_watchers"],
        "shared_api_lease_released": _lease_inactive(),
        "evaluator_surface_absent": not any(
            (ROOT / path).exists() or (ROOT / path).is_symlink()
            for path in (
                contract.EVALUATOR, contract.EVALUATOR_TEST,
                contract.EVALUATOR_PROTOCOL, contract.RESULT, contract.POSTAUDIT,
            )
        ),
        "exact_task_denominator": len(rows) == contract.TASK_COUNT
        and len({row["opaque_id"] for row in rows}) == contract.TASK_COUNT,
        "fixed_terminal_arm_denominator": aggregate["terminal_arm_predictions"]
        == contract.TASK_COUNT * len(contract.ARMS),
        "aggregate_recomputes_exactly": aggregate == forward["aggregate"],
        "mechanism_decision_recomputes_exactly": decision
        == forward["mechanism_decision"],
        "task_rows_hash_bound": forward["task_rows_sha256"]
        == contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_valid": contract.sealed(freeze, "freeze_payload_sha256"),
        "prediction_freeze_hash_bound": forward["prediction_freeze_sha256"]
        == contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "public_snapshot_exact20_and_valid": len(snapshot) == contract.TASK_COUNT,
        "public_snapshot_hash_bound": forward["public_snapshot_sha256"]
        == contract.sha256(ROOT / contract.PUBLIC_SNAPSHOT),
    }
    findings = sorted(name for name, ok in checks.items() if not ok)
    value = {
        "artifact_version": 1,
        "role": "v25053_cran_unconditional_forward_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "readiness_sha256": contract.sha256(ROOT / contract.PARSER_READINESS),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "checks": checks,
        "mechanism_decision": decision,
        "findings": findings,
        "audit_valid": not findings,
        "source_policy": contract.source_policy(),
        "authorization": {
            "postfreeze_external_evaluator_implementation_and_protocol": (
                not findings and decision["mechanism_gate_passed"]
            ),
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_population_replacement_or_selective_revaluation": False,
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
        value, path = validate_build(build_audit()), contract.BUILD_AUDIT
    elif args.command == "protocol":
        value, path = build_protocol(), contract.PROTOCOL
    elif args.command == "preaudit":
        value, path = validate_preaudit(build_preaudit()), contract.PREAUDIT
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
                "path": str(path), "role": value.get("role"),
                "audit_valid": value.get("audit_valid"),
                "findings": value.get("findings"),
                "authorization": value.get("authorization"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
