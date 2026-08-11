"""Fresh shared-evidence external contract for V2.50.44 synthesis treatment."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v25039_batching_external_contract as parent
from .v25044_evidence_constrained_synthesis import ARMS


DATE = "20260811"
PROTOCOL_ID = "v25045_shared_evidence_constrained_synthesis_external_v1"
BUILD_AUDIT = Path(f"results/v25045_evidence_constrained_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25045_evidence_constrained_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25045_evidence_constrained_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25045_evidence_constrained_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25045_evidence_constrained_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25045_evidence_constrained_forward_audit_v1_{DATE}.json")
EVALUATOR = Path("scripts/evaluate_v25045_evidence_constrained_external.py")
EVALUATOR_TEST = Path("tests/test_evaluate_v25045_evidence_constrained_external.py")
EVALUATOR_PROTOCOL = Path(f"results/v25045_evidence_constrained_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v25045_evidence_constrained_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v25045_evidence_constrained_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v25045_evidence_constrained_external_v1_{DATE}")
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
GOLD_SNAPSHOT = OUTPUT_ROOT / "postfreeze_pypi_gold.json"

SOURCE = Path("src/deepwide_agent/v25044_evidence_constrained_synthesis.py")
CONTRACT = Path("src/deepwide_agent/v25045_evidence_constrained_external_contract.py")
RUNNER = Path("scripts/run_v25045_evidence_constrained_external.py")
CONTROL = Path("scripts/control_v25045_evidence_constrained_external.py")
TEST = Path("tests/test_v25045_evidence_constrained_external.py")
FORWARD_SOURCES = (SOURCE, CONTRACT, RUNNER)
LOCAL_SOURCES = (SOURCE, CONTRACT, RUNNER, CONTROL, TEST)

TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 8
MODEL_OUTPUT_TOKENS = 2_400
TASK_DEADLINE_SECONDS = 240.0
EVIDENCE_CHARS = 12_000
MINIMUM_USABLE_PAGES = 2
MINIMUM_RAW_CHARACTERS = 12_000
LEAD_CAP = 10
MINIMUM_PREDICTION_CHANGES = 4
CONTROL_ARM, CANDIDATE_ARM = ARMS
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = copy.deepcopy(parent.SEARCH)
EXPECTED_WATCHERS = parent.EXPECTED_WATCHERS
LEASE_PATH = parent.LEASE_PATH
FRESHNESS_PARENT_COMMIT = "9cc4db0826234b3b3d81874430dd6929b03a7799"

# Selected only by local package-name brainstorming followed by a literal-zero
# scan against FRESHNESS_PARENT_COMMIT.  No URL, endpoint, page, answer, model,
# or evaluator was opened while selecting this vector.
PROJECTS = (
    "beartype", "typeguard", "plum-dispatch", "multipledispatch",
    "iteration-utilities", "jmespath", "jsonpath-ng", "pipdeptree", "deptry",
    "basedpyright", "autoflake", "autopep8", "yapf", "flake8", "pycodestyle",
    "pyflakes", "mccabe", "pylint", "astroid", "semgrep",
)
QUERY_PATTERNS = parent.QUERY_PATTERNS
COLUMNS = parent.COLUMNS
FALLBACK_TABLE = parent.FALLBACK_TABLE
SECRET = parent.SECRET

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
seal = parent.seal
sealed = parent.sealed
git = parent.git
ordinary = parent.ordinary
watcher_snapshot = parent.watcher_snapshot


def task_vector() -> list[dict[str, str]]:
    if len(PROJECTS) != TASK_COUNT or len(set(PROJECTS)) != TASK_COUNT:
        raise RuntimeError("V2.50.45 project vector drifted")
    rows: list[dict[str, str]] = []
    for project in PROJECTS:
        opaque = "task_" + hashlib.sha256(
            f"v25045:{project}".encode()
        ).hexdigest()[:24]
        question = (
            "Using only the supplied fetched public pages, return exactly one "
            "Markdown table and no prose. Include exactly one row for the Python "
            f"package {project}. Columns exactly: " + " | ".join(COLUMNS)
            + ". Use the canonical PyPI project name in Package. Latest release "
            "date means the earliest file upload date in the latest release, in "
            "YYYY-MM-DD form. Preserve the Requires-Python expression while "
            "collapsing whitespace. Use Unknown only when the supplied pages do "
            "not establish a value."
        )
        rows.append({"opaque_id": opaque, "question": question})
    return validate_task_vector(rows)


def validate_task_vector(values: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.50.45 task denominator drifted")
    output: list[dict[str, str]] = []
    for value, project in zip(values, PROJECTS, strict=True):
        if (
            not isinstance(value, Mapping)
            or set(value) != {"opaque_id", "question"}
            or not re.fullmatch(r"task_[0-9a-f]{24}", str(value.get("opaque_id") or ""))
            or not isinstance(value.get("question"), str)
            or project not in value["question"]
            or any(column not in value["question"] for column in COLUMNS)
            or "https://" in value["question"]
        ):
            raise ValueError("V2.50.45 visible task drifted")
        output.append({"opaque_id": str(value["opaque_id"]), "question": value["question"]})
    if len({row["opaque_id"] for row in output}) != TASK_COUNT:
        raise ValueError("V2.50.45 opaque identity collision")
    return output


def query_vector() -> list[list[str]]:
    return [
        [pattern.format(project=project) for pattern in QUERY_PATTERNS]
        for project in PROJECTS
    ]


def arm_order_vector() -> list[list[str]]:
    ranked = sorted(
        range(TASK_COUNT),
        key=lambda index: hashlib.sha256(
            f"v25045-arm-order:{task_vector()[index]['opaque_id']}".encode()
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
        "freshness_checked_against_parent_history_without_network": True,
        "one_shared_production_shaped_split_2_plus_2_search_prefix": True,
        "one_shared_task_local_union_fetch_and_evidence_prefix": True,
        "same_evidence_bytes_columns_model_output_cap_and_deadline": True,
        "only_treatment_identity_field_record_bound_synthesis_contract": True,
        "candidate_conflict_or_ambiguity_projects_unknown": True,
        "candidate_does_not_force_coverage_or_unknown_reduction": True,
        "provider_narrative_or_snippet_used_as_active_evidence": False,
        "prediction_freeze_before_gold_or_evaluator": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
        "entropy_or_information_gain_assigns_credit_or_routes": False,
        "deepwidebench_dev64_exact220_leaderboard_or_sota_authorized": False,
    }


def mechanism_gate() -> dict[str, Any]:
    return {
        "fixed_task_denominator": TASK_COUNT,
        "all_tasks_terminal": True,
        "maximum_failure_as_zero_tasks": 2,
        "exact_shared_logical_queries_per_task": 4,
        "exact_shared_provider_calls_per_task": 2,
        "maximum_provider_attempts_equal_calls": True,
        "exact_action_query_coverage": True,
        "minimum_shared_fetch_success_rate": 0.85,
        "fixed_shared_evidence_characters_per_completed_task": EVIDENCE_CHARS,
        "exact_model_attempts_per_completed_arm": 1,
        "minimum_prediction_changed_tasks": MINIMUM_PREDICTION_CHANGES,
        "maximum_transport_search_fetch_or_model_hard_failure": 0,
    }


def quality_gate() -> dict[str, Any]:
    return {
        "fixed_denominator": TASK_COUNT,
        "candidate_exact_strict_gain": True,
        "candidate_composite_nonregression": True,
        "entity_row_item_column_nonregression": True,
        "invalid_or_fallback_nonincrease": True,
        "same_search_fetch_evidence_and_per_arm_model_call_count": True,
    }


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
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            candidates: list[Path] = []
            if isinstance(node, ast.Import):
                for item in node.names:
                    if item.name.startswith("deepwide_agent."):
                        candidates.append(Path("src") / Path(*item.name.split(".")).with_suffix(".py"))
                    elif item.name.startswith("scripts."):
                        candidates.append(Path(*item.name.split(".")).with_suffix(".py"))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level and relative.parts[:2] == ("src", "deepwide_agent"):
                    if module:
                        candidates.append(Path("src/deepwide_agent") / Path(*module.split(".")).with_suffix(".py"))
                    else:
                        candidates.extend(Path("src/deepwide_agent") / f"{item.name}.py" for item in node.names)
                elif module == "deepwide_agent":
                    candidates.extend(Path("src/deepwide_agent") / f"{item.name}.py" for item in node.names)
                elif module.startswith("deepwide_agent."):
                    candidates.append(Path("src") / Path(*module.split(".")).with_suffix(".py"))
                elif module == "scripts":
                    candidates.extend(Path("scripts") / f"{item.name}.py" for item in node.names)
                elif module.startswith("scripts."):
                    candidates.append(Path(*module.split(".")).with_suffix(".py"))
            for candidate in candidates:
                if (root / candidate).is_file() and not (root / candidate).is_symlink():
                    pending.append(candidate)
    return tuple(sorted(observed, key=str))


def dependency_manifest(root: Path, *, tracked: bool) -> dict[str, str]:
    relatives = {*forward_dependency_closure(root), CONTROL, TEST}
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.50.45 credential literal in source manifest")
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
    if tracked and git(root, "rev-parse", FRESHNESS_PARENT_COMMIT) != FRESHNESS_PARENT_COMMIT:
        raise RuntimeError("V2.50.45 freshness parent absent")
    future = (
        PROTOCOL, PREAUDIT, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT,
        EVALUATOR, EVALUATOR_TEST, EVALUATOR_PROTOCOL, RESULT, POSTAUDIT,
        OUTPUT_ROOT,
    )
    if require_pristine and any((root / path).exists() or (root / path).is_symlink() for path in future):
        raise RuntimeError("V2.50.45 future surface is not pristine")
    manifest = dependency_manifest(root, tracked=tracked)
    value = {
        "artifact_version": 1,
        "role": "v25045_evidence_constrained_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit_sha256": build_audit_sha256,
        "freshness": {
            "parent_commit": FRESHNESS_PARENT_COMMIT,
            "parent_history_literal_zero_hit_projects": list(PROJECTS),
            "url_endpoint_page_answer_model_or_evaluator_opened_during_selection": False,
        },
        "population": {
            "task_count": TASK_COUNT,
            "project_vector_sha256": payload_sha256(PROJECTS),
            "task_vector_sha256": payload_sha256(task_vector()),
            "query_vector_sha256": payload_sha256(query_vector()),
            "arm_order_vector_sha256": payload_sha256(arm_order_vector()),
        },
        "execution": {
            "arms": list(ARMS),
            "only_treatment": "identity_field_record_bound_synthesis_contract",
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "shared_query_count_per_task": 4,
            "shared_provider_calls_per_task": 2,
            "shared_lead_cap": LEAD_CAP,
            "shared_evidence_chars": EVIDENCE_CHARS,
            "minimum_usable_pages": MINIMUM_USABLE_PAGES,
            "minimum_raw_characters": MINIMUM_RAW_CHARACTERS,
            "per_arm_model_calls": 1,
            "per_arm_model_output_tokens": MODEL_OUTPUT_TOKENS,
            "task_deadline_seconds": TASK_DEADLINE_SECONDS,
            "model": MODEL,
            "search": SEARCH,
        },
        "mechanism_gate": mechanism_gate(),
        "quality_gate": quality_gate(),
        "protected_watchers": watcher_snapshot(),
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": source_policy(),
        "authorization": {
            "one_external_forward_after_separate_clean_pushed_start": True,
            "evaluator_only_after_prediction_freeze_and_pushed_forward_audit": True,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_selective_rerun_or_revaluation": False,
        },
    }
    return seal(value, "protocol_payload_sha256")


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    manifest = dependency_manifest(root, tracked=True)
    expected_build = sha256(root / BUILD_AUDIT)
    if (
        copied.get("role") != "v25045_evidence_constrained_external_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("build_audit_sha256") != expected_build
        or copied.get("freshness", {}).get("parent_commit") != FRESHNESS_PARENT_COMMIT
        or copied.get("population", {}).get("task_vector_sha256") != payload_sha256(task_vector())
        or copied.get("population", {}).get("query_vector_sha256") != payload_sha256(query_vector())
        or copied.get("population", {}).get("arm_order_vector_sha256") != payload_sha256(arm_order_vector())
        or copied.get("execution", {}).get("only_treatment") != "identity_field_record_bound_synthesis_contract"
        or copied.get("mechanism_gate") != mechanism_gate()
        or copied.get("quality_gate") != quality_gate()
        or copied.get("protected_watchers") != watcher_snapshot()
        or copied.get("source_manifest") != manifest
        or copied.get("source_manifest_sha256") != payload_sha256(manifest)
        or copied.get("source_policy") != source_policy()
        or copied.get("authorization", {}).get("deepwidebench_dev64_exact220_or_sota") is not False
        or not sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.50.45 protocol drifted")
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "arm_order_vector", "build_protocol", "dependency_manifest",
    "forward_dependency_closure", "git", "mechanism_gate", "ordinary",
    "payload_sha256", "quality_gate", "query_vector", "seal", "sealed",
    "sha256", "source_policy", "task_vector", "validate_protocol",
    "validate_task_vector", "watcher_snapshot",
]
