"""Fresh production-isomorphic external gate for V2.51.58.

The forward closure freezes only twenty new public package-description clues.
Package identities, endpoints, page bytes, gold values, evaluator code, and
quality outcomes remain absent until production and deterministic-final
predictions are terminal, frozen, audited, committed, and pushed.

For each task, the control is the first completed production prediction and
the candidate is the final prediction after the V2.51.58 verified-gain gate.
Both therefore share one plan, retrieval trace, fetched bytes, production
synthesis, and task deadline.  The candidate spends a second provider
candidate-selection call only after a same-forward source/identity/field gain.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v25068_quote_verified_external_contract as base
from . import v25165_observed_vertical_key_value_runtime as runtime


DATE = "20260812"
PROTOCOL_ID = "v25167_observed_vertical_external_matched_v1"
BUILD_AUDIT = Path(
    f"results/v25167_observed_vertical_external_build_audit_v1_{DATE}.json"
)
PROTOCOL = Path(
    f"results/v25167_observed_vertical_external_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v25167_observed_vertical_external_preactivation_audit_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v25167_observed_vertical_external_execution_start_v1_{DATE}.json"
)
FORWARD_RESULT = Path(
    f"results/v25167_observed_vertical_external_forward_result_v1_{DATE}.json"
)
FORWARD_AUDIT = Path(
    f"results/v25167_observed_vertical_external_forward_audit_v1_{DATE}.json"
)
EVALUATOR = Path("scripts/evaluate_v25167_observed_vertical_external.py")
EVALUATOR_TEST = Path(
    "tests/test_evaluate_v25167_observed_vertical_external.py"
)
EVALUATOR_PROTOCOL = Path(
    f"results/v25167_observed_vertical_external_evaluator_preregistration_v1_{DATE}.json"
)
RESULT = Path(
    f"results/v25167_observed_vertical_external_result_v1_{DATE}.json"
)
POSTAUDIT = Path(
    f"results/v25167_observed_vertical_external_postresult_audit_v1_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v25167_observed_vertical_external_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
POSTFREEZE_GOLD = OUTPUT_ROOT / "postfreeze_hidden_package_gold.json"

CONTRACT = Path(
    "src/deepwide_agent/v25167_observed_vertical_external_contract.py"
)
RUNNER = Path("scripts/run_v25167_observed_vertical_external.py")
CONTROL = Path("scripts/control_v25167_observed_vertical_external.py")
TEST = Path("tests/test_v25167_observed_vertical_external.py")
POPULATION_SELECTION_SOURCE = Path(
    "scripts/audit_v25167_population_selection.py"
)
POPULATION_SELECTION_TEST = Path(
    "tests/test_audit_v25167_population_selection.py"
)
HELPER = base.HELPER
POPULATION_SELECTION_AUDIT = Path(
    f"results/v25167_observed_vertical_population_selection_audit_v1_{DATE}.json"
)
POPULATION_SELECTION_AUDIT_SHA256 = (
    "ead8c78cc4242bd905fecbe088538af2a01c7838d0e405148936111c88d52e27"
)
PARENT_AUDIT = Path(
    "results/v25168_observed_vertical_preprotocol_audit_v1_20260812.json"
)
PARENT_AUDIT_SHA256 = (
    "0802b85f5540487e388632e5b58018d50f7148c903d7392395da6b071af64d74"
)
FORWARD_SOURCES = (CONTRACT, RUNNER, HELPER)

TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 8
FRESHNESS_PARENT_COMMIT = "7c66c70e"
LEASE_PATH = base.LEASE_PATH
LEASE_OWNER = "v25167_observed_vertical_external_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_vertical_key_value_candidate_matched_gate_v1"
MODEL = copy.deepcopy(base.MODEL)
SEARCH = copy.deepcopy(base.SEARCH)
LIMITS = copy.deepcopy(base.LIMITS)
CLEANUP_RESERVE_SECONDS = base.CLEANUP_RESERVE_SECONDS
MINIMUM_MODEL_ATTEMPT_SECONDS = base.MINIMUM_MODEL_ATTEMPT_SECONDS
RUNTIME_ARMS = runtime.ARMS
PRODUCTION_ARM = "production_prediction"
DETERMINISTIC_FINAL_ARM = "observed_vertical_final_prediction"
ARMS = (PRODUCTION_ARM, DETERMINISTIC_FINAL_ARM)
COLUMNS = ("Package", "Version", "License", "NeedsCompilation")
EXPECTED_WATCHERS = base.EXPECTED_WATCHERS
IDENTITY_SELECTION_SHA256 = (
    "4d984773c19f09beb615d7e20ba01d288a07f8b735ad91f59d4beff0efbdc359"
)

CLUES = (
    "an R framework for quantitative financial modelling and charting from market data",
    "an R package for performance and risk analytics of investment portfolios",
    "an R package for univariate GARCH model estimation forecasting and simulation",
    "an R package for multivariate GARCH model estimation forecasting and simulation",
    "an R package providing tidy forecasting models for time series",
    "an R package for feature extraction and statistics from tidy time series",
    "an R package supplying tidy temporal data frames with explicit time indexes",
    "an R package implementing unit root and cointegration analysis",
    "an R package estimating linear panel data models",
    "an R package for portfolio analysis allocation and numerical optimization",
    "an R package providing transaction infrastructure for trading strategy analysis",
    "an R package defining financial instruments for strategy and portfolio workflows",
    "an Rmetrics package for portfolio selection and optimization",
    "an R package estimating Markov switching GARCH models",
    "an R package for statistical analysis of extreme values",
    "an R package supporting quantitative risk management methods",
    "an R package for multivariate dependence modelling with copulas",
    "an R package for statistical inference with vine copulas",
    "an R package offering high performance vine copula modelling",
    "an R package for state space modelling and Kalman filtering with exponential family observations",
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
        raise RuntimeError("V2.51.67 clue vector drifted")
    rows: list[dict[str, str]] = []
    for clue in CLUES:
        opaque = "task_" + hashlib.sha256(
            f"v25167:{clue}".encode()
        ).hexdigest()[:24]
        question = (
            "Identify the single R package matching this public description clue: "
            f"<CLUE>{clue}</CLUE>. Resolve the package from public web pages, then "
            "use CRAN as the visible authority for current package metadata. Return "
            "exactly one Markdown table and no prose. Columns exactly: "
            + " | ".join(COLUMNS)
            + ". Use the canonical CRAN package spelling in Package. Version means the "
            "current CRAN version. Preserve the complete License value and preserve "
            "NeedsCompilation exactly as published while collapsing whitespace. All "
            "values must belong to the same package metadata record. Use Unknown "
            "only when same-forward fetched public pages do not establish a value."
        )
        rows.append({"opaque_id": opaque, "question": question})
    return validate_task_vector(rows)


def validate_task_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.51.67 task denominator drifted")
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
            raise ValueError("V2.51.67 visible task drifted")
        output.append(
            {"opaque_id": str(value["opaque_id"]), "question": value["question"]}
        )
    if len({row["opaque_id"] for row in output}) != TASK_COUNT:
        raise ValueError("V2.51.67 opaque identity collision")
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
        "offline_inferred_identity_vector_hashed_and_all_history_introduction_counts_zero": True,
        "offline_identity_plaintext_or_clue_identity_mapping_in_forward_closure": False,
        "population_endpoint_page_answer_model_or_evaluator_not_opened_before_freeze": True,
        "production_control_and_deterministic_candidate_final_share_one_forward": True,
        "one_visible_only_plan_and_grounded_plan_shared": True,
        "one_query_vector_search_response_fetch_union_and_page_bytes_shared": True,
        "production_prediction_is_terminal_before_revision_provider_effect": True,
        "revision_provider_effect_requires_same_forward_source_identity_field_gain": True,
        "no_gain_uses_local_identity_replay_not_provider_effect": True,
        "revision_or_posteffect_failure_preserves_production_prediction": True,
        "deterministic_candidates_use_only_same_forward_verified_delta_pages": True,
        "observer_and_parent_share_one_verified_delta_cache": True,
        "observer_failure_isolated_and_parent_continues": True,
        "observer_reason_buckets_change_admission_routing_prediction_or_budget": False,
        "disposition_counts_are_content_free_mutually_exclusive_and_exhaustive": True,
        "candidates_cover_bound_flat_json_pipe_inline_multiline_heading_and_vertical_key_value_records": True,
        "vertical_blocks_require_unique_primary_identity_and_unique_visible_keys": True,
        "vertical_quotes_are_same_page_unique_bounded_identity_to_field_spans": True,
        "every_candidate_is_preverified_and_selected_edit_reverified": True,
        "model_only_selects_candidate_ids_or_abstains": True,
        "conflicting_coordinates_are_omitted_and_duplicates_deterministically_collapsed": True,
        "deterministic_projection_preserves_row_identity_order_shape_and_unselected_cells": True,
        "candidate_selector_system_plus_user_characters_do_not_exceed_replaced_candidate_prompt": True,
        "query_fetch_context_token_wall_and_network_caps_not_expanded": True,
        "fixed_twenty_failure_as_zero_denominator_no_retry_resume_skip_or_replacement": True,
        "prediction_freeze_precedes_hidden_mapping_gold_evaluator_or_quality_decision": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "deepwidebench_dev64_exact220_leaderboard_or_sota_authorized": False,
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
        "maximum_unattributable_prediction_changed_tasks": 0,
        "maximum_positive_signed_credit_count": 0,
        "minimum_observer_completed_tasks": 4,
        "maximum_observer_failure_tasks": 0,
        "minimum_observed_page_count": 4,
        "minimum_vertical_block_tasks": 2,
        "minimum_vertical_blocks": 3,
        "minimum_nonzero_disposition_buckets": 1,
        "minimum_rejected_vertical_blocks": 1,
        "maximum_disposition_accounting_error": 0,
        "maximum_parent_behavior_drift_tasks": 0,
        "exact_physical_queries_per_completed_task": 4,
        "maximum_physical_fetches_per_completed_task": 14,
        "dense_reference_model_forwards_per_completed_task": 4,
        "maximum_sparse_model_forwards_total": 76,
        "minimum_model_forwards_saved_vs_dense": 4,
        "provider_forward_formula": "3_times_completed_plus_verified_gain",
        "candidate_prompt_selection_projection_and_parent_sparse_receipts_cross_bound": True,
        "observer_and_parent_share_one_verified_delta_cache": True,
        "disposition_counts_mutually_exclusive_exhaustive_and_parent_bound": True,
        "all_content_free_receipts_valid": True,
        "outer_failure_actual_effect_count_complete": True,
    }


def quality_gate() -> dict[str, Any]:
    return {
        "quality_evaluator_authorized": False,
        "localization_gate_cannot_establish_outer_utility": True,
        "successful_localization_only_authorizes_binding_successor_design": True,
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
        POPULATION_SELECTION_SOURCE,
        POPULATION_SELECTION_TEST,
        PARENT_AUDIT,
        POPULATION_SELECTION_AUDIT,
    }
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.51.67 credential literal in source manifest")
        output[str(relative)] = sha256(path)
    return output


def validate_population_selection_audit(
    root: Path, *, tracked: bool
) -> dict[str, Any]:
    path = ordinary(root, POPULATION_SELECTION_AUDIT, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    unsigned = dict(value) if isinstance(value, dict) else {}
    audit_seal = unsigned.pop("audit_payload_sha256", None)
    parent = git(root, "rev-parse", "--verify", FRESHNESS_PARENT_COMMIT + "^{commit}")
    if (
        not isinstance(value, dict)
        or sha256(path) != POPULATION_SELECTION_AUDIT_SHA256
        or value.get("role")
        != "v25167_observed_vertical_population_selection_aggregate_audit"
        or value.get("parent_commit") != parent
        or value.get("identity_count") != TASK_COUNT
        or value.get("unique_identity_count") != TASK_COUNT
        or value.get("ordered_identity_vector_sha256") != IDENTITY_SELECTION_SHA256
        or value.get("identity_history_introduction_hit_total") != 0
        or value.get("identity_history_zero_hit_count") != TASK_COUNT
        or value.get("identity_plaintext_or_item_hash_persisted") is not False
        or value.get("clue_to_identity_mapping_persisted") is not False
        or value.get("network_endpoint_page_value_model_or_evaluator_access")
        is not False
        or value.get("selection_uses_repository_history_only") is not True
        or value.get(
            "v25141_v25145_v25149_v25153_v25157_v25160_population_reuse"
        )
        is not False
        or value.get(
            "population_frozen_for_single_future_observed_vertical_disposition_gate"
        )
        is not True
        or value.get("vertical_binding_policy_change") is not False
        or value.get(
            "external_protocol_activation_evaluator_or_deepwidebench_authorized"
        )
        is not False
        or value.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or audit_seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.51.67 population selection audit invalid")
    return value


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
        raise RuntimeError("V2.51.67 future surface is not pristine")
    if sha256(root / PARENT_AUDIT) != PARENT_AUDIT_SHA256:
        raise RuntimeError("V2.51.67 parent preprotocol audit drifted")
    if (
        POPULATION_SELECTION_AUDIT_SHA256 == "TO_BE_FROZEN"
        or sha256(root / POPULATION_SELECTION_AUDIT)
        != POPULATION_SELECTION_AUDIT_SHA256
    ):
        raise RuntimeError("V2.51.67 population selection audit drifted")
    selection = validate_population_selection_audit(root, tracked=tracked)
    manifest = dependency_manifest(root, tracked=tracked)
    tasks = task_vector()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25167_observed_vertical_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit_sha256": build_audit_sha256,
        "parent": {
            "preprotocol_authorization_audit_path": str(PARENT_AUDIT),
            "preprotocol_authorization_audit_sha256": PARENT_AUDIT_SHA256,
        },
        "freshness": {
            "parent_commit": FRESHNESS_PARENT_COMMIT,
            "parent_history_exact_clue_literal_zero_hit": True,
            "clue_vector_sha256": payload_sha256(CLUES),
            "offline_identity_vector_sha256": IDENTITY_SELECTION_SHA256,
            "offline_identity_count": selection["identity_count"],
            "offline_identity_history_introduction_hit_count": selection[
                "identity_history_introduction_hit_total"
            ],
            "selection_audit_path": str(POPULATION_SELECTION_AUDIT),
            "selection_audit_sha256": POPULATION_SELECTION_AUDIT_SHA256,
            "offline_identity_plaintext_or_mapping_in_forward_closure": False,
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
            "only_treatment": "behavior_preserving_content_free_vertical_admission_disposition_observation_on_shared_verified_delta_cache",
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
            "one_fresh_observed_vertical_external_forward_after_separate_clean_pushed_start": True,
            "binding_successor_design_only_after_prediction_freeze_and_pushed_forward_audit_go": True,
            "evaluator": False,
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
        raise RuntimeError("V2.51.67 protocol drifted")
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
    "validate_population_selection_audit",
    "validate_task_vector",
    "watcher_snapshot",
]
