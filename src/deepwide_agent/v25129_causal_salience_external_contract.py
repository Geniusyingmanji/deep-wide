"""Fresh external contract for causally coupled target-record salience.

Only twenty new public description clues are frozen in the forward closure.
Hidden package identities, endpoints, pages, values, gold, and evaluator code
are absent.  V2.51.27 preserves query compatibility, prioritizes each arm's
second-wave evidence without changing prompt length, and forbids a prediction
difference without an actual target-field-page gain.  The consumed V2.51.21
and V2.51.25 populations are never resumed.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v25121_grounded_target_record_external_contract as parent
from . import v25127_causally_coupled_target_record_runtime as runtime


DATE = "20260811"
PROTOCOL_ID = "v25129_causal_salience_external_mechanism_v1"
BUILD_AUDIT = Path(
    f"results/v25129_causal_salience_external_build_audit_v1_{DATE}.json"
)
PROTOCOL = Path(
    f"results/v25129_causal_salience_external_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v25129_causal_salience_external_preactivation_audit_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v25129_causal_salience_external_execution_start_v1_{DATE}.json"
)
FORWARD_RESULT = Path(
    f"results/v25129_causal_salience_external_forward_result_v1_{DATE}.json"
)
FORWARD_AUDIT = Path(
    f"results/v25129_causal_salience_external_forward_audit_v1_{DATE}.json"
)
EVALUATOR = Path("scripts/evaluate_v25129_causal_salience_external.py")
EVALUATOR_TEST = Path(
    "tests/test_evaluate_v25129_causal_salience_external.py"
)
EVALUATOR_PROTOCOL = Path(
    f"results/v25129_causal_salience_external_evaluator_preregistration_v1_{DATE}.json"
)
RESULT = Path(f"results/v25129_causal_salience_external_result_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v25129_causal_salience_external_postresult_audit_v1_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v25129_causal_salience_external_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
POSTFREEZE_GOLD = OUTPUT_ROOT / "postfreeze_hidden_package_gold.jsonl"

CONTRACT = Path(
    "src/deepwide_agent/v25129_causal_salience_external_contract.py"
)
RUNNER = Path("scripts/run_v25129_causal_salience_external.py")
CONTROL = Path("scripts/control_v25129_causal_salience_external.py")
TEST = Path("tests/test_v25129_causal_salience_external.py")
HELPER = parent.HELPER
PARENT_AUDIT = Path(
    "results/v25128_causally_coupled_target_record_build_audit_v1_20260811.json"
)
PARENT_AUDIT_SHA256 = "fdf625954fe3aa23fbe4d7671ee30081eed9d1842e8185aaced62c74c905d39b"
CONSUMED_PARENT_DIAGNOSIS = Path(
    "results/v25126_v25125_recovery_mechanism_diagnosis_v1_20260811.json"
)
CONSUMED_PARENT_DIAGNOSIS_SHA256 = (
    "0aafe98022e473bfd0e8223030c2af5f34eaee71b5f48fe5a926a9054ab41d62"
)
FORWARD_SOURCES = (CONTRACT, RUNNER, HELPER)

TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 4
FRESHNESS_PARENT_COMMIT = "dafad377"
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v25129_causal_salience_external_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_causal_salience_mechanism_gate"
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = copy.deepcopy(parent.SEARCH)
LIMITS = copy.deepcopy(parent.LIMITS)
CLEANUP_RESERVE_SECONDS = parent.CLEANUP_RESERVE_SECONDS
MINIMUM_MODEL_ATTEMPT_SECONDS = parent.MINIMUM_MODEL_ATTEMPT_SECONDS
ARMS = runtime.ARMS
CONTROL_ARM, CANDIDATE_ARM = ARMS
COLUMNS = parent.COLUMNS
EXPECTED_WATCHERS = parent.EXPECTED_WATCHERS

CLUES = (
    "a composable command-line interface library based on Python type hints",
    "a Python library for building rich text and beautiful formatting in terminal applications",
    "a library for creating interactive command-line prompts with completion and syntax highlighting",
    "a library for declaratively building command-line interfaces from Python objects",
    "a simple Python library for building command-line interfaces with minimal boilerplate",
    "a framework for building cross-platform terminal user interfaces with an application loop",
    "a library for parsing human-readable dates and times in Python",
    "a Python library for making HTTP requests for humans",
    "an asynchronous HTTP client and server framework for asyncio",
    "a fast ASGI server implementation using uvloop and httptools",
    "an ASGI toolkit for building lightweight asynchronous web services",
    "a modern high-performance web framework based on type hints and automatic API documentation",
    "a lightweight WSGI web application framework designed to be quick to start",
    "a full-featured web framework encouraging rapid development and pragmatic design",
    "a Python library that validates dataframes against declarative schemas",
    "a flexible object serialization and deserialization library with validation schemas",
    "a library for converting complex Python objects to and from native data types",
    "a library that generates fast JSON encoders and decoders for typed Python models",
    "a Python implementation of JSON Web Token encoding and decoding",
    "a cryptographic recipes and primitives package for Python developers",
)

SECRET = parent.SECRET
payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
seal = parent.seal
sealed = parent.sealed
git = parent.git
ordinary = parent.ordinary
watcher_snapshot = parent.watcher_snapshot


def task_vector() -> list[dict[str, str]]:
    if len(CLUES) != TASK_COUNT or len(set(CLUES)) != TASK_COUNT:
        raise RuntimeError("V2.51.29 clue vector drifted")
    rows: list[dict[str, str]] = []
    for clue in CLUES:
        opaque = "task_" + hashlib.sha256(
            f"v25129:{clue}".encode()
        ).hexdigest()[:24]
        question = (
            "Identify the single Python package matching this public description clue: "
            f"<CLUE>{clue}</CLUE>. Resolve the package from public web pages, then use "
            "PyPI as the visible authority for release metadata. Return exactly one "
            "Markdown table and no prose. Columns exactly: "
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
        raise ValueError("V2.51.29 task denominator drifted")
    output: list[dict[str, str]] = []
    for value, clue in zip(values, CLUES, strict=True):
        if (
            not isinstance(value, Mapping)
            or set(value) != {"opaque_id", "question"}
            or re.fullmatch(r"task_[0-9a-f]{24}", str(value.get("opaque_id") or ""))
            is None
            or not isinstance(value.get("question"), str)
            or f"<CLUE>{clue}</CLUE>" not in value["question"]
            or "Columns exactly: " + " | ".join(COLUMNS) not in value["question"]
            or "https://" in value["question"]
        ):
            raise ValueError("V2.51.29 visible task drifted")
        output.append(
            {"opaque_id": str(value["opaque_id"]), "question": value["question"]}
        )
    if len({row["opaque_id"] for row in output}) != TASK_COUNT:
        raise ValueError("V2.51.29 opaque identity collision")
    return output


def arm_order_vector() -> list[list[str]]:
    tasks = task_vector()
    ranked = sorted(
        range(TASK_COUNT),
        key=lambda index: hashlib.sha256(
            f"v25129-arm-order:{tasks[index]['opaque_id']}".encode()
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
    value = copy.deepcopy(parent.source_policy())
    value.update(
        {
            "fresh_population_selected_by_parent_history_exact_clue_literal_zero_scan_only": True,
            "v25121_and_v25125_populations_are_consumed_and_never_reused_resumed_or_completed": True,
            "visible_legacy_query_seeds_are_deterministically_compatible_before_first_wave": True,
            "visible_query_seed_markup_controls_urls_and_forbidden_syntax_removed": True,
            "visible_query_seed_character_cap": runtime.parent.MAXIMUM_SEED_QUERY_CHARACTERS,
            "plan_transport_and_output_validation_failures_are_separately_accounted": True,
            "grounded_plan_generated_query_strict_grammar_is_unchanged": True,
            "unattributable_prediction_difference_forbidden_by_identity_handoff": True,
            "second_wave_evidence_precedes_shared_first_wave_evidence_with_equal_prompt_length": True,
            "grounded_plan_prompt_checklist_added_without_relaxing_verbatim_validator": True,
            "only_successor_changes_are_causal_coupling_salience_and_strict_checklist": True,
            "outer_failure_rows_retain_content_free_actual_effect_counts": True,
        }
    )
    return value


def mechanism_gate() -> dict[str, Any]:
    value = copy.deepcopy(parent.mechanism_gate())
    value.update(
        {
            "maximum_plan_model_effect_failures": 0,
            "maximum_plan_transport_failures": 0,
            "maximum_plan_output_validation_failures": 0,
            "minimum_tasks_with_compatible_visible_query_seed": 20,
            "outer_failure_actual_effect_count_complete": True,
            "maximum_unattributable_prediction_changed_tasks": 0,
            "minimum_causal_coupling_receipt_valid_tasks": 20,
            "minimum_grounded_prompt_checklist_tasks": 20,
            "minimum_paired_synthesis_salience_tasks": 20,
            "minimum_prompt_length_preserved_tasks": 20,
            "minimum_both_arms_second_wave_prioritized_tasks": 18,
            "identity_handoff_exactly_complements_retrieval_mechanism": True,
            "maximum_identity_handoff_prediction_changed_tasks": 0,
        }
    )
    return value


def quality_gate() -> dict[str, Any]:
    return copy.deepcopy(parent.quality_gate())


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
            for candidate in parent.base._module_candidates(relative, node):
                if (root / candidate).is_file() and not (root / candidate).is_symlink():
                    pending.append(candidate)
    return tuple(sorted(observed, key=str))


def dependency_manifest(root: Path, *, tracked: bool) -> dict[str, str]:
    relatives = {
        *forward_dependency_closure(root),
        CONTROL,
        TEST,
        PARENT_AUDIT,
        CONSUMED_PARENT_DIAGNOSIS,
    }
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.51.29 credential literal in source manifest")
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
        raise RuntimeError("V2.51.29 future surface is not pristine")
    if sha256(root / PARENT_AUDIT) != PARENT_AUDIT_SHA256:
        raise RuntimeError("V2.51.29 parent build audit drifted")
    if (
        sha256(root / CONSUMED_PARENT_DIAGNOSIS)
        != CONSUMED_PARENT_DIAGNOSIS_SHA256
    ):
        raise RuntimeError("V2.51.29 consumed parent diagnosis drifted")
    manifest = dependency_manifest(root, tracked=tracked)
    tasks = task_vector()
    value = {
        "artifact_version": 1,
        "role": "v25129_causal_salience_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit_sha256": build_audit_sha256,
        "recovery_parent": {
            "clean_build_audit_path": str(PARENT_AUDIT),
            "clean_build_audit_sha256": PARENT_AUDIT_SHA256,
            "consumed_population_diagnosis_path": str(CONSUMED_PARENT_DIAGNOSIS),
            "consumed_population_diagnosis_sha256": CONSUMED_PARENT_DIAGNOSIS_SHA256,
            "v25121_and_v25125_population_reuse_resume_or_completion": False,
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
            "arm_order_vector_sha256": payload_sha256(arm_order_vector()),
        },
        "execution": {
            "arms": list(ARMS),
            "only_treatment": "grounded_target_record_frontier_selection",
            "only_successor_change": "causal_prediction_coupling_and_equal_length_second_wave_salience",
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
            "one_fresh_causal_salience_external_forward_after_separate_clean_pushed_start": True,
            "v25121_or_v25125_population_reuse_rerun_resume_or_selective_completion": False,
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
        raise RuntimeError("V2.51.29 protocol drifted")
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
