#!/usr/bin/env python3
"""Create-exclusive build audit for the V2.42.28 challenge-bound graph."""

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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepwide_agent.v24228_challenge_bound_outer_graph import (  # noqa: E402
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CREDIT_TRAINING_AUTHORIZED,
    EXTERNAL_TARGET_PRECOMPUTATION_EXCLUDED,
    FORMAL_GATE2B_EVALUATION_AUTHORIZED,
    GATE2B_PASS_AUTHORIZED,
    OUTER_CAMPAIGN_EXECUTION_AUTHORIZED,
    POLICY_ID,
    PRODUCTION_PACKAGE_AUTHORIZED,
    STORE_API_EXECUTION_INDEPENDENTLY_ATTESTED,
)
from tests.test_v24228_challenge_bound_outer_graph import (  # noqa: E402
    V24228ChallengeBoundOuterGraphTests,
)


ROLE = "v24228_challenge_bound_outer_graph_build_audit"
OUTPUT = Path(
    "results/v24228_challenge_bound_outer_graph_build_audit_v1_20260801.json"
)
MODULE = Path("src/deepwide_agent/v24228_challenge_bound_outer_graph.py")
MODULE_TEST = Path("tests/test_v24228_challenge_bound_outer_graph.py")
AUDIT = Path("scripts/audit_v24228_challenge_bound_outer_graph.py")
AUDIT_TEST = Path("tests/test_audit_v24228_challenge_bound_outer_graph.py")
CONTROL_FILES = (MODULE, MODULE_TEST, AUDIT, AUDIT_TEST)
ACTIVE_FORWARD_GUARD_FILES = (
    Path("src/deepwide_agent/__init__.py"),
    Path("src/deepwide_agent/runtime.py"),
    Path("src/deepwide_agent/v24211_entropy_runtime.py"),
    Path("scripts/run_deepwide_agent.py"),
    Path("scripts/launch_frozen_deepwide.py"),
)
FORMAL_GATE_GUARD_FILES = (
    Path("scripts/evaluate_v2405_information_credit_gates.py"),
    Path("tests/test_evaluate_v2405_owic_gate2b.py"),
)

