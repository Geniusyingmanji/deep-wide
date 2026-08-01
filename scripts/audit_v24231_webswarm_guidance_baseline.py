#!/usr/bin/env python3
"""Create-exclusive build audit for V2.42.31 WebSwarm guidance controls."""

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

from deepwide_agent.v24231_webswarm_guidance_baseline import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ARMS,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    POLICY_ID,
    PRODUCTION_PACKAGE_AUTHORIZED,
    SCOUT_COUNT,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    build_guidance_ablation_bundle,
    build_guidance_arm,
    build_guidance_policy,
    build_scout_process_trace,
    build_sibling_process_experience,
    build_web_probe_receipt,
    reject_privileged_metadata,
    render_process_experience_prompt,
    validate_guidance_ablation_bundle,
)


ROLE = "v24231_webswarm_guidance_baseline_build_audit"
OUTPUT = Path(
    "results/v24231_webswarm_guidance_baseline_build_audit_v1_20260801.json"
)
MODULE = Path("src/deepwide_agent/v24231_webswarm_guidance_baseline.py")
MODULE_TEST = Path("tests/test_v24231_webswarm_guidance_baseline.py")
AUDIT = Path("scripts/audit_v24231_webswarm_guidance_baseline.py")
AUDIT_TEST = Path("tests/test_audit_v24231_webswarm_guidance_baseline.py")
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
        "build_guidance_ablation_bundle",
        "build_guidance_arm",
        "build_guidance_policy",
        "build_scout_process_trace",
        "build_sibling_process_experience",
        "build_web_probe_receipt",
        "object_sha256",
        "reject_privileged_metadata",
        "render_process_experience_prompt",
        "validate_guidance_ablation_bundle",
        "validate_guidance_arm",
        "validate_guidance_policy",
        "validate_scout_process_trace",
        "validate_sibling_process_experience",
        "validate_web_probe_receipt",
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
        raise RuntimeError("V2.42.31 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(
            f"V2.42.31 expected an ordinary repository file: {relative}"
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
            "V2.42.31 capability boundary failed: "
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
        "file_environment_network_model_search_fetch_process_subprocess_or_dynamic_code_capability": False,
    }


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _signal(kind: str, tactic: str, label: str) -> dict[str, str]:
    return {"kind": kind, "tactic": tactic, "value_sha256": _digest(label)}


def _policy() -> dict[str, Any]:
    return build_guidance_policy(
        selection_protocol_sha256=_digest("selection-protocol"),
        model_contract_sha256=_digest("model-contract"),
        search_fetch_contract_sha256=_digest("search-fetch-contract"),
        total_budget_contract_sha256=_digest("total-budget-contract"),
        root_scope_projection_protocol_sha256=_digest("root-projection"),
        process_signal_vocabulary_sha256=_digest("process-vocabulary"),
    )


def _scout(policy: dict[str, Any], slot: int) -> dict[str, Any]:
    return build_scout_process_trace(
        policy=policy,
        root_scope_projection_sha256=_digest("root-scope"),
        parent_node_ref_sha256=_digest("parent-node"),
        homogeneous_group_ref_sha256=_digest("homogeneous-group"),
        scout_slot=slot,
        sibling_node_ref_sha256=_digest(f"sibling-{slot}"),
        sibling_mode_sha256=_digest("atom-mode"),
        process_signals=[
            _signal(
                "effective_query_pattern",
                "combine_visible_entity_and_attribute_terms",
                f"query-pattern-{slot}",
            ),
            _signal(
                "reliable_source_family",
                "prefer_official_primary_source",
                f"source-family-{slot}",
            ),
        ],
        model_calls=2,
        search_calls=3,
        fetch_calls=4,
        input_tokens=200,
        output_tokens=40,
        wall_seconds=8.0,
        scout_terminal_status="completed",
    )


