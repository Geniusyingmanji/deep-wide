"""Frozen contract for a fresh20 same-forward checkpoint reliability gate."""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v25248_header_totality_shadow_external_contract as foundation
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25278_paired_checkpoint_reliability_runtime as runtime


DATE = "20260813"
PROTOCOL_ID = "v25280_paired_checkpoint_reliability_external_v1"
ROLE = "v25280_paired_checkpoint_reliability_external_contract"
CONTRACT = Path(
    "src/deepwide_agent/v25280_paired_checkpoint_reliability_external_contract.py"
)
RUNNER = Path("scripts/run_v25280_paired_checkpoint_reliability_external.py")
CONTROL = Path("scripts/control_v25280_paired_checkpoint_reliability_external.py")
TEST = Path("tests/test_v25280_paired_checkpoint_reliability_external.py")
BUILD_AUDIT = Path(f"results/v25281_paired_checkpoint_external_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25280_paired_checkpoint_reliability_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25282_paired_checkpoint_reliability_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25282_paired_checkpoint_reliability_execution_start_v1_{DATE}.json")
ATTEMPT_CLAIM = Path(f"results/v25280_paired_checkpoint_reliability_attempt_claim_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25280_paired_checkpoint_reliability_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25283_paired_checkpoint_reliability_forward_audit_v1_{DATE}.json")

POPULATION = Path(
    "results/v25274_third_disjoint_checkpoint_population_freeze_v1_20260812.json"
)
POPULATION_SHA256 = (
    "f23c64907535ac2cd2bf57f30e51086f9247f36cd51bb5a1b1fff9df5155b5ad"
)
POPULATION_AUDIT = Path(
    "results/v25277_third_disjoint_checkpoint_population_postfreeze_audit_v1_20260813.json"
)
POPULATION_AUDIT_SHA256 = (
    "deeaac00d0a294f877f15de7152b535abee60219227bd4d09ac501532d024457"
)
RUNTIME_BUILD_AUDIT = Path(
    "results/v25279_paired_checkpoint_reliability_build_audit_v1_20260813.json"
)
RUNTIME_BUILD_AUDIT_SHA256 = (
    "b2281791caacbf6302c357fe00c75b063f47eece13d0696c1fb9e22fe5c4b253"
)

