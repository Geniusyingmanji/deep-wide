"""Frozen contract for a fresh exact post-effect compatibility quality gate."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v25199_invariant_observable_quality_contract as base


DATE = "20260812"
PROTOCOL_ID = "v25203_post_effect_tolerant_quality_external_v1"
BUILD_AUDIT = Path(
    f"results/v25203_post_effect_tolerant_quality_build_audit_v1_{DATE}.json"
)
PROTOCOL = Path(
    f"results/v25203_post_effect_tolerant_quality_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v25203_post_effect_tolerant_quality_preactivation_audit_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v25203_post_effect_tolerant_quality_execution_start_v1_{DATE}.json"
)
FORWARD_RESULT = Path(
    f"results/v25203_post_effect_tolerant_quality_forward_result_v1_{DATE}.json"
)
FORWARD_AUDIT = Path(
    f"results/v25203_post_effect_tolerant_quality_forward_audit_v1_{DATE}.json"
)
EVALUATOR = Path("scripts/evaluate_v25203_post_effect_tolerant_quality.py")
EVALUATOR_TEST = Path(
    "tests/test_evaluate_v25203_post_effect_tolerant_quality.py"
)
EVALUATOR_PROTOCOL = Path(
    f"results/v25203_post_effect_tolerant_quality_evaluator_preregistration_v1_{DATE}.json"
)
RESULT = Path(f"results/v25203_post_effect_tolerant_quality_result_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v25203_post_effect_tolerant_quality_postresult_audit_v1_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v25203_post_effect_tolerant_quality_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
COMPATIBILITY_AGGREGATE = OUTPUT_ROOT / "compatibility_aggregate.json"
# Kept as an alias so the frozen V2.51.99 accounting helpers cannot silently
# redirect the content-free sidecar to their historical output location.
INVARIANT_OBSERVATION_AGGREGATE = COMPATIBILITY_AGGREGATE
POSTFREEZE_GOLD = OUTPUT_ROOT / "postfreeze_cran_gold.json"

CONTRACT = Path(
    "src/deepwide_agent/v25203_post_effect_tolerant_quality_contract.py"
)
RUNNER = Path("scripts/run_v25203_post_effect_tolerant_quality.py")
CONTROL = Path("scripts/control_v25203_post_effect_tolerant_quality.py")
TEST = Path("tests/test_v25203_post_effect_tolerant_quality.py")
COMPATIBILITY = Path(
    "src/deepwide_agent/v25200_post_effect_tolerant_vertical_receipt.py"
)
COMPATIBILITY_TEST = Path(
    "tests/test_v25200_post_effect_tolerant_vertical_receipt.py"
)
SELECTION_SOURCE = Path(
    "scripts/audit_v25202_post_effect_tolerant_population_selection.py"
)
SELECTION_TEST = Path(
    "tests/test_audit_v25202_post_effect_tolerant_population_selection.py"
)
SELECTION_AUDIT = Path(
    "results/v25202_post_effect_tolerant_population_selection_audit_v1_20260812.json"
)
SELECTION_AUDIT_SHA256 = (
    "7f294d87256f3feee2d8aea3af6af2fe716d57f86474934e0bb79ed8ec4eeb7a"
)
SELECTION_PARENT = "1f1d25f48e51b631bca95cfad917415d05767c22"
IDENTITY_SELECTION_SHA256 = (
    "de371e1e49effd506326cdc6937ae143aebc67013df181cc9bd5e2b0c16cf7b2"
)
DIAGNOSIS = Path(
    "results/v25201_v25199_inactive_post_effect_diagnosis_v1_20260812.json"
)
DIAGNOSIS_SOURCE = Path(
    "scripts/diagnose_v25201_v25199_inactive_post_effect.py"
)
DIAGNOSIS_TEST = Path(
    "tests/test_diagnose_v25201_v25199_inactive_post_effect.py"
)
DIAGNOSIS_SHA256 = (
    "ef795f27318492130fa36aaf753e738ad478a6b87fabed301c475b5000ee0440"
)
FORWARD_SOURCES = (
    CONTRACT,
    RUNNER,
    COMPATIBILITY,
    *base.FORWARD_SOURCES,
)

TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 8
LEASE_PATH = base.LEASE_PATH
LEASE_OWNER = "v25203_post_effect_tolerant_quality_forward_v1"
LEASE_PURPOSE = "fresh_exact_post_effect_compatibility_quality_gate_v1"
MODEL = copy.deepcopy(base.MODEL)
SEARCH = copy.deepcopy(base.SEARCH)
LIMITS = copy.deepcopy(base.LIMITS)
CLEANUP_RESERVE_SECONDS = base.CLEANUP_RESERVE_SECONDS
MINIMUM_MODEL_ATTEMPT_SECONDS = base.MINIMUM_MODEL_ATTEMPT_SECONDS
runtime = base.runtime
ARMS = runtime.ARMS
CONTROL_ARM = runtime.CONTROL_ARM
CANDIDATE_ARM = runtime.CANDIDATE_ARM
COLUMNS = ("Package", "Version", "License", "NeedsCompilation")
EXPECTED_WATCHERS = base.EXPECTED_WATCHERS

PACKAGES = (
    "evtree",
    "exams2ilias",
    "exams2learnr",
    "exams2sakai",
    "eyelinker",
    "fangs",
    "fastcluster",
    "FastCUB",
    "fastICA",
    "fdANOVA",
    "fontquiver",
    "footballpenaltiesBL",
    "foqat",
    "FPCA3D",
    "fracprolif",
    "FinancialInstrument",
    "formula.tools",
    "fortunes",
    "frbs",
    "fxregime",
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
        raise RuntimeError("V2.52.03 package vector drifted")
    rows: list[dict[str, str]] = []
    for package in PACKAGES:
        opaque = "task_" + hashlib.sha256(
            f"v25203:{package}".encode()
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
        raise ValueError("V2.52.03 task denominator drifted")
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
            raise ValueError("V2.52.03 natural visible task drifted")
        output.append({"opaque_id": str(value["opaque_id"]), "question": question})
    if len({row["opaque_id"] for row in output}) != TASK_COUNT:
        raise ValueError("V2.52.03 opaque identity collision")
    return output


def source_policy() -> dict[str, Any]:
    return {
        **base.source_policy(),
        "exact_post_effect_compatibility_only_after_frozen_v25158_rejection": True,
        "compatibility_surrogate_changes_only_parent_post_effect_flag": True,
        "compatibility_surrogate_must_pass_exact_frozen_validator": True,
        "compatibility_returns_original_receipt_byte_identical": True,
        "compatibility_changes_candidate_prediction_routing_effect_budget_or_credit": False,
        "compatibility_application_is_thread_local_and_published_aggregate_only": True,
        "residual_frozen_v25158_failure_keeps_finite_invariant_observation": True,
        "v25195_or_v25199_population_reuse": False,
        "v25199_retry_resume_or_selective_completion": False,
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
            for candidate in base.base.base.base.base._module_candidates(relative, node):
                if (root / candidate).is_file() and not (root / candidate).is_symlink():
                    pending.append(candidate)
    return tuple(sorted(observed, key=str))


def dependency_manifest(root: Path, *, tracked: bool) -> dict[str, str]:
    relatives = {
        *forward_dependency_closure(root),
        CONTROL,
        TEST,
        COMPATIBILITY_TEST,
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
            raise RuntimeError("V2.52.03 credential literal in manifest")
        output[str(relative)] = sha256(path)
    return output


def validate_selection(root: Path, *, tracked: bool) -> dict[str, Any]:
    from scripts import audit_v25202_post_effect_tolerant_population_selection as audit  # noqa: PLC0415

    path = ordinary(root, SELECTION_AUDIT, tracked=tracked)
    value = audit.validate_audit(json.loads(path.read_text(encoding="utf-8")))
    if (
        sha256(path) != SELECTION_AUDIT_SHA256
        or value["parent_commit"] != SELECTION_PARENT
        or value["ordered_identity_vector_sha256"] != IDENTITY_SELECTION_SHA256
        or value["identity_history_zero_hit_count"] != TASK_COUNT
        or value["preselection_enriched_for_license_literal_pipe"] is not True
        or value["preselection_is_unconditional_natural_population"] is not False
        or value["v25195_population_reuse"] is not False
        or value["v25199_population_reuse"] is not False
        or value["prior_external_population_reuse"] is not False
    ):
        raise RuntimeError("V2.52.03 selection audit invalid")
    return value


def _validate_diagnosis(root: Path, *, tracked: bool) -> dict[str, Any]:
    from scripts import diagnose_v25201_v25199_inactive_post_effect as diagnosis  # noqa: PLC0415

    path = ordinary(root, DIAGNOSIS, tracked=tracked)
    value = diagnosis.validate_diagnosis(json.loads(path.read_text(encoding="utf-8")))
    if (
        sha256(path) != DIAGNOSIS_SHA256
        or value["audit_valid"] is not True
        or value["findings"] != []
        or value["authorization"]["fresh_disjoint_successor_design"] is not True
    ):
        raise RuntimeError("V2.52.03 diagnosis invalid")
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
        raise RuntimeError("V2.52.03 future surface is not pristine")
    selection = validate_selection(root, tracked=tracked)
    diagnosis = _validate_diagnosis(root, tracked=tracked)
    manifest = dependency_manifest(root, tracked=tracked)
    tasks = task_vector()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25203_post_effect_tolerant_quality_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit_sha256": build_audit_sha256,
        "selection": {
            "path": str(SELECTION_AUDIT),
            "sha256": SELECTION_AUDIT_SHA256,
            "identity_vector_sha256": selection["ordered_identity_vector_sha256"],
            "history_zero_hit_count": selection["identity_history_zero_hit_count"],
            "v25195_or_v25199_population_reuse": False,
        },
        "diagnosis_parent": {
            "path": str(DIAGNOSIS),
            "sha256": DIAGNOSIS_SHA256,
            "root_cause": diagnosis["root_cause"][
                "inactive_dynamic_zero_has_one_static_parent_post_effect_explanation"
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
            "only_treatment": "exact_post_effect_compatibility_after_frozen_v25158_rejection",
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
        raise RuntimeError("V2.52.03 protocol drifted")
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
