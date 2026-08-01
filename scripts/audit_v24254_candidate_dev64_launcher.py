#!/usr/bin/env python3
"""Create-exclusive, parent-bound audit for V2.42.54 launcher preparation."""

from __future__ import annotations

import argparse
import ast
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

from deepwide_agent.v24254_candidate_dev64_launcher import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    ARM_EXECUTION_IMPLEMENTED,
    ARM_ORDER,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CREATE_EXCLUSIVE_PAIR_PREPARATION_IMPLEMENTED,
    DEV64_LAUNCH_AUTHORIZED,
    EVALUATOR_EXECUTION_IMPLEMENTED,
    EXACT220_LAUNCH_AUTHORIZED,
    EXACT_VISIBLE_DEV64_INPUT_SNAPSHOT_IMPLEMENTED,
    FAILURE_AS_ZERO_AGGREGATE_IMPLEMENTED,
    FAILURE_AS_ZERO_CONTRACT_FROZEN,
    LAUNCH_ACTIVATION_IMPLEMENTED,
    LEASE_ACQUISITION_IMPLEMENTED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    MAPPING_OR_EVALUATOR_OPEN_AUTHORIZED,
    NO_RESUME_OR_SELECTIVE_RERUN_CONTRACT_FROZEN,
    PARENT_AUDIT_CONTROL_MANIFEST_SHA256,
    PARENT_AUDIT_FILE_SHA256,
    PARENT_AUDIT_PATH,
    PARENT_AUDIT_PAYLOAD_SHA256,
    PARENT_CONTROL_RELATIVE_PATHS,
    PRODUCTION_LAUNCHER_AUTHORIZED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    SINGLE_CONTIGUOUS_SHARED_LEASE_CONTRACT_FROZEN,
    TWO_ARM_TERMINAL_BEFORE_EVALUATOR_CONTRACT_FROZEN,
    TWO_DISJOINT_PRISTINE_ARM_ROOTS_IMPLEMENTED,
    UPSTREAM_V24216_RECEIPTS,
    CandidateDev64LauncherPackage,
)
from tests import test_v24254_candidate_dev64_launcher as fixture_module  # noqa: E402


