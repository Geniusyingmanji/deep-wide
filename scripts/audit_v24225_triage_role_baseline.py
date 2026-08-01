#!/usr/bin/env python3
"""Build-only audit for the V2.42.25 TRIAGE role-typed baseline."""

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

from deepwide_agent.v24225_triage_role_baseline import (  # noqa: E402
    CREDIT_TRAINING_AUTHORIZED,
    MAX_CONTEXT_PAIRS_PER_SIDE,
    POLICY_ID,
    PRODUCTION_PACKAGE_AUTHORIZED,
    ROLE_CONSTANTS,
    build_credit_policy,
    build_outcome_advantage_receipt,
    build_role_judgment,
    build_role_typed_credit,
    build_whitened_credit_batch,
    object_sha256,
    reject_role_judge_privileged_metadata,
    validate_whitened_credit_batch,
)


ROLE = "v24225_triage_role_typed_credit_baseline_build_audit"
OUTPUT = Path(
    "results/v24225_triage_role_typed_credit_baseline_build_audit_v1_20260731.json"
)
MODULE = Path("src/deepwide_agent/v24225_triage_role_baseline.py")
MODULE_TEST = Path("tests/test_v24225_triage_role_baseline.py")
AUDIT = Path("scripts/audit_v24225_triage_role_baseline.py")
AUDIT_TEST = Path("tests/test_audit_v24225_triage_role_baseline.py")
CONTROL_FILES = (MODULE, MODULE_TEST, AUDIT, AUDIT_TEST)
ACTIVE_FORWARD_GUARD_FILES = (
    Path("src/deepwide_agent/__init__.py"),
    Path("src/deepwide_agent/runtime.py"),
    Path("src/deepwide_agent/v24211_entropy_runtime.py"),
    Path("scripts/run_deepwide_agent.py"),
    Path("scripts/launch_frozen_deepwide.py"),
)

