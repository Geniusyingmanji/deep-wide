"""Fresh external contract for grounded resolve-then-expand retrieval.

Only public description clues are frozen in the forward closure.  The hidden
package identities, canonical endpoints, page contents, field values, gold,
and evaluator do not exist here.  Runtime receives exactly ``opaque_id`` and
the visible question; first-wave public pages must ground any package target
used by the second wave.
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
from . import v25119_grounded_target_record_paired_runtime as runtime


DATE = "20260811"
PROTOCOL_ID = "v25121_grounded_target_record_external_mechanism_v1"
BUILD_AUDIT = Path(
    f"results/v25121_grounded_target_record_external_build_audit_v1_{DATE}.json"
)
PROTOCOL = Path(
    f"results/v25121_grounded_target_record_external_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v25121_grounded_target_record_external_preactivation_audit_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v25121_grounded_target_record_external_execution_start_v1_{DATE}.json"
)
FORWARD_RESULT = Path(
    f"results/v25121_grounded_target_record_external_forward_result_v1_{DATE}.json"
)
FORWARD_AUDIT = Path(
    f"results/v25121_grounded_target_record_external_forward_audit_v1_{DATE}.json"
)
EVALUATOR = Path("scripts/evaluate_v25121_grounded_target_record_external.py")
EVALUATOR_TEST = Path(
    "tests/test_evaluate_v25121_grounded_target_record_external.py"
)
EVALUATOR_PROTOCOL = Path(
    f"results/v25121_grounded_target_record_external_evaluator_preregistration_v1_{DATE}.json"
)
RESULT = Path(
    f"results/v25121_grounded_target_record_external_result_v1_{DATE}.json"
)
POSTAUDIT = Path(
    f"results/v25121_grounded_target_record_external_postresult_audit_v1_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v25121_grounded_target_record_external_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
POSTFREEZE_GOLD = OUTPUT_ROOT / "postfreeze_hidden_package_gold.jsonl"

CONTRACT = Path(
    "src/deepwide_agent/v25121_grounded_target_record_external_contract.py"
)
RUNNER = Path("scripts/run_v25121_grounded_target_record_external.py")
CONTROL = Path("scripts/control_v25121_grounded_target_record_external.py")
TEST = Path("tests/test_v25121_grounded_target_record_external.py")
HELPER = base.HELPER
PARENT_AUDIT = Path(
    "results/v25120_grounded_target_record_build_audit_v1_20260811.json"
)
PARENT_AUDIT_SHA256 = (
    "e5dc2db5a4e90ead9cf5a23b591bc41646c9bab95b1b06f004e5a428d5fe4b6a"
)
FORWARD_SOURCES = (CONTRACT, RUNNER, HELPER)

TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 4
FRESHNESS_PARENT_COMMIT = "08eb8785"
LEASE_PATH = base.LEASE_PATH
LEASE_OWNER = "v25121_grounded_target_record_external_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_grounded_target_record_mechanism_gate"
MODEL = copy.deepcopy(base.MODEL)
SEARCH = copy.deepcopy(base.SEARCH)
LIMITS = copy.deepcopy(base.LIMITS)
CLEANUP_RESERVE_SECONDS = base.CLEANUP_RESERVE_SECONDS
MINIMUM_MODEL_ATTEMPT_SECONDS = base.MINIMUM_MODEL_ATTEMPT_SECONDS
ARMS = runtime.ARMS
CONTROL_ARM, CANDIDATE_ARM = ARMS
COLUMNS = (
    "Package",
    "Version",
    "Released",
    "Requires",
)
EXPECTED_WATCHERS = base.EXPECTED_WATCHERS

# These are description-only clues.  Hidden identities are intentionally not
# present in this module or any other forward source.
CLUES = (
    "a library for creating decorators with a stable function signature and optional caller arguments",
    "a library that dynamically creates Python functions while preserving a requested signature",
    "a lightweight framework that turns Python functions into dependency-aware pipelines",
    "an extremely lightweight compatibility layer for dataframe libraries",
    "a fast Excel reader for Python whose parsing core is written in Rust",
    "a dataframe modelling and validation library combining Polars and Pydantic",
    "a data validation library for pandas-like dataframe objects",
    "a fast and flexible library for converting structured data models",
    "a serializer and deserializer focused on dataclasses and attrs classes",
    "a fast asynchronous Python web framework powered by a Rust runtime",
    "a dependency injection framework built around explicit scopes",
    "a small Python dependency injection container with constructor resolution",
    "a dependency injection container designed to require almost no application changes",
    "a flexible Python service locator with typed service registration",
    "an asyncio-compatible scheduler for limiting concurrency and request rate",
    "an efficient leaky-bucket rate limiter for asyncio",
    "a generator-based library for composing asynchronous iteration streams",
    "a type-driven framework for building command-line interfaces",
    "a tool that automatically generates a Textual interface for a Click command-line app",
    "a terminal user-interface framework with widgets animations layouts and mouse support",
)

_SECRET_PREFIXES = (
    "gh" + "p_",
    "github_" + "pat_",
    "tvly-" + "dev-",
    "s" + "k-",
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in _SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)

payload_sha256 = base.payload_sha256
sha256 = base.sha256
seal = base.seal
sealed = base.sealed
git = base.git
ordinary = base.ordinary
watcher_snapshot = base.watcher_snapshot


def task_vector() -> list[dict[str, str]]:
    if len(CLUES) != TASK_COUNT or len(set(CLUES)) != TASK_COUNT:
        raise RuntimeError("V2.51.21 clue vector drifted")
    rows: list[dict[str, str]] = []
    for clue in CLUES:
        opaque = "task_" + hashlib.sha256(
            f"v25121:{clue}".encode()
        ).hexdigest()[:24]
        question = (
            "Identify the single Python package matching this public description clue: "
            f"<CLUE>{clue}</CLUE>. "
            "Resolve the package from public web pages, then use PyPI as the visible "
            "authority for release metadata. Return exactly one Markdown table and no "
            "prose. Columns exactly: "
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
        raise ValueError("V2.51.21 task denominator drifted")
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
            raise ValueError("V2.51.21 visible task drifted")
        output.append(
            {"opaque_id": str(value["opaque_id"]), "question": value["question"]}
        )
    if len({row["opaque_id"] for row in output}) != TASK_COUNT:
        raise ValueError("V2.51.21 opaque identity collision")
    return output


def arm_order_vector() -> list[list[str]]:
    tasks = task_vector()
    ranked = sorted(
        range(TASK_COUNT),
        key=lambda index: hashlib.sha256(
            f"v25121-arm-order:{tasks[index]['opaque_id']}".encode()
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
        "forward_closure_contains_description_clues_but_no_hidden_target_mapping": True,
        "fresh_population_selected_by_parent_history_exact_clue_literal_zero_scan_only": True,
        "population_endpoint_page_answer_model_or_evaluator_not_opened_before_freeze": True,
        "one_visible_only_plan_shared_by_both_arms": True,
        "first_two_queries_and_at_most_six_pages_execute_once": True,
        "one_first_wave_grounded_plan_shared_by_both_arms": True,
        "all_nonvisible_pivots_and_targets_must_be_verbatim_first_wave_phrases": True,
        "invalid_grounded_plan_is_exact_legacy_second_wave_handoff": True,
        "one_grounded_second_wave_query_vector_and_search_response_shared": True,
        "control_preserves_stable_complete_frontier_prefix": True,
        "candidate_uses_only_target_authority_field_or_record_url_signals": True,
        "page_body_query_provider_score_prediction_and_answer_do_not_rank_urls": True,
        "two_arm_selected_url_union_fetched_once": True,
        "unselected_page_text_never_enters_arm_evidence": True,
        "selection_change_needs_actual_target_field_page_gain_for_mechanism_credit": True,
        "prediction_change_needs_mechanism_exposure_for_attributable_credit": True,
        "both_arms_have_equal_evidence_character_budget": True,
        "per_arm_cap_three_models_four_queries_ten_fetches": True,
        "paired_physical_cap_four_models_four_queries_fourteen_fetches": True,
        "twenty_task_concurrency_with_four_global_model_slots": True,
        "robust_late_page_bound_search_client_required": True,
        "fixed_twenty_failure_as_zero_denominator_no_retry_resume_skip_or_replacement": True,
        "prediction_freeze_precedes_hidden_mapping_gold_evaluator_or_quality_decision": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "deepwidebench_dev64_exact220_leaderboard_or_sota_authorized": False,
    }


def mechanism_gate() -> dict[str, Any]:
    return {
        "fixed_task_denominator": TASK_COUNT,
        "terminal_tasks": TASK_COUNT,
        "completed_runtime_tasks": TASK_COUNT,
        "both_arms_model_success_tasks": TASK_COUNT,
        "minimum_first_wave_completed_tasks": 18,
        "minimum_grounded_plan_attempted_tasks": 18,
        "minimum_grounded_plan_strategy_applied_tasks": 8,
        "minimum_second_wave_completed_tasks": 18,
        "minimum_selection_strategy_eligible_tasks": 6,
        "minimum_selection_changed_tasks": 4,
        "minimum_positive_target_field_page_gain_tasks": 4,
        "minimum_positive_target_field_pair_gain_tasks": 4,
        "minimum_retrieval_mechanism_engaged_tasks": 4,
        "minimum_prediction_changed_tasks": 3,
        "minimum_attributable_prediction_changed_tasks": 3,
        "maximum_outer_or_accounting_failure_tasks": 0,
        "maximum_terminal_transport_timeout_helper_or_model_hard_failures": 0,
        "maximum_candidate_arm_model_failures_over_control": 0,
        "exact_physical_queries_per_completed_task": 4,
        "maximum_physical_fetches_per_completed_task": 14,
        "maximum_physical_model_logical_calls_per_completed_task": 4,
        "maximum_effective_model_logical_calls_per_completed_arm": 3,
        "equal_control_candidate_evidence_characters_per_task": True,
        "frozen_arm_order_exact": True,
    }


def quality_gate() -> dict[str, Any]:
    return {
        "fixed_denominator": TASK_COUNT,
        "candidate_exact_strict_gain": True,
        "candidate_composite_nonregression": True,
        "entity_row_item_column_nonregression": True,
        "invalid_or_fallback_nonincrease": True,
        "same_search_fetch_evidence_length_and_effective_model_budget": True,
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
                if (root / candidate).is_file() and not (root / candidate).is_symlink():
                    pending.append(candidate)
    return tuple(sorted(observed, key=str))


def dependency_manifest(root: Path, *, tracked: bool) -> dict[str, str]:
    relatives = {*forward_dependency_closure(root), CONTROL, TEST, PARENT_AUDIT}
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.51.21 credential literal in source manifest")
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
        raise RuntimeError("V2.51.21 future surface is not pristine")
    if sha256(root / PARENT_AUDIT) != PARENT_AUDIT_SHA256:
        raise RuntimeError("V2.51.21 parent build audit drifted")
    manifest = dependency_manifest(root, tracked=tracked)
    tasks = task_vector()
    value = {
        "artifact_version": 1,
        "role": "v25121_grounded_target_record_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit_sha256": build_audit_sha256,
        "parent": {"path": str(PARENT_AUDIT), "sha256": PARENT_AUDIT_SHA256},
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
            "arm_order_vector_sha256": payload_sha256(arm_order_vector()),
        },
        "execution": {
            "arms": list(ARMS),
            "only_treatment": "grounded_target_record_frontier_selection",
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "limits": copy.deepcopy(LIMITS),
            "physical_paired_model_call_cap": 4,
            "physical_query_cap": 4,
            "physical_fetch_cap": 14,
            "effective_model_call_cap_per_arm": 3,
            "single_atomic_forward_no_retry_resume_skip_or_replacement": True,
        },
        "mechanism_gate": mechanism_gate(),
        "quality_gate": quality_gate(),
        "protected_watchers": watcher_snapshot(),
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": source_policy(),
        "authorization": {
            "one_external_forward_after_separate_clean_pushed_start": True,
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
        raise RuntimeError("V2.51.21 protocol drifted")
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "arm_order_vector",
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
