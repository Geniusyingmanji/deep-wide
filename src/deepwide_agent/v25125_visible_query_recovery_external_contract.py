"""Fresh external recovery contract after the consumed V2.51.21 failure.

Only twenty new public description clues are frozen in the forward closure.
Hidden package identities, endpoints, pages, values, gold, and evaluator code
are absent.  V2.51.23 is the only runtime successor: it makes visible legacy
query seeds compatible while leaving grounded-plan validation and all matched
budgets unchanged.  The consumed V2.51.21 population is never resumed.
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
from . import v25123_visible_legacy_query_compatible_runtime as runtime


DATE = "20260811"
PROTOCOL_ID = "v25125_visible_query_recovery_external_mechanism_v1"
BUILD_AUDIT = Path(
    f"results/v25125_visible_query_recovery_external_build_audit_v1_{DATE}.json"
)
PROTOCOL = Path(
    f"results/v25125_visible_query_recovery_external_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v25125_visible_query_recovery_external_preactivation_audit_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v25125_visible_query_recovery_external_execution_start_v1_{DATE}.json"
)
FORWARD_RESULT = Path(
    f"results/v25125_visible_query_recovery_external_forward_result_v1_{DATE}.json"
)
FORWARD_AUDIT = Path(
    f"results/v25125_visible_query_recovery_external_forward_audit_v1_{DATE}.json"
)
EVALUATOR = Path("scripts/evaluate_v25125_visible_query_recovery_external.py")
EVALUATOR_TEST = Path(
    "tests/test_evaluate_v25125_visible_query_recovery_external.py"
)
EVALUATOR_PROTOCOL = Path(
    f"results/v25125_visible_query_recovery_external_evaluator_preregistration_v1_{DATE}.json"
)
RESULT = Path(f"results/v25125_visible_query_recovery_external_result_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v25125_visible_query_recovery_external_postresult_audit_v1_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v25125_visible_query_recovery_external_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
POSTFREEZE_GOLD = OUTPUT_ROOT / "postfreeze_hidden_package_gold.jsonl"

CONTRACT = Path(
    "src/deepwide_agent/v25125_visible_query_recovery_external_contract.py"
)
RUNNER = Path("scripts/run_v25125_visible_query_recovery_external.py")
CONTROL = Path("scripts/control_v25125_visible_query_recovery_external.py")
TEST = Path("tests/test_v25125_visible_query_recovery_external.py")
HELPER = parent.HELPER
PARENT_AUDIT = Path("results/v25124_visible_legacy_query_build_audit_v1_20260811.json")
PARENT_AUDIT_SHA256 = "a399ea106b005fa9062b69e0017b4b2657dcf2f7fd0cfeab2bdeea9c81675c75"
CONSUMED_PARENT_DIAGNOSIS = Path(
    "results/v25122_v25121_legacy_query_failure_diagnosis_v1_20260811.json"
)
CONSUMED_PARENT_DIAGNOSIS_SHA256 = (
    "ad3ab90697376a099d1ef04174e3c17c63b3321389fdc373985a05a7cdd2c2c9"
)
FORWARD_SOURCES = (CONTRACT, RUNNER, HELPER)

TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 4
FRESHNESS_PARENT_COMMIT = "1c3cf37c"
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v25125_visible_query_recovery_external_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_visible_query_recovery_mechanism_gate"
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
    "a general-purpose retrying library for Python with configurable stop and wait policies",
    "structured logging for Python that turns log events into processable dictionaries",
    "a datetime library with intuitive time-zone handling and human-friendly arithmetic",
    "Python logging made simple through a preconfigured sink-based logger",
    "fast standards-compliant JSON serialization powered by Rust and SIMD",
    "a fast serialization and validation library built around typed immutable structs",
    "settings management that loads environment variables into validated Pydantic models",
    "a minimal low-level HTTP client that powers higher-level Python clients",
    "a fast drop-in replacement for the asyncio event loop implemented with libuv",
    "a friendly structured-concurrency library for asynchronous Python programs",
    "a compatibility layer providing structured concurrency across asyncio and Trio",
    "an extremely fast Python linter and formatter implemented in Rust",
    "a standards-focused static type checker for Python implemented in TypeScript",
    "a modern extensible Python project manager with environment and build plugins",
    "a modern Python package and dependency manager supporting current packaging standards",
    "a dependency manager and packaging workflow centered on a declarative project file",
    "a tool that installs and runs Python command-line applications in isolated environments",
    "a tool for creating isolated Python environments across multiple interpreter versions",
    "a framework for managing and maintaining multi-language pre-commit hooks",
    "a generic virtual-environment automation tool for testing Python packages",
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
        raise RuntimeError("V2.51.25 clue vector drifted")
    rows: list[dict[str, str]] = []
    for clue in CLUES:
        opaque = "task_" + hashlib.sha256(
            f"v25125:{clue}".encode()
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
        raise ValueError("V2.51.25 task denominator drifted")
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
            raise ValueError("V2.51.25 visible task drifted")
        output.append(
            {"opaque_id": str(value["opaque_id"]), "question": value["question"]}
        )
    if len({row["opaque_id"] for row in output}) != TASK_COUNT:
        raise ValueError("V2.51.25 opaque identity collision")
    return output


def arm_order_vector() -> list[list[str]]:
    tasks = task_vector()
    ranked = sorted(
        range(TASK_COUNT),
        key=lambda index: hashlib.sha256(
            f"v25125-arm-order:{tasks[index]['opaque_id']}".encode()
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
            "v25121_population_is_consumed_and_never_reused_resumed_or_completed": True,
            "visible_legacy_query_seeds_are_deterministically_compatible_before_first_wave": True,
            "visible_query_seed_markup_controls_urls_and_forbidden_syntax_removed": True,
            "visible_query_seed_character_cap": runtime.MAXIMUM_SEED_QUERY_CHARACTERS,
            "plan_transport_and_output_validation_failures_are_separately_accounted": True,
            "grounded_plan_generated_query_strict_grammar_is_unchanged": True,
            "only_successor_change_is_first_plan_envelope_visible_query_compatibility": True,
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
            raise RuntimeError("V2.51.25 credential literal in source manifest")
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
        raise RuntimeError("V2.51.25 future surface is not pristine")
    if sha256(root / PARENT_AUDIT) != PARENT_AUDIT_SHA256:
        raise RuntimeError("V2.51.25 parent build audit drifted")
    if (
        sha256(root / CONSUMED_PARENT_DIAGNOSIS)
        != CONSUMED_PARENT_DIAGNOSIS_SHA256
    ):
        raise RuntimeError("V2.51.25 consumed parent diagnosis drifted")
    manifest = dependency_manifest(root, tracked=tracked)
    tasks = task_vector()
    value = {
        "artifact_version": 1,
        "role": "v25125_visible_query_recovery_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit_sha256": build_audit_sha256,
        "recovery_parent": {
            "clean_build_audit_path": str(PARENT_AUDIT),
            "clean_build_audit_sha256": PARENT_AUDIT_SHA256,
            "consumed_population_diagnosis_path": str(CONSUMED_PARENT_DIAGNOSIS),
            "consumed_population_diagnosis_sha256": CONSUMED_PARENT_DIAGNOSIS_SHA256,
            "v25121_population_reuse_resume_or_completion": False,
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
            "only_successor_change": "visible_legacy_query_seed_compatibility",
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
            "one_fresh_recovery_external_forward_after_separate_clean_pushed_start": True,
            "v25121_population_reuse_rerun_resume_or_selective_completion": False,
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
        raise RuntimeError("V2.51.25 protocol drifted")
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
