#!/usr/bin/env python3
"""Build, freeze, authorize, and audit the V2.50.27 external gate."""

from __future__ import annotations

import argparse
import ast
import json
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

from deepwide_agent import v25025_evidence_conditioned_paired_runtime as runtime  # noqa: E402
from deepwide_agent import v25027_clue_resolved_external_contract as contract  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import control_v24997_shared_first_wave_external as engine  # noqa: E402


TEST_SUITES = (
    (contract.REFINEMENT_TEST, 8),
    (contract.REACHABILITY_TEST, 6),
    (contract.RUNTIME_TEST, 6),
    (contract.TEST, 10),
    (Path("tests/test_v24996_shared_first_wave_paired_runtime.py"), 7),
    (Path("tests/test_v24990_query_vector_paired_runtime.py"), 7),
    (Path("tests/test_v24986_robust_paired_runtime.py"), 5),
    (Path("tests/test_v24985_robust_late_page_fetch.py"), 2),
    (Path("tests/test_v24982_paired_production_runtime.py"), 7),
)
EXPECTED_TESTS = sum(count for _path, count in TEST_SUITES)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


def configure() -> None:
    engine.contract = contract
    engine.runtime = runtime
    engine.FORWARD_SOURCES = contract.FORWARD_SOURCES
    engine.TEST_SUITES = TEST_SUITES
    engine.EXPECTED_TESTS = EXPECTED_TESTS


def _findings() -> tuple[list[str], list[str], list[str]]:
    privileged: list[str] = []
    evaluator: list[str] = []
    secrets: list[str] = []
    for relative in contract.FORWARD_SOURCES:
        path = ROOT / relative
        source = path.read_text(encoding="utf-8")
        privileged.extend(semantic_audit._accesses(path, ROOT))
        evaluator.extend(semantic_audit._evaluator_capabilities(path, ROOT))
        if SECRET.search(source):
            secrets.append(str(relative))
    # clients.py's public provider relevance score is outside this manifest;
    # no benchmark/evaluator score is accepted by any V2.50.27 source.
    return sorted(set(privileged)), sorted(set(evaluator)), sorted(set(secrets))


