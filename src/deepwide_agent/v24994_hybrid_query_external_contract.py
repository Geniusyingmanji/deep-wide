"""Preregistered paired hybrid-query external mechanism and quality gate."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v24831_keyless_exact220_contract as production
from . import v24983_late_page_external_contract as prior83
from . import v24991_short_query_external_contract as prior91
from . import v24993_hybrid_query_paired_runtime as runtime
from .v24799_fixed_full_budget_control import POLICY_VALUES


DATE = "20260809"
PROTOCOL_ID = "v24994_paired_provider_anchor_hybrid_query_external_gate_v1"
BUILD_AUDIT = Path(f"results/v24994_hybrid_query_external_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v24994_hybrid_query_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24994_hybrid_query_external_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24994_hybrid_query_external_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24994_hybrid_query_external_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24994_hybrid_query_external_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(f"results/v24994_hybrid_query_external_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v24994_hybrid_query_external_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24994_hybrid_query_external_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24994_hybrid_query_external_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_RESULTS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
POSTFREEZE_GOLD = OUTPUT_ROOT / "postfreeze_iana_gold.json"
LEASE_PATH = production.LEASE_PATH
LEASE_OWNER = "v24994_hybrid_query_external_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_paired_hybrid_query_external_gate"

SOURCE = Path("src/deepwide_agent/v24994_hybrid_query_external_contract.py")
HISTORICAL_COHORT_SOURCE = Path(
    "src/deepwide_agent/v24991_short_query_external_contract.py"
)
PROJECTOR = Path("src/deepwide_agent/v24984_robust_late_page_projection.py")
FETCH = Path("src/deepwide_agent/v24985_robust_late_page_fetch.py")
HYBRID_QUERY = Path("src/deepwide_agent/v24992_hybrid_authority_queries.py")
RUNTIME = Path("src/deepwide_agent/v24993_hybrid_query_paired_runtime.py")
HELPER = Path("scripts/run_v24985_robust_late_page_fetch_helper.py")
CONTROL = Path("scripts/control_v24994_hybrid_query_external.py")
RUNNER = Path("scripts/run_v24994_hybrid_query_external.py")
EVALUATOR = Path("scripts/evaluate_v24994_hybrid_query_external.py")
TEST = Path("tests/test_v24994_hybrid_query_external.py")
PROJECTOR_TEST = Path("tests/test_v24984_robust_late_page_projection.py")
FETCH_TEST = Path("tests/test_v24985_robust_late_page_fetch.py")
HYBRID_QUERY_TEST = Path("tests/test_v24992_hybrid_authority_queries.py")
RUNTIME_TEST = Path("tests/test_v24993_hybrid_query_paired_runtime.py")
LOCAL_SOURCES = (
    SOURCE,
    HISTORICAL_COHORT_SOURCE,
    PROJECTOR,
    FETCH,
    HYBRID_QUERY,
    RUNTIME,
    HELPER,
    CONTROL,
    RUNNER,
    EVALUATOR,
    TEST,
    PROJECTOR_TEST,
    FETCH_TEST,
    HYBRID_QUERY_TEST,
    RUNTIME_TEST,
)

TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 8
LIMITS = copy.deepcopy(production.LIMITS)
MODEL = copy.deepcopy(production.MODEL)
SEARCH = copy.deepcopy(production.SEARCH)
TWO_WAVE_POLICY = copy.deepcopy(POLICY_VALUES)
ARMS = runtime.ARMS
CONTROL_ARM = runtime.CONTROL_ARM
CANDIDATE_ARM = runtime.CANDIDATE_ARM
PROTECTED_WATCHERS = production.PROTECTED_WATCHERS
IANA_URL = prior83.IANA_URL
COLUMNS = prior83.COLUMNS
MAX_GOLD_BYTES = prior83.MAX_GOLD_BYTES
TLD_COHORT = (
    ".ch", ".ci", ".ck", ".cl", ".cm", ".cn", ".co", ".cr", ".cu", ".cv",
    ".cw", ".cx", ".cy", ".cz", ".de", ".dj", ".dk", ".dm", ".do", ".dz",
)
HISTORICAL_TLD_COHORT = frozenset(
    (*prior91.HISTORICAL_TLD_COHORT, *prior91.TLD_COHORT)
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
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


def seal(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    copied.pop(field, None)
    copied[field] = payload_sha256(copied)
    return copied


def sealed(value: Mapping[str, Any], field: str) -> bool:
    copied = copy.deepcopy(dict(value))
    observed = copied.pop(field, None)
    return isinstance(observed, str) and observed == payload_sha256(copied)


def watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    return production.protected_watcher_snapshot(proc_root)


def task_vector() -> list[dict[str, str]]:
    if (
        len(TLD_COHORT) != TASK_COUNT
        or len(set(TLD_COHORT)) != TASK_COUNT
        or set(TLD_COHORT).intersection(HISTORICAL_TLD_COHORT)
    ):
        raise RuntimeError("V2.49.94 fresh TLD population drifted")
    values: list[dict[str, str]] = []
    for tld in TLD_COHORT:
        opaque = "task_" + hashlib.sha256(f"v24994:{tld}".encode()).hexdigest()[:24]
        question = (
            "Use web search and the official IANA Root Zone Database public page to "
            "return exactly one Markdown table and no prose. Include exactly one row "
            f"for the visible domain identity <DOMAIN>{tld}</DOMAIN>. "
            "Column names: Domain, Type, TLD Manager. Preserve the exact domain spelling "
            "shown above. The Type and TLD Manager must come from the same official "
            "IANA table record. Use Unknown only if the fetched official page does not "
            "establish the value."
        )
        values.append({"opaque_id": opaque, "question": question})
    return validate_task_vector(values)


def validate_task_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.49.94 task denominator drifted")
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for value, tld in zip(values, TLD_COHORT, strict=True):
        if not isinstance(value, Mapping) or set(value) != {"opaque_id", "question"}:
            raise ValueError("V2.49.94 runtime input must be opaque_id and question")
        opaque = value.get("opaque_id")
        question = value.get("question")
        if (
            not isinstance(opaque, str)
            or len(opaque) != 29
            or not opaque.startswith("task_")
            or opaque in seen
            or not isinstance(question, str)
            or f"<DOMAIN>{tld}</DOMAIN>" not in question
            or any(column not in question for column in COLUMNS)
            or IANA_URL in question
        ):
            raise ValueError("V2.49.94 visible task binding drifted")
        seen.add(opaque)
        output.append({"opaque_id": opaque, "question": question})
    return output


def arm_order_vector() -> list[list[str]]:
    tasks = task_vector()
    ranked = sorted(
        range(TASK_COUNT),
        key=lambda index: hashlib.sha256(
            f"v24994-arm-order:{tasks[index]['opaque_id']}".encode()
        ).hexdigest(),
    )
    candidate_first = set(ranked[: TASK_COUNT // 2])
    return [
        [CANDIDATE_ARM, CONTROL_ARM]
        if index in candidate_first
        else [CONTROL_ARM, CANDIDATE_ARM]
        for index in range(TASK_COUNT)
    ]


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "fresh_population_disjoint_from_all_prior_tld_cohorts": True,
        "final_iana_url_or_population_probed_before_protocol_freeze": False,
        "one_shared_visible_only_planning_call": True,
        "control_uses_legacy_visible_query_completion": True,
        "candidate_preserves_provider_anchor_and_replaces_only_other_three": True,
        "candidate_uses_visible_tagged_identity_authority_and_schema_only": True,
        "independent_equal_per_arm_retrieval_budgets": True,
        "per_arm_query_fetch_caps": {"queries": 4, "fetches": 10},
        "external_gate_total_retrieval_budget_doubles_production": True,
        "external_gate_not_a_production_latency_or_throughput_measurement": True,
        "same_robust_compact_projector_and_evidence_renderer": True,
        "same_columns_prompt_model_output_cap_and_task_deadline": True,
        "retrieval_and_synthesis_order_balanced_before_outcomes": True,
        "action_source_and_page_volume_are_diagnostics_not_gate_targets": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
        "prediction_freeze_before_gold_fetch_or_quality_decision": True,
        "entropy_or_information_gain_assigns_credit_or_routes": False,
        "public_deepwidebench_exact220_launch_authorized": False,
    }


def mechanism_gate() -> dict[str, Any]:
    return {
        "terminal_tasks": 20,
        "hybrid_query_strategy_applied_tasks": 20,
        "provider_anchor_preserved_tasks": 20,
        "first_explicit_authority_phrase_selected_tasks": 20,
        "query_vector_changed_tasks": 20,
        "minimum_both_arms_model_success_tasks": 18,
        "all_task_evidence_character_counts_equal_between_arms": True,
        "completed_task_model_calls_at_most_three": True,
        "all_tasks_plan_exactly_four_queries_per_arm": True,
        "all_tasks_execute_exactly_four_queries_per_arm": True,
        "executed_arm_order_matches_frozen_vector": True,
        "candidate_total_query_local_results_nonregression": True,
        "minimum_tasks_with_candidate_query_local_result_advantage": 4,
        "minimum_candidate_retained_records": 4,
        "candidate_total_retained_records_nonregression": True,
        "minimum_tasks_with_candidate_record_advantage": 4,
        "minimum_prediction_changed_tasks": 4,
        "query_cap_per_arm_per_task": 4,
        "fetch_cap_per_arm_per_task": 10,
    }


def quality_gate() -> dict[str, Any]:
    return {
        "fixed_denominator": TASK_COUNT,
        "candidate_exact_strictly_greater": True,
        "entity_row_item_column_composite_nonregression": True,
        "invalid_or_fallback_nonincrease": True,
    }


def dependency_manifest(root: Path, *, tracked: bool = True) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in LOCAL_SOURCES:
        path = root / relative
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or path.is_symlink()
            or not path.is_file()
        ):
            raise RuntimeError("V2.49.94 source manifest path drifted")
        if tracked and subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode != 0:
            raise RuntimeError("V2.49.94 source is not tracked")
        output[str(relative)] = sha256(path)
    return output


def _protocol(root: Path, *, now: int, tracked: bool) -> dict[str, Any]:
    tasks = task_vector()
    manifest = dependency_manifest(root, tracked=tracked)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24994_hybrid_query_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "git_head": git(root, "rev-parse", "HEAD"),
        "population": {
            "selected_tasks": TASK_COUNT,
            "opaque_id_vector_sha256": payload_sha256(
                [task["opaque_id"] for task in tasks]
            ),
            "visible_question_vector_sha256": payload_sha256(
                [task["question"] for task in tasks]
            ),
            "task_vector_sha256": payload_sha256(tasks),
            "tld_vector_sha256": payload_sha256(TLD_COHORT),
            "arm_order_vector_sha256": payload_sha256(arm_order_vector()),
            "disjoint_from_all_prior_tld_cohorts": not bool(
                set(TLD_COHORT).intersection(HISTORICAL_TLD_COHORT)
            ),
            "official_gold_endpoint_sha256": payload_sha256(IANA_URL),
            "final_population_url_or_page_probed_before_protocol_freeze": False,
        },
        "execution": {
            "output_root": str(OUTPUT_ROOT),
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "limits_per_arm": copy.deepcopy(LIMITS),
            "two_wave_policy_per_arm": copy.deepcopy(TWO_WAVE_POLICY),
            "protected_watchers": watcher_snapshot(),
            "single_atomic_forward_no_retry_resume_or_selective_rerun": True,
        },
        "mechanism_gate_before_evaluator": mechanism_gate(),
        "quality_gate": quality_gate(),
        "source_policy": source_policy(),
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "authorization": {
            "preactivation_audit_generation": True,
            "one_external_forward": False,
            "postfreeze_evaluator": False,
            "public_exact220_launch": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(root, value, tracked=tracked)


def build_protocol(root: Path, *, now: int) -> dict[str, Any]:
    return _protocol(root, now=now, tracked=True)


def validate_protocol(
    root: Path, value: Mapping[str, Any], *, tracked: bool = True
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal_value = unsigned.pop("protocol_payload_sha256", None)
    population = copied.get("population")
    execution = copied.get("execution")
    authorization = copied.get("authorization")
    expected = {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "git_head",
        "population",
        "execution",
        "mechanism_gate_before_evaluator",
        "quality_gate",
        "source_policy",
        "dependency_manifest",
        "dependency_manifest_sha256",
        "authorization",
        "protocol_payload_sha256",
    }
    population_expected = {
        "selected_tasks",
        "opaque_id_vector_sha256",
        "visible_question_vector_sha256",
        "task_vector_sha256",
        "tld_vector_sha256",
        "arm_order_vector_sha256",
        "disjoint_from_all_prior_tld_cohorts",
        "official_gold_endpoint_sha256",
        "final_population_url_or_page_probed_before_protocol_freeze",
    }
    execution_expected = {
        "output_root",
        "executor_concurrency",
        "model_slot_cap",
        "model",
        "search",
        "limits_per_arm",
        "two_wave_policy_per_arm",
        "protected_watchers",
        "single_atomic_forward_no_retry_resume_or_selective_rerun",
    }
    authorization_expected = {
        "preactivation_audit_generation",
        "one_external_forward",
        "postfreeze_evaluator",
        "public_exact220_launch",
        "leaderboard_or_sota",
    }
    tasks = task_vector()
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v24994_hybrid_query_external_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not isinstance(copied.get("created_at_unix"), int)
        or not isinstance(copied.get("git_head"), str)
        or len(copied["git_head"]) != 40
        or not isinstance(population, Mapping)
        or set(population) != population_expected
        or population.get("selected_tasks") != TASK_COUNT
        or population.get("opaque_id_vector_sha256")
        != payload_sha256([task["opaque_id"] for task in tasks])
        or population.get("visible_question_vector_sha256")
        != payload_sha256([task["question"] for task in tasks])
        or population.get("task_vector_sha256") != payload_sha256(tasks)
        or population.get("tld_vector_sha256") != payload_sha256(TLD_COHORT)
        or population.get("arm_order_vector_sha256")
        != payload_sha256(arm_order_vector())
        or population.get("disjoint_from_all_prior_tld_cohorts") is not True
        or population.get("official_gold_endpoint_sha256")
        != payload_sha256(IANA_URL)
        or population.get("final_population_url_or_page_probed_before_protocol_freeze")
        is not False
        or not isinstance(execution, Mapping)
        or set(execution) != execution_expected
        or execution.get("output_root") != str(OUTPUT_ROOT)
        or execution.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or execution.get("model_slot_cap") != MODEL_SLOT_CAP
        or execution.get("limits_per_arm") != LIMITS
        or execution.get("model") != MODEL
        or execution.get("search") != SEARCH
        or execution.get("two_wave_policy_per_arm") != TWO_WAVE_POLICY
        or execution.get("protected_watchers") != watcher_snapshot()
        or execution.get("single_atomic_forward_no_retry_resume_or_selective_rerun")
        is not True
        or copied.get("mechanism_gate_before_evaluator") != mechanism_gate()
        or copied.get("quality_gate") != quality_gate()
        or copied.get("source_policy") != source_policy()
        or copied.get("dependency_manifest")
        != dependency_manifest(root, tracked=tracked)
        or copied.get("dependency_manifest_sha256")
        != payload_sha256(copied["dependency_manifest"])
        or not isinstance(authorization, Mapping)
        or set(authorization) != authorization_expected
        or authorization.get("preactivation_audit_generation") is not True
        or authorization.get("one_external_forward") is not False
        or authorization.get("postfreeze_evaluator") is not False
        or authorization.get("public_exact220_launch") is not False
        or authorization.get("leaderboard_or_sota") is not False
        or seal_value != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.94 protocol drifted")
    return copied


__all__ = [
    "ARMS", "BUILD_AUDIT", "CANDIDATE_ARM", "CONTROL_ARM", "EXECUTION_START",
    "EVALUATOR", "EVALUATOR_PROTOCOL", "FORWARD_AUDIT", "FORWARD_RESULT",
    "HISTORICAL_TLD_COHORT", "HYBRID_QUERY", "MODEL_SLOT_DIRECTORY",
    "OUTPUT_ROOT", "POSTFREEZE_GOLD", "POSTAUDIT",
    "PREAUDIT", "PREDICTION_FREEZE", "PROTOCOL", "PROTOCOL_ID", "RESULT",
    "TASK_RESULTS", "TLD_COHORT", "arm_order_vector", "build_protocol",
    "dependency_manifest", "git", "mechanism_gate", "payload_sha256",
    "quality_gate", "seal", "sealed", "sha256", "source_policy", "task_vector",
    "validate_protocol", "validate_task_vector", "watcher_snapshot",
]
