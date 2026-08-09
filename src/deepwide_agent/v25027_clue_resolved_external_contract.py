"""Preregistered clue-resolved evidence-conditioned external gate.

The forward population exposes only capital/currency clues and the requested
IANA table schema.  Country names, ccTLD identities, and gold rows live in a
separate evaluator-only module that is not a forward dependency and remains
unopened until predictions and the content-free mechanism audit are frozen.
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v24831_keyless_exact220_contract as production
from . import v25025_evidence_conditioned_paired_runtime as runtime


DATE = "20260809"
PROTOCOL_ID = "v25027_clue_resolved_evidence_conditioned_external_gate_v1"
BUILD_AUDIT = Path(f"results/v25027_clue_resolved_external_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25027_clue_resolved_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25027_clue_resolved_external_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25027_clue_resolved_external_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25027_clue_resolved_external_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25027_clue_resolved_external_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(f"results/v25027_clue_resolved_external_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v25027_clue_resolved_external_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v25027_clue_resolved_external_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v25027_clue_resolved_external_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_RESULTS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
POSTFREEZE_GOLD = OUTPUT_ROOT / "postfreeze_iana_clue_gold.json"
LEASE_PATH = production.LEASE_PATH
LEASE_OWNER = "v25027_clue_resolved_external_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_clue_resolved_query_refinement_gate"

SOURCE = Path("src/deepwide_agent/v25027_clue_resolved_external_contract.py")
REFINEMENT = Path("src/deepwide_agent/v25024_evidence_conditioned_queries.py")
RUNTIME = Path("src/deepwide_agent/v25025_evidence_conditioned_paired_runtime.py")
REACHABILITY = Path("src/deepwide_agent/v25026_resolved_schema_reachability.py")
PARENT_RUNTIME = Path("src/deepwide_agent/v24996_shared_first_wave_paired_runtime.py")
FETCH = Path("src/deepwide_agent/v24985_robust_late_page_fetch.py")
HELPER = Path("scripts/run_v24985_robust_late_page_fetch_helper.py")
CONTROL = Path("scripts/control_v25027_clue_resolved_external.py")
RUNNER = Path("scripts/run_v25027_clue_resolved_external.py")
RUNNER_ENGINE = Path("scripts/run_v24997_shared_first_wave_external.py")
LEASE = Path("scripts/deepwide_api_lease.py")
EVALUATOR = Path("scripts/evaluate_v25027_clue_resolved_external.py")
EVALUATOR_MAPPING = Path("src/deepwide_agent/v25027_clue_gold_mapping.py")
TEST = Path("tests/test_v25027_clue_resolved_external.py")
REFINEMENT_TEST = Path("tests/test_v25024_evidence_conditioned_queries.py")
RUNTIME_TEST = Path("tests/test_v25025_evidence_conditioned_paired_runtime.py")
REACHABILITY_TEST = Path("tests/test_v25026_resolved_schema_reachability.py")
LOCAL_SOURCES = (
    SOURCE,
    REFINEMENT,
    RUNTIME,
    REACHABILITY,
    PARENT_RUNTIME,
    FETCH,
    HELPER,
    CONTROL,
    RUNNER,
    RUNNER_ENGINE,
    LEASE,
    TEST,
    REFINEMENT_TEST,
    RUNTIME_TEST,
    REACHABILITY_TEST,
)
FORWARD_SOURCES = (
    SOURCE,
    REFINEMENT,
    RUNTIME,
    REACHABILITY,
    PARENT_RUNTIME,
    FETCH,
    HELPER,
    RUNNER,
    RUNNER_ENGINE,
    LEASE,
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
IANA_URL = "https://www.iana.org/domains/root/db"
COLUMNS = ("Domain", "Type", "TLD Manager")
MAX_GOLD_BYTES = 3_000_000

# Public task data only.  Order is frozen before any final-population network,
# model, or evaluator access.  The corresponding country/TLD vector is absent.
CLUES = (
    ("New Delhi", "INR"),
    ("Baghdad", "IQD"),
    ("Tehran", "IRR"),
    ("Reykjavik", "ISK"),
    ("Rome", "EUR"),
    ("Saint Helier", "GBP"),
    ("Kingston", "JMD"),
    ("Amman", "JOD"),
    ("Tokyo", "JPY"),
    ("Nairobi", "KES"),
    ("Bishkek", "KGS"),
    ("Phnom Penh", "KHR"),
    ("South Tarawa", "AUD"),
    ("Moroni", "KMF"),
    ("Basseterre", "XCD"),
    ("Seoul", "KRW"),
    ("Kuwait City", "KWD"),
    ("George Town", "KYD"),
    ("Astana", "KZT"),
    ("Vientiane", "LAK"),
)


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
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        timeout=20, check=True,
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
    if len(CLUES) != TASK_COUNT or len(set(CLUES)) != TASK_COUNT:
        raise RuntimeError("V2.50.27 public clue population drifted")
    values: list[dict[str, str]] = []
    for capital, currency_code in CLUES:
        opaque = "task_" + hashlib.sha256(
            f"v25027:{capital}:{currency_code}".encode()
        ).hexdigest()[:24]
        question = (
            f"Identify the jurisdiction whose capital is {capital} and whose official "
            f"currency has ISO 4217 code {currency_code}. Then use public web search "
            "and the official IANA Root Zone Database to return exactly one Markdown "
            "table and no prose for that jurisdiction's country-code top-level domain. "
            "Column names: Domain, Type, TLD Manager. Preserve exact spelling and use "
            "the Type and TLD Manager from the same official IANA record."
        )
        values.append({"opaque_id": opaque, "question": question})
    return validate_task_vector(values)


def validate_task_vector(values: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.50.27 task denominator drifted")
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for value, (capital, code) in zip(values, CLUES, strict=True):
        if not isinstance(value, Mapping) or set(value) != {"opaque_id", "question"}:
            raise ValueError("V2.50.27 runtime input must be opaque_id and question")
        opaque = value.get("opaque_id")
        question = value.get("question")
        if (
            not isinstance(opaque, str) or len(opaque) != 29
            or not opaque.startswith("task_") or opaque in seen
            or not isinstance(question, str) or capital not in question or code not in question
            or any(column not in question for column in COLUMNS)
            or IANA_URL in question or "<DOMAIN>" in question or "<COUNTRY>" in question
        ):
            raise ValueError("V2.50.27 visible task binding drifted")
        seen.add(opaque)
        output.append({"opaque_id": opaque, "question": question})
    return output


def arm_order_vector() -> list[list[str]]:
    tasks = task_vector()
    ranked = sorted(
        range(TASK_COUNT),
        key=lambda index: hashlib.sha256(
            f"v25027-arm:{tasks[index]['opaque_id']}".encode()
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
        "visible_population_contains_capital_currency_clues_but_no_country_or_tld_mapping": True,
        "evaluator_only_country_tld_mapping_module_absent_before_prediction_freeze": True,
        "excluded_development_probe_not_in_final_population": True,
        "one_shared_visible_only_planning_call": True,
        "one_shared_evidence_conditioned_refinement_call": True,
        "one_physical_first_wave_reused_byte_exactly_by_both_arms": True,
        "control_ignores_refinement_and_replays_legacy_second_wave": True,
        "candidate_uses_refinement_only_after_strict_visible_support_gate": True,
        "per_arm_logical_model_query_fetch_caps": {"models": 3, "queries": 4, "fetches": 10},
        "paired_physical_model_query_fetch_caps": {"models": 4, "queries": 6, "fetches": 14},
        "same_projector_evidence_prompt_model_output_and_deadline": True,
        "resolved_schema_observer_changes_no_runtime_effect": True,
        "prediction_freeze_before_mapping_gold_evaluator_or_quality_decision": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
        "entropy_or_information_gain_assigns_credit_or_routes": False,
        "public_deepwidebench_exact220_launch_authorized": False,
    }


def mechanism_gate() -> dict[str, Any]:
    return {
        "terminal_tasks": TASK_COUNT,
        "minimum_refinement_model_call_attempted_tasks": 18,
        "minimum_refinement_strategy_applied_tasks": 12,
        "minimum_candidate_resolved_schema_pages": 6,
        "minimum_tasks_with_candidate_resolved_schema_strict_advantage": 6,
        "minimum_both_arms_model_success_tasks": 18,
        "minimum_prediction_changed_tasks": 6,
        "shared_prefix_byte_equal_tasks": TASK_COUNT,
        "all_tasks_execute_at_most_six_physical_queries": True,
        "all_tasks_fetch_at_most_fourteen_physical_pages": True,
        "all_tasks_use_at_most_four_physical_model_calls": True,
        "executed_arm_order_matches_frozen_vector": True,
    }


def quality_gate() -> dict[str, Any]:
    return {
        "fixed_denominator": TASK_COUNT,
        "candidate_exact_strictly_greater": True,
        "candidate_composite_strictly_greater": True,
        "entity_row_item_column_nonregression": True,
        "invalid_or_fallback_nonincrease": True,
    }


def dependency_manifest(root: Path, *, tracked: bool = True) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in LOCAL_SOURCES:
        path = root / relative
        if relative.is_absolute() or ".." in relative.parts or path.is_symlink() or not path.is_file():
            raise RuntimeError("V2.50.27 source manifest path drifted")
        if tracked and subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)], cwd=root,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=20, check=False,
        ).returncode != 0:
            raise RuntimeError("V2.50.27 source is not tracked")
        output[str(relative)] = sha256(path)
    return output


def _protocol(root: Path, *, now: int, tracked: bool) -> dict[str, Any]:
    tasks = task_vector()
    manifest = dependency_manifest(root, tracked=tracked)
    value = {
        "artifact_version": 1,
        "role": "v25027_clue_resolved_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "git_head": git(root, "rev-parse", "HEAD"),
        "population": {
            "selected_tasks": TASK_COUNT,
            "opaque_id_vector_sha256": payload_sha256([row["opaque_id"] for row in tasks]),
            "visible_question_vector_sha256": payload_sha256([row["question"] for row in tasks]),
            "task_vector_sha256": payload_sha256(tasks),
            "public_clue_vector_sha256": payload_sha256(CLUES),
            "arm_order_vector_sha256": payload_sha256(arm_order_vector()),
            "country_tld_or_gold_mapping_module_present_opened_or_hashed": False,
            "final_population_network_model_or_evaluator_probed_before_freeze": False,
        },
        "execution": {
            "output_root": str(OUTPUT_ROOT),
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "limits_per_arm": copy.deepcopy(LIMITS),
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


def validate_protocol(root: Path, value: Mapping[str, Any], *, tracked: bool = True) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    observed = unsigned.pop("protocol_payload_sha256", None)
    tasks = task_vector()
    population = copied.get("population")
    execution = copied.get("execution")
    authorization = copied.get("authorization")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != "v25027_clue_resolved_external_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not isinstance(copied.get("created_at_unix"), int)
        or not isinstance(copied.get("git_head"), str)
        or len(copied["git_head"]) != 40
        or not isinstance(population, Mapping)
        or population != {
            "selected_tasks": TASK_COUNT,
            "opaque_id_vector_sha256": payload_sha256([row["opaque_id"] for row in tasks]),
            "visible_question_vector_sha256": payload_sha256([row["question"] for row in tasks]),
            "task_vector_sha256": payload_sha256(tasks),
            "public_clue_vector_sha256": payload_sha256(CLUES),
            "arm_order_vector_sha256": payload_sha256(arm_order_vector()),
            "country_tld_or_gold_mapping_module_present_opened_or_hashed": False,
            "final_population_network_model_or_evaluator_probed_before_freeze": False,
        }
        or not isinstance(execution, Mapping)
        or execution.get("output_root") != str(OUTPUT_ROOT)
        or execution.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or execution.get("model_slot_cap") != MODEL_SLOT_CAP
        or execution.get("model") != MODEL or execution.get("search") != SEARCH
        or execution.get("limits_per_arm") != LIMITS
        or execution.get("protected_watchers") != watcher_snapshot()
        or execution.get("single_atomic_forward_no_retry_resume_or_selective_rerun") is not True
        or copied.get("mechanism_gate_before_evaluator") != mechanism_gate()
        or copied.get("quality_gate") != quality_gate()
        or copied.get("source_policy") != source_policy()
        or copied.get("dependency_manifest") != dependency_manifest(root, tracked=tracked)
        or copied.get("dependency_manifest_sha256") != payload_sha256(copied["dependency_manifest"])
        or authorization != {
            "preactivation_audit_generation": True,
            "one_external_forward": False,
            "postfreeze_evaluator": False,
            "public_exact220_launch": False,
            "leaderboard_or_sota": False,
        }
        or observed != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.27 protocol drifted")
    return copied


__all__ = [
    "ARMS", "BUILD_AUDIT", "CANDIDATE_ARM", "CLUES", "COLUMNS", "CONTROL_ARM",
    "CONTROL", "EVALUATOR", "EVALUATOR_MAPPING", "EVALUATOR_PROTOCOL",
    "EXECUTION_START", "FORWARD_AUDIT", "FORWARD_RESULT", "FORWARD_SOURCES",
    "HELPER", "LEASE_OWNER", "LEASE_PATH", "LEASE_PURPOSE", "LIMITS",
    "LOCAL_SOURCES", "MAX_GOLD_BYTES", "MODEL", "MODEL_SLOT_CAP",
    "MODEL_SLOT_DIRECTORY", "OUTPUT_ROOT", "PHASES", "POSTAUDIT",
    "POSTFREEZE_GOLD", "PREAUDIT", "PREDICTION_FREEZE", "PROTOCOL",
    "PROTOCOL_ID", "REACHABILITY", "REFINEMENT", "RESULT", "RUNNER", "RUNNER_ENGINE", "RUNTIME",
    "SEARCH", "SOURCE", "TASK_COUNT", "TASK_RESULTS", "TEST", "arm_order_vector",
    "build_protocol", "dependency_manifest", "git", "mechanism_gate", "payload_sha256",
    "quality_gate", "seal", "sealed", "sha256", "source_policy", "task_vector",
    "validate_protocol", "validate_task_vector", "watcher_snapshot",
]
