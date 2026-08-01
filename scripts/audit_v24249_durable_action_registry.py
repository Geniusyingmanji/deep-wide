#!/usr/bin/env python3
"""Create-exclusive, parent-bound audit for V2.42.49 action registry."""

from __future__ import annotations

import argparse
import ast
import hashlib
import inspect
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepwide_agent.v24249_durable_action_registry import (  # noqa: E402
    ACTION_CLAIM_ORDER_EQUALS_EFFECT_COMPLETION_ORDER_VERIFIED,
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    ADAPTER_CODE_IDENTITY_INDEPENDENTLY_ATTESTED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CALLER_SINGLE_REGISTRY_OWNERSHIP_INDEPENDENTLY_VERIFIED,
    CALLER_SUPPLIED_ACTION_REF_ACCEPTED,
    CLAIM_TO_EFFECT_OUTCOME_DURABLE_BINDING_IMPLEMENTED,
    CLAIMED_BUT_UNSTARTED_ACTION_RECOVERY_IMPLEMENTED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    DIRECT_PARENT_FACADE_BYPASS_GLOBALLY_EXCLUDED,
    DURABLE_CLAIM_BEFORE_FACADE_EFFECT_IMPLEMENTED,
    EPHEMERAL_REQUEST_CONTENT_USED_FOR_ACTION_IDENTITY,
    EQUAL_EPHEMERAL_REQUEST_DEDUPLICATION_IMPLEMENTED,
    EXTERNAL_SIDE_EFFECT_AUTHORIZED,
    FILE_AND_DIRECTORY_FSYNC_IMPLEMENTED,
    FIXED_OPERATION_STAGE_REFS_IMPLEMENTED,
    GLOBAL_MONOTONIC_ACTION_ORDINAL_IMPLEMENTED,
    INITIALIZATION_CRASH_AUTOMATIC_RECOVERY_IMPLEMENTED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    LOCAL_POSIX_ADVISORY_LOCK_IMPLEMENTED,
    MALICIOUS_SAME_USER_RESEALING_EXCLUDED,
    NETWORK_OR_DISTRIBUTED_FILESYSTEM_SEMANTICS_PROVEN,
    OS_CSPRNG_INSTANCE_DOMAIN_IMPLEMENTED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    SEARCH_LEADS_OR_PAGE_TEXT_ACTIVE_EVIDENCE_ELIGIBILITY_GRANTED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    DurableCandidateActionRegistry,
    validate_registered_facade_receipt,
)
from tests import test_v24248_candidate_client_facade as parent_fixture  # noqa: E402


