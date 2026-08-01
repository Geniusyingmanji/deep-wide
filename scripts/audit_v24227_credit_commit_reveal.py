#!/usr/bin/env python3
"""Create-exclusive build audit for V2.42.27 credit commit/reveal ordering."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepwide_agent.v24223_sign_preserving_credit import object_sha256  # noqa: E402
from deepwide_agent.v24227_credit_commit_reveal import (  # noqa: E402
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CREDIT_TRAINING_AUTHORIZED,
    GATE2B_PASS_AUTHORIZED,
    OUTER_CAMPAIGN_EXECUTION_AUTHORIZED,
    POLICY_ID,
    PRODUCTION_PACKAGE_AUTHORIZED,
    CreditOuterSequenceStore,
    build_commit_reveal_protocol,
)
from tests.test_v24226_credit_outer_target_firewall import (  # noqa: E402
    components,
    digest,
    pair,
)


ROLE = "v24227_credit_commit_reveal_build_audit"
OUTPUT = Path("results/v24227_credit_commit_reveal_build_audit_v1_20260801.json")
MODULE = Path("src/deepwide_agent/v24227_credit_commit_reveal.py")
MODULE_TEST = Path("tests/test_v24227_credit_commit_reveal.py")
AUDIT = Path("scripts/audit_v24227_credit_commit_reveal.py")
AUDIT_TEST = Path("tests/test_audit_v24227_credit_commit_reveal.py")
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
        "copy",
        "hashlib",
        "json",
        "os",
        "pathlib",
        "stat",
        "typing",
        "v2409_interventions",
        "v24123_release",
        "v24223_sign_preserving_credit",
        "v24226_credit_outer_target_firewall",
    }
)
ALLOWED_OS_ATTRIBUTES = frozenset(
    {
        "O_CREAT",
        "O_EXCL",
        "O_DIRECTORY",
        "O_NOFOLLOW",
        "O_RDONLY",
        "O_WRONLY",
        "close",
        "fdopen",
        "fstat",
        "fsync",
        "mkdir",
        "open",
        "read",
        "urandom",
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
FORBIDDEN_ATTRIBUTE_CALLS = frozenset(
    {
        "connect",
        "chmod",
        "fork",
        "getenv",
        "glob",
        "hardlink_to",
        "mkdir",
        "open",
        "popen",
        "read_bytes",
        "read_text",
        "readlink",
        "rename",
        "replace",
        "request",
        "rglob",
        "rmdir",
        "spawn",
        "symlink_to",
        "system",
        "touch",
        "unlink",
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
        "benchmark_subset",
        "category",
        "evaluator_payload",
        "evaluator_score",
        "gold",
        "ground_truth",
        "mapping",
        "official_metrics",
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
        "build_commit_reveal_protocol",
        "validate_commit_reveal_protocol",
        "validate_prediction_commitment",
        "validate_launch_receipt",
        "validate_outer_reservation_receipt",
        "validate_reveal_receipt",
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
        raise RuntimeError("V2.42.27 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(
            f"V2.42.27 expected an ordinary repository file: {relative}"
        )
    return path


def _literal_key(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.casefold()
    return None


def audit_python_source(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    imports: set[str] = set()
    functions: set[str] = set()
    forbidden_calls: list[str] = []
    forbidden_attribute_calls: list[str] = []
    disallowed_os_attributes: list[str] = []
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
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in FORBIDDEN_ATTRIBUTE_CALLS
                and not (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "os"
                    and node.func.attr in ALLOWED_OS_ATTRIBUTES
                )
            ):
                forbidden_attribute_calls.append(node.func.attr)
            if (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
                and node.func.attr not in ALLOWED_OS_ATTRIBUTES
            ):
                disallowed_os_attributes.append(node.func.attr)
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and node.args
            ):
                key = _literal_key(node.args[0])
                if key in FORBIDDEN_METADATA_ACCESS_KEYS:
                    privileged_reads.append(key)
        elif isinstance(node, ast.Subscript):
            key = _literal_key(node.slice)
            if key in FORBIDDEN_METADATA_ACCESS_KEYS:
                privileged_reads.append(key)
        elif (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "os"
            and node.attr not in ALLOWED_OS_ATTRIBUTES
        ):
            disallowed_os_attributes.append(node.attr)
    disallowed_imports = sorted(imports - ALLOWED_IMPORT_ROOTS)
    missing_functions = sorted(REQUIRED_PUBLIC_FUNCTIONS - functions)
    class_names = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
    }
    missing_class = "CreditOuterSequenceStore" not in class_names
    if (
        disallowed_imports
        or forbidden_calls
        or forbidden_attribute_calls
        or disallowed_os_attributes
        or privileged_reads
        or missing_functions
        or missing_class
    ):
        raise RuntimeError(
            "V2.42.27 capability boundary failed: "
            f"imports={disallowed_imports}, calls={sorted(forbidden_calls)}, "
            f"attribute_calls={sorted(set(forbidden_attribute_calls))}, "
            f"os={sorted(set(disallowed_os_attributes))}, "
            f"privileged_reads={sorted(set(privileged_reads))}, "
            f"missing={missing_functions}, missing_store={missing_class}"
        )
    return {
        "ast_node_count": sum(1 for _ in ast.walk(tree)),
        "import_roots": sorted(imports),
        "required_public_functions_present": sorted(REQUIRED_PUBLIC_FUNCTIONS),
        "fixed_path_store_class_present": True,
        "disallowed_import_count": 0,
        "forbidden_dynamic_code_or_builtin_open_call_count": 0,
        "forbidden_path_network_process_or_reflection_call_count": 0,
        "disallowed_os_attribute_count": 0,
        "privileged_metadata_read_count": 0,
        "network_process_environment_or_subprocess_capability": False,
        "narrow_create_exclusive_file_io_and_os_randomness_capability": True,
    }


def _sequence_protocol(values: dict[str, object], namespace: str) -> dict[str, Any]:
    return build_commit_reveal_protocol(
        outer_target_protocol=values["protocol"],  # type: ignore[arg-type]
        sequence_namespace_sha256=namespace,
        coordinator_contract_sha256=digest("2"),
        launch_policy_sha256=digest("3"),
    )


def _commit(
    store: CreditOuterSequenceStore,
    protocol: dict[str, Any],
    values: dict[str, object],
) -> dict[str, Any]:
    return store.commit(
        protocol=protocol,
        prediction_freeze=values["freeze"],  # type: ignore[arg-type]
        outer_seed_schedule_sha256=digest("4"),
        outer_execution_contract_sha256=digest("5"),
        outer_evaluator_protocol_sha256=digest("6"),
    )


def replay_synthetic_contracts() -> dict[str, Any]:
    values = components()
    valid_pair = pair(values)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        namespace = digest("1")
        protocol = _sequence_protocol(values, namespace)
        store = CreditOuterSequenceStore(
            root=root, sequence_namespace_sha256=namespace
        )
        commitment = _commit(store, protocol, values)
        outer_absent_at_commit = not store.outer_directory.exists()
        launch = store.open_launch(launch_request_sha256=digest("7"))
        reservation = store._read_object(store.outer_reservation_path)
        store.publish_outer_pair(pair=valid_pair)
        reveal = store.reveal()
        replayed = store.validate_complete_sequence()
        valid_complete = replayed == reveal
        exact_parent_bindings = all(
            (
                reveal["prediction_commitment_sha256"]
                == commitment["commitment_sha256"],
                reveal["outer_launch_receipt_sha256"]
                == launch["launch_receipt_sha256"],
                reveal["outer_reservation_receipt_sha256"]
                == reservation["reservation_sha256"],
                reveal["outer_pair_sha256"] == valid_pair["pair_sha256"],
            )
        )

    skipped_pair_rejected = False
    skipped_reveal_rejected = False
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        namespace = digest("8")
        protocol = _sequence_protocol(values, namespace)
        store = CreditOuterSequenceStore(
            root=root, sequence_namespace_sha256=namespace
        )
        _commit(store, protocol, values)
        try:
            store.publish_outer_pair(pair=valid_pair)
        except (FileNotFoundError, ValueError):
            skipped_pair_rejected = True
        store.open_launch(launch_request_sha256=digest("7"))
        try:
            store.reveal()
        except (FileNotFoundError, ValueError):
            skipped_reveal_rejected = True

    wrong_pair_rejected = False
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        namespace = digest("9")
        protocol = _sequence_protocol(values, namespace)
        store = CreditOuterSequenceStore(
            root=root, sequence_namespace_sha256=namespace
        )
        _commit(store, protocol, values)
        store.open_launch(launch_request_sha256=digest("7"))
        wrong = copy.deepcopy(valid_pair)
        wrong["semantic_bundle_sha256"] = digest("a")
        wrong.pop("pair_sha256")
        wrong["pair_sha256"] = object_sha256(wrong)
        try:
            store.publish_outer_pair(pair=wrong)
        except ValueError:
            wrong_pair_rejected = True

    residue_rejected = False
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        namespace = digest("b")
        protocol = _sequence_protocol(values, namespace)
        store = CreditOuterSequenceStore(
            root=root, sequence_namespace_sha256=namespace
        )
        _commit(store, protocol, values)
        store.open_launch(launch_request_sha256=digest("7"))
        residue = store.outer_directory / "residue"
        descriptor = os.open(
            residue, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
        )
        os.close(descriptor)
        try:
            store.publish_outer_pair(pair=valid_pair)
        except ValueError:
            residue_rejected = True

    required = (
        outer_absent_at_commit,
        valid_complete,
        exact_parent_bindings,
        skipped_pair_rejected,
        skipped_reveal_rejected,
        wrong_pair_rejected,
        residue_rejected,
        reveal["repository_commit_launch_reveal_order_enforced"] is True,
        reveal["external_target_precomputation_excluded"] is False,
        reveal["trusted_physical_wall_clock_used"] is False,
        reveal["outer_pair_native_launch_challenge_binding_present"] is False,
        reveal["formal_gate2b_evaluation_authorized"] is False,
    )
    if not all(required):
        raise RuntimeError("V2.42.27 synthetic sequence replay drifted")
    return {
        "prediction_committed_before_outer_root_exists": outer_absent_at_commit,
        "launch_receipt_and_reservation_replayed": True,
        "valid_complete_sequence_replayed": valid_complete,
        "exact_parent_hash_bindings_replayed": exact_parent_bindings,
        "pair_before_launch_rejected": skipped_pair_rejected,
        "reveal_before_pair_rejected": skipped_reveal_rejected,
        "resealed_wrong_campaign_pair_rejected": wrong_pair_rejected,
        "uncommitted_outer_residue_rejected": residue_rejected,
        "create_exclusive_stage_publication_replayed": True,
        "post_prediction_synthetic_outer_target_contribution_validated": True,
        "outer_target_used_for_runtime_routing_or_same_forward_pass": False,
        "physical_time_or_external_precomputation_claimed": False,
        "native_launch_challenge_bound_inside_v24226_pair": False,
        "synthetic_benchmark_rows_or_real_evaluator_payload_read": False,
    }


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.27 audit may only use the canonical workspace")
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
        raise RuntimeError("V2.42.27 control source contains forbidden content")
    module_source = control_sources[str(MODULE)]
    static = audit_python_source(module_source)
    module_name = "v24227_credit_commit_reveal"
    guard_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in guards.items()
    }
    gate_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in gate_guards.items()
    }
    if any(guard_hits.values()):
        raise RuntimeError("V2.42.27 appears in an active forward guard file")
    if any(gate_hits.values()):
        raise RuntimeError("V2.42.27 unexpectedly changed historical Gate 2B")
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
            "historical_gate_authorizes_formal_gate2b_after_v24227": False,
        },
        "static_capability_audit": static,
        "control_source_forbidden_literal_scan": {
            "file_count": len(source_secret_hits),
            "hit_count": 0,
            "secret_or_concrete_opaque_id_literal_present": False,
        },
        "synthetic_contract_replay": replay,
        "scientific_scope": {
            "repository_local_commit_launch_reserve_pair_reveal_order_enforced": True,
            "prediction_freeze_bound_to_exact_v24226_protocol": True,
            "outer_pair_bound_to_exact_committed_campaign": True,
            "create_exclusive_stage_files_and_residue_rejection_implemented": True,
            "local_file_and_directory_fsync_implemented": True,
            "post_prediction_outer_target_available_only_to_reveal_validation": True,
            "trusted_physical_clock_used": False,
            "external_target_precomputation_excluded": False,
            "hostile_concurrent_filesystem_mutation_excluded": False,
            "independent_append_only_or_transparency_service_used": False,
            "store_api_execution_independently_attested": False,
            "offline_self_consistent_chain_fabrication_cryptographically_excluded": False,
            "pair_native_launch_challenge_binding_present": False,
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
            "synthetic_post_prediction_outer_target_contribution_validated": True,
            "credential_environment_keyring_or_secret_value_read": False,
            "network_model_search_fetch_subprocess_or_api_called": False,
        },
        "authorization": {
            "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
            "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
            "gate2b_pass_authorized": GATE2B_PASS_AUTHORIZED,
            "outer_campaign_execution_authorized": OUTER_CAMPAIGN_EXECUTION_AUTHORIZED,
            "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
            "active_forward_prompt_model_search_budget_or_controller_change": False,
            "process_signal_restart_resume_rerun_or_selective_retry": False,
            "candidate_materialization_or_package_gate": False,
            "shared_api_lease_acquire": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "claims": {
            "build_only_commit_reveal_store_available": True,
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
        raise RuntimeError("V2.42.27 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.27 audit output path is noncanonical")
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