ALLOWED_IMPORT_ROOTS = frozenset(
    {
        "__future__",
        "abc",
        "collections",
        "copy",
        "hashlib",
        "json",
        "math",
        "typing",
        "v24123_release",
        "v24223_sign_preserving_credit",
        "v24224_credit_source_adapter",
        "v24226_credit_outer_target_firewall",
        "v24227_credit_commit_reveal",
    }
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
FORBIDDEN_METADATA_ACCESS_KEYS = frozenset(
    {
        "answer",
        "answer_key",
        "benchmark_category",
        "benchmark_subset",
        "category",
        "evaluator_payload",
        "evaluator_score",
        "gold",
        "ground_truth",
        "mapping",
        "question_type",
        "results.csv",
        "reward",
        "score",
        "split",
        "task_category",
    }
)
REQUIRED_PUBLIC_FUNCTIONS = frozenset(
    {
        "build_challenge_bound_outer_pair",
        "build_challenge_contribution_record",
        "build_challenge_evaluated_terminal",
        "build_challenge_evaluator_provenance",
        "build_challenge_execution_request",
        "build_challenge_graph_protocol",
        "build_challenge_prediction_freeze",
        "build_challenge_replicate_aggregate",
        "build_unsigned_executor_declaration",
        "validate_challenge_bound_outer_pair",
        "validate_challenge_contribution_record",
        "validate_challenge_evaluated_terminal",
        "validate_challenge_evaluator_provenance",
        "validate_challenge_execution_request",
        "validate_challenge_graph_protocol",
        "validate_challenge_prediction_freeze",
        "validate_challenge_replicate_aggregate",
        "validate_unsigned_executor_declaration",
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
        raise RuntimeError("V2.42.28 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(
            f"V2.42.28 expected an ordinary repository file: {relative}"
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
                imports.add(node.module.rsplit(".", 1)[-1])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.add(node.name)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALL_NAMES:
                forbidden_calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                root = _attribute_root(node.func)
                if root in FORBIDDEN_ATTRIBUTE_ROOTS:
                    forbidden_attributes.append(f"{root}.{node.func.attr}")
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
            "V2.42.28 capability boundary failed: "
            f"imports={disallowed_imports}, calls={sorted(forbidden_calls)}, "
            f"attributes={sorted(forbidden_attributes)}, "
            f"privileged_reads={sorted(set(privileged_reads))}, "
            f"missing={missing_functions}"
        )
    return {
        "ast_node_count": sum(1 for _ in ast.walk(tree)),
        "import_roots": sorted(imports),
        "required_public_functions_present": sorted(REQUIRED_PUBLIC_FUNCTIONS),
        "disallowed_import_count": 0,
        "forbidden_dynamic_code_file_environment_network_or_process_call_count": 0,
        "privileged_metadata_read_count": 0,
        "file_environment_network_model_search_fetch_process_or_dynamic_code_capability": False,
    }


def replay_synthetic_contracts() -> dict[str, Any]:
    V24228ChallengeBoundOuterGraphTests.setUpClass()
    case = V24228ChallengeBoundOuterGraphTests(methodName="runTest")
    graph = case.build_graph()
    case.validate_graph(graph)
    challenge = case.launch["launch_challenge_sha256"]
    layers = [
        graph["request"],
        graph["freeze"],
        graph["attestation"],
        graph["evaluator"],
        *graph["terminals"],
        *graph["contributions"],
        graph["aggregate"],
        graph["pair"],
    ]
    if any(layer["launch_challenge_sha256"] != challenge for layer in layers):
        raise RuntimeError("V2.42.28 challenge propagation replay drifted")
    pair = graph["pair"]
    attestation = graph["attestation"]
    required_false = (
        pair["challenge_only_at_top_level"],
        pair["legacy_payloads_are_challenge_native"],
        pair["native_executor_consumed_challenge_independently_proven"],
        pair["independent_append_only_or_transparency_service_used"],
        pair["store_api_execution_independently_attested"],
        pair["offline_self_consistent_graph_fabrication_cryptographically_excluded"],
        pair["external_target_precomputation_excluded"],
        pair["formal_gate2b_evaluation_authorized"],
    )
    if (
        any(required_false)
        or pair["all_required_layers_present"] is not True
        or pair["launch_challenge_bound_in_every_envelope_layer"] is not True
        or pair["exact_parent_hash_dag_validated"] is not True
        or pair["legacy_source_graph_replayed_through_v24224"] is not True
        or pair["legacy_v24226_pair_revalidated"] is not True
        or pair["historical_payload_after_wrapping_possible"] is not True
        or attestation["signature_scheme"] != "none"
        or attestation["detached_signature"] is not None
    ):
        raise RuntimeError("V2.42.28 synthetic graph scope drifted")
    return {
        "complete_challenge_graph_replayed": True,
        "required_layer_count": len(layers),
        "launch_challenge_present_in_every_envelope_layer": True,
        "exact_parent_hash_dag_replayed": True,
        "legacy_source_graph_replayed_through_v24224": True,
        "legacy_v24226_pair_revalidated": True,
        "historical_payload_after_wrapping_possible": True,
        "legacy_payloads_challenge_native": False,
        "keyed_or_asymmetric_signature_present": False,
        "independent_append_only_attestation_present": False,
        "external_target_precomputation_excluded": False,
        "formal_gate2b_evaluation_authorized": False,
        "synthetic_benchmark_rows_or_real_evaluator_payload_read": False,
    }


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.28 audit may only use the canonical workspace")
    paths = {str(path): ordinary(root, path) for path in CONTROL_FILES}
    guards = {
        str(path): ordinary(root, path) for path in ACTIVE_FORWARD_GUARD_FILES
    }
    gate_guards = {
        str(path): ordinary(root, path) for path in FORMAL_GATE_GUARD_FILES
    }
    control_sources = {
        name: path.read_text(encoding="utf-8") for name, path in paths.items()
    }
    source_secret_hits = {
        name: bool(SECRET_LITERAL.search(source) or OPAQUE_ID.search(source))
        for name, source in control_sources.items()
    }
    if any(source_secret_hits.values()):
        raise RuntimeError("V2.42.28 control source contains forbidden content")
    static = audit_python_source(control_sources[str(MODULE)])
    module_name = "v24228_challenge_bound_outer_graph"
    guard_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in guards.items()
    }
    gate_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in gate_guards.items()
    }
    if any(guard_hits.values()):
        raise RuntimeError("V2.42.28 appears in an active forward guard file")
    if any(gate_hits.values()):
        raise RuntimeError("V2.42.28 unexpectedly changed historical Gate 2B")
    control_manifest = {name: sha256(path) for name, path in paths.items()}
    guard_manifest = {name: sha256(path) for name, path in guards.items()}
    gate_manifest = {name: sha256(path) for name, path in gate_guards.items()}
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
        "historical_gate_guard": {
            "file_count": len(gate_manifest),
            "manifest": gate_manifest,
            "manifest_sha256": payload_sha256(gate_manifest),
            "module_name_hit_count_by_file": gate_hits,
            "historical_synthetic_gate_preserved_for_regression_only": True,
            "historical_gate_authorizes_formal_gate2b_after_v24228": False,
        },
        "static_capability_audit": static,
        "control_source_forbidden_literal_scan": {
            "file_count": len(source_secret_hits),
            "hit_count": 0,
            "secret_or_concrete_opaque_id_literal_present": False,
        },
        "synthetic_contract_replay": replay,
        "scientific_scope": {
            "launch_challenge_bound_in_request_freeze_executor_evaluator_terminal_contribution_aggregate_and_pair_envelopes": True,
            "exact_parent_hash_dag_validated": True,
            "legacy_v24123_source_graph_replayed_through_v24224": True,
            "legacy_v24226_pair_revalidated": True,
            "legacy_payload_schemas_modified": False,
            "legacy_payloads_challenge_native": False,
            "historical_payload_after_wrapping_possible": True,
            "executor_declares_challenge_consumed_before_execution": True,
            "executor_challenge_consumption_independently_verified": False,
            "keyed_or_asymmetric_signature_present": False,
            "independent_append_only_or_transparency_service_used": False,
            "store_api_execution_independently_attested": STORE_API_EXECUTION_INDEPENDENTLY_ATTESTED,
            "offline_self_consistent_graph_fabrication_cryptographically_excluded": False,
            "external_target_precomputation_excluded": EXTERNAL_TARGET_PRECOMPUTATION_EXCLUDED,
            "semantic_or_distributional_ood_independently_assessed": False,
            "real_independent_outer_target_data_observed": False,
            "formal_gate2b_evaluated": False,
            "training_effect_observed": False,
            "benchmark_quality_or_cost_effect_observed": False,
        },
        "source_policy": {
            "repository_control_code_and_synthetic_hashes_only": True,
            "runtime_task_question_query_raw_evidence_url_prediction_or_answer_read": False,
            "benchmark_subset_category_question_type_label_split_or_mapping_read": False,
            "gold_or_real_evaluator_payload_score_reward_or_results_read": False,
            "credential_environment_keyring_or_secret_value_read": False,
            "network_model_search_fetch_subprocess_or_api_called": False,
        },
        "authorization": {
            "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
            "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
            "gate2b_pass_authorized": GATE2B_PASS_AUTHORIZED,
            "formal_gate2b_evaluation_authorized": FORMAL_GATE2B_EVALUATION_AUTHORIZED,
            "outer_campaign_execution_authorized": OUTER_CAMPAIGN_EXECUTION_AUTHORIZED,
            "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
            "active_forward_prompt_model_search_budget_or_controller_change": False,
            "process_signal_restart_resume_rerun_or_selective_retry": False,
            "candidate_materialization_or_package_gate": False,
            "shared_api_lease_acquire": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "claims": {
            "build_only_challenge_bound_compatibility_graph_available": True,
            "native_challenge_consuming_executor_available": False,
            "independent_executor_attestation_available": False,
            "formal_gate2b_evaluator_available": False,
            "real_independent_outer_target_pairs_available": False,
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
        raise RuntimeError("V2.42.28 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.28 audit output path is noncanonical")
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