ROLE = "v24254_candidate_dev64_launcher_candidate_audit"
OUTPUT = Path("results/v24254_candidate_dev64_launcher_candidate_audit_v1_20260801.json")
PARENT_RECEIPT = Path(PARENT_AUDIT_PATH)
MODULE = Path("src/deepwide_agent/v24254_candidate_dev64_launcher.py")
MODULE_TEST = Path("tests/test_v24254_candidate_dev64_launcher.py")
AUDIT = Path("scripts/audit_v24254_candidate_dev64_launcher.py")
AUDIT_TEST = Path("tests/test_audit_v24254_candidate_dev64_launcher.py")
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
        "hashlib",
        "json",
        "os",
        "re",
        "stat",
        "pathlib",
        "typing",
        "deepwide_agent.runtime",
        "deepwide_agent.v24232_webswarm_total_budget",
        "deepwide_agent.v24253_candidate_runtime_integration",
    }
)
REQUIRED_PUBLIC_SYMBOLS = frozenset(
    {
        "CandidateDev64LauncherPackage",
        "build_candidate_dev64_launcher_source_manifest",
        "validate_candidate_dev64_launcher_source_manifest",
        "snapshot_visible_dev64_inputs",
        "validate_visible_dev64_input_snapshot",
        "build_candidate_dev64_launcher_contract",
        "validate_candidate_dev64_launcher_contract",
        "validate_candidate_dev64_launcher_initial",
        "validate_candidate_dev64_lease_intent",
        "validate_candidate_dev64_launcher_ready",
        "initialize",
        "open",
        "arm_roots",
        "preflight",
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
    }
)
SECRET_LITERAL = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-(?:dev-)?|sk-)[A-Za-z0-9_-]{16,}"
)
CONCRETE_OPAQUE_ID = re.compile(r"[\"']task_[0-9a-f]{24}[\"']")


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
        raise RuntimeError("V2.42.54 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.42.54 expected ordinary repository file: {relative}")
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
    direct_capability_calls: list[str] = []
    public_expansive_parameters: list[str] = []
    visible_task_validators = 0
    package_publish_calls = 0
    preflight_calls = 0
    forbidden_calls = {
        "eval",
        "exec",
        "system",
        "popen",
        "getenv",
        "socket",
        "urlopen",
        "post",
        "request",
        "check_call",
        "check_output",
        "kill",
        "killpg",
        "fork",
        "forkpty",
        "posix_spawn",
        "posix_spawnp",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
        "execv",
        "execve",
        "execvp",
        "execvpe",
        "startfile",
        "run_task",
        "evaluate_package_gate",
        "acquire_deepwide_api_lease",
    }
    forbidden_public_method_names = {
        "run",
        "launch",
        "activate",
        "acquire_lease",
        "evaluate",
        "aggregate",
        "resume",
        "retry",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.add(node.name)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names = [argument.arg for argument in node.args.args + node.args.kwonlyargs]
                if node.name in forbidden_public_method_names:
                    direct_capability_calls.append(f"public_method:{node.name}")
                if node.name in {"initialize", "open", "arm_roots", "preflight"}:
                    public_expansive_parameters.extend(
                        name
                        for name in names
                        if name
                        in {
                            "answer",
                            "category",
                            "question_type",
                            "mapping",
                            "gold",
                            "evaluator",
                            "score",
                            "credential",
                            "credentials",
                            "callback",
                            "runner",
                            "lease_factory",
                            "resume",
                            "retry",
                            "fault_hook",
                            "activation",
                        }
                    )
                if node.name == "snapshot_visible_dev64_inputs":
                    visible_task_validators += sum(
                        isinstance(descendant, ast.Call)
                        and isinstance(descendant.func, ast.Name)
                        and descendant.func.id == "validate_visible_runtime_task"
                        for descendant in ast.walk(node)
                    )
                    duplicate_hooks = sum(
                        isinstance(descendant, ast.keyword)
                        and descendant.arg == "object_pairs_hook"
                        and isinstance(descendant.value, ast.Name)
                        and descendant.value.id == "_reject_duplicate_object_pairs"
                        for descendant in ast.walk(node)
                    )
                    if duplicate_hooks != 1:
                        direct_capability_calls.append(
                            f"duplicate_key_hook_count:{duplicate_hooks}"
                        )
                if node.name == "initialize":
                    package_publish_calls += sum(
                        isinstance(descendant, ast.Call)
                        and isinstance(descendant.func, ast.Name)
                        and descendant.func.id == "_publish_new"
                        for descendant in ast.walk(node)
                    )
                if node.name == "preflight":
                    preflight_calls += sum(
                        isinstance(descendant, ast.Call)
                        and isinstance(descendant.func, ast.Attribute)
                        and descendant.func.attr == "_require_ready"
                        for descendant in ast.walk(node)
                    )
        if isinstance(node, ast.Call):
            name = (
                node.func.id
                if isinstance(node.func, ast.Name)
                else node.func.attr
                if isinstance(node.func, ast.Attribute)
                else ""
            )
            if name in forbidden_calls:
                direct_capability_calls.append(name)
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "os"
            and node.attr == "environ"
        ):
            direct_capability_calls.append("environ")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "get" and node.args:
                key = _literal_key(node.args[0])
                if key in FORBIDDEN_METADATA_ACCESS_KEYS:
                    privileged_reads.append(str(key))
        elif isinstance(node, ast.Subscript):
            key = _literal_key(node.slice)
            if key in FORBIDDEN_METADATA_ACCESS_KEYS:
                privileged_reads.append(str(key))
    disallowed_imports = sorted(imports - ALLOWED_IMPORT_MODULES)
    missing = sorted(REQUIRED_PUBLIC_SYMBOLS - symbols)
    if (
        disallowed_imports
        or privileged_reads
        or direct_capability_calls
        or public_expansive_parameters
        or missing
        or visible_task_validators != 1
        or package_publish_calls != 3
        or preflight_calls != 1
    ):
        raise RuntimeError(
            "V2.42.54 capability boundary failed: "
            f"imports={disallowed_imports}, privileged={privileged_reads}, "
            f"direct={direct_capability_calls}, public_params={public_expansive_parameters}, "
            f"missing={missing}, visible_task_validator={visible_task_validators}, "
            f"package_publishes={package_publish_calls}, preflight={preflight_calls}"
        )
    return {
        "ast_node_count": sum(1 for _ in ast.walk(tree)),
        "import_modules": sorted(imports),
        "required_public_symbols_present": sorted(REQUIRED_PUBLIC_SYMBOLS),
        "visible_task_schema_validator_call_count": visible_task_validators,
        "create_exclusive_package_receipt_publish_call_count": package_publish_calls,
        "public_preflight_full_binding_call_count": preflight_calls,
        "public_privileged_credential_callback_runner_lease_resume_retry_parameter_count": 0,
        "privileged_metadata_read_count": 0,
        "direct_network_environment_process_subprocess_dynamic_code_launch_lease_evaluator_or_task_call_site_count": 0,
    }


