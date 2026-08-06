#!/usr/bin/env python3
"""Preregister, audit, activate, and authorize the V2.46.42 gate."""

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
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24642_ror_external_contract import (  # noqa: E402
    ACTIVATION,
    ARM_COUNT,
    DATE,
    EXECUTION_START,
    EXECUTOR_CONCURRENCY,
    FORWARD_AUDIT,
    FORWARD_RESULT,
    LEASE_OWNER,
    LEASE_PATH,
    LEASE_PURPOSE,
    LIMITS,
    MODEL,
    MODEL_SLOT_CAP,
    OUTPUT_ROOT,
    PARENT_TIMEOUT_SECONDS,
    PREAUDIT,
    PROTOCOL,
    PROTOCOL_ID,
    SEARCH,
    SELECTED_COUNT,
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
    task_vector,
)
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


SELECTION_AUDIT = Path(f"results/v24642_ror_selection_build_audit_v1_{DATE}.json")
PARENT_DIAGNOSIS = Path(
    f"results/v24641_v24640_zero_trigger_diagnosis_v1_{DATE}.json"
)
EVALUATOR_PROTOCOL = Path(
    f"results/v24642_deterministic_pair_evaluator_preregistration_v1_{DATE}.json"
)
RESULT = Path(f"results/v24642_deterministic_pair_result_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v24642_deterministic_pair_postresult_audit_v1_{DATE}.json"
)
DEPENDENCIES = (
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/native_search.py",
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24259_deterministic_table_normalizer.py",
    "src/deepwide_agent/v24263_global_model_limiter.py",
    "src/deepwide_agent/v24269_task_union_discovery.py",
    "src/deepwide_agent/v24272_two_wave_entropy_voc.py",
    "src/deepwide_agent/v24286_visible_schema_runtime.py",
    "src/deepwide_agent/v24287_hard_deadline_fetch.py",
    "src/deepwide_agent/v24308_child_exit_observability.py",
    "src/deepwide_agent/v24309_runner_exit_integration.py",
    "src/deepwide_agent/v24312_deadline_reliability.py",
    "src/deepwide_agent/v24316_deadline_search.py",
    "src/deepwide_agent/v24325_shared_prefix_revision_runtime.py",
    "src/deepwide_agent/v24468_total_wall_transport.py",
    "src/deepwide_agent/v24630_thin_backfill_search.py",
    "src/deepwide_agent/v24637_objective_alignment_runtime.py",
    "src/deepwide_agent/v24639_ror_objective_runtime.py",
    "src/deepwide_agent/v24640_evidence_constrained_runtime.py",
    "src/deepwide_agent/v24642_deterministic_pair_runtime.py",
    "src/deepwide_agent/v24642_ror_external_contract.py",
    "scripts/deepwide_api_lease.py",
    "scripts/audit_v24195_lease_owner_compatibility.py",
    "scripts/run_v24287_fetch_helper.py",
    "scripts/v24468_total_wall_http_helper.py",
    "scripts/run_v24642_ror_task.py",
    "scripts/run_v24642_deterministic_pair.py",
    "scripts/control_v24642_deterministic_pair.py",
    "scripts/audit_v24642_deterministic_pair_forward.py",
    "tests/test_v24642_deterministic_pair_runtime.py",
    str(SELECTION_AUDIT),
    str(PARENT_DIAGNOSIS),
)
FORWARD_FILES = (
    "src/deepwide_agent/v24642_deterministic_pair_runtime.py",
    "src/deepwide_agent/v24642_ror_external_contract.py",
    "scripts/run_v24642_ror_task.py",
    "scripts/run_v24642_deterministic_pair.py",
    "scripts/audit_v24642_deterministic_pair_forward.py",
)
SECRET_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9])(?:gh" + "p_|github_" + "pat_)[A-Za-z0-9_-]{16,}"),
    re.compile(r"(?<![A-Za-z0-9])tvly-" + "dev-[A-Za-z0-9_-]{16,}"),
    re.compile(r"(?<![A-Za-z0-9])s" + "k-[A-Za-z0-9_-]{16,}"),
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout.strip()


def read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.42 control expected object")
    return value


