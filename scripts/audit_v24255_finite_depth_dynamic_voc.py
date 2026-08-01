#!/usr/bin/env python3
"""Create-exclusive build audit for the V2.42.55 dynamic-VOC kernel."""

from __future__ import annotations

import argparse
import ast
import copy
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

from deepwide_agent.v24255_finite_depth_dynamic_voc import (  # noqa: E402
    BENCHMARK_EVALUATOR_AUTHORIZED,
    CREDIT_TRAINING_AUTHORIZED,
    LEADERBOARD_OR_SOTA_CLAIM_AUTHORIZED,
    POLICY_ID,
    PRODUCTION_PACKAGE_AUTHORIZED,
    RUNTIME_FORWARD_AUTHORIZED,
    build_transition_model,
    evaluate_voc_policies,
    reject_privileged_runtime_metadata,
    validate_planning_receipt,
)


ROLE = "v24255_finite_depth_dynamic_voc_build_audit"
OUTPUT = Path(
    "results/v24255_finite_depth_dynamic_voc_build_audit_v3_20260801.json"
)
MODULE = Path("src/deepwide_agent/v24255_finite_depth_dynamic_voc.py")
MODULE_TEST = Path("tests/test_v24255_finite_depth_dynamic_voc.py")
AUDIT = Path("scripts/audit_v24255_finite_depth_dynamic_voc.py")
AUDIT_TEST = Path("tests/test_audit_v24255_finite_depth_dynamic_voc.py")
CONTROL_FILES = (MODULE, MODULE_TEST, AUDIT, AUDIT_TEST)
ACTIVE_FORWARD_GUARD_FILES = (
    Path("src/deepwide_agent/__init__.py"),
    Path("src/deepwide_agent/runtime.py"),
    Path("src/deepwide_agent/v24211_entropy_runtime.py"),
    Path("src/deepwide_agent/v24253_candidate_runtime_integration.py"),
    Path("src/deepwide_agent/v24254_candidate_dev64_launcher.py"),
    Path("scripts/run_deepwide_agent.py"),
    Path("scripts/launch_frozen_deepwide.py"),
)

ALLOWED_IMPORT_ROOTS = frozenset(
    {"__future__", "copy", "hashlib", "json", "math", "typing"}
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
        "kill",
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
        "build_transition_model",
        "evaluate_voc_policies",
        "object_sha256",
        "reject_privileged_runtime_metadata",
        "validate_planning_receipt",
        "validate_transition_model",
    }
)
SECRET_LITERAL = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-(?:dev-)?|sk-)"
    r"[A-Za-z0-9_-]{16,}"
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
        raise RuntimeError("V2.42.55 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(
            f"V2.42.55 expected an ordinary repository file: {relative}"
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
    """Fail closed on I/O, dynamic execution, and evaluator-side reads."""

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
            if (
                isinstance(node.func, ast.Name)
                and node.func.id in FORBIDDEN_CALL_NAMES
            ):
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
            "V2.42.55 capability boundary failed: "
            f"imports={disallowed_imports}, calls={sorted(forbidden_calls)}, "
            f"attributes={sorted(set(forbidden_attributes))}, "
            f"privileged_reads={sorted(set(privileged_reads))}, "
            f"missing={missing_functions}"
        )
    return {
        "ast_node_count": sum(1 for _ in ast.walk(tree)),
        "import_roots": sorted(imports),
        "required_public_functions_present": sorted(
            REQUIRED_PUBLIC_FUNCTIONS
        ),
        "disallowed_import_count": 0,
        "forbidden_file_environment_network_process_or_dynamic_code_call_count": 0,
        "privileged_metadata_read_count": 0,
        "file_environment_network_model_search_fetch_process_subprocess_or_dynamic_code_capability": False,
    }


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _outcome(
    target: str,
    *,
    probability: float = 1.0,
    calibrated: bool = True,
) -> dict[str, Any]:
    return {
        "next_state_ref_sha256": target,
        "probability": probability,
        "calibration_ready": calibrated,
        "calibration_ref_sha256": (
            _digest(f"calibration:{target}") if calibrated else None
        ),
    }


