#!/usr/bin/env python3
"""Create-exclusive build audit for the V2.42.30 MICA credit baseline."""

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

from deepwide_agent.v24230_mica_credit_baseline import (  # noqa: E402
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CREDIT_TRAINING_AUTHORIZED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    NORMALIZATION_EPSILON,
    POLICY_ID,
    PRODUCTION_PACKAGE_AUTHORIZED,
    build_mica_mixed_advantage_batch,
    build_mica_policy,
    build_potential_transition,
    reject_privileged_runtime_metadata,
    validate_mica_mixed_advantage_batch,
)


ROLE = "v24230_mica_credit_baseline_build_audit"
OUTPUT = Path("results/v24230_mica_credit_baseline_build_audit_v1_20260801.json")
MODULE = Path("src/deepwide_agent/v24230_mica_credit_baseline.py")
MODULE_TEST = Path("tests/test_v24230_mica_credit_baseline.py")
AUDIT = Path("scripts/audit_v24230_mica_credit_baseline.py")
AUDIT_TEST = Path("tests/test_audit_v24230_mica_credit_baseline.py")
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
    {
        "__import__",
        "breakpoint",
        "compile",
        "eval",
        "exec",
        "getattr",
        "globals",
        "input",
        "locals",
        "open",
        "setattr",
        "vars",
    }
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
FORBIDDEN_ATTRIBUTE_CALLS = frozenset(
    {
        "connect",
        "fork",
        "getenv",
        "glob",
        "open",
        "popen",
        "read_bytes",
        "read_text",
        "request",
        "rglob",
        "spawn",
        "system",
        "urlopen",
        "walk",
        "write_bytes",
        "write_text",
    }
)
FORBIDDEN_METADATA_ACCESS_KEYS = frozenset(
    {
        "answer",
        "answer_key",
        "benchmark_category",
        "benchmark_label",
        "benchmark_subset",
        "category",
        "correctness",
        "evaluator",
        "evaluator_output",
        "evaluator_payload",
        "evaluator_score",
        "final_outcome",
        "gold",
        "ground_truth",
        "mapping",
        "official_metrics",
        "prediction",
        "question_type",
        "results.csv",
        "reward",
        "score",
        "split",
        "task_category",
        "task_id",
        "verifier_outcome",
    }
)
REQUIRED_PUBLIC_FUNCTIONS = frozenset(
    {
        "build_mica_mixed_advantage_batch",
        "build_mica_policy",
        "build_potential_transition",
        "object_sha256",
        "reject_privileged_runtime_metadata",
        "validate_mica_mixed_advantage_batch",
        "validate_mica_policy",
        "validate_potential_transition",
    }
)
SECRET_LITERAL = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-(?:dev-)?|sk-)[A-Za-z0-9_-]{16,}"
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
        raise RuntimeError("V2.42.30 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(
            f"V2.42.30 expected an ordinary repository file: {relative}"
        )
    return path


