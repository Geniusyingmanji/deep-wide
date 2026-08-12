"""Frozen contract for a fresh failure-observable same-response quality gate.

The only runtime change from V2.51.91 is content-free observability at the
runtime, conversion, and row-validation boundaries.  It cannot change a
response, prediction, route, budget, or effect.  All package identities are
explicit visible inputs selected from a fresh, history-disjoint CRAN cohort.
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

from . import v25188_export_failure_tolerant_same_response_runtime as runtime
from . import v25191_export_tolerant_quality_contract as base


DATE = "20260812"
PROTOCOL_ID = "v25195_failure_observable_quality_external_v1"
BUILD_AUDIT = Path(
    f"results/v25195_failure_observable_quality_build_audit_v1_{DATE}.json"
)
PROTOCOL = Path(
    f"results/v25195_failure_observable_quality_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v25195_failure_observable_quality_preactivation_audit_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v25195_failure_observable_quality_execution_start_v1_{DATE}.json"
)
FORWARD_RESULT = Path(
    f"results/v25195_failure_observable_quality_forward_result_v1_{DATE}.json"
)
FORWARD_AUDIT = Path(
    f"results/v25195_failure_observable_quality_forward_audit_v1_{DATE}.json"
)
EVALUATOR = Path("scripts/evaluate_v25195_failure_observable_quality.py")
EVALUATOR_TEST = Path(
    "tests/test_evaluate_v25195_failure_observable_quality.py"
)
EVALUATOR_PROTOCOL = Path(
    f"results/v25195_failure_observable_quality_evaluator_preregistration_v1_{DATE}.json"
)
RESULT = Path(
    f"results/v25195_failure_observable_quality_result_v1_{DATE}.json"
)
POSTAUDIT = Path(
    f"results/v25195_failure_observable_quality_postresult_audit_v1_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v25195_failure_observable_quality_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
POSTFREEZE_GOLD = OUTPUT_ROOT / "postfreeze_cran_gold.json"

CONTRACT = Path(
    "src/deepwide_agent/v25195_failure_observable_quality_contract.py"
)
RUNNER = Path("scripts/run_v25195_failure_observable_quality.py")
CONTROL = Path("scripts/control_v25195_failure_observable_quality.py")
TEST = Path("tests/test_v25195_failure_observable_quality.py")
SELECTION_SOURCE = Path(
    "scripts/audit_v25194_failure_observable_population_selection.py"
)
SELECTION_TEST = Path(
    "tests/test_audit_v25194_failure_observable_population_selection.py"
)
SELECTION_AUDIT = Path(
    "results/v25194_failure_observable_population_selection_audit_v1_20260812.json"
)
SELECTION_AUDIT_SHA256 = (
    "a6164e728ed8ab821369573e168eecd1607d388bab4259b539181201bbefbf55"
)
SELECTION_PARENT = "f7855aa3f26f866745d5d6bb0fd6eb225be8de1a"
IDENTITY_SELECTION_SHA256 = (
    "9f859633f191d531aaa0745845c2bf2feda624f00dc39cf713b870a0e1f29650"
)
FAILURE_OBSERVER = Path(
    "src/deepwide_agent/v25192_content_free_outer_failure_observer.py"
)
STAGED_EXECUTION = Path(
    "src/deepwide_agent/v25193_failure_observable_execution.py"
)
PARENT_FORWARD_RESULT = base.FORWARD_RESULT
PARENT_FORWARD_RESULT_SHA256 = (
    "80bc7e6950a03c0c5146778e387e36e3901953a5baf73afd940c08d5e9d3baf3"
)
PARENT_FORWARD_AUDIT = base.FORWARD_AUDIT
PARENT_FORWARD_AUDIT_SHA256 = (
    "704f88ea6d9d6c989f22e7acf38f5b710e7dcf2b5eb052f10ba130c190af096d"
)
FORWARD_SOURCES = (CONTRACT, RUNNER, FAILURE_OBSERVER, STAGED_EXECUTION)

TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 8
LEASE_PATH = base.LEASE_PATH
LEASE_OWNER = "v25195_failure_observable_quality_forward_v1"
LEASE_PURPOSE = "fresh_failure_observable_same_response_quality_gate_v1"
MODEL = copy.deepcopy(base.MODEL)
SEARCH = copy.deepcopy(base.SEARCH)
LIMITS = copy.deepcopy(base.LIMITS)
CLEANUP_RESERVE_SECONDS = base.CLEANUP_RESERVE_SECONDS
MINIMUM_MODEL_ATTEMPT_SECONDS = base.MINIMUM_MODEL_ATTEMPT_SECONDS
ARMS = runtime.ARMS
CONTROL_ARM = runtime.CONTROL_ARM
CANDIDATE_ARM = runtime.CANDIDATE_ARM
COLUMNS = ("Package", "Version", "License", "NeedsCompilation")
EXPECTED_WATCHERS = base.EXPECTED_WATCHERS

PACKAGES = (
    "D3GB",
    "DAISIE",
    "dataPreparation",
    "DBTC",
    "dendextend",
    "dendsort",
    "DescriptiveStats.OBeu",
    "designmatch",
    "dglm",
    "dHSIC",
    "DiallelAnalysisR",
    "DiceKriging",
    "DiceOptim",
    "diffobj",
    "DImodelsMulti",
    "dimRed",
    "DirectedClustering",
    "disagg2",
    "disagmethod",
    "disclapmix",
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
    if len(PACKAGES) != TASK_COUNT or len(set(PACKAGES)) != TASK_COUNT:
        raise RuntimeError("V2.51.95 package vector drifted")
    rows: list[dict[str, str]] = []
    for package in PACKAGES:
        opaque = "task_" + hashlib.sha256(
            f"v25195:{package}".encode()
        ).hexdigest()[:24]
        question = (
            "Retrieve the current public CRAN metadata record for the visible R "
            f"package <PACKAGE>{package}</PACKAGE>. Return exactly one Markdown "
            "table and no prose. Columns exactly: "
            + " | ".join(COLUMNS)
            + ". Use the canonical CRAN package spelling, current Version, "
            "complete License value, and NeedsCompilation exactly as published "
            "while collapsing ordinary whitespace. Preserve punctuation and "
            "separators that are part of a value. All values must come from the "
            "same visible package record. Use Unknown only when same-forward "
            "public pages do not establish a value."
        )
        rows.append({"opaque_id": opaque, "question": question})
    return validate_task_vector(rows)


def validate_task_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.51.95 task denominator drifted")
    output: list[dict[str, str]] = []
    for value, package in zip(values, PACKAGES, strict=True):
        question = value.get("question") if isinstance(value, Mapping) else None
        if (
            not isinstance(value, Mapping)
            or set(value) != {"opaque_id", "question"}
            or re.fullmatch(
                r"task_[0-9a-f]{24}", str(value.get("opaque_id") or "")
            )
            is None
            or not isinstance(question, str)
            or f"<PACKAGE>{package}</PACKAGE>" not in question
            or "Columns exactly: " + " | ".join(COLUMNS) not in question
            or r"\|" in question
            or "https://" in question
        ):
            raise ValueError("V2.51.95 natural visible task drifted")
        output.append(
            {"opaque_id": str(value["opaque_id"]), "question": question}
        )
    if len({row["opaque_id"] for row in output}) != TASK_COUNT:
        raise ValueError("V2.51.95 opaque identity collision")
    return output


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": [
            "opaque_id",
            "question",
            "same_forward_public_pages",
        ],
        "all_package_identities_are_explicit_visible_inputs": True,
        "population_is_history_disjoint_but_mechanism_enriched_not_unconditional": True,
        "visible_prompt_does_not_request_backslash_pipe_or_specific_encoding": True,
        "same_raw_response_shared_by_control_and_candidate": True,
        "control_is_frozen_parent_fallback_only_when_quote_repair_activates": True,
        "candidate_is_quote_aware_production_not_later_revision": True,
        "counterfactual_adds_no_model_search_fetch_token_context_or_network_effect": True,
        "outer_failure_stage_is_runtime_conversion_or_row_validation": True,
        "failure_code_is_finite_static_or_exception_class_fallback": True,
        "raw_exception_message_repr_traceback_or_frame_persisted_or_hashed": False,
        "failure_observer_changes_response_prediction_routing_budget_or_effect": False,
        "v25187_or_v25191_population_reuse": False,
        "v25191_retry_resume_or_selective_completion": False,
        "fixed_twenty_failure_as_zero_no_retry_resume_skip_or_replacement": True,
        "query_and_fetch_caps_use_fixed_terminal_denominator": True,
        "prediction_freeze_precedes_gold_evaluator_or_quality_decision": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "deepwidebench_dev64_exact220_leaderboard_or_sota_authorized": False,
    }


def mechanism_gate() -> dict[str, Any]:
    return {
        "fixed_task_denominator": TASK_COUNT,
        "terminal_tasks": TASK_COUNT,
        "completed_runtime_tasks": TASK_COUNT,
        "maximum_failure_as_zero_tasks": 0,
        "minimum_model_generated_tasks": 18,
        "maximum_fallback_tasks": 2,
        "minimum_same_raw_counterfactual_active_tasks": 10,
        "minimum_prediction_changed_tasks": 10,
        "active_equals_prediction_changed": True,
        "maximum_unsafe_public_export_failure_tasks": 0,
        "safe_public_export_failure_must_equal_safe_production_fallback": True,
        "maximum_outer_or_accounting_failure_tasks": 0,
        "maximum_terminal_effect_hard_failures": 0,
        "exact_physical_queries_total": 80,
        "maximum_physical_fetches_total": 280,
        "maximum_model_forwards_total": 80,
        "positive_signed_credit_count": 0,
    }


def quality_gate() -> dict[str, Any]:
    return {
        "fixed_denominator_all_valid": True,
        "minimum_candidate_exact_successes": 10,
        "minimum_candidate_exact_gain": 10,
        "candidate_exact_strictly_greater": True,
        "entity_row_item_column_composite_nonregression": True,
        "fallback_and_invalid_nonincrease": True,
        "scope_is_mechanism_enriched_cran_cohort_only": True,
        "deepwidebench_exact220_launch_only_after_pushed_postresult_audit_go": True,
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
            for candidate in base.base.base._module_candidates(relative, node):
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
        SELECTION_SOURCE,
        SELECTION_TEST,
        SELECTION_AUDIT,
        PARENT_FORWARD_RESULT,
        PARENT_FORWARD_AUDIT,
    }
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if path.suffix in {".py", ".json", ".md"} and SECRET.search(
            path.read_text(encoding="utf-8")
        ):
            raise RuntimeError("V2.51.95 credential literal in manifest")
        output[str(relative)] = sha256(path)
    return output


def validate_selection(root: Path, *, tracked: bool) -> dict[str, Any]:
    from scripts import (  # noqa: PLC0415
        audit_v25194_failure_observable_population_selection as audit,
    )

    path = ordinary(root, SELECTION_AUDIT, tracked=tracked)
    value = audit.validate_audit(json.loads(path.read_text(encoding="utf-8")))
    if (
        sha256(path) != SELECTION_AUDIT_SHA256
        or value["parent_commit"] != SELECTION_PARENT
        or value["ordered_identity_vector_sha256"]
        != IDENTITY_SELECTION_SHA256
        or value["identity_history_zero_hit_count"] != TASK_COUNT
        or value["preselection_enriched_for_license_literal_pipe"] is not True
        or value["preselection_is_unconditional_natural_population"] is not False
        or value["v25187_population_reuse"] is not False
        or value["v25191_population_reuse"] is not False
        or value["prior_external_population_reuse"] is not False
    ):
        raise RuntimeError("V2.51.95 selection audit invalid")
    return value


def _validate_parent(root: Path, *, tracked: bool) -> dict[str, Any]:
    result_path = ordinary(root, PARENT_FORWARD_RESULT, tracked=tracked)
    audit_path = ordinary(root, PARENT_FORWARD_AUDIT, tracked=tracked)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if (
        sha256(result_path) != PARENT_FORWARD_RESULT_SHA256
        or sha256(audit_path) != PARENT_FORWARD_AUDIT_SHA256
        or result.get("protocol_id") != base.PROTOCOL_ID
        or result.get("aggregate", {}).get("failure_as_zero_tasks") != 15
        or result.get("mechanism_decision", {}).get(
            "same_response_mechanism_gate_passed"
        )
        is not False
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get(
            "postfreeze_evaluator_implementation_and_protocol"
        )
        is not False
    ):
        raise RuntimeError("V2.51.95 V2.51.91 parent invalid")
    return {
        "forward_result_sha256": PARENT_FORWARD_RESULT_SHA256,
        "forward_audit_sha256": PARENT_FORWARD_AUDIT_SHA256,
        "frozen_failure_as_zero_tasks": 15,
        "mechanism_gate_passed": False,
        "evaluator_authorized": False,
    }


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
        (root / path).exists() or (root / path).is_symlink()
        for path in future
    ):
        raise RuntimeError("V2.51.95 future surface is not pristine")
    selection = validate_selection(root, tracked=tracked)
    parent = _validate_parent(root, tracked=tracked)
    manifest = dependency_manifest(root, tracked=tracked)
    tasks = task_vector()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25195_failure_observable_quality_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit_sha256": build_audit_sha256,
        "selection": {
            "path": str(SELECTION_AUDIT),
            "sha256": SELECTION_AUDIT_SHA256,
            "identity_vector_sha256": selection[
                "ordered_identity_vector_sha256"
            ],
            "history_zero_hit_count": selection[
                "identity_history_zero_hit_count"
            ],
            "mechanism_enriched": True,
            "unconditional_natural_population": False,
            "v25187_or_v25191_population_reuse": False,
        },
        "diagnosis_parent": parent,
        "population": {
            "task_count": TASK_COUNT,
            "task_vector_sha256": payload_sha256(tasks),
            "opaque_id_vector_sha256": payload_sha256(
                [row["opaque_id"] for row in tasks]
            ),
        },
        "execution": {
            "arms": list(ARMS),
            "only_treatment": "content_free_stage_and_static_failure_code_observability_without_behavior_change",
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "limits": copy.deepcopy(LIMITS),
            "single_atomic_forward_no_retry_resume_skip_or_replacement": True,
        },
        "mechanism_gate": mechanism_gate(),
        "quality_gate": quality_gate(),
        "protected_watchers": watcher_snapshot(),
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": source_policy(),
        "authorization": {
            "one_fresh_external_forward_after_separate_clean_pushed_start": True,
            "postfreeze_evaluator_implementation_only_after_pushed_forward_audit_go": True,
            "external_evaluator_now": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_rerun": False,
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
        raise RuntimeError("V2.51.95 protocol drifted")
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol",
    "dependency_manifest",
    "forward_dependency_closure",
    "mechanism_gate",
    "payload_sha256",
    "quality_gate",
    "seal",
    "sealed",
    "sha256",
    "source_policy",
    "task_vector",
    "validate_protocol",
    "validate_selection",
    "validate_task_vector",
    "watcher_snapshot",
]
