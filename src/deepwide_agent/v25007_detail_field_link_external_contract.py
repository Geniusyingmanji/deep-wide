"""Preregistered identity-bound detail-field link external gate."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v24831_keyless_exact220_contract as production
from . import v25003_page_visible_link_external_contract as prior03
from . import v25006_detail_field_link_runtime as runtime


DATE = "20260809"
PROTOCOL_ID = "v25007_detail_field_page_visible_link_external_gate_v1"
BUILD_AUDIT = Path(f"results/v25007_detail_field_link_external_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25007_detail_field_link_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25007_detail_field_link_external_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25007_detail_field_link_external_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25007_detail_field_link_external_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25007_detail_field_link_external_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(f"results/v25007_detail_field_link_external_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v25007_detail_field_link_external_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v25007_detail_field_link_external_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v25007_detail_field_link_external_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_RESULTS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
POSTFREEZE_GOLD = OUTPUT_ROOT / "postfreeze_iana_detail_gold.json"
LEASE_PATH = production.LEASE_PATH
LEASE_OWNER = "v25007_detail_field_link_external_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_identity_bound_detail_field_link_gate"

SOURCE = Path("src/deepwide_agent/v25007_detail_field_link_external_contract.py")
HISTORICAL_COHORT_SOURCE = Path(
    "src/deepwide_agent/v25003_page_visible_link_external_contract.py"
)
PARENT_PROJECTOR = Path("src/deepwide_agent/v24980_late_page_bound_projection.py")
ROBUST_PROJECTOR = Path("src/deepwide_agent/v24984_robust_late_page_projection.py")
PROJECTOR = Path("src/deepwide_agent/v25004_identity_bound_detail_fields.py")
PARENT_FETCH = Path("src/deepwide_agent/v24981_late_page_bound_fetch.py")
ROBUST_FETCH = Path("src/deepwide_agent/v24985_robust_late_page_fetch.py")
FETCH = Path("src/deepwide_agent/v25005_detail_field_fetch.py")
PARENT_SELECTOR = Path("src/deepwide_agent/v24998_identity_authority_action_selection.py")
PARENT_RUNTIME = Path("src/deepwide_agent/v24999_shared_response_selection_runtime.py")
SELECTOR = Path("src/deepwide_agent/v25001_page_visible_link_selection.py")
LINK_RUNTIME = Path("src/deepwide_agent/v25002_page_visible_link_paired_runtime.py")
RUNTIME = Path("src/deepwide_agent/v25006_detail_field_link_runtime.py")
HELPER = Path("scripts/run_v25005_detail_field_fetch_helper.py")
CONTROL = Path("scripts/control_v25007_detail_field_link_external.py")
RUNNER = Path("scripts/run_v25007_detail_field_link_external.py")
EVALUATOR = Path("scripts/evaluate_v25007_detail_field_link_external.py")
TEST = Path("tests/test_v25007_detail_field_link_external.py")
TEST_SOURCES = (
    Path("tests/test_v24980_late_page_bound_projection.py"),
    Path("tests/test_v24981_late_page_bound_fetch.py"),
    Path("tests/test_v24984_robust_late_page_projection.py"),
    Path("tests/test_v24985_robust_late_page_fetch.py"),
    Path("tests/test_v24998_identity_authority_action_selection.py"),
    Path("tests/test_v24999_shared_response_selection_runtime.py"),
    Path("tests/test_v25001_page_visible_link_selection.py"),
    Path("tests/test_v25002_page_visible_link_paired_runtime.py"),
    Path("tests/test_v25004_identity_bound_detail_fields.py"),
    Path("tests/test_v25005_detail_field_fetch.py"),
    Path("tests/test_v25006_detail_field_link_runtime.py"),
    Path("tests/test_native_search.py"),
    Path("tests/test_v24286_visible_schema_runtime.py"),
    Path("tests/test_v24259_deterministic_table_normalizer.py"),
)
LOCAL_SOURCES = (
    SOURCE, HISTORICAL_COHORT_SOURCE, PARENT_PROJECTOR, ROBUST_PROJECTOR,
    PROJECTOR, PARENT_FETCH, ROBUST_FETCH, FETCH, PARENT_SELECTOR,
    PARENT_RUNTIME, SELECTOR, LINK_RUNTIME, RUNTIME, HELPER, CONTROL, RUNNER,
    EVALUATOR, TEST, *TEST_SOURCES,
)

TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 8
LIMITS = copy.deepcopy(production.LIMITS)
MODEL = copy.deepcopy(production.MODEL)
SEARCH = copy.deepcopy(production.SEARCH)
ARMS = runtime.ARMS
CONTROL_ARM = runtime.CONTROL_ARM
CANDIDATE_ARM = runtime.CANDIDATE_ARM
PHASES = runtime.PHASES
PROTECTED_WATCHERS = production.PROTECTED_WATCHERS
COLUMNS = (
    "Domain", "Sponsoring Organisation", "Registration date",
    "Record last updated",
)
IANA_DETAIL_PREFIX = "https://www.iana.org/domains/root/db/"
MAX_GOLD_BYTES_PER_PAGE = 1_000_000
TLD_COHORT = (
    ".aero", ".aetna", ".afl", ".africa", ".agakhan", ".agency", ".aig",
    ".airbus", ".airforce", ".airtel", ".akdn", ".alfaromeo", ".alibaba",
    ".alipay", ".allfinanz", ".allstate", ".ally", ".alsace", ".alstom",
    ".amazon",
)
HISTORICAL_TLD_COHORT = frozenset(
    (*prior03.HISTORICAL_TLD_COHORT, *prior03.TLD_COHORT)
)


def detail_url(tld: str) -> str:
    if tld not in TLD_COHORT:
        raise ValueError("V2.50.07 detail identity is outside frozen cohort")
    return IANA_DETAIL_PREFIX + tld.removeprefix(".") + ".html"


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20,
        check=True,
    ).stdout.strip()


def seal(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value)); copied.pop(field, None)
    copied[field] = payload_sha256(copied)
    return copied


def sealed(value: Mapping[str, Any], field: str) -> bool:
    copied = copy.deepcopy(dict(value)); observed = copied.pop(field, None)
    return isinstance(observed, str) and observed == payload_sha256(copied)


def watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    return production.protected_watcher_snapshot(proc_root)


def task_vector() -> list[dict[str, str]]:
    if (
        len(TLD_COHORT) != TASK_COUNT
        or len(set(TLD_COHORT)) != TASK_COUNT
        or set(TLD_COHORT).intersection(HISTORICAL_TLD_COHORT)
    ):
        raise RuntimeError("V2.50.07 fresh TLD population drifted")
    values: list[dict[str, str]] = []
    for tld in TLD_COHORT:
        opaque = "task_" + hashlib.sha256(f"v25007:{tld}".encode()).hexdigest()[:24]
        question = (
            "Use web search and the official IANA Root Zone Database public page to "
            "return exactly one Markdown table and no prose. Include exactly one row "
            f"for the visible domain identity <DOMAIN>{tld}</DOMAIN>. Column names: "
            "Domain, Sponsoring Organisation, Registration date, Record last updated. "
            "Preserve the exact domain spelling shown above. All three target fields "
            "must come from the same official IANA detail record. Use Unknown only if "
            "the fetched official detail page does not establish the value."
        )
        values.append({"opaque_id": opaque, "question": question})
    return validate_task_vector(values)


def validate_task_vector(values: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.50.07 task denominator drifted")
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for value, tld in zip(values, TLD_COHORT, strict=True):
        if not isinstance(value, Mapping) or set(value) != {"opaque_id", "question"}:
            raise ValueError("V2.50.07 runtime input must be opaque_id and question")
        opaque, question = value.get("opaque_id"), value.get("question")
        if (
            not isinstance(opaque, str) or len(opaque) != 29
            or not opaque.startswith("task_") or opaque in seen
            or not isinstance(question, str) or f"<DOMAIN>{tld}</DOMAIN>" not in question
            or any(column not in question for column in COLUMNS)
            or IANA_DETAIL_PREFIX in question or detail_url(tld) in question
        ):
            raise ValueError("V2.50.07 visible task binding drifted")
        seen.add(opaque); output.append({"opaque_id": opaque, "question": question})
    return output


def arm_order_vector() -> list[list[str]]:
    tasks = task_vector()
    ranked = sorted(
        range(TASK_COUNT),
        key=lambda index: hashlib.sha256(
            f"v25007-arm-order:{tasks[index]['opaque_id']}".encode()
        ).hexdigest(),
    )
    candidate_first = set(ranked[: TASK_COUNT // 2])
    return [
        [CANDIDATE_ARM, CONTROL_ARM] if index in candidate_first
        else [CONTROL_ARM, CANDIDATE_ARM]
        for index in range(TASK_COUNT)
    ]


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "fresh_population_disjoint_from_all_prior_tld_cohorts": True,
        "final_population_url_or_page_probed_before_protocol_freeze": False,
        "population_selected_by_public_namespace_order_after_v25003_only": True,
        "one_visible_only_planning_call": True,
        "same_completed_legacy_query_vector_for_both_arms": True,
        "one_physical_first_wave_pages_and_visible_link_vectors_reused_by_both_arms": True,
        "one_physical_second_wave_search_response_reused_by_both_arms": True,
        "completed_search_prefix_identical_and_non_displaceable": True,
        "candidate_reorders_only_visible_links_by_exact_identity_authority_binding": True,
        "detail_projector_requires_exact_url_page_identity_authority_and_all_fields": True,
        "detail_projector_supports_exact_key_value_heading_or_sentence_grammar": True,
        "two_arm_full_second_wave_url_union_fetched_once": True,
        "page_text_partitioned_by_selected_canonical_url": True,
        "per_arm_logical_query_fetch_caps": {"queries": 4, "fetches": 10},
        "paired_physical_query_fetch_caps": {"queries": 4, "fetches": 14},
        "same_evidence_renderer_columns_prompt_model_output_and_deadline": True,
        "external_gate_not_production_latency_or_throughput": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
        "prediction_freeze_before_gold_fetch_or_quality_decision": True,
        "entropy_or_information_gain_assigns_credit_or_routes": False,
        "public_deepwidebench_exact220_launch_authorized": False,
    }


def mechanism_gate() -> dict[str, Any]:
    return {
        "terminal_tasks": TASK_COUNT,
        "minimum_visible_link_strategy_eligible_tasks": 8,
        "shared_first_wave_completed_tasks": TASK_COUNT,
        "shared_second_wave_completed_tasks": TASK_COUNT,
        "all_tasks_execute_exactly_four_physical_queries": True,
        "all_tasks_fetch_at_most_fourteen_physical_pages": True,
        "minimum_both_arms_model_success_tasks": 18,
        "all_task_evidence_character_counts_equal_between_arms": True,
        "completed_task_model_calls_at_most_three": True,
        "all_tasks_plan_exactly_four_queries_per_arm": True,
        "all_tasks_execute_exactly_four_queries_per_arm": True,
        "executed_arm_order_matches_frozen_vector": True,
        "minimum_selection_changed_tasks": 8,
        "minimum_total_bound_visible_link_gain": 8,
        "minimum_tasks_with_positive_bound_visible_link_gain": 8,
        "candidate_total_target_bound_projected_pages_strict_gain": True,
        "minimum_tasks_with_positive_target_bound_projected_page_gain": 6,
        "candidate_total_target_bound_records_strict_gain": True,
        "minimum_tasks_with_positive_target_bound_record_gain": 6,
        "minimum_target_bound_record_mechanism_engaged_tasks": 6,
        "minimum_prediction_changed_tasks": 4,
        "query_cap_per_arm_per_task": 4,
        "fetch_cap_per_arm_per_task": 10,
        "physical_query_cap_per_task": 4,
        "physical_fetch_cap_per_task": 14,
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
        if relative.is_absolute() or ".." in relative.parts or path.is_symlink() or not path.is_file():
            raise RuntimeError("V2.50.07 source manifest path drifted")
        if tracked and subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)], cwd=root,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=20, check=False,
        ).returncode != 0:
            raise RuntimeError("V2.50.07 source is not tracked")
        output[str(relative)] = sha256(path)
    return output


def _protocol(root: Path, *, now: int, tracked: bool) -> dict[str, Any]:
    tasks = task_vector(); manifest = dependency_manifest(root, tracked=tracked)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25007_detail_field_link_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "git_head": git(root, "rev-parse", "HEAD"),
        "population": {
            "selected_tasks": TASK_COUNT,
            "opaque_id_vector_sha256": payload_sha256([task["opaque_id"] for task in tasks]),
            "visible_question_vector_sha256": payload_sha256([task["question"] for task in tasks]),
            "task_vector_sha256": payload_sha256(tasks),
            "tld_vector_sha256": payload_sha256(TLD_COHORT),
            "arm_order_vector_sha256": payload_sha256(arm_order_vector()),
            "disjoint_from_all_prior_tld_cohorts": not bool(set(TLD_COHORT) & HISTORICAL_TLD_COHORT),
            "selection_basis": "next_twenty_alphabetic_unseen_iana_identities_after_v25003_within_frozen_256_link_bound",
            "official_detail_endpoint_vector_sha256": payload_sha256([detail_url(tld) for tld in TLD_COHORT]),
            "final_population_url_or_page_probed_before_protocol_freeze": False,
        },
        "execution": {
            "output_root": str(OUTPUT_ROOT), "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP, "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH), "limits_per_arm": copy.deepcopy(LIMITS),
            "protected_watchers": watcher_snapshot(),
            "single_atomic_forward_no_retry_resume_or_selective_rerun": True,
        },
        "mechanism_gate_before_evaluator": mechanism_gate(),
        "quality_gate": quality_gate(), "source_policy": source_policy(),
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "authorization": {
            "preactivation_audit_generation": True, "one_external_forward": False,
            "postfreeze_evaluator": False, "public_exact220_launch": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(root, value, tracked=tracked)


def build_protocol(root: Path, *, now: int) -> dict[str, Any]:
    return _protocol(root, now=now, tracked=True)


def validate_protocol(root: Path, value: Mapping[str, Any], *, tracked: bool = True) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value)); unsigned = dict(copied)
    seal_value = unsigned.pop("protocol_payload_sha256", None)
    population, execution, authorization = copied.get("population"), copied.get("execution"), copied.get("authorization")
    tasks = task_vector()
    if (
        set(copied) != {
            "artifact_version", "role", "protocol_id", "created_at_unix", "git_head",
            "population", "execution", "mechanism_gate_before_evaluator", "quality_gate",
            "source_policy", "dependency_manifest", "dependency_manifest_sha256",
            "authorization", "protocol_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25007_detail_field_link_external_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not isinstance(copied.get("created_at_unix"), int)
        or not isinstance(copied.get("git_head"), str) or len(copied["git_head"]) != 40
        or not isinstance(population, Mapping)
        or set(population) != {
            "selected_tasks", "opaque_id_vector_sha256", "visible_question_vector_sha256",
            "task_vector_sha256", "tld_vector_sha256", "arm_order_vector_sha256",
            "disjoint_from_all_prior_tld_cohorts", "selection_basis",
            "official_detail_endpoint_vector_sha256",
            "final_population_url_or_page_probed_before_protocol_freeze",
        }
        or population.get("selected_tasks") != TASK_COUNT
        or population.get("opaque_id_vector_sha256") != payload_sha256([task["opaque_id"] for task in tasks])
        or population.get("visible_question_vector_sha256") != payload_sha256([task["question"] for task in tasks])
        or population.get("task_vector_sha256") != payload_sha256(tasks)
        or population.get("tld_vector_sha256") != payload_sha256(TLD_COHORT)
        or population.get("arm_order_vector_sha256") != payload_sha256(arm_order_vector())
        or population.get("disjoint_from_all_prior_tld_cohorts") is not True
        or population.get("selection_basis") != "next_twenty_alphabetic_unseen_iana_identities_after_v25003_within_frozen_256_link_bound"
        or population.get("official_detail_endpoint_vector_sha256") != payload_sha256([detail_url(tld) for tld in TLD_COHORT])
        or population.get("final_population_url_or_page_probed_before_protocol_freeze") is not False
        or not isinstance(execution, Mapping)
        or set(execution) != {
            "output_root", "executor_concurrency", "model_slot_cap", "model", "search",
            "limits_per_arm", "protected_watchers", "single_atomic_forward_no_retry_resume_or_selective_rerun",
        }
        or execution.get("output_root") != str(OUTPUT_ROOT)
        or execution.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or execution.get("model_slot_cap") != MODEL_SLOT_CAP
        or execution.get("limits_per_arm") != LIMITS or execution.get("model") != MODEL
        or execution.get("search") != SEARCH or execution.get("protected_watchers") != watcher_snapshot()
        or execution.get("single_atomic_forward_no_retry_resume_or_selective_rerun") is not True
        or copied.get("mechanism_gate_before_evaluator") != mechanism_gate()
        or copied.get("quality_gate") != quality_gate() or copied.get("source_policy") != source_policy()
        or copied.get("dependency_manifest") != dependency_manifest(root, tracked=tracked)
        or copied.get("dependency_manifest_sha256") != payload_sha256(copied["dependency_manifest"])
        or not isinstance(authorization, Mapping)
        or authorization != {
            "preactivation_audit_generation": True, "one_external_forward": False,
            "postfreeze_evaluator": False, "public_exact220_launch": False,
            "leaderboard_or_sota": False,
        }
        or seal_value != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.07 protocol drifted")
    return copied


__all__ = [
    "ARMS", "BUILD_AUDIT", "CANDIDATE_ARM", "COLUMNS", "CONTROL_ARM",
    "EVALUATOR", "EVALUATOR_PROTOCOL", "EXECUTION_START", "FORWARD_AUDIT",
    "FORWARD_RESULT", "HISTORICAL_TLD_COHORT", "LEASE_OWNER", "LEASE_PATH",
    "LEASE_PURPOSE", "LOCAL_SOURCES", "MAX_GOLD_BYTES_PER_PAGE", "MODEL_SLOT_CAP",
    "MODEL_SLOT_DIRECTORY", "OUTPUT_ROOT", "PHASES", "POSTAUDIT", "POSTFREEZE_GOLD",
    "PREAUDIT", "PREDICTION_FREEZE", "PROTOCOL", "PROTOCOL_ID", "RESULT",
    "RUNNER", "TASK_COUNT", "TASK_RESULTS", "TEST_SOURCES", "TLD_COHORT",
    "arm_order_vector", "build_protocol", "dependency_manifest", "detail_url",
    "git", "mechanism_gate", "payload_sha256", "quality_gate", "seal", "sealed",
    "sha256", "source_policy", "task_vector", "validate_protocol",
    "validate_task_vector", "watcher_snapshot",
]
