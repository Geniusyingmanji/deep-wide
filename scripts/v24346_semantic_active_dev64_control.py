#!/usr/bin/env python3
"""Freeze and activate the V2.43.46 shared-forward paired-dev64 gate."""

from __future__ import annotations

import argparse
import ast
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

from deepwide_agent.v24346_forward_contract import (  # noqa: E402
    ACTIVATION,
    ARMS,
    CHILD_MARKER,
    CHILD_TERMINAL_NAME,
    EVALUATOR_IDENTITY_PARENT,
    EVALUATOR_LEASE_OWNER,
    EVALUATOR_LEASE_PURPOSE,
    EXECUTION_START,
    EXECUTOR_CONCURRENCY,
    FINAL_RESULT,
    FORWARD_CONTRACT,
    FORWARD_RESULT,
    ID_SOURCE,
    LEASE_OWNER,
    LEASE_PATH,
    LEASE_PURPOSE,
    LIMITS,
    MODEL,
    MODEL_SLOT_CAP,
    OUTPUT_ROOT,
    PAIR_SUMMARY,
    PARENT_AUDIT,
    PARENT_DECISION,
    PARENT_EXIT_NAME,
    POSTAUDIT,
    PREAUDIT,
    PREDICTION_FREEZE,
    PROTOCOL,
    PROTOCOL_ID,
    ROLE,
    RUNNER_MARKER,
    RUNTIME_PREDICTIONS,
    RUN_SUMMARY,
    SEARCH,
    SELECTED_COUNT,
    SOURCE_MANIFEST,
    TASK_ROOT,
    payload_sha256,
    protected_watcher_snapshot,
    read_object,
    selected_tasks,
    sha256,
    source_selected_ids,
    validate_forward_contract,
)
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402