ALLOWED_IMPORT_ROOTS = frozenset(
    {"__future__", "hashlib", "json", "math", "typing"}
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
        "build_credit_policy",
        "build_outcome_advantage_receipt",
        "build_role_judgment",
        "build_role_typed_credit",
        "build_whitened_credit_batch",
        "object_sha256",
        "reject_role_judge_privileged_metadata",
        "validate_credit_policy",
        "validate_outcome_advantage_receipt",
        "validate_role_judgment",
        "validate_role_typed_credit",
        "validate_whitened_credit_batch",
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
        raise RuntimeError("V2.42.25 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(
            f"V2.42.25 expected an ordinary repository file: {relative}"
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
            "V2.42.25 capability boundary failed: "
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


def _judgment(
    role: str, *, segment: str, trajectory: str = "2"
) -> dict[str, Any]:
    return build_role_judgment(
        segment_ref_sha256=_digest(segment),
        trajectory_ref_sha256=_digest(trajectory),
        visible_task_prompt_projection_sha256=_digest("3"),
        judge_context_projection_sha256=_digest("4"),
        judge_model_sha256=_digest("5"),
        rubric_sha256=_digest("6"),
        previous_action_observation_pair_count=MAX_CONTEXT_PAIRS_PER_SIDE,
        future_action_observation_pair_count=MAX_CONTEXT_PAIRS_PER_SIDE,
        assigned_role=role,
        judge_input_tokens=120,
        judge_output_tokens=8,
    )


def _outcome(
    advantage: float, *, segment: str, trajectory: str = "2"
) -> dict[str, Any]:
    return build_outcome_advantage_receipt(
        segment_ref_sha256=_digest(segment),
        trajectory_ref_sha256=_digest(trajectory),
        group_ref_sha256=_digest("7"),
        verifier_protocol_sha256=_digest("8"),
        verifier_outcome_ref_sha256=_digest("9"),
        outcome_advantage=advantage,
    )


def replay_synthetic_contracts() -> dict[str, Any]:
    policy = build_credit_policy(
        selection_protocol_sha256=_digest("a"),
        mixing_weight=0.4,
    )
    records: list[dict[str, Any]] = []
    for index, (role, constant) in enumerate(ROLE_CONSTANTS.items()):
        segment = format(index + 1, "x")
        typed = _judgment(role, segment=segment)
        terminal = _outcome(0.25, segment=segment)
        record = build_role_typed_credit(
            policy=policy,
            judgment=typed,
            outcome_receipt=terminal,
        )
        if (
            record["role_constant"] != constant
            or record["role_correction"] != 0.4 * constant
        ):
            raise RuntimeError("V2.42.25 role formula replay drifted")
        records.append(record)

    regression = build_role_typed_credit(
        policy=policy,
        judgment=_judgment("regression", segment="b"),
        outcome_receipt=_outcome(0.05, segment="b"),
    )
    exploration = build_role_typed_credit(
        policy=policy,
        judgment=_judgment("useful_exploration", segment="c"),
        outcome_receipt=_outcome(-0.05, segment="c"),
    )
    if (
        regression["verifier_direction_preserved"] is not False
        or exploration["verifier_direction_preserved"] is not False
    ):
        raise RuntimeError("V2.42.25 additive sign-reversal replay drifted")

    batch = build_whitened_credit_batch(
        policy=policy,
        batch_ref_sha256=_digest("d"),
        credit_records=records,
    )
    validate_whitened_credit_batch(
        batch,
        policy=policy,
        batch_ref_sha256=_digest("d"),
        credit_records=records,
    )

    privileged_rejected = False
    try:
        reject_role_judge_privileged_metadata(
            {"safe": [{"final_outcome": 1}]}
        )
    except ValueError:
        privileged_rejected = True
    if not privileged_rejected:
        raise RuntimeError("V2.42.25 privileged role-judge input was accepted")

    cross_identity_rejected = False
    try:
        build_role_typed_credit(
            policy=policy,
            judgment=_judgment("decisive_progress", segment="e"),
            outcome_receipt=_outcome(0.1, segment="f"),
        )
    except ValueError:
        cross_identity_rejected = True
    if not cross_identity_rejected:
        raise RuntimeError("V2.42.25 cross-segment source join was accepted")

    encoded = json.dumps(
        {"policy": policy, "records": records, "batch": batch},
        ensure_ascii=False,
    )
    if SECRET_LITERAL.search(encoded) or OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.25 synthetic replay exposed forbidden content")
    return {
        "role_formula_replay_count": len(records),
        "all_four_triage_v3_role_constants_covered": True,
        "bounded_5_plus_5_context_covered": True,
        "judge_verifier_source_separation_covered": True,
        "additive_role_correction_sign_reversal_disclosed": True,
        "within_batch_whitening_replayed": True,
        "nested_privileged_role_judge_metadata_rejected": privileged_rejected,
        "cross_segment_source_join_rejected": cross_identity_rejected,
        "synthetic_benchmark_rows_or_content_read": False,
    }


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    control_paths = {str(path): ordinary(root, path) for path in CONTROL_FILES}
    guard_paths = {
        str(path): ordinary(root, path) for path in ACTIVE_FORWARD_GUARD_FILES
    }
    control_manifest = {
        relative: sha256(path) for relative, path in control_paths.items()
    }
    guard_manifest = {
        relative: sha256(path) for relative, path in guard_paths.items()
    }
    static = audit_python_source(
        control_paths[str(MODULE)].read_text(encoding="utf-8")
    )
    replay = replay_synthetic_contracts()
    module_name = "v24225_triage_role_baseline"
    guard_hits = {
        relative: path.read_text(encoding="utf-8").count(module_name)
        for relative, path in guard_paths.items()
    }
    if any(guard_hits.values()):
        raise RuntimeError("V2.42.25 is imported by an active forward entrypoint")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": (
            int(time.time()) if created_at_unix is None else int(created_at_unix)
        ),
        "policy_id": POLICY_ID,
        "label_blind_forward": True,
        "build_only": True,
        "baseline_only": True,
        "control_surface": {
            "file_count": len(control_manifest),
            "manifest": control_manifest,
            "manifest_sha256": payload_sha256(control_manifest),
        },
        "active_forward_guard": {
            "file_count": len(guard_manifest),
            "manifest": guard_manifest,
            "guard_manifest_sha256": payload_sha256(guard_manifest),
            "module_name_hit_count_by_file": guard_hits,
            "module_absent_from_guarded_forward_entrypoints": True,
        },
        "static_capability_audit": static,
        "synthetic_contract_replay": replay,
        "scientific_scope": {
            "triage_v3_four_role_constants_and_additive_formula_implemented": True,
            "bounded_local_judge_context_5_previous_and_5_future_pairs": True,
            "final_verifier_outcome_unavailable_to_role_judge": True,
            "role_judge_label_unavailable_to_verifier": True,
            "post_terminal_outcome_advantage_bound_separately": True,
            "within_batch_whitening_implemented": True,
            "judge_calls_and_token_cost_recorded": True,
            "additive_baseline_can_reverse_verifier_direction": True,
            "role_typing_is_causal_identification": False,
            "role_judge_semantic_correctness_proven": False,
            "real_role_judgments_or_outcome_records_observed": False,
            "gate2b_evaluated": False,
            "training_effect_observed": False,
            "benchmark_quality_or_cost_effect_observed": False,
        },
        "source_policy": {
            "repository_control_code_and_synthetic_hashes_only": True,
            "runtime_task_question_query_raw_evidence_url_prediction_or_answer_read": False,
            "benchmark_subset_category_question_type_label_split_or_mapping_read": False,
            "gold_evaluator_payload_score_reward_or_results_read": False,
            "isolated_post_terminal_outcome_advantage_schema_only": True,
            "credential_environment_keyring_or_secret_value_read": False,
            "network_model_search_fetch_subprocess_or_api_called": False,
        },
        "authorization": {
            "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
            "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
            "active_forward_prompt_model_search_budget_or_controller_change": False,
            "process_signal_restart_resume_rerun_or_selective_retry": False,
            "candidate_materialization_or_package_gate": False,
            "benchmark_forward_dev64_full220_or_evaluator_launch": False,
            "shared_api_lease_acquire": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "claims": {
            "build_only_baseline_available": True,
            "runtime_integration_available": False,
            "real_credit_estimate_available": False,
            "benchmark_score_available": False,
            "benchmark_improvement_observed": False,
            "training_improvement_observed": False,
            "leaderboard_submission_performed": False,
            "sota": False,
        },
        "audit_valid": True,
    }
    encoded = json.dumps(value, ensure_ascii=False)
    if SECRET_LITERAL.search(encoded) or OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.25 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.25 audit output path is noncanonical")
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
