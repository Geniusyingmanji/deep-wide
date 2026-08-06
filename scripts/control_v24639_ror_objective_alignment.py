#!/usr/bin/env python3
"""Preregister, audit, activate, and authorize the V2.46.39 ROR gate."""

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
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path: sys.path.insert(0, str(path))

from deepwide_agent.v24639_ror_external_contract import (  # noqa: E402
    ACTIVATION, ARM_COUNT, EXECUTION_START, EXECUTOR_CONCURRENCY, FORWARD_RESULT,
    LEASE_OWNER, LEASE_PATH, LEASE_PURPOSE, LIMITS, MODEL, MODEL_SLOT_CAP,
    OUTPUT_ROOT, PARENT_TIMEOUT_SECONDS, PREAUDIT, PROTOCOL, PROTOCOL_ID,
    SEARCH, SELECTED_COUNT, payload_sha256, protected_watcher_snapshot, sha256,
    task_vector,
)
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402


DEPENDENCIES = (
    "src/deepwide_agent/clients.py", "src/deepwide_agent/native_search.py",
    "src/deepwide_agent/v24257_score_first_runtime.py", "src/deepwide_agent/v24259_deterministic_table_normalizer.py",
    "src/deepwide_agent/v24263_global_model_limiter.py", "src/deepwide_agent/v24269_task_union_discovery.py",
    "src/deepwide_agent/v24272_two_wave_entropy_voc.py", "src/deepwide_agent/v24286_visible_schema_runtime.py",
    "src/deepwide_agent/v24287_hard_deadline_fetch.py", "src/deepwide_agent/v24308_child_exit_observability.py",
    "src/deepwide_agent/v24309_runner_exit_integration.py", "src/deepwide_agent/v24312_deadline_reliability.py",
    "src/deepwide_agent/v24316_deadline_search.py", "src/deepwide_agent/v24325_shared_prefix_revision_runtime.py",
    "src/deepwide_agent/v24468_total_wall_transport.py", "src/deepwide_agent/v24630_thin_backfill_search.py",
    "src/deepwide_agent/v24637_objective_alignment_runtime.py", "src/deepwide_agent/v24639_ror_objective_runtime.py",
    "src/deepwide_agent/v24639_ror_external_contract.py", "scripts/deepwide_api_lease.py",
    "scripts/run_v24287_fetch_helper.py", "scripts/v24468_total_wall_http_helper.py",
    "scripts/run_v24639_ror_task.py", "scripts/run_v24639_ror_objective_alignment.py",
    "scripts/control_v24639_ror_objective_alignment.py", "scripts/audit_v24639_ror_forward.py",
)
FORWARD_FILES = (
    "src/deepwide_agent/v24639_ror_objective_runtime.py",
    "src/deepwide_agent/v24639_ror_external_contract.py",
    "scripts/run_v24639_ror_task.py", "scripts/run_v24639_ror_objective_alignment.py",
)
SECRET_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9])(?:gh" + "p_|github_" + "pat_)[A-Za-z0-9_-]{16,}"),
    re.compile(r"(?<![A-Za-z0-9])tvly-" + "dev-[A-Za-z0-9_-]{16,}"),
    re.compile(r"(?<![A-Za-z0-9])s" + "k-[A-Za-z0-9_-]{16,}"),
)


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout.strip()


def read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise RuntimeError("V2.46.39 control expected object")
    return value


def sealed(value: dict, field: str) -> bool:
    unsigned = dict(value); seal = unsigned.pop(field, None); return seal == payload_sha256(unsigned)


def publish(path: Path, value: dict) -> None:
    if path.exists() or path.is_symlink(): raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