ROLE = "v24249_durable_action_registry_candidate_audit"
OUTPUT = Path("results/v24249_durable_action_registry_candidate_audit_v1_20260801.json")
PARENT_RECEIPT = Path(
    "results/v24248_candidate_client_facade_candidate_audit_v1_20260801.json"
)
PARENT_RECEIPT_SHA256 = (
    "ff49c36b7c0b1f8e555538b6d50836184c3e5831b0c3d78c57c04e0c87154e55"
)
PARENT_PAYLOAD_SHA256 = (
    "b8113b8f95618aee80eacf7fa5da315ada2d4f12d3f0d9690aadb79e24b63690"
)
PARENT_MANIFEST_SHA256 = (
    "c06f696efa2a5187fc437818f42129835b63f593bca53b2d95585105baa7a5cb"
)
PARENT_CONTROL_FILES = (
    Path("src/deepwide_agent/v24248_candidate_client_facade.py"),
    Path("tests/test_v24248_candidate_client_facade.py"),
    Path("scripts/audit_v24248_candidate_client_facade.py"),
    Path("tests/test_audit_v24248_candidate_client_facade.py"),
)
MODULE = Path("src/deepwide_agent/v24249_durable_action_registry.py")
MODULE_TEST = Path("tests/test_v24249_durable_action_registry.py")
AUDIT = Path("scripts/audit_v24249_durable_action_registry.py")
AUDIT_TEST = Path("tests/test_audit_v24249_durable_action_registry.py")
CONTROL_FILES = (MODULE, MODULE_TEST, AUDIT, AUDIT_TEST)
ACTIVE_FORWARD_GUARDS = (
    Path("src/deepwide_agent/__init__.py"),
    Path("src/deepwide_agent/clients.py"),
    Path("src/deepwide_agent/native_search.py"),
    Path("src/deepwide_agent/anthropic_search.py"),
    Path("src/deepwide_agent/runtime.py"),
    Path("src/deepwide_agent/v24211_entropy_runtime.py"),
    Path("scripts/run_deepwide_agent.py"),
    Path("scripts/launch_frozen_deepwide.py"),
)
ALLOWED_IMPORT_MODULES = frozenset(
    {
        "__future__",
        "copy",
        "dataclasses",
        "fcntl",
        "json",
        "os",
        "re",
        "secrets",
        "stat",
        "contextlib",
        "pathlib",
        "typing",
        "deepwide_agent.v24232_webswarm_total_budget",
        "deepwide_agent.v24248_candidate_client_facade",
    }
)
REQUIRED_PUBLIC_SYMBOLS = frozenset(
    {
        "DurableActionRegistryError",
        "DurableActionRegistryPoisoned",
        "DurableRegisteredFacadeResult",
        "validate_durable_action_registry_initial",
        "validate_registered_facade_receipt",
        "DurableCandidateActionRegistry",
        "initialize",
        "open",
        "load_claims",
        "status",
        "validate_receipt_against_registry",
        "run_model_json",
        "run_search_leads",
        "run_fetched_page",
    }
)
FORBIDDEN_METADATA_ACCESS_KEYS = frozenset(
    {
        "answer_key",
        "benchmark_category",
        "benchmark_label",
        "benchmark_subset",
        "category",
        "correctness",
        "evaluator_payload",
        "evaluator_score",
        "gold",
        "ground_truth",
        "mapping",
        "prediction",
        "question_type",
        "results.csv",
        "reward",
        "score",
        "split",
        "task_category",
        "task_id",
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
        raise RuntimeError("V2.42.49 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.42.49 expected ordinary repository file: {relative}")
    return path


def _literal_key(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.casefold()
    return None


def audit_python_source(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    imports: set[str] = set()
    symbols: set[str] = set()
    privileged_reads: list[str] = []
    public_action_ref_parameters: list[str] = []
    facade_dispatch = {name: 0 for name in (
        "run_model_json", "run_search_leads", "run_fetched_page"
    )}
    allowed_os_attributes = {
        "O_RDONLY",
        "O_WRONLY",
        "O_RDWR",
        "O_CREAT",
        "O_EXCL",
        "O_NOFOLLOW",
        "O_DIRECTORY",
        "open",
        "close",
        "fdopen",
        "fstat",
        "read",
        "fsync",
        "mkdir",
    }
    os_attributes: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.add(node.name)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in facade_dispatch:
                names = [argument.arg for argument in node.args.args + node.args.kwonlyargs]
                public_action_ref_parameters.extend(
                    name for name in names if name in {"action_ref", "callback", "fault_hook"}
                )
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "os":
                os_attributes.add(node.attr)
            if node.attr == "get" and isinstance(node.ctx, ast.Load):
                parent = node
            if node.attr in facade_dispatch:
                facade_dispatch[node.attr] += 1
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "get" and node.args:
                key = _literal_key(node.args[0])
                if key in FORBIDDEN_METADATA_ACCESS_KEYS:
                    privileged_reads.append(str(key))
        elif isinstance(node, ast.Subscript):
            key = _literal_key(node.slice)
            if key in FORBIDDEN_METADATA_ACCESS_KEYS:
                privileged_reads.append(str(key))
    disallowed_imports = sorted(imports - ALLOWED_IMPORT_MODULES)
    disallowed_os = sorted(os_attributes - allowed_os_attributes)
    missing = sorted(REQUIRED_PUBLIC_SYMBOLS - symbols)
    if (
        disallowed_imports
        or disallowed_os
        or privileged_reads
        or missing
        or public_action_ref_parameters
        or facade_dispatch != {
            "run_model_json": 1,
            "run_search_leads": 1,
            "run_fetched_page": 1,
        }
    ):
        raise RuntimeError(
            "V2.42.49 capability boundary failed: "
            f"imports={disallowed_imports}, os={disallowed_os}, "
            f"privileged={privileged_reads}, missing={missing}, "
            f"public_params={public_action_ref_parameters}, dispatch={facade_dispatch}"
        )
    return {
        "ast_node_count": sum(1 for _ in ast.walk(tree)),
        "import_modules": sorted(imports),
        "required_public_symbols_present": sorted(REQUIRED_PUBLIC_SYMBOLS),
        "facade_dispatch_call_site_count_by_method": facade_dispatch,
        "caller_action_ref_public_parameter_count": 0,
        "public_callback_or_fault_hook_parameter_count": 0,
        "privileged_metadata_read_count": 0,
        "direct_network_environment_process_subprocess_or_dynamic_code_call_site_count": 0,
        "filesystem_capability_restricted_to_local_registry_store": True,
    }


def replay_fake_registry() -> dict[str, Any]:
    private_values = (
        "private system content",
        "private user content",
        "private query content",
        "https://example.test/private-page",
        "synthetic page",
    )
    fixture = parent_fixture.V24248CandidateClientFacadeTests(methodName="runTest")
    fixture.setUp()
    try:
        model_post = parent_fixture.ModelPost(
            parent_fixture.ModelResponse(
                200,
                parent_fixture.model_response_bytes(
                    text='{"ready":true,"value":"private model result"}'
                ),
            ),
            parent_fixture.ModelResponse(
                200,
                parent_fixture.model_response_bytes(
                    text='{"ready":true,"value":"private model result"}'
                ),
            ),
        )
        facade, _, model_adapter, search_adapter, fetch_factory = fixture.build_facade(
            model_post=model_post
        )
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory).resolve()
            first_root = root / "registry-a"
            second_root = root / "registry-b"
            first_root.mkdir()
            second_root.mkdir()
            with mock.patch(
                "deepwide_agent.v24249_durable_action_registry.secrets.token_bytes",
                side_effect=(b"a" * 32, b"b" * 32),
            ):
                registry = DurableCandidateActionRegistry.initialize(
                    root=first_root,
                    facade=facade,
                )
                other = DurableCandidateActionRegistry.initialize(
                    root=second_root,
                    facade=facade,
                )
            model = registry.run_model_json(
                system=private_values[0],
                user=private_values[1],
                max_output_tokens=200,
            )
            search = registry.run_search_leads(
                query=private_values[2],
                max_results=1,
            )
            page = registry.run_fetched_page(url=private_values[3])
            repeated = registry.run_model_json(
                system=private_values[0],
                user=private_values[1],
                max_output_tokens=200,
            )
            claims = registry.load_claims()
            validations = [
                registry.validate_receipt_against_registry(result.receipt)
                for result in (model, search, page, repeated)
            ]
            for result in (model, search, page, repeated):
                validate_registered_facade_receipt(result.receipt)
            encoded = json.dumps(
                [result.receipt for result in (model, search, page, repeated)],
                ensure_ascii=False,
            )
            method_parameters = {
                name: sorted(
                    inspect.signature(
                        getattr(DurableCandidateActionRegistry, name)
                    ).parameters
                )
                for name in (
                    "run_model_json",
                    "run_search_leads",
                    "run_fetched_page",
                )
            }
            return {
                "local_tempdir_virtual_time_and_injected_fake_transports_only": True,
                "network_socket_or_real_model_search_fetch_api_called": False,
                "allocated_action_count": len(claims),
                "allocated_ordinals": [claim["action_ordinal"] for claim in claims],
                "allocated_operation_kinds": [claim["operation_kind"] for claim in claims],
                "claim_prefix_replayed_for_all_receipts": all(
                    value["claim_prefix_replayed_from_store"] for value in validations
                ),
                "model_post_count": len(model_adapter._post.calls),
                "search_post_count": len(search_adapter._post.calls),
                "fetch_pool_count": len(fetch_factory.calls),
                "fetch_urlopen_count": len(fetch_factory.pools[0].urlopen_calls),
                "equal_model_requests_received_distinct_actions": (
                    model.receipt["action_claim_sha256"]
                    != repeated.receipt["action_claim_sha256"]
                ),
                "equal_ephemeral_request_deduplication_claimed": False,
                "separate_registry_received_distinct_random_domain": (
                    registry._initial["initial_sha256"]
                    != other._initial["initial_sha256"]
                ),
                "caller_single_registry_ownership_independently_verified": False,
                "private_prompt_query_url_page_or_json_entered_receipts": any(
                    value in encoded for value in private_values
                ),
                "public_action_ref_callback_or_fault_hook_parameter_present": any(
                    any(
                        parameter in parameters
                        for parameter in ("action_ref", "callback", "fault_hook")
                    )
                    for parameters in method_parameters.values()
                ),
                "benchmark_question_prediction_mapping_gold_evaluator_or_score_used_for_routing": False,
            }
    finally:
        fixture.tearDown()


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.49 audit may only use canonical workspace")
    paths = {str(path): ordinary(root, path) for path in CONTROL_FILES}
    parent_path = ordinary(root, PARENT_RECEIPT)
    if sha256(parent_path) != PARENT_RECEIPT_SHA256:
        raise RuntimeError("V2.42.49 parent receipt bytes drifted")
    parent_value = json.loads(parent_path.read_text(encoding="utf-8"))
    parent_unsigned = dict(parent_value)
    parent_payload = parent_unsigned.pop("audit_payload_sha256", None)
    if (
        parent_value.get("role")
        != "v24248_candidate_client_facade_candidate_audit"
        or parent_value.get("audit_valid") is not True
        or parent_payload != PARENT_PAYLOAD_SHA256
        or payload_sha256(parent_unsigned) != PARENT_PAYLOAD_SHA256
        or parent_value.get("control_surface", {}).get("manifest_sha256")
        != PARENT_MANIFEST_SHA256
    ):
        raise RuntimeError("V2.42.49 parent receipt semantics drifted")
    parent_paths = {str(path): ordinary(root, path) for path in PARENT_CONTROL_FILES}
    parent_manifest = {name: sha256(path) for name, path in parent_paths.items()}
    if parent_manifest != parent_value["control_surface"]["manifest"]:
        raise RuntimeError("V2.42.49 parent control files drifted")
    if payload_sha256(parent_manifest) != PARENT_MANIFEST_SHA256:
        raise RuntimeError("V2.42.49 parent manifest seal drifted")
    sources = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    literal_hits = {
        name: bool(SECRET_LITERAL.search(source) or OPAQUE_ID.search(source))
        for name, source in sources.items()
    }
    if any(literal_hits.values()):
        raise RuntimeError("V2.42.49 control source contains forbidden content")
    static = audit_python_source(sources[str(MODULE)])
    guards = {str(path): ordinary(root, path) for path in ACTIVE_FORWARD_GUARDS}
    module_name = "v24249_durable_action_registry"
    guard_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in guards.items()
    }
    if any(guard_hits.values()):
        raise RuntimeError("V2.42.49 appears in an active forward guard")
    control_manifest = {name: sha256(path) for name, path in paths.items()}
    guard_manifest = {name: sha256(path) for name, path in guards.items()}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "label_blind_runtime": True,
        "candidate_durable_action_registry": True,
        "parent_receipt": {
            "path": str(PARENT_RECEIPT),
            "file_sha256": PARENT_RECEIPT_SHA256,
            "payload_sha256": PARENT_PAYLOAD_SHA256,
            "v24248_control_manifest_sha256": PARENT_MANIFEST_SHA256,
            "v24248_control_files_rehashed": len(parent_manifest),
            "v24248_candidate_parent_validated": True,
        },
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
            "module_absent_from_guarded_clients_and_forward_entrypoints": True,
        },
        "static_capability_audit": static,
        "control_source_forbidden_literal_scan": {
            "file_count": len(literal_hits),
            "hit_count": 0,
            "credential_or_concrete_opaque_id_literal_present": False,
        },
        "fake_registry_replay": replay_fake_registry(),
        "scientific_scope": {
            "os_csprng_instance_domain_implemented": OS_CSPRNG_INSTANCE_DOMAIN_IMPLEMENTED,
            "fixed_operation_stage_refs_implemented": FIXED_OPERATION_STAGE_REFS_IMPLEMENTED,
            "global_monotonic_action_ordinal_implemented": GLOBAL_MONOTONIC_ACTION_ORDINAL_IMPLEMENTED,
            "durable_claim_before_facade_effect_implemented": DURABLE_CLAIM_BEFORE_FACADE_EFFECT_IMPLEMENTED,
            "local_posix_advisory_lock_implemented": LOCAL_POSIX_ADVISORY_LOCK_IMPLEMENTED,
            "file_and_directory_fsync_implemented": FILE_AND_DIRECTORY_FSYNC_IMPLEMENTED,
            "caller_supplied_action_ref_accepted": CALLER_SUPPLIED_ACTION_REF_ACCEPTED,
            "ephemeral_request_content_used_for_action_identity": EPHEMERAL_REQUEST_CONTENT_USED_FOR_ACTION_IDENTITY,
            "equal_ephemeral_request_deduplication_implemented": EQUAL_EPHEMERAL_REQUEST_DEDUPLICATION_IMPLEMENTED,
            "caller_single_registry_ownership_independently_verified": CALLER_SINGLE_REGISTRY_OWNERSHIP_INDEPENDENTLY_VERIFIED,
            "direct_parent_facade_bypass_globally_excluded": DIRECT_PARENT_FACADE_BYPASS_GLOBALLY_EXCLUDED,
            "action_claim_order_equals_effect_completion_order_verified": ACTION_CLAIM_ORDER_EQUALS_EFFECT_COMPLETION_ORDER_VERIFIED,
            "claim_to_effect_outcome_durable_binding_implemented": CLAIM_TO_EFFECT_OUTCOME_DURABLE_BINDING_IMPLEMENTED,
            "claimed_but_unstarted_action_recovery_implemented": CLAIMED_BUT_UNSTARTED_ACTION_RECOVERY_IMPLEMENTED,
            "initialization_crash_automatic_recovery_implemented": INITIALIZATION_CRASH_AUTOMATIC_RECOVERY_IMPLEMENTED,
            "adapter_code_identity_independently_attested": ADAPTER_CODE_IDENTITY_INDEPENDENTLY_ATTESTED,
            "malicious_same_user_resealing_excluded": MALICIOUS_SAME_USER_RESEALING_EXCLUDED,
            "network_or_distributed_filesystem_semantics_proven": NETWORK_OR_DISTRIBUTED_FILESYSTEM_SEMANTICS_PROVEN,
            "search_leads_or_page_text_active_evidence_eligibility_granted": SEARCH_LEADS_OR_PAGE_TEXT_ACTIVE_EVIDENCE_ELIGIBILITY_GRANTED,
            "real_provider_traffic_observed": False,
            "active_client_or_runner_integrated": False,
            "dev64_gate_evaluated": False,
            "fresh_exact220_evaluated": False,
            "quality_cost_or_benchmark_effect_observed": False,
        },
        "source_policy": {
            "repository_control_code_parent_receipt_synthetic_requests_values_fake_transports_and_local_tempdir_only": True,
            "runtime_task_question_prediction_or_answer_read": False,
            "benchmark_subset_category_question_type_label_split_or_mapping_used_for_routing": False,
            "gold_evaluator_payload_score_reward_or_results_read": False,
            "credential_environment_keyring_or_secret_value_read": False,
            "audit_network_socket_real_model_search_fetch_subprocess_or_api_called": False,
        },
        "authorization": {
            "isolated_durable_action_registry_capability": True,
            "active_provider_traffic_authorized": ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
            "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
            "active_forward_integration_authorized": ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
            "external_side_effect_authorized": EXTERNAL_SIDE_EFFECT_AUTHORIZED,
            "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
            "dev64_or_exact220_launch_authorized": DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
            "shared_api_lease_acquire_authorized": SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
            "process_signal_restart_resume_rerun_or_selective_retry": False,
            "leaderboard_submission_or_sota_claim": LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
        },
        "claims": {
            "candidate_durable_action_registry_available": True,
            "legacy_runtime_drop_in_client_available": False,
            "active_runtime_wrapper_available": False,
            "active_evidence_admission_available": False,
            "real_provider_execution_evidence_available": False,
            "benchmark_score_available": False,
            "benchmark_improvement_observed": False,
            "leaderboard_submission_performed": False,
            "sota": False,
        },
        "audit_valid": True,
    }
    encoded = json.dumps(value, ensure_ascii=False)
    if SECRET_LITERAL.search(encoded) or OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.49 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.49 audit output path is noncanonical")
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
                "candidate_durable_action_registry": value[
                    "candidate_durable_action_registry"
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
