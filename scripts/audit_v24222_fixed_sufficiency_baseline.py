#!/usr/bin/env python3
"""Build-only audit for the V2.42.22 fixed-sufficiency baseline."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent.v24222_fixed_sufficiency_baseline import (  # noqa: E402
    POLICY_ID,
    PRODUCTION_PACKAGE_AUTHORIZED,
    build_action_step,
    build_criterion_catalog,
    build_evidence_snapshot,
    decide_fixed_sufficiency_baseline,
    validate_decision_receipt,
)


ROLE = "v24222_label_blind_fixed_sufficiency_baseline_audit"
OUTPUT = Path(
    "results/v24222_label_blind_fixed_sufficiency_baseline_audit_v1_20260731.json"
)
MODULE = Path("src/deepwide_agent/v24222_fixed_sufficiency_baseline.py")
MODULE_TEST = Path("tests/test_v24222_fixed_sufficiency_baseline.py")
AUDIT = Path("scripts/audit_v24222_fixed_sufficiency_baseline.py")
AUDIT_TEST = Path("tests/test_audit_v24222_fixed_sufficiency_baseline.py")
CONTROL_FILES = (MODULE, MODULE_TEST, AUDIT, AUDIT_TEST)

ALLOWED_IMPORT_ROOTS = frozenset(
    {"__future__", "collections", "hashlib", "json", "re", "typing"}
)
FORBIDDEN_CALL_NAMES = frozenset(
    {"__import__", "breakpoint", "compile", "eval", "exec", "input", "open"}
)
FORBIDDEN_ATTRIBUTE_ROOTS = frozenset(
    {
        "aiohttp",
        "anyio",
        "asyncio",
        "builtins",
        "http",
        "httpx",
        "importlib",
        "os",
        "pathlib",
        "requests",
        "shutil",
        "socket",
        "subprocess",
        "urllib",
    }
)
REQUIRED_PUBLIC_FUNCTIONS = frozenset(
    {
        "build_action_step",
        "build_criterion_catalog",
        "build_evidence_snapshot",
        "decide_fixed_sufficiency_baseline",
        "object_sha256",
        "reject_privileged_metadata",
        "validate_action_trace",
        "validate_criterion_catalog",
        "validate_decision_receipt",
        "validate_evidence_snapshot",
    }
)
SECRET_LITERAL = re.compile(
    r"(?:ghp_|github_pat_|tvly-(?:dev-)?|sk-)[A-Za-z0-9_-]{16,}"
)
OPAQUE_ID = re.compile(r"task_[0-9a-f]{24}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def ordinary(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.42.22 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(
            f"V2.42.22 expected an ordinary repository file: {relative}"
        )
    return path


def _attribute_root(node: ast.Attribute) -> str | None:
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        current = current.value
    return current.id if isinstance(current, ast.Name) else None


def audit_python_source(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    imports: set[str] = set()
    defined_functions: set[str] = set()
    forbidden_calls: list[str] = []
    forbidden_attributes: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".", 1)[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defined_functions.add(node.name)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALL_NAMES:
                forbidden_calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                root = _attribute_root(node.func)
                if root in FORBIDDEN_ATTRIBUTE_ROOTS:
                    forbidden_attributes.append(f"{root}.{node.func.attr}")
    disallowed_imports = sorted(imports - ALLOWED_IMPORT_ROOTS)
    missing_functions = sorted(REQUIRED_PUBLIC_FUNCTIONS - defined_functions)
    if disallowed_imports or forbidden_calls or forbidden_attributes or missing_functions:
        raise RuntimeError(
            "V2.42.22 capability boundary failed: "
            f"imports={disallowed_imports}, calls={sorted(forbidden_calls)}, "
            f"attributes={sorted(forbidden_attributes)}, missing={missing_functions}"
        )
    return {
        "ast_node_count": sum(1 for _ in ast.walk(tree)),
        "import_roots": sorted(imports),
        "required_public_functions_present": sorted(REQUIRED_PUBLIC_FUNCTIONS),
        "disallowed_import_count": 0,
        "forbidden_call_count": 0,
        "forbidden_attribute_call_count": 0,
        "file_environment_network_process_or_dynamic_code_capability": False,
    }


def _digest(character: str) -> str:
    return character * 64


def _criterion(
    reference: str,
    action: str,
    *,
    priority: int,
    kind: str = "coverage",
    minimum_evidence: int = 1,
    minimum_sources: int = 1,
) -> dict[str, object]:
    return {
        "criterion_ref_sha256": reference,
        "criterion_kind": kind,
        "priority": priority,
        "action_class_sha256": action,
        "minimum_clean_evidence_classes": minimum_evidence,
        "minimum_clean_source_classes": minimum_sources,
    }


def _assertion(
    reference: str,
    evidence_class: str,
    source_class: str,
    *,
    page_backed: bool = True,
    assertion_kind: str = "support",
) -> dict[str, object]:
    return {
        "criterion_ref_sha256": reference,
        "evidence_class_sha256": evidence_class,
        "source_class_sha256": source_class,
        "page_backed": page_backed,
        "assertion_kind": assertion_kind,
    }


def _catalog(
    criteria: list[dict[str, object]], *, max_action_steps: int = 2
) -> dict[str, object]:
    return build_criterion_catalog(
        visible_input_projection_sha256=_digest("0"),
        root_scope_sha256=_digest("1"),
        max_action_steps=max_action_steps,
        criteria=criteria,
    )


def _trace(*actions: str) -> list[dict[str, object]]:
    return [
        build_action_step(step_index=index, action_class_sha256=action)
        for index, action in enumerate(actions)
    ]


def _decision(
    criteria: list[dict[str, object]],
    actions: list[dict[str, object]],
    assertions: list[dict[str, object]],
    *,
    max_action_steps: int = 2,
) -> dict[str, object]:
    catalog = _catalog(criteria, max_action_steps=max_action_steps)
    snapshot = build_evidence_snapshot(
        root_scope_sha256=_digest("1"),
        after_action_count=len(actions),
        assertions=assertions,
    )
    receipt = decide_fixed_sufficiency_baseline(
        criterion_catalog=catalog,
        action_trace=actions,
        evidence_snapshot=snapshot,
        opaque_task_ref_sha256=_digest("2"),
    )
    validate_decision_receipt(
        receipt,
        criterion_catalog=catalog,
        action_trace=actions,
        evidence_snapshot=snapshot,
        opaque_task_ref_sha256=_digest("2"),
    )
    return receipt


def replay_synthetic_contracts() -> dict[str, Any]:
    action_a = _digest("a")
    action_b = _digest("b")
    reference_a = _digest("c")
    reference_b = _digest("d")
    evidence_a = _digest("e")
    source_a = _digest("f")

    ready = _decision(
        [_criterion(reference_a, action_a, priority=0)],
        _trace(action_a),
        [_assertion(reference_a, evidence_a, source_a)],
    )
    pending = _decision(
        [
            _criterion(reference_a, action_a, priority=9),
            _criterion(reference_b, action_b, priority=1, kind="time"),
        ],
        [],
        [],
    )
    exhausted = _decision(
        [_criterion(reference_a, action_a, priority=0)],
        _trace(action_a, action_a),
        [],
    )
    contradicted = _decision(
        [
            _criterion(reference_a, action_a, priority=0),
            _criterion(
                reference_b,
                action_b,
                priority=100,
                kind="exclusion",
            ),
        ],
        [],
        [
            _assertion(
                reference_b,
                evidence_a,
                source_a,
                assertion_kind="contradiction",
            )
        ],
    )
    if (
        ready["decision_kind"] != "answer_ready"
        or ready["answer_ready_is_not_task_success"] is not True
        or pending["decision_kind"] != "continue"
        or pending["selected_action_class_sha256"] != action_b
        or exhausted["decision_kind"] != "abstain_budget_exhausted"
        or exhausted["budget_exhaustion_is_not_task_success"] is not True
        or contradicted["selected_criterion_ref_sha256"] != reference_b
    ):
        raise RuntimeError("V2.42.22 synthetic decision replay drifted")

    chronology_rejected = False
    try:
        build_criterion_catalog(
            visible_input_projection_sha256=_digest("0"),
            root_scope_sha256=_digest("1"),
            max_action_steps=2,
            criteria=[_criterion(reference_a, action_a, priority=0)],
            presearch_action_trace=_trace(action_a),
        )
    except ValueError as error:
        chronology_rejected = "before the first action" in str(error)
    if not chronology_rejected:
        raise RuntimeError("V2.42.22 post-action criterion construction was accepted")

    conflict_rejected = False
    try:
        _decision(
            [_criterion(reference_a, action_a, priority=0)],
            [],
            [
                _assertion(reference_a, evidence_a, source_a),
                _assertion(
                    reference_a,
                    evidence_a,
                    _digest("9"),
                    assertion_kind="contradiction",
                ),
            ],
        )
    except ValueError as error:
        conflict_rejected = "both support and contradiction" in str(error)
    if not conflict_rejected:
        raise RuntimeError("V2.42.22 support/contradiction conflict was accepted")

    privileged_metadata_rejected = False
    unsafe = _criterion(reference_a, action_a, priority=0)
    unsafe["priority"] = {"nested": [{"ground_truth": "forbidden"}]}
    try:
        _catalog([unsafe])
    except ValueError as error:
        privileged_metadata_rejected = "privileged metadata rejected" in str(error)
    if not privileged_metadata_rejected:
        raise RuntimeError("V2.42.22 privileged metadata was accepted")

    return {
        "decision_replay_count": 4,
        "decision_kinds_observed": [
            "abstain_budget_exhausted",
            "answer_ready",
            "continue",
        ],
        "criteria_frozen_before_first_action": True,
        "post_action_catalog_construction_rejected": True,
        "contradicted_criterion_prioritized": True,
        "budget_exhaustion_is_not_task_success": True,
        "answer_ready_is_not_task_success": True,
        "support_contradiction_conflict_rejected": True,
        "nested_privileged_metadata_rejected": True,
        "synthetic_content_or_benchmark_rows_read": False,
    }


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.22 audit may only use the canonical workspace")
    paths = {str(relative): ordinary(root, relative) for relative in CONTROL_FILES}
    module_source = paths[str(MODULE)].read_text(encoding="utf-8")
    static_audit = audit_python_source(module_source)
    manifest = {relative: sha256(path) for relative, path in paths.items()}
    replay = replay_synthetic_contracts()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "policy_id": POLICY_ID,
        "label_blind": True,
        "build_only": True,
        "baseline_only": True,
        "control_surface": {
            "file_count": len(manifest),
            "manifest": manifest,
            "manifest_sha256": payload_sha256(manifest),
        },
        "static_capability_audit": static_audit,
        "synthetic_contract_replay": replay,
        "scientific_scope": {
            "fixed_evidence_sufficiency_termination_implemented": True,
            "coverage_source_time_and_exclusion_criterion_kinds_supported": True,
            "catalog_requires_empty_supplied_presearch_action_trace": True,
            "clean_page_evidence_and_source_thresholds_required": True,
            "active_page_contradiction_prevents_satisfaction": True,
            "hard_budget_exhaustion_abstains_without_success_claim": True,
            "criterion_semantic_quality_validated": False,
            "criterion_derivation_from_visible_input_projection_proven": False,
            "chronology_beyond_supplied_trace_attestation_proven": False,
            "active_evidence_snapshot_completeness_proven": False,
            "calibrated_probabilistic_belief_implemented": False,
            "four_layer_open_world_risk_implemented": False,
            "entropy_information_gain_or_voc_implemented": False,
            "source_independence_estimated_or_claimed": False,
            "quality_cost_or_benchmark_effect_observed": False,
        },
        "source_policy": {
            "repository_control_files_and_synthetic_hashes_only": True,
            "runtime_task_question_query_raw_evidence_url_prediction_or_answer_read": False,
            "benchmark_subset_category_question_type_label_split_or_mapping_read": False,
            "gold_evaluator_score_reward_or_results_read": False,
            "credential_environment_keyring_or_secret_value_read": False,
            "network_model_search_fetch_subprocess_or_api_called": False,
        },
        "authorization": {
            "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
            "active_forward_prompt_model_search_budget_or_controller_change": False,
            "process_signal_restart_resume_rerun_or_selective_retry": False,
            "candidate_materialization_or_package_gate": False,
            "benchmark_forward_dev64_full220_or_evaluator_launch": False,
            "shared_api_lease_acquire": False,
            "credit_assignment_or_training": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "claims": {
            "baseline_implementation_available": True,
            "runtime_integration_available": False,
            "benchmark_score_available": False,
            "benchmark_improvement_observed": False,
            "entropy_or_credit_effect_observed": False,
            "leaderboard_submission_performed": False,
            "sota": False,
        },
        "audit_valid": True,
    }
    encoded = json.dumps(value, ensure_ascii=False)
    if OPAQUE_ID.search(encoded) or SECRET_LITERAL.search(encoded):
        raise RuntimeError("V2.42.22 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.22 audit output path is noncanonical")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    target = target if target.is_absolute() else ROOT / target
    value = build_audit()
    publish_new(target, value)
    print(
        json.dumps(
            {
                "path": str(target),
                "sha256": sha256(target),
                "audit_valid": value["audit_valid"],
                "build_only": value["build_only"],
            }
        )
    )


if __name__ == "__main__":
    main()