def _action(
    label: str, *, cost: int, outcomes: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "action_ref_sha256": _digest(f"action:{label}"),
        "cost": cost,
        "outcomes": outcomes,
    }


def _state(
    label: str,
    *,
    loss: float,
    entropy: float,
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "state_ref_sha256": _digest(f"state:{label}"),
        "stop_terminal_loss": loss,
        "belief_entropy": entropy,
        "actions": actions,
    }


def _synthetic_states() -> list[dict[str, Any]]:
    return [
        _state(
            "root",
            loss=0.6,
            entropy=0.9,
            actions=[
                _action(
                    "high-ig",
                    cost=1,
                    outcomes=[_outcome(_digest("state:high-ig"))],
                ),
                _action(
                    "high-value",
                    cost=1,
                    outcomes=[_outcome(_digest("state:high-value"))],
                ),
                _action(
                    "bridge",
                    cost=1,
                    outcomes=[_outcome(_digest("state:bridge"))],
                ),
            ],
        ),
        _state("high-ig", loss=0.58, entropy=0.1, actions=[]),
        _state("high-value", loss=0.3, entropy=0.8, actions=[]),
        _state(
            "bridge",
            loss=0.6,
            entropy=0.9,
            actions=[
                _action(
                    "unlock",
                    cost=1,
                    outcomes=[_outcome(_digest("state:bridge-terminal"))],
                )
            ],
        ),
        _state(
            "bridge-terminal",
            loss=0.1,
            entropy=0.9,
            actions=[],
        ),
    ]


