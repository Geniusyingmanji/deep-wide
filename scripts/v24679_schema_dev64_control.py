#!/usr/bin/env python3
"""Freeze and activate the label-blind V2.46.79 paired-dev64 forward.

The pre-forward control plane never reads, hashes, imports, or opens mapping,
gold, category, split, question-type, score, reward, or evaluator resources.
Only the visible ``{opaque_id, question}`` population may cross the forward
boundary.  Evaluator controls are deliberately absent until both arms are
frozen and a separate post-forward reliability gate is published.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24679_schema_dev64_contract as contract  # noqa: E402
from scripts import audit_v24495_targeted_conversion_projection_build as common  # noqa: E402
from scripts import audit_v24680_schema_dev64_runtime_build as build_audit  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


BUILD_AUDIT = build_audit.AUDIT
FORWARD_FILES = (
    "src/deepwide_agent/__init__.py",
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/native_search.py",
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24259_deterministic_table_normalizer.py",
    "src/deepwide_agent/v24263_global_model_limiter.py",
    "src/deepwide_agent/v24267_total_fallback.py",
    "src/deepwide_agent/v24268_keyless_batched_runtime.py",
    "src/deepwide_agent/v24269_task_union_discovery.py",
    "src/deepwide_agent/v24270_budget_equivalent_union.py",
    "src/deepwide_agent/v24272_two_wave_entropy_voc.py",
    "src/deepwide_agent/v24272_two_wave_retrieval.py",
    "src/deepwide_agent/v24273_two_wave_task_runtime.py",
    "src/deepwide_agent/v24275_forward_contract.py",
    "src/deepwide_agent/v24275_hard_deadline_fetch.py",
    "src/deepwide_agent/v24280_task_union_single_shot.py",
    "src/deepwide_agent/v24286_visible_schema_runtime.py",
    "src/deepwide_agent/v24287_forward_contract.py",
    "src/deepwide_agent/v24287_hard_deadline_fetch.py",
    "src/deepwide_agent/v24289_low_coverage_rescue.py",
    "src/deepwide_agent/v24290_low_coverage_task_runtime.py",
    "src/deepwide_agent/v24294_staged_reserve.py",
    "src/deepwide_agent/v24296_staged_reserve_task_runtime.py",
    "src/deepwide_agent/v24299_synthesis_recovery.py",
    "src/deepwide_agent/v24308_child_exit_observability.py",
    "src/deepwide_agent/v24309_runner_exit_integration.py",
    "src/deepwide_agent/v24310_paired_dev_runtime.py",
    "src/deepwide_agent/v24312_deadline_reliability.py",
    "src/deepwide_agent/v24316_deadline_search.py",
    "src/deepwide_agent/v24318_deadline_conservation_runtime.py",
    "src/deepwide_agent/v24319_runner_integration.py",
    "src/deepwide_agent/v24468_total_wall_transport.py",
    "src/deepwide_agent/v24630_thin_backfill_search.py",
    "src/deepwide_agent/v24630_exact220_task_integration.py",
    "src/deepwide_agent/v24675_expanded_visible_schema.py",
    "src/deepwide_agent/v24677_expanded_visible_schema_runtime.py",
    "src/deepwide_agent/v24679_schema_dev64_contract.py",
    "scripts/deepwide_api_lease.py",
    "scripts/run_v24287_fetch_helper.py",
    "scripts/v24468_total_wall_http_helper.py",
    "scripts/run_v24679_schema_dev64_task.py",
    "scripts/run_v24679_schema_dev64.py",
)
CONTROL_FILES = (
    "scripts/v24679_schema_dev64_control.py",
    "tests/test_v24679_schema_dev64.py",
    "tests/test_v24679_schema_dev64_control.py",
    str(BUILD_AUDIT),
)
FOCUSED_TESTS = (
    ("test_v24318_deadline_conservation_runtime.py", 8),
    ("test_v24319_runner_integration.py", 7),
    ("test_v24630_exact220.py", 5),
    ("test_v24677_expanded_visible_schema_runtime.py", 8),
    ("test_v24679_schema_dev64.py", 9),
    ("test_v24679_schema_dev64_control.py", 10),
)
EXPECTED_FOCUSED_TEST_COUNT = 47
DECISION_CONTRACT = {
    "minimum_changed_candidate_tasks_for_evaluator_gate": 1,
    "maximum_baseline_runtime_failures_for_evaluator_gate": 4,
    "maximum_candidate_runtime_failures_for_evaluator_gate": 4,
    "maximum_real_child_runtime_failures_for_evaluator_gate": 4,
    "maximum_model_slot_timeouts_for_evaluator_gate": 0,
    "required_terminal_prediction_rows_per_arm": contract.SELECTED_COUNT,
    "minimum_whole_table_success_delta_for_go": 1,
    "minimum_quality_composite_delta_for_go": 0.0,
    "minimum_entity_acc_delta_for_go": 0.0,
    "minimum_f1_by_row_delta_for_go": 0.0,
    "minimum_f1_by_item_delta_for_go": 0.0,
    "minimum_column_f1_delta_for_go": 0.0,
    "maximum_candidate_minus_baseline_runtime_failures_for_go": 0,
    "maximum_candidate_minus_baseline_evaluator_failures_for_go": 0,
}
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)
OPAQUE_LITERAL = re.compile(r"task_[0-9a-f]{24}")


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    path = root / raw
    if (
        raw.is_absolute()
        or ".." in raw.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.46.79 expected repository file: {relative}")
    return path


def _read(root: Path, relative: str | Path) -> dict[str, Any]:
    return contract.read_object(_ordinary(root, relative))


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == contract.payload_sha256(unsigned)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _manifest(
    root: Path,
    files: Sequence[str],
    *,
    reject_opaque_literals: bool,
) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in files:
        path = _ordinary(root, relative)
        source = path.read_text(encoding="utf-8")
        if SECRET.search(source):
            raise RuntimeError(f"V2.46.79 credential literal in {relative}")
        if reject_opaque_literals and OPAQUE_LITERAL.search(source):
            raise RuntimeError(f"V2.46.79 opaque task literal in {relative}")
        output[relative] = contract.sha256(path)
    return output


def _field_and_import_findings(root: Path) -> tuple[list[str], list[str]]:
    accesses: list[str] = []
    imports: list[str] = []
    for relative in FORWARD_FILES:
        current_accesses, current_imports = common.ast_findings(Path(relative))
        accesses.extend(current_accesses)
        imports.extend(current_imports)
    allowed = {"src/deepwide_agent/clients.py:565:score"}
    return sorted(set(accesses) - allowed), sorted(set(imports))


def _parent(root: Path) -> dict[str, Any]:
    value = _read(root, BUILD_AUDIT)
    build_audit.validate_audit(value)
    if (
        value.get("role") != "v24680_schema_dev64_runtime_build_audit"
        or value.get("findings") != []
        or value.get("authorization")
        != {
            "forward_contract_publication": True,
            "preactivation_or_launch": False,
            "evaluator": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.79 build-audit parent drifted")
    return value


def _port_listening() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=0.5):
            return True
    except OSError:
        return False


def _active(marker: str) -> bool:
    completed = subprocess.run(
        ["ps", "-eo", "cmd="],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    return any(
        marker in line
        for line in completed.stdout.splitlines()
        if "ps -eo" not in line and "v24679_schema_dev64_control.py" not in line
    )


def _run_tests() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for filename, expected in FOCUSED_TESTS:
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
                filename,
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
            timeout=300,
            check=False,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(match.group(1)) if match else 0
        output.append(
            {
                "file": filename,
                "expected_test_count": expected,
                "observed_test_count": observed,
                "passed": completed.returncode == 0 and observed == expected,
            }
        )
    return output


def _future_pristine(root: Path, paths: Sequence[Path]) -> bool:
    return all(
        not (root / path).exists() and not (root / path).is_symlink()
        for path in paths
    )


def build_forward_contract(
    root: Path = ROOT,
    *,
    now: int | None = None,
    require_pristine: bool = True,
    require_clean: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    _parent(root)
    if require_clean and (
        _git(root, "rev-parse", "HEAD") != _git(root, "rev-parse", "target/main")
        or _git(root, "status", "--porcelain")
    ):
        raise RuntimeError("V2.46.79 contract requires clean pushed HEAD")
    future = (
        contract.FORWARD_CONTRACT,
        contract.PROTOCOL,
        contract.PREAUDIT,
        contract.ACTIVATION,
        contract.EXECUTION_START,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.OUTPUT_ROOT,
    )
    if require_pristine and not _future_pristine(root, future):
        raise RuntimeError("V2.46.79 contract future surface is not pristine")
    ids = contract.source_selected_ids(root)
    dependencies = _manifest(root, FORWARD_FILES, reject_opaque_literals=True)
    value = {
        "artifact_version": 1,
        "role": contract.ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "parent_evidence": {
            "v24680_build_audit_path": str(BUILD_AUDIT),
            "v24680_build_audit_sha256": contract.sha256(root / BUILD_AUDIT),
        },
        "task_contract": {
            "runtime_boundary": ["opaque_id", "question"],
            "selected_count": contract.SELECTED_COUNT,
            "selected_opaque_ids": ids,
            "selected_opaque_ids_sha256": contract.payload_sha256(ids),
            "manifest_path": str(contract.SOURCE_MANIFEST),
            "manifest_sha256": contract.sha256(root / contract.SOURCE_MANIFEST),
            "id_source_path": str(contract.ID_SOURCE),
            "id_source_sha256": contract.sha256(root / contract.ID_SOURCE),
            "historical_dev_population_not_unseen": True,
            "mapping_gold_category_question_type_split_score_or_reward_read": False,
        },
        "execution": {
            "selected_tasks": contract.SELECTED_COUNT,
            "expected_treated_tasks": contract.EXPECTED_TREATED_COUNT,
            "total_child_runs": contract.TOTAL_CHILD_RUNS,
            "executor_concurrency": contract.EXECUTOR_CONCURRENCY,
            "model_slot_cap": contract.MODEL_SLOT_CAP,
            "model_slot_pool_id": contract.MODEL_SLOT_POOL_ID,
            "output_root": str(contract.OUTPUT_ROOT),
            "runner_marker": contract.RUNNER_MARKER,
            "child_marker": contract.CHILD_MARKER,
            "protected_watchers": contract.protected_watcher_snapshot(),
        },
        "fixed_denominator_contract": {
            "fresh_baseline_children": contract.SELECTED_COUNT,
            "fresh_candidate_children_only_for_incremental_schema_tasks": (
                contract.EXPECTED_TREATED_COUNT
            ),
            "same_run_baseline_exact_reuse_candidate_tasks": (
                contract.SELECTED_COUNT - contract.EXPECTED_TREATED_COUNT
            ),
            "terminal_prediction_rows_per_arm": contract.SELECTED_COUNT,
            "parent_timeout_or_failure_projects_nonempty_fallback": True,
            "failure_as_zero": True,
            "no_resume_retry_skip_selective_rerun_or_revaluation": True,
        },
        "limits": dict(contract.LIMITS),
        "two_wave_policy": dict(contract.TWO_WAVE_POLICY),
        "model": dict(contract.MODEL),
        "search": dict(contract.SEARCH),
        "lease": {
            "path": str(contract.LEASE_PATH),
            "owner": contract.LEASE_OWNER,
            "purpose": contract.LEASE_PURPOSE,
            "single_owner_nonblocking": True,
        },
        "source_policy": {
            "runtime_input_keys": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "evaluator_surface_absent_from_forward_dependency_manifest": True,
            "credential_read_hashed_persisted_or_emitted": False,
        },
        "authorization": {
            "preactivation_audit_generation": True,
            "activation_or_launch": False,
            "evaluator": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        },
        "dependency_manifest": dependencies,
        "dependency_manifest_sha256": contract.payload_sha256(dependencies),
    }
    value["contract_payload_sha256"] = contract.payload_sha256(value)
    return value


def build_protocol(
    root: Path = ROOT,
    *,
    now: int | None = None,
    require_pristine: bool = True,
    require_clean: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    forward = contract.validate_forward_contract(root)
    if require_clean and (
        _git(root, "rev-parse", "HEAD") != _git(root, "rev-parse", "target/main")
        or _git(root, "status", "--porcelain")
    ):
        raise RuntimeError("V2.46.79 protocol requires clean pushed HEAD")
    future = (
        contract.PROTOCOL,
        contract.PREAUDIT,
        contract.ACTIVATION,
        contract.EXECUTION_START,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.OUTPUT_ROOT,
    )
    if require_pristine and not _future_pristine(root, future):
        raise RuntimeError("V2.46.79 protocol future surface is not pristine")
    controls = _manifest(root, CONTROL_FILES, reject_opaque_literals=False)
    value = {
        "artifact_version": 1,
        "role": "v24679_schema_dev64_preregistration",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "forward_contract_sha256": contract.sha256(root / contract.FORWARD_CONTRACT),
        "dependency_manifest_sha256": forward["dependency_manifest_sha256"],
        "control_manifest": controls,
        "control_manifest_sha256": contract.payload_sha256(controls),
        "task_contract": {
            "historical_dev_population_not_unseen": True,
            "selected_per_arm": contract.SELECTED_COUNT,
            "fresh_baseline_children": contract.SELECTED_COUNT,
            "fresh_candidate_children": contract.EXPECTED_TREATED_COUNT,
            "exact_same_run_control_reuse_candidate_tasks": (
                contract.SELECTED_COUNT - contract.EXPECTED_TREATED_COUNT
            ),
            "real_child_runs": contract.TOTAL_CHILD_RUNS,
            "fixed_denominator_per_arm": contract.SELECTED_COUNT,
            "failure_as_zero": True,
            "no_resume_retry_skip_selective_rerun_or_revaluation": True,
        },
        "causal_treatment": {
            "baseline": "frozen_visible_schema_parser_and_frozen_v24630_pipeline",
            "candidate": "expanded_visible_schema_parser_only_when_frozen_parser_abstains",
            "treated_tasks": contract.EXPECTED_TREATED_COUNT,
            "untreated_candidate_exactly_reuses_same_run_baseline": True,
            "model_query_fetch_token_deadline_search_title_backfill_or_synthesis_policy_changed": False,
            "module_global_parser_mutated": False,
        },
        "decision_contract": dict(DECISION_CONTRACT),
        "postfreeze_evaluator_policy": {
            "evaluator_mapping_gold_query_answer_category_split_score_or_reward_opened_or_hashed_pre_freeze": False,
            "evaluator_code_imported_by_forward_or_pre_freeze_control": False,
            "separate_evaluator_gate_required_after_both_arm_prediction_freezes": True,
            "changed_candidate_tasks_zero_is_direct_no_go_without_evaluator": True,
            "all_64_frozen_predictions_per_arm_evaluated_on_fixed_denominator": True,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read_by_forward": False,
            "both_arm_prediction_freezes_before_evaluator_resource_open": True,
        },
        "authorization": {
            "preactivation_audit_generation": True,
            "single_fresh_paired_dev64_forward_after_activation_and_start": False,
            "evaluator": False,
            "exact220": False,
            "avg_at_4_leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = contract.payload_sha256(value)
    return validate_protocol(root, value=value)


def validate_protocol(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    protocol = dict(value) if value is not None else _read(root, contract.PROTOCOL)
    forward = contract.validate_forward_contract(root)
    controls = protocol.get("control_manifest")
    if (
        protocol.get("role") != "v24679_schema_dev64_preregistration"
        or protocol.get("protocol_id") != contract.PROTOCOL_ID
        or protocol.get("forward_contract_sha256")
        != contract.sha256(root / contract.FORWARD_CONTRACT)
        or protocol.get("dependency_manifest_sha256")
        != forward["dependency_manifest_sha256"]
        or not isinstance(controls, Mapping)
        or controls != _manifest(root, CONTROL_FILES, reject_opaque_literals=False)
        or protocol.get("control_manifest_sha256")
        != contract.payload_sha256(controls)
        or protocol.get("decision_contract") != DECISION_CONTRACT
        or protocol.get("task_contract", {}).get("selected_per_arm")
        != contract.SELECTED_COUNT
        or protocol.get("task_contract", {}).get("real_child_runs")
        != contract.TOTAL_CHILD_RUNS
        or protocol.get("task_contract", {}).get("failure_as_zero") is not True
        or protocol.get("causal_treatment", {}).get(
            "untreated_candidate_exactly_reuses_same_run_baseline"
        )
        is not True
        or protocol.get("postfreeze_evaluator_policy", {}).get(
            "evaluator_mapping_gold_query_answer_category_split_score_or_reward_opened_or_hashed_pre_freeze"
        )
        is not False
        or protocol.get("postfreeze_evaluator_policy", {}).get(
            "separate_evaluator_gate_required_after_both_arm_prediction_freezes"
        )
        is not True
        or protocol.get("authorization")
        != {
            "preactivation_audit_generation": True,
            "single_fresh_paired_dev64_forward_after_activation_and_start": False,
            "evaluator": False,
            "exact220": False,
            "avg_at_4_leaderboard_or_sota": False,
        }
        or not _sealed(protocol, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.46.79 protocol drifted")
    return protocol


def build_preaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    forward = contract.validate_forward_contract(root)
    protocol = validate_protocol(root)
    suites = _run_tests()
    fields, imports = _field_and_import_findings(root)
    lease = lease_observation(root, Path("/proc"))
    head = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "rev-parse", "target/main")
    clean = _git(root, "status", "--porcelain") == ""
    future = (
        contract.PREAUDIT,
        contract.ACTIVATION,
        contract.EXECUTION_START,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.OUTPUT_ROOT,
    )
    pristine = _future_pristine(root, future)
    secrets = [
        relative
        for relative in (*FORWARD_FILES, *CONTROL_FILES)
        if SECRET.search(_ordinary(root, relative).read_text(encoding="utf-8"))
    ]
    treated = sum(
        contract.is_treated_task(task)
        for task in contract.selected_tasks(root, forward)
    )
    active = _active(contract.RUNNER_MARKER) or _active(contract.CHILD_MARKER)
    proxy = _port_listening()
    watchers = contract.protected_watcher_snapshot()
    test_count = sum(item["observed_test_count"] for item in suites)
    findings: list[str] = []
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_FOCUSED_TEST_COUNT:
        findings.append("focused_tests_failed_or_count_drifted")
    if fields:
        findings.append("privileged_field_access_in_forward_surface")
    if imports:
        findings.append("evaluator_import_in_forward_surface")
    if secrets:
        findings.append("credential_literal_in_control_or_forward_surface")
    if treated != contract.EXPECTED_TREATED_COUNT:
        findings.append("treated_population_drifted")
    if not proxy:
        findings.append("keyless_proxy_not_listening")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if active:
        findings.append("v24679_forward_process_already_active")
    if head != remote:
        findings.append("protocol_commit_not_pushed")
    if not clean:
        findings.append("worktree_not_clean")
    if not pristine:
        findings.append("future_surface_not_pristine")
    if watchers != forward["execution"]["protected_watchers"]:
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24679_schema_dev64_preactivation_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "forward_contract_sha256": contract.sha256(root / contract.FORWARD_CONTRACT),
        "protocol_sha256": contract.sha256(root / contract.PROTOCOL),
        "dependency_manifest_sha256": forward["dependency_manifest_sha256"],
        "control_manifest_sha256": protocol["control_manifest_sha256"],
        "focused_tests": suites,
        "focused_test_count": test_count,
        "unexpected_privileged_field_accesses": fields,
        "evaluator_import_hits": imports,
        "credential_literal_hits": secrets,
        "selected_visible_tasks": contract.SELECTED_COUNT,
        "treated_visible_tasks": treated,
        "protected_watchers": watchers,
        "checks": {
            "focused_tests_passed": all(item["passed"] for item in suites),
            "forward_label_blind_ast": not fields and not imports,
            "keyless_proxy_listening_without_api_request": proxy,
            "shared_api_lease_inactive": lease.get("active") is False,
            "no_v24679_runner_active": not active,
            "head_equals_target_main": head == remote,
            "worktree_clean": clean,
            "future_surface_pristine": pristine,
            "mapping_gold_category_question_type_split_evaluator_score_reward_opened_hashed_or_imported": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "launch_authorized": not findings,
        "authorization": {
            "one_fresh_72_child_paired_dev64_forward": not findings,
            "evaluator": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    if findings:
        raise RuntimeError("V2.46.79 preaudit failed: " + ",".join(findings))
    return value


def validate_preaudit(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(root, contract.PREAUDIT)
    if (
        value.get("role") != "v24679_schema_dev64_preactivation_audit"
        or value.get("protocol_id") != contract.PROTOCOL_ID
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("launch_authorized") is not True
        or value.get("focused_test_count") != EXPECTED_FOCUSED_TEST_COUNT
        or value.get("forward_contract_sha256")
        != contract.sha256(root / contract.FORWARD_CONTRACT)
        or value.get("protocol_sha256") != contract.sha256(root / contract.PROTOCOL)
        or value.get("protected_watchers") != contract.protected_watcher_snapshot()
        or value.get("authorization")
        != {
            "one_fresh_72_child_paired_dev64_forward": True,
            "evaluator": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.79 preaudit drifted")
    validate_protocol(root)
    return value


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    forward = contract.validate_forward_contract(root)
    audit = validate_preaudit(root)
    head = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "rev-parse", "target/main")
    clean = _git(root, "status", "--porcelain") == ""
    future = (
        contract.ACTIVATION,
        contract.EXECUTION_START,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.OUTPUT_ROOT,
    )
    lease = lease_observation(root, Path("/proc"))
    active = _active(contract.RUNNER_MARKER) or _active(contract.CHILD_MARKER)
    proxy = _port_listening()
    findings: list[str] = []
    if head != remote:
        findings.append("preaudit_commit_not_pushed")
    if not clean:
        findings.append("worktree_not_clean")
    if not _future_pristine(root, future):
        findings.append("activation_or_execution_surface_not_pristine")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if active:
        findings.append("v24679_forward_process_already_active")
    if not proxy:
        findings.append("keyless_proxy_not_listening")
    if contract.protected_watcher_snapshot() != forward["execution"]["protected_watchers"]:
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24679_schema_dev64_activation",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "active" if not findings else "rejected",
        "findings": findings,
        "launch_authorized": not findings,
        "forward_contract_sha256": contract.sha256(root / contract.FORWARD_CONTRACT),
        "protocol_sha256": contract.sha256(root / contract.PROTOCOL),
        "preaudit_sha256": contract.sha256(root / contract.PREAUDIT),
        "selected_pair_tasks": contract.SELECTED_COUNT,
        "real_child_runs": contract.TOTAL_CHILD_RUNS,
        "executor_concurrency": contract.EXECUTOR_CONCURRENCY,
        "model_slot_cap": contract.MODEL_SLOT_CAP,
        "protected_watchers": audit["protected_watchers"],
        "network_model_search_fetch_evaluator_or_api_called": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "authorization": {
            "one_forward_launch": not findings,
            "evaluator": False,
            "exact220": False,
        },
    }
    value["activation_payload_sha256"] = contract.payload_sha256(value)
    if findings:
        raise RuntimeError("V2.46.79 activation failed: " + ",".join(findings))
    return value


def validate_activation(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(root, contract.ACTIVATION)
    if (
        value.get("role") != "v24679_schema_dev64_activation"
        or value.get("protocol_id") != contract.PROTOCOL_ID
        or value.get("status") != "active"
        or value.get("findings") != []
        or value.get("launch_authorized") is not True
        or value.get("forward_contract_sha256")
        != contract.sha256(root / contract.FORWARD_CONTRACT)
        or value.get("protocol_sha256") != contract.sha256(root / contract.PROTOCOL)
        or value.get("preaudit_sha256") != contract.sha256(root / contract.PREAUDIT)
        or value.get("protected_watchers") != contract.protected_watcher_snapshot()
        or value.get("authorization")
        != {"one_forward_launch": True, "evaluator": False, "exact220": False}
        or not _sealed(value, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.46.79 activation drifted")
    validate_preaudit(root)
    return value


def build_execution_start(
    root: Path = ROOT, *, now: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    activation = validate_activation(root)
    head = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "rev-parse", "target/main")
    clean = _git(root, "status", "--porcelain") == ""
    future = (
        contract.EXECUTION_START,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.OUTPUT_ROOT,
    )
    lease = lease_observation(root, Path("/proc"))
    active = _active(contract.RUNNER_MARKER) or _active(contract.CHILD_MARKER)
    findings: list[str] = []
    if head != remote:
        findings.append("activation_commit_not_pushed")
    if not clean:
        findings.append("worktree_not_clean")
    if not _future_pristine(root, future):
        findings.append("execution_surface_not_pristine")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if active:
        findings.append("v24679_forward_process_already_active")
    if not _port_listening():
        findings.append("keyless_proxy_not_listening")
    if activation["protected_watchers"] != contract.protected_watcher_snapshot():
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24679_schema_dev64_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "authorized" if not findings else "rejected",
        "findings": findings,
        "execution_authorized": not findings,
        "activation_base_commit": head,
        "target_main_at_start": remote,
        "forward_contract_sha256": contract.sha256(root / contract.FORWARD_CONTRACT),
        "protocol_sha256": contract.sha256(root / contract.PROTOCOL),
        "preaudit_sha256": contract.sha256(root / contract.PREAUDIT),
        "activation_sha256": contract.sha256(root / contract.ACTIVATION),
        "selected_pair_tasks": contract.SELECTED_COUNT,
        "real_child_runs": contract.TOTAL_CHILD_RUNS,
        "executor_concurrency": contract.EXECUTOR_CONCURRENCY,
        "model_slot_cap": contract.MODEL_SLOT_CAP,
        "protected_watchers": activation["protected_watchers"],
        "api_called_before_execution_start": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "authorization": {
            "one_fresh_paired_dev64_forward": not findings,
            "evaluator": False,
            "exact220": False,
        },
    }
    value["execution_start_payload_sha256"] = contract.payload_sha256(value)
    if findings:
        raise RuntimeError("V2.46.79 execution start failed: " + ",".join(findings))
    return value


def validate_execution_start(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(root, contract.EXECUTION_START)
    if (
        value.get("role") != "v24679_schema_dev64_execution_start"
        or value.get("protocol_id") != contract.PROTOCOL_ID
        or value.get("status") != "authorized"
        or value.get("findings") != []
        or value.get("execution_authorized") is not True
        or value.get("activation_base_commit") != value.get("target_main_at_start")
        or value.get("forward_contract_sha256")
        != contract.sha256(root / contract.FORWARD_CONTRACT)
        or value.get("protocol_sha256") != contract.sha256(root / contract.PROTOCOL)
        or value.get("preaudit_sha256") != contract.sha256(root / contract.PREAUDIT)
        or value.get("activation_sha256") != contract.sha256(root / contract.ACTIVATION)
        or value.get("selected_pair_tasks") != contract.SELECTED_COUNT
        or value.get("real_child_runs") != contract.TOTAL_CHILD_RUNS
        or value.get("executor_concurrency") != contract.EXECUTOR_CONCURRENCY
        or value.get("model_slot_cap") != contract.MODEL_SLOT_CAP
        or value.get("protected_watchers") != contract.protected_watcher_snapshot()
        or value.get("api_called_before_execution_start") is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get("authorization")
        != {
            "one_fresh_paired_dev64_forward": True,
            "evaluator": False,
            "exact220": False,
        }
        or not _sealed(value, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.46.79 execution start drifted")
    validate_activation(root)
    return value


def publish(path: Path, value: Mapping[str, Any]) -> None:
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("contract", "protocol", "preaudit", "activation", "start")
    )
    args = parser.parse_args()
    if args.command == "contract":
        value, path = build_forward_contract(), contract.FORWARD_CONTRACT
    elif args.command == "protocol":
        value, path = build_protocol(), contract.PROTOCOL
    elif args.command == "preaudit":
        value, path = build_preaudit(), contract.PREAUDIT
    elif args.command == "activation":
        value, path = build_activation(), contract.ACTIVATION
    else:
        value, path = build_execution_start(), contract.EXECUTION_START
    publish(ROOT / path, value)
    print(json.dumps({"path": str(path), "command": args.command}, sort_keys=True))


if __name__ == "__main__":
    main()
