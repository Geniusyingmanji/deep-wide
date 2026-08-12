"""Frozen contract for a fresh DCF-observable CRAN quality successor."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v25203_post_effect_tolerant_quality_contract as base


DATE = "20260812"
PROTOCOL_ID = "v25206_cran_dcf_quality_external_v1"
BUILD_AUDIT = Path(f"results/v25206_cran_dcf_quality_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25206_cran_dcf_quality_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25206_cran_dcf_quality_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25206_cran_dcf_quality_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25206_cran_dcf_quality_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25206_cran_dcf_quality_forward_audit_v1_{DATE}.json")
EVALUATOR = Path("scripts/evaluate_v25206_cran_dcf_quality.py")
EVALUATOR_TEST = Path("tests/test_evaluate_v25206_cran_dcf_quality.py")
EVALUATOR_PROTOCOL = Path(
    f"results/v25206_cran_dcf_quality_evaluator_preregistration_v1_{DATE}.json"
)
RESULT = Path(f"results/v25206_cran_dcf_quality_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v25206_cran_dcf_quality_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v25206_cran_dcf_quality_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
COMPATIBILITY_AGGREGATE = OUTPUT_ROOT / "compatibility_aggregate.json"
INVARIANT_OBSERVATION_AGGREGATE = COMPATIBILITY_AGGREGATE
POSTFREEZE_GOLD = OUTPUT_ROOT / "postfreeze_cran_gold.json"

CONTRACT = Path("src/deepwide_agent/v25206_cran_dcf_quality_contract.py")
RUNNER = Path("scripts/run_v25206_cran_dcf_quality.py")
CONTROL = Path("scripts/control_v25206_cran_dcf_quality.py")
TEST = Path("tests/test_v25206_cran_dcf_quality.py")
COMPATIBILITY = base.COMPATIBILITY
COMPATIBILITY_TEST = base.COMPATIBILITY_TEST
DCF_PARSER = Path("src/deepwide_agent/v25204_cran_dcf_parser.py")
DCF_PARSER_TEST = Path("tests/test_v25204_cran_dcf_parser.py")
SELECTION_SOURCE = Path(
    "scripts/audit_v25206_cran_dcf_quality_population_selection.py"
)
SELECTION_TEST = Path(
    "tests/test_audit_v25206_cran_dcf_quality_population_selection.py"
)
SELECTION_AUDIT = Path(
    "results/v25206_cran_dcf_quality_population_selection_audit_v1_20260812.json"
)
SELECTION_AUDIT_SHA256 = (
    "082de55caaf9740843dee310065490f9d4ea3614d557cd02cfba8f95e93810ba"
)
SELECTION_PARENT = "45dafcd2147c3b7831cc887c5d82d8eef9b7ab38"
IDENTITY_SELECTION_SHA256 = (
    "b16c9433bbdfb8e0e834d64c29fd1f7902a31dba981a1d22c05c160510860d79"
)
DIAGNOSIS = Path(
    "results/v25205_v25203_evaluator_invalid_diagnosis_v1_20260812.json"
)
DIAGNOSIS_SHA256 = (
    "f82b5c4249f80e77a03898a9eb98d24c7ba1ba07a63e22dbc504857aecccab03"
)
DIAGNOSIS_SOURCE = Path("scripts/diagnose_v25205_v25203_evaluator_invalid.py")
DIAGNOSIS_TEST = Path("tests/test_diagnose_v25205_v25203_evaluator_invalid.py")
FORWARD_SOURCES = (CONTRACT, RUNNER, COMPATIBILITY, *base.FORWARD_SOURCES)

TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 8
LEASE_PATH = base.LEASE_PATH
LEASE_OWNER = "v25206_cran_dcf_quality_forward_v1"
LEASE_PURPOSE = "fresh_dcf_observable_cran_quality_gate_v1"
MODEL = copy.deepcopy(base.MODEL)
SEARCH = copy.deepcopy(base.SEARCH)
LIMITS = copy.deepcopy(base.LIMITS)
CLEANUP_RESERVE_SECONDS = base.CLEANUP_RESERVE_SECONDS
MINIMUM_MODEL_ATTEMPT_SECONDS = base.MINIMUM_MODEL_ATTEMPT_SECONDS
runtime = base.runtime
ARMS = runtime.ARMS
CONTROL_ARM = runtime.CONTROL_ARM
CANDIDATE_ARM = runtime.CANDIDATE_ARM
COLUMNS = base.COLUMNS
EXPECTED_WATCHERS = base.EXPECTED_WATCHERS

PACKAGES = (
    "statmod",
    "sticky",
    "StrainRanking",
    "stripless",
    "strucchange",
    "strucchangeRcpp",
    "subgroup",
    "sumup",
    "superpc",
    "surveyCV",
    "surveydata",
    "survPen",
    "survregVB",
    "SVEMnet",
    "swagger",
    "synchronicity",
    "synthpop",
    "tailloss",
    "taxonomizr",
    "tbrf",
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
        raise RuntimeError("V2.52.06 package vector drifted")
    rows: list[dict[str, str]] = []
    for package in PACKAGES:
        opaque = "task_" + hashlib.sha256(
            f"v25206:{package}".encode()
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
        raise ValueError("V2.52.06 task denominator drifted")
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
            raise ValueError("V2.52.06 natural visible task drifted")
        output.append({"opaque_id": str(value["opaque_id"]), "question": question})
    if len({row["opaque_id"] for row in output}) != TASK_COUNT:
        raise ValueError("V2.52.06 opaque identity collision")
    return output


def source_policy() -> dict[str, Any]:
    return {
        **base.source_policy(),
        "v25203_population_reuse": False,
        "v25203_quality_result_reused_or_revalued": False,
        "fresh_population_is_mechanism_enriched_not_unconditional": True,
        "dcf_parser_is_postfreeze_evaluator_only_not_forward_runtime": True,
        "dcf_failure_stage_is_finite_and_content_free": True,
        "same_population_refetch_revalue_retry_resume_or_replacement": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "deepwidebench_dev64_exact220_leaderboard_or_sota_authorized": False,
    }


def mechanism_gate() -> dict[str, Any]:
    return copy.deepcopy(base.mechanism_gate())


def quality_gate() -> dict[str, Any]:
    return copy.deepcopy(base.quality_gate())


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
            for candidate in base.base.base.base.base.base._module_candidates(
                relative, node
            ):
                if (root / candidate).is_file() and not (root / candidate).is_symlink():
                    pending.append(candidate)
    return tuple(sorted(observed, key=str))


def dependency_manifest(root: Path, *, tracked: bool) -> dict[str, str]:
    relatives = {
        *forward_dependency_closure(root),
        CONTROL,
        TEST,
        COMPATIBILITY_TEST,
        DCF_PARSER,
        DCF_PARSER_TEST,
        SELECTION_SOURCE,
        SELECTION_TEST,
        SELECTION_AUDIT,
        DIAGNOSIS,
        DIAGNOSIS_SOURCE,
        DIAGNOSIS_TEST,
    }
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if path.suffix in {".py", ".json", ".md"} and SECRET.search(
            path.read_text(encoding="utf-8")
        ):
            raise RuntimeError("V2.52.06 credential literal in manifest")
        output[str(relative)] = sha256(path)
    return output


def validate_selection(root: Path, *, tracked: bool) -> dict[str, Any]:
    from scripts import (  # noqa: PLC0415
        audit_v25206_cran_dcf_quality_population_selection as audit,
    )

    path = ordinary(root, SELECTION_AUDIT, tracked=tracked)
    value = audit.validate_audit(json.loads(path.read_text(encoding="utf-8")))
    if (
        sha256(path) != SELECTION_AUDIT_SHA256
        or value["parent_commit"] != SELECTION_PARENT
        or value["ordered_identity_vector_sha256"] != IDENTITY_SELECTION_SHA256
        or value["identity_history_zero_hit_count"] != TASK_COUNT
        or value[
            "preselection_requires_license_literal_pipe_and_nonempty_needs_compilation"
        ]
        is not True
        or value["preselection_is_unconditional_natural_population"] is not False
        or value["v25203_population_reuse"] is not False
        or value["prior_external_population_reuse"] is not False
    ):
        raise RuntimeError("V2.52.06 selection audit invalid")
    return value


def _validate_diagnosis(root: Path, *, tracked: bool) -> dict[str, Any]:
    path = ordinary(root, DIAGNOSIS, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(value, dict)
        or sha256(path) != DIAGNOSIS_SHA256
        or value.get("role") != "v25205_v25203_evaluator_invalid_diagnosis"
        or value["audit_valid"] is not True
        or value["findings"] != []
        or not value.get("checks")
        or not all(value["checks"].values())
        or value["diagnosis"][
            "v25203_quality_outcome_is_evaluator_invalid_not_model_no_go"
        ]
        is not True
        or value["diagnosis"][
            "actual_failed_stage_is_unidentified_due_to_catch_all"
        ]
        is not True
        or value["diagnosis"][
            "old_parser_bug_is_plausible_but_not_proven_unique_cause_of_network_run"
        ]
        is not True
        or value["authorization"]["fresh_disjoint_quality_successor_design"]
        is not True
        or value["authorization"][
            "same_population_refetch_revalue_retry_resume_or_replacement"
        ]
        is not False
        or not sealed(value, "diagnosis_payload_sha256")
    ):
        raise RuntimeError("V2.52.06 diagnosis invalid")
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
        raise RuntimeError("V2.52.06 future surface is not pristine")
    selection = validate_selection(root, tracked=tracked)
    diagnosis = _validate_diagnosis(root, tracked=tracked)
    manifest = dependency_manifest(root, tracked=tracked)
    tasks = task_vector()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25206_cran_dcf_quality_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit_sha256": build_audit_sha256,
        "selection": {
            "path": str(SELECTION_AUDIT),
            "sha256": SELECTION_AUDIT_SHA256,
            "identity_vector_sha256": selection["ordered_identity_vector_sha256"],
            "history_zero_hit_count": selection["identity_history_zero_hit_count"],
            "v25203_population_reuse": False,
            "mechanism_enriched_not_unconditional": True,
        },
        "diagnosis_parent": {
            "path": str(DIAGNOSIS),
            "sha256": DIAGNOSIS_SHA256,
            "v25203_quality_is_evaluator_invalid": diagnosis["diagnosis"][
                "v25203_quality_outcome_is_evaluator_invalid_not_model_no_go"
            ],
            "actual_failure_stage_was_unidentified": diagnosis["diagnosis"][
                "actual_failed_stage_is_unidentified_due_to_catch_all"
            ],
            "fresh_disjoint_successor_design": True,
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
            "only_treatment": "same_raw_quote_aware_production_against_frozen_parent_fallback",
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
        raise RuntimeError("V2.52.06 protocol drifted")
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
