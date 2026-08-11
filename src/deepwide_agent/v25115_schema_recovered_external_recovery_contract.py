"""Append-only recovery contract after V2.51.13 zero-effect preactivation failure."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v25113_schema_recovered_external_contract as parent


DATE = parent.DATE
PROTOCOL_ID = "v25115_schema_recovered_external_recovery_mechanism_v1"
BUILD_AUDIT = Path(f"results/v25115_schema_recovered_external_recovery_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25115_schema_recovered_external_recovery_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25115_schema_recovered_external_recovery_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25115_schema_recovered_external_recovery_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25115_schema_recovered_external_recovery_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25115_schema_recovered_external_recovery_forward_audit_v1_{DATE}.json")
EVALUATOR = Path("scripts/evaluate_v25115_schema_recovered_external_recovery.py")
EVALUATOR_TEST = Path("tests/test_evaluate_v25115_schema_recovered_external_recovery.py")
EVALUATOR_PROTOCOL = Path(
    f"results/v25115_schema_recovered_external_recovery_evaluator_preregistration_v1_{DATE}.json"
)
RESULT = Path(f"results/v25115_schema_recovered_external_recovery_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v25115_schema_recovered_external_recovery_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v25115_schema_recovered_external_recovery_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
POSTFREEZE_GOLD = OUTPUT_ROOT / "postfreeze_pypi_gold.jsonl"

CONTRACT = Path("src/deepwide_agent/v25115_schema_recovered_external_recovery_contract.py")
RUNNER = Path("scripts/run_v25115_schema_recovered_external_recovery.py")
CONTROL = Path("scripts/control_v25115_schema_recovered_external_recovery.py")
TEST = Path("tests/test_v25115_schema_recovered_external_recovery.py")
HELPER = parent.HELPER
PARENT_AUDIT = Path("results/v25114_v25113_failed_preactivation_audit_v1_20260811.json")
PARENT_AUDIT_SHA256 = "1640bda8130cb11c16b61d77b5a07c10fa1f1b8c967944d9aca4800f3033d9e4"
FAILED_PARENT_BUILD = parent.BUILD_AUDIT
FAILED_PARENT_BUILD_SHA256 = "9b3b5207c5d3a7b66948dd7ea86a4001b6ae98a8371127749df4b139d8d0d398"
FAILED_PARENT_PROTOCOL = parent.PROTOCOL
FAILED_PARENT_PROTOCOL_SHA256 = "088ffc59d2c08467a4e59ba5eac2f2eb73adba7647a7b1e1f5ae2f5d263b7717"
FORWARD_SOURCES = (CONTRACT, RUNNER, HELPER)

TASK_COUNT = parent.TASK_COUNT
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
FRESHNESS_PARENT_COMMIT = parent.FRESHNESS_PARENT_COMMIT
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v25115_schema_recovered_external_recovery_forward_v1"
LEASE_PURPOSE = "zero_effect_recovery_label_blind_exact_visible_schema_mechanism_gate"
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = copy.deepcopy(parent.SEARCH)
LIMITS = copy.deepcopy(parent.LIMITS)
CLEANUP_RESERVE_SECONDS = parent.CLEANUP_RESERVE_SECONDS
MINIMUM_MODEL_ATTEMPT_SECONDS = parent.MINIMUM_MODEL_ATTEMPT_SECONDS
ARMS = parent.ARMS
CONTROL_ARM, CANDIDATE_ARM = ARMS
COLUMNS = parent.COLUMNS
EXPECTED_WATCHERS = parent.EXPECTED_WATCHERS
PROJECTS = parent.PROJECTS
SECRET = parent.SECRET

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
seal = parent.seal
sealed = parent.sealed
git = parent.git
ordinary = parent.ordinary
watcher_snapshot = parent.watcher_snapshot


def task_vector() -> list[dict[str, str]]:
    return parent.task_vector()


def validate_task_vector(values: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    return parent.validate_task_vector(values)


def arm_order_vector() -> list[list[str]]:
    return parent.arm_order_vector()


def source_policy() -> dict[str, Any]:
    value = copy.deepcopy(parent.source_policy())
    value.update(
        {
            "recovery_reuses_only_zero_runtime_effect_population_and_frozen_vectors": True,
            "failed_v25113_protocol_is_never_overwritten_activated_or_resumed": True,
            "only_recovery_change_is_phase_stable_tests_and_fresh_control_namespace": True,
        }
    )
    return value


def mechanism_gate() -> dict[str, Any]:
    return copy.deepcopy(parent.mechanism_gate())


def quality_gate() -> dict[str, Any]:
    return copy.deepcopy(parent.quality_gate())


def forward_dependency_closure(root: Path) -> tuple[Path, ...]:
    pending = list(FORWARD_SOURCES)
    observed: set[Path] = set()
    while pending:
        relative = pending.pop()
        if relative in observed:
            continue
        path = ordinary(root, relative, tracked=False)
        observed.add(relative)
        if path.suffix != ".py":
            continue
        import ast

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            for candidate in parent.base._module_candidates(relative, node):
                if (root / candidate).is_file() and not (root / candidate).is_symlink():
                    pending.append(candidate)
    return tuple(sorted(observed, key=str))


def dependency_manifest(root: Path, *, tracked: bool) -> dict[str, str]:
    relatives = {
        *forward_dependency_closure(root),
        CONTROL,
        TEST,
        PARENT_AUDIT,
        FAILED_PARENT_BUILD,
        FAILED_PARENT_PROTOCOL,
    }
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.51.15 credential literal in source manifest")
        output[str(relative)] = sha256(path)
    return output


def build_protocol(
    root: Path,
    *,
    now: int,
    tracked: bool,
    require_pristine: bool,
    build_audit_sha256: str,
) -> dict[str, Any]:
    future = (
        PROTOCOL,
        PREAUDIT,
        EXECUTION_START,
        FORWARD_RESULT,
        FORWARD_AUDIT,
        EVALUATOR,
        EVALUATOR_TEST,
        EVALUATOR_PROTOCOL,
        RESULT,
        POSTAUDIT,
        OUTPUT_ROOT,
    )
    if require_pristine and any(
        (root / path).exists() or (root / path).is_symlink() for path in future
    ):
        raise RuntimeError("V2.51.15 future surface is not pristine")
    if sha256(root / PARENT_AUDIT) != PARENT_AUDIT_SHA256:
        raise RuntimeError("V2.51.15 failed preactivation audit drifted")
    if sha256(root / FAILED_PARENT_BUILD) != FAILED_PARENT_BUILD_SHA256:
        raise RuntimeError("V2.51.15 failed parent build drifted")
    if sha256(root / FAILED_PARENT_PROTOCOL) != FAILED_PARENT_PROTOCOL_SHA256:
        raise RuntimeError("V2.51.15 failed parent protocol drifted")
    manifest = dependency_manifest(root, tracked=tracked)
    tasks = task_vector()
    value = {
        "artifact_version": 1,
        "role": "v25115_schema_recovered_external_recovery_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit_sha256": build_audit_sha256,
        "recovery_parent": {
            "failed_preactivation_audit_path": str(PARENT_AUDIT),
            "failed_preactivation_audit_sha256": PARENT_AUDIT_SHA256,
            "failed_build_path": str(FAILED_PARENT_BUILD),
            "failed_build_sha256": FAILED_PARENT_BUILD_SHA256,
            "failed_protocol_path": str(FAILED_PARENT_PROTOCOL),
            "failed_protocol_sha256": FAILED_PARENT_PROTOCOL_SHA256,
            "failed_parent_runtime_effects": 0,
        },
        "freshness": {
            "parent_commit": FRESHNESS_PARENT_COMMIT,
            "parent_history_literal_zero_hit_projects": list(PROJECTS),
            "endpoint_page_value_model_or_evaluator_opened_during_selection": False,
            "same_population_reuse_authorized_only_because_failed_parent_runtime_effects_zero": True,
        },
        "population": {
            "task_count": TASK_COUNT,
            "project_vector_sha256": payload_sha256(PROJECTS),
            "task_vector_sha256": payload_sha256(tasks),
            "opaque_id_vector_sha256": payload_sha256([row["opaque_id"] for row in tasks]),
            "arm_order_vector_sha256": payload_sha256(arm_order_vector()),
        },
        "execution": {
            "arms": list(ARMS),
            "only_treatment": "same_length_verified_field_enforced_representation",
            "exact_visible_schema_recovery": True,
            "separated_stage_failure_accounting": True,
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "limits": copy.deepcopy(LIMITS),
            "query_policy": "one_visible_only_plan_four_queries_shared_by_both_arms",
            "physical_paired_model_call_cap": 4,
            "effective_model_call_cap_per_arm": 3,
            "unexposed_prediction_identity_handoff": True,
            "representation_validation_failure_safe_identity_handoff": True,
            "post_synthesis_accounting_or_receipt_validation_failure_terminal_no_go": True,
            "single_atomic_forward_no_retry_resume_skip_or_replacement": True,
        },
        "mechanism_gate": mechanism_gate(),
        "quality_gate": quality_gate(),
        "protected_watchers": watcher_snapshot(),
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": source_policy(),
        "authorization": {
            "one_recovery_external_forward_after_separate_clean_pushed_start": True,
            "failed_v25113_protocol_activation_or_resume": False,
            "evaluator_implementation_only_after_prediction_freeze_and_pushed_forward_audit_go": True,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_revaluation": False,
        },
    }
    return seal(value, "protocol_payload_sha256")


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = build_protocol(
        root,
        now=int(copied.get("created_at_unix", -1)),
        tracked=True,
        require_pristine=False,
        build_audit_sha256=sha256(root / BUILD_AUDIT),
    )
    if copied != expected or not sealed(copied, "protocol_payload_sha256"):
        raise RuntimeError("V2.51.15 protocol drifted")
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "arm_order_vector",
    "build_protocol",
    "dependency_manifest",
    "forward_dependency_closure",
    "git",
    "mechanism_gate",
    "ordinary",
    "payload_sha256",
    "quality_gate",
    "seal",
    "sealed",
    "sha256",
    "source_policy",
    "task_vector",
    "validate_protocol",
    "validate_task_vector",
    "watcher_snapshot",
]
