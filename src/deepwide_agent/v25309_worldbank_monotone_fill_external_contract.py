"""Frozen contract for the fresh12 World Bank monotone-fill mechanism gate.

The runtime boundary is exactly ``{opaque_id, question}``.  The only evidence
available to either arm is the already-frozen V2.53.05 World Bank page vector.
This contract has no evaluator capability and grants no DeepWideBench launch
authority.  Entropy/information gain remains shadow-only with signed credit 0.
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v25309_pipe_visible_schema_worldbank_gate as runtime
from . import v25248_header_totality_shadow_external_contract as foundation


DATE = "20260813"
PROTOCOL_ID = "v25309_worldbank_monotone_fill_mechanism_v1"
ROLE = "v25309_worldbank_monotone_fill_external_contract"

CONTRACT = Path(
    "src/deepwide_agent/v25309_worldbank_monotone_fill_external_contract.py"
)
RUNNER = Path("scripts/run_v25309_worldbank_monotone_fill_external.py")
CONTROL = Path("scripts/control_v25309_worldbank_monotone_fill_external.py")
LAUNCH_CONTROL = Path("scripts/control_v25310_worldbank_monotone_fill_launch.py")
FORWARD_AUDITOR = Path("scripts/audit_v25311_worldbank_monotone_fill_forward.py")
TEST = Path("tests/test_v25309_worldbank_monotone_fill_external.py")

BUILD_AUDIT = Path(f"results/v25309_worldbank_monotone_fill_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25309_worldbank_monotone_fill_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25310_worldbank_monotone_fill_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25310_worldbank_monotone_fill_execution_start_v1_{DATE}.json")
ATTEMPT_CLAIM = Path(f"results/v25309_worldbank_monotone_fill_attempt_claim_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25309_worldbank_monotone_fill_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25311_worldbank_monotone_fill_forward_audit_v1_{DATE}.json")

OUTPUT_ROOT = Path(f"outputs/v25309_worldbank_monotone_fill_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"

POPULATION_FREEZE = Path(f"results/v25305_worldbank_population_freeze_v1_{DATE}.json")
POPULATION_FREEZE_SHA256 = "6abbce3cb6271cde5046479b78a8436ba41fbb383679c102d857731d262e600b"
PRIVATE_POPULATION = Path(f"outputs/v25305_worldbank_population_v1_{DATE}/population.json")
PRIVATE_POPULATION_SHA256 = "ced33e651b0d72a65a59d4106ea5b68316f25bd5b31ca9a54f8f1c9d2689fcec"
POPULATION_AUDIT = Path(f"results/v25308_worldbank_population_postfreeze_audit_v1_{DATE}.json")
POPULATION_AUDIT_SHA256 = "eb699da33a7615ddecb854d1982ea2e2f2233b86464563914c75ea4d017c4b09"
RUNTIME_BUILD_AUDIT = Path(f"results/v25296_worldbank_monotone_fill_build_audit_v1_{DATE}.json")
RUNTIME_BUILD_AUDIT_SHA256 = "6a07c8459175660374a0cdb32e09bffa314f2c0fa0088ab9c19374e765ba6de8"
DESIGN = Path(f"results/v25294_worldbank_monotone_fill_gate_design_r2_{DATE}.json")
DESIGN_SHA256 = "92e1ad85f8a363243abd64676c3149eef0266b1acb5c7196e7d8b5061c03ead4"

TASK_COUNT = 12
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 8
LEASE_PATH = foundation.LEASE_PATH
LEASE_OWNER = "v25309_worldbank_monotone_fill_forward_v1"
LEASE_PURPOSE = "fresh12_frozen_worldbank_shared_prefix_monotone_fill_mechanism"
MODEL = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "name": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 65,
    "max_retries": 2,
}
LIMITS = copy.deepcopy(runtime.PARENT_LIMITS)
TWO_WAVE_POLICY = copy.deepcopy(runtime.PARENT_TWO_WAVE_POLICY)
PHYSICAL_CAPS = {
    "queries_per_task": 4,
    "fetches_per_task": 10,
    "model_forwards_per_task": 3,
    "wall_seconds_per_task": 240,
}
CLEANUP_RESERVE_SECONDS = 5.0
MINIMUM_MODEL_ATTEMPT_SECONDS = 0.05
PROTECTED_WATCHERS = copy.deepcopy(foundation.PROTECTED_WATCHERS)

TASK_VECTOR_SHA256 = "a1185cd7dec525c97332b04cbf1e86f78c71bfdc1f6e54755293c6331c04ba4e"
OPAQUE_ID_VECTOR_SHA256 = "b865907e726e4b81def58fc1555ad4dd69ee8435498b8e34fe5f62dbfa1a849b"
QUESTION_VECTOR_SHA256 = "6f676b2fac44ca574c40214e4b8ec0499d31464ceaf12b3b41fe6b43e85275f2"
RENDERED_PAGES_SHA256 = "5d24a832a30f5d9156a313599413e1ab34ac13713431c0bfe1fd744691009b1d"
TARGET_KEYS = (
    "fi.res.xgld.cd@2022",
    "sl.ind.empl.ma.zs@2022",
    "er.h2o.fwin.zs@2022",
    "sl.emp.totl.sp.zs@2022",
)

payload_sha256 = foundation.payload_sha256
seal = foundation.seal
sealed = foundation.sealed
ordinary = foundation.ordinary
sha256 = foundation.sha256
git = foundation.git
watcher_snapshot = foundation.watcher_snapshot


def _load_json(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(ordinary(root, relative, tracked=True).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.53.09 expected a JSON object")
    return value


def _validate_task(value: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != {"opaque_id", "question"}:
        raise ValueError("V2.53.09 runtime task boundary drifted")
    opaque_id = value.get("opaque_id")
    question = value.get("question")
    if (
        not isinstance(opaque_id, str)
        or re.fullmatch(r"task_[0-9a-f]{24}", opaque_id) is None
        or not isinstance(question, str)
        or not question.startswith("Return exactly one Markdown table and no prose. Column names: ")
        or ". Include exactly these entity-code rows in this order: " not in question
        or not question.endswith(
            ". Use Unknown only when the supplied official pages do not show a value."
        )
    ):
        raise ValueError("V2.53.09 visible task grammar drifted")
    return {"opaque_id": opaque_id, "question": question}


def validate_task_vector(values: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.53.09 task denominator drifted")
    tasks = [_validate_task(value) for value in values]
    if (
        len({row["opaque_id"] for row in tasks}) != TASK_COUNT
        or payload_sha256(tasks) != TASK_VECTOR_SHA256
        or payload_sha256([row["opaque_id"] for row in tasks]) != OPAQUE_ID_VECTOR_SHA256
        or payload_sha256([row["question"] for row in tasks]) != QUESTION_VECTOR_SHA256
    ):
        raise ValueError("V2.53.09 frozen task vector seal drifted")
    return tasks


def _validate_pages(values: object) -> list[dict[str, Any]]:
    if not isinstance(values, list) or len(values) != runtime.PAGE_COUNT:
        raise ValueError("V2.53.09 frozen page vector drifted")
    pages: list[dict[str, Any]] = []
    for value in values:
        if (
            not isinstance(value, Mapping)
            or set(value) != {"url", "title", "content", "fetch_integrity"}
            or value.get("fetch_integrity") is not True
            or not isinstance(value.get("url"), str)
            or not isinstance(value.get("title"), str)
            or not isinstance(value.get("content"), str)
            or not value["content"]
            or len(value["content"]) > runtime.MAXIMUM_PAGE_CHARS
        ):
            raise ValueError("V2.53.09 frozen page schema drifted")
        pages.append(copy.deepcopy(dict(value)))
    if payload_sha256(pages) != RENDERED_PAGES_SHA256:
        raise ValueError("V2.53.09 frozen page hash drifted")
    return pages


def frozen_population(root: Path | None = None) -> dict[str, Any]:
    repository = Path(__file__).resolve().parents[2] if root is None else Path(root).resolve()
    fixed = {
        POPULATION_FREEZE: POPULATION_FREEZE_SHA256,
        PRIVATE_POPULATION: PRIVATE_POPULATION_SHA256,
        POPULATION_AUDIT: POPULATION_AUDIT_SHA256,
        RUNTIME_BUILD_AUDIT: RUNTIME_BUILD_AUDIT_SHA256,
        DESIGN: DESIGN_SHA256,
    }
    if any(sha256(ordinary(repository, path, tracked=True)) != digest for path, digest in fixed.items()):
        raise RuntimeError("V2.53.09 parent authority hash drifted")
    freeze = _load_json(repository, POPULATION_FREEZE)
    private = _load_json(repository, PRIVATE_POPULATION)
    audit = _load_json(repository, POPULATION_AUDIT)
    build = _load_json(repository, RUNTIME_BUILD_AUDIT)
    design = _load_json(repository, DESIGN)
    unsigned = dict(private)
    private_seal = unsigned.pop("population_payload_sha256", None)
    population = private.get("population")
    if (
        private.get("role") != "v25305_private_frozen_worldbank_population"
        or private_seal != payload_sha256(unsigned)
        or not isinstance(population, Mapping)
        or set(population) != {"target_keys", "target_columns", "entities", "pages", "tasks"}
        or tuple(population.get("target_keys") or ()) != TARGET_KEYS
        or len(population.get("target_columns") or ()) != runtime.TARGET_COUNT
        or len(population.get("entities") or ()) != runtime.ENTITY_ROW_COUNT
        or freeze.get("decision") != "go"
        or (freeze.get("population") or {}).get("private_sha256") != PRIVATE_POPULATION_SHA256
        or (freeze.get("population") or {}).get("task_vector_sha256") != TASK_VECTOR_SHA256
        or audit.get("role") != "v25308_worldbank_population_postfreeze_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or (audit.get("authorization") or {}).get(
            "external_monotone_fill_mechanism_protocol_design"
        )
        is not True
        or (audit.get("authorization") or {}).get(
            "external_monotone_fill_forward_or_postfreeze_evaluator"
        )
        is not False
        or build.get("role") != "v25296_worldbank_monotone_fill_clean_build_audit"
        or build.get("audit_valid") is not True
        or build.get("findings") != []
        or (build.get("authorization") or {}).get("external_activation_or_launch") is not False
        or design.get("research_question")
        != "does_one_budgeted_third_model_call_plus_mechanical_monotone_support_fill_unknown_cells_and_improve_outer_table_utility"
    ):
        raise RuntimeError("V2.53.09 parent authority semantics drifted")
    tasks = validate_task_vector(population["tasks"])
    pages = _validate_pages(population["pages"])
    return {
        "tasks": tasks,
        "pages": pages,
        "target_keys": list(TARGET_KEYS),
        "target_columns": copy.deepcopy(list(population["target_columns"])),
        "entities": copy.deepcopy(list(population["entities"])),
    }


def task_vector(root: Path | None = None) -> list[dict[str, str]]:
    return copy.deepcopy(frozen_population(root)["tasks"])


def page_vector(root: Path | None = None) -> list[dict[str, Any]]:
    return copy.deepcopy(frozen_population(root)["pages"])


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_frozen_pages"],
        "control_and_candidate_share_parent_queries_search_fetch_and_page_bytes": True,
        "candidate_only_may_consume_unused_third_model_slot": True,
        "candidate_additional_query_or_fetch_effect": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "retry_resume_skip_backfill_replacement_selective_rerun_or_second_attempt": False,
        "quality_metric_or_evaluator_called": False,
        "entropy_or_information_gain_assigns_signed_credit_or_routes": False,
        "positive_signed_credit_count": 0,
    }


def mechanism_gate() -> dict[str, Any]:
    return {
        "fixed_task_denominator": TASK_COUNT,
        "required_terminal_tasks": TASK_COUNT,
        "minimum_parent_two_call_baseline_unknown_tasks": 2,
        "minimum_complete_eight_page_prefix_tasks": 2,
        "minimum_revision_prompt_within_cap_tasks": 2,
        "minimum_third_slot_proposal_tasks": 2,
        "minimum_supported_unknown_fill_tasks": 2,
        "minimum_supported_unknown_fill_cells": 2,
        "minimum_attributable_prediction_change_tasks": 2,
        "required_query_effect_equal_tasks": TASK_COUNT,
        "required_fetch_effect_equal_tasks": TASK_COUNT,
        "required_total_model_calls_at_most_three_tasks": TASK_COUNT,
        "maximum_known_cell_schema_row_key_order_or_count_violation_tasks": 0,
        "maximum_unsupported_or_conflicting_admitted_fill_cells": 0,
        "maximum_queries_total": TASK_COUNT * PHYSICAL_CAPS["queries_per_task"],
        "maximum_fetches_total": TASK_COUNT * PHYSICAL_CAPS["fetches_per_task"],
        "maximum_model_forwards_total": TASK_COUNT * PHYSICAL_CAPS["model_forwards_per_task"],
        "positive_signed_credit_count": 0,
        "go_only_authorizes_postfreeze_evaluator_after_pushed_forward_audit": True,
    }


def build_protocol(*, source_manifest: Mapping[str, str], now: int) -> dict[str, Any]:
    population = frozen_population()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25309_worldbank_monotone_fill_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "parents": {
            str(POPULATION_FREEZE): POPULATION_FREEZE_SHA256,
            str(PRIVATE_POPULATION): PRIVATE_POPULATION_SHA256,
            str(POPULATION_AUDIT): POPULATION_AUDIT_SHA256,
            str(RUNTIME_BUILD_AUDIT): RUNTIME_BUILD_AUDIT_SHA256,
            str(DESIGN): DESIGN_SHA256,
        },
        "source_manifest": dict(source_manifest),
        "population": {
            "task_count": TASK_COUNT,
            "task_vector_sha256": payload_sha256(population["tasks"]),
            "page_vector_sha256": payload_sha256(population["pages"]),
            "runtime_keys": ["opaque_id", "question"],
        },
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "single_cold_forward": True,
            "failure_as_zero_fixed_denominator": True,
            "retry_resume_skip_backfill_replacement_or_selective_rerun": False,
            "protected_watchers": watcher_snapshot(),
        },
        "model": copy.deepcopy(MODEL),
        "logical_limits": copy.deepcopy(LIMITS),
        "two_wave_policy": copy.deepcopy(TWO_WAVE_POLICY),
        "physical_caps": copy.deepcopy(PHYSICAL_CAPS),
        "source_policy": source_policy(),
        "mechanism_gate": mechanism_gate(),
        "authorization": {
            "preactivation_audit_generation": True,
            "external_forward": False,
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    return seal(value, "protocol_payload_sha256")


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    manifest = copied.get("source_manifest")
    population = frozen_population(root)
    expected_parents = {
        str(POPULATION_FREEZE): POPULATION_FREEZE_SHA256,
        str(PRIVATE_POPULATION): PRIVATE_POPULATION_SHA256,
        str(POPULATION_AUDIT): POPULATION_AUDIT_SHA256,
        str(RUNTIME_BUILD_AUDIT): RUNTIME_BUILD_AUDIT_SHA256,
        str(DESIGN): DESIGN_SHA256,
    }
    try:
        observed_manifest = {
            str(path): sha256(ordinary(root, Path(str(path)), tracked=True))
            for path in manifest or {}
        }
    except BaseException:
        observed_manifest = {}
    if (
        set(copied)
        != {
            "artifact_version", "role", "protocol_id", "created_at_unix", "parents",
            "source_manifest", "population", "execution", "model", "logical_limits",
            "two_wave_policy", "physical_caps", "source_policy", "mechanism_gate",
            "authorization", "protocol_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25309_worldbank_monotone_fill_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied.get("parents") != expected_parents
        or not isinstance(manifest, Mapping)
        or not manifest
        or any(re.fullmatch(r"[0-9a-f]{64}", str(digest)) is None for digest in manifest.values())
        or observed_manifest != dict(manifest)
        or copied.get("population")
        != {
            "task_count": TASK_COUNT,
            "task_vector_sha256": payload_sha256(population["tasks"]),
            "page_vector_sha256": payload_sha256(population["pages"]),
            "runtime_keys": ["opaque_id", "question"],
        }
        or copied.get("execution")
        != {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "single_cold_forward": True,
            "failure_as_zero_fixed_denominator": True,
            "retry_resume_skip_backfill_replacement_or_selective_rerun": False,
            "protected_watchers": watcher_snapshot(),
        }
        or copied.get("model") != MODEL
        or copied.get("logical_limits") != LIMITS
        or copied.get("two_wave_policy") != TWO_WAVE_POLICY
        or copied.get("physical_caps") != PHYSICAL_CAPS
        or copied.get("source_policy") != source_policy()
        or copied.get("mechanism_gate") != mechanism_gate()
        or copied.get("authorization")
        != {
            "preactivation_audit_generation": True,
            "external_forward": False,
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
        }
        or not sealed(copied, "protocol_payload_sha256")
    ):
        raise ValueError("V2.53.09 protocol drifted")
    return copied


__all__ = [
    "ATTEMPT_CLAIM", "BUILD_AUDIT", "CLEANUP_RESERVE_SECONDS", "CONTRACT",
    "CONTROL", "DATE", "DESIGN", "DESIGN_SHA256", "EXECUTION_START",
    "EXECUTOR_CONCURRENCY", "FORWARD_AUDIT", "FORWARD_AUDITOR", "FORWARD_RESULT",
    "LAUNCH_CONTROL", "LEASE_OWNER", "LEASE_PATH", "LEASE_PURPOSE", "LIMITS",
    "MINIMUM_MODEL_ATTEMPT_SECONDS", "MODEL", "MODEL_SLOT_CAP", "MODEL_SLOT_DIRECTORY",
    "OPAQUE_ID_VECTOR_SHA256", "OUTPUT_ROOT", "PHYSICAL_CAPS", "POPULATION_AUDIT",
    "POPULATION_AUDIT_SHA256", "POPULATION_FREEZE", "POPULATION_FREEZE_SHA256",
    "PREAUDIT", "PREDICTION_FREEZE", "PRIVATE_POPULATION", "PRIVATE_POPULATION_SHA256",
    "PROTOCOL", "PROTOCOL_ID", "QUESTION_VECTOR_SHA256", "RENDERED_PAGES_SHA256",
    "ROLE", "RUNNER", "RUNTIME_BUILD_AUDIT", "RUNTIME_BUILD_AUDIT_SHA256",
    "SAFE_PROGRESS", "TASK_COUNT", "TASK_ROWS", "TASK_VECTOR_SHA256", "TEST",
    "TWO_WAVE_POLICY", "build_protocol", "frozen_population", "git", "mechanism_gate",
    "ordinary", "page_vector", "payload_sha256", "runtime", "seal", "sealed", "sha256",
    "source_policy", "task_vector", "validate_protocol", "validate_task_vector",
    "watcher_snapshot",
]