def replay_fake_preparation() -> dict[str, Any]:
    fixture = fixture_module.V24254CandidateDev64LauncherTests(methodName="runTest")
    fixture.setUp()
    try:
        package = fixture.initialize()
        status = package.preflight()
        reopened = CandidateDev64LauncherPackage.open(
            root=package.root,
            repository_root=ROOT,
            contract=fixture.contract,
            runtime_manifest_path=fixture.manifest,
            opaque_id_file_path=fixture.ids,
        )
        reopened_status = reopened.preflight()
        receipt_paths = (
            package.initial_path,
            package.lease_intent_path,
            package.ready_path,
        )
        encoded_receipts = b"".join(path.read_bytes() for path in receipt_paths)
        source_questions = [
            json.loads(line)["question"]
            for line in fixture.manifest.read_text(encoding="utf-8").splitlines()
        ]
        source_ids = fixture.ids.read_text(encoding="utf-8").splitlines()
        roots = [
            package.arm_roots(arm)[kind]
            for arm in ARM_ORDER
            for kind in ("package", "output")
        ]
        return {
            "local_tempdirs_and_synthetic_visible_inputs_only": True,
            "network_socket_real_model_search_fetch_evaluator_or_api_called": False,
            "subprocess_or_shared_lease_acquire_called": False,
            "exact_visible_dev64_snapshot_validated": status["selected_count"] == 64,
            "four_disjoint_pristine_arm_roots_prepared": (
                len({path.resolve() for path in roots}) == 4
                and all(not any(path.iterdir()) for path in roots)
            ),
            "three_create_exclusive_receipts_persisted": all(
                path.is_file() and not path.is_symlink() for path in receipt_paths
            ),
            "raw_questions_absent_from_receipts": all(
                question.encode("utf-8") not in encoded_receipts
                for question in source_questions
            ),
            "raw_opaque_ids_absent_from_receipts": all(
                opaque_id.encode("ascii") not in encoded_receipts
                for opaque_id in source_ids
            ),
            "input_hash_and_runtime_contract_bound": (
                status["input_snapshot_sha256"]
                == package._initial["input_snapshot_sha256"]
                and status["runtime_integration_contract_sha256"]
                == fixture.integration["integration_contract_sha256"]
            ),
            "single_contiguous_lease_required_but_not_acquired": (
                status["single_contiguous_shared_lease_required"] is True
                and status["shared_api_lease_acquired"] is False
            ),
            "existing_v24216_to_v24220_priority_preserved": status[
                "existing_v24216_to_v24220_chain_has_priority"
            ]
            is True,
            "outcome_before_engineering_gate_thresholds_frozen": (
                fixture.contract["engineering_gate_decision_contract"][
                    "thresholds_frozen_before_pair_materialization"
                ]
                is True
                and fixture.contract["engineering_gate_decision_contract"][
                    "go_authorizes_exact220_launch"
                ]
                is False
            ),
            "launch_evaluator_exact220_and_sota_unauthorized": (
                status["dev64_launch_authorized"] is False
                and status["exact220_launch_authorized"] is False
                and status["leaderboard_submission_or_sota_claim_authorized"]
                is False
            ),
            "reopen_status_byte_equivalent": reopened_status == status,
            "mapping_gold_category_question_type_evaluator_or_score_read": False,
        }
    finally:
        fixture.tearDown()