def _literal_key(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.casefold()
    return None


def _attribute_root(node: ast.Attribute) -> str | None:
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        current = current.value
    return current.id if isinstance(current, ast.Name) else None


def audit_python_source(source: str) -> dict[str, Any]:
    """Fail closed on file, environment, network, process, and dynamic code."""

    tree = ast.parse(source)
    imports: set[str] = set()
    functions: set[str] = set()
    forbidden_calls: list[str] = []
    forbidden_attributes: list[str] = []
    privileged_reads: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".", 1)[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.add(node.name)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALL_NAMES:
                forbidden_calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                root = _attribute_root(node.func)
                if (
                    root in FORBIDDEN_ATTRIBUTE_ROOTS
                    or node.func.attr in FORBIDDEN_ATTRIBUTE_CALLS
                ):
                    forbidden_attributes.append(
                        f"{root}.{node.func.attr}" if root else node.func.attr
                    )
                if node.func.attr == "get" and node.args:
                    key = _literal_key(node.args[0])
                    if key in FORBIDDEN_METADATA_ACCESS_KEYS:
                        privileged_reads.append(str(key))
        elif isinstance(node, ast.Subscript):
            key = _literal_key(node.slice)
            if key in FORBIDDEN_METADATA_ACCESS_KEYS:
                privileged_reads.append(str(key))
    disallowed_imports = sorted(imports - ALLOWED_IMPORT_ROOTS)
    missing_functions = sorted(REQUIRED_PUBLIC_FUNCTIONS - functions)
    if (
        disallowed_imports
        or forbidden_calls
        or forbidden_attributes
        or privileged_reads
        or missing_functions
    ):
        raise RuntimeError(
            "V2.42.30 capability boundary failed: "
            f"imports={disallowed_imports}, calls={sorted(forbidden_calls)}, "
            f"attributes={sorted(set(forbidden_attributes))}, "
            f"privileged_reads={sorted(set(privileged_reads))}, "
            f"missing={missing_functions}"
        )
    return {
        "ast_node_count": sum(1 for _ in ast.walk(tree)),
        "import_roots": sorted(imports),
        "required_public_functions_present": sorted(REQUIRED_PUBLIC_FUNCTIONS),
        "disallowed_import_count": 0,
        "forbidden_file_environment_network_process_or_dynamic_code_call_count": 0,
        "privileged_metadata_read_count": 0,
        "file_environment_network_model_search_fetch_process_subprocess_or_"
        "dynamic_code_capability": False,
    }


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _trajectory(
    policy: dict[str, Any], *, name: str, potentials: list[float]
) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    before_state = _digest("common-initial-state")
    for turn_index, (before, after) in enumerate(
        zip(potentials, potentials[1:]), start=1
    ):
        after_state = _digest(f"{name}-state-{turn_index}")
        values.append(
            build_potential_transition(
                policy=policy,
                prompt_group_ref_sha256=_digest("prompt-group"),
                trajectory_ref_sha256=_digest(f"trajectory-{name}"),
                segment_ref_sha256=_digest(f"segment-{name}-{turn_index}"),
                turn_index=turn_index,
                state_before_projection_sha256=before_state,
                state_after_projection_sha256=after_state,
                dense_feedback_receipt_sha256=_digest(
                    f"dense-feedback-{name}-{turn_index}"
                ),
                previous_potential=before,
                current_potential=after,
                dense_feedback_calls=1,
                dense_feedback_input_tokens=10,
                dense_feedback_output_tokens=2,
                data_scope="preregistered_training",
            )
        )
        before_state = after_state
    return values


def replay_synthetic_contracts() -> dict[str, Any]:
    policy = build_mica_policy(
        selection_protocol_sha256=_digest("selection-protocol"),
        potential_definition_sha256=_digest("potential-definition"),
        dense_feedback_protocol_sha256=_digest("dense-feedback-protocol"),
        discount_factor=0.5,
        turn_return_weight=0.25,
    )
    transitions = _trajectory(
        policy, name="long", potentials=[10.0, 8.0, 7.0]
    ) + _trajectory(policy, name="short", potentials=[10.0, 6.0])
    batch_ref = _digest("batch")
    batch = build_mica_mixed_advantage_batch(
        policy=policy,
        batch_ref_sha256=batch_ref,
        transitions=transitions,
    )
    validate_mica_mixed_advantage_batch(
        batch,
        policy=policy,
        batch_ref_sha256=batch_ref,
        transitions=transitions,
    )
    records = {
        row["segment_ref_sha256"]: row for row in batch["normalized_records"]
    }
    expected_returns = {
        _digest("segment-long-1"): 2.5,
        _digest("segment-long-2"): 1.0,
        _digest("segment-short-1"): 4.0,
    }
    if any(
        records[segment]["monte_carlo_return"] != expected
        for segment, expected in expected_returns.items()
    ):
        raise RuntimeError("V2.42.30 MICA return replay drifted")
    if [row["eligible_trajectory_count"] for row in batch["turn_statistics"]] != [
        2,
        1,
    ]:
        raise RuntimeError("V2.42.30 variable-horizon replay drifted")
    privileged_rejected = False
    try:
        reject_privileged_runtime_metadata(
            {"visible": [{"question_type": "evaluator-only"}]}
        )
    except ValueError:
        privileged_rejected = True
    if not privileged_rejected:
        raise RuntimeError("V2.42.30 privileged metadata replay was accepted")
    if (
        batch["dense_feedback_cost"]
        != {"calls": 3, "input_tokens": 30, "output_tokens": 6}
        or batch["potential_is_causal_state_value"] is not False
        or batch["same_state_causal_identification"] is not False
        or batch["independent_outer_target_used"] is not False
        or batch["runtime_forward_evaluator_or_credit_training_authorized"]
        is not False
    ):
        raise RuntimeError("V2.42.30 scope or cost replay drifted")
    encoded = json.dumps(
        {"policy": policy, "transitions": transitions, "batch": batch},
        ensure_ascii=False,
    )
    if SECRET_LITERAL.search(encoded) or OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.30 synthetic replay exposed forbidden content")
    return {
        "paper_immediate_idr_equation_replayed": True,
        "discounted_monte_carlo_return_equation_replayed": True,
        "same_prompt_same_turn_population_normalization_replayed": True,
        "same_prompt_all_valid_turn_population_normalization_replayed": True,
        "convex_mixed_advantage_replayed": True,
        "variable_horizon_eligible_trajectory_normalization_replayed": True,
        "state_and_potential_continuity_replayed": True,
        "dense_feedback_cost_aggregation_replayed": True,
        "nested_privileged_runtime_metadata_rejected": True,
        "dense_feedback_semantic_correctness_independently_verified": False,
        "potential_is_causal_state_value": False,
        "same_state_causal_identification": False,
        "independent_outer_target_used": False,
        "synthetic_benchmark_rows_or_real_evaluator_payload_read": False,
    }


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.30 audit may only use the canonical workspace")
    paths = {str(path): ordinary(root, path) for path in CONTROL_FILES}
    guards = {
        str(path): ordinary(root, path) for path in ACTIVE_FORWARD_GUARD_FILES
    }
    control_sources = {
        name: path.read_text(encoding="utf-8") for name, path in paths.items()
    }
    forbidden_source_hits = {
        name: bool(SECRET_LITERAL.search(source) or OPAQUE_ID.search(source))
        for name, source in control_sources.items()
    }
    if any(forbidden_source_hits.values()):
        raise RuntimeError("V2.42.30 control source contains forbidden content")
    static = audit_python_source(control_sources[str(MODULE)])
    module_name = "v24230_mica_credit_baseline"
    guard_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in guards.items()
    }
    if any(guard_hits.values()):
        raise RuntimeError("V2.42.30 appears in an active forward guard file")
    control_manifest = {name: sha256(path) for name, path in paths.items()}
    guard_manifest = {name: sha256(path) for name, path in guards.items()}
    replay = replay_synthetic_contracts()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": (
            int(time.time()) if created_at_unix is None else int(created_at_unix)
        ),
        "policy_id": POLICY_ID,
        "source_paper": {
            "arxiv_id": "2603.06194",
            "version": 3,
            "formula_scope": "mica_multi_granularity_intertemporal_credit",
        },
        "label_blind_runtime": True,
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
            "manifest_sha256": payload_sha256(guard_manifest),
            "module_name_hit_count_by_file": guard_hits,
            "module_absent_from_guarded_forward_entrypoints": True,
        },
        "static_capability_audit": static,
        "control_source_forbidden_literal_scan": {
            "file_count": len(forbidden_source_hits),
            "hit_count": 0,
            "credential_or_concrete_opaque_id_literal_present": False,
        },
        "synthetic_contract_replay": replay,
        "scientific_scope": {
            "mica_v3_immediate_idr_return_and_mixed_advantage_implemented": True,
            "gamma_domain_zero_excluded_and_one_included": True,
            "alpha_and_beta_convex_boundary_included": True,
            "population_not_sample_standard_deviation_implemented": True,
            "normalization_epsilon": NORMALIZATION_EPSILON,
            "variable_horizon_eligible_turn_sets_implemented": True,
            "dense_feedback_calls_and_tokens_recorded": True,
            "dense_feedback_limited_to_training_or_calibration_scope": True,
            "dense_feedback_semantic_correctness_proven": False,
            "potential_is_causal_state_value": False,
            "same_state_causal_identification": False,
            "independent_outer_target_used": False,
            "real_rollouts_or_dense_judgments_observed": False,
            "gate2b_evaluated": False,
            "training_effect_observed": False,
            "benchmark_quality_or_cost_effect_observed": False,
        },
        "source_policy": {
            "repository_control_code_and_synthetic_hashes_only": True,
            "runtime_task_question_query_raw_evidence_url_prediction_or_answer_read": False,
            "benchmark_subset_category_question_type_label_split_or_mapping_read": False,
            "gold_evaluator_payload_score_reward_or_results_read": False,
            "credential_environment_keyring_or_secret_value_read": False,
            "network_model_search_fetch_subprocess_or_api_called": False,
        },
        "authorization": {
            "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
            "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
            "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
            "active_forward_prompt_model_search_budget_or_controller_change": False,
            "process_signal_restart_resume_rerun_or_selective_retry": False,
            "candidate_materialization_or_package_gate": False,
            "dev64_full220_or_evaluator_launch": False,
            "shared_api_lease_acquire": False,
            "leaderboard_submission_or_sota_claim": LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
        },
        "claims": {
            "build_only_mica_baseline_available": True,
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
        raise RuntimeError("V2.42.30 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.30 audit output path is noncanonical")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        parent_descriptor = os.open(
            target.parent,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )
        try:
            os.fsync(parent_descriptor)
        finally:
            os.close(parent_descriptor)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
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