EVALUATOR_WORKERS_PER_ARM = 4
TOTAL_EVALUATOR_WORKERS = 8
MAPPING_PATH = Path("outputs/runtime_manifest_v1_repro/evaluator_mapping.jsonl")
BOOTSTRAP_SEED = 24346
BOOTSTRAP_RESAMPLES = 10_000
DECISION_CONTRACT = {
    "minimum_quality_composite_delta": 0.0,
    "minimum_entity_acc_delta": -0.005,
    "minimum_f1_by_row_delta": -0.005,
    "minimum_f1_by_item_delta": -0.005,
    "minimum_column_f1_delta": -0.005,
    "minimum_whole_table_success_delta": 0,
    "maximum_candidate_evaluator_invalid_or_not_run": 2,
    "maximum_candidate_minus_baseline_evaluator_invalid": 1,
    "maximum_failed_pair_tasks": 0,
    "minimum_effect_accounting_complete_tasks": SELECTED_COUNT,
    "minimum_shared_raw_page_tasks": SELECTED_COUNT,
    "minimum_fetch_before_baseline_tasks": SELECTED_COUNT,
    "minimum_semantic_projection_tasks": 1,
    "minimum_eligible_support_tasks": 1,
    "minimum_revision_model_admitted_tasks": 1,
    "minimum_revision_gate_tasks": 1,
    "minimum_candidate_nonidentity_tasks": 1,
    "minimum_admitted_cell_changes": 1,
    "minimum_credited_conditional_entropy_reduction_nats": 0.000001,
    "required_repeated_upstream_effects": 0,
    "maximum_slot_timeouts": 0,
    "maximum_provider_deadline_failures": 0,
    "maximum_hard_fetch_deadline_failures": 4,
    "maximum_fetch_helper_failures": 4,
    "maximum_hosted_search_deadline_failures": 4,
    "maximum_fetch_deadline_rejections": 8,
    "maximum_deadline_exhausted_tasks": 0,
    "minimum_paired_bootstrap_95_lower_bound": -0.05,
    "maximum_paired_bootstrap_95_interval_width": 0.16,
    "minimum_paired_median_delta": 0.0,
    "paired_bootstrap_seed": BOOTSTRAP_SEED,
    "paired_bootstrap_resamples": BOOTSTRAP_RESAMPLES,
}
FORWARD_FILES = (
    "src/deepwide_agent/__init__.py",
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/native_search.py",
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24259_deterministic_table_normalizer.py",
    "src/deepwide_agent/v24263_global_model_limiter.py",
    "src/deepwide_agent/v24269_task_union_discovery.py",
    "src/deepwide_agent/v24286_visible_schema_runtime.py",
    "src/deepwide_agent/v24287_hard_deadline_fetch.py",
    "src/deepwide_agent/v24308_child_exit_observability.py",
    "src/deepwide_agent/v24309_runner_exit_integration.py",
    "src/deepwide_agent/v24312_deadline_reliability.py",
    "src/deepwide_agent/v24313_runner_integration.py",
    "src/deepwide_agent/v24316_deadline_search.py",
    "src/deepwide_agent/v24323_shared_prefix_cell_entropy.py",
    "src/deepwide_agent/v24324_shared_prefix_runner.py",
    "src/deepwide_agent/v24325_shared_prefix_revision_runtime.py",
    "src/deepwide_agent/v24333_programmatic_support_catalog.py",
    "src/deepwide_agent/v24334_support_catalog_revision_gate.py",
    "src/deepwide_agent/v24335_programmatic_support_runtime.py",
    "src/deepwide_agent/v24339_active_evidence_support.py",
    "src/deepwide_agent/v24341_semantic_evidence_projection.py",
    "src/deepwide_agent/v24342_semantic_active_runtime.py",
    "src/deepwide_agent/v24343_semantic_active_runner.py",
    "src/deepwide_agent/v24346_forward_contract.py",
    "scripts/run_v24287_fetch_helper.py",
    "scripts/run_v24346_semantic_active_dev64_task.py",
    "scripts/run_v24346_semantic_active_dev64.py",
    "scripts/deepwide_api_lease.py",
)
CONTROL_FILES = (
    "scripts/v24346_semantic_active_dev64_control.py",
    "scripts/finalize_v24346_semantic_active_dev64.py",
    "scripts/run_official_eval_local.py",
    "scripts/finalize_fullset_rollout.py",
    "tests/test_v24346_semantic_active_dev64.py",
)
FOCUSED_TESTS = (
    "test_v24342_semantic_active_runtime.py",
    "test_v24343_semantic_active_runner.py",
    "test_v24345_semantic_active_natural_admission.py",
    "test_v24346_semantic_active_dev64.py",
)
FUTURE_PATHS = (
    PREAUDIT,
    ACTIVATION,
    EXECUTION_START,
    FORWARD_RESULT,
    FINAL_RESULT,
    POSTAUDIT,
    OUTPUT_ROOT,
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)
OPAQUE_LITERAL = re.compile(r"task_[0-9a-f]{24}")
PRIVILEGED = frozenset(
    {
        "benchmark_question_type", "question_type", "task_category", "category",
        "split", "ground_truth", "gold", "answer_key", "mapping", "evaluator",
        "score", "reward", "results.csv",
    }
)


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
        raise RuntimeError(f"V2.43.46 expected ordinary file: {relative}")
    return path


def _read(root: Path, relative: str | Path) -> dict[str, Any]:
    return read_object(_ordinary(root, relative))


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, timeout=20,
    ).stdout.strip()


def _manifest(
    root: Path, files: Sequence[str], *, reject_opaque_literals: bool
) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in files:
        path = _ordinary(root, relative)
        source = path.read_text(encoding="utf-8")
        if SECRET.search(source):
            raise RuntimeError(f"V2.43.46 credential literal in {relative}")
        if reject_opaque_literals and OPAQUE_LITERAL.search(source):
            raise RuntimeError(f"V2.43.46 opaque task literal in {relative}")
        output[relative] = sha256(path)
    return output