def _validate_parent(root: Path) -> dict[str, Any]:
    parent_path = ordinary(root, PARENT_RECEIPT)
    if sha256(parent_path) != PARENT_AUDIT_FILE_SHA256:
        raise RuntimeError("V2.42.54 parent receipt bytes drifted")
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    unsigned = dict(parent)
    payload = unsigned.pop("audit_payload_sha256", None)
    manifest = {
        relative: sha256(ordinary(root, Path(relative)))
        for relative in PARENT_CONTROL_RELATIVE_PATHS
    }
    if (
        parent.get("role")
        != "v24253_candidate_runtime_integration_candidate_audit"
        or parent.get("audit_valid") is not True
        or parent.get("label_blind_runtime") is not True
        or parent.get("candidate_deepwide_runtime_integration") is not True
        or payload != PARENT_AUDIT_PAYLOAD_SHA256
        or payload_sha256(unsigned) != PARENT_AUDIT_PAYLOAD_SHA256
        or parent.get("control_surface", {}).get("manifest") != manifest
        or parent.get("control_surface", {}).get("manifest_sha256")
        != PARENT_AUDIT_CONTROL_MANIFEST_SHA256
        or payload_sha256(manifest) != PARENT_AUDIT_CONTROL_MANIFEST_SHA256
        or parent.get("claims", {}).get("active_runtime_wrapper_available") is not False
        or parent.get("claims", {}).get("benchmark_score_available") is not False
        or parent.get("claims", {}).get("sota") is not False
    ):
        raise RuntimeError("V2.42.54 parent receipt semantics drifted")
    return {
        "path": str(PARENT_RECEIPT),
        "file_sha256": PARENT_AUDIT_FILE_SHA256,
        "payload_sha256": PARENT_AUDIT_PAYLOAD_SHA256,
        "v24253_control_manifest_sha256": PARENT_AUDIT_CONTROL_MANIFEST_SHA256,
        "v24253_control_files_rehashed": len(manifest),
        "v24253_candidate_parent_validated": True,
    }


def _validate_upstream_v24216(root: Path) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for relative, expected_sha256, expected_role in UPSTREAM_V24216_RECEIPTS:
        path = ordinary(root, Path(relative))
        value = json.loads(path.read_text(encoding="utf-8"))
        if sha256(path) != expected_sha256 or value.get("role") != expected_role:
            raise RuntimeError("V2.42.54 upstream V2.42.16 receipt drifted")
        output.append({"path": relative, "sha256": expected_sha256})
    return output


