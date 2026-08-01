#!/usr/bin/env python3
"""Create-exclusive build audit for V2.42.29 signed graph verification."""

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

from deepwide_agent.v24229_signed_outer_attestation import (  # noqa: E402
    APPEND_ONLY_TRANSPARENCY_SERVICE_USED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CREDIT_TRAINING_AUTHORIZED,
    EXTERNAL_TARGET_PRECOMPUTATION_EXCLUDED,
    FORMAL_GATE2B_EVALUATION_AUTHORIZED,
    GATE2B_PASS_AUTHORIZED,
    INDEPENDENT_SIGNER_IDENTITY_VERIFIED,
    INDEPENDENT_TRUST_DOMAIN_VERIFIED,
    LAUNCH_BEFORE_EXECUTION_INDEPENDENTLY_ATTESTED,
    OUTER_CAMPAIGN_EXECUTION_AUTHORIZED,
    POLICY_ID,
    PRODUCTION_PACKAGE_AUTHORIZED,
    STATEMENT_TRUTH_INDEPENDENTLY_VERIFIED,
    TRUSTED_TIMESTAMP_VERIFIED,
    canonical_attestation_message,
    validate_verified_signature_receipt,
    verify_rsa_pss_sha256,
)
from tests import test_v24229_signed_outer_attestation as fixture  # noqa: E402


ROLE = "v24229_signed_outer_attestation_build_audit"
OUTPUT = Path(
    "results/v24229_signed_outer_attestation_build_audit_v2_20260801.json"
)
MODULE = Path("src/deepwide_agent/v24229_signed_outer_attestation.py")
MODULE_TEST = Path("tests/test_v24229_signed_outer_attestation.py")
AUDIT = Path("scripts/audit_v24229_signed_outer_attestation.py")
AUDIT_TEST = Path("tests/test_audit_v24229_signed_outer_attestation.py")
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
        "base64",
        "collections",
        "copy",
        "hashlib",
        "hmac",
        "json",
        "typing",
        "v24123_release",
        "v24223_sign_preserving_credit",
        "v24228_challenge_bound_outer_graph",
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
        "build_outer_graph_signing_statement",
        "build_signed_attestation_protocol",
        "build_verified_signature_receipt",
        "canonical_attestation_message",
        "parse_rsa_public_key_spki",
        "validate_outer_graph_signing_statement",
        "validate_signed_attestation_protocol",
        "validate_verified_signature_receipt",
        "verify_rsa_pss_sha256",
    }
)
SECRET_LITERAL = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-(?:dev-)?|sk-)[A-Za-z0-9_-]{16,}"
)
PEM_PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA )?PRIVATE KEY-----")
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
        raise RuntimeError("V2.42.29 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(
            f"V2.42.29 expected an ordinary repository file: {relative}"
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
    private_key_parameters: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.rsplit(".", 1)[-1])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.add(node.name)
            arguments = (
                list(node.args.posonlyargs)
                + list(node.args.args)
                + list(node.args.kwonlyargs)
            )
            private_key_parameters.extend(
                argument.arg
                for argument in arguments
                if "private" in argument.arg.casefold()
                and "key" in argument.arg.casefold()
            )
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
        or private_key_parameters
        or missing_functions
    ):
        raise RuntimeError(
            "V2.42.29 capability boundary failed: "
            f"imports={disallowed_imports}, calls={sorted(forbidden_calls)}, "
            f"attributes={sorted(forbidden_attributes)}, "
            f"privileged_reads={sorted(set(privileged_reads))}, "
            f"private_key_parameters={sorted(private_key_parameters)}, "
            f"missing={missing_functions}"
        )
    return {
        "ast_node_count": sum(1 for _ in ast.walk(tree)),
        "import_roots": sorted(imports),
        "required_public_functions_present": sorted(REQUIRED_PUBLIC_FUNCTIONS),
        "disallowed_import_count": 0,
        "forbidden_dynamic_code_file_environment_network_or_process_call_count": 0,
        "privileged_metadata_read_count": 0,
        "private_key_parameter_count": 0,
        "file_environment_network_model_search_fetch_process_subprocess_or_dynamic_code_capability": False,
        "public_key_and_signature_verification_only": True,
    }