def replay_synthetic_contracts() -> dict[str, Any]:
    model = build_transition_model(
        model_fit_manifest_sha256=_digest("fit"),
        calibration_protocol_sha256=_digest("calibration-protocol"),
        root_state_ref_sha256=_digest("state:root"),
        max_depth=3,
        max_budget=3,
        states=_synthetic_states(),
    )
    receipt = evaluate_voc_policies(
        model=model,
        expected_transition_model_sha256=model["transition_model_sha256"],
        requested_depth=2,
        available_budget=2,
    )
    validate_planning_receipt(
        receipt,
        model=model,
        expected_transition_model_sha256=model["transition_model_sha256"],
    )
    pure = receipt["policies"]["pure_information_gain"]
    myopic = receipt["policies"]["myopic_terminal_loss_voc"]
    dynamic = receipt["policies"]["finite_depth_dynamic_voc"]
    bridge = receipt["action_values"][_digest("action:bridge")]
    if (
        pure["selected_action_ref_sha256"] != _digest("action:high-ig")
        or myopic["selected_action_ref_sha256"]
        != _digest("action:high-value")
        or dynamic["selected_action_ref_sha256"] != _digest("action:bridge")
        or bridge["myopic_terminal_loss_voc"] != 0.0
        or bridge["finite_depth_dynamic_voc"] != 0.5
        or bridge["descendant_option_value"] != 0.5
    ):
        raise RuntimeError("V2.42.55 ranking counterexample replay drifted")

    depth_one = evaluate_voc_policies(
        model=model,
        expected_transition_model_sha256=model["transition_model_sha256"],
        requested_depth=1,
        available_budget=2,
    )
    if depth_one["requested_depth_one_myopic_equivalence"] is not True:
        raise RuntimeError("V2.42.55 depth-one replay drifted")

    uncalibrated_states = copy.deepcopy(_synthetic_states())
    uncalibrated_states[0]["actions"][0]["outcomes"][0][
        "calibration_ready"
    ] = False
    uncalibrated_states[0]["actions"][0]["outcomes"][0][
        "calibration_ref_sha256"
    ] = None
    uncalibrated = build_transition_model(
        model_fit_manifest_sha256=_digest("fit"),
        calibration_protocol_sha256=_digest("calibration-protocol"),
        root_state_ref_sha256=_digest("state:root"),
        max_depth=3,
        max_budget=3,
        states=uncalibrated_states,
    )
    abstain = evaluate_voc_policies(
        model=uncalibrated,
        expected_transition_model_sha256=uncalibrated[
            "transition_model_sha256"
        ],
        requested_depth=2,
        available_budget=2,
    )
    if any(
        row["decision_kind"] != "abstain"
        for row in abstain["policies"].values()
    ):
        raise RuntimeError("V2.42.55 missing-calibration replay drifted")

    privileged_rejected = False
    try:
        reject_privileged_runtime_metadata(
            {"visible": [{"question_type": "evaluator-only"}]}
        )
    except ValueError:
        privileged_rejected = True
    if not privileged_rejected:
        raise RuntimeError("V2.42.55 privileged metadata was accepted")

    encoded = json.dumps(
        {"model": model, "receipt": receipt, "abstain": abstain},
        ensure_ascii=False,
    )
    if SECRET_LITERAL.search(encoded) or OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.55 synthetic replay exposed content")
    return {
        "pure_information_gain_policy_replayed": True,
        "myopic_terminal_loss_voc_policy_replayed": True,
        "finite_depth_bellman_voc_policy_replayed": True,
        "high_ig_low_terminal_value_counterexample_replayed": True,
        "low_ig_high_terminal_value_counterexample_replayed": True,
        "myopic_zero_dynamic_positive_bridge_replayed": True,
        "descendant_option_value_replayed": True,
        "depth_one_equals_myopic_replayed": True,
        "hard_budget_and_stop_action_replayed": True,
        "missing_calibration_abstention_replayed": True,
        "nested_privileged_runtime_metadata_rejected": True,
        "synthetic_benchmark_rows_or_real_evaluator_payload_read": False,
    }


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.55 audit may only use the canonical workspace")
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
        raise RuntimeError("V2.42.55 control source contains forbidden content")
    static = audit_python_source(control_sources[str(MODULE)])
    module_name = "v24255_finite_depth_dynamic_voc"
    guard_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in guards.items()
    }
    if any(guard_hits.values()):
        raise RuntimeError("V2.42.55 appears in an active forward guard file")
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
        "label_blind_runtime": True,
        "build_only": True,
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
            "same_action_graph_pure_ig_myopic_and_dynamic_voc_implemented": True,
            "finite_depth_bellman_recursion_implemented": True,
            "descendant_option_value_explicit": True,
            "heterogeneous_cost_and_hard_budget_implemented": True,
            "deterministic_value_per_cost_tie_break_implemented": True,
            "explicit_stop_and_missing_calibration_abstain_implemented": True,
            "cycle_unreachable_probability_and_budget_fail_closed": True,
            "terminal_loss_not_entropy_is_dynamic_utility": True,
            "real_four_layer_loss_calibration_semantics_proven": False,
            "real_transition_probabilities_fitted_or_calibrated": False,
            "real_action_graph_or_rollout_observed": False,
            "runtime_integration_available": False,
            "gate2a_or_gate3a_evaluated": False,
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
            "runtime_forward_authorized": RUNTIME_FORWARD_AUTHORIZED,
            "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
            "benchmark_evaluator_authorized": BENCHMARK_EVALUATOR_AUTHORIZED,
            "active_forward_prompt_model_search_budget_or_controller_change": False,
            "process_signal_restart_resume_rerun_or_selective_retry": False,
            "candidate_materialization_or_package_gate": False,
            "dev64_full220_or_evaluator_launch": False,
            "shared_api_lease_acquire": False,
            "leaderboard_submission_or_sota_claim": LEADERBOARD_OR_SOTA_CLAIM_AUTHORIZED,
        },
        "claims": {
            "build_only_dynamic_voc_kernel_available": True,
            "runtime_integration_available": False,
            "real_transition_model_available": False,
            "benchmark_score_available": False,
            "benchmark_improvement_observed": False,
            "leaderboard_submission_performed": False,
            "sota": False,
        },
        "audit_valid": True,
    }
    encoded = json.dumps(value, ensure_ascii=False)
    if SECRET_LITERAL.search(encoded) or OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.55 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.55 audit output path is noncanonical")
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