def build_audit(root: Path = ROOT, *, created_at_unix: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.54 audit may only use canonical workspace")
    paths = {str(path): ordinary(root, path) for path in CONTROL_FILES}
    parent = _validate_parent(root)
    upstream = _validate_upstream_v24216(root)
    sources = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    literal_hits = {
        name: bool(SECRET_LITERAL.search(source) or CONCRETE_OPAQUE_ID.search(source))
        for name, source in sources.items()
    }
    if any(literal_hits.values()):
        raise RuntimeError("V2.42.54 control source contains forbidden content")
    static = audit_python_source(sources[str(MODULE)])
    guards = {str(path): ordinary(root, path) for path in ACTIVE_FORWARD_GUARDS}
    module_name = "v24254_candidate_dev64_launcher"
    guard_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in guards.items()
    }
    if any(guard_hits.values()):
        raise RuntimeError("V2.42.54 appears in an active forward guard")
    control_manifest = {name: sha256(path) for name, path in paths.items()}
    guard_manifest = {name: sha256(path) for name, path in guards.items()}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "label_blind_runtime": True,
        "candidate_dev64_launcher_preparation": True,
        "parent_receipt": parent,
        "upstream_v24216_priority_receipts": upstream,
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
            "module_absent_from_active_runner_launcher_and_forward_entrypoints": True,
        },
        "static_capability_audit": static,
        "control_source_forbidden_literal_scan": {
            "file_count": len(literal_hits),
            "hit_count": 0,
            "credential_or_concrete_opaque_id_literal_present": False,
        },
        "fake_launcher_preparation_replay": replay_fake_preparation(),
        "scientific_scope": {
            "create_exclusive_pair_preparation_implemented": CREATE_EXCLUSIVE_PAIR_PREPARATION_IMPLEMENTED,
            "exact_visible_dev64_input_snapshot_implemented": EXACT_VISIBLE_DEV64_INPUT_SNAPSHOT_IMPLEMENTED,
            "two_disjoint_pristine_arm_roots_implemented": TWO_DISJOINT_PRISTINE_ARM_ROOTS_IMPLEMENTED,
            "single_contiguous_shared_lease_contract_frozen": SINGLE_CONTIGUOUS_SHARED_LEASE_CONTRACT_FROZEN,
            "two_arm_terminal_before_evaluator_contract_frozen": TWO_ARM_TERMINAL_BEFORE_EVALUATOR_CONTRACT_FROZEN,
            "failure_as_zero_contract_frozen": FAILURE_AS_ZERO_CONTRACT_FROZEN,
            "outcome_before_engineering_gate_thresholds_frozen": True,
            "no_resume_or_selective_rerun_contract_frozen": NO_RESUME_OR_SELECTIVE_RERUN_CONTRACT_FROZEN,
            "launch_activation_implemented": LAUNCH_ACTIVATION_IMPLEMENTED,
            "lease_acquisition_implemented": LEASE_ACQUISITION_IMPLEMENTED,
            "arm_execution_implemented": ARM_EXECUTION_IMPLEMENTED,
            "evaluator_execution_implemented": EVALUATOR_EXECUTION_IMPLEMENTED,
            "failure_as_zero_aggregate_implemented": FAILURE_AS_ZERO_AGGREGATE_IMPLEMENTED,
            "real_provider_traffic_observed": False,
            "dev64_gate_evaluated": False,
            "fresh_exact220_evaluated": False,
            "quality_cost_or_benchmark_effect_observed": False,
        },
        "source_policy": {
            "repository_control_code_parent_receipt_synthetic_visible_tasks_and_local_tempdirs_only": True,
            "visible_question_read_only_for_exact_schema_validation": True,
            "runtime_task_question_prediction_or_answer_emitted": False,
            "benchmark_subset_category_question_type_label_split_or_mapping_used_for_routing": False,
            "gold_evaluator_payload_score_reward_or_results_read": False,
            "credential_environment_keyring_or_secret_value_read": False,
            "audit_network_socket_real_model_search_fetch_subprocess_lease_evaluator_or_api_called": False,
        },
        "authorization": {
            "isolated_candidate_launcher_preparation_capability": True,
            "production_launcher_authorized": PRODUCTION_LAUNCHER_AUTHORIZED,
            "active_provider_traffic_authorized": ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
            "active_forward_integration_authorized": ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
            "shared_api_lease_acquire_authorized": SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
            "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
            "mapping_or_evaluator_open_authorized": MAPPING_OR_EVALUATOR_OPEN_AUTHORIZED,
            "dev64_launch_authorized": DEV64_LAUNCH_AUTHORIZED,
            "exact220_launch_authorized": EXACT220_LAUNCH_AUTHORIZED,
            "process_signal_restart_resume_rerun_or_selective_retry": False,
            "leaderboard_submission_or_sota_claim": LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
        },
        "claims": {
            "candidate_dev64_launcher_preparation_available": True,
            "active_launcher_available": False,
            "shared_lease_acquired": False,
            "real_provider_execution_evidence_available": False,
            "dev64_result_available": False,
            "benchmark_score_available": False,
            "benchmark_improvement_observed": False,
            "leaderboard_submission_performed": False,
            "sota": False,
        },
        "audit_valid": True,
    }
    encoded = json.dumps(value, ensure_ascii=False)
    if SECRET_LITERAL.search(encoded) or CONCRETE_OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.54 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.54 audit output path is noncanonical")
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
                "candidate_dev64_launcher_preparation": value[
                    "candidate_dev64_launcher_preparation"
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