OUTPUT_ROOT = Path(f"outputs/v25280_paired_checkpoint_reliability_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"

TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 16
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v25280_paired_checkpoint_reliability_forward_v1"
LEASE_PURPOSE = "fresh20_same_forward_validated_checkpoint_reliability"
MODEL = copy.deepcopy(foundation.MODEL)
SEARCH = copy.deepcopy(foundation.SEARCH)
LIMITS = copy.deepcopy(foundation.LIMITS)
PHYSICAL_CAPS = {
    "queries_per_task": cap.QUERY_CAP,
    "fetches_per_task": cap.FETCH_CAP,
    "model_forwards_per_task": cap.MODEL_CAP,
}
CLEANUP_RESERVE_SECONDS = foundation.CLEANUP_RESERVE_SECONDS
MINIMUM_MODEL_ATTEMPT_SECONDS = foundation.MINIMUM_MODEL_ATTEMPT_SECONDS
COLUMNS = foundation.COLUMNS
PROTECTED_WATCHERS = copy.deepcopy(foundation.PROTECTED_WATCHERS)
TASK_VECTOR_SHA256 = (
    "a9696499bd2a2ac5d9254027c8d03505f981219325299e2ca8938b0163ad8a04"
)
OPAQUE_ID_VECTOR_SHA256 = (
    "12138ca2bb81a56244f42b1ddea4bdfaae3bbc49d9d33f55eb36ef2d1d45d57a"
)
QUESTION_VECTOR_SHA256 = (
    "1c1b340e916f8c3c1b6b3914aa404931f7f3239622ff3e6d76847b7ec4b8e195"
)
QUESTION = re.compile(
    r"\AResearch these two public Debian source packages in the given order: "
    r"`([a-z0-9][a-z0-9+.-]*)` and `([a-z0-9][a-z0-9+.-]*)`\. "
    r"Return exactly one Markdown table with one row per package in the same "
    r"order\. Columns exactly: Package \| Latest stable version \| License \| "
    r"Short purpose\. Use Unknown for any unavailable cell; do not omit a package\.\Z"
)

payload_sha256 = foundation.payload_sha256
seal = foundation.seal
sealed = foundation.sealed
ordinary = foundation.ordinary
sha256 = foundation.sha256
git = foundation.git
watcher_snapshot = foundation.watcher_snapshot


def packages_from_question(question: str) -> tuple[str, str]:
    match = QUESTION.fullmatch(str(question))
    if match is None:
        raise ValueError("V2.52.80 visible question grammar drifted")
    return match.group(1), match.group(2)


def validate_task_vector(values: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.52.80 task denominator drifted")
    output: list[dict[str, str]] = []
    entities: list[str] = []
    for value in values:
        if not isinstance(value, Mapping) or set(value) != {"opaque_id", "question"}:
            raise ValueError("V2.52.80 runtime task boundary drifted")
        opaque_id = value.get("opaque_id")
        question = value.get("question")
        if (
            not isinstance(opaque_id, str)
            or re.fullmatch(r"task_[0-9a-f]{24}", opaque_id) is None
            or not isinstance(question, str)
        ):
            raise ValueError("V2.52.80 visible task field drifted")
        entities.extend(packages_from_question(question))
        output.append({"opaque_id": opaque_id, "question": question})
    if (
        len({row["opaque_id"] for row in output}) != TASK_COUNT
        or len(entities) != 40
        or len(set(entities)) != 40
        or payload_sha256(output) != TASK_VECTOR_SHA256
        or payload_sha256([row["opaque_id"] for row in output])
        != OPAQUE_ID_VECTOR_SHA256
        or payload_sha256([row["question"] for row in output])
        != QUESTION_VECTOR_SHA256
    ):
        raise ValueError("V2.52.80 visible task vector seal drifted")
    return output


def task_vector(root: Path | None = None) -> list[dict[str, str]]:
    repository = Path(__file__).resolve().parents[2] if root is None else Path(root).resolve()
    population_path = ordinary(repository, POPULATION, tracked=True)
    audit_path = ordinary(repository, POPULATION_AUDIT, tracked=True)
    runtime_audit_path = ordinary(repository, RUNTIME_BUILD_AUDIT, tracked=True)
    if (
        sha256(population_path) != POPULATION_SHA256
        or sha256(audit_path) != POPULATION_AUDIT_SHA256
        or sha256(runtime_audit_path) != RUNTIME_BUILD_AUDIT_SHA256
    ):
        raise RuntimeError("V2.52.80 parent authority hash drifted")
    population = json.loads(population_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    runtime_audit = json.loads(runtime_audit_path.read_text(encoding="utf-8"))
    tasks = validate_task_vector((population.get("population") or {}).get("task_vector"))
    if (
        population.get("role")
        != "v25274_third_disjoint_checkpoint_population_freeze"
        or population.get("status") != "frozen"
        or population.get(
            "network_model_search_fetch_evaluator_benchmark_or_api_called"
        )
        is not False
        or population.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or population.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or (population.get("population") or {}).get("runtime_keys")
        != ["opaque_id", "question"]
        or (population.get("population") or {}).get("task_vector_sha256")
        != TASK_VECTOR_SHA256
        or audit.get("role")
        != "v25277_third_disjoint_checkpoint_population_postfreeze_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or (audit.get("authorization") or {}).get(
            "paired_checkpoint_reliability_protocol_design"
        )
        is not True
        or (audit.get("authorization") or {}).get(
            "paired_checkpoint_reliability_external_activation_or_launch"
        )
        is not False
        or runtime_audit.get("role")
        != "v25279_paired_checkpoint_reliability_clean_build_audit"
        or runtime_audit.get("audit_valid") is not True
        or runtime_audit.get("findings") != []
        or runtime_audit.get("physical_caps")
        != {"queries": 4, "fetches": 14, "model_forwards": 4}
        or (runtime_audit.get("authorization") or {}).get(
            "paired_checkpoint_reliability_protocol_build"
        )
        is not True
        or (runtime_audit.get("authorization") or {}).get(
            "external_activation_or_launch"
        )
        is not False
    ):
        raise RuntimeError("V2.52.80 parent authority semantics drifted")
    return tasks


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "population_stratum_history_outcome_or_hidden_identity_mapping_passed_to_runtime": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "one_real_forward_per_task_then_local_same_checkpoint_projection": True,
        "control_is_clean_v25271_result": True,
        "candidate_is_fixed_result_envelope_validate_fault_recovery": True,
        "candidate_additional_query_fetch_model_or_token_effect": False,
        "model_search_prompt_retrieval_and_logical_limits_match_frozen_parent": True,
        "truthful_outer_physical_query4_fetch14_model4_caps": True,
        "fixed20_failure_as_zero_no_retry_resume_skip_replacement_or_selective_rerun": True,
        "quality_metric_or_evaluator_called": False,
        "entropy_or_information_gain_assigns_signed_credit_or_routes": False,
        "positive_signed_credit_count": 0,
    }


def reliability_gate() -> dict[str, Any]:
    return {
        "fixed_task_denominator": TASK_COUNT,
        "required_terminal_tasks": TASK_COUNT,
        "required_completed_runtime_tasks": TASK_COUNT,
        "required_clean_trusted_checkpoint_tasks": TASK_COUNT,
        "required_candidate_recovery_tasks": TASK_COUNT,
        "required_prediction_equal_tasks": TASK_COUNT,
        "required_checkpoint_equal_tasks": TASK_COUNT,
        "required_cost_equal_tasks": TASK_COUNT,
        "required_budget_receipt_equal_tasks": TASK_COUNT,
        "required_fixed_fault_identity_tasks": TASK_COUNT,
        "maximum_outer_failure_tasks": 0,
        "maximum_budget_rejection_tasks": 0,
        "maximum_candidate_additional_queries_total": 0,
        "maximum_candidate_additional_fetches_total": 0,
        "maximum_candidate_additional_model_forwards_total": 0,
        "maximum_candidate_additional_system_total_tokens": 0,
        "maximum_physical_queries_total": TASK_COUNT * cap.QUERY_CAP,
        "maximum_physical_fetches_total": TASK_COUNT * cap.FETCH_CAP,
        "maximum_model_forwards_total": TASK_COUNT * cap.MODEL_CAP,
        "all_task_rows_runtime_paired_and_budget_receipts_valid": True,
        "positive_signed_credit_count": 0,
        "go_only_authorizes_postforward_reliability_audit_and_diagnosis": True,
    }


def build_protocol(*, source_manifest: Mapping[str, str], now: int) -> dict[str, Any]:
    tasks = task_vector()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25280_paired_checkpoint_reliability_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "parents": {
            str(POPULATION): POPULATION_SHA256,
            str(POPULATION_AUDIT): POPULATION_AUDIT_SHA256,
            str(RUNTIME_BUILD_AUDIT): RUNTIME_BUILD_AUDIT_SHA256,
        },
        "source_manifest": dict(source_manifest),
        "population": {
            "task_count": TASK_COUNT,
            "task_vector_sha256": payload_sha256(tasks),
            "opaque_id_vector_sha256": payload_sha256(
                [row["opaque_id"] for row in tasks]
            ),
            "question_vector_sha256": payload_sha256(
                [row["question"] for row in tasks]
            ),
            "runtime_keys": ["opaque_id", "question"],
        },
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "single_cold_forward": True,
            "one_real_forward_per_task": True,
            "candidate_local_projection_only": True,
            "failure_as_zero_fixed_denominator": True,
            "retry_resume_skip_replacement_or_selective_rerun": False,
            "protected_watchers": watcher_snapshot(),
        },
        "model": copy.deepcopy(MODEL),
        "search": copy.deepcopy(SEARCH),
        "logical_parent_limits": copy.deepcopy(LIMITS),
        "truthful_physical_caps": copy.deepcopy(PHYSICAL_CAPS),
        "source_policy": source_policy(),
        "reliability_gate": reliability_gate(),
        "authorization": {
            "preactivation_audit_generation": True,
            "external_forward": False,
            "candidate_quality_or_prediction_change_claim": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    return seal(value, "protocol_payload_sha256")


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    source_manifest = copied.get("source_manifest")
    tasks = task_vector(root)
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "protocol_id",
            "created_at_unix",
            "parents",
            "source_manifest",
            "population",
            "execution",
            "model",
            "search",
            "logical_parent_limits",
            "truthful_physical_caps",
            "source_policy",
            "reliability_gate",
            "authorization",
            "protocol_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25280_paired_checkpoint_reliability_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied.get("parents")
        != {
            str(POPULATION): POPULATION_SHA256,
            str(POPULATION_AUDIT): POPULATION_AUDIT_SHA256,
            str(RUNTIME_BUILD_AUDIT): RUNTIME_BUILD_AUDIT_SHA256,
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
        or copied.get("population")
        != {
            "task_count": TASK_COUNT,
            "task_vector_sha256": payload_sha256(tasks),
            "opaque_id_vector_sha256": payload_sha256(
                [row["opaque_id"] for row in tasks]
            ),
            "question_vector_sha256": payload_sha256(
                [row["question"] for row in tasks]
            ),
            "runtime_keys": ["opaque_id", "question"],
        }
        or copied.get("execution")
        != {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "single_cold_forward": True,
            "one_real_forward_per_task": True,
            "candidate_local_projection_only": True,
            "failure_as_zero_fixed_denominator": True,
            "retry_resume_skip_replacement_or_selective_rerun": False,
            "protected_watchers": watcher_snapshot(),
        }
        or copied.get("model") != MODEL
        or copied.get("search") != SEARCH
        or copied.get("logical_parent_limits") != LIMITS
        or copied.get("truthful_physical_caps") != PHYSICAL_CAPS
        or copied.get("source_policy") != source_policy()
        or copied.get("reliability_gate") != reliability_gate()
        or copied.get("authorization")
        != {
            "preactivation_audit_generation": True,
            "external_forward": False,
            "candidate_quality_or_prediction_change_claim": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or not sealed(copied, "protocol_payload_sha256")
    ):
        raise ValueError("V2.52.80 paired checkpoint protocol drifted")
    return copied


__all__ = [
    "ATTEMPT_CLAIM",
    "BUILD_AUDIT",
    "CLEANUP_RESERVE_SECONDS",
    "COLUMNS",
    "CONTRACT",
    "CONTROL",
    "DATE",
    "EXECUTION_START",
    "EXECUTOR_CONCURRENCY",
    "FORWARD_AUDIT",
    "FORWARD_RESULT",
    "LEASE_OWNER",
    "LEASE_PATH",
    "LEASE_PURPOSE",
    "LIMITS",
    "MINIMUM_MODEL_ATTEMPT_SECONDS",
    "MODEL",
    "MODEL_SLOT_CAP",
    "MODEL_SLOT_DIRECTORY",
    "OPAQUE_ID_VECTOR_SHA256",
    "OUTPUT_ROOT",
    "PHYSICAL_CAPS",
    "POPULATION",
    "POPULATION_AUDIT",
    "POPULATION_AUDIT_SHA256",
    "POPULATION_SHA256",
    "PREAUDIT",
    "PREDICTION_FREEZE",
    "PROTECTED_WATCHERS",
    "PROTOCOL",
    "PROTOCOL_ID",
    "QUESTION_VECTOR_SHA256",
    "ROLE",
    "RUNNER",
    "RUNTIME_BUILD_AUDIT",
    "RUNTIME_BUILD_AUDIT_SHA256",
    "SAFE_PROGRESS",
    "SEARCH",
    "TASK_COUNT",
    "TASK_ROWS",
    "TASK_VECTOR_SHA256",
    "TEST",
    "build_protocol",
    "git",
    "ordinary",
    "packages_from_question",
    "payload_sha256",
    "reliability_gate",
    "runtime",
    "seal",
    "sealed",
    "sha256",
    "source_policy",
    "task_vector",
    "validate_protocol",
    "validate_task_vector",
    "watcher_snapshot",
]
