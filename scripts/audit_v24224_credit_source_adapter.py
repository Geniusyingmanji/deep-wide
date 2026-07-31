#!/usr/bin/env python3
"""Build-only audit for the V2.42.24 V2.41.23 credit source adapter."""

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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent.v24224_credit_source_adapter import (  # noqa: E402
    CREDIT_TRAINING_AUTHORIZED,
    POLICY_ID,
    PRODUCTION_PACKAGE_AUTHORIZED,
    adapt_v24123_source_graph,
    object_sha256,
    validate_adapter_result,
)
from tests.test_v24224_credit_source_adapter import (  # noqa: E402
    artifact_sha256,
    build_fixture,
    reseal,
)


ROLE = "v24224_v24123_credit_source_adapter_build_audit"
OUTPUT = Path(
    "results/v24224_v24123_credit_source_adapter_build_audit_v2_20260731.json"
)
MODULE = Path("src/deepwide_agent/v24224_credit_source_adapter.py")
MODULE_TEST = Path("tests/test_v24224_credit_source_adapter.py")
AUDIT = Path("scripts/audit_v24224_credit_source_adapter.py")
AUDIT_TEST = Path("tests/test_audit_v24224_credit_source_adapter.py")
CONTROL_FILES = (MODULE, MODULE_TEST, AUDIT, AUDIT_TEST)
ACTIVE_FORWARD_GUARD_FILES = (
    Path("src/deepwide_agent/runtime.py"),
    Path("src/deepwide_agent/v24211_entropy_runtime.py"),
    Path("src/deepwide_agent/__init__.py"),
    Path("scripts/run_deepwide_agent.py"),
    Path("scripts/launch_frozen_deepwide.py"),
)
ALLOWED_IMPORT_ROOTS = frozenset(
    {
        "__future__",
        "collections",
        "copy",
        "deepwide_agent",
        "hashlib",
        "json",
        "math",
        "typing",
        "v24121_continuation",
        "v24123_release",
        "v24223_sign_preserving_credit",
    }
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
        "adapt_v24123_source_graph",
        "validate_adapter_result",
        "validate_source_receipt",
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
        ).encode()
    ).hexdigest()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def ordinary(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.42.24 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not _is_relative_to(path.resolve(), root)
    ):
        raise RuntimeError(
            f"V2.42.24 expected an ordinary repository file: {relative}"
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
    functions: set[str] = set()
    forbidden_calls: list[str] = []
    forbidden_attributes: list[str] = []
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
                if root in FORBIDDEN_ATTRIBUTE_ROOTS:
                    forbidden_attributes.append(f"{root}.{node.func.attr}")
    bad_imports = sorted(imports - ALLOWED_IMPORT_ROOTS)
    missing = sorted(REQUIRED_PUBLIC_FUNCTIONS - functions)
    if bad_imports or forbidden_calls or forbidden_attributes or missing:
        raise RuntimeError(
            "V2.42.24 capability boundary failed: "
            f"imports={bad_imports}, calls={sorted(forbidden_calls)}, "
            f"attributes={sorted(forbidden_attributes)}, missing={missing}"
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


def _adapt(fixture: dict[str, object]) -> dict[str, Any]:
    return adapt_v24123_source_graph(**fixture)  # type: ignore[arg-type]


def replay_synthetic_contracts() -> dict[str, Any]:
    fixture = build_fixture()
    result = _adapt(fixture)
    validate_adapter_result(result)
    vector = result["verified_contribution"][
        "replicate_signed_terminal_contributions"
    ]
    failures: dict[str, bool] = {}

    missing = build_fixture()
    missing["evaluated_terminal_receipts"].pop()  # type: ignore[union-attr]
    try:
        _adapt(missing)
    except ValueError:
        failures["missing_receipt_rejected"] = True

    freeze = build_fixture()
    freeze["prediction_freeze"]["terminal_receipt_sha256s"].reverse()  # type: ignore[index,union-attr]
    reseal(freeze["prediction_freeze"], "seal_sha256")  # type: ignore[arg-type]
    try:
        _adapt(freeze)
    except ValueError:
        failures["resealed_freeze_tamper_rejected"] = True

    provenance = build_fixture()
    provenance["evaluator_provenance_receipt"][  # type: ignore[index]
        "prediction_freeze_sha256"
    ] = artifact_sha256({"not": "the freeze"})
    reseal(  # type: ignore[arg-type]
        provenance["evaluator_provenance_receipt"], "receipt_sha256"
    )
    try:
        _adapt(provenance)
    except ValueError:
        failures["resealed_provenance_tamper_rejected"] = True

    sign = build_fixture()
    record = sign["contribution_records"][0]  # type: ignore[index]
    record["signed_task_contribution"] = -record["signed_task_contribution"]
    reseal(record, "record_sha256")
    try:
        _adapt(sign)
    except ValueError:
        failures["resealed_sign_flip_rejected"] = True

    failed = _adapt(
        build_fixture(
            signed_gains=(0.4, -0.4, 0.1), failed_action_replicate=1
        )
    )
    if (
        vector != [0.4, -0.2, 0.1]
        or failed["verified_contribution"][
            "replicate_signed_terminal_contributions"
        ]
        != [0.4, -0.4, 0.1]
        or set(failures)
        != {
            "missing_receipt_rejected",
            "resealed_freeze_tamper_rejected",
            "resealed_provenance_tamper_rejected",
            "resealed_sign_flip_rejected",
        }
    ):
        raise RuntimeError("V2.42.24 synthetic receipt graph replay drifted")
    return {
        "valid_six_receipt_graph_replayed": True,
        "signed_contribution_vector": vector,
        "failed_branch_unit_loss_contribution_replayed": True,
        **failures,
        "semantic_or_distributional_ood_independently_assessed": False,
        "evaluator_live_provenance_independently_replayed": False,
        "synthetic_benchmark_rows_or_content_read": False,
    }


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.24 audit may only use the canonical workspace")
    paths = {str(value): ordinary(root, value) for value in CONTROL_FILES}
    guards = {
        str(value): ordinary(root, value) for value in ACTIVE_FORWARD_GUARD_FILES
    }
    static = audit_python_source(paths[str(MODULE)].read_text(encoding="utf-8"))
    module_name = "v24224_credit_source_adapter"
    guard_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in guards.items()
    }
    if any(guard_hits.values()):
        raise RuntimeError("V2.42.24 appears in an active forward guard file")
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
            "guard_manifest_sha256": payload_sha256(guard_manifest),
            "module_name_hit_count_by_file": guard_hits,
            "module_absent_from_guarded_forward_entrypoints": True,
        },
        "static_capability_audit": static,
        "synthetic_contract_replay": replay,
        "scientific_scope": {
            "v24123_exact_manifest_bundle_freeze_provenance_receipt_state_contribution_and_aggregate_graph_validated": True,
            "terminal_same_state_contribution_is_only_sign_source": True,
            "failure_as_unit_loss_replayed": True,
            "prediction_freeze_artifact_validated": True,
            "post_freeze_evaluator_provenance_binding_validated": True,
            "evaluator_live_provenance_independently_replayed": False,
            "semantic_or_distributional_ood_independently_assessed": False,
            "real_intervention_data_observed": False,
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
            "active_forward_prompt_model_search_budget_or_controller_change": False,
            "process_signal_restart_resume_rerun_or_selective_retry": False,
            "candidate_materialization_or_package_gate": False,
            "benchmark_forward_dev64_full220_or_evaluator_launch": False,
            "shared_api_lease_acquire": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "claims": {
            "build_only_source_adapter_available": True,
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
    if OPAQUE_ID.search(encoded) or SECRET_LITERAL.search(encoded):
        raise RuntimeError("V2.42.24 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not _is_relative_to(target, ROOT / "results"):
        raise RuntimeError("V2.42.24 audit output path is noncanonical")
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
