#!/usr/bin/env python3
"""Create-exclusive build audit for the V2.42.32 budget primitive."""

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

from deepwide_agent.v24232_webswarm_total_budget import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    POLICY_ID,
    PRODUCTION_PACKAGE_AUTHORIZED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    apply_budget_charge,
    build_budget_start_bundle,
    build_cost_vector,
    build_shared_total_budget_contract,
    initialize_arm_budget_ledger,
    object_sha256,
    validate_arm_budget_ledger,
    validate_budget_start_bundle,
    validate_budget_transition,
    validate_shared_total_budget_contract,
)
from deepwide_agent.v24231_webswarm_guidance_baseline import (  # noqa: E402
    build_guidance_ablation_bundle,
    build_guidance_arm,
    build_guidance_policy,
    build_scout_process_trace,
    build_sibling_process_experience,
    build_web_probe_receipt,
)


ROLE = "v24232_webswarm_shared_total_budget_build_audit"
OUTPUT = Path(
    "results/v24232_webswarm_shared_total_budget_build_audit_v1_20260801.json"
)
PARENT_RECEIPT = Path(
    "results/v24231_webswarm_guidance_baseline_build_audit_v1_20260801.json"
)
MODULE = Path("src/deepwide_agent/v24232_webswarm_total_budget.py")
MODULE_TEST = Path("tests/test_v24232_webswarm_total_budget.py")
AUDIT = Path("scripts/audit_v24232_webswarm_total_budget.py")
AUDIT_TEST = Path("tests/test_audit_v24232_webswarm_total_budget.py")
CONTROL_FILES = (MODULE, MODULE_TEST, AUDIT, AUDIT_TEST)
ACTIVE_FORWARD_GUARDS = (
    Path("src/deepwide_agent/__init__.py"),
    Path("src/deepwide_agent/runtime.py"),
    Path("src/deepwide_agent/v24211_entropy_runtime.py"),
    Path("scripts/run_deepwide_agent.py"),
    Path("scripts/launch_frozen_deepwide.py"),
)
PARENT_RECEIPT_SHA256 = (
    "b8480355741d126a70b62ee28e0674275bfae6f84e55cdba409b1a2c5d4e8826"
)
PARENT_CONTROL_FILES = (
    Path("src/deepwide_agent/v24231_webswarm_guidance_baseline.py"),
    Path("tests/test_v24231_webswarm_guidance_baseline.py"),
    Path("scripts/audit_v24231_webswarm_guidance_baseline.py"),
    Path("tests/test_audit_v24231_webswarm_guidance_baseline.py"),
)