def protocol() -> dict:
    if git("status", "--porcelain") or git("rev-parse", "HEAD") != git("rev-parse", "target/main"): raise RuntimeError("V2.46.39 protocol requires clean HEAD == target/main")
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (PROTOCOL, PREAUDIT, ACTIVATION, EXECUTION_START, FORWARD_RESULT, OUTPUT_ROOT)): raise RuntimeError("V2.46.39 future surface not pristine")
    manifest = {path: sha256(ROOT / path) for path in DEPENDENCIES}
    tasks = task_vector(); ids = [task["opaque_id"] for task in tasks]; questions = [task["question"] for task in tasks]
    value = {
        "artifact_version": 1, "role": "v24639_ror_objective_alignment_preregistration", "protocol_id": PROTOCOL_ID, "created_at_unix": int(time.time()),
        "parent": {"v24638_external_result_path": "results/v24638_objective_alignment_result_v1_20260806.json", "v24638_external_result_sha256": sha256(ROOT / "results/v24638_objective_alignment_result_v1_20260806.json"), "v24638_status": "external_objective_alignment_no_go", "reason_for_successor": "airport_ceiling"},
        "task_contract": {"runtime_input_keys": ["opaque_id", "question"], "selected_tasks": SELECTED_COUNT, "selected_arm_predictions": SELECTED_COUNT * ARM_COUNT, "selected_ids": ids, "selected_ids_sha256": payload_sha256(ids), "visible_question_vector_sha256": payload_sha256(questions), "fresh_entity_count": 48, "prior_4288_entity_canonical_overlap": 0, "immutable_ror_commit_and_gold_absent_from_forward_contract": True, "entities_per_task": 4},
        "difficulty_design": {"registry": "ROR", "selection_rule": "first_1000_active_unique_display_no_parenthetical_country_prior_entity_disjoint_sha256_rank_country_cap3_balanced_groups", "opaque_ror_id_not_model_memory_trivial": True, "one_entity_specific_query_per_visible_entity": True, "country_diversity": True, "non_ceiling_or_non_floor_not_assumed_before_run": True},
        "execution": {"executor_concurrency": EXECUTOR_CONCURRENCY, "model_slot_cap": MODEL_SLOT_CAP, "parent_timeout_seconds": PARENT_TIMEOUT_SECONDS, "output_root": str(OUTPUT_ROOT), "protected_watchers": protected_watcher_snapshot(), "balanced_arm_order_by_opaque_id_parity": True},
        "paired_design": {"shared_plan_search_fetch_evidence_prefix": True, "shared_deterministic_visible_row_projector": True, "projector_creates_fact_value": False, "candidate_changes_synthesis_objective_only": True, "candidate_additional_query_fetch_model_or_token_cap": False, "entropy_shadow_only": True},
        "limits": LIMITS, "model": MODEL, "search": SEARCH, "lease": {"path": str(LEASE_PATH), "owner": LEASE_OWNER, "purpose": LEASE_PURPOSE},
        "evaluator_separation": {"all_predictions_frozen_before_gold_or_evaluator_open": True, "forward_manifest_excludes_ror_evaluator_gold_and_provenance": True, "fixed_denominator_failure_as_zero": True, "go_rule": "strict_exact_table_gain_and_nonnegative_composite_delta"},
        "source_policy": {"mapping_gold_ror_id_country_code_category_question_type_split_evaluator_score_or_reward_read_by_forward": False, "credential_value_read_persisted_hashed_or_emitted": False, "deepwidebench_task_gold_or_error_pattern_used": False},
        "authorization": {"preactivation_audit_design": True, "one_external_forward_launch": False, "evaluator": False, "dev64": False, "exact220": False},
        "dependency_manifest": manifest, "dependency_manifest_sha256": payload_sha256(manifest),
    }
    value["protocol_sha256"] = payload_sha256(value); return value


def audit() -> dict:
    value = read(ROOT / PROTOCOL); findings = []
    if value.get("protocol_id") != PROTOCOL_ID or not sealed(value, "protocol_sha256"): findings.append("protocol_invalid")
    manifest = value.get("dependency_manifest", {})
    if not isinstance(manifest, dict) or any(sha256(ROOT / path) != digest for path, digest in manifest.items()): findings.append("manifest_drifted")
    source = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in manifest)
    if any(pattern.search(source) for pattern in SECRET_PATTERNS): findings.append("credential_literal_present")
    imports = []
    for path in FORWARD_FILES:
        text = (ROOT / path).read_text(encoding="utf-8"); tree = ast.parse(text)
        imports.extend((node.module or "") for node in ast.walk(tree) if isinstance(node, ast.ImportFrom))
        if "evaluation/v24639" in text or "ROR_GOLD" in text or "ror_external_evaluator" in text: findings.append("forward_gold_capability_present")
    if any("external_evaluator" in item for item in imports): findings.append("forward_evaluator_import_present")
    test = subprocess.run([str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(ROOT / "tests/test_v24639_ror_objective_alignment.py"), "-v"], cwd=ROOT, env={"HOME": str(Path.home()), "USER": os.environ.get("USER", "azureuser"), "LOGNAME": os.environ.get("LOGNAME", "azureuser"), "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1"}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120).returncode == 0
    if not test: findings.append("focused_tests_failed")
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=1): endpoint = True
    except OSError: endpoint = False; findings.append("gpt56_endpoint_unreachable")
    lease = lease_observation(ROOT, Path("/proc")); watchers = protected_watcher_snapshot()
    if lease.get("active") is not False: findings.append("shared_api_lease_active")
    if watchers != value.get("execution", {}).get("protected_watchers"): findings.append("watcher_drifted")
    result = {"artifact_version": 1, "role": "v24639_ror_objective_alignment_preactivation_audit", "protocol_id": PROTOCOL_ID, "created_at_unix": int(time.time()), "checks": {"focused_tests_passed": test, "forward_evaluator_and_gold_capability_absent": not any("gold_capability" in item or "evaluator_import" in item for item in findings), "credential_literal_absent": "credential_literal_present" not in findings, "gpt56_endpoint_reachable_without_provider_request": endpoint, "shared_api_lease_inactive": lease.get("active") is False, "network_model_search_fetch_or_evaluator_called_by_audit": False}, "protected_watchers": watchers, "findings": findings, "audit_valid": not findings, "launch_authorized": not findings, "protocol_file_sha256": sha256(ROOT / PROTOCOL), "authorization": {"one_external_forward_launch": not findings, "evaluator": False, "dev64": False, "exact220": False}}; result["audit_sha256"] = payload_sha256(result)
    if findings: raise RuntimeError("V2.46.39 preaudit failed: " + ",".join(findings))
    return result


