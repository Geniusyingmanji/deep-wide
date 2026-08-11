"""Unconditional fixed-denominator successor for the CRAN bridge gate.

The forward begins after all twenty preparations are terminal, independent of
how many are ready.  Each unready task emits two identical canonical fallback
predictions with zero model calls; each ready task receives the unchanged
paired representation treatment.  Natural-ready coverage remains a strict
post-forward mechanism gate and cannot suppress the fixed prediction set.
"""

from __future__ import annotations

import ast
import copy
import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v25052_cran_fixed_denominator_contract as base


DATE = "20260811"
PROTOCOL_ID = "v25053_cran_unconditional_fixed_denominator_quality_v1"
BUILD_AUDIT = Path(f"results/v25053_cran_unconditional_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25053_cran_unconditional_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25053_cran_unconditional_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25053_cran_unconditional_execution_start_v1_{DATE}.json")
PARSER_READINESS = Path(f"results/v25053_cran_unconditional_readiness_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25053_cran_unconditional_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25053_cran_unconditional_forward_audit_v1_{DATE}.json")
EVALUATOR = Path("scripts/evaluate_v25053_cran_unconditional.py")
EVALUATOR_TEST = Path("tests/test_evaluate_v25053_cran_unconditional.py")
EVALUATOR_PROTOCOL = Path(f"results/v25053_cran_unconditional_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v25053_cran_unconditional_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v25053_cran_unconditional_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v25053_cran_unconditional_v1_{DATE}")
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
PUBLIC_SNAPSHOT = OUTPUT_ROOT / "postprediction_public_cran_snapshot.jsonl"

SOURCE = Path("src/deepwide_agent/v25049_page_self_identified_record.py")
CONTRACT = Path("src/deepwide_agent/v25053_cran_unconditional_denominator_contract.py")
RUNNER = Path("scripts/run_v25053_cran_unconditional.py")
CONTROL = Path("scripts/control_v25053_cran_unconditional.py")
TEST = Path("tests/test_v25053_cran_unconditional.py")
FORWARD_SOURCES = (SOURCE, CONTRACT, RUNNER)

ARMS = base.ARMS
CONTROL_ARM, CANDIDATE_ARM = ARMS
TASK_COUNT = 20
MINIMUM_READY_TASKS = 15
EXECUTOR_CONCURRENCY = base.EXECUTOR_CONCURRENCY
MODEL_CONCURRENCY = base.MODEL_CONCURRENCY
EVIDENCE_CHAR_CAP = base.EVIDENCE_CHAR_CAP
MODEL_OUTPUT_TOKENS = base.MODEL_OUTPUT_TOKENS
TASK_DEADLINE_SECONDS = base.TASK_DEADLINE_SECONDS
FETCH_TIMEOUT = base.FETCH_TIMEOUT
MAX_RESPONSE_BYTES = base.MAX_RESPONSE_BYTES
MINIMUM_PREDICTION_CHANGES = base.MINIMUM_PREDICTION_CHANGES
ENDPOINT = base.ENDPOINT
MODEL = base.MODEL
LEASE_PATH = base.LEASE_PATH
EXPECTED_WATCHERS = base.EXPECTED_WATCHERS
SECRET = base.SECRET
FRESHNESS_PARENT_COMMIT = "00bd6066f64672ac79dfe8f6031fb7882b8c0b06"

PROJECTS = (
    "admiralophtha", "admiralonco", "admiralvaccine", "admiralpeds",
    "admiralneuro", "admiralmetabolic", "formatters", "scda",
    "nestcolor", "shinyvalidate", "shinybusy", "shinyscreenshot",
    "shinyWidgets", "reactable.extras", "deckgl", "mapdeck", "mapgl",
    "mapboxapi", "maptiles", "rglwidget",
)
PREDECESSOR_PROJECTS = tuple(dict.fromkeys((*base.PROJECTS, *base.PREDECESSOR_PROJECTS)))
COLUMNS = base.COLUMNS
FALLBACK_TABLE = base.FALLBACK_TABLE