def replay_synthetic_contracts() -> dict[str, Any]:
    fixture.V24229SignedOuterAttestationTests.setUpClass()
    try:
        case = fixture.V24229SignedOuterAttestationTests(methodName="runTest")
        receipt = case.receipt
        validate_verified_signature_receipt(receipt, protocol=case.protocol)
        message = canonical_attestation_message(case.statement)
        valid_signature_verified = verify_rsa_pss_sha256(
            public_key_spki_der=case.public_der_bytes,
            message=message,
            signature=case.signature,
        )
        tampered = bytearray(case.signature)
        tampered[-1] ^= 1
        tampered_signature_rejected = not verify_rsa_pss_sha256(
            public_key_spki_der=case.public_der_bytes,
            message=message,
            signature=bytes(tampered),
        )
        wrong_key_rejected = not verify_rsa_pss_sha256(
            public_key_spki_der=case.other_public_der.read_bytes(),
            message=message,
            signature=case.signature,
        )
        required_false = (
            receipt["independent_signer_identity_verified"],
            receipt["independent_trust_domain_verified"],
            receipt["append_only_transparency_service_used"],
            receipt["trusted_timestamp_verified"],
            receipt["statement_truth_independently_verified"],
            receipt["launch_before_execution_independently_attested"],
            receipt["external_target_precomputation_excluded"],
            receipt["formal_gate2b_evaluation_authorized"],
            receipt["credit_training_authorized"],
            receipt["benchmark_forward_or_evaluator_authorized"],
        )
        if (
            not valid_signature_verified
            or not tampered_signature_rejected
            or not wrong_key_rejected
            or any(required_false)
            or receipt["cryptographic_signature_verified"] is not True
            or receipt[
                "signature_proves_only_possession_of_corresponding_private_key"
            ]
            is not True
            or receipt["private_key_input_accepted_or_read"] is not False
            or receipt["historical_payload_after_wrapping_possible"] is not True
        ):
            raise RuntimeError("V2.42.29 synthetic signature replay drifted")
        return {
            "openssl_generated_test_signature_verified_by_pure_module": True,
            "canonical_domain_separated_statement_replayed": True,
            "public_key_matches_frozen_protocol": True,
            "tampered_signature_rejected": True,
            "wrong_public_key_rejected": True,
            "private_key_passed_to_production_module": False,
            "private_key_or_signature_material_persisted_in_audit": False,
            "signature_proves_only_private_key_possession": True,
            "independent_signer_identity_verified": False,
            "independent_trust_domain_verified": False,
            "append_only_transparency_service_used": False,
            "trusted_timestamp_verified": False,
            "statement_truth_independently_verified": False,
            "launch_before_execution_independently_attested": False,
            "external_target_precomputation_excluded": False,
            "formal_gate2b_evaluation_authorized": False,
            "synthetic_benchmark_rows_or_real_evaluator_payload_read": False,
        }
    finally:
        fixture.V24229SignedOuterAttestationTests.tearDownClass()


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.29 audit may only use the canonical workspace")
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
    forbidden_source_hits = {
        name: bool(
            SECRET_LITERAL.search(source)
            or PEM_PRIVATE_KEY.search(source)
            or OPAQUE_ID.search(source)
        )
        for name, source in control_sources.items()
    }
    if any(forbidden_source_hits.values()):
        raise RuntimeError("V2.42.29 control source contains forbidden content")
    static = audit_python_source(control_sources[str(MODULE)])
    module_name = "v24229_signed_outer_attestation"
    guard_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in guards.items()
    }
    gate_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in gate_guards.items()
    }
    if any(guard_hits.values()):
        raise RuntimeError("V2.42.29 appears in an active forward guard file")
    if any(gate_hits.values()):
        raise RuntimeError("V2.42.29 unexpectedly changed historical Gate 2B")
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
            "historical_gate_authorizes_formal_gate2b_after_v24229": False,
        },
        "static_capability_audit": static,
        "control_source_forbidden_literal_scan": {
            "file_count": len(forbidden_source_hits),
            "hit_count": 0,
            "credential_private_key_pem_or_concrete_opaque_id_literal_present": False,
        },
        "synthetic_contract_replay": replay,
        "scientific_scope": {
            "rsa_pss_sha256_detached_signature_verified": True,
            "canonical_statement_binds_complete_v24228_compatibility_graph": True,
            "public_key_frozen_before_verification": True,
            "private_key_accepted_read_hashed_or_persisted_by_production_module": False,
            "signature_proves_only_possession_of_corresponding_private_key": True,
            "independent_signer_identity_verified": INDEPENDENT_SIGNER_IDENTITY_VERIFIED,
            "independent_trust_domain_verified": INDEPENDENT_TRUST_DOMAIN_VERIFIED,
            "append_only_transparency_service_used": APPEND_ONLY_TRANSPARENCY_SERVICE_USED,
            "trusted_timestamp_verified": TRUSTED_TIMESTAMP_VERIFIED,
            "statement_truth_independently_verified": STATEMENT_TRUTH_INDEPENDENTLY_VERIFIED,
            "launch_before_execution_independently_attested": LAUNCH_BEFORE_EXECUTION_INDEPENDENTLY_ATTESTED,
            "historical_payload_after_wrapping_possible": True,
            "external_target_precomputation_excluded": EXTERNAL_TARGET_PRECOMPUTATION_EXCLUDED,
            "real_independent_outer_target_data_observed": False,
            "formal_gate2b_evaluated": False,
            "training_effect_observed": False,
            "benchmark_quality_or_cost_effect_observed": False,
        },
        "test_key_policy": {
            "openssl_subprocess_used_by_test_fixture_only": True,
            "temporary_key_directory_limited_to_repository": True,
            "temporary_private_keys_deleted_after_replay": True,
            "private_key_bytes_read_hashed_logged_or_emitted": False,
            "private_key_or_signature_bytes_in_audit_artifact": False,
        },
        "source_policy": {
            "repository_control_code_and_synthetic_hashes_only": True,
            "runtime_task_question_query_raw_evidence_url_prediction_or_answer_read": False,
            "benchmark_subset_category_question_type_label_split_or_mapping_read": False,
            "gold_or_real_evaluator_payload_score_reward_or_results_read": False,
            "credential_environment_keyring_or_secret_value_read": False,
            "production_module_network_model_search_fetch_subprocess_or_api_called": False,
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
            "build_only_public_signature_verifier_available": True,
            "independent_trust_domain_established": False,
            "native_challenge_consuming_executor_available": False,
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
    if (
        SECRET_LITERAL.search(encoded)
        or PEM_PRIVATE_KEY.search(encoded)
        or OPAQUE_ID.search(encoded)
    ):
        raise RuntimeError("V2.42.29 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.29 audit output path is noncanonical")
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