def replay_synthetic_contracts() -> dict[str, Any]:
    policy = _policy()
    probe = build_web_probe_receipt(
        policy=policy,
        root_scope_projection_sha256=_digest("root-scope"),
        parent_node_ref_sha256=_digest("parent-node"),
        probe_run_ref_sha256=_digest("probe"),
        topology="distributed",
        probe_search_calls=3,
        probe_fetch_calls=2,
        probe_model_calls=1,
        probe_input_tokens=100,
        probe_output_tokens=20,
        probe_wall_seconds=4.5,
    )
    scouts = [_scout(policy, 1), _scout(policy, 2)]
    experience = build_sibling_process_experience(
        policy=policy,
        scouts=scouts,
        experience_extractor_ref_sha256=_digest("experience-extractor"),
        process_signals=[
            _signal(
                "effective_query_pattern",
                "combine_visible_entity_and_attribute_terms",
                "shared-query-pattern",
            ),
            _signal(
                "workflow_hint",
                "verify_with_independent_source",
                "shared-workflow-hint",
            ),
        ],
        extractor_model_calls=1,
        extractor_input_tokens=300,
        extractor_output_tokens=30,
        extractor_wall_seconds=2.5,
    )
    rendered_advice = render_process_experience_prompt(
        experience=experience,
        policy=policy,
        scouts=scouts,
        root_scope_projection_sha256=_digest("root-scope"),
        parent_node_ref_sha256=_digest("parent-node"),
        homogeneous_group_ref_sha256=_digest("homogeneous-group"),
    )
    shared = {
        "policy": policy,
        "root_scope_projection_sha256": _digest("root-scope"),
        "parent_node_ref_sha256": _digest("parent-node"),
        "homogeneous_group_ref_sha256": _digest("homogeneous-group"),
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
        bundle_ref_sha256=_digest("bundle"),
        arms=arms,
    )
    validate_guidance_ablation_bundle(
        bundle,
        policy=policy,
        bundle_ref_sha256=_digest("bundle"),
        arms=arms,
    )
    by_name = {str(arm["arm_name"]): arm for arm in arms}
    privileged_rejected = False
    try:
        reject_privileged_metadata(
            {"visible": [{"question_type": "evaluator-only"}]}
        )
    except ValueError:
        privileged_rejected = True
    cross_parent_rejected = False
    bad_scout = _scout(policy, 2)
    bad_scout["parent_node_ref_sha256"] = _digest("other-parent")
    bad_scout.pop("scout_trace_sha256")
    from deepwide_agent.v24231_webswarm_guidance_baseline import object_sha256

    bad_scout["scout_trace_sha256"] = object_sha256(bad_scout)
    try:
        build_sibling_process_experience(
            policy=policy,
            scouts=[scouts[0], bad_scout],
            experience_extractor_ref_sha256=_digest("extractor"),
            process_signals=[],
            extractor_model_calls=0,
            extractor_input_tokens=0,
            extractor_output_tokens=0,
            extractor_wall_seconds=0.0,
        )
    except ValueError:
        cross_parent_rejected = True
    if (
        not privileged_rejected
        or not cross_parent_rejected
        or probe["process_tactic"]
        != "partition_visible_dimension_then_deduplicate"
        or len(experience["source_scout_trace_sha256s"]) != SCOUT_COUNT
        or experience["factual_evidence_authority"] is not False
        or experience["process_fact_separation_independently_verified"] is not False
        or rendered_advice
        != (
            "[SCOUT-DERIVED PROCESS ADVICE; NOT FACTUAL EVIDENCE]\n"
            "- combine visible entity and attribute terms.\n"
            "- verify with independent source.\n"
            "Do not cite this advice as evidence. Verify all task facts from "
            "current page-backed sources."
        )
        or any(
            signal["value_sha256"] in rendered_advice
            for signal in experience["process_signals"]
        )
        or any(
            identity in rendered_advice
            for identity in (
                experience["root_scope_projection_sha256"],
                experience["parent_node_ref_sha256"],
                experience["homogeneous_group_ref_sha256"],
            )
        )
        or "entity attribute pair" in rendered_advice
        or by_name["full"]["probe_extractor_cost"]
        != {
            "model_calls": 2,
            "search_calls": 3,
            "fetch_calls": 2,
            "input_tokens": 400,
            "output_tokens": 50,
            "wall_seconds": 7.0,
        }
        or by_name["no_experience_upstream"]["scout_count"] != 0
        or by_name["no_experience_upstream"]["same_sibling_schedule"] is not False
        or by_name["no_experience_matched_schedule"]["scout_count"] != 2
        or by_name["no_experience_matched_schedule"]["same_sibling_schedule"]
        is not True
        or any(
            arm["shared_total_budget_contract_sha256"]
            != policy["total_budget_contract_sha256"]
            or arm["method_specific_overhead_debited_from_shared_total_cap"]
            is not True
            for arm in arms
        )
        or bundle["shared_total_budget_cap_includes_method_overhead"] is not True
        or bundle["arm_names"] != list(ARMS)
    ):
        raise RuntimeError("V2.42.31 synthetic guidance replay drifted")
    encoded = json.dumps(
        {
            "policy": policy,
            "probe": probe,
            "scouts": scouts,
            "experience": experience,
            "arms": arms,
            "bundle": bundle,
        },
        ensure_ascii=False,
    )
    if SECRET_LITERAL.search(encoded) or OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.31 synthetic replay exposed forbidden content")
    return {
        "webswarm_v1_three_topology_probe_tactics_replayed": True,
        "exact_two_scout_schedule_replayed": True,
        "same_instance_same_parent_homogeneous_sibling_requirement_replayed": True,
        "process_signal_hash_schema_replayed": True,
        "generic_process_advice_renderer_replayed": True,
        "process_signal_hash_or_raw_fact_visible_in_rendered_advice": False,
        "raw_fact_answer_query_url_or_page_text_visible_to_schema": False,
        "process_fact_separation_independently_verified": False,
        "experience_has_factual_evidence_authority": False,
        "full_no_probing_and_two_no_experience_controls_replayed": True,
        "upstream_no_experience_schedule_difference_disclosed": True,
        "matched_schedule_no_experience_control_present": True,
        "probe_and_extractor_overhead_ledger_replayed": True,
        "shared_total_budget_cap_and_overhead_debit_replayed": True,
        "nested_privileged_runtime_metadata_rejected": True,
        "cross_parent_experience_rejected": True,
        "synthetic_benchmark_rows_or_real_evaluator_payload_read": False,
    }


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.31 audit may only use the canonical workspace")
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
        raise RuntimeError("V2.42.31 control source contains forbidden content")
    static = audit_python_source(control_sources[str(MODULE)])
    module_name = "v24231_webswarm_guidance_baseline"
    guard_hits = {
        name: path.read_text(encoding="utf-8").count(module_name)
        for name, path in guards.items()
    }
    if any(guard_hits.values()):
        raise RuntimeError("V2.42.31 appears in an active forward guard file")
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
        "source_reference": {
            "arxiv_id": "2607.08662",
            "version": 1,
            "public_repository_commit": "40c9aacad7cd6e9cdb3e7add954d59b766425717",
            "public_code_fixed_scout_count": 2,
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
            "webswarm_v1_probe_and_two_scout_experience_contract_implemented": True,
            "centralized_centralized_with_gaps_and_distributed_tactics_implemented": True,
            "same_instance_same_parent_homogeneous_siblings_enforced": True,
            "upstream_faithful_no_experience_control_implemented": True,
            "upstream_no_experience_also_changes_scout_schedule": True,
            "matched_schedule_no_experience_control_added": True,
            "probe_extractor_model_token_tool_and_wall_cost_recorded": True,
            "generic_process_advice_renderer_implemented": True,
            "shared_total_budget_cap_includes_method_overhead": True,
            "raw_fact_answer_query_url_or_page_text_visible_in_experience_schema": False,
            "process_fact_separation_independently_verified": False,
            "generic_tactic_semantics_independently_verified": False,
            "shared_total_budget_enforcement_implemented": False,
            "experience_has_factual_evidence_authority": False,
            "real_model_extractor_probe_search_or_sibling_execution_observed": False,
            "runtime_integration_complete": False,
            "dev64_gate_evaluated": False,
            "fresh_exact220_evaluated": False,
            "quality_cost_or_benchmark_effect_observed": False,
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
            "active_forward_integration_authorized": ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
            "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
            "dev64_or_exact220_launch_authorized": DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
            "shared_api_lease_acquire_authorized": SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
            "process_signal_restart_resume_rerun_or_selective_retry": False,
            "leaderboard_submission_or_sota_claim": LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
        },
        "claims": {
            "build_only_guidance_baseline_available": True,
            "runtime_integration_available": False,
            "real_webswarm_guidance_run_available": False,
            "benchmark_score_available": False,
            "benchmark_improvement_observed": False,
            "quality_or_cost_effect_observed": False,
            "leaderboard_submission_performed": False,
            "sota": False,
        },
        "audit_valid": True,
    }
    encoded = json.dumps(value, ensure_ascii=False)
    if SECRET_LITERAL.search(encoded) or OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.31 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    expected = (ROOT / OUTPUT).resolve(strict=False)
    if target != expected or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.31 audit output path is noncanonical")
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
