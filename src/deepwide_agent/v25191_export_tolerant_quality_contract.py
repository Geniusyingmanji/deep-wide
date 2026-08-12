"""Frozen contract for a same-response quote-aware external quality gate."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v25183_quote_aware_external_contract as base
from . import v25188_export_failure_tolerant_same_response_runtime as runtime


DATE = "20260812"
PROTOCOL_ID = "v25191_export_tolerant_quality_external_v1"
BUILD_AUDIT = Path(f"results/v25191_export_tolerant_quality_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25191_export_tolerant_quality_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25191_export_tolerant_quality_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25191_export_tolerant_quality_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25191_export_tolerant_quality_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25191_export_tolerant_quality_forward_audit_v1_{DATE}.json")
EVALUATOR = Path("scripts/evaluate_v25191_export_tolerant_quality.py")
EVALUATOR_TEST = Path("tests/test_evaluate_v25191_export_tolerant_quality.py")
EVALUATOR_PROTOCOL = Path(f"results/v25191_export_tolerant_quality_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v25191_export_tolerant_quality_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v25191_export_tolerant_quality_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v25191_export_tolerant_quality_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
POSTFREEZE_GOLD = OUTPUT_ROOT / "postfreeze_cran_gold.json"

CONTRACT = Path("src/deepwide_agent/v25191_export_tolerant_quality_contract.py")
RUNNER = Path("scripts/run_v25191_export_tolerant_quality.py")
CONTROL = Path("scripts/control_v25191_export_tolerant_quality.py")
TEST = Path("tests/test_v25191_export_tolerant_quality.py")
SELECTION_SOURCE = Path(
    "scripts/audit_v25190_export_tolerant_quality_population_selection.py"
)
SELECTION_TEST = Path(
    "tests/test_audit_v25190_export_tolerant_quality_population_selection.py"
)
SELECTION_AUDIT = Path(
    "results/v25190_export_tolerant_quality_population_selection_audit_v1_20260812.json"
)
SELECTION_AUDIT_SHA256 = (
    "b9acfbe8a860ee3eb0d323a6324c8765df826ffa817d55c5d955da4aedb0766e"
)
SELECTION_PARENT = "5f8f8f1ac4b78d010cd8269bb34cb9bdac5ce672"
IDENTITY_SELECTION_SHA256 = (
    "65f2dfbf035cf34d1c04ded80c0ece16d92fc5b70cc76b15e4ea96700b322f01"
)
DIAGNOSIS = Path("results/v25189_v25187_outer_failure_diagnosis_v1_20260812.json")
DIAGNOSIS_SHA256 = (
    "6cb82c52dd52a4fb727315a4156609807176bc02867183183ba21f51a783a36a"
)
FORWARD_SOURCES = (CONTRACT, RUNNER)

TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 8
LEASE_PATH = base.LEASE_PATH
LEASE_OWNER = "v25191_export_tolerant_quality_forward_v1"
LEASE_PURPOSE = "fresh_export_failure_tolerant_same_response_quality_gate_v1"
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
    "bigtabulate", "bigalgebra", "BinNonNor", "BivUnifBin", "bnstruct",
    "BNPmix", "caffsim", "bcmaps", "bsgof", "bs4Dash", "bsreg",
    "BoomSpikeSlab", "BVAR", "calibrateBinary", "CatEncoders",
    "CausalImpact", "ChannelAttribution", "ChannelAttributionApp",
    "caRamel", "catcont",
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
        raise RuntimeError("V2.51.91 package vector drifted")
    rows = []
    for package in PACKAGES:
        opaque = "task_" + hashlib.sha256(f"v25191:{package}".encode()).hexdigest()[:24]
        question = (
            "Retrieve the current public CRAN metadata record for the visible R "
            f"package <PACKAGE>{package}</PACKAGE>. Return exactly one Markdown "
            "table and no prose. Columns exactly: " + " | ".join(COLUMNS) + ". "
            "Use the canonical CRAN package spelling, current Version, complete "
            "License value, and NeedsCompilation exactly as published while "
            "collapsing ordinary whitespace. Preserve punctuation and separators "
            "that are part of a value. All values must come from the same visible "
            "package record. Use Unknown only when same-forward public pages do "
            "not establish a value."
        )
        rows.append({"opaque_id": opaque, "question": question})
    return validate_task_vector(rows)


def validate_task_vector(values: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.51.91 task denominator drifted")
    output = []
    for value, package in zip(values, PACKAGES, strict=True):
        question = value.get("question") if isinstance(value, Mapping) else None
        if (
            not isinstance(value, Mapping)
            or set(value) != {"opaque_id", "question"}
            or re.fullmatch(r"task_[0-9a-f]{24}", str(value.get("opaque_id") or "")) is None
            or not isinstance(question, str)
            or f"<PACKAGE>{package}</PACKAGE>" not in question
            or "Columns exactly: " + " | ".join(COLUMNS) not in question
            or r"\|" in question
            or "https://" in question
        ):
            raise ValueError("V2.51.91 natural visible task drifted")
        output.append({"opaque_id": str(value["opaque_id"]), "question": question})
    if len({row["opaque_id"] for row in output}) != TASK_COUNT:
        raise ValueError("V2.51.91 opaque identity collision")
    return output


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "all_package_identities_are_explicit_visible_inputs": True,
        "population_is_history_disjoint_but_mechanism_enriched_not_unconditional": True,
        "visible_prompt_does_not_request_backslash_pipe_or_specific_encoding": True,
        "same_raw_response_shared_by_control_and_candidate": True,
        "control_is_frozen_parent_fallback_only_when_quote_repair_activates": True,
        "candidate_is_quote_aware_production_not_later_revision": True,
        "counterfactual_adds_no_model_search_fetch_token_context_or_network_effect": True,
        "active_parent_export_failure_allowed_only_with_validated_safe_production_fallback": True,
        "v25187_population_reuse": False,
        "v25187_failed_forward_retry_resume_or_selective_completion": False,
        "fixed_twenty_failure_as_zero_no_retry_resume_skip_or_replacement": True,
        "prediction_freeze_precedes_gold_evaluator_or_quality_decision": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "deepwidebench_dev64_exact220_leaderboard_or_sota_authorized": False,
    }


def mechanism_gate() -> dict[str, Any]:
    return {
        "fixed_task_denominator": 20,
        "terminal_tasks": 20,
        "completed_runtime_tasks": 20,
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
        "exact_physical_queries_per_completed_task": 4,
        "maximum_physical_fetches_per_completed_task": 14,
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
            for candidate in base.base._module_candidates(relative, node):
                if (root / candidate).is_file() and not (root / candidate).is_symlink():
                    pending.append(candidate)
    return tuple(sorted(observed, key=str))


def dependency_manifest(root: Path, *, tracked: bool) -> dict[str, str]:
    relatives = {
        *forward_dependency_closure(root), CONTROL, TEST, SELECTION_SOURCE,
        SELECTION_TEST, SELECTION_AUDIT, DIAGNOSIS,
    }
    output = {}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.51.91 credential literal in manifest")
        output[str(relative)] = sha256(path)
    return output


def validate_selection(root: Path, *, tracked: bool) -> dict[str, Any]:
    from scripts import audit_v25190_export_tolerant_quality_population_selection as audit

    path = ordinary(root, SELECTION_AUDIT, tracked=tracked)
    value = audit.validate_audit(json.loads(path.read_text(encoding="utf-8")))
    if (
        sha256(path) != SELECTION_AUDIT_SHA256
        or value["parent_commit"] != SELECTION_PARENT
        or value["ordered_identity_vector_sha256"] != IDENTITY_SELECTION_SHA256
        or value["identity_history_zero_hit_count"] != TASK_COUNT
        or value["preselection_enriched_for_license_literal_pipe"] is not True
        or value["preselection_is_unconditional_natural_population"] is not False
        or value["v25187_population_reuse"] is not False
        or value["prior_external_population_reuse"] is not False
    ):
        raise RuntimeError("V2.51.91 selection audit invalid")
    return value


def build_protocol(
    root: Path,
    *,
    now: int,
    tracked: bool,
    require_pristine: bool,
    build_audit_sha256: str,
) -> dict[str, Any]:
    future = (PROTOCOL, PREAUDIT, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT,
              EVALUATOR, EVALUATOR_TEST, EVALUATOR_PROTOCOL, RESULT, POSTAUDIT,
              OUTPUT_ROOT)
    if require_pristine and any((root / p).exists() or (root / p).is_symlink() for p in future):
        raise RuntimeError("V2.51.91 future surface is not pristine")
    diagnosis = json.loads(
        ordinary(root, DIAGNOSIS, tracked=tracked).read_text(encoding="utf-8")
    )
    if (
        sha256(root / DIAGNOSIS) != DIAGNOSIS_SHA256
        or diagnosis.get("audit_valid") is not True
        or diagnosis.get("findings") != []
        or diagnosis.get("authorization", {}).get("fresh_disjoint_successor_design")
        is not True
        or diagnosis.get("authorization", {}).get(
            "old_population_retry_resume_skip_replacement_or_selective_rerun"
        )
        is not False
    ):
        raise RuntimeError("V2.51.91 V2.51.89 diagnosis parent invalid")
    selection = validate_selection(root, tracked=tracked)
    manifest = dependency_manifest(root, tracked=tracked)
    tasks = task_vector()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25191_export_tolerant_quality_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit_sha256": build_audit_sha256,
        "selection": {
            "path": str(SELECTION_AUDIT),
            "sha256": SELECTION_AUDIT_SHA256,
            "identity_vector_sha256": selection["ordered_identity_vector_sha256"],
            "history_zero_hit_count": selection["identity_history_zero_hit_count"],
            "mechanism_enriched": True,
            "unconditional_natural_population": False,
            "v25187_population_reuse": False,
        },
        "diagnosis_parent": {
            "path": str(DIAGNOSIS),
            "sha256": DIAGNOSIS_SHA256,
            "fresh_disjoint_successor_design": True,
            "old_population_retry_resume_or_selective_completion": False,
        },
        "population": {
            "task_count": TASK_COUNT,
            "task_vector_sha256": payload_sha256(tasks),
            "opaque_id_vector_sha256": payload_sha256([row["opaque_id"] for row in tasks]),
        },
        "execution": {
            "arms": list(ARMS),
            "only_treatment": "deterministic_quote_aware_parse_of_the_same_raw_production_response_with_parent_valid_safe_export_fallback",
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
        raise RuntimeError("V2.51.91 protocol drifted")
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol", "dependency_manifest", "forward_dependency_closure",
    "mechanism_gate", "payload_sha256", "quality_gate", "seal", "sealed",
    "sha256", "source_policy", "task_vector", "validate_protocol",
    "validate_selection", "validate_task_vector", "watcher_snapshot",
]
