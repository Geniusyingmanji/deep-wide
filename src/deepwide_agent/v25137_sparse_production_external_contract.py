"""Fresh production-isomorphic external gate for V2.51.35.

The forward closure freezes only twenty new public package-description clues.
Package identities, endpoints, page bytes, gold values, evaluator code, and
quality outcomes remain absent until both production and sparse-final
predictions are terminal, frozen, audited, committed, and pushed.

For each task, the control is the first completed production prediction and
the candidate is the final prediction after the V2.51.35 verified-gain gate.
Both therefore share one plan, retrieval trace, fetched bytes, production
synthesis, and task deadline.  The candidate spends a second provider
synthesis only after a same-forward source/identity/field-bound gain.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v25068_quote_verified_external_contract as base
from . import v25135_sparse_production_runtime as runtime


DATE = "20260812"
PROTOCOL_ID = "v25137_sparse_production_external_matched_r2"
BUILD_AUDIT = Path(
    f"results/v25137_sparse_production_external_build_audit_r2_{DATE}.json"
)
PROTOCOL = Path(
    f"results/v25137_sparse_production_external_preregistration_r2_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v25137_sparse_production_external_preactivation_audit_r2_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v25137_sparse_production_external_execution_start_r2_{DATE}.json"
)
FORWARD_RESULT = Path(
    f"results/v25137_sparse_production_external_forward_result_r2_{DATE}.json"
)
FORWARD_AUDIT = Path(
    f"results/v25137_sparse_production_external_forward_audit_r2_{DATE}.json"
)
EVALUATOR = Path("scripts/evaluate_v25137_sparse_production_external.py")
EVALUATOR_TEST = Path(
    "tests/test_evaluate_v25137_sparse_production_external.py"
)
EVALUATOR_PROTOCOL = Path(
    f"results/v25137_sparse_production_external_evaluator_preregistration_r2_{DATE}.json"
)
RESULT = Path(
    f"results/v25137_sparse_production_external_result_r2_{DATE}.json"
)
POSTAUDIT = Path(
    f"results/v25137_sparse_production_external_postresult_audit_r2_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v25137_sparse_production_external_r2_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
POSTFREEZE_GOLD = OUTPUT_ROOT / "postfreeze_hidden_package_gold.json"

CONTRACT = Path(
    "src/deepwide_agent/v25137_sparse_production_external_contract.py"
)
RUNNER = Path("scripts/run_v25137_sparse_production_external.py")
CONTROL = Path("scripts/control_v25137_sparse_production_external.py")
TEST = Path("tests/test_v25137_sparse_production_external.py")
HELPER = base.HELPER
PARENT_AUDIT = Path(
    "results/v25136_sparse_production_build_audit_v1_20260811.json"
)
PARENT_AUDIT_SHA256 = (
    "4860dbf3d9f81ea9983b66f121f52c2f86797a1cde9b2c9a2f8b5a268985ad92"
)
SUPERSEDED_BUILD_AUDIT = Path(
    f"results/v25137_sparse_production_external_build_audit_v1_{DATE}.json"
)
SUPERSEDED_BUILD_AUDIT_SHA256 = (
    "80fa745315e5f3cbda987f9b2638a6222161c7171e2f2bd293cf2e84ed818889"
)
SUPERSEDED_PROTOCOL = Path(
    f"results/v25137_sparse_production_external_preregistration_v1_{DATE}.json"
)
SUPERSEDED_PROTOCOL_SHA256 = (
    "81819cc5c3e72aaf67596a124274efe2f52dc0103a4e267f89f3a6cb93da55f8"
)
SUPERSEDED_PREAUDIT = Path(
    f"results/v25137_sparse_production_external_preactivation_audit_v1_{DATE}.json"
)
SUPERSEDED_EXECUTION_START = Path(
    f"results/v25137_sparse_production_external_execution_start_v1_{DATE}.json"
)
SUPERSEDED_FORWARD_RESULT = Path(
    f"results/v25137_sparse_production_external_forward_result_v1_{DATE}.json"
)
FORWARD_SOURCES = (CONTRACT, RUNNER, HELPER)

TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 8
FRESHNESS_PARENT_COMMIT = "ac0cdb79"
LEASE_PATH = base.LEASE_PATH
LEASE_OWNER = "v25137_sparse_production_external_forward_r2"
LEASE_PURPOSE = "fresh_label_blind_sparse_production_matched_gate_r2"
MODEL = copy.deepcopy(base.MODEL)
SEARCH = copy.deepcopy(base.SEARCH)
LIMITS = copy.deepcopy(base.LIMITS)
CLEANUP_RESERVE_SECONDS = base.CLEANUP_RESERVE_SECONDS
MINIMUM_MODEL_ATTEMPT_SECONDS = base.MINIMUM_MODEL_ATTEMPT_SECONDS
RUNTIME_ARMS = runtime.ARMS
PRODUCTION_ARM = "production_prediction"
SPARSE_FINAL_ARM = "sparse_final_prediction"
ARMS = (PRODUCTION_ARM, SPARSE_FINAL_ARM)
COLUMNS = ("Package", "Version", "Released", "Requires")
EXPECTED_WATCHERS = base.EXPECTED_WATCHERS

CLUES = (
    "a Python library for creating and extracting 7zip archives",
    "a pure Python library for reading and writing Microsoft Compound File Binary files",
    "a Python library for reading and writing metadata in audio files",
    "a Python library for manipulating PDF files including splitting merging cropping and transforming pages",
    "a Python library for generating PDF documents using a canvas and a document layout toolkit",
    "a Python library for reading and writing Excel xlsx files",
    "a Python library for creating Excel xlsx files with charts and formatting",
    "a Python library for reading legacy Excel xls files",
    "a Python library for writing legacy Excel xls files",
    "a Python library for parsing and creating iCalendar files",
    "a Python library for parsing and creating vCard files",
    "a Python library for processing internationalized domain names",
    "a Python library for extracting registrable domains using the public suffix list",
    "a Python library for parsing browser user agent strings",
    "a Python binding for detecting file types through libmagic",
    "a fast fuzzy string matching library for Python backed by C++",
    "a Python library for transliterating Unicode text into ASCII",
    "a Python library for generating URL slugs from Unicode text",
    "a Python implementation of Markdown that converts text to HTML",
    "a Python library for sanitizing HTML and stripping unsafe markup",
)

SECRET = base.SECRET
payload_sha256 = base.payload_sha256
sha256 = base.sha256
seal = base.seal
sealed = base.sealed
git = base.git
ordinary = base.ordinary
watcher_snapshot = base.watcher_snapshot


def task_vector() -> list[dict[str, str]]:
    if len(CLUES) != TASK_COUNT or len(set(CLUES)) != TASK_COUNT:
        raise RuntimeError("V2.51.37 clue vector drifted")
    rows: list[dict[str, str]] = []
    for clue in CLUES:
        opaque = "task_" + hashlib.sha256(
            f"v25137:{clue}".encode()
        ).hexdigest()[:24]
        question = (
            "Identify the single Python package matching this public description clue: "
            f"<CLUE>{clue}</CLUE>. Resolve the package from public web pages, then "
            "use PyPI as the visible authority for current release metadata. Return "
            "exactly one Markdown table and no prose. Columns exactly: "
            + " | ".join(COLUMNS)
            + ". Use the canonical PyPI project name in Package. Version means the "
            "current release version. Render Released in YYYY-MM-DD form and preserve "
            "the Python requirement expression in Requires while collapsing whitespace. "
            "All values must belong to the same package and release record. Use Unknown "
            "only when same-forward fetched public pages do not establish a value."
        )
        rows.append({"opaque_id": opaque, "question": question})
    return validate_task_vector(rows)


def validate_task_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.51.37 task denominator drifted")
    output: list[dict[str, str]] = []
    for value, clue in zip(values, CLUES, strict=True):
        if (
            not isinstance(value, Mapping)
            or set(value) != {"opaque_id", "question"}
            or re.fullmatch(
                r"task_[0-9a-f]{24}", str(value.get("opaque_id") or "")
            )
            is None
            or not isinstance(value.get("question"), str)
            or f"<CLUE>{clue}</CLUE>" not in value["question"]
            or "Columns exactly: " + " | ".join(COLUMNS)
            not in value["question"]
            or "https://" in value["question"]
        ):
            raise ValueError("V2.51.37 visible task drifted")
        output.append(
            {"opaque_id": str(value["opaque_id"]), "question": value["question"]}
        )
    if len({row["opaque_id"] for row in output}) != TASK_COUNT:
        raise ValueError("V2.51.37 opaque identity collision")
    return output


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": [
            "opaque_id",
            "question",
            "same_forward_public_pages",
        ],
        "forward_closure_contains_description_clues_but_no_hidden_target_mapping": True,
        "fresh_population_selected_by_parent_history_exact_clue_literal_zero_scan_only": True,
        "population_endpoint_page_answer_model_or_evaluator_not_opened_before_freeze": True,
        "production_control_and_sparse_final_share_one_forward": True,
        "one_visible_only_plan_and_grounded_plan_shared": True,
        "one_query_vector_search_response_fetch_union_and_page_bytes_shared": True,
        "production_prediction_is_terminal_before_revision_provider_effect": True,
        "revision_provider_effect_requires_same_forward_source_identity_field_gain": True,
        "no_gain_uses_local_identity_replay_not_provider_effect": True,
        "revision_or_posteffect_failure_preserves_production_prediction": True,
        "query_fetch_context_token_wall_and_network_caps_not_expanded": True,
        "fixed_twenty_failure_as_zero_denominator_no_retry_resume_skip_or_replacement": True,
        "prediction_freeze_precedes_hidden_mapping_gold_evaluator_or_quality_decision": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "deepwidebench_dev64_exact220_leaderboard_or_sota_authorized": False,
        "superseded_r1_protocol_never_reached_preaudit_start_or_forward": True,
    }


def mechanism_gate() -> dict[str, Any]:
    return {
        "fixed_task_denominator": 20,
        "terminal_tasks": 20,
        "completed_runtime_tasks": 20,
        "production_model_generated_tasks": 20,
        "maximum_failure_as_zero_tasks": 0,
        "maximum_outer_or_accounting_failure_tasks": 0,
        "maximum_terminal_transport_timeout_helper_or_model_hard_failures": 0,
        "maximum_revision_failure_tasks": 0,
        "maximum_post_effect_failure_tasks": 0,
        "maximum_parent_prediction_loss_tasks": 0,
        "minimum_verified_gain_tasks": 4,
        "maximum_verified_gain_tasks": 16,
        "minimum_revision_provider_forward_tasks": 4,
        "minimum_identity_replay_tasks": 4,
        "minimum_attributable_prediction_changed_tasks": 3,
        "maximum_unattributable_prediction_changed_tasks": 0,
        "exact_physical_queries_per_completed_task": 4,
        "maximum_physical_fetches_per_completed_task": 14,
        "dense_reference_model_forwards_per_completed_task": 4,
        "maximum_sparse_model_forwards_total": 76,
        "minimum_model_forwards_saved_vs_dense": 4,
        "provider_forward_formula": "3_times_completed_plus_verified_gain",
        "all_content_free_receipts_valid": True,
        "outer_failure_actual_effect_count_complete": True,
    }


def quality_gate() -> dict[str, Any]:
    return {
        "fixed_denominator": 20,
        "candidate_exact_strict_gain": True,
        "candidate_entity_row_item_column_composite_nonregression": True,
        "invalid_or_fallback_nonincrease": True,
        "same_forward_search_fetch_and_production_prediction": True,
        "candidate_revision_only_after_verified_gain": True,
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
            for candidate in base._module_candidates(relative, node):
                if (root / candidate).is_file() and not (
                    root / candidate
                ).is_symlink():
                    pending.append(candidate)
    return tuple(sorted(observed, key=str))


def dependency_manifest(root: Path, *, tracked: bool) -> dict[str, str]:
    relatives = {
        *forward_dependency_closure(root),
        CONTROL,
        TEST,
        PARENT_AUDIT,
        SUPERSEDED_BUILD_AUDIT,
        SUPERSEDED_PROTOCOL,
    }
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.51.37 credential literal in source manifest")
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
        raise RuntimeError("V2.51.37 future surface is not pristine")
    if sha256(root / PARENT_AUDIT) != PARENT_AUDIT_SHA256:
        raise RuntimeError("V2.51.37 parent build audit drifted")
    if (
        sha256(root / SUPERSEDED_BUILD_AUDIT)
        != SUPERSEDED_BUILD_AUDIT_SHA256
        or sha256(root / SUPERSEDED_PROTOCOL) != SUPERSEDED_PROTOCOL_SHA256
        or any(
            (root / path).exists() or (root / path).is_symlink()
            for path in (
                SUPERSEDED_PREAUDIT,
                SUPERSEDED_EXECUTION_START,
                SUPERSEDED_FORWARD_RESULT,
            )
        )
    ):
        raise RuntimeError("V2.51.37 superseded r1 activation barrier drifted")
    manifest = dependency_manifest(root, tracked=tracked)
    tasks = task_vector()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25137_sparse_production_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit_sha256": build_audit_sha256,
        "parent": {
            "clean_build_audit_path": str(PARENT_AUDIT),
            "clean_build_audit_sha256": PARENT_AUDIT_SHA256,
        },
        "superseded_unactivated_protocol": {
            "build_audit_path": str(SUPERSEDED_BUILD_AUDIT),
            "build_audit_sha256": SUPERSEDED_BUILD_AUDIT_SHA256,
            "protocol_path": str(SUPERSEDED_PROTOCOL),
            "protocol_sha256": SUPERSEDED_PROTOCOL_SHA256,
            "preaudit_created": False,
            "execution_start_created": False,
            "forward_created": False,
            "population_consumed": False,
        },
        "freshness": {
            "parent_commit": FRESHNESS_PARENT_COMMIT,
            "parent_history_exact_clue_literal_zero_hit": True,
            "clue_vector_sha256": payload_sha256(CLUES),
            "hidden_target_mapping_present_in_forward_closure": False,
            "endpoint_page_value_model_or_evaluator_opened_during_selection": False,
        },
        "population": {
            "task_count": TASK_COUNT,
            "task_vector_sha256": payload_sha256(tasks),
            "opaque_id_vector_sha256": payload_sha256(
                [row["opaque_id"] for row in tasks]
            ),
        },
        "execution": {
            "arms": list(ARMS),
            "runtime_internal_arms": list(RUNTIME_ARMS),
            "only_treatment": "verified_gain_conditional_revision_provider_effect",
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "limits": copy.deepcopy(LIMITS),
            "physical_model_forward_cap": 4,
            "no_gain_physical_model_forward_cap": 3,
            "physical_query_cap": 4,
            "physical_fetch_cap": 14,
            "single_atomic_forward_no_retry_resume_skip_or_replacement": True,
        },
        "mechanism_gate": mechanism_gate(),
        "quality_gate": quality_gate(),
        "protected_watchers": watcher_snapshot(),
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": source_policy(),
        "authorization": {
            "one_fresh_sparse_production_external_forward_after_separate_clean_pushed_start": True,
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
        raise RuntimeError("V2.51.37 protocol drifted")
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
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
