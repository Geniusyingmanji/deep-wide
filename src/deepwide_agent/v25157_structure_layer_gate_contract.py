"""Fresh fixed-denominator zero-model structure-layer gate contract."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v25061_docsrs_late_record_gate_contract as base


DATE = "20260812"
PROTOCOL_ID = "v25157_cran_structure_layer_gate_v1"
BUILD_AUDIT = Path(
    f"results/v25157_structure_layer_gate_build_audit_v1_{DATE}.json"
)
PROTOCOL = Path(
    f"results/v25157_structure_layer_gate_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v25157_structure_layer_gate_preactivation_audit_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v25157_structure_layer_gate_execution_start_v1_{DATE}.json"
)
FORWARD_RESULT = Path(
    f"results/v25157_structure_layer_gate_forward_result_v1_{DATE}.json"
)
FORWARD_AUDIT = Path(
    f"results/v25157_structure_layer_gate_forward_audit_v1_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v25157_structure_layer_gate_v1_{DATE}")
TASK_ROWS = OUTPUT_ROOT / "content_free_task_receipts.jsonl"

CONTRACT = Path("src/deepwide_agent/v25157_structure_layer_gate_contract.py")
RUNNER = Path("scripts/run_v25157_structure_layer_gate.py")
CONTROL = Path("scripts/control_v25157_structure_layer_gate.py")
TEST = Path("tests/test_v25157_structure_layer_gate.py")
OBSERVER = Path("src/deepwide_agent/v25155_projection_structure_observer.py")
NATIVE = Path("src/deepwide_agent/native_search.py")
HTML_SURFACE = Path("src/deepwide_agent/v25061_html_surface.py")
PROJECTION = Path("src/deepwide_agent/v24984_robust_late_page_projection.py")
POPULATION_SOURCE = Path("scripts/audit_v25157_structure_population_selection.py")
POPULATION_TEST = Path("tests/test_audit_v25157_structure_population_selection.py")
POPULATION_AUDIT = Path(
    f"results/v25157_structure_population_selection_audit_v1_{DATE}.json"
)
POPULATION_AUDIT_SHA256 = (
    "6504a353882733db1e2337090721ee863496cb75cafce96bd2604eacc05a7210"
)
PARENT_BUILD_AUDIT = Path(
    "results/v25156_projection_structure_observer_build_audit_v1_20260812.json"
)
PARENT_BUILD_AUDIT_SHA256 = (
    "9925e290163904ed3340dfe59188462188a3f8e13244c6af36c6b7b239e35480"
)
FORWARD_SOURCES = (CONTRACT, RUNNER, OBSERVER, HTML_SURFACE, PROJECTION)

TASK_COUNT = 20
FETCH_WORKERS = 20
FETCH_CONNECT_TIMEOUT_SECONDS = 5.0
FETCH_READ_TIMEOUT_SECONDS = 20.0
MAX_RESPONSE_BYTES = 3_000_000
MINIMUM_FETCH_SUCCESSES = 18
FRESHNESS_PARENT_COMMIT = "aa971a16"
EXPECTED_WATCHERS = base.EXPECTED_WATCHERS
PACKAGES = (
    "chatlas",
    "finetune",
    "chores",
    "querychat",
    "tidyllm",
    "vitals",
    "fiery",
    "routr",
    "brochure",
    "ambiorix",
    "rhino",
    "leprechaun",
    "charpente",
    "shiny.fluent",
    "shiny.react",
    "reactR",
    "ggh4x",
    "ggdist",
    "sfnetworks",
    "pointblank",
)
SELECTION_VECTOR_SHA256 = (
    "6b73e11cd8df36aab572a2d421b065c16a5d92a507d3eb39e76d578271e7963e"
)
COLUMNS = ("Package", "Version", "License", "NeedsCompilation")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)

payload_sha256 = base.payload_sha256
sha256 = base.sha256
seal = base.seal
sealed = base.sealed
git = base.git
ordinary = base.ordinary
watcher_snapshot = base.watcher_snapshot


def task_vector() -> list[dict[str, str]]:
    if (
        len(PACKAGES) != TASK_COUNT
        or len(set(PACKAGES)) != TASK_COUNT
        or payload_sha256(PACKAGES) != SELECTION_VECTOR_SHA256
    ):
        raise RuntimeError("V2.51.57 package vector drifted")
    question = (
        "Using only the supplied public CRAN package page, return exactly one "
        "Markdown table and no prose. Include exactly one row. Columns must "
        "be: Package | Version | License | NeedsCompilation. Preserve the "
        "canonical published values while collapsing whitespace. Use Unknown "
        "only when the supplied page does not establish a value."
    )
    return [
        {
            "opaque_id": "task_"
            + hashlib.sha256(f"v25157:{package}".encode()).hexdigest()[:24],
            "question": question,
        }
        for package in PACKAGES
    ]


def endpoint_vector() -> list[str]:
    return [
        f"https://cran.r-project.org/web/packages/{package}/index.html"
        for package in PACKAGES
    ]


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": [
            "opaque_task_position",
            "shared_visible_question",
            "same_forward_public_html_page",
        ],
        "fixed_twenty_task_failure_as_zero_denominator": True,
        "population_selected_by_parent_history_git_log_s_only": True,
        "population_selection_artifact_contains_no_identity_plaintext_or_endpoint": True,
        "final_population_endpoints_not_opened_before_protocol_freeze": True,
        "one_http_fetch_attempt_per_task_no_retry_redirect_or_replacement": True,
        "production_decode_html_extraction_and_v24984_projection_used": True,
        "raw_html_extracted_text_and_projected_text_observed_in_one_task": True,
        "only_content_free_structure_counts_and_transitions_persisted": True,
        "structure_signal_is_diagnostic_not_admissible_evidence": True,
        "no_page_identity_url_question_label_value_text_prediction_or_content_hash_persisted": True,
        "no_model_hosted_search_evaluator_or_benchmark_call": True,
        "mapping_gold_category_question_type_split_score_reward_read": False,
        "entropy_or_information_gain_assigns_credit_or_routes": False,
        "deepwidebench_dev64_exact220_leaderboard_or_sota_authorized": False,
    }


def gates() -> dict[str, Any]:
    return {
        "fixed_denominator": TASK_COUNT,
        "fetch_attempts": TASK_COUNT,
        "minimum_fetch_successes": MINIMUM_FETCH_SUCCESSES,
        "minimum_observed_structure_pages": MINIMUM_FETCH_SUCCESSES,
        "minimum_any_layer_structure_or_loss_events": 1,
        "positive_signed_credit_count": 0,
        "quality_or_evaluator_authorization": False,
    }


def _module_candidates(relative: Path, node: ast.AST) -> list[Path]:
    return base._module_candidates(relative, node)


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
            for candidate in _module_candidates(relative, node):
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
        POPULATION_SOURCE,
        POPULATION_TEST,
        POPULATION_AUDIT,
        PARENT_BUILD_AUDIT,
    }
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.51.57 credential literal in source manifest")
        output[str(relative)] = sha256(path)
    return output


def validate_population_selection(root: Path, *, tracked: bool) -> dict[str, Any]:
    path = ordinary(root, POPULATION_AUDIT, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    unsigned = dict(value) if isinstance(value, dict) else {}
    seal_value = unsigned.pop("audit_payload_sha256", None)
    if (
        not isinstance(value, dict)
        or sha256(path) != POPULATION_AUDIT_SHA256
        or value.get("role")
        != "v25157_structure_population_selection_aggregate_audit"
        or value.get("parent_commit")
        != git(root, "rev-parse", "--verify", FRESHNESS_PARENT_COMMIT + "^{commit}")
        or value.get("identity_count") != TASK_COUNT
        or value.get("unique_identity_count") != TASK_COUNT
        or value.get("identity_history_total_hit_count") != 0
        or value.get("identity_history_zero_hit_count") != TASK_COUNT
        or value.get("ordered_identity_vector_sha256") != SELECTION_VECTOR_SHA256
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or seal_value != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.51.57 population selection drifted")
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
        raise RuntimeError("V2.51.57 future surface is not pristine")
    selection = validate_population_selection(root, tracked=tracked)
    manifest = dependency_manifest(root, tracked=tracked)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25157_structure_layer_gate_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit_sha256": build_audit_sha256,
        "parent_observer_build_audit": {
            "path": str(PARENT_BUILD_AUDIT),
            "sha256": PARENT_BUILD_AUDIT_SHA256,
        },
        "freshness": {
            "parent_commit": FRESHNESS_PARENT_COMMIT,
            "population_selection_audit_sha256": sha256(root / POPULATION_AUDIT),
            "identity_history_zero_hit_count": selection[
                "identity_history_zero_hit_count"
            ],
            "endpoint_page_value_model_search_evaluator_or_credential_opened_during_selection": False,
        },
        "population": {
            "task_count": TASK_COUNT,
            "identity_vector_sha256": SELECTION_VECTOR_SHA256,
            "task_vector_sha256": payload_sha256(task_vector()),
            "endpoint_vector_sha256": payload_sha256(endpoint_vector()),
        },
        "execution": {
            "fetch_workers": FETCH_WORKERS,
            "logical_fetch_attempts_per_task": 1,
            "redirects": 0,
            "retries": 0,
            "replacements": 0,
            "fetch_connect_timeout_seconds": FETCH_CONNECT_TIMEOUT_SECONDS,
            "fetch_read_timeout_seconds": FETCH_READ_TIMEOUT_SECONDS,
            "maximum_response_bytes": MAX_RESPONSE_BYTES,
            "model_calls": 0,
            "hosted_search_calls": 0,
            "evaluator_calls": 0,
            "only_candidate": "v25155_three_layer_content_free_structure_observer",
        },
        "gates": gates(),
        "protected_watchers": watcher_snapshot(),
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": source_policy(),
        "authorization": {
            "one_fixed_denominator_external_structure_forward_after_clean_pushed_start": True,
            "next_layer_repair_design_only_after_audited_structure_result": True,
            "model_or_evaluator_on_this_population": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_population_replacement_or_selective_revaluation": False,
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
        raise RuntimeError("V2.51.57 protocol drifted")
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol",
    "dependency_manifest",
    "endpoint_vector",
    "forward_dependency_closure",
    "gates",
    "git",
    "ordinary",
    "payload_sha256",
    "seal",
    "sealed",
    "sha256",
    "source_policy",
    "task_vector",
    "validate_population_selection",
    "validate_protocol",
    "watcher_snapshot",
]