def activate() -> dict:
    protocol_value, audit_value = read(ROOT / PROTOCOL), read(ROOT / PREAUDIT); findings = []
    if protocol_value.get("protocol_id") != PROTOCOL_ID or audit_value.get("audit_valid") is not True: findings.append("parent_invalid")
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (ACTIVATION, EXECUTION_START, FORWARD_RESULT, OUTPUT_ROOT)): findings.append("future_not_pristine")
    if lease_observation(ROOT, Path("/proc")).get("active") is not False: findings.append("lease_active")
    watchers = protected_watcher_snapshot()
    if watchers != audit_value.get("protected_watchers"): findings.append("watcher_drifted")
    result = {"artifact_version": 1, "role": "v24639_ror_objective_alignment_activation", "protocol_id": PROTOCOL_ID, "created_at_unix": int(time.time()), "status": "active" if not findings else "rejected", "findings": findings, "launch_authorized": not findings, "protocol_sha256": sha256(ROOT / PROTOCOL), "preaudit_sha256": sha256(ROOT / PREAUDIT), "protected_watchers": watchers, "network_model_search_fetch_or_evaluator_called": False, "mapping_gold_ror_id_country_code_evaluator_score_or_reward_read": False, "authorization": {"one_external_forward_launch": not findings, "evaluator": False, "dev64": False, "exact220": False}}; result["activation_sha256"] = payload_sha256(result)
    if findings: raise RuntimeError("V2.46.39 activation rejected")
    return result


def start() -> dict:
    protocol_value, audit_value, activation_value = (read(ROOT / path) for path in (PROTOCOL, PREAUDIT, ACTIVATION)); findings = []
    if protocol_value.get("protocol_id") != PROTOCOL_ID or audit_value.get("launch_authorized") is not True or activation_value.get("launch_authorized") is not True: findings.append("chain_invalid")
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (EXECUTION_START, FORWARD_RESULT, OUTPUT_ROOT)): findings.append("future_not_pristine")
    if lease_observation(ROOT, Path("/proc")).get("active") is not False: findings.append("lease_active")
    watchers = protected_watcher_snapshot()
    if watchers != activation_value.get("protected_watchers"): findings.append("watcher_drifted")
    result = {"artifact_version": 1, "role": "v24639_ror_objective_alignment_execution_start", "protocol_id": PROTOCOL_ID, "created_at_unix": int(time.time()), "status": "authorized" if not findings else "rejected", "findings": findings, "launch_authorized": not findings, "protocol_sha256": sha256(ROOT / PROTOCOL), "preaudit_sha256": sha256(ROOT / PREAUDIT), "activation_sha256": sha256(ROOT / ACTIVATION), "protected_watchers": watchers, "first_network_model_search_or_fetch_effect_started": False, "mapping_gold_ror_id_country_code_evaluator_score_or_reward_read": False, "authorization": {"one_external_forward_launch": not findings, "evaluator": False, "dev64": False, "exact220": False}}; result["execution_start_sha256"] = payload_sha256(result)
    if findings: raise RuntimeError("V2.46.39 execution start rejected")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("command", choices=("protocol", "audit", "activate", "start")); args = parser.parse_args()
    builders = {"protocol": (protocol, PROTOCOL), "audit": (audit, PREAUDIT), "activate": (activate, ACTIVATION), "start": (start, EXECUTION_START)}
    function, path = builders[args.command]; value = function(); publish(ROOT / path, value); print(json.dumps({"path": str(path), "audit_valid": value.get("audit_valid"), "launch_authorized": value.get("launch_authorized")}, sort_keys=True))


if __name__ == "__main__": main()
