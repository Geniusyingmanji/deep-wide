"""Label-blind exact-220 contract for the V2.50.18 treatment bundle.

The parent is the repository-best V2.48.57 pacing-aware policy.  This contract
keeps its visible 220-vector, model, prompts, pacing/rate transport, budgets,
and 20-executor/8-model-slot concurrency.  The preregistered treatment bundle
contains exactly the two components jointly validated by V2.50.18:

* matched-count second-wave selection for strict distinct visible identities;
* strict multi-identity detail projection inside the inherited bounded fetch.

The selector replays the frozen parent URL vector as control and changes it
only for strict distinct-identity gain.  The projector returns the exact parent
5k prefix unless one page atomically binds one visible identity and all target
fields.  Entropy/IG remain shadow-only and assign no signed credit.
"""

from __future__ import annotations

import copy
import json
import re
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v24857_pacing_aware_exact220_contract as parent
from . import v25019_production_distinct_coverage_selection as selection
from . import v25020_pacing_distinct_coverage_retrieval as retrieval
from . import v25021_rate_aware_multi_identity_search as search
from . import v25022_production_distinct_coverage_task as task_integration
from . import v25014_multi_identity_detail_fields as identity_parser
from . import v24630_exact220_contract as visible_source


DATE = "20260809"
ROLE = "v25023_distinct_coverage_exact220_preregistration"
PROTOCOL_ID = "v25023_label_blind_distinct_identity_coverage_exact220_v1"
EXPOSURE_AUDIT = Path(
    f"results/v25023_distinct_coverage_exact220_exposure_audit_v1_{DATE}.json"
)
PROTOCOL = Path(f"results/v25023_distinct_coverage_exact220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25023_distinct_coverage_exact220_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25023_distinct_coverage_exact220_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25023_distinct_coverage_exact220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25023_distinct_coverage_exact220_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(f"results/v25023_distinct_coverage_exact220_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v25023_distinct_coverage_exact220_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v25023_distinct_coverage_exact220_postresult_audit_v1_{DATE}.json")
QUALITY_DECISION = Path(f"results/v25023_distinct_coverage_exact220_quality_decision_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v25023_distinct_coverage_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
KEY_SLOT_DIRECTORY = OUTPUT_ROOT / "tavily_key_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v25023_distinct_coverage_exact220_forward_v1"
LEASE_PURPOSE = "label_blind_distinct_identity_coverage_exact220"
RUNNER_MARKER = "scripts/run_v25023_distinct_coverage_exact220.py"
CHILD_MARKER = "scripts/run_v25023_distinct_coverage_exact220_task.py"
DIRECT_RECEIPT_NAME = parent.DIRECT_RECEIPT_NAME
RATE_RECEIPT_NAME = parent.RATE_RECEIPT_NAME
PACING_RECEIPT_NAME = parent.PACING_RECEIPT_NAME
DISTINCT_RECEIPT_NAME = "distinct_coverage_selection_receipt.json"
PROJECTION_RECEIPT_NAME = "multi_identity_projection_receipt.json"

SELECTED_COUNT = parent.SELECTED_COUNT
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
TAVILY_KEY_SLOT_CAP = parent.TAVILY_KEY_SLOT_CAP
LIMITS = copy.deepcopy(parent.LIMITS)
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = copy.deepcopy(parent.SEARCH)
TWO_WAVE_POLICY = copy.deepcopy(parent.TWO_WAVE_POLICY)
PROTECTED_WATCHERS = parent.PROTECTED_WATCHERS
PARENT_PROTOCOL = parent.PROTOCOL
TRANSPORT_SOURCE = parent.TRANSPORT_SOURCE
TRANSPORT_TEST = parent.TRANSPORT_TEST
ADMISSION_SOURCE = parent.ADMISSION_SOURCE
ADMISSION_TEST = parent.ADMISSION_TEST
SELECTION_SOURCE = Path("src/deepwide_agent/v25019_production_distinct_coverage_selection.py")
RETRIEVAL_SOURCE = Path("src/deepwide_agent/v25020_pacing_distinct_coverage_retrieval.py")
SEARCH_SOURCE = Path("src/deepwide_agent/v25021_rate_aware_multi_identity_search.py")
TASK_INTEGRATION_SOURCE = Path("src/deepwide_agent/v25022_production_distinct_coverage_task.py")
PROJECTOR_SOURCE = Path("src/deepwide_agent/v25014_multi_identity_detail_fields.py")
SELECTOR_PARENT_SOURCE = Path("src/deepwide_agent/v25015_distinct_identity_child_selection.py")
FETCH_SOURCE = Path("src/deepwide_agent/v25016_multi_identity_detail_fetch.py")
FETCH_PARENT_SOURCE = Path("src/deepwide_agent/v24981_late_page_bound_fetch.py")
FETCH_HELPER = Path("scripts/run_v25016_multi_identity_detail_fetch_helper.py")
SOURCE = Path("src/deepwide_agent/v25023_distinct_coverage_exact220_contract.py")
CONTROL = Path("scripts/control_v25023_distinct_coverage_exact220.py")
RUNNER = Path(RUNNER_MARKER)
CHILD = Path(CHILD_MARKER)
FINALIZER = Path("scripts/finalize_v25023_distinct_coverage_exact220.py")
TEST = Path("tests/test_v25023_distinct_coverage_exact220.py")
TREATMENT_TESTS = (
    Path("tests/test_v25019_production_distinct_coverage_selection.py"),
    Path("tests/test_v25020_pacing_distinct_coverage_retrieval.py"),
    Path("tests/test_v25021_rate_aware_multi_identity_search.py"),
    Path("tests/test_v25022_production_distinct_coverage_task.py"),
    Path("tests/test_v25014_multi_identity_detail_fields.py"),
    Path("tests/test_v25015_distinct_identity_child_selection.py"),
    Path("tests/test_v25016_multi_identity_detail_fetch.py"),
)
LOCAL_SOURCES = (
    SOURCE,
    CONTROL,
    RUNNER,
    CHILD,
    FINALIZER,
    TEST,
    SELECTION_SOURCE,
    RETRIEVAL_SOURCE,
    SEARCH_SOURCE,
    TASK_INTEGRATION_SOURCE,
    PROJECTOR_SOURCE,
    SELECTOR_PARENT_SOURCE,
    FETCH_SOURCE,
    FETCH_PARENT_SOURCE,
    FETCH_HELPER,
    *TREATMENT_TESTS,
)

_LINE_LIST_ITEM = re.compile(
    r"^\s*(?:[-*•·]|\d{1,2}[.)、]|[（(]\d{1,2}[）)])\s*\S"
)
_FORMAT_LIST_CUE = re.compile(
    r"(?:输出.{0,16}(?:要求|格式)|format|requirements?|note|注意|列名|columns?|表格)",
    re.IGNORECASE,
)

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
_git = parent._git
_ordinary_tracked = parent._ordinary_tracked
protected_watcher_snapshot = parent.protected_watcher_snapshot
validate_transport_gate = parent.validate_transport_gate
rate_policy = parent.rate_policy


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.50.23 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.23 expected JSON object")
    return value


def parent_contract(root: Path) -> dict[str, Any]:
    return parent.validate_protocol(root, _read(root / PARENT_PROTOCOL))


def task_vector(
    root: Path, protocol: Mapping[str, Any] | None = None
) -> list[dict[str, str]]:
    tasks = exposure_task_vector(root)
    if len(tasks) != 220 or any(set(task) != {"opaque_id", "question"} for task in tasks):
        raise RuntimeError("V2.50.23 visible exact-220 vector drifted")
    if protocol is not None and protocol.get("task_contract") != _task_contract(tasks):
        raise RuntimeError("V2.50.23 visible task binding drifted")
    return tasks


def exposure_task_vector(root: Path) -> list[dict[str, str]]:
    """Load the frozen visible-only 220 vector without opening run outputs.

    The V2.46.30 contract is the root visible manifest used by every later
    exact-220 successor.  This fast path validates its frozen selection and
    returns only ``opaque_id`` and ``question``; it never traverses prediction,
    evaluator, mapping, gold, or score artifacts.
    """

    contract = visible_source.validate_forward_contract(root)
    tasks = visible_source.selected_tasks(root, contract)
    if len(tasks) != SELECTED_COUNT or any(
        set(task) != {"opaque_id", "question"} for task in tasks
    ):
        raise RuntimeError("V2.50.23 exposure visible vector drifted")
    parent_protocol = _read(root / PARENT_PROTOCOL)
    expected = parent_protocol.get("task_contract") or {}
    observed = _task_contract(tasks)
    if any(
        expected.get(name) != observed[name]
        for name in (
            "selected_count",
            "opaque_id_vector_sha256",
            "visible_question_vector_sha256",
        )
    ):
        raise RuntimeError("V2.50.23 exposure vector differs from V2.48.57")
    return tasks


def _task_contract(tasks: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "runtime_input_keys": ["opaque_id", "question"],
        "selected_count": 220,
        "opaque_id_vector_sha256": payload_sha256([task["opaque_id"] for task in tasks]),
        "visible_question_vector_sha256": payload_sha256([task["question"] for task in tasks]),
    }


def mechanism_exposure(tasks: list[dict[str, str]]) -> dict[str, Any]:
    """Return a content-free visible-question exposure aggregate.

    Only the public ``question`` member is passed to the frozen V2.50.14
    parser.  Opaque IDs are neither read nor emitted.  Line-list structure is
    counted solely to distinguish genuine row vectors from formatting blocks;
    no list item or question text is retained.
    """

    if len(tasks) != SELECTED_COUNT or any(
        not isinstance(task, Mapping)
        or set(task) != {"opaque_id", "question"}
        or not isinstance(task.get("question"), str)
        or not task["question"].strip()
        for task in tasks
    ):
        raise RuntimeError("V2.50.23 exposure task vector drifted")
    identity_counts: Counter[int] = Counter()
    line_list_blocks = 0
    formatting_line_list_blocks = 0
    tasks_with_line_list_blocks = 0
    for task in tasks:
        question = task["question"]
        identity_counts[len(identity_parser.visible_identities(question))] += 1
        lines = question.splitlines()
        position = 0
        task_blocks = 0
        while position < len(lines):
            if _LINE_LIST_ITEM.match(lines[position]) is None:
                position += 1
                continue
            start = position
            while position < len(lines) and _LINE_LIST_ITEM.match(lines[position]):
                position += 1
            task_blocks += 1
            line_list_blocks += 1
            visible_context = "\n".join(lines[max(0, start - 3) : start])
            formatting_line_list_blocks += int(
                _FORMAT_LIST_CUE.search(visible_context) is not None
            )
        tasks_with_line_list_blocks += int(task_blocks > 0)
    strict = sum(
        task_count for identity_count, task_count in identity_counts.items()
        if identity_count >= 2
    )
    total_identities = sum(
        identity_count * task_count
        for identity_count, task_count in identity_counts.items()
    )
    value = {
        "selected_public_question_count": len(tasks),
        "parser_policy_id": identity_parser.POLICY_ID,
        "minimum_strict_multi_identity_tasks_for_protocol": 1,
        "strict_multi_identity_task_count": strict,
        "visible_identity_count_total": total_identities,
        "visible_identity_count_distribution": {
            str(count): identity_counts[count] for count in sorted(identity_counts)
        },
        "tasks_with_line_list_blocks": tasks_with_line_list_blocks,
        "line_list_block_count": line_list_blocks,
        "formatting_context_line_list_block_count": formatting_line_list_blocks,
        "nonformatting_context_line_list_block_count": (
            line_list_blocks - formatting_line_list_blocks
        ),
        "exposure_gate_passed": strict >= 1,
        "only_public_question_text_parsed": True,
        "opaque_id_question_text_identity_or_list_item_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed_by_parser": False,
    }
    return value


def build_exposure_audit(
    root: Path, *, now: int | None = None, require_clean: bool = True
) -> dict[str, Any]:
    if require_clean and (
        _git(root, "status", "--porcelain")
        or _git(root, "rev-parse", "HEAD")
        != _git(root, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.50.23 exposure audit requires clean pushed HEAD")
    exposure = mechanism_exposure(exposure_task_vector(root))
    passed = bool(exposure["exposure_gate_passed"])
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25023_distinct_coverage_exact220_exposure_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "natural_exposure_go" if passed else "no_go_zero_natural_exposure",
        "passed": passed,
        "source_bindings": {
            str(SOURCE): sha256(root / SOURCE),
            str(PROJECTOR_SOURCE): sha256(root / PROJECTOR_SOURCE),
        },
        "exposure": exposure,
        "findings": [] if passed else ["strict_multi_identity_task_exposure_zero"],
        "source_policy": {
            "runtime_input_projection": ["question"],
            "opaque_id_value_read_or_emitted": False,
            "question_identity_or_list_item_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "network_model_search_fetch_process_or_evaluator_effect": False,
        },
        "authorization": {
            "protocol_generation": passed,
            "preactivation_audit_generation": False,
            "execution_start_generation": False,
            "single_fresh_exact220_forward": False,
            "evaluator_call": False,
            "retry_resume_skip_or_selective_rerun": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_exposure_audit(root, value)


def validate_exposure_audit(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    exposure = mechanism_exposure(exposure_task_vector(root))
    passed = bool(exposure["exposure_gate_passed"])
    if (
        copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25023_distinct_coverage_exact220_exposure_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied.get("status")
        != ("natural_exposure_go" if passed else "no_go_zero_natural_exposure")
        or copied.get("passed") is not passed
        or copied.get("source_bindings")
        != {
            str(SOURCE): sha256(root / SOURCE),
            str(PROJECTOR_SOURCE): sha256(root / PROJECTOR_SOURCE),
        }
        or copied.get("exposure") != exposure
        or copied.get("findings")
        != ([] if passed else ["strict_multi_identity_task_exposure_zero"])
        or copied.get("source_policy")
        != {
            "runtime_input_projection": ["question"],
            "opaque_id_value_read_or_emitted": False,
            "question_identity_or_list_item_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "network_model_search_fetch_process_or_evaluator_effect": False,
        }
        or copied.get("authorization")
        != {
            "protocol_generation": passed,
            "preactivation_audit_generation": False,
            "execution_start_generation": False,
            "single_fresh_exact220_forward": False,
            "evaluator_call": False,
            "retry_resume_skip_or_selective_rerun": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.50.23 exposure audit drifted")
    return copied


def dependency_manifest(
    root: Path, *, require_tracked: bool = True
) -> dict[str, str]:
    base = parent_contract(root)
    relatives = {Path(name) for name in base["dependency_manifest"]}
    relatives.add(PARENT_PROTOCOL)
    relatives.update(LOCAL_SOURCES)
    return {
        str(relative): sha256(
            _ordinary_tracked(root, relative)
            if require_tracked
            else (root / relative)
        )
        for relative in sorted(relatives, key=str)
    }


def pacing_policy() -> dict[str, Any]:
    return copy.deepcopy(parent.pacing_policy())


def treatment_policy() -> dict[str, Any]:
    return {
        "selection_policy_id": selection.POLICY_ID,
        "retrieval_policy_id": retrieval.POLICY_ID,
        "search_policy_id": search.POLICY_ID,
        "task_integration_policy_id": task_integration.POLICY_ID,
        "control_second_wave_exactly_replays_v24857": True,
        "candidate_second_wave_fetch_count_equals_control": True,
        "candidate_selection_requires_strict_distinct_identity_gain": True,
        "non_multi_identity_selection_exact_handoff": True,
        "projector_nonadmission_exact_parent_5k_handoff": True,
        "projector_requires_one_joint_identity_and_all_target_fields": True,
        "same_search_response_and_same_run_first_wave_pages_only": True,
        "additional_query_fetch_model_token_context_byte_wall_or_network_cap": False,
        "entropy_or_information_gain_assigns_credit_or_routes": False,
    }


def _parent_equalities() -> dict[str, bool]:
    values = {
        "selected_count_equal_v24857": SELECTED_COUNT == parent.SELECTED_COUNT == 220,
        "executor_concurrency_equal_v24857": EXECUTOR_CONCURRENCY == parent.EXECUTOR_CONCURRENCY == 20,
        "model_slot_cap_equal_v24857": MODEL_SLOT_CAP == parent.MODEL_SLOT_CAP == 8,
        "tavily_key_slot_cap_equal_v24857": TAVILY_KEY_SLOT_CAP == parent.TAVILY_KEY_SLOT_CAP == 12,
        "limits_equal_v24857": LIMITS == parent.LIMITS,
        "model_equal_v24857": MODEL == parent.MODEL,
        "search_equal_v24857": SEARCH == parent.SEARCH,
        "two_wave_policy_equal_v24857": TWO_WAVE_POLICY == parent.TWO_WAVE_POLICY,
        "rate_policy_equal_v24857": rate_policy() == parent.rate_policy(),
        "pacing_policy_equal_v24857": pacing_policy() == parent.pacing_policy(),
    }
    if not all(values.values()):
        raise RuntimeError("V2.50.23 frozen parent equality drifted")
    return values


def _single_change() -> dict[str, Any]:
    return {
        "preregistered_v25018_treatment_bundle": treatment_policy(),
        "parent_equalities": _parent_equalities(),
        "fresh_execution_and_artifact_surfaces": True,
        "prior_prediction_result_score_or_evaluator_read_or_reused": False,
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
        raise RuntimeError("V2.50.23 protocol requires clean pushed HEAD")
    future = (
        PROTOCOL,
        PREAUDIT,
        EXECUTION_START,
        FORWARD_RESULT,
        FORWARD_AUDIT,
        EVALUATOR_PROTOCOL,
        RESULT,
        POSTAUDIT,
        QUALITY_DECISION,
        OUTPUT_ROOT,
    )
    if require_pristine and any((root / path).exists() or (root / path).is_symlink() for path in future):
        raise FileExistsError("V2.50.23 future surface exists")
    exposure = validate_exposure_audit(root, _read(root / EXPOSURE_AUDIT))
    if exposure["passed"] is not True:
        raise RuntimeError("V2.50.23 protocol blocked by zero natural mechanism exposure")
    base = parent_contract(root)
    tasks = task_vector(root)
    manifest = dependency_manifest(root, require_tracked=require_clean)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "git_head": _git(root, "rev-parse", "HEAD") if require_clean else "build-only",
        "parent_algorithm": {
            "path": str(PARENT_PROTOCOL),
            "sha256": sha256(root / PARENT_PROTOCOL),
            "protocol_id": base["protocol_id"],
            "dependency_manifest_sha256": base["dependency_manifest_sha256"],
            "prior_output_prediction_result_score_or_evaluator_read_or_reused": False,
        },
        "neutral_transport_gate": copy.deepcopy(base["neutral_transport_gate"]),
        "fixed_full_budget_control_gate": copy.deepcopy(base["fixed_full_budget_control_gate"]),
        "mechanism_exposure_gate": {
            "path": str(EXPOSURE_AUDIT),
            "sha256": sha256(root / EXPOSURE_AUDIT),
            "strict_multi_identity_task_count": exposure["exposure"][
                "strict_multi_identity_task_count"
            ],
            "passed": True,
        },
        "task_contract": _task_contract(tasks),
        "execution": {
            "executor_concurrency": 20,
            "model_slot_cap": 8,
            "tavily_key_slot_cap": 12,
            "task_wall_seconds": 240,
            "model_calls_per_task": 3,
            "search_queries_per_task": 4,
            "fetch_targets_per_task": 10,
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "two_wave_policy": copy.deepcopy(TWO_WAVE_POLICY),
            "rate_policy": rate_policy(),
            "pacing_admission_policy": pacing_policy(),
            "treatment_policy": treatment_policy(),
            "protected_watchers": protected_watcher_snapshot(),
            "output_root": str(OUTPUT_ROOT),
            "key_slot_directory": str(KEY_SLOT_DIRECTORY),
            "single_fresh_forward_no_retry_resume_or_selective_rerun": True,
        },
        "single_change": _single_change(),
        "quality_gate_after_fixed_full_evaluation": {
            "candidate_exact_strictly_greater_than_v24857_nine_of_220": True,
            "candidate_composite_strictly_greater_than_v24857_0_457248978": True,
            "entity_row_item_column_nonregression_vs_v24857": True,
            "invalid_fallback_transport_failure_nonincrease_vs_v24857": True,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "runtime_reads_only_opaque_id_and_question": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
            "prior_benchmark_prediction_result_score_or_evaluator_opened_or_hashed": False,
            "credential_values_stdin_memory_only_not_persisted_hashed_or_emitted": True,
            "fixed_public_exact220_task_set_reexecuted": True,
            "new_or_disjoint_task_population_claimed": False,
            "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
            "explicit_user_request_authorizes_one_complete_exact220": True,
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


def validate_protocol(
    root: Path,
    value: Mapping[str, Any],
    *,
    manifest: Mapping[str, str] | None = None,
    tasks: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("protocol_payload_sha256", None)
    base = parent_contract(root)
    exposure = validate_exposure_audit(root, _read(root / EXPOSURE_AUDIT))
    tasks = task_vector(root) if tasks is None else tasks
    manifest = dependency_manifest(root) if manifest is None else dict(manifest)
    execution = copied.get("execution") or {}
    if (
        copied.get("role") != ROLE
        or copied.get("protocol_id") != PROTOCOL_ID
        or seal != payload_sha256(unsigned)
        or copied.get("parent_algorithm") != {
            "path": str(PARENT_PROTOCOL),
            "sha256": sha256(root / PARENT_PROTOCOL),
            "protocol_id": base["protocol_id"],
            "dependency_manifest_sha256": base["dependency_manifest_sha256"],
            "prior_output_prediction_result_score_or_evaluator_read_or_reused": False,
        }
        or copied.get("neutral_transport_gate") != base["neutral_transport_gate"]
        or copied.get("fixed_full_budget_control_gate") != base["fixed_full_budget_control_gate"]
        or exposure.get("passed") is not True
        or copied.get("mechanism_exposure_gate")
        != {
            "path": str(EXPOSURE_AUDIT),
            "sha256": sha256(root / EXPOSURE_AUDIT),
            "strict_multi_identity_task_count": exposure["exposure"][
                "strict_multi_identity_task_count"
            ],
            "passed": True,
        }
        or copied.get("task_contract") != _task_contract(tasks)
        or copied.get("dependency_manifest") != manifest
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or execution.get("executor_concurrency") != 20
        or execution.get("model_slot_cap") != 8
        or execution.get("tavily_key_slot_cap") != 12
        or execution.get("task_wall_seconds") != 240
        or execution.get("model_calls_per_task") != 3
        or execution.get("search_queries_per_task") != 4
        or execution.get("fetch_targets_per_task") != 10
        or execution.get("model") != MODEL
        or execution.get("search") != SEARCH
        or execution.get("two_wave_policy") != TWO_WAVE_POLICY
        or execution.get("rate_policy") != rate_policy()
        or execution.get("pacing_admission_policy") != pacing_policy()
        or execution.get("treatment_policy") != treatment_policy()
        or execution.get("protected_watchers") != protected_watcher_snapshot()
        or execution.get("output_root") != str(OUTPUT_ROOT)
        or execution.get("key_slot_directory") != str(KEY_SLOT_DIRECTORY)
        or execution.get("single_fresh_forward_no_retry_resume_or_selective_rerun") is not True
        or copied.get("single_change") != _single_change()
        or copied.get("source_policy", {}).get("runtime_reads_only_opaque_id_and_question") is not True
        or copied.get("source_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward"
        ) is not False
        or copied.get("authorization") != {
            "preactivation_audit_generation": True,
            "execution_start_generation": False,
            "single_fresh_exact220_forward": False,
            "evaluator_call": False,
            "retry_resume_skip_or_selective_rerun": False,
        }
    ):
        raise RuntimeError("V2.50.23 protocol drifted")
    task_vector(root, copied)
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_exposure_audit",
    "build_protocol",
    "dependency_manifest",
    "exposure_task_vector",
    "mechanism_exposure",
    "pacing_policy",
    "parent_contract",
    "payload_sha256",
    "protected_watcher_snapshot",
    "rate_policy",
    "sha256",
    "task_vector",
    "treatment_policy",
    "validate_protocol",
    "validate_exposure_audit",
    "validate_transport_gate",
]