payload_sha256 = base.payload_sha256
sha256 = base.sha256
seal = base.seal
sealed = base.sealed
git = base.git
ordinary = base.ordinary
watcher_snapshot = base.watcher_snapshot


def task_vector() -> list[dict[str, str]]:
    if (
        len(PROJECTS) != TASK_COUNT
        or len(set(PROJECTS)) != TASK_COUNT
        or set(PROJECTS) & set(PREDECESSOR_PROJECTS)
    ):
        raise RuntimeError("V2.50.53 project vector drifted")
    question = (
        "Using only the supplied public CRAN package page, identify the package "
        "and return exactly one Markdown table and no prose. Include exactly one "
        "row. Columns must be: Package | Version | Published | License. Preserve "
        "the canonical package spelling and field values while collapsing "
        "whitespace. Use Unknown only when the supplied page does not establish "
        "a value."
    )
    return [
        {
            "opaque_id": "task_" + hashlib.sha256(
                f"v25053:{project}".encode()
            ).hexdigest()[:24],
            "question": question,
        }
        for project in PROJECTS
    ]


def endpoint_vector() -> list[str]:
    return [
        f"https://cran.r-project.org/web/packages/{project}/index.html"
        for project in PROJECTS
    ]


def arm_order_vector() -> list[list[str]]:
    ranked = sorted(
        range(TASK_COUNT),
        key=lambda index: hashlib.sha256(
            f"v25053-arm-order:{task_vector()[index]['opaque_id']}".encode()
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
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_cran_html_bytes"],
        "fresh_population_zero_overlap_with_all_predecessors": True,
        "final_population_endpoint_page_answer_model_or_evaluator_not_probed_before_freeze": True,
        "all_twenty_preparations_terminal_before_any_model_call": True,
        "no_batch_ready_count_controls_forward_activation": True,
        "unready_tasks_receive_paired_identical_failure_as_zero_without_model_call": True,
        "ready_coverage_is_postforward_mechanism_gate_only": True,
        "no_retry_resume_replacement_or_selective_rerun": True,
        "ordinary_html_decoded_by_production_html_to_document": True,
        "question_does_not_enumerate_or_name_row_identity": True,
        "identity_discovered_from_same_page_url_title_and_visible_surface": True,
        "same_exact_response_and_decoded_page_underlie_both_ready_arms": True,
        "ready_task_evidence_lengths_positive_equal_between_arms_and_at_most_cap": True,
        "same_prompt_model_output_cap_attempt_count_and_deadline": True,
        "only_treatment_on_ready_tasks_is_evidence_representation": True,
        "fixed_twenty_task_and_forty_prediction_denominator": True,
        "public_snapshot_published_only_after_all_predictions": True,
        "prediction_freeze_before_evaluator_module_or_quality_decision": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
        "entropy_or_information_gain_assigns_credit_or_routes": False,
        "deepwidebench_dev64_exact220_leaderboard_or_sota_authorized": False,
    }


def gates() -> dict[str, Any]:
    return {
        "readiness": {
            "terminal_preparations": TASK_COUNT,
            "ready_count_activation_threshold": None,
            "model_calls_before_all_preparations_terminal": 0,
        },
        "mechanism": {
            "terminal_tasks": TASK_COUNT,
            "terminal_arm_predictions": TASK_COUNT * len(ARMS),
            "minimum_ready_tasks": MINIMUM_READY_TASKS,
            "maximum_preparation_failure_tasks": TASK_COUNT - MINIMUM_READY_TASKS,
            "model_successes_and_attempts_equal_ready_tasks": True,
            "paired_preparation_failures_equal_fallback_tasks": True,
            "maximum_evidence_chars_per_arm": TASK_COUNT * EVIDENCE_CHAR_CAP,
            "minimum_prediction_changed_tasks": MINIMUM_PREDICTION_CHANGES,
        },
        "quality": {
            "fixed_denominator": TASK_COUNT,
            "preparation_failures_score_zero_in_both_arms": True,
            "candidate_exact_strict_gain": True,
            "entity_row_item_column_composite_nonregression": True,
            "invalid_and_fallback_nonincrease": True,
        },
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
            raise RuntimeError("V2.50.53 credential literal in source manifest")
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
        PROTOCOL, PREAUDIT, EXECUTION_START, PARSER_READINESS, FORWARD_RESULT,
        FORWARD_AUDIT, EVALUATOR, EVALUATOR_TEST, EVALUATOR_PROTOCOL, RESULT,
        POSTAUDIT, OUTPUT_ROOT,
    )
    if require_pristine and any((root / path).exists() or (root / path).is_symlink() for path in future):
        raise RuntimeError("V2.50.53 future surface is not pristine")
    manifest = dependency_manifest(root, tracked=tracked)
    value = {
        "artifact_version": 1,
        "role": "v25053_cran_unconditional_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit_sha256": build_audit_sha256,
        "freshness": {
            "parent_commit": FRESHNESS_PARENT_COMMIT,
            "parent_history_literal_zero_hit_projects": list(PROJECTS),
            "zero_overlap_with_predecessor_projects": True,
            "endpoint_page_answer_model_or_evaluator_opened_during_selection": False,
            "predecessor_no_go_retried_or_resumed": False,
        },
        "population": {
            "task_count": TASK_COUNT,
            "project_vector_sha256": payload_sha256(PROJECTS),
            "task_vector_sha256": payload_sha256(task_vector()),
            "endpoint_vector_sha256": payload_sha256(endpoint_vector()),
            "arm_order_vector_sha256": payload_sha256(arm_order_vector()),
        },
        "execution": {
            "arms": list(ARMS),
            "only_treatment_on_ready_tasks": "raw_decoded_prefix_vs_page_self_identified_record_representation",
            "control_plane_change_from_v25052": "remove_batch_ready_activation_threshold",
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_concurrency": MODEL_CONCURRENCY,
            "fetch_attempts_per_task": 1,
            "ready_count_activation_threshold": None,
            "postforward_minimum_ready_tasks": MINIMUM_READY_TASKS,
            "evidence_character_cap_per_ready_arm": EVIDENCE_CHAR_CAP,
            "model_calls_per_ready_arm": 1,
            "model_calls_per_unready_arm": 0,
            "model_output_tokens": MODEL_OUTPUT_TOKENS,
            "task_deadline_seconds": TASK_DEADLINE_SECONDS,
            "fetch_timeout": list(FETCH_TIMEOUT),
            "max_response_bytes": MAX_RESPONSE_BYTES,
            "model_endpoint": ENDPOINT,
            "model": MODEL,
        },
        "gates": gates(),
        "protected_watchers": watcher_snapshot(),
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": source_policy(),
        "authorization": {
            "one_unconditional_fixed_denominator_forward_after_clean_pushed_start": True,
            "evaluator_only_after_prediction_freeze_and_pushed_forward_audit": True,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_population_replacement_or_selective_revaluation": False,
        },
    }
    return seal(value, "protocol_payload_sha256")


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    manifest = dependency_manifest(root, tracked=True)
    expected = build_protocol(
        root,
        now=int(copied.get("created_at_unix", -1)),
        tracked=True,
        require_pristine=False,
        build_audit_sha256=sha256(root / BUILD_AUDIT),
    )
    if (
        set(copied) != set(expected)
        or copied != expected
        or copied.get("artifact_version") != 1
        or copied.get("source_manifest") != manifest
        or copied.get("source_manifest_sha256") != payload_sha256(manifest)
        or not sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.50.53 protocol drifted")
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "arm_order_vector", "build_protocol", "dependency_manifest", "endpoint_vector",
    "forward_dependency_closure", "gates", "git", "ordinary", "payload_sha256",
    "seal", "sealed", "sha256", "source_policy", "task_vector",
    "validate_protocol", "watcher_snapshot",
]
