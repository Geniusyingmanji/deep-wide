"""Frozen contract for the fresh V2.52.32 header-totality shadow gate.

The population is the already-frozen V2.52.40 visible task vector.  Runtime
code receives exactly ``opaque_id`` and ``question`` plus pages fetched during
that same forward pass.  Population-construction strata, benchmark labels,
gold, evaluator state, and historical correctness are not runtime inputs.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v25232_header_totality_shadow_runtime as runtime


DATE = "20260812"
PROTOCOL_ID = "v25248_header_totality_shadow_external_v1"
ROLE = "v25248_header_totality_shadow_external_contract"
CONTRACT = Path("src/deepwide_agent/v25248_header_totality_shadow_external_contract.py")
RUNNER = Path("scripts/run_v25248_header_totality_shadow_external.py")
CONTROL = Path("scripts/control_v25248_header_totality_shadow_external.py")
TEST = Path("tests/test_v25248_header_totality_shadow_external.py")
BUILD_AUDIT = Path(f"results/v25248_header_totality_shadow_external_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25248_header_totality_shadow_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25248_header_totality_shadow_external_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25248_header_totality_shadow_external_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25248_header_totality_shadow_external_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25248_header_totality_shadow_external_forward_audit_v1_{DATE}.json")
ATTEMPT_CLAIM = Path(f"results/v25248_header_totality_shadow_external_attempt_claim_v1_{DATE}.json")
POPULATION = Path(f"results/v25240_source_package_shadow_population_freeze_v1_{DATE}.json")
POPULATION_SHA256 = "45604e8e4c1d0670890289f9a165f9539bf7dcd50add3cfac4b62d1e638ddcdf"
POPULATION_AUDIT = Path(f"results/v25243_source_package_population_postfreeze_audit_v1_{DATE}.json")
POPULATION_AUDIT_SHA256 = "b53609e617dd7107d57ffa4a109354ec41982ff14265e3d190778557c7a31fa2"
SHADOW_BUILD_AUDIT = Path(f"results/v25233_header_totality_shadow_build_audit_v1_{DATE}.json")
SHADOW_BUILD_AUDIT_SHA256 = "eebbc5577f46998c5a97f75e0e76afac9aa7b3399f6f7a9a78d3256ced130fc2"
REVOKED_PARENT = Path(f"results/v25247_v25244_shadow_start_schema_revocation_v1_{DATE}.json")
REVOKED_PARENT_SHA256 = "2d986b23331249977e641c956a85d0de96f3439e7ca0736cc6caf6f07c2431be"
REVOKED_ATTEMPT_CLAIM = Path(f"results/v25244_header_totality_shadow_external_attempt_claim_v1_{DATE}.json")
REVOKED_FORWARD_RESULT = Path(f"results/v25244_header_totality_shadow_external_forward_result_v1_{DATE}.json")
REVOKED_FORWARD_AUDIT = Path(f"results/v25244_header_totality_shadow_external_forward_audit_v1_{DATE}.json")
REVOKED_OUTPUT_ROOT = Path(f"outputs/v25244_header_totality_shadow_external_v1_{DATE}")

OUTPUT_ROOT = Path(f"outputs/v25248_header_totality_shadow_external_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"

TASK_COUNT = 64
EXECUTOR_CONCURRENCY = 32
MODEL_SLOT_CAP = 16
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v25248_header_totality_shadow_external_forward_v1"
LEASE_PURPOSE = "fresh64_behavior_preserving_header_totality_shadow"
MODEL = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "name": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 65,
    "max_retries": 2,
}
SEARCH = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "model": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 65,
    "max_retries": 2,
    "workers": 1,
    "batch_size": 8,
    "context_size": "medium",
    "max_output_tokens": 7000,
    "server_auto_fetch_enabled": False,
    "fetch_workers": 8,
    "fetch_timeout_seconds": 20,
    "hard_fetch_deadline_seconds": 25,
}
LIMITS = {
    "search_queries": 4,
    "search_results_per_query": 3,
    "fetch_targets": 10,
    "model_calls": 3,
    "evidence_chars": 60000,
    "page_chars": 5000,
    "plan_output_tokens": 4000,
    "synthesis_output_tokens": 30000,
    "repair_output_tokens": 12000,
    "wall_seconds": 240,
}
CLEANUP_RESERVE_SECONDS = 5.0
MINIMUM_MODEL_ATTEMPT_SECONDS = 0.05
ARMS = runtime.ARMS
CONTROL_ARM = runtime.CONTROL_ARM
CANDIDATE_ARM = runtime.CANDIDATE_ARM
COLUMNS = ("Package", "Latest stable version", "License", "Short purpose")
PROTECTED_WATCHERS = {
    795336: 713986317,
    2808901: 746680268,
    2889939: 746969965,
    3061652: 747569004,
}
TASK_VECTOR_SHA256 = "dc9cf8e96e1bf6eb68252eb342b675e7c0682509d4f42357599002e25236dadd"
OPAQUE_ID_VECTOR_SHA256 = "3534d22cb3432ed5b63e5b7fdd78d832acc41fea39e64e9612364dbf0b197ebc"
QUESTION_VECTOR_SHA256 = "3b3310b7f257745e2c0f78cee3ed4fd186fec5382b96e3717d7e63969b3e6046"
QUESTION = re.compile(
    r"\AResearch these four public Debian source packages in the given order: "
    r"`[a-z0-9][a-z0-9+.-]*`, `[a-z0-9][a-z0-9+.-]*`, "
    r"`[a-z0-9][a-z0-9+.-]*`, and `[a-z0-9][a-z0-9+.-]*`\. "
    r"Return exactly one Markdown table with one row per package in the same "
    r"order\. Columns exactly: Package \| Latest stable version \| License \| "
    r"Short purpose\. Use Unknown for any unavailable cell; do not omit a package\.\Z"
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def seal(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if field in copied:
        raise ValueError("V2.52.48 seal field already exists")
    copied[field] = payload_sha256(copied)
    return copied


def sealed(value: Mapping[str, Any], field: str) -> bool:
    copied = copy.deepcopy(dict(value))
    observed = copied.pop(field, None)
    return isinstance(observed, str) and observed == payload_sha256(copied)


def ordinary(root: Path, relative: Path, *, tracked: bool = True) -> Path:
    repository = Path(root).resolve()
    path = repository / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(repository)
    ):
        raise RuntimeError("V2.52.48 expected ordinary repository file")
    if tracked:
        completed = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)],
            cwd=repository,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError("V2.52.48 expected tracked repository file")
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def watcher_snapshot() -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for pid, expected in PROTECTED_WATCHERS.items():
        path = Path("/proc") / str(pid) / "stat"
        if not path.is_file():
            values.append({"pid": pid, "start_ticks": None, "matches_frozen_identity": False})
            continue
        raw = path.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        start = int(suffix[19]) if len(suffix) > 19 else None
        values.append({"pid": pid, "start_ticks": start, "matches_frozen_identity": start == expected})
    return values


def validate_revoked_parent(root: Path | None = None) -> dict[str, Any]:
    """Bind the pre-effect V2.52.44 revocation and keep its old effects absent."""

    repository = Path(__file__).resolve().parents[2] if root is None else Path(root).resolve()
    path = ordinary(repository, REVOKED_PARENT, tracked=True)
    if sha256(path) != REVOKED_PARENT_SHA256:
        raise RuntimeError("V2.52.48 revoked parent hash drifted")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise RuntimeError("V2.52.48 revoked parent is not an object")
    copied = copy.deepcopy(dict(value))
    failure = copied.get("failure") or {}
    revocation = copied.get("revocation") or {}
    authorization = copied.get("authorization") or {}
    runtime_state = copied.get("runtime_state") or {}
    old_surfaces = (
        REVOKED_ATTEMPT_CLAIM,
        REVOKED_FORWARD_RESULT,
        REVOKED_FORWARD_AUDIT,
        REVOKED_OUTPUT_ROOT,
    )
    if (
        set(copied)
        != {
            "artifact_version", "authorization", "created_at_unix",
            "entropy_or_information_gain_assigns_signed_credit", "failure",
            "frozen_chain", "git",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "revocation", "role", "runtime_state", "revocation_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25247_v25244_shadow_start_schema_revocation"
        or not isinstance(copied.get("created_at_unix"), int)
        or failure
        != {
            "actual_execution_start_extra_keys": ["git_head"],
            "attempt_claim_created": False,
            "endpoint_probe_model_search_fetch_or_output_effect_occurred": False,
            "failure_stage": "runner_execution_start_exact_schema_validation",
            "forward_result_or_output_root_created": False,
            "runner_exception_type": "RuntimeError",
            "runner_start_validation_passed": False,
            "status": "pre_effect_no_go",
        }
        or revocation
        != {
            "old_attempt_claim_result_and_output_surfaces_remain_absent": True,
            "old_execution_start_authority_revoked": True,
            "old_protocol_or_execution_start_must_not_be_reused_or_resealed": True,
            "successor_must_revalidate_runner_start_at_entrypoint_before_new_start": True,
            "successor_requires_new_protocol_id_artifact_paths_attempt_claim_and_output_root": True,
        }
        or authorization
        != {
            "candidate_activation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
            "fresh_successor_build_with_new_protocol_artifact_and_output_namespace": True,
            "retry_resume_reuse_or_reseal_v25244_execution_start": False,
            "v25244_external_forward": False,
        }
        or runtime_state
        != {
            "active_v25244_forward_process": False,
            "protected_watcher_identity_drift_count": 0,
            "shared_api_lease_inactive": True,
        }
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read") is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called") is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or not sealed(copied, "revocation_payload_sha256")
        or any((repository / relative).exists() or (repository / relative).is_symlink() for relative in old_surfaces)
    ):
        raise RuntimeError("V2.52.48 revoked parent semantics drifted")
    return copied


def validate_task_vector(values: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.52.48 task denominator drifted")
    output: list[dict[str, str]] = []
    for value in values:
        if not isinstance(value, Mapping) or set(value) != {"opaque_id", "question"}:
            raise ValueError("V2.52.48 runtime task boundary drifted")
        opaque_id = value.get("opaque_id")
        question = value.get("question")
        if (
            not isinstance(opaque_id, str)
            or re.fullmatch(r"task_[0-9a-f]{24}", opaque_id) is None
            or not isinstance(question, str)
            or QUESTION.fullmatch(question) is None
        ):
            raise ValueError("V2.52.48 visible task field drifted")
        output.append({"opaque_id": opaque_id, "question": question})
    if (
        len({row["opaque_id"] for row in output}) != TASK_COUNT
        or payload_sha256(output) != TASK_VECTOR_SHA256
        or payload_sha256([row["opaque_id"] for row in output]) != OPAQUE_ID_VECTOR_SHA256
        or payload_sha256([row["question"] for row in output]) != QUESTION_VECTOR_SHA256
    ):
        raise ValueError("V2.52.48 visible task vector hash drifted")
    return output


def task_vector(root: Path | None = None) -> list[dict[str, str]]:
    repository = Path(__file__).resolve().parents[2] if root is None else Path(root).resolve()
    validate_revoked_parent(repository)
    population_path = ordinary(repository, POPULATION, tracked=True)
    audit_path = ordinary(repository, POPULATION_AUDIT, tracked=True)
    if sha256(population_path) != POPULATION_SHA256 or sha256(audit_path) != POPULATION_AUDIT_SHA256:
        raise RuntimeError("V2.52.48 population authority hash drifted")
    population = json.loads(population_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    tasks = validate_task_vector((population.get("population") or {}).get("task_vector"))
    if (
        population.get("role") != "v25240_source_package_shadow_population_freeze"
        or population.get("status") != "frozen"
        or population.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read") is not False
        or population.get("network_model_search_fetch_evaluator_benchmark_or_api_called") is not False
        or population.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or (population.get("population") or {}).get("runtime_keys_exactly_opaque_id_and_question") is not True
        or (population.get("population") or {}).get("task_vector_sha256") != TASK_VECTOR_SHA256
        or audit.get("role") != "v25243_source_package_population_postfreeze_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or (audit.get("authorization") or {}).get("fresh64_shadow_reliability_protocol_design") is not True
        or (audit.get("authorization") or {}).get("fresh64_shadow_external_activation_or_launch") is not False
    ):
        raise RuntimeError("V2.52.48 population authority drifted")
    return tasks


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "population_stratum_or_hidden_identity_mapping_passed_to_runtime": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "only_treatment_is_behavior_preserving_v25232_header_totality_shadow": True,
        "shadow_candidate_is_discarded_and_never_changes_parent_response_or_prediction": True,
        "model_search_prompt_retrieval_and_budget_match_v25208_production": True,
        "fixed64_failure_as_zero_no_retry_resume_skip_replacement_or_selective_rerun": True,
        "evaluator_or_quality_metric_called": False,
        "entropy_or_information_gain_assigns_signed_credit_or_routes": False,
        "positive_signed_credit_count": 0,
        "revoked_v25244_start_protocol_attempt_and_output_never_reused": True,
        "successor_start_revalidated_at_runner_entry_before_any_effect": True,
    }


def mechanism_gate() -> dict[str, Any]:
    return {
        "fixed_task_denominator": 64,
        "terminal_tasks": 64,
        "required_completed_runtime_tasks": 64,
        "minimum_natural_shadow_entry_tasks": 1,
        "minimum_safe_shadow_candidate_tasks": 1,
        "maximum_shadow_observer_failure_tasks": 0,
        "maximum_parent_behavior_drift_tasks": 0,
        "maximum_shadow_prediction_change_tasks": 0,
        "maximum_physical_queries_total": 64 * LIMITS["search_queries"],
        "maximum_physical_fetches_total": 64 * LIMITS["fetch_targets"],
        "maximum_model_forwards_total": 64 * LIMITS["model_calls"],
        "all_task_rows_and_content_free_receipts_valid": True,
        "positive_signed_credit_count": 0,
        "mechanism_go_only_authorizes_independent_activation_and_quality_design": True,
    }


def build_protocol(*, source_manifest: Mapping[str, str], now: int) -> dict[str, Any]:
    tasks = task_vector()
    value = {
        "artifact_version": 1,
        "role": "v25248_header_totality_shadow_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "parents": {
            str(POPULATION): POPULATION_SHA256,
            str(POPULATION_AUDIT): POPULATION_AUDIT_SHA256,
            str(SHADOW_BUILD_AUDIT): SHADOW_BUILD_AUDIT_SHA256,
            str(REVOKED_PARENT): REVOKED_PARENT_SHA256,
        },
        "source_manifest": dict(source_manifest),
        "population": {
            "task_count": TASK_COUNT,
            "task_vector_sha256": payload_sha256(tasks),
            "opaque_id_vector_sha256": payload_sha256([row["opaque_id"] for row in tasks]),
            "question_vector_sha256": payload_sha256([row["question"] for row in tasks]),
            "runtime_keys": ["opaque_id", "question"],
        },
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "single_cold_forward": True,
            "failure_as_zero_fixed_denominator": True,
            "retry_resume_skip_replacement_or_selective_rerun": False,
            "protected_watchers": watcher_snapshot(),
        },
        "model": copy.deepcopy(MODEL),
        "search": copy.deepcopy(SEARCH),
        "limits": copy.deepcopy(LIMITS),
        "source_policy": source_policy(),
        "mechanism_gate": mechanism_gate(),
        "authorization": {
            "preactivation_audit_generation": True,
            "external_forward": False,
            "candidate_activation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    return seal(value, "protocol_payload_sha256")


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    parents = copied.get("parents") or {}
    population = copied.get("population") or {}
    execution = copied.get("execution") or {}
    authorization = copied.get("authorization") or {}
    source_manifest = copied.get("source_manifest")
    expected_top = {
        "artifact_version", "role", "protocol_id", "created_at_unix", "parents",
        "source_manifest", "population", "execution", "model", "search", "limits",
        "source_policy", "mechanism_gate", "authorization", "protocol_payload_sha256",
    }
    tasks = task_vector(root)
    if (
        set(copied) != expected_top
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25248_header_totality_shadow_external_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not isinstance(copied.get("created_at_unix"), int)
        or parents != {
            str(POPULATION): POPULATION_SHA256,
            str(POPULATION_AUDIT): POPULATION_AUDIT_SHA256,
            str(SHADOW_BUILD_AUDIT): SHADOW_BUILD_AUDIT_SHA256,
            str(REVOKED_PARENT): REVOKED_PARENT_SHA256,
        }
        or not isinstance(source_manifest, Mapping)
        or not source_manifest
        or any(
            not isinstance(path, str)
            or not path
            or Path(path).is_absolute()
            or ".." in Path(path).parts
            or re.fullmatch(r"[0-9a-f]{64}", str(digest)) is None
            for path, digest in source_manifest.items()
        )
        or set(population) != {
            "task_count", "task_vector_sha256", "opaque_id_vector_sha256",
            "question_vector_sha256", "runtime_keys",
        }
        or population.get("task_count") != TASK_COUNT
        or population.get("task_vector_sha256") != payload_sha256(tasks)
        or population.get("opaque_id_vector_sha256") != payload_sha256([row["opaque_id"] for row in tasks])
        or population.get("question_vector_sha256") != payload_sha256([row["question"] for row in tasks])
        or population.get("runtime_keys") != ["opaque_id", "question"]
        or set(execution) != {
            "executor_concurrency", "model_slot_cap", "single_cold_forward",
            "failure_as_zero_fixed_denominator",
            "retry_resume_skip_replacement_or_selective_rerun", "protected_watchers",
        }
        or execution.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or execution.get("model_slot_cap") != MODEL_SLOT_CAP
        or execution.get("single_cold_forward") is not True
        or execution.get("failure_as_zero_fixed_denominator") is not True
        or execution.get("retry_resume_skip_replacement_or_selective_rerun") is not False
        or execution.get("protected_watchers") != watcher_snapshot()
        or copied.get("model") != MODEL
        or copied.get("search") != SEARCH
        or copied.get("limits") != LIMITS
        or copied.get("source_policy") != source_policy()
        or copied.get("mechanism_gate") != mechanism_gate()
        or authorization != {
            "preactivation_audit_generation": True,
            "external_forward": False,
            "candidate_activation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or not sealed(copied, "protocol_payload_sha256")
    ):
        raise ValueError("V2.52.48 shadow protocol drifted")
    return copied


__all__ = [
    "ARMS", "ATTEMPT_CLAIM", "BUILD_AUDIT", "CANDIDATE_ARM", "CLEANUP_RESERVE_SECONDS",
    "COLUMNS", "CONTRACT", "CONTROL", "CONTROL_ARM", "DATE",
    "EXECUTION_START", "EXECUTOR_CONCURRENCY", "FORWARD_AUDIT", "FORWARD_RESULT",
    "LEASE_OWNER", "LEASE_PATH", "LEASE_PURPOSE", "LIMITS", "MINIMUM_MODEL_ATTEMPT_SECONDS",
    "MODEL", "MODEL_SLOT_CAP", "MODEL_SLOT_DIRECTORY", "OUTPUT_ROOT", "POPULATION",
    "POPULATION_AUDIT", "PREAUDIT", "PROTOCOL", "PROTOCOL_ID", "PROTECTED_WATCHERS",
    "REVOKED_ATTEMPT_CLAIM", "REVOKED_FORWARD_AUDIT", "REVOKED_FORWARD_RESULT",
    "REVOKED_OUTPUT_ROOT", "REVOKED_PARENT", "REVOKED_PARENT_SHA256", "RUNNER",
    "SAFE_PROGRESS", "SEARCH", "SHADOW_BUILD_AUDIT", "TASK_COUNT",
    "TASK_ROWS", "TEST", "build_protocol", "git", "mechanism_gate", "ordinary",
    "payload_sha256", "runtime", "seal", "sealed", "sha256", "source_policy",
    "task_vector", "validate_protocol", "validate_revoked_parent", "validate_task_vector",
    "watcher_snapshot",
]