def sealed(value: dict, field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def publish(path: Path, value: dict) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def clean_remote() -> None:
    if git("status", "--porcelain") or git("rev-parse", "HEAD") != git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.46.42 control requires clean HEAD == target/main")


def validated_selection() -> dict:
    value = read(ROOT / SELECTION_AUDIT)
    if (
        not sealed(value, "audit_sha256")
        or value.get("role") != "v24642_ror_selection_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("historical_entity_count") != 4_384
        or value.get("historical_canonical_count") != 4_384
        or value.get("candidate_count") != 541
        or value.get("candidate_country_count") != 46
        or value.get("country_cap3_capacity") != 73
        or value.get("selected_count") != 48
        or value.get("selected_country_count") != 32
        or value.get("selected_country_max") != 3
        or value.get("authorization", {}).get("external_launch") is not False
    ):
        raise RuntimeError("V2.46.42 selection audit drifted")
    return value


def validated_parent() -> dict:
    value = read(ROOT / PARENT_DIAGNOSIS)
    if (
        not sealed(value, "diagnosis_sha256")
        or value.get("role") != "v24641_v24640_zero_trigger_postfreeze_diagnosis"
        or value.get("diagnosis", {}).get(
            "dependent_revision_emitted_zero_raw_declarations"
        )
        is not True
        or value.get("authorization", {}).get("fresh_external_successor_design")
        is not True
        or value.get("authorization", {}).get("fresh_external_successor_launch")
        is not False
    ):
        raise RuntimeError("V2.46.42 parent diagnosis drifted")
    return value


def protocol() -> dict:
    clean_remote()
    future = (
        PROTOCOL,
        PREAUDIT,
        ACTIVATION,
        EXECUTION_START,
        FORWARD_RESULT,
        FORWARD_AUDIT,
        EVALUATOR_PROTOCOL,
        RESULT,
        POSTAUDIT,
        OUTPUT_ROOT,
    )
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.46.42 future surface not pristine")
    selection = validated_selection()
    validated_parent()
    manifest = {path: sha256(ROOT / path) for path in DEPENDENCIES}
    tasks = task_vector()
    identifiers = [task["opaque_id"] for task in tasks]
    questions = [task["question"] for task in tasks]
    value = {
        "artifact_version": 1,
        "role": "v24642_deterministic_pair_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "parent": {
            "diagnosis_path": str(PARENT_DIAGNOSIS),
            "diagnosis_sha256": sha256(ROOT / PARENT_DIAGNOSIS),
            "v24640_status": "evidence_constrained_external_no_go",
            "reason_for_successor": "provider_revision_zero_raw_declarations",
        },
        "selection": {
            "audit_path": str(SELECTION_AUDIT),
            "audit_sha256": sha256(ROOT / SELECTION_AUDIT),
            "historical_entity_count": selection["historical_entity_count"],
            "fresh_entity_count": selection["selected_count"],
            "fresh_country_count": selection["selected_country_count"],
            "selection_rule": selection["selection_rule"],
            "selected_visible_vector_sha256": selection[
                "selected_visible_vector_sha256"
            ],
        },
        "task_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_tasks": SELECTED_COUNT,
            "selected_arm_predictions": SELECTED_COUNT * ARM_COUNT,
            "selected_ids": identifiers,
            "selected_ids_sha256": payload_sha256(identifiers),
            "visible_question_vector_sha256": payload_sha256(questions),
            "immutable_ror_commit_gold_and_provenance_absent_from_forward_contract": True,
            "entities_per_task": 4,
        },
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "parent_timeout_seconds": PARENT_TIMEOUT_SECONDS,
            "output_root": str(OUTPUT_ROOT),
            "protected_watchers": protected_watcher_snapshot(),
        },
        "paired_design": {
            "shared_plan_search_fetch_evidence_prefix": True,
            "baseline_precedes_deterministic_pair_discovery": True,
            "candidate_provider_model_declaration_call": False,
            "exact_provider_model_calls_per_valid_task": 2,
            "v24640_provider_model_calls_per_valid_task": 3,
            "quality_cost_pareto_gate_not_equal_effect_causal_ablation": True,
            "exact_entity_and_locally_bound_explicit_ror_required": True,
            "multi_id_or_cross_page_conflict_fails_closed": True,
            "nonunknown_ror_and_country_cells_immutable": True,
            "entropy_shadow_only": True,
        },
        "limits": LIMITS,
        "model": MODEL,
        "search": SEARCH,
        "lease": {
            "path": str(LEASE_PATH),
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
        },
        "evaluator_separation": {
            "all_predictions_frozen_before_gold_or_evaluator_open": True,
            "forward_manifest_excludes_ror_evaluator_gold_and_provenance": True,
            "fixed_denominator_failure_as_zero": True,
            "go_rule": "strict_exact_table_gain_nonnegative_composite_and_nonnegative_item_f1",
            "unknown_count_diagnostic_only": True,
        },
        "source_policy": {
            "mapping_gold_ror_id_country_code_category_question_type_split_evaluator_score_or_reward_read_by_forward": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "deepwidebench_task_gold_or_error_pattern_used": False,
        },
        "authorization": {
            "preactivation_audit_design": True,
            "one_external_forward_launch": False,
            "evaluator": False,
            "dev64": False,
            "exact220": False,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
    }
    value["protocol_sha256"] = payload_sha256(value)
    return value


