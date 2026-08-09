#!/usr/bin/env python3
"""Build, freeze, authorize, and audit the V2.50.03 external gate."""

from __future__ import annotations

import argparse
import ast
import fcntl
import json
import os
import re
import socket
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25003_page_visible_link_external_contract as contract  # noqa: E402
from deepwide_agent import v25002_page_visible_link_paired_runtime as runtime  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402


FORWARD_SOURCES = (
    contract.PROJECTOR,
    contract.FETCH,
    contract.PARENT_SELECTOR,
    contract.PARENT_RUNTIME,
    contract.SELECTOR,
    contract.RUNTIME,
    contract.HELPER,
    contract.RUNNER,
)
TEST_SUITES = (
    (contract.PROJECTOR_TEST, 4),
    (contract.FETCH_TEST, 2),
    (contract.PARENT_SELECTOR_TEST, 7),
    (contract.PARENT_RUNTIME_TEST, 7),
    (contract.SELECTOR_TEST, 7),
    (contract.RUNTIME_TEST, 6),
    (contract.TEST, 11),
    (Path("tests/test_v24980_late_page_bound_projection.py"), 8),
    (Path("tests/test_v24981_late_page_bound_fetch.py"), 8),
    (Path("tests/test_v24982_paired_production_runtime.py"), 7),
    (Path("tests/test_v24983_late_page_external.py"), 8),
    (Path("tests/test_v24986_robust_paired_runtime.py"), 5),
    (Path("tests/test_v24987_robust_external.py"), 8),
    (Path("tests/test_v24994_hybrid_query_external.py"), 11),
    (Path("tests/test_native_search.py"), 15),
    (Path("tests/test_v24286_visible_schema_runtime.py"), 6),
    (Path("tests/test_v24259_deterministic_table_normalizer.py"), 11),
)
EXPECTED_TESTS = sum(value for _path, value in TEST_SUITES)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


def _read(relative: Path, *, tracked: bool = False) -> dict[str, Any]:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.50.03 expected ordinary object: {relative}")
    if tracked and subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode != 0:
        raise RuntimeError("V2.50.03 expected tracked artifact")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.03 expected JSON object")
    return value


def _read_jsonl(relative: Path) -> list[dict[str, Any]]:
    path = ROOT / relative
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT)
    ):
        raise RuntimeError("V2.50.03 expected ordinary JSONL")
    values = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if any(not isinstance(value, dict) for value in values):
        raise RuntimeError("V2.50.03 JSONL row drifted")
    return values


def _publish(relative: Path, value: Mapping[str, Any]) -> None:
    path = ROOT / relative
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _clean_pushed() -> None:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(
        ROOT, "rev-parse", "HEAD"
    ) != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.50.03 stage requires clean pushed HEAD")


def _tests() -> dict[str, Any]:
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    rows: list[dict[str, Any]] = []
    for path, expected in TEST_SUITES:
        completed = subprocess.run(
            [
                str(ROOT / ".venv-eval/bin/python"),
                "-I", "-B", "-m", "unittest", "discover", "-s", "tests",
                "-p", path.name, "-v",
            ],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=240,
            check=False,
        )
        matched = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(matched.group(1)) if matched else 0
        rows.append(
            {
                "path": str(path),
                "expected": expected,
                "observed": observed,
                "passed": completed.returncode == 0 and observed == expected,
                "output_sha256": contract.payload_sha256(completed.stdout),
            }
        )
    observed = sum(row["observed"] for row in rows)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in rows),
        "suites": rows,
    }


def _findings() -> tuple[list[str], list[str], list[str]]:
    privileged: list[str] = []
    evaluator: list[str] = []
    secrets: list[str] = []
    for relative in FORWARD_SOURCES:
        path = ROOT / relative
        if not path.is_file():
            continue
        source = path.read_text(encoding="utf-8")
        privileged.extend(semantic_audit._accesses(path, ROOT))
        evaluator.extend(semantic_audit._evaluator_capabilities(path, ROOT))
        if SECRET.search(source):
            secrets.append(str(relative))
    return sorted(set(privileged)), sorted(set(evaluator)), sorted(set(secrets))


