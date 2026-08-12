"""Fresh label-blind mechanism gate for the V2.51.80 runtime.

All twenty package identities are explicit visible task inputs.  They were
selected only because repository history had no prior occurrence and their
public CRAN License fields exercise literal-pipe representation.  There is no
hidden identity mapping, benchmark label, gold value, evaluator, or score in
the forward closure.  This gate measures mechanism and reliability only.
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
from . import v25180_quote_aware_production_runtime as runtime


DATE = "20260812"
PROTOCOL_ID = "v25183_quote_aware_external_mechanism_r2"
BUILD_AUDIT = Path(
    f"results/v25183_quote_aware_external_build_audit_r2_{DATE}.json"
)
PROTOCOL = Path(
    f"results/v25183_quote_aware_external_preregistration_r2_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v25183_quote_aware_external_preactivation_audit_r2_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v25183_quote_aware_external_execution_start_r2_{DATE}.json"
)
FORWARD_RESULT = Path(
    f"results/v25183_quote_aware_external_forward_result_r2_{DATE}.json"
)
FORWARD_AUDIT = Path(
    f"results/v25183_quote_aware_external_forward_audit_r2_{DATE}.json"
)
EVALUATOR = Path("scripts/evaluate_v25183_quote_aware_external.py")
EVALUATOR_TEST = Path("tests/test_evaluate_v25183_quote_aware_external.py")
EVALUATOR_PROTOCOL = Path(
    f"results/v25183_quote_aware_external_evaluator_preregistration_v1_{DATE}.json"
)
RESULT = Path(f"results/v25183_quote_aware_external_result_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v25183_quote_aware_external_postresult_audit_v1_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v25183_quote_aware_external_r2_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
POSTFREEZE_GOLD = OUTPUT_ROOT / "postfreeze_hidden_gold.json"

CONTRACT = Path("src/deepwide_agent/v25183_quote_aware_external_contract.py")
RUNNER = Path("scripts/run_v25183_quote_aware_external.py")
CONTROL = Path("scripts/control_v25183_quote_aware_external.py")
TEST = Path("tests/test_v25183_quote_aware_external.py")
HELPER = base.HELPER
BUILD_PARENT = Path(
    "results/v25181_quote_aware_runtime_build_audit_v1_20260812.json"
)
BUILD_PARENT_SHA256 = (
    "be1177e3627c9a229fb3c3f8af5424b473eebda6614b5a2d488af49c43379c14"
)
POPULATION_SOURCE = Path(
    "scripts/audit_v25182_quote_aware_population_selection.py"
)
POPULATION_TEST = Path(
    "tests/test_audit_v25182_quote_aware_population_selection.py"
)
POPULATION_AUDIT = Path(
    "results/v25182_quote_aware_population_selection_audit_v1_20260812.json"
)
POPULATION_AUDIT_SHA256 = (
    "927e84bda363ea38f6b9d0ccd8ae63ae610ebc55c1c413ff07df3ef10d41af38"
)
FORWARD_SOURCES = (CONTRACT, RUNNER, HELPER)

TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 8
LEASE_PATH = base.LEASE_PATH
LEASE_OWNER = "v25183_quote_aware_external_forward_r2"
LEASE_PURPOSE = "fresh_label_blind_quote_aware_mechanism_gate_r2"
MODEL = copy.deepcopy(base.MODEL)
SEARCH = copy.deepcopy(base.SEARCH)
LIMITS = copy.deepcopy(base.LIMITS)
CLEANUP_RESERVE_SECONDS = base.CLEANUP_RESERVE_SECONDS
MINIMUM_MODEL_ATTEMPT_SECONDS = base.MINIMUM_MODEL_ATTEMPT_SECONDS
RUNTIME_ARMS = runtime.ARMS
PRODUCTION_ARM = "quote_aware_production_prediction"
DETERMINISTIC_FINAL_ARM = "quote_aware_final_prediction"
ARMS = (PRODUCTION_ARM, DETERMINISTIC_FINAL_ARM)
COLUMNS = ("Package", "Version", "License", "NeedsCompilation")
EXPECTED_WATCHERS = base.EXPECTED_WATCHERS
IDENTITY_SELECTION_SHA256 = (
    "074db8b82176a9176a2cd0c6a5f4d02ee4354f36e02c4369795a4d1b3b8791b5"
)

PACKAGES = (
    "abess",
    "alphahull",
    "backports",
    "bamlss",
    "base64enc",
    "bayesmix",
    "BayesX",
    "benchmarkme",
    "betareg",
    "binaryGP",
    "bit64",
    "brunnermunzel",
    "adnuts",
    "ahnr",
    "ANN2",
    "antaresRead",
    "AnthropMMD",
    "ApacheLogProcessor",
    "apng",
    "asciiruler",
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
        raise RuntimeError("V2.51.83 package vector drifted")
    rows: list[dict[str, str]] = []
    for package in PACKAGES:
        opaque = "task_" + hashlib.sha256(
            f"v25183:{package}".encode()
        ).hexdigest()[:24]
        question = (
            "Retrieve the current public CRAN metadata record for the visible R "
            f"package <PACKAGE>{package}</PACKAGE>. Return exactly one Markdown "
            "table and no prose. Columns exactly: "
            + " | ".join(COLUMNS)
            + ". Use the canonical CRAN package spelling in Package, the current "
            "CRAN Version, the complete CRAN License, and NeedsCompilation exactly "
            "as published while collapsing ordinary whitespace. When License "
            "contains a literal vertical bar, encode each content pipe inside that "
            r"cell as the Markdown escape sequence \| so it remains one semantic "
            "cell. All values must come from the same visible package record. Use "
            "Unknown only when same-forward fetched public pages do not establish "
            "a value."
        )
        rows.append({"opaque_id": opaque, "question": question})
    return validate_task_vector(rows)


def validate_task_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.51.83 task denominator drifted")
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
            or r"escape sequence \|" not in question
            or "https://" in question
        ):
            raise ValueError("V2.51.83 visible task drifted")
        output.append(
            {"opaque_id": str(value["opaque_id"]), "question": question}
        )
    if len({row["opaque_id"] for row in output}) != TASK_COUNT:
        raise ValueError("V2.51.83 opaque identity collision")
    return output


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "all_package_identities_are_explicit_visible_task_inputs": True,
        "hidden_identity_mapping_present_in_forward_closure": False,
        "population_selected_by_repository_history_zero_hit_only": True,
        "prior_external_population_reuse": False,
        "only_treatment_is_unambiguous_single_backslash_escaped_pipe_repair": True,
        "repair_runs_only_after_frozen_production_contract_rejection": True,
        "parent_plan_retrieval_candidate_projection_failure_and_budget_logic_unchanged": True,
        "raw_accepted_parent_prediction_cost_effect_and_receipts_byte_exact": True,
        "public_loader_values_match_only_pipe_adjacent_whitespace_canonicalization": True,
        "new_moved_or_extra_entity_fails_candidate_publication_closed": True,
        "observer_repair_or_public_export_failure_preserves_completed_production": True,
        "fixed_twenty_failure_as_zero_denominator_no_retry_resume_skip_or_replacement": True,
        "prediction_freeze_precedes_any_later_quality_or_benchmark_decision": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "evaluator_deepwidebench_leaderboard_or_sota_authorized": False,
    }


def mechanism_gate() -> dict[str, Any]:
    return {
        "fixed_task_denominator": 20,
        "terminal_tasks": 20,
        "completed_runtime_tasks": 20,
        "maximum_failure_as_zero_tasks": 0,
        "minimum_production_model_generated_tasks": 18,
        "maximum_production_fallback_tasks": 2,
        "raw_observer_entry_tasks": 20,
        "raw_observer_completed_tasks": 20,
        "maximum_raw_observer_failure_tasks": 0,
        "minimum_quote_aware_repair_attempt_tasks": 12,
        "minimum_quote_aware_repair_applied_tasks": 12,
        "maximum_quote_aware_repair_failure_tasks": 0,
        "public_export_attempt_equals_repair_applied": True,
        "public_export_completed_equals_repair_applied": True,
        "maximum_public_export_failure_tasks": 0,
        "maximum_public_export_fallback_tasks": 0,
        "maximum_parent_behavior_drift_tasks": 0,
        "maximum_outer_or_accounting_failure_tasks": 0,
        "maximum_terminal_effect_hard_failures": 0,
        "exact_physical_queries_per_completed_task": 4,
        "maximum_physical_fetches_per_completed_task": 14,
        "maximum_sparse_model_forwards_total": 80,
        "all_content_free_receipts_valid": True,
    }


def quality_gate() -> dict[str, Any]:
    return {
        "quality_evaluator_authorized": False,
        "mechanism_gate_cannot_establish_outer_utility": True,
        "successful_mechanism_gate_only_authorizes_independent_natural_quality_gate_design": True,
        "deepwidebench_or_sota": False,
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
        BUILD_PARENT,
        POPULATION_SOURCE,
        POPULATION_TEST,
        POPULATION_AUDIT,
    }
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.51.83 credential literal in manifest")
        output[str(relative)] = sha256(path)
    return output


def validate_population_audit(root: Path, *, tracked: bool) -> dict[str, Any]:
    from scripts import audit_v25182_quote_aware_population_selection as audit

    path = ordinary(root, POPULATION_AUDIT, tracked=tracked)
    value = audit.validate_audit(json.loads(path.read_text(encoding="utf-8")))
    if (
        sha256(path) != POPULATION_AUDIT_SHA256
        or value["ordered_identity_vector_sha256"] != IDENTITY_SELECTION_SHA256
        or value["identity_count"] != TASK_COUNT
        or value["identity_history_zero_hit_count"] != TASK_COUNT
        or value["prior_external_population_reuse"] is not False
    ):
        raise RuntimeError("V2.51.83 population audit invalid")
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
        OUTPUT_ROOT,
    )
    if require_pristine and any(
        (root / path).exists() or (root / path).is_symlink() for path in future
    ):
        raise RuntimeError("V2.51.83 future surface is not pristine")
    if sha256(root / BUILD_PARENT) != BUILD_PARENT_SHA256:
        raise RuntimeError("V2.51.83 build parent drifted")
    selection = validate_population_audit(root, tracked=tracked)
    manifest = dependency_manifest(root, tracked=tracked)
    tasks = task_vector()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25183_quote_aware_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit_sha256": build_audit_sha256,
        "parents": {
            "runtime_build_audit_path": str(BUILD_PARENT),
            "runtime_build_audit_sha256": BUILD_PARENT_SHA256,
            "population_audit_path": str(POPULATION_AUDIT),
            "population_audit_sha256": POPULATION_AUDIT_SHA256,
        },
        "population": {
            "task_count": TASK_COUNT,
            "task_vector_sha256": payload_sha256(tasks),
            "opaque_id_vector_sha256": payload_sha256(
                [row["opaque_id"] for row in tasks]
            ),
            "identity_vector_sha256": selection[
                "ordered_identity_vector_sha256"
            ],
            "identity_history_zero_hit_count": selection[
                "identity_history_zero_hit_count"
            ],
            "all_identities_visible_not_hidden_mapping": True,
        },
        "execution": {
            "arms": list(ARMS),
            "runtime_internal_arms": list(RUNTIME_ARMS),
            "only_treatment": "conditional_unambiguous_single_backslash_escaped_pipe_repair_and_safe_csv_publication",
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "limits": copy.deepcopy(LIMITS),
            "physical_model_forward_cap": 4,
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
            "one_fresh_quote_aware_mechanism_forward_after_separate_clean_pushed_start": True,
            "independent_natural_quality_gate_design_only_after_pushed_forward_audit_go": True,
            "external_evaluator": False,
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
        raise RuntimeError("V2.51.83 protocol drifted")
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
    "validate_population_audit",
    "validate_protocol",
    "validate_task_vector",
    "watcher_snapshot",
]