def audit() -> dict:
    clean_remote()
    value = read(ROOT / PROTOCOL)
    findings: list[str] = []
    if value.get("protocol_id") != PROTOCOL_ID or not sealed(value, "protocol_sha256"):
        findings.append("protocol_invalid")
    manifest = value.get("dependency_manifest", {})
    if not isinstance(manifest, dict) or any(
        sha256(ROOT / path) != digest for path, digest in manifest.items()
    ):
        findings.append("manifest_drifted")
    source = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in manifest)
    if any(pattern.search(source) for pattern in SECRET_PATTERNS):
        findings.append("credential_literal_present")
    for path in FORWARD_FILES:
        text = (ROOT / path).read_text(encoding="utf-8")
        tree = ast.parse(text)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        if (
            any("external_evaluator" in item for item in imports)
            or "evaluation/v24642" in text
            or "EVALUATOR_PROTOCOL" in text
            or "ROR_GOLD" in text
        ):
            findings.append(f"forward_evaluator_or_gold_capability:{path}")
    test = subprocess.run(
        [
            str(ROOT / ".venv-eval/bin/python"),
            "-I",
            "-B",
            str(ROOT / "tests/test_v24642_deterministic_pair_runtime.py"),
            "PairDiscoveryTests",
            "RuntimeTests",
            "-v",
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
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=120,
    ).returncode == 0
    if not test:
        findings.append("focused_tests_failed")
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=1):
            endpoint = True
    except OSError:
        endpoint = False
        findings.append("gpt56_endpoint_unreachable")
    lease = lease_observation(ROOT, Path("/proc"))
    watchers = protected_watcher_snapshot()
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if watchers != value.get("execution", {}).get("protected_watchers"):
        findings.append("watcher_drifted")
    try:
        selection = validated_selection()
        parent = validated_parent()
        if (
            value.get("selection", {}).get("audit_sha256")
            != sha256(ROOT / SELECTION_AUDIT)
            or value.get("parent", {}).get("diagnosis_sha256")
            != sha256(ROOT / PARENT_DIAGNOSIS)
        ):
            findings.append("selection_or_parent_binding_drifted")
    except RuntimeError:
        selection = parent = {}
        findings.append("selection_or_parent_invalid")
    result = {
        "artifact_version": 1,
        "role": "v24642_deterministic_pair_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "checks": {
            "focused_runtime_tests_passed": test,
            "preactivation_evaluator_tests_skipped": True,
            "evaluator_gold_not_opened_or_hashed_by_preactivation": True,
            "forward_evaluator_and_gold_capability_absent": not any(
                item.startswith("forward_evaluator") for item in findings
            ),
            "credential_literal_absent": "credential_literal_present" not in findings,
            "gpt56_endpoint_reachable_without_provider_request": endpoint,
            "shared_api_lease_inactive": lease.get("active") is False,
            "selection_audit_valid": selection.get("audit_valid") is True,
            "parent_diagnosis_valid": parent.get("role")
            == "v24641_v24640_zero_trigger_postfreeze_diagnosis",
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "protected_watchers": watchers,
        "findings": findings,
        "audit_valid": not findings,
        "launch_authorized": not findings,
        "protocol_file_sha256": sha256(ROOT / PROTOCOL),
        "authorization": {
            "one_external_forward_launch": not findings,
            "evaluator": False,
            "dev64": False,
            "exact220": False,
        },
    }
    result["audit_sha256"] = payload_sha256(result)
    if findings:
        raise RuntimeError("V2.46.42 preaudit failed: " + ",".join(findings))
    return result