def _imports_safe() -> bool:
    for relative in FORWARD_SOURCES:
        path = ROOT / relative
        if not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name.casefold() for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append((node.module or "").casefold())
        if any(
            "deepwidebench" in name or "evaluate_v25003" in name
            for name in imports
        ):
            return False
    return True


def _endpoint_ready() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=1.0):
            return True
    except OSError:
        return False


def _lease_inactive() -> bool:
    path = ROOT / contract.LEASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        return False
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (OSError, BlockingIOError):
        return False


def _future_pristine(paths: tuple[Path, ...]) -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in paths
    )


def _active_conflicts() -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    markers = (str(contract.RUNNER), str(contract.EVALUATOR))
    values: list[int] = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if (
            len(parts) == 3
            and "python" in parts[1].casefold()
            and int(parts[0]) != os.getpid()
            and any(marker in parts[2] for marker in markers)
        ):
            values.append(int(parts[0]))
    return sorted(values)


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    tests = _tests()
    privileged, evaluator, secrets = _findings()
    manifest = contract.dependency_manifest(ROOT, tracked=False)
    checks = {
        "focused_and_parent_tests_pass": tests["passed"],
        "source_manifest_complete": len(manifest) == len(contract.LOCAL_SOURCES),
        "forward_imports_exclude_benchmark_and_evaluator": _imports_safe(),
        "privileged_runtime_field_findings_empty": not privileged,
        "evaluator_capability_findings_empty": not evaluator,
        "credential_literal_findings_empty": not secrets,
        "fresh_population_fixed_without_network_preflight": len(contract.task_vector()) == 20,
        "population_disjoint_from_all_prior_tld_cohorts": not bool(
            set(contract.TLD_COHORT).intersection(contract.HISTORICAL_TLD_COHORT)
        ),
        "arm_order_exactly_balanced": sum(
            order[0] == contract.CANDIDATE_ARM
            for order in contract.arm_order_vector()
        ) == 10,
        "per_arm_caps_match_production": contract.LIMITS == {
            "wall_seconds": 240,
            "model_calls": 3,
            "search_queries": 4,
            "fetch_targets": 10,
            "search_results_per_query": 3,
            "evidence_chars": 60000,
            "page_chars": 5000,
            "plan_output_tokens": 4000,
            "synthesis_output_tokens": 30000,
            "repair_output_tokens": 12000,
        },
        "paired_physical_budget_disclosed_and_public220_closed": contract.source_policy()[
            "paired_physical_query_fetch_caps"
        ] == {"queries": 4, "fetches": 14} and not contract.source_policy()[
            "public_deepwidebench_exact220_launch_authorized"
        ],
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    return contract.seal(
        {
            "artifact_version": 1,
            "role": "v25003_page_visible_link_external_build_audit",
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
        copied.get("role") != "v25003_page_visible_link_external_build_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.03 build audit drifted")
    return copied


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL, tracked=True))
    validate_build(_read(contract.BUILD_AUDIT, tracked=True))
    tests = _tests()
    privileged, evaluator, secrets = _findings()
    checks = {
        "protocol_valid": True,
        "build_audit_valid": True,
        "focused_and_parent_tests_pass": tests["passed"],
        "future_surface_pristine": _future_pristine(
            (
                contract.PREAUDIT, contract.EXECUTION_START, contract.FORWARD_RESULT,
                contract.FORWARD_AUDIT, contract.EVALUATOR_PROTOCOL, contract.RESULT,
                contract.POSTAUDIT, contract.OUTPUT_ROOT,
            )
        ),
        "protected_watchers_exact": contract.watcher_snapshot()
        == protocol["execution"]["protected_watchers"],
        "shared_api_lease_inactive": _lease_inactive(),
        "keyless_gpt56_endpoint_reachable": _endpoint_ready(),
        "conflicting_forward_or_evaluator_processes_absent": not _active_conflicts(),
        "privileged_runtime_field_findings_empty": not privileged,
        "evaluator_capability_findings_empty": not evaluator,
        "credential_literal_findings_empty": not secrets,
        "postfreeze_gold_surface_absent": not (ROOT / contract.POSTFREEZE_GOLD).exists(),
        "final_iana_url_not_preflighted": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    return contract.seal(
        {
            "artifact_version": 1,
            "role": "v25003_page_visible_link_external_preactivation_audit",
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


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v25003_page_visible_link_external_preactivation_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("authorization", {}).get("execution_start_generation") is not True
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.03 preactivation audit drifted")
    return copied


def build_start(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL, tracked=True))
    validate_preaudit(_read(contract.PREAUDIT, tracked=True))
    if not _future_pristine(
        (
            contract.EXECUTION_START, contract.FORWARD_RESULT, contract.FORWARD_AUDIT,
            contract.EVALUATOR_PROTOCOL, contract.RESULT, contract.POSTAUDIT,
            contract.OUTPUT_ROOT,
        )
    ):
        raise RuntimeError("V2.50.03 execution surface is not pristine")
    if not _lease_inactive() or not _endpoint_ready() or _active_conflicts():
        raise RuntimeError("V2.50.03 execution runtime is not ready")
    return contract.seal(
        {
            "artifact_version": 1,
            "role": "v25003_page_visible_link_external_execution_start",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()) if now is None else int(now),
            "git_head": contract.git(ROOT, "rev-parse", "HEAD"),
            "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
            "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
            "task_vector_sha256": protocol["population"]["task_vector_sha256"],
            "arm_order_vector_sha256": protocol["population"]["arm_order_vector_sha256"],
            "protected_watchers": contract.watcher_snapshot(),
            "prediction_and_postfreeze_gold_surfaces_pristine": True,
            "authorization": {
                "one_external_forward": True,
                "evaluator": False,
                "public_exact220_or_sota": False,
                "retry_resume_selective_rerun": False,
            },
        },
        "execution_start_payload_sha256",
    )


def validate_start(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL, tracked=True))
    if (
        copied.get("role") != "v25003_page_visible_link_external_execution_start"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or copied.get("preactivation_audit_sha256")
        != contract.sha256(ROOT / contract.PREAUDIT)
        or copied.get("task_vector_sha256")
        != protocol["population"]["task_vector_sha256"]
        or copied.get("arm_order_vector_sha256")
        != protocol["population"]["arm_order_vector_sha256"]
        or copied.get("protected_watchers") != contract.watcher_snapshot()
        or copied.get("authorization", {}).get("one_external_forward") is not True
        or copied.get("authorization", {}).get("evaluator") is not False
        or not contract.sealed(copied, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.50.03 execution start drifted")
    return copied


def _mechanism(rows: list[dict[str, Any]], gate: Mapping[str, Any]) -> dict[str, Any]:
    checked = [runtime.validate_result(row) for row in rows]
    control = contract.CONTROL_ARM
    candidate = contract.CANDIDATE_ARM
    metric = lambda row, arm, name: row["content_free_receipt"]["arm_metrics"][arm][name]
    terminal = len(checked)
    eligible = sum(
        row["content_free_receipt"]["visible_link_strategy_eligible"]
        for row in checked
    )
    selection_changed = sum(
        row["content_free_receipt"]["selection_changed"]
        for row in checked
    )
    shared_completed = sum(
        row["content_free_receipt"]["shared_first_wave_completed"]
        for row in checked
    )
    second_completed = sum(
        row["content_free_receipt"]["shared_second_wave_completed"]
        for row in checked
    )
    physical_queries_exact = all(
        row["content_free_receipt"]["physical_query_count"] == 4
        for row in checked
    )
    physical_fetches_bounded = all(
        row["content_free_receipt"]["physical_fetch_count"] <= 14
        for row in checked
    )
    both_success = sum(all(row["model_success"].values()) for row in checked)
    evidence_equal = all(
        row["evidence_characters"][control] == row["evidence_characters"][candidate]
        for row in checked
    )
    model_calls_bounded = all(
        row["content_free_receipt"]["model_logical_call_count"] <= 3
        for row in checked
    )
    planned_four = all(
        metric(row, arm, "planned_queries") == 4
        for row in checked for arm in contract.ARMS
    )
    executed_four = all(
        metric(row, arm, "executed_queries") == 4
        for row in checked for arm in contract.ARMS
    )
    executed_orders = [
        [
            row["content_free_receipt"]["first_synthesis_arm"],
            next(
                arm for arm in contract.ARMS
                if arm != row["content_free_receipt"]["first_synthesis_arm"]
            ),
        ]
        for row in checked
        if row["content_free_receipt"]["first_synthesis_arm"] in contract.ARMS
    ]
    order_exact = len(executed_orders) == terminal and executed_orders == contract.arm_order_vector()
    totals = {
        arm: {
            name: sum(metric(row, arm, name) for row in checked)
            for name in (
                "planned_queries", "executed_queries", "logical_fetch_attempts",
                "usable_pages", "second_wave_search_prefix_urls",
                "second_wave_visible_link_urls", "second_wave_bound_visible_links",
                "second_wave_target_bound_projected_pages",
                "second_wave_target_bound_records", "evidence_characters",
            )
        }
        for arm in contract.ARMS
    }
    total_bound_gain = sum(
        row["content_free_receipt"]["bound_visible_link_gain"] for row in checked
    )
    positive_bound = sum(
        row["content_free_receipt"]["bound_visible_link_gain"] > 0
        for row in checked
    )
    positive_projected_page = sum(
        row["content_free_receipt"]["candidate_target_bound_projected_page_gain"] > 0
        for row in checked
    )
    positive_record = sum(
        row["content_free_receipt"]["candidate_target_bound_record_gain"] > 0
        for row in checked
    )
    mechanism_engaged = sum(
        row["content_free_receipt"]["target_bound_record_mechanism_engaged"]
        for row in checked
    )
    prediction_changed = sum(row["prediction_changed"] for row in checked)
    passed = (
        terminal == gate["terminal_tasks"]
        and eligible >= gate["minimum_visible_link_strategy_eligible_tasks"]
        and shared_completed == gate["shared_first_wave_completed_tasks"]
        and second_completed == gate["shared_second_wave_completed_tasks"]
        and physical_queries_exact
        and physical_fetches_bounded
        and both_success >= gate["minimum_both_arms_model_success_tasks"]
        and evidence_equal
        and model_calls_bounded
        and planned_four
        and executed_four
        and order_exact
        and selection_changed >= gate["minimum_selection_changed_tasks"]
        and total_bound_gain >= gate["minimum_total_bound_visible_link_gain"]
        and positive_bound >= gate["minimum_tasks_with_positive_bound_visible_link_gain"]
        and totals[candidate]["second_wave_target_bound_projected_pages"]
        > totals[control]["second_wave_target_bound_projected_pages"]
        and positive_projected_page
        >= gate["minimum_tasks_with_positive_target_bound_projected_page_gain"]
        and totals[candidate]["second_wave_target_bound_records"]
        > totals[control]["second_wave_target_bound_records"]
        and positive_record
        >= gate["minimum_tasks_with_positive_target_bound_record_gain"]
        and mechanism_engaged
        >= gate["minimum_target_bound_record_mechanism_engaged_tasks"]
        and prediction_changed >= gate["minimum_prediction_changed_tasks"]
    )
    return {
        "terminal_tasks": terminal,
        "visible_link_strategy_eligible_tasks": eligible,
        "selection_changed_tasks": selection_changed,
        "shared_first_wave_completed_tasks": shared_completed,
        "shared_second_wave_completed_tasks": second_completed,
        "all_tasks_execute_exactly_four_physical_queries": physical_queries_exact,
        "all_tasks_fetch_at_most_fourteen_physical_pages": physical_fetches_bounded,
        "both_arms_model_success_tasks": both_success,
        "all_task_evidence_character_counts_equal_between_arms": evidence_equal,
        "completed_task_model_calls_at_most_three": model_calls_bounded,
        "all_tasks_plan_exactly_four_queries_per_arm": planned_four,
        "all_tasks_execute_exactly_four_queries_per_arm": executed_four,
        "executed_arm_order_matches_frozen_vector": order_exact,
        "total_bound_visible_link_gain": total_bound_gain,
        "tasks_with_positive_bound_visible_link_gain": positive_bound,
        "tasks_with_positive_target_bound_projected_page_gain": positive_projected_page,
        "tasks_with_positive_target_bound_record_gain": positive_record,
        "target_bound_record_mechanism_engaged_tasks": mechanism_engaged,
        "prediction_changed_tasks": prediction_changed,
        "arms": totals,
        "passed": passed,
    }


def build_forward_audit(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL, tracked=True))
    forward = _read(contract.FORWARD_RESULT, tracked=True)
    rows = _read_jsonl(contract.TASK_RESULTS)
    if (
        forward.get("role") != "v25003_page_visible_link_external_forward_result"
        or not contract.sealed(forward, "result_payload_sha256")
        or len(rows) != contract.TASK_COUNT
    ):
        raise RuntimeError("V2.50.03 frozen forward drifted")
    mechanism = _mechanism(rows, protocol["mechanism_gate_before_evaluator"])
    aggregate = forward.get("aggregate")
    checks = {
        "prediction_freeze_bound": forward.get("prediction_freeze_sha256")
        == contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "task_results_bound": forward.get("task_results_sha256")
        == contract.sha256(ROOT / contract.TASK_RESULTS),
        "all_rows_valid": mechanism["terminal_tasks"] == contract.TASK_COUNT,
        "forward_aggregate_terminal_bound": isinstance(aggregate, Mapping)
        and aggregate.get("terminal_tasks") == mechanism["terminal_tasks"],
        "forward_aggregate_eligibility_bound": isinstance(aggregate, Mapping)
        and aggregate.get("visible_link_strategy_eligible_tasks")
        == mechanism["visible_link_strategy_eligible_tasks"],
        "forward_aggregate_selection_change_bound": isinstance(aggregate, Mapping)
        and aggregate.get("selection_changed_tasks")
        == mechanism["selection_changed_tasks"],
        "forward_aggregate_shared_completion_bound": isinstance(aggregate, Mapping)
        and aggregate.get("shared_first_wave_completed_tasks")
        == mechanism["shared_first_wave_completed_tasks"],
        "forward_aggregate_second_wave_completion_bound": isinstance(aggregate, Mapping)
        and aggregate.get("shared_second_wave_completed_tasks")
        == mechanism["shared_second_wave_completed_tasks"],
        "forward_aggregate_physical_query_bound": isinstance(aggregate, Mapping)
        and aggregate.get("all_tasks_execute_exactly_four_physical_queries")
        == mechanism["all_tasks_execute_exactly_four_physical_queries"],
        "forward_aggregate_physical_fetch_bound": isinstance(aggregate, Mapping)
        and aggregate.get("all_tasks_fetch_at_most_fourteen_physical_pages")
        == mechanism["all_tasks_fetch_at_most_fourteen_physical_pages"],
        "forward_aggregate_model_success_bound": isinstance(aggregate, Mapping)
        and aggregate.get("both_arms_model_success_tasks")
        == mechanism["both_arms_model_success_tasks"],
        "forward_aggregate_prediction_change_bound": isinstance(aggregate, Mapping)
        and aggregate.get("prediction_changed_tasks")
        == mechanism["prediction_changed_tasks"],
        "forward_aggregate_bound_url_gain_bound": isinstance(aggregate, Mapping)
        and aggregate.get("total_bound_visible_link_gain")
        == mechanism["total_bound_visible_link_gain"],
        "forward_aggregate_positive_bound_tasks_bound": isinstance(aggregate, Mapping)
        and aggregate.get("tasks_with_positive_bound_visible_link_gain")
        == mechanism["tasks_with_positive_bound_visible_link_gain"],
        "forward_aggregate_positive_page_tasks_bound": isinstance(aggregate, Mapping)
        and aggregate.get("tasks_with_positive_target_bound_projected_page_gain")
        == mechanism["tasks_with_positive_target_bound_projected_page_gain"],
        "forward_aggregate_positive_record_tasks_bound": isinstance(aggregate, Mapping)
        and aggregate.get("tasks_with_positive_target_bound_record_gain")
        == mechanism["tasks_with_positive_target_bound_record_gain"],
        "forward_aggregate_mechanism_tasks_bound": isinstance(aggregate, Mapping)
        and aggregate.get("target_bound_record_mechanism_engaged_tasks")
        == mechanism["target_bound_record_mechanism_engaged_tasks"],
        "forward_aggregate_arm_totals_bound": isinstance(aggregate, Mapping)
        and isinstance(aggregate.get("arms"), Mapping)
        and all(
            aggregate["arms"].get(arm, {}).get(name)
            == mechanism["arms"][arm][name]
            for arm in contract.ARMS
            for name in (
                "planned_queries", "executed_queries", "logical_fetch_attempts",
                "usable_pages", "second_wave_search_prefix_urls",
                "second_wave_visible_link_urls", "second_wave_bound_visible_links",
                "second_wave_target_bound_projected_pages",
                "second_wave_target_bound_records", "evidence_characters",
            )
        ),
        "mapping_gold_evaluator_closed_during_forward": forward.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read"
        ) is False,
        "postfreeze_gold_absent": not (ROOT / contract.POSTFREEZE_GOLD).exists(),
        "protected_watchers_exact": contract.watcher_snapshot()
        == protocol["execution"]["protected_watchers"],
        "forward_process_absent": not _active_conflicts(),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    return contract.seal(
        {
            "artifact_version": 1,
            "role": "v25003_page_visible_link_external_forward_audit",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()) if now is None else int(now),
            "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
            "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
            "mechanism_gate": mechanism,
            "checks": checks,
            "findings": findings,
            "audit_valid": not findings,
            "authorization": {
                "postfreeze_external_evaluator_protocol": not findings
                and mechanism["passed"],
                "public_exact220_launch": False,
                "leaderboard_or_sota": False,
            },
        },
        "audit_payload_sha256",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("build", "protocol", "preaudit", "start", "audit")
    )
    args = parser.parse_args()
    if args.command == "build":
        value = build_audit()
        if not value["audit_valid"]:
            raise RuntimeError(f"V2.50.03 build audit failed: {value['findings']}")
        path = contract.BUILD_AUDIT
    elif args.command == "protocol":
        _clean_pushed()
        validate_build(_read(contract.BUILD_AUDIT, tracked=True))
        value = contract.build_protocol(ROOT, now=int(time.time()))
        path = contract.PROTOCOL
    elif args.command == "preaudit":
        value = build_preaudit()
        if not value["audit_valid"]:
            raise RuntimeError(f"V2.50.03 preaudit failed: {value['findings']}")
        path = contract.PREAUDIT
    elif args.command == "start":
        value = build_start()
        path = contract.EXECUTION_START
    else:
        value = build_forward_audit()
        path = contract.FORWARD_AUDIT
    _publish(path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "audit_valid": value.get("audit_valid"),
                "findings": value.get("findings"),
                "authorization": value.get("authorization"),
                "mechanism_gate": value.get("mechanism_gate"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