ALLOWED_IMPORT_MODULES = frozenset(
    {
        "__future__",
        "hashlib",
        "json",
        "math",
        "typing",
        "deepwide_agent.v24231_webswarm_guidance_baseline",
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
        "evaluator_payload",
        "evaluator_score",
        "gold",
        "ground_truth",
        "mapping",
        "prediction",
        "question",
        "question_type",
        "raw_page",
        "results.csv",
        "reward",
        "score",
        "split",
        "task_category",
        "task_id",
        "url",
    }
)
REQUIRED_PUBLIC_FUNCTIONS = frozenset(
    {
        "apply_budget_charge",
        "build_budget_start_bundle",
        "build_cost_vector",
        "build_shared_total_budget_contract",
        "initialize_arm_budget_ledger",
        "object_sha256",
        "validate_arm_budget_ledger",
        "validate_budget_charge",
        "validate_budget_start_bundle",
        "validate_budget_transition",
        "validate_shared_total_budget_contract",
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
        raise RuntimeError("V2.42.32 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.42.32 expected ordinary repository file: {relative}")
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
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
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
    disallowed_imports = sorted(imports - ALLOWED_IMPORT_MODULES)
    missing_functions = sorted(REQUIRED_PUBLIC_FUNCTIONS - functions)
    if (
        disallowed_imports
        or forbidden_calls
        or forbidden_attributes
        or privileged_reads
        or missing_functions
    ):
        raise RuntimeError(
            "V2.42.32 capability boundary failed: "
            f"imports={disallowed_imports}, calls={sorted(forbidden_calls)}, "
            f"attributes={sorted(set(forbidden_attributes))}, "
            f"privileged_reads={sorted(set(privileged_reads))}, "
            f"missing={missing_functions}"
        )
    return {
        "ast_node_count": sum(1 for _ in ast.walk(tree)),
        "import_modules": sorted(imports),
        "required_public_functions_present": sorted(REQUIRED_PUBLIC_FUNCTIONS),
        "disallowed_import_count": 0,
        "forbidden_file_environment_network_process_or_dynamic_code_call_count": 0,
        "privileged_metadata_read_count": 0,
        "file_environment_network_model_search_fetch_process_subprocess_or_dynamic_code_capability": False,
    }


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _signal(kind: str, tactic: str, label: str) -> dict[str, str]:
    return {"kind": kind, "tactic": tactic, "value_sha256": _digest(label)}


def _guidance(
    contract: dict[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    policy = build_guidance_policy(
        selection_protocol_sha256=_digest("selection"),
        model_contract_sha256=_digest("model"),
        search_fetch_contract_sha256=_digest("search-fetch"),
        total_budget_contract_sha256=contract["contract_sha256"],
        root_scope_projection_protocol_sha256=_digest("root-projection"),
        process_signal_vocabulary_sha256=_digest("process-vocabulary"),
    )
    probe = build_web_probe_receipt(
        policy=policy,
        root_scope_projection_sha256=_digest("root"),
        parent_node_ref_sha256=_digest("parent"),
        probe_run_ref_sha256=_digest("probe"),
        topology="distributed",
        probe_search_calls=3,
        probe_fetch_calls=2,
        probe_model_calls=1,
        probe_input_tokens=100,
        probe_output_tokens=20,
        probe_wall_seconds=4.0004,
    )
    scouts: list[dict[str, Any]] = []
    for slot in (1, 2):
        scouts.append(
            build_scout_process_trace(
                policy=policy,
                root_scope_projection_sha256=_digest("root"),
                parent_node_ref_sha256=_digest("parent"),
                homogeneous_group_ref_sha256=_digest("group"),
                scout_slot=slot,
                sibling_node_ref_sha256=_digest(f"sibling-{slot}"),
                sibling_mode_sha256=_digest("mode"),
                process_signals=[
                    _signal(
                        "effective_query_pattern",
                        "combine_visible_entity_and_attribute_terms",
                        f"query-{slot}",
                    )
                ],
                model_calls=1,
                search_calls=1,
                fetch_calls=1,
                input_tokens=10,
                output_tokens=5,
                wall_seconds=1.0,
                scout_terminal_status="completed",
            )
        )
    experience = build_sibling_process_experience(
        policy=policy,
        scouts=scouts,
        experience_extractor_ref_sha256=_digest("extractor"),
        process_signals=[
            _signal("workflow_hint", "verify_with_independent_source", "workflow")
        ],
        extractor_model_calls=1,
        extractor_input_tokens=300,
        extractor_output_tokens=30,
        extractor_wall_seconds=2.0002,
    )
    shared = {
        "policy": policy,
        "root_scope_projection_sha256": _digest("root"),
        "parent_node_ref_sha256": _digest("parent"),
        "homogeneous_group_ref_sha256": _digest("group"),
        "sibling_count": 8,
    }
    arms = [
        build_guidance_arm(
            **shared,
            arm_name="full",
            arm_ref_sha256=_digest("arm-full"),
            scouts=scouts,
            probe=probe,
            experience=experience,
        ),
        build_guidance_arm(
            **shared,
            arm_name="no_probing",
            arm_ref_sha256=_digest("arm-no-probing"),
            scouts=scouts,
            probe=None,
            experience=experience,
        ),
        build_guidance_arm(
            **shared,
            arm_name="no_experience_upstream",
            arm_ref_sha256=_digest("arm-no-experience-upstream"),
            scouts=[],
            probe=probe,
            experience=None,
        ),
        build_guidance_arm(
            **shared,
            arm_name="no_experience_matched_schedule",
            arm_ref_sha256=_digest("arm-no-experience-matched"),
            scouts=scouts,
            probe=probe,
            experience=None,
        ),
    ]
    bundle = build_guidance_ablation_bundle(
        policy=policy,
        bundle_ref_sha256=_digest("guidance-bundle"),
        arms=arms,
    )
    sources = {
        "full": {"scouts": scouts, "probe": probe, "experience": experience},
        "no_probing": {
            "scouts": scouts,
            "probe": None,
            "experience": experience,
        },
        "no_experience_upstream": {
            "scouts": [],
            "probe": probe,
            "experience": None,
        },
        "no_experience_matched_schedule": {
            "scouts": scouts,
            "probe": probe,
            "experience": None,
        },
    }
    return policy, bundle, arms, sources


def replay_synthetic_contracts() -> dict[str, Any]:
    contract = build_shared_total_budget_contract(
        model_calls=100,
        model_attempts=120,
        search_calls=100,
        fetch_calls=200,
        other_tool_calls=100,
        orchestrator_calls=100,
        input_tokens=100_000,
        output_tokens=20_000,
        wall_milliseconds=1_000_000,
    )
    validate_shared_total_budget_contract(contract)
    policy, guidance_bundle, arms, sources = _guidance(contract)
    ledgers = []
    for arm in arms:
        name = str(arm["arm_name"])
        source = sources[name]
        start = initialize_arm_budget_ledger(
            contract=contract,
            guidance_policy=policy,
            arm=arm,
            scouts=source["scouts"],
            probe=source["probe"],
            experience=source["experience"],
            charge_ref_sha256=_digest(f"overhead-{name}"),
            method_overhead_model_attempts=arm["probe_extractor_cost"][
                "model_calls"
            ],
            method_overhead_other_tool_calls=0,
            method_overhead_orchestrator_calls=1,
        )
        validate_arm_budget_ledger(
            start,
            contract=contract,
            guidance_policy=policy,
            guidance_arm=arm,
            scouts=source["scouts"],
            probe=source["probe"],
            experience=source["experience"],
        )
        ledgers.append(start)
    start_bundle = build_budget_start_bundle(
        contract=contract,
        guidance_policy=policy,
        guidance_bundle=guidance_bundle,
        guidance_bundle_ref_sha256=_digest("guidance-bundle"),
        guidance_arms=arms,
        guidance_sources=sources,
        ledgers=ledgers,
    )
    validate_budget_start_bundle(
        start_bundle,
        contract=contract,
        guidance_policy=policy,
        guidance_bundle=guidance_bundle,
        guidance_bundle_ref_sha256=_digest("guidance-bundle"),
        guidance_arms=arms,
        guidance_sources=sources,
        ledgers=ledgers,
    )
    full_arm = next(arm for arm in arms if arm["arm_name"] == "full")
    full_source = sources["full"]
    cost = build_cost_vector(
        model_calls=1,
        model_attempts=1,
        search_calls=1,
        fetch_calls=2,
        other_tool_calls=0,
        orchestrator_calls=1,
        input_tokens=100,
        output_tokens=20,
        wall_milliseconds=1000,
    )
    full_start = next(ledger for ledger in ledgers if ledger["arm_name"] == "full")
    full_next = apply_budget_charge(
        full_start,
        contract=contract,
        guidance_policy=policy,
        guidance_arm=full_arm,
        scouts=full_source["scouts"],
        probe=full_source["probe"],
        experience=full_source["experience"],
        charge_kind="fanout_execution",
        charge_ref_sha256=_digest("fanout"),
        source_cost_sha256=_digest("fanout-cost"),
        cost=cost,
    )
    validate_budget_transition(
        full_start,
        full_next,
        contract=contract,
        guidance_policy=policy,
        guidance_arm=full_arm,
        scouts=full_source["scouts"],
        probe=full_source["probe"],
        experience=full_source["experience"],
        charge_kind="fanout_execution",
        charge_ref_sha256=_digest("fanout"),
        source_cost_sha256=_digest("fanout-cost"),
        cost=cost,
    )
    dimension_overflow_rejected: dict[str, bool] = {}
    for dimension in contract["cost_dimensions"]:
        vector = {key: 0 for key in contract["cost_dimensions"]}
        vector[dimension] = full_start["remaining"][dimension] + 1
        if dimension == "model_calls":
            vector["model_attempts"] = vector["model_calls"]
        rejected = False
        try:
            apply_budget_charge(
                full_start,
                contract=contract,
                guidance_policy=policy,
                guidance_arm=full_arm,
                scouts=full_source["scouts"],
                probe=full_source["probe"],
                experience=full_source["experience"],
                charge_kind="fanout_execution",
                charge_ref_sha256=_digest(f"over-{dimension}"),
                source_cost_sha256=_digest(f"source-{dimension}"),
                cost=build_cost_vector(**vector),
            )
        except ValueError:
            rejected = True
        dimension_overflow_rejected[dimension] = rejected
    if not all(dimension_overflow_rejected.values()):
        raise RuntimeError("V2.42.32 did not enforce every budget dimension")
    duplicate_rejected = False
    try:
        apply_budget_charge(
            full_start,
            contract=contract,
            guidance_policy=policy,
            guidance_arm=full_arm,
            scouts=full_source["scouts"],
            probe=full_source["probe"],
            experience=full_source["experience"],
            charge_kind="fanout_execution",
            charge_ref_sha256=full_start["charges"][0]["charge_ref_sha256"],
            source_cost_sha256=_digest("duplicate"),
            cost=cost,
        )
    except ValueError:
        duplicate_rejected = True
    if not duplicate_rejected:
        raise RuntimeError("V2.42.32 duplicate charge was accepted")
    encoded = json.dumps(
        {
            "contract": contract,
            "guidance_bundle": guidance_bundle,
            "ledgers": ledgers,
            "start_bundle": start_bundle,
            "full_next": full_next,
        },
        ensure_ascii=False,
    )
    if SECRET_LITERAL.search(encoded) or OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.32 synthetic replay exposed forbidden content")
    return {
        "four_guidance_arms_bound_to_one_exact_total_budget": True,
        "method_overhead_charged_first_for_every_arm": True,
        "probe_and_extractor_wall_each_ceiled_before_sum": True,
        "immutable_hash_chained_transition_replayed": True,
        "duplicate_charge_ref_rejected": duplicate_rejected,
        "all_nine_budget_dimensions_overflow_rejected": all(
            dimension_overflow_rejected.values()
        ),
        "hard_stop_at_exact_cap_replayed_by_tests": True,
        "caller_reported_cost_independently_verified": False,
        "pre_side_effect_charge_order_independently_verified": False,
        "runtime_budget_enforcement_integrated": False,
        "synthetic_benchmark_rows_or_real_evaluator_payload_read": False,
    }


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.32 audit may only use canonical workspace")
    paths = {str(path): ordinary(root, path) for path in CONTROL_FILES}
    parent = ordinary(root, PARENT_RECEIPT)
    if sha256(parent) != PARENT_RECEIPT_SHA256:
        raise RuntimeError("V2.42.32 V2.42.31 parent receipt drifted")
    parent_value = json.loads(parent.read_text(encoding="utf-8"))
    if (
        parent_value.get("role")
        != "v24231_webswarm_guidance_baseline_build_audit"
        or parent_value.get("audit_valid") is not True
        or parent_value.get("build_only") is not True
        or parent_value.get("audit_payload_sha256")
        != "90f7af98e4af1279d780ed2fa2a4ec19fc30e12f62a9c9b52e942d555fb31625"
    ):
        raise RuntimeError("V2.42.32 parent receipt semantics drifted")
    parent_manifest = parent_value["control_surface"]["manifest"]
    parent_control_paths = {
        str(path): ordinary(root, path) for path in PARENT_CONTROL_FILES
    }
    parent_control_manifest = {
        name: sha256(path) for name, path in parent_control_paths.items()
    }
    if parent_control_manifest != parent_manifest:
        raise RuntimeError("V2.42.32 V2.42.31 parent control files drifted")
    if (
        payload_sha256(parent_control_manifest)
        != parent_value["control_surface"]["manifest_sha256"]
    ):
        raise RuntimeError("V2.42.32 V2.42.31 parent manifest seal drifted")
    guards = {
        str(path): ordinary(root, path) for path in ACTIVE_FORWARD_GUARDS
    }
    sources = {
        name: path.read_text(encoding="utf-8") for name, path in paths.items()
    }
    literal_hits = {
        name: bool(SECRET_LITERAL.search(source) or OPAQUE_ID.search(source))
        for name, source in sources.items()
    }
    if any(literal_hits.values()):
        raise RuntimeError("V2.42.32 control source contains forbidden content")
    static = audit_python_source(sources[str(MODULE)])
    module_name = "v24232_webswarm_total_budget"
    guard_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in guards.items()
    }
    if any(guard_hits.values()):
        raise RuntimeError("V2.42.32 appears in active forward guard")
    control_manifest = {name: sha256(path) for name, path in paths.items()}
    guard_manifest = {name: sha256(path) for name, path in guards.items()}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": (
            int(time.time()) if created_at_unix is None else int(created_at_unix)
        ),
        "policy_id": POLICY_ID,
        "label_blind_runtime": True,
        "build_only": True,
        "parent_receipt": {
            "path": str(PARENT_RECEIPT),
            "file_sha256": PARENT_RECEIPT_SHA256,
            "payload_sha256": parent_value["audit_payload_sha256"],
            "v24231_control_manifest_sha256": parent_value["control_surface"][
                "manifest_sha256"
            ],
            "v24231_control_files_rehashed": len(parent_control_manifest),
            "v24231_build_only_parent_validated": True,
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
            "module_absent_from_guarded_forward_entrypoints": True,
        },
        "static_capability_audit": static,
        "control_source_forbidden_literal_scan": {
            "file_count": len(literal_hits),
            "hit_count": 0,
            "credential_or_concrete_opaque_id_literal_present": False,
        },
        "synthetic_contract_replay": replay_synthetic_contracts(),
        "scientific_scope": {
            "model_attempt_search_fetch_other_tool_orchestrator_input_output_and_wall_caps_implemented": True,
            "four_webswarm_arms_share_one_exact_contract": True,
            "v24231_probe_and_extractor_overhead_is_first_charge": True,
            "method_overhead_debited_before_remaining_capacity": True,
            "charge_chain_is_canonical_immutable_and_duplicate_ref_rejecting": True,
            "any_dimension_exact_cap_requires_hard_stop": True,
            "any_dimension_overflow_rejected_before_new_ledger": True,
            "caller_reported_execution_cost_independently_verified": False,
            "method_overhead_attempts_extra_tools_independently_verified": False,
            "charge_happens_before_external_side_effect_independently_verified": False,
            "runtime_budget_enforcement_integrated": False,
            "real_model_search_fetch_or_orchestrator_execution_observed": False,
            "dev64_gate_evaluated": False,
            "fresh_exact220_evaluated": False,
            "quality_cost_or_benchmark_effect_observed": False,
        },
        "source_policy": {
            "repository_control_code_parent_receipt_and_synthetic_hashes_only": True,
            "runtime_task_question_query_raw_evidence_url_prediction_or_answer_read": False,
            "benchmark_subset_category_question_type_label_split_or_mapping_read": False,
            "gold_evaluator_payload_score_reward_or_results_read": False,
            "credential_environment_keyring_or_secret_value_read": False,
            "network_model_search_fetch_subprocess_or_api_called": False,
        },
        "authorization": {
            "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
            "active_forward_integration_authorized": ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
            "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
            "dev64_or_exact220_launch_authorized": DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
            "shared_api_lease_acquire_authorized": SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
            "process_signal_restart_resume_rerun_or_selective_retry": False,
            "leaderboard_submission_or_sota_claim": LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
        },
        "claims": {
            "build_only_shared_total_budget_primitive_available": True,
            "runtime_budget_enforcement_available": False,
            "real_webswarm_budgeted_run_available": False,
            "benchmark_score_available": False,
            "benchmark_improvement_observed": False,
            "leaderboard_submission_performed": False,
            "sota": False,
        },
        "audit_valid": True,
    }
    encoded = json.dumps(value, ensure_ascii=False)
    if SECRET_LITERAL.search(encoded) or OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.32 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.32 audit output path is noncanonical")
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