def activate() -> dict:
    clean_remote()
    protocol_value = read(ROOT / PROTOCOL)
    audit_value = read(ROOT / PREAUDIT)
    findings = []
    if (
        not sealed(protocol_value, "protocol_sha256")
        or not sealed(audit_value, "audit_sha256")
        or audit_value.get("audit_valid") is not True
    ):
        findings.append("parent_invalid")
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (ACTIVATION, EXECUTION_START, FORWARD_RESULT, OUTPUT_ROOT)
    ):
        findings.append("future_not_pristine")
    if lease_observation(ROOT, Path("/proc")).get("active") is not False:
        findings.append("lease_active")
    watchers = protected_watcher_snapshot()
    if watchers != audit_value.get("protected_watchers"):
        findings.append("watcher_drifted")
    result = {
        "artifact_version": 1,
        "role": "v24642_deterministic_pair_activation",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "status": "active" if not findings else "rejected",
        "findings": findings,
        "launch_authorized": not findings,
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "preaudit_sha256": sha256(ROOT / PREAUDIT),
        "protected_watchers": watchers,
        "network_model_search_fetch_or_evaluator_called": False,
        "mapping_gold_ror_id_country_code_evaluator_score_or_reward_read": False,
        "authorization": {
            "one_external_forward_launch": not findings,
            "evaluator": False,
            "dev64": False,
            "exact220": False,
        },
    }
    result["activation_sha256"] = payload_sha256(result)
    if findings:
        raise RuntimeError("V2.46.42 activation rejected")
    return result


def start() -> dict:
    clean_remote()
    protocol_value, audit_value, activation_value = (
        read(ROOT / path) for path in (PROTOCOL, PREAUDIT, ACTIVATION)
    )
    findings = []
    if (
        not sealed(protocol_value, "protocol_sha256")
        or not sealed(audit_value, "audit_sha256")
        or not sealed(activation_value, "activation_sha256")
        or audit_value.get("launch_authorized") is not True
        or activation_value.get("launch_authorized") is not True
    ):
        findings.append("chain_invalid")
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (EXECUTION_START, FORWARD_RESULT, OUTPUT_ROOT)
    ):
        findings.append("future_not_pristine")
    if lease_observation(ROOT, Path("/proc")).get("active") is not False:
        findings.append("lease_active")
    watchers = protected_watcher_snapshot()
    if watchers != activation_value.get("protected_watchers"):
        findings.append("watcher_drifted")
    result = {
        "artifact_version": 1,
        "role": "v24642_deterministic_pair_execution_start",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "status": "authorized" if not findings else "rejected",
        "findings": findings,
        "launch_authorized": not findings,
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "preaudit_sha256": sha256(ROOT / PREAUDIT),
        "activation_sha256": sha256(ROOT / ACTIVATION),
        "protected_watchers": watchers,
        "first_network_model_search_or_fetch_effect_started": False,
        "mapping_gold_ror_id_country_code_evaluator_score_or_reward_read": False,
        "authorization": {
            "one_external_forward_launch": not findings,
            "evaluator": False,
            "dev64": False,
            "exact220": False,
        },
    }
    result["execution_start_sha256"] = payload_sha256(result)
    if findings:
        raise RuntimeError("V2.46.42 execution start rejected")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("protocol", "audit", "activate", "start"))
    args = parser.parse_args()
    builders = {
        "protocol": (protocol, PROTOCOL),
        "audit": (audit, PREAUDIT),
        "activate": (activate, ACTIVATION),
        "start": (start, EXECUTION_START),
    }
    function, path = builders[args.command]
    value = function()
    publish(ROOT / path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "audit_valid": value.get("audit_valid"),
                "launch_authorized": value.get("launch_authorized"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
