"""Fresh label-blind V2.48.46 atomic-table-header 30k exact-220 contract."""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v24844_atomic_table_header_exact220_contract as parent
from .v24846_atomic_table_header_30k_profile import (
    BLOCK_CHARACTER_CAP,
    MAXIMUM_PAGE_CHARS,
    MAXIMUM_QUERY_TERMS,
    MAXIMUM_VISIBLE_GROUPS,
    PROFILE_ID as PROJECTOR_POLICY_ID,
    TOTAL_CHARACTER_CAP,
    validate_receipt,
)


DATE = "20260808"
ROLE = "v24848_atomic_table_header_30k_exact220_preregistration"
PROTOCOL_ID = "v24848_fresh_v24846_atomic_table_header_30k_exact220_v1"
PROTOCOL = Path(f"results/v24848_atomic_table_header_30k_exact220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24848_atomic_table_header_30k_exact220_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24848_atomic_table_header_30k_exact220_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24848_atomic_table_header_30k_exact220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24848_atomic_table_header_30k_exact220_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24848_atomic_table_header_30k_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
PROJECTION_RECEIPT_NAME = "projection_receipt.json"
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v24848_atomic_table_header_30k_exact220_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_v24846_atomic_table_header_30k_exact220"
RUNNER_MARKER = "scripts/run_v24848_atomic_table_header_30k_exact220.py"
CHILD_MARKER = "scripts/run_v24848_atomic_table_header_30k_exact220_task.py"

SELECTED_COUNT = parent.SELECTED_COUNT
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
LIMITS = copy.deepcopy(parent.LIMITS)
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = copy.deepcopy(parent.SEARCH)
TWO_WAVE_POLICY = copy.deepcopy(parent.TWO_WAVE_POLICY)
PROTECTED_WATCHERS = parent.PROTECTED_WATCHERS
PARENT_PROTOCOL = parent.PROTOCOL
PROJECTOR_POLICY = {
    "policy_id": PROJECTOR_POLICY_ID,
    "total_character_cap": TOTAL_CHARACTER_CAP,
    "maximum_page_chars": MAXIMUM_PAGE_CHARS,
    "block_character_cap": BLOCK_CHARACTER_CAP,
    "maximum_visible_groups": MAXIMUM_VISIBLE_GROUPS,
    "maximum_query_terms": MAXIMUM_QUERY_TERMS,
}
PROJECTOR_AUDIT = Path(
    "results/v24846_atomic_table_header_30k_profile_build_audit_v1_20260808.json"
)
EXTERNAL_GATE = Path(
    "results/v24847_projection_budget_external_result_v1_20260808.json"
)
EXTERNAL_GATE_AUDIT = Path(
    "results/v24847_projection_budget_external_postresult_audit_v1_20260808.json"
)
SOURCE = Path("src/deepwide_agent/v24848_atomic_table_header_30k_exact220_contract.py")
PROJECTOR_SOURCE = Path("src/deepwide_agent/v24846_atomic_table_header_30k_profile.py")
CONTROL = Path("scripts/control_v24848_atomic_table_header_30k_exact220.py")
RUNNER = Path(RUNNER_MARKER)
CHILD = Path(CHILD_MARKER)
FINALIZER = Path("scripts/finalize_v24848_atomic_table_header_30k_exact220.py")
TEST = Path("tests/test_v24848_atomic_table_header_30k_exact220.py")
LOCAL_SOURCES = (SOURCE, CONTROL, RUNNER, CHILD, FINALIZER, TEST)

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
_git = parent._git
_ordinary_tracked = parent._ordinary_tracked


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.48.48 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.48 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _validated_external_gate(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate the preregistered external GO and its post-result SHA chain."""

    result = _read(root / EXTERNAL_GATE)
    audit = _read(root / EXTERNAL_GATE_AUDIT)
    if (
        result.get("role") != "v24847_projection_budget_external_result"
        or result.get("protocol_id")
        != "v24847_target_cell_disjoint_projection_budget_shared_prefix_v1"
        or result.get("passed") is not True
        or result.get("status") != "projection_budget_external_go"
        or result.get("fixed_denominator_failure_as_zero") is not True
        or result.get("quality_evaluation_executed_once_after_prediction_freeze")
        is not True
        or result.get("claim_scope", {}).get("target_cell_disjoint") is not True
        or result.get("claim_scope", {}).get("deepwidebench_quality_measured")
        is not False
        or result.get("claim_scope", {}).get("sota_supported") is not False
        or result.get("authorization")
        != {
            "public_exact220_candidate_design": True,
            "public_exact220_launch": False,
            "sota_claim": False,
        }
        or not _sealed(result, "result_payload_sha256")
        or audit.get("role")
        != "v24847_projection_budget_external_postresult_audit"
        or audit.get("protocol_id") != result.get("protocol_id")
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("result_sha256") != sha256(root / EXTERNAL_GATE)
        or audit.get("protected_watchers") != protected_watcher_snapshot()
        or audit.get("authorization") != result.get("authorization")
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.48.48 external projection-budget gate drifted")
    return result, audit


def projection_receipt_summary(root: Path) -> dict[str, Any]:
    """Validate and aggregate all content-free same-forward receipts."""

    total_fields = {
        "projected_rendered_characters": "rendered_characters",
        "selected_table_continuation_block_count": "selected_table_continuations",
        "table_header_dependency_addition_count": "table_header_dependency_additions",
        "orphan_selected_table_continuation_block_count": "orphan_table_continuations",
        "retained_supported_visible_requirement_group_count": "retained_supported_visible_requirements",
        "missed_supported_visible_requirement_group_count": "missed_supported_visible_requirements",
    }
    totals = {target: 0 for target in total_fields.values()}
    payload_seals: list[str] = []
    valid = 0
    missing = 0
    for position in range(1, SELECTED_COUNT + 1):
        path = (
            root
            / TASK_ROOT
            / f"task_{position:04d}"
            / PROJECTION_RECEIPT_NAME
        )
        if path.is_symlink():
            raise RuntimeError("V2.48.48 projection receipt is a symlink")
        if not path.exists():
            missing += 1
            continue
        if not path.is_file():
            raise RuntimeError("V2.48.48 projection receipt is nonordinary")
        try:
            receipt = validate_receipt(_read(path))
        except (OSError, RuntimeError, TypeError, ValueError) as error:
            raise RuntimeError(
                f"V2.48.48 invalid projection receipt at task {position:04d}"
            ) from error
        valid += 1
        payload_seals.append(str(receipt["receipt_payload_sha256"]))
        for source, target in total_fields.items():
            totals[target] += int(receipt[source])
    if valid + missing != SELECTED_COUNT:
        raise RuntimeError("V2.48.48 projection receipt denominator drifted")
    value = {
        "expected_receipts": SELECTED_COUNT,
        "valid_receipts": valid,
        "missing_receipts": missing,
        **totals,
        "receipt_payload_seal_vector_sha256": payload_sha256(payload_seals),
        "contains_question_query_url_host_page_projection_content_or_hash": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }
    if value["orphan_table_continuations"] != 0:
        raise RuntimeError("V2.48.48 orphan table continuation entered receipts")
    return value


def protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    return parent.protected_watcher_snapshot(proc_root)


def parent_contract(root: Path) -> dict[str, Any]:
    value = _read(root / PARENT_PROTOCOL)
    unsigned = dict(value)
    seal = unsigned.pop("protocol_payload_sha256", None)
    if (
        value.get("role") != parent.ROLE
        or value.get("protocol_id") != parent.PROTOCOL_ID
        or seal != payload_sha256(unsigned)
        or value.get("git_head") is None
        or not isinstance(value.get("dependency_manifest"), dict)
        or value.get("dependency_manifest_sha256")
        != payload_sha256(value["dependency_manifest"])
        or value.get("task_contract", {}).get("selected_count") != SELECTED_COUNT
        or value.get("source_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward"
        )
        is not False
    ):
        raise RuntimeError("V2.48.48 frozen parent protocol drifted")
    return value


def _parent_tasks(root: Path) -> list[dict[str, str]]:
    """Load the frozen public vector without recursively revalidating its manifest."""

    base = parent.parent.parent.parent.parent.parent.parent
    frozen = base.read_object(root / base.FORWARD_CONTRACT)
    return base.selected_tasks(root, frozen)


def task_vector(
    root: Path, protocol: Mapping[str, Any] | None = None
) -> list[dict[str, str]]:
    tasks = _parent_tasks(root)
    if len(tasks) != SELECTED_COUNT or any(
        set(task) != {"opaque_id", "question"} for task in tasks
    ):
        raise RuntimeError("V2.48.48 visible exact-220 vector drifted")
    if protocol is not None:
        observed = {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": SELECTED_COUNT,
            "opaque_id_vector_sha256": payload_sha256(
                [task["opaque_id"] for task in tasks]
            ),
            "visible_question_vector_sha256": payload_sha256(
                [task["question"] for task in tasks]
            ),
        }
        if protocol.get("task_contract") != observed:
            raise RuntimeError("V2.48.48 visible task binding drifted")
    return tasks


def dependency_manifest(root: Path) -> dict[str, str]:
    base = parent_contract(root)
    relatives = {Path(name) for name in base["dependency_manifest"]}
    relatives.update((
        PARENT_PROTOCOL, PROJECTOR_AUDIT, PROJECTOR_SOURCE,
        EXTERNAL_GATE, EXTERNAL_GATE_AUDIT,
    ))
    relatives.update(LOCAL_SOURCES)
    return {
        str(relative): sha256(_ordinary_tracked(root, relative))
        for relative in sorted(relatives, key=str)
    }


def build_protocol(
    root: Path,
    *,
    now: int,
    require_clean: bool = True,
    require_pristine: bool = True,
) -> dict[str, Any]:
    if require_clean and (
        _git(root, "status", "--porcelain")
        or _git(root, "rev-parse", "HEAD") != _git(root, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.48.48 protocol requires clean pushed HEAD")
    future = (
        PROTOCOL,
        PREAUDIT,
        EXECUTION_START,
        FORWARD_RESULT,
        FORWARD_AUDIT,
        OUTPUT_ROOT,
    )
    if require_pristine and any(
        (root / path).exists() or (root / path).is_symlink() for path in future
    ):
        raise FileExistsError("V2.48.48 future surface exists")
    base = parent_contract(root)
    tasks = task_vector(root)
    manifest = dependency_manifest(root)
    projector_audit = _read(root / PROJECTOR_AUDIT)
    external_gate, external_audit = _validated_external_gate(root)
    if (
        projector_audit.get("role")
        != "v24846_atomic_table_header_30k_profile_build_audit"
        or projector_audit.get("audit_valid") is not True
        or projector_audit.get("findings") != []
        or projector_audit.get("checks", {}).get(
            "candidate_rendered_and_per_page_caps_hard"
        )
        is not True
        or projector_audit.get("source_policy", {}).get(
            "entropy_or_information_gain_assigns_credit"
        )
        is not False
    ):
        raise RuntimeError("V2.48.48 projector audit drifted")
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "git_head": _git(root, "rev-parse", "HEAD"),
        "parent_algorithm": {
            "path": str(PARENT_PROTOCOL),
            "sha256": sha256(root / PARENT_PROTOCOL),
            "protocol_id": base["protocol_id"],
            "dependency_manifest_sha256": base["dependency_manifest_sha256"],
            "prior_output_prediction_result_score_or_evaluator_read_or_reused": False,
        },
        "projector": {
            "source": str(PROJECTOR_SOURCE),
            "source_sha256": sha256(root / PROJECTOR_SOURCE),
            "build_audit": str(PROJECTOR_AUDIT),
            "build_audit_sha256": sha256(root / PROJECTOR_AUDIT),
            "policy": copy.deepcopy(PROJECTOR_POLICY),
            "visible_question_and_same_forward_fetched_page_text_only": True,
            "structure_and_record_boundaries_preserved": True,
            "atomic_table_header_closure_enforced": True,
            "stable_first_seen_page_and_block_order": True,
            "entropy_information_gain_shadow_only": True,
            "entropy_or_information_gain_assigns_credit": False,
            "content_free_projection_receipt_enabled": True,
            "external_shared_prefix_gate": str(EXTERNAL_GATE),
            "external_shared_prefix_gate_sha256": sha256(root / EXTERNAL_GATE),
            "external_shared_prefix_gate_result_payload_sha256": external_gate[
                "result_payload_sha256"
            ],
            "external_shared_prefix_gate_postresult_audit": str(
                EXTERNAL_GATE_AUDIT
            ),
            "external_shared_prefix_gate_postresult_audit_sha256": sha256(
                root / EXTERNAL_GATE_AUDIT
            ),
            "external_shared_prefix_gate_audit_payload_sha256": external_audit[
                "audit_payload_sha256"
            ],
        },
        "task_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": SELECTED_COUNT,
            "opaque_id_vector_sha256": payload_sha256(
                [task["opaque_id"] for task in tasks]
            ),
            "visible_question_vector_sha256": payload_sha256(
                [task["question"] for task in tasks]
            ),
        },
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "task_wall_seconds": LIMITS["wall_seconds"],
            "model_calls_per_task": LIMITS["model_calls"],
            "search_queries_per_task": LIMITS["search_queries"],
            "fetch_targets_per_task": LIMITS["fetch_targets"],
            "model": MODEL,
            "search": SEARCH,
            "two_wave_policy": TWO_WAVE_POLICY,
            "protected_watchers": protected_watcher_snapshot(),
            "output_root": str(OUTPUT_ROOT),
            "single_fresh_forward_no_retry_resume_or_selective_rerun": True,
        },
        "single_change": {
            "fresh_execution_surfaces_only": True,
            "task_vector_prompt_model_search_fetch_controller_budgets_and_concurrency_equal_v24844": True,
            "only_projection_total_cap_changes_from_16000_to_30000": True,
            "atomic_table_header_closure_logic_unchanged": True,
            "projection_receipt_is_content_free_observability_only": True,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "runtime_reads_only_opaque_id_and_question": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
            "prior_v24844_output_prediction_result_score_or_evaluator_opened_or_hashed": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "fixed_public_exact220_task_set_reexecuted": True,
            "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
        },
        "authorization": {
            "preactivation_audit_generation": True,
            "execution_start_generation": False,
            "single_fresh_exact220_forward": False,
            "evaluator_call": False,
            "retry_resume_skip_or_selective_rerun": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(root, value)


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("protocol_payload_sha256", None)
    base = parent_contract(root)
    tasks = task_vector(root)
    manifest = dependency_manifest(root)
    execution = copied.get("execution", {})
    projector = copied.get("projector", {})
    single_change = copied.get("single_change", {})
    external_gate, external_audit = _validated_external_gate(root)
    expected_tasks = {
        "runtime_input_keys": ["opaque_id", "question"],
        "selected_count": SELECTED_COUNT,
        "opaque_id_vector_sha256": payload_sha256([task["opaque_id"] for task in tasks]),
        "visible_question_vector_sha256": payload_sha256([task["question"] for task in tasks]),
    }
    if (
        copied.get("role") != ROLE
        or copied.get("protocol_id") != PROTOCOL_ID
        or seal != payload_sha256(unsigned)
        or copied.get("parent_algorithm")
        != {
            "path": str(PARENT_PROTOCOL),
            "sha256": sha256(root / PARENT_PROTOCOL),
            "protocol_id": base["protocol_id"],
            "dependency_manifest_sha256": base["dependency_manifest_sha256"],
            "prior_output_prediction_result_score_or_evaluator_read_or_reused": False,
        }
        or projector.get("source_sha256") != sha256(root / PROJECTOR_SOURCE)
        or projector.get("build_audit_sha256") != sha256(root / PROJECTOR_AUDIT)
        or projector.get("policy") != PROJECTOR_POLICY
        or projector.get("visible_question_and_same_forward_fetched_page_text_only")
        is not True
        or projector.get("structure_and_record_boundaries_preserved") is not True
        or projector.get("atomic_table_header_closure_enforced") is not True
        or projector.get("stable_first_seen_page_and_block_order") is not True
        or projector.get("entropy_information_gain_shadow_only") is not True
        or projector.get("entropy_or_information_gain_assigns_credit") is not False
        or projector.get("content_free_projection_receipt_enabled") is not True
        or projector.get("external_shared_prefix_gate") != str(EXTERNAL_GATE)
        or projector.get("external_shared_prefix_gate_sha256")
        != sha256(root / EXTERNAL_GATE)
        or projector.get("external_shared_prefix_gate_result_payload_sha256")
        != external_gate["result_payload_sha256"]
        or projector.get("external_shared_prefix_gate_postresult_audit")
        != str(EXTERNAL_GATE_AUDIT)
        or projector.get("external_shared_prefix_gate_postresult_audit_sha256")
        != sha256(root / EXTERNAL_GATE_AUDIT)
        or projector.get("external_shared_prefix_gate_audit_payload_sha256")
        != external_audit["audit_payload_sha256"]
        or copied.get("task_contract") != expected_tasks
        or copied.get("dependency_manifest") != manifest
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or execution.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or execution.get("model_slot_cap") != MODEL_SLOT_CAP
        or execution.get("task_wall_seconds") != LIMITS["wall_seconds"]
        or execution.get("model_calls_per_task") != LIMITS["model_calls"]
        or execution.get("search_queries_per_task") != LIMITS["search_queries"]
        or execution.get("fetch_targets_per_task") != LIMITS["fetch_targets"]
        or execution.get("model") != MODEL
        or execution.get("search") != SEARCH
        or execution.get("two_wave_policy") != TWO_WAVE_POLICY
        or execution.get("protected_watchers") != protected_watcher_snapshot()
        or execution.get("output_root") != str(OUTPUT_ROOT)
        or execution.get("single_fresh_forward_no_retry_resume_or_selective_rerun")
        is not True
        or single_change
        != {
            "fresh_execution_surfaces_only": True,
            "task_vector_prompt_model_search_fetch_controller_budgets_and_concurrency_equal_v24844": True,
            "only_projection_total_cap_changes_from_16000_to_30000": True,
            "atomic_table_header_closure_logic_unchanged": True,
            "projection_receipt_is_content_free_observability_only": True,
        }
        or copied.get("source_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward"
        )
        is not False
        or copied.get("source_policy", {}).get(
            "prior_v24844_output_prediction_result_score_or_evaluator_opened_or_hashed"
        )
        is not False
        or copied.get("authorization")
        != {
            "preactivation_audit_generation": True,
            "execution_start_generation": False,
            "single_fresh_exact220_forward": False,
            "evaluator_call": False,
            "retry_resume_skip_or_selective_rerun": False,
        }
    ):
        raise RuntimeError("V2.48.48 protocol drifted")
    task_vector(root, copied)
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol",
    "dependency_manifest",
    "parent_contract",
    "payload_sha256",
    "projection_receipt_summary",
    "protected_watcher_snapshot",
    "sha256",
    "task_vector",
    "validate_protocol",
]
