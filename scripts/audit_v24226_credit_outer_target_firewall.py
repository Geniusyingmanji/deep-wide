#!/usr/bin/env python3
"""Build-only audit for the V2.42.26 credit outer-target firewall."""

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

from deepwide_agent.v24223_sign_preserving_credit import (  # noqa: E402
    build_amplitude_features,
    modulate_verified_credit,
)
from deepwide_agent.v24224_credit_source_adapter import (  # noqa: E402
    adapt_v24123_source_graph,
)
from deepwide_agent.v24226_credit_outer_target_firewall import (  # noqa: E402
    CREDIT_TRAINING_AUTHORIZED,
    GATE2B_PASS_AUTHORIZED,
    POLICY_ID,
    PRODUCTION_PACKAGE_AUTHORIZED,
    build_credit_prediction_freeze,
    build_outer_target_diagnostic_aggregate,
    build_outer_target_protocol,
    join_independent_outer_target,
)
from tests.test_v24226_credit_outer_target_firewall import (  # noqa: E402
    adapt,
    digest,
    independent_outer,
    make_fixture,
)


ROLE = "v24226_credit_outer_target_firewall_build_audit"
OUTPUT = Path(
    "results/v24226_credit_outer_target_firewall_build_audit_v1_20260801.json"
)
MODULE = Path("src/deepwide_agent/v24226_credit_outer_target_firewall.py")
MODULE_TEST = Path("tests/test_v24226_credit_outer_target_firewall.py")
AUDIT = Path("scripts/audit_v24226_credit_outer_target_firewall.py")
AUDIT_TEST = Path("tests/test_audit_v24226_credit_outer_target_firewall.py")
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
        "collections",
        "copy",
        "math",
        "typing",
        "v24123_release",
        "v24223_sign_preserving_credit",
        "v24224_credit_source_adapter",
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
        "build_credit_prediction_freeze",
        "build_outer_target_diagnostic_aggregate",
        "build_outer_target_protocol",
        "join_independent_outer_target",
        "validate_credit_prediction_freeze",
        "validate_independent_outer_target_pair",
        "validate_outer_target_diagnostic_aggregate",
        "validate_outer_target_protocol",
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
        raise RuntimeError("V2.42.26 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(
            f"V2.42.26 expected an ordinary repository file: {relative}"
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
    disallowed_imports = sorted(imports - ALLOWED_IMPORT_ROOTS)
    missing_functions = sorted(REQUIRED_PUBLIC_FUNCTIONS - functions)
    if disallowed_imports or forbidden_calls or forbidden_attributes or missing_functions:
        raise RuntimeError(
            "V2.42.26 capability boundary failed: "
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


def _build_pair(
    *, cluster: str, gains: tuple[float, float, float], nonce: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = build_outer_target_protocol(
        selection_protocol_sha256=digest("a"),
        fit_task_cluster_ref_sha256s=[digest("b")],
        calibration_task_cluster_ref_sha256s=[digest("c")],
        audit_task_cluster_ref_sha256s=[digest(cluster)],
    )
    inner_fixture = make_fixture(gains, cluster=cluster)
    inner_result = adapt_v24123_source_graph(**inner_fixture)  # type: ignore[arg-type]
    verified = inner_result["verified_contribution"]
    features = build_amplitude_features(
        opaque_step_ref_sha256=verified["opaque_step_ref_sha256"],
        source_checkpoint_sha256=verified["source_checkpoint_sha256"],
        feature_source_sha256=digest("9"),
        entropy_reduction=0.2,
        provenance_role="discovery",
        provenance_strength=0.6,
        cost_fraction=0.1,
    )
    modulation = modulate_verified_credit(
        verified_contribution=verified,
        amplitude_features=features,
    )
    freeze = build_credit_prediction_freeze(
        protocol=protocol,
        inner_job_manifest=inner_fixture["job_manifest"],  # type: ignore[arg-type]
        inner_adapter_result=inner_result,
        amplitude_features=features,
        modulation_receipt=modulation,
    )
    outer_fixture = independent_outer(inner_fixture, gains, nonce=nonce)
    outer_result = adapt(outer_fixture)
    pair = join_independent_outer_target(
        protocol=protocol,
        prediction_freeze=freeze,
        inner_job_manifest=inner_fixture["job_manifest"],  # type: ignore[arg-type]
        inner_adapter_result=inner_result,
        amplitude_features=features,
        modulation_receipt=modulation,
        outer_job_manifest=outer_fixture["job_manifest"],  # type: ignore[arg-type]
        outer_adapter_result=outer_result,
    )
    return protocol, pair


def replay_synthetic_contracts() -> dict[str, Any]:
    protocol, valid = _build_pair(
        cluster="e", gains=(0.4, -0.2, 0.1), nonce="f"
    )
    equal_numeric_independent = (
        valid["inner_source_contribution_diagnostic"]
        == valid["outer_target_contribution"]
        and valid["inner_outer_arm_graph_hashes_disjoint"] is True
    )
    source_reuse_rejected = False
    inner_fixture = make_fixture((0.4, -0.2, 0.1), cluster="e")
    inner_result = adapt(inner_fixture)
    verified = inner_result["verified_contribution"]
    features = build_amplitude_features(
        opaque_step_ref_sha256=verified["opaque_step_ref_sha256"],
        source_checkpoint_sha256=verified["source_checkpoint_sha256"],
        feature_source_sha256=digest("9"),
        entropy_reduction=0.2,
        provenance_role="discovery",
        provenance_strength=0.6,
        cost_fraction=0.1,
    )
    modulation = modulate_verified_credit(
        verified_contribution=verified, amplitude_features=features
    )
    freeze = build_credit_prediction_freeze(
        protocol=protocol,
        inner_job_manifest=inner_fixture["job_manifest"],  # type: ignore[arg-type]
        inner_adapter_result=inner_result,
        amplitude_features=features,
        modulation_receipt=modulation,
    )
    try:
        join_independent_outer_target(
            protocol=protocol,
            prediction_freeze=freeze,
            inner_job_manifest=inner_fixture["job_manifest"],  # type: ignore[arg-type]
            inner_adapter_result=inner_result,
            amplitude_features=features,
            modulation_receipt=modulation,
            outer_job_manifest=inner_fixture["job_manifest"],  # type: ignore[arg-type]
            outer_adapter_result=inner_result,
        )
    except ValueError:
        source_reuse_rejected = True
    split_overlap_rejected = False
    try:
        build_outer_target_protocol(
            selection_protocol_sha256=digest("a"),
            fit_task_cluster_ref_sha256s=[digest("b")],
            calibration_task_cluster_ref_sha256s=[digest("c")],
            audit_task_cluster_ref_sha256s=[digest("b")],
        )
    except ValueError:
        split_overlap_rejected = True
    aggregate = build_outer_target_diagnostic_aggregate(
        protocol=protocol, pairs=[valid]
    )
    if not all(
        (
            equal_numeric_independent,
            source_reuse_rejected,
            split_overlap_rejected,
            aggregate["diagnostic_status"]
            == "contract_only_not_evaluable_or_fail",
            aggregate["gate2b_pass_authorized"] is False,
        )
    ):
        raise RuntimeError("V2.42.26 synthetic firewall replay drifted")
    return {
        "valid_independent_outer_target_pair_replayed": True,
        "same_frozen_manifest_and_semantic_bundle_reused": True,
        "inner_outer_arm_graph_hashes_disjoint": True,
        "equal_numeric_contribution_with_independent_artifacts_accepted": True,
        "same_source_graph_as_outer_target_rejected": source_reuse_rejected,
        "fit_calibration_audit_cluster_overlap_rejected": split_overlap_rejected,
        "prediction_builder_signature_excludes_outer_target": True,
        "diagnostic_aggregate_cannot_authorize_gate2b_pass": True,
        "synthetic_benchmark_rows_or_content_read": False,
    }


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.26 audit may only use the canonical workspace")
    paths = {str(path): ordinary(root, path) for path in CONTROL_FILES}
    guards = {
        str(path): ordinary(root, path) for path in ACTIVE_FORWARD_GUARD_FILES
    }
    gate_guards = {
        str(path): ordinary(root, path) for path in FORMAL_GATE_GUARD_FILES
    }
    static = audit_python_source(paths[str(MODULE)].read_text(encoding="utf-8"))
    module_name = "v24226_credit_outer_target_firewall"
    guard_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in guards.items()
    }
    if any(guard_hits.values()):
        raise RuntimeError("V2.42.26 appears in an active forward guard file")
    formal_gate_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in gate_guards.items()
    }
    if any(formal_gate_hits.values()):
        raise RuntimeError("V2.42.26 unexpectedly changed the historical Gate 2B")
    control_manifest = {name: sha256(path) for name, path in paths.items()}
    guard_manifest = {name: sha256(path) for name, path in guards.items()}
    formal_gate_manifest = {
        name: sha256(path) for name, path in gate_guards.items()
    }
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
        "historical_gate_disposition": {
            "file_count": len(formal_gate_manifest),
            "manifest": formal_gate_manifest,
            "manifest_sha256": payload_sha256(formal_gate_manifest),
            "v24226_module_name_hit_count_by_file": formal_gate_hits,
            "historical_synthetic_same_target_pass_preserved_for_regression_only": True,
            "historical_gate_authorizes_formal_gate2b_claim_after_v24226": False,
            "formal_future_gate_requires_independent_outer_target_pairs": True,
        },
        "static_capability_audit": static,
        "synthetic_contract_replay": replay,
        "scientific_scope": {
            "outcome_anchored_credit_self_target_confirmation_identified": True,
            "fit_calibration_audit_cluster_separation_implemented": True,
            "prediction_freeze_api_excludes_outer_target_input": True,
            "same_frozen_manifest_and_semantic_step_required": True,
            "inner_outer_arm_graph_hash_disjointness_required": True,
            "equal_numeric_contribution_without_artifact_reuse_allowed": True,
            "same_source_contribution_as_outer_target_rejected": True,
            "wall_clock_creation_order_independently_proven": False,
            "semantic_or_distributional_ood_independently_assessed": False,
            "real_independent_outer_target_data_observed": False,
            "cluster_bootstrap_or_stress_family_minima_evaluated": False,
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
            "gate2b_pass_authorized": GATE2B_PASS_AUTHORIZED,
            "active_forward_prompt_model_search_budget_or_controller_change": False,
            "process_signal_restart_resume_rerun_or_selective_retry": False,
            "candidate_materialization_or_package_gate": False,
            "benchmark_forward_dev64_full220_or_evaluator_launch": False,
            "shared_api_lease_acquire": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "claims": {
            "build_only_firewall_available": True,
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
        raise RuntimeError("V2.42.26 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.26 audit output path is noncanonical")
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