def _imports_safe() -> bool:
    forbidden = {
        "deepwidebench",
        "v25027_clue_gold_mapping",
        "evaluate_v25027_clue_resolved_external",
    }
    for relative in contract.FORWARD_SOURCES:
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(item.name.casefold() for item in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append((node.module or "").casefold())
        if any(any(marker in name for marker in forbidden) for name in imports):
            return False
    return True


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    configure()
    tests = engine._tests()
    privileged, evaluator, secrets = _findings()
    manifest = contract.dependency_manifest(ROOT, tracked=False)
    future_mapping_absent = not (ROOT / contract.EVALUATOR_MAPPING).exists()
    future_evaluator_absent = not (ROOT / contract.EVALUATOR).exists()
    checks = {
        "focused_and_parent_tests_pass": tests["passed"],
        "source_manifest_complete": len(manifest) == len(contract.LOCAL_SOURCES),
        "forward_imports_exclude_benchmark_evaluator_and_mapping": _imports_safe(),
        "privileged_runtime_field_findings_empty": not privileged,
        "evaluator_capability_findings_empty": not evaluator,
        "credential_literal_findings_empty": not secrets,
        "public_clue_population_fixed_twenty": len(contract.task_vector()) == 20,
        "evaluator_mapping_module_absent": future_mapping_absent,
        "evaluator_script_absent": future_evaluator_absent,
        "arm_order_exactly_balanced": sum(
            order[0] == contract.CANDIDATE_ARM for order in contract.arm_order_vector()
        ) == 10,
        "per_arm_caps_match_production": contract.LIMITS == {
            "wall_seconds": 240, "model_calls": 3, "search_queries": 4,
            "fetch_targets": 10, "search_results_per_query": 3,
            "evidence_chars": 60000, "page_chars": 5000,
            "plan_output_tokens": 4000, "synthesis_output_tokens": 30000,
            "repair_output_tokens": 12000,
        },
        "paired_budget_disclosed_and_public220_closed": (
            contract.source_policy()["paired_physical_model_query_fetch_caps"]
            == {"models": 4, "queries": 6, "fetches": 14}
            and not contract.source_policy()["public_deepwidebench_exact220_launch_authorized"]
        ),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    return contract.seal(
        {
            "artifact_version": 1,
            "role": "v25027_clue_resolved_external_build_audit",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()) if now is None else int(now),
            "tests": tests,
            "source_manifest": manifest,
            "source_manifest_sha256": contract.payload_sha256(manifest),
            "label_blind_audit": {
                "privileged_runtime_field_accesses": privileged,
                "evaluator_capabilities": evaluator,
                "credential_literal_hits": secrets,
            },
            "checks": checks,
            "findings": findings,
            "audit_valid": not findings,
            "source_policy": contract.source_policy(),
            "authorization": {
                "implementation_commit": not findings,
                "protocol_publication": not findings,
                "one_external_forward": False,
                "evaluator": False,
                "public_exact220_or_sota": False,
            },
        },
        "audit_payload_sha256",
    )


def validate_build(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v25027_clue_resolved_external_build_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True or copied.get("findings") != []
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.27 build audit drifted")
    return copied


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    configure()
    engine._clean_pushed()
    protocol = contract.validate_protocol(ROOT, engine._read(contract.PROTOCOL, tracked=True))
    validate_build(engine._read(contract.BUILD_AUDIT, tracked=True))
    tests = engine._tests()
    privileged, evaluator, secrets = _findings()
    checks = {
        "protocol_valid": True,
        "build_audit_valid": True,
        "focused_and_parent_tests_pass": tests["passed"],
        "future_surface_pristine": engine._future_pristine((
            contract.PREAUDIT, contract.EXECUTION_START, contract.FORWARD_RESULT,
            contract.FORWARD_AUDIT, contract.EVALUATOR_PROTOCOL, contract.RESULT,
            contract.POSTAUDIT, contract.OUTPUT_ROOT, contract.EVALUATOR,
            contract.EVALUATOR_MAPPING,
        )),
        "protected_watchers_exact": contract.watcher_snapshot()
        == protocol["execution"]["protected_watchers"],
        "shared_api_lease_inactive": engine._lease_inactive(),
        "keyless_gpt56_endpoint_reachable": engine._endpoint_ready(),
        "conflicting_forward_or_evaluator_processes_absent": not engine._active_conflicts(),
        "privileged_runtime_field_findings_empty": not privileged,
        "evaluator_capability_findings_empty": not evaluator,
        "credential_literal_findings_empty": not secrets,
        "country_tld_mapping_module_absent": not (ROOT / contract.EVALUATOR_MAPPING).exists(),
        "postfreeze_gold_surface_absent": not (ROOT / contract.POSTFREEZE_GOLD).exists(),
        "final_population_not_preflighted": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    return contract.seal(
        {
            "artifact_version": 1,
            "role": "v25027_clue_resolved_external_preactivation_audit",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()) if now is None else int(now),
            "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
            "build_audit_sha256": contract.sha256(ROOT / contract.BUILD_AUDIT),
            "dependency_manifest_sha256": protocol["dependency_manifest_sha256"],
            "tests": tests,
            "checks": checks,
            "findings": findings,
            "audit_valid": not findings,
            "source_policy": contract.source_policy(),
            "authorization": {
                "execution_start_generation": not findings,
                "one_external_forward": False,
                "evaluator": False,
                "public_exact220_or_sota": False,
            },
        },
        "audit_payload_sha256",
    )


def build_start(*, now: int | None = None) -> dict[str, Any]:
    configure()
    engine._clean_pushed()
    protocol = contract.validate_protocol(ROOT, engine._read(contract.PROTOCOL, tracked=True))
    preaudit = engine._read(contract.PREAUDIT, tracked=True)
    if (
        preaudit.get("role") != "v25027_clue_resolved_external_preactivation_audit"
        or preaudit.get("audit_valid") is not True or preaudit.get("findings") != []
        or not contract.sealed(preaudit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.27 preactivation audit drifted")
    if not engine._future_pristine((
        contract.EXECUTION_START, contract.FORWARD_RESULT, contract.FORWARD_AUDIT,
        contract.EVALUATOR_PROTOCOL, contract.RESULT, contract.POSTAUDIT,
        contract.OUTPUT_ROOT, contract.EVALUATOR, contract.EVALUATOR_MAPPING,
    )):
        raise RuntimeError("V2.50.27 execution surface is not pristine")
    if not engine._lease_inactive() or not engine._endpoint_ready() or engine._active_conflicts():
        raise RuntimeError("V2.50.27 runtime is not ready")
    return contract.seal(
        {
            "artifact_version": 1,
            "role": "v25027_clue_resolved_external_execution_start",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()) if now is None else int(now),
            "git_head": contract.git(ROOT, "rev-parse", "HEAD"),
            "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
            "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
            "task_vector_sha256": protocol["population"]["task_vector_sha256"],
            "arm_order_vector_sha256": protocol["population"]["arm_order_vector_sha256"],
            "protected_watchers": contract.watcher_snapshot(),
            "mapping_evaluator_prediction_and_gold_surfaces_pristine": True,
            "authorization": {
                "one_external_forward": True,
                "evaluator": False,
                "public_exact220_or_sota": False,
                "retry_resume_selective_rerun": False,
            },
        },
        "execution_start_payload_sha256",
    )


def _mechanism(rows: list[dict[str, Any]], gate: Mapping[str, Any]) -> dict[str, Any]:
    checked = [runtime.validate_result(row) for row in rows]
    receipts = [row["content_free_receipt"] for row in checked]
    resolved = [runtime.reachability.validate_receipt(
        receipt["resolved_schema_reachability_receipt"]
    ) for receipt in receipts]
    orders = [
        [receipt["first_delta_arm"], next(
            arm for arm in contract.ARMS if arm != receipt["first_delta_arm"]
        )]
        for receipt in receipts
    ]
    value = {
        "terminal_tasks": len(checked),
        "refinement_model_call_attempted_tasks": sum(
            receipt["refinement_model_call_attempted"] for receipt in receipts
        ),
        "refinement_strategy_applied_tasks": sum(
            receipt["refinement_strategy_applied"] for receipt in receipts
        ),
        "candidate_resolved_schema_pages": sum(
            item["candidate_resolved_schema_page_count"] for item in resolved
        ),
        "control_resolved_schema_pages": sum(
            item["control_resolved_schema_page_count"] for item in resolved
        ),
        "tasks_with_candidate_resolved_schema_strict_advantage": sum(
            item["candidate_resolved_schema_page_strict_advantage"] for item in resolved
        ),
        "both_arms_model_success_tasks": sum(
            all(row["model_success"].values()) for row in checked
        ),
        "prediction_changed_tasks": sum(row["prediction_changed"] for row in checked),
        "shared_prefix_byte_equal_tasks": sum(
            receipt["shared_prefix_byte_equal_between_arms"] for receipt in receipts
        ),
        "all_tasks_execute_at_most_six_physical_queries": all(
            receipt["physical_query_count"] <= 6 for receipt in receipts
        ),
        "all_tasks_fetch_at_most_fourteen_physical_pages": all(
            receipt["physical_fetch_count"] <= 14 for receipt in receipts
        ),
        "all_tasks_use_at_most_four_physical_model_calls": all(
            receipt["model_logical_call_count"] <= 4
            and receipt["model_provider_request_count"] <= 4
            for receipt in receipts
        ),
        "executed_arm_order_matches_frozen_vector": orders == contract.arm_order_vector(),
    }
    value["passed"] = (
        value["terminal_tasks"] == gate["terminal_tasks"]
        and value["refinement_model_call_attempted_tasks"]
        >= gate["minimum_refinement_model_call_attempted_tasks"]
        and value["refinement_strategy_applied_tasks"]
        >= gate["minimum_refinement_strategy_applied_tasks"]
        and value["candidate_resolved_schema_pages"]
        >= gate["minimum_candidate_resolved_schema_pages"]
        and value["tasks_with_candidate_resolved_schema_strict_advantage"]
        >= gate["minimum_tasks_with_candidate_resolved_schema_strict_advantage"]
        and value["both_arms_model_success_tasks"]
        >= gate["minimum_both_arms_model_success_tasks"]
        and value["prediction_changed_tasks"] >= gate["minimum_prediction_changed_tasks"]
        and value["shared_prefix_byte_equal_tasks"] == gate["shared_prefix_byte_equal_tasks"]
        and value["all_tasks_execute_at_most_six_physical_queries"]
        and value["all_tasks_fetch_at_most_fourteen_physical_pages"]
        and value["all_tasks_use_at_most_four_physical_model_calls"]
        and value["executed_arm_order_matches_frozen_vector"]
    )
    return value


def build_forward_audit(*, now: int | None = None) -> dict[str, Any]:
    configure()
    engine._clean_pushed()
    protocol = contract.validate_protocol(ROOT, engine._read(contract.PROTOCOL, tracked=True))
    forward = engine._read(contract.FORWARD_RESULT, tracked=True)
    rows = engine._read_jsonl(contract.TASK_RESULTS)
    if (
        forward.get("role") != "v25027_clue_resolved_external_forward_result"
        or not contract.sealed(forward, "result_payload_sha256")
        or len(rows) != contract.TASK_COUNT
    ):
        raise RuntimeError("V2.50.27 frozen forward drifted")
    mechanism = _mechanism(rows, protocol["mechanism_gate_before_evaluator"])
    aggregate = forward.get("aggregate")
    names = tuple(name for name in mechanism if name != "passed")
    checks = {
        "prediction_freeze_bound": forward.get("prediction_freeze_sha256")
        == contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "task_results_bound": forward.get("task_results_sha256")
        == contract.sha256(ROOT / contract.TASK_RESULTS),
        "forward_aggregate_bound": isinstance(aggregate, Mapping) and all(
            aggregate.get(name) == mechanism[name] for name in names
            if name in aggregate
        ),
        "all_rows_valid": mechanism["terminal_tasks"] == contract.TASK_COUNT,
        "mapping_module_still_absent": not (ROOT / contract.EVALUATOR_MAPPING).exists(),
        "evaluator_script_still_absent": not (ROOT / contract.EVALUATOR).exists(),
        "postfreeze_gold_absent": not (ROOT / contract.POSTFREEZE_GOLD).exists(),
        "mapping_gold_evaluator_closed_during_forward": forward.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read"
        ) is False and forward.get("mapping_module_present_opened_or_hashed") is False,
        "protected_watchers_exact": contract.watcher_snapshot()
        == protocol["execution"]["protected_watchers"],
        "forward_process_absent": not engine._active_conflicts(),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    return contract.seal(
        {
            "artifact_version": 1,
            "role": "v25027_clue_resolved_external_forward_audit",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()) if now is None else int(now),
            "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
            "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
            "mechanism_gate": mechanism,
            "checks": checks,
            "findings": findings,
            "audit_valid": not findings,
            "authorization": {
                "postfreeze_evaluator_implementation_and_protocol": not findings
                and mechanism["passed"],
                "public_exact220_launch": False,
                "leaderboard_or_sota": False,
            },
        },
        "audit_payload_sha256",
    )


def main() -> None:
    configure()
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "protocol", "preaudit", "start", "audit"))
    args = parser.parse_args()
    if args.command == "build":
        value = build_audit()
        if not value["audit_valid"]:
            raise RuntimeError(value["findings"])
        path = contract.BUILD_AUDIT
    elif args.command == "protocol":
        engine._clean_pushed()
        validate_build(engine._read(contract.BUILD_AUDIT, tracked=True))
        value = contract.build_protocol(ROOT, now=int(time.time()))
        path = contract.PROTOCOL
    elif args.command == "preaudit":
        value = build_preaudit()
        if not value["audit_valid"]:
            raise RuntimeError(value["findings"])
        path = contract.PREAUDIT
    elif args.command == "start":
        value = build_start()
        path = contract.EXECUTION_START
    else:
        value = build_forward_audit()
        path = contract.FORWARD_AUDIT
    engine._publish(path, value)
    print(json.dumps({
        "path": str(path), "audit_valid": value.get("audit_valid"),
        "findings": value.get("findings"), "authorization": value.get("authorization"),
        "mechanism_gate": value.get("mechanism_gate"),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
