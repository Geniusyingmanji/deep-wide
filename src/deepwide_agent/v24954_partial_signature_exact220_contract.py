"""Label-blind exact-220 contract for mutually unique partial signatures."""

from __future__ import annotations

import copy
from pathlib import Path

from . import v24945_injective_schema_signature_ledger as legacy_projector
from . import v24948_schema_signature_exact220_contract as parent
from . import v24949_mutual_partial_signature_ledger as projector


DATE = "20260809"
ROLE = "v24954_partial_signature_exact220_preregistration"
PROTOCOL_ID = "v24954_keyless_mutual_partial_signature_exact220_v1"
PROTOCOL = Path(f"results/v24954_partial_signature_exact220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24954_partial_signature_exact220_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24954_partial_signature_exact220_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24954_partial_signature_exact220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24954_partial_signature_exact220_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24954_partial_signature_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
PROJECTION_RECEIPT_NAME = "partial_signature_projection_receipt.json"
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v24954_partial_signature_exact220_forward_v1"
LEASE_PURPOSE = "label_blind_mutual_partial_signature_exact220"
RUNNER_MARKER = "scripts/run_v24954_partial_signature_exact220.py"
CHILD_MARKER = "scripts/run_v24954_partial_signature_exact220_task.py"

SELECTED_COUNT = parent.SELECTED_COUNT
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
LIMITS = copy.deepcopy(parent.LIMITS)
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = copy.deepcopy(parent.SEARCH)
TWO_WAVE_POLICY = copy.deepcopy(parent.TWO_WAVE_POLICY)
PROTECTED_WATCHERS = parent.PROTECTED_WATCHERS
PARENT_PROTOCOL = parent.PROTOCOL
PROJECTOR_SOURCE = Path("src/deepwide_agent/v24949_mutual_partial_signature_ledger.py")
PROJECTOR_AUDIT = Path("results/v24950_mutual_partial_signature_build_audit_v2_20260809.json")
LEGACY_PROJECTOR_SOURCE = parent.PROJECTOR_SOURCE
TARGET_VALUE_SOURCE = parent.TARGET_VALUE_SOURCE
SOURCE = Path("src/deepwide_agent/v24954_partial_signature_exact220_contract.py")
BINDING = parent.BINDING
CONTROL = Path("scripts/control_v24954_partial_signature_exact220.py")
RUNNER = Path(RUNNER_MARKER)
CHILD = Path(CHILD_MARKER)
FINALIZER = Path("scripts/finalize_v24954_partial_signature_exact220.py")
TEST = Path("tests/test_v24954_partial_signature_exact220.py")
LOCAL_SOURCES = (SOURCE, CONTROL, RUNNER, CHILD, FINALIZER, TEST)

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
protected_watcher_snapshot = parent.protected_watcher_snapshot


def _read(path: Path):
    return parent._read(path)


def _sealed(value, field: str) -> bool:
    return parent._sealed(value, field)


def parent_contract(root: Path):
    return parent.validate_protocol(root, _read(root / PARENT_PROTOCOL))


def _task_contract(tasks):
    return {
        "runtime_input_keys": ["opaque_id", "question"],
        "selected_count": SELECTED_COUNT,
        "opaque_id_vector_sha256": payload_sha256([task["opaque_id"] for task in tasks]),
        "visible_question_vector_sha256": payload_sha256([task["question"] for task in tasks]),
    }


def task_vector(root: Path, protocol=None):
    tasks = parent.task_vector(root)
    if len(tasks) != 220 or any(set(task) != {"opaque_id", "question"} for task in tasks):
        raise RuntimeError("V2.49.54 visible task vector drifted")
    if protocol is not None and protocol.get("task_contract") != _task_contract(tasks):
        raise RuntimeError("V2.49.54 task binding drifted")
    return tasks


def _evidence(root: Path):
    build = _read(root / PROJECTOR_AUDIT)
    manifest = build.get("source_manifest", {})
    if (
        build.get("role") != "v24950_mutual_partial_signature_build_audit"
        or build.get("audit_valid") is not True
        or build.get("findings") != []
        or build.get("candidate_policy_id") != projector.POLICY_ID
        or manifest.get(str(PROJECTOR_SOURCE)) != sha256(root / PROJECTOR_SOURCE)
        or build.get("checks", {}).get("mutual_unique_injective_fail_closed") is not True
        or build.get("checks", {}).get("entropy_information_gain_shadow_only") is not True
        or build.get("checks", {}).get("runtime_privileged_field_access_zero") is not True
        or build.get("authorization", {}).get("public_exact220") is not False
        or not _sealed(build, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.49.54 candidate build evidence drifted")
    return {
        "mutual_partial_signature_build_audit_valid": True,
        "implementation_audit_is_not_quality_evidence": True,
        "external_quality_gate_not_claimed": True,
        "fixed_public_exact220_run_requested_for_measurement": True,
        "sota_or_improvement_not_assumed_before_evaluation": True,
    }


def dependency_manifest(root: Path):
    base = parent_contract(root)
    relatives = {Path(name) for name in base["dependency_manifest"]}
    relatives.update(
        (
            PARENT_PROTOCOL,
            PROJECTOR_SOURCE,
            PROJECTOR_AUDIT,
            LEGACY_PROJECTOR_SOURCE,
            TARGET_VALUE_SOURCE,
            *LOCAL_SOURCES,
        )
    )
    return {
        str(relative): sha256(parent.parent.parent._ordinary_tracked(root, relative))
        for relative in sorted(relatives, key=str)
    }


def _single_change():
    equalities = {
        "selected_count_equal_parent": SELECTED_COUNT == parent.SELECTED_COUNT == 220,
        "executor_concurrency_equal_parent": EXECUTOR_CONCURRENCY == parent.EXECUTOR_CONCURRENCY == 20,
        "model_slot_cap_equal_parent": MODEL_SLOT_CAP == parent.MODEL_SLOT_CAP == 8,
        "limits_equal_parent": LIMITS == parent.LIMITS,
        "model_equal_parent": MODEL == parent.MODEL,
        "search_equal_parent": SEARCH == parent.SEARCH,
        "two_wave_policy_equal_parent": TWO_WAVE_POLICY == parent.TWO_WAVE_POLICY,
    }
    if not all(equalities.values()):
        raise RuntimeError("V2.49.54 parent equality drifted")
    return {
        "field": "schema_header_binding",
        "from": legacy_projector.POLICY_ID,
        "to": projector.POLICY_ID,
        "change": "add mutually unique strict multiset-containment binding for complete pipe headers",
        "same_compact_render_conflict_record_observation_and_budget_policy": True,
        "same_forward_page_bytes_only": True,
        "additional_search_fetch_model_token_context_or_wall_cap": False,
        "entropy_or_information_gain_assigns_credit_or_routes": False,
        "equalities": equalities,
    }


def build_protocol(root: Path, *, now: int, require_clean: bool = True, require_pristine: bool = True):
    if require_clean and (
        parent.parent.parent._git(root, "status", "--porcelain")
        or parent.parent.parent._git(root, "rev-parse", "HEAD")
        != parent.parent.parent._git(root, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.49.54 protocol requires clean pushed HEAD")
    future = (PROTOCOL, PREAUDIT, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT, OUTPUT_ROOT)
    if require_pristine and any((root / path).exists() or (root / path).is_symlink() for path in future):
        raise FileExistsError("V2.49.54 future surface exists")
    base = parent_contract(root)
    tasks = task_vector(root)
    evidence = _evidence(root)
    manifest = dependency_manifest(root)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "git_head": parent.parent.parent._git(root, "rev-parse", "HEAD"),
        "parent_algorithm": {
            "path": str(PARENT_PROTOCOL),
            "sha256": sha256(root / PARENT_PROTOCOL),
            "protocol_id": base["protocol_id"],
            "dependency_manifest_sha256": base["dependency_manifest_sha256"],
            "prior_output_prediction_result_score_or_evaluator_read_or_reused": False,
        },
        "projector": {
            "policy_id": projector.POLICY_ID,
            "source": str(PROJECTOR_SOURCE),
            "source_sha256": sha256(root / PROJECTOR_SOURCE),
            "build_audit": str(PROJECTOR_AUDIT),
            "build_audit_sha256": sha256(root / PROJECTOR_AUDIT),
            "total_character_cap": 30_000,
            "per_page_character_cap": 5_000,
            "visible_question_and_same_forward_pages_only": True,
            "content_free_per_task_receipt": True,
            "entropy_information_gain_shadow_only": True,
            "entropy_or_information_gain_assigns_credit": False,
        },
        "candidate_evidence": evidence,
        "task_contract": _task_contract(tasks),
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "task_wall_seconds": LIMITS["wall_seconds"],
            "model_calls_per_task": LIMITS["model_calls"],
            "search_queries_per_task": LIMITS["search_queries"],
            "fetch_targets_per_task": LIMITS["fetch_targets"],
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "two_wave_policy": copy.deepcopy(TWO_WAVE_POLICY),
            "protected_watchers": protected_watcher_snapshot(),
            "output_root": str(OUTPUT_ROOT),
            "single_fresh_forward_no_retry_resume_or_selective_rerun": True,
        },
        "single_change": _single_change(),
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "runtime_reads_only_opaque_id_and_question": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
            "prior_benchmark_prediction_result_score_or_evaluator_opened_or_hashed": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "fixed_public_exact220_task_set_reexecuted": True,
            "unseen_heldout_or_disjoint_population_claimed": False,
            "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
            "candidate_build_audit_is_safety_evidence_not_quality_evidence": True,
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
    return validate_protocol(root, value, manifest=manifest, tasks=tasks)


def validate_protocol(root: Path, value, *, manifest=None, tasks=None):
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("protocol_payload_sha256", None)
    manifest = dependency_manifest(root) if manifest is None else dict(manifest)
    tasks = task_vector(root) if tasks is None else tasks
    if (
        copied.get("role") != ROLE
        or copied.get("protocol_id") != PROTOCOL_ID
        or seal != payload_sha256(unsigned)
        or copied.get("task_contract") != _task_contract(tasks)
        or copied.get("dependency_manifest") != manifest
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or copied.get("candidate_evidence") != _evidence(root)
        or copied.get("projector", {}).get("policy_id") != projector.POLICY_ID
        or copied.get("projector", {}).get("source_sha256") != sha256(root / PROJECTOR_SOURCE)
        or copied.get("projector", {}).get("build_audit_sha256") != sha256(root / PROJECTOR_AUDIT)
        or copied.get("execution", {}).get("executor_concurrency") != 20
        or copied.get("execution", {}).get("model_slot_cap") != 8
        or copied.get("execution", {}).get("task_wall_seconds") != 240
        or copied.get("execution", {}).get("model_calls_per_task") != 3
        or copied.get("execution", {}).get("search_queries_per_task") != 4
        or copied.get("execution", {}).get("fetch_targets_per_task") != 10
        or copied.get("execution", {}).get("model") != MODEL
        or copied.get("execution", {}).get("search") != SEARCH
        or copied.get("execution", {}).get("two_wave_policy") != TWO_WAVE_POLICY
        or copied.get("execution", {}).get("protected_watchers") != protected_watcher_snapshot()
        or copied.get("single_change") != _single_change()
        or copied.get("source_policy", {}).get("mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward") is not False
        or copied.get("authorization")
        != {
            "preactivation_audit_generation": True,
            "execution_start_generation": False,
            "single_fresh_exact220_forward": False,
            "evaluator_call": False,
            "retry_resume_skip_or_selective_rerun": False,
        }
    ):
        raise RuntimeError("V2.49.54 protocol drifted")
    task_vector(root, copied)
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol",
    "dependency_manifest",
    "parent_contract",
    "payload_sha256",
    "protected_watcher_snapshot",
    "sha256",
    "task_vector",
    "validate_protocol",
]