def _field_accesses(root: Path) -> list[str]:
    hits: list[str] = []
    for relative in FORWARD_FILES:
        tree = ast.parse(_ordinary(root, relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            key: str | None = None
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                key = node.args[0].value
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
            ):
                key = node.slice.value
            if key is not None and key.casefold() in PRIVILEGED:
                if relative == "src/deepwide_agent/clients.py" and key.casefold() == "score":
                    continue
                hits.append(f"{relative}:{node.lineno}:{key}")
    return sorted(hits)


def _import_hits(root: Path) -> list[str]:
    hits: list[str] = []
    forbidden = ("finalize", "official_eval", "evaluator", "mapping")
    for relative in FORWARD_FILES:
        tree = ast.parse(_ordinary(root, relative).read_text(encoding="utf-8"))
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.append(node.module or "")
        for name in names:
            if any(token in name.casefold() for token in forbidden):
                hits.append(f"{relative}:{name}")
    return sorted(hits)


def _run_tests() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for filename in FOCUSED_TESTS:
        completed = subprocess.run(
            [
                str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest",
                "discover", "-s", "tests", "-p", filename,
            ],
            cwd=ROOT,
            env={
                "HOME": str(Path.home()),
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
            timeout=300,
            check=False,
            text=True,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        output.append(
            {
                "file": filename,
                "passed": completed.returncode == 0,
                "test_count": int(match.group(1)) if match else 0,
            }
        )
    return output


def _port_listening() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=0.5):
            return True
    except OSError:
        return False


def _parent(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    decision = _read(root, PARENT_DECISION)
    audit = _read(root, PARENT_AUDIT)
    if (
        decision.get("status") != "natural_admission_go"
        or decision.get("passed") is not True
        or decision.get("authorization", {}).get("fresh_paired_benchmark_design") is not True
        or not _sealed(decision, "decision_payload_sha256")
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get("fresh_paired_benchmark_design") is not True
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.46 natural-admission parent drifted")
    return decision, audit


def _evaluator_contract(root: Path) -> dict[str, Any]:
    value = _read(root, EVALUATOR_IDENTITY_PARENT)
    evaluator = value.get("evaluator_contract")
    if (
        not isinstance(evaluator, Mapping)
        or evaluator.get("mapping_query_answer_or_gold_bytes_opened_or_hashed") is not False
        or value.get("source_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward"
        )
        is not False
    ):
        raise RuntimeError("V2.43.46 evaluator identity parent drifted")
    return json.loads(json.dumps(evaluator))


def build_forward_contract(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    _parent(root)
    ids = source_selected_ids(root)
    future = (PREAUDIT, ACTIVATION, EXECUTION_START, FORWARD_RESULT, OUTPUT_ROOT)
    if require_pristine and any((root / path).exists() or (root / path).is_symlink() for path in future):
        raise RuntimeError("V2.43.46 forward future surface is not pristine")
    dependencies = _manifest(root, FORWARD_FILES, reject_opaque_literals=True)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "parent_evidence": {
            "decision": {"path": str(PARENT_DECISION), "sha256": sha256(root / PARENT_DECISION)},
            "postaudit": {"path": str(PARENT_AUDIT), "sha256": sha256(root / PARENT_AUDIT)},
        },
        "task_contract": {
            "runtime_boundary": ["opaque_id", "question"],
            "selected_count": SELECTED_COUNT,
            "selected_opaque_ids": ids,
            "selected_opaque_ids_sha256": payload_sha256(ids),
            "manifest_path": str(SOURCE_MANIFEST),
            "manifest_sha256": sha256(root / SOURCE_MANIFEST),
            "id_source_path": str(ID_SOURCE),
            "id_source_sha256": sha256(root / ID_SOURCE),
            "mapping_split_category_gold_score_used_for_selection": False,
        },
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "one_shared_forward_per_visible_task": True,
            "two_predictions_from_each_single_task_forward": True,
            "same_raw_pages_for_both_predictions": True,
            "candidate_only_semantic_catalog_and_entropy_gate": True,
            "resume_skip_rerun_or_selective_retry": False,
            "runner_marker": RUNNER_MARKER,
            "child_marker": CHILD_MARKER,
            "output_root": str(OUTPUT_ROOT),
            "child_terminal_receipt_name": CHILD_TERMINAL_NAME,
            "parent_exit_receipt_name": PARENT_EXIT_NAME,
            "protected_watchers": protected_watcher_snapshot(),
        },
        "limits": dict(LIMITS),
        "model": dict(MODEL),
        "search": dict(SEARCH),
        "lease": {
            "path": str(LEASE_PATH), "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE, "nonblocking_single_owner": True,
        },
        "source_policy": {
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "evaluator_surface_absent_from_forward_dependency_manifest": True,
            "both_arm_64_prediction_freezes_before_evaluator_resources_open": True,
            "credential_value_persisted_hashed_or_emitted": False,
        },
        "authorization": {
            "single_fresh_shared_forward_paired_dev64": True,
            "additional_rollout_resume_or_rerun": False,
            "exact220_launch": False,
        },
        "dependency_manifest": dependencies,
        "dependency_manifest_sha256": payload_sha256(dependencies),
    }
    value["forward_contract_payload_sha256"] = payload_sha256(value)
    return value


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    contract = validate_forward_contract(root)
    if require_pristine and any((root / path).exists() or (root / path).is_symlink() for path in FUTURE_PATHS):
        raise RuntimeError("V2.43.46 protocol future surface is not pristine")
    controls = _manifest(root, CONTROL_FILES, reject_opaque_literals=False)
    value = {
        "artifact_version": 1,
        "role": "v24346_semantic_active_paired_dev64_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "dependency_manifest_sha256": contract["dependency_manifest_sha256"],
        "control_manifest": controls,
        "control_manifest_sha256": payload_sha256(controls),
        "task_contract": {
            "selected_per_arm": SELECTED_COUNT,
            "same_opaque_id_vector_both_arms": True,
            "runtime_boundary": ["opaque_id", "question"],
            "shared_single_forward_per_pair": True,
            "fresh_output_root": str(OUTPUT_ROOT),
            "failure_as_zero": True,
            "no_resume_skip_selective_retry_or_revaluation": True,
        },
        "causal_treatment": {
            "baseline": "raw_shared_7_plus_3_evidence_synthesis",
            "candidate": "same_baseline_plus_programmatic_semantic_projection_multihost_support_and_entropy_gate",
            "same_raw_pages": True,
            "same_plan_search_fetch_and_baseline_synthesis": True,
            "candidate_extra_model_call_only_when_eligible_support_exists": True,
            "pure_reserve_effect_ablation": False,
            "algorithmic_credit_assignment_ablation": True,
        },
        "evaluator_pairing_policy": {
            "baseline_predictions_evaluated_exactly_once": True,
            "candidate_exact_prediction_hash_identity_reuses_baseline_evaluator_row": True,
            "candidate_changed_predictions_evaluated_exactly_once": True,
            "routing_keys": ["instance_id", "prediction_sha256"],
            "routing_uses_mapping_gold_category_question_type_split_score_or_reward": False,
            "fixed_denominator_per_arm": SELECTED_COUNT,
            "evaluator_workers_per_changed_arm_maximum": EVALUATOR_WORKERS_PER_ARM,
            "total_evaluator_workers_maximum": TOTAL_EVALUATOR_WORKERS,
        },
        "decision_contract": dict(DECISION_CONTRACT),
        "evaluator_contract": _evaluator_contract(root),
        "lease_contract": {
            "path": str(LEASE_PATH),
            "forward_owner": LEASE_OWNER,
            "forward_purpose": LEASE_PURPOSE,
            "evaluator_owner": EVALUATOR_LEASE_OWNER,
            "evaluator_purpose": EVALUATOR_LEASE_PURPOSE,
            "single_owner_nonblocking": True,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "both_arm_prediction_freezes_before_mapping_or_evaluator_open": True,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        },
        "authorization": {
            "single_fresh_paired_dev64_forward_and_postfreeze_full_both_arm_evaluation": True,
            "additional_dev64_rollout_resume_skip_selective_retry": False,
            "exact220_launch": False,
            "avg_at_4": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    validate_protocol(root, value=value)
    return value


def validate_protocol(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    protocol = dict(value) if value is not None else _read(root, PROTOCOL)
    contract = validate_forward_contract(root)
    if (
        protocol.get("role") != "v24346_semantic_active_paired_dev64_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or protocol.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or protocol.get("dependency_manifest_sha256") != contract["dependency_manifest_sha256"]
        or protocol.get("decision_contract") != DECISION_CONTRACT
        or protocol.get("evaluator_pairing_policy")
        != {
            "baseline_predictions_evaluated_exactly_once": True,
            "candidate_exact_prediction_hash_identity_reuses_baseline_evaluator_row": True,
            "candidate_changed_predictions_evaluated_exactly_once": True,
            "routing_keys": ["instance_id", "prediction_sha256"],
            "routing_uses_mapping_gold_category_question_type_split_score_or_reward": False,
            "fixed_denominator_per_arm": SELECTED_COUNT,
            "evaluator_workers_per_changed_arm_maximum": EVALUATOR_WORKERS_PER_ARM,
            "total_evaluator_workers_maximum": TOTAL_EVALUATOR_WORKERS,
        }
        or protocol.get("control_manifest") != _manifest(root, CONTROL_FILES, reject_opaque_literals=False)
        or protocol.get("control_manifest_sha256") != payload_sha256(protocol["control_manifest"])
        or protocol.get("evaluator_contract") != _evaluator_contract(root)
        or protocol.get("source_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward"
        )
        is not False
        or protocol.get("authorization", {}).get("exact220_launch") is not False
        or not _sealed(protocol, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.43.46 protocol drifted")
    return protocol


def build_preaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    contract = validate_forward_contract(root)
    protocol = validate_protocol(root)
    suites = _run_tests()
    fields = _field_accesses(root)
    imports = _import_hits(root)
    lease = lease_observation(root, Path("/proc"))
    head = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "rev-parse", "target/main")
    clean = _git(root, "status", "--porcelain") == ""
    pristine = all(not (root / path).exists() and not (root / path).is_symlink() for path in (PREAUDIT, ACTIVATION, EXECUTION_START, FORWARD_RESULT, FINAL_RESULT, POSTAUDIT, OUTPUT_ROOT))
    findings: list[str] = []
    if any(not suite["passed"] for suite in suites): findings.append("focused_tests_failed")
    if fields: findings.append("privileged_field_access_in_forward_surface")
    if imports: findings.append("evaluator_import_in_forward_surface")
    if not _port_listening(): findings.append("keyless_proxy_not_listening")
    if lease.get("active") is not False: findings.append("shared_api_lease_active")
    if head != remote: findings.append("protocol_commit_not_pushed")
    if not clean: findings.append("worktree_not_clean")
    if not pristine: findings.append("future_surface_not_pristine")
    if protected_watcher_snapshot() != contract["execution"]["protected_watchers"]: findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24346_semantic_active_paired_dev64_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "protocol_sha256": sha256(root / PROTOCOL),
        "dependency_manifest_sha256": contract["dependency_manifest_sha256"],
        "control_manifest_sha256": protocol["control_manifest_sha256"],
        "focused_tests": suites,
        "privileged_field_accesses": fields,
        "evaluator_import_hits": imports,
        "protected_watchers": protected_watcher_snapshot(),
        "checks": {
            "focused_tests_passed": all(suite["passed"] for suite in suites),
            "forward_label_blind_ast": not fields and not imports,
            "keyless_proxy_listening_without_api_request": _port_listening(),
            "shared_api_lease_inactive": lease.get("active") is False,
            "head_equals_target_main": head == remote,
            "worktree_clean": clean,
            "future_surface_pristine": pristine,
            "mapping_gold_evaluator_or_score_opened_or_hashed": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "launch_authorized": not findings,
        "authorization": {
            "one_fresh_paired_dev64_forward": not findings,
            "evaluator_execution": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.43.46 preaudit failed: " + ",".join(findings))
    return value


def validate_preaudit(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(root, PREAUDIT)
    if (
        value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("launch_authorized") is not True
        or value.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or value.get("protocol_sha256") != sha256(root / PROTOCOL)
        or value.get("protected_watchers") != protected_watcher_snapshot()
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.46 preaudit drifted")
    validate_protocol(root)
    return value


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    contract = validate_forward_contract(root)
    audit = validate_preaudit(root)
    findings: list[str] = []
    if any((root / path).exists() or (root / path).is_symlink() for path in (ACTIVATION, EXECUTION_START, FORWARD_RESULT, FINAL_RESULT, POSTAUDIT, OUTPUT_ROOT)): findings.append("activation_or_execution_surface_not_pristine")
    if lease_observation(root, Path("/proc")).get("active") is not False: findings.append("shared_api_lease_active")
    if not _port_listening(): findings.append("keyless_proxy_not_listening")
    value = {
        "artifact_version": 1,
        "role": "v24346_semantic_active_paired_dev64_activation",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "active" if not findings else "rejected",
        "findings": findings,
        "launch_authorized": not findings,
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "selected_pair_tasks": SELECTED_COUNT,
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "model_slot_cap": MODEL_SLOT_CAP,
        "protected_watchers": audit["protected_watchers"],
        "network_model_search_fetch_evaluator_or_api_called": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "authorization": {"one_forward_launch": not findings, "evaluator": False, "exact220": False},
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    if findings: raise RuntimeError("V2.43.46 activation failed")
    return value


def validate_activation(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(root, ACTIVATION)
    if (
        value.get("status") != "active"
        or value.get("findings") != []
        or value.get("launch_authorized") is not True
        or value.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or value.get("preactivation_audit_sha256") != sha256(root / PREAUDIT)
        or value.get("protected_watchers") != protected_watcher_snapshot()
        or not _sealed(value, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.43.46 activation drifted")
    validate_preaudit(root)
    return value


def build_execution_start(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    validate_protocol(root)
    activation = validate_activation(root)
    if any((root / path).exists() or (root / path).is_symlink() for path in (EXECUTION_START, FORWARD_RESULT, FINAL_RESULT, POSTAUDIT, OUTPUT_ROOT)):
        raise RuntimeError("V2.43.46 execution surface is not pristine")
    head = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "rev-parse", "target/main")
    clean = _git(root, "status", "--porcelain") == ""
    findings: list[str] = []
    if head != remote: findings.append("activation_commit_not_pushed")
    if not clean: findings.append("worktree_not_clean")
    if lease_observation(root, Path("/proc")).get("active") is not False: findings.append("shared_api_lease_active")
    if not _port_listening(): findings.append("keyless_proxy_not_listening")
    value = {
        "artifact_version": 1,
        "role": "v24346_semantic_active_paired_dev64_execution_start",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "ready" if not findings else "rejected",
        "findings": findings,
        "execution_authorized": not findings,
        "activation_base_commit": head,
        "target_main_at_start": remote,
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "activation_sha256": sha256(root / ACTIVATION),
        "selected_pair_tasks": SELECTED_COUNT,
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "model_slot_cap": MODEL_SLOT_CAP,
        "protected_watchers": activation["protected_watchers"],
        "api_called_before_execution_start": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "evaluator_authorized": False,
    }
    value["execution_start_payload_sha256"] = payload_sha256(value)
    if findings: raise RuntimeError("V2.43.46 execution start failed: " + ",".join(findings))
    return value


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink(): raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("contract", "protocol", "preaudit", "activation", "start"))
    args = parser.parse_args()
    if args.command == "contract": publish(ROOT / FORWARD_CONTRACT, build_forward_contract())
    elif args.command == "protocol": publish(ROOT / PROTOCOL, build_protocol())
    elif args.command == "preaudit": publish(ROOT / PREAUDIT, build_preaudit())
    elif args.command == "activation": publish(ROOT / ACTIVATION, build_activation())
    elif args.command == "start": publish(ROOT / EXECUTION_START, build_execution_start())


if __name__ == "__main__":
    main()
