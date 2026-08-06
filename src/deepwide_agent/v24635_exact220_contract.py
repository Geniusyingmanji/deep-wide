"""Frozen visible-only contract for the V2.46.35 DeepWideBench exact-220."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROLE = "v24635_exact220_forward_contract"
PROTOCOL_ID = "v24635_capacity_validated_bounded_title_backfill_exact220_v1"
FORWARD_CONTRACT = Path("results/v24635_exact220_forward_contract_v1_20260806.json")
PREAUDIT = Path("results/v24635_exact220_preactivation_audit_v1_20260806.json")
ACTIVATION = Path("results/v24635_exact220_activation_v1_20260806.json")
EXECUTION_START = Path("results/v24635_exact220_execution_start_v1_20260806.json")
FORWARD_RESULT = Path("results/v24635_exact220_forward_result_v1_20260806.json")
OUTPUT_ROOT = Path("outputs/v24635_exact220_v1_20260806")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24635_exact220_forward_v1"
LEASE_PURPOSE = "label_blind_capacity_validated_title_backfill_exact220"

CAPACITY_DECISION = Path(
    "results/v24633_neutral_capacity_stress_decision_v1_20260806.json"
)
CAPACITY_AUDIT = Path(
    "results/v24633_neutral_capacity_stress_postresult_audit_v1_20260806.json"
)
CAPACITY_RESULT = Path(
    "results/v24633_neutral_capacity_stress_result_v1_20260806.json"
)
PREDECESSOR_FORWARD_CONTRACT = Path(
    "results/v24634_exact220_forward_contract_v1_20260806.json"
)
PREDECESSOR_PREAUDIT = Path(
    "results/v24634_exact220_preactivation_audit_v1_20260806.json"
)
SELECTED_CAPACITY_ARM = "selected_20_active_8_slots_240s_fifo"

RUNNER_MARKER = "scripts/run_v24635_exact220.py"
CHILD_MARKER = "scripts/run_v24635_exact220_task.py"
CHILD_TERMINAL_NAME = "child_terminal_receipt.json"
PARENT_EXIT_NAME = "parent_exit_receipt.json"
RECEIPT_NAME = "model_slot_receipt.json"
TRANSPORT_NAME = "transport_health.json"
SOURCE_MANIFEST = Path("outputs/runtime_manifest_v1_repro/manifest.jsonl")
ID_SOURCES = (
    ("test_s01", Path("configs/full220_v2403_r1_test_s01.ids"), 52),
    ("test_s02", Path("configs/full220_v2403_r1_test_s02.ids"), 52),
    ("test_s03", Path("configs/full220_v2403_r1_test_s03.ids"), 52),
    ("devval", Path("configs/full220_v2403_r1_devval_s04.ids"), 64),
)

SELECTED_COUNT = 220
ARM = "baseline"
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 8
MODEL_SLOT_POOL_ID = "v24263_score_first_global_model_slots_v1"
CLEANUP_RESERVE_SECONDS = 5.0
MINIMUM_MODEL_ATTEMPT_SECONDS = 0.05
PARENT_DEADLINE_GRACE_SECONDS = 15.0
PROTECTED_WATCHERS = (
    (795336, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, "scripts/watch_v24218_exact220_executor.py"),
)
LIMITS = {
    "wall_seconds": 240,
    "model_calls": 3,
    "search_queries": 4,
    "fetch_targets": 10,
    "search_results_per_query": 3,
    "evidence_chars": 60_000,
    "page_chars": 5_000,
    "plan_output_tokens": 4_000,
    "synthesis_output_tokens": 30_000,
    "repair_output_tokens": 12_000,
}
TWO_WAVE_POLICY = {
    "wave1_queries": 2,
    "wave1_fetches": 6,
    "wave2_queries": 2,
    "wave2_fetches": 4,
    "minimum_usable_pages": 3,
    "minimum_novel_pages": 3,
    "minimum_unique_hosts": 2,
    "content_chars_per_column": 1_200,
    "maximum_wave1_seconds": 30.0,
    "latency_loss_per_second": 0.005,
    "information_gain_weight": 0.25,
    "minimum_net_value": 0.0,
    "beta_prior_alpha": 1.0,
    "beta_prior_beta": 1.0,
}
MODEL = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "name": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 65,
    "max_retries": 2,
}
SEARCH = {
    "provider": "azure-native-keyless-bounded-same-response-title-backfill",
    "proxy_url": "http://127.0.0.1:9878/responses",
    "model": "gpt-5.6-sol",
    "batch_size": 8,
    "workers": 1,
    "context_size": "medium",
    "max_output_tokens": 7_000,
    "timeout_seconds": 65,
    "max_retries": 2,
    "fetch_workers": 8,
    "fetch_timeout_seconds": 20,
    "hard_fetch_deadline_seconds": 25,
    "server_auto_fetch_enabled": False,
}
SINGLE_CHANGE_CONTRACT = {
    "parent_forward_implementation": "v24630",
    "executor_concurrency_from_to": [32, EXECUTOR_CONCURRENCY],
    "task_wall_seconds_from_to": [150, LIMITS["wall_seconds"]],
    "model_slot_cap_unchanged": MODEL_SLOT_CAP == 8,
    "model_search_retrieval_budget_and_runtime_unchanged": True,
    "runtime_input_boundary_unchanged": True,
}
CROSS_VERSION_POPULATION_POLICY = {
    "fixed_public_exact220_task_set_reexecuted": True,
    "new_or_disjoint_task_population_claimed": False,
    "v24630_task_outputs_predictions_evaluator_rows_scores_or_rewards_read_by_forward": False,
    "v24630_output_directory_reused_resumed_or_modified": False,
    "same_v24635_protocol_retry_resume_skip_or_selective_rerun": False,
    "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
}
AUDIT_SUCCESSOR_POLICY = {
    "predecessor_version": "v24634",
    "predecessor_protocol_id": "v24634_capacity_validated_bounded_title_backfill_exact220_v1",
    "predecessor_status": "immutable_preactivation_no_go",
    "predecessor_audit_valid": False,
    "predecessor_launch_authorized": False,
    "predecessor_findings": ["forward_evaluator_capability_present"],
    "predecessor_activation_execution_or_forward_reused": False,
    "correction_scope": "semantic_ast_evaluator_capability_detection_only",
    "inert_conflict_process_marker_literal_is_not_evaluator_capability": True,
    "true_evaluator_import_dynamic_import_process_launch_call_or_resource_access_remains_forbidden": True,
    "forward_algorithm_model_search_retrieval_budgets_slots_schedule_and_task_ids_unchanged_from_v24634": True,
}
OPAQUE = re.compile(r"task_[0-9a-f]{24}")


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.46.35 expected ordinary JSON object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.35 expected JSON object")
    return value


def protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for pid, marker in PROTECTED_WATCHERS:
        stat = proc_root / str(pid) / "stat"
        cmdline = proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.46.35 protected watcher is absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\x00", b" ").decode(errors="replace")
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.46.35 protected watcher identity drifted")
        output.append({"pid": pid, "marker": marker, "start_ticks": int(suffix[19])})
    return output


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def validate_capacity_parent(root: Path) -> dict[str, Any]:
    result = read_object(root / CAPACITY_RESULT)
    decision = read_object(root / CAPACITY_DECISION)
    audit = read_object(root / CAPACITY_AUDIT)
    observed = decision.get("observed", {}).get(SELECTED_CAPACITY_ARM, {})
    control = decision.get("observed", {}).get(
        "control_32_active_8_slots_150s_fifo", {}
    )
    if (
        result.get("role") != "v24633_neutral_capacity_stress_result"
        or result.get("mechanism_gate_passed") is not True
        or SELECTED_CAPACITY_ARM not in result.get("passing_candidate_arms", [])
        or result.get("source_policy", {}).get(
            "benchmark_manifest_task_question_prediction_mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or result.get("authorization", {}).get(
            "benchmark_dev_or_exact220_launch"
        )
        is not False
        or not _sealed(result, "result_payload_sha256")
        or decision.get("result_sha256") != sha256(root / CAPACITY_RESULT)
        or decision.get("role") != "v24633_neutral_capacity_stress_decision"
        or decision.get("status") != "mechanism_go"
        or decision.get("passed") is not True
        or decision.get("selected_arm") != SELECTED_CAPACITY_ARM
        or observed.get("failed_jobs") != 0
        or observed.get("slot_timeouts") != 0
        or observed.get("provider_failures") != 0
        or observed.get("mechanism_gate_passed") is not True
        or control.get("failed_jobs") != 20
        or control.get("mechanism_gate_passed") is not False
        or decision.get("authorization", {}).get(
            "next_label_blind_exact220_protocol_design"
        )
        is not True
        or decision.get("authorization", {}).get("exact220_launch") is not False
        or not _sealed(decision, "decision_payload_sha256")
        or audit.get("role")
        != "v24633_neutral_capacity_stress_postresult_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("decision", {}).get("sha256")
        != sha256(root / CAPACITY_DECISION)
        or audit.get("result", {}).get("sha256")
        != sha256(root / CAPACITY_RESULT)
        or audit.get("authorization", {}).get(
            "next_label_blind_exact220_protocol_design"
        )
        is not True
        or audit.get("authorization", {}).get("exact220_launch") is not False
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.35 capacity parent drifted")
    return {
        "selected_arm": SELECTED_CAPACITY_ARM,
        "result_sha256": sha256(root / CAPACITY_RESULT),
        "result_payload_sha256": result["result_payload_sha256"],
        "decision_sha256": sha256(root / CAPACITY_DECISION),
        "decision_payload_sha256": decision["decision_payload_sha256"],
        "audit_sha256": sha256(root / CAPACITY_AUDIT),
        "audit_payload_sha256": audit["audit_payload_sha256"],
        "control_failed_jobs": control["failed_jobs"],
        "selected_failed_jobs": observed["failed_jobs"],
        "selected_wall_seconds": observed["wall_seconds"],
    }


def source_selected_ids(root: Path) -> list[str]:
    values: list[str] = []
    for tag, relative, expected in ID_SOURCES:
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"V2.46.35 {tag} ID source is absent")
        current = [line.strip() for line in path.read_text().splitlines() if line.strip()]
        if (
            len(current) != expected
            or len(set(current)) != expected
            or any(OPAQUE.fullmatch(item) is None for item in current)
        ):
            raise RuntimeError(f"V2.46.35 {tag} opaque IDs drifted")
        values.extend(current)
    if len(values) != SELECTED_COUNT or len(set(values)) != SELECTED_COUNT:
        raise RuntimeError("V2.46.35 selected ID partition is not exact-220")
    return values


def selected_ids(contract: dict[str, Any]) -> list[str]:
    values = contract.get("task_contract", {}).get("selected_opaque_ids")
    if (
        not isinstance(values, list)
        or len(values) != SELECTED_COUNT
        or len(set(values)) != SELECTED_COUNT
        or any(not isinstance(item, str) or OPAQUE.fullmatch(item) is None for item in values)
        or payload_sha256(values)
        != contract.get("task_contract", {}).get("selected_opaque_ids_sha256")
    ):
        raise RuntimeError("V2.46.35 frozen ID vector drifted")
    return list(values)


def selected_tasks(root: Path, contract: dict[str, Any]) -> list[dict[str, str]]:
    path = root / SOURCE_MANIFEST
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.46.35 visible manifest is absent")
    rows: dict[str, dict[str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = json.loads(line)
        if (
            not isinstance(raw, dict)
            or set(raw) != {"opaque_id", "question"}
            or OPAQUE.fullmatch(str(raw.get("opaque_id", ""))) is None
            or not isinstance(raw.get("question"), str)
            or not raw["question"].strip()
            or raw["opaque_id"] in rows
        ):
            raise RuntimeError("V2.46.35 visible manifest schema drifted")
        rows[raw["opaque_id"]] = {
            "opaque_id": raw["opaque_id"],
            "question": raw["question"],
        }
    ids = selected_ids(contract)
    if any(item not in rows for item in ids):
        raise RuntimeError("V2.46.35 selected visible task is absent")
    tasks = [rows[item] for item in ids]
    if any(set(task) != {"opaque_id", "question"} for task in tasks):
        raise RuntimeError("V2.46.35 runtime boundary drifted")
    return tasks


def validate_forward_contract(root: Path, path: Path = FORWARD_CONTRACT) -> dict[str, Any]:
    value = read_object(root / path)
    capacity_parent = validate_capacity_parent(root)
    unsigned = dict(value)
    seal = unsigned.pop("forward_contract_payload_sha256", None)
    if (
        value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("label_blind") is not True
        or seal != payload_sha256(unsigned)
        or value.get("task_contract")
        != {
            "runtime_boundary": ["opaque_id", "question"],
            "selected_count": SELECTED_COUNT,
            "selected_opaque_ids": selected_ids(value),
            "selected_opaque_ids_sha256": payload_sha256(selected_ids(value)),
            "manifest_path": str(SOURCE_MANIFEST),
            "manifest_sha256": sha256(root / SOURCE_MANIFEST),
            "mapping_split_category_gold_score_used_for_selection": False,
        }
        or selected_ids(value) != source_selected_ids(root)
        or value.get("execution")
        != {
            "arm": ARM,
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "model_slot_pool_id": MODEL_SLOT_POOL_ID,
            "child_terminal_receipt_name": CHILD_TERMINAL_NAME,
            "parent_exit_receipt_name": PARENT_EXIT_NAME,
            "runner_marker": RUNNER_MARKER,
            "child_marker": CHILD_MARKER,
            "output_root": str(OUTPUT_ROOT),
            "protected_watchers": protected_watcher_snapshot(),
        }
        or value.get("deadline_contract")
        != {
            "cleanup_reserve_seconds": CLEANUP_RESERVE_SECONDS,
            "minimum_attempt_seconds": MINIMUM_MODEL_ATTEMPT_SECONDS,
            "parent_deadline_grace_seconds": PARENT_DEADLINE_GRACE_SECONDS,
            "model_and_search_share_absolute_deadline": True,
            "provider_requests_use_process_enforced_total_wall": True,
        }
        or value.get("limits") != LIMITS
        or value.get("two_wave_policy") != TWO_WAVE_POLICY
        or value.get("model") != MODEL
        or value.get("search") != SEARCH
        or value.get("capacity_parent") != capacity_parent
        or value.get("single_change_contract") != SINGLE_CHANGE_CONTRACT
        or value.get("cross_version_population_policy")
        != CROSS_VERSION_POPULATION_POLICY
        or value.get("audit_successor_policy") != AUDIT_SUCCESSOR_POLICY
        or value.get("predecessor_no_go_binding")
        != {
            "forward_contract_path": str(PREDECESSOR_FORWARD_CONTRACT),
            "forward_contract_sha256": sha256(root / PREDECESSOR_FORWARD_CONTRACT),
            "preactivation_audit_path": str(PREDECESSOR_PREAUDIT),
            "preactivation_audit_sha256": sha256(root / PREDECESSOR_PREAUDIT),
        }
        or value.get("lease")
        != {
            "path": str(LEASE_PATH),
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
            "nonblocking_single_owner": True,
        }
        or value.get("fixed_denominator_contract")
        != {
            "required_terminal_predictions": SELECTED_COUNT,
            "parent_timeout_or_failure_projects_fallback": True,
            "all_220_predictions_frozen_before_evaluator_resources_open": True,
            "child_success_or_receipt_completeness_not_required_for_postfreeze_evaluator": True,
            "no_selective_retry_resume_skip_or_revaluation": True,
        }
        or value.get("source_policy")
        != {
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "evaluator_surface_absent_from_forward_dependency_manifest": True,
            "credential_value_persisted_hashed_or_emitted": False,
        }
        or value.get("authorization")
        != {
            "preactivation_audit_design": True,
            "single_fresh_exact220_forward": False,
            "resume_retry_skip_or_rerun": False,
        }
        or value.get("claims")
        != {
            "benchmark_score_before_postfreeze_evaluation": False,
            "avg_at_4": False,
            "leaderboard_submission": False,
            "sota": False,
        }
    ):
        raise RuntimeError("V2.46.35 forward contract identity drifted")
    manifest = value.get("dependency_manifest")
    if not isinstance(manifest, dict) or value.get("dependency_manifest_sha256") != payload_sha256(manifest):
        raise RuntimeError("V2.46.35 dependency manifest drifted")
    for relative, digest in manifest.items():
        candidate = root / relative
        if candidate.is_symlink() or not candidate.is_file() or sha256(candidate) != digest:
            raise RuntimeError(f"V2.46.35 frozen dependency drifted: {relative}")
    if sha256(root / SOURCE_MANIFEST) != value["task_contract"]["manifest_sha256"]:
        raise RuntimeError("V2.46.35 visible manifest hash drifted")
    if len(selected_tasks(root, value)) != SELECTED_COUNT:
        raise RuntimeError("V2.46.35 task count drifted")
    return value


__all__ = [name for name in globals() if name.isupper()] + [
    "payload_sha256",
    "protected_watcher_snapshot",
    "read_object",
    "selected_ids",
    "selected_tasks",
    "sha256",
    "source_selected_ids",
    "validate_capacity_parent",
    "validate_forward_contract",
]
